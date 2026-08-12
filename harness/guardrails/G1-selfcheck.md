# 护栏1 · 自检闭环（Self-Check Gate）

## 规则
- 写完代码，**必须先自己 build + 跑测试**，全部通过，才允许向用户报「完成」。
- build 或 test 失败 → 自行继续修复，直到通过；**不得**把未通过的代码报成完成。
- 配合 护栏5 做代码清洁检查（code_clean=true 才允许报完成）。

## 完成态硬性条件（缺一不可）
1. build 成功
2. 相关测试通过（无失败项）
3. code_clean = true（无死代码/冗余注释/垃圾代码）

## 产出
向用户提交 `self_check_report`：
- `status`: pass / fail
- `build_result`: 通过项
- `test_result`: 通过项
- `failed`: 失败项列表（status=fail 时必填）
- `code_clean`: true / false

## 禁止
- 禁止「我觉得写完了」就报完成而不跑验证。
- 禁止跳过测试。
- 禁止靠用户跑起来才发现报错。
