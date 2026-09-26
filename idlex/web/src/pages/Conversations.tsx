import { useEffect, useState } from "react";
import { List, Avatar, Badge, Empty, Skeleton } from "antd";
import { MessageOutlined } from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import { imApi } from "../api";
import type { Conversation } from "../types";
import { coverUrl, timeAgo } from "../utils";
import { useAuth } from "../store/auth";

export default function Conversations() {
  const nav = useNavigate();
  const auth = useAuth();
  const [list, setList] = useState<Conversation[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    load();
    const timer = setInterval(load, 10000);
    return () => clearInterval(timer);
  }, []);

  function load() {
    imApi.conversations().then((r) => {
      if (r.code === 0) setList(r.data.list);
    }).finally(() => setLoading(false));
  }

  return (
    <div className="idlex-page" style={{ maxWidth: 760, margin: "0 auto" }}>
      <h2 style={{ marginBottom: 16 }}>消息中心</h2>
      <div style={{ background: "#fff", borderRadius: 12, boxShadow: "0 1px 6px rgba(0,0,0,0.05)", overflow: "hidden" }}>
        {loading ? <Skeleton active style={{ padding: 20 }} />
          : list.length === 0 ? <Empty description="暂无会话，去商品页发起聊天吧" style={{ padding: 40 }} />
            : list.map((c) => {
              const otherId = c.other?.id;
              return (
                <div key={c.conversationId} className="chat-list-item" style={{ display: "flex", alignItems: "center", gap: 12, padding: 14, cursor: "pointer" }}
                  onClick={() => nav(`/conversations/${c.conversationId}`)}>
                  <Badge count={c.unreadCount} size="small">
                    <Avatar size={46} src={c.other?.avatar || undefined} icon={<MessageOutlined />} />
                  </Badge>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ display: "flex", justifyContent: "space-between" }}>
                      <strong>{c.other?.username}</strong>
                      <span style={{ color: "#bbb", fontSize: 12 }}>{timeAgo(c.lastMessageAt)}</span>
                    </div>
                    <div style={{ color: "#999", fontSize: 13, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                      {c.lastMessage || "（商品：" + c.itemTitle + "）"}
                    </div>
                  </div>
                  <div style={{ color: "#999", fontSize: 12, maxWidth: 160, textAlign: "right" }}>{c.itemTitle}</div>
                </div>
              );
            })}
      </div>
    </div>
  );
}