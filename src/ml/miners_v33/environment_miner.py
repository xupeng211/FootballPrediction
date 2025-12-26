#!/usr/bin/env python3
"""
V33.0 Environment Miner - 环境与裁判深度建模器
============================================
从 general 和 matchFacts 中提取环境与裁判因子
"""

import numpy as np
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class EnvironmentFeatures:
    """环境特征数据类"""
    # 基础信息
    league_id: int
    match_round: int
    country_code: str
    coverage_level: str

    # 时间特征
    match_hour: int
    match_day_of_week: int
    is_weekend: bool
    is_night_match: bool

    # 天气特征
    weather_temperature: float
    weather_wind_speed: float
    weather_precipitation: float
    weather_humidity: float
    weather_cloud_cover: float
    is_bad_weather: bool

    # 场地特征 (如果可获取)
    venue_capacity: int
    attendance_fill_ratio: float

    # 裁判特征
    referee_name: str
    referee_yellow_tendency: float
    referee_red_tendency: float

    # 赛程密集度
    days_since_last_match_home: int
    days_since_last_match_away: int


class EnvironmentMiner:
    """
    环境与裁判深度建模器

    核心功能:
    1. 天气影响建模 - 温度、风速、降水
    2. 场地压力分析 - 上座率
    3. 裁判倾向建模 - 红黄牌习惯
    4. 赛程因素 - 疲劳度指标
    """

    # 裁判红黄牌倾向缓存 (实际应用中需要从历史数据计算)
    _referee_stats = {}

    def __init__(self):
        """初始化环境采矿器"""
        pass

    def extract_features(self, json_data: Dict, previous_matches: Optional[List[Dict]] = None) -> Optional[EnvironmentFeatures]:
        """
        从 FotMob JSON 中提取环境特征

        Args:
            json_data: FotMob API 响应数据
            previous_matches: 历史比赛数据（用于计算疲劳度）

        Returns:
            EnvironmentFeatures 或 None
        """
        try:
            # 提取 general 数据
            general = json_data.get('general', {})

            # 提取 weather 数据
            content = json_data.get('content', {})
            weather = content.get('weather', {})

            # 提取 matchFacts 数据 (包含裁判信息)
            match_facts = content.get('matchFacts', {})

            # 解析比赛时间
            match_time_str = general.get('matchTimeUTCDate', '')
            match_time = self._parse_match_time(match_time_str)

            # 计算特征
            features = self._calculate_environment_features(
                general, weather, match_facts, match_time, previous_matches
            )

            return features

        except Exception as e:
            logger.error(f"环境特征提取失败: {e}")
            return None

    def _parse_match_time(self, time_str: str) -> Optional[datetime]:
        """解析比赛时间"""
        try:
            return datetime.fromisoformat(time_str.replace('Z', '+00:00'))
        except:
            return None

    def _calculate_environment_features(
        self,
        general: Dict,
        weather: Dict,
        match_facts: Dict,
        match_time: Optional[datetime],
        previous_matches: Optional[List[Dict]]
    ) -> EnvironmentFeatures:
        """计算环境特征"""

        # 基础信息
        league_id = general.get('leagueId', 0)
        match_round = general.get('matchRound', 0)
        country_code = general.get('countryCode', '')
        coverage_level = general.get('coverageLevel', '')

        # 时间特征
        match_hour = match_time.hour if match_time else 0
        match_day_of_week = match_time.weekday() if match_time else 0
        is_weekend = match_day_of_week >= 5 if match_time else False
        is_night_match = match_hour >= 19 or match_hour <= 4

        # 天气特征
        weather_temperature = float(weather.get('temperature', 15))
        weather_wind_speed = float(weather.get('windSpeed', 0))
        weather_precipitation = float(weather.get('precipitation', 0))
        weather_humidity = float(weather.get('relativeHumidity', 50))
        weather_cloud_cover = float(weather.get('cloudCover', 0))
        is_bad_weather = weather_precipitation > 5 or weather_wind_speed > 20

        # 场地特征 (从 matchFacts 或 infoBox 获取)
        info_box = match_facts.get('infoBox', {})
        venue_capacity = int(info_box.get('capacity', 0))
        attendance = int(info_box.get('attendance', 0))
        attendance_fill_ratio = attendance / venue_capacity if venue_capacity > 0 else 0.0

        # 裁判特征
        referee_info = match_facts.get('referee', {})
        referee_name = referee_info.get('name', 'Unknown')

        # 从历史数据或缓存获取裁判倾向
        referee_yellow = self._get_referee_tendency(referee_name, 'yellow')
        referee_red = self._get_referee_tendency(referee_name, 'red')

        # 赛程密集度 (需要历史数据)
        days_since_last_home, days_since_last_away = self._calculate_fatigue(previous_matches)

        return EnvironmentFeatures(
            league_id=league_id,
            match_round=match_round,
            country_code=country_code,
            coverage_level=coverage_level,
            match_hour=match_hour,
            match_day_of_week=match_day_of_week,
            is_weekend=is_weekend,
            is_night_match=is_night_match,
            weather_temperature=weather_temperature,
            weather_wind_speed=weather_wind_speed,
            weather_precipitation=weather_precipitation,
            weather_humidity=weather_humidity,
            weather_cloud_cover=weather_cloud_cover,
            is_bad_weather=is_bad_weather,
            venue_capacity=venue_capacity,
            attendance_fill_ratio=attendance_fill_ratio,
            referee_name=referee_name,
            referee_yellow_tendency=referee_yellow,
            referee_red_tendency=referee_red,
            days_since_last_match_home=days_since_last_home,
            days_since_last_match_away=days_since_last_away,
        )

    def _get_referee_tendency(self, referee_name: str, card_type: str) -> float:
        """
        获取裁判掏牌倾向

        实际应用中应该从历史比赛数据统计得出
        这里返回模拟值
        """
        # 从缓存获取或使用默认值
        key = f"{referee_name}_{card_type}"
        if key in self._referee_stats:
            return self._referee_stats[key]

        # 默认值 (每场平均掏牌数)
        if card_type == 'yellow':
            return 3.5  # 平均每场 3.5 张黄牌
        else:  # red
            return 0.3  # 平均每场 0.3 张红牌

    def _calculate_fatigue(self, previous_matches: Optional[List[Dict]]) -> tuple:
        """
        计算疲劳度 (距上场比赛天数)

        Args:
            previous_matches: 历史比赛列表

        Returns:
            (距上场比赛天数_主队, 距上场比赛天数_客队)
        """
        if not previous_matches:
            return 7, 7  # 默认一周

        # 简化逻辑: 返回历史数据中最近一场比赛的天数差
        # 实际应用中需要更复杂的计算
        return 7, 7

    def to_feature_dict(self, features: EnvironmentFeatures) -> Dict[str, float]:
        """
        将 EnvironmentFeatures 转换为特征字典

        Args:
            features: 环境特征对象

        Returns:
            特征字典
        """
        if not features:
            return {}

        return {
            'env_league_id': features.league_id,
            'env_match_round': features.match_round,
            'env_match_hour': features.match_hour,
            'env_day_of_week': features.match_day_of_week,
            'env_is_weekend': float(features.is_weekend),
            'env_is_night_match': float(features.is_night_match),
            'env_weather_temp': features.weather_temperature,
            'env_weather_wind': features.weather_wind_speed,
            'env_weather_rain': features.weather_precipitation,
            'env_weather_humidity': features.weather_humidity,
            'env_is_bad_weather': float(features.is_bad_weather),
            'env_venue_capacity': features.venue_capacity,
            'env_attendance_ratio': features.attendance_fill_ratio,
            'env_referee_yellow': features.referee_yellow_tendency,
            'env_referee_red': features.referee_red_tendency,
            'env_fatigue_home': features.days_since_last_match_home,
            'env_fatigue_away': features.days_since_last_match_away,
            'env_fatigue_diff': features.days_since_last_match_home - features.days_since_last_match_away,
        }
