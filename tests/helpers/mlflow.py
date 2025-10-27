"""
MLflow测试辅助工具
提供MLflow客户端和运行时Mock实现
"""

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union
from unittest.mock import AsyncMock, Mock


class MockMlflowRun:
    """模拟MLflow运行"""

    def __init__(
        self,
        run_id: str = "test_run_id",
        experiment_id: str = "test_experiment_id",
        status: str = "RUNNING",
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ):
        self.run_id = run_id
        self.experiment_id = experiment_id
        self.status = status
        self.start_time = start_time or datetime.now(timezone.utc)
        self.end_time = end_time
        self.metrics: Dict[str, float] = {}
        self.params: Dict[str, str] = {}
        self.tags: Dict[str, str] = {}
        self.artifacts: List[str] = []

    def log_metric(self, key: str, value: float, step: Optional[int] = None) -> None:
        """记录指标"""
        if step is not None:
            key = f"{key}_step_{step}"
        self.metrics[key] = value

    def log_param(self, key: str, value: str) -> None:
        """记录参数"""
        self.params[key] = value

    def set_tag(self, key: str, value: str) -> None:
        """设置标签"""
        self.tags[key] = value

    def log_artifact(
        self, local_path: str, artifact_path: Optional[str] = None
    ) -> None:
        """记录文件"""
        self.artifacts.append(local_path)

    def get_metrics(self) -> Dict[str, float]:
        """获取所有指标"""
        return self.metrics.copy()

    def get_params(self) -> Dict[str, str]:
        """获取所有参数"""
        return self.params.copy()

    def get_tags(self) -> Dict[str, str]:
        """获取所有标签"""
        return self.tags.copy()


class MockMlflowClient:
    """模拟MLflow客户端"""

    def __init__(self):
        self.experiments: Dict[str, Dict[str, Any]] = {}
        self.runs: Dict[str, MockMlflowRun] = {}
        self.models: Dict[str, Dict[str, Any]] = {}

    def create_experiment(
        self, name: str, tags: Optional[Dict[str, str]] = None
    ) -> str:
        """创建实验"""
        experiment_id = f"exp_{len(self.experiments) + 1}"
        self.experiments[experiment_id] = {
            "id": experiment_id,
            "name": name,
            "tags": tags or {},
            "creation_time": datetime.now(timezone.utc),
        }
        return experiment_id

    def get_experiment_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """根据名称获取实验"""
        for exp in self.experiments.values():
            if exp["name"] == name:
                return exp
        return None

    def create_run(
        self,
        experiment_id: str,
        tags: Optional[Dict[str, str]] = None,
        run_name: Optional[str] = None,
    ) -> MockMlflowRun:
        """创建运行"""
        run_id = f"run_{len(self.runs) + 1}"
        run = MockMlflowRun(run_id=run_id, experiment_id=experiment_id, tags=tags or {})
        if run_name:
            run.set_tag("mlflow.runName", run_name)

        self.runs[run_id] = run
        return run

    def get_run(self, run_id: str) -> Optional[MockMlflowRun]:
        """获取运行"""
        return self.runs.get(run_id)

    def list_run_infos(
        self, experiment_id: str, max_results: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """列出运行信息"""
        run_infos = []
        for run in self.runs.values():
            if run.experiment_id == experiment_id:
                run_infos.append(
                    {
                        "run_id": run.run_id,
                        "experiment_id": run.experiment_id,
                        "status": run.status,
                        "start_time": run.start_time,
                        "end_time": run.end_time,
                    }
                )

        if max_results:
            run_infos = run_infos[:max_results]

        return run_infos

    def log_model(
        self,
        run_id: str,
        model_path: str,
        model: Any,
        registered_model_name: Optional[str] = None,
    ) -> None:
        """记录模型"""
        if run_id not in self.runs:
            return

        model_info = {
            "run_id": run_id,
            "model_path": model_path,
            "model_type": type(model).__name__,
            "registered_name": registered_model_name,
            "creation_time": datetime.now(timezone.utc),
        }

        if registered_model_name:
            self.models[registered_model_name] = model_info

    def get_model_version(self, name: str, version: str) -> Optional[Dict[str, Any]]:
        """获取模型版本"""
        return self.models.get(name)

    def transition_model_version_stage(
        self, name: str, version: str, stage: str
    ) -> None:
        """转换模型版本阶段"""
        if name in self.models:
            self.models[name]["stage"] = stage

    def delete_run(self, run_id: str) -> None:
        """删除运行"""
        self.runs.pop(run_id, None)

    def search_runs(
        self,
        experiment_ids: Optional[List[str]] = None,
        filter_string: str = "",
        max_results: Optional[int] = None,
    ) -> List[MockMlflowRun]:
        """搜索运行"""
        runs = list(self.runs.values())

        if experiment_ids:
            runs = [run for run in runs if run.experiment_id in experiment_ids]

        # 简单的过滤实现
        if filter_string:
            # 可以根据需要实现更复杂的过滤逻辑
            pass

        if max_results:
            runs = runs[:max_results]

        return runs


class MockMlflow:
    """模拟MLflow模块"""

    def __init__(self):
        self.client = MockMlflowClient()
        self.active_run: Optional[MockMlflowRun] = None

    def start_run(
        self,
        run_id: Optional[str] = None,
        experiment_id: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
        run_name: Optional[str] = None,
    ) -> MockMlflowRun:
        """开始运行"""
        if run_id and run_id in self.client.runs:
            self.active_run = self.client.runs[run_id]
        else:
            self.active_run = self.client.create_run(
                experiment_id or "default", tags=tags, run_name=run_name
            )
        return self.active_run

    def end_run(self) -> None:
        """结束运行"""
        if self.active_run:
            self.active_run.status = "FINISHED"
            self.active_run.end_time = datetime.now(timezone.utc)
        self.active_run = None

    def log_metric(self, key: str, value: float, step: Optional[int] = None) -> None:
        """记录指标"""
        if self.active_run:
            self.active_run.log_metric(key, value, step)

    def log_param(self, key: str, value: str) -> None:
        """记录参数"""
        if self.active_run:
            self.active_run.log_param(key, value)

    def set_tag(self, key: str, value: str) -> None:
        """设置标签"""
        if self.active_run:
            self.active_run.set_tag(key, value)

    def log_artifact(
        self, local_path: str, artifact_path: Optional[str] = None
    ) -> None:
        """记录文件"""
        if self.active_run:
            self.active_run.log_artifact(local_path, artifact_path)

    def get_active_run(self) -> Optional[MockMlflowRun]:
        """获取当前活动运行"""
        return self.active_run

    def log_model(
        self, model_path: str, model: Any, registered_model_name: Optional[str] = None
    ) -> None:
        """记录模型"""
        if self.active_run:
            self.client.log_model(
                self.active_run.run_id, model_path, model, registered_model_name
            )

    def create_experiment(
        self, name: str, tags: Optional[Dict[str, str]] = None
    ) -> str:
        """创建实验"""
        return self.client.create_experiment(name, tags)

    def get_experiment_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """根据名称获取实验"""
        return self.client.get_experiment_by_name(name)

    def set_experiment(self, experiment_id: str) -> None:
        """设置活动实验"""
        # 在mock中简化实现
        pass

    def tracking_uri(self) -> str:
        """获取跟踪URI"""
        return "http://mock-mlflow:5000"


def apply_mlflow_mocks():
    """应用MLflow mock装饰器"""

    def decorator(func):
        def wrapper(*args, **kwargs):
            mock_mlflow = MockMlflow()
            return func(mock_mlflow, *args, **kwargs)

        return wrapper

    return decorator


# 全局mock实例
mock_mlflow = MockMlflow()
mock_mlflow_client = MockMlflowClient()
