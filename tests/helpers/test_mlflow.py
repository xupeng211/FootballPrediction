"""MLflow 测试桩实现 - 重构版本（不使用 monkeypatch）"""

from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any, Dict, List, Optional


@dataclass
class MockMlflowRun:
    """简化的 MLflow run 上下文对象"""

    run_id: str = "mock-run"

    def __enter__(self) -> "MockMlflowRun":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        return False

    @property
    def info(self) -> SimpleNamespace:
        return SimpleNamespace(run_id=self.run_id)


class MockMlflow:
    """捕获日志调用的 MLflow 模拟实现"""

    def __init__(self) -> None:
        self.experiments: Dict[str, SimpleNamespace] = {}
        self.runs: Dict[str, SimpleNamespace] = {}
        self.logged_metrics: Dict[str, List[Dict[str, Any]]] = {}
        self.logged_params: Dict[str, List[Dict[str, Any]]] = {}
        self.logged_artifacts: Dict[str, List[str]] = {}

    def set_experiment(self, experiment_name: str) -> None:
        """设置实验"""
        if experiment_name not in self.experiments:
            self.experiments[experiment_name] = SimpleNamespace(
                experiment_id=f"exp-{len(self.experiments)}",
                name=experiment_name,
            )

    def get_experiment_by_name(self, experiment_name: str) -> Optional[SimpleNamespace]:
        """获取实验"""
        return self.experiments.get(experiment_name)

    def start_run(
        self,
        run_name: Optional[str] = None,
        experiment_id: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
    ) -> MockMlflowRun:
        """开始运行"""
        run_id = f"run-{len(self.runs)}"
        run = SimpleNamespace(
            run_id=run_id,
            name=run_name or "mock-run",
            experiment_id=experiment_id or "default",
            tags=tags or {},
        )
        self.runs[run_id] = run
        self.logged_metrics[run_id] = []
        self.logged_params[run_id] = []
        self.logged_artifacts[run_id] = []

        return MockMlflowRun(run_id=run_id)

    def log_metric(self, key: str, value: float, step: Optional[int] = None) -> None:
        """记录指标"""
        active_run = self.active_run()
        if active_run:
            self.logged_metrics[active_run.run_id].append(
                {"key": key, "value": value, "step": step}
            )

    def log_param(self, key: str, value: Any) -> None:
        """记录参数"""
        active_run = self.active_run()
        if active_run:
            self.logged_params[active_run.run_id].append({"key": key, "value": value})

    def log_artifact(self, local_path: str, artifact_path: Optional[str] = None) -> None:
        """记录文件"""
        active_run = self.active_run()
        if active_run:
            self.logged_artifacts[active_run.run_id].append(local_path)

    def active_run(self) -> Optional[SimpleNamespace]:
        """获取当前运行"""
        # 简单实现:返回最后一个运行
        if self.runs:
            run_id = list(self.runs.keys())[-1]
            return self.runs[run_id]
        return None


class MockMlflowClient:
    """模拟 MLflow 客户端"""

    def __init__(self, tracking_uri: Optional[str] = None) -> None:
        self.tracking_uri = tracking_uri or "http://localhost:5000"
        self._mlflow = MockMlflow()

    def list_experiments(self) -> List[SimpleNamespace]:
        """列出所有实验"""
        return list(self._mlflow.experiments.values())

    def create_experiment(self, name: str, tags: Optional[Dict[str, str]] = None) -> str:
        """创建实验"""
        exp_id = f"exp-{len(self._mlflow.experiments)}"
        self._mlflow.experiments[name] = SimpleNamespace(
            experiment_id=exp_id, name=name, tags=tags or {}
        )
        return exp_id


# 创建全局 mock 实例（仅在测试中使用）
_global_mlflow_mock = None
_global_client_mock = None


def get_mock_mlflow() -> MockMlflow:
    """获取 MLflow mock 实例（单例）"""
    global _global_mlflow_mock
    if _global_mlflow_mock is None:
        _global_mlflow_mock = MockMlflow()
    return _global_mlflow_mock


def get_mock_mlflow_client(tracking_uri: Optional[str] = None) -> MockMlflowClient:
    """获取 MLflow Client mock 实例"""
    return MockMlflowClient(tracking_uri)


def reset_mlflow_mocks() -> None:
    """重置 MLflow mock 实例（用于测试隔离）"""
    global _global_mlflow_mock, _global_client_mock
    if _global_mlflow_mock:
        _global_mlflow_mock.experiments.clear()
        _global_mlflow_mock.runs.clear()
        _global_mlflow_mock.logged_metrics.clear()
        _global_mlflow_mock.logged_params.clear()
        _global_mlflow_mock.logged_artifacts.clear()


# 向后兼容的函数（现在只是返回 mock 实例,不使用 monkeypatch）
def apply_mlflow_mocks(*args, **kwargs) -> Dict[str, Any]:
    """
    向后兼容:返回 MLflow mocks
    不再使用 monkeypatch,而是返回 mock 实例供测试使用
    """
    return {
        "mlflow": get_mock_mlflow(),
        "mlflow.client": {
            "MlflowClient": MockMlflowClient,
        },
        "mlflow.tracking": {
            "MlflowClient": MockMlflowClient,
        },
    }


__all__ = [
    "MockMlflowRun",
    "MockMlflow",
    "MockMlflowClient",
    "get_mock_mlflow",
    "get_mock_mlflow_client",
    "reset_mlflow_mocks",
    "apply_mlflow_mocks",
]
