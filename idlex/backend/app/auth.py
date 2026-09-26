"""双令牌签发/校验、密码散列、登录失败锁定（开发环境令牌与规则内存化）"""
import re
import time
import secrets
from datetime import datetime, timezone, timedelta
import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from .config import settings
from . import errors

_hasher = PasswordHasher()

# 开发环境内存态：刷新令牌记录、验证码、失败锁定（映射为 Redis 键名）
_tokens: dict[str, dict] = {}          # refresh jti -> {user_type, id, exp}
_codes: dict[str, dict] = {}           # phone -> {code, exp, last_sent, day_count}
_login_fail: dict[str, dict] = {}      # phone -> {count, locked_until}


# ---------------- 密码 ----------------
def hash_password(raw: str) -> str:
    return _hasher.hash(raw)


def verify_password(hash_: str, raw: str) -> bool:
    try:
        return _hasher.verify(hash_, raw)
    except VerifyMismatchError:
        return False
    except Exception:
        return False


# ---------------- 校验规则 ----------------
_PHONE_RE = re.compile(r"^1[3-9]\d{9}$")
_USERNAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]{2,31}$")

# 注册时可选用的密保问题
SECURITY_QUESTIONS = [
    "您的出生城市是？",
    "您的小学名称是？",
    "您的班主任姓什么？",
    "您最爱的食物是？",
    "您第一只宠物的名字？",
]


def get_security_questions() -> list[str]:
    return list(SECURITY_QUESTIONS)


def validate_phone(phone: str):
    if not _PHONE_RE.match(phone):
        raise errors.error(errors.ErrorCodes.PHONE_INVALID, "phone.invalid")


def validate_username(username: str):
    if not _USERNAME_RE.match(username):
        raise errors.error(errors.ErrorCodes.USERNAME_INVALID, "username.invalid")


def validate_question_answer(question: str, answer: str):
    if question not in SECURITY_QUESTIONS or not answer or len(answer.strip()) < 2 or len(answer.strip()) > 50:
        raise errors.error(errors.ErrorCodes.SECURITY_INVALID, "security.invalid")


def validate_password(password: str, username: str):
    if not (8 <= len(password) <= 20) or not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
        raise errors.error(errors.ErrorCodes.PASSWORD_FORMAT_INVALID, "password.format")
    if password == username:
        raise errors.error(errors.ErrorCodes.PASSWORD_EQUALS_PHONE, "password.equals.account")
    # 连续或重复字符
    if re.search(r"(.)\1{3,}", password):
        raise errors.error(errors.ErrorCodes.PASSWORD_WEAK_SEQUENCE, "password.weak")
    ascending = "0123456789abcdefghijklmnopqrstuvwxyz"
    low = password.lower()
    for i in range(len(low) - 3):
        seg = low[i:i + 4]
        if seg in ascending or seg in ascending[::-1]:
            raise errors.error(errors.ErrorCodes.PASSWORD_WEAK_SEQUENCE, "password.weak")


def hash_security_answer(answer: str) -> str:
    return hash_password(answer.strip())


def verify_security_answer(hashed: str | None, answer: str) -> bool:
    if not hashed:
        return False
    return verify_password(hashed, answer.strip())


# ---------------- 验证码（开发模式） ----------------
def issue_sms_code(phone: str):
    now = time.time()
    rec = _codes.get(phone, {})
    if rec and now - rec.get("last_sent", 0) < 60:
        raise errors.error(errors.ErrorCodes.SMS_TOO_FREQUENT, "sms.too.frequent")
    day = rec.get("day_count", 0)
    if day >= 10:
        raise errors.error(errors.ErrorCodes.SMS_DAY_LIMIT, "message.frequent")
    code = str(secrets.randbelow(1000000)).zfill(6)
    _codes[phone] = {"code": code, "exp": now + 300, "last_sent": now, "day_count": day + 1}
    return code


def check_sms_code(phone: str, code: str):
    rec = _codes.get(phone)
    if not rec or rec["code"] != code or time.time() > rec["exp"]:
        raise errors.error(errors.ErrorCodes.SMS_CODE_INVALID, "sms.code.invalid")
    _codes.pop(phone, None)


# ---------------- 令牌 ----------------
def _issue(user_type: str, subject_id: int) -> tuple[str, str]:
    now = time.time()
    jti = secrets.token_hex(8)
    access = jwt.encode(
        {"sub": str(subject_id), "ut": user_type, "typ": "access", "jti": jti, "iat": int(now),
         "exp": int(now + settings.access_token_expire)},
        settings.secret_key, algorithm=settings.jwt_algorithm)
    refresh_jti = secrets.token_hex(8)
    refresh = jwt.encode(
        {"sub": str(subject_id), "ut": user_type, "typ": "refresh", "jti": refresh_jti, "iat": int(now),
         "exp": int(now + settings.refresh_token_expire)},
        settings.secret_key, algorithm=settings.jwt_algorithm)
    _tokens[refresh_jti] = {"ut": user_type, "id": subject_id, "exp": now + settings.refresh_token_expire}
    return access, refresh


def issue_tokens(user_type: str, subject_id: int):
    return _issue(user_type, subject_id)


def revoke_refresh(refresh_token: str):
    try:
        payload = jwt.decode(refresh_token, settings.secret_key, algorithms=[settings.jwt_algorithm])
        _tokens.pop(payload.get("jti"), None)
    except Exception:
        return


def decode_token(token: str, expected_type: str = "access"):
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
    except jwt.ExpiredSignatureError:
        raise errors.BizError(errors.ErrorCodes.UNAUTHORIZED, errors.MSG["unauthorized"],
                              http_status=401)
    except Exception:
        raise errors.BizError(errors.ErrorCodes.UNAUTHORIZED, errors.MSG["unauthorized"],
                              http_status=401)
    if payload.get("typ") != expected_type:
        raise errors.BizError(errors.ErrorCodes.UNAUTHORIZED, errors.MSG["unauthorized"],
                              http_status=401)
    payload["sub"] = int(payload["sub"])
    return payload


def refresh_access(refresh_token: str):
    payload = decode_token(refresh_token, "refresh")
    jti = payload.get("jti")
    rec = _tokens.get(jti)
    if not rec or rec["ut"] != "user" or time.time() > rec["exp"]:
        raise errors.BizError(errors.ErrorCodes.UNAUTHORIZED, errors.MSG["unauthorized"],
                              http_status=401)
    access, refresh = issue_tokens("user", rec["id"])
    return access, refresh


# ---------------- 用户失败锁定（按账号标识，用户名/手机号均可） ----------------
def record_login_fail(account: str) -> dict:
    now = time.time()
    rec = _login_fail.get(account, {"count": 0, "locked_until": None})
    if rec["locked_until"] and now < rec["locked_until"]:
        remain = int(rec["locked_until"] - now)
        raise errors.error(errors.ErrorCodes.ACCOUNT_LOCKED, "login.locked",
                           minutes=max(1, remain // 60), data={"remainSeconds": remain})
    rec["count"] += 1
    data = {"failCount": rec["count"], "remainTimes": max(0, 5 - rec["count"])}
    if rec["count"] >= 5:
        rec["locked_until"] = now + 1800
        rec["count"] = 0
        remain = 1800
        raise errors.error(errors.ErrorCodes.ACCOUNT_LOCKED, "login.locked", minutes=30,
                           data={"remainSeconds": remain})
    _login_fail[account] = rec
    return data


def clear_login_fail(account: str):
    _login_fail.pop(account, None)


def is_locked(account: str) -> dict | None:
    rec = _login_fail.get(account)
    now = time.time()
    if rec and rec["locked_until"] and now < rec["locked_until"]:
        remain = int(rec["locked_until"] - now)
        return {"remainSeconds": remain}
    return None