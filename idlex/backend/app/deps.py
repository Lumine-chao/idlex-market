"""FastAPI 依赖注入：请求体校验、当前用户/管理员解析、限流（开发环境内存化）"""
import time
from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from .db import get_db
from .auth import decode_token
from . import errors
from .models import User, AdminUser

_rate: dict = {}  # key -> [window_start, count]


def enforce_rate_limit(key: str, limit: int, window: int = 60):
    now = time.time()
    rec = _rate.get(key)
    if not rec or now - rec[0] >= window:
        _rate[key] = [now, 1]
        return
    if rec[1] >= limit:
        raise errors.BizError(errors.ErrorCodes.RATE_LIMITED, errors.MSG["message.frequent"],
                              http_status=429)
    rec[1] += 1


def rate_limit(limit: int, window: int = 60):
    return limit, window


async def load_user(db: AsyncSession, user_id: int) -> User:
    result = await db.get(User, user_id)
    if not result or result.deleted_at is not None:
        raise errors.error(errors.ErrorCodes.UNAUTHORIZED, "unauthorized",
                           http_status=401)
    if result.status == 2:  # 封禁登录
        raise errors.error(errors.ErrorCodes.UNAUTHORIZED, "unauthorized", http_status=403)
    return result


def ensure_can_publish(user: User) -> None:
    """禁止发布（status=3）：不可新建商品，也不可把已下架商品重新上架"""
    if user.status == 3:
        raise errors.error(errors.ErrorCodes.PUBLISH_BANNED, "publish.banned")


async def get_current_user_async(
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise errors.BizError(errors.ErrorCodes.UNAUTHORIZED, errors.MSG["unauthorized"],
                              http_status=401)
    token = authorization[7:]
    payload = decode_token(token, "access")
    if payload.get("ut") != "user":
        raise errors.BizError(errors.ErrorCodes.UNAUTHORIZED, errors.MSG["unauthorized"],
                              http_status=401)
    return await load_user(db, payload["sub"])


async def get_current_admin(
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> AdminUser:
    if not authorization or not authorization.startswith("Bearer "):
        raise errors.BizError(errors.ErrorCodes.UNAUTHORIZED, errors.MSG["unauthorized"],
                              http_status=401)
    token = authorization[7:]
    try:
        payload = decode_token(token, "access")
    except errors.BizError:
        raise
    if payload.get("ut") != "admin":
        raise errors.BizError(errors.ErrorCodes.FORBIDDEN, errors.MSG["forbidden"],
                              http_status=403)
    admin = await db.get(AdminUser, payload["sub"])
    if not admin or admin.status != 1:
        raise errors.BizError(errors.ErrorCodes.FORBIDDEN, errors.MSG["forbidden"],
                              http_status=403)
    return admin