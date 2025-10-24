"""
Mock Factory - 统一的测试Mock对象创建
提供预配置的高质量Mock对象，简化测试代码编写
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union
from unittest.mock import Mock, AsyncMock, MagicMock

from tests.factories.data_factory import DataFactory


class MockFactory:
    """
    Mock对象工厂类
    提供各种预配置的Mock对象，确保测试的一致性和可维护性
    """

    # 默认配置常量
    DEFAULT_USER_ID = "test_user_123"
    DEFAULT_USERNAME = "testuser"
    DEFAULT_EMAIL = "test@example.com"
    DEFAULT_MATCH_ID = 999
    DEFAULT_TEAM_ID = "team_123"
    DEFAULT_LEAGUE_ID = "league_456"

    @classmethod
    def mock_user(cls, overrides: Dict[str, Any] = None) -> Mock:
        """
        创建Mock用户对象

        Args:
            overrides: 覆盖默认属性的字段

        Returns:
            Mock: 配置好的用户Mock对象
        """
        if overrides is None:
            overrides = {}

        mock = Mock()
        mock.id = overrides.get('id', cls.DEFAULT_USER_ID)
        mock.username = overrides.get('username', cls.DEFAULT_USERNAME)
        mock.email = overrides.get('email', cls.DEFAULT_EMAIL)
        mock.hashed_password = overrides.get('hashed_password', 'hashed_password_123')
        mock.is_active = overrides.get('is_active', True)
        mock.is_verified = overrides.get('is_verified', True)
        mock.is_admin = overrides.get('is_admin', False)
        mock.is_analyst = overrides.get('is_analyst', False)
        mock.created_at = overrides.get('created_at', datetime.now(timezone.utc))
        mock.last_login = overrides.get('last_login', datetime.now(timezone.utc))

        # 添加常用的方法
        mock.check_password.return_value = True
        mock.update_last_login = Mock()
        mock.to_dict.return_value = {
            'id': mock.id,
            'username': mock.username,
            'email': mock.email,
            'is_active': mock.is_active,
            'is_admin': mock.is_admin,
            'created_at': mock.created_at.isoformat()
        }

        return mock

    @classmethod
    def mock_admin_user(cls, overrides: Dict[str, Any] = None) -> Mock:
        """
        创建Mock管理员用户

        Args:
            overrides: 覆盖默认属性的字段

        Returns:
            Mock: 配置好的管理员Mock对象
        """
        admin_overrides = {
            'username': 'admin',
            'email': 'admin@example.com',
            'is_admin': True,
            'is_active': True
        }
        if overrides:
            admin_overrides.update(overrides)

        return cls.mock_user(admin_overrides)

    @classmethod
    def mock_match(cls, overrides: Dict[str, Any] = None) -> Mock:
        """
        创建Mock比赛对象

        Args:
            overrides: 覆盖默认属性的字段

        Returns:
            Mock: 配置好的比赛Mock对象
        """
        if overrides is None:
            overrides = {}

        mock = Mock()
        mock.id = overrides.get('id', cls.DEFAULT_MATCH_ID)
        mock.home_team = overrides.get('home_team', 'Team A')
        mock.away_team = overrides.get('away_team', 'Team B')
        mock.home_score = overrides.get('home_score', None)
        mock.away_score = overrides.get('away_score', None)
        mock.status = overrides.get('status', 'upcoming')
        mock.match_date = overrides.get('match_date', datetime.now(timezone.utc))
        mock.created_at = overrides.get('created_at', datetime.now(timezone.utc))

        # 添加常用的方法
        mock.to_dict.return_value = {
            'id': mock.id,
            'home_team': mock.home_team,
            'away_team': mock.away_team,
            'home_score': mock.home_score,
            'away_score': mock.away_score,
            'status': mock.status,
            'match_date': mock.match_date.isoformat()
        }

        return mock

    @classmethod
    def mock_prediction(cls, overrides: Dict[str, Any] = None) -> Mock:
        """
        创建Mock预测对象

        Args:
            overrides: 覆盖默认属性的字段

        Returns:
            Mock: 配置好的预测Mock对象
        """
        if overrides is None:
            overrides = {}

        mock = Mock()
        mock.id = overrides.get('id', 'prediction_123')
        mock.match_id = overrides.get('match_id', cls.DEFAULT_MATCH_ID)
        mock.user_id = overrides.get('user_id', cls.DEFAULT_USER_ID)
        mock.predicted_home_score = overrides.get('predicted_home_score', 2)
        mock.predicted_away_score = overrides.get('predicted_away_score', 1)
        mock.confidence = overrides.get('confidence', 0.85)
        mock.is_correct = overrides.get('is_correct', None)
        mock.created_at = overrides.get('created_at', datetime.now(timezone.utc))

        # 添加常用的方法
        mock.to_dict.return_value = {
            'id': mock.id,
            'match_id': mock.match_id,
            'user_id': mock.user_id,
            'predicted_home_score': mock.predicted_home_score,
            'predicted_away_score': mock.predicted_away_score,
            'confidence': mock.confidence,
            'is_correct': mock.is_correct,
            'created_at': mock.created_at.isoformat()
        }

        return mock

    @classmethod
    def mock_team(cls, overrides: Dict[str, Any] = None) -> Mock:
        """
        创建Mock球队对象

        Args:
            overrides: 覆盖默认属性的字段

        Returns:
            Mock: 配置好的球队Mock对象
        """
        if overrides is None:
            overrides = {}

        mock = Mock()
        mock.id = overrides.get('id', cls.DEFAULT_TEAM_ID)
        mock.name = overrides.get('name', 'Test Team FC')
        mock.short_name = overrides.get('short_name', 'TTF')
        mock.country = overrides.get('country', 'Test Country')
        mock.league_id = overrides.get('league_id', cls.DEFAULT_LEAGUE_ID)
        mock.created_at = overrides.get('created_at', datetime.now(timezone.utc))

        mock.to_dict.return_value = {
            'id': mock.id,
            'name': mock.name,
            'short_name': mock.short_name,
            'country': mock.country,
            'league_id': mock.league_id
        }

        return mock

    @classmethod
    def mock_league(cls, overrides: Dict[str, Any] = None) -> Mock:
        """
        创建Mock联赛对象

        Args:
            overrides: 覆盖默认属性的字段

        Returns:
            Mock: 配置好的联赛Mock对象
        """
        if overrides is None:
            overrides = {}

        mock = Mock()
        mock.id = overrides.get('id', cls.DEFAULT_LEAGUE_ID)
        mock.name = overrides.get('name', 'Test League')
        mock.country = overrides.get('country', 'Test Country')
        mock.season = overrides.get('season', '2024-2025')
        mock.created_at = overrides.get('created_at', datetime.now(timezone.utc))

        mock.to_dict.return_value = {
            'id': mock.id,
            'name': mock.name,
            'country': mock.country,
            'season': mock.season
        }

        return mock

    @classmethod
    def mock_repository(cls, repository_type: str = "base", overrides: Dict[str, Any] = None) -> Mock:
        """
        创建Mock仓储对象

        Args:
            repository_type: 仓储类型 (user, match, prediction, base)
            overrides: 覆盖默认行为的配置

        Returns:
            Mock: 配置好的仓储Mock对象
        """
        if overrides is None:
            overrides = {}

        mock = Mock()
        mock._data = {}

        # 基础仓储方法
        mock.get = Mock(side_effect=lambda id: mock._data.get(id))
        mock.get_all = Mock(return_value=list(mock._data.values()))
        mock.create = Mock(side_effect=lambda obj: mock._create(obj))
        mock.update = Mock(side_effect=lambda id, data: mock._update(id, data))
        mock.delete = Mock(side_effect=lambda id: mock._delete(id))
        mock.count = Mock(return_value=len(mock._data))

        def _create(obj):
            obj.id = DataFactory.random_string(10)
            mock._data[obj.id] = obj
            return obj

        def _update(id, data):
            if id in mock._data:
                for key, value in data.items():
                    setattr(mock._data[id], key, value)
                return mock._data[id]
            return None

        def _delete(id):
            return mock._data.pop(id, None)

        mock._create = _create
        mock._update = _update
        mock._delete = _delete

        # 根据仓储类型添加特定方法
        if repository_type == "user":
            mock.get_by_username = Mock(side_effect=lambda username: next((u for u in mock._data.values() if hasattr(u, 'username') and u.username == username), None))
            mock.get_by_email = Mock(side_effect=lambda email: next((u for u in mock._data.values() if hasattr(u, 'email') and u.email == email), None))
            mock.verify_password = AsyncMock(return_value=overrides.get('password_valid', True))
        elif repository_type == "match":
            mock.get_by_status = Mock(side_effect=lambda status: [m for m in mock._data.values() if hasattr(m, 'status') and m.status == status])
            mock.get_by_date_range = Mock(side_effect=lambda start, end: [m for m in mock._data.values() if hasattr(m, 'match_date') and start <= m.match_date <= end])
            mock.get_by_team = Mock(side_effect=lambda team: [m for m in mock._data.values() if hasattr(m, 'home_team') and (m.home_team == team or m.away_team == team)])
        elif repository_type == "prediction":
            mock.get_by_user = Mock(side_effect=lambda user_id: [p for p in mock._data.values() if hasattr(p, 'user_id') and p.user_id == user_id])
            mock.get_by_match = Mock(side_effect=lambda match_id: [p for p in mock._data.values() if hasattr(p, 'match_id') and p.match_id == match_id])

        return mock

    @classmethod
    def mock_database_connection(cls, overrides: Dict[str, Any] = None) -> Mock:
        """
        创建Mock数据库连接

        Args:
            overrides: 覆盖默认行为的配置

        Returns:
            Mock: 配置好的数据库连接Mock对象
        """
        if overrides is None:
            overrides = {}

        mock = Mock()
        mock.engine = Mock()
        mock.session_factory = Mock()

        # 异步会话模拟
        mock_session = AsyncMock()
        mock_session.add = Mock()
        mock_session.commit = AsyncMock()
        mock_session.rollback = AsyncMock()
        mock_session.close = AsyncMock()
        mock_session.refresh = Mock()
        mock_session.delete = Mock()
        mock_session.execute = AsyncMock(return_value=Mock())

        # 支持上下文管理器
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock.get_session.return_value = mock_session

        return mock

    @classmethod
    def mock_redis_client(cls, overrides: Dict[str, Any] = None) -> Mock:
        """
        创建Mock Redis客户端

        Args:
            overrides: 覆盖默认行为的配置

        Returns:
            Mock: 配置好的Redis客户端Mock对象
        """
        if overrides is None:
            overrides = {}

        mock = Mock()
        mock._data = overrides.get('data', {})

        # 异步方法
        mock.get = AsyncMock(side_effect=lambda key: mock._redis_get(key))
        mock.set = AsyncMock(side_effect=lambda key, value, ex=None: mock._redis_set(key, value))
        mock.delete = AsyncMock(side_effect=lambda key: mock._data.pop(key, None))
        mock.exists = AsyncMock(side_effect=lambda key: key in mock._data)
        mock.expire = AsyncMock(return_value=True)
        mock.ping = AsyncMock(return_value=True)

        def _redis_get(key):
            value = mock._data.get(key)
            if value is None:
                return None
            # 如果是JSON字符串，尝试解析
            if isinstance(value, str) and (value.startswith('{') or value.startswith('[')):
                try:
                    import json
                    return json.loads(value)
                except:
                    return value
            return value

        def _redis_set(key, value):
            if isinstance(value, (dict, list)):
                import json
                mock._data[key] = json.dumps(value)
            else:
                mock._data[key] = str(value)

        mock._redis_get = _redis_get
        mock._redis_set = _redis_set

        # 同步方法
        mock.get_sync = Mock(side_effect=_redis_get)
        mock.set_sync = Mock(side_effect=_redis_set)

        return mock

    @classmethod
    def mock_api_client(cls, overrides: Dict[str, Any] = None) -> Mock:
        """
        创建Mock API客户端

        Args:
            overrides: 覆盖默认行为的配置

        Returns:
            Mock: 配置好的API客户端Mock对象
        """
        if overrides is None:
            overrides = {}

        mock = Mock()

        # 响应对象模拟
        mock_response = Mock()
        mock_response.status_code = overrides.get('status_code', 200)
        mock_response.json.return_value = overrides.get('response_data', DataFactory.api_response_data())
        mock_response.text = overrides.get('response_text', '{"success": true}')
        mock_response.headers = overrides.get('response_headers', {})

        # HTTP方法模拟
        mock.get = AsyncMock(return_value=mock_response)
        mock.post = AsyncMock(return_value=mock_response)
        mock.put = AsyncMock(return_value=mock_response)
        mock.delete = AsyncMock(return_value=Mock(status_code=204, json=Mock(return_value=None), text=""))

        # 配置
        mock.base_url = overrides.get('base_url', "https://api.example.com")
        mock.headers = overrides.get('headers', {"Authorization": "Bearer token123"})
        mock.timeout = overrides.get('timeout', 30)

        return mock

    @classmethod
    def mock_cache_service(cls, overrides: Dict[str, Any] = None) -> Mock:
        """
        创建Mock缓存服务

        Args:
            overrides: 覆盖默认行为的配置

        Returns:
            Mock: 配置好的缓存服务Mock对象
        """
        if overrides is None:
            overrides = {}

        mock = Mock()
        mock.cache = overrides.get('cache_data', {})

        mock.get = AsyncMock(side_effect=lambda key: mock.cache.get(key))
        mock.set = AsyncMock(side_effect=lambda key, value, ttl=None: mock.cache.update({key: value}))
        mock.delete = AsyncMock(side_effect=lambda key: mock.cache.pop(key, None))
        mock.clear = AsyncMock(side_effect=lambda: mock.cache.clear())
        mock.exists = AsyncMock(side_effect=lambda key: key in mock.cache)
        mock.get_ttl = AsyncMock(return_value=overrides.get('ttl', 3600))

        return mock

    @classmethod
    def mock_logger(cls, overrides: Dict[str, Any] = None) -> Mock:
        """
        创建Mock日志器

        Args:
            overrides: 覆盖默认行为的配置

        Returns:
            Mock: 配置好的日志器Mock对象
        """
        mock = Mock()
        mock.info = Mock()
        mock.debug = Mock()
        mock.warning = Mock()
        mock.error = Mock()
        mock.critical = Mock()
        mock.exception = Mock()

        # 异步日志方法
        mock.info_async = AsyncMock()
        mock.debug_async = AsyncMock()
        mock.warning_async = AsyncMock()
        mock.error_async = AsyncMock()

        # 支持上下文管理器
        mock.__enter__ = Mock(return_value=mock)
        mock.__exit__ = Mock(return_value=None)

        return mock

    @classmethod
    def mock_event_bus(cls, overrides: Dict[str, Any] = None) -> Mock:
        """
        创建Mock事件总线

        Args:
            overrides: 覆盖默认行为的配置

        Returns:
            Mock: 配置好的事件总线Mock对象
        """
        if overrides is None:
            overrides = {}

        mock = Mock()
        mock.handlers = overrides.get('handlers', {})
        mock.events = overrides.get('events', [])

        mock.subscribe = Mock(side_effect=lambda event, handler: mock.handlers.setdefault(event, []).append(handler))
        mock.unsubscribe = Mock(side_effect=lambda event, handler: mock.handlers.get(event, []).remove(handler) if event in mock.handlers else None)
        mock.publish = AsyncMock(side_effect=lambda event, data: mock._publish(event, data))
        mock.clear = Mock(side_effect=lambda: mock.handlers.clear())

        def _publish(event, data):
            mock.events.append({'event': event, 'data': data, 'timestamp': datetime.now(timezone.utc)})
            if event in mock.handlers:
                for handler in mock.handlers[event]:
                    if asyncio.iscoroutinefunction(handler):
                        asyncio.create_task(handler(data))
                    else:
                        handler(data)

        mock._publish = _publish

        return mock

    @classmethod
    def mock_scheduler(cls, overrides: Dict[str, Any] = None) -> Mock:
        """
        创建Mock任务调度器

        Args:
            overrides: 覆盖默认行为的配置

        Returns:
            Mock: 配置好的任务调度器Mock对象
        """
        if overrides is None:
            overrides = {}

        mock = Mock()
        mock.jobs = overrides.get('jobs', [])
        mock.running = overrides.get('running', False)

        mock.add_job = Mock(side_effect=lambda func, trigger, **kwargs: mock._add_job(func, trigger, kwargs))
        mock.remove_job = Mock(side_effect=lambda job_id: mock._remove_job(job_id))
        mock.start = AsyncMock(return_value=True)
        mock.stop = AsyncMock(return_value=True)
        mock.get_jobs = Mock(return_value=mock.jobs)
        mock.pause_job = Mock(return_value=True)
        mock.resume_job = Mock(return_value=True)

        def _add_job(func, trigger, kwargs):
            job = Mock()
            job.id = DataFactory.random_string(10)
            job.func = func
            job.trigger = trigger
            job.kwargs = kwargs
            job.next_run_time = DataFactory.future_date()
            mock.jobs.append(job)
            return job

        def _remove_job(job_id):
            mock.jobs = [job for job in mock.jobs if job.id != job_id]

        mock._add_job = _add_job
        mock._remove_job = _remove_job

        return mock

    @classmethod
    def mock_email_service(cls, overrides: Dict[str, Any] = None) -> Mock:
        """
        创建Mock邮件服务

        Args:
            overrides: 覆盖默认行为的配置

        Returns:
            Mock: 配置好的邮件服务Mock对象
        """
        if overrides is None:
            overrides = {}

        mock = Mock()
        mock.sent_emails = overrides.get('sent_emails', [])

        mock.send_email = AsyncMock(side_effect=lambda to, subject, body, **kwargs: mock._record_email(to, subject, body, kwargs))
        mock.send_template = AsyncMock(side_effect=lambda template, to, context, **kwargs: mock._record_template_email(template, to, context, kwargs))
        mock.send_bulk = AsyncMock(return_value=True)
        mock.get_sent_emails = Mock(return_value=mock.sent_emails)
        mock.clear_sent = Mock(side_effect=lambda: mock.sent_emails.clear())

        def _record_email(to, subject, body, kwargs):
            email = {
                'to': to,
                'subject': subject,
                'body': body,
                'kwargs': kwargs,
                'timestamp': datetime.now(timezone.utc)
            }
            mock.sent_emails.append(email)
            return True

        def _record_template_email(template, to, context, kwargs):
            email = {
                'template': template,
                'to': to,
                'context': context,
                'kwargs': kwargs,
                'timestamp': datetime.now(timezone.utc)
            }
            mock.sent_emails.append(email)
            return True

        mock._record_email = _record_email
        mock._record_template_email = _record_template_email

        return mock

    @classmethod
    def create_batch(cls, factory_method, count: int, **overrides) -> List[Mock]:
        """
        批量创建Mock对象

        Args:
            factory_method: MockFactory的工厂方法
            count: 创建数量
            **overrides: 覆盖默认属性的字段

        Returns:
            List[Mock]: Mock对象列表
        """
        mocks = []
        for i in range(count):
            item_overrides = overrides.copy()
            if 'id' in overrides and isinstance(overrides['id'], str):
                item_overrides['id'] = f"{overrides['id']}_{i+1}"
            elif 'id' in overrides and isinstance(overrides['id'], int):
                item_overrides['id'] = overrides['id'] + i

            mocks.append(factory_method(item_overrides))

        return mocks

    @classmethod
    def create_test_context(cls, **components) -> Dict[str, Any]:
        """
        创建完整的测试上下文

        Args:
            **components: 要包含的组件类型

        Returns:
            Dict[str, Any]: 包含所有Mock组件的测试上下文
        """
        context = {}

        # 默认包含所有组件
        include_all = not components

        if include_all or 'users' in components:
            context['users'] = cls.create_batch(cls.mock_user, components.get('user_count', 3))
            context['admin_user'] = cls.mock_admin_user()

        if include_all or 'matches' in components:
            context['matches'] = cls.create_batch(cls.mock_match, components.get('match_count', 5))

        if include_all or 'predictions' in components:
            context['predictions'] = cls.create_batch(cls.mock_prediction, components.get('prediction_count', 10))

        if include_all or 'teams' in components:
            context['teams'] = cls.create_batch(cls.mock_team, components.get('team_count', 8))

        if include_all or 'repositories' in components:
            context['user_repo'] = cls.mock_repository('user')
            context['match_repo'] = cls.mock_repository('match')
            context['prediction_repo'] = cls.mock_repository('prediction')

        if include_all or 'services' in components:
            context['db'] = cls.mock_database_connection()
            context['redis'] = cls.mock_redis_client()
            context['cache'] = cls.mock_cache_service()
            context['api_client'] = cls.mock_api_client()
            context['logger'] = cls.mock_logger()
            context['event_bus'] = cls.mock_event_bus()
            context['scheduler'] = cls.mock_scheduler()
            context['email_service'] = cls.mock_email_service()

        return context


# 便捷函数，用于快速创建常用Mock对象
def create_mock_user(**overrides) -> Mock:
    """便捷函数：创建Mock用户"""
    return MockFactory.mock_user(overrides)


def create_mock_match(**overrides) -> Mock:
    """便捷函数：创建Mock比赛"""
    return MockFactory.mock_match(overrides)


def create_mock_prediction(**overrides) -> Mock:
    """便捷函数：创建Mock预测"""
    return MockFactory.mock_prediction(overrides)


def create_mock_repository(repo_type: str = "base", **overrides) -> Mock:
    """便捷函数：创建Mock仓储"""
    return MockFactory.mock_repository(repo_type, overrides)


def create_mock_database(**overrides) -> Mock:
    """便捷函数：创建Mock数据库连接"""
    return MockFactory.mock_database_connection(overrides)


def create_mock_redis(**overrides) -> Mock:
    """便捷函数：创建Mock Redis客户端"""
    return MockFactory.mock_redis_client(overrides)


def create_test_context(**components) -> Dict[str, Any]:
    """便捷函数：创建测试上下文"""
    return MockFactory.create_test_context(**components)