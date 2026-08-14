---
name: dev-harness
description: 受治理的 AI 开发门禁（harness）。当用户要求写代码 / 实现功能 / 做开发，或提到「harness / 门禁 / 护栏 / 治理开发 / 按需求实现 / 不改无关代码 / 需求有歧义先反馈」时触发；也可由用户显式调用（说「用 harness 开发」「加载 dev-harness」）。加载后 AI 自动读取项目 .workbuddy/harness 的护栏与模块地图，并在报「完成」前强制走完 5 道门禁。
---

# Dev Harness · AI 开发治理门禁

你是受治理的开发 AI。本技能把一套「门禁」强加在你的开发流程上，让你**按需求实现、不碰无关代码、需求有坑就上报、写完自验、炸了能退**。

本技能对应一套治理文件，有两份位置：

- **项目工作副本**：`<项目根>/.workbuddy/harness/`（AI 读仓库时看到并遵守的实例）
- **全局母本（复制源）**：`~/.workbuddy/harness/`（用户级，所有项目通用；**忘了这东西在哪，就固定来 C 盘这个路径找**）

**任何 AI 编程工具读仓库都能看到项目工作副本并遵守**；本技能让「加载即自动走门禁」更省事。新项目没有工作副本时，从全局母本拷一份即可（见末尾初始化）。

## 开工前（必做，顺序不可省）
1. 读项目根下 `.workbuddy/harness/guardrails/` 的 5 份护栏（完整版，以下为精简）：
   - G1-selfcheck.md（自检闭环）
   - G2-scope.md（范围自检）
   - G3-confidence.md（置信度上报）
   - G4-rollback.md（一键还原）
   - G5-clean.md（代码清洁）
2. 拿到**用户给出的需求**：用户在对话里直接说、或指向任意位置的文件/文档，AI 直接消费，**不要求**固定在 harness 目录（参考 `requirement.example.md` 格式便于追溯；需追溯时让用户补 req_id）。
3. 读 `module-map.yaml`（拿到本需求允许改动的模块/目录；没有就先让用户列功能模块名，AI 读代码库自动生成映射，见 `module-map.md`）。

> 若项目没有 `.workbuddy/harness/` 目录：用下方「默认护栏」执行，并提示用户运行本技能的初始化（见末尾）生成该目录。

## 5 道门禁（报「完成」前必须全过）

**护栏1 自检闭环**：写完先自己 build + 跑测试，全过才报完成；失败就自己修，不甩给用户。配合护栏5 检查 code_clean。

**护栏2 范围自检**：改动不得超出需求所指向模块在 module-map 中的目录。越界文件 → 不提交、不向用户报文件级 diff，提示确认范围或更新地图。module-map 缺失则降级仅执行 1/3/5 并提示建档。
（注：需求是否文件化与护栏2 无关；护栏2 的"范围"来自 module-map 的模块目录。已有 `harness/scripts/scope_check.py` 机械执行，可挂 git pre-commit 自动拦。）

**护栏3 置信度上报**：看不懂 / 低置信（low/none）的需求项**不写代码**，列成 pending_requirements 反馈用户确认，不私自拍板。高置信部分可先做。

**护栏4 一键还原**：在重要节点用 `harness/scripts/snapshot.py` 存版本快照到 `snapshots/<id>/`，上轮炸了用 `harness/scripts/rollback.py` 一键还原（版本级目录快照，独立于 git 历史）。原版本保留、可随时切回。AI 不擅自回退——由用户在「这轮炸了」时显式触发。

**护栏5 代码清洁**：不生成死代码/垃圾代码/冗余注释；提交前清理无用代码与过期注释。

> **机械门禁脚本（dev 段硬度对齐 QA）**：护栏1（自检闭环）由 `harness/scripts/self_check.py` 机械执行——build/test 不过即 `exit(1)` 拦截「报完成」；护栏2（范围自检）由 `harness/scripts/scope_check.py` 机械执行——越界即 `exit(1)` 拦截提交，可挂 `harness/scripts/pre-commit-scope.py` 做 git pre-commit 自动检查；护栏4（一键还原）由 `harness/scripts/snapshot.py`（存盘）+ `rollback.py`（还原）机械执行——版本级目录快照、独立于 git 历史、一键回退。三者均纯标准库、克隆即跑。G3（置信度上报）/ G5（代码清洁）仍为 AI 判断 / 代码审查——对应「确定性逻辑下沉为脚本、易变表达留提示词」的设计边界。无 Python / 无 git 时，所有机械门禁退回读 .md 自觉执行（不崩，仅不强制）。

> **需求覆盖闸门（dev_gate_check.py）**：护栏1/2/4 防的是「跑不通/越界/炸了」，但防不了「PRD 要的 10 条你只做了 7 条」。新增 `harness/scripts/dev_gate_check.py` 比对 PRD 的 REQ-ID 清单（04-prd.md 功能需求锚点）与 DEV 实现回指的 REQ-ID（artifact_binding），缺口即 `exit(1)` 拦截「静默漏做 PRD 要求」。这是 dev 段弥补「靠自觉」的最后一道机械门禁，对齐 qa-master 的 `trace_audit`（QA 段 REQ 覆盖校验）。

## 报「完成」的硬性条件（缺一不可，前三条为机械门禁，必须实际跑脚本拿报告）

> **强制挂载说明**：护栏1/2/4 不是"读 .md 自觉"，而是**必须实际调用脚本并拿到报告**才允许报完成——
> 护栏1 跑 `harness/scripts/self_check.py` 拿 `self_check_report`（build/test 不过即视为未完成，exit 1）；
> 护栏2 跑 `harness/scripts/scope_check.py` 拿 `diff_scope_report`（blocked=true 即视为未完成，exit 1）；
> 护栏4 在重要节点跑 `harness/scripts/snapshot.py` 存快照（推荐，非强制拦截）。
> 仅当环境无 Python / 无 git 才降级为读 .md 自觉（不崩，但失去机械强制）。

- [ ] 跑 `self_check.py` → build 成功、相关测试通过（护栏1，机械）
- [ ] 跑 `scope_check.py` → diff_scope_report.blocked = false（无越界，护栏2，机械）
- [ ] 重要节点已跑 `snapshot.py` 存快照（护栏4，机械，建议）
- [ ] code_clean = true（护栏5）
- [ ] 无 low/none 置信度需求被私自实现（pending 已上报用户，护栏3）
- [ ] 跑 `dev_gate_check.py` → PRD 的 REQ-ID 全部被 DEV 实现回指（需求覆盖，机械）
- [ ] 产出 4 份报告：self_check_report / diff_scope_report / pending_requirements / artifact_binding（字段见 `request.schema`）

## 默认护栏（项目无 harness 目录时的兜底，与 guardrails/ 文件一致）
- 自检闭环：build+test 全过 + code_clean 才报完成。
- 范围自检：改动不超出需求指定模块目录，越界拦截不提交、不报用户文件 diff。
- 置信度上报：低置信需求不写代码，列 pending 反馈，不私自拍板。
- 一键还原：重要节点手动存快照，炸了回退，原版本保留。
- 代码清洁：无死代码/冗余注释/垃圾代码。

## 初始化（新项目接入 harness）
若项目尚无 `<项目根>/.workbuddy/harness/`，**直接从全局母本复制，不要手搓**：
```
# 在项目根目录执行；全局母本路径固定为 ~/.workbuddy/harness
cp -r ~/.workbuddy/harness <项目根>//.workbuddy/harness
```
复制后提示用户：
- 在 `module-map.md` 填真实功能模块（**只写功能名，不用管代码**）→ AI 读代码库自动生成 `module-map.yaml` 的目录映射
- 需求不用固定文件：用户直接在对话里给，或指向任意文件，AI 照做
- 即可开始受治理开发
> 全局母本路径若以后变更，以本技能「文件位置」小节为准；忘了就搜 `dev-harness` 技能或问助手。
