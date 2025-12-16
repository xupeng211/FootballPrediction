"""
特征工程模块 - Phase 5 Advanced Features

本模块包含高级特征转换器，专门设计用于解决Phase 4中识别的关键问题：
1. 主客场滚动统计分离 (解决Napoli vs Juventus案例中的主场偏见)
2. 历史交锋统计 (Head-to-Head记录)
3. 联赛形态特征 (积分滚动统计)

核心组件：
- AdvancedFeatureTransformer: 主要特征转换器
- H2HCalculator: 历史交锋统计计算器
- VenueAnalyzer: 场馆专用分析器

目标：将模型准确率从58.69%提升至65%+
"""

from .advanced_feature_transformer import AdvancedFeatureTransformer
from .h2h_calculator import H2HCalculator
from .venue_analyzer import VenueAnalyzer
from .extractor import MatchFeatureExtractor, MatchFeatureSet

__all__ = ["AdvancedFeatureTransformer", "H2HCalculator", "VenueAnalyzer", "MatchFeatureExtractor", "MatchFeatureSet"]

__version__ = "5.0.0"
__author__ = "Football Prediction Team"
__status__ = "Phase 5 - Advanced Features Development"
