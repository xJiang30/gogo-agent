# Gogo Agent 五轮分层人工验收测试集

运行命令：

```powershell
python manual_agent_playground.py
```

这个脚本不是菜单，也不是完全自由聊天。它会引导你按五轮测试完整产品闭环：初始规划、上下文追问、选择方案、生成 proposal、接受并执行 proposal。

## Round 1. 初始规划

默认输入：

```text
PS C:\Users\32696\Desktop\gogo-agent> python manual_agent_playground.py
Gogo Agent Five-Round Manual Test
---------------------------------
This uses the real model from .env.
Follow the prompts. Press Enter to use each suggested test input.

Round 1. 初始规划
----------------------------------------
OK: 有 3 个方案，包含住宿/周边游/美食，不完全重复。

Travel request
Default: 帮我规划一个福冈三日游，想吃好吃的，也想安排一天周边游，节奏不要太赶
Press Enter to use default. Type b/back to stop this test.
> 
```

OK 标准：

- 返回 `kind: recommendation_set`。
- 有 3 个推荐方案。
- 每个方案至少能看出住宿区域、周边游、美食、节奏。
- 不出现完全重复的方案。

需要记录的问题：

- 方案太模板化。
- 三个方案只是换住宿区域，周边游都一样。
- 输出缺少具体 day plan。

## Round 2. 上下文追问

默认输入：

```text
你觉得第二天会不会太赶？
```

OK 标准：

- 返回 `kind: answer`。
- 能基于 Round 1 的推荐摘要回答。
- 不应该说“请提供具体行程”。
- 最好能分析活动数量、交通压力、吃饭时间、是否需要删减。

需要记录的问题：

- 忘记上一轮规划。
- 不理解“第二天”。
- 回答太泛泛。

## Round 3. 选择推荐方案

默认输入：

```text
1
```

OK 标准：

- 脚本把第一个 recommendation 转成 `current_trip`。
- 能打印出 Day 1 / Day 2 / Day 3。
- 每天下面有可修改的 node。

需要记录的问题：

- recommendation 缺少 `day_plans`，只能生成 fallback trip。
- day/node 信息太少，后续 proposal 无法准确定位。

## Round 4. 生成修改 Proposal

默认输入：

```text
第二天和第三天都有点赶，帮我重新平衡一下，但不要减少美食
```

OK 标准：

- 返回 `kind: proposal`。
- 有 `proposal_id`。
- 有至少 1 个 operation。
- 不直接修改正式 trip。
- proposal 能说明影响哪些 day/node。

需要记录的问题：

- 只返回普通 answer，没有 proposal。
- proposal operations 为空。
- proposal 太泛泛，看不出改了什么。

## Round 5. 接受并执行 Proposal

默认输入：

```text
接受这个修改
```

OK 标准：

- 返回 `kind: execution`。
- trip version 增加。
- decision log 记录执行的 proposal id。
- current trip 被更新。

需要记录的问题：

- 找不到 latest proposal。
- proposal 无法接受。
- 执行后 version 没变。
- 执行后看不出 trip 哪里变了。

## 总体判断

一轮完整 OK 的结果应该是：

```text
recommendation_set -> answer -> current_trip -> proposal -> execution
```

如果某一轮失败，先记录是哪一轮失败，不要急着继续端到端。这样我们能判断问题属于模型效果、上下文、推荐转 trip、proposal 生成，还是 proposal 执行。
