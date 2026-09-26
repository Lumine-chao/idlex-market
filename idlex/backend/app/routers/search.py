"""检索服务（开发环境用 DB 实现，对齐文档的分词/筛选/排序/联想语义）"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, or_, and_, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from ..db import get_db
from .. import errors
from ..models import Item, Category
from ..serializers import item_brief

router = APIRouter(prefix="/api/v1/search", tags=["search"])


def _ok(data=None, message="ok"):
    return {"code": 0, "message": message, "data": data}


@router.get("", name="search_items")
async def search_items(q: str = "", category_id: int | None = None,
                       condition: str | None = None,
                       min_price: float | None = None, max_price: float | None = None,
                       city: str | None = None, trade_type: int | None = None,
                       free_shipping: bool | None = None,
                       sort: str = "relevance", page: int = 1, size: int = 20,
                       db: AsyncSession = Depends(get_db)):
    if len(q) > 50:
        raise errors.error(errors.ErrorCodes.KEYWORD_TOO_LONG, "keyword.long")
    if min_price is not None and max_price is not None and min_price > max_price:
        raise errors.error(errors.ErrorCodes.PRICE_RANGE_INVALID, "price.range")
    size = size if size in (20, 40, 60) else 20
    if page < 1:
        page = 1
    cond = [Item.status == 3, Item.deleted_at.is_(None)]
    if q:
        like = f"%{q}%"
        cond.append(or_(Item.title.like(like), Item.description.like(like)))
    if category_id:
        # 支持末级或父级分类：收集该分类及其下后代
        cat_ids = await _category_and_children(db, category_id)
        cond.append(Item.category_id.in_(cat_ids))
    if condition:
        try:
            conds = [int(x) for x in condition.split(",") if x]
        except Exception:
            conds = []
        if conds:
            cond.append(Item.condition_level.in_(conds))
    if min_price is not None:
        cond.append(Item.price >= min_price)
    if max_price is not None:
        cond.append(Item.price <= max_price)
    if city:
        cond.append(Item.city == city)
    if trade_type:
        cond.append(Item.trade_type == trade_type)
    if free_shipping:
        cond.append(Item.freight == 0)

    query = select(Item).where(and_(*cond))
    total = (await db.execute(select(func.count()).select_from(Item)
                              .where(and_(*cond)))).scalar()

    if sort == "price_asc":
        query = query.order_by(Item.price.asc())
    elif sort == "price_desc":
        query = query.order_by(Item.price.desc())
    elif sort == "newest":
        query = query.order_by(Item.created_at.desc())
    else:
        query = query.order_by(Item.view_count.desc(), Item.created_at.desc())

    rows = (await db.execute(query.offset((page - 1) * size).limit(size)
                             .options(selectinload(Item.images),
                                      selectinload(Item.seller)))).scalars().all()
    items = [item_brief(it) for it in rows]
    if not items and page == 1 and (q or min_price or max_price or condition):
        items = await _fallback_same_category(db, category_id, min_price, max_price)
        return _ok({"total": len(items), "page": 1, "size": size, "list": items,
                    "fallback": True})
    return _ok({"total": total or 0, "page": page, "size": size, "list": items,
                "fallback": False})


async def _category_and_children(db, cat_id: int) -> list[int]:
    c = await db.get(Category, cat_id)
    if not c:
        return [cat_id]
    if c.level == 3:
        return [c.id]
    rows = (await db.execute(select(Category.id).where(
        (Category.parent_id == c.id) | (Category.id == c.id)))).scalars().all()
    direct = list(rows)
    # collect grandchildren
    grand = (await db.execute(select(Category.id).where(
        Category.parent_id.in_(direct)))).scalars().all()
    return list(dict.fromkeys([c.id] + direct + list(grand)))


async def _fallback_same_category(db, category_id, min_price, max_price):
    if not category_id:
        return []
    cat_ids = await _category_and_children(db, category_id)
    cond = [Item.status == 3, Item.deleted_at.is_(None), Item.category_id.in_(cat_ids)]
    if min_price:
        cond.append(Item.price >= min_price * 0.6)
    if max_price:
        cond.append(Item.price <= max_price * 1.6)
    rows = (await db.execute(select(Item).where(and_(*cond)).limit(6)
                             .options(selectinload(Item.images),
                                      selectinload(Item.seller)))).scalars().all()
    return [item_brief(it) for it in rows]


@router.get("/suggest")
async def suggest(q: str = "", db: AsyncSession = Depends(get_db)):
    if not q:
        return _ok({"keywords": [], "categories": []})
    like = f"%{q}%"
    kw = (await db.execute(select(Item.title).where(
        Item.title.like(like), Item.status == 3).limit(8))).scalars().all()
    cats = (await db.execute(select(Category).where(Category.name.like(f"%{q}%"))
                             .limit(5))).scalars().all()
    return _ok({"keywords": list(kw), "categories": [
        {"id": c.id, "name": c.name, "level": c.level} for c in cats]})


@router.get("/hot")
async def hot_words(db: AsyncSession = Depends(get_db)):
    # 开发环境返回内置热词
    return _ok({"keywords": ["iPhone", "iPad", "显示器", "冲锋衣", "耳机", "三体", "积木", "手环", "MacBook", "折叠屏"]})