"""
qa-master 回指完整性检查脚本（trace_audit）

用法：
  python trace_audit.py <02-scenarios.md> <03-cases.md> [--json]

功能：检查 ② 立案的每一条 SCN 和 REQ 是否在 ③ 的用例中有回指。输出 gap 清单。

逻辑：
- 读 02 的 TABLE:scenarios → 提取所有 scn_id + source_req_id[]
- 读 03 的 TABLE:cases → 提取所有 source_scn_id
- 比对：每个 SCN-ID 至少被一条用例回指？每个 REQ-ID 至少被一条用例回指？
- gap → 拦截；covered → 通过
"""

import re
import sys
import json
import os

# 下游脚本前置校验：闸门状态位必须是 confirmed 才允许运行
# 防止编排器跳过"用户确认"直接跑后续步骤（SKILL.md「产物状态位契约」）
def _gate_guard(gate_key, md_path):
    try:
        with open(md_path, "r", encoding="utf-8") as f:
            head = f.read(2048)
    except Exception as e:
        print(f"🚫 gate 拦截 [{gate_key}]: 无法读取 {md_path} ({e})", file=sys.stderr)
        sys.exit(1)
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


def parse_scenarios(md_path):
    """从 02-scenarios.md 提取所有 SCN-ID 和 REQ-ID"""
    with open(md_path, "r", encoding="utf-8") as f:
        content = f.read()

    match = re.search(
        r"<!-- TABLE:scenarios BEGIN -->(.*?)<!-- TABLE:scenarios END -->",
        content, re.DOTALL
    )
    if not match:
        match = re.search(
            r"\| scn_id \|.*?\n\|[-| ]+\|\n((?:\|.*\|\n)+)",
            content
        )
    if not match:
        return [], {}, "未找到 TABLE:scenarios"

    table_text = match.group(1) if match.lastindex == 1 else match.group(1)
    lines = [l for l in table_text.strip().split("\n") if l.strip().startswith("|")]
    if len(lines) < 2:
        return [], {}, "TABLE:scenarios 为空"

    headers = [h.strip() for h in lines[0].strip("|").split("|")]
    scn_ids = []
    req_map = {}  # REQ-ID → list of SCN-IDs

    for line in lines[1:]:
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 3:
            continue
        if all(set(c) <= set("-: ") for c in cells):
            continue  # 跳过分隔线
        row = {headers[i]: cells[i] for i in range(min(len(headers), len(cells)))}
        scn = row.get("scn_id", "").strip()
        if not scn:
            continue
        scn_ids.append(scn)

        # 提取 source_req_id[]
        req_ids = row.get("source_req_id[]", "").strip()
        if req_ids:
            for r in re.split(r"[,;，；\s]+", req_ids):
                r = r.strip()
                if r and r.startswith("REQ-"):
                    if r not in req_map:
                        req_map[r] = []
                    req_map[r].append(scn)

    return scn_ids, req_map, None


def parse_cases(md_path):
    """从 03-cases.md 提取所有 source_scn_id"""
    with open(md_path, "r", encoding="utf-8") as f:
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
        return set(), "未找到 TABLE:cases"

    table_text = match.group(1) if match.lastindex == 1 else match.group(1)
    lines = [l for l in table_text.strip().split("\n") if l.strip().startswith("|")]
    if len(lines) < 2:
        return set(), "TABLE:cases 为空"

    headers = [h.strip() for h in lines[0].strip("|").split("|")]
    covered_scn = set()

    for line in lines[1:]:
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 3:
            continue
        if all(set(c) <= set("-: ") for c in cells):
            continue  # 跳过分隔线
        row = {headers[i]: cells[i] for i in range(min(len(headers), len(cells)))}
        sid = row.get("source_scn_id", "").strip()
        if sid:
            for s in re.split(r"[,;，；\s]+", sid):
                s = s.strip()
                if s.startswith("SCN-"):
                    covered_scn.add(s)

    return covered_scn, None


def main():
    if len(sys.argv) < 3:
        print("用法: python trace_audit.py <02-scenarios.md> <03-cases.md> [--json]", file=sys.stderr)
        sys.exit(1)

    scn_path = sys.argv[1]
    cases_path = sys.argv[2]
    output_json = "--json" in sys.argv

    # 前置闸门：02 需 gate_2=confirmed（用户已确认测试设计，才允许跑用例回指/进入 ③ 收尾）
    _gate_guard("gate_2", scn_path)

    # 解析
    all_scn, req_map, err = parse_scenarios(scn_path)
    if err:
        print(f"❌ {err}")
        sys.exit(1)

    covered_scn, err = parse_cases(cases_path)
    if err:
        print(f"❌ {err}")
        sys.exit(1)

    # SCN 检查
    scn_gaps = [s for s in all_scn if s not in covered_scn]

    # REQ 检查：每个 REQ-ID 至少有一条 SCN 被用例回指
    req_gaps = []
    for req_id, scn_list in req_map.items():
        if not any(s in covered_scn for s in scn_list):
            req_gaps.append({"req_id": req_id, "scn_ids": scn_list})

    result = {
        "total_scn": len(all_scn),
        "covered_scn": len(covered_scn),
        "scn_gaps": scn_gaps,
        "total_req": len(req_map),
        "req_gaps": req_gaps,
        "pass": len(scn_gaps) == 0 and len(req_gaps) == 0,
    }

    if output_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        scn_pct = round(len(covered_scn) / len(all_scn) * 100, 1) if all_scn else 0
        print(f"📋 回指检查: {len(covered_scn)}/{len(all_scn)} SCN ({scn_pct}%)")
        if scn_gaps:
            print(f"   ❌ SCN gap ({len(scn_gaps)}): {', '.join(scn_gaps)}")
        if req_gaps:
            for g in req_gaps:
                print(f"   ❌ REQ gap: {g['req_id']} (SCN: {', '.join(g['scn_ids'])}) 均未被回指")
        if result["pass"]:
            print("   ✅ 通过")
        else:
            print(f"   🚫 拦截 — 存在 gap")
            sys.exit(1)


if __name__ == "__main__":
    main()
