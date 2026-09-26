import { useEffect, useRef, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Input, Button, Card, Popconfirm, message, Space } from "antd";
import { ArrowLeftOutlined, SendOutlined, UndoOutlined } from "@ant-design/icons";
import { imApi } from "../api";
import type { ChatMessage } from "../types";
import { useAuth } from "../store/auth";

const WS_BASE = (import.meta.env.VITE_WS_BASE as string) || "ws://127.0.0.1:8000";

export default function Chat() {
  const { id } = useParams();
  const nav = useNavigate();
  const auth = useAuth();
  const [msgs, setMsgs] = useState<ChatMessage[]>([]);
  const [text, setText] = useState("");
  const [otherName, setOtherName] = useState("");
  const [otherAvatar, setOtherAvatar] = useState<string | undefined>();
  const endRef = useRef<HTMLDivElement>(null);
  const wsRef = useRef<WebSocket | null>(null);

  function scrollToEnd() { setTimeout(() => endRef.current?.scrollIntoView({ behavior: "smooth" }), 50); }

  useEffect(() => {
    loadHistory();
    // WebSocket 实时推送
    const token = localStorage.getItem("idlex_access");
    if (token) {
      try {
        const ws = new WebSocket(`${WS_BASE}/api/v1/ws?token=${encodeURIComponent(token)}`);
        wsRef.current = ws;
        ws.onmessage = (e) => {
          const data = JSON.parse(e.data);
          if (data.type === "MESSAGE_PUSH" && Number(data.payload.conversationId) === Number(id)) {
            setMsgs((p) => [...p, data.payload].filter((m, i, arr) => arr.findIndex((x) => x.seq === m.seq && x.conversationId === m.conversationId) === i));
            scrollToEnd();
          }
        };
        return () => ws.close();
      } catch { /* ws 可选 */ }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  useEffect(() => {
    imApi.conversations().then((r) => {
      if (r.code === 0) {
        const c = r.data.list.find((x) => x.conversationId === Number(id));
        if (c) { setOtherName(c.other?.username || "对方"); setOtherAvatar(c.other?.avatar || undefined); }
      }
    });
  }, [id]);

  function loadHistory() {
    imApi.history(Number(id)).then((r) => {
      if (r.code === 0) setMsgs(r.data.list);
      scrollToEnd();
    });
  }

  function send() {
    const content = text.trim();
    if (!content) return;
    setText("");
    imApi.send(Number(id), content).then((r) => {
      if (r.code === 0) { setMsgs((p) => [...p, r.data].filter((m, i, arr) => arr.findIndex((x) => x.seq === m.seq) === i)); scrollToEnd(); }
      else { message.error(r.message); setText(content); }
    });
  }

  function recall(m: ChatMessage) {
    imApi.recall(m.id).then((r) => {
      if (r.code === 0) { message.success("已撤回"); loadHistory(); }
      else message.error(r.message);
    });
  }

  return (
    <div className="idlex-page" style={{ maxWidth: 760, margin: "0 auto", display: "flex", flexDirection: "column", height: "calc(100vh - 160px)" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 12, background: "#fff", borderBottom: "1px solid #eee", padding: "10px 16px", borderRadius: "12px 12px 0 0" }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => nav(-1)} type="text" />
        <strong>{otherName}</strong>
      </div>
      <Card style={{ flex: 1, overflowY: "auto", borderRadius: 0, borderTop: "none" }} bodyStyle={{ display: "flex", flexDirection: "column", gap: 10 }} id="chat-scroll">
        {msgs.map((m) => {
          const own = m.senderId === auth.user?.id;
          return (
            <div key={`${m.conversationId}-${m.seq}-${m.id}`} style={{ display: "flex", justifyContent: own ? "flex-end" : "flex-start" }}>
              {!own && <img src={otherAvatar || ""} alt="" width={32} height={32} style={{ borderRadius: "50%", marginRight: 8, background: "#eee" }} />}
              <Popconfirm title="确认撤回该消息？" onConfirm={() => recall(m)} okText="撤回" cancelText="取消" disabled={!own || m.revoked}>
                <div style={{ maxWidth: 320, padding: "8px 12px", borderRadius: 10, fontSize: 14, boxShadow: "0 1px 2px rgba(0,0,0,0.06)",
                  ...(own ? { background: "#ff8a00", color: "#fff", borderTopRightRadius: 2 } : { background: "#fff", border: "1px solid #eee", borderTopLeftRadius: 2 }) }}>
                  {m.revoked ? <span style={{ color: "#bbb" }}>该消息已撤回</span> : m.content}
                </div>
              </Popconfirm>
            </div>
          );
        })}
        <div ref={endRef} />
      </Card>
      <div style={{ display: "flex", gap: 10, background: "#fff", padding: 12, borderRadius: "0 0 12px 12px", borderTop: "1px solid #eee" }}>
        <Input.TextArea
          autoSize={{ minRows: 1, maxRows: 4 }}
          placeholder="请文明聊天，违规内容会被系统拦截"
          value={text}
          onChange={(e) => setText(e.target.value)}
          onPressEnter={(e) => { if (!e.shiftKey) { e.preventDefault(); send(); } }}
        />
        <Button type="primary" icon={<SendOutlined />} onClick={send}>发送</Button>
      </div>
    </div>
  );
}