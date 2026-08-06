# 专家 Agent 设计

Gogo Agent 对用户应该只呈现一个安静、统一的助手。专家 Agent 是内部能力，当 Trip
Board 需要更深入判断时，由主 TravelAdvisor 作为工具调用。

## 用户体验原则

普通规划过程中，用户不应该看到 Agent handoff。用户应该感觉 Gogo Agent 同时理解路线节奏、预算、住宿和餐食，而不是被几个 Agent 轮流接管。

专家只返回简洁的结构化建议。主 TravelAdvisor 负责把这些建议整理成 proposal、追问，或 Trip Board 变更。

## 什么时候使用专家

当任务需要基于结构化 itinerary 做判断，而且无法用简单确定性函数表达时，使用专家 Agent。

如果任务属于下面这些情况，用普通 function tool 更合适：

- 检查必填字段
- 解析或验证结构化输入
- 调用一个外部 API
- 计算确定性数值

## 专家候选

### Route Sense

目的：评估路线形状和每天的节奏。

输入：

- 旅行目的地和日期
- 每天的 itinerary nodes
- 大致位置
- 已知交通段
- 用户节奏偏好

输出：

- 节奏评分
- 路线问题
- 建议移动或删除的节点
- 简洁理由

### Budget Sense

目的：估算当前计划是否符合用户预算。

输入：

- 预算范围
- 出行人数
- 目的地
- 住宿假设
- itinerary nodes 和交通段

输出：

- 预算可信度
- 可能昂贵的部分
- 取舍建议
- 需要确认的假设

### Stay Sense

目的：比较住宿区域的取舍。

输入：

- 候选住宿区域
- itinerary anchors
- 机场或车站约束
- 用户偏好的旅行方式

输出：

- 推荐 base area
- 各区域取舍
- 通勤问题
- 预订前需要确认的问题

### Food Sense

目的：建议餐食锚点，但不过度塞满行程。

输入：

- 目的地
- itinerary 时间安排
- 餐食偏好
- 预约接受度
- 街区上下文

输出：

- 餐食锚点建议
- 预约提醒
- 灵活备选
- 餐食安排让当天过紧时的提醒

## 接入形态

等 Trip Board schema 稳定后，再把专家加成 agents-as-tools。主 TravelAdvisor 负责用户可见表达，只在专家输出能改善 proposal 时调用专家。

目标流程：

```text
TravelAdvisor
  -> function tools 做确定性检查
  -> specialist agents as tools 做路线、预算、住宿、餐食判断
  -> proposal 返回 application service
  -> 用户确认后再修改 Trip Board
```

## 非目标

- 不在 UI 中创建可见专家人格。
- 不把普通规划对话 handoff 给专家。
- 不在真实输入 schema 稳定前添加专家 Agent。
- 不允许专家直接修改 Trip Board 状态。
