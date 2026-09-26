"""商品服务：发布、编辑、详情、上下架、删除、我的发布"""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from ..db import get_db
from .. import errors, sensitive
from ..deps import ensure_can_publish, get_current_user_async
from ..state_machine import ACTIVE_ORDER_STATUSES
from ..models import User, Item, ItemImage, Favorite, Footprint, Order, Category
from ..schemas import ItemCreateReq, ItemStatusReq
from ..serializers import item_brief, user_summary

router = APIRouter(prefix="/api/v1", tags=["items"])


def _ok(data=None, message="ok"):
    return {"code": 0, "message": message, "data": data}


def _validate_item_input(req: ItemCreateReq):
    if not (5 <= len(req.title.strip()) <= 50):
        raise errors.error(errors.ErrorCodes.TITLE_LENGTH, "title.length")
    if not (10 <= len(req.description.strip()) <= 2000):
        raise errors.error(errors.ErrorCodes.DESC_LENGTH, "desc.length")
    if req.price is None or not (0 < req.price <= 1000000):
        raise errors.error(errors.ErrorCodes.PRICE_INVALID, "price.invalid")
    if not (1 <= req.stock):
        raise errors.error(errors.ErrorCodes.STOCK_INVALID, "stock.invalid")
    if not (1 <= req.condition_level <= 4):
        raise errors.error(errors.ErrorCodes.PRICE_INVALID, "price.invalid")
    if sensitive.check_sensitive(req.title) or sensitive.check_sensitive(req.description):
        raise errors.error(errors.ErrorCodes.SENSITIVE_CONTENT, "sensitive")
    if not (1 <= len(req.images) <= 9):
        raise errors.error(errors.ErrorCodes.IMAGE_COUNT, "image.count")


async def _category_valid(db, category_id: int):
    c = await db.get(Category, category_id)
    if not c or c.level != 3:
        raise errors.error(errors.ErrorCodes.CATEGORY_INVALID, "category.invalid")


@router.post("/items")
async def create_item(req: ItemCreateReq, user: User = Depends(get_current_user_async),
                      db: AsyncSession = Depends(get_db)):
    ensure_can_publish(user)
    _validate_item_input(req)
    await _category_valid(db, req.category_id)
    it = Item(seller_id=user.id, title=req.title.strip(), description=req.description.strip(),
              category_id=req.category_id, condition_level=req.condition_level, price=req.price,
              origin_price=req.origin_price, stock=req.stock, city=req.city or "",
              trade_type=req.trade_type, freight_payer=req.freight_payer, freight=req.freight,
              status=2, extra=req.extra)
    db.add(it)
    await db.flush()
    for i, url in enumerate(req.images[:9]):
        db.add(ItemImage(item_id=it.id, url=url, sort=i, audit_status=2))
    await db.commit()
    await db.refresh(it)
    # 移除 seller 未加载问题：重新查询
    from sqlalchemy.orm import selectinload
    it2 = (await db.execute(select(Item).where(Item.id == it.id)
                            .options(selectinload(Item.images),
                                     selectinload(Item.seller)))).scalar_one()
    return _ok({"item": item_brief(it2)}, "商品已提交，等待平台审核通过后上架")


@router.put("/items/{item_id}")
async def edit_item(item_id: int, req: ItemCreateReq,
                    user: User = Depends(get_current_user_async),
                    db: AsyncSession = Depends(get_db)):
    it = (await db.execute(select(Item).where(Item.id == item_id,
                                              Item.deleted_at.is_(None)))).scalar_one_or_none()
    if not it:
        raise errors.error(errors.ErrorCodes.ITEM_NOT_FOUND, "item.not.found")
    if it.seller_id != user.id:
        raise errors.error(errors.ErrorCodes.ITEM_NOT_FOUND, "item.not.found")
    if it.status == 5:  # 已售出不可编辑
        raise errors.error(errors.ErrorCodes.ITEM_STATUS_FORBIDDEN, "item.status.forbidden")
    _validate_item_input(req)
    it.title = req.title.strip(); it.description = req.description.strip()
    it.category_id = req.category_id; it.condition_level = req.condition_level
    it.price = req.price; it.origin_price = req.origin_price; it.stock = req.stock
    it.city = req.city or ""; it.trade_type = req.trade_type
    it.freight_payer = req.freight_payer; it.freight = req.freight; it.extra = req.extra
    it.updated_at = datetime.now(timezone.utc)
    # 在售商品被修改后需重新审核，避免改文案绕过审核
    recheck = it.status == 3
    if recheck:
        it.status = 2
    await db.execute(update(ItemImage).where(ItemImage.item_id == it.id).values(url=""))
    await db.flush()
    for i, url in enumerate(req.images[:9]):
        rows = (await db.execute(select(ItemImage).where(
            ItemImage.item_id == it.id).order_by(ItemImage.sort))).scalars().all()
        if i < len(rows):
            rows[i].url = url
        else:
            db.add(ItemImage(item_id=it.id, url=url, sort=i, audit_status=2))
    await db.commit()
    from sqlalchemy.orm import selectinload
    it2 = (await db.execute(select(Item).where(Item.id == item_id)
                            .options(selectinload(Item.images),
                                     selectinload(Item.seller)))).scalar_one()
    return _ok({"item": item_brief(it2)},
               "商品已更新，等待平台重新审核通过后上架" if recheck else "商品已更新")


@router.get("/items/mine")
async def my_items(user: User = Depends(get_current_user_async),
                   db: AsyncSession = Depends(get_db),
                   status: int | None = None):
    from sqlalchemy.orm import selectinload
    q = select(Item).where(Item.seller_id == user.id, Item.deleted_at.is_(None))
    if status:
        q = q.where(Item.status == status)
    rows = (await db.execute(q.order_by(Item.created_at.desc())
                             .options(selectinload(Item.images),
                                      selectinload(Item.seller)))).scalars().all()
    return _ok({"list": [item_brief(it) for it in rows], "total": len(rows)})


@router.get("/items/{item_id}")
async def item_detail(item_id: int, db: AsyncSession = Depends(get_db)):
    from sqlalchemy.orm import selectinload
    it = (await db.execute(select(Item).where(Item.id == item_id, Item.deleted_at.is_(None))
                           .options(selectinload(Item.images), selectinload(Item.seller)))
          ).scalar_one_or_none()
    if not it:
        raise errors.error(errors.ErrorCodes.ITEM_NOT_FOUND, "item.not.found")
    # 浏览量（未登录用户也计数；简化：仅非本人）
    it.view_count += 1
    await db.commit()
    return _ok(item_brief(it))


@router.post("/items/{item_id}/status")
async def item_status(item_id: int, req: ItemStatusReq,
                      user: User = Depends(get_current_user_async),
                      db: AsyncSession = Depends(get_db)):
    it = (await db.execute(select(Item).where(Item.id == item_id,
                                              Item.deleted_at.is_(None)))).scalar_one_or_none()
    if not it:
        raise errors.error(errors.ErrorCodes.ITEM_NOT_FOUND, "item.not.found")
    if it.seller_id != user.id:
        raise errors.error(errors.ErrorCodes.ITEM_NOT_FOUND, "item.not.found")
    if req.action == "on_sale":
        ensure_can_publish(user)
        # 仅「已下架」可重新上架；待审核/已驳回必须走平台审核，防止绕过审核直接上架
        if it.status != 4:
            raise errors.error(errors.ErrorCodes.ITEM_STATUS_FORBIDDEN, "item.audit.required")
        if it.stock < 1:
            raise errors.error(errors.ErrorCodes.STOCK_INVALID, "stock.invalid")
        it.status = 3
    elif req.action == "off_sale":
        it.status = 4
    elif req.action == "delete":
        # 仅「进行中」的订单阻塞删除；已关闭/已退款/已完成的订单不阻塞（订单展示依赖快照）
        active_order = (await db.execute(select(Order).where(
            Order.item_id == it.id,
            Order.status.in_(ACTIVE_ORDER_STATUSES)).limit(1))).scalar_one_or_none()
        if active_order:
            raise errors.error(errors.ErrorCodes.ITEM_HAS_ORDERS, "item.has.orders")
        it.deleted_at = datetime.now(timezone.utc)
    else:
        raise errors.error(errors.ErrorCodes.ITEM_STATUS_FORBIDDEN, "item.status.forbidden")
    await db.commit()
    return _ok({"itemId": it.id, "status": it.status}, "操作成功")


# ---------- 收藏 ----------
@router.post("/favorites")
async def toggle_favorite(data: dict, user: User = Depends(get_current_user_async),
                          db: AsyncSession = Depends(get_db)):
    item_id = data.get("itemId")
    if not item_id:
        raise errors.error(errors.ErrorCodes.ITEM_NOT_FOUND, "item.not.found")
    it = (await db.execute(select(Item).where(Item.id == item_id,
                                              Item.deleted_at.is_(None)))).scalar_one_or_none()
    if not it:
        raise errors.error(errors.ErrorCodes.ITEM_NOT_FOUND, "item.not.found")
    fav = (await db.execute(select(Favorite).where(Favorite.user_id == user.id,
                                                   Favorite.item_id == item_id))
           ).scalar_one_or_none()
    if fav:
        await db.delete(fav)
        await db.commit()
        return _ok({"favorited": False}, "已取消收藏")
    db.add(Favorite(user_id=user.id, item_id=item_id))
    await db.commit()
    return _ok({"favorited": True}, "已收藏")


# ---------- 足迹记录 ----------
@router.post("/footprints")
async def record_footprint(data: dict, user: User = Depends(get_current_user_async),
                           db: AsyncSession = Depends(get_db)):
    item_id = data.get("itemId")
    if not item_id:
        raise errors.error(errors.ErrorCodes.ITEM_NOT_FOUND, "item.not.found")
    exists = (await db.execute(select(Footprint).where(
        Footprint.user_id == user.id, Footprint.item_id == item_id))).scalar_one_or_none()
    if not exists:
        db.add(Footprint(user_id=user.id, item_id=item_id))
        await db.commit()
    return _ok()