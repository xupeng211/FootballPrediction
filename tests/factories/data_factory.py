"""数据工厂 - 生成各种测试数据"""

from __future__ import annotations

import secrets
import string
from datetime import datetime, timedelta
from typing import Any, Dict, List

from faker import Faker

fake = Faker("zh_CN")


class DataFactory:
    """生成各种测试数据的工厂类"""

    @staticmethod
    def random_string(length: int = 10) -> str:
        """生成随机字符串"""
        return "".join(
            secrets.choice(string.ascii_letters + string.digits) for _ in range(length)
        )

    @staticmethod
    def random_email() -> str:
        """生成随机邮箱"""
        return fake.email()

    @staticmethod
    def random_phone() -> str:
        """生成随机手机号"""
        return fake.phone_number()

    @staticmethod
    def random_url() -> str:
        """生成随机URL"""
        return fake.url()

    @staticmethod
    def random_date(start_date: datetime = None, end_date: datetime = None) -> datetime:
        """生成随机日期"""
        if start_date is None:
            start_date = datetime.now() - timedelta(days=365)
        if end_date is None:
            end_date = datetime.now()
        return fake.date_time_between(start_date=start_date, end_date=end_date)

    @staticmethod
    def future_date(days: int = 30) -> datetime:
        """生成未来日期"""
        return datetime.now() + timedelta(days=secrets.randbelow(days) + 1)

    @staticmethod
    def past_date(days: int = 30) -> datetime:
        """生成过去日期"""
        return datetime.now() - timedelta(days=secrets.randbelow(days) + 1)

    @staticmethod
    def random_ip() -> str:
        """生成随机IP地址"""
        return fake.ipv4()

    @staticmethod
    def random_json_data() -> Dict[str, Any]:
        """生成随机JSON数据"""
        return {
            "id": fake.random_int(min=1, max=1000),
            "name": fake.name(),
            "email": fake.email(),
            "created_at": fake.iso8601(),
            "active": fake.boolean(),
            "tags": [fake.word() for _ in range(secrets.randbelow(5) + 1)],
            "score": round(fake.random.uniform(0, 100), 2),
        }

    @staticmethod
    def user_data(overrides: Dict[str, Any] = None) -> Dict[str, Any]:
        """生成用户数据"""
        data = {
            "username": fake.user_name(),
            "email": fake.email(),
            "full_name": fake.name(),
            "password": DataFactory.random_string(12),
            "is_active": True,
            "is_verified": True,
            "timezone": fake.timezone(),
        }
        if overrides:
            data.update(overrides)
        return data

    @staticmethod
    def match_data(overrides: Dict[str, Any] = None) -> Dict[str, Any]:
        """生成比赛数据"""
        data = {
            "home_team": fake.company(),
            "away_team": fake.company(),
            "league": fake.country(),
            "match_date": DataFactory.future_date(days=7),
            "venue": fake.city() + " Stadium",
            "status": secrets.choice(["scheduled", "live", "finished", "postponed"]),
        }
        if overrides:
            data.update(overrides)
        return data

    @staticmethod
    def prediction_data(overrides: Dict[str, Any] = None) -> Dict[str, Any]:
        """生成预测数据"""
        data = {
            "match_id": fake.random_int(min=1, max=10000),
            "prediction": secrets.choice(["home_win", "away_win", "draw"]),
            "confidence": round(fake.random.uniform(0.5, 1.0), 2),
            "odds": round(fake.random.uniform(1.5, 5.0), 2),
            "stake": round(fake.random.uniform(10, 1000), 2),
            "created_at": fake.iso8601(),
        }
        if overrides:
            data.update(overrides)
        return data

    @staticmethod
    def api_response_data(success: bool = True, data: Any = None) -> Dict[str, Any]:
        """生成API响应数据"""
        response = {
            "success": success,
            "message": "Success" if success else "Error",
            "timestamp": fake.iso8601(),
            "request_id": DataFactory.random_string(20),
        }
        if data is not None:
            response["data"] = data
        if not success:
            response["error_code"] = secrets.randbelow(1000)
            response["error_details"] = fake.sentence()
        return response

    @staticmethod
    def batch_data(factory_func, count: int, **kwargs) -> List[Any]:
        """批量生成数据"""
        return [factory_func(**kwargs) for _ in range(count)]

    @staticmethod
    def unique_values(factory_func, count: int, **kwargs) -> List[Any]:
        """生成唯一的值列表"""
        seen = set()
        result = []
        while len(result) < count:
            value = factory_func(**kwargs)
            if value not in seen:
                seen.add(value)
                result.append(value)
        return result
