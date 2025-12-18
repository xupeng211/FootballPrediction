"""
FotMob 与 Titan007 比赛 ID 对齐服务

使用 rapidfuzz 实现模糊匹配算法，解决不同数据源之间比赛实体 (Entity) 的对齐问题。
"""

from typing import List, Optional
from datetime import datetime

from rapidfuzz import fuzz

from src.schemas.titan import FotMobMatchInfo, TitanMatchInfo, MatchAlignmentResult


class MatchAlignmentService:
    """
    比赛ID对齐服务

    核心功能：将FotMob的比赛ID与Titan007的比赛ID进行对齐。
    使用模糊匹配算法处理队名差异（如"Man City" vs "Manchester City"）。
    """

    def __init__(self, min_confidence_score: float = 80.0):
        """
        初始化对齐服务

        Args:
            min_confidence_score: 最小置信度分数阈值 (0-100)
        """
        self.min_confidence_score = min_confidence_score

    def align_match(
        self, fotmob_match: FotMobMatchInfo, titan_match: TitanMatchInfo
    ) -> Optional[MatchAlignmentResult]:
        """
        对齐单个比赛

        算法流程：
        1. 首先检查日期是否匹配（精确到日）
        2. 分别匹配主队和客队名称
        3. 计算综合置信度分数
        4. 返回对齐结果或None（不匹配）

        Args:
            fotmob_match: FotMob比赛信息
            titan_match: Titan007比赛信息

        Returns:
            MatchAlignmentResult: 对齐结果（包含置信度分数）
            None: 当日期不匹配或置信度低于阈值时返回None
        """
        # Step 1: 日期匹配检查（精确到日）
        if not self._dates_match(fotmob_match.match_date, titan_match.match_date):
            return None

        # Step 2: 队名模糊匹配
        home_score = self._calculate_team_similarity(
            fotmob_match.home_team, titan_match.home_team.name
        )

        away_score = self._calculate_team_similarity(
            fotmob_match.away_team, titan_match.away_team.name
        )

        # Step 3: 计算综合置信度分数
        # 采用加权平均：主队 50% + 客队 50%
        confidence_score = home_score * 0.5 + away_score * 0.5

        # Step 4: 阈值检查
        if confidence_score < self.min_confidence_score:
            return None

        # Step 5: 返回对齐结果
        return MatchAlignmentResult(
            fotmob_id=fotmob_match.fotmob_id,
            titan_id=titan_match.match_id,
            home_team_fotmob=fotmob_match.home_team,
            home_team_titan=titan_match.home_team.name,
            away_team_fotmob=fotmob_match.away_team,
            away_team_titan=titan_match.away_team.name,
            confidence_score=round(confidence_score, 2),
            match_date=fotmob_match.match_date,
            is_aligned=True,
        )

    def batch_align(
        self, fotmob_matches: List[FotMobMatchInfo], titan_matches: List[TitanMatchInfo]
    ) -> List[MatchAlignmentResult]:
        """
        批量对齐多个比赛

        优化算法：
        1. 按日期分组处理，减少不必要的比较
        2. 优先匹配高置信度结果
        3. 使用rapidfuzz的批量匹配优化

        Args:
            fotmob_matches: 多个FotMob比赛信息
            titan_matches: 多个Titan007比赛信息

        Returns:
            List[MatchAlignmentResult]: 对齐结果列表（仅返回对齐成功的）
        """
        results: List[MatchAlignmentResult] = []

        # Step 1: 按日期分组 Titan matches
        titan_by_date = self._group_matches_by_date(titan_matches)

        # Step 2: 遍历每个 FotMob 比赛
        for fotmob_match in fotmob_matches:
            fotmob_date = fotmob_match.match_date.date()

            # Step 3: 获取相同日期的 Titan 比赛
            candidate_titan_matches = titan_by_date.get(fotmob_date, [])
            if not candidate_titan_matches:
                continue  # 无候选，跳过

            # Step 4: 单场比赛的最佳匹配
            best_match: Optional[MatchAlignmentResult] = None
            best_score = 0.0

            for titan_match in candidate_titan_matches:
                match_result = self.align_match(fotmob_match, titan_match)
                if match_result and match_result.confidence_score > best_score:
                    best_match = match_result
                    best_score = match_result.confidence_score

            # Step 5: 添加最佳匹配结果
            if best_match:
                results.append(best_match)

        # Step 6: 按置信度分数降序排序
        results.sort(key=lambda x: x.confidence_score, reverse=True)

        return results

    def _dates_match(self, fotmob_date: datetime, titan_date: str) -> bool:
        """
        检查两个日期是否匹配（精确到日）

        Args:
            fotmob_date: FotMob日期（datetime对象）
            titan_date: Titan日期（字符串格式YYYY-MM-DD，或datetime对象）

        Returns:
            bool: 日期是否相同
        """
        try:
            # 处理 titan_date 可能是字符串或 datetime 的情况
            if isinstance(titan_date, str):
                # 将 Titan 日期字符串转换为 datetime
                titan_datetime = datetime.strptime(titan_date, "%Y-%m-%d")
            elif isinstance(titan_date, datetime):
                # 已经是 datetime 对象
                titan_datetime = titan_date
            else:
                # 未知类型，返回 False
                return False

            # 比较日期部分（忽略时间）
            return fotmob_date.date() == titan_datetime.date()
        except (ValueError, AttributeError):
            # 日期格式异常或类型错误
            return False

    def _calculate_team_similarity(self, name1: str, name2: str) -> float:
        """
        计算两个队名的相似度分数

        使用 rapidfuzz 的 token_sort_ratio 算法：
        - 忽略单词顺序
        - 对缩写（如 "Man City" vs "Manchester City"）有较好效果
        - 返回 0-100 的分数

        Args:
            name1: 第一个队名
            name2: 第二个队名

        Returns:
            float: 相似度分数 (0-100)
        """
        # Step 1: 预处理 - 统一小写
        name1_processed = name1.lower().strip()
        name2_processed = name2.lower().strip()

        # Step 2: 计算相似度
        # 使用 token_sort_ratio：忽略单词顺序，适合处理 "Manchester City" vs "Man City"
        similarity_score = fuzz.token_sort_ratio(name1_processed, name2_processed)

        return float(similarity_score)

    def _group_matches_by_date(self, titan_matches: List[TitanMatchInfo]) -> dict:
        """
        按日期分组 Titan 比赛

        Args:
            titan_matches: Titan 比赛列表

        Returns:
            dict: 日期 -> 比赛列表的映射
        """
        grouped = {}

        for match in titan_matches:
            # match.match_date 可能是字符串或 datetime 对象
            if isinstance(match.match_date, str):
                match_date = datetime.strptime(match.match_date, "%Y-%m-%d").date()
            elif isinstance(match.match_date, datetime):
                match_date = match.match_date.date()
            else:
                continue  # 跳过无效日期

            if match_date not in grouped:
                grouped[match_date] = []

            grouped[match_date].append(match)

        return grouped

    def set_min_confidence_score(self, score: float):
        """
        动态调整最小置信度分数阈值

        Args:
            score: 新的阈值 (0-100)
        """
        if not (0 <= score <= 100):
            raise ValueError("置信度分数必须在 0-100 之间")

        self.min_confidence_score = score

    def get_alignment_stats(self, results: List[MatchAlignmentResult]) -> dict:
        """
        获取对齐统计信息

        Args:
            results: 对齐结果列表

        Returns:
            dict: 统计信息
        """
        if not results:
            return {
                "total_aligned": 0,
                "average_confidence": 0.0,
                "high_confidence_count": 0,  # > 90
                "medium_confidence_count": 0,  # 80-90
            }

        confidence_scores = [r.confidence_score for r in results]

        stats = {
            "total_aligned": len(results),
            "average_confidence": round(
                sum(confidence_scores) / len(confidence_scores), 2
            ),
            "high_confidence_count": len([s for s in confidence_scores if s > 90.0]),
            "medium_confidence_count": len(
                [s for s in confidence_scores if 80.0 <= s <= 90.0]
            ),
        }

        return stats
