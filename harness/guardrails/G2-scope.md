# 护栏2 · 改动范围自检（Scope Gate）+ 申诉通道

> **机械落地**：`harness/scripts/scope_check.py` 是本护栏的可执行版——读 `module-map.yaml`
> 拿允许目录，比对本次 `git` 改动，越界即拦截。但**不再一刀切**：越界文件会按影响层
> 自动分级，并给出申诉通道（`harness/appeal_log.yaml`），已签字的例外放行，未签字的才
> 真拦截。可挂成 git pre-commit 钩子（`pre-commit-scope.py`）实现「提交前自动检查」。
> 优先调脚本；无 map / 无 git / 无 Python 时退回本 .md 自觉执行（降级放行）。

## 规则
- 改动范围**不得超出** requirement.md 中该需求所指定模块，在 module-map.yaml 中对应的目录。
- 写码后比对 `changed_files` 与 module-map；凡落在需求模块目录之外的文件 → 视为越界。
- 越界文件**不再一律拦截**，而是进入申诉通道（见下），按影响层分级处置。

## 影响层分级（脚本按路径自动探测，人工可在 appeal_log 覆盖）
- **UI 层**：展示型文件（.tsx/.jsx/.vue/.css/...）。越界风险低 → **人审放行**。
- **配置**：配置型文件（.yaml/.yml/.env/...）。越界风险低 → **人审放行**。
- **函数依赖**：逻辑型文件（.py/.ts/.go/...）。其中命中 `shared/common/lib/utils/core`
  路径的标为「跨模块共享」，风险最高 → **强制 sign-off**（须人工显式签字）。

> 分级是「确定性逻辑下沉脚本」的体现：层别由路径启发式机械判定；但「该层要不要放行」
> 这类易变判断交人工签字，不靠 AI 自觉。

## 申诉通道（appeal_log.yaml）
越界文件报为 `appeal_needed`，你（人）在 `harness/appeal_log.yaml` 的 `appeals:` 下补一条
并签字，重跑 `scope_check.py` 即通过（计入 `appealed_ok`，不再 blocked）。

条目字段：
- `file`：越界文件 repo 相对路径（须与脚本报出的一致）
- `layer`：UI 层 / 函数依赖 / 配置（可覆盖自动探测）
- `impact_scope`：**一句话说明影响范围**（必填；为空视为申诉未完成，仍拦截）
- `approved_by`：human / ai-reviewed（必填；**函数依赖须 human 显式签字**，AI 自签无效）
- `approved_at`：YYYY-MM-DD

## 流程
1. 开工前从 requirement.md 取出本需求的 module_id（或明确的范围描述）。
2. 从 module-map.yaml 取出该模块对应的目录集合。
3. 写码后列出 changed_files。
4. 任一文件不在允许目录集合内 → 标记越界：
   - 该文件已在 appeal_log 签字（impact_scope + approved_by 齐全）→ `appealed_ok`，放行；
   - 否则 → `appeal_needed`，附自动探测的层别与处置要求，**exit(1) 拦提交**，
     并打印可直接粘贴的申诉模板，提示你补签字。

## 产出
向用户提交 `diff_scope_report`：
- `changed_files`: 本次改动文件
- `mapped_modules`: 命中的模块
- `out_of_scope`: 越界文件列表
- `appeal_needed`: 待申诉清单（含 `file` / `layer` / `shared` / `required_action`）
- `appealed_ok`: 已签字放行的越界文件（含 `file` / `layer` / `approved_by` / `approved_at`）
- `blocked`: true / false（仅当存在未签字申诉时为 true）

## 边界
- module-map 缺失 → 护栏2 不生效，降级提示「请先建档 module-map」，仅执行护栏1/3/5。
- 需求未指定模块 → 视为需先补地图映射，不擅自全仓库改。
- 申诉是「分级处置」不是「免检」：函数依赖 / 跨模块共享必须 human 签字，AI 不得在
  appeal_log 自签放行（属违反治理，验收时核查）。
