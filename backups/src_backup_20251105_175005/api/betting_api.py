#!/usr/bin/env python3
"""
投注API模块
Betting API Module

提供EV计算和投注策略的RESTful API接口:
- 单场比赛投注建议
- 组合投注优化
- 历史表现分析
- 实时赔率更新
- SRS合规性验证

创建时间: 2025-10-29  # TODO: 将魔法数字 2025 提取为常量
Issue: #116 EV计算和投注策略
"""



from src.core.logging_system import get_logger

logger = get_logger(__name__)
