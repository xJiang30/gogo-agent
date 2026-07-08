# AI 旅行 Agent MVP 设计方案

日期：2026-07-07  
状态：设计已确认，等待书面规格审阅

## 1. 项目目标

面向中国大陆用户，构建一个桌面 Web 优先的 AI 原生旅行规划 MVP：

1. 用户从一句不完整的自然语言旅行想法开始。
2. 系统只追问必要信息，并生成恰好三个可编辑的计划方向。
3. 用户选择一个方向后进入 Trip Board，以时间线、地图、交通段和酒店查看完整行程。
4. 用户可以直接编辑行程节点，也可以围绕某个节点与 AI 进行多轮讨论。
5. AI 默认只提供建议。只有用户明确批准、委托执行，或未来主动开启自动模式后，AI 才能影响正式行程状态。
6. 发现、比较、规划和编辑都在本产品内完成；一期仅在预订或导航时通过深链跳转到外部平台。

MVP 不要求用户先去其他平台搜集并粘贴资料。链接、截图等导入能力只是后续补充入口，不是核心工作流。

## 2. 范围

### 2.1 一期能力

- 用户登录和旅行数据持久化
- 对话式旅行需求收集
- 三个结构化候选计划
- 按天、按时间组织的可编辑 Trip Board
- 高德 POI 搜索、地图渲染和路线规划
- 地点、餐饮、酒店、活动、抵达和离开节点
- 节点之间显式建模的交通段
- 节点级多轮讨论
- 住宿、交通和游玩研究 Specialist Agent
- Proposal 差异展示、接受、拒绝、版本冲突处理和撤销
- 预算与路线校验
- 预订平台和导航平台深链
- Agent Trace、确定性测试和初始评测数据集
- 邀请制邮箱密码登录和服务端 Session

### 2.2 一期不做

- 实时酒店库存或票务库存
- 站内预订、支付、取消或客服
- 原生移动端应用
- 浏览器插件或系统分享扩展
- 链接、截图、PDF 或邮件解析
- 价格监控和定时提醒
- 自由协作的 Agent Swarm
- 无边界的长期对话记忆
- 完整多人协作或组织权限体系
- 面向用户的自动执行模式；一期只保留策略字段，对外提供人工确认和单次明确委托

## 3. 产品原则

### 3.1 AI 默认是建议者

用户直接编辑 Trip Board。AI 可以解释、研究、比较和提出修改建议。除非用户明确委托，否则任何正式状态变化都必须先生成 `TripProposal` 并由用户批准。

### 3.2 Trip 数据库是唯一真实状态

行程是结构化应用状态，不是一篇 AI 生成文章，也不是聊天记录。PostgreSQL 保存唯一正式 Trip State；LangGraph Checkpoint 只保存某次 Agent Run 的临时执行状态。

### 3.3 地图是时间线的投影视图

Trip 节点和交通段同时驱动时间线与地图。编辑节点时先更新结构化时间线，再重算受影响的交通段和地图路线。

### 3.4 重要建议必须可追溯

建议必须记录数据来源、获取时间、置信度、风险和缺失信息。系统不能把不确定的外部数据静默转换成确定事实。

## 4. 系统架构

```text
Next.js Web
  - Trip Board
  - 对话和节点讨论
  - 高德地图可视化
  - Proposal Diff 和确认
  - 乐观交互状态
          |
          | 自动生成的 OpenAPI Client + SSE
          v
FastAPI Application
  - 认证与授权
  - Trip 和 Discussion API
  - Proposal Executor
  - Agent 流式接口
  - 领域服务与 Provider 服务
          |
          +--> Travel Advisor
          |      +--> Plan Agent
          |      +--> Stay Agent
          |      +--> Mobility Agent
          |      +--> Experience Agent
          |      +--> 确定性 Validators
          |
          +--> LangGraph Manager
          |      - 初始计划生成
          |      - 复杂研究
          |      - 跨天重规划
          |
          +--> Provider Adapters
                 - 通义千问 / DeepSeek
                 - 高德
                 - 天气
                 - Web Search
                 - 平台深链
          |
          v
PostgreSQL + PostGIS
  - 正式 Trip State
  - Discussion 和 Message
  - Proposal 和 DecisionLog
  - AgentRun 和 LangGraph Checkpoint
```

### 4.1 状态所有权

- Next.js 只拥有临时交互状态。
- FastAPI 是唯一对外业务 API。
- PostgreSQL 是唯一正式 Trip State 来源。
- Agent 可以读取带版本号的 `TripSnapshot`，但不能写 Trip 正式表。
- LangGraph 可以保存 Run Checkpoint，但不能把它当作正式 Trip State。
- 从 AI 输出到正式状态修改只能经过 `ProposalExecutor`。

## 5. 受控多 Agent 设计

MVP 使用 Manager Pattern，不使用自由多 Agent 协作。

### 5.1 用户可见 Agent

`TravelAdvisor` 是用户唯一感知到的 AI 身份。它负责理解意图、追问、选择能力、解释取舍，并保持对话连续性。

### 5.2 Specialist Agents

- `PlanAgent`：根据不完整需求生成三个连贯的计划方向。
- `StayAgent`：研究住宿区域、候选酒店、通勤影响、灵活性和参考价格。
- `MobilityAgent`：比较交通类别、路线耗时、换乘和特定交通风险。
- `ExperienceAgent`：研究 POI、餐饮、活动、替代项和旅行适配度。

所有 Specialist 必须：

- 接收明确的 `ResearchBrief` 和不可变 `TripSnapshot`。
- 返回严格的 `ResearchResult` Schema。
- 不直接与用户对话。
- 不修改正式 Trip State。
- 不互相聊天。
- 每次最多返回三个用户可见候选项。

### 5.3 确定性服务

预算计算、路线校验、营业时间检查、冲突检测、Proposal 执行和版本检查均使用普通 Python 服务，不做成 Agent。

### 5.4 LangGraph 使用边界

使用 LangGraph：

- 并行查询 Specialist 的初始计划生成
- 需要多轮工具调用的复杂领域研究
- 跨天重规划
- 复杂 Run 的持久化暂停和恢复

不使用 LangGraph：

- 普通 Trip CRUD
- 简单节点问答
- 用户直接手动编辑
- 地图渲染
- 每一个对话回合

## 6. 对话和 Agent 流程

### 6.1 初始规划

```text
用户旅行想法
  -> TravelAdvisor 提取已知信息和关键缺口
  -> 只追问阻塞性问题
  -> LangGraph 并行调用相关 Specialists
  -> 确定性预算和路线校验
  -> PlanAgent 生成恰好三个计划方向
  -> 用户选择并编辑一个方向
  -> 用户确认后才创建正式 Trip
```

### 6.2 节点级讨论

每个行程节点可以拥有一个或多个 `NodeDiscussion`。上下文包括：

- Discussion 摘要和最近消息
- 当前节点和相邻节点
- 有效 Trip 约束和偏好
- 未处理的 Proposal
- 正式 Trip 版本号

根据复杂度逐级升级：

```text
L1 解释              -> 直接模型回答
L2 事实研究          -> 动态调用 Provider Tools
L3 局部替换          -> 节点级 TripProposal
L4 跨天影响          -> LangGraph 重规划工作流
```

### 6.3 上下文管理

不能每轮都把完整 Trip 和全部聊天历史发给模型。上下文由结构化 Trip 数据、滚动 Discussion 摘要、最近消息、未解决 Proposal 和相关时间邻域构建。

## 7. Proposal 协议

Agent 输出仅允许三种类型：

- `Answer`：解释，不涉及状态变化
- `RecommendationSet`：恰好三个候选项，供讨论或选择
- `TripProposal`：正式、可审阅的修改建议

```python
class TripProposal(BaseModel):
    id: UUID
    trip_id: UUID
    base_version: int
    scope: Literal["node", "day", "trip"]
    title: str
    summary: str
    reasons: list[str]
    warnings: list[str]
    operations: list[TripOperation]
    impact: ProposalImpact
    evidence: list[Evidence]
    status: Literal[
        "draft", "pending", "accepted", "rejected", "expired", "conflicted"
    ]
```

允许的 Operation 是显式命令：

- `ReplaceNode`
- `InsertNode`
- `RemoveNode`
- `MoveNode`
- `UpdateNode`
- `ReplaceTransportSegment`
- `UpdateHotelStay`
- `ReorderDay`

禁止模型生成任意数据库更新语句。

### 7.1 审批和冲突处理

`base_version` 必须与当前 Trip 版本一致。如果不一致：

1. 检查 Proposal 目标实体是否已变化。
2. 如果变化无关，则重新校验。
3. 如果目标实体已变化，将 Proposal 标记为 `conflicted`。
4. 使用最新 Snapshot 重新生成建议。

接受的 Operations 必须在一个数据库事务中执行，同时增加 Trip 版本、记录 `DecisionLog`，并保存用于 Undo 的反向操作。

## 8. 领域数据模型

### 8.1 主要实体

```text
User
Trip
TripConstraint
ItineraryDay
TripNode
TransportSegment
PlaceRef
BookingRecord
NodeDiscussion
DiscussionMessage
TripProposal
DecisionLog
AgentRun
AgentEvidence
```

### 8.2 TripNode

`TripNode` 类型包括地点、餐饮、酒店、活动、抵达和离开。节点包含开始/结束时间、时区、排序位置、PlaceRef、BookingRef、选择状态、数据来源和实体版本号。

### 8.3 TransportSegment

`TransportSegment` 显式连接两个节点，包含交通方式、出发/到达时间、时长、距离、路线 Geometry、Provider RouteRef，以及 estimated/selected/booked 状态。

替换节点后，仅使其进入和离开的两个交通段失效并重算；除非 Validator 判断存在更广泛影响。

### 8.4 地点和坐标

一期保存高德 POI ID，以及带时间戳的名称、地址、营业时间快照和 GCJ-02 坐标。PostGIS 用于附近筛选和地理聚类；真实路线耗时和路线 Geometry 仍以高德为准。

## 9. 前端状态和交互

### 9.1 服务端状态

TanStack Query 管理 Trip、Day、Node、Segment、Discussion、Proposal 和 AgentRun。

### 9.2 临时 UI 状态

Zustand 管理当前 Day/Node、抽屉状态、地图视口和拖拽临时状态。不得在 Zustand 中保存第二份完整 Trip。

### 9.3 乐观编辑

手动编辑先立即更新前端时间线，再提交带版本的 Mutation，然后确认或回滚。成功修改节点后，系统发出事件，把相邻路线标记为重新计算，并在后端返回后替换路线 Geometry。

## 10. 技术栈

### 10.1 Web

- Next.js App Router、React、TypeScript
- Tailwind CSS 和 shadcn/ui
- TanStack Query 和受限使用的 Zustand
- dnd-kit
- 高德地图 JavaScript API 2.0
- Zod
- Vitest 和 Playwright

### 10.2 后端

- Python 3.12 或以上
- FastAPI 和 Pydantic v2
- SQLAlchemy 2 async、Alembic、psycopg 3
- PostgreSQL 16 和 PostGIS
- LangGraph 1.x，使用 PostgreSQL Checkpoint
- HTTPX
- pytest 和 Testcontainers

### 10.3 模型和 Provider

- 主模型：阿里云百炼 OpenAI-compatible API 的通义千问
- 备用 Provider：DeepSeek
- 应用自有的 `ModelProvider` 抽象
- 高德 Web Service 提供服务端 POI 和路线数据
- 高德 JavaScript API 负责前端地图渲染
- Provider 结果必须包含来源、获取时间、置信度和缺失字段

一期不同时引入 LangGraph 和 Qwen-Agent 两套重叠的编排 Runtime。

### 10.4 部署

- 容器化 Next.js standalone 进程
- 容器化 FastAPI 进程
- 一期 LangGraph 在 FastAPI 进程内运行，Checkpoint 写入 PostgreSQL
- 阿里云 ECS 或容器服务
- 阿里云 RDS PostgreSQL 和 OSS
- Nginx 或 Caddy 反向代理
- Redis 和持久化 Queue 推迟到需要定时或脱离请求的任务时再引入

一期不包含独立 Python Worker。只有实际测量发现请求耗时或离线任务确实需要时，才引入 Worker 和持久化 Queue；此变化不影响 Agent 或 Proposal 契约。

## 11. API 范围

```text
POST  /v1/conversations
POST  /v1/conversations/{id}/messages

POST  /v1/trips
GET   /v1/trips/{id}
PATCH /v1/trips/{id}
PATCH /v1/trips/{id}/nodes/{node_id}

POST  /v1/trips/{id}/nodes/{node_id}/discussions
POST  /v1/trips/{id}/plan-runs
GET   /v1/runs/{run_id}/events

GET   /v1/proposals/{id}
POST  /v1/proposals/{id}/accept
POST  /v1/proposals/{id}/reject
POST  /v1/decisions/{id}/undo
```

流式通信使用 SSE。Next.js 使用 FastAPI OpenAPI 自动生成的 TypeScript API Client。

## 12. 错误处理

- `ProviderTransientError`：有界指数退避重试
- `ProviderDataMissing`：返回缺失字段，禁止要求模型编造
- `ProposalConflict`：基于最新 Trip 版本重新校验或生成
- `ConstraintViolation`：拒绝执行并返回违反的约束
- `AgentOutputInvalid`：进行一次 Schema 修复，仍失败则安全终止
- `RouteUnavailable`：保留节点，将交通段标记为 unresolved
- `UnauthorizedTripAccess`：在构建 Agent Context 前拒绝请求

所有外部调用必须有 Timeout、Cancellation、Trace ID 和脱敏日志。

## 13. 测试和评测

### 13.1 确定性测试

- 领域规则和 `ProposalExecutor` 单元测试
- Repository、PostGIS 和事务集成测试
- 使用脱敏录制 Fixture 的 Provider Contract Test
- 前端状态和组件测试
- 核心用户路径 Playwright 测试

### 13.2 Agent Evals

初始回归数据集包含 50–100 条案例，覆盖：

- 不完整需求生成恰好三个有效计划
- 替代建议排除已在行程中的地点
- 住宿建议考虑每日路线
- 先选择交通类别，再选择具体班次
- Proposal 只能使用允许的 Operations
- 旧 Trip 版本冲突处理
- Provider 数据缺失时诚实反馈
- 保留硬约束

修改 Prompt、模型或 Tool Description 后必须运行评测套件。

## 14. 两人并行开发策略

团队采用 Contract-first。前端和后端都不等待另一方完成整层实现。

### 14.1 并行开发前的共享契约

前两天共同产出：

- Pydantic 领域 Schema
- OpenAPI Endpoint Contract
- SSE Event Schema
- Proposal Operation Schema
- Trip、候选计划、Discussion 和 Proposal 的代表性 JSON Fixtures
- 状态所有权 ADR

OpenAPI 和 Fixtures 是版本化工程资产。破坏性 Contract 变化必须由两人共同审阅。

### 14.2 开发分线

```text
开发者 A：产品 / Web 线
  - Next.js Shell 和认证 UI
  - Trip Board 时间线
  - 高德地图渲染与交互
  - Discussion Drawer
  - Proposal Diff 和确认 UI
  - Playwright 用户路径

开发者 B：Python / Core 线
  - FastAPI 和认证后端
  - 领域模型和 Migration
  - Trip/Proposal/Discussion Use Cases
  - 高德和模型 Provider Adapters
  - LangGraph 和 Specialist Agents
  - pytest 和 Agent Evals
```

两人都要 Review 对方的边界代码，Ownership 不是排他的。

### 14.3 前端如何独立开发

Web 线依赖：

- 自动生成的 TypeScript API Types
- 基于共享 Fixtures 的 Mock Service Worker Handlers
- 可确定性回放的 Fake SSE Event Source
- 同时具有 Fake 和 AMap 实现的 Map Adapter

真实后端 Endpoint 完成前，前端已经可以实现 Loading、Success、Conflict、Partial Data、Tool Progress 和 Failure 状态。

### 14.4 后端如何独立开发

Python 线依赖：

- API Contract Tests
- Fake Model、AMap、Weather 和 Search Providers
- Golden TripSnapshot 和 TripProposal Fixtures
- Agent Run CLI 或 pytest Harness

Agent 和领域行为无需浏览器即可测试。

### 14.5 纵向集成节奏

每 2–3 天集成一条最薄的真实纵向链路：

1. 用真实 Endpoint 替换一个 Mock。
2. 运行生成 Client 的 Type Check。
3. 运行后端 Contract Tests。
4. 运行对应 Playwright Path。
5. 立即记录 Contract 或行为变化。

不能把集成推迟到每周末。

### 14.6 六周并行计划

#### Week 1：基础设施

共同：Repository、Compose、Contracts、Fixtures、CI、Architecture Tests。

Web：Next.js Shell、Generated Client、MSW、Trip Board Skeleton。

Python：FastAPI、数据库、Migration、认证、Trip CRUD。

集成里程碑：在 Trip Board 中创建并读取真实持久化 Trip。

#### Week 2：结构化行程

Web：时间线编辑、节点 Drawer、乐观 Mutation、Undo UI。

Python：Node/Segment 领域服务、版本管理、DecisionLog、ProposalExecutor。

集成里程碑：手动节点编辑支持冲突检测和 Undo。

#### Week 3：规划对话

Web：Chat Streaming UI、三个计划选择、Agent Progress States。

Python：TravelAdvisor、PlanAgent、SSE、Fake 后切换真实 Model Provider。

集成里程碑：自然语言需求生成三个可选择计划。

#### Week 4：地图和 Discussion

Web：高德 Marker、Polyline、同步选择、路线重算状态。

Python：高德 POI/Route Adapter、NodeDiscussion、Context Builder。

集成里程碑：替换节点后更新相邻交通段和地图 Geometry。

#### Week 5：Specialists 和 Proposals

Web：三个候选 UI、Proposal Diff、Accept/Reject/Conflict Flow。

Python：Stay/Mobility/Experience Agents、LangGraph Manager、Validators。

集成里程碑：节点 Discussion 委派研究并生成可执行 Proposal。

#### Week 6：可靠性和发布

Web：基础响应式兼容、Accessibility、错误恢复打磨。

Python：Eval Dataset、Tracing、Timeout、Retry、部署加固。

共同：Playwright Suite、性能检查、部署、真实用户测试。

集成里程碑：可部署 MVP 和 Release Checklist。

### 14.7 协作规则

- 每日 20 分钟 Contract 和 Blocker Sync
- 一人可修改共享 Schema，但必须两人批准
- CI 检查 API Client Generation 和 Schema Drift
- 未完成的后端 Endpoint 必须有 MSW Fixture
- 每个 Provider 必须有确定性 Fake
- Feature 只有通过一条跨边界 Integration Test 才算完成

## 15. 推荐仓库结构

```text
gogo-agent/
├── apps/
│   ├── web/
│   │   ├── app/
│   │   ├── components/
│   │   │   ├── trip-board/
│   │   │   ├── timeline/
│   │   │   ├── map/
│   │   │   ├── discussion/
│   │   │   └── proposals/
│   │   ├── lib/api-generated/
│   │   └── mocks/
│   └── api/
│       ├── app/
│       │   ├── domain/
│       │   ├── application/
│       │   ├── api/
│       │   ├── agents/
│       │   ├── providers/
│       │   └── infrastructure/
│       ├── migrations/
│       └── tests/
├── contracts/
│   ├── fixtures/
│   └── openapi/
├── evals/
│   ├── datasets/
│   ├── scorers/
│   └── regression/
├── infra/
│   ├── docker/
│   └── compose.yaml
└── docs/
```

## 16. 成功标准

满足以下条件后，MVP 可以邀请真实用户：

- 用户可以从不完整需求创建 Trip，并从三个计划中选择一个。
- Trip Board 每个节点都可编辑并与地图联动。
- 节点 Discussion 能返回三个不重复、有证据的候选项。
- 接受 Proposal 后只修改允许的实体，并且可以撤销。
- 路线变化可见，未解决路线被明确标记。
- 规划和重规划在测试场景中不破坏硬约束。
- 核心 Agent Evals 达到约定阈值且不存在严重回归。
- 部署环境中的核心 Playwright 用户路径通过。

