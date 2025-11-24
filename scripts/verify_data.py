#!/usr/bin/env python3
"""
数据验证脚本 - 检查现有数据状态
Data Verification Script - Check existing data status
"""

import json
import sys
from datetime import datetime

try:
    import requests
except ImportError:
    sys.exit(1)

BASE_URL = "http://localhost:8000"


def check_api_health():
    """检查API健康状态"""
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            response.json()
            return True
    except Exception:
        pass
    return False


def check_matches():
    """检查比赛数据"""
    try:
        response = requests.get(f"{BASE_URL}/api/v1/matches")
        if response.status_code == 200:
            matches_data = response.json()
            matches = matches_data.get("matches", [])

            status_count = {}
            for _i, match in enumerate(matches[:3], 1):  # 只显示前3场
                status = match.get("status", "unknown")
                status_count[status] = status_count.get(status, 0) + 1

                home_team = match.get("home_team", {})
                away_team = match.get("away_team", {})
                home_team.get("name", "Unknown")
                away_team.get("name", "Unknown")

                if status == "finished" and "home_score" in match:
                    pass

            return len(matches) > 0

    except Exception:
        return False


def check_predictions():
    """检查预测数据"""
    try:
        # 检查几个具体比赛的预测
        matches_response = requests.get(f"{BASE_URL}/api/v1/matches")
        if matches_response.status_code == 200:
            matches_data = matches_response.json()
            matches = matches_data.get("matches", [])

            if not matches:
                return False

            predictions_found = 0

            for match in matches[:3]:  # 检查前3场比赛的预测
                match_id = match.get("id")
                if match_id:
                    pred_response = requests.get(
                        f"{BASE_URL}/api/v1/predictions/match/{match_id}"
                    )
                    if pred_response.status_code == 200:
                        predictions = pred_response.json()
                        if predictions:
                            predictions_found += len(predictions)

                            match.get("home_team", {}).get("name", "Unknown")
                            match.get("away_team", {}).get("name", "Unknown")

                            for _pred in predictions:
                                pass

            return predictions_found > 0

    except Exception:
        return False


def check_frontend():
    """检查前端状态"""
    try:
        response = requests.get("http://localhost:3000")
        if response.status_code == 200:
            return True
        else:
            return False
    except Exception:
        return False


def main():
    """主函数"""

    # 检查各个组件
    api_ok = check_api_health()

    if api_ok:
        matches_ok = check_matches()
        check_predictions()

        frontend_ok = check_frontend()

        if api_ok and matches_ok and frontend_ok:
            pass
        else:
            pass

        return api_ok and matches_ok and frontend_ok
    else:
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
