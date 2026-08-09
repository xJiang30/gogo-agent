# 可观测性

Gogo Agent 需要足够的可观测性来理解 Agent 为什么给出某个建议，但默认不应该泄露用户的旅行细节。

## Trace Metadata

Agent run 应该带上轻量元数据：

- `workflow_name`：产品工作流，例如 `gogo-agent-intake`
- `group_id`：当前 `session_id`
- `app_name`
- `app_env`
- `litellm_model`
- `session_id`

这些 `RunConfig` 设置由 `app/providers/llm.py` 统一负责，避免各个 service 重复实现 tracing 行为。

## 默认隐私姿态

本地开发默认关闭 trace export：

```env
ENABLE_AGENT_TRACING=false
OPENAI_AGENTS_DONT_LOG_MODEL_DATA=1
OPENAI_AGENTS_DONT_LOG_TOOL_DATA=1
```

`RunConfig` 里把 `trace_include_sensitive_data` 设为 `False`。这样默认不会把完整用户消息、预算、偏好和工具 payload 记录到 traces 中。只有在受控调试场景下，团队才应该有意识地调整这个设置。

## LiteLLM 和非 OpenAI 模型

后端通过 `LitellmModel` 路由模型，通常会经过 LiteLLM Proxy。Tracing export 应该和模型路由分开理解。

如果之后启用 OpenAI tracing，需要显式配置 OpenAI tracing 凭证，并继续把 LiteLLM provider 凭证留在 LiteLLM 层。不要因为存在某个模型供应商 key，就隐式打开 hosted tracing。

## 应该观察什么

有价值的 trace 和 log 维度包括：

- session id 和 workflow name
- 选中的模型别名
- tool calls 和 tool failures
- guardrail tripwires
- proposal 创建
- proposal 确认或拒绝
- Trip Board apply 成功或失败

## 未来 Evals

在 Trip Board schema 和 UI 闭环更稳定前，先不要急着做完整 eval suite。第一批适合的 eval cases 包括：

- intake 只追问必要缺失字段
- 信息足够时进入 Trip Board，而不是继续冗余提问
- proposal 在修改前必须要求用户确认
- guardrails 拦截未确认修改的表述
- itinerary 节奏保持轻松，不把每天塞太满
