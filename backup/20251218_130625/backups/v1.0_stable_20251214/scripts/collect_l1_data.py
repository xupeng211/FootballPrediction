#!/usr/bin/env python3
"""
L1数据收集脚本 - 同步简化版 (修复版)
L1 Data Collection Script - Synchronous Simplified Version (Fixed)
"""

import sys
import requests
import urllib.parse
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

from loguru import logger

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.database.repositories import MatchRepository, LeagueRepository, TeamRepository
from src.utils.normalizer import team_standardizer, league_standardizer


class L1DataCollector:
    """L1数据收集器 - 同步版本"""

    def __init__(self, league_id: str = "47", days_back: int = 600, days_ahead: int = 100):
        self.league_id = league_id
        self.days_back = days_back
        self.days_ahead = days_ahead
        self.base_url = "https://www.fotmob.com/api"
        self.session = requests.Session()

        # 设置请求头
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
        })

        logger.info(f"L1DataCollector initialized for league {league_id}, past {days_back} days, future {days_ahead} days")

    def fetch_league_matches(self) -> List[Dict]:
        """从FotMob API获取联赛赛程数据"""
        logger.info(f"Fetching Premier League (ID: {self.league_id}) matches")

        import urllib.request
        import json

        url = f"{self.base_url}/leagues?id={self.league_id}&season=2024/2025"

        try:
            logger.debug(f"Making request to {url}")

            # 使用urllib以避免requests的压缩问题
            req = urllib.request.Request(url)
            req.add_header('User-Agent', 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36')
            req.add_header('Accept', 'application/json, text/plain, */*')
            req.add_header('Accept-Language', 'en-US,en;q=0.9')

            with urllib.request.urlopen(req, timeout=30) as response:
                data = json.loads(response.read().decode('utf-8'))

            logger.info(f"Successfully fetched data from FotMob API")

            return self._extract_matches_from_response(data)

        except urllib.error.URLError as e:
            logger.error(f"Request failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error fetching matches: {e}")
            raise

    def _extract_matches_from_response(self, data: Dict) -> List[Dict]:
        """从API响应中提取比赛数据 - 修复比分解析问题"""
        matches = []

        # 检查fixtures数据（新的API结构）
        if 'fixtures' in data and 'allMatches' in data['fixtures']:
            all_matches = data['fixtures']['allMatches']
            logger.info(f"Found {len(all_matches)} matches in fixtures.allMatches section")
        # 兼容旧的API结构
        elif 'matches' in data and 'allMatches' in data['matches']:
            all_matches = data['matches']['allMatches']
            logger.info(f"Found {len(all_matches)} matches in matches.allMatches section")
        else:
            logger.warning("No matches found in API response")
            return matches

        # 计算时间范围 - 使用UTC时区以匹配API返回的时间格式
        from datetime import timezone
        now = datetime.now(timezone.utc)
        date_from = now - timedelta(days=self.days_back)
        date_to = now + timedelta(days=self.days_ahead)
        logger.info(f"Date range: {date_from} to {date_to} (current: {now})")

        processed_count = 0
        score_fix_count = 0
        for i, match in enumerate(all_matches):
            if not isinstance(match, dict):
                continue

            match_time_str = match.get('status', {}).get('utcTime')
            if not match_time_str:
                continue

            try:
                match_time = datetime.fromisoformat(match_time_str.replace('Z', '+00:00'))
            except:
                logger.debug(f"Failed to parse time: {match_time_str}")
                continue

            # 临时：只处理前50场比赛进行测试
            if processed_count >= 50:
                break

            # 时间过滤
            if not (date_from <= match_time <= date_to):
                if i < 3:  # 只记录前几场用于调试
                    logger.debug(f"Match {i} time {match_time} outside range {date_from} to {date_to}")
                continue

            # === 修复比分解析逻辑 ===
            home_score = None
            away_score = None

            # 方法1: 优先从 status.scoreStr 中提取 (如 "4 - 2")
            score_str = match.get('status', {}).get('scoreStr')
            if score_str:
                try:
                    # 分割比分字符串 "4 - 2" -> ["4", "2"]
                    parts = score_str.split('-')
                    if len(parts) == 2:
                        home_score = int(parts[0].strip())
                        away_score = int(parts[1].strip())
                        score_fix_count += 1
                except (ValueError, IndexError) as e:
                    logger.debug(f"Failed to parse scoreStr '{score_str}': {e}")

            # 方法2: 备用方案 - 从 home/away.score 中提取（如果方法1失败）
            if home_score is None or away_score is None:
                home_score = match.get('home', {}).get('score')
                away_score = match.get('away', {}).get('score')
                # 检查是否为0（可能表示解析问题）
                if home_score == 0 and away_score == 0:
                    logger.debug(f"Warning: Both scores are 0 for match {match.get('id')} - potential parsing issue")

            match_data = {
                'fotmob_id': str(match.get('id', '')),
                'match_time': match_time,
                'home_team': match.get('home', {}).get('name', ''),
                'away_team': match.get('away', {}).get('name', ''),
                'home_score': home_score,
                'away_score': away_score,
                'status': match.get('status', {}).get('reason', {}).get('short', 'scheduled'),
                'league': data.get('details', {}).get('name', 'Premier League'),
            }

            if not match_data['fotmob_id'] or not match_data['home_team'] or not match_data['away_team']:
                continue

            # 记录比分样例用于验证
            if processed_count < 5:  # 只显示前5场
                status_code = match.get('status', {}).get('reason', {}).get('short', 'unknown')
                logger.info(f"Score Sample: {match_data['home_team']} vs {match_data['away_team']} - "
                           f"Score: {match_data['home_score']}-{match_data['away_score']} "
                           f"(Status: {status_code}, FotMob ID: {match_data['fotmob_id']})")

            matches.append(match_data)
            processed_count += 1

        logger.info(f"Filtered to {len(matches)} matches within date range (processed {processed_count})")
        logger.info(f"Score parsing fix applied to {score_fix_count} matches using scoreStr")
        return matches

    def process_match(self, match_data: Dict, session) -> bool:
        """处理单个比赛数据"""
        try:
            fotmob_id = match_data['fotmob_id']
            logger.debug(f"Processing match: {match_data['home_team']} vs {match_data['away_team']} (ID: {fotmob_id})")

            # 标准化队名和联赛名
            home_team_standardized = team_standardizer.normalize_team_name(match_data['home_team'])
            away_team_standardized = team_standardizer.normalize_team_name(match_data['away_team'])
            league_standardized = league_standardizer.normalize_league_name(match_data['league'])

            logger.debug(f"Standardized names: {home_team_standardized} vs {away_team_standardized} in {league_standardized}")

            # 转换为MatchRepository需要的格式
            match_dict = {
                'external_id': fotmob_id,
                'match_date': match_data['match_time'],
                'status': match_data['status'],
                'home_team': home_team_standardized,
                'away_team': away_team_standardized,
                'league': league_standardized,
                'home_score': match_data['home_score'],
                'away_score': match_data['away_score'],
                'home_xg': None,
                'away_xg': None,
                'home_possession': None,
                'away_possession': None,
            }

            # 使用MatchRepository进行upsert
            match_repo = MatchRepository(session)
            match_obj, is_new = match_repo.upsert_match(match_dict)

            action = "Created" if is_new else "Updated"
            logger.info(f"{action} match: {home_team_standardized} vs {away_team_standardized} (ID: {fotmob_id})")

            return True

        except Exception as e:
            logger.error(f"Error processing match {match_data.get('fotmob_id', 'unknown')}: {str(e)}")
            return False

    def run_collection(self) -> Dict:
        """运行L1数据收集"""
        logger.info("Starting L1 data collection (synchronous)...")
        start_time = datetime.now()

        try:
            # 获取赛程数据
            matches = self.fetch_league_matches()
            if not matches:
                logger.warning("No matches found in the specified date range")
                elapsed = (datetime.now() - start_time).total_seconds()
                return {"total": 0, "success": 0, "failed": 0, "elapsed_time": elapsed}

            logger.info(f"Processing {len(matches)} matches")

            total_processed = 0
            successful = 0
            failed = 0

            # 创建数据库连接
            engine = create_engine("sqlite:///data/football_prediction.db")
            SessionLocal = sessionmaker(bind=engine)

            # 处理每场比赛
            for i, match_data in enumerate(matches):
                try:
                    with SessionLocal() as session:
                        success = self.process_match(match_data, session)
                        session.commit()

                        total_processed += 1
                        if success:
                            successful += 1
                        else:
                            failed += 1

                        # 每10场比赛记录一次进度
                        if (i + 1) % 10 == 0:
                            logger.info(f"Progress: {i+1}/{len(matches)} (Success: {successful}, Failed: {failed})")

                except Exception as e:
                    logger.error(f"Error processing match {i+1}: {e}")
                    failed += 1
                    total_processed += 1

            elapsed = (datetime.now() - start_time).total_seconds()
            logger.info(f"L1 data collection completed! Total: {total_processed}, Success: {successful}, Failed: {failed}, Time: {elapsed:.2f}s")

            return {
                "total": total_processed,
                "success": successful,
                "failed": failed,
                "elapsed_time": elapsed
            }

        except Exception as e:
            logger.error(f"Fatal error in L1 collection process: {e}")
            raise


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="L1数据收集脚本（同步版）")
    parser.add_argument("--league-id", "-l", type=str, default="47", help="FotMob联赛ID")
    parser.add_argument("--days-back", "-b", type=int, default=600, help="获取过去多少天的比赛")
    parser.add_argument("--days-ahead", "-a", type=int, default=100, help="获取未来多少天的比赛")
    parser.add_argument("--no-progress", action="store_true", help="禁用进度显示")

    args = parser.parse_args()

    collector = L1DataCollector(
        league_id=args.league_id,
        days_back=args.days_back,
        days_ahead=args.days_ahead
    )

    try:
        stats = collector.run_collection()
        print("\n🎉 L1 data collection completed!")
        print("📊 Statistics:")
        print(f"   Total matches: {stats['total']}")
        print(f"   Successful: {stats['success']}")
        print(f"   Failed: {stats['failed']}")
        if stats['total'] > 0:
            print(f"   Success rate: {(stats['success']/stats['total']*100):.2f}%")
        print(f"   Elapsed time: {stats['elapsed_time']:.2f} seconds")

    except KeyboardInterrupt:
        print("\n⏹️ L1 data collection interrupted by user")
    except Exception as e:
        print(f"\n❌ L1 data collection failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()