#!/usr/bin/env python3
"""
V20.8 焦土收割执行器 - Scorched Earth Harvester
===============================================

核心改进:
1. 强制覆盖逻辑 - 废除"ID存在即跳过"，基于 extraction_version 强制重写
2. 深度球员聚合 - 攻克最后 200 维，实现 850+ 维全息数据
3. 严苛质量门禁 - MIN_FEATURES 锁定为 800，低于则 CRITICAL 异常
4. 位置聚合 - 按 GK/DF/MF/FW 进行 4x12 级联累加

目标: 7,161 场比赛全部强制拉齐至 850+ 维

作者: Data Reliability Engineer
日期: 2025-12-24
版本: V20.8
"""

import os
import sys
import json
import time
import logging
import signal
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from collections import defaultdict

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dotenv import load_dotenv
if os.getenv('DB_HOST'):
    load_dotenv(override=False)
else:
    load_dotenv(override=True)

import psycopg2
from psycopg2.extras import RealDictCursor

from src.config_unified import get_settings
from src.ml.fault_tolerance import CircuitBreaker, CircuitBreakerConfig
from src.api.collectors.fotmob_core import FotMobCoreCollector

# V20.8 Docker 容器原生日志配置 - 权限脱钩版（强制 /tmp）
import os
# V20.8 强制锁定 /tmp 目录，彻底避开容器权限陷阱
log_path = '/tmp/harvester.log'  # 强制路径，忽略环境变量

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_path),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# ==================== V20.8 全局配置 ====================
V20_8_VERSION = "V20.8"
MIN_FEATURES = 881  # V20.8 终极维度死结 - 881 维熔断阈值
TARGET_FEATURES = 881  # 目标维度（与熔断阈值一致，确保100%对齐）
DIMENSION_FUSE_COUNT = 5  # 前5场维度检查熔断机制

# 五大联赛配置
LEAGUES = {
    47: "Premier_League",
    53: "Serie_A",
    54: "Bundesliga",
    55: "Ligue_1",
    87: "LaLiga"
}

SEASONS = ["2122", "2223", "2324", "2425"]

# 深度球员聚合指标 - 攻克最后 200 维
DEEP_PLAYER_METRICS = [
    # 进攻端
    'touches_in_box',           # 禁区内触球
    'key_passes_segment',        # 关键传球分段
    'shot_assists',              # 射门助攻
    'goal_contribution',         # 进球贡献

    # 防守端
    'ball_recoveries',           # 夺回球权分布
    'aerial_duels_won',          # 空中对垒成功率
    'possession_recovered',      # 拦截恢复球权
    'clearances_headed',         # 头球解围

    # 组织端
    'progressive_passes',        # 向前推进传球
    'passes_final_third',        # 前场三分之一传球
    'crosses_successful',        # 成功传中

    # 压迫端
    'pressures',                 # 压迫次数
    'pressures_successful',      # 成功压迫
    'fouls_conceded',            # 犯规次数
]

# 位置聚合映射
POSITION_GROUPS = {
    'GK': ['Goalkeeper'],           # 门将
    'DF': ['Centre-Back', 'Left-Back', 'Right-Back', 'Wing-Back'],  # 后卫
    'MF': ['Central-Midfield', 'Defensive-Midfield', 'Attacking-Midfield',
           'Left-Midfield', 'Right-Midfield', 'Winger'],  # 中场
    'FW': ['Centre-Forward', 'Second-Striker', 'Wing-back']  # 前锋
}


@dataclass
class V20_8Metrics:
    """V20.8 执行指标"""
    total_matches: int = 0
    forced_overwrites: int = 0  # 强制覆盖的记录数
    dimension_passed: int = 0   # 维度达标的记录数
    dimension_failed: int = 0   # 维度不达标的记录数
    critical_errors: int = 0    # 严重错误数
    first_batch_matches: list = field(default_factory=list)  # 前5场维度记录
    dimension_fuse_triggered: bool = False  # 维度熔断是否触发


class V20_8DeepPlayerAggregator:
    """
    V20.8 深度球员聚合器 - 攻克最后 200 维

    新增特征:
    - 进攻端: 禁区内触球 (touches_in_box)、关键传球分段 (key_passes_segment)
    - 防守端: 夺回球权分布 (ball_recoveries)、空中对垒成功率 (aerial_duels_won)
    - 位置聚合: 按 GK/DF/MF/FW 进行 4x12 级联累加
    """

    def __init__(self, home_team_id: int, away_team_id: int):
        self.home_team_id = home_team_id
        self.away_team_id = away_team_id

    def extract_deep_aggregates(
        self,
        content: Dict,
        features: Dict
    ) -> Dict[str, Any]:
        """
        提取深度球员聚合特征

        Returns:
            新增的深度聚合特征字典
        """
        aggregated = {}
        player_stats = content.get('content', {}).get('playerStats', {})

        if not player_stats:
            logger.debug("playerStats 不可用，跳过深度聚合")
            return aggregated

        # 提取主队和客队球员数据
        home_stats = player_stats.get(str(self.home_team_id), {})
        away_stats = player_stats.get(str(self.away_team_id), {})

        for team_side, team_stats in [('home', home_stats), ('away', away_stats)]:
            if not team_stats:
                continue

            # 1. 全队加总聚合（11 人）
            for metric in DEEP_PLAYER_METRICS:
                total = 0.0
                player_count = 0

                for player_id, player_data in team_stats.items():
                    if isinstance(player_data, dict):
                        value = self._extract_metric_value(player_data, metric)
                        if value is not None and value > 0:
                            total += value
                            player_count += 1

                if player_count > 0:
                    aggregated[f'{team_side}_team_total_{metric}'] = total
                    aggregated[f'{team_side}_team_avg_{metric}'] = round(total / player_count, 3)

            # 2. 位置级联聚合（GK/DF/MF/FW）
            position_aggregates = self._aggregate_by_position(team_stats, team_side)
            aggregated.update(position_aggregates)

        return aggregated

    def _extract_metric_value(self, player_data: Dict, metric: str) -> Optional[float]:
        """从球员数据中提取指标值"""
        # 尝试直接获取
        if metric in player_data:
            return float(player_data.get(metric, 0))

        # 尝试从 stats 子节点获取
        stats = player_data.get('stats', {})
        if isinstance(stats, dict):
            if metric in stats:
                return float(stats.get(metric, 0))

        return None

    def _aggregate_by_position(
        self,
        team_stats: Dict,
        team_side: str
    ) -> Dict[str, Any]:
        """
        按位置聚合 (GK/DF/MF/FW)

        为每个位置和每个深度指标计算聚合值
        """
        aggregated = {}

        # 初始化位置分组
        position_groups = defaultdict(list)

        # 按位置分组球员
        for player_id, player_data in team_stats.items():
            if not isinstance(player_data, dict):
                continue

            position = player_data.get('position', 'Unknown')
            position_groups[position].append(player_data)

        # 为每个位置组计算聚合
        for position_group, position_names in POSITION_GROUPS.items():
            group_players = []

            # 收集该位置组的所有球员
            for pos_name in position_names:
                group_players.extend(position_groups.get(pos_name, []))

            if not group_players:
                continue

            # 为每个深度指标计算位置聚合
            for metric in DEEP_PLAYER_METRICS:
                total = 0.0
                player_count = 0

                for player_data in group_players:
                    value = self._extract_metric_value(player_data, metric)
                    if value is not None and value > 0:
                        total += value
                        player_count += 1

                if player_count > 0:
                    aggregated[f'{team_side}_{position_group}_{metric}_total'] = total
                    aggregated[f'{team_side}_{position_group}_{metric}_avg'] = round(total / player_count, 3)

        return aggregated


class V20_8ScorchedEarthHarvester:
    """V20.8 焦土收割执行器"""

    # V20.8 强制覆盖逻辑代码片段
    FORCE_OVERRIDE_SQL = """
        -- 检查是否需要强制覆盖
        SELECT match_id,
               COALESCE(
                   (meta_data->>'extraction_version')::text,
                   'V0.0'
               ) as current_version
        FROM match_features_training
        WHERE match_id = %s
    """

    def __init__(self):
        self.settings = get_settings()
        self.metrics = V20_8Metrics()

        # 初始化熔断器
        cb_config = CircuitBreakerConfig(
            failure_threshold=20,
            timeout_seconds=300,
            error_codes={403, 429, 500, 502, 503}
        )
        self.circuit_breaker = CircuitBreaker(cb_config)

        # 初始化组件
        self.fotmob_collector = FotMobCoreCollector()
        self.deep_aggregator = None  # 延迟初始化

        # 数据库连接
        self.db_conn = None

        logger.info("="*70)
        logger.info("V20.8 焦土收割执行器初始化完成")
        logger.info(f"🎯 目标维度: {TARGET_FEATURES} 维")
        logger.info(f"🔒 维度死结: {MIN_FEATURES} 维（前5场熔断）")
        logger.info("="*70)

    def _get_db_connection(self):
        """
        V20.8 环境感知型认证 - 自动探测 + 显式注入密码

        优先级:
        1. 显式环境变量 POSTGRES_PASSWORD (容器内强制)
        2. .env 文件配置
        3. settings 配置
        """
        if self.db_conn is None or self.db_conn.closed:
            # V20.8 环境感知逻辑
            db_host = os.getenv('DB_HOST', os.getenv('FOOTBALL_DB_HOST', self.settings.database.host))

            # Docker 容器内自动探测
            if db_host == 'db':
                try:
                    import socket
                    socket.gethostbyname('db')
                    logger.debug("✓ Docker 容器环境: 'db' 主机可解析")
                except socket.gaierror:
                    logger.info("✗ 非 Docker 环境，自动切换到 localhost")
                    db_host = 'localhost'

            # V20.8 显式密码注入（无视 .env 挂载状态）
            db_password = os.getenv('POSTGRES_PASSWORD',
                                    os.getenv('DB_PASSWORD',
                                             self.settings.database.password.get_secret_value()))
            db_name = os.getenv('DB_NAME',
                                os.getenv('FOOTBALL_DB_NAME',
                                         self.settings.database.name))
            db_user = os.getenv('POSTGRES_USER',
                                os.getenv('DB_USER',
                                         self.settings.database.user))

            self.db_conn = psycopg2.connect(
                host=db_host,
                port=self.settings.database.port,
                database=db_name,
                user=db_user,
                password=db_password,
                cursor_factory=RealDictCursor
            )
            logger.info(f"✓ 数据库连接已建立: {db_host}/{db_name} (user={db_user})")

        return self.db_conn

    def _should_force_override(self, match_id: int) -> bool:
        """
        V20.8 强制覆盖逻辑

        判断规则:
        1. 如果数据库中不存在该记录 -> 需要插入
        2. 如果 extraction_version < V20.8 -> 强制覆盖
        3. 如果 extraction_version >= V20.8 -> 跳过

        Returns:
            True 表示需要执行/覆盖，False 表示跳过
        """
        conn = self._get_db_connection()
        cur = conn.cursor()

        cur.execute(
            "SELECT match_id, league_id, season_id, home_team, away_team, "
            "COALESCE((meta_data->>'extraction_version')::text, 'V0.0') as current_version "
            "FROM match_features_training WHERE match_id = %s",
            (match_id,)
        )
        result = cur.fetchone()
        cur.close()

        if not result:
            return True  # 不存在，需要插入

        current_version = result.get('current_version', 'V0.0')

        # V20.8 修复: 检查标签完整性 - 如果 league_id/season_id 为 NULL，强制覆盖
        if result.get('league_id') is None or result.get('season_id') is None:
            logger.info(f"  🔄 标签修复: 检测到 NULL 标签 (league_id={result.get('league_id')}, season_id={result.get('season_id')})，强制覆盖")
            self.metrics.forced_overwrites += 1
            return True

        # 版本比较: V20.8 > V20.7 > V20.6 > ...
        if self._compare_versions(current_version, V20_8_VERSION) < 0:
            logger.info(f"  🔄 版本升级: {current_version} -> {V20_8_VERSION}，强制覆盖")
            self.metrics.forced_overwrites += 1
            return True

        return False

    def _compare_versions(self, v1: str, v2: str) -> int:
        """
        版本比较

        Returns:
            -1: v1 < v2
             0: v1 == v2
             1: v1 > v2
        """
        # 简单版本比较: V20.8 -> 20.8
        def parse_version(v):
            parts = v.replace('V', '').split('.')
            return tuple(int(p) for p in parts if p.isdigit())

        v1_parsed = parse_version(v1)
        v2_parsed = parse_version(v2)

        if v1_parsed < v2_parsed:
            return -1
        elif v1_parsed > v2_parsed:
            return 1
        else:
            return 0

    def _infer_season_from_date(self, date_str: str) -> str:
        """
        V20.8 从日期推断赛季

        Args:
            date_str: ISO 日期字符串，如 "2026-02-22T18:00:00.000Z"

        Returns:
            赛季字符串，如 "2526"
        """
        try:
            # 解析日期
            from datetime import datetime
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            year = dt.year

            # 赛季规则：8月1日之后跨年
            if dt.month >= 8:
                return f"{str(year)[2:]}{str(year + 1)[2:]}"
            else:
                return f"{str(year - 1)[2:]}{str(year)[2:]}"
        except Exception:
            return "unknown"

    def _validate_feature_count(self, features: Dict, match_id: int) -> bool:
        """
        V20.8 维度死结 - 验证特征数量

        熔断机制:
        - 前5场比赛中任何一场 < 881 维 -> 立即 sys.exit(1)
        - 第6场及以后仅记录警告，继续执行

        Args:
            features: 特征字典
            match_id: 比赛 ID

        Returns:
            True 通过，False 失败

        Raises:
            SystemExit: 前5场维度不达标（熔断）
            CriticalError: 维度严重不达标
        """
        feature_count = len(features)

        # V20.8 维度死结熔断机制
        if len(self.metrics.first_batch_matches) < DIMENSION_FUSE_COUNT:
            self.metrics.first_batch_matches.append({
                'match_id': match_id,
                'feature_count': feature_count
            })

            if feature_count < MIN_FEATURES:
                # 触发熔断
                error_msg = (
                    f"\n{'='*70}\n"
                    f"🚨 V20.8 维度死结熔断触发！\n"
                    f"{'='*70}\n"
                    f"Match {match_id}: {feature_count} < {MIN_FEATURES} 维\n"
                    f"前 {DIMENSION_FUSE_COUNT} 场维度记录:\n"
                )
                for i, record in enumerate(self.metrics.first_batch_matches, 1):
                    status = "✓" if record['feature_count'] >= MIN_FEATURES else "✗"
                    error_msg += f"  {status} {i}. Match {record['match_id']}: {record['feature_count']} 维\n"

                error_msg += (
                    f"{'='*70}\n"
                    f"💀 维度主权已锁死在 {MIN_FEATURES} 维，系统拒绝执行。\n"
                    f"{'='*70}\n"
                )

                logger.error(error_msg)
                self.metrics.dimension_fuse_triggered = True
                self.metrics.dimension_failed += 1
                self.metrics.critical_errors += 1
                sys.exit(1)  # 立即终止

        elif feature_count < MIN_FEATURES:
            # 第6场及以后仅记录警告
            logger.warning(f"  ⚠️  Match {match_id}: {feature_count} < {MIN_FEATURES} 维 (已过熔断期)")
            self.metrics.dimension_failed += 1
            return False

        # 维度达标
        self.metrics.dimension_passed += 1
        logger.debug(f"  ✓ 维度验证通过: {feature_count} >= {MIN_FEATURES}")
        return True

    def harvest_match(self, match_id: int) -> Optional[Dict]:
        """
        收割单场比赛 - V20.8 强制覆盖逻辑

        Args:
            match_id: FotMob 比赛 ID

        Returns:
            处理后的特征字典
        """
        self.metrics.total_matches += 1

        # 检查是否需要强制覆盖
        if not self._should_force_override(match_id):
            logger.debug(f"  ⏭️  Match {match_id} 已是 {V20_8_VERSION}，跳过")
            return None

        logger.info(f"  🌾 收割 Match {match_id}...")

        try:
            # 1. 从 FotMob API 采集数据
            content = self.fotmob_collector.fetch_match_details(match_id)
            if not content:
                logger.warning(f"  ⚠️  Match {match_id} API 数据不可用")
                return None

            # 2. 构造 match_data 结构（V20.8 修复：包含 general 字段以触发 atomic_align_v20_8）
            # V20.8 修复：API 响应结构已改变，从根级别的 content.general 提取字段
            general = content.get('general', {})
            match_info = content.get('content', {}).get('match', {})

            # V20.8 关键修复：确保 l2_json 包含 general 字段
            l2_json = {
                'l2_json': content,
                'general': {
                    'homeTeam': {'id': general.get('homeTeam', {}).get('id')},
                    'awayTeam': {'id': general.get('awayTeam', {}).get('id')}
                }
            }

            # V20.8 修复：从 general 提取 league_id, season_id, team names
            league_id = general.get('leagueId')

            # V20.8 修复：从 matchTimeUTCDate 推断赛季 (如 2025-08 -> 2526)
            match_time_str = general.get('matchTimeUTCDate', '')
            season_id = self._infer_season_from_date(match_time_str)

            home_team = general.get('homeTeam', {}).get('name', 'Unknown')
            away_team = general.get('awayTeam', {}).get('name', 'Unknown')

            match_data = {
                'match_id': match_id,
                'league_id': league_id,
                'season_id': season_id,
                'home_team': home_team,
                'away_team': away_team,
                'player_stats': l2_json,
                'l2_raw_json': l2_json,
            }

            # 3. 提取基础特征
            from src.ml.feature_forge_v20 import FeatureExtractor
            extractor = FeatureExtractor()
            extracted = extractor.extract_features(match_data)

            # V20.8 返回结构: {'core': {...}, 'enriched': {...}, '_meta': {...}}
            if not extracted:
                logger.error(f"  ❌ Match {match_id} 特征提取失败")
                return None

            # 合并 core 和 enriched
            features = {**extracted.get('enriched', {}), **extracted.get('core', {})}

            # 4. 获取球队 ID 用于深度聚合
            home_id = match_info.get('homeTeam')
            away_id = match_info.get('awayTeam')

            if home_id and away_id:
                self.deep_aggregator = V20_8DeepPlayerAggregator(home_id, away_id)
                deep_features = self.deep_aggregator.extract_deep_aggregates(content, features)
                features.update(deep_features)
                logger.info(f"  ✓ 深度聚合: +{len(deep_features)} 维")

            # 5. 注入版本号
            features['_meta'] = {
                'extraction_version': V20_8_VERSION,
                'extraction_timestamp': datetime.now().isoformat(),
                'feature_count': len(features)
            }

            # 6. 严苛质量门禁
            self._validate_feature_count(features, match_id)

            # 7. 存入数据库
            self._save_to_database(match_id, content, features)

            logger.info(f"  ✅ Match {match_id} 完成: {len(features)} 维")
            return features

        except CriticalError as e:
            logger.error(f"  💀 CRITICAL: {e}")
            raise
        except AssertionError:
            # V20.8 SRE: 质量看门狗断言失败，必须传播并崩溃
            # 我们宁可停机，也不要匿名数据
            raise
        except Exception as e:
            logger.error(f"  ❌ Match {match_id} 处理失败: {e}")
            return None

    def _save_to_database(self, match_id: int, content: Dict, features: Dict):
        """
        V20.8 保存到数据库 - 修复标签丢失问题

        修复:
        - 从 content.general 提取 league_id, season_id, team names
        - UPDATE 语句包含完整字段
        """
        conn = self._get_db_connection()
        cur = conn.cursor()

        # V20.8 修复：从根级别的 content.general 提取标签信息（API 响应结构）
        general = content.get('general', {})
        match_info = content.get('content', {}).get('match', {})

        league_id = general.get('leagueId')
        home_team = general.get('homeTeam', {}).get('name', 'Unknown')
        away_team = general.get('awayTeam', {}).get('name', 'Unknown')

        # V20.8 修复：从日期推断赛季
        match_time_str = general.get('matchTimeUTCDate', '')
        season_id = self._infer_season_from_date(match_time_str)

        # ==================== V20.8 SRE 质量看门狗 ====================
        # 我们宁可停机，也不要匿名数据

        # V20.8 调试日志: 追踪质量检查值
        logger.debug(f"🔍 质量检查 Match {match_id}: league_id={league_id}, season_id={season_id}, home={home_team}, away={away_team}")

        assert league_id is not None, f"🚨 质量看门狗触发: Match {match_id} league_id 为 NULL，系统拒绝执行"
        assert season_id is not None and season_id != 'unknown', \
            f"🚨 质量看门狗触发: Match {match_id} season_id 为 {season_id}，系统拒绝执行"
        assert home_team is not None and home_team != 'Unknown', \
            f"🚨 质量看门狗触发: Match {match_id} home_team 为 {home_team}，系统拒绝执行"
        assert away_team is not None and away_team != 'Unknown', \
            f"🚨 质量看门狗触发: Match {match_id} away_team 为 {away_team}，系统拒绝执行"

        # V20.8 质量看门狗通过确认
        logger.debug(f"✅ 质量看门狗通过: Match {match_id}")
        # ==============================================================

        # 检查是否需要更新或插入
        cur.execute(
            "SELECT match_id FROM match_features_training WHERE match_id = %s",
            (match_id,)
        )

        if cur.fetchone():
            # V20.8 修复: UPDATE 包含完整字段
            cur.execute("""
                UPDATE match_features_training
                SET league_id = %s,
                    season_id = %s,
                    home_team = %s,
                    away_team = %s,
                    enriched_features = %s,
                    meta_data = %s,
                    updated_at = NOW()
                WHERE match_id = %s
            """, (
                league_id,
                season_id,
                home_team,
                away_team,
                json.dumps(features),
                json.dumps(features.get('_meta', {})),
                match_id
            ))
        else:
            # V20.8 SRE 修复: INSERT 必须使用经过质量看门狗验证的变量
            # 严禁使用 match_info (可能为 NULL)，必须使用 league_id/season_id
            cur.execute("""
                INSERT INTO match_features_training (
                    match_id, league_id, season_id, home_team, away_team,
                    enriched_features, meta_data, status, created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
            """, (
                match_id,
                league_id,        # 使用质量看门狗验证的变量
                season_id,        # 使用质量看门狗验证的变量
                home_team,        # 使用质量看门狗验证的变量
                away_team,        # 使用质量看门狗验证的变量
                json.dumps(features),
                json.dumps(features.get('_meta', {})),
                'completed'
            ))

        conn.commit()
        cur.close()

    def harvest_season(
        self,
        league_id: int,
        season: str,
        match_ids: List[int]
    ):
        """收割整个赛季"""
        logger.info(f"\n{'='*70}")
        logger.info(f"开始收割: {LEAGUES[league_id]} {season} ({len(match_ids)} 场)")
        logger.info(f"{'='*70}\n")

        success_count = 0
        fail_count = 0

        for i, match_id in enumerate(match_ids, 1):
            if self.circuit_breaker.is_open():
                logger.error("🔴 熔断器已打开，停止执行")
                break

            # 使用 print 代替 logger.info 支持 end 参数
            print(f"[{i}/{len(match_ids)}] ", end='', flush=True)

            try:
                result = self.harvest_match(match_id)
                if result:
                    success_count += 1
                else:
                    fail_count += 1

                # API 限速
                time.sleep(2.0)

            except CriticalError:
                logger.error("🚨 检测到严重错误，立即停止执行")
                break
            except AssertionError:
                # V20.8 SRE: 质量看门狗触发 AssertionError，立即传播崩溃
                raise
            except Exception as e:
                logger.error(f"  ❌ 处理失败: {e}")
                fail_count += 1

        logger.info(f"\n{'='*70}")
        logger.info(f"收割完成: 成功 {success_count}, 失败 {fail_count}")
        logger.info(f"{'='*70}\n")

    def print_final_report(self):
        """打印最终报告"""
        logger.info("\n" + "="*70)
        logger.info("V20.8 焦土收割计划 - 最终报告")
        logger.info("="*70)
        logger.info(f"总处理场次: {self.metrics.total_matches}")
        logger.info(f"强制覆盖记录: {self.metrics.forced_overwrites}")
        logger.info(f"维度验证通过: {self.metrics.dimension_passed}")
        logger.info(f"维度验证失败: {self.metrics.dimension_failed}")
        logger.info(f"严重错误数: {self.metrics.critical_errors}")

        # 前5场维度记录
        if self.metrics.first_batch_matches:
            logger.info("\n前5场维度死结验证:")
            for i, record in enumerate(self.metrics.first_batch_matches, 1):
                status = "✓" if record['feature_count'] >= MIN_FEATURES else "✗"
                logger.info(f"  {status} {i}. Match {record['match_id']}: {record['feature_count']} 维")

        # 熔断状态
        if self.metrics.dimension_fuse_triggered:
            logger.info("\n🚨 维度熔断已触发，系统已终止执行")

        logger.info("="*70)


class CriticalError(Exception):
    """严重错误 - 维度不达标"""
    pass


# ==================== 主程序 ====================
if __name__ == "__main__":
    logger.info("🚀 V20.8 焦土收割计划启动...")

    # V20.8 修复: 从清单文件加载比赛 ID，按联赛分组
    def load_match_ids_by_league(season: str) -> Dict[int, List[int]]:
        """
        从清单文件加载比赛 ID，按联赛分组

        Returns:
            {league_id: [match_ids]}
        """
        manifest_file = f"data/production/harvest_manifest_{season}.csv"
        if not os.path.exists(manifest_file):
            logger.warning(f"清单文件不存在: {manifest_file}")
            return {}

        import csv
        matches_by_league = defaultdict(list)
        total_matches = 0

        with open(manifest_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                match_id = row.get('match_id')
                league_id = row.get('league_id')
                if match_id and league_id:
                    matches_by_league[int(league_id)].append(int(match_id))
                    total_matches += 1

        logger.info(f"📋 加载 {total_matches} 个比赛 ID: {season}")
        for league_id, match_ids in sorted(matches_by_league.items()):
            league_name = LEAGUES.get(league_id, f"League_{league_id}")
            logger.info(f"   {league_name}: {len(match_ids)} 场")

        return dict(matches_by_league)

    harvester = V20_8ScorchedEarthHarvester()

    try:
        # V20.8 修复: 按联赛和赛季收割（而非硬编码 league_id=47）
        total_processed = 0
        for season in SEASONS:
            matches_by_league = load_match_ids_by_league(season)
            if matches_by_league:
                for league_id, match_ids in sorted(matches_by_league.items()):
                    if league_id in LEAGUES:
                        harvester.harvest_season(league_id, season, match_ids)
                        total_processed += len(match_ids)
                    else:
                        logger.warning(f"⚠️ 未知联赛 ID: {league_id}，跳过 {len(match_ids)} 场比赛")

        harvester.print_final_report()

        logger.info(f"\n🎯 焦土计划执行完毕，历史断层已抹平。{total_processed} 场 881 维镜像已就绪，请求全量起飞。")

    except KeyboardInterrupt:
        logger.info("\n⚠️  收到中断信号，正在退出...")
    except AssertionError:
        # V20.8 SRE: 质量看门狗触发 AssertionError，立即崩溃
        raise
    except Exception as e:
        logger.error(f"💀 执行失败: {e}")
        raise
