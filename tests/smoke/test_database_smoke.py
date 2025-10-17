#!/usr/bin/env python3
"""
Database模块smoke测试
测试数据库模块是否可以正常导入和初始化
"""

import pytest
import sys
from pathlib import Path

# 添加src到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


class TestDatabaseSmoke:
    """Database模块冒烟测试"""

    def test_database_models(self):
        """测试数据库模型"""
        # 测试导入主要模型
        from src.database.models.user import User
        from src.database.models.match import Match
        from src.database.models.team import Team
        from src.database.models.league import League
        from src.database.models.prediction import Prediction

        assert User is not None
        assert Match is not None
        assert Team is not None
        assert League is not None
        assert Prediction is not None

    def test_database_base(self):
        """测试数据库基础类"""
        from src.database.base import Base

        assert Base is not None
        assert hasattr(Base, "metadata")

    def test_database_config(self):
        """测试数据库配置"""
        from src.database.config import DatabaseConfig

        config = DatabaseConfig()
        assert config is not None
        assert hasattr(config, "database_url")

    def test_repositories(self):
        """测试仓储模式"""
        from src.database.repositories.base import BaseRepository
        from src.database.repositories.user import UserRepository
        from src.database.repositories.match import MatchRepository

        assert BaseRepository is not None
        assert UserRepository is not None
        assert MatchRepository is not None

    def test_database_types(self):
        """测试数据库类型"""
        from src.database.types import JSONType

        assert JSONType is not None

    def test_sql_compatibility(self):
        """测试SQL兼容性"""
        from src.database.sql_compatibility import SQLCompatibility

        compat = SQLCompatibility()
        assert compat is not None
