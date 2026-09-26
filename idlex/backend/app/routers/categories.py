"""分类服务：分类树"""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..db import get_db
from ..models import Category

router = APIRouter(prefix="/api/v1/categories", tags=["categories"])


@router.get("", name="categories")
async def categories(db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(Category).order_by(Category.sort))).scalars().all()
    tree = []
    l1 = {c.id: c for c in rows if c.level == 1}
    l2 = [c for c in rows if c.level == 2]
    l3 = [c for c in rows if c.level == 3]
    for c1 in sorted(l1.values(), key=lambda x: x.sort):
        node = {"value": c1.id, "label": c1.name, "children": []}
        for c2 in [x for x in l2 if x.parent_id == c1.id]:
            c2node = {"value": c2.id, "label": c2.name, "children": []}
            for c3 in [x for x in l3 if x.parent_id == c2.id]:
                c2node["children"].append({"value": c3.id, "label": c3.name})
            if c2node["children"]:
                node["children"].append(c2node)
            else:
                node["children"].append(c2node)
        tree.append(node)
    return {"code": 0, "message": "ok", "data": tree}


@router.get("/plain")
async def categories_plain(db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(Category).order_by(Category.sort))).scalars().all()
    return {"code": 0, "message": "ok", "data": [
        {"id": c.id, "name": c.name, "parentId": c.parent_id, "level": c.level} for c in rows]}