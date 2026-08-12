# AI-Native SDLC · 受治理的 PRD → Dev → QA 流水线技能包

> 一套**覆盖「需求 → 开发 → 测试」全链路的 AI 交付治理框架**——不是三个零散工具，而是共用同一套「文件化交接 + 确认闸门 + 真实工具链」的三段流水线。
> 顶层还有一个 **`ai-sdlc-master` 多 Agent 总编排器**：一条指令把 PRD → Dev → QA 当一整条链自动跑，只在确认闸门点打扰你。
> 它解决的核心问题：让 AI 从「说写完了」变成「真的写完了、且可验证、且可回退」。由**产品经理视角**设计。

![AI-Native SDLC 架构](assets/architecture.svg)

---

## 为什么做这个

AI 编程工具越来越强，但有三个通病：

1. **一次性写码就跑偏**——需求里有 10 个隐含假设，Agent 替你拍了 9 个，第 4 个在生产环境才爆。
2. **上下文一多就漂移**——对话越长，越早期的决策越容易被忘，前后产物对不上。
3. **无人验收就当完成**——Agent 说"写完了"，其实没跑测试、改了不相关的代码。

我的解法不是写更长的 prompt，而是把"产品 → 开发 → 测试"拆成**三段受治理的流水线**，每段用
**多 Agent 编排 + 确认闸门 + 文件化交接**串起来。

---

## 它包含什么

### 1. PRD 流水线（`prd-master` + 5 步子技能）
把"一个想法"变成"一份可执行的 PRD + 可点击原型"。编排器只做调度，**不生产内容**；
每步产物落盘为文件（01-brief → 02-stories → 03-outline → 04-prd → 05-prototype），
下游步骤只看文件、不读聊天历史，从根上杜绝上下文漂移。每步有**确认闸门**，没确认不进下一步。

### 2. 受治理开发（`dev-harness` + `harness/` 治理母本）
一套架在"需求"与"开发 AI"之间的 5 道门禁：
`G1 自检闭环` / `G2 范围自检` / `G3 置信度上报` / `G4 一键还原` / `G5 代码清洁`。
看不懂的需求不写、超范围的不提交、炸了能秒回退。治理规则以**人读 + AI 读**双视图存在。

### 3. QA 流水线（`qa-master` + 5 步子技能，含 Python 工具链）
把"测什么"变成"可执行的用例 + 人/AI 分工表 + 执行报告"。不只是 prompt——
`scripts/` 下是**真实干活的 Python 工具**：`gate_check`（门禁校验）、`trace_audit`（过程追溯）、
`merge`（结果合并）、`generate_excel` / `format_excel`（用例表生成）。

---

## 端到端流程：一条从想法到验证的链路

三段不是孤立的技能，而是一条**产物级无缝衔接**的交付链——上一阶段的产出文件，就是下一阶段的唯一输入；中间没有复制粘贴，也没有重新 briefing：

```
想法
  │  prd-master（需求拷问 → 用户故事 → 大纲 → PRD → 可点击原型）
  ▼
04-prd.md  +  05-prototype.html          ← PRD 产物
  │  dev-harness 直接以 04-prd.md 为需求输入（无需重新描述背景）
  ▼
代码  +  4 份门禁报告（self_check / diff_scope / pending / artifact_binding）
  │  QA 以 PRD + 代码产出为测试基线
  ▼
qa-work/ 用例  +  人/AI 分工表  +  05-results 执行结果
```

你体感上"跑的是一条链、甚至不用每次重新交代就能接着跑"，靠的是两件事：

1. **文件化交接**：阶段之间靠产物自动衔接，不用复制粘贴、不用重新 briefing；
2. **项目级持久记忆**：三段的所有产物都落盘在项目工作区（`prd-work/` `qa-work/` `harness/`），还有一个显式的 `ai-sdlc-master` 项目记忆 `state.json`——所以在一个真实项目里，你今天跑完 PRD，明天回来说"继续"，编排器读文件 + 读 `state.json` 就能直接进开发、进测试；跨会话、跨阶段，链路不断。

这正是它和「三个独立 prompt skill 拼在一起」最大的代差：**别人每次都要从头喂背景，你的是"记得住的项目"。** 你只需要在确认闸门点拍板，其余的衔接交给文件与记忆。

---

## 真正的多 Agent 模式（`ai-sdlc-master`）

前面三段各自是编排器，但过去要靠你手动依次调用。现在 `ai-sdlc-master` 把它们升级成**一个层级多 Agent 系统**——这才是它"非常之牛"的地方：

```
你（一句话："跑 xxx 的完整交付"）
  │  加载 ai-sdlc-master → 顶层编排器 agent
  ▼
┌─ PRD phase agent ──────────────┐
│   加载 prd-master → 再派 5 个 step agent │   ← 上下文隔离，天然抗漂移
├─ DEV phase agent ──────────────┤
│   加载 dev-harness → 走 5 道门禁 G1~G5  │   ← 真实写代码 + 4 份报告
├─ QA phase agent ───────────────┤
│   加载 qa-master → 再派 5 个 step agent │   ← 含 Python 工具链
└────────────────────────────────┘
      每个 phase 之间靠产物自动 handoff，只在闸门点停
```

**为什么是"真多 Agent"而非"一个长 prompt"：**

- **层级调度**：你 → phase agent → step agent，三层 agent 各管一摊。PRD/QA 的 phase agent 自己还会再派发 step agent，是真正的 agent 调 agent。（在支持嵌套派发的运行时下为三层；若运行时限制子 agent 再派发，phase agent 会**内联执行** step，治理机制不变——这是优雅降级，不是缺陷。）
- **上下文层层隔离**：每个 agent 启动时只读取上游产物文件，不继承任何聊天历史。对话再长，早期决策也不会被忘——这正是反漂移铁律的运行时保证。
- **持久记忆跨会话**：编排器把三段进度写进 `<项目根>/.workbuddy/sdlc/state.json`（由 `sdlc_status.py` 读写，纯标准库、零依赖）。隔天回来说"继续"，从断点秒级恢复，不用重新交代。
- **闸门只在真决策点停**：phase 之间靠产物自动流转；只有 phase 内部闸门（如 QA 的测试方案确认、DEV 的 G3 低置信上报）要求时才打断你。

> 一句话：过去是「三个 skill 你手动串」，现在是「一个编排器把三个 skill 当一整条多 Agent 链路自动跑」。

---

## 为什么值得看（对比「单文件 prompt skill」）

市面上大多数 Agent Skills 是「一个 SKILL.md，一次对话出结果」。这套不一样，差异在三点：

| 通病 | 单文件 prompt skill | 本仓库的做法 |
| --- | --- | --- |
| **长对话失忆** | 决策散在聊天里，越长越漂移，前后产物对不上 | **文件化交接**：步骤间唯一接口是产物文件，聊天噪音到此为止，从根上 anti-drift |
| **全自动跑飞** | Agent 自己拍板推进，没人拦 | **确认闸门**：关键节点必须人确认，Agent 不私自往下走 |
| **规则靠嘴约束** | 写「请遵守 XX 规范」，靠模型自觉 | **真实工具链**：能写成代码的校验/追溯就用 Python 干（`gate_check` / `trace_audit` / `merge`），不靠自觉 |

一句话：别人交的是「更好的提示词」，我们交的是「一套带闸门和工具链的治理流水线」。

---

## 稳定性从哪来（不是靠自觉，是靠机制）

- **机械闸门，跳过不可能**：QA 的 `gate_check` / `merge` / `trace_audit` 在跑之前检查上游产物的状态位，未 `confirmed` 直接 `exit(1)` 拒绝执行。"跳过确认"在工具层面无法发生，不是靠模型自觉。
- **只在真决策点打断你**：`auto-confirm` 机制——子 agent 自检通过且无范围争议时，编排器自动放行、不弹窗；只有「测试方案」「人机分工」这类真要判断的节点才请你拍板。既不每步烦你，也不悄悄跑飞。
- **长链路不漂移**：每一步都是独立子 agent，启动时只读取上游产物文件，不继承任何聊天历史。对话再长，早期决策也不会被忘。
- **炸了能秒回退**：dev-harness 的 G4 一键还原，重要节点存快照；上轮炸了，原版本保留、一键回退。
- **需求 ↔ 用例可追溯**：`trace_audit` 逐条比对每个需求是否被用例回指，漏测即拦截——不会"测了一堆却没覆盖关键需求"。
- **失败时回填上游**：下游变了自动回头同步上游文档，产物始终一致。

---

## 怎么用

### 前置
1. 安装 [WorkBuddy](https://www.workbuddy.cn)。
2. 把本仓库 `skills/` 下的 14 个 skill 复制到你的 WorkBuddy skills 目录。
3. 把 `harness/` 复制到 `~/.workbuddy/harness/`（或某个项目的 `.workbuddy/harness/`）。

### 跑起来

**方式 A · 一条指令跑完整链（推荐，多 Agent 模式）**
- 对 AI 说"用 ai-sdlc-master 跑 <项目名> 的完整交付" → 顶层编排器自动串联 PRD → Dev → QA，阶段间自动 handoff，只在闸门点拍板。
- 隔天回来说"继续 <项目名>" → 编排器读 `state.json` 从断点续跑，不用重新交代。

**方式 B · 三段分开手动调**
- 对 AI 说"帮我做个 PRD" → 走 `prd-master`，产出 `04-prd.md`
- 说"用 harness 开发（基于这份 PRD）" → `dev-harness` 以 `04-prd.md` 为需求输入
- 说"跑 QA" → `qa-master` 以 PRD + 代码产出为测试基线
- 三段共用文件化交接与闸门契约，阶段间无需重新 briefing

---

## 这是方法论，也是参考实现

即使你不装 WorkBuddy，本仓库的 **README + 架构图 + 各 skill 的产物规范**也能让你完整看懂
"如何治理 AI 开发"。这套方法论可平移到 Cursor / Claude Code / Codex 等任何 Agent 运行时——
把 `guardrails/` 和"确认闸门"搬过去即可。

> 注：本仓库的 skill 使用 WorkBuddy 的 Skill / Agent / 文件工具原语，是唯一可"直接运行"的环境。
> 其价值更在**设计思路**本身。

---

## 目录结构

```
ai-sdlc-skills/
├── README.md
├── LICENSE                 # MIT
├── .gitignore
├── .gitattributes
├── assets/
│   └── architecture.svg    # 架构图（本文档配图）
├── skills/
│   ├── ai-sdlc-master/     # ★ 多 Agent 总编排器（串联整条链 + 持久记忆）
│   │   ├── SKILL.md        #   顶层编排器指令
│   │   ├── state.schema    #   state.json 字段契约
│   │   ├── HANDOFF.md      #   阶段间 handoff 契约
│   │   └── scripts/
│   │       └── sdlc_status.py  # 项目记忆读写（纯标准库）
│   ├── prd-master/         # PRD 编排器
│   ├── prd-step1-grill/    # ① 需求拷问
│   ├── prd-step2-stories/  # ② 用户故事
│   ├── prd-step3-outline/  # ③ 设计大纲
│   ├── prd-step4-prd/      # ④ PRD
│   ├── prd-step5-prototype/# ⑤ 交互原型
│   ├── qa-master/          # QA 编排器 + Python 工具链
│   ├── qa-step1-extract/   # ① 需求提取
│   ├── qa-step2-design/    # ② 测试设计
│   ├── qa-step3-cases/     # ③ 用例编写
│   ├── qa-step4-classify/  # ④ 用例分类（人 / AI）
│   ├── qa-step5-exec/      # ⑤ 用例执行
│   └── dev-harness/        # 受治理开发门禁
└── harness/                # dev-harness 依赖的治理母本
    ├── guardrails/         # G1~G5 五道门禁
    ├── module-map.yaml/.md # 功能 → 目录 映射
    ├── request.schema      # 产物报告字段规范
    ├── requirement.example.md
    └── snapshots/          # 版本快照
```

## License

[MIT](LICENSE) © 2026 susubing123
