"""
用户工厂 - 用于测试数据创建
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import random
import hashlib

from .base import BaseFactory, DataFactoryMixin, TimestampMixin


class UserFactory(BaseFactory, DataFactoryMixin, TimestampMixin):
    """用户测试数据工厂"""

    # 用户名池
    USERNAMES = [
        "football_fan", "soccer_expert", "match_predictor", "sports_analyst",
        "game_reviewer", "stats_master", "betting_pro", "tipster_123",
        "football_guru", "soccer_wizard", "match_day", "goal_scorer"
    ]

    # 真实姓名池
    REAL_NAMES = [
        "张三", "李四", "王五", "赵六", "陈七",
        "刘八", "周九", "吴十", "郑十一", "孙十二"
    ]

    @classmethod
    def create(cls, **kwargs) -> Dict[str, Any]:
        """创建单个用户实例"""
        username = kwargs.get('username', f"{random.choice(cls.USERNAMES)}_{random.randint(1, 9999)}")
        email = kwargs.get('email', f"{username}@example.com")

        default_data = {
            'id': cls.generate_id(),
            'username': username,
            'email': email,
            'password_hash': cls._hash_password("default_password"),
            'real_name': kwargs.get('real_name', random.choice(cls.REAL_NAMES)),
            'nickname': kwargs.get('nickname', username),
            'avatar_url': kwargs.get('avatar_url', f"https://avatar.example.com/{username}.jpg"),
            'phone': kwargs.get('phone', f"138{random.randint(10000000, 99999999)}"),
            'date_of_birth': kwargs.get('date_of_birth', cls._generate_birth_date()),
            'gender': kwargs.get('gender', random.choice(['male', 'female', 'other'])),
            'country': kwargs.get('country', '中国'),
            'city': kwargs.get('city', random.choice(['北京', '上海', '广州', '深圳', '杭州'])),
            'timezone': kwargs.get('timezone', 'Asia/Shanghai'),
            'language': kwargs.get('language', 'zh-CN'),
            'currency': kwargs.get('currency', 'CNY'),
            'is_active': True,
            'is_verified': kwargs.get('is_verified', random.choice([True, False])),
            'is_premium': kwargs.get('is_premium', False),
            'membership_level': kwargs.get('membership_level', random.choice(['free', 'basic', 'premium', 'vip'])),
            'registration_date': cls.generate_timestamp(),
            'last_login_date': kwargs.get('last_login_date', cls.generate_timestamp()),
            'login_count': random.randint(1, 1000),
            'prediction_count': random.randint(0, 500),
            'win_rate': round(random.uniform(0.3, 0.8), 3),
            'points_balance': random.randint(0, 10000),
            'total_earnings': round(random.uniform(0, 50000), 2),
            'favorite_league': kwargs.get('favorite_league', random.choice(['西甲', '英超', '意甲', '德甲', '法甲', '中超'])),
            'favorite_team': kwargs.get('favorite_team', random.choice(['皇家马德里', '巴塞罗那', '曼联', '利物浦', '拜仁慕尼黑'])),
            'notification_enabled': True,
            'email_notifications': kwargs.get('email_notifications', random.choice([True, False])),
            'push_notifications': kwargs.get('push_notifications', random.choice([True, False])),
            'privacy_level': kwargs.get('privacy_level', random.choice(['public', 'friends', 'private'])),
            'bio': kwargs.get('bio', f"足球爱好者，擅长比赛分析"),
            'website': kwargs.get('website', None),
            'social_links': kwargs.get('social_links', {}),
            'banned_until': None,
            'suspension_count': random.randint(0, 3),
            'created_at': cls.generate_timestamp(),
            'updated_at': cls.generate_timestamp(),
        }

        # 合并用户提供的参数
        default_data.update(kwargs)
        return cls.with_timestamps(**default_data)

    @classmethod
    def create_batch(cls, count: int, **kwargs) -> List[Dict[str, Any]]:
        """批量创建用户实例"""
        users = []
        for i in range(count):
            user_data = cls.create(**kwargs)
            users.append(user_data)
        return users

    @classmethod
    def create_premium_user(cls, **kwargs) -> Dict[str, Any]:
        """创建高级用户"""
        return cls.create(
            is_premium=True,
            membership_level=random.choice(['premium', 'vip']),
            points_balance=random.randint(5000, 50000),
            prediction_count=random.randint(100, 1000),
            win_rate=round(random.uniform(0.6, 0.9), 3),
            **kwargs
        )

    @classmethod
    def create_free_user(cls, **kwargs) -> Dict[str, Any]:
        """创建免费用户"""
        return cls.create(
            is_premium=False,
            membership_level='free',
            points_balance=random.randint(0, 5000),
            prediction_count=random.randint(0, 100),
            win_rate=round(random.uniform(0.3, 0.7), 3),
            **kwargs
        )

    @classmethod
    def create_verified_user(cls, **kwargs) -> Dict[str, Any]:
        """创建已验证用户"""
        return cls.create(
            is_verified=True,
            verification_date=cls.generate_timestamp(),
            **kwargs
        )

    @classmethod
    def create_unverified_user(cls, **kwargs) -> Dict[str, Any]:
        """创建未验证用户"""
        return cls.create(
            is_verified=False,
            verification_date=None,
            **kwargs
        )

    @classmethod
    def create_expert_user(cls, **kwargs) -> Dict[str, Any]:
        """创建专家用户"""
        return cls.create(
            win_rate=round(random.uniform(0.75, 0.95), 3),
            prediction_count=random.randint(500, 2000),
            points_balance=random.randint(10000, 100000),
            membership_level='vip',
            is_verified=True,
            is_premium=True,
            bio="专业足球分析师，拥有丰富的比赛预测经验",
            **kwargs
        )

    @classmethod
    def create_beginner_user(cls, **kwargs) -> Dict[str, Any]:
        """创建新手用户"""
        return cls.create(
            win_rate=round(random.uniform(0.3, 0.5), 3),
            prediction_count=random.randint(0, 20),
            points_balance=random.randint(0, 1000),
            membership_level='free',
            login_count=random.randint(1, 10),
            bio="足球预测新手，正在学习中",
            **kwargs
        )

    @classmethod
    def create_suspended_user(cls, **kwargs) -> Dict[str, Any]:
        """创建被暂停用户"""
        suspension_days = random.randint(1, 30)
        banned_until = datetime.now(timezone.utc).replace(day=datetime.now(timezone.utc).day + suspension_days)

        return cls.create(
            is_active=False,
            banned_until=banned_until,
            suspension_count=random.randint(1, 5),
            **kwargs
        )

    @classmethod
    def create_with_email(cls, email: str, **kwargs) -> Dict[str, Any]:
        """创建指定邮箱的用户"""
        username = email.split('@')[0] if '@' in email else f"user_{random.randint(1, 9999)}"
        return cls.create(
            username=username,
            email=email,
            **kwargs
        )

    @classmethod
    def _hash_password(cls, password: str) -> str:
        """哈希密码"""
        return hashlib.sha256(password.encode('utf-8')).hexdigest()

    @classmethod
    def _generate_birth_date(cls) -> datetime:
        """生成出生日期"""
        years_ago = random.randint(18, 65)
        birth_date = datetime.now(timezone.utc).replace(year=datetime.now(timezone.utc).year - years_ago)
        return birth_date


class AdminUserFactory(UserFactory):
    """管理员用户工厂"""

    @classmethod
    def create(cls, **kwargs) -> Dict[str, Any]:
        """创建管理员用户"""
        admin_data = super().create(**kwargs)

        # 添加管理员特有字段
        admin_data.update({
            'is_admin': True,
            'admin_level': kwargs.get('admin_level', random.choice(['moderator', 'admin', 'super_admin'])),
            'admin_permissions': kwargs.get('admin_permissions', [
                'user_management', 'content_moderation', 'system_settings'
            ]),
            'admin_notes': kwargs.get('admin_notes', '系统管理员'),
        })

        return admin_data


class AnalystUserFactory(UserFactory):
    """分析师用户工厂"""

    @classmethod
    def create(cls, **kwargs) -> Dict[str, Any]:
        """创建分析师用户"""
        analyst_data = super().create(**kwargs)

        # 添加分析师特有字段
        analyst_data.update({
            'is_analyst': True,
            'analyst_level': kwargs.get('analyst_level', random.choice(['junior', 'senior', 'expert'])),
            'specialization': kwargs.get('specialization', random.choice([
                'match_analysis', 'statistical_analysis', 'player_performance',
                'tactical_analysis', 'market_analysis'
            ])),
            'certifications': kwargs.get('certifications', [
                'FIFA Analyst Certificate',
                'UEFA Data Analytics License'
            ]),
            'followers_count': random.randint(100, 10000),
            'articles_published': random.randint(10, 500),
            'accuracy_rating': round(random.uniform(0.7, 0.95), 3),
        })

        return analyst_data