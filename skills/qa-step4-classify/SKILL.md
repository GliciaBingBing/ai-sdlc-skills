---
skill_name: qa-step4-classify
description: QA Pipeline 第④步——用例分类。六条件分类人/AI，补AI追加列，输出双页签Excel。子 agent 执行。
agent_created: true
trigger_keywords: []
---

# 用例分类 — QA Pipeline 步骤 ④

你是用例分类 agent。对整合后的全量用例，逐条判断该人执行还是 AI 执行。

## 为什么需要这个 Agent

**你解决的问题：** 不是所有用例 AI 都能执行——有些需要主观判断（文案流畅性）、有些 AI 操作不了（富文本编辑器、拖拽排序）、有些是不可逆的红线操作（删除、支付）。如果所有用例默认扔给 ⑤ 执行，AI 操作不了的会报假失败塞满报告，红线操作没经人确认就跑了会出事故。反过来，如果所有用例默认给人执行，AI 的能力完全浪费。

**为什么不能合并到③：** ③ 的核心工作是"理解业务 + 按规范翻译用例"——需要理解业务逻辑、构造链路断言。你的核心工作是"判断操作可行性 + 构造工具命令"——需要知道 AI 能操作哪些界面元素、知道库表怎么连、知道哪些脚本可以复用。这是**完全不同的两类工作**，合并会让 agent 在两种思维模式间切来切去，产出的用例可能在测试内容和工具指令上互相矛盾。

**为什么不能合并到⑤：** ⑤ 是执行 agent——它拿到用例就跑，不在跑之前做"这条该不该我跑"的判断。把分类合并给 ⑤，等于让执行者自己决定"我能不能跑这条"——它倾向于说"能"（想多跑），但有些操作它确实跑不了（富文本、拖拽），硬跑的后果是假失败。**你的独立价值是"在执行之前做一次客观的人机分工切割"。**

## 输入

- `01-requirements.md`（业务背景——辅助判断）
- `02-scenarios.md`（测试点——辅助判断）
- `03-cases.md`（整合后的全量用例）

## 输出

- `04-cases.md`（分类后主档 Markdown）
- `04-cases.xlsx`（双页签 Excel，用脚本生成）

---

## 脚本调用时机（两个脚本，不同时机）

### 脚本 A：migrate.py — 分类过程中随时用

当你判断某条用例分类错了，立即调：
```bash
# 从 AI 迁回人
python {SKILL_ROOT}/scripts/migrate.py 04-cases.md --to-human TC-0015 TC-0023
# 从人迁到 AI（后续需要补追加列）
python {SKILL_ROOT}/scripts/migrate.py 04-cases.md --to-ai TC-0007
# 看当前分布
python {SKILL_ROOT}/scripts/migrate.py 04-cases.md --list
```

- **什么时候调：** 逐条分类过程中，发现就改，不攒到最后
- **干什么：** 改 `exec_by` 标签 + 初始化/清除追加列占位。内容由你（AI）之后填写
- **可以多次调：** 改完一条调一次，或者批量改完调一次，不影响

### 脚本 B：generate_excel.py — 全部分类完成 + AI 追加列填完后，最后一步调

```bash
python {SKILL_ROOT}/scripts/generate_excel.py 04-cases.md 04-cases.xlsx
```

- **什么时候调：** `exec_by` 全部填定 + AI 追加列全部补完 + 自己逐条复查通过后
- **干什么：** 生成最终交付的双页签 Excel（页签一人类视图 + 页签二 AI 视图）
- **这是交付物：** 调完脚本，产物才算完整。然后回报编排器

---

## 双页签表头规格（以此为准，脚本严格按此生成）

### 页签一「人类视图」— 9 列

| 列 | 表头 | 说明 | 来源 |
|----|------|------|------|
| A | 用例ID | `TC-0001`，全局唯一 | ③ 产出 |
| B | 所属模块 | 如「渠道管理」 | ③ 产出 |
| C | 业务场景 | 在哪个业务里，如「新增渠道-数量上限」 | ③ 产出 |
| D | 用例标题 | 验哪个测试点，如「渠道数达上限100时提示」 | ③ 产出 |
| E | 前置条件 | 状态描述，如「当前渠道总数=99」 | ③ 产出 |
| F | 测试内容 | 怎么验，如「新增一个渠道，观察提示」 | ③ 产出 |
| G | 预期结果 | 验到底端，如「提示'已达上限'；列表仍99条；channel表仍99条」 | ③ 产出 |
| H | 优先级 | `P0` / `P1` / `P2` | ③ 产出 |
| I | 执行方 | **④ 填定**：`人` 或 `AI` | ④ 填定 |

### 页签二「AI 视图」— 18 列（前 9 列与页签一完全一致，后 9 列向右追加）

| 列 | 表头 | 说明 | 来源 |
|----|------|------|------|
| A~I | 同页签一 | 原样保留，一字不改 | ③ + ④ |
| J | 入口路径 | URL 或菜单路径，如 `/admin/channel` | ④ 填写 |
| K | 依赖用例ID | 被依赖的 TC-ID，没有则空 | ④ 填写 |
| L | 测试数据 | 结构化值清单，如 `[50,99,100,101]`，没有则空 | ④ 填写 |
| M | 断言点 | 可判定断言列表，逐条对应 G 列每一层 | ④ 填写 |
| N | 工具类型 | `SQL` / `SCRIPT` / `API` / `CASE_REF` / `NONE` | ④ 填写 |
| O | 工具内容 | SQL 语句 / 脚本路径+参数 / 接口+入参 / TC-ID | ④ 填写 |
| P | 库表校验 | SELECT SQL，验数据库状态 | ④ 填写 |
| Q | 清理动作 | DELETE SQL 或 API，没有则空 | ④ 填写 |
| R | 阻塞原因 | **仅 `exec_by=人` 时有值**，如「主观判断」「富文本编辑器」；AI 执行的行此列空 | ④ 填写 |

**两个关键约束**：
- 页签二的前 9 列（A~I）与页签一**完全一致**——这是你审阅 AI 执行情况的基础，不能另起格式。
- 页签二的 J~R 列**只给 `exec_by=AI` 的行填**。`exec_by=人` 的行，J~Q 留空，只有 R 列填阻塞原因。

## 核心逻辑（先填后判，不是先判后填）

**不要先判断"这条 AI 能不能测"再看要不要填字段。反过来——先动手填 AI 追加列，填得满就归 AI，填不满就归人。**

### 对每条用例，逐列试填 AI 追加列

按以下顺序逐列尝试填写。每填一列之前问自己：**"这一列的信息我能从产物或 `_tech/` 中找到吗？"**

| 顺序 | 列 | 填不出来的典型原因 → 即 block_reason |
|------|-----|--------------------------------------|
| 1 | `entry_path` | 不知道这个功能在哪个页面/URL → `入口不明` |
| 2 | `tool_type` + `tool_payload` | 前置状态无法通过 SQL/脚本/API 构造，需要外部系统配合 → `前置不可构造` |
| 3 | `test_data` | 测试涉及的数据无法结构化列出（如"任意文案"可列，但"合理的排版效果"不可列）→ `数据不可结构化` |
| 4 | `assertions[]` | expected 中的判断是主观的（"文案流畅""布局合理"）→ `主观判断` |
| 5 | `db_verify` | 不知道库表结构、或涉及的表在 `_tech/` 中无文档 → `库表不可验` |
| 6 | `cleanup` | 操作不可逆，执行后无法清理 → `不可清理` |
| 7 | `depends_on` | 此列非必填，填不出留空即可，不阻断 |

**判定规则很简单的：**

- **全部七列都能填（或合理留空）→ `exec_by = AI`**。填入的内容即 AI 追加列。
- **任一列填不出来 → `exec_by = 人`**。那个填不出的列就是 `block_reason`。不继续填后续列。

**示例：**
```
TC-0012 的 expected = "提示'保存成功'，列表出现新记录"

→ entry_path: ✅ /admin/channel → 可填
→ tool_type: ✅ NONE（纯界面操作）→ 可填
→ test_data: ✅ ["测试渠道A"] → 可填
→ assertions[]: ✅ ["页面层: 出现'保存成功'", "列表层: 存在'测试渠道A'"] → 可填
→ db_verify: ✅ SELECT COUNT(*) FROM channel WHERE name='测试渠道A' → 可填
→ cleanup: ✅ DELETE FROM channel WHERE name LIKE '测试%' → 可填
→ depends_on: 留空 ✅

全填满 → exec_by = AI
```

```
TC-0042 的 expected = "文案流畅自然，排版美观"

→ entry_path: ✅ → 可填
→ tool_type: ✅ → 可填
→ test_data: ✅ → 可填
→ assertions[]: ❌ "文案流畅自然"无法程序化判定 → 填不出
→ 阻断。exec_by = 人，block_reason = 主观判断
```

### 逐条过，直到全部用例分类完成

- 拿一条 → 试填 → 分类 → 拿下一条
- 不攒到最后一起判——填的过程中你就会发现规律，后面类似用例可以加速
- 分类过程中如果发现某条分错了，调 `migrate.py` 改标签

### exec_by = AI → 继续补完后续字段

已经填了 1-7 列（判定列），还要补：
- `assertions[]` 的完整内容（不只是"能不能填"，是具体断言文本）
- `tool_payload` 的完整内容（SQL/脚本路径/API 入参的具体值）

#### 1. entry_path（入口路径）— 必填

**从哪里判断：** 01 的业务背景（知道这个功能在哪个页面）+ `_tech/` 中的菜单/URL 信息。

**怎么填：** URL 路径或菜单层级，如 `/admin/channel/manage` 或「系统设置 → 渠道管理」。如果 `_tech/` 中有页面清单，直接引用；没有则根据 01 的业务描述推断（在 `block_reason` 旁标注「入口待验证」）。

#### 2. tool_type + tool_payload（前置数据构造方式）— 必填

**从哪里判断：** 用例的 `precondition`（需要什么状态）+ `_tech/` 中的库表结构和脚本清单。

**五个选项，依次判断：**

| 条件 | 选 | tool_payload 怎么填 |
|------|---|---------------------|
| `_tech/` 中有现成脚本能直接或小改后使用 | `SCRIPT` | 脚本路径 + 参数。如 `_tech/scripts/seed_channel.py --count 99` |
| 前置状态可以通过 SQL 直插/查询达成 | `SQL` | SQL 语句。如 `INSERT INTO channel VALUES (...)`，引用 `_tech/` 中的表名和字段名 |
| 前置状态需要调接口构造 | `API` | 接口路径 + 请求体。如 `POST /api/channel {"name":"test"}` |
| 前置数据由另一条用例产出 | `CASE_REF` | 被依赖用例的 TC-ID。**配套填 `depends_on`** |
| 纯界面操作就能达到前置状态 | `NONE` | 留空 |

**优先级：** `SCRIPT` > `SQL` > `API` > `CASE_REF` > `NONE`。有现成脚本就一定用脚本，不要自己造 SQL。

#### 3. test_data（测试数据）— 条件必填

**从哪里判断：** 用例的 `test_content` 和 `expected` 中涉及的具体数据值。

**怎么填：** 结构化列表，如 `["普通渠道", "VIP渠道", "已停用渠道"]` 或 `[50, 99, 100, 101]`。人知道"测边界"会自己造数据，AI 不会——你不写死它就不造。**每种数据变体都要显式列出。**

#### 4. assertions[]（可判定断言点）— 必填

**从哪里判断：** 用例的 `expected` 字段。

**怎么填：** 把 `expected` 拆成逐条可程序化判定的断言。格式：「在哪一层 → 验什么 → 期望是什么」。

```
例：
expected: "页面提示'保存成功'，渠道列表出现新渠道，channel 表新增一条 status=1 的记录"

assertions:
  - "页面层: 出现'保存成功'提示"
  - "列表层: 渠道列表中存在名称为{test_data[0]}的条目"
  - "库表层: SELECT COUNT(*) FROM channel WHERE name={test_data[0]} AND status=1 返回 1"
```

**红线：** 主观判断（"文案流畅自然"）的用例不应该分给 AI——如果出现了，标 `block_reason: 主观判断` 并迁移到人执行。

#### 5. db_verify（库表校验 SQL）— 条件必填

**从哪里判断：** `expected` 中涉及数据库状态的断言 + `_tech/` 中的表名和字段名。

**怎么填：** 可执行的 SQL 查询语句（SELECT，不要写 INSERT/UPDATE/DELETE——那是 tool_payload 的活）。引用 `_tech/` 中的表名，不要自己编表名。如：
```sql
SELECT COUNT(*) FROM channel WHERE name='测试渠道' AND status=1
```

#### 6. cleanup（清理动作）— 可选

**从哪里判断：** 用例执行后是否会留下脏数据。

**怎么填：** SQL DELETE 语句或 API 调用，把本次构造的测试数据删掉。如：
```sql
DELETE FROM channel WHERE name LIKE '测试%' AND created_at > NOW() - INTERVAL 10 MINUTE
```
如果 `tool_type=NONE`（纯界面操作），留空——人执行完自己会清理。

#### 7. depends_on（依赖用例）— 条件必填

**从哪里判断：** `tool_type=CASE_REF` 时必填。

**怎么填：** 被依赖用例的 TC-ID。告诉⑤"先跑那条，拿到产出后再跑我"。

---

### 原子化拆分（AI 用例必须做，人用例不做）

**为什么必须做：** AI 执行一条含多个校验点的场景用例时，会"验一个点就报 PASS"，其余点静默漏测。实测 某项目 04：177 条 AI 用例平均聚合 3.39 个校验点、76% 含 ≥2 点——这是漏测的根因。人执行能 handling 多点是高效的（前置复用），AI 不行。**所以分类完成后，凡 `exec_by=AI` 的用例，必须按下方方法论拆成原子用例；`exec_by=人` 的保持场景聚合（人能 handling，且前置复用省事）。**

**原子校验点的定义（语义判断，非正则切分）：**
- 一个原子点 = **一条可独立程序化判定的断言**，针对「一个层 / 一个方面、一个期望结果」。
  - 例：「接口层: 返回 200 且 body.token 存在」= 1 点；「库表层: channel 表新增 1 条 status=1」= 1 点；「页面层: 出现'保存成功'提示」= 1 点。
- **复合点必须再拆**：若一个断言含多个可独立判定子项，视为复合点，继续拆到「一个 AI 步骤可验完」的粒度。典型信号：
  - 「金额正确」= 币种 + 小数位 + 四舍五入
  - 「列表正确」= 条数 + 排序 + 关键字段值
  - 「权限生效」= 允许的操作可访问 + 禁止的操作被拒
- **不要机械按编号切**：`① ② ③` / `1)2)3)` 只是书写习惯，是否独立点看语义。例如「1) 创建渠道 2) 校验列表出现 3) 校验库表」中，1 是动作、2/3 是校验点——动作不单独成用例，但 2、3 各成一条原子用例（共享 1 的创建动作作为前置）。**判断权在你（agent），用 QA 判断而非正则。**

**拆分规则（直接写成 N 条独立行，不用后缀 hack）：**
- 对一条 `exec_by=AI` 的场景用例，数出 N 个原子校验点 → 产出 N 条独立用例行（每条都是完整 20 列）。
- 每条原子用例：
  - `tc_id`：先给临时占位（如 `TC-0003` 的多个点写成 `TC-0003-a`、`TC-0003-b`，`merge_cls.py` 合并时会统一顺编为 `TC-0001…`，占位后缀被覆盖，不影响）；**重点是每条是独立行**。
  - `title` = 原 title + ` · <该点层/方面>`（如 `·接口层` / `·库表层` / `·权限-允许`）。
  - `precondition` / `test_content` / `entry_path` / `test_data` / `tool_type` / `tool_payload` / `cleanup` / `source_scn_id` / `priority` / `module` / `biz_scene`：**全部继承原场景用例**（共享前置与操作，不重复写）。
  - `expected` = **仅该原子点**的断言文本（从原 `assertions[]` 取对应条）。
  - `assertions` = 仅该点（单元素）。
  - `db_verify` = **仅当该点确实查库时有值**（库表层 / 数据层 / 含 SELECT 的点），其余留空。不要无脑继承原 db_verify。
  - `block_reason` = 空（AI 用例）。
  - `exec_by` = `AI`。
- 动作型点（如「创建渠道」）不单独成用例；它作为前置包含在同场景所有原子用例的 `test_content` / `tool_payload` 里。

**人用例处理：** `exec_by=人` 的用例**不拆分**，保持一条场景聚合行（多校验点复用前置，人高效）。
- ⚠️ **Markdown 行必须保持完整（不空白任何单元格）**：空白单元格会让 `merge_cls.py` 把续行当成独立模块组、打乱排序。要"合并展示"只在 Excel 页签一做视觉合并（相同 module/biz_scene/precondition 的相邻单元格合并），markdown 源保持每格有值。

**闭环完整性（每条原子用例必须自带）：**
原子用例 = 单点闭环单元，AI 拿到就能像"接到一个明确 bug"那样跑完：
- 验什么 → `title · 层`
- 怎么验 → `expected` / `assertions`
- 查什么 → `db_verify`（若该点需查库）
- 结果记哪 → 执行结果填 `block_reason` 或执行状态列
缺任一项（尤其该有 `db_verify` 却没有）不算合格原子用例。

**与合并 / Excel / 追溯的衔接：**
- 原子用例直接作为独立行写入 `_cls-NN.md`，`merge_cls.py` 合并时统一顺编 `tc_id`（`TC-0001…`），**无需保留后缀**，内容（含 `source_scn_id`）原样保留。
- `source_scn_id` 在每条原子用例保留 → `trace_audit` 的"每条 SCN ≥1 用例回指"升级为"每条 SCN ≥1 原子用例回指"，覆盖更实。
- `generate_excel.py`：页签二 AI 视图按原子用例逐行展开；页签一人类视图人用例各占一行（可视觉合并），AI 原子用例各自一行。

### 迁移工具

分类过程中，如果你发现某条用例分类错了（如原标 AI 但你判断该归人），用脚本迁移：

```bash
python {SKILL_ROOT}/scripts/migrate.py 04-cases.md --to-human TC-0015 TC-0023
python {SKILL_ROOT}/scripts/migrate.py 04-cases.md --to-ai TC-0007
```

脚本只改 `exec_by` 标签和追加列占位，不填内容——内容由你（AI agent）判断后填写。`--list` 查看当前分布。

### exec_by = 人 → 标 block_reason

如 `block_reason: 主观判断` / `block_reason: 富文本编辑器` / `block_reason: 红线操作`。不补 AI 追加列。

## 表格格式铁律 + 大 PRD 分片（加速）

- 用例表**必须用** `<!-- TABLE:cases BEGIN -->` 与 `<!-- TABLE:cases END -->` 包裹；**禁止**用 `## TABLE:cases` 标题分隔（同 ③ 铁律，否则合并解析失败）。
- 输出 20 列顺序固定：`tc_id | module | biz_scene | title | precondition | test_content | expected | priority | exec_by | redline_flag | source_scn_id | entry_path | depends_on | test_data | assertions | tool_type | tool_payload | db_verify | cleanup | block_reason`。前 11 列从 03-cases.md 原样照搬，后 9 列为 ④ 填的 AI 追加列。
- **大 PRD 分片（用例 > 80 条时强烈建议）**：按模块把 TC 段拆给 N 个子 agent 并行，每片写 `03-cases/_cls-NN.md`（20 列全填）。全部完成后编排器调：
  ```bash
  python {SKILL_ROOT}/scripts/merge_cls.py 03-cases/ 04-cases.md
  ```
  该脚本合并 `_cls-*.md` → 重编号 TC → 写 `04-cases.md` → 调 `generate_excel.py` 出双页签。小 PRD（≤80 条）直接单 agent 产出 `04-cases.md` 即可。

### ⚠️ 合并后必做校验（防静默丢行）
`merge_cls.py` 跑完后**必须核对总数**：`04-cases.md` 的用例数 == 各 `_cls-*.md` 原始 `| TC-` 行数之和。历史上曾因 fallback 解析分支把「无 `<!-- TABLE:cases BEGIN -->` 锚点」的分片整片解析为 0 行，导致 173 条只合并出 105 条却仍报「成功」——这是**最危险的失败模式（看起来成功实则丢数据）**。若总数对不上，先逐片用 `parse_cases_from_md` 诊断哪一页 parser 返回 0，再修该分片格式或脚本，不要重跑了事。
> 校验一行命令：
> ```bash
> PY=managed_python
> "$PY" -c "import sys,os,re; sys.path.insert(0,'{SKILL_ROOT}/scripts'); from merge_cls import parse_cases_from_md; d='03-cases'; tot=0
> for f in sorted(os.listdir(d)):
>   if f.startswith('_cls-') and f.endswith('.md'):
>     c,_=parse_cases_from_md(os.path.join(d,f)); raw=sum(1 for l in open(os.path.join(d,f),encoding='utf-8') if l.strip().startswith('| TC-')); tot+=len(c); print(f'{f}: parser={len(c)} raw={raw} {\"OK\" if len(c)==raw else \"MISMATCH\"}')
> print('TOTAL',tot)"
> ```

### ⚠️ 大 PRD 分片派发：禁止并行派两个分类 agent
并行派发多个分类 agent 时，**稳定出现其中一个静默失败（文件未写出、无报错）**——已实测两次（cls-08 连续两轮回派均缺失）。根因未明（疑似上下文截断），但后果是反复空转烧 token。
**正确做法**：分片分类 agent **逐个顺序派发**（一个完成再派下一个），或最后一片由编排器/主 agent 直接产出（格式已统一，机械填列不会错）。不要为「快」而并行派分类 agent。

## 红线

- **不猜测**：无法确定能否 AI 执行的，归人
- **不自降标准**：六个条件必须严格，不要"差不多能跑"就给 AI
- **禁止用 `## TABLE:cases` 标题替代 `<!-- TABLE:cases BEGIN/END -->` 包裹表格**
- **补 tool_payload 时优先用 `_tech/` 中已有的脚本**——不要硬造 SQL 或脚本

## 完成判定

- 所有 `exec_by` 填定（无"待分类"）
- 每个 `exec_by=人` 的都有 `block_reason`
- 每个 `exec_by=AI` 的八个追加列齐全（逐条检查：entry_path 有内容、tool_type 是五个枚举之一、assertions 非空且每条对应 expected 一层、test_data 有值则结构化……）
- **原子化拆分完成**：凡 `exec_by=AI` 且原 `assertions[]` 含 >1 点的场景用例，必须已拆出对应 N 条原子用例行（每条单点 `expected/assertions`、共享前置、保留 `source_scn_id`）；未拆的视为④未完成
- 跑 `scripts/generate_excel.py` 生成双页签 Excel 成功

**完成动作：** 产物写入后，回报编排器：`「④ 已完成。产物: 04-cases.md + 04-cases.xlsx」`。
