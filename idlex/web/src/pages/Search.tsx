import { useEffect, useState } from "react";
import { Row, Col, Select, Slider, Empty, Radio, Space } from "antd";
import { useSearchParams } from "react-router-dom";
import { searchApi, catApi } from "../api";
import type { Item, CategoryNode } from "../types";
import ItemCard from "../components/ItemCard";

const SORTS = [
  { label: "综合", value: "relevance" },
  { label: "最新", value: "newest" },
  { label: "价格↑", value: "price_asc" },
  { label: "价格↓", value: "price_desc" },
];

const MAX_PRICE = 5000;

export default function Search() {
  const [params] = useSearchParams();
  const [q, setQ] = useState(params.get("q") || "");
  const [cats, setCats] = useState<CategoryNode[]>([]);
  const [categoryId, setCategoryId] = useState<number | undefined>(undefined);
  const [priceRange, setPriceRange] = useState<[number, number]>([0, MAX_PRICE]);
  const [sort, setSort] = useState("relevance");
  const [freeShipping, setFreeShipping] = useState(false);
  const [items, setItems] = useState<Item[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    catApi.tree().then((r) => r.code === 0 && setCats(r.data));
  }, []);

  useEffect(() => {
    setQ(params.get("q") || "");
  }, [params]);

  function search() {
    const lo = priceRange[0] > 0 ? priceRange[0] : undefined;
    const hi = priceRange[1] < MAX_PRICE ? priceRange[1] : undefined;
    setLoading(true);
    searchApi
      .run({
        q,
        category_id: categoryId,
        min_price: lo,
        max_price: hi,
        free_shipping: freeShipping || undefined,
        sort,
        size: 40,
      })
      .then((r) => {
        if (r.code === 0) { setItems(r.data.list); setTotal(r.data.total); }
      })
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    const t = setTimeout(search, 300);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [q, categoryId, sort, freeShipping, priceRange]);

  return (
    <div className="idlex-page">
      {q && <div style={{ marginBottom: 12, fontSize: 15, color: "#555" }}>搜索「<b>{q}</b>」 的结果</div>}
      <div style={{ display: "flex", gap: 12, marginBottom: 6, alignItems: "center", flexWrap: "wrap" }}>
        <Select
          allowClear placeholder="全部分类" size="large" style={{ minWidth: 180 }}
          value={categoryId} onChange={setCategoryId}
          options={cats.map((c) => ({ label: c.label, value: c.value }))}
        />
        <span style={{ color: "#666", fontSize: 14 }}>价格区间</span>
        <Slider
          style={{ width: 200, margin: "0 8px" }} range min={0} max={MAX_PRICE} step={50}
          value={priceRange}
          onChange={(v) => setPriceRange(v as [number, number])}
          tooltip={{ formatter: (v) => (v === MAX_PRICE ? "不限" : `¥${v}`) }}
        />
        <span style={{ color: "#ff7a00", fontWeight: 600, fontSize: 14 }}>
          ¥{priceRange[0]} ~ {priceRange[1] >= MAX_PRICE ? "不限" : `¥${priceRange[1]}`}
        </span>
      </div>
      <div style={{ fontSize: 12, color: "#999", marginBottom: 14 }}>
        拖动左右两个圆点设置可接受的价格范围，左侧为最低价、右侧为最高价（拖到最右表示不限）
      </div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
        <Space>
          <Radio.Group value={sort} onChange={(e) => setSort(e.target.value)} optionType="button" size="small"
            options={SORTS} />
          <label style={{ fontSize: 13, cursor: "pointer" }}>
            <input type="checkbox" checked={freeShipping} onChange={(e) => setFreeShipping(e.target.checked)} /> 包邮
          </label>
        </Space>
        <span style={{ color: "#999", fontSize: 13 }}>共 {total} 件</span>
      </div>
      <Row gutter={[16, 16]}>
        {items.map((it) => (
          <Col key={it.itemId} xs={12} sm={12} md={8} lg={6}><ItemCard item={it} /></Col>
        ))}
      </Row>
      {!loading && items.length === 0 && <Empty description="没有找到相关商品，试试更换关键词或放宽价格区间" style={{ marginTop: 40 }} />}
    </div>
  );
}