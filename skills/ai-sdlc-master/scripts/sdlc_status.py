#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI SDLC Master — 持久化项目记忆工具（state.json）

这是「多 Agent 整条链路能自动跑、也能隔天从断点续跑」的物理载体。
纯标准库实现，零第三方依赖，克隆即跑。

用法：
  python sdlc_status.py init <项目根> <slug> "<项目名>"
  python sdlc_status.py show <项目根>
  python sdlc_status.py set  <项目根> <phase> <status> [gate]
  python sdlc_status.py path <项目根>          # 仅打印 state.json 绝对路径

state.json 字段契约见 state.schema（同目录）。

phase 取值：prd | dev | qa
status 取值：pending | running | done
gate   取值：pending | confirmed
"""

import sys
import os
import json
import datetime


SCHEMA_VERSION = 1


def migrate(data):
    """把旧/无版本的 state.json 升级到当前 SCHEMA_VERSION。

    升级链可随版本增长追加（v1 → v2 → ...）。返回升级后的 data。
    设计意图：state.schema 里已声明 schema_version，但「有版本号」必须配合
    「能迁移」才有意义——否则升 v2 时旧 state.json 直接崩，与「断点续跑可靠性」
    自相矛盾。
    """
    v = data.get("schema_version", 0)
    if v < 1:
        # v0（无版本，早期草稿）：补全缺失字段并置版本号
        data.setdefault("project", {"name": "", "slug": "", "root": ""})
        data.setdefault("phases", {})
        data.setdefault("current_phase", "prd")
        data.setdefault("updated_at", "")
        data["schema_version"] = SCHEMA_VERSION
    # 未来版本在此追加：elif v < 2: 兼容 v2 字段迁移
    return data


def state_path(root):
    # 项目记忆放在 <项目根>/.workbuddy/sdlc/state.json
    # 与 dev-harness 的治理目录同族（.workbuddy/ 下），属于「项目级持久记忆」
    return os.path.join(root, ".workbuddy", "sdlc", "state.json")


def load(root):
    p = state_path(root)
    if not os.path.exists(p):
        return None
    with open(p, encoding="utf-8") as f:
        data = json.load(f)
    # 版本检查 + 迁移：旧/无版本 state.json 自动升级，避免直接崩
    return migrate(data)


def save(root, data):
    p = state_path(root)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    data["updated_at"] = datetime.datetime.now().isoformat(timespec="seconds")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def init(root, slug, name):
    if load(root):
        print("[sdlc] 已存在 state.json，跳过 init；用 show 查看断点")
        return
    data = {
        "schema_version": 1,
        "project": {
            "name": name,
            "slug": slug,
            "root": os.path.abspath(root),
        },
        "phases": {
            "prd": {
                "status": "pending",
                "gate": "pending",
                "workdir": "prd-work/%s" % slug,
                "outputs": [],
            },
            "dev": {
                "status": "pending",
                "gate": "pending",
                "requirement": "prd-work/%s/04-prd.md" % slug,
                "reports": [],
            },
            "qa": {
                "status": "pending",
                "gate": "pending",
                "workdir": "qa-work/%s" % slug,
                "inputs": [],
            },
        },
        "current_phase": "prd",
        "updated_at": "",
    }
    save(root, data)
    print("[sdlc] 已初始化项目记忆：%s" % state_path(root))
    print("[sdlc] 当前阶段=prd  下一步：派发 PRD phase agent")


def show(root):
    data = load(root)
    if not data:
        print("[sdlc] 暂无项目记忆（未 init 或已清理）")
        return
    print("项目：%s  (slug=%s)" % (data["project"]["name"], data["project"]["slug"]))
    print("当前阶段：%s    更新于：%s" % (data["current_phase"], data["updated_at"]))
    print("阶段进度：")
    for ph, v in data["phases"].items():
        print("  - %s  status=%-8s gate=%s" % (ph.upper().ljust(4), v["status"], v["gate"]))


def set_status(root, phase, status, gate=None):
    data = load(root)
    if not data:
        print("[sdlc] 未找到 state.json，请先 init")
        sys.exit(1)
    if phase not in data["phases"]:
        print("[sdlc] 未知 phase：%s（应为 prd/dev/qa）" % phase)
        sys.exit(1)
    data["phases"][phase]["status"] = status
    if gate:
        data["phases"][phase]["gate"] = gate

    # 自动推进 current_phase：某阶段 done + confirmed → 下一阶段成为当前
    order = ["prd", "dev", "qa"]
    idx = order.index(phase)
    if status == "done" and gate == "confirmed" and idx < 2:
        data["current_phase"] = order[idx + 1]
    elif status in ("running", "pending"):
        data["current_phase"] = phase

    save(root, data)
    tail = ("  gate=%s" % gate) if gate else ""
    print("[sdlc] %s -> status=%s%s" % (phase, status, tail))
    print("[sdlc] 当前阶段=%s" % data["current_phase"])


def main():
    argv = sys.argv[1:]
    if not argv:
        print(__doc__)
        sys.exit(0)
    cmd = argv[0]
    if cmd == "init":
        if len(argv) < 3:
            print("[sdlc] 用法：init <项目根> <slug> \"<项目名>\"")
            sys.exit(1)
        init(argv[1], argv[2], argv[3] if len(argv) > 3 else argv[2])
    elif cmd == "show":
        show(argv[1])
    elif cmd == "set":
        if len(argv) < 4:
            print("[sdlc] 用法：set <项目根> <phase> <status> [gate]")
            sys.exit(1)
        set_status(argv[1], argv[2], argv[3], argv[4] if len(argv) > 4 else None)
    elif cmd == "path":
        print(state_path(argv[1]))
    else:
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
