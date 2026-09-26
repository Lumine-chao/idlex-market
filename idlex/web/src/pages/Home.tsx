import { useEffect, useState } from "react";
import { Row, Col, Skeleton, Tag, message } from "antd";
import { useNavigate } from "react-router-dom";
import { searchApi } from "../api";
import type { Item, CategoryNode } from "../types";
import ItemCard from "../components/ItemCard";
import { catApi } from "../api";

export default function Home() {
  const nav = useNavigate();
  const [items, setItems] = useState<Item[]>([]);
  const [loading, setLoading] = useState(true);
  const [topCats, setTopCats] = useState<CategoryNode[]>([]);
  const [hot, setHot] = useState<string[]>([]);
  const [activeCat, setActiveCat] = useState<number | undefined>(undefined);

  useEffect(() => {
    catApi.tree().then((r) => r.code === 0 && setTopCats(r.data));
    searchApi.hot().then((r) => r.code === 0 && setHot(r.data.keywords));
    load(undefined);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function load(cat?: number) {
    setLoading(true);
    searchApi.run({ sort: "relevance", size: 40, category_id: cat })
      .then((r) => {
        if (r.code === 0) setItems(r.data.list);
        else message.warning(r.message);
      })
      .finally(() => setLoading(false));
  }

  function pickCat(cat?: number) {
    setActiveCat(cat);
    load(cat);
  }

  return (
    <div className="idlex-page">
      <div className="hero-banner">
        <h1>闲置不算闲置，遇对人就是宝贝</h1>
        <p>全新二级交易平台：真实认证 · 议价改价 · 资金托管 · 全程可追溯</p>
        <div className="hot-tags">
          {hot.map((k) => (
            <Tag key={k} color="rgba(255,255,255,0.9)" style={{ color: "#ff7a00", cursor: "pointer", fontWeight: 600 }}
              onClick={() => nav(`/search?q=${encodeURIComponent(k)}`)}>
              {k}
            </Tag>
          ))}
        </div>
      </div>

      <div className="cat-bar">
        <span className={`cat-item ${activeCat === undefined ? "active" : ""}`} onClick={() => pickCat(undefined)}>全部</span>
        {topCats.map((c) => (
          <span key={c.value} className={`cat-item ${activeCat === c.value ? "active" : ""}`}
            onClick={() => pickCat(c.value)}>{c.label}</span>
        ))}
      </div>

      <div className="section-title">为你精选优质闲置</div>
      <Row gutter={[16, 16]}>
        {loading
          ? Array.from({ length: 8 }).map((_, i) => (
              <Col key={i} xs={12} sm={12} md={8} lg={6}><Skeleton.Image active style={{ width: "100%", height: 170 }} /><Skeleton active /></Col>
            ))
          : items.map((it) => (
              <Col key={it.itemId} xs={12} sm={12} md={8} lg={6}>
                <ItemCard item={it} />
              </Col>
            ))}
      </Row>
    </div>
  );
}