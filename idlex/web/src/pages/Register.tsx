import { useEffect, useState } from "react";
import { Form, Input, Button, Card, message, Select } from "antd";
import { LockOutlined, UserOutlined, SafetyOutlined } from "@ant-design/icons";
import { Link, useNavigate } from "react-router-dom";
import { authApi } from "../api";
import { passwordError } from "../utils";
import { useAuth } from "../store/auth";

export default function Register() {
  const nav = useNavigate();
  const auth = useAuth();
  const [loading, setLoading] = useState(false);
  const [questions, setQuestions] = useState<string[]>([]);

  useEffect(() => {
    authApi.securityQuestions().then((r) => {
      if (r.code === 0) setQuestions(r.data.questions);
    });
  }, []);

  function onFinish(v: any) {
    setLoading(true);
    authApi.register(v)
      .then((r) => {
        if (r.code === 0) {
          auth.setAuth(r.data.accessToken, r.data.refreshToken);
          message.success("注册成功，已自动登录");
          nav("/");
        } else {
          // 后端业务错误以 HTTP 200 + 非 0 code 返回，需显式提示，否则按钮看起来毫无反应
          message.error(r.message || "注册失败");
        }
      })
      .catch((e) => message.error(e?.message || "注册失败"))
      .finally(() => setLoading(false));
  }

  return (
    <div className="idlex-page" style={{ maxWidth: 440, margin: "0 auto", paddingTop: 40 }}>
      <Card bordered={false} style={{ boxShadow: "0 4px 20px rgba(0,0,0,0.06)" }}>
        <h2 style={{ textAlign: "center", color: "#ff7a00" }}>注册闲置易</h2>
        <Form onFinish={onFinish} size="large" layout="vertical">
          <Form.Item
            name="username" label="用户名"
            rules={[
              { required: true, message: "请输入用户名" },
              { pattern: /^[A-Za-z][A-Za-z0-9_]{2,31}$/, message: "以字母开头，由3~32位字母/数字/下划线组成" },
            ]}
          >
            <Input prefix={<UserOutlined />} placeholder="登录用户名，如 xianzhidaren" maxLength={32} />
          </Form.Item>
          <Form.Item
            name="password" label="密码"
            rules={[
              { required: true, message: "请设置密码" },
              ({ getFieldValue }) => ({
                validator(_, value) {
                  const msg = passwordError(value || "", getFieldValue("username"));
                  return msg ? Promise.reject(new Error(msg)) : Promise.resolve();
                },
              }),
            ]}
          >
            <Input.Password prefix={<LockOutlined />} placeholder="8~20位，含字母与数字，不含连续字符" />
          </Form.Item>
          <Form.Item
            name="confirm" label="确认密码"
            dependencies={["password"]}
            rules={[
              { required: true, message: "请再次输入密码" },
              ({ getFieldValue }) => ({
                validator(_, value) {
                  if (!value || getFieldValue("password") === value) return Promise.resolve();
                  return Promise.reject(new Error("两次输入的密码不一致"));
                },
              }),
            ]}
          >
            <Input.Password prefix={<LockOutlined />} placeholder="再次输入密码" />
          </Form.Item>
          <Form.Item name="securityQuestion" label="密保问题" rules={[{ required: true, message: "请选择密保问题" }]}>
            <Select placeholder="用于忘记密码时找回" options={questions.map((q) => ({ label: q, value: q }))} />
          </Form.Item>
          <Form.Item
            name="securityAnswer" label="问题答案"
            rules={[{ required: true, min: 2, max: 50, message: "答案2~50个字符，请牢记" }]}
          >
            <Input prefix={<SafetyOutlined />} placeholder="请务必牢记此答案" maxLength={50} />
          </Form.Item>
          <Button type="primary" htmlType="submit" block loading={loading}>注册并登录</Button>
        </Form>
        <div style={{ textAlign: "center", marginTop: 16 }}>
          已有账号？<Link to="/login">去登录</Link>
        </div>
      </Card>
    </div>
  );
}