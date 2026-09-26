import { client, ApiResp } from "./client";
import type {
  Address,
  CategoryNode,
  ChatMessage,
  Conversation,
  Item,
  OrderDetail,
  OrderItem,
  Review,
  UserMe,
  Paginated,
} from "../types";

async function post<T>(url: string, body?: unknown): Promise<ApiResp<T>> {
  return (await client.post(url, body)).data;
}
async function get<T>(url: string, params?: unknown): Promise<ApiResp<T>> {
  return (await client.get(url, { params })).data;
}
async function put<T>(url: string, body?: unknown): Promise<ApiResp<T>> {
  return (await client.put(url, body)).data;
}
async function del<T>(url: string): Promise<ApiResp<T>> {
  return (await client.delete(url)).data;
}

/* ---------- 账号 ---------- */
export const authApi = {
  securityQuestions: () => get<{ questions: string[] }>("/auth/security-questions"),
  register: (p: {
    username: string;
    password: string;
    securityQuestion: string;
    securityAnswer: string;
  }) =>
    post<{ accessToken: string; refreshToken: string; expiresIn: number }>("/auth/register", p),
  login: (p: { username: string; password: string }) =>
    post<{ accessToken: string; refreshToken: string; expiresIn: number }>("/auth/login", p),
  resetPassword: (p: {
    username: string;
    securityQuestion: string;
    securityAnswer: string;
    newPassword: string;
  }) => post("/auth/password/reset", p),
  logout: (p: { refreshToken: string }) => post("/auth/logout", p),
};

export const adminApi = {
  login: (p: { username: string; password: string }) =>
    post<{ accessToken: string; refreshToken: string; expiresIn: number; username: string }>(
      "/admin/login",
      p
    ),
};

/* ---------- 分类 / 检索 ---------- */
export const catApi = {
  tree: () => get<CategoryNode[]>("/categories"),
};

export const searchApi = {
  run: (params: Record<string, unknown>) =>
    get<Paginated<Item>>("/search", params),
  suggest: (q: string) => get<{ keywords: string[]; categories: { id: number; name: string }[] }>("/search/suggest", { q }),
  hot: () => get<{ keywords: string[] }>("/search/hot"),
};

/* ---------- 用户 ---------- */
export const userApi = {
  me: () => get<UserMe>("/users/me"),
  updateMe: (p: Partial<Pick<UserMe, "avatar" | "city">>) =>
    put<UserMe>("/users/me", p),
  addresses: () => get<Address[]>("/users/addresses"),
  addAddress: (p: Omit<Address, "id">) => post<{ id: number }>("/users/addresses", p),
  updateAddress: (id: number, p: Omit<Address, "id">) =>
    put<{ id: number }>(`/users/addresses/${id}`, p),
  deleteAddress: (id: number) => del(`/users/addresses/${id}`),
  favorites: () => get<Paginated<Item>>("/users/favorites"),
  footprints: () => get<Paginated<Item>>("/users/footprints"),
  clearFootprints: () => del("/users/footprints"),
};

/* ---------- 商品 ---------- */
export interface ItemCreateInput {
  title: string;
  description: string;
  categoryId: number;
  conditionLevel: number;
  price: number;
  originPrice?: number | null;
  stock: number;
  city: string;
  tradeType: number;
  freightPayer: number;
  freight: number;
  images: string[];
}

export const itemApi = {
  create: (p: ItemCreateInput) => post<{ item: Item }>("/items", p),
  update: (id: number, p: ItemCreateInput) => put<{ item: Item }>(`/items/${id}`, p),
  detail: (id: number) => get<Item>(`/items/${id}`),
  mine: (status?: number) => get<Paginated<Item>>("/items/mine", { status }),
  status: (id: number, action: "on_sale" | "off_sale" | "delete") =>
    post<{ itemId: number; status: number }>(`/items/${id}/status`, { action }),
  toggleFavorite: (itemId: number) => post<{ favorited: boolean }>("/favorites", { itemId }),
  footprint: (itemId: number) => post("/footprints", { itemId }),
};

export const uploadApi = {
  upload: async (file: File): Promise<string> => {
    const form = new FormData();
    form.append("file", file);
    const token = localStorage.getItem("idlex_access");
    const resp = await client.post("/uploads/upload", form, {
      headers: {
        "Content-Type": "multipart/form-data",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
    });
    const body = resp.data;
    // 后端业务失败时 data 为 null，直接取 url 会抛出 "Cannot read property 'url' of null"
    if (!body || body.code !== 0 || !body.data?.url) {
      throw new Error(body?.message || "图片上传失败，请重试");
    }
    return body.data.url;
  },
};

/* ---------- 会话 / 消息 ---------- */
export const imApi = {
  conversations: () => get<{ list: Conversation[]; total: number }>("/conversations"),
  create: (itemId: number) =>
    post<{ conversationId: number; itemId: number; sellerId: number }>("/conversations", {
      itemId,
    }),
  history: (convId: number, page = 1, size = 30) =>
    get<{ list: ChatMessage[]; total: number; page: number; size: number }>(
      `/conversations/${convId}/messages`,
      { page, size }
    ),
  send: (conversationId: number, content: string, msgType = "TEXT") =>
    post<ChatMessage>("/messages", { conversationId, content, msgType }),
  recall: (messageId: number) => post(`/messages/${messageId}/recall`),
};

/* ---------- 订单 ---------- */
export const orderApi = {
  create: (p: { itemId: number; quantity: number; addressId: number }) =>
    post<{ orderNo: string; totalAmount: number; status: string }>("/orders", p),
  list: (role: "buy" | "sell", status?: string, page = 1, size = 20) =>
    get<{ list: OrderItem[]; total: number; page: number; size: number }>("/orders", {
      role,
      status,
      page,
      size,
    }),
  detail: (orderNo: string) => get<OrderDetail>(`/orders/${orderNo}`),
  pay: (orderNo: string, channel = "MOCK") =>
    post<{ orderNo: string; status: string }>(`/orders/${orderNo}/pay`, { channel }),
  cancel: (orderNo: string) => post(`/orders/${orderNo}/cancel`),
  ship: (orderNo: string, logisticsCompany: string, trackingNo: string) =>
    post(`/orders/${orderNo}/ship`, { logisticsCompany, trackingNo }),
  confirm: (orderNo: string) => post(`/orders/${orderNo}/confirm`),
  refund: (orderNo: string, reason: string) => post(`/orders/${orderNo}/refund`, { reason }),
  refundAgree: (orderNo: string) => post(`/orders/${orderNo}/refund/agree`),
  dispute: (orderNo: string, reason: string) => post(`/orders/${orderNo}/dispute`, { reason }),
  remove: (orderNo: string) => del(`/orders/${orderNo}`),
};

/* ---------- 评价 / 举报 ---------- */
export const reviewApi = {
  submit: (p: { orderId: number; targetId: number; score: number; tags?: string; content?: string }) =>
    post<Review>("/reviews", p),
  // 商品详情页按商品查评价；卖家主页按被评价人（targetId）查
  listByItem: (itemId: number, rating = "all") =>
    get<{ list: Review[]; avgScore: number; count: number }>("/reviews", { itemId, rating }),
  list: (targetId: number, rating = "all") =>
    get<{ list: Review[]; avgScore: number; count: number }>("/reviews", { targetId, rating }),
};

export const reportApi = {
  submit: (p: {
    targetType: string;
    targetId: number;
    reasonType: string;
    description?: string;
    evidence?: string[];
  }) => post("/reports", p),
  mine: () => get<{ list: unknown[]; total: number }>("/reports/mine"),
};

/* ---------- 管理端（使用独立 admin token） ---------- */
function adminHeaders() {
  return { Authorization: `Bearer ${localStorage.getItem("idlex_admin_access")}` };
}

export const adminUserApi = {
  dashboard: () => adminGet<DashboardData>("/admin/dashboard"),
  items: (params?: Record<string, unknown>) => adminGet<{ list: Item[] }>("/admin/items", params),
  audit: (itemId: number, approve: boolean, reason?: string) =>
    adminPost(`/admin/items/${itemId}/audit`, { approve, reason }),
  users: (keyword?: string) => adminGet<{ list: AdminUserRow[] }>("/admin/users", { keyword }),
  userAction: (userId: number, action: string, reason: string) =>
    adminPost(`/admin/users/${userId}/action`, { action, reason }),
  orders: (status?: string) => adminGet<{ list: OrderItem[] }>("/admin/orders", { status }),
  intervene: (orderNo: string, action: string, reason: string) =>
    adminPost(`/admin/orders/${orderNo}/intervene`, { action, reason }),
  deleteOrder: (orderNo: string) => adminDel(`/admin/orders/${orderNo}`),
  reports: (params?: Record<string, unknown>) =>
    adminGet<{ list: AdminReportRow[] }>("/admin/reports", params),
  handleReport: (reportId: number, approve: boolean, reason: string) =>
    adminPost(`/admin/reports/${reportId}/handle`, { approve, reason }),
  sensitiveWords: () => adminGet<{ list: { id: number; word: string; level: string; status: number }[] }>("/admin/sensitive-words"),
  addSensitive: (word: string) => adminPost("/admin/sensitive-words", { word }),
  delSensitive: (wordId: number) => adminDel(`/admin/sensitive-words/${wordId}`),
};

export interface DashboardData {
  users: number;
  items: number;
  onSale: number;
  orders: number;
  todayOrders: number;
  amount: number;
  pendingAudit: number;
  pendingReport: number;
}

export interface AdminUserRow {
  id: number;
  username: string;
  phone?: string;
  city?: string;
  creditLevel: number;
  status: number;
  createdAt?: string;
}

export interface AdminReportRow {
  id: number;
  targetType: string;
  targetId: number;
  reasonType: string;
  description?: string;
  status: number;
  result?: string;
  createdAt?: string;
}

/* client 的 baseURL 已包含 /api/v1，此处不要再拼前缀 */
export async function adminGet<T = unknown>(path: string, params?: unknown): Promise<ApiResp<T>> {
  return (await client.get(path, { params, headers: adminHeaders() })).data;
}
export async function adminPost<T = unknown>(path: string, body?: unknown): Promise<ApiResp<T>> {
  return (await client.post(path, body, { headers: adminHeaders() })).data;
}
export async function adminDel<T = unknown>(path: string): Promise<ApiResp<T>> {
  return (await client.delete(path, { headers: adminHeaders() })).data;
}