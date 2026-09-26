"""账号认证：注册、双令牌登录/刷新/登出、密保找回密码"""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..db import get_db
from .. import auth, errors
from ..models import User
from ..schemas import (RegisterReq, LoginReq, RefreshReq, ResetPasswordReq)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.get("/security-questions")
async def security_questions():
    return {"code": 0, "message": "ok", "data": {"questions": auth.get_security_questions()}}


@router.post("/register")
async def register(req: RegisterReq, db: AsyncSession = Depends(get_db)):
    auth.validate_username(req.username)
    auth.validate_password(req.password, req.username)
    auth.validate_question_answer(req.security_question, req.security_answer)
    exists = (await db.execute(select(User).where(User.username == req.username))).scalar_one_or_none()
    if exists:
        raise errors.error(errors.ErrorCodes.USERNAME_REGISTERED, "username.registered")
    user = User(username=req.username, password_hash=auth.hash_password(req.password),
                security_question=req.security_question,
                security_answer=auth.hash_security_answer(req.security_answer),
                status=1, credit_level=1)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    access, refresh = auth.issue_tokens("user", user.id)
    return {"code": 0, "message": "注册成功", "data": {
        "accessToken": access, "refreshToken": refresh, "expiresIn": 7200, "userId": user.id}}


@router.post("/login")
async def login(req: LoginReq, db: AsyncSession = Depends(get_db)):
    account = req.username.strip()
    auth.validate_username(account)
    lock = auth.is_locked(account)
    if lock:
        remain = lock["remainSeconds"]
        raise errors.BizError(errors.ErrorCodes.ACCOUNT_LOCKED,
                              errors.MSG["login.locked"].format(minutes=max(1, remain // 60)),
                              data={"remainSeconds": remain})
    user = (await db.execute(select(User).where(User.username == account))).scalar_one_or_none()
    if not user or auth.verify_password(user.password_hash, req.password) is not True:
        # 账号枚举防护：不区分用户名是否注册；未注册按同样失败计数提示
        if not user:
            raise errors.error(errors.ErrorCodes.LOGIN_FAILED, "login.failed",
                               data={"failCount": 0, "remainTimes": 5})
        data = auth.record_login_fail(account)
        raise errors.error(errors.ErrorCodes.LOGIN_FAILED, "login.failed", data=data)
    # 封禁登录（status=2）：放在密码校验之后，避免向非本人泄露账号状态
    if user.status == 2:
        raise errors.error(errors.ErrorCodes.ACCOUNT_BANNED, "account.banned")
    auth.clear_login_fail(account)
    user.last_login_at = datetime.now(timezone.utc)
    await db.commit()
    access, refresh = auth.issue_tokens("user", user.id)
    return {"code": 0, "message": "登录成功", "data": {"accessToken": access,
            "refreshToken": refresh, "expiresIn": 7200, "userId": user.id}}


@router.post("/token/refresh")
async def refresh(req: RefreshReq):
    access, refresh_token = auth.refresh_access(req.refreshToken)
    return {"code": 0, "message": "ok", "data": {"accessToken": access,
            "refreshToken": refresh_token, "expiresIn": 7200}}


@router.post("/logout")
async def logout(req: RefreshReq):
    auth.revoke_refresh(req.refreshToken)
    return {"code": 0, "message": "已退出登录"}


@router.post("/password/reset")
async def password_reset(req: ResetPasswordReq, db: AsyncSession = Depends(get_db)):
    account = req.username.strip()
    auth.validate_username(account)
    auth.validate_question_answer(req.security_question, req.security_answer)
    auth.validate_password(req.new_password, account)
    user = (await db.execute(select(User).where(User.username == account))).scalar_one_or_none()
    if not user or not user.security_answer:
        raise errors.BizError(errors.ErrorCodes.LOGIN_FAILED, errors.MSG["login.failed"])
    if user.security_question != req.security_question:
        raise errors.error(errors.ErrorCodes.SECURITY_WRONG, "security.wrong")
    if not auth.verify_security_answer(user.security_answer, req.security_answer):
        raise errors.error(errors.ErrorCodes.SECURITY_WRONG, "security.wrong")
    if auth.verify_password(user.password_hash, req.new_password):
        raise errors.error(errors.ErrorCodes.PASSWORD_RESET_SAME, "reset.same")
    user.password_hash = auth.hash_password(req.new_password)
    auth.clear_login_fail(account)
    await db.commit()
    return {"code": 0, "message": "密码重置成功，请重新登录"}