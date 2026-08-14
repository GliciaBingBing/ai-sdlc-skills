"""
dev_gate_check.py - DEV 段需求覆盖闸门

比对 PRD 列出的 REQ-ID 清单（功能需求锚点）与 DEV 实际实现的 REQ-ID
（dev 产物 artifact_binding 中回指的 req_id），发现「PRD 要求但 DEV 静默漏做」
的需求 → exit(1) 拦截。这是 dev 段弥补「靠自觉」的最后一道机械门禁，
对齐 qa-master 的 trace_audit（QA 段 REQ 覆盖校验）。

用法：
  python dev_gate_check.py <prd.md> <artifact_binding.json> [--report <out.json>]

退出码：0=覆盖完整（放行）  1=存在缺口（拦截）
降级：PRD 无 REQ-ID 或 artifact_binding 缺失 → 不拦截（warning + exit 0），避免误杀。
"""
import json
import re
import sys


def extract_prd_req_ids(prd_path):
    """从 04-prd.md 的「## 4. 功能需求」节提取所有 REQ-ID。
    支持标题行 `### 4.x <模块名> · REQ-xxx` 及节内任意 REQ-xxx。"""
    try:
        with open(prd_path, encoding="utf-8") as f:
            text = f.read()
    except Exception:
        return []
    m = re.search(r"##\s*4\.\s*功能需求(.*?)(?=\n##\s*5\.|\Z)", text, re.DOTALL)
    section = m.group(1) if m else text
    return sorted(set(re.findall(r"REQ-\d+", section)))


def extract_dev_req_ids(binding_path):
    """从 artifact_binding.json 递归提取所有 req_id 值。"""
    try:
        with open(binding_path, encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return None  # 缺失/损坏 → 降级
    reqs = []

    def walk(node):
        if isinstance(node, dict):
            for k, v in node.items():
                if k == "req_id" and isinstance(v, str) and v.strip():
                    reqs.append(v.strip())
                else:
                    walk(v)
        elif isinstance(node, list):
            for item in node:
                walk(item)
    walk(data)
    return sorted(set(reqs))


def main():
    if len(sys.argv) < 3:
        print("用法: python dev_gate_check.py <prd.md> <artifact_binding.json> [--report <out.json>]", file=sys.stderr)
        sys.exit(1)
    prd_path = sys.argv[1]
    binding_path = sys.argv[2]
    report_path = None
    for a in sys.argv[3:]:
        if a.startswith("--report"):
            report_path = a.split("=", 1)[1] if "=" in a else None

    prd_reqs = extract_prd_req_ids(prd_path)
    if not prd_reqs:
        print("⚠️ dev_gate_check 降级：PRD 未提取到 REQ-ID（请确认 04-prd.md 功能需求带 REQ-xxx）。不拦截。")
        sys.exit(0)

    dev_reqs = extract_dev_req_ids(binding_path)
    if dev_reqs is None:
        print(f"⚠️ dev_gate_check 降级：artifact_binding 缺失/损坏（{binding_path}）。不拦截。")
        sys.exit(0)

    gaps = [r for r in prd_reqs if r not in dev_reqs]
    report = {
        "prd_req_count": len(prd_reqs),
        "dev_req_count": len(dev_reqs),
        "gaps": gaps,
        "blocked": bool(gaps),
    }
    if report_path:
        try:
            with open(report_path, "w", encoding="utf-8") as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    if gaps:
        print(f"🚫 dev_gate_check 拦截：PRD 有 {len(prd_reqs)} 个 REQ，DEV 实现 {len(dev_reqs)} 个，缺口 {len(gaps)} 个：")
        for g in gaps:
            print(f"   ❌ {g} 在 PRD 要求但 DEV 未回指实现（静默漏做）")
        print("   说明: dev 实现须通过 artifact_binding 回指每个 PRD 的 REQ-ID；缺回指即视为漏做，补齐后再报完成。")
        sys.exit(1)
    print(f"✅ dev_gate_check 放行：PRD {len(prd_reqs)} 个 REQ 全部被 DEV 实现回指（{', '.join(prd_reqs)}）")
    sys.exit(0)


if __name__ == "__main__":
    main()
