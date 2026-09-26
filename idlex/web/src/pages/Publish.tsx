import { useEffect, useState } from "react";
import { Form, Input, InputNumber, Select, Button, Card, Upload, Radio, Cascader, message } from "antd";
import { InboxOutlined } from "@ant-design/icons";
import { useNavigate, useSearchParams } from "react-router-dom";
import { catApi, itemApi, uploadApi } from "../api";
import type { CategoryNode } from "../types";

/** 由三级分类 id 反查 Cascader 需要的完整路径 [一级, 二级, 三级] */
function findCatPath(nodes: CategoryNode[], target: number, trail: number[] = []): number[] | null {
  for (const n of nodes) {
    const next = [...trail, n.value];
    if (n.value === target) return next;
    if (n.children?.length) {
      const hit = findCatPath(n.children, target, next);
      if (hit) return hit;
    }
  }
  return null;
}

export default function Publish() {
  const nav = useNavigate();
  const [params] = useSearchParams();
  const [form] = Form.useForm();
  const [cats, setCats] = useState<CategoryNode[]>([]);
  const [fileList, setFileList] = useState<any[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const editId = params.get("edit");
  const editIdNum = editId ? Number(editId) : null;

  useEffect(() => {
    catApi.tree().then((r) => r.code === 0 && setCats(r.data));
  }, []);

  // 编辑模式：拉取原闲置信息回填，方便在此基础上修改
  // 依赖分类树：三级分类要拼出完整路径才能让 Cascader 正确显示
  useEffect(() => {
    if (!editIdNum || !cats.length) return;
    itemApi.mine().then((r) => {
      if (r.code !== 0) return;
      const it = r.data.list.find((x) => x.itemId === editIdNum);
      if (!it) {
        message.error("未找到该闲置，可能已被删除");
        return;
      }
      setFileList(
        (it.images || []).filter(Boolean).map((url, i) => ({
          uid: `saved_${i}`,
          name: url.split("/").pop() || `图片${i + 1}`,
          status: "done",
          url,
        })),
      );
      form.setFieldsValue({
        title: it.title,
        description: it.description,
        categoryId: findCatPath(cats, it.categoryId) ?? undefined,
        conditionLevel: it.conditionLevel,
        price: it.price,
        originPrice: it.originPrice ?? undefined,
        stock: it.stock,
        city: it.city,
        tradeType: it.tradeType,
        freightPayer: it.freightPayer,
        freight: it.freight,
      });
    }).catch(() => message.error("加载闲置信息失败"));
  }, [editIdNum, cats, form]);

  async function beforeUpload(file: File) {
    try {
      const url = await uploadApi.upload(file);
      setFileList((p) => [...p, { uid: name(file), name: file.name, status: "done", url }]);
    } catch (e: any) {
      message.error(e?.message || "上传失败");
    }
    return false;
  }
  function name(f: File) { return `${Date.now()}_${f.name}`; }

  const imgUrls = fileList.map((f) => f.url).filter(Boolean);

  function onFinish(v: any) {
    setSubmitting(true);
    const catLeaf = Array.isArray(v.categoryId) ? v.categoryId[v.categoryId.length - 1] : v.categoryId;
    const payload = {
      title: v.title,
      description: v.description,
      categoryId: catLeaf,
      conditionLevel: v.conditionLevel,
      price: v.price,
      originPrice: v.originPrice || null,
      stock: v.stock || 1,
      city: v.city || "",
      tradeType: v.tradeType || 1,
      freightPayer: v.freightPayer || 1,
      freight: v.freight || 0,
      images: imgUrls,
    };
    const req = editId ? itemApi.update(Number(editId), payload) : itemApi.create(payload);
    req.then((r) => {
      if (r.code === 0) { message.success(r.message); nav("/profile?tab=items"); }
      else message.error(r.message);
    }).catch((e) => message.error(e?.message || "发布失败")).finally(() => setSubmitting(false));
  }

  return (
    <div className="idlex-page" style={{ maxWidth: 860, margin: "0 auto" }}>
      <Card title={editId ? "编辑闲置" : "发布闲置"} style={{ boxShadow: "0 2px 12px rgba(0,0,0,0.05)" }}>
        <Form form={form} layout="vertical" onFinish={onFinish} requiredMark={false}>
          <Form.Item name="title" label="标题（5-50字）" rules={[{ required: true, min: 5, max: 50, message: "标题5~50字" }]}>
            <Input placeholder="例：九成新 iPhone 13 128G 自用出" />
          </Form.Item>
          <Form.Item name="categoryId" label="分类" rules={[{ required: true, message: "请选择三级分类" }]}>
            <Cascader options={cats} fieldNames={{ label: "label", value: "value", children: "children" }} placeholder="选择分类" />
          </Form.Item>
          <Form.Item name="description" label="描述（10-2000字）" rules={[{ required: true, min: 10, max: 2000, message: "描述10~2000字" }]}>
            <Input.TextArea rows={5} placeholder="说说闲置情况、使用时长、瑕疵、转让原因等" maxLength={2000} showCount />
          </Form.Item>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 16 }}>
            <Form.Item name="price" label="售价（元）" rules={[{ required: true, message: "请输入售价" }]}>
              <InputNumber min={0.01} max={1000000} style={{ width: "100%" }} placeholder="199" />
            </Form.Item>
            <Form.Item name="originPrice" label="原价（元，选填）">
              <InputNumber min={0} max={1000000} style={{ width: "100%" }} placeholder="399" />
            </Form.Item>
            <Form.Item name="stock" label="数量" initialValue={1}>
              <InputNumber min={1} max={999} style={{ width: "100%" }} />
            </Form.Item>
            <Form.Item name="conditionLevel" label="成色" rules={[{ required: true, message: "选择成色" }]}>
              <Select placeholder="选择成色" options={[
                { value: 1, label: "全新" }, { value: 2, label: "几乎全新" },
                { value: 3, label: "轻微使用痕迹" }, { value: 4, label: "明显使用痕迹" },
              ]} />
            </Form.Item>
            <Form.Item name="tradeType" label="交易方式" initialValue={1}>
              <Select options={[{ value: 1, label: "同城面交" }, { value: 2, label: "邮寄" }]} />
            </Form.Item>
            <Form.Item name="city" label="所在城市">
              <Input placeholder="深圳" maxLength={20} />
            </Form.Item>
            <Form.Item name="freightPayer" label="运费承担" initialValue={1}>
              <Radio.Group>
                <Radio value={1}>包邮</Radio>
                <Radio value={2}>买家承担</Radio>
              </Radio.Group>
            </Form.Item>
            <Form.Item name="freight" label="运费（元）" initialValue={0}>
              <InputNumber min={0} max={999} style={{ width: "100%" }} />
            </Form.Item>
          </div>
          <Form.Item label="图片（1-9张，支持 jpg/png/webp）" required>
            <Upload listType="picture-card" fileList={fileList} accept=".jpg,.jpeg,.png,.webp"
              beforeUpload={beforeUpload} onRemove={(f) => setFileList((p) => p.filter((x) => x.uid !== f.uid))}>
              {fileList.length >= 9 ? null : (
                <div><InboxOutlined style={{ fontSize: 28, color: "#ff8a00" }} /><div style={{ fontSize: 12 }}>上传</div></div>
              )}
            </Upload>
          </Form.Item>
          <Button type="primary" htmlType="submit" size="large" block loading={submitting}>
            {editId ? "保存修改" : "确认发布"}
          </Button>
        </Form>
      </Card>
    </div>
  );
}