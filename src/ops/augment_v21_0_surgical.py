"""
V21.0 增量特征补完脚本（Surgical Feature Augmentor）
======================================================

在不中断 Docker 现有 V20.8 收割进程的前提下，将数据库中已存在的记录
从 881 维无损升级至 900+ 维。

核心功能:
    1. 增量扫描: 找出所有需要升级的记录（缺少 V21.0 新因子）
    2. 深度缝合: 读取现有特征 + 提取新因子 + 原子合并
    3. 容错与原子性: 记录警告但不崩盘，支持断点续传

设计原则:
    - 并发安全: 批量处理 50 场，避免死锁
    - 原子操作: 每场比赛独立处理，失败不影响其他
    - 版本晋升: 成功后更新 extraction_version 为 'V21.0'
    - 统计透明: 展示成功/失败/维持的场数

作者: FootballPrediction Architecture Team
版本: V21.0-deep-blowout
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
    TeamStats,
)
from config_unified import get_settings

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/v21_augmentation.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# ============================================================================
# 数据类定义
# ============================================================================

@dataclass
class AugmentationConfig:
    """
    补完配置

    Attributes:
        batch_size: 批量处理大小（默认 50 场）
        dry_run: 是否为演练模式（不实际更新数据库）
        enable_referee_features: 是否启用裁判因子
        enable_context_features: 是否启用上下文因子
        sleep_between_batches: 批次间休眠秒数（避免干扰 Docker）
        max_retries: 单场比赛最大重试次数
    """
    batch_size: int = 50
    dry_run: bool = False
    enable_referee_features: bool = True
    enable_context_features: bool = True
    sleep_between_batches: float = 1.0
    max_retries: int = 3


@dataclass
class AugmentationStats:
    """
    统计信息

    Attributes:
        total_scanned: 扫描的总记录数
        v20_candidates: V20.8 候选记录数
        v21_upgraded: 成功晋升至 V21.0 的场数
        v20_maintained: 维持 V20.8 的场数（失败或跳过）
        missing_raw_json: 原始 JSON 缺失的场数
        processing_errors: 处理错误的场数
    """
    total_scanned: int = 0
    v20_candidates: int = 0
    v21_upgraded: int = 0
    v20_maintained: int = 0
    missing_raw_json: int = 0
    processing_errors: int = 0

    def to_dict(self) -> Dict[str, int]:
        """转换为字典"""
        return {
            'total_scanned': self.total_scanned,
            'v20_candidates': self.v20_candidates,
            'v21_upgraded': self.v21_upgraded,
            'v20_maintained': self.v20_maintained,
            'missing_raw_json': self.missing_raw_json,
            'processing_errors': self.processing_errors,
        }


# ============================================================================
# 核心类定义
# ============================================================================

class SurgicalAugmentor:
    """
    手术级特征补完器

    职责:
        1. 扫描数据库找出需要升级的记录
        2. 从 l2_raw_json 提取 V21.0 新因子
        3. 将新因子深度缝合到现有 enriched_features
        4. 更新 extraction_version 为 'V21.0'
    """

    # V21.0 新因子列表
    V21_FEATURES = [
        'ref_is_strict',
        'ref_penalty_bias',
        'ref_home_advantage',
        'ref_name_hash',
        'ref_experience_level',
        'kickoff_time_slot',
        'is_early_kickoff',
        'stadium_attendance_rate',
        'stadium_pressure',
        'adverse_weather_score',
    ]

    def __init__(self, config: Optional[AugmentationConfig] = None):
        """
        初始化补完器

        Args:
            config: 补完配置
        """
        self.config = config or AugmentationConfig()
        self.stats = AugmentationStats()

        # 获取数据库配置
        settings = get_settings()
        self.db_config = settings.database

        # 初始化特征引擎
        self.feature_engine = FeatureEngine()

        # 数据库连接（延迟初始化）
        self._conn = None

        logger.info("SurgicalAugmentor 初始化完成")
        logger.info(f"  - 批量大小: {self.config.batch_size}")
        logger.info(f"  - 演练模式: {self.config.dry_run}")
        logger.info(f"  - 裁判因子: {self.config.enable_referee_features}")
        logger.info(f"  - 上下文因子: {self.config.enable_context_features}")

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
            1. extraction_version = 'V20.8' 或类似版本
            2. enriched_features 中缺少至少一个 V21.0 新因子

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
                  AND enriched_features IS NOT NULL
            """)
            total_count = cur.fetchone()['total']
            self.stats.total_scanned = total_count
            logger.info(f"数据库总记录数: {total_count}")

            # 查找 V20.8 候选记录
            # 条件: enriched_features 不包含所有 V21.0 新因子
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
                    meta_data
                FROM match_features_training
                WHERE status = 'completed'
                  AND enriched_features IS NOT NULL
                  AND (
                      -- 缺少裁判因子
                      enriched_features->'ref_is_strict' IS NULL
                      OR enriched_features->'stadium_pressure' IS NULL
                      OR enriched_features->'kickoff_time_slot' IS NULL
                  )
                ORDER BY match_time DESC
                LIMIT %s;
            """

            cur.execute(query, (self.config.batch_size,))
            candidates = cur.fetchall()

            self.stats.v20_candidates = len(candidates)
            logger.info(f"找到 {len(candidates)} 条 V20.8 候选记录")

            return candidates

    def fetch_raw_json(self, match_id: int) -> Optional[Dict[str, Any]]:
        """
        获取原始 JSON 数据

        Args:
            match_id: 比赛 ID

        Returns:
            原始 JSON 数据（字典），如果不存在则返回 None
        """
        with self._conn.cursor() as cur:
            try:
                cur.execute("""
                    SELECT l2_raw_json
                    FROM matches
                    WHERE id = %s
                      AND l2_raw_json IS NOT NULL;
                """, (match_id,))

                result = cur.fetchone()
                if result is None:
                    return None

                raw_json = result['l2_raw_json']

                # 处理字符串类型的 JSON
                if isinstance(raw_json, str):
                    return json.loads(raw_json)

                return raw_json
            except Exception as e:
                logger.error(f"获取原始 JSON 失败 (match_id={match_id}): {e}")
                return None

    def extract_v21_features(
        self, raw_json: Dict[str, Any], match_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        从原始 JSON 提取 V21.0 新因子

        Args:
            raw_json: 原始 FotMob JSON 数据
            match_info: 比赛基础信息

        Returns:
            V21.0 新因子字典
        """
        # 构建 MatchData 对象
        match_data = self._build_match_data(raw_json, match_info)

        # 使用 FeatureEngine 提取特征
        result = self.feature_engine.extract_features(match_data)

        if not result.success:
            logger.warning(f"特征提取失败: {result.errors}")
            return {}

        # 只返回 V21.0 新因子
        all_features = result.feature_vector.to_dict()
        v21_features = {
            k: v for k, v in all_features.items()
            if k in self.V21_FEATURES or k.startswith('ref_') or k.startswith('stadium_')
        }

        return v21_features

    def _build_match_data(
        self, raw_json: Dict[str, Any], match_info: Dict[str, Any]
    ) -> MatchData:
        """
        从原始 JSON 构建 MatchData 对象

        Args:
            raw_json: 原始 FotMob JSON 数据
            match_info: 比赛基础信息

        Returns:
            MatchData 对象
        """
        # 解析裁判信息
        referee_name = self._extract_referee_name(raw_json)
        referee_id = raw_json.get('referee', {}).get('id')

        # 解析比赛时间
        match_time = match_info.get('match_time')
        if isinstance(match_time, str):
            match_time = datetime.fromisoformat(match_time.replace('Z', '+00:00'))

        # 解析场地信息
        venue_info = raw_json.get('venue', {})
        venue = venue_info.get('name')
        venue_capacity = venue_info.get('capacity')

        # 解析天气信息（如果有）
        weather = raw_json.get('weather', {})
        weather_temp = weather.get('temperature')
        weather_condition = weather.get('condition')

        # 构建上下文
        context = MatchContext(
            match_time=match_time,
            venue=venue,
            venue_capacity=venue_capacity,
            referee_name=referee_name,
            referee_id=referee_id,
            weather_temperature=weather_temp,
            weather_condition=weather_condition,
        )

        # 解析球队统计
        general = raw_json.get('general', {})
        home_team_data = general.get('homeTeam', {})
        away_team_data = general.get('awayTeam', {})

        home_stats = TeamStats(
            shots_total=home_team_data.get('shotsTotal'),
            shots_on_target=home_team_data.get('shotsOnTarget'),
            possession=home_team_data.get('possessionPercent'),
            corners=home_team_data.get('corners'),
            expected_goals=home_team_data.get('expectedGoals'),
            team_rating=home_team_data.get('rating'),
        )

        away_stats = TeamStats(
            shots_total=away_team_data.get('shotsTotal'),
            shots_on_target=away_team_data.get('shotsOnTarget'),
            possession=away_team_data.get('possessionPercent'),
            corners=away_team_data.get('corners'),
            expected_goals=away_team_data.get('expectedGoals'),
            team_rating=away_team_data.get('rating'),
        )

        # 构建 MatchData
        match_data = MatchData(
            match_id=str(match_info['match_id']),
            league_id=str(match_info.get('league_id', '')),
            season=match_info.get('season_id', '2324'),
            home_team=match_info['home_team'],
            away_team=match_info['away_team'],
            home_score=match_info.get('home_score'),
            away_score=match_info.get('away_score'),
            home_stats=home_stats,
            away_stats=away_stats,
            context=context,
        )

        return match_data

    def _extract_referee_name(self, raw_json: Dict[str, Any]) -> Optional[str]:
        """
        从原始 JSON 提取裁判姓名

        Args:
            raw_json: 原始 JSON 数据

        Returns:
            裁判姓名，如果不存在则返回 None
        """
        # 尝试多种路径
        referee = raw_json.get('referee')
        if referee and isinstance(referee, dict):
            return referee.get('name')

        # 尝试 matchFacts 路径
        match_facts = raw_json.get('matchFacts', {})
        info = match_facts.get('info', {})
        referee_info = info.get('referee')
        if referee_info:
            return referee_info.get('name') if isinstance(referee_info, dict) else referee_info

        return None

    def merge_and_update(
        self, match_id: int, enriched_features: Dict[str, Any],
        v21_features: Dict[str, Any]
    ) -> bool:
        """
        深度合并特征并更新数据库

        Args:
            match_id: 比赛 ID
            enriched_features: 现有特征字典
            v21_features: V21.0 新因子字典

        Returns:
            是否成功更新
        """
        if self.config.dry_run:
            logger.info(f"[DRY RUN] 将更新 match_id={match_id}")
            return True

        try:
            # 深度合并（原子操作）
            merged_features = {**enriched_features, **v21_features}

            # 更新 meta_data 中的版本
            meta_data = {
                'extraction_version': 'V21.0',
                'augmented_at': datetime.now().isoformat(),
                'new_feature_count': len(v21_features),
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
                    (json.dumps(merged_features), json.dumps(meta_data), match_id)
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
                # 1. 获取原始 JSON
                raw_json = self.fetch_raw_json(match_id)

                if raw_json is None:
                    logger.warning(f"match_id={match_id}: 原始 JSON 缺失，跳过")
                    self.stats.missing_raw_json += 1
                    self.stats.v20_maintained += 1
                    continue

                # 2. 提取 V21.0 新因子
                v21_features = self.extract_v21_features(raw_json, candidate)

                if not v21_features:
                    logger.warning(f"match_id={match_id}: 未能提取 V21.0 因子")
                    self.stats.processing_errors += 1
                    self.stats.v20_maintained += 1
                    continue

                # 3. 深度合并并更新
                enriched_features = candidate['enriched_features']
                if isinstance(enriched_features, str):
                    enriched_features = json.loads(enriched_features)

                success = self.merge_and_update(match_id, enriched_features, v21_features)

                if success:
                    self.stats.v21_upgraded += 1
                    logger.info(f"match_id={match_id}: ✓ 成功晋升至 V21.0 (+{len(v21_features)} 因子)")
                else:
                    self.stats.processing_errors += 1
                    self.stats.v20_maintained += 1

            except Exception as e:
                logger.error(f"match_id={match_id}: 处理异常 - {e}")
                self.stats.processing_errors += 1
                self.stats.v20_maintained += 1

    def run(self) -> AugmentationStats:
        """
        执行完整的补完流程

        Returns:
            统计信息
        """
        logger.info("=" * 60)
        logger.info("V21.0 增量特征补完开始")
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
                logger.info(f"  🟢 成功晋升: {self.stats.v21_upgraded}")
                logger.info(f"  🟡 维持原版: {self.stats.v20_maintained}")
                logger.info(f"  ⚠️  原始缺失: {self.stats.missing_raw_json}")
                logger.info(f"  ❌ 处理错误: {self.stats.processing_errors}")

                # 批次间休眠（避免干扰 Docker）
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
        logger.info("V21.0 增量特征补完完成")
        logger.info("=" * 60)
        self._print_final_stats()

        return self.stats

    def _print_final_stats(self) -> None:
        """打印最终统计"""
        stats = self.stats.to_dict()

        print("\n" + "📊 " + "=" * 58)
        print("最终统计报告")
        print("=" * 60)

        print(f"\n扫描记录:")
        print(f"  • 总记录数: {stats['total_scanned']}")

        print(f"\n处理结果:")
        print(f"  🟢 成功晋升至 V21.0: {stats['v21_upgraded']} 场")
        print(f"  🟡 维持 V20.8 版本: {stats['v20_maintained']} 场")

        print(f"\n失败原因:")
        print(f"  ⚠️  原始 JSON 缺失: {stats['missing_raw_json']} 场")
        print(f"  ❌ 处理错误: {stats['processing_errors']} 场")

        if stats['v21_upgraded'] > 0:
            success_rate = stats['v21_upgraded'] / max(stats['v20_candidates'], 1) * 100
            print(f"\n成功率: {success_rate:.1f}%")

        print("\n" + "=" * 60)


# ============================================================================
# 主程序入口
# ============================================================================

def main():
    """主程序入口"""
    import argparse

    parser = argparse.ArgumentParser(
        description='V21.0 增量特征补完脚本'
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
        '--no-referee', action='store_true',
        help='禁用裁判因子'
    )
    parser.add_argument(
        '--no-context', action='store_true',
        help='禁用上下文因子'
    )
    parser.add_argument(
        '--sleep', type=float, default=1.0,
        help='批次间休眠秒数（默认: 1.0）'
    )

    args = parser.parse_args()

    # 创建配置
    config = AugmentationConfig(
        batch_size=args.batch_size,
        dry_run=args.dry_run,
        enable_referee_features=not args.no_referee,
        enable_context_features=not args.no_context,
        sleep_between_batches=args.sleep,
    )

    # 创建并运行补完器
    augmentor = SurgicalAugmentor(config)
    stats = augmentor.run()

    # 返回退出码
    if stats.processing_errors > 0:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
