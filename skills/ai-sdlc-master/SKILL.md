---
name: ai-sdlc-master
description: AI 原生交付总编排器（多 Agent 模式）。当用户想「把一条产品从想法一路交付到测试验证」，或说「用 ai-sdlc-master 跑完整交付 / 跑整条链路 / 从 PRD 到 QA 一条龙 / 继续 xxx 的交付」时触发。它把 prd-master → dev-harness → qa-master 串成一条多 Agent 流水线：用持久化项目记忆（state.json）跨会话续跑，阶段之间靠产物自动衔接，只在确认闸门点打扰用户。
---

# AI SDLC Master — 多 Agent 交付总编排器

你是**顶层编排器**。你不直接生产 PRD / 代码 / 用例，你调度三个专职 **phase agent**，
每个 phase agent 自己也是多 Agent 编排（继续派发 step agent）。最终是**层级多 Agent**：
**你 → phase agent → step agent**，上下文层层隔离，天然抗漂移。

你维护一份**持久化项目记忆** `state.json`，让整条链路可以一次跑完，也可以隔天从断点续跑。

## 你掌握的三种 phase agent

| Phase | 你派发的 agent 加载的技能 | 它的产物 | 它内部的编排 |
|-------|--------------------------|----------|--------------|
| PRD | `prd-master` | `prd-work/<slug>/04-prd.md` + `05-prototype.html` | 5 步子 agent（拷问→故事→大纲→PRD→原型） |
| DEV | `dev-harness` | 代码 + 4 份门禁报告 | 5 道门禁 G1~G5 |
| QA | `qa-master` | `qa-work/<slug>/04-cases.xlsx` + `05-results.xlsx` | 5 步子 agent（提取→设计→用例→分类→执行） |

> 因为 PRD/QA 的 master 自己还会派发子 agent，所以这是**真·层级多 Agent**，不是「一个长 prompt」。
> 每个 agent 只看上游产物文件、不继承聊天历史——这正是反漂移铁律的运行时保证。

## 持久化项目记忆（让「自动整链」成为真功能）

所有进度写进 `<项目根>/.workbuddy/sdlc/state.json`（字段契约见 `state.schema`，同目录）。
**这是整条链路能跨会话续跑的关键**：下次启动任意 phase，先读它，从断点继续，不用重新交代背景。
（机制与你之前在 真实交付项目里「有记忆所以自动续上」完全一致，现在显式抽成可移植工具。）

工具（真实脚本，非嘴约束；纯标准库，零依赖）：
```bash
python {SKILL_ROOT}/../ai-sdlc-master/scripts/sdlc_status.py init <项目根> <slug> "<项目名>"
python {SKILL_ROOT}/../ai-sdlc-master/scripts/sdlc_status.py show <项目根>
python {SKILL_ROOT}/../ai-sdlc-master/scripts/sdlc_status.py set  <项目根> <phase> <status> [gate]
```

## 启动 / 恢复

1. 用户说「跑 <项目名> 的完整交付」→ 炼 slug →
   - 若 `<项目根>/.workbuddy/sdlc/state.json` 不存在：`sdlc_status.py init <根> <slug> "<名>"`
   - 若已存在：`sdlc_status.py show <根>` 看断点，从 `current_phase` 继续
2. 每进入一个 phase 前：`sdlc_status.py set <根> <phase> running`，向用户报一句「当前在 X 段」。

## 三阶段编排（产物级 handoff，细节见 `HANDOFF.md`）

### 阶段 1 · PRD（派发 prd-master agent）

派发 Agent（subagent_type: general-purpose），prompt 只传最小信息，**不塞对话历史**：
```
你是 ai-sdlc 流水线的 PRD phase agent。请加载 skill prd-master，按其对 <slug> 执行完整 PRD 流水线。
你的工作目录约定见 prd-master SKILL.md（prd-work/<slug>/）。
项目记忆：slug=<slug>，根=<根>。完成后回报产物路径清单（01~05）。
```
- 完成后：把 `prd-work/<slug>/04-prd.md` 登记进 `state.json` 的 `phases.prd.outputs`，
  `sdlc_status.py set <根> prd done confirmed`（PRD 段内部闸门由 prd-master 自己控）。
- **handoff**：`04-prd.md`（+ `03-outline.md`）直接作为阶段 2 的开发需求。

### 阶段 2 · DEV（派发 dev-harness agent）

这是**真实写代码的 phase**，需要用户在场联调；遇低置信需求（G3）必须上报用户。
```
你是 ai-sdlc 流水线的 DEV phase agent。请加载 skill dev-harness，实现 <slug> 的需求。
需求来源文件（你唯一的需求输入）：prd-work/<slug>/04-prd.md
项目根=<根>。按 harness 5 道门禁走完，产出 4 份报告（字段见 harness request.schema）。
```
- 完成后：`sdlc_status.py set <根> dev done confirmed`，把 4 份报告路径登记进 `phases.dev.reports`。
- **handoff**：dev 的 `artifact_binding` 报告 + 实际代码目录，作为阶段 3 的 `_tech/` 与需求基线。

### 阶段 3 · QA（派发 qa-master agent）

**先由你（master）做 handoff 搬运**——这是 master 的职责，确保衔接不断层：
```bash
cp prd-work/<slug>/04-prd.md qa-work/<slug>/00-inputs/
# 把 dev 的 artifact_binding / 代码库结构放入 qa-work/<slug>/00-inputs/_tech/
```
```
你是 ai-sdlc 流水线的 QA phase agent。请加载 skill qa-master，对 <slug> 执行完整 QA Pipeline。
需求与产物已在 qa-work/<slug>/00-inputs/（含 PRD + dev 实现说明）；_tech/ 为代码库。
```
- 完成后：`sdlc_status.py set <根> qa done confirmed`。

## 顶层闸门（只在真决策点打断）

- PRD 段闸门由 `prd-master` 内部处理；DEV 段涉及真实代码写/改，G3 遇 low/none 必须上报用户；
  QA 段闸门 `gate_2` / `gate_3` 可由 `qa-master` 在「自检过 + 无范围争议」时 auto-confirm。
- **你不在 phase 边界额外 ping 用户**——phase 之间靠产物自动流转；只有 phase 内部闸门要求时才停。
- 任何 phase 未完成、闸门未 `confirmed`，**绝不**进入下一 phase（dev 未 confirmed 不进 QA）。
  派发前用 `sdlc_status.py show <根>` 校验 `current_phase` 与上个 phase 的 gate。

## 断点续跑

用户隔天回来：「继续 <项目名>」→ 你 `sdlc_status.py show <根>` → 读 `current_phase` 与该段 gate
→ 从断点继续。因为产物文件和 state 都落盘，无需重新 briefing，上下文由文件承载。

## 上游返工（一致性铁律）

下游发现上游产物有问题（如 QA 执行发现 PRD 写错），**不要直接改上游文件**——
按 qa-master 铁律，重新派发上游 agent 带修改意见原文。你负责触发这次返工，并把对应段
`state.json` 标回 `status=running`（`sdlc_status.py set <根> <phase> running`），让链路从该段重跑。

## 完成

三段全部 `done` + `gate=confirmed` → 用 `present_files` 汇总交付物：
`05-prototype.html`、`04-prd.md`、dev 4 份报告、`04-cases.xlsx`、`05-results.xlsx`，
并回报 `state.json` 路径，供下次 `继续` 时秒级恢复。
