#!/usr/bin/env python3
"""
客户端模块
Football Prediction SDK - 主客户端类

Author: Claude Code
Version: 1.0.0
"""

import builtins
from datetime import datetime
from typing import Any

import requests

from .auth import AuthManager
from .exceptions import FootballPredictionError, create_exception_from_response
from .models import (
    Match,
    MatchListResponse,
    Prediction,
    PredictionRequest,
    PredictionResponse,
    UserProfileResponse,
    UserStatistics,
)
from .utils import parse_api_error, rate_limit_handler, retry_with_backoff


class PredictionAPI:
    """预测API管理"""

    def __init__(self, client: "FootballPredictionClient"):
        self.client = client

    @retry_with_backoff(max_retries=3)
    def create(self, request: PredictionRequest) -> PredictionResponse:
        """
        创建预测请求

        Args:
            request: 预测请求数据

        Returns:
            PredictionResponse: 预测响应

        Example:
            >>> request = PredictionRequest(
            ...     match_id="match_123",
            ...     home_team="Manchester United",
            ...     away_team="Liverpool",
            ...     match_date=datetime(2025, 11, 15, 20, 0),
            ...     league="Premier League"
            ... )
            >>> response = predictions.create(request)
            >>> prediction_id = response.prediction.prediction_id
        """
        try:
            url = f"{self.client.base_url}/predictions/enhanced"
            data = request.to_dict()

            response = self.client.session.post(
                url,
                json=data,
                timeout=self.client.timeout
            )

            if response.status_code == 200:
                return PredictionResponse.from_dict(response.json())
            else:
                # 检查是否是限流错误
                rate_limit_error = rate_limit_handler(response)
                if rate_limit_error:
                    raise rate_limit_error

                # 其他错误
                error_data = parse_api_error(response)
                raise create_exception_from_response(error_data, response)

        except requests.exceptions.RequestException as e:
            raise FootballPredictionError(f"创建预测失败: {str(e)}")

    @retry_with_backoff(max_retries=2)
    def get(self, prediction_id: str) -> Prediction | None:
        """
        获取预测结果

        Args:
            prediction_id: 预测ID

        Returns:
            Optional[Prediction]: 预测对象，如果不存在则返回None

        Example:
            >>> prediction = predictions.get("pred_12345")
            >>> if prediction:
            ...     print(f"主胜概率: {prediction.probabilities['home_win']:.2%}")
        """
        try:
            url = f"{self.client.base_url}/predictions/{prediction_id}"
            response = self.client.session.get(url, timeout=self.client.timeout)

            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    prediction_data = data.get("data")
                    return Prediction.from_dict(prediction_data)
            elif response.status_code == 404:
                return None
            else:
                error_data = parse_api_error(response)
                raise create_exception_from_response(error_data, response)

        except requests.exceptions.RequestException as e:
            raise FootballPredictionError(f"获取预测失败: {str(e)}")

    @retry_with_backoff(max_retries=2)
    def list(
        self,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
        date_from: datetime | None = None,
        date_to: datetime | None = None
    ) -> list[Prediction]:
        """
        获取预测历史列表

        Args:
            status: 状态筛选
            page: 页码
            page_size: 每页数量
            date_from: 开始日期
            date_to: 结束日期

        Returns:
            List[Prediction]: 预测列表

        Example:
            >>> predictions = predictions.list(
            ...     status="completed",
            ...     page=1,
            ...     page_size=10
            ... )
            >>> print(f"找到 {len(predictions)} 个预测")
        """
        try:
            params = {
                "page": page,
                "page_size": min(page_size, 100)  # 限制最大页面大小
            }

            if status:
                params["status"] = status
            if date_from:
                params["date_from"] = date_from.isoformat()
            if date_to:
                params["date_to"] = date_to.isoformat()

            url = f"{self.client.base_url}/predictions/history"
            response = self.client.session.get(url, params=params, timeout=self.client.timeout)

            if response.status_code == 200:
                data = response.json()
                predictions_data = data.get("data", [])
                return [Prediction.from_dict(pred_data) for pred_data in predictions_data]
            else:
                error_data = parse_api_error(response)
                raise create_exception_from_response(error_data, response)

        except requests.exceptions.RequestException as e:
            raise FootballPredictionError(f"获取预测列表失败: {str(e)}")

    @retry_with_backoff(max_retries=3)
    def batch_create(self, requests: builtins.list[PredictionRequest]) -> dict[str, Any]:
        """
        批量创建预测

        Args:
            requests: 预测请求列表

        Returns:
            Dict[str, Any]: 批量处理结果

        Example:
            >>> requests = [
            ...     PredictionRequest(...),
            ...     PredictionRequest(...)
            ... ]
            >>> result = predictions.batch_create(requests)
            >>> print(f"批量ID: {result['batch_id']}")
        """
        if len(requests) > 50:
            raise ValidationError("批量预测最多支持50个请求")

        try:
            url = f"{self.client.base_url}/predictions/batch"
            data = {
                "predictions": [req.to_dict() for req in requests]
            }

            response = self.client.session.post(
                url,
                json=data,
                timeout=self.client.timeout * 2  # 批量请求需要更长时间
            )

            if response.status_code == 200:
                return response.json().get("data", {})
            else:
                error_data = parse_api_error(response)
                raise create_exception_from_response(error_data, response)

        except requests.exceptions.RequestException as e:
            raise FootballPredictionError(f"批量创建预测失败: {str(e)}")


class MatchAPI:
    """比赛API管理"""

    def __init__(self, client: "FootballPredictionClient"):
        self.client = client

    @retry_with_backoff(max_retries=2)
    def get(self, match_id: str) -> Match | None:
        """
        获取比赛详情

        Args:
            match_id: 比赛ID

        Returns:
            Optional[Match]: 比赛对象，如果不存在则返回None

        Example:
            >>> match = matches.get("match_123")
            >>> if match:
            ...     print(f"比赛: {match.home_team.name} vs {match.away_team.name}")
        """
        try:
            url = f"{self.client.base_url}/matches/{match_id}"
            response = self.client.session.get(url, timeout=self.client.timeout)

            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    match_data = data.get("data")
                    return Match.from_dict(match_data)
            elif response.status_code == 404:
                return None
            else:
                error_data = parse_api_error(response)
                raise create_exception_from_response(error_data, response)

        except requests.exceptions.RequestException as e:
            raise FootballPredictionError(f"获取比赛详情失败: {str(e)}")

    @retry_with_backoff(max_retries=2)
    def list(
        self,
        league: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20
    ) -> MatchListResponse:
        """
        获取比赛列表

        Args:
            league: 联赛筛选
            date_from: 开始日期
            date_to: 结束日期
            status: 比赛状态筛选
            page: 页码
            page_size: 每页数量

        Returns:
            MatchListResponse: 比赛列表响应

        Example:
            >>> response = matches.list(
            ...     league="Premier League",
            ...     status="scheduled",
            ...     page=1,
            ...     page_size=10
            ... )
            >>> print(f"找到 {len(response.matches)} 场比赛")
        """
        try:
            params = {
                "page": page,
                "page_size": min(page_size, 100)
            }

            if league:
                params["league"] = league
            if date_from:
                params["date_from"] = date_from.isoformat()
            if date_to:
                params["date_to"] = date_to.isoformat()
            if status:
                params["status"] = status

            url = f"{self.client.base_url}/matches"
            response = self.client.session.get(url, params=params, timeout=self.client.timeout)

            if response.status_code == 200:
                return MatchListResponse.from_dict(response.json())
            else:
                error_data = parse_api_error(response)
                raise create_exception_from_response(error_data, response)

        except requests.exceptions.RequestException as e:
            raise FootballPredictionError(f"获取比赛列表失败: {str(e)}")

    @retry_with_backoff(max_retries=2)
    def get_leagues(self) -> builtins.list[dict[str, Any]]:
        """
        获取联赛列表

        Returns:
            List[Dict[str, Any]]: 联赛列表

        Example:
            >>> leagues = matches.get_leagues()
            >>> for league in leagues:
            ...     print(f"{league['name']} - {league['country']}")
        """
        try:
            url = f"{self.client.base_url}/leagues"
            response = self.client.session.get(url, timeout=self.client.timeout)

            if response.status_code == 200:
                data = response.json()
                return data.get("data", [])
            else:
                error_data = parse_api_error(response)
                raise create_exception_from_response(error_data, response)

        except requests.exceptions.RequestException as e:
            raise FootballPredictionError(f"获取联赛列表失败: {str(e)}")


class UserAPI:
    """用户API管理"""

    def __init__(self, client: "FootballPredictionClient"):
        self.client = client

    @retry_with_backoff(max_retries=2)
    def get_profile(self) -> UserProfileResponse:
        """
        获取用户配置信息

        Returns:
            UserProfileResponse: 用户配置响应

        Example:
            >>> response = users.get_profile()
            >>> user = response.user
            >>> print(f"用户: {user.username}")
            >>> print(f"订阅计划: {user.subscription.plan}")
        """
        try:
            url = f"{self.client.base_url}/user/profile"
            response = self.client.session.get(url, timeout=self.client.timeout)

            if response.status_code == 200:
                return UserProfileResponse.from_dict(response.json())
            else:
                error_data = parse_api_error(response)
                raise create_exception_from_response(error_data, response)

        except requests.exceptions.RequestException as e:
            raise FootballPredictionError(f"获取用户配置失败: {str(e)}")

    @retry_with_backoff(max_retries=2)
    def update_profile(self, preferences: dict[str, Any]) -> bool:
        """
        更新用户配置信息

        Args:
            preferences: 偏好设置

        Returns:
            bool: 是否更新成功

        Example:
            >>> success = users.update_profile({
            ...     "favorite_teams": ["Manchester United"],
            ...     "notification_settings": {"predictions": True}
            ... })
        """
        try:
            url = f"{self.client.base_url}/user/profile"
            response = self.client.session.put(
                url,
                json={"preferences": preferences},
                timeout=self.client.timeout
            )

            return response.status_code == 200

        except requests.exceptions.RequestException as e:
            raise FootballPredictionError(f"更新用户配置失败: {str(e)}")

    @retry_with_backoff(max_retries=2)
    def get_statistics(self) -> UserStatistics:
        """
        获取用户统计信息

        Returns:
            UserStatistics: 用户统计信息

        Example:
            >>> stats = users.get_statistics()
            >>> print(f"总预测数: {stats.total_predictions}")
            >>> print(f"成功率: {stats.success_percentage}")
        """
        try:
            url = f"{self.client.base_url}/user/statistics"
            response = self.client.session.get(url, timeout=self.client.timeout)

            if response.status_code == 200:
                data = response.json()
                stats_data = data.get("data", {})
                return UserStatistics.from_dict(stats_data)
            else:
                error_data = parse_api_error(response)
                raise create_exception_from_response(error_data, response)

        except requests.exceptions.RequestException as e:
            raise FootballPredictionError(f"获取用户统计失败: {str(e)}")


class FootballPredictionClient:
    """足球预测API客户端"""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.football-prediction.com/v1",
        timeout: int = 30,
        auto_retry: bool = True,
        user_agent: str = None,
        offline_mode: bool = False
    ):
        """
        初始化客户端

        Args:
            api_key: API密钥
            base_url: API基础URL
            timeout: 请求超时时间
            auto_retry: 是否自动重试失败的请求
            user_agent: 用户代理字符串
            offline_mode: 是否启用离线模式（不进行API调用）

        Example:
            >>> client = FootballPredictionClient(
            ...     api_key="your_api_key",
            ...     base_url="https://api.football-prediction.com/v1"
            ... )
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.auto_retry = auto_retry
        self.offline_mode = offline_mode

        # 初始化认证管理器
        self.auth = AuthManager(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
            auto_refresh=True
        )

        # 初始化API管理器
        self.predictions = PredictionAPI(self)
        self.matches = MatchAPI(self)
        self.users = UserAPI(self)

        # 创建会话
        self.session = requests.Session()

        # 设置用户代理
        if user_agent:
            self.session.headers["User-Agent"] = user_agent
        else:
            self.session.headers["User-Agent"] = "football-prediction-sdk/1.0.0"

        # 默认请求头
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json"
        })

        # 认证（仅在非离线模式下）
        if not offline_mode:
            try:
                self.authenticate()
            except Exception:
                self.offline_mode = True

    def authenticate(self, username: str = None, password: str = None) -> bool:
        """
        进行认证

        Args:
            username: 用户名（可选）
            password: 密码（可选）

        Returns:
            bool: 认证是否成功

        Example:
            >>> # 使用API密钥认证
            >>> client.authenticate()
            >>>
            >>> # 使用用户名密码认证
            >>> client.authenticate("username", "password")
        """
        try:
            success = self.auth.authenticate_with_api_key(username, password)
            if success:
                # 更新session认证头
                headers = self.auth.get_auth_headers()
                self.session.headers.update(headers)
            return success
        except Exception as e:
            raise FootballPredictionError(f"认证失败: {str(e)}")

    @property
    def is_authenticated(self) -> bool:
        """检查是否已认证"""
        return self.auth.is_authenticated

    def get(self, endpoint: str, params: dict[str, Any] = None) -> dict[str, Any]:
        """
        通用GET请求

        Args:
            endpoint: API端点
            params: 查询参数

        Returns:
            Dict[str, Any]: 响应数据
        """
        return self._make_request("GET", endpoint, params=params)

    def post(self, endpoint: str, data: dict[str, Any] = None) -> dict[str, Any]:
        """
        通用POST请求

        Args:
            endpoint: API端点
            data: 请求数据

        Returns:
            Dict[str, Any]: 响应数据
        """
        return self._make_request("POST", endpoint, json=data)

    def put(self, endpoint: str, data: dict[str, Any] = None) -> dict[str, Any]:
        """
        通用PUT请求

        Args:
            endpoint: API端点
            data: 请求数据

        Returns:
            Dict[str, Any]: 响应数据
        """
        return self._make_request("PUT", endpoint, json=data)

    def delete(self, endpoint: str) -> dict[str, Any]:
        """
        通用DELETE请求

        Args:
            endpoint: API端点

        Returns:
            Dict[str, Any]: 响应数据
        """
        return self._make_request("DELETE", endpoint)

    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] = None,
        json: dict[str, Any] = None,
        **kwargs
    ) -> dict[str, Any]:
        """
        发起HTTP请求

        Args:
            method: HTTP方法
            endpoint: API端点
            params: 查询参数
            json: JSON数据
            **kwargs: 其他请求参数

        Returns:
            Dict[str, Any]: 响应数据
        """
        if not self.is_authenticated:
            raise FootballPredictionError("未认证，请先调用authenticate()")

        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        try:
            response = self.session.request(
                method,
                url,
                params=params,
                json=json,
                timeout=self.timeout,
                **kwargs
            )

            # 检查限流错误
            if response.status_code == 429:
                rate_limit_error = rate_limit_handler(response)
                if rate_limit_error and self.auto_retry:
                    # 自动等待重试
                    retry_after = rate_limit_error.get_retry_after_seconds()
                    if retry_after and retry_after > 0:
                        import time
                        time.sleep(retry_after)
                        return self._make_request(method, endpoint, params, json, **kwargs)

                raise rate_limit_error

            # 处理其他错误
            if response.status_code >= 400:
                error_data = parse_api_error(response)
                raise create_exception_from_response(error_data, response)

            # 成功响应
            try:
                return response.json()
            except json.JSONDecodeError:
                return {"success": True, "data": response.text}

        except requests.exceptions.RequestException as e:
            if not isinstance(e, FootballPredictionError):
                raise FootballPredictionError(f"请求失败: {str(e)}")
            raise

    def health_check(self) -> dict[str, Any]:
        """
        健康检查

        Returns:
            Dict[str, Any]: 健康状态信息

        Example:
            >>> health = client.health_check()
            >>> print(f"API状态: {health['status']}")
        """
        try:
            url = f"{self.base_url}/health"
            response = self.session.get(url, timeout=10)

            if response.status_code == 200:
                return response.json()
            else:
                return {"status": "unhealthy", "error": f"HTTP {response.status_code}"}

        except requests.exceptions.RequestException:
            return {"status": "unhealthy", "error": "连接失败"}

    def get_api_info(self) -> dict[str, Any]:
        """
        获取API信息

        Returns:
            Dict[str, Any]: API信息

        Example:
            >>> info = client.get_api_info()
            >>> print(f"API版本: {info['api_version']}")
        """
        try:
            url = f"{self.base_url}/api/info"
            response = self.session.get(url, timeout=10)

            if response.status_code == 200:
                return response.json().get("data", {})
            else:
                return {}

        except requests.exceptions.RequestException:
            return {}

    def __enter__(self):
        """上下文管理器入口"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.auth.clear_tokens()
        self.session.close()

    def __repr__(self) -> str:
        """字符串表示"""
        status = "已认证" if self.is_authenticated else "未认证"
        return f"<FootballPredictionClient base_url={self.base_url} status={status}>"
