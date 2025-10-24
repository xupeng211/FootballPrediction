"""
数据工厂 - 通用测试数据生成器
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timezone
import random
import uuid
import json

from .base import BaseFactory, DataFactoryMixin, TimestampMixin


class DataFactory(BaseFactory, DataFactoryMixin, TimestampMixin):
    """通用数据工厂"""

    # 常用数据池
    NAMES = ["张三", "李四", "王五", "赵六", "陈七", "刘八", "周九", "吴十"]
    EMAILS = ["test@example.com", "user@test.com", "demo@sample.org"]
    CITIES = ["北京", "上海", "广州", "深圳", "杭州", "成都", "武汉", "西安"]
    COUNTRIES = ["中国", "美国", "英国", "日本", "韩国", "德国", "法国", "意大利"]
    COMPANIES = ["阿里巴巴", "腾讯", "百度", "字节跳动", "美团", "滴滴", "京东", "网易"]

    @classmethod
    def create(cls, **kwargs) -> Dict[str, Any]:
        """创建通用数据实例"""
        default_data = {
            'id': cls.generate_id(),
            'uuid': str(uuid.uuid4()),
            'name': random.choice(cls.NAMES),
            'email': random.choice(cls.EMAILS),
            'phone': f"138{random.randint(10000000, 99999999)}",
            'city': random.choice(cls.CITIES),
            'country': random.choice(cls.COUNTRIES),
            'company': random.choice(cls.COMPANIES),
            'created_at': cls.generate_timestamp(),
            'updated_at': cls.generate_timestamp(),
            'is_active': True,
            'score': random.randint(0, 100),
            'rating': round(random.uniform(1.0, 5.0), 1),
            'description': f"测试数据描述_{random.randint(1, 1000)}",
            'tags': random.sample(['tag1', 'tag2', 'tag3', 'tag4', 'tag5'], random.randint(1, 3)),
            'metadata': cls._generate_metadata(),
        }

        default_data.update(kwargs)
        return cls.with_timestamps(**default_data)

    @classmethod
    def create_batch(cls, count: int, **kwargs) -> List[Dict[str, Any]]:
        """批量创建数据实例"""
        return [cls.create(**kwargs) for _ in range(count)]

    @classmethod
    def create_with_name(cls, name: str, **kwargs) -> Dict[str, Any]:
        """创建指定名称的数据"""
        return cls.create(name=name, **kwargs)

    @classmethod
    def create_with_email(cls, email: str, **kwargs) -> Dict[str, Any]:
        """创建指定邮箱的数据"""
        return cls.create(email=email, **kwargs)

    @classmethod
    def create_active(cls, **kwargs) -> Dict[str, Any]:
        """创建活跃数据"""
        return cls.create(is_active=True, **kwargs)

    @classmethod
    def create_inactive(cls, **kwargs) -> Dict[str, Any]:
        """创建非活跃数据"""
        return cls.create(is_active=False, **kwargs)

    @classmethod
    def create_high_score(cls, **kwargs) -> Dict[str, Any]:
        """创建高分数据"""
        return cls.create(score=random.randint(80, 100), rating=round(random.uniform(4.0, 5.0), 1), **kwargs)

    @classmethod
    def create_low_score(cls, **kwargs) -> Dict[str, Any]:
        """创建低分数据"""
        return cls.create(score=random.randint(0, 30), rating=round(random.uniform(1.0, 2.0), 1), **kwargs)

    @classmethod
    def create_with_tags(cls, tags: List[str], **kwargs) -> Dict[str, Any]:
        """创建带标签的数据"""
        return cls.create(tags=tags, **kwargs)

    @classmethod
    def _generate_metadata(cls) -> Dict[str, Any]:
        """生成元数据"""
        return {
            'source': 'test_factory',
            'version': '1.0',
            'environment': 'test',
            'created_by': 'DataFactory',
            'random_seed': random.randint(1, 10000),
            'checksum': f"checksum_{random.randint(1000, 9999)}"
        }

    @classmethod
    def create_json_data(cls, **kwargs) -> str:
        """创建JSON格式的测试数据"""
        data = cls.create(**kwargs)
        return json.dumps(data, ensure_ascii=False, indent=2, default=str)

    @classmethod
    def create_numeric_data(cls, **kwargs) -> Dict[str, Union[int, float]]:
        """创建数值型测试数据"""
        return {
            'integer_value': random.randint(1, 1000),
            'float_value': round(random.uniform(0.1, 99.9), 2),
            'percentage': round(random.uniform(0.0, 100.0), 2),
            'ratio': round(random.uniform(0.1, 10.0), 3),
            'score': random.randint(0, 100),
            'rating': round(random.uniform(1.0, 5.0), 1),
            **kwargs
        }

    @classmethod
    def create_text_data(cls, **kwargs) -> Dict[str, str]:
        """创建文本型测试数据"""
        texts = [
            "这是一段测试文本",
            "Lorem ipsum dolor sit amet",
            "测试数据生成器",
            "Sample text for testing",
            "示例文本内容"
        ]

        return {
            'title': f"标题_{random.randint(1, 100)}",
            'content': random.choice(texts),
            'description': f"描述_{random.randint(1, 1000)}",
            'summary': f"摘要_{random.randint(1, 500)}",
            'notes': f"备注_{random.randint(1, 200)}",
            **kwargs
        }

    @classmethod
    def create_datetime_data(cls, **kwargs) -> Dict[str, datetime]:
        """创建日期时间测试数据"""
        now = datetime.now(timezone.utc)
        return {
            'created_at': now,
            'updated_at': now,
            'start_date': now.replace(day=random.randint(1, 28)),
            'end_date': now.replace(day=random.randint(1, 28)),
            'last_modified': now.replace(hour=random.randint(0, 23)),
            'expiry_date': now.replace(year=now.year + random.randint(1, 5)),
            **{k: v for k, v in kwargs.items() if isinstance(v, datetime)}
        }

    @classmethod
    def create_list_data(cls, count: int = 5, **kwargs) -> List[Dict[str, Any]]:
        """创建列表型测试数据"""
        return [cls.create(**kwargs) for _ in range(count)]

    @classmethod
    def create_nested_data(cls, **kwargs) -> Dict[str, Any]:
        """创建嵌套型测试数据"""
        return {
            'id': cls.generate_id(),
            'name': random.choice(cls.NAMES),
            'profile': {
                'email': random.choice(cls.EMAILS),
                'phone': f"138{random.randint(10000000, 99999999)}",
                'address': {
                    'city': random.choice(cls.CITIES),
                    'country': random.choice(cls.COUNTRIES),
                    'zipcode': f"{random.randint(100000, 999999)}"
                }
            },
            'settings': {
                'theme': random.choice(['light', 'dark']),
                'language': random.choice(['zh-CN', 'en-US']),
                'notifications': random.choice([True, False])
            },
            'activities': [
                {
                    'type': random.choice(['login', 'logout', 'update']),
                    'timestamp': cls.generate_timestamp(),
                    'details': f"活动详情_{random.randint(1, 100)}"
                } for _ in range(random.randint(1, 5))
            ],
            **kwargs
        }


class SequenceDataFactory(DataFactory):
    """序列数据工厂"""

    def __init__(self):
        self._counter = 0

    def create(self, **kwargs) -> Dict[str, Any]:
        """创建序列数据"""
        self._counter += 1
        default_data = {
            'sequence_id': self._counter,
            'order': self._counter,
            'prefix': f"SEQ_{self._counter:04d}",
            'name': f"序列数据_{self._counter}",
        }

        default_data.update(kwargs)
        return super().create(**default_data)

    def reset_counter(self) -> None:
        """重置计数器"""
        self._counter = 0


class RandomDataFactory(DataFactory):
    """随机数据工厂"""

    @classmethod
    def create_string(cls, length: int = 10) -> str:
        """生成随机字符串"""
        import string
        return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

    @classmethod
    def create_integer(cls, min_val: int = 1, max_val: int = 1000) -> int:
        """生成随机整数"""
        return random.randint(min_val, max_val)

    @classmethod
    def create_float(cls, min_val: float = 0.1, max_val: float = 99.9) -> float:
        """生成随机浮点数"""
        return round(random.uniform(min_val, max_val), 2)

    @classmethod
    def create_boolean(cls, probability: float = 0.5) -> bool:
        """生成随机布尔值"""
        return random.random() < probability

    @classmethod
    def create_choice(cls, choices: List[Any]) -> Any:
        """从选项中随机选择"""
        return random.choice(choices)

    @classmethod
    def create_choices(cls, choices: List[Any], count: int = 1) -> List[Any]:
        """从选项中随机选择多个"""
        return random.sample(choices, min(count, len(choices)))

    @classmethod
    def create_uuid(cls) -> str:
        """生成随机UUID"""
        return str(uuid.uuid4())

    @classmethod
    def create_timestamp(cls, start_year: int = 2020, end_year: int = 2024) -> datetime:
        """生成随机时间戳"""
        year = random.randint(start_year, end_year)
        month = random.randint(1, 12)
        day = random.randint(1, 28)  # 避免月份天数问题
        hour = random.randint(0, 23)
        minute = random.randint(0, 59)
        second = random.randint(0, 59)

        return datetime(year, month, day, hour, minute, second, tzinfo=timezone.utc)