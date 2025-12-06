"""
FBref 采集器 V2 - 异步基础设施版本
FBref Collector V2 - Async Infrastructure Version

基于 AsyncBaseCollector 重新设计的 FBref 数据采集器，集成：
1. RateLimiter 限流保护 (QPS=0.5)
2. ProxyPool 代理轮换
3. httpx/curl_cffi HTTP 客户端
4. 指数退避重试机制
5. 完整的反爬虫策略

技术特性:
- 继承 AsyncBaseCollector 统一基础设施
- 支持 curl_cffi 绕过 TLS 指纹检测
- 实现 Slow Crawl 策略（至少2秒间隔）
- 保持与旧版 100% 兼容的输出格式

作者: Data Engineer (P2-2 Migration)
创建时间: 2025-12-06
版本: 2.0.0
"""

import asyncio
import gzip
import hashlib
import logging
import random
import re
import time
from datetime import datetime, timedelta
from io import StringIO
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
from bs4 import BeautifulSoup

# 基础设施导入
from src.core.async_base import AsyncBaseCollector, AsyncConfig
from src.collectors.rate_limiter import RateLimiter, RateLimitConfig
from src.collectors.proxy_pool import ProxyPool, Proxy

# HTTP 客户端导入 - 支持两种选择
try:
    import curl_cffi
    from curl_cffi import requests
    HAVE_CURL_CFFI = True
except ImportError:
    HAVE_CURL_CFFI = False
    curl_cffi = None
    requests = None

import httpx
from httpx import AsyncClient

logger = logging.getLogger(__name__)


class FBrefCollectorV2(AsyncBaseCollector):
    """
    FBref 数据采集器 V2

    基于 AsyncBaseCollector 的异步实现，集成限流和代理功能
    """

    def __init__(
        self,
        rate_limiter: Optional[RateLimiter] = None,
        proxy_pool: Optional[ProxyPool] = None,
        use_curl_cffi: bool = True,
        config: Optional[AsyncConfig] = None,
        raw_data_dir: Optional[str] = None
    ):
        """
        初始化 FBref 采集器 V2

        Args:
            rate_limiter: 速率限制器，如果为None则创建默认配置
            proxy_pool: 代理池，如果为None则不使用代理
            use_curl_cffi: 是否使用 curl_cffi（绕过 TLS 指纹）
            config: 异步配置
            raw_data_dir: 原始数据存储目录
        """
        # 初始化基础配置 - FBref 需要"慢速采集"
        if config is None:
            config = AsyncConfig(
                http_timeout=45.0,  # 增加超时
                max_retries=5,      # 增加重试次数
                retry_delay=8.0,    # 增加重试延迟
                rate_limit_delay=2.0,  # 强制至少2秒间隔
                enable_performance_monitoring=True
            )

        super().__init__(config=config, name="FBrefCollectorV2")

        # 初始化限流器 - FBref 限制严格：QPS=0.5, Burst=1
        if rate_limiter:
            self.rate_limiter = rate_limiter
        else:
            # 创建配置字典而不是直接传递RateLimitConfig对象
            rate_limit_config = {
                "default": {
                    "rate": 0.5,
                    "burst": 1,
                    "max_wait_time": 60.0
                }
            }
            self.rate_limiter = RateLimiter(rate_limit_config)

        # 初始化代理池
        self.proxy_pool = proxy_pool

        # HTTP 客户端配置
        self.use_curl_cffi = use_curl_cffi and HAVE_CURL_CFFI
        self.async_client: Optional[AsyncClient] = None

        # 原始数据存储配置
        self.raw_data_dir = Path(raw_data_dir or Path(__file__).parent.parent.parent / "data" / "raw_landing" / "fbref_v2")
        self.raw_data_dir.mkdir(parents=True, exist_ok=True)

        # FBref 特定的浏览器指纹轮换
        self.browser_configs = [
            "chrome", "chrome99", "chrome100", "chrome101", "chrome104"
        ]
        self.current_config_index = 0

        self.logger.info(f"🚀 FBref Collector V2 初始化完成")
        self.logger.info(f"   - HTTP客户端: {'curl_cffi' if self.use_curl_cffi else 'httpx'}")
        self.logger.info(f"   - 限流配置: QPS=0.5, Burst=1, Interval=2s")
        self.logger.info(f"   - 代理池: {'启用' if self.proxy_pool else '禁用'}")

    async def _get_headers(self) -> Dict[str, str]:
        """
        获取 FBref 专用请求头

        Returns:
            Dict[str, str]: HTTP请求头
        """
        headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-US,en;q=0.9,en-GB;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
            'sec-ch-ua': '"Google Chrome";v="120", "Chromium";v="120", "Not.A/Brand";v="24"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"'
        }

        # 如果使用代理，添加代理相关头
        if self.proxy_pool:
            headers['X-Forwarded-For'] = self._get_random_ip()
            headers['X-Real-IP'] = self._get_random_ip()

        return headers

    async def _get_user_agent(self) -> str:
        """
        获取随机 User-Agent

        Returns:
            str: User-Agent字符串
        """
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
        ]
        return random.choice(user_agents)

    def _get_random_ip(self) -> str:
        """生成随机 IP 地址"""
        return f"{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}"

    async def _setup_async_client(self) -> None:
        """设置异步 HTTP 客户端"""
        if self.async_client and not self.async_client.is_closed:
            return

        headers = await self._get_headers()
        timeout = httpx.Timeout(self.config.http_timeout)

        # 获取代理配置
        proxies = None
        if self.proxy_pool:
            proxy = await self.proxy_pool.get_proxy()
            if proxy:
                proxies = proxy.url
                self.logger.debug(f"Using proxy: {proxy.url}")

        # 注意：httpx的代理参数名是proxy而不是proxies
        self.async_client = AsyncClient(
            headers=headers,
            timeout=timeout,
            proxy=proxies,
            limits=httpx.Limits(max_connections=self.config.max_connections),
            follow_redirects=True
        )

    def _create_curl_session(self):
        """创建 curl_cffi 会话"""
        if not self.use_curl_cffi:
            return None

        # 轮换浏览器配置
        browser_type = self.browser_configs[self.current_config_index]
        self.current_config_index = (self.current_config_index + 1) % len(self.browser_configs)

        headers = asyncio.run(self._get_headers())

        try:
            session = requests.Session(
                impersonate=browser_type,
                headers=headers
            )
            self.logger.debug(f"Created curl_cffi session with {browser_type}")
            return session
        except Exception as e:
            self.logger.warning(f"Failed to create curl_cffi session: {e}")
            return None

    async def fetch_html(self, url: str) -> Optional[str]:
        """
        获取 HTML 内容（统一接口）

        Args:
            url: 目标URL

        Returns:
            HTML文本内容或None
        """
        self.logger.info(f"🔗 请求HTML: {url}")

        # 应用速率限制 - Slow Crawl 策略
        # 从URL中提取域名
        from urllib.parse import urlparse
        parsed_url = urlparse(url)
        domain = parsed_url.netloc or "fbref.com"

        async with self.rate_limiter.acquire(domain):
            # 额外的间隔时间 - 确保至少2秒间隔
            await asyncio.sleep(2.0)

            for attempt in range(self.config.max_retries):
                try:
                    # 重试时的额外延迟
                    if attempt > 0:
                        delay = self.config.retry_delay * (2 ** attempt) + random.uniform(3, 8)
                        self.logger.warning(f"⏸️ 重试 {attempt + 1}/{self.config.max_retries}，延迟 {delay:.1f}s")
                        await asyncio.sleep(delay)

                    # 添加时间戳避免缓存
                    timestamp = int(time.time() * 1000)
                    url_with_timestamp = f"{url}&_t={timestamp}" if '?' not in url else f"{url}&_t={timestamp}"

                    # 尝试使用 curl_cffi（如果可用且是第一次尝试）
                    if attempt == 0 and self.use_curl_cffi:
                        html_content = await self._fetch_with_curl_cffi(url_with_timestamp)
                        if html_content:
                            return html_content

                    # 回退到 httpx
                    html_content = await self._fetch_with_httpx(url_with_timestamp)
                    if html_content:
                        return html_content

                except Exception as e:
                    self.logger.error(f"❌ 请求失败 (尝试 {attempt + 1}): {e}")
                    if attempt < self.config.max_retries - 1:
                        continue

            self.logger.error("💥 所有请求尝试均失败")
            return None

    async def _fetch_with_curl_cffi(self, url: str) -> Optional[str]:
        """使用 curl_cffi 获取内容"""
        try:
            # 在线程池中运行 curl_cffi（它是同步的）
            loop = asyncio.get_event_loop()
            session = self._create_curl_session()

            if not session:
                return None

            def sync_fetch():
                response = session.get(url, timeout=self.config.http_timeout)
                if response.status_code == 200:
                    return response.text
                elif response.status_code == 403:
                    raise Exception("403 Forbidden: 可能被检测到")
                elif response.status_code == 429:
                    raise Exception("429 Too Many Requests: 请求过于频繁")
                else:
                    raise Exception(f"HTTP {response.status_code}")

            html_content = await loop.run_in_executor(None, sync_fetch)

            # 关闭会话
            session.close()

            self.logger.info(f"✅ curl_cffi 获取成功，大小: {len(html_content):,} 字节")

            # 执行 HTML 解封
            unsealed_html = self._unseal_html(html_content)

            if '<table' in unsealed_html.lower():
                self.logger.info("✅ HTML包含表格数据")
                return unsealed_html
            else:
                self.logger.warning("⚠️ HTML可能不包含表格数据")
                return unsealed_html

        except Exception as e:
            self.logger.error(f"❌ curl_cffi 请求失败: {e}")
            return None

    async def _fetch_with_httpx(self, url: str) -> Optional[str]:
        """使用 httpx 获取内容"""
        try:
            await self._setup_async_client()

            response = await self.async_client.get(url)

            if response.status_code == 200:
                html_content = response.text
                self.logger.info(f"✅ httpx 获取成功，大小: {len(html_content):,} 字节")

                # 执行 HTML 解封
                unsealed_html = self._unseal_html(html_content)

                if '<table' in unsealed_html.lower():
                    self.logger.info("✅ HTML包含表格数据")
                    return unsealed_html
                else:
                    self.logger.warning("⚠️ HTML可能不包含表格数据")
                    return unsealed_html

            elif response.status_code == 403:
                raise Exception("403 Forbidden: 可能被检测到")
            elif response.status_code == 429:
                raise Exception("429 Too Many Requests: 请求过于频繁")
            else:
                raise Exception(f"HTTP {response.status_code}")

        except Exception as e:
            self.logger.error(f"❌ httpx 请求失败: {e}")
            return None

    def _unseal_html(self, html_content: str) -> str:
        """
        HTML 注释解封技术 - 提取 FBref 隐藏的 xG 数据

        Args:
            html_content: 原始HTML内容

        Returns:
            解封后的HTML内容
        """
        try:
            self.logger.info("🔓 开始HTML注释解封...")

            # 统计原始注释数量
            original_comment_count = html_content.count('<!--')
            self.logger.info(f"📋 发现 {original_comment_count} 个HTML注释")

            unsealed_html = html_content
            unsealed_count = 0

            # 正则表达式匹配包含表格的注释
            comment_pattern = r'<!--(.*?)-->'
            comments = re.findall(comment_pattern, unsealed_html, re.DOTALL)

            for comment in comments:
                comment_str = comment.strip()

                # 检查是否为包含统计表格的注释
                if (any(keyword in comment_str.lower() for keyword in ['id="sched_', 'id="all_', 'table', 'tbody']) and
                    any(keyword in comment_str.lower() for keyword in ['xg', 'xga', 'shot', 'possession', 'touches'])):

                    # 解封：移除注释标记
                    sealed_html = f'<!--{comment_str}-->'
                    unsealed_content = comment_str

                    # 执行替换
                    unsealed_html = unsealed_html.replace(sealed_html, unsealed_content)
                    unsealed_count += 1

                    self.logger.debug(f"🔓 解封表格 {unsealed_count}: {comment_str[:100]}...")

            # 统计解封结果
            remaining_comments = unsealed_html.count('<!--')
            self.logger.info(f"✅ 解封完成: {unsealed_count} 个表格已解封")
            self.logger.info(f"📊 注释统计: {original_comment_count} → {remaining_comments}")

            # 验证解封效果
            new_table_count = unsealed_html.count('<table')
            original_table_count = html_content.count('<table')
            if new_table_count > original_table_count:
                self.logger.info(f"🎯 表格数量增加: {original_table_count} → {new_table_count} (+{new_table_count - original_table_count})")

            return unsealed_html

        except Exception as e:
            self.logger.error(f"❌ HTML注释解封失败: {e}")
            return html_content

    def _save_raw_html(self, html_content: str, url: str, league_id: str = None, season: str = None) -> Optional[str]:
        """
        保存原始HTML内容到文件系统

        Args:
            html_content: HTML文本内容
            url: 原始请求URL
            league_id: 联赛ID
            season: 赛季

        Returns:
            保存的文件绝对路径，如果保存失败返回None
        """
        try:
            # 生成文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            content_hash = hashlib.sha256(html_content.encode('utf-8')).hexdigest()[:16]
            filename = f"{timestamp}_{content_hash}.html.gz"

            # 创建目录结构
            if league_id and season:
                season_normalized = season.replace("-", "")
                target_dir = self.raw_data_dir / league_id / season_normalized
            else:
                # 从URL中提取league_id
                league_match = re.search(r'/comps/(\d+)/', url)
                if league_match:
                    league_id_fallback = league_match.group(1)
                    target_dir = self.raw_data_dir / league_id_fallback / "unknown_season"
                else:
                    target_dir = self.raw_data_dir / "unknown_league" / "unknown_season"

            target_dir.mkdir(parents=True, exist_ok=True)
            file_path = target_dir / filename

            # 压缩保存HTML内容
            with gzip.open(file_path, 'wt', encoding='utf-8') as f:
                f.write(html_content)

            file_size = file_path.stat().st_size
            self.logger.info(f"🗂️ 原始HTML已保存: {file_path} ({file_size:,} 字节压缩后)")

            return str(file_path.absolute())

        except Exception as e:
            self.logger.warning(f"⚠️ 原始HTML保存失败 (不影响采集): {e}")
            return None

    def parse_html_tables(self, html_content: str) -> Tuple[List[pd.DataFrame], Dict[str, pd.DataFrame]]:
        """
        解析HTML中的表格数据 - 与旧版保持兼容

        Args:
            html_content: HTML内容

        Returns:
            解析出的DataFrame列表，包含match_report_url列和统计数据
        """
        try:
            self.logger.info("🔗 开始HTML表格解析...")

            # 1. 使用BeautifulSoup识别所有表格
            soup = BeautifulSoup(html_content, 'html.parser')

            # 查找统计表格关键词
            table_keywords = [
                'stats', 'shooting', 'schedule', 'passing', 'defending', 'possession',
                'misc', 'team', 'summary', 'keeper', 'keeper_adv'
            ]
            all_table_divs = soup.find_all('div', id=lambda x: x and any(keyword in x.lower() for keyword in table_keywords))
            self.logger.info(f"🎯 发现 {len(all_table_divs)} 个包含统计信息的表格div")

            # 查找战术统计表格
            tactical_table_divs = soup.find_all('table', id=lambda x: x and any(
                keyword in str(x).lower() for keyword in ['shots', 'passes', 'fouls', 'tackles', 'possession']
            ))
            self.logger.info(f"🎯 发现 {len(tactical_table_divs)} 个战术统计表格")

            # 2. 用pandas解析所有表格数据
            tables = pd.read_html(StringIO(html_content))
            self.logger.info(f"📊 pandas解析出 {len(tables)} 个基础表格")

            # 3. 使用BeautifulSoup提取Match Report链接
            match_report_links = self._extract_match_report_links(html_content)
            self.logger.info(f"🔗 BeautifulSoup提取到 {len(match_report_links)} 个Match Report链接")

            # 4. 提取高级统计数据
            advanced_stats = self._extract_advanced_stats(tables)
            self.logger.info(f"📈 提取到 {len(advanced_stats)} 个统计表格")

            # 5. 将统计数据附加到返回结果中
            stats_result = advanced_stats if advanced_stats else {}

            # 6. 将链接合并到赛程表格中
            if tables and match_report_links:
                schedule_df = tables[0]

                if len(match_report_links) <= len(schedule_df):
                    schedule_df = schedule_df.copy()
                    schedule_df['match_report_url'] = None
                    schedule_df.loc[:len(match_report_links)-1, 'match_report_url'] = match_report_links
                    self.logger.info(f"✅ 成功将 {len(match_report_links)} 个链接合并到赛程表")

                tables[0] = schedule_df

            return tables, stats_result

        except Exception as e:
            self.logger.error(f"❌ HTML表格解析失败: {e}")
            return [], {}

    def _extract_match_report_links(self, html_content: str) -> List[str]:
        """从HTML内容中提取Match Report链接"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            match_report_urls = []

            # 寻找FBref的Match Report链接
            for link in soup.find_all('a', href=True):
                href = link['href']
                if '/matches/' in href and 'fbref.com' not in href:  # 相对路径
                    full_url = f"https://fbref.com{href}"
                    match_report_urls.append(full_url)

            # 如果方法1失败，查找特定data-stat属性
            if not match_report_urls:
                for td in soup.find_all('td', {'data-stat': 'match_report'}):
                    link = td.find('a', href=True)
                    if link and '/matches/' in link['href']:
                        full_url = f"https://fbref.com{link['href']}"
                        match_report_urls.append(full_url)

            # 如果还没找到，使用正则表达式
            if not match_report_urls:
                pattern = r'href="(/en/matches/[^"]+)"'
                matches = re.findall(pattern, html_content)
                for match in matches:
                    full_url = f"https://fbref.com{match}"
                    match_report_urls.append(full_url)

            self.logger.info(f"🔗 总共提取到 {len(match_report_urls)} 个Match Report链接")
            return match_report_urls

        except Exception as e:
            self.logger.error(f"❌ Match Report链接提取失败: {e}")
            return []

    def _extract_advanced_stats(self, tables: List[pd.DataFrame]) -> Dict[str, pd.DataFrame]:
        """从表格中提取高级统计数据"""
        stats_dict = {}

        try:
            for i, table in enumerate(tables):
                if table.empty:
                    continue

                columns_str = [str(col).lower() for col in table.columns]

                # 检查不同类型的统计表
                is_shooting_stats = any(keyword in ' '.join(columns_str) for keyword in
                    ['xg', 'xga', 'shots', 'possession', 'touches', 'pressures', 'passes'])

                if is_shooting_stats:
                    self.logger.info(f"📈 发现射击统计表 (索引 {i}): {table.shape}")
                    stats_dict['shooting'] = table
                elif any(keyword in ' '.join(columns_str) for keyword in
                    ['keeper', 'gk', 'goalkeeper', 'defending']):
                    self.logger.info(f"🛡️ 发现防守统计表 (索引 {i}): {table.shape}")
                    stats_dict['defending'] = table
                elif any(keyword in ' '.join(columns_str) for keyword in
                    ['passing', 'pass_types', 'gca', 'scca']):
                    self.logger.info(f"🎯 发现传球统计表 (索引 {i}): {table.shape}")
                    stats_dict['passing'] = table
                elif any(keyword in ' '.join(columns_str) for keyword in
                    ['dribbles', 'take_ons', 'carries']):
                    self.logger.info(f"🏃 发现运球统计表 (索引 {i}): {table.shape}")
                    stats_dict['dribbling'] = table
                elif any(keyword in ' '.join(columns_str) for keyword in
                    ['misc', 'fouls', 'cards']):
                    self.logger.info(f"📝 发现杂项统计表 (索引 {i}): {table.shape}")
                    stats_dict['misc'] = table

        except Exception as e:
            self.logger.error(f"❌ 统计表提取失败: {e}")

        return stats_dict

    def extract_schedule_table(self, tables: List[pd.DataFrame]) -> Optional[pd.DataFrame]:
        """
        从表格中提取赛程表 - 与旧版保持兼容

        Args:
            tables: DataFrame列表

        Returns:
            赛程表DataFrame或None
        """
        if not tables:
            return None

        # 智能识别赛程表
        for i, table in enumerate(tables):
            columns_str = [str(col).lower() for col in table.columns]

            # 检查赛程表特征列
            has_date = any(keyword in col for col in columns_str
                         for keyword in ['date', 'wk', 'week', 'day', 'time'])
            has_home = any(keyword in col for col in columns_str
                         for keyword in ['home', 'squad', 'team'])
            has_score = any(keyword in col for col in columns_str
                          for keyword in ['score', 'result', 'goals'])
            has_away = any(keyword in col for col in columns_str
                         for keyword in ['away', 'opponent', 'visitor'])

            # 排除积分榜特征列
            standings_keywords = ['mp', 'w', 'd', 'l', 'pts', 'ga', 'gd', 'points', 'played']
            is_standings = any(keyword in col for col in columns_str
                              for keyword in standings_keywords
                              if 'away' not in col)

            self.logger.info(f"🔍 表格 {i}: {table.shape}, 列: {columns_str[:5]}...")
            self.logger.info(f"   特征: date={has_date}, home={has_home}, score={has_score}, away={has_away}, standings={is_standings}")

            # 赛程表识别条件
            if (has_date and has_home and has_away and has_score and
                table.shape[0] >= 10 and table.shape[1] >= 3):

                self.logger.info(f"🎯 找到赛程表 (索引 {i}): {table.shape}")
                self.logger.info(f"📋 表格列名: {list(table.columns)}")

                # 检查是否包含xG数据
                has_xg = any('xg' in col for col in columns_str)
                if has_xg:
                    self.logger.info("✅ 确认包含xG数据列")

                return table

        self.logger.error("❌ 未找到有效的赛程表")
        return None

    async def collect_season_stats(self, season_url: str, season_year: Optional[str] = None) -> pd.DataFrame:
        """
        采集赛季统计数据 - 核心业务逻辑

        Args:
            season_url: FBref赛季URL
            season_year: 赛季年份 (如 "2023-2024")

        Returns:
            包含比赛数据的DataFrame
        """
        self.logger.info(f"🕵️ FBref赛季数据采集: {season_url}")

        # 构建完整URL
        if season_year:
            if '?' in season_url:
                url = f"{season_url}&season={season_year.replace('-', '')}"
            else:
                url = f"{season_url}?season={season_year.replace('-', '')}"
        else:
            url = season_url

        self.logger.info(f"🎯 目标URL: {url}")

        # 获取HTML内容
        html_content = await self.fetch_html(url)
        if not html_content:
            self.logger.error("❌ 无法获取HTML内容")
            return pd.DataFrame()

        # 保存原始HTML内容
        import re
        league_match = re.search(r'/comps/(\d+)/', url)
        league_id = league_match.group(1) if league_match else None
        season_normalized = season_year.replace("-", "") if season_year else None

        raw_file_path = self._save_raw_html(
            html_content=html_content,
            url=url,
            league_id=league_id,
            season=season_normalized
        )

        # 解析HTML表格
        tables, advanced_stats = self.parse_html_tables(html_content)
        if not tables:
            self.logger.error("❌ 未找到任何HTML表格")
            return pd.DataFrame()

        # 提取赛程表
        schedule_table = self.extract_schedule_table(tables)
        if schedule_table is None:
            self.logger.error("❌ 无法提取赛程表")
            return pd.DataFrame()

        # 将原始文件路径添加到DataFrame中
        if raw_file_path and not schedule_table.empty:
            schedule_table = schedule_table.copy()
            schedule_table['raw_file_path'] = raw_file_path
            self.logger.info(f"✅ 原始文件路径已添加到DataFrame")

        self.logger.info(f"🎉 赛季数据采集成功，表格形状: {schedule_table.shape}")
        return schedule_table

    async def collect_match_stats(self, match_url: str) -> Dict[str, Any]:
        """
        采集单场比赛的详细统计数据

        Args:
            match_url: 比赛详情页URL

        Returns:
            包含比赛统计数据的字典
        """
        self.logger.info(f"⚽ FBref比赛详情采集: {match_url}")

        # 获取HTML内容
        html_content = await self.fetch_html(match_url)
        if not html_content:
            self.logger.error("❌ 无法获取比赛HTML内容")
            return {}

        # 保存原始HTML
        raw_file_path = self._save_raw_html(html_content, match_url)

        # 解析表格
        tables, advanced_stats = self.parse_html_tables(html_content)

        # 构建比赛统计结果
        match_stats = {
            'match_url': match_url,
            'raw_file_path': raw_file_path,
            'tables_count': len(tables),
            'advanced_stats': advanced_stats,
            'has_shooting_stats': 'shooting' in advanced_stats,
            'has_passing_stats': 'passing' in advanced_stats,
            'has_defending_stats': 'defending' in advanced_stats,
        }

        self.logger.info(f"✅ 比赛统计采集完成，表格数: {len(tables)}")
        return match_stats

    def _clean_schedule_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        清洗赛程数据 - 与旧版保持完全兼容

        Args:
            df: 原始DataFrame

        Returns:
            清洗后的DataFrame
        """
        self.logger.info("🧹 开始数据清洗...")

        if df.empty:
            return df

        # 处理MultiIndex列名
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = ['_'.join(col).strip() if col[1] else col[0] for col in df.columns.values]

        # 智能列名映射（与旧版保持一致）
        column_mapping = {}
        for col in df.columns:
            col_str = str(col).lower()

            # 基础比赛信息
            if 'date' in col_str and 'date' not in column_mapping:
                column_mapping['date'] = col
            elif 'home' in col_str and 'away' not in col_str and 'home' not in column_mapping:
                column_mapping['home'] = col
            elif 'away' in col_str and 'home' not in col_str and 'away' not in column_mapping:
                column_mapping['away'] = col
            elif 'score' in col_str and 'score' not in column_mapping:
                column_mapping['score'] = col

            # xG数据映射（与旧版完全一致）
            elif col_str == 'xg' and 'xg_home' not in column_mapping:
                column_mapping['xg_home'] = col
                self.logger.info(f"🎯 映射xG列: {col} -> xg_home")
            elif col_str == 'xg.1' and 'xg_away' not in column_mapping:
                column_mapping['xg_away'] = col
                self.logger.info(f"🎯 映射xG列: {col} -> xg_away")
            elif 'expected goals' in col_str and 'xg_home' not in column_mapping:
                column_mapping['xg_home'] = col
                self.logger.info(f"🎯 映射Expected Goals列: {col} -> xg_home")
            elif 'expected goals' in col_str and 'away' in col_str and 'xg_away' not in column_mapping:
                column_mapping['xg_away'] = col
                self.logger.info(f"🎯 映射Expected Goals列: {col} -> xg_away")

            # 其他统计字段
            elif 'shots' in col_str and 'shots_on_target' not in col_str and 'shots' not in column_mapping:
                column_mapping['shots'] = col
            elif 'shots on target' in col_str and 'shots_on_target' not in column_mapping:
                column_mapping['shots_on_target'] = col
            elif 'possession' in col_str and 'possession_home' not in column_mapping and 'possession' not in column_mapping:
                column_mapping['possession_home'] = col
            elif 'match_report_url' in col_str and 'match_report_url' not in column_mapping:
                column_mapping['match_report_url'] = col

        # 构建清洗后的DataFrame
        cleaned_df = pd.DataFrame()
        for new_name, old_name in column_mapping.items():
            if old_name in df.columns:
                cleaned_df[new_name] = df[old_name].copy()

        # 强制保留match_report_url列
        if 'match_report_url' in df.columns and 'match_report_url' not in cleaned_df.columns:
            cleaned_df['match_report_url'] = df['match_report_url'].copy()
            self.logger.info("🔗 强制保留match_report_url列")

        # 保留所有未映射的列
        for col in df.columns:
            if col not in column_mapping.values() and col not in cleaned_df.columns:
                cleaned_df[f'raw_{col}'] = df[col].copy()

        # 强制转换xG列为float类型
        if 'xg_home' in cleaned_df.columns:
            cleaned_df['xg_home'] = pd.to_numeric(cleaned_df['xg_home'], errors='coerce')
            xg_home_valid = cleaned_df['xg_home'].notna().sum()
            self.logger.info(f"   xg_home有效数据: {xg_home_valid}/{len(cleaned_df)}")

        if 'xg_away' in cleaned_df.columns:
            cleaned_df['xg_away'] = pd.to_numeric(cleaned_df['xg_away'], errors='coerce')
            xg_away_valid = cleaned_df['xg_away'].notna().sum()
            self.logger.info(f"   xg_away有效数据: {xg_away_valid}/{len(cleaned_df)}")

        self.logger.info(f"✅ 数据清洗完成: {len(cleaned_df.columns)} 列")
        return cleaned_df

    async def cleanup(self):
        """清理资源"""
        if self.async_client and not self.async_client.is_closed:
            await self.async_client.aclose()
            self.async_client = None

        await super()._cleanup()
        self.logger.info("🧹 FBref Collector V2 资源清理完成")

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.cleanup()
        await super().__aexit__(exc_type, exc_val, exc_tb)