#!/usr/bin/env python3
"""
V41.31 Hash Resolver - 哈希冲突仲裁器

目标：通过 Confidence Score、Mapping Method 版本号、队名相似度等指标
自动识别并清除重复哈希中的冒名顶替者

仲裁原则：
1. Shadow ID (op_) 优先清除
2. Confidence 高的保留
3. Mapping Method 版本号高的保留
4. 队名相似度高的保留

Author: 首席数据架构师
Version: V41.31
Date: 2026-01-13
"""

from dataclasses import dataclass, field
import logging
import re

from thefuzz import fuzz

logger = logging.getLogger(__name__)


@dataclass
class HashConflict:
    """哈希冲突数据结构"""

    hash_value: str
    league_name: str
    records: list[dict] = field(default_factory=list)

    def __post_init__(self):
        """验证冲突数据"""
        if len(self.records) < 2:
            raise ValueError(f"HashConflict requires at least 2 records, got {len(self.records)}")


@dataclass
class ArbitrationResult:
    """仲裁结果数据结构"""

    hash_value: str
    winner: dict | None
    losers: list[dict] = field(default_factory=list)
    arbitration_reason: str = ""


class HashResolver:
    """V41.31 哈希冲突仲裁器

    负责解决同一个哈希对应多个比赛 ID 的冲突问题
    """

    def __init__(self):
        """初始化仲裁器"""
        self.logger = logging.getLogger(__name__)

    def is_shadow_id(self, record: dict) -> bool:
        """检查是否为 Shadow ID

        Args:
            record: 比赛记录

        Returns:
            是否为 Shadow ID
        """
        fotmob_id = record.get("fotmob_id", "")
        return fotmob_id.startswith(("OP_", "op_"))

    def extract_version(self, mapping_method: str) -> float:
        """从 Mapping Method 提取版本号

        Args:
            mapping_method: 映射方法名称

        Returns:
            版本号（浮点数）
        """
        # 匹配模式：v40_3_6 -> 40.36, v40.22 -> 40.22
        match = re.search(r"v?(\d+)\.?(\d+)?(?:\.?(\d+))?", mapping_method)
        if match:
            major = int(match.group(1))
            minor = int(match.group(2)) if match.group(2) else 0
            patch = int(match.group(3)) if match.group(3) else 0
            return major + minor / 100.0 + patch / 10000.0
        return 0.0

    def calculate_team_similarity(self, record1: dict, record2: dict) -> float:
        """计算两个比赛的队名相似度

        Args:
            record1: 比赛 1
            record2: 比赛 2

        Returns:
            相似度 (0-100)
        """
        # 提取队名
        home1 = record1.get("home_team", "").lower().strip()
        away1 = record1.get("away_team", "").lower().strip()
        home2 = record2.get("home_team", "").lower().strip()
        away2 = record2.get("away_team", "").lower().strip()

        # 计算主队和客队的相似度
        home_similarity = fuzz.token_set_ratio(home1, home2)
        away_similarity = fuzz.token_set_ratio(away1, away2)

        # 如果是主客场互换，计算交叉相似度
        cross_similarity1 = fuzz.token_set_ratio(home1, away2)
        cross_similarity2 = fuzz.token_set_ratio(away1, home2)

        # 返回最高相似度
        return max(home_similarity, away_similarity, cross_similarity1, cross_similarity2)

    def resolve_conflict(self, conflict: HashConflict) -> tuple[dict | None, list[dict]]:
        """解决单个哈希冲突

        仲裁原则：
        1. Shadow ID (op_) 优先清除
        2. Confidence 高的保留
        3. Mapping Method 版本号高的保留
        4. 队名相似度高的保留

        Args:
            conflict: 哈希冲突

        Returns:
            (winner, losers) 元组
        """
        records = conflict.records.copy()

        # 第一步：分离 Shadow ID
        shadow_ids = [r for r in records if self.is_shadow_id(r)]
        normal_ids = [r for r in records if not self.is_shadow_id(r)]

        # 如果只有 Shadow ID，无法仲裁
        if not normal_ids:
            self.logger.warning(
                f"Hash {conflict.hash_value}: Only shadow IDs found, cannot arbitrate"
            )
            return None, shadow_ids

        # 第二步：按 Confidence 排序
        normal_ids.sort(key=lambda r: r.get("confidence", 0.0), reverse=True)

        # 第三步：如果有多个最高 confidence 的记录，按 Mapping Method 版本号排序
        max_confidence = normal_ids[0].get("confidence", 0.0)
        top_confidence_records = [
            r for r in normal_ids if r.get("confidence", 0.0) == max_confidence
        ]

        if len(top_confidence_records) > 1:
            # 按 Mapping Method 版本号排序
            top_confidence_records.sort(
                key=lambda r: self.extract_version(r.get("mapping_method", "")), reverse=True
            )

        # 选择 winner
        winner = top_confidence_records[0]
        losers = shadow_ids.copy()

        # 将其他 normal_ids 添加到 losers
        for record in normal_ids:
            if record["fotmob_id"] != winner["fotmob_id"]:
                # 将哈希置空
                record_with_null_hash = record.copy()
                record_with_null_hash["oddsportal_hash"] = None
                losers.append(record_with_null_hash)

        # 将 shadow IDs 的哈希也置空
        for shadow in shadow_ids:
            shadow["oddsportal_hash"] = None

        self.logger.info(
            f"Resolved conflict for hash {conflict.hash_value}: "
            f"winner={winner['fotmob_id']} (confidence={winner.get('confidence', 0)}, "
            f"method={winner.get('mapping_method', 'N/A')}), "
            f"losers={[l['fotmob_id'] for l in losers]}"
        )

        return winner, losers

    def resolve_batch_conflicts(self, conflicts: list[HashConflict]) -> list[ArbitrationResult]:
        """批量解决哈希冲突

        Args:
            conflicts: 哈希冲突列表

        Returns:
            仲裁结果列表
        """
        results = []

        for conflict in conflicts:
            winner, losers = self.resolve_conflict(conflict)

            reason = self._build_arbitration_reason(winner, losers)

            result = ArbitrationResult(
                hash_value=conflict.hash_value,
                winner=winner,
                losers=losers,
                arbitration_reason=reason,
            )
            results.append(result)

        return results

    def _build_arbitration_reason(self, winner: dict | None, losers: list[dict]) -> str:
        """构建仲裁原因说明

        Args:
            winner: 获胜记录
            losers: 失败记录列表

        Returns:
            仲裁原因说明
        """
        if not winner:
            return "No winner (only shadow IDs found)"

        reasons = []

        # 检查是否有 Shadow ID 被清除
        shadow_count = sum(1 for l in losers if self.is_shadow_id(l))
        if shadow_count > 0:
            reasons.append(f"Removed {shadow_count} shadow ID(s)")

        # 检查 confidence 差异
        winner_confidence = winner.get("confidence", 0.0)
        non_shadow_losers = [l for l in losers if not self.is_shadow_id(l)]
        if non_shadow_losers:
            loser_confidence = non_shadow_losers[0].get("confidence", 0.0)
            if winner_confidence > loser_confidence:
                reasons.append(f"Higher confidence ({winner_confidence} > {loser_confidence})")
            elif winner_confidence == loser_confidence:
                # 检查 Mapping Method 版本号
                winner_version = self.extract_version(winner.get("mapping_method", ""))
                loser_version = self.extract_version(non_shadow_losers[0].get("mapping_method", ""))
                if winner_version > loser_version:
                    reasons.append(
                        f"Higher mapping method version ({winner_version} > {loser_version})"
                    )

        return "; ".join(reasons) if reasons else "Default arbitration"


# ========== 便捷函数 ==========


def resolve_hash_conflicts_from_db(conn) -> list[ArbitrationResult]:
    """从数据库扫描并解决所有哈希冲突

    Args:
        conn: 数据库连接

    Returns:
        仲裁结果列表
    """
    from psycopg2.extras import RealDictCursor

    resolver = HashResolver()

    # 查询所有重复哈希
    query = """
    SELECT
        mm.oddsportal_hash,
        mm.league_name,
        array_agg(mm.fotmob_id) as fotmob_ids
    FROM matches_mapping mm
    WHERE mm.season = '2023/2024'
      AND mm.oddsportal_hash IS NOT NULL
      AND LENGTH(mm.oddsportal_hash) = 8
      AND mm.fotmob_id IS NOT NULL
    GROUP BY mm.oddsportal_hash, mm.league_name
    HAVING COUNT(DISTINCT mm.fotmob_id) > 1
    ORDER BY mm.oddsportal_hash;
    """

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(query)
        duplicate_hashes = cur.fetchall()

    conflicts = []

    # 为每个重复哈希创建 HashConflict 对象
    for dup in duplicate_hashes:
        hash_value = dup["oddsportal_hash"]
        league_name = dup["league_name"]
        dup["fotmob_ids"]

        # 获取每个记录的详细信息
        records_query = """
        SELECT
            fotmob_id,
            home_team,
            away_team,
            oddsportal_hash,
            confidence,
            mapping_method
        FROM matches_mapping
        WHERE oddsportal_hash = %s
          AND league_name = %s
        ORDER BY created_at;
        """

        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(records_query, (hash_value, league_name))
            records = [dict(row) for row in cur.fetchall()]

        conflict = HashConflict(hash_value=hash_value, league_name=league_name, records=records)
        conflicts.append(conflict)

    # 解决所有冲突
    return resolver.resolve_batch_conflicts(conflicts)
