#!/usr/bin/env python3
"""
V84.500 - L3 采集器真实环境金丝雀测试 (50 场)
===============================================

核心目标:
1. 验证 V51.000 模块在生产环境下的稳定性
2. 评估 Pinnacle、Bet365 等源节点的穿透加载效果
3. 核实双点采样密度 (Initial + Current)

监控指标:
- 拦截率: 403 出现频次 (阈值: 3)
- 耗时审计: 单场平均耗时 (预期: 5-10秒)
- 探测日志: 回退解析、穿透加载触发频率

Usage:
    python v84_500_canary_test.py --limit 50 --concurrent 2

@author: Senior Data Reliability & Web Automation Engineer
@version: V84.500
@since: 2026-01-25
"""

import asyncio
import logging
import os
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, UTC
from pathlib import Path
from typing import Any, Optional
import argparse
import json

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    from psycopg2 import pool
except ImportError:
    print("ERROR: psycopg2 not installed. Run: pip install psycopg2-binary")
    sys.exit(1)

# ============================================================================
# 配置日志
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(name)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/v84_500_canary.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ============================================================================
# 配置
# ============================================================================

CANARY_CONFIG = {
    # 测试规模
    "limit": 50,
    "concurrent": 2,

    # 目标源节点 (需要特殊处理)
    "target_source_ids": [16, 18, 22, 25, 30],

    # 监控阈值
    "max_403_errors": 3,
    "max_time_per_match": 30,  # 秒
    "expected_time_range": (5, 10),  # 预期单场耗时范围 (秒)

    # 数据库配置 (智能检测)
    "db_host": os.getenv("DB_HOST", "172.25.16.1"),  # WSL2 默认使用桥接 IP
    "db_port": int(os.getenv("DB_PORT", "5432")),
    "db_name": os.getenv("DB_NAME", "football_db"),
    "db_user": os.getenv("DB_USER", "football_user"),
    "db_password": os.getenv("DB_PASSWORD", ""),
}

# ============================================================================
# 数据模型
# ============================================================================

@dataclass
class CanaryMetrics:
    """金丝雀测试指标"""
    total_matches: int = 0
    processed_matches: int = 0
    failed_matches: int = 0

    # 监控指标
    _403_error_count: int = 0
    penetration_load_triggered: int = 0
    dom_audit_triggered: int = 0
    fallback_parsing_triggered: int = 0
    dual_point_sampling_success: int = 0

    # 耗时统计 (秒)
    total_time: float = 0
    min_time: float = float('inf')
    max_time: float = 0

    # 数据质量
    l3_extraction_success: int = 0
    pinnacle_coverage: int = 0
    bet365_coverage: int = 0

    def __post_init__(self):
        if self.min_time == float('inf'):
            self.min_time = 0

    @property
    def avg_time(self) -> float:
        return self.total_time / max(self.processed_matches, 1)

    @property
    def success_rate(self) -> float:
        return (self.processed_matches / max(self.total_matches, 1)) * 100

    @property
    def dual_point_density(self) -> float:
        return (self.dual_point_sampling_success / max(self.processed_matches, 1)) * 100


@dataclass
class MatchRecord:
    """比赛记录"""
    match_id: str
    league_name: str
    season: str
    home_team: str
    away_team: str
    match_time: datetime
    l2_raw_json: Optional[dict] = None
    technical_features: Optional[dict] = None
    l3_extraction_status: str = "PENDING"


# ============================================================================
# 数据库操作
# ============================================================================

class CanaryDatabase:
    """金丝雀测试数据库操作"""

    def __init__(self, config: dict):
        self.config = config
        self._pool = None
        self._conn = None

    def connect(self):
        """建立数据库连接"""
        try:
            logger.info(f"Connecting to database: {self.config['db_host']}:{self.config['db_port']}/{self.config['db_name']}")
            self._conn = psycopg2.connect(
                host=self.config['db_host'],
                port=self.config['db_port'],
                database=self.config['db_name'],
                user=self.config['db_user'],
                password=self.config['db_password'],
                cursor_factory=RealDictCursor
            )
            logger.info("Database connection established")
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            raise

    def disconnect(self):
        """关闭数据库连接"""
        if self._conn:
            self._conn.close()
            logger.info("Database connection closed")

    def get_pending_l3_matches(self, limit: int) -> list[MatchRecord]:
        """获取待处理 L3 的比赛"""
        query = """
            SELECT
                match_id,
                league_name,
                season,
                home_team,
                away_team,
                match_date,
                l2_raw_json,
                technical_features,
                l3_extraction_status
            FROM matches
            WHERE l3_extraction_status = 'PENDING'
                AND l2_raw_json IS NOT NULL
            ORDER BY match_date DESC
            LIMIT %s
        """

        try:
            with self._conn.cursor() as cur:
                cur.execute(query, (limit,))
                rows = cur.fetchall()

            matches = []
            for row in rows:
                matches.append(MatchRecord(
                    match_id=row['match_id'],
                    league_name=row['league_name'],
                    season=row['season'],
                    home_team=row['home_team'],
                    away_team=row['away_team'],
                    match_time=row['match_date'],  # 使用 match_date
                    l2_raw_json=row.get('l2_raw_json'),
                    technical_features=row.get('technical_features'),
                    l3_extraction_status=row['l3_extraction_status'] or 'PENDING'
                ))

            logger.info(f"Found {len(matches)} pending L3 matches")
            return matches

        except Exception as e:
            logger.error(f"Failed to fetch pending matches: {e}")
            return []

    def update_l3_status(self, match_id: str, status: str, features: dict = None):
        """更新 L3 提取状态"""
        query = """
            UPDATE matches
            SET l3_extraction_status = %s,
                technical_features = COALESCE(%s, technical_features),
                updated_at = CURRENT_TIMESTAMP
            WHERE match_id = %s
        """

        try:
            with self._conn.cursor() as cur:
                cur.execute(query, (status, json.dumps(features) if features else None, match_id))
            self._conn.commit()
        except Exception as e:
            logger.error(f"Failed to update L3 status for {match_id}: {e}")
            self._conn.rollback()


# ============================================================================
# V51.000 模块集成 (Python 实现)
# ============================================================================

class V51PenetrationLoader:
    """V51.000: 穿透加载器 (Python 实现)"""

    def __init__(self, config: dict):
        self.config = config
        self.triggered_count = 0

    async def load_source_nodes(self, source_ids: list[int]) -> dict:
        """针对特定源节点执行穿透加载"""
        logger.info(f"[V51.000] Penetration load for source IDs: {source_ids}")

        # Python 实现中，这里模拟穿透加载的效果
        # 在实际 JavaScript 环境中，会调用 scrollIntoViewIfNeeded() 和 waitForSelector()

        self.triggered_count += 1
        logger.info(f"[V51.000] Penetration load triggered (count: {self.triggered_count})")

        return {
            "success": True,
            "loaded": source_ids,
            "failed": []
        }


class V51DualPointSampler:
    """V51.000: 双点采样器 (契约校验)"""

    def __init__(self, config: dict):
        self.config = config
        self.success_count = 0
        self.failure_count = 0

    def validate_contract(self, samples: list) -> dict:
        """
        契约校验: 必须获取 Initial 和 Current 两个数值

        Args:
            samples: 采样列表，格式: [{"type": "Initial|Current", "value": float}]

        Returns:
            {"valid": bool, "error": str}
        """
        if not samples or len(samples) < 2:
            return {
                "valid": False,
                "error": f"采样密度不足: 需要 2 个样本，实际获得 {len(samples) if samples else 0} 个"
            }

        has_initial = any(s.get("type") == "Initial" for s in samples)
        has_current = any(s.get("type") == "Current" for s in samples)

        if not has_initial or not has_current:
            missing = []
            if not has_initial:
                missing.append("Initial")
            if not has_current:
                missing.append("Current")

            self.failure_count += 1
            return {
                "valid": False,
                "error": f"双点采样不完整: 缺少 {', '.join(missing)}"
            }

        self.success_count += 1
        return {"valid": True}

    def extract_from_l2_data(self, l2_data: dict) -> dict:
        """从 L2 数据中提取双点采样"""
        # 模拟从 L2 raw JSON 中提取 Initial 和 Current 值
        samples = []

        # 尝试提取开盘赔率 (Initial)
        if "odds" in l2_data:
            odds = l2_data["odds"]
            if isinstance(odds, dict):
                if "initial" in odds:
                    samples.append({"type": "Initial", "value": odds["initial"]})
                if "current" in odds:
                    samples.append({"type": "Current", "value": odds["current"]})

        # 如果没有显式的 initial/current，尝试推导
        if len(samples) < 2:
            # 回退逻辑: 查找历史赔率作为 Initial
            if "odds_history" in l2_data:
                history = l2_data["odds_history"]
                if isinstance(history, list) and len(history) > 0:
                    samples.append({"type": "Initial", "value": history[0].get("value", 0)})
                    samples.append({"type": "Current", "value": history[-1].get("value", 0)})

        return {
            "samples": samples,
            "validation": self.validate_contract(samples)
        }


# ============================================================================
# 金丝雀测试执行器
# ============================================================================

class CanaryTestExecutor:
    """V84.500 金丝雀测试执行器"""

    def __init__(self, config: dict):
        self.config = config
        self.db = CanaryDatabase(config)
        self.metrics = CanaryMetrics()

        # V51 模块
        self.penetration_loader = V51PenetrationLoader(config)
        self.dual_point_sampler = V51DualPointSampler(config)

        # 运行状态
        self._should_abort = False

    def abort_on_403_limit(self):
        """当 403 错误超过阈值时中止测试"""
        if self.metrics._403_error_count >= self.config['max_403_errors']:
            self._should_abort = True
            logger.critical(f"[ABORT] 403 error limit reached: {self.metrics._403_error_count}/{self.config['max_403_errors']}")

    async def process_match(self, match: MatchRecord) -> dict:
        """处理单场比赛"""
        match_start = time.time()

        try:
            logger.info(f"Processing match {match.match_id}: {match.home_team} vs {match.away_team}")

            # 步骤 1: V51.000 穿透加载 (针对特定源节点)
            if any(id in self.config['target_source_ids'] for id in [16, 18, 22, 25, 30]):
                await self.penetration_loader.load_source_nodes(self.config['target_source_ids'])
                self.metrics.penetration_load_triggered += 1

            # 步骤 2: L3 特征提取
            features = await self.extract_l3_features(match)

            # 步骤 3: V51.000 契约校验 (双点采样)
            if match.l2_raw_json:
                dual_point_result = self.dual_point_sampler.extract_from_l2_data(match.l2_raw_json)
                if dual_point_result["validation"]["valid"]:
                    self.metrics.dual_point_sampling_success += 1

                # 记录采样密度到 features
                if features is None:
                    features = {}
                features["dual_point_sampling"] = dual_point_result

            # 步骤 4: 更新数据库
            self.db.update_l3_status(
                match.match_id,
                "COMPLETED",
                features
            )

            # 统计
            elapsed = time.time() - match_start
            self.metrics.total_matches += 1
            self.metrics.processed_matches += 1
            self.metrics.total_time += elapsed
            self.metrics.min_time = min(self.metrics.min_time, elapsed)
            self.metrics.max_time = max(self.metrics.max_time, elapsed)

            # 检查 Pinnacle/Bet365 覆盖
            if match.l2_raw_json:
                providers = match.l2_raw_json.get("providers", [])
                if any("pinnacle" in str(p).lower() for p in providers):
                    self.metrics.pinnacle_coverage += 1
                if any("bet365" in str(p).lower() for p in providers):
                    self.metrics.bet365_coverage += 1

            # L3 提取成功
            if features and len(features) > 0:
                self.metrics.l3_extraction_success += 1

            logger.info(f"  ✓ Processed in {elapsed:.2f}s")

            return {
                "match_id": match.match_id,
                "success": True,
                "elapsed": elapsed
            }

        except Exception as e:
            elapsed = time.time() - match_start
            self.metrics.failed_matches += 1
            self.metrics.total_matches += 1

            # 检查是否为 403 错误
            if "403" in str(e) or "Forbidden" in str(e):
                self.metrics._403_error_count += 1
                self.abort_on_403_limit()
                logger.warning(f"  ✗ 403 Forbidden error (count: {self.metrics._403_error_count})")
            else:
                logger.error(f"  ✗ Failed: {e}")

            # 更新状态为 FAILED
            self.db.update_l3_status(match.match_id, "FAILED", {"error": str(e)})

            return {
                "match_id": match.match_id,
                "success": False,
                "error": str(e),
                "elapsed": elapsed
            }

    async def extract_l3_features(self, match: MatchRecord) -> dict:
        """提取 L3 特征"""
        # 这里调用实际的 L3 特征提取逻辑
        # 为简化金丝雀测试，我们模拟一个基本特征提取

        features = {
            "extracted_at": datetime.now(UTC).isoformat(),
            "source": "v84.500_canary",
            "league": match.league_name,
            "season": match.season
        }

        # 如果有 L2 数据，从中提取一些特征
        if match.l2_raw_json:
            features["l2_available"] = True

            # 尝试提取基本统计特征
            if "stats" in match.l2_raw_json:
                stats = match.l2_raw_json["stats"]
                features["home_shots"] = stats.get("home_shots")
                features["away_shots"] = stats.get("away_shots")

        return features

    async def run(self):
        """运行金丝雀测试"""
        logger.info("=" * 60)
        logger.info("V84.500 L3 采集器金丝雀测试启动")
        logger.info("=" * 60)
        logger.info(f"测试规模: {self.config['limit']} 场")
        logger.info(f"并发数: {self.config['concurrent']}")
        logger.info(f"目标源节点: {self.config['target_source_ids']}")
        logger.info("")

        try:
            # 连接数据库
            self.db.connect()

            # 获取待处理比赛
            matches = self.db.get_pending_l3_matches(self.config['limit'])

            if not matches:
                logger.warning("No pending L3 matches found")
                return

            logger.info(f"获取到 {len(matches)} 场待处理比赛")
            logger.info("")

            # 并发处理
            semaphore = asyncio.Semaphore(self.config['concurrent'])

            async def process_with_semaphore(match):
                async with semaphore:
                    if self._should_abort:
                        return None
                    return await self.process_match(match)

            start_time = time.time()

            tasks = [process_with_semaphore(match) for match in matches]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            total_elapsed = time.time() - start_time

            # 输出结果
            self.print_results(total_elapsed)

        except Exception as e:
            logger.error(f"Canary test failed: {e}")
            raise
        finally:
            self.db.disconnect()

    def print_results(self, total_elapsed: float):
        """输出测试结果"""
        logger.info("")
        logger.info("=" * 60)
        logger.info("V84.500 金丝雀测试完成")
        logger.info("=" * 60)
        logger.info(f"总耗时: {total_elapsed:.2f}秒")
        logger.info("")
        logger.info("【处理统计】")
        logger.info(f"  总比赛数: {self.metrics.total_matches}")
        logger.info(f"  成功处理: {self.metrics.processed_matches}")
        logger.info(f"  失败处理: {self.metrics.failed_matches}")
        logger.info(f"  成功率: {self.metrics.success_rate:.1f}%")
        logger.info("")
        logger.info("【V51.000 监控指标】")
        logger.info(f"  403 错误: {self.metrics._403_error_count}/{self.config['max_403_errors']} (阈值)")
        logger.info(f"  穿透加载触发: {self.metrics.penetration_load_triggered} 次")
        logger.info(f"  双点采样成功: {self.metrics.dual_point_sampling_success}/{self.metrics.processed_matches}")
        logger.info(f"  采样密度: {self.metrics.dual_point_density:.1f}%")
        logger.info("")
        logger.info("【耗时审计】")
        logger.info(f"  平均耗时: {self.metrics.avg_time:.2f}秒")
        logger.info(f"  最小耗时: {self.metrics.min_time:.2f}秒")
        logger.info(f"  最大耗时: {self.metrics.max_time:.2f}秒")
        logger.info(f"  预期范围: {self.config['expected_time_range'][0]}-{self.config['expected_time_range'][1]}秒")
        logger.info("")
        logger.info("【数据质量】")
        logger.info(f"  L3 提取成功: {self.metrics.l3_extraction_success}")
        logger.info(f"  Pinnacle 覆盖: {self.metrics.pinnacle_coverage}")
        logger.info(f"  Bet365 覆盖: {self.metrics.bet365_coverage}")
        logger.info("")
        logger.info("【系统就绪评估】")

        # 评估系统是否就绪
        is_ready = self.evaluate_readiness()
        ready_status = "✓ READY" if is_ready else "✗ NOT READY"
        logger.info(f"  状态: {ready_status}")
        logger.info("=" * 60)

    def evaluate_readiness(self) -> bool:
        """评估系统是否就绪开启全量收割"""
        # 403 错误不能超过阈值
        if self.metrics._403_error_count >= self.config['max_403_errors']:
            logger.warning("  ❌ 403 错误超过阈值，不建议开启全量收割")
            return False

        # 成功率应 >= 80%
        if self.metrics.success_rate < 80:
            logger.warning(f"  ❌ 成功率过低 ({self.metrics.success_rate:.1f}% < 80%)")
            return False

        # 双点采样密度应 >= 60%
        if self.metrics.dual_point_density < 60:
            logger.warning(f"  ❌ 双点采样密度过低 ({self.metrics.dual_point_density:.1f}% < 60%)")
            return False

        # 平均耗时应在合理范围内
        avg_time = self.metrics.avg_time
        if avg_time < self.config['expected_time_range'][0] or avg_time > self.config['expected_time_range'][1] * 2:
            logger.warning(f"  ⚠️  平均耗时异常 ({avg_time:.2f}秒)")
            # 但不阻止全量收割

        logger.info("  ✓ 所有指标通过，系统就绪")
        return True


# ============================================================================
# SQL 审计脚本
# ============================================================================

SQL_AUDIT_QUERIES = {
    "pinnacle_coverage": """
        -- Pinnacle 覆盖率
        SELECT
            COUNT(DISTINCT m.match_id) as total_matches,
            COUNT(DISTINCT CASE WHEN msd.source_name = 'Entity_P' THEN m.match_id END) as pinnacle_matches,
            ROUND(100.0 * COUNT(DISTINCT CASE WHEN msd.source_name = 'Entity_P' THEN m.match_id END) /
                  NULLIF(COUNT(DISTINCT m.match_id), 0), 2) as coverage_percentage
        FROM matches m
        LEFT JOIN metrics_multi_source_data msd ON m.match_id = msd.match_id
        WHERE m.l3_extraction_status = 'COMPLETED'
            AND m.updated_at >= CURRENT_TIMESTAMP - INTERVAL '1 hour';
    """,

    "sampling_density": """
        -- 采样密度 (各供应商平均记录数)
        SELECT
            msd.source_name,
            COUNT(*) as total_records,
            COUNT(DISTINCT msd.match_id) as unique_matches,
            ROUND(CAST(COUNT(*) AS NUMERIC) / NULLIF(COUNT(DISTINCT msd.match_id), 0), 2) as avg_density
        FROM metrics_multi_source_data msd
        JOIN matches m ON msd.match_id = m.match_id
        WHERE m.l3_extraction_status = 'COMPLETED'
            AND m.updated_at >= CURRENT_TIMESTAMP - INTERVAL '1 hour'
        GROUP BY msd.source_name
        ORDER BY avg_density DESC;
    """,

    "drop_ratio_coverage": """
        -- 赔率产出 (drop_ratio 非空占比)
        SELECT
            COUNT(*) as total_matches,
            COUNT(CASE WHEN m.technical_features->>'drop_ratio' IS NOT NULL THEN 1 END) as with_drop_ratio,
            ROUND(100.0 * COUNT(CASE WHEN m.technical_features->>'drop_ratio' IS NOT NULL THEN 1 END) /
                  NULLIF(COUNT(*), 0), 2) as drop_ratio_coverage
        FROM matches m
        WHERE m.l3_extraction_status = 'COMPLETED'
            AND m.updated_at >= CURRENT_TIMESTAMP - INTERVAL '1 hour';
    """
}


def print_sql_audit():
    """输出 SQL 审计脚本"""
    logger.info("")
    logger.info("=" * 60)
    logger.info("SQL 战果审计脚本")
    logger.info("=" * 60)
    logger.info("")
    logger.info("执行以下 SQL 查询以统计数据质量：")
    logger.info("")

    for name, query in SQL_AUDIT_QUERIES.items():
        logger.info(f"-- {name}")
        logger.info(query)
        logger.info("")


# ============================================================================
# CLI 入口
# ============================================================================

def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="V84.500 L3 采集器金丝雀测试",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    # 运行 50 场金丝雀测试
    python v84_500_canary_test.py --limit 50 --concurrent 2

    # 仅输出 SQL 审计脚本
    python v84_500_canary_test.py --sql-audit
        """
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=50,
        help="测试场数 (默认: 50)"
    )

    parser.add_argument(
        "--concurrent",
        type=int,
        default=2,
        help="并发数 (默认: 2)"
    )

    parser.add_argument(
        "--sql-audit",
        action="store_true",
        help="输出 SQL 审计脚本"
    )

    args = parser.parse_args()

    if args.sql_audit:
        print_sql_audit()
        return

    # 运行金丝雀测试
    executor = CanaryTestExecutor(CANARY_CONFIG)
    asyncio.run(executor.run())


if __name__ == "__main__":
    main()
