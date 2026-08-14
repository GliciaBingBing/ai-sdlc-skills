# AI 开发治理 Harness（dev-harness 的依赖母本）

本目录是一套架在「需求」与「开发 AI」之间的治理规则（门禁）。任何 AI 编程工具
（Cursor / Claude / Codex / WorkBuddy 等）读到此目录，都应**先读 `guardrails/` 下的 5 份护栏，
遵守门禁**，再开始写码。

## 目录结构
- `guardrails/G1-selfcheck.md` — 护栏1 自检闭环（build/test 通过才报完成）
- `guardrails/G2-scope.md` — 护栏2 范围自检（改动不得超出 module-map 指定模块）
- `guardrails/G3-confidence.md` — 护栏3 置信度上报（看不懂的需求不写，先反馈）
- `guardrails/G4-rollback.md` — 护栏4 一键还原（版本级手动快照，炸了秒回退）
- `guardrails/G5-clean.md` — 护栏5 代码清洁（无死代码/垃圾代码/冗余注释）
- `scripts/self_check.py` / `scope_check.py` / `pre-commit-scope.py` — 护栏1/2 的机械落地脚本（纯标准库）
- `module-map.yaml` / `module-map.md` — 功能→目录 映射（护栏2 依据）；**你只写功能名，AI 读代码库自动补全目录映射**
- `requirement.example.md` — 需求文档**可选**模板（需求你直接给，不必放这）
- `request.schema` — 产物报告字段规范
- `snapshots/` — 版本快照，回退用

## AI 开发前必做
1. 读 `guardrails/` 全部 5 份
2. 拿到**用户给出的需求**（对话里说、或任意位置的文件/文档，AI 直接消费，**不要求**固定在 harness 目录）
3. 读 `module-map.yaml`（拿到本需求允许改动的模块/目录；没有就先让用户列功能模块名，AI 读代码库生成）
4. 按护栏写码，完成后产出 4 份报告，全部通过才报「完成」

> 更省事：直接让 AI 加载 `dev-harness` 技能，它会自动读以上文件并执行门禁。

## 接入新项目
把本目录整体复制到你的项目：`cp -r <本仓库>/harness <项目根>/.workbuddy/harness`
（或全局母本 `~/.workbuddy/harness`，让所有项目共用）。
AI 加载 `dev-harness` 后会自动读项目内的 `.workbuddy/harness/` 并走门禁。
