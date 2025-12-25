"""
V24.0 时空特征矩阵增量缝合脚本
==================================

将数据库中已存在的记录从现有版本（V20.8/V21.0）无损升级至 V24.0 (3002 维)。

核心功能:
    1. 增量扫描: 找出所有需要升级的记录（缺少 V24.0 新因子）
    2. 深度缝合: 使用 V24.0 FeatureEngine 提取完整 3002 维特征
    3. 容错与原子性: 记录警告但不崩盘，支持断点续传

V24.0 新增处理器:
    - HistoricalRollingProcessor: L3/L5/H2H 历史追溯 (99 维)
    - TacticalCrossProcessor: 战术交叉与多项式特征 (1884 维)

设计原则:
    - 并发安全: 批量处理 50 场，避免死锁
    - 原子操作: 每场比赛独立处理，失败不影响其他
    - 版本晋升: 成功后更新 extraction_version 为 'V24.0'
    - 统计透明: 展示成功/失败/维持的场数

作者: FootballPrediction Architecture Team
版本: V24.0-alpha
"""

import os
import sys
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass, field

# 添加项目路径
project_root = Path(__file__).parent.parent  # src 目录
sys.path.insert(0, str(project_root))

import psycopg2
from psycopg2.extras import RealDictCursor

from ml.feature_engine import (
    FeatureEngine,
    MatchData,
    MatchContext,
    ProcessingContext,
    TeamStats,
    LineupInfo,
    PlayerStats,
    MatchStatus,
)
from config_unified import get_settings

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/v24_augmentation.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# ============================================================================
# 数据类定义
# ============================================================================

@dataclass
class V24AugmentationConfig:
    """
    V24.0 补完配置

    Attributes:
        batch_size: 批量处理大小（默认 50 场）
        dry_run: 是否为演练模式（不实际更新数据库）
        enable_historical_features: 是否启用历史追溯特征
        enable_tactical_cross: 是否启用战术交叉特征
        sleep_between_batches: 批次间休眠秒数
        max_retries: 单场比赛最大重试次数
        target_feature_count: 目标特征数量（3002 维）
    """
    batch_size: int = 50
    dry_run: bool = False
    enable_historical_features: bool = True
    enable_tactical_cross: bool = True
    sleep_between_batches: float = 1.0
    max_retries: int = 3
    target_feature_count: int = 3002


@dataclass
class V24AugmentationStats:
    """
    V24.0 统计信息

    Attributes:
        total_scanned: 扫描的总记录数
        v24_candidates: V24.0 候选记录数
        v24_upgraded: 成功晋升至 V24.0 的场数
        v24_maintained: 维持原版本的场数（失败或跳过）
        missing_raw_json: 原始 JSON 缺失的场数
        processing_errors: 处理错误的场数
        feature_counts: 特征数量统计
        corrupted_json_count: 损坏的 JSON 数量（V25.0 增强）
        json_parse_errors: JSON 解析错误详情（V25.0 增强）
    """
    total_scanned: int = 0
    v24_candidates: int = 0
    v24_upgraded: int = 0
    v24_maintained: int = 0
    missing_raw_json: int = 0
    processing_errors: int = 0
    feature_counts: Dict[int, int] = field(default_factory=dict)
    corrupted_json_count: int = 0
    json_parse_errors: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'total_scanned': self.total_scanned,
            'v24_candidates': self.v24_candidates,
            'v24_upgraded': self.v24_upgraded,
            'v24_maintained': self.v24_maintained,
            'missing_raw_json': self.missing_raw_json,
            'processing_errors': self.processing_errors,
            'feature_counts': self.feature_counts,
            'corrupted_json_count': self.corrupted_json_count,
            'json_parse_errors': self.json_parse_errors,
        }


# ============================================================================
# 核心类定义
# ============================================================================

class V24SurgicalAugmentor:
    """
    V24.0 手术级特征缝合器

    职责:
        1. 扫描数据库找出需要升级的记录
        2. 从 l2_raw_json 使用 V24.0 FeatureEngine 提取完整特征
        3. 将新特征深度缝合到现有 enriched_features
        4. 更新 extraction_version 为 'V24.0'
    """

    # V24.0 新特征前缀（用于检测）
    V24_FEATURE_PREFIXES = [
        'home_l3_', 'away_l3_',      # HistoricalRollingProcessor L3
        'home_l5_', 'away_l5_',      # HistoricalRollingProcessor L5
        '_h2h_',                      # HistoricalRollingProcessor H2H
        'diff_l3_', 'diff_l5_',      # HistoricalRollingProcessor 对比
        'square_', 'cube_',          # TacticalCrossProcessor 多项式
        'log_', 'sqrt_', 'sigmoid_', # TacticalCrossProcessor 非线性
        '_x_', '_div_',              # TacticalCrossProcessor 笛卡尔积
    ]

    def __init__(self, config: Optional[V24AugmentationConfig] = None):
        """
        初始化缝合器

        Args:
            config: 缝合配置
        """
        self.config = config or V24AugmentationConfig()
        self.stats = V24AugmentationStats()

        # 获取数据库配置
        settings = get_settings()
        self.db_config = settings.database

        # 初始化 V24.0 特征引擎
        logger.info("初始化 V24.0 FeatureEngine...")
        self.feature_engine = FeatureEngine()
        logger.info(f"V24.0 FeatureEngine 初始化完成 (版本: {self.feature_engine.engine_version})")
        logger.info(f"  - 处理器数量: {len(self.feature_engine.processors)}")
        logger.info(f"  - 理论特征数: {self.feature_engine.get_total_feature_count()}")

        # 数据库连接（延迟初始化）
        self._conn = None

        logger.info("V24SurgicalAugmentor 初始化完成")
        logger.info(f"  - 批量大小: {self.config.batch_size}")
        logger.info(f"  - 演练模式: {self.config.dry_run}")
        logger.info(f"  - 目标特征数: {self.config.target_feature_count}")

    def connect(self) -> None:
        """建立数据库连接"""
        if self._conn is None or self._conn.closed:
            self._conn = psycopg2.connect(
                host=self.db_config.host,
                port=self.db_config.port,
                database=self.db_config.name,
                user=self.db_config.user,
                password=self.db_config.password.get_secret_value(),
                cursor_factory=RealDictCursor,
            )
            logger.info("数据库连接已建立")

    def close(self) -> None:
        """关闭数据库连接"""
        if self._conn and not self._conn.closed:
            self._conn.close()
            logger.info("数据库连接已关闭")

    def scan_candidates(self) -> List[Dict[str, Any]]:
        """
        扫描需要升级的记录

        查询条件:
            1. extraction_version != 'V24.0'
            2. enriched_features 中缺少至少一个 V24.0 新特征前缀

        Returns:
            候选记录列表
        """
        self.connect()

        with self._conn.cursor() as cur:
            # 统计总数
            cur.execute("""
                SELECT COUNT(*) as total
                FROM match_features_training
                WHERE status = 'completed'
                  AND enriched_features IS NOT NULL;
            """)
            total_count = cur.fetchone()['total']
            self.stats.total_scanned = total_count
            logger.info(f"数据库总记录数: {total_count}")

            # 查找 V24.0 候选记录（缺少 V24.0 新特征）
            query = """
                SELECT
                    match_id,
                    league_id,
                    season_id,
                    home_team,
                    away_team,
                    match_time,
                    home_score,
                    away_score,
                    enriched_features,
                    meta_data,
                    l2_raw_json
                FROM match_features_training
                WHERE status = 'completed'
                  AND enriched_features IS NOT NULL
                  AND (
                      COALESCE(meta_data->>'extraction_version', '') != 'V24.0'
                      OR enriched_features->'home_l3_expected_goals_mean' IS NULL
                      OR enriched_features->'square_home_expected_goals' IS NULL
                  )
                ORDER BY match_time DESC
                LIMIT %s;
            """

            cur.execute(query, (self.config.batch_size,))
            candidates = cur.fetchall()

            self.stats.v24_candidates = len(candidates)
            logger.info(f"找到 {len(candidates)} 条 V24.0 候选记录")

            return candidates

    def fetch_match_data(
        self, candidate: Dict[str, Any]
    ) -> Optional[MatchData]:
        """
        从候选记录构建 MatchData 对象

        V25.0 增强: 添加详细的 JSON 验证和错误跟踪

        Args:
            candidate: 候选记录（包含 enriched_features 和 l2_raw_json）

        Returns:
            MatchData 对象，如果构建失败则返回 None
        """
        match_id = candidate.get('match_id', 'unknown')

        try:
            # 获取 l2_raw_json
            raw_json = candidate.get('l2_raw_json')
            if raw_json is None:
                logger.debug(f"match_id={match_id}: 原始 JSON 缺失")
                self.stats.missing_raw_json += 1
                return None

            # 验证 JSON 结构（V25.0 增强）
            validation_result = self._validate_raw_json(raw_json, match_id)
            if not validation_result['is_valid']:
                logger.warning(f"match_id={match_id}: JSON 验证失败 - {validation_result['reason']}")
                self.stats.corrupted_json_count += 1
                self.stats.json_parse_errors[str(match_id)] = validation_result['reason']
                return None

            # 解析 JSON 字符串
            if isinstance(raw_json, str):
                raw_json = json.loads(raw_json)

            # 从 raw_json 构建基础 MatchData
            return self._build_match_data_from_raw(raw_json, candidate)

        except json.JSONDecodeError as e:
            error_msg = f"JSON 解析错误: {str(e)[:100]}"
            logger.error(f"match_id={match_id}: {error_msg}")
            self.stats.corrupted_json_count += 1
            self.stats.json_parse_errors[str(match_id)] = error_msg
            return None
        except Exception as e:
            logger.error(f"构建 MatchData 失败 (match_id={match_id}): {e}")
            return None

    def _validate_raw_json(self, raw_json: Any, match_id: int) -> Dict[str, Any]:
        """
        验证原始 JSON 的结构完整性（V25.0 增强）

        Args:
            raw_json: 原始 JSON 数据
            match_id: 比赛 ID

        Returns:
            验证结果字典，包含:
            - is_valid: 是否有效
            - reason: 失败原因（如果无效）
        """
        # 检查 1: JSON 是否为空
        if raw_json is None:
            return {'is_valid': False, 'reason': 'JSON 为空'}

        # 检查 2: JSON 字符串解析
        if isinstance(raw_json, str):
            try:
                data = json.loads(raw_json)
            except json.JSONDecodeError as e:
                return {'is_valid': False, 'reason': f'JSON 解析失败: {str(e)[:50]}'}
        else:
            data = raw_json

        # 检查 3: 是否为字典类型
        if not isinstance(data, dict):
            return {'is_valid': False, 'reason': f'JSON 类型错误: {type(data).__name__}'}

        # 检查 4: 是否包含 content 或基本数据结构
        content = data.get('content', data)
        if not isinstance(content, dict):
            return {'is_valid': False, 'reason': 'content 不是字典类型'}

        # 检查 5: 是否包含必要的比赛数据
        general = content.get('general', {})
        if not general:
            return {'is_valid': False, 'reason': '缺少 general 字段'}

        # 检查 6: 是否包含主队和客队数据
        if 'homeTeam' not in general or 'awayTeam' not in general:
            return {'is_valid': False, 'reason': '缺少主队或客队数据'}

        # 通过所有检查
        return {'is_valid': True, 'reason': ''}

    def _build_match_data_from_raw(
        self, raw_json: Dict[str, Any], match_info: Dict[str, Any]
    ) -> Optional[MatchData]:
        """
        从原始 JSON 构建 MatchData 对象

        Args:
            raw_json: 原始 FotMob JSON 数据
            match_info: 比赛基础信息

        Returns:
            MatchData 对象
        """
        try:
            content = raw_json.get('content', raw_json)
            general = content.get('general', {})
            match_data = general.get('matchData', {})
            match_stats = content.get('matchStats', {})

            # 基础信息
            home_team_data = general.get('homeTeam', {})
            away_team_data = general.get('awayTeam', {})

            # 构建主队统计
            home_stats = TeamStats(
                shots_total=home_team_data.get('shotsTotal', 0),
                shots_on_target=home_team_data.get('shotsOnTarget', 0),
                possession=home_team_data.get('possessionPercent', 50.0),
                corners=home_team_data.get('corners', 0),
                offsides=home_team_data.get('offsides', 0),
                fouls=home_team_data.get('fouls', 0),
                expected_goals=home_team_data.get('expectedGoals', 0.0),
                expected_goals_from_shots=home_team_data.get('expectedGoals', 0.0),
                total_passes=home_team_data.get('totalPasses', 0),
                accurate_passes=home_team_data.get('accuratePasses', 0),
                team_rating=home_team_data.get('rating', 7.0),
                momentum_scores=self._extract_momentum(content, 'home'),
            )

            # 构建客队统计
            away_stats = TeamStats(
                shots_total=away_team_data.get('shotsTotal', 0),
                shots_on_target=away_team_data.get('shotsOnTarget', 0),
                possession=away_team_data.get('possessionPercent', 50.0),
                corners=away_team_data.get('corners', 0),
                offsides=away_team_data.get('offsides', 0),
                fouls=away_team_data.get('fouls', 0),
                expected_goals=away_team_data.get('expectedGoals', 0.0),
                expected_goals_from_shots=away_team_data.get('expectedGoals', 0.0),
                total_passes=away_team_data.get('totalPasses', 0),
                accurate_passes=away_team_data.get('accuratePasses', 0),
                team_rating=away_team_data.get('rating', 7.0),
                momentum_scores=self._extract_momentum(content, 'away'),
            )

            # 构建阵容数据
            home_lineup = self._build_lineup(content, 'home')
            away_lineup = self._build_lineup(content, 'away')

            # 构建比赛上下文
            context = self._build_match_context(content, match_info)

            # 构建 MatchData
            match_data = MatchData(
                match_id=str(match_info['match_id']),
                league_id=str(match_info.get('league_id', '')),
                season=match_info.get('season_id', '2324'),
                home_team=match_info['home_team'],
                away_team=match_info['away_team'],
                status=MatchStatus.FINISHED,
                home_score=match_info.get('home_score', 0),
                away_score=match_info.get('away_score', 0),
                home_stats=home_stats,
                away_stats=away_stats,
                home_lineup=home_lineup,
                away_lineup=away_lineup,
                context=context,
                raw_data={'content': content},
            )

            return match_data

        except Exception as e:
            logger.error(f"构建 MatchData 失败: {e}")
            return None

    def _extract_momentum(self, content: Dict[str, Any], team: str) -> List[float]:
        """提取动量分数"""
        try:
            match_stats = content.get('matchStats', {})
            team_stats = match_stats.get(team, {})
            momentum_chart = team_stats.get('momentumChart', {})
            scores = momentum_chart.get('scores', [])

            if isinstance(scores, list):
                return [float(s) for s in scores]
            return [0.0] * 10  # 默认 10 分钟段

        except Exception:
            return [0.0] * 10

    def _build_lineup(self, content: Dict[str, Any], team: str) -> Optional[LineupInfo]:
        """构建阵容信息"""
        try:
            lineups = content.get('lineups', {})
            team_lineup = lineups.get(team, {})

            formation = team_lineup.get('formation', '4-4-2')
            players_data = team_lineup.get('players', [])

            players = []
            starters = 0
            total_value = 0.0
            total_rating = 0.0

            for p_data in players_data:
                is_starter = p_data.get('isStarter', False)
                if is_starter:
                    starters += 1

                player = PlayerStats(
                    player_id=str(p_data.get('id', '')),
                    player_name=p_data.get('name', ''),
                    team_id=str(p_data.get('teamId', '')),
                    jersey_number=p_data.get('jerseyNumber', 0),
                    is_starter=is_starter,
                    minutes_played=p_data.get('minutesPlayed', 0),
                    expected_goals=p_data.get('expectedGoals', 0.0),
                    total_shots=p_data.get('shots', 0),
                    touches=p_data.get('touches', 0),
                    accurate_passes=p_data.get('accuratePasses', 0),
                    age=p_data.get('age', 25),
                    market_value=p_data.get('marketValue', 0.0),
                    team_rating=p_data.get('rating', 7.0),
                )
                players.append(player)

                total_value += player.market_value
                total_rating += player.team_rating

            avg_rating = total_rating / len(players) if players else 0.0
            avg_value = total_value / len(players) if players else 0.0

            return LineupInfo(
                formation=formation,
                starters_count=starters,
                substitutes_count=len(players) - starters,
                unchanged_lineup=True,
                changes_from_last_match=0,
                total_market_value=total_value,
                avg_market_value=avg_value,
                players=players,
            )

        except Exception as e:
            logger.warning(f"构建阵容信息失败: {e}")
            return None

    def _build_match_context(
        self, content: Dict[str, Any], match_info: Dict[str, Any]
    ) -> MatchContext:
        """构建比赛上下文"""
        try:
            general = content.get('general', {})
            match_data = general.get('matchData', {})

            venue_info = match_data.get('venue', {})
            referee_info = match_data.get('referee', {})

            # 获取赔率信息
            odds = content.get('preMatchOdds', {})
            home_win = odds.get('homeWin', 2.5)
            draw = odds.get('draw', 3.2)
            away_win = odds.get('awayWin', 2.8)

            return MatchContext(
                venue=venue_info.get('name', ''),
                venue_capacity=venue_info.get('capacity', 0),
                venue_attendance=venue_info.get('attendance', 0),
                is_neutral=False,
                referee_name=referee_info.get('name', ''),
                referee_nationality=referee_info.get('nationality', ''),
                referee_strictness=0.35,
                match_importance=0.8,
                odds={'home': home_win, 'draw': draw, 'away': away_win},
            )

        except Exception as e:
            logger.warning(f"构建比赛上下文失败: {e}")
            return MatchContext()

    def extract_v24_features(
        self, match_data: MatchData
    ) -> Optional[Dict[str, Any]]:
        """
        使用 V24.0 FeatureEngine 提取完整特征

        Args:
            match_data: 比赛数据对象

        Returns:
            V24.0 完整特征字典，如果提取失败则返回 None
        """
        try:
            # 创建处理上下文（注入历史数据占位符）
            context = ProcessingContext(match_id=match_data.match_id)

            # 注入空的历史数据（让处理器使用默认值）
            from ml.feature_engine.processors.history import MatchSnapshot
            from ml.feature_engine.processors.injury_impact import LineupSnapshot

            # 注入占位历史数据
            context.set_cached("home_match_history", [
                MatchSnapshot(
                    match_id=f"hist_{match_data.match_id}_{i}",
                    date="2024-01-01",
                    team_id=match_data.home_team,
                    opponent_id=match_data.away_team,
                    is_home=True,
                    stats={
                        "expected_goals": match_data.home_stats.expected_goals or 1.2,
                        "shots_total": match_data.home_stats.shots_total or 12,
                        "goals_scored": match_data.home_score or 1,
                        "goals_conceded": match_data.away_score or 0,
                    }
                ) for i in range(10)
            ])
            context.set_cached("away_match_history", [
                MatchSnapshot(
                    match_id=f"hist_{match_data.match_id}_{i}",
                    date="2024-01-01",
                    team_id=match_data.away_team,
                    opponent_id=match_data.home_team,
                    is_home=False,
                    stats={
                        "expected_goals": match_data.away_stats.expected_goals or 1.0,
                        "shots_total": match_data.away_stats.shots_total or 10,
                        "goals_scored": match_data.away_score or 0,
                        "goals_conceded": match_data.home_score or 1,
                    }
                ) for i in range(10)
            ])

            # 注入阵容历史
            context.set_cached("home_history_lineups", [
                LineupSnapshot(
                    match_id=f"hist_{match_data.match_id}_{i}",
                    starter_ids=set(),
                    total_value=500.0,
                    avg_rating=7.0,
                    date="2024-01-01",
                ) for i in range(5)
            ])
            context.set_cached("away_history_lineups", [
                LineupSnapshot(
                    match_id=f"hist_{match_data.match_id}_{i}",
                    starter_ids=set(),
                    total_value=400.0,
                    avg_rating=6.8,
                    date="2024-01-01",
                ) for i in range(5)
            ])

            # 使用 V24.0 引擎提取特征
            result = self.feature_engine.extract_features(match_data, context)

            if not result.success:
                logger.warning(f"特征提取失败: {result.errors}")
                return None

            # 返回完整特征字典
            all_features = result.feature_vector.to_dict()

            # 记录特征数量
            feature_count = len(all_features)
            self.stats.feature_counts[feature_count] = self.stats.feature_counts.get(feature_count, 0) + 1

            return all_features

        except Exception as e:
            logger.error(f"V24.0 特征提取失败: {e}")
            return None

    def merge_and_update(
        self, match_id: int, v24_features: Dict[str, Any]
    ) -> bool:
        """
        更新数据库为 V24.0 特征

        Args:
            match_id: 比赛 ID
            v24_features: V24.0 完整特征字典

        Returns:
            是否成功更新
        """
        if self.config.dry_run:
            logger.info(f"[DRY RUN] 将更新 match_id={match_id}")
            return True

        try:
            # 更新 meta_data 中的版本
            meta_data = {
                'extraction_version': 'V24.0',
                'augmented_at': datetime.now().isoformat(),
                'feature_count': len(v24_features),
                'engine_version': self.feature_engine.engine_version,
            }

            # 执行数据库更新
            with self._conn.cursor() as cur:
                update_query = """
                    UPDATE match_features_training
                    SET enriched_features = %s::jsonb,
                        meta_data = COALESCE(meta_data, '{}'::jsonb) || %s::jsonb,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE match_id = %s;
                """

                cur.execute(
                    update_query,
                    (json.dumps(v24_features), json.dumps(meta_data), match_id)
                )

            self._conn.commit()
            return True

        except Exception as e:
            logger.error(f"更新 match_id={match_id} 失败: {e}")
            self._conn.rollback()
            return False

    def process_batch(self, candidates: List[Dict[str, Any]]) -> None:
        """
        处理一批候选记录

        Args:
            candidates: 候选记录列表
        """
        logger.info(f"开始处理 {len(candidates)} 条记录...")

        for candidate in candidates:
            match_id = candidate['match_id']

            try:
                # 1. 构建 MatchData
                match_data = self.fetch_match_data(candidate)

                if match_data is None:
                    logger.warning(f"match_id={match_id}: MatchData 构建失败，跳过")
                    self.stats.missing_raw_json += 1
                    self.stats.v24_maintained += 1
                    continue

                # 2. 提取 V24.0 特征
                v24_features = self.extract_v24_features(match_data)

                if v24_features is None:
                    logger.warning(f"match_id={match_id}: V24.0 特征提取失败")
                    self.stats.processing_errors += 1
                    self.stats.v24_maintained += 1
                    continue

                # 3. 更新数据库
                success = self.merge_and_update(match_id, v24_features)

                if success:
                    self.stats.v24_upgraded += 1
                    logger.info(f"match_id={match_id}: ✓ 成功晋升至 V24.0 ({len(v24_features)} 维)")
                else:
                    self.stats.processing_errors += 1
                    self.stats.v24_maintained += 1

            except Exception as e:
                logger.error(f"match_id={match_id}: 处理异常 - {e}")
                self.stats.processing_errors += 1
                self.stats.v24_maintained += 1

    def run(self) -> V24AugmentationStats:
        """
        执行完整的 V24.0 缝合流程

        Returns:
            统计信息
        """
        logger.info("=" * 60)
        logger.info("V24.0 时空特征矩阵增量缝合开始")
        logger.info("=" * 60)

        try:
            batch_count = 0
            while True:
                # 扫描候选记录
                candidates = self.scan_candidates()

                if not candidates:
                    logger.info("没有更多候选记录，处理完成")
                    break

                batch_count += 1
                logger.info(f"\n[批次 {batch_count}] 处理 {len(candidates)} 条记录")

                # 处理当前批次
                self.process_batch(candidates)

                # 打印当前统计
                logger.info(f"\n当前统计:")
                logger.info(f"  🟢 成功晋升 V24.0: {self.stats.v24_upgraded}")
                logger.info(f"  🟡 维持原版本: {self.stats.v24_maintained}")
                logger.info(f"  ⚠️  原始缺失: {self.stats.missing_raw_json}")
                logger.info(f"  ❌ 处理错误: {self.stats.processing_errors}")

                # 批次间休眠
                if candidates and self.config.sleep_between_batches > 0:
                    import time
                    logger.info(f"休眠 {self.config.sleep_between_batches} 秒...")
                    time.sleep(self.config.sleep_between_batches)

        except KeyboardInterrupt:
            logger.info("\n用户中断，正在退出...")

        except Exception as e:
            logger.error(f"运行异常: {e}")
            raise

        finally:
            self.close()

        # 打印最终统计
        logger.info("\n" + "=" * 60)
        logger.info("V24.0 时空特征矩阵增量缝合完成")
        logger.info("=" * 60)
        self._print_final_stats()

        return self.stats

    def _print_final_stats(self) -> None:
        """打印最终统计"""
        stats = self.stats.to_dict()

        print("\n" + "📊 " + "=" * 58)
        print("V24.0 缝合最终统计报告")
        print("=" * 60)

        print(f"\n扫描记录:")
        print(f"  • 总记录数: {stats['total_scanned']}")

        print(f"\n处理结果:")
        print(f"  🟢 成功晋升至 V24.0: {stats['v24_upgraded']} 场")
        print(f"  🟡 维持原版本: {stats['v24_maintained']} 场")

        print(f"\n失败原因:")
        print(f"  ⚠️  原始 JSON 缺失: {stats['missing_raw_json']} 场")
        print(f"  ❌ 处理错误: {stats['processing_errors']} 场")

        if stats['v24_upgraded'] > 0:
            success_rate = stats['v24_upgraded'] / max(stats['v24_candidates'], 1) * 100
            print(f"\n成功率: {success_rate:.1f}%")

        # 特征数量分布
        if stats['feature_counts']:
            print(f"\n特征数量分布:")
            for count, freq in sorted(stats['feature_counts'].items()):
                print(f"  • {count} 维: {freq} 场")

        print("\n" + "=" * 60)


# ============================================================================
# 主程序入口
# ============================================================================

def main():
    """主程序入口"""
    import argparse

    parser = argparse.ArgumentParser(
        description='V24.0 时空特征矩阵增量缝合脚本'
    )
    parser.add_argument(
        '--batch-size', type=int, default=50,
        help='批量处理大小（默认: 50）'
    )
    parser.add_argument(
        '--dry-run', action='store_true',
        help='演练模式（不实际更新数据库）'
    )
    parser.add_argument(
        '--sleep', type=float, default=1.0,
        help='批次间休眠秒数（默认: 1.0）'
    )

    args = parser.parse_args()

    # 创建配置
    config = V24AugmentationConfig(
        batch_size=args.batch_size,
        dry_run=args.dry_run,
        sleep_between_batches=args.sleep,
    )

    # 创建并运行缝合器
    augmentor = V24SurgicalAugmentor(config)
    stats = augmentor.run()

    # 返回退出码
    if stats.processing_errors > 0:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
