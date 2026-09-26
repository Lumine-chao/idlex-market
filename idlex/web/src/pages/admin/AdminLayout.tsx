import { Layout, Menu, Button, Space } from "antd";
import { DashboardOutlined, AppstoreOutlined, TeamOutlined, ShoppingCartOutlined, FlagOutlined, LogoutOutlined } from "@ant-design/icons";
import { Outlet, useNavigate, useLocation } from "react-router-dom";

const { Sider, Header, Content } = Layout;

const MENU = [
  { key: "/admin/dashboard", icon: <DashboardOutlined />, label: "数据看板" },
  { key: "/admin/items", icon: <AppstoreOutlined />, label: "商品审核" },
  { key: "/admin/users", icon: <TeamOutlined />, label: "用户管理" },
  { key: "/admin/orders", icon: <ShoppingCartOutlined />, label: "订单干预" },
  { key: "/admin/reports", icon: <FlagOutlined />, label: "举报处理" },
];

export default function AdminLayout() {
  const nav = useNavigate();
  const loc = useLocation();
  return (
    <Layout style={{ minHeight: "100vh" }}>
      <Sider theme="dark" width={200}>
        <div style={{ color: "#fff", fontWeight: 800, fontSize: 17, padding: "18px 16px", background: "#1f2a3d" }}>
          闲置易 · 后台
        </div>
        <Menu theme="dark" mode="inline" selectedKeys={[loc.pathname]} items={MENU}
          onClick={(e) => nav(e.key)} />
      </Sider>
      <Layout>
        <Header style={{ background: "#fff", display: "flex", justifyContent: "flex-end", alignItems: "center", paddingRight: 24 }}>
          <Space>
            <span style={{ color: "#999" }}>管理员</span>
            <Button icon={<LogoutOutlined />} onClick={() => {
              localStorage.removeItem("idlex_admin_access");
              localStorage.removeItem("idlex_admin_refresh");
              nav("/admin/login");
            }}>退出</Button>
          </Space>
        </Header>
        <Content style={{ margin: 16, background: "#fff", borderRadius: 12, padding: 20 }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
}