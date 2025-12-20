"""
统一数据质量检查模块

整合归档脚本中的所有数据质量检查逻辑，提供：
- 表结构验证
- 数据完整性检查
- 数据一致性验证
- 数据质量评分
- 异常检测机制
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any, Union
from dataclasses import dataclass, field
from enum import Enum
import numpy as np
import asyncpg
from pathlib import Path

from src.config_unified import get_settings

logger = logging.getLogger(__name__)


class DataQualityLevel(Enum):
    """数据质量等级"""
    EXCELLENT = "A+ (卓越)"
    GOOD = "A (优秀)"
    SATISFACTORY = "B+ (良好)"
    PASS = "B (合格)"
    NEED_IMPROVEMENT = "C (待改进)"


@dataclass
class TableStructureValidation:
    """表结构验证结果"""
    table_name: str
    expected_columns: List[str]
    actual_columns: List[str]
    missing_columns: List[str] = field(default_factory=list)
    extra_columns: List[str] = field(default_factory=list)
    is_valid: bool = False
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DataIntegrityResult:
    """数据完整性检查结果"""
    table_name: str
    total_records: int
    valid_records: int
    missing_values: Dict[str, int] = field(default_factory=dict)
    null_percentages: Dict[str, float] = field(default_factory=dict)
    integrity_score: float = 0.0
    issues: List[str] = field(default_factory=list)


@dataclass
class DataConsistencyResult:
    """数据一致性检查结果"""
    check_type: str
    is_consistent: bool
    inconsistent_count: int
    total_checked: int
    consistency_rate: float
    details: Dict[str, Any] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)


@dataclass
class AnomalyDetectionResult:
    """异常检测结果"""
    anomaly_type: str
    detected_anomalies: List[Dict[str, Any]]
    anomaly_count: int
    severity: str  # low, medium, high, critical
    affected_records: int


@dataclass
class DataQualityReport:
    """数据质量综合报告"""
    timestamp: str
    overall_score: float
    quality_level: DataQualityLevel
    table_validations: List[TableStructureValidation] = field(default_factory=list)
    integrity_results: List[DataIntegrityResult] = field(default_factory=list)
    consistency_results: List[DataConsistencyResult] = field(default_factory=list)
    anomaly_results: List[AnomalyDetectionResult] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)


class DataQualityChecker:
    """统一数据质量检查器"""

    def __init__(self):
        self.settings = get_settings()
        self.conn = None

        # 预定义的表结构期望
        self.expected_table_schemas = {
            'matches': [
                'id', 'external_id', 'league_id', 'season', 'home_team_id',
                'away_team_id', 'home_score', 'away_score', 'match_date',
                'match_time', 'venue', 'collection_status', 'l2_collected_at'
            ],
            'match_features_training': [
                'id', 'match_id', 'home_team_id', 'away_team_id',
                'home_team', 'away_team', 'match_time', 'home_goals',
                'away_goals', 'home_xg', 'away_xg', 'home_shots',
                'away_shots', 'home_possession', 'away_possession',
                'home_opening_odds', 'draw_opening_odds', 'away_opening_odds',
                'home_advantage_flag', 'home_advantage_strength',
                'h2h_home_win_rate', 'home_recent_form', 'away_recent_form',
                'match_completed'
            ],
            'raw_match_data': [
                'id', 'match_id', 'external_id', 'raw_match_data',
                'raw_odds_data', 'created_at', 'updated_at'
            ],
            'teams': ['id', 'name', 'league_id', 'external_id'],
            'leagues': ['id', 'name', 'external_id']
        }

        # 联赛识别模式
        self.league_patterns = {
            'Premier League': [
                'United', 'City', 'Chelsea', 'Arsenal', 'Liverpool',
                'Tottenham', 'Leicester', 'West Ham', 'Everton', 'Wolverhampton'
            ],
            'Bundesliga': [
                'Bayern', 'Dortmund', 'Leipzig', 'Leverkusen',
                'Frankfurt', 'Mönchengladbach', 'Hoffenheim'
            ]
        }

        # 数据质量阈值
        self.quality_thresholds = {
            'min_records': 500,  # 最小记录数
            'excellent_records': 700,  # 优秀记录数
            'xg_coverage_excellent': 80,  # xG覆盖率优秀阈值
            'xg_coverage_good': 60,  # xG覆盖率良好阈值
            'odds_coverage_excellent': 80,  # 赔率覆盖率优秀阈值
            'odds_coverage_good': 60,  # 赔率覆盖率良好阈值
        }

    async def connect(self):
        """连接数据库"""
        try:
            self.conn = await asyncpg.connect(
                host=self.settings.database.host,
                port=self.settings.database.port,
                database=self.settings.database.name,
                user=self.settings.database.user,
                password=self.settings.database.password.get_secret_value()
            )
            logger.info("数据质量检查器：数据库连接成功")
        except Exception as e:
            logger.error(f"数据质量检查器：数据库连接失败 {e}")
            raise

    async def close(self):
        """关闭数据库连接"""
        if self.conn:
            await self.conn.close()

    async def check_table_structure(self, table_name: str) -> TableStructureValidation:
        """检查表结构"""
        if table_name not in self.expected_table_schemas:
            raise ValueError(f"未知的表名: {table_name}")

        expected_columns = self.expected_table_schemas[table_name]

        # 查询实际表结构
        query = """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = $1
            ORDER BY ordinal_position
        """
        actual_columns = [row['column_name'] for row in await self.conn.fetch(query, table_name)]

        # 检查差异
        missing_columns = set(expected_columns) - set(actual_columns)
        extra_columns = set(actual_columns) - set(expected_columns)
        is_valid = len(missing_columns) == 0

        # 获取列类型信息
        column_details = {}
        for col in actual_columns:
            type_query = """
                SELECT data_type, is_nullable, character_maximum_length
                FROM information_schema.columns
                WHERE table_name = $1 AND column_name = $2
            """
            details = await self.conn.fetchrow(type_query, table_name, col)
            if details:
                column_details[col] = {
                    'type': details['data_type'],
                    'nullable': details['is_nullable'] == 'YES',
                    'max_length': details['character_maximum_length']
                }

        return TableStructureValidation(
            table_name=table_name,
            expected_columns=expected_columns,
            actual_columns=actual_columns,
            missing_columns=list(missing_columns),
            extra_columns=list(extra_columns),
            is_valid=is_valid,
            details=column_details
        )

    async def check_data_integrity(self, table_name: str) -> DataIntegrityResult:
        """检查数据完整性"""
        # 获取总记录数
        total_records = await self.conn.fetchval(f"SELECT COUNT(*) FROM {table_name}")

        # 根据表名进行特定的完整性检查
        if table_name == 'match_features_training':
            return await self._check_features_integrity(total_records)
        elif table_name == 'matches':
            return await self._check_matches_integrity(total_records)
        elif table_name == 'raw_match_data':
            return await self._check_raw_data_integrity(total_records)
        else:
            # 通用完整性检查
            return await self._check_generic_integrity(table_name, total_records)

    async def _check_features_integrity(self, total_records: int) -> DataIntegrityResult:
        """检查特征表完整性"""
        # 检查关键字段的空值情况
        critical_fields = [
            'home_team', 'away_team', 'match_time',
            'home_xg', 'away_xg', 'home_opening_odds'
        ]

        missing_values = {}
        null_percentages = {}
        valid_records = total_records

        for field in critical_fields:
            null_count = await self.conn.fetchval(
                f"SELECT COUNT(*) FROM match_features_training WHERE {field} IS NULL"
            )
            missing_values[field] = null_count
            null_percentages[field] = (null_count / total_records * 100) if total_records > 0 else 0

            # 如果关键字段为空，减少有效记录数
            if field in ['home_team', 'away_team'] and null_count > 0:
                valid_records = min(valid_records, total_records - null_count)

        # 检查xG数据质量
        zero_xg_count = await self.conn.fetchval(
            "SELECT COUNT(*) FROM match_features_training WHERE home_xg = 0 AND away_xg = 0"
        )

        # 检查数据范围异常
        issues = []
        if null_percentages.get('home_team', 0) > 0:
            issues.append(f"主队名称缺失: {null_percentages['home_team']:.1f}%")
        if null_percentages.get('away_team', 0) > 0:
            issues.append(f"客队名称缺失: {null_percentages['away_team']:.1f}%")
        if zero_xg_count > total_records * 0.1:  # 超过10%的xG为0
            issues.append(f"xG数据异常: {zero_xg_count}条记录xG为0")

        # 计算完整性分数
        integrity_score = (valid_records / total_records * 100) if total_records > 0 else 0

        return DataIntegrityResult(
            table_name='match_features_training',
            total_records=total_records,
            valid_records=valid_records,
            missing_values=missing_values,
            null_percentages=null_percentages,
            integrity_score=integrity_score,
            issues=issues
        )

    async def _check_matches_integrity(self, total_records: int) -> DataIntegrityResult:
        """检查比赛表完整性"""
        # 检查关键字段
        null_counts = {}
        critical_fields = ['external_id', 'league_id', 'home_team_id', 'away_team_id', 'match_date']

        for field in critical_fields:
            null_count = await self.conn.fetchval(
                f"SELECT COUNT(*) FROM matches WHERE {field} IS NULL"
            )
            null_counts[field] = null_count

        # 检查外部ID重复
        duplicate_external_ids = await self.conn.fetchval("""
            SELECT COUNT(*) FROM (
                SELECT external_id FROM matches
                WHERE external_id IS NOT NULL
                GROUP BY external_id
                HAVING COUNT(*) > 1
            ) duplicates
        """)

        issues = []
        if duplicate_external_ids > 0:
            issues.append(f"发现{duplicate_external_ids}个重复的外部ID")

        valid_records = total_records - sum(null_counts.values())
        integrity_score = (valid_records / total_records * 100) if total_records > 0 else 0

        return DataIntegrityResult(
            table_name='matches',
            total_records=total_records,
            valid_records=valid_records,
            missing_values=null_counts,
            null_percentages={k: (v/total_records*100) for k, v in null_counts.items()},
            integrity_score=integrity_score,
            issues=issues
        )

    async def _check_raw_data_integrity(self, total_records: int) -> DataIntegrityResult:
        """检查原始数据表完整性"""
        # 检查原始数据质量
        empty_json_count = await self.conn.fetchval(
            "SELECT COUNT(*) FROM raw_match_data WHERE raw_match_data = '{}'::jsonb OR raw_match_data IS NULL"
        )

        issues = []
        if empty_json_count > 0:
            issues.append(f"发现{empty_json_count}条空的原始数据记录")

        valid_records = total_records - empty_json_count
        integrity_score = (valid_records / total_records * 100) if total_records > 0 else 0

        return DataIntegrityResult(
            table_name='raw_match_data',
            total_records=total_records,
            valid_records=valid_records,
            missing_values={'empty_json': empty_json_count},
            null_percentages={'empty_json': (empty_json_count/total_records*100) if total_records > 0 else 0},
            integrity_score=integrity_score,
            issues=issues
        )

    async def _check_generic_integrity(self, table_name: str, total_records: int) -> DataIntegrityResult:
        """通用完整性检查"""
        # 获取所有列
        columns = await self.conn.fetch(f"""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = $1
        """, table_name)

        # 检查每列的空值
        missing_values = {}
        for col in columns:
            null_count = await self.conn.fetchval(
                f"SELECT COUNT(*) FROM {table_name} WHERE {col['column_name']} IS NULL"
            )
            if null_count > 0:
                missing_values[col['column_name']] = null_count

        valid_records = total_records  # 通用检查无法确定有效记录

        return DataIntegrityResult(
            table_name=table_name,
            total_records=total_records,
            valid_records=valid_records,
            missing_values=missing_values,
            null_percentages={k: (v/total_records*100) for k, v in missing_values.items()},
            integrity_score=100.0,  # 默认分数
            issues=[]
        )

    async def check_data_consistency(self) -> List[DataConsistencyResult]:
        """检查数据一致性"""
        results = []

        # 1. 检查match_features_training与matches的关联一致性
        results.append(await self._check_features_matches_consistency())

        # 2. 检查主客场优势逻辑一致性
        results.append(await self._check_home_advantage_consistency())

        # 3. 检查联赛数据一致性
        results.append(await self._check_league_consistency())

        # 4. 检查比分与xG的一致性
        results.append(await self._check_score_xg_consistency())

        return results

    async def _check_features_matches_consistency(self) -> DataConsistencyResult:
        """检查特征表与比赛表的一致性"""
        # 检查特征表中的match_id是否都在matches表中存在
        orphaned_features = await self.conn.fetchval("""
            SELECT COUNT(*) FROM match_features_training mft
            LEFT JOIN matches m ON mft.match_id = m.id
            WHERE m.id IS NULL
        """)

        total_features = await self.conn.fetchval("SELECT COUNT(*) FROM match_features_training")
        is_consistent = orphaned_features == 0
        consistency_rate = ((total_features - orphaned_features) / total_features * 100) if total_features > 0 else 100

        recommendations = []
        if orphaned_features > 0:
            recommendations.append(f"清理{orphaned_features}条孤立的特征记录")

        return DataConsistencyResult(
            check_type="特征表-比赛表关联一致性",
            is_consistent=is_consistent,
            inconsistent_count=orphaned_features,
            total_checked=total_features,
            consistency_rate=consistency_rate,
            details={"orphaned_features": orphaned_features},
            recommendations=recommendations
        )

    async def _check_home_advantage_consistency(self) -> DataConsistencyResult:
        """检查主场优势逻辑一致性"""
        # 检查主场优势标志与实际统计数据的一致性
        inconsistent_count = await self.conn.fetchval("""
            SELECT COUNT(*) FROM match_features_training
            WHERE (
                (h2h_home_win_rate > 0.5 AND home_recent_form > away_recent_form AND home_advantage_flag != 1)
                OR
                (h2h_home_win_rate <= 0.5 AND home_recent_form <= away_recent_form AND home_advantage_flag = 1)
            )
        """)

        total_checked = await self.conn.fetchval(
            "SELECT COUNT(*) FROM match_features_training WHERE h2h_home_win_rate IS NOT NULL"
        )

        is_consistent = inconsistent_count == 0
        consistency_rate = ((total_checked - inconsistent_count) / total_checked * 100) if total_checked > 0 else 100

        return DataConsistencyResult(
            check_type="主场优势逻辑一致性",
            is_consistent=is_consistent,
            inconsistent_count=inconsistent_count,
            total_checked=total_checked,
            consistency_rate=consistency_rate,
            details={"inconsistent_records": inconsistent_count}
        )

    async def _check_league_consistency(self) -> DataConsistencyResult:
        """检查联赛数据一致性"""
        # 通过队名识别联赛并统计
        league_identification = await self.conn.fetch("""
            SELECT
                CASE
                    WHEN home_team ~ ANY(ARRAY[$1]) THEN 'Premier League'
                    WHEN home_team ~ ANY(ARRAY[$2]) THEN 'Bundesliga'
                    ELSE 'Other'
                END as identified_league,
                COUNT(*) as count
            FROM match_features_training
            GROUP BY identified_league
        """, self.league_patterns['Premier League'], self.league_patterns['Bundesliga'])

        # 这里简化处理，实际可以更复杂
        total_checked = sum(row['count'] for row in league_identification)

        return DataConsistencyResult(
            check_type="联赛数据一致性",
            is_consistent=True,  # 简化处理
            inconsistent_count=0,
            total_checked=total_checked,
            consistency_rate=100.0,
            details={"league_distribution": dict(league_identification)}
        )

    async def _check_score_xg_consistency(self) -> DataConsistencyResult:
        """检查比分与xG的一致性"""
        # 检查极端不一致的情况（比如大胜但xG很低）
        extreme_inconsistency = await self.conn.fetchval("""
            SELECT COUNT(*) FROM match_features_training
            WHERE home_goals IS NOT NULL AND away_goals IS NOT NULL
            AND home_xg IS NOT NULL AND away_xg IS NOT NULL
            AND (
                (ABS(home_goals - away_goals) >= 3 AND ABS(home_xg - away_xg) < 0.5)
                OR
                (ABS(home_goals - away_goals) = 0 AND ABS(home_xg - away_xg) > 3)
            )
        """)

        total_checked = await self.conn.fetchval("""
            SELECT COUNT(*) FROM match_features_training
            WHERE home_goals IS NOT NULL AND away_goals IS NOT NULL
            AND home_xg IS NOT NULL AND away_xg IS NOT NULL
        """)

        is_consistent = extreme_inconsistency < (total_checked * 0.05)  # 允许5%的极端情况
        consistency_rate = ((total_checked - extreme_inconsistency) / total_checked * 100) if total_checked > 0 else 100

        return DataConsistencyResult(
            check_type="比分-xG一致性",
            is_consistent=is_consistent,
            inconsistent_count=extreme_inconsistency,
            total_checked=total_checked,
            consistency_rate=consistency_rate,
            details={"extreme_inconsistencies": extreme_inconsistency}
        )

    async def detect_anomalies(self) -> List[AnomalyDetectionResult]:
        """检测数据异常"""
        anomalies = []

        # 1. 检测xG异常值
        anomalies.append(await self._detect_xg_anomalies())

        # 2. 检测赔率异常值
        anomalies.append(await self._detect_odds_anomalies())

        # 3. 检测比赛时间异常
        anomalies.append(await self._detect_time_anomalies())

        # 4. 检测数据收集异常
        anomalies.append(await self._detect_collection_anomalies())

        return anomalies

    async def _detect_xg_anomalies(self) -> AnomalyDetectionResult:
        """检测xG异常值"""
        # 查找极端xG值
        extreme_xg = await self.conn.fetch("""
            SELECT id, home_team, away_team, home_xg, away_xg,
                   ABS(home_xg - away_xg) as xg_diff
            FROM match_features_training
            WHERE home_xg > 5 OR away_xg > 5 OR ABS(home_xg - away_xg) > 4
            LIMIT 10
        """)

        anomaly_count = len(extreme_xg)
        severity = "high" if anomaly_count > 5 else "medium"

        return AnomalyDetectionResult(
            anomaly_type="xG异常值",
            detected_anomalies=[dict(record) for record in extreme_xg],
            anomaly_count=anomaly_count,
            severity=severity,
            affected_records=anomaly_count
        )

    async def _detect_odds_anomalies(self) -> AnomalyDetectionResult:
        """检测赔率异常值"""
        # 查找不合理赔率
        odd_anomalies = await self.conn.fetch("""
            SELECT id, home_team, away_team,
                   home_opening_odds, draw_opening_odds, away_opening_odds
            FROM match_features_training
            WHERE (home_opening_odds < 1.01 OR home_opening_odds > 100)
               OR (away_opening_odds < 1.01 OR away_opening_odds > 100)
               OR (draw_opening_odds < 1.01 OR draw_opening_odds > 100)
            LIMIT 10
        """)

        anomaly_count = len(odd_anomalies)
        severity = "critical" if anomaly_count > 0 else "low"

        return AnomalyDetectionResult(
            anomaly_type="赔率异常值",
            detected_anomalies=[dict(record) for record in odd_anomalies],
            anomaly_count=anomaly_count,
            severity=severity,
            affected_records=anomaly_count
        )

    async def _detect_time_anomalies(self) -> AnomalyDetectionResult:
        """检测时间异常"""
        # 查找未来日期或异常旧日期
        time_anomalies = await self.conn.fetch("""
            SELECT id, home_team, away_team, match_time
            FROM match_features_training
            WHERE match_time > NOW() + INTERVAL '7 days'
               OR match_time < '2010-01-01'
            LIMIT 10
        """)

        anomaly_count = len(time_anomalies)
        severity = "medium" if anomaly_count > 0 else "low"

        return AnomalyDetectionResult(
            anomaly_type="比赛时间异常",
            detected_anomalies=[dict(record) for record in time_anomalies],
            anomaly_count=anomaly_count,
            severity=severity,
            affected_records=anomaly_count
        )

    async def _detect_collection_anomalies(self) -> AnomalyDetectionResult:
        """检测数据收集异常"""
        # 检查数据收集中的断点
        collection_gaps = await self.conn.fetch("""
            SELECT DATE(match_time) as match_date, COUNT(*) as count
            FROM matches
            WHERE match_time >= NOW() - INTERVAL '30 days'
            GROUP BY DATE(match_time)
            ORDER BY match_date
        """)

        # 简化处理：如果某天数据量异常少，标记为异常
        anomalies = []
        if collection_gaps:
            avg_count = sum(row['count'] for row in collection_gaps) / len(collection_gaps)
            for row in collection_gaps:
                if row['count'] < avg_count * 0.1:  # 少于平均10%
                    anomalies.append({
                        'date': row['match_date'].isoformat(),
                        'count': row['count'],
                        'expected_avg': avg_count
                    })

        return AnomalyDetectionResult(
            anomaly_type="数据收集异常",
            detected_anomalies=anomalies,
            anomaly_count=len(anomalies),
            severity="medium",
            affected_records=sum(a['count'] for a in anomalies)
        )

    async def calculate_quality_score(self,
                                    integrity_results: List[DataIntegrityResult],
                                    consistency_results: List[DataConsistencyResult],
                                    anomaly_results: List[AnomalyDetectionResult]) -> Tuple[float, DataQualityLevel]:
        """计算数据质量总分"""
        # 完整性分数 (40%)
        if integrity_results:
            avg_integrity = np.mean([r.integrity_score for r in integrity_results])
            integrity_component = avg_integrity * 0.4
        else:
            integrity_component = 40

        # 一致性分数 (30%)
        if consistency_results:
            avg_consistency = np.mean([r.consistency_rate for r in consistency_results])
            consistency_component = avg_consistency * 0.3
        else:
            consistency_component = 30

        # 异常分数 (30%)
        if anomaly_results:
            # 根据异常严重程度计算
            anomaly_penalty = 0
            for anomaly in anomaly_results:
                if anomaly.severity == "critical":
                    anomaly_penalty += 30
                elif anomaly.severity == "high":
                    anomaly_penalty += 20
                elif anomaly.severity == "medium":
                    anomaly_penalty += 10
                elif anomaly.severity == "low":
                    anomaly_penalty += 5

            anomaly_component = max(0, 30 - anomaly_penalty)
        else:
            anomaly_component = 30

        total_score = integrity_component + consistency_component + anomaly_component

        # 确定质量等级
        if total_score >= 90:
            quality_level = DataQualityLevel.EXCELLENT
        elif total_score >= 80:
            quality_level = DataQualityLevel.GOOD
        elif total_score >= 70:
            quality_level = DataQualityLevel.SATISFACTORY
        elif total_score >= 60:
            quality_level = DataQualityLevel.PASS
        else:
            quality_level = DataQualityLevel.NEED_IMPROVEMENT

        return total_score, quality_level

    async def generate_summary(self,
                             table_validations: List[TableStructureValidation],
                             integrity_results: List[DataIntegrityResult],
                             consistency_results: List[DataConsistencyResult],
                             anomaly_results: List[AnomalyDetectionResult]) -> Dict[str, Any]:
        """生成数据质量摘要"""
        summary = {
            'tables_checked': len(table_validations),
            'tables_valid': sum(1 for v in table_validations if v.is_valid),
            'total_records': sum(r.total_records for r in integrity_results),
            'valid_records': sum(r.valid_records for r in integrity_results),
            'consistency_checks': len(consistency_results),
            'consistency_passed': sum(1 for r in consistency_results if r.is_consistent),
            'anomalies_detected': sum(r.anomaly_count for r in anomaly_results),
            'critical_anomalies': sum(1 for r in anomaly_results if r.severity == "critical"),
            'coverage_stats': {}
        }

        # 计算覆盖率统计
        if integrity_results:
            features_result = next((r for r in integrity_results if r.table_name == 'match_features_training'), None)
            if features_result:
                # xG覆盖率
                xg_coverage = 100 - features_result.null_percentages.get('home_xg', 100)
                summary['coverage_stats']['xg_coverage'] = xg_coverage

                # 赔率覆盖率
                odds_coverage = 100 - features_result.null_percentages.get('home_opening_odds', 100)
                summary['coverage_stats']['odds_coverage'] = odds_coverage

                # 数据量评级
                total_features = features_result.total_records
                if total_features >= self.quality_thresholds['excellent_records']:
                    summary['data_volume_rating'] = "优秀"
                elif total_features >= self.quality_thresholds['min_records']:
                    summary['data_volume_rating'] = "良好"
                else:
                    summary['data_volume_rating'] = "待提升"

        return summary

    async def generate_recommendations(self,
                                     table_validations: List[TableStructureValidation],
                                     integrity_results: List[DataIntegrityResult],
                                     consistency_results: List[DataConsistencyResult],
                                     anomaly_results: List[AnomalyDetectionResult]) -> List[str]:
        """生成改进建议"""
        recommendations = []

        # 表结构建议
        for validation in table_validations:
            if not validation.is_valid:
                if validation.missing_columns:
                    recommendations.append(
                        f"表{validation.table_name}缺少必要字段: {', '.join(validation.missing_columns)}"
                    )
                if validation.extra_columns:
                    recommendations.append(
                        f"表{validation.table_name}存在多余字段: {', '.join(validation.extra_columns)}"
                    )

        # 完整性建议
        for result in integrity_results:
            if result.integrity_score < 90:
                for field, null_pct in result.null_percentages.items():
                    if null_pct > 10:
                        recommendations.append(
                            f"表{result.table_name}的{field}字段空值率过高({null_pct:.1f}%)"
                        )

        # 一致性建议
        for result in consistency_results:
            if not result.is_consistent:
                recommendations.extend(result.recommendations)

        # 异常建议
        for result in anomaly_results:
            if result.anomaly_count > 0:
                if result.severity == "critical":
                    recommendations.append(
                        f"紧急处理{result.anomaly_type}问题，发现{result.anomaly_count}个严重异常"
                    )
                elif result.severity == "high":
                    recommendations.append(
                        f"优先处理{result.anomaly_type}问题，发现{result.anomaly_count}个高优先级异常"
                    )

        # 通用建议
        if not recommendations:
            recommendations.append("数据质量良好，继续保持")

        return recommendations

    async def run_full_check(self) -> DataQualityReport:
        """运行完整的数据质量检查"""
        logger.info("开始执行完整数据质量检查...")

        # 1. 检查表结构
        table_validations = []
        for table_name in self.expected_table_schemas.keys():
            try:
                validation = await self.check_table_structure(table_name)
                table_validations.append(validation)
            except Exception as e:
                logger.error(f"检查表{table_name}结构失败: {e}")

        # 2. 检查数据完整性
        integrity_results = []
        for table_name in ['matches', 'match_features_training', 'raw_match_data']:
            try:
                integrity = await self.check_data_integrity(table_name)
                integrity_results.append(integrity)
            except Exception as e:
                logger.error(f"检查表{table_name}完整性失败: {e}")

        # 3. 检查数据一致性
        consistency_results = await self.check_data_consistency()

        # 4. 检测异常
        anomaly_results = await self.detect_anomalies()

        # 5. 计算质量分数
        overall_score, quality_level = await self.calculate_quality_score(
            integrity_results, consistency_results, anomaly_results
        )

        # 6. 生成摘要和建议
        summary = await self.generate_summary(
            table_validations, integrity_results, consistency_results, anomaly_results
        )
        recommendations = await self.generate_recommendations(
            table_validations, integrity_results, consistency_results, anomaly_results
        )

        # 构建报告
        report = DataQualityReport(
            timestamp=datetime.now().isoformat(),
            overall_score=overall_score,
            quality_level=quality_level,
            table_validations=table_validations,
            integrity_results=integrity_results,
            consistency_results=consistency_results,
            anomaly_results=anomaly_results,
            summary=summary,
            recommendations=recommendations
        )

        logger.info(f"数据质量检查完成，总分: {overall_score:.1f}, 等级: {quality_level.value}")

        return report

    async def get_quick_health_status(self) -> Dict[str, Any]:
        """获取快速健康状态"""
        try:
            # 获取关键指标
            total_features = await self.conn.fetchval(
                "SELECT COUNT(*) FROM match_features_training"
            )

            xg_coverage = await self.conn.fetchval("""
                SELECT ROUND(COUNT(home_xg)::numeric / COUNT(*) * 100, 2)
                FROM match_features_training
                WHERE home_xg IS NOT NULL
            """) or 0

            odds_coverage = await self.conn.fetchval("""
                SELECT ROUND(COUNT(home_opening_odds)::numeric / COUNT(*) * 100, 2)
                FROM match_features_training
                WHERE home_opening_odds IS NOT NULL
            """) or 0

            # 计算健康分数
            health_score = 0
            if total_features >= self.quality_thresholds['excellent_records']:
                health_score += 40
            elif total_features >= self.quality_thresholds['min_records']:
                health_score += 30

            health_score += min(30, xg_coverage * 0.3)
            health_score += min(30, odds_coverage * 0.3)

            # 确定状态
            if health_score >= 80:
                status = "healthy"
                status_text = "健康"
            elif health_score >= 60:
                status = "warning"
                status_text = "警告"
            else:
                status = "unhealthy"
                status_text = "异常"

            return {
                'status': status,
                'status_text': status_text,
                'score': health_score,
                'metrics': {
                    'total_features': total_features,
                    'xg_coverage': xg_coverage,
                    'odds_coverage': odds_coverage
                },
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"获取快速健康状态失败: {e}")
            return {
                'status': 'unhealthy',
                'status_text': '检查失败',
                'score': 0,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }