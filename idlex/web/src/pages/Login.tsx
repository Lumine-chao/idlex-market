import { useState } from "react";
import { Form, Input, Button, Card, message, Space, Divider } from "antd";
import { UserOutlined, LockOutlined } from "@ant-design/icons";
import { Link, useNavigate } from "react-router-dom";
import { authApi } from "../api";
import { useAuth } from "../store/auth";

export default function Login() {
  const nav = useNavigate();
  const auth = useAuth();
  const [loading, setLoading] = useState(false);

  function afterLogin(access: string, refresh: string) {
    auth.setAuth(access, refresh);
    message.success("登录成功");
    nav("/");
  }

  function onPwd(v: { username: string; password: string }) {
    setLoading(true);
    authApi.login(v)
      .then((r) => {
        if (r.code === 0) afterLogin(r.data.accessToken, r.data.refreshToken);
        // 业务错误以 HTTP 200 + 非 0 code 返回，必须显式提示
        else message.error(r.message || "登录失败");
      })
      .catch((e) => message.error(e?.message || "登录失败"))
      .finally(() => setLoading(false));
  }

  const demos = [
    { username: "xianzhidaren", label: "闲置达人" },
    { username: "xiaozhou", label: "小洲同学" },
    { username: "zhangshop", label: "老张杂货铺" },
  ];

  return (
    <div className="idlex-page" style={{ maxWidth: 420, margin: "0 auto", paddingTop: 60 }}>
      <Card bordered={false} style={{ boxShadow: "0 4px 20px rgba(0,0,0,0.06)" }}>
        <h2 style={{ textAlign: "center", color: "#ff7a00", marginBottom: 4 }}>闲置易</h2>
        <p style={{ textAlign: "center", color: "#999", marginBottom: 20 }}>欢迎回来，登录继续淘好物</p>
        <Form onFinish={onPwd} size="large">
          <Form.Item
            name="username"
            rules={[{ required: true, message: "请输入用户名" }, { pattern: /^[A-Za-z][A-Za-z0-9_]{2,31}$/, message: "用户名以字母开头，3~32位字母/数字/下划线" }]}
          >
            <Input prefix={<UserOutlined />} placeholder="用户名" maxLength={32} />
          </Form.Item>
          <Form.Item name="password" rules={[{ required: true, message: "请输入密码" }]}>
            <Input.Password prefix={<LockOutlined />} placeholder="密码" />
          </Form.Item>
          <Button type="primary" htmlType="submit" block loading={loading}>登录</Button>
        </Form>
        <div style={{ textAlign: "right", marginTop: 4 }}>
          <Link to="/forgot">忘记密码？</Link>
        </div>
        <Divider plain style={{ color: "#bbb", fontSize: 12 }}>演示账号一键登录（密码 Abc12345）</Divider>
        <Space wrap style={{ width: "100%", justifyContent: "center" }}>
          {demos.map((d) => (
            <Button key={d.username} onClick={() => {
              onPwd({ username: d.username, password: "Abc12345" });
            }}>{d.label}</Button>
          ))}
        </Space>
        <div style={{ textAlign: "center", marginTop: 18 }}>
          还没有账号？<Link to="/register">立即注册</Link>
        </div>
      </Card>
    </div>
  );
}