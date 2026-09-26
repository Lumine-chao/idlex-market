// 与后端一致的领域类型定义

export interface Seller {
  id: number;
  username: string;
  avatar?: string | null;
  city?: string | null;
  creditLevel: number;
}

export interface Item {
  itemId: number;
  title: string;
  description: string;
  categoryId: number;
  conditionLevel: number;
  conditionText: string;
  price: number;
  originPrice?: number | null;
  stock: number;
  city?: string;
  tradeType: number;
  freightPayer: number;
  freight: number;
  status: number;
  viewCount: number;
  coverUrl?: string | null;
  images: string[];
  seller: Seller;
  createdAt?: string | null;
}

export interface CategoryNode {
  value: number;
  label: string;
  children?: CategoryNode[];
}

export interface Conversation {
  conversationId: number;
  itemId: number;
  itemTitle: string;
  cover: string;
  other?: Seller;
  lastMessage?: string;
  lastMessageAt?: string;
  unreadCount: number;
}

export interface ChatMessage {
  id: number;
  conversationId: number;
  senderId: number;
  msgType: string;
  content: string;
  seq: number;
  createdAt?: string;
  revoked: boolean;
  sender?: Seller;
}

export interface Address {
  id: number;
  receiver: string;
  phone: string;
  province: string;
  city: string;
  district: string;
  detail: string;
  isDefault: boolean;
}

export type OrderStatus =
  | "PENDING_PAYMENT"
  | "PAID"
  | "SHIPPED"
  | "COMPLETED"
  | "CLOSED"
  | "REFUNDING"
  | "REFUNDED"
  | "DISPUTING";

export const ORDER_STATUS_TEXT: Record<OrderStatus, string> = {
  PENDING_PAYMENT: "待付款",
  PAID: "待发货",
  SHIPPED: "已发货",
  COMPLETED: "已完成",
  CLOSED: "已关闭",
  REFUNDING: "退款中",
  REFUNDED: "已退款",
  DISPUTING: "争议中",
};

export interface OrderItem {
  orderNo: string;
  orderId: number;
  buyerId: number;
  sellerId: number;
  itemId: number;
  itemTitle: string;
  cover: string;
  unitPrice: number;
  quantity: number;
  freight: number;
  totalAmount: number;
  status: OrderStatus;
  statusText: string;
  logisticsCompany?: string;
  trackingNo?: string;
  createdAt?: string;
  paidAt?: string;
  shippedAt?: string;
  intervenedAt?: string | null;
  interveneAction?: string | null;
  interveneReason?: string | null;
}

export interface OrderDetail extends OrderItem {
  itemSnapshot: Record<string, unknown>;
  addressSnapshot: {
    receiver: string;
    phone: string;
    province: string;
    city: string;
    district: string;
    detail: string;
  };
  payExpireAt?: string;
  timeline: {
    fromStatus?: string;
    toStatus: string;
    action: string;
    operatorType: string;
    remark?: string;
    time?: string;
  }[];
}

export interface Review {
  id: number;
  orderId: number;
  reviewerId: number;
  targetId: number;
  score: number;
  tags?: string;
  content?: string;
  reviewerName?: string;
  createdAt?: string;
}

export interface Paginated<T> {
  list: T[];
  total: number;
  page: number;
  size: number;
}

export interface UserMe {
  id: number;
  username: string;
  avatar?: string | null;
  city?: string | null;
  creditLevel: number;
}

export const ITEM_STATUS_TEXT: Record<number, string> = {
  2: "待审核",
  3: "在售",
  4: "已下架",
  5: "已售出",
  6: "审核驳回",
};

export const CONDITION_TEXT: Record<number, string> = {
  1: "全新",
  2: "几乎全新",
  3: "轻微使用痕迹",
  4: "明显使用痕迹",
};

export const TRADE_TYPE_TEXT: Record<number, string> = {
  1: "同城面交",
  2: "邮寄",
};