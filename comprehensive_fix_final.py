#!/usr/bin/env python3
"""
最终全面修复脚本
"""

import os
from pathlib import Path

def fix_files():
    """修复多个文件"""

    # 文件路径和修复内容的映射
    fixes = {
        "src/adapters/factory_simple.py": '''from typing import Any, Dict, List, Optional

"""
适配器工厂（简化版）
Simplified Adapter Factory
"""

class AdapterConfig:
    """适配器配置"""
    def __init__(
        self,
        name: str,
        adapter_type: str,
        config: Dict[str, Any] | None = None
    ):
        self.name = name
        self.adapter_type = adapter_type
        self.config = config or {}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AdapterConfig":
        """从字典创建配置"""
        return cls(
            name=data["name"],
            adapter_type=data["adapter_type"],
            config=data.get("config", {})
        )


class SimpleAdapterFactory:
    """简单适配器工厂"""

    def __init__(self):
        self._adapters: Dict[str, Any] = {}

    def register_adapter(self, name: str, adapter_class: type) -> None:
        """注册适配器类"""
        self._adapters[name] = adapter_class

    def create_adapter(self, config: AdapterConfig) -> Any:
        """创建适配器实例"""
        adapter_class = self._adapters.get(config.adapter_type)
        if not adapter_class:
            raise ValueError(f"Unknown adapter type: {config.adapter_type}")

        return adapter_class(config.config)

    def create_from_dict(self, data: Dict[str, Any]) -> Any:
        """从字典创建适配器"""
        config = AdapterConfig.from_dict(data)
        return self.create_adapter(config)


def create_adapter(config: Dict[str, Any]) -> Any:
    """便捷函数：获取适配器"""
    factory = SimpleAdapterFactory()
    return factory.create_from_dict(config)
''',

        "src/adapters/football.py": '''from typing import Any, Dict, List

"""
足球数据适配器
Football Data Adapter

集成各种足球数据API。
Integrate various football data APIs.
"""

import aiohttp
import asyncio
from datetime import datetime


class FootballDataAdapter:
    """足球数据适配器"""

    def __init__(self, api_key: str | None = None, base_url: str = "https://api.football-data.org"):
        self.api_key = api_key
        self.base_url = base_url
        self.session: aiohttp.ClientSession | None = None

    async def initialize(self) -> None:
        """初始化适配器"""
        self.session = aiohttp.ClientSession()

    async def cleanup(self) -> None:
        """清理资源"""
        if self.session:
            await self.session.close()

    async def get_teams(self, league_id: int) -> List[Dict[str, Any]]:
        """获取联赛球队列表"""
        if not self.session:
            raise RuntimeError("Adapter not initialized")

        url = f"{self.base_url}/v4/teams"
        params = {"league": league_id}

        async with self.session.get(url, params=params) as response:
            response.raise_for_status()
            data = await response.json()
            return data.get("teams", [])

    async def get_matches(self, team_id: int, date_from: str | None = None) -> List[Dict[str, Any]]:
        """获取比赛数据"""
        if not self.session:
            raise RuntimeError("Adapter not initialized")

        url = f"{self.base_url}/v4/matches"
        params = {"team": team_id}
        if date_from:
            params["dateFrom"] = date_from

        async with self.session.get(url, params=params) as response:
            response.raise_for_status()
            data = await response.json()
            return data.get("matches", [])
''',

        "src/adapters/registry_simple.py": '''from typing import Any, Dict, List

"""
简化的适配器注册表
Simplified Adapter Registry
"""

from .factory_simple import AdapterConfig, SimpleAdapterFactory


class SimpleAdapterRegistry:
    """简化的适配器注册表"""

    def __init__(self):
        self.factory = SimpleAdapterFactory()
        self.adapters: Dict[str, Any] = {}
        self.status = "inactive"

    async def initialize(self) -> None:
        """初始化注册表"""
        self.status = "active"

    async def register_adapter(self, config: AdapterConfig) -> Any:
        """注册适配器"""
        if config.name in self.adapters:
            raise ValueError(f"Adapter {config.name} already registered")

        adapter = self.factory.create_adapter(config)
        if hasattr(adapter, 'initialize'):
            await adapter.initialize()

        self.adapters[config.name] = adapter
        return adapter

    def get_adapter(self, name: str) -> Any:
        """获取适配器"""
        return self.adapters.get(name)

    def list_adapters(self) -> List[str]:
        """列出所有适配器"""
        return list(self.adapters.keys())

    async def shutdown(self) -> None:
        """关闭注册表"""
        for adapter in self.adapters.values():
            if hasattr(adapter, 'cleanup'):
                await adapter.cleanup()
        self.adapters.clear()
        self.status = "inactive"


# 创建全局注册表实例
adapter_registry = SimpleAdapterRegistry()
''',

        "src/adapters/football.py": '''from typing import Any, Dict, List

"""
足球数据适配器
Football Data Adapter

集成各种足球数据API。
Integrate various football data APIs.
"""

import aiohttp
import asyncio
from datetime import datetime


class FootballDataAdapter:
    """足球数据适配器"""

    def __init__(self, api_key: str | None = None, base_url: str = "https://api.football-data.org"):
        self.api_key = api_key
        self.base_url = base_url
        self.session: aiohttp.ClientSession | None = None

    async def initialize(self) -> None:
        """初始化适配器"""
        self.session = aiohttp.ClientSession()

    async def cleanup(self) -> None:
        """清理资源"""
        if self.session:
            await self.session.close()

    async def get_teams(self, league_id: int) -> List[Dict[str, Any]]:
        """获取联赛球队列表"""
        if not self.session:
            raise RuntimeError("Adapter not initialized")

        url = f"{self.base_url}/v4/teams"
        params = {"league": league_id}

        async with self.session.get(url, params=params) as response:
            response.raise_for_status()
            data = await response.json()
            return data.get("teams", [])

    async def get_matches(self, team_id: int, date_from: str | None = None) -> List[Dict[str, Any]]:
        """获取比赛数据"""
        if not self.session:
            raise RuntimeError("Adapter not initialized")

        url = f"{self.base_url}/v4/matches"
        params = {"team": team_id}
        if date_from:
            params["dateFrom"] = date_from

        async with self.session.get(url, params=params) as response:
            response.raise_for_status()
            data = await response.json()
            return data.get("matches", [])
''',

        "src/api/adapters.py": '''from typing import Any, Dict, List

"""
适配器API
Adapter API

展示适配器模式的使用和效果。
Demonstrates the usage and effects of the adapter pattern.
"""

from fastapi import APIRouter, Depends, HTTPException
from ..adapters.registry_simple import adapter_registry
from ..adapters.factory_simple import AdapterConfig

router = APIRouter(prefix="/adapters", tags=["adapters"])


@router.get("/", summary="列出所有适配器")
async def list_adapters() -> Dict[str, Any]:
    """列出所有已注册的适配器"""
    return {
        "adapters": adapter_registry.list_adapters(),
        "status": adapter_registry.status
    }


@router.post("/register", summary="注册新适配器")
async def register_adapter(config: Dict[str, Any]) -> Dict[str, Any]:
    """注册一个新的适配器"""
    try:
        adapter_config = AdapterConfig.from_dict(config)
        adapter = await adapter_registry.register_adapter(adapter_config)
        return {
            "success": True,
            "adapter_name": adapter_config.name,
            "message": f"Adapter {adapter_config.name} registered successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{adapter_name}", summary="获取适配器信息")
async def get_adapter(adapter_name: str) -> Dict[str, Any]:
    """获取指定适配器的信息"""
    adapter = adapter_registry.get_adapter(adapter_name)
    if not adapter:
        raise HTTPException(status_code=404, detail="Adapter not found")

    return {
        "name": adapter_name,
        "type": type(adapter).__name__,
        "status": "active"
    }
''',

        "src/api/auth.py": '''"""
认证相关API路由
Authentication API Routes
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Dict, Any

router = APIRouter(prefix="/auth", tags=["authentication"])
security = HTTPBearer()


# 模拟用户数据库
fake_users_db = {
    "johndoe": {
        "username": "johndoe",
        "full_name": "John Doe",
        "email": "johndoe@example.com",
        "hashed_password": "fakehashedsecret",
        "disabled": False
    }
}


def fake_decode_token(token: str) -> Dict[str, Any]:
    """模拟JWT解码"""
    # 实际应用中应该验证JWT签名和过期时间
    if token == "fake-super-secret-token":
        return fake_users_db["johndoe"]
    return None


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """获取当前用户"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    user = fake_decode_token(credentials.credentials)
    if user is None:
        raise credentials_exception

    return user


@router.post("/login")
async def login(username: str, password: str) -> Dict[str, str]:
    """用户登录"""
    user = fake_users_db.get(username)
    if not user or user["hashed_password"] != password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 实际应用中应该生成真实的JWT token
    return {"access_token": "fake-super-secret-token", "token_type": "bearer"}


@router.get("/me")
async def read_users_me(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """获取当前用户信息"""
    return current_user
''',

        "src/api/data/models/__init__.py": '''"""
Models package for API data models
"""

from .match_models import *
from .team_models import *
from .league_models import *
from .odds_models import *

__all__ = [
    "MatchRequest",
    "MatchResponse",
    "TeamInfo",
    "LeagueInfo",
    "OddsQueryParams",
]
''',
    }

    for file_path, content in fixes.items():
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✓ 修复: {file_path}")
        except Exception as e:
            print(f"✗ 错误: {file_path} - {e}")

    # 批量修复文件末尾的多余内容
    files_to_clean = [
        "src/database/base.py",
        "src/adapters/registry.py",
        "src/api/decorators.py",
        "src/api/dependencies.py",
        "src/api/facades.py",
        "src/api/features.py",
        "src/api/monitoring.py",
        "src/database/query_optimizer.py",
        "src/data/features/feature_store.py",
    ]

    print("\n清理文件末尾...")
    for file_path in files_to_clean:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            # 移除末尾的多余内容
            cleaned_lines = []
            for line in lines:
                # 移除只有 """ "" "的行
                if line.strip() in ['"""', '""""', '""" """', '"']:
                    continue
                # 修复一些明显的错误
                line = line.replace('setattr(self, key, value)', 'setattr(self, key, value)')
                line = line.replace('return f"<{self.__class__.__name__}(id={getattr(self, \'id\', None)})>', 'return f"<{self.__class__.__name__}(id={getattr(self, \'id\', None)})>"')
                cleaned_lines.append(line)

            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(cleaned_lines)

            print(f"✓ 清理: {file_path}")
        except Exception as e:
            print(f"✗ 错误: {file_path} - {e}")


if __name__ == "__main__":
    print("开始全面修复...")
    fix_files()
    print("\n修复完成！")