# Gogo Agent

Gogo Agent 是一个 AI 原生旅行规划 MVP，聚焦对话式需求收集、可编辑 Trip Board、
地图可视化，以及 proposal-first 的 AI 辅助流程。

[English README](README.md)

## 工作区结构

```text
demo/       静态交互原型，用作产品流程和体验参考。
frontend/   正式前端工作区，使用官方 Vite React TypeScript 模板初始化。
backend/    FastAPI 后端，使用 OpenAI Agents SDK 和中心化 LiteLLM。
docs/       产品和架构规格文档。
```

`demo/` 会刻意和正式前端分开。它适合快速验证交互想法；稳定下来的流程再基于真实
API 契约重建到 `frontend/`。

## Demo

```bash
python3 -m http.server 8765 --directory demo
node demo/tests/ux-regression.test.mjs
```

然后打开 `http://127.0.0.1:8765`。

## Frontend

```bash
cd frontend
npm install
npm run dev
```

如果后端不是运行在 `http://127.0.0.1:8000`，后续可以通过 `VITE_API_BASE_URL`
指定 API 地址。

## Backend

```bash
cd backend
python --version  # requires Python >= 3.11
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
pytest
```

复制 `backend/.env.example` 为 `backend/.env`，配置 LiteLLM Proxy 连接：

```env
LITELLM_MODEL=travel-primary
LITELLM_BASE_URL=http://127.0.0.1:4000
LITELLM_API_KEY=local-proxy-key
```

启动 LiteLLM Proxy：

```bash
cd backend
litellm --config litellm.config.example.yaml
```

真实供应商密钥，例如 `ZAI_API_KEY`，应该通过本地 shell 环境或部署平台 secret 提供。
如果把 `LITELLM_BASE_URL` 留空，后端仍可退回 LiteLLM 直连供应商模式。

## 设计文档

- [中文 MVP 设计](docs/superpowers/specs/2026-07-07-ai-travel-agent-mvp-design.zh-CN.md)
- [High-level architecture](docs/superpowers/specs/2026-07-07-ai-travel-agent-high-level-architecture.zh-CN.md)
- [English MVP design](docs/superpowers/specs/2026-07-07-ai-travel-agent-mvp-design.md)
