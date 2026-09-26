"""沟通与消息：会话、消息收发、未读、撤回、历史分页、WebSocket 长连接"""
from __future__ import annotations
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from ..db import get_db, SessionLocal
from .. import errors, sensitive, auth as auth_mod
from ..deps import get_current_user_async
from ..models import User, Item, Conversation, Message, ensure_utc
from ..serializers import user_summary
from ..ws import manager
from ..auth import decode_token

router = APIRouter(prefix="/api/v1", tags=["im"])


def _ok(data=None, message="ok"):
    return {"code": 0, "message": message, "data": data}


def _msg_out(m: Message, sender: User | None = None) -> dict:
    return {
        "id": m.id, "conversationId": m.conversation_id, "senderId": m.sender_id,
        "msgType": m.msg_type, "content": m.content, "seq": m.seq,
        "createdAt": m.created_at.isoformat() if m.created_at else None,
        "revoked": m.revoked_at is not None,
        "sender": user_summary(sender) if sender else None,
    }


async def _unread_for_conv(db: AsyncSession, conv_id: int, reader_id: int) -> int:
    conv = await db.get(Conversation, conv_id)
    if not conv:
        return 0
    other = conv.seller_id if conv.buyer_id == reader_id else conv.buyer_id
    cond = [Message.conversation_id == conv_id, Message.sender_id == other,
            Message.revoked_at.is_(None)]
    # 仅统计该用户上次进入会话之后收到的消息
    read_at = ensure_utc(conv.buyer_read_at if conv.buyer_id == reader_id
                         else conv.seller_read_at)
    if read_at:
        cond.append(Message.created_at > read_at)
    return (await db.execute(select(func.count()).select_from(Message).where(*cond))).scalar() or 0


async def push_unread_total(user_id: int):
    async with SessionLocal() as db:
        convos = (await db.execute(select(Conversation).where(
            (Conversation.buyer_id == user_id) | (Conversation.seller_id == user_id))
        )).scalars().all()
        total = 0
        for c in convos:
            total += await _unread_for_conv(db, c.id, user_id)
    await manager.send_to_user(user_id, {"type": "UNREAD_TOTAL", "payload": {"total": total}})


@router.post("/conversations")
async def create_conversation(data: dict, user: User = Depends(get_current_user_async),
                              db: AsyncSession = Depends(get_db)):
    item_id = data.get("itemId")
    if not item_id:
        raise errors.error(errors.ErrorCodes.ITEM_NOT_FOUND, "item.not.found")
    it = (await db.execute(select(Item).where(Item.id == item_id,
                                              Item.deleted_at.is_(None)))).scalar_one_or_none()
    if not it:
        raise errors.error(errors.ErrorCodes.ITEM_NOT_FOUND, "item.not.found")
    conv = (await db.execute(select(Conversation).where(
        Conversation.buyer_id == user.id, Conversation.item_id == item_id))
    ).scalar_one_or_none()
    if not conv:
        conv = Conversation(item_id=item_id, buyer_id=user.id, seller_id=it.seller_id)
        db.add(conv)
        await db.commit()
        await db.refresh(conv)
    return _ok({"conversationId": conv.id, "itemId": item_id, "sellerId": it.seller_id})


@router.get("/conversations")
async def list_conversations(user: User = Depends(get_current_user_async),
                             db: AsyncSession = Depends(get_db)):
    convos = (await db.execute(
        select(Conversation).where((Conversation.buyer_id == user.id) |
                                   (Conversation.seller_id == user.id))
        .order_by(Conversation.last_message_at.desc().nullslast())
    )).scalars().all()
    result = []
    for c in convos:
        other_id = c.seller_id if c.buyer_id == user.id else c.buyer_id
        other = await db.get(User, other_id)
        it = await db.get(Item, c.item_id)
        unread = await _unread_for_conv(db, c.id, user.id)
        result.append({
            "conversationId": c.id, "itemId": c.item_id,
            "itemTitle": it.title if it else "",
            "cover": (it.images[0].url if it and it.images else ""),
            "other": user_summary(other) if other else None,
            "lastMessage": c.last_message,
            "lastMessageAt": c.last_message_at.isoformat() if c.last_message_at else None,
            "unreadCount": unread,
        })
    return _ok({"list": result, "total": len(result)})


@router.get("/conversations/{conv_id}/messages")
async def history(conv_id: int, page: int = 1, size: int = 30,
                  user: User = Depends(get_current_user_async),
                  db: AsyncSession = Depends(get_db)):
    conv = await db.get(Conversation, conv_id)
    if not conv or (conv.buyer_id != user.id and conv.seller_id != user.id):
        raise errors.error(errors.ErrorCodes.CONVERSATION_NOT_FOUND, "conversation.not.found")
    rows = (await db.execute(
        select(Message).where(Message.conversation_id == conv_id)
        .order_by(Message.created_at.desc()).offset((page - 1) * size).limit(size)
    )).scalars().all()
    rows = list(rows)[::-1]
    total = (await db.execute(select(func.count()).select_from(Message)
                              .where(Message.conversation_id == conv_id))).scalar() or 0
    # 进入会话即回执已读：刷新未读计数
    if conv.buyer_id == user.id:
        conv.buyer_read_at = datetime.now(timezone.utc)
    else:
        conv.seller_read_at = datetime.now(timezone.utc)
    await db.commit()
    await push_unread_total(user.id)
    return _ok({"list": [_msg_out(m) for m in rows], "page": page, "size": size,
                "total": total})


@router.post("/messages")
async def send_message(data: dict, user: User = Depends(get_current_user_async),
                       db: AsyncSession = Depends(get_db)):
    conv_id = data.get("conversationId")
    content = str(data.get("content") or "").strip()
    msg_type = data.get("msgType") or "TEXT"
    if len(content) > 2000:
        raise errors.error(errors.ErrorCodes.MESSAGE_TOO_LONG, "message.long")
    if msg_type == "TEXT" and sensitive.check_sensitive(content):
        raise errors.error(errors.ErrorCodes.MESSAGE_SENSITIVE, "message.sensitive")
    conv = await db.get(Conversation, conv_id)
    if not conv or (conv.buyer_id != user.id and conv.seller_id != user.id):
        raise errors.error(errors.ErrorCodes.CONVERSATION_NOT_FOUND, "conversation.not.found")
    msg = await _do_store(db, conv, user.id, content, msg_type)
    other_id = conv.seller_id if conv.buyer_id == user.id else conv.buyer_id
    await _push_message(conv_id, msg, other_id)
    return _ok(_msg_out(msg), "发送成功")


async def _do_store(db, conv, sender_id, content, msg_type):
    seq = (await db.execute(select(func.coalesce(func.max(Message.seq), 0))
                            .where(Message.conversation_id == conv.id))).scalar() + 1
    msg = Message(conversation_id=conv.id, sender_id=sender_id, content=content,
                  msg_type=msg_type, seq=seq)
    db.add(msg)
    conv.last_message = content[:200]
    conv.last_message_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(msg)
    return msg


async def _push_message(conv_id, msg, other_id):
    envelope = {"type": "MESSAGE_PUSH", "payload": {
        "messageId": str(msg.id), "conversationId": conv_id, "senderId": msg.sender_id,
        "msgType": msg.msg_type, "content": msg.content, "seq": msg.seq}}
    await manager.send_to_user(other_id, envelope)
    await push_unread_total(other_id)


@router.post("/messages/{message_id}/recall")
async def recall(message_id: int, user: User = Depends(get_current_user_async),
                 db: AsyncSession = Depends(get_db)):
    msg = await db.get(Message, message_id)
    if not msg or msg.sender_id != user.id or msg.revoked_at is not None:
        raise errors.error(errors.ErrorCodes.MESSAGE_RECALL_EXPIRED, "message.recall.expired")
    if datetime.now(timezone.utc) - ensure_utc(msg.created_at) > timedelta(minutes=2):
        raise errors.error(errors.ErrorCodes.MESSAGE_RECALL_EXPIRED, "message.recall.expired")
    msg.revoked_at = datetime.now(timezone.utc)
    msg.content = ""
    await db.commit()
    return _ok({"messageId": message_id}, "已撤回")


@router.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    token = ws.query_params.get("token", "")
    try:
        payload = decode_token(token, "access")
        user_id = payload["sub"]
    except Exception:
        await ws.close(code=4401)
        return
    await manager.connect(user_id, ws)
    try:
        while True:
            data = await ws.receive_json()
            mtype = data.get("type")
            if mtype == "PING":
                await ws.send_json({"type": "PONG"})
            elif mtype == "MESSAGE_SEND":
                payload = data.get("payload", {})
                conv_id = payload.get("conversationId")
                content = str(payload.get("content") or "")
                async with SessionLocal() as db:
                    conv = await db.get(Conversation, conv_id)
                    if not conv or (conv.buyer_id != user_id and conv.seller_id != user_id):
                        await ws.send_json({"type": "ERROR", "code": 4101,
                                            "message": errors.MSG["conversation.not.found"]})
                        continue
                    if len(content) > 2000:
                        await ws.send_json({"type": "ERROR", "code": 4001,
                                            "message": errors.MSG["message.long"]})
                        continue
                    if sensitive.check_sensitive(content):
                        await ws.send_json({"type": "ERROR", "code": 4002,
                                            "message": errors.MSG["message.sensitive"]})
                        continue
                    msg = await _do_store(db, conv, user_id, content, "TEXT")
                    await _push_message(conv_id, msg,
                                        conv.seller_id if conv.buyer_id == user_id else conv.buyer_id)
                    await ws.send_json({"type": "MESSAGE_ACK", "status": "SENT",
                                        "message": _msg_out(msg)})
    except WebSocketDisconnect:
        manager.disconnect(user_id, ws)
    except Exception:
        manager.disconnect(user_id, ws)