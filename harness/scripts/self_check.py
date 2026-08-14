#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
G1 自检闭环 — 机械门禁（dev-harness 护栏1 的可执行落地）

把「护栏1 自检闭环」从 Markdown 指令升级为脚本：
  - 跑 build 命令、跑 test 命令
  - 二者都过 → status=pass，exit 0
  - 任一失败 → status=fail，列出 failed 项，exit 1（拦截「报完成」）
  - 输出 self_check_report（对齐 request.schema 的 self_check_report 字段）

纯标准库，克隆即跑，零第三方依赖。与 scope_check.py（G2）配合，让 dev 段
拥有 2 道机械门禁，硬度对齐 QA 段的 gate_check / merge / trace_audit。

用法：
  python self_check.py <项目根> --build "<构建命令>" --test "<测试命令>" [--report <out.json>]

退出码：
  0 = build+test 全过
  1 = 任一失败（拦截报完成）
  2 = 参数/运行错误
"""

import sys
import os
import json
import subprocess


def run_cmd(root, cmd):
    """跑一条 shell 命令，返回 (returncode, 末尾输出)。"""
    try:
        r = subprocess.run(
            cmd, cwd=root, shell=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8",
        )
        tail = "\n".join(r.stdout.strip().splitlines()[-8:]) if r.stdout else ""
        return r.returncode, tail
    except Exception as e:
        return 127, "执行异常：%s" % e


def main():
    argv = sys.argv[1:]
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        sys.exit(0)

    root = argv[0]
    if not os.path.isdir(root):
        print("[selfcheck] 项目根不存在：%s" % root, file=sys.stderr)
        sys.exit(2)

    build_cmd = None
    test_cmd = None
    report_path = None
    i = 1
    while i < len(argv):
        a = argv[i]
        if a == "--build" and i + 1 < len(argv):
            build_cmd = argv[i + 1]
            i += 2
        elif a == "--test" and i + 1 < len(argv):
            test_cmd = argv[i + 1]
            i += 2
        elif a == "--report" and i + 1 < len(argv):
            report_path = argv[i + 1]
            i += 2
        else:
            i += 1

    if not build_cmd and not test_cmd:
        print("[selfcheck] 至少需要 --build 或 --test 之一", file=sys.stderr)
        sys.exit(2)

    failed = []
    build_result = "未执行"
    test_result = "未执行"

    if build_cmd:
        rc, out = run_cmd(root, build_cmd)
        build_result = out if out else ("exit=%d" % rc)
        if rc != 0:
            failed.append("build")
    if test_cmd:
        rc, out = run_cmd(root, test_cmd)
        test_result = out if out else ("exit=%d" % rc)
        if rc != 0:
            failed.append("test")

    status = "fail" if failed else "pass"
    report = {
        "status": status,
        "build_result": build_result,
        "test_result": test_result,
        "failed": failed,
        "code_clean": None,  # G5 独立护栏，不在此代劳
    }
    txt = json.dumps(report, ensure_ascii=False, indent=2)
    if report_path:
        try:
            with open(report_path, "w", encoding="utf-8") as f:
                f.write(txt)
        except Exception as e:
            print("[selfcheck] 写报告失败：%s" % e, file=sys.stderr)
    print(txt)

    if status == "fail":
        print("[selfcheck] 拦截：build/test 未全过，不报完成：%s" % ", ".join(failed),
              file=sys.stderr)
        sys.exit(1)
    print("[selfcheck] OK：build+test 全过")
    sys.exit(0)


if __name__ == "__main__":
    main()
