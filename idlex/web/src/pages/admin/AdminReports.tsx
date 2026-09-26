import { useEffect, useState } from "react";
import { Table, Button, Tag, Modal, Input, message, Space, Alert, Skeleton } from "antd";
import type { ColumnsType } from "antd/es/table";
import { adminUserApi, AdminReportRow } from "../../api";
import { timeAgo } from "../../utils";

const TYPE_TEXT: Record<string, string> = { item: "商品", user: "用户", message: "消息" };

export default function AdminReports() {
  const [data, setData] = useState<AdminReportRow[]>([]);
  const [target, setTarget] = useState<AdminReportRow | null>(null);
  const [reason, setReason] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  function load() {
    setLoading(true);
    setError("");
    adminUserApi.reports({})
      .then((r) => { if (r.code === 0) setData(r.data.list); else setError(r.message || "加载失败"); })
      .catch((e) => setError(e?.message || "加载失败，请稍后重试"))
      .finally(() => setLoading(false));
  }
  useEffect(load, []);

  function handle(approve: boolean) {
    if (!target) return;
    if (!reason.trim()) return message.warning("请填写处理备注");
    adminUserApi.handleReport(target.id, approve, reason).then((r) => {
      if (r.code === 0) { message.success(r.message); setTarget(null); setReason(""); load(); } else message.error(r.message);
    }).catch((e) => message.error(e?.message || "处理失败"));
  }

  const columns: ColumnsType<AdminReportRow> = [
    { title: "ID", dataIndex: "id", width: 60 },
    { title: "对象", dataIndex: "targetType",
      render: (v, r) => <Tag>{TYPE_TEXT[v] || v} #{r.targetId}</Tag> },
    { title: "原因", dataIndex: "reasonType" },
    { title: "说明", dataIndex: "description", ellipsis: true },
    { title: "状态", dataIndex: "status", render: (v) => v === 0 ? <Tag color="orange">待处理</Tag> : <Tag color="green">已处理</Tag> },
    { title: "时间", dataIndex: "createdAt", render: (v) => timeAgo(v) },
    { title: "操作", render: (_, r) => (
      <Button size="small" type="primary" ghost disabled={r.status !== 0} onClick={() => { setTarget(r); setReason(""); }}>处理</Button>) },
  ];

  if (loading) return <Skeleton active paragraph={{ rows: 5 }} />;
  if (error) return (
    <Alert type="error" showIcon message="举报列表加载失败" description={error}
      action={<Button size="small" onClick={load}>重新加载</Button>} />
  );

  return (
    <div>
      <Table rowKey="id" columns={columns} dataSource={data}
        locale={{ emptyText: "暂无举报记录" }} />
      <Modal title="处理举报" open={!!target} onCancel={() => setTarget(null)}
        footer={[
          <Button key="reject" onClick={() => handle(false)}>举报不成立</Button>,
          <Button key="ok" type="primary" danger onClick={() => handle(true)}>举报成立（下架/禁发）</Button>,
        ]}>
        {target && <div style={{ marginBottom: 12, color: "#666" }}>
          {TYPE_TEXT[target.targetType] || target.targetType} #{target.targetId} · {target.reasonType}：{target.description}
        </div>}
        <Input.TextArea rows={2} placeholder="处理备注" value={reason} onChange={(e) => setReason(e.target.value)} />
      </Modal>
    </div>
  );
}