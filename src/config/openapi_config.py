from typing import Any, Dict, List, Optional, Union
"""
OpenAPI 配置和文档增强
"""

from fastapi import FastAPI


class OpenAPIConfig:
    """OpenAPI 配置管理类"""

    @staticmethod
    def get_app_info() -> Dict[str, Any]:
        """获取应用基本信息"""
        return {
            "title": "Football Prediction API",
            "description": """
## 基于机器学习的足球比赛结果预测系统

本系统提供以下功能：

### 🔮 比赛预测
- 基于机器学习模型预测比赛结果
- 支持实时预测和批量预测
- 提供预测置信度和概率分布

### 📊 数据分析
- 球队近期表现分析
- 历史对战记录查询
- 联赛排名和积分统计

### 📈 实时数据
- 实时比分更新
- 比赛事件追踪（进球、红黄牌等）
- 赔率变化监控

### 🎯 特征工程
- 自动计算预测特征
- 特征存储和管理
- 支持自定义特征

### 📋 模型管理
- MLflow 集成
- 模型版本控制
- A/B 测试支持

## 使用指南

### 1. 快速开始
```bash
# 健康检查
curl http://localhost:8000/health

# 获取预测
curl http://localhost:8000/predictions/{match_id}

# 查看文档
# 访问 http://localhost:8000/docs
```

### 2. 认证说明
- 当前版本无需认证
- 生产环境建议配置 API Key
- 使用 Bearer Token 或 API Key Header

### 3. 限流规则
- 每分钟最多 100 请求
- 超出限制返回 429 状态码
- 建议合理使用缓存

### 4. 错误处理
- 所有错误返回 JSON 格式
- 包含错误码和详细描述
- 参考 /health 端点了解系统状态

## 数据模型

### 比赛 (Match)
```json
{
  "id": "match_123",
  "home_team": "Team A",
  "away_team": "Team B",
  "league": "Premier League",
  "start_time": "2024-01-01T20:00:00Z",
  "status": "scheduled"
}
```

### 预测 (Prediction)
```json
{
  "match_id": "match_123",
  "prediction": "home_win",
  "confidence": 0.75,
  "probabilities": {
    "home_win": 0.75,
    "draw": 0.15,
    "away_win": 0.10
  },
  "model_version": "v2.1.0"
}
```
            """,
            "version": "1.0.0",
            "terms_of_service": "https://football-prediction.com/terms/",
            "contact": {
                "name": "Football Prediction Team",
                "url": "https://github.com/xupeng211/FootballPrediction",
                "email": "support@football-prediction.com",
            },
            "license_info": {
                "name": "MIT License",
                "url": "https://opensource.org/licenses/MIT",
            },
        }

    @staticmethod
    def get_servers() -> List[Dict[str, str]:
        """获取服务器配置"""
        return [
            {"url": "http://localhost:8000", "description": "开发环境 - 本地开发"},
            {
                "url": "https://staging-api.football-prediction.com",
                "description": "测试环境 - 功能验证",
            },
            {
                "url": "https://api.football-prediction.com",
                "description": "生产环境 - 正式服务",
            },
        ]

    @staticmethod
    def get_tags() -> List[Dict[str, str]:
        """获取API标签定义"""
        return [
            {
                "name": "健康检查",
                "description": "系统健康状态检查相关接口",
                "externalDocs": {  # type: ignore
                    "description": "健康检查详细说明",
                    "url": "https://football-prediction.com/docs/health-check",
                },
            },
            {
                "name": "预测",
                "description": "比赛预测相关接口",
                "externalDocs": {  # type: ignore
                    "description": "预测模型说明",
                    "url": "https://football-prediction.com/docs/prediction-models",
                },
            },
            {
                "name": "数据",
                "description": "数据管理和查询接口",
                "externalDocs": {  # type: ignore
                    "description": "数据源说明",
                    "url": "https://football-prediction.com/docs/data-sources",
                },
            },
            {
                "name": "特征",
                "description": "特征工程相关接口",
                "externalDocs": {  # type: ignore
                    "description": "特征工程文档",
                    "url": "https://football-prediction.com/docs/feature-engineering",
                },
            },
            {
                "name": "模型",
                "description": "ML模型管理接口",
                "externalDocs": {  # type: ignore
                    "description": "MLOps 流程说明",
                    "url": "https://football-prediction.com/docs/mlops",
                },
            },
            {
                "name": "监控",
                "description": "系统监控和指标接口",
                "externalDocs": {  # type: ignore
                    "description": "监控配置指南",
                    "url": "https://football-prediction.com/docs/monitoring",
                },
            },
        ]

    @staticmethod
    def get_security_schemes() -> Dict[str, Any]:
        """获取安全配置"""
        return {
            "ApiKeyAuth": {
                "type": "apiKey",
                "in": "header",
                "name": "X-API-Key",
                "description": "API密钥认证，请在请求头中携带 X-API-Key",
            },
            "BearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
                "description": "JWT Token 认证，格式：Bearer <token>",
            },
        }

    @staticmethod
    def configure_openapi(app: FastAPI) -> None:
        """配置 FastAPI 应用的 OpenAPI"""
        # 获取配置
        info = OpenAPIConfig.get_app_info()
        servers = OpenAPIConfig.get_servers()
        tags = OpenAPIConfig.get_tags()
        security_schemes = OpenAPIConfig.get_security_schemes()

        # 自定义 OpenAPI
        def custom_openapi():
            if app.openapi_schema:
                return app.openapi_schema

            # 先获取基础 schema
            from fastapi.openapi.utils import get_openapi

            openapi_schema = get_openapi(
                title=info["title"],
                version=info["version"],
                description=info["description"],
                routes=app.routes,
                servers=servers,
                tags=tags,
            )

            # 添加 logo
            openapi_schema["info"]["x-logo"] = {
                "url": "https://fastapi.tiangolo.com/img/logo-margin/logo-teal.png"
            }

            # 更新联系人和许可证信息
            openapi_schema["info"]["contact"] = info["contact"]
            openapi_schema["info"]["license"] = info["license_info"]
            openapi_schema["info"]["termsOfService"] = info["terms_of_service"]

            # 添加示例
            if "components" not in openapi_schema:
                openapi_schema["components"] = {}
            openapi_schema["components"]["examples"] = {
                # 预测相关示例
                "PredictionExample": {
                    "summary": "比赛预测响应",
                    "description": "单场比赛预测结果",
                    "value": {
                        "match_id": "match_123",
                        "home_team": "Manchester United",
                        "away_team": "Liverpool",
                        "league": "Premier League",
                        "prediction": "home_win",
                        "confidence": 0.65,
                        "probabilities": {
                            "home_win": 0.65,
                            "draw": 0.25,
                            "away_win": 0.10,
                        },
                        "features_used": [
                            "team_form",
                            "head_to_head",
                            "home_advantage",
                            "player_stats",
                            "recent_performance",
                        ],
                        "model_version": "v2.1.0",
                        "predicted_at": "2024-01-01T10:00:00Z",
                        "odds": {"home_win": 2.10, "draw": 3.40, "away_win": 3.20},
                    },
                },
                "BatchPredictionRequest": {
                    "summary": "批量预测请求",
                    "description": "多场比赛批量预测请求",
                    "value": {
                        "match_ids": ["match_123", "match_124", "match_125"],
                        "model_version": "latest",
                        "include_features": True,
                        "force_recalculate": False,
                    },
                },
                "BatchPredictionResponse": {
                    "summary": "批量预测响应",
                    "description": "批量预测结果",
                    "value": {
                        "predictions": [
                            {
                                "match_id": "match_123",
                                "prediction": "home_win",
                                "confidence": 0.65,
                                "predicted_at": "2024-01-01T10:00:00Z",
                            },
                            {
                                "match_id": "match_124",
                                "prediction": "draw",
                                "confidence": 0.45,
                                "predicted_at": "2024-01-01T10:01:00Z",
                            },
                            {
                                "match_id": "match_125",
                                "prediction": "away_win",
                                "confidence": 0.72,
                                "predicted_at": "2024-01-01T10:02:00Z",
                            },
                        ],
                        "total_count": 3,
                        "processing_time_ms": 450.5,
                    },
                },
                # 健康检查示例
                "HealthCheckExample": {
                    "summary": "系统健康检查",
                    "description": "完整的系统健康状态",
                    "value": {
                        "status": "healthy",
                        "timestamp": "2024-01-01T10:00:00Z",
                        "version": "1.0.0",
                        "uptime": 3600.0,
                        "response_time_ms": 45.2,
                        "checks": {
                            "database": {
                                "status": "healthy",
                                "response_time_ms": 15.5,
                                "details": {
                                    "connection_pool": "8/20",
                                    "active_connections": 5,
                                    "total_connections": 150,
                                },
                            },
                            "redis": {
                                "status": "healthy",
                                "response_time_ms": 2.3,
                                "details": {
                                    "memory_usage": "45%",
                                    "connected_clients": 3,
                                    "hit_rate": 0.89,
                                },
                            },
                            "ml_model": {
                                "status": "healthy",
                                "response_time_ms": 125.0,
                                "details": {
                                    "model_version": "v2.1.0",
                                    "last_prediction": "2024-01-01T09:45:00Z",
                                    "model_load_time_ms": 45.2,
                                },
                            },
                            "external_apis": {
                                "status": "healthy",
                                "response_time_ms": 234.5,
                                "details": {"football_api": "OK", "odds_api": "OK"},
                            },
                        },
                    },
                },
                # 特征数据示例
                "MatchFeaturesExample": {
                    "summary": "比赛特征数据",
                    "description": "用于预测的完整特征集",
                    "value": {
                        "match_id": "match_123",
                        "home_team": "Manchester United",
                        "away_team": "Liverpool",
                        "features": {
                            "home_team_form": {
                                "last_5_games": 4,
                                "goals_scored": 10,
                                "goals_conceded": 3,
                                "possession_avg": 58.5,
                            },
                            "away_team_form": {
                                "last_5_games": 3,
                                "goals_scored": 8,
                                "goals_conceded": 5,
                                "possession_avg": 52.3,
                            },
                            "head_to_head": {
                                "last_10_meetings": {
                                    "home_wins": 6,
                                    "away_wins": 3,
                                    "draws": 1,
                                },
                                "avg_goals": 2.8,
                            },
                            "context": {
                                "home_advantage": 0.15,
                                "days_since_last_match_home": 3,
                                "days_since_last_match_away": 4,
                                "travel_distance_km": 35,
                            },
                        },
                        "computed_at": "2024-01-01T09:30:00Z",
                    },
                },
                # 模型信息示例
                "ModelInfoExample": {
                    "summary": "模型信息",
                    "description": "当前活跃模型详细信息",
                    "value": {
                        "name": "football_baseline_model",
                        "version": "v2.1.0",
                        "type": "gradient_boosting",
                        "status": "active",
                        "created_at": "2024-01-01T00:00:00Z",
                        "performance_metrics": {
                            "accuracy": 0.68,
                            "precision": 0.66,
                            "recall": 0.64,
                            "f1_score": 0.65,
                            "auc_roc": 0.72,
                        },
                        "training_data": {
                            "matches_count": 15000,
                            "features_count": 45,
                            "training_time_hours": 2.5,
                        },
                        "feature_importance": {
                            "team_form": 0.23,
                            "head_to_head": 0.19,
                            "home_advantage": 0.15,
                            "player_stats": 0.12,
                            "recent_goals": 0.10,
                        },
                    },
                },
                # 错误响应示例
                "ErrorResponseExample": {
                    "summary": "错误响应",
                    "description": "API 错误响应格式",
                    "value": {
                        "error": True,
                        "status_code": 400,
                        "message": "Invalid match_id format",
                        "details": {
                            "field": "match_id",
                            "provided_value": "invalid",
                            "expected_format": "string starting with 'match_'",
                        },
                        "timestamp": "2024-01-01T10:00:00Z",
                        "path": "/predictions/match/invalid",
                    },
                },
            }

            # 添加请求/响应模型
            if "schemas" not in openapi_schema["components"]:
                openapi_schema["components"]["schemas"] = {}

            openapi_schema["components"]["schemas"].update(
                {
                    "PredictionRequest": {
                        "type": "object",
                        "required": ["match_id"],
                        "properties": {
                            "match_id": {
                                "type": "string",
                                "description": "比赛唯一标识符",
                                "pattern": "^match_\\d+$",
                                "example": "match_123456",
                            },
                            "model_version": {
                                "type": "string",
                                "description": "指定模型版本，默认使用最新版本",
                                "example": "v2.1.0",
                            },
                            "force_recalculate": {
                                "type": "boolean",
                                "description": "是否强制重新计算特征",
                                "default": False,
                            },
                        },
                    },
                    "PredictionResponse": {
                        "type": "object",
                        "properties": {
                            "match_id": {"type": "string"},
                            "home_team": {"type": "string"},
                            "away_team": {"type": "string"},
                            "prediction": {
                                "type": "string",
                                "enum": ["home_win", "draw", "away_win"],
                            },
                            "confidence": {
                                "type": "number",
                                "minimum": 0,
                                "maximum": 1,
                            },
                            "probabilities": {
                                "type": "object",
                                "properties": {
                                    "home_win": {"type": "number"},
                                    "draw": {"type": "number"},
                                    "away_win": {"type": "number"},
                                },
                            },
                            "model_version": {"type": "string"},
                            "predicted_at": {"type": "string", "format": "date-time"},
                        },
                    },
                    "ErrorResponse": {
                        "type": "object",
                        "properties": {
                            "error": {"type": "boolean"},
                            "status_code": {"type": "integer"},
                            "message": {"type": "string"},
                            "details": {"type": "object"},
                            "timestamp": {"type": "string", "format": "date-time"},
                            "path": {"type": "string"},
                        },
                    },
                }
            )

            # 添加安全配置
            openapi_schema["components"]["securitySchemes"] = security_schemes

            # 添加认证流程说明
            openapi_schema["components"]["authenticationFlows"] = {
                "ApiKeyAuth": {
                    "type": "apiKey",
                    "description": "API Key 认证流程：\n1. 联系管理员获取 API Key\n2. 在请求头中添加 X-API-Key: your-api-key\n3. 正常调用 API",
                    "example": "curl -H 'X-API-Key: your-api-key' https://api.football-prediction.com/predictions/match_123",
                },
                "BearerAuth": {
                    "type": "http",
                    "scheme": "bearer",
                    "bearerFormat": "JWT",
                    "description": "JWT Bearer Token 认证流程：\n1. 使用用户名密码登录获取 JWT\n2. 在请求头中添加 Authorization: Bearer <jwt-token>\n3. Token 有效期为 24 小时",
                    "example": "curl -H 'Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...' https://api.football-prediction.com/predictions/match_123",
                },
            }

            # 添加扩展信息
            openapi_schema["x-tag-groups"] = [
                {"name": "核心业务", "tags": ["预测", "数据", "特征"]},
                {"name": "系统管理", "tags": ["健康检查", "监控", "模型"]},
            ]

            app.openapi_schema = openapi_schema
            return openapi_schema

        app.openapi = custom_openapi  # type: ignore


# 导出配置函数
def setup_openapi(app: FastAPI) -> None:
    """设置 OpenAPI 配置的便捷函数"""
    OpenAPIConfig.configure_openapi(app)
