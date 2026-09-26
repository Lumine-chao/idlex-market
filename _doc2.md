**闲置易二手交易平台**

**技术架构文档**

  ------------------------------------------------------------------------------
             **文档名称**             闲置易二手交易平台技术架构文档
  ----------------------------------- ------------------------------------------
               **版本**               V1.0

             **文档状态**             评审稿

             **编制日期**             2026 年 9 月 24 日

             **配套文档**             《闲置易二手交易平台项目说明文档》V1.0

             **读者对象**             架构师、开发工程师、测试工程师、运维人员

            **核心技术栈**            Python + FastAPI / React + TypeScript /
                                      PostgreSQL + MongoDB + Elasticsearch +
                                      Redis / Kubernetes
  ------------------------------------------------------------------------------

**目 录**

# **1 文档概述**

## **1.1 编写目的**

本文档描述闲置易二手交易平台的技术架构、技术选型、模块划分、数据设计、接口设计、关键设计、安全设计与部署方案，用于指导系统开发实施与后续维护，并作为开发、测试、运维各方的技术共识基线。

平台定位为面向个人用户的 C2C
二手闲置交易平台，用户自助完成注册登录、商品发布、检索浏览、在线沟通、下单交易、履约评价全流程。架构围绕这一业务形态，重点解决海量商品检索、实时消息投递、交易一致性与内容安全四类技术问题。

本文档中的需求编号沿用《闲置易二手交易平台项目说明文档》的编号体系：UR
为账号与用户类，PR 为商品类，SR 为搜索浏览类，CT 为沟通消息类，OR
为交易订单类，RV 为评价类，RP 为举报类，AD 为管理端类。

## **1.2 架构设计要点**

本系统的架构围绕以下八个要点展开，是理解后续各章的主线：

  --------------------------------------------------------------------------------------------------------------------------------------------------
  **要点**                            **设计决策**
  ----------------------------------- --------------------------------------------------------------------------------------------------------------
  检索优先                            以 Elasticsearch 承载商品检索，PostgreSQL 只承担事务与持久化，检索与写入解耦，避免数据库成为检索瓶颈

  读写分离与异步化                    商品写入后经 Kafka 异步同步至检索索引与推荐池，主链路不等待重操作

  长连接消息                          消息服务以 WebSocket 长连接承载实时投递，配合离线队列与回执机制保证不丢不重

  多模存储                            关系型（PostgreSQL）存交易与账号，文档型（MongoDB）存海量消息，检索（ES）存商品索引，对象存储（MinIO）存图片

  库存与交易一致                      二手商品多为单件，采用 Redis 原子锁库存 + 15 分钟锁定 + 超时释放，杜绝超卖

  状态机驱动交易                      订单状态由服务端状态机统一驱动，客户端只提交动作，每次流转写入流转记录

  内容安全内建                        敏感词过滤、图片审核、举报处置与限流风控作为平台基础能力内建，而非外挂

  云原生部署                          服务容器化并以 Kubernetes 编排，支持按服务独立扩缩容与滚动发布
  --------------------------------------------------------------------------------------------------------------------------------------------------

## **1.3 技术栈说明**

本文档按「Python 后端 + React 前端 + 多模数据存储 + Kubernetes
部署」的技术栈编写。Python 生态在异步
IO、数据处理与检索集成方面成熟，配合 FastAPI
的异步能力可支撑长连接与高吞吐场景；同时与既有的「Java 后端 + Vue 前端 +
单一关系库 +
单机部署」路线形成明确区隔，便于团队积累不同方向的技术资产。若项目实际采用其他语言或框架，可按下文分层逐层替换，模块划分、数据模型与接口契约部分保持不变。

# **2 架构总览**

## **2.1 架构设计原则**

  ---------------------------------------------------------------------------------------------------------------------------------------------------
  **原则**                **说明**                                         **在本系统中的落地方式**
  ----------------------- ------------------------------------------------ --------------------------------------------------------------------------
  服务自治                按业务边界拆分服务，数据所有权归服务私有         用户、商品、检索、消息、交易各自持有数据与库表，跨服务通过接口或消息协作

  异步优先                非关键路径操作异步化，主链路只做必要工作         索引同步、图片处理、通知推送经 Kafka 交由消费者处理

  检索下沉                检索能力由专用引擎承担，不让关系库承担模糊查询   商品检索全部走 Elasticsearch，PostgreSQL 仅做事务与回源

  连接可伸缩              长连接服务无状态化，状态外置                     WebSocket 连接不绑定本机状态，连接表与未读计数外置 Redis，节点可任意扩缩

  一致性可追溯            关键状态流转留痕，异常可补偿                     订单每次流转写入流转记录；定时任务与补偿任务对账修复

  内容安全默认开启        发布与沟通链路默认经过内容安全校验               敏感词过滤、图片审核、限流风控作为中间件默认接入

  可观测性内建            指标、日志、链路三者统一采集                     OpenTelemetry 埋点 + Prometheus 指标 + Loki 日志，服务默认接入
  ---------------------------------------------------------------------------------------------------------------------------------------------------

## **2.2 总体分层架构**

![](media/image1.png){width="6.111111111111111in"
height="4.180476815398075in"}

图 1 闲置易二手交易平台分层架构

  -------------------------------------------------------------------------------------------------------------------------------------
  **层次**                **主要职责**                                 **关键组件**
  ----------------------- -------------------------------------------- ----------------------------------------------------------------
  客户端层                页面渲染、输入采集、实时消息呈现             React 18 + TypeScript + Ant
                                                                       Design；首页、搜索页、商品详情、发布页、会话页、订单页、管理端

  接入层                  路由、限流、鉴权、TLS 终止、静态资源         APISIX 网关（路由 / 限流 / 插件）、Nginx Ingress、CDN

  应用服务层              用例编排、事务边界、权限校验、流程控制       user、item、search、im、trade、admin 六个 Python
                                                                       服务，同步调用走 REST 与 gRPC，异步协作走 Kafka

  异步层                  事件解耦、削峰填谷、异步任务                 Kafka（索引同步 / 通知 / 图片处理）、indexer 与 notify 消费者

  领域层                  业务实体与核心规则，与技术框架无关           Item、Order（含状态机）、Conversation、Message 实体与
                                                                       PricePolicy、StockLocker、SensitiveFilter 等

  基础设施层              持久化、缓存、检索、对象存储与日志           SQLAlchemy 2.0 异步会话、redis-py
                                                                       asyncio、elasticsearch-py、motor、minio-py、structlog

  数据存储层              业务数据、消息数据、检索数据与文件的持久化   PostgreSQL 16（主库）、MongoDB 7（消息）、Elasticsearch
                                                                       8（检索）、Redis 7（缓存与锁）、MinIO（图片）
  -------------------------------------------------------------------------------------------------------------------------------------

# **3 技术选型**

## **3.1 选型清单**

  -------------------------------------------------------------------------------------------------------------------------
  **层次**       **技术 / 组件**     **版本建议**   **用途**               **选型理由**
  -------------- ------------------- -------------- ---------------------- ------------------------------------------------
  前端           React + TypeScript  18 + 5.x       构建单页应用           类型系统降低大型前端维护成本，生态成熟

  前端           Vite                5.x            构建与开发服务         冷启动与热更新快，适合多页面工程

  前端           Ant Design          5.x            UI 组件库              表单、上传、列表、消息组件齐全，适合电商类流程

  前端           Zustand + React     4.x + 6.x      状态管理与路由         轻量状态容器，配合路由守卫实现登录拦截
                 Router                                                    

  接入           APISIX              3.x            API 网关               插件化限流、鉴权与灰度，性能高

  接入           Nginx Ingress + CDN 1.24+          入口与静态加速         统一域名入口，静态资源走 CDN

  后端           Python + FastAPI    3.12 + 0.115   应用主体框架           原生异步 IO，适合 IO 密集与长连接；自动生成
                                                                           OpenAPI 文档

  后端           Pydantic +          2.x            数据校验与配置         声明式模型校验，配置集中管理且与校验规则同源
                 pydantic-settings                                         

  后端           SQLAlchemy +        2.0 + 1.13 +   持久层与迁移           异步会话与版本化迁移，支持事务与行级锁
                 Alembic + asyncpg   0.29                                  

  后端           FastAPI WebSocket   内建           长连接通信             基于 Starlette，与 REST
                                                                           同栈，便于统一鉴权与中间件

  后端           httpx + grpcio      0.27 + 1.6x    服务间通信             同步调用以 httpx 与 gRPC 并存，按场景选择

  后端           structlog +         最新稳定版     结构化日志与埋点       结构化日志与链路埋点统一输出
                 OpenTelemetry SDK                                         

  后端           Celery + Redis      5.x            定时任务与异步作业     承担超时关单、自动确认收货与图片处理

  消息           Kafka + aiokafka    3.7            异步事件总线           高吞吐、可重放，支撑索引同步与通知

  检索           Elasticsearch + IK  8.13           商品检索               中文分词与相关性排序能力强，支持联想与聚合
                 分词                                                      

  数据           PostgreSQL          16             业务主库               JSONB 支持商品扩展属性，事务与约束完善

  数据           MongoDB + motor     7.0            聊天消息存储           文档模型天然适合消息，异步驱动契合 asyncio 服务

  数据           Redis               7.x            缓存、会话、锁、未读   原子操作与过期机制支撑库存锁与一次性数据

  存储           MinIO               最新稳定版     商品图片对象存储       兼容 S3 协议，可私有化部署

  部署           Kubernetes + Helm   1.29 + 3.x     编排与发布             按服务独立扩缩容，声明式发布可回滚

  部署           GitLab CI + Argo CD 最新稳定版     持续集成与交付         镜像构建后由 GitOps 自动同步至集群

  观测           Prometheus +        最新稳定版     指标、看板与日志       云原生标准组合，告警与排查闭环
                 Grafana + Loki                                            

  观测           OpenTelemetry       1.x            链路追踪               统一埋点标准，跨服务串联调用链

  质量           pytest +            最新稳定版     单元测试               异步用例原生支持，配合 mock 覆盖边界
                 pytest-asyncio +                                          
                 respx                                                     

  质量           Locust              最新稳定版     性能压测               Python 脚本化压测检索与下单链路
  -------------------------------------------------------------------------------------------------------------------------

## **3.2 与既有技术栈的差异**

为形成技术方向的区隔，本平台在语言、框架、存储与部署形态上均选择与《航班预订系统》不同的路线，仅容器化与缓存组件保持复用。

  ----------------------------------------------------------------------------------------------------------------------------
  **维度**          **航班预订系统（既有）**   **闲置易平台（本方案）**       **差异带来的能力变化**
  ----------------- -------------------------- ------------------------------ ------------------------------------------------
  后端语言与框架    Java 17 + Spring Boot 3.2  Python 3.12 + FastAPI          原生异步 IO 与自动 OpenAPI
                                                                              文档，开发效率高，检索与数据处理生态成熟

  服务形态          单体分层架构               按业务边界拆分的多服务         检索、消息、交易可独立扩缩容，故障隔离

  前端框架          Vue 3 + Element Plus       React 18 + TypeScript + Ant    类型系统支撑大型前端工程，组件生态不同
                                               Design                         

  主数据库          MySQL 8.0                  PostgreSQL 16                  JSONB 承载商品扩展属性，窗口函数与并发控制更强

  检索方式          数据库条件查询             Elasticsearch 8 + IK 分词      支持中文分词、相关性排序、联想与聚合

  消息与异步        无                         Kafka 3.7 事件总线             索引同步、通知与图片处理异步化，主链路不阻塞

  实时通信          无                         WebSocket + 离线队列 + 回执    端到端 500 毫秒内送达，支持未读与补发

  消息存储          无                         MongoDB 7                      海量消息写入与水平扩展

  文件存储          无（无图片能力）           MinIO 对象存储                 支持图片直传、多规格缩略图与私有化部署

  部署形态          Docker Compose 单机        Kubernetes + Helm + Argo CD    按服务弹性伸缩、滚动发布与一键回滚

  可观测性          Logback 日志               OpenTelemetry + Prometheus +   指标、日志、链路三位一体
                                               Loki                           

  可复用部分        ---                        Redis 7、Docker                缓存、容器与检索入口经验直接复用，降低学习成本
                                               容器化、Nginx、Elasticsearch   
  ----------------------------------------------------------------------------------------------------------------------------

## **3.3 技术栈可替换说明**

> · 后端可替换为 Go（Gin）或
> Node.js（NestJS）：分层结构、数据模型与接口契约保持一致，仅需替换基础设施层实现；Python
> 的 asyncio 已能支撑目标并发，切换主要用于追求更低内存占用。
>
> · 检索可替换为 OpenSearch 或 PostgreSQL
> 全文检索：检索服务对外契约不变，仅需替换查询构建与索引同步实现。
>
> · 对象存储可替换为腾讯云 COS 或 AWS S3：预签名上传接口抽象后，仅需替换
> SDK 与域名配置。
>
> · 消息中间件可替换为 RocketMQ 或
> Pulsar：事件契约不变，仅需替换生产者与消费者封装。

# **4 模块划分与代码结构**

## **4.1 功能模块划分**

  ----------------------------------------------------------------------------------------------------------------
  **模块**                **包含能力**                                                     **对应需求**
  ----------------------- ---------------------------------------------------------------- -----------------------
  用户模块 user           注册登录、双令牌会话、资料维护、收货地址、收藏与足迹             UR-01 ～ UR-12

  商品模块 item           发布与编辑、图片管理、上下架、库存、浏览量、我的发布             PR-01 ～ PR-12

  检索模块 search         关键词检索、多维筛选、排序分页、联想、热词、推荐                 SR-01 ～ SR-12

  消息模块 im             会话管理、长连接投递、离线补发、未读计数、撤回、系统通知         CT-01 ～ CT-12

  交易模块 trade          下单、议价改价、库存锁定、支付、发货、收货、退款、争议、状态机   OR-01 ～ OR-19

  评价与举报模块 review   买卖互评、评分标签、评价申诉、举报受理与进度                     RV-01 ～ RV-05、RP-01
                                                                                           ～ RP-04

  管理模块 admin          商品审核、用户处置、订单干预、举报处理、敏感词维护、数据看板     AD-01 ～ AD-06

  异步任务模块 job        索引同步、图片处理、通知推送、超时关单、自动确认收货             全部（异步支撑）

  公共模块 pkg            统一响应、错误码、鉴权、校验器、敏感词、追踪、缓存与锁封装       全部
  ----------------------------------------------------------------------------------------------------------------

## **4.2 后端代码结构**

后端采用单仓多服务的组织方式（Monorepo），各服务以独立 Python
包组织，共享 common 公共库；服务间同步调用走 REST 与 gRPC，异步协作走
Kafka，定时任务与异步作业由 Celery 承担。

> idlex/
>
> ├── services/
>
> │ ├── user/ 用户服务：注册登录、资料、地址、收藏足迹
>
> │ │ ├── main.py FastAPI 应用入口与生命周期
>
> │ │ ├── api/ APIRouter：auth、profile、address、favorite
>
> │ │ ├── schemas/ Pydantic 请求与响应模型
>
> │ │ ├── service/ 业务逻辑层
>
> │ │ ├── repo/ 数据访问层（SQLAlchemy 异步会话）
>
> │ │ └── models/ ORM 模型
>
> │ ├── item/ 商品服务：发布、编辑、上下架、库存
>
> │ │ ├── api/ items、uploads、categories
>
> │ │ └── service/ item_service、stock_service、audit_service
>
> │ ├── search/ 检索服务：搜索、筛选、联想、热词
>
> │ │ ├── query_builder.py ES 查询构建（bool / filter / function_score）
>
> │ │ ├── ranker.py 综合排序权重
>
> │ │ └── suggester.py completion 联想与 Redis 热词
>
> │ ├── im/ 消息服务：WebSocket 长连接与投递
>
> │ │ ├── ws.py WebSocket 端点与鉴权握手
>
> │ │ ├── hub.py 连接注册、心跳与节点路由
>
> │ │ ├── deliver.py 投递、ACK、重试与跨节点 Pub/Sub
>
> │ │ └── offline.py 离线队列与按 seq 补发
>
> │ ├── trade/ 交易服务：下单、支付、发货、退款、状态机
>
> │ │ ├── api/ orders、payments、reviews、reports
>
> │ │ ├── order.py 下单、快照与库存预占
>
> │ │ ├── payment.py 支付网关抽象与 MOCK 通道
>
> │ │ ├── logistics.py 物流单号与轨迹接口预留
>
> │ │ └── statemachine.py 订单状态机与流转留痕
>
> │ ├── admin/ 管理服务：审核、处置、词库、看板
>
> │ └── worker/ Celery Worker 与 Beat
>
> │ ├── celery_app.py Celery 实例与队列路由
>
> │ ├── tasks/indexer.py Kafka 消费：商品索引同步与对账
>
> │ ├── tasks/image.py 缩略图生成、EXIF 清除与图片审核
>
> │ ├── tasks/notify.py 系统通知与消息推送
>
> │ └── tasks/schedule.py 超时关单、自动确认收货、退款超时
>
> ├── common/
>
> │ ├── auth.py 双令牌签发、校验、刷新与失效
>
> │ ├── response.py 统一响应包装
>
> │ ├── errors.py 业务异常与错误码分段
>
> │ ├── deps.py FastAPI 依赖注入：会话、当前用户、限流
>
> │ ├── cache.py redis-py asyncio 客户端
>
> │ ├── lock.py 分布式锁与库存 Lua 脚本
>
> │ ├── es.py elasticsearch-py 异步客户端
>
> │ ├── mongo.py motor 客户端
>
> │ ├── oss.py minio-py 预签名与对象操作
>
> │ ├── kafka.py aiokafka 生产者与消费者封装
>
> │ ├── sensitive.py 敏感词 DFA 过滤
>
> │ └── trace.py OpenTelemetry 初始化与埋点
>
> ├── migrations/ Alembic 版本化迁移脚本
>
> ├── tests/ pytest 用例：unit / api / flow
>
> ├── deploy/ Helm Chart 与各环境 values
>
> └── web/ 前端工程（React + TypeScript）

代码清单 1 后端代码结构（Python 3.12 / FastAPI）

## **4.3 前端目录结构**

> src/
>
> ├── api/ 各模块接口定义与请求封装
>
> ├── pages/
>
> │ ├── HomePage.tsx 首页与推荐流（SR-08）
>
> │ ├── SearchPage.tsx 搜索结果页（SR-01 ～ SR-07）
>
> │ ├── ItemDetailPage.tsx 商品详情（SR-09、SR-10）
>
> │ ├── PublishPage.tsx 发布与编辑商品（PR-01 ～ PR-08）
>
> │ ├── ChatPage.tsx 会话与消息（CT-01 ～ CT-12）
>
> │ ├── OrderConfirmPage.tsx 确认订单（OR-01 ～ OR-05）
>
> │ ├── OrderListPage.tsx 我买到的 / 我卖出的（OR-08）
>
> │ ├── OrderDetailPage.tsx 订单详情与时间线（OR-09、OR-12 ～ OR-16）
>
> │ ├── ReviewPage.tsx 评价与申诉（RV-01 ～ RV-05）
>
> │ ├── UserProfilePage.tsx 个人主页与资料（UR-08 ～ UR-11）
>
> │ ├── LoginPage.tsx 登录与注册（UR-01 ～ UR-07）
>
> │ └── admin/ 管理端：审核、用户、订单、举报、看板
>
> ├── components/
>
> │ ├── ItemCard.tsx 商品卡片
>
> │ ├── ImageUploader.tsx 图片选择与直传（PR-02）
>
> │ ├── ChatBubble.tsx 消息气泡与状态
>
> │ ├── OrderStatusTimeline.tsx 订单状态时间线
>
> │ ├── PriceTag.tsx 价格与成色标签
>
> │ └── SensitiveText.tsx 敏感词替换展示
>
> ├── hooks/ useWebSocket、useAuth、useInfiniteList
>
> ├── store/ Zustand：用户、会话、未读、购物车态
>
> ├── utils/ 日期、金额、提示语映射、校验规则
>
> └── router/ 路由与登录守卫

代码清单 2 前端目录结构（React 18 + TypeScript）

## **4.4 前端关键交互映射**

需求中的界面要素与交互行为由前端按下表映射实现；文案统一取自 utils
提示语常量，与服务端提示语同源，避免前后端文案漂移。

  --------------------------------------------------------------------------------------------------------------------
  **需求编号**            **界面要素**            **实现要点**
  ----------------------- ----------------------- --------------------------------------------------------------------
  SR-01、SR-05            搜索框与联想            输入防抖 300 毫秒请求联想接口；结果页高亮命中关键词

  SR-02、SR-04            筛选与分页              筛选条件写入 URL 查询串，可分享与回退；滚动到底自动加载下一页

  SR-07                   无结果页                展示同类推荐与「减少筛选条件」引导按钮

  PR-02、BR-07            图片上传                前端校验数量与大小后请求预签名直传对象存储，展示上传进度与缩略图

  PR-11、BR-09            敏感词提示              提交前本地预校验，命中时给出「内容包含违规信息，请修改后重新发布」

  CT-04、CT-08            长连接                  useWebSocket
                                                  维护连接与心跳，断线按指数退避重连，重连后按游标补齐消息

  CT-05、CT-07            已读与未读              进入会话发送已读回执并清零未读；全局未读由服务端推送更新

  CT-09、BR-16            撤回                    2 分钟内展示撤回入口，撤回后本地替换为「消息已撤回」

  OR-03、OR-11            支付倒计时              订单页展示 15 分钟倒计时，归零后自动刷新为已关闭

  OR-08、OR-09            订单时间线              按流转记录渲染时间线，展示每次状态变更的操作人与时间

  OR-16                   申诉入口                已发货订单展示申诉入口，提交后展示「平台处理中」

  RV-02、RV-04            评分与标签              星级选择 + 标签多选；卖家主页展示累计评分与好评率
  --------------------------------------------------------------------------------------------------------------------

# **5 数据架构**

## **5.1 实体关系**

系统核心实体包括用户、收货地址、商品、商品图片、分类、收藏、足迹、会话、消息、订单、状态流转记录、评价与举报。一名用户可发布多件商品、创建多笔订单；一笔订单对应一件商品快照；一个会话关联一件商品与两名用户；一条消息属于一个会话。

  --------------------------------------------------------------------------------------------
  **关系**                **基数**                **说明**
  ----------------------- ----------------------- --------------------------------------------
  user → items            1 : N                   一名用户可发布多件商品

  user → orders           1 : N                   订单分别记录 buyer_id 与
                                                  seller_id，两者均指向用户

  item → orders           1 : N                   一件商品可被多笔订单引用，订单保存商品快照

  item → item_images      1 : N                   一件商品 1 ～ 9 张图片，首图为主图

  category → items        1 : N                   三级分类，商品挂载末级分类

  conversation → messages 1 : N                   消息存储于 MongoDB，以 conversation_id 关联

  order →                 1 : N                   每次状态流转写入一条记录
  order_status_logs                               

  order → reviews         1 : N                   一笔订单最多两条评价（买卖互评）
  --------------------------------------------------------------------------------------------

## **5.2 PostgreSQL 表结构**

### **5.2.1 用户表 users**

  ------------------------------------------------------------------------------------------------
  **字段**          **类型**          **约束**          **说明**
  ----------------- ----------------- ----------------- ------------------------------------------
  id                BIGSERIAL         PK                主键

  phone             VARCHAR(11)       NOT NULL，UNIQUE  手机号，登录主体

  password_hash     VARCHAR(100)      NOT NULL          Argon2id 加密后的密码，永不明文存储

  nickname          VARCHAR(40)       NOT NULL          昵称，2 ～ 20 个字符

  avatar            VARCHAR(255)      NULL              头像图片地址

  city_code         VARCHAR(16)       NULL              所在城市编码

  credit_level      SMALLINT          默认 3            信用等级 1 ～ 5

  status            SMALLINT          NOT NULL，默认 1  状态：1 正常，2 封禁登录，3 禁用发布

  locked_until      TIMESTAMPTZ       NULL              锁定截止时间；非空且晚于当前时间即锁定中

  fail_count        INT               默认 0            连续密码失败次数，登录成功或解锁时清零

  last_login_at     TIMESTAMPTZ       NULL              最近一次登录成功时间

  created_at        TIMESTAMPTZ       NOT NULL          注册时间

  updated_at        TIMESTAMPTZ       NOT NULL          更新时间

  deleted_at        TIMESTAMPTZ       NULL              软删除时间
  ------------------------------------------------------------------------------------------------

### **5.2.2 收货地址表 user_addresses**

  ----------------------------------------------------------------------------
  **字段**          **类型**          **约束**          **说明**
  ----------------- ----------------- ----------------- ----------------------
  id                BIGSERIAL         PK                主键

  user_id           BIGINT            NOT NULL，FK →    所属用户，单用户最多
                                      users.id          20 个

  receiver          VARCHAR(32)       NOT NULL          收货人姓名

  phone             VARCHAR(11)       NOT NULL          收货手机号

  province / city / VARCHAR(32)       NOT NULL          省市区
  district                                              

  detail            VARCHAR(255)      NOT NULL          详细地址

  is_default        BOOLEAN           默认 false        是否默认地址

  created_at        TIMESTAMPTZ       NOT NULL          创建时间
  ----------------------------------------------------------------------------

### **5.2.3 商品表 items**

  --------------------------------------------------------------------------------------
  **字段**          **类型**          **约束**          **说明**
  ----------------- ----------------- ----------------- --------------------------------
  id                BIGSERIAL         PK                主键

  seller_id         BIGINT            NOT NULL，FK →    卖家
                                      users.id          

  title             VARCHAR(100)      NOT NULL          标题，5 ～ 50 字

  description       TEXT              NOT NULL          描述，10 ～ 2000 字

  category_id       BIGINT            NOT NULL，FK →    末级分类
                                      categories.id     

  condition_level   SMALLINT          NOT NULL          成色：1 全新，2 几乎全新，3
                                                        轻微使用痕迹，4 明显使用痕迹

  price             NUMERIC(10,2)     NOT NULL          售价，单位元

  origin_price      NUMERIC(10,2)     NULL              原价，可为空

  stock             INT               NOT NULL，默认 1  库存数量，二手多为 1

  city_code         VARCHAR(16)       NOT NULL          所在地城市编码

  trade_type        SMALLINT          NOT NULL          交易方式：1 快递，2 同城自提，3
                                                        两者皆可

  freight_payer     SMALLINT          NOT NULL，默认 1  运费承担：1 卖家包邮，2 买家承担

  freight           NUMERIC(10,2)     默认 0            运费金额

  status            SMALLINT          NOT NULL，默认 1  状态：1 草稿，2 审核中，3
                                                        在售，4 已下架，5 已售出，6
                                                        审核不通过

  view_count        INT               默认 0            浏览量

  extra             JSONB             NULL              扩展属性，如品牌、型号、尺寸等

  created_at        TIMESTAMPTZ       NOT NULL          发布时间

  updated_at        TIMESTAMPTZ       NOT NULL          更新时间

  deleted_at        TIMESTAMPTZ       NULL              软删除时间
  --------------------------------------------------------------------------------------

### **5.2.4 商品图片表 item_images**

  ----------------------------------------------------------------------------------
  **字段**          **类型**          **约束**          **说明**
  ----------------- ----------------- ----------------- ----------------------------
  id                BIGSERIAL         PK                主键

  item_id           BIGINT            NOT NULL，FK →    所属商品
                                      items.id          

  url               VARCHAR(255)      NOT NULL          原图地址

  thumb_url         VARCHAR(255)      NULL              缩略图地址，异步生成后回写

  sort              INT               默认 0            排序，0 为主图

  width / height    INT               NULL              图片尺寸

  audit_status      SMALLINT          默认 1            审核状态：1 待审，2 通过，3
                                                        疑似违规
  ----------------------------------------------------------------------------------

### **5.2.5 订单表 orders**

  ----------------------------------------------------------------------------------------------
  **字段**            **类型**          **约束**          **说明**
  ------------------- ----------------- ----------------- --------------------------------------
  id                  BIGSERIAL         PK                主键

  order_no            VARCHAR(32)       NOT NULL，UNIQUE  订单号，系统生成，全局唯一且不可修改

  buyer_id            BIGINT            NOT NULL，FK →    买家
                                        users.id          

  seller_id           BIGINT            NOT NULL，FK →    卖家
                                        users.id          

  item_id             BIGINT            NOT NULL，FK →    关联商品
                                        items.id          

  item_snapshot       JSONB             NOT NULL          商品快照：标题、主图、成色、单价

  quantity            INT               NOT NULL，默认 1  购买数量

  unit_price          NUMERIC(10,2)     NOT NULL          下单时单价

  freight             NUMERIC(10,2)     默认 0            运费

  total_amount        NUMERIC(10,2)     NOT NULL          订单总额 = 单价 × 数量 + 运费

  address_snapshot    JSONB             NOT NULL          收货地址快照

  status              VARCHAR(24)       NOT NULL，默认    订单状态，见 7.6
                                        PENDING_PAYMENT   

  pay_channel         VARCHAR(24)       NULL              支付通道，本期为 MOCK

  paid_at             TIMESTAMPTZ       NULL              支付时间

  logistics_company   VARCHAR(64)       NULL              物流公司

  tracking_no         VARCHAR(64)       NULL              运单号

  shipped_at          TIMESTAMPTZ       NULL              发货时间

  finished_at         TIMESTAMPTZ       NULL              完成时间

  version             INT               NOT NULL，默认 0  乐观锁版本号，防止并发更新覆盖

  created_at          TIMESTAMPTZ       NOT NULL          创建时间

  updated_at          TIMESTAMPTZ       NOT NULL          更新时间
  ----------------------------------------------------------------------------------------------

### **5.2.6 订单状态流转表 order_status_logs**

  ----------------------------------------------------------------------------------
  **字段**          **类型**          **约束**          **说明**
  ----------------- ----------------- ----------------- ----------------------------
  id                BIGSERIAL         PK                主键

  order_id          BIGINT            NOT NULL，FK →    所属订单
                                      orders.id         

  from_status       VARCHAR(24)       NULL              变更前状态，新建时可空

  to_status         VARCHAR(24)       NOT NULL          变更后状态

  action            VARCHAR(32)       NOT NULL          触发动作：CREATE / PAY /
                                                        CANCEL / TIMEOUT_CLOSE /
                                                        SHIP / CONFIRM /
                                                        AUTO_CONFIRM / REFUND /
                                                        DISPUTE / ADMIN

  operator_type     VARCHAR(16)       NOT NULL          操作人类型：BUYER / SELLER /
                                                        SYSTEM / ADMIN

  operator_id       BIGINT            NULL              操作人 ID，SYSTEM 时为空

  operate_time      TIMESTAMPTZ       NOT NULL          操作时间

  remark            VARCHAR(255)      NULL              备注，如驳回理由或处置说明
  ----------------------------------------------------------------------------------

说明：订单每次状态变更均写入本表，支撑订单详情页的时间线展示与运营追溯；订单记录不做物理删除。

### **5.2.7 其他业务表**

  -----------------------------------------------------------------------------------------------------------------------------------------------
  **表名**                **主要字段**                                                                     **说明**
  ----------------------- -------------------------------------------------------------------------------- --------------------------------------
  categories              id、name、parent_id、level、sort                                                 三级分类树，作为发布与筛选的可选范围

  favorites               id、user_id、item_id、created_at                                                 收藏；唯一约束（user_id, item_id）

  footprints              id、user_id、item_id、created_at                                                 浏览足迹，异步写入，保留最近 100 条

  conversations           id、item_id、buyer_id、seller_id、last_message_at、last_message                  会话，同一买家与商品唯一

  reviews                 id、order_id、reviewer_id、target_id、score、tags、content、is_modified          评价，一笔订单买卖双方各一条

  reports                 id、reporter_id、target_type、target_id、reason_type、evidence、status、result   举报及其处置结果

  admin_users             id、username、password_hash、role、status                                        管理员账号，独立于用户表

  sensitive_words         id、word、level、status                                                          敏感词库，支持停用与分级
  -----------------------------------------------------------------------------------------------------------------------------------------------

## **5.3 MongoDB 集合设计**

聊天消息写入频繁且量大，采用 MongoDB
存储，按会话与时间组织，避免关系库被高频写入拖累。

  -----------------------------------------------------------------------------------------------------------------------------------------------------
  **集合**                **关键字段**                                                                           **说明**
  ----------------------- -------------------------------------------------------------------------------------- --------------------------------------
  messages                \_id、conversation_id、sender_id、type、content、status、seq、created_at、revoked_at   消息正文；type 为 TEXT / IMAGE /
                                                                                                                 ITEM_CARD / PRICE_CARD / SYSTEM

  offline_messages        \_id、user_id、conversation_id、message_id、created_at                                 离线队列，接收方上线后按序补发并删除

  message_idempotent      \_id（client_msg_id）、message_id、created_at                                          客户端消息 ID 去重表，支撑幂等投递
  -----------------------------------------------------------------------------------------------------------------------------------------------------

说明：消息以 conversation_id 为分片键，配合（conversation_id,
created_at）索引支撑按会话翻页；离线消息设置 30
天过期时间，避免长期堆积。

## **5.4 Elasticsearch 索引设计**

商品检索索引以读优化为目标，字段冗余商品关键信息与卖家信息，避免检索后回源。

> PUT /items
>
> {
>
> \"settings\": { \"number_of_shards\": 3, \"number_of_replicas\": 1,
>
> \"analysis\": { \"analyzer\": { \"ik_search\": { \"type\": \"custom\",
> \"tokenizer\": \"ik_smart\" } } } },
>
> \"mappings\": { \"properties\": {
>
> \"item_id\": { \"type\": \"long\" },
>
> \"title\": { \"type\": \"text\", \"analyzer\": \"ik_max_word\",
> \"search_analyzer\": \"ik_smart\" },
>
> \"description\": { \"type\": \"text\", \"analyzer\": \"ik_max_word\",
> \"search_analyzer\": \"ik_smart\" },
>
> \"category_id\": { \"type\": \"long\" },
>
> \"category_path\": { \"type\": \"keyword\" },
>
> \"condition_level\":{ \"type\": \"short\" },
>
> \"price\": { \"type\": \"scaled_float\", \"scaling_factor\": 100 },
>
> \"city_code\": { \"type\": \"keyword\" },
>
> \"trade_type\": { \"type\": \"short\" },
>
> \"free_shipping\": { \"type\": \"boolean\" },
>
> \"status\": { \"type\": \"short\" },
>
> \"seller_id\": { \"type\": \"long\" },
>
> \"seller_name\": { \"type\": \"text\", \"analyzer\": \"ik_smart\" },
>
> \"view_count\": { \"type\": \"integer\" },
>
> \"cover_url\": { \"type\": \"keyword\", \"index\": false },
>
> \"created_at\": { \"type\": \"date\" },
>
> \"suggest\": { \"type\": \"completion\" }
>
> } }
>
> }

代码清单 3 商品检索索引映射（Elasticsearch 8）

## **5.5 Redis 键设计**

  -----------------------------------------------------------------------------------------------------------
  **键**                         **类型**          **过期**          **用途**
  ------------------------------ ----------------- ----------------- ----------------------------------------
  auth:refresh:{userId}:{jti}    String            7 天              刷新令牌记录，登出或改密时删除实现失效

  auth:fail:{phone}              String            30 分钟           连续失败计数，达到 5 次写入锁定

  auth:sms:{phone}               String            5 分钟            短信验证码与重发间隔控制

  stock:lock:{itemId}            String            15 分钟           下单未支付期间的库存锁定量

  stock:deduct:{orderNo}         String            24 小时           库存扣减幂等标记，防重复扣减

  im:conn:{userId}               Set               连接期            用户当前所在网关节点，用于定向投递

  im:unread:{userId}             Hash              永久              会话级未读计数

  im:seq:{conversationId}        String            永久              会话消息递增序号，用于消息去重与补发

  search:hot                     ZSet              7 天              热门搜索词及计数

  item:view:{itemId}:{userId}    String            30 分钟           浏览量去重

  rate:limit:{userId}:{action}   String            1 分钟            接口与发消息限流计数
  -----------------------------------------------------------------------------------------------------------

## **5.6 对象存储设计**

  ----------------------------------------------------------------------------------------------------
  **桶 / 前缀**                 **内容**                **处理策略**
  ----------------------------- ----------------------- ----------------------------------------------
  idlex-item /                  商品原图                仅服务可写，客户端通过预签名直传，不公开列举
  original/{yyyyMM}/{itemId}/                           

  idlex-item /                  缩略图（200 / 400 /     图片上传后由异步任务生成多规格缩略图，转 WebP
  thumb/{size}/{itemId}/        800）                   

  idlex-avatar /                用户头像                上传后压缩至 200×200

  idlex-evidence /              举报凭证图片            仅管理员与举报人可访问，带时效签名
  ----------------------------------------------------------------------------------------------------

说明：图片上传经服务端签发预签名地址后由客户端直传对象存储，避免图片流量穿透应用服务；上传完成后写入消息事件，由异步任务生成缩略图并回写
item_images。

## **5.7 索引与查询设计**

  ------------------------------------------------------------------------------------------------------------------
  **库 / 引擎**     **索引**                                              **类型**          **服务场景**
  ----------------- ----------------------------------------------------- ----------------- ------------------------
  PostgreSQL        uk_users_phone（phone）                               唯一索引          登录查询与手机号唯一性

  PostgreSQL        idx_items_seller_status（seller_id, status）          联合索引          我的发布列表按状态筛选

  PostgreSQL        idx_items_cat_status_time（category_id, status,       联合索引          分类浏览与检索降级回源
                    created_at）                                                            

  PostgreSQL        uk_favorites_user_item（user_id, item_id）            唯一索引          收藏去重

  PostgreSQL        idx_orders_buyer_status（buyer_id, status,            联合索引          我买到的列表与状态筛选
                    created_at）                                                            

  PostgreSQL        idx_orders_seller_status（seller_id, status,          联合索引          我卖出的列表与状态筛选
                    created_at）                                                            

  PostgreSQL        uk_orders_no（order_no）                              唯一索引          订单号精确检索

  PostgreSQL        idx_order_logs_order（order_id）                      普通索引          订单状态时间线

  MongoDB           idx_messages_conv_seq（conversation_id, seq）         联合索引          按会话翻页拉取历史消息

  MongoDB           idx_offline_user（user_id, created_at）               联合索引          离线消息补发

  Elasticsearch     title / description（ik_max_word）                    倒排索引          关键词检索与高亮

  Elasticsearch     category_id、condition_level、city_code、trade_type   字段索引          多维筛选（filter
                                                                                            上下文，可缓存）

  Elasticsearch     price、created_at、view_count                         字段索引          排序与区间筛选
  ------------------------------------------------------------------------------------------------------------------

## **5.8 数据一致性设计**

> · 商品主数据以 PostgreSQL
> 为准，检索索引为派生数据：商品发布、编辑、上下架后写入 Kafka 事件，由
> indexer 消费者更新 Elasticsearch，正常情况下 3 秒内可见。
>
> ·
> 索引同步失败进入重试队列，连续失败写入死信表并告警；定时任务每小时对账一次，比对商品更新时间与索引更新时间，差异数据批量重建。
>
> · Elasticsearch 不可用时，检索服务降级至 PostgreSQL
> 全文检索（tsvector）与分类筛选，保证浏览可用，同时限制分页深度。
>
> · 订单与库存：库存扣减与订单创建在同一数据库事务内完成，Redis
> 锁库存作为前置防超卖手段，二者以订单号做幂等对齐。
>
> · 消息与未读：消息先落 MongoDB 再推送，未读数以 Redis
> 计数为准并异步持久化，节点重启后由 MongoDB 重新计算校正。

# **6 接口设计**

## **6.1 接口约定**

> · 协议与格式：HTTP + JSON（REST），实时消息使用 WebSocket；字符编码
> UTF-8。
>
> ·
> 基础路径：/api/v1。除注册、登录、验证码、重置密码、商品详情与检索外，其余接口均需在请求头携带
> Authorization: Bearer \<accessToken\>。
>
> · 统一响应结构：{ code, message, data }，code 为 0 表示成功，非 0
> 为业务失败，message 直接取需求中定义的中文提示语。
>
> · 错误映射：业务校验失败返回 200 + 业务错误码；未认证返回
> 401；越权访问返回 403 并统一提示「订单不存在」；限流返回 429。
>
> ·
> 数据隔离：订单、会话、地址等资源的服务端从令牌解析用户标识，不接受客户端传入的他人标识。
>
> · 分页约定：分页参数使用 page 与 size，返回 { list, total, page, size
> }。
>
> · WebSocket 消息信封：{ type, seq, ack, payload, timestamp }，客户端按
> seq 去重并对需要确认的消息回 ack。

## **6.2 接口清单**

  -----------------------------------------------------------------------------------------------------------------------------------------
  **编号**    **方法**              **路径**                                   **说明**                 **对应需求**          **鉴权**
  ----------- --------------------- ------------------------------------------ ------------------------ --------------------- -------------
  API-01      POST                  /api/v1/auth/sms-code                      获取短信验证码           UR-01                 否

  API-02      POST                  /api/v1/auth/register                      手机号注册               UR-01 ～ UR-03        否

  API-03      POST                  /api/v1/auth/login                         密码登录                 UR-04、UR-05          否

  API-04      POST                  /api/v1/auth/login/sms                     验证码登录               UR-01、UR-04          否

  API-05      POST                  /api/v1/auth/token/refresh                 刷新令牌续期             UR-06                 否

  API-06      POST                  /api/v1/auth/logout                        登出并失效令牌           UR-06                 是

  API-07      POST                  /api/v1/auth/password/reset                验证码重置密码           UR-07                 否

  API-08      GET                   /api/v1/users/me                           查询当前用户资料         UR-08、UR-09          是

  API-09      PUT                   /api/v1/users/me                           更新资料与头像           UR-08                 是

  API-10      GET/POST/PUT/DELETE   /api/v1/users/addresses                    收货地址增删改查         UR-10、BR-05          是

  API-11      GET                   /api/v1/categories                         分类树                   PR-01                 否

  API-12      POST                  /api/v1/uploads/presign                    图片上传预签名           PR-02、BR-07          是

  API-13      POST                  /api/v1/items                              发布商品                 PR-01 ～ PR-08、BR-06 是
                                                                                                        ～ BR-09              

  API-14      PUT                   /api/v1/items/{id}                         编辑商品                 PR-04                 是

  API-15      GET                   /api/v1/items/{id}                         商品详情                 SR-09                 否

  API-16      POST                  /api/v1/items/{id}/status                  上下架与删除             PR-05、PR-06、BR-10   是

  API-17      GET                   /api/v1/items/mine                         我的发布列表             PR-10                 是

  API-18      GET                   /api/v1/search                             商品检索与筛选           SR-01 ～ SR-04、SR-12 否

  API-19      GET                   /api/v1/search/suggest                     搜索联想                 SR-05                 否

  API-20      GET                   /api/v1/search/hot                         热门搜索词               SR-06                 否

  API-21      POST                  /api/v1/favorites                          收藏与取消收藏           SR-10                 是

  API-22      GET                   /api/v1/favorites                          收藏列表                 SR-10                 是

  API-23      GET                   /api/v1/footprints                         浏览足迹                 SR-11                 是

  API-24      POST                  /api/v1/conversations                      创建会话（联系卖家）     CT-01                 是

  API-25      GET                   /api/v1/conversations                      会话列表                 CT-02、CT-07          是

  API-26      GET                   /api/v1/conversations/{id}/messages        历史消息分页             CT-12                 是

  API-27      POST                  /api/v1/messages                           发送消息（HTTP 兜底）    CT-03、BR-14、BR-15   是

  API-28      WS                    /ws                                        长连接：收发消息与回执   CT-04 ～ CT-09、CT-11 是

  API-29      POST                  /api/v1/orders                             创建订单（含议价下单）   OR-01 ～              是
                                                                                                        OR-05、OR-18、OR-19   

  API-30      GET                   /api/v1/orders                             订单列表（买 / 卖）      OR-08、OR-17          是

  API-31      GET                   /api/v1/orders/{orderNo}                   订单详情与时间线         OR-09、OR-13          是

  API-32      POST                  /api/v1/orders/{orderNo}/pay               支付（模拟通道）         OR-06、OR-07          是

  API-33      POST                  /api/v1/orders/{orderNo}/cancel            取消订单                 OR-10、OR-11、BR-19   是

  API-34      POST                  /api/v1/orders/{orderNo}/ship              卖家发货                 OR-12                 是

  API-35      POST                  /api/v1/orders/{orderNo}/confirm           确认收货                 OR-14                 是

  API-36      POST                  /api/v1/orders/{orderNo}/refund            申请退款与退货           OR-15                 是

  API-37      POST                  /api/v1/orders/{orderNo}/dispute           发起申诉                 OR-16                 是

  API-38      POST                  /api/v1/reviews                            提交与修改评价           RV-01 ～ RV-03、BR-23 是

  API-39      GET                   /api/v1/reviews                            评价列表（卖家维度）     RV-04                 否

  API-40      POST                  /api/v1/reports                            提交举报                 RP-01 ～ RP-03、BR-24 是

  API-41      GET                   /api/v1/reports/mine                       我的举报进度             RP-04                 是

  API-42      POST                  /api/v1/admin/login                        管理员登录               AD-01                 否

  API-43      POST                  /api/v1/admin/items/{id}/audit             商品审核通过 / 驳回      AD-01、BR-25          是（ADMIN）

  API-44      POST                  /api/v1/admin/users/{id}/action            用户封禁与解封           AD-02、BR-25          是（ADMIN）

  API-45      POST                  /api/v1/admin/orders/{orderNo}/intervene   订单干预与判定           AD-03、BR-25          是（ADMIN）

  API-46      POST                  /api/v1/admin/reports/{id}/handle          举报受理与判定           AD-04、BR-25          是（ADMIN）

  API-47      GET                   /api/v1/admin/dashboard                    数据看板指标             AD-06                 是（ADMIN）
  -----------------------------------------------------------------------------------------------------------------------------------------

## **6.3 核心接口示例**

### **6.3.1 注册与登录 API-02、API-03**

> POST /api/v1/auth/register
>
> 请求：{ \"phone\": \"13800138000\", \"smsCode\": \"836291\",
> \"nickname\": \"闲置达人\", \"password\": \"Abc12345\" }
>
> 成功响应：{ \"code\": 0, \"message\": \"注册成功\",
>
> \"data\": { \"accessToken\": \"eyJhbGciOi\...\", \"refreshToken\":
> \"rt_9f2c\...\",
>
> \"expiresIn\": 7200, \"userId\": 10001 } }
>
> 失败响应：
>
> { \"code\": 1001, \"message\": \"请输入正确的手机号\" }
>
> { \"code\": 1002, \"message\": \"验证码错误或已失效\" }
>
> { \"code\": 1003, \"message\": \"昵称长度为2～20个字符\" }
>
> { \"code\": 1004, \"message\":
> \"密码为8～20位，且需同时包含字母与数字\" }
>
> { \"code\": 1005, \"message\": \"密码不能与手机号相同\" }
>
> { \"code\": 1006, \"message\":
> \"密码不能为连续或重复字符，请重新设置\" }
>
> { \"code\": 1007, \"message\": \"该手机号已注册，请直接登录\" }
>
> POST /api/v1/auth/login
>
> 请求：{ \"phone\": \"13800138000\", \"password\": \"Abc12345\" }
>
> 成功响应：{ \"code\": 0, \"message\": \"登录成功\", \"data\": {
> \"accessToken\": \"\...\", \"refreshToken\": \"\...\" } }
>
> 失败响应：
>
> { \"code\": 1101, \"message\": \"手机号或密码错误，请重试\", \"data\":
> { \"failCount\": 3, \"remainTimes\": 2 } }
>
> { \"code\": 1102, \"message\":
> \"密码错误次数过多，账号已锁定，请28分钟后重试\", \"data\": {
> \"remainSeconds\": 1680 } }

代码清单 4 注册与登录接口示例

### **6.3.2 商品检索 API-18**

> GET
> /api/v1/search?q=iphone13&categoryId=101&condition=2,3&minPrice=1000&maxPrice=4000
>
> &cityCode=SZ&tradeType=1&freeShipping=true&sort=relevance&page=1&size=20
>
> 成功响应：
>
> { \"code\": 0, \"message\": \"ok\",
>
> \"data\": { \"total\": 138, \"page\": 1, \"size\": 20,
>
> \"list\": \[ { \"itemId\": 88012, \"title\": \"iPhone 13 128G 国行\",
> \"price\": 2899.00,
>
> \"conditionLevel\": 2, \"cityName\": \"深圳\", \"coverUrl\": \"\...\",
>
> \"highlight\": { \"title\": \"iPhone 13 128G 国行\" }, \"sellerName\":
> \"闲置达人\" } \] } }
>
> 失败响应：
>
> { \"code\": 3001, \"message\": \"关键词过长，请精简后重试\" }
>
> { \"code\": 3002, \"message\": \"价格区间不正确，请重新输入\" }
>
> { \"code\": 3003, \"message\":
> \"没有找到相关商品，试试减少筛选条件或更换关键词\" }

代码清单 5 商品检索接口示例

### **6.3.3 长连接消息协议 API-28**

> 连接：WS /ws?token=\<accessToken\>
>
> 客户端上行（发送消息）：
>
> { \"type\": \"MESSAGE_SEND\", \"seq\": 1024, \"ack\": false,
> \"timestamp\": 1758000000000,
>
> \"payload\": { \"clientMsgId\": \"c9f1-\...\", \"conversationId\":
> 5501,
>
> \"msgType\": \"TEXT\", \"content\": \"还能便宜一点吗\" } }
>
> 服务端下行（投递）：
>
> { \"type\": \"MESSAGE_PUSH\", \"seq\": 88, \"ack\": true,
> \"timestamp\": 1758000000120,
>
> \"payload\": { \"messageId\": \"665f\...\", \"conversationId\": 5501,
> \"senderId\": 10002,
>
> \"msgType\": \"TEXT\", \"content\": \"还能便宜一点吗\", \"seq\": 88 }
> }
>
> 客户端回执：{ \"type\": \"ACK\", \"seq\": 88, \"payload\": {
> \"messageId\": \"665f\...\" } }
>
> 服务端回执（发送结果）：
>
> { \"type\": \"MESSAGE_ACK\", \"seq\": 1024, \"payload\": {
> \"clientMsgId\": \"c9f1-\...\",
>
> \"messageId\": \"665f\...\", \"status\": \"SENT\" } }
>
> 心跳：客户端每 30 秒发送 { \"type\": \"PING\" }，服务端回 { \"type\":
> \"PONG\" }；
>
> 连续 2 个周期未收到 PONG 视为断线，按 1s / 2s / 4s / 8s / 16s
> 指数退避重连，
>
> 重连时携带 lastSeq 补齐断连期间消息。

代码清单 6 WebSocket 消息协议示例

### **6.3.4 下单与交易 API-29、API-32、API-34、API-35**

> POST /api/v1/orders
>
> 请求：{ \"itemId\": 88012, \"quantity\": 1, \"addressId\": 31,
> \"priceCardId\": 7702 }
>
> 成功响应：{ \"code\": 0, \"message\":
> \"订单创建成功，请在15分钟内完成支付\",
>
> \"data\": { \"orderNo\": \"IDX20260924000137\", \"totalAmount\":
> 2899.00,
>
> \"status\": \"PENDING_PAYMENT\", \"payExpireAt\":
> \"2026-09-24T10:15:00+08:00\" } }
>
> 失败响应：
>
> { \"code\": 5001, \"message\": \"该商品已售出，去看看其他商品吧\" }
>
> { \"code\": 5002, \"message\": \"库存不足，当前仅剩0件\" }
>
> { \"code\": 5003, \"message\": \"请选择收货地址\" }
>
> { \"code\": 5004, \"message\": \"改价已失效，请重新与卖家确认价格\" }
>
> POST /api/v1/orders/IDX20260924000137/pay
>
> 请求：{ \"channel\": \"MOCK\" }
>
> 成功响应：{ \"code\": 0, \"message\": \"支付成功，资金已托管\",
> \"data\": { \"status\": \"PAID\" } }
>
> 失败响应：{ \"code\": 5005, \"message\":
> \"订单已超时关闭，请重新下单\" }
>
> { \"code\": 5006, \"message\": \"订单状态不允许支付\" }
>
> POST /api/v1/orders/{orderNo}/ship
>
> 请求：{ \"logisticsCompany\": \"顺丰速运\", \"trackingNo\":
> \"SF1234567890\" }
>
> 成功响应：{ \"code\": 0, \"message\": \"发货成功\", \"data\": {
> \"status\": \"SHIPPED\" } }
>
> POST /api/v1/orders/{orderNo}/confirm
>
> 成功响应：{ \"code\": 0, \"message\": \"已确认收货，交易完成\",
> \"data\": { \"status\": \"COMPLETED\" } }
>
> 失败响应：{ \"code\": 5007, \"message\": \"该订单不支持确认收货\" }
>
> { \"code\": 5008, \"message\": \"订单不存在\" }

代码清单 7 下单与交易接口示例

# **7 关键设计**

## **7.1 认证与会话**

> · 注册：手机号经验证码校验后写入 users 表，密码使用 Argon2id
> 加盐哈希存储，系统不保存明文，也不提供反查。
>
> · 双令牌：访问令牌有效期 2 小时，刷新令牌 7 天；刷新令牌记录于
> Redis，支持滑动续期，登出、改密与封禁时删除记录实现即时失效。
>
> · 登录校验顺序：手机号格式 → 锁定状态 → 密码比对；密码错误以
> auth:fail:{phone} 计数，达到 5 次写入 locked_until（30 分钟），返回
> 1102 及剩余解锁秒数。
>
> ·
> 账号枚举防护：手机号未注册时统一按「手机号或密码错误，请重试」提示，响应耗时与已注册场景保持一致（BR-04）。
>
> · 多端登录：同一账号允许多端在线，刷新令牌按 jti
> 区分；管理端使用独立账号表 admin_users 与独立令牌，两套令牌互不可用。
>
> · 验证码：短信验证码 5 分钟有效，同一号码 60
> 秒内只能获取一次，单号码单日上限 10 次，超出触发图形验证码。

## **7.2 检索与索引**

> · 分词与相关性：标题与描述使用 ik_max_word 索引、ik_smart
> 检索；综合排序采用 function_score，以 BM25
> 相关性为主分，叠加成色、浏览量与时间衰减权重。
>
> · 筛选与排序：分类、成色、城市、交易方式与是否包邮走 filter
> 上下文，结果可被节点缓存；价格与时间为区间与排序字段。
>
> · 联想与热词：suggest 字段使用 completion 类型支撑输入联想；热门词以
> Redis ZSet 统计近 7 天搜索次数，每小时持久化一次。
>
> · 索引同步：商品服务在发布、编辑、上下架后发送 Kafka 事件，indexer
> 消费者更新索引；失败重试 3
> 次后进入死信并告警，定时任务每小时对账补偿。
>
> · 降级策略：Elasticsearch 不可用时切换至 PostgreSQL
> 全文检索（tsvector + GIN 索引）与分类筛选，限制分页深度并告警。
>
> ·
> 无结果处理：无结果时按同分类与相似价格区间回源推荐，并提示减少筛选条件（SR-07）。

## **7.3 即时通讯**

> · 连接管理：消息服务节点无状态，连接建立时在 Redis 记录
> im:conn:{userId} →
> 节点标识；节点下线时清理自身记录，避免投递到失效节点。
>
> · 投递流程：消息先落 MongoDB 并取得
> seq，再按接收方所在节点定向投递；跨节点通过 Redis Pub/Sub
> 转发，节点内直接写入连接。
>
> · 可靠投递：服务端推送需客户端回 ACK，未收到 ACK
> 的消息进入重试队列，最多重试 3 次；接收方离线时写入
> offline_messages，上线后按 seq 补发。
>
> · 幂等去重：客户端发送消息携带 clientMsgId，服务端以
> message_idempotent 集合去重，重复提交返回首次结果，避免消息重复。
>
> · 未读计数：会话级未读存于 Redis
> Hash，进入会话清零并异步持久化；节点重启后按 MongoDB
> 中最后已读位点重新计算校正。
>
> · 心跳与重连：30 秒心跳，连续 2
> 次无响应判定断线，客户端按指数退避重连并携带 lastSeq
> 补齐消息（CT-08）。
>
> · 撤回：2 分钟内允许撤回，更新消息 revoked_at
> 并推送撤回事件，双方会话展示「消息已撤回」（CT-09）。
>
> · 水平扩展：消息服务按连接数扩容，节点间不共享内存状态，全部经 Redis
> 与 MongoDB 协作。

## **7.4 图片上传与处理**

> · 直传：客户端调用 API-12 获取预签名地址后直传
> MinIO，图片流量不穿透应用服务；预签名地址 5
> 分钟有效且限定内容类型与大小。
>
> · 校验：服务端在签发前校验数量（1 ～ 9）、格式（jpg / png /
> webp）与大小（单张不超过 10 MB），不满足直接拒绝（BR-07）。
>
> · 异步处理：上传完成后发送图片处理事件，异步任务生成 200 / 400 / 800
> 三档缩略图并转 WebP，同时清除 EXIF 位置信息，完成后回写 item_images。
>
> ·
> 审核：原图进入机器审核，疑似违规的置为待审并通知卖家；审核通过前商品不进入检索索引。
>
> · 访问：图片通过 CDN
> 分发，凭证类图片使用带时效的签名地址，不公开列举。

## **7.5 库存与并发**

二手商品多为单件，超卖会直接导致交易纠纷，因此库存以「Redis 原子锁 +
数据库事务扣减」双重保障。

> · 预占库存：下单时以 Lua 脚本原子校验并写入 stock:lock:{itemId}，锁定
> 15 分钟；库存不足直接返回 5001 / 5002。
>
> · 事务扣减：支付成功后在数据库事务内扣减 items.stock
> 并写入库存流水，以 stock:deduct:{orderNo} 做幂等标记，防止重复扣减。
>
> · 超时释放：待付款订单 15
> 分钟超时由定时任务关闭，删除锁定标记并回补可售库存；取消与退款同样触发释放。
>
> ·
> 并发安全：订单状态流转与库存更新使用乐观锁（version）配合条件更新，防止并发操作相互覆盖。
>
> · 售罄处理：库存为 0 时商品自动置为已售出并同步下架检索索引。

## **7.6 订单状态机与定时任务**

![](media/image2.png){width="5.972222222222222in"
height="2.6948293963254595in"}

图 2 交易订单状态机

> · 状态定义：待付款 PENDING_PAYMENT → 待发货 PAID → 已发货 SHIPPED →
> 已完成 COMPLETED；另设已关闭 CLOSED、退款中 REFUNDING、已退款
> REFUNDED、争议中 DISPUTING。
>
> · 流转控制：由 statemachine
> 统一管理，定义每个状态允许的下一状态集合；非法流转直接拒绝并返回错误码。
>
> ·
> 客户端不提交目标状态，只提交动作（支付、发货、确认收货、申请退款、申诉），由服务端决定目标状态。
>
> · 流转留痕：每次状态变更写入 order_status_logs，记录
> from_status、to_status、action、operator_type（BUYER / SELLER / SYSTEM
> / ADMIN）与时间。
>
> · 定时任务：每分钟扫描待付款超时订单关闭并释放库存；每日扫描发货满 10
> 天的订单自动确认收货并结算；退款申请超过 48 小时未处理自动同意。
>
> · 幂等：定时任务按订单号加锁执行，重复执行不产生重复流转记录。

## **7.7 风控与内容安全**

> · 敏感词：基于 DFA
> 算法构建词树，商品标题描述与消息内容在写入前过滤；命中时按词级别拦截或替换为
> \*（PR-11、CT-10）。
>
> ·
> 图片审核：图片经机器审核与抽样人工审核，疑似违规商品置为审核中并暂停展示。
>
> · 限流：网关层按 IP
> 与用户维度限流；发消息、发布商品、搜索等接口单独配置阈值，超出返回 429
> 与友好提示。
>
> · 反爬：商品详情与检索接口对高频匿名访问启用滑块验证与访问频控。
>
> ·
> 举报闭环：举报进入待受理队列，管理端判定成立后下架商品或处置账号，结果以系统消息通知举报人（RP-04、AD-04）。
>
> ·
> 信用分：根据成交、评价与违规记录更新用户信用等级，作为排序权重与风控输入。

## **7.9 Python 运行时与并发策略**

Python 服务以 asyncio 单线程事件循环加多进程的方式运行，针对 IO
密集特征做专门设计，避免 GIL 成为瓶颈。

> · 运行时：以 uvicorn 作为 ASGI 服务器，单容器内以 gunicorn 管理多
> worker（worker 数按 CPU
> 核数配置），进程间不共享内存状态，会话与连接路由全部外置 Redis。
>
> · IO 密集为主：检索调用、数据库访问、Redis、Kafka
> 与对象存储均为异步客户端（asyncpg、redis-py
> asyncio、motor、aiokafka、elasticsearch-py async），全程 await
> 不阻塞事件循环。
>
> · CPU 密集卸载：图片缩略图生成、EXIF 处理与敏感词大规模重建等 CPU
> 密集任务交由 Celery Worker 独立进程池执行，不占用 API 服务的事件循环。
>
> · 长连接容量：WebSocket 为空闲长连接，内存占用低，单 worker
> 可支撑数千连接；消息服务按连接数水平扩容
> Pod，不做单机连接数上限硬约束。
>
> · 阻塞调用隔离：确需使用同步 SDK 的场景（如部分第三方客户端）通过
> run_in_executor 线程池隔离，避免阻塞事件循环。
>
> · 性能验证：以 Locust 对检索、下单与消息投递链路压测，校验 P95
> 达标；发现事件循环阻塞时以 py-spy 采样定位热点。

## **7.8 异常处理与提示语**

> · 定义统一业务错误结构，携带错误码与提示语，由全局中间件转为统一响应。
>
> · 错误码分段：1xxx 账号、2xxx 商品、3xxx 检索、4xxx 消息、5xxx
> 订单、6xxx 评价与举报、9xxx 系统。
>
> · 所有提示语集中在 messages 配置（如
> user.phone.invalid、order.stock.empty），与需求文档中的中文文案一一对应。
>
> · 未知异常统一转为「服务繁忙，请稍后再试」并记录完整日志与链路
> ID，避免向用户暴露系统细节。
>
> · 所有服务默认接入 OpenTelemetry 埋点，异常日志携带
> trace_id，便于跨服务定位。

# **8 安全设计**

  ---------------------------------------------------------------------------------------------------------------------------------
  **方面**                **措施**                                                                         **对应风险**
  ----------------------- -------------------------------------------------------------------------------- ------------------------
  身份认证                除注册、登录、验证码、重置密码与公开检索外全量鉴权；双令牌与刷新令牌可即时失效   未授权访问

  密码安全                密码 Argon2id 加盐存储；弱口令拦截；重置后全部登录态失效                         密码泄露与撞库

  暴力破解                连续 5 次失败锁定 30 分钟；登录与验证码接口限流；失败提示不区分账号是否存在      密码暴力枚举与账号枚举

  越权访问                订单、会话、地址资源服务端解析用户标识并强制归属校验；他人资源统一提示不存在     水平越权与信息泄露

  上传安全                预签名限定类型与大小；异步清除 EXIF；图片机器审核；凭证图片带时效签名            恶意文件上传与隐私泄露

  注入防护                全程参数化查询（SQLAlchemy 参数绑定），禁止 SQL 与命令拼接                       SQL 注入

  内容安全                敏感词过滤、图片审核、举报处置与信用分联动                                       违规内容传播

  传输安全                生产环境全站 HTTPS；网关终止 TLS；内部服务间通信启用 mTLS                        中间人窃听

  日志脱敏                密码、令牌、手机号在日志中脱敏输出                                               敏感信息外泄

  审计留痕                订单流转、管理端处置、封禁与退款操作全量留痕                                     操作不可追溯

  依赖与镜像              依赖漏洞扫描与镜像签名，基础镜像定期更新                                         供应链攻击
  ---------------------------------------------------------------------------------------------------------------------------------

# **9 部署架构**

## **9.1 部署拓扑**

![](media/image3.png){width="6.111111111111111in"
height="3.9420319335083116in"}

图 3 部署架构（Kubernetes）

## **9.2 环境与组件**

  ----------------------------------------------------------------------------------------------------------------
  **组件**          **部署形态**                    **端口**          **说明**
  ----------------- ------------------------------- ----------------- --------------------------------------------
  前端制品          CDN + 对象存储静态托管          443               React 构建产物，开启 gzip 与缓存

  user / item /     Deployment（无状态，uvicorn +   8080              按 CPU 与 QPS 弹性伸缩，最少 2 副本
  trade 服务        gunicorn）                                        

  search 服务       Deployment（无状态，uvicorn）   8080              按检索 QPS 独立扩容

  im 服务           Deployment（长连接，uvicorn）   8081              按连接数扩容，Pod 优雅退出需等待连接迁移

  admin 服务        Deployment                      8080              管理端接口，不与外部业务共用

  worker 作业       Deployment + Celery Beat        ---               Kafka 消费者（aiokafka）与 Celery
                                                                      定时任务：indexer、image、notify、schedule

  PostgreSQL        StatefulSet 或云托管主从        5432              业务主库，字符集 UTF8

  MongoDB           副本集                          27017             消息库，按 conversation_id 分片

  Elasticsearch     3 节点集群                      9200              商品检索，分片 3 副本 1

  Redis             哨兵或集群                      6379              缓存、会话、锁与未读

  Kafka             3 Broker                        9092              事件总线

  MinIO             分布式部署                      9000              对象存储

  观测组件          Prometheus + Grafana + Loki     ---               指标、看板与日志
  ----------------------------------------------------------------------------------------------------------------

## **9.3 环境划分**

  --------------------------------------------------------------------------------------------
  **环境**                **用途**                **关键差异**
  ----------------------- ----------------------- --------------------------------------------
  dev 开发环境            开发自测与联调          单副本部署，Elasticsearch 与 MongoDB
                                                  单节点，模拟支付通道

  test 测试环境           测试执行与缺陷验证      数据与生产隔离；保留压测数据；开启全量日志

  staging 预发环境        发布前验证              与生产同规格缩量部署，使用生产配置模板

  prod 生产环境           正式使用                多副本高可用、全站 HTTPS、定期备份、告警全开
  --------------------------------------------------------------------------------------------

## **9.4 基础数据初始化**

  -----------------------------------------------------------------------------------------
  **数据项**              **初始化方式**                   **说明**
  ----------------------- -------------------------------- --------------------------------
  分类树 categories       迁移脚本（migrations）           三级分类，覆盖常见闲置品类

  城市编码                迁移脚本                         支撑所在地筛选与展示

  敏感词库                迁移脚本 + 管理端维护            初始内置通用词库，支持运营扩展

  管理员初始账号          迁移脚本创建，首次登录强制改密   仅初始化一次，不进用户账号体系

  Elasticsearch 索引      初始化脚本创建 mapping           indexer
                                                           启动前必须存在，否则重建失败
  -----------------------------------------------------------------------------------------

# **10 非功能性设计**

  ---------------------------------------------------------------------------------------------------------------------------------
  **类别**                **设计方案**                                                   **目标**
  ----------------------- -------------------------------------------------------------- ------------------------------------------
  性能                    检索下沉 Elasticsearch；热门商品与分类缓存                     搜索 P95 不超过 500 毫秒；商品详情不超过
                          Redis；前端组件懒加载与图片懒加载                              300 毫秒

  实时性                  长连接投递 + 离线补发 + 心跳重连                               消息端到端送达不超过 500 毫秒，离线不丢失

  容量                    服务无状态多副本；数据库与中间件独立部署；消息与检索独立扩容   支撑 10 万注册用户、10 万日活、5000
                                                                                         并发、500 万商品、日均 5 万单

  可用性                  健康检查与自动重启；滚动发布与一键回滚；多副本反亲和部署       单实例故障不影响整体可用，发布期间不中断

  数据一致性              状态机流转、乐观锁、库存双保障、索引对账补偿                   不超卖、不丢消息、状态不跳变

  可扩展性                服务按业务边界拆分，事件驱动解耦；支付与物流通道抽象           新增业务能力不影响既有服务

  可维护性                统一响应与错误码、集中提示语、结构化日志与链路追踪             问题可在 10 分钟内定位到服务与接口

  可观测性                Prometheus 指标 + OpenTelemetry 链路 + Loki 日志 + Grafana     核心指标异常可告警、可下钻
                          看板                                                           

  兼容性                  响应式布局适配 1366×768 及以上分辨率；支持 Chrome / Edge /     主流终端可用，界面不错位
                          Safari 主流版本与移动端 H5                                     

  数据备份                PostgreSQL 每日全量 + WAL 增量保留 30 天；MongoDB              数据可恢复至任意时间点
                          每日快照；MinIO 跨桶复制                                       
  ---------------------------------------------------------------------------------------------------------------------------------

# **11 测试策略**

  ---------------------------------------------------------------------------------------------------------------------------
  **测试类型**            **范围**                                                 **方式**
  ----------------------- -------------------------------------------------------- ------------------------------------------
  单元测试                敏感词过滤、价格计算、库存锁                             pytest + pytest-asyncio，配合 respx 与
                          Lua、状态机流转、双令牌签发与刷新、消息去重              mongomock 覆盖合法类、边界值与非法类

  接口测试                API-01 ～ API-47                                         按参数合法 / 非法 / 边界 /
                                                                                   空值组合执行，校验返回码与提示语

  检索专项                中文分词、同义词、筛选组合、排序、联想、无结果降级       构造语料校验召回与排序，校验降级链路可用

  消息专项                实时送达、离线补发、断线重连、幂等去重、未读计数、撤回   两客户端对测，模拟断网与重连

  并发与库存              单件商品并发下单、重复支付、超时释放、退款回补           脚本并发压测，校验不超卖且库存守恒

  状态机专项              支付、发货、确认、取消、退款、申诉、超时关闭与自动确认   重点验证非法流转被拒与流转留痕完整

  安全测试                越权访问、未登录访问、SQL 注入、文件上传绕过、限流生效   手工验证结合自动化扫描

  性能压测                检索、商品详情、下单、消息投递四条主链路                 Locust 脚本压测，校验 P95 与错误率达标

  回归测试                每次缺陷修复后的核心链路                                 注册 → 发布 → 检索 → 沟通 → 下单 → 支付 →
                                                                                   发货 → 收货 → 评价 全链路回归
  ---------------------------------------------------------------------------------------------------------------------------

# **12 技术风险与演进**

  --------------------------------------------------------------------------------------------------------------------------------------------
  **编号**          **风险 / 事项**                  **影响**                   **应对**
  ----------------- -------------------------------- -------------------------- --------------------------------------------------------------
  T-01              索引同步延迟导致商品检索不到     新发布商品曝光延迟         同步时效 3
                                                                                秒内并监控积压；提供手动重建索引入口；检索降级可回源

  T-02              长连接节点扩容时连接迁移抖动     消息瞬时延迟或重连风暴     优雅退出等待连接迁移；客户端指数退避重连；按连接数提前扩容

  T-03              单件商品在高关注下并发下单       超卖引发纠纷               Redis 原子锁库存 + 数据库事务扣减 + 幂等标记三重保障；压测验证

  T-04              消息量增长导致 MongoDB 写入压力  消息延迟或存储成本上升     按 conversation_id 分片；历史消息冷热分离，超过 1 年归档

  T-05              图片审核依赖外部服务             审核成本与合规风险         本期机器审核 + 人工抽检；接口抽象，后续可替换服务商

  T-06              支付本期为模拟通道               与真实资金流存在差异       支付网关抽象，订单已记录支付通道与流水字段，后续替换实现即可

  T-07              物流轨迹未对接外部接口           用户无法查看实时轨迹       保留物流公司与运单号字段，查询接口预留，后续接入快递鸟等服务

  T-08              多服务架构带来运维复杂度         排障与发布成本上升         统一脚手架与 Helm Chart；链路追踪与看板先行建设

  T-09              Elasticsearch 集群资源占用较高   成本压力                   按检索量独立扩容；冷数据降副本；必要时降级至 PostgreSQL
                                                                                全文检索

  T-10              Python                           长连接延迟抖动与吞吐下降   全程异步客户端；CPU 密集任务交 Celery 卸载；同步 SDK
                    全局解释器锁与事件循环阻塞风险                              走线程池隔离；以 py-spy 常态采样监控
  --------------------------------------------------------------------------------------------------------------------------------------------

## **演进路线建议**

> ·
> 第一阶段：完成用户、商品、检索、消息、交易五大模块与订单状态机，模拟支付，单集群部署。
>
> ·
> 第二阶段：完善内容安全（机器审核与举报闭环）、推荐流与数据看板，补齐压测与告警。
>
> · 第三阶段：对接真实支付通道与物流轨迹，引入资金结算与对账能力。
>
> ·
> 第四阶段：扩展推荐与搜索个性化、信用体系、直播鉴宝与验货担保等高阶交易保障能力。
