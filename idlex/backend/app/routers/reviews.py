"""评价：买卖互评、评分标签、恶意评价申诉"""
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from ..db import get_db
from .. import errors
from ..deps import get_current_user_async
from ..models import User, Order, Review, ensure_utc
from ..schemas import ReviewReq

router = APIRouter(prefix="/api/v1/reviews", tags=["reviews"])


def _ok(data=None, message="ok"):
    return {"code": 0, "message": message, "data": data}


def _review_out(r: Review) -> dict:
    return {
        "id": r.id, "orderId": r.order_id, "reviewerId": r.reviewer_id,
        "targetId": r.target_id, "score": r.score, "tags": r.tags, "content": r.content,
        "isModified": r.is_modified,
        "createdAt": r.created_at.isoformat() if r.created_at else None,
    }


@router.post("", name="submit_review")
async def submit_review(req: ReviewReq, user: User = Depends(get_current_user_async),
                        db: AsyncSession = Depends(get_db)):
    if not (1 <= req.score <= 5):
        raise errors.error(errors.ErrorCodes.REVIEW_WINDOW_CLOSED, "review.window")
    o = await db.get(Order, req.order_id)
    if not o or (o.buyer_id != user.id and o.seller_id != user.id):
        raise errors.error(errors.ErrorCodes.ORDER_NOT_FOUND, "order.not.found")
    if o.status != "COMPLETED":
        raise errors.error(errors.ErrorCodes.REVIEW_WINDOW_CLOSED, "review.window")
    # 30 天窗口
    finished = ensure_utc(o.finished_at)
    if not finished or datetime.now(timezone.utc) - finished > timedelta(days=30):
        raise errors.error(errors.ErrorCodes.REVIEW_WINDOW_CLOSED, "review.window")
    existing = (await db.execute(select(Review).where(
        Review.order_id == o.id, Review.reviewer_id == user.id))).scalar_one_or_none()
    if existing:
        if existing.is_modified:
            raise errors.error(errors.ErrorCodes.REVIEW_EDIT_LIMIT, "review.edit")
        existing.score = req.score
        existing.tags = req.tags
        existing.content = req.content
        existing.is_modified = True
        await db.commit()
        return _ok(_review_out(existing), "评价已修改")
    r = Review(order_id=o.id, reviewer_id=user.id, target_id=req.target_id,
               score=req.score, tags=req.tags, content=req.content)
    db.add(r)
    await db.commit()
    return _ok(_review_out(r), "评价成功")


@router.get("", name="list_reviews")
async def list_reviews(targetId: int | None = None, itemId: int | None = None,
                       rating: str = "all", db: AsyncSession = Depends(get_db)):
    """按被评价人（卖家主页）或商品（商品详情页）查询评价列表。"""
    cond = [Review.hidden.is_(False)]
    if itemId:
        # 商品页：该商品下所有订单产生的评价
        cond.append(Review.order_id.in_(select(Order.id).where(Order.item_id == itemId)))
    elif targetId:
        cond.append(Review.target_id == targetId)
    else:
        return _ok({"list": [], "avgScore": 0, "count": 0})
    if rating in ("good", "mid", "bad"):
        if rating == "good":
            cond.append(Review.score >= 4)
        elif rating == "mid":
            cond.append(Review.score == 3)
        else:
            cond.append(Review.score <= 2)
    rows = (await db.execute(select(Review).where(*cond)
                             .order_by(Review.created_at.desc()).limit(100))).scalars().all()
    reviews = []
    for r in rows:
        reviewer = await db.get(User, r.reviewer_id)
        d = _review_out(r)
        d["reviewerName"] = reviewer.username if reviewer else ""
        d["reviewerAvatar"] = reviewer.avatar if reviewer else None
        reviews.append(d)
    agg = (await db.execute(select(
        func.avg(Review.score), func.count(Review.id)
    ).where(*cond))).one()
    return _ok({"list": reviews, "avgScore": round(float(agg[0] or 0), 1), "count": agg[1] or 0})