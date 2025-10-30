"""测试工厂基类"""

from factory.alchemy import SQLAlchemyModelFactory


class BaseFactory(SQLAlchemyModelFactory):
    """所有SQLAlchemy工厂的基础类,统一会话配置。"""

    class Meta:
        abstract = True
        sqlalchemy_session = None  # 由测试fixture在运行期注入
        sqlalchemy_session_persistence = "flush"
