"""
MLflow客户端配置
MLflow Client Configuration

配置和提供MLflow客户端实例。
"""

from mlflow import MlflowClient

# MLflow客户端
mlflow_client = MlflowClient(tracking_uri="http://localhost:5002")