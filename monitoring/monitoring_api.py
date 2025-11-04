#!/usr/bin/env python3
"""
监控数据API - 为监控面板提供数据接口
"""

import json
import sys
import os
from pathlib import Path
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.insert(0, ".")


def load_validation_data():
    """加载最新验证数据"""
    try:
        with open("validation_report.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return None


def load_maintenance_logs():
    """加载维护日志"""
    log_file = Path("maintenance_logs/maintenance_log.json")
    if log_file.exists():
        try:
            with open(log_file, "r", encoding="utf-8") as f:
                logs = json.load(f)
            return logs[-5:]  # 返回最近5条日志
        except Exception:
            pass
    return []


def get_system_status():
    """获取系统状态数据"""
    validation_data = load_validation_data()
    maintenance_logs = load_maintenance_logs()

    if validation_data and "results" in validation_data:
        results = validation_data["results"]

        status_data = {
            "overall_status": results.get("overall_status", {}).get("status", "未知"),
            "health_score": results.get("overall_status", {}).get("score", "N/A"),
            "tests": results.get("tests", {}),
            "code_quality": results.get("code_quality", {}),
            "coverage": results.get("coverage", {}),
            "last_updated": validation_data.get(
                "validation_time", datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ),
        }
    else:
        status_data = {
            "overall_status": "❓ 未知",
            "health_score": "N/A",
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

    # 添加维护日志信息
    if maintenance_logs:
        last_maintenance = maintenance_logs[-1]
        status_data["last_maintenance"] = last_maintenance.get("timestamp", "未知")
        status_data["maintenance_actions"] = len(last_maintenance.get("actions_performed",
    []))
    else:
        status_data["last_maintenance"] = "无记录"
        status_data["maintenance_actions"] = 0

    return status_data


def main():
    """主函数 - 输出JSON格式的状态数据"""
    if len(sys.argv) > 1 and sys.argv[1] == "--json":
        status = get_system_status()
        print(json.dumps(status, indent=2, ensure_ascii=False))
    else:
        print("使用 --json 参数输出JSON格式数据")


if __name__ == "__main__":
    main()
