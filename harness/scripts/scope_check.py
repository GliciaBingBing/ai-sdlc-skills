#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
G2 范围自检 — 机械门禁（dev-harness 护栏2 的可执行落地）+ 申诉通道

把「护栏2 范围自检」从 Markdown 指令升级为脚本：
  - 读 harness/module-map.yaml 拿「允许改动的目录集合」
  - 用 git 拿出本次改动文件（含未提交 / 未跟踪）
  - 逐文件比对：落在允许目录内 = 在范围；否则 = 越界
  - 越界 → 不再一律 exit(1) 一刀切，而是**自动探测影响层**并产出 `appeal_needed`
    清单，已由人工签字的例外（harness/appeal_log.yaml）放行，未签字的才拦截提交。

影响层分级（按路径启发式，机械判定；人工可在 appeal_log 覆盖）：
  - UI 层      ：展示型文件（.tsx/.jsx/.vue/.css/...），越界风险低 → 人审放行
  - 配置       ：配置型文件（.yaml/.yml/.env/...），越界风险低 → 人审放行
  - 函数依赖   ：逻辑型文件（.py/.ts/.go/...），其中命中 shared/common/lib/utils/core
                 路径的标记为「跨模块共享」，风险高 → 强制 sign-off

纯标准库（含极简 module-map / appeal_log 解析），克隆即跑，零第三方依赖。

用法：
  python scope_check.py <项目根> [--modules MOD-001,MOD-002]
                          [--harness <harness目录>] [--report <out.json>]

退出码：
  0 = 无越界（或越界文件均已走申诉通道签字放行）
  1 = 存在越界改动且未走申诉通道（机械拦截，不提交）

降级（不拦截、exit 0）：
  - harness/module-map.yaml 不存在
  - 选定模块无任何目录映射
  - 非 git 仓库 / git 不可用
降级时仍输出 report，但 blocked=false 并打印 warning，对应 G2.md 的边界约定。
"""

import sys
import os
import json
import subprocess


# ---- 影响层启发式 ----
UI_EXT = {"tsx", "jsx", "vue", "svelte", "css", "scss", "less", "html", "htm"}
CONFIG_EXT = {"yaml", "yml", "toml", "ini", "env"}
SHARED_PATH_HINTS = ("shared/", "common/", "lib/", "utils/", "core/", "internal/")


def classify_layer(path):
    """按路径启发式返回 (layer, shared_flag)。layer ∈ {UI 层, 配置, 函数依赖}。"""
    p = path.replace("\\", "/").lower()
    ext = p.rsplit(".", 1)[-1] if "." in p else ""
    shared = any(h in p.split("/") for h in
                 ("shared", "common", "lib", "utils", "core", "internal"))
    if ext in UI_EXT:
        return "UI 层", shared
    if ext in CONFIG_EXT:
        return "配置", shared
    # json 仅在明显是配置/settings 时才算配置，否则归逻辑层
    if ext == "json" and ("config" in p or "settings" in p):
        return "配置", shared
    return "函数依赖", shared


def required_action(layer, shared):
    if layer == "函数依赖":
        return "强制 sign-off" + ("（跨模块共享，必须显式人工签字）" if shared else "")
    return "人审放行"


def run_git(root, args):
    """在 root 下跑 git，返回 (returncode, stdout_text)。失败不抛，交给调用方降级。"""
    try:
        r = subprocess.run(
            ["git"] + args, cwd=root,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, encoding="utf-8",
        )
        return r.returncode, r.stdout
    except Exception:
        return 127, ""


def get_changed_files(root):
    """拿本次改动文件（repo 相对路径）：已跟踪的 diff + 未跟踪文件。非 git 则降级。"""
    files = set()
    rc, out = run_git(root, ["diff", "--name-only", "HEAD"])
    if rc == 0:
        for ln in out.splitlines():
            ln = ln.strip()
            if ln:
                files.add(ln.replace("\\", "/"))
    else:
        # 可能没有提交（空仓库）：退回「全部已跟踪文件」
        rc2, out2 = run_git(root, ["ls-files"])
        if rc2 == 0:
            for ln in out2.splitlines():
                ln = ln.strip()
                if ln:
                    files.add(ln.replace("\\", "/"))
    # 未跟踪文件（将要被 add 的）
    rc3, out3 = run_git(root, ["ls-files", "--others", "--exclude-standard"])
    if rc3 == 0:
        for ln in out3.splitlines():
            ln = ln.strip()
            if ln:
                files.add(ln.replace("\\", "/"))
    return sorted(files)


def parse_module_map(yaml_path):
    """极简解析 module-map.yaml：返回 {module_id: {"name":..,"dirs":[..]}}。"""
    modules = {}
    try:
        with open(yaml_path, encoding="utf-8") as f:
            text = f.read()
    except Exception:
        return modules
    cur = None
    in_dirs = False
    for raw in text.splitlines():
        s = raw.strip()
        if not s or s.startswith("#"):
            continue
        if s.startswith("modules:"):
            cur = None
            in_dirs = False
            continue
        if s.startswith("- module_id:"):
            mid = s.split(":", 1)[1].strip()
            cur = {"id": mid, "name": "", "dirs": []}
            modules[mid] = cur
            in_dirs = False
            continue
        if cur is None:
            continue
        if s.startswith("module_name:"):
            cur["name"] = s.split(":", 1)[1].strip()
            in_dirs = False
        elif s.startswith("dirs:"):
            in_dirs = True
        elif in_dirs and s.startswith("- "):
            d = s[2:].strip()
            if d:
                cur["dirs"].append(d.replace("\\", "/"))
        else:
            in_dirs = False
    return modules


def _norm_val(v):
    """归一化 YAML 标量：去掉引号；"" / '' / ~ / 无 均视为空。"""
    v = v.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in ("'", '"'):
        v = v[1:-1].strip()
    if v in ("", "~", "null", "None"):
        v = ""
    return v


def parse_appeal_log(yaml_path):
    """极简解析 appeal_log.yaml：返回已签字申诉条目列表。

    条目结构：
      - file: <repo 相对路径>
        layer: <UI 层|函数依赖|配置>   # 可覆盖自动探测
        impact_scope: <一句话影响范围>
        approved_by: <human | ai-reviewed>
        approved_at: <YYYY-MM-DD>
    impact_scope / approved_by 为空（或 "" / '' / ~）视为申诉未完成。
    """
    appeals = []
    try:
        with open(yaml_path, encoding="utf-8") as f:
            text = f.read()
    except Exception:
        return appeals
    cur = None
    in_appeals = False
    for raw in text.splitlines():
        s = raw.strip()
        if not s or s.startswith("#"):
            continue
        if s.startswith("appeals:"):
            in_appeals = True
            cur = None
            continue
        if not in_appeals:
            continue
        if s.startswith("- file:"):
            if cur:
                appeals.append(cur)
            cur = {"file": _norm_val(s.split(":", 1)[1]).replace("\\", "/"),
                   "layer": "", "impact_scope": "", "approved_by": "", "approved_at": ""}
            continue
        if cur is None:
            continue
        if s.startswith("file:"):
            cur["file"] = _norm_val(s.split(":", 1)[1]).replace("\\", "/")
        elif s.startswith("layer:"):
            cur["layer"] = _norm_val(s.split(":", 1)[1])
        elif s.startswith("impact_scope:"):
            cur["impact_scope"] = _norm_val(s.split(":", 1)[1])
        elif s.startswith("approved_by:"):
            cur["approved_by"] = _norm_val(s.split(":", 1)[1])
        elif s.startswith("approved_at:"):
            cur["approved_at"] = _norm_val(s.split(":", 1)[1])
    if cur:
        appeals.append(cur)
    return appeals


def main():
    argv = sys.argv[1:]
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        sys.exit(0)

    root = argv[0]
    if not os.path.isdir(root):
        print("[scope] 项目根不存在：%s" % root, file=sys.stderr)
        sys.exit(2)

    modules_filter = None
    harness_dir = None
    report_path = None
    i = 1
    while i < len(argv):
        a = argv[i]
        if a == "--modules" and i + 1 < len(argv):
            modules_filter = [m.strip() for m in argv[i + 1].split(",") if m.strip()]
            i += 2
        elif a == "--harness" and i + 1 < len(argv):
            harness_dir = argv[i + 1]
            i += 2
        elif a == "--report" and i + 1 < len(argv):
            report_path = argv[i + 1]
            i += 2
        else:
            i += 1

    if harness_dir is None:
        harness_dir = os.path.join(root, ".workbuddy", "harness")
    map_path = os.path.join(harness_dir, "module-map.yaml")
    appeal_log_path = os.path.join(harness_dir, "appeal_log.yaml")

    # ---- 降级：无 map ----
    if not os.path.isfile(map_path):
        report = {
            "changed_files": get_changed_files(root),
            "mapped_modules": [],
            "out_of_scope": [],
            "appeal_needed": [],
            "appealed_ok": [],
            "blocked": False,
            "warning": "module-map.yaml 缺失，护栏2 降级放行（仅执行 G1/G3/G5），请先建档 module-map",
        }
        _emit(report, report_path)
        print("[scope] WARNING: 无 module-map.yaml，降级放行（不拦截）", file=sys.stderr)
        sys.exit(0)

    all_modules = parse_module_map(map_path)
    if not all_modules:
        report = {
            "changed_files": get_changed_files(root),
            "mapped_modules": [],
            "out_of_scope": [],
            "appeal_needed": [],
            "appealed_ok": [],
            "blocked": False,
            "warning": "module-map.yaml 未解析出任何模块，护栏2 降级放行",
        }
        _emit(report, report_path)
        print("[scope] WARNING: module-map 为空，降级放行（不拦截）", file=sys.stderr)
        sys.exit(0)

    # 选定允许目录集合
    if modules_filter:
        selected = {m: all_modules[m] for m in modules_filter if m in all_modules}
        if not selected:
            selected = all_modules  # 过滤无效时退回全部，避免误拦截
    else:
        selected = all_modules

    allowed_dirs = []
    for m in selected.values():
        allowed_dirs.extend(m["dirs"])
    allowed_dirs = [d.rstrip("/") for d in allowed_dirs if d.strip()]

    # 无可用目录映射 → 降级
    if not allowed_dirs:
        report = {
            "changed_files": get_changed_files(root),
            "mapped_modules": list(selected.keys()),
            "out_of_scope": [],
            "appeal_needed": [],
            "appealed_ok": [],
            "blocked": False,
            "warning": "选定模块无任何目录映射，护栏2 降级放行（请先让 AI 生成 module-map 目录映射）",
        }
        _emit(report, report_path)
        print("[scope] WARNING: 选定模块无目录映射，降级放行（不拦截）", file=sys.stderr)
        sys.exit(0)

    changed = get_changed_files(root)
    out_of_scope = []
    hit_modules = set()
    for f in changed:
        # harness 自身的控制文件（module-map / appeal_log）不在模块目录内，
        # 但属治理元数据，恒不算越界，避免「申诉白名单拦截自己」。
        base = f.rsplit("/", 1)[-1]
        if base in ("module-map.yaml", "appeal_log.yaml") and f.startswith(".workbuddy/harness/"):
            continue
        in_scope = False
        for d in allowed_dirs:
            if f == d or f.startswith(d + "/"):
                in_scope = True
                for mid, m in selected.items():
                    if d in [x.rstrip("/") for x in m["dirs"]]:
                        hit_modules.add(mid)
                break
        if not in_scope:
            out_of_scope.append(f)

    # ---- 申诉通道：越界文件按影响层分级处置 ----
    appeals = parse_appeal_log(appeal_log_path) if os.path.isfile(appeal_log_path) else []
    appeal_needed = []
    appealed_ok = []
    for f in out_of_scope:
        layer, shared = classify_layer(f)
        approved = None
        for a in appeals:
            if a.get("file", "").replace("\\", "/") == f:
                if a.get("impact_scope", "").strip() and a.get("approved_by", "").strip():
                    approved = a
                    break
        if approved:
            appealed_ok.append({
                "file": f,
                "layer": approved.get("layer") or layer,
                "approved_by": approved.get("approved_by"),
                "approved_at": approved.get("approved_at"),
            })
        else:
            appeal_needed.append({
                "file": f,
                "layer": layer,
                "shared": shared,
                "required_action": required_action(layer, shared),
            })

    blocked = len(appeal_needed) > 0
    report = {
        "changed_files": changed,
        "mapped_modules": sorted(hit_modules),
        "out_of_scope": out_of_scope,
        "appeal_needed": appeal_needed,
        "appealed_ok": appealed_ok,
        "blocked": blocked,
    }
    _emit(report, report_path)

    if blocked:
        print("[scope] 拦截：以下越界文件需走申诉通道（按影响层分级处置）：", file=sys.stderr)
        for it in appeal_needed:
            tag = " [共享]" if it.get("shared") else ""
            print("  - %s  [%s%s] 需：%s" % (it["file"], it["layer"], tag, it["required_action"]),
                  file=sys.stderr)
        print("[scope] 处置：在 harness/appeal_log.yaml 的 appeals: 下补一条并人工签字，"
              "再重跑即通过：", file=sys.stderr)
        for it in appeal_needed:
            print("    - file: %s" % it["file"], file=sys.stderr)
            print("      layer: %s   # 可覆盖自动探测（UI 层 / 函数依赖 / 配置）" % it["layer"],
                  file=sys.stderr)
            print('      impact_scope: "<一句话说明影响范围>"', file=sys.stderr)
            print("      approved_by: human", file=sys.stderr)
            print("      approved_at: <YYYY-MM-DD>", file=sys.stderr)
        sys.exit(1)
    else:
        if appealed_ok:
            print("[scope] OK：越界文件已走申诉通道签字放行（%s），本次改动可提交" %
                  (", ".join(x["file"] for x in appealed_ok)), file=sys.stderr)
        else:
            print("[scope] OK：本次改动全部在允许范围内（模块 %s）" %
                  (",".join(sorted(hit_modules)) or "全部映射模块"))
        sys.exit(0)


def _emit(report, report_path):
    txt = json.dumps(report, ensure_ascii=False, indent=2)
    if report_path:
        try:
            with open(report_path, "w", encoding="utf-8") as f:
                f.write(txt)
        except Exception as e:
            print("[scope] 写报告失败：%s" % e, file=sys.stderr)
    print(txt)


if __name__ == "__main__":
    main()
