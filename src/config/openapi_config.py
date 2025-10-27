"""
OpenAPI 配置和文档增强
"""

from typing import Any, Dict, List

from fastapi import FastAPI


class OpenAPIConfig:
    """OpenAPI 配置管理类"""

    @staticmethod
    def configure_openapi(app: FastAPI) -> None:
        """配置OpenAPI文档"""
        app.title = "足球预测系统 API"
        app.description = "基于机器学习的足球比赛结果预测系统"
        app.version = "2.0.0"

        # 配置OpenAPI信息
        app.openapi_info = {
            "title": "足球预测系统 API",
            "description": "基于机器学习的足球比赛结果预测系统",
            "version": "2.0.0",
            "contact": {
                "name": "API Support",
                "email": "support@example.com"
            }
        }

    @staticmethod
# TODO: 方法 def get_tags_metadata 过长(22行)，建议拆分
    def get_tags_metadata() -> List[Dict[str, Any]]:
        """获取API标签元数据"""
        return [
            {
                "name": "预测",
                "description": "比赛预测相关操作"
            },
            {
                "name": "数据",
                "description": "数据管理相关操作"
            },
            {
                "name": "分析",
                "description": "数据分析相关操作"
            },
            {
                "name": "健康检查",
                "description": "系统健康检查"
            }
        ]

    @staticmethod
    def setup_docs_servers(app: FastAPI) -> None:
        """设置文档服务器信息"""
        app.servers = [
            {"url": "http://localhost:8000", "description": "开发环境"},  # TODO: 将魔法数字 8000 提取为常量
            {"url": "https://api.footballprediction.com", "description": "生产环境"}
        ]


def setup_openapi(app: FastAPI) -> None:
    """设置OpenAPI配置的便捷函数"""
    OpenAPIConfig.configure_openapi(app)
    OpenAPIConfig.setup_docs_servers(app)