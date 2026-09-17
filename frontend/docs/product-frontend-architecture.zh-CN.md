# 正式前端架构

正式 `frontend` 不是 `demo/` 的静态复制，也不应该把 mock 行程数据硬写在页面组件里。`demo/` 保持为交互参考，`frontend/` 才是产品实现。

## 产品方向

Gogo Agent 有两个主要产品界面：

- Project Inbox：轻量规划工作区，支持多个旅行项目、进行中的 intake 对话，以及已创建 Trip Board 的入口。
- Trip Board：路线优先的规划工作区，参考 demo 的体验，包括 route canvas、day timeline、node inspector 和 assistant panel。

Demo 里的 Trip Board 交互是更强的参考；demo 的入口页在正式 frontend 中应该重新设计。

## 核心原则

- 组件消费 typed data，不在组件里硬写 trip fixture。
- Mock 数据放在 `mock.ts`，通过 service adapter 访问。
- 同一套 UI 今天可以接 mock service，之后可以切到 backend API service。
- Chat 是上下文助手，不是主应用本身。
- Trip Board 状态由 application service 修改，assistant UI 不直接修改状态。

## 建议目录结构

```text
frontend/src/
  app/
    App.tsx
    routes.tsx
  features/
    projects/
      model.ts
      mock.ts
      service.ts
      ProjectInboxPage.tsx
      components/
        ProjectList.tsx
        ProjectHome.tsx
    intake/
      model.ts
      mock.ts
      service.ts
      IntakePage.tsx
      components/
    trip-board/
      model.ts
      mock.ts
      service.ts
      TripBoardPage.tsx
      components/
        BoardHeader.tsx
        RouteCanvas.tsx
        DayTimeline.tsx
        NodeInspector.tsx
    assistant/
      model.ts
      mock.ts
      service.ts
      AssistantPanel.tsx
      chatkitAdapter.ts
  shared/
    api/
    ui/
```

这样能让领域数据、service 边界和 UI 组件都靠近各自 feature。

## Project Inbox 和 Intake

入口界面应该更接近 Codex 的项目/线程列表，而不是一次性的 prompt box。用户可能有多个旅行项目，每个项目也可能处在不同规划状态。

推荐布局：

```text
左侧：project list
右侧：selected project home
```

项目模型：

```ts
type PlanningProject = {
  id: string
  title: string
  status: 'collecting' | 'ready_to_start' | 'board_created'
  intake: IntakeFields
  chatSessionId: string
  tripBoardId?: string
  updatedAt: string
}
```

当项目还在收集信息时，右侧 project home 保留对话：

预期流程：

```text
用户输入
  -> intake service 抽取或更新字段
  -> 用 compact chips 展示已收集和缺失字段
  -> assistant 只追问缺失内容
  -> 信息足够后 Start Plan 可用
  -> 用户进入 Trip Board
```

Collecting 状态的 project home 应该包含：

- 自然语言输入
- 聊天记录
- 已收集字段摘要
- 缺失字段状态
- `Start Plan` 操作

当 Trip Board 已经创建后，project home 不再展示大的对话输入框，而是展示轻量项目摘要：

- 目的地、时间、人数、预算和偏好
- Trip Board 状态
- 主要操作 `Enter Trip Board`
- 可选的历史记录或继续补充入口

这样已完成项目保持轻，未完成项目还能从上次中断处继续。

入口界面不应该包含：

- 三个生成方案卡片
- 强制模板选择
- 全屏聊天式布局

## Trip Board 页面

Trip Board 页面应该继承 demo 的 route-board 感觉，同时优化布局质感和信息密度。

推荐 desktop 布局：

```text
顶部：board header、day selector、关键操作
中左：带连接节点的 route canvas
底部或左侧：day timeline
右侧：可折叠 assistant panel
```

推荐 mobile 布局：

```text
顶部：board header 和 day selector
主体：route canvas
下方：day timeline 和 node inspector
底部 sheet：assistant panel
```

Route canvas 应该保留 demo 的视觉语言：空间化节点、连接线、day context、直接选中节点。它要避免大面积空地图，也避免在 canvas 下堆冗余总结块。

## 节点交互

节点应该可以直接点击。选中节点后打开 node inspector，不需要再点单独的“查看”按钮。

Node inspector 负责：

- 展示时间、标题、地点、时长和备注
- 展示预订或确认状态
- 展示相关 proposal 操作
- 提供上下文 assistant 入口

## Assistant 和 ChatKit

ChatKit 属于 `features/assistant/AssistantPanel`。

Assistant 负责：

- intake 追问
- day 或 node 级问题
- proposal 确认
- apply 后总结

Assistant 不负责：

- 渲染 Trip Board
- 负责地图布局
- 直接修改 itinerary 状态
- 决定模型路由

当前实现可以先渲染内部 mock assistant panel。之后 `chatkitAdapter.ts` 可以把 panel body 换成 ChatKit，同时保持同样的 feature 边界。

ChatKit 会出现在两个地方：

- Project Inbox 中 `collecting` 或 `ready_to_start` 状态的项目。
- Trip Board 的 assistant panel，用于 day 或 node 上下文。

对于 inbox 里的 `board_created` 项目，默认界面应该是摘要和 `Enter Trip Board`，而不是大的聊天输入框。

## 数据流

初期开发使用 mock services：

```text
mock.ts -> service.ts -> page state -> components
```

接后端时保持同样的 page/component 边界：

```text
backend API -> service.ts -> page state -> components
```

这样可以先把真实前端体验做出来，同时避免把数据硬写进 React 组件。

## 第一阶段实现切片

第一阶段应该实现：

- feature 目录结构
- typed project model
- typed intake 和 Trip Board models
- mock-backed services
- 重新设计的 Project Inbox，包括 project list 和按状态变化的 project home
- 参考 demo 的 Trip Board 页面
- 带 mock proposal confirmation 的 assistant panel 壳

这一阶段先不安装 ChatKit。等后端 custom server 和 session endpoint 到位后，再接 ChatKit。
