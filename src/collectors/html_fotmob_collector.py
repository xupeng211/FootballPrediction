#!/usr/bin/env python3
"""
FotMob HTML 数据采集器 - QA验证版本
FotMob HTML Data Collector - QA Verified Version

经过调试验证的稳定版本，专注于核心功能和xG数据提取
"""

import asyncio
import json
import logging
import random
import re
import time
from typing import Optional, Dict, Any, List
from datetime import datetime

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .user_agent import UserAgentManager

logger = logging.getLogger(__name__)


class HTMLFotMobCollector:
    """FotMob HTML 数据采集器 - QA验证版本"""

    def __init__(
        self,
        max_retries: int = 3,
        timeout: int = 30,
        enable_stealth: bool = True,  # 强制启用隐身模式对抗Docker检测
        enable_proxy: bool = False,
    ):
        self.max_retries = max_retries
        self.timeout = (10, 30)  # 连接超时10秒，读取超时30秒
        self.enable_stealth = enable_stealth
        self.enable_proxy = enable_proxy

        # 统计信息
        self.stats = {
            "requests_made": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "matches_collected": 0,
            "ua_switches": 0,
            "retry_count": 0,
        }

        # 会话和用户代理
        self.session = None
        # 强制初始化用户代理管理器以对抗Docker检测
        self.user_manager = UserAgentManager()
        self.current_headers = None
        self.last_rotation = time.time()

        logger.info("🕷️ FotMob HTML采集器初始化完成 - QA验证版本")

    async def initialize(self):
        """初始化HTTP客户端"""
        # 不使用Session避免Docker环境下的反爬检测
        self.session = None

        # 初始化伪装
        await self._refresh_disguise()

        logger.info("✅ HTTP客户端初始化完成")

    async def _refresh_disguise(self):
        """刷新User-Agent伪装"""
        if not self.enable_stealth:
            return

        # 检查是否需要轮换
        now = time.time()
        rotation_interval = 300  # 5分钟
        if now - self.last_rotation < rotation_interval:
            return

        if self.user_manager:
            self.current_headers = self.user_manager.get_realistic_headers()
            self.stats["ua_switches"] += 1

        self.last_rotation = now

    def _get_current_headers(self) -> dict[str, str]:
        """获取当前请求头"""
        # 使用标准的浏览器请求头，让requests自动处理GZIP解压
        return {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-GB,en;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',  # 让requests自动处理GZIP
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }

    async def collect_match_data(self, match_id: str) -> Optional[dict[str, Any]]:
        """
        采集单场比赛数据 - QA验证版本

        关键逻辑：
        1. 遇到404状态码不返回None，继续解析response.text
        2. 使用正则提取__NEXT_DATA__ JSON
        3. 解析props.pageProps.content提取核心数据
        """
        try:
            url = f"https://www.fotmob.com/match/{match_id}"
            logger.info(f"🕷️ 请求比赛数据: {url}")

            # 定期刷新伪装
            if random.random() < 0.2:  # 20%概率刷新伪装
                await self._refresh_disguise()

            # 发起请求
            headers = self._get_current_headers()

            response = requests.get(
                url,
                headers=headers,
                timeout=self.timeout,
                allow_redirects=True,
                verify=False  # 禁用SSL验证，避免Docker环境证书问题
            )

            self.stats["requests_made"] += 1

            logger.info(f"📊 响应状态: {response.status_code}, 大小: {len(response.text):,} 字符")

            # 🎯 关键处理：即使是404也要继续解析
            if response.status_code in [200, 404]:
                self.stats["successful_requests"] += 1

                # 检查是否包含Next.js数据
                if '__NEXT_DATA__' in response.text:
                    logger.info("✅ 发现Next.js SSR数据")

                    # 🎯 关键：提取Next.js数据
                    nextjs_data = self._extract_nextjs_data(response.text, match_id)

                    if nextjs_data:
                        # 🎯 关键：提取content数据
                        content_data = self._extract_content_data(nextjs_data, match_id)

                        if content_data:
                            self.stats["matches_collected"] += 1
                            logger.info(f"✅ 数据提取成功: {match_id}")

                            # 返回标准API格式
                            return {
                                "match": {"id": match_id},
                                "content": content_data
                            }
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
                self.stats["retry_count"] += 1
                await asyncio.sleep(random.uniform(10, 20))
                return await self.collect_match_data(match_id)

            elif response.status_code == 403:
                logger.warning("⚠️ 触发反爬检测")
                self.stats["retry_count"] += 1
                await self._refresh_disguise()
                await asyncio.sleep(random.uniform(5, 10))
                return await self.collect_match_data(match_id)

            else:
                logger.error(f"❌ 未处理的状态码: {response.status_code}")
                self.stats["failed_requests"] += 1
                return None

        except Exception as e:
            logger.error(f"❌ 采集异常 {match_id}: {e}")
            self.stats["failed_requests"] += 1
            return None

    def _manual_decompress_response(self, response) -> str:
        """手动解压响应内容（处理GZIP压缩问题）"""
        try:
            # 检查是否需要手动解压GZIP
            if hasattr(response, 'content') and response.content:
                # 检查GZIP魔数 (1f 8b)
                if response.content[:2] == b'\x1f\x8b':
                    import gzip
                    import io
                    try:
                        decompressed = gzip.GzipFile(fileobj=io.BytesIO(response.content)).read().decode('utf-8')
                        self.logger.info("✅ 手动GZIP解压成功")
                        return decompressed
                    except Exception as e:
                        self.logger.error(f"❌ 手动GZIP解压失败: {e}")
                        # 回退到原始文本
                        if hasattr(response, 'text'):
                            return response.text
                        else:
                            return response.content.decode('utf-8', errors='ignore')

            # 如果不是GZIP，尝试正常方式
            if hasattr(response, 'text'):
                return response.text
            else:
                return response.content.decode('utf-8', errors='ignore')

        except Exception as e:
            self.logger.error(f"❌ 响应解压异常: {e}")
            # 最后回退方案
            try:
                return str(response.content, errors='ignore')
            except:
                return ""

    def _extract_nextjs_data(self, html: str, match_id: str) -> Optional[dict[str, Any]]:
        """
        从HTML中提取Next.js数据 - QA验证版本

        🎯 关键：使用正则表达式精确匹配__NEXT_DATA__ JSON
        """
        try:
            # 改进的正则表达式，精确匹配script标签
            patterns = [
                r'<script[^>]*id=["\']__NEXT_DATA__["\'][^>]*type=["\']application/json["\'][^>]*>(.*?)</script>',
                r'<script[^>]*id=["\']__NEXT_DATA__["\'][^>]*>(.*?)</script>',
                r'window\.__NEXT_DATA__\s*=\s*(\{.*?\});?\s*<\/script>'
            ]

            for pattern in patterns:
                matches = re.findall(pattern, html, re.DOTALL)
                if matches:
                    nextjs_data_str = matches[0].strip()

                    # 清理可能的JavaScript包装
                    if nextjs_data_str.startswith('window.__NEXT_DATA__'):
                        nextjs_data_str = nextjs_data_str.replace('window.__NEXT_DATA__', '').replace('=', '').strip()
                        if nextjs_data_str.endswith(';'):
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

    def _extract_content_data(self, nextjs_data: dict[str, Any], match_id: str) -> Optional[dict[str, Any]]:
        """
        从Next.js数据中提取content - QA验证版本

        🎯 关键：解析props.pageProps.content并提取ML特征
        """
        try:
            props = nextjs_data.get('props', {})
            if not props:
                logger.warning(f"⚠️ 未找到props: {match_id}")
                return None

            page_props = props.get('pageProps', {})
            if not page_props:
                # 检查是否是404页面
                url = props.get('url', '')
                if '/404' in url:
                    logger.info(f"ℹ️ 跳过404页面: {match_id}")
                return None

            content = page_props.get('content', {})
            if not content:
                logger.warning(f"⚠️ 未找到content: {match_id}")
                return None

            logger.info(f"✅ 成功提取content: {match_id}")
            logger.info(f"   Content Keys: {list(content.keys())}")

            # 🎯 关键：验证ML特征字段
            required_features = ['matchFacts', 'stats', 'lineup', 'shotmap', 'playerStats']
            found_features = [feature for feature in required_features if feature in content]

            logger.info(f"   找到ML特征: {found_features}/{len(required_features)}")

            # 🎯 关键：检查xG数据
            if 'stats' in content:
                stats = content.get('stats', {})
                if isinstance(stats, dict):
                    periods = stats.get('Periods', {})
                    all_stats = periods.get('All', {})
                    stats_list = all_stats.get('stats', [])

                    xg_found = False
                    for stat_group in stats_list:
                        if isinstance(stat_group, dict) and 'stats' in stat_group:
                            for stat in stat_group.get('stats', []):
                                if isinstance(stat, dict):
                                    title = stat.get('title', '').lower()
                                    if 'expected goals' in title or 'xg' in title:
                                        xg_values = stat.get('stats', [])
                                        if xg_values and len(xg_values) >= 2:
                                            logger.info(f"🎯 找到xG数据: 主队={xg_values[0]}, 客队={xg_values[1]}")
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

    def get_stats(self) -> dict[str, Any]:
        """获取采集统计信息"""
        stats = self.stats.copy()
        if stats["requests_made"] > 0:
            stats["success_rate"] = stats["successful_requests"] / stats["requests_made"]
        else:
            stats["success_rate"] = 0.0

        stats["stealth_mode"] = self.enable_stealth
        stats["proxy_enabled"] = self.enable_proxy

        return stats

    async def close(self):
        """关闭采集器"""
        # 不使用Session，无需清理
        self.session = None
        logger.info("🔒 采集器已关闭")
