"""用户服务：资料/地址/收藏与足迹/注销"""
from fastapi import APIRouter, Depends
from sqlalchemy import select, func, delete, update
from sqlalchemy.ext.asyncio import AsyncSession
from ..db import get_db
from .. import errors
from ..deps import get_current_user_async
from ..models import User, Address, Favorite, Item, Footprint, Order
from ..schemas import ProfileUpdateReq, AddressReq
from ..serializers import user_summary, item_brief

router = APIRouter(prefix="/api/v1/users", tags=["users"])


def _ok(data=None, message="ok"):
    return {"code": 0, "message": message, "data": data}


@router.get("/me")
async def read_me(user: User = Depends(get_current_user_async)):
    return _ok(user_summary(user))


@router.put("/me")
async def update_me(req: ProfileUpdateReq, user: User = Depends(get_current_user_async),
                    db: AsyncSession = Depends(get_db)):
    if req.avatar is not None:
        user.avatar = req.avatar
    if req.gender is not None:
        user.gender = req.gender
    if req.city is not None:
        user.city = req.city
    if req.bio is not None:
        user.bio = req.bio
    await db.commit()
    return _ok(user_summary(user), "资料已更新")


@router.get("/addresses")
async def list_addresses(user: User = Depends(get_current_user_async),
                         db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(Address).where(Address.user_id == user.id)
                             .order_by(Address.is_default.desc(), Address.created_at.desc()))
            ).scalars().all()
    return _ok([{
        "id": a.id, "receiver": a.receiver, "phone": a.phone,
        "province": a.province, "city": a.city, "district": a.district,
        "detail": a.detail, "isDefault": a.is_default} for a in rows])


@router.post("/addresses")
async def create_address(req: AddressReq, user: User = Depends(get_current_user_async),
                         db: AsyncSession = Depends(get_db)):
    if not (req.receiver and req.phone and req.detail):
        raise errors.error(errors.ErrorCodes.ADDRESS_MISSING_FIELDS, "address.missing")
    count = (await db.execute(select(func.count()).select_from(Address)
                              .where(Address.user_id == user.id))).scalar()
    if count >= 20:
        raise errors.error(errors.ErrorCodes.ADDRESS_LIMIT, "address.limit")
    if req.is_default:
        await db.execute(update(Address).where(Address.user_id == user.id)
                         .values(is_default=False))
    a = Address(user_id=user.id, **req.model_dump())
    db.add(a)
    await db.commit()
    return _ok({"id": a.id}, "地址已添加")


@router.put("/addresses/{addr_id}")
async def update_address(addr_id: int, req: AddressReq,
                         user: User = Depends(get_current_user_async),
                         db: AsyncSession = Depends(get_db)):
    a = (await db.execute(select(Address).where(
        Address.id == addr_id, Address.user_id == user.id))).scalar_one_or_none()
    if not a:
        raise errors.BizError(404, "地址不存在", http_status=404)
    if req.is_default:
        await db.execute(update(Address).where(Address.user_id == user.id)
                         .values(is_default=False))
    for k, v in req.model_dump().items():
        setattr(a, k, v)
    await db.commit()
    return _ok({"id": a.id}, "地址已更新")


@router.delete("/addresses/{addr_id}")
async def delete_address(addr_id: int, user: User = Depends(get_current_user_async),
                         db: AsyncSession = Depends(get_db)):
    a = (await db.execute(select(Address).where(
        Address.id == addr_id, Address.user_id == user.id))).scalar_one_or_none()
    if not a:
        raise errors.BizError(404, "地址不存在", http_status=404)
    await db.delete(a)
    await db.commit()
    return _ok({"id": addr_id}, "地址已删除")


# ---------- 收藏 ----------
@router.get("/favorites")
async def list_favorites(user: User = Depends(get_current_user_async),
                         db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(
        select(Favorite, Item).join(Item, Item.id == Favorite.item_id)
        .where(Favorite.user_id == user.id)
        .order_by(Favorite.created_at.desc())
    )).all()
    items = [item_brief(it) for _, it in rows]
    # 标记是否已收藏
    return _ok({"list": items, "total": len(items)})


# ---------- 足迹 ----------
@router.get("/footprints")
async def list_footprints(user: User = Depends(get_current_user_async),
                          db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(
        select(Footprint, Item).join(Item, Item.id == Footprint.item_id)
        .where(Footprint.user_id == user.id)
        .order_by(Footprint.created_at.desc()).limit(100)
    )).all()
    return _ok({"list": [item_brief(it) for _, it in rows]})


@router.delete("/footprints")
async def clear_footprints(user: User = Depends(get_current_user_async),
                           db: AsyncSession = Depends(get_db)):
    await db.execute(delete(Footprint).where(Footprint.user_id == user.id))
    await db.commit()
    return _ok(message="足迹已清空")


@router.delete("/footprints/{item_id}")
async def del_footprint(item_id: int, user: User = Depends(get_current_user_async),
                        db: AsyncSession = Depends(get_db)):
    await db.execute(delete(Footprint).where(
        Footprint.user_id == user.id, Footprint.item_id == item_id))
    await db.commit()
    return _ok(message="已删除")


# ---------- 注销 ----------
@router.post("/me/deactivate")
async def deactivate(user: User = Depends(get_current_user_async),
                     db: AsyncSession = Depends(get_db)):
    active = (await db.execute(select(func.count()).select_from(Order).where(
        Order.buyer_id == user.id, Order.status.in_(["PENDING_PAYMENT", "PAID",
                                                     "SHIPPED", "REFUNDING", "DISPUTING"])))).scalar()
    if active:
        raise errors.error(errors.ErrorCodes.ACCOUNT_ACTIVE_ORDERS, "account.active.orders")
    from datetime import datetime, timezone
    user.deleted_at = datetime.now(timezone.utc)
    await db.commit()
    return _ok(message="账号已注销")