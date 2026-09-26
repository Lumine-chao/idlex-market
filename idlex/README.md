# 闲置易 · 二手交易平台

一个可本地一键跑起来的全栈二手交易平台 Demo。覆盖**注册 → 发布 → 搜索 → 聊天 → 下单 → 支付 → 发货 → 收货 → 评价**的完整业务闭环，并带管理后台。严格遵循《项目说明文档》与《技术架构文档》中的业务规则、订单状态机、错误码与中文提示。

## 技术栈

| 端 | 技术 |
| --- | --- |
| 后端 | Python 3.11 · FastAPI · SQLAlchemy(Async) · SQLite(aiosqlite) · PyJWT · Argon2 |
| 前端 | React 18 · TypeScript · Vite · Ant Design 5 · Zustand · React Router 6 |
| 实时通信 | WebSocket（卖家/买家即时消息 + 未读推送） |

## 目录结构

```
idlex/
├── backend/
│   ├── app/
│   │   ├── main.py            # 应用入口（业务路由 + 静态/前端产物托管）
│   │   ├── config.py          # 配置
│   │   ├── db.py              # SQLAlchemy 异步引擎
│   │   ├── models.py          # 数据模型（用户/商品/分类/订单/会话/消息/评价/举报…）
│   │   ├── schemas.py         # Pydantic 请求模型（camelCase / snake_case 双兼容）
│   │   ├── serializers.py     # 实体 -> 响应 JSON
│   │   ├── state_machine.py   # 订单状态机（禁止非法跳动 + 留痕）
│   │   ├── stock.py           # 库存内存锁（防超卖）
│   │   ├── sensitive.py       # DFA 敏感词过滤
│   │   ├── ws.py              # WebSocket 连接管理
│   │   ├── auth.py · deps.py  # JWT 双令牌 / 依赖注入与鉴权
│   │   ├── errors.py          # 统一业务错误码 + 中文提示
│   │   ├── seed.py            # 种子数据（分类树/敏感词/管理员/演示账号+商品）
│   │   └── routers/           # auth/users/categories/uploads/items/search/im/orders/reviews/reports/admin
│   ├── smoke_test.py          # 端到端冒烟测试（核心业务闭环）
│   └── requirements.txt
└── web/                       # 前端（Vite + React TS + AntD）
    └── dist/                  # 构建产物（由后端 / 直接托管）
```

## 快速启动

### 方式 A：生产模式（推荐演示）

后端构建好后会**自动托管**前端 `web/dist` 产物，直接访问 `http://127.0.0.1:8000` 即可。

```bash
# 1. 后端
cd backend
python -m venv .venv && .\.venv\Scripts\activate
pip install -r requirements.txt         # 内含 sqlalchemy[asyncio]
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

# 2. 前端（首次需先构建产物；之后改前端需重新 npm run build）
cd ../web
npm install
npm run build
# 前端已 build 进 web/dist，被后端自动托管
```

### 方式 B：开发模式

前端起 Vite dev server（已配置代理到 8000）：`npm run dev`，访问 `http://127.0.0.1:5173`。

## 演示账号

| 角色 | 用户名 | 密码 | 密保（找回密码用） | 说明 |
| --- | --- | --- | --- | --- |
| 买家/卖家 | xianzhidaren | Abc12345 | 您最爱的食物是？ → 火锅 | 示例用户（深圳） |
| 卖家 | xiaozhou | Abc12345 | 您的小学名称是？ → 实验小学 | 示例卖家（杭州） |
| 卖家 | zhangshop | Abc12345 | 您的出生城市是？ → 上海 | 示例卖家（上海） |
| 管理员 | admin | Admin123 | － | 管理后台 `/admin/login` |

> 平台**不设昵称**，用户名即展示身份。注册采用**用户名+密码**，并需设置密保问题用于**忘记密码**时找回（用户名以字母开头，3~32 位字母/数字/下划线）。种子账号跳过注册弱密码校验直接入库（演示用）；新用户注册请使用含字母+数字且无连续序列的密码，例如 `Qwer8520`。

## 冒烟测试

```bash
cd backend
.\.venv\Scripts\python.exe smoke_test.py
```

覆盖：注册 → 登录 → 失败密码提示 → 分类 → 发布商品 → 搜索 → 详情 → 建会话 → 发消息 → 敏感词拦截 → 加地址 → 下单 → 支付 → 订单 PAID → 时间线留痕 → 未登录鉴权(401) → 管理端登录。全部 `PASS` 即视为业务闭环打通。

## 核心设计

- **订单状态机**：`待付款→待发货→已发货→已完成`，支持 取消/退款/争议/超时关闭/管理员干预，所有非法跳转一律拒绝，且每次流转写入 `order_status_logs` 留痕。
- **库存防超卖**：内存锁预占可售库存，支付后再扣减真实库存。
- **资金托管承诺**：支付后资金进入"托管"，确认收货才打款给卖家（页面明示）。
- **内容安全**：DFA 敏感词过滤（发布/消息双层拦截），管理端可维护词库。
- **错误码**：1xxx 账号 / 2xxx 商品 / 3xxx 检索 / 4xxx 消息 / 5xxx 订单 / 6xxx 评价举报 / 7xxx 管理 / 9xxx 系统，全部中文提示。