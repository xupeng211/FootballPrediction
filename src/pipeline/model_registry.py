"""
Model Registry - 模型注册表和版本管理

统一的模型保存、加载和版本管理。
支持元数据管理、模型比较和部署准备。

主要功能:
- 模型保存和加载
- 版本管理和元数据
- 模型比较和选择
- 部署包生成
- 跨环境兼容

P0-4 核心组件 - 统一模型管理
"""

from __future__ import annotations

import json
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import joblib
import pandas as pd

from .config import PipelineConfig

logger = logging.getLogger(__name__)


class ModelRegistry:
    """
    模型注册表.

    提供统一的模型保存、加载和版本管理功能。
    """

    def __init__(self, config: Optional[PipelineConfig] = None):
        """初始化模型注册表.

        Args:
            config: 流水线配置
        """
        self.config = config or PipelineConfig()
        self.models_dir = Path(self.config.models_dir)

        # 确保目录存在
        self.models_dir.mkdir(parents=True, exist_ok=True)

        # 模型索引
        self._model_index: Dict[str, List[Dict[str, Any]]] = {}
        self._load_model_index()

    def save_model(
        self,
        model: Any,
        name: str,
        version: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        include_preprocessors: bool = True,
    ) -> str:
        """
        保存模型.

        Args:
            model: 训练好的模型对象
            name: 模型名称
            version: 模型版本 (None自动生成)
            metadata: 模型元数据
            include_preprocessors: 是否包含预处理器

        Returns:
            模型路径
        """
        # 生成版本号
        if version is None:
            version = datetime.now().strftime("%Y%m%d_%H%M%S")

        # 创建模型目录
        model_dir = self.models_dir / name / version
        model_dir.mkdir(parents=True, exist_ok=True)

        # 保存模型文件
        model_path = model_dir / "model.joblib"
        joblib.dump(model, model_path)

        # 准备元数据
        model_metadata = {
            "name": name,
            "version": version,
            "created_at": datetime.now().isoformat(),
            "model_type": type(model).__name__,
            "model_module": type(model).__module__,
            "file_path": str(model_path.relative_to(self.models_dir.parent)),
            "environment": self.config.environment,
        }

        # 合并用户元数据
        if metadata:
            model_metadata.update(metadata)

        # 保存元数据
        metadata_path = model_dir / "metadata.json"
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(model_metadata, f, indent=2, default=str)

        # 保存预处理器 (如果有)
        if include_preprocessors and hasattr(self, '_preprocessors'):
            preprocessors_path = model_dir / "preprocessors.joblib"
            joblib.dump(self._preprocessors, preprocessors_path)

        # 更新索引
        self._update_model_index(name, model_metadata)

        logger.info(f"Model saved: {name}:{version} at {model_path}")
        return str(model_path)

    def load_model(
        self,
        name: str,
        version: Optional[str] = None,
        load_preprocessors: bool = True,
    ) -> Tuple[Any, Dict[str, Any]]:
        """
        加载模型.

        Args:
            name: 模型名称
            version: 模型版本 (None加载最新)
            load_preprocessors: 是否加载预处理器

        Returns:
            Tuple[模型, 元数据]
        """
        # 获取模型路径
        if version is None:
            version = self.get_latest_version(name)

        model_dir = self.models_dir / name / version
        if not model_dir.exists():
            raise FileNotFoundError(f"Model not found: {name}:{version}")

        # 加载模型
        model_path = model_dir / "model.joblib"
        model = joblib.load(model_path)

        # 加载元数据
        metadata_path = model_dir / "metadata.json"
        with open(metadata_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)

        # 加载预处理器 (如果存在且需要)
        if load_preprocessors:
            preprocessors_path = model_dir / "preprocessors.joblib"
            if preprocessors_path.exists():
                metadata["preprocessors"] = joblib.load(preprocessors_path)

        logger.info(f"Model loaded: {name}:{version}")
        return model, metadata

    def list_models(self, name: Optional[str] = None) -> Dict[str, List[Dict[str, Any]]]:
        """列出所有模型."""
        if name:
            return {name: self._model_index.get(name, [])}
        return self._model_index.copy()

    def get_latest_version(self, name: str) -> str:
        """获取模型的最新版本."""
        if name not in self._model_index or not self._model_index[name]:
            raise ValueError(f"No versions found for model: {name}")

        # 按创建时间排序，返回最新的
        versions = self._model_index[name]
        latest = max(versions, key=lambda x: x["created_at"])
        return latest["version"]

    def compare_models(
        self, name: str, versions: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """比较模型版本."""
        if versions is None:
            versions = [v["version"] for v in self._model_index.get(name, [])]

        comparison_data = []

        for version in versions:
            try:
                _, metadata = self.load_model(name, version, load_preprocessors=False)
                comparison_data.append({
                    "version": version,
                    "created_at": metadata["created_at"],
                    "model_type": metadata["model_type"],
                    "environment": metadata["environment"],
                    # 添加指标比较 (如果元数据中有)
                    **{
                        k: v for k, v in metadata.items()
                        if k.startswith("metric_") or k in ["accuracy", "f1_score"]
                    }
                })
            except Exception as e:
                logger.warning(f"Failed to load model {name}:{version} - {e}")

        return pd.DataFrame(comparison_data)

    def delete_model(self, name: str, version: Optional[str] = None) -> bool:
        """删除模型."""
        if version is None:
            # 删除所有版本
            if name in self._model_index:
                for model_version in self._model_index[name]:
                    model_dir = self.models_dir / name / model_version["version"]
                    if model_dir.exists():
                        shutil.rmtree(model_dir)

                del self._model_index[name]
                logger.info(f"Deleted all versions of model: {name}")
                return True
        else:
            # 删除特定版本
            model_dir = self.models_dir / name / version
            if model_dir.exists():
                shutil.rmtree(model_dir)

                # 更新索引
                if name in self._model_index:
                    self._model_index[name] = [
                        v for v in self._model_index[name] if v["version"] != version
                    ]
                    if not self._model_index[name]:
                        del self._model_index[name]

                logger.info(f"Deleted model: {name}:{version}")
                return True

        return False

    def export_model(
        self,
        name: str,
        version: Optional[str] = None,
        export_path: str = "deployment_package",
    ) -> str:
        """
        导出模型为部署包.

        Args:
            name: 模型名称
            version: 模型版本
            export_path: 导出路径

        Returns:
            导出包路径
        """
        if version is None:
            version = self.get_latest_version(name)

        export_dir = Path(export_path) / f"{name}_{version}"
        export_dir.mkdir(parents=True, exist_ok=True)

        # 复制模型文件
        model_dir = self.models_dir / name / version
        shutil.copytree(model_dir, export_dir / "model", dirs_exist_ok=True)

        # 创建部署配置
        deployment_config = {
            "model_name": name,
            "model_version": version,
            "exported_at": datetime.now().isoformat(),
            "environment": self.config.environment,
            "requirements": [
                "scikit-learn",
                "pandas",
                "numpy",
                "joblib",
                "xgboost",  # 根据模型类型动态添加
            ],
        }

        with open(export_dir / "deployment_config.json", "w") as f:
            json.dump(deployment_config, f, indent=2)

        # 创建推理脚本模板
        inference_script = f'''#!/usr/bin/env python3
"""
模型推理脚本 - {name}:{version}
"""

import joblib
import json
from pathlib import Path

def load_model():
    """加载模型."""
    model_path = Path(__file__).parent / "model" / "model.joblib"
    metadata_path = Path(__file__).parent / "model" / "metadata.json"

    model = joblib.load(model_path)
    with open(metadata_path, "r") as f:
        metadata = json.load(f)

    return model, metadata

def predict(features):
    """执行预测."""
    model, metadata = load_model()
    return model.predict(features)

if __name__ == "__main__":
    # 示例用法
    model, metadata = load_model()
    print(f"Loaded model: {{metadata['name']}}:{{metadata['version']}}")
'''

        with open(export_dir / "predict.py", "w") as f:
            f.write(inference_script)

        # 使推理脚本可执行
        (export_dir / "predict.py").chmod(0o755)

        logger.info(f"Model exported to: {export_dir}")
        return str(export_dir)

    def _load_model_index(self) -> None:
        """加载模型索引."""
        index_path = self.models_dir / "model_index.json"

        if index_path.exists():
            try:
                with open(index_path, "r", encoding="utf-8") as f:
                    self._model_index = json.load(f)
                logger.debug("Model index loaded")
            except Exception as e:
                logger.warning(f"Failed to load model index: {e}")
                self._model_index = {}
        else:
            self._model_index = {}
            self._rebuild_model_index()

    def _save_model_index(self) -> None:
        """保存模型索引."""
        index_path = self.models_dir / "model_index.json"

        with open(index_path, "w", encoding="utf-8") as f:
            json.dump(self._model_index, f, indent=2, default=str)

        logger.debug("Model index saved")

    def _update_model_index(self, name: str, metadata: Dict[str, Any]) -> None:
        """更新模型索引."""
        if name not in self._model_index:
            self._model_index[name] = []

        # 检查版本是否已存在
        version = metadata["version"]
        existing_indices = [
            i for i, m in enumerate(self._model_index[name])
            if m["version"] == version
        ]

        if existing_indices:
            # 更新现有记录
            self._model_index[name][existing_indices[0]] = metadata
        else:
            # 添加新记录
            self._model_index[name].append(metadata)

        # 按创建时间排序
        self._model_index[name].sort(key=lambda x: x["created_at"])

        # 保存索引
        self._save_model_index()

    def _rebuild_model_index(self) -> None:
        """重建模型索引."""
        logger.info("Rebuilding model index from file system")

        self._model_index = {}

        for model_dir in self.models_dir.iterdir():
            if not model_dir.is_dir():
                continue

            model_name = model_dir.name

            for version_dir in model_dir.iterdir():
                if not version_dir.is_dir():
                    continue

                metadata_path = version_dir / "metadata.json"
                if metadata_path.exists():
                    try:
                        with open(metadata_path, "r", encoding="utf-8") as f:
                            metadata = json.load(f)

                        if model_name not in self._model_index:
                            self._model_index[model_name] = []

                        self._model_index[model_name].append(metadata)
                    except Exception as e:
                        logger.warning(f"Failed to load metadata from {metadata_path}: {e}")

        # 保存重建的索引
        self._save_model_index()
        logger.info(f"Model index rebuilt with {len(self._model_index)} models")

    def get_model_info(self, name: str, version: Optional[str] = None) -> Dict[str, Any]:
        """获取模型详细信息."""
        if version is None:
            version = self.get_latest_version(name)

        _, metadata = self.load_model(name, version, load_preprocessors=False)
        return metadata

    def cleanup_old_versions(self, name: str, keep_count: int = 5) -> int:
        """清理旧版本，保留最近的几个版本."""
        if name not in self._model_index:
            return 0

        versions = sorted(
            self._model_index[name],
            key=lambda x: x["created_at"],
            reverse=True,
        )

        if len(versions) <= keep_count:
            return 0

        old_versions = versions[keep_count:]
        deleted_count = 0

        for version_info in old_versions:
            if self.delete_model(name, version_info["version"]):
                deleted_count += 1

        logger.info(f"Cleaned up {deleted_count} old versions of model {name}")
        return deleted_count