import { Image, Tag } from "antd";
import { useNavigate } from "react-router-dom";
import type { Item } from "../types";
import { coverUrl, formatPrice } from "../utils";

export default function ItemCard({ item }: { item: Item }) {
  const nav = useNavigate();
  return (
    <div className="card-item" onClick={() => nav(`/item/${item.itemId}`)}>
      <Image
        className="cover"
        preview={false}
        src={coverUrl(item)}
        fallback={coverUrl({ title: item.title })}
        alt={item.title}
      />
      <div style={{ padding: "10px 12px 12px" }}>
        <div className="desc-clamp" style={{ fontSize: 14, lineHeight: 1.4, minHeight: 40 }}>
          {item.title}
        </div>
        <div className="price" style={{ margin: "6px 0 4px" }}>
          {formatPrice(item.price)}
          {item.originPrice ? (
            <span style={{ color: "#bbb", fontSize: 12, fontWeight: 400, marginLeft: 6 }}>
              <s>{formatPrice(item.originPrice)}</s>
            </span>
          ) : null}
        </div>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <span style={{ color: "#999", fontSize: 12 }}>{item.city || "同城"}</span>
          <Tag color="orange" style={{ margin: 0, fontSize: 11 }}>
            {item.conditionText}
          </Tag>
        </div>
      </div>
    </div>
  );
}