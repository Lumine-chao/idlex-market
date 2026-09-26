"""Pydantic 请求/响应模型"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List


def _to_camel(s: str) -> str:
    parts = s.split("_")
    return parts[0] + "".join(p.title() for p in parts[1:])


class CamelModel(BaseModel):
    # 同时接受 snake_case 与 camelCase，贴合文档中的接口示例
    model_config = ConfigDict(alias_generator=_to_camel, populate_by_name=True)


# ---------- 账号 ----------
class SmsCodeReq(CamelModel):
    phone: str


class RegisterReq(CamelModel):
    username: str
    password: str
    security_question: str
    security_answer: str


class LoginReq(CamelModel):
    username: str
    password: str


class SmsLoginReq(CamelModel):
    phone: str
    smsCode: str


class RefreshReq(CamelModel):
    refreshToken: str


class ResetPasswordReq(CamelModel):
    username: str
    security_question: str
    security_answer: str
    new_password: str


class ProfileUpdateReq(CamelModel):
    avatar: Optional[str] = None
    gender: Optional[str] = None
    city: Optional[str] = None
    bio: Optional[str] = None


class AddressReq(CamelModel):
    receiver: str
    phone: str
    province: str
    city: str
    district: str
    detail: str
    is_default: bool = False


# ---------- 商品 ----------
class ItemCreateReq(CamelModel):
    title: str
    description: str
    category_id: int
    condition_level: int
    price: float
    origin_price: Optional[float] = None
    stock: int = 1
    city: str = ""
    trade_type: int = 1
    freight_payer: int = 1
    freight: float = 0
    images: List[str] = Field(default_factory=list)
    extra: Optional[dict] = None


class ItemStatusReq(CamelModel):
    action: str  # on_sale / off_sale / delete


# ---------- 搜索 ----------
class SearchReq(CamelModel):
    q: Optional[str] = ""
    category_id: Optional[int] = None
    condition: Optional[str] = None  # "2,3"
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    city: Optional[str] = None
    trade_type: Optional[int] = None
    free_shipping: Optional[bool] = None
    sort: str = "relevance"  # relevance / price_asc / price_desc / newest
    page: int = 1
    size: int = 20


# ---------- 会话 / 消息 ----------
class ConversationCreateReq(CamelModel):
    item_id: int


class MessageSendReq(CamelModel):
    conversation_id: int
    msg_type: str = "TEXT"
    content: str


# ---------- 订单 ----------
class OrderCreateReq(CamelModel):
    item_id: int
    quantity: int = 1
    address_id: int
    priceCardId: Optional[int] = None
    price: Optional[float] = None  # 议价改价后的成交价


class PayReq(CamelModel):
    channel: str = "MOCK"


class ShipReq(CamelModel):
    logisticsCompany: str
    trackingNo: str


class RefundReq(CamelModel):
    reason: str
    return_tracking_no: Optional[str] = None


class DisputeReq(CamelModel):
    reason: str


# ---------- 评价 / 举报 ----------
class ReviewReq(CamelModel):
    order_id: int
    target_id: int
    score: int
    tags: Optional[str] = None
    content: Optional[str] = None


class ReportReq(CamelModel):
    target_type: str  # item / user / message
    target_id: int
    reason_type: str
    description: Optional[str] = None
    evidence: Optional[List[str]] = None


# ---------- 管理端 ----------
class AuditReq(CamelModel):
    approve: bool
    reason: Optional[str] = None


class UserActionReq(CamelModel):
    action: str  # ban / unban / ban_publish / unpublish_ban
    reason: str


class OrderInterveneReq(CamelModel):
    action: str  # close / refund / to_ship / to_shipped
    reason: str


class ReportHandleReq(CamelModel):
    approve: bool
    reason: str


class SensitiveWordReq(CamelModel):
    word: str
    level: str = "BLOCK"
    status: int = 1