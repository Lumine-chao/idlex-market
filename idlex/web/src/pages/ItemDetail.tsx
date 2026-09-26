import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Button, Tag, Image, Row, Col, message, Modal, Radio, Empty, Rate, Card, Divider, Input, Skeleton, Form, Space } from "antd";
import { MessageOutlined, HeartOutlined, HeartFilled, FlagOutlined, SafetyOutlined, CheckCircleFilled } from "@ant-design/icons";
import { itemApi, imApi, orderApi, reviewApi, reportApi, userApi } from "../api";
import type { Item, Address, Review } from "../types";
import { coverUrl, fallbackCover, formatPrice, timeAgo } from "../utils";
import { useAuth } from "../store/auth";

export default function ItemDetail() {
  const { id } = useParams();
  const nav = useNavigate();
  const auth = useAuth();
  const [item, setItem] = useState<Item>();
  const [mainImg, setMainImg] = useState<string>();
  const [reviews, setReviews] = useState<Review[]>([]);
  const [avg, setAvg] = useState(0);
  const [loading, setLoading] = useState(true);
  const [buyOpen, setBuyOpen] = useState(false);
  const [addresses, setAddresses] = useState<Address[]>([]);
  const [chosenAddr, setChosenAddr] = useState<number>();
  const [buying, setBuying] = useState(false);
  const [reportOpen, setReportOpen] = useState(false);
  const [detailLoading, setDetailLoading] = useState(true);
  const [faved, setFaved] = useState(false);

  useEffect(() => {
    setDetailLoading(true);
    itemApi.detail(Number(id)).then((r) => {
      if (r.code === 0) {
        setItem(r.data);
        setMainImg(r.data.images?.find((x) => x) || coverUrl(r.data));
      } else message.error(r.message);
    }).finally(() => { setLoading(false); setDetailLoading(false); });
    reviewApi.listByItem(Number(id)).then((r) => { if (r.code === 0) { setReviews(r.data.list); setAvg(r.data.avgScore); } });
    if (auth.token) {
      userApi.favorites().then((r) => {
        if (r.code === 0) setFaved(r.data.list.some((x) => x.itemId === Number(id)));
      });
    } else {
      setFaved(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id, auth.token]);

  function toggleFav() {
    if (!auth.token) return nav("/login");
    itemApi.toggleFavorite(Number(id)).then((r) => {
      if (r.code === 0) { setFaved(r.data.favorited); message.success(r.message); }
      else message.warning(r.message);
    });
  }

  function contact() {
    if (!auth.token) return nav("/login");
    imApi.create(Number(id)).then((r) => {
      if (r.code === 0) { itemApi.footprint(Number(id)); nav(`/conversations/${r.data.conversationId}`); }
      else message.warning(r.message);
    });
  }

  function openBuy() {
    if (!auth.token) return nav("/login");
    itemApi.footprint(Number(id));
    if (item?.seller?.id === auth.user?.id) return message.warning("不能购买自己发布的商品");
    userApi.addresses().then((r) => {
      if (r.code === 0) { setAddresses(r.data); setBuyOpen(true); setChosenAddr(r.data.find((a) => a.isDefault)?.id || r.data[0]?.id); }
    });
  }

  function confirmBuy() {
    if (!chosenAddr) return message.warning("请选择收货地址");
    setBuying(true);
    orderApi.create({ itemId: Number(id), quantity: 1, addressId: chosenAddr })
      .then(async (r) => {
        if (r.code !== 0) return message.warning(r.message);
        const orderNo = r.data.orderNo;
        message.success(r.message);
        // 引导确认支付
        const ok = await new Promise<boolean>((res) => {
          Modal.confirm({
            title: "订单已创建，请完成支付",
            content: `订单号：${orderNo}，金额 ${formatPrice(r.data.totalAmount)}。资金全额托管，收货确认后才打给卖家。`,
            okText: "立即支付", cancelText: "稍后支付",
            onOk: () => res(true), onCancel: () => res(false),
            closable: true, maskClosable: true,
          });
        });
        setBuyOpen(false);
        if (ok) {
          const pay = await orderApi.pay(orderNo);
          if (pay.code === 0) message.success("支付成功，资金已托管");
          else message.warning(pay.message);
        }
        nav("/orders");
      })
      .catch((e) => message.error(e?.message || "下单失败"))
      .finally(() => setBuying(false));
  }

  function copyLink() {
    const url = window.location.href;
    navigator.clipboard?.writeText(url);
    message.success("链接已复制");
  }

  if (loading || !item) return <div className="idlex-page"><Skeleton active /><Skeleton active /></div>;

  return (
    <div className="idlex-page">
      <Row gutter={24}>
        <Col xs={24} md={11}>
          <div style={{ position: "relative" }}>
            <Image
              src={mainImg || coverUrl(item)}
              fallback={coverUrl({ title: item.title })}
              className="detail-cover"
              preview={{ src: mainImg }}
            />
            <div style={{ display: "flex", gap: 8, marginTop: 10 }}>
              {(item.images && item.images.length ? item.images : [""]).map((img, i) => (
                <img key={i} src={img || coverUrl(item, "square")} className={`thumb ${mainImg === img ? "active" : ""}`}
                  onClick={() => setMainImg(img || coverUrl(item, "square"))} alt="" onError={(e) => fallbackCover(e.currentTarget, item.title, "square")} />
              ))}
            </div>
          </div>
        </Col>
        <Col xs={24} md={13}>
          <h1 style={{ fontSize: 20, lineHeight: 1.4, margin: "0 0 10px" }}>{item.title}</h1>
          <div style={{ display: "flex", gap: 8, marginBottom: 14 }}>
            <Tag color="orange">{item.conditionText}</Tag>
            {item.tradeType === 1 ? <Tag color="blue">同城面交</Tag> : <Tag color="geekblue">邮寄</Tag>}
            {item.freight === 0 && item.tradeType === 2 ? <Tag color="green">包邮</Tag> : null}
            <span style={{ color: "#999", fontSize: 13 }}>{item.city}</span>
          </div>
          <Card size="small" style={{ background: "#fff7ef", borderColor: "#ffe3c2", marginBottom: 16 }}>
            <div className="price-big">{formatPrice(item.price)}
              {item.originPrice ? <span style={{ fontSize: 14, color: "#bbb", fontWeight: 400, marginLeft: 10 }}><s style={{}}>{formatPrice(item.originPrice)}</s></span> : null}
            </div>
            <div style={{ color: "#999", fontSize: 12, marginTop: 4 }}>库存 {item.stock} 件 · 浏览 {item.viewCount}</div>
          </Card>
          <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "12px 0", borderTop: "1px dashed #eee", borderBottom: "1px dashed #eee", marginBottom: 16 }}>
            <Image width={44} height={44} style={{ borderRadius: "50%" }} src={item.seller?.avatar || undefined} fallback={coverUrl({ title: item.seller?.username }, "square")} preview={false} />
            <div style={{ flex: 1 }}>
              <div style={{ fontWeight: 600 }}>{item.seller?.username}</div>
              <div style={{ fontSize: 12, color: "#999" }}>信用等级 {item.seller?.creditLevel}/5 · {item.seller?.city}</div>
            </div>
            {item.seller?.id === auth.user?.id ? null : (
              <Button icon={<MessageOutlined />} onClick={contact}>聊一聊</Button>
            )}
          </div>
          <Space wrap>
            <Button type="primary" size="large" icon={<SafetyOutlined />} disabled={item.stock < 1 || item.seller?.id === auth.user?.id} onClick={openBuy}>
              立即购买
            </Button>
            <Button size="large" icon={faved ? <HeartFilled style={{ color: "#ff4d4f" }} /> : <HeartOutlined />} onClick={toggleFav}>
              {faved ? "已收藏" : "收藏"}
            </Button>
            <Button size="large" onClick={copyLink}>分享链接</Button>
            <Button size="large" icon={<FlagOutlined />} onClick={() => setReportOpen(true)}>举报</Button>
          </Space>
          <div style={{ marginTop: 20, color: "#666", fontSize: 13, background: "#fafafa", borderRadius: 10, padding: 12 }}>
            <CheckCircleFilled style={{ color: "#52c41a" }} /> 平台担保交易，资金托管到收货确认<br />
            <CheckCircleFilled style={{ color: "#52c41a" }} /> 全程状态流转留痕，可追溯可申诉
          </div>
        </Col>
      </Row>

      <Divider>商品描述</Divider>
      <div style={{ whiteSpace: "pre-wrap", lineHeight: 1.8, fontSize: 15, color: "#444" }}>{item.description}</div>
      <Divider>买家评价（{reviews.length}）</Divider>
      <Rate disabled value={avg} style={{ fontSize: 16 }} /> <span style={{ color: "#999", marginLeft: 8 }}>平均 {avg} 分</span>
      {reviews.length === 0 ? <Empty description="暂无评价" /> : reviews.map((r) => (
        <Card size="small" key={r.id} style={{ marginTop: 10 }}>
          <Space><strong>{r.reviewerName}</strong><Rate disabled value={r.score} style={{ fontSize: 12 }} /></Space>
          <div style={{ color: "#666" }}>{r.content}</div>
        </Card>
      ))}

      {/* 购买弹窗 */}
      <Modal title="选择收货地址并下单" open={buyOpen} onCancel={() => setBuyOpen(false)} onOk={confirmBuy} okText="确认下单并支付" okButtonProps={{ loading: buying }}>
        {addresses.length === 0 ? (
          <Empty description="请先添加收货地址">
            <Button type="primary" onClick={() => nav("/profile?tab=address")}>去添加地址</Button>
          </Empty>
        ) : (
          <Radio.Group value={chosenAddr} onChange={(e) => setChosenAddr(e.target.value)} style={{ width: "100%" }}>
            {addresses.map((a) => (
              <Radio value={a.id} key={a.id} style={{ display: "block", padding: "8px 0" }}>
                {a.receiver} {a.phone.slice(-4)} · {a.province}{a.city}{a.district}{a.detail}
                {a.isDefault && <Tag color="green" style={{ marginLeft: 8 }}>默认</Tag>}
              </Radio>
            ))}
          </Radio.Group>
        )}
        {item && <>
          <Divider />
          <span className="price-big">{formatPrice(item.price + item.freight)}</span>
          <span style={{ color: "#999", marginLeft: 8 }}>含运费 {formatPrice(item.freight)}</span>
        </>}
      </Modal>

      <ReportModal itemId={item.itemId} open={reportOpen} onClose={() => setReportOpen(false)} />
    </div>
  );
}

function ReportModal({ itemId, open, onClose }: { itemId: number; open: boolean; onClose: () => void }) {
  const [form] = Form.useForm();
  function submit(v: { reasonType: string; description?: string }) {
    reportApi.submit({ targetType: "item", targetId: itemId, reasonType: v.reasonType, description: v.description })
      .then((r) => { r.code === 0 ? message.success(r.message) : message.error(r.message); onClose(); });
  }
  return (
    <Modal title="举报该商品" open={open} onCancel={onClose} onOk={() => form.submit()} okText="提交举报">
      <Form form={form} onFinish={submit} layout="vertical">
        <Form.Item name="reasonType" label="举报原因" rules={[{ required: true, message: "请选择原因" }]}>
          <Radio.Group>
            <Radio.Button value="违规商品">违规商品</Radio.Button>
            <Radio.Button value="假货仿品">假货仿品</Radio.Button>
            <Radio.Button value="骗取钱财">骗取钱财</Radio.Button>
            <Radio.Button value="描述不符">描述不符</Radio.Button>
          </Radio.Group>
        </Form.Item>
        <Form.Item name="description" label="补充说明">
          <Input.TextArea rows={3} placeholder="补充情况说明（选填）" maxLength={500} />
        </Form.Item>
      </Form>
    </Modal>
  );
}