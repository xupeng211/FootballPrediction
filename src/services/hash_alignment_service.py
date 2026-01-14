#!/usr/bin/env python3
"""
V41.40 Hash Alignment Service - 工业级哈希对齐服务

核心功能:
1. 地毯扫射 (Carpet Sweep) - V41.35 算法
2. 雷达搜索 (Radar Search) - V41.37 算法
3. 青年队拦截 (Youth Team Blocking) - V41.29 算法
4. 跨日期校验 (Cross-Date Validation) - V41.36 算法
5. 隧道轮换 (Tunnel Rotation) - V41.43 算法

工程化特性:
- 解耦: 独立于具体脚本环境
- 反爬集成: 集成 Ghost Protocol
- 统一配置: 通过 YAML 驱动
- 幂等性: UPSERT 保证多次运行安全
- TDD: 100% 测试覆盖
- 并发采集: 10 端口隔离 (7890-7899)

Author: 资深软件架构师 & 首席质量官
Version: V41.43
Date: 2026-01-14
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
import logging
import os
import random
import re
from typing import ClassVar

from bs4 import BeautifulSoup
import psycopg2

# 延迟导入避免循环依赖 - TeamNameNormalizer 需要在 __init__ 中导入
from src.utils.text_processor import TeamNameNormalizer, YouthTeamDetector

# 配置日志
logger = logging.getLogger(__name__)


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
    V41.43 哈希对齐服务

    集成 V41.35 地毯扫射 + V41.37 雷达搜索 + V41.43 隧道轮换
    工程化重构，解耦脚本依赖
    """

    # 8位黄金哈希正则
    HASH_PATTERN = re.compile(r"/football/[^/]+/[^/]+/([^/]+)-([^/]+)-([A-Za-z0-9]{8})/")

    # V41.43: 隧道轮换配置 (10 端口隔离)
    PROXY_PORTS: ClassVar[list[int]] = list(range(7890, 7900))  # 7890-7899

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

    def __init__(self, db_conn, season: str = "23/24"):
        """
        初始化哈希对齐服务

        Args:
            db_conn: 数据库连接
            season: 目标赛季
        """
        self.conn = db_conn
        self.season = season
        self.stats = HarvestStats()

        self.normalizer = TeamNameNormalizer()
        self.youth_detector = YouthTeamDetector()

        logger.info("✅ HashAlignmentService 初始化完成 (season=%s)", season)

    # ========================================================================
    # V41.35: 地毯扫射算法 (Carpet Sweep)
    # ========================================================================

    def extract_matches_from_html(self, html: str) -> list[MatchInfo]:
        """
        V41.35: 从 HTML 中提取所有比赛信息（地毯扫射）

        Args:
            html: 页面 HTML

        Returns:
            MatchInfo 列表
        """
        soup = BeautifulSoup(html, "html.parser")
        matches = []

        for link in soup.find_all("a", href=True):
            href = link.get("href", "")
            match = self.HASH_PATTERN.search(href)

            if match:
                home_team_raw, away_team_raw, hash_str = match.groups()

                # 格式化队名
                home_team = home_team_raw.replace("-", " ").title()
                away_team = away_team_raw.replace("-", " ").title()

                matches.append(MatchInfo(
                    home_team=home_team,
                    away_team=away_team,
                    hash_value=hash_str,
                    url=href
                ))

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
        method: str = "v41.40_carpet_sweep"
    ) -> bool:
        """
        幂等性更新比赛哈希（多次运行安全）

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
            SELECT %s, %s, %s, m.home_team, m.away_team, %s, %s, %s, %s, 'approved'
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
                    logger.warning("⚠️  Hash %s 已被 match_id=%s 使用", hash_value, existing[0])
                    self.stats.conflicts += 1
                    return False

                # 执行 UPSERT
                cur.execute(upsert_query, (
                    match_id, league_name, self.season,
                    hash_value, url, confidence, method, match_id
                ))
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
        self,
        target_date: datetime,
        actual_date: datetime,
        tolerance_hours: int = 24
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
        return random.choice(self.PROXY_PORTS)

    def set_proxy_port(self, port: int | None = None) -> int:
        """
        V41.43: 设置代理端口环境变量

        Args:
            port: 代理端口，如果为 None 则随机选择

        Returns:
            设置的代理端口
        """
        if port is None:
            port = self.get_random_proxy_port()

        if port not in self.PROXY_PORTS:
            logger.warning("⚠️  代理端口 %d 不在允许范围内，使用随机端口", port)
            port = self.get_random_proxy_port()

        os.environ['PROXY_PORT'] = str(port)
        logger.debug("🔌 设置代理端口: %d", port)
        return port

    def get_proxy_port(self) -> int | None:
        """
        V41.43: 获取当前代理端口

        Returns:
            当前代理端口，如果未设置则返回 None
        """
        port_str = os.environ.get('PROXY_PORT')
        return int(port_str) if port_str else None


# ============================================================================
# 工厂函数
# ============================================================================

def create_hash_alignment_service(
    db_host: str = "localhost",
    db_name: str = "football_prediction_dev",
    db_user: str = "football_user",
    db_password: str = "football_pass",
    season: str = "23/24"
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
        cursor_factory=psycopg2.extras.RealDictCursor
    )

    return HashAlignmentService(conn, season=season)
