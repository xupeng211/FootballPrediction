"""FotMob API 采集器 - 资深后端工程师重构版
Senior Backend Engineer Refactored Version

使用正确的鉴权头直接访问 FotMob API，无需浏览器自动化。
"""

import asyncio
import json
from typing import Any, , , Optional
import aiohttp
from src.core.logging import get_logger

logger = get_logger(__name__)


class EnhancedFotMobCollector:
    """FotMob API 采集器 - 正确鉴权版本."""

    def __init__(
        self,
        max_retries: int = 3,
        timeout: int = 30,
    ):
        self.max_retries = max_retries
        self.timeout = timeout
        self.client: Optional[aiohttp.ClientSession] = None

        # 统计信息
        self.stats = {
            "requests_made": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "matches_collected": 0,
        }

        logger.info("🔐 FotMob API采集器初始化完成 - 资深后端工程师版本")

    async def initialize(self):
        """初始化HTTP客户端 - 包含关键鉴权头."""
        # 🎯 这就是钥匙！FotMob API的正确鉴权头
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Referer": "https://www.fotmob.com/",
            "Origin": "https://www.fotmob.com",
            # 🔑 关键鉴权头 - 必须硬编码！
            "x-mas": "eyJib2R5Ijp7InVybCI6Ii9hcGkvZGF0YS9hdWRpby1tYXRjaGVzIiwiY29kZSI6MTc2NDA1NTcxMjgyOCwiZm9vIjoicHJvZHVjdGlvbjoyMDhhOGY4N2MyY2MxMzM0M2YxZGQ4NjcxNDcxY2Y1YTAzOWRjZWQzIn0sInNpZ25hdHVyZSI6IkMyMkI0MUQ5Njk2NUJBREM1NjMyNzcwRDgyNzVFRTQ4In0=",
            "x-foo": "production:208a8f87c2cc13343f1dd8671471cf5a039dced3",
        }

        # 创建HTTP客户端
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        self.client = aiohttp.ClientSession(
            headers=headers,
            timeout=timeout,
        )

        logger.info("🔐 HTTP客户端初始化完成 - 已加载FotMob关键鉴权头")

    async def collect_match_data(self, match_id: str) -> Optional[dict[str, Any]]:
        """采集单场比赛详情数据 - L2详情采集."""
        try:
            if not self.client:
                await self.initialize()

            # 🎯 正确的L2 API端点
            url = "https://www.fotmob.com/api/matchDetails"
            params = {"matchId": match_id}

            full_url = f"{url}?matchId={match_id}"
            logger.info(f"🎯 L2请求: {full_url}")

            async with self.client.get(url, params=params) as response:
                self.stats["requests_made"] += 1

                logger.info(f"🔍 L2响应状态码: {response.status}, URL: {full_url}")

                if response.status == 200:
                    data = await response.json()
                    self.stats["successful_requests"] += 1
                    self.stats["matches_collected"] += 1

                    # 🎯 关键验证：检查是否包含xG数据
                    if self._validate_data_quality(data, match_id):
                        logger.info(f"✅ L2采集成功: {match_id}")
                        return data
                    else:
                        logger.warning(f"⚠️ L2数据质量不足: {match_id}")
                        return None
                else:
                    response_text = await response.text()
                    logger.error(
                        f"❌ L2请求失败，状态码: {response.status}, URL: {full_url}"
                    )
                    logger.error(f"🔍 响应内容: {response_text[:200]}...")
                    self.stats["failed_requests"] += 1
                    return None

        except Exception as e:
            logger.error(f"❌ L2采集异常 {match_id}: {e}")
            import traceback

            logger.error(f"🔍 详细错误: {traceback.format_exc()}")
            self.stats["failed_requests"] += 1
            return None

    def _validate_data_quality(self, data: dict[str, Any], match_id: str) -> bool:
        """验证数据质量 - 确保包含关键ML特征"""
        try:
            # 检查基础结构
            if not data or "content" not in data:
                logger.warning(f"⚠️ 数据结构异常 {match_id}: 缺少content字段")
                return False

            content = data.get("content", {})

            # 检查xG数据（关键ML特征）
            has_xg = False
            if "stats" in content:
                stats = content.get("stats", {})
                # 检查各种可能的xG字段
                xg_fields = ["xg", "expectedGoals", "xG", "expected_goals"]
                for field in xg_fields:
                    if field in str(stats):
                        has_xg = True
                        break

            # 检查阵容数据
            has_lineups = "lineups" in content and content.get("lineups")

            # 检查赔率数据
            has_odds = False
            odds_fields = ["betting", "odds", "superlive", "preMatchOdds"]
            for field in odds_fields:
                if field in content and content.get(field):
                    has_odds = True
                    break

            # 至少需要一个关键特征
            quality_score = sum([has_xg, has_lineups, has_odds])

            logger.info(
                f"📊 数据质量评估 {match_id}: xG={has_xg}, lineups={has_lineups}, odds={has_odds}, score={quality_score}/3"
            )

            return quality_score >= 1  # 至少有一个特征

        except Exception as e:
            logger.error(f"❌ 数据质量验证失败 {match_id}: {e}")
            return False

    async def collect_matches_by_date(self, date_str: str) -> list[dict[str, Any]]:
        """按日期采集比赛列表 - L1列表采集."""
        try:
            if not self.client:
                await self.initialize()

            # 🎯 正确的L1 API端点 - 修正日期格式
            formatted_date = date_str.replace("-", "")  # 2024-12-04 -> 20241204
            url = "https://www.fotmob.com/api/matches"
            params = {
                "date": formatted_date,
                "timezone": "Asia/Shanghai",
                "ccode3": "CHN",
            }

            full_url = f"{url}?date={formatted_date}&timezone=Asia/Shanghai&ccode3=CHN"
            logger.info(f"🎯 L1请求: {full_url}")

            async with self.client.get(url, params=params) as response:
                self.stats["requests_made"] += 1

                logger.info(f"🔍 L1响应状态码: {response.status}, URL: {full_url}")

                if response.status == 200:
                    data = await response.json()
                    logger.info(f"✅ L1采集成功: {formatted_date}")

                    # 解析比赛数据
                    matches = []
                    if "matches" in data:
                        matches = data["matches"]
                    elif "leagues" in data:
                        for league in data["leagues"]:
                            if "matches" in league:
                                matches.extend(league["matches"])
                    else:
                        logger.info(f"🔍 L1数据结构: {list(data.keys())}")
                        for _key, value in data.items():
                            if (
                                isinstance(value, list)
                                and value
                                and isinstance(value[0], dict)
                            ):
                                matches.extend(value)
                                break

                    logger.info(f"✅ 解析到 {len(matches)} 场比赛")
                    return matches
                else:
                    response_text = await response.text()
                    logger.error(
                        f"❌ L1请求失败，状态码: {response.status}, URL: {full_url}"
                    )
                    logger.error(f"🔍 响应内容: {response_text[:200]}...")
                    return []

        except Exception as e:
            logger.error(f"❌ L1采集异常 {date_str}: {e}")
            import traceback

            logger.error(f"🔍 详细错误: {traceback.format_exc()}")
            return []

    async def batch_collect_matches(
        self, match_ids: list[str], delay_between_requests: float = 2.0
    ) -> list[dict[str, Any]]:
        """批量采集比赛数据."""
        results = []
        total_matches = len(match_ids)

        logger.info(f"🚀 开始批量采集 {total_matches} 场比赛数据")

        for i, match_id in enumerate(match_ids, 1):
            try:
                logger.info(f"🔄 采集进度: {i}/{total_matches} - 比赛 {match_id}")

                data = await self.collect_match_data(match_id)
                if data:
                    results.append(data)
                    logger.info(f"✅ 成功采集: {match_id}")
                else:
                    logger.warning(f"⚠️ 采集失败: {match_id}")

                # 智能延迟，避免触发反爬
                if i < total_matches:
                    delay = delay_between_requests + (i % 2) * 0.5  # 2.0-2.5秒变化延迟
                    await asyncio.sleep(delay)

            except Exception as e:
                logger.error(f"❌ 采集比赛 {match_id} 时发生错误: {e}")
                continue

        logger.info(f"🎉 批量采集完成，成功: {len(results)}/{total_matches}")
        return results

    def get_stats(self) -> dict[str, Any]:
        """获取采集器统计信息."""
        stats = self.stats.copy()

        # 添加成功率
        if stats["requests_made"] > 0:
            stats["success_rate"] = (
                stats["successful_requests"] / stats["requests_made"]
            )
        else:
            stats["success_rate"] = 0.0

        return stats

    async def close(self):
        """关闭采集器."""
        if self.client:
            await self.client.close()
            logger.info("🔐 HTTP客户端已关闭")

    async def __aenter__(self):
        """异步上下文管理器入口."""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口."""
        await self.close()


# 便捷函数
async def create_fotmob_collector(**kwargs) -> EnhancedFotMobCollector:
    """创建FotMob采集器."""
    return EnhancedFotMobCollector(**kwargs)
