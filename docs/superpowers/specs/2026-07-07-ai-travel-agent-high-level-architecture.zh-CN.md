# AI 旅行 Agent High-level 系统架构

```mermaid
flowchart TB
    U["用户"]

    subgraph WEB["产品层 · Next.js / React / TypeScript"]
        CHAT["旅行对话"]
        BOARD["Trip Board 时间线"]
        MAP["高德地图可视化"]
        DISCUSS["节点 Discussion"]
        DIFF["Proposal Diff / Confirm / Undo"]
        STATE["TanStack Query + Zustand"]
    end

    subgraph API["业务层 · FastAPI / Pydantic / SQLAlchemy"]
        AUTH["Auth / Session"]
        TRIP["Trip Application Service"]
        DISCUSSION["Discussion Service"]
        PROPOSAL["Proposal Service"]
        EXECUTOR["Proposal Executor"]
        STREAM["SSE Event Stream"]
    end

    subgraph AGENT["智能层 · LangGraph Manager"]
        ADVISOR["Travel Advisor\n唯一用户可见 Agent"]
        PLAN["Plan Agent"]
        STAY["Stay Agent"]
        MOBILITY["Mobility Agent"]
        EXPERIENCE["Experience Agent"]
        VALIDATOR["Budget / Route / Constraint Validators\n确定性 Python 服务"]
    end

    subgraph PROVIDERS["Provider 适配层"]
        MODEL["通义千问 / DeepSeek"]
        AMAP_SERVER["高德 Web Service\nPOI / Route / Geocode"]
        WEATHER["天气服务"]
        SEARCH["联网搜索"]
        DEEPLINK["携程 / 飞猪 / 12306 / 高德深链"]
    end

    subgraph DATA["数据层 · PostgreSQL 16 + PostGIS"]
        TRIP_DB[("正式 Trip State")]
        CHAT_DB[("Discussion / Message")]
        PROPOSAL_DB[("Proposal / DecisionLog")]
        RUN_DB[("AgentRun / LangGraph Checkpoint")]
    end

    U <--> WEB
    CHAT --> ADVISOR
    DISCUSS --> DISCUSSION
    BOARD --> TRIP
    MAP --> AMAP_SERVER
    DIFF --> PROPOSAL

    WEB <-->|"OpenAPI Client + SSE"| API
    STREAM --> STATE

    DISCUSSION --> ADVISOR
    TRIP -->|"只读 TripSnapshot"| ADVISOR
    ADVISOR --> PLAN
    ADVISOR --> STAY
    ADVISOR --> MOBILITY
    ADVISOR --> EXPERIENCE

    PLAN --> MODEL
    STAY --> MODEL
    STAY --> AMAP_SERVER
    MOBILITY --> MODEL
    MOBILITY --> AMAP_SERVER
    EXPERIENCE --> MODEL
    EXPERIENCE --> AMAP_SERVER
    EXPERIENCE --> WEATHER
    EXPERIENCE --> SEARCH

    PLAN --> VALIDATOR
    STAY --> VALIDATOR
    MOBILITY --> VALIDATOR
    EXPERIENCE --> VALIDATOR
    VALIDATOR -->|"TripProposal"| PROPOSAL

    PROPOSAL --> PROPOSAL_DB
    PROPOSAL -->|"等待用户确认"| DIFF
    DIFF -->|"Accept / Reject"| EXECUTOR
    EXECUTOR -->|"唯一 AI 写入通道"| TRIP_DB
    EXECUTOR --> PROPOSAL_DB

    AUTH --> TRIP_DB
    TRIP --> TRIP_DB
    DISCUSSION --> CHAT_DB
    ADVISOR --> RUN_DB
    PLAN --> RUN_DB

    TRIP --> STREAM
    PROPOSAL --> STREAM
    AMAP_SERVER --> STREAM

    BOARD --> DEEPLINK
    MAP --> DEEPLINK

    classDef web fill:#e8f2ec,stroke:#2d6a4f,color:#173d2d;
    classDef api fill:#e8f0f6,stroke:#245a7e,color:#16384e;
    classDef agent fill:#fff1cf,stroke:#9a6300,color:#5d3c00;
    classDef provider fill:#f5e9e6,stroke:#9f433b,color:#572520;
    classDef data fill:#eee9f5,stroke:#665083,color:#382c49;

    class CHAT,BOARD,MAP,DISCUSS,DIFF,STATE web;
    class AUTH,TRIP,DISCUSSION,PROPOSAL,EXECUTOR,STREAM api;
    class ADVISOR,PLAN,STAY,MOBILITY,EXPERIENCE,VALIDATOR agent;
    class MODEL,AMAP_SERVER,WEATHER,SEARCH,DEEPLINK provider;
    class TRIP_DB,CHAT_DB,PROPOSAL_DB,RUN_DB data;
```

## 如何理解这张图

### 1. Next.js 是产品界面，不承担核心 Agent 逻辑

Next.js 负责对话、时间线、地图、节点讨论和 Proposal 确认。它通过 FastAPI OpenAPI 自动生成的 TypeScript Client 调用后端，通过 SSE 接收流式 Token、工具进度、路线更新和 Proposal 状态。

### 2. FastAPI 是业务边界

FastAPI 管理认证、Trip CRUD、Discussion、Proposal 和正式状态写入。任何前端或 Agent 都不能绕过这一层直接修改数据库。

### 3. LangGraph 管理复杂智能流程

用户只看到一个 `TravelAdvisor`。它根据任务按需调用 Plan、Stay、Mobility 和 Experience Agents。预算、路线和约束校验仍由确定性 Python 服务完成。

### 4. Agent 只输出建议

Specialist Agent 的结果经过 Validator 后形成 `TripProposal`。Proposal 先展示给用户；只有用户确认后，`ProposalExecutor` 才在一个事务中修改正式 Trip State，并记录 DecisionLog 和 Undo 信息。

### 5. PostgreSQL 中存在两类状态

- `Trip State` 是产品唯一正式状态。
- `LangGraph Checkpoint` 只是某次 Agent Run 的临时过程状态。

二者不能互相替代，避免 Agent 运行状态与用户实际行程产生冲突。

## 典型请求路径

### 创建旅行计划

```text
用户输入模糊需求
→ TravelAdvisor
→ LangGraph 并行调用 Plan / Stay / Mobility / Experience
→ Validators
→ 返回三个计划方向
→ 用户选择
→ FastAPI 创建正式 Trip
```

### 编辑一个地点

```text
用户点击 TripNode 并持续提问
→ NodeDiscussion
→ TravelAdvisor 调用 ExperienceAgent
→ 查询高德 / 天气 / 搜索
→ 返回三个替代项
→ 用户选择一个
→ 生成 TripProposal
→ 用户确认
→ ProposalExecutor 替换节点
→ 重算相邻 TransportSegments
→ SSE 更新 Trip Board 和地图
```

### 比较交通

```text
用户讨论某个 TransportSegment
→ MobilityAgent 先比较交通类别
→ 用户确定类别
→ 查询更具体的路线与参考班次
→ Proposal 修改 TransportSegment
→ 用户确认后执行
```

