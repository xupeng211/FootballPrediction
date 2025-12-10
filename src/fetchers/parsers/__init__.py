"""
解析器模块
Parsers Module

提供各种数据解析器，用于从 HTML 内容中提取结构化数据。

可用解析器:
- odds_parser: 赔率数据解析器
- 更多解析器待实现...

作者: Data Integration Team
创建时间: 2025-12-07
版本: 1.0.0
"""

from .odds_parser import OddsParser

# 导出所有公共接口
__all__ = [
    "OddsParser",
]
