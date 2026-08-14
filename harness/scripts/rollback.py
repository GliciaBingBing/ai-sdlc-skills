#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""G4 机械回退：把某快照内容覆盖回工作区（版本级还原）。

不自动删除工作区中「快照没有」的文件（安全）；仅还原快照内文件并报告差异。
AI 不擅自调用——由用户 / 开发流程在「这轮炸了」时显式触发。纯标准库。

用法：
  rollback.py <root>                 # 回退到最新一份快照
  rollback.py <root> --to <id>       # 回退到指定快照
  rollback.py <root> --list          # 列出全部快照
  rollback.py <root> --dry-run       # 预演，不改任何文件
"""
import os
import sys
import json
import shutil

HARNESS_SUBDIR = os.path.join(".workbuddy", "harness")
SNAP_DIR = "snapshots"


def snapshot_root(root):
    return os.path.join(root, HARNESS_SUBDIR, SNAP_DIR)


def list_snapshots(root):
    d = snapshot_root(root)
    if not os.path.isdir(d):
        return []
    out = []
    for name in sorted(os.listdir(d)):
        m = os.path.join(d, name, "manifest.json")
        if os.path.isfile(m):
            try:
                meta = json.load(open(m, encoding="utf-8"))
                out.append((name, meta.get("created_at", ""), meta.get("label", "")))
            except Exception:
                out.append((name, "", ""))
    return out


def _collect_snap_files(src):
    files = []
    for dp, _, fns in os.walk(src):
        for fn in fns:
            if fn == "manifest.json":
                continue
            full = os.path.join(dp, fn)
            rel = os.path.relpath(full, src)
            files.append(rel)
    return files


def rollback(root, snap_id=None, dry_run=False, list_only=False):
    if list_only:
        snaps = list_snapshots(root)
        print(json.dumps({
            "snapshots": [{"id": n, "created_at": c, "label": l} for n, c, l in snaps]
        }, ensure_ascii=False))
        return 0

    d = snapshot_root(root)
    if not os.path.isdir(d):
        print("ERROR 没有快照目录，无法回退", file=sys.stderr)
        sys.exit(1)

    if snap_id is None:
        snaps = list_snapshots(root)
        if not snaps:
            print("ERROR 无可用快照，请先存储快照", file=sys.stderr)
            sys.exit(1)
        snap_id = snaps[-1][0]  # 最新

    src = os.path.join(d, snap_id)
    if not os.path.isdir(src):
        print("ERROR 快照不存在: %s" % snap_id, file=sys.stderr)
        sys.exit(1)

    snap_files = _collect_snap_files(src)
    restored, overwritten = [], []
    for rel in snap_files:
        tgt = os.path.join(root, rel)
        sfull = os.path.join(src, rel)
        if os.path.exists(tgt):
            try:
                with open(sfull, "rb") as a, open(tgt, "rb") as b:
                    same = a.read() == b.read()
            except Exception:
                same = False
            if same:
                continue
            overwritten.append(rel)
        if dry_run:
            restored.append(rel)
            continue
        os.makedirs(os.path.dirname(tgt), exist_ok=True)
        shutil.copy2(sfull, tgt)
        restored.append(rel)

    result = {
        "action": "rollback",
        "snapshot_id": snap_id,
        "restored": len(restored),
        "overwritten": len(overwritten),
        "dry_run": dry_run,
    }
    print(json.dumps(result, ensure_ascii=False))
    return 0


def main():
    argv = sys.argv[1:]
    root = "."
    snap_id = None
    dry_run = False
    list_only = False
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--list":
            list_only = True
        elif a == "--dry-run":
            dry_run = True
        elif a == "--to" and i + 1 < len(argv):
            snap_id = argv[i + 1]
            i += 1
        elif not a.startswith("-"):
            root = a
        i += 1
    root = os.path.abspath(root)
    if not os.path.isdir(root):
        print("ERROR root 不存在", file=sys.stderr)
        sys.exit(2)
    sys.exit(rollback(root, snap_id, dry_run, list_only))


if __name__ == "__main__":
    main()
