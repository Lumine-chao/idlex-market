"""扩展检查：覆盖冒烟测试未涉及的流程（订单逆向、评价、举报、会话撤回、管理端处置等）。
仅用于本次排查，可重复运行。"""
import time
import random
import httpx

BASE = "http://127.0.0.1:8000/api/v1"
RESULTS = []


def req(method, path, token=None, **kw):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    r = httpx.request(method, BASE + path, headers=headers, **kw)
    try:
        return r.status_code, r.json()
    except Exception:
        return r.status_code, {"raw": r.text[:200]}


def check(name, cond, detail=""):
    RESULTS.append((name, cond))
    print(("PASS " if cond else "FAIL ") + name + (" | " + str(detail) if detail else ""))


def login(u, p="Abc12345"):
    _, r = req("POST", "/auth/login", json={"username": u, "password": p})
    return r["data"]["accessToken"] if r.get("code") == 0 else None


def new_user():
    uname = "chk%s" % random.randint(10**7, 10**9 - 1)
    _, r = req("POST", "/auth/register", json={
        "username": uname, "password": "Qwer8520",
        "securityQuestion": "您最爱的食物是？", "securityAnswer": "检查账号"})
    return uname, r["data"]["accessToken"]


buyer_name, buyer_tok = new_user()
seller_tok = login("xiaozhou")
admin_tok = None
_, r = req("POST", "/admin/login", json={"username": "admin", "password": "Admin123"})
admin_tok = r["data"]["accessToken"]

_, cats = req("GET", "/categories")
leaf = cats["data"][0]["children"][0]["children"][0]["value"]


def publish(stock=1, price=100.0):
    title = f"检查专用闲置{int(time.time()*1000)%100000000}"
    _, r = req("POST", "/items", token=seller_tok, json={
        "title": title,
        "description": "这是一件用于功能排查的专属闲置商品，描述足够长以满足系统校验要求。",
        "categoryId": leaf, "conditionLevel": 2, "price": price, "originPrice": price * 2,
        "stock": stock, "city": "杭州", "tradeType": 1, "freightPayer": 1, "freight": 0,
        "images": ["/static/61585c692ddd4a02b168471f79c1a24a.jpg"]})
    iid = r["data"]["item"]["itemId"]
    req("POST", f"/admin/items/{iid}/audit", token=admin_tok, json={"approve": True, "reason": ""})
    return iid


def get_addr():
    _, r = req("GET", "/users/addresses", token=buyer_tok)
    if r["data"]:
        return r["data"][0]["id"]
    _, r = req("POST", "/users/addresses", token=buyer_tok, json={
        "receiver": "李四", "phone": "13900000000", "province": "广东省",
        "city": "广州市", "district": "越秀区", "detail": "中山路1号", "is_default": True})
    return r["data"]["id"]


addr_id = get_addr()


def make_order(iid, qty=1):
    _, r = req("POST", "/orders", token=buyer_tok,
               json={"itemId": iid, "quantity": qty, "addressId": addr_id})
    return r


print("=== 1. 订单取消（待付款） ===")
iid = publish()
o = make_order(iid)
no = o["data"]["orderNo"]
_, r = req("POST", f"/orders/{no}/cancel", token=buyer_tok)
check("cancel-pending", r.get("code") == 0 and r["data"]["status"] == "CLOSED", r.get("message"))
_, r = req("POST", f"/orders/{no}/cancel", token=buyer_tok)
check("cancel-again-rejected", r.get("code") != 0, r.get("message"))
_, r = req("DELETE", f"/orders/{no}", token=buyer_tok)
check("delete-closed-order", r.get("code") == 0, r.get("message"))

print("=== 2. 退款流程 + 库存恢复 ===")
iid = publish(stock=1)
_, orig = req("GET", f"/items/{iid}")
orig_stock = orig["data"]["stock"]
o = make_order(iid)
no = o["data"]["orderNo"]
req("POST", f"/orders/{no}/pay", token=buyer_tok, json={"channel": "MOCK"})
_, paid = req("GET", f"/items/{iid}")
check("pay-deducts-stock", paid["data"]["stock"] == orig_stock - 1,
      f"下单前stock={orig_stock} 支付后stock={paid['data']['stock']}")
_, r = req("POST", f"/orders/{no}/refund", token=buyer_tok, json={"reason": "不想要了"})
check("refund-apply", r.get("code") == 0 and r["data"]["status"] == "REFUNDING", r.get("message"))
_, r = req("POST", f"/orders/{no}/refund/agree", token=seller_tok)
check("refund-agree", r.get("code") == 0 and r["data"]["status"] == "REFUNDED", r.get("message"))
_, after = req("GET", f"/items/{iid}")
check("refund-restores-stock", after["data"]["stock"] == orig_stock,
      f"下单前stock={orig_stock} 退款后stock={after['data']['stock']}")
check("refund-restores-status", after["data"]["status"] == 3,
      f"退款后商品status={after['data']['status']}（3=在售）")

print("=== 3. 发货 -> 确认收货 -> 评价 ===")
iid = publish(stock=1)
o = make_order(iid)
no = o["data"]["orderNo"]
_, payr = req("POST", f"/orders/{no}/pay", token=buyer_tok, json={"channel": "MOCK"})
_, r = req("POST", f"/orders/{no}/ship", token=seller_tok,
           json={"logisticsCompany": "顺丰", "trackingNo": "SF123456"})
check("ship", r.get("code") == 0 and r["data"]["status"] == "SHIPPED", r.get("message"))
_, r = req("POST", f"/orders/{no}/confirm", token=buyer_tok)
check("confirm", r.get("code") == 0 and r["data"]["status"] == "COMPLETED", r.get("message"))
_, od = req("GET", f"/orders/{no}", token=buyer_tok)
order_id = od["data"]["orderId"]
seller_id = od["data"]["sellerId"]
http, r = req("POST", "/reviews", token=buyer_tok,
              json={"orderId": order_id, "targetId": seller_id, "score": 5,
                    "tags": "描述相符", "content": "卖家很好"})
check("submit-review", r.get("code") == 0, f"http={http} code={r.get('code')} {r.get('message')}")
if r.get("code") == 0:
    http, r2 = req("POST", "/reviews", token=buyer_tok,
                   json={"orderId": order_id, "targetId": seller_id, "score": 4,
                         "content": "改成4星"})
    check("modify-review-once", r2.get("code") == 0 and r2["data"]["isModified"], r2.get("message"))
    http, r3 = req("POST", "/reviews", token=buyer_tok,
                   json={"orderId": order_id, "targetId": seller_id, "score": 3,
                         "content": "再改"})
    check("modify-review-limit", r3.get("code") == 6003, f"code={r3.get('code')} {r3.get('message')}")
http, r = req("GET", f"/reviews?targetId={seller_id}")
check("list-reviews", r.get("code") == 0 and r["data"]["count"] >= 1,
      f"http={http} code={r.get('code')} count={r.get('data', {}).get('count')}")
http, r = req("GET", f"/reviews?itemId={iid}")
check("list-reviews-by-item", r.get("code") == 0 and r["data"]["count"] >= 1,
      f"http={http} code={r.get('code')} count={r.get('data', {}).get('count')}")

print("=== 4. 争议 -> 管理端干预退款 ===")
iid = publish(stock=1)
_, orig = req("GET", f"/items/{iid}")
orig_stock = orig["data"]["stock"]
o = make_order(iid)
no = o["data"]["orderNo"]
req("POST", f"/orders/{no}/pay", token=buyer_tok, json={"channel": "MOCK"})
req("POST", f"/orders/{no}/ship", token=seller_tok,
    json={"logisticsCompany": "中通", "trackingNo": "ZT999"})
_, r = req("POST", f"/orders/{no}/dispute", token=buyer_tok, json={"reason": "货不对板"})
check("dispute", r.get("code") == 0 and r["data"]["status"] == "DISPUTING", r.get("message"))
_, r = req("POST", f"/admin/orders/{no}/intervene", token=admin_tok,
           json={"action": "refund", "reason": "判定买家胜诉"})
check("admin-intervene-refund", r.get("code") == 0 and r["data"]["status"] == "REFUNDED", r.get("message"))
_, after = req("GET", f"/items/{iid}")
check("admin-refund-restores-stock", after["data"]["stock"] == orig_stock,
      f"下单前stock={orig_stock} 干预后stock={after['data']['stock']}")

print("=== 5. 消息撤回 ===")
iid = publish()
_, r = req("POST", "/conversations", token=buyer_tok, json={"itemId": iid})
conv_id = r["data"]["conversationId"]
_, r = req("POST", "/messages", token=buyer_tok,
           json={"conversationId": conv_id, "content": "第一条：稍后要撤回"})
mid = r["data"]["id"]
req("POST", "/messages", token=buyer_tok,
    json={"conversationId": conv_id, "content": "第二条：保留"})
http, r = req("POST", f"/messages/{mid}/recall", token=buyer_tok)
check("recall-message", r.get("code") == 0, f"http={http} code={r.get('code')} {r.get('message')}")

print("=== 6. 会话未读与分页 total ===")
_, r = req("GET", "/conversations", token=seller_tok)
mine = [c for c in r["data"]["list"] if c["conversationId"] == conv_id]
check("conv-visible-to-seller", len(mine) == 1, f"找到={len(mine)}")
# 共 2 条来自买家的消息，其中 1 条已撤回；撤回消息不应计入未读
check("unread-before-open", mine and mine[0]["unreadCount"] == 1,
      f"unread={mine[0]['unreadCount'] if mine else 'N/A'} 期望=1（已撤回的不计未读）")
_, r = req("GET", f"/conversations/{conv_id}/messages?page=1&size=1", token=seller_tok)
check("history-total-is-all", r["data"]["total"] == 2 and len(r["data"]["list"]) == 1,
      f"total={r['data']['total']} 本页条数={len(r['data']['list'])} 期望 total=2 本页=1")
_, r = req("GET", "/conversations", token=seller_tok)
mine = [c for c in r["data"]["list"] if c["conversationId"] == conv_id]
check("unread-cleared-after-open", mine and mine[0]["unreadCount"] == 0,
      f"unread={mine[0]['unreadCount'] if mine else 'N/A'} 期望=0")

print("=== 7. 举报（含凭证） ===")
http, r = req("POST", "/reports", token=buyer_tok,
              json={"targetType": "item", "targetId": iid, "reasonType": "虚假描述",
                    "description": "描述与实际不符",
                    "evidence": ["/static/61585c692ddd4a02b168471f79c1a24a.jpg"]})
check("report-with-evidence", r.get("code") == 0, f"http={http} code={r.get('code')} {r.get('message')}")
_, r = req("GET", "/reports/mine", token=buyer_tok)
check("my-reports", r.get("code") == 0 and r["data"]["total"] >= 1, f"total={r['data'].get('total')}")
if r.get("code") == 0 and r["data"]["total"] >= 1:
    rid = r["data"]["list"][0]["id"]
    _, r = req("POST", f"/admin/reports/{rid}/handle", token=admin_tok,
               json={"approve": True, "reason": "举报成立"})
    check("admin-handle-report", r.get("code") == 0, r.get("message"))

print("=== 8. 收藏与足迹 ===")
_, r = req("POST", "/favorites", token=buyer_tok, json={"itemId": iid})
check("toggle-favorite-on", r.get("code") == 0 and r["data"]["favorited"], r.get("message"))
_, r = req("GET", "/users/favorites", token=buyer_tok)
check("list-favorites", r.get("code") == 0 and r["data"]["total"] >= 1, f"total={r['data'].get('total')}")
_, r = req("POST", "/footprints", token=buyer_tok, json={"itemId": iid})
check("record-footprint", r.get("code") == 0, r.get("message"))
_, r = req("GET", "/users/footprints", token=buyer_tok)
check("list-footprints", r.get("code") == 0 and len(r["data"]["list"]) >= 1, "")

print("=== 9. 商品编辑/上下架/删除 ===")
iid = publish()
_, r = req("PUT", f"/items/{iid}", token=seller_tok, json={
    "title": "编辑后的检查商品标题", "description": "编辑后的描述内容，长度依然满足系统校验要求。",
    "categoryId": leaf, "conditionLevel": 3, "price": 88.0, "stock": 2, "city": "杭州",
    "tradeType": 1, "freightPayer": 1, "freight": 0,
    "images": ["/static/61585c692ddd4a02b168471f79c1a24a.jpg"]})
check("edit-item", r.get("code") == 0, r.get("message"))
_, det = req("GET", f"/items/{iid}")
check("edit-item-images-ok", all(u for u in det["data"]["images"]), f"images={det['data']['images']}")
req("POST", f"/admin/items/{iid}/audit", token=admin_tok, json={"approve": True, "reason": ""})
_, r = req("POST", f"/items/{iid}/status", token=seller_tok, json={"action": "off_sale"})
check("off-sale", r.get("code") == 0 and r["data"]["status"] == 4, r.get("message"))
_, r = req("POST", f"/items/{iid}/status", token=seller_tok, json={"action": "on_sale"})
check("on-sale", r.get("code") == 0 and r["data"]["status"] == 3, r.get("message"))
_, r = req("POST", f"/items/{iid}/status", token=seller_tok, json={"action": "delete"})
check("delete-item", r.get("code") == 0, r.get("message"))

print("=== 10. 搜索筛选/排序 ===")
_, r = req("GET", "/search?q=iPhone&sort=price_asc&size=20")
check("search-sort-asc", r.get("code") == 0, r.get("message"))
prices = [i["price"] for i in r["data"]["list"]]
check("search-sort-asc-ordered", prices == sorted(prices), f"prices={prices[:5]}")
_, r = req("GET", "/search?min_price=99999&max_price=1")
check("search-price-range-invalid", r.get("code") == 3002, f"code={r.get('code')} {r.get('message')}")
_, r = req("GET", "/search?q=" + "x" * 60)
check("search-keyword-too-long", r.get("code") == 3001, f"code={r.get('code')} {r.get('message')}")
_, r = req("GET", "/search/suggest?q=iPhone")
check("search-suggest", r.get("code") == 0, r.get("message"))

print("=== 11. 管理端用户处置 ===")
_, r = req("GET", "/admin/users", token=admin_tok)
check("admin-users", r.get("code") == 0 and len(r["data"]["list"]) >= 1, "")
target = [u for u in r["data"]["list"] if u["username"] == buyer_name]
if target:
    uid = target[0]["id"]
    _, r = req("POST", f"/admin/users/{uid}/action", token=admin_tok,
               json={"action": "ban_publish", "reason": "违规发布"})
    check("admin-ban-publish", r.get("code") == 0 and r["data"]["status"] == 3, r.get("message"))
    _, r = req("POST", "/items", token=buyer_tok, json={
        "title": "被限制发布后尝试发布", "description": "该用户已被禁用发布权限，此请求应当被拒绝。",
        "categoryId": leaf, "conditionLevel": 2, "price": 10.0, "stock": 1, "city": "广州",
        "tradeType": 1, "freightPayer": 1, "freight": 0,
        "images": ["/static/61585c692ddd4a02b168471f79c1a24a.jpg"]})
    check("publish-banned-enforced", r.get("code") == 1105, f"code={r.get('code')} {r.get('message')}")
    req("POST", f"/admin/users/{uid}/action", token=admin_tok,
        json={"action": "unpublish_ban", "reason": "恢复"})
else:
    check("admin-ban-publish", False, "未找到测试买家")

print("=== 12. 敏感词维护 ===")
_, r = req("POST", "/admin/sensitive-words", token=admin_tok,
           json={"word": "排查测试词", "level": "BLOCK", "status": 1})
check("add-sensitive-word", r.get("code") == 0, r.get("message"))
wid = r["data"]["id"] if r.get("code") == 0 else None
_, r = req("POST", "/items", token=seller_tok, json={
    "title": "排查测试词出现在标题里", "description": "该商品标题包含刚新增的敏感词，应被拦截。",
    "categoryId": leaf, "conditionLevel": 2, "price": 10.0, "stock": 1, "city": "杭州",
    "tradeType": 1, "freightPayer": 1, "freight": 0,
    "images": ["/static/61585c692ddd4a02b168471f79c1a24a.jpg"]})
check("sensitive-word-effective", r.get("code") == 2006, f"code={r.get('code')} {r.get('message')}")
if wid:
    req("DELETE", f"/admin/sensitive-words/{wid}", token=admin_tok)

print()
failed = [n for n, ok in RESULTS if not ok]
print(f"==== 汇总：{len(RESULTS) - len(failed)}/{len(RESULTS)} 通过 ====")
if failed:
    print("未通过：")
    for n in failed:
        print("  - " + n)