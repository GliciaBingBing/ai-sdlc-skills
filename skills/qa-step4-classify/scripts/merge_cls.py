"""
qa-step4-classify 分类分片合并脚本

用法：
  python merge_cls.py <03-cases-dir> <output_md_path>

功能：
1. 读取 03-cases/ 下所有 _cls-NN.md（分类分片，20 列全填）
2. 抽取 TABLE:cases（兼容 <!-- TABLE:cases BEGIN/END --> 与 ## TABLE:cases 两种分隔符）
3. 按模块顺序稳定合并，重编号 tc_id = TC-0001 ..
4. 写 04-cases.md（保留 redline_flag / source_scn_id 追溯列）
5. 调 generate_excel.py 生成双页签 04-cases.xlsx

本脚本不检查上游 gate（它产出 gate_3: pending 的 04-cases.md，由编排器按 auto-confirm 规则回写 confirmed）。
"""
import re
import sys
import os
import subprocess
from datetime import datetime

SKILL_ROOT = os.path.dirname(os.path.abspath(__file__))
GEN = os.path.join(SKILL_ROOT, "generate_excel.py")


def parse_cases_from_md(filepath):
    """从 Markdown 文件解析 TABLE:cases，鲁棒兼容两种分隔符"""
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    m = re.search(
        r"<!-- TABLE:cases BEGIN -->(.*?)<!-- TABLE:cases END -->",
        content, re.DOTALL
    )
    if not m:
        # 注：fallback 分支必须让 group(1) 也包含表头行，否则表头会被误当首条数据，
        # 导致 headers 错位、tc_id 取不到、整片解析为 0 行（cls-03/04 早期分片曾因此整片丢失）。
        m = re.search(
            r"(\| tc_id \|.*?\n\|[-| ]+\|\n(?:\|.*\|\n)+)",
            content
        )
    if not m:
        return [], None

    table_text = m.group(1)
    lines = [l for l in table_text.strip().split("\n") if l.strip().startswith("|")]
    if len(lines) < 2:
        return [], None

    headers = [h.strip() for h in lines[0].strip("|").split("|")]
    cases = []
    for line in lines[1:]:
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 5:
            continue
        # 跳分隔行
        if set("".join(cells).replace(" ", "")) <= set("-:"):
            continue
        case = {headers[i]: cells[i] for i in range(min(len(headers), len(cells)))}
        if case.get("tc_id"):
            cases.append(case)
    return cases, headers


def main():
    if len(sys.argv) < 3:
        print("用法: python merge_cls.py <03-cases-dir> <output_md_path>", file=sys.stderr)
        sys.exit(1)

    input_dir = sys.argv[1]
    output_path = sys.argv[2]

    cls_files = sorted(
        os.path.join(input_dir, f) for f in os.listdir(input_dir)
        if f.startswith("_cls-") and f.endswith(".md")
    )
    if not cls_files:
        print("❌ 未找到 _cls-NN.md 文件")
        sys.exit(1)

    all_cases = []
    for cf in cls_files:
        cases, _ = parse_cases_from_md(cf)
        all_cases.extend(cases)

    if not all_cases:
        print("❌ 所有分类分片均无用例数据")
        sys.exit(1)

    # 按模块首次出现顺序稳定排序
    order = []
    for c in all_cases:
        mod = c.get("module", "")
        if mod not in order:
            order.append(mod)
    all_cases.sort(
        key=lambda c: order.index(c["module"]) if c["module"] in order else 999
    )

    # 统一编号
    for i, c in enumerate(all_cases, 1):
        c["tc_id"] = f"TC-{i:04d}"

    all_cols = list(all_cases[0].keys())

    lines = [
        "---",
        "step: 4",
        "merged_from: classify shards",
        f"generated_at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "---",
        "",
        "<!-- TABLE:cases BEGIN -->",
        "| " + " | ".join(all_cols) + " |",
        "|" + "|".join(["------"] * len(all_cols)) + "|",
    ]
    for c in all_cases:
        lines.append("| " + " | ".join(c.get(col, "") for col in all_cols) + " |")
    lines.append("<!-- TABLE:cases END -->")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"✅ {output_path} ({len(all_cases)} 条，来自 {len(cls_files)} 个分片)")

    # 出双页签
    xlsx = os.path.splitext(output_path)[0] + ".xlsx"
    try:
        subprocess.run([sys.executable, GEN, output_path, xlsx], check=True)
        print(f"✅ {xlsx} 已生成")
    except subprocess.CalledProcessError as e:
        print(f"⚠️ generate_excel.py 失败：{e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
