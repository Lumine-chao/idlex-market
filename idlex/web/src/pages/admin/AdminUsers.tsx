import { useEffect, useState } from "react";
import { Table, Button, Tag, Input, Modal, Form, Select, message, Alert } from "antd";
import type { ColumnsType } from "antd/es/table";
import { adminUserApi, AdminUserRow } from "../../api";

const STATUS_TEXT: Record<number, string> = { 1: "正常", 2: "封禁登录", 3: "禁发布" };

export default function AdminUsers() {
  const [data, setData] = useState<AdminUserRow[]>([]);
  const [kw, setKw] = useState("");
  const [target, setTarget] = useState<AdminUserRow | null>(null);
  const [form] = Form.useForm();
  const [error, setError] = useState("");

  function load() {
    setError("");
    adminUserApi.users(kw || undefined)
      .then((r) => { if (r.code === 0) setData(r.data.list); else setError(r.message || "加载失败"); })
      .catch((e) => setError(e?.message || "加载失败，请稍后重试"));
  }
  useEffect(load, []);

  function act() {
    if (!target) return;
    form.validateFields().then((v) => {
      adminUserApi.userAction(target.id, v.action, v.reason).then((r) => {
        if (r.code === 0) { message.success(r.message); setTarget(null); form.resetFields(); load(); } else message.error(r.message);
      });
    });
  }

  const columns: ColumnsType<AdminUserRow> = [
    { title: "ID", dataIndex: "id", width: 60 },
    { title: "用户名", dataIndex: "username" },
    { title: "城市", dataIndex: "city" },
    { title: "信用", dataIndex: "creditLevel" },
    { title: "状态", dataIndex: "status", render: (v) => { const c = v === 2 ? "red" : v === 3 ? "orange" : "green"; return <Tag color={c}>{STATUS_TEXT[v] || v}</Tag>; } },
    {
      title: "操作",
      render: (_: unknown, r: AdminUserRow) => (
        <Button size="small" type="primary" ghost onClick={() => handleDispose(r)}>处置</Button>
      ),
    },
  ];

  function handleDispose(r: AdminUserRow) {
    setTarget(r);
    form.resetFields();
  }

  return (
    <div>
      {error && <Alert type="error" showIcon message="用户列表加载失败" description={error}
        action={<Button size="small" onClick={load}>重新加载</Button>} style={{ marginBottom: 12 }} />}
      <Input.Search placeholder="按用户名搜索" value={kw} onChange={(e) => setKw(e.target.value)} onSearch={load} style={{ width: 240, marginBottom: 16 }} />
      <Table rowKey="id" columns={columns} dataSource={data}
        locale={{ emptyText: error ? "加载失败" : "暂无用户" }} />
      <Modal title={`处置用户：${target?.username || ""}`} open={!!target} onCancel={() => setTarget(null)} onOk={act} okText="执行处置">
        {target && <div style={{ marginBottom: 12 }}>用户名 {target.username}，当前状态：{STATUS_TEXT[target.status]}</div>}
        <Form form={form} layout="vertical">
          <Form.Item name="action" label="处置动作" rules={[{ required: true }]}>
            <Select options={[
              { value: "ban", label: "封禁登录" },
              { value: "unban", label: "解除封禁" },
              { value: "ban_publish", label: "禁止发布" },
              { value: "unpublish_ban", label: "恢复发布" },
            ]} />
          </Form.Item>
          <Form.Item name="reason" label="处置原因（必填）" rules={[{ required: true, message: "请填写处置原因" }]}>
            <Input.TextArea rows={2} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}