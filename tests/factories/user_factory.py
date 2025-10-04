"""用户工厂"""

import factory
from .base import BaseFactory


class UserFactory(BaseFactory):
    """用户工厂"""

    class Meta:
        model = None  # 需要导入实际模型
        sqlalchemy_session = None

    email = factory.LazyAttribute(lambda o: f"{o.username}@example.com")
    username = factory.Faker("user_name")
    full_name = factory.Faker("name")
    hashed_password = factory.LazyFunction(lambda: "hashed_password_here")
    is_active = True
    is_verified = False

    @factory.post_generation
    def password(self, create, extracted, **kwargs):
        """设置密码"""
        if extracted:
            self.set_password(extracted)


class AdminUserFactory(UserFactory):
    """管理员用户工厂"""

    is_admin = True
    is_verified = True
    email = factory.LazyAttribute(lambda o: f"admin.{o.username}@example.com")
