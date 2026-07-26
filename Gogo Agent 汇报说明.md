# Gogo Agent 代码文件夹说明

这份文档说明当前工作区里的代码包含什么、每个文件负责什么、代码运行时的整体逻辑是什么。它不是聊天记录，而是给汇报和交接用的代码导览。

## 1. 工作区整体结构

```text
gogo-agent/
  README.md
  requirements.txt
  index.html
  app.js
  agent-runtime.js
  styles.css
  manual_agent_playground.py
  Gogo Agent Architecture and Graph Spec.html
  Gogo Agent 汇报说明.md
  archive/
    js-agent-implementation.zip
  backend/
    application/
    agent/
  tests_py/
    test_python_agent.py
```

整体分成四块：

- 前端 demo：`index.html`、`app.js`、`agent-runtime.js`、`styles.css`。
- Python agent 后端：`backend/`。
- 人工测试入口：`manual_agent_playground.py`。
- 架构和说明文档：`Gogo Agent Architecture and Graph Spec.html`、本文件。

## 2. 根目录文件

`README.md` 是项目简短说明，目前仍偏原型阶段，主要写了打开 `index.html` 查看 prototype，还没有完整写 Python agent 的运行命令。

`requirements.txt` 是 Python 依赖文件，目前包含 `pydantic` 和 `langgraph`。`pydantic` 用来定义 schema/contracts 并做字段校验，`langgraph` 用来实现复杂规划 graph。

`index.html` 是前端 demo 入口页面，负责加载 `agent-runtime.js` 和 `app.js`。

`styles.css` 是前端 demo 样式文件，负责页面布局、卡片、地图、drawer、按钮等视觉样式。

`app.js` is the frontend Trip Board demo logic. It shows the Trip Board, day nodes, map points, drawer, and prototype graph replan/proposal-first interactions. The frontend demo is still not the formal Python backend integration.

`agent-runtime.js` 是前端 demo 保留的一套轻量 JS runtime，主要用于浏览器原型模拟。它包含 `EscalationDecision`、`decideEscalation`、`createTripProposal`、`createProposalService`、`executeAcceptedProposal`。它不是当前 Python 后端主实现，而是前端 demo 用来模拟 proposal-first 行为的 JS 版本。

`manual_agent_playground.py` 是新的五轮人工端到端测试入口。运行 `python manual_agent_playground.py` 后，它会读取 `.env` 里的真模型配置，按顺序引导测试：初始规划、上下文追问、选择推荐方案、生成 proposal、接受并执行 proposal。不调用模型的启动检查命令是 `python manual_agent_playground.py --self-check`。

`Gogo Agent Architecture and Graph Spec.html` 是当前最完整的架构文档，包含总体目标、调用链、graph 结构、node 职责、时序图、所有 contracts/schema、proposal 边界、provider 错误处理和测试覆盖。

`archive/js-agent-implementation.zip` 是之前 JS agent 实现的打包归档。当前 Python 后端已经迁移出来，这个 zip 主要用于保留历史版本。

## 3. Python 后端总览

Python 后端集中在：

```text
backend/
  application/
  agent/
```

整体运行关系是：

```text
manual_agent_playground.py / frontend / application service
        ->
TravelAdvisor
        ->
ClarificationPolicy
        ->
ReplanIntentRouter + SpecialistSelector
        ->
TripPlanningGraph or LightweightFlows
        ->
TripBoardResponse / AnswerResponse / ProposalResponse
```

Chat import now returns one TripBoardResponse. TripPlanningGraph can still keep RecommendationSet candidates internally for comparison, but users no longer manually choose from three options.

This means the first user-facing result is already an editable Trip Board. The internal RecommendationSet is kept as graph/planner evidence and debug context, not as a screen where users must choose among three plans.

CurrentTrip Board is the source of truth. Agent 不保存“自己以为的行程状态”，也不依赖上一轮聊天里未写入 Board 的内容。每次请求都读取当前 Board 的 `trip.version`、`days`、`nodes`、当前选中的 day/node 和用户这次输入。用户手动保存、点击应用到节点、或接受 graph proposal 后，Board 内容才变化，`trip.version` 才递增。

## 3.1 LLM / Rules / Fallback Matrix

This table explains which modules call the model, which modules are deterministic, and what happens when they fail.

| Module | Main mechanism | Fallback behavior | Output |
| --- | --- | --- | --- |
| `TravelAdvisor` | Main agent and orchestration layer | Converts graph/lightweight failures into `AdvisorFallbackDecision`; enforces that free-text consultation cannot mutate trip | `TripBoardResponse`, `AnswerResponse`, `ProposalResponse`, or `ClarificationQuestionResponse` |
| `ClarificationPolicy` | LLM-first: `generate_clarification_decision` | For initial chat import, asks destination/duration when the request is too vague; provider/schema failure uses safe required questions | `ClarificationQuestionResponse` or continue |
| `ReplanIntentRouter` | LLM-first: `generate_replan_routing_decision` | Rule fallback maps initial plan/regenerate/replace/research/replan into stable routing decisions | `ReplanRoutingDecision` |
| `SpecialistSelector` | LLM-first: `generate_specialist_selection` | Keyword fallback detects optional weather, ticket, price, stay, mobility, experience, flight, and rail needs; node type/tag adds required minimum capabilities | `CapabilityPlan` / `SpecialistSelection` |
| `PlanningBriefBuilder` | LLM-first: `generate_planning_brief` | Safe fallback keeps the original user message without guessing destination/days/interests | `PlanningBrief` |
| `TripPlanningGraph` | LangGraph workflow with stay/mobility/experience research | Graph errors are surfaced as `GraphErrorEnvelope` and then advisor fallback | internal `RecommendationSet` or `TripProposal` |
| `TripBoardBuilder` | Deterministic adapter | Uses the best internal recommendation candidate; creates a minimal fallback board only when no candidate exists | `TripBoardResponse(kind="trip_board")` |
| `LightweightFlows` | LLM-backed consultation layer: direct answer + contextual research | Provider failures become safe advisor fallback answers; it never creates TripProposal | `AnswerResponse` only |
| `ProposalService / ProposalExecutor` | Deterministic state machine and executor | Rejects empty operations, missing target nodes, invalid status transitions, and unsafe patches | Updated trip or structured failure |

## 4. backend/application/agent_application_services.py

This is the application-service entry layer. It creates agent runs, calls `TravelAdvisor`, executes proposals, and updates proposal status. If this project later gets an HTTP API, this layer can sit between controllers and the agent.

Key methods:

```text
start_initial_plan_run(command)
handle_discussion_turn(command)
execute_proposal(command)
set_proposal_status(proposal_id, status)
```

## 5. backend/agent/travel_advisor.py

`TravelAdvisor` is the main user-facing agent entry. It receives user message, current trip, and optional intent; then it coordinates clarification, routing, specialist selection, lightweight flows, graph runs, proposal persistence, and fallback.

Current initial planning behavior:

```text
Initial chat message
  -> ClarificationPolicy
  -> PlanningBriefBuilder
  -> TripPlanningGraph initial plan
  -> internal RecommendationSet candidates
  -> TripBoardBuilder
  -> TripBoardResponse
```

Trip Board behavior:

```text
Existing current_trip + intent
  -> ReplanIntentRouter + SpecialistSelector
  -> If consultative: LightweightFlows.answer/contextual_research
  -> If explicit day/cross-day/full replan: TripPlanningGraph.replan
  -> ProposalService pending proposal only for graph replan
  -> ProposalExecutor only after user acceptance
```

Return kinds are now mainly: `trip_board`, `answer`, `proposal`, and `clarification_question`. `recommendation_set` remains an internal graph candidate structure, not the primary initial-planning user output.

## 6. backend/agent/clarification_policy.py

这是 graph 外的追问判断模块。它发生在 `PlanningBriefBuilder` 和 `TripPlanningGraph` 之前。

当前逻辑是：如果用户要做 `initial_plan`，Advisor 会优先调用真模型 `generate_clarification_decision(...)`，让模型判断信息是否足够开始规划。如果模型判断还缺关键信息，Advisor 不会直接进入 graph，而是返回：

```text
kind = clarification_question
```

例如用户只说 “Plan a trip for me”，系统会追问目的地和天数。这样可以避免模型在信息不足时硬编方案。

如果 clarification 模型调用失败或返回 JSON 不合法，系统会 fallback 到最小安全追问：目的地和天数。也就是说，判断优先交给 LLM，但返回结构仍然受 schema 约束。

注意：`regenerate_recommendations` 不会被这个 policy 拦截，因为它通常依赖上一轮推荐上下文；已有 `trip` 的修改也不会被初始规划追问拦截。

这里要客观看：当前 `ClarificationPolicy` 不是“覆盖所有 demo 入口的完整追问系统”，它现在只覆盖“从零开始规划新旅程”这个入口。它能避免普通咨询被迫补目的地/天数，但如果 demo 里有更多入口，后续最好升级成 profile-aware policy：

| 入口/场景 | 当前行为 | 建议升级 |
| --- | --- | --- |
| 初始界面规划新旅程 | LLM 判断是否足够开始规划；fallback 追问目的地和天数 | 增加 `initial_trip_planning` profile：目的地、日期/天数必填；预算、人数、节奏、兴趣作为高价值可选信息 |
| 普通咨询 | 不走初始规划追问，直接进入 lightweight answer | 增加 `quick_consultation` profile：默认不要求旅行完整信息，只在问题缺对象时追问 |
| 单点咨询/一键填入 | 不走初始规划追问；进入 lightweight research，结合当前 node 和 specialistSelection 生成可参考内容 | 增加 `node_consultation` profile：缺目标节点时追问“你想咨询或填入哪一个酒店/景点/餐厅/交通块” |
| 单日/跨天重排 | 不走初始规划追问；graph replan 要求明确 affected nodes | 增加 `day_or_cross_day_replan` profile：缺天数、节点或修改目标时追问 |
| 换一组推荐 | 由 router 识别为 `regenerate_recommendations` | 如果缺上一轮 brief 或用户没说不满意点，可追问“想换风格、预算、节奏还是目的地” |

## 7. backend/agent/replan_intent_router.py 和 specialist_selector.py

`replan_intent_router.py` 是修改范围判断器。它把用户这句话归类为：

```text
initial_plan
discussion_turn
day_replan
cross_day_replan
regenerate_recommendations
lightweight_research
```

它解决的是“这次应该输出什么”：从零规划会先经过 graph 内部候选，再由 `TripBoardBuilder` 输出一个 `TripBoardResponse`；已有行程上的普通追问、单点咨询、换酒店/换餐厅自由文本都输出 `answer`；只有单日、跨天、全局重排这类明确结构调整才输出 `TripProposal`。`recommendation_set` 现在主要是内部候选结构，不是初始规划给用户看的主输出。

`specialist_selector.py` 是专业能力选择器。它现在输出的是一个 capability plan，而不是简单的 needs list。

这个 plan 分三层：

```text
required = node type / tag 强制要求的最低能力
optional = LLM 或 fallback 根据用户输入额外选择的能力
needs = required + optional 的去重合集，兼容旧前端/旧测试
```

例如用户在交通节点问酒店，交通节点会强制带 `mobility`，用户问题会额外加入 `stay`。用户在酒店节点问下雨和打车，酒店节点强制带 `stay`，用户问题额外加入 `weather` 和 `mobility`。

当前可选能力包括：

```text
stay
mobility
experience
weather
ticket
flight
rail
price
```

注意：这些 specialist needs 不是单独 graph node。API 仍然作为住宿、交通、体验等 specialist 内部可调用的工具，等真实 API key 到位后再接。后续增加更多子 agent 或 skill 时，优先加入 capability plan，而不是把判断写死在 LightweightFlow 或 Graph 里。

`replan_escalation_policy.py` 是之前的升级规则文件，目前保留兼容，但新的主入口已经改为由 `TravelAdvisor` 消费 `ReplanIntentRouter` 和 `SpecialistSelector` 的结构化结果。

## 8. backend/agent/planning_brief_builder.py 和 intent_extraction.py

`planning_brief_builder.py` 是正式的 PlanningBriefBuilder。它优先调用真模型，把用户自然语言提取成 `PlanningBrief`。

`intent_extraction.py` 现在只做最小安全 fallback：当模型不可用或返回无效 JSON 时，它只保留原始用户消息，不再用规则从用户文本里猜目的地、天数、兴趣或偏好。人工测试里的“三日游”只是测试输入，不是 agent fallback contract。

`PlanningBrief` 里有两个观测字段：`builder_source` 表示 brief 来自 `llm` 还是 `fallback`，`builder_fallback_reason` 表示 fallback 的原因，例如 `timeout_error`、`ValidationError` 或 `provider_unavailable`。

## 9. backend/agent/lightweight_flows.py

This is the graph-external Trip Board consultation layer. Users still feel they have one LLM input window, but TravelAdvisor decides whether the turn is direct answer, contextual research, or explicit graph replan.

LightweightFlows now has two user-facing consultation modes:

- `direct_answer`: ordinary questions that can be answered without specialist context. It calls provider `generate_answer` and never changes the trip.
- `contextual_research`: questions that need current trip, target node, routing, or specialist context. It also calls provider `generate_answer`, but the prompt includes `current_node`, `trip_summary`, and `routing.specialistSelection`.

Important rule:

```text
Free-text replace/check/compare in Trip Board = consultation by default.
It returns AnswerResponse only.
It does not create TripProposal.
It does not mutate trip.
```

Default specialist selection by node type:

```text
hotel / stay / lodging -> stay specialist
transport / mobility / route -> mobility specialist
food / meal / restaurant / activity / attraction / experience -> experience specialist
```

Only explicit day / cross-day / full-trip replan intent enters `TripPlanningGraph.replan` and can produce a pending `TripProposal`.

## 10. backend/agent/graph/trip_planning_graph.py

这是复杂规划 graph 的核心。

Python 类名是 `TripPlanningGraph`。架构文档里把它称为 `TripPlanningGraphV2`，二者指的是同一个当前版本 graph。

Graph 支持两种模式：

```text
initial_plan
cross_day_replan
```

`initial_plan` 生成内部推荐候选，随后由 `TripBoardBuilder` 转成一个 `TripBoardResponse`。

`cross_day_replan` 基于已有 trip 和 intent，生成 `TripProposal`。

当前 graph 是：

```text
START
  ↓
skeleton_planning_node
  ↓
并行：stay_research_node / mobility_research_node / experience_research_node
  ↓
research_barrier_node
  ↓
candidate_merge_node
  ↓
recommendation_planner_node
  ↓
validate_candidates_node
  ↓
finalize_output_node
  ↓
END
```

`research_barrier_node` 用来等待三个并行分支都完成，并检查是否出现 `graph_error`。如果任一分支失败，就中断到 fallback；如果全部成功，就进入 candidate merge。

## 11. backend/agent/nodes/

这里放 LangGraph 里的 node 实现。

`skeleton_planning_node.py` 生成基础行程骨架。它不会调用模型，而是根据 `PlanningBrief` 生成 trip shape、stay strategy、mobility strategy、experience strategy、day frames。

`stay_research_node.py` 是住宿 specialist。长期职责是接酒店/民宿 API，规划具体可住候选。当前 `.env` 里还没有酒店 API key，所以先调用 provider 的 `generate_research(domain="stay")`，要求模型返回 JSON，包括 summary、options、warnings、missingInfo、evidence、assumptions、confidence。

`mobility_research_node.py` 是交通 specialist。长期职责是接地图/高德/高铁/飞机等 API，规划真实路线、耗时、换乘和成本。当前 `.env` 里还没有相关 API key，所以先调用 provider 的 `generate_research(domain="mobility")`。

`experience_research_node.py` 是体验/美食 specialist。长期职责是接 POI/餐厅/活动 API；当前已经先接入 Open-Meteo 天气 API context，并把天气结果放进 experience research prompt 和 `raw.api_context.weather`。它特别要求 `foodHighlights` 必须是真正的食物、餐厅、食物区域或小吃，不能是一日游标题。

`run_research_step.py` 是 research 节点共用的错误处理包装器。它会调用实际 research；如果 evidence 缺失或 confidence 太低，标记为 degraded；如果 provider 抛错，转成 `GraphErrorEnvelope`；输出 `ResearchOutcome`。

`candidate_merge_node.py` 把三个 specialist 的输出归一化成 planner 可读的 `candidate_context`。它不生成完整行程，只整理 `stay_candidates`、`mobility_candidates`、`experience_candidates`、constraints 和 preferences。

`recommendation_planner_node.py` 是主规划节点。它调用 provider 的 `generate_recommendations(...)`，基于 `PlanningBrief`、skeleton plan 和 `candidate_context`，直接生成完整 3 个 `TravelPlanRecommendation`。每个 recommendation 包含 title、theme、summary、best_for、tradeoffs、stay_plan、mobility_plan、food_plan、day_plans、evidence、missing_info、warnings、score。

`recommendation_planner_node.py` 是 graph 内部 recommendation 候选生成节点。它调用 LLM 基于 stay/mobility/experience 的候选上下文生成可比较的候选方案；如果模型失败或返回无效 JSON，graph 会返回 `graph_error`，不会再用占位 composer 伪造正式推荐。用户侧不会再看到三套候选，而是看到 `TripBoardBuilder` 转换出来的一个 Trip Board。

`validate_candidates_node.py` 是质量校验节点，不是子 agent。它检查候选方案是否有明显问题：没有 day plans、没有 food plan、没有 day trip destination、没有 evidence、score 太低、meal block 看起来像错误塞入了一日游标题。通过的 candidate 会保留；如果全部失败，会写入 `candidate_validation_failed` graph error 并中断，不返回 Trip Board。

`finalize_output_node.py` 是 graph 最终输出节点。如果 mode 是 `initial_plan`，它先输出内部 `RecommendationSet`，再由 `TravelAdvisor` 调用 `TripBoardBuilder` 转成 `TripBoardResponse`；如果 mode 是 `cross_day_replan`，会先根据 affected days/nodes 找到目标节点，再调用 provider 的 `generate_replan_proposal(...)` 生成真实 `UpdateNode` 或 `ReplaceNode` operations，最后输出 `TripProposal`。如果缺少明确 affected_node_ids、找不到匹配节点、模型返回缺 title/summary 或模型失败，会返回 graph fallback，不会写入模板 patch。

## 12. backend/agent/contracts/

这里是所有 schema/contracts 的集中目录。当前所有 Pydantic/Enum schema 都在这里，没有散落到其它 backend 文件。

- `advisor_io.py`：TravelAdvisor 的输入输出 contract，包括 `TravelAdvisorRequest`、`AnswerResponse`、`ClarificationQuestionResponse`、`ProposalResponse`、`RecommendationSetResponse`；其中 `RecommendationSetResponse` 主要保留为内部/兼容结构，初始规划用户侧主输出是 `TripBoardResponse`。
- `trip_board.py`：初始规划用户侧输出 contract，包括 `TripBoardResponse`。它包含 `kind`、`routing`、`planningBrief`、`trip`、`sourceRecommendation`、`sourceRecommendationSet`、`evidence`、`warnings`、`trace`。
- `clarification.py`：追问 contract，包括 `ClarificationQuestion`、`ClarificationDecision`。
- `planning.py`：规划任务 contract，包括 `PlanningBrief`、`TripPlanningGraphRequest`。
- `graph_state.py`：LangGraph 状态 contract，包括 `TripPlanningGraphState`。
- `research.py`：research 输入/输出 contract，包括 `ResearchBrief`、`ResearchOption`、`ResearchResult`。
- `research_outcome.py`：research 步骤结果包装，包括 `ResearchOutcome`。
- `recommendation_output.py`：最终推荐方案 contract，包括 `TripIntent`、`StayPlan`、`DayTripPlan`、`MobilityPlan`、`FoodPlan`、`DayBlock`、`DayPlan`、`TravelPlanRecommendation`、`RecommendationSet`。
- `replan_routing.py`：replan 路由和能力选择 contract，包括 `ReplanScope`、`ReplanNeed`、`ReplanRoutingDecision`、`SpecialistSelection`。`SpecialistSelection` 同时承担 `CapabilityPlan` 的作用，字段包括 `required`、`optional`、`needs`、`reasons`、`execution_mode`。
- `routing_and_proposal.py`：路由和 proposal contract，包括 `EscalationDecision`、`ProposalOperation`、`ProposalImpact`、`ProposalEvidence`、`TripProposal`。
- `errors.py`：错误和 fallback contract，包括 `GraphErrorEnvelope`、`AdvisorFallbackDecision`。
- `run_events.py`：运行事件 contract，包括 `RunMetadata`、`AgentRunAccepted`、`RunEvent`。
- `validation.py`：校验结果 contract，包括 `CandidateValidationResult`、`ValidationResult`。

重点规则：`TripProposal.operations` 必填且不能为空；`ReplaceNode` 必须有 day_id、node_id、replacement；`UpdateNode` 必须有 day_id、node_id、patch；未知 operation type 会被拒绝。

## 13. backend/agent/providers/

这里是模型 provider 和错误处理。

`qwen_provider.py` 是真实模型调用实现。它使用 DashScope 的 OpenAI-compatible `/chat/completions` 格式。

读取环境变量：

```text
LLM_API_KEY
LLM_API_BASE
LLM_MODEL_NAME
LLM_TIMEOUT_MS
```

它提供这些主要方法：`generate_clarification_decision(...)`、`generate_replan_routing_decision(...)`、`generate_specialist_selection(...)`、`generate_planning_brief(...)`、`generate_research(...)`、`generate_recommendations(...)`、`generate_replan_proposal(...)` 和 `generate_answer(...)`。除 `generate_answer` 返回普通文本外，其它模型方法都要求返回 JSON，并经过 schema 校验。它还提供 `get_weather_context(...)`，通过 Open-Meteo 获取天气上下文，先给 experience 子系统使用。

`errors.py` 定义 `LlmProviderError`，用于包装配置错误、HTTP 错误、网络错误、超时、响应解析错误。

`failure_policy.py` 把 provider 错误分类成系统能处理的 failure policy，比如 config_error → fail_fast，timeout_error/network_error → retry，5xx/429 → retry，其它硬错误 → fail。

## 14. Proposal 整体逻辑

Proposal 是安全修改行程的核心机制。

完整流程：

```text
用户提出修改
  ↓
TravelAdvisor 判断路由
  ↓
explicit graph_replan generates TripProposal
  ↓
ProposalService.persist_proposal
  ↓
状态变成 pending 或 conflicted
  ↓
用户 accepted
  ↓
ProposalExecutor.execute
  ↓
生成新 trip version
```

`ProposalService` 负责保存和管理 proposal 状态。状态规则是：pending 可以变成 accepted/rejected/expired/conflicted，其它状态基本是终态。

`ProposalExecutor` 负责真正修改 trip。执行前检查 proposal 必须 accepted、operations 必须存在、trip.version 必须等于 proposal.base_version、operation 必须合法、day/node 必须存在。执行成功后才会升级 trip version。

## 15. Fallback 整体逻辑

Fallback 是 agent 失败时的安全出口。

常见路径：

```text
Provider error
  ↓
LlmProviderError
  ↓
failure_policy
  ↓
ResearchOutcome + GraphErrorEnvelope
  ↓
TravelAdvisor
  ↓
AdvisorFallbackDecision
  ↓
AnswerResponse.fallback
```

If lightweight answer/contextual research fails, TravelAdvisor returns `AdvisorFallbackDecision`. Free-text replace/check/compare is consultative by default.

## 16. tests_py/test_python_agent.py

这是当前 Python 后端的测试文件。

Coverage includes schema compatibility, initial TripBoardResponse output, parallel research barrier, candidate merge, recommendation planner, TripBoardBuilder conversion, graph fallback, TravelAdvisor routing, ReplanIntentRouter, SpecialistSelector, free-text replace consultation guard, node-type default specialist selection, lightweight answer/contextual research, explicit graph replan proposal, proposal status state machine, ReplaceNode merge semantics, unsafe proposal protection, frontend camelCase adapter, ApplicationServices provider injection, and Qwen provider config guards.

当前测试命令：

```bash
python -m unittest tests_py.test_python_agent
```

当前结果：

```text
84 tests OK
```

## 17. 当前主要运行入口

人工菜单测试：

```bash
python manual_agent_playground.py
```

自动测试：

```bash
python -m unittest tests_py.test_python_agent
```

前端 demo：直接打开 `index.html`。注意：前端 demo 当前主要是原型，不是正式接 Python 后端的版本。

## 18. 当前代码已经实现了什么

已经实现 Python 后端主链路、TravelAdvisor 用户入口、ClarificationPolicy LLM 结构化初始规划追问、ReplanIntentRouter LLM 结构化修改范围判断、SpecialistSelector LLM 结构化专业能力判断、LLM PlanningBriefBuilder、LangGraph 复杂规划 graph、3 个并行 specialist research 节点、research barrier 汇合节点、candidate merge 节点、recommendation planner 节点、TripBoardBuilder、experience 天气 API context、stay/mobility API 异常隔离、初始聊天导入直接输出一个 TripBoardResponse、regenerate_recommendations 重新生成新的 Trip Board、free-text consultation does not mutate trip、LLM cross_day_replan TripProposal 输出、replan target node 硬校验、proposal executor 字段白名单、proposal-first 状态机、proposal 强校验、ReplaceNode/UpdateNode 执行、provider error 包装、fallback contract、前端 camelCase 兼容、人工测试脚本、84 个自动测试、HTML 架构文档同步。

## 19. 当前还没有完全实现什么

还没有完全产品化的部分包括：正式 HTTP API、SSE/流式输出、数据库持久化、真实 selective specialist graph、真实复杂跨天优化算法、完整路线合理性评分、前端 demo 真正接 Python 后端、前端中文编码清理。

## 20. 最简汇报总结




