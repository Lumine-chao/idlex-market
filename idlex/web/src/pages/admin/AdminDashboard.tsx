import { useEffect, useState } from "react";
import { Row, Col, Card, Statistic, Alert, Button, Skeleton } from "antd";
import { UserOutlined, AppstoreOutlined, ShoppingCartOutlined, WalletOutlined, AuditOutlined, FlagOutlined } from "@ant-design/icons";
import { adminUserApi, DashboardData } from "../../api";

export default function AdminDashboard() {
  const [d, setD] = useState<DashboardData | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  function load() {
    setLoading(true);
    setError("");
    adminUserApi.dashboard()
      .then((r) => { if (r.code === 0) setD(r.data); else setError(r.message || "加载失败"); })
      .catch((e) => setError(e?.message || "加载失败，请稍后重试"))
      .finally(() => setLoading(false));
  }
  useEffect(load, []);

  if (loading) return <Skeleton active paragraph={{ rows: 6 }} />;
  if (error) return (
    <Alert
      type="error"
      showIcon
      message="数据看板加载失败"
      description={error}
      action={<Button size="small" onClick={load}>重新加载</Button>}
    />
  );
  if (!d) return <Alert type="warning" showIcon message="暂无数据" />;
  return (
    <div>
      <h2>数据看板</h2>
      <Row gutter={[16, 16]}>
        <Col xs={12} md={8}><Card><Statistic title="注册用户" value={d.users} prefix={<UserOutlined />} /></Card></Col>
        <Col xs={12} md={8}><Card><Statistic title="商品总量" value={d.items} prefix={<AppstoreOutlined />} /></Card></Col>
        <Col xs={12} md={8}><Card><Statistic title="在售商品" value={d.onSale} /></Card></Col>
        <Col xs={12} md={8}><Card><Statistic title="订单总量" value={d.orders} prefix={<ShoppingCartOutlined />} /></Card></Col>
        <Col xs={12} md={8}><Card><Statistic title="今日新增订单" value={d.todayOrders} /></Card></Col>
        <Col xs={12} md={8}><Card><Statistic title="成交金额(元)" value={d.amount} prefix={<WalletOutlined />} /></Card></Col>
        <Col xs={12} md={8}><Card><Statistic title="待审核商品" value={d.pendingAudit} prefix={<AuditOutlined />} valueStyle={{ color: d.pendingAudit ? "#faad14" : undefined }} /></Card></Col>
        <Col xs={12} md={8}><Card><Statistic title="待处理举报" value={d.pendingReport} prefix={<FlagOutlined />} valueStyle={{ color: d.pendingReport ? "#ff4d4f" : undefined }} /></Card></Col>
      </Row>
    </div>
  );
}