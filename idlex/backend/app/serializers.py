"""实体 -> 响应 JSON 转换"""
from .state_machine import STATUS_MEANING
from .models import Item, User, Order, Conversation

CONDITION_TEXT = {1: "全新", 2: "几乎全新", 3: "轻微使用痕迹", 4: "明显使用痕迹"}


def user_summary(u: User) -> dict:
    return {
        "id": u.id, "username": u.username, "avatar": u.avatar, "city": u.city,
        "creditLevel": u.credit_level,
    }


def item_brief(it) -> dict:
    cover = it.images[0].url if it.images and it.images[0].url else None
    return {
        "itemId": it.id, "title": it.title, "description": it.description,
        "categoryId": it.category_id, "conditionLevel": it.condition_level,
        "conditionText": CONDITION_TEXT.get(it.condition_level, ""),
        "price": float(it.price), "originPrice": float(it.origin_price) if it.origin_price else None,
        "stock": it.stock, "city": it.city, "tradeType": it.trade_type,
        "freightPayer": it.freight_payer, "freight": float(it.freight),
        "status": it.status, "viewCount": it.view_count,
        "coverUrl": cover, "images": [im.url for im in it.images][:9],
        "seller": user_summary(it.seller) if getattr(it, "seller", None) else None,
        "createdAt": it.created_at.isoformat() if it.created_at else None,
        "isLate": False,
    }


def order_brief(o: Order, snapshot_from_item: Item | None = None) -> dict:
    snap = o.item_snapshot or {}
    return {
        "orderNo": o.order_no, "orderId": o.id, "buyerId": o.buyer_id, "sellerId": o.seller_id,
        "itemId": o.item_id, "itemTitle": snap.get("title", ""),
        "cover": snap.get("cover", ""), "unitPrice": float(o.unit_price),
        "quantity": o.quantity, "freight": float(o.freight),
        "totalAmount": float(o.total_amount), "status": o.status,
        "statusText": STATUS_MEANING.get(o.status, o.status),
        "logisticsCompany": o.logistics_company, "trackingNo": o.tracking_no,
        "createdAt": o.created_at.isoformat() if o.created_at else None,
        "paidAt": o.paid_at.isoformat() if o.paid_at else None,
        "shippedAt": o.shipped_at.isoformat() if o.shipped_at else None,
    }