#!/usr/bin/env python3
"""
手动修复最关键的语法错误
"""

import os
from pathlib import Path

def fix_file(file_path: str, content: str) -> None:
    """修复文件内容"""
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

def main():
    """修复关键文件"""

    # 修复 src/utils/file_utils.py
    fix_file("src/utils/file_utils.py", '''from typing import Any

"""
足球预测系统文件处理工具模块

提供文件操作相关的工具函数。
"""
import hashlib
import json
import os
import time
from pathlib import Path


class FileUtils:
    """文件处理工具类"""

    @staticmethod
    def ensure_dir(path: str | Path) -> Path:
        """确保目录存在"""
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)
        return path

    @staticmethod
    def ensure_directory(path: str | Path) -> Path:
        """确保目录存在(ensure_dir的别名)"""
        return FileUtils.ensure_dir(path)

    @staticmethod
    def read_text(path: str | Path, encoding: str = "utf-8") -> str:
        """读取文本文件"""
        path = Path(path)
        return path.read_text(encoding=encoding)

    @staticmethod
    def write_text(path: str | Path, content: str, encoding: str = "utf-8") -> None:
        """写入文本文件"""
        path = Path(path)
        FileUtils.ensure_dir(path.parent)
        path.write_text(content, encoding=encoding)

    @staticmethod
    def read_json(path: str | Path, encoding: str = "utf-8") -> dict[str, Any]:
        """读取JSON文件"""
        content = FileUtils.read_text(path, encoding)
        return json.loads(content)

    @staticmethod
    def write_json(path: str | Path, data: dict[str, Any], encoding: str = "utf-8", indent: int = 2) -> None:
        """写入JSON文件"""
        content = json.dumps(data, ensure_ascii=False, indent=indent)
        FileUtils.write_text(path, content, encoding)

    @staticmethod
    def get_file_hash(path: str | Path, algorithm: str = "md5") -> str:
        """获取文件哈希值"""
        path = Path(path)
        hash_func = hashlib.new(algorithm)

        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_func.update(chunk)

        return hash_func.hexdigest()

    @staticmethod
    def get_file_size(path: str | Path) -> int:
        """获取文件大小(字节)"""
        path = Path(path)
        return path.stat().st_size

    @staticmethod
    def get_file_mtime(path: str | Path) -> float:
        """获取文件修改时间"""
        path = Path(path)
        return path.stat().st_mtime

    @staticmethod
    def exists(path: str | Path) -> bool:
        """检查文件或目录是否存在"""
        return Path(path).exists()

    @staticmethod
    def is_file(path: str | Path) -> bool:
        """检查是否为文件"""
        return Path(path).is_file()

    @staticmethod
    def is_dir(path: str | Path) -> bool:
        """检查是否为目录"""
        return Path(path).is_dir()

    @staticmethod
    def delete(path: str | Path) -> bool:
        """删除文件或目录"""
        path = Path(path)
        try:
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                path.rmdir()
            return True
        except OSError:
            return False

    @staticmethod
    def list_files(directory: str | Path, pattern: str = "*") -> list[Path]:
        """列出目录中的文件"""
        directory = Path(directory)
        return list(directory.glob(pattern))

    @staticmethod
    def get_temp_dir() -> Path:
        """获取临时目录"""
        return Path("/tmp")
''')

    # 修复 src/core/service_lifecycle.py
    fix_file("src/core/service_lifecycle.py", '''from typing import Any

"""
服务生命周期管理
Service Lifecycle Management

管理服务的创建、初始化、运行和销毁。
Manages service creation, initialization, running and destruction.
"""
import asyncio
import logging
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from ..core.exceptions import ServiceLifecycleError

logger = logging.getLogger(__name__)


class ServiceStatus(Enum):
    """服务状态"""
    INACTIVE = "inactive"
    STARTING = "starting"
    ACTIVE = "active"
    STOPPING = "stopping"
    ERROR = "error"


@dataclass
class ServiceInfo:
    """服务信息"""
    service: "Service"
    status: ServiceStatus = ServiceStatus.INACTIVE
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: datetime | None = None
    stopped_at: datetime | None = None
    error: str | None = None
    health_status: bool = False


class Service(ABC):
    """服务基类"""

    @abstractmethod
    async def initialize(self) -> None:
        """初始化服务"""
        pass

    @abstractmethod
    async def start(self) -> None:
        """启动服务"""
        pass

    @abstractmethod
    async def stop(self) -> None:
        """停止服务"""
        pass

    @abstractmethod
    async def cleanup(self) -> None:
        """清理资源"""
        pass

    @abstractmethod
    def health_check(self) -> bool:
        """健康检查"""
        pass


class ServiceLifecycleManager:
    """
    服务生命周期管理器
    """

    def __init__(self) -> None:
        self._services: dict[str, ServiceInfo] = {}
        self._start_order: list[str] = []
        self._stop_order: list[str] = []
        self._lock = threading.RLock()
        self._shutdown_event = asyncio.Event()
        self._monitor_task: asyncio.Task | None = None
''')

    # 修复 src/api/app.py
    fix_file("src/api/app.py", '''"""
FastAPI主应用
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from .data_router import router as data_router
from .health import router as health_router
from .predictions import router as predictions_router
from .monitoring import router as monitoring_router

# 创建FastAPI应用实例
app = FastAPI(
    title="Football Prediction API",
    description="足球预测系统API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 添加Gzip压缩中间件
app.add_middleware(GZipMiddleware, minimum_size=1000)

# 注册路由
app.include_router(data_router, prefix="/api/v1")
app.include_router(health_router, prefix="/api/v1")
app.include_router(predictions_router, prefix="/api/v1")
app.include_router(monitoring_router, prefix="/api/v1")

# 根路径
@app.get("/")
async def root():
    return {"message": "Football Prediction API", "version": "1.0.0"}
''')

    print("✓ 修复了关键文件")

if __name__ == "__main__":
    main()