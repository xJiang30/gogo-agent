# Gogo Agent Backend

这是 Gogo Agent 正式产品后端工作区。

[English README](README.md)

## 职责

后端负责：

- Trip 和 Proposal 的 API 边界
- OpenAI Agents SDK 的 Agent 定义
- 通过一个 provider 模块统一接入 LiteLLM
- 共享的确定性旅行能力

## 当前架构

```text
FastAPI API
  -> Application Services
  -> OpenAI Agents SDK
  -> LitellmModel
  -> LiteLLM Proxy
  -> 模型供应商
```

默认推荐走 LiteLLM Proxy。后端只认 `travel-primary` 这样的稳定模型别名，真实模型在
`litellm.config.example.yaml` 中配置。这样未来在 GPT、DeepSeek、千问、Kimi、Claude
等模型之间切换时，优先修改 LiteLLM 配置，而不是修改 Agent 代码。

如果临时不想启动 Proxy，可以把 `LITELLM_BASE_URL` 留空，后端会退回 LiteLLM 直连
provider 的模式。

## 命令

```bash
python --version  # requires Python >= 3.11
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
pytest
```

复制 `.env.example` 为 `.env`，并在运行真实 Agent 调用前配置相关密钥。

## 模型网关

默认路径是：

```text
OpenAI Agents SDK -> LitellmModel -> LiteLLM Proxy -> 模型供应商
```

用示例配置启动本地 LiteLLM Proxy：

```bash
export ZAI_API_KEY=...
litellm --config litellm.config.example.yaml
```

后端保持指向稳定模型别名：

```env
LITELLM_MODEL=travel-primary
LITELLM_BASE_URL=http://127.0.0.1:4000
LITELLM_API_KEY=local-proxy-key
```

要切换底层模型时，修改 LiteLLM 配置里的 `travel-primary` 指向即可，不需要改 Agent
代码。

如果本地快速实验不想走 Proxy，可以留空 `LITELLM_BASE_URL`，并使用 LiteLLM 的
provider 路由模型字符串：

```env
LITELLM_MODEL=zai/glm-4.7-flash
LITELLM_BASE_URL=
ZAI_API_KEY=...
```

`pyproject.toml` 仍然是 Python 包元数据来源。`requirements.txt` 和
`requirements-dev.txt` 用于本地快速安装，以及需要 pip-style 依赖列表的部署环境。

LiteLLM 目前限制在 `1.75.0` 以下，是为了保持本地安装轻量，避免 macOS 上意外拉取
需要 Rust 的源码构建。
