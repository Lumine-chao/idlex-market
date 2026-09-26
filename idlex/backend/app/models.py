"""ORM 模型（对齐架构文档中的数据实体，消息在开发环境落 SQLite 而非 MongoDB）"""
from datetime import datetime, timezone
from sqlalchemy import (BigInteger, String, Text, Integer, SmallInteger,
                        Numeric, Boolean, DateTime, ForeignKey, JSON, UniqueConstraint)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .db import Base


def utcnow():
    return datetime.now(timezone.utc)


def ensure_utc(dt: datetime | None) -> datetime | None:
    """SQLite 读回的时间不带时区，统一补齐为 UTC，避免与 aware 时间相减报错。"""
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    phone: Mapped[str | None] = mapped_column(String(11), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    security_question: Mapped[str | None] = mapped_column(String(128))
    security_answer: Mapped[str | None] = mapped_column(String(255))
    avatar: Mapped[str | None] = mapped_column(String(255))
    gender: Mapped[str | None] = mapped_column(String(10))
    city: Mapped[str | None] = mapped_column(String(32))
    bio: Mapped[str | None] = mapped_column(String(255))
    credit_level: Mapped[int] = mapped_column(SmallInteger, default=3)
    status: Mapped[int] = mapped_column(SmallInteger, default=1)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    fail_count: Mapped[int] = mapped_column(Integer, default=0)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Address(Base):
    __tablename__ = "user_addresses"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
    receiver: Mapped[str] = mapped_column(String(32), nullable=False)
    phone: Mapped[str] = mapped_column(String(11), nullable=False)
    province: Mapped[str] = mapped_column(String(32), nullable=False)
    city: Mapped[str] = mapped_column(String(32), nullable=False)
    district: Mapped[str] = mapped_column(String(32), nullable=False)
    detail: Mapped[str] = mapped_column(String(255), nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Category(Base):
    __tablename__ = "categories"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(32), nullable=False)
    parent_id: Mapped[int | None] = mapped_column(BigInteger, default=None)
    level: Mapped[int] = mapped_column(SmallInteger, default=1)
    sort: Mapped[int] = mapped_column(Integer, default=0)


class Item(Base):
    __tablename__ = "items"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    seller_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("categories.id"), nullable=False)
    condition_level: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    origin_price: Mapped[float | None] = mapped_column(Numeric(10, 2))
    stock: Mapped[int] = mapped_column(Integer, default=1)
    city: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    trade_type: Mapped[int] = mapped_column(SmallInteger, default=1)
    freight_payer: Mapped[int] = mapped_column(SmallInteger, default=1)
    freight: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    status: Mapped[int] = mapped_column(SmallInteger, default=3)
    view_count: Mapped[int] = mapped_column(Integer, default=0)
    extra: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    images = relationship("ItemImage", order_by="ItemImage.sort", lazy="selectin")
    seller = relationship("User", lazy="joined")


class ItemImage(Base):
    __tablename__ = "item_images"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    item_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("items.id"), nullable=False)
    url: Mapped[str] = mapped_column(String(255), nullable=False)
    sort: Mapped[int] = mapped_column(Integer, default=0)
    audit_status: Mapped[int] = mapped_column(SmallInteger, default=2)  # 开发环境默认通过


class Favorite(Base):
    __tablename__ = "favorites"
    __table_args__ = (UniqueConstraint("user_id", "item_id", name="uk_favorites_user_item"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    item_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Footprint(Base):
    __tablename__ = "footprints"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    item_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Conversation(Base):
    __tablename__ = "conversations"
    __table_args__ = (UniqueConstraint("buyer_id", "item_id", name="uk_conv_buyer_item"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    item_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("items.id"), nullable=False)
    buyer_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    seller_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_message: Mapped[str | None] = mapped_column(String(500))
    # 双方各自的已读时间：用于计算会话未读数（进入会话即回执已读）
    buyer_read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    seller_read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Message(Base):
    __tablename__ = "messages"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    conversation_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("conversations.id"), index=True, nullable=False)
    sender_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    msg_type: Mapped[str] = mapped_column(String(16), default="TEXT")
    content: Mapped[str] = mapped_column(Text, nullable=False)
    seq: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Order(Base):
    __tablename__ = "orders"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_no: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    buyer_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    seller_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    item_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    item_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    unit_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    freight: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    total_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    address_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="PENDING_PAYMENT")
    pay_channel: Mapped[str | None] = mapped_column(String(24))
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    logistics_company: Mapped[str | None] = mapped_column(String(64))
    tracking_no: Mapped[str | None] = mapped_column(String(64))
    shipped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    version: Mapped[int] = mapped_column(Integer, default=0)
    # 管理员干预记录
    intervened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    intervene_action: Mapped[str | None] = mapped_column(String(24))
    intervene_reason: Mapped[str | None] = mapped_column(String(255))
    # 用户侧删除标记：买卖双方各自独立，一方删除不影响另一方查看
    buyer_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    seller_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class OrderStatusLog(Base):
    __tablename__ = "order_status_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(BigInteger, index=True, nullable=False)
    from_status: Mapped[str | None] = mapped_column(String(24))
    to_status: Mapped[str] = mapped_column(String(24), nullable=False)
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    operator_type: Mapped[str] = mapped_column(String(16), nullable=False)
    operator_id: Mapped[int | None] = mapped_column(BigInteger)
    operate_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    remark: Mapped[str | None] = mapped_column(String(255))


class Review(Base):
    __tablename__ = "reviews"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    reviewer_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    target_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    score: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    tags: Mapped[str | None] = mapped_column(String(255))
    content: Mapped[str | None] = mapped_column(String(500))
    is_modified: Mapped[bool] = mapped_column(Boolean, default=False)
    hidden: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Report(Base):
    __tablename__ = "reports"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    reporter_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    target_type: Mapped[str] = mapped_column(String(16), nullable=False)
    target_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    reason_type: Mapped[str] = mapped_column(String(32), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500))
    evidence: Mapped[str | None] = mapped_column(Text)
    status: Mapped[int] = mapped_column(SmallInteger, default=0)  # 0待受理1处理中2已处理
    result: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AdminUser(Base):
    __tablename__ = "admin_users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(16), default="ADMIN")
    status: Mapped[int] = mapped_column(SmallInteger, default=1)


class SensitiveWord(Base):
    __tablename__ = "sensitive_words"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    word: Mapped[str] = mapped_column(String(64), nullable=False)
    level: Mapped[str] = mapped_column(String(16), default="BLOCK")  # BLOCK拦截 / REPLACE替换
    status: Mapped[int] = mapped_column(SmallInteger, default=1)     # 1启用 0停用