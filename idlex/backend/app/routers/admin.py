"""管理服务：登录、商品审核、用户处置、订单干预、举报处理、敏感词、数据看板"""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy import select, func, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from ..db import get_db
from .. import errors, auth, sensitive, state_machine, stock
from ..deps import get_current_admin
from ..models import (AdminUser, Item, User, Order, Report, SensitiveWord, Review,
                      OrderStatusLog)
from ..schemas import AuditReq, UserActionReq, OrderInterveneReq, ReportHandleReq, SensitiveWordReq

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


def _ok(data=None, message="ok"):
    return {"code": 0, "message": message, "data": data}


def _require_reason(reason: str | None):
    if not reason or not reason.strip():
        raise errors.error(errors.ErrorCodes.ADMIN_REASON_REQUIRED, "admin.reason")


# 订单已处理完（终态）后才允许后台删除记录；进行中的订单必须先干预或等其结束
ORDER_TERMINAL_STATUSES = {"COMPLETED", "CLOSED", "REFUNDED"}


@router.post("/login", name="admin_login")
async def admin_login(data: dict, db: AsyncSession = Depends(get_db)):
    username = data.get("username", "")
    password = data.get("password", "")
    adm = (await db.execute(select(AdminUser).where(AdminUser.username == username))
           ).scalar_one_or_none()
    if not adm or not auth.verify_password(adm.password_hash, password) or adm.status != 1:
        raise errors.error(errors.ErrorCodes.LOGIN_FAILED, "login.failed")
    access, refresh = auth.issue_tokens("admin", adm.id)
    return _ok({"accessToken": access, "refreshToken": refresh,
                "expiresIn": 7200, "adminId": adm.id, "username": adm.username}, "登录成功")


@router.get("/dashboard")
async def dashboard(admin: AdminUser = Depends(get_current_admin),
                    db: AsyncSession = Depends(get_db)):
    async def one(stmt):
        return (await db.execute(stmt)).scalar() or 0

    today = datetime.now().date()
    users = await one(select(func.count()).select_from(User).where(User.deleted_at.is_(None)))
    items = await one(select(func.count()).select_from(Item).where(Item.deleted_at.is_(None)))
    on_sale = await one(select(func.count()).select_from(Item).where(Item.status == 3))
    orders = await one(select(func.count()).select_from(Order))
    today_orders = await one(select(func.count()).select_from(Order).where(
        func.date(Order.created_at) == today))
    amount = await one(select(func.coalesce(func.sum(Order.total_amount), 0)).where(
        Order.status.in_(["PAID", "SHIPPED", "COMPLETED"])))
    pending_audit = await one(select(func.count()).select_from(Item).where(Item.status == 2))
    pending_report = await one(select(func.count()).select_from(Report).where(Report.status == 0))
    return _ok({
        "users": users, "items": items, "onSale": on_sale, "orders": orders,
        "todayOrders": today_orders, "amount": round(float(amount), 2),
        "pendingAudit": pending_audit, "pendingReport": pending_report,
    })


@router.get("/items")
async def admin_items(status: int | None = None, keyword: str | None = None,
                      admin: AdminUser = Depends(get_current_admin),
                      db: AsyncSession = Depends(get_db)):
    from sqlalchemy.orm import selectinload
    q = select(Item).where(Item.deleted_at.is_(None))
    if status:
        q = q.where(Item.status == status)
    if keyword:
        q = q.where(Item.title.contains(keyword))
    rows = (await db.execute(q.order_by(Item.created_at.desc()).limit(200)
                             .options(selectinload(Item.seller)))).scalars().all()
    from ..serializers import item_brief
    return _ok({"list": [dict(item_brief(it), sellerName=it.seller.username) for it in rows]})


@router.post("/items/{item_id}/audit")
async def audit_item(item_id: int, req: AuditReq, admin: AdminUser = Depends(get_current_admin),
                     db: AsyncSession = Depends(get_db)):
    _require_reason(req.reason) if not req.approve else None
    it = await db.get(Item, item_id)
    if not it:
        raise errors.error(errors.ErrorCodes.ITEM_NOT_FOUND, "item.not.found")
    it.status = 3 if req.approve else 6
    await db.commit()
    return _ok({"itemId": it.id, "status": it.status},
               "审核通过" if req.approve else "已驳回")


@router.get("/users")
async def admin_users(keyword: str | None = None,
                      admin: AdminUser = Depends(get_current_admin),
                      db: AsyncSession = Depends(get_db)):
    q = select(User).where(User.deleted_at.is_(None))
    if keyword:
        q = q.where(User.username.contains(keyword))
    rows = (await db.execute(q.order_by(User.created_at.desc()).limit(200))).scalars().all()
    return _ok({"list": [{
        "id": u.id, "username": u.username, "phone": u.phone, "avatar": u.avatar,
        "city": u.city, "creditLevel": u.credit_level, "status": u.status,
        "createdAt": u.created_at.isoformat() if u.created_at else None} for u in rows]})


@router.post("/users/{user_id}/action")
async def user_action(user_id: int, req: UserActionReq,
                      admin: AdminUser = Depends(get_current_admin),
                      db: AsyncSession = Depends(get_db)):
    _require_reason(req.reason)
    u = await db.get(User, user_id)
    if not u or u.deleted_at is not None:
        raise errors.error(errors.ErrorCodes.ADMIN_USER_NOT_FOUND, "admin.user.not.found")
    if req.action == "ban":
        u.status = 2
    elif req.action == "unban":
        u.status = 1
    elif req.action == "ban_publish":
        u.status = 3 if u.status == 1 else u.status
    elif req.action == "unpublish_ban":
        u.status = 1 if u.status == 3 else u.status
    else:
        raise errors.error(errors.ErrorCodes.ADMIN_REASON_REQUIRED, "admin.reason")
    await db.commit()
    return _ok({"userId": u.id, "status": u.status}, "已处置")


@router.get("/orders")
async def admin_orders(status: str | None = None,
                       admin: AdminUser = Depends(get_current_admin),
                       db: AsyncSession = Depends(get_db)):
    q = select(Order)
    if status:
        q = q.where(Order.status == status)
    rows = (await db.execute(q.order_by(Order.created_at.desc()).limit(200))).scalars().all()
    from ..serializers import order_brief
    return _ok({"list": [dict(
        order_brief(o),
        intervenedAt=o.intervened_at.isoformat() if o.intervened_at else None,
        interveneAction=o.intervene_action,
        interveneReason=o.intervene_reason,
    ) for o in rows]})


@router.post("/orders/{order_no}/intervene")
async def order_intervene(order_no: str, req: OrderInterveneReq,
                          admin: AdminUser = Depends(get_current_admin),
                          db: AsyncSession = Depends(get_db)):
    _require_reason(req.reason)
    o = (await db.execute(select(Order).where(Order.order_no == order_no))).scalar_one_or_none()
    if not o:
        raise errors.error(errors.ErrorCodes.ORDER_NOT_FOUND, "order.not.found")
    mapping = {"close": "admin_close", "refund": "admin_refund", "to_ship": "admin_to_ship",
               "to_shipped": "admin_to_shipped"}
    action = mapping.get(req.action)
    if action:
        if action == "admin_refund":
            # 已支付订单被判定退款：把支付时扣减的库存还给商品
            from .orders import restore_item_stock
            await restore_item_stock(db, o)
        elif action == "admin_close":
            # 待付款订单被关闭：释放内存中的库存占用
            stock.release_stock(o.item_id, o.quantity)
        await state_machine.transition(db, o, action, "ADMIN", admin.id, req.reason)
    o.intervened_at = datetime.now(timezone.utc)
    o.intervene_action = req.action
    o.intervene_reason = req.reason.strip()
    await db.commit()
    return _ok({"orderNo": o.order_no, "status": o.status,
                "intervenedAt": o.intervened_at.isoformat(),
                "interveneAction": o.intervene_action}, "已干预")


@router.delete("/orders/{order_no}")
async def admin_delete_order(order_no: str, admin: AdminUser = Depends(get_current_admin),
                             db: AsyncSession = Depends(get_db)):
    """删除已处理完的订单记录（已终态或已被干预过），进行中的订单不允许删除。"""
    o = (await db.execute(select(Order).where(Order.order_no == order_no))).scalar_one_or_none()
    if not o:
        raise errors.error(errors.ErrorCodes.ORDER_NOT_FOUND, "order.not.found")
    if o.intervened_at is None and o.status not in ORDER_TERMINAL_STATUSES:
        raise errors.error(errors.ErrorCodes.ORDER_DELETE_FORBIDDEN, "order.delete.forbidden")
    # 订单的从属记录一并清理，避免留下悬空的流转日志与评价
    await db.execute(delete(OrderStatusLog).where(OrderStatusLog.order_id == o.id))
    await db.execute(delete(Review).where(Review.order_id == o.id))
    await db.delete(o)
    await db.commit()
    return _ok({"orderNo": order_no}, "订单记录已删除，该记录无法恢复")


@router.get("/reports")
async def admin_reports(status: int | None = None,
                        admin: AdminUser = Depends(get_current_admin),
                        db: AsyncSession = Depends(get_db)):
    q = select(Report)
    if status is not None:
        q = q.where(Report.status == status)
    rows = (await db.execute(q.order_by(Report.created_at.desc()).limit(200))).scalars().all()
    from .reports import _parse_evidence
    return _ok({"list": [{
        "id": r.id, "targetType": r.target_type, "targetId": r.target_id,
        "reasonType": r.reason_type, "description": r.description,
        "evidence": _parse_evidence(r.evidence),
        "status": r.status, "result": r.result,
        "createdAt": r.created_at.isoformat() if r.created_at else None} for r in rows]})


@router.post("/reports/{report_id}/handle")
async def report_handle(report_id: int, req: ReportHandleReq,
                        admin: AdminUser = Depends(get_current_admin),
                        db: AsyncSession = Depends(get_db)):
    _require_reason(req.reason)
    r = await db.get(Report, report_id)
    if not r:
        raise errors.error(errors.ErrorCodes.ADMIN_USER_NOT_FOUND, "admin.user.not.found")
    r.status = 2
    r.result = ("成立：" if req.approve else "不成立：") + req.reason
    if req.approve:
        if r.target_type == "item":
            it = await db.get(Item, r.target_id)
            if it:
                it.status = 4  # 下架
        elif r.target_type == "user":
            u = await db.get(User, r.target_id)
            if u:
                u.status = 3  # 禁用发布
    await db.commit()
    return _ok({"reportId": r.id, "status": r.status}, "已处理")


@router.get("/sensitive-words")
async def list_words(admin: AdminUser = Depends(get_current_admin),
                     db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(SensitiveWord).order_by(SensitiveWord.id))).scalars().all()
    return _ok({"list": [{"id": w.id, "word": w.word, "level": w.level, "status": w.status}
                         for w in rows]})


@router.post("/sensitive-words")
async def add_word(req: SensitiveWordReq, admin: AdminUser = Depends(get_current_admin),
                   db: AsyncSession = Depends(get_db)):
    if not req.word.strip():
        raise errors.error(errors.ErrorCodes.ADMIN_REASON_REQUIRED, "admin.reason")
    w = SensitiveWord(word=req.word.strip(), level=req.level, status=req.status)
    db.add(w)
    await db.commit()
    await _rebuild_sensitive(db)
    return _ok({"id": w.id, "word": w.word}, "已添加")


@router.delete("/sensitive-words/{word_id}")
async def del_word(word_id: int, admin: AdminUser = Depends(get_current_admin),
                   db: AsyncSession = Depends(get_db)):
    w = await db.get(SensitiveWord, word_id)
    if w:
        w.status = 0
        await db.commit()
        await _rebuild_sensitive(db)
    return _ok(message="已停用")


async def _rebuild_sensitive(db):
    words = (await db.execute(select(SensitiveWord).where(SensitiveWord.status == 1))
             ).scalars().all()
    sensitive.build_from_words([w.word for w in words])