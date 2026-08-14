#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
提交前自动检查钩子（git pre-commit）：越界改动直接拦下来。

把 scope_check.py 挂到 git commit 流程——任何不在 module-map 允许目录内的改动，
在 `git commit` 时直接被机械拦截（exit 非 0），从根上杜绝「超范围提交」。

安装（项目级，推荐）：
  cp harness/scripts/pre-commit-scope.py <项目根>/.git/hooks/pre-commit
  chmod +x <项目根>/.git/hooks/pre-commit

（Windows 下 Git Bash 同样支持；钩子名必须是 `pre-commit`，无 .py 后缀也可，
 Git 会按可执行文件调用。）

行为：
  - 项目无 .workbuddy/harness/module-map.yaml → 放行（不拦截，对应 G2 降级）。
  - 脚本不存在 / 运行失败 → 放行（不阻断正常提交，避免误伤）。
  - 越界 → exit 1，git commit 中止，并打印越界文件清单。
"""

import os
import sys
import subprocess


def main():
    # 找仓库根
    r = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    if r.returncode != 0:
        sys.exit(0)  # 不在 git 仓库，放行
    root = r.stdout.strip()

    here = os.path.dirname(os.path.abspath(__file__))
    script = os.path.join(here, "scope_check.py")
    if not os.path.isfile(script):
        sys.exit(0)  # 脚本缺失，放行（不阻断）

    map_path = os.path.join(root, ".workbuddy", "harness", "module-map.yaml")
    if not os.path.isfile(map_path):
        sys.exit(0)  # 无 map，G2 降级放行

    proc = subprocess.run([sys.executable, script, root])
    sys.exit(proc.returncode)


if __name__ == "__main__":
    main()
