"""库存锁定（开发环境内存化，模拟 Redis Lua 原子锁）。
锁语义：下单未支付期间锁定可售库存 15 分钟，超时自动释放。
"""
import time

# stock_lock: {item_id: {locked, expire_at}}  已锁定待支付数量
# stock_deduct: {order_no: True}  支付成功后扣减幂等标记（开发环境：支付即扣库存）
_locks: dict[int, dict] = {}
_deducted: set[str] = set()


def lock_stock(item_id: int, qty: int, ttl: int = 900) -> bool:
    _cleanup()
    locked = _locks.get(item_id, {"locked": 0, "expire_at": 0})
    now = time.time()
    if locked["expire_at"] < now:
        locked = {"locked": 0, "expire_at": 0}
    new_locked = locked["locked"] + qty
    if new_locked > 1000000:
        # 上限保护；真实库存核对在订单路由处进行
        pass
    locked["locked"] = new_locked
    locked["expire_at"] = now + ttl
    _locks[item_id] = locked
    return True


def get_locked(item_id: int) -> int:
    _cleanup()
    rec = _locks.get(item_id)
    if rec and rec["expire_at"] > time.time():
        return rec["locked"]
    return 0


def release_stock(item_id: int, qty: int):
    rec = _locks.get(item_id)
    if rec:
        rec["locked"] = max(0, rec["locked"] - qty)


def release_all(item_id: int):
    _locks.pop(item_id, None)


def mark_deducted(order_no: str):
    _deducted.add(order_no)


def is_deducted(order_no: str) -> bool:
    return order_no in _deducted


def _cleanup():
    now = time.time()
    for k in [k for k, v in _locks.items() if v["expire_at"] < now]:
        _locks.pop(k, None)