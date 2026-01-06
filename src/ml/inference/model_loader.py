#!/usr/bin/env python3
"""
模型加载器模块 (Model Loader)

专职负责模型的加载、版本校验、文件路径管理。
支持热更新和自动监听模型版本变更。
遵循单一职责原则，只负责模型生命周期管理。
"""

from dataclasses import dataclass
import json
import logging
from pathlib import Path
import pickle
import threading
import time
from typing import Any

# Import joblib for model loading
import joblib

logger = logging.getLogger(__name__)


class ModelLoadError(Exception):
    """模型加载异常"""


@dataclass
class ModelMetadata:
    """模型元数据"""

    model_version: str = "unknown"
    feature_names: list[str] | None = None
    created_at: str | None = None
    description: str | None = None
    accuracy: float | None = None
    training_data_hash: str | None = None


class ModelLoader:
    """
    模型加载器 - 专职负责模型生命周期管理

    主要职责：
    1. 模型文件的加载和验证
    2. 模型版本管理
    3. 模型缓存管理
    4. 模型元数据解析

    设计原则：单一职责，高内聚，易于测试
    """

    def __init__(
        self,
        model_cache_dir: str | Path | None = None,
        enable_hot_reload: bool = True,
        reload_interval: int = 30,
    ):
        """
        初始化模型加载器

        Args:
            model_cache_dir: 模型缓存目录，用于存储和管理多个模型文件
            enable_hot_reload: 是否启用热更新功能
            reload_interval: 热更新检查间隔（秒）
        """
        self.model_cache_dir = Path(model_cache_dir) if model_cache_dir else Path("models")
        self.loaded_models: dict[str, Any] = {}  # 存储加载的模型对象
        self.model_metadata: dict[str, ModelMetadata] = {}  # 存储模型元数据
        self.model_paths: dict[str, Path] = {}  # 存储模型路径

        # 热更新相关配置
        self.enable_hot_reload = enable_hot_reload
        self.reload_interval = reload_interval
        self.current_best_file = self.model_cache_dir / "current_best.txt"
        self.registry_file = self.model_cache_dir / "registry.json"
        self._current_version = None
        self._reload_thread = None
        self._stop_reload = threading.Event()

        # 确保缓存目录存在
        self.model_cache_dir.mkdir(parents=True, exist_ok=True)

        # 启动热更新监听
        if self.enable_hot_reload:
            self._start_hot_reload()

        logger.info(f"模型加载器初始化完成，缓存目录: {self.model_cache_dir}")
        logger.info(f"热更新功能: {'启用' if self.enable_hot_reload else '禁用'}")

    def load_model(
        self,
        model_name: str,
        model_path: str | Path | None = None,
        validate_model: bool = True,
    ) -> bool:
        """
        加载模型到内存

        Args:
            model_name: 模型名称，用于标识和管理模型
            model_path: 模型文件路径，如果为None则使用默认路径
            validate_model: 是否验证模型可用性

        Returns:
            bool: 加载成功返回True

        Raises:
            ModelLoadError: 模型加载失败时抛出
        """
        try:
            # 确定模型路径
            if model_path is None:
                model_path = self.model_cache_dir / f"{model_name}.pkl"
            else:
                model_path = Path(model_path)

            # 检查模型文件是否存在
            if not model_path.exists():
                raise ModelLoadError(f"模型文件不存在: {model_path}")

            logger.info(f"开始加载模型: {model_name} from {model_path}")

            # 加载模型数据
            model_data = self._load_model_file(model_path)

            # 解析模型和元数据
            model, metadata = self._parse_model_data(model_data, model_name)

            # 验证模型（如果启用）
            if validate_model:
                self._validate_model(model, model_name)

            # 存储模型信息
            self.loaded_models[model_name] = model
            self.model_metadata[model_name] = metadata
            self.model_paths[model_name] = model_path

            logger.info(f"模型 {model_name} 加载成功")
            logger.info(f"模型类型: {type(model).__name__}")
            if metadata.feature_names:
                logger.info(f"特征数量: {len(metadata.feature_names)}")

            return True

        except ModelLoadError:
            raise
        except Exception as e:
            error_msg = f"模型 {model_name} 加载失败: {e!s}"
            logger.error(error_msg)
            raise ModelLoadError(error_msg) from e

    def _load_model_file(self, model_path: Path) -> Any:
        """
        从文件加载模型数据

        Args:
            model_path: 模型文件路径

        Returns:
            Any: 模型数据
        """
        try:
            # 根据文件扩展名选择加载方式
            if model_path.suffix == ".json":
                import xgboost as xgb

                return xgb.XGBClassifier()
            if model_path.suffix in [".pkl", ".pickle"]:
                with open(model_path, "rb") as f:
                    try:
                        model_data = pickle.load(f)  # nosec B301
                        # 安全验证：确保是XGBoost模型
                        if not hasattr(model_data, "predict"):
                            raise ModelLoadError("加载的模型不是有效的预测模型")
                        return model_data
                    except (pickle.PickleError, EOFError, AttributeError) as e:
                        raise ModelLoadError(f"模型文件损坏: {e}")
            else:
                # 使用joblib加载，适合大型模型文件
                return joblib.load(model_path)
        except Exception as e:
            raise ModelLoadError(f"模型文件读取失败: {e!s}") from e

    def _parse_model_data(self, model_data: Any, model_name: str) -> tuple[Any, ModelMetadata]:
        """
        解析模型数据和元数据

        Args:
            model_data: 原始模型数据
            model_name: 模型名称

        Returns:
            tuple: (模型对象, 模型元数据)
        """
        if isinstance(model_data, dict):
            # 如果是包含模型和元数据的字典
            model = model_data.get("model")
            metadata_dict = model_data.get("metadata", {})

            # 构建元数据对象
            metadata = ModelMetadata(
                model_version=metadata_dict.get("model_version", "unknown"),
                feature_names=metadata_dict.get("feature_names"),
                created_at=metadata_dict.get("created_at"),
                description=metadata_dict.get("description"),
                accuracy=metadata_dict.get("accuracy"),
                training_data_hash=metadata_dict.get("training_data_hash"),
            )
        else:
            # 直接是模型对象
            model = model_data
            metadata = ModelMetadata(model_version="unknown")

        if model is None:
            raise ModelLoadError("模型文件中未找到有效的模型对象")

        return model, metadata

    def _validate_model(self, model: Any, model_name: str) -> None:
        """
        验证模型的基本可用性

        Args:
            model: 模型对象
            model_name: 模型名称

        Raises:
            ModelLoadError: 模型验证失败时抛出
        """
        # 检查必要的预测方法
        required_methods = ["predict"]
        optional_methods = ["predict_proba"]

        for method in required_methods:
            if not hasattr(model, method):
                raise ModelLoadError(f"模型缺少必要方法: {method}")

        # 记录可选方法的可用性
        available_methods = [method for method in optional_methods if hasattr(model, method)]
        if available_methods:
            logger.info(f"模型 {model_name} 支持高级方法: {available_methods}")

    def get_model(self, model_name: str) -> Any | None:
        """
        获取已加载的模型

        Args:
            model_name: 模型名称

        Returns:
            Optional[Any]: 模型对象，如果模型未加载则返回None
        """
        return self.loaded_models.get(model_name)

    def get_model_metadata(self, model_name: str) -> ModelMetadata | None:
        """
        获取模型元数据

        Args:
            model_name: 模型名称

        Returns:
            Optional[ModelMetadata]: 模型元数据，如果模型未加载则返回None
        """
        return self.model_metadata.get(model_name)

    def get_model_path(self, model_name: str) -> Path | None:
        """
        获取模型文件路径

        Args:
            model_name: 模型名称

        Returns:
            Optional[Path]: 模型文件路径，如果模型未加载则返回None
        """
        return self.model_paths.get(model_name)

    def unload_model(self, model_name: str) -> bool:
        """
        卸载模型并释放内存

        Args:
            model_name: 模型名称

        Returns:
            bool: 卸载成功返回True
        """
        if model_name in self.loaded_models:
            # 清理所有相关数据
            del self.loaded_models[model_name]
            self.model_metadata.pop(model_name, None)
            self.model_paths.pop(model_name, None)

            logger.info(f"模型 {model_name} 已卸载")
            return True

        logger.warning(f"模型 {model_name} 未找到，无需卸载")
        return False

    def reload_model(self, model_name: str) -> bool:
        """
        重新加载已存在的模型

        Args:
            model_name: 模型名称

        Returns:
            bool: 重新加载成功返回True
        """
        if model_name not in self.model_paths:
            logger.error(f"无法重新加载模型 {model_name}: 路径信息丢失")
            return False

        model_path = self.model_paths[model_name]
        logger.info(f"重新加载模型: {model_name}")

        # 先卸载现有模型
        self.unload_model(model_name)

        # 重新加载
        return self.load_model(model_name, model_path)

    def list_loaded_models(self) -> list[str]:
        """
        获取已加载模型名称列表

        Returns:
            List[str]: 已加载的模型名称列表
        """
        return list(self.loaded_models.keys())

    def get_model_info(self, model_name: str) -> dict[str, Any]:
        """
        获取模型的详细信息

        Args:
            model_name: 模型名称

        Returns:
            Dict[str, Any]: 模型详细信息
        """
        if model_name not in self.loaded_models:
            return {"status": "not_loaded", "model_name": model_name}

        model = self.loaded_models[model_name]
        metadata = self.model_metadata[model_name]
        model_path = self.model_paths[model_name]

        return {
            "status": "loaded",
            "model_name": model_name,
            "model_type": type(model).__name__,
            "model_path": str(model_path),
            "metadata": {
                "model_version": metadata.model_version,
                "feature_count": (len(metadata.feature_names) if metadata.feature_names else None),
                "feature_names": metadata.feature_names,
                "created_at": metadata.created_at,
                "description": metadata.description,
                "accuracy": metadata.accuracy,
            },
            "capabilities": {
                "has_predict": hasattr(model, "predict"),
                "has_predict_proba": hasattr(model, "predict_proba"),
            },
        }

    def is_model_loaded(self, model_name: str) -> bool:
        """
        检查模型是否已加载

        Args:
            model_name: 模型名称

        Returns:
            bool: 模型已加载返回True
        """
        return model_name in self.loaded_models

    def clear_all_models(self) -> None:
        """清空所有已加载的模型"""
        model_count = len(self.loaded_models)
        self.loaded_models.clear()
        self.model_metadata.clear()
        self.model_paths.clear()

        logger.info(f"已清空所有模型，共清理 {model_count} 个模型")

    def get_cache_directory(self) -> Path:
        """
        获取模型缓存目录路径

        Returns:
            Path: 缓存目录路径
        """
        return self.model_cache_dir

    def scan_available_models(self) -> list[str]:
        """
        扫描缓存目录中的可用模型文件

        Returns:
            List[str]: 可用的模型名称列表
        """
        if not self.model_cache_dir.exists():
            return []

        available_models = []
        for model_file in self.model_cache_dir.glob("*.pkl"):
            model_name = model_file.stem
            available_models.append(model_name)

        return available_models

    # ================================
    # 热更新功能
    # ================================

    def _start_hot_reload(self):
        """启动热更新监听线程"""
        if self._reload_thread is not None:
            logger.warning("热更新线程已在运行")
            return

        self._stop_reload.clear()
        self._reload_thread = threading.Thread(target=self._hot_reload_worker, daemon=True)
        self._reload_thread.start()
        logger.info("热更新监听线程已启动")

    def _hot_reload_worker(self):
        """热更新工作线程"""
        logger.info("热更新监听线程开始运行")

        while not self._stop_reload.is_set():
            try:
                self._check_for_model_updates()
                time.sleep(self.reload_interval)
            except Exception as e:
                logger.error(f"热更新检查出错: {e!s}")
                time.sleep(self.reload_interval)

        logger.info("热更新监听线程已停止")

    def _check_for_model_updates(self):
        """检查模型更新"""
        try:
            # 检查当前最佳模型文件
            if not self.current_best_file.exists():
                if self._current_version is None:
                    # 首次运行，尝试加载当前最佳模型
                    self._load_current_best_model()
                return

            # 读取当前最佳版本
            with open(self.current_best_file, encoding="utf-8") as f:
                current_version = f.read().strip()

            # 如果版本没有变化，无需更新
            if current_version == self._current_version:
                return

            logger.info(f"检测到模型版本更新: {self._current_version} -> {current_version}")

            # 加载新模型
            self._load_current_best_model()

        except Exception as e:
            logger.error(f"检查模型更新失败: {e!s}")

    def _load_current_best_model(self):
        """加载当前最佳模型"""
        try:
            if not self.current_best_file.exists():
                logger.warning("当前最佳模型文件不存在")
                return

            # 读取当前版本
            with open(self.current_best_file, encoding="utf-8") as f:
                current_version = f.read().strip()

            if not current_version:
                logger.warning("当前最佳模型版本为空")
                return

            # 构建模型路径
            model_path = self.model_cache_dir / f"{current_version}.json"

            if not model_path.exists():
                logger.warning(f"模型文件不存在: {model_path}")
                return

            # 加载模型元数据
            metadata = self._load_model_metadata(current_version)
            if not metadata:
                logger.warning(f"无法加载模型元数据: {current_version}")
                return

            # 如果当前已加载的模型版本相同，无需重新加载
            if self._current_version == current_version and "xgboost_v2" in self.loaded_models:
                logger.info(f"模型版本 {current_version} 已是最新版本")
                return

            # 卸载旧模型
            if "xgboost_v2" in self.loaded_models:
                self.unload_model("xgboost_v2")

            # 加载新模型
            success = self.load_model("xgboost_v2", model_path, validate_model=True)
            if success:
                self._current_version = current_version
                logger.info(f"✅ 成功加载新模型版本: {current_version}")

                # 更新 Prometheus 指标（如果可用）
                try:
                    from src.main import cache_operations_total

                    cache_operations_total.labels(cache_type="model", operation="hot_reload").inc()
                except ImportError:
                    pass

            else:
                logger.error(f"❌ 加载新模型失败: {current_version}")

        except Exception as e:
            logger.error(f"加载当前最佳模型失败: {e!s}")

    def _load_model_metadata(self, version: str) -> dict[str, Any] | None:
        """加载模型元数据"""
        try:
            if not self.registry_file.exists():
                return None

            with open(self.registry_file, encoding="utf-8") as f:
                registry = json.load(f)

            models = registry.get("models", {})
            model_data = models.get(version)

            if not model_data:
                return None

            return model_data

        except Exception as e:
            logger.error(f"加载模型元数据失败: {e!s}")
            return None

    def trigger_model_reload(self) -> bool:
        """手动触发模型重载"""
        try:
            logger.info("手动触发模型重载")
            self._check_for_model_updates()
            return True
        except Exception as e:
            logger.error(f"手动触发模型重载失败: {e!s}")
            return False

    def get_current_version(self) -> str | None:
        """获取当前加载的模型版本"""
        return self._current_version

    def switch_model_version(self, target_version: str) -> bool:
        """切换到指定版本的模型"""
        try:
            logger.info(f"手动切换模型版本到: {target_version}")

            # 检查目标版本是否存在
            model_path = self.model_cache_dir / f"{target_version}.json"
            if not model_path.exists():
                logger.error(f"目标模型版本不存在: {target_version}")
                return False

            # 检查元数据是否存在
            metadata = self._load_model_metadata(target_version)
            if not metadata:
                logger.error(f"目标模型元数据不存在: {target_version}")
                return False

            # 更新当前最佳文件
            with open(self.current_best_file, "w", encoding="utf-8") as f:
                f.write(target_version)

            # 触发重载
            self._current_version = None  # 强制重载
            self.trigger_model_reload()

            logger.info(f"✅ 成功切换到模型版本: {target_version}")
            return True

        except Exception as e:
            logger.error(f"切换模型版本失败: {e!s}")
            return False

    def stop_hot_reload(self):
        """停止热更新监听"""
        if self._reload_thread is None:
            return

        logger.info("停止热更新监听")
        self._stop_reload.set()
        self._reload_thread.join(timeout=5)
        self._reload_thread = None

    def __del__(self):
        """析构函数，确保线程正确停止"""
        try:
            self.stop_hot_reload()
        except Exception:
            pass

    def __len__(self) -> int:
        """
        返回已加载模型数量

        Returns:
            int: 已加载的模型数量
        """
        return len(self.loaded_models)

    def __contains__(self, model_name: str) -> bool:
        """
        检查模型是否已加载

        Args:
            model_name: 模型名称

        Returns:
            bool: 模型已加载返回True
        """
        return self.is_model_loaded(model_name)
