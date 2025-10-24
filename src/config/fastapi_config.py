"""
FastAPI 中文配置
"""

from fastapi import FastAPI

from src.utils.i18n import init_i18n, I18nUtils


def create_chinese_app() -> FastAPI:
    """创建中文界面的 FastAPI 应用"""

    # 初始化中文
    init_i18n()

    app = FastAPI(
        title=I18nUtils.translate("Football Prediction API"),
        description=I18nUtils.translate("Machine Learning Based Football Match Prediction System"),
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # 保存原始的openapi方法
    original_openapi = app.openapi

    # 自定义文档
    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema

        openapi_schema = original_openapi()

        # 修改信息为中文
        openapi_schema["info"]["title"] = I18nUtils.translate("Football Prediction API")
        openapi_schema["info"]["description"] = I18nUtils.translate(
            "Machine Learning Based Football Match Prediction System"
        )

        # 添加中文标签
        openapi_schema["tags"] = [
            {"name": "基础", "description": "基础接口"},
            {"name": "预测", "description": "预测相关接口"},
            {"name": "数据", "description": "数据管理接口"},
            {"name": "监控", "description": "系统监控接口"},
        ]

        app.openapi_schema = openapi_schema
        return app.openapi_schema

    app.openapi = custom_openapi

    return app
