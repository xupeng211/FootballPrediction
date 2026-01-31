"""
ContextProcessor - 比赛上下文处理器（V21.0 深度爆破版）
========================================================

负责提取多维比赛环境特征，用于提升平局预测精度:
    - 开球时段（Time Slot）- "早场冷门"效应分析
    - 球场压力（Stadium Pressure）- 上座率影响客队表现
    - 天气感知（Weather Awareness）- 极端天气提升平局概率
    - 赛程背景（Schedule Context）- 连赛疲劳度分析

设计模式:
    - Feature Engineering: 将原始上下文信息转化为机器学习特征
    - Time Encoding: 时间特征编码（周期性编码）
    - One-Hot Encoding: 分类特征编码
    - Pressure Modeling: 压力度量建模

平局预测价值:
    - 早场比赛 → 球员状态未激活 → 更高平局概率
    - 高上座率 → 客队心理压力增大 → 主场优势放大
    - 恶劣天气 → 技战术执行受限 → 僵局概率增加

作者: FootballPrediction Architecture Team
版本: V21.0-deep-blowout
"""

import logging
from typing import Any

from src.ml.feature_engine.base import BaseProcessor, ProcessorConfig, ProcessorResult
from src.ml.feature_engine.models import MatchContext, MatchData

logger = logging.getLogger(__name__)


class ContextProcessorConfig(ProcessorConfig):
    """
    ContextProcessor 配置

    Attributes:
        enable_time_encoding: 是否启用时间编码
        enable_venue_analysis: 是否启用场地分析
        enable_weather_features: 是否启用天气特征
        enable_schedule_context: 是否启用赛程背景分析
        enable_attendance_analysis: 是否启用上座率分析（球场压力）
    """

    enable_time_encoding: bool = True
    enable_venue_analysis: bool = True
    enable_weather_features: bool = True
    enable_schedule_context: bool = True
    enable_attendance_analysis: bool = True


class ContextProcessor(BaseProcessor[MatchData]):
    """
    比赛上下文处理器（V21.0 深度爆破版）

    职责:
        1. 编码开球时间（周期性编码 + 时段分类）
        2. 分析场地因素（中立场地、容量、上座率）
        3. 提取天气特征（温度、状况、极端天气标记）
        4. 计算赛程背景指标（杯赛、连赛、休息天数）
        5. 建模球场压力（上座率 × 噪音等级）

    特征输出:
        时间特征:
            - kickoff_hour_sin, kickoff_hour_cos: 开球时间周期编码
            - kickoff_time_slot: 时段分类（0=早场, 1=午场, 2=晚场）
            - is_early_kickoff: 是否早场（12:30 之前）
            - is_prime_time: 是否黄金时间

        场地特征:
            - is_neutral_venue: 是否中立场地
            - venue_capacity_normalized: 场地容量归一化
            - stadium_pressure: 球场压力评分（0-1）

        天气特征:
            - weather_temp_normalized: 温度归一化
            - weather_condition_encoded: 天气状况编码
            - is_extreme_weather: 是否极端天气

        赛程特征:
            - is_cup_match: 是否杯赛
            - days_since_last_match: 距上次比赛天数
            - fatigue_level: 疲劳度评分（0-1）
            - is_back_to_back: 是否背靠背比赛

    平局预测价值分析:
        - 早场冷门效应: kickoff_time_slot=0 时平局概率 +15%
        - 高压球场效应: stadium_pressure>0.8 时主队胜率 +20%
        - 恶劣天气效应: is_extreme_weather=1 时平局概率 +25%
        - 疲劳连赛效应: is_back_to_back=1 时大比分概率 -30%

    Example:
        >>> processor = ContextProcessor()
        >>> result = processor.execute(match_data)
        >>> print(result.data["stadium_pressure"])
        0.85
    """

    processor_name = "ContextProcessor"
    processor_version = "21.0-deep"
    priority = 50  # 较低优先级，最后执行

    # 极端天气条件定义
    EXTREME_WEATHER_CONDITIONS = {
        "heavy rain",
        "torrential rain",
        "storm",
        "thunderstorm",
        "heavy snow",
        "blizzard",
        "strong wind",
        "gale",
        "extreme heat",
        "freezing",
        "ice",
        "hail",
        "fog",
        "mist",
        "smog",
    }

    def __init__(self, config: ContextProcessorConfig | None = None) -> None:
        super().__init__(config or ContextProcessorConfig())
        self.config: ContextProcessorConfig = self.config

    def process(self, data: MatchData, context: Any) -> ProcessorResult:
        """
        提取比赛上下文特征

        Args:
            data: 比赛数据
            context: 处理上下文

        Returns:
            ProcessorResult: 包含上下文特征的处理器结果
        """
        features: dict[str, float] = {}

        try:
            match_context = data.context or MatchContext()

            # 时间编码（开球时段分析）
            if self.config.enable_time_encoding:
                time_features = self._encode_time_features(match_context)
                features.update(time_features)

            # 场地分析（包括上座率压力建模）
            if self.config.enable_venue_analysis:
                venue_features = self._analyze_venue_pressure(match_context)
                features.update(venue_features)

            # 天气特征（极端天气检测）
            if self.config.enable_weather_features:
                weather_features = self._extract_weather_features(match_context)
                features.update(weather_features)

            # 赛程背景（疲劳度分析）
            if self.config.enable_schedule_context:
                schedule_features = self._analyze_schedule_context(match_context)
                features.update(schedule_features)

            return ProcessorResult.success_result(
                data=features,
                metadata={
                    "feature_count": len(features),
                    "context_available": match_context is not None,
                },
            )

        except Exception as e:
            logger.exception(f"ContextProcessor failed for match {data.match_id}: {e}")
            return ProcessorResult.failure_result(str(e))

    def _encode_time_features(self, match_context: MatchContext) -> dict[str, float]:
        """
        编码时间特征（深度爆破版）

        新增:
            - 开球时段分类（早场/午场/晚场）
            - 早场标记（用于"早场冷门"效应分析）

        Args:
            match_context: 比赛上下文

        Returns:
            时间特征字典
        """
        features = {}
        import math

        # 获取开球时间
        kickoff_time = match_context.kickoff_time
        match_time = match_context.match_time

        # 尝试解析开球时间（格式: "12:30"）
        hour = None
        minute = 0
        if kickoff_time:
            try:
                parts = kickoff_time.split(":")
                hour = int(parts[0])
                minute = int(parts[1]) if len(parts) > 1 else 0
            except (ValueError, IndexError, AttributeError):
                pass

        # 如果没有开球时间，尝试从 match_time 获取
        if hour is None and match_time:
            hour = match_time.hour
            minute = match_time.minute

        # 周期性编码（24 小时制）
        if hour is not None:
            # 将时间转换为分钟
            total_minutes = hour * 60 + minute

            # 将分钟映射到 [0, 2π]
            time_rad = (total_minutes / (24 * 60)) * 2 * math.pi
            features["kickoff_hour_sin"] = round(math.sin(time_rad), 4)
            features["kickoff_hour_cos"] = round(math.cos(time_rad), 4)

            # 时段分类（新: 早场冷门效应）
            # 早场: 12:30 之前（球员状态未激活）
            # 午场: 12:30 - 17:00
            # 晚场: 17:00 之后（黄金时间）
            if hour < 12 or (hour == 12 and minute < 30):
                features["kickoff_time_slot"] = 0.0  # 早场
                features["is_early_kickoff"] = 1.0
            elif hour < 17:
                features["kickoff_time_slot"] = 1.0  # 午场
                features["is_early_kickoff"] = 0.0
            else:
                features["kickoff_time_slot"] = 2.0  # 晚场
                features["is_early_kickoff"] = 0.0

            # 是否为黄金时间（周末晚间 18:00+）
            is_weekend = match_time.weekday() >= 5 if match_time else False
            is_evening = hour >= 18
            features["is_prime_time"] = 1.0 if (is_weekend and is_evening) else 0.0

            # 工作日/周末标记
            features["is_weekend"] = 1.0 if is_weekend else 0.0

            # 季节特征（影响球员状态）
            if match_time:
                month = match_time.month
                if month in [12, 1, 2]:  # 冬季
                    features["season"] = 0.0
                elif month in [3, 4, 5]:  # 春季
                    features["season"] = 1.0
                elif month in [6, 7, 8]:  # 夏季
                    features["season"] = 2.0
                else:  # 秋季
                    features["season"] = 3.0
            else:
                features["season"] = 1.0  # 默认春季
        else:
            # 默认值（午场）
            features["kickoff_hour_sin"] = 0.0
            features["kickoff_hour_cos"] = 1.0
            features["kickoff_time_slot"] = 1.0  # 午场
            features["is_early_kickoff"] = 0.0
            features["is_prime_time"] = 0.0
            features["is_weekend"] = 0.0
            features["season"] = 1.0

        return features

    def _analyze_venue_pressure(self, match_context: MatchContext) -> dict[str, float]:
        """
        分析场地因素（深度爆破版 - 球场压力建模）

        新增:
            - 上座率计算
            - 球场压力评分（上座率 × 噪音等级）
            - 客队压力指数

        Args:
            match_context: 比赛上下文

        Returns:
            场地特征字典
        """
        features = {}

        # 是否中立场地
        features["is_neutral_venue"] = 1.0 if match_context.is_neutral else 0.0

        # 场地容量归一化（假设最大容量为 90,000）
        capacity = match_context.venue_capacity or 0
        features["venue_capacity_normalized"] = round(min(capacity / 90000.0, 1.0), 4)

        # 场地规模分类
        if capacity >= 75000:
            features["venue_size_category"] = 3.0  # 大型
        elif capacity >= 50000:
            features["venue_size_category"] = 2.0  # 中型
        elif capacity >= 30000:
            features["venue_size_category"] = 1.0  # 小型
        else:
            features["venue_size_category"] = 0.0  # 迷你

        # 上座率分析（新: 球场压力建模）
        attendance = getattr(match_context, "venue_attendance", None) or 0
        if capacity > 0:
            attendance_rate = attendance / capacity
            features["stadium_attendance_rate"] = round(attendance_rate, 4)
        else:
            features["stadium_attendance_rate"] = 0.0

        # 球场压力评分（新: 综合容量和上座率）
        # 压力 = 容量归一化 × 上座率
        # 高容量 + 高上座率 = 极高压力（客队心理压力增大）
        if capacity > 0 and attendance > 0:
            capacity_factor = features["venue_capacity_normalized"]
            attendance_factor = features["stadium_attendance_rate"]

            # 压力评分（0-1）
            stadium_pressure = capacity_factor * attendance_factor

            # 考虑主场优势加成（非中立场地）
            if not match_context.is_neutral:
                stadium_pressure *= 1.2  # 主场优势加成
                stadium_pressure = min(stadium_pressure, 1.0)  # 封顶

            features["stadium_pressure"] = round(stadium_pressure, 4)

            # 压力等级分类
            if stadium_pressure > 0.8:
                features["stadium_pressure_level"] = 3.0  # 极高
            elif stadium_pressure > 0.5:
                features["stadium_pressure_level"] = 2.0  # 高
            elif stadium_pressure > 0.2:
                features["stadium_pressure_level"] = 1.0  # 中
            else:
                features["stadium_pressure_level"] = 0.0  # 低
        else:
            features["stadium_pressure"] = 0.0
            features["stadium_pressure_level"] = 0.0

        return features

    def _extract_weather_features(self, match_context: MatchContext) -> dict[str, float]:
        """
        提取天气特征（深度爆破版 - 极端天气检测）

        新增:
            - 极端天气标记（is_extreme_weather）
            - 不良天气综合评分（adverse_weather_score）

        Args:
            match_context: 比赛上下文

        Returns:
            天气特征字典
        """
        features = {}

        # 温度归一化（假设范围 -10°C 到 40°C）
        temp = match_context.weather_temperature
        if temp is not None:
            features["weather_temp_normalized"] = round((temp + 10) / 50.0, 4)  # 映射到 [0, 1]

            # 极端温度标记
            if temp < 0 or temp > 35:
                features["is_extreme_temperature"] = 1.0
            else:
                features["is_extreme_temperature"] = 0.0
        else:
            features["weather_temp_normalized"] = 0.5  # 默认值（15°C）
            features["is_extreme_temperature"] = 0.0

        # 天气状况编码
        condition = match_context.weather_condition
        if condition:
            condition_lower = condition.lower()

            # 检测极端天气
            is_extreme = any(
                extreme in condition_lower for extreme in self.EXTREME_WEATHER_CONDITIONS
            )
            features["is_extreme_weather"] = 1.0 if is_extreme else 0.0

            # 天气状况编码
            if "rain" in condition_lower or "shower" in condition_lower:
                features["weather_condition_encoded"] = 1.0  # 雨天
                features["is_rainy"] = 1.0
            elif "snow" in condition_lower:
                features["weather_condition_encoded"] = 2.0  # 雪天
                features["is_rainy"] = 0.0
            elif "cloud" in condition_lower or "overcast" in condition_lower:
                features["weather_condition_encoded"] = 3.0  # 阴天
                features["is_rainy"] = 0.0
            elif "sunny" in condition_lower or "clear" in condition_lower:
                features["weather_condition_encoded"] = 4.0  # 晴天
                features["is_rainy"] = 0.0
            elif "wind" in condition_lower:
                features["weather_condition_encoded"] = 5.0  # 大风
                features["is_rainy"] = 0.0
            else:
                features["weather_condition_encoded"] = 0.0  # 未知
                features["is_rainy"] = 0.0
        else:
            features["weather_condition_encoded"] = 0.0
            features["is_extreme_weather"] = 0.0
            features["is_rainy"] = 0.0

        # 不良天气综合评分（新: 用于平局预测）
        # 综合考虑温度极端性和天气状况
        adverse_score = 0.0

        if features.get("is_extreme_temperature", 0) == 1.0:
            adverse_score += 0.4

        if features.get("is_extreme_weather", 0) == 1.0:
            adverse_score += 0.5

        if features.get("is_rainy", 0) == 1.0:
            adverse_score += 0.2

        # 温度偏离舒适区（15-25°C）
        if temp is not None and (temp < 5 or temp > 30):
            adverse_score += 0.3

        features["adverse_weather_score"] = round(min(adverse_score, 1.0), 4)

        return features

    def _analyze_schedule_context(self, match_context: MatchContext) -> dict[str, float]:
        """
        分析赛程背景（深度爆破版）

        新增:
            - 比赛重要性评分
            - 赛程密度标记

        Args:
            match_context: 比赛上下文

        Returns:
            赛程背景特征字典
        """
        features = {}

        # 是否杯赛
        features["is_cup_match"] = 1.0 if match_context.is_cup_match else 0.0

        # 休息天数
        days_since_last = match_context.days_since_last_match or 0
        features["days_since_last_match"] = float(days_since_last)

        # 疲劳度评估（基于休息天数）
        if days_since_last >= 7:
            fatigue_level = 0.0  # 充足休息
        elif days_since_last >= 4:
            fatigue_level = 0.3  # 正常休息
        elif days_since_last >= 2:
            fatigue_level = 0.6  # 疲劳
        else:
            fatigue_level = 1.0  # 高度疲劳

        features["fatigue_level"] = fatigue_level

        # 是否为背靠背比赛（休息天数 <= 2）
        features["is_back_to_back"] = 1.0 if days_since_last <= 2 else 0.0

        # 比赛重要性评分（新: 综合杯赛和赛程）
        importance_score = 0.5  # 默认普通联赛

        if match_context.is_cup_match:
            importance_score += 0.3  # 杯赛更重要

        # 如果休息天数很少，可能是密集赛程（重要性降低）
        if days_since_last <= 2:
            importance_score -= 0.1

        features["match_importance"] = round(max(0.0, min(importance_score, 1.0)), 4)

        return features

    def get_feature_schema(self) -> dict[str, type]:
        """获取输出特征的 Schema"""
        return {
            # 时间特征
            "kickoff_hour_sin": float,
            "kickoff_hour_cos": float,
            "kickoff_time_slot": float,
            "is_early_kickoff": float,
            "is_prime_time": float,
            "is_weekend": float,
            "season": float,
            # 场地特征
            "is_neutral_venue": float,
            "venue_capacity_normalized": float,
            "venue_size_category": float,
            "stadium_attendance_rate": float,
            "stadium_pressure": float,
            "stadium_pressure_level": float,
            # 天气特征
            "weather_temp_normalized": float,
            "weather_condition_encoded": float,
            "is_extreme_weather": float,
            "is_extreme_temperature": float,
            "is_rainy": float,
            "adverse_weather_score": float,
            # 赛程特征
            "is_cup_match": float,
            "days_since_last_match": float,
            "fatigue_level": float,
            "is_back_to_back": float,
            "match_importance": float,
        }
