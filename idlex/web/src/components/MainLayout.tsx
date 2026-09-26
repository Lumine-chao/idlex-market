import { useEffect, useState } from "react";
import { Input, Space, Button, Avatar, Dropdown, Badge, message } from "antd";
import {
  SearchOutlined,
  PlusOutlined,
  MessageOutlined,
  UserOutlined,
  LogoutOutlined,
  ShopOutlined,
  FlagOutlined,
} from "@ant-design/icons";
import { Link, useNavigate, Outlet } from "react-router-dom";
import { imApi, userApi } from "../api";
import { useAuth } from "../store/auth";

export default function MainLayout() {
  const nav = useNavigate();
  const auth = useAuth();
  const [kw, setKw] = useState("");
  const [unread, setUnread] = useState(0);

  useEffect(() => {
    if (auth.token) {
      userApi.me().then((r) => {
        if (r.code === 0) auth.setUser(r.data);
      });
      refreshUnread();
      const timer = setInterval(refreshUnread, 15000);
      return () => clearInterval(timer);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [auth.token]);

  function refreshUnread() {
    imApi.conversations().then((r) => {
      if (r.code === 0) {
        const total = r.data.list.reduce((s, c) => s + c.unreadCount, 0);
        setUnread(total);
      }
    });
  }

  function doSearch() {
    nav(kw ? `/search?q=${encodeURIComponent(kw)}` : "/search");
  }

  return (
    <div className="idlex-shell">
      <header className="topbar">
        <div className="topbar-inner">
          <Link to="/" className="logo">
            <span className="logo-ic">闲</span> 闲置易
          </Link>
          <Space.Compact className="searchbox" size="large">
            <Input
              placeholder="搜索闲置好物"
              value={kw}
              onChange={(e) => setKw(e.target.value)}
              onPressEnter={doSearch}
              allowClear
            />
            <Button type="primary" icon={<SearchOutlined />} onClick={doSearch} />
          </Space.Compact>
          <div className="actions">
            <Link to="/publish">
              <Button type="primary" icon={<PlusOutlined />}>发布闲置</Button>
            </Link>
            {auth.token ? (
              <Dropdown
                menu={{
                  items: [
                    { key: "profile", icon: <UserOutlined />, label: <Link to="/profile">个人中心</Link> },
                    { key: "orders", icon: <ShopOutlined />, label: <Link to="/orders">我的订单</Link> },
                    { key: "reports", icon: <FlagOutlined />, label: <Link to="/profile?tab=reports">我的举报</Link> },
                    { key: "cols", icon: <MessageOutlined />, label: <Link to="/conversations">消息中心</Link> },
                    { type: "divider" },
                    {
                      key: "logout",
                      icon: <LogoutOutlined />,
                      label: "退出登录",
                      onClick: () => {
                        auth.clear();
                        message.success("已退出登录");
                        nav("/");
                      },
                    },
                  ],
                }}
              >
                <span className="user-chip">
                  <Badge count={unread} size="small">
                    <Avatar size="small" src={auth.user?.avatar || undefined} icon={<UserOutlined />} />
                  </Badge>
                  <em>{auth.user?.username || "我"}</em>
                </span>
              </Dropdown>
            ) : (
              <Link to="/login">
                <Button>登录 / 注册</Button>
              </Link>
            )}
          </div>
        </div>
      </header>
      <div className="idlex-body">
        <Outlet />
      </div>
      <footer className="idlex-footer">闲置易二手交易平台 · 让闲置流动起来</footer>
    </div>
  );
}