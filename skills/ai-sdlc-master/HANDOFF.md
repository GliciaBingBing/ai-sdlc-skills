# 阶段间 Handoff 契约（PRD → DEV → QA）

`ai-sdlc-master` 把三段串成一条链，靠的是**产物级 handoff**：每段只消费上游的产物文件，
不消费上游的对话历史。下面是每段「吃什么、拉什么」的明确契约。

> 术语：`{root}` = 项目根；`{slug}` = 项目 slug。路径为相对 `{root}` 的约定。

---

## ① PRD → DEV

**PRD 段产出（prd-master 落盘于 `prd-work/{slug}/`）：**
- `04-prd.md` —— **主交付物，直接作为开发需求**
- `03-outline.md` —— 设计决策表（dev 做范围判断时的背景）
- `05-prototype.html` —— 交互原型（dev 对齐 UI 意图的参考）

**DEV 段消费：**
- 需求来源文件：`prd-work/{slug}/04-prd.md`（dev-harness 接受「指向任意位置的文件」作为需求，见其 SKILL.md）
- 范围地图：`module-map.yaml`（dev 读代码库自动生成目录映射）

**Handoff 动作（由 master 编排器在派发 DEV agent 前确认）：**
- 校验 `04-prd.md` 存在且 PRD 段 `gate=confirmed`
- 把 `04-prd.md` 路径作为 dev-harness 的「需求来源」传入 DEV agent 的 prompt
- 若项目尚无 `.workbuddy/harness/`，提示用户从母本初始化（见 dev-harness SKILL.md 末尾）

**DEV 段产出（dev-harness 落盘于 `<root>/.workbuddy/harness/` + 代码仓库）：**
- 实际代码变更
- 4 份门禁报告：`self_check_report` / `diff_scope_report` / `pending_requirements` / `artifact_binding`（字段见 harness `request.schema`）
- `snapshots/<version>/` 还原点（G4）

---

## ② DEV → QA

**DEV 段产出（接上）：**
- `artifact_binding` 报告 —— 把「需求项 ↔ 实现的代码/接口」绑定，QA 可追溯
- 代码仓库本身（含 `module-map` 对应的目录）

**QA 段消费（`qa-master` 落盘于 `qa-work/{slug}/`）：**
- `00-inputs/04-prd.md` —— **需求基线**（由 master 从 PRD 段拷贝）
- `00-inputs/_tech/` —— **技术输入**：dev 的 `artifact_binding` + 库表结构 + 接口文档（由 master 从代码库/报告搬运）
- `00-inputs/_archive/` —— PRD/原型归档（可选）

**Handoff 动作（由 master 编排器执行，这是 master 的职责，确保衔接不断层）：**
```bash
# 1) 需求基线：PRD 主交付物进 QA 输入
cp prd-work/{slug}/04-prd.md qa-work/{slug}/00-inputs/

# 2) 技术输入：dev 实现说明 + 代码库结构进 _tech/
#    artifact_binding 报告复制到 00-inputs/_tech/
#    代码库结构（库表/接口）按需抽取进 00-inputs/_tech/
```
- 校验 DEV 段 `gate=confirmed`（4 份报告齐全、无 low/none 置信度被私自实现）
- 确认 `00-inputs/` 与 `_tech/` 就绪后再派发 QA agent

**QA 段产出：**
- `04-cases.xlsx`（双页签：人/AI 分类）+ `05-results.xlsx`（执行结果）

---

## 闸门在 handoff 中的角色

- PRD 段闸门由 `prd-master` 内部处理；其 `04-prd.md` 通过即视为「可交付开发」。
- DEV 段涉及真实代码写改，`G3 置信度上报` 遇 low/none 必须上报用户，未确认不进 QA。
- QA 段闸门 `gate_2`（测试方案）/ `gate_3`（分类）可由 qa-master 在「自检过 + 无范围争议」时 auto-confirm。
- **master 不在 phase 边界额外 ping 用户**——phase 之间靠产物自动流转；只有 phase 内部闸门要求时才停。

## 一致性铁律

下游发现上游产物有问题（如 QA 执行发现 PRD 写错）**不直接改上游文件**——
按 qa-master 铁律，重新派发上游 agent 带修改意见原文。只有原 agent 有当时上下文，
改起来才不会引入新错。master 负责触发这次「上游返工」，并在 state.json 标记对应段 `status=running` 回退。
