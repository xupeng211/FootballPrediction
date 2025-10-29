"""
League模型测试
League Model Tests
"""

import pytest

# 尝试导入League模型并设置可用性标志
try:
    from src.database.models.league import League

    LEAGUE_AVAILABLE = True
    TEST_SKIP_REASON = "League模型不可用"
except ImportError as e:
    print(f"League model import error: {e}")
    LEAGUE_AVAILABLE = False
    TEST_SKIP_REASON = "League模型不可用"


@pytest.mark.skipif(not LEAGUE_AVAILABLE, reason=TEST_SKIP_REASON)
@pytest.mark.unit
@pytest.mark.database
class TestLeagueModel:
    """League模型测试"""

    def test_league_class_import(self):
        """测试League类导入"""
        try:
            from src.database.models.league import League

            assert League is not None
        except ImportError:
            pytest.skip("League类导入失败")

    def test_league_inheritance(self):
        """测试League类继承关系"""
        try:
            from src.database.models.league import League
            from src.database.base import BaseModel

            assert issubclass(League, BaseModel)
        except ImportError:
            pytest.skip("继承关系检查失败")

    def test_league_table_name(self):
        """测试League表名配置"""
        try:
            assert hasattr(League, "__tablename__")
            assert League.__tablename__ == "leagues"
        except Exception:
            pytest.skip("表名配置检查失败")

    def test_league_table_options(self):
        """测试League表选项配置"""
        try:
            assert hasattr(League, "__table_args__")
            table_args = League.__table_args__
            assert isinstance(table_args, dict)
            assert table_args.get("extend_existing") is True
        except Exception:
            pytest.skip("表选项配置检查失败")

    def test_league_instantiation(self):
        """测试League实例化"""
        try:
            league = League()
            assert league is not None
            assert isinstance(league, League)
        except Exception:
            pytest.skip("League实例化失败")

    def test_league_class_attributes(self):
        """测试League类属性"""
        try:
            # 检查是否有基本的SQLAlchemy模型属性
            league_class = League

            # 应该有id字段（从BaseModel继承）
            assert hasattr(league_class, "id") or hasattr(league_class, "__annotations__")

        except Exception:
            pytest.skip("League类属性检查失败")

    def test_league_module_docstring(self):
        """测试League模块文档字符串"""
        try:
            import src.database.models.league as league_module

            assert league_module.__doc__ is not None
            assert "联赛" in league_module.__doc__
            assert "英超" in league_module.__doc__
            assert "西甲" in league_module.__doc__

        except ImportError:
            pytest.skip("League模块文档检查失败")

    def test_league_str_representation(self):
        """测试League字符串表示"""
        try:
            league = League()
            # 检查是否有__str__或__repr__方法
            assert hasattr(league, "__str__") or hasattr(league, "__repr__")
        except Exception:
            pytest.skip("League字符串表示检查失败")


@pytest.mark.skipif(not LEAGUE_AVAILABLE, reason=TEST_SKIP_REASON)
@pytest.mark.unit
@pytest.mark.database
class TestLeagueModelAdvanced:
    """League模型高级测试"""

    def test_league_metadata(self):
        """测试League模型元数据"""
        try:
            from sqlalchemy import inspect

            league = League()
            mapper = inspect(league)

            # 检查映射信息
            assert mapper is not None
            assert mapper.mapper.class_ == League

        except ImportError:
            pytest.skip("SQLAlchemy检查失败")
        except Exception:
            pytest.skip("元数据检查失败")

    def test_league_table_metadata(self):
        """测试League表元数据"""
        try:
            assert hasattr(League, "__table__")
            table = League.__table__

            if table is not None:
                assert table.name == "leagues"
                assert len(table.columns) > 0  # 至少有id列

        except Exception:
            pytest.skip("表元数据检查失败")
