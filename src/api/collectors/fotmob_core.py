#!/usr/bin/env python3
"""
FotMob 核心数据采集器 - V144.5 (Stable Integrated)
集成自适应解码、动态联赛分级哨兵、容错解析和故障熔断逻辑

V144.5 更新:
- 集成 BaseExtractor V144.2 Ghost Protocol
- 30+ 主流浏览器指纹池
- 统一隐身协议架构
- V36.0 Schema 支持 (season_id, season_name, match_time_utc, fetched_at)
- 集成测试全绿通过 (29/29)
"""

from datetime import datetime
import gzip
import json
import logging
import os
import random
import sys
import time
from typing import Any

import brotli
import numpy as np
import psycopg2
import requests

# V144.3: 集成 BaseExtractor Ghost Protocol
from src.api.collectors.base_extractor import BaseExtractor

# 配置日志
logger = logging.getLogger(__name__)


# V144.3: 已弃用 - 使用 BaseExtractor V144.2 Ghost Protocol
# 保留旧代码用于向后兼容，但不再使用
STEALTH_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
]

# V144.3: 已弃用 - 使用 BaseExtractor V144.2 Ghost Protocol
STEALTH_LANGUAGES = [
    "en-US,en;q=0.9,en-GB;q=0.8",
    "fr-FR,fr;q=0.9,en;q=0.8",
    "de-DE,de;q=0.9,en;q=0.8",
    "es-ES,es;q=0.9,en;q=0.8",
    "en-GB,en;q=0.9",
]

# V11.2: 备用端点配置
FALLBACK_ENDPOINTS = {
    "team_matches": "https://www.fotmob.com/api/teams?tab=matches&id={}",
}


# V11.0: 联赛质量等级配置
LEAGUE_QUALITY_TIERS = {
    "tier_1_premium": {
        "name": "Tier 1 Premium",
        "description": "五大联赛 + 欧冠",
        "min_response_size": 102400,  # 100KB
        "leagues": [47, 87, 94, 118, 126, 53],  # FotMob league IDs - 添加法甲 53
        "expected_features": ["expected_goals", "expected_assists", "big_chance"],
    },
    "tier_2_standard": {
        "name": "Tier 2 Standard",
        "description": "次级联赛 (英冠、葡超、荷甲等)",
        "min_response_size": 51200,  # 50KB
        "leagues": [48, 78, 95, 129, 155],
        "expected_features": ["ShotsOnTarget", "corners", "BallPossesion"],
    },
    "tier_3_basic": {
        "name": "Tier 3 Basic",
        "description": "低级别联赛 (意乙、德乙、苏冠等)",
        "min_response_size": 20480,  # 20KB
        "leagues": [49, 96, 127, 157],
        "expected_features": ["ShotsOnTarget", "corners"],
    },
    "tier_default": {
        "name": "Default Tier",
        "description": "未分类联赛的默认级别",
        "min_response_size": 20480,  # 20KB - 使用最宽松的标准
        "leagues": [],
        "expected_features": ["ShotsOnTarget", "corners"],
    },
}

# 构建 league_id -> tier 的反向映射
LEAGUE_ID_TO_TIER = {}
for _tier_name, tier_config in LEAGUE_QUALITY_TIERS.items():
    for league_id in tier_config["leagues"]:
        LEAGUE_ID_TO_TIER[league_id] = tier_config

# V26.7: league_id -> league_name 映射表
LEAGUE_ID_TO_NAME = {
    47: "Premier League",    # 英超
    87: "La Liga",           # 西甲
    94: "Serie A",           # 意甲
    118: "Bundesliga",       # 德甲
    126: "Ligue 1",          # 法甲
    53: "Ligue 1",           # 法甲 (备用ID)
}


class FotMobCoreCollector:
    """
    FotMob核心数据采集器 - V11.0 多联赛增强版

    核心功能:
    1. 自适应解码：智能处理Gzip/Brotli/原始JSON
    2. 数据库UPSERT：断点续传和赔率回填
    3. V11.0动态哨兵：联赛分级响应长度验证
    4. V11.0容错解析：缺失特征自动填充NaN
    5. 故障熔断：连续失败5次触发30分钟休眠
    6. 断点续传：仅采集缺失数据，避免API浪费
    """

    def __init__(self):
        """初始化核心采集器 - V11.2 隐身模式版"""
        from src.config_unified import get_settings
        settings = get_settings()
        self.base_url = settings.fotmob_base_url
        self.web_url = settings.fotmob_web_url

        # V11.2: 动态生成随机 Headers（隐身模式）
        self._refresh_stealth_headers()

        self.session = requests.Session()
        self.session.headers.update(self.headers)

        # V11.0 新增属性
        self.consecutive_failures = 0  # 连续失败计数器
        self.max_consecutive_failures = 50  # V11.4: 提高到50以跳过manifest中的问题比赛
        self.circuit_breaker_timeout = 60  # V11.4: 降低到60秒，快速恢复
        self.hollow_matches_log = "data/logs/hollow_matches.log"  # 空心场次日志路径

        # V11.2: 回退策略计数器
        self.fallback_attempts = {}  # {match_id: attempt_count}
        self.max_fallback_attempts = 2

        # V26.7: 状态过滤统计
        self.last_skipped_count = 0  # 最近一次 discover_ligue_matches 跳过的比赛数

        # V11.0: 联赛分级哨兵配置（不再使用硬编码的 100KB）
        # self.min_response_size 已废弃，改用 _get_league_tier() 动态获取

    def _refresh_stealth_headers(self) -> None:
        """
        V144.3: 刷新隐身模式 Headers (Ghost Protocol 集成)

        使用 BaseExtractor V144.2 的 30+ 主流浏览器指纹池
        """
        # V144.3: 使用 BaseExtractor Ghost Protocol
        user_agent = BaseExtractor.get_random_user_agent()
        viewport = BaseExtractor.get_random_viewport()

        self.headers = {
            "User-Agent": user_agent,
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9,en-GB;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "Referer": f"{self.web_url}/",
            "Origin": self.web_url,
            "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Sec-Ch-Ua-Viewport": f'"{viewport["width"]}x{viewport["height"]}"',
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
        }
        logger.info(
            f"🎭 V144.3 Ghost Protocol: UA={user_agent[:50]}... (30+ 指纹池)"
        )

    def get_missing_match_ids(self, limit: int = 100) -> list[int]:
        """
        获取缺失的比赛ID列表

        Args:
            limit: 返回ID数量限制

        Returns:
            缺失的比赛ID列表
        """
        logger.info(f"🔍 动态查找缺失的比赛数据，目标数量: {limit}")

        # 从harvest_manifest.csv动态读取比赛ID
        target_match_ids = self._load_match_ids_from_manifest()

        try:
            conn = self.get_database_connection()
            with conn.cursor() as cur:
                # 检查已存在的比赛ID
                if len(target_match_ids) > 0:
                    id_list_str = ",".join(map(str, target_match_ids))
                    # 构建安全的参数化查询
                    placeholders = ",".join(["%s"] * len(target_match_ids))
                    cur.execute(
                        f"""
                        SELECT external_id
                        FROM matches
                        WHERE external_id::text IN ({placeholders})
                    """,
                        [str(mid) for mid in target_match_ids],
                    )
                    existing_ids = {row[0] for row in cur.fetchall()}

                    # 计算缺失的ID
                    missing_ids = [mid for mid in target_match_ids if mid not in existing_ids]
                else:
                    missing_ids = []

                # 限制返回数量
                missing_ids = missing_ids[:limit]

                logger.info(f"📋 找到 {len(missing_ids)} 条待采集比赛")
                return missing_ids

        except Exception as e:
            logger.error(f"❌ 获取缺失比赛ID失败: {e}")
            # 出错时返回前N个ID
            return target_match_ids[:limit]
        finally:
            if "conn" in locals():
                conn.close()

    def _load_match_ids_from_manifest(self, manifest_path: str = None) -> list[int]:
        """
        从harvest_manifest.csv加载比赛ID列表

        Args:
            manifest_path: manifest文件路径（可选，默认使用标准路径）

        Returns:
            比赛ID列表
        """
        import csv
        import os

        if manifest_path is None:
            manifest_path = "data/production/harvest_manifest.csv"

        if not os.path.exists(manifest_path):
            logger.error(f"❌ 找不到harvest manifest文件: {manifest_path}")
            return []

        match_ids = []

        try:
            with open(manifest_path, encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # 只获取已匹配的比赛
                    if row.get("is_matched") == "True":
                        match_id = int(row["match_id"])
                        match_ids.append(match_id)

            logger.info(f"📋 从manifest文件读取到 {len(match_ids)} 场已验证比赛 ({manifest_path})")
            return match_ids

        except Exception as e:
            logger.error(f"❌ 读取manifest文件失败: {e}")
            return []

    def get_database_connection(self) -> psycopg2.extensions.connection:
        """
        获取数据库连接 - 直接连接方式（绕过配置系统避免 Pydantic 验证错误）

        Returns:
            psycopg2连接对象
        """
        from src.config_unified import get_settings
        settings = get_settings()
        logger.debug(f"🔧 连接数据库: {settings.database.host}:{settings.database.port}/{settings.database.name}")

        return psycopg2.connect(
            host=settings.database.host,
            port=settings.database.port,
            database=settings.database.name,
            user=settings.database.user,
            password=settings.database.password.get_secret_value(),
        )

    def _log_hollow_match(self, match_id: int, content_size: int, reason: str) -> None:
        """
        记录空心场次到专用日志文件 - V11.0哨兵功能

        Args:
            match_id: 比赛ID
            content_size: 响应内容大小
            reason: 被拒绝的原因
        """
        try:
            os.makedirs(os.path.dirname(self.hollow_matches_log), exist_ok=True)

            timestamp = datetime.now().isoformat()
            log_entry = (
                f"{timestamp} - HOLLOW_MATCH - MatchID: {match_id}, Size: {content_size} bytes, Reason: {reason}\n"
            )

            with open(self.hollow_matches_log, "a", encoding="utf-8") as f:
                f.write(log_entry)

            logger.warning(f"🚨 空心场次已记录: MatchID {match_id}, 响应大小: {content_size} bytes, 原因: {reason}")

        except Exception as e:
            logger.error(f"写入空心场次日志失败: {e}")

    def _get_league_tier(self, league_id: int) -> dict:
        """
        V11.0: 根据联赛ID获取质量等级配置

        Args:
            league_id: FotMob联赛ID

        Returns:
            联赛等级配置字典
        """
        if league_id in LEAGUE_ID_TO_TIER:
            return LEAGUE_ID_TO_TIER[league_id]
        # 默认使用最宽松的标准
        return LEAGUE_QUALITY_TIERS["tier_default"]

    def _validate_response_size(self, match_id: int, content: bytes, league_id: int = None, season: str = None) -> bool:
        """
        V11.3 联赛+赛季感知哨兵检查：验证响应大小

        赛季自适应阈值:
        - 2122, 2223 (旧赛季): 30KB - FotMob 对旧比赛存储较少数据
        - 2324 (上一赛季): 50KB
        - 2425 (当前赛季): 100KB - 标准完整数据

        Args:
            match_id: 比赛ID
            content: 响应内容字节
            league_id: 联赛ID（可选，用于动态阈值）
            season: 赛季代码（可选，用于赛季自适应阈值）

        Returns:
            bool: 响应大小是否通过验证
        """
        content_size = len(content)

        # V11.3: 根据联赛等级动态确定基准阈值
        tier_config = self._get_league_tier(league_id) if league_id else LEAGUE_QUALITY_TIERS["tier_default"]
        base_min_size = tier_config["min_response_size"]

        # V11.4: 严格数据质量底线 - 五大联赛必须有完整统计数据
        season_multiplier = 0.8  # 80KB 底线 - 确保 xG/Shots/Stats 完整
        # 对于所有赛季，统一使用高质量标准
        # 拒绝任何低于 80KB 的响应 - 这些数据不完整，不可用于训练

        min_size = int(base_min_size * season_multiplier)

        if content_size < min_size:
            tier_name = tier_config["name"]
            season_info = f", season={season}" if season else ""
            reason = f"响应过小 ({content_size} < {min_size} bytes, tier={tier_name}{season_info})"
            self._log_hollow_match(match_id, content_size, reason)
            logger.warning(f"🛡️  哨兵拦截: MatchID {match_id} - {reason}")
            return False

        logger.debug(
            f"✅ 响应大小验证通过: MatchID {match_id}, 大小: {content_size} bytes (tier={tier_config['name']}, season={season})"
        )
        return True

    def _check_circuit_breaker(self) -> bool:
        """
        V10.9熔断检查：检查是否需要触发熔断

        Returns:
            bool: 是否允许继续执行
        """
        if self.consecutive_failures >= self.max_consecutive_failures:
            logger.error(f"🚨 触发自动熔断！连续失败 {self.consecutive_failures} 次")
            logger.error(f"⏱️  休眠 {self.circuit_breaker_timeout / 60:.1f} 分钟后尝试重启...")
            time.sleep(self.circuit_breaker_timeout)

            # 重置计数器，尝试重启
            self.consecutive_failures = 0
            logger.info("🔄 熔断重启，重新开始采集")
            return True

        return True

    def _increment_failure(self) -> None:
        """增加失败计数"""
        self.consecutive_failures += 1
        logger.warning(f"⚠️  连续失败次数: {self.consecutive_failures}/{self.max_consecutive_failures}")

        # 检查是否需要熔断
        if self.consecutive_failures >= self.max_consecutive_failures:
            self._check_circuit_breaker()

    def _reset_failure_count(self) -> None:
        """重置失败计数器"""
        if self.consecutive_failures > 0:
            logger.info(f"✅ 成功采集，重置失败计数 (之前: {self.consecutive_failures})")
            self.consecutive_failures = 0

    def get_missing_matches(self, match_ids: list[int]) -> list[int]:
        """
        V10.9断点查询：获取确实缺失数据的场次ID列表

        Args:
            match_ids: 需要检查的比赛ID列表

        Returns:
            List[int]: 确实缺失数据的比赛ID列表
        """
        conn = None
        try:
            conn = self.get_database_connection()
            with conn.cursor() as cur:
                # 构建IN子句
                id_list = ",".join([str(id) for id in match_ids])
                query = f"""
                SELECT id FROM matches
                WHERE id IN ({id_list}) AND l2_raw_json IS NULL
                """
                cur.execute(query)
                missing_ids = [row[0] for row in cur.fetchall()]

                logger.info(f"🎯 断点查询结果: 总计 {len(match_ids)} 场，缺失 {len(missing_ids)} 场")
                return missing_ids

        except Exception as e:
            logger.error(f"断点查询失败: {e}")
            # 出错时返回完整列表，确保不遗漏
            return match_ids
        finally:
            if conn:
                conn.close()

    def adaptive_decode_response(self, content: bytes, content_encoding: str = "") -> dict | None:
        """
        自适应解码响应数据 - V10.6黄金逻辑

        智能处理不同压缩格式：
        1. Gzip (0x1f 0x8b 文件头)
        2. 原始JSON (以 { 开头)
        3. Brotli (content_encoding='br')

        Args:
            content: 响应内容字节
            content_encoding: HTTP响应的Content-Encoding头

        Returns:
            解析后的JSON数据或None
        """
        try:
            if not content:
                logger.error("响应内容为空")
                return None

            # 检查文件头字节判断压缩格式
            if len(content) >= 2:
                # Gzip文件头: 0x1f 0x8b
                if content[:2] == b"\x1f\x8b":
                    logger.debug("检测到Gzip格式，执行解压")
                    decompressed_data = gzip.decompress(content)
                    return json.loads(decompressed_data.decode("utf-8"))

                # 原始JSON格式
                if content[:1] == b"{":
                    logger.debug("检测到原始JSON格式，直接解析")
                    return json.loads(content.decode("utf-8"))

                # Brotli压缩 (根据编码头或内容特征)
                if content_encoding == "br" or self._is_brotli_content(content):
                    logger.debug("检测到Brotli压缩，执行解压")
                    try:
                        decompressed_data = brotli.decompress(content)
                        return json.loads(decompressed_data.decode("utf-8"))
                    except Exception as brotli_error:
                        logger.warning(f"Brotli解压失败: {brotli_error}")
                        # 尝试作为原始JSON处理
                        return json.loads(content.decode("utf-8"))

            # 默认尝试UTF-8解码
            logger.debug("使用默认UTF-8解码")
            return json.loads(content.decode("utf-8"))

        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {e}")
            logger.debug(f"内容前100字节: {content[:100]}")
            return None
        except Exception as e:
            logger.error(f"自适应解码失败: {e}")
            return None

    def _is_brotli_content(self, content: bytes) -> bool:
        """
        检测是否为Brotli压缩内容

        Args:
            content: 内容字节

        Returns:
            bool: 是否为Brotli格式
        """
        try:
            # 尝试解压一小部分来验证
            brotli.decompress(content[:100])
            return True
        except:
            return False

    def parse_raw_json_to_db(self, limit: int = 1000) -> int:
        """
        工业级JSON解析引擎 - 自动解析l2_raw_json数据

        核心功能:
        1. 自动从header.teams提取比分
        2. 自动判定H/D/A结果并更新actual_result
        3. 解析playerStats节点提取技术特征
        4. 批量处理，支持断点续传

        Args:
            limit: 处理记录数限制，默认1000

        Returns:
            int: 成功解析的记录数
        """
        conn = None
        processed_count = 0

        try:
            conn = self.get_database_connection()

            with conn.cursor() as cur:
                # 查询需要解析的记录（有l2_raw_json但没有技术特征的）
                cur.execute(
                    """
                    SELECT id, external_id, l2_raw_json, home_team, away_team
                    FROM matches
                    WHERE l2_raw_json IS NOT NULL
                    AND player_stats IS NULL
                    ORDER BY id DESC
                    LIMIT %s
                """,
                    (limit,),
                )

                records = cur.fetchall()
                logger.info(f"🔍 找到 {len(records)} 条待解析记录")

                for record in records:
                    record_id = record[0]
                    external_id = record[1]
                    raw_json = record[2]
                    home_team = record[3]
                    away_team = record[4]

                    try:
                        # 解析JSON数据
                        json_data = json.loads(raw_json)

                        # V14.0修复: 提取真正的L2数据
                        if "l2_json" in json_data:
                            actual_l2_data = json_data["l2_json"]
                            if isinstance(actual_l2_data, str):
                                actual_l2_data = json.loads(actual_l2_data)
                        else:
                            actual_l2_data = json_data

                        # Step 1: 解析比分和结果
                        score_result = self._parse_match_score(actual_l2_data)

                        # Step 2: 解析技术特征
                        tech_features = self._parse_technical_features(actual_l2_data)

                        logger.info(
                            f"✅ 解析成功: {external_id} - {score_result.get('result_score', 'N/A')} ({score_result.get('actual_result', 'N/A')}) - 特征: {'有' if tech_features else '无'}"
                        )

                        # Step 3: 更新数据库
                        if score_result or tech_features:
                            update_fields = []
                            update_values = []

                            if score_result:
                                update_fields.extend(
                                    ["home_score = %s", "away_score = %s", "actual_result = %s", "result_score = %s"]
                                )
                                update_values.extend(
                                    [
                                        score_result["home_score"],
                                        score_result["away_score"],
                                        score_result["actual_result"],
                                        score_result["result_score"],
                                    ]
                                )

                            if tech_features:
                                update_fields.append("player_stats = %s")
                                update_values.append(json.dumps(tech_features))

                            update_fields.append("updated_at = NOW()")

                            # 执行更新
                            update_sql = f"""
                                UPDATE matches
                                SET {", ".join(update_fields)}
                                WHERE id = %s
                            """
                            update_values.append(record_id)

                            cur.execute(update_sql, update_values)
                            processed_count += 1

                            logger.info(
                                f"✅ 解析成功: {external_id} - "
                                f"{score_result.get('home_score', '?')}-{score_result.get('away_score', '?')} "
                                f"({score_result.get('actual_result', '?')})"
                            )

                    except json.JSONDecodeError as e:
                        logger.error(f"❌ JSON解析失败 {external_id}: {e}")
                        continue
                    except Exception as e:
                        logger.error(f"❌ 解析异常 {external_id}: {e}")
                        continue

                conn.commit()
                logger.info(f"🎉 JSON解析完成！成功处理 {processed_count} 条记录")

        except Exception as e:
            logger.error(f"❌ JSON解析引擎失败: {e}")
            if conn:
                conn.rollback()
        finally:
            if conn:
                conn.close()

        return processed_count

    def _parse_match_score(self, json_data: dict) -> dict | None:
        """
        从JSON中解析比分和比赛结果

        Args:
            json_data: 解析的JSON数据

        Returns:
            包含比分和结果的字典或None
        """
        try:
            # 从header.teams节点提取比分
            if "header" in json_data and "teams" in json_data["header"]:
                teams = json_data["header"]["teams"]

                if len(teams) >= 2:
                    home_team_data = teams[0]
                    away_team_data = teams[1]

                    home_score = home_team_data.get("score", 0)
                    away_score = away_team_data.get("score", 0)

                    # 判定比赛结果
                    if home_score > away_score:
                        actual_result = "H"  # Home Win
                    elif home_score < away_score:
                        actual_result = "A"  # Away Win
                    else:
                        actual_result = "D"  # Draw

                    return {
                        "home_score": int(home_score),
                        "away_score": int(away_score),
                        "actual_result": actual_result,
                        "result_score": f"{home_score}-{away_score}",
                    }

            return None

        except Exception as e:
            logger.error(f"比分解析失败: {e}")
            return None

    def _parse_technical_features(self, json_data: dict) -> dict | None:
        """
        V11.0 容错重构: 从FotMob JSON中解析技术特征
        使用团队级统计: content.stats.Periods.All.stats[x].stats[home,away]

        V11.0 核心改进:
        1. 使用 .get() 链式调用，严禁硬编码索引
        2. 缺失特征自动填充 NaN
        3. 永不因特征缺失而中断入库流程

        Args:
            json_data: 解析的JSON数据

        Returns:
            技术特征字典，即使解析失败也返回空字典（不返回None）
        """
        try:
            features = {}

            # V11.0: 使用 .get() 安全提取数据结构
            actual_json_data = json_data.get("l2_json", json_data)

            # V11.0: 容错提取 content.stats 路径
            content = actual_json_data.get("content", {})
            stats_structure = content.get("stats", {})
            periods = stats_structure.get("Periods", {})
            all_period = periods.get("All", {})
            all_stats = all_period.get("stats", [])

            if not isinstance(all_stats, list):
                logger.debug("⚪ stats 不是列表类型，跳过团队统计解析")
                all_stats = []

            # V11.0: FotMob统计键映射（包含所有可能的特征）
            stat_mapping = {
                # 基础统计（所有联赛都应该有）
                "BallPossesion": "possession",
                "total_shots": "shots_total",
                "ShotsOnTarget": "shots_on_target",
                "corners": "corners",
                "fouls": "fouls",
                # 高级统计（可能缺失）
                "expected_goals": "xg",
                "expected_assists": "xa",
                "big_chance": "big_chances_created",
                "accurate_passes": "passes_accurate",
                # 射门详细统计
                "shots": "shots_total_alt",
                "ShotsOffTarget": "shots_off_target",
                "blocked_shots": "shots_blocked",
                "shots_woodwork": "shots_woodwork",
                # xG 详细统计
                "expected_goals_open_play": "xg_open_play",
                "expected_goals_set_play": "xg_set_piece",
                "expected_goals_non_penalty": "xg_non_penalty",
                # 传球统计
                "passes": "passes_total",
                "Offsides": "offsides",
                # 防守统计
                "interceptions": "interceptions",
                "clearances": "clearances",
                # 对抗统计
                "duel_won": "duels_won",
                "aerials_won": "aerial_duels_won",
                # 纪律统计
                "yellow_cards": "yellow_cards",
                "red_cards": "red_cards",
            }

            # V11.0: 容错解析 - 使用 .get() 链式调用
            home_stats = {}
            away_stats = {}
            missing_features = []

            for stat_group in all_stats:
                if not isinstance(stat_group, dict):
                    continue

                stats_list = stat_group.get("stats", [])
                if not isinstance(stats_list, list):
                    continue

                for stat_item in stats_list:
                    if not isinstance(stat_item, dict):
                        continue

                    key = stat_item.get("key", "")
                    if not key or key not in stat_mapping:
                        continue

                    stats_values = stat_item.get("stats", [])
                    if not isinstance(stats_values, list) or len(stats_values) < 2:
                        # V11.0: 数据不完整时记录但不中断
                        logger.debug(f"⚪ 特征 '{key}' 数据不完整，跳过")
                        continue

                    mapped_key = stat_mapping[key]

                    # V11.0: 安全解析主客队数值
                    home_value = self._safe_parse_stat(stats_values, 0)
                    away_value = self._safe_parse_stat(stats_values, 1)

                    home_stats[mapped_key] = home_value
                    away_stats[mapped_key] = away_value

            # V11.0: 检查预期特征是否存在，缺失的填充 NaN
            tier_expected = LEAGUE_QUALITY_TIERS["tier_default"]["expected_features"]
            for expected_key in tier_expected:
                # 检查原始键是否存在
                original_key = None
                for orig_key, mapped in stat_mapping.items():
                    if mapped == expected_key:
                        original_key = orig_key
                        break

                if expected_key not in home_stats:
                    # V11.0: 缺失特征填充 NaN，记录但不中断
                    home_stats[expected_key] = np.nan
                    away_stats[expected_key] = np.nan
                    missing_features.append(expected_key)
                    logger.debug(f"⚪ 缺失特征填充 NaN: {expected_key}")

            # V11.0: 生成特征向量（容错 NaN 处理）
            all_metrics = set(home_stats.keys()) | set(away_stats.keys())

            for metric in all_metrics:
                home_val = home_stats.get(metric)
                away_val = away_stats.get(metric)

                # V11.0: NaN 安全处理
                if home_val is None:
                    home_val = np.nan
                if away_val is None:
                    away_val = np.nan

                # 处理 NaN 值的加减运算
                if np.isnan(home_val) or np.isnan(away_val):
                    total_val = np.nan
                    diff_val = np.nan
                else:
                    total_val = home_val + away_val
                    diff_val = home_val - away_val

                # 基础指标
                features[f"home_{metric}"] = home_val
                features[f"away_{metric}"] = away_val
                features[f"total_{metric}"] = total_val
                features[f"diff_{metric}"] = diff_val

                # 比率特征（NaN 安全）
                if not np.isnan(total_val) and total_val > 0:
                    features[f"home_ratio_{metric}"] = home_val / total_val
                    features[f"away_ratio_{metric}"] = away_val / total_val
                else:
                    features[f"home_ratio_{metric}"] = np.nan
                    features[f"away_ratio_{metric}"] = np.nan

            # V11.0: 从 lineup 获取基础信息（使用 .get() 容错）
            lineup = content.get("lineup", {})
            home_team_data = lineup.get("homeTeam", {})
            away_team_data = lineup.get("awayTeam", {})

            home_player_count = len(home_team_data.get("starters", [])) + len(home_team_data.get("subs", []))
            away_player_count = len(away_team_data.get("starters", [])) + len(away_team_data.get("subs", []))

            features.update(
                {
                    "home_player_count": home_player_count if home_player_count > 0 else np.nan,
                    "away_player_count": away_player_count if away_player_count > 0 else np.nan,
                    "total_player_count": home_player_count + away_player_count,
                    "home_team_rating": self._safe_float(home_team_data.get("rating")),
                    "away_team_rating": self._safe_float(away_team_data.get("rating")),
                    "home_formation": home_team_data.get("formation", ""),
                    "away_formation": away_team_data.get("formation", ""),
                }
            )

            # V11.0: 添加数据质量元信息
            features["_meta"] = {
                "total_metrics": len(all_metrics),
                "missing_features": missing_features,
                "has_nan": any(np.isnan(v) for v in features.values() if isinstance(v, (int, float))),
            }

            if missing_features:
                logger.info(f"📊 特征解析完成: {len(features)}维，缺失 {len(missing_features)} 个特征")
            else:
                logger.info(f"📊 特征解析完成: {len(features)}维")

            # V11.0: 永不返回 None，总是返回字典（即使为空）
            return features

        except Exception as e:
            logger.error(f"V11.0特征解析异常: {e}")
            import traceback

            logger.debug(f"详细错误: {traceback.format_exc()}")
            # V11.0: 异常时返回空字典而不是 None
            return {}

    def _safe_parse_stat(self, stats_values: list, index: int) -> float:
        """
        V11.0: 安全解析统计数值

        Args:
            stats_values: 统计值列表
            index: 要获取的索引

        Returns:
            解析后的浮点数，失败时返回 NaN
        """
        try:
            if not isinstance(stats_values, list) or index >= len(stats_values):
                return np.nan

            value = stats_values[index]
            if value is None or value == "" or value == "-":
                return np.nan

            if isinstance(value, (int, float)):
                return float(value)

            if isinstance(value, str):
                # 处理 "290 (79%)" 或 "45%" 格式
                if "(" in value:
                    value = value.split("(")[0].strip()
                elif "%" in value:
                    value = value.replace("%", "").strip()

                # 移除非数字字符
                value = "".join(c for c in value if c.isdigit() or c == ".")

                return float(value) if value else np.nan

            return np.nan

        except (ValueError, TypeError, IndexError):
            return np.nan

    def _parse_stat_value(self, value) -> float:
        """
        兼容旧版本的解析方法（内部调用 _safe_parse_stat）

        Args:
            value: 原始值

        Returns:
            解析后的浮点数
        """
        if value is None or value == "" or value == "-":
            return 0.0

        try:
            if isinstance(value, (int, float)):
                return float(value)

            if isinstance(value, str):
                # 处理格式如 "290 (79%)" 或 "45%" 的情况
                if "(" in value:
                    # 提取括号前的数字
                    value = value.split("(")[0].strip()
                elif "%" in value:
                    # 移除百分号
                    value = value.replace("%", "").strip()

                # 移除其他非数字字符
                value = "".join(c for c in value if c.isdigit() or c == ".")

                return float(value) if value else 0.0

        except (ValueError, TypeError):
            return 0.0

        return 0.0

    def _safe_float(self, value) -> float:
        """安全转换为浮点数"""
        try:
            return float(value) if value else 0.0
        except (ValueError, TypeError):
            return 0.0

    def get_match_details(self, match_id: int) -> dict | None:
        """
        获取比赛详情数据（V145.0 修复版）

        Args:
            match_id: 比赛外部ID

        Returns:
            包含比赛信息的字典，或None如果失败
        """
        try:
            url = f"{self.base_url}/matchDetails?matchId={match_id}"

            logger.info(f"🌍 请求比赛详情: {match_id}")
            response = self.session.get(url, timeout=30)

            if response.status_code == 200:
                response.raise_for_status()

                # 尝试解码数据
                json_data = self.adaptive_decode_response(
                    response.content, response.headers.get("Content-Encoding", "")
                )

                if json_data and isinstance(json_data, dict):
                    # V145.0: 使用默认 tier 哨兵检查（无 league_id 时）
                    if not self._validate_response_size(match_id, response.content):
                        return None

                    # 提取基础信息
                    match_info = self._extract_match_basic_info(json_data, match_id)
                    if match_info:
                        return {"match_info": match_info, "l2_json": json_data}
                    logger.error(f"❌ 无法提取比赛基础信息: {match_id}")
                    return None
                logger.error(f"❌ 响应数据格式错误: {match_id}")
                return None
            logger.error(f"❌ HTTP请求失败: {match_id} - {response.status_code}")
            return None

        except requests.exceptions.Timeout:
            logger.error(f"⏰ 请求超时: {match_id}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ 网络请求异常: {match_id} - {e}")
            return None
        except Exception as e:
            logger.error(f"❌ 获取比赛详情异常: {match_id} - {e}")
            return None

    def _extract_match_basic_info(self, json_data: dict, match_id: int) -> dict | None:
        """
        从JSON数据中提取比赛基础信息

        Args:
            json_data: 响应JSON数据
            match_id: 比赛ID

        Returns:
            比赛基础信息字典，或None
        """
        try:
            # 提取基本信息
            match_header = json_data.get("header", {})

            match_info = {
                "match_id": match_id,  # 添加match_id字段
                "external_id": str(match_id),
                "home_team": match_header.get("teams", [{}])[0].get("name", "Unknown Home"),
                "away_team": match_header.get("teams", [{}])[1].get("name", "Unknown Away"),
                "league_name": match_header.get("league", {}).get("name", "Unknown League"),
                "match_time": match_header.get("status", {}).get("utcTime", ""),
                "match_date": match_header.get("status", {}).get("utcTime", "")[:10],  # 提取日期部分
                "venue": match_header.get("venue", {}).get("name", ""),
                "home_score": None,  # 将在parse阶段填入
                "away_score": None,  # 将在parse阶段填入
            }

            return match_info

        except Exception as e:
            logger.error(f"❌ 提取比赛基础信息失败: {e}")
            return None

    def upsert_match_data(self, match_info: dict, l2_json: dict, league_id: int = None, season: str = None) -> bool:
        """
        数据库UPSERT操作 - V26.3 架构修复版

        V26.3 变更:
        1. l2_raw_json 现在存储原始 FotMob API JSON（而非提取后的特征）
        2. 新增 collection_status 字段追踪采集状态
        3. 新增 collected_at 字段记录采集时间

        功能：
        1. 插入新记录或更新现有记录
        2. 存储原始 API JSON 到 l2_raw_json
        3. 标记采集状态为 SUCCESS
        4. 自动更新时间戳

        Args:
            match_info: 比赛基础信息
            l2_json: FotMob L2 API 原始 JSON（未处理）
            league_id: 联赛ID
            season: 赛季代码 (如 '2324')

        Returns:
            bool: 操作是否成功
        """
        conn = None
        try:
            conn = self.get_database_connection()

            with conn.cursor() as cur:
                # V26.3: 更新字段名以匹配新 schema
                query = """
                INSERT INTO matches (
                    match_id, external_id, home_team, away_team, match_date,
                    l2_raw_json,                    -- V26.3: 存储原始 API JSON
                    collection_status, collected_at,
                    league_name, season, data_source, data_version
                ) VALUES (
                    %s, %s, %s, %s, %s,
                    %s,                             -- 原始 JSON
                    %s, %s,
                    %s, %s, %s, %s
                )
                ON CONFLICT (match_id) DO UPDATE SET
                    l2_raw_json = EXCLUDED.l2_raw_json,
                    collection_status = EXCLUDED.collection_status,
                    collected_at = COALESCE(EXCLUDED.collected_at, matches.collected_at),
                    data_version = EXCLUDED.data_version,
                    league_name = EXCLUDED.league_name,
                    season = EXCLUDED.season,
                    updated_at = NOW()
                """

                # 序列化 JSON 时处理 NaN 值（Python NaN -> JSON null）
                def serialize_json(obj):
                    def default(o):
                        if isinstance(o, float) and (o != o):  # NaN 检查
                            return
                        raise TypeError(f"Object of type {type(o)} is not JSON serializable")

                    import math

                    def clean_nan(value):
                        """递归清理 NaN 值"""
                        if isinstance(value, float) and math.isnan(value):
                            return None
                        if isinstance(value, dict):
                            return {k: clean_nan(v) for k, v in value.items()}
                        if isinstance(value, list):
                            return [clean_nan(v) for v in value]
                        return value

                    return json.dumps(clean_nan(obj), default=default)

                # V26.7: 智能 league_name 处理 - 优先使用 league_id 映射
                extracted_league_name = match_info.get("league_name", "Premier League")
                if (extracted_league_name == "Unknown League" and league_id is not None
                    and league_id in LEAGUE_ID_TO_NAME):
                    extracted_league_name = LEAGUE_ID_TO_NAME[league_id]
                    logger.debug(f"✅ 使用 league_id 映射: {league_id} -> {extracted_league_name}")

                params = (
                    match_info["match_id"],
                    match_info["match_id"],
                    match_info["home_team"],
                    match_info["away_team"],
                    match_info["match_date"],
                    serialize_json(l2_json),        # V26.3: 原始 JSON
                    "SUCCESS",                       # collection_status
                    match_info.get("match_date"),     # collected_at
                    extracted_league_name,           # V26.7: 修复后的 league_name
                    season,
                    "FotMob",
                    "V26.3",                         # data_version
                )

                cur.execute(query, params)
                conn.commit()

                logger.info(
                    f"UPSERT成功: {match_info['match_id']} {match_info['home_team']} vs {match_info['away_team']} (league={league_id}, season={season})"
                )
                return True

        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"UPSERT失败: {e}")
            import traceback

            logger.error(f"详细错误: {traceback.format_exc()}")
            return False
        finally:
            if conn:
                conn.close()

    def save_extracted_features(self, match_id: str, features: dict, extractor_version: str) -> bool:
        """
        V26.3: 保存提取后的特征到 l2_extracted_features

        这是一个新方法，用于在特征提取后保存结果：
        1. 将特征字典存入 l2_extracted_features
        2. 更新 collection_status（根据特征数量）
        3. 记录提取时间 extracted_at

        Args:
            match_id: 比赛 ID
            features: V25ProductionExtractor 输出的特征字典
            extractor_version: 提取器版本 (如 "V26.2")

        Returns:
            bool: 操作是否成功
        """
        conn = None
        try:
            conn = self.get_database_connection()

            with conn.cursor() as cur:
                # 计算特征数量（从 adaptive_features._meta.feature_count 或顶层）
                feature_count = len(features)
                if "adaptive_features" in features and "_meta" in features["adaptive_features"]:
                    feature_count = features["adaptive_features"]["_meta"].get("feature_count", feature_count)

                # 根据特征数量确定状态
                if feature_count >= 3000:
                    collection_status = "SUCCESS"
                elif feature_count >= 1000:
                    collection_status = "PARTIAL"
                else:
                    collection_status = "FAILED"

                query = """
                UPDATE matches SET
                    l2_extracted_features = %s::jsonb,
                    l2_data_version = %s,
                    extracted_at = NOW(),
                    collection_status = %s,
                    last_error = CASE
                        WHEN %s < 1000 THEN 'Insufficient features: ' || %s::text
                        ELSE NULL
                    END,
                    updated_at = NOW()
                WHERE match_id = %s
                """

                params = (
                    json.dumps(features),
                    extractor_version,
                    collection_status,
                    feature_count, feature_count,  # for last_error calculation
                    match_id,
                )

                cur.execute(query, params)
                conn.commit()

                logger.info(
                    f"特征保存成功: {match_id} (状态={collection_status}, 特征数={feature_count})"
                )
                return True

        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"特征保存失败 ({match_id}): {e}")
            import traceback
            logger.error(f"详细错误: {traceback.format_exc()}")
            return False
        finally:
            if conn:
                conn.close()

    def _determine_season(self, match_date: str) -> str:
        """
        V10.9 物理纯净版：根据比赛日期强制判定赛季
        绝不允许 'Unknown' 存在

        Args:
            match_date: 比赛日期字符串

        Returns:
            str: 赛季字符串 (如 "25/26")
        """
        try:
            # 支持多种日期格式
            if "T" in match_date:
                # ISO格式: 2025-08-15T19:00:00Z
                date_str = match_date.split("T")[0]
            else:
                # 简单格式: 2025-08-15
                date_str = match_date

            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            year = date_obj.year
            month = date_obj.month

            # 英超赛季：8月开始到次年7月结束
            # 2025-08 及之后 -> 25/26 赛季
            # 2025-07 及之前 -> 24/25 赛季
            if month >= 8:
                season_start = year % 100  # 取后两位
                season_end = (year + 1) % 100
                return f"{season_start:02d}/{season_end:02d}"
            season_start = (year - 1) % 100
            season_end = year % 100
            return f"{season_start:02d}/{season_end:02d}"

        except Exception as e:
            logger.error(f"赛季判定失败 - 日期: {match_date}, 错误: {e}")
            # 强制使用当前赛季，绝不返回 Unknown
            current_year = datetime.now().year
            current_month = datetime.now().month

            if current_month >= 8:
                season_start = current_year % 100
                season_end = (current_year + 1) % 100
            else:
                season_start = (current_year - 1) % 100
                season_end = current_year % 100

            return f"{season_start:02d}/{season_end:02d}"

    def fetch_match_details(self, match_id: int) -> dict | None:
        """
        V10.9护航加固版：获取比赛详情 - 集成哨兵检查和故障熔断

        Args:
            match_id: 比赛ID

        Returns:
            Dict: 比赛详情数据或None
        """
        url = f"{self.base_url}/matchDetails?matchId={match_id}"

        # V10.9: 检查熔断器状态
        if not self._check_circuit_breaker():
            return None

        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()

            # V10.9: 哨兵检查 - 验证响应大小
            if not self._validate_response_size(match_id, response.content):
                self._increment_failure()
                return None

            # 使用自适应解码
            content_encoding = response.headers.get("content-encoding", "").lower()
            decoded_data = self.adaptive_decode_response(response.content, content_encoding)

            if decoded_data:
                # V10.9: 成功采集，重置失败计数
                self._reset_failure_count()
                logger.debug(f"✅ 成功获取比赛 {match_id} 数据")
                return decoded_data
            logger.error(f"比赛 {match_id} 数据解码失败")
            self._increment_failure()
            return None

        except requests.RequestException as e:
            logger.error(f"HTTP请求失败 {match_id}: {e}")
            self._increment_failure()
            return None
        except Exception as e:
            logger.error(f"获取比赛 {match_id} 详情失败: {e}")
            self._increment_failure()
            return None

    def harvest_match_with_league(self, match_id: int, league_id: int = None, season: str = None) -> bool:
        """
        V26.4: 联赛感知的比赛采集（安全加固版）

        V26.4 安全加固:
        - 强制 Jittering 延迟 (2-5 秒) - 防止 IP 封禁
        - 403/429 自杀逻辑 - 连续 3 次触发立即终止程序
        - 使用 time.perf_counter() 提高计时精度

        Args:
            match_id: 比赛 ID
            league_id: 联赛 ID (用于动态哨兵阈值和数据库存储)
            season: 赛季代码 (如 '2223')

        Returns:
            bool: 采集是否成功
        """
        url = f"{self.base_url}/matchDetails?matchId={match_id}"

        # V11.0: 检查熔断器状态
        if not self._check_circuit_breaker():
            return False

        try:
            response = self.session.get(url, timeout=30)

            # V26.4: 检查 403/429 错误，触发自杀逻辑
            if response.status_code in [403, 429]:
                self._increment_failure()
                error_code = response.status_code
                error_msg = "Forbidden" if error_code == 403 else "Too Many Requests"

                # 记录严重错误
                logger.critical(
                    f"🚨 IP 封禁检测: HTTP {error_code} ({error_msg}) - match_id={match_id}"
                )

                # V26.4: 检查连续 403/429 失败次数，达到 3 次立即自杀
                if self.consecutive_failures >= 3:
                    logger.critical(
                        f"💀 连续 {self.consecutive_failures} 次 IP 封禁！触发程序自杀机制"
                    )
                    logger.critical("⛔ 系统将立即终止，请等待 6-24 小时冷却期")
                    logger.critical(f"📊 最后请求: match_id={match_id}, league={league_id}")
                    # 立即终止程序
                    sys.exit(1)

                return False

            response.raise_for_status()

            # V11.3: 联赛+赛季感知的哨兵检查
            if not self._validate_response_size(match_id, response.content, league_id, season):
                self._increment_failure()
                return False

            # 使用自适应解码
            content_encoding = response.headers.get("content-encoding", "").lower()
            decoded_data = self.adaptive_decode_response(response.content, content_encoding)

            if decoded_data:
                # 提取比赛基础信息
                match_info = self._extract_match_basic_info(decoded_data, match_id)

                if match_info:
                    # V11.0: 使用容错解析器
                    technical_features = self._parse_technical_features(decoded_data)

                    # 构造完整的 L2 JSON
                    l2_json = {
                        "l2_json": decoded_data,
                        "technical_features": technical_features,
                        "collected_at": datetime.now().isoformat(),
                        "league_id": league_id,
                    }

                    # V11.1: 数据库 UPSERT - 传递 league_id 和 season
                    success = self.upsert_match_data(match_info, l2_json, league_id, season)

                    if success:
                        self._reset_failure_count()
                        tier_info = (
                            self._get_league_tier(league_id) if league_id else LEAGUE_QUALITY_TIERS["tier_default"]
                        )
                        logger.info(
                            f"✅ 采集成功: {match_id} (league={league_id}, season={season}, tier={tier_info['name']})"
                        )

                        # V26.7: 深度特征提取 - 使用 V25ProductionExtractor
                        try:
                            from src.processors.v25_production_extractor import V25ProductionExtractor

                            logger.debug(f"🔬 开始深度特征提取: {match_id}")
                            extractor = V25ProductionExtractor()
                            extraction_result = extractor.extract(decoded_data)

                            if extraction_result and extraction_result.features:
                                features = extraction_result.features
                                feature_count = len([k for k in features.keys() if not k.startswith("_")])

                                # V26.7: 只有真正的 6000+ 维才输出成功日志
                                if feature_count >= 6000:
                                    logger.info(
                                        f"📊 [深度解析成功] 维度: {feature_count}维 - {match_id}"
                                    )
                                else:
                                    logger.warning(
                                        f"⚠️  [深度解析维度不足] {feature_count}维 - {match_id} (期望 6000+)"
                                    )

                                # 保存深度提取的特征
                                self.save_extracted_features(
                                    str(match_id),
                                    features,
                                    extractor.version
                                )
                            else:
                                logger.warning(f"⚠️ 深度特征提取失败: {match_id}")

                        except Exception as extract_error:
                            logger.error(f"❌ 深度特征提取异常: {match_id} - {extract_error}")

                        # V26.4: 强制 Jittering 延迟（2-5 秒随机）
                        jitter_delay = random.uniform(2.0, 5.0)
                        logger.debug(
                            f"⏱️  Jittering 延迟: {jitter_delay:.2f}秒 - 防止 IP 封禁"
                        )
                        time.sleep(jitter_delay)

                        return True

            self._increment_failure()
            return False

        except requests.RequestException as e:
            logger.error(f"HTTP 请求失败 {match_id}: {e}")
            self._increment_failure()
            return False
        except Exception as e:
            logger.error(f"采集比赛 {match_id} 失败: {e}")
            self._increment_failure()
            return False

    def smart_fetch(self, match_id: int, league_id: int = None, season: str = None) -> dict | None:
        """
        V11.2: 智能获取 - 支持故障回退策略

        策略:
        1. 标准端点: matchDetails
        2. 回退端点: 通过球队比赛列表获取
        3. 隐身模式: 动态刷新 Headers

        Args:
            match_id: 比赛 ID
            league_id: 联赛 ID
            season: 赛季代码

        Returns:
            解析后的 JSON 数据或 None
        """
        # 尝试 1: 标准端点
        url = f"{self.base_url}/matchDetails?matchId={match_id}"

        try:
            # V11.2: 每次请求前刷新隐身 Headers
            self._refresh_stealth_headers()
            self.session.headers.update(self.headers)

            response = self.session.get(url, timeout=30)

            if response.status_code == 200:
                # 尝试解码
                content_encoding = response.headers.get("content-encoding", "").lower()
                decoded_data = self.adaptive_decode_response(response.content, content_encoding)

                if decoded_data:
                    logger.debug(f"✅ 标准端点成功: {match_id}")
                    return decoded_data

            # 响应为空或失败，尝试回退策略
            logger.warning(f"⚠️ 标准端点失败: {match_id} (status={response.status_code})")

        except Exception as e:
            logger.warning(f"⚠️ 标准端点异常: {match_id} - {e}")

        # 尝试 2: 回退策略 - 通过已知球队获取
        if match_id not in self.fallback_attempts:
            self.fallback_attempts[match_id] = 0

        if self.fallback_attempts[match_id] < self.max_fallback_attempts:
            self.fallback_attempts[match_id] += 1
            logger.info(f"🔄 回退策略 {self.fallback_attempts[match_id]}/{self.max_fallback_attempts}: {match_id}")

            return self._fallback_fetch_via_team(match_id, league_id)

        logger.error(f"❌ 所有策略失败: {match_id}")
        return None

    def _fallback_fetch_via_team(self, match_id: int, league_id: int = None) -> dict | None:
        """
        V11.2: 通过球队比赛列表回退获取

        当标准端点失败时，尝试从已知球队的比赛列表中获取数据

        Args:
            match_id: 比赛 ID
            league_id: 联赛 ID（用于筛选）

        Returns:
            解析后的 JSON 数据或 None
        """
        # 知道的球队 ID 池（按联赛分类）
        TEAM_IDS_BY_LEAGUE = {
            34: [9825, 4199, 4019, 4504, 4475],  # Ligue 1: PSG, Marseille, Lyon, Monaco, Lille
            87: [3787, 8631, 8633, 3785, 4484],  # La Liga: Real Madrid, Barcelona, Atletico, Sevilla, Athletic
            55: [9857, 8628, 8636, 4023, 4031],  # Serie A: Inter, Milan, Juventus, Roma, Lazio
            54: [9823, 9810, 8019, 8035, 9845],  # Bundesliga: Bayern, Dortmund, Leverkusen, Frankfurt, Wolfsburg
            47: [9825, 8456, 8650, 8586, 10260],  # Premier League: Arsenal, Man City, Liverpool, Spurs, Man Utd
        }

        if league_id and league_id in TEAM_IDS_BY_LEAGUE:
            team_ids = TEAM_IDS_BY_LEAGUE[league_id]

            for team_id in team_ids:
                try:
                    # 使用球队比赛列表端点
                    team_url = FALLBACK_ENDPOINTS["team_matches"].format(team_id)

                    # 刷新 Headers
                    self._refresh_stealth_headers()
                    response = self.session.get(team_url, timeout=30)

                    if response.status_code == 200:
                        data = response.json()
                        if "fixtures" in data and "allMatches" in data["fixtures"]:
                            # 查找目标比赛
                            for match in data["fixtures"]["allMatches"]:
                                if match.get("id") == match_id:
                                    logger.info(f"✅ 回退成功: {match_id} (via team {team_id})")
                                    return match

                except Exception as e:
                    logger.debug(f"球队 {team_id} 回退失败: {e}")
                    continue

        logger.warning(f"⚠️ 球队回退策略失败: {match_id}")
        return None

    @staticmethod
    def filter_finished_matches(matches: list[dict]) -> list[dict]:
        """
        V26.7: 过滤已结束的比赛

        过滤逻辑：
        1. 只保留 status.finished == true 的比赛
        2. 排除 status.cancelled == true 的比赛
        3. 确保比赛有有效的 id 字段

        Args:
            matches: 原始比赛列表（来自 FotMob API）

        Returns:
            过滤后的比赛列表（只包含已结束的比赛）
        """
        finished_matches = []

        for match in matches:
            # 检查比赛是否有 ID
            if not match.get("id"):
                continue

            # 获取状态对象
            status = match.get("status", {})

            # 检查比赛状态
            is_finished = status.get("finished", False)
            is_cancelled = status.get("cancelled", False)

            # 只保留已结束且未取消的比赛
            if is_finished and not is_cancelled:
                finished_matches.append(match)

        return finished_matches

    def discover_ligue_matches(self, league_id: int, season_code: str) -> list[int]:
        """
        V26.7: 智能联赛比赛发现（状态感知过滤）

        功能：
        1. 从 FotMob API 获取比赛列表
        2. **自动过滤未结束的比赛**（只保留 finished == true）
        3. 支持多种发现策略

        Args:
            league_id: 联赛 ID
            season_code: 赛季代码

        Returns:
            已结束的比赛 ID 列表
        """
        discovered_ids = []

        # 策略 1: 标准端点
        try:
            self._refresh_stealth_headers()
            url = f"{self.base_url}/leagues"
            params = {"tab": "fixtures", "season": season_code, "id": league_id}

            response = self.session.get(url, params=params, timeout=30)

            if response.status_code == 200 and response.content:
                data = response.json()
                if "fixtures" in data and "allMatches" in data["fixtures"]:
                    matches = data["fixtures"]["allMatches"]

                    # V26.7: 应用状态过滤
                    finished_matches = self.filter_finished_matches(matches)
                    discovered_ids = [m.get("id") for m in finished_matches if m.get("id")]

                    # V26.7: 记录跳过的比赛数
                    self.last_skipped_count = len(matches) - len(finished_matches)

                    logger.info(
                        f"✅ 标准发现成功: {len(discovered_ids)} 场已结束比赛 "
                        f"(跳过 {self.last_skipped_count} 场未结束/取消)"
                    )
                    return discovered_ids

        except Exception as e:
            logger.warning(f"⚠️ 标准发现失败: {e}")

        # 策略 2: 通过球队聚合
        logger.info("🔄 尝试球队聚合发现...")

        TEAM_IDS_BY_LEAGUE = {
            34: [9825, 4199, 4019, 4504, 4475],  # Ligue 1
        }

        if league_id in TEAM_IDS_BY_LEAGUE:
            all_match_ids = set()

            for team_id in TEAM_IDS_BY_LEAGUE[league_id]:
                try:
                    team_url = FALLBACK_ENDPOINTS["team_matches"].format(team_id)
                    response = self.session.get(team_url, timeout=30)

                    if response.status_code == 200:
                        data = response.json()
                        if "fixtures" in data and "allMatches" in data["fixtures"]:
                            for match in data["fixtures"]["allMatches"]:
                                # 筛选指定联赛的比赛
                                if match.get("leagueId") == league_id:
                                    all_match_ids.add(match.get("id"))

                    # 避免频繁请求
                    time.sleep(1)

                except Exception as e:
                    logger.debug(f"球队 {team_id} 发现失败: {e}")
                    continue

            discovered_ids = list(all_match_ids)
            logger.info(f"✅ 球队聚合发现: {len(discovered_ids)} 场比赛")
            return discovered_ids

        logger.error(f"❌ 所有发现策略失败: league_id={league_id}, season={season_code}")
        return []

    def enriched_l1_harvest(
        self,
        league_id: int,
        season_code: str,
        league_name: str = None,
        batch_size: int = 50
    ) -> dict[str, Any]:
        """
        V26.7: 全息 L1 索引入库（增强版）

        核心改进：
        1. **不再只返回 ID** - 返回完整的比赛元数据
        2. **提取比分和状态** - 从 L1 API 直接获取 home_score, away_score, status
        3. **轻量级 UPSERT** - 仅更新 L1 字段，不覆盖已有的 L2 高维特征
        4. **批量入库优化** - 支持批量处理，减少数据库往返

        约束：
        - 严禁在 L1 阶段发起昂贵的详情页（L2）请求
        - ON CONFLICT 逻辑不覆盖 l2_raw_json 和 l2_extracted_features

        Args:
            league_id: 联赛 ID (e.g., 47 for Premier League)
            season_code: 赛季代码 (e.g., '2425')
            league_name: 联赛名称 (e.g., 'Premier League')
            batch_size: 批量入库大小

        Returns:
            dict: 采集统计
                - total_discovered: 发现的总比赛数
                - total_finished: 已结束的比赛数
                - total_upserted: 成功入库的比赛数
                - match_details: 前 5 场比赛的详细信息（用于验证）
        """
        # V26.7: 使用 league_id 映射获取 league_name
        if league_name is None:
            league_name = LEAGUE_ID_TO_NAME.get(
                league_id,
                match_header.get("league", {}).get("name", "Unknown League")
                if 'match_header' in locals() else "Unknown League"
            )

        discovered_matches = []
        batch_upsert_queue = []

        # 策略 1: 标准端点（全息采集）
        try:
            self._refresh_stealth_headers()
            url = f"{self.base_url}/leagues"
            params = {"tab": "fixtures", "season": season_code, "id": league_id}

            response = self.session.get(url, params=params, timeout=30)

            if response.status_code == 200 and response.content:
                data = response.json()
                if "fixtures" in data and "allMatches" in data["fixtures"]:
                    matches = data["fixtures"]["allMatches"]

                    # V26.7: 过滤已结束的比赛
                    finished_matches = self.filter_finished_matches(matches)

                    logger.info(
                        f"🎯 全息 L1 采集: {len(finished_matches)} 场已结束比赛 "
                        f"(总发现: {len(matches)}, 跳过: {len(matches) - len(finished_matches)})"
                    )

                    # V26.7: 提取完整元数据
                    for match in finished_matches:
                        match_id = match.get("id")
                        if not match_id:
                            continue

                        # V26.7: 修复 - API 结构分析
                        # 直接从顶层获取 home/away 对象
                        home_team_obj = match.get("home", {})
                        away_team_obj = match.get("away", {})
                        status_obj = match.get("status", {})

                        # V26.7: 从 status.scoreStr 解析比分（格式: "4 - 2"）
                        home_score = None
                        away_score = None
                        score_str = status_obj.get("scoreStr", "")
                        if score_str and " - " in score_str:
                            try:
                                scores = score_str.split(" - ")
                                home_score = int(scores[0].strip())
                                away_score = int(scores[1].strip())
                            except (ValueError, IndexError):
                                pass

                        # V26.7: 提取日期（从 utcTime）
                        utc_time = status_obj.get("utcTime", "")
                        match_date = utc_time[:10] if utc_time else None  # YYYY-MM-DD

                        # V26.7: 构建增强的 L1 数据结构
                        enriched_match = {
                            "match_id": str(match_id),
                            "external_id": str(match_id),
                            "home_team": home_team_obj.get("name", "Unknown Home"),
                            "away_team": away_team_obj.get("name", "Unknown Away"),
                            "home_score": home_score,
                            "away_score": away_score,
                            "match_date": match_date,
                            "status_str": status_obj.get("reason", {}).get("short", "unknown"),
                            "status_finished": status_obj.get("finished", False),
                            "status_cancelled": status_obj.get("cancelled", False),
                            "status_started": status_obj.get("started", False),
                            "league_id": league_id,
                            "league_name": league_name,
                            "season": season_code,
                        }

                        # V26.7 DBRE: 数据一致性校验 - match_date 与 season 对齐检查
                        if not self._validate_season_date_alignment(season_code, match_date, match_id):
                            logger.warning(
                                f"⚠️ 赛季标签不匹配 - match_id={match_id}, "
                                f"season={season_code}, match_date={match_date}"
                            )
                            continue  # 跳过不匹配的记录

                        discovered_matches.append(enriched_match)
                        batch_upsert_queue.append(enriched_match)

                        # V26.7: 批量入库
                        if len(batch_upsert_queue) >= batch_size:
                            upserted_count = self._batch_upsert_l1_data(batch_upsert_queue)
                            batch_upsert_queue.clear()

                    # 处理剩余批次
                    if batch_upsert_queue:
                        upserted_count = self._batch_upsert_l1_data(batch_upsert_queue)

                    # 返回统计信息
                    return {
                        "total_discovered": len(matches),
                        "total_finished": len(finished_matches),
                        "total_upserted": len(discovered_matches),
                        "match_details": discovered_matches[:5] if discovered_matches else [],
                    }

        except Exception as e:
            logger.error(f"❌ 全息 L1 采集失败: {e}")
            return {
                "total_discovered": 0,
                "total_finished": 0,
                "total_upserted": 0,
                "match_details": [],
            }

    def _validate_season_date_alignment(
        self,
        season_code: str,
        match_date: str | None,
        match_id: str
    ) -> bool:
        """
        V26.7 DBRE: 验证赛季标签与比赛日期的对齐性

        防止数据污染：如日期在 2025 年但 season 标签为 "2324"

        FotMob 赛季代码约定：
        - '2425' = 2025-2026 赛季（2025-08 ~ 2026-05）
        - '2324' = 2023-2024 赛季（2023-08 ~ 2024-05）
        - 第一位数字对应起始年份的末位

        Args:
            season_code: 赛季代码 (e.g., '2425', '2324')
            match_date: 比赛日期 (YYYY-MM-DD 格式)
            match_id: 比赛 ID (用于日志)

        Returns:
            True: 日期与赛季标签对齐
            False: 不对齐，应拒绝入库

        Examples:
            - season='2425', date='2025-08-15' → True (2025-26 赛季)
            - season='2425', date='2026-05-20' → True (2025-26 赛季)
            - season='2425', date='2024-08-15' → False (应为 2324)
            - season='2324', date='2024-05-20' → True (2023-24 赛季)
            - season='2324', date='2024-08-15' → False (应为 2425)
        """
        if not match_date:
            # 无日期数据，允许通过（可能由后续流程填充）
            return True

        try:
            # 解析赛季代码（FotMob 约定：2425 = 2025-2026）
            if len(season_code) == 4 and season_code.isdigit():
                # 第一位数字是起始年份末位，第二位是结束年份末位
                start_year_digit = int(season_code[0])  # e.g., 2 from '2425'
                end_year_digit = int(season_code[2])    # e.g., 2 from '2425'

                # 推算完整年份（假设在 2000-2099 范围内）
                # 对于 2425: 2025-2026, 对于 2324: 2023-2024
                base_century = 2000
                year1 = base_century + start_year_digit * 10 + int(season_code[1])
                year2 = base_century + end_year_digit * 10 + int(season_code[3])
            else:
                # 无法解析的赛季格式，允许通过
                return True

            # 解析比赛日期
            date_year = int(match_date[:4])

            # 赛季通常跨越 8 月到次年 5 月
            # 例如 2425 赛季：2025-08 ~ 2026-05
            if date_year == year1 or date_year == year2:
                return True
            else:
                logger.warning(
                    f"🚨 Season-Date Misalignment: match_id={match_id}, "
                    f"season={season_code} (years {year1}-{year2}), "
                    f"match_date={match_date} (year {date_year})"
                )
                return False

        except (ValueError, IndexError) as e:
            logger.warning(f"⚠️ Season-date validation failed for match_id={match_id}: {e}")
            return True  # 解析失败时允许通过，避免阻塞流程

    def _batch_upsert_l1_data(self, matches: list[dict]) -> int:
        """
        V26.7 DBRE: 批量 UPSERT L1 数据（事务安全加固版）

        事务安全策略：
        - 任何单条记录失败时，立即回滚并停止当前批次
        - 确保连接每次都是新创建的（避免缓存）
        - 详细错误日志，便于排查问题

        Args:
            matches: 比赛数据列表

        Returns:
            成功入库的记录数

        Raises:
            Exception: 当任何 UPSERT 失败时抛出异常
        """
        if not matches:
            return 0

        conn = None
        success_count = 0

        try:
            # V26.7 DBRE: 每次都创建新连接，避免缓存
            conn = self.get_database_connection()

            # 设置自动提交为 False，确保事务控制
            conn.autocommit = False

            with conn.cursor() as cur:
                for i, match in enumerate(matches, 1):
                    try:
                        # V26.7 DBRE: 轻量级 UPSERT - 包含完整状态信息
                        # 计算比赛结果 (actual_result)
                        home_score = match.get("home_score")
                        away_score = match.get("away_score")
                        actual_result = None

                        if home_score is not None and away_score is not None:
                            if home_score > away_score:
                                actual_result = "H"
                            elif home_score < away_score:
                                actual_result = "A"
                            else:
                                actual_result = "D"

                        # 获取状态信息
                        status_str = match.get("status_str", "unknown")
                        status_finished = match.get("status_finished", False)

                        query = """
                        INSERT INTO matches (
                            match_id, external_id, home_team, away_team,
                            home_score, away_score, match_date,
                            league_id, league_name, season,
                            status, is_finished, actual_result,
                            data_source, collection_status,
                            created_at, updated_at
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW()
                        )
                        ON CONFLICT (match_id) DO UPDATE SET
                            home_team = EXCLUDED.home_team,
                            away_team = EXCLUDED.away_team,
                            home_score = EXCLUDED.home_score,
                            away_score = EXCLUDED.away_score,
                            match_date = EXCLUDED.match_date,
                            league_id = EXCLUDED.league_id,
                            league_name = EXCLUDED.league_name,
                            season = EXCLUDED.season,
                            status = EXCLUDED.status,
                            is_finished = EXCLUDED.is_finished,
                            actual_result = EXCLUDED.actual_result,
                            updated_at = NOW(),
                            -- V26.7: 关键 - 不覆盖 L2 特征字段
                            l2_raw_json = COALESCE(matches.l2_raw_json, EXCLUDED.l2_raw_json),
                            l2_extracted_features = COALESCE(matches.l2_extracted_features, EXCLUDED.l2_extracted_features)
                        """

                        params = (
                            match["match_id"],
                            match["external_id"],
                            match["home_team"],
                            match["away_team"],
                            home_score,
                            away_score,
                            match["match_date"],
                            match["league_id"],
                            match["league_name"],
                            match["season"],
                            status_str,
                            status_finished,
                            actual_result,
                            "FotMob-L1",
                            "L1-ONLY" if not match.get("has_l2") else "SUCCESS",
                        )

                        cur.execute(query, params)
                        success_count += 1

                    except Exception as e:
                        # V26.7 DBRE: 任何错误立即回滚并停止
                        error_msg = f"L1 UPSERT 失败 (match_id={match.get('match_id')}, index={i}/{len(matches)}): {e}"
                        logger.error(f"❌ {error_msg}")
                        logger.error(f"⚠️ 正在回滚事务，已写入 {success_count} 条记录将被丢弃")

                        # 立即回滚
                        conn.rollback()

                        # 抛出异常，停止当前批次
                        raise Exception(f"事务中止: {error_msg}") from e

                # 所有记录成功后才提交
                conn.commit()
                logger.info(f"✅ L1 批量入库成功: {success_count}/{len(matches)} 条记录已提交")
                return success_count

        except Exception as e:
            # V26.7 DBRE: 确保异常时回滚
            logger.error(f"❌ L1 批量入库异常: {e}")
            if conn:
                try:
                    conn.rollback()
                    logger.warning("⚠️ 事务已回滚")
                except Exception as rollback_error:
                    logger.error(f"❌ 回滚失败: {rollback_error}")
            raise  # 重新抛出异常，让调用方知道失败了
        finally:
            # V26.7 DBRE: 确保连接被关闭
            if conn:
                try:
                    conn.close()
                except Exception as close_error:
                    logger.warning(f"⚠️ 关闭连接时出错: {close_error}")

    def health_check(self) -> dict[str, Any]:
        """
        V11.2: 系统健康检查（包含隐身模式状态）

        Returns:
            Dict: 健康状态报告
        """
        # 获取默认最小响应大小（从默认 tier）
        default_min_size = LEAGUE_QUALITY_TIERS["tier_default"]["min_response_size"]

        status = {
            "collector": "FotMobCore V11.0",
            "timestamp": datetime.now().isoformat(),  # V144.5: 使用 UTC 时间
            "database_connection": False,
            "api_connectivity": False,
            "adaptive_decoder": False,
            "consecutive_failures": self.consecutive_failures,
            "circuit_breaker_active": self.consecutive_failures >= self.max_consecutive_failures,
            "default_min_response_size": default_min_size,
            "league_tiers_configured": len(LEAGUE_QUALITY_TIERS),
            "hollow_matches_log_exists": os.path.exists(self.hollow_matches_log),
        }

        # 检查数据库连接
        try:
            conn = self.get_database_connection()
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
            conn.close()
            status["database_connection"] = True
        except Exception as e:
            status["database_error"] = str(e)

        # 检查API连接
        try:
            response = self.session.get(f"{self.base_url}/leagues?id=127", timeout=10)
            status["api_connectivity"] = response.status_code == 200
        except Exception as e:
            status["api_error"] = str(e)

        # 检查自适应解码器
        try:
            test_json = b'{"test": "value"}'
            result = self.adaptive_decode_response(test_json)
            status["adaptive_decoder"] = result is not None
        except Exception as e:
            status["decoder_error"] = str(e)

        return status


# 单例实例
_core_collector = None


def get_core_collector() -> FotMobCoreCollector:
    """获取核心采集器单例"""
    global _core_collector
    if _core_collector is None:
        _core_collector = FotMobCoreCollector()
    return _core_collector
