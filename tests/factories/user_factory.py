"""User 模型工厂。"""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta

import factory

from tests.factories.base import BaseFactory
from src.database.models.user import User


class UserFactory(BaseFactory):
    """创建平台用户。"""

    class Meta:
        model = User

    username = factory.Sequence(lambda n: f"user{n:03d}")
    email = factory.LazyAttribute(lambda obj: f"{obj.username}@example.com")
    full_name = factory.Faker("name")
    password_hash = factory.LazyFunction(
        lambda: hashlib.sha256(b"password123").hexdigest()
    )
    is_active = True
    is_verified = True
    is_admin = False
    is_analyst = False
    is_premium = False
    is_professional_bettor = False
    is_casual_bettor = False
    created_at = factory.LazyFunction(datetime.utcnow)
    updated_at = factory.LazyFunction(datetime.utcnow)
    last_login = factory.LazyFunction(datetime.utcnow)
    subscription_plan = None
    subscription_expires_at = None
    bankroll = None
    risk_preference = None
    favorite_leagues = factory.LazyFunction(lambda: [])
    timezone = factory.Faker("timezone")
    avatar_url = factory.LazyAttribute(
        lambda obj: f"https://ui-avatars.com/api/?name={obj.full_name.replace(' ', '+')}"
    )

    @classmethod
    def create_admin(cls, **kwargs) -> User:
        return cls(is_admin=True, **kwargs)

    @classmethod
    def create_analyst(cls, **kwargs) -> User:
        return cls(is_analyst=True, **kwargs)

    @classmethod
    def create_premium_user(cls, **kwargs) -> User:
        return cls(
            is_premium=True,
            subscription_plan="premium",
            subscription_expires_at=datetime.utcnow() + timedelta(days=365),
            **kwargs,
        )

    @classmethod
    def create_with_email(cls, email: str, **kwargs) -> User:
        return cls(username=email.split("@")[0], email=email, **kwargs)

    @classmethod
    def create_batch_with_prefix(cls, count: int, prefix: str, **kwargs):
        return [
            cls.create(
                username=f"{prefix}_{index+1:03d}",
                email=f"{prefix}_{index+1:03d}@example.com",
                **kwargs,
            )
            for index in range(count)
        ]

    @classmethod
    def create_user_with_password(cls, password: str, **kwargs) -> User:
        return cls(
            password_hash=hashlib.sha256(password.encode()).hexdigest(), **kwargs
        )

    @classmethod
    def create_test_users(cls):
        return TestUserFactory.create_test_users()


class AnalystUserFactory(UserFactory):
    """分析师角色。"""

    class Meta:
        model = User

    is_analyst = True
    specialization = factory.LazyFunction(
        lambda: secrets.choice(
            [
                "Premier League",
                "La Liga",
                "Serie A",
                "Bundesliga",
                "Ligue 1",
                "Chinese Super League",
            ]
        )
    )
    experience_years = factory.Faker("random_int", min=2, max=20)


class BettorUserFactory(UserFactory):
    """投注用户。"""

    class Meta:
        model = User

    is_professional_bettor = True
    bankroll = factory.Faker("random_int", min=10_000, max=100_000)
    risk_preference = factory.LazyFunction(
        lambda: secrets.choice(["low", "medium", "high"])
    )


class TestUserFactory(UserFactory):
    """常用测试用户集合。"""

    class Meta:
        model = User

    @classmethod
    def create_test_users(cls):
        return [
            cls.create(username="test_admin", email="admin@test.com", is_admin=True),
            cls.create(username="test_user", email="user@test.com"),
            cls.create(
                username="test_analyst", email="analyst@test.com", is_analyst=True
            ),
            cls.create(
                username="test_premium", email="premium@test.com", is_premium=True
            ),
        ]
