"""
足球数据清洗器

实现足球数据的清洗和标准化逻辑。
包含时间统一、球队ID映射、赔率校验、比分校验等功能。

清洗规则：
- 时间数据：统一转换为UTC时间
- 球队名称：映射到标准team_id
- 赔率数据：精度保持3位小数，异常值标记
- 比分数据：非负整数，上限99
- 联赛名称：标准化联赛代码

该文件已重构为模块化架构，原始功能现在通过以下模块提供：
- time_processor: 时间处理和转换
- id_mapper: 球队和联赛ID映射
- data_validator: 数据验证和清洗
- odds_processor: 赔率数据处理
- cleaner: 主清洗器协调器

基于 DATA_DESIGN.md 第4.1节设计。
"""

from .football_data_cleaner_mod import (

# 为了向后兼容，从新的模块化实现重新导出所有类
    FootballDataCleaner,
)

# 保持原有的导出
__all__ = [
    "FootballDataCleaner",
]
