"""交易服务：下单、库存锁、支付、发货、收货、取消、退款、申诉、状态机与时间线"""
from __future__ import annotations
import secrets
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from fastapi import APIRouter, Depends
from sqlalchemy import select, update, and_, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from ..db import get_db
from .. import errors, stock
from ..deps import get_current_user_async
from ..models import User, Item, Address, Order, OrderStatusLog, Conversation
from .. import state_machine
from ..schemas import OrderCreateReq, PayReq, ShipReq, RefundReq, DisputeReq
from ..serializers import order_brief

router = APIRouter(prefix="/api/v1/orders", tags=["orders"])

PAY_TIMEOUT_MINUTES = 15
AUTO_CONFIRM_DAYS = 10
REFUND_TIMEOUT_HOURS = 48

# 仅已结束的订单允许用户删除记录，进行中的订单需先完成或取消
DELETABLE_STATUS = {"COMPLETED", "CLOSED", "REFUNDED"}


def _ok(data=None, message="ok"):
    return {"code": 0, "message": message, "data": data}


def _gen_order_no() -> str:
    now = datetime.now()
    return f"IDX{now.strftime('%Y%m%d')}{secrets.randbelow(100000)}"


def _allowed_role(o: Order, user_id: int) -> bool:
    return o.buyer_id == user_id or o.seller_id == user_id


async def restore_item_stock(db, order: Order) -> None:
    """退款成功后释放占用：支付时扣减的真实库存需还给商品，售罄商品恢复在售。"""
    it = await db.get(Item, order.item_id)
    if not it or it.deleted_at is not None:
        return
    it.stock = it.stock + order.quantity
    if it.status == 5 and it.stock > 0:
        it.status = 3


@router.post("", name="create_order")
async def create_order(req: OrderCreateReq, user: User = Depends(get_current_user_async),
                       db: AsyncSession = Depends(get_db)):
    it = (await db.execute(select(Item).where(Item.id == req.item_id,
                                              Item.deleted_at.is_(None)))
          ).scalar_one_or_none()
    if not it:
        raise errors.error(errors.ErrorCodes.ITEM_NOT_FOUND, "item.not.found")
    if it.status != 3:
        raise errors.error(errors.ErrorCodes.ITEM_SOLD_OUT, "order.sold.out")
    if req.quantity < 1 or req.quantity > it.stock:
        raise errors.error(errors.ErrorCodes.STOCK_NOT_ENOUGH, "order.stock",
                           stock=it.stock)
    addr = (await db.execute(select(Address).where(
        Address.id == req.address_id, Address.user_id == user.id))).scalar_one_or_none()
    if not addr:
        raise errors.error(errors.ErrorCodes.ADDRESS_REQUIRED, "order.address")
    # 库存预占（开发环境内存锁：以可售库存再减锁定数作为可下单量）
    locked = stock.get_locked(it.id)
    available = it.stock - locked
    if available < req.quantity:
        raise errors.error(errors.ErrorCodes.STOCK_NOT_ENOUGH, "order.stock",
                           stock=available)
    stock.lock_stock(it.id, req.quantity, PAY_TIMEOUT_MINUTES * 60)

    unit = Decimal(str(req.price)) if req.price else Decimal(str(it.price))
    freight = Decimal(str(it.freight))
    total = unit * req.quantity + freight
    cover = it.images[0].url if it.images else ""
    snap = {"title": it.title, "cover": cover, "condition_level": it.condition_level,
            "unit_price": float(unit)}
    addr_snap = {"receiver": addr.receiver, "phone": addr.phone,
                 "province": addr.province, "city": addr.city, "district": addr.district,
                 "detail": addr.detail}
    order = Order(order_no=_gen_order_no(), buyer_id=user.id, seller_id=it.seller_id,
                  item_id=it.id, item_snapshot=snap, quantity=req.quantity,
                  unit_price=unit, freight=freight, total_amount=total,
                  address_snapshot=addr_snap, status="PENDING_PAYMENT")
    db.add(order)
    await db.flush()
    # 状态流转起点
    db.add(OrderStatusLog(order_id=order.id, from_status=None, to_status="PENDING_PAYMENT",
                          action="CREATE", operator_type="BUYER", operator_id=user.id,
                          remark="下单"))
    await db.commit()
    await db.refresh(order)
    return _ok({
        "orderNo": order.order_no, "totalAmount": float(order.total_amount),
        "status": order.status,
        "payExpireAt": (order.created_at + timedelta(minutes=PAY_TIMEOUT_MINUTES)).isoformat(),
    }, "订单创建成功，请在15分钟内完成支付")


async def _get_own_order(db, user: User, order_no: str, require_buyer: bool = None) -> Order:
    o = (await db.execute(select(Order).where(Order.order_no == order_no))).scalar_one_or_none()
    if not o or not _allowed_role(o, user.id):
        raise errors.error(errors.ErrorCodes.ORDER_NOT_FOUND, "order.not.found")
    if require_buyer is True and o.buyer_id != user.id:
        raise errors.error(errors.ErrorCodes.ORDER_NOT_FOUND, "order.not.found")
    if (o.buyer_id == user.id and o.buyer_deleted) or (o.seller_id == user.id and o.seller_deleted):
        raise errors.error(errors.ErrorCodes.ORDER_NOT_FOUND, "order.not.found")
    return o


@router.get("", name="list_orders")
async def list_orders(role: str = "buy", status: str | None = None,
                      user: User = Depends(get_current_user_async),
                      db: AsyncSession = Depends(get_db),
                      page: int = 1, size: int = 20):
    cond = [Order.created_at.isnot(None)]
    if role == "buy":
        cond.append(Order.buyer_id == user.id)
        cond.append(Order.buyer_deleted.is_(False))
    else:
        cond.append(Order.seller_id == user.id)
        cond.append(Order.seller_deleted.is_(False))
    if status and status != "ALL":
        cond.append(Order.status == status)
    total = (await db.execute(select(func.count()).select_from(Order)
                              .where(and_(*cond)))).scalar() or 0
    rows = (await db.execute(select(Order).where(and_(*cond))
                             .order_by(Order.created_at.desc())
                             .offset((page - 1) * size).limit(size))).scalars().all()
    return _ok({"list": [order_brief(o) for o in rows], "total": total,
                "page": page, "size": size})


@router.delete("/{order_no}", name="delete_order")
async def delete_order(order_no: str, user: User = Depends(get_current_user_async),
                       db: AsyncSession = Depends(get_db)):
    """从当前用户的订单列表移除该记录（买卖双方互不影响），删除后无法恢复。"""
    o = await _get_own_order(db, user, order_no)
    if o.status not in DELETABLE_STATUS:
        raise errors.error(errors.ErrorCodes.ORDER_DELETE_FORBIDDEN, "order.delete.forbidden")
    if o.buyer_id == user.id:
        o.buyer_deleted = True
    else:
        o.seller_deleted = True
    await db.commit()
    return _ok({"orderNo": o.order_no}, "订单记录已删除，该记录无法恢复")


@router.get("/{order_no}")
async def order_detail(order_no: str, user: User = Depends(get_current_user_async),
                       db: AsyncSession = Depends(get_db)):
    o = await _get_own_order(db, user, order_no)
    logs = (await db.execute(select(OrderStatusLog).where(OrderStatusLog.order_id == o.id)
                             .order_by(OrderStatusLog.operate_time.asc()))).scalars().all()
    brief = order_brief(o)
    brief["itemSnapshot"] = o.item_snapshot
    brief["addressSnapshot"] = o.address_snapshot
    brief["payExpireAt"] = (o.created_at + timedelta(minutes=PAY_TIMEOUT_MINUTES)).isoformat()
    brief["timeline"] = [{
        "fromStatus": lg.from_status, "toStatus": lg.to_status, "action": lg.action,
        "operatorType": lg.operator_type, "remark": lg.remark,
        "time": lg.operate_time.isoformat() if lg.operate_time else None} for lg in logs]
    return _ok(brief)


@router.post("/{order_no}/pay")
async def pay(order_no: str, req: PayReq, user: User = Depends(get_current_user_async),
              db: AsyncSession = Depends(get_db)):
    o = await _get_own_order(db, user, order_no, require_buyer=True)
    created = o.created_at
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) - created > timedelta(minutes=PAY_TIMEOUT_MINUTES):
        # 超时：若仍待付款则关闭
        if o.status == "PENDING_PAYMENT":
            await state_machine.transition(db, o, "timeout_close", "SYSTEM", None)
            await db.commit()
        raise errors.error(errors.ErrorCodes.ORDER_EXPIRED, "order.expired")
    if o.status != "PENDING_PAYMENT":
        raise errors.error(errors.ErrorCodes.ORDER_STATE_FORBIDDEN, "order.state")
    await state_machine.transition(db, o, "pay", "BUYER", user.id, "支付")
    o.paid_at = datetime.now(timezone.utc)
    o.pay_channel = req.channel
    # 扣减真实库存（支付后）
    it = await db.get(Item, o.item_id)
    if it:
        it.stock = max(0, it.stock - o.quantity)
        if it.stock == 0:
            it.status = 5  # 售罄置为已售出
        stock.release_stock(it.id, o.quantity)
        stock.mark_deducted(o.order_no)
    await db.commit()
    return _ok({"orderNo": o.order_no, "status": o.status}, "支付成功，资金已托管")


@router.post("/{order_no}/cancel")
async def cancel(order_no: str, user: User = Depends(get_current_user_async),
                 db: AsyncSession = Depends(get_db)):
    o = await _get_own_order(db, user, order_no, require_buyer=True)
    if o.status not in ("PENDING_PAYMENT",):
        # 已付款订单引导走退款
        if o.status in ("PAID", "SHIPPED"):
            raise errors.error(errors.ErrorCodes.ORDER_STATE_FORBIDDEN,
                               "该订单已付款，请申请退款")
        raise errors.error(errors.ErrorCodes.ORDER_STATE_FORBIDDEN, "order.state")
    await state_machine.transition(db, o, "cancel", "BUYER", user.id, "买家取消")
    stock.release_stock(o.item_id, o.quantity)
    await db.commit()
    return _ok({"orderNo": o.order_no, "status": o.status}, "订单已取消，库存已释放")


@router.post("/{order_no}/ship")
async def ship(order_no: str, req: ShipReq, user: User = Depends(get_current_user_async),
               db: AsyncSession = Depends(get_db)):
    o = await _get_own_order(db, user, order_no)
    if o.seller_id != user.id:
        raise errors.error(errors.ErrorCodes.ORDER_NOT_FOUND, "order.not.found")
    await state_machine.transition(db, o, "ship", "SELLER", user.id, "卖家发货")
    o.logistics_company = req.logisticsCompany
    o.tracking_no = req.trackingNo
    o.shipped_at = datetime.now(timezone.utc)
    await db.commit()
    return _ok({"orderNo": o.order_no, "status": o.status}, "发货成功")


@router.post("/{order_no}/confirm")
async def confirm(order_no: str, user: User = Depends(get_current_user_async),
                  db: AsyncSession = Depends(get_db)):
    o = await _get_own_order(db, user, order_no, require_buyer=True)
    if o.status != "SHIPPED":
        raise errors.error(errors.ErrorCodes.ORDER_CONFIRM_FORBIDDEN, "order.confirm")
    await state_machine.transition(db, o, "confirm", "BUYER", user.id, "确认收货")
    o.finished_at = datetime.now(timezone.utc)
    await db.commit()
    return _ok({"orderNo": o.order_no, "status": o.status}, "已确认收货，交易完成")


@router.post("/{order_no}/refund")
async def refund(order_no: str, req: RefundReq, user: User = Depends(get_current_user_async),
                 db: AsyncSession = Depends(get_db)):
    o = await _get_own_order(db, user, order_no, require_buyer=True)
    if o.status not in ("PAID", "SHIPPED"):
        raise errors.error(errors.ErrorCodes.ORDER_STATE_FORBIDDEN, "order.state")
    await state_machine.transition(db, o, "refund", "BUYER", user.id,
                                   f"申请退款：{req.reason[:100]}")
    await db.commit()
    return _ok({"orderNo": o.order_no, "status": o.status}, "退款申请已提交，等待卖家处理")


@router.post("/{order_no}/refund/agree")
async def refund_agree(order_no: str, user: User = Depends(get_current_user_async),
                       db: AsyncSession = Depends(get_db)):
    o = await _get_own_order(db, user, order_no)
    if o.seller_id != user.id:
        raise errors.error(errors.ErrorCodes.ORDER_NOT_FOUND, "order.not.found")
    if o.status != "REFUNDING":
        raise errors.error(errors.ErrorCodes.ORDER_STATE_FORBIDDEN, "order.state")
    await state_machine.transition(db, o, "seller_agree_refund", "SELLER", user.id, "卖家同意退款")
    await restore_item_stock(db, o)
    await db.commit()
    return _ok({"orderNo": o.order_no, "status": o.status}, "退款成功，商品库存已恢复")


@router.post("/{order_no}/dispute")
async def dispute(order_no: str, req: DisputeReq, user: User = Depends(get_current_user_async),
                  db: AsyncSession = Depends(get_db)):
    o = await _get_own_order(db, user, order_no)
    if o.status not in ("PAID", "SHIPPED"):
        raise errors.error(errors.ErrorCodes.ORDER_STATE_FORBIDDEN, "order.state")
    await state_machine.transition(db, o, "dispute", "BUYER", user.id, f"发起申诉：{req.reason[:100]}")
    await db.commit()
    return _ok({"orderNo": o.order_no, "status": o.status}, "申诉已提交，平台将介入处理")