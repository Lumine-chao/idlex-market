import { useState } from "react";
import { Form, Input, Button, Card, message } from "antd";
import { LockOutlined, UserOutlined, SafetyOutlined } from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import { adminApi } from "../../api";

export default function AdminLogin() {
  const nav = useNavigate();
  const [loading, setLoading] = useState(false);
  function onFinish(v: { username: string; password: string }) {
    setLoading(true);
    adminApi.login(v)
      .then((r) => {
        if (r.code === 0) {
          localStorage.setItem("idlex_admin_access", r.data.accessToken);
          localStorage.setItem("idlex_admin_refresh", r.data.refreshToken);
          message.success("管理员登录成功");
          nav("/admin/dashboard");
        } else message.error(r.message);
      })
      .catch((e) => message.error(e?.message || "登录失败"))
      .finally(() => setLoading(false));
  }
  return (
    <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center",
      background: "linear-gradient(135deg,#1f2a3d,#2c3e50)" }}>
      <Card style={{ width: 380, boxShadow: "0 8px 30px rgba(0,0,0,0.2)" }} >
        <div style={{ textAlign: "center", marginBottom: 20 }}>
          <SafetyOutlined style={{ fontSize: 40, color: "#ff8a00" }} />
          <h2 style={{ margin: "8px 0 4px" }}>闲置易 · 管理后台</h2>
          <div style={{ color: "#999", fontSize: 13 }}>请使用管理员账号登录</div>
        </div>
        <Form onFinish={onFinish} size="large">
          <Form.Item name="username" rules={[{ required: true, message: "请输入管理员账号" }]}>
            <Input prefix={<UserOutlined />} placeholder="admin" />
          </Form.Item>
          <Form.Item name="password" rules={[{ required: true, message: "请输入密码" }]}>
            <Input.Password prefix={<LockOutlined />} placeholder="密码" />
          </Form.Item>
          <Button type="primary" htmlType="submit" block loading={loading}>登录</Button>
        </Form>
        <div style={{ textAlign: "center", marginTop: 14, color: "#bbb", fontSize: 12 }}>
          演示账号：admin / Admin123
        </div>
      </Card>
    </div>
  );
}