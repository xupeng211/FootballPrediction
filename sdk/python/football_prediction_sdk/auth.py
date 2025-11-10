#!/usr/bin/env python3
"""
认证管理模块
Football Prediction SDK - 认证和授权管理

Author: Claude Code
Version: 1.0.0
"""

import time
import json
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

import requests

from .exceptions import AuthenticationError, SystemError


class AuthManager:
    """认证管理器"""

    def __init__(
        self,
        api_key: str,
        base_url: str,
        timeout: int = 30,
        auto_refresh: bool = True
    ):
        """
        初始化认证管理器

        Args:
            api_key: API密钥
            base_url: API基础URL
            timeout: 请求超时时间
            auto_refresh: 是否自动刷新token
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.auto_refresh = auto_refresh

        # Token缓存
        self._access_token: Optional[str] = None
        self._refresh_token: Optional[str] = None
        self._token_expires_at: Optional[datetime] = None
        self._refresh_token_expires_at: Optional[datetime] = None

        # 会话管理
        self._session = requests.Session()
        self._session.headers.update({
            "Content-Type": "application/json",
            "User-Agent": "football-prediction-sdk/1.0.0"
        })

    @property
    def is_authenticated(self) -> bool:
        """检查是否已认证"""
        if not self._access_token or not self._token_expires_at:
            return False

        # 检查token是否过期（提前5分钟刷新）
        now = datetime.now()
        expiry_buffer = timedelta(minutes=5)
        return now < (self._token_expires_at - expiry_buffer)

    @property
    def access_token(self) -> Optional[str]:
        """获取访问token"""
        if self.auto_refresh and not self.is_authenticated:
            self.refresh_token_if_needed()
        return self._access_token

    def get_auth_headers(self) -> Dict[str, str]:
        """
        获取认证头

        Returns:
            Dict[str, str]: 包含认证信息的请求头

        Raises:
            AuthenticationError: 认证失败时抛出
        """
        token = self.access_token
        if not token:
            raise AuthenticationError("未找到有效的访问令牌")

        return {"Authorization": f"Bearer {token}"}

    def authenticate_with_api_key(self, username: Optional[str] = None, password: Optional[str] = None) -> bool:
        """
        使用API密钥进行认证

        Args:
            username: 用户名（可选）
            password: 密码（可选）

        Returns:
            bool: 认证是否成功

        Raises:
            AuthenticationError: 认证失败时抛出
        """
        try:
            # 如果提供了用户名和密码，使用密码认证
            if username and password:
                return self._authenticate_with_password(username, password)
            else:
                # 使用API密钥认证
                return self._authenticate_with_api_key()

        except requests.exceptions.RequestException as e:
            raise AuthenticationError(f"认证请求失败: {str(e)}")

    def _authenticate_with_api_key(self) -> bool:
        """使用API密钥认证"""
        auth_url = f"{self.base_url}/auth/api-key"

        try:
            response = self._session.post(
                auth_url,
                json={"api_key": self.api_key},
                timeout=self.timeout
            )

            if response.status_code == 200:
                auth_data = response.json()
                self._process_auth_response(auth_data)
                return True
            else:
                self._handle_auth_error(response)
                return False

        except requests.exceptions.RequestException as e:
            raise AuthenticationError(f"API密钥认证失败: {str(e)}")

    def _authenticate_with_password(self, username: str, password: str) -> bool:
        """使用用户名密码认证"""
        auth_url = f"{self.base_url}/auth/token"

        try:
            response = self._session.post(
                auth_url,
                json={"username": username, "password": password},
                timeout=self.timeout
            )

            if response.status_code == 200:
                auth_data = response.json()
                self._process_auth_response(auth_data)
                return True
            else:
                self._handle_auth_error(response)
                return False

        except requests.exceptions.RequestException as e:
            raise AuthenticationError(f"密码认证失败: {str(e)}")

    def _process_auth_response(self, auth_data: Dict[str, Any]) -> None:
        """处理认证响应"""
        if not auth_data.get("success"):
            raise AuthenticationError("认证响应失败")

        data = auth_data.get("data", {})

        self._access_token = data.get("access_token")
        self._refresh_token = data.get("refresh_token")

        # 处理token过期时间
        expires_in = data.get("expires_in", 3600)  # 默认1小时
        refresh_expires_in = data.get("refresh_expires_in", 86400)  # 默认24小时

        now = datetime.now()
        self._token_expires_at = now + timedelta(seconds=expires_in)
        self._refresh_token_expires_at = now + timedelta(seconds=refresh_expires_in)

        # 更新session头
        if self._access_token:
            self._session.headers.update({
                "Authorization": f"Bearer {self._access_token}"
            })

    def _handle_auth_error(self, response: requests.Response) -> None:
        """处理认证错误响应"""
        try:
            error_data = response.json()
            error_info = error_data.get("error", {})
            error_code = error_info.get("code", "UNKNOWN")
            message = error_info.get("message", "认证失败")

            if error_code == "AUTH_004":
                raise AuthenticationError("用户名或密码错误")
            elif error_code == "AUTH_005":
                raise AuthenticationError("账户已被禁用")
            else:
                raise AuthenticationError(f"认证失败: {message}")

        except (json.JSONDecodeError, KeyError):
            raise AuthenticationError(f"认证失败: HTTP {response.status_code}")

    def refresh_token_if_needed(self) -> bool:
        """如果需要，刷新访问token"""
        if not self._refresh_token or not self._refresh_token_expires_at:
            return False

        # 检查refresh token是否过期
        if datetime.now() >= self._refresh_token_expires_at:
            return False

        # 检查access token是否需要刷新
        if self.is_authenticated:
            return True  # 不需要刷新

        try:
            return self._refresh_access_token()

        except Exception as e:
            # 刷新失败，清除token
            self.clear_tokens()
            raise AuthenticationError(f"Token刷新失败: {str(e)}")

    def _refresh_access_token(self) -> bool:
        """刷新访问token"""
        refresh_url = f"{self.base_url}/auth/refresh"

        try:
            response = self._session.post(
                refresh_url,
                json={"refresh_token": self._refresh_token},
                timeout=self.timeout
            )

            if response.status_code == 200:
                auth_data = response.json()
                self._process_auth_response(auth_data)
                return True
            else:
                # 刷新失败，清除token
                self.clear_tokens()
                return False

        except requests.exceptions.RequestException as e:
            self.clear_tokens()
            raise AuthenticationError(f"Token刷新请求失败: {str(e)}")

    def clear_tokens(self) -> None:
        """清除所有token"""
        self._access_token = None
        self._refresh_token = None
        self._token_expires_at = None
        self._refresh_token_expires_at = None

        # 清除session头
        if "Authorization" in self._session.headers:
            del self._session.headers["Authorization"]

    def logout(self) -> bool:
        """登出"""
        if not self.is_authenticated:
            return True

        logout_url = f"{self.base_url}/auth/logout"

        try:
            response = self._session.post(logout_url, timeout=self.timeout)
            success = response.status_code == 200

        except requests.exceptions.RequestException:
            success = False

        # 无论请求是否成功，都清除本地token
        self.clear_tokens()
        return success

    def validate_token(self) -> bool:
        """验证当前token是否有效"""
        if not self._access_token:
            return False

        validate_url = f"{self.base_url}/auth/validate"

        try:
            response = self._session.get(validate_url, timeout=self.timeout)
            return response.status_code == 200

        except requests.exceptions.RequestException:
            return False

    def get_user_info(self) -> Optional[Dict[str, Any]]:
        """获取当前用户信息"""
        if not self.is_authenticated:
            raise AuthenticationError("未认证")

        user_url = f"{self.base_url}/auth/me"

        try:
            response = self._session.get(user_url, timeout=self.timeout)

            if response.status_code == 200:
                return response.json().get("data")
            else:
                return None

        except requests.exceptions.RequestException as e:
            raise SystemError(f"获取用户信息失败: {str(e)}")

    def change_password(self, current_password: str, new_password: str) -> bool:
        """修改密码"""
        if not self.is_authenticated:
            raise AuthenticationError("未认证")

        change_url = f"{self.base_url}/auth/change-password"

        try:
            response = self._session.post(
                change_url,
                json={
                    "current_password": current_password,
                    "new_password": new_password
                },
                timeout=self.timeout
            )

            return response.status_code == 200

        except requests.exceptions.RequestException as e:
            raise SystemError(f"修改密码失败: {str(e)}")

    def generate_api_key(self, name: str, description: str = None) -> Optional[str]:
        """生成新的API密钥"""
        if not self.is_authenticated:
            raise AuthenticationError("未认证")

        generate_url = f"{self.base_url}/auth/api-keys"

        try:
            response = self._session.post(
                generate_url,
                json={
                    "name": name,
                    "description": description or ""
                },
                timeout=self.timeout
            )

            if response.status_code == 200:
                data = response.json().get("data", {})
                return data.get("api_key")
            else:
                return None

        except requests.exceptions.RequestException as e:
            raise SystemError(f"生成API密钥失败: {str(e)}")

    def revoke_api_key(self, api_key_id: str) -> bool:
        """撤销API密钥"""
        if not self.is_authenticated:
            raise AuthenticationError("未认证")

        revoke_url = f"{self.base_url}/auth/api-keys/{api_key_id}/revoke"

        try:
            response = self._session.post(revoke_url, timeout=self.timeout)
            return response.status_code == 200

        except requests.exceptions.RequestException as e:
            raise SystemError(f"撤销API密钥失败: {str(e)}")

    def list_api_keys(self) -> list:
        """列出所有API密钥"""
        if not self.is_authenticated:
            raise AuthenticationError("未认证")

        list_url = f"{self.base_url}/auth/api-keys"

        try:
            response = self._session.get(list_url, timeout=self.timeout)

            if response.status_code == 200:
                return response.json().get("data", [])
            else:
                return []

        except requests.exceptions.RequestException as e:
            raise SystemError(f"获取API密钥列表失败: {str(e)}")

    def __enter__(self):
        """上下文管理器入口"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        if self.auto_refresh:
            self.clear_tokens()

    def __repr__(self) -> str:
        """字符串表示"""
        status = "已认证" if self.is_authenticated else "未认证"
        return f"<AuthManager status={status} expires_at={self._token_expires_at}>"