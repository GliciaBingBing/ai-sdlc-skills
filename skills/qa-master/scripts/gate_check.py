"""
qa-master 闸门状态位校验脚本（gate_check）

用法：
  python gate_check.py <产物md路径> <gate_key> [--strict] [--mode conflict|confirm]

gate_key 语义（对应 SKILL.md「闸门清单」+「用户不审需求文档原则」）：

  gate_1  ①→②  01-requirements.md
          ——【冲突裁决门，不是确认门】——
          需求文档不需要用户审核。仅当 01 识别出需求冲突/歧义时才需用户裁决。
          默认无冲突 = 自动放行。--mode conflict 检查 frontmatter 是否含待裁决冲突。

  gate_2  ②→③  02-scenarios.md
          ——【主确认门·需求理解探针】——
          用户唯一必须主动确认的点。测试方案没问题 = 需求理解对。
          --mode confirm 要求 gate_2 == confirmed（由用户确认后回写）。

  gate_3  ④→⑤  04-cases.md
          ——【确认门·分类过目】——
          --mode confirm 要求 gate_3 == confirmed。

frontmatter 状态位契约：
  gate_N: pending    产物写完初始态（自检通过 ≠ 确认）
  gate_N: confirmed  仅编排器在用户 AskUserQuestion 确认后回写
  01 无冲突时不需要 confirmed；其放行由「无待裁决冲突」决定

退出码：0=放行  1=拦截（打印原因，供编排器中止）
"""

import re
import sys


def load_frontmatter(md_path):
    """解析 Markdown frontmatter，返回 dict"""
    try:
        with open(md_path, "r", encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        return None, f"产物不存在: {md_path}"
    except Exception as e:
        return None, f"读取失败: {e}"

    m = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
    if not m:
        return None, "缺少 frontmatter（应以 --- 开头）"

    fm = {}
    for line in m.group(1).split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            k, _, v = line.partition(":")
            fm[k.strip()] = v.strip()
    return fm, None


def check_confirm(fm, gate_key, md_path):
    """gate_2/gate_3：必须是 confirmed 才放行"""
    value = fm.get(gate_key, "").strip()
    if not value:
        print(f"🚫 gate_check 拦截 [{gate_key}]: frontmatter 缺少 `{gate_key}` 字段")
        print("   说明: 该步产物尚未经用户确认。先 present_files 展示产物 → AskUserQuestion 询问 → 用户确认后回写 gate_N: confirmed 再继续。")
        return False
    if value != "confirmed":
        print(f"🚫 gate_check 拦截 [{gate_key}]: 当前值 `{value}` ≠ `confirmed`")
        print("   说明: 状态位必须是 confirmed 才放行——只有用户确认过才算通过闸门，自检通过不算。")
        return False
    print(f"✅ gate_check 放行 [{gate_key}]: confirmed")
    return True


def check_conflict(fm, md_path):
    """gate_1：需求文档不审。仅当存在待裁决冲突时拦截（需要用户裁决）"""
    # 01 的 frontmatter 用 conflicts_status: pending|resolved 标记
    status = fm.get("conflicts_status", "").strip().lower()
    if status == "pending" or status == "待裁决":
        print(f"🚫 gate_check 拦截 [gate_1]: 01 存在待裁决需求冲突（conflicts_status=pending）")
        print("   说明: 需求文档无需用户审核；但 01 识别出需求冲突/歧义，需先请用户裁决。裁决后回写 conflicts_status: resolved 再继续。")
        return False
    # 无冲突标记 = 默认放行（需求已澄清，用户无需介入）
    print(f"✅ gate_check 放行 [gate_1]: 无待裁决冲突（需求文档无需用户审核）")
    return True


def main():
    if len(sys.argv) < 3:
        print("用法: python gate_check.py <产物md路径> <gate_key> [--strict] [--mode conflict|confirm]", file=sys.stderr)
        sys.exit(1)

    md_path = sys.argv[1]
    gate_key = sys.argv[2]
    mode = "confirm"
    for a in sys.argv[3:]:
        if a.startswith("--mode"):
            mode = a.split("=", 1)[1] if "=" in a else "confirm"

    fm, err = load_frontmatter(md_path)
    if err:
        print(f"🚫 gate_check 拦截 [{gate_key}]: {err}")
        sys.exit(1)

    if gate_key == "gate_1":
        ok = check_conflict(fm, md_path)        # 冲突裁决门（非确认门）
    else:
        ok = check_confirm(fm, gate_key, md_path)  # 确认门

    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
