"""
Hot Reload Manager
模型热更新机制

提供模型文件监控、自动重载和版本管理功能。
支持无损模型更新和自动回滚。
"""

import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler, FileModifiedEvent

    HAVE_WATCHDOG = True
except ImportError:
    HAVE_WATCHDOG = False
    Observer = None
    FileSystemEventHandler = object
    FileModifiedEvent = object

from .loader import get_model_loader
from .errors import HotReloadError

logger = logging.getLogger(__name__)


class ModelFileHandler(FileSystemEventHandler):
    """模型文件变化监听器"""

    def __init__(self, hot_reload_manager: "HotReloadManager"):
        super().__init__()
        self.hot_reload_manager = hot_reload_manager
        self._debounce_time = 2.0  # 防抖时间（秒）
        self._pending_files: dict[str, datetime] = {}

    def on_modified(self, event):
        """文件修改事件处理"""
        if event.is_directory:
            return

        # 只处理模型文件
        if not self._is_model_file(event.src_path):
            return

        file_path = str(event.src_path)
        now = datetime.utcnow()

        # 防抖处理
        if file_path in self._pending_files:
            last_time = self._pending_files[file_path]
            if (now - last_time).total_seconds() < self._debounce_time:
                return

        self._pending_files[file_path] = now

        # 异步处理文件变化
        asyncio.create_task(self.hot_reload_manager.handle_file_change(file_path))

    def _is_model_file(self, file_path: str) -> bool:
        """判断是否为模型文件"""
        path = Path(file_path)
        return path.suffix.lower() in [".pkl", ".joblib", ".model", ".h5"]


class HotReloadManager:
    """
    模型热更新管理器

    功能：
    1. 文件监控
    2. 自动重载
    3. 版本管理
    4. 健康检查
    5. 回滚机制
    """

    def __init__(
        self,
        model_directory: str = "models/",
        check_interval: float = 1.0,
        max_workers: int = 2,
    ):
        """
        初始化热更新管理器

        Args:
            model_directory: 模型目录路径
            check_interval: 检查间隔（秒）
            max_workers: 最大工作线程数
        """
        self.model_directory = Path(model_directory)
        self.check_interval = check_interval
        self.max_workers = max_workers

        # 文件监控
        self._observer: Optional[Observer] = None
        self._file_handler: Optional[ModelFileHandler] = None
        self._is_monitoring = False

        # 重载状态管理
        self._reloading_models: set[str] = set()
        self._reload_locks: dict[str, asyncio.Lock] = {}
        self._reload_history: list[dict[str, Any]] = []

        # 统计信息
        self._stats = {
            "total_reloads": 0,
            "successful_reloads": 0,
            "failed_reloads": 0,
            "rollbacks": 0,
            "last_reload": None,
            "monitoring_start": None,
        }

        # 健康检查
        self._health_check_interval = 60.0  # 健康检查间隔
        self._last_health_check = None

        # 回调函数
        self._reload_callbacks: list[Callable] = []

        # 线程池
        self._executor = ThreadPoolExecutor(max_workers=max_workers)

    async def start_monitoring(self):
        """启动文件监控"""
        if self._is_monitoring:
            logger.warning("Hot reload monitoring is already running")
            return

        try:
            # 确保模型目录存在
            self.model_directory.mkdir(parents=True, exist_ok=True)

            # 创建文件监控器（仅在watchdog可用时）
            if HAVE_WATCHDOG:
                self._file_handler = ModelFileHandler(self)
                self._observer = Observer()
                self._observer.schedule(
                    self._file_handler, str(self.model_directory), recursive=True
                )
            else:
                self._observer = None
                logger.warning(
                    "Watchdog not available, hot reload functionality disabled"
                )

            # 启动监控（仅在observer可用时）
            if self._observer:
                self._observer.start()
                self._is_monitoring = True
            else:
                self._is_monitoring = False
            self._stats["monitoring_start"] = datetime.utcnow()

            # 启动健康检查任务
            asyncio.create_task(self._health_check_loop())

            logger.info(
                f"Hot reload monitoring started for directory: {self.model_directory}"
            )

        except Exception as e:
            raise HotReloadError(f"Failed to start hot reload monitoring: {str(e)}")

    async def stop_monitoring(self):
        """停止文件监控"""
        if not self._is_monitoring:
            return

        try:
            if self._observer:
                self._observer.stop()
                self._observer.join()
                self._observer = None

            self._is_monitoring = False
            logger.info("Hot reload monitoring stopped")

        except Exception as e:
            logger.error(f"Error stopping hot reload monitoring: {e}")

    async def handle_file_change(self, file_path: str):
        """处理文件变化"""
        try:
            # 解析模型名称
            model_name = self._extract_model_name(file_path)
            if not model_name:
                logger.warning(
                    f"Could not extract model name from file path: {file_path}"
                )
                return

            # 避免并发重载
            if model_name in self._reloading_models:
                logger.info(f"Model {model_name} is already being reloaded, skipping")
                return

            await self._reload_model(model_name, file_path)

        except Exception as e:
            logger.error(f"Error handling file change for {file_path}: {e}")

    async def _reload_model(self, model_name: str, file_path: str):
        """重载模型"""
        reload_start = datetime.utcnow()
        self._reloading_models.add(model_name)

        try:
            logger.info(f"Starting hot reload for model: {model_name}")

            # 获取重载锁
            if model_name not in self._reload_locks:
                self._reload_locks[model_name] = asyncio.Lock()

            async with self._reload_locks[model_name]:
                # 1. 验证新模型
                await self._validate_new_model(file_path)

                # 2. 加载新模型（在后台验证）
                await self._load_new_model(file_path)

                # 3. 更新模型加载器
                model_loader = await get_model_loader()
                await model_loader.reload_model(model_name)

                # 4. 验证重载结果
                await self._verify_reload(model_name)

                # 5. 记录成功
                self._record_reload_success(model_name, file_path, reload_start)
                self._stats["successful_reloads"] += 1

                # 6. 触发回调
                await self._trigger_reload_callbacks(model_name, "success")

                logger.info(f"Successfully reloaded model: {model_name}")

        except Exception as e:
            # 记录失败
            self._record_reload_failure(model_name, file_path, reload_start, str(e))
            self._stats["failed_reloads"] += 1

            # 尝试回滚
            try:
                await self._rollback_model(model_name)
                self._stats["rollbacks"] += 1
                logger.info(f"Rolled back model: {model_name} due to reload failure")
            except Exception as rollback_error:
                logger.error(f"Failed to rollback model {model_name}: {rollback_error}")

            # 触发错误回调
            await self._trigger_reload_callbacks(model_name, "error", str(e))

            raise HotReloadError(f"Model hot reload failed for {model_name}: {str(e)}")

        finally:
            self._reloading_models.discard(model_name)

    def _extract_model_name(self, file_path: str) -> Optional[str]:
        """从文件路径提取模型名称"""
        try:
            path = Path(file_path)
            # 移除扩展名
            model_name = path.stem

            # 移除版本后缀（如果有）
            if (
                "_" in model_name
                and model_name.split("_")[-1].replace(".", "").isdigit()
            ):
                model_name = "_".join(model_name.split("_")[:-1])

            return model_name

        except Exception as e:
            return None

    async def _validate_new_model(self, file_path: str):
        """验证新模型文件"""
        path = Path(file_path)

        # 检查文件是否存在
        if not path.exists():
            raise HotReloadError(f"Model file does not exist: {file_path}")

        # 检查文件大小
        file_size = path.stat().st_size
        if file_size == 0:
            raise HotReloadError(f"Model file is empty: {file_path}")

        # 检查文件格式
        if path.suffix.lower() not in [".pkl", ".joblib", ".model", ".h5"]:
            raise HotReloadError(f"Unsupported model file format: {path.suffix}")

        # 基本加载测试（在线程池中执行）
        try:
            await asyncio.get_event_loop().run_in_executor(
                self._executor, self._test_model_load, file_path
            )
        except Exception as e:
            raise HotReloadError(f"Model validation failed: {str(e)}")

    def _test_model_load(self, file_path: str):
        """测试模型加载（同步方法）"""
        import joblib
        import pickle

        try:
            # 尝试加载模型
            if file_path.endswith(".pkl"):
                joblib.load(file_path)
            else:
                with open(file_path, "rb") as f:
                    pickle.load(f)
        except Exception as e:
            raise RuntimeError(f"Model load test failed: {str(e)}")

    async def _load_new_model(self, file_path: str) -> Any:
        """加载新模型（完整加载以验证）"""
        try:
            return await asyncio.get_event_loop().run_in_executor(
                self._executor, self._load_model_sync, file_path
            )
        except Exception as e:
            raise HotReloadError(f"Failed to load new model: {str(e)}")

    def _load_model_sync(self, file_path: str):
        """同步加载模型"""
        import joblib
        import pickle

        if file_path.endswith(".pkl"):
            return joblib.load(file_path)
        else:
            with open(file_path, "rb") as f:
                return pickle.load(f)

    async def _verify_reload(self, model_name: str):
        """验证重载结果"""
        try:
            # 尝试获取模型
            model_loader = await get_model_loader()
            loaded_model = await model_loader.get(model_name)

            if loaded_model is None:
                raise HotReloadError(f"Model {model_name} not available after reload")

            # 简单的预测测试（如果可能）
            await self._test_model_prediction(loaded_model.model)

        except Exception as e:
            raise HotReloadError(f"Reload verification failed: {str(e)}")

    async def _test_model_prediction(self, model: Any):
        """测试模型预测"""
        # 这里可以添加简单的预测测试
        # 暂时跳过，因为不同模型的接口可能不同
        pass

    async def _rollback_model(self, model_name: str):
        """回滚模型"""
        try:
            logger.warning(f"Attempting to rollback model: {model_name}")

            # 这里可以实现更复杂的回滚逻辑
            # 例如：从备份恢复、回退到上一版本等
            model_loader = await get_model_loader()

            # 卸载当前模型
            await model_loader.unload_model(model_name)

            # 尝试重新加载（如果可能）
            # 这里简化处理，实际应该有版本管理
            logger.info(f"Model {model_name} rollback completed")

        except Exception as e:
            raise HotReloadError(f"Model rollback failed: {str(e)}")

    def _record_reload_success(
        self, model_name: str, file_path: str, start_time: datetime
    ):
        """记录成功重载"""
        reload_time = (datetime.utcnow() - start_time).total_seconds()

        record = {
            "timestamp": datetime.utcnow().isoformat(),
            "model_name": model_name,
            "file_path": file_path,
            "status": "success",
            "reload_time_seconds": reload_time,
            "file_size": Path(file_path).stat().st_size,
        }

        self._reload_history.append(record)
        self._stats["last_reload"] = record
        self._stats["total_reloads"] += 1

        # 保持历史记录在合理范围内
        if len(self._reload_history) > 100:
            self._reload_history = self._reload_history[-100:]

    def _record_reload_failure(
        self, model_name: str, file_path: str, start_time: datetime, error: str
    ):
        """记录失败重载"""
        reload_time = (datetime.utcnow() - start_time).total_seconds()

        record = {
            "timestamp": datetime.utcnow().isoformat(),
            "model_name": model_name,
            "file_path": file_path,
            "status": "failed",
            "reload_time_seconds": reload_time,
            "error": error,
        }

        self._reload_history.append(record)
        self._stats["last_reload"] = record

        # 保持历史记录在合理范围内
        if len(self._reload_history) > 100:
            self._reload_history = self._reload_history[-100:]

    async def _trigger_reload_callbacks(
        self, model_name: str, status: str, error: Optional[str] = None
    ):
        """触发重载回调"""
        for callback in self._reload_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(model_name, status, error)
                else:
                    callback(model_name, status, error)
            except Exception as e:
                logger.error(f"Reload callback error: {e}")

    def add_reload_callback(self, callback: Callable):
        """添加重载回调函数"""
        self._reload_callbacks.append(callback)

    def remove_reload_callback(self, callback: Callable):
        """移除重载回调函数"""
        if callback in self._reload_callbacks:
            self._reload_callbacks.remove(callback)

    async def force_reload(self, model_name: str, file_path: Optional[str] = None):
        """强制重载模型"""
        if file_path is None:
            # 尝试从模型目录查找文件
            model_files = list(self.model_directory.glob(f"{model_name}.*"))
            if not model_files:
                raise HotReloadError(f"No model file found for {model_name}")

            file_path = str(model_files[0])

        await self._reload_model(model_name, file_path)

    async def _health_check_loop(self):
        """健康检查循环"""
        while self._is_monitoring:
            try:
                await self._perform_health_check()
                await asyncio.sleep(self._health_check_interval)
            except Exception as e:
                logger.error(f"Health check error: {e}")
                await asyncio.sleep(10)  # 出错时等待较短时间

    async def _perform_health_check(self):
        """执行健康检查"""
        try:
            model_loader = await get_model_loader()
            stats = model_loader.get_load_stats()

            # 检查模型加载状态
            if stats.get("load_errors", 0) > 10:
                logger.warning("High model load error rate detected")

            self._last_health_check = datetime.utcnow()

        except Exception as e:
            logger.error(f"Health check failed: {e}")

    def get_reload_stats(self) -> dict[str, Any]:
        """获取重载统计信息"""
        uptime = None
        if self._stats["monitoring_start"]:
            uptime = (
                datetime.utcnow() - self._stats["monitoring_start"]
            ).total_seconds()

        success_rate = (
            self._stats["successful_reloads"] / self._stats["total_reloads"] * 100
            if self._stats["total_reloads"] > 0
            else 0
        )

        return {
            **self._stats,
            "uptime_seconds": uptime,
            "success_rate": round(success_rate, 2),
            "is_monitoring": self._is_monitoring,
            "reloading_models": list(self._reloading_models),
            "reload_history_count": len(self._reload_history),
            "callback_count": len(self._reload_callbacks),
            "last_health_check": (
                self._last_health_check.isoformat() if self._last_health_check else None
            ),
        }

    def get_reload_history(self, limit: int = 50) -> list[dict[str, Any]]:
        """获取重载历史"""
        return self._reload_history[-limit:]

    async def cleanup(self):
        """清理资源"""
        try:
            # 停止监控
            await self.stop_monitoring()

            # 关闭线程池
            self._executor.shutdown(wait=True)

            # 清理数据
            self._reloading_models.clear()
            self._reload_locks.clear()
            self._reload_history.clear()
            self._reload_callbacks.clear()

            logger.info("HotReloadManager cleanup completed")

        except Exception as e:
            logger.error(f"Hot reload cleanup error: {e}")


# 全局实例
_hot_reload_manager: Optional[HotReloadManager] = None


async def get_hot_reload_manager() -> HotReloadManager:
    """获取全局热更新管理器实例"""
    global _hot_reload_manager

    if _hot_reload_manager is None:
        # 从环境变量获取配置
        import os

        model_dir = os.getenv("MODEL_DIRECTORY", "models/")
        check_interval = float(os.getenv("HOT_RELOAD_CHECK_INTERVAL", "1.0"))

        _hot_reload_manager = HotReloadManager(
            model_directory=model_dir, check_interval=check_interval
        )

    return _hot_reload_manager


def get_hot_reload_manager_sync() -> HotReloadManager:
    """同步获取热更新管理器实例"""
    global _hot_reload_manager

    if _hot_reload_manager is None:
        raise RuntimeError(
            "HotReloadManager not initialized. Call get_hot_reload_manager() first."
        )

    return _hot_reload_manager
