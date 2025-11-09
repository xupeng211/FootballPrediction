from fastapi import FastAPI

from src.utils.i18n import I18nUtils, init_i18n

"""


"""

# TODO: 方法 def custom_openapi 过长(29行),建议拆分
# TODO: 方法 def create_chinese_app 过长(21行),建议拆分
# TODO: 方法 def custom_openapi 过长(29行),建议拆分
# TODO: 方法 def custom_openapi 过长(29行),建议拆分
# TODO: 方法 def create_chinese_app 过长(21行),建议拆分
# TODO: 方法 def create_chinese_app 过长(22行),建议拆分
# TODO: 方法 def custom_openapi 过长(29行),建议拆分
# TODO: 方法 def create_chinese_app 过长(23行),建议拆分
# TODO: 方法 def create_chinese_app 过长(24行),建议拆分
# TODO: 方法 def custom_openapi 过长(29行),建议拆分
# TODO: 方法 def create_chinese_app 过长(25行),建议拆分
# TODO: 方法 def custom_openapi 过长(29行),建议拆分
# TODO: 方法 def custom_openapi 过长(29行),建议拆分
# TODO: 方法 def create_chinese_app 过长(25行),建议拆分
# TODO: 方法 def create_chinese_app 过长(24行),建议拆分
# TODO: 方法 def custom_openapi 过长(29行),建议拆分
# TODO: 方法 def create_chinese_app 过长(25行),建议拆分
# TODO: 方法 def custom_openapi 过长(29行),建议拆分
# TODO: 方法 def custom_openapi 过长(29行),建议拆分
# TODO: 方法 def create_chinese_app 过长(25行),建议拆分
# TODO: 方法 def custom_openapi 过长(29行),建议拆分
# TODO: 方法 def custom_openapi 过长(29行),建议拆分
# TODO: 方法 def create_chinese_app 过长(25行),建议拆分
# TODO: 方法 def custom_openapi 过长(29行),建议拆分
# TODO: 方法 def custom_openapi 过长(29行),建议拆分
# TODO: 方法 def create_chinese_app 过长(25行),建议拆分
# TODO: 方法 def custom_openapi 过长(29行),建议拆分
# TODO: 方法 def custom_openapi 过长(29行),建议拆分
# TODO: 方法 def create_chinese_app 过长(25行),建议拆分
# TODO: 方法 def custom_openapi 过长(29行),建议拆分
# TODO: 方法 def custom_openapi 过长(29行),建议拆分
# TODO: 方法 def create_chinese_app 过长(25行),建议拆分
# TODO: 方法 def create_chinese_app 过长(28行),建议拆分
# TODO: 方法 def custom_openapi 过长(29行),建议拆分
# TODO: 方法 def create_chinese_app 过长(29行),建议拆分
# TODO: 方法 def custom_openapi 过长(29行),建议拆分
# TODO: 方法 def custom_openapi 过长(29行),建议拆分
# TODO: 方法 def create_chinese_app 过长(29行),建议拆分
# TODO: 方法 def custom_openapi 过长(29行),建议拆分
# TODO: 方法 def custom_openapi 过长(29行),建议拆分
# TODO: 方法 def create_chinese_app 过长(29行),建议拆分
# TODO: 方法 def custom_openapi 过长(29行),建议拆分
# TODO: 方法 def custom_openapi 过长(29行),建议拆分
# TODO: 方法 def create_chinese_app 过长(29行),建议拆分
# TODO: 方法 def create_chinese_app 过长(30行),建议拆分
# TODO: 方法 def custom_openapi 过长(29行),建议拆分
# TODO: 方法 def create_chinese_app 过长(31行),建议拆分
# TODO: 方法 def custom_openapi 过长(29行),建议拆分
# TODO: 方法 def custom_openapi 过长(29行),建议拆分
# TODO: 方法 def create_chinese_app 过长(31行),建议拆分
# TODO: 方法 def custom_openapi 过长(29行),建议拆分
# TODO: 方法 def custom_openapi 过长(29行),建议拆分
# TODO: 方法 def create_chinese_app 过长(31行),建议拆分
# TODO: 方法 def create_chinese_app 过长(32行),建议拆分
# TODO: 方法 def create_chinese_app 过长(33行),建议拆分
# TODO: 方法 def custom_openapi 过长(29行),建议拆分
# TODO: 方法 def create_chinese_app 过长(34行),建议拆分
# TODO: 方法 def custom_openapi 过长(29行),建议拆分
# TODO: 方法 def custom_openapi 过长(29行),建议拆分
# TODO: 方法 def create_chinese_app 过长(34行),建议拆分
# TODO: 方法 def custom_openapi 过长(29行),建议拆分
# TODO: 方法 def custom_openapi 过长(29行),建议拆分
# TODO: 方法 def create_chinese_app 过长(34行),建议拆分
# TODO: 方法 def custom_openapi 过长(29行),建议拆分
# TODO: 方法 def custom_openapi 过长(29行),建议拆分
# TODO: 方法 def create_chinese_app 过长(34行),建议拆分
# TODO: 方法 def custom_openapi 过长(29行),建议拆分
# TODO: 方法 def custom_openapi 过长(29行),建议拆分
# TODO: 方法 def create_chinese_app 过长(34行),建议拆分
# TODO: 方法 def custom_openapi 过长(29行),建议拆分
# TODO: 方法 def custom_openapi 过长(29行),建议拆分
# TODO: 方法 def create_chinese_app 过长(34行),建议拆分
# TODO: 方法 def custom_openapi 过长(29行),建议拆分
# TODO: 方法 def custom_openapi 过长(29行),建议拆分
# TODO: 方法 def create_chinese_app 过长(34行),建议拆分
# TODO: 方法 def custom_openapi 过长(29行),建议拆分
# TODO: 方法 def custom_openapi 过长(29行),建议拆分
# TODO: 方法 def create_chinese_app 过长(34行),建议拆分
# TODO: 方法 def custom_openapi 过长(29行),建议拆分
# TODO: 方法 def custom_openapi 过长(29行),建议拆分
# TODO: 方法 def create_chinese_app 过长(34行),建议拆分
# TODO: 方法 def custom_openapi 过长(29行),建议拆分
# TODO: 方法 def custom_openapi 过长(29行),建议拆分
# TODO: 方法 def create_chinese_app 过长(34行),建议拆分
# TODO: 方法 def custom_openapi 过长(29行),建议拆分
# TODO: 方法 def custom_openapi 过长(29行),建议拆分
# TODO: 方法 def create_chinese_app 过长(34行),建议拆分
# TODO: 方法 def custom_openapi 过长(29行),建议拆分
# TODO: 方法 def custom_openapi 过长(29行),建议拆分
# TODO: 方法 def create_chinese_app 过长(34行),建议拆分
# TODO: 方法 def custom_openapi 过长(29行),建议拆分
# TODO: 方法 def custom_openapi 过长(29行),建议拆分
# TODO: 方法 def create_chinese_app 过长(34行),建议拆分
# TODO: 方法 def custom_openapi 过长(29行),建议拆分
# TODO: 方法 def custom_openapi 过长(29行),建议拆分
# TODO: 方法 def create_chinese_app 过长(34行),建议拆分
# TODO: 方法 def custom_openapi 过长(29行),建议拆分
# TODO: 方法 def custom_openapi 过长(29行),建议拆分
# TODO: 方法 def create_chinese_app 过长(34行),建议拆分
# TODO: 方法 def create_chinese_app 过长(35行),建议拆分
# TODO: 方法 def custom_openapi 过长(29行),建议拆分
# TODO: 方法 def create_chinese_app 过长(36行),建议拆分
# TODO: 方法 def custom_openapi 过长(29行),建议拆分
# TODO: 方法 def custom_openapi 过长(29行),建议拆分
# TODO: 方法 def create_chinese_app 过长(36行),建议拆分
# TODO: 方法 def custom_openapi 过长(29行),建议拆分
# TODO: 方法 def custom_openapi 过长(29行),建议拆分
# TODO: 方法 def create_chinese_app 过长(36行),建议拆分
# TODO: 方法 def custom_openapi 过长(29行),建议拆分
# TODO: 方法 def custom_openapi 过长(29行),建议拆分
# TODO: 方法 def create_chinese_app 过长(36行),建议拆分
# TODO: 方法 def custom_openapi 过长(29行),建议拆分
# TODO: 方法 def custom_openapi 过长(29行),建议拆分
# TODO: 方法 def create_chinese_app 过长(36行),建议拆分
# TODO: 方法 def custom_openapi 过长(29行),建议拆分
# TODO: 方法 def custom_openapi 过长(29行),建议拆分
# TODO: 方法 def create_chinese_app 过长(36行),建议拆分
# TODO: 方法 def custom_openapi 过长(29行),建议拆分
# TODO: 方法 def custom_openapi 过长(29行),建议拆分
# TODO: 方法 def create_chinese_app 过长(36行),建议拆分
# TODO: 方法 def custom_openapi 过长(29行),建议拆分
# TODO: 方法 def custom_openapi 过长(29行),建议拆分
# TODO: 方法 def create_chinese_app 过长(36行),建议拆分
# TODO: 方法 def custom_openapi 过长(29行),建议拆分
# TODO: 方法 def custom_openapi 过长(29行),建议拆分
# TODO: 方法 def create_chinese_app 过长(36行),建议拆分
    """创建中文界面的 FastAPI 应用"""

    # 初始化中文

    # 保存原始的openapi方法

    # 自定义文档
    # TODO: 方法 def custom_openapi 过长(29行),建议拆分
    # TODO: 方法 def custom_openapi 过长(29行),建议拆分
    # TODO: 方法 def custom_openapi 过长(29行),建议拆分
    # TODO: 方法 def custom_openapi 过长(29行),建议拆分
    # TODO: 方法 def custom_openapi 过长(29行),建议拆分
    # TODO: 方法 def custom_openapi 过长(29行),建议拆分
    # TODO: 方法 def custom_openapi 过长(29行),建议拆分
    # TODO: 方法 def custom_openapi 过长(29行),建议拆分
    # TODO: 方法 def custom_openapi 过长(29行),建议拆分
    # TODO: 方法 def custom_openapi 过长(29行),建议拆分
    # TODO: 方法 def custom_openapi 过长(29行),建议拆分
    # TODO: 方法 def custom_openapi 过长(29行),建议拆分
    # TODO: 方法 def custom_openapi 过长(29行),建议拆分
    # TODO: 方法 def custom_openapi 过长(29行),建议拆分
    # TODO: 方法 def custom_openapi 过长(29行),建议拆分
    # TODO: 方法 def custom_openapi 过长(29行),建议拆分
    # TODO: 方法 def custom_openapi 过长(29行),建议拆分
        """TODO: 添加函数文档"""

        # 修改信息为中文

        # 添加中文标签

    # 使用setattr来设置openapi方法

FastAPI 中文配置
def create_chinese_app() -> FastAPI:
    init_i18n()
    app = FastAPI(
        title=I18nUtils.translate("Football Prediction API"),
        description=I18nUtils.translate(
            "Machine Learning Based Football Match Prediction System"
        ),
        version="1.0.0",
        DOCS_URL ="/docs",
        REDOC_URL ="/redoc",
    )
    ORIGINAL_OPENAPI = app.openapi
def custom_openapi():  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解
        if app.openapi_schema:
            return app.openapi_schema
        OPENAPI_SCHEMA = original_openapi()
        OPENAPI_SCHEMA["INFO"]["TITLE"] = I18nUtils.translate("Football Prediction API")
        OPENAPI_SCHEMA["INFO"]["DESCRIPTION"] = I18nUtils.translate(
            "Machine Learning Based Football Match Prediction System"
        )
        OPENAPI_SCHEMA["TAGS"] = [
            {"name": "基础", "description": "基础接口"},
            {"name": "预测", "description": "预测相关接口"},
            {"name": "数据", "description": "数据管理接口"},
            {"name": "监控", "description": "系统监控接口"},
        ]
        APP.OPENAPI_SCHEMA = openapi_schema
        return app.openapi_schema
    app.openapi = custom_openapi
    return app
