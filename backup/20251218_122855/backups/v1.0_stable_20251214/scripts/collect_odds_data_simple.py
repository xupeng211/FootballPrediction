#!/usr/bin/env python3
"""
简化版赔率数据集成脚本 - 模拟赔率数据
Simplified Odds Data Collection Script - Mock odds data

演示赔率数据集成功能，为现有比赛添加模拟赔率数据。
"""

import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from loguru import logger

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker


@dataclass
class OddsCollectionConfig:
    """赔率收集配置"""
    limit_matches: Optional[int] = None
    dry_run: bool = False


@dataclass
class CollectionStats:
    """收集统计信息"""
    total_processed: int = 0
    successful_updates: int = 0
    failed_updates: int = 0
    start_time: datetime = None

    def __post_init__(self):
        if self.start_time is None:
            self.start_time = datetime.now()

    @property
    def success_rate(self) -> float:
        """成功率"""
        return (self.successful_updates / max(self.total_processed, 1)) * 100

    @property
    def elapsed_time(self) -> float:
        """已用时间（秒）"""
        return (datetime.now() - self.start_time).total_seconds()


class SimpleOddsCollector:
    """简化版赔率数据收集器"""

    def __init__(self, config: Optional[OddsCollectionConfig] = None):
        self.config = config or OddsCollectionConfig()
        self.stats = CollectionStats()

        # 初始化数据库连接
        self._engine = create_engine("sqlite:///data/football_prediction.db")
        self._SessionLocal = sessionmaker(bind=self._engine)

        logger.info(f"SimpleOddsCollector initialized with config: {self.config}")

    def get_matches_to_process(self) -> List[Tuple[str, str]]:
        """获取需要处理赔率的比赛列表"""
        logger.info("Fetching matches that need odds data...")

        with self._SessionLocal() as session:
            query = text("""
                SELECT
                    m.id,
                    m.home_win_odds,
                    m.draw_odds,
                    m.away_win_odds,
                    t1.name as home_team_name,
                    t2.name as away_team_name,
                    m.match_date,
                    m.status
                FROM matches m
                JOIN teams t1 ON m.home_team_id = t1.id
                JOIN teams t2 ON m.away_team_id = t2.id
                WHERE m.fotmob_id IS NOT NULL
                ORDER BY m.match_date DESC
            """)

            matches = []
            for row in session.execute(query).fetchall():
                match_id = row[0]
                home_odds = row[1]
                draw_odds = row[2]
                away_odds = row[3]
                home_team = row[4]
                away_team = row[5]

                # 判断是否需要更新赔率数据：缺少赔率数据的比赛
                needs_update = (
                    home_odds is None or draw_odds is None or away_odds is None
                )

                if needs_update:
                    match_info = f"{home_team} vs {away_team}"
                    matches.append((match_id, match_info))

            # 限制处理数量
            if self.config.limit_matches:
                matches = matches[:self.config.limit_matches]

            logger.info(f"Found {len(matches)} matches that need odds data processing")
            return matches

    def generate_mock_odds(self, home_team: str, away_team: str) -> Dict[str, float]:
        """
        生成模拟的赔率数据
        基于球队名称生成合理的赔率
        """
        import random

        # 基于球队名称的简单赔率生成逻辑
        # 实际项目中应该使用更复杂的算法

        # 随机生成基础赔率，确保主胜 < 平局 < 客胜
        base_home = random.uniform(1.8, 3.5)
        base_draw = random.uniform(2.5, 4.0)
        base_away = random.uniform(3.0, 6.0)

        # 确保赔率的合理性
        # 计算总和来验证
        total = 1/base_home + 1/base_draw + 1/base_away
        if total < 0.8:  # 总和太低，降低赔率
            base_home *= 0.8
            base_draw *= 0.8
            base_away *= 0.8
        elif total > 1.2:  # 总和太高，提高赔率
            base_home *= 1.2
            base_draw *= 1.2
            base_away *= 1.2

        return {
            "home_win": round(base_home, 2),
            "draw": round(base_draw, 2),
            "away_win": round(base_away, 2),
        }

    def process_match_odds(self, match_id: str, match_info: str) -> Tuple[bool, str]:
        """处理单个比赛的赔率数据"""
        try:
            logger.debug(f"Processing odds for match: {match_info}")

            # 提取主客队名称
            home_team, away_team = match_info.split(" vs ")

            # 生成模拟赔率数据
            odds_data = self.generate_mock_odds(home_team, away_team)

            # 更新数据库
            success = self._update_odds_in_db(match_id, odds_data)
            if success:
                success_msg = (
                    f"Updated odds for match {match_info}: "
                    f"{odds_data['home_win']}-{odds_data['draw']}-{odds_data['away_win']}"
                )
                logger.info(success_msg)
                return True, success_msg
            else:
                return False, "Failed to update odds data"

        except Exception as e:
            error_msg = f"Error processing odds for match {match_id}: {str(e)}"
            logger.exception(error_msg)
            return False, error_msg

    def _update_odds_in_db(self, match_id: str, odds_data: Dict) -> bool:
        """更新数据库中的赔率数据"""
        try:
            with self._SessionLocal() as session:
                result = session.execute(
                    text("""
                        UPDATE matches
                        SET home_win_odds = :home_win,
                            draw_odds = :draw,
                            away_win_odds = :away_win,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = :match_id
                    """),
                    {
                        "home_win": odds_data.get('home_win'),
                        "draw": odds_data.get('draw'),
                        "away_win": odds_data.get('away_win'),
                        "match_id": match_id
                    }
                )

                session.commit()
                return result.rowcount > 0

        except Exception as e:
            logger.error(f"Failed to update odds in database: {e}")
            return False

    def run_collection(self) -> CollectionStats:
        """运行赔率数据收集主流程"""
        logger.info("Starting odds data collection (simplified)...")
        self.stats.start_time = datetime.now()

        try:
            # 获取需要处理的比赛
            matches = self.get_matches_to_process()
            if not matches:
                logger.info("No matches need odds data processing")
                return self.stats

            logger.info(f"Processing {len(matches)} matches for odds data")

            # 处理每场比赛的赔率
            for i, (match_id, match_info) in enumerate(matches):
                try:
                    success, message = self.process_match_odds(match_id, match_info)
                    self.stats.total_processed += 1

                    if success:
                        self.stats.successful_updates += 1
                        logger.debug(f"Success {i+1}/{len(matches)}: {message}")
                    else:
                        self.stats.failed_updates += 1
                        logger.warning(f"Failed {i+1}/{len(matches)}: {message}")

                    # 定期记录进度
                    if self.stats.total_processed % 10 == 0:
                        logger.info(
                            f"Progress: {self.stats.total_processed}/{len(matches)} "
                            f"(Success rate: {self.stats.success_rate:.1f}%)"
                        )

                except Exception as e:
                    logger.error(f"Error processing match {i+1}: {e}")
                    self.stats.failed_updates += 1
                    self.stats.total_processed += 1

        except Exception as e:
            logger.error(f"Fatal error in odds collection process: {e}")
            raise

        # 最终统计
        logger.info(
            f"Odds data collection completed!\n"
            f"Statistics:\n"
            f"  Total processed: {self.stats.total_processed}\n"
            f"  Successful: {self.stats.successful_updates}\n"
            f"  Failed: {self.stats.failed_updates}\n"
            f"  Success rate: {self.stats.success_rate:.2f}%\n"
            f"  Elapsed time: {self.stats.elapsed_time:.2f} seconds"
        )

        return self.stats


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="简化版赔率数据收集脚本")
    parser.add_argument("--limit", "-l", type=int, help="限制处理比赛数量")
    parser.add_argument("--dry-run", "-d", action="store_true", help="只记录不实际写入数据库")

    args = parser.parse_args()

    # 配置收集参数
    config = OddsCollectionConfig(
        limit_matches=args.limit,
        dry_run=args.dry_run,
    )

    # 运行收集
    collector = SimpleOddsCollector(config)

    try:
        stats = collector.run_collection()
        print("\n🎉 Odds data collection completed!")
        print("📊 Statistics:")
        print(f"   Total processed: {stats.total_processed}")
        print(f"   Successful: {stats.successful_updates}")
        print(f"   Failed: {stats.failed_updates}")
        print(f"   Success rate: {stats.success_rate:.2f}%")
        print(f"   Elapsed time: {stats.elapsed_time:.2f} seconds")

    except KeyboardInterrupt:
        print("\n⏹️ Odds data collection interrupted by user")
    except Exception as e:
        print(f"\n❌ Odds data collection failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()