import { useEffect, useState } from "react";
import { Tabs, List, Tag, Button, Empty, Modal, Input, Rate, message, Space, Skeleton, Form, Alert, Checkbox, Pagination } from "antd";
import { ExclamationCircleOutlined } from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import { orderApi, reviewApi } from "../api";
import type { OrderItem } from "../types";
import { coverUrl, fallbackCover, formatPrice, timeAgo } from "../utils";
import { useAuth } from "../store/auth";

const STATUS_COLOR: Record<string, string> = {
  PENDING_PAYMENT: "orange", PAID: "blue", SHIPPED: "geekblue", COMPLETED: "green",
  CLOSED: "default", REFUNDING: "volcano", REFUNDED: "purple", DISPUTING: "red",
};

// 仅已结束的订单可删除记录，进行中的订单需先完成或取消
const DELETABLE = ["COMPLETED", "CLOSED", "REFUNDED"];

export default function Orders() {
  const nav = useNavigate();
  const auth = useAuth();
  const [tab, setTab] = useState("buy");
  const [buy, setBuy] = useState<OrderItem[]>([]);
  const [sell, setSell] = useState<OrderItem[]>([]);
  const [buyTotal, setBuyTotal] = useState(0);
  const [sellTotal, setSellTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [active, setActive] = useState<OrderItem | null>(null);
  const [shipOpen, setShipOpen] = useState(false);
  const [shipForm] = Form.useForm();
  const [refundOpen, setRefundOpen] = useState(false);
  const [refundForm] = Form.useForm();
  const [reviewing, setReviewing] = useState<OrderItem | null>(null);
  const [reviewForm] = Form.useForm();

  function load() {
    orderApi.list("buy", undefined, page).then((r) => {
      if (r.code === 0) { setBuy(r.data.list); setBuyTotal(r.data.total); }
    });
    orderApi.list("sell", undefined, page).then((r) => {
      if (r.code === 0) { setSell(r.data.list); setSellTotal(r.data.total); }
    });
    setLoading(false);
  }
  useEffect(() => { load(); }, [page]);

  function act(p: Promise<any>, okMsg = "操作成功") {
    p.then((r) => { if (r.code === 0) { message.success(r.message || okMsg); load(); } else message.error(r.message); });
  }

  function ship() {
    if (!active) return;
    shipForm.validateFields().then((v) => {
      act(orderApi.ship(active.orderNo, v.company, v.trackingNo), "发货成功");
      setShipOpen(false);
    });
  }
  function refund() {
    if (!active) return;
    refundForm.validateFields().then((v) => {
      act(orderApi.refund(active.orderNo, v.reason), "退款申请已提交");
      setRefundOpen(false);
    });
  }
  function review() {
    if (!reviewing) return;
    reviewForm.validateFields().then((v) => {
      const targetId = reviewing.sellerId === auth.user?.id ? reviewing.buyerId : reviewing.sellerId;
      const tags = Array.isArray(v.tags) ? v.tags.join(",") : v.tags;
      reviewApi.submit({ orderId: reviewing.orderId, targetId, score: v.score, content: v.content, tags })
        .then((r) => {
          if (r.code === 0) { message.success(r.message || "评价成功"); load(); }
          else message.error(r.message);
        })
        .catch((e) => message.error(e?.message));
      setReviewing(null);
    });
  }

  function remove(o: OrderItem) {
    Modal.confirm({
      title: "删除订单记录？",
      icon: <ExclamationCircleOutlined style={{ color: "#ff4d4f" }} />,
      width: 440,
      okText: "确认删除",
      okButtonProps: { danger: true },
      cancelText: "取消",
      content: (
        <div>
          <Alert
            type="warning"
            showIcon
            message="删除后无法恢复"
            description="该订单记录将从你的列表中永久移除，删除后无法找回，也无法再查看订单详情、物流与评价入口。"
            style={{ marginBottom: 12 }}
          />
          <div style={{ fontSize: 13, color: "#666" }}>
            订单号：{o.orderNo}
            <br />
            商品：{o.itemTitle}
            <br />
            金额：{formatPrice(o.totalAmount)}
          </div>
        </div>
      ),
      onOk: () => act(orderApi.remove(o.orderNo), "订单记录已删除，该记录无法恢复"),
    });
  }

  function actions(o: OrderItem) {
    const buy = o.buyerId === auth.user?.id;
    const el: any[] = [];
    if (o.status === "PENDING_PAYMENT" && buy) {
      el.push(<Button key="pay" type="primary" onClick={() => act(orderApi.pay(o.orderNo), "支付成功，资金已托管")}>去支付</Button>);
      el.push(<Button key="cancel" onClick={() => act(orderApi.cancel(o.orderNo))}>取消</Button>);
    }
    if (o.status === "PAID" && !buy) el.push(<Button key="ship" type="primary" onClick={() => { setActive(o); setShipOpen(true); }}>发货</Button>);
    if (o.status === "REFUNDING" && !buy) el.push(<Button key="agree" type="primary" onClick={() => act(orderApi.refundAgree(o.orderNo), "退款成功")}>同意退款</Button>);
    if (o.status === "SHIPPED" && buy) el.push(<Button key="cf" type="primary" onClick={() => act(orderApi.confirm(o.orderNo), "已确认收货")}>确认收货</Button>);
    if (["PAID", "SHIPPED"].includes(o.status) && buy) {
      el.push(<Button key="refund" onClick={() => { setActive(o); setRefundOpen(true); }}>申请退款</Button>);
      el.push(<Button key="dispute" onClick={() => act(orderApi.dispute(o.orderNo, "申请平台介入"))}>申请仲裁</Button>);
    }
    if (o.status === "COMPLETED") el.push(<Button key="review" onClick={() => setReviewing(o)}>点评</Button>);
    if (DELETABLE.includes(o.status)) {
      el.push(<Button key="del" danger onClick={() => remove(o)}>删除</Button>);
    }
    return el;
  }

  const list = tab === "buy" ? buy : sell;

  return (
    <div className="idlex-page" style={{ maxWidth: 900, margin: "0 auto" }}>
      <h2 style={{ marginBottom: 4 }}>我的订单</h2>
      <Tabs activeKey={tab} onChange={(k) => { setTab(k); setPage(1); }} items={[
        { key: "buy", label: `我买到的（${buyTotal}）` },
        { key: "sell", label: `我卖出的（${sellTotal}）` },
      ]} />
      {loading ? <Skeleton active /> : list.length === 0 ? <Empty description="暂无订单" /> :
        <List
          dataSource={list}
          renderItem={(o) => (
            <List.Item style={{ background: "#fff", borderRadius: 12, padding: 16, marginBottom: 12, boxShadow: "0 1px 4px rgba(0,0,0,0.05)" }}>
              <List.Item.Meta
                avatar={<img src={o.cover || coverUrl({ title: o.itemTitle }, "square")} alt="" width={72} height={72} style={{ borderRadius: 8, objectFit: "cover" }}
                  onError={(e) => fallbackCover(e.currentTarget, o.itemTitle, "square")} />}
                title={<Space><a onClick={() => nav(`/item/${o.itemId}`)}>{o.itemTitle}</a>
                  <Tag color={STATUS_COLOR[o.status]}>{o.statusText}</Tag></Space>}
                description={<>
                  <div>订单号：{o.orderNo}</div>
                  <div style={{ color: "#999", fontSize: 12 }}>{timeAgo(o.createdAt)}{o.trackingNo ? ` · ${o.logisticsCompany} ${o.trackingNo}` : ""}</div>
                </>}
              />
              <div style={{ textAlign: "right", minWidth: 180 }}>
                <div className="price" style={{ fontSize: 16 }}>{formatPrice(o.totalAmount)}</div>
                <div style={{ color: "#999", fontSize: 12, marginBottom: 8 }}>x{o.quantity}</div>
                <Space wrap>{actions(o)}</Space>
              </div>
            </List.Item>
          )}
        />}

      {(tab === "buy" ? buyTotal : sellTotal) > 20 && (
        <div style={{ textAlign: "right", marginTop: 12 }}>
          <Pagination current={page} pageSize={20} total={tab === "buy" ? buyTotal : sellTotal}
            showSizeChanger={false} onChange={(p) => setPage(p)} />
        </div>
      )}

      <Modal title="卖家发货" open={shipOpen} onCancel={() => setShipOpen(false)} onOk={ship} okText="确认发货">
        <Form form={shipForm} layout="vertical">
          <Form.Item name="company" label="物流公司" rules={[{ required: true }]}>
            <Input placeholder="如：顺丰速运" />
          </Form.Item>
          <Form.Item name="trackingNo" label="运单号" rules={[{ required: true }]}>
            <Input placeholder="填写快递单号" />
          </Form.Item>
        </Form>
      </Modal>

      <Modal title="申请退款" open={refundOpen} onCancel={() => setRefundOpen(false)} onOk={refund} okText="提交申请">
        <Form form={refundForm} layout="vertical">
          <Form.Item name="reason" label="退款原因" rules={[{ required: true }]}>
            <Input.TextArea rows={3} placeholder="说明退款原因，卖家将尽快处理" maxLength={200} />
          </Form.Item>
        </Form>
      </Modal>

      <Modal title="评价本次交易" open={!!reviewing} onCancel={() => setReviewing(null)} onOk={review} okText="提交评价">
        <Form form={reviewForm} layout="vertical" initialValues={{ score: 5 }}>
          <Form.Item name="score" label="评分" rules={[{ required: true }]}>
            <Rate />
          </Form.Item>
          <Form.Item name="tags" label="贴标">
            <Checkbox.Group options={["很及时", "描述相符", "包装严实", "沟通顺畅", "有瑕疵缺描述"]} />
          </Form.Item>
          <Form.Item name="content" label="评价内容">
            <Input.TextArea rows={3} maxLength={500} placeholder="说说这次交易体验" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}