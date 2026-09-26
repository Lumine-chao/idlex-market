import axios from "axios";

/** 统一响应结构（后端约定) */
export interface ApiResp<T = unknown> {
  code: number;
  message: string;
  data: T;
}

export const client = axios.create({ baseURL: "/api/v1", timeout: 20000 });

client.interceptors.request.use((config) => {
  // 已显式指定 Authorization（如管理端令牌）时不覆盖，避免用户令牌顶掉管理员令牌
  if (config.headers.Authorization) return config;
  const token = localStorage.getItem("idlex_access");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

/** 登录态失效（401/403）时清理本地凭证并回到登录页，避免页面仍显示为已登录 */
function handleAuthExpired(isAdmin: boolean) {
  if (isAdmin) {
    localStorage.removeItem("idlex_admin_access");
    if (window.location.pathname !== "/admin/login") window.location.replace("/admin/login");
    return;
  }
  localStorage.removeItem("idlex_access");
  localStorage.removeItem("idlex_refresh");
  if (window.location.pathname !== "/login") window.location.replace("/login");
}

client.interceptors.response.use(
  (resp) => resp,
  (error) => {
    // 网络/服务端异常
    const resp = error?.response;
    if (resp) {
      const status = resp.status;
      const headers = (error?.config?.headers || {}) as Record<string, string>;
      const sentToken = !!(headers.Authorization || headers.authorization);
      // 仅当本次请求确实携带令牌时才判定为登录态失效：未登录浏览公开页面被拒不应触发跳转
      if (sentToken && (status === 401 || status === 403)) {
        handleAuthExpired(String(error?.config?.url || "").startsWith("/admin"));
      }
      const body = resp.data;
      if (body && typeof body === "object" && "code" in body) return Promise.reject(body);
      return Promise.reject({ code: status || 500, message: "请求失败，请稍后重试", data: null });
    }
    return Promise.reject({ code: 0, message: "网络异常，请检查服务是否启动", data: null });
  }
);

/** 判断响应是否业务成功 */
export function ok(resp: ApiResp<any> | undefined): boolean {
  return !!resp && resp.code === 0;
}

/** 抛出/返回错误信息（业务错误 message 优先） */
export function errMsg(e: any): string {
  return e?.message || "操作失败，请重试";
}