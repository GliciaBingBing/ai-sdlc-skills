#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""G4 机械快照：在项目根 .workbuddy/harness/snapshots/<id>/ 存一份工作区副本。

独立于 git 历史，不污染提交。由开发 AI 在「认为这轮稳了」的节点调用，
炸了用 rollback.py 一键还原。纯标准库，克隆即跑。

设计取舍（与原手动快照一致，只是把「复制」机械化）：
- 快照只存文件副本，不碰 git 历史、不自动创建 commit。
- AI 不擅自触发回退；回退由用户 / 开发流程在「这轮炸了」时显式调用 rollback.py。
"""
import os
import sys
import json
import shutil
import datetime
import uuid

HARNESS_SUBDIR = os.path.join(".workbuddy", "harness")
SNAP_DIR = "snapshots"
EXCLUDE_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build", ".idea", ".DS_Store", ".workbuddy"}


def snapshot_root(root):
    return os.path.join(root, HARNESS_SUBDIR, SNAP_DIR)


def _is_excluded(rel):
    """rel 是相对 root 的目录路径；返回是否应整体跳过。"""
    # 快照自身所在的目录：.workbuddy/harness/snapshots 及其子目录
    prefix = os.path.join(".workbuddy", "harness", "snapshots")
    if rel == prefix or rel.startswith(prefix + os.sep):
        return True
    return False


def make_snapshot(root, label=None):
    git_commit = ""
    try:
        import subprocess
        r = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root,
                           capture_output=True, text=True)
        if r.returncode == 0:
            git_commit = r.stdout.strip()
    except Exception:
        pass

    sid = "snap-" + datetime.datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:6]
    dest = os.path.join(snapshot_root(root), sid)
    os.makedirs(dest, exist_ok=True)

    count = 0
    for dirpath, dirnames, filenames in os.walk(root):
        rel = os.path.relpath(dirpath, root)
        # 在 walk 内即时剪枝：排除大目录 / 缓存 / 快照自身
        for e in list(dirnames):
            if e in EXCLUDE_DIRS:
                dirnames.remove(e)
        if _is_excluded(rel):
            dirnames[:] = []
            continue
        for fn in filenames:
            if fn.endswith(".pyc"):
                continue
            src = os.path.join(dirpath, fn)
            tgt = os.path.join(dest, rel, fn) if rel != "." else os.path.join(dest, fn)
            os.makedirs(os.path.dirname(tgt), exist_ok=True)
            shutil.copy2(src, tgt)
            count += 1

    manifest = {
        "snapshot_id": sid,
        "created_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "git_commit": git_commit,
        "label": label or "",
        "root": os.path.abspath(root),
        "file_count": count,
    }
    with open(os.path.join(dest, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    return manifest


def main():
    argv = sys.argv[1:]
    root = "."
    label = None
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--label" and i + 1 < len(argv):
            label = argv[i + 1]
            i += 1
        elif not a.startswith("-"):
            root = a
        i += 1
    root = os.path.abspath(root)
    if not os.path.isdir(root):
        print("ERROR root 不存在: %s" % root, file=sys.stderr)
        sys.exit(2)

    m = make_snapshot(root, label)
    print(json.dumps({
        "action": "snapshot",
        "snapshot_id": m["snapshot_id"],
        "file_count": m["file_count"],
        "git_commit": m["git_commit"],
    }, ensure_ascii=False))
    sys.exit(0)


if __name__ == "__main__":
    main()
