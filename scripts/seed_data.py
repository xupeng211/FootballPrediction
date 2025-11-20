#!/usr/bin/env python3
"""
足球预测系统数据播种脚本
Football Prediction System Data Seeding Script

通过调用后端API向数据库注入模拟数据
"""

import json
import sys
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional

try:
    import requests
except ImportError:
    print("❌ 错误: 需要安装 requests 库")
    print("请运行: pip install requests")
    sys.exit(1)

# API配置
BASE_URL = "http://localhost:8000"
API_BASE = f"{BASE_URL}/api/v1"

class DataSeeder:
    """数据播种器"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        self.created_teams = []
        self.created_matches = []
        self.created_predictions = []

    def check_api_health(self) -> bool:
        """检查API健康状态"""
        try:
            response = self.session.get(f"{BASE_URL}/health")
            if response.status_code == 200:
                print("✅ 后端API连接正常")
                return True
            else:
                print(f"❌ 后端API异常: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ 无法连接到后端API: {e}")
            print("请确保后端服务运行在 http://localhost:8000")
            return False

    def create_team(self, name: str, short_name: str, country: str = "England") -> Optional[Dict]:
        """创建球队"""
        try:
            team_data = {
                "name": name,
                "short_name": short_name,
                "country": country,
                "founded": 1886,
                "stadium": f"{name} Stadium",
                "city": "London" if name in ["Arsenal", "Chelsea"] else "Manchester"
            }

            response = self.session.post(f"{API_BASE}/teams", json=team_data)
            if response.status_code in [200, 201]:
                team = response.json()
                print(f"✅ 创建球队成功: {name}")
                return team
            else:
                print(f"⚠️ 创建球队失败 {name}: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            print(f"❌ 创建球队异常 {name}: {e}")
            return None

    def create_match(self, home_team_id: int, away_team_id: int, status: str,
                    home_score: Optional[int] = None, away_score: Optional[int] = None,
                    match_date: Optional[str] = None) -> Optional[Dict]:
        """创建比赛"""
        try:
            if not match_date:
                if status == "finished":
                    match_date = (datetime.now() - timedelta(days=1)).isoformat()
                elif status == "live":
                    match_date = (datetime.now() - timedelta(hours=2)).isoformat()
                else:  # upcoming
                    match_date = (datetime.now() + timedelta(days=2)).isoformat()

            match_data = {
                "home_team_id": home_team_id,
                "away_team_id": away_team_id,
                "match_date": match_date,
                "status": status,
                "venue": "Premier League Stadium",
                "league": "英超"
            }

            if home_score is not None and away_score is not None:
                match_data["home_score"] = home_score
                match_data["away_score"] = away_score

            response = self.session.post(f"{API_BASE}/matches", json=match_data)
            if response.status_code in [200, 201]:
                match = response.json()
                print(f"✅ 创建比赛成功: {status}")
                return match
            else:
                print(f"⚠️ 创建比赛失败: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            print(f"❌ 创建比赛异常: {e}")
            return None

    def create_prediction(self, match_id: int, prediction: str, confidence: float) -> Optional[Dict]:
        """创建预测"""
        try:
            # 根据预测类型生成概率
            if prediction == "home_win":
                home_prob = 0.65 + (confidence - 0.7) * 0.5
                away_prob = 0.15 - (confidence - 0.7) * 0.3
                draw_prob = 1.0 - home_prob - away_prob
            elif prediction == "away_win":
                away_prob = 0.65 + (confidence - 0.7) * 0.5
                home_prob = 0.15 - (confidence - 0.7) * 0.3
                draw_prob = 1.0 - home_prob - away_prob
            else:  # draw
                draw_prob = 0.35 + (confidence - 0.7) * 0.4
                home_prob = 0.3 - (confidence - 0.7) * 0.2
                away_prob = 1.0 - home_prob - draw_prob

            # 确保概率有效
            home_prob = max(0.05, min(0.90, home_prob))
            away_prob = max(0.05, min(0.90, away_prob))
            draw_prob = max(0.05, min(0.90, draw_prob))

            # 归一化
            total = home_prob + away_prob + draw_prob
            home_prob /= total
            away_prob /= total
            draw_prob /= total

            prediction_data = {
                "match_id": match_id,
                "prediction": prediction,
                "confidence": confidence,
                "home_win_prob": home_prob,
                "draw_prob": draw_prob,
                "away_win_prob": away_prob,
                "ev": 0.05 if confidence > 0.75 else -0.02,  # 期望收益
                "suggestion": "推荐投注" if confidence > 0.75 else "观望"
            }

            response = self.session.post(f"{API_BASE}/predictions", json=prediction_data)
            if response.status_code in [200, 201]:
                prediction = response.json()
                print(f"✅ 创建预测成功: {prediction} (置信度: {confidence:.2f})")
                return prediction
            else:
                print(f"⚠️ 创建预测失败: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            print(f"❌ 创建预测异常: {e}")
            return None

    def seed_teams(self) -> bool:
        """播种球队数据"""
        print("\n=== 创建球队数据 ===")

        teams_data = [
            {"name": "Arsenal", "short_name": "ARS", "country": "England"},
            {"name": "Chelsea", "short_name": "CHE", "country": "England"},
            {"name": "Liverpool", "short_name": "LIV", "country": "England"},
            {"name": "Manchester City", "short_name": "MCI", "country": "England"},
            {"name": "Manchester United", "short_name": "MUN", "country": "England"},
            {"name": "Tottenham Hotspur", "short_name": "TOT", "country": "England"}
        ]

        success_count = 0
        for team_info in teams_data:
            team = self.create_team(**team_info)
            if team:
                self.created_teams.append(team)
                success_count += 1
            time.sleep(0.1)  # 避免请求过快

        print(f"球队创建完成: {success_count}/{len(teams_data)}")
        return success_count > 0

    def seed_matches(self) -> bool:
        """播种比赛数据"""
        print("\n=== 创建比赛数据 ===")

        if len(self.created_teams) < 2:
            print("❌ 球队数量不足，无法创建比赛")
            return False

        matches_data = [
            {
                "home_idx": 0, "away_idx": 1, "status": "finished",
                "home_score": 2, "away_score": 1,
                "description": "已结束比赛"
            },
            {
                "home_idx": 2, "away_idx": 3, "status": "live",
                "home_score": 1, "away_score": 1,
                "description": "进行中比赛"
            },
            {
                "home_idx": 4, "away_idx": 5, "status": "upcoming",
                "home_score": None, "away_score": None,
                "description": "即将开始比赛"
            }
        ]

        success_count = 0
        for match_info in matches_data:
            home_team = self.created_teams[match_info["home_idx"]]
            away_team = self.created_teams[match_info["away_idx"]]

            match = self.create_match(
                home_team_id=home_team.get("id", 1),
                away_team_id=away_team.get("id", 2),
                status=match_info["status"],
                home_score=match_info["home_score"],
                away_score=match_info["away_score"]
            )
            if match:
                self.created_matches.append(match)
                success_count += 1
            time.sleep(0.1)

        print(f"比赛创建完成: {success_count}/{len(matches_data)}")
        return success_count > 0

    def seed_predictions(self) -> bool:
        """播种预测数据"""
        print("\n=== 创建预测数据 ===")

        if not self.created_matches:
            print("❌ 比赛数量不足，无法创建预测")
            return False

        predictions_data = [
            {"match_idx": 0, "prediction": "home_win", "confidence": 0.85},
            {"match_idx": 1, "prediction": "draw", "confidence": 0.72},
            {"match_idx": 2, "prediction": "away_win", "confidence": 0.68},
            {"match_idx": 0, "prediction": "home_win", "confidence": 0.78},  # 第二个预测
        ]

        success_count = 0
        for pred_info in predictions_data:
            if pred_info["match_idx"] < len(self.created_matches):
                match = self.created_matches[pred_info["match_idx"]]
                prediction = self.create_prediction(
                    match_id=match.get("id", 1),
                    prediction=pred_info["prediction"],
                    confidence=pred_info["confidence"]
                )
                if prediction:
                    self.created_predictions.append(prediction)
                    success_count += 1
                time.sleep(0.1)

        print(f"预测创建完成: {success_count}/{len(predictions_data)}")
        return success_count > 0

    def run(self) -> bool:
        """运行完整的数据播种流程"""
        print("🚀 开始数据播种...")

        # 检查API健康状态
        if not self.check_api_health():
            return False

        # 播种球队数据
        if not self.seed_teams():
            print("❌ 球队数据播种失败")
            return False

        # 播种比赛数据
        if not self.seed_matches():
            print("❌ 比赛数据播种失败")
            return False

        # 播种预测数据
        if not self.seed_predictions():
            print("❌ 预测数据播种失败")
            return False

        # 输出结果摘要
        print("\n" + "="*50)
        print("📊 数据播种完成摘要:")
        print(f"  球队数量: {len(self.created_teams)}")
        print(f"  比赛数量: {len(self.created_matches)}")
        print(f"  预测数量: {len(self.created_predictions)}")
        print("="*50)
        print("✅ 数据注入完成！")
        print("🔄 请刷新前端页面查看效果")

        return True

def main():
    """主函数"""
    try:
        seeder = DataSeeder()
        success = seeder.run()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️ 用户中断播种过程")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 播种过程出现异常: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()