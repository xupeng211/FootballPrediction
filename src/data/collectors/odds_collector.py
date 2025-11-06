"""
赔率数据采集器

实现足球比赛赔率数据的采集逻辑。
包含多家博彩公司赔率对比、历史赔率变化追踪等功能。

采集策略:
- 实时采集主流博彩公司赔率
- 记录赔率历史变化
- 计算平均赔率和隐含概率
- 监控赔率异常波动

基于 DATA_DESIGN.md 第1.2节设计.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from src.collectors.base_collector import CollectionResult, BaseCollector

logger = logging.getLogger(__name__)


class OddsCollector(BaseCollector):
    """
    赔率数据采集器

    负责从博彩数据API采集足球比赛赔率信息,
    包含胜平负赔率、亚洲盘口、大小球等多种赔率类型。
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.odds_types = {
            'match_winner': '1X2',  # 胜平负
            'asian_handicap': 'AH',  # 亚洲盘口
            'over_under': 'OU',  # 大小球
            'both_teams_score': 'BTTS'  # 双方进球
        }

    async def collect_match_odds(self, match_id: int) -> CollectionResult:
        """
        采集单场比赛赔率

        Args:
            match_id: 比赛ID

        Returns:
            CollectionResult: 包含赔率数据的采集结果
        """
        try:
            endpoint = f"/matches/{match_id}/odds"
            result = await self._make_request('GET', endpoint)

            if result.success and result.data:
                # 处理赔率数据
                processed_odds = self._process_odds_data(result.data)
                return CollectionResult(
                    success=True,
                    data=processed_odds,
                    count=len(processed_odds) if processed_odds else 0,
                    cached=result.cached,
                    response_time=result.response_time
                )
            else:
                return CollectionResult(
                    success=False,
                    error=f"Failed to fetch odds for match {match_id}: {result.error}"
                )

        except Exception as e:
            logger.error(f"Error collecting odds for match {match_id}: {e}")
            return CollectionResult(
                success=False,
                error=f"Exception occurred: {str(e)}"
            )

    async def collect_league_odds(self, league_id: int, season: str) -> CollectionResult:
        """
        采集联赛赔率概览

        Args:
            league_id: 联赛ID
            season: 赛季

        Returns:
            CollectionResult: 包含联赛赔率概览的采集结果
        """
        try:
            endpoint = f"/competitions/{league_id}/odds"
            params = {'season': season}

            result = await self._make_request('GET', endpoint, params=params)

            if result.success and result.data:
                # 处理联赛赔率数据
                processed_data = self._process_league_odds(result.data)
                return CollectionResult(
                    success=True,
                    data=processed_data,
                    count=len(processed_data.get('matches', [])),
                    cached=result.cached,
                    response_time=result.response_time
                )
            else:
                return CollectionResult(
                    success=False,
                    error=f"Failed to fetch league odds: {result.error}"
                )

        except Exception as e:
            logger.error(f"Error collecting league odds: {e}")
            return CollectionResult(
                success=False,
                error=f"Exception occurred: {str(e)}"
            )

    async def collect_historical_odds(self, match_id: int, days_back: int = 30) -> CollectionResult:
        """
        采集历史赔率数据

        Args:
            match_id: 比赛ID
            days_back: 回溯天数

        Returns:
            CollectionResult: 包含历史赔率数据的采集结果
        """
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)

            endpoint = f"/matches/{match_id}/odds/history"
            params = {
                'from': start_date.strftime('%Y-%m-%d'),
                'to': end_date.strftime('%Y-%m-%d')
            }

            result = await self._make_request('GET', endpoint, params=params)

            if result.success and result.data:
                # 处理历史赔率数据
                historical_data = self._process_historical_odds(result.data)
                return CollectionResult(
                    success=True,
                    data=historical_data,
                    count=len(historical_data.get('odds_history', [])),
                    cached=result.cached,
                    response_time=result.response_time
                )
            else:
                return CollectionResult(
                    success=False,
                    error=f"Failed to fetch historical odds: {result.error}"
                )

        except Exception as e:
            logger.error(f"Error collecting historical odds: {e}")
            return CollectionResult(
                success=False,
                error=f"Exception occurred: {str(e)}"
            )

    def _process_odds_data(self, raw_data: Dict) -> Dict:
        """处理赔率数据"""
        processed = {
            'match_id': raw_data.get('match', {}).get('id'),
            'match_info': {
                'home_team': raw_data.get('match', {}).get('homeTeam', {}).get('name'),
                'away_team': raw_data.get('match', {}).get('awayTeam', {}).get('name'),
                'competition': raw_data.get('match', {}).get('competition', {}).get('name'),
                'utc_date': raw_data.get('match', {}).get('utcDate')
            },
            'odds': {}
        }

        # 处理不同类型的赔率
        for bet_type, bets in raw_data.get('bets', {}).items():
            if bet_type in self.odds_types:
                processed['odds'][bet_type] = self._process_bet_type(bets)

        return processed

    def _process_bet_type(self, bets: List[Dict]) -> Dict:
        """处理特定类型的投注赔率"""
        if not bets:
            return {}

        processed = []
        for bet in bets:
            bet_info = {
                'name': bet.get('name'),
                'id': bet.get('id'),
                'values': []
            }

            # 处理赔率值
            for value in bet.get('values', []):
                bet_value = {
                    'value': value.get('value'),
                    'odd': value.get('odd'),
                    'cutoff': value.get('cutoff'),
                    'localteam': value.get('localteam')
                }
                bet_info['values'].append(bet_value)

            processed.append(bet_info)

        return processed

    def _process_league_odds(self, raw_data: Dict) -> Dict:
        """处理联赛赔率数据"""
        processed = {
            'league_id': raw_data.get('competition', {}).get('id'),
            'league_name': raw_data.get('competition', {}).get('name'),
            'matches': []
        }

        for match in raw_data.get('matches', []):
            match_odds = {
                'match_id': match.get('id'),
                'home_team': match.get('homeTeam', {}).get('name'),
                'away_team': match.get('awayTeam', {}).get('name'),
                'utc_date': match.get('utcDate'),
                'status': match.get('status'),
                'has_odds': bool(match.get('odds')),
                'odds_count': len(match.get('odds', {}))
            }
            processed['matches'].append(match_odds)

        return processed

    def _process_historical_odds(self, raw_data: Dict) -> Dict:
        """处理历史赔率数据"""
        processed = {
            'match_id': raw_data.get('match', {}).get('id'),
            'odds_history': []
        }

        for odds_record in raw_data.get('oddsHistory', []):
            history_item = {
                'timestamp': odds_record.get('timestamp'),
                'bookmaker': odds_record.get('bookmaker'),
                'odds': odds_record.get('odds'),
                'price_changes': self._calculate_price_changes(odds_record.get('odds', {}))
            }
            processed['odds_history'].append(history_item)

        # 按时间排序
        processed['odds_history'].sort(key=lambda x: x['timestamp'])

        return processed

    def _calculate_price_changes(self, current_odds: Dict) -> Dict:
        """计算赔率变化"""
        changes = {}

        for bet_type, bet_data in current_odds.items():
            if isinstance(bet_data, dict) and 'values' in bet_data:
                for value in bet_data.get('values', []):
                    if 'price_change' in value:
                        changes[f"{bet_type}_{value.get('value', '')}"] = value['price_change']

        return changes

    async def get_odds_summary(self, match_id: int) -> Dict:
        """获取赔率摘要信息"""
        result = await self.collect_match_odds(match_id)

        if not result.success or not result.data:
            return {}

        odds_data = result.data.get('odds', {})
        summary = {
            'match_id': match_id,
            'has_1x2': 'match_winner' in odds_data,
            'has_asian_handicap': 'asian_handicap' in odds_data,
            'has_over_under': 'over_under' in odds_data,
            'bookmakers_count': self._count_bookmakers(odds_data),
            'last_updated': datetime.now().isoformat()
        }

        return summary

    def _count_bookmakers(self, odds_data: Dict) -> int:
        """统计博彩公司数量"""
        bookmakers = set()

        for bet_type, bet_data in odds_data.items():
            if isinstance(bet_data, list):
                for bet in bet_data:
                    if isinstance(bet, dict) and 'name' in bet:
                        bookmakers.add(bet['name'])

        return len(bookmakers)

    async def monitor_odds_changes(self, match_ids: List[int], check_interval: int = 300) -> None:
        """
        监控赔率变化

        Args:
            match_ids: 要监控的比赛ID列表
            check_interval: 检查间隔（秒）
        """
        logger.info(f"开始监控 {len(match_ids)} 场比赛的赔率变化")

        while True:
            try:
                for match_id in match_ids:
                    # 获取当前赔率
                    result = await self.collect_match_odds(match_id)

                    if result.success:
                        # 这里可以实现赔率变化检测逻辑
                        # 比如与之前的赔率进行比较，记录变化等
                        logger.debug(f"检查比赛 {match_id} 的赔率变化")
                    else:
                        logger.warning(f"无法获取比赛 {match_id} 的赔率: {result.error}")

                # 等待下一次检查
                await asyncio.sleep(check_interval)

            except Exception as e:
                logger.error(f"赔率监控过程中发生错误: {e}")
                await asyncio.sleep(60)  # 出错时等待1分钟后重试


# 便捷函数
async def collect_odds_for_match(match_id: int, api_key: str, base_url: str) -> Dict:
    """
    为单场比赛采集赔率的便捷函数

    Args:
        match_id: 比赛ID
        api_key: API密钥
        base_url: API基础URL

    Returns:
        Dict: 采集结果
    """
    collector = OddsCollector(
        api_key=api_key,
        base_url=base_url
    )

    result = await collector.collect_match_odds(match_id)

    if result.success:
        return {
            'success': True,
            'data': result.data,
            'message': f"成功采集比赛 {match_id} 的赔率数据"
        }
    else:
        return {
            'success': False,
            'error': result.error,
            'message': f"采集比赛 {match_id} 的赔率数据失败"
        }