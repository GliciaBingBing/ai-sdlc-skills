# 护栏2 · 改动范围自检（Scope Gate）

## 规则
- 改动范围**不得超出** requirement.md 中该需求所指定模块，在 module-map.yaml 中对应的目录。
- 写码后比对 `changed_files` 与 module-map；凡落在需求模块目录之外的文件 → 视为越界。
- 越界改动**自动拦截，不提交**，也**不向用户报文件级 diff**（用户看不懂代码）。

## 流程
1. 开工前从 requirement.md 取出本需求的 module_id（或明确的范围描述）。
2. 从 module-map.yaml 取出该模块对应的目录集合。
3. 写码后列出 changed_files。
4. 任一文件不在允许目录集合内 → out_of_scope 非空 → blocked=true → 不提交，
   提示用户确认范围或更新地图。

## 产出
向用户提交 `diff_scope_report`：
- `changed_files`: 本次改动文件
- `mapped_modules`: 命中的模块
- `out_of_scope`: 越界文件列表
- `blocked`: true / false

## 边界
- module-map 缺失 → 护栏2 不生效，降级提示「请先建档 module-map」，仅执行护栏1/3/5。
- 需求未指定模块 → 视为需先补地图映射，不擅自全仓库改。
