"""
基准模型训练器 - 兼容性包装器

为了保持向后兼容性，此文件重新导出新模块化结构中的类和函数。
实际的实现已经拆分到 src/models/training/ 目录下。
"""

# 从新模块化结构导入所有组件
from .training import BaselineModelTrainer

# 处理可选依赖（保持向后兼容）
try:
    import xgboost as xgb
    HAS_XGB = True
except ImportError:
    HAS_XGB = False
    xgb = None

try:
    import mlflow
    import mlflow.sklearn
    from mlflow import MlflowClient
    HAS_MLFLOW = True
except ImportError:
    HAS_MLFLOW = False
    # 创建一个模拟的 mlflow 对象
    class MockMLflow:
        def start_run(self, **kwargs):
            return self

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def log_metric(self, *args, **kwargs):
            pass

        def log_param(self, *args, **kwargs):
            pass

        def log_artifacts(self, *args, **kwargs):
            pass

        class sklearn:
            @staticmethod
            def log_model(*args, **kwargs):
                pass

    mlflow = MockMLflow()
    mlflow.sklearn = MockMLflow.sklearn()

    class MockMlflowClient:
        def __init__(self, *args, **kwargs):
            pass

        def get_latest_versions(self, *args, **kwargs):
            return []

    MlflowClient = MockMlflowClient

# 重新导出以保持向后兼容性
__all__ = [
    "BaselineModelTrainer",
    "HAS_XGB",
    "HAS_MLFLOW",
    "xgb",
    "mlflow",
    "MlflowClient",
]