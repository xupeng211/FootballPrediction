#!/usr/bin/env python3
"""
V8.5 多赛季收割脚本 - 收割 23/24 + 24/25 赛季数据
目标: 500+ 场比赛，消除小样本偏差
"""

import json
import random
import sys
import time
from pathlib import Path

import pandas as pd

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.core.config import get_config
from src.data_access.api_client import get_api_client
from src.data_access.processors.bulletproof_feature_extractor import BulletproofFeatureExtractor
from src.utils import setup_logger


class MultiSeasonHarvester:
    """多赛季数据收割器"""

    # 英超联赛配置
    LEAGUE_ID = "47"
    SEASONS = [
        {"id": "2023/2024", "name": "23/24", "expected_matches": 380},
        {"id": "2024/2025", "name": "24/25", "expected_matches": 380},  # 进行中
    ]

    def __init__(self):
        self.config = get_config()
        self.logger = setup_logger("multi_season_harvest")
        self.api_client = get_api_client()
        self.feature_extractor = BulletproofFeatureExtractor()

        self.all_matches = []
        self.failed_matches = []

        self.logger.info("🚀 V8.5 多赛季收割器初始化")

    def harvest_season(self, season_id: str, season_name: str) -> list:
        """收割单个赛季"""
        self.logger.info(f"📅 开始收割 {season_name} 赛季...")

        try:
            # 获取赛季比赛列表
            matches = self.api_client.get_season_matches(league_id=self.LEAGUE_ID, season=season_id)

            if not matches:
                self.logger.warning(f"⚠️ {season_name} 赛季未获取到比赛")
                return []

            self.logger.info(f"✅ {season_name}: 获取到 {len(matches)} 场已完成比赛")

            season_data = []

            for i, match in enumerate(matches, 1):
                match_id = match["match_id"]
                home_team = match["home_team"]
                away_team = match["away_team"]

                self.logger.info(f"[{season_name}][{i}/{len(matches)}] {home_team} vs {away_team}")

                try:
                    # 获取比赛详情
                    match_data = self.api_client.get_match_details(match_id)
                    if not match_data:
                        raise ValueError("比赛数据为空")

                    # 提取特征
                    features = self.feature_extractor.extract(match_data)
                    if not features:
                        raise ValueError("特征提取失败")

                    # 添加元数据
                    features.update(
                        {
                            "external_id": match_id,
                            "season": season_name,
                            "league_id": self.LEAGUE_ID,
                            "is_real_data": True,
                            "data_source": "fotmob_api",
                        }
                    )

                    season_data.append(features)
                    self.logger.info("  ✅ 成功")

                except Exception as e:
                    self.failed_matches.append(
                        {
                            "match_id": match_id,
                            "season": season_name,
                            "teams": f"{home_team} vs {away_team}",
                            "error": str(e),
                        }
                    )
                    self.logger.warning(f"  ❌ 失败: {e}")

                # 进度报告
                if i % 50 == 0:
                    self.logger.info(f"  📊 {season_name} 进度: {i}/{len(matches)} ({i / len(matches) * 100:.1f}%)")

            return season_data

        except Exception as e:
            self.logger.error(f"❌ 收割 {season_name} 赛季失败: {e}")
            return []

    def run(self) -> bool:
        """运行多赛季收割"""
        self.logger.info("=" * 60)
        self.logger.info("🌐 V8.5 多赛季收割启动")
        self.logger.info("=" * 60)

        for season in self.SEASONS:
            season_data = self.harvest_season(season["id"], season["name"])
            self.all_matches.extend(season_data)

            self.logger.info(f"📊 {season['name']}: 收割 {len(season_data)} 场")
            self.logger.info(f"📊 累计: {len(self.all_matches)} 场")

            # 赛季间休息
            time.sleep(random.uniform(5, 10))

        # 保存数据
        if self.all_matches:
            df = pd.DataFrame(self.all_matches)

            # 按时间排序
            if "match_time" in df.columns:
                df["match_time"] = pd.to_datetime(df["match_time"])
                df = df.sort_values("match_time")

            # 保存
            output_path = self.config.paths.data_dir / "multi_season_v85.csv"
            df.to_csv(output_path, index=False)

            self.logger.info(f"\n✅ 数据已保存: {output_path}")
            self.logger.info(f"  总场次: {len(df)}")
            self.logger.info(f"  特征数: {df.shape[1]}")

            # 保存失败列表
            if self.failed_matches:
                failed_path = self.config.paths.data_dir / "failed_matches_v85.json"
                with open(failed_path, "w", encoding="utf-8") as f:
                    json.dump(self.failed_matches, f, indent=2, ensure_ascii=False)
                self.logger.info(f"  失败记录: {failed_path} ({len(self.failed_matches)} 场)")

            return True

        return False


def main():
    harvester = MultiSeasonHarvester()
    success = harvester.run()

    if success:
        print("\n🎉 多赛季收割完成!")
    else:
        print("\n❌ 收割失败")


if __name__ == "__main__":
    main()
