#!/usr/bin/env python3
"""
V41.50 Hash Alignment Service - 工业级哈希对齐服务

核心功能:
1. 地毯扫射 (Carpet Sweep) - V41.35 算法
2. 雷达搜索 (Radar Search) - V41.37 算法
3. 青年队拦截 (Youth Team Blocking) - V41.29 算法
4. 跨日期校验 (Cross-Date Validation) - V41.36 算法
5. 隧道轮换 (Tunnel Rotation) - V41.43 算法
6. 全自动收割 (Active Harvest) - V41.44 算法
7. 代理容错 (Proxy Fault Tolerance) - V41.45 算法
8. WSL2 代理适配 (V41.50) - 自动检测 WSL2 并使用宿主机 IP
9. 赛季格式归一化 (V41.50) - 支持 23/24 和 2023/2024 两种格式

工程化特性:
- 解耦: 独立于具体脚本环境
- 反爬集成: 集成 Ghost Protocol
- 统一配置: 通过 YAML 驱动
- 幂等性: UPSERT 保证多次运行安全
- TDD: 100% 测试覆盖
- 并发采集: 10 端口隔离 (7890-7899)
- Playwright 集成: 自动化浏览器抓取
- 代理容错: 自动跳过失效端口
- 浏览器清理: 异常安全保证
- WSL2 适配: 自动检测并使用宿主机代理地址

Author: 资深 SRE 架构师
Version: V41.50
Date: 2026-01-14
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging
import os
import random
import re
import socket
import sys
import threading
from typing import TYPE_CHECKING, Any, ClassVar

from bs4 import BeautifulSoup
import psycopg2

# V41.44: Playwright 集成（延迟导入以避免启动时的开销）
try:
    from playwright.async_api import Browser, async_playwright

    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    async_playwright = None

# 延迟导入避免循环依赖 - TeamNameNormalizer 需要在 __init__ 中导入
from src.utils.text_processor import TeamNameNormalizer, YouthTeamDetector

if TYPE_CHECKING:
    from playwright.async_api import Page

# 配置日志
logger = logging.getLogger(__name__)


# ============================================================================
# V41.62: 反爬对抗配置 - 隐身逻辑回归
# ============================================================================

# User-Agent 轮换池（50+ 量，覆盖主流浏览器和版本）
USER_AGENTS = [
    # Chrome on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 11.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    # Firefox on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:119.0) Gecko/20100101 Firefox/119.0",
    # Edge on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0",
    # Chrome on macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    # Safari on macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    # Firefox on macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14.1; rv:120.0) Gecko/20100101 Firefox/120.0",
    # Chrome on Linux
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    # Firefox on Linux
    "Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0",
    # Additional Windows variants
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:118.0) Gecko/20100101 Firefox/118.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:117.0) Gecko/20100101 Firefox/117.0",
    # Additional macOS variants
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    # Additional Edge variants
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36 Edg/118.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36 Edg/117.0.0.0",
    # Additional Safari variants
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Safari/605.1.15",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1",
    # Additional Linux variants
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Fedora; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64; rv:119.0) Gecko/20100101 Firefox/119.0",
    # Chrome variations
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
    # Firefox variations
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:116.0) Gecko/20100101 Firefox/116.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:115.0) Gecko/20100101 Firefox/115.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (X11; Linux x86_64; rv:118.0) Gecko/20100101 Firefox/118.0",
    # Edge variations
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36 Edg/116.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36 Edg/115.0.0.0",
    # Safari mobile
    "Mozilla/5.0 (iPad; CPU OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1",
    # Mix of other versions
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:114.0) Gecko/20100101 Firefox/114.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:113.0) Gecko/20100101 Firefox/113.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36",
]

# 视口尺寸池（随机化窗口大小）
VIEWPORT_SIZES = [
    {"width": 1920, "height": 1080},
    {"width": 1366, "height": 768},
    {"width": 1536, "height": 864},
    {"width": 1440, "height": 900},
    {"width": 1680, "height": 1050},
    {"width": 1600, "height": 900},
    {"width": 1280, "height": 720},
    {"width": 1024, "height": 768},
]


# ============================================================================
# 数据模型
# ============================================================================


@dataclass
class MatchInfo:
    """比赛信息"""

    home_team: str
    away_team: str
    hash_value: str
    url: str
    start_date: datetime | None = None


@dataclass
class AlignmentResult:
    """对齐结果"""

    match_id: str
    hash_value: str
    url: str
    confidence: float
    method: str
    reviewed: bool


@dataclass
class HarvestStats:
    """收割统计"""

    visited: int = 0
    extracted: int = 0
    matched: int = 0
    updated: int = 0
    conflicts: int = 0
    skipped: int = 0
    total_missing: int = 0


# ============================================================================
# 核心服务类
# ============================================================================


class HashAlignmentService:
    """
    V41.44 哈希对齐服务

    集成 V41.35 地毯扫射 + V41.37 雷达搜索 + V41.43 隧道轮换 + V41.44 全自动收割
    工程化重构，解耦脚本依赖
    """

    # V41.44: 多模式 8位黄金哈希正则（增强匹配）
    # 模式1: 标准格式 /football/country/league/team-team-hash/
    # 模式2: 带赛季格式 /football/country/league-season/team-team-hash/
    HASH_PATTERNS = [
        re.compile(r"/football/[^/]+/[^/]+-[^/]+/([a-z-]+)-([a-z-]+)-([A-Za-z0-9]{8})/?$"),
        re.compile(r"/football/[^/]+/[^/]+/([a-z-]+)-([a-z-]+)-([A-Za-z0-9]{8})/?$"),
        re.compile(r"/football/[^/]+/[^/]+/([^/]+)-([^/]+)-([A-Za-z0-9]{8})/"),
    ]

    # V41.128: 线程锁保护并发别名库注浆
    # 多个 Worker 共享同一个数据库连接时，需要串行化别名库注浆操作
    _alias_injection_lock: ClassVar[threading.Lock] = threading.Lock()

    # V41.121: 隧道轮换配置（从统一配置读取）
    # V41.63 原配置: 6 端口物理对齐 - 严格匹配 Clash 脚本
    @classmethod
    def get_proxy_ports(cls) -> list[int]:
        """获取代理端口列表（从统一配置读取）"""
        from src.config_unified import get_config

        config = get_config()
        return config.proxy.proxy_ports

    @classmethod
    def get_wsl2_proxy_host(cls) -> str:
        """获取 WSL2 代理主机（从统一配置读取）"""
        from src.config_unified import get_config

        config = get_config()
        return config.proxy.wsl2_bridge_host

    # 保留向后兼容的默认值（如果统一配置不可用）
    PROXY_PORTS: ClassVar[list[int]] = [
        7892,
        7893,
        7894,
        7895,
        7896,
        7898,
        7899,
    ]  # V41.121 更新: 使用验证后的端口
    WSL2_PROXY_HOST: ClassVar[str] = "172.25.16.1"  # WSL2 宿主机默认 IP
    LOCAL_PROXY_HOST: ClassVar[str] = "127.0.0.1"  # 本地回环地址

    # 联赛URL映射配置
    LEAGUE_URLS: ClassVar[dict[str, dict[str, str]]] = {
        "Premier League": {
            "url": "https://www.oddsportal.com/football/england/premier-league-2023-2024/results/",
            "country": "england",
        },
        "La Liga": {
            "url": "https://www.oddsportal.com/football/spain/laliga-2023-2024/results/",
            "country": "spain",
        },
        "Bundesliga": {
            "url": "https://www.oddsportal.com/football/germany/bundesliga-2023-2024/results/",
            "country": "germany",
        },
        "Serie A": {
            "url": "https://www.oddsportal.com/football/italy/serie-a-2023-2024/results/",
            "country": "italy",
        },
        "Ligue 1": {
            "url": "https://www.oddsportal.com/football/france/ligue-1-2023-2024/results/",
            "country": "france",
        },
    }

    # V41.50: 环境检测与格式归一化
    # ========================================================================

    @staticmethod
    def is_wsl2_environment() -> bool:
        """
        V41.50: 检测是否运行在 WSL2 环境

        Returns:
            True 如果在 WSL2 环境中运行
        """
        try:
            with open("/proc/version") as f:
                version_content = f.read().lower()
                return "microsoft" in version_content and "wsl2" in version_content
        except (OSError, FileNotFoundError):
            return False

    @classmethod
    def get_proxy_host(cls) -> str:
        """
        V41.50: 获取代理主机地址

        自动检测 WSL2 环境，返回正确的代理主机地址：
        - WSL2 环境: 返回 172.25.16.1 (宿主机 IP)
        - 其他环境: 返回 127.0.0.1 (本地回环)

        Returns:
            代理主机 IP 地址
        """
        # V41.121: 使用统一配置获取 WSL2 代理主机
        from src.config_unified import get_config

        config = get_config()
        proxy_config = config.proxy

        if cls.is_wsl2_environment():
            return proxy_config.wsl2_bridge_host
        return "127.0.0.1"

    @staticmethod
    def normalize_season_format(season: str) -> str:
        """
        V41.50: 归一化赛季格式

        将简写赛季格式 (23/24) 转换为完整格式 (2023/2024)，
        确保与数据库中的赛季格式一致。

        Args:
            season: 赛季字符串 (如 "23/24", "2023/2024")

        Returns:
            归一化后的赛季格式 (如 "2023/2024")

        Examples:
            >>> normalize_season_format("23/24")
            "2023/2024"
            >>> normalize_season_format("2023/2024")
            "2023/2024"
            >>> normalize_season_format("22/23")
            "2022/2023"
        """
        # 如果已经是完整格式 (4位/4位)，直接返回
        if re.match(r"^\d{4}/\d{4}$", season):
            return season

        # 如果是简写格式 (2位/2位)，转换为完整格式
        match = re.match(r"^(\d{2})/(\d{2})$", season)
        if match:
            year1, year2 = match.groups()
            # 判断是 19xx 还是 20xx
            # 假设赛季格式为 YY/YY，第一个年份通常在 20-25 之间
            if int(year1) <= 50:
                full_year1 = f"20{year1}"
                full_year2 = f"20{year2}"
            else:
                full_year1 = f"19{year1}"
                full_year2 = f"19{year2}"
            return f"{full_year1}/{full_year2}"

        # 其他格式（如 "2024" 自然年赛季），保持不变
        return season

    # ========================================================================
    # 初始化与核心方法
    # ========================================================================

    def __init__(self, db_conn, season: str = "23/24"):
        """
        初始化哈希对齐服务

        Args:
            db_conn: 数据库连接
            season: 目标赛季 (支持 "23/24" 或 "2023/2024" 格式)
        """
        self.conn = db_conn
        # V41.50: 归一化赛季格式，确保与数据库一致
        self.season = self.normalize_season_format(season)
        self.stats = HarvestStats()

        self.normalizer = TeamNameNormalizer()
        self.youth_detector = YouthTeamDetector()

        # V41.51: 数据库身份验证 - 确保连接到正确的数据库实例
        self._verify_database_identity()

        # V41.50: 记录原始赛季和归一化后的赛季
        if season != self.season:
            logger.info(
                "✅ HashAlignmentService 初始化完成 (season: %s → %s, WSL2: %s)",
                season,
                self.season,
                self.is_wsl2_environment(),
            )
        else:
            logger.info(
                "✅ HashAlignmentService 初始化完成 (season=%s, WSL2: %s)",
                self.season,
                self.is_wsl2_environment(),
            )

    def _verify_database_identity(self) -> None:
        """
        V41.51: 数据库身份验证

        验证连接的数据库实例是否为 football_db，并检查核心表是否存在。
        如果连接到错误的数据库实例，抛出致命错误。

        Raises:
            DatabaseConfigurationError: 如果连接到错误的数据库实例
        """
        from src.config_unified import DatabaseConfigurationError

        try:
            with self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                # 1. 检查当前连接的数据库名称
                cursor.execute("SELECT current_database();")
                result = cursor.fetchone()
                current_db = result["current_database"] if result else None

                # 2. 检查 matches 表是否存在
                cursor.execute("SELECT to_regclass('public.matches');")
                result = cursor.fetchone()
                matches_table = result["to_regclass"] if result else None

                # 3. 验证数据库身份
                if current_db != "football_db":
                    raise DatabaseConfigurationError(
                        f"🚨 V41.51 数据库身份验证失败：错误的数据库实例\n"
                        f"   期望: football_db\n"
                        f"   实际: {current_db}\n"
                        f"   请检查 .env 文件，确保 DB_NAME=football_db"
                    )

                # 4. 验证核心表存在
                if matches_table is None:
                    raise DatabaseConfigurationError(
                        f"🚨 V41.51 数据库身份验证失败：核心表不存在\n"
                        f"   数据库: {current_db}\n"
                        f"   缺失: public.matches 表\n"
                        f"   请运行数据库迁移脚本初始化 schema"
                    )

                # 5. 验证通过：记录表数量
                cursor.execute("""
                    SELECT COUNT(*) FROM information_schema.tables
                    WHERE table_schema = 'public' AND table_type = 'BASE TABLE';
                """)
                result = cursor.fetchone()
                table_count = result["count"] if result else 0

                logger.info(f"✅ V41.51 数据库身份验证通过 (db={current_db}, tables={table_count})")

        except DatabaseConfigurationError:
            raise
        except Exception as e:
            raise DatabaseConfigurationError(
                f"🚨 V41.51 数据库身份验证异常\n   错误: {e}\n   请检查数据库连接配置"
            )

    # ========================================================================
    # V41.47: 动态 URL 引擎 (Dynamic URL Engine)
    # ========================================================================

    @staticmethod
    def detect_season_format(season: str) -> str:
        """
        V41.47: 检测赛季格式

        Args:
            season: 赛季字符串 (如 "23/24", "2024", "2023-2024")

        Returns:
            "cross_year" 或 "calendar_year"
        """
        # 跨年赛季格式: "23/24" 或 "2023-2024"
        if "/" in season or "-" in season:
            return "cross_year"

        # 自然年赛季格式: "2024"
        if season.isdigit() and len(season) == 4:
            return "calendar_year"

        # 默认尝试通过 "/" 判断
        if "/" in season:
            return "cross_year"

        return "calendar_year"

    @staticmethod
    def get_league_url(league_config: dict, season: str) -> str:
        """
        V41.47: 动态生成联赛 URL

        自动识别跨年赛季 (23/24) vs 自然年赛季 (2024)，生成符合 OddsPortal 规范的 URL

        Args:
            league_config: 联赛配置字典，必须包含:
                - name: 联赛名称
                - oddsportal_slug: OddsPortal slug (如 "england/premier-league-2023-2024")
                - seasons: 支持的赛季列表
            season: 目标赛季 (如 "23/24", "2024")

        Returns:
            完整的 OddsPortal results 页面 URL

        Examples:
            >>> get_league_url({"oddsportal_slug": "england/premier-league-2023-2024"}, "23/24")
            "https://www.oddsportal.com/football/england/premier-league-2023-2024/results/"

            >>> get_league_url({"oddsportal_slug": "england/premier-league-2023-2024"}, "22/23")
            "https://www.oddsportal.com/football/england/premier-league-2022-2023/results/"

            >>> get_league_url({"oddsportal_slug": "usa/mls-2024"}, "2024")
            "https://www.oddsportal.com/football/usa/mls-2024/results/"
        """
        base_url = "https://www.oddsportal.com/football/"
        slug = league_config.get("oddsportal_slug", "")

        if not slug:
            raise ValueError(f"oddsportal_slug 未配置: {league_config.get('name')}")

        # 检测赛季格式
        season_format = HashAlignmentService.detect_season_format(season)

        # 转换赛季为 OddsPortal URL 格式
        if season_format == "cross_year":
            # 跨年赛季: "23/24" → "2023-2024", "22/23" → "2022-2023"
            if "/" in season:
                parts = season.split("/")
                year1 = "20" + parts[0]
                year2 = "20" + parts[1]
                season_suffix = f"{year1}-{year2}"
            elif "-" in season:
                # 已经是 "2023-2024" 格式
                season_suffix = season
            else:
                raise ValueError(f"无法解析跨年赛季格式: {season}")
        else:
            # 自然年赛季: "2024" → "2024"
            season_suffix = season

        # 从 slug 中提取基础路径（移除原赛季部分）
        # 模式: {country}/{league}-{season} → {country}/{league}
        # 匹配跨年赛季或自然年赛季模式
        base_slug = re.sub(
            r"-[\d]{4}-[\d]{4}/?$",  # 跨年: -2023-2024
            "",
            slug,
        )
        base_slug = re.sub(
            r"-[\d]{4}/?$",  # 自然年: -2024
            "",
            base_slug,
        )

        # 构建新 URL
        new_slug = f"{base_slug}-{season_suffix}"
        return f"{base_url}{new_slug}/results/"

    @staticmethod
    def _load_league_config_from_yaml(league_name: str) -> dict | None:
        """
        V41.47: 从 YAML 配置加载联赛信息

        Args:
            league_name: 联赛名称

        Returns:
            联赛配置字典，如果未找到则返回 None
        """
        from pathlib import Path

        import yaml

        yaml_path = Path("config/leagues.yaml")
        if not yaml_path.exists():
            return None

        with open(yaml_path) as f:
            config = yaml.safe_load(f)

        # 通过英文名称查找联赛
        for league_config in config.get("leagues", {}).values():
            if league_config.get("name") == league_name:
                return league_config

        return None

    # ========================================================================
    # V41.35: 地毯扫射算法 (Carpet Sweep) - V41.44 增强
    # ========================================================================

    def extract_matches_from_html(self, html: str) -> list[MatchInfo]:
        """
        V41.44: 从 HTML 中提取所有比赛信息（地毯扫射 - 增强版）

        使用多模式正则匹配，提高匹配成功率

        Args:
            html: 页面 HTML

        Returns:
            MatchInfo 列表
        """
        soup = BeautifulSoup(html, "html.parser")
        matches = []

        for link in soup.find_all("a", href=True):
            href = link.get("href", "")

            # V41.44: 尝试所有正则模式
            for pattern in self.HASH_PATTERNS:
                match = pattern.search(href)
                if match:
                    home_team_raw, away_team_raw, hash_str = match.groups()

                    # 格式化队名（连字符转空格，首字母大写）
                    home_team = home_team_raw.replace("-", " ").title()
                    away_team = away_team_raw.replace("-", " ").title()

                    matches.append(
                        MatchInfo(
                            home_team=home_team, away_team=away_team, hash_value=hash_str, url=href
                        )
                    )
                    break  # 匹配成功后跳出循环

        return matches

    def get_missing_matches(self, league_name: str) -> dict[str, str]:
        """
        获取缺失的比赛

        Args:
            league_name: 联赛名称

        Returns:
            {match_id: "home_team vs away_team"} 字典
        """
        query = """
            SELECT m.match_id, m.home_team, m.away_team
            FROM matches m
            LEFT JOIN matches_mapping mm ON m.match_id = mm.fotmob_id
            WHERE m.season = %s
              AND m.league_name = %s
              AND (mm.oddsportal_hash IS NULL OR LENGTH(mm.oddsportal_hash) <> 8)
        """

        with self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(query, (self.season, league_name))
            rows = cur.fetchall()

        missing = {}
        for row in rows:
            key = f"{row['home_team']} vs {row['away_team']}"
            missing[row["match_id"]] = key

        logger.info("📊 %s 缺失 %d 场比赛", league_name, len(missing))
        return missing

    # ========================================================================
    # V41.29: 青年队拦截 (Youth Team Blocking)
    # ========================================================================

    def is_youth_team_collision(self, team_a: str, team_b: str) -> bool:
        """
        V41.29: 检测青年队碰撞

        Args:
            team_a: 队伍A
            team_b: 队伍B

        Returns:
            是否为青年队碰撞（应该拦截）
        """
        return self.youth_detector.are_different_tiers(team_a, team_b)

    # ========================================================================
    # V41.37: 雷达搜索算法 (Radar Search)
    # ========================================================================

    def normalize_team_for_search(self, team_name: str) -> str:
        """
        标准化队名用于搜索

        Args:
            team_name: 原始队名

        Returns:
            标准化后的搜索词
        """
        # 移除 FC 前缀/后缀，转小写，空格转连字符
        normalized = team_name.lower()
        # 移除前导 "fc " 和后缀 " fc"
        normalized = re.sub(r"^fc\s+", "", normalized)
        normalized = re.sub(r"\s+fc\s*$", "", normalized)
        return re.sub(r"\s+", "-", normalized.strip())

    # ========================================================================
    # 幂等性: UPSERT 操作
    # ========================================================================

    def upsert_match_hash(
        self,
        match_id: str,
        hash_value: str,
        url: str,
        league_name: str,
        confidence: float = 0.98,
        method: str = "v41.40_carpet_sweep",
    ) -> bool:
        """
        幂等性更新比赛哈希（多次运行安全）

        V41.56 增强:
        - 拦截 OP_ 前缀的 match_id
        - 验证 URL 赛季与数据库赛季一致

        Args:
            match_id: 比赛 ID
            hash_value: 哈希值
            url: URL
            league_name: 联赛名称
            confidence: 置信度
            method: 映射方法

        Returns:
            是否更新成功
        """
        # V41.56: 拦截 OP_ 前缀的 match_id（幽灵记录）
        if match_id and match_id.startswith("OP_"):
            logger.error("🚨 V41.56: 拦截幽灵记录 - fotmob_id=%s 带有 OP_ 前缀", match_id)
            self.stats.skipped += 1
            return False

        # V41.56: 验证 URL 赛季与数据库赛季一致
        url_season = None
        if url and "[0-9]{4}-[0-9]{4}" in url:
            import re

            season_match = re.search(r"([0-9]{4}-[0-9]{4})", url)
            if season_match:
                url_season = season_match.group(1).replace("-", "/")
                # 从 matches 表获取实际赛季
                check_season_query = """
                    SELECT season FROM matches WHERE match_id = %s
                """
                with self.conn.cursor() as cur:
                    cur.execute(check_season_query, (match_id,))
                    result = cur.fetchone()
                    if result:
                        db_season = result["season"]
                        # 归一化赛季格式（23/24 → 2023/2024）
                        normalized_db_season = db_season.replace("/", "")
                        if len(normalized_db_season) == 4:
                            normalized_db_season = (
                                f"20{normalized_db_season[:2]}/20{normalized_db_season[2:]}"
                            )

                        # 检查赛季是否一致
                        if url_season not in (db_season, normalized_db_season):
                            logger.error(
                                "🚨 V41.56: 赛季错位拦截 - match_id=%s, db_season=%s, url_season=%s, url=%s",
                                match_id,
                                db_season,
                                url_season,
                                url,
                            )
                            self.stats.skipped += 1
                            return False

        # 检查哈希是否已被其他 match_id 使用
        check_query = """
            SELECT fotmob_id FROM matches_mapping
            WHERE oddsportal_hash = %s AND fotmob_id != %s
            LIMIT 1
        """

        # UPSERT 查询
        upsert_query = """
            INSERT INTO matches_mapping (
                fotmob_id, league_name, season, home_team, away_team,
                oddsportal_hash, oddsportal_url, confidence, mapping_method, review_status
            )
            SELECT %s, %s, m.season, m.home_team, m.away_team, %s, %s, %s, %s, 'approved'
            FROM matches m
            WHERE m.match_id = %s
            ON CONFLICT (fotmob_id)
            DO UPDATE SET
                oddsportal_hash = EXCLUDED.oddsportal_hash,
                oddsportal_url = EXCLUDED.oddsportal_url,
                confidence = GREATEST(matches_mapping.confidence, EXCLUDED.confidence),
                mapping_method = EXCLUDED.mapping_method,
                updated_at = NOW()
            WHERE matches_mapping.oddsportal_hash IS NULL
        """

        try:
            with self.conn.cursor() as cur:
                # 检查哈希冲突
                cur.execute(check_query, (hash_value, match_id))
                existing = cur.fetchone()

                if existing:
                    logger.warning(
                        "⚠️  Hash %s 已被 match_id=%s 使用", hash_value, existing["fotmob_id"]
                    )
                    self.stats.conflicts += 1
                    return False

                # 执行 UPSERT（使用 matches 表的实际 season，而非 self.season）
                cur.execute(
                    upsert_query,
                    (
                        match_id,
                        league_name,  # season 现在从 matches.m.season 获取
                        hash_value,
                        url,
                        confidence,
                        method,
                        match_id,
                    ),
                )
                self.conn.commit()

                logger.info("✅ 更新哈希: %s -> %s", match_id, hash_value)
                self.stats.updated += 1
                return True

        except psycopg2.IntegrityError as e:
            error_str = str(e).lower()
            if "duplicate key" in error_str or "unique" in error_str:
                logger.warning("⚠️  UNIQUE constraint: %s -> %s", match_id, hash_value)
                self.stats.conflicts += 1
                return False
            logger.exception("❌ 数据库错误")
            self.conn.rollback()
            return False

    # ========================================================================
    # V41.36: 跨日期校验 (Cross-Date Validation)
    # ========================================================================

    def validate_cross_date(
        self, target_date: datetime, actual_date: datetime, tolerance_hours: int = 24
    ) -> bool:
        """
        V41.36: 验证日期是否在容差范围内

        Args:
            target_date: 目标日期
            actual_date: 实际日期
            tolerance_hours: 容差小时数

        Returns:
            是否有效
        """
        if actual_date is None:
            return False

        delta = abs(target_date - actual_date)
        return delta <= timedelta(hours=tolerance_hours)

    # ========================================================================
    # V41.43: 隧道轮换 (Tunnel Rotation)
    # ========================================================================

    def get_random_proxy_port(self) -> int:
        """
        V41.43: 获取随机代理端口

        Returns:
            代理端口 (7890-7899)
        """
        # V41.121: 使用统一配置获取代理端口列表
        proxy_ports = self.get_proxy_ports()
        return random.choice(proxy_ports)

    def set_proxy_port(self, port: int | None = None) -> int:
        """
        V41.43: 设置代理端口环境变量

        Args:
            port: 代理端口，如果为 None 则随机选择

        Returns:
            设置的代理端口
        """
        # V41.121: 使用统一配置获取代理端口列表
        proxy_ports = self.get_proxy_ports()

        if port is None:
            port = self.get_random_proxy_port()

        if port not in proxy_ports:
            logger.warning("⚠️  代理端口 %d 不在允许范围内，使用随机端口", port)
            port = self.get_random_proxy_port()

        os.environ["PROXY_PORT"] = str(port)
        logger.debug("🔌 设置代理端口: %d", port)
        return port

    def get_proxy_port(self) -> int | None:
        """
        V41.43: 获取当前代理端口

        Returns:
            当前代理端口，如果未设置则返回 None
        """
        port_str = os.environ.get("PROXY_PORT")
        return int(port_str) if port_str else None

    # ========================================================================
    # V41.45: 代理容错机制 (Proxy Fault Tolerance)
    # ========================================================================

    def check_proxy_port_health(self, port: int, timeout: float = 1.0) -> bool:
        """
        V41.50: 检查代理端口健康状态（WSL2 适配）

        通过尝试连接端口来检测代理服务是否可用。
        自动检测 WSL2 环境并使用正确的代理主机地址。

        Args:
            port: 要检查的代理端口
            timeout: 连接超时时间（秒），默认 1 秒

        Returns:
            True 如果端口可用，False 如果端口不可用
        """
        try:
            # V41.50: 使用正确的代理主机地址
            proxy_host = self.get_proxy_host()
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((proxy_host, port))
            sock.close()
            return result == 0
        except OSError as e:
            logger.debug("⚠️  端口 %d 健康检查失败: %s", port, e)
            return False

    def get_healthy_proxy_port(
        self, excluded_ports: set[int] | None = None, max_attempts: int | None = None
    ) -> int | None:
        """
        V41.45: 获取健康的代理端口（带容错机制）

        按顺序尝试代理端口，跳过失效和被排除的端口，直到找到可用的端口。
        如果所有端口都不可用，返回 None。

        Args:
            excluded_ports: 要排除的端口集合（如最近失效的端口）
            max_attempts: 最大尝试次数，默认为所有端口数量

        Returns:
            可用的代理端口，如果所有端口都不可用则返回 None

        Example:
            >>> # 场景 1: 获取任意健康端口
            >>> port = service.get_healthy_proxy_port()
            >>>
            >>> # 场景 2: 排除最近失效的端口
            >>> failed_ports = {7890, 7891, 7892}
            >>> port = service.get_healthy_proxy_port(excluded_ports=failed_ports)
            >>>
            >>> # 场景 3: 限制尝试次数
            >>> port = service.get_healthy_proxy_port(max_attempts=5)
        """
        if excluded_ports is None:
            excluded_ports = set()

        # V41.121: 使用统一配置获取代理端口列表
        proxy_ports = self.get_proxy_ports()

        if max_attempts is None:
            max_attempts = len(proxy_ports)

        available_ports = [p for p in proxy_ports if p not in excluded_ports]

        if not available_ports:
            logger.warning("⚠️  没有可用的代理端口（所有端口都被排除）")
            return None

        # 打乱顺序以避免总是尝试相同的端口
        random.shuffle(available_ports)

        for port in available_ports[:max_attempts]:
            if self.check_proxy_port_health(port):
                logger.info("✅ 找到健康代理端口: %d", port)
                return port
            logger.debug("⚠️  端口 %d 不可用，尝试下一个...", port)

        logger.warning("⚠️  在 %d 次尝试后未找到健康代理端口", max_attempts)
        return None

    def set_proxy_port_with_retry(
        self, port: int | None = None, excluded_ports: set[int] | None = None, max_retry: int = 3
    ) -> int:
        """
        V41.45: 设置代理端口（带重试和容错）

        如果指定端口不可用，自动尝试其他端口。如果多次重试失败，
        将使用随机端口（即使可能不可用，以保证程序继续运行）。

        Args:
            port: 首选代理端口，如果为 None 则自动选择
            excluded_ports: 要排除的端口集合
            max_retry: 最大重试次数

        Returns:
            设置的代理端口（保证返回有效端口号）

        Raises:
            RuntimeError: 如果所有代理端口都不可用且系统无法恢复
        """
        # 如果指定了端口，先尝试该端口
        if port is not None:
            if self.check_proxy_port_health(port):
                os.environ["PROXY_PORT"] = str(port)
                logger.info("🔌 设置代理端口: %d (首选)", port)
                return port
            logger.warning("⚠️  首选端口 %d 不可用，尝试其他端口...", port)

        # 尝试获取健康端口（排除首选失败端口）
        if excluded_ports is None:
            excluded_ports = set()
        if port is not None:
            excluded_ports.add(port)

        # V41.121: 使用统一配置获取代理端口列表
        proxy_ports = self.get_proxy_ports()

        for attempt in range(max_retry):
            healthy_port = self.get_healthy_proxy_port(
                excluded_ports=excluded_ports, max_attempts=len(proxy_ports)
            )
            if healthy_port is not None:
                os.environ["PROXY_PORT"] = str(healthy_port)
                logger.info(
                    "🔌 设置代理端口: %d (重试 %d/%d)", healthy_port, attempt + 1, max_retry
                )
                return healthy_port
            logger.warning("⚠️  重试 %d/%d 失败，继续尝试...", attempt + 1, max_retry)

        # 所有尝试都失败，使用随机端口（降级策略）
        fallback_port = self.get_random_proxy_port()
        os.environ["PROXY_PORT"] = str(fallback_port)
        logger.error("🚨 所有代理端口不可用，使用降级端口: %d", fallback_port)
        return fallback_port

    # ========================================================================
    # V41.125: 多特征加权对齐引擎 (Multi-Feature Alignment Engine)
    # ========================================================================

    def align_with_multi_feature_validation(
        self, fotmob_match: dict[str, Any], oddsportal_match: dict[str, Any], verbose: bool = False
    ) -> dict[str, Any]:
        """
        V41.125: 多特征加权对齐验证 - 工业级 0.99 精准对齐

        加权策略:
        - 队名相似度 (50%): Levenshtein 距离算法
        - 比分强校验 (30%): score_str 标准化后绝对相等
        - 时间窗口校验 (10%): ±24h 内，按 exp(-diff) 指数衰减
        - ID 映射奖励 (10%): alias_teams 历史成功记录

        断言: 只有总分 ≥ 0.85 的记录才允许数据库自动关联

        Args:
            fotmob_match: FotMob 比赛数据（来自 matches 表）
                必需字段: home_team, away_team, match_date, score_str (可选)
            oddsportal_match: OddsPortal 比赛数据
                必需字段: home_team, away_team, match_time, score (可选)
            verbose: 是否输出详细得分拆解

        Returns:
            {
                "is_aligned": bool,        # 是否对齐成功 (分数 ≥ 0.85)
                "score": float,            # 综合评分 (0.0 - 1.0)
                "threshold": float,        # 对齐阈值 (0.85)
                "breakdown": {             # 得分拆解
                    "name_similarity": float,     # 队名相似度 (0.0 - 0.5)
                    "score_validation": float,    # 比分校验 (0.0 - 0.3)
                    "time_window": float,         # 时间窗口 (0.0 - 0.1)
                    "id_mapping": float,          # ID 映射 (0.0 - 0.1)
                },
                "reason": str,             # 对齐/拒绝原因
                "confidence": str          # 置信度: HIGH/MEDIUM/LOW
            }

        Example:
            >>> fotmob = {
            ...     "home_team": "Liverpool",
            ...     "away_team": "Chelsea",
            ...     "match_date": datetime(2024, 4, 20, 15, 0),
            ...     "score_str": "2:1",
            ... }
            >>> odds = {
            ...     "home_team": "Liverpool",
            ...     "away_team": "Chelsea",
            ...     "match_time": datetime(2024, 4, 20, 15, 0),
            ...     "score": "2:1",
            ... }
            >>> result = service.align_with_multi_feature_validation(fotmob, odds)
            >>> print(f"对齐: {result['is_aligned']}, 分数: {result['score']:.2f}")
            对齐: True, 分数: 0.95
        """
        score = 0.0
        breakdown = {
            "name_similarity": 0.0,
            "score_validation": 0.0,
            "time_window": 0.0,
            "id_mapping": 0.0,
        }
        reasons = []

        # ====================================================================
        # 1. 队名相似度 (50%) - Levenshtein 距离算法
        # ====================================================================
        fm_home = fotmob_match.get("home_team", "")
        fm_away = fotmob_match.get("away_team", "")
        op_home = oddsportal_match.get("home_team", "")
        op_away = oddsportal_match.get("away_team", "")

        # 使用 TeamNameNormalizer 计算相似度
        home_sim = self.normalizer.fuzzy_match(fm_home, op_home)
        away_sim = self.normalizer.fuzzy_match(fm_away, op_away)

        # 取两队相似度的平均值（fuzzy_match 返回 0-100，需归一化到 0.0-1.0）
        avg_name_sim = ((home_sim + away_sim) / 2.0) / 100.0

        # 映射到 0.0 - 0.5 分数 (50% 权重)
        name_score = avg_name_sim * 0.5
        breakdown["name_similarity"] = name_score
        score += name_score

        if avg_name_sim >= 0.95:
            reasons.append(f"队名完美匹配({avg_name_sim:.2f})")
        elif avg_name_sim >= 0.85:
            reasons.append(f"队名高相似度({avg_name_sim:.2f})")
        else:
            reasons.append(f"队名低相似度({avg_name_sim:.2f})")

        # ====================================================================
        # 2. 比分强校验 (30%) - score_str 标准化后绝对相等
        # ====================================================================
        fm_score = fotmob_match.get("score_str", "").strip()
        op_score = oddsportal_match.get("score", "").strip()

        # 标准化比分格式（"2:1" → "2-1" 等）
        fm_score_normalized = self._normalize_score(fm_score)
        op_score_normalized = self._normalize_score(op_score)

        if fm_score_normalized and op_score_normalized:
            # 比分强校验：绝对相等
            if fm_score_normalized == op_score_normalized:
                score_validation = 0.3
                reasons.append(f"比分验证通过({fm_score_normalized})")
            else:
                score_validation = 0.0
                reasons.append(f"比分不匹配({fm_score_normalized} vs {op_score_normalized})")
        else:
            # 无比分数据，不打分也不惩罚
            score_validation = 0.0
            if verbose:
                reasons.append("比分数据缺失（跳过验证）")

        breakdown["score_validation"] = score_validation
        score += score_validation

        # ====================================================================
        # 3. 时间窗口校验 (10%) - ±24h 内，exp(-diff) 指数衰减
        # ====================================================================
        fm_date = fotmob_match.get("match_date")
        op_time = oddsportal_match.get("match_time")

        if fm_date and op_time:
            # 确保都是 datetime 对象
            if isinstance(fm_date, str):
                fm_date = datetime.fromisoformat(fm_date.replace("Z", "+00:00"))
            if isinstance(op_time, str):
                op_time = datetime.fromisoformat(op_time.replace("Z", "+00:00"))

            # 计算时间差（小时）
            time_diff_hours = abs((fm_date - op_time).total_seconds()) / 3600.0

            if time_diff_hours <= 24:
                # 线性衰减: 1 - (diff/48)，0h = 1.0, 24h = 0.5
                decay_factor = max(0.5, 1.0 - (time_diff_hours / 48.0))
                time_window_score = decay_factor * 0.1
                reasons.append(f"时间窗口({time_diff_hours:.1f}h, 因子{decay_factor:.2f})")
            else:
                # 超过 24h，时间窗口得 0 分
                time_window_score = 0.0
                reasons.append(f"时间超限({time_diff_hours:.1f}h > 24h)")
        else:
            # 缺失时间数据，打部分分数（0.05 分）
            time_window_score = 0.05
            if verbose:
                reasons.append("时间数据缺失（部分分数）")

        breakdown["time_window"] = time_window_score
        score += time_window_score

        # ====================================================================
        # 4. ID 映射奖励 (10%) - alias_teams 历史成功记录
        # ====================================================================
        fm_home_id = fotmob_match.get("home_team_id")
        fm_away_id = fotmob_match.get("away_team_id")

        if fm_home_id or fm_away_id:
            # 检查是否有历史 ID 映射记录
            id_mapping_score = 0.0
            if self._check_id_mapping_history(fm_home_id, fm_away_id):
                id_mapping_score = 0.1
                reasons.append("ID 映射匹配")
            else:
                # 有 ID 但无历史记录，给部分分数 (0.05)
                id_mapping_score = 0.05
                if verbose:
                    reasons.append("ID 存在但无历史记录")
        else:
            # 无 ID 数据，不打分
            id_mapping_score = 0.0

        breakdown["id_mapping"] = id_mapping_score
        score += id_mapping_score

        # ====================================================================
        # 5. 综合判定
        # ====================================================================
        THRESHOLD = 0.85
        is_aligned = score >= THRESHOLD

        # 确定置信度
        if score >= 0.95:
            confidence = "HIGH"
        elif score >= 0.85:
            confidence = "MEDIUM"
        else:
            confidence = "LOW"

        # 生成对齐原因
        if is_aligned:
            reason = f"对齐成功: {', '.join(reasons)}"
        else:
            reason = f"对齐失败: {', '.join(reasons)}"

        # 详细输出
        if verbose:
            logger.info("🎯 V41.125 对齐详情:")
            logger.info(f"   队名相似度: {breakdown['name_similarity']:.3f} (50%)")
            logger.info(f"   比分校验: {breakdown['score_validation']:.3f} (30%)")
            logger.info(f"   时间窗口: {breakdown['time_window']:.3f} (10%)")
            logger.info(f"   ID 映射: {breakdown['id_mapping']:.3f} (10%)")
            logger.info(f"   综合评分: {score:.3f} / {THRESHOLD}")
            logger.info(f"   置信度: {confidence}")
            logger.info(f"   原因: {reason}")

        return {
            "is_aligned": is_aligned,
            "score": round(score, 3),
            "threshold": THRESHOLD,
            "breakdown": breakdown,
            "reason": reason,
            "confidence": confidence,
        }

    def _normalize_score(self, score: str) -> str:
        """
        V41.125: 标准化比分格式

        Args:
            score: 原始比分字符串 (如 "2:1", "2-1", "2 - 1")

        Returns:
            标准化后的比分 (如 "2-1")

        Examples:
            >>> _normalize_score("2:1")
            "2-1"
            >>> _normalize_score("2 - 1")
            "2-1"
        """
        if not score:
            return ""

        # 移除空格
        score = score.replace(" ", "")

        # 统一分隔符为 "-"
        return score.replace(":", "-")

    def _check_id_mapping_history(self, home_id: str | None, away_id: str | None) -> bool:
        """
        V41.125: 检查 ID 映射历史记录

        查询 alias_teams 表，检查该 team_id 是否有成功的对齐记录。

        V41.128: 修复列名错误（team_id → fotmob_team_id）

        Args:
            home_id: 主队 ID
            away_id: 客队 ID

        Returns:
            True 如果有历史记录，False 否则
        """
        if not home_id and not away_id:
            return False

        try:
            with self.conn.cursor() as cur:
                # V41.128: 修复列名（fotmob_team_id, is_active）
                cur.execute(
                    """
                    SELECT COUNT(*) as cnt
                    FROM alias_teams
                    WHERE (fotmob_team_id = %s OR fotmob_team_id = %s)
                      AND is_active = true
                """,
                    (home_id, away_id),
                )

                result = cur.fetchone()
                if result and result["cnt"] > 0:
                    return True

        except Exception as e:
            logger.debug(f"⚠️  ID 映射历史查询失败: {e}")

        return False

    # ========================================================================
    # V41.126: 工业化适配 (Industrial Adaptation)
    # ========================================================================

    def _inject_alias_mapping(
        self,
        fotmob_match: dict[str, Any],
        oddsportal_match: dict[str, Any],
        score: float,
        confidence: str,
    ) -> bool:
        """
        V41.126: 自动注浆别名库（V41.128 线程安全）

        当对齐分数 ≥ 0.95 (HIGH 置信度) 时，自动将队伍映射关系写入 alias_teams 表。
        实现"自我学习、自我完善"的别名库增长机制。

        V41.128: 使用线程锁保护并发注浆操作，避免多线程事务冲突。

        Args:
            fotmob_match: FotMob 比赛数据
            oddsportal_match: OddsPortal 比赛数据
            score: 对齐分数
            confidence: 对齐置信度 (HIGH/MEDIUM/LOW)

        Returns:
            True 如果注浆成功，False 否则
        """
        # 只在 HIGH 置信度时自动注浆
        if score < 0.95 or confidence != "HIGH":
            return False

        # V41.128: 使用类级线程锁保护并发注浆
        with self._alias_injection_lock:
            try:
                fotmob_home_id = fotmob_match.get("home_team_id")
                fotmob_away_id = fotmob_match.get("away_team_id")
                fotmob_home = fotmob_match.get("home_team", "")
                fotmob_away = fotmob_match.get("away_team", "")
                op_home = oddsportal_match.get("home_team", "")
                op_away = oddsportal_match.get("away_team", "")

                with self.conn.cursor() as cur:
                    # 注入主队映射
                    if fotmob_home_id:
                        cur.execute(
                            """
                            INSERT INTO alias_teams (
                                fotmob_team_id,
                                fotmob_team_name,
                                oddsportal_team_name,
                                confidence,
                                alignment_count,
                                league_name
                            ) VALUES (%s, %s, %s, %s, 1, %s)
                            ON CONFLICT (fotmob_team_id, oddsportal_team_name)
                            DO UPDATE SET
                                confidence = GREATEST(alias_teams.confidence, EXCLUDED.confidence),
                                alignment_count = alias_teams.alignment_count + 1,
                                last_aligned_at = NOW()
                        """,
                            (
                                fotmob_home_id,
                                fotmob_home,
                                op_home,
                                score,
                                fotmob_match.get("league_name", ""),
                            ),
                        )

                    # 注入客队映射
                    if fotmob_away_id:
                        cur.execute(
                            """
                            INSERT INTO alias_teams (
                                fotmob_team_id,
                                fotmob_team_name,
                                oddsportal_team_name,
                                confidence,
                                alignment_count,
                                league_name
                            ) VALUES (%s, %s, %s, %s, 1, %s)
                            ON CONFLICT (fotmob_team_id, oddsportal_team_name)
                            DO UPDATE SET
                                confidence = GREATEST(alias_teams.confidence, EXCLUDED.confidence),
                                alignment_count = alias_teams.alignment_count + 1,
                                last_aligned_at = NOW()
                        """,
                            (
                                fotmob_away_id,
                                fotmob_away,
                                op_away,
                                score,
                                fotmob_match.get("league_name", ""),
                            ),
                        )

                    self.conn.commit()
                    logger.info(
                        f"📝 V41.126 别名库注浆: {fotmob_home} vs {op_home}, {fotmob_away} vs {op_away} (分数: {score:.3f})"
                    )
                    return True

            except Exception as e:
                # V41.128: 添加更详细的错误日志，包括异常类型和参数
                import traceback

                logger.exception(f"❌ V41.126 别名库注浆失败: {type(e).__name__}: {e}")
                logger.debug(f"详细错误堆栈:\n{traceback.format_exc()}")
                logger.debug(
                    f"fotmob_home_id={fotmob_home_id}, fotmob_home={fotmob_home}, op_home={op_home}"
                )
                logger.debug(
                    f"fotmob_away_id={fotmob_away_id}, fotmob_away={fotmob_away}, op_away={op_away}"
                )
                try:
                    self.conn.rollback()
                except Exception as rollback_err:
                    logger.debug(f"回滚失败（事务已中止）: {rollback_err}")
                return False

    def _is_match_live_or_finished(self, fotmob_match: dict[str, Any]) -> bool:
        """
        V41.126: 判断比赛是否正在进行或已完场

        Args:
            fotmob_match: FotMob 比赛数据

        Returns:
            True 如果比赛正在进行或已完场，False 如果未开赛
        """
        # 方法 1: 检查比分数据
        score_str = fotmob_match.get("score_str", "").strip()
        if score_str and score_str not in ["", "0:0", "0-0", "-"]:
            # 有非零比分，说明已开赛
            return True

        # 方法 2: 检查比赛时间
        match_date = fotmob_match.get("match_date")
        if match_date:
            if isinstance(match_date, str):
                match_date = datetime.fromisoformat(match_date.replace("Z", "+00:00"))

            # 比赛时间已过，说明已开赛
            if datetime.now(match_date.tzinfo) > match_date:
                return True

        # 默认认为是未开赛
        return False

    def align_with_dynamic_weighting(
        self,
        fotmob_match: dict[str, Any],
        oddsportal_match: dict[str, Any],
        verbose: bool = False,
        auto_inject: bool = True,
    ) -> dict[str, Any]:
        """
        V41.126: 动态调权对齐 - 工业化适配版本

        加权策略（根据比赛状态动态调整）:
        - **已开赛/已完场**: 队名(50%) + 比分(30%) + 时间(10%) + ID(10%)，阈值 0.85
        - **未开赛**: 队名(80%) + 时间(20%)，阈值 0.80（无比分数据）

        自动注浆:
        - 分数 ≥ 0.95 时自动写入 alias_teams 表
        - 实现"自我学习、自我完善"的别名库增长

        Args:
            fotmob_match: FotMob 比赛数据
            oddsportal_match: OddsPortal 比赛数据
            verbose: 是否输出详细日志
            auto_inject: 是否自动注浆别名库（默认 True）

        Returns:
            对齐结果字典（包含 is_aligned, score, threshold, breakdown, reason, confidence）
        """
        # 判断比赛状态
        is_live_or_finished = self._is_match_live_or_finished(fotmob_match)

        if is_live_or_finished:
            # 已开赛/已完场：使用标准权重（50/30/10/10）
            result = self.align_with_multi_feature_validation(
                fotmob_match=fotmob_match, oddsportal_match=oddsportal_match, verbose=verbose
            )
        else:
            # 未开赛：使用动态权重（80% 队名 + 20% 时间）
            result = self._align_with_upcoming_weights(
                fotmob_match=fotmob_match, oddsportal_match=oddsportal_match, verbose=verbose
            )

        # 自动注浆别名库
        if auto_inject and result["is_aligned"] and result["score"] >= 0.95:
            self._inject_alias_mapping(
                fotmob_match=fotmob_match,
                oddsportal_match=oddsportal_match,
                score=result["score"],
                confidence=result["confidence"],
            )

        # 添加比赛状态标记
        result["match_status"] = "LIVE_OR_FINISHED" if is_live_or_finished else "UPCOMING"

        return result

    def _align_with_upcoming_weights(
        self, fotmob_match: dict[str, Any], oddsportal_match: dict[str, Any], verbose: bool = False
    ) -> dict[str, Any]:
        """
        V41.126: 未开赛比赛的动态调权对齐

        加权策略（未开赛）:
        - 队名相似度 (80%): 提高权重，因为无比分数据
        - 时间窗口 (20%): 提高权重，确保时间匹配
        - 阈值: 0.80（降低阈值，因为缺少比分验证）

        Args:
            fotmob_match: FotMob 比赛数据
            oddsportal_match: OddsPortal 比赛数据
            verbose: 是否输出详细日志

        Returns:
            对齐结果字典
        """
        score = 0.0
        breakdown = {"name_similarity": 0.0, "time_window": 0.0, "id_mapping": 0.0}
        reasons = []

        # ====================================================================
        # 1. 队名相似度 (80%) - Levenshtein 距离算法
        # ====================================================================
        fm_home = fotmob_match.get("home_team", "")
        fm_away = fotmob_match.get("away_team", "")
        op_home = oddsportal_match.get("home_team", "")
        op_away = oddsportal_match.get("away_team", "")

        home_sim = self.normalizer.fuzzy_match(fm_home, op_home)
        away_sim = self.normalizer.fuzzy_match(fm_away, op_away)

        # 归一化到 0.0-1.0
        avg_name_sim = ((home_sim + away_sim) / 2.0) / 100.0

        # 映射到 0.0 - 0.8 分数 (80% 权重)
        name_score = avg_name_sim * 0.8
        breakdown["name_similarity"] = name_score
        score += name_score

        if avg_name_sim >= 0.95:
            reasons.append(f"队名完美匹配({avg_name_sim:.2f})")
        elif avg_name_sim >= 0.85:
            reasons.append(f"队名高相似度({avg_name_sim:.2f})")
        else:
            reasons.append(f"队名低相似度({avg_name_sim:.2f})")

        # ====================================================================
        # 2. 时间窗口校验 (20%) - 线性衰减
        # ====================================================================
        fm_date = fotmob_match.get("match_date")
        op_time = oddsportal_match.get("match_time")

        if fm_date and op_time:
            if isinstance(fm_date, str):
                fm_date = datetime.fromisoformat(fm_date.replace("Z", "+00:00"))
            if isinstance(op_time, str):
                op_time = datetime.fromisoformat(op_time.replace("Z", "+00:00"))

            time_diff_hours = abs((fm_date - op_time).total_seconds()) / 3600.0

            if time_diff_hours <= 48:  # 未开赛放宽到 48 小时
                decay_factor = max(0.5, 1.0 - (time_diff_hours / 96.0))  # 48h → 0.5
                time_window_score = decay_factor * 0.2  # 20% 权重
                reasons.append(f"时间窗口({time_diff_hours:.1f}h, 因子{decay_factor:.2f})")
            else:
                time_window_score = 0.0
                reasons.append(f"时间超限({time_diff_hours:.1f}h > 48h)")
        else:
            time_window_score = 0.1  # 默认 0.1
            if verbose:
                reasons.append("时间数据缺失（部分分数）")

        breakdown["time_window"] = time_window_score
        score += time_window_score

        # ====================================================================
        # 3. ID 映射奖励（可选）
        # ====================================================================
        fm_home_id = fotmob_match.get("home_team_id")
        fm_away_id = fotmob_match.get("away_team_id")

        if fm_home_id or fm_away_id:
            id_mapping_score = 0.05  # 降低奖励
            reasons.append("ID 存在")
        else:
            id_mapping_score = 0.0

        breakdown["id_mapping"] = id_mapping_score
        score += id_mapping_score

        # ====================================================================
        # 4. 综合判定
        # ====================================================================
        THRESHOLD = 0.80  # 未开赛降低阈值
        is_aligned = score >= THRESHOLD

        # 确定置信度
        if score >= 0.90:
            confidence = "HIGH"
        elif score >= 0.80:
            confidence = "MEDIUM"
        else:
            confidence = "LOW"

        # 生成对齐原因
        if is_aligned:
            reason = f"对齐成功(未开赛): {', '.join(reasons)}"
        else:
            reason = f"对齐失败(未开赛): {', '.join(reasons)}"

        # 详细输出
        if verbose:
            logger.info("🎯 V41.126 未开赛对齐详情:")
            logger.info(f"   队名相似度: {breakdown['name_similarity']:.3f} (80%)")
            logger.info(f"   时间窗口: {breakdown['time_window']:.3f} (20%)")
            logger.info(f"   ID 映射: {breakdown['id_mapping']:.3f}")
            logger.info(f"   综合评分: {score:.3f} / {THRESHOLD}")
            logger.info(f"   置信度: {confidence}")
            logger.info(f"   原因: {reason}")

        return {
            "is_aligned": is_aligned,
            "score": round(score, 3),
            "threshold": THRESHOLD,
            "breakdown": breakdown,
            "reason": reason,
            "confidence": confidence,
        }

    # ========================================================================
    # V41.44: 全自动收割 (Active Harvest)
    # ========================================================================

    async def extract_matches_from_dom(self, page: Page) -> list[MatchInfo]:
        """
        V41.59: 从 Playwright Page 对象提取比赛信息（DOM 直取）- 异步版本

        使用 page.evaluate() 直接在浏览器中执行 JavaScript，比 BeautifulSoup 更可靠

        Args:
            page: Playwright Page 对象

        Returns:
            MatchInfo 列表
        """
        if not PLAYWRIGHT_AVAILABLE:
            logger.warning("⚠️  Playwright 不可用，回退到 HTML 解析")
            html = await page.content()  # V41.59: page.content() 也是异步的
            return self.extract_matches_from_html(html)

        # V41.59: 使用 await 调用 page.evaluate()
        matches = await page.evaluate("""
            () => {
                const results = [];

                // 查找所有包含比赛hash的链接
                const links = document.querySelectorAll('a[href*="/football/"]');

                links.forEach(link => {
                    const href = link.getAttribute('href');

                    // 只处理比赛详情页（8位hash）
                    if (!href || !href.match(/-[a-zA-Z0-9]{8}\\/?$/)) {
                        return;
                    }

                    results.push({
                        href: href
                    });
                });

                return results;
            }
        """)

        # 解析URL
        parsed_matches = []
        for match in matches:
            href = match.get("href", "")
            for pattern in self.HASH_PATTERNS:
                url_match = pattern.search(href)
                if url_match:
                    home_team_raw, away_team_raw, hash_str = url_match.groups()

                    # 格式化队名
                    home_team = home_team_raw.replace("-", " ").title()
                    away_team = away_team_raw.replace("-", " ").title()

                    parsed_matches.append(
                        MatchInfo(
                            home_team=home_team, away_team=away_team, hash_value=hash_str, url=href
                        )
                    )
                    break

        return parsed_matches

    async def active_harvest(
        self,
        league_name: str,
        max_pages: int = 10,
        headless: bool = True,
        league_config: dict | None = None,
    ) -> dict[str, int]:
        """
        V41.47: 全自动收割方法 - 集成 Playwright + 隧道轮换 + 代理容错 + Tier 分级延迟

        流程:
        1. 从 YAML 配置读取联赛 URL 和 Tier
        2. 使用容错机制选择健康代理端口（跳过失效端口）
        3. 根据 Tier 设置请求间隔（Tier 1: 10s, Tier 2: 15s, Tier 3: 20s）
        4. 启动浏览器，翻页采集所有比赛哈希
        5. 每页自动切换代理端口（带健康检查）
        6. 通过 upsert_match_hash 物理入库
        7. 异常安全：确保浏览器始终被关闭

        Args:
            league_name: 联赛名称
            max_pages: 最大翻页数
            headless: 是否无头模式
            league_config: 可选的联赛配置（包含 name, oddsportal_slug, tier, seasons）

        Returns:
            {
                "total_harvested": 总采集数,
                "total_updated": 总更新数,
                "total_conflicts": 冲突数,
                "pages_visited": 访问页数
            }
        """
        if not PLAYWRIGHT_AVAILABLE:
            logger.error("❌ Playwright 未安装，无法执行全自动收割")
            logger.error("   请运行: pip install playwright && playwright install")
            return {
                "total_harvested": 0,
                "total_updated": 0,
                "total_conflicts": 0,
                "pages_visited": 0,
            }

        # V41.47: 从 YAML 配置加载联赛信息（如果未提供）
        if league_config is None:
            # 首先尝试从 YAML 加载
            league_config = self._load_league_config_from_yaml(league_name)

            # 如果 YAML 中没有，回退到硬编码配置
            if league_config is None:
                hardcoded_config = self.LEAGUE_URLS.get(league_name)
                if hardcoded_config:
                    # 转换为 YAML 格式
                    base_url = hardcoded_config["url"]
                    # 从 URL 推断 tier（默认为 1）
                    league_config = {
                        "name": league_name,
                        "oddsportal_slug": base_url.replace(
                            "https://www.oddsportal.com/football/", ""
                        ).replace("/results/", ""),
                        "tier": 1,
                        "seasons": [self.season],
                    }
                else:
                    logger.error(f"❌ 联赛配置未找到: {league_name}")
                    return {
                        "total_harvested": 0,
                        "total_updated": 0,
                        "total_conflicts": 0,
                        "pages_visited": 0,
                    }

        # 获取联赛信息
        tier = league_config.get("tier", 3)
        league_name_cn = league_config.get("name_zh", league_config.get("name", league_name))

        # V41.47: 动态生成 URL
        season = league_config.get("seasons", [self.season])[0]
        base_url = self.get_league_url(league_config, season)

        # V41.47: Tier 分级延迟策略
        tier_delays = {
            1: 10.0,  # Tier 1 Premium: 10 秒延迟
            2: 15.0,  # Tier 2 Standard: 15 秒延迟
            3: 20.0,  # Tier 3 Basic: 20 秒延迟
        }
        page_delay = tier_delays.get(tier, 15.0)

        logger.info(f"🚀 V41.47 全自动收割启动: {league_name} ({league_name_cn})")
        logger.info(f"   URL: {base_url}")
        logger.info(f"   Tier: {tier}")
        logger.info(f"   请求间隔: {page_delay}s")
        logger.info(f"   最大页数: {max_pages}")

        stats = {"total_harvested": 0, "total_updated": 0, "total_conflicts": 0, "pages_visited": 0}

        # V41.45: 跟踪失效端口，避免重复尝试
        failed_ports: set[int] = set()

        browser = None
        try:
            async with async_playwright() as p:
                # V41.45: 使用容错机制选择初始代理端口
                proxy_port = self.set_proxy_port_with_retry(
                    excluded_ports=failed_ports, max_retry=3
                )

                # V41.60: 使用 Playwright 的 proxy 参数（TDD 验证通过）
                # V41.62: 添加指纹掩护 - ignoreDefaultArgs 隐藏自动化标记
                browser = await p.chromium.launch(
                    headless=headless,
                    proxy={"server": f"http://{self.get_proxy_host()}:{proxy_port}"},
                    args=[
                        "--disable-blink-features=AutomationControlled",
                        "--disable-dev-shm-usage",
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                        "--disable-web-security",
                        "--disable-features=IsolateOrigins,site-per-process",
                    ],
                    ignore_default_args=["--enable-automation"],
                )

                # V41.62: User-Agent 轮换 + 随机视口尺寸
                random_ua = random.choice(USER_AGENTS)
                random_viewport = random.choice(VIEWPORT_SIZES)

                context = await browser.new_context(
                    user_agent=random_ua,
                    viewport=random_viewport,
                    # V41.60: 添加真实浏览器特征（TDD 验证通过）
                    locale=random.choice(["en-US", "en-GB", "en-CA"]),
                    timezone_id=random.choice(
                        [
                            "Europe/London",
                            "Europe/Paris",
                            "Europe/Berlin",
                            "America/New_York",
                            "America/Los_Angeles",
                        ]
                    ),
                    # V41.62: 额外的浏览器指纹伪装
                    device_scale_factor=random.choice([1.0, 1.25, 1.5]),
                    has_touch=random.choice([True, False, False]),  # 33% 触摸屏
                )

                page = await context.new_page()

                try:
                    # 访问联赛结果页面
                    await page.goto(base_url, wait_until="networkidle", timeout=30000)
                    # V41.64: 随机延迟 Jitter (5-9秒) - 强化反爬对抗
                    initial_delay = random.uniform(5, 9)
                    await asyncio.sleep(initial_delay)

                    # V41.65: 初始化熔断机制计数器
                    empty_page_count = 0

                    for page_num in range(1, max_pages + 1):
                        logger.info(f"📖 正在处理第 {page_num} 页...")

                        # V41.45: 每页切换代理端口（带容错）
                        if page_num > 1:
                            new_proxy_port = self.set_proxy_port_with_retry(
                                excluded_ports=failed_ports, max_retry=2
                            )
                            if new_proxy_port != proxy_port:
                                logger.info(f"🔌 切换代理端口: {proxy_port} → {new_proxy_port}")
                                proxy_port = new_proxy_port

                        # V41.59: 使用 await 调用异步方法
                        matches = await self.extract_matches_from_dom(page)
                        stats["pages_visited"] += 1

                        logger.info(f"   提取到 {len(matches)} 场比赛")

                        # V41.65: 熔断机制 - 检测 Shadow Ban
                        if len(matches) == 0:
                            try:
                                page_title = await page.title()
                                if "Results" in page_title:
                                    empty_page_count += 1
                                    logger.warning(
                                        f"⚠️  检测到空页面（标题包含 'Results'），计数器: {empty_page_count}/3"
                                    )

                                    if empty_page_count >= 3:
                                        logger.error("🚨 触发 IP 保护熔断：检测到 Shadow Ban")
                                        logger.error(
                                            "   症状：连续 3 页提取到 0 场比赛，但页面标题正常"
                                        )
                                        logger.error("   建议：等待 6-24 小时冷却期，或更换代理 IP")
                                        logger.error("   正在强制退出以避免 IP 被永久封禁...")
                                        sys.exit(1)
                            except Exception as title_e:
                                logger.warning(f"⚠️  无法获取页面标题: {title_e}")
                        else:
                            # 重置计数器（检测到正常数据）
                            empty_page_count = 0

                        # 入库
                        for match_info in matches:
                            match_id = f"{league_name}_{match_info.hash_value}"

                            result = self.upsert_match_hash(
                                match_id=match_id,
                                hash_value=match_info.hash_value,
                                url=match_info.url,
                                league_name=league_name,
                                confidence=0.98,
                                method="v41.45_active_harvest",
                            )

                            stats["total_harvested"] += 1
                            if result:
                                stats["total_updated"] += 1
                            else:
                                stats["total_conflicts"] += 1

                        # V41.60: 尝试翻页（使用 URL 模式替代点击）
                        if page_num >= max_pages:
                            logger.info(f"✅ 已达到最大页数 {max_pages}")
                            break

                        # V41.60: URL 遍历模式（更可靠）
                        # 检查当前页面 URL 是否包含 /page/#
                        current_url = page.url
                        if "/page/" in current_url:
                            # 当前是分页 URL，构建下一页 URL
                            base_url_without_page = current_url.split("/page/")[0]
                            next_page_url = f"{base_url_without_page}/page/{page_num + 1}/"
                        else:
                            # 当前不是分页 URL，添加第一页
                            next_page_url = f"{base_url.rstrip('/')}/page/{page_num + 1}/"

                        logger.info(f"📍 翻页到第 {page_num + 1} 页: {next_page_url}")

                        try:
                            await page.goto(next_page_url, wait_until="networkidle", timeout=30000)
                            # V41.62: 随机延迟 Jitter (4-8秒)
                            page_delay = random.uniform(4, 8)
                            await asyncio.sleep(page_delay)

                            # 检查是否有内容（如果没有 hash 链接，说明到了最后一页）
                            check_hash = await self.extract_matches_from_dom(page)
                            if len(check_hash) == 0:
                                logger.info(f"✅ 第 {page_num + 1} 页无内容，结束翻页")
                                break

                        except Exception as e:
                            logger.warning(f"⚠️  URL 翻页失败: {e}")
                            # 回退到点击翻页
                            logger.info("   回退到点击翻页模式...")
                            try:
                                next_button = await page.query_selector(f"text={page_num + 1}")
                                if next_button:
                                    await next_button.click()
                                    await asyncio.sleep(page_delay)
                                else:
                                    logger.info(f"✅ 未找到第 {page_num + 1} 页按钮，结束翻页")
                                    break
                            except Exception as click_e:
                                logger.warning(f"⚠️  点击翻页也失败: {click_e}")
                                break

                    # V41.64: 收割冷却期 - 模拟用户自然节奏（强化版）
                    if stats["total_harvested"] > 0:
                        cooldown = random.uniform(60, 120)
                        logger.info(f"💤 收割冷却期: {cooldown:.1f} 秒（模拟用户自然节奏）")
                        await asyncio.sleep(cooldown)

                except Exception as e:
                    logger.exception(f"❌ 收割过程出错: {e}")
                    raise
                finally:
                    # V41.45: 浏览器清理闭环（确保资源释放）
                    if browser:
                        try:
                            await browser.close()
                            logger.info("✅ 浏览器已安全关闭")
                        except Exception as e:
                            logger.warning(f"⚠️  关闭浏览器时出错: {e}")

        except Exception as e:
            logger.exception(f"❌ V41.45 active_harvest 失败: {e}")
            # 确保即使外层异常也能返回统计信息
        finally:
            logger.info("=" * 60)
            logger.info(f"📊 {league_name} 收割统计:")
            logger.info(f"   总采集: {stats['total_harvested']} 场")
            logger.info(f"   成功更新: {stats['total_updated']} 场")
            logger.info(f"   冲突: {stats['total_conflicts']} 场")
            logger.info(f"   访问页数: {stats['pages_visited']} 页")
            logger.info("=" * 60)

        return stats


# ============================================================================
# 工厂函数
# ============================================================================


def create_hash_alignment_service(
    db_host: str = "localhost",
    db_name: str = "football_prediction_dev",
    db_user: str = "football_user",
    db_password: str = "football_pass",
    season: str = "23/24",
) -> HashAlignmentService:
    """
    创建哈希对齐服务实例

    Args:
        db_host: 数据库主机
        db_name: 数据库名称
        db_user: 数据库用户
        db_password: 数据库密码
        season: 目标赛季

    Returns:
        HashAlignmentService 实例
    """
    conn = psycopg2.connect(
        host=db_host,
        database=db_name,
        user=db_user,
        password=db_password,
        cursor_factory=psycopg2.extras.RealDictCursor,
    )

    return HashAlignmentService(conn, season=season)
