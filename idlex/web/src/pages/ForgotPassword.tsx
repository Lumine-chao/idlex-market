import { useEffect, useState } from "react";
import { Form, Input, Button, Card, message, Select } from "antd";
import { LockOutlined, UserOutlined, SafetyOutlined } from "@ant-design/icons";
import { Link, useNavigate } from "react-router-dom";
import { authApi } from "../api";
import { passwordError } from "../utils";

export default function ForgotPassword() {
  const nav = useNavigate();
  const [loading, setLoading] = useState(false);
  const [questions, setQuestions] = useState<string[]>([]);

  useEffect(() => {
    authApi.securityQuestions().then((r) => {
      if (r.code === 0) setQuestions(r.data.questions);
    });
  }, []);

  function onFinish(v: any) {
    setLoading(true);
    authApi.resetPassword(v)
      .then((r) => {
        if (r.code === 0) {
          message.success("密码重置成功，请用新密码登录");
          nav("/login");
        } else {
          // 业务错误以 HTTP 200 + 非 0 code 返回，必须显式提示
          message.error(r.message || "找回失败");
        }
      })
      .catch((e) => message.error(e?.message || "找回失败"))
      .finally(() => setLoading(false));
  }

  return (
    <div className="idlex-page" style={{ maxWidth: 440, margin: "0 auto", paddingTop: 60 }}>
      <Card bordered={false} style={{ boxShadow: "0 4px 20px rgba(0,0,0,0.06)" }}>
        <h2 style={{ textAlign: "center", color: "#ff7a00", marginBottom: 4 }}>找回密码</h2>
        <p style={{ textAlign: "center", color: "#999", marginBottom: 20 }}>通过密保问题验证后重置密码</p>
        <Form onFinish={onFinish} size="large" layout="vertical">
          <Form.Item
            name="username" label="用户名"
            rules={[{ required: true, message: "请输入用户名" }, { pattern: /^[A-Za-z][A-Za-z0-9_]{2,31}$/, message: "用户名以字母开头，3~32位" }]}
          >
            <Input prefix={<UserOutlined />} placeholder="你的登录用户名" maxLength={32} />
          </Form.Item>
          <Form.Item name="securityQuestion" label="密保问题" rules={[{ required: true, message: "请选择密保问题" }]}>
            <Select placeholder="注册时设置的密保问题" options={questions.map((q) => ({ label: q, value: q }))} />
          </Form.Item>
          <Form.Item name="securityAnswer" label="问题答案" rules={[{ required: true, message: "请输入密保答案" }]}>
            <Input prefix={<SafetyOutlined />} placeholder="注册时填写的答案" maxLength={50} />
          </Form.Item>
          <Form.Item
            name="newPassword" label="新密码"
            rules={[
              { required: true, message: "请设置新密码" },
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
            name="confirm" label="确认新密码"
            dependencies={["newPassword"]}
            rules={[
              { required: true, message: "请再次输入新密码" },
              ({ getFieldValue }) => ({
                validator(_, value) {
                  if (!value || getFieldValue("newPassword") === value) return Promise.resolve();
                  return Promise.reject(new Error("两次输入的密码不一致"));
                },
              }),
            ]}
          >
            <Input.Password prefix={<LockOutlined />} placeholder="再次输入新密码" />
          </Form.Item>
          <Button type="primary" htmlType="submit" block loading={loading}>重置密码</Button>
        </Form>
        <div style={{ textAlign: "center", marginTop: 16 }}>
          想起来了？<Link to="/login">返回登录</Link>
        </div>
      </Card>
    </div>
  );
}