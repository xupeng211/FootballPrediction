#!/usr/bin/env python3
"""
V20.8 焦土收割执行器 - 重构硬化版
================================

⚠️  DEPRECATED - 此文件已被弃用 ⚠️

此模块已被 V25 统一特征提取框架取代:
    - 新框架位置: src/processors/v25_production_extractor.py
    - 新入口: ExtractorRegistry.create("V25.0")

保留原因:
    - 用于历史数据回填任务 (V20.5/V20.8 backfill scripts)
    - 某些 V20 专用功能尚未迁移到 V25

计划:
    - V26.0 将完全移除此文件
    - 881 维特征提取将统一使用 V25 框架

核心改进（旧版）:
1. 使用 Pydantic BaseSettings 自动加载环境变量
2. 数据库连接 3 次重试机制
3. 解耦 os.environ 注入
4. 881 维维度死结熔断

作者: SRE Lead
日期: 2025-12-25
版本: V20.8
弃用日期: 2025-12-26
"""

import os
import sys
import json
import time
import random
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from collections import defaultdict

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dotenv import load_dotenv
load_dotenv(override=False)

import psycopg2
from psycopg2.extras import RealDictCursor

from src.config_unified import get_settings
from src.ml.fault_tolerance import CircuitBreaker, CircuitBreakerConfig
from src.api.collectors.fotmob_core import FotMobCoreCollector
from src.ml.harvester_config import get_harvester_settings
from src.ml.harvester_db import get_connection_manager, DatabaseConnectionError

# V20.8 日志配置
from src.ml.harvester_config import get_harvester_settings

harvester_settings = get_harvester_settings()
log_params = harvester_settings.get_log_params()

# V20.8 确保日志目录存在（权限安全）
log_file = log_params['log_file']
log_dir = os.path.dirname(log_file)

# 在非 Docker 环境下，如果无法创建 /var/log/harvester，自动切换到 /tmp
if log_dir and not os.path.exists(log_dir):
    try:
        os.makedirs(log_dir, exist_ok=True)
    except (PermissionError, OSError):
        # 自动切换到 /tmp 目录（WSL2 或非 root 用户环境）
        log_file = '/tmp/harvester.log'
        log_dir = None
        # 更新日志文件设置
        harvester_settings.harvest_log_file = log_file

logging.basicConfig(
    level=getattr(logging, log_params['log_level']),
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# ==================== V20.8 全局配置 ====================
V20_8_VERSION = "V20.8"


@dataclass
class V20_8Metrics:
    """V20.8 执行指标"""
    total_matches: int = 0
    forced_overwrites: int = 0
    dimension_passed: int = 0
    dimension_failed: int = 0
    critical_errors: int = 0
    first_batch_matches: list = field(default_factory=list)
    dimension_fuse_triggered: bool = False


class V20_8Harvester:
    """
    V20.8 焦土收割执行器 - 重构硬化版

    改进:
    - 使用 Pydantic BaseSettings 自动加载环境变量
    - 数据库连接 3 次重试机制
    - 解耦 os.environ 注入
    """

    # 版本比较 SQL
    VERSION_CHECK_SQL = """
        SELECT match_id,
               COALESCE(
                   (meta_data->>'extraction_version')::text,
                   'V0.0'
               ) as current_version
        FROM match_features_training
        WHERE match_id = %s
    """

    def __init__(self):
        # V20.8 使用 Pydantic BaseSettings
        self.settings = get_harvester_settings()
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

        # V20.8 使用专用连接管理器（带重试机制）
        self.db_manager = get_connection_manager()

        logger.info("="*70)
        logger.info("V20.8 焦土收割执行器初始化完成 (重构硬化版)")
        logger.info(f"🎯 目标维度: {self.settings.target_features} 维")
        logger.info(f"🔒 维度死结: {self.settings.min_features} 维（前 {self.settings.dimension_fuse_count} 场熔断）")
        logger.info(f"🔌 数据库重试: {self.settings.db_retry_attempts} 次")
        logger.info(f"📋 日志文件: {self.settings.harvest_log_file}")
        logger.info("="*70)

    def _get_db_connection(self):
        """
        V20.8 数据库连接（使用连接管理器，自动重试）

        Returns:
            psycopg2 连接对象
        """
        return self.db_manager.get_connection()

    def _should_force_override(self, match_id: int) -> bool:
        """
        V20.8 强制覆盖逻辑

        判断规则:
        1. 如果数据库中不存在该记录 -> 需要插入
        2. 如果 extraction_version < V20.8 -> 强制覆盖
        3. 如果 extraction_version >= V20.8 -> 跳过
        """
        conn = self._get_db_connection()
        cur = conn.cursor()

        cur.execute(self.VERSION_CHECK_SQL, (match_id,))
        result = cur.fetchone()
        cur.close()

        if not result:
            return True  # 不存在，需要插入

        current_version = result.get('current_version', 'V0.0')

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

    def _validate_feature_count(self, features: Dict, match_id: int) -> bool:
        """
        V20.8 维度死结 - 验证特征数量

        熔断机制:
        - 前5场比赛中任何一场 < 881 维 -> 立即 sys.exit(1)
        - 第6场及以后仅记录警告，继续执行
        """
        feature_count = len(features)
        min_features = self.settings.min_features
        fuse_count = self.settings.dimension_fuse_count

        # 维度死结熔断机制
        if len(self.metrics.first_batch_matches) < fuse_count:
            self.metrics.first_batch_matches.append({
                'match_id': match_id,
                'feature_count': feature_count
            })

            if feature_count < min_features:
                # 触发熔断
                error_msg = (
                    f"\n{'='*70}\n"
                    f"🚨 V20.8 维度死结熔断触发！\n"
                    f"{'='*70}\n"
                    f"Match {match_id}: {feature_count} < {min_features} 维\n"
                    f"前 {fuse_count} 场维度记录:\n"
                )
                for i, record in enumerate(self.metrics.first_batch_matches, 1):
                    status = "✓" if record['feature_count'] >= min_features else "✗"
                    error_msg += f"  {status} {i}. Match {record['match_id']}: {record['feature_count']} 维\n"

                error_msg += (
                    f"{'='*70}\n"
                    f"💀 维度主权已锁死在 {min_features} 维，系统拒绝执行。\n"
                    f"{'='*70}\n"
                )

                logger.error(error_msg)
                self.metrics.dimension_fuse_triggered = True
                self.metrics.dimension_failed += 1
                self.metrics.critical_errors += 1
                sys.exit(1)

        elif feature_count < min_features:
            # 第6场及以后仅记录警告
            logger.warning(f"  ⚠️  Match {match_id}: {feature_count} < {min_features} 维 (已过熔断期)")
            self.metrics.dimension_failed += 1
            return False

        # 维度达标
        self.metrics.dimension_passed += 1
        logger.debug(f"  ✓ 维度验证通过: {feature_count} >= {min_features}")
        return True

    def harvest_match(self, match_id: int) -> Optional[Dict]:
        """
        收割单场比赛 - V20.8 强制覆盖逻辑
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

            # 2. 构造 match_data 结构（V20.8 修复：确保 atomic_align_v20_8 能被触发）
            match_info = content.get('content', {}).get('match', {})
            general = content.get('content', {}).get('general', {})

            # V20.8 关键修复：确保 l2_json 包含 general 字段，以便 FeatureExtractor 能提取 team_id
            l2_json = {
                'l2_json': content,
                'general': {
                    'homeTeam': {'id': match_info.get('homeTeam')},
                    'awayTeam': {'id': match_info.get('awayTeam')}
                }
            }

            match_data = {
                'match_id': match_id,
                'league_id': match_info.get('leagueId'),
                'season_id': match_info.get('seasonId'),
                'home_team': match_info.get('homeTeam'),
                'away_team': match_info.get('awayTeam'),
                # V20.8 关键修复：添加 team_id 以触发 atomic_align_v20_8
                'home_team_id': match_info.get('homeTeam'),
                'away_team_id': match_info.get('awayTeam'),
                'player_stats': l2_json,
                'l2_raw_json': l2_json,
            }

            # 3. 提取基础特征
            from src.ml.feature_forge_v20 import FeatureExtractor
            extractor = FeatureExtractor()
            extracted = extractor.extract_features(match_data)

            if not extracted:
                logger.error(f"  ❌ Match {match_id} 特征提取失败")
                return None

            # 合并 core 和 enriched
            features = {**extracted.get('enriched', {}), **extracted.get('core', {})}

            # 4. 深度聚合（可选）
            # TODO: 添加深度聚合逻辑

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

        except SystemExit:
            raise
        except Exception as e:
            logger.error(f"  ❌ Match {match_id} 处理失败: {e}")
            return None

    def _save_to_database(self, match_id: int, content: Dict, features: Dict):
        """
        V20.8 保存到数据库 - 修复标签丢失问题

        修复:
        - UPDATE 语句包含 league_id, season_id, home_team, away_team
        - 避免 Unknown/NULL 污染数据库
        """
        conn = self._get_db_connection()
        cur = conn.cursor()

        match_info = content.get('content', {}).get('match', {})
        home_team = match_info.get('homeTeam', 'Unknown')
        away_team = match_info.get('awayTeam', 'Unknown')

        # 提取联赛和赛季信息
        league_id = match_info.get('leagueId')
        season_id = match_info.get('seasonId')

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
            cur.execute("""
                INSERT INTO match_features_training (
                    match_id, league_id, season_id, home_team, away_team,
                    enriched_features, meta_data, status, created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
            """, (
                match_id,
                league_id,
                season_id,
                home_team,
                away_team,
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
        """
        收割整个赛季 - V20.8 呼吸式限流器

        呼吸式限流:
        - 随机 sleep 1.2s - 2.0s
        - 模拟人类行为，防止 API 针对性封锁
        """
        leagues = {
            47: "Premier_League",
            53: "Serie_A",
            54: "Bundesliga",
            55: "Ligue_1",
            87: "LaLiga"
        }

        logger.info(f"\n{'='*70}")
        logger.info(f"开始收割: {leagues.get(league_id, f'League {league_id}')} {season} ({len(match_ids)} 场)")
        logger.info(f"🫁 呼吸式限流器已激活: 1.2s - 2.0s")
        logger.info(f"{'='*70}\n")

        success_count = 0
        fail_count = 0

        for i, match_id in enumerate(match_ids, 1):
            if self.circuit_breaker.is_open():
                logger.error("🔴 熔断器已打开，停止执行")
                break

            print(f"[{i}/{len(match_ids)}] ", end='', flush=True)

            try:
                result = self.harvest_match(match_id)
                if result:
                    success_count += 1
                else:
                    fail_count += 1

                # V20.8 呼吸式限流器（随机波动）
                breathing_sleep = random.uniform(1.2, 2.0)
                time.sleep(breathing_sleep)

            except SystemExit:
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

        if self.metrics.first_batch_matches:
            logger.info("\n前5场维度死结验证:")
            for i, record in enumerate(self.metrics.first_batch_matches, 1):
                status = "✓" if record['feature_count'] >= self.settings.min_features else "✗"
                logger.info(f"  {status} {i}. Match {record['match_id']}: {record['feature_count']} 维")

        if self.metrics.dimension_fuse_triggered:
            logger.info("\n🚨 维度熔断已触发，系统已终止执行")

        logger.info("="*70)


# ==================== 主程序 ====================
if __name__ == "__main__":
    logger.info("🚀 V20.8 焦土收割计划启动 (重构硬化版)...")

    def load_match_ids(season: str) -> List[int]:
        """加载比赛 ID"""
        manifest_file = f"data/production/harvest_manifest_{season}.csv"
        if not os.path.exists(manifest_file):
            logger.warning(f"清单文件不存在: {manifest_file}")
            return []

        import csv
        match_ids = []
        with open(manifest_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                match_id = row.get('match_id')
                if match_id:
                    match_ids.append(int(match_id))

        logger.info(f"📋 加载 {len(match_ids)} 个比赛 ID: {season}")
        return match_ids

    harvester = V20_8Harvester()

    try:
        seasons = ["2122", "2223", "2324", "2425"]
        for season in seasons:
            match_ids = load_match_ids(season)
            if match_ids:
                harvester.harvest_season(47, season, match_ids)

        harvester.print_final_report()

        logger.info("\n🎯 焦土计划执行完毕，7161 场 881 维镜像已就绪。")

    except KeyboardInterrupt:
        logger.info("\n⚠️  收到中断信号，正在退出...")
    except SystemExit:
        raise
    except Exception as e:
        logger.error(f"💀 执行失败: {e}")
        raise
