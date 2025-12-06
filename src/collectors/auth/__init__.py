"""
认证模块
Authentication Module

该模块提供动态认证功能，包括令牌管理、缓存和自动刷新。

主要组件:
- TokenManager: 令牌管理器
- AuthProvider: 认证提供者协议
- FotMobAuthProvider: FotMob 认证实现
"""

from .token_manager import (
    Token,
    TokenType,
    AuthProvider,
    TokenManager,
    FotMobAuthProvider,
    MockAuthProvider,
    AuthenticationError,
    TokenExpiredError,
    TokenRefreshError,
    get_token_manager,
    close_token_manager,
    create_token_manager,
    create_fotmob_provider,
    create_mock_provider,
)

__all__ = [
    'Token',
    'TokenType',
    'AuthProvider',
    'TokenManager',
    'FotMobAuthProvider',
    'MockAuthProvider',
    'AuthenticationError',
    'TokenExpiredError',
    'TokenRefreshError',
    'get_token_manager',
    'close_token_manager',
    'create_token_manager',
    'create_fotmob_provider',
    'create_mock_provider',
]