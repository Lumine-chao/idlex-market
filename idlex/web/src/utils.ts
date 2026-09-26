// 商品封面：有真实图用真实图，否则用按标题生成的插画（trae-api）
export function coverUrl(item: { coverUrl?: string | null; title?: string }, size = "landscape_4_3"): string {
  if (item.coverUrl) return item.coverUrl;
  const prompt = encodeURIComponent(
    `扁平插画风格的商品主图，主题：${item.title || "闲置好物"}，干净浅色背景，柔和光影，电商展示图`
  );
  return `https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt=${prompt}&image_size=${size}`;
}

/** <img> 加载失败时换成按标题生成的插画；对同一地址不重复赋值，避免 onError 循环 */
export function fallbackCover(el: HTMLImageElement, title?: string, size = "landscape_4_3"): void {
  const fb = coverUrl({ title }, size);
  if (el.src !== fb) el.src = fb;
}

export function formatPrice(n: number): string {
  return `¥${n.toLocaleString("zh-CN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export function timeAgo(iso?: string | null): string {
  if (!iso) return "";
  const t = new Date(iso).getTime();
  if (Number.isNaN(t)) return "";
  const diff = Date.now() - t;
  const m = Math.floor(diff / 60000);
  if (m < 1) return "刚刚";
  if (m < 60) return `${m}分钟前`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}小时前`;
  const d = Math.floor(h / 24);
  if (d < 30) return `${d}天前`;
  return iso.slice(0, 10);
}

const _ASC = "0123456789abcdefghijklmnopqrstuvwxyz";
const _DESC = _ASC.split("").reverse().join("");

/** 与后端一致的密码规则校验：返回错误提示，校验通过返回 null */
export function passwordError(pw: string, username?: string): string | null {
  if (!pw) return "请设置密码";
  if (pw.length < 8 || pw.length > 20) return "密码为8~20位";
  if (!/[A-Za-z]/.test(pw) || !/\d/.test(pw)) return "需同时包含字母与数字";
  if (username && pw === username) return "密码不能与用户名相同";
  if (/(.)\1{3,}/.test(pw)) return "不能包含 4 个以上连续重复的字符";
  const low = pw.toLowerCase();
  for (let i = 0; i <= low.length - 4; i++) {
    const seg = low.slice(i, i + 4);
    if (_ASC.includes(seg) || _DESC.includes(seg)) return "不能包含连续字符（如 1234、abcd）";
  }
  return null;
}