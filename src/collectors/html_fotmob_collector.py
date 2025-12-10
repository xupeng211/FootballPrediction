#!/usr/bin/env python3
"""
FotMob HTML 数据采集器 - 异步标准化版本
FotMob HTML Data Collector - Async Standard Version

基于Async Base Class的标准化异步采集器
"""

import asyncio
import json
import logging
import random
import re
from typing import Optional, , Any, 
from datetime import datetime

import httpx
from httpx import AsyncClient, Response

from src.core.async_base import AsyncBaseCollector, AsyncConfig
from .user_agent import UserAgentManager

logger = logging.getLogger(__name__)


class AsyncHTMLFotMobCollector(AsyncBaseCollector):
    """
    FotMob HTML 异步数据采集器

    继承AsyncBaseCollector，使用标准异步基础设施
    """

    def __init__(
        self,
        max_retries: int = 3,
        timeout: int = 30,
        enable_stealth: bool = True,
        enable_proxy: bool = False,
    ):
        # 创建异步配置
        config = AsyncConfig(
            http_timeout=timeout,
            max_retries=max_retries,
            retry_delay=1.0,
            rate_limit_delay=0.5,  # 500ms间隔避免频率限制
        )

        # 初始化异步基类
        super().__init__(config=config, name="AsyncHTMLFotMobCollector")

        # FotMob特定配置
        self.max_retries = max_retries
        self.enable_stealth = enable_stealth
        self.enable_proxy = enable_proxy

        # 统计信息
        self.fotmob_stats = {
            "matches_collected": 0,
            "ua_switches": 0,
            "retry_count": 0,
        }

        # 用户代理管理器
        self.user_manager = UserAgentManager()
        self.current_headers = None
        self.last_rotation = 0.0

        logger.info("🕷️ FotMob HTML异步采集器初始化完成")

    async def _get_headers(self) -> dict[str, str]:
        """获取当前请求头"""
        if self.enable_stealth:
            await self._refresh_disguise()

        # 使用FotMob特定的请求头
        headers = await super()._get_headers()
        headers.update(
            {
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
                "Accept-Language": "en-GB,en;q=0.9,en;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Cache-Control": "max-age=0",
            }
        )

        return headers

    async def _get_user_agent(self) -> str:
        """获取FotMob特定的User-Agent"""
        if self.enable_stealth and self.user_manager:
            headers = self.user_manager.get_realistic_headers()
            return headers.get("User-Agent", await super()._get_user_agent())

        return await super()._get_user_agent()

    async def _refresh_disguise(self):
        """刷新User-Agent伪装"""
        if not self.enable_stealth:
            return

        # 检查是否需要轮换
        now = asyncio.get_event_loop().time()
        rotation_interval = 300  # 5分钟
        if now - self.last_rotation < rotation_interval:
            return

        if self.user_manager:
            self.current_headers = self.user_manager.get_realistic_headers()
            self.fotmob_stats["ua_switches"] += 1
            logger.info(f"🔄 User-Agent轮换 (#{self.fotmob_stats['ua_switches']})")

        self.last_rotation = now

    async def collect_match_data(self, match_id: str) -> Optional[dict[str, Any]]:
        """
        采集单场比赛数据

        Args:
            match_id (str): 比赛ID

        Returns:
            Optional[dict[str, Any]]: 比赛数据
        """
        try:
            url = f"https://www.fotmob.com/match/{match_id}"
            logger.info(f"🕷️ 请求比赛数据: {url}")

            # 20%概率刷新伪装
            if random.random() < 0.2:
                await self._refresh_disguise()

            # 发起异步请求
            response = await self.fetch_with_retry(url)

            logger.info(
                f"📊 响应状态: {response.status_code}, 大小: {len(response.text):,} 字符"
            )

            # 处理不同的响应状态
            if response.status_code in [200, 404]:
                self.fotmob_stats["matches_collected"] += 1

                # 检查是否包含Next.js数据
                if "__NEXT_DATA__" in response.text:
                    logger.info("✅ 发现Next.js SSR数据")

                    # 提取Next.js数据
                    nextjs_data = await self._extract_nextjs_data(
                        response.text, match_id
                    )

                    if nextjs_data:
                        # 提取content数据
                        content_data = await self._extract_content_data(
                            nextjs_data, match_id
                        )

                        if content_data:
                            logger.info(f"✅ 数据提取成功: {match_id}")
                            return {"match": {"id": match_id}, "content": content_data}
                        else:
                            logger.warning(f"⚠️ content数据提取失败: {match_id}")
                            return None
                    else:
                        logger.warning(f"⚠️ Next.js数据解析失败: {match_id}")
                        return None
                else:
                    if response.status_code == 404:
                        logger.info(f"ℹ️ 404页面无Next.js数据: {match_id}")
                    else:
                        logger.warning(f"⚠️ 页面无Next.js数据: {match_id}")
                    return None

            elif response.status_code == 429:
                logger.warning("⚠️ 触发频率限制")
                self.fotmob_stats["retry_count"] += 1
                await asyncio.sleep(random.uniform(10, 20))
                return await self.collect_match_data(match_id)

            elif response.status_code == 403:
                logger.warning("⚠️ 触发反爬检测")
                self.fotmob_stats["retry_count"] += 1
                await self._refresh_disguise()
                await asyncio.sleep(random.uniform(5, 10))
                return await self.collect_match_data(match_id)

            else:
                logger.error(f"❌ 未处理的状态码: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"❌ 采集异常 {match_id}: {e}")
            return None

    async def _extract_nextjs_data(
        self, html: str, match_id: str
    ) -> Optional[dict[str, Any]]:
        """
        从HTML中提取Next.js数据

        Args:
            html (str): HTML内容
            match_id (str): 比赛ID

        Returns:
            Optional[dict[str, Any]]: Next.js数据
        """
        try:
            # 改进的正则表达式，精确匹配script标签
            patterns = [
                r'<script[^>]*id=["\']__NEXT_DATA__["\'][^>]*typing.Type=["\']application/json["\'][^>]*>(.*?)</script>',
                r'<script[^>]*id=["\']__NEXT_DATA__["\'][^>]*>(.*?)</script>',
                r"window\.__NEXT_DATA__\s*=\s*(\{.*?\});?\s*<\/script>",
            ]

            for pattern in patterns:
                matches = re.findall(pattern, html, re.DOTALL)
                if matches:
                    nextjs_data_str = matches[0].strip()

                    # 清理可能的JavaScript包装
                    if nextjs_data_str.startswith("window.__NEXT_DATA__"):
                        nextjs_data_str = (
                            nextjs_data_str.replace("window.__NEXT_DATA__", "")
                            .replace("=", "")
                            .strip()
                        )
                        if nextjs_data_str.endswith(";"):
                            nextjs_data_str = nextjs_data_str[:-1]

                    try:
                        nextjs_data = json.loads(nextjs_data_str)
                        logger.info(f"✅ Next.js JSON解析成功: {match_id}")
                        return nextjs_data
                    except json.JSONDecodeError as e:
                        logger.warning(f"⚠️ JSON解析失败 {match_id}: {e}")
                        logger.debug(f"   数据预览: {nextjs_data_str[:200]}...")
                        continue

            logger.warning(f"⚠️ 未找到__NEXT_DATA__: {match_id}")
            return None

        except Exception as e:
            logger.error(f"❌ Next.js提取异常 {match_id}: {e}")
            return None

    async def _extract_content_data(
        self, nextjs_data: dict[str, Any], match_id: str
    ) -> Optional[dict[str, Any]]:
        """
        从Next.js数据中提取content

        Args:
            nextjs_data (dict[str, Any]): Next.js数据
            match_id (str): 比赛ID

        Returns:
            Optional[dict[str, Any]]: content数据
        """
        try:
            props = nextjs_data.get("props", {})
            if not props:
                logger.warning(f"⚠️ 未找到props: {match_id}")
                return None

            page_props = props.get("pageProps", {})
            if not page_props:
                # 检查是否是404页面
                url = props.get("url", "")
                if "/404" in url:
                    logger.info(f"ℹ️ 跳过404页面: {match_id}")
                return None

            content = page_props.get("content", {})
            if not content:
                logger.warning(f"⚠️ 未找到content: {match_id}")
                return None

            logger.info(f"✅ 成功提取content: {match_id}")
            logger.info(f"   Content Keys: {list(content.keys())}")

            # 验证ML特征字段
            required_features = [
                "matchFacts",
                "stats",
                "lineup",
                "shotmap",
                "playerStats",
            ]
            found_features = [
                feature for feature in required_features if feature in content
            ]

            logger.info(f"   找到ML特征: {found_features}/{len(required_features)}")

            # 检查xG数据
            if "stats" in content:
                stats = content.get("stats", {})
                if isinstance(stats, dict):
                    periods = stats.get("Periods", {})
                    all_stats = periods.get("All", {})
                    stats_list = all_stats.get("stats", [])

                    xg_found = False
                    for stat_group in stats_list:
                        if isinstance(stat_group, dict) and "stats" in stat_group:
                            for stat in stat_group.get("stats", []):
                                if isinstance(stat, dict):
                                    title = stat.get("title", "").lower()
                                    if "expected goals" in title or "xg" in title:
                                        xg_values = stat.get("stats", [])
                                        if xg_values and len(xg_values) >= 2:
                                            logger.info(
                                                f"🎯 找到xG数据: 主队={xg_values[0]}, 客队={xg_values[1]}"
                                            )
                                            xg_found = True
                                            break
                        if xg_found:
                            break

                    if not xg_found:
                        logger.info(f"ℹ️ 未找到xG数据: {match_id}")

            return content

        except Exception as e:
            logger.error(f"❌ content提取异常 {match_id}: {e}")
            import traceback

            logger.debug(f"🔍 详细错误: {traceback.format_exc()}")
            return None

    async def get_stats(self) -> dict[str, Any]:
        """获取采集统计信息"""
        # 获取基类统计
        base_stats = super().get_stats()

        # 添加FotMob特定统计
        fotmob_stats = self.fotmob_stats.copy()
        fotmob_stats.update(base_stats)

        fotmob_stats["stealth_mode"] = self.enable_stealth
        fotmob_stats["proxy_enabled"] = self.enable_proxy
        fotmob_stats["collection_rate"] = fotmob_stats["matches_collected"] / max(
            fotmob_stats["total_requests"], 1
        )

        return fotmob_stats


# 向后兼容的别名
HTMLFotMobCollector = AsyncHTMLFotMobCollector
