"""端到端冒烟测试：注册 -> 发布 -> 搜索 -> 会话 -> 下单 -> 支付 -> 详情。
不消耗演示商品（卖家自建专属测试闲置），可重复运行。"""
import time
import random
import httpx

BASE = "http://127.0.0.1:8000/api/v1"


def req(method, path, token=None, **kw):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    r = httpx.request(method, BASE + path, headers=headers, **kw)
    return r.json()


def check(name, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + name + (" " + detail if detail else ""))


def random_username():
    return "smoke%s" % str(random.randint(10**7, 10**9 - 1))


# 1. 注册新用户（用户名 + 密保）
username = random_username()
reg = req("POST", "/auth/register", json={
    "username": username, "password": "Qwer8520",
    "securityQuestion": "您最爱的食物是？", "securityAnswer": "冒烟测试"}
)
check("register", reg["code"] == 0, str(reg.get("code")))

# 1.1 密保找回密码
reset = req("POST", "/auth/password/reset", json={
    "username": username, "securityQuestion": "您最爱的食物是？",
    "securityAnswer": "冒烟测试", "newPassword": "Zxcv7531p"})
check("reset-password", reset["code"] == 0, reset.get("message", ""))

# 2. 密码登录
login = req("POST", "/auth/login", json={"username": "xianzhidaren", "password": "Abc12345"})
check("login", login["code"] == 0, str(login.get("code")))
tok = login["data"]["accessToken"]

# 3. 错误密码提示
bad = req("POST", "/auth/login", json={"username": "xianzhidaren", "password": "wrongpw123"})
check("bad-password-msg", bad["message"] == "用户名或密码错误，请重试", bad.get("message"))

# 4. 当前用户
me = req("GET", "/users/me", token=tok)
check("me-username", me["data"]["username"] == "xianzhidaren", me["data"]["username"])

# 5. 分类
cats = req("GET", "/categories")
check("categories", len(cats["data"]) == 6, f"L1={len(cats['data'])}")

# 6. 卖家登录并发布专属测试商品
slog = req("POST", "/auth/login", json={"username": "xiaozhou", "password": "Abc12345"})
stok = slog["data"]["accessToken"]
leaf_cat = cats["data"][0]["children"][0]["children"][0]["value"]
title = f"冒烟测试专属闲置{int(time.time())}"
pub = req("POST", "/items", token=stok, json={
    "title": title, "description": "这是一件供端到端冒烟测试自动发布的专属闲置商品，描述足够长满足系统校验要求。", 
    "categoryId": leaf_cat, "conditionLevel": 2, "price": 199.0, "originPrice": 399.0,
    "stock": 1, "city": "杭州", "tradeType": 1, "freightPayer": 1, "freight": 0,
    "images": ["/static/61585c692ddd4a02b168471f79c1a24a.jpg"]})
check("publish-item", pub["code"] == 0, str(pub.get("code")) + pub.get("message", ""))
item_id = pub["data"]["item"]["itemId"]
check("publish-pending-audit", pub["data"]["item"]["status"] == 2,
      f"status={pub['data']['item']['status']}")

# 6.1 未审核前不可见，且卖家不能绕过审核自行上架
pre = req("GET", "/search?q=" + title)
check("not-visible-before-audit", pre["data"]["total"] == 0, f"total={pre['data']['total']}")
bypass = req("POST", f"/items/{item_id}/status", token=stok, json={"action": "on_sale"})
check("audit-bypass-blocked", bypass["code"] != 0, str(bypass.get("code")))

# 6.2 管理员登录并审核通过
admlog = req("POST", "/admin/login", json={"username": "admin", "password": "Admin123"})
check("admin-login", admlog["code"] == 0, str(admlog.get("code")))
adm_tok = admlog["data"]["accessToken"]
aud = req("POST", f"/admin/items/{item_id}/audit", token=adm_tok,
          json={"approve": True, "reason": ""})
check("admin-audit", aud["code"] == 0, str(aud.get("code")))

# 7. 搜索该测试商品（买家视角）
sr = req("GET", "/search?q=" + title)
check("search", sr["data"]["total"] >= 1, f"total={sr['data']['total']}")

# 8. 商品详情
det = req("GET", f"/items/{item_id}")
check("item-detail", det["code"] == 0 and det["data"]["title"], det.get("message", ""))

# 9. 联系卖家 -> 会话
conv = req("POST", "/conversations", token=tok, json={"itemId": item_id})
check("create-conversation", conv["code"] == 0, str(conv.get("code")))
conv_id = conv["data"]["conversationId"]

# 10. 发消息
send = req("POST", "/messages", token=tok,
           json={"conversationId": conv_id, "content": "你好，还能便宜点吗"})
check("send-message", send["code"] == 0, str(send.get("code")))

# 11. 会话列表
convs = req("GET", "/conversations", token=tok)
check("conversation-list", len(convs["data"]["list"]) >= 1)

# 12. 敏感词拦截
sen = req("POST", "/messages", token=tok,
          json={"conversationId": conv_id, "content": "来，我们加微信刷单返利吧"})
check("sensitive-block", sen["code"] == 4002, sen.get("message", ""))

# 13. 地址 + 下单 + 支付
addr = req("POST", "/users/addresses", token=tok,
           json={"receiver": "张三", "phone": "13800000000", "province": "广东省",
                 "city": "广州市", "district": "天河区", "detail": "珠江新城", "is_default": True})
check("create-address", addr["code"] == 0, str(addr.get("code")))
addr_list = req("GET", "/users/addresses", token=tok)
addr_id = addr_list["data"][0]["id"]
order = req("POST", "/orders", token=tok,
            json={"itemId": item_id, "quantity": 1, "addressId": addr_id})
check("create-order", order["code"] == 0, order.get("message", ""))
if order["code"] == 0:
    order_no = order["data"]["orderNo"]
    pay = req("POST", f"/orders/{order_no}/pay", token=tok, json={"channel": "MOCK"})
    check("pay", pay["code"] == 0, pay.get("message", ""))
    od = req("GET", f"/orders/{order_no}", token=tok)
    check("order-detail-status", od["data"]["status"] == "PAID", od["data"]["status"])
    check("order-timeline", len(od["data"]["timeline"]) >= 2,
          f"timeline={len(od['data']['timeline'])}")

# 14. 未登录访问受保护接口（应返回 401 + 业务错误码）
with httpx.Client(base_url=BASE) as c:
    r = c.get("/users/me")
    body = r.json()
    check("auth-guard", r.status_code == 401 and body.get("code") != 0,
          f"http={r.status_code} code={body.get('code')}")

# 15. 管理端接口鉴权与数据看板/举报列表
dash = req("GET", "/admin/dashboard", token=adm_tok)
check("admin-dashboard", dash["code"] == 0 and dash["data"]["users"] >= 1,
      f"code={dash.get('code')} users={dash.get('data', {}).get('users')}")
reps = req("GET", "/admin/reports", token=adm_tok)
check("admin-reports", reps["code"] == 0, f"code={reps.get('code')}")
# 用户令牌不能访问管理端接口
cross = req("GET", "/admin/dashboard", token=tok)
check("admin-token-isolation", cross["code"] != 0, f"code={cross.get('code')}")