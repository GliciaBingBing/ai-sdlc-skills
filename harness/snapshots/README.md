# 版本快照（护栏4）

由 `harness/scripts/snapshot.py` / `rollback.py` **机械执行**（替代手动复制）。

用法：
- 存盘：你觉得「这一轮稳了」时，运行 `snapshot.py <项目根>` 存一份版本级目录副本到 `snapshots/<id>/`。
- 回退：上轮写炸了 → 运行 `rollback.py <项目根>` 一键还原到最新快照（或 `--to <id>` 指定）；原快照保留，可随时切回。
- 列出：`rollback.py <项目根> --list`；预演：`--dry-run`。

快照特性：
- **独立于 git 历史**：副本不污染提交、不自动建 commit。
- 存盘时记录 `manifest.json`（快照 id / 时间 / git commit / 文件数）。
- 自动排除 `.git`、`node_modules`、缓存目录、快照自身，避免无限膨胀。

> 回退由用户主动触发；AI 不擅自回退，也不擅自删除快照。
> 运行时生成的 `snapshots/*` 已被仓库 `.gitignore` 排除，不会误提交。
