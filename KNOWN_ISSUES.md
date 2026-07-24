# Gogo Agent Known Issues

## 1. Initial plan recommendation diversity is still limited

Status: recorded, not fixed yet.

Observed in manual test:

```text
Travel request:
帮我规划一个福冈三日游，想吃好吃的，也想安排一天周边游，节奏不要太赶

Output examples:
- Hakata Station base with Dazaifu day trip
- Tenjin base with Dazaifu day trip
- Nakasu base with Dazaifu day trip
```

What it means:

The agent is running correctly and no longer returns exact duplicate recommendation titles, but the three options are still too similar because they mainly vary the stay base while reusing the same day-trip destination.

Why it matters:

For a user-facing trip planner, recommendation options should feel meaningfully different. For example, one option could focus on Dazaifu, another on Yanagawa, and another on Itoshima, instead of all three using Dazaifu.

Likely improvement:

- Ask `mobility_research_node` to produce 3 distinct nearby day-trip destinations when the user asks for a surrounding-area trip.
- Improve recommendation diversity at the LLM planner layer, especially when multiple options share the same day-trip destination or stay base.
- Add a validation or scoring signal that penalizes recommendation sets where all options share the same day-trip destination.
