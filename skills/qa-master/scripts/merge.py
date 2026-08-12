"""
qa-master 用例合并去重脚本

用法：
  python merge.py <03-cases-dir> <output_md_path> [--auto]

功能：
1. 读取 03-cases/ 下所有 _shard-NN.md
2. 抽取 TABLE:cases，统一编号
3. 执行规则③（同 biz_scene + 同 title → 合并 test_data）
4. 执行规则④（继承 source_scn_id）
5. 标记规则①②候选（需 AI 判断的断言重叠对）
6. 写 03-cases.md + _merge-log.md

规则：
  ① 断言包含即删 — 标记候选，AI 判
  ② 部分重叠砍重叠 — 标记候选，AI 判
  ③ 同场景同测试点不同数据并一条 — 脚本自动
  ④ 合并继承回指 — 脚本自动
  ⑤ 删除留痕 — 脚本自动写 _merge-log.md

--auto：自动执行规则①②（子串匹配），不标候选
"""

import re
import sys
import json
import os
from datetime import datetime
from collections import defaultdict

MERGE_LOG_HEADER = """# 合并去重日志
generated_at: {timestamp}
shards: {shard_list}

"""


def gate_guard(gate_key, md_path):
    """前置闸门：frontmatter 中 gate_2/gate_3 状态位须为 confirmed 才允许运行。
    防止编排器跳过「用户确认」直接跑后续步骤（SKILL.md「产物状态位契约」）。"""
    if not os.path.exists(md_path):
        print(f"🚫 gate 拦截 [{gate_key}]: 产物不存在 {md_path}", file=sys.stderr)
        sys.exit(1)
    with open(md_path, "r", encoding="utf-8") as f:
        head = f.read(2048)
    m = re.search(r"^---\s*\n(.*?)\n---", head, re.DOTALL)
    if not m:
        print(f"🚫 gate 拦截 [{gate_key}]: {os.path.basename(md_path)} 缺少 frontmatter", file=sys.stderr)
        sys.exit(1)
    value = ""
    for line in m.group(1).split("\n"):
        if line.strip().startswith(gate_key + ":"):
            value = line.split(":", 1)[1].strip()
            break
    if value != "confirmed":
        print(f"🚫 gate 拦截 [{gate_key}]: {os.path.basename(md_path)} 状态位 = {value!r}，须为 confirmed", file=sys.stderr)
        print("   说明: 上游产物尚未经用户确认。先展示产物 → 用户确认 → 回写 gate_N: confirmed 再重跑本脚本。", file=sys.stderr)
        sys.exit(1)


def parse_cases_from_md(filepath):
    """从 Markdown 文件解析 TABLE:cases"""
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    match = re.search(
        r"<!-- TABLE:cases BEGIN -->(.*?)<!-- TABLE:cases END -->",
        content, re.DOTALL
    )
    if not match:
        match = re.search(
            r"\| tc_id \|.*?\n\|[-| ]+\|\n((?:\|.*\|\n)+)",
            content
        )
    if not match:
        return [], None

    table_text = match.group(1) if match.lastindex == 1 else match.group(1)
    lines = [l for l in table_text.strip().split("\n") if l.strip().startswith("|")]
    if len(lines) < 2:
        return [], None

    headers = [h.strip() for h in lines[0].strip("|").split("|")]
    cases = []
    for line in lines[1:]:
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 5:
            continue
        case = {headers[i]: cells[i] for i in range(min(len(headers), len(cells)))}
        if case.get("tc_id"):
            cases.append(case)
    return cases, headers


def merge_rule3(cases):
    """规则③：同 biz_scene + 同 title 不同数据 → 并成一条"""
    groups = defaultdict(list)
    for c in cases:
        key = (c.get("biz_scene", ""), c.get("title", ""))
        groups[key].append(c)

    merged = []
    log_entries = []

    for key, group in groups.items():
        if len(group) == 1:
            merged.append(group[0])
            continue

        survivor = group[0]
        victims = group[1:]

        # 合并 test_data
        all_data = set()
        for c in group:
            td = c.get("test_data", "").strip()
            if td:
                all_data.add(td)
        if all_data:
            survivor["test_data"] = ", ".join(sorted(all_data))

        # 合并 source_scn_id
        all_scn = set()
        for c in group:
            sid = c.get("source_scn_id", "").strip()
            if sid:
                for s in sid.split(","):
                    all_scn.add(s.strip())
        survivor["source_scn_id"] = ", ".join(sorted(all_scn))

        # 合并 merged_from
        mf = set(survivor.get("merged_from", "").split(","))
        for v in victims:
            mf.add(v["tc_id"])
            of = v.get("merged_from", "")
            if of:
                for x in of.split(","):
                    mf.add(x.strip())
        survivor["merged_from"] = ", ".join(f for f in sorted(mf) if f)

        merged.append(survivor)
        log_entries.append({
            "rule": "③ 同场景同测试点并数据",
            "survivor": survivor["tc_id"],
            "victims": [v["tc_id"] for v in victims],
            "biz_scene": key[0],
            "title": key[1],
            "merged_data": list(all_data) if all_data else [],
        })

    return merged, log_entries


def find_rule12_candidates(cases):
    """规则①②候选：断言高度重叠的用例对"""
    candidates = []
    for i in range(len(cases)):
        for j in range(i + 1, len(cases)):
            a = cases[i]
            b = cases[j]
            exp_a = a.get("expected", "")
            exp_b = b.get("expected", "")

            if not exp_a or not exp_b:
                continue

            # 简单启发式：其中一个是另一个的子串，或关键词重叠 > 60%
            if exp_a in exp_b or exp_b in exp_a:
                candidates.append({
                    "type": "子串包含",
                    "a_tc": a["tc_id"], "b_tc": b["tc_id"],
                    "a_expected": exp_a[:80], "b_expected": exp_b[:80],
                })
                continue

            words_a = set(exp_a)
            words_b = set(exp_b)
            if words_a and words_b:
                overlap = len(words_a & words_b) / min(len(words_a), len(words_b))
                if overlap > 0.6 and a.get("biz_scene") == b.get("biz_scene"):
                    candidates.append({
                        "type": f"高重叠({overlap:.0%})",
                        "a_tc": a["tc_id"], "b_tc": b["tc_id"],
                        "a_expected": exp_a[:80], "b_expected": exp_b[:80],
                    })

    return candidates


def write_merged_md(cases, output_path, candidates, shard_count):
    """写合并后的 Markdown，按模块分组排序"""
    if not cases:
        return

    # 按 module → biz_scene 排序，同模块的用例聚在一起
    cases.sort(key=lambda c: (c.get("module", ""), c.get("biz_scene", "")))

    # 统一编号
    for i, c in enumerate(cases, 1):
        c["tc_id"] = f"TC-{i:04d}"

    # 确定所有列
    all_cols = list(cases[0].keys())
    lines = []
    lines.append("---")
    lines.append(f"step: 3")
    lines.append(f"merged_from: {shard_count} shards")
    lines.append(f"generated_at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("---")
    lines.append("")

    if candidates:
        lines.append(f"### ⚠️ 待 AI 判断的去重候选（{len(candidates)} 对）")
        for c in candidates:
            lines.append(f"- [{c['type']}] {c['a_tc']} ↔ {c['b_tc']}")
            lines.append(f"  - A: {c['a_expected']}")
            lines.append(f"  - B: {c['b_expected']}")
        lines.append("")

    lines.append("<!-- TABLE:cases BEGIN -->")
    lines.append("| " + " | ".join(all_cols) + " |")
    lines.append("|" + "|".join(["------"] * len(all_cols)) + "|")
    for c in cases:
        cells = [c.get(col, "") for col in all_cols]
        lines.append("| " + " | ".join(cells) + " |")
    lines.append("<!-- TABLE:cases END -->")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def write_merge_log(log_entries, output_dir, shard_files):
    """写合并日志"""
    path = os.path.join(output_dir, "_merge-log.md")
    lines = [MERGE_LOG_HEADER.format(
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        shard_list=", ".join(os.path.basename(f) for f in shard_files)
    )]
    for entry in log_entries:
        lines.append(f"### {entry['rule']}")
        lines.append(f"- 存活: {entry['survivor']}")
        lines.append(f"- 并入: {', '.join(entry['victims'])}")
        lines.append(f"- 场景: {entry.get('biz_scene', '-')} / {entry.get('title', '-')}")
        if entry.get('merged_data'):
            lines.append(f"- 合并数据: {entry['merged_data']}")
        lines.append("")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def main():
    if len(sys.argv) < 3:
        print("用法: python merge.py <03-cases-dir> <output.md> [--auto]", file=sys.stderr)
        sys.exit(1)

    input_dir = sys.argv[1]
    output_path = sys.argv[2]
    auto_mode = "--auto" in sys.argv

    # 前置闸门：02-scenarios.md 需 gate_2=confirmed（用户已确认测试设计）才允许写用例
    # 定位 02 产物：与 03-cases 同级的 02-scenarios.md
    gate_guard("gate_2", os.path.join(os.path.dirname(os.path.abspath(output_path)), "02-scenarios.md"))

    # 收集所有分片
    shard_files = sorted([
        os.path.join(input_dir, f) for f in os.listdir(input_dir)
        if f.startswith("_shard-") and f.endswith(".md")
    ])
    if not shard_files:
        print("❌ 未找到 _shard-NN.md 文件")
        sys.exit(1)

    # 解析
    all_cases = []
    for sf in shard_files:
        cases, _ = parse_cases_from_md(sf)
        all_cases.extend(cases)

    if not all_cases:
        print("❌ 所有分片均无用例数据")
        sys.exit(1)

    print(f"📋 读取 {len(shard_files)} 个分片，共 {len(all_cases)} 条用例")

    # 规则③：同场景合并
    merged, log = merge_rule3(all_cases)
    rule3_count = len(all_cases) - len(merged)
    print(f"   规则③ 合并: {rule3_count} 条 → 现 {len(merged)} 条")

    # 规则①②候选
    candidates = []
    if not auto_mode:
        candidates = find_rule12_candidates(merged)
        if candidates:
            print(f"   ⚠️ 规则①②候选: {len(candidates)} 对（需 AI 判断）")

    # 写产物
    write_merged_md(merged, output_path, candidates, len(shard_files))
    write_merge_log(log, input_dir, shard_files)

    print(f"✅ {output_path} ({len(merged)} 条)")


if __name__ == "__main__":
    main()
