"""
Model Loader
异步模型加载器

提供高性能的异步模型加载、缓存和版本管理功能。
支持模型回滚、并发加载和内存管理。
"""

import asyncio
import json
import os
import pickle
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional, Union
from concurrent.futures import ThreadPoolExecutor
import hashlib

try:
    import joblib

    HAVE_JOBLIB = True
except ImportError:
    HAVE_JOBLIB = False
    joblib = None

try:
    from cachetools import LRUCache

    HAVE_CACHETOOLS = True
except ImportError:
    HAVE_CACHETOOLS = False
    LRUCache = dict

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler

    HAVE_WATCHDOG = True
except ImportError:
    HAVE_WATCHDOG = False
    Observer = None
    FileSystemEventHandler = object

from .errors import ModelLoadError, ErrorCode
from .schemas import ModelInfo, ModelType


class ModelLoadLock:
    """模型加载锁"""

    def __init__(self):
        self._locks: dict[str, asyncio.Lock] = {}
        self._global_lock = asyncio.Lock()

    async def get_lock(self, model_name: str) -> asyncio.Lock:
        """获取模型的加载锁"""
        async with self._global_lock:
            if model_name not in self._locks:
                self._locks[model_name] = asyncio.Lock()
            return self._locks[model_name]


class ModelMetadata:
    """模型元数据"""

    def __init__(self, model_info: ModelInfo, file_path: str):
        self.model_info = model_info
        self.file_path = file_path
        self.file_hash = self._calculate_file_hash(file_path)
        self.last_modified = datetime.fromtimestamp(os.path.getmtime(file_path))

    def _calculate_file_hash(self, file_path: str) -> str:
        """计算文件哈希"""
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()

    def is_modified(self) -> bool:
        """检查文件是否被修改"""
        if not os.path.exists(self.file_path):
            return True

        current_mtime = datetime.fromtimestamp(os.path.getmtime(self.file_path))
        current_hash = self._calculate_file_hash(self.file_path)

        return current_mtime != self.last_modified or current_hash != self.file_hash

    def update_metadata(self):
        """更新元数据"""
        if os.path.exists(self.file_path):
            self.last_modified = datetime.fromtimestamp(
                os.path.getmtime(self.file_path)
            )
            self.file_hash = self._calculate_file_hash(self.file_path)


class LoadedModel:
    """已加载的模型实例"""

    def __init__(self, model: Any, metadata: ModelMetadata):
        self.model = model
        self.metadata = metadata
        self.load_time = datetime.utcnow()
        self.access_count = 0
        self.last_access = datetime.utcnow()

    def access(self) -> Any:
        """访问模型"""
        self.access_count += 1
        self.last_access = datetime.utcnow()
        return self.model


class ModelLoader:
    """异步模型加载器"""

    def __init__(self, registry_path: str = "models/", max_loaded_models: int = 10):
        self.registry_path = Path(registry_path)
        self.max_loaded_models = max_loaded_models

        # 模型存储
        self._loaded_models: LRUCache[str, LoadedModel] = (
            LRUCache(maxsize=max_loaded_models) if HAVE_CACHETOOLS else {}
        )
        self._model_metadata: dict[str, ModelMetadata] = {}

        # 线程池和锁
        self._executor = ThreadPoolExecutor(
            max_workers=4, thread_name_prefix="model_loader"
        )
        self._load_locks = ModelLoadLock()

        # 版本管理
        self._default_models: dict[str, str] = {}  # model_type -> default_model_name
        self._model_versions: dict[str, list[str]] = {}  # model_name -> [versions]

        # 监控
        self._load_stats = {
            "total_loads": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "load_errors": 0,
        }

    async def initialize(self):
        """初始化模型加载器"""
        try:
            await self._scan_models()
            await self._load_default_models()
            print(f"ModelLoader initialized: {len(self._model_metadata)} models found")
        except Exception as e:
            raise ModelLoadError(f"Failed to initialize ModelLoader: {str(e)}")

    async def load(self, model_name: str, version: Optional[str] = None) -> LoadedModel:
        """
        异步加载模型

        Args:
            model_name: 模型名称
            version: 指定版本（可选）

        Returns:
            LoadedModel: 已加载的模型实例

        Raises:
            ModelLoadError: 模型加载失败
        """
        load_lock = await self._load_locks.get_lock(model_name)

        async with load_lock:
            return await self._load_model_internal(model_name, version)

    async def get(self, model_name: str) -> LoadedModel:
        """获取已加载的模型"""
        if model_name in self._loaded_models:
            self._load_stats["cache_hits"] += 1
            return self._loaded_models[model_name]

        # 模型未加载，尝试加载
        try:
            model = await self.load(model_name)
            self._load_stats["cache_misses"] += 1
            return model
        except Exception as e:
            self._load_stats["load_errors"] += 1
            raise ModelLoadError(f"Failed to load model '{model_name}': {str(e)}")

    async def get_model_info(self, model_name: str) -> Optional[ModelInfo]:
        """获取模型信息"""
        if model_name in self._model_metadata:
            return self._model_metadata[model_name].model_info
        return None

    async def list_models(
        self, model_type: Optional[ModelType] = None
    ) -> list[ModelInfo]:
        """列出所有可用模型"""
        models = [metadata.model_info for metadata in self._model_metadata.values()]

        if model_type:
            models = [m for m in models if m.model_type == model_type]

        return sorted(models, key=lambda x: (x.model_name, x.created_at))

    async def set_default_model(self, model_type: ModelType, model_name: str):
        """设置默认模型"""
        if model_name not in self._model_metadata:
            raise ModelLoadError(f"Model '{model_name}' not found")

        self._default_models[model_type.value] = model_name

    async def get_default_model(self, model_type: ModelType) -> Optional[str]:
        """获取默认模型"""
        return self._default_models.get(model_type.value)

    async def unload_model(self, model_name: str):
        """卸载模型"""
        if model_name in self._loaded_models:
            del self._loaded_models[model_name]

    async def reload_model(self, model_name: str) -> LoadedModel:
        """重新加载模型"""
        load_lock = await self._load_locks.get_lock(model_name)

        async with load_lock:
            # 卸载现有模型
            if model_name in self._loaded_models:
                del self._loaded_models[model_name]

            # 重新加载
            return await self._load_model_internal(model_name, None, force_reload=True)

    def get_load_stats(self) -> dict[str, Any]:
        """获取加载统计信息"""
        total_requests = (
            self._load_stats["cache_hits"] + self._load_stats["cache_misses"]
        )
        cache_hit_rate = (
            self._load_stats["cache_hits"] / total_requests * 100
            if total_requests > 0
            else 0
        )

        return {
            **self._load_stats,
            "cache_hit_rate": round(cache_hit_rate, 2),
            "loaded_models": len(self._loaded_models),
            "total_models": len(self._model_metadata),
        }

    async def _scan_models(self):
        """扫描模型目录"""
        if not self.registry_path.exists():
            self.registry_path.mkdir(parents=True, exist_ok=True)
            return

        # 扫描所有模型文件
        for model_file in self.registry_path.rglob("*.pkl"):
            await self._register_model_file(model_file)

        # 扫描JSON元数据文件
        for json_file in self.registry_path.rglob("*.json"):
            await self._load_model_metadata(json_file)

    async def _register_model_file(self, model_file: Path):
        """注册模型文件"""
        try:
            # 尝试从文件名解析模型信息
            model_name = model_file.stem
            model_type = self._detect_model_type(model_file)

            # 创建模型信息
            model_info = ModelInfo(
                model_name=model_name,
                model_version="1.0.0",  # 默认版本
                model_type=model_type,
                created_at=datetime.fromtimestamp(model_file.stat().st_ctime),
                file_size=model_file.stat().st_size,
            )

            # 创建元数据
            metadata = ModelMetadata(model_info, str(model_file))
            self._model_metadata[model_name] = metadata

        except Exception as e:
            print(f"Warning: Failed to register model file {model_file}: {e}")

    async def _load_model_metadata(self, json_file: Path):
        """加载模型元数据"""
        try:
            with open(json_file) as f:
                data = json.load(f)

            model_info = ModelInfo(**data)
            model_file = json_file.with_suffix(".pkl")

            if model_file.exists():
                metadata = ModelMetadata(model_info, str(model_file))
                self._model_metadata[model_info.model_name] = metadata

        except Exception as e:
            print(f"Warning: Failed to load metadata from {json_file}: {e}")

    async def _load_default_models(self):
        """加载默认模型"""
        # 为每种模型类型设置默认模型
        for model_type in ModelType:
            models_of_type = await self.list_models(model_type)
            if models_of_type:
                await self.set_default_model(model_type, models_of_type[0].model_name)

    async def _load_model_internal(
        self, model_name: str, version: Optional[str] = None, force_reload: bool = False
    ) -> LoadedModel:
        """内部模型加载方法"""

        # 检查是否已加载
        if not force_reload and model_name in self._loaded_models:
            loaded_model = self._loaded_models[model_name]

            # 检查文件是否被修改
            if not loaded_model.metadata.is_modified():
                return loaded_model

        # 获取模型元数据
        if model_name not in self._model_metadata:
            raise ModelLoadError(
                f"Model '{model_name}' not found",
                model_name=model_name,
                details={"available_models": list(self._model_metadata.keys())},
            )

        metadata = self._model_metadata[model_name]

        # 检查文件是否存在
        if not os.path.exists(metadata.file_path):
            raise ModelLoadError(
                f"Model file not found: {metadata.file_path}",
                model_name=model_name,
                details={"file_path": metadata.file_path},
            )

        try:
            # 在线程池中加载模型
            model = await asyncio.get_event_loop().run_in_executor(
                self._executor, self._load_model_sync, metadata.file_path
            )

            # 创建加载的模型实例
            loaded_model = LoadedModel(model, metadata)

            # 缓存模型
            self._loaded_models[model_name] = loaded_model
            self._load_stats["total_loads"] += 1

            # 更新元数据
            metadata.update_metadata()

            print(f"Successfully loaded model '{model_name}' from {metadata.file_path}")
            return loaded_model

        except Exception as e:
            self._load_stats["load_errors"] += 1
            raise ModelLoadError(
                f"Failed to load model '{model_name}': {str(e)}",
                model_name=model_name,
                details={
                    "file_path": metadata.file_path,
                    "error_type": type(e).__name__,
                },
            )

    def _load_model_sync(self, file_path: str) -> Any:
        """同步加载模型"""
        try:
            # 尝试使用joblib加载
            if file_path.endswith(".pkl"):
                return joblib.load(file_path)
            else:
                # 尝试使用pickle加载
                with open(file_path, "rb") as f:
                    return pickle.load(f)
        except Exception as e:
            raise RuntimeError(f"Failed to load model from {file_path}: {str(e)}")

    def _detect_model_type(self, model_file: Path) -> ModelType:
        """检测模型类型"""
        file_name = model_file.name.lower()

        if "xgboost" in file_name or "xgb" in file_name:
            return ModelType.XGBOOST
        elif "lstm" in file_name or "rnn" in file_name:
            return ModelType.LSTM
        elif "ensemble" in file_name:
            return ModelType.ENSEMBLE
        elif "mock" in file_name:
            return ModelType.MOCK
        else:
            return ModelType.XGBOOST  # 默认类型

    async def cleanup(self):
        """清理资源"""
        # 关闭线程池
        self._executor.shutdown(wait=True)

        # 清理模型缓存
        self._loaded_models.clear()

        print("ModelLoader cleanup completed")


# 全局实例
_model_loader: Optional[ModelLoader] = None


async def get_model_loader() -> ModelLoader:
    """获取全局模型加载器实例"""
    global _model_loader

    if _model_loader is None:
        _model_loader = ModelLoader()
        await _model_loader.initialize()

    return _model_loader


def get_model_loader_sync() -> ModelLoader:
    """同步获取模型加载器（用于非异步上下文）"""
    global _model_loader

    if _model_loader is None:
        raise RuntimeError(
            "ModelLoader not initialized. Call get_model_loader() first."
        )

    return _model_loader
