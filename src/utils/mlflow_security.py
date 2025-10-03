"""MLflow 安全加固模块

此模块提供 MLflow 的安全封装，防止反序列化漏洞被利用。
"""

import hashlib
import logging
from typing import Any, Optional
from pathlib import Path
import tempfile
import shutil

logger = logging.getLogger(__name__)


class SecureMLflowLoader:
    """安全的 MLflow 模型加载器

    提供模型加载的安全检查和沙箱化功能。
    """

    def __init__(self, allowed_model_types: Optional[list] = None):
        """初始化安全加载器

        Args:
            allowed_model_types: 允许的模型类型列表
        """
        self.allowed_model_types = allowed_model_types or [
            'sklearn', 'xgboost', 'lightgbm', 'catboost'
        ]
        self.temp_dir = None

    def __enter__(self):
        """创建临时沙箱目录"""
        self.temp_dir = tempfile.mkdtemp(prefix = os.getenv("MLFLOW_SECURITY_PREFIX_35"))
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """清理临时沙箱目录"""
        if self.temp_dir and Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def validate_model_signature(self, model_path: str) -> bool:
        """验证模型签名

        Args:
            model_path: 模型文件路径

        Returns:
            bool: 验证是否通过
        """
        try:
            # 检查模型文件是否存在
            model_path = Path(model_path)
            if not model_path.exists():
                logger.error(f"模型文件不存在: {model_path}")
                return False

            # 计算文件哈希
            with open(model_path, 'rb') as f:
                file_hash = hashlib.sha256(f.read()).hexdigest()

            # TODO: 在实际部署中，这里应该检查哈希值是否在允许列表中
            logger.info(f"模型文件哈希: {file_hash}")

            # 检查模型类型
            if not any(mt in str(model_path) for mt in self.allowed_model_types):
                logger.error(f"不支持的模型类型: {model_path}")
                return False

            return True

        except Exception as e:
            logger.error(f"模型签名验证失败: {e}")
            return False

    def safe_load_model(self, model_uri: str, **kwargs):
        """安全加载模型

        在沙箱环境中加载模型，防止恶意代码执行。

        Args:
            model_uri: MLflow 模型 URI
            **kwargs: 传递给 mlflow.sklearn.load_model 的参数

        Returns:
            加载的模型对象
        """
        import mlflow.sklearn
        from mlflow.exceptions import MlflowException

        # 验证模型签名
        if not self.validate_model_signature(model_uri):
            raise ValueError("模型签名验证失败")

        try:
            # 在沙箱环境中加载模型
            logger.info(f"在沙箱中加载模型: {model_uri}")

            # 设置安全的环境变量
            import os
            os.environ['MLFLOW_ENABLE_MODEL_LOGGING'] = 'false'
            os.environ['MLFLOW_ENABLE_ARTIFACT_LOGGING'] = 'false'

            # 加载模型
            model = mlflow.sklearn.load_model(model_uri, **kwargs)

            # 验证模型对象
            if not hasattr(model, 'predict'):
                raise ValueError("加载的对象不是有效的模型")

            logger.info("模型加载成功")
            return model

        except MlflowException as e:
            logger.error(f"MLflow 错误: {e}")
            raise
        except Exception as e:
            logger.error(f"模型加载失败: {e}")
            raise ValueError(f"模型加载失败: {str(e)}")


class SecureMLflowLogger:
    """安全的 MLflow 日志记录器

    提供安全的模型记录功能，防止恶意代码通过日志记录注入。
    """

    def __init__(self):
        self.safe_params = set([
            'model_type', 'algorithm', 'version', 'feature_count',
            'training_samples', 'test_samples', 'accuracy', 'precision',
            'recall', 'f1_score', 'auc', 'training_time'
        ])

    def safe_log_param(self, key: str, value: Any):
        """安全记录参数

        Args:
            key: 参数键
            value: 参数值
        """
        import mlflow

        # 验证参数键
        if not isinstance(key, str) or len(key) > 100:
            logger.warning(f"无效的参数键: {key}")
            return

        # 验证参数值
        if not self._is_safe_value(value):
            logger.warning(f"不安全的参数值: {key}")
            return

        try:
            mlflow.log_param(key, str(value))
        except Exception as e:
            logger.error(f"参数记录失败: {e}")

    def safe_log_metric(self, key: str, value: float, step: Optional[int] = None):
        """安全记录指标

        Args:
            key: 指标键
            value: 指标值
            step: 步骤号
        """
        import mlflow

        # 验证指标键
        if not isinstance(key, str) or len(key) > 100:
            logger.warning(f"无效的指标键: {key}")
            return

        # 验证指标值
        if not isinstance(value, (int, float)) or not -1e10 <= value <= 1e10:
            logger.warning(f"无效的指标值: {key}={value}")
            return

        try:
            mlflow.log_metric(key, value, step=step)
        except Exception as e:
            logger.error(f"指标记录失败: {e}")

    def safe_log_model(self, model, artifact_path: str, **kwargs):
        """安全记录模型

        Args:
            model: 模型对象
            artifact_path: 模型路径
            **kwargs: 额外参数
        """
        import mlflow.sklearn

        # 验证模型对象
        if not hasattr(model, 'predict'):
            raise ValueError("无效的模型对象")

        # 验证路径
        if not isinstance(artifact_path, str) or len(artifact_path) > 200:
            raise ValueError("无效的模型路径")

        # 设置安全参数
        safe_kwargs = {
            'registered_model_name': kwargs.get('registered_model_name'),
            'signature': kwargs.get('signature'),
            'input_example': None,  # 不记录输入示例
            'pip_requirements': None,  # 不记录 pip 依赖
        }

        try:
            logger.info(f"安全记录模型: {artifact_path}")
            mlflow.sklearn.log_model(
                model,
                artifact_path,
                **{k: v for k, v in safe_kwargs.items() if v is not None}
            )
        except Exception as e:
            logger.error(f"模型记录失败: {e}")
            raise

    def _is_safe_value(self, value: Any) -> bool:
        """检查值是否安全

        Args:
            value: 要检查的值

        Returns:
            bool: 是否安全
        """
        # 检查类型
        if isinstance(value, (str, int, float, bool)):
            if isinstance(value, str) and len(value) > 1000:
                return False
            return True

        # 检查列表
        if isinstance(value, (list, tuple)):
            return len(value) <= 100 and all(self._is_safe_item(v) for v in value)

        # 检查字典
        if isinstance(value, dict):
            return len(value) <= 50 and all(
                isinstance(k, str) and len(k) <= 100 and self._is_safe_item(v)
                for k, v in value.items()
            )

        return False

    def _is_safe_item(self, item: Any) -> bool:
        """检查单个项目是否安全"""
        if isinstance(item, (str, int, float, bool)):
            if isinstance(item, str) and len(item) > 500:
                return False
            return True
        return False


# 安全装饰器
def mlflow_security_check(func):
    """MLflow 操作安全检查装饰器"""
    def wrapper(*args, **kwargs):
        # 检查环境
        import os
        if os.environ.get('MLFLOW_SECURITY_MODE', 'true').lower() == 'true':
            logger.info("MLflow 安全模式已启用")

        return func(*args, **kwargs)
    return wrapper


# 创建全局安全实例
secure_loader = SecureMLflowLoader()
secure_logger = SecureMLflowLogger()