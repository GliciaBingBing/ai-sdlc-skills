#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
G2 范围自检 — 机械门禁（dev-harness 护栏2 的可执行落地）

把「护栏2 范围自检」从 Markdown 指令升级为脚本：
  - 读 harness/module-map.yaml 拿「允许改动的目录集合」
  - 用 git 拿出本次改动文件（含未提交 / 未跟踪）
  - 逐文件比对：落在允许目录内 = 在范围；否则 = 越界
  - 越界 → 输出 diff_scope_report 且 exit(1)，**在工具层面拦截提交**，不靠 AI 自觉

纯标准库（含极简 module-map 解析），克隆即跑，零第三方依赖。

用法：
  python scope_check.py <项目根> [--modules MOD-001,MOD-002]
                          [--harness <harness目录>] [--report <out.json>]

退出码：
  0 = 无越界（或降级放行）
  1 = 存在越界改动（机械拦截，不提交）

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
    """极简解析 module-map.yaml：返回 {module_id: {"name":..,"dirs":[..]}}。
    只支持本仓库约定结构（modules: 下若干 - module_id: 块，含 dirs: 列表）。"""
    modules = {}
    try:
        with open(yaml_path, encoding="utf-8") as f:
            text = f.read()
    except Exception:
        return modules
    cur = None          # 当前正在解析的模块块
    in_dirs = False     # 是否处于 dirs: 的列表项中
    for raw in text.splitlines():
        s = raw.strip()
        if not s or s.startswith("#"):
            continue
        if s.startswith("modules:"):
            # 顶层列表声明：重置，等待第一个 - module_id 块
            cur = None
            in_dirs = False
            continue
        # 模块块开始（顶层列表项）
        if s.startswith("- module_id:"):
            mid = s.split(":", 1)[1].strip()
            cur = {"id": mid, "name": "", "dirs": []}
            modules[mid] = cur
            in_dirs = False
            continue
        # 字段必须属于某个模块块
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
            # 其他字段（owner 等）或缩进变化的字段，退出 dirs 列表，但不离开模块块
            in_dirs = False
    return modules


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

    # ---- 降级：无 map ----
    if not os.path.isfile(map_path):
        report = {
            "changed_files": get_changed_files(root),
            "mapped_modules": [],
            "out_of_scope": [],
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
        in_scope = False
        for d in allowed_dirs:
            if f == d or f.startswith(d + "/"):
                in_scope = True
                # 记录命中的模块
                for mid, m in selected.items():
                    if d in [x.rstrip("/") for x in m["dirs"]]:
                        hit_modules.add(mid)
                break
        if not in_scope:
            out_of_scope.append(f)

    blocked = len(out_of_scope) > 0
    report = {
        "changed_files": changed,
        "mapped_modules": sorted(hit_modules),
        "out_of_scope": out_of_scope,
        "blocked": blocked,
    }
    _emit(report, report_path)

    if blocked:
        print("[scope] 拦截：以下文件越界（不在允许目录内），不提交：", file=sys.stderr)
        for f in out_of_scope:
            print("  - %s" % f, file=sys.stderr)
        sys.exit(1)
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
