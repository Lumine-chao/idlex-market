# 闲置易 · 二手交易平台

一个可本地一键跑起来的**全栈二手交易平台 Demo**，覆盖 **注册 → 发布 → 搜索 → 聊天 → 下单 → 支付 → 发货 → 收货 → 评价** 的完整业务闭环，并附带管理后台。

严格遵循《项目说明文档（PRD）》与《技术架构文档》中定义的业务规则、订单状态机、错误码与中文提示。

---

## 仓库结构

```
project1/
├── idlex/                                   # 源码
│   ├── backend/                             # FastAPI 后端
│   ├── web/                                 # React 前端
│   ├── run.bat                              # Windows 后台启动（运行）
│   ├── stop.bat                             # Windows 停止服务
│   └── README.md                            # 源码级详细说明（推荐先读）
├── _doc1.md                                 # 项目说明文档（PRD）Markdown 版
├── _doc2.md                                 # 技术架构文档 Markdown 版
├── 闲置易二手交易平台项目说明文档.docx
└── 闲置易二手交易平台技术架构文档.docx
```

> 代码细节、目录说明与设计要点见 **[idlex/README.md](idlex/README.md)**。

---

## 技术栈

| 端 | 技术 |
| --- | --- |
| 后端 | Python 3.11 · FastAPI · SQLAlchemy (Async) · SQLite (aiosqlite) · PyJWT · Argon2 |
| 前端 | React 18 · TypeScript · Vite · Ant Design 5 · Zustand · React Router 6 |
| 实时通信 | WebSocket（买家/卖家即时消息 + 未读推送） |

---

## 快速开始

### 方式 A：一键启动（推荐演示）

双击根目录下的 `idlex/run.bat`，脚本会自动完成：创建后端虚拟环境 → 安装依赖 → 构建前端产物 → 后台启动服务并打开浏览器；需要关闭时双击 `idlex/stop.bat`。服务日志窗口已最小化在任务栏，点开即可查看。

访问 <http://127.0.0.1:8000> 即可。后端会直接托管前端 `web/dist` 构建产物。

### 方式 B：手动分步启动

```bash
# 1) 后端
cd idlex/backend
python -m venv .venv && .\.venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

# 2) 前端（首次需构建；之后改前端需重新 build）
cd ../web
npm install
npm run build
```

### 方式 C：开发模式

前端单独起 Vite dev server（已配置代理到 8000），访问 <http://127.0.0.1:5173>：

```bash
cd idlex/web
npm run dev
```

---

## 演示账号

| 角色 | 用户名 | 密码 | 密保（找回密码用） | 说明 |
| --- | --- | --- | --- | --- |
| 买家/卖家 | `xianzhidaren` | `Abc12345` | 您最爱的食物是？ → 火锅 | 示例用户（深圳） |
| 卖家 | `xiaozhou` | `Abc12345` | 您的小学名称是？ → 实验小学 | 示例卖家（杭州） |
| 卖家 | `zhangshop` | `Abc12345` | 您的出生城市是？ → 上海 | 示例卖家（上海） |
| 管理员 | `admin` | `Admin123` | － | 管理后台 `/admin/login` |

> 平台**不设昵称**，用户名即展示身份。注册采用**用户名 + 密码**，并需设置密保问题用于**忘记密码**时找回。种子账号跳过注册弱密码校验直接入库（演示用）；新用户注册请使用含字母 + 数字且无连续序列的密码，例如 `Qwer8520`。

---

## 核心设计

- **订单状态机**：`待付款 → 待发货 → 已发货 → 已完成`，支持取消/退款/争议/超时关闭/管理员干预；所有非法跳转一律拒绝，每次流转写入 `order_status_logs` 留痕。
- **库存防超卖**：内存锁预占可售库存，支付后再扣减真实库存。
- **资金托管承诺**：支付后资金进入"托管"，确认收货才打款给卖家（页面明示）。
- **内容安全**：DFA 敏感词过滤（发布/消息双层拦截），管理端可维护词库。
- **错误码**：`1xxx` 账号 / `2xxx` 商品 / `3xxx` 检索 / `4xxx` 消息 / `5xxx` 订单 / `6xxx` 评价举报 / `7xxx` 管理 / `9xxx` 系统，全部中文提示。

---

## 冒烟测试

```bash
cd idlex/backend
.\.venv\Scripts\python.exe smoke_test.py
```

覆盖：注册 → 登录 → 失败密码提示 → 分类 → 发布商品 → 搜索 → 详情 → 建会话 → 发消息 → 敏感词拦截 → 加地址 → 下单 → 支付 → 订单 PAID → 时间线留痕 → 未登录鉴权 (401) → 管理端登录。全部 `PASS` 即视为业务闭环打通。

---

## 关于数据

仓库**不包含**依赖目录与运行时数据（`.venv/`、`node_modules/`、`dist/`、`*.db`、`uploads/` 均已通过 `.gitignore` 排除）。

后端启动时会自动执行 `seed_demo()`：建表并灌入分类树、敏感词库、管理员账号、演示账号与 **24 件演示商品**（覆盖全部六个一级分类）。因此**新克隆的仓库无需附带数据库即可直接运行**。种子逻辑按标题幂等，重复启动不会产生重复数据。