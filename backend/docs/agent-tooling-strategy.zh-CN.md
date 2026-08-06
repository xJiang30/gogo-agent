# Agent 工具策略

后端通过 LiteLLM Proxy 保持模型路由灵活，所以 Agent 工具层不应该默认假设当前模型一定是
OpenAI Responses 模型。

## 建议

默认使用本地 function tools。把 `app/capabilities` 中共享的能力，用
`app/agents/tools` 下的轻量 Agents SDK 适配层包装起来，让 Agent 在需要可靠业务逻辑时调用。

对 Gogo Agent 来说，这意味着：

- 模型负责理解自然语言里的旅行意图。
- Function tools 负责检查或转换结构化旅行数据。
- Application services 负责维护 Trip 状态和 Proposal 状态，不把业务状态只藏在聊天记忆里。

## Hosted Tools

在后端通过 `LitellmModel` 路由模型时，默认不使用 OpenAI hosted tools。

Web search、file search、code interpreter、hosted MCP、image generation、tool search
这类 hosted tools，更适合 Agent 运行在 OpenAI 托管的 Responses models 上时使用。Gogo
Agent 现在需要通过 LiteLLM 在 GPT、Claude、DeepSeek、Qwen、Kimi 等模型之间切换，如果核心旅行流程依赖 hosted tools，会降低可移植性。

当产品需要实时数据时，优先做后端自己拥有的 adapters：

- 地图和路线 API
- 酒店或 POI 搜索 API
- 天气 API
- 签证或政策数据源
- 预算和汇率服务

再把这些 adapters 暴露成 function tools，这样不管底层选择哪个模型供应商都能使用。

## Tool Search

现在先不启用 tool search。

Tool search 适合工具很多、模型需要按需加载工具 schema 的场景。当前后端工具数量还很少，显式挂载 function tools 更简单，也更容易测试。

等旅行工具目录变大以后再重新评估 tool search，比如后面分别加入机票、酒店、地图、天气、签证规则、预算、日历、预订流程等工具时。

## Agents As Tools

等 Trip Board schema 稳定后，agents-as-tools 是首选的专家能力模式。

当一个面向用户的 Gogo Agent 仍然需要掌控整体体验，同时把边界清晰的任务交给专家 Agent 时，可以使用这个模式。比较适合的候选包括：

- Route Sense：检查每天的路线形状、交通压力和地理节奏。
- Budget Sense：估算费用范围，并标记昂贵选择。
- Stay Sense：比较住宿区域的取舍。
- Food Sense：建议餐食锚点，但不过度塞满行程。

用户感受到的应该是一个助手背后有专家判断，而不是被多个可见 Agent 来回交接。

普通旅行规划里不要使用可见 handoff。Handoff 会改变当前由哪个 Agent 接管对话，容易让体验变重。除非未来某个流程有明确的合规、客服或运营边界，否则专家能力都应该保持在内部。

## 当前边界

当前：

- 用 `@function_tool` 包装稳定、可测试的后端能力。
- 模型路由继续集中在 `app/providers/llm.py`。
- Agent session memory 和 Trip Board 业务状态保持分离。

之后：

- 当专家推理变得有价值时，再加入 agents-as-tools。
- 只有工具目录变大以后，才考虑 tool search。
- 只有明确需要 OpenAI 托管 Responses model 能力的流程，才使用 hosted tools。
