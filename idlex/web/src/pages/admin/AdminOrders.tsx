import { useEffect, useState } from "react";
import { Table, Button, Tag, Select, Modal, Form, Input, message, Tooltip, Alert, Space, Popconfirm } from "antd";
import type { ColumnsType } from "antd/es/table";
import { adminUserApi } from "../../api";
import type { OrderItem } from "../../types";
import { ORDER_STATUS_TEXT } from "../../types";
import { formatPrice, timeAgo } from "../../utils";

const STATUS_COLOR: Record<string, string> = { PENDING_PAYMENT: "orange", PAID: "blue", SHIPPED: "geekblue", COMPLETED: "green", CLOSED: "default", REFUNDING: "volcano", REFUNDED: "purple", DISPUTING: "red" };

const ACTIONS = [
  { value: "close", label: "强制关闭" },
  { value: "refund", label: "强制退款" },
  { value: "to_ship", label: "强制发货" },
  { value: "to_shipped", label: "强制确认收货" },
];

const ACTION_TEXT: Record<string, string> = Object.fromEntries(
  ACTIONS.map((a) => [a.value, a.label]));

// 各状态下可执行的干预动作（与后端状态机保持一致）
const ACTIONS_BY_STATUS: Record<string, string[]> = {
  PENDING_PAYMENT: ["close"],
  REFUNDING: ["refund"],
  DISPUTING: ["refund", "to_ship", "to_shipped"],
};

// 订单已处理完（终态）后才允许删除记录（与后端保持一致）
const TERMINAL_STATUSES = ["COMPLETED", "CLOSED", "REFUNDED"];

function canDelete(r: OrderItem) {
  return !!r.intervenedAt || TERMINAL_STATUSES.includes(r.status);
}

export default function AdminOrders() {
  const [data, setData] = useState<OrderItem[]>([]);
  const [status, setStatus] = useState<string>("ALL");
  const [target, setTarget] = useState<OrderItem | null>(null);
  const [error, setError] = useState("");
  const [form] = Form.useForm();

  function load() {
    setError("");
    adminUserApi.orders(status === "ALL" ? undefined : status)
      .then((r) => { if (r.code === 0) setData(r.data.list); else setError(r.message || "加载失败"); })
      .catch((e) => setError(e?.message || "加载失败，请稍后重试"));
  }
  useEffect(load, [status]);

  function run() {
    if (!target) return;
    form.validateFields().then((v) => {
      adminUserApi.intervene(target.orderNo, v.action, v.reason).then((r) => {
        if (r.code === 0) { message.success(r.message); setTarget(null); form.resetFields(); load(); } else message.error(r.message);
      });
    });
  }

  function remove(orderNo: string) {
    adminUserApi.deleteOrder(orderNo).then((r) => {
      if (r.code === 0) { message.success(r.message); load(); } else message.error(r.message);
    });
  }

  const columns: ColumnsType<OrderItem> = [
    { title: "订单号", dataIndex: "orderNo" },
    { title: "商品", dataIndex: "itemTitle" },
    { title: "金额", dataIndex: "totalAmount", render: (v) => formatPrice(v) },
    { title: "买家ID", dataIndex: "buyerId", width: 80 },
    { title: "卖家ID", dataIndex: "sellerId", width: 80 },
    { title: "状态", dataIndex: "status", render: (v) => <Tag color={STATUS_COLOR[v]}>{ORDER_STATUS_TEXT[v as keyof typeof ORDER_STATUS_TEXT] || v}</Tag> },
    { title: "下单时间", dataIndex: "createdAt", render: (v) => timeAgo(v) },
    { title: "操作", render: (_, r) => {
      const nodes = [];
      if (r.intervenedAt) {
        nodes.push(
          <Tooltip key="iv" title={`已于 ${timeAgo(r.intervenedAt)} 干预：${ACTION_TEXT[r.interveneAction || ""] || r.interveneAction}${r.interveneReason ? `（${r.interveneReason}）` : ""}`}>
            <Tag color="default">已干预</Tag>
          </Tooltip>
        );
      } else {
        const usable = ACTIONS_BY_STATUS[r.status] || [];
        nodes.push(usable.length
          ? <Button key="iv" size="small" type="primary" ghost onClick={() => { setTarget(r); form.resetFields(); }}>干预</Button>
          : (
            <Tooltip key="iv" title="该状态下没有可执行的干预动作">
              <Button size="small" type="primary" ghost disabled>干预</Button>
            </Tooltip>
          ));
      }
      if (canDelete(r)) {
        nodes.push(
          <Popconfirm key="del" title="删除该订单记录？" description="删除后无法恢复，关联的流转日志与评价会一并清除，且不再计入后台统计。"
            okText="删除" okButtonProps={{ danger: true }} cancelText="取消" onConfirm={() => remove(r.orderNo)}>
            <Button size="small" danger>删除</Button>
          </Popconfirm>
        );
      }
      return <Space size={8}>{nodes}</Space>;
    } },
  ];

  return (
    <div>
      {error && <Alert type="error" showIcon message="订单列表加载失败" description={error}
        action={<Button size="small" onClick={load}>重新加载</Button>} style={{ marginBottom: 12 }} />}
      <Select style={{ width: 200, marginBottom: 16 }}
        value={status} onChange={setStatus}
        options={[{ value: "ALL", label: "全部" },
          ...Object.entries(ORDER_STATUS_TEXT).map(([value, label]) => ({ value, label }))]} />
      <Table rowKey="orderNo" columns={columns} dataSource={data}
        locale={{ emptyText: error ? "加载失败" : "暂无订单" }} />
      <Modal title={`干预订单：${target?.orderNo || ""}`} open={!!target} onCancel={() => setTarget(null)} onOk={run} okText="执行干预">
        <Form form={form} layout="vertical">
          <Form.Item name="action" label="干预动作" rules={[{ required: true }]}>
            <Select options={ACTIONS.filter((a) => (ACTIONS_BY_STATUS[target?.status || ""] || []).includes(a.value))} />
          </Form.Item>
          <Form.Item name="reason" label="干预原因（必填）" rules={[{ required: true, message: "请填写原因" }]}>
            <Input />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}