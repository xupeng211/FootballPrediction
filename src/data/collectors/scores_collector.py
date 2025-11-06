"""
比分数据采集器

实现足球比赛实时比分和赛后数据采集逻辑。
包含实时比分更新、比赛事件记录、统计数据收集等功能。

采集策略:
- 实时采集比赛比分变化
- 记录比赛关键事件（进球、红黄牌等）
- 收集比赛统计数据
- 监控比赛状态变化

基于 DATA_DESIGN.md 第1.3节设计.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from src.collectors.base_collector import CollectionResult, BaseCollector

logger = logging.getLogger(__name__)


class ScoresCollector(BaseCollector):
    """
    比分数据采集器

    负责从数据API采集足球比赛实时比分和赛后数据,
    包含比分更新、事件记录、统计数据收集等功能。
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.match_events = {
            'goal': '进球',
            'yellow_card': '黄牌',
            'red_card': '红牌',
            'substitution': '换人',
            'var': 'VAR',
            'penalty': '点球',
            'whistle': '哨声'
        }

    async def collect_live_scores(self, match_ids: List[int]) -> CollectionResult:
        """
        采集多场比赛实时比分

        Args:
            match_ids: 比赛ID列表

        Returns:
            CollectionResult: 包含实时比分的采集结果
        """
        try:
            if not match_ids:
                return CollectionResult(
                    success=False,
                    error="No match IDs provided"
                )

            all_scores = {}
            collected_count = 0

            for match_id in match_ids:
                try:
                    # 采集单场比赛比分
                    match_score = await self._collect_single_match_score(match_id)
                    if match_score:
                        all_scores[match_id] = match_score
                        collected_count += 1

                except Exception as e:
                    logger.warning(f"Failed to collect score for match {match_id}: {e}")
                    continue

            return CollectionResult(
                success=True,
                data=all_scores,
                count=collected_count,
                cached=False
            )

        except Exception as e:
            logger.error(f"Error collecting live scores: {e}")
            return CollectionResult(
                success=False,
                error=f"Exception occurred: {str(e)}"
            )

    async def collect_match_score(self, match_id: int) -> CollectionResult:
        """
        采集单场比赛比分详情

        Args:
            match_id: 比赛ID

        Returns:
            CollectionResult: 包含比分详情的采集结果
        """
        try:
            endpoint = f"/matches/{match_id}"
            result = await self._make_request('GET', endpoint)

            if result.success and result.data:
                # 处理比分数据
                processed_score = self._process_match_score(result.data)
                return CollectionResult(
                    success=True,
                    data=processed_score,
                    count=1,
                    cached=result.cached,
                    response_time=result.response_time
                )
            else:
                return CollectionResult(
                    success=False,
                    error=f"Failed to fetch match score for {match_id}: {result.error}"
                )

        except Exception as e:
            logger.error(f"Error collecting match score for {match_id}: {e}")
            return CollectionResult(
                success=False,
                error=f"Exception occurred: {str(e)}"
            )

    async def collect_match_events(self, match_id: int) -> CollectionResult:
        """
        采集比赛事件

        Args:
            match_id: 比赛ID

        Returns:
            CollectionResult: 包含比赛事件的采集结果
        """
        try:
            endpoint = f"/matches/{match_id}/events"
            result = await self._make_request('GET', endpoint)

            if result.success and result.data:
                # 处理比赛事件
                processed_events = self._process_match_events(result.data)
                return CollectionResult(
                    success=True,
                    data=processed_events,
                    count=len(processed_events.get('events', [])),
                    cached=result.cached,
                    response_time=result.response_time
                )
            else:
                return CollectionResult(
                    success=False,
                    error=f"Failed to fetch match events for {match_id}: {result.error}"
                )

        except Exception as e:
            logger.error(f"Error collecting match events for {match_id}: {e}")
            return CollectionResult(
                success=False,
                error=f"Exception occurred: {str(e)}"
            )

    async def collect_match_statistics(self, match_id: int) -> CollectionResult:
        """
        采集比赛统计数据

        Args:
            match_id: 比赛ID

        Returns:
            CollectionResult: 包含统计数据的采集结果
        """
        try:
            endpoint = f"/matches/{match_id}/statistics"
            result = await self._make_request('GET', endpoint)

            if result.success and result.data:
                # 处理统计数据
                processed_stats = self._process_match_statistics(result.data)
                return CollectionResult(
                    success=True,
                    data=processed_stats,
                    count=len(processed_stats.get('statistics', [])),
                    cached=result.cached,
                    response_time=result.response_time
                )
            else:
                return CollectionResult(
                    success=False,
                    error=f"Failed to fetch match statistics for {match_id}: {result.error}"
                )

        except Exception as e:
            logger.error(f"Error collecting match statistics for {match_id}: {e}")
            return CollectionResult(
                success=False,
                error=f"Exception occurred: {str(e)}"
            )

    async def collect_lineups(self, match_id: int) -> CollectionResult:
        """
        采集比赛阵容信息

        Args:
            match_id: 比赛ID

        Returns:
            CollectionResult: 包含阵容信息的采集结果
        """
        try:
            endpoint = f"/matches/{match_id}/lineups"
            result = await self._make_request('GET', endpoint)

            if result.success and result.data:
                # 处理阵容数据
                processed_lineups = self._process_lineups(result.data)
                return CollectionResult(
                    success=True,
                    data=processed_lineups,
                    count=len(processed_lineups.get('teams', [])),
                    cached=result.cached,
                    response_time=result.response_time
                )
            else:
                return CollectionResult(
                    success=False,
                    error=f"Failed to fetch lineups for match {match_id}: {result.error}"
                )

        except Exception as e:
            logger.error(f"Error collecting lineups for match {match_id}: {e}")
            return CollectionResult(
                success=False,
                error=f"Exception occurred: {str(e)}"
            )

    async def _collect_single_match_score(self, match_id: int) -> Dict:
        """采集单场比赛比分"""
        endpoint = f"/matches/{match_id}"
        result = await self._make_request('GET', endpoint)

        if result.success and result.data:
            return self._process_match_score(result.data)
        return {}

    def _process_match_score(self, raw_data: Dict) -> Dict:
        """处理比分数据"""
        match = raw_data.get('match', {})
        score = match.get('score', {})

        processed = {
            'match_id': match.get('id'),
            'match_info': {
                'home_team': match.get('homeTeam', {}).get('name'),
                'away_team': match.get('awayTeam', {}).get('name'),
                'competition': match.get('competition', {}).get('name'),
                'utc_date': match.get('utcDate'),
                'status': match.get('status'),
                'matchday': match.get('matchday'),
                'stage': match.get('stage'),
                'group': match.get('group')
            },
            'score': {
                'home_team': score.get('fullTime', {}).get('home'),
                'away_team': score.get('fullTime', {}).get('away'),
                'winner': score.get('fullTime', {}).get('winner'),
                'duration': match.get('duration'),
                'regular_time': score.get('regularTime'),
                'extra_time': score.get('extraTime'),
                'penalties': score.get('penalties')
            },
            'half_time_score': {
                'home_team': score.get('halfTime', {}).get('home'),
                'away_team': score.get('halfTime', {}).get('away'),
                'winner': score.get('halfTime', {}).get('winner')
            },
            'last_updated': datetime.now().isoformat()
        }

        return processed

    def _process_match_events(self, raw_data: Dict) -> Dict:
        """处理比赛事件数据"""
        events = raw_data.get('events', [])
        processed_events = []

        for event in events:
            processed_event = {
                'id': event.get('id'),
                'type': {
                    'id': event.get('type', {}).get('id'),
                    'name': event.get('type', {}).get('name')
                },
                'minute': event.get('minute'),
                'team': {
                    'id': event.get('team', {}).get('id'),
                    'name': event.get('team', {}).get('name')
                },
                'player': {
                    'id': event.get('player', {}).get('id'),
                    'name': event.get('player', {}).get('name')
                },
                'assist': {
                    'id': event.get('assist', {}).get('id'),
                    'name': event.get('assist', {}).get('name')
                } if event.get('assist') else None,
                'extra_time': event.get('extraTime'),
                'comments': event.get('comments'),
                'timestamp': self._parse_event_timestamp(event)
            }
            processed_events.append(processed_event)

        return {
            'match_id': raw_data.get('match', {}).get('id'),
            'events': processed_events,
            'total_events': len(processed_events),
            'last_updated': datetime.now().isoformat()
        }

    def _process_match_statistics(self, raw_data: Dict) -> Dict:
        """处理比赛统计数据"""
        match = raw_data.get('match', {})
        statistics = raw_data.get('statistics', [])

        processed_stats = {
            'match_id': match.get('id'),
            'teams': {}
        }

        for team_stats in statistics:
            team = team_stats.get('team', {})
            team_name = team.get('name')

            stats = {
                'team_id': team.get('id'),
                'team_name': team_name,
                'shots': {
                    'total': team_stats.get('shots', {}).get('total'),
                    'on_target': team_stats.get('shots', {}).get('onTarget'),
                    'off_target': team_stats.get('shots', {}).get('offTarget')
                },
                'possession': team_stats.get('possession'),
                'passes': {
                    'total': team_stats.get('passes', {}).get('total'),
                    'accurate': team_stats.get('passes', {}).get('accurate'),
                    'inaccurate': team_stats.get('passes', {}).get('inaccurate')
                },
                'fouls': team_stats.get('fouls'),
                'corners': team_stats.get('corners'),
                'offsides': team_stats.get('offsides'),
                'yellow_cards': team_stats.get('yellowCards'),
                'red_cards': team_stats.get('redCards'),
                'tackles': team_stats.get('tackles'),
                ' interceptions': team_stats.get('interceptions')
            }

            processed_stats['teams'][team_name] = stats

        processed_stats['last_updated'] = datetime.now().isoformat()
        return processed_stats

    def _process_lineups(self, raw_data: Dict) -> Dict:
        """处理阵容数据"""
        match = raw_data.get('match', {})

        processed_lineups = {
            'match_id': match.get('id'),
            'teams': {}
        }

        for team_data in raw_data.get('teams', []):
            team = team_data.get('team', {})
            team_name = team.get('name')

            lineup = {
                'team_id': team.get('id'),
                'team_name': team_name,
                'formation': team_data.get('formation'),
                'coach': {
                    'id': team_data.get('coach', {}).get('id'),
                    'name': team_data.get('coach', {}).get('name')
                },
                'startXI': [],
                'substitutes': []
            }

            # 处理首发阵容
            for player in team_data.get('startXI', []):
                player_info = {
                    'id': player.get('id'),
                    'name': player.get('name'),
                    'position': player.get('position'),
                    'shirt_number': player.get('shirtNumber'),
                    'captain': player.get('captain')
                }
                lineup['startXI'].append(player_info)

            # 处理替补阵容
            for player in team_data.get('substitutes', []):
                player_info = {
                    'id': player.get('id'),
                    'name': player.get('name'),
                    'position': player.get('position'),
                    'shirt_number': player.get('shirtNumber')
                }
                lineup['substitutes'].append(player_info)

            processed_lineups['teams'][team_name] = lineup

        processed_lineups['last_updated'] = datetime.now().isoformat()
        return processed_lineups

    def _parse_event_timestamp(self, event: Dict) -> Optional[str]:
        """解析事件时间戳"""
        # 这里可以根据实际API响应格式来解析时间戳
        if 'timestamp' in event:
            return event['timestamp']
        elif 'minute' in event:
            # 基于比赛分钟数估算时间戳
            # 注意：这是估算，实际应该使用API提供的时间戳
            return f"minute_{event['minute']}"
        return None

    async def monitor_live_match(self, match_id: int, update_interval: int = 60) -> None:
        """
        监控单场实时比赛

        Args:
            match_id: 比赛ID
            update_interval: 更新间隔（秒）
        """
        logger.info(f"开始监控比赛 {match_id} 的实时数据")

        while True:
            try:
                # 检查比赛状态
                score_result = await self.collect_match_score(match_id)

                if score_result.success:
                    match_status = score_result.data.get('match_info', {}).get('status')

                    if match_status in ['FINISHED', 'POSTPONED', 'CANCELLED']:
                        logger.info(f"比赛 {match_id} 已结束，状态: {match_status}")
                        break

                    # 采集比分数据
                    logger.debug(f"比赛 {match_id} 当前比分: "
                               f"{score_result.data.get('score', {}).get('home_team', 0)} - "
                               f"{score_result.data.get('score', {}).get('away_team', 0)}")

                    # 采集最新事件
                    events_result = await self.collect_match_events(match_id)
                    if events_result.success and events_result.data.get('events'):
                        latest_event = events_result.data['events'][-1]
                        logger.debug(f"比赛 {match_id} 最新事件: {latest_event['type']['name']} "
                                   f"({latest_event['minute']}分钟)")

                else:
                    logger.warning(f"无法获取比赛 {match_id} 的数据: {score_result.error}")

                # 等待下一次更新
                await asyncio.sleep(update_interval)

            except Exception as e:
                logger.error(f"监控比赛 {match_id} 时发生错误: {e}")
                await asyncio.sleep(30)  # 出错时等待30秒后重试

    async def get_live_matches_summary(self) -> Dict:
        """获取正在进行比赛的摘要"""
        try:
            # 这里可以根据实际API获取正在进行的比赛列表
            # 示例实现
            today = datetime.now().strftime('%Y-%m-%d')
            endpoint = f"/matches?date={today}&status=LIVE"

            result = await self._make_request('GET', endpoint)

            if result.success and result.data:
                matches = result.data.get('matches', [])
                summary = {
                    'date': today,
                    'total_live_matches': len(matches),
                    'matches': []
                }

                for match in matches:
                    match_summary = {
                        'id': match.get('id'),
                        'home_team': match.get('homeTeam', {}).get('name'),
                        'away_team': match.get('awayTeam', {}).get('name'),
                        'score': {
                            'home': match.get('score', {}).get('fullTime', {}).get('home', 0),
                            'away': match.get('score', {}).get('fullTime', {}).get('away', 0)
                        },
                        'minute': match.get('minute'),
                        'status': match.get('status')
                    }
                    summary['matches'].append(match_summary)

                return summary
            else:
                return {
                    'date': today,
                    'total_live_matches': 0,
                    'matches': [],
                    'error': result.error
                }

        except Exception as e:
            logger.error(f"Error getting live matches summary: {e}")
            return {
                'date': datetime.now().strftime('%Y-%m-%d'),
                'total_live_matches': 0,
                'matches': [],
                'error': str(e)
            }


# 便捷函数
async def get_match_score(match_id: int, api_key: str, base_url: str) -> Dict:
    """
    获取比赛比分的便捷函数

    Args:
        match_id: 比赛ID
        api_key: API密钥
        base_url: API基础URL

    Returns:
        Dict: 比分数据
    """
    collector = ScoresCollector(
        api_key=api_key,
        base_url=base_url
    )

    result = await collector.collect_match_score(match_id)

    if result.success:
        return {
            'success': True,
            'data': result.data,
            'message': f"成功获取比赛 {match_id} 的比分数据"
        }
    else:
        return {
            'success': False,
            'error': result.error,
            'message': f"获取比赛 {match_id} 的比分数据失败"
        }