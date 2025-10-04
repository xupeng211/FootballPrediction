"""MLflow 测试桩实现"""

import sys
from dataclasses import dataclass
from types import ModuleType, SimpleNamespace
from typing import Any, Dict, List, Optional

from pytest import MonkeyPatch


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
        self._tracking_uri = "mlflow://tests"
        self.logged_params: List[Dict[str, Any]] = []
        self.logged_metrics: List[Dict[str, Any]] = []
        self.tags: Dict[str, Any] = {}
        self.current_experiment: Optional[str] = None

    def set_tracking_uri(self, uri: str) -> None:
        self._tracking_uri = uri

    def get_tracking_uri(self) -> str:
        return self._tracking_uri

    def start_run(self, experiment_id: Optional[str] = None) -> MockMlflowRun:
        run_id = f"mock-run-{experiment_id or 'default'}"
        return MockMlflowRun(run_id=run_id)

    def log_params(self, params: Dict[str, Any]) -> None:
        self.logged_params.append(dict(params))

    def log_metrics(self, metrics: Dict[str, Any], step: Optional[int] = None) -> None:
        payload = dict(metrics)
        if step is not None:
            payload["step"] = step
        self.logged_metrics.append(payload)

    def log_metric(self, key: str, value: Any, step: Optional[int] = None) -> None:
        self.log_metrics({key: value}, step=step)

    def set_tags(self, tags: Dict[str, Any]) -> None:
        self.tags.update(tags)

    def get_experiment_by_name(self, name: str) -> Dict[str, Any]:
        return {"name": name, "experiment_id": f"mock-exp-{name}"}

    def create_experiment(self, name: str) -> str:
        return f"mock-exp-{name}"

    def set_experiment(self, name: str) -> None:
        self.current_experiment = name

    def log_model(self, *args: Any, **kwargs: Any) -> bool:
        return True

    def sklearn_log_model(self, *args: Any, **kwargs: Any) -> bool:
        return True


class MockMlflowClient:
    """精简版 MlflowClient"""

    def __init__(self, tracking_uri: Optional[str] = None) -> None:
        self.tracking_uri = tracking_uri or "mlflow://tests"

    def search_registered_models(self, *args: Any, **kwargs: Any) -> List[Any]:
        return []

    def get_latest_versions(self, name: str, stages: Optional[List[str]] = None) -> List[Any]:
        return []

    def get_model_version(self, name: str, version: Any) -> SimpleNamespace:
        return SimpleNamespace(name=name, version=version, run_id="mock-run")

    def get_run(self, run_id: str) -> SimpleNamespace:
        return SimpleNamespace(data=SimpleNamespace(metrics={}, params={}), info=SimpleNamespace(run_id=run_id))

    def search_model_versions(self, *args: Any, **kwargs: Any) -> List[Any]:
        return []

    def transition_model_version_stage(self, *args: Any, **kwargs: Any) -> None:
        return None


def apply_mlflow_mocks(monkeypatch: MonkeyPatch) -> None:
    """将 MLflow 相关调用替换为内建桩实现"""

    mock_mlflow = MockMlflow()
    try:
        import mlflow  # type: ignore
    except ImportError:
        mlflow = ModuleType("mlflow")  # type: ignore
        sys.modules["mlflow"] = mlflow

    monkeypatch.setattr(mlflow, "set_tracking_uri", mock_mlflow.set_tracking_uri, raising=False)
    monkeypatch.setattr(mlflow, "get_tracking_uri", mock_mlflow.get_tracking_uri, raising=False)
    monkeypatch.setattr(mlflow, "start_run", mock_mlflow.start_run, raising=False)
    monkeypatch.setattr(mlflow, "log_params", mock_mlflow.log_params, raising=False)
    monkeypatch.setattr(mlflow, "log_metrics", mock_mlflow.log_metrics, raising=False)
    monkeypatch.setattr(mlflow, "log_metric", mock_mlflow.log_metric, raising=False)
    monkeypatch.setattr(mlflow, "set_tags", mock_mlflow.set_tags, raising=False)
    monkeypatch.setattr(mlflow, "get_experiment_by_name", mock_mlflow.get_experiment_by_name, raising=False)
    monkeypatch.setattr(mlflow, "create_experiment", mock_mlflow.create_experiment, raising=False)
    monkeypatch.setattr(mlflow, "set_experiment", mock_mlflow.set_experiment, raising=False)
    monkeypatch.setattr(mlflow, "MlflowClient", MockMlflowClient, raising=False)

    sklearn_module = getattr(mlflow, "sklearn", None)
    if sklearn_module is None:
        sklearn_module = ModuleType("mlflow.sklearn")
        mlflow.sklearn = sklearn_module  # type: ignore[attr-defined]
        sys.modules["mlflow.sklearn"] = sklearn_module
    monkeypatch.setattr(sklearn_module, "log_model", mock_mlflow.sklearn_log_model, raising=False)

    models_module = getattr(mlflow, "models", None)
    if models_module is None:
        models_module = ModuleType("mlflow.models")
        mlflow.models = models_module  # type: ignore[attr-defined]
        sys.modules["mlflow.models"] = models_module
    monkeypatch.setattr(models_module, "infer_signature", lambda *args, **kwargs: {"inputs": [], "outputs": []}, raising=False)


__all__ = [
    "MockMlflow",
    "MockMlflowClient",
    "MockMlflowRun",
    "apply_mlflow_mocks",
]
