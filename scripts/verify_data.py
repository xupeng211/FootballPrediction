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
    print("❌ 需要安装 requests 库: pip install requests")
    sys.exit(1)

BASE_URL = "http://localhost:8000"

def check_api_health():
    """检查API健康状态"""
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            health_data = response.json()
            print("✅ 后端API健康状态:")
            print(f"   状态: {health_data['status']}")
            print(f"   版本: {health_data['version']}")
            print(f"   服务: {health_data['service']}")
            return True
    except Exception as e:
        print(f"❌ 无法连接到后端API: {e}")
    return False

def check_matches():
    """检查比赛数据"""
    try:
        response = requests.get(f"{BASE_URL}/api/v1/matches")
        if response.status_code == 200:
            matches_data = response.json()
            matches = matches_data.get("matches", [])

            print(f"\n✅ 比赛数据 (共 {len(matches)} 场):")

            status_count = {}
            for i, match in enumerate(matches[:3], 1):  # 只显示前3场
                status = match.get("status", "unknown")
                status_count[status] = status_count.get(status, 0) + 1

                home_team = match.get("home_team", {})
                away_team = match.get("away_team", {})
                home_name = home_team.get("name", "Unknown")
                away_name = away_team.get("name", "Unknown")

                print(f"   {i}. {home_name} vs {away_name}")
                print(f"      状态: {status}")
                print(f"      日期: {match.get('date', 'N/A')}")

                if status == "finished" and "home_score" in match:
                    print(f"      比分: {match.get('home_score', 0)} - {match.get('away_score', 0)}")

                print()

            print(f"   状态统计: {status_count}")
            return len(matches) > 0

    except Exception as e:
        print(f"❌ 获取比赛数据失败: {e}")
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
                print("\n⚠️ 没有比赛数据，无法检查预测")
                return False

            print(f"\n✅ 检查预测数据:")
            predictions_found = 0

            for match in matches[:3]:  # 检查前3场比赛的预测
                match_id = match.get("id")
                if match_id:
                    pred_response = requests.get(f"{BASE_URL}/api/v1/predictions/match/{match_id}")
                    if pred_response.status_code == 200:
                        predictions = pred_response.json()
                        if predictions:
                            predictions_found += len(predictions)

                            home_team = match.get("home_team", {}).get("name", "Unknown")
                            away_team = match.get("away_team", {}).get("name", "Unknown")

                            print(f"   比赛 {match_id}: {home_team} vs {away_team}")
                            for pred in predictions:
                                print(f"     预测: {pred.get('predicted_result', 'N/A')}")
                                print(f"     置信度: {pred.get('confidence', 0):.2f}")
                            print()

            print(f"   预测总数: {predictions_found}")
            return predictions_found > 0

    except Exception as e:
        print(f"❌ 获取预测数据失败: {e}")
        return False

def check_frontend():
    """检查前端状态"""
    try:
        response = requests.get("http://localhost:3000")
        if response.status_code == 200:
            print("✅ 前端服务正常运行 (http://localhost:3000)")
            return True
        else:
            print(f"⚠️ 前端服务异常: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 前端服务无法访问: {e}")
        print("请确保前端开发服务器正在运行:")
        print("   cd frontend && npm start")
        return False

def main():
    """主函数"""
    print("🔍 足球预测系统数据验证")
    print("="*50)

    # 检查各个组件
    api_ok = check_api_health()

    if api_ok:
        matches_ok = check_matches()
        predictions_ok = check_predictions()

        frontend_ok = check_frontend()

        print("\n" + "="*50)
        print("📊 验证结果摘要:")
        print(f"   后端API: {'✅ 正常' if api_ok else '❌ 异常'}")
        print(f"   比赛数据: {'✅ 有数据' if matches_ok else '❌ 无数据'}")
        print(f"   预测数据: {'✅ 有数据' if predictions_ok else '❌ 无数据'}")
        print(f"   前端服务: {'✅ 正常' if frontend_ok else '❌ 异常'}")

        if api_ok and matches_ok and frontend_ok:
            print("\n🎉 系统数据验证通过！")
            print("💡 建议操作:")
            print("   1. 打开浏览器访问: http://localhost:3000")
            print("   2. 如果页面仍然空白，尝试强制刷新 (Ctrl+F5)")
            print("   3. 检查浏览器控制台是否有错误信息")
        else:
            print("\n⚠️ 系统存在问题，请检查上述异常项")

        return api_ok and matches_ok and frontend_ok
    else:
        print("\n❌ 后端API不可用，无法继续验证")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)