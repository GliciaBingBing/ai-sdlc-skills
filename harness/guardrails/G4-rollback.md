# 护栏4 · 一键还原（Rollback Gate）

## 规则
- 回退粒度为**版本级目录快照**：在重要节点用 `harness/scripts/snapshot.py` 自动存一份工作区副本。
- 上轮产出有问题（缺陷/越界/读不懂）→ 触发 `harness/scripts/rollback.py` 回退到上一快照，在干净基线重新派发。
- 回退**不丢失**已迭代成果：原快照保留，可随时切回（`rollback.py --list` 查看全部）。

## 机械执行（替代手动复制）
- 存盘：`python harness/scripts/snapshot.py <项目根> [--label 备注]`
  → 在 `.workbuddy/harness/snapshots/<id>/` 生成版本级副本（排除 .git / node_modules / 缓存 / 快照自身），并写 `manifest.json`（含快照 id、时间、git commit、文件数）。
- 还原：`python harness/scripts/rollback.py <项目根>`（回退最新） / `--to <id>`（指定） / `--dry-run`（预演） / `--list`（列出）。
- 快照**独立于 git 历史**，不污染提交、不自动建 commit。

## 边界
- 无快照可回退 → 脚本提示「请先存储快照」，不执行回退（`exit(1)`）。
- 回退只还原快照内文件；工作区中「快照没有」的文件**保留不删**（安全），仅报告改写冲突项。
- AI 不擅自回退：由用户在「这轮炸了」时显式触发脚本。
- 运行期生成的快照目录（`snapshots/*`）已被 `.gitignore` 排除，不会误提交进仓库。
