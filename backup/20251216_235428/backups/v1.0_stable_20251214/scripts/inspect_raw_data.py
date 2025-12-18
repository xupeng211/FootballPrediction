#!/usr/bin/env python3
"""
Deep Data Inspection Script - 深度数据审计脚本
Deep inspection of FotMob API raw data structure and content

用于诊断数据质量问题和探索 FotMob API 的完整数据结构
重点检查：
1. 比赛状态和比分解析问题
2. 射门地图 (shotmap) 数据结构
3. 阵容 (lineup) 和详细统计 (stats)
4. 完整的 JSON 响应结构

作者: Data Audit Team
创建时间: 2025-12-13
版本: 1.0.0 (Deep Audit Edition)
"""

import json
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List
import urllib.request
import urllib.parse

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger


class FotMobDataInspector:
    """FotMob 数据审计器 - 深度检查 API 响应结构"""

    def __init__(self):
        """初始化审计器"""
        self.league_id = 47  # 英超
        self.base_url = "https://www.fotmob.com/api"

        # 创建日志目录
        Path("logs").mkdir(exist_ok=True)

        logger.info("FotMobDataInspector initialized for deep audit")

    def fetch_league_matches(self, days_back: int = 30) -> Dict[str, Any]:
        """
        获取联赛比赛列表

        Args:
            days_back: 查询过去几天的比赛

        Returns:
            Dict: API 响应数据
        """
        logger.info(f"Fetching Premier League matches from last {days_back} days...")

        # 计算日期范围
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)

        # 构建请求 URL - 尝试不同的API端点
        urls = [
            f"{self.base_url}/leagues?id={self.league_id}&type=league&timezone=UTC",
            f"{self.base_url}/leagues?id={self.league_id}&type=match&timezone=UTC",
            f"{self.base_url}/matches?leagueId={self.league_id}&timezone=UTC"
        ]

        for i, url in enumerate(urls):
            try:
                logger.info(f"Trying URL {i+1}/{len(urls)}: {url}")

                req = urllib.request.Request(url)
                req.add_header('User-Agent', 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')

                with urllib.request.urlopen(req, timeout=30) as response:
                    raw_data = response.read().decode('utf-8')
                    data = json.loads(raw_data)

                # 检查返回的数据结构
                logger.debug(f"Response keys: {list(data.keys())}")

                matches = []
                if 'matches' in data:
                    matches = data['matches']
                elif 'match' in data:
                    matches = data['match']
                elif 'fixtures' in data:
                    fixtures = data['fixtures']
                    if 'allMatches' in fixtures:
                        matches = fixtures['allMatches']
                    else:
                        matches = fixtures
                elif 'data' in data:
                    data_section = data['data']
                    if 'match' in data_section:
                        matches = data_section['match']
                    elif 'matches' in data_section:
                        matches = data_section['matches']

                logger.info(f"Successfully fetched data from URL {i+1}: {len(matches)} matches")

                # 返回包含matches的数据
                return {'matches': matches, 'raw_data': data}

            except Exception as e:
                logger.warning(f"Failed to fetch from URL {i+1}: {e}")
                continue

        logger.error("All URLs failed to fetch league matches")
        raise Exception("Unable to fetch league data from any endpoint")

    def find_finished_match(self, league_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        从联赛数据中找到已完赛的比赛

        Args:
            league_data: 联赛数据

        Returns:
            Optional[Dict]: 已完赛的比赛信息
        """
        logger.info("Searching for FT (Full Time) matches...")

        matches = league_data.get('matches', [])

        for match in matches:
            try:
                # 检查比赛状态
                status = match.get('status', {}).get('reason', {}).get('short', '').upper()
                score_info = match.get('header', {})

                home_team = match.get('home', {}).get('name', 'Unknown Home')
                away_team = match.get('away', {}).get('name', 'Unknown Away')
                home_score = score_info.get('teams', [{}])[0].get('score', 0)
                away_score = score_info.get('teams', [{}, {}])[1].get('score', 0)
                match_time = match.get('status', {}).get('utcTime', 'Unknown Time')

                logger.debug(f"Match: {home_team} vs {away_team} - Status: {status} - Score: {home_score}-{away_score}")

                # 寻找已完赛的比赛
                if status == 'FT':
                    logger.info(f"Found FT match: {home_team} vs {away_team} ({home_score}-{away_score})")

                    return {
                        'match_id': match.get('id'),
                        'fotmob_id': str(match.get('id')),
                        'home_team': home_team,
                        'away_team': away_team,
                        'status': status,
                        'home_score': home_score,
                        'away_score': away_score,
                        'match_time': match_time,
                        'raw_match_data': match
                    }

            except Exception as e:
                logger.warning(f"Error processing match: {e}")
                continue

        logger.warning("No FT matches found in the data")
        return None

    def fetch_match_details(self, fotmob_id: str) -> Dict[str, Any]:
        """
        获取比赛详情数据

        Args:
            fotmob_id: FotMob 比赛 ID

        Returns:
            Dict: 比赛详情数据
        """
        logger.info(f"Fetching detailed match data for fotmob_id: {fotmob_id}")

        url = f"{self.base_url}/matchDetails?matchId={fotmob_id}"

        try:
            req = urllib.request.Request(url)
            req.add_header('User-Agent', 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')

            with urllib.request.urlopen(req, timeout=30) as response:
                raw_data = response.read().decode('utf-8')
                data = json.loads(raw_data)

            logger.info(f"Successfully fetched match details for {fotmob_id}")
            return data

        except Exception as e:
            logger.error(f"Failed to fetch match details for {fotmob_id}: {e}")
            raise

    def analyze_json_structure(self, data: Any, prefix: str = "", max_depth: int = 4, current_depth: int = 0) -> List[str]:
        """
        分析 JSON 数据结构，返回所有键的路径

        Args:
            data: 要分析的数据
            prefix: 键的前缀
            max_depth: 最大深度
            current_depth: 当前深度

        Returns:
            List[str]: 所有键的路径
        """
        if current_depth >= max_depth:
            return [f"{prefix}[MAX_DEPTH_REACHED]"]

        paths = []

        if isinstance(data, dict):
            for key, value in data.items():
                current_prefix = f"{prefix}.{key}" if prefix else key
                paths.append(f"{current_prefix} ({type(value).__name__})")

                if isinstance(value, (dict, list)) and len(str(value)) < 1000:  # 限制大小
                    sub_paths = self.analyze_json_structure(
                        value, current_prefix, max_depth, current_depth + 1
                    )
                    paths.extend([f"  {p}" for p in sub_paths])

        elif isinstance(data, list):
            if len(data) > 0:
                paths.append(f"{prefix}[{len(data)} items]")

                # 只分析前几个元素
                for i, item in enumerate(data[:3]):
                    current_prefix = f"{prefix}[{i}]"
                    if isinstance(item, (dict, list)):
                        sub_paths = self.analyze_json_structure(
                            item, current_prefix, max_depth, current_depth + 1
                        )
                        paths.extend([f"  {p}" for p in sub_paths])
                    else:
                        paths.append(f"  {current_prefix} ({type(item).__name__}): {str(item)[:50]}...")
            else:
                paths.append(f"{prefix}[0 items]")

        return paths

    def check_specific_fields(self, match_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        检查特定字段是否存在和内容

        Args:
            match_data: 比赛数据

        Returns:
            Dict: 检查结果
        """
        logger.info("Checking specific high-value fields...")

        results = {
            'header_status': None,
            'header_score': None,
            'shotmap_exists': False,
            'shotmap_details': None,
            'lineup_exists': False,
            'lineup_details': None,
            'content_stats_exists': False,
            'content_stats_details': None,
            'content_team_stats_exists': False,
            'content_team_stats_details': None,
            'general_match_info': None,
        }

        # 检查 header 信息
        if 'header' in match_data:
            header = match_data['header']
            results['header_status'] = {
                'status': header.get('status', {}).get('reason', {}).get('long', 'Not found'),
                'status_short': header.get('status', {}).get('reason', {}).get('short', 'Not found'),
                'status_finished': header.get('status', {}).get('finished', False)
            }

            teams = header.get('teams', [])
            if len(teams) >= 2:
                results['header_score'] = {
                    'home_score': teams[0].get('score', 'N/A'),
                    'away_score': teams[1].get('score', 'N/A'),
                    'home_team': teams[0].get('name', 'N/A'),
                    'away_team': teams[1].get('name', 'N/A')
                }

        # 检查 shotmap 数据
        if 'shotmap' in match_data:
            shotmap = match_data['shotmap']
            results['shotmap_exists'] = True
            results['shotmap_details'] = {
                'total_shots': len(shotmap.get('shots', [])),
                'sample_shots': shotmap.get('shots', [])[:3] if len(shotmap.get('shots', [])) > 0 else [],
                'xg_available': any('expectedGoals' in shot for shot in shotmap.get('shots', [])),
                'coordinates_available': any('x' in shot and 'y' in shot for shot in shotmap.get('shots', []))
            }

        # 检查 lineup 数据
        if 'content' in match_data and 'lineup' in match_data['content']:
            lineup = match_data['content']['lineup']
            results['lineup_exists'] = True
            results['lineup_details'] = {
                'has_lineup_data': bool(lineup),
                'lineup_type': type(lineup).__name__,
                'lineup_keys': list(lineup.keys()) if isinstance(lineup, dict) else 'Not a dict'
            }

        # 检查 content.stats 数据
        if 'content' in match_data and 'stats' in match_data['content']:
            stats = match_data['content']['stats']
            results['content_stats_exists'] = True
            results['content_stats_details'] = {
                'stats_type': type(stats).__name__,
                'stats_keys': list(stats.keys()) if isinstance(stats, dict) else 'Not a dict'
            }

        # 检查 content.teamStats 数据（通常包含详细统计）
        if 'content' in match_data and 'teamStats' in match_data['content']:
            team_stats = match_data['content']['teamStats']
            results['content_team_stats_exists'] = True
            results['content_team_stats_details'] = {
                'team_stats_type': type(team_stats).__name__,
                'sample_structure': self.analyze_json_structure(team_stats, 'content.teamStats', max_depth=3)
            }

        # 检查 general 信息
        if 'general' in match_data:
            general = match_data['general']
            results['general_match_info'] = {
                'match_id': general.get('matchId', 'N/A'),
                'league': general.get('league', {}).get('name', 'N/A'),
                'start_time': general.get('startTimeUTC', 'N/A'),
                'has_formations': 'formations' in general,
                'has_managers': 'managers' in general
            }

        return results

    def save_sample_data(self, match_info: Dict[str, Any], match_details: Dict[str, Any]) -> str:
        """
        保存样本数据到文件

        Args:
            match_info: 比赛基本信息
            match_details: 比赛详情数据

        Returns:
            str: 保存的文件路径
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"logs/sample_match_{timestamp}_ft_{match_info['fotmob_id']}.json"

        sample_data = {
            'audit_info': {
                'timestamp': timestamp,
                'match_info': match_info,
                'purpose': 'Deep data structure audit for Score Anomaly and Missing Data investigation'
            },
            'raw_response': match_details
        }

        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(sample_data, f, indent=2, ensure_ascii=False, default=str)

            logger.info(f"Sample data saved to: {filename}")
            return filename

        except Exception as e:
            logger.error(f"Failed to save sample data: {e}")
            raise

    def run_inspection(self) -> Dict[str, Any]:
        """
        运行完整的深度审计流程

        Returns:
            Dict: 审计结果
        """
        logger.info("Starting deep data inspection...")

        results = {
            'inspection_time': datetime.now().isoformat(),
            'league_data_fetched': False,
            'ft_match_found': False,
            'match_details_fetched': False,
            'sample_file_saved': False,
            'findings': {}
        }

        try:
            # 步骤1: 获取联赛数据
            league_data = self.fetch_league_matches(days_back=7)
            results['league_data_fetched'] = True

            # 步骤2: 找到已完赛的比赛
            ft_match = self.find_finished_match(league_data)
            if not ft_match:
                raise ValueError("No FT matches found for inspection")

            results['ft_match_found'] = True
            results['found_match'] = ft_match

            # 步骤3: 获取比赛详情
            match_details = self.fetch_match_details(ft_match['fotmob_id'])
            results['match_details_fetched'] = True

            # 步骤4: 分析 JSON 结构
            logger.info("Analyzing complete JSON structure...")
            structure_paths = self.analyze_json_structure(match_details, max_depth=4)
            results['json_structure'] = structure_paths

            # 步骤5: 检查特定字段
            field_checks = self.check_specific_fields(match_details)
            results['field_checks'] = field_checks

            # 步骤6: 保存样本数据
            sample_file = self.save_sample_data(ft_match, match_details)
            results['sample_file_saved'] = True
            results['sample_file_path'] = sample_file

            # 生成发现摘要
            results['findings'] = {
                'total_json_keys': len([p for p in structure_paths if not p.startswith('  ')]),
                'has_shotmap_data': field_checks['shotmap_exists'],
                'has_lineup_data': field_checks['lineup_exists'],
                'has_detailed_stats': field_checks['content_team_stats_exists'],
                'score_inconsistency': {
                    'header_vs_raw_match': (
                        field_checks.get('header_score', {}).get('home_score') != ft_match.get('home_score') or
                        field_checks.get('header_score', {}).get('away_score') != ft_match.get('away_score')
                    ),
                    'header_score': field_checks.get('header_score'),
                    'raw_match_score': f"{ft_match.get('home_score')}-{ft_match.get('away_score')}"
                }
            }

            logger.info("Deep data inspection completed successfully")
            return results

        except Exception as e:
            logger.error(f"Deep data inspection failed: {e}")
            results['error'] = str(e)
            raise


def main():
    """主函数"""
    inspector = FotMobDataInspector()

    try:
        # 运行深度审计
        results = inspector.run_inspection()

        # 打印审计结果
        print("\n" + "="*80)
        print("🔍 DEEP DATA INSPECTION RESULTS")
        print("="*80)

        # 基本信息
        print(f"\n📅 Inspection Time: {results['inspection_time']}")
        print(f"✅ League Data Fetched: {results['league_data_fetched']}")
        print(f"✅ FT Match Found: {results['ft_match_found']}")
        print(f"✅ Match Details Fetched: {results['match_details_fetched']}")
        print(f"✅ Sample File Saved: {results['sample_file_saved']}")

        # 找到的比赛信息
        if results['ft_match_found']:
            match = results['found_match']
            print(f"\n⚽ FT Match Found:")
            print(f"   Match: {match['home_team']} vs {match['away_team']}")
            print(f"   Score: {match['home_score']}-{match['away_score']}")
            print(f"   Status: {match['status']}")
            print(f"   FotMob ID: {match['fotmob_id']}")

        # JSON 结构分析
        print(f"\n🏗️ JSON Structure Analysis:")
        print(f"   Total Top-Level Keys: {results['findings']['total_json_keys']}")
        print(f"   Sample Structure Paths:")
        for path in results.get('json_structure', [])[:15]:  # 只显示前15个
            print(f"     {path}")
        if len(results.get('json_structure', [])) > 15:
            print(f"     ... (and {len(results['json_structure']) - 15} more paths)")

        # 字段检查结果
        field_checks = results.get('field_checks', {})
        print(f"\n📊 High-Value Field Analysis:")
        print(f"   ShotMap Data: {'✅' if field_checks.get('shotmap_exists') else '❌'}")
        if field_checks.get('shotmap_details'):
            details = field_checks['shotmap_details']
            print(f"     - Total Shots: {details.get('total_shots', 0)}")
            print(f"     - xG Available: {'✅' if details.get('xg_available') else '❌'}")
            print(f"     - Coordinates Available: {'✅' if details.get('coordinates_available') else '❌'}")

        print(f"   Lineup Data: {'✅' if field_checks.get('lineup_exists') else '❌'}")
        print(f"   Detailed Stats: {'✅' if field_checks.get('content_team_stats_exists') else '❌'}")

        # 比分一致性检查
        score_inconsistency = results['findings']['score_inconsistency']
        print(f"\n🚨 Score Consistency Check:")
        print(f"   Header Score vs Raw Match: {'❌ INCONSISTENT' if score_inconsistency['score_inconsistency'] else '✅ CONSISTENT'}")
        print(f"   Header Score: {score_inconsistency.get('header_score', 'N/A')}")
        print(f"   Raw Match Score: {score_inconsistency.get('raw_match_score', 'N/A')}")

        # 样本文件路径
        if results['sample_file_saved']:
            print(f"\n💾 Sample Data Saved:")
            print(f"   File: {results['sample_file_path']}")
            print(f"   Purpose: Manual inspection of complete JSON structure")

        print("\n" + "="*80)
        print("🎯 INSPECTION COMPLETE - Review sample file for detailed analysis")
        print("="*80)

    except Exception as e:
        print(f"\n❌ Deep data inspection failed: {e}")
        logger.exception("Inspection failed")
        sys.exit(1)


if __name__ == "__main__":
    main()