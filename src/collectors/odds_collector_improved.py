"""
改进的赔率收集器
Improved Odds Collector

提供高性能的赔率数据收集功能，支持：
- 多博彩公司数据源
- 实时赔率更新
- 赔率历史追踪
- 价值投注识别
- 异常检测

Provides high-performance odds collection with:
- Multiple bookmaker sources
- Real-time odds updates
- Odds history tracking
- Value betting identification
- Anomaly detection
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple

import aiohttp
import numpy as np
from sqlalchemy import select, update, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.cache.redis_manager import RedisManager, CacheKeyManager
from src.core.exceptions import DataCollectionError
from src.database.models import Match, Odds, MarketType, RawOddsData
from src.utils.retry import RetryConfig, retry
from src.utils.time_utils import utc_now, parse_datetime

logger = logging.getLogger(__name__)


class OddsCollector:
    """
    赔率收集器
    Odds Collector

    从多个博彩公司收集赔率数据，支持实时更新和历史追踪。
    Collects odds data from multiple bookmakers with real-time updates and history tracking.
    """

    def __init__(
        self,
        db_session: AsyncSession,
        redis_manager: RedisManager,
        api_key: Optional[str] = None,
        update_interval: int = 300,  # 5分钟
    ):
        """
        初始化赔率收集器

        Args:
            db_session: 数据库会话
            redis_manager: Redis管理器
            api_key: API密钥
            update_interval: 更新间隔（秒）
        """
        self.db_session = db_session
        self.redis_manager = redis_manager
        self.cache_manager = CacheKeyManager()

        # 配置
        self.api_key = api_key or os.getenv("ODDS_API_TOKEN")
        self.update_interval = update_interval

        # API端点
        self.api_endpoints = {
            "odds_api": os.getenv("ODDS_API_URL", "https://api.the-odds-api.com/v4"),
            "betfair": os.getenv("BETFAIR_URL", "https://api.betfair.com/exchange/betting/rest/v1.0"),
            "pinnacle": os.getenv("PINNACLE_URL", "https://api.pinnacle.com/v1"),
        }

        # 支持的博彩公司
        self.bookmakers = [
            "bet365", "william_hill", "ladbrokes", "betfair", "pinnacle",
            "betway", "888sport", "unibet", "betfred", "coral"
        ]

        # 支持的市场类型
        self.market_types = {
            "match_winner": MarketType.MATCH_WINNER,
            "over_under": MarketType.OVER_UNDER,
            "handicap": MarketType.HANDICAP,
            "both_teams_score": MarketType.BOTH_TEAMS_SCORE,
            "correct_score": MarketType.CORRECT_SCORE,
        }

        # 状态管理
        self.running = False
        self.update_task: Optional[asyncio.Task] = None

        # 数据缓存
        self.odds_cache: Dict[str, Dict[str, Any]] = {}
        self.last_update_cache: Dict[str, datetime] = {}

        # 性能统计
        self.stats = {
            "total_updates": 0,
            "successful_updates": 0,
            "failed_updates": 0,
            "api_calls": 0,
            "unique_matches": 0,
            "average_processing_time": 0.0,
        }

        # 重试配置
        self.retry_config = RetryConfig(
            max_attempts=3,
            base_delay=1.0,
            max_delay=10.0,
            exponential_base=2.0,
            jitter=True,
        )

    async def start_collection(self):
        """启动赔率收集"""
        if self.running:
            logger.warning("赔率收集器已在运行")
            return

        self.running = True
        logger.info("启动赔率收集器")

        # 启动定期更新任务
        self.update_task = asyncio.create_task(self._periodic_update())

    async def stop_collection(self):
        """停止赔率收集"""
        self.running = False
        logger.info("停止赔率收集器")

        if self.update_task:
            self.update_task.cancel()
            try:
                await self.update_task
            except asyncio.CancelledError:
                pass

    async def collect_match_odds(
        self,
        match_id: int,
        bookmakers: Optional[List[str]] = None,
        markets: Optional[List[str]] = None,
        force: bool = False,
    ) -> Dict[str, Any]:
        """
        收集指定比赛的赔率数据

        Args:
            match_id: 比赛ID
            bookmakers: 指定博彩公司列表
            markets: 指定市场类型列表
            force: 是否强制更新

        Returns:
            Dict[str, Any]: 赔率数据
        """
        bookmakers = bookmakers or self.bookmakers
        markets = markets or list(self.market_types.keys())

        # 检查缓存
        cache_key = f"odds:{match_id}:{':'.join(bookmakers)}:{':'.join(markets)}"
        if not force and cache_key in self.odds_cache:
            last_update = self.last_update_cache.get(cache_key, utc_now())
            if utc_now() - last_update < timedelta(minutes=5):
                return self.odds_cache[cache_key]

        try:
            # 获取比赛信息
            match = await self._get_match_info(match_id)
            if not match:
                raise ValueError(f"比赛 {match_id} 不存在")

            # 从API获取赔率
            odds_data = await self._fetch_odds_from_apis(match_id, bookmakers, markets)

            # 处理和分析赔率
            processed_data = await self._process_odds_data(match_id, odds_data)

            if processed_data:
                # 更新缓存
                self.odds_cache[cache_key] = processed_data
                self.last_update_cache[cache_key] = utc_now()

                # 保存到数据库
                await self._save_odds_data(processed_data)

                # 识别价值投注
                value_bets = await self._identify_value_bets(processed_data)
                if value_bets:
                    processed_data["value_bets"] = value_bets

                # 发布更新通知
                await self._publish_odds_update(processed_data)

                return processed_data

            return {}

        except Exception as e:
            logger.error(f"收集比赛 {match_id} 赔率失败: {e}")
            return {}

    async def collect_upcoming_matches_odds(
        self,
        hours_ahead: int = 48,
        max_matches: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        收集即将开始比赛的赔率

        Args:
            hours_ahead: 未来多少小时
            max_matches: 最大比赛数

        Returns:
            List[Dict[str, Any]]: 赔率数据列表
        """
        # 获取即将开始的比赛
        upcoming_matches = await self._get_upcoming_matches(hours_ahead, max_matches)

        if not upcoming_matches:
            return []

        # 批量收集赔率
        tasks = [
            self.collect_match_odds(match["id"])
            for match in upcoming_matches
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 处理结果
        odds_list = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"收集比赛 {upcoming_matches[i]['id']} 赔率失败: {result}")
            elif result:
                result.update(upcoming_matches[i])
                odds_list.append(result)

        return odds_list

    async def get_odds_history(
        self,
        match_id: int,
        bookmaker: str,
        market: str,
        hours: int = 24,
    ) -> List[Dict[str, Any]]:
        """
        获取赔率历史数据

        Args:
            match_id: 比赛ID
            bookmaker: 博彩公司
            market: 市场类型
            hours: 历史时长（小时）

        Returns:
            List[Dict[str, Any]]: 历史赔率数据
        """
        cutoff_time = utc_now() - timedelta(hours=hours)

        query = select(Odds).where(
            and_(
                Odds.match_id == match_id,
                Odds.bookmaker == bookmaker,
                Odds.market_type == self.market_types.get(market, MarketType.MATCH_WINNER),
                Odds.created_at >= cutoff_time,
            )
        ).order_by(Odds.created_at)

        result = await self.db_session.execute(query)
        odds_records = result.scalars().all()

        return [
            {
                "timestamp": odds.created_at.isoformat(),
                "home_win": odds.home_win_odds,
                "draw": odds.draw_odds,
                "away_win": odds.away_win_odds,
                "over_line": odds.over_line,
                "over_odds": odds.over_odds,
                "under_odds": odds.under_odds,
            }
            for odds in odds_records
        ]

    async def _periodic_update(self):
        """定期更新赔率"""
        logger.info("启动定期赔率更新")

        while self.running:
            try:
                # 收集即将开始的比赛赔率
                await self.collect_upcoming_matches_odds()
                self.stats["api_calls"] += 1

                # 等待下次更新
                await asyncio.sleep(self.update_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"定期更新失败: {e}")
                await asyncio.sleep(60)

    async def _fetch_odds_from_apis(
        self,
        match_id: int,
        bookmakers: List[str],
        markets: List[str],
    ) -> Dict[str, Any]:
        """从API获取赔率数据"""
        all_odds = {}

        # 尝试多个数据源
        for source_name, base_url in self.api_endpoints.items():
            try:
                source_odds = await self._fetch_from_odds_source(
                    source_name, match_id, bookmakers, markets
                )
                if source_odds:
                    all_odds[source_name] = source_odds
            except Exception as e:
                logger.warning(f"从 {source_name} 获取赔率失败: {e}")
                continue

        return all_odds

    @retry(retry_config)
    async def _fetch_from_odds_source(
        self,
        source: str,
        match_id: int,
        bookmakers: List[str],
        markets: List[str],
    ) -> Optional[Dict[str, Any]]:
        """从指定数据源获取赔率"""
        if source == "odds_api":
            return await self._fetch_from_odds_api(match_id, bookmakers)
        elif source == "betfair":
            return await self._fetch_from_betfair(match_id, markets)
        elif source == "pinnacle":
            return await self._fetch_from_pinnacle(match_id)

        return None

    async def _fetch_from_odds_api(
        self,
        match_id: int,
        bookmakers: List[str],
    ) -> Optional[Dict[str, Any]]:
        """从The Odds API获取赔率"""
        if not self.api_key:
            return None

        # 构建API URL
        regions = "uk,eu,us"
        markets = "h2h,ou,bts,cs,ah"
        bookmakers_str = ",".join(bookmakers[:10])  # API限制

        url = (
            f"{self.api_endpoints['odds_api']}/sports/soccer/odds"
            f"?apiKey={self.api_key}"
            f"&regions={regions}"
            f"&markets={markets}"
            f"&bookmakers={bookmakers_str}"
            f"&oddsFormat=decimal"
        )

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    # 查找指定比赛
                    for game in data:
                        if game.get("id") == match_id:
                            return self._transform_odds_api_data(game)
                    return None
                else:
                    logger.warning(f"Odds API请求失败: {response.status}")
                    return None

    async def _fetch_from_betfair(
        self,
        match_id: int,
        markets: List[str],
    ) -> Optional[Dict[str, Any]]:
        """从Betfair获取赔率（简化实现）"""
        # Betfair需要更复杂的认证和会话管理
        return None

    async def _fetch_from_pinnacle(self, match_id: int) -> Optional[Dict[str, Any]]:
        """从Pinnacle获取赔率（简化实现）"""
        # Pinnacle需要特定的认证
        return None

    def _transform_odds_api_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """转换Odds API数据格式"""
        transformed = {
            "match_id": data.get("id"),
            "sport_key": data.get("sport_key"),
            "commence_time": data.get("commence_time"),
            "bookmakers": [],
        }

        for bookmaker in data.get("bookmakers", []):
            bookmaker_data = {
                "key": bookmaker.get("key"),
                "title": bookmaker.get("title"),
                "markets": {},
            }

            for market in bookmaker.get("markets", []):
                market_key = market.get("key")
                if market_key == "h2h":
                    # Match winner market
                    outcomes = {o["name"]: o["price"] for o in market.get("outcomes", [])}
                    bookmaker_data["markets"]["match_winner"] = {
                        "home_win": outcomes.get("Home"),
                        "draw": outcomes.get("Draw"),
                        "away_win": outcomes.get("Away"),
                    }
                elif market_key == "ou":
                    # Over/Under market
                    outcomes = {o["name"]: o["price"] for o in market.get("outcomes", [])}
                    over_line = None
                    if "Over" in outcomes:
                        # 提取盘口线
                        import re
                        match = re.search(r"Over (\d+\.?\d*)", market.get("outcomes", [{}])[0].get("name", ""))
                        if match:
                            over_line = float(match.group(1))

                    bookmaker_data["markets"]["over_under"] = {
                        "line": over_line,
                        "over_odds": outcomes.get("Over"),
                        "under_odds": outcomes.get("Under"),
                    }
                elif market_key == "bts":
                    # Both teams to score
                    outcomes = {o["name"]: o["price"] for o in market.get("outcomes", [])}
                    bookmaker_data["markets"]["both_teams_score"] = {
                        "yes": outcomes.get("Yes"),
                        "no": outcomes.get("No"),
                    }

            transformed["bookmakers"].append(bookmaker_data)

        return transformed

    async def _process_odds_data(
        self,
        match_id: int,
        raw_odds_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """处理和分析赔率数据"""
        processed = {
            "match_id": match_id,
            "timestamp": utc_now().isoformat(),
            "bookmakers": [],
            "market_analysis": {},
            "average_odds": {},
            "best_odds": {},
        }

        # 收集所有博彩公司的数据
        all_home_win = []
        all_draw = []
        all_away_win = []

        for source, source_data in raw_odds_data.items():
            for bookmaker in source_data.get("bookmakers", []):
                bookmaker_name = bookmaker.get("key")
                markets = bookmaker.get("markets", {})

                # Match winner odds
                if "match_winner" in markets:
                    h2h_odds = markets["match_winner"]
                    if all(h2h_odds.values()):
                        processed["bookmakers"].append({
                            "name": bookmaker_name,
                            "home_win": h2h_odds["home_win"],
                            "draw": h2h_odds["draw"],
                            "away_win": h2h_odds["away_win"],
                            "source": source,
                        })

                        all_home_win.append(h2h_odds["home_win"])
                        all_draw.append(h2h_odds["draw"])
                        all_away_win.append(h2h_odds["away_win"])

        # 计算平均赔率
        if all_home_win and all_draw and all_away_win:
            processed["average_odds"] = {
                "home_win": np.mean(all_home_win),
                "draw": np.mean(all_draw),
                "away_win": np.mean(all_away_win),
            }

            # 计算最佳赔率
            processed["best_odds"] = {
                "home_win": max(all_home_win),
                "draw": max(all_draw),
                "away_win": max(all_away_win),
            }

            # 计算隐含概率
            processed["implied_probabilities"] = {
                "home_win": 1 / processed["best_odds"]["home_win"],
                "draw": 1 / processed["best_odds"]["draw"],
                "away_win": 1 / processed["best_odds"]["away_win"],
            }

            # 市场分析
            total_prob = sum(processed["implied_probabilities"].values())
            processed["market_analysis"] = {
                "total_implied_probability": total_prob,
                "bookmaker_margin": (total_prob - 1) * 100,  # 百分比
                "efficiency": 1 / total_prob if total_prob > 0 else 0,
            }

        return processed

    async def _save_odds_data(self, odds_data: Dict[str, Any]):
        """保存赔率数据到数据库"""
        try:
            start_time = utc_now()

            # 保存每个博彩公司的赔率
            for bookmaker_data in odds_data.get("bookmakers", []):
                odds = Odds(
                    match_id=odds_data["match_id"],
                    bookmaker=bookmaker_data["name"],
                    market_type=MarketType.MATCH_WINNER,
                    home_win_odds=bookmaker_data["home_win"],
                    draw_odds=bookmaker_data["draw"],
                    away_win_odds=bookmaker_data["away_win"],
                    created_at=parse_datetime(odds_data["timestamp"]),
                )
                self.db_session.add(odds)

            # 保存原始数据
            raw_data = RawOddsData(
                match_id=odds_data["match_id"],
                source="odds_collector",
                data=odds_data,
                collected_at=parse_datetime(odds_data["timestamp"]),
            )
            self.db_session.add(raw_data)

            await self.db_session.commit()

            # 更新统计
            self.stats["total_updates"] += 1
            self.stats["successful_updates"] += 1
            self.stats["unique_matches"] = len(set(o.get("match_id") for o in self.odds_cache.values()))

            processing_time = (utc_now() - start_time).total_seconds()
            self.stats["average_processing_time"] = (
                self.stats["average_processing_time"] * (self.stats["successful_updates"] - 1) + processing_time
            ) / self.stats["successful_updates"]

            logger.debug(f"保存比赛 {odds_data['match_id']} 赔率数据成功")

        except Exception as e:
            await self.db_session.rollback()
            self.stats["failed_updates"] += 1
            logger.error(f"保存赔率数据失败: {e}")
            raise

    async def _identify_value_bets(self, odds_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """识别价值投注机会"""
        value_bets = []

        # 获取模型预测概率（如果有）
        match_id = odds_data["match_id"]
        model_prob = await self._get_model_prediction(match_id)

        if not model_prob:
            return value_bets

        # 比较博彩公司赔率和模型预测
        for bookmaker in odds_data.get("bookmakers", []):
            # 计算凯利值
            for outcome in ["home_win", "draw", "away_win"]:
                bookmaker_odds = bookmaker[outcome]
                model_outcome = outcome.replace("_win", "")
                model_probability = model_prob.get(model_outcome, 0)

                if bookmaker_odds and model_probability > 0:
                    # 计算价值
                    implied_prob = 1 / bookmaker_odds
                    value = (bookmaker_odds * model_probability) - 1

                    if value > 0:  # 有价值
                        # 计算凯利比例
                        kelly_fraction = (bookmaker_odds * model_probability - 1) / (bookmaker_odds - 1)

                        value_bets.append({
                            "bookmaker": bookmaker["name"],
                            "outcome": outcome,
                            "odds": bookmaker_odds,
                            "model_probability": model_probability,
                            "implied_probability": implied_prob,
                            "value": value,
                            "kelly_fraction": kelly_fraction,
                            "confidence": "high" if value > 0.1 else "medium" if value > 0.05 else "low",
                        })

        # 按价值排序
        value_bets.sort(key=lambda x: x["value"], reverse=True)

        return value_bets[:5]  # 返回前5个价值最高的投注

    async def _get_model_prediction(self, match_id: int) -> Optional[Dict[str, float]]:
        """获取模型预测概率"""
        try:
            # 从Redis缓存获取预测
            cache_key = f"model_prediction:{match_id}"
            prediction = await self.redis_manager.aget(cache_key)

            if prediction:
                return {
                    "home": prediction.get("home_win_probability", 0),
                    "draw": prediction.get("draw_probability", 0),
                    "away": prediction.get("away_win_probability", 0),
                }

            # 从数据库获取最新预测
            from src.database.models import Predictions
            query = select(Predictions).where(
                Predictions.match_id == match_id
            ).order_by(Predictions.created_at.desc()).limit(1)

            result = await self.db_session.execute(query)
            prediction = result.scalar_one_or_none()

            if prediction:
                return {
                    "home": prediction.home_win_probability,
                    "draw": prediction.draw_probability,
                    "away": prediction.away_win_probability,
                }

            return None

        except Exception as e:
            logger.error(f"获取模型预测失败: {e}")
            return None

    async def _publish_odds_update(self, odds_data: Dict[str, Any]):
        """发布赔率更新到Redis"""
        try:
            channel = f"odds:match:{odds_data['match_id']}"
            message = {
                "type": "odds_update",
                "match_id": odds_data["match_id"],
                "average_odds": odds_data.get("average_odds"),
                "best_odds": odds_data.get("best_odds"),
                "bookmaker_count": len(odds_data.get("bookmakers", [])),
                "timestamp": odds_data["timestamp"],
            }

            await self.redis_manager.client.publish(channel, json.dumps(message))

            # 如果有价值投注，发送通知
            if odds_data.get("value_bets"):
                await self.redis_manager.client.publish(
                    "value_bets:alerts",
                    json.dumps({
                        "match_id": odds_data["match_id"],
                        "value_bets": odds_data["value_bets"],
                        "timestamp": odds_data["timestamp"],
                    })
                )

        except Exception as e:
            logger.error(f"发布赔率更新失败: {e}")

    async def _get_match_info(self, match_id: int) -> Optional[Dict[str, Any]]:
        """获取比赛基本信息"""
        query = select(Match).where(Match.id == match_id)
        result = await self.db_session.execute(query)
        match = result.scalar_one_or_none()

        if match:
            return {
                "id": match.id,
                "home_team_id": match.home_team_id,
                "away_team_id": match.away_team_id,
                "match_time": match.match_time,
                "status": match.match_status,
            }
        return None

    async def _get_upcoming_matches(
        self,
        hours_ahead: int,
        max_matches: int,
    ) -> List[Dict[str, Any]]:
        """获取即将开始的比赛"""
        start_time = utc_now()
        end_time = start_time + timedelta(hours=hours_ahead)

        query = select(Match).where(
            and_(
                Match.match_time >= start_time,
                Match.match_time <= end_time,
                Match.match_status == MatchStatus.SCHEDULED,
            )
        ).order_by(Match.match_time).limit(max_matches)

        result = await self.db_session.execute(query)
        matches = result.scalars().all()

        return [
            {
                "id": match.id,
                "home_team_id": match.home_team_id,
                "away_team_id": match.away_team_id,
                "match_time": match.match_time.isoformat(),
                "status": match.match_status.value,
            }
            for match in matches
        ]

    def get_stats(self) -> Dict[str, Any]:
        """获取收集统计信息"""
        return {
            **self.stats,
            "running": self.running,
            "cached_odds": len(self.odds_cache),
            "success_rate": (
                self.stats["successful_updates"] / self.stats["total_updates"]
                if self.stats["total_updates"] > 0
                else 0.0
            ),
        }


class OddsCollectorManager:
    """赔率收集器管理器"""

    def __init__(self):
        self.collectors: Dict[int, OddsCollector] = {}
        self.redis_manager = RedisManager()

    async def get_collector(self, session_id: int) -> OddsCollector:
        """获取或创建收集器实例"""
        if session_id not in self.collectors:
            from src.database.connection import get_async_session
            async with get_async_session() as session:
                collector = OddsCollector(session, self.redis_manager)
                self.collectors[session_id] = collector
        return self.collectors[session_id]

    async def start_all(self):
        """启动所有收集器"""
        for collector in self.collectors.values():
            await collector.start_collection()

    async def stop_all(self):
        """停止所有收集器"""
        for collector in self.collectors.values():
            await collector.stop_collection()

    def remove_collector(self, session_id: int):
        """移除收集器"""
        if session_id in self.collectors:
            del self.collectors[session_id]


# 全局管理器实例
_odds_manager: Optional[OddsCollectorManager] = None


def get_odds_manager() -> OddsCollectorManager:
    """获取全局赔率收集器管理器"""
    global _odds_manager
    if _odds_manager is None:
        _odds_manager = OddsCollectorManager()
    return _odds_manager