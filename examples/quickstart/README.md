# 一眼看懂 · 完整跑通示例

这个目录让你**不读一堆文档**，直接看懂这套「需求 → 开发 → 测试」AI 原生交付流水线
到底产出什么。下面是从「一句话需求」到「三段产物」的真实流程缩略版。

> 这是示意性精简样本（字段、命名与真实运行一致），用于展示产物长什么样。
> 真实运行由 `ai-sdlc-master` 编排器自动串起 PRD → Dev → QA 三段。

---

## 流程一句话

```
你（一句话）：「给账号管理加一个「忘记密码」入口，用户能走邮件重置」
   │  ai-sdlc-master 顶层编排器
   ▼
┌─ PRD phase ──────┐  产出 04-prd.md（需求被拆成可验收的用户故事）
├─ DEV phase ──────┤  产出 代码 + 4 份门禁报告（self_check / diff_scope / pending / artifact_binding）
├─ QA phase ───────┤  产出 用例表 + 人/AI 分工 + 05-results 执行结果
└──────────────────┘
   全程文件化交接 + 项目级 state.json 记忆 → 隔天回来说「继续」可从断点续跑
```

---

## 各段产物长什么样

### ① 输入（你的一句话）
见 [`00-input-requirement.md`](00-input-requirement.md)

### ② PRD 段 → `04-prd.md`（节选）
见 [`prd/04-prd.excerpt.md`](prd/04-prd.excerpt.md)
- 把模糊需求拆成：用户故事 + 验收标准 + 范围边界
- 标了 `module: MOD-001`（账号管理）→ 下游开发段据此限范围

### ③ DEV 段 → 4 份门禁报告（节选 `diff_scope_report`）
见 [`dev/diff_scope_report.json`](dev/diff_scope_report.json)
- **G1 自检闭环**：`self_check.py` 跑 build+test，全过才 pass
- **G2 范围自检**：`scope_check.py` 比对改动目录 ⊆ module-map，`blocked=false` 才提交
- **G3 置信度**：看不懂的需求列 `pending_requirements` 反馈，不私自写
- **G4 一键还原**：重要节点存快照，炸了回退
- **G5 代码清洁**：无死代码/冗余注释

### ④ QA 段 → 用例 + 执行结果（节选）
见 [`qa/05-results.excerpt.md`](qa/05-results.excerpt.md)
- 用例按「人 / AI」分工（人审判断类，AI 跑确定性）
- `trace_audit` 逐条比对需求是否被用例回指，漏测即拦截

---

## 机械门禁在哪（为什么不是「靠自觉」）

| 段 | 机械强制点 | 实现 |
|----|-----------|------|
| PRD→Dev 交接 | 无 `04-prd.md` confirmed，不进 Dev | `sdlc_status.py` 状态机 exit 拦截 |
| Dev G1 | build/test 不过 → 拦截报完成 | `self_check.py` exit 1 |
| Dev G2 | 越界改动 → 拦截提交 | `scope_check.py` exit 1（可挂 git pre-commit 自动拦） |
| QA | 上游未 confirmed → 拒绝执行 | `gate_check.py` exit 1 |
| 全链 | 隔天续跑不断点 | `state.json` 持久记忆 |

要亲手试，回到仓库根目录 README 的「怎么用」一节。
