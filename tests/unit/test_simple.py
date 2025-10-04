"""简单测试 - 验证基本功能"""

import pytest
import sys
from pathlib import Path

# 添加src目录
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def test_imports():
    """测试核心包导入"""
    try:
        import fastapi  # noqa: F401
        import sqlalchemy  # noqa: F401
        import pydantic  # noqa: F401
        import redis  # noqa: F401
        import celery  # noqa: F401
        import numpy  # noqa: F401
        import pandas  # noqa: F401

        assert True
    except ImportError as e:
        pytest.fail(f"导入失败: {e}")


def test_fastapi_app():
    """测试FastAPI应用创建"""
    from fastapi import FastAPI

    app = FastAPI()
    assert app is not None

    @app.get("/")
    async def root():
        return {"message": "Hello World"}

    assert len(app.routes) > 0


def test_pydantic_model():
    """测试Pydantic模型"""
    from pydantic import BaseModel

    class TestModel(BaseModel):
        name: str
        age: int

    model = TestModel(name="test", age=25)
    assert model.name == "test"
    assert model.age == 25


def test_sqlalchemy_connection():
    """测试SQLAlchemy连接"""
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker

    # 使用SQLite内存数据库
    engine = create_engine("sqlite:///:memory:")
    Session = sessionmaker(bind=engine)

    with Session() as session:
        result = session.execute(text("SELECT 1"))
        assert result.scalar() == 1
