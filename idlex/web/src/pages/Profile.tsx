import { useEffect, useState } from "react";
import { Tabs, Form, Input, Button, message, Card, List, Tag, Modal, Space, Popconfirm, Row, Col, Empty, Checkbox } from "antd";
import { UserOutlined } from "@ant-design/icons";
import { useSearchParams, useNavigate } from "react-router-dom";
import { userApi, itemApi, reportApi } from "../api";
import { useAuth } from "../store/auth";
import type { Item, Address } from "../types";
import { coverUrl, fallbackCover, formatPrice } from "../utils";
import { ITEM_STATUS_TEXT } from "../types";

export default function Profile() {
  const [params] = useSearchParams();
  const nav = useNavigate();
  const auth = useAuth();
  const tab = params.get("tab") || "info";
  const [items, setItems] = useState<Item[]>([]);
  const [addresses, setAddresses] = useState<Address[]>([]);
  const [favorites, setFavorites] = useState<Item[]>([]);
  const [footprints, setFootprints] = useState<Item[]>([]);
  const [reports, setReports] = useState<any[]>([]);
  const [addrOpen, setAddrOpen] = useState(false);
  const [editingAddr, setEditingAddr] = useState<Address | null>(null);
  const [addrForm] = Form.useForm();

  useEffect(() => {
    if (auth.token) refresh(tab);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tab]);

  function refresh(t: string) {
    if (t === "items") itemApi.mine().then((r) => r.code === 0 && setItems(r.data.list));
    if (t === "address") userApi.addresses().then((r) => r.code === 0 && setAddresses(r.data));
    if (t === "favorites") userApi.favorites().then((r) => r.code === 0 && setFavorites(r.data.list));
    if (t === "footprints") userApi.footprints().then((r) => r.code === 0 && setFootprints(r.data.list));
    if (t === "reports") reportApi.mine().then((r) => r.code === 0 && setReports(r.data.list));
  }

  function saveAddr(v: any) {
    const payload = { receiver: v.receiver, phone: v.phone, province: v.province, city: v.city, district: v.district, detail: v.detail, isDefault: !!v.isDefault };
    const p = editingAddr ? userApi.updateAddress(editingAddr.id, payload) : userApi.addAddress(payload);
    p.then((r) => { if (r.code === 0) { message.success(r.message); setAddrOpen(false); setEditingAddr(null); addrForm.resetFields(); refresh("address"); } else message.error(r.message); });
  }

  function actItem(it: Item, action: "on_sale" | "off_sale" | "delete") {
    itemApi.status(it.itemId, action).then((r) => { if (r.code === 0) { message.success(r.message); refresh("items"); } else message.error(r.message); });
  }

  const itemsTabs = [
    { key: "info", label: "个人资料" },
    { key: "items", label: "我的发布" },
    { key: "address", label: "收货地址" },
    { key: "favorites", label: "我的收藏" },
    { key: "footprints", label: "我的足迹" },
    { key: "reports", label: "我的举报" },
  ];

  return (
    <div className="idlex-page" style={{ maxWidth: 960, margin: "0 auto" }}>
      <Row gutter={20}>
        <Col xs={24} md={6}>
          <Card style={{ textAlign: "center", boxShadow: "0 1px 6px rgba(0,0,0,0.05)" }}>
            <div style={{ fontSize: 52, color: "#ff8a00" }}><UserOutlined /></div>
            <h3 style={{ margin: "8px 0 2px" }}>{auth.user?.username}</h3>
            <div style={{ color: "#999", fontSize: 13 }}>{auth.user?.city} · 信用 {auth.user?.creditLevel}/5</div>
            <div style={{ marginBottom: 12 }} />
            <Button type="link" onClick={() => { auth.clear(); message.success("已退出"); nav("/"); }}>退出登录</Button>
          </Card>
        </Col>
        <Col xs={24} md={18}>
          <div style={{ background: "#fff", borderRadius: 12, padding: 16, boxShadow: "0 1px 6px rgba(0,0,0,0.05)" }}>
            <Tabs activeKey={tab} onChange={(k) => nav(`/profile?tab=${k}`)} items={itemsTabs.map((it2) => ({ key: it2.key, label: it2.label, children: content(it2.key) }))} />
          </div>
        </Col>
      </Row>

      <Modal title={editingAddr ? "编辑地址" : "添加地址"} open={addrOpen} onCancel={() => setAddrOpen(false)} onOk={() => addrForm.submit()} okText="保存">
        <Form form={addrForm} layout="vertical" onFinish={saveAddr}>
          <div style={{ display: "flex", gap: 10 }}>
            <Form.Item name="receiver" label="收货人" rules={[{ required: true }]}><Input /></Form.Item>
            <Form.Item name="phone" label="手机号" rules={[{ required: true }]}><Input maxLength={11} /></Form.Item>
          </div>
          <div style={{ display: "flex", gap: 10 }}>
            <Form.Item name="province" label="省" rules={[{ required: true }]}><Input /></Form.Item>
            <Form.Item name="city" label="市" rules={[{ required: true }]}><Input /></Form.Item>
            <Form.Item name="district" label="区" rules={[{ required: true }]}><Input /></Form.Item>
          </div>
          <Form.Item name="detail" label="详细地址" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="isDefault" valuePropName="checked"><Checkbox>设为默认地址</Checkbox></Form.Item>
        </Form>
      </Modal>
    </div>
  );

  function itStatus(it: Item) {
    return <Tag color={it.status === 3 ? "green" : it.status === 5 ? "default" : "orange"}>{ITEM_STATUS_TEXT[it.status]}</Tag>;
  }

  function content(t: string) {
    if (t === "info") return <ProfileForm />;
    if (t === "items") {
      return items.length === 0 ? <Empty description="还没有发布过闲置" /> : (
        <List dataSource={items} renderItem={(it) => (
          <List.Item actions={[
            <Button size="small" onClick={() => nav(`/publish?edit=${it.itemId}`)}>编辑</Button>,
            it.status === 3 ? <Button size="small" onClick={() => actItem(it, "off_sale")}>下架</Button>
              : it.status === 4 ? <Button size="small" type="primary" onClick={() => actItem(it, "on_sale")}>上架</Button> : null,
            <Popconfirm title="删除该商品？" onConfirm={() => actItem(it, "delete")}><Button size="small" danger>删除</Button></Popconfirm>,
          ]}>
            <List.Item.Meta avatar={<img src={coverUrl(it)} alt="" width={64} height={64} style={{ borderRadius: 8, objectFit: "cover" }} onError={(e) => fallbackCover(e.currentTarget, it.title)} />}
              title={<Space>{it.title}{itStatus(it)}</Space>}
              description={<span className="price">{formatPrice(it.price)}</span>} />
          </List.Item>
        )} />
      );
    }
    if (t === "address") {
      return (<>
        <Button type="primary" onClick={() => { setEditingAddr(null); addrForm.resetFields(); setAddrOpen(true); }} style={{ marginBottom: 14 }}>添加地址</Button>
        {addresses.length === 0 ? <Empty description="暂无收货地址" /> : <List dataSource={addresses} renderItem={(a) => (
          <List.Item actions={[
            <Button size="small" onClick={() => { setEditingAddr(a); addrForm.setFieldsValue(a); setAddrOpen(true); }}>编辑</Button>,
            <Popconfirm title="删除该地址？" onConfirm={() => userApi.deleteAddress(a.id).then(() => { message.success("已删除"); refresh("address"); })}><Button size="small" danger>删除</Button></Popconfirm>,
          ]}>
            <div>
              <div>{a.receiver} · {a.phone} {a.isDefault && <Tag color="green">默认</Tag>}</div>
              <div style={{ color: "#999", fontSize: 13 }}>{a.province}{a.city}{a.district}{a.detail}</div>
            </div>
          </List.Item>
        )} />}
      </>);
    }
    if (t === "favorites") return favorites.length === 0 ? <Empty description="暂无收藏" /> : <Grid items={favorites} />;
    if (t === "footprints") return (
      <>
        <Button size="small" onClick={() => userApi.clearFootprints().then(() => { message.success("已清空"); refresh("footprints"); })}>清空足迹</Button>
        <div style={{ marginTop: 14 }}>{footprints.length === 0 ? <Empty description="暂无足迹" /> : <Grid items={footprints} />}</div>
      </>
    );
    if (t === "reports") return reports.length === 0 ? <Empty description="暂无举报记录" /> : <List dataSource={reports} renderItem={(r: any) => (
      <List.Item><div>
        <Tag>{r.targetType === "item" ? "举报商品" : r.targetType === "user" ? "举报用户" : "举报消息"}</Tag>
        <span style={{ marginLeft: 6 }}>原因：{r.reasonType}</span>
        <div style={{ color: r.status >= 2 ? "#ff7a00" : "#999", fontSize: 13 }}>
          {r.status === 0 ? "处理中" : r.status >= 2 ? `已处理（${r.result || ""}）` : "已受理"}
        </div>
      </div></List.Item>
    )} />;
    return null;
  }
}

function Grid({ items }: { items: Item[] }) {
  const nav = useNavigate();
  return <Row gutter={[12, 12]}>{items.map((it) => (
    <Col key={it.itemId} xs={12} md={8}>
      <Card size="small" hoverable cover={<img src={coverUrl(it)} alt="" style={{ height: 120, objectFit: "cover" }} onClick={() => nav(`/item/${it.itemId}`)} onError={(e) => fallbackCover(e.currentTarget, it.title)} />} onClick={() => nav(`/item/${it.itemId}`)}>
        <Card.Meta title={<span className="price">{formatPrice(it.price)}</span>} description={<span style={{ fontSize: 13 }}>{it.title}</span>} />
      </Card>
    </Col>
  ))}</Row>;
}

function ProfileForm() {
  const auth = useAuth();
  const [form] = Form.useForm();
  useEffect(() => { form.setFieldsValue({ city: auth.user?.city }); // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [auth.user]);
  return (
    <Form form={form} layout="vertical" onFinish={(v) => userApi.updateMe(v).then((r) => {
      if (r.code === 0) { message.success("已保存"); auth.setUser(r.data); } else message.error(r.message);
    })} style={{ maxWidth: 400 }}>
      <Form.Item label="用户名">
        <Input value={auth.user?.username} disabled />
      </Form.Item>
      <Form.Item name="city" label="城市"><Input /></Form.Item>
      <Button type="primary" htmlType="submit">保存</Button>
    </Form>
  );
}