"""测试工厂基类"""

import factory
import faker

fake = faker.Faker()


class BaseFactory(factory.alchemy.SQLAlchemyModelFactory):
    """基础工厂类"""

    class Meta:
        abstract = True
        sqlalchemy_session_persistence = "flush"
