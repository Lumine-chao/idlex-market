"""订单状态机：统一驱动状态流转，禁止非法跳转，每次流转写入留痕记录"""
from . import errors
from .models import OrderStatusLog
from .db import AsyncSession
from .models import Order

# 状态与允许的动作 / 目标状态
TRANSITIONS = {
    "PENDING_PAYMENT": {
        "pay": "PAID",
        "cancel": "CLOSED",
        "timeout_close": "CLOSED",
        "admin_close": "CLOSED",
    },
    "PAID": {
        "ship": "SHIPPED",
        "refund": "REFUNDING",
        "dispute": "DISPUTING",
    },
    "SHIPPED": {
        "confirm": "COMPLETED",
        "auto_confirm": "COMPLETED",
        "refund": "REFUNDING",
        "dispute": "DISPUTING",
    },
    "REFUNDING": {
        "seller_agree_refund": "REFUNDED",
        "auto_refund": "REFUNDED",
        "dispute": "DISPUTING",
        "admin_refund": "REFUNDED",
        "admin_reject": "PAID",
    },
    "DISPUTING": {
        "admin_refund": "REFUNDED",
        "admin_to_ship": "PAID",
        "admin_to_shipped": "SHIPPED",
    },
    "COMPLETED": {},
    "CLOSED": {},
    "REFUNDED": {},
}

# 交易尚未终结的订单状态：这些状态下的订单会阻塞商品删除
ACTIVE_ORDER_STATUSES = {"PENDING_PAYMENT", "PAID", "SHIPPED", "REFUNDING", "DISPUTING"}

STATUS_MEANING = {
    "PENDING_PAYMENT": "待付款",
    "PAID": "待发货",
    "SHIPPED": "已发货",
    "COMPLETED": "已完成",
    "CLOSED": "已关闭",
    "REFUNDING": "退款中",
    "REFUNDED": "已退款",
    "DISPUTING": "争议中",
}


def allowed_next(current: str, action: str) -> str | None:
    return TRANSITIONS.get(current, {}).get(action)


async def transition(db: AsyncSession, order: Order, action: str, operator_type: str,
                     operator_id: int | None, remark: str | None = None) -> str:
    """执行一次状态流转；非法直接拒绝。返回新状态。"""
    to_status = allowed_next(order.status, action)
    if not to_status:
        raise errors.error(errors.ErrorCodes.ORDER_STATE_FORBIDDEN, "order.state",
                           http_status=200)
    from_status = order.status
    order.status = to_status
    order.version += 1
    log = OrderStatusLog(
        order_id=order.id, from_status=from_status, to_status=to_status,
        action=action.upper(), operator_type=operator_type, operator_id=operator_id,
        remark=remark)
    db.add(log)
    await db.flush()
    return to_status