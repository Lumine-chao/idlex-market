import { useEffect, useState } from "react";
import { Table, Button, Tag, Input, Modal, message, Space, Alert, Select } from "antd";
import type { ColumnsType } from "antd/es/table";
import { adminUserApi } from "../../api";
import type { Item } from "../../types";
import { coverUrl, formatPrice } from "../../utils";
import { ITEM_STATUS_TEXT } from "../../types";

export default function AdminItems() {
  const [data, setData] = useState<Item[]>([]);
  const [kw, setKw] = useState("");
  const [status, setStatus] = useState<number | undefined>(undefined);
  const [auditTarget, setAuditTarget] = useState<Item | null>(null);
  const [reason, setReason] = useState("");
  const [error, setError] = useState("");

  function load() {
    setError("");
    adminUserApi.items({ keyword: kw || undefined, status })
      .then((r) => { if (r.code === 0) setData(r.data.list); else setError(r.message || "加载失败"); })
      .catch((e) => setError(e?.message || "加载失败，请稍后重试"));
  }
  useEffect(() => { load(); /* eslint-disable-next-line */ }, [status]);

  function audit(approve: boolean) {
    if (!auditTarget) return;
    if (!approve && !reason.trim()) return message.warning("驳回需填写原因");
    adminUserApi.audit(auditTarget.itemId, approve, reason).then((r) => {
      if (r.code === 0) { message.success(r.message); setAuditTarget(null); setReason(""); load(); } else message.error(r.message);
    });
  }

  const columns: ColumnsType<Item> = [
    { title: "商品", dataIndex: "title", render: (_, r) => (
      <Space>
        <img
          src={coverUrl(r, "square")}
          alt=""
          width={44}
          height={44}
          style={{ borderRadius: 6, objectFit: "cover", background: "#f5f5f5" }}
          onError={(e) => { const el = e.target as HTMLImageElement; el.onerror = null; el.src = coverUrl({ title: r.title }, "square"); }}
        />
        <span>{r.title}</span>
      </Space>) },
    { title: "卖家", render: (_, r) => r.seller?.username },
    { title: "价格", dataIndex: "price", render: (v) => formatPrice(v) },
    { title: "城市", dataIndex: "city" },
    { title: "状态", dataIndex: "status", render: (v) => { const c = v === 3 ? "green" : v === 2 ? "orange" : v === 6 ? "red" : v === 4 ? "default" : undefined; return <Tag color={c}>{ITEM_STATUS_TEXT[v] || v}</Tag>; } },
    { title: "操作", render: (_, r) => (
      <Space key={r.itemId}>
        <Button size="small" onClick={() => { setAuditTarget(r); setReason(""); }} disabled={r.status === 3 || r.status === 5 || r.status === 6}>审核</Button>
        {r.status === 3 && <Button size="small" type="primary" onClick={() => adminUserApi.audit(r.itemId, true, "重新通过").then(() => { message.success("已设置通过"); load(); })}>通过</Button>}
        {r.status === 3 && <Button size="small" danger onClick={() => adminUserApi.audit(r.itemId, false, "管理员下架").then(() => { message.success("已下架/驳回"); load(); })}>驳回下架</Button>}
      </Space>) },
  ];

  return (
    <div>
      {error && <Alert type="error" showIcon message="商品列表加载失败" description={error}
        action={<Button size="small" onClick={load}>重新加载</Button>} style={{ marginBottom: 12 }} />}
      <Space style={{ marginBottom: 16 }}>
        <Input.Search placeholder="按标题搜索" value={kw} onChange={(e) => setKw(e.target.value)} onSearch={() => load()} style={{ width: 240 }} />
        <Select style={{ width: 160 }} value={status === undefined ? "ALL" : status}
          onChange={(v) => setStatus(v === "ALL" ? undefined : (v as number))}
          options={[{ value: "ALL", label: "全部" },
            ...Object.entries(ITEM_STATUS_TEXT).map(([value, label]) => ({ value: Number(value), label }))]} />
      </Space>
      <Table rowKey="itemId" columns={columns} dataSource={data}
        locale={{ emptyText: error ? "加载失败" : "暂无商品" }} />
      <Modal title={`审核商品：${auditTarget?.title || ""}`} open={!!auditTarget} onCancel={() => setAuditTarget(null)}
        footer={[
          <Button key="reject" danger onClick={() => audit(false)}>驳回</Button>,
          <Button key="ok" type="primary" onClick={() => audit(true)}>审核通过</Button>,
        ]}>
        {auditTarget && <div>
          <div style={{ color: "#666", marginBottom: 8 }}>{auditTarget.description}</div>
          <Tag>{auditTarget.conditionText}</Tag>
        </div>}
        <Input.TextArea rows={2} placeholder="处置原因（驳回必填）" value={reason} onChange={(e) => setReason(e.target.value)} style={{ marginTop: 12 }} />
      </Modal>
    </div>
  );
}