# RUNTIME_CONTRACT · 宿主运行时能力契约

本 skill 包宣称可「平移到 Cursor / Claude Code / Codex 等任何 Agent 运行时」，
但「可移植」不是口号——它要求宿主 runtime 提供以下能力。缺任一项，对应能力按
文末「降级约定」降级，不会崩，但会变弱（从机械强制退回自觉）。

> 一句话：本仓库在 WorkBuddy 里「直接可跑、全机械」；在其他 runtime 里「方法可平移，
> 机械门禁在具备 Python+git 时自动生效，否则降级为读 .md 自觉」。

---

## 必备能力（host runtime 必须满足）

| # | 能力 | 用途 | 缺了会怎样 |
|---|------|------|-----------|
| 1 | **文件读写** | 读 `harness/` 治理母本与 skill 文件；写阶段产物（`prd-work/` `qa-work/` `harness/`）与 `state.json` | 流水线无法落盘产物，断点续跑失效 |
| 2 | **命令执行** | 跑 Python3 脚本（`scope_check.py` / `self_check.py` / `sdlc_status.py`）与 `git` 命令 | 机械门禁失效，退回「AI 读 .md 自觉」 |
| 3 | **子 agent 派发** | `ai-sdlc-master` 的 phase agent 能再派发 step agent（PRD/QA 各派 5 个） | 失去三层上下文隔离；phase agent 内联执行 step（治理机制不变） |
| 4 | **跨 session 持久存储** | `state.json` 落盘在项目 `<根>/.workbuddy/sdlc/`，隔天可续跑 | 每次重新 briefing，断点续跑失效 |
| 5 | **确认闸门交互** | 在决策点打断用户（测试方案确认、G3 低置信上报），不私自推进关键节点 | 关键节点无人确认，可能跑飞 |

## 运行时原语映射

- **WorkBuddy（直接可跑）**：Skill / Agent / 文件工具原语，唯一「全机械」环境。
- **其他 runtime**：用等价原语替代——
  - 加载 skill → 将 `SKILL.md` 注入 system prompt
  - 派发子 agent → 嵌套 agent / 子流程（sub-agent / sub-flow）
  - 确认闸门 → 在决策点 `pause / ask-human`
  - 文件化交接 → 阶段间共享文件系统（同一工作区目录）

## 降级约定（优雅降级，不崩）

- 不支持嵌套派发 → phase agent **内联执行** step（治理机制不变，仅失去上下文隔离）。
- 无 `module-map.yaml` → 护栏2（G2）**降级放行**，仅执行 G1/G3/G5，提示建档。
- 无 `git` → `scope_check.py` **降级放行**（不拦截越界）。
- 无 Python → 所有机械门禁退回「AI 读 .md 自觉」（本仓库默认降级路径，仍可用，只是不强制）。

## 移植步骤（以 Cursor / Claude Code / Codex 为例）

1. 复制 `skills/` 下 14 个 skill 到目标运行时的技能目录。
2. 复制 `harness/` 到项目 `.workbuddy/harness/`（或全局母本 `~/.workbuddy/harness`）。
3. 确保 runtime 提供上表「必备能力」。门禁脚本在**支持 Python≥3.8 + git** 时自动机械生效；
   否则按降级约定退回自觉模式。
4. （可选）安装提交前自动检查：`cp harness/scripts/pre-commit-scope.py <项目>/.git/hooks/pre-commit`
   并 `chmod +x`，越界改动在 `git commit` 时被机械拦截。
