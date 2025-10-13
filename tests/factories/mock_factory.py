"""Mock对象工厂 - 创建测试用的Mock对象"""

from __future__ import annotations

from unittest.mock import MagicMock, Mock
from typing import Any, Dict, List, Optional
import asyncio
from datetime import datetime

from tests.factories.data_factory import DataFactory


class MockFactory:
    """创建各种Mock对象的工厂类"""

    @staticmethod
    def mock_user(overrides: Dict[str, Any] = None) -> Mock:
        """创建Mock用户对象"""
        mock = Mock()
        mock.id = DataFactory.random_string(10)
        mock.username = DataFactory.random_string(8)
        mock.email = DataFactory.random_email()
        mock.is_active = True
        mock.is_verified = True
        mock.is_admin = False
        mock.is_analyst = False
        mock.created_at = datetime.now()
        mock.last_login = datetime.now()

        # 添加方法
        mock.check_password = Mock(return_value=True)
        mock.update_last_login = Mock()
        mock.to_dict = Mock(
            return_value={
                "id": mock.id,
                "username": mock.username,
                "email": mock.email,
                "is_active": mock.is_active,
            }
        )

        if overrides:
            for key, value in overrides.items():
                setattr(mock, key, value)

        return mock

    @staticmethod
    def mock_repository(model_class: Any = None) -> Mock:
        """创建Mock仓储对象"""
        mock = Mock()
        mock._data = {}

        # 仓储方法
        mock.get = Mock(side_effect=lambda id: mock.data.get(id))
        mock.get_all = Mock(return_value=list(mock.data.values()))
        mock.create = Mock(side_effect=lambda obj: mock._create(obj))
        mock.update = Mock(side_effect=lambda id, data: mock._update(id, data))
        mock.delete = Mock(side_effect=lambda id: mock._delete(id))
        mock.filter = Mock(return_value=list(mock.data.values()))
        mock.count = Mock(return_value=len(mock.data))

        def _create(obj):
            obj.id = DataFactory.random_string(10)
            mock.data[obj.id] = obj
            return obj

        def _update(id, data):
            if id in mock.data:
                for key, value in data.items():
                    setattr(mock.data[id], key, value)
                return mock.data[id]
            return None

        def _delete(id):
            return mock.data.pop(id, None)

        mock._create = _create
        mock._update = _update
        mock._delete = _delete

        return mock

    @staticmethod
    def mock_database_connection() -> Mock:
        """创建Mock数据库连接"""
        mock = Mock()
        mock.execute = Mock(return_value=MagicMock())
        mock.fetch_one = Mock(return_value=None)
        mock.fetch_all = Mock(return_value=[])
        mock.fetch_val = Mock(return_value=None)
        mock.transaction = Mock()
        mock.commit = Mock()
        mock.rollback = Mock()
        mock.close = Mock()
        return mock

    @staticmethod
    def mock_redis_client() -> Mock:
        """创建Mock Redis客户端"""
        mock = Mock()
        mock._data = {}

        mock.get = Mock(side_effect=lambda key: mock.data.get(key))
        mock.set = Mock(side_effect=lambda key, value, ex=None: mock._set(key, value))
        mock.delete = Mock(side_effect=lambda key: mock.data.pop(key, None))
        mock.exists = Mock(side_effect=lambda key: key in mock.data)
        mock.expire = Mock(return_value=True)
        mock.flushall = Mock(return_value=True)
        mock.ping = Mock(return_value=True)

        def _set(key, value):
            if isinstance(value, (dict, list)):
                import json

                mock.data[key] = json.dumps(value)
            else:
                mock.data[key] = str(value)

        mock._set = _set

        return mock

    @staticmethod
    def mock_api_client() -> Mock:
        """创建Mock API客户端"""
        mock = Mock()

        # HTTP方法
        mock.get = Mock(
            return_value=Mock(
                status_code=200,
                json=Mock(return_value=DataFactory.api_response_data()),
                text='{"success": true}',
            )
        )
        mock.post = Mock(
            return_value=Mock(
                status_code=201,
                json=Mock(return_value=DataFactory.api_response_data()),
                text='{"success": true}',
            )
        )
        mock.put = Mock(
            return_value=Mock(
                status_code=200,
                json=Mock(return_value=DataFactory.api_response_data()),
                text='{"success": true}',
            )
        )
        mock.delete = Mock(
            return_value=Mock(status_code=204, json=Mock(return_value=None), text="")
        )

        # 配置
        mock.base_url = "https://api.example.com"
        mock.headers = {"Authorization": "Bearer token123"}
        mock.timeout = 30

        return mock

    @staticmethod
    def mock_cache_service() -> Mock:
        """创建Mock缓存服务"""
        mock = Mock()
        mock.cache = {}

        mock.get = Mock(side_effect=lambda key: mock.cache.get(key))
        mock.set = Mock(
            side_effect=lambda key, value, ttl=None: mock.cache.update({key: value})
        )
        mock.delete = Mock(side_effect=lambda key: mock.cache.pop(key, None))
        mock.clear = Mock(side_effect=lambda: mock.cache.clear())
        mock.exists = Mock(side_effect=lambda key: key in mock.cache)
        mock.get_ttl = Mock(return_value=3600)

        return mock

    @staticmethod
    def mock_logger() -> Mock:
        """创建Mock日志器"""
        mock = Mock()
        mock.debug = Mock()
        mock.info = Mock()
        mock.warning = Mock()
        mock.error = Mock()
        mock.critical = Mock()
        mock.exception = Mock()
        mock.log = Mock()

        # 支持上下文管理器
        mock.__enter__ = Mock(return_value=mock)
        mock.__exit__ = Mock(return_value=None)

        return mock

    @staticmethod
    def mock_event_bus() -> Mock:
        """创建Mock事件总线"""
        mock = Mock()
        mock.handlers = {}

        mock.subscribe = Mock(
            side_effect=lambda event, handler: mock.handlers.setdefault(
                event, []
            ).append(handler)
        )
        mock.unsubscribe = Mock(
            side_effect=lambda event, handler: mock.handlers.get(event, []).remove(
                handler
            )
            if event in mock.handlers
            else None
        )
        mock.publish = Mock(side_effect=lambda event, data: mock._publish(event, data))
        mock.clear = Mock(side_effect=lambda: mock.handlers.clear())

        def _publish(event, data):
            if event in mock.handlers:
                for handler in mock.handlers[event]:
                    if asyncio.iscoroutinefunction(handler):
                        asyncio.create_task(handler(data))
                    else:
                        handler(data)

        mock._publish = _publish

        return mock

    @staticmethod
    def mock_scheduler() -> Mock:
        """创建Mock任务调度器"""
        mock = Mock()
        mock.jobs = []

        mock.add_job = Mock(
            side_effect=lambda func, trigger, **kwargs: mock._add_job(
                func, trigger, kwargs
            )
        )
        mock.remove_job = Mock(side_effect=lambda job_id: mock._remove_job(job_id))
        mock.start = Mock()
        mock.stop = Mock()
        mock.pause_job = Mock()
        mock.resume_job = Mock()
        mock.get_jobs = Mock(return_value=mock.jobs)

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

    @staticmethod
    def mock_file_storage() -> Mock:
        """创建Mock文件存储"""
        mock = Mock()
        mock.files = {}

        mock.save = Mock(side_effect=lambda path, content: mock._save(path, content))
        mock.load = Mock(side_effect=lambda path: mock.files.get(path))
        mock.delete = Mock(side_effect=lambda path: mock.files.pop(path, None))
        mock.exists = Mock(side_effect=lambda path: path in mock.files)
        mock.list_files = Mock(
            side_effect=lambda path: [
                k for k in mock.files.keys() if k.startswith(path)
            ]
        )
        mock.get_size = Mock(
            side_effect=lambda path: len(str(mock.files.get(path, "")))
        )

        def _save(path, content):
            mock.files[path] = content
            return len(str(content))

        mock._save = _save

        return mock

    @staticmethod
    def mock_email_service() -> Mock:
        """创建Mock邮件服务"""
        mock = Mock()
        mock.sent_emails = []

        mock.send_email = Mock(
            side_effect=lambda to, subject, body, **kwargs: mock._send(
                to, subject, body
            )
        )
        mock.send_template = Mock(
            side_effect=lambda to, template, data, **kwargs: mock._send_template(
                to, template, data
            )
        )
        mock.send_bulk = Mock(side_effect=lambda emails: mock._send_bulk(emails))
        mock.get_sent_count = Mock(return_value=lambda: len(mock.sent_emails))
        mock.clear_sent = Mock(side_effect=lambda: mock.sent_emails.clear())

        def _send(to, subject, body):
            email = {
                "to": to,
                "subject": subject,
                "body": body,
                "sent_at": datetime.now(),
                "id": DataFactory.random_string(20),
            }
            mock.sent_emails.append(email)
            return email["id"]

        def _send_template(to, template, data):
            subject = f"[{template}] {data.get('subject', 'No Subject')}"
            body = f"Template: {template}\nData: {data}"
            return mock._send(to, subject, body)

        def _send_bulk(emails):
            results = []
            for email in emails:
                _result = mock._send(
                    email.get("to"), email.get("subject"), email.get("body")
                )
                results.append(result)
            return results

        mock._send = _send
        mock._send_template = _send_template
        mock._send_bulk = _send_bulk

        return mock
