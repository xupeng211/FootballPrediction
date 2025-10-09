"""
模块导出
Module Exports
"""

# 由于模块尚未实现，使用占位符
try:
    from .matches import router as Matches
except ImportError:
    Matches = None

try:
    from .teams import router as Teams
except ImportError:
    Teams = None

try:
    from .leagues import router as Leagues
except ImportError:
    Leagues = None

try:
    from .odds import router as Odds
except ImportError:
    Odds = None

try:
    from .statistics import router as Statistics
except ImportError:
    Statistics = None

try:
    from .dependencies import router as Dependencies
except ImportError:
    Dependencies = None

__all__ = [
    "Matches",
    "Teams",
    "Leagues",
    "Odds",
    "Statistics",
    "Dependencies",
]
