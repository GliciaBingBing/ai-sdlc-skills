"""
项目工作目录检测脚本

用法：
  python detect_workspace.py <项目根目录> [--json]

检测优先级：
  1. .cloud 或 .agent 目录存在 → 以此为工作区根目录
  2. .workbuddy 中有 workspace_dir 配置 → 使用配置值
  3. 都没有 → 返回项目根目录本身

这是过程产物的门禁——项目指定了操作范围，所有中间文件必须在这个范围内。
"""

import os
import sys
import json


def detect(project_root):
    """检测项目的工作目录约束"""
    # 1. .cloud 目录
    cloud_dir = os.path.join(project_root, ".cloud")
    if os.path.isdir(cloud_dir):
        return cloud_dir, ".cloud/"

    # 2. .agent 目录
    agent_dir = os.path.join(project_root, ".agent")
    if os.path.isdir(agent_dir):
        return agent_dir, ".agent/"

    # 3. .workbuddy 配置
    wb_dir = os.path.join(project_root, ".workbuddy")
    if os.path.isdir(wb_dir):
        config_path = os.path.join(wb_dir, "config.json")
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                ws = config.get("workspace_dir", "")
                if ws:
                    full = os.path.join(project_root, ws)
                    os.makedirs(full, exist_ok=True)
                    return full, ".workbuddy/config.json"
            except (json.JSONDecodeError, KeyError):
                pass
        # .workbuddy 目录存在但无配置 → 以此为工作区
        return wb_dir, ".workbuddy/"

    # 4. 无约束 → 项目根目录
    return project_root, "project root (无约束)"


def main():
    project_root = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
    output_json = "--json" in sys.argv

    ws_dir, source = detect(project_root)

    if output_json:
        print(json.dumps({"workspace": ws_dir, "source": source}, ensure_ascii=False))
    else:
        print(f"工作区: {ws_dir}")
        print(f"来源: {source}")


if __name__ == "__main__":
    main()
