"""
RefereeProcessor - 裁判因子处理器（V21.0 深度爆破版）
======================================================

负责提取裁判行为学特征，用于提升平局预测精度:
    - 裁判严格度（历史场均黄牌/红牌数）
    - 点球偏向度（ref_penalty_bias - "点球狂人"型裁判）
    - 主场偏向度（裁判国籍与主队关系）
    - 裁判姓名哈希（ref_name_hash - 用于 Embedding）

设计模式:
    - Lookup Pattern: 从裁判数据库查询历史数据
    - Scoring System: 将裁判风格量化为评分
    - Hash Encoding: 裁判姓名哈希化

作者: FootballPrediction Architecture Team
版本: V21.0-deep-blowout
"""

import hashlib
import logging
from typing import Any

from ..base import BaseProcessor, ProcessorConfig, ProcessorResult
from ..models import MatchContext, MatchData

logger = logging.getLogger(__name__)


class RefereeProcessorConfig(ProcessorConfig):
    """
    RefereeProcessor 配置

    Attributes:
        enable_strictness_analysis: 是否启用严格度分析
        enable_home_bias_analysis: 是否启用主场偏向分析
        enable_penalty_bias: 是否启用点球偏向分析
        enable_name_hashing: 是否启用裁判姓名哈希
        default_strictness: 默认严格度评分
    """

    enable_strictness_analysis: bool = True
    enable_home_bias_analysis: bool = True
    enable_penalty_bias: bool = True
    enable_name_hashing: bool = True
    default_strictness: float = 0.5  # 0-1, 0.5 为中等


class RefereeProcessor(BaseProcessor[MatchData]):
    """
    裁判行为学处理器（V21.0 深度爆破版）

    职责:
        1. 分析裁判严格度（基于历史数据）
        2. 评估裁判主场偏向度（裁判国籍与主队关系）
        3. 计算点球偏向度（"点球狂人"型裁判识别）
        4. 生成裁判姓名哈希（用于 Embedding 学习）

    特征输出:
        - ref_is_strict: 裁判严格度（0-1）
        - ref_penalty_bias: 点球偏向度（-1 到 1）
        - ref_home_advantage: 主场偏向度（-1 到 1）
        - ref_name_hash: 裁判姓名哈希（int32）
        - ref_nationality_match: 裁判国籍与主队匹配度
        - ref_style_encoded: 裁判风格编码（0-8）

    平局预测价值:
        - 严格裁判 → 更多犯规 → 更多定位球 → 更高平局概率
        - 点球狂人 → 更多个球 → 比分不确定性增加
        - 主场偏向 → 打破平衡 → 降低平局概率

    Example:
        >>> processor = RefereeProcessor()
        >>> result = processor.execute(match_data)
        >>> print(result.data["ref_is_strict"])
        0.85
    """

    processor_name = "RefereeProcessor"
    processor_version = "21.0-deep"
    priority = 40

    # 已知"点球狂人"型裁判名单（英超）
    KNOWN_PENALTY_REFEREES = {
        "michael oliver",
        "anthony taylor",
        "paul tierney",
        "chris kavanagh",
        "stuart attwell",
        "robert jones",
        "david coote",
        "jarred gillett",
        "darren england",
        "michael salisbury",
        "thomas Bramall",
        "john brooks",
    }

    # 已知严格裁判名单（高黄牌率）
    KNOWN_STRICT_REFEREES = {
        "michael oliver",
        "anthony taylor",
        "paul tierney",
        "andrew madley",
        "robert jones",
        "david coote",
    }

    def __init__(self, config: RefereeProcessorConfig | None = None) -> None:
        super().__init__(config or RefereeProcessorConfig())
        self.config: RefereeProcessorConfig = self.config

        # 裁判数据库（预留，可从外部加载）
        self._referee_db: dict[str, dict[str, float]] = {}

    def process(self, data: MatchData, context: Any) -> ProcessorResult:
        """
        提取裁判特征

        Args:
            data: 比赛数据
            context: 处理上下文

        Returns:
            ProcessorResult: 包含裁判特征的处理器结果
        """
        features: dict[str, float] = {}
        warnings: list[str] = []

        try:
            # 获取比赛上下文
            match_context = data.context or MatchContext()
            referee_name = match_context.referee_name or "Unknown"

            # 裁判姓名哈希（用于 Embedding）
            if self.config.enable_name_hashing:
                name_hash = self._hash_referee_name(referee_name)
                features["ref_name_hash"] = float(name_hash)

            # 裁判严格度（基于历史数据库或名单）
            if self.config.enable_strictness_analysis:
                strictness = self._compute_referee_strictness(referee_name, match_context.referee_strictness)
                features["ref_is_strict"] = strictness

                # 二分类特征（便于决策树切分）
                features["ref_is_strict_binary"] = 1.0 if strictness > 0.6 else 0.0

            # 点球偏向度（"点球狂人"识别）
            if self.config.enable_penalty_bias:
                penalty_bias = self._compute_penalty_bias(referee_name)
                features["ref_penalty_bias"] = penalty_bias

                # 二分类特征
                features["ref_is_penalty_prone"] = 1.0 if penalty_bias > 0.5 else 0.0

            # 裁判主场偏向度（国籍匹配分析）
            if self.config.enable_home_bias_analysis:
                home_advantage = self._compute_home_advantage(referee_name, data.home_team, data.league_id)
                features["ref_home_advantage"] = home_advantage

                # 裁判国籍与主队匹配度
                nationality_match = self._compute_nationality_match(referee_name, data.home_team)
                features["ref_nationality_match"] = nationality_match

            # 裁判风格编码（综合编码）
            features["ref_style_encoded"] = self._encode_referee_style(
                features.get("ref_is_strict", 0.5),
                features.get("ref_home_advantage", 0.0),
                features.get("ref_penalty_bias", 0.0),
            )

            # 裁判经验等级（基于姓名知名度估算）
            experience_level = self._estimate_experience_level(referee_name)
            features["ref_experience_level"] = experience_level

            result = ProcessorResult.success_result(
                data=features,
                metadata={
                    "feature_count": len(features),
                    "referee_name": referee_name,
                    "referee_id": match_context.referee_id or "unknown",
                },
            )

            # 添加警告
            for warning in warnings:
                result.with_warning(warning)

            return result

        except Exception as e:
            logger.error(f"RefereeProcessor failed for match {data.match_id}: {e}")
            return ProcessorResult.failure_result(str(e))

    def _hash_referee_name(self, name: str) -> int:
        """
        对裁判姓名进行哈希编码

        使用 MD5 哈希并转换为有符号 int32（便于 Embedding 学习）

        Args:
            name: 裁判姓名

        Returns:
            哈希值（int32 范围）
        """
        # 标准化姓名（小写、去空格）
        normalized = name.lower().strip().replace(" ", "")

        # MD5 哈希
        hash_bytes = hashlib.md5(normalized.encode()).digest()

        # 取前 4 字节转换为 int32
        hash_int = int.from_bytes(hash_bytes[:4], byteorder="big", signed=True)

        return hash_int

    def _compute_referee_strictness(self, referee_name: str, provided_strictness: float | None) -> float:
        """
        计算裁判严格度

        基于:
            1. API 提供的严格度数据
            2. 已知严格裁判名单
            3. 历史数据库

        Args:
            referee_name: 裁判姓名
            provided_strictness: API 提供的严格度

        Returns:
            严格度评分（0-1，1 为最严格）
        """
        # 优先使用 API 提供的数据
        if provided_strictness is not None:
            return round(provided_strictness, 4)

        # 查询已知严格裁判名单
        name_lower = referee_name.lower().strip()
        if name_lower in self.KNOWN_STRICT_REFEREES:
            return 0.85  # 高严格度

        # 查询裁判数据库
        if name_lower in self._referee_db:
            return self._referee_db[name_lower].get("strictness", self.config.default_strictness)

        # 使用默认值
        logger.debug(f"Referee strictness not found for {referee_name}, using default")
        return self.config.default_strictness

    def _compute_penalty_bias(self, referee_name: str) -> float:
        """
        计算点球偏向度（"点球狂人"识别）

        基于:
            1. 已知点球裁判名单
            2. 历史点球率数据

        Args:
            referee_name: 裁判姓名

        Returns:
            点球偏向度（0-1，1 为高度倾向于判点球）
        """
        name_lower = referee_name.lower().strip()

        # 查询已知点球裁判名单
        if name_lower in self.KNOWN_PENALTY_REFEREES:
            return 0.75  # 高点球偏向

        # 查询裁判数据库
        if name_lower in self._referee_db:
            historical_rate = self._referee_db[name_lower].get("penalty_rate", 0.0)
            return round(historical_rate, 4)

        # 默认中等偏向
        return 0.3

    def _compute_home_advantage(self, referee_name: str, home_team: str, league_id: str) -> float:
        """
        计算裁判主场偏向度

        基于:
            1. 裁判国籍与主队国家的匹配度
            2. 历史主场胜率偏差

        Args:
            referee_name: 裁判姓名
            home_team: 主队名称
            league_id: 联赛 ID

        Returns:
            主场偏向度（-1 到 1，1 为极度偏向主队，-1 为偏向客队）
        """
        name_lower = referee_name.lower().strip()

        # 查询裁判数据库
        if name_lower in self._referee_db:
            home_bias = self._referee_db[name_lower].get("home_bias", 0.0)
            return round(home_bias, 4)

        # 默认无偏向
        return 0.0

    def _compute_nationality_match(self, referee_name: str, home_team: str) -> float:
        """
        计算裁判国籍与主队匹配度

        用于跨国赛事（如欧冠），裁判与主队同国籍可能存在潜在偏向

        Args:
            referee_name: 裁判姓名
            home_team: 主队名称

        Returns:
            匹配度（0-1，1 为完全匹配）
        """
        # 简化版本：基于姓名后缀推断国籍
        # 实际应用需要完整裁判国籍数据库

        name_lower = referee_name.lower().strip()

        # 英格兰/英国裁判特征
        english_suffixes = [
            "smith",
            "jones",
            "taylor",
            "brown",
            "wilson",
            "evans",
            "thomas",
            "johnson",
            "roberts",
            "walker",
        ]

        # 检查裁判姓名是否包含英国姓氏特征
        has_english_name = any(name_lower.endswith(suffix) for suffix in english_suffixes)

        # 检查主队是否为英格兰球队（简化判断）
        is_english_team = any(
            keyword in home_team.lower()
            for keyword in [
                "united",
                "city",
                "liverpool",
                "chelsea",
                "arsenal",
                "tottenham",
                "newcastle",
                "aston villa",
                "everton",
            ]
        )

        # 如果裁判和主队都是英格兰背景，返回高匹配度
        if has_english_name and is_english_team:
            return 0.8

        # 默认无匹配
        return 0.0

    def _encode_referee_style(self, strictness: float, home_bias: float, penalty_bias: float) -> int:
        """
        将裁判风格编码为整数

        编码规则（27 种组合）:
            - 严格度（3 类）× 主场偏向（3 类）× 点球偏向（3 类）
            - 取值范围: 0-26

        Args:
            strictness: 严格度（0-1）
            home_bias: 主场偏向（-1 到 1）
            penalty_bias: 点球偏向（0-1）

        Returns:
            风格编码（0-26）
        """
        # 严格度分类
        if strictness < 0.33:
            strict_cat = 0  # 宽松
        elif strictness < 0.66:
            strict_cat = 1  # 中等
        else:
            strict_cat = 2  # 严格

        # 主场偏向分类
        if home_bias < -0.2:
            bias_cat = 0  # 偏向客队
        elif home_bias > 0.2:
            bias_cat = 2  # 偏向主队
        else:
            bias_cat = 1  # 无偏向

        # 点球偏向分类
        if penalty_bias < 0.3:
            pen_cat = 0  # 低
        elif penalty_bias < 0.6:
            pen_cat = 1  # 中
        else:
            pen_cat = 2  # 高

        # 组合编码（3 进制）
        return strict_cat * 9 + bias_cat * 3 + pen_cat

    def _estimate_experience_level(self, referee_name: str) -> float:
        """
        估算裁判经验等级

        基于姓名知名度（出现频率）估算经验水平

        Args:
            referee_name: 裁判姓名

        Returns:
            经验等级（0-1，1 为顶级裁判）
        """
        name_lower = referee_name.lower().strip()

        # 顶级裁判（英超主裁）
        elite_referees = {
            "michael oliver",
            "anthony taylor",
            "paul tierney",
            "andrew madley",
            "craig pawson",
            "michael jones",
            "chris kavanagh",
            "stuart attwell",
            "robert jones",
            "david coote",
            "jarred gillett",
            "darran england",
        }

        # 资深裁判
        senior_referees = {
            "thomas Bramall",
            "michael salisbury",
            "john brooks",
            "neil swarbrick",
            "kevin friend",
            "martin atkinson",
            "mike dean",
            "jon moss",
            "lee mason",
        }

        if name_lower in elite_referees:
            return 1.0  # 顶级
        if name_lower in senior_referees:
            return 0.7  # 资深
        return 0.4  # 普通/新人

    def load_referee_database(self, db_path: str) -> None:
        """
        加载裁判数据库（预留接口）

        Args:
            db_path: 数据库文件路径

        Note: 此方法为预留接口，用于从外部文件加载裁判历史数据
        """
        logger.info(f"Loading referee database from {db_path}")

    def get_feature_schema(self) -> dict[str, type]:
        """获取输出特征的 Schema"""
        return {
            "ref_is_strict": float,
            "ref_is_strict_binary": float,
            "ref_penalty_bias": float,
            "ref_is_penalty_prone": float,
            "ref_home_advantage": float,
            "ref_nationality_match": float,
            "ref_name_hash": float,
            "ref_style_encoded": int,
            "ref_experience_level": float,
        }
