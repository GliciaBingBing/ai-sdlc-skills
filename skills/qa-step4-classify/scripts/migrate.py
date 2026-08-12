"""
qa-step4-classify 用例迁移工具

用法：
  python migrate.py <cases_md> --to-ai <tc_id> [<tc_id> ...]
  python migrate.py <cases_md> --to-human <tc_id> [<tc_id> ...]
  python migrate.py <cases_md> --list

功能：
- --to-ai: 把指定用例的 exec_by 改为 "AI"，并初始化 AI 追加列为空（待 AI 填写）
- --to-human: 把指定用例的 exec_by 改为 "人"，清除 AI 追加列
- --list: 列出当前 exec_by 分布

这个脚本只改 exec_by 标签和追加列占位，不填内容——内容由 AI agent 判断后填写。
"""

import re
import sys
import json

HUMAN_COLS = [
    "tc_id", "module", "biz_scene", "title",
    "precondition", "test_content", "expected",
    "priority", "exec_by"
]

AI_EXTRA_COLS = [
    "entry_path", "depends_on", "test_data", "assertions",
    "tool_type", "tool_payload", "db_verify", "cleanup", "block_reason"
]


def read_cases_md(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def write_cases_md(path, content):
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def parse_table(text):
    """解析 TABLE:cases，返回 (headers, rows, table_start, table_end)"""
    match = re.search(
        r"(<!-- TABLE:cases BEGIN -->.*?)(\| tc_id \|.*?\n\|[-| ]+\|\n((?:\|.*\|\n)+))",
        text, re.DOTALL
    )
    if not match:
        match = re.search(
            r"(\| tc_id \|.*?\n\|[-| ]+\|\n((?:\|.*\|\n)+))",
            text
        )
    if not match:
        return [], [], [], -1, -1

    prefix = match.group(1) if "BEGIN" in match.group(0) else ""
    table_start = text.find(match.group(2) if "BEGIN" not in match.group(0) else
                            match.group(2).split("\n")[0].split("| tc_id")[0] + "| tc_id")
    # 简化：找表格块
    lines = [l for l in match.group(0).strip().split("\n") if l.strip().startswith("|")]
    if len(lines) < 2:
        return [], [], [], -1, -1

    headers = [h.strip() for h in lines[0].strip("|").split("|")]
    rows = []
    for line in lines[1:]:
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 5:
            continue
        row = {headers[i]: cells[i] for i in range(min(len(headers), len(cells)))}
        if row.get("tc_id"):
            rows.append(row)
    return headers, rows, lines[0], lines[1:]


def list_distribution(path):
    text = read_cases_md(path)
    headers, rows, _, _ = parse_table(text)
    ai = sum(1 for r in rows if r.get("exec_by") == "AI")
    human = sum(1 for r in rows if r.get("exec_by") == "人")
    pending = sum(1 for r in rows if r.get("exec_by") not in ("AI", "人"))
    return {"total": len(rows), "ai": ai, "human": human, "pending": pending}


def migrate(path, tc_ids, to_ai):
    text = read_cases_md(path)
    headers, rows, hdr_line, data_lines = parse_table(text)
    if not headers or not rows:
        print("❌ 无法解析 TABLE:cases")
        return False

    changed = []
    for row in rows:
        if row.get("tc_id") in tc_ids:
            old = row.get("exec_by", "")
            if to_ai:
                row["exec_by"] = "AI"
                row["block_reason"] = ""
                # 初始化 AI 追加列（空值，待 AI 填写）
                for col in AI_EXTRA_COLS:
                    if col not in row or col == "block_reason":
                        row[col] = ""
            else:
                row["exec_by"] = "人"
                row["block_reason"] = "待填写"
                # 清除 AI 追加列
                for col in AI_EXTRA_COLS:
                    row[col] = ""
            changed.append({"tc_id": row["tc_id"], "from": old, "to": row["exec_by"]})

    if not changed:
        print("⚠️ 没有匹配的用例 ID")
        return True

    # 重建表格
    all_headers = list(headers)
    for col in HUMAN_COLS + AI_EXTRA_COLS:
        if col not in all_headers:
            all_headers.append(col)

    new_lines = []
    # 保留锚点前的内容
    table_match = re.search(r"(<!-- TABLE:cases BEGIN -->)?(\| tc_id \|)", text)
    if table_match:
        before = text[:table_match.start()]
        after_anchor = text[table_match.end():]
        # 找表格结束
        table_end = after_anchor.find("\n\n")
        if table_end == -1:
            table_end = len(after_anchor)
        after = after_anchor[table_end:]

        # 重建表头
        new_table = "| " + " | ".join(all_headers) + " |\n"
        new_table += "|" + "|".join(["------"] * len(all_headers)) + "|\n"
        for row in rows:
            cells = [row.get(h, "") for h in all_headers]
            new_table += "| " + " | ".join(cells) + " |\n"

        new_text = before + new_table + after
    else:
        # 简单追加
        new_table = "\n| " + " | ".join(all_headers) + " |\n"
        new_table += "|" + "|".join(["------"] * len(all_headers)) + "|\n"
        for row in rows:
            cells = [row.get(h, "") for h in all_headers]
            new_table += "| " + " | ".join(cells) + " |\n"
        new_text = text + "\n" + new_table

    write_cases_md(path, new_text)

    direction = "AI" if to_ai else "人"
    for c in changed:
        print(f"  ✅ {c['tc_id']}: {c['from']} → {c['to']}")

    return True


def main():
    if "--list" in sys.argv:
        path = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else sys.argv[2]
        dist = list_distribution(path)
        print(json.dumps(dist, ensure_ascii=False) if "--json" in sys.argv else
              f"  总: {dist['total']}  |  AI: {dist['ai']}  |  人: {dist['human']}  |  待分类: {dist['pending']}")
        return

    if "--to-ai" in sys.argv:
        idx = sys.argv.index("--to-ai")
        path = sys.argv[1]
        tc_ids = set(sys.argv[idx+1:])
        to_ai = True
    elif "--to-human" in sys.argv:
        idx = sys.argv.index("--to-human")
        path = sys.argv[1]
        tc_ids = set(sys.argv[idx+1:])
        to_ai = False
    else:
        print("用法: python migrate.py <cases_md> --to-ai|--to-human <tc_id>...", file=sys.stderr)
        print("      python migrate.py <cases_md> --list", file=sys.stderr)
        sys.exit(1)

    if not tc_ids:
        print("❌ 未指定用例 ID")
        sys.exit(1)

    ok = migrate(path, tc_ids, to_ai)
    if ok:
        print(f"\n✅ 迁移完成。被迁移用例的 AI 追加列已{'初始化（待 AI 填写）' if to_ai else '清除'}。")


if __name__ == "__main__":
    main()
