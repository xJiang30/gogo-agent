# Agent Tooling Strategy

This backend keeps model routing flexible through LiteLLM Proxy, so agent tools
should not assume that the active model is an OpenAI Responses model.

## Recommendation

Use local function tools as the default integration path. Wrap shared
capabilities from `app/capabilities` in thin Agents SDK adapters under
`app/agents/tools`, and let agents call those tools when they need reliable
business logic.

For Gogo Agent, this means:

- The model interprets natural-language travel intent.
- Function tools inspect or transform structured travel data.
- Application services keep trip state and proposal state outside chat memory.

## Hosted Tools

Do not use hosted OpenAI tools by default while the backend is routed through
`LitellmModel`.

Hosted tools such as web search, file search, code interpreter, hosted MCP,
image generation, and tool search are most useful when the agent runs on
OpenAI-hosted Responses models. Gogo Agent currently needs to switch across GPT,
Claude, DeepSeek, Qwen, Kimi, and other providers through LiteLLM, so relying on
hosted tools would make core travel flows less portable.

When the product needs live data, prefer backend-owned adapters first:

- maps and routing APIs
- hotel or POI search APIs
- weather APIs
- visa or policy data sources
- budget and currency services

Expose those adapters as function tools so they remain available regardless of
the selected model provider.

## Tool Search

Do not enable tool search yet.

Tool search helps when there are many tools and the model should load tool
schemas only when needed. The current backend has a small tool surface, so
explicit function tools are simpler and easier to test.

Revisit tool search when the travel tool catalog grows large enough that prompt
and schema loading become noisy, for example after adding separate tools for
flights, hotels, maps, weather, visa rules, budgets, calendars, and reservation
workflows.

## Agents As Tools

Agents-as-tools are a good future fit, but not the next immediate layer.

Use this pattern when one user-facing Gogo Agent should stay in control while
delegating bounded work to specialist agents. Good candidates include:

- Route Sense: checks day shape, transit pressure, and geographic pacing.
- Budget Sense: estimates cost ranges and flags expensive choices.
- Stay Sense: compares hotel area trade-offs.
- Food Sense: suggests meal anchors without overloading the itinerary.

This should feel like one assistant with specialist judgment behind it, not
like the user is being handed between several visible agents.

## Current Boundary

Current:

- Use `@function_tool` for stable, testable backend capabilities.
- Keep model routing centralized in `app/providers/llm.py`.
- Keep agent session memory separate from Trip Board business state.

Later:

- Add agents-as-tools when specialist reasoning becomes valuable.
- Consider tool search only after the tool catalog becomes large.
- Use hosted tools only for flows that intentionally require OpenAI-hosted
  Responses model capabilities.
