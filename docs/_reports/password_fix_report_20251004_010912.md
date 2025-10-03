# 密码安全修复报告

**修复时间**: 2025-10-04 01:09:12
**修复工具**: scripts/security/password_fixer.py

## 修复统计

- 修复文件数: 391
- 修复密码数: 3940
- 生成环境变量: 3691

## 修复详情

### config/monitoring/mutmut_config.py

- 行 39: `TEST_RUNNER = "python -m pytest tests/unit/ -x -q --tb=short"`
  → `TEST_RUNNER = os.getenv("MUTMUT_CONFIG_TEST_RUNNER_39")`
  → 环境变量: `MUTMUT_CONFIG_TEST_RUNNER_39`

### src/__init__.py

- 行 9: `__author__ = "FootballPrediction Team"`
  → `__author__ = os.getenv("__INIT_____AUTHOR___9")`
  → 环境变量: `__INIT_____AUTHOR___9`

- 行 9: `__email__ = "football@prediction.com"`
  → `__email__ = os.getenv("__INIT_____EMAIL___9")`
  → 环境变量: `__INIT_____EMAIL___9`

### src/main.py

- 行 40: `format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"`
  → `format = os.getenv("MAIN_FORMAT_40")`
  → 环境变量: `MAIN_FORMAT_40`

- 行 144: `title="足球预测API"`
  → `title = os.getenv("MAIN_TITLE_144")`
  → 环境变量: `MAIN_TITLE_144`

- 行 144: `description="基于机器学习的足球比赛结果预测系统"`
  → `description = os.getenv("MAIN_DESCRIPTION_144")`
  → 环境变量: `MAIN_DESCRIPTION_144`

### src/config/env_validator.py

- 行 23: `WARNING = "warning"`
  → `WARNING = os.getenv("ENV_VALIDATOR_WARNING_23")`
  → 环境变量: `ENV_VALIDATOR_WARNING_23`

- 行 23: `CRITICAL = "critical"`
  → `CRITICAL = os.getenv("ENV_VALIDATOR_CRITICAL_23")`
  → 环境变量: `ENV_VALIDATOR_CRITICAL_23`

- 行 52: `str = "General"`
  → `str = os.getenv("ENV_VALIDATOR_STR_52")`
  → 环境变量: `ENV_VALIDATOR_STR_52`

- 行 67: `name="ENVIRONMENT"`
  → `name = os.getenv("ENV_VALIDATOR_NAME_67")`
  → 环境变量: `ENV_VALIDATOR_NAME_67`

- 行 70: `default="development"`
  → `default = os.getenv("ENV_VALIDATOR_DEFAULT_70")`
  → 环境变量: `ENV_VALIDATOR_DEFAULT_70`

- 行 75: `name="DATABASE_URL"`
  → `name = os.getenv("ENV_VALIDATOR_NAME_75")`
  → 环境变量: `ENV_VALIDATOR_NAME_75`

- 行 80: `description="数据库连接URL"`
  → `description = os.getenv("ENV_VALIDATOR_DESCRIPTION_80")`
  → 环境变量: `ENV_VALIDATOR_DESCRIPTION_80`

- 行 84: `name="DB_POOL_SIZE"`
  → `name = os.getenv("ENV_VALIDATOR_NAME_84")`
  → 环境变量: `ENV_VALIDATOR_NAME_84`

- 行 90: `description="数据库连接池大小"`
  → `description = os.getenv("ENV_VALIDATOR_DESCRIPTION_90")`
  → 环境变量: `ENV_VALIDATOR_DESCRIPTION_90`

- 行 94: `name="DB_MAX_OVERFLOW"`
  → `name = os.getenv("ENV_VALIDATOR_NAME_94")`
  → 环境变量: `ENV_VALIDATOR_NAME_94`

- 行 98: `description="连接池最大溢出数"`
  → `description = os.getenv("ENV_VALIDATOR_DESCRIPTION_98")`
  → 环境变量: `ENV_VALIDATOR_DESCRIPTION_98`

- 行 103: `name="REDIS_HOST"`
  → `name = os.getenv("ENV_VALIDATOR_NAME_103")`
  → 环境变量: `ENV_VALIDATOR_NAME_103`

- 行 108: `description="Redis主机地址"`
  → `description = os.getenv("ENV_VALIDATOR_DESCRIPTION_108")`
  → 环境变量: `ENV_VALIDATOR_DESCRIPTION_108`

- 行 113: `name="REDIS_PORT"`
  → `name = os.getenv("ENV_VALIDATOR_NAME_113")`
  → 环境变量: `ENV_VALIDATOR_NAME_113`

- 行 117: `description="Redis端口"`
  → `description = os.getenv("ENV_VALIDATOR_DESCRIPTION_117")`
  → 环境变量: `ENV_VALIDATOR_DESCRIPTION_117`

- 行 120: `name="REDIS_PASSWORD"`
  → `name = os.getenv("ENV_VALIDATOR_NAME_120")`
  → 环境变量: `ENV_VALIDATOR_NAME_120`

- 行 124: `description="Redis密码"`
  → `description = os.getenv("ENV_VALIDATOR_DESCRIPTION_124")`
  → 环境变量: `ENV_VALIDATOR_DESCRIPTION_124`

- 行 129: `name="API_HOST"`
  → `name = os.getenv("ENV_VALIDATOR_NAME_129")`
  → 环境变量: `ENV_VALIDATOR_NAME_129`

- 行 134: `description="API服务器地址"`
  → `description = os.getenv("ENV_VALIDATOR_DESCRIPTION_134")`
  → 环境变量: `ENV_VALIDATOR_DESCRIPTION_134`

- 行 138: `name="API_PORT"`
  → `name = os.getenv("ENV_VALIDATOR_NAME_138")`
  → 环境变量: `ENV_VALIDATOR_NAME_138`

- 行 144: `description="API服务器端口"`
  → `description = os.getenv("ENV_VALIDATOR_DESCRIPTION_144")`
  → 环境变量: `ENV_VALIDATOR_DESCRIPTION_144`

- 行 147: `name="API_LOG_LEVEL"`
  → `name = os.getenv("ENV_VALIDATOR_NAME_147")`
  → 环境变量: `ENV_VALIDATOR_NAME_147`

- 行 157: `name="JWT_SECRET_KEY"`
  → `name = os.getenv("ENV_VALIDATOR_NAME_157")`
  → 环境变量: `ENV_VALIDATOR_NAME_157`

- 行 160: `description="JWT签名密钥"`
  → `description = os.getenv("ENV_VALIDATOR_DESCRIPTION_160")`
  → 环境变量: `ENV_VALIDATOR_DESCRIPTION_160`

- 行 166: `name="SECRET_KEY"`
  → `name = os.getenv("ENV_VALIDATOR_NAME_166")`
  → 环境变量: `ENV_VALIDATOR_NAME_166`

- 行 175: `name="ACCESS_TOKEN_EXPIRE_MINUTES"`
  → `name = os.getenv("ENV_VALIDATOR_NAME_175")`
  → 环境变量: `ENV_VALIDATOR_NAME_175`

- 行 180: `description="访问令牌过期时间（分钟）"`
  → `description = os.getenv("ENV_VALIDATOR_DESCRIPTION_180")`
  → 环境变量: `ENV_VALIDATOR_DESCRIPTION_180`

- 行 183: `name="CACHE_ENABLED"`
  → `name = os.getenv("ENV_VALIDATOR_NAME_183")`
  → 环境变量: `ENV_VALIDATOR_NAME_183`

- 行 187: `description="是否启用缓存"`
  → `description = os.getenv("ENV_VALIDATOR_DESCRIPTION_187")`
  → 环境变量: `ENV_VALIDATOR_DESCRIPTION_187`

- 行 191: `name="CACHE_DEFAULT_TTL"`
  → `name = os.getenv("ENV_VALIDATOR_NAME_191")`
  → 环境变量: `ENV_VALIDATOR_NAME_191`

- 行 197: `description="默认缓存TTL（秒）"`
  → `description = os.getenv("ENV_VALIDATOR_DESCRIPTION_197")`
  → 环境变量: `ENV_VALIDATOR_DESCRIPTION_197`

- 行 201: `name="CORS_ORIGINS"`
  → `name = os.getenv("ENV_VALIDATOR_NAME_201")`
  → 环境变量: `ENV_VALIDATOR_NAME_201`

- 行 207: `description="CORS允许的源"`
  → `description = os.getenv("ENV_VALIDATOR_DESCRIPTION_207")`
  → 环境变量: `ENV_VALIDATOR_DESCRIPTION_207`

- 行 211: `name="METRICS_ENABLED"`
  → `name = os.getenv("ENV_VALIDATOR_NAME_211")`
  → 环境变量: `ENV_VALIDATOR_NAME_211`

- 行 213: `description="是否启用指标收集"`
  → `description = os.getenv("ENV_VALIDATOR_DESCRIPTION_213")`
  → 环境变量: `ENV_VALIDATOR_DESCRIPTION_213`

- 行 218: `name="SENTRY_DSN"`
  → `name = os.getenv("ENV_VALIDATOR_NAME_218")`
  → 环境变量: `ENV_VALIDATOR_NAME_218`

- 行 223: `description="Sentry错误追踪DSN"`
  → `description = os.getenv("ENV_VALIDATOR_DESCRIPTION_223")`
  → 环境变量: `ENV_VALIDATOR_DESCRIPTION_223`

- 行 229: `name="PERF_SLOW_QUERY_THRESHOLD"`
  → `name = os.getenv("ENV_VALIDATOR_NAME_229")`
  → 环境变量: `ENV_VALIDATOR_NAME_229`

- 行 234: `description="慢查询阈值（秒）"`
  → `description = os.getenv("ENV_VALIDATOR_DESCRIPTION_234")`
  → 环境变量: `ENV_VALIDATOR_DESCRIPTION_234`

- 行 239: `name="CELERY_BROKER_URL"`
  → `name = os.getenv("ENV_VALIDATOR_NAME_239")`
  → 环境变量: `ENV_VALIDATOR_NAME_239`

- 行 242: `description="Celery代理URL"`
  → `description = os.getenv("ENV_VALIDATOR_DESCRIPTION_242")`
  → 环境变量: `ENV_VALIDATOR_DESCRIPTION_242`

- 行 315: `message="缺少必需的环境变量"`
  → `message = os.getenv("ENV_VALIDATOR_MESSAGE_315")`
  → 环境变量: `ENV_VALIDATOR_MESSAGE_315`

- 行 421: `actual_value="********"`
  → `actual_value = os.getenv("ENV_VALIDATOR_ACTUAL_VALUE_421")`
  → 环境变量: `ENV_VALIDATOR_ACTUAL_VALUE_421`

- 行 438: `var_name="DATABASE_URL"`
  → `var_name = os.getenv("ENV_VALIDATOR_VAR_NAME_438")`
  → 环境变量: `ENV_VALIDATOR_VAR_NAME_438`

- 行 440: `suggestion="使用: postgresql://, sqlite:///"`
  → `suggestion = os.getenv("ENV_VALIDATOR_SUGGESTION_440")`
  → 环境变量: `ENV_VALIDATOR_SUGGESTION_440`

- 行 451: `message="PostgreSQL URL缺少主机或数据库名"`
  → `message = os.getenv("ENV_VALIDATOR_MESSAGE_451")`
  → 环境变量: `ENV_VALIDATOR_MESSAGE_451`

- 行 453: `var_name="DATABASE_URL"`
  → `var_name = os.getenv("ENV_VALIDATOR_VAR_NAME_453")`
  → 环境变量: `ENV_VALIDATOR_VAR_NAME_453`

- 行 458: `message="数据库URL格式正确"`
  → `message = os.getenv("ENV_VALIDATOR_MESSAGE_458")`
  → 环境变量: `ENV_VALIDATOR_MESSAGE_458`

- 行 460: `var_name="DATABASE_URL"`
  → `var_name = os.getenv("ENV_VALIDATOR_VAR_NAME_460")`
  → 环境变量: `ENV_VALIDATOR_VAR_NAME_460`

- 行 467: `var_name="DATABASE_URL"`
  → `var_name = os.getenv("ENV_VALIDATOR_VAR_NAME_467")`
  → 环境变量: `ENV_VALIDATOR_VAR_NAME_467`

- 行 475: `message="主机地址有效"`
  → `message = os.getenv("ENV_VALIDATOR_MESSAGE_475")`
  → 环境变量: `ENV_VALIDATOR_MESSAGE_475`

- 行 475: `var_name="API_HOST"`
  → `var_name = os.getenv("ENV_VALIDATOR_VAR_NAME_475")`
  → 环境变量: `ENV_VALIDATOR_VAR_NAME_475`

- 行 480: `message="主机地址有效"`
  → `message = os.getenv("ENV_VALIDATOR_MESSAGE_480")`
  → 环境变量: `ENV_VALIDATOR_MESSAGE_480`

- 行 481: `var_name="API_HOST"`
  → `var_name = os.getenv("ENV_VALIDATOR_VAR_NAME_481")`
  → 环境变量: `ENV_VALIDATOR_VAR_NAME_481`

- 行 489: `message="主机地址有效"`
  → `message = os.getenv("ENV_VALIDATOR_MESSAGE_489")`
  → 环境变量: `ENV_VALIDATOR_MESSAGE_489`

- 行 492: `var_name="API_HOST"`
  → `var_name = os.getenv("ENV_VALIDATOR_VAR_NAME_492")`
  → 环境变量: `ENV_VALIDATOR_VAR_NAME_492`

- 行 496: `message="主机地址格式可能不正确"`
  → `message = os.getenv("ENV_VALIDATOR_MESSAGE_496")`
  → 环境变量: `ENV_VALIDATOR_MESSAGE_496`

- 行 497: `var_name="API_HOST"`
  → `var_name = os.getenv("ENV_VALIDATOR_VAR_NAME_497")`
  → 环境变量: `ENV_VALIDATOR_VAR_NAME_497`

- 行 498: `suggestion="使用: 0.0.0.0, 127.0.0.1, localhost 或有效域名"`
  → `suggestion = os.getenv("ENV_VALIDATOR_SUGGESTION_498")`
  → 环境变量: `ENV_VALIDATOR_SUGGESTION_498`

- 行 508: `var_name="secret_key"`
  → `var_name = os.getenv("ENV_VALIDATOR_VAR_NAME_508")`
  → 环境变量: `ENV_VALIDATOR_VAR_NAME_508`

- 行 511: `suggestion="使用至少32个字符的强密钥"`
  → `suggestion = os.getenv("ENV_VALIDATOR_SUGGESTION_511")`
  → 环境变量: `ENV_VALIDATOR_SUGGESTION_511`

- 行 522: `message="使用了弱密钥"`
  → `message = os.getenv("ENV_VALIDATOR_MESSAGE_522")`
  → 环境变量: `ENV_VALIDATOR_MESSAGE_522`

- 行 523: `var_name="secret_key"`
  → `var_name = os.getenv("ENV_VALIDATOR_VAR_NAME_523")`
  → 环境变量: `ENV_VALIDATOR_VAR_NAME_523`

- 行 525: `suggestion="请生成强随机密钥"`
  → `suggestion = os.getenv("ENV_VALIDATOR_SUGGESTION_525")`
  → 环境变量: `ENV_VALIDATOR_SUGGESTION_525`

- 行 528: `message="密钥强度良好"`
  → `message = os.getenv("ENV_VALIDATOR_MESSAGE_528")`
  → 环境变量: `ENV_VALIDATOR_MESSAGE_528`

- 行 529: `var_name="secret_key"`
  → `var_name = os.getenv("ENV_VALIDATOR_VAR_NAME_529")`
  → 环境变量: `ENV_VALIDATOR_VAR_NAME_529`

- 行 537: `message="CORS未配置"`
  → `message = os.getenv("ENV_VALIDATOR_MESSAGE_537")`
  → 环境变量: `ENV_VALIDATOR_MESSAGE_537`

- 行 537: `var_name="CORS_ORIGINS"`
  → `var_name = os.getenv("ENV_VALIDATOR_VAR_NAME_537")`
  → 环境变量: `ENV_VALIDATOR_VAR_NAME_537`

- 行 554: `var_name="CORS_ORIGINS"`
  → `var_name = os.getenv("ENV_VALIDATOR_VAR_NAME_554")`
  → 环境变量: `ENV_VALIDATOR_VAR_NAME_554`

- 行 555: `suggestion="使用: https://example.com,https://app.com"`
  → `suggestion = os.getenv("ENV_VALIDATOR_SUGGESTION_555")`
  → 环境变量: `ENV_VALIDATOR_SUGGESTION_555`

- 行 561: `message="CORS配置有效"`
  → `message = os.getenv("ENV_VALIDATOR_MESSAGE_561")`
  → 环境变量: `ENV_VALIDATOR_MESSAGE_561`

- 行 562: `var_name="CORS_ORIGINS"`
  → `var_name = os.getenv("ENV_VALIDATOR_VAR_NAME_562")`
  → 环境变量: `ENV_VALIDATOR_VAR_NAME_562`

- 行 567: `message="Sentry未配置"`
  → `message = os.getenv("ENV_VALIDATOR_MESSAGE_567")`
  → 环境变量: `ENV_VALIDATOR_MESSAGE_567`

- 行 567: `var_name="SENTRY_DSN"`
  → `var_name = os.getenv("ENV_VALIDATOR_VAR_NAME_567")`
  → 环境变量: `ENV_VALIDATOR_VAR_NAME_567`

- 行 574: `message="Sentry DSN必须使用HTTPS"`
  → `message = os.getenv("ENV_VALIDATOR_MESSAGE_574")`
  → 环境变量: `ENV_VALIDATOR_MESSAGE_574`

- 行 575: `var_name="SENTRY_DSN"`
  → `var_name = os.getenv("ENV_VALIDATOR_VAR_NAME_575")`
  → 环境变量: `ENV_VALIDATOR_VAR_NAME_575`

- 行 582: `message="Sentry DSN格式正确"`
  → `message = os.getenv("ENV_VALIDATOR_MESSAGE_582")`
  → 环境变量: `ENV_VALIDATOR_MESSAGE_582`

- 行 583: `var_name="SENTRY_DSN"`
  → `var_name = os.getenv("ENV_VALIDATOR_VAR_NAME_583")`
  → 环境变量: `ENV_VALIDATOR_VAR_NAME_583`

- 行 600: `message="生产环境不应该使用通配符CORS"`
  → `message = os.getenv("ENV_VALIDATOR_MESSAGE_600")`
  → 环境变量: `ENV_VALIDATOR_MESSAGE_600`

- 行 600: `var_name="CORS_ORIGINS"`
  → `var_name = os.getenv("ENV_VALIDATOR_VAR_NAME_600")`
  → 环境变量: `ENV_VALIDATOR_VAR_NAME_600`

- 行 602: `suggestion="请明确指定允许的源"`
  → `suggestion = os.getenv("ENV_VALIDATOR_SUGGESTION_602")`
  → 环境变量: `ENV_VALIDATOR_SUGGESTION_602`

### src/api/health.py

- 行 76: `summary="系统健康检查"`
  → `summary = os.getenv("HEALTH_SUMMARY_76")`
  → 环境变量: `HEALTH_SUMMARY_76`

- 行 76: `description="检查API、数据库、缓存等服务状态"`
  → `description = os.getenv("HEALTH_DESCRIPTION_76")`
  → 环境变量: `HEALTH_DESCRIPTION_76`

- 行 158: `description="简单的存活性检查，仅返回基本状态"`
  → `description = os.getenv("HEALTH_DESCRIPTION_158")`
  → 环境变量: `HEALTH_DESCRIPTION_158`

- 行 170: `description="检查服务是否就绪，包括依赖服务检查"`
  → `description = os.getenv("HEALTH_DESCRIPTION_170")`
  → 环境变量: `HEALTH_DESCRIPTION_170`

### src/api/schemas.py

- 行 16: `description="响应时间(毫秒)"`
  → `description = os.getenv("SCHEMAS_DESCRIPTION_16")`
  → 环境变量: `SCHEMAS_DESCRIPTION_16`

- 行 23: `description="整体健康状态"`
  → `description = os.getenv("SCHEMAS_DESCRIPTION_23")`
  → 环境变量: `SCHEMAS_DESCRIPTION_23`

- 行 23: `description="检查时间(ISO格式)"`
  → `description = os.getenv("SCHEMAS_DESCRIPTION_23")`
  → 环境变量: `SCHEMAS_DESCRIPTION_23`

- 行 26: `description="应用运行时间(秒)"`
  → `description = os.getenv("SCHEMAS_DESCRIPTION_26")`
  → 环境变量: `SCHEMAS_DESCRIPTION_26`

- 行 27: `description="总响应时间(毫秒)"`
  → `description = os.getenv("SCHEMAS_DESCRIPTION_27")`
  → 环境变量: `SCHEMAS_DESCRIPTION_27`

- 行 28: `description="各服务检查结果"`
  → `description = os.getenv("SCHEMAS_DESCRIPTION_28")`
  → 环境变量: `SCHEMAS_DESCRIPTION_28`

- 行 37: `description="响应时间(毫秒)"`
  → `description = os.getenv("SCHEMAS_DESCRIPTION_37")`
  → 环境变量: `SCHEMAS_DESCRIPTION_37`

- 行 41: `description="系统资源指标"`
  → `description = os.getenv("SCHEMAS_DESCRIPTION_41")`
  → 环境变量: `SCHEMAS_DESCRIPTION_41`

- 行 44: `description="数据库性能指标"`
  → `description = os.getenv("SCHEMAS_DESCRIPTION_44")`
  → 环境变量: `SCHEMAS_DESCRIPTION_44`

- 行 45: `description="业务指标统计"`
  → `description = os.getenv("SCHEMAS_DESCRIPTION_45")`
  → 环境变量: `SCHEMAS_DESCRIPTION_45`

- 行 48: `description="API文档地址"`
  → `description = os.getenv("SCHEMAS_DESCRIPTION_48")`
  → 环境变量: `SCHEMAS_DESCRIPTION_48`

- 行 51: `description="健康检查地址"`
  → `description = os.getenv("SCHEMAS_DESCRIPTION_51")`
  → 环境变量: `SCHEMAS_DESCRIPTION_51`

- 行 56: `description="HTTP状态码"`
  → `description = os.getenv("SCHEMAS_DESCRIPTION_56")`
  → 环境变量: `SCHEMAS_DESCRIPTION_56`

### src/api/data.py

- 行 118: `detail="limit must be greater than 0"`
  → `detail = os.getenv("DATA_DETAIL_118")`
  → 环境变量: `DATA_DETAIL_118`

- 行 120: `detail="offset must be non-negative"`
  → `detail = os.getenv("DATA_DETAIL_120")`
  → 环境变量: `DATA_DETAIL_120`

- 行 349: `detail="获取比赛特征失败"`
  → `detail = os.getenv("DATA_DETAIL_349")`
  → 环境变量: `DATA_DETAIL_349`

- 行 443: `detail="获取球队统计失败"`
  → `detail = os.getenv("DATA_DETAIL_443")`
  → 环境变量: `DATA_DETAIL_443`

- 行 575: `detail="获取球队统计失败"`
  → `detail = os.getenv("DATA_DETAIL_575")`
  → 环境变量: `DATA_DETAIL_575`

- 行 662: `detail="获取仪表板数据失败"`
  → `detail = os.getenv("DATA_DETAIL_662")`
  → 环境变量: `DATA_DETAIL_662`

- 行 725: `detail="获取比赛列表失败"`
  → `detail = os.getenv("DATA_DETAIL_725")`
  → 环境变量: `DATA_DETAIL_725`

- 行 786: `detail="获取球队列表失败"`
  → `detail = os.getenv("DATA_DETAIL_786")`
  → 环境变量: `DATA_DETAIL_786`

- 行 817: `detail="获取球队信息失败"`
  → `detail = os.getenv("DATA_DETAIL_817")`
  → 环境变量: `DATA_DETAIL_817`

- 行 899: `detail="获取联赛列表失败"`
  → `detail = os.getenv("DATA_DETAIL_899")`
  → 环境变量: `DATA_DETAIL_899`

- 行 932: `detail="联赛不存在或无比赛数据"`
  → `detail = os.getenv("DATA_DETAIL_932")`
  → 环境变量: `DATA_DETAIL_932`

- 行 959: `detail="获取联赛信息失败"`
  → `detail = os.getenv("DATA_DETAIL_959")`
  → 环境变量: `DATA_DETAIL_959`

- 行 979: `detail="获取比赛详情失败"`
  → `detail = os.getenv("DATA_DETAIL_979")`
  → 环境变量: `DATA_DETAIL_979`

- 行 992: `detail="start_date must be <= end_date"`
  → `detail = os.getenv("DATA_DETAIL_992")`
  → 环境变量: `DATA_DETAIL_992`

- 行 1014: `detail="获取比赛列表失败"`
  → `detail = os.getenv("DATA_DETAIL_1014")`
  → 环境变量: `DATA_DETAIL_1014`

- 行 1041: `detail="获取比赛列表失败"`
  → `detail = os.getenv("DATA_DETAIL_1041")`
  → 环境变量: `DATA_DETAIL_1041`

- 行 1091: `detail="获取球队比赛失败"`
  → `detail = os.getenv("DATA_DETAIL_1091")`
  → 环境变量: `DATA_DETAIL_1091`

- 行 1188: `detail="获取联赛积分榜失败"`
  → `detail = os.getenv("DATA_DETAIL_1188")`
  → 环境变量: `DATA_DETAIL_1188`

- 行 1207: `db_health = "healthy"`
  → `db_health = os.getenv("DATA_DB_HEALTH_1207")`
  → 环境变量: `DATA_DB_HEALTH_1207`

- 行 1211: `db_health = "unhealthy"`
  → `db_health = os.getenv("DATA_DB_HEALTH_1211")`
  → 环境变量: `DATA_DB_HEALTH_1211`

- 行 1231: `collection_health = "healthy"`
  → `collection_health = os.getenv("DATA_COLLECTION_HEALTH_1231")`
  → 环境变量: `DATA_COLLECTION_HEALTH_1231`

- 行 1232: `collection_health = "no_data"`
  → `collection_health = os.getenv("DATA_COLLECTION_HEALTH_1232")`
  → 环境变量: `DATA_COLLECTION_HEALTH_1232`

- 行 1236: `collection_health = "unhealthy"`
  → `collection_health = os.getenv("DATA_COLLECTION_HEALTH_1236")`
  → 环境变量: `DATA_COLLECTION_HEALTH_1236`

- 行 1239: `collection_health = "warning"`
  → `collection_health = os.getenv("DATA_COLLECTION_HEALTH_1239")`
  → 环境变量: `DATA_COLLECTION_HEALTH_1239`

### src/api/buggy_api.py

- 行 9: `description="返回记录数量限制"`
  → `description = os.getenv("BUGGY_API_DESCRIPTION_9")`
  → 环境变量: `BUGGY_API_DESCRIPTION_9`

- 行 24: `description="返回记录数量限制"`
  → `description = os.getenv("BUGGY_API_DESCRIPTION_24")`
  → 环境变量: `BUGGY_API_DESCRIPTION_24`

### src/api/features.py

- 行 47: `summary="获取比赛特征"`
  → `summary = os.getenv("FEATURES_SUMMARY_47")`
  → 环境变量: `FEATURES_SUMMARY_47`

- 行 47: `description="获取指定比赛的所有特征，包括球队近期表现、历史对战、赔率等"`
  → `description = os.getenv("FEATURES_DESCRIPTION_47")`
  → 环境变量: `FEATURES_DESCRIPTION_47`

- 行 52: `description="是否包含原始特征数据"`
  → `description = os.getenv("FEATURES_DESCRIPTION_52")`
  → 环境变量: `FEATURES_DESCRIPTION_52`

- 行 70: `detail="比赛ID必须大于0"`
  → `detail = os.getenv("FEATURES_DETAIL_70")`
  → 环境变量: `FEATURES_DETAIL_70`

- 行 75: `detail="特征存储服务暂时不可用，请稍后重试"`
  → `detail = os.getenv("FEATURES_DETAIL_75")`
  → 环境变量: `FEATURES_DETAIL_75`

- 行 98: `detail="数据库查询失败，请稍后重试"`
  → `detail = os.getenv("FEATURES_DETAIL_98")`
  → 环境变量: `FEATURES_DETAIL_98`

- 行 112: `detail="处理比赛数据时发生错误"`
  → `detail = os.getenv("FEATURES_DETAIL_112")`
  → 环境变量: `FEATURES_DETAIL_112`

- 行 191: `summary="获取球队特征"`
  → `summary = os.getenv("FEATURES_SUMMARY_191")`
  → 环境变量: `FEATURES_SUMMARY_191`

- 行 192: `description="获取指定球队的特征，包括近期表现、统计数据等"`
  → `description = os.getenv("FEATURES_DESCRIPTION_192")`
  → 环境变量: `FEATURES_DESCRIPTION_192`

- 行 198: `description="特征计算日期，默认为当前时间"`
  → `description = os.getenv("FEATURES_DESCRIPTION_198")`
  → 环境变量: `FEATURES_DESCRIPTION_198`

- 行 201: `description="是否包含原始特征数据"`
  → `description = os.getenv("FEATURES_DESCRIPTION_201")`
  → 环境变量: `FEATURES_DESCRIPTION_201`

- 行 280: `summary="计算比赛特征"`
  → `summary = os.getenv("FEATURES_SUMMARY_280")`
  → 环境变量: `FEATURES_SUMMARY_280`

- 行 280: `description="实时计算指定比赛的所有特征并存储到特征存储"`
  → `description = os.getenv("FEATURES_DESCRIPTION_280")`
  → 环境变量: `FEATURES_DESCRIPTION_280`

- 行 286: `description="是否强制重新计算"`
  → `description = os.getenv("FEATURES_DESCRIPTION_286")`
  → 环境变量: `FEATURES_DESCRIPTION_286`

- 行 342: `message="特征计算完成"`
  → `message = os.getenv("FEATURES_MESSAGE_342")`
  → 环境变量: `FEATURES_MESSAGE_342`

- 行 346: `summary="计算球队特征"`
  → `summary = os.getenv("FEATURES_SUMMARY_346")`
  → 环境变量: `FEATURES_SUMMARY_346`

- 行 346: `description="实时计算指定球队的特征并存储到特征存储"`
  → `description = os.getenv("FEATURES_DESCRIPTION_346")`
  → 环境变量: `FEATURES_DESCRIPTION_346`

- 行 353: `description="特征计算日期"`
  → `description = os.getenv("FEATURES_DESCRIPTION_353")`
  → 环境变量: `FEATURES_DESCRIPTION_353`

- 行 400: `summary="批量计算特征"`
  → `summary = os.getenv("FEATURES_SUMMARY_400")`
  → 环境变量: `FEATURES_SUMMARY_400`

- 行 400: `description="批量计算指定时间范围内的特征"`
  → `description = os.getenv("FEATURES_DESCRIPTION_400")`
  → 环境变量: `FEATURES_DESCRIPTION_400`

- 行 413: `detail="开始日期必须早于结束日期"`
  → `detail = os.getenv("FEATURES_DETAIL_413")`
  → 环境变量: `FEATURES_DETAIL_413`

- 行 416: `detail="时间范围不能超过30天"`
  → `detail = os.getenv("FEATURES_DETAIL_416")`
  → 环境变量: `FEATURES_DETAIL_416`

- 行 423: `detail="开始日期必须早于结束日期"`
  → `detail = os.getenv("FEATURES_DETAIL_423")`
  → 环境变量: `FEATURES_DETAIL_423`

- 行 442: `message="批量特征计算完成"`
  → `message = os.getenv("FEATURES_MESSAGE_442")`
  → 环境变量: `FEATURES_MESSAGE_442`

- 行 449: `summary="获取历史特征"`
  → `summary = os.getenv("FEATURES_SUMMARY_449")`
  → 环境变量: `FEATURES_SUMMARY_449`

- 行 449: `description="获取比赛的历史特征数据，用于模型训练"`
  → `description = os.getenv("FEATURES_DESCRIPTION_449")`
  → 环境变量: `FEATURES_DESCRIPTION_449`

- 行 452: `description="特征引用列表"`
  → `description = os.getenv("FEATURES_DESCRIPTION_452")`
  → 环境变量: `FEATURES_DESCRIPTION_452`

- 行 506: `message="成功获取历史特征数据"`
  → `message = os.getenv("FEATURES_MESSAGE_506")`
  → 环境变量: `FEATURES_MESSAGE_506`

- 行 513: `summary="特征服务健康检查"`
  → `summary = os.getenv("FEATURES_SUMMARY_513")`
  → 环境变量: `FEATURES_SUMMARY_513`

### src/api/models.py

- 行 37: `summary="获取当前活跃模型"`
  → `summary = os.getenv("MODELS_SUMMARY_37")`
  → 环境变量: `MODELS_SUMMARY_37`

- 行 37: `description="获取当前生产环境使用的模型版本信息"`
  → `description = os.getenv("MODELS_DESCRIPTION_37")`
  → 环境变量: `MODELS_DESCRIPTION_37`

- 行 64: `name="__health_check__"`
  → `name = os.getenv("MODELS_NAME_64")`
  → 环境变量: `MODELS_NAME_64`

- 行 172: `summary="获取模型性能指标"`
  → `summary = os.getenv("MODELS_SUMMARY_172")`
  → 环境变量: `MODELS_SUMMARY_172`

- 行 174: `description="获取模型的性能指标和统计信息"`
  → `description = os.getenv("MODELS_DESCRIPTION_174")`
  → 环境变量: `MODELS_DESCRIPTION_174`

- 行 179: `description="时间窗口：1d, 7d, 30d"`
  → `description = os.getenv("MODELS_DESCRIPTION_179")`
  → 环境变量: `MODELS_DESCRIPTION_179`

- 行 335: `summary="获取模型版本列表"`
  → `summary = os.getenv("MODELS_SUMMARY_335")`
  → 环境变量: `MODELS_SUMMARY_335`

- 行 335: `description="获取指定模型的所有版本信息"`
  → `description = os.getenv("MODELS_DESCRIPTION_335")`
  → 环境变量: `MODELS_DESCRIPTION_335`

- 行 340: `description="返回版本数量限制"`
  → `description = os.getenv("MODELS_DESCRIPTION_340")`
  → 环境变量: `MODELS_DESCRIPTION_340`

- 行 355: `name='{model_name}'`
  → `name = os.getenv("MODELS_NAME_355")`
  → 环境变量: `MODELS_NAME_355`

- 行 409: `summary="推广模型版本"`
  → `summary = os.getenv("MODELS_SUMMARY_409")`
  → 环境变量: `MODELS_SUMMARY_409`

- 行 409: `description="将模型版本推广到生产环境"`
  → `description = os.getenv("MODELS_DESCRIPTION_409")`
  → 环境变量: `MODELS_DESCRIPTION_409`

- 行 415: `description="目标阶段：Staging, Production"`
  → `description = os.getenv("MODELS_DESCRIPTION_415")`
  → 环境变量: `MODELS_DESCRIPTION_415`

- 行 485: `summary="获取模型详细性能"`
  → `summary = os.getenv("MODELS_SUMMARY_485")`
  → 环境变量: `MODELS_SUMMARY_485`

- 行 486: `description="获取模型的详细性能分析"`
  → `description = os.getenv("MODELS_DESCRIPTION_486")`
  → 环境变量: `MODELS_DESCRIPTION_486`

- 行 490: `description="模型版本，为空则获取生产版本"`
  → `description = os.getenv("MODELS_DESCRIPTION_490")`
  → 环境变量: `MODELS_DESCRIPTION_490`

- 行 659: `summary="获取实验列表"`
  → `summary = os.getenv("MODELS_SUMMARY_659")`
  → 环境变量: `MODELS_SUMMARY_659`

- 行 662: `description="获取MLflow实验列表"`
  → `description = os.getenv("MODELS_DESCRIPTION_662")`
  → 环境变量: `MODELS_DESCRIPTION_662`

- 行 668: `description="返回实验数量限制"`
  → `description = os.getenv("MODELS_DESCRIPTION_668")`
  → 环境变量: `MODELS_DESCRIPTION_668`

### src/api/predictions.py

- 行 64: `summary="获取比赛预测结果 / Get Match Prediction"`
  → `summary = os.getenv("PREDICTIONS_SUMMARY_64")`
  → 环境变量: `PREDICTIONS_SUMMARY_64`

- 行 65: `description="获取指定比赛的预测结果，如果不存在则实时生成 / Get prediction result for specified match, generate in real-time if not exists"`
  → `description = os.getenv("PREDICTIONS_DESCRIPTION_65")`
  → 环境变量: `PREDICTIONS_DESCRIPTION_65`

- 行 103: `description="比赛唯一标识符 / Unique match identifier"`
  → `description = os.getenv("PREDICTIONS_DESCRIPTION_103")`
  → 环境变量: `PREDICTIONS_DESCRIPTION_103`

- 行 106: `description="是否强制重新预测 / Whether to force re-prediction"`
  → `description = os.getenv("PREDICTIONS_DESCRIPTION_106")`
  → 环境变量: `PREDICTIONS_DESCRIPTION_106`

- 行 235: `summary="实时预测比赛结果"`
  → `summary = os.getenv("PREDICTIONS_SUMMARY_235")`
  → 环境变量: `PREDICTIONS_SUMMARY_235`

- 行 233: `description="对指定比赛进行实时预测"`
  → `description = os.getenv("PREDICTIONS_DESCRIPTION_233")`
  → 环境变量: `PREDICTIONS_DESCRIPTION_233`

- 行 273: `summary="批量预测比赛"`
  → `summary = os.getenv("PREDICTIONS_SUMMARY_273")`
  → 环境变量: `PREDICTIONS_SUMMARY_273`

- 行 273: `description="对多场比赛进行批量预测"`
  → `description = os.getenv("PREDICTIONS_DESCRIPTION_273")`
  → 环境变量: `PREDICTIONS_DESCRIPTION_273`

- 行 290: `detail="批量预测最多支持50场比赛"`
  → `detail = os.getenv("PREDICTIONS_DETAIL_290")`
  → 环境变量: `PREDICTIONS_DETAIL_290`

- 行 317: `detail="批量预测失败"`
  → `detail = os.getenv("PREDICTIONS_DETAIL_317")`
  → 环境变量: `PREDICTIONS_DETAIL_317`

- 行 319: `summary="获取比赛历史预测"`
  → `summary = os.getenv("PREDICTIONS_SUMMARY_319")`
  → 环境变量: `PREDICTIONS_SUMMARY_319`

- 行 319: `description="获取指定比赛的所有历史预测记录"`
  → `description = os.getenv("PREDICTIONS_DESCRIPTION_319")`
  → 环境变量: `PREDICTIONS_DESCRIPTION_319`

- 行 324: `description="返回记录数量限制"`
  → `description = os.getenv("PREDICTIONS_DESCRIPTION_324")`
  → 环境变量: `PREDICTIONS_DESCRIPTION_324`

- 行 392: `detail="获取历史预测失败"`
  → `detail = os.getenv("PREDICTIONS_DETAIL_392")`
  → 环境变量: `PREDICTIONS_DETAIL_392`

- 行 396: `summary="获取最近的预测"`
  → `summary = os.getenv("PREDICTIONS_SUMMARY_396")`
  → 环境变量: `PREDICTIONS_SUMMARY_396`

- 行 397: `description="获取最近的预测记录"`
  → `description = os.getenv("PREDICTIONS_DESCRIPTION_397")`
  → 环境变量: `PREDICTIONS_DESCRIPTION_397`

- 行 400: `description="时间范围（小时）"`
  → `description = os.getenv("PREDICTIONS_DESCRIPTION_400")`
  → 环境变量: `PREDICTIONS_DESCRIPTION_400`

- 行 400: `description="返回记录数量限制"`
  → `description = os.getenv("PREDICTIONS_DESCRIPTION_400")`
  → 环境变量: `PREDICTIONS_DESCRIPTION_400`

- 行 470: `detail="获取最近预测失败"`
  → `detail = os.getenv("PREDICTIONS_DETAIL_470")`
  → 环境变量: `PREDICTIONS_DETAIL_470`

- 行 474: `summary="验证预测结果"`
  → `summary = os.getenv("PREDICTIONS_SUMMARY_474")`
  → 环境变量: `PREDICTIONS_SUMMARY_474`

- 行 474: `description="验证指定比赛的预测结果（比赛结束后调用）"`
  → `description = os.getenv("PREDICTIONS_DESCRIPTION_474")`
  → 环境变量: `PREDICTIONS_DESCRIPTION_474`

- 行 491: `message="预测结果验证完成"`
  → `message = os.getenv("PREDICTIONS_MESSAGE_491")`
  → 环境变量: `PREDICTIONS_MESSAGE_491`

- 行 500: `message="预测结果验证失败"`
  → `message = os.getenv("PREDICTIONS_MESSAGE_500")`
  → 环境变量: `PREDICTIONS_MESSAGE_500`

- 行 510: `detail="验证预测结果失败"`
  → `detail = os.getenv("PREDICTIONS_DETAIL_510")`
  → 环境变量: `PREDICTIONS_DETAIL_510`

### src/api/features_improved.py

- 行 42: `summary="获取比赛特征"`
  → `summary = os.getenv("FEATURES_IMPROVED_SUMMARY_42")`
  → 环境变量: `FEATURES_IMPROVED_SUMMARY_42`

- 行 42: `description="获取指定比赛的所有特征，包括球队近期表现、历史对战、赔率等"`
  → `description = os.getenv("FEATURES_IMPROVED_DESCRIPTION_42")`
  → 环境变量: `FEATURES_IMPROVED_DESCRIPTION_42`

- 行 46: `description="是否包含原始特征数据"`
  → `description = os.getenv("FEATURES_IMPROVED_DESCRIPTION_46")`
  → 环境变量: `FEATURES_IMPROVED_DESCRIPTION_46`

- 行 64: `detail="比赛ID必须大于0"`
  → `detail = os.getenv("FEATURES_IMPROVED_DETAIL_64")`
  → 环境变量: `FEATURES_IMPROVED_DETAIL_64`

- 行 68: `detail="特征存储服务暂时不可用，请稍后重试"`
  → `detail = os.getenv("FEATURES_IMPROVED_DETAIL_68")`
  → 环境变量: `FEATURES_IMPROVED_DETAIL_68`

- 行 93: `detail="数据库查询失败，请稍后重试"`
  → `detail = os.getenv("FEATURES_IMPROVED_DETAIL_93")`
  → 环境变量: `FEATURES_IMPROVED_DETAIL_93`

- 行 95: `detail="查询比赛信息失败"`
  → `detail = os.getenv("FEATURES_IMPROVED_DETAIL_95")`
  → 环境变量: `FEATURES_IMPROVED_DETAIL_95`

- 行 108: `detail="处理比赛数据时发生错误"`
  → `detail = os.getenv("FEATURES_IMPROVED_DETAIL_108")`
  → 环境变量: `FEATURES_IMPROVED_DETAIL_108`

- 行 186: `summary="特征服务健康检查"`
  → `summary = os.getenv("FEATURES_IMPROVED_SUMMARY_186")`
  → 环境变量: `FEATURES_IMPROVED_SUMMARY_186`

### src/api/monitoring.py

- 行 73: `state = 'active'`
  → `state = os.getenv("MONITORING_STATE_73")`
  → 环境变量: `MONITORING_STATE_73`

- 行 283: `detail="获取监控指标失败"`
  → `detail = os.getenv("MONITORING_DETAIL_283")`
  → 环境变量: `MONITORING_DETAIL_283`

- 行 320: `detail="获取状态失败"`
  → `detail = os.getenv("MONITORING_DETAIL_320")`
  → 环境变量: `MONITORING_DETAIL_320`

### src/api/cache.py

- 行 23: `description="L1缓存统计"`
  → `description = os.getenv("CACHE_DESCRIPTION_23")`
  → 环境变量: `CACHE_DESCRIPTION_23`

- 行 24: `description="L2缓存统计"`
  → `description = os.getenv("CACHE_DESCRIPTION_24")`
  → 环境变量: `CACHE_DESCRIPTION_24`

- 行 29: `description="操作是否成功"`
  → `description = os.getenv("CACHE_DESCRIPTION_29")`
  → 环境变量: `CACHE_DESCRIPTION_29`

- 行 31: `description="操作结果消息"`
  → `description = os.getenv("CACHE_DESCRIPTION_31")`
  → 环境变量: `CACHE_DESCRIPTION_31`

- 行 33: `description="要操作的缓存键列表"`
  → `description = os.getenv("CACHE_DESCRIPTION_33")`
  → 环境变量: `CACHE_DESCRIPTION_33`

- 行 36: `description="键模式（支持通配符）"`
  → `description = os.getenv("CACHE_DESCRIPTION_36")`
  → 环境变量: `CACHE_DESCRIPTION_36`

- 行 39: `description="预热任务类型列表"`
  → `description = os.getenv("CACHE_DESCRIPTION_39")`
  → 环境变量: `CACHE_DESCRIPTION_39`

- 行 39: `description="是否强制重新预热"`
  → `description = os.getenv("CACHE_DESCRIPTION_39")`
  → 环境变量: `CACHE_DESCRIPTION_39`

- 行 44: `summary="获取缓存统计"`
  → `summary = os.getenv("CACHE_SUMMARY_44")`
  → 环境变量: `CACHE_SUMMARY_44`

- 行 53: `detail="缓存管理器未初始化"`
  → `detail = os.getenv("CACHE_DETAIL_53")`
  → 环境变量: `CACHE_DETAIL_53`

- 行 83: `detail="缓存管理器未初始化"`
  → `detail = os.getenv("CACHE_DETAIL_83")`
  → 环境变量: `CACHE_DETAIL_83`

- 行 141: `detail="缓存初始化器未初始化"`
  → `detail = os.getenv("CACHE_DETAIL_141")`
  → 环境变量: `CACHE_DETAIL_141`

- 行 188: `detail="缓存初始化器未初始化"`
  → `detail = os.getenv("CACHE_DETAIL_188")`
  → 环境变量: `CACHE_DETAIL_188`

- 行 200: `message="已启动缓存优化任务"`
  → `message = os.getenv("CACHE_MESSAGE_200")`
  → 环境变量: `CACHE_MESSAGE_200`

- 行 211: `summary="缓存健康检查"`
  → `summary = os.getenv("CACHE_SUMMARY_211")`
  → 环境变量: `CACHE_SUMMARY_211`

- 行 272: `summary="获取缓存配置"`
  → `summary = os.getenv("CACHE_SUMMARY_272")`
  → 环境变量: `CACHE_SUMMARY_272`

### src/utils/time_utils.py

- 行 29: `str = "%Y-%m-%d %H:%M:%S"`
  → `str = os.getenv("TIME_UTILS_STR_29")`
  → 环境变量: `TIME_UTILS_STR_29`

- 行 35: `str = "%Y-%m-%d %H:%M:%S"`
  → `str = os.getenv("TIME_UTILS_STR_35")`
  → 环境变量: `TIME_UTILS_STR_35`

### src/utils/mlflow_security.py

- 行 35: `prefix='mlflow_sandbox_'`
  → `prefix = os.getenv("MLFLOW_SECURITY_PREFIX_35")`
  → 环境变量: `MLFLOW_SECURITY_PREFIX_35`

### src/utils/retry.py

- 行 308: `CLOSED = "closed"`
  → `CLOSED = os.getenv("RETRY_CLOSED_308")`
  → 环境变量: `RETRY_CLOSED_308`

- 行 309: `HALF_OPEN = "half_open"`
  → `HALF_OPEN = os.getenv("RETRY_HALF_OPEN_309")`
  → 环境变量: `RETRY_HALF_OPEN_309`

### src/monitoring/quality_monitor.py

- 行 767: `match_status = 'finished'`
  → `match_status = os.getenv("QUALITY_MONITOR_MATCH_STATUS_767")`
  → 环境变量: `QUALITY_MONITOR_MATCH_STATUS_767`

- 行 791: `match_status = 'scheduled'`
  → `match_status = os.getenv("QUALITY_MONITOR_MATCH_STATUS_791")`
  → 环境变量: `QUALITY_MONITOR_MATCH_STATUS_791`

### src/monitoring/metrics_exporter.py

- 行 246: `collection_type="default"`
  → `collection_type = os.getenv("METRICS_EXPORTER_COLLECTION_TYPE_246")`
  → 环境变量: `METRICS_EXPORTER_COLLECTION_TYPE_246`

- 行 263: `collection_type="default"`
  → `collection_type = os.getenv("METRICS_EXPORTER_COLLECTION_TYPE_263")`
  → 环境变量: `METRICS_EXPORTER_COLLECTION_TYPE_263`

- 行 275: `data_type="default"`
  → `data_type = os.getenv("METRICS_EXPORTER_DATA_TYPE_275")`
  → 环境变量: `METRICS_EXPORTER_DATA_TYPE_275`

- 行 334: `failure_reason="test_failure"`
  → `failure_reason = os.getenv("METRICS_EXPORTER_FAILURE_REASON_334")`
  → 环境变量: `METRICS_EXPORTER_FAILURE_REASON_334`

### src/monitoring/system_monitor.py

- 行 441: `status = "healthy"`
  → `status = os.getenv("SYSTEM_MONITOR_STATUS_441")`
  → 环境变量: `SYSTEM_MONITOR_STATUS_441`

- 行 442: `status = "unhealthy"`
  → `status = os.getenv("SYSTEM_MONITOR_STATUS_442")`
  → 环境变量: `SYSTEM_MONITOR_STATUS_442`

- 行 444: `status = "warning"`
  → `status = os.getenv("SYSTEM_MONITOR_STATUS_444")`
  → 环境变量: `SYSTEM_MONITOR_STATUS_444`

- 行 445: `status = "warning"`
  → `status = os.getenv("SYSTEM_MONITOR_STATUS_445")`
  → 环境变量: `SYSTEM_MONITOR_STATUS_445`

- 行 473: `test_key = "health_check_test"`
  → `test_key = os.getenv("SYSTEM_MONITOR_TEST_KEY_473")`
  → 环境变量: `SYSTEM_MONITOR_TEST_KEY_473`

- 行 485: `status = "healthy"`
  → `status = os.getenv("SYSTEM_MONITOR_STATUS_485")`
  → 环境变量: `SYSTEM_MONITOR_STATUS_485`

- 行 486: `status = "unhealthy"`
  → `status = os.getenv("SYSTEM_MONITOR_STATUS_486")`
  → 环境变量: `SYSTEM_MONITOR_STATUS_486`

- 行 490: `status = "warning"`
  → `status = os.getenv("SYSTEM_MONITOR_STATUS_490")`
  → 环境变量: `SYSTEM_MONITOR_STATUS_490`

- 行 492: `status = "warning"`
  → `status = os.getenv("SYSTEM_MONITOR_STATUS_492")`
  → 环境变量: `SYSTEM_MONITOR_STATUS_492`

- 行 520: `status = "healthy"`
  → `status = os.getenv("SYSTEM_MONITOR_STATUS_520")`
  → 环境变量: `SYSTEM_MONITOR_STATUS_520`

- 行 525: `status = "warning"`
  → `status = os.getenv("SYSTEM_MONITOR_STATUS_525")`
  → 环境变量: `SYSTEM_MONITOR_STATUS_525`

- 行 528: `status = "unhealthy"`
  → `status = os.getenv("SYSTEM_MONITOR_STATUS_528")`
  → 环境变量: `SYSTEM_MONITOR_STATUS_528`

- 行 532: `status = "warning"`
  → `status = os.getenv("SYSTEM_MONITOR_STATUS_532")`
  → 环境变量: `SYSTEM_MONITOR_STATUS_532`

- 行 533: `status = "unhealthy"`
  → `status = os.getenv("SYSTEM_MONITOR_STATUS_533")`
  → 环境变量: `SYSTEM_MONITOR_STATUS_533`

- 行 535: `status = "warning"`
  → `status = os.getenv("SYSTEM_MONITOR_STATUS_535")`
  → 环境变量: `SYSTEM_MONITOR_STATUS_535`

- 行 538: `status = "unhealthy"`
  → `status = os.getenv("SYSTEM_MONITOR_STATUS_538")`
  → 环境变量: `SYSTEM_MONITOR_STATUS_538`

- 行 541: `status = "warning"`
  → `status = os.getenv("SYSTEM_MONITOR_STATUS_541")`
  → 环境变量: `SYSTEM_MONITOR_STATUS_541`

- 行 559: `status = "healthy"`
  → `status = os.getenv("SYSTEM_MONITOR_STATUS_559")`
  → 环境变量: `SYSTEM_MONITOR_STATUS_559`

- 行 584: `status = "warning"`
  → `status = os.getenv("SYSTEM_MONITOR_STATUS_584")`
  → 环境变量: `SYSTEM_MONITOR_STATUS_584`

- 行 586: `status = "unhealthy"`
  → `status = os.getenv("SYSTEM_MONITOR_STATUS_586")`
  → 环境变量: `SYSTEM_MONITOR_STATUS_586`

- 行 606: `status = "warning"`
  → `status = os.getenv("SYSTEM_MONITOR_STATUS_606")`
  → 环境变量: `SYSTEM_MONITOR_STATUS_606`

- 行 608: `status = "unhealthy"`
  → `status = os.getenv("SYSTEM_MONITOR_STATUS_608")`
  → 环境变量: `SYSTEM_MONITOR_STATUS_608`

- 行 622: `status = "healthy"`
  → `status = os.getenv("SYSTEM_MONITOR_STATUS_622")`
  → 环境变量: `SYSTEM_MONITOR_STATUS_622`

- 行 636: `status = "warning"`
  → `status = os.getenv("SYSTEM_MONITOR_STATUS_636")`
  → 环境变量: `SYSTEM_MONITOR_STATUS_636`

- 行 650: `status = "warning"`
  → `status = os.getenv("SYSTEM_MONITOR_STATUS_650")`
  → 环境变量: `SYSTEM_MONITOR_STATUS_650`

- 行 662: `status = "healthy"`
  → `status = os.getenv("SYSTEM_MONITOR_STATUS_662")`
  → 环境变量: `SYSTEM_MONITOR_STATUS_662`

- 行 690: `status = "warning"`
  → `status = os.getenv("SYSTEM_MONITOR_STATUS_690")`
  → 环境变量: `SYSTEM_MONITOR_STATUS_690`

- 行 693: `status = "unhealthy"`
  → `status = os.getenv("SYSTEM_MONITOR_STATUS_693")`
  → 环境变量: `SYSTEM_MONITOR_STATUS_693`

- 行 704: `status = "warning"`
  → `status = os.getenv("SYSTEM_MONITOR_STATUS_704")`
  → 环境变量: `SYSTEM_MONITOR_STATUS_704`

- 行 707: `status = "unhealthy"`
  → `status = os.getenv("SYSTEM_MONITOR_STATUS_707")`
  → 环境变量: `SYSTEM_MONITOR_STATUS_707`

### src/monitoring/metrics_collector.py

- 行 656: `format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"`
  → `format = os.getenv("METRICS_COLLECTOR_FORMAT_656")`
  → 环境变量: `METRICS_COLLECTOR_FORMAT_656`

### src/monitoring/anomaly_detector.py

- 行 29: `OUTLIER = "outlier"`
  → `OUTLIER = os.getenv("ANOMALY_DETECTOR_OUTLIER_29")`
  → 环境变量: `ANOMALY_DETECTOR_OUTLIER_29`

- 行 29: `TREND_CHANGE = "trend_change"`
  → `TREND_CHANGE = os.getenv("ANOMALY_DETECTOR_TREND_CHANGE_29")`
  → 环境变量: `ANOMALY_DETECTOR_TREND_CHANGE_29`

- 行 30: `PATTERN_BREAK = "pattern_break"`
  → `PATTERN_BREAK = os.getenv("ANOMALY_DETECTOR_PATTERN_BREAK_30")`
  → 环境变量: `ANOMALY_DETECTOR_PATTERN_BREAK_30`

- 行 30: `VALUE_RANGE = "value_range"`
  → `VALUE_RANGE = os.getenv("ANOMALY_DETECTOR_VALUE_RANGE_30")`
  → 环境变量: `ANOMALY_DETECTOR_VALUE_RANGE_30`

- 行 31: `FREQUENCY = "frequency"`
  → `FREQUENCY = os.getenv("ANOMALY_DETECTOR_FREQUENCY_31")`
  → 环境变量: `ANOMALY_DETECTOR_FREQUENCY_31`

- 行 31: `NULL_SPIKE = "null_spike"`
  → `NULL_SPIKE = os.getenv("ANOMALY_DETECTOR_NULL_SPIKE_31")`
  → 环境变量: `ANOMALY_DETECTOR_NULL_SPIKE_31`

- 行 33: `MEDIUM = "medium"`
  → `MEDIUM = os.getenv("ANOMALY_DETECTOR_MEDIUM_33")`
  → 环境变量: `ANOMALY_DETECTOR_MEDIUM_33`

- 行 33: `CRITICAL = "critical"`
  → `CRITICAL = os.getenv("ANOMALY_DETECTOR_CRITICAL_33")`
  → 环境变量: `ANOMALY_DETECTOR_CRITICAL_33`

- 行 393: `detection_method="3sigma"`
  → `detection_method = os.getenv("ANOMALY_DETECTOR_DETECTION_METHOD_393")`
  → 环境变量: `ANOMALY_DETECTOR_DETECTION_METHOD_393`

- 行 496: `detection_method="z_score"`
  → `detection_method = os.getenv("ANOMALY_DETECTOR_DETECTION_METHOD_496")`
  → 环境变量: `ANOMALY_DETECTOR_DETECTION_METHOD_496`

- 行 551: `detection_method="range_check"`
  → `detection_method = os.getenv("ANOMALY_DETECTOR_DETECTION_METHOD_551")`
  → 环境变量: `ANOMALY_DETECTOR_DETECTION_METHOD_551`

- 行 601: `detection_method="frequency"`
  → `detection_method = os.getenv("ANOMALY_DETECTOR_DETECTION_METHOD_601")`
  → 环境变量: `ANOMALY_DETECTOR_DETECTION_METHOD_601`

- 行 662: `detection_method="time_gap"`
  → `detection_method = os.getenv("ANOMALY_DETECTOR_DETECTION_METHOD_662")`
  → 环境变量: `ANOMALY_DETECTOR_DETECTION_METHOD_662`

### src/monitoring/alert_manager.py

- 行 28: `WARNING = "warning"`
  → `WARNING = os.getenv("ALERT_MANAGER_WARNING_28")`
  → 环境变量: `ALERT_MANAGER_WARNING_28`

- 行 28: `CRITICAL = "critical"`
  → `CRITICAL = os.getenv("ALERT_MANAGER_CRITICAL_28")`
  → 环境变量: `ALERT_MANAGER_CRITICAL_28`

- 行 30: `ACTIVE = "active"`
  → `ACTIVE = os.getenv("ALERT_MANAGER_ACTIVE_30")`
  → 环境变量: `ALERT_MANAGER_ACTIVE_30`

- 行 33: `RESOLVED = "resolved"`
  → `RESOLVED = os.getenv("ALERT_MANAGER_RESOLVED_33")`
  → 环境变量: `ALERT_MANAGER_RESOLVED_33`

- 行 34: `SILENCED = "silenced"`
  → `SILENCED = os.getenv("ALERT_MANAGER_SILENCED_34")`
  → 环境变量: `ALERT_MANAGER_SILENCED_34`

- 行 37: `PROMETHEUS = "prometheus"`
  → `PROMETHEUS = os.getenv("ALERT_MANAGER_PROMETHEUS_37")`
  → 环境变量: `ALERT_MANAGER_PROMETHEUS_37`

- 行 38: `WEBHOOK = "webhook"`
  → `WEBHOOK = os.getenv("ALERT_MANAGER_WEBHOOK_38")`
  → 环境变量: `ALERT_MANAGER_WEBHOOK_38`

- 行 255: `rule_id="data_freshness_critical"`
  → `rule_id = os.getenv("ALERT_MANAGER_RULE_ID_255")`
  → 环境变量: `ALERT_MANAGER_RULE_ID_255`

- 行 259: `name="数据新鲜度严重告警"`
  → `name = os.getenv("ALERT_MANAGER_NAME_259")`
  → 环境变量: `ALERT_MANAGER_NAME_259`

- 行 260: `condition="freshness_hours > 24"`
  → `condition = os.getenv("ALERT_MANAGER_CONDITION_260")`
  → 环境变量: `ALERT_MANAGER_CONDITION_260`

- 行 266: `rule_id="data_freshness_warning"`
  → `rule_id = os.getenv("ALERT_MANAGER_RULE_ID_266")`
  → 环境变量: `ALERT_MANAGER_RULE_ID_266`

- 行 267: `name="数据新鲜度警告"`
  → `name = os.getenv("ALERT_MANAGER_NAME_267")`
  → 环境变量: `ALERT_MANAGER_NAME_267`

- 行 267: `condition="freshness_hours > 12"`
  → `condition = os.getenv("ALERT_MANAGER_CONDITION_267")`
  → 环境变量: `ALERT_MANAGER_CONDITION_267`

- 行 273: `rule_id="data_completeness_critical"`
  → `rule_id = os.getenv("ALERT_MANAGER_RULE_ID_273")`
  → 环境变量: `ALERT_MANAGER_RULE_ID_273`

- 行 274: `name="数据完整性严重告警"`
  → `name = os.getenv("ALERT_MANAGER_NAME_274")`
  → 环境变量: `ALERT_MANAGER_NAME_274`

- 行 275: `condition="completeness_ratio < 0.8"`
  → `condition = os.getenv("ALERT_MANAGER_CONDITION_275")`
  → 环境变量: `ALERT_MANAGER_CONDITION_275`

- 行 281: `rule_id="data_completeness_warning"`
  → `rule_id = os.getenv("ALERT_MANAGER_RULE_ID_281")`
  → 环境变量: `ALERT_MANAGER_RULE_ID_281`

- 行 282: `name="数据完整性警告"`
  → `name = os.getenv("ALERT_MANAGER_NAME_282")`
  → 环境变量: `ALERT_MANAGER_NAME_282`

- 行 282: `condition="completeness_ratio < 0.95"`
  → `condition = os.getenv("ALERT_MANAGER_CONDITION_282")`
  → 环境变量: `ALERT_MANAGER_CONDITION_282`

- 行 288: `rule_id="data_quality_critical"`
  → `rule_id = os.getenv("ALERT_MANAGER_RULE_ID_288")`
  → 环境变量: `ALERT_MANAGER_RULE_ID_288`

- 行 289: `name="数据质量严重告警"`
  → `name = os.getenv("ALERT_MANAGER_NAME_289")`
  → 环境变量: `ALERT_MANAGER_NAME_289`

- 行 290: `condition="quality_score < 0.7"`
  → `condition = os.getenv("ALERT_MANAGER_CONDITION_290")`
  → 环境变量: `ALERT_MANAGER_CONDITION_290`

- 行 294: `rule_id="anomaly_critical"`
  → `rule_id = os.getenv("ALERT_MANAGER_RULE_ID_294")`
  → 环境变量: `ALERT_MANAGER_RULE_ID_294`

- 行 296: `name="数据异常严重告警"`
  → `name = os.getenv("ALERT_MANAGER_NAME_296")`
  → 环境变量: `ALERT_MANAGER_NAME_296`

- 行 298: `condition="anomaly_score > 0.2"`
  → `condition = os.getenv("ALERT_MANAGER_CONDITION_298")`
  → 环境变量: `ALERT_MANAGER_CONDITION_298`

- 行 302: `rule_id="anomaly_warning"`
  → `rule_id = os.getenv("ALERT_MANAGER_RULE_ID_302")`
  → 环境变量: `ALERT_MANAGER_RULE_ID_302`

- 行 302: `name="数据异常警告"`
  → `name = os.getenv("ALERT_MANAGER_NAME_302")`
  → 环境变量: `ALERT_MANAGER_NAME_302`

- 行 303: `condition="anomaly_score > 0.1"`
  → `condition = os.getenv("ALERT_MANAGER_CONDITION_303")`
  → 环境变量: `ALERT_MANAGER_CONDITION_303`

- 行 485: `error_type="alert_handler"`
  → `error_type = os.getenv("ALERT_MANAGER_ERROR_TYPE_485")`
  → 环境变量: `ALERT_MANAGER_ERROR_TYPE_485`

- 行 689: `source="quality_monitor"`
  → `source = os.getenv("ALERT_MANAGER_SOURCE_689")`
  → 环境变量: `ALERT_MANAGER_SOURCE_689`

- 行 697: `rule_id="data_freshness_critical"`
  → `rule_id = os.getenv("ALERT_MANAGER_RULE_ID_697")`
  → 环境变量: `ALERT_MANAGER_RULE_ID_697`

- 行 705: `source="quality_monitor"`
  → `source = os.getenv("ALERT_MANAGER_SOURCE_705")`
  → 环境变量: `ALERT_MANAGER_SOURCE_705`

- 行 707: `rule_id="data_freshness_warning"`
  → `rule_id = os.getenv("ALERT_MANAGER_RULE_ID_707")`
  → 环境变量: `ALERT_MANAGER_RULE_ID_707`

- 行 719: `source="quality_monitor"`
  → `source = os.getenv("ALERT_MANAGER_SOURCE_719")`
  → 环境变量: `ALERT_MANAGER_SOURCE_719`

- 行 722: `rule_id="data_completeness_critical"`
  → `rule_id = os.getenv("ALERT_MANAGER_RULE_ID_722")`
  → 环境变量: `ALERT_MANAGER_RULE_ID_722`

- 行 733: `source="quality_monitor"`
  → `source = os.getenv("ALERT_MANAGER_SOURCE_733")`
  → 环境变量: `ALERT_MANAGER_SOURCE_733`

- 行 735: `rule_id="data_completeness_warning"`
  → `rule_id = os.getenv("ALERT_MANAGER_RULE_ID_735")`
  → 环境变量: `ALERT_MANAGER_RULE_ID_735`

- 行 741: `title="数据质量严重告警"`
  → `title = os.getenv("ALERT_MANAGER_TITLE_741")`
  → 环境变量: `ALERT_MANAGER_TITLE_741`

- 行 744: `source="quality_monitor"`
  → `source = os.getenv("ALERT_MANAGER_SOURCE_744")`
  → 环境变量: `ALERT_MANAGER_SOURCE_744`

- 行 746: `rule_id="data_quality_critical"`
  → `rule_id = os.getenv("ALERT_MANAGER_RULE_ID_746")`
  → 环境变量: `ALERT_MANAGER_RULE_ID_746`

- 行 762: `source="anomaly_detector"`
  → `source = os.getenv("ALERT_MANAGER_SOURCE_762")`
  → 环境变量: `ALERT_MANAGER_SOURCE_762`

- 行 771: `rule_id="anomaly_critical"`
  → `rule_id = os.getenv("ALERT_MANAGER_RULE_ID_771")`
  → 环境变量: `ALERT_MANAGER_RULE_ID_771`

- 行 786: `source="anomaly_detector"`
  → `source = os.getenv("ALERT_MANAGER_SOURCE_786")`
  → 环境变量: `ALERT_MANAGER_SOURCE_786`

- 行 791: `rule_id="anomaly_warning"`
  → `rule_id = os.getenv("ALERT_MANAGER_RULE_ID_791")`
  → 环境变量: `ALERT_MANAGER_RULE_ID_791`

### src/models/common_models.py

- 行 26: `DOCUMENT = "document"`
  → `DOCUMENT = os.getenv("COMMON_MODELS_DOCUMENT_26")`
  → 环境变量: `COMMON_MODELS_DOCUMENT_26`

- 行 33: `MODERATOR = "moderator"`
  → `MODERATOR = os.getenv("COMMON_MODELS_MODERATOR_33")`
  → 环境变量: `COMMON_MODELS_MODERATOR_33`

### src/models/prediction_service.py

- 行 122: `str = "football_baseline_model"`
  → `str = os.getenv("PREDICTION_SERVICE_STR_122")`
  → 环境变量: `PREDICTION_SERVICE_STR_122`

- 行 246: `str = "football_baseline_model"`
  → `str = os.getenv("PREDICTION_SERVICE_STR_246")`
  → 环境变量: `PREDICTION_SERVICE_STR_246`

- 行 291: `str = "football_baseline_model"`
  → `str = os.getenv("PREDICTION_SERVICE_STR_291")`
  → 环境变量: `PREDICTION_SERVICE_STR_291`

- 行 362: `str = "football_baseline_model"`
  → `str = os.getenv("PREDICTION_SERVICE_STR_362")`
  → 环境变量: `PREDICTION_SERVICE_STR_362`

- 行 544: `model_name="football_baseline_model"`
  → `model_name = os.getenv("PREDICTION_SERVICE_MODEL_NAME_544")`
  → 环境变量: `PREDICTION_SERVICE_MODEL_NAME_544`

- 行 567: `model_name="football_baseline_model"`
  → `model_name = os.getenv("PREDICTION_SERVICE_MODEL_NAME_567")`
  → 环境变量: `PREDICTION_SERVICE_MODEL_NAME_567`

- 行 892: `str = "football_baseline_model"`
  → `str = os.getenv("PREDICTION_SERVICE_STR_892")`
  → 环境变量: `PREDICTION_SERVICE_STR_892`

### src/models/model_training.py

- 行 210: `left_on="match_id"`
  → `left_on = os.getenv("MODEL_TRAINING_LEFT_ON_210")`
  → 环境变量: `MODEL_TRAINING_LEFT_ON_210`

- 行 211: `target_col = "result"`
  → `target_col = os.getenv("MODEL_TRAINING_TARGET_COL_211")`
  → 环境变量: `MODEL_TRAINING_TARGET_COL_211`

- 行 375: `str = "football_prediction_baseline"`
  → `str = os.getenv("MODEL_TRAINING_STR_375")`
  → 环境变量: `MODEL_TRAINING_STR_375`

- 行 377: `str = "football_baseline_model"`
  → `str = os.getenv("MODEL_TRAINING_STR_377")`
  → 环境变量: `MODEL_TRAINING_STR_377`

- 行 458: `average="weighted"`
  → `average = os.getenv("MODEL_TRAINING_AVERAGE_458")`
  → 环境变量: `MODEL_TRAINING_AVERAGE_458`

- 行 459: `average="weighted"`
  → `average = os.getenv("MODEL_TRAINING_AVERAGE_459")`
  → 环境变量: `MODEL_TRAINING_AVERAGE_459`

- 行 461: `average="weighted"`
  → `average = os.getenv("MODEL_TRAINING_AVERAGE_461")`
  → 环境变量: `MODEL_TRAINING_AVERAGE_461`

- 行 464: `average="weighted"`
  → `average = os.getenv("MODEL_TRAINING_AVERAGE_464")`
  → 环境变量: `MODEL_TRAINING_AVERAGE_464`

- 行 466: `average="weighted"`
  → `average = os.getenv("MODEL_TRAINING_AVERAGE_466")`
  → 环境变量: `MODEL_TRAINING_AVERAGE_466`

- 行 467: `average="weighted"`
  → `average = os.getenv("MODEL_TRAINING_AVERAGE_467")`
  → 环境变量: `MODEL_TRAINING_AVERAGE_467`

- 行 544: `str = "football_baseline_model"`
  → `str = os.getenv("MODEL_TRAINING_STR_544")`
  → 环境变量: `MODEL_TRAINING_STR_544`

- 行 575: `stage="Production"`
  → `stage = os.getenv("MODEL_TRAINING_STAGE_575")`
  → 环境变量: `MODEL_TRAINING_STAGE_575`

### src/middleware/security.py

- 行 134: `detail="IP address blocked"`
  → `detail = os.getenv("SECURITY_DETAIL_134")`
  → 环境变量: `SECURITY_DETAIL_134`

- 行 145: `detail="Rate limit exceeded"`
  → `detail = os.getenv("SECURITY_DETAIL_145")`
  → 环境变量: `SECURITY_DETAIL_145`

- 行 170: `detail="Request entity too large"`
  → `detail = os.getenv("SECURITY_DETAIL_170")`
  → 环境变量: `SECURITY_DETAIL_170`

### src/middleware/performance.py

- 行 197: `str = "X-Batch-Request"`
  → `str = os.getenv("PERFORMANCE_STR_197")`
  → 环境变量: `PERFORMANCE_STR_197`

- 行 250: `media_type="application/json"`
  → `media_type = os.getenv("PERFORMANCE_MEDIA_TYPE_250")`
  → 环境变量: `PERFORMANCE_MEDIA_TYPE_250`

### src/streaming/kafka_producer.py

- 行 143: `topic = "matches-stream"`
  → `topic = os.getenv("KAFKA_PRODUCER_TOPIC_143")`
  → 环境变量: `KAFKA_PRODUCER_TOPIC_143`

- 行 190: `topic = "odds-stream"`
  → `topic = os.getenv("KAFKA_PRODUCER_TOPIC_190")`
  → 环境变量: `KAFKA_PRODUCER_TOPIC_190`

- 行 240: `topic = "scores-stream"`
  → `topic = os.getenv("KAFKA_PRODUCER_TOPIC_240")`
  → 环境变量: `KAFKA_PRODUCER_TOPIC_240`

### src/streaming/stream_config.py

- 行 21: `str = "localhost:9092"`
  → `str = os.getenv("STREAM_CONFIG_STR_21")`
  → 环境变量: `STREAM_CONFIG_STR_21`

- 行 22: `str = "PLAINTEXT"`
  → `str = os.getenv("STREAM_CONFIG_STR_22")`
  → 环境变量: `STREAM_CONFIG_STR_22`

- 行 22: `str = "football-prediction-producer"`
  → `str = os.getenv("STREAM_CONFIG_STR_22")`
  → 环境变量: `STREAM_CONFIG_STR_22`

- 行 30: `str = "football-prediction-consumers"`
  → `str = os.getenv("STREAM_CONFIG_STR_30")`
  → 环境变量: `STREAM_CONFIG_STR_30`

- 行 33: `str = "football-prediction-consumer"`
  → `str = os.getenv("STREAM_CONFIG_STR_33")`
  → 环境变量: `STREAM_CONFIG_STR_33`

- 行 34: `str = "latest"`
  → `str = os.getenv("STREAM_CONFIG_STR_34")`
  → 环境变量: `STREAM_CONFIG_STR_34`

- 行 38: `str = "string"`
  → `str = os.getenv("STREAM_CONFIG_STR_38")`
  → 环境变量: `STREAM_CONFIG_STR_38`

- 行 47: `str = "delete"`
  → `str = os.getenv("STREAM_CONFIG_STR_47")`
  → 环境变量: `STREAM_CONFIG_STR_47`

- 行 90: `name="matches-stream"`
  → `name = os.getenv("STREAM_CONFIG_NAME_90")`
  → 环境变量: `STREAM_CONFIG_NAME_90`

- 行 96: `name="odds-stream"`
  → `name = os.getenv("STREAM_CONFIG_NAME_96")`
  → 环境变量: `STREAM_CONFIG_NAME_96`

- 行 102: `name="scores-stream"`
  → `name = os.getenv("STREAM_CONFIG_NAME_102")`
  → 环境变量: `STREAM_CONFIG_NAME_102`

- 行 107: `name="processed-data-stream"`
  → `name = os.getenv("STREAM_CONFIG_NAME_107")`
  → 环境变量: `STREAM_CONFIG_NAME_107`

### src/database/optimization.py

- 行 177: `str = "production"`
  → `str = os.getenv("OPTIMIZATION_STR_177")`
  → 环境变量: `OPTIMIZATION_STR_177`

- 行 267: `status = 'completed'`
  → `status = os.getenv("OPTIMIZATION_STATUS_267")`
  → 环境变量: `OPTIMIZATION_STATUS_267`

- 行 322: `state = 'active'`
  → `state = os.getenv("OPTIMIZATION_STATE_322")`
  → 环境变量: `OPTIMIZATION_STATE_322`

- 行 339: `schemaname = 'public'`
  → `schemaname = os.getenv("OPTIMIZATION_SCHEMANAME_339")`
  → 环境变量: `OPTIMIZATION_SCHEMANAME_339`

### src/database/connection.py

- 行 115: `READER = "reader"`
  → `READER = os.getenv("CONNECTION_READER_115")`
  → 环境变量: `CONNECTION_READER_115`

- 行 115: `WRITER = "writer"`
  → `WRITER = os.getenv("CONNECTION_WRITER_115")`
  → 环境变量: `CONNECTION_WRITER_115`

- 行 201: `database="football_prediction"`
  → `database = os.getenv("CONNECTION_DATABASE_201")`
  → 环境变量: `CONNECTION_DATABASE_201`

- 行 203: `user="football_user"`
  → `user = os.getenv("CONNECTION_USER_203")`
  → 环境变量: `CONNECTION_USER_203`

- 行 203: `password="football_password"`
  → `password = os.getenv("CONNECTION_PASSWORD_203")`
  → 环境变量: `CONNECTION_PASSWORD_203`

### src/database/models/league.py

- 行 20: `__tablename__ = "leagues"`
  → `__tablename__ = os.getenv("LEAGUE___TABLENAME___20")`
  → 环境变量: `LEAGUE___TABLENAME___20`

- 行 30: `comment="联赛级别（1=顶级联赛，2=二级联赛等）"`
  → `comment = os.getenv("LEAGUE_COMMENT_30")`
  → 环境变量: `LEAGUE_COMMENT_30`

- 行 34: `comment="API联赛ID"`
  → `comment = os.getenv("LEAGUE_COMMENT_34")`
  → 环境变量: `LEAGUE_COMMENT_34`

- 行 36: `comment="赛季开始月份（1-12）"`
  → `comment = os.getenv("LEAGUE_COMMENT_36")`
  → 环境变量: `LEAGUE_COMMENT_36`

- 行 37: `comment="赛季结束月份（1-12）"`
  → `comment = os.getenv("LEAGUE_COMMENT_37")`
  → 环境变量: `LEAGUE_COMMENT_37`

- 行 42: `back_populates="league"`
  → `back_populates = os.getenv("LEAGUE_BACK_POPULATES_42")`
  → 环境变量: `LEAGUE_BACK_POPULATES_42`

- 行 42: `lazy="dynamic"`
  → `lazy = os.getenv("LEAGUE_LAZY_42")`
  → 环境变量: `LEAGUE_LAZY_42`

- 行 42: `cascade="all, delete-orphan"`
  → `cascade = os.getenv("LEAGUE_CASCADE_42")`
  → 环境变量: `LEAGUE_CASCADE_42`

- 行 46: `back_populates="league"`
  → `back_populates = os.getenv("LEAGUE_BACK_POPULATES_46")`
  → 环境变量: `LEAGUE_BACK_POPULATES_46`

- 行 46: `lazy="dynamic"`
  → `lazy = os.getenv("LEAGUE_LAZY_46")`
  → 环境变量: `LEAGUE_LAZY_46`

- 行 53: `name='{self.league_name}'`
  → `name = os.getenv("LEAGUE_NAME_53")`
  → 环境变量: `LEAGUE_NAME_53`

- 行 53: `country='{self.country}'`
  → `country = os.getenv("LEAGUE_COUNTRY_53")`
  → 环境变量: `LEAGUE_COUNTRY_53`

### src/database/models/audit_log.py

- 行 25: `CREATE = "CREATE"`
  → `CREATE = os.getenv("AUDIT_LOG_CREATE_25")`
  → 环境变量: `AUDIT_LOG_CREATE_25`

- 行 26: `UPDATE = "UPDATE"`
  → `UPDATE = os.getenv("AUDIT_LOG_UPDATE_26")`
  → 环境变量: `AUDIT_LOG_UPDATE_26`

- 行 27: `DELETE = "DELETE"`
  → `DELETE = os.getenv("AUDIT_LOG_DELETE_27")`
  → 环境变量: `AUDIT_LOG_DELETE_27`

- 行 28: `REVOKE = "REVOKE"`
  → `REVOKE = os.getenv("AUDIT_LOG_REVOKE_28")`
  → 环境变量: `AUDIT_LOG_REVOKE_28`

- 行 32: `LOGOUT = "LOGOUT"`
  → `LOGOUT = os.getenv("AUDIT_LOG_LOGOUT_32")`
  → 环境变量: `AUDIT_LOG_LOGOUT_32`

- 行 32: `BACKUP = "BACKUP"`
  → `BACKUP = os.getenv("AUDIT_LOG_BACKUP_32")`
  → 环境变量: `AUDIT_LOG_BACKUP_32`

- 行 34: `RESTORE = "RESTORE"`
  → `RESTORE = os.getenv("AUDIT_LOG_RESTORE_34")`
  → 环境变量: `AUDIT_LOG_RESTORE_34`

- 行 36: `CONFIG_CHANGE = "CONFIG_CHANGE"`
  → `CONFIG_CHANGE = os.getenv("AUDIT_LOG_CONFIG_CHANGE_36")`
  → 环境变量: `AUDIT_LOG_CONFIG_CHANGE_36`

- 行 37: `SCHEMA_CHANGE = "SCHEMA_CHANGE"`
  → `SCHEMA_CHANGE = os.getenv("AUDIT_LOG_SCHEMA_CHANGE_37")`
  → 环境变量: `AUDIT_LOG_SCHEMA_CHANGE_37`

- 行 41: `MEDIUM = "MEDIUM"`
  → `MEDIUM = os.getenv("AUDIT_LOG_MEDIUM_41")`
  → 环境变量: `AUDIT_LOG_MEDIUM_41`

- 行 42: `CRITICAL = "CRITICAL"`
  → `CRITICAL = os.getenv("AUDIT_LOG_CRITICAL_42")`
  → 环境变量: `AUDIT_LOG_CRITICAL_42`

- 行 50: `__tablename__ = "audit_logs"`
  → `__tablename__ = os.getenv("AUDIT_LOG___TABLENAME___50")`
  → 环境变量: `AUDIT_LOG___TABLENAME___50`

- 行 52: `comment="审计日志ID"`
  → `comment = os.getenv("AUDIT_LOG_COMMENT_52")`
  → 环境变量: `AUDIT_LOG_COMMENT_52`

- 行 59: `comment="操作用户ID"`
  → `comment = os.getenv("AUDIT_LOG_COMMENT_59")`
  → 环境变量: `AUDIT_LOG_COMMENT_59`

- 行 82: `comment="旧值哈希（敏感数据）"`
  → `comment = os.getenv("AUDIT_LOG_COMMENT_82")`
  → 环境变量: `AUDIT_LOG_COMMENT_82`

- 行 83: `comment="新值哈希（敏感数据）"`
  → `comment = os.getenv("AUDIT_LOG_COMMENT_83")`
  → 环境变量: `AUDIT_LOG_COMMENT_83`

- 行 86: `comment="客户端IP地址"`
  → `comment = os.getenv("AUDIT_LOG_COMMENT_86")`
  → 环境变量: `AUDIT_LOG_COMMENT_86`

- 行 89: `comment="HTTP方法"`
  → `comment = os.getenv("AUDIT_LOG_COMMENT_89")`
  → 环境变量: `AUDIT_LOG_COMMENT_89`

- 行 93: `comment="操作是否成功"`
  → `comment = os.getenv("AUDIT_LOG_COMMENT_93")`
  → 环境变量: `AUDIT_LOG_COMMENT_93`

- 行 96: `comment="操作耗时（毫秒）"`
  → `comment = os.getenv("AUDIT_LOG_COMMENT_96")`
  → 环境变量: `AUDIT_LOG_COMMENT_96`

- 行 104: `comment="标签（逗号分隔）"`
  → `comment = os.getenv("AUDIT_LOG_COMMENT_104")`
  → 环境变量: `AUDIT_LOG_COMMENT_104`

- 行 111: `comment="保留期限（天）"`
  → `comment = os.getenv("AUDIT_LOG_COMMENT_111")`
  → 环境变量: `AUDIT_LOG_COMMENT_111`

- 行 115: `comment="是否包含敏感数据"`
  → `comment = os.getenv("AUDIT_LOG_COMMENT_115")`
  → 环境变量: `AUDIT_LOG_COMMENT_115`

- 行 131: `user_id='{self.user_id}'`
  → `user_id = os.getenv("AUDIT_LOG_USER_ID_131")`
  → 环境变量: `AUDIT_LOG_USER_ID_131`

- 行 132: `action='{self.action}'`
  → `action = os.getenv("AUDIT_LOG_ACTION_132")`
  → 环境变量: `AUDIT_LOG_ACTION_132`

- 行 132: `table_name='{self.table_name}'`
  → `table_name = os.getenv("AUDIT_LOG_TABLE_NAME_132")`
  → 环境变量: `AUDIT_LOG_TABLE_NAME_132`

- 行 133: `timestamp='{self.timestamp}'`
  → `timestamp = os.getenv("AUDIT_LOG_TIMESTAMP_133")`
  → 环境变量: `AUDIT_LOG_TIMESTAMP_133`

### src/database/models/data_quality_log.py

- 行 30: `__tablename__ = "data_quality_logs"`
  → `__tablename__ = os.getenv("DATA_QUALITY_LOG___TABLENAME___30")`
  → 环境变量: `DATA_QUALITY_LOG___TABLENAME___30`

- 行 33: `comment="日志记录唯一标识"`
  → `comment = os.getenv("DATA_QUALITY_LOG_COMMENT_33")`
  → 环境变量: `DATA_QUALITY_LOG_COMMENT_33`

- 行 34: `comment="出现问题的表名"`
  → `comment = os.getenv("DATA_QUALITY_LOG_COMMENT_34")`
  → 环境变量: `DATA_QUALITY_LOG_COMMENT_34`

- 行 35: `comment="出现问题的记录ID"`
  → `comment = os.getenv("DATA_QUALITY_LOG_COMMENT_35")`
  → 环境变量: `DATA_QUALITY_LOG_COMMENT_35`

- 行 40: `default="medium"`
  → `default = os.getenv("DATA_QUALITY_LOG_DEFAULT_40")`
  → 环境变量: `DATA_QUALITY_LOG_DEFAULT_40`

- 行 40: `comment="严重程度: low/medium/high/critical"`
  → `comment = os.getenv("DATA_QUALITY_LOG_COMMENT_40")`
  → 环境变量: `DATA_QUALITY_LOG_COMMENT_40`

- 行 42: `comment="错误数据和上下文信息"`
  → `comment = os.getenv("DATA_QUALITY_LOG_COMMENT_42")`
  → 环境变量: `DATA_QUALITY_LOG_COMMENT_42`

- 行 42: `comment="详细错误描述"`
  → `comment = os.getenv("DATA_QUALITY_LOG_COMMENT_42")`
  → 环境变量: `DATA_QUALITY_LOG_COMMENT_42`

- 行 46: `default="logged"`
  → `default = os.getenv("DATA_QUALITY_LOG_DEFAULT_46")`
  → 环境变量: `DATA_QUALITY_LOG_DEFAULT_46`

- 行 46: `comment="处理状态: logged/in_progress/resolved/ignored"`
  → `comment = os.getenv("DATA_QUALITY_LOG_COMMENT_46")`
  → 环境变量: `DATA_QUALITY_LOG_COMMENT_46`

- 行 50: `comment="是否需要人工审核"`
  → `comment = os.getenv("DATA_QUALITY_LOG_COMMENT_50")`
  → 环境变量: `DATA_QUALITY_LOG_COMMENT_50`

- 行 57: `comment="解决方案说明"`
  → `comment = os.getenv("DATA_QUALITY_LOG_COMMENT_57")`
  → 环境变量: `DATA_QUALITY_LOG_COMMENT_57`

- 行 103: `status = "resolved"`
  → `status = os.getenv("DATA_QUALITY_LOG_STATUS_103")`
  → 环境变量: `DATA_QUALITY_LOG_STATUS_103`

- 行 108: `status = "ignored"`
  → `status = os.getenv("DATA_QUALITY_LOG_STATUS_108")`
  → 环境变量: `DATA_QUALITY_LOG_STATUS_108`

- 行 113: `status = "in_progress"`
  → `status = os.getenv("DATA_QUALITY_LOG_STATUS_113")`
  → 环境变量: `DATA_QUALITY_LOG_STATUS_113`

- 行 136: `error_type="ge_validation_failed"`
  → `error_type = os.getenv("DATA_QUALITY_LOG_ERROR_TYPE_136")`
  → 环境变量: `DATA_QUALITY_LOG_ERROR_TYPE_136`

- 行 137: `severity="medium"`
  → `severity = os.getenv("DATA_QUALITY_LOG_SEVERITY_137")`
  → 环境变量: `DATA_QUALITY_LOG_SEVERITY_137`

- 行 150: `status="logged"`
  → `status = os.getenv("DATA_QUALITY_LOG_STATUS_150")`
  → 环境变量: `DATA_QUALITY_LOG_STATUS_150`

### src/database/models/features.py

- 行 33: `__tablename__ = "features"`
  → `__tablename__ = os.getenv("FEATURES___TABLENAME___33")`
  → 环境变量: `FEATURES___TABLENAME___33`

- 行 37: `ondelete="CASCADE"`
  → `ondelete = os.getenv("FEATURES_ONDELETE_37")`
  → 环境变量: `FEATURES_ONDELETE_37`

- 行 40: `ondelete="CASCADE"`
  → `ondelete = os.getenv("FEATURES_ONDELETE_40")`
  → 环境变量: `FEATURES_ONDELETE_40`

- 行 44: `comment="球队类型（主队/客队）"`
  → `comment = os.getenv("FEATURES_COMMENT_44")`
  → 环境变量: `FEATURES_COMMENT_44`

- 行 45: `comment="近5场胜利数"`
  → `comment = os.getenv("FEATURES_COMMENT_45")`
  → 环境变量: `FEATURES_COMMENT_45`

- 行 50: `comment="近5场平局数"`
  → `comment = os.getenv("FEATURES_COMMENT_50")`
  → 环境变量: `FEATURES_COMMENT_50`

- 行 54: `comment="近5场失败数"`
  → `comment = os.getenv("FEATURES_COMMENT_54")`
  → 环境变量: `FEATURES_COMMENT_54`

- 行 57: `comment="近5场进球数"`
  → `comment = os.getenv("FEATURES_COMMENT_57")`
  → 环境变量: `FEATURES_COMMENT_57`

- 行 61: `comment="近5场失球数"`
  → `comment = os.getenv("FEATURES_COMMENT_61")`
  → 环境变量: `FEATURES_COMMENT_61`

- 行 76: `comment="对战历史胜利数"`
  → `comment = os.getenv("FEATURES_COMMENT_76")`
  → 环境变量: `FEATURES_COMMENT_76`

- 行 78: `comment="对战历史平局数"`
  → `comment = os.getenv("FEATURES_COMMENT_78")`
  → 环境变量: `FEATURES_COMMENT_78`

- 行 80: `comment="对战历史失败数"`
  → `comment = os.getenv("FEATURES_COMMENT_80")`
  → 环境变量: `FEATURES_COMMENT_80`

- 行 83: `comment="对战历史进球数"`
  → `comment = os.getenv("FEATURES_COMMENT_83")`
  → 环境变量: `FEATURES_COMMENT_83`

- 行 85: `comment="对战历史失球数"`
  → `comment = os.getenv("FEATURES_COMMENT_85")`
  → 环境变量: `FEATURES_COMMENT_85`

- 行 87: `comment="当前联赛排名"`
  → `comment = os.getenv("FEATURES_COMMENT_87")`
  → 环境变量: `FEATURES_COMMENT_87`

- 行 91: `comment="距离上场比赛天数"`
  → `comment = os.getenv("FEATURES_COMMENT_91")`
  → 环境变量: `FEATURES_COMMENT_91`

- 行 94: `comment="是否为德比战"`
  → `comment = os.getenv("FEATURES_COMMENT_94")`
  → 环境变量: `FEATURES_COMMENT_94`

- 行 101: `comment="场均射门次数"`
  → `comment = os.getenv("FEATURES_COMMENT_101")`
  → 环境变量: `FEATURES_COMMENT_101`

- 行 108: `comment="场均射正次数"`
  → `comment = os.getenv("FEATURES_COMMENT_108")`
  → 环境变量: `FEATURES_COMMENT_108`

- 行 121: `comment="场均红黄牌数"`
  → `comment = os.getenv("FEATURES_COMMENT_121")`
  → 环境变量: `FEATURES_COMMENT_121`

- 行 125: `comment="当前状态（如 WWDLW）"`
  → `comment = os.getenv("FEATURES_COMMENT_125")`
  → 环境变量: `FEATURES_COMMENT_125`

- 行 132: `back_populates="features"`
  → `back_populates = os.getenv("FEATURES_BACK_POPULATES_132")`
  → 环境变量: `FEATURES_BACK_POPULATES_132`

- 行 134: `back_populates="features"`
  → `back_populates = os.getenv("FEATURES_BACK_POPULATES_134")`
  → 环境变量: `FEATURES_BACK_POPULATES_134`

- 行 145: `type='{self.team_type.value}'`
  → `type = os.getenv("FEATURES_TYPE_145")`
  → 环境变量: `FEATURES_TYPE_145`

### src/database/models/data_collection_log.py

- 行 23: `SUCCESS = "success"`
  → `SUCCESS = os.getenv("DATA_COLLECTION_LOG_SUCCESS_23")`
  → 环境变量: `DATA_COLLECTION_LOG_SUCCESS_23`

- 行 23: `FAILED = "failed"`
  → `FAILED = os.getenv("DATA_COLLECTION_LOG_FAILED_23")`
  → 环境变量: `DATA_COLLECTION_LOG_FAILED_23`

- 行 23: `PARTIAL = "partial"`
  → `PARTIAL = os.getenv("DATA_COLLECTION_LOG_PARTIAL_23")`
  → 环境变量: `DATA_COLLECTION_LOG_PARTIAL_23`

- 行 24: `RUNNING = "running"`
  → `RUNNING = os.getenv("DATA_COLLECTION_LOG_RUNNING_24")`
  → 环境变量: `DATA_COLLECTION_LOG_RUNNING_24`

- 行 25: `FIXTURES = "fixtures"`
  → `FIXTURES = os.getenv("DATA_COLLECTION_LOG_FIXTURES_25")`
  → 环境变量: `DATA_COLLECTION_LOG_FIXTURES_25`

- 行 26: `SCORES = "scores"`
  → `SCORES = os.getenv("DATA_COLLECTION_LOG_SCORES_26")`
  → 环境变量: `DATA_COLLECTION_LOG_SCORES_26`

- 行 26: `LIVE_SCORES = "live_scores"`
  → `LIVE_SCORES = os.getenv("DATA_COLLECTION_LOG_LIVE_SCORES_26")`
  → 环境变量: `DATA_COLLECTION_LOG_LIVE_SCORES_26`

- 行 34: `__tablename__ = "data_collection_logs"`
  → `__tablename__ = os.getenv("DATA_COLLECTION_LOG___TABLENAME___34")`
  → 环境变量: `DATA_COLLECTION_LOG___TABLENAME___34`

### src/database/models/predictions.py

- 行 25: `HOME_WIN = "home_win"`
  → `HOME_WIN = os.getenv("PREDICTIONS_HOME_WIN_25")`
  → 环境变量: `PREDICTIONS_HOME_WIN_25`

- 行 26: `AWAY_WIN = "away_win"`
  → `AWAY_WIN = os.getenv("PREDICTIONS_AWAY_WIN_26")`
  → 环境变量: `PREDICTIONS_AWAY_WIN_26`

- 行 31: `__tablename__ = "predictions"`
  → `__tablename__ = os.getenv("PREDICTIONS___TABLENAME___31")`
  → 环境变量: `PREDICTIONS___TABLENAME___31`

- 行 40: `ondelete="CASCADE"`
  → `ondelete = os.getenv("PREDICTIONS_ONDELETE_40")`
  → 环境变量: `PREDICTIONS_ONDELETE_40`

- 行 57: `comment="主队胜利概率"`
  → `comment = os.getenv("PREDICTIONS_COMMENT_57")`
  → 环境变量: `PREDICTIONS_COMMENT_57`

- 行 65: `comment="客队胜利概率"`
  → `comment = os.getenv("PREDICTIONS_COMMENT_65")`
  → 环境变量: `PREDICTIONS_COMMENT_65`

- 行 74: `comment="预测主队比分"`
  → `comment = os.getenv("PREDICTIONS_COMMENT_74")`
  → 环境变量: `PREDICTIONS_COMMENT_74`

- 行 78: `comment="预测客队比分"`
  → `comment = os.getenv("PREDICTIONS_COMMENT_78")`
  → 环境变量: `PREDICTIONS_COMMENT_78`

- 行 85: `comment="双方进球概率"`
  → `comment = os.getenv("PREDICTIONS_COMMENT_85")`
  → 环境变量: `PREDICTIONS_COMMENT_85`

- 行 95: `comment="实际比赛结果"`
  → `comment = os.getenv("PREDICTIONS_COMMENT_95")`
  → 环境变量: `PREDICTIONS_COMMENT_95`

- 行 100: `comment="预测是否正确"`
  → `comment = os.getenv("PREDICTIONS_COMMENT_100")`
  → 环境变量: `PREDICTIONS_COMMENT_100`

- 行 108: `comment="预测时使用的特征数据"`
  → `comment = os.getenv("PREDICTIONS_COMMENT_108")`
  → 环境变量: `PREDICTIONS_COMMENT_108`

- 行 112: `comment="预测相关的元数据"`
  → `comment = os.getenv("PREDICTIONS_COMMENT_112")`
  → 环境变量: `PREDICTIONS_COMMENT_112`

- 行 116: `back_populates="predictions"`
  → `back_populates = os.getenv("PREDICTIONS_BACK_POPULATES_116")`
  → 环境变量: `PREDICTIONS_BACK_POPULATES_116`

- 行 132: `model='{self.model_name}'`
  → `model = os.getenv("PREDICTIONS_MODEL_132")`
  → 环境变量: `PREDICTIONS_MODEL_132`

- 行 135: `result='{self.predicted_result.value}'`
  → `result = os.getenv("PREDICTIONS_RESULT_135")`
  → 环境变量: `PREDICTIONS_RESULT_135`

### src/database/models/raw_data.py

- 行 27: `__tablename__ = "raw_match_data"`
  → `__tablename__ = os.getenv("RAW_DATA___TABLENAME___27")`
  → 环境变量: `RAW_DATA___TABLENAME___27`

- 行 32: `comment="原始JSON/JSONB数据"`
  → `comment = os.getenv("RAW_DATA_COMMENT_32")`
  → 环境变量: `RAW_DATA_COMMENT_32`

- 行 39: `comment="外部比赛ID"`
  → `comment = os.getenv("RAW_DATA_COMMENT_39")`
  → 环境变量: `RAW_DATA_COMMENT_39`

- 行 39: `comment="外部联赛ID"`
  → `comment = os.getenv("RAW_DATA_COMMENT_39")`
  → 环境变量: `RAW_DATA_COMMENT_39`

- 行 101: `__tablename__ = "raw_odds_data"`
  → `__tablename__ = os.getenv("RAW_DATA___TABLENAME___101")`
  → 环境变量: `RAW_DATA___TABLENAME___101`

- 行 113: `comment="原始JSON/JSONB数据"`
  → `comment = os.getenv("RAW_DATA_COMMENT_113")`
  → 环境变量: `RAW_DATA_COMMENT_113`

- 行 118: `comment="外部比赛ID"`
  → `comment = os.getenv("RAW_DATA_COMMENT_118")`
  → 环境变量: `RAW_DATA_COMMENT_118`

- 行 178: `__tablename__ = "raw_scores_data"`
  → `__tablename__ = os.getenv("RAW_DATA___TABLENAME___178")`
  → 环境变量: `RAW_DATA___TABLENAME___178`

- 行 193: `comment="原始JSON/JSONB数据"`
  → `comment = os.getenv("RAW_DATA_COMMENT_193")`
  → 环境变量: `RAW_DATA_COMMENT_193`

- 行 199: `comment="外部比赛ID"`
  → `comment = os.getenv("RAW_DATA_COMMENT_199")`
  → 环境变量: `RAW_DATA_COMMENT_199`

### src/database/models/odds.py

- 行 24: `OVER_UNDER = "over_under"`
  → `OVER_UNDER = os.getenv("ODDS_OVER_UNDER_24")`
  → 环境变量: `ODDS_OVER_UNDER_24`

- 行 24: `ASIAN_HANDICAP = "asian_handicap"`
  → `ASIAN_HANDICAP = os.getenv("ODDS_ASIAN_HANDICAP_24")`
  → 环境变量: `ODDS_ASIAN_HANDICAP_24`

- 行 25: `BOTH_TEAMS_SCORE = "both_teams_score"`
  → `BOTH_TEAMS_SCORE = os.getenv("ODDS_BOTH_TEAMS_SCORE_25")`
  → 环境变量: `ODDS_BOTH_TEAMS_SCORE_25`

- 行 39: `ondelete="CASCADE"`
  → `ondelete = os.getenv("ODDS_ONDELETE_39")`
  → 环境变量: `ODDS_ONDELETE_39`

- 行 43: `comment="博彩公司名称"`
  → `comment = os.getenv("ODDS_COMMENT_43")`
  → 环境变量: `ODDS_COMMENT_43`

- 行 76: `comment="赔率收集时间"`
  → `comment = os.getenv("ODDS_COMMENT_76")`
  → 环境变量: `ODDS_COMMENT_76`

- 行 92: `name="ck_odds_home_odds_range"`
  → `name = os.getenv("ODDS_NAME_92")`
  → 环境变量: `ODDS_NAME_92`

- 行 95: `name="ck_odds_draw_odds_range"`
  → `name = os.getenv("ODDS_NAME_95")`
  → 环境变量: `ODDS_NAME_95`

- 行 98: `name="ck_odds_away_odds_range"`
  → `name = os.getenv("ODDS_NAME_98")`
  → 环境变量: `ODDS_NAME_98`

- 行 101: `name="ck_odds_over_odds_range"`
  → `name = os.getenv("ODDS_NAME_101")`
  → 环境变量: `ODDS_NAME_101`

- 行 104: `name="ck_odds_under_odds_range"`
  → `name = os.getenv("ODDS_NAME_104")`
  → 环境变量: `ODDS_NAME_104`

- 行 107: `name="ck_odds_line_value_range"`
  → `name = os.getenv("ODDS_NAME_107")`
  → 环境变量: `ODDS_NAME_107`

- 行 112: `bookmaker='{self.bookmaker}'`
  → `bookmaker = os.getenv("ODDS_BOOKMAKER_112")`
  → 环境变量: `ODDS_BOOKMAKER_112`

- 行 115: `market='{self.market_type.value}'`
  → `market = os.getenv("ODDS_MARKET_115")`
  → 环境变量: `ODDS_MARKET_115`

### src/database/models/team.py

- 行 34: `comment="API球队ID"`
  → `comment = os.getenv("TEAM_COMMENT_34")`
  → 环境变量: `TEAM_COMMENT_34`

- 行 38: `comment="所属联赛ID"`
  → `comment = os.getenv("TEAM_COMMENT_38")`
  → 环境变量: `TEAM_COMMENT_38`

- 行 44: `comment="主场体育场名称"`
  → `comment = os.getenv("TEAM_COMMENT_44")`
  → 环境变量: `TEAM_COMMENT_44`

- 行 54: `back_populates="home_team"`
  → `back_populates = os.getenv("TEAM_BACK_POPULATES_54")`
  → 环境变量: `TEAM_BACK_POPULATES_54`

- 行 55: `lazy="dynamic"`
  → `lazy = os.getenv("TEAM_LAZY_55")`
  → 环境变量: `TEAM_LAZY_55`

- 行 60: `back_populates="away_team"`
  → `back_populates = os.getenv("TEAM_BACK_POPULATES_60")`
  → 环境变量: `TEAM_BACK_POPULATES_60`

- 行 61: `lazy="dynamic"`
  → `lazy = os.getenv("TEAM_LAZY_61")`
  → 环境变量: `TEAM_LAZY_61`

- 行 64: `lazy="dynamic"`
  → `lazy = os.getenv("TEAM_LAZY_64")`
  → 环境变量: `TEAM_LAZY_64`

- 行 64: `cascade="all, delete-orphan"`
  → `cascade = os.getenv("TEAM_CASCADE_64")`
  → 环境变量: `TEAM_CASCADE_64`

- 行 75: `name='{self.team_name}'`
  → `name = os.getenv("TEAM_NAME_75")`
  → 环境变量: `TEAM_NAME_75`

- 行 76: `league='{self.league.league_name if self.league else None}'`
  → `league = os.getenv("TEAM_LEAGUE_76")`
  → 环境变量: `TEAM_LEAGUE_76`

### src/database/models/match.py

- 行 22: `SCHEDULED = "scheduled"`
  → `SCHEDULED = os.getenv("MATCH_SCHEDULED_22")`
  → 环境变量: `MATCH_SCHEDULED_22`

- 行 23: `FINISHED = "finished"`
  → `FINISHED = os.getenv("MATCH_FINISHED_23")`
  → 环境变量: `MATCH_FINISHED_23`

- 行 24: `CANCELLED = "cancelled"`
  → `CANCELLED = os.getenv("MATCH_CANCELLED_24")`
  → 环境变量: `MATCH_CANCELLED_24`

- 行 30: `__tablename__ = "matches"`
  → `__tablename__ = os.getenv("MATCH___TABLENAME___30")`
  → 环境变量: `MATCH___TABLENAME___30`

- 行 37: `ondelete="CASCADE"`
  → `ondelete = os.getenv("MATCH_ONDELETE_37")`
  → 环境变量: `MATCH_ONDELETE_37`

- 行 39: `ondelete="CASCADE"`
  → `ondelete = os.getenv("MATCH_ONDELETE_39")`
  → 环境变量: `MATCH_ONDELETE_39`

- 行 43: `ondelete="CASCADE"`
  → `ondelete = os.getenv("MATCH_ONDELETE_43")`
  → 环境变量: `MATCH_ONDELETE_43`

- 行 69: `comment="主队半场比分"`
  → `comment = os.getenv("MATCH_COMMENT_69")`
  → 环境变量: `MATCH_COMMENT_69`

- 行 73: `comment="客队半场比分"`
  → `comment = os.getenv("MATCH_COMMENT_73")`
  → 环境变量: `MATCH_COMMENT_73`

- 行 77: `comment="比赛进行时间（分钟）"`
  → `comment = os.getenv("MATCH_COMMENT_77")`
  → 环境变量: `MATCH_COMMENT_77`

- 行 91: `back_populates="home_matches"`
  → `back_populates = os.getenv("MATCH_BACK_POPULATES_91")`
  → 环境变量: `MATCH_BACK_POPULATES_91`

- 行 95: `back_populates="away_matches"`
  → `back_populates = os.getenv("MATCH_BACK_POPULATES_95")`
  → 环境变量: `MATCH_BACK_POPULATES_95`

- 行 100: `back_populates="matches"`
  → `back_populates = os.getenv("MATCH_BACK_POPULATES_100")`
  → 环境变量: `MATCH_BACK_POPULATES_100`

- 行 103: `lazy="dynamic"`
  → `lazy = os.getenv("MATCH_LAZY_103")`
  → 环境变量: `MATCH_LAZY_103`

- 行 103: `cascade="all, delete-orphan"`
  → `cascade = os.getenv("MATCH_CASCADE_103")`
  → 环境变量: `MATCH_CASCADE_103`

- 行 107: `lazy="dynamic"`
  → `lazy = os.getenv("MATCH_LAZY_107")`
  → 环境变量: `MATCH_LAZY_107`

- 行 107: `cascade="all, delete-orphan"`
  → `cascade = os.getenv("MATCH_CASCADE_107")`
  → 环境变量: `MATCH_CASCADE_107`

- 行 111: `lazy="dynamic"`
  → `lazy = os.getenv("MATCH_LAZY_111")`
  → 环境变量: `MATCH_LAZY_111`

- 行 111: `cascade="all, delete-orphan"`
  → `cascade = os.getenv("MATCH_CASCADE_111")`
  → 环境变量: `MATCH_CASCADE_111`

- 行 131: `name="ck_matches_home_score_range"`
  → `name = os.getenv("MATCH_NAME_131")`
  → 环境变量: `MATCH_NAME_131`

- 行 133: `name="ck_matches_away_score_range"`
  → `name = os.getenv("MATCH_NAME_133")`
  → 环境变量: `MATCH_NAME_133`

- 行 135: `name="ck_matches_home_ht_score_range"`
  → `name = os.getenv("MATCH_NAME_135")`
  → 环境变量: `MATCH_NAME_135`

- 行 138: `name="ck_matches_away_ht_score_range"`
  → `name = os.getenv("MATCH_NAME_138")`
  → 环境变量: `MATCH_NAME_138`

- 行 141: `name="ck_matches_match_time_range"`
  → `name = os.getenv("MATCH_NAME_141")`
  → 环境变量: `MATCH_NAME_141`

- 行 144: `name="ck_matches_different_teams"`
  → `name = os.getenv("MATCH_NAME_144")`
  → 环境变量: `MATCH_NAME_144`

- 行 148: `name="ck_matches_minute_range"`
  → `name = os.getenv("MATCH_NAME_148")`
  → 环境变量: `MATCH_NAME_148`

- 行 152: `home='{self.home_team.team_name if self.home_team else '`
  → `home = os.getenv("MATCH_HOME_152")`
  → 环境变量: `MATCH_HOME_152`

- 行 155: `away='{self.away_team.team_name if self.away_team else '`
  → `away = os.getenv("MATCH_AWAY_155")`
  → 环境变量: `MATCH_AWAY_155`

- 行 156: `date='{self.match_time}'`
  → `date = os.getenv("MATCH_DATE_156")`
  → 环境变量: `MATCH_DATE_156`

### src/database/migrations/env.py

- 行 156: `prefix="sqlalchemy."`
  → `prefix = os.getenv("ENV_PREFIX_156")`
  → 环境变量: `ENV_PREFIX_156`

### src/database/migrations/versions/d3bf28af22ff_add_performance_critical_indexes.py

- 行 24: `str = "d3bf28af22ff"`
  → `str = os.getenv("D3BF28AF22FF_ADD_PERFORMANCE_CRITICAL_INDEXES_STR_")`
  → 环境变量: `D3BF28AF22FF_ADD_PERFORMANCE_CRITICAL_INDEXES_STR_`

### src/database/migrations/versions/d6d814cc1078_database_performance_optimization_.py

- 行 23: `str = "d6d814cc1078"`
  → `str = os.getenv("D6D814CC1078_DATABASE_PERFORMANCE_OPTIMIZATION__ST")`
  → 环境变量: `D6D814CC1078_DATABASE_PERFORMANCE_OPTIMIZATION__ST`

- 行 309: `tablename = 'features'`
  → `tablename = os.getenv("D6D814CC1078_DATABASE_PERFORMANCE_OPTIMIZATION__TA")`
  → 环境变量: `D6D814CC1078_DATABASE_PERFORMANCE_OPTIMIZATION__TA`

- 行 310: `indexname = 'idx_features_match_team'`
  → `indexname = os.getenv("D6D814CC1078_DATABASE_PERFORMANCE_OPTIMIZATION__IN")`
  → 环境变量: `D6D814CC1078_DATABASE_PERFORMANCE_OPTIMIZATION__IN`

- 行 321: `tablename = 'features'`
  → `tablename = os.getenv("D6D814CC1078_DATABASE_PERFORMANCE_OPTIMIZATION__TA")`
  → 环境变量: `D6D814CC1078_DATABASE_PERFORMANCE_OPTIMIZATION__TA`

- 行 324: `indexname = 'idx_features_team_created'`
  → `indexname = os.getenv("D6D814CC1078_DATABASE_PERFORMANCE_OPTIMIZATION__IN")`
  → 环境变量: `D6D814CC1078_DATABASE_PERFORMANCE_OPTIMIZATION__IN`

- 行 348: `match_status = 'finished'`
  → `match_status = os.getenv("D6D814CC1078_DATABASE_PERFORMANCE_OPTIMIZATION__MA")`
  → 环境变量: `D6D814CC1078_DATABASE_PERFORMANCE_OPTIMIZATION__MA`

- 行 354: `match_status = 'finished'`
  → `match_status = os.getenv("D6D814CC1078_DATABASE_PERFORMANCE_OPTIMIZATION__MA")`
  → 环境变量: `D6D814CC1078_DATABASE_PERFORMANCE_OPTIMIZATION__MA`

- 行 356: `match_status = 'finished'`
  → `match_status = os.getenv("D6D814CC1078_DATABASE_PERFORMANCE_OPTIMIZATION__MA")`
  → 环境变量: `D6D814CC1078_DATABASE_PERFORMANCE_OPTIMIZATION__MA`

- 行 359: `match_status = 'finished'`
  → `match_status = os.getenv("D6D814CC1078_DATABASE_PERFORMANCE_OPTIMIZATION__MA")`
  → 环境变量: `D6D814CC1078_DATABASE_PERFORMANCE_OPTIMIZATION__MA`

- 行 361: `match_status = 'finished'`
  → `match_status = os.getenv("D6D814CC1078_DATABASE_PERFORMANCE_OPTIMIZATION__MA")`
  → 环境变量: `D6D814CC1078_DATABASE_PERFORMANCE_OPTIMIZATION__MA`

- 行 364: `match_status = 'finished'`
  → `match_status = os.getenv("D6D814CC1078_DATABASE_PERFORMANCE_OPTIMIZATION__MA")`
  → 环境变量: `D6D814CC1078_DATABASE_PERFORMANCE_OPTIMIZATION__MA`

- 行 367: `match_status = 'finished'`
  → `match_status = os.getenv("D6D814CC1078_DATABASE_PERFORMANCE_OPTIMIZATION__MA")`
  → 环境变量: `D6D814CC1078_DATABASE_PERFORMANCE_OPTIMIZATION__MA`

- 行 369: `match_status = 'finished'`
  → `match_status = os.getenv("D6D814CC1078_DATABASE_PERFORMANCE_OPTIMIZATION__MA")`
  → 环境变量: `D6D814CC1078_DATABASE_PERFORMANCE_OPTIMIZATION__MA`

- 行 374: `match_status = 'finished'`
  → `match_status = os.getenv("D6D814CC1078_DATABASE_PERFORMANCE_OPTIMIZATION__MA")`
  → 环境变量: `D6D814CC1078_DATABASE_PERFORMANCE_OPTIMIZATION__MA`

- 行 376: `match_status = 'finished'`
  → `match_status = os.getenv("D6D814CC1078_DATABASE_PERFORMANCE_OPTIMIZATION__MA")`
  → 环境变量: `D6D814CC1078_DATABASE_PERFORMANCE_OPTIMIZATION__MA`

- 行 470: `table_schema = 'public'`
  → `table_schema = os.getenv("D6D814CC1078_DATABASE_PERFORMANCE_OPTIMIZATION__TA")`
  → 环境变量: `D6D814CC1078_DATABASE_PERFORMANCE_OPTIMIZATION__TA`

### src/database/migrations/versions/09d03cebf664_implement_partitioned_tables_and_indexes.py

- 行 24: `str = "09d03cebf664"`
  → `str = os.getenv("09D03CEBF664_IMPLEMENT_PARTITIONED_TABLES_AND_INDE")`
  → 环境变量: `09D03CEBF664_IMPLEMENT_PARTITIONED_TABLES_AND_INDE`

- 行 154: `partrelid = 'matches'`
  → `partrelid = os.getenv("09D03CEBF664_IMPLEMENT_PARTITIONED_TABLES_AND_INDE")`
  → 环境变量: `09D03CEBF664_IMPLEMENT_PARTITIONED_TABLES_AND_INDE`

- 行 236: `match_status = 'finished'`
  → `match_status = os.getenv("09D03CEBF664_IMPLEMENT_PARTITIONED_TABLES_AND_INDE")`
  → 环境变量: `09D03CEBF664_IMPLEMENT_PARTITIONED_TABLES_AND_INDE`

### src/database/migrations/versions/006_add_missing_database_indexes.py

- 行 24: `str = "006_missing_indexes"`
  → `str = os.getenv("006_ADD_MISSING_DATABASE_INDEXES_STR_24")`
  → 环境变量: `006_ADD_MISSING_DATABASE_INDEXES_STR_24`

### src/database/migrations/versions/d82ea26f05d0_add_mlops_support_to_predictions_table.py

- 行 13: `revision = "d82ea26f05d0"`
  → `revision = os.getenv("D82EA26F05D0_ADD_MLOPS_SUPPORT_TO_PREDICTIONS_TABL")`
  → 环境变量: `D82EA26F05D0_ADD_MLOPS_SUPPORT_TO_PREDICTIONS_TABL`

- 行 13: `down_revision = "d6d814cc1078"`
  → `down_revision = os.getenv("D82EA26F05D0_ADD_MLOPS_SUPPORT_TO_PREDICTIONS_TABL")`
  → 环境变量: `D82EA26F05D0_ADD_MLOPS_SUPPORT_TO_PREDICTIONS_TABL`

- 行 24: `comment="实际比赛结果"`
  → `comment = os.getenv("D82EA26F05D0_ADD_MLOPS_SUPPORT_TO_PREDICTIONS_TABL")`
  → 环境变量: `D82EA26F05D0_ADD_MLOPS_SUPPORT_TO_PREDICTIONS_TABL`

- 行 26: `comment="预测是否正确"`
  → `comment = os.getenv("D82EA26F05D0_ADD_MLOPS_SUPPORT_TO_PREDICTIONS_TABL")`
  → 环境变量: `D82EA26F05D0_ADD_MLOPS_SUPPORT_TO_PREDICTIONS_TABL`

- 行 35: `comment="预测时使用的特征数据"`
  → `comment = os.getenv("D82EA26F05D0_ADD_MLOPS_SUPPORT_TO_PREDICTIONS_TABL")`
  → 环境变量: `D82EA26F05D0_ADD_MLOPS_SUPPORT_TO_PREDICTIONS_TABL`

- 行 42: `comment="预测相关的元数据"`
  → `comment = os.getenv("D82EA26F05D0_ADD_MLOPS_SUPPORT_TO_PREDICTIONS_TABL")`
  → 环境变量: `D82EA26F05D0_ADD_MLOPS_SUPPORT_TO_PREDICTIONS_TABL`

- 行 52: `table_name="predictions"`
  → `table_name = os.getenv("D82EA26F05D0_ADD_MLOPS_SUPPORT_TO_PREDICTIONS_TABL")`
  → 环境变量: `D82EA26F05D0_ADD_MLOPS_SUPPORT_TO_PREDICTIONS_TABL`

- 行 54: `table_name="predictions"`
  → `table_name = os.getenv("D82EA26F05D0_ADD_MLOPS_SUPPORT_TO_PREDICTIONS_TABL")`
  → 环境变量: `D82EA26F05D0_ADD_MLOPS_SUPPORT_TO_PREDICTIONS_TABL`

### src/database/migrations/versions/a20f91c49306_add_business_constraints.py

- 行 21: `str = "a20f91c49306"`
  → `str = os.getenv("A20F91C49306_ADD_BUSINESS_CONSTRAINTS_STR_21")`
  → 环境变量: `A20F91C49306_ADD_BUSINESS_CONSTRAINTS_STR_21`

### src/database/migrations/versions/f48d412852cc_add_data_collection_logs_and_bronze_layer_tables.py

- 行 16: `str = "f48d412852cc"`
  → `str = os.getenv("F48D412852CC_ADD_DATA_COLLECTION_LOGS_AND_BRONZE_L")`
  → 环境变量: `F48D412852CC_ADD_DATA_COLLECTION_LOGS_AND_BRONZE_L`

- 行 41: `comment="采集类型(fixtures/odds/scores)"`
  → `comment = os.getenv("F48D412852CC_ADD_DATA_COLLECTION_LOGS_AND_BRONZE_L")`
  → 环境变量: `F48D412852CC_ADD_DATA_COLLECTION_LOGS_AND_BRONZE_L`

- 行 61: `comment="状态(success/failed/partial)"`
  → `comment = os.getenv("F48D412852CC_ADD_DATA_COLLECTION_LOGS_AND_BRONZE_L")`
  → 环境变量: `F48D412852CC_ADD_DATA_COLLECTION_LOGS_AND_BRONZE_L`

- 行 67: `comment="数据采集日志表"`
  → `comment = os.getenv("F48D412852CC_ADD_DATA_COLLECTION_LOGS_AND_BRONZE_L")`
  → 环境变量: `F48D412852CC_ADD_DATA_COLLECTION_LOGS_AND_BRONZE_L`

- 行 86: `comment="原始JSON数据"`
  → `comment = os.getenv("F48D412852CC_ADD_DATA_COLLECTION_LOGS_AND_BRONZE_L")`
  → 环境变量: `F48D412852CC_ADD_DATA_COLLECTION_LOGS_AND_BRONZE_L`

- 行 94: `comment="外部比赛ID"`
  → `comment = os.getenv("F48D412852CC_ADD_DATA_COLLECTION_LOGS_AND_BRONZE_L")`
  → 环境变量: `F48D412852CC_ADD_DATA_COLLECTION_LOGS_AND_BRONZE_L`

- 行 100: `comment="外部联赛ID"`
  → `comment = os.getenv("F48D412852CC_ADD_DATA_COLLECTION_LOGS_AND_BRONZE_L")`
  → 环境变量: `F48D412852CC_ADD_DATA_COLLECTION_LOGS_AND_BRONZE_L`

- 行 107: `comment="Bronze层原始比赛数据表"`
  → `comment = os.getenv("F48D412852CC_ADD_DATA_COLLECTION_LOGS_AND_BRONZE_L")`
  → 环境变量: `F48D412852CC_ADD_DATA_COLLECTION_LOGS_AND_BRONZE_L`

- 行 128: `comment="外部比赛ID"`
  → `comment = os.getenv("F48D412852CC_ADD_DATA_COLLECTION_LOGS_AND_BRONZE_L")`
  → 环境变量: `F48D412852CC_ADD_DATA_COLLECTION_LOGS_AND_BRONZE_L`

- 行 137: `comment="原始JSON数据"`
  → `comment = os.getenv("F48D412852CC_ADD_DATA_COLLECTION_LOGS_AND_BRONZE_L")`
  → 环境变量: `F48D412852CC_ADD_DATA_COLLECTION_LOGS_AND_BRONZE_L`

- 行 147: `comment="Bronze层原始赔率数据表"`
  → `comment = os.getenv("F48D412852CC_ADD_DATA_COLLECTION_LOGS_AND_BRONZE_L")`
  → 环境变量: `F48D412852CC_ADD_DATA_COLLECTION_LOGS_AND_BRONZE_L`

- 行 223: `table_name="raw_odds_data"`
  → `table_name = os.getenv("F48D412852CC_ADD_DATA_COLLECTION_LOGS_AND_BRONZE_L")`
  → 环境变量: `F48D412852CC_ADD_DATA_COLLECTION_LOGS_AND_BRONZE_L`

- 行 225: `table_name="raw_odds_data"`
  → `table_name = os.getenv("F48D412852CC_ADD_DATA_COLLECTION_LOGS_AND_BRONZE_L")`
  → 环境变量: `F48D412852CC_ADD_DATA_COLLECTION_LOGS_AND_BRONZE_L`

- 行 230: `table_name="raw_odds_data"`
  → `table_name = os.getenv("F48D412852CC_ADD_DATA_COLLECTION_LOGS_AND_BRONZE_L")`
  → 环境变量: `F48D412852CC_ADD_DATA_COLLECTION_LOGS_AND_BRONZE_L`

- 行 231: `table_name="raw_odds_data"`
  → `table_name = os.getenv("F48D412852CC_ADD_DATA_COLLECTION_LOGS_AND_BRONZE_L")`
  → 环境变量: `F48D412852CC_ADD_DATA_COLLECTION_LOGS_AND_BRONZE_L`

- 行 233: `table_name="raw_odds_data"`
  → `table_name = os.getenv("F48D412852CC_ADD_DATA_COLLECTION_LOGS_AND_BRONZE_L")`
  → 环境变量: `F48D412852CC_ADD_DATA_COLLECTION_LOGS_AND_BRONZE_L`

- 行 236: `table_name="raw_match_data"`
  → `table_name = os.getenv("F48D412852CC_ADD_DATA_COLLECTION_LOGS_AND_BRONZE_L")`
  → 环境变量: `F48D412852CC_ADD_DATA_COLLECTION_LOGS_AND_BRONZE_L`

- 行 239: `table_name="raw_match_data"`
  → `table_name = os.getenv("F48D412852CC_ADD_DATA_COLLECTION_LOGS_AND_BRONZE_L")`
  → 环境变量: `F48D412852CC_ADD_DATA_COLLECTION_LOGS_AND_BRONZE_L`

- 行 239: `table_name="raw_match_data"`
  → `table_name = os.getenv("F48D412852CC_ADD_DATA_COLLECTION_LOGS_AND_BRONZE_L")`
  → 环境变量: `F48D412852CC_ADD_DATA_COLLECTION_LOGS_AND_BRONZE_L`

- 行 240: `table_name="raw_match_data"`
  → `table_name = os.getenv("F48D412852CC_ADD_DATA_COLLECTION_LOGS_AND_BRONZE_L")`
  → 环境变量: `F48D412852CC_ADD_DATA_COLLECTION_LOGS_AND_BRONZE_L`

- 行 240: `table_name="raw_match_data"`
  → `table_name = os.getenv("F48D412852CC_ADD_DATA_COLLECTION_LOGS_AND_BRONZE_L")`
  → 环境变量: `F48D412852CC_ADD_DATA_COLLECTION_LOGS_AND_BRONZE_L`

- 行 242: `table_name="data_collection_logs"`
  → `table_name = os.getenv("F48D412852CC_ADD_DATA_COLLECTION_LOGS_AND_BRONZE_L")`
  → 环境变量: `F48D412852CC_ADD_DATA_COLLECTION_LOGS_AND_BRONZE_L`

- 行 242: `table_name="data_collection_logs"`
  → `table_name = os.getenv("F48D412852CC_ADD_DATA_COLLECTION_LOGS_AND_BRONZE_L")`
  → 环境变量: `F48D412852CC_ADD_DATA_COLLECTION_LOGS_AND_BRONZE_L`

- 行 243: `table_name="data_collection_logs"`
  → `table_name = os.getenv("F48D412852CC_ADD_DATA_COLLECTION_LOGS_AND_BRONZE_L")`
  → 环境变量: `F48D412852CC_ADD_DATA_COLLECTION_LOGS_AND_BRONZE_L`

### src/database/migrations/versions/c1d8ae5075f0_add_jsonb_sqlite_compatibility.py

- 行 25: `str = "c1d8ae5075f0"`
  → `str = os.getenv("C1D8AE5075F0_ADD_JSONB_SQLITE_COMPATIBILITY_STR_25")`
  → 环境变量: `C1D8AE5075F0_ADD_JSONB_SQLITE_COMPATIBILITY_STR_25`

### src/database/migrations/versions/9ac2aff86228_merge_multiple_migration_heads.py

- 行 12: `str = "9ac2aff86228"`
  → `str = os.getenv("9AC2AFF86228_MERGE_MULTIPLE_MIGRATION_HEADS_STR_12")`
  → 环境变量: `9AC2AFF86228_MERGE_MULTIPLE_MIGRATION_HEADS_STR_12`

### src/database/migrations/versions/004_configure_database_permissions.py

- 行 21: `revision = "004_configure_permissions"`
  → `revision = os.getenv("004_CONFIGURE_DATABASE_PERMISSIONS_REVISION_21")`
  → 环境变量: `004_CONFIGURE_DATABASE_PERMISSIONS_REVISION_21`

- 行 21: `down_revision = "f48d412852cc"`
  → `down_revision = os.getenv("004_CONFIGURE_DATABASE_PERMISSIONS_DOWN_REVISION_2")`
  → 环境变量: `004_CONFIGURE_DATABASE_PERMISSIONS_DOWN_REVISION_2`

- 行 54: `usename = 'football_reader'`
  → `usename = os.getenv("004_CONFIGURE_DATABASE_PERMISSIONS_USENAME_54")`
  → 环境变量: `004_CONFIGURE_DATABASE_PERMISSIONS_USENAME_54`

- 行 66: `usename = 'football_writer'`
  → `usename = os.getenv("004_CONFIGURE_DATABASE_PERMISSIONS_USENAME_66")`
  → 环境变量: `004_CONFIGURE_DATABASE_PERMISSIONS_USENAME_66`

- 行 78: `usename = 'football_admin'`
  → `usename = os.getenv("004_CONFIGURE_DATABASE_PERMISSIONS_USENAME_78")`
  → 环境变量: `004_CONFIGURE_DATABASE_PERMISSIONS_USENAME_78`

- 行 232: `usename = 'football_reader'`
  → `usename = os.getenv("004_CONFIGURE_DATABASE_PERMISSIONS_USENAME_232")`
  → 环境变量: `004_CONFIGURE_DATABASE_PERMISSIONS_USENAME_232`

- 行 234: `usename = 'football_writer'`
  → `usename = os.getenv("004_CONFIGURE_DATABASE_PERMISSIONS_USENAME_234")`
  → 环境变量: `004_CONFIGURE_DATABASE_PERMISSIONS_USENAME_234`

- 行 237: `usename = 'football_admin'`
  → `usename = os.getenv("004_CONFIGURE_DATABASE_PERMISSIONS_USENAME_237")`
  → 环境变量: `004_CONFIGURE_DATABASE_PERMISSIONS_USENAME_237`

- 行 257: `table_schema = 'public'`
  → `table_schema = os.getenv("004_CONFIGURE_DATABASE_PERMISSIONS_TABLE_SCHEMA_25")`
  → 环境变量: `004_CONFIGURE_DATABASE_PERMISSIONS_TABLE_SCHEMA_25`

- 行 281: `privilege_type = 'SELECT'`
  → `privilege_type = os.getenv("004_CONFIGURE_DATABASE_PERMISSIONS_PRIVILEGE_TYPE_")`
  → 环境变量: `004_CONFIGURE_DATABASE_PERMISSIONS_PRIVILEGE_TYPE_`

- 行 282: `privilege_type = 'INSERT'`
  → `privilege_type = os.getenv("004_CONFIGURE_DATABASE_PERMISSIONS_PRIVILEGE_TYPE_")`
  → 环境变量: `004_CONFIGURE_DATABASE_PERMISSIONS_PRIVILEGE_TYPE_`

- 行 284: `privilege_type = 'UPDATE'`
  → `privilege_type = os.getenv("004_CONFIGURE_DATABASE_PERMISSIONS_PRIVILEGE_TYPE_")`
  → 环境变量: `004_CONFIGURE_DATABASE_PERMISSIONS_PRIVILEGE_TYPE_`

- 行 286: `privilege_type = 'DELETE'`
  → `privilege_type = os.getenv("004_CONFIGURE_DATABASE_PERMISSIONS_PRIVILEGE_TYPE_")`
  → 环境变量: `004_CONFIGURE_DATABASE_PERMISSIONS_PRIVILEGE_TYPE_`

- 行 293: `table_schema = 'public'`
  → `table_schema = os.getenv("004_CONFIGURE_DATABASE_PERMISSIONS_TABLE_SCHEMA_29")`
  → 环境变量: `004_CONFIGURE_DATABASE_PERMISSIONS_TABLE_SCHEMA_29`

- 行 294: `table_type = 'BASE TABLE'`
  → `table_type = os.getenv("004_CONFIGURE_DATABASE_PERMISSIONS_TABLE_TYPE_294")`
  → 环境变量: `004_CONFIGURE_DATABASE_PERMISSIONS_TABLE_TYPE_294`

### src/database/migrations/versions/002_add_raw_scores_data_and_upgrade_jsonb.py

- 行 17: `str = "002_add_raw_scores_data_and_upgrade_jsonb"`
  → `str = os.getenv("002_ADD_RAW_SCORES_DATA_AND_UPGRADE_JSONB_STR_17")`
  → 环境变量: `002_ADD_RAW_SCORES_DATA_AND_UPGRADE_JSONB_STR_17`

- 行 44: `comment="原始JSONB数据"`
  → `comment = os.getenv("002_ADD_RAW_SCORES_DATA_AND_UPGRADE_JSONB_COMMENT_")`
  → 环境变量: `002_ADD_RAW_SCORES_DATA_AND_UPGRADE_JSONB_COMMENT_`

- 行 58: `comment="外部比赛ID"`
  → `comment = os.getenv("002_ADD_RAW_SCORES_DATA_AND_UPGRADE_JSONB_COMMENT_")`
  → 环境变量: `002_ADD_RAW_SCORES_DATA_AND_UPGRADE_JSONB_COMMENT_`

- 行 69: `comment="Bronze层原始比分数据表"`
  → `comment = os.getenv("002_ADD_RAW_SCORES_DATA_AND_UPGRADE_JSONB_COMMENT_")`
  → 环境变量: `002_ADD_RAW_SCORES_DATA_AND_UPGRADE_JSONB_COMMENT_`

- 行 201: `table_name="raw_scores_data"`
  → `table_name = os.getenv("002_ADD_RAW_SCORES_DATA_AND_UPGRADE_JSONB_TABLE_NA")`
  → 环境变量: `002_ADD_RAW_SCORES_DATA_AND_UPGRADE_JSONB_TABLE_NA`

- 行 202: `table_name="raw_scores_data"`
  → `table_name = os.getenv("002_ADD_RAW_SCORES_DATA_AND_UPGRADE_JSONB_TABLE_NA")`
  → 环境变量: `002_ADD_RAW_SCORES_DATA_AND_UPGRADE_JSONB_TABLE_NA`

- 行 205: `table_name="raw_scores_data"`
  → `table_name = os.getenv("002_ADD_RAW_SCORES_DATA_AND_UPGRADE_JSONB_TABLE_NA")`
  → 环境变量: `002_ADD_RAW_SCORES_DATA_AND_UPGRADE_JSONB_TABLE_NA`

- 行 205: `table_name="raw_scores_data"`
  → `table_name = os.getenv("002_ADD_RAW_SCORES_DATA_AND_UPGRADE_JSONB_TABLE_NA")`
  → 环境变量: `002_ADD_RAW_SCORES_DATA_AND_UPGRADE_JSONB_TABLE_NA`

- 行 206: `table_name="raw_scores_data"`
  → `table_name = os.getenv("002_ADD_RAW_SCORES_DATA_AND_UPGRADE_JSONB_TABLE_NA")`
  → 环境变量: `002_ADD_RAW_SCORES_DATA_AND_UPGRADE_JSONB_TABLE_NA`

- 行 207: `table_name="raw_scores_data"`
  → `table_name = os.getenv("002_ADD_RAW_SCORES_DATA_AND_UPGRADE_JSONB_TABLE_NA")`
  → 环境变量: `002_ADD_RAW_SCORES_DATA_AND_UPGRADE_JSONB_TABLE_NA`

- 行 207: `table_name="raw_scores_data"`
  → `table_name = os.getenv("002_ADD_RAW_SCORES_DATA_AND_UPGRADE_JSONB_TABLE_NA")`
  → 环境变量: `002_ADD_RAW_SCORES_DATA_AND_UPGRADE_JSONB_TABLE_NA`

- 行 210: `table_name="raw_match_data"`
  → `table_name = os.getenv("002_ADD_RAW_SCORES_DATA_AND_UPGRADE_JSONB_TABLE_NA")`
  → 环境变量: `002_ADD_RAW_SCORES_DATA_AND_UPGRADE_JSONB_TABLE_NA`

- 行 211: `table_name="raw_odds_data"`
  → `table_name = os.getenv("002_ADD_RAW_SCORES_DATA_AND_UPGRADE_JSONB_TABLE_NA")`
  → 环境变量: `002_ADD_RAW_SCORES_DATA_AND_UPGRADE_JSONB_TABLE_NA`

### src/database/migrations/versions/d56c8d0d5aa0_initial_database_schema.py

- 行 16: `str = "d56c8d0d5aa0"`
  → `str = os.getenv("D56C8D0D5AA0_INITIAL_DATABASE_SCHEMA_STR_16")`
  → 环境变量: `D56C8D0D5AA0_INITIAL_DATABASE_SCHEMA_STR_16`

- 行 35: `comment="API联赛ID"`
  → `comment = os.getenv("D56C8D0D5AA0_INITIAL_DATABASE_SCHEMA_COMMENT_35")`
  → 环境变量: `D56C8D0D5AA0_INITIAL_DATABASE_SCHEMA_COMMENT_35`

- 行 35: `comment="赛季开始月份"`
  → `comment = os.getenv("D56C8D0D5AA0_INITIAL_DATABASE_SCHEMA_COMMENT_35")`
  → 环境变量: `D56C8D0D5AA0_INITIAL_DATABASE_SCHEMA_COMMENT_35`

- 行 37: `comment="赛季结束月份"`
  → `comment = os.getenv("D56C8D0D5AA0_INITIAL_DATABASE_SCHEMA_COMMENT_37")`
  → 环境变量: `D56C8D0D5AA0_INITIAL_DATABASE_SCHEMA_COMMENT_37`

- 行 61: `comment="API球队ID"`
  → `comment = os.getenv("D56C8D0D5AA0_INITIAL_DATABASE_SCHEMA_COMMENT_61")`
  → 环境变量: `D56C8D0D5AA0_INITIAL_DATABASE_SCHEMA_COMMENT_61`

- 行 62: `comment="所属联赛ID"`
  → `comment = os.getenv("D56C8D0D5AA0_INITIAL_DATABASE_SCHEMA_COMMENT_62")`
  → 环境变量: `D56C8D0D5AA0_INITIAL_DATABASE_SCHEMA_COMMENT_62`

- 行 79: `comment="主场球队ID"`
  → `comment = os.getenv("D56C8D0D5AA0_INITIAL_DATABASE_SCHEMA_COMMENT_79")`
  → 环境变量: `D56C8D0D5AA0_INITIAL_DATABASE_SCHEMA_COMMENT_79`

- 行 80: `comment="客场球队ID"`
  → `comment = os.getenv("D56C8D0D5AA0_INITIAL_DATABASE_SCHEMA_COMMENT_80")`
  → 环境变量: `D56C8D0D5AA0_INITIAL_DATABASE_SCHEMA_COMMENT_80`

- 行 86: `comment="比赛日期时间"`
  → `comment = os.getenv("D56C8D0D5AA0_INITIAL_DATABASE_SCHEMA_COMMENT_86")`
  → 环境变量: `D56C8D0D5AA0_INITIAL_DATABASE_SCHEMA_COMMENT_86`

- 行 87: `name="matchstatus"`
  → `name = os.getenv("D56C8D0D5AA0_INITIAL_DATABASE_SCHEMA_NAME_87")`
  → 环境变量: `D56C8D0D5AA0_INITIAL_DATABASE_SCHEMA_NAME_87`

- 行 87: `default="scheduled"`
  → `default = os.getenv("D56C8D0D5AA0_INITIAL_DATABASE_SCHEMA_DEFAULT_87")`
  → 环境变量: `D56C8D0D5AA0_INITIAL_DATABASE_SCHEMA_DEFAULT_87`

- 行 90: `comment="主队半场得分"`
  → `comment = os.getenv("D56C8D0D5AA0_INITIAL_DATABASE_SCHEMA_COMMENT_90")`
  → 环境变量: `D56C8D0D5AA0_INITIAL_DATABASE_SCHEMA_COMMENT_90`

- 行 93: `comment="客队半场得分"`
  → `comment = os.getenv("D56C8D0D5AA0_INITIAL_DATABASE_SCHEMA_COMMENT_93")`
  → 环境变量: `D56C8D0D5AA0_INITIAL_DATABASE_SCHEMA_COMMENT_93`

- 行 116: `comment="博彩公司名称"`
  → `comment = os.getenv("D56C8D0D5AA0_INITIAL_DATABASE_SCHEMA_COMMENT_116")`
  → 环境变量: `D56C8D0D5AA0_INITIAL_DATABASE_SCHEMA_COMMENT_116`

- 行 120: `name="markettype"`
  → `name = os.getenv("D56C8D0D5AA0_INITIAL_DATABASE_SCHEMA_NAME_120")`
  → 环境变量: `D56C8D0D5AA0_INITIAL_DATABASE_SCHEMA_NAME_120`

- 行 122: `comment="赔率市场类型"`
  → `comment = os.getenv("D56C8D0D5AA0_INITIAL_DATABASE_SCHEMA_COMMENT_122")`
  → 环境变量: `D56C8D0D5AA0_INITIAL_DATABASE_SCHEMA_COMMENT_122`

- 行 153: `comment="赔率收集时间"`
  → `comment = os.getenv("D56C8D0D5AA0_INITIAL_DATABASE_SCHEMA_COMMENT_153")`
  → 环境变量: `D56C8D0D5AA0_INITIAL_DATABASE_SCHEMA_COMMENT_153`

- 行 185: `name="teamtype"`
  → `name = os.getenv("D56C8D0D5AA0_INITIAL_DATABASE_SCHEMA_NAME_185")`
  → 环境变量: `D56C8D0D5AA0_INITIAL_DATABASE_SCHEMA_NAME_185`

- 行 190: `comment="最近5场胜利场次"`
  → `comment = os.getenv("D56C8D0D5AA0_INITIAL_DATABASE_SCHEMA_COMMENT_190")`
  → 环境变量: `D56C8D0D5AA0_INITIAL_DATABASE_SCHEMA_COMMENT_190`

- 行 192: `comment="最近5场平局场次"`
  → `comment = os.getenv("D56C8D0D5AA0_INITIAL_DATABASE_SCHEMA_COMMENT_192")`
  → 环境变量: `D56C8D0D5AA0_INITIAL_DATABASE_SCHEMA_COMMENT_192`

- 行 197: `comment="最近5场失败场次"`
  → `comment = os.getenv("D56C8D0D5AA0_INITIAL_DATABASE_SCHEMA_COMMENT_197")`
  → 环境变量: `D56C8D0D5AA0_INITIAL_DATABASE_SCHEMA_COMMENT_197`

- 行 200: `comment="最近5场进球数"`
  → `comment = os.getenv("D56C8D0D5AA0_INITIAL_DATABASE_SCHEMA_COMMENT_200")`
  → 环境变量: `D56C8D0D5AA0_INITIAL_DATABASE_SCHEMA_COMMENT_200`

- 行 203: `comment="最近5场失球数"`
  → `comment = os.getenv("D56C8D0D5AA0_INITIAL_DATABASE_SCHEMA_COMMENT_203")`
  → 环境变量: `D56C8D0D5AA0_INITIAL_DATABASE_SCHEMA_COMMENT_203`

- 行 208: `comment="主场胜利场次"`
  → `comment = os.getenv("D56C8D0D5AA0_INITIAL_DATABASE_SCHEMA_COMMENT_208")`
  → 环境变量: `D56C8D0D5AA0_INITIAL_DATABASE_SCHEMA_COMMENT_208`

- 行 213: `comment="主场平局场次"`
  → `comment = os.getenv("D56C8D0D5AA0_INITIAL_DATABASE_SCHEMA_COMMENT_213")`
  → 环境变量: `D56C8D0D5AA0_INITIAL_DATABASE_SCHEMA_COMMENT_213`

- 行 219: `comment="主场失败场次"`
  → `comment = os.getenv("D56C8D0D5AA0_INITIAL_DATABASE_SCHEMA_COMMENT_219")`
  → 环境变量: `D56C8D0D5AA0_INITIAL_DATABASE_SCHEMA_COMMENT_219`

- 行 222: `comment="客场胜利场次"`
  → `comment = os.getenv("D56C8D0D5AA0_INITIAL_DATABASE_SCHEMA_COMMENT_222")`
  → 环境变量: `D56C8D0D5AA0_INITIAL_DATABASE_SCHEMA_COMMENT_222`

- 行 227: `comment="客场平局场次"`
  → `comment = os.getenv("D56C8D0D5AA0_INITIAL_DATABASE_SCHEMA_COMMENT_227")`
  → 环境变量: `D56C8D0D5AA0_INITIAL_DATABASE_SCHEMA_COMMENT_227`

- 行 233: `comment="客场失败场次"`
  → `comment = os.getenv("D56C8D0D5AA0_INITIAL_DATABASE_SCHEMA_COMMENT_233")`
  → 环境变量: `D56C8D0D5AA0_INITIAL_DATABASE_SCHEMA_COMMENT_233`

- 行 238: `comment="历史交锋胜利场次"`
  → `comment = os.getenv("D56C8D0D5AA0_INITIAL_DATABASE_SCHEMA_COMMENT_238")`
  → 环境变量: `D56C8D0D5AA0_INITIAL_DATABASE_SCHEMA_COMMENT_238`

- 行 243: `comment="历史交锋平局场次"`
  → `comment = os.getenv("D56C8D0D5AA0_INITIAL_DATABASE_SCHEMA_COMMENT_243")`
  → 环境变量: `D56C8D0D5AA0_INITIAL_DATABASE_SCHEMA_COMMENT_243`

- 行 245: `comment="历史交锋失败场次"`
  → `comment = os.getenv("D56C8D0D5AA0_INITIAL_DATABASE_SCHEMA_COMMENT_245")`
  → 环境变量: `D56C8D0D5AA0_INITIAL_DATABASE_SCHEMA_COMMENT_245`

- 行 252: `comment="历史交锋进球数"`
  → `comment = os.getenv("D56C8D0D5AA0_INITIAL_DATABASE_SCHEMA_COMMENT_252")`
  → 环境变量: `D56C8D0D5AA0_INITIAL_DATABASE_SCHEMA_COMMENT_252`

- 行 258: `comment="历史交锋失球数"`
  → `comment = os.getenv("D56C8D0D5AA0_INITIAL_DATABASE_SCHEMA_COMMENT_258")`
  → 环境变量: `D56C8D0D5AA0_INITIAL_DATABASE_SCHEMA_COMMENT_258`

- 行 269: `comment="距离上场比赛天数"`
  → `comment = os.getenv("D56C8D0D5AA0_INITIAL_DATABASE_SCHEMA_COMMENT_269")`
  → 环境变量: `D56C8D0D5AA0_INITIAL_DATABASE_SCHEMA_COMMENT_269`

- 行 274: `comment="是否为德比战"`
  → `comment = os.getenv("D56C8D0D5AA0_INITIAL_DATABASE_SCHEMA_COMMENT_274")`
  → 环境变量: `D56C8D0D5AA0_INITIAL_DATABASE_SCHEMA_COMMENT_274`

- 行 284: `comment="场均射门次数"`
  → `comment = os.getenv("D56C8D0D5AA0_INITIAL_DATABASE_SCHEMA_COMMENT_284")`
  → 环境变量: `D56C8D0D5AA0_INITIAL_DATABASE_SCHEMA_COMMENT_284`

- 行 296: `comment="场均射正次数"`
  → `comment = os.getenv("D56C8D0D5AA0_INITIAL_DATABASE_SCHEMA_COMMENT_296")`
  → 环境变量: `D56C8D0D5AA0_INITIAL_DATABASE_SCHEMA_COMMENT_296`

- 行 360: `name="predictedresult"`
  → `name = os.getenv("D56C8D0D5AA0_INITIAL_DATABASE_SCHEMA_NAME_360")`
  → 环境变量: `D56C8D0D5AA0_INITIAL_DATABASE_SCHEMA_NAME_360`

- 行 363: `comment="预测的比赛结果"`
  → `comment = os.getenv("D56C8D0D5AA0_INITIAL_DATABASE_SCHEMA_COMMENT_363")`
  → 环境变量: `D56C8D0D5AA0_INITIAL_DATABASE_SCHEMA_COMMENT_363`

- 行 369: `comment="主队获胜概率"`
  → `comment = os.getenv("D56C8D0D5AA0_INITIAL_DATABASE_SCHEMA_COMMENT_369")`
  → 环境变量: `D56C8D0D5AA0_INITIAL_DATABASE_SCHEMA_COMMENT_369`

- 行 382: `comment="客队获胜概率"`
  → `comment = os.getenv("D56C8D0D5AA0_INITIAL_DATABASE_SCHEMA_COMMENT_382")`
  → 环境变量: `D56C8D0D5AA0_INITIAL_DATABASE_SCHEMA_COMMENT_382`

- 行 386: `comment="预测主队得分"`
  → `comment = os.getenv("D56C8D0D5AA0_INITIAL_DATABASE_SCHEMA_COMMENT_386")`
  → 环境变量: `D56C8D0D5AA0_INITIAL_DATABASE_SCHEMA_COMMENT_386`

- 行 393: `comment="预测客队得分"`
  → `comment = os.getenv("D56C8D0D5AA0_INITIAL_DATABASE_SCHEMA_COMMENT_393")`
  → 环境变量: `D56C8D0D5AA0_INITIAL_DATABASE_SCHEMA_COMMENT_393`

- 行 399: `comment="双方进球概率"`
  → `comment = os.getenv("D56C8D0D5AA0_INITIAL_DATABASE_SCHEMA_COMMENT_399")`
  → 环境变量: `D56C8D0D5AA0_INITIAL_DATABASE_SCHEMA_COMMENT_399`

- 行 403: `comment="预测置信度评分"`
  → `comment = os.getenv("D56C8D0D5AA0_INITIAL_DATABASE_SCHEMA_COMMENT_403")`
  → 环境变量: `D56C8D0D5AA0_INITIAL_DATABASE_SCHEMA_COMMENT_403`

- 行 407: `comment="特征重要性数据"`
  → `comment = os.getenv("D56C8D0D5AA0_INITIAL_DATABASE_SCHEMA_COMMENT_407")`
  → 环境变量: `D56C8D0D5AA0_INITIAL_DATABASE_SCHEMA_COMMENT_407`

- 行 409: `comment="预测生成时间"`
  → `comment = os.getenv("D56C8D0D5AA0_INITIAL_DATABASE_SCHEMA_COMMENT_409")`
  → 环境变量: `D56C8D0D5AA0_INITIAL_DATABASE_SCHEMA_COMMENT_409`

### src/database/migrations/versions/005_create_audit_logs_table.py

- 行 19: `down_revision = "004_configure_permissions"`
  → `down_revision = os.getenv("005_CREATE_AUDIT_LOGS_TABLE_DOWN_REVISION_19")`
  → 环境变量: `005_CREATE_AUDIT_LOGS_TABLE_DOWN_REVISION_19`

- 行 32: `comment="审计日志ID"`
  → `comment = os.getenv("005_CREATE_AUDIT_LOGS_TABLE_COMMENT_32")`
  → 环境变量: `005_CREATE_AUDIT_LOGS_TABLE_COMMENT_32`

- 行 35: `comment="操作用户ID"`
  → `comment = os.getenv("005_CREATE_AUDIT_LOGS_TABLE_COMMENT_35")`
  → 环境变量: `005_CREATE_AUDIT_LOGS_TABLE_COMMENT_35`

- 行 44: `server_default="MEDIUM"`
  → `server_default = os.getenv("005_CREATE_AUDIT_LOGS_TABLE_SERVER_DEFAULT_44")`
  → 环境变量: `005_CREATE_AUDIT_LOGS_TABLE_SERVER_DEFAULT_44`

- 行 61: `comment="旧值哈希（敏感数据）"`
  → `comment = os.getenv("005_CREATE_AUDIT_LOGS_TABLE_COMMENT_61")`
  → 环境变量: `005_CREATE_AUDIT_LOGS_TABLE_COMMENT_61`

- 行 65: `comment="新值哈希（敏感数据）"`
  → `comment = os.getenv("005_CREATE_AUDIT_LOGS_TABLE_COMMENT_65")`
  → 环境变量: `005_CREATE_AUDIT_LOGS_TABLE_COMMENT_65`

- 行 69: `comment="客户端IP地址"`
  → `comment = os.getenv("005_CREATE_AUDIT_LOGS_TABLE_COMMENT_69")`
  → 环境变量: `005_CREATE_AUDIT_LOGS_TABLE_COMMENT_69`

- 行 76: `comment="HTTP方法"`
  → `comment = os.getenv("005_CREATE_AUDIT_LOGS_TABLE_COMMENT_76")`
  → 环境变量: `005_CREATE_AUDIT_LOGS_TABLE_COMMENT_76`

- 行 80: `comment="操作是否成功"`
  → `comment = os.getenv("005_CREATE_AUDIT_LOGS_TABLE_COMMENT_80")`
  → 环境变量: `005_CREATE_AUDIT_LOGS_TABLE_COMMENT_80`

- 行 91: `comment="操作耗时（毫秒）"`
  → `comment = os.getenv("005_CREATE_AUDIT_LOGS_TABLE_COMMENT_91")`
  → 环境变量: `005_CREATE_AUDIT_LOGS_TABLE_COMMENT_91`

- 行 100: `comment="标签（逗号分隔）"`
  → `comment = os.getenv("005_CREATE_AUDIT_LOGS_TABLE_COMMENT_100")`
  → 环境变量: `005_CREATE_AUDIT_LOGS_TABLE_COMMENT_100`

- 行 112: `comment="保留期限（天）"`
  → `comment = os.getenv("005_CREATE_AUDIT_LOGS_TABLE_COMMENT_112")`
  → 环境变量: `005_CREATE_AUDIT_LOGS_TABLE_COMMENT_112`

- 行 117: `comment="是否包含敏感数据"`
  → `comment = os.getenv("005_CREATE_AUDIT_LOGS_TABLE_COMMENT_117")`
  → 环境变量: `005_CREATE_AUDIT_LOGS_TABLE_COMMENT_117`

- 行 133: `comment="权限审计日志表，记录所有敏感操作的详细信息"`
  → `comment = os.getenv("005_CREATE_AUDIT_LOGS_TABLE_COMMENT_133")`
  → 环境变量: `005_CREATE_AUDIT_LOGS_TABLE_COMMENT_133`

### src/cache/redis_manager.py

- 行 73: `type='recent'`
  → `type = os.getenv("REDIS_MANAGER_TYPE_73")`
  → 环境变量: `REDIS_MANAGER_TYPE_73`

- 行 113: `str = "recent"`
  → `str = os.getenv("REDIS_MANAGER_STR_113")`
  → 环境变量: `REDIS_MANAGER_STR_113`

- 行 122: `str = "latest"`
  → `str = os.getenv("REDIS_MANAGER_STR_122")`
  → 环境变量: `REDIS_MANAGER_STR_122`

### src/core/config.py

- 行 82: `default="sqlite+aiosqlite:///./data/football_prediction.db"`
  → `default = os.getenv("CONFIG_DEFAULT_82")`
  → 环境变量: `CONFIG_DEFAULT_82`

- 行 83: `description="数据库连接URL"`
  → `description = os.getenv("CONFIG_DESCRIPTION_83")`
  → 环境变量: `CONFIG_DESCRIPTION_83`

- 行 90: `default="postgresql+asyncpg://postgres:postgres@db:5432/football_prediction_test"`
  → `default = os.getenv("CONFIG_DEFAULT_90")`
  → 环境变量: `CONFIG_DEFAULT_90`

- 行 92: `description="测试数据库连接URL"`
  → `description = os.getenv("CONFIG_DESCRIPTION_92")`
  → 环境变量: `CONFIG_DESCRIPTION_92`

- 行 99: `default="redis://redis:6379/0"`
  → `default = os.getenv("CONFIG_DEFAULT_99")`
  → 环境变量: `CONFIG_DEFAULT_99`

- 行 99: `description="Redis连接URL"`
  → `description = os.getenv("CONFIG_DESCRIPTION_99")`
  → 环境变量: `CONFIG_DESCRIPTION_99`

- 行 106: `description="API服务器主机"`
  → `description = os.getenv("CONFIG_DESCRIPTION_106")`
  → 环境变量: `CONFIG_DESCRIPTION_106`

- 行 109: `description="API服务器端口"`
  → `description = os.getenv("CONFIG_DESCRIPTION_109")`
  → 环境变量: `CONFIG_DESCRIPTION_109`

- 行 111: `default="development"`
  → `default = os.getenv("CONFIG_DEFAULT_111")`
  → 环境变量: `CONFIG_DEFAULT_111`

- 行 121: `default="file:///tmp/mlflow"`
  → `default = os.getenv("CONFIG_DEFAULT_121")`
  → 环境变量: `CONFIG_DEFAULT_121`

- 行 122: `description="MLflow跟踪URI"`
  → `description = os.getenv("CONFIG_DESCRIPTION_122")`
  → 环境变量: `CONFIG_DESCRIPTION_122`

- 行 127: `description="API-Football密钥"`
  → `description = os.getenv("CONFIG_DESCRIPTION_127")`
  → 环境变量: `CONFIG_DESCRIPTION_127`

- 行 133: `description="API-Football基础URL"`
  → `description = os.getenv("CONFIG_DESCRIPTION_133")`
  → 环境变量: `CONFIG_DESCRIPTION_133`

- 行 147: `database_url = "sqlite+aiosqlite:///./data/football_prediction.db"`
  → `database_url = os.getenv("CONFIG_DATABASE_URL_147")`
  → 环境变量: `CONFIG_DATABASE_URL_147`

- 行 149: `test_database_url = "postgresql+asyncpg://postgres:postgres@db:5432/football_prediction_test"`
  → `test_database_url = os.getenv("CONFIG_TEST_DATABASE_URL_149")`
  → 环境变量: `CONFIG_TEST_DATABASE_URL_149`

- 行 155: `redis_url = "redis://redis:6379/0"`
  → `redis_url = os.getenv("CONFIG_REDIS_URL_155")`
  → 环境变量: `CONFIG_REDIS_URL_155`

- 行 157: `environment = "development"`
  → `environment = os.getenv("CONFIG_ENVIRONMENT_157")`
  → 环境变量: `CONFIG_ENVIRONMENT_157`

- 行 158: `mlflow_tracking_uri = "file:///tmp/mlflow"`
  → `mlflow_tracking_uri = os.getenv("CONFIG_MLFLOW_TRACKING_URI_158")`
  → 环境变量: `CONFIG_MLFLOW_TRACKING_URI_158`

### src/services/audit_service.py

- 行 277: `old_value = "[SENSITIVE]"`
  → `old_value = os.getenv("AUDIT_SERVICE_OLD_VALUE_277")`
  → 环境变量: `AUDIT_SERVICE_OLD_VALUE_277`

- 行 279: `new_value = "[SENSITIVE]"`
  → `new_value = os.getenv("AUDIT_SERVICE_NEW_VALUE_279")`
  → 环境变量: `AUDIT_SERVICE_NEW_VALUE_279`

### src/services/base.py

- 行 12: `str = "BaseService"`
  → `str = os.getenv("BASE_STR_12")`
  → 环境变量: `BASE_STR_12`

### src/services/data_processing.py

- 行 164: `cache_type="match_info"`
  → `cache_type = os.getenv("DATA_PROCESSING_CACHE_TYPE_164")`
  → 环境变量: `DATA_PROCESSING_CACHE_TYPE_164`

- 行 431: `table_name="processed_matches"`
  → `table_name = os.getenv("DATA_PROCESSING_TABLE_NAME_431")`
  → 环境变量: `DATA_PROCESSING_TABLE_NAME_431`

- 行 500: `table_name="processed_odds"`
  → `table_name = os.getenv("DATA_PROCESSING_TABLE_NAME_500")`
  → 环境变量: `DATA_PROCESSING_TABLE_NAME_500`

- 行 572: `table_name="processed_matches"`
  → `table_name = os.getenv("DATA_PROCESSING_TABLE_NAME_572")`
  → 环境变量: `DATA_PROCESSING_TABLE_NAME_572`

### src/services/content_analysis.py

- 行 58: `analysis_type="content_analysis"`
  → `analysis_type = os.getenv("CONTENT_ANALYSIS_ANALYSIS_TYPE_58")`
  → 环境变量: `CONTENT_ANALYSIS_ANALYSIS_TYPE_58`

### src/features/feature_store.py

- 行 126: `description="比赛实体，用于比赛级别的特征"`
  → `description = os.getenv("FEATURE_STORE_DESCRIPTION_126")`
  → 环境变量: `FEATURE_STORE_DESCRIPTION_126`

- 行 130: `description="球队实体，用于球队级别的特征"`
  → `description = os.getenv("FEATURE_STORE_DESCRIPTION_130")`
  → 环境变量: `FEATURE_STORE_DESCRIPTION_130`

- 行 143: `name="football_postgres"`
  → `name = os.getenv("FEATURE_STORE_NAME_143")`
  → 环境变量: `FEATURE_STORE_NAME_143`

- 行 159: `timestamp_field="event_timestamp"`
  → `timestamp_field = os.getenv("FEATURE_STORE_TIMESTAMP_FIELD_159")`
  → 环境变量: `FEATURE_STORE_TIMESTAMP_FIELD_159`

- 行 161: `name="football_match_postgres"`
  → `name = os.getenv("FEATURE_STORE_NAME_161")`
  → 环境变量: `FEATURE_STORE_NAME_161`

- 行 177: `timestamp_field="event_timestamp"`
  → `timestamp_field = os.getenv("FEATURE_STORE_TIMESTAMP_FIELD_177")`
  → 环境变量: `FEATURE_STORE_TIMESTAMP_FIELD_177`

- 行 180: `name="football_odds_postgres"`
  → `name = os.getenv("FEATURE_STORE_NAME_180")`
  → 环境变量: `FEATURE_STORE_NAME_180`

- 行 195: `timestamp_field="event_timestamp"`
  → `timestamp_field = os.getenv("FEATURE_STORE_TIMESTAMP_FIELD_195")`
  → 环境变量: `FEATURE_STORE_TIMESTAMP_FIELD_195`

- 行 199: `name="team_recent_performance"`
  → `name = os.getenv("FEATURE_STORE_NAME_199")`
  → 环境变量: `FEATURE_STORE_NAME_199`

- 行 205: `name="recent_5_wins"`
  → `name = os.getenv("FEATURE_STORE_NAME_205")`
  → 环境变量: `FEATURE_STORE_NAME_205`

- 行 206: `name="recent_5_draws"`
  → `name = os.getenv("FEATURE_STORE_NAME_206")`
  → 环境变量: `FEATURE_STORE_NAME_206`

- 行 208: `name="recent_5_losses"`
  → `name = os.getenv("FEATURE_STORE_NAME_208")`
  → 环境变量: `FEATURE_STORE_NAME_208`

- 行 210: `name="recent_5_goals_for"`
  → `name = os.getenv("FEATURE_STORE_NAME_210")`
  → 环境变量: `FEATURE_STORE_NAME_210`

- 行 210: `name="recent_5_goals_against"`
  → `name = os.getenv("FEATURE_STORE_NAME_210")`
  → 环境变量: `FEATURE_STORE_NAME_210`

- 行 211: `name="recent_5_points"`
  → `name = os.getenv("FEATURE_STORE_NAME_211")`
  → 环境变量: `FEATURE_STORE_NAME_211`

- 行 212: `name="recent_5_home_wins"`
  → `name = os.getenv("FEATURE_STORE_NAME_212")`
  → 环境变量: `FEATURE_STORE_NAME_212`

- 行 213: `name="recent_5_away_wins"`
  → `name = os.getenv("FEATURE_STORE_NAME_213")`
  → 环境变量: `FEATURE_STORE_NAME_213`

- 行 214: `name="recent_5_home_goals_for"`
  → `name = os.getenv("FEATURE_STORE_NAME_214")`
  → 环境变量: `FEATURE_STORE_NAME_214`

- 行 214: `name="recent_5_away_goals_for"`
  → `name = os.getenv("FEATURE_STORE_NAME_214")`
  → 环境变量: `FEATURE_STORE_NAME_214`

- 行 216: `description="球队近期表现特征（最近5场比赛）"`
  → `description = os.getenv("FEATURE_STORE_DESCRIPTION_216")`
  → 环境变量: `FEATURE_STORE_DESCRIPTION_216`

- 行 217: `name="historical_matchup"`
  → `name = os.getenv("FEATURE_STORE_NAME_217")`
  → 环境变量: `FEATURE_STORE_NAME_217`

- 行 219: `name="home_team_id"`
  → `name = os.getenv("FEATURE_STORE_NAME_219")`
  → 环境变量: `FEATURE_STORE_NAME_219`

- 行 221: `name="away_team_id"`
  → `name = os.getenv("FEATURE_STORE_NAME_221")`
  → 环境变量: `FEATURE_STORE_NAME_221`

- 行 222: `name="h2h_total_matches"`
  → `name = os.getenv("FEATURE_STORE_NAME_222")`
  → 环境变量: `FEATURE_STORE_NAME_222`

- 行 224: `name="h2h_home_wins"`
  → `name = os.getenv("FEATURE_STORE_NAME_224")`
  → 环境变量: `FEATURE_STORE_NAME_224`

- 行 225: `name="h2h_away_wins"`
  → `name = os.getenv("FEATURE_STORE_NAME_225")`
  → 环境变量: `FEATURE_STORE_NAME_225`

- 行 226: `name="h2h_draws"`
  → `name = os.getenv("FEATURE_STORE_NAME_226")`
  → 环境变量: `FEATURE_STORE_NAME_226`

- 行 228: `name="h2h_home_goals_total"`
  → `name = os.getenv("FEATURE_STORE_NAME_228")`
  → 环境变量: `FEATURE_STORE_NAME_228`

- 行 229: `name="h2h_away_goals_total"`
  → `name = os.getenv("FEATURE_STORE_NAME_229")`
  → 环境变量: `FEATURE_STORE_NAME_229`

- 行 231: `description="球队历史对战特征"`
  → `description = os.getenv("FEATURE_STORE_DESCRIPTION_231")`
  → 环境变量: `FEATURE_STORE_DESCRIPTION_231`

- 行 232: `name="odds_features"`
  → `name = os.getenv("FEATURE_STORE_NAME_232")`
  → 环境变量: `FEATURE_STORE_NAME_232`

- 行 234: `name="home_odds_avg"`
  → `name = os.getenv("FEATURE_STORE_NAME_234")`
  → 环境变量: `FEATURE_STORE_NAME_234`

- 行 234: `name="draw_odds_avg"`
  → `name = os.getenv("FEATURE_STORE_NAME_234")`
  → 环境变量: `FEATURE_STORE_NAME_234`

- 行 235: `name="away_odds_avg"`
  → `name = os.getenv("FEATURE_STORE_NAME_235")`
  → 环境变量: `FEATURE_STORE_NAME_235`

- 行 236: `name="home_implied_probability"`
  → `name = os.getenv("FEATURE_STORE_NAME_236")`
  → 环境变量: `FEATURE_STORE_NAME_236`

- 行 238: `name="draw_implied_probability"`
  → `name = os.getenv("FEATURE_STORE_NAME_238")`
  → 环境变量: `FEATURE_STORE_NAME_238`

- 行 239: `name="away_implied_probability"`
  → `name = os.getenv("FEATURE_STORE_NAME_239")`
  → 环境变量: `FEATURE_STORE_NAME_239`

- 行 241: `name="bookmaker_count"`
  → `name = os.getenv("FEATURE_STORE_NAME_241")`
  → 环境变量: `FEATURE_STORE_NAME_241`

- 行 242: `name="bookmaker_consensus"`
  → `name = os.getenv("FEATURE_STORE_NAME_242")`
  → 环境变量: `FEATURE_STORE_NAME_242`

- 行 245: `description="赔率衍生特征"`
  → `description = os.getenv("FEATURE_STORE_DESCRIPTION_245")`
  → 环境变量: `FEATURE_STORE_DESCRIPTION_245`

- 行 577: `cache_type="match_features"`
  → `cache_type = os.getenv("FEATURE_STORE_CACHE_TYPE_577")`
  → 环境变量: `FEATURE_STORE_CACHE_TYPE_577`

### src/tasks/backup_tasks.py

- 行 195: `database_name="football_prediction"`
  → `database_name = os.getenv("BACKUP_TASKS_DATABASE_NAME_195")`
  → 环境变量: `BACKUP_TASKS_DATABASE_NAME_195`

- 行 271: `str = "football_prediction"`
  → `str = os.getenv("BACKUP_TASKS_STR_271")`
  → 环境变量: `BACKUP_TASKS_STR_271`

- 行 312: `database_name="football_prediction"`
  → `database_name = os.getenv("BACKUP_TASKS_DATABASE_NAME_312")`
  → 环境变量: `BACKUP_TASKS_DATABASE_NAME_312`

- 行 403: `error_type="script_execution_failed"`
  → `error_type = os.getenv("BACKUP_TASKS_ERROR_TYPE_403")`
  → 环境变量: `BACKUP_TASKS_ERROR_TYPE_403`

- 行 414: `error_type="timeout"`
  → `error_type = os.getenv("BACKUP_TASKS_ERROR_TYPE_414")`
  → 环境变量: `BACKUP_TASKS_ERROR_TYPE_414`

- 行 560: `str = "football_prediction"`
  → `str = os.getenv("BACKUP_TASKS_STR_560")`
  → 环境变量: `BACKUP_TASKS_STR_560`

- 行 595: `str = "football_prediction"`
  → `str = os.getenv("BACKUP_TASKS_STR_595")`
  → 环境变量: `BACKUP_TASKS_STR_595`

- 行 606: `backup_type="incremental"`
  → `backup_type = os.getenv("BACKUP_TASKS_BACKUP_TYPE_606")`
  → 环境变量: `BACKUP_TASKS_BACKUP_TYPE_606`

- 行 626: `str = "football_prediction"`
  → `str = os.getenv("BACKUP_TASKS_STR_626")`
  → 环境变量: `BACKUP_TASKS_STR_626`

- 行 659: `str = "football_prediction"`
  → `str = os.getenv("BACKUP_TASKS_STR_659")`
  → 环境变量: `BACKUP_TASKS_STR_659`

- 行 695: `str = "football_prediction"`
  → `str = os.getenv("BACKUP_TASKS_STR_695")`
  → 环境变量: `BACKUP_TASKS_STR_695`

- 行 860: `str = "football_prediction"`
  → `str = os.getenv("BACKUP_TASKS_STR_860")`
  → 环境变量: `BACKUP_TASKS_STR_860`

### src/tasks/streaming_tasks.py

- 行 97: `task_name="consume_kafka_streams_task"`
  → `task_name = os.getenv("STREAMING_TASKS_TASK_NAME_97")`
  → 环境变量: `STREAMING_TASKS_TASK_NAME_97`

- 行 162: `task_name="start_continuous_consumer_task"`
  → `task_name = os.getenv("STREAMING_TASKS_TASK_NAME_162")`
  → 环境变量: `STREAMING_TASKS_TASK_NAME_162`

- 行 228: `task_name="produce_to_kafka_stream_task"`
  → `task_name = os.getenv("STREAMING_TASKS_TASK_NAME_228")`
  → 环境变量: `STREAMING_TASKS_TASK_NAME_228`

- 行 280: `task_name="stream_health_check_task"`
  → `task_name = os.getenv("STREAMING_TASKS_TASK_NAME_280")`
  → 环境变量: `STREAMING_TASKS_TASK_NAME_280`

- 行 350: `task_name="stream_data_processing_task"`
  → `task_name = os.getenv("STREAMING_TASKS_TASK_NAME_350")`
  → 环境变量: `STREAMING_TASKS_TASK_NAME_350`

- 行 440: `task_name="kafka_topic_management_task"`
  → `task_name = os.getenv("STREAMING_TASKS_TASK_NAME_440")`
  → 环境变量: `STREAMING_TASKS_TASK_NAME_440`

### src/tasks/maintenance_tasks.py

- 行 131: `status = 'running'`
  → `status = os.getenv("MAINTENANCE_TASKS_STATUS_131")`
  → 环境变量: `MAINTENANCE_TASKS_STATUS_131`

- 行 300: `status = "healthy"`
  → `status = os.getenv("MAINTENANCE_TASKS_STATUS_300")`
  → 环境变量: `MAINTENANCE_TASKS_STATUS_300`

- 行 364: `status = 'running'`
  → `status = os.getenv("MAINTENANCE_TASKS_STATUS_364")`
  → 环境变量: `MAINTENANCE_TASKS_STATUS_364`

- 行 379: `table_schema = 'public'`
  → `table_schema = os.getenv("MAINTENANCE_TASKS_TABLE_SCHEMA_379")`
  → 环境变量: `MAINTENANCE_TASKS_TABLE_SCHEMA_379`

- 行 380: `table_type = 'BASE TABLE'`
  → `table_type = os.getenv("MAINTENANCE_TASKS_TABLE_TYPE_380")`
  → 环境变量: `MAINTENANCE_TASKS_TABLE_TYPE_380`

### src/tasks/error_logger.py

- 行 245: `_db_type = "postgresql"`
  → `_db_type = os.getenv("ERROR_LOGGER__DB_TYPE_245")`
  → 环境变量: `ERROR_LOGGER__DB_TYPE_245`

- 行 246: `_db_type = "postgresql"`
  → `_db_type = os.getenv("ERROR_LOGGER__DB_TYPE_246")`
  → 环境变量: `ERROR_LOGGER__DB_TYPE_246`

### src/tasks/celery_app.py

- 行 96: `task_default_queue="default"`
  → `task_default_queue = os.getenv("CELERY_APP_TASK_DEFAULT_QUEUE_96")`
  → 环境变量: `CELERY_APP_TASK_DEFAULT_QUEUE_96`

### src/tasks/monitoring.py

- 行 139: `str = "success"`
  → `str = os.getenv("MONITORING_STR_139")`
  → 环境变量: `MONITORING_STR_139`

- 行 179: `_db_type = "postgresql"`
  → `_db_type = os.getenv("MONITORING__DB_TYPE_179")`
  → 环境变量: `MONITORING__DB_TYPE_179`

- 行 180: `_db_type = "postgresql"`
  → `_db_type = os.getenv("MONITORING__DB_TYPE_180")`
  → 环境变量: `MONITORING__DB_TYPE_180`

### src/tasks/data_collection_tasks.py

- 行 104: `task_name="collect_fixtures_task"`
  → `task_name = os.getenv("DATA_COLLECTION_TASKS_TASK_NAME_104")`
  → 环境变量: `DATA_COLLECTION_TASKS_TASK_NAME_104`

- 行 104: `api_endpoint="fixtures_api"`
  → `api_endpoint = os.getenv("DATA_COLLECTION_TASKS_API_ENDPOINT_104")`
  → 环境变量: `DATA_COLLECTION_TASKS_API_ENDPOINT_104`

- 行 172: `data_source="fixtures_api"`
  → `data_source = os.getenv("DATA_COLLECTION_TASKS_DATA_SOURCE_172")`
  → 环境变量: `DATA_COLLECTION_TASKS_DATA_SOURCE_172`

- 行 173: `collection_type="fixtures"`
  → `collection_type = os.getenv("DATA_COLLECTION_TASKS_COLLECTION_TYPE_173")`
  → 环境变量: `DATA_COLLECTION_TASKS_COLLECTION_TYPE_173`

- 行 228: `task_name="collect_odds_task"`
  → `task_name = os.getenv("DATA_COLLECTION_TASKS_TASK_NAME_228")`
  → 环境变量: `DATA_COLLECTION_TASKS_TASK_NAME_228`

- 行 230: `api_endpoint="odds_api"`
  → `api_endpoint = os.getenv("DATA_COLLECTION_TASKS_API_ENDPOINT_230")`
  → 环境变量: `DATA_COLLECTION_TASKS_API_ENDPOINT_230`

- 行 274: `data_source="odds_api"`
  → `data_source = os.getenv("DATA_COLLECTION_TASKS_DATA_SOURCE_274")`
  → 环境变量: `DATA_COLLECTION_TASKS_DATA_SOURCE_274`

- 行 337: `task_name="collect_scores_task"`
  → `task_name = os.getenv("DATA_COLLECTION_TASKS_TASK_NAME_337")`
  → 环境变量: `DATA_COLLECTION_TASKS_TASK_NAME_337`

- 行 338: `api_endpoint="scores_api"`
  → `api_endpoint = os.getenv("DATA_COLLECTION_TASKS_API_ENDPOINT_338")`
  → 环境变量: `DATA_COLLECTION_TASKS_API_ENDPOINT_338`

- 行 398: `data_source="scores_api"`
  → `data_source = os.getenv("DATA_COLLECTION_TASKS_DATA_SOURCE_398")`
  → 环境变量: `DATA_COLLECTION_TASKS_DATA_SOURCE_398`

- 行 400: `collection_type="scores"`
  → `collection_type = os.getenv("DATA_COLLECTION_TASKS_COLLECTION_TYPE_400")`
  → 环境变量: `DATA_COLLECTION_TASKS_COLLECTION_TYPE_400`

- 行 535: `task_name="emergency_data_collection_task"`
  → `task_name = os.getenv("DATA_COLLECTION_TASKS_TASK_NAME_535")`
  → 环境变量: `DATA_COLLECTION_TASKS_TASK_NAME_535`

### src/data/storage/data_lake_storage.py

- 行 48: `str = "snappy"`
  → `str = os.getenv("DATA_LAKE_STORAGE_STR_48")`
  → 环境变量: `DATA_LAKE_STORAGE_STR_48`

- 行 365: `year=")]
                        month_part = [p for p in parts if p.startswith("`
  → `year = os.getenv("DATA_LAKE_STORAGE_YEAR_365")`
  → 环境变量: `DATA_LAKE_STORAGE_YEAR_365`

- 行 365: `month=")]

                        if year_part and month_part:
                            year = int(year_part[0].split("`
  → `month = os.getenv("DATA_LAKE_STORAGE_MONTH_365")`
  → 环境变量: `DATA_LAKE_STORAGE_MONTH_365`

- 行 456: `str = "us-east-1"`
  → `str = os.getenv("DATA_LAKE_STORAGE_STR_456")`
  → 环境变量: `DATA_LAKE_STORAGE_STR_456`

- 行 457: `str = "snappy"`
  → `str = os.getenv("DATA_LAKE_STORAGE_STR_457")`
  → 环境变量: `DATA_LAKE_STORAGE_STR_457`

- 行 597: `ContentType="application/octet-stream"`
  → `ContentType = os.getenv("DATA_LAKE_STORAGE_CONTENTTYPE_597")`
  → 环境变量: `DATA_LAKE_STORAGE_CONTENTTYPE_597`

- 行 740: `year="):
                    year_part = int(part.split("`
  → `year = os.getenv("DATA_LAKE_STORAGE_YEAR_740")`
  → 环境变量: `DATA_LAKE_STORAGE_YEAR_740`

- 行 742: `month="):
                    month_part = int(part.split("`
  → `month = os.getenv("DATA_LAKE_STORAGE_MONTH_742")`
  → 环境变量: `DATA_LAKE_STORAGE_MONTH_742`

- 行 743: `day="):
                    day_part = int(part.split("`
  → `day = os.getenv("DATA_LAKE_STORAGE_DAY_743")`
  → 环境变量: `DATA_LAKE_STORAGE_DAY_743`

- 行 798: `year="):
                                    year_part = int(part.split("`
  → `year = os.getenv("DATA_LAKE_STORAGE_YEAR_798")`
  → 环境变量: `DATA_LAKE_STORAGE_YEAR_798`

- 行 799: `month="):
                                    month_part = int(part.split("`
  → `month = os.getenv("DATA_LAKE_STORAGE_MONTH_799")`
  → 环境变量: `DATA_LAKE_STORAGE_MONTH_799`

- 行 802: `day="):
                                    day_part = int(part.split("`
  → `day = os.getenv("DATA_LAKE_STORAGE_DAY_802")`
  → 环境变量: `DATA_LAKE_STORAGE_DAY_802`

### src/data/processing/missing_data_handler.py

- 行 163: `method="linear"`
  → `method = os.getenv("MISSING_DATA_HANDLER_METHOD_163")`
  → 环境变量: `MISSING_DATA_HANDLER_METHOD_163`

### src/data/quality/data_quality_monitor.py

- 行 150: `collection_type = 'fixtures'`
  → `collection_type = os.getenv("DATA_QUALITY_MONITOR_COLLECTION_TYPE_150")`
  → 环境变量: `DATA_QUALITY_MONITOR_COLLECTION_TYPE_150`

- 行 150: `status = 'success'`
  → `status = os.getenv("DATA_QUALITY_MONITOR_STATUS_150")`
  → 环境变量: `DATA_QUALITY_MONITOR_STATUS_150`

- 行 288: `match_status = 'finished'`
  → `match_status = os.getenv("DATA_QUALITY_MONITOR_MATCH_STATUS_288")`
  → 环境变量: `DATA_QUALITY_MONITOR_MATCH_STATUS_288`

### src/data/quality/ge_prometheus_exporter.py

- 行 204: `table_name="overall"`
  → `table_name = os.getenv("GE_PROMETHEUS_EXPORTER_TABLE_NAME_204")`
  → 环境变量: `GE_PROMETHEUS_EXPORTER_TABLE_NAME_204`

- 行 234: `table_name="matches"`
  → `table_name = os.getenv("GE_PROMETHEUS_EXPORTER_TABLE_NAME_234")`
  → 环境变量: `GE_PROMETHEUS_EXPORTER_TABLE_NAME_234`

- 行 234: `data_type="fixtures"`
  → `data_type = os.getenv("GE_PROMETHEUS_EXPORTER_DATA_TYPE_234")`
  → 环境变量: `GE_PROMETHEUS_EXPORTER_DATA_TYPE_234`

- 行 265: `table_name = "unknown"`
  → `table_name = os.getenv("GE_PROMETHEUS_EXPORTER_TABLE_NAME_265")`
  → 环境变量: `GE_PROMETHEUS_EXPORTER_TABLE_NAME_265`

- 行 270: `table_name = "matches"`
  → `table_name = os.getenv("GE_PROMETHEUS_EXPORTER_TABLE_NAME_270")`
  → 环境变量: `GE_PROMETHEUS_EXPORTER_TABLE_NAME_270`

### src/data/quality/great_expectations_config.py

- 行 392: `datasource_name="football_postgres"`
  → `datasource_name = os.getenv("GREAT_EXPECTATIONS_CONFIG_DATASOURCE_NAME_392")`
  → 环境变量: `GREAT_EXPECTATIONS_CONFIG_DATASOURCE_NAME_392`

- 行 392: `data_connector_name="default_runtime_data_connector"`
  → `data_connector_name = os.getenv("GREAT_EXPECTATIONS_CONFIG_DATA_CONNECTOR_NAME_392")`
  → 环境变量: `GREAT_EXPECTATIONS_CONFIG_DATA_CONNECTOR_NAME_392`

### src/data/quality/anomaly_detector.py

- 行 85: `str = "medium"`
  → `str = os.getenv("ANOMALY_DETECTOR_STR_85")`
  → 环境变量: `ANOMALY_DETECTOR_STR_85`

- 行 179: `detection_method="3sigma"`
  → `detection_method = os.getenv("ANOMALY_DETECTOR_DETECTION_METHOD_179")`
  → 环境变量: `ANOMALY_DETECTOR_DETECTION_METHOD_179`

- 行 180: `anomaly_type="statistical_outlier"`
  → `anomaly_type = os.getenv("ANOMALY_DETECTOR_ANOMALY_TYPE_180")`
  → 环境变量: `ANOMALY_DETECTOR_ANOMALY_TYPE_180`

- 行 233: `detection_method="3sigma"`
  → `detection_method = os.getenv("ANOMALY_DETECTOR_DETECTION_METHOD_233")`
  → 环境变量: `ANOMALY_DETECTOR_DETECTION_METHOD_233`

- 行 233: `anomaly_type="statistical_outlier"`
  → `anomaly_type = os.getenv("ANOMALY_DETECTOR_ANOMALY_TYPE_233")`
  → 环境变量: `ANOMALY_DETECTOR_ANOMALY_TYPE_233`

- 行 235: `severity="medium"`
  → `severity = os.getenv("ANOMALY_DETECTOR_SEVERITY_235")`
  → 环境变量: `ANOMALY_DETECTOR_SEVERITY_235`

- 行 274: `anomaly_type="statistical_outlier"`
  → `anomaly_type = os.getenv("ANOMALY_DETECTOR_ANOMALY_TYPE_274")`
  → 环境变量: `ANOMALY_DETECTOR_ANOMALY_TYPE_274`

- 行 275: `detection_method="3sigma"`
  → `detection_method = os.getenv("ANOMALY_DETECTOR_DETECTION_METHOD_275")`
  → 环境变量: `ANOMALY_DETECTOR_DETECTION_METHOD_275`

- 行 282: `detection_method="3sigma"`
  → `detection_method = os.getenv("ANOMALY_DETECTOR_DETECTION_METHOD_282")`
  → 环境变量: `ANOMALY_DETECTOR_DETECTION_METHOD_282`

- 行 323: `severity = "critical"`
  → `severity = os.getenv("ANOMALY_DETECTOR_SEVERITY_323")`
  → 环境变量: `ANOMALY_DETECTOR_SEVERITY_323`

- 行 328: `severity = "medium"`
  → `severity = os.getenv("ANOMALY_DETECTOR_SEVERITY_328")`
  → 环境变量: `ANOMALY_DETECTOR_SEVERITY_328`

- 行 335: `detection_method="ks_test"`
  → `detection_method = os.getenv("ANOMALY_DETECTOR_DETECTION_METHOD_335")`
  → 环境变量: `ANOMALY_DETECTOR_DETECTION_METHOD_335`

- 行 336: `anomaly_type="distribution_shift"`
  → `anomaly_type = os.getenv("ANOMALY_DETECTOR_ANOMALY_TYPE_336")`
  → 环境变量: `ANOMALY_DETECTOR_ANOMALY_TYPE_336`

- 行 397: `anomaly_type="distribution_shift"`
  → `anomaly_type = os.getenv("ANOMALY_DETECTOR_ANOMALY_TYPE_397")`
  → 环境变量: `ANOMALY_DETECTOR_ANOMALY_TYPE_397`

- 行 399: `detection_method="ks_test"`
  → `detection_method = os.getenv("ANOMALY_DETECTOR_DETECTION_METHOD_399")`
  → 环境变量: `ANOMALY_DETECTOR_DETECTION_METHOD_399`

- 行 408: `detection_method="ks_test"`
  → `detection_method = os.getenv("ANOMALY_DETECTOR_DETECTION_METHOD_408")`
  → 环境变量: `ANOMALY_DETECTOR_DETECTION_METHOD_408`

- 行 453: `anomaly_type="statistical_outlier"`
  → `anomaly_type = os.getenv("ANOMALY_DETECTOR_ANOMALY_TYPE_453")`
  → 环境变量: `ANOMALY_DETECTOR_ANOMALY_TYPE_453`

- 行 457: `severity="medium"`
  → `severity = os.getenv("ANOMALY_DETECTOR_SEVERITY_457")`
  → 环境变量: `ANOMALY_DETECTOR_SEVERITY_457`

- 行 494: `anomaly_type="statistical_outlier"`
  → `anomaly_type = os.getenv("ANOMALY_DETECTOR_ANOMALY_TYPE_494")`
  → 环境变量: `ANOMALY_DETECTOR_ANOMALY_TYPE_494`

- 行 571: `severity = "critical"`
  → `severity = os.getenv("ANOMALY_DETECTOR_SEVERITY_571")`
  → 环境变量: `ANOMALY_DETECTOR_SEVERITY_571`

- 行 575: `severity = "medium"`
  → `severity = os.getenv("ANOMALY_DETECTOR_SEVERITY_575")`
  → 环境变量: `ANOMALY_DETECTOR_SEVERITY_575`

- 行 580: `detection_method="isolation_forest"`
  → `detection_method = os.getenv("ANOMALY_DETECTOR_DETECTION_METHOD_580")`
  → 环境变量: `ANOMALY_DETECTOR_DETECTION_METHOD_580`

- 行 581: `anomaly_type="ml_anomaly"`
  → `anomaly_type = os.getenv("ANOMALY_DETECTOR_ANOMALY_TYPE_581")`
  → 环境变量: `ANOMALY_DETECTOR_ANOMALY_TYPE_581`

- 行 622: `anomaly_type="ml_anomaly"`
  → `anomaly_type = os.getenv("ANOMALY_DETECTOR_ANOMALY_TYPE_622")`
  → 环境变量: `ANOMALY_DETECTOR_ANOMALY_TYPE_622`

- 行 623: `detection_method="isolation_forest"`
  → `detection_method = os.getenv("ANOMALY_DETECTOR_DETECTION_METHOD_623")`
  → 环境变量: `ANOMALY_DETECTOR_DETECTION_METHOD_623`

- 行 628: `detection_method="isolation_forest"`
  → `detection_method = os.getenv("ANOMALY_DETECTOR_DETECTION_METHOD_628")`
  → 环境变量: `ANOMALY_DETECTOR_DETECTION_METHOD_628`

- 行 704: `severity = "critical"`
  → `severity = os.getenv("ANOMALY_DETECTOR_SEVERITY_704")`
  → 环境变量: `ANOMALY_DETECTOR_SEVERITY_704`

- 行 710: `severity = "medium"`
  → `severity = os.getenv("ANOMALY_DETECTOR_SEVERITY_710")`
  → 环境变量: `ANOMALY_DETECTOR_SEVERITY_710`

- 行 717: `detection_method="data_drift"`
  → `detection_method = os.getenv("ANOMALY_DETECTOR_DETECTION_METHOD_717")`
  → 环境变量: `ANOMALY_DETECTOR_DETECTION_METHOD_717`

- 行 720: `anomaly_type="feature_drift"`
  → `anomaly_type = os.getenv("ANOMALY_DETECTOR_ANOMALY_TYPE_720")`
  → 环境变量: `ANOMALY_DETECTOR_ANOMALY_TYPE_720`

- 行 763: `anomaly_type="feature_drift"`
  → `anomaly_type = os.getenv("ANOMALY_DETECTOR_ANOMALY_TYPE_763")`
  → 环境变量: `ANOMALY_DETECTOR_ANOMALY_TYPE_763`

- 行 764: `detection_method="data_drift"`
  → `detection_method = os.getenv("ANOMALY_DETECTOR_DETECTION_METHOD_764")`
  → 环境变量: `ANOMALY_DETECTOR_DETECTION_METHOD_764`

- 行 778: `detection_method="data_drift"`
  → `detection_method = os.getenv("ANOMALY_DETECTOR_DETECTION_METHOD_778")`
  → 环境变量: `ANOMALY_DETECTOR_DETECTION_METHOD_778`

- 行 818: `severity = "critical"`
  → `severity = os.getenv("ANOMALY_DETECTOR_SEVERITY_818")`
  → 环境变量: `ANOMALY_DETECTOR_SEVERITY_818`

- 行 824: `severity = "medium"`
  → `severity = os.getenv("ANOMALY_DETECTOR_SEVERITY_824")`
  → 环境变量: `ANOMALY_DETECTOR_SEVERITY_824`

- 行 835: `detection_method="dbscan_clustering"`
  → `detection_method = os.getenv("ANOMALY_DETECTOR_DETECTION_METHOD_835")`
  → 环境变量: `ANOMALY_DETECTOR_DETECTION_METHOD_835`

- 行 836: `anomaly_type="clustering_outlier"`
  → `anomaly_type = os.getenv("ANOMALY_DETECTOR_ANOMALY_TYPE_836")`
  → 环境变量: `ANOMALY_DETECTOR_ANOMALY_TYPE_836`

- 行 877: `anomaly_type="clustering_outlier"`
  → `anomaly_type = os.getenv("ANOMALY_DETECTOR_ANOMALY_TYPE_877")`
  → 环境变量: `ANOMALY_DETECTOR_ANOMALY_TYPE_877`

- 行 878: `detection_method="dbscan_clustering"`
  → `detection_method = os.getenv("ANOMALY_DETECTOR_DETECTION_METHOD_878")`
  → 环境变量: `ANOMALY_DETECTOR_DETECTION_METHOD_878`

- 行 888: `detection_method="dbscan_clustering"`
  → `detection_method = os.getenv("ANOMALY_DETECTOR_DETECTION_METHOD_888")`
  → 环境变量: `ANOMALY_DETECTOR_DETECTION_METHOD_888`

- 行 1032: `detection_method="comprehensive"`
  → `detection_method = os.getenv("ANOMALY_DETECTOR_DETECTION_METHOD_1032")`
  → 环境变量: `ANOMALY_DETECTOR_DETECTION_METHOD_1032`

### src/data/quality/exception_handler.py

- 行 355: `match_status = 'finished'`
  → `match_status = os.getenv("EXCEPTION_HANDLER_MATCH_STATUS_355")`
  → 环境变量: `EXCEPTION_HANDLER_MATCH_STATUS_355`

- 行 365: `match_status = 'finished'`
  → `match_status = os.getenv("EXCEPTION_HANDLER_MATCH_STATUS_365")`
  → 环境变量: `EXCEPTION_HANDLER_MATCH_STATUS_365`

- 行 458: `error_type="suspicious_odds"`
  → `error_type = os.getenv("EXCEPTION_HANDLER_ERROR_TYPE_458")`
  → 环境变量: `EXCEPTION_HANDLER_ERROR_TYPE_458`

- 行 482: `error_type="missing_values_filled"`
  → `error_type = os.getenv("EXCEPTION_HANDLER_ERROR_TYPE_482")`
  → 环境变量: `EXCEPTION_HANDLER_ERROR_TYPE_482`

- 行 513: `status="logged"`
  → `status = os.getenv("EXCEPTION_HANDLER_STATUS_513")`
  → 环境变量: `EXCEPTION_HANDLER_STATUS_513`

### src/data/collectors/streaming_collector.py

- 行 33: `str = "default_source"`
  → `str = os.getenv("STREAMING_COLLECTOR_STR_33")`
  → 环境变量: `STREAMING_COLLECTOR_STR_33`

- 行 126: `stream_type = "scores"`
  → `stream_type = os.getenv("STREAMING_COLLECTOR_STREAM_TYPE_126")`
  → 环境变量: `STREAMING_COLLECTOR_STREAM_TYPE_126`

### src/data/collectors/scores_collector.py

- 行 30: `NOT_STARTED = "not_started"`
  → `NOT_STARTED = os.getenv("SCORES_COLLECTOR_NOT_STARTED_30")`
  → 环境变量: `SCORES_COLLECTOR_NOT_STARTED_30`

- 行 30: `FIRST_HALF = "first_half"`
  → `FIRST_HALF = os.getenv("SCORES_COLLECTOR_FIRST_HALF_30")`
  → 环境变量: `SCORES_COLLECTOR_FIRST_HALF_30`

- 行 31: `HALF_TIME = "half_time"`
  → `HALF_TIME = os.getenv("SCORES_COLLECTOR_HALF_TIME_31")`
  → 环境变量: `SCORES_COLLECTOR_HALF_TIME_31`

- 行 31: `SECOND_HALF = "second_half"`
  → `SECOND_HALF = os.getenv("SCORES_COLLECTOR_SECOND_HALF_31")`
  → 环境变量: `SCORES_COLLECTOR_SECOND_HALF_31`

- 行 32: `FINISHED = "finished"`
  → `FINISHED = os.getenv("SCORES_COLLECTOR_FINISHED_32")`
  → 环境变量: `SCORES_COLLECTOR_FINISHED_32`

- 行 32: `POSTPONED = "postponed"`
  → `POSTPONED = os.getenv("SCORES_COLLECTOR_POSTPONED_32")`
  → 环境变量: `SCORES_COLLECTOR_POSTPONED_32`

- 行 32: `CANCELLED = "cancelled"`
  → `CANCELLED = os.getenv("SCORES_COLLECTOR_CANCELLED_32")`
  → 环境变量: `SCORES_COLLECTOR_CANCELLED_32`

- 行 34: `YELLOW_CARD = "yellow_card"`
  → `YELLOW_CARD = os.getenv("SCORES_COLLECTOR_YELLOW_CARD_34")`
  → 环境变量: `SCORES_COLLECTOR_YELLOW_CARD_34`

- 行 35: `RED_CARD = "red_card"`
  → `RED_CARD = os.getenv("SCORES_COLLECTOR_RED_CARD_35")`
  → 环境变量: `SCORES_COLLECTOR_RED_CARD_35`

- 行 35: `SUBSTITUTION = "substitution"`
  → `SUBSTITUTION = os.getenv("SCORES_COLLECTOR_SUBSTITUTION_35")`
  → 环境变量: `SCORES_COLLECTOR_SUBSTITUTION_35`

- 行 36: `PENALTY = "penalty"`
  → `PENALTY = os.getenv("SCORES_COLLECTOR_PENALTY_36")`
  → 环境变量: `SCORES_COLLECTOR_PENALTY_36`

- 行 36: `OWN_GOAL = "own_goal"`
  → `OWN_GOAL = os.getenv("SCORES_COLLECTOR_OWN_GOAL_36")`
  → 环境变量: `SCORES_COLLECTOR_OWN_GOAL_36`

- 行 36: `VAR_DECISION = "var_decision"`
  → `VAR_DECISION = os.getenv("SCORES_COLLECTOR_VAR_DECISION_36")`
  → 环境变量: `SCORES_COLLECTOR_VAR_DECISION_36`

- 行 45: `str = "scores_api"`
  → `str = os.getenv("SCORES_COLLECTOR_STR_45")`
  → 环境变量: `SCORES_COLLECTOR_STR_45`

- 行 82: `collection_type="fixtures"`
  → `collection_type = os.getenv("SCORES_COLLECTOR_COLLECTION_TYPE_82")`
  → 环境变量: `SCORES_COLLECTOR_COLLECTION_TYPE_82`

- 行 87: `status="skipped"`
  → `status = os.getenv("SCORES_COLLECTOR_STATUS_87")`
  → 环境变量: `SCORES_COLLECTOR_STATUS_87`

- 行 95: `status="skipped"`
  → `status = os.getenv("SCORES_COLLECTOR_STATUS_95")`
  → 环境变量: `SCORES_COLLECTOR_STATUS_95`

- 行 130: `collection_type="live_scores"`
  → `collection_type = os.getenv("SCORES_COLLECTOR_COLLECTION_TYPE_130")`
  → 环境变量: `SCORES_COLLECTOR_COLLECTION_TYPE_130`

- 行 137: `status="success"`
  → `status = os.getenv("SCORES_COLLECTOR_STATUS_137")`
  → 环境变量: `SCORES_COLLECTOR_STATUS_137`

- 行 177: `status = "success"`
  → `status = os.getenv("SCORES_COLLECTOR_STATUS_177")`
  → 环境变量: `SCORES_COLLECTOR_STATUS_177`

- 行 179: `status = "partial"`
  → `status = os.getenv("SCORES_COLLECTOR_STATUS_179")`
  → 环境变量: `SCORES_COLLECTOR_STATUS_179`

- 行 180: `status = "failed"`
  → `status = os.getenv("SCORES_COLLECTOR_STATUS_180")`
  → 环境变量: `SCORES_COLLECTOR_STATUS_180`

- 行 183: `collection_type="live_scores"`
  → `collection_type = os.getenv("SCORES_COLLECTOR_COLLECTION_TYPE_183")`
  → 环境变量: `SCORES_COLLECTOR_COLLECTION_TYPE_183`

- 行 202: `collection_type="live_scores"`
  → `collection_type = os.getenv("SCORES_COLLECTOR_COLLECTION_TYPE_202")`
  → 环境变量: `SCORES_COLLECTOR_COLLECTION_TYPE_202`

- 行 205: `status="failed"`
  → `status = os.getenv("SCORES_COLLECTOR_STATUS_205")`
  → 环境变量: `SCORES_COLLECTOR_STATUS_205`

### src/data/collectors/odds_collector.py

- 行 34: `str = "odds_api"`
  → `str = os.getenv("ODDS_COLLECTOR_STR_34")`
  → 环境变量: `ODDS_COLLECTOR_STR_34`

- 行 62: `collection_type="fixtures"`
  → `collection_type = os.getenv("ODDS_COLLECTOR_COLLECTION_TYPE_62")`
  → 环境变量: `ODDS_COLLECTOR_COLLECTION_TYPE_62`

- 行 65: `status="skipped"`
  → `status = os.getenv("ODDS_COLLECTOR_STATUS_65")`
  → 环境变量: `ODDS_COLLECTOR_STATUS_65`

- 行 166: `status = "success"`
  → `status = os.getenv("ODDS_COLLECTOR_STATUS_166")`
  → 环境变量: `ODDS_COLLECTOR_STATUS_166`

- 行 167: `status = "partial"`
  → `status = os.getenv("ODDS_COLLECTOR_STATUS_167")`
  → 环境变量: `ODDS_COLLECTOR_STATUS_167`

- 行 168: `status = "failed"`
  → `status = os.getenv("ODDS_COLLECTOR_STATUS_168")`
  → 环境变量: `ODDS_COLLECTOR_STATUS_168`

- 行 195: `status="failed"`
  → `status = os.getenv("ODDS_COLLECTOR_STATUS_195")`
  → 环境变量: `ODDS_COLLECTOR_STATUS_195`

- 行 201: `collection_type="live_scores"`
  → `collection_type = os.getenv("ODDS_COLLECTOR_COLLECTION_TYPE_201")`
  → 环境变量: `ODDS_COLLECTOR_COLLECTION_TYPE_201`

- 行 206: `status="skipped"`
  → `status = os.getenv("ODDS_COLLECTOR_STATUS_206")`
  → 环境变量: `ODDS_COLLECTOR_STATUS_206`

### src/data/collectors/base_collector.py

- 行 492: `status="failed"`
  → `status = os.getenv("BASE_COLLECTOR_STATUS_492")`
  → 环境变量: `BASE_COLLECTOR_STATUS_492`

### src/data/collectors/fixtures_collector.py

- 行 33: `str = "football_api"`
  → `str = os.getenv("FIXTURES_COLLECTOR_STR_33")`
  → 环境变量: `FIXTURES_COLLECTOR_STR_33`

- 行 162: `status = "success"`
  → `status = os.getenv("FIXTURES_COLLECTOR_STATUS_162")`
  → 环境变量: `FIXTURES_COLLECTOR_STATUS_162`

- 行 163: `status = "partial"`
  → `status = os.getenv("FIXTURES_COLLECTOR_STATUS_163")`
  → 环境变量: `FIXTURES_COLLECTOR_STATUS_163`

- 行 165: `status = "failed"`
  → `status = os.getenv("FIXTURES_COLLECTOR_STATUS_165")`
  → 环境变量: `FIXTURES_COLLECTOR_STATUS_165`

- 行 167: `collection_type="fixtures"`
  → `collection_type = os.getenv("FIXTURES_COLLECTOR_COLLECTION_TYPE_167")`
  → 环境变量: `FIXTURES_COLLECTOR_COLLECTION_TYPE_167`

- 行 188: `collection_type="fixtures"`
  → `collection_type = os.getenv("FIXTURES_COLLECTOR_COLLECTION_TYPE_188")`
  → 环境变量: `FIXTURES_COLLECTOR_COLLECTION_TYPE_188`

- 行 190: `status="failed"`
  → `status = os.getenv("FIXTURES_COLLECTOR_STATUS_190")`
  → 环境变量: `FIXTURES_COLLECTOR_STATUS_190`

- 行 199: `status="skipped"`
  → `status = os.getenv("FIXTURES_COLLECTOR_STATUS_199")`
  → 环境变量: `FIXTURES_COLLECTOR_STATUS_199`

- 行 206: `collection_type="live_scores"`
  → `collection_type = os.getenv("FIXTURES_COLLECTOR_COLLECTION_TYPE_206")`
  → 环境变量: `FIXTURES_COLLECTOR_COLLECTION_TYPE_206`

- 行 210: `status="skipped"`
  → `status = os.getenv("FIXTURES_COLLECTOR_STATUS_210")`
  → 环境变量: `FIXTURES_COLLECTOR_STATUS_210`

### src/data/features/feature_store.py

- 行 52: `str = "football_prediction"`
  → `str = os.getenv("FEATURE_STORE_STR_52")`
  → 环境变量: `FEATURE_STORE_STR_52`

- 行 102: `type="postgres"`
  → `type = os.getenv("FEATURE_STORE_TYPE_102")`
  → 环境变量: `FEATURE_STORE_TYPE_102`

- 行 160: `str = "event_timestamp"`
  → `str = os.getenv("FEATURE_STORE_STR_160")`
  → 环境变量: `FEATURE_STORE_STR_160`

- 行 184: `to="online_and_offline"`
  → `to = os.getenv("FEATURE_STORE_TO_184")`
  → 环境变量: `FEATURE_STORE_TO_184`

- 行 304: `feature_service_name="match_prediction_v1"`
  → `feature_service_name = os.getenv("FEATURE_STORE_FEATURE_SERVICE_NAME_304")`
  → 环境变量: `FEATURE_STORE_FEATURE_SERVICE_NAME_304`

- 行 426: `str = "football_prediction"`
  → `str = os.getenv("FEATURE_STORE_STR_426")`
  → 环境变量: `FEATURE_STORE_STR_426`

### src/data/features/examples.py

- 行 55: `project_name="football_prediction_demo"`
  → `project_name = os.getenv("EXAMPLES_PROJECT_NAME_55")`
  → 环境变量: `EXAMPLES_PROJECT_NAME_55`

- 行 132: `feature_view_name="team_recent_stats"`
  → `feature_view_name = os.getenv("EXAMPLES_FEATURE_VIEW_NAME_132")`
  → 环境变量: `EXAMPLES_FEATURE_VIEW_NAME_132`

- 行 200: `feature_view_name="odds_features"`
  → `feature_view_name = os.getenv("EXAMPLES_FEATURE_VIEW_NAME_200")`
  → 环境变量: `EXAMPLES_FEATURE_VIEW_NAME_200`

- 行 222: `feature_service_name="real_time_prediction_v1"`
  → `feature_service_name = os.getenv("EXAMPLES_FEATURE_SERVICE_NAME_222")`
  → 环境变量: `EXAMPLES_FEATURE_SERVICE_NAME_222`

- 行 257: `feature_service_name="match_prediction_v1"`
  → `feature_service_name = os.getenv("EXAMPLES_FEATURE_SERVICE_NAME_257")`
  → 环境变量: `EXAMPLES_FEATURE_SERVICE_NAME_257`

- 行 436: `feature_service_name="real_time_prediction_v1"`
  → `feature_service_name = os.getenv("EXAMPLES_FEATURE_SERVICE_NAME_436")`
  → 环境变量: `EXAMPLES_FEATURE_SERVICE_NAME_436`

### src/data/features/feature_definitions.py

- 行 100: `name="match_id"`
  → `name = os.getenv("FEATURE_DEFINITIONS_NAME_100")`
  → 环境变量: `FEATURE_DEFINITIONS_NAME_100`

- 行 100: `description="比赛唯一标识符"`
  → `description = os.getenv("FEATURE_DEFINITIONS_DESCRIPTION_100")`
  → 环境变量: `FEATURE_DEFINITIONS_DESCRIPTION_100`

- 行 100: `name="team_id"`
  → `name = os.getenv("FEATURE_DEFINITIONS_NAME_100")`
  → 环境变量: `FEATURE_DEFINITIONS_NAME_100`

- 行 100: `description="球队唯一标识符"`
  → `description = os.getenv("FEATURE_DEFINITIONS_DESCRIPTION_100")`
  → 环境变量: `FEATURE_DEFINITIONS_DESCRIPTION_100`

- 行 104: `name="league_id"`
  → `name = os.getenv("FEATURE_DEFINITIONS_NAME_104")`
  → 环境变量: `FEATURE_DEFINITIONS_NAME_104`

- 行 104: `description="联赛唯一标识符"`
  → `description = os.getenv("FEATURE_DEFINITIONS_DESCRIPTION_104")`
  → 环境变量: `FEATURE_DEFINITIONS_DESCRIPTION_104`

- 行 107: `name="match_features_source"`
  → `name = os.getenv("FEATURE_DEFINITIONS_NAME_107")`
  → 环境变量: `FEATURE_DEFINITIONS_NAME_107`

- 行 108: `path="data/match_features.parquet"`
  → `path = os.getenv("FEATURE_DEFINITIONS_PATH_108")`
  → 环境变量: `FEATURE_DEFINITIONS_PATH_108`

- 行 108: `timestamp_field="event_timestamp"`
  → `timestamp_field = os.getenv("FEATURE_DEFINITIONS_TIMESTAMP_FIELD_108")`
  → 环境变量: `FEATURE_DEFINITIONS_TIMESTAMP_FIELD_108`

- 行 108: `name="team_recent_stats_source"`
  → `name = os.getenv("FEATURE_DEFINITIONS_NAME_108")`
  → 环境变量: `FEATURE_DEFINITIONS_NAME_108`

- 行 112: `path="data/team_stats.parquet"`
  → `path = os.getenv("FEATURE_DEFINITIONS_PATH_112")`
  → 环境变量: `FEATURE_DEFINITIONS_PATH_112`

- 行 113: `timestamp_field="event_timestamp"`
  → `timestamp_field = os.getenv("FEATURE_DEFINITIONS_TIMESTAMP_FIELD_113")`
  → 环境变量: `FEATURE_DEFINITIONS_TIMESTAMP_FIELD_113`

- 行 114: `name="odds_features_source"`
  → `name = os.getenv("FEATURE_DEFINITIONS_NAME_114")`
  → 环境变量: `FEATURE_DEFINITIONS_NAME_114`

- 行 115: `path="data/odds_features.parquet"`
  → `path = os.getenv("FEATURE_DEFINITIONS_PATH_115")`
  → 环境变量: `FEATURE_DEFINITIONS_PATH_115`

- 行 115: `timestamp_field="event_timestamp"`
  → `timestamp_field = os.getenv("FEATURE_DEFINITIONS_TIMESTAMP_FIELD_115")`
  → 环境变量: `FEATURE_DEFINITIONS_TIMESTAMP_FIELD_115`

- 行 119: `name="match_features"`
  → `name = os.getenv("FEATURE_DEFINITIONS_NAME_119")`
  → 环境变量: `FEATURE_DEFINITIONS_NAME_119`

- 行 125: `name="team_recent_stats"`
  → `name = os.getenv("FEATURE_DEFINITIONS_NAME_125")`
  → 环境变量: `FEATURE_DEFINITIONS_NAME_125`

- 行 131: `name="odds_features"`
  → `name = os.getenv("FEATURE_DEFINITIONS_NAME_131")`
  → 环境变量: `FEATURE_DEFINITIONS_NAME_131`

- 行 139: `name="head_to_head_features"`
  → `name = os.getenv("FEATURE_DEFINITIONS_NAME_139")`
  → 环境变量: `FEATURE_DEFINITIONS_NAME_139`

### src/lineage/lineage_reporter.py

- 行 36: `str = "football_prediction"`
  → `str = os.getenv("LINEAGE_REPORTER_STR_36")`
  → 环境变量: `LINEAGE_REPORTER_STR_36`

- 行 124: `producer="football_prediction_lineage_reporter"`
  → `producer = os.getenv("LINEAGE_REPORTER_PRODUCER_124")`
  → 环境变量: `LINEAGE_REPORTER_PRODUCER_124`

- 行 201: `eventType="COMPLETE"`
  → `eventType = os.getenv("LINEAGE_REPORTER_EVENTTYPE_201")`
  → 环境变量: `LINEAGE_REPORTER_EVENTTYPE_201`

- 行 206: `producer="football_prediction_lineage_reporter"`
  → `producer = os.getenv("LINEAGE_REPORTER_PRODUCER_206")`
  → 环境变量: `LINEAGE_REPORTER_PRODUCER_206`

- 行 246: `programmingLanguage="PYTHON"`
  → `programmingLanguage = os.getenv("LINEAGE_REPORTER_PROGRAMMINGLANGUAGE_246")`
  → 环境变量: `LINEAGE_REPORTER_PROGRAMMINGLANGUAGE_246`

- 行 256: `producer="football_prediction_lineage_reporter"`
  → `producer = os.getenv("LINEAGE_REPORTER_PRODUCER_256")`
  → 环境变量: `LINEAGE_REPORTER_PRODUCER_256`

- 行 313: `source_location="src/data/collectors/"`
  → `source_location = os.getenv("LINEAGE_REPORTER_SOURCE_LOCATION_313")`
  → 环境变量: `LINEAGE_REPORTER_SOURCE_LOCATION_313`

- 行 375: `source_location="src/data/processing/"`
  → `source_location = os.getenv("LINEAGE_REPORTER_SOURCE_LOCATION_375")`
  → 环境变量: `LINEAGE_REPORTER_SOURCE_LOCATION_375`

### src/scheduler/recovery_handler.py

- 行 21: `TIMEOUT = "timeout"`
  → `TIMEOUT = os.getenv("RECOVERY_HANDLER_TIMEOUT_21")`
  → 环境变量: `RECOVERY_HANDLER_TIMEOUT_21`

- 行 21: `CONNECTION_ERROR = "connection_error"`
  → `CONNECTION_ERROR = os.getenv("RECOVERY_HANDLER_CONNECTION_ERROR_21")`
  → 环境变量: `RECOVERY_HANDLER_CONNECTION_ERROR_21`

- 行 22: `DATA_ERROR = "data_error"`
  → `DATA_ERROR = os.getenv("RECOVERY_HANDLER_DATA_ERROR_22")`
  → 环境变量: `RECOVERY_HANDLER_DATA_ERROR_22`

- 行 22: `RESOURCE_ERROR = "resource_error"`
  → `RESOURCE_ERROR = os.getenv("RECOVERY_HANDLER_RESOURCE_ERROR_22")`
  → 环境变量: `RECOVERY_HANDLER_RESOURCE_ERROR_22`

- 行 23: `PERMISSION_ERROR = "permission_error"`
  → `PERMISSION_ERROR = os.getenv("RECOVERY_HANDLER_PERMISSION_ERROR_23")`
  → 环境变量: `RECOVERY_HANDLER_PERMISSION_ERROR_23`

- 行 23: `UNKNOWN_ERROR = "unknown_error"`
  → `UNKNOWN_ERROR = os.getenv("RECOVERY_HANDLER_UNKNOWN_ERROR_23")`
  → 环境变量: `RECOVERY_HANDLER_UNKNOWN_ERROR_23`

- 行 25: `IMMEDIATE_RETRY = "immediate_retry"`
  → `IMMEDIATE_RETRY = os.getenv("RECOVERY_HANDLER_IMMEDIATE_RETRY_25")`
  → 环境变量: `RECOVERY_HANDLER_IMMEDIATE_RETRY_25`

- 行 25: `EXPONENTIAL_BACKOFF = "exponential_backoff"`
  → `EXPONENTIAL_BACKOFF = os.getenv("RECOVERY_HANDLER_EXPONENTIAL_BACKOFF_25")`
  → 环境变量: `RECOVERY_HANDLER_EXPONENTIAL_BACKOFF_25`

- 行 26: `FIXED_DELAY = "fixed_delay"`
  → `FIXED_DELAY = os.getenv("RECOVERY_HANDLER_FIXED_DELAY_26")`
  → 环境变量: `RECOVERY_HANDLER_FIXED_DELAY_26`

- 行 26: `MANUAL_INTERVENTION = "manual_intervention"`
  → `MANUAL_INTERVENTION = os.getenv("RECOVERY_HANDLER_MANUAL_INTERVENTION_26")`
  → 环境变量: `RECOVERY_HANDLER_MANUAL_INTERVENTION_26`

- 行 30: `SKIP_AND_CONTINUE = "skip_and_continue"`
  → `SKIP_AND_CONTINUE = os.getenv("RECOVERY_HANDLER_SKIP_AND_CONTINUE_30")`
  → 环境变量: `RECOVERY_HANDLER_SKIP_AND_CONTINUE_30`

- 行 519: `level="CRITICAL"`
  → `level = os.getenv("RECOVERY_HANDLER_LEVEL_519")`
  → 环境变量: `RECOVERY_HANDLER_LEVEL_519`

- 行 574: `level="WARNING"`
  → `level = os.getenv("RECOVERY_HANDLER_LEVEL_574")`
  → 环境变量: `RECOVERY_HANDLER_LEVEL_574`

### src/scheduler/celery_config.py

- 行 105: `task_default_queue = "default"`
  → `task_default_queue = os.getenv("CELERY_CONFIG_TASK_DEFAULT_QUEUE_105")`
  → 环境变量: `CELERY_CONFIG_TASK_DEFAULT_QUEUE_105`

### src/scheduler/task_scheduler.py

- 行 204: `task_id="fixtures_collection"`
  → `task_id = os.getenv("TASK_SCHEDULER_TASK_ID_204")`
  → 环境变量: `TASK_SCHEDULER_TASK_ID_204`

- 行 204: `name="赛程数据采集"`
  → `name = os.getenv("TASK_SCHEDULER_NAME_204")`
  → 环境变量: `TASK_SCHEDULER_NAME_204`

- 行 205: `cron_expression="0 2 * * *"`
  → `cron_expression = os.getenv("TASK_SCHEDULER_CRON_EXPRESSION_205")`
  → 环境变量: `TASK_SCHEDULER_CRON_EXPRESSION_205`

- 行 208: `description="采集比赛赛程数据，更新比赛安排信息"`
  → `description = os.getenv("TASK_SCHEDULER_DESCRIPTION_208")`
  → 环境变量: `TASK_SCHEDULER_DESCRIPTION_208`

- 行 211: `task_id="odds_collection"`
  → `task_id = os.getenv("TASK_SCHEDULER_TASK_ID_211")`
  → 环境变量: `TASK_SCHEDULER_TASK_ID_211`

- 行 211: `name="赔率数据采集"`
  → `name = os.getenv("TASK_SCHEDULER_NAME_211")`
  → 环境变量: `TASK_SCHEDULER_NAME_211`

- 行 213: `cron_expression="*/5 * * * *"`
  → `cron_expression = os.getenv("TASK_SCHEDULER_CRON_EXPRESSION_213")`
  → 环境变量: `TASK_SCHEDULER_CRON_EXPRESSION_213`

- 行 216: `description="采集博彩公司赔率数据，支持实时更新"`
  → `description = os.getenv("TASK_SCHEDULER_DESCRIPTION_216")`
  → 环境变量: `TASK_SCHEDULER_DESCRIPTION_216`

- 行 218: `task_id="live_scores_collection"`
  → `task_id = os.getenv("TASK_SCHEDULER_TASK_ID_218")`
  → 环境变量: `TASK_SCHEDULER_TASK_ID_218`

- 行 220: `name="实时比分采集"`
  → `name = os.getenv("TASK_SCHEDULER_NAME_220")`
  → 环境变量: `TASK_SCHEDULER_NAME_220`

- 行 221: `cron_expression="*/2 * * * *"`
  → `cron_expression = os.getenv("TASK_SCHEDULER_CRON_EXPRESSION_221")`
  → 环境变量: `TASK_SCHEDULER_CRON_EXPRESSION_221`

- 行 227: `description="采集比赛实时比分和状态数据"`
  → `description = os.getenv("TASK_SCHEDULER_DESCRIPTION_227")`
  → 环境变量: `TASK_SCHEDULER_DESCRIPTION_227`

- 行 227: `task_id="feature_calculation"`
  → `task_id = os.getenv("TASK_SCHEDULER_TASK_ID_227")`
  → 环境变量: `TASK_SCHEDULER_TASK_ID_227`

- 行 229: `cron_expression="0 * * * *"`
  → `cron_expression = os.getenv("TASK_SCHEDULER_CRON_EXPRESSION_229")`
  → 环境变量: `TASK_SCHEDULER_CRON_EXPRESSION_229`

- 行 236: `description="计算机器学习特征，为预测模型提供数据"`
  → `description = os.getenv("TASK_SCHEDULER_DESCRIPTION_236")`
  → 环境变量: `TASK_SCHEDULER_DESCRIPTION_236`

- 行 238: `task_id="data_cleanup"`
  → `task_id = os.getenv("TASK_SCHEDULER_TASK_ID_238")`
  → 环境变量: `TASK_SCHEDULER_TASK_ID_238`

- 行 238: `cron_expression="0 3 * * 0"`
  → `cron_expression = os.getenv("TASK_SCHEDULER_CRON_EXPRESSION_238")`
  → 环境变量: `TASK_SCHEDULER_CRON_EXPRESSION_238`

- 行 242: `description="清理过期数据，优化数据库性能"`
  → `description = os.getenv("TASK_SCHEDULER_DESCRIPTION_242")`
  → 环境变量: `TASK_SCHEDULER_DESCRIPTION_242`

- 行 400: `name="TaskScheduler"`
  → `name = os.getenv("TASK_SCHEDULER_NAME_400")`
  → 环境变量: `TASK_SCHEDULER_NAME_400`

### src/scheduler/tasks.py

- 行 283: `status = 'scheduled'`
  → `status = os.getenv("TASKS_STATUS_283")`
  → 环境变量: `TASKS_STATUS_283`

- 行 740: `file=" + backup_path,
                        "`
  → `file = os.getenv("TASKS_FILE_740")`
  → 环境变量: `TASKS_FILE_740`

- 行 900: `status = 'scheduled'`
  → `status = os.getenv("TASKS_STATUS_900")`
  → 环境变量: `TASKS_STATUS_900`

- 行 911: `status = 'scheduled'`
  → `status = os.getenv("TASKS_STATUS_911")`
  → 环境变量: `TASKS_STATUS_911`

### scripts/fix_test_decorators.py

- 行 20: `reason="Function not implemented in src\.api\.data"`
  → `reason = os.getenv("FIX_TEST_DECORATORS_REASON_20")`
  → 环境变量: `FIX_TEST_DECORATORS_REASON_20`

### scripts/auto_boost_coverage.py

- 行 15: `str = "src/api"`
  → `str = os.getenv("AUTO_BOOST_COVERAGE_STR_15")`
  → 环境变量: `AUTO_BOOST_COVERAGE_STR_15`

- 行 15: `str = "tests/unit/api"`
  → `str = os.getenv("AUTO_BOOST_COVERAGE_STR_15")`
  → 环境变量: `AUTO_BOOST_COVERAGE_STR_15`

- 行 290: `description="自动覆盖率提升工具"`
  → `description = os.getenv("AUTO_BOOST_COVERAGE_DESCRIPTION_290")`
  → 环境变量: `AUTO_BOOST_COVERAGE_DESCRIPTION_290`

- 行 292: `help="要提升的模块名（不指定则处理所有模块）"`
  → `help = os.getenv("AUTO_BOOST_COVERAGE_HELP_292")`
  → 环境变量: `AUTO_BOOST_COVERAGE_HELP_292`

- 行 296: `default="src/api"`
  → `default = os.getenv("AUTO_BOOST_COVERAGE_DEFAULT_296")`
  → 环境变量: `AUTO_BOOST_COVERAGE_DEFAULT_296`

- 行 299: `default="tests/unit/api"`
  → `default = os.getenv("AUTO_BOOST_COVERAGE_DEFAULT_299")`
  → 环境变量: `AUTO_BOOST_COVERAGE_DEFAULT_299`

### scripts/cleanup_docs.py

- 行 358: `description="文档清理工具"`
  → `description = os.getenv("CLEANUP_DOCS_DESCRIPTION_358")`
  → 环境变量: `CLEANUP_DOCS_DESCRIPTION_358`

- 行 359: `help="项目根目录路径"`
  → `help = os.getenv("CLEANUP_DOCS_HELP_359")`
  → 环境变量: `CLEANUP_DOCS_HELP_359`

- 行 359: `action="store_true"`
  → `action = os.getenv("CLEANUP_DOCS_ACTION_359")`
  → 环境变量: `CLEANUP_DOCS_ACTION_359`

- 行 359: `help="试运行，不实际删除文件"`
  → `help = os.getenv("CLEANUP_DOCS_HELP_359")`
  → 环境变量: `CLEANUP_DOCS_HELP_359`

### scripts/fix_model_integration.py

- 行 10: `file_path = 'tests/integration/models/test_model_integration.py'`
  → `file_path = os.getenv("FIX_MODEL_INTEGRATION_FILE_PATH_10")`
  → 环境变量: `FIX_MODEL_INTEGRATION_FILE_PATH_10`

### scripts/verify_requirements.py

- 行 340: `help="输出报告到文件"`
  → `help = os.getenv("VERIFY_REQUIREMENTS_HELP_340")`
  → 环境变量: `VERIFY_REQUIREMENTS_HELP_340`

- 行 340: `action='store_true'`
  → `action = os.getenv("VERIFY_REQUIREMENTS_ACTION_340")`
  → 环境变量: `VERIFY_REQUIREMENTS_ACTION_340`

- 行 341: `help="尝试修复一些问题"`
  → `help = os.getenv("VERIFY_REQUIREMENTS_HELP_341")`
  → 环境变量: `VERIFY_REQUIREMENTS_HELP_341`

### scripts/update_predictions_results.py

- 行 396: `help="更新预测结果"`
  → `help = os.getenv("UPDATE_PREDICTIONS_RESULTS_HELP_396")`
  → 环境变量: `UPDATE_PREDICTIONS_RESULTS_HELP_396`

- 行 396: `help="生成准确率报告"`
  → `help = os.getenv("UPDATE_PREDICTIONS_RESULTS_HELP_396")`
  → 环境变量: `UPDATE_PREDICTIONS_RESULTS_HELP_396`

- 行 397: `help="计算准确率趋势"`
  → `help = os.getenv("UPDATE_PREDICTIONS_RESULTS_HELP_397")`
  → 环境变量: `UPDATE_PREDICTIONS_RESULTS_HELP_397`

- 行 398: `help="移动平均窗口大小"`
  → `help = os.getenv("UPDATE_PREDICTIONS_RESULTS_HELP_398")`
  → 环境变量: `UPDATE_PREDICTIONS_RESULTS_HELP_398`

- 行 399: `help="单次处理限制"`
  → `help = os.getenv("UPDATE_PREDICTIONS_RESULTS_HELP_399")`
  → 环境变量: `UPDATE_PREDICTIONS_RESULTS_HELP_399`

### scripts/feast_init.py

- 行 98: `description="球队实体，用于球队级别的特征"`
  → `description = os.getenv("FEAST_INIT_DESCRIPTION_98")`
  → 环境变量: `FEAST_INIT_DESCRIPTION_98`

- 行 102: `description="比赛实体，用于比赛级别的特征"`
  → `description = os.getenv("FEAST_INIT_DESCRIPTION_102")`
  → 环境变量: `FEAST_INIT_DESCRIPTION_102`

- 行 112: `name="team_performance_source"`
  → `name = os.getenv("FEAST_INIT_NAME_112")`
  → 环境变量: `FEAST_INIT_NAME_112`

- 行 129: `timestamp_field="event_timestamp"`
  → `timestamp_field = os.getenv("FEAST_INIT_TIMESTAMP_FIELD_129")`
  → 环境变量: `FEAST_INIT_TIMESTAMP_FIELD_129`

- 行 131: `name="historical_matchup_source"`
  → `name = os.getenv("FEAST_INIT_NAME_131")`
  → 环境变量: `FEAST_INIT_NAME_131`

- 行 150: `timestamp_field="event_timestamp"`
  → `timestamp_field = os.getenv("FEAST_INIT_TIMESTAMP_FIELD_150")`
  → 环境变量: `FEAST_INIT_TIMESTAMP_FIELD_150`

- 行 152: `name="odds_source"`
  → `name = os.getenv("FEAST_INIT_NAME_152")`
  → 环境变量: `FEAST_INIT_NAME_152`

- 行 169: `timestamp_field="event_timestamp"`
  → `timestamp_field = os.getenv("FEAST_INIT_TIMESTAMP_FIELD_169")`
  → 环境变量: `FEAST_INIT_TIMESTAMP_FIELD_169`

- 行 177: `name="team_recent_performance"`
  → `name = os.getenv("FEAST_INIT_NAME_177")`
  → 环境变量: `FEAST_INIT_NAME_177`

- 行 183: `name="recent_5_wins"`
  → `name = os.getenv("FEAST_INIT_NAME_183")`
  → 环境变量: `FEAST_INIT_NAME_183`

- 行 184: `name="recent_5_draws"`
  → `name = os.getenv("FEAST_INIT_NAME_184")`
  → 环境变量: `FEAST_INIT_NAME_184`

- 行 185: `name="recent_5_losses"`
  → `name = os.getenv("FEAST_INIT_NAME_185")`
  → 环境变量: `FEAST_INIT_NAME_185`

- 行 187: `name="recent_5_goals_for"`
  → `name = os.getenv("FEAST_INIT_NAME_187")`
  → 环境变量: `FEAST_INIT_NAME_187`

- 行 188: `name="recent_5_goals_against"`
  → `name = os.getenv("FEAST_INIT_NAME_188")`
  → 环境变量: `FEAST_INIT_NAME_188`

- 行 189: `name="recent_5_points"`
  → `name = os.getenv("FEAST_INIT_NAME_189")`
  → 环境变量: `FEAST_INIT_NAME_189`

- 行 189: `name="recent_5_home_wins"`
  → `name = os.getenv("FEAST_INIT_NAME_189")`
  → 环境变量: `FEAST_INIT_NAME_189`

- 行 190: `name="recent_5_away_wins"`
  → `name = os.getenv("FEAST_INIT_NAME_190")`
  → 环境变量: `FEAST_INIT_NAME_190`

- 行 191: `name="recent_5_home_goals_for"`
  → `name = os.getenv("FEAST_INIT_NAME_191")`
  → 环境变量: `FEAST_INIT_NAME_191`

- 行 192: `name="recent_5_away_goals_for"`
  → `name = os.getenv("FEAST_INIT_NAME_192")`
  → 环境变量: `FEAST_INIT_NAME_192`

- 行 194: `description="球队近期表现特征（最近5场比赛）"`
  → `description = os.getenv("FEAST_INIT_DESCRIPTION_194")`
  → 环境变量: `FEAST_INIT_DESCRIPTION_194`

- 行 195: `name="historical_matchup"`
  → `name = os.getenv("FEAST_INIT_NAME_195")`
  → 环境变量: `FEAST_INIT_NAME_195`

- 行 197: `name="home_team_id"`
  → `name = os.getenv("FEAST_INIT_NAME_197")`
  → 环境变量: `FEAST_INIT_NAME_197`

- 行 199: `name="away_team_id"`
  → `name = os.getenv("FEAST_INIT_NAME_199")`
  → 环境变量: `FEAST_INIT_NAME_199`

- 行 199: `name="h2h_total_matches"`
  → `name = os.getenv("FEAST_INIT_NAME_199")`
  → 环境变量: `FEAST_INIT_NAME_199`

- 行 202: `name="h2h_home_wins"`
  → `name = os.getenv("FEAST_INIT_NAME_202")`
  → 环境变量: `FEAST_INIT_NAME_202`

- 行 203: `name="h2h_away_wins"`
  → `name = os.getenv("FEAST_INIT_NAME_203")`
  → 环境变量: `FEAST_INIT_NAME_203`

- 行 205: `name="h2h_draws"`
  → `name = os.getenv("FEAST_INIT_NAME_205")`
  → 环境变量: `FEAST_INIT_NAME_205`

- 行 206: `name="h2h_home_goals_total"`
  → `name = os.getenv("FEAST_INIT_NAME_206")`
  → 环境变量: `FEAST_INIT_NAME_206`

- 行 207: `name="h2h_away_goals_total"`
  → `name = os.getenv("FEAST_INIT_NAME_207")`
  → 环境变量: `FEAST_INIT_NAME_207`

- 行 208: `description="球队历史对战特征"`
  → `description = os.getenv("FEAST_INIT_DESCRIPTION_208")`
  → 环境变量: `FEAST_INIT_DESCRIPTION_208`

- 行 209: `name="odds_features"`
  → `name = os.getenv("FEAST_INIT_NAME_209")`
  → 环境变量: `FEAST_INIT_NAME_209`

- 行 211: `name="home_odds_avg"`
  → `name = os.getenv("FEAST_INIT_NAME_211")`
  → 环境变量: `FEAST_INIT_NAME_211`

- 行 212: `name="draw_odds_avg"`
  → `name = os.getenv("FEAST_INIT_NAME_212")`
  → 环境变量: `FEAST_INIT_NAME_212`

- 行 213: `name="away_odds_avg"`
  → `name = os.getenv("FEAST_INIT_NAME_213")`
  → 环境变量: `FEAST_INIT_NAME_213`

- 行 213: `name="home_implied_probability"`
  → `name = os.getenv("FEAST_INIT_NAME_213")`
  → 环境变量: `FEAST_INIT_NAME_213`

- 行 216: `name="draw_implied_probability"`
  → `name = os.getenv("FEAST_INIT_NAME_216")`
  → 环境变量: `FEAST_INIT_NAME_216`

- 行 218: `name="away_implied_probability"`
  → `name = os.getenv("FEAST_INIT_NAME_218")`
  → 环境变量: `FEAST_INIT_NAME_218`

- 行 220: `name="bookmaker_count"`
  → `name = os.getenv("FEAST_INIT_NAME_220")`
  → 环境变量: `FEAST_INIT_NAME_220`

- 行 221: `name="bookmaker_consensus"`
  → `name = os.getenv("FEAST_INIT_NAME_221")`
  → 环境变量: `FEAST_INIT_NAME_221`

- 行 223: `description="赔率衍生特征"`
  → `description = os.getenv("FEAST_INIT_DESCRIPTION_223")`
  → 环境变量: `FEAST_INIT_DESCRIPTION_223`

### scripts/run_pipeline.py

- 行 88: `subset="match_id"`
  → `subset = os.getenv("RUN_PIPELINE_SUBSET_88")`
  → 环境变量: `RUN_PIPELINE_SUBSET_88`

- 行 137: `multi_class="multinomial"`
  → `multi_class = os.getenv("RUN_PIPELINE_MULTI_CLASS_137")`
  → 环境变量: `RUN_PIPELINE_MULTI_CLASS_137`

- 行 186: `format="%(asctime)s %(levelname)s %(message)s"`
  → `format = os.getenv("RUN_PIPELINE_FORMAT_186")`
  → 环境变量: `RUN_PIPELINE_FORMAT_186`

- 行 190: `description="Synthetic pipeline runner for CI"`
  → `description = os.getenv("RUN_PIPELINE_DESCRIPTION_190")`
  → 环境变量: `RUN_PIPELINE_DESCRIPTION_190`

- 行 194: `action="store_true"`
  → `action = os.getenv("RUN_PIPELINE_ACTION_194")`
  → 环境变量: `RUN_PIPELINE_ACTION_194`

### scripts/auto_ci_updater.py

- 行 985: `help="防御机制JSON文件路径"`
  → `help = os.getenv("AUTO_CI_UPDATER_HELP_985")`
  → 环境变量: `AUTO_CI_UPDATER_HELP_985`

- 行 986: `help="项目根目录路径"`
  → `help = os.getenv("AUTO_CI_UPDATER_HELP_986")`
  → 环境变量: `AUTO_CI_UPDATER_HELP_986`

- 行 986: `help="仅验证现有集成"`
  → `help = os.getenv("AUTO_CI_UPDATER_HELP_986")`
  → 环境变量: `AUTO_CI_UPDATER_HELP_986`

- 行 987: `help="仅更新Makefile"`
  → `help = os.getenv("AUTO_CI_UPDATER_HELP_987")`
  → 环境变量: `AUTO_CI_UPDATER_HELP_987`

- 行 988: `help="仅更新GitHub Actions"`
  → `help = os.getenv("AUTO_CI_UPDATER_HELP_988")`
  → 环境变量: `AUTO_CI_UPDATER_HELP_988`

- 行 989: `help="显示集成摘要"`
  → `help = os.getenv("AUTO_CI_UPDATER_HELP_989")`
  → 环境变量: `AUTO_CI_UPDATER_HELP_989`

### scripts/coverage_monitor.py

- 行 253: `description="覆盖率监控工具"`
  → `description = os.getenv("COVERAGE_MONITOR_DESCRIPTION_253")`
  → 环境变量: `COVERAGE_MONITOR_DESCRIPTION_253`

- 行 254: `action="store_true"`
  → `action = os.getenv("COVERAGE_MONITOR_ACTION_254")`
  → 环境变量: `COVERAGE_MONITOR_ACTION_254`

- 行 255: `help="启用持续监控模式"`
  → `help = os.getenv("COVERAGE_MONITOR_HELP_255")`
  → 环境变量: `COVERAGE_MONITOR_HELP_255`

- 行 258: `help="监控间隔（分钟），默认60分钟"`
  → `help = os.getenv("COVERAGE_MONITOR_HELP_258")`
  → 环境变量: `COVERAGE_MONITOR_HELP_258`

- 行 263: `help="历史数据文件路径"`
  → `help = os.getenv("COVERAGE_MONITOR_HELP_263")`
  → 环境变量: `COVERAGE_MONITOR_HELP_263`

### scripts/generate_test_report.py

- 行 86: `trend = "stable"`
  → `trend = os.getenv("GENERATE_TEST_REPORT_TREND_86")`
  → 环境变量: `GENERATE_TEST_REPORT_TREND_86`

- 行 88: `trend = "improving"`
  → `trend = os.getenv("GENERATE_TEST_REPORT_TREND_88")`
  → 环境变量: `GENERATE_TEST_REPORT_TREND_88`

- 行 90: `trend = "degrading"`
  → `trend = os.getenv("GENERATE_TEST_REPORT_TREND_90")`
  → 环境变量: `GENERATE_TEST_REPORT_TREND_90`

- 行 164: `status = "improving"`
  → `status = os.getenv("GENERATE_TEST_REPORT_STATUS_164")`
  → 环境变量: `GENERATE_TEST_REPORT_STATUS_164`

- 行 164: `status = "degrading"`
  → `status = os.getenv("GENERATE_TEST_REPORT_STATUS_164")`
  → 环境变量: `GENERATE_TEST_REPORT_STATUS_164`

- 行 167: `status = "stable"`
  → `status = os.getenv("GENERATE_TEST_REPORT_STATUS_167")`
  → 环境变量: `GENERATE_TEST_REPORT_STATUS_167`

- 行 322: `name="viewport"`
  → `name = os.getenv("GENERATE_TEST_REPORT_NAME_322")`
  → 环境变量: `GENERATE_TEST_REPORT_NAME_322`

- 行 323: `content="width=device-width, initial-scale=1.0"`
  → `content = os.getenv("GENERATE_TEST_REPORT_CONTENT_323")`
  → 环境变量: `GENERATE_TEST_REPORT_CONTENT_323`

- 行 459: `class="container"`
  → `class = os.getenv("GENERATE_TEST_REPORT_CLASS_459")`
  → 环境变量: `GENERATE_TEST_REPORT_CLASS_459`

- 行 460: `class="header"`
  → `class = os.getenv("GENERATE_TEST_REPORT_CLASS_460")`
  → 环境变量: `GENERATE_TEST_REPORT_CLASS_460`

- 行 468: `class="summary-grid"`
  → `class = os.getenv("GENERATE_TEST_REPORT_CLASS_468")`
  → 环境变量: `GENERATE_TEST_REPORT_CLASS_468`

- 行 471: `class="summary-card"`
  → `class = os.getenv("GENERATE_TEST_REPORT_CLASS_471")`
  → 环境变量: `GENERATE_TEST_REPORT_CLASS_471`

- 行 474: `class="summary-card"`
  → `class = os.getenv("GENERATE_TEST_REPORT_CLASS_474")`
  → 环境变量: `GENERATE_TEST_REPORT_CLASS_474`

- 行 478: `style="color: #666;"`
  → `style = os.getenv("GENERATE_TEST_REPORT_STYLE_478")`
  → 环境变量: `GENERATE_TEST_REPORT_STYLE_478`

- 行 480: `class="summary-card"`
  → `class = os.getenv("GENERATE_TEST_REPORT_CLASS_480")`
  → 环境变量: `GENERATE_TEST_REPORT_CLASS_480`

- 行 481: `style="font-size: 1.5rem;"`
  → `style = os.getenv("GENERATE_TEST_REPORT_STYLE_481")`
  → 环境变量: `GENERATE_TEST_REPORT_STYLE_481`

- 行 484: `class="summary-card"`
  → `class = os.getenv("GENERATE_TEST_REPORT_CLASS_484")`
  → 环境变量: `GENERATE_TEST_REPORT_CLASS_484`

- 行 487: `style="color: #666;"`
  → `style = os.getenv("GENERATE_TEST_REPORT_STYLE_487")`
  → 环境变量: `GENERATE_TEST_REPORT_STYLE_487`

- 行 490: `class="section"`
  → `class = os.getenv("GENERATE_TEST_REPORT_CLASS_490")`
  → 环境变量: `GENERATE_TEST_REPORT_CLASS_490`

- 行 491: `style="list-style: none; padding: 0;"`
  → `style = os.getenv("GENERATE_TEST_REPORT_STYLE_491")`
  → 环境变量: `GENERATE_TEST_REPORT_STYLE_491`

- 行 492: `style="padding: 8px 0;"`
  → `style = os.getenv("GENERATE_TEST_REPORT_STYLE_492")`
  → 环境变量: `GENERATE_TEST_REPORT_STYLE_492`

- 行 495: `class="section"`
  → `class = os.getenv("GENERATE_TEST_REPORT_CLASS_495")`
  → 环境变量: `GENERATE_TEST_REPORT_CLASS_495`

- 行 497: `class="recommendations"`
  → `class = os.getenv("GENERATE_TEST_REPORT_CLASS_497")`
  → 环境变量: `GENERATE_TEST_REPORT_CLASS_497`

- 行 498: `class="footer"`
  → `class = os.getenv("GENERATE_TEST_REPORT_CLASS_498")`
  → 环境变量: `GENERATE_TEST_REPORT_CLASS_498`

- 行 510: `class="recommendation-item {priority_class}"`
  → `class = os.getenv("GENERATE_TEST_REPORT_CLASS_510")`
  → 环境变量: `GENERATE_TEST_REPORT_CLASS_510`

- 行 512: `style="margin-top: 10px; padding-left: 20px;"`
  → `style = os.getenv("GENERATE_TEST_REPORT_STYLE_512")`
  → 环境变量: `GENERATE_TEST_REPORT_STYLE_512`

- 行 589: `description="测试质量报告生成器"`
  → `description = os.getenv("GENERATE_TEST_REPORT_DESCRIPTION_589")`
  → 环境变量: `GENERATE_TEST_REPORT_DESCRIPTION_589`

- 行 595: `action="store_true"`
  → `action = os.getenv("GENERATE_TEST_REPORT_ACTION_595")`
  → 环境变量: `GENERATE_TEST_REPORT_ACTION_595`

### scripts/defense_validator.py

- 行 679: `user_input = "print('`
  → `user_input = os.getenv("DEFENSE_VALIDATOR_USER_INPUT_679")`
  → 环境变量: `DEFENSE_VALIDATOR_USER_INPUT_679`

- 行 1039: `help="防御机制JSON文件路径"`
  → `help = os.getenv("DEFENSE_VALIDATOR_HELP_1039")`
  → 环境变量: `DEFENSE_VALIDATOR_HELP_1039`

- 行 1039: `help="原始问题JSON文件路径"`
  → `help = os.getenv("DEFENSE_VALIDATOR_HELP_1039")`
  → 环境变量: `DEFENSE_VALIDATOR_HELP_1039`

- 行 1040: `help="项目根目录路径"`
  → `help = os.getenv("DEFENSE_VALIDATOR_HELP_1040")`
  → 环境变量: `DEFENSE_VALIDATOR_HELP_1040`

- 行 1040: `help="验证结果输出文件路径"`
  → `help = os.getenv("DEFENSE_VALIDATOR_HELP_1040")`
  → 环境变量: `DEFENSE_VALIDATOR_HELP_1040`

- 行 1041: `help="仅验证测试文件"`
  → `help = os.getenv("DEFENSE_VALIDATOR_HELP_1041")`
  → 环境变量: `DEFENSE_VALIDATOR_HELP_1041`

- 行 1042: `help="仅验证配置文件"`
  → `help = os.getenv("DEFENSE_VALIDATOR_HELP_1042")`
  → 环境变量: `DEFENSE_VALIDATOR_HELP_1042`

- 行 1043: `help="仅验证防御效果"`
  → `help = os.getenv("DEFENSE_VALIDATOR_HELP_1043")`
  → 环境变量: `DEFENSE_VALIDATOR_HELP_1043`

- 行 1044: `help="显示验证摘要"`
  → `help = os.getenv("DEFENSE_VALIDATOR_HELP_1044")`
  → 环境变量: `DEFENSE_VALIDATOR_HELP_1044`

- 行 1044: `help="显示详细结果"`
  → `help = os.getenv("DEFENSE_VALIDATOR_HELP_1044")`
  → 环境变量: `DEFENSE_VALIDATOR_HELP_1044`

### scripts/fix_undefined_vars.py

- 行 372: `description='检测和修复未定义变量 (F821)'`
  → `description = os.getenv("FIX_UNDEFINED_VARS_DESCRIPTION_372")`
  → 环境变量: `FIX_UNDEFINED_VARS_DESCRIPTION_372`

- 行 373: `help='要修复的目录 (默认: 当前目录)'`
  → `help = os.getenv("FIX_UNDEFINED_VARS_HELP_373")`
  → 环境变量: `FIX_UNDEFINED_VARS_HELP_373`

- 行 373: `default='docs/_reports/UNDEFINED_VARS_REPORT.md'`
  → `default = os.getenv("FIX_UNDEFINED_VARS_DEFAULT_373")`
  → 环境变量: `FIX_UNDEFINED_VARS_DEFAULT_373`

- 行 374: `help='报告输出路径 (默认: docs/_reports/UNDEFINED_VARS_REPORT.md)'`
  → `help = os.getenv("FIX_UNDEFINED_VARS_HELP_374")`
  → 环境变量: `FIX_UNDEFINED_VARS_HELP_374`

### scripts/fix_critical_issues.py

- 行 117: `description="AICultureKit 致命问题检查工具"`
  → `description = os.getenv("FIX_CRITICAL_ISSUES_DESCRIPTION_117")`
  → 环境变量: `FIX_CRITICAL_ISSUES_DESCRIPTION_117`

- 行 126: `action="store_true"`
  → `action = os.getenv("FIX_CRITICAL_ISSUES_ACTION_126")`
  → 环境变量: `FIX_CRITICAL_ISSUES_ACTION_126`

- 行 127: `help="仅检查问题，不执行修复"`
  → `help = os.getenv("FIX_CRITICAL_ISSUES_HELP_127")`
  → 环境变量: `FIX_CRITICAL_ISSUES_HELP_127`

- 行 127: `action="store_true"`
  → `action = os.getenv("FIX_CRITICAL_ISSUES_ACTION_127")`
  → 环境变量: `FIX_CRITICAL_ISSUES_ACTION_127`

- 行 127: `help="自动修复模式（未实现，请手动修复）"`
  → `help = os.getenv("FIX_CRITICAL_ISSUES_HELP_127")`
  → 环境变量: `FIX_CRITICAL_ISSUES_HELP_127`

- 行 131: `help="项目根目录路径 (默认: 当前目录)"`
  → `help = os.getenv("FIX_CRITICAL_ISSUES_HELP_131")`
  → 环境变量: `FIX_CRITICAL_ISSUES_HELP_131`

### scripts/lock_dependencies.py

- 行 465: `description="依赖锁定工具"`
  → `description = os.getenv("LOCK_DEPENDENCIES_DESCRIPTION_465")`
  → 环境变量: `LOCK_DEPENDENCIES_DESCRIPTION_465`

- 行 469: `help="requirements文件路径"`
  → `help = os.getenv("LOCK_DEPENDENCIES_HELP_469")`
  → 环境变量: `LOCK_DEPENDENCIES_HELP_469`

### scripts/alert_verification.py

- 行 172: `task_name="{task_name}"`
  → `task_name = os.getenv("ALERT_VERIFICATION_TASK_NAME_172")`
  → 环境变量: `ALERT_VERIFICATION_TASK_NAME_172`

- 行 220: `task_name="{task}"`
  → `task_name = os.getenv("ALERT_VERIFICATION_TASK_NAME_220")`
  → 环境变量: `ALERT_VERIFICATION_TASK_NAME_220`

- 行 385: `format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"`
  → `format = os.getenv("ALERT_VERIFICATION_FORMAT_385")`
  → 环境变量: `ALERT_VERIFICATION_FORMAT_385`

- 行 417: `final_status = "✅ 完全成功"`
  → `final_status = os.getenv("ALERT_VERIFICATION_FINAL_STATUS_417")`
  → 环境变量: `ALERT_VERIFICATION_FINAL_STATUS_417`

### scripts/alert_verification_mock.py

- 行 420: `format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"`
  → `format = os.getenv("ALERT_VERIFICATION_MOCK_FORMAT_420")`
  → 环境变量: `ALERT_VERIFICATION_MOCK_FORMAT_420`

- 行 452: `final_status = "✅ 完全成功"`
  → `final_status = os.getenv("ALERT_VERIFICATION_MOCK_FINAL_STATUS_452")`
  → 环境变量: `ALERT_VERIFICATION_MOCK_FINAL_STATUS_452`

### scripts/ci_monitor.py

- 行 401: `description="GitHub Actions CI监控工具"`
  → `description = os.getenv("CI_MONITOR_DESCRIPTION_401")`
  → 环境变量: `CI_MONITOR_DESCRIPTION_401`

- 行 412: `action="store_true"`
  → `action = os.getenv("CI_MONITOR_ACTION_412")`
  → 环境变量: `CI_MONITOR_ACTION_412`

- 行 412: `help="启动实时监控模式"`
  → `help = os.getenv("CI_MONITOR_HELP_412")`
  → 环境变量: `CI_MONITOR_HELP_412`

- 行 412: `help="深度分析指定的工作流运行ID"`
  → `help = os.getenv("CI_MONITOR_HELP_412")`
  → 环境变量: `CI_MONITOR_HELP_412`

- 行 414: `help="显示历史运行记录数量 (默认: 10)"`
  → `help = os.getenv("CI_MONITOR_HELP_414")`
  → 环境变量: `CI_MONITOR_HELP_414`

- 行 417: `help="实时监控刷新间隔(秒) (默认: 30)"`
  → `help = os.getenv("CI_MONITOR_HELP_417")`
  → 环境变量: `CI_MONITOR_HELP_417`

### scripts/migrate_config.py

- 行 76: `description="添加Redis配置"`
  → `description = os.getenv("MIGRATE_CONFIG_DESCRIPTION_76")`
  → 环境变量: `MIGRATE_CONFIG_DESCRIPTION_76`

- 行 104: `description="重命名API配置变量"`
  → `description = os.getenv("MIGRATE_CONFIG_DESCRIPTION_104")`
  → 环境变量: `MIGRATE_CONFIG_DESCRIPTION_104`

- 行 123: `description="添加缓存配置"`
  → `description = os.getenv("MIGRATE_CONFIG_DESCRIPTION_123")`
  → 环境变量: `MIGRATE_CONFIG_DESCRIPTION_123`

- 行 138: `description="添加监控配置"`
  → `description = os.getenv("MIGRATE_CONFIG_DESCRIPTION_138")`
  → 环境变量: `MIGRATE_CONFIG_DESCRIPTION_138`

- 行 159: `description="增强安全配置"`
  → `description = os.getenv("MIGRATE_CONFIG_DESCRIPTION_159")`
  → 环境变量: `MIGRATE_CONFIG_DESCRIPTION_159`

- 行 175: `description="添加性能配置"`
  → `description = os.getenv("MIGRATE_CONFIG_DESCRIPTION_175")`
  → 环境变量: `MIGRATE_CONFIG_DESCRIPTION_175`

- 行 475: `description="配置迁移工具"`
  → `description = os.getenv("MIGRATE_CONFIG_DESCRIPTION_475")`
  → 环境变量: `MIGRATE_CONFIG_DESCRIPTION_475`

- 行 484: `help="环境文件路径"`
  → `help = os.getenv("MIGRATE_CONFIG_HELP_484")`
  → 环境变量: `MIGRATE_CONFIG_HELP_484`

- 行 486: `action='store_true'`
  → `action = os.getenv("MIGRATE_CONFIG_ACTION_486")`
  → 环境变量: `MIGRATE_CONFIG_ACTION_486`

### scripts/test_performance_migration.py

- 行 33: `table_name = 'matches_2025_09'`
  → `table_name = os.getenv("TEST_PERFORMANCE_MIGRATION_TABLE_NAME_33")`
  → 环境变量: `TEST_PERFORMANCE_MIGRATION_TABLE_NAME_33`

- 行 51: `constraint_type = 'FOREIGN KEY'`
  → `constraint_type = os.getenv("TEST_PERFORMANCE_MIGRATION_CONSTRAINT_TYPE_51")`
  → 环境变量: `TEST_PERFORMANCE_MIGRATION_CONSTRAINT_TYPE_51`

- 行 68: `table_name = 'matches'`
  → `table_name = os.getenv("TEST_PERFORMANCE_MIGRATION_TABLE_NAME_68")`
  → 环境变量: `TEST_PERFORMANCE_MIGRATION_TABLE_NAME_68`

- 行 68: `constraint_type = 'PRIMARY KEY'`
  → `constraint_type = os.getenv("TEST_PERFORMANCE_MIGRATION_CONSTRAINT_TYPE_68")`
  → 环境变量: `TEST_PERFORMANCE_MIGRATION_CONSTRAINT_TYPE_68`

### scripts/config_crypto.py

- 行 289: `description="配置加密存储工具"`
  → `description = os.getenv("CONFIG_CRYPTO_DESCRIPTION_289")`
  → 环境变量: `CONFIG_CRYPTO_DESCRIPTION_289`

- 行 292: `help="要执行的命令"`
  → `help = os.getenv("CONFIG_CRYPTO_HELP_292")`
  → 环境变量: `CONFIG_CRYPTO_HELP_292`

- 行 293: `help="输入文件路径"`
  → `help = os.getenv("CONFIG_CRYPTO_HELP_293")`
  → 环境变量: `CONFIG_CRYPTO_HELP_293`

- 行 295: `help="输出文件路径"`
  → `help = os.getenv("CONFIG_CRYPTO_HELP_295")`
  → 环境变量: `CONFIG_CRYPTO_HELP_295`

- 行 298: `action='store_true'`
  → `action = os.getenv("CONFIG_CRYPTO_ACTION_298")`
  → 环境变量: `CONFIG_CRYPTO_ACTION_298`

- 行 299: `help="使用密码保护"`
  → `help = os.getenv("CONFIG_CRYPTO_HELP_299")`
  → 环境变量: `CONFIG_CRYPTO_HELP_299`

- 行 300: `help="自定义密钥文件路径"`
  → `help = os.getenv("CONFIG_CRYPTO_HELP_300")`
  → 环境变量: `CONFIG_CRYPTO_HELP_300`

### scripts/generate-passwords.py

- 行 22: `special_safe = "!@#$%^&*()_+-="`
  → `special_safe = os.getenv("GENERATE_PASSWORDS_SPECIAL_SAFE_22")`
  → 环境变量: `GENERATE_PASSWORDS_SPECIAL_SAFE_22`

- 行 22: `special_extended = "!@#$%^&*()_+-=[]{}|;:,.<>?"`
  → `special_extended = os.getenv("GENERATE_PASSWORDS_SPECIAL_EXTENDED_22")`
  → 环境变量: `GENERATE_PASSWORDS_SPECIAL_EXTENDED_22`

- 行 210: `description="FootballPrediction项目强密码生成器"`
  → `description = os.getenv("GENERATE_PASSWORDS_DESCRIPTION_210")`
  → 环境变量: `GENERATE_PASSWORDS_DESCRIPTION_210`

- 行 214: `help="输出格式 (默认: text)"`
  → `help = os.getenv("GENERATE_PASSWORDS_HELP_214")`
  → 环境变量: `GENERATE_PASSWORDS_HELP_214`

- 行 219: `help="密码长度 (默认: 32)"`
  → `help = os.getenv("GENERATE_PASSWORDS_HELP_219")`
  → 环境变量: `GENERATE_PASSWORDS_HELP_219`

### scripts/ci_guardian.py

- 行 28: `CODE_STYLE = "code_style"`
  → `CODE_STYLE = os.getenv("CI_GUARDIAN_CODE_STYLE_28")`
  → 环境变量: `CI_GUARDIAN_CODE_STYLE_28`

- 行 28: `TYPE_CHECK = "type_check"`
  → `TYPE_CHECK = os.getenv("CI_GUARDIAN_TYPE_CHECK_28")`
  → 环境变量: `CI_GUARDIAN_TYPE_CHECK_28`

- 行 29: `SYNTAX_ERROR = "syntax_error"`
  → `SYNTAX_ERROR = os.getenv("CI_GUARDIAN_SYNTAX_ERROR_29")`
  → 环境变量: `CI_GUARDIAN_SYNTAX_ERROR_29`

- 行 29: `TEST_FAILURE = "test_failure"`
  → `TEST_FAILURE = os.getenv("CI_GUARDIAN_TEST_FAILURE_29")`
  → 环境变量: `CI_GUARDIAN_TEST_FAILURE_29`

- 行 30: `IMPORT_ERROR = "import_error"`
  → `IMPORT_ERROR = os.getenv("CI_GUARDIAN_IMPORT_ERROR_30")`
  → 环境变量: `CI_GUARDIAN_IMPORT_ERROR_30`

- 行 30: `SECURITY_ISSUE = "security_issue"`
  → `SECURITY_ISSUE = os.getenv("CI_GUARDIAN_SECURITY_ISSUE_30")`
  → 环境变量: `CI_GUARDIAN_SECURITY_ISSUE_30`

- 行 31: `COVERAGE_LOW = "coverage_low"`
  → `COVERAGE_LOW = os.getenv("CI_GUARDIAN_COVERAGE_LOW_31")`
  → 环境变量: `CI_GUARDIAN_COVERAGE_LOW_31`

- 行 32: `DEPENDENCY_ISSUE = "dependency_issue"`
  → `DEPENDENCY_ISSUE = os.getenv("CI_GUARDIAN_DEPENDENCY_ISSUE_32")`
  → 环境变量: `CI_GUARDIAN_DEPENDENCY_ISSUE_32`

- 行 32: `UNKNOWN = "unknown"`
  → `UNKNOWN = os.getenv("CI_GUARDIAN_UNKNOWN_32")`
  → 环境变量: `CI_GUARDIAN_UNKNOWN_32`

- 行 42: `str = "medium"`
  → `str = os.getenv("CI_GUARDIAN_STR_42")`
  → 环境变量: `CI_GUARDIAN_STR_42`

- 行 324: `style = "double"`
  → `style = os.getenv("CI_GUARDIAN_STYLE_324")`
  → 环境变量: `CI_GUARDIAN_STYLE_324`

- 行 669: `help="要监控的CI命令 (例如: '`
  → `help = os.getenv("CI_GUARDIAN_HELP_669")`
  → 环境变量: `CI_GUARDIAN_HELP_669`

- 行 670: `help="分析现有日志文件中的问题"`
  → `help = os.getenv("CI_GUARDIAN_HELP_670")`
  → 环境变量: `CI_GUARDIAN_HELP_670`

- 行 674: `help="仅生成防御机制，不执行命令"`
  → `help = os.getenv("CI_GUARDIAN_HELP_674")`
  → 环境变量: `CI_GUARDIAN_HELP_674`

- 行 677: `help="验证现有防御机制"`
  → `help = os.getenv("CI_GUARDIAN_HELP_677")`
  → 环境变量: `CI_GUARDIAN_HELP_677`

- 行 678: `help="项目根目录路径"`
  → `help = os.getenv("CI_GUARDIAN_HELP_678")`
  → 环境变量: `CI_GUARDIAN_HELP_678`

- 行 679: `help="显示执行摘要"`
  → `help = os.getenv("CI_GUARDIAN_HELP_679")`
  → 环境变量: `CI_GUARDIAN_HELP_679`

### scripts/sync_issues.py

- 行 43: `GITHUB_TOKEN_ENV = "GITHUB_TOKEN"`
  → `GITHUB_TOKEN_ENV = os.getenv("SYNC_ISSUES_GITHUB_TOKEN_ENV_43")`
  → 环境变量: `SYNC_ISSUES_GITHUB_TOKEN_ENV_43`

- 行 43: `GITHUB_REPO_ENV = "GITHUB_REPO"`
  → `GITHUB_REPO_ENV = os.getenv("SYNC_ISSUES_GITHUB_REPO_ENV_43")`
  → 环境变量: `SYNC_ISSUES_GITHUB_REPO_ENV_43`

- 行 325: `description="GitHub Issues 双向同步工具"`
  → `description = os.getenv("SYNC_ISSUES_DESCRIPTION_325")`
  → 环境变量: `SYNC_ISSUES_DESCRIPTION_325`

- 行 341: `help="同步操作: pull(拉取), push(推送), sync(双向同步)"`
  → `help = os.getenv("SYNC_ISSUES_HELP_341")`
  → 环境变量: `SYNC_ISSUES_HELP_341`

### scripts/update_dependencies.py

- 行 81: `package="cryptography"`
  → `package = os.getenv("UPDATE_DEPENDENCIES_PACKAGE_81")`
  → 环境变量: `UPDATE_DEPENDENCIES_PACKAGE_81`

- 行 81: `strategy="security"`
  → `strategy = os.getenv("UPDATE_DEPENDENCIES_STRATEGY_81")`
  → 环境变量: `UPDATE_DEPENDENCIES_STRATEGY_81`

- 行 82: `reason="安全库，需要及时更新"`
  → `reason = os.getenv("UPDATE_DEPENDENCIES_REASON_82")`
  → 环境变量: `UPDATE_DEPENDENCIES_REASON_82`

- 行 83: `package="pydantic"`
  → `package = os.getenv("UPDATE_DEPENDENCIES_PACKAGE_83")`
  → 环境变量: `UPDATE_DEPENDENCIES_PACKAGE_83`

- 行 85: `reason="主要依赖，只接受补丁更新"`
  → `reason = os.getenv("UPDATE_DEPENDENCIES_REASON_85")`
  → 环境变量: `UPDATE_DEPENDENCIES_REASON_85`

- 行 87: `package="fastapi"`
  → `package = os.getenv("UPDATE_DEPENDENCIES_PACKAGE_87")`
  → 环境变量: `UPDATE_DEPENDENCIES_PACKAGE_87`

- 行 88: `reason="核心框架，保持较新版本"`
  → `reason = os.getenv("UPDATE_DEPENDENCIES_REASON_88")`
  → 环境变量: `UPDATE_DEPENDENCIES_REASON_88`

- 行 91: `package="uvicorn"`
  → `package = os.getenv("UPDATE_DEPENDENCIES_PACKAGE_91")`
  → 环境变量: `UPDATE_DEPENDENCIES_PACKAGE_91`

- 行 92: `reason="ASGI服务器，通常兼容"`
  → `reason = os.getenv("UPDATE_DEPENDENCIES_REASON_92")`
  → 环境变量: `UPDATE_DEPENDENCIES_REASON_92`

- 行 95: `package="sqlalchemy"`
  → `package = os.getenv("UPDATE_DEPENDENCIES_PACKAGE_95")`
  → 环境变量: `UPDATE_DEPENDENCIES_PACKAGE_95`

- 行 96: `strategy="manual"`
  → `strategy = os.getenv("UPDATE_DEPENDENCIES_STRATEGY_96")`
  → 环境变量: `UPDATE_DEPENDENCIES_STRATEGY_96`

- 行 96: `reason="ORM，重大更新可能不兼容"`
  → `reason = os.getenv("UPDATE_DEPENDENCIES_REASON_96")`
  → 环境变量: `UPDATE_DEPENDENCIES_REASON_96`

- 行 98: `package="psycopg2-binary"`
  → `package = os.getenv("UPDATE_DEPENDENCIES_PACKAGE_98")`
  → 环境变量: `UPDATE_DEPENDENCIES_PACKAGE_98`

- 行 100: `strategy="manual"`
  → `strategy = os.getenv("UPDATE_DEPENDENCIES_STRATEGY_100")`
  → 环境变量: `UPDATE_DEPENDENCIES_STRATEGY_100`

- 行 102: `reason="数据库驱动，需要验证"`
  → `reason = os.getenv("UPDATE_DEPENDENCIES_REASON_102")`
  → 环境变量: `UPDATE_DEPENDENCIES_REASON_102`

- 行 104: `package="requests"`
  → `package = os.getenv("UPDATE_DEPENDENCIES_PACKAGE_104")`
  → 环境变量: `UPDATE_DEPENDENCIES_PACKAGE_104`

- 行 104: `strategy="security"`
  → `strategy = os.getenv("UPDATE_DEPENDENCIES_STRATEGY_104")`
  → 环境变量: `UPDATE_DEPENDENCIES_STRATEGY_104`

- 行 105: `reason="HTTP客户端，安全优先"`
  → `reason = os.getenv("UPDATE_DEPENDENCIES_REASON_105")`
  → 环境变量: `UPDATE_DEPENDENCIES_REASON_105`

- 行 107: `package="python-jose"`
  → `package = os.getenv("UPDATE_DEPENDENCIES_PACKAGE_107")`
  → 环境变量: `UPDATE_DEPENDENCIES_PACKAGE_107`

- 行 108: `strategy="security"`
  → `strategy = os.getenv("UPDATE_DEPENDENCIES_STRATEGY_108")`
  → 环境变量: `UPDATE_DEPENDENCIES_STRATEGY_108`

- 行 108: `reason="JWT处理，安全关键"`
  → `reason = os.getenv("UPDATE_DEPENDENCIES_REASON_108")`
  → 环境变量: `UPDATE_DEPENDENCIES_REASON_108`

- 行 112: `reason="代码格式化工具"`
  → `reason = os.getenv("UPDATE_DEPENDENCIES_REASON_112")`
  → 环境变量: `UPDATE_DEPENDENCIES_REASON_112`

- 行 116: `reason="代码检查工具"`
  → `reason = os.getenv("UPDATE_DEPENDENCIES_REASON_116")`
  → 环境变量: `UPDATE_DEPENDENCIES_REASON_116`

- 行 117: `package="pytest"`
  → `package = os.getenv("UPDATE_DEPENDENCIES_PACKAGE_117")`
  → 环境变量: `UPDATE_DEPENDENCIES_PACKAGE_117`

- 行 360: `strategy = "manual"`
  → `strategy = os.getenv("UPDATE_DEPENDENCIES_STRATEGY_360")`
  → 环境变量: `UPDATE_DEPENDENCIES_STRATEGY_360`

- 行 594: `description="依赖更新管理"`
  → `description = os.getenv("UPDATE_DEPENDENCIES_DESCRIPTION_594")`
  → 环境变量: `UPDATE_DEPENDENCIES_DESCRIPTION_594`

- 行 596: `action='store_true'`
  → `action = os.getenv("UPDATE_DEPENDENCIES_ACTION_596")`
  → 环境变量: `UPDATE_DEPENDENCIES_ACTION_596`

- 行 602: `action='store_true'`
  → `action = os.getenv("UPDATE_DEPENDENCIES_ACTION_602")`
  → 环境变量: `UPDATE_DEPENDENCIES_ACTION_602`

- 行 605: `action='store_true'`
  → `action = os.getenv("UPDATE_DEPENDENCIES_ACTION_605")`
  → 环境变量: `UPDATE_DEPENDENCIES_ACTION_605`

- 行 607: `action='store_true'`
  → `action = os.getenv("UPDATE_DEPENDENCIES_ACTION_607")`
  → 环境变量: `UPDATE_DEPENDENCIES_ACTION_607`

- 行 610: `help="输出报告到文件"`
  → `help = os.getenv("UPDATE_DEPENDENCIES_HELP_610")`
  → 环境变量: `UPDATE_DEPENDENCIES_HELP_610`

### scripts/test_runner.py

- 行 380: `description="智能测试运行器"`
  → `description = os.getenv("TEST_RUNNER_DESCRIPTION_380")`
  → 环境变量: `TEST_RUNNER_DESCRIPTION_380`

- 行 382: `help="指定要运行的测试层级"`
  → `help = os.getenv("TEST_RUNNER_HELP_382")`
  → 环境变量: `TEST_RUNNER_HELP_382`

- 行 383: `action="store_true"`
  → `action = os.getenv("TEST_RUNNER_ACTION_383")`
  → 环境变量: `TEST_RUNNER_ACTION_383`

- 行 384: `help="并行执行测试"`
  → `help = os.getenv("TEST_RUNNER_HELP_384")`
  → 环境变量: `TEST_RUNNER_HELP_384`

- 行 384: `action="store_true"`
  → `action = os.getenv("TEST_RUNNER_ACTION_384")`
  → 环境变量: `TEST_RUNNER_ACTION_384`

- 行 385: `help="禁用并行执行"`
  → `help = os.getenv("TEST_RUNNER_HELP_385")`
  → 环境变量: `TEST_RUNNER_HELP_385`

- 行 386: `action="store_true"`
  → `action = os.getenv("TEST_RUNNER_ACTION_386")`
  → 环境变量: `TEST_RUNNER_ACTION_386`

- 行 386: `help="仅运行失败的测试"`
  → `help = os.getenv("TEST_RUNNER_HELP_386")`
  → 环境变量: `TEST_RUNNER_HELP_386`

- 行 387: `action="store_true"`
  → `action = os.getenv("TEST_RUNNER_ACTION_387")`
  → 环境变量: `TEST_RUNNER_ACTION_387`

- 行 388: `help="执行质量门禁"`
  → `help = os.getenv("TEST_RUNNER_HELP_388")`
  → 环境变量: `TEST_RUNNER_HELP_388`

- 行 389: `help="最小覆盖率要求（默认20%%）"`
  → `help = os.getenv("TEST_RUNNER_HELP_389")`
  → 环境变量: `TEST_RUNNER_HELP_389`

- 行 391: `help="最小成功率要求（默认90%%）"`
  → `help = os.getenv("TEST_RUNNER_HELP_391")`
  → 环境变量: `TEST_RUNNER_HELP_391`

- 行 392: `action="store_true"`
  → `action = os.getenv("TEST_RUNNER_ACTION_392")`
  → 环境变量: `TEST_RUNNER_ACTION_392`

- 行 392: `help="输出测试矩阵（用于CI）"`
  → `help = os.getenv("TEST_RUNNER_HELP_392")`
  → 环境变量: `TEST_RUNNER_HELP_392`

- 行 393: `help="输出结果到文件"`
  → `help = os.getenv("TEST_RUNNER_HELP_393")`
  → 环境变量: `TEST_RUNNER_HELP_393`

### scripts/demo_ci_guardian.py

- 行 116: `user_input = "print('`
  → `user_input = os.getenv("DEMO_CI_GUARDIAN_USER_INPUT_116")`
  → 环境变量: `DEMO_CI_GUARDIAN_USER_INPUT_116`

- 行 425: `help="项目根目录路径"`
  → `help = os.getenv("DEMO_CI_GUARDIAN_HELP_425")`
  → 环境变量: `DEMO_CI_GUARDIAN_HELP_425`

- 行 425: `help="快速演示（跳过某些步骤）"`
  → `help = os.getenv("DEMO_CI_GUARDIAN_HELP_425")`
  → 环境变量: `DEMO_CI_GUARDIAN_HELP_425`

- 行 426: `help="仅清理演示环境"`
  → `help = os.getenv("DEMO_CI_GUARDIAN_HELP_426")`
  → 环境变量: `DEMO_CI_GUARDIAN_HELP_426`

- 行 427: `help="显示演示摘要"`
  → `help = os.getenv("DEMO_CI_GUARDIAN_HELP_427")`
  → 环境变量: `DEMO_CI_GUARDIAN_HELP_427`

### scripts/disable_failing_tests.py

- 行 39: `reason="Function not implemented in src.api.data"`
  → `reason = os.getenv("DISABLE_FAILING_TESTS_REASON_39")`
  → 环境变量: `DISABLE_FAILING_TESTS_REASON_39`

### scripts/materialized_views_examples.py

- 行 33: `format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"`
  → `format = os.getenv("MATERIALIZED_VIEWS_EXAMPLES_FORMAT_33")`
  → 环境变量: `MATERIALIZED_VIEWS_EXAMPLES_FORMAT_33`

- 行 324: `match_status = 'finished'`
  → `match_status = os.getenv("MATERIALIZED_VIEWS_EXAMPLES_MATCH_STATUS_324")`
  → 环境变量: `MATERIALIZED_VIEWS_EXAMPLES_MATCH_STATUS_324`

- 行 326: `match_status = 'finished'`
  → `match_status = os.getenv("MATERIALIZED_VIEWS_EXAMPLES_MATCH_STATUS_326")`
  → 环境变量: `MATERIALIZED_VIEWS_EXAMPLES_MATCH_STATUS_326`

- 行 328: `match_status = 'finished'`
  → `match_status = os.getenv("MATERIALIZED_VIEWS_EXAMPLES_MATCH_STATUS_328")`
  → 环境变量: `MATERIALIZED_VIEWS_EXAMPLES_MATCH_STATUS_328`

- 行 330: `match_status = 'finished'`
  → `match_status = os.getenv("MATERIALIZED_VIEWS_EXAMPLES_MATCH_STATUS_330")`
  → 环境变量: `MATERIALIZED_VIEWS_EXAMPLES_MATCH_STATUS_330`

- 行 412: `description="物化视图查询示例"`
  → `description = os.getenv("MATERIALIZED_VIEWS_EXAMPLES_DESCRIPTION_412")`
  → 环境变量: `MATERIALIZED_VIEWS_EXAMPLES_DESCRIPTION_412`

- 行 419: `help="选择要运行的示例"`
  → `help = os.getenv("MATERIALIZED_VIEWS_EXAMPLES_HELP_419")`
  → 环境变量: `MATERIALIZED_VIEWS_EXAMPLES_HELP_419`

- 行 419: `action="store_true"`
  → `action = os.getenv("MATERIALIZED_VIEWS_EXAMPLES_ACTION_419")`
  → 环境变量: `MATERIALIZED_VIEWS_EXAMPLES_ACTION_419`

- 行 419: `help="运行性能基准测试"`
  → `help = os.getenv("MATERIALIZED_VIEWS_EXAMPLES_HELP_419")`
  → 环境变量: `MATERIALIZED_VIEWS_EXAMPLES_HELP_419`

### scripts/setup.py

- 行 4: `name="football-prediction"`
  → `name = os.getenv("SETUP_NAME_4")`
  → 环境变量: `SETUP_NAME_4`

- 行 11: `python_requires=">=3.11"`
  → `python_requires = os.getenv("SETUP_PYTHON_REQUIRES_11")`
  → 环境变量: `SETUP_PYTHON_REQUIRES_11`

- 行 12: `description="Football Prediction System with AI Analysis"`
  → `description = os.getenv("SETUP_DESCRIPTION_12")`
  → 环境变量: `SETUP_DESCRIPTION_12`

- 行 14: `long_description_content_type="text/markdown"`
  → `long_description_content_type = os.getenv("SETUP_LONG_DESCRIPTION_CONTENT_TYPE_14")`
  → 环境变量: `SETUP_LONG_DESCRIPTION_CONTENT_TYPE_14`

- 行 15: `author="FootballPrediction Team"`
  → `author = os.getenv("SETUP_AUTHOR_15")`
  → 环境变量: `SETUP_AUTHOR_15`

### scripts/backup_config.py

- 行 58: `name="environment"`
  → `name = os.getenv("BACKUP_CONFIG_NAME_58")`
  → 环境变量: `BACKUP_CONFIG_NAME_58`

- 行 68: `name="configuration"`
  → `name = os.getenv("BACKUP_CONFIG_NAME_68")`
  → 环境变量: `BACKUP_CONFIG_NAME_68`

- 行 79: `name="secrets"`
  → `name = os.getenv("BACKUP_CONFIG_NAME_79")`
  → 环境变量: `BACKUP_CONFIG_NAME_79`

- 行 88: `name="certificates"`
  → `name = os.getenv("BACKUP_CONFIG_NAME_88")`
  → 环境变量: `BACKUP_CONFIG_NAME_88`

- 行 437: `description="配置备份工具"`
  → `description = os.getenv("BACKUP_CONFIG_DESCRIPTION_437")`
  → 环境变量: `BACKUP_CONFIG_DESCRIPTION_437`

- 行 444: `help="要执行的命令"`
  → `help = os.getenv("BACKUP_CONFIG_HELP_444")`
  → 环境变量: `BACKUP_CONFIG_HELP_444`

- 行 449: `action='store_true'`
  → `action = os.getenv("BACKUP_CONFIG_ACTION_449")`
  → 环境变量: `BACKUP_CONFIG_ACTION_449`

- 行 450: `action='store_true'`
  → `action = os.getenv("BACKUP_CONFIG_ACTION_450")`
  → 环境变量: `BACKUP_CONFIG_ACTION_450`

### scripts/cursor_runner.py

- 行 365: `str = "logs/cursor_execution.json"`
  → `str = os.getenv("CURSOR_RUNNER_STR_365")`
  → 环境变量: `CURSOR_RUNNER_STR_365`

- 行 395: `description="Cursor闭环执行器"`
  → `description = os.getenv("CURSOR_RUNNER_DESCRIPTION_395")`
  → 环境变量: `CURSOR_RUNNER_DESCRIPTION_395`

- 行 398: `default="logs/cursor_execution.json"`
  → `default = os.getenv("CURSOR_RUNNER_DEFAULT_398")`
  → 环境变量: `CURSOR_RUNNER_DEFAULT_398`

- 行 399: `help="执行日志输出文件"`
  → `help = os.getenv("CURSOR_RUNNER_HELP_399")`
  → 环境变量: `CURSOR_RUNNER_HELP_399`

- 行 399: `action="store_true"`
  → `action = os.getenv("CURSOR_RUNNER_ACTION_399")`
  → 环境变量: `CURSOR_RUNNER_ACTION_399`

- 行 399: `help="显示执行摘要"`
  → `help = os.getenv("CURSOR_RUNNER_HELP_399")`
  → 环境变量: `CURSOR_RUNNER_HELP_399`

### scripts/ci_issue_analyzer.py

- 行 143: `FAILURES =" in line:
                in_failure_section = True
                continue

            # 检测失败测试结束
            if line.startswith("`
  → `FAILURES = os.getenv("CI_ISSUE_ANALYZER_FAILURES_143")`
  → 环境变量: `CI_ISSUE_ANALYZER_FAILURES_143`

- 行 614: `help="分析特定工具的输出 (ruff, mypy, pytest, bandit, coverage)"`
  → `help = os.getenv("CI_ISSUE_ANALYZER_HELP_614")`
  → 环境变量: `CI_ISSUE_ANALYZER_HELP_614`

- 行 616: `help="输入文件路径 (工具输出或日志文件)"`
  → `help = os.getenv("CI_ISSUE_ANALYZER_HELP_616")`
  → 环境变量: `CI_ISSUE_ANALYZER_HELP_616`

- 行 617: `help="输出分析报告的文件路径"`
  → `help = os.getenv("CI_ISSUE_ANALYZER_HELP_617")`
  → 环境变量: `CI_ISSUE_ANALYZER_HELP_617`

- 行 617: `help="质量检查日志文件路径"`
  → `help = os.getenv("CI_ISSUE_ANALYZER_HELP_617")`
  → 环境变量: `CI_ISSUE_ANALYZER_HELP_617`

- 行 618: `help="显示分析摘要"`
  → `help = os.getenv("CI_ISSUE_ANALYZER_HELP_618")`
  → 环境变量: `CI_ISSUE_ANALYZER_HELP_618`

- 行 618: `help="显示解决建议"`
  → `help = os.getenv("CI_ISSUE_ANALYZER_HELP_618")`
  → 环境变量: `CI_ISSUE_ANALYZER_HELP_618`

- 行 618: `help="项目根目录路径"`
  → `help = os.getenv("CI_ISSUE_ANALYZER_HELP_618")`
  → 环境变量: `CI_ISSUE_ANALYZER_HELP_618`

### scripts/collect_quality_trends.py

- 行 118: `error_type = "type_error"`
  → `error_type = os.getenv("COLLECT_QUALITY_TRENDS_ERROR_TYPE_118")`
  → 环境变量: `COLLECT_QUALITY_TRENDS_ERROR_TYPE_118`

- 行 119: `error_type = "warning"`
  → `error_type = os.getenv("COLLECT_QUALITY_TRENDS_ERROR_TYPE_119")`
  → 环境变量: `COLLECT_QUALITY_TRENDS_ERROR_TYPE_119`

### scripts/retrain_pipeline.py

- 行 249: `trend = "improving"`
  → `trend = os.getenv("RETRAIN_PIPELINE_TREND_249")`
  → 环境变量: `RETRAIN_PIPELINE_TREND_249`

- 行 250: `trend = "declining"`
  → `trend = os.getenv("RETRAIN_PIPELINE_TREND_250")`
  → 环境变量: `RETRAIN_PIPELINE_TREND_250`

- 行 251: `trend = "stable"`
  → `trend = os.getenv("RETRAIN_PIPELINE_TREND_251")`
  → 环境变量: `RETRAIN_PIPELINE_TREND_251`

- 行 253: `trend = "insufficient_data"`
  → `trend = os.getenv("RETRAIN_PIPELINE_TREND_253")`
  → 环境变量: `RETRAIN_PIPELINE_TREND_253`

- 行 384: `stage="Staging"`
  → `stage = os.getenv("RETRAIN_PIPELINE_STAGE_384")`
  → 环境变量: `RETRAIN_PIPELINE_STAGE_384`

- 行 763: `help="最小预测数量要求"`
  → `help = os.getenv("RETRAIN_PIPELINE_HELP_763")`
  → 环境变量: `RETRAIN_PIPELINE_HELP_763`

- 行 767: `help="评估窗口天数"`
  → `help = os.getenv("RETRAIN_PIPELINE_HELP_767")`
  → 环境变量: `RETRAIN_PIPELINE_HELP_767`

- 行 768: `help="指定模型名称（可选）"`
  → `help = os.getenv("RETRAIN_PIPELINE_HELP_768")`
  → 环境变量: `RETRAIN_PIPELINE_HELP_768`

- 行 768: `help="试运行模式，不执行实际重训练"`
  → `help = os.getenv("RETRAIN_PIPELINE_HELP_768")`
  → 环境变量: `RETRAIN_PIPELINE_HELP_768`

### scripts/coverage_bugfix_loop.py

- 行 67: `kanban_file = "docs/_reports/TEST_COVERAGE_KANBAN.md"`
  → `kanban_file = os.getenv("COVERAGE_BUGFIX_LOOP_KANBAN_FILE_67")`
  → 环境变量: `COVERAGE_BUGFIX_LOOP_KANBAN_FILE_67`

### scripts/check_licenses.py

- 行 25: `PERMISSIVE = "permissive"`
  → `PERMISSIVE = os.getenv("CHECK_LICENSES_PERMISSIVE_25")`
  → 环境变量: `CHECK_LICENSES_PERMISSIVE_25`

- 行 25: `COPYLEFT = "copyleft"`
  → `COPYLEFT = os.getenv("CHECK_LICENSES_COPYLEFT_25")`
  → 环境变量: `CHECK_LICENSES_COPYLEFT_25`

- 行 26: `COMMERCIAL = "commercial"`
  → `COMMERCIAL = os.getenv("CHECK_LICENSES_COMMERCIAL_26")`
  → 环境变量: `CHECK_LICENSES_COMMERCIAL_26`

- 行 26: `PROPRIETARY = "proprietary"`
  → `PROPRIETARY = os.getenv("CHECK_LICENSES_PROPRIETARY_26")`
  → 环境变量: `CHECK_LICENSES_PROPRIETARY_26`

- 行 27: `UNKNOWN = "unknown"`
  → `UNKNOWN = os.getenv("CHECK_LICENSES_UNKNOWN_27")`
  → 环境变量: `CHECK_LICENSES_UNKNOWN_27`

- 行 97: `description="MIT许可证，允许自由使用、修改和分发"`
  → `description = os.getenv("CHECK_LICENSES_DESCRIPTION_97")`
  → 环境变量: `CHECK_LICENSES_DESCRIPTION_97`

- 行 102: `description="BSD许可证，宽松的开源许可证"`
  → `description = os.getenv("CHECK_LICENSES_DESCRIPTION_102")`
  → 环境变量: `CHECK_LICENSES_DESCRIPTION_102`

- 行 107: `name="Apache-2.0"`
  → `name = os.getenv("CHECK_LICENSES_NAME_107")`
  → 环境变量: `CHECK_LICENSES_NAME_107`

- 行 115: `description="ISC许可证，类似MIT的简化版"`
  → `description = os.getenv("CHECK_LICENSES_DESCRIPTION_115")`
  → 环境变量: `CHECK_LICENSES_DESCRIPTION_115`

- 行 122: `description="Python软件基金会许可证"`
  → `description = os.getenv("CHECK_LICENSES_DESCRIPTION_122")`
  → 环境变量: `CHECK_LICENSES_DESCRIPTION_122`

- 行 125: `name="Unlicense"`
  → `name = os.getenv("CHECK_LICENSES_NAME_125")`
  → 环境变量: `CHECK_LICENSES_NAME_125`

- 行 128: `description="放弃版权的公共领域许可证"`
  → `description = os.getenv("CHECK_LICENSES_DESCRIPTION_128")`
  → 环境变量: `CHECK_LICENSES_DESCRIPTION_128`

- 行 129: `name="CC0-1.0"`
  → `name = os.getenv("CHECK_LICENSES_NAME_129")`
  → 环境变量: `CHECK_LICENSES_NAME_129`

- 行 132: `description="Creative Commons Zero，公共领域"`
  → `description = os.getenv("CHECK_LICENSES_DESCRIPTION_132")`
  → 环境变量: `CHECK_LICENSES_DESCRIPTION_132`

- 行 138: `description="GNU通用公共许可证，要求开源派生作品"`
  → `description = os.getenv("CHECK_LICENSES_DESCRIPTION_138")`
  → 环境变量: `CHECK_LICENSES_DESCRIPTION_138`

- 行 147: `description="GNU较宽松通用公共许可证"`
  → `description = os.getenv("CHECK_LICENSES_DESCRIPTION_147")`
  → 环境变量: `CHECK_LICENSES_DESCRIPTION_147`

- 行 154: `description="GNU Affero通用公共许可证"`
  → `description = os.getenv("CHECK_LICENSES_DESCRIPTION_154")`
  → 环境变量: `CHECK_LICENSES_DESCRIPTION_154`

- 行 163: `description="Eclipse公共许可证"`
  → `description = os.getenv("CHECK_LICENSES_DESCRIPTION_163")`
  → 环境变量: `CHECK_LICENSES_DESCRIPTION_163`

- 行 169: `description="Mozilla公共许可证"`
  → `description = os.getenv("CHECK_LICENSES_DESCRIPTION_169")`
  → 环境变量: `CHECK_LICENSES_DESCRIPTION_169`

- 行 175: `name="Apache 2.0"`
  → `name = os.getenv("CHECK_LICENSES_NAME_175")`
  → 环境变量: `CHECK_LICENSES_NAME_175`

- 行 179: `name="UNKNOWN"`
  → `name = os.getenv("CHECK_LICENSES_NAME_179")`
  → 环境变量: `CHECK_LICENSES_NAME_179`

- 行 465: `description="依赖许可证检查"`
  → `description = os.getenv("CHECK_LICENSES_DESCRIPTION_465")`
  → 环境变量: `CHECK_LICENSES_DESCRIPTION_465`

- 行 469: `help="输出报告文件"`
  → `help = os.getenv("CHECK_LICENSES_HELP_469")`
  → 环境变量: `CHECK_LICENSES_HELP_469`

- 行 469: `action='store_true'`
  → `action = os.getenv("CHECK_LICENSES_ACTION_469")`
  → 环境变量: `CHECK_LICENSES_ACTION_469`

- 行 470: `help="生成NOTICE文件"`
  → `help = os.getenv("CHECK_LICENSES_HELP_470")`
  → 环境变量: `CHECK_LICENSES_HELP_470`

### scripts/test_failure.py

- 行 45: `very_long_line = "这是一个故意写得很长的行，超过了88个字符的限制，用来测试flake8的检查功能，应该会报错"`
  → `very_long_line = os.getenv("TEST_FAILURE_VERY_LONG_LINE_45")`
  → 环境变量: `TEST_FAILURE_VERY_LONG_LINE_45`

### scripts/enable_tests.py

- 行 20: `reason="Function not implemented in src\.api\.data"`
  → `reason = os.getenv("ENABLE_TESTS_REASON_20")`
  → 环境变量: `ENABLE_TESTS_REASON_20`

### scripts/generate_ci_report.py

- 行 57: `summary_line="No summary found"`
  → `summary_line = os.getenv("GENERATE_CI_REPORT_SUMMARY_LINE_57")`
  → 环境变量: `GENERATE_CI_REPORT_SUMMARY_LINE_57`

- 行 71: `anchor = "slowest"`
  → `anchor = os.getenv("GENERATE_CI_REPORT_ANCHOR_71")`
  → 环境变量: `GENERATE_CI_REPORT_ANCHOR_71`

- 行 108: `errors="ignore"`
  → `errors = os.getenv("GENERATE_CI_REPORT_ERRORS_108")`
  → 环境变量: `GENERATE_CI_REPORT_ERRORS_108`

- 行 346: `errors="ignore"`
  → `errors = os.getenv("GENERATE_CI_REPORT_ERRORS_346")`
  → 环境变量: `GENERATE_CI_REPORT_ERRORS_346`

- 行 397: `color="#1f77b4"`
  → `color = os.getenv("GENERATE_CI_REPORT_COLOR_397")`
  → 环境变量: `GENERATE_CI_REPORT_COLOR_397`

### scripts/quality_checker.py

- 行 668: `str = "logs/quality_check.json"`
  → `str = os.getenv("QUALITY_CHECKER_STR_668")`
  → 环境变量: `QUALITY_CHECKER_STR_668`

- 行 680: `str = "logs/iteration.log"`
  → `str = os.getenv("QUALITY_CHECKER_STR_680")`
  → 环境变量: `QUALITY_CHECKER_STR_680`

- 行 711: `description="代码质量检查器"`
  → `description = os.getenv("QUALITY_CHECKER_DESCRIPTION_711")`
  → 环境变量: `QUALITY_CHECKER_DESCRIPTION_711`

- 行 712: `help="最大重试次数"`
  → `help = os.getenv("QUALITY_CHECKER_HELP_712")`
  → 环境变量: `QUALITY_CHECKER_HELP_712`

- 行 713: `default="logs/quality_check.json"`
  → `default = os.getenv("QUALITY_CHECKER_DEFAULT_713")`
  → 环境变量: `QUALITY_CHECKER_DEFAULT_713`

- 行 713: `help="结果输出文件"`
  → `help = os.getenv("QUALITY_CHECKER_HELP_713")`
  → 环境变量: `QUALITY_CHECKER_HELP_713`

- 行 715: `action="store_true"`
  → `action = os.getenv("QUALITY_CHECKER_ACTION_715")`
  → 环境变量: `QUALITY_CHECKER_ACTION_715`

### scripts/cleanup_imports.py

- 行 301: `description='自动清理和排序 Python import 语句'`
  → `description = os.getenv("CLEANUP_IMPORTS_DESCRIPTION_301")`
  → 环境变量: `CLEANUP_IMPORTS_DESCRIPTION_301`

- 行 302: `help='要清理的目录 (默认: 当前目录)'`
  → `help = os.getenv("CLEANUP_IMPORTS_HELP_302")`
  → 环境变量: `CLEANUP_IMPORTS_HELP_302`

- 行 302: `default='docs/_reports/IMPORT_CLEANUP_REPORT.md'`
  → `default = os.getenv("CLEANUP_IMPORTS_DEFAULT_302")`
  → 环境变量: `CLEANUP_IMPORTS_DEFAULT_302`

- 行 303: `help='报告输出路径 (默认: docs/_reports/IMPORT_CLEANUP_REPORT.md)'`
  → `help = os.getenv("CLEANUP_IMPORTS_HELP_303")`
  → 环境变量: `CLEANUP_IMPORTS_HELP_303`

### scripts/project_health_checker.py

- 行 556: `description="项目健康检查工具"`
  → `description = os.getenv("PROJECT_HEALTH_CHECKER_DESCRIPTION_556")`
  → 环境变量: `PROJECT_HEALTH_CHECKER_DESCRIPTION_556`

- 行 556: `help="项目根目录路径"`
  → `help = os.getenv("PROJECT_HEALTH_CHECKER_HELP_556")`
  → 环境变量: `PROJECT_HEALTH_CHECKER_HELP_556`

### scripts/ultimate_cleanup.py

- 行 324: `description="终极项目清理工具"`
  → `description = os.getenv("ULTIMATE_CLEANUP_DESCRIPTION_324")`
  → 环境变量: `ULTIMATE_CLEANUP_DESCRIPTION_324`

- 行 325: `help="项目根目录路径"`
  → `help = os.getenv("ULTIMATE_CLEANUP_HELP_325")`
  → 环境变量: `ULTIMATE_CLEANUP_HELP_325`

- 行 325: `action="store_true"`
  → `action = os.getenv("ULTIMATE_CLEANUP_ACTION_325")`
  → 环境变量: `ULTIMATE_CLEANUP_ACTION_325`

- 行 325: `help="试运行，不实际删除文件"`
  → `help = os.getenv("ULTIMATE_CLEANUP_HELP_325")`
  → 环境变量: `ULTIMATE_CLEANUP_HELP_325`

### scripts/prepare_test_db.py

- 行 35: `format="%(asctime)s %(levelname)s %(message)s"`
  → `format = os.getenv("PREPARE_TEST_DB_FORMAT_35")`
  → 环境变量: `PREPARE_TEST_DB_FORMAT_35`

- 行 49: `league_name="Synthetic Premier League"`
  → `league_name = os.getenv("PREPARE_TEST_DB_LEAGUE_NAME_49")`
  → 环境变量: `PREPARE_TEST_DB_LEAGUE_NAME_49`

- 行 50: `country="Synthetic"`
  → `country = os.getenv("PREPARE_TEST_DB_COUNTRY_50")`
  → 环境变量: `PREPARE_TEST_DB_COUNTRY_50`

- 行 61: `team_name="Synthetic United"`
  → `team_name = os.getenv("PREPARE_TEST_DB_TEAM_NAME_61")`
  → 环境变量: `PREPARE_TEST_DB_TEAM_NAME_61`

- 行 63: `country="Synthetic"`
  → `country = os.getenv("PREPARE_TEST_DB_COUNTRY_63")`
  → 环境变量: `PREPARE_TEST_DB_COUNTRY_63`

- 行 65: `stadium="Synthetic Arena"`
  → `stadium = os.getenv("PREPARE_TEST_DB_STADIUM_65")`
  → 环境变量: `PREPARE_TEST_DB_STADIUM_65`

- 行 73: `team_name="Synthetic City"`
  → `team_name = os.getenv("PREPARE_TEST_DB_TEAM_NAME_73")`
  → 环境变量: `PREPARE_TEST_DB_TEAM_NAME_73`

- 行 75: `country="Synthetic"`
  → `country = os.getenv("PREPARE_TEST_DB_COUNTRY_75")`
  → 环境变量: `PREPARE_TEST_DB_COUNTRY_75`

- 行 77: `stadium="Synthetic Dome"`
  → `stadium = os.getenv("PREPARE_TEST_DB_STADIUM_77")`
  → 环境变量: `PREPARE_TEST_DB_STADIUM_77`

- 行 87: `season="2024/2025"`
  → `season = os.getenv("PREPARE_TEST_DB_SEASON_87")`
  → 环境变量: `PREPARE_TEST_DB_SEASON_87`

- 行 92: `venue="Synthetic Arena"`
  → `venue = os.getenv("PREPARE_TEST_DB_VENUE_92")`
  → 环境变量: `PREPARE_TEST_DB_VENUE_92`

- 行 93: `referee="Synthetic Ref"`
  → `referee = os.getenv("PREPARE_TEST_DB_REFEREE_93")`
  → 环境变量: `PREPARE_TEST_DB_REFEREE_93`

### scripts/coverage_auto_phase1.py

- 行 61: `action="store_true"`
  → `action = os.getenv("COVERAGE_AUTO_PHASE1_ACTION_61")`
  → 环境变量: `COVERAGE_AUTO_PHASE1_ACTION_61`

- 行 61: `help="Run only one iteration and exit"`
  → `help = os.getenv("COVERAGE_AUTO_PHASE1_HELP_61")`
  → 环境变量: `COVERAGE_AUTO_PHASE1_HELP_61`

### scripts/end_to_end_verification.py

- 行 69: `test_key = "test_verification"`
  → `test_key = os.getenv("END_TO_END_VERIFICATION_TEST_KEY_69")`
  → 环境变量: `END_TO_END_VERIFICATION_TEST_KEY_69`

- 行 214: `status = 'scheduled'`
  → `status = os.getenv("END_TO_END_VERIFICATION_STATUS_214")`
  → 环境变量: `END_TO_END_VERIFICATION_STATUS_214`

- 行 395: `header_style="bold magenta"`
  → `header_style = os.getenv("END_TO_END_VERIFICATION_HEADER_STYLE_395")`
  → 环境变量: `END_TO_END_VERIFICATION_HEADER_STYLE_395`

- 行 449: `status_text = "🎉 系统状态良好"`
  → `status_text = os.getenv("END_TO_END_VERIFICATION_STATUS_TEXT_449")`
  → 环境变量: `END_TO_END_VERIFICATION_STATUS_TEXT_449`

- 行 452: `status_color = "yellow"`
  → `status_color = os.getenv("END_TO_END_VERIFICATION_STATUS_COLOR_452")`
  → 环境变量: `END_TO_END_VERIFICATION_STATUS_COLOR_452`

- 行 453: `status_text = "⚠️ 系统部分功能异常"`
  → `status_text = os.getenv("END_TO_END_VERIFICATION_STATUS_TEXT_453")`
  → 环境变量: `END_TO_END_VERIFICATION_STATUS_TEXT_453`

- 行 454: `status_text = "❌ 系统存在严重问题"`
  → `status_text = os.getenv("END_TO_END_VERIFICATION_STATUS_TEXT_454")`
  → 环境变量: `END_TO_END_VERIFICATION_STATUS_TEXT_454`

- 行 475: `description="执行验证步骤..."`
  → `description = os.getenv("END_TO_END_VERIFICATION_DESCRIPTION_475")`
  → 环境变量: `END_TO_END_VERIFICATION_DESCRIPTION_475`

### scripts/setup_project.py

- 行 147: `text = "Hello, World!"`
  → `text = os.getenv("SETUP_PROJECT_TEXT_147")`
  → 环境变量: `SETUP_PROJECT_TEXT_147`

### scripts/fix_syntax_ast.py

- 行 311: `description='AST 驱动的 Python 语法修复工具'`
  → `description = os.getenv("FIX_SYNTAX_AST_DESCRIPTION_311")`
  → 环境变量: `FIX_SYNTAX_AST_DESCRIPTION_311`

- 行 312: `default='tests/unit'`
  → `default = os.getenv("FIX_SYNTAX_AST_DEFAULT_312")`
  → 环境变量: `FIX_SYNTAX_AST_DEFAULT_312`

- 行 312: `help='要修复的目录'`
  → `help = os.getenv("FIX_SYNTAX_AST_HELP_312")`
  → 环境变量: `FIX_SYNTAX_AST_HELP_312`

- 行 312: `help='每批处理的文件数'`
  → `help = os.getenv("FIX_SYNTAX_AST_HELP_312")`
  → 环境变量: `FIX_SYNTAX_AST_HELP_312`

- 行 313: `help='报告文件路径'`
  → `help = os.getenv("FIX_SYNTAX_AST_HELP_313")`
  → 环境变量: `FIX_SYNTAX_AST_HELP_313`

- 行 313: `default='docs/_reports/UNFIXED_FILES.md'`
  → `default = os.getenv("FIX_SYNTAX_AST_DEFAULT_313")`
  → 环境变量: `FIX_SYNTAX_AST_DEFAULT_313`

- 行 314: `help='无法修复文件报告'`
  → `help = os.getenv("FIX_SYNTAX_AST_HELP_314")`
  → 环境变量: `FIX_SYNTAX_AST_HELP_314`

### scripts/cleanup_project.py

- 行 332: `description="项目清理工具"`
  → `description = os.getenv("CLEANUP_PROJECT_DESCRIPTION_332")`
  → 环境变量: `CLEANUP_PROJECT_DESCRIPTION_332`

- 行 333: `help="项目根目录路径"`
  → `help = os.getenv("CLEANUP_PROJECT_HELP_333")`
  → 环境变量: `CLEANUP_PROJECT_HELP_333`

- 行 333: `help="清理多少天前的日志"`
  → `help = os.getenv("CLEANUP_PROJECT_HELP_333")`
  → 环境变量: `CLEANUP_PROJECT_HELP_333`

- 行 334: `help="归档多少天前的报告"`
  → `help = os.getenv("CLEANUP_PROJECT_HELP_334")`
  → 环境变量: `CLEANUP_PROJECT_HELP_334`

### scripts/line_length_fix.py

- 行 514: `description='自动修复超过行长限制的代码行'`
  → `description = os.getenv("LINE_LENGTH_FIX_DESCRIPTION_514")`
  → 环境变量: `LINE_LENGTH_FIX_DESCRIPTION_514`

- 行 515: `help='要修复的目录 (默认: 当前目录)'`
  → `help = os.getenv("LINE_LENGTH_FIX_HELP_515")`
  → 环境变量: `LINE_LENGTH_FIX_HELP_515`

- 行 516: `help='行长限制 (默认: 120 字符)'`
  → `help = os.getenv("LINE_LENGTH_FIX_HELP_516")`
  → 环境变量: `LINE_LENGTH_FIX_HELP_516`

- 行 517: `default='docs/_reports/LINE_LENGTH_REPORT.md'`
  → `default = os.getenv("LINE_LENGTH_FIX_DEFAULT_517")`
  → 环境变量: `LINE_LENGTH_FIX_DEFAULT_517`

- 行 518: `help='报告输出路径 (默认: docs/_reports/LINE_LENGTH_REPORT.md)'`
  → `help = os.getenv("LINE_LENGTH_FIX_HELP_518")`
  → 环境变量: `LINE_LENGTH_FIX_HELP_518`

### scripts/process_orphans.py

- 行 62: `category="Uncategorized"`
  → `category = os.getenv("PROCESS_ORPHANS_CATEGORY_62")`
  → 环境变量: `PROCESS_ORPHANS_CATEGORY_62`

- 行 117: `category = "Security"`
  → `category = os.getenv("PROCESS_ORPHANS_CATEGORY_117")`
  → 环境变量: `PROCESS_ORPHANS_CATEGORY_117`

- 行 119: `category = "Testing"`
  → `category = os.getenv("PROCESS_ORPHANS_CATEGORY_119")`
  → 环境变量: `PROCESS_ORPHANS_CATEGORY_119`

- 行 126: `category = "Performance"`
  → `category = os.getenv("PROCESS_ORPHANS_CATEGORY_126")`
  → 环境变量: `PROCESS_ORPHANS_CATEGORY_126`

- 行 127: `category = "General"`
  → `category = os.getenv("PROCESS_ORPHANS_CATEGORY_127")`
  → 环境变量: `PROCESS_ORPHANS_CATEGORY_127`

### scripts/validate_config.py

- 行 345: `description="验证生产环境配置"`
  → `description = os.getenv("VALIDATE_CONFIG_DESCRIPTION_345")`
  → 环境变量: `VALIDATE_CONFIG_DESCRIPTION_345`

- 行 346: `help="输出报告到文件"`
  → `help = os.getenv("VALIDATE_CONFIG_HELP_346")`
  → 环境变量: `VALIDATE_CONFIG_HELP_346`

- 行 347: `action='store_true'`
  → `action = os.getenv("VALIDATE_CONFIG_ACTION_347")`
  → 环境变量: `VALIDATE_CONFIG_ACTION_347`

- 行 349: `help="静默模式，只输出结果"`
  → `help = os.getenv("VALIDATE_CONFIG_HELP_349")`
  → 环境变量: `VALIDATE_CONFIG_HELP_349`

- 行 352: `format='%(levelname)s: %(message)s'`
  → `format = os.getenv("VALIDATE_CONFIG_FORMAT_352")`
  → 环境变量: `VALIDATE_CONFIG_FORMAT_352`

### scripts/deep_cleanup.py

- 行 405: `description="深度项目清理工具"`
  → `description = os.getenv("DEEP_CLEANUP_DESCRIPTION_405")`
  → 环境变量: `DEEP_CLEANUP_DESCRIPTION_405`

- 行 406: `help="项目根目录路径"`
  → `help = os.getenv("DEEP_CLEANUP_HELP_406")`
  → 环境变量: `DEEP_CLEANUP_HELP_406`

- 行 406: `action="store_true"`
  → `action = os.getenv("DEEP_CLEANUP_ACTION_406")`
  → 环境变量: `DEEP_CLEANUP_ACTION_406`

- 行 406: `help="试运行，不实际删除文件"`
  → `help = os.getenv("DEEP_CLEANUP_HELP_406")`
  → 环境变量: `DEEP_CLEANUP_HELP_406`

### scripts/context_loader.py

- 行 17: `message=".*Number.*field should not be instantiated.*"`
  → `message = os.getenv("CONTEXT_LOADER_MESSAGE_17")`
  → 环境变量: `CONTEXT_LOADER_MESSAGE_17`

- 行 21: `message=".*Number.*field.*should.*not.*be.*instantiated.*"`
  → `message = os.getenv("CONTEXT_LOADER_MESSAGE_21")`
  → 环境变量: `CONTEXT_LOADER_MESSAGE_21`

- 行 408: `str = "logs/project_context.json"`
  → `str = os.getenv("CONTEXT_LOADER_STR_408")`
  → 环境变量: `CONTEXT_LOADER_STR_408`

- 行 454: `description="项目上下文加载器"`
  → `description = os.getenv("CONTEXT_LOADER_DESCRIPTION_454")`
  → 环境变量: `CONTEXT_LOADER_DESCRIPTION_454`

- 行 456: `default="logs/project_context.json"`
  → `default = os.getenv("CONTEXT_LOADER_DEFAULT_456")`
  → 环境变量: `CONTEXT_LOADER_DEFAULT_456`

- 行 458: `action="store_true"`
  → `action = os.getenv("CONTEXT_LOADER_ACTION_458")`
  → 环境变量: `CONTEXT_LOADER_ACTION_458`

### scripts/refresh_materialized_views.py

- 行 34: `format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"`
  → `format = os.getenv("REFRESH_MATERIALIZED_VIEWS_FORMAT_34")`
  → 环境变量: `REFRESH_MATERIALIZED_VIEWS_FORMAT_34`

- 行 233: `schemaname = 'public'`
  → `schemaname = os.getenv("REFRESH_MATERIALIZED_VIEWS_SCHEMANAME_233")`
  → 环境变量: `REFRESH_MATERIALIZED_VIEWS_SCHEMANAME_233`

- 行 310: `description="物化视图刷新工具"`
  → `description = os.getenv("REFRESH_MATERIALIZED_VIEWS_DESCRIPTION_310")`
  → 环境变量: `REFRESH_MATERIALIZED_VIEWS_DESCRIPTION_310`

- 行 312: `help="指定要刷新的物化视图"`
  → `help = os.getenv("REFRESH_MATERIALIZED_VIEWS_HELP_312")`
  → 环境变量: `REFRESH_MATERIALIZED_VIEWS_HELP_312`

- 行 315: `action="store_true"`
  → `action = os.getenv("REFRESH_MATERIALIZED_VIEWS_ACTION_315")`
  → 环境变量: `REFRESH_MATERIALIZED_VIEWS_ACTION_315`

- 行 315: `help="使用并发刷新模式（需要视图有唯一索引）"`
  → `help = os.getenv("REFRESH_MATERIALIZED_VIEWS_HELP_315")`
  → 环境变量: `REFRESH_MATERIALIZED_VIEWS_HELP_315`

- 行 318: `action="store_true"`
  → `action = os.getenv("REFRESH_MATERIALIZED_VIEWS_ACTION_318")`
  → 环境变量: `REFRESH_MATERIALIZED_VIEWS_ACTION_318`

- 行 318: `help="显示物化视图信息"`
  → `help = os.getenv("REFRESH_MATERIALIZED_VIEWS_HELP_318")`
  → 环境变量: `REFRESH_MATERIALIZED_VIEWS_HELP_318`

### scripts/license_compliance_check.py

- 行 25: `COMPLIANT = "compliant"`
  → `COMPLIANT = os.getenv("LICENSE_COMPLIANCE_CHECK_COMPLIANT_25")`
  → 环境变量: `LICENSE_COMPLIANCE_CHECK_COMPLIANT_25`

- 行 25: `WARNING = "warning"`
  → `WARNING = os.getenv("LICENSE_COMPLIANCE_CHECK_WARNING_25")`
  → 环境变量: `LICENSE_COMPLIANCE_CHECK_WARNING_25`

- 行 25: `NON_COMPLIANT = "non_compliant"`
  → `NON_COMPLIANT = os.getenv("LICENSE_COMPLIANCE_CHECK_NON_COMPLIANT_25")`
  → 环境变量: `LICENSE_COMPLIANCE_CHECK_NON_COMPLIANT_25`

- 行 101: `summary="无法获取许可证数据"`
  → `summary = os.getenv("LICENSE_COMPLIANCE_CHECK_SUMMARY_101")`
  → 环境变量: `LICENSE_COMPLIANCE_CHECK_SUMMARY_101`

- 行 135: `summary = "所有许可证都符合要求"`
  → `summary = os.getenv("LICENSE_COMPLIANCE_CHECK_SUMMARY_135")`
  → 环境变量: `LICENSE_COMPLIANCE_CHECK_SUMMARY_135`

- 行 173: `issue_type="forbidden_license"`
  → `issue_type = os.getenv("LICENSE_COMPLIANCE_CHECK_ISSUE_TYPE_173")`
  → 环境变量: `LICENSE_COMPLIANCE_CHECK_ISSUE_TYPE_173`

- 行 174: `severity="critical"`
  → `severity = os.getenv("LICENSE_COMPLIANCE_CHECK_SEVERITY_174")`
  → 环境变量: `LICENSE_COMPLIANCE_CHECK_SEVERITY_174`

- 行 176: `recommendation="请立即寻找替代包"`
  → `recommendation = os.getenv("LICENSE_COMPLIANCE_CHECK_RECOMMENDATION_176")`
  → 环境变量: `LICENSE_COMPLIANCE_CHECK_RECOMMENDATION_176`

- 行 184: `issue_type="agpl_license"`
  → `issue_type = os.getenv("LICENSE_COMPLIANCE_CHECK_ISSUE_TYPE_184")`
  → 环境变量: `LICENSE_COMPLIANCE_CHECK_ISSUE_TYPE_184`

- 行 187: `recommendation="AGPL要求网络服务也开源，请评估法律风险"`
  → `recommendation = os.getenv("LICENSE_COMPLIANCE_CHECK_RECOMMENDATION_187")`
  → 环境变量: `LICENSE_COMPLIANCE_CHECK_RECOMMENDATION_187`

- 行 192: `issue_type="copyleft_license"`
  → `issue_type = os.getenv("LICENSE_COMPLIANCE_CHECK_ISSUE_TYPE_192")`
  → 环境变量: `LICENSE_COMPLIANCE_CHECK_ISSUE_TYPE_192`

- 行 193: `severity="medium"`
  → `severity = os.getenv("LICENSE_COMPLIANCE_CHECK_SEVERITY_193")`
  → 环境变量: `LICENSE_COMPLIANCE_CHECK_SEVERITY_193`

- 行 194: `recommendation="请确认使用方式符合许可证要求"`
  → `recommendation = os.getenv("LICENSE_COMPLIANCE_CHECK_RECOMMENDATION_194")`
  → 环境变量: `LICENSE_COMPLIANCE_CHECK_RECOMMENDATION_194`

- 行 201: `issue_type="unknown_license"`
  → `issue_type = os.getenv("LICENSE_COMPLIANCE_CHECK_ISSUE_TYPE_201")`
  → 环境变量: `LICENSE_COMPLIANCE_CHECK_ISSUE_TYPE_201`

- 行 202: `recommendation="请手动验证许可证合规性"`
  → `recommendation = os.getenv("LICENSE_COMPLIANCE_CHECK_RECOMMENDATION_202")`
  → 环境变量: `LICENSE_COMPLIANCE_CHECK_RECOMMENDATION_202`

- 行 231: `issue_type="special_requirement"`
  → `issue_type = os.getenv("LICENSE_COMPLIANCE_CHECK_ISSUE_TYPE_231")`
  → 环境变量: `LICENSE_COMPLIANCE_CHECK_ISSUE_TYPE_231`

- 行 360: `description="许可证合规检查"`
  → `description = os.getenv("LICENSE_COMPLIANCE_CHECK_DESCRIPTION_360")`
  → 环境变量: `LICENSE_COMPLIANCE_CHECK_DESCRIPTION_360`

- 行 361: `help="输入的许可证报告文件"`
  → `help = os.getenv("LICENSE_COMPLIANCE_CHECK_HELP_361")`
  → 环境变量: `LICENSE_COMPLIANCE_CHECK_HELP_361`

- 行 364: `help="输出的合规报告文件"`
  → `help = os.getenv("LICENSE_COMPLIANCE_CHECK_HELP_364")`
  → 环境变量: `LICENSE_COMPLIANCE_CHECK_HELP_364`

- 行 368: `action='store_true'`
  → `action = os.getenv("LICENSE_COMPLIANCE_CHECK_ACTION_368")`
  → 环境变量: `LICENSE_COMPLIANCE_CHECK_ACTION_368`

- 行 368: `help="CI模式，返回退出码"`
  → `help = os.getenv("LICENSE_COMPLIANCE_CHECK_HELP_368")`
  → 环境变量: `LICENSE_COMPLIANCE_CHECK_HELP_368`

### scripts/env_checker.py

- 行 476: `description="开发环境检查器"`
  → `description = os.getenv("ENV_CHECKER_DESCRIPTION_476")`
  → 环境变量: `ENV_CHECKER_DESCRIPTION_476`

- 行 478: `action="store_true"`
  → `action = os.getenv("ENV_CHECKER_ACTION_478")`
  → 环境变量: `ENV_CHECKER_ACTION_478`

- 行 478: `help="显示检查摘要"`
  → `help = os.getenv("ENV_CHECKER_HELP_478")`
  → 环境变量: `ENV_CHECKER_HELP_478`

- 行 478: `action="store_true"`
  → `action = os.getenv("ENV_CHECKER_ACTION_478")`
  → 环境变量: `ENV_CHECKER_ACTION_478`

- 行 478: `help="显示修复建议"`
  → `help = os.getenv("ENV_CHECKER_HELP_478")`
  → 环境变量: `ENV_CHECKER_HELP_478`

### scripts/fix_test_suite.py

- 行 89: `addopts = "-ra -q"`
  → `addopts = os.getenv("FIX_TEST_SUITE_ADDOPTS_89")`
  → 环境变量: `FIX_TEST_SUITE_ADDOPTS_89`

- 行 89: `addopts = "-ra -q --timeout=300 --timeout-method=thread"`
  → `addopts = os.getenv("FIX_TEST_SUITE_ADDOPTS_89")`
  → 环境变量: `FIX_TEST_SUITE_ADDOPTS_89`

- 行 111: `RED='\\033[0;31m'`
  → `RED = os.getenv("FIX_TEST_SUITE_RED_111")`
  → 环境变量: `FIX_TEST_SUITE_RED_111`

- 行 113: `GREEN='\\033[0;32m'`
  → `GREEN = os.getenv("FIX_TEST_SUITE_GREEN_113")`
  → 环境变量: `FIX_TEST_SUITE_GREEN_113`

- 行 114: `YELLOW='\\033[1;33m'`
  → `YELLOW = os.getenv("FIX_TEST_SUITE_YELLOW_114")`
  → 环境变量: `FIX_TEST_SUITE_YELLOW_114`

- 行 114: `NC='\\033[0m'`
  → `NC = os.getenv("FIX_TEST_SUITE_NC_114")`
  → 环境变量: `FIX_TEST_SUITE_NC_114`

### scripts/dependency_manager/create_clean_env.py

- 行 18: `venv_name = "venv_clean"`
  → `venv_name = os.getenv("CREATE_CLEAN_ENV_VENV_NAME_18")`
  → 环境变量: `CREATE_CLEAN_ENV_VENV_NAME_18`

### scripts/dependency_manager/task_board.py

- 行 96: `title="创建依赖诊断工具"`
  → `title = os.getenv("TASK_BOARD_TITLE_96")`
  → 环境变量: `TASK_BOARD_TITLE_96`

- 行 96: `description="开发一个全面的依赖诊断工具，能够检测版本冲突、循环依赖等问题"`
  → `description = os.getenv("TASK_BOARD_DESCRIPTION_96")`
  → 环境变量: `TASK_BOARD_DESCRIPTION_96`

- 行 99: `assignee="AI Assistant"`
  → `assignee = os.getenv("TASK_BOARD_ASSIGNEE_99")`
  → 环境变量: `TASK_BOARD_ASSIGNEE_99`

- 行 105: `title="生成完整依赖树"`
  → `title = os.getenv("TASK_BOARD_TITLE_105")`
  → 环境变量: `TASK_BOARD_TITLE_105`

- 行 106: `description="使用pipdeptree等工具生成项目的完整依赖关系图"`
  → `description = os.getenv("TASK_BOARD_DESCRIPTION_106")`
  → 环境变量: `TASK_BOARD_DESCRIPTION_106`

- 行 108: `assignee="AI Assistant"`
  → `assignee = os.getenv("TASK_BOARD_ASSIGNEE_108")`
  → 环境变量: `TASK_BOARD_ASSIGNEE_108`

- 行 114: `title="识别冲突源头"`
  → `title = os.getenv("TASK_BOARD_TITLE_114")`
  → 环境变量: `TASK_BOARD_TITLE_114`

- 行 114: `description="分析依赖树，定位scipy/highspy等具体冲突点"`
  → `description = os.getenv("TASK_BOARD_DESCRIPTION_114")`
  → 环境变量: `TASK_BOARD_DESCRIPTION_114`

- 行 120: `assignee="AI Assistant"`
  → `assignee = os.getenv("TASK_BOARD_ASSIGNEE_120")`
  → 环境变量: `TASK_BOARD_ASSIGNEE_120`

- 行 124: `title="分析版本兼容性矩阵"`
  → `title = os.getenv("TASK_BOARD_TITLE_124")`
  → 环境变量: `TASK_BOARD_TITLE_124`

- 行 125: `description="创建各包版本的兼容性矩阵，找出最佳组合"`
  → `description = os.getenv("TASK_BOARD_DESCRIPTION_125")`
  → 环境变量: `TASK_BOARD_DESCRIPTION_125`

- 行 130: `assignee="AI Assistant"`
  → `assignee = os.getenv("TASK_BOARD_ASSIGNEE_130")`
  → 环境变量: `TASK_BOARD_ASSIGNEE_130`

- 行 135: `title="备份当前环境"`
  → `title = os.getenv("TASK_BOARD_TITLE_135")`
  → 环境变量: `TASK_BOARD_TITLE_135`

- 行 135: `description="使用pip freeze备份当前所有依赖版本"`
  → `description = os.getenv("TASK_BOARD_DESCRIPTION_135")`
  → 环境变量: `TASK_BOARD_DESCRIPTION_135`

- 行 139: `assignee="AI Assistant"`
  → `assignee = os.getenv("TASK_BOARD_ASSIGNEE_139")`
  → 环境变量: `TASK_BOARD_ASSIGNEE_139`

- 行 146: `title="创建干净虚拟环境"`
  → `title = os.getenv("TASK_BOARD_TITLE_146")`
  → 环境变量: `TASK_BOARD_TITLE_146`

- 行 147: `description="创建全新的Python虚拟环境，避免污染"`
  → `description = os.getenv("TASK_BOARD_DESCRIPTION_147")`
  → 环境变量: `TASK_BOARD_DESCRIPTION_147`

- 行 149: `assignee="AI Assistant"`
  → `assignee = os.getenv("TASK_BOARD_ASSIGNEE_149")`
  → 环境变量: `TASK_BOARD_ASSIGNEE_149`

- 行 157: `title="解决关键冲突"`
  → `title = os.getenv("TASK_BOARD_TITLE_157")`
  → 环境变量: `TASK_BOARD_TITLE_157`

- 行 157: `description="修复scipy/highspy类型注册冲突"`
  → `description = os.getenv("TASK_BOARD_DESCRIPTION_157")`
  → 环境变量: `TASK_BOARD_DESCRIPTION_157`

- 行 160: `assignee="AI Assistant"`
  → `assignee = os.getenv("TASK_BOARD_ASSIGNEE_160")`
  → 环境变量: `TASK_BOARD_ASSIGNEE_160`

- 行 167: `title="验证核心功能"`
  → `title = os.getenv("TASK_BOARD_TITLE_167")`
  → 环境变量: `TASK_BOARD_TITLE_167`

- 行 168: `description="测试导入和基本功能是否正常"`
  → `description = os.getenv("TASK_BOARD_DESCRIPTION_168")`
  → 环境变量: `TASK_BOARD_DESCRIPTION_168`

- 行 170: `assignee="AI Assistant"`
  → `assignee = os.getenv("TASK_BOARD_ASSIGNEE_170")`
  → 环境变量: `TASK_BOARD_ASSIGNEE_170`

- 行 178: `title="开发依赖检测脚本"`
  → `title = os.getenv("TASK_BOARD_TITLE_178")`
  → 环境变量: `TASK_BOARD_TITLE_178`

- 行 179: `description="创建自动检测依赖冲突的脚本"`
  → `description = os.getenv("TASK_BOARD_DESCRIPTION_179")`
  → 环境变量: `TASK_BOARD_DESCRIPTION_179`

- 行 181: `assignee="AI Assistant"`
  → `assignee = os.getenv("TASK_BOARD_ASSIGNEE_181")`
  → 环境变量: `TASK_BOARD_ASSIGNEE_181`

- 行 186: `title="创建CI检查流程"`
  → `title = os.getenv("TASK_BOARD_TITLE_186")`
  → 环境变量: `TASK_BOARD_TITLE_186`

- 行 187: `description="在GitHub Actions中添加依赖冲突检查"`
  → `description = os.getenv("TASK_BOARD_DESCRIPTION_187")`
  → 环境变量: `TASK_BOARD_DESCRIPTION_187`

- 行 193: `assignee="AI Assistant"`
  → `assignee = os.getenv("TASK_BOARD_ASSIGNEE_193")`
  → 环境变量: `TASK_BOARD_ASSIGNEE_193`

- 行 197: `title="建立依赖监控仪表板"`
  → `title = os.getenv("TASK_BOARD_TITLE_197")`
  → 环境变量: `TASK_BOARD_TITLE_197`

- 行 197: `description="创建Web界面展示依赖状态"`
  → `description = os.getenv("TASK_BOARD_DESCRIPTION_197")`
  → 环境变量: `TASK_BOARD_DESCRIPTION_197`

- 行 200: `assignee="AI Assistant"`
  → `assignee = os.getenv("TASK_BOARD_ASSIGNEE_200")`
  → 环境变量: `TASK_BOARD_ASSIGNEE_200`

- 行 207: `title="设置自动化报告"`
  → `title = os.getenv("TASK_BOARD_TITLE_207")`
  → 环境变量: `TASK_BOARD_TITLE_207`

- 行 208: `description="定期生成依赖健康报告"`
  → `description = os.getenv("TASK_BOARD_DESCRIPTION_208")`
  → 环境变量: `TASK_BOARD_DESCRIPTION_208`

- 行 210: `assignee="AI Assistant"`
  → `assignee = os.getenv("TASK_BOARD_ASSIGNEE_210")`
  → 环境变量: `TASK_BOARD_ASSIGNEE_210`

- 行 218: `title="依赖锁定策略"`
  → `title = os.getenv("TASK_BOARD_TITLE_218")`
  → 环境变量: `TASK_BOARD_TITLE_218`

- 行 219: `description="制定和实施依赖版本锁定策略"`
  → `description = os.getenv("TASK_BOARD_DESCRIPTION_219")`
  → 环境变量: `TASK_BOARD_DESCRIPTION_219`

- 行 221: `assignee="AI Assistant"`
  → `assignee = os.getenv("TASK_BOARD_ASSIGNEE_221")`
  → 环境变量: `TASK_BOARD_ASSIGNEE_221`

- 行 229: `title="版本管理规范"`
  → `title = os.getenv("TASK_BOARD_TITLE_229")`
  → 环境变量: `TASK_BOARD_TITLE_229`

- 行 229: `description="建立包版本更新和管理规范"`
  → `description = os.getenv("TASK_BOARD_DESCRIPTION_229")`
  → 环境变量: `TASK_BOARD_DESCRIPTION_229`

- 行 232: `assignee="AI Assistant"`
  → `assignee = os.getenv("TASK_BOARD_ASSIGNEE_232")`
  → 环境变量: `TASK_BOARD_ASSIGNEE_232`

- 行 237: `title="更新流程标准化"`
  → `title = os.getenv("TASK_BOARD_TITLE_237")`
  → 环境变量: `TASK_BOARD_TITLE_237`

- 行 239: `description="标准化依赖更新流程"`
  → `description = os.getenv("TASK_BOARD_DESCRIPTION_239")`
  → 环境变量: `TASK_BOARD_DESCRIPTION_239`

- 行 243: `assignee="AI Assistant"`
  → `assignee = os.getenv("TASK_BOARD_ASSIGNEE_243")`
  → 环境变量: `TASK_BOARD_ASSIGNEE_243`

- 行 248: `description="编写文档并培训团队"`
  → `description = os.getenv("TASK_BOARD_DESCRIPTION_248")`
  → 环境变量: `TASK_BOARD_DESCRIPTION_248`

- 行 253: `assignee="AI Assistant"`
  → `assignee = os.getenv("TASK_BOARD_ASSIGNEE_253")`
  → 环境变量: `TASK_BOARD_ASSIGNEE_253`

- 行 258: `description="运行完整的测试套件验证修复"`
  → `description = os.getenv("TASK_BOARD_DESCRIPTION_258")`
  → 环境变量: `TASK_BOARD_DESCRIPTION_258`

- 行 261: `assignee="AI Assistant"`
  → `assignee = os.getenv("TASK_BOARD_ASSIGNEE_261")`
  → 环境变量: `TASK_BOARD_ASSIGNEE_261`

- 行 268: `title="性能基准测试"`
  → `title = os.getenv("TASK_BOARD_TITLE_268")`
  → 环境变量: `TASK_BOARD_TITLE_268`

- 行 269: `description="测试修复后的性能表现"`
  → `description = os.getenv("TASK_BOARD_DESCRIPTION_269")`
  → 环境变量: `TASK_BOARD_DESCRIPTION_269`

- 行 271: `assignee="AI Assistant"`
  → `assignee = os.getenv("TASK_BOARD_ASSIGNEE_271")`
  → 环境变量: `TASK_BOARD_ASSIGNEE_271`

- 行 279: `description="更新所有相关文档"`
  → `description = os.getenv("TASK_BOARD_DESCRIPTION_279")`
  → 环境变量: `TASK_BOARD_DESCRIPTION_279`

- 行 282: `assignee="AI Assistant"`
  → `assignee = os.getenv("TASK_BOARD_ASSIGNEE_282")`
  → 环境变量: `TASK_BOARD_ASSIGNEE_282`

- 行 291: `description="培训团队使用新工具和流程"`
  → `description = os.getenv("TASK_BOARD_DESCRIPTION_291")`
  → 环境变量: `TASK_BOARD_DESCRIPTION_291`

- 行 293: `assignee="AI Assistant"`
  → `assignee = os.getenv("TASK_BOARD_ASSIGNEE_293")`
  → 环境变量: `TASK_BOARD_ASSIGNEE_293`

- 行 447: `class="header"`
  → `class = os.getenv("TASK_BOARD_CLASS_447")`
  → 环境变量: `TASK_BOARD_CLASS_447`

- 行 449: `class="stat-box"`
  → `class = os.getenv("TASK_BOARD_CLASS_449")`
  → 环境变量: `TASK_BOARD_CLASS_449`

- 行 450: `class="stat-box"`
  → `class = os.getenv("TASK_BOARD_CLASS_450")`
  → 环境变量: `TASK_BOARD_CLASS_450`

- 行 451: `class="stat-box"`
  → `class = os.getenv("TASK_BOARD_CLASS_451")`
  → 环境变量: `TASK_BOARD_CLASS_451`

- 行 452: `class="stat-box"`
  → `class = os.getenv("TASK_BOARD_CLASS_452")`
  → 环境变量: `TASK_BOARD_CLASS_452`

- 行 463: `class="phase-header"`
  → `class = os.getenv("TASK_BOARD_CLASS_463")`
  → 环境变量: `TASK_BOARD_CLASS_463`

- 行 475: `class="task {priority_class} {status_class}"`
  → `class = os.getenv("TASK_BOARD_CLASS_475")`
  → 环境变量: `TASK_BOARD_CLASS_475`

- 行 478: `class="task-header"`
  → `class = os.getenv("TASK_BOARD_CLASS_478")`
  → 环境变量: `TASK_BOARD_CLASS_478`

- 行 479: `class="task-title"`
  → `class = os.getenv("TASK_BOARD_CLASS_479")`
  → 环境变量: `TASK_BOARD_CLASS_479`

- 行 486: `class="task-meta"`
  → `class = os.getenv("TASK_BOARD_CLASS_486")`
  → 环境变量: `TASK_BOARD_CLASS_486`

- 行 493: `class="dependencies"`
  → `class = os.getenv("TASK_BOARD_CLASS_493")`
  → 环境变量: `TASK_BOARD_CLASS_493`

### scripts/dependency_manager/diagnose_dependencies.py

- 行 196: `type="conflict"`
  → `type = os.getenv("DIAGNOSE_DEPENDENCIES_TYPE_196")`
  → 环境变量: `DIAGNOSE_DEPENDENCIES_TYPE_196`

- 行 198: `severity="critical"`
  → `severity = os.getenv("DIAGNOSE_DEPENDENCIES_SEVERITY_198")`
  → 环境变量: `DIAGNOSE_DEPENDENCIES_SEVERITY_198`

- 行 217: `type="version_conflict"`
  → `type = os.getenv("DIAGNOSE_DEPENDENCIES_TYPE_217")`
  → 环境变量: `DIAGNOSE_DEPENDENCIES_TYPE_217`

- 行 221: `solution="卸载多余版本，只保留一个"`
  → `solution = os.getenv("DIAGNOSE_DEPENDENCIES_SOLUTION_221")`
  → 环境变量: `DIAGNOSE_DEPENDENCIES_SOLUTION_221`

- 行 259: `type="circular"`
  → `type = os.getenv("DIAGNOSE_DEPENDENCIES_TYPE_259")`
  → 环境变量: `DIAGNOSE_DEPENDENCIES_TYPE_259`

- 行 262: `solution="重构依赖结构，消除循环引用"`
  → `solution = os.getenv("DIAGNOSE_DEPENDENCIES_SOLUTION_262")`
  → 环境变量: `DIAGNOSE_DEPENDENCIES_SOLUTION_262`

- 行 289: `severity = "critical"`
  → `severity = os.getenv("DIAGNOSE_DEPENDENCIES_SEVERITY_289")`
  → 环境变量: `DIAGNOSE_DEPENDENCIES_SEVERITY_289`

- 行 293: `type="import_error"`
  → `type = os.getenv("DIAGNOSE_DEPENDENCIES_TYPE_293")`
  → 环境变量: `DIAGNOSE_DEPENDENCIES_TYPE_293`

- 行 296: `solution="检查依赖或修复导入路径"`
  → `solution = os.getenv("DIAGNOSE_DEPENDENCIES_SOLUTION_296")`
  → 环境变量: `DIAGNOSE_DEPENDENCIES_SOLUTION_296`

- 行 323: `type="outdated"`
  → `type = os.getenv("DIAGNOSE_DEPENDENCIES_TYPE_323")`
  → 环境变量: `DIAGNOSE_DEPENDENCIES_TYPE_323`

- 行 326: `severity="medium"`
  → `severity = os.getenv("DIAGNOSE_DEPENDENCIES_SEVERITY_326")`
  → 环境变量: `DIAGNOSE_DEPENDENCIES_SEVERITY_326`

### scripts/analysis/comprehensive_mcp_health_check.py

- 行 63: `user="postgres"`
  → `user = os.getenv("COMPREHENSIVE_MCP_HEALTH_CHECK_USER_63")`
  → 环境变量: `COMPREHENSIVE_MCP_HEALTH_CHECK_USER_63`

- 行 63: `password="postgres"`
  → `password = os.getenv("COMPREHENSIVE_MCP_HEALTH_CHECK_PASSWORD_63")`
  → 环境变量: `COMPREHENSIVE_MCP_HEALTH_CHECK_PASSWORD_63`

- 行 64: `database="postgres"`
  → `database = os.getenv("COMPREHENSIVE_MCP_HEALTH_CHECK_DATABASE_64")`
  → 环境变量: `COMPREHENSIVE_MCP_HEALTH_CHECK_DATABASE_64`

- 行 118: `password="redispass"`
  → `password = os.getenv("COMPREHENSIVE_MCP_HEALTH_CHECK_PASSWORD_118")`
  → 环境变量: `COMPREHENSIVE_MCP_HEALTH_CHECK_PASSWORD_118`

- 行 146: `bootstrap_servers="localhost:9092"`
  → `bootstrap_servers = os.getenv("COMPREHENSIVE_MCP_HEALTH_CHECK_BOOTSTRAP_SERVERS_1")`
  → 环境变量: `COMPREHENSIVE_MCP_HEALTH_CHECK_BOOTSTRAP_SERVERS_1`

- 行 149: `client_id="mcp-health-check"`
  → `client_id = os.getenv("COMPREHENSIVE_MCP_HEALTH_CHECK_CLIENT_ID_149")`
  → 环境变量: `COMPREHENSIVE_MCP_HEALTH_CHECK_CLIENT_ID_149`

- 行 220: `namespace="default"`
  → `namespace = os.getenv("COMPREHENSIVE_MCP_HEALTH_CHECK_NAMESPACE_220")`
  → 环境变量: `COMPREHENSIVE_MCP_HEALTH_CHECK_NAMESPACE_220`

- 行 289: `YWRtaW46YWRtaW4="}
            response = requests.get(
                "`
  → `YWRtaW46YWRtaW4 = os.getenv("COMPREHENSIVE_MCP_HEALTH_CHECK_YWRTAW46YWRTAW4_289")`
  → 环境变量: `COMPREHENSIVE_MCP_HEALTH_CHECK_YWRTAW46YWRTAW4_289`

### scripts/fixes/fix_missing_colons_systematic.py

- 行 12: `errors='ignore'`
  → `errors = os.getenv("FIX_MISSING_COLONS_SYSTEMATIC_ERRORS_12")`
  → 环境变量: `FIX_MISSING_COLONS_SYSTEMATIC_ERRORS_12`

### scripts/fixes/fix_conftest_syntax.py

- 行 7: `file_path = "tests/conftest.py"`
  → `file_path = os.getenv("FIX_CONFTEST_SYNTAX_FILE_PATH_7")`
  → 环境变量: `FIX_CONFTEST_SYNTAX_FILE_PATH_7`

### scripts/fix_tools/fix_remaining_lint.py

- 行 85: `result =")

            # 添加缺失的导入
            if imports_to_add:
                # 找到导入区域
                lines = content.split("`
  → `result = os.getenv("FIX_REMAINING_LINT_RESULT_85")`
  → 环境变量: `FIX_REMAINING_LINT_RESULT_85`

### scripts/tests/test_quality_monitor.py

- 行 29: `table_name="matches"`
  → `table_name = os.getenv("TEST_QUALITY_MONITOR_TABLE_NAME_29")`
  → 环境变量: `TEST_QUALITY_MONITOR_TABLE_NAME_29`

- 行 42: `table_name="matches"`
  → `table_name = os.getenv("TEST_QUALITY_MONITOR_TABLE_NAME_42")`
  → 环境变量: `TEST_QUALITY_MONITOR_TABLE_NAME_42`

### scripts/tests/test_metadata_manager.py

- 行 71: `expected_value = "application/json"`
  → `expected_value = os.getenv("TEST_METADATA_MANAGER_EXPECTED_VALUE_71")`
  → 环境变量: `TEST_METADATA_MANAGER_EXPECTED_VALUE_71`

### scripts/tests/test_anomaly_detector.py

- 行 84: `table_name="test_table"`
  → `table_name = os.getenv("TEST_ANOMALY_DETECTOR_TABLE_NAME_84")`
  → 环境变量: `TEST_ANOMALY_DETECTOR_TABLE_NAME_84`

- 行 84: `detection_method="3sigma"`
  → `detection_method = os.getenv("TEST_ANOMALY_DETECTOR_DETECTION_METHOD_84")`
  → 环境变量: `TEST_ANOMALY_DETECTOR_DETECTION_METHOD_84`

- 行 85: `anomaly_type="statistical_outlier"`
  → `anomaly_type = os.getenv("TEST_ANOMALY_DETECTOR_ANOMALY_TYPE_85")`
  → 环境变量: `TEST_ANOMALY_DETECTOR_ANOMALY_TYPE_85`

- 行 85: `severity="medium"`
  → `severity = os.getenv("TEST_ANOMALY_DETECTOR_SEVERITY_85")`
  → 环境变量: `TEST_ANOMALY_DETECTOR_SEVERITY_85`

### scripts/tests/test_kafka_producer.py

- 行 42: `return_value="test-topic"`
  → `return_value = os.getenv("TEST_KAFKA_PRODUCER_RETURN_VALUE_42")`
  → 环境变量: `TEST_KAFKA_PRODUCER_RETURN_VALUE_42`

- 行 129: `str_data = "test message"`
  → `str_data = os.getenv("TEST_KAFKA_PRODUCER_STR_DATA_129")`
  → 环境变量: `TEST_KAFKA_PRODUCER_STR_DATA_129`

### scripts/tests/test_lineage_reporter.py

- 行 86: `namespace="test_namespace"`
  → `namespace = os.getenv("TEST_LINEAGE_REPORTER_NAMESPACE_86")`
  → 环境变量: `TEST_LINEAGE_REPORTER_NAMESPACE_86`

- 行 135: `job_name="test_job"`
  → `job_name = os.getenv("TEST_LINEAGE_REPORTER_JOB_NAME_135")`
  → 环境变量: `TEST_LINEAGE_REPORTER_JOB_NAME_135`

- 行 138: `description="Test job for lineage tracking"`
  → `description = os.getenv("TEST_LINEAGE_REPORTER_DESCRIPTION_138")`
  → 环境变量: `TEST_LINEAGE_REPORTER_DESCRIPTION_138`

- 行 148: `job_name="test_job"`
  → `job_name = os.getenv("TEST_LINEAGE_REPORTER_JOB_NAME_148")`
  → 环境变量: `TEST_LINEAGE_REPORTER_JOB_NAME_148`

- 行 164: `job_name="fail_test_job"`
  → `job_name = os.getenv("TEST_LINEAGE_REPORTER_JOB_NAME_164")`
  → 环境变量: `TEST_LINEAGE_REPORTER_JOB_NAME_164`

- 行 168: `job_name="fail_test_job"`
  → `job_name = os.getenv("TEST_LINEAGE_REPORTER_JOB_NAME_168")`
  → 环境变量: `TEST_LINEAGE_REPORTER_JOB_NAME_168`

- 行 169: `error_message="Test failure for lineage tracking"`
  → `error_message = os.getenv("TEST_LINEAGE_REPORTER_ERROR_MESSAGE_169")`
  → 环境变量: `TEST_LINEAGE_REPORTER_ERROR_MESSAGE_169`

- 行 183: `source_name="football_api"`
  → `source_name = os.getenv("TEST_LINEAGE_REPORTER_SOURCE_NAME_183")`
  → 环境变量: `TEST_LINEAGE_REPORTER_SOURCE_NAME_183`

- 行 184: `target_table="raw_matches"`
  → `target_table = os.getenv("TEST_LINEAGE_REPORTER_TARGET_TABLE_184")`
  → 环境变量: `TEST_LINEAGE_REPORTER_TARGET_TABLE_184`

- 行 198: `target_table="processed_features"`
  → `target_table = os.getenv("TEST_LINEAGE_REPORTER_TARGET_TABLE_198")`
  → 环境变量: `TEST_LINEAGE_REPORTER_TARGET_TABLE_198`

- 行 199: `transformation_sql="SELECT * FROM raw_matches WHERE processed = false"`
  → `transformation_sql = os.getenv("TEST_LINEAGE_REPORTER_TRANSFORMATION_SQL_199")`
  → 环境变量: `TEST_LINEAGE_REPORTER_TRANSFORMATION_SQL_199`

- 行 286: `job_name="integration_test"`
  → `job_name = os.getenv("TEST_LINEAGE_REPORTER_JOB_NAME_286")`
  → 环境变量: `TEST_LINEAGE_REPORTER_JOB_NAME_286`

### scripts/security/mlflow_audit.py

- 行 17: `format='%(asctime)s - %(levelname)s - %(message)s'`
  → `format = os.getenv("MLFLOW_AUDIT_FORMAT_17")`
  → 环境变量: `MLFLOW_AUDIT_FORMAT_17`

- 行 324: `description='MLflow 安全审计工具'`
  → `description = os.getenv("MLFLOW_AUDIT_DESCRIPTION_324")`
  → 环境变量: `MLFLOW_AUDIT_DESCRIPTION_324`

- 行 327: `help='项目根目录路径'`
  → `help = os.getenv("MLFLOW_AUDIT_HELP_327")`
  → 环境变量: `MLFLOW_AUDIT_HELP_327`

- 行 330: `help='输出报告文件路径'`
  → `help = os.getenv("MLFLOW_AUDIT_HELP_330")`
  → 环境变量: `MLFLOW_AUDIT_HELP_330`

- 行 332: `action='store_true'`
  → `action = os.getenv("MLFLOW_AUDIT_ACTION_332")`
  → 环境变量: `MLFLOW_AUDIT_ACTION_332`

- 行 334: `help='尝试自动修复问题'`
  → `help = os.getenv("MLFLOW_AUDIT_HELP_334")`
  → 环境变量: `MLFLOW_AUDIT_HELP_334`

- 行 336: `action='store_true'`
  → `action = os.getenv("MLFLOW_AUDIT_ACTION_336")`
  → 环境变量: `MLFLOW_AUDIT_ACTION_336`

- 行 337: `help='模拟运行，不实际修复'`
  → `help = os.getenv("MLFLOW_AUDIT_HELP_337")`
  → 环境变量: `MLFLOW_AUDIT_HELP_337`

### scripts/security/password_fixer.py

- 行 385: `description="密码安全修复工具"`
  → `description = os.getenv("PASSWORD_FIXER_DESCRIPTION_385")`
  → 环境变量: `PASSWORD_FIXER_DESCRIPTION_385`

- 行 387: `action="store_true"`
  → `action = os.getenv("PASSWORD_FIXER_ACTION_387")`
  → 环境变量: `PASSWORD_FIXER_ACTION_387`

- 行 387: `help="试运行，不修改文件"`
  → `help = os.getenv("PASSWORD_FIXER_HELP_387")`
  → 环境变量: `PASSWORD_FIXER_HELP_387`

- 行 387: `action="store_true"`
  → `action = os.getenv("PASSWORD_FIXER_ACTION_387")`
  → 环境变量: `PASSWORD_FIXER_ACTION_387`

- 行 387: `help="不生成环境变量模板"`
  → `help = os.getenv("PASSWORD_FIXER_HELP_387")`
  → 环境变量: `PASSWORD_FIXER_HELP_387`

- 行 101: `auth = ("username", "password")`
  → `auth = (os.getenv("PASSWORD_FIXER_AUTH_101_USER"), os.getenv("PASSWORD_FIXER_AUTH_101_PASS"))`
  → 环境变量: `PASSWORD_FIXER_AUTH_101`

### tests/conftest_core_mocks.py

- 行 69: `experiment_id="test_exp"`
  → `experiment_id = os.getenv("CONFTEST_CORE_MOCKS_EXPERIMENT_ID_69")`
  → 环境变量: `CONFTEST_CORE_MOCKS_EXPERIMENT_ID_69`

### tests/conftest.py

- 行 15: `scope="session"`
  → `scope = os.getenv("CONFTEST_SCOPE_15")`
  → 环境变量: `CONFTEST_SCOPE_15`

- 行 66: `current_stage = "Production"`
  → `current_stage = os.getenv("CONFTEST_CURRENT_STAGE_66")`
  → 环境变量: `CONFTEST_CURRENT_STAGE_66`

- 行 67: `name = "football_baseline_model"`
  → `name = os.getenv("CONFTEST_NAME_67")`
  → 环境变量: `CONFTEST_NAME_67`

### tests/integration/test_simple_api.py

- 行 57: `title="Test App"`
  → `title = os.getenv("TEST_SIMPLE_API_TITLE_57")`
  → 环境变量: `TEST_SIMPLE_API_TITLE_57`

### tests/integration/test_memory_database.py

- 行 126: `status = 'scheduled'`
  → `status = os.getenv("TEST_MEMORY_DATABASE_STATUS_126")`
  → 环境变量: `TEST_MEMORY_DATABASE_STATUS_126`

- 行 215: `status = 'active'`
  → `status = os.getenv("TEST_MEMORY_DATABASE_STATUS_215")`
  → 环境变量: `TEST_MEMORY_DATABASE_STATUS_215`

- 行 220: `status = 'resolved'`
  → `status = os.getenv("TEST_MEMORY_DATABASE_STATUS_220")`
  → 环境变量: `TEST_MEMORY_DATABASE_STATUS_220`

- 行 225: `status = 'active'`
  → `status = os.getenv("TEST_MEMORY_DATABASE_STATUS_225")`
  → 环境变量: `TEST_MEMORY_DATABASE_STATUS_225`

- 行 228: `status = 'resolved'`
  → `status = os.getenv("TEST_MEMORY_DATABASE_STATUS_228")`
  → 环境变量: `TEST_MEMORY_DATABASE_STATUS_228`

### tests/integration/test_api_to_database_integration.py

- 行 75: `match_status = "scheduled"`
  → `match_status = os.getenv("TEST_API_TO_DATABASE_INTEGRATION_MATCH_STATUS_75")`
  → 环境变量: `TEST_API_TO_DATABASE_INTEGRATION_MATCH_STATUS_75`

- 行 121: `match_status = "scheduled"`
  → `match_status = os.getenv("TEST_API_TO_DATABASE_INTEGRATION_MATCH_STATUS_121")`
  → 环境变量: `TEST_API_TO_DATABASE_INTEGRATION_MATCH_STATUS_121`

- 行 171: `match_status = "scheduled"`
  → `match_status = os.getenv("TEST_API_TO_DATABASE_INTEGRATION_MATCH_STATUS_171")`
  → 环境变量: `TEST_API_TO_DATABASE_INTEGRATION_MATCH_STATUS_171`

- 行 196: `search_term = "United"`
  → `search_term = os.getenv("TEST_API_TO_DATABASE_INTEGRATION_SEARCH_TERM_196")`
  → 环境变量: `TEST_API_TO_DATABASE_INTEGRATION_SEARCH_TERM_196`

- 行 206: `country = "England"`
  → `country = os.getenv("TEST_API_TO_DATABASE_INTEGRATION_COUNTRY_206")`
  → 环境变量: `TEST_API_TO_DATABASE_INTEGRATION_COUNTRY_206`

- 行 239: `match_status = "scheduled"`
  → `match_status = os.getenv("TEST_API_TO_DATABASE_INTEGRATION_MATCH_STATUS_239")`
  → 环境变量: `TEST_API_TO_DATABASE_INTEGRATION_MATCH_STATUS_239`

- 行 350: `database="test_db"`
  → `database = os.getenv("TEST_API_TO_DATABASE_INTEGRATION_DATABASE_350")`
  → 环境变量: `TEST_API_TO_DATABASE_INTEGRATION_DATABASE_350`

- 行 389: `match_status = "scheduled"`
  → `match_status = os.getenv("TEST_API_TO_DATABASE_INTEGRATION_MATCH_STATUS_389")`
  → 环境变量: `TEST_API_TO_DATABASE_INTEGRATION_MATCH_STATUS_389`

- 行 467: `value="scheduled"`
  → `value = os.getenv("TEST_API_TO_DATABASE_INTEGRATION_VALUE_467")`
  → 环境变量: `TEST_API_TO_DATABASE_INTEGRATION_VALUE_467`

- 行 489: `name = "Home Team"`
  → `name = os.getenv("TEST_API_TO_DATABASE_INTEGRATION_NAME_489")`
  → 环境变量: `TEST_API_TO_DATABASE_INTEGRATION_NAME_489`

- 行 493: `name = "Away Team"`
  → `name = os.getenv("TEST_API_TO_DATABASE_INTEGRATION_NAME_493")`
  → 环境变量: `TEST_API_TO_DATABASE_INTEGRATION_NAME_493`

- 行 495: `value = "scheduled"`
  → `value = os.getenv("TEST_API_TO_DATABASE_INTEGRATION_VALUE_495")`
  → 环境变量: `TEST_API_TO_DATABASE_INTEGRATION_VALUE_495`

- 行 360: `password="pass"`
  → `password = os.getenv("TEST_API_TO_DATABASE_INTEGRATION_PASSWORD_360")`
  → 环境变量: `TEST_API_TO_DATABASE_INTEGRATION_PASSWORD_360`

### tests/integration/test_database_integration.py

- 行 64: `name='matches'`
  → `name = os.getenv("TEST_DATABASE_INTEGRATION_NAME_64")`
  → 环境变量: `TEST_DATABASE_INTEGRATION_NAME_64`

### tests/integration/test_sqlite_integration.py

- 行 110: `title="Test API"`
  → `title = os.getenv("TEST_SQLITE_INTEGRATION_TITLE_110")`
  → 环境变量: `TEST_SQLITE_INTEGRATION_TITLE_110`

- 行 148: `title="数据库连接告警"`
  → `title = os.getenv("TEST_SQLITE_INTEGRATION_TITLE_148")`
  → 环境变量: `TEST_SQLITE_INTEGRATION_TITLE_148`

- 行 149: `message="SQLite连接测试"`
  → `message = os.getenv("TEST_SQLITE_INTEGRATION_MESSAGE_149")`
  → 环境变量: `TEST_SQLITE_INTEGRATION_MESSAGE_149`

- 行 150: `source="integration_test"`
  → `source = os.getenv("TEST_SQLITE_INTEGRATION_SOURCE_150")`
  → 环境变量: `TEST_SQLITE_INTEGRATION_SOURCE_150`

- 行 151: `title="数据完整性告警"`
  → `title = os.getenv("TEST_SQLITE_INTEGRATION_TITLE_151")`
  → 环境变量: `TEST_SQLITE_INTEGRATION_TITLE_151`

- 行 152: `message="测试数据完整性"`
  → `message = os.getenv("TEST_SQLITE_INTEGRATION_MESSAGE_152")`
  → 环境变量: `TEST_SQLITE_INTEGRATION_MESSAGE_152`

- 行 155: `source="integration_test"`
  → `source = os.getenv("TEST_SQLITE_INTEGRATION_SOURCE_155")`
  → 环境变量: `TEST_SQLITE_INTEGRATION_SOURCE_155`

### tests/integration/test_cache_integration.py

- 行 31: `redis_url="redis://localhost:6379/1"`
  → `redis_url = os.getenv("TEST_CACHE_INTEGRATION_REDIS_URL_31")`
  → 环境变量: `TEST_CACHE_INTEGRATION_REDIS_URL_31`

- 行 210: `cache_key = "test:ttl"`
  → `cache_key = os.getenv("TEST_CACHE_INTEGRATION_CACHE_KEY_210")`
  → 环境变量: `TEST_CACHE_INTEGRATION_CACHE_KEY_210`

### tests/integration/test_standalone_api.py

- 行 15: `title="Test API"`
  → `title = os.getenv("TEST_STANDALONE_API_TITLE_15")`
  → 环境变量: `TEST_STANDALONE_API_TITLE_15`

- 行 50: `detail="Not found"`
  → `detail = os.getenv("TEST_STANDALONE_API_DETAIL_50")`
  → 环境变量: `TEST_STANDALONE_API_DETAIL_50`

### tests/monitoring/quality_dashboard.py

- 行 48: `name="viewport"`
  → `name = os.getenv("QUALITY_DASHBOARD_NAME_48")`
  → 环境变量: `QUALITY_DASHBOARD_NAME_48`

- 行 48: `content="width=device-width, initial-scale=1.0"`
  → `content = os.getenv("QUALITY_DASHBOARD_CONTENT_48")`
  → 环境变量: `QUALITY_DASHBOARD_CONTENT_48`

- 行 257: `class="header"`
  → `class = os.getenv("QUALITY_DASHBOARD_CLASS_257")`
  → 环境变量: `QUALITY_DASHBOARD_CLASS_257`

- 行 262: `class="container"`
  → `class = os.getenv("QUALITY_DASHBOARD_CLASS_262")`
  → 环境变量: `QUALITY_DASHBOARD_CLASS_262`

- 行 262: `id="metrics-container"`
  → `id = os.getenv("QUALITY_DASHBOARD_ID_262")`
  → 环境变量: `QUALITY_DASHBOARD_ID_262`

- 行 263: `class="metrics-grid"`
  → `class = os.getenv("QUALITY_DASHBOARD_CLASS_263")`
  → 环境变量: `QUALITY_DASHBOARD_CLASS_263`

- 行 265: `class="loading"`
  → `class = os.getenv("QUALITY_DASHBOARD_CLASS_265")`
  → 环境变量: `QUALITY_DASHBOARD_CLASS_265`

- 行 266: `class="charts-container"`
  → `class = os.getenv("QUALITY_DASHBOARD_CLASS_266")`
  → 环境变量: `QUALITY_DASHBOARD_CLASS_266`

- 行 266: `class="chart-card"`
  → `class = os.getenv("QUALITY_DASHBOARD_CLASS_266")`
  → 环境变量: `QUALITY_DASHBOARD_CLASS_266`

- 行 267: `class="chart-container"`
  → `class = os.getenv("QUALITY_DASHBOARD_CLASS_267")`
  → 环境变量: `QUALITY_DASHBOARD_CLASS_267`

- 行 270: `id="coverageChart"`
  → `id = os.getenv("QUALITY_DASHBOARD_ID_270")`
  → 环境变量: `QUALITY_DASHBOARD_ID_270`

- 行 271: `class="chart-card"`
  → `class = os.getenv("QUALITY_DASHBOARD_CLASS_271")`
  → 环境变量: `QUALITY_DASHBOARD_CLASS_271`

- 行 273: `class="chart-container"`
  → `class = os.getenv("QUALITY_DASHBOARD_CLASS_273")`
  → 环境变量: `QUALITY_DASHBOARD_CLASS_273`

- 行 273: `id="performanceChart"`
  → `id = os.getenv("QUALITY_DASHBOARD_ID_273")`
  → 环境变量: `QUALITY_DASHBOARD_ID_273`

- 行 275: `class="recommendations"`
  → `class = os.getenv("QUALITY_DASHBOARD_CLASS_275")`
  → 环境变量: `QUALITY_DASHBOARD_CLASS_275`

- 行 278: `id="recommendations-list"`
  → `id = os.getenv("QUALITY_DASHBOARD_ID_278")`
  → 环境变量: `QUALITY_DASHBOARD_ID_278`

- 行 279: `class="loading"`
  → `class = os.getenv("QUALITY_DASHBOARD_CLASS_279")`
  → 环境变量: `QUALITY_DASHBOARD_CLASS_279`

- 行 317: `class="metric-card"`
  → `class = os.getenv("QUALITY_DASHBOARD_CLASS_317")`
  → 环境变量: `QUALITY_DASHBOARD_CLASS_317`

- 行 320: `class="metric-label"`
  → `class = os.getenv("QUALITY_DASHBOARD_CLASS_320")`
  → 环境变量: `QUALITY_DASHBOARD_CLASS_320`

- 行 321: `class="metric-value"`
  → `class = os.getenv("QUALITY_DASHBOARD_CLASS_321")`
  → 环境变量: `QUALITY_DASHBOARD_CLASS_321`

- 行 323: `class="quality-grade ${gradeClass}"`
  → `class = os.getenv("QUALITY_DASHBOARD_CLASS_323")`
  → 环境变量: `QUALITY_DASHBOARD_CLASS_323`

- 行 326: `class="metric-value"`
  → `class = os.getenv("QUALITY_DASHBOARD_CLASS_326")`
  → 环境变量: `QUALITY_DASHBOARD_CLASS_326`

- 行 328: `class="metric-trend"`
  → `class = os.getenv("QUALITY_DASHBOARD_CLASS_328")`
  → 环境变量: `QUALITY_DASHBOARD_CLASS_328`

- 行 331: `class="metric-card"`
  → `class = os.getenv("QUALITY_DASHBOARD_CLASS_331")`
  → 环境变量: `QUALITY_DASHBOARD_CLASS_331`

- 行 332: `class="metric-label"`
  → `class = os.getenv("QUALITY_DASHBOARD_CLASS_332")`
  → 环境变量: `QUALITY_DASHBOARD_CLASS_332`

- 行 332: `class="metric-value"`
  → `class = os.getenv("QUALITY_DASHBOARD_CLASS_332")`
  → 环境变量: `QUALITY_DASHBOARD_CLASS_332`

- 行 333: `class="metric-trend trend-${metrics.coverage_trend}"`
  → `class = os.getenv("QUALITY_DASHBOARD_CLASS_333")`
  → 环境变量: `QUALITY_DASHBOARD_CLASS_333`

- 行 337: `class="metric-card"`
  → `class = os.getenv("QUALITY_DASHBOARD_CLASS_337")`
  → 环境变量: `QUALITY_DASHBOARD_CLASS_337`

- 行 337: `class="metric-label"`
  → `class = os.getenv("QUALITY_DASHBOARD_CLASS_337")`
  → 环境变量: `QUALITY_DASHBOARD_CLASS_337`

- 行 340: `class="metric-value"`
  → `class = os.getenv("QUALITY_DASHBOARD_CLASS_340")`
  → 环境变量: `QUALITY_DASHBOARD_CLASS_340`

- 行 341: `class="metric-trend trend-${metrics.performance_trend}"`
  → `class = os.getenv("QUALITY_DASHBOARD_CLASS_341")`
  → 环境变量: `QUALITY_DASHBOARD_CLASS_341`

- 行 344: `class="metric-card"`
  → `class = os.getenv("QUALITY_DASHBOARD_CLASS_344")`
  → 环境变量: `QUALITY_DASHBOARD_CLASS_344`

- 行 345: `class="metric-label"`
  → `class = os.getenv("QUALITY_DASHBOARD_CLASS_345")`
  → 环境变量: `QUALITY_DASHBOARD_CLASS_345`

- 行 345: `class="metric-value"`
  → `class = os.getenv("QUALITY_DASHBOARD_CLASS_345")`
  → 环境变量: `QUALITY_DASHBOARD_CLASS_345`

- 行 349: `class="metric-trend"`
  → `class = os.getenv("QUALITY_DASHBOARD_CLASS_349")`
  → 环境变量: `QUALITY_DASHBOARD_CLASS_349`

- 行 350: `class="metric-card"`
  → `class = os.getenv("QUALITY_DASHBOARD_CLASS_350")`
  → 环境变量: `QUALITY_DASHBOARD_CLASS_350`

- 行 350: `class="metric-label"`
  → `class = os.getenv("QUALITY_DASHBOARD_CLASS_350")`
  → 环境变量: `QUALITY_DASHBOARD_CLASS_350`

- 行 351: `class="metric-value"`
  → `class = os.getenv("QUALITY_DASHBOARD_CLASS_351")`
  → 环境变量: `QUALITY_DASHBOARD_CLASS_351`

- 行 352: `class="metric-trend"`
  → `class = os.getenv("QUALITY_DASHBOARD_CLASS_352")`
  → 环境变量: `QUALITY_DASHBOARD_CLASS_352`

- 行 353: `class="metric-card"`
  → `class = os.getenv("QUALITY_DASHBOARD_CLASS_353")`
  → 环境变量: `QUALITY_DASHBOARD_CLASS_353`

- 行 353: `class="metric-label"`
  → `class = os.getenv("QUALITY_DASHBOARD_CLASS_353")`
  → 环境变量: `QUALITY_DASHBOARD_CLASS_353`

- 行 354: `class="metric-value"`
  → `class = os.getenv("QUALITY_DASHBOARD_CLASS_354")`
  → 环境变量: `QUALITY_DASHBOARD_CLASS_354`

- 行 355: `class="metric-trend"`
  → `class = os.getenv("QUALITY_DASHBOARD_CLASS_355")`
  → 环境变量: `QUALITY_DASHBOARD_CLASS_355`

- 行 425: `innerHTML = '<p>✅ 所有质量指标都良好！</p>'`
  → `innerHTML = os.getenv("QUALITY_DASHBOARD_INNERHTML_425")`
  → 环境变量: `QUALITY_DASHBOARD_INNERHTML_425`

- 行 429: `class="recommendation-item"`
  → `class = os.getenv("QUALITY_DASHBOARD_CLASS_429")`
  → 环境变量: `QUALITY_DASHBOARD_CLASS_429`

- 行 431: `class="recommendation-icon"`
  → `class = os.getenv("QUALITY_DASHBOARD_CLASS_431")`
  → 环境变量: `QUALITY_DASHBOARD_CLASS_431`

- 行 435: `style="margin-top: 5px; color: #666;"`
  → `style = os.getenv("QUALITY_DASHBOARD_STYLE_435")`
  → 环境变量: `QUALITY_DASHBOARD_STYLE_435`

- 行 607: `description="测试质量仪表板"`
  → `description = os.getenv("QUALITY_DASHBOARD_DESCRIPTION_607")`
  → 环境变量: `QUALITY_DASHBOARD_DESCRIPTION_607`

- 行 609: `action="store_true"`
  → `action = os.getenv("QUALITY_DASHBOARD_ACTION_609")`
  → 环境变量: `QUALITY_DASHBOARD_ACTION_609`

- 行 609: `help="生成静态HTML报告"`
  → `help = os.getenv("QUALITY_DASHBOARD_HELP_609")`
  → 环境变量: `QUALITY_DASHBOARD_HELP_609`

- 行 613: `help="输出文件名（仅静态模式）"`
  → `help = os.getenv("QUALITY_DASHBOARD_HELP_613")`
  → 环境变量: `QUALITY_DASHBOARD_HELP_613`

- 行 616: `action="store_true"`
  → `action = os.getenv("QUALITY_DASHBOARD_ACTION_616")`
  → 环境变量: `QUALITY_DASHBOARD_ACTION_616`

- 行 617: `help="运行Web服务器"`
  → `help = os.getenv("QUALITY_DASHBOARD_HELP_617")`
  → 环境变量: `QUALITY_DASHBOARD_HELP_617`

- 行 623: `help="服务器主机地址"`
  → `help = os.getenv("QUALITY_DASHBOARD_HELP_623")`
  → 环境变量: `QUALITY_DASHBOARD_HELP_623`

- 行 628: `action="store_true"`
  → `action = os.getenv("QUALITY_DASHBOARD_ACTION_628")`
  → 环境变量: `QUALITY_DASHBOARD_ACTION_628`

- 行 633: `help="项目根目录路径"`
  → `help = os.getenv("QUALITY_DASHBOARD_HELP_633")`
  → 环境变量: `QUALITY_DASHBOARD_HELP_633`

### tests/monitoring/test_quality_monitor.py

- 行 465: `description="测试质量监控工具"`
  → `description = os.getenv("TEST_QUALITY_MONITOR_DESCRIPTION_465")`
  → 环境变量: `TEST_QUALITY_MONITOR_DESCRIPTION_465`

- 行 466: `help="输出文件路径"`
  → `help = os.getenv("TEST_QUALITY_MONITOR_HELP_466")`
  → 环境变量: `TEST_QUALITY_MONITOR_HELP_466`

- 行 466: `action="store_true"`
  → `action = os.getenv("TEST_QUALITY_MONITOR_ACTION_466")`
  → 环境变量: `TEST_QUALITY_MONITOR_ACTION_466`

### tests/monitoring/coverage_optimization.py

- 行 269: `decorator = "@pytest.mark.asyncio\n    "`
  → `decorator = os.getenv("COVERAGE_OPTIMIZATION_DECORATOR_269")`
  → 环境变量: `COVERAGE_OPTIMIZATION_DECORATOR_269`

- 行 396: `description="覆盖率优化工具"`
  → `description = os.getenv("COVERAGE_OPTIMIZATION_DESCRIPTION_396")`
  → 环境变量: `COVERAGE_OPTIMIZATION_DESCRIPTION_396`

- 行 396: `help="为指定模块生成测试模板"`
  → `help = os.getenv("COVERAGE_OPTIMIZATION_HELP_396")`
  → 环境变量: `COVERAGE_OPTIMIZATION_HELP_396`

- 行 397: `action="store_true"`
  → `action = os.getenv("COVERAGE_OPTIMIZATION_ACTION_397")`
  → 环境变量: `COVERAGE_OPTIMIZATION_ACTION_397`

- 行 397: `help="生成优化计划"`
  → `help = os.getenv("COVERAGE_OPTIMIZATION_HELP_397")`
  → 环境变量: `COVERAGE_OPTIMIZATION_HELP_397`

- 行 398: `help="生成测试模板并保存到文件"`
  → `help = os.getenv("COVERAGE_OPTIMIZATION_HELP_398")`
  → 环境变量: `COVERAGE_OPTIMIZATION_HELP_398`

### tests/legacy/conftest_broken.py

- 行 232: `orient="]records["`
  → `orient = os.getenv("CONFTEST_BROKEN_ORIENT_232")`
  → 环境变量: `CONFTEST_BROKEN_ORIENT_232`

- 行 651: `return_value="]string["`
  → `return_value = os.getenv("CONFTEST_BROKEN_RETURN_VALUE_651")`
  → 环境变量: `CONFTEST_BROKEN_RETURN_VALUE_651`

- 行 651: `return_value="]string["`
  → `return_value = os.getenv("CONFTEST_BROKEN_RETURN_VALUE_651")`
  → 环境变量: `CONFTEST_BROKEN_RETURN_VALUE_651`

- 行 702: `__version__ = "]1.24.0["`
  → `__version__ = os.getenv("CONFTEST_BROKEN___VERSION___702")`
  → 环境变量: `CONFTEST_BROKEN___VERSION___702`

- 行 993: `scope="]]session["`
  → `scope = os.getenv("CONFTEST_BROKEN_SCOPE_993")`
  → 环境变量: `CONFTEST_BROKEN_SCOPE_993`

- 行 1004: `host = "]localhost["`
  → `host = os.getenv("CONFTEST_BROKEN_HOST_1004")`
  → 环境变量: `CONFTEST_BROKEN_HOST_1004`

- 行 1018: `scope="session["`
  → `scope = os.getenv("CONFTEST_BROKEN_SCOPE_1018")`
  → 环境变量: `CONFTEST_BROKEN_SCOPE_1018`

- 行 1237: `current_stage = "]Production["`
  → `current_stage = os.getenv("CONFTEST_BROKEN_CURRENT_STAGE_1237")`
  → 环境变量: `CONFTEST_BROKEN_CURRENT_STAGE_1237`

- 行 1241: `name = "]football_baseline_model["`
  → `name = os.getenv("CONFTEST_BROKEN_NAME_1241")`
  → 环境变量: `CONFTEST_BROKEN_NAME_1241`

- 行 1254: `return_value="]experiment_123["`
  → `return_value = os.getenv("CONFTEST_BROKEN_RETURN_VALUE_1254")`
  → 环境变量: `CONFTEST_BROKEN_RETURN_VALUE_1254`

- 行 1278: `return_value="]experiment_123["`
  → `return_value = os.getenv("CONFTEST_BROKEN_RETURN_VALUE_1278")`
  → 环境变量: `CONFTEST_BROKEN_RETURN_VALUE_1278`

- 行 1290: `run_id = "]run_123["`
  → `run_id = os.getenv("CONFTEST_BROKEN_RUN_ID_1290")`
  → 环境变量: `CONFTEST_BROKEN_RUN_ID_1290`

- 行 1512: `orient = "]records["`
  → `orient = os.getenv("CONFTEST_BROKEN_ORIENT_1512")`
  → 环境变量: `CONFTEST_BROKEN_ORIENT_1512`

- 行 2198: `registry_path = "]/tmp/feature_repo/data/registry.db["`
  → `registry_path = os.getenv("CONFTEST_BROKEN_REGISTRY_PATH_2198")`
  → 环境变量: `CONFTEST_BROKEN_REGISTRY_PATH_2198`

- 行 2276: `message="].*Number.*field should not be instantiated.*"`
  → `message = os.getenv("CONFTEST_BROKEN_MESSAGE_2276")`
  → 环境变量: `CONFTEST_BROKEN_MESSAGE_2276`

- 行 2282: `message="].*Number.*field.*should.*not.*be.*instantiated.*"`
  → `message = os.getenv("CONFTEST_BROKEN_MESSAGE_2282")`
  → 环境变量: `CONFTEST_BROKEN_MESSAGE_2282`

### tests/legacy/conftest_minimal.py

- 行 15: `scope="session"`
  → `scope = os.getenv("CONFTEST_MINIMAL_SCOPE_15")`
  → 环境变量: `CONFTEST_MINIMAL_SCOPE_15`

- 行 66: `current_stage = "Production"`
  → `current_stage = os.getenv("CONFTEST_MINIMAL_CURRENT_STAGE_66")`
  → 环境变量: `CONFTEST_MINIMAL_CURRENT_STAGE_66`

- 行 67: `name = "football_baseline_model"`
  → `name = os.getenv("CONFTEST_MINIMAL_NAME_67")`
  → 环境变量: `CONFTEST_MINIMAL_NAME_67`

### tests/legacy/integration/test_mlflow_database_integration.py

- 行 38: `current_stage = "]Production["`
  → `current_stage = os.getenv("TEST_MLFLOW_DATABASE_INTEGRATION_CURRENT_STAGE_38")`
  → 环境变量: `TEST_MLFLOW_DATABASE_INTEGRATION_CURRENT_STAGE_38`

- 行 48: `model_name="]test_model["`
  → `model_name = os.getenv("TEST_MLFLOW_DATABASE_INTEGRATION_MODEL_NAME_48")`
  → 环境变量: `TEST_MLFLOW_DATABASE_INTEGRATION_MODEL_NAME_48`

- 行 49: `predicted_result="]home["`
  → `predicted_result = os.getenv("TEST_MLFLOW_DATABASE_INTEGRATION_PREDICTED_RESULT_")`
  → 环境变量: `TEST_MLFLOW_DATABASE_INTEGRATION_PREDICTED_RESULT_`

- 行 79: `experiment_id = "test_experiment_123["`
  → `experiment_id = os.getenv("TEST_MLFLOW_DATABASE_INTEGRATION_EXPERIMENT_ID_79")`
  → 环境变量: `TEST_MLFLOW_DATABASE_INTEGRATION_EXPERIMENT_ID_79`

- 行 97: `current_stage = "]Staging["`
  → `current_stage = os.getenv("TEST_MLFLOW_DATABASE_INTEGRATION_CURRENT_STAGE_97")`
  → 环境变量: `TEST_MLFLOW_DATABASE_INTEGRATION_CURRENT_STAGE_97`

- 行 116: `model_name="]test_model["`
  → `model_name = os.getenv("TEST_MLFLOW_DATABASE_INTEGRATION_MODEL_NAME_116")`
  → 环境变量: `TEST_MLFLOW_DATABASE_INTEGRATION_MODEL_NAME_116`

- 行 119: `predicted_result="]home["`
  → `predicted_result = os.getenv("TEST_MLFLOW_DATABASE_INTEGRATION_PREDICTED_RESULT_")`
  → 环境变量: `TEST_MLFLOW_DATABASE_INTEGRATION_PREDICTED_RESULT_`

### tests/legacy/integration/conftest.py

- 行 9: `scope="session"`
  → `scope = os.getenv("CONFTEST_SCOPE_9")`
  → 环境变量: `CONFTEST_SCOPE_9`

- 行 13: `scope="session"`
  → `scope = os.getenv("CONFTEST_SCOPE_13")`
  → 环境变量: `CONFTEST_SCOPE_13`

### tests/legacy/integration/api/test_api_features.py

- 行 34: `table_name = 'matches'`
  → `table_name = os.getenv("TEST_API_FEATURES_TABLE_NAME_34")`
  → 环境变量: `TEST_API_FEATURES_TABLE_NAME_34`

- 行 53: `reason="Database connection not available["`
  → `reason = os.getenv("TEST_API_FEATURES_REASON_53")`
  → 环境变量: `TEST_API_FEATURES_REASON_53`

- 行 80: `season="2024-25["`
  → `season = os.getenv("TEST_API_FEATURES_SEASON_80")`
  → 环境变量: `TEST_API_FEATURES_SEASON_80`

- 行 80: `match_status="]scheduled["`
  → `match_status = os.getenv("TEST_API_FEATURES_MATCH_STATUS_80")`
  → 环境变量: `TEST_API_FEATURES_MATCH_STATUS_80`

- 行 85: `venue="]测试球场["`
  → `venue = os.getenv("TEST_API_FEATURES_VENUE_85")`
  → 环境变量: `TEST_API_FEATURES_VENUE_85`

### tests/legacy/integration/performance/test_performance_benchmarks.py

- 行 292: `baseline_file = "]]tests/performance/baseline_metrics.json["`
  → `baseline_file = os.getenv("TEST_PERFORMANCE_BENCHMARKS_BASELINE_FILE_292")`
  → 环境变量: `TEST_PERFORMANCE_BENCHMARKS_BASELINE_FILE_292`

- 行 347: `cache_key = "]]baseline_test_key["`
  → `cache_key = os.getenv("TEST_PERFORMANCE_BENCHMARKS_CACHE_KEY_347")`
  → 环境变量: `TEST_PERFORMANCE_BENCHMARKS_CACHE_KEY_347`

### tests/legacy/integration/performance/test_concurrent_requests.py

- 行 84: `user_id = "test_user["`
  → `user_id = os.getenv("TEST_CONCURRENT_REQUESTS_USER_ID_84")`
  → 环境变量: `TEST_CONCURRENT_REQUESTS_USER_ID_84`

- 行 107: `cache_key = "concurrent_test_key["`
  → `cache_key = os.getenv("TEST_CONCURRENT_REQUESTS_CACHE_KEY_107")`
  → 环境变量: `TEST_CONCURRENT_REQUESTS_CACHE_KEY_107`

### tests/legacy/integration/performance/test_api_performance.py

- 行 245: `test_key = "performance_test_key["`
  → `test_key = os.getenv("TEST_API_PERFORMANCE_TEST_KEY_245")`
  → 环境变量: `TEST_API_PERFORMANCE_TEST_KEY_245`

### tests/legacy/integration/models/test_model_integration.py

- 行 52: `table_name = 'matches'`
  → `table_name = os.getenv("TEST_MODEL_INTEGRATION_TABLE_NAME_52")`
  → 环境变量: `TEST_MODEL_INTEGRATION_TABLE_NAME_52`

- 行 66: `table_name = 'predictions'`
  → `table_name = os.getenv("TEST_MODEL_INTEGRATION_TABLE_NAME_66")`
  → 环境变量: `TEST_MODEL_INTEGRATION_TABLE_NAME_66`

- 行 79: `reason="Database connection not available["`
  → `reason = os.getenv("TEST_MODEL_INTEGRATION_REASON_79")`
  → 环境变量: `TEST_MODEL_INTEGRATION_REASON_79`

- 行 96: `league_name="Test League["`
  → `league_name = os.getenv("TEST_MODEL_INTEGRATION_LEAGUE_NAME_96")`
  → 环境变量: `TEST_MODEL_INTEGRATION_LEAGUE_NAME_96`

- 行 97: `country="]Test Country["`
  → `country = os.getenv("TEST_MODEL_INTEGRATION_COUNTRY_97")`
  → 环境变量: `TEST_MODEL_INTEGRATION_COUNTRY_97`

- 行 99: `team_name="]Home Team["`
  → `team_name = os.getenv("TEST_MODEL_INTEGRATION_TEAM_NAME_99")`
  → 环境变量: `TEST_MODEL_INTEGRATION_TEAM_NAME_99`

- 行 99: `country="]Test Country["`
  → `country = os.getenv("TEST_MODEL_INTEGRATION_COUNTRY_99")`
  → 环境变量: `TEST_MODEL_INTEGRATION_COUNTRY_99`

- 行 102: `team_name="]Away Team["`
  → `team_name = os.getenv("TEST_MODEL_INTEGRATION_TEAM_NAME_102")`
  → 环境变量: `TEST_MODEL_INTEGRATION_TEAM_NAME_102`

- 行 103: `country="]Test Country["`
  → `country = os.getenv("TEST_MODEL_INTEGRATION_COUNTRY_103")`
  → 环境变量: `TEST_MODEL_INTEGRATION_COUNTRY_103`

- 行 106: `season="]2024-25["`
  → `season = os.getenv("TEST_MODEL_INTEGRATION_SEASON_106")`
  → 环境变量: `TEST_MODEL_INTEGRATION_SEASON_106`

- 行 108: `match_status="]scheduled["`
  → `match_status = os.getenv("TEST_MODEL_INTEGRATION_MATCH_STATUS_108")`
  → 环境变量: `TEST_MODEL_INTEGRATION_MATCH_STATUS_108`

- 行 123: `run_id = "]test_run_id_123["`
  → `run_id = os.getenv("TEST_MODEL_INTEGRATION_RUN_ID_123")`
  → 环境变量: `TEST_MODEL_INTEGRATION_RUN_ID_123`

- 行 132: `experiment_id = "]]test_experiment_id["`
  → `experiment_id = os.getenv("TEST_MODEL_INTEGRATION_EXPERIMENT_ID_132")`
  → 环境变量: `TEST_MODEL_INTEGRATION_EXPERIMENT_ID_132`

- 行 146: `season="]2024-25["`
  → `season = os.getenv("TEST_MODEL_INTEGRATION_SEASON_146")`
  → 环境变量: `TEST_MODEL_INTEGRATION_SEASON_146`

- 行 149: `match_status="]completed["`
  → `match_status = os.getenv("TEST_MODEL_INTEGRATION_MATCH_STATUS_149")`
  → 环境变量: `TEST_MODEL_INTEGRATION_MATCH_STATUS_149`

- 行 208: `current_stage = "]Production["`
  → `current_stage = os.getenv("TEST_MODEL_INTEGRATION_CURRENT_STAGE_208")`
  → 环境变量: `TEST_MODEL_INTEGRATION_CURRENT_STAGE_208`

- 行 263: `model_name="]test_model["`
  → `model_name = os.getenv("TEST_MODEL_INTEGRATION_MODEL_NAME_263")`
  → 环境变量: `TEST_MODEL_INTEGRATION_MODEL_NAME_263`

- 行 265: `predicted_result="]home_win["`
  → `predicted_result = os.getenv("TEST_MODEL_INTEGRATION_PREDICTED_RESULT_265")`
  → 环境变量: `TEST_MODEL_INTEGRATION_PREDICTED_RESULT_265`

- 行 272: `match_status = "]completed["`
  → `match_status = os.getenv("TEST_MODEL_INTEGRATION_MATCH_STATUS_272")`
  → 环境变量: `TEST_MODEL_INTEGRATION_MATCH_STATUS_272`

- 行 282: `model_name="]test_model["`
  → `model_name = os.getenv("TEST_MODEL_INTEGRATION_MODEL_NAME_282")`
  → 环境变量: `TEST_MODEL_INTEGRATION_MODEL_NAME_282`

- 行 285: `predicted_result="]home["`
  → `predicted_result = os.getenv("TEST_MODEL_INTEGRATION_PREDICTED_RESULT_285")`
  → 环境变量: `TEST_MODEL_INTEGRATION_PREDICTED_RESULT_285`

- 行 291: `model_name="]test_model["`
  → `model_name = os.getenv("TEST_MODEL_INTEGRATION_MODEL_NAME_291")`
  → 环境变量: `TEST_MODEL_INTEGRATION_MODEL_NAME_291`

- 行 292: `predicted_result="]home["`
  → `predicted_result = os.getenv("TEST_MODEL_INTEGRATION_PREDICTED_RESULT_292")`
  → 环境变量: `TEST_MODEL_INTEGRATION_PREDICTED_RESULT_292`

- 行 311: `season="]2024-25["`
  → `season = os.getenv("TEST_MODEL_INTEGRATION_SEASON_311")`
  → 环境变量: `TEST_MODEL_INTEGRATION_SEASON_311`

- 行 314: `match_status="]scheduled["`
  → `match_status = os.getenv("TEST_MODEL_INTEGRATION_MATCH_STATUS_314")`
  → 环境变量: `TEST_MODEL_INTEGRATION_MATCH_STATUS_314`

- 行 360: `model_name="]test_model["`
  → `model_name = os.getenv("TEST_MODEL_INTEGRATION_MODEL_NAME_360")`
  → 环境变量: `TEST_MODEL_INTEGRATION_MODEL_NAME_360`

- 行 362: `predicted_result="]home_win["`
  → `predicted_result = os.getenv("TEST_MODEL_INTEGRATION_PREDICTED_RESULT_362")`
  → 环境变量: `TEST_MODEL_INTEGRATION_PREDICTED_RESULT_362`

- 行 387: `model_name="]test_model["`
  → `model_name = os.getenv("TEST_MODEL_INTEGRATION_MODEL_NAME_387")`
  → 环境变量: `TEST_MODEL_INTEGRATION_MODEL_NAME_387`

- 行 413: `model_name="]test_model["`
  → `model_name = os.getenv("TEST_MODEL_INTEGRATION_MODEL_NAME_413")`
  → 环境变量: `TEST_MODEL_INTEGRATION_MODEL_NAME_413`

- 行 413: `predicted_result="]home["`
  → `predicted_result = os.getenv("TEST_MODEL_INTEGRATION_PREDICTED_RESULT_413")`
  → 环境变量: `TEST_MODEL_INTEGRATION_PREDICTED_RESULT_413`

- 行 432: `model_name="]performance_test_model["`
  → `model_name = os.getenv("TEST_MODEL_INTEGRATION_MODEL_NAME_432")`
  → 环境变量: `TEST_MODEL_INTEGRATION_MODEL_NAME_432`

- 行 483: `model_name="]test_model["`
  → `model_name = os.getenv("TEST_MODEL_INTEGRATION_MODEL_NAME_483")`
  → 环境变量: `TEST_MODEL_INTEGRATION_MODEL_NAME_483`

- 行 489: `name="]test_model["`
  → `name = os.getenv("TEST_MODEL_INTEGRATION_NAME_489")`
  → 环境变量: `TEST_MODEL_INTEGRATION_NAME_489`

- 行 491: `stage="]Production["`
  → `stage = os.getenv("TEST_MODEL_INTEGRATION_STAGE_491")`
  → 环境变量: `TEST_MODEL_INTEGRATION_STAGE_491`

### tests/legacy/examples/test_example.py

- 行 15: `text = "Hello, World!"`
  → `text = os.getenv("TEST_EXAMPLE_TEXT_15")`
  → 环境变量: `TEST_EXAMPLE_TEXT_15`

### tests/legacy/unit/test_final_coverage_push.py

- 行 34: `test_sql = "SELECT * FROM test WHERE data->>'`
  → `test_sql = os.getenv("TEST_FINAL_COVERAGE_PUSH_TEST_SQL_34")`
  → 环境变量: `TEST_FINAL_COVERAGE_PUSH_TEST_SQL_34`

### tests/legacy/unit/test_analyze_coverage_precise.py

- 行 37: `encoding="utf-8["`
  → `encoding = os.getenv("TEST_ANALYZE_COVERAGE_PRECISE_ENCODING_37")`
  → 环境变量: `TEST_ANALYZE_COVERAGE_PRECISE_ENCODING_37`

- 行 68: `encoding="utf-8["`
  → `encoding = os.getenv("TEST_ANALYZE_COVERAGE_PRECISE_ENCODING_68")`
  → 环境变量: `TEST_ANALYZE_COVERAGE_PRECISE_ENCODING_68`

- 行 143: `return_value="]/home/user/projects/FootballPrediction/src/normal.py["`
  → `return_value = os.getenv("TEST_ANALYZE_COVERAGE_PRECISE_RETURN_VALUE_143")`
  → 环境变量: `TEST_ANALYZE_COVERAGE_PRECISE_RETURN_VALUE_143`

- 行 146: `name="]test.py["`
  → `name = os.getenv("TEST_ANALYZE_COVERAGE_PRECISE_NAME_146")`
  → 环境变量: `TEST_ANALYZE_COVERAGE_PRECISE_NAME_146`

- 行 146: `return_value="]/home/user/projects/FootballPrediction/src/test.py["`
  → `return_value = os.getenv("TEST_ANALYZE_COVERAGE_PRECISE_RETURN_VALUE_146")`
  → 环境变量: `TEST_ANALYZE_COVERAGE_PRECISE_RETURN_VALUE_146`

- 行 146: `name="]__init__.py["`
  → `name = os.getenv("TEST_ANALYZE_COVERAGE_PRECISE_NAME_146")`
  → 环境变量: `TEST_ANALYZE_COVERAGE_PRECISE_NAME_146`

- 行 146: `return_value="]/home/user/projects/FootballPrediction/src/__init__.py["`
  → `return_value = os.getenv("TEST_ANALYZE_COVERAGE_PRECISE_RETURN_VALUE_146")`
  → 环境变量: `TEST_ANALYZE_COVERAGE_PRECISE_RETURN_VALUE_146`

- 行 146: `name="]cache.py["`
  → `name = os.getenv("TEST_ANALYZE_COVERAGE_PRECISE_NAME_146")`
  → 环境变量: `TEST_ANALYZE_COVERAGE_PRECISE_NAME_146`

- 行 146: `return_value="]/home/user/projects/FootballPrediction/__pycache__/cache.py["`
  → `return_value = os.getenv("TEST_ANALYZE_COVERAGE_PRECISE_RETURN_VALUE_146")`
  → 环境变量: `TEST_ANALYZE_COVERAGE_PRECISE_RETURN_VALUE_146`

- 行 186: `stdout = "]]2025-09-27 12:0000["`
  → `stdout = os.getenv("TEST_ANALYZE_COVERAGE_PRECISE_STDOUT_186")`
  → 环境变量: `TEST_ANALYZE_COVERAGE_PRECISE_STDOUT_186`

- 行 205: `stdout = "]]2025-09-27 12:0000["`
  → `stdout = os.getenv("TEST_ANALYZE_COVERAGE_PRECISE_STDOUT_205")`
  → 环境变量: `TEST_ANALYZE_COVERAGE_PRECISE_STDOUT_205`

- 行 229: `stdout = "]]2025-09-27 12:0000["`
  → `stdout = os.getenv("TEST_ANALYZE_COVERAGE_PRECISE_STDOUT_229")`
  → 环境变量: `TEST_ANALYZE_COVERAGE_PRECISE_STDOUT_229`

- 行 241: `rate="]0.75["`
  → `rate = os.getenv("TEST_ANALYZE_COVERAGE_PRECISE_RATE_241")`
  → 环境变量: `TEST_ANALYZE_COVERAGE_PRECISE_RATE_241`

- 行 241: `rate="]0.65["`
  → `rate = os.getenv("TEST_ANALYZE_COVERAGE_PRECISE_RATE_241")`
  → 环境变量: `TEST_ANALYZE_COVERAGE_PRECISE_RATE_241`

- 行 244: `rate="]0.65["`
  → `rate = os.getenv("TEST_ANALYZE_COVERAGE_PRECISE_RATE_244")`
  → 环境变量: `TEST_ANALYZE_COVERAGE_PRECISE_RATE_244`

- 行 246: `name="]test_module,"`
  → `name = os.getenv("TEST_ANALYZE_COVERAGE_PRECISE_NAME_246")`
  → 环境变量: `TEST_ANALYZE_COVERAGE_PRECISE_NAME_246`

- 行 247: `filename="src/test_module.py["`
  → `filename = os.getenv("TEST_ANALYZE_COVERAGE_PRECISE_FILENAME_247")`
  → 环境变量: `TEST_ANALYZE_COVERAGE_PRECISE_FILENAME_247`

- 行 248: `name="]test_function,"`
  → `name = os.getenv("TEST_ANALYZE_COVERAGE_PRECISE_NAME_248")`
  → 环境变量: `TEST_ANALYZE_COVERAGE_PRECISE_NAME_248`

- 行 259: `encoding="utf-8["`
  → `encoding = os.getenv("TEST_ANALYZE_COVERAGE_PRECISE_ENCODING_259")`
  → 环境变量: `TEST_ANALYZE_COVERAGE_PRECISE_ENCODING_259`

- 行 310: `match = "]]Path not relative["`
  → `match = os.getenv("TEST_ANALYZE_COVERAGE_PRECISE_MATCH_310")`
  → 环境变量: `TEST_ANALYZE_COVERAGE_PRECISE_MATCH_310`

### tests/legacy/unit/test_kafka_producer_comprehensive.py

- 行 40: `bootstrap_servers = "custom - server9092["`
  → `bootstrap_servers = os.getenv("TEST_KAFKA_PRODUCER_COMPREHENSIVE_BOOTSTRAP_SERVER")`
  → 环境变量: `TEST_KAFKA_PRODUCER_COMPREHENSIVE_BOOTSTRAP_SERVER`

- 行 71: `test_data = "Simple string message["`
  → `test_data = os.getenv("TEST_KAFKA_PRODUCER_COMPREHENSIVE_TEST_DATA_71")`
  → 环境变量: `TEST_KAFKA_PRODUCER_COMPREHENSIVE_TEST_DATA_71`

- 行 89: `return_value = "test - topic["`
  → `return_value = os.getenv("TEST_KAFKA_PRODUCER_COMPREHENSIVE_RETURN_VALUE_89")`
  → 环境变量: `TEST_KAFKA_PRODUCER_COMPREHENSIVE_RETURN_VALUE_89`

- 行 94: `return_value = "Message delivery failed["`
  → `return_value = os.getenv("TEST_KAFKA_PRODUCER_COMPREHENSIVE_RETURN_VALUE_94")`
  → 环境变量: `TEST_KAFKA_PRODUCER_COMPREHENSIVE_RETURN_VALUE_94`

- 行 123: `custom_key = "]custom_match_key["`
  → `custom_key = os.getenv("TEST_KAFKA_PRODUCER_COMPREHENSIVE_CUSTOM_KEY_123")`
  → 环境变量: `TEST_KAFKA_PRODUCER_COMPREHENSIVE_CUSTOM_KEY_123`

### tests/legacy/unit/test_main_simple.py

- 行 28: `title="足球预测API["`
  → `title = os.getenv("TEST_MAIN_SIMPLE_TITLE_28")`
  → 环境变量: `TEST_MAIN_SIMPLE_TITLE_28`

- 行 28: `description="]基于机器学习的足球比赛结果预测系统["`
  → `description = os.getenv("TEST_MAIN_SIMPLE_DESCRIPTION_28")`
  → 环境变量: `TEST_MAIN_SIMPLE_DESCRIPTION_28`

- 行 28: `version="]1.0.0["`
  → `version = os.getenv("TEST_MAIN_SIMPLE_VERSION_28")`
  → 环境变量: `TEST_MAIN_SIMPLE_VERSION_28`

- 行 28: `docs_url="]_docs["`
  → `docs_url = os.getenv("TEST_MAIN_SIMPLE_DOCS_URL_28")`
  → 环境变量: `TEST_MAIN_SIMPLE_DOCS_URL_28`

- 行 28: `redoc_url="]/redoc["`
  → `redoc_url = os.getenv("TEST_MAIN_SIMPLE_REDOC_URL_28")`
  → 环境变量: `TEST_MAIN_SIMPLE_REDOC_URL_28`

- 行 28: `cors_origins = "http:_/localhost3000["`
  → `cors_origins = os.getenv("TEST_MAIN_SIMPLE_CORS_ORIGINS_28")`
  → 环境变量: `TEST_MAIN_SIMPLE_CORS_ORIGINS_28`

- 行 50: `url = "http_/test.com/api/test["`
  → `url = os.getenv("TEST_MAIN_SIMPLE_URL_50")`
  → 环境变量: `TEST_MAIN_SIMPLE_URL_50`

- 行 54: `detail="]]页面未找到["`
  → `detail = os.getenv("TEST_MAIN_SIMPLE_DETAIL_54")`
  → 环境变量: `TEST_MAIN_SIMPLE_DETAIL_54`

- 行 75: `url = "http_/test.com/api/test["`
  → `url = os.getenv("TEST_MAIN_SIMPLE_URL_75")`
  → 环境变量: `TEST_MAIN_SIMPLE_URL_75`

- 行 156: `match = "]]]数据库连接失败["`
  → `match = os.getenv("TEST_MAIN_SIMPLE_MATCH_156")`
  → 环境变量: `TEST_MAIN_SIMPLE_MATCH_156`

- 行 166: `default_host = "]0.0.0.0["`
  → `default_host = os.getenv("TEST_MAIN_SIMPLE_DEFAULT_HOST_166")`
  → 环境变量: `TEST_MAIN_SIMPLE_DEFAULT_HOST_166`

- 行 167: `default_host = "]127.0.0.1["`
  → `default_host = os.getenv("TEST_MAIN_SIMPLE_DEFAULT_HOST_167")`
  → 环境变量: `TEST_MAIN_SIMPLE_DEFAULT_HOST_167`

- 行 171: `default_host = "]0.0.0.0["`
  → `default_host = os.getenv("TEST_MAIN_SIMPLE_DEFAULT_HOST_171")`
  → 环境变量: `TEST_MAIN_SIMPLE_DEFAULT_HOST_171`

- 行 171: `default_host = "]127.0.0.1["`
  → `default_host = os.getenv("TEST_MAIN_SIMPLE_DEFAULT_HOST_171")`
  → 环境变量: `TEST_MAIN_SIMPLE_DEFAULT_HOST_171`

- 行 183: `prefix="]/api/v1["`
  → `prefix = os.getenv("TEST_MAIN_SIMPLE_PREFIX_183")`
  → 环境变量: `TEST_MAIN_SIMPLE_PREFIX_183`

- 行 236: `format="%(asctime)s - %(name)s - %(levelname)s - %(message)s["`
  → `format = os.getenv("TEST_MAIN_SIMPLE_FORMAT_236")`
  → 环境变量: `TEST_MAIN_SIMPLE_FORMAT_236`

- 行 241: `format="]%(asctime)s - %(name)s - %(levelname)s - %(message)s["`
  → `format = os.getenv("TEST_MAIN_SIMPLE_FORMAT_241")`
  → 环境变量: `TEST_MAIN_SIMPLE_FORMAT_241`

- 行 252: `default_host = "]0.0.0.0["`
  → `default_host = os.getenv("TEST_MAIN_SIMPLE_DEFAULT_HOST_252")`
  → 环境变量: `TEST_MAIN_SIMPLE_DEFAULT_HOST_252`

- 行 254: `default_host = "]127.0.0.1["`
  → `default_host = os.getenv("TEST_MAIN_SIMPLE_DEFAULT_HOST_254")`
  → 环境变量: `TEST_MAIN_SIMPLE_DEFAULT_HOST_254`

- 行 262: `default_host = "]0.0.0.0["`
  → `default_host = os.getenv("TEST_MAIN_SIMPLE_DEFAULT_HOST_262")`
  → 环境变量: `TEST_MAIN_SIMPLE_DEFAULT_HOST_262`

- 行 262: `default_host = "]127.0.0.1["`
  → `default_host = os.getenv("TEST_MAIN_SIMPLE_DEFAULT_HOST_262")`
  → 环境变量: `TEST_MAIN_SIMPLE_DEFAULT_HOST_262`

### tests/legacy/unit/test_data_lake_storage_phase4.py

- 行 14: `logger="]]storage.DataLakeStorage["`
  → `logger = os.getenv("TEST_DATA_LAKE_STORAGE_PHASE4_LOGGER_14")`
  → 环境变量: `TEST_DATA_LAKE_STORAGE_PHASE4_LOGGER_14`

### tests/legacy/unit/test_extract_coverage.py

- 行 195: `stdout = "]2025-09-27 12:00:00["`
  → `stdout = os.getenv("TEST_EXTRACT_COVERAGE_STDOUT_195")`
  → 环境变量: `TEST_EXTRACT_COVERAGE_STDOUT_195`

- 行 217: `stdout = "]2025-09-27 12:00:00["`
  → `stdout = os.getenv("TEST_EXTRACT_COVERAGE_STDOUT_217")`
  → 环境变量: `TEST_EXTRACT_COVERAGE_STDOUT_217`

- 行 239: `stdout = "]2025-09-27 12:00:00["`
  → `stdout = os.getenv("TEST_EXTRACT_COVERAGE_STDOUT_239")`
  → 环境变量: `TEST_EXTRACT_COVERAGE_STDOUT_239`

- 行 261: `stdout = "]2025-09-27 12:00:00["`
  → `stdout = os.getenv("TEST_EXTRACT_COVERAGE_STDOUT_261")`
  → 环境变量: `TEST_EXTRACT_COVERAGE_STDOUT_261`

- 行 333: `match="]Path not relative["`
  → `match = os.getenv("TEST_EXTRACT_COVERAGE_MATCH_333")`
  → 环境变量: `TEST_EXTRACT_COVERAGE_MATCH_333`

### tests/legacy/unit/test_football_data_cleaner_batch_delta_002.py

- 行 248: `invalid_time = "invalid-time-format["`
  → `invalid_time = os.getenv("TEST_FOOTBALL_DATA_CLEANER_BATCH_DELTA_002_INVALID")`
  → 环境变量: `TEST_FOOTBALL_DATA_CLEANER_BATCH_DELTA_002_INVALID`

### tests/legacy/unit/test_main.py

- 行 26: `title="足球预测API["`
  → `title = os.getenv("TEST_MAIN_TITLE_26")`
  → 环境变量: `TEST_MAIN_TITLE_26`

- 行 26: `description="]基于机器学习的足球比赛结果预测系统["`
  → `description = os.getenv("TEST_MAIN_DESCRIPTION_26")`
  → 环境变量: `TEST_MAIN_DESCRIPTION_26`

- 行 26: `version="]1.0.0["`
  → `version = os.getenv("TEST_MAIN_VERSION_26")`
  → 环境变量: `TEST_MAIN_VERSION_26`

- 行 26: `docs_url="]/docs["`
  → `docs_url = os.getenv("TEST_MAIN_DOCS_URL_26")`
  → 环境变量: `TEST_MAIN_DOCS_URL_26`

- 行 26: `redoc_url="]/redoc["`
  → `redoc_url = os.getenv("TEST_MAIN_REDOC_URL_26")`
  → 环境变量: `TEST_MAIN_REDOC_URL_26`

- 行 52: `description="]服务状态["`
  → `description = os.getenv("TEST_MAIN_DESCRIPTION_52")`
  → 环境变量: `TEST_MAIN_DESCRIPTION_52`

- 行 52: `description="]API文档地址["`
  → `description = os.getenv("TEST_MAIN_DESCRIPTION_52")`
  → 环境变量: `TEST_MAIN_DESCRIPTION_52`

- 行 52: `description="]健康检查地址["`
  → `description = os.getenv("TEST_MAIN_DESCRIPTION_52")`
  → 环境变量: `TEST_MAIN_DESCRIPTION_52`

- 行 66: `url = "http_/test.com/api/test["`
  → `url = os.getenv("TEST_MAIN_URL_66")`
  → 环境变量: `TEST_MAIN_URL_66`

- 行 70: `detail="]页面未找到["`
  → `detail = os.getenv("TEST_MAIN_DETAIL_70")`
  → 环境变量: `TEST_MAIN_DETAIL_70`

- 行 93: `url = "http_/test.com/api/test["`
  → `url = os.getenv("TEST_MAIN_URL_93")`
  → 环境变量: `TEST_MAIN_URL_93`

- 行 161: `match = "]]]数据库连接失败["`
  → `match = os.getenv("TEST_MAIN_MATCH_161")`
  → 环境变量: `TEST_MAIN_MATCH_161`

- 行 193: `format="]%(asctime)s - %(name)s - %(levelname)s - %(message)s["`
  → `format = os.getenv("TEST_MAIN_FORMAT_193")`
  → 环境变量: `TEST_MAIN_FORMAT_193`

- 行 198: `format="]%(asctime)s - %(name)s - %(levelname)s - %(message)s["`
  → `format = os.getenv("TEST_MAIN_FORMAT_198")`
  → 环境变量: `TEST_MAIN_FORMAT_198`

- 行 207: `default_host = "]0.0.0.0["`
  → `default_host = os.getenv("TEST_MAIN_DEFAULT_HOST_207")`
  → 环境变量: `TEST_MAIN_DEFAULT_HOST_207`

- 行 208: `default_host = "]127.0.0.1["`
  → `default_host = os.getenv("TEST_MAIN_DEFAULT_HOST_208")`
  → 环境变量: `TEST_MAIN_DEFAULT_HOST_208`

- 行 209: `default_host = "]0.0.0.0["`
  → `default_host = os.getenv("TEST_MAIN_DEFAULT_HOST_209")`
  → 环境变量: `TEST_MAIN_DEFAULT_HOST_209`

- 行 209: `default_host = "]127.0.0.1["`
  → `default_host = os.getenv("TEST_MAIN_DEFAULT_HOST_209")`
  → 环境变量: `TEST_MAIN_DEFAULT_HOST_209`

- 行 264: `default_host = "]0.0.0.0["`
  → `default_host = os.getenv("TEST_MAIN_DEFAULT_HOST_264")`
  → 环境变量: `TEST_MAIN_DEFAULT_HOST_264`

- 行 265: `default_host = "]127.0.0.1["`
  → `default_host = os.getenv("TEST_MAIN_DEFAULT_HOST_265")`
  → 环境变量: `TEST_MAIN_DEFAULT_HOST_265`

- 行 270: `default_host = "]0.0.0.0["`
  → `default_host = os.getenv("TEST_MAIN_DEFAULT_HOST_270")`
  → 环境变量: `TEST_MAIN_DEFAULT_HOST_270`

- 行 270: `default_host = "]127.0.0.1["`
  → `default_host = os.getenv("TEST_MAIN_DEFAULT_HOST_270")`
  → 环境变量: `TEST_MAIN_DEFAULT_HOST_270`

### tests/legacy/unit/test_data_lake_storage_batch_delta_001.py

- 行 59: `return_value = '_test/dir'`
  → `return_value = os.getenv("TEST_DATA_LAKE_STORAGE_BATCH_DELTA_001_RETURN_VALU")`
  → 环境变量: `TEST_DATA_LAKE_STORAGE_BATCH_DELTA_001_RETURN_VALU`

- 行 107: `table_name="raw_matches["`
  → `table_name = os.getenv("TEST_DATA_LAKE_STORAGE_BATCH_DELTA_001_TABLE_NAME_")`
  → 环境变量: `TEST_DATA_LAKE_STORAGE_BATCH_DELTA_001_TABLE_NAME_`

- 行 126: `table_name="raw_matches["`
  → `table_name = os.getenv("TEST_DATA_LAKE_STORAGE_BATCH_DELTA_001_TABLE_NAME_")`
  → 环境变量: `TEST_DATA_LAKE_STORAGE_BATCH_DELTA_001_TABLE_NAME_`

- 行 138: `table_name="invalid_table["`
  → `table_name = os.getenv("TEST_DATA_LAKE_STORAGE_BATCH_DELTA_001_TABLE_NAME_")`
  → 环境变量: `TEST_DATA_LAKE_STORAGE_BATCH_DELTA_001_TABLE_NAME_`

- 行 144: `table_name="raw_matches["`
  → `table_name = os.getenv("TEST_DATA_LAKE_STORAGE_BATCH_DELTA_001_TABLE_NAME_")`
  → 环境变量: `TEST_DATA_LAKE_STORAGE_BATCH_DELTA_001_TABLE_NAME_`

- 行 156: `table_name="raw_matches["`
  → `table_name = os.getenv("TEST_DATA_LAKE_STORAGE_BATCH_DELTA_001_TABLE_NAME_")`
  → 环境变量: `TEST_DATA_LAKE_STORAGE_BATCH_DELTA_001_TABLE_NAME_`

- 行 171: `table_name="invalid_table["`
  → `table_name = os.getenv("TEST_DATA_LAKE_STORAGE_BATCH_DELTA_001_TABLE_NAME_")`
  → 环境变量: `TEST_DATA_LAKE_STORAGE_BATCH_DELTA_001_TABLE_NAME_`

- 行 187: `table_name="raw_matches["`
  → `table_name = os.getenv("TEST_DATA_LAKE_STORAGE_BATCH_DELTA_001_TABLE_NAME_")`
  → 环境变量: `TEST_DATA_LAKE_STORAGE_BATCH_DELTA_001_TABLE_NAME_`

- 行 205: `table_name="raw_matches["`
  → `table_name = os.getenv("TEST_DATA_LAKE_STORAGE_BATCH_DELTA_001_TABLE_NAME_")`
  → 环境变量: `TEST_DATA_LAKE_STORAGE_BATCH_DELTA_001_TABLE_NAME_`

- 行 225: `table_name="raw_matches["`
  → `table_name = os.getenv("TEST_DATA_LAKE_STORAGE_BATCH_DELTA_001_TABLE_NAME_")`
  → 环境变量: `TEST_DATA_LAKE_STORAGE_BATCH_DELTA_001_TABLE_NAME_`

- 行 290: `table_name="raw_matches["`
  → `table_name = os.getenv("TEST_DATA_LAKE_STORAGE_BATCH_DELTA_001_TABLE_NAME_")`
  → 环境变量: `TEST_DATA_LAKE_STORAGE_BATCH_DELTA_001_TABLE_NAME_`

### tests/legacy/unit/test_celery_app_comprehensive.py

- 行 66: `queue="test_queue["`
  → `queue = os.getenv("TEST_CELERY_APP_COMPREHENSIVE_QUEUE_66")`
  → 环境变量: `TEST_CELERY_APP_COMPREHENSIVE_QUEUE_66`

### tests/legacy/unit/test_dict_utils.py

- 行 8: `be = "]retries["`
  → `be = os.getenv("TEST_DICT_UTILS_BE_8")`
  → 环境变量: `TEST_DICT_UTILS_BE_8`

- 行 35: `be = "]email["`
  → `be = os.getenv("TEST_DICT_UTILS_BE_35")`
  → 环境变量: `TEST_DICT_UTILS_BE_35`

### tests/legacy/unit/services_data_processing_batch_gamma_.py

- 行 227: `text = "Team A vs Team B 2-1["`
  → `text = os.getenv("SERVICES_DATA_PROCESSING_BATCH_GAMMA__TEXT_227")`
  → 环境变量: `SERVICES_DATA_PROCESSING_BATCH_GAMMA__TEXT_227`

- 行 311: `cache_key = "test_cache_key["`
  → `cache_key = os.getenv("SERVICES_DATA_PROCESSING_BATCH_GAMMA__CACHE_KEY_31")`
  → 环境变量: `SERVICES_DATA_PROCESSING_BATCH_GAMMA__CACHE_KEY_31`

- 行 320: `cache_key = "test_cache_key["`
  → `cache_key = os.getenv("SERVICES_DATA_PROCESSING_BATCH_GAMMA__CACHE_KEY_32")`
  → 环境变量: `SERVICES_DATA_PROCESSING_BATCH_GAMMA__CACHE_KEY_32`

- 行 328: `cache_key = "nonexistent_key["`
  → `cache_key = os.getenv("SERVICES_DATA_PROCESSING_BATCH_GAMMA__CACHE_KEY_32")`
  → 环境变量: `SERVICES_DATA_PROCESSING_BATCH_GAMMA__CACHE_KEY_32`

### tests/legacy/unit/test_data_collectors.py

- 行 20: `data_source="test_api["`
  → `data_source = os.getenv("TEST_DATA_COLLECTORS_DATA_SOURCE_20")`
  → 环境变量: `TEST_DATA_COLLECTORS_DATA_SOURCE_20`

- 行 20: `collection_type="]fixtures["`
  → `collection_type = os.getenv("TEST_DATA_COLLECTORS_COLLECTION_TYPE_20")`
  → 环境变量: `TEST_DATA_COLLECTORS_COLLECTION_TYPE_20`

- 行 20: `status="]partial["`
  → `status = os.getenv("TEST_DATA_COLLECTORS_STATUS_20")`
  → 环境变量: `TEST_DATA_COLLECTORS_STATUS_20`

- 行 20: `error_message="]Some records failed["`
  → `error_message = os.getenv("TEST_DATA_COLLECTORS_ERROR_MESSAGE_20")`
  → 环境变量: `TEST_DATA_COLLECTORS_ERROR_MESSAGE_20`

- 行 24: `data_source="football_api["`
  → `data_source = os.getenv("TEST_DATA_COLLECTORS_DATA_SOURCE_24")`
  → 环境变量: `TEST_DATA_COLLECTORS_DATA_SOURCE_24`

- 行 25: `collection_type="]odds["`
  → `collection_type = os.getenv("TEST_DATA_COLLECTORS_COLLECTION_TYPE_25")`
  → 环境变量: `TEST_DATA_COLLECTORS_COLLECTION_TYPE_25`

- 行 27: `status="]success["`
  → `status = os.getenv("TEST_DATA_COLLECTORS_STATUS_27")`
  → 环境变量: `TEST_DATA_COLLECTORS_STATUS_27`

- 行 29: `data_source="football_api["`
  → `data_source = os.getenv("TEST_DATA_COLLECTORS_DATA_SOURCE_29")`
  → 环境变量: `TEST_DATA_COLLECTORS_DATA_SOURCE_29`

- 行 29: `collection_type="]live_scores["`
  → `collection_type = os.getenv("TEST_DATA_COLLECTORS_COLLECTION_TYPE_29")`
  → 环境变量: `TEST_DATA_COLLECTORS_COLLECTION_TYPE_29`

- 行 30: `status="]failed["`
  → `status = os.getenv("TEST_DATA_COLLECTORS_STATUS_30")`
  → 环境变量: `TEST_DATA_COLLECTORS_STATUS_30`

- 行 31: `error_message="]API connection timeout["`
  → `error_message = os.getenv("TEST_DATA_COLLECTORS_ERROR_MESSAGE_31")`
  → 环境变量: `TEST_DATA_COLLECTORS_ERROR_MESSAGE_31`

- 行 35: `collection_type="fixtures["`
  → `collection_type = os.getenv("TEST_DATA_COLLECTORS_COLLECTION_TYPE_35")`
  → 环境变量: `TEST_DATA_COLLECTORS_COLLECTION_TYPE_35`

- 行 35: `status="]success["`
  → `status = os.getenv("TEST_DATA_COLLECTORS_STATUS_35")`
  → 环境变量: `TEST_DATA_COLLECTORS_STATUS_35`

- 行 42: `status="]success["`
  → `status = os.getenv("TEST_DATA_COLLECTORS_STATUS_42")`
  → 环境变量: `TEST_DATA_COLLECTORS_STATUS_42`

- 行 48: `collection_type="live_scores["`
  → `collection_type = os.getenv("TEST_DATA_COLLECTORS_COLLECTION_TYPE_48")`
  → 环境变量: `TEST_DATA_COLLECTORS_COLLECTION_TYPE_48`

- 行 49: `status="]success["`
  → `status = os.getenv("TEST_DATA_COLLECTORS_STATUS_49")`
  → 环境变量: `TEST_DATA_COLLECTORS_STATUS_49`

- 行 53: `data_source="]test_api["`
  → `data_source = os.getenv("TEST_DATA_COLLECTORS_DATA_SOURCE_53")`
  → 环境变量: `TEST_DATA_COLLECTORS_DATA_SOURCE_53`

- 行 102: `collection_type="]odds["`
  → `collection_type = os.getenv("TEST_DATA_COLLECTORS_COLLECTION_TYPE_102")`
  → 环境变量: `TEST_DATA_COLLECTORS_COLLECTION_TYPE_102`

- 行 104: `status="]failed["`
  → `status = os.getenv("TEST_DATA_COLLECTORS_STATUS_104")`
  → 环境变量: `TEST_DATA_COLLECTORS_STATUS_104`

- 行 105: `error_message="]Invalid API response["`
  → `error_message = os.getenv("TEST_DATA_COLLECTORS_ERROR_MESSAGE_105")`
  → 环境变量: `TEST_DATA_COLLECTORS_ERROR_MESSAGE_105`

- 行 109: `collection_type="]live_scores["`
  → `collection_type = os.getenv("TEST_DATA_COLLECTORS_COLLECTION_TYPE_109")`
  → 环境变量: `TEST_DATA_COLLECTORS_COLLECTION_TYPE_109`

- 行 112: `status="]success["`
  → `status = os.getenv("TEST_DATA_COLLECTORS_STATUS_112")`
  → 环境变量: `TEST_DATA_COLLECTORS_STATUS_112`

- 行 113: `data_source="]error_api["`
  → `data_source = os.getenv("TEST_DATA_COLLECTORS_DATA_SOURCE_113")`
  → 环境变量: `TEST_DATA_COLLECTORS_DATA_SOURCE_113`

- 行 121: `data_source="empty_api["`
  → `data_source = os.getenv("TEST_DATA_COLLECTORS_DATA_SOURCE_121")`
  → 环境变量: `TEST_DATA_COLLECTORS_DATA_SOURCE_121`

- 行 122: `collection_type="]fixtures["`
  → `collection_type = os.getenv("TEST_DATA_COLLECTORS_COLLECTION_TYPE_122")`
  → 环境变量: `TEST_DATA_COLLECTORS_COLLECTION_TYPE_122`

- 行 124: `status="]success["`
  → `status = os.getenv("TEST_DATA_COLLECTORS_STATUS_124")`
  → 环境变量: `TEST_DATA_COLLECTORS_STATUS_124`

- 行 129: `data_source="minimal_api["`
  → `data_source = os.getenv("TEST_DATA_COLLECTORS_DATA_SOURCE_129")`
  → 环境变量: `TEST_DATA_COLLECTORS_DATA_SOURCE_129`

- 行 129: `collection_type="]odds["`
  → `collection_type = os.getenv("TEST_DATA_COLLECTORS_COLLECTION_TYPE_129")`
  → 环境变量: `TEST_DATA_COLLECTORS_COLLECTION_TYPE_129`

- 行 131: `status="]success["`
  → `status = os.getenv("TEST_DATA_COLLECTORS_STATUS_131")`
  → 环境变量: `TEST_DATA_COLLECTORS_STATUS_131`

- 行 137: `data_source="]custom_api["`
  → `data_source = os.getenv("TEST_DATA_COLLECTORS_DATA_SOURCE_137")`
  → 环境变量: `TEST_DATA_COLLECTORS_DATA_SOURCE_137`

### tests/legacy/unit/test_time_utils.py

- 行 49: `date_str = "2025_01/01 1230["`
  → `date_str = os.getenv("TEST_TIME_UTILS_DATE_STR_49")`
  → 环境变量: `TEST_TIME_UTILS_DATE_STR_49`

### tests/legacy/unit/test_data_collection_tasks_comprehensive.py

- 行 63: `status="success["`
  → `status = os.getenv("TEST_DATA_COLLECTION_TASKS_COMPREHENSIVE_STATUS_63")`
  → 环境变量: `TEST_DATA_COLLECTION_TASKS_COMPREHENSIVE_STATUS_63`

- 行 63: `data_source="]test["`
  → `data_source = os.getenv("TEST_DATA_COLLECTION_TASKS_COMPREHENSIVE_DATA_SOUR")`
  → 环境变量: `TEST_DATA_COLLECTION_TASKS_COMPREHENSIVE_DATA_SOUR`

- 行 63: `collection_type="]odds["`
  → `collection_type = os.getenv("TEST_DATA_COLLECTION_TASKS_COMPREHENSIVE_COLLECTIO")`
  → 环境变量: `TEST_DATA_COLLECTION_TASKS_COMPREHENSIVE_COLLECTIO`

- 行 64: `bookmaker="]]bet365["`
  → `bookmaker = os.getenv("TEST_DATA_COLLECTION_TASKS_COMPREHENSIVE_BOOKMAKER")`
  → 环境变量: `TEST_DATA_COLLECTION_TASKS_COMPREHENSIVE_BOOKMAKER`

- 行 68: `match_ids="]12345["`
  → `match_ids = os.getenv("TEST_DATA_COLLECTION_TASKS_COMPREHENSIVE_MATCH_IDS")`
  → 环境变量: `TEST_DATA_COLLECTION_TASKS_COMPREHENSIVE_MATCH_IDS`

- 行 68: `bookmakers="]bet365["`
  → `bookmakers = os.getenv("TEST_DATA_COLLECTION_TASKS_COMPREHENSIVE_BOOKMAKER")`
  → 环境变量: `TEST_DATA_COLLECTION_TASKS_COMPREHENSIVE_BOOKMAKER`

- 行 72: `status="success["`
  → `status = os.getenv("TEST_DATA_COLLECTION_TASKS_COMPREHENSIVE_STATUS_72")`
  → 环境变量: `TEST_DATA_COLLECTION_TASKS_COMPREHENSIVE_STATUS_72`

- 行 74: `data_source="]test["`
  → `data_source = os.getenv("TEST_DATA_COLLECTION_TASKS_COMPREHENSIVE_DATA_SOUR")`
  → 环境变量: `TEST_DATA_COLLECTION_TASKS_COMPREHENSIVE_DATA_SOUR`

- 行 74: `collection_type="]scores["`
  → `collection_type = os.getenv("TEST_DATA_COLLECTION_TASKS_COMPREHENSIVE_COLLECTIO")`
  → 环境变量: `TEST_DATA_COLLECTION_TASKS_COMPREHENSIVE_COLLECTIO`

- 行 79: `match_ids="]12345["`
  → `match_ids = os.getenv("TEST_DATA_COLLECTION_TASKS_COMPREHENSIVE_MATCH_IDS")`
  → 环境变量: `TEST_DATA_COLLECTION_TASKS_COMPREHENSIVE_MATCH_IDS`

- 行 80: `status="success["`
  → `status = os.getenv("TEST_DATA_COLLECTION_TASKS_COMPREHENSIVE_STATUS_80")`
  → 环境变量: `TEST_DATA_COLLECTION_TASKS_COMPREHENSIVE_STATUS_80`

- 行 81: `data_source="]test["`
  → `data_source = os.getenv("TEST_DATA_COLLECTION_TASKS_COMPREHENSIVE_DATA_SOUR")`
  → 环境变量: `TEST_DATA_COLLECTION_TASKS_COMPREHENSIVE_DATA_SOUR`

- 行 81: `collection_type="]live_scores["`
  → `collection_type = os.getenv("TEST_DATA_COLLECTION_TASKS_COMPREHENSIVE_COLLECTIO")`
  → 环境变量: `TEST_DATA_COLLECTION_TASKS_COMPREHENSIVE_COLLECTIO`

- 行 85: `match_ids="]12345["`
  → `match_ids = os.getenv("TEST_DATA_COLLECTION_TASKS_COMPREHENSIVE_MATCH_IDS")`
  → 环境变量: `TEST_DATA_COLLECTION_TASKS_COMPREHENSIVE_MATCH_IDS`

- 行 89: `id="fixtures_task_id["`
  → `id = os.getenv("TEST_DATA_COLLECTION_TASKS_COMPREHENSIVE_ID_89")`
  → 环境变量: `TEST_DATA_COLLECTION_TASKS_COMPREHENSIVE_ID_89`

- 行 89: `id="]odds_task_id["`
  → `id = os.getenv("TEST_DATA_COLLECTION_TASKS_COMPREHENSIVE_ID_89")`
  → 环境变量: `TEST_DATA_COLLECTION_TASKS_COMPREHENSIVE_ID_89`

- 行 89: `id="]scores_task_id["`
  → `id = os.getenv("TEST_DATA_COLLECTION_TASKS_COMPREHENSIVE_ID_89")`
  → 环境变量: `TEST_DATA_COLLECTION_TASKS_COMPREHENSIVE_ID_89`

- 行 114: `id="emergency_fixtures["`
  → `id = os.getenv("TEST_DATA_COLLECTION_TASKS_COMPREHENSIVE_ID_114")`
  → 环境变量: `TEST_DATA_COLLECTION_TASKS_COMPREHENSIVE_ID_114`

- 行 115: `id="]emergency_odds["`
  → `id = os.getenv("TEST_DATA_COLLECTION_TASKS_COMPREHENSIVE_ID_115")`
  → 环境变量: `TEST_DATA_COLLECTION_TASKS_COMPREHENSIVE_ID_115`

- 行 115: `id="]emergency_scores["`
  → `id = os.getenv("TEST_DATA_COLLECTION_TASKS_COMPREHENSIVE_ID_115")`
  → 环境变量: `TEST_DATA_COLLECTION_TASKS_COMPREHENSIVE_ID_115`

- 行 129: `match = "]Network timeout["`
  → `match = os.getenv("TEST_DATA_COLLECTION_TASKS_COMPREHENSIVE_MATCH_129")`
  → 环境变量: `TEST_DATA_COLLECTION_TASKS_COMPREHENSIVE_MATCH_129`

- 行 137: `match = "]Request timeout["`
  → `match = os.getenv("TEST_DATA_COLLECTION_TASKS_COMPREHENSIVE_MATCH_137")`
  → 环境变量: `TEST_DATA_COLLECTION_TASKS_COMPREHENSIVE_MATCH_137`

- 行 148: `match = "]Celery retry["`
  → `match = os.getenv("TEST_DATA_COLLECTION_TASKS_COMPREHENSIVE_MATCH_148")`
  → 环境变量: `TEST_DATA_COLLECTION_TASKS_COMPREHENSIVE_MATCH_148`

- 行 155: `match = "]]Invalid match_id["`
  → `match = os.getenv("TEST_DATA_COLLECTION_TASKS_COMPREHENSIVE_MATCH_155")`
  → 环境变量: `TEST_DATA_COLLECTION_TASKS_COMPREHENSIVE_MATCH_155`

- 行 155: `match_id="]invalid["`
  → `match_id = os.getenv("TEST_DATA_COLLECTION_TASKS_COMPREHENSIVE_MATCH_ID_")`
  → 环境变量: `TEST_DATA_COLLECTION_TASKS_COMPREHENSIVE_MATCH_ID_`

- 行 164: `match = "]Celery retry["`
  → `match = os.getenv("TEST_DATA_COLLECTION_TASKS_COMPREHENSIVE_MATCH_164")`
  → 环境变量: `TEST_DATA_COLLECTION_TASKS_COMPREHENSIVE_MATCH_164`

- 行 258: `leagues="]]]epl["`
  → `leagues = os.getenv("TEST_DATA_COLLECTION_TASKS_COMPREHENSIVE_LEAGUES_2")`
  → 环境变量: `TEST_DATA_COLLECTION_TASKS_COMPREHENSIVE_LEAGUES_2`

### tests/legacy/unit/test_crypto_utils.py

- 行 71: `test_string = "Hello, World!"`
  → `test_string = os.getenv("TEST_CRYPTO_UTILS_TEST_STRING_71")`
  → 环境变量: `TEST_CRYPTO_UTILS_TEST_STRING_71`

- 行 76: `test_string = "你好，世界！🌍"`
  → `test_string = os.getenv("TEST_CRYPTO_UTILS_TEST_STRING_76")`
  → 环境变量: `TEST_CRYPTO_UTILS_TEST_STRING_76`

- 行 81: `test_string = "consistency test["`
  → `test_string = os.getenv("TEST_CRYPTO_UTILS_TEST_STRING_81")`
  → 环境变量: `TEST_CRYPTO_UTILS_TEST_STRING_81`

- 行 83: `test_string = "Hello, SHA256!"`
  → `test_string = os.getenv("TEST_CRYPTO_UTILS_TEST_STRING_83")`
  → 环境变量: `TEST_CRYPTO_UTILS_TEST_STRING_83`

- 行 86: `test_string = "测试SHA256 🔐"`
  → `test_string = os.getenv("TEST_CRYPTO_UTILS_TEST_STRING_86")`
  → 环境变量: `TEST_CRYPTO_UTILS_TEST_STRING_86`

- 行 89: `match = "不支持的哈希算法["`
  → `match = os.getenv("TEST_CRYPTO_UTILS_MATCH_89")`
  → 环境变量: `TEST_CRYPTO_UTILS_MATCH_89`

- 行 91: `password = "test_password_123["`
  → `password = os.getenv("TEST_CRYPTO_UTILS_PASSWORD_91")`
  → 环境变量: `TEST_CRYPTO_UTILS_PASSWORD_91`

- 行 116: `password = "test_password_123["`
  → `password = os.getenv("TEST_CRYPTO_UTILS_PASSWORD_116")`
  → 环境变量: `TEST_CRYPTO_UTILS_PASSWORD_116`

- 行 123: `password = "密码测试123 🔑"`
  → `password = os.getenv("TEST_CRYPTO_UTILS_PASSWORD_123")`
  → 环境变量: `TEST_CRYPTO_UTILS_PASSWORD_123`

- 行 130: `password = "verify_test_123["`
  → `password = os.getenv("TEST_CRYPTO_UTILS_PASSWORD_130")`
  → 环境变量: `TEST_CRYPTO_UTILS_PASSWORD_130`

- 行 151: `password = "verify_test_fallback["`
  → `password = os.getenv("TEST_CRYPTO_UTILS_PASSWORD_151")`
  → 环境变量: `TEST_CRYPTO_UTILS_PASSWORD_151`

- 行 164: `password = "test_password["`
  → `password = os.getenv("TEST_CRYPTO_UTILS_PASSWORD_164")`
  → 环境变量: `TEST_CRYPTO_UTILS_PASSWORD_164`

- 行 165: `invalid_hash = "]not_a_valid_hash["`
  → `invalid_hash = os.getenv("TEST_CRYPTO_UTILS_INVALID_HASH_165")`
  → 环境变量: `TEST_CRYPTO_UTILS_INVALID_HASH_165`

### tests/legacy/unit/test_model_training.py

- 行 20: `mlflow_tracking_uri = "]sqlite///test.db["`
  → `mlflow_tracking_uri = os.getenv("TEST_MODEL_TRAINING_MLFLOW_TRACKING_URI_20")`
  → 环境变量: `TEST_MODEL_TRAINING_MLFLOW_TRACKING_URI_20`

### tests/legacy/unit/test_anomaly_detector_batch_delta_004.py

- 行 72: `table_name="test_table["`
  → `table_name = os.getenv("TEST_ANOMALY_DETECTOR_BATCH_DELTA_004_TABLE_NAME_7")`
  → 环境变量: `TEST_ANOMALY_DETECTOR_BATCH_DELTA_004_TABLE_NAME_7`

- 行 72: `detection_method="]3sigma["`
  → `detection_method = os.getenv("TEST_ANOMALY_DETECTOR_BATCH_DELTA_004_DETECTION_ME")`
  → 环境变量: `TEST_ANOMALY_DETECTOR_BATCH_DELTA_004_DETECTION_ME`

- 行 72: `anomaly_type="]statistical_outlier["`
  → `anomaly_type = os.getenv("TEST_ANOMALY_DETECTOR_BATCH_DELTA_004_ANOMALY_TYPE")`
  → 环境变量: `TEST_ANOMALY_DETECTOR_BATCH_DELTA_004_ANOMALY_TYPE`

- 行 72: `severity="]medium["`
  → `severity = os.getenv("TEST_ANOMALY_DETECTOR_BATCH_DELTA_004_SEVERITY_72")`
  → 环境变量: `TEST_ANOMALY_DETECTOR_BATCH_DELTA_004_SEVERITY_72`

- 行 116: `match = "输入数据为空["`
  → `match = os.getenv("TEST_ANOMALY_DETECTOR_BATCH_DELTA_004_MATCH_116")`
  → 环境变量: `TEST_ANOMALY_DETECTOR_BATCH_DELTA_004_MATCH_116`

- 行 211: `match = "]没有可用的数值列进行异常检测["`
  → `match = os.getenv("TEST_ANOMALY_DETECTOR_BATCH_DELTA_004_MATCH_211")`
  → 环境变量: `TEST_ANOMALY_DETECTOR_BATCH_DELTA_004_MATCH_211`

- 行 326: `match = "]没有可用的数值列进行聚类异常检测["`
  → `match = os.getenv("TEST_ANOMALY_DETECTOR_BATCH_DELTA_004_MATCH_326")`
  → 环境变量: `TEST_ANOMALY_DETECTOR_BATCH_DELTA_004_MATCH_326`

### tests/legacy/unit/test_utils_comprehensive.py

- 行 25: `password = "test_password_123["`
  → `password = os.getenv("TEST_UTILS_COMPREHENSIVE_PASSWORD_25")`
  → 环境变量: `TEST_UTILS_COMPREHENSIVE_PASSWORD_25`

- 行 29: `password = "test_password_123["`
  → `password = os.getenv("TEST_UTILS_COMPREHENSIVE_PASSWORD_29")`
  → 环境变量: `TEST_UTILS_COMPREHENSIVE_PASSWORD_29`

- 行 30: `wrong_password = "]wrong_password["`
  → `wrong_password = os.getenv("TEST_UTILS_COMPREHENSIVE_WRONG_PASSWORD_30")`
  → 环境变量: `TEST_UTILS_COMPREHENSIVE_WRONG_PASSWORD_30`

- 行 76: `test_content = "]Hello, World!"`
  → `test_content = os.getenv("TEST_UTILS_COMPREHENSIVE_TEST_CONTENT_76")`
  → 环境变量: `TEST_UTILS_COMPREHENSIVE_TEST_CONTENT_76`

- 行 112: `message="]操作成功["`
  → `message = os.getenv("TEST_UTILS_COMPREHENSIVE_MESSAGE_112")`
  → 环境变量: `TEST_UTILS_COMPREHENSIVE_MESSAGE_112`

- 行 132: `message="]]错误信息["`
  → `message = os.getenv("TEST_UTILS_COMPREHENSIVE_MESSAGE_132")`
  → 环境变量: `TEST_UTILS_COMPREHENSIVE_MESSAGE_132`

### tests/legacy/unit/test_debt_tracker.py

- 行 178: `encoding = "]utf-8["`
  → `encoding = os.getenv("TEST_DEBT_TRACKER_ENCODING_178")`
  → 环境变量: `TEST_DEBT_TRACKER_ENCODING_178`

- 行 231: `encoding = "]utf-8["`
  → `encoding = os.getenv("TEST_DEBT_TRACKER_ENCODING_231")`
  → 环境变量: `TEST_DEBT_TRACKER_ENCODING_231`

- 行 385: `encoding = "]utf-8["`
  → `encoding = os.getenv("TEST_DEBT_TRACKER_ENCODING_385")`
  → 环境变量: `TEST_DEBT_TRACKER_ENCODING_385`

- 行 438: `encoding = "]utf-8["`
  → `encoding = os.getenv("TEST_DEBT_TRACKER_ENCODING_438")`
  → 环境变量: `TEST_DEBT_TRACKER_ENCODING_438`

- 行 519: `encoding = "]utf-8["`
  → `encoding = os.getenv("TEST_DEBT_TRACKER_ENCODING_519")`
  → 环境变量: `TEST_DEBT_TRACKER_ENCODING_519`

### tests/legacy/unit/test_utils.py

- 行 20: `message="]Success])"`
  → `message = os.getenv("TEST_UTILS_MESSAGE_20")`
  → 环境变量: `TEST_UTILS_MESSAGE_20`

- 行 23: `message="Error occurred["`
  → `message = os.getenv("TEST_UTILS_MESSAGE_23")`
  → 环境变量: `TEST_UTILS_MESSAGE_23`

- 行 26: `message="Success["`
  → `message = os.getenv("TEST_UTILS_MESSAGE_26")`
  → 环境变量: `TEST_UTILS_MESSAGE_26`

- 行 49: `long_string = "This is a very long string that needs to be truncated["`
  → `long_string = os.getenv("TEST_UTILS_LONG_STRING_49")`
  → 环境变量: `TEST_UTILS_LONG_STRING_49`

- 行 55: `text = "Hello World! This is a test."`
  → `text = os.getenv("TEST_UTILS_TEXT_55")`
  → 环境变量: `TEST_UTILS_TEXT_55`

- 行 58: `camel = "camelCaseString["`
  → `camel = os.getenv("TEST_UTILS_CAMEL_58")`
  → 环境变量: `TEST_UTILS_CAMEL_58`

- 行 60: `snake = "snake_case_string["`
  → `snake = os.getenv("TEST_UTILS_SNAKE_60")`
  → 环境变量: `TEST_UTILS_SNAKE_60`

- 行 63: `dirty_text = ": This   is   a   test   string  \n\t  "`
  → `dirty_text = os.getenv("TEST_UTILS_DIRTY_TEXT_63")`
  → 环境变量: `TEST_UTILS_DIRTY_TEXT_63`

- 行 68: `text = "The price is 123.45 and quantity is 10["`
  → `text = os.getenv("TEST_UTILS_TEXT_68")`
  → 环境变量: `TEST_UTILS_TEXT_68`

- 行 111: `content = "]Test content["`
  → `content = os.getenv("TEST_UTILS_CONTENT_111")`
  → 环境变量: `TEST_UTILS_CONTENT_111`

- 行 120: `content = "]Test content["`
  → `content = os.getenv("TEST_UTILS_CONTENT_120")`
  → 环境变量: `TEST_UTILS_CONTENT_120`

- 行 125: `original = "test_string["`
  → `original = os.getenv("TEST_UTILS_ORIGINAL_125")`
  → 环境变量: `TEST_UTILS_ORIGINAL_125`

- 行 134: `original = "test_password_123["`
  → `original = os.getenv("TEST_UTILS_ORIGINAL_134")`
  → 环境变量: `TEST_UTILS_ORIGINAL_134`

- 行 134: `wrong_password = "]wrong_password["`
  → `wrong_password = os.getenv("TEST_UTILS_WRONG_PASSWORD_134")`
  → 环境变量: `TEST_UTILS_WRONG_PASSWORD_134`

- 行 136: `original = "test_string["`
  → `original = os.getenv("TEST_UTILS_ORIGINAL_136")`
  → 环境变量: `TEST_UTILS_ORIGINAL_136`

- 行 144: `short_string = "short["`
  → `short_string = os.getenv("TEST_UTILS_SHORT_STRING_144")`
  → 环境变量: `TEST_UTILS_SHORT_STRING_144`

### tests/legacy/unit/test_stream_processor_phase4.py

- 行 21: `data_type="]match["`
  → `data_type = os.getenv("TEST_STREAM_PROCESSOR_PHASE4_DATA_TYPE_21")`
  → 环境变量: `TEST_STREAM_PROCESSOR_PHASE4_DATA_TYPE_21`

### tests/legacy/unit/test_monitoring_anomaly_detector.py

- 行 52: `table_name="test_table["`
  → `table_name = os.getenv("TEST_MONITORING_ANOMALY_DETECTOR_TABLE_NAME_52")`
  → 环境变量: `TEST_MONITORING_ANOMALY_DETECTOR_TABLE_NAME_52`

- 行 52: `column_name="]test_column["`
  → `column_name = os.getenv("TEST_MONITORING_ANOMALY_DETECTOR_COLUMN_NAME_52")`
  → 环境变量: `TEST_MONITORING_ANOMALY_DETECTOR_COLUMN_NAME_52`

- 行 52: `detection_method="]test_method["`
  → `detection_method = os.getenv("TEST_MONITORING_ANOMALY_DETECTOR_DETECTION_METHOD_")`
  → 环境变量: `TEST_MONITORING_ANOMALY_DETECTOR_DETECTION_METHOD_`

- 行 52: `description="]test description["`
  → `description = os.getenv("TEST_MONITORING_ANOMALY_DETECTOR_DESCRIPTION_52")`
  → 环境变量: `TEST_MONITORING_ANOMALY_DETECTOR_DESCRIPTION_52`

- 行 58: `table_name="test_table["`
  → `table_name = os.getenv("TEST_MONITORING_ANOMALY_DETECTOR_TABLE_NAME_58")`
  → 环境变量: `TEST_MONITORING_ANOMALY_DETECTOR_TABLE_NAME_58`

- 行 58: `column_name="]test_column["`
  → `column_name = os.getenv("TEST_MONITORING_ANOMALY_DETECTOR_COLUMN_NAME_58")`
  → 环境变量: `TEST_MONITORING_ANOMALY_DETECTOR_COLUMN_NAME_58`

- 行 62: `detection_method="]test_method["`
  → `detection_method = os.getenv("TEST_MONITORING_ANOMALY_DETECTOR_DETECTION_METHOD_")`
  → 环境变量: `TEST_MONITORING_ANOMALY_DETECTOR_DETECTION_METHOD_`

- 行 62: `description="]test description["`
  → `description = os.getenv("TEST_MONITORING_ANOMALY_DETECTOR_DESCRIPTION_62")`
  → 环境变量: `TEST_MONITORING_ANOMALY_DETECTOR_DESCRIPTION_62`

### tests/legacy/unit/test_monitoring_metrics.py

- 行 141: `table_name="]]test_table["`
  → `table_name = os.getenv("TEST_MONITORING_METRICS_TABLE_NAME_141")`
  → 环境变量: `TEST_MONITORING_METRICS_TABLE_NAME_141`

### tests/legacy/unit/test_analyze_coverage.py

- 行 32: `encoding="utf-8["`
  → `encoding = os.getenv("TEST_ANALYZE_COVERAGE_ENCODING_32")`
  → 环境变量: `TEST_ANALYZE_COVERAGE_ENCODING_32`

- 行 39: `encoding="utf-8["`
  → `encoding = os.getenv("TEST_ANALYZE_COVERAGE_ENCODING_39")`
  → 环境变量: `TEST_ANALYZE_COVERAGE_ENCODING_39`

- 行 41: `encoding="utf-8["`
  → `encoding = os.getenv("TEST_ANALYZE_COVERAGE_ENCODING_41")`
  → 环境变量: `TEST_ANALYZE_COVERAGE_ENCODING_41`

- 行 60: `encoding="utf-8["`
  → `encoding = os.getenv("TEST_ANALYZE_COVERAGE_ENCODING_60")`
  → 环境变量: `TEST_ANALYZE_COVERAGE_ENCODING_60`

- 行 92: `stdout = ": malformed output without proper format["`
  → `stdout = os.getenv("TEST_ANALYZE_COVERAGE_STDOUT_92")`
  → 环境变量: `TEST_ANALYZE_COVERAGE_STDOUT_92`

- 行 100: `stderr = "Error running pytest["`
  → `stderr = os.getenv("TEST_ANALYZE_COVERAGE_STDERR_100")`
  → 环境变量: `TEST_ANALYZE_COVERAGE_STDERR_100`

- 行 111: `name="]file2.py["`
  → `name = os.getenv("TEST_ANALYZE_COVERAGE_NAME_111")`
  → 环境变量: `TEST_ANALYZE_COVERAGE_NAME_111`

- 行 114: `name="]__pycache__/cache.py["`
  → `name = os.getenv("TEST_ANALYZE_COVERAGE_NAME_114")`
  → 环境变量: `TEST_ANALYZE_COVERAGE_NAME_114`

- 行 156: `stdout = "]]2025-09-27 12:0000["`
  → `stdout = os.getenv("TEST_ANALYZE_COVERAGE_STDOUT_156")`
  → 环境变量: `TEST_ANALYZE_COVERAGE_STDOUT_156`

- 行 177: `stdout = "]2025-09-27 12:0000["`
  → `stdout = os.getenv("TEST_ANALYZE_COVERAGE_STDOUT_177")`
  → 环境变量: `TEST_ANALYZE_COVERAGE_STDOUT_177`

- 行 189: `encoding="utf-8["`
  → `encoding = os.getenv("TEST_ANALYZE_COVERAGE_ENCODING_189")`
  → 环境变量: `TEST_ANALYZE_COVERAGE_ENCODING_189`

- 行 193: `encoding="utf-8["`
  → `encoding = os.getenv("TEST_ANALYZE_COVERAGE_ENCODING_193")`
  → 环境变量: `TEST_ANALYZE_COVERAGE_ENCODING_193`

- 行 217: `match = "]TimeoutExpired["`
  → `match = os.getenv("TEST_ANALYZE_COVERAGE_MATCH_217")`
  → 环境变量: `TEST_ANALYZE_COVERAGE_MATCH_217`

- 行 224: `match = "]Permission denied["`
  → `match = os.getenv("TEST_ANALYZE_COVERAGE_MATCH_224")`
  → 环境变量: `TEST_ANALYZE_COVERAGE_MATCH_224`

### tests/legacy/unit/test_lineage_metadata_manager.py

- 行 12: `marquez_url = "http//test-marquez5000["`
  → `marquez_url = os.getenv("TEST_LINEAGE_METADATA_MANAGER_MARQUEZ_URL_12")`
  → 环境变量: `TEST_LINEAGE_METADATA_MANAGER_MARQUEZ_URL_12`

- 行 25: `name="]]test_namespace["`
  → `name = os.getenv("TEST_LINEAGE_METADATA_MANAGER_NAME_25")`
  → 环境变量: `TEST_LINEAGE_METADATA_MANAGER_NAME_25`

- 行 26: `description="]Test namespace["`
  → `description = os.getenv("TEST_LINEAGE_METADATA_MANAGER_DESCRIPTION_26")`
  → 环境变量: `TEST_LINEAGE_METADATA_MANAGER_DESCRIPTION_26`

- 行 26: `owner_name="]test_owner["`
  → `owner_name = os.getenv("TEST_LINEAGE_METADATA_MANAGER_OWNER_NAME_26")`
  → 环境变量: `TEST_LINEAGE_METADATA_MANAGER_OWNER_NAME_26`

- 行 34: `match = "]Network error["`
  → `match = os.getenv("TEST_LINEAGE_METADATA_MANAGER_MATCH_34")`
  → 环境变量: `TEST_LINEAGE_METADATA_MANAGER_MATCH_34`

- 行 35: `name="]test_namespace["`
  → `name = os.getenv("TEST_LINEAGE_METADATA_MANAGER_NAME_35")`
  → 环境变量: `TEST_LINEAGE_METADATA_MANAGER_NAME_35`

- 行 40: `namespace="]]test_namespace["`
  → `namespace = os.getenv("TEST_LINEAGE_METADATA_MANAGER_NAMESPACE_40")`
  → 环境变量: `TEST_LINEAGE_METADATA_MANAGER_NAMESPACE_40`

- 行 41: `name="]test_dataset["`
  → `name = os.getenv("TEST_LINEAGE_METADATA_MANAGER_NAME_41")`
  → 环境变量: `TEST_LINEAGE_METADATA_MANAGER_NAME_41`

- 行 41: `description="]Test dataset["`
  → `description = os.getenv("TEST_LINEAGE_METADATA_MANAGER_DESCRIPTION_41")`
  → 环境变量: `TEST_LINEAGE_METADATA_MANAGER_DESCRIPTION_41`

- 行 41: `source_name="test_source["`
  → `source_name = os.getenv("TEST_LINEAGE_METADATA_MANAGER_SOURCE_NAME_41")`
  → 环境变量: `TEST_LINEAGE_METADATA_MANAGER_SOURCE_NAME_41`

- 行 41: `tags="]test_tag["`
  → `tags = os.getenv("TEST_LINEAGE_METADATA_MANAGER_TAGS_41")`
  → 环境变量: `TEST_LINEAGE_METADATA_MANAGER_TAGS_41`

- 行 45: `namespace="]test_namespace["`
  → `namespace = os.getenv("TEST_LINEAGE_METADATA_MANAGER_NAMESPACE_45")`
  → 环境变量: `TEST_LINEAGE_METADATA_MANAGER_NAMESPACE_45`

- 行 46: `name="]test_job["`
  → `name = os.getenv("TEST_LINEAGE_METADATA_MANAGER_NAME_46")`
  → 环境变量: `TEST_LINEAGE_METADATA_MANAGER_NAME_46`

- 行 46: `description="]Test job["`
  → `description = os.getenv("TEST_LINEAGE_METADATA_MANAGER_DESCRIPTION_46")`
  → 环境变量: `TEST_LINEAGE_METADATA_MANAGER_DESCRIPTION_46`

- 行 46: `job_type="]BATCH["`
  → `job_type = os.getenv("TEST_LINEAGE_METADATA_MANAGER_JOB_TYPE_46")`
  → 环境变量: `TEST_LINEAGE_METADATA_MANAGER_JOB_TYPE_46`

- 行 51: `location="test/location["`
  → `location = os.getenv("TEST_LINEAGE_METADATA_MANAGER_LOCATION_51")`
  → 环境变量: `TEST_LINEAGE_METADATA_MANAGER_LOCATION_51`

- 行 51: `namespace="]]test_namespace["`
  → `namespace = os.getenv("TEST_LINEAGE_METADATA_MANAGER_NAMESPACE_51")`
  → 环境变量: `TEST_LINEAGE_METADATA_MANAGER_NAMESPACE_51`

- 行 51: `name="]test_dataset["`
  → `name = os.getenv("TEST_LINEAGE_METADATA_MANAGER_NAME_51")`
  → 环境变量: `TEST_LINEAGE_METADATA_MANAGER_NAME_51`

- 行 61: `query="]]test["`
  → `query = os.getenv("TEST_LINEAGE_METADATA_MANAGER_QUERY_61")`
  → 环境变量: `TEST_LINEAGE_METADATA_MANAGER_QUERY_61`

- 行 61: `namespace="]test_namespace["`
  → `namespace = os.getenv("TEST_LINEAGE_METADATA_MANAGER_NAMESPACE_61")`
  → 环境变量: `TEST_LINEAGE_METADATA_MANAGER_NAMESPACE_61`

- 行 71: `namespace="]]test_namespace["`
  → `namespace = os.getenv("TEST_LINEAGE_METADATA_MANAGER_NAMESPACE_71")`
  → 环境变量: `TEST_LINEAGE_METADATA_MANAGER_NAMESPACE_71`

- 行 72: `name="]test_dataset["`
  → `name = os.getenv("TEST_LINEAGE_METADATA_MANAGER_NAME_72")`
  → 环境变量: `TEST_LINEAGE_METADATA_MANAGER_NAME_72`

- 行 83: `namespace="]]test_namespace["`
  → `namespace = os.getenv("TEST_LINEAGE_METADATA_MANAGER_NAMESPACE_83")`
  → 环境变量: `TEST_LINEAGE_METADATA_MANAGER_NAMESPACE_83`

- 行 83: `job_name="]test_job["`
  → `job_name = os.getenv("TEST_LINEAGE_METADATA_MANAGER_JOB_NAME_83")`
  → 环境变量: `TEST_LINEAGE_METADATA_MANAGER_JOB_NAME_83`

- 行 95: `namespace="]]test_namespace["`
  → `namespace = os.getenv("TEST_LINEAGE_METADATA_MANAGER_NAMESPACE_95")`
  → 环境变量: `TEST_LINEAGE_METADATA_MANAGER_NAMESPACE_95`

- 行 95: `name="]test_dataset["`
  → `name = os.getenv("TEST_LINEAGE_METADATA_MANAGER_NAME_95")`
  → 环境变量: `TEST_LINEAGE_METADATA_MANAGER_NAME_95`

- 行 95: `tag="]test_tag["`
  → `tag = os.getenv("TEST_LINEAGE_METADATA_MANAGER_TAG_95")`
  → 环境变量: `TEST_LINEAGE_METADATA_MANAGER_TAG_95`

- 行 104: `match = "]HTTP Error["`
  → `match = os.getenv("TEST_LINEAGE_METADATA_MANAGER_MATCH_104")`
  → 环境变量: `TEST_LINEAGE_METADATA_MANAGER_MATCH_104`

- 行 106: `name="]test_namespace["`
  → `name = os.getenv("TEST_LINEAGE_METADATA_MANAGER_NAME_106")`
  → 环境变量: `TEST_LINEAGE_METADATA_MANAGER_NAME_106`

- 行 108: `match = "]HTTP Error["`
  → `match = os.getenv("TEST_LINEAGE_METADATA_MANAGER_MATCH_108")`
  → 环境变量: `TEST_LINEAGE_METADATA_MANAGER_MATCH_108`

- 行 110: `namespace="]test_namespace["`
  → `namespace = os.getenv("TEST_LINEAGE_METADATA_MANAGER_NAMESPACE_110")`
  → 环境变量: `TEST_LINEAGE_METADATA_MANAGER_NAMESPACE_110`

- 行 111: `name="]test_dataset["`
  → `name = os.getenv("TEST_LINEAGE_METADATA_MANAGER_NAME_111")`
  → 环境变量: `TEST_LINEAGE_METADATA_MANAGER_NAME_111`

- 行 118: `match = "]HTTP Error["`
  → `match = os.getenv("TEST_LINEAGE_METADATA_MANAGER_MATCH_118")`
  → 环境变量: `TEST_LINEAGE_METADATA_MANAGER_MATCH_118`

- 行 118: `namespace="]test_namespace["`
  → `namespace = os.getenv("TEST_LINEAGE_METADATA_MANAGER_NAMESPACE_118")`
  → 环境变量: `TEST_LINEAGE_METADATA_MANAGER_NAMESPACE_118`

- 行 118: `name="]test_job["`
  → `name = os.getenv("TEST_LINEAGE_METADATA_MANAGER_NAME_118")`
  → 环境变量: `TEST_LINEAGE_METADATA_MANAGER_NAME_118`

- 行 122: `match = "]HTTP Error["`
  → `match = os.getenv("TEST_LINEAGE_METADATA_MANAGER_MATCH_122")`
  → 环境变量: `TEST_LINEAGE_METADATA_MANAGER_MATCH_122`

- 行 122: `namespace="]test_namespace["`
  → `namespace = os.getenv("TEST_LINEAGE_METADATA_MANAGER_NAMESPACE_122")`
  → 环境变量: `TEST_LINEAGE_METADATA_MANAGER_NAMESPACE_122`

- 行 122: `name="]test_dataset["`
  → `name = os.getenv("TEST_LINEAGE_METADATA_MANAGER_NAME_122")`
  → 环境变量: `TEST_LINEAGE_METADATA_MANAGER_NAME_122`

- 行 124: `match = "]HTTP Error["`
  → `match = os.getenv("TEST_LINEAGE_METADATA_MANAGER_MATCH_124")`
  → 环境变量: `TEST_LINEAGE_METADATA_MANAGER_MATCH_124`

- 行 125: `query="]test["`
  → `query = os.getenv("TEST_LINEAGE_METADATA_MANAGER_QUERY_125")`
  → 环境变量: `TEST_LINEAGE_METADATA_MANAGER_QUERY_125`

- 行 126: `match = "]HTTP Error["`
  → `match = os.getenv("TEST_LINEAGE_METADATA_MANAGER_MATCH_126")`
  → 环境变量: `TEST_LINEAGE_METADATA_MANAGER_MATCH_126`

- 行 127: `namespace="]test_namespace["`
  → `namespace = os.getenv("TEST_LINEAGE_METADATA_MANAGER_NAMESPACE_127")`
  → 环境变量: `TEST_LINEAGE_METADATA_MANAGER_NAMESPACE_127`

- 行 127: `name="]test_dataset["`
  → `name = os.getenv("TEST_LINEAGE_METADATA_MANAGER_NAME_127")`
  → 环境变量: `TEST_LINEAGE_METADATA_MANAGER_NAME_127`

- 行 130: `match = "]HTTP Error["`
  → `match = os.getenv("TEST_LINEAGE_METADATA_MANAGER_MATCH_130")`
  → 环境变量: `TEST_LINEAGE_METADATA_MANAGER_MATCH_130`

- 行 130: `namespace="]test_namespace["`
  → `namespace = os.getenv("TEST_LINEAGE_METADATA_MANAGER_NAMESPACE_130")`
  → 环境变量: `TEST_LINEAGE_METADATA_MANAGER_NAMESPACE_130`

- 行 130: `job_name="]test_job["`
  → `job_name = os.getenv("TEST_LINEAGE_METADATA_MANAGER_JOB_NAME_130")`
  → 环境变量: `TEST_LINEAGE_METADATA_MANAGER_JOB_NAME_130`

- 行 136: `match = "]HTTP Error["`
  → `match = os.getenv("TEST_LINEAGE_METADATA_MANAGER_MATCH_136")`
  → 环境变量: `TEST_LINEAGE_METADATA_MANAGER_MATCH_136`

- 行 136: `namespace="]test_namespace["`
  → `namespace = os.getenv("TEST_LINEAGE_METADATA_MANAGER_NAMESPACE_136")`
  → 环境变量: `TEST_LINEAGE_METADATA_MANAGER_NAMESPACE_136`

- 行 136: `name="]test_dataset["`
  → `name = os.getenv("TEST_LINEAGE_METADATA_MANAGER_NAME_136")`
  → 环境变量: `TEST_LINEAGE_METADATA_MANAGER_NAME_136`

- 行 136: `tag="]test_tag["`
  → `tag = os.getenv("TEST_LINEAGE_METADATA_MANAGER_TAG_136")`
  → 环境变量: `TEST_LINEAGE_METADATA_MANAGER_TAG_136`

- 行 146: `name="]]minimal_namespace["`
  → `name = os.getenv("TEST_LINEAGE_METADATA_MANAGER_NAME_146")`
  → 环境变量: `TEST_LINEAGE_METADATA_MANAGER_NAME_146`

- 行 150: `namespace="]]test_namespace["`
  → `namespace = os.getenv("TEST_LINEAGE_METADATA_MANAGER_NAMESPACE_150")`
  → 环境变量: `TEST_LINEAGE_METADATA_MANAGER_NAMESPACE_150`

- 行 150: `name="]minimal_dataset["`
  → `name = os.getenv("TEST_LINEAGE_METADATA_MANAGER_NAME_150")`
  → 环境变量: `TEST_LINEAGE_METADATA_MANAGER_NAME_150`

- 行 157: `namespace="]test_namespace["`
  → `namespace = os.getenv("TEST_LINEAGE_METADATA_MANAGER_NAMESPACE_157")`
  → 环境变量: `TEST_LINEAGE_METADATA_MANAGER_NAMESPACE_157`

- 行 158: `name="]minimal_job["`
  → `name = os.getenv("TEST_LINEAGE_METADATA_MANAGER_NAME_158")`
  → 环境变量: `TEST_LINEAGE_METADATA_MANAGER_NAME_158`

### tests/legacy/unit/data_storage_data_lake_storage_batch_gamma_.py

- 行 252: `compression="]gzip["`
  → `compression = os.getenv("DATA_STORAGE_DATA_LAKE_STORAGE_BATCH_GAMMA__COMPRE")`
  → 环境变量: `DATA_STORAGE_DATA_LAKE_STORAGE_BATCH_GAMMA__COMPRE`

- 行 252: `compression="]snappy["`
  → `compression = os.getenv("DATA_STORAGE_DATA_LAKE_STORAGE_BATCH_GAMMA__COMPRE")`
  → 环境变量: `DATA_STORAGE_DATA_LAKE_STORAGE_BATCH_GAMMA__COMPRE`

- 行 274: `base_path="./test_data["`
  → `base_path = os.getenv("DATA_STORAGE_DATA_LAKE_STORAGE_BATCH_GAMMA__BASE_P")`
  → 环境变量: `DATA_STORAGE_DATA_LAKE_STORAGE_BATCH_GAMMA__BASE_P`

- 行 277: `abs_path = "]/tmp/test_data["`
  → `abs_path = os.getenv("DATA_STORAGE_DATA_LAKE_STORAGE_BATCH_GAMMA__ABS_PA")`
  → 环境变量: `DATA_STORAGE_DATA_LAKE_STORAGE_BATCH_GAMMA__ABS_PA`

- 行 396: `compression="invalid_format["`
  → `compression = os.getenv("DATA_STORAGE_DATA_LAKE_STORAGE_BATCH_GAMMA__COMPRE")`
  → 环境变量: `DATA_STORAGE_DATA_LAKE_STORAGE_BATCH_GAMMA__COMPRE`

### tests/legacy/unit/test_api_predictions.py

- 行 43: `match_status = "scheduled["`
  → `match_status = os.getenv("TEST_API_PREDICTIONS_MATCH_STATUS_43")`
  → 环境变量: `TEST_API_PREDICTIONS_MATCH_STATUS_43`

- 行 43: `season = "]2024-25["`
  → `season = os.getenv("TEST_API_PREDICTIONS_SEASON_43")`
  → 环境变量: `TEST_API_PREDICTIONS_SEASON_43`

- 行 47: `model_name = "]football_model["`
  → `model_name = os.getenv("TEST_API_PREDICTIONS_MODEL_NAME_47")`
  → 环境变量: `TEST_API_PREDICTIONS_MODEL_NAME_47`

- 行 48: `predicted_result = "]]]]home["`
  → `predicted_result = os.getenv("TEST_API_PREDICTIONS_PREDICTED_RESULT_48")`
  → 环境变量: `TEST_API_PREDICTIONS_PREDICTED_RESULT_48`

- 行 78: `match_status = "scheduled["`
  → `match_status = os.getenv("TEST_API_PREDICTIONS_MATCH_STATUS_78")`
  → 环境变量: `TEST_API_PREDICTIONS_MATCH_STATUS_78`

- 行 79: `season = "]2024-25["`
  → `season = os.getenv("TEST_API_PREDICTIONS_SEASON_79")`
  → 环境变量: `TEST_API_PREDICTIONS_SEASON_79`

- 行 82: `model_name="]football_model["`
  → `model_name = os.getenv("TEST_API_PREDICTIONS_MODEL_NAME_82")`
  → 环境变量: `TEST_API_PREDICTIONS_MODEL_NAME_82`

- 行 84: `predicted_result="]home["`
  → `predicted_result = os.getenv("TEST_API_PREDICTIONS_PREDICTED_RESULT_84")`
  → 环境变量: `TEST_API_PREDICTIONS_PREDICTED_RESULT_84`

- 行 119: `match_status = "scheduled["`
  → `match_status = os.getenv("TEST_API_PREDICTIONS_MATCH_STATUS_119")`
  → 环境变量: `TEST_API_PREDICTIONS_MATCH_STATUS_119`

- 行 119: `season = "]2024-25["`
  → `season = os.getenv("TEST_API_PREDICTIONS_SEASON_119")`
  → 环境变量: `TEST_API_PREDICTIONS_SEASON_119`

- 行 124: `model_name="]football_model["`
  → `model_name = os.getenv("TEST_API_PREDICTIONS_MODEL_NAME_124")`
  → 环境变量: `TEST_API_PREDICTIONS_MODEL_NAME_124`

- 行 127: `predicted_result="]home["`
  → `predicted_result = os.getenv("TEST_API_PREDICTIONS_PREDICTED_RESULT_127")`
  → 环境变量: `TEST_API_PREDICTIONS_PREDICTED_RESULT_127`

- 行 160: `model_name="]football_model["`
  → `model_name = os.getenv("TEST_API_PREDICTIONS_MODEL_NAME_160")`
  → 环境变量: `TEST_API_PREDICTIONS_MODEL_NAME_160`

- 行 160: `predicted_result="]home["`
  → `predicted_result = os.getenv("TEST_API_PREDICTIONS_PREDICTED_RESULT_160")`
  → 环境变量: `TEST_API_PREDICTIONS_PREDICTED_RESULT_160`

- 行 183: `model_name = "]football_model["`
  → `model_name = os.getenv("TEST_API_PREDICTIONS_MODEL_NAME_183")`
  → 环境变量: `TEST_API_PREDICTIONS_MODEL_NAME_183`

- 行 185: `predicted_result = "]]]]home["`
  → `predicted_result = os.getenv("TEST_API_PREDICTIONS_PREDICTED_RESULT_185")`
  → 环境变量: `TEST_API_PREDICTIONS_PREDICTED_RESULT_185`

- 行 221: `model_name = "]football_model["`
  → `model_name = os.getenv("TEST_API_PREDICTIONS_MODEL_NAME_221")`
  → 环境变量: `TEST_API_PREDICTIONS_MODEL_NAME_221`

- 行 221: `predicted_result = "]home["`
  → `predicted_result = os.getenv("TEST_API_PREDICTIONS_PREDICTED_RESULT_221")`
  → 环境变量: `TEST_API_PREDICTIONS_PREDICTED_RESULT_221`

- 行 224: `match_status = "]]]scheduled["`
  → `match_status = os.getenv("TEST_API_PREDICTIONS_MATCH_STATUS_224")`
  → 环境变量: `TEST_API_PREDICTIONS_MATCH_STATUS_224`

### tests/legacy/unit/test_file_utils.py

- 行 35: `encoding = "]utf-8["`
  → `encoding = os.getenv("TEST_FILE_UTILS_ENCODING_35")`
  → 环境变量: `TEST_FILE_UTILS_ENCODING_35`

- 行 38: `match = "]无法读取JSON文件["`
  → `match = os.getenv("TEST_FILE_UTILS_MATCH_38")`
  → 环境变量: `TEST_FILE_UTILS_MATCH_38`

- 行 40: `match = "]无法读取JSON文件["`
  → `match = os.getenv("TEST_FILE_UTILS_MATCH_40")`
  → 环境变量: `TEST_FILE_UTILS_MATCH_40`

- 行 42: `encoding = "]utf-8["`
  → `encoding = os.getenv("TEST_FILE_UTILS_ENCODING_42")`
  → 环境变量: `TEST_FILE_UTILS_ENCODING_42`

- 行 45: `encoding = "]utf-8["`
  → `encoding = os.getenv("TEST_FILE_UTILS_ENCODING_45")`
  → 环境变量: `TEST_FILE_UTILS_ENCODING_45`

- 行 47: `encoding = "]utf-8["`
  → `encoding = os.getenv("TEST_FILE_UTILS_ENCODING_47")`
  → 环境变量: `TEST_FILE_UTILS_ENCODING_47`

- 行 74: `test_content = "这是测试内容["`
  → `test_content = os.getenv("TEST_FILE_UTILS_TEST_CONTENT_74")`
  → 环境变量: `TEST_FILE_UTILS_TEST_CONTENT_74`

- 行 78: `encoding = "]utf-8["`
  → `encoding = os.getenv("TEST_FILE_UTILS_ENCODING_78")`
  → 环境变量: `TEST_FILE_UTILS_ENCODING_78`

- 行 87: `test_content = "Hello, World!"`
  → `test_content = os.getenv("TEST_FILE_UTILS_TEST_CONTENT_87")`
  → 环境变量: `TEST_FILE_UTILS_TEST_CONTENT_87`

- 行 87: `encoding = "]utf-8["`
  → `encoding = os.getenv("TEST_FILE_UTILS_ENCODING_87")`
  → 环境变量: `TEST_FILE_UTILS_ENCODING_87`

### tests/legacy/unit/test_string_utils.py

- 行 14: `_text = "Hello["`
  → `_text = os.getenv("TEST_STRING_UTILS__TEXT_14")`
  → 环境变量: `TEST_STRING_UTILS__TEXT_14`

- 行 15: `_text = "Price is 12.99 and discount 5.5%"`
  → `_text = os.getenv("TEST_STRING_UTILS__TEXT_15")`
  → 环境变量: `TEST_STRING_UTILS__TEXT_15`

- 行 16: `_text = "Temperature -15.5 degrees["`
  → `_text = os.getenv("TEST_STRING_UTILS__TEXT_16")`
  → 环境变量: `TEST_STRING_UTILS__TEXT_16`

### tests/legacy/unit/test_data_features_feature_store.py

- 行 33: `return_value = "]/tmp/test_feast_repo["`
  → `return_value = os.getenv("TEST_DATA_FEATURES_FEATURE_STORE_RETURN_VALUE_33")`
  → 环境变量: `TEST_DATA_FEATURES_FEATURE_STORE_RETURN_VALUE_33`

- 行 46: `return_value = "]/tmp/test_feast_repo["`
  → `return_value = os.getenv("TEST_DATA_FEATURES_FEATURE_STORE_RETURN_VALUE_46")`
  → 环境变量: `TEST_DATA_FEATURES_FEATURE_STORE_RETURN_VALUE_46`

- 行 46: `project_name="]custom_project["`
  → `project_name = os.getenv("TEST_DATA_FEATURES_FEATURE_STORE_PROJECT_NAME_46")`
  → 环境变量: `TEST_DATA_FEATURES_FEATURE_STORE_PROJECT_NAME_46`

- 行 59: `return_value = "]/tmp/test_feast_repo["`
  → `return_value = os.getenv("TEST_DATA_FEATURES_FEATURE_STORE_RETURN_VALUE_59")`
  → 环境变量: `TEST_DATA_FEATURES_FEATURE_STORE_RETURN_VALUE_59`

- 行 60: `return_value = "]]yaml_content["`
  → `return_value = os.getenv("TEST_DATA_FEATURES_FEATURE_STORE_RETURN_VALUE_60")`
  → 环境变量: `TEST_DATA_FEATURES_FEATURE_STORE_RETURN_VALUE_60`

- 行 60: `repo_path="]]/tmp/test_feast_repo["`
  → `repo_path = os.getenv("TEST_DATA_FEATURES_FEATURE_STORE_REPO_PATH_60")`
  → 环境变量: `TEST_DATA_FEATURES_FEATURE_STORE_REPO_PATH_60`

- 行 71: `return_value = "]/tmp/test_feast_repo["`
  → `return_value = os.getenv("TEST_DATA_FEATURES_FEATURE_STORE_RETURN_VALUE_71")`
  → 环境变量: `TEST_DATA_FEATURES_FEATURE_STORE_RETURN_VALUE_71`

- 行 75: `return_value = "]yaml_content["`
  → `return_value = os.getenv("TEST_DATA_FEATURES_FEATURE_STORE_RETURN_VALUE_75")`
  → 环境变量: `TEST_DATA_FEATURES_FEATURE_STORE_RETURN_VALUE_75`

- 行 123: `push_source_name="]team_stats["`
  → `push_source_name = os.getenv("TEST_DATA_FEATURES_FEATURE_STORE_PUSH_SOURCE_NAME_")`
  → 环境变量: `TEST_DATA_FEATURES_FEATURE_STORE_PUSH_SOURCE_NAME_`

- 行 124: `to="]online_and_offline["`
  → `to = os.getenv("TEST_DATA_FEATURES_FEATURE_STORE_TO_124")`
  → 环境变量: `TEST_DATA_FEATURES_FEATURE_STORE_TO_124`

- 行 239: `name="feature1["`
  → `name = os.getenv("TEST_DATA_FEATURES_FEATURE_STORE_NAME_239")`
  → 环境变量: `TEST_DATA_FEATURES_FEATURE_STORE_NAME_239`

- 行 239: `name="]feature2["`
  → `name = os.getenv("TEST_DATA_FEATURES_FEATURE_STORE_NAME_239")`
  → 环境变量: `TEST_DATA_FEATURES_FEATURE_STORE_NAME_239`

- 行 239: `name="]team["`
  → `name = os.getenv("TEST_DATA_FEATURES_FEATURE_STORE_NAME_239")`
  → 环境变量: `TEST_DATA_FEATURES_FEATURE_STORE_NAME_239`

- 行 264: `name = "team_stats["`
  → `name = os.getenv("TEST_DATA_FEATURES_FEATURE_STORE_NAME_264")`
  → 环境变量: `TEST_DATA_FEATURES_FEATURE_STORE_NAME_264`

- 行 265: `name="]team["`
  → `name = os.getenv("TEST_DATA_FEATURES_FEATURE_STORE_NAME_265")`
  → 环境变量: `TEST_DATA_FEATURES_FEATURE_STORE_NAME_265`

- 行 265: `name = "]wins["`
  → `name = os.getenv("TEST_DATA_FEATURES_FEATURE_STORE_NAME_265")`
  → 环境变量: `TEST_DATA_FEATURES_FEATURE_STORE_NAME_265`

- 行 265: `name="]int64["`
  → `name = os.getenv("TEST_DATA_FEATURES_FEATURE_STORE_NAME_265")`
  → 环境变量: `TEST_DATA_FEATURES_FEATURE_STORE_NAME_265`

- 行 268: `name = "]match_stats["`
  → `name = os.getenv("TEST_DATA_FEATURES_FEATURE_STORE_NAME_268")`
  → 环境变量: `TEST_DATA_FEATURES_FEATURE_STORE_NAME_268`

- 行 269: `name="]match["`
  → `name = os.getenv("TEST_DATA_FEATURES_FEATURE_STORE_NAME_269")`
  → 环境变量: `TEST_DATA_FEATURES_FEATURE_STORE_NAME_269`

- 行 271: `name = "]goals["`
  → `name = os.getenv("TEST_DATA_FEATURES_FEATURE_STORE_NAME_271")`
  → 环境变量: `TEST_DATA_FEATURES_FEATURE_STORE_NAME_271`

- 行 272: `name="]float64["`
  → `name = os.getenv("TEST_DATA_FEATURES_FEATURE_STORE_NAME_272")`
  → 环境变量: `TEST_DATA_FEATURES_FEATURE_STORE_NAME_272`

- 行 315: `_feature_store = "existing_store["`
  → `_feature_store = os.getenv("TEST_DATA_FEATURES_FEATURE_STORE__FEATURE_STORE_31")`
  → 环境变量: `TEST_DATA_FEATURES_FEATURE_STORE__FEATURE_STORE_31`

- 行 341: `project_name="test_project["`
  → `project_name = os.getenv("TEST_DATA_FEATURES_FEATURE_STORE_PROJECT_NAME_341")`
  → 环境变量: `TEST_DATA_FEATURES_FEATURE_STORE_PROJECT_NAME_341`

- 行 343: `repo_path="]/test/path["`
  → `repo_path = os.getenv("TEST_DATA_FEATURES_FEATURE_STORE_REPO_PATH_343")`
  → 环境变量: `TEST_DATA_FEATURES_FEATURE_STORE_REPO_PATH_343`

### tests/legacy/unit/test_response.py

- 行 37: `success="not_boolean["`
  → `success = os.getenv("TEST_RESPONSE_SUCCESS_37")`
  → 环境变量: `TEST_RESPONSE_SUCCESS_37`

- 行 37: `message="]test["`
  → `message = os.getenv("TEST_RESPONSE_MESSAGE_37")`
  → 环境变量: `TEST_RESPONSE_MESSAGE_37`

- 行 56: `custom_message = "数据保存成功["`
  → `custom_message = os.getenv("TEST_RESPONSE_CUSTOM_MESSAGE_56")`
  → 环境变量: `TEST_RESPONSE_CUSTOM_MESSAGE_56`

- 行 59: `custom_message = "]任务执行完成["`
  → `custom_message = os.getenv("TEST_RESPONSE_CUSTOM_MESSAGE_59")`
  → 环境变量: `TEST_RESPONSE_CUSTOM_MESSAGE_59`

- 行 69: `error_message = "用户名已存在["`
  → `error_message = os.getenv("TEST_RESPONSE_ERROR_MESSAGE_69")`
  → 环境变量: `TEST_RESPONSE_ERROR_MESSAGE_69`

- 行 72: `error_message = "资源未找到["`
  → `error_message = os.getenv("TEST_RESPONSE_ERROR_MESSAGE_72")`
  → 环境变量: `TEST_RESPONSE_ERROR_MESSAGE_72`

- 行 78: `message="]验证失败["`
  → `message = os.getenv("TEST_RESPONSE_MESSAGE_78")`
  → 环境变量: `TEST_RESPONSE_MESSAGE_78`

- 行 89: `message="无数据返回["`
  → `message = os.getenv("TEST_RESPONSE_MESSAGE_89")`
  → 环境变量: `TEST_RESPONSE_MESSAGE_89`

### tests/legacy/unit/test_main_minimal.py

- 行 24: `title="足球预测API["`
  → `title = os.getenv("TEST_MAIN_MINIMAL_TITLE_24")`
  → 环境变量: `TEST_MAIN_MINIMAL_TITLE_24`

- 行 24: `description="]基于机器学习的足球比赛结果预测系统["`
  → `description = os.getenv("TEST_MAIN_MINIMAL_DESCRIPTION_24")`
  → 环境变量: `TEST_MAIN_MINIMAL_DESCRIPTION_24`

- 行 24: `version="]1.0.0["`
  → `version = os.getenv("TEST_MAIN_MINIMAL_VERSION_24")`
  → 环境变量: `TEST_MAIN_MINIMAL_VERSION_24`

- 行 24: `docs_url="]_docs["`
  → `docs_url = os.getenv("TEST_MAIN_MINIMAL_DOCS_URL_24")`
  → 环境变量: `TEST_MAIN_MINIMAL_DOCS_URL_24`

- 行 24: `redoc_url="]/redoc["`
  → `redoc_url = os.getenv("TEST_MAIN_MINIMAL_REDOC_URL_24")`
  → 环境变量: `TEST_MAIN_MINIMAL_REDOC_URL_24`

- 行 24: `cors_origins = "http:_/localhost3000["`
  → `cors_origins = os.getenv("TEST_MAIN_MINIMAL_CORS_ORIGINS_24")`
  → 环境变量: `TEST_MAIN_MINIMAL_CORS_ORIGINS_24`

- 行 46: `url = "http_/test.com/api/test["`
  → `url = os.getenv("TEST_MAIN_MINIMAL_URL_46")`
  → 环境变量: `TEST_MAIN_MINIMAL_URL_46`

- 行 48: `detail="]页面未找到["`
  → `detail = os.getenv("TEST_MAIN_MINIMAL_DETAIL_48")`
  → 环境变量: `TEST_MAIN_MINIMAL_DETAIL_48`

- 行 69: `url = "http_/test.com/api/test["`
  → `url = os.getenv("TEST_MAIN_MINIMAL_URL_69")`
  → 环境变量: `TEST_MAIN_MINIMAL_URL_69`

- 行 147: `match = "]]]数据库连接失败["`
  → `match = os.getenv("TEST_MAIN_MINIMAL_MATCH_147")`
  → 环境变量: `TEST_MAIN_MINIMAL_MATCH_147`

- 行 155: `default_host = "]0.0.0.0["`
  → `default_host = os.getenv("TEST_MAIN_MINIMAL_DEFAULT_HOST_155")`
  → 环境变量: `TEST_MAIN_MINIMAL_DEFAULT_HOST_155`

- 行 156: `default_host = "]127.0.0.1["`
  → `default_host = os.getenv("TEST_MAIN_MINIMAL_DEFAULT_HOST_156")`
  → 环境变量: `TEST_MAIN_MINIMAL_DEFAULT_HOST_156`

- 行 160: `default_host = "]0.0.0.0["`
  → `default_host = os.getenv("TEST_MAIN_MINIMAL_DEFAULT_HOST_160")`
  → 环境变量: `TEST_MAIN_MINIMAL_DEFAULT_HOST_160`

- 行 160: `default_host = "]127.0.0.1["`
  → `default_host = os.getenv("TEST_MAIN_MINIMAL_DEFAULT_HOST_160")`
  → 环境变量: `TEST_MAIN_MINIMAL_DEFAULT_HOST_160`

- 行 174: `prefix="]/api/v1["`
  → `prefix = os.getenv("TEST_MAIN_MINIMAL_PREFIX_174")`
  → 环境变量: `TEST_MAIN_MINIMAL_PREFIX_174`

- 行 220: `default_host = "]0.0.0.0["`
  → `default_host = os.getenv("TEST_MAIN_MINIMAL_DEFAULT_HOST_220")`
  → 环境变量: `TEST_MAIN_MINIMAL_DEFAULT_HOST_220`

- 行 221: `default_host = "]127.0.0.1["`
  → `default_host = os.getenv("TEST_MAIN_MINIMAL_DEFAULT_HOST_221")`
  → 环境变量: `TEST_MAIN_MINIMAL_DEFAULT_HOST_221`

- 行 230: `default_host = "]0.0.0.0["`
  → `default_host = os.getenv("TEST_MAIN_MINIMAL_DEFAULT_HOST_230")`
  → 环境变量: `TEST_MAIN_MINIMAL_DEFAULT_HOST_230`

- 行 230: `default_host = "]127.0.0.1["`
  → `default_host = os.getenv("TEST_MAIN_MINIMAL_DEFAULT_HOST_230")`
  → 环境变量: `TEST_MAIN_MINIMAL_DEFAULT_HOST_230`

### tests/legacy/unit/test_data_processing_coverage_acceleration.py

- 行 164: `invalid_data = "invalid_data_type["`
  → `invalid_data = os.getenv("TEST_DATA_PROCESSING_COVERAGE_ACCELERATION_INVALID")`
  → 环境变量: `TEST_DATA_PROCESSING_COVERAGE_ACCELERATION_INVALID`

- 行 372: `invalid_type = "invalid_type["`
  → `invalid_type = os.getenv("TEST_DATA_PROCESSING_COVERAGE_ACCELERATION_INVALID")`
  → 环境变量: `TEST_DATA_PROCESSING_COVERAGE_ACCELERATION_INVALID`

- 行 526: `cache_key = "test_key["`
  → `cache_key = os.getenv("TEST_DATA_PROCESSING_COVERAGE_ACCELERATION_CACHE_K")`
  → 环境变量: `TEST_DATA_PROCESSING_COVERAGE_ACCELERATION_CACHE_K`

- 行 655: `invalid_data = "invalid_string["`
  → `invalid_data = os.getenv("TEST_DATA_PROCESSING_COVERAGE_ACCELERATION_INVALID")`
  → 环境变量: `TEST_DATA_PROCESSING_COVERAGE_ACCELERATION_INVALID`

### tests/legacy/unit/test_data_processing_service.py

- 行 171: `text = "This is a test text for processing["`
  → `text = os.getenv("TEST_DATA_PROCESSING_SERVICE_TEXT_171")`
  → 环境变量: `TEST_DATA_PROCESSING_SERVICE_TEXT_171`

### tests/legacy/unit/test_data_features_examples.py

- 行 87: `_feature_view_name = "team_recent_stats["`
  → `_feature_view_name = os.getenv("TEST_DATA_FEATURES_EXAMPLES__FEATURE_VIEW_NAME_87")`
  → 环境变量: `TEST_DATA_FEATURES_EXAMPLES__FEATURE_VIEW_NAME_87`

- 行 96: `_feature_view_name = "odds_features["`
  → `_feature_view_name = os.getenv("TEST_DATA_FEATURES_EXAMPLES__FEATURE_VIEW_NAME_96")`
  → 环境变量: `TEST_DATA_FEATURES_EXAMPLES__FEATURE_VIEW_NAME_96`

### tests/legacy/unit/test_data_lake_storage.py

- 行 86: `match = "Unknown table["`
  → `match = os.getenv("TEST_DATA_LAKE_STORAGE_MATCH_86")`
  → 环境变量: `TEST_DATA_LAKE_STORAGE_MATCH_86`

### tests/legacy/unit/streaming_kafka_consumer_batch_gamma_.py

- 行 58: `topic = "football_matches["`
  → `topic = os.getenv("STREAMING_KAFKA_CONSUMER_BATCH_GAMMA__TOPIC_58")`
  → 环境变量: `STREAMING_KAFKA_CONSUMER_BATCH_GAMMA__TOPIC_58`

- 行 87: `topic = "matches["`
  → `topic = os.getenv("STREAMING_KAFKA_CONSUMER_BATCH_GAMMA__TOPIC_87")`
  → 环境变量: `STREAMING_KAFKA_CONSUMER_BATCH_GAMMA__TOPIC_87`

- 行 266: `topic = "matches["`
  → `topic = os.getenv("STREAMING_KAFKA_CONSUMER_BATCH_GAMMA__TOPIC_266")`
  → 环境变量: `STREAMING_KAFKA_CONSUMER_BATCH_GAMMA__TOPIC_266`

### tests/legacy/unit/test_edge_cases_and_failures.py

- 行 92: `match = "]比赛 0 不存在["`
  → `match = os.getenv("TEST_EDGE_CASES_AND_FAILURES_MATCH_92")`
  → 环境变量: `TEST_EDGE_CASES_AND_FAILURES_MATCH_92`

- 行 92: `match = "]比赛 -1 不存在["`
  → `match = os.getenv("TEST_EDGE_CASES_AND_FAILURES_MATCH_92")`
  → 环境变量: `TEST_EDGE_CASES_AND_FAILURES_MATCH_92`

- 行 202: `model_version="]]1.0["`
  → `model_version = os.getenv("TEST_EDGE_CASES_AND_FAILURES_MODEL_VERSION_202")`
  → 环境变量: `TEST_EDGE_CASES_AND_FAILURES_MODEL_VERSION_202`

- 行 219: `match = "]模型文件损坏["`
  → `match = os.getenv("TEST_EDGE_CASES_AND_FAILURES_MATCH_219")`
  → 环境变量: `TEST_EDGE_CASES_AND_FAILURES_MATCH_219`

- 行 227: `match="模型 football_baseline_model 没有可用版本["`
  → `match = os.getenv("TEST_EDGE_CASES_AND_FAILURES_MATCH_227")`
  → 环境变量: `TEST_EDGE_CASES_AND_FAILURES_MATCH_227`

### tests/legacy/unit/test_data_features.py

- 行 19: `prefix="feast_repo_test_["`
  → `prefix = os.getenv("TEST_DATA_FEATURES_PREFIX_19")`
  → 环境变量: `TEST_DATA_FEATURES_PREFIX_19`

- 行 19: `project_name="]test_project["`
  → `project_name = os.getenv("TEST_DATA_FEATURES_PROJECT_NAME_19")`
  → 环境变量: `TEST_DATA_FEATURES_PROJECT_NAME_19`

- 行 20: `project_name="test_project["`
  → `project_name = os.getenv("TEST_DATA_FEATURES_PROJECT_NAME_20")`
  → 环境变量: `TEST_DATA_FEATURES_PROJECT_NAME_20`

- 行 46: `match = "特征仓库未初始化["`
  → `match = os.getenv("TEST_DATA_FEATURES_MATCH_46")`
  → 环境变量: `TEST_DATA_FEATURES_MATCH_46`

- 行 58: `match = "]]特征仓库未初始化["`
  → `match = os.getenv("TEST_DATA_FEATURES_MATCH_58")`
  → 环境变量: `TEST_DATA_FEATURES_MATCH_58`

- 行 64: `match = "]]特征仓库未初始化["`
  → `match = os.getenv("TEST_DATA_FEATURES_MATCH_64")`
  → 环境变量: `TEST_DATA_FEATURES_MATCH_64`

- 行 74: `match = "]特征仓库未初始化["`
  → `match = os.getenv("TEST_DATA_FEATURES_MATCH_74")`
  → 环境变量: `TEST_DATA_FEATURES_MATCH_74`

- 行 89: `match = "特征仓库未初始化["`
  → `match = os.getenv("TEST_DATA_FEATURES_MATCH_89")`
  → 环境变量: `TEST_DATA_FEATURES_MATCH_89`

- 行 92: `name = "]view1["`
  → `name = os.getenv("TEST_DATA_FEATURES_NAME_92")`
  → 环境变量: `TEST_DATA_FEATURES_NAME_92`

- 行 96: `name = "]feature1["`
  → `name = os.getenv("TEST_DATA_FEATURES_NAME_96")`
  → 环境变量: `TEST_DATA_FEATURES_NAME_96`

- 行 97: `name = "]INT32["`
  → `name = os.getenv("TEST_DATA_FEATURES_NAME_97")`
  → 环境变量: `TEST_DATA_FEATURES_NAME_97`

- 行 97: `description = "]First feature["`
  → `description = os.getenv("TEST_DATA_FEATURES_DESCRIPTION_97")`
  → 环境变量: `TEST_DATA_FEATURES_DESCRIPTION_97`

- 行 97: `name = "]feature2["`
  → `name = os.getenv("TEST_DATA_FEATURES_NAME_97")`
  → 环境变量: `TEST_DATA_FEATURES_NAME_97`

- 行 97: `name = "]FLOAT["`
  → `name = os.getenv("TEST_DATA_FEATURES_NAME_97")`
  → 环境变量: `TEST_DATA_FEATURES_NAME_97`

- 行 97: `description = "]Second feature["`
  → `description = os.getenv("TEST_DATA_FEATURES_DESCRIPTION_97")`
  → 环境变量: `TEST_DATA_FEATURES_DESCRIPTION_97`

- 行 97: `match = "特征仓库未初始化["`
  → `match = os.getenv("TEST_DATA_FEATURES_MATCH_97")`
  → 环境变量: `TEST_DATA_FEATURES_MATCH_97`

- 行 115: `project_name="]]test_project["`
  → `project_name = os.getenv("TEST_DATA_FEATURES_PROJECT_NAME_115")`
  → 环境变量: `TEST_DATA_FEATURES_PROJECT_NAME_115`

- 行 149: `project_name="]custom_project["`
  → `project_name = os.getenv("TEST_DATA_FEATURES_PROJECT_NAME_149")`
  → 环境变量: `TEST_DATA_FEATURES_PROJECT_NAME_149`

### tests/legacy/unit/test_comprehensive_mcp_health_check.py

- 行 135: `stdout = "container1\ncontainer2\ncontainer3\n["`
  → `stdout = os.getenv("TEST_COMPREHENSIVE_MCP_HEALTH_CHECK_STDOUT_135")`
  → 环境变量: `TEST_COMPREHENSIVE_MCP_HEALTH_CHECK_STDOUT_135`

- 行 140: `stderr = "Command not found["`
  → `stderr = os.getenv("TEST_COMPREHENSIVE_MCP_HEALTH_CHECK_STDERR_140")`
  → 环境变量: `TEST_COMPREHENSIVE_MCP_HEALTH_CHECK_STDERR_140`

- 行 142: `cmd="docker["`
  → `cmd = os.getenv("TEST_COMPREHENSIVE_MCP_HEALTH_CHECK_CMD_142")`
  → 环境变量: `TEST_COMPREHENSIVE_MCP_HEALTH_CHECK_CMD_142`

- 行 150: `name = "]pod2["`
  → `name = os.getenv("TEST_COMPREHENSIVE_MCP_HEALTH_CHECK_NAME_150")`
  → 环境变量: `TEST_COMPREHENSIVE_MCP_HEALTH_CHECK_NAME_150`

- 行 198: `name = "Experiment 1["`
  → `name = os.getenv("TEST_COMPREHENSIVE_MCP_HEALTH_CHECK_NAME_198")`
  → 环境变量: `TEST_COMPREHENSIVE_MCP_HEALTH_CHECK_NAME_198`

- 行 199: `name = "]Experiment 2["`
  → `name = os.getenv("TEST_COMPREHENSIVE_MCP_HEALTH_CHECK_NAME_199")`
  → 环境变量: `TEST_COMPREHENSIVE_MCP_HEALTH_CHECK_NAME_199`

- 行 210: `name = "feature_view_1["`
  → `name = os.getenv("TEST_COMPREHENSIVE_MCP_HEALTH_CHECK_NAME_210")`
  → 环境变量: `TEST_COMPREHENSIVE_MCP_HEALTH_CHECK_NAME_210`

- 行 210: `name = "]feature_view_2["`
  → `name = os.getenv("TEST_COMPREHENSIVE_MCP_HEALTH_CHECK_NAME_210")`
  → 环境变量: `TEST_COMPREHENSIVE_MCP_HEALTH_CHECK_NAME_210`

- 行 225: `return_value = "]0.75["`
  → `return_value = os.getenv("TEST_COMPREHENSIVE_MCP_HEALTH_CHECK_RETURN_VALUE_2")`
  → 环境变量: `TEST_COMPREHENSIVE_MCP_HEALTH_CHECK_RETURN_VALUE_2`

- 行 247: `stderr = "No tests found["`
  → `stderr = os.getenv("TEST_COMPREHENSIVE_MCP_HEALTH_CHECK_STDERR_247")`
  → 环境变量: `TEST_COMPREHENSIVE_MCP_HEALTH_CHECK_STDERR_247`

### tests/legacy/unit/monitoring_anomaly_detector_batch_gamma_.py

- 行 249: `table_name="matches["`
  → `table_name = os.getenv("MONITORING_ANOMALY_DETECTOR_BATCH_GAMMA__TABLE_NAM")`
  → 环境变量: `MONITORING_ANOMALY_DETECTOR_BATCH_GAMMA__TABLE_NAM`

- 行 249: `column_name="]home_score["`
  → `column_name = os.getenv("MONITORING_ANOMALY_DETECTOR_BATCH_GAMMA__COLUMN_NA")`
  → 环境变量: `MONITORING_ANOMALY_DETECTOR_BATCH_GAMMA__COLUMN_NA`

- 行 249: `detection_method="]3sigma["`
  → `detection_method = os.getenv("MONITORING_ANOMALY_DETECTOR_BATCH_GAMMA__DETECTION")`
  → 环境变量: `MONITORING_ANOMALY_DETECTOR_BATCH_GAMMA__DETECTION`

- 行 249: `description="]严重异常["`
  → `description = os.getenv("MONITORING_ANOMALY_DETECTOR_BATCH_GAMMA__DESCRIPTI")`
  → 环境变量: `MONITORING_ANOMALY_DETECTOR_BATCH_GAMMA__DESCRIPTI`

- 行 250: `table_name="]matches["`
  → `table_name = os.getenv("MONITORING_ANOMALY_DETECTOR_BATCH_GAMMA__TABLE_NAM")`
  → 环境变量: `MONITORING_ANOMALY_DETECTOR_BATCH_GAMMA__TABLE_NAM`

- 行 251: `column_name="]away_score["`
  → `column_name = os.getenv("MONITORING_ANOMALY_DETECTOR_BATCH_GAMMA__COLUMN_NA")`
  → 环境变量: `MONITORING_ANOMALY_DETECTOR_BATCH_GAMMA__COLUMN_NA`

- 行 251: `detection_method="]range["`
  → `detection_method = os.getenv("MONITORING_ANOMALY_DETECTOR_BATCH_GAMMA__DETECTION")`
  → 环境变量: `MONITORING_ANOMALY_DETECTOR_BATCH_GAMMA__DETECTION`

- 行 251: `description="]范围异常["`
  → `description = os.getenv("MONITORING_ANOMALY_DETECTOR_BATCH_GAMMA__DESCRIPTI")`
  → 环境变量: `MONITORING_ANOMALY_DETECTOR_BATCH_GAMMA__DESCRIPTI`

- 行 251: `table_name="]odds["`
  → `table_name = os.getenv("MONITORING_ANOMALY_DETECTOR_BATCH_GAMMA__TABLE_NAM")`
  → 环境变量: `MONITORING_ANOMALY_DETECTOR_BATCH_GAMMA__TABLE_NAM`

- 行 251: `column_name="]home_odds["`
  → `column_name = os.getenv("MONITORING_ANOMALY_DETECTOR_BATCH_GAMMA__COLUMN_NA")`
  → 环境变量: `MONITORING_ANOMALY_DETECTOR_BATCH_GAMMA__COLUMN_NA`

- 行 251: `anomalous_values="]abnormal["`
  → `anomalous_values = os.getenv("MONITORING_ANOMALY_DETECTOR_BATCH_GAMMA__ANOMALOUS")`
  → 环境变量: `MONITORING_ANOMALY_DETECTOR_BATCH_GAMMA__ANOMALOUS`

- 行 251: `detection_method="]frequency["`
  → `detection_method = os.getenv("MONITORING_ANOMALY_DETECTOR_BATCH_GAMMA__DETECTION")`
  → 环境变量: `MONITORING_ANOMALY_DETECTOR_BATCH_GAMMA__DETECTION`

- 行 252: `description="]频率异常["`
  → `description = os.getenv("MONITORING_ANOMALY_DETECTOR_BATCH_GAMMA__DESCRIPTI")`
  → 环境变量: `MONITORING_ANOMALY_DETECTOR_BATCH_GAMMA__DESCRIPTI`

- 行 271: `column_name="]test_column["`
  → `column_name = os.getenv("MONITORING_ANOMALY_DETECTOR_BATCH_GAMMA__COLUMN_NA")`
  → 环境变量: `MONITORING_ANOMALY_DETECTOR_BATCH_GAMMA__COLUMN_NA`

- 行 274: `detection_method="]test["`
  → `detection_method = os.getenv("MONITORING_ANOMALY_DETECTOR_BATCH_GAMMA__DETECTION")`
  → 环境变量: `MONITORING_ANOMALY_DETECTOR_BATCH_GAMMA__DETECTION`

- 行 275: `description="]test["`
  → `description = os.getenv("MONITORING_ANOMALY_DETECTOR_BATCH_GAMMA__DESCRIPTI")`
  → 环境变量: `MONITORING_ANOMALY_DETECTOR_BATCH_GAMMA__DESCRIPTI`

- 行 280: `table_name="]]test["`
  → `table_name = os.getenv("MONITORING_ANOMALY_DETECTOR_BATCH_GAMMA__TABLE_NAM")`
  → 环境变量: `MONITORING_ANOMALY_DETECTOR_BATCH_GAMMA__TABLE_NAM`

- 行 280: `column_name="]test_column["`
  → `column_name = os.getenv("MONITORING_ANOMALY_DETECTOR_BATCH_GAMMA__COLUMN_NA")`
  → 环境变量: `MONITORING_ANOMALY_DETECTOR_BATCH_GAMMA__COLUMN_NA`

- 行 283: `detection_method="]test["`
  → `detection_method = os.getenv("MONITORING_ANOMALY_DETECTOR_BATCH_GAMMA__DETECTION")`
  → 环境变量: `MONITORING_ANOMALY_DETECTOR_BATCH_GAMMA__DETECTION`

- 行 283: `description="]test["`
  → `description = os.getenv("MONITORING_ANOMALY_DETECTOR_BATCH_GAMMA__DESCRIPTI")`
  → 环境变量: `MONITORING_ANOMALY_DETECTOR_BATCH_GAMMA__DESCRIPTI`

- 行 289: `table_names="]matches["`
  → `table_names = os.getenv("MONITORING_ANOMALY_DETECTOR_BATCH_GAMMA__TABLE_NAM")`
  → 环境变量: `MONITORING_ANOMALY_DETECTOR_BATCH_GAMMA__TABLE_NAM`

### tests/legacy/unit/test_main_coverage.py

- 行 37: `expected_title = "足球预测API["`
  → `expected_title = os.getenv("TEST_MAIN_COVERAGE_EXPECTED_TITLE_37")`
  → 环境变量: `TEST_MAIN_COVERAGE_EXPECTED_TITLE_37`

- 行 37: `expected_description = "]基于机器学习的足球比赛结果预测系统["`
  → `expected_description = os.getenv("TEST_MAIN_COVERAGE_EXPECTED_DESCRIPTION_37")`
  → 环境变量: `TEST_MAIN_COVERAGE_EXPECTED_DESCRIPTION_37`

- 行 37: `expected_version = "]1.0.0["`
  → `expected_version = os.getenv("TEST_MAIN_COVERAGE_EXPECTED_VERSION_37")`
  → 环境变量: `TEST_MAIN_COVERAGE_EXPECTED_VERSION_37`

- 行 37: `expected_docs_url = "]_docs["`
  → `expected_docs_url = os.getenv("TEST_MAIN_COVERAGE_EXPECTED_DOCS_URL_37")`
  → 环境变量: `TEST_MAIN_COVERAGE_EXPECTED_DOCS_URL_37`

- 行 37: `expected_redoc_url = "]/redoc["`
  → `expected_redoc_url = os.getenv("TEST_MAIN_COVERAGE_EXPECTED_REDOC_URL_37")`
  → 环境变量: `TEST_MAIN_COVERAGE_EXPECTED_REDOC_URL_37`

- 行 92: `default_host = "]0.0.0.0["`
  → `default_host = os.getenv("TEST_MAIN_COVERAGE_DEFAULT_HOST_92")`
  → 环境变量: `TEST_MAIN_COVERAGE_DEFAULT_HOST_92`

- 行 92: `default_host = "]127.0.0.1["`
  → `default_host = os.getenv("TEST_MAIN_COVERAGE_DEFAULT_HOST_92")`
  → 环境变量: `TEST_MAIN_COVERAGE_DEFAULT_HOST_92`

- 行 93: `expected_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s["`
  → `expected_format = os.getenv("TEST_MAIN_COVERAGE_EXPECTED_FORMAT_93")`
  → 环境变量: `TEST_MAIN_COVERAGE_EXPECTED_FORMAT_93`

- 行 100: `title="足球预测API["`
  → `title = os.getenv("TEST_MAIN_COVERAGE_TITLE_100")`
  → 环境变量: `TEST_MAIN_COVERAGE_TITLE_100`

- 行 101: `description="]基于机器学习的足球比赛结果预测系统["`
  → `description = os.getenv("TEST_MAIN_COVERAGE_DESCRIPTION_101")`
  → 环境变量: `TEST_MAIN_COVERAGE_DESCRIPTION_101`

- 行 101: `version="]1.0.0["`
  → `version = os.getenv("TEST_MAIN_COVERAGE_VERSION_101")`
  → 环境变量: `TEST_MAIN_COVERAGE_VERSION_101`

- 行 102: `docs_url="]_docs["`
  → `docs_url = os.getenv("TEST_MAIN_COVERAGE_DOCS_URL_102")`
  → 环境变量: `TEST_MAIN_COVERAGE_DOCS_URL_102`

- 行 102: `redoc_url="]/redoc["`
  → `redoc_url = os.getenv("TEST_MAIN_COVERAGE_REDOC_URL_102")`
  → 环境变量: `TEST_MAIN_COVERAGE_REDOC_URL_102`

### tests/legacy/unit/test_kafka_consumer_phase4.py

- 行 30: `return_value = "]matches["`
  → `return_value = os.getenv("TEST_KAFKA_CONSUMER_PHASE4_RETURN_VALUE_30")`
  → 环境变量: `TEST_KAFKA_CONSUMER_PHASE4_RETURN_VALUE_30`

- 行 38: `return_value = "]matches["`
  → `return_value = os.getenv("TEST_KAFKA_CONSUMER_PHASE4_RETURN_VALUE_38")`
  → 环境变量: `TEST_KAFKA_CONSUMER_PHASE4_RETURN_VALUE_38`

- 行 51: `return_value = "]]broker unavailable["`
  → `return_value = os.getenv("TEST_KAFKA_CONSUMER_PHASE4_RETURN_VALUE_51")`
  → 环境变量: `TEST_KAFKA_CONSUMER_PHASE4_RETURN_VALUE_51`

### tests/legacy/unit/test_lineage_reporter.py

- 行 14: `marquez_url = "http//test-marquez5000["`
  → `marquez_url = os.getenv("TEST_LINEAGE_REPORTER_MARQUEZ_URL_14")`
  → 环境变量: `TEST_LINEAGE_REPORTER_MARQUEZ_URL_14`

- 行 26: `job_name="test_job["`
  → `job_name = os.getenv("TEST_LINEAGE_REPORTER_JOB_NAME_26")`
  → 环境变量: `TEST_LINEAGE_REPORTER_JOB_NAME_26`

- 行 26: `job_type="]BATCH["`
  → `job_type = os.getenv("TEST_LINEAGE_REPORTER_JOB_TYPE_26")`
  → 环境变量: `TEST_LINEAGE_REPORTER_JOB_TYPE_26`

- 行 26: `description="Test job description["`
  → `description = os.getenv("TEST_LINEAGE_REPORTER_DESCRIPTION_26")`
  → 环境变量: `TEST_LINEAGE_REPORTER_DESCRIPTION_26`

- 行 26: `source_location="]test/location["`
  → `source_location = os.getenv("TEST_LINEAGE_REPORTER_SOURCE_LOCATION_26")`
  → 环境变量: `TEST_LINEAGE_REPORTER_SOURCE_LOCATION_26`

- 行 26: `transformation_sql="]SELECT * FROM test["`
  → `transformation_sql = os.getenv("TEST_LINEAGE_REPORTER_TRANSFORMATION_SQL_26")`
  → 环境变量: `TEST_LINEAGE_REPORTER_TRANSFORMATION_SQL_26`

- 行 34: `test_run_id = "test-run-id-123["`
  → `test_run_id = os.getenv("TEST_LINEAGE_REPORTER_TEST_RUN_ID_34")`
  → 环境变量: `TEST_LINEAGE_REPORTER_TEST_RUN_ID_34`

- 行 38: `job_name="]]test_job["`
  → `job_name = os.getenv("TEST_LINEAGE_REPORTER_JOB_NAME_38")`
  → 环境变量: `TEST_LINEAGE_REPORTER_JOB_NAME_38`

- 行 46: `test_run_id = "test-run-id-456["`
  → `test_run_id = os.getenv("TEST_LINEAGE_REPORTER_TEST_RUN_ID_46")`
  → 环境变量: `TEST_LINEAGE_REPORTER_TEST_RUN_ID_46`

- 行 50: `job_name="]]test_job["`
  → `job_name = os.getenv("TEST_LINEAGE_REPORTER_JOB_NAME_50")`
  → 环境变量: `TEST_LINEAGE_REPORTER_JOB_NAME_50`

- 行 56: `job_name="nonexistent_job["`
  → `job_name = os.getenv("TEST_LINEAGE_REPORTER_JOB_NAME_56")`
  → 环境变量: `TEST_LINEAGE_REPORTER_JOB_NAME_56`

- 行 61: `test_run_id = "test-run-id-789["`
  → `test_run_id = os.getenv("TEST_LINEAGE_REPORTER_TEST_RUN_ID_61")`
  → 环境变量: `TEST_LINEAGE_REPORTER_TEST_RUN_ID_61`

- 行 62: `job_name="]]test_job["`
  → `job_name = os.getenv("TEST_LINEAGE_REPORTER_JOB_NAME_62")`
  → 环境变量: `TEST_LINEAGE_REPORTER_JOB_NAME_62`

- 行 62: `error_message="]Test error occurred["`
  → `error_message = os.getenv("TEST_LINEAGE_REPORTER_ERROR_MESSAGE_62")`
  → 环境变量: `TEST_LINEAGE_REPORTER_ERROR_MESSAGE_62`

- 行 72: `test_run_id = "test-run-id-999["`
  → `test_run_id = os.getenv("TEST_LINEAGE_REPORTER_TEST_RUN_ID_72")`
  → 环境变量: `TEST_LINEAGE_REPORTER_TEST_RUN_ID_72`

- 行 75: `job_name="]]test_job["`
  → `job_name = os.getenv("TEST_LINEAGE_REPORTER_JOB_NAME_75")`
  → 环境变量: `TEST_LINEAGE_REPORTER_JOB_NAME_75`

- 行 75: `error_message="]Test error occurred["`
  → `error_message = os.getenv("TEST_LINEAGE_REPORTER_ERROR_MESSAGE_75")`
  → 环境变量: `TEST_LINEAGE_REPORTER_ERROR_MESSAGE_75`

- 行 82: `job_name="nonexistent_job["`
  → `job_name = os.getenv("TEST_LINEAGE_REPORTER_JOB_NAME_82")`
  → 环境变量: `TEST_LINEAGE_REPORTER_JOB_NAME_82`

- 行 82: `error_message="]Test error occurred["`
  → `error_message = os.getenv("TEST_LINEAGE_REPORTER_ERROR_MESSAGE_82")`
  → 环境变量: `TEST_LINEAGE_REPORTER_ERROR_MESSAGE_82`

- 行 89: `source_name="test_source["`
  → `source_name = os.getenv("TEST_LINEAGE_REPORTER_SOURCE_NAME_89")`
  → 环境变量: `TEST_LINEAGE_REPORTER_SOURCE_NAME_89`

- 行 90: `target_table="]test_table["`
  → `target_table = os.getenv("TEST_LINEAGE_REPORTER_TARGET_TABLE_90")`
  → 环境变量: `TEST_LINEAGE_REPORTER_TARGET_TABLE_90`

- 行 102: `target_table="]result_table["`
  → `target_table = os.getenv("TEST_LINEAGE_REPORTER_TARGET_TABLE_102")`
  → 环境变量: `TEST_LINEAGE_REPORTER_TARGET_TABLE_102`

- 行 102: `transformation_sql="]SELECT * FROM table1 JOIN table2["`
  → `transformation_sql = os.getenv("TEST_LINEAGE_REPORTER_TRANSFORMATION_SQL_102")`
  → 环境变量: `TEST_LINEAGE_REPORTER_TRANSFORMATION_SQL_102`

- 行 102: `transformation_type="]JOIN["`
  → `transformation_type = os.getenv("TEST_LINEAGE_REPORTER_TRANSFORMATION_TYPE_102")`
  → 环境变量: `TEST_LINEAGE_REPORTER_TRANSFORMATION_TYPE_102`

- 行 128: `job_name="child_job["`
  → `job_name = os.getenv("TEST_LINEAGE_REPORTER_JOB_NAME_128")`
  → 环境变量: `TEST_LINEAGE_REPORTER_JOB_NAME_128`

- 行 129: `parent_run_id="]parent-run-id-123["`
  → `parent_run_id = os.getenv("TEST_LINEAGE_REPORTER_PARENT_RUN_ID_129")`
  → 环境变量: `TEST_LINEAGE_REPORTER_PARENT_RUN_ID_129`

- 行 137: `match = "]Client error["`
  → `match = os.getenv("TEST_LINEAGE_REPORTER_MATCH_137")`
  → 环境变量: `TEST_LINEAGE_REPORTER_MATCH_137`

- 行 139: `job_name="]failing_job["`
  → `job_name = os.getenv("TEST_LINEAGE_REPORTER_JOB_NAME_139")`
  → 环境变量: `TEST_LINEAGE_REPORTER_JOB_NAME_139`

- 行 147: `test_run_id = "]test-run-id-exception["`
  → `test_run_id = os.getenv("TEST_LINEAGE_REPORTER_TEST_RUN_ID_147")`
  → 环境变量: `TEST_LINEAGE_REPORTER_TEST_RUN_ID_147`

- 行 149: `job_name="]]test_job["`
  → `job_name = os.getenv("TEST_LINEAGE_REPORTER_JOB_NAME_149")`
  → 环境变量: `TEST_LINEAGE_REPORTER_JOB_NAME_149`

- 行 157: `test_run_id = "]test-run-id-exception["`
  → `test_run_id = os.getenv("TEST_LINEAGE_REPORTER_TEST_RUN_ID_157")`
  → 环境变量: `TEST_LINEAGE_REPORTER_TEST_RUN_ID_157`

- 行 160: `job_name="]]test_job["`
  → `job_name = os.getenv("TEST_LINEAGE_REPORTER_JOB_NAME_160")`
  → 环境变量: `TEST_LINEAGE_REPORTER_JOB_NAME_160`

- 行 160: `error_message="]Test error["`
  → `error_message = os.getenv("TEST_LINEAGE_REPORTER_ERROR_MESSAGE_160")`
  → 环境变量: `TEST_LINEAGE_REPORTER_ERROR_MESSAGE_160`

### tests/legacy/unit/monitoring_quality_monitor_batch_gamma_.py

- 行 32: `table_name="matches["`
  → `table_name = os.getenv("MONITORING_QUALITY_MONITOR_BATCH_GAMMA__TABLE_NAME")`
  → 环境变量: `MONITORING_QUALITY_MONITOR_BATCH_GAMMA__TABLE_NAME`

- 行 74: `table_name="test_table["`
  → `table_name = os.getenv("MONITORING_QUALITY_MONITOR_BATCH_GAMMA__TABLE_NAME")`
  → 环境变量: `MONITORING_QUALITY_MONITOR_BATCH_GAMMA__TABLE_NAME`

- 行 98: `table_name="test_table["`
  → `table_name = os.getenv("MONITORING_QUALITY_MONITOR_BATCH_GAMMA__TABLE_NAME")`
  → 环境变量: `MONITORING_QUALITY_MONITOR_BATCH_GAMMA__TABLE_NAME`

### tests/legacy/unit/test_tasks_basic.py

- 行 96: `task_name="test_task["`
  → `task_name = os.getenv("TEST_TASKS_BASIC_TASK_NAME_96")`
  → 环境变量: `TEST_TASKS_BASIC_TASK_NAME_96`

- 行 96: `error_type="]task_error["`
  → `error_type = os.getenv("TEST_TASKS_BASIC_ERROR_TYPE_96")`
  → 环境变量: `TEST_TASKS_BASIC_ERROR_TYPE_96`

### tests/legacy/unit/api/test_api_schemas.py

- 行 17: `status="healthy"`
  → `status = os.getenv("TEST_API_SCHEMAS_STATUS_17")`
  → 环境变量: `TEST_API_SCHEMAS_STATUS_17`

- 行 18: `service="football-prediction-api"`
  → `service = os.getenv("TEST_API_SCHEMAS_SERVICE_18")`
  → 环境变量: `TEST_API_SCHEMAS_SERVICE_18`

- 行 24: `status="healthy"`
  → `status = os.getenv("TEST_API_SCHEMAS_STATUS_24")`
  → 环境变量: `TEST_API_SCHEMAS_STATUS_24`

### tests/legacy/unit/utils/test_data_validator.py

- 行 11: `text = "]<script>alert('`
  → `text = os.getenv("TEST_DATA_VALIDATOR_TEXT_11")`
  → 环境变量: `TEST_DATA_VALIDATOR_TEXT_11`

### tests/legacy/unit/utils/test_response_utils.py

- 行 8: `message="]]bad["`
  → `message = os.getenv("TEST_RESPONSE_UTILS_MESSAGE_8")`
  → 环境变量: `TEST_RESPONSE_UTILS_MESSAGE_8`

### tests/legacy/unit/utils/test_retry.py

- 行 91: `match = "]Permanent failure["`
  → `match = os.getenv("TEST_RETRY_MATCH_91")`
  → 环境变量: `TEST_RETRY_MATCH_91`

- 行 102: `match = "]Failure["`
  → `match = os.getenv("TEST_RETRY_MATCH_102")`
  → 环境变量: `TEST_RETRY_MATCH_102`

- 行 136: `match = "]Permanent failure["`
  → `match = os.getenv("TEST_RETRY_MATCH_136")`
  → 环境变量: `TEST_RETRY_MATCH_136`

- 行 176: `match = "]Circuit breaker is OPEN["`
  → `match = os.getenv("TEST_RETRY_MATCH_176")`
  → 环境变量: `TEST_RETRY_MATCH_176`

### tests/legacy/unit/utils/test_crypto_utils.py

- 行 11: `algorithm="]unknown["`
  → `algorithm = os.getenv("TEST_CRYPTO_UTILS_ALGORITHM_11")`
  → 环境变量: `TEST_CRYPTO_UTILS_ALGORITHM_11`

- 行 11: `salt = "]testsalt["`
  → `salt = os.getenv("TEST_CRYPTO_UTILS_SALT_11")`
  → 环境变量: `TEST_CRYPTO_UTILS_SALT_11`

### tests/legacy/unit/utils/test_utils_comprehensive.py

- 行 10: `password = "test_password["`
  → `password = os.getenv("TEST_UTILS_COMPREHENSIVE_PASSWORD_10")`
  → 环境变量: `TEST_UTILS_COMPREHENSIVE_PASSWORD_10`

- 行 12: `password = "test_password["`
  → `password = os.getenv("TEST_UTILS_COMPREHENSIVE_PASSWORD_12")`
  → 环境变量: `TEST_UTILS_COMPREHENSIVE_PASSWORD_12`

- 行 14: `password = "test_password["`
  → `password = os.getenv("TEST_UTILS_COMPREHENSIVE_PASSWORD_14")`
  → 环境变量: `TEST_UTILS_COMPREHENSIVE_PASSWORD_14`

- 行 14: `wrong_password = "]wrong_password["`
  → `wrong_password = os.getenv("TEST_UTILS_COMPREHENSIVE_WRONG_PASSWORD_14")`
  → 环境变量: `TEST_UTILS_COMPREHENSIVE_WRONG_PASSWORD_14`

- 行 34: `password1 = "password1["`
  → `password1 = os.getenv("TEST_UTILS_COMPREHENSIVE_PASSWORD1_34")`
  → 环境变量: `TEST_UTILS_COMPREHENSIVE_PASSWORD1_34`

- 行 34: `password2 = "]password2["`
  → `password2 = os.getenv("TEST_UTILS_COMPREHENSIVE_PASSWORD2_34")`
  → 环境变量: `TEST_UTILS_COMPREHENSIVE_PASSWORD2_34`

- 行 37: `password = "same_password["`
  → `password = os.getenv("TEST_UTILS_COMPREHENSIVE_PASSWORD_37")`
  → 环境变量: `TEST_UTILS_COMPREHENSIVE_PASSWORD_37`

### tests/legacy/unit/utils/test_utils.py

- 行 25: `suffix="].json["`
  → `suffix = os.getenv("TEST_UTILS_SUFFIX_25")`
  → 环境变量: `TEST_UTILS_SUFFIX_25`

- 行 29: `match = "无法读取JSON文件["`
  → `match = os.getenv("TEST_UTILS_MATCH_29")`
  → 环境变量: `TEST_UTILS_MATCH_29`

- 行 31: `suffix="].json["`
  → `suffix = os.getenv("TEST_UTILS_SUFFIX_31")`
  → 环境变量: `TEST_UTILS_SUFFIX_31`

- 行 31: `match = "]无法读取JSON文件["`
  → `match = os.getenv("TEST_UTILS_MATCH_31")`
  → 环境变量: `TEST_UTILS_MATCH_31`

- 行 33: `encoding = "]utf-8["`
  → `encoding = os.getenv("TEST_UTILS_ENCODING_33")`
  → 环境变量: `TEST_UTILS_ENCODING_33`

- 行 40: `test_content = "]]test content["`
  → `test_content = os.getenv("TEST_UTILS_TEST_CONTENT_40")`
  → 环境变量: `TEST_UTILS_TEST_CONTENT_40`

- 行 130: `text = "test string["`
  → `text = os.getenv("TEST_UTILS_TEXT_130")`
  → 环境变量: `TEST_UTILS_TEXT_130`

- 行 134: `text = "test string["`
  → `text = os.getenv("TEST_UTILS_TEXT_134")`
  → 环境变量: `TEST_UTILS_TEXT_134`

- 行 137: `match = "不支持的哈希算法["`
  → `match = os.getenv("TEST_UTILS_MATCH_137")`
  → 环境变量: `TEST_UTILS_MATCH_137`

- 行 140: `password = "test_password["`
  → `password = os.getenv("TEST_UTILS_PASSWORD_140")`
  → 环境变量: `TEST_UTILS_PASSWORD_140`

- 行 142: `salt = "]fixed_salt["`
  → `salt = os.getenv("TEST_UTILS_SALT_142")`
  → 环境变量: `TEST_UTILS_SALT_142`

- 行 148: `text = "short["`
  → `text = os.getenv("TEST_UTILS_TEXT_148")`
  → 环境变量: `TEST_UTILS_TEXT_148`

- 行 150: `text = "这是一个很长的字符串需要被截断["`
  → `text = os.getenv("TEST_UTILS_TEXT_150")`
  → 环境变量: `TEST_UTILS_TEXT_150`

- 行 153: `text = "Hello World Test["`
  → `text = os.getenv("TEST_UTILS_TEXT_153")`
  → 环境变量: `TEST_UTILS_TEXT_153`

- 行 166: `text = "  这是   一个\t测试\n文本  "`
  → `text = os.getenv("TEST_UTILS_TEXT_166")`
  → 环境变量: `TEST_UTILS_TEXT_166`

### tests/legacy/unit/utils/test_utils_dict.py

- 行 29: `parent_key="]parent["`
  → `parent_key = os.getenv("TEST_UTILS_DICT_PARENT_KEY_29")`
  → 环境变量: `TEST_UTILS_DICT_PARENT_KEY_29`

### tests/legacy/unit/utils/test_file_utils.py

- 行 13: `encoding="]utf-8["`
  → `encoding = os.getenv("TEST_FILE_UTILS_ENCODING_13")`
  → 环境变量: `TEST_FILE_UTILS_ENCODING_13`

### tests/legacy/unit/utils/test_response.py

- 行 22: `code="]SUCCESS["`
  → `code = os.getenv("TEST_RESPONSE_CODE_22")`
  → 环境变量: `TEST_RESPONSE_CODE_22`

- 行 43: `message="]操作成功["`
  → `message = os.getenv("TEST_RESPONSE_MESSAGE_43")`
  → 环境变量: `TEST_RESPONSE_MESSAGE_43`

- 行 47: `message="]操作成功["`
  → `message = os.getenv("TEST_RESPONSE_MESSAGE_47")`
  → 环境变量: `TEST_RESPONSE_MESSAGE_47`

- 行 64: `code="]SUCCESS["`
  → `code = os.getenv("TEST_RESPONSE_CODE_64")`
  → 环境变量: `TEST_RESPONSE_CODE_64`

- 行 91: `message="自定义成功消息["`
  → `message = os.getenv("TEST_RESPONSE_MESSAGE_91")`
  → 环境变量: `TEST_RESPONSE_MESSAGE_91`

- 行 96: `message = "]用户数据获取成功["`
  → `message = os.getenv("TEST_RESPONSE_MESSAGE_96")`
  → 环境变量: `TEST_RESPONSE_MESSAGE_96`

- 行 110: `message="]别名方法测试["`
  → `message = os.getenv("TEST_RESPONSE_MESSAGE_110")`
  → 环境变量: `TEST_RESPONSE_MESSAGE_110`

- 行 153: `message="]别名方法错误["`
  → `message = os.getenv("TEST_RESPONSE_MESSAGE_153")`
  → 环境变量: `TEST_RESPONSE_MESSAGE_153`

- 行 198: `message="测试特殊字符["`
  → `message = os.getenv("TEST_RESPONSE_MESSAGE_198")`
  → 环境变量: `TEST_RESPONSE_MESSAGE_198`

- 行 202: `message="]Unicode测试]"`
  → `message = os.getenv("TEST_RESPONSE_MESSAGE_202")`
  → 环境变量: `TEST_RESPONSE_MESSAGE_202`

### tests/legacy/unit/monitoring/test_quality_monitor_batch_omega_001.py

- 行 41: `table_name="matches["`
  → `table_name = os.getenv("TEST_QUALITY_MONITOR_BATCH_OMEGA_001_TABLE_NAME_41")`
  → 环境变量: `TEST_QUALITY_MONITOR_BATCH_OMEGA_001_TABLE_NAME_41`

- 行 48: `table_name="matches["`
  → `table_name = os.getenv("TEST_QUALITY_MONITOR_BATCH_OMEGA_001_TABLE_NAME_48")`
  → 环境变量: `TEST_QUALITY_MONITOR_BATCH_OMEGA_001_TABLE_NAME_48`

- 行 67: `table_name="matches["`
  → `table_name = os.getenv("TEST_QUALITY_MONITOR_BATCH_OMEGA_001_TABLE_NAME_67")`
  → 环境变量: `TEST_QUALITY_MONITOR_BATCH_OMEGA_001_TABLE_NAME_67`

- 行 81: `table_name="matches["`
  → `table_name = os.getenv("TEST_QUALITY_MONITOR_BATCH_OMEGA_001_TABLE_NAME_81")`
  → 环境变量: `TEST_QUALITY_MONITOR_BATCH_OMEGA_001_TABLE_NAME_81`

- 行 90: `table_name="matches["`
  → `table_name = os.getenv("TEST_QUALITY_MONITOR_BATCH_OMEGA_001_TABLE_NAME_90")`
  → 环境变量: `TEST_QUALITY_MONITOR_BATCH_OMEGA_001_TABLE_NAME_90`

- 行 99: `table_name="]matches["`
  → `table_name = os.getenv("TEST_QUALITY_MONITOR_BATCH_OMEGA_001_TABLE_NAME_99")`
  → 环境变量: `TEST_QUALITY_MONITOR_BATCH_OMEGA_001_TABLE_NAME_99`

- 行 107: `table_name="]matches["`
  → `table_name = os.getenv("TEST_QUALITY_MONITOR_BATCH_OMEGA_001_TABLE_NAME_10")`
  → 环境变量: `TEST_QUALITY_MONITOR_BATCH_OMEGA_001_TABLE_NAME_10`

- 行 118: `table_name="matches["`
  → `table_name = os.getenv("TEST_QUALITY_MONITOR_BATCH_OMEGA_001_TABLE_NAME_11")`
  → 环境变量: `TEST_QUALITY_MONITOR_BATCH_OMEGA_001_TABLE_NAME_11`

- 行 146: `table_name="matches["`
  → `table_name = os.getenv("TEST_QUALITY_MONITOR_BATCH_OMEGA_001_TABLE_NAME_14")`
  → 环境变量: `TEST_QUALITY_MONITOR_BATCH_OMEGA_001_TABLE_NAME_14`

- 行 163: `table_name="matches["`
  → `table_name = os.getenv("TEST_QUALITY_MONITOR_BATCH_OMEGA_001_TABLE_NAME_16")`
  → 环境变量: `TEST_QUALITY_MONITOR_BATCH_OMEGA_001_TABLE_NAME_16`

- 行 210: `table_name="]test["`
  → `table_name = os.getenv("TEST_QUALITY_MONITOR_BATCH_OMEGA_001_TABLE_NAME_21")`
  → 环境变量: `TEST_QUALITY_MONITOR_BATCH_OMEGA_001_TABLE_NAME_21`

- 行 225: `table_name="]]test["`
  → `table_name = os.getenv("TEST_QUALITY_MONITOR_BATCH_OMEGA_001_TABLE_NAME_22")`
  → 环境变量: `TEST_QUALITY_MONITOR_BATCH_OMEGA_001_TABLE_NAME_22`

- 行 238: `table_name="big_table["`
  → `table_name = os.getenv("TEST_QUALITY_MONITOR_BATCH_OMEGA_001_TABLE_NAME_23")`
  → 环境变量: `TEST_QUALITY_MONITOR_BATCH_OMEGA_001_TABLE_NAME_23`

- 行 246: `table_name="]big_table["`
  → `table_name = os.getenv("TEST_QUALITY_MONITOR_BATCH_OMEGA_001_TABLE_NAME_24")`
  → 环境变量: `TEST_QUALITY_MONITOR_BATCH_OMEGA_001_TABLE_NAME_24`

- 行 315: `table_name="matches["`
  → `table_name = os.getenv("TEST_QUALITY_MONITOR_BATCH_OMEGA_001_TABLE_NAME_31")`
  → 环境变量: `TEST_QUALITY_MONITOR_BATCH_OMEGA_001_TABLE_NAME_31`

### tests/legacy/unit/monitoring/test_anomaly_detector_batch_omega_003.py

- 行 171: `table_name="matches["`
  → `table_name = os.getenv("TEST_ANOMALY_DETECTOR_BATCH_OMEGA_003_TABLE_NAME_1")`
  → 环境变量: `TEST_ANOMALY_DETECTOR_BATCH_OMEGA_003_TABLE_NAME_1`

- 行 171: `column_name="]home_score["`
  → `column_name = os.getenv("TEST_ANOMALY_DETECTOR_BATCH_OMEGA_003_COLUMN_NAME_")`
  → 环境变量: `TEST_ANOMALY_DETECTOR_BATCH_OMEGA_003_COLUMN_NAME_`

- 行 171: `detection_method="]3sigma["`
  → `detection_method = os.getenv("TEST_ANOMALY_DETECTOR_BATCH_OMEGA_003_DETECTION_ME")`
  → 环境变量: `TEST_ANOMALY_DETECTOR_BATCH_OMEGA_003_DETECTION_ME`

- 行 171: `description="]异常高分值["`
  → `description = os.getenv("TEST_ANOMALY_DETECTOR_BATCH_OMEGA_003_DESCRIPTION_")`
  → 环境变量: `TEST_ANOMALY_DETECTOR_BATCH_OMEGA_003_DESCRIPTION_`

- 行 180: `table_name="matches["`
  → `table_name = os.getenv("TEST_ANOMALY_DETECTOR_BATCH_OMEGA_003_TABLE_NAME_1")`
  → 环境变量: `TEST_ANOMALY_DETECTOR_BATCH_OMEGA_003_TABLE_NAME_1`

- 行 180: `column_name="]home_score["`
  → `column_name = os.getenv("TEST_ANOMALY_DETECTOR_BATCH_OMEGA_003_COLUMN_NAME_")`
  → 环境变量: `TEST_ANOMALY_DETECTOR_BATCH_OMEGA_003_COLUMN_NAME_`

- 行 183: `detection_method="]3sigma["`
  → `detection_method = os.getenv("TEST_ANOMALY_DETECTOR_BATCH_OMEGA_003_DETECTION_ME")`
  → 环境变量: `TEST_ANOMALY_DETECTOR_BATCH_OMEGA_003_DETECTION_ME`

- 行 184: `description="]异常高分值["`
  → `description = os.getenv("TEST_ANOMALY_DETECTOR_BATCH_OMEGA_003_DESCRIPTION_")`
  → 环境变量: `TEST_ANOMALY_DETECTOR_BATCH_OMEGA_003_DESCRIPTION_`

- 行 297: `methods = "frequency["`
  → `methods = os.getenv("TEST_ANOMALY_DETECTOR_BATCH_OMEGA_003_METHODS_297")`
  → 环境变量: `TEST_ANOMALY_DETECTOR_BATCH_OMEGA_003_METHODS_297`

- 行 399: `table_names="matches["`
  → `table_names = os.getenv("TEST_ANOMALY_DETECTOR_BATCH_OMEGA_003_TABLE_NAMES_")`
  → 环境变量: `TEST_ANOMALY_DETECTOR_BATCH_OMEGA_003_TABLE_NAMES_`

- 行 424: `table_name="matches["`
  → `table_name = os.getenv("TEST_ANOMALY_DETECTOR_BATCH_OMEGA_003_TABLE_NAME_4")`
  → 环境变量: `TEST_ANOMALY_DETECTOR_BATCH_OMEGA_003_TABLE_NAME_4`

- 行 425: `column_name="]home_score["`
  → `column_name = os.getenv("TEST_ANOMALY_DETECTOR_BATCH_OMEGA_003_COLUMN_NAME_")`
  → 环境变量: `TEST_ANOMALY_DETECTOR_BATCH_OMEGA_003_COLUMN_NAME_`

- 行 425: `detection_method="]3sigma["`
  → `detection_method = os.getenv("TEST_ANOMALY_DETECTOR_BATCH_OMEGA_003_DETECTION_ME")`
  → 环境变量: `TEST_ANOMALY_DETECTOR_BATCH_OMEGA_003_DETECTION_ME`

- 行 427: `table_name="]odds["`
  → `table_name = os.getenv("TEST_ANOMALY_DETECTOR_BATCH_OMEGA_003_TABLE_NAME_4")`
  → 环境变量: `TEST_ANOMALY_DETECTOR_BATCH_OMEGA_003_TABLE_NAME_4`

- 行 427: `column_name="]home_odds["`
  → `column_name = os.getenv("TEST_ANOMALY_DETECTOR_BATCH_OMEGA_003_COLUMN_NAME_")`
  → 环境变量: `TEST_ANOMALY_DETECTOR_BATCH_OMEGA_003_COLUMN_NAME_`

- 行 429: `anomalous_values="]200.0["`
  → `anomalous_values = os.getenv("TEST_ANOMALY_DETECTOR_BATCH_OMEGA_003_ANOMALOUS_VA")`
  → 环境变量: `TEST_ANOMALY_DETECTOR_BATCH_OMEGA_003_ANOMALOUS_VA`

- 行 430: `detection_method="]range["`
  → `detection_method = os.getenv("TEST_ANOMALY_DETECTOR_BATCH_OMEGA_003_DETECTION_ME")`
  → 环境变量: `TEST_ANOMALY_DETECTOR_BATCH_OMEGA_003_DETECTION_ME`

- 行 431: `description="]超出范围["`
  → `description = os.getenv("TEST_ANOMALY_DETECTOR_BATCH_OMEGA_003_DESCRIPTION_")`
  → 环境变量: `TEST_ANOMALY_DETECTOR_BATCH_OMEGA_003_DESCRIPTION_`

### tests/legacy/unit/monitoring/test_quality_monitor_basic.py

- 行 46: `table_name="]matches["`
  → `table_name = os.getenv("TEST_QUALITY_MONITOR_BASIC_TABLE_NAME_46")`
  → 环境变量: `TEST_QUALITY_MONITOR_BASIC_TABLE_NAME_46`

- 行 67: `table_name="]matches["`
  → `table_name = os.getenv("TEST_QUALITY_MONITOR_BASIC_TABLE_NAME_67")`
  → 环境变量: `TEST_QUALITY_MONITOR_BASIC_TABLE_NAME_67`

- 行 144: `table_name="test_table["`
  → `table_name = os.getenv("TEST_QUALITY_MONITOR_BASIC_TABLE_NAME_144")`
  → 环境变量: `TEST_QUALITY_MONITOR_BASIC_TABLE_NAME_144`

- 行 150: `table_name="test_table["`
  → `table_name = os.getenv("TEST_QUALITY_MONITOR_BASIC_TABLE_NAME_150")`
  → 环境变量: `TEST_QUALITY_MONITOR_BASIC_TABLE_NAME_150`

- 行 159: `table_name="test_table["`
  → `table_name = os.getenv("TEST_QUALITY_MONITOR_BASIC_TABLE_NAME_159")`
  → 环境变量: `TEST_QUALITY_MONITOR_BASIC_TABLE_NAME_159`

- 行 163: `table_name="test_table["`
  → `table_name = os.getenv("TEST_QUALITY_MONITOR_BASIC_TABLE_NAME_163")`
  → 环境变量: `TEST_QUALITY_MONITOR_BASIC_TABLE_NAME_163`

### tests/legacy/unit/monitoring/test_alert_manager.py

- 行 36: `alert_id="test-123["`
  → `alert_id = os.getenv("TEST_ALERT_MANAGER_ALERT_ID_36")`
  → 环境变量: `TEST_ALERT_MANAGER_ALERT_ID_36`

- 行 36: `title="]Test Alert["`
  → `title = os.getenv("TEST_ALERT_MANAGER_TITLE_36")`
  → 环境变量: `TEST_ALERT_MANAGER_TITLE_36`

- 行 36: `message="]This is a test alert["`
  → `message = os.getenv("TEST_ALERT_MANAGER_MESSAGE_36")`
  → 环境变量: `TEST_ALERT_MANAGER_MESSAGE_36`

- 行 36: `source="]test["`
  → `source = os.getenv("TEST_ALERT_MANAGER_SOURCE_36")`
  → 环境变量: `TEST_ALERT_MANAGER_SOURCE_36`

- 行 45: `alert_id="]test-456["`
  → `alert_id = os.getenv("TEST_ALERT_MANAGER_ALERT_ID_45")`
  → 环境变量: `TEST_ALERT_MANAGER_ALERT_ID_45`

- 行 45: `title="]Complete Alert["`
  → `title = os.getenv("TEST_ALERT_MANAGER_TITLE_45")`
  → 环境变量: `TEST_ALERT_MANAGER_TITLE_45`

- 行 45: `message = "]Complete alert with all params["`
  → `message = os.getenv("TEST_ALERT_MANAGER_MESSAGE_45")`
  → 环境变量: `TEST_ALERT_MANAGER_MESSAGE_45`

- 行 45: `source="]monitoring["`
  → `source = os.getenv("TEST_ALERT_MANAGER_SOURCE_45")`
  → 环境变量: `TEST_ALERT_MANAGER_SOURCE_45`

- 行 46: `alert_id="test-789["`
  → `alert_id = os.getenv("TEST_ALERT_MANAGER_ALERT_ID_46")`
  → 环境变量: `TEST_ALERT_MANAGER_ALERT_ID_46`

- 行 47: `title="]Dict Test["`
  → `title = os.getenv("TEST_ALERT_MANAGER_TITLE_47")`
  → 环境变量: `TEST_ALERT_MANAGER_TITLE_47`

- 行 47: `message="]Test dictionary conversion["`
  → `message = os.getenv("TEST_ALERT_MANAGER_MESSAGE_47")`
  → 环境变量: `TEST_ALERT_MANAGER_MESSAGE_47`

- 行 49: `source="]unittest["`
  → `source = os.getenv("TEST_ALERT_MANAGER_SOURCE_49")`
  → 环境变量: `TEST_ALERT_MANAGER_SOURCE_49`

- 行 57: `alert_id="test-resolve["`
  → `alert_id = os.getenv("TEST_ALERT_MANAGER_ALERT_ID_57")`
  → 环境变量: `TEST_ALERT_MANAGER_ALERT_ID_57`

- 行 57: `title="]Resolve Test["`
  → `title = os.getenv("TEST_ALERT_MANAGER_TITLE_57")`
  → 环境变量: `TEST_ALERT_MANAGER_TITLE_57`

- 行 58: `message="]Test resolution["`
  → `message = os.getenv("TEST_ALERT_MANAGER_MESSAGE_58")`
  → 环境变量: `TEST_ALERT_MANAGER_MESSAGE_58`

- 行 59: `source="]test["`
  → `source = os.getenv("TEST_ALERT_MANAGER_SOURCE_59")`
  → 环境变量: `TEST_ALERT_MANAGER_SOURCE_59`

- 行 63: `alert_id="test-silence["`
  → `alert_id = os.getenv("TEST_ALERT_MANAGER_ALERT_ID_63")`
  → 环境变量: `TEST_ALERT_MANAGER_ALERT_ID_63`

- 行 63: `title="]Silence Test["`
  → `title = os.getenv("TEST_ALERT_MANAGER_TITLE_63")`
  → 环境变量: `TEST_ALERT_MANAGER_TITLE_63`

- 行 63: `message="]Test silencing["`
  → `message = os.getenv("TEST_ALERT_MANAGER_MESSAGE_63")`
  → 环境变量: `TEST_ALERT_MANAGER_MESSAGE_63`

- 行 63: `source="]test["`
  → `source = os.getenv("TEST_ALERT_MANAGER_SOURCE_63")`
  → 环境变量: `TEST_ALERT_MANAGER_SOURCE_63`

- 行 67: `rule_id="rule-123["`
  → `rule_id = os.getenv("TEST_ALERT_MANAGER_RULE_ID_67")`
  → 环境变量: `TEST_ALERT_MANAGER_RULE_ID_67`

- 行 67: `name="]Test Rule["`
  → `name = os.getenv("TEST_ALERT_MANAGER_NAME_67")`
  → 环境变量: `TEST_ALERT_MANAGER_NAME_67`

- 行 68: `condition="]error_rate > 0.1["`
  → `condition = os.getenv("TEST_ALERT_MANAGER_CONDITION_68")`
  → 环境变量: `TEST_ALERT_MANAGER_CONDITION_68`

- 行 74: `rule_id="rule-default["`
  → `rule_id = os.getenv("TEST_ALERT_MANAGER_RULE_ID_74")`
  → 环境变量: `TEST_ALERT_MANAGER_RULE_ID_74`

- 行 74: `name="]Default Rule["`
  → `name = os.getenv("TEST_ALERT_MANAGER_NAME_74")`
  → 环境变量: `TEST_ALERT_MANAGER_NAME_74`

- 行 74: `condition="]cpu_usage > 80["`
  → `condition = os.getenv("TEST_ALERT_MANAGER_CONDITION_74")`
  → 环境变量: `TEST_ALERT_MANAGER_CONDITION_74`

- 行 128: `rule_id="custom_rule["`
  → `rule_id = os.getenv("TEST_ALERT_MANAGER_RULE_ID_128")`
  → 环境变量: `TEST_ALERT_MANAGER_RULE_ID_128`

- 行 128: `name="]Custom Rule["`
  → `name = os.getenv("TEST_ALERT_MANAGER_NAME_128")`
  → 环境变量: `TEST_ALERT_MANAGER_NAME_128`

- 行 128: `condition="]custom_condition["`
  → `condition = os.getenv("TEST_ALERT_MANAGER_CONDITION_128")`
  → 环境变量: `TEST_ALERT_MANAGER_CONDITION_128`

- 行 143: `title="Test Alert["`
  → `title = os.getenv("TEST_ALERT_MANAGER_TITLE_143")`
  → 环境变量: `TEST_ALERT_MANAGER_TITLE_143`

- 行 143: `message="]This is a test["`
  → `message = os.getenv("TEST_ALERT_MANAGER_MESSAGE_143")`
  → 环境变量: `TEST_ALERT_MANAGER_MESSAGE_143`

- 行 144: `source="]test["`
  → `source = os.getenv("TEST_ALERT_MANAGER_SOURCE_144")`
  → 环境变量: `TEST_ALERT_MANAGER_SOURCE_144`

- 行 151: `title="Throttle Test["`
  → `title = os.getenv("TEST_ALERT_MANAGER_TITLE_151")`
  → 环境变量: `TEST_ALERT_MANAGER_TITLE_151`

- 行 152: `message="]First alert["`
  → `message = os.getenv("TEST_ALERT_MANAGER_MESSAGE_152")`
  → 环境变量: `TEST_ALERT_MANAGER_MESSAGE_152`

- 行 152: `source="]test["`
  → `source = os.getenv("TEST_ALERT_MANAGER_SOURCE_152")`
  → 环境变量: `TEST_ALERT_MANAGER_SOURCE_152`

- 行 152: `rule_id="]data_freshness_critical["`
  → `rule_id = os.getenv("TEST_ALERT_MANAGER_RULE_ID_152")`
  → 环境变量: `TEST_ALERT_MANAGER_RULE_ID_152`

- 行 155: `title="]]Throttle Test["`
  → `title = os.getenv("TEST_ALERT_MANAGER_TITLE_155")`
  → 环境变量: `TEST_ALERT_MANAGER_TITLE_155`

- 行 155: `message="]Second alert["`
  → `message = os.getenv("TEST_ALERT_MANAGER_MESSAGE_155")`
  → 环境变量: `TEST_ALERT_MANAGER_MESSAGE_155`

- 行 155: `source="]test["`
  → `source = os.getenv("TEST_ALERT_MANAGER_SOURCE_155")`
  → 环境变量: `TEST_ALERT_MANAGER_SOURCE_155`

- 行 155: `rule_id="]data_freshness_critical["`
  → `rule_id = os.getenv("TEST_ALERT_MANAGER_RULE_ID_155")`
  → 环境变量: `TEST_ALERT_MANAGER_RULE_ID_155`

- 行 162: `title="No Throttle Test["`
  → `title = os.getenv("TEST_ALERT_MANAGER_TITLE_162")`
  → 环境变量: `TEST_ALERT_MANAGER_TITLE_162`

- 行 162: `message="]First alert["`
  → `message = os.getenv("TEST_ALERT_MANAGER_MESSAGE_162")`
  → 环境变量: `TEST_ALERT_MANAGER_MESSAGE_162`

- 行 162: `source="]test["`
  → `source = os.getenv("TEST_ALERT_MANAGER_SOURCE_162")`
  → 环境变量: `TEST_ALERT_MANAGER_SOURCE_162`

- 行 162: `title="]No Throttle Test["`
  → `title = os.getenv("TEST_ALERT_MANAGER_TITLE_162")`
  → 环境变量: `TEST_ALERT_MANAGER_TITLE_162`

- 行 162: `message="]Second alert["`
  → `message = os.getenv("TEST_ALERT_MANAGER_MESSAGE_162")`
  → 环境变量: `TEST_ALERT_MANAGER_MESSAGE_162`

- 行 163: `source="]test["`
  → `source = os.getenv("TEST_ALERT_MANAGER_SOURCE_163")`
  → 环境变量: `TEST_ALERT_MANAGER_SOURCE_163`

- 行 192: `alert_id="test-send["`
  → `alert_id = os.getenv("TEST_ALERT_MANAGER_ALERT_ID_192")`
  → 环境变量: `TEST_ALERT_MANAGER_ALERT_ID_192`

- 行 192: `title="]Send Test["`
  → `title = os.getenv("TEST_ALERT_MANAGER_TITLE_192")`
  → 环境变量: `TEST_ALERT_MANAGER_TITLE_192`

- 行 192: `message="]Test sending["`
  → `message = os.getenv("TEST_ALERT_MANAGER_MESSAGE_192")`
  → 环境变量: `TEST_ALERT_MANAGER_MESSAGE_192`

- 行 192: `source="]test["`
  → `source = os.getenv("TEST_ALERT_MANAGER_SOURCE_192")`
  → 环境变量: `TEST_ALERT_MANAGER_SOURCE_192`

- 行 196: `alert_id="test-send-no-rule["`
  → `alert_id = os.getenv("TEST_ALERT_MANAGER_ALERT_ID_196")`
  → 环境变量: `TEST_ALERT_MANAGER_ALERT_ID_196`

- 行 196: `title="]Send Test No Rule["`
  → `title = os.getenv("TEST_ALERT_MANAGER_TITLE_196")`
  → 环境变量: `TEST_ALERT_MANAGER_TITLE_196`

- 行 197: `message="]Test sending without rule["`
  → `message = os.getenv("TEST_ALERT_MANAGER_MESSAGE_197")`
  → 环境变量: `TEST_ALERT_MANAGER_MESSAGE_197`

- 行 198: `source="]test["`
  → `source = os.getenv("TEST_ALERT_MANAGER_SOURCE_198")`
  → 环境变量: `TEST_ALERT_MANAGER_SOURCE_198`

- 行 202: `alert_id="]test-error["`
  → `alert_id = os.getenv("TEST_ALERT_MANAGER_ALERT_ID_202")`
  → 环境变量: `TEST_ALERT_MANAGER_ALERT_ID_202`

- 行 203: `title="]Error Test["`
  → `title = os.getenv("TEST_ALERT_MANAGER_TITLE_203")`
  → 环境变量: `TEST_ALERT_MANAGER_TITLE_203`

- 行 203: `message="]Test error handling["`
  → `message = os.getenv("TEST_ALERT_MANAGER_MESSAGE_203")`
  → 环境变量: `TEST_ALERT_MANAGER_MESSAGE_203`

- 行 205: `source="]test["`
  → `source = os.getenv("TEST_ALERT_MANAGER_SOURCE_205")`
  → 环境变量: `TEST_ALERT_MANAGER_SOURCE_205`

- 行 208: `alert_id="test-metrics["`
  → `alert_id = os.getenv("TEST_ALERT_MANAGER_ALERT_ID_208")`
  → 环境变量: `TEST_ALERT_MANAGER_ALERT_ID_208`

- 行 209: `title="]Metrics Test["`
  → `title = os.getenv("TEST_ALERT_MANAGER_TITLE_209")`
  → 环境变量: `TEST_ALERT_MANAGER_TITLE_209`

- 行 209: `message="]Test metrics update["`
  → `message = os.getenv("TEST_ALERT_MANAGER_MESSAGE_209")`
  → 环境变量: `TEST_ALERT_MANAGER_MESSAGE_209`

- 行 210: `source="]test["`
  → `source = os.getenv("TEST_ALERT_MANAGER_SOURCE_210")`
  → 环境变量: `TEST_ALERT_MANAGER_SOURCE_210`

- 行 212: `level="]warning["`
  → `level = os.getenv("TEST_ALERT_MANAGER_LEVEL_212")`
  → 环境变量: `TEST_ALERT_MANAGER_LEVEL_212`

- 行 212: `source="]test["`
  → `source = os.getenv("TEST_ALERT_MANAGER_SOURCE_212")`
  → 环境变量: `TEST_ALERT_MANAGER_SOURCE_212`

- 行 212: `rule_id="]test_rule["`
  → `rule_id = os.getenv("TEST_ALERT_MANAGER_RULE_ID_212")`
  → 环境变量: `TEST_ALERT_MANAGER_RULE_ID_212`

- 行 213: `level="]warning["`
  → `level = os.getenv("TEST_ALERT_MANAGER_LEVEL_213")`
  → 环境变量: `TEST_ALERT_MANAGER_LEVEL_213`

- 行 217: `alert_id="]test-log-info["`
  → `alert_id = os.getenv("TEST_ALERT_MANAGER_ALERT_ID_217")`
  → 环境变量: `TEST_ALERT_MANAGER_ALERT_ID_217`

- 行 217: `title="]Log Info Test["`
  → `title = os.getenv("TEST_ALERT_MANAGER_TITLE_217")`
  → 环境变量: `TEST_ALERT_MANAGER_TITLE_217`

- 行 217: `message="]Test info logging["`
  → `message = os.getenv("TEST_ALERT_MANAGER_MESSAGE_217")`
  → 环境变量: `TEST_ALERT_MANAGER_MESSAGE_217`

- 行 217: `source="]test["`
  → `source = os.getenv("TEST_ALERT_MANAGER_SOURCE_217")`
  → 环境变量: `TEST_ALERT_MANAGER_SOURCE_217`

- 行 221: `alert_id="]test-log-critical["`
  → `alert_id = os.getenv("TEST_ALERT_MANAGER_ALERT_ID_221")`
  → 环境变量: `TEST_ALERT_MANAGER_ALERT_ID_221`

- 行 222: `title="]Log Critical Test["`
  → `title = os.getenv("TEST_ALERT_MANAGER_TITLE_222")`
  → 环境变量: `TEST_ALERT_MANAGER_TITLE_222`

- 行 222: `message="]Test critical logging["`
  → `message = os.getenv("TEST_ALERT_MANAGER_MESSAGE_222")`
  → 环境变量: `TEST_ALERT_MANAGER_MESSAGE_222`

- 行 223: `source="]test["`
  → `source = os.getenv("TEST_ALERT_MANAGER_SOURCE_223")`
  → 环境变量: `TEST_ALERT_MANAGER_SOURCE_223`

- 行 228: `alert_id="test-prometheus["`
  → `alert_id = os.getenv("TEST_ALERT_MANAGER_ALERT_ID_228")`
  → 环境变量: `TEST_ALERT_MANAGER_ALERT_ID_228`

- 行 228: `title="]Prometheus Test["`
  → `title = os.getenv("TEST_ALERT_MANAGER_TITLE_228")`
  → 环境变量: `TEST_ALERT_MANAGER_TITLE_228`

- 行 228: `message="]Test Prometheus handler["`
  → `message = os.getenv("TEST_ALERT_MANAGER_MESSAGE_228")`
  → 环境变量: `TEST_ALERT_MANAGER_MESSAGE_228`

- 行 228: `source="]test["`
  → `source = os.getenv("TEST_ALERT_MANAGER_SOURCE_228")`
  → 环境变量: `TEST_ALERT_MANAGER_SOURCE_228`

- 行 231: `alert_id="test-resolve-alert["`
  → `alert_id = os.getenv("TEST_ALERT_MANAGER_ALERT_ID_231")`
  → 环境变量: `TEST_ALERT_MANAGER_ALERT_ID_231`

- 行 231: `title="]Resolve Alert Test["`
  → `title = os.getenv("TEST_ALERT_MANAGER_TITLE_231")`
  → 环境变量: `TEST_ALERT_MANAGER_TITLE_231`

- 行 231: `message="]Test alert resolution["`
  → `message = os.getenv("TEST_ALERT_MANAGER_MESSAGE_231")`
  → 环境变量: `TEST_ALERT_MANAGER_MESSAGE_231`

- 行 233: `source="]test["`
  → `source = os.getenv("TEST_ALERT_MANAGER_SOURCE_233")`
  → 环境变量: `TEST_ALERT_MANAGER_SOURCE_233`

- 行 237: `alert_id="test-already-resolved["`
  → `alert_id = os.getenv("TEST_ALERT_MANAGER_ALERT_ID_237")`
  → 环境变量: `TEST_ALERT_MANAGER_ALERT_ID_237`

- 行 237: `title="]Already Resolved["`
  → `title = os.getenv("TEST_ALERT_MANAGER_TITLE_237")`
  → 环境变量: `TEST_ALERT_MANAGER_TITLE_237`

- 行 237: `message="]Test already resolved alert["`
  → `message = os.getenv("TEST_ALERT_MANAGER_MESSAGE_237")`
  → 环境变量: `TEST_ALERT_MANAGER_MESSAGE_237`

- 行 238: `source="]test["`
  → `source = os.getenv("TEST_ALERT_MANAGER_SOURCE_238")`
  → 环境变量: `TEST_ALERT_MANAGER_SOURCE_238`

- 行 272: `table_name="]matches["`
  → `table_name = os.getenv("TEST_ALERT_MANAGER_TABLE_NAME_272")`
  → 环境变量: `TEST_ALERT_MANAGER_TABLE_NAME_272`

- 行 272: `table_name="]teams["`
  → `table_name = os.getenv("TEST_ALERT_MANAGER_TABLE_NAME_272")`
  → 环境变量: `TEST_ALERT_MANAGER_TABLE_NAME_272`

- 行 280: `table_name="]matches["`
  → `table_name = os.getenv("TEST_ALERT_MANAGER_TABLE_NAME_280")`
  → 环境变量: `TEST_ALERT_MANAGER_TABLE_NAME_280`

- 行 280: `table_name="]teams["`
  → `table_name = os.getenv("TEST_ALERT_MANAGER_TABLE_NAME_280")`
  → 环境变量: `TEST_ALERT_MANAGER_TABLE_NAME_280`

- 行 280: `table_name="]matches["`
  → `table_name = os.getenv("TEST_ALERT_MANAGER_TABLE_NAME_280")`
  → 环境变量: `TEST_ALERT_MANAGER_TABLE_NAME_280`

- 行 283: `table_name = "matches["`
  → `table_name = os.getenv("TEST_ALERT_MANAGER_TABLE_NAME_283")`
  → 环境变量: `TEST_ALERT_MANAGER_TABLE_NAME_283`

- 行 284: `column_name = "]home_score["`
  → `column_name = os.getenv("TEST_ALERT_MANAGER_COLUMN_NAME_284")`
  → 环境变量: `TEST_ALERT_MANAGER_COLUMN_NAME_284`

- 行 286: `value = "]outlier["`
  → `value = os.getenv("TEST_ALERT_MANAGER_VALUE_286")`
  → 环境变量: `TEST_ALERT_MANAGER_VALUE_286`

- 行 286: `value = "]high["`
  → `value = os.getenv("TEST_ALERT_MANAGER_VALUE_286")`
  → 环境变量: `TEST_ALERT_MANAGER_VALUE_286`

- 行 287: `table_name="]]matches["`
  → `table_name = os.getenv("TEST_ALERT_MANAGER_TABLE_NAME_287")`
  → 环境变量: `TEST_ALERT_MANAGER_TABLE_NAME_287`

- 行 288: `column_name="]home_score["`
  → `column_name = os.getenv("TEST_ALERT_MANAGER_COLUMN_NAME_288")`
  → 环境变量: `TEST_ALERT_MANAGER_COLUMN_NAME_288`

- 行 288: `anomaly_type="]outlier["`
  → `anomaly_type = os.getenv("TEST_ALERT_MANAGER_ANOMALY_TYPE_288")`
  → 环境变量: `TEST_ALERT_MANAGER_ANOMALY_TYPE_288`

- 行 288: `severity="]high["`
  → `severity = os.getenv("TEST_ALERT_MANAGER_SEVERITY_288")`
  → 环境变量: `TEST_ALERT_MANAGER_SEVERITY_288`

- 行 291: `table_name="]matches["`
  → `table_name = os.getenv("TEST_ALERT_MANAGER_TABLE_NAME_291")`
  → 环境变量: `TEST_ALERT_MANAGER_TABLE_NAME_291`

- 行 292: `column_name="]home_score["`
  → `column_name = os.getenv("TEST_ALERT_MANAGER_COLUMN_NAME_292")`
  → 环境变量: `TEST_ALERT_MANAGER_COLUMN_NAME_292`

- 行 334: `table_name = "matches["`
  → `table_name = os.getenv("TEST_ALERT_MANAGER_TABLE_NAME_334")`
  → 环境变量: `TEST_ALERT_MANAGER_TABLE_NAME_334`

- 行 334: `column_name = "]home_score["`
  → `column_name = os.getenv("TEST_ALERT_MANAGER_COLUMN_NAME_334")`
  → 环境变量: `TEST_ALERT_MANAGER_COLUMN_NAME_334`

- 行 336: `value = "]outlier["`
  → `value = os.getenv("TEST_ALERT_MANAGER_VALUE_336")`
  → 环境变量: `TEST_ALERT_MANAGER_VALUE_336`

- 行 337: `description = "]]High score detected["`
  → `description = os.getenv("TEST_ALERT_MANAGER_DESCRIPTION_337")`
  → 环境变量: `TEST_ALERT_MANAGER_DESCRIPTION_337`

- 行 349: `table_name = "matches["`
  → `table_name = os.getenv("TEST_ALERT_MANAGER_TABLE_NAME_349")`
  → 环境变量: `TEST_ALERT_MANAGER_TABLE_NAME_349`

- 行 349: `column_name = "]home_score["`
  → `column_name = os.getenv("TEST_ALERT_MANAGER_COLUMN_NAME_349")`
  → 环境变量: `TEST_ALERT_MANAGER_COLUMN_NAME_349`

- 行 350: `value = "]outlier["`
  → `value = os.getenv("TEST_ALERT_MANAGER_VALUE_350")`
  → 环境变量: `TEST_ALERT_MANAGER_VALUE_350`

- 行 352: `description = "]]Medium score detected["`
  → `description = os.getenv("TEST_ALERT_MANAGER_DESCRIPTION_352")`
  → 环境变量: `TEST_ALERT_MANAGER_DESCRIPTION_352`

- 行 364: `table_name = "matches["`
  → `table_name = os.getenv("TEST_ALERT_MANAGER_TABLE_NAME_364")`
  → 环境变量: `TEST_ALERT_MANAGER_TABLE_NAME_364`

- 行 365: `column_name = "]home_score["`
  → `column_name = os.getenv("TEST_ALERT_MANAGER_COLUMN_NAME_365")`
  → 环境变量: `TEST_ALERT_MANAGER_COLUMN_NAME_365`

- 行 366: `value = "]outlier["`
  → `value = os.getenv("TEST_ALERT_MANAGER_VALUE_366")`
  → 环境变量: `TEST_ALERT_MANAGER_VALUE_366`

- 行 369: `description = "]]Low score detected["`
  → `description = os.getenv("TEST_ALERT_MANAGER_DESCRIPTION_369")`
  → 环境变量: `TEST_ALERT_MANAGER_DESCRIPTION_369`

- 行 380: `title="Workflow Test["`
  → `title = os.getenv("TEST_ALERT_MANAGER_TITLE_380")`
  → 环境变量: `TEST_ALERT_MANAGER_TITLE_380`

- 行 381: `message="]Testing complete workflow["`
  → `message = os.getenv("TEST_ALERT_MANAGER_MESSAGE_381")`
  → 环境变量: `TEST_ALERT_MANAGER_MESSAGE_381`

- 行 382: `source="]integration_test["`
  → `source = os.getenv("TEST_ALERT_MANAGER_SOURCE_382")`
  → 环境变量: `TEST_ALERT_MANAGER_SOURCE_382`

- 行 383: `rule_id="]data_freshness_warning["`
  → `rule_id = os.getenv("TEST_ALERT_MANAGER_RULE_ID_383")`
  → 环境变量: `TEST_ALERT_MANAGER_RULE_ID_383`

- 行 411: `title="]]Error Handling Test["`
  → `title = os.getenv("TEST_ALERT_MANAGER_TITLE_411")`
  → 环境变量: `TEST_ALERT_MANAGER_TITLE_411`

- 行 411: `message="]Testing error handling["`
  → `message = os.getenv("TEST_ALERT_MANAGER_MESSAGE_411")`
  → 环境变量: `TEST_ALERT_MANAGER_MESSAGE_411`

- 行 411: `source="]test["`
  → `source = os.getenv("TEST_ALERT_MANAGER_SOURCE_411")`
  → 环境变量: `TEST_ALERT_MANAGER_SOURCE_411`

### tests/legacy/unit/monitoring/test_alert_verification.py

- 行 282: `encoding = "]utf-8["`
  → `encoding = os.getenv("TEST_ALERT_VERIFICATION_ENCODING_282")`
  → 环境变量: `TEST_ALERT_VERIFICATION_ENCODING_282`

- 行 286: `encoding = "]utf-8["`
  → `encoding = os.getenv("TEST_ALERT_VERIFICATION_ENCODING_286")`
  → 环境变量: `TEST_ALERT_VERIFICATION_ENCODING_286`

### tests/legacy/unit/monitoring/test_alert_manager_batch_omega_002.py

- 行 34: `alert_id="test-001["`
  → `alert_id = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_ALERT_ID_34")`
  → 环境变量: `TEST_ALERT_MANAGER_BATCH_OMEGA_002_ALERT_ID_34`

- 行 34: `title="]Test Alert["`
  → `title = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_TITLE_34")`
  → 环境变量: `TEST_ALERT_MANAGER_BATCH_OMEGA_002_TITLE_34`

- 行 34: `message="]This is a test alert["`
  → `message = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_MESSAGE_34")`
  → 环境变量: `TEST_ALERT_MANAGER_BATCH_OMEGA_002_MESSAGE_34`

- 行 34: `source="]test_source["`
  → `source = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_SOURCE_34")`
  → 环境变量: `TEST_ALERT_MANAGER_BATCH_OMEGA_002_SOURCE_34`

- 行 45: `alert_id="test-001["`
  → `alert_id = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_ALERT_ID_45")`
  → 环境变量: `TEST_ALERT_MANAGER_BATCH_OMEGA_002_ALERT_ID_45`

- 行 45: `title="]Test Alert["`
  → `title = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_TITLE_45")`
  → 环境变量: `TEST_ALERT_MANAGER_BATCH_OMEGA_002_TITLE_45`

- 行 46: `message="]Test message["`
  → `message = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_MESSAGE_46")`
  → 环境变量: `TEST_ALERT_MANAGER_BATCH_OMEGA_002_MESSAGE_46`

- 行 47: `source="]test_source["`
  → `source = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_SOURCE_47")`
  → 环境变量: `TEST_ALERT_MANAGER_BATCH_OMEGA_002_SOURCE_47`

- 行 54: `alert_id="test-002["`
  → `alert_id = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_ALERT_ID_54")`
  → 环境变量: `TEST_ALERT_MANAGER_BATCH_OMEGA_002_ALERT_ID_54`

- 行 54: `title = "]Alert with metadata["`
  → `title = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_TITLE_54")`
  → 环境变量: `TEST_ALERT_MANAGER_BATCH_OMEGA_002_TITLE_54`

- 行 55: `message = "]Test with metadata["`
  → `message = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_MESSAGE_55")`
  → 环境变量: `TEST_ALERT_MANAGER_BATCH_OMEGA_002_MESSAGE_55`

- 行 57: `source="]test_source["`
  → `source = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_SOURCE_57")`
  → 环境变量: `TEST_ALERT_MANAGER_BATCH_OMEGA_002_SOURCE_57`

- 行 65: `alert_id="test-001["`
  → `alert_id = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_ALERT_ID_65")`
  → 环境变量: `TEST_ALERT_MANAGER_BATCH_OMEGA_002_ALERT_ID_65`

- 行 66: `title="]Test Alert["`
  → `title = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_TITLE_66")`
  → 环境变量: `TEST_ALERT_MANAGER_BATCH_OMEGA_002_TITLE_66`

- 行 66: `message="]Test message["`
  → `message = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_MESSAGE_66")`
  → 环境变量: `TEST_ALERT_MANAGER_BATCH_OMEGA_002_MESSAGE_66`

- 行 67: `source="]test_source["`
  → `source = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_SOURCE_67")`
  → 环境变量: `TEST_ALERT_MANAGER_BATCH_OMEGA_002_SOURCE_67`

- 行 71: `alert_id="test-001["`
  → `alert_id = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_ALERT_ID_71")`
  → 环境变量: `TEST_ALERT_MANAGER_BATCH_OMEGA_002_ALERT_ID_71`

- 行 72: `title="]Test Alert["`
  → `title = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_TITLE_72")`
  → 环境变量: `TEST_ALERT_MANAGER_BATCH_OMEGA_002_TITLE_72`

- 行 72: `message="]Test message["`
  → `message = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_MESSAGE_72")`
  → 环境变量: `TEST_ALERT_MANAGER_BATCH_OMEGA_002_MESSAGE_72`

- 行 72: `source="]test_source["`
  → `source = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_SOURCE_72")`
  → 环境变量: `TEST_ALERT_MANAGER_BATCH_OMEGA_002_SOURCE_72`

- 行 77: `rule_id="test_rule["`
  → `rule_id = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_RULE_ID_77")`
  → 环境变量: `TEST_ALERT_MANAGER_BATCH_OMEGA_002_RULE_ID_77`

- 行 77: `name="]Test Rule["`
  → `name = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_NAME_77")`
  → 环境变量: `TEST_ALERT_MANAGER_BATCH_OMEGA_002_NAME_77`

- 行 78: `condition="]error_count > 10["`
  → `condition = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_CONDITION_78")`
  → 环境变量: `TEST_ALERT_MANAGER_BATCH_OMEGA_002_CONDITION_78`

- 行 90: `rule_id="test_rule["`
  → `rule_id = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_RULE_ID_90")`
  → 环境变量: `TEST_ALERT_MANAGER_BATCH_OMEGA_002_RULE_ID_90`

- 行 90: `name="]Test Rule["`
  → `name = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_NAME_90")`
  → 环境变量: `TEST_ALERT_MANAGER_BATCH_OMEGA_002_NAME_90`

- 行 90: `condition="]error_count > 10["`
  → `condition = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_CONDITION_90")`
  → 环境变量: `TEST_ALERT_MANAGER_BATCH_OMEGA_002_CONDITION_90`

- 行 95: `rule_id="test_rule["`
  → `rule_id = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_RULE_ID_95")`
  → 环境变量: `TEST_ALERT_MANAGER_BATCH_OMEGA_002_RULE_ID_95`

- 行 95: `name="]Test Rule["`
  → `name = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_NAME_95")`
  → 环境变量: `TEST_ALERT_MANAGER_BATCH_OMEGA_002_NAME_95`

- 行 95: `condition="]error_count > 10["`
  → `condition = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_CONDITION_95")`
  → 环境变量: `TEST_ALERT_MANAGER_BATCH_OMEGA_002_CONDITION_95`

- 行 105: `title="Test Alert["`
  → `title = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_TITLE_105")`
  → 环境变量: `TEST_ALERT_MANAGER_BATCH_OMEGA_002_TITLE_105`

- 行 105: `message="]Test message["`
  → `message = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_MESSAGE_105")`
  → 环境变量: `TEST_ALERT_MANAGER_BATCH_OMEGA_002_MESSAGE_105`

- 行 105: `source="]test_source["`
  → `source = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_SOURCE_105")`
  → 环境变量: `TEST_ALERT_MANAGER_BATCH_OMEGA_002_SOURCE_105`

- 行 113: `title="]Test Alert["`
  → `title = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_TITLE_113")`
  → 环境变量: `TEST_ALERT_MANAGER_BATCH_OMEGA_002_TITLE_113`

- 行 113: `message="]Test message["`
  → `message = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_MESSAGE_113")`
  → 环境变量: `TEST_ALERT_MANAGER_BATCH_OMEGA_002_MESSAGE_113`

- 行 113: `source="]test_source["`
  → `source = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_SOURCE_113")`
  → 环境变量: `TEST_ALERT_MANAGER_BATCH_OMEGA_002_SOURCE_113`

- 行 119: `title="Test Alert["`
  → `title = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_TITLE_119")`
  → 环境变量: `TEST_ALERT_MANAGER_BATCH_OMEGA_002_TITLE_119`

- 行 119: `message="]Test message["`
  → `message = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_MESSAGE_119")`
  → 环境变量: `TEST_ALERT_MANAGER_BATCH_OMEGA_002_MESSAGE_119`

- 行 120: `source="]test_source["`
  → `source = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_SOURCE_120")`
  → 环境变量: `TEST_ALERT_MANAGER_BATCH_OMEGA_002_SOURCE_120`

- 行 121: `rule_id="]data_freshness_warning["`
  → `rule_id = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_RULE_ID_121")`
  → 环境变量: `TEST_ALERT_MANAGER_BATCH_OMEGA_002_RULE_ID_121`

- 行 123: `rule_id="test_rule["`
  → `rule_id = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_RULE_ID_123")`
  → 环境变量: `TEST_ALERT_MANAGER_BATCH_OMEGA_002_RULE_ID_123`

- 行 123: `name="]Test Rule["`
  → `name = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_NAME_123")`
  → 环境变量: `TEST_ALERT_MANAGER_BATCH_OMEGA_002_NAME_123`

- 行 124: `condition="]error_count > 10["`
  → `condition = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_CONDITION_124")`
  → 环境变量: `TEST_ALERT_MANAGER_BATCH_OMEGA_002_CONDITION_124`

- 行 128: `title="]Test Alert["`
  → `title = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_TITLE_128")`
  → 环境变量: `TEST_ALERT_MANAGER_BATCH_OMEGA_002_TITLE_128`

- 行 128: `message="]Test message["`
  → `message = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_MESSAGE_128")`
  → 环境变量: `TEST_ALERT_MANAGER_BATCH_OMEGA_002_MESSAGE_128`

- 行 130: `source="]test_source["`
  → `source = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_SOURCE_130")`
  → 环境变量: `TEST_ALERT_MANAGER_BATCH_OMEGA_002_SOURCE_130`

- 行 130: `rule_id="]test_rule["`
  → `rule_id = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_RULE_ID_130")`
  → 环境变量: `TEST_ALERT_MANAGER_BATCH_OMEGA_002_RULE_ID_130`

- 行 131: `title="]Test Alert["`
  → `title = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_TITLE_131")`
  → 环境变量: `TEST_ALERT_MANAGER_BATCH_OMEGA_002_TITLE_131`

- 行 131: `message="]Test message["`
  → `message = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_MESSAGE_131")`
  → 环境变量: `TEST_ALERT_MANAGER_BATCH_OMEGA_002_MESSAGE_131`

- 行 131: `source="]test_source["`
  → `source = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_SOURCE_131")`
  → 环境变量: `TEST_ALERT_MANAGER_BATCH_OMEGA_002_SOURCE_131`

- 行 131: `rule_id="]test_rule["`
  → `rule_id = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_RULE_ID_131")`
  → 环境变量: `TEST_ALERT_MANAGER_BATCH_OMEGA_002_RULE_ID_131`

- 行 140: `alert_id="test-001["`
  → `alert_id = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_ALERT_ID_140")`
  → 环境变量: `TEST_ALERT_MANAGER_BATCH_OMEGA_002_ALERT_ID_140`

- 行 140: `title="]Test Alert["`
  → `title = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_TITLE_140")`
  → 环境变量: `TEST_ALERT_MANAGER_BATCH_OMEGA_002_TITLE_140`

- 行 140: `message="]Test message["`
  → `message = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_MESSAGE_140")`
  → 环境变量: `TEST_ALERT_MANAGER_BATCH_OMEGA_002_MESSAGE_140`

- 行 140: `source="]test_source["`
  → `source = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_SOURCE_140")`
  → 环境变量: `TEST_ALERT_MANAGER_BATCH_OMEGA_002_SOURCE_140`

- 行 148: `title="Test Alert["`
  → `title = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_TITLE_148")`
  → 环境变量: `TEST_ALERT_MANAGER_BATCH_OMEGA_002_TITLE_148`

- 行 148: `message="]Test message["`
  → `message = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_MESSAGE_148")`
  → 环境变量: `TEST_ALERT_MANAGER_BATCH_OMEGA_002_MESSAGE_148`

- 行 148: `source="]test_source["`
  → `source = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_SOURCE_148")`
  → 环境变量: `TEST_ALERT_MANAGER_BATCH_OMEGA_002_SOURCE_148`

- 行 153: `title="Alert 1["`
  → `title = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_TITLE_153")`
  → 环境变量: `TEST_ALERT_MANAGER_BATCH_OMEGA_002_TITLE_153`

- 行 154: `message="]Message 1["`
  → `message = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_MESSAGE_154")`
  → 环境变量: `TEST_ALERT_MANAGER_BATCH_OMEGA_002_MESSAGE_154`

- 行 157: `source="]test_source["`
  → `source = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_SOURCE_157")`
  → 环境变量: `TEST_ALERT_MANAGER_BATCH_OMEGA_002_SOURCE_157`

- 行 158: `title="]Alert 2["`
  → `title = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_TITLE_158")`
  → 环境变量: `TEST_ALERT_MANAGER_BATCH_OMEGA_002_TITLE_158`

- 行 158: `message="]Message 2["`
  → `message = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_MESSAGE_158")`
  → 环境变量: `TEST_ALERT_MANAGER_BATCH_OMEGA_002_MESSAGE_158`

- 行 158: `source="]test_source["`
  → `source = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_SOURCE_158")`
  → 环境变量: `TEST_ALERT_MANAGER_BATCH_OMEGA_002_SOURCE_158`

- 行 169: `title="Warning Alert["`
  → `title = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_TITLE_169")`
  → 环境变量: `TEST_ALERT_MANAGER_BATCH_OMEGA_002_TITLE_169`

- 行 169: `message="]Warning message["`
  → `message = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_MESSAGE_169")`
  → 环境变量: `TEST_ALERT_MANAGER_BATCH_OMEGA_002_MESSAGE_169`

- 行 170: `source="]test_source["`
  → `source = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_SOURCE_170")`
  → 环境变量: `TEST_ALERT_MANAGER_BATCH_OMEGA_002_SOURCE_170`

- 行 172: `title="]Error Alert["`
  → `title = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_TITLE_172")`
  → 环境变量: `TEST_ALERT_MANAGER_BATCH_OMEGA_002_TITLE_172`

- 行 173: `message="]Error message["`
  → `message = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_MESSAGE_173")`
  → 环境变量: `TEST_ALERT_MANAGER_BATCH_OMEGA_002_MESSAGE_173`

- 行 174: `source="]test_source["`
  → `source = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_SOURCE_174")`
  → 环境变量: `TEST_ALERT_MANAGER_BATCH_OMEGA_002_SOURCE_174`

- 行 201: `table_name = "matches["`
  → `table_name = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_TABLE_NAME_201")`
  → 环境变量: `TEST_ALERT_MANAGER_BATCH_OMEGA_002_TABLE_NAME_201`

- 行 201: `column_name = "]home_score["`
  → `column_name = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_COLUMN_NAME_201")`
  → 环境变量: `TEST_ALERT_MANAGER_BATCH_OMEGA_002_COLUMN_NAME_201`

- 行 202: `value = "]statistical["`
  → `value = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_VALUE_202")`
  → 环境变量: `TEST_ALERT_MANAGER_BATCH_OMEGA_002_VALUE_202`

- 行 205: `value = "]high["`
  → `value = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_VALUE_205")`
  → 环境变量: `TEST_ALERT_MANAGER_BATCH_OMEGA_002_VALUE_205`

- 行 221: `table_name = "matches["`
  → `table_name = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_TABLE_NAME_221")`
  → 环境变量: `TEST_ALERT_MANAGER_BATCH_OMEGA_002_TABLE_NAME_221`

- 行 223: `column_name = "]home_score["`
  → `column_name = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_COLUMN_NAME_223")`
  → 环境变量: `TEST_ALERT_MANAGER_BATCH_OMEGA_002_COLUMN_NAME_223`

- 行 225: `value = "]statistical["`
  → `value = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_VALUE_225")`
  → 环境变量: `TEST_ALERT_MANAGER_BATCH_OMEGA_002_VALUE_225`

- 行 227: `value = "]high["`
  → `value = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_VALUE_227")`
  → 环境变量: `TEST_ALERT_MANAGER_BATCH_OMEGA_002_VALUE_227`

- 行 227: `description = "]异常高的得分["`
  → `description = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_DESCRIPTION_227")`
  → 环境变量: `TEST_ALERT_MANAGER_BATCH_OMEGA_002_DESCRIPTION_227`

- 行 251: `rule_id="test_rule["`
  → `rule_id = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_RULE_ID_251")`
  → 环境变量: `TEST_ALERT_MANAGER_BATCH_OMEGA_002_RULE_ID_251`

- 行 251: `name="]Test Rule["`
  → `name = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_NAME_251")`
  → 环境变量: `TEST_ALERT_MANAGER_BATCH_OMEGA_002_NAME_251`

- 行 252: `condition="]error_count > 10["`
  → `condition = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_CONDITION_252")`
  → 环境变量: `TEST_ALERT_MANAGER_BATCH_OMEGA_002_CONDITION_252`

- 行 267: `rule_id="]test_rule["`
  → `rule_id = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_RULE_ID_267")`
  → 环境变量: `TEST_ALERT_MANAGER_BATCH_OMEGA_002_RULE_ID_267`

- 行 268: `name="]Test Rule["`
  → `name = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_NAME_268")`
  → 环境变量: `TEST_ALERT_MANAGER_BATCH_OMEGA_002_NAME_268`

- 行 269: `condition="]error_count > 10["`
  → `condition = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_CONDITION_269")`
  → 环境变量: `TEST_ALERT_MANAGER_BATCH_OMEGA_002_CONDITION_269`

- 行 273: `alert_id="]test-001["`
  → `alert_id = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_ALERT_ID_273")`
  → 环境变量: `TEST_ALERT_MANAGER_BATCH_OMEGA_002_ALERT_ID_273`

- 行 274: `title="]Test Alert["`
  → `title = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_TITLE_274")`
  → 环境变量: `TEST_ALERT_MANAGER_BATCH_OMEGA_002_TITLE_274`

- 行 274: `message="]Test message["`
  → `message = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_MESSAGE_274")`
  → 环境变量: `TEST_ALERT_MANAGER_BATCH_OMEGA_002_MESSAGE_274`

- 行 275: `source="]test_source["`
  → `source = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_SOURCE_275")`
  → 环境变量: `TEST_ALERT_MANAGER_BATCH_OMEGA_002_SOURCE_275`

### tests/legacy/unit/monitoring/test_anomaly_detector.py

- 行 44: `table_names="matches["`
  → `table_names = os.getenv("TEST_ANOMALY_DETECTOR_TABLE_NAMES_44")`
  → 环境变量: `TEST_ANOMALY_DETECTOR_TABLE_NAMES_44`

- 行 50: `table_names="]]matches["`
  → `table_names = os.getenv("TEST_ANOMALY_DETECTOR_TABLE_NAMES_50")`
  → 环境变量: `TEST_ANOMALY_DETECTOR_TABLE_NAMES_50`

- 行 55: `table_names="]]matches["`
  → `table_names = os.getenv("TEST_ANOMALY_DETECTOR_TABLE_NAMES_55")`
  → 环境变量: `TEST_ANOMALY_DETECTOR_TABLE_NAMES_55`

- 行 63: `value="]outlier["`
  → `value = os.getenv("TEST_ANOMALY_DETECTOR_VALUE_63")`
  → 环境变量: `TEST_ANOMALY_DETECTOR_VALUE_63`

- 行 64: `table_name="]matches["`
  → `table_name = os.getenv("TEST_ANOMALY_DETECTOR_TABLE_NAME_64")`
  → 环境变量: `TEST_ANOMALY_DETECTOR_TABLE_NAME_64`

- 行 65: `value="]range_check["`
  → `value = os.getenv("TEST_ANOMALY_DETECTOR_VALUE_65")`
  → 环境变量: `TEST_ANOMALY_DETECTOR_VALUE_65`

- 行 65: `table_name="]odds["`
  → `table_name = os.getenv("TEST_ANOMALY_DETECTOR_TABLE_NAME_65")`
  → 环境变量: `TEST_ANOMALY_DETECTOR_TABLE_NAME_65`

- 行 73: `table_name="matches["`
  → `table_name = os.getenv("TEST_ANOMALY_DETECTOR_TABLE_NAME_73")`
  → 环境变量: `TEST_ANOMALY_DETECTOR_TABLE_NAME_73`

- 行 73: `column_name="]home_score["`
  → `column_name = os.getenv("TEST_ANOMALY_DETECTOR_COLUMN_NAME_73")`
  → 环境变量: `TEST_ANOMALY_DETECTOR_COLUMN_NAME_73`

- 行 76: `detection_method="]3sigma["`
  → `detection_method = os.getenv("TEST_ANOMALY_DETECTOR_DETECTION_METHOD_76")`
  → 环境变量: `TEST_ANOMALY_DETECTOR_DETECTION_METHOD_76`

- 行 77: `description="]Outlier values detected["`
  → `description = os.getenv("TEST_ANOMALY_DETECTOR_DESCRIPTION_77")`
  → 环境变量: `TEST_ANOMALY_DETECTOR_DESCRIPTION_77`

- 行 83: `table_name="matches["`
  → `table_name = os.getenv("TEST_ANOMALY_DETECTOR_TABLE_NAME_83")`
  → 环境变量: `TEST_ANOMALY_DETECTOR_TABLE_NAME_83`

- 行 84: `column_name="]away_score["`
  → `column_name = os.getenv("TEST_ANOMALY_DETECTOR_COLUMN_NAME_84")`
  → 环境变量: `TEST_ANOMALY_DETECTOR_COLUMN_NAME_84`

- 行 85: `detection_method="]range_check["`
  → `detection_method = os.getenv("TEST_ANOMALY_DETECTOR_DETECTION_METHOD_85")`
  → 环境变量: `TEST_ANOMALY_DETECTOR_DETECTION_METHOD_85`

- 行 85: `description="]Negative score detected["`
  → `description = os.getenv("TEST_ANOMALY_DETECTOR_DESCRIPTION_85")`
  → 环境变量: `TEST_ANOMALY_DETECTOR_DESCRIPTION_85`

- 行 89: `table_name="teams["`
  → `table_name = os.getenv("TEST_ANOMALY_DETECTOR_TABLE_NAME_89")`
  → 环境变量: `TEST_ANOMALY_DETECTOR_TABLE_NAME_89`

- 行 89: `column_name="]rating["`
  → `column_name = os.getenv("TEST_ANOMALY_DETECTOR_COLUMN_NAME_89")`
  → 环境变量: `TEST_ANOMALY_DETECTOR_COLUMN_NAME_89`

- 行 89: `anomalous_values="]unknown["`
  → `anomalous_values = os.getenv("TEST_ANOMALY_DETECTOR_ANOMALOUS_VALUES_89")`
  → 环境变量: `TEST_ANOMALY_DETECTOR_ANOMALOUS_VALUES_89`

- 行 90: `detection_method="]frequency["`
  → `detection_method = os.getenv("TEST_ANOMALY_DETECTOR_DETECTION_METHOD_90")`
  → 环境变量: `TEST_ANOMALY_DETECTOR_DETECTION_METHOD_90`

- 行 91: `description="]Unknown value frequency anomaly["`
  → `description = os.getenv("TEST_ANOMALY_DETECTOR_DESCRIPTION_91")`
  → 环境变量: `TEST_ANOMALY_DETECTOR_DESCRIPTION_91`

- 行 123: `table_names="]]matches["`
  → `table_names = os.getenv("TEST_ANOMALY_DETECTOR_TABLE_NAMES_123")`
  → 环境变量: `TEST_ANOMALY_DETECTOR_TABLE_NAMES_123`

- 行 161: `table_name = "]matches["`
  → `table_name = os.getenv("TEST_ANOMALY_DETECTOR_TABLE_NAME_161")`
  → 环境变量: `TEST_ANOMALY_DETECTOR_TABLE_NAME_161`

- 行 161: `column_name = "]test_column["`
  → `column_name = os.getenv("TEST_ANOMALY_DETECTOR_COLUMN_NAME_161")`
  → 环境变量: `TEST_ANOMALY_DETECTOR_COLUMN_NAME_161`

- 行 162: `methods = "]three_sigma["`
  → `methods = os.getenv("TEST_ANOMALY_DETECTOR_METHODS_162")`
  → 环境变量: `TEST_ANOMALY_DETECTOR_METHODS_162`

- 行 162: `column_type = "]numeric["`
  → `column_type = os.getenv("TEST_ANOMALY_DETECTOR_COLUMN_TYPE_162")`
  → 环境变量: `TEST_ANOMALY_DETECTOR_COLUMN_TYPE_162`

- 行 169: `table_name = "matches["`
  → `table_name = os.getenv("TEST_ANOMALY_DETECTOR_TABLE_NAME_169")`
  → 环境变量: `TEST_ANOMALY_DETECTOR_TABLE_NAME_169`

- 行 169: `column_name = "]home_score["`
  → `column_name = os.getenv("TEST_ANOMALY_DETECTOR_COLUMN_NAME_169")`
  → 环境变量: `TEST_ANOMALY_DETECTOR_COLUMN_NAME_169`

- 行 174: `table_name = "matches["`
  → `table_name = os.getenv("TEST_ANOMALY_DETECTOR_TABLE_NAME_174")`
  → 环境变量: `TEST_ANOMALY_DETECTOR_TABLE_NAME_174`

- 行 175: `column_name = "]home_score["`
  → `column_name = os.getenv("TEST_ANOMALY_DETECTOR_COLUMN_NAME_175")`
  → 环境变量: `TEST_ANOMALY_DETECTOR_COLUMN_NAME_175`

- 行 179: `table_name = "matches["`
  → `table_name = os.getenv("TEST_ANOMALY_DETECTOR_TABLE_NAME_179")`
  → 环境变量: `TEST_ANOMALY_DETECTOR_TABLE_NAME_179`

- 行 179: `column_name = "]home_score["`
  → `column_name = os.getenv("TEST_ANOMALY_DETECTOR_COLUMN_NAME_179")`
  → 环境变量: `TEST_ANOMALY_DETECTOR_COLUMN_NAME_179`

- 行 189: `table_name = "]matches["`
  → `table_name = os.getenv("TEST_ANOMALY_DETECTOR_TABLE_NAME_189")`
  → 环境变量: `TEST_ANOMALY_DETECTOR_TABLE_NAME_189`

- 行 189: `column_name = "]home_score["`
  → `column_name = os.getenv("TEST_ANOMALY_DETECTOR_COLUMN_NAME_189")`
  → 环境变量: `TEST_ANOMALY_DETECTOR_COLUMN_NAME_189`

- 行 195: `table_name = "matches["`
  → `table_name = os.getenv("TEST_ANOMALY_DETECTOR_TABLE_NAME_195")`
  → 环境变量: `TEST_ANOMALY_DETECTOR_TABLE_NAME_195`

- 行 195: `column_name = "]home_score["`
  → `column_name = os.getenv("TEST_ANOMALY_DETECTOR_COLUMN_NAME_195")`
  → 环境变量: `TEST_ANOMALY_DETECTOR_COLUMN_NAME_195`

- 行 200: `table_name = "matches["`
  → `table_name = os.getenv("TEST_ANOMALY_DETECTOR_TABLE_NAME_200")`
  → 环境变量: `TEST_ANOMALY_DETECTOR_TABLE_NAME_200`

- 行 201: `column_name = "]home_score["`
  → `column_name = os.getenv("TEST_ANOMALY_DETECTOR_COLUMN_NAME_201")`
  → 环境变量: `TEST_ANOMALY_DETECTOR_COLUMN_NAME_201`

- 行 207: `table_name = "]matches["`
  → `table_name = os.getenv("TEST_ANOMALY_DETECTOR_TABLE_NAME_207")`
  → 环境变量: `TEST_ANOMALY_DETECTOR_TABLE_NAME_207`

- 行 207: `column_name = "]home_score["`
  → `column_name = os.getenv("TEST_ANOMALY_DETECTOR_COLUMN_NAME_207")`
  → 环境变量: `TEST_ANOMALY_DETECTOR_COLUMN_NAME_207`

- 行 211: `table_name = "matches["`
  → `table_name = os.getenv("TEST_ANOMALY_DETECTOR_TABLE_NAME_211")`
  → 环境变量: `TEST_ANOMALY_DETECTOR_TABLE_NAME_211`

- 行 211: `column_name = "]home_score["`
  → `column_name = os.getenv("TEST_ANOMALY_DETECTOR_COLUMN_NAME_211")`
  → 环境变量: `TEST_ANOMALY_DETECTOR_COLUMN_NAME_211`

- 行 217: `table_name = "matches["`
  → `table_name = os.getenv("TEST_ANOMALY_DETECTOR_TABLE_NAME_217")`
  → 环境变量: `TEST_ANOMALY_DETECTOR_TABLE_NAME_217`

- 行 218: `column_name = "]home_score["`
  → `column_name = os.getenv("TEST_ANOMALY_DETECTOR_COLUMN_NAME_218")`
  → 环境变量: `TEST_ANOMALY_DETECTOR_COLUMN_NAME_218`

- 行 222: `table_name = "]matches["`
  → `table_name = os.getenv("TEST_ANOMALY_DETECTOR_TABLE_NAME_222")`
  → 环境变量: `TEST_ANOMALY_DETECTOR_TABLE_NAME_222`

- 行 222: `column_name = "]home_score["`
  → `column_name = os.getenv("TEST_ANOMALY_DETECTOR_COLUMN_NAME_222")`
  → 环境变量: `TEST_ANOMALY_DETECTOR_COLUMN_NAME_222`

- 行 230: `table_name = "]matches["`
  → `table_name = os.getenv("TEST_ANOMALY_DETECTOR_TABLE_NAME_230")`
  → 环境变量: `TEST_ANOMALY_DETECTOR_TABLE_NAME_230`

- 行 230: `column_name = "]home_score["`
  → `column_name = os.getenv("TEST_ANOMALY_DETECTOR_COLUMN_NAME_230")`
  → 环境变量: `TEST_ANOMALY_DETECTOR_COLUMN_NAME_230`

- 行 237: `table_name = "matches["`
  → `table_name = os.getenv("TEST_ANOMALY_DETECTOR_TABLE_NAME_237")`
  → 环境变量: `TEST_ANOMALY_DETECTOR_TABLE_NAME_237`

- 行 237: `column_name = "]unknown_column["`
  → `column_name = os.getenv("TEST_ANOMALY_DETECTOR_COLUMN_NAME_237")`
  → 环境变量: `TEST_ANOMALY_DETECTOR_COLUMN_NAME_237`

- 行 241: `table_name = "]matches["`
  → `table_name = os.getenv("TEST_ANOMALY_DETECTOR_TABLE_NAME_241")`
  → 环境变量: `TEST_ANOMALY_DETECTOR_TABLE_NAME_241`

- 行 241: `column_name = "]home_score["`
  → `column_name = os.getenv("TEST_ANOMALY_DETECTOR_COLUMN_NAME_241")`
  → 环境变量: `TEST_ANOMALY_DETECTOR_COLUMN_NAME_241`

- 行 250: `table_name = "]matches["`
  → `table_name = os.getenv("TEST_ANOMALY_DETECTOR_TABLE_NAME_250")`
  → 环境变量: `TEST_ANOMALY_DETECTOR_TABLE_NAME_250`

- 行 250: `column_name = "]status["`
  → `column_name = os.getenv("TEST_ANOMALY_DETECTOR_COLUMN_NAME_250")`
  → 环境变量: `TEST_ANOMALY_DETECTOR_COLUMN_NAME_250`

- 行 258: `table_name = "matches["`
  → `table_name = os.getenv("TEST_ANOMALY_DETECTOR_TABLE_NAME_258")`
  → 环境变量: `TEST_ANOMALY_DETECTOR_TABLE_NAME_258`

- 行 258: `column_name = "]status["`
  → `column_name = os.getenv("TEST_ANOMALY_DETECTOR_COLUMN_NAME_258")`
  → 环境变量: `TEST_ANOMALY_DETECTOR_COLUMN_NAME_258`

- 行 262: `table_name = "]matches["`
  → `table_name = os.getenv("TEST_ANOMALY_DETECTOR_TABLE_NAME_262")`
  → 环境变量: `TEST_ANOMALY_DETECTOR_TABLE_NAME_262`

- 行 262: `column_name = "]match_time["`
  → `column_name = os.getenv("TEST_ANOMALY_DETECTOR_COLUMN_NAME_262")`
  → 环境变量: `TEST_ANOMALY_DETECTOR_COLUMN_NAME_262`

- 行 274: `table_name = "matches["`
  → `table_name = os.getenv("TEST_ANOMALY_DETECTOR_TABLE_NAME_274")`
  → 环境变量: `TEST_ANOMALY_DETECTOR_TABLE_NAME_274`

- 行 275: `column_name = "]match_time["`
  → `column_name = os.getenv("TEST_ANOMALY_DETECTOR_COLUMN_NAME_275")`
  → 环境变量: `TEST_ANOMALY_DETECTOR_COLUMN_NAME_275`

- 行 279: `table_name = "]matches["`
  → `table_name = os.getenv("TEST_ANOMALY_DETECTOR_TABLE_NAME_279")`
  → 环境变量: `TEST_ANOMALY_DETECTOR_TABLE_NAME_279`

- 行 279: `column_name = "]match_time["`
  → `column_name = os.getenv("TEST_ANOMALY_DETECTOR_COLUMN_NAME_279")`
  → 环境变量: `TEST_ANOMALY_DETECTOR_COLUMN_NAME_279`

- 行 297: `table_name="matches["`
  → `table_name = os.getenv("TEST_ANOMALY_DETECTOR_TABLE_NAME_297")`
  → 环境变量: `TEST_ANOMALY_DETECTOR_TABLE_NAME_297`

- 行 297: `column_name="]home_score["`
  → `column_name = os.getenv("TEST_ANOMALY_DETECTOR_COLUMN_NAME_297")`
  → 环境变量: `TEST_ANOMALY_DETECTOR_COLUMN_NAME_297`

- 行 299: `detection_method="]3sigma["`
  → `detection_method = os.getenv("TEST_ANOMALY_DETECTOR_DETECTION_METHOD_299")`
  → 环境变量: `TEST_ANOMALY_DETECTOR_DETECTION_METHOD_299`

- 行 300: `description="]Outlier detected["`
  → `description = os.getenv("TEST_ANOMALY_DETECTOR_DESCRIPTION_300")`
  → 环境变量: `TEST_ANOMALY_DETECTOR_DESCRIPTION_300`

- 行 302: `table_name="]odds["`
  → `table_name = os.getenv("TEST_ANOMALY_DETECTOR_TABLE_NAME_302")`
  → 环境变量: `TEST_ANOMALY_DETECTOR_TABLE_NAME_302`

- 行 302: `column_name="]home_odds["`
  → `column_name = os.getenv("TEST_ANOMALY_DETECTOR_COLUMN_NAME_302")`
  → 环境变量: `TEST_ANOMALY_DETECTOR_COLUMN_NAME_302`

- 行 302: `anomalous_values="]200.0["`
  → `anomalous_values = os.getenv("TEST_ANOMALY_DETECTOR_ANOMALOUS_VALUES_302")`
  → 环境变量: `TEST_ANOMALY_DETECTOR_ANOMALOUS_VALUES_302`

- 行 302: `detection_method="]range_check["`
  → `detection_method = os.getenv("TEST_ANOMALY_DETECTOR_DETECTION_METHOD_302")`
  → 环境变量: `TEST_ANOMALY_DETECTOR_DETECTION_METHOD_302`

- 行 302: `description="]Range violation["`
  → `description = os.getenv("TEST_ANOMALY_DETECTOR_DESCRIPTION_302")`
  → 环境变量: `TEST_ANOMALY_DETECTOR_DESCRIPTION_302`

- 行 302: `table_name="]matches["`
  → `table_name = os.getenv("TEST_ANOMALY_DETECTOR_TABLE_NAME_302")`
  → 环境变量: `TEST_ANOMALY_DETECTOR_TABLE_NAME_302`

- 行 302: `column_name="]away_score["`
  → `column_name = os.getenv("TEST_ANOMALY_DETECTOR_COLUMN_NAME_302")`
  → 环境变量: `TEST_ANOMALY_DETECTOR_COLUMN_NAME_302`

- 行 306: `description="]Negative score["`
  → `description = os.getenv("TEST_ANOMALY_DETECTOR_DESCRIPTION_306")`
  → 环境变量: `TEST_ANOMALY_DETECTOR_DESCRIPTION_306`

### tests/legacy/unit/monitoring/test_quality_monitor_comprehensive.py

- 行 37: `table_name="matches["`
  → `table_name = os.getenv("TEST_QUALITY_MONITOR_COMPREHENSIVE_TABLE_NAME_37")`
  → 环境变量: `TEST_QUALITY_MONITOR_COMPREHENSIVE_TABLE_NAME_37`

- 行 44: `table_name="matches["`
  → `table_name = os.getenv("TEST_QUALITY_MONITOR_COMPREHENSIVE_TABLE_NAME_44")`
  → 环境变量: `TEST_QUALITY_MONITOR_COMPREHENSIVE_TABLE_NAME_44`

- 行 64: `table_name="matches["`
  → `table_name = os.getenv("TEST_QUALITY_MONITOR_COMPREHENSIVE_TABLE_NAME_64")`
  → 环境变量: `TEST_QUALITY_MONITOR_COMPREHENSIVE_TABLE_NAME_64`

### tests/legacy/unit/monitoring/test_ci_monitor.py

- 行 32: `stdout = "https_/github.com/owner/repo.git["`
  → `stdout = os.getenv("TEST_CI_MONITOR_STDOUT_32")`
  → 环境变量: `TEST_CI_MONITOR_STDOUT_32`

- 行 34: `stdout = "]git@github.comowner/repo.git["`
  → `stdout = os.getenv("TEST_CI_MONITOR_STDOUT_34")`
  → 环境变量: `TEST_CI_MONITOR_STDOUT_34`

- 行 55: `token = "]test_token["`
  → `token = os.getenv("TEST_CI_MONITOR_TOKEN_55")`
  → 环境变量: `TEST_CI_MONITOR_TOKEN_55`

- 行 113: `token = "]test_token["`
  → `token = os.getenv("TEST_CI_MONITOR_TOKEN_113")`
  → 环境变量: `TEST_CI_MONITOR_TOKEN_113`

- 行 136: `stdout = "https_/github.com/test/repo.git["`
  → `stdout = os.getenv("TEST_CI_MONITOR_STDOUT_136")`
  → 环境变量: `TEST_CI_MONITOR_STDOUT_136`

### tests/legacy/unit/models/test_prediction_service_complete.py

- 行 25: `mlflow_tracking_uri = "http//localhost5002["`
  → `mlflow_tracking_uri = os.getenv("TEST_PREDICTION_SERVICE_COMPLETE_MLFLOW_TRACKING_U")`
  → 环境变量: `TEST_PREDICTION_SERVICE_COMPLETE_MLFLOW_TRACKING_U`

- 行 82: `return_value = "]1.0.0["`
  → `return_value = os.getenv("TEST_PREDICTION_SERVICE_COMPLETE_RETURN_VALUE_82")`
  → 环境变量: `TEST_PREDICTION_SERVICE_COMPLETE_RETURN_VALUE_82`

- 行 122: `match = "]Network error["`
  → `match = os.getenv("TEST_PREDICTION_SERVICE_COMPLETE_MATCH_122")`
  → 环境变量: `TEST_PREDICTION_SERVICE_COMPLETE_MATCH_122`

- 行 131: `return_value = "]1.0.0["`
  → `return_value = os.getenv("TEST_PREDICTION_SERVICE_COMPLETE_RETURN_VALUE_131")`
  → 环境变量: `TEST_PREDICTION_SERVICE_COMPLETE_RETURN_VALUE_131`

- 行 277: `predicted_result="]home["`
  → `predicted_result = os.getenv("TEST_PREDICTION_SERVICE_COMPLETE_PREDICTED_RESULT_")`
  → 环境变量: `TEST_PREDICTION_SERVICE_COMPLETE_PREDICTED_RESULT_`

- 行 281: `predicted_result="]home["`
  → `predicted_result = os.getenv("TEST_PREDICTION_SERVICE_COMPLETE_PREDICTED_RESULT_")`
  → 环境变量: `TEST_PREDICTION_SERVICE_COMPLETE_PREDICTED_RESULT_`

- 行 287: `predicted_result="]home["`
  → `predicted_result = os.getenv("TEST_PREDICTION_SERVICE_COMPLETE_PREDICTED_RESULT_")`
  → 环境变量: `TEST_PREDICTION_SERVICE_COMPLETE_PREDICTED_RESULT_`

- 行 292: `predicted_result="]home["`
  → `predicted_result = os.getenv("TEST_PREDICTION_SERVICE_COMPLETE_PREDICTED_RESULT_")`
  → 环境变量: `TEST_PREDICTION_SERVICE_COMPLETE_PREDICTED_RESULT_`

- 行 327: `predicted_result="]home["`
  → `predicted_result = os.getenv("TEST_PREDICTION_SERVICE_COMPLETE_PREDICTED_RESULT_")`
  → 环境变量: `TEST_PREDICTION_SERVICE_COMPLETE_PREDICTED_RESULT_`

- 行 335: `predicted_result="]home["`
  → `predicted_result = os.getenv("TEST_PREDICTION_SERVICE_COMPLETE_PREDICTED_RESULT_")`
  → 环境变量: `TEST_PREDICTION_SERVICE_COMPLETE_PREDICTED_RESULT_`

- 行 345: `predicted_result="]home["`
  → `predicted_result = os.getenv("TEST_PREDICTION_SERVICE_COMPLETE_PREDICTED_RESULT_")`
  → 环境变量: `TEST_PREDICTION_SERVICE_COMPLETE_PREDICTED_RESULT_`

### tests/legacy/unit/models/test_model_training_phase53.py

- 行 125: `return_value = 'model_v1'`
  → `return_value = os.getenv("TEST_MODEL_TRAINING_PHASE53_RETURN_VALUE_125")`
  → 环境变量: `TEST_MODEL_TRAINING_PHASE53_RETURN_VALUE_125`

- 行 171: `return_value='classification_report'`
  → `return_value = os.getenv("TEST_MODEL_TRAINING_PHASE53_RETURN_VALUE_171")`
  → 环境变量: `TEST_MODEL_TRAINING_PHASE53_RETURN_VALUE_171`

- 行 197: `run_id='test_run'`
  → `run_id = os.getenv("TEST_MODEL_TRAINING_PHASE53_RUN_ID_197")`
  → 环境变量: `TEST_MODEL_TRAINING_PHASE53_RUN_ID_197`

### tests/legacy/unit/models/test_model_training.py

- 行 64: `season = "2023-24["`
  → `season = os.getenv("TEST_MODEL_TRAINING_SEASON_64")`
  → 环境变量: `TEST_MODEL_TRAINING_SEASON_64`

- 行 93: `match = "]]训练数据不足["`
  → `match = os.getenv("TEST_MODEL_TRAINING_MATCH_93")`
  → 环境变量: `TEST_MODEL_TRAINING_MATCH_93`

- 行 209: `model_name = "test_model["`
  → `model_name = os.getenv("TEST_MODEL_TRAINING_MODEL_NAME_209")`
  → 环境变量: `TEST_MODEL_TRAINING_MODEL_NAME_209`

- 行 219: `stage="]Production["`
  → `stage = os.getenv("TEST_MODEL_TRAINING_STAGE_219")`
  → 环境变量: `TEST_MODEL_TRAINING_STAGE_219`

- 行 222: `run_id = "test_run_123["`
  → `run_id = os.getenv("TEST_MODEL_TRAINING_RUN_ID_222")`
  → 环境变量: `TEST_MODEL_TRAINING_RUN_ID_222`

- 行 242: `run_id = "]test_run_456["`
  → `run_id = os.getenv("TEST_MODEL_TRAINING_RUN_ID_242")`
  → 环境变量: `TEST_MODEL_TRAINING_RUN_ID_242`

### tests/legacy/unit/models/test_prediction_service_mocked.py

- 行 72: `match = "]数据库连接失败["`
  → `match = os.getenv("TEST_PREDICTION_SERVICE_MOCKED_MATCH_72")`
  → 环境变量: `TEST_PREDICTION_SERVICE_MOCKED_MATCH_72`

### tests/legacy/unit/models/test_prediction_service_final.py

- 行 78: `match_status = "scheduled["`
  → `match_status = os.getenv("TEST_PREDICTION_SERVICE_FINAL_MATCH_STATUS_78")`
  → 环境变量: `TEST_PREDICTION_SERVICE_FINAL_MATCH_STATUS_78`

- 行 78: `season = "]2023-2024["`
  → `season = os.getenv("TEST_PREDICTION_SERVICE_FINAL_SEASON_78")`
  → 环境变量: `TEST_PREDICTION_SERVICE_FINAL_SEASON_78`

- 行 168: `predicted_result="]home["`
  → `predicted_result = os.getenv("TEST_PREDICTION_SERVICE_FINAL_PREDICTED_RESULT_168")`
  → 环境变量: `TEST_PREDICTION_SERVICE_FINAL_PREDICTED_RESULT_168`

- 行 249: `match_status = "scheduled["`
  → `match_status = os.getenv("TEST_PREDICTION_SERVICE_FINAL_MATCH_STATUS_249")`
  → 环境变量: `TEST_PREDICTION_SERVICE_FINAL_MATCH_STATUS_249`

- 行 250: `season = "]2023-2024["`
  → `season = os.getenv("TEST_PREDICTION_SERVICE_FINAL_SEASON_250")`
  → 环境变量: `TEST_PREDICTION_SERVICE_FINAL_SEASON_250`

### tests/legacy/unit/models/test_prediction_service_caching.py

- 行 59: `current_stage = "]Production["`
  → `current_stage = os.getenv("TEST_PREDICTION_SERVICE_CACHING_CURRENT_STAGE_59")`
  → 环境变量: `TEST_PREDICTION_SERVICE_CACHING_CURRENT_STAGE_59`

- 行 79: `current_stage = "]Production["`
  → `current_stage = os.getenv("TEST_PREDICTION_SERVICE_CACHING_CURRENT_STAGE_79")`
  → 环境变量: `TEST_PREDICTION_SERVICE_CACHING_CURRENT_STAGE_79`

- 行 84: `cache_key = "]modelfootball_baseline_model["`
  → `cache_key = os.getenv("TEST_PREDICTION_SERVICE_CACHING_CACHE_KEY_84")`
  → 环境变量: `TEST_PREDICTION_SERVICE_CACHING_CACHE_KEY_84`

### tests/legacy/unit/models/test_model_training_basic.py

- 行 75: `match = "]]训练数据不足["`
  → `match = os.getenv("TEST_MODEL_TRAINING_BASIC_MATCH_75")`
  → 环境变量: `TEST_MODEL_TRAINING_BASIC_MATCH_75`

### tests/legacy/unit/models/test_prediction_service_basic.py

- 行 47: `match = "]模型加载失败["`
  → `match = os.getenv("TEST_PREDICTION_SERVICE_BASIC_MATCH_47")`
  → 环境变量: `TEST_PREDICTION_SERVICE_BASIC_MATCH_47`

- 行 81: `predicted_result="home_win["`
  → `predicted_result = os.getenv("TEST_PREDICTION_SERVICE_BASIC_PREDICTED_RESULT_81")`
  → 环境变量: `TEST_PREDICTION_SERVICE_BASIC_PREDICTED_RESULT_81`

- 行 82: `model_version="]v1.0["`
  → `model_version = os.getenv("TEST_PREDICTION_SERVICE_BASIC_MODEL_VERSION_82")`
  → 环境变量: `TEST_PREDICTION_SERVICE_BASIC_MODEL_VERSION_82`

- 行 100: `match = "]数据库连接失败["`
  → `match = os.getenv("TEST_PREDICTION_SERVICE_BASIC_MATCH_100")`
  → 环境变量: `TEST_PREDICTION_SERVICE_BASIC_MATCH_100`

### tests/legacy/unit/models/test_prediction_service_core.py

- 行 210: `_ = "models / prediction_model.pkl["`
  → `_ = os.getenv("TEST_PREDICTION_SERVICE_CORE___210")`
  → 环境变量: `TEST_PREDICTION_SERVICE_CORE___210`

- 行 483: `_ = "not a dataframe["`
  → `_ = os.getenv("TEST_PREDICTION_SERVICE_CORE___483")`
  → 环境变量: `TEST_PREDICTION_SERVICE_CORE___483`

### tests/legacy/unit/models/test_prediction_service_simplified.py

- 行 129: `match = "]模型加载失败["`
  → `match = os.getenv("TEST_PREDICTION_SERVICE_SIMPLIFIED_MATCH_129")`
  → 环境变量: `TEST_PREDICTION_SERVICE_SIMPLIFIED_MATCH_129`

### tests/legacy/unit/models/test_model_training_simplified.py

- 行 82: `match = "]]训练数据不足["`
  → `match = os.getenv("TEST_MODEL_TRAINING_SIMPLIFIED_MATCH_82")`
  → 环境变量: `TEST_MODEL_TRAINING_SIMPLIFIED_MATCH_82`

- 行 150: `match = "]特征存储错误["`
  → `match = os.getenv("TEST_MODEL_TRAINING_SIMPLIFIED_MATCH_150")`
  → 环境变量: `TEST_MODEL_TRAINING_SIMPLIFIED_MATCH_150`

### tests/legacy/unit/models/test_coverage_improvements.py

- 行 31: `current_stage = "]Staging["`
  → `current_stage = os.getenv("TEST_COVERAGE_IMPROVEMENTS_CURRENT_STAGE_31")`
  → 环境变量: `TEST_COVERAGE_IMPROVEMENTS_CURRENT_STAGE_31`

- 行 31: `version = "]0.8.0-latest["`
  → `version = os.getenv("TEST_COVERAGE_IMPROVEMENTS_VERSION_31")`
  → 环境变量: `TEST_COVERAGE_IMPROVEMENTS_VERSION_31`

- 行 31: `current_stage = "]None["`
  → `current_stage = os.getenv("TEST_COVERAGE_IMPROVEMENTS_CURRENT_STAGE_31")`
  → 环境变量: `TEST_COVERAGE_IMPROVEMENTS_CURRENT_STAGE_31`

- 行 62: `match_status = "scheduled["`
  → `match_status = os.getenv("TEST_COVERAGE_IMPROVEMENTS_MATCH_STATUS_62")`
  → 环境变量: `TEST_COVERAGE_IMPROVEMENTS_MATCH_STATUS_62`

- 行 63: `season = "]2024["`
  → `season = os.getenv("TEST_COVERAGE_IMPROVEMENTS_SEASON_63")`
  → 环境变量: `TEST_COVERAGE_IMPROVEMENTS_SEASON_63`

### tests/legacy/unit/models/test_prediction_service_comprehensive.py

- 行 25: `predicted_result="]home["`
  → `predicted_result = os.getenv("TEST_PREDICTION_SERVICE_COMPREHENSIVE_PREDICTED_RE")`
  → 环境变量: `TEST_PREDICTION_SERVICE_COMPREHENSIVE_PREDICTED_RE`

- 行 65: `mlflow_tracking_uri="http:_/test5002["`
  → `mlflow_tracking_uri = os.getenv("TEST_PREDICTION_SERVICE_COMPREHENSIVE_MLFLOW_TRACK")`
  → 环境变量: `TEST_PREDICTION_SERVICE_COMPREHENSIVE_MLFLOW_TRACK`

- 行 75: `current_stage = "]Production["`
  → `current_stage = os.getenv("TEST_PREDICTION_SERVICE_COMPREHENSIVE_CURRENT_STAG")`
  → 环境变量: `TEST_PREDICTION_SERVICE_COMPREHENSIVE_CURRENT_STAG`

- 行 83: `current_stage = "]Staging["`
  → `current_stage = os.getenv("TEST_PREDICTION_SERVICE_COMPREHENSIVE_CURRENT_STAG")`
  → 环境变量: `TEST_PREDICTION_SERVICE_COMPREHENSIVE_CURRENT_STAG`

- 行 99: `match = "]]模型 test_model 没有可用版本["`
  → `match = os.getenv("TEST_PREDICTION_SERVICE_COMPREHENSIVE_MATCH_99")`
  → 环境变量: `TEST_PREDICTION_SERVICE_COMPREHENSIVE_MATCH_99`

- 行 104: `current_stage = "]Production["`
  → `current_stage = os.getenv("TEST_PREDICTION_SERVICE_COMPREHENSIVE_CURRENT_STAG")`
  → 环境变量: `TEST_PREDICTION_SERVICE_COMPREHENSIVE_CURRENT_STAG`

- 行 164: `match = "]比赛 999 不存在["`
  → `match = os.getenv("TEST_PREDICTION_SERVICE_COMPREHENSIVE_MATCH_164")`
  → 环境变量: `TEST_PREDICTION_SERVICE_COMPREHENSIVE_MATCH_164`

### tests/legacy/unit/models/test_prediction_service_minimal.py

- 行 106: `match = "]数据库连接失败["`
  → `match = os.getenv("TEST_PREDICTION_SERVICE_MINIMAL_MATCH_106")`
  → 环境变量: `TEST_PREDICTION_SERVICE_MINIMAL_MATCH_106`

### tests/legacy/unit/models/test_prediction_service.py

- 行 19: `predicted_result="]home["`
  → `predicted_result = os.getenv("TEST_PREDICTION_SERVICE_PREDICTED_RESULT_19")`
  → 环境变量: `TEST_PREDICTION_SERVICE_PREDICTED_RESULT_19`

- 行 60: `current_stage = "]Production["`
  → `current_stage = os.getenv("TEST_PREDICTION_SERVICE_CURRENT_STAGE_60")`
  → 环境变量: `TEST_PREDICTION_SERVICE_CURRENT_STAGE_60`

- 行 66: `model_name = "football_baseline_model["`
  → `model_name = os.getenv("TEST_PREDICTION_SERVICE_MODEL_NAME_66")`
  → 环境变量: `TEST_PREDICTION_SERVICE_MODEL_NAME_66`

- 行 84: `current_stage = "]Staging["`
  → `current_stage = os.getenv("TEST_PREDICTION_SERVICE_CURRENT_STAGE_84")`
  → 环境变量: `TEST_PREDICTION_SERVICE_CURRENT_STAGE_84`

- 行 100: `match="]]模型 football_baseline_model 没有可用版本["`
  → `match = os.getenv("TEST_PREDICTION_SERVICE_MATCH_100")`
  → 环境变量: `TEST_PREDICTION_SERVICE_MATCH_100`

- 行 127: `match = "]mlflow down["`
  → `match = os.getenv("TEST_PREDICTION_SERVICE_MATCH_127")`
  → 环境变量: `TEST_PREDICTION_SERVICE_MATCH_127`

- 行 166: `match_status = "scheduled["`
  → `match_status = os.getenv("TEST_PREDICTION_SERVICE_MATCH_STATUS_166")`
  → 环境变量: `TEST_PREDICTION_SERVICE_MATCH_STATUS_166`

- 行 167: `season = "]2023-24["`
  → `season = os.getenv("TEST_PREDICTION_SERVICE_SEASON_167")`
  → 环境变量: `TEST_PREDICTION_SERVICE_SEASON_167`

- 行 189: `predicted_result="]home["`
  → `predicted_result = os.getenv("TEST_PREDICTION_SERVICE_PREDICTED_RESULT_189")`
  → 环境变量: `TEST_PREDICTION_SERVICE_PREDICTED_RESULT_189`

- 行 198: `model_version="]]v1.0["`
  → `model_version = os.getenv("TEST_PREDICTION_SERVICE_MODEL_VERSION_198")`
  → 环境变量: `TEST_PREDICTION_SERVICE_MODEL_VERSION_198`

- 行 199: `match = "]Database error["`
  → `match = os.getenv("TEST_PREDICTION_SERVICE_MATCH_199")`
  → 环境变量: `TEST_PREDICTION_SERVICE_MATCH_199`

- 行 259: `match = "]比赛 999 不存在["`
  → `match = os.getenv("TEST_PREDICTION_SERVICE_MATCH_259")`
  → 环境变量: `TEST_PREDICTION_SERVICE_MATCH_259`

- 行 267: `match_status = "completed["`
  → `match_status = os.getenv("TEST_PREDICTION_SERVICE_MATCH_STATUS_267")`
  → 环境变量: `TEST_PREDICTION_SERVICE_MATCH_STATUS_267`

- 行 338: `model_version="]v1.0["`
  → `model_version = os.getenv("TEST_PREDICTION_SERVICE_MODEL_VERSION_338")`
  → 环境变量: `TEST_PREDICTION_SERVICE_MODEL_VERSION_338`

### tests/legacy/unit/models/test_model_training_complete.py

- 行 23: `model_type="xgboost["`
  → `model_type = os.getenv("TEST_MODEL_TRAINING_COMPLETE_MODEL_TYPE_23")`
  → 环境变量: `TEST_MODEL_TRAINING_COMPLETE_MODEL_TYPE_23`

- 行 33: `experiment_name="]football_prediction["`
  → `experiment_name = os.getenv("TEST_MODEL_TRAINING_COMPLETE_EXPERIMENT_NAME_33")`
  → 环境变量: `TEST_MODEL_TRAINING_COMPLETE_EXPERIMENT_NAME_33`

- 行 86: `experiment_name="]custom_experiment["`
  → `experiment_name = os.getenv("TEST_MODEL_TRAINING_COMPLETE_EXPERIMENT_NAME_86")`
  → 环境变量: `TEST_MODEL_TRAINING_COMPLETE_EXPERIMENT_NAME_86`

- 行 87: `model_type="xgboost["`
  → `model_type = os.getenv("TEST_MODEL_TRAINING_COMPLETE_MODEL_TYPE_87")`
  → 环境变量: `TEST_MODEL_TRAINING_COMPLETE_MODEL_TYPE_87`

- 行 94: `model_type="]]invalid_model["`
  → `model_type = os.getenv("TEST_MODEL_TRAINING_COMPLETE_MODEL_TYPE_94")`
  → 环境变量: `TEST_MODEL_TRAINING_COMPLETE_MODEL_TYPE_94`

- 行 106: `seasons="]]2024["`
  → `seasons = os.getenv("TEST_MODEL_TRAINING_COMPLETE_SEASONS_106")`
  → 环境变量: `TEST_MODEL_TRAINING_COMPLETE_SEASONS_106`

- 行 205: `seasons="]]2024["`
  → `seasons = os.getenv("TEST_MODEL_TRAINING_COMPLETE_SEASONS_205")`
  → 环境变量: `TEST_MODEL_TRAINING_COMPLETE_SEASONS_205`

- 行 220: `seasons="]2024["`
  → `seasons = os.getenv("TEST_MODEL_TRAINING_COMPLETE_SEASONS_220")`
  → 环境变量: `TEST_MODEL_TRAINING_COMPLETE_SEASONS_220`

- 行 304: `return_value = "]model_uri["`
  → `return_value = os.getenv("TEST_MODEL_TRAINING_COMPLETE_RETURN_VALUE_304")`
  → 环境变量: `TEST_MODEL_TRAINING_COMPLETE_RETURN_VALUE_304`

- 行 309: `run_name="]test_run["`
  → `run_name = os.getenv("TEST_MODEL_TRAINING_COMPLETE_RUN_NAME_309")`
  → 环境变量: `TEST_MODEL_TRAINING_COMPLETE_RUN_NAME_309`

- 行 309: `return_value = "]experiment_id["`
  → `return_value = os.getenv("TEST_MODEL_TRAINING_COMPLETE_RETURN_VALUE_309")`
  → 环境变量: `TEST_MODEL_TRAINING_COMPLETE_RETURN_VALUE_309`

- 行 321: `run_name="]test_run["`
  → `run_name = os.getenv("TEST_MODEL_TRAINING_COMPLETE_RUN_NAME_321")`
  → 环境变量: `TEST_MODEL_TRAINING_COMPLETE_RUN_NAME_321`

### tests/legacy/unit/ai/test_model_evaluation.py

- 行 40: `model_name="football_baseline_model"`
  → `model_name = os.getenv("TEST_MODEL_EVALUATION_MODEL_NAME_40")`
  → 环境变量: `TEST_MODEL_EVALUATION_MODEL_NAME_40`

### tests/legacy/unit/streaming/test_kafka_consumer_new.py

- 行 54: `match = "]连接失败["`
  → `match = os.getenv("TEST_KAFKA_CONSUMER_NEW_MATCH_54")`
  → 环境变量: `TEST_KAFKA_CONSUMER_NEW_MATCH_54`

- 行 63: `topics = "test-topic["`
  → `topics = os.getenv("TEST_KAFKA_CONSUMER_NEW_TOPICS_63")`
  → 环境变量: `TEST_KAFKA_CONSUMER_NEW_TOPICS_63`

- 行 67: `topic = "]test-topic["`
  → `topic = os.getenv("TEST_KAFKA_CONSUMER_NEW_TOPIC_67")`
  → 环境变量: `TEST_KAFKA_CONSUMER_NEW_TOPIC_67`

- 行 108: `topic = "test-topic["`
  → `topic = os.getenv("TEST_KAFKA_CONSUMER_NEW_TOPIC_108")`
  → 环境变量: `TEST_KAFKA_CONSUMER_NEW_TOPIC_108`

### tests/legacy/unit/streaming/test_stream_config.py

- 行 40: `bootstrap_servers = "kafka-server9092["`
  → `bootstrap_servers = os.getenv("TEST_STREAM_CONFIG_BOOTSTRAP_SERVERS_40")`
  → 环境变量: `TEST_STREAM_CONFIG_BOOTSTRAP_SERVERS_40`

- 行 40: `security_protocol="]SASL_SSL["`
  → `security_protocol = os.getenv("TEST_STREAM_CONFIG_SECURITY_PROTOCOL_40")`
  → 环境变量: `TEST_STREAM_CONFIG_SECURITY_PROTOCOL_40`

- 行 40: `producer_client_id="]custom-producer["`
  → `producer_client_id = os.getenv("TEST_STREAM_CONFIG_PRODUCER_CLIENT_ID_40")`
  → 环境变量: `TEST_STREAM_CONFIG_PRODUCER_CLIENT_ID_40`

- 行 40: `consumer_group_id="]custom-group["`
  → `consumer_group_id = os.getenv("TEST_STREAM_CONFIG_CONSUMER_GROUP_ID_40")`
  → 环境变量: `TEST_STREAM_CONFIG_CONSUMER_GROUP_ID_40`

- 行 40: `consumer_client_id="]custom-consumer["`
  → `consumer_client_id = os.getenv("TEST_STREAM_CONFIG_CONSUMER_CLIENT_ID_40")`
  → 环境变量: `TEST_STREAM_CONFIG_CONSUMER_CLIENT_ID_40`

- 行 40: `consumer_auto_offset_reset="]earliest["`
  → `consumer_auto_offset_reset = os.getenv("TEST_STREAM_CONFIG_CONSUMER_AUTO_OFFSET_RESET_40")`
  → 环境变量: `TEST_STREAM_CONFIG_CONSUMER_AUTO_OFFSET_RESET_40`

- 行 40: `key_serializer="]avro["`
  → `key_serializer = os.getenv("TEST_STREAM_CONFIG_KEY_SERIALIZER_40")`
  → 环境变量: `TEST_STREAM_CONFIG_KEY_SERIALIZER_40`

- 行 40: `value_serializer="]avro["`
  → `value_serializer = os.getenv("TEST_STREAM_CONFIG_VALUE_SERIALIZER_40")`
  → 环境变量: `TEST_STREAM_CONFIG_VALUE_SERIALIZER_40`

- 行 76: `name="test-topic["`
  → `name = os.getenv("TEST_STREAM_CONFIG_NAME_76")`
  → 环境变量: `TEST_STREAM_CONFIG_NAME_76`

- 行 83: `name="custom-topic["`
  → `name = os.getenv("TEST_STREAM_CONFIG_NAME_83")`
  → 环境变量: `TEST_STREAM_CONFIG_NAME_83`

- 行 84: `cleanup_policy="]compact["`
  → `cleanup_policy = os.getenv("TEST_STREAM_CONFIG_CLEANUP_POLICY_84")`
  → 环境变量: `TEST_STREAM_CONFIG_CLEANUP_POLICY_84`

- 行 226: `custom_group = "custom-test-group["`
  → `custom_group = os.getenv("TEST_STREAM_CONFIG_CUSTOM_GROUP_226")`
  → 环境变量: `TEST_STREAM_CONFIG_CUSTOM_GROUP_226`

- 行 258: `name="]new-topic["`
  → `name = os.getenv("TEST_STREAM_CONFIG_NAME_258")`
  → 环境变量: `TEST_STREAM_CONFIG_NAME_258`

- 行 327: `bootstrap_servers = "kafka:9092,another-kafka9093["`
  → `bootstrap_servers = os.getenv("TEST_STREAM_CONFIG_BOOTSTRAP_SERVERS_327")`
  → 环境变量: `TEST_STREAM_CONFIG_BOOTSTRAP_SERVERS_327`

- 行 329: `security_protocol="]SASL_SSL["`
  → `security_protocol = os.getenv("TEST_STREAM_CONFIG_SECURITY_PROTOCOL_329")`
  → 环境变量: `TEST_STREAM_CONFIG_SECURITY_PROTOCOL_329`

- 行 330: `producer_client_id="]producer@test#123["`
  → `producer_client_id = os.getenv("TEST_STREAM_CONFIG_PRODUCER_CLIENT_ID_330")`
  → 环境变量: `TEST_STREAM_CONFIG_PRODUCER_CLIENT_ID_330`

- 行 340: `name="测试主题-中文-🚀"`
  → `name = os.getenv("TEST_STREAM_CONFIG_NAME_340")`
  → 环境变量: `TEST_STREAM_CONFIG_NAME_340`

- 行 341: `name="large-topic["`
  → `name = os.getenv("TEST_STREAM_CONFIG_NAME_341")`
  → 环境变量: `TEST_STREAM_CONFIG_NAME_341`

### tests/legacy/unit/streaming/test_kafka_consumer_batch_delta_033.py

- 行 32: `matches = "]]matches-topic["`
  → `matches = os.getenv("TEST_KAFKA_CONSUMER_BATCH_DELTA_033_MATCHES_32")`
  → 环境变量: `TEST_KAFKA_CONSUMER_BATCH_DELTA_033_MATCHES_32`

- 行 32: `odds = "]odds-topic["`
  → `odds = os.getenv("TEST_KAFKA_CONSUMER_BATCH_DELTA_033_ODDS_32")`
  → 环境变量: `TEST_KAFKA_CONSUMER_BATCH_DELTA_033_ODDS_32`

- 行 32: `scores = "]scores-topic["`
  → `scores = os.getenv("TEST_KAFKA_CONSUMER_BATCH_DELTA_033_SCORES_32")`
  → 环境变量: `TEST_KAFKA_CONSUMER_BATCH_DELTA_033_SCORES_32`

- 行 46: `return_value = "matches-topic["`
  → `return_value = os.getenv("TEST_KAFKA_CONSUMER_BATCH_DELTA_033_RETURN_VALUE_4")`
  → 环境变量: `TEST_KAFKA_CONSUMER_BATCH_DELTA_033_RETURN_VALUE_4`

- 行 81: `consumer_group_id="]]custom_group["`
  → `consumer_group_id = os.getenv("TEST_KAFKA_CONSUMER_BATCH_DELTA_033_CONSUMER_GROUP")`
  → 环境变量: `TEST_KAFKA_CONSUMER_BATCH_DELTA_033_CONSUMER_GROUP`

- 行 89: `match = "]Kafka连接失败["`
  → `match = os.getenv("TEST_KAFKA_CONSUMER_BATCH_DELTA_033_MATCH_89")`
  → 环境变量: `TEST_KAFKA_CONSUMER_BATCH_DELTA_033_MATCH_89`

- 行 228: `topics = "matches-topic["`
  → `topics = os.getenv("TEST_KAFKA_CONSUMER_BATCH_DELTA_033_TOPICS_228")`
  → 环境变量: `TEST_KAFKA_CONSUMER_BATCH_DELTA_033_TOPICS_228`

- 行 416: `topics = "]test-topic["`
  → `topics = os.getenv("TEST_KAFKA_CONSUMER_BATCH_DELTA_033_TOPICS_416")`
  → 环境变量: `TEST_KAFKA_CONSUMER_BATCH_DELTA_033_TOPICS_416`

- 行 416: `match = "]订阅失败["`
  → `match = os.getenv("TEST_KAFKA_CONSUMER_BATCH_DELTA_033_MATCH_416")`
  → 环境变量: `TEST_KAFKA_CONSUMER_BATCH_DELTA_033_MATCH_416`

### tests/legacy/unit/streaming/test_stream_config_and_producer.py

- 行 46: `data_type="]match["`
  → `data_type = os.getenv("TEST_STREAM_CONFIG_AND_PRODUCER_DATA_TYPE_46")`
  → 环境变量: `TEST_STREAM_CONFIG_AND_PRODUCER_DATA_TYPE_46`

- 行 46: `data_type="]odds["`
  → `data_type = os.getenv("TEST_STREAM_CONFIG_AND_PRODUCER_DATA_TYPE_46")`
  → 环境变量: `TEST_STREAM_CONFIG_AND_PRODUCER_DATA_TYPE_46`

### tests/legacy/unit/streaming/test_streaming.py

- 行 51: `KAFKA_BOOTSTRAP_SERVERS = "localhost9092["`
  → `KAFKA_BOOTSTRAP_SERVERS = os.getenv("TEST_STREAMING_KAFKA_BOOTSTRAP_SERVERS_51")`
  → 环境变量: `TEST_STREAMING_KAFKA_BOOTSTRAP_SERVERS_51`

- 行 51: `KAFKA_GROUP_ID="]football-data-consumers["`
  → `KAFKA_GROUP_ID = os.getenv("TEST_STREAMING_KAFKA_GROUP_ID_51")`
  → 环境变量: `TEST_STREAMING_KAFKA_GROUP_ID_51`

- 行 285: `topic="test-topic["`
  → `topic = os.getenv("TEST_STREAMING_TOPIC_285")`
  → 环境变量: `TEST_STREAMING_TOPIC_285`

- 行 771: `data_source="]]test_source["`
  → `data_source = os.getenv("TEST_STREAMING_DATA_SOURCE_771")`
  → 环境变量: `TEST_STREAMING_DATA_SOURCE_771`

- 行 771: `collection_type="]fixtures["`
  → `collection_type = os.getenv("TEST_STREAMING_COLLECTION_TYPE_771")`
  → 环境变量: `TEST_STREAMING_COLLECTION_TYPE_771`

- 行 772: `status="]success["`
  → `status = os.getenv("TEST_STREAMING_STATUS_772")`
  → 环境变量: `TEST_STREAMING_STATUS_772`

- 行 790: `data_source="]]test_source["`
  → `data_source = os.getenv("TEST_STREAMING_DATA_SOURCE_790")`
  → 环境变量: `TEST_STREAMING_DATA_SOURCE_790`

- 行 791: `collection_type="]odds["`
  → `collection_type = os.getenv("TEST_STREAMING_COLLECTION_TYPE_791")`
  → 环境变量: `TEST_STREAMING_COLLECTION_TYPE_791`

- 行 793: `status="]success["`
  → `status = os.getenv("TEST_STREAMING_STATUS_793")`
  → 环境变量: `TEST_STREAMING_STATUS_793`

- 行 810: `data_source="]]test_source["`
  → `data_source = os.getenv("TEST_STREAMING_DATA_SOURCE_810")`
  → 环境变量: `TEST_STREAMING_DATA_SOURCE_810`

- 行 810: `collection_type="]live_scores["`
  → `collection_type = os.getenv("TEST_STREAMING_COLLECTION_TYPE_810")`
  → 环境变量: `TEST_STREAMING_COLLECTION_TYPE_810`

- 行 812: `status="]success["`
  → `status = os.getenv("TEST_STREAMING_STATUS_812")`
  → 环境变量: `TEST_STREAMING_STATUS_812`

### tests/legacy/unit/streaming/test_kafka_consumer_comprehensive.py

- 行 25: `kafka_servers = "localhost9092["`
  → `kafka_servers = os.getenv("TEST_KAFKA_CONSUMER_COMPREHENSIVE_KAFKA_SERVERS_25")`
  → 环境变量: `TEST_KAFKA_CONSUMER_COMPREHENSIVE_KAFKA_SERVERS_25`

- 行 25: `kafka_group_id = "]football_consumer_group["`
  → `kafka_group_id = os.getenv("TEST_KAFKA_CONSUMER_COMPREHENSIVE_KAFKA_GROUP_ID_2")`
  → 环境变量: `TEST_KAFKA_CONSUMER_COMPREHENSIVE_KAFKA_GROUP_ID_2`

- 行 25: `kafka_auto_offset_reset = "]earliest["`
  → `kafka_auto_offset_reset = os.getenv("TEST_KAFKA_CONSUMER_COMPREHENSIVE_KAFKA_AUTO_OFFSE")`
  → 环境变量: `TEST_KAFKA_CONSUMER_COMPREHENSIVE_KAFKA_AUTO_OFFSE`

- 行 71: `topic = "matches["`
  → `topic = os.getenv("TEST_KAFKA_CONSUMER_COMPREHENSIVE_TOPIC_71")`
  → 环境变量: `TEST_KAFKA_CONSUMER_COMPREHENSIVE_TOPIC_71`

- 行 100: `consumer_group_id="custom_group["`
  → `consumer_group_id = os.getenv("TEST_KAFKA_CONSUMER_COMPREHENSIVE_CONSUMER_GROUP_I")`
  → 环境变量: `TEST_KAFKA_CONSUMER_COMPREHENSIVE_CONSUMER_GROUP_I`

- 行 501: `custom_group_id = "custom_consumer_group["`
  → `custom_group_id = os.getenv("TEST_KAFKA_CONSUMER_COMPREHENSIVE_CUSTOM_GROUP_ID_")`
  → 环境变量: `TEST_KAFKA_CONSUMER_COMPREHENSIVE_CUSTOM_GROUP_ID_`

### tests/legacy/unit/streaming/test_kafka_consumer.py

- 行 59: `topics = "matches-stream["`
  → `topics = os.getenv("TEST_KAFKA_CONSUMER_TOPICS_59")`
  → 环境变量: `TEST_KAFKA_CONSUMER_TOPICS_59`

- 行 219: `topics="matches-stream["`
  → `topics = os.getenv("TEST_KAFKA_CONSUMER_TOPICS_219")`
  → 环境变量: `TEST_KAFKA_CONSUMER_TOPICS_219`

- 行 235: `topics = "matches-stream["`
  → `topics = os.getenv("TEST_KAFKA_CONSUMER_TOPICS_235")`
  → 环境变量: `TEST_KAFKA_CONSUMER_TOPICS_235`

- 行 242: `topics = "matches-stream["`
  → `topics = os.getenv("TEST_KAFKA_CONSUMER_TOPICS_242")`
  → 环境变量: `TEST_KAFKA_CONSUMER_TOPICS_242`

- 行 286: `topics = "]matches-stream["`
  → `topics = os.getenv("TEST_KAFKA_CONSUMER_TOPICS_286")`
  → 环境变量: `TEST_KAFKA_CONSUMER_TOPICS_286`

### tests/legacy/unit/streaming/test_kafka_producer_simple.py

- 行 51: `match = "]连接失败["`
  → `match = os.getenv("TEST_KAFKA_PRODUCER_SIMPLE_MATCH_51")`
  → 环境变量: `TEST_KAFKA_PRODUCER_SIMPLE_MATCH_51`

- 行 63: `topic = "test-topic["`
  → `topic = os.getenv("TEST_KAFKA_PRODUCER_SIMPLE_TOPIC_63")`
  → 环境变量: `TEST_KAFKA_PRODUCER_SIMPLE_TOPIC_63`

- 行 65: `key = "]test-key["`
  → `key = os.getenv("TEST_KAFKA_PRODUCER_SIMPLE_KEY_65")`
  → 环境变量: `TEST_KAFKA_PRODUCER_SIMPLE_KEY_65`

- 行 67: `topic = "test-topic["`
  → `topic = os.getenv("TEST_KAFKA_PRODUCER_SIMPLE_TOPIC_67")`
  → 环境变量: `TEST_KAFKA_PRODUCER_SIMPLE_TOPIC_67`

- 行 71: `topic = "test-topic["`
  → `topic = os.getenv("TEST_KAFKA_PRODUCER_SIMPLE_TOPIC_71")`
  → 环境变量: `TEST_KAFKA_PRODUCER_SIMPLE_TOPIC_71`

### tests/legacy/unit/streaming/test_kafka_producer.py

- 行 98: `custom_key = "custom_key_123["`
  → `custom_key = os.getenv("TEST_KAFKA_PRODUCER_CUSTOM_KEY_98")`
  → 环境变量: `TEST_KAFKA_PRODUCER_CUSTOM_KEY_98`

- 行 232: `return_value = "matches-stream["`
  → `return_value = os.getenv("TEST_KAFKA_PRODUCER_RETURN_VALUE_232")`
  → 环境变量: `TEST_KAFKA_PRODUCER_RETURN_VALUE_232`

- 行 233: `return_value = "]match_1["`
  → `return_value = os.getenv("TEST_KAFKA_PRODUCER_RETURN_VALUE_233")`
  → 环境变量: `TEST_KAFKA_PRODUCER_RETURN_VALUE_233`

### tests/legacy/unit/database/test_connection_core.py

- 行 69: `return_value = "]postgresql://testtest@localhost/test["`
  → `return_value = os.getenv("TEST_CONNECTION_CORE_RETURN_VALUE_69")`
  → 环境变量: `TEST_CONNECTION_CORE_RETURN_VALUE_69`

### tests/legacy/unit/cache/test_ttl_cache.py

- 行 38: `value = "test_value["`
  → `value = os.getenv("TEST_TTL_CACHE_VALUE_38")`
  → 环境变量: `TEST_TTL_CACHE_VALUE_38`

- 行 42: `value = "test_value["`
  → `value = os.getenv("TEST_TTL_CACHE_VALUE_42")`
  → 环境变量: `TEST_TTL_CACHE_VALUE_42`

- 行 46: `value = "test_value["`
  → `value = os.getenv("TEST_TTL_CACHE_VALUE_46")`
  → 环境变量: `TEST_TTL_CACHE_VALUE_46`

- 行 49: `value = "test_value["`
  → `value = os.getenv("TEST_TTL_CACHE_VALUE_49")`
  → 环境变量: `TEST_TTL_CACHE_VALUE_49`

- 行 51: `value = "test_value["`
  → `value = os.getenv("TEST_TTL_CACHE_VALUE_51")`
  → 环境变量: `TEST_TTL_CACHE_VALUE_51`

- 行 53: `value = "test_value["`
  → `value = os.getenv("TEST_TTL_CACHE_VALUE_53")`
  → 环境变量: `TEST_TTL_CACHE_VALUE_53`

- 行 59: `value = "test_value["`
  → `value = os.getenv("TEST_TTL_CACHE_VALUE_59")`
  → 环境变量: `TEST_TTL_CACHE_VALUE_59`

- 行 64: `value = "test_value["`
  → `value = os.getenv("TEST_TTL_CACHE_VALUE_64")`
  → 环境变量: `TEST_TTL_CACHE_VALUE_64`

- 行 71: `key = "test_key["`
  → `key = os.getenv("TEST_TTL_CACHE_KEY_71")`
  → 环境变量: `TEST_TTL_CACHE_KEY_71`

- 行 72: `value = "]test_value["`
  → `value = os.getenv("TEST_TTL_CACHE_VALUE_72")`
  → 环境变量: `TEST_TTL_CACHE_VALUE_72`

- 行 80: `key = "nonexistent_key["`
  → `key = os.getenv("TEST_TTL_CACHE_KEY_80")`
  → 环境变量: `TEST_TTL_CACHE_KEY_80`

- 行 87: `key = "test_key["`
  → `key = os.getenv("TEST_TTL_CACHE_KEY_87")`
  → 环境变量: `TEST_TTL_CACHE_KEY_87`

- 行 87: `value = "]test_value["`
  → `value = os.getenv("TEST_TTL_CACHE_VALUE_87")`
  → 环境变量: `TEST_TTL_CACHE_VALUE_87`

- 行 94: `key = "test_key["`
  → `key = os.getenv("TEST_TTL_CACHE_KEY_94")`
  → 环境变量: `TEST_TTL_CACHE_KEY_94`

- 行 94: `value = "]test_value["`
  → `value = os.getenv("TEST_TTL_CACHE_VALUE_94")`
  → 环境变量: `TEST_TTL_CACHE_VALUE_94`

- 行 105: `key = "test_key["`
  → `key = os.getenv("TEST_TTL_CACHE_KEY_105")`
  → 环境变量: `TEST_TTL_CACHE_KEY_105`

- 行 106: `value = "]test_value["`
  → `value = os.getenv("TEST_TTL_CACHE_VALUE_106")`
  → 环境变量: `TEST_TTL_CACHE_VALUE_106`

- 行 115: `key = "nonexistent_key["`
  → `key = os.getenv("TEST_TTL_CACHE_KEY_115")`
  → 环境变量: `TEST_TTL_CACHE_KEY_115`

### tests/legacy/unit/core/test_additional_coverage.py

- 行 65: `bookmaker="test_bookmaker["`
  → `bookmaker = os.getenv("TEST_ADDITIONAL_COVERAGE_BOOKMAKER_65")`
  → 环境变量: `TEST_ADDITIONAL_COVERAGE_BOOKMAKER_65`

- 行 73: `model_name="test_model["`
  → `model_name = os.getenv("TEST_ADDITIONAL_COVERAGE_MODEL_NAME_73")`
  → 环境变量: `TEST_ADDITIONAL_COVERAGE_MODEL_NAME_73`

- 行 115: `bookmaker="test_bookmaker["`
  → `bookmaker = os.getenv("TEST_ADDITIONAL_COVERAGE_BOOKMAKER_115")`
  → 环境变量: `TEST_ADDITIONAL_COVERAGE_BOOKMAKER_115`

- 行 126: `model_name="test_model["`
  → `model_name = os.getenv("TEST_ADDITIONAL_COVERAGE_MODEL_NAME_126")`
  → 环境变量: `TEST_ADDITIONAL_COVERAGE_MODEL_NAME_126`

- 行 138: `team_code="]TEST["`
  → `team_code = os.getenv("TEST_ADDITIONAL_COVERAGE_TEAM_CODE_138")`
  → 环境变量: `TEST_ADDITIONAL_COVERAGE_TEAM_CODE_138`

- 行 172: `season="]2024["`
  → `season = os.getenv("TEST_ADDITIONAL_COVERAGE_SEASON_172")`
  → 环境变量: `TEST_ADDITIONAL_COVERAGE_SEASON_172`

- 行 178: `bookmaker="]test_bookmaker["`
  → `bookmaker = os.getenv("TEST_ADDITIONAL_COVERAGE_BOOKMAKER_178")`
  → 环境变量: `TEST_ADDITIONAL_COVERAGE_BOOKMAKER_178`

- 行 181: `model_name="]test["`
  → `model_name = os.getenv("TEST_ADDITIONAL_COVERAGE_MODEL_NAME_181")`
  → 环境变量: `TEST_ADDITIONAL_COVERAGE_MODEL_NAME_181`

### tests/legacy/unit/core/test_core_config.py

- 行 24: `encoding = "]utf-8["`
  → `encoding = os.getenv("TEST_CORE_CONFIG_ENCODING_24")`
  → 环境变量: `TEST_CORE_CONFIG_ENCODING_24`

- 行 28: `encoding = "]utf-8["`
  → `encoding = os.getenv("TEST_CORE_CONFIG_ENCODING_28")`
  → 环境变量: `TEST_CORE_CONFIG_ENCODING_28`

- 行 46: `encoding = "]utf-8["`
  → `encoding = os.getenv("TEST_CORE_CONFIG_ENCODING_46")`
  → 环境变量: `TEST_CORE_CONFIG_ENCODING_46`

### tests/legacy/unit/core/test_external_mocks.py

- 行 61: `key="]test_key["`
  → `key = os.getenv("TEST_EXTERNAL_MOCKS_KEY_61")`
  → 环境变量: `TEST_EXTERNAL_MOCKS_KEY_61`

- 行 102: `endpoint="]_api["`
  → `endpoint = os.getenv("TEST_EXTERNAL_MOCKS_ENDPOINT_102")`
  → 环境变量: `TEST_EXTERNAL_MOCKS_ENDPOINT_102`

- 行 102: `method="]post["`
  → `method = os.getenv("TEST_EXTERNAL_MOCKS_METHOD_102")`
  → 环境变量: `TEST_EXTERNAL_MOCKS_METHOD_102`

- 行 102: `endpoint="]/api["`
  → `endpoint = os.getenv("TEST_EXTERNAL_MOCKS_ENDPOINT_102")`
  → 环境变量: `TEST_EXTERNAL_MOCKS_ENDPOINT_102`

### tests/legacy/unit/core/test_core.py

- 行 42: `read_data="]invalid json["`
  → `read_data = os.getenv("TEST_CORE_READ_DATA_42")`
  → 环境变量: `TEST_CORE_READ_DATA_42`

- 行 148: `encoding = "]utf-8["`
  → `encoding = os.getenv("TEST_CORE_ENCODING_148")`
  → 环境变量: `TEST_CORE_ENCODING_148`

### tests/legacy/unit/core/test_core_logger.py

- 行 20: `logger_name = "test_no_duplicate["`
  → `logger_name = os.getenv("TEST_CORE_LOGGER_LOGGER_NAME_20")`
  → 环境变量: `TEST_CORE_LOGGER_LOGGER_NAME_20`

- 行 28: `expected_format = "]]%(asctime)s - %(name)s - %(levelname)s - %(message)s["`
  → `expected_format = os.getenv("TEST_CORE_LOGGER_EXPECTED_FORMAT_28")`
  → 环境变量: `TEST_CORE_LOGGER_EXPECTED_FORMAT_28`

### tests/legacy/unit/services/test_user_profile_service.py

- 行 29: `user_id="user-1"`
  → `user_id = os.getenv("TEST_USER_PROFILE_SERVICE_USER_ID_29")`
  → 环境变量: `TEST_USER_PROFILE_SERVICE_USER_ID_29`

- 行 29: `display_name="Analyst"`
  → `display_name = os.getenv("TEST_USER_PROFILE_SERVICE_DISPLAY_NAME_29")`
  → 环境变量: `TEST_USER_PROFILE_SERVICE_DISPLAY_NAME_29`

- 行 29: `email="analyst@example.com"`
  → `email = os.getenv("TEST_USER_PROFILE_SERVICE_EMAIL_29")`
  → 环境变量: `TEST_USER_PROFILE_SERVICE_EMAIL_29`

- 行 32: `id="user-1"`
  → `id = os.getenv("TEST_USER_PROFILE_SERVICE_ID_32")`
  → 环境变量: `TEST_USER_PROFILE_SERVICE_ID_32`

- 行 32: `username="analyst"`
  → `username = os.getenv("TEST_USER_PROFILE_SERVICE_USERNAME_32")`
  → 环境变量: `TEST_USER_PROFILE_SERVICE_USERNAME_32`

### tests/legacy/unit/services/test_content_analysis_service.py

- 行 83: `text = "football analytics delivers repeatable value"`
  → `text = os.getenv("TEST_CONTENT_ANALYSIS_SERVICE_TEXT_83")`
  → 环境变量: `TEST_CONTENT_ANALYSIS_SERVICE_TEXT_83`

### tests/legacy/unit/features/test_feature_calculator_phase53.py

- 行 302: `cache_key = 'team_a_features_20240120'`
  → `cache_key = os.getenv("TEST_FEATURE_CALCULATOR_PHASE53_CACHE_KEY_302")`
  → 环境变量: `TEST_FEATURE_CALCULATOR_PHASE53_CACHE_KEY_302`

### tests/legacy/unit/features/test_entities.py

- 行 41: `season="2024-25["`
  → `season = os.getenv("TEST_ENTITIES_SEASON_41")`
  → 环境变量: `TEST_ENTITIES_SEASON_41`

- 行 53: `season="2024-25["`
  → `season = os.getenv("TEST_ENTITIES_SEASON_53")`
  → 环境变量: `TEST_ENTITIES_SEASON_53`

- 行 75: `season="2025-26["`
  → `season = os.getenv("TEST_ENTITIES_SEASON_75")`
  → 环境变量: `TEST_ENTITIES_SEASON_75`

- 行 104: `season="]]9999-99["`
  → `season = os.getenv("TEST_ENTITIES_SEASON_104")`
  → 环境变量: `TEST_ENTITIES_SEASON_104`

- 行 112: `season="2024-25["`
  → `season = os.getenv("TEST_ENTITIES_SEASON_112")`
  → 环境变量: `TEST_ENTITIES_SEASON_112`

- 行 120: `season="]2024-25["`
  → `season = os.getenv("TEST_ENTITIES_SEASON_120")`
  → 环境变量: `TEST_ENTITIES_SEASON_120`

- 行 134: `team_name="Test FC["`
  → `team_name = os.getenv("TEST_ENTITIES_TEAM_NAME_134")`
  → 环境变量: `TEST_ENTITIES_TEAM_NAME_134`

- 行 134: `home_venue="]Test Stadium["`
  → `home_venue = os.getenv("TEST_ENTITIES_HOME_VENUE_134")`
  → 环境变量: `TEST_ENTITIES_HOME_VENUE_134`

- 行 140: `team_name="Test FC["`
  → `team_name = os.getenv("TEST_ENTITIES_TEAM_NAME_140")`
  → 环境变量: `TEST_ENTITIES_TEAM_NAME_140`

- 行 149: `team_name="Test FC["`
  → `team_name = os.getenv("TEST_ENTITIES_TEAM_NAME_149")`
  → 环境变量: `TEST_ENTITIES_TEAM_NAME_149`

- 行 150: `home_venue="]Test Stadium["`
  → `home_venue = os.getenv("TEST_ENTITIES_HOME_VENUE_150")`
  → 环境变量: `TEST_ENTITIES_HOME_VENUE_150`

- 行 158: `team_name="Test FC["`
  → `team_name = os.getenv("TEST_ENTITIES_TEAM_NAME_158")`
  → 环境变量: `TEST_ENTITIES_TEAM_NAME_158`

- 行 176: `team_name="Test Team FC["`
  → `team_name = os.getenv("TEST_ENTITIES_TEAM_NAME_176")`
  → 环境变量: `TEST_ENTITIES_TEAM_NAME_176`

- 行 176: `home_venue="]Test Arena["`
  → `home_venue = os.getenv("TEST_ENTITIES_HOME_VENUE_176")`
  → 环境变量: `TEST_ENTITIES_HOME_VENUE_176`

- 行 186: `team_name="测试球队 FC 中文 español 日本語["`
  → `team_name = os.getenv("TEST_ENTITIES_TEAM_NAME_186")`
  → 环境变量: `TEST_ENTITIES_TEAM_NAME_186`

- 行 188: `home_venue="]测试体育场 🏟️"`
  → `home_venue = os.getenv("TEST_ENTITIES_HOME_VENUE_188")`
  → 环境变量: `TEST_ENTITIES_HOME_VENUE_188`

- 行 192: `team_name='Special "`
  → `team_name = os.getenv("TEST_ENTITIES_TEAM_NAME_192")`
  → 环境变量: `TEST_ENTITIES_TEAM_NAME_192`

- 行 194: `home_venue='Stadium "`
  → `home_venue = os.getenv("TEST_ENTITIES_HOME_VENUE_194")`
  → 环境变量: `TEST_ENTITIES_HOME_VENUE_194`

- 行 201: `entity_type="match["`
  → `entity_type = os.getenv("TEST_ENTITIES_ENTITY_TYPE_201")`
  → 环境变量: `TEST_ENTITIES_ENTITY_TYPE_201`

- 行 277: `season="2024-25["`
  → `season = os.getenv("TEST_ENTITIES_SEASON_277")`
  → 环境变量: `TEST_ENTITIES_SEASON_277`

- 行 280: `team_name="]Home FC["`
  → `team_name = os.getenv("TEST_ENTITIES_TEAM_NAME_280")`
  → 环境变量: `TEST_ENTITIES_TEAM_NAME_280`

- 行 280: `home_venue="]Home Stadium["`
  → `home_venue = os.getenv("TEST_ENTITIES_HOME_VENUE_280")`
  → 环境变量: `TEST_ENTITIES_HOME_VENUE_280`

- 行 280: `team_name="]Away FC["`
  → `team_name = os.getenv("TEST_ENTITIES_TEAM_NAME_280")`
  → 环境变量: `TEST_ENTITIES_TEAM_NAME_280`

- 行 282: `home_venue="]Away Stadium["`
  → `home_venue = os.getenv("TEST_ENTITIES_HOME_VENUE_282")`
  → 环境变量: `TEST_ENTITIES_HOME_VENUE_282`

- 行 301: `season="2024-25["`
  → `season = os.getenv("TEST_ENTITIES_SEASON_301")`
  → 环境变量: `TEST_ENTITIES_SEASON_301`

- 行 303: `team_name="]Test FC["`
  → `team_name = os.getenv("TEST_ENTITIES_TEAM_NAME_303")`
  → 环境变量: `TEST_ENTITIES_TEAM_NAME_303`

### tests/legacy/unit/features/test_feature_calculator.py

- 行 50: `table_name = 'matches'`
  → `table_name = os.getenv("TEST_FEATURE_CALCULATOR_TABLE_NAME_50")`
  → 环境变量: `TEST_FEATURE_CALCULATOR_TABLE_NAME_50`

- 行 64: `reason="Database connection not available["`
  → `reason = os.getenv("TEST_FEATURE_CALCULATOR_REASON_64")`
  → 环境变量: `TEST_FEATURE_CALCULATOR_REASON_64`

- 行 79: `season="2024-25["`
  → `season = os.getenv("TEST_FEATURE_CALCULATOR_SEASON_79")`
  → 环境变量: `TEST_FEATURE_CALCULATOR_SEASON_79`

- 行 82: `home_venue="]测试球场["`
  → `home_venue = os.getenv("TEST_FEATURE_CALCULATOR_HOME_VENUE_82")`
  → 环境变量: `TEST_FEATURE_CALCULATOR_HOME_VENUE_82`

- 行 202: `bookmaker="Bet365["`
  → `bookmaker = os.getenv("TEST_FEATURE_CALCULATOR_BOOKMAKER_202")`
  → 环境变量: `TEST_FEATURE_CALCULATOR_BOOKMAKER_202`

- 行 206: `bookmaker="]William Hill["`
  → `bookmaker = os.getenv("TEST_FEATURE_CALCULATOR_BOOKMAKER_206")`
  → 环境变量: `TEST_FEATURE_CALCULATOR_BOOKMAKER_206`

- 行 207: `bookmaker="]Pinnacle["`
  → `bookmaker = os.getenv("TEST_FEATURE_CALCULATOR_BOOKMAKER_207")`
  → 环境变量: `TEST_FEATURE_CALCULATOR_BOOKMAKER_207`

- 行 253: `bookmaker="Bet365["`
  → `bookmaker = os.getenv("TEST_FEATURE_CALCULATOR_BOOKMAKER_253")`
  → 环境变量: `TEST_FEATURE_CALCULATOR_BOOKMAKER_253`

### tests/legacy/unit/features/test_feature_entities.py

- 行 14: `season="2024_25["`
  → `season = os.getenv("TEST_FEATURE_ENTITIES_SEASON_14")`
  → 环境变量: `TEST_FEATURE_ENTITIES_SEASON_14`

- 行 16: `team_name="]Arsenal["`
  → `team_name = os.getenv("TEST_FEATURE_ENTITIES_TEAM_NAME_16")`
  → 环境变量: `TEST_FEATURE_ENTITIES_TEAM_NAME_16`

- 行 17: `home_venue="]Emirates["`
  → `home_venue = os.getenv("TEST_FEATURE_ENTITIES_HOME_VENUE_17")`
  → 环境变量: `TEST_FEATURE_ENTITIES_HOME_VENUE_17`

### tests/legacy/unit/tasks/test_monitoring_task_monitor.py

- 行 16: `task_name="]collect_odds_task["`
  → `task_name = os.getenv("TEST_MONITORING_TASK_MONITOR_TASK_NAME_16")`
  → 环境变量: `TEST_MONITORING_TASK_MONITOR_TASK_NAME_16`

- 行 18: `task_name="]]collect_scores_task["`
  → `task_name = os.getenv("TEST_MONITORING_TASK_MONITOR_TASK_NAME_18")`
  → 环境变量: `TEST_MONITORING_TASK_MONITOR_TASK_NAME_18`

- 行 28: `return_value = "]postgresql["`
  → `return_value = os.getenv("TEST_MONITORING_TASK_MONITOR_RETURN_VALUE_28")`
  → 环境变量: `TEST_MONITORING_TASK_MONITOR_RETURN_VALUE_28`

- 行 82: `task_name="]collect_odds_task["`
  → `task_name = os.getenv("TEST_MONITORING_TASK_MONITOR_TASK_NAME_82")`
  → 环境变量: `TEST_MONITORING_TASK_MONITOR_TASK_NAME_82`

- 行 84: `task_name="]collect_scores_task["`
  → `task_name = os.getenv("TEST_MONITORING_TASK_MONITOR_TASK_NAME_84")`
  → 环境变量: `TEST_MONITORING_TASK_MONITOR_TASK_NAME_84`

- 行 89: `return_value = "]SELECT 1["`
  → `return_value = os.getenv("TEST_MONITORING_TASK_MONITOR_RETURN_VALUE_89")`
  → 环境变量: `TEST_MONITORING_TASK_MONITOR_RETURN_VALUE_89`

- 行 107: `return_value="]sqlite["`
  → `return_value = os.getenv("TEST_MONITORING_TASK_MONITOR_RETURN_VALUE_107")`
  → 环境变量: `TEST_MONITORING_TASK_MONITOR_RETURN_VALUE_107`

- 行 125: `return_value="]postgresql["`
  → `return_value = os.getenv("TEST_MONITORING_TASK_MONITOR_RETURN_VALUE_125")`
  → 环境变量: `TEST_MONITORING_TASK_MONITOR_RETURN_VALUE_125`

- 行 135: `status="]success["`
  → `status = os.getenv("TEST_MONITORING_TASK_MONITOR_STATUS_135")`
  → 环境变量: `TEST_MONITORING_TASK_MONITOR_STATUS_135`

### tests/legacy/unit/tasks/test_streaming_tasks.py

- 行 56: `id="]]task-123["`
  → `id = os.getenv("TEST_STREAMING_TASKS_ID_56")`
  → 环境变量: `TEST_STREAMING_TASKS_ID_56`

- 行 81: `consumer_group_id="]group-1["`
  → `consumer_group_id = os.getenv("TEST_STREAMING_TASKS_CONSUMER_GROUP_ID_81")`
  → 环境变量: `TEST_STREAMING_TASKS_CONSUMER_GROUP_ID_81`

- 行 129: `action="]list["`
  → `action = os.getenv("TEST_STREAMING_TASKS_ACTION_129")`
  → 环境变量: `TEST_STREAMING_TASKS_ACTION_129`

- 行 132: `action="]create["`
  → `action = os.getenv("TEST_STREAMING_TASKS_ACTION_132")`
  → 环境变量: `TEST_STREAMING_TASKS_ACTION_132`

- 行 132: `topic_name="]matches["`
  → `topic_name = os.getenv("TEST_STREAMING_TASKS_TOPIC_NAME_132")`
  → 环境变量: `TEST_STREAMING_TASKS_TOPIC_NAME_132`

- 行 137: `action="]create["`
  → `action = os.getenv("TEST_STREAMING_TASKS_ACTION_137")`
  → 环境变量: `TEST_STREAMING_TASKS_ACTION_137`

- 行 137: `topic_name="]invalid["`
  → `topic_name = os.getenv("TEST_STREAMING_TASKS_TOPIC_NAME_137")`
  → 环境变量: `TEST_STREAMING_TASKS_TOPIC_NAME_137`

- 行 141: `action="]]list["`
  → `action = os.getenv("TEST_STREAMING_TASKS_ACTION_141")`
  → 环境变量: `TEST_STREAMING_TASKS_ACTION_141`

- 行 143: `action="]delete["`
  → `action = os.getenv("TEST_STREAMING_TASKS_ACTION_143")`
  → 环境变量: `TEST_STREAMING_TASKS_ACTION_143`

### tests/legacy/unit/tasks/test_utils.py

- 行 65: `name = "]Premier League["`
  → `name = os.getenv("TEST_UTILS_NAME_65")`
  → 环境变量: `TEST_UTILS_NAME_65`

### tests/legacy/unit/tasks/test_data_collection_tasks.py

- 行 36: `name = "]test.data_collection_task["`
  → `name = os.getenv("TEST_DATA_COLLECTION_TASKS_NAME_36")`
  → 环境变量: `TEST_DATA_COLLECTION_TASKS_NAME_36`

- 行 44: `task_id = "]test-task-id["`
  → `task_id = os.getenv("TEST_DATA_COLLECTION_TASKS_TASK_ID_44")`
  → 环境变量: `TEST_DATA_COLLECTION_TASKS_TASK_ID_44`

- 行 44: `return_value="]Error info["`
  → `return_value = os.getenv("TEST_DATA_COLLECTION_TASKS_RETURN_VALUE_44")`
  → 环境变量: `TEST_DATA_COLLECTION_TASKS_RETURN_VALUE_44`

- 行 53: `task_id = "]test-task-id["`
  → `task_id = os.getenv("TEST_DATA_COLLECTION_TASKS_TASK_ID_53")`
  → 环境变量: `TEST_DATA_COLLECTION_TASKS_TASK_ID_53`

- 行 62: `task_id = "]test-task-id["`
  → `task_id = os.getenv("TEST_DATA_COLLECTION_TASKS_TASK_ID_62")`
  → 环境变量: `TEST_DATA_COLLECTION_TASKS_TASK_ID_62`

- 行 67: `task_id = "]test-task-id["`
  → `task_id = os.getenv("TEST_DATA_COLLECTION_TASKS_TASK_ID_67")`
  → 环境变量: `TEST_DATA_COLLECTION_TASKS_TASK_ID_67`

- 行 71: `task_id = "]test-task-id["`
  → `task_id = os.getenv("TEST_DATA_COLLECTION_TASKS_TASK_ID_71")`
  → 环境变量: `TEST_DATA_COLLECTION_TASKS_TASK_ID_71`

- 行 156: `match = "]赛程采集失败["`
  → `match = os.getenv("TEST_DATA_COLLECTION_TASKS_MATCH_156")`
  → 环境变量: `TEST_DATA_COLLECTION_TASKS_MATCH_156`

- 行 168: `match = "]API connection failed["`
  → `match = os.getenv("TEST_DATA_COLLECTION_TASKS_MATCH_168")`
  → 环境变量: `TEST_DATA_COLLECTION_TASKS_MATCH_168`

- 行 219: `match = "]Permanent error["`
  → `match = os.getenv("TEST_DATA_COLLECTION_TASKS_MATCH_219")`
  → 环境变量: `TEST_DATA_COLLECTION_TASKS_MATCH_219`

- 行 231: `status = "success["`
  → `status = os.getenv("TEST_DATA_COLLECTION_TASKS_STATUS_231")`
  → 环境变量: `TEST_DATA_COLLECTION_TASKS_STATUS_231`

- 行 314: `bookmaker="]bet365["`
  → `bookmaker = os.getenv("TEST_DATA_COLLECTION_TASKS_BOOKMAKER_314")`
  → 环境变量: `TEST_DATA_COLLECTION_TASKS_BOOKMAKER_314`

### tests/legacy/unit/tasks/test_data_collection_tasks_basic.py

- 行 38: `match = "]retry invoked["`
  → `match = os.getenv("TEST_DATA_COLLECTION_TASKS_BASIC_MATCH_38")`
  → 环境变量: `TEST_DATA_COLLECTION_TASKS_BASIC_MATCH_38`

- 行 47: `match = "]final fail["`
  → `match = os.getenv("TEST_DATA_COLLECTION_TASKS_BASIC_MATCH_47")`
  → 环境变量: `TEST_DATA_COLLECTION_TASKS_BASIC_MATCH_47`

### tests/legacy/unit/tasks/test_maintenance_tasks_basic.py

- 行 72: `table_name = "]matches["`
  → `table_name = os.getenv("TEST_MAINTENANCE_TASKS_BASIC_TABLE_NAME_72")`
  → 环境变量: `TEST_MAINTENANCE_TASKS_BASIC_TABLE_NAME_72`

- 行 72: `size = "]10 MB["`
  → `size = os.getenv("TEST_MAINTENANCE_TASKS_BASIC_SIZE_72")`
  → 环境变量: `TEST_MAINTENANCE_TASKS_BASIC_SIZE_72`

### tests/legacy/unit/tasks/test_error_logger.py

- 行 69: `task_name = "test_task["`
  → `task_name = os.getenv("TEST_ERROR_LOGGER_TASK_NAME_69")`
  → 环境变量: `TEST_ERROR_LOGGER_TASK_NAME_69`

- 行 69: `task_id = "]task-123["`
  → `task_id = os.getenv("TEST_ERROR_LOGGER_TASK_ID_69")`
  → 环境变量: `TEST_ERROR_LOGGER_TASK_ID_69`

- 行 81: `task_name = "test_task["`
  → `task_name = os.getenv("TEST_ERROR_LOGGER_TASK_NAME_81")`
  → 环境变量: `TEST_ERROR_LOGGER_TASK_NAME_81`

- 行 82: `task_id = "]task-123["`
  → `task_id = os.getenv("TEST_ERROR_LOGGER_TASK_ID_82")`
  → 环境变量: `TEST_ERROR_LOGGER_TASK_ID_82`

- 行 90: `task_name = "test_task["`
  → `task_name = os.getenv("TEST_ERROR_LOGGER_TASK_NAME_90")`
  → 环境变量: `TEST_ERROR_LOGGER_TASK_NAME_90`

- 行 91: `task_id = "]task-123["`
  → `task_id = os.getenv("TEST_ERROR_LOGGER_TASK_ID_91")`
  → 环境变量: `TEST_ERROR_LOGGER_TASK_ID_91`

- 行 99: `task_name = "]test_task["`
  → `task_name = os.getenv("TEST_ERROR_LOGGER_TASK_NAME_99")`
  → 环境变量: `TEST_ERROR_LOGGER_TASK_NAME_99`

- 行 99: `task_id = "]task-123["`
  → `task_id = os.getenv("TEST_ERROR_LOGGER_TASK_ID_99")`
  → 环境变量: `TEST_ERROR_LOGGER_TASK_ID_99`

- 行 110: `task_name = "]test_task["`
  → `task_name = os.getenv("TEST_ERROR_LOGGER_TASK_NAME_110")`
  → 环境变量: `TEST_ERROR_LOGGER_TASK_NAME_110`

- 行 111: `task_id = "]task-123["`
  → `task_id = os.getenv("TEST_ERROR_LOGGER_TASK_ID_111")`
  → 环境变量: `TEST_ERROR_LOGGER_TASK_ID_111`

- 行 131: `task_name = "test_task["`
  → `task_name = os.getenv("TEST_ERROR_LOGGER_TASK_NAME_131")`
  → 环境变量: `TEST_ERROR_LOGGER_TASK_NAME_131`

- 行 131: `api_endpoint = "]/api/fixtures["`
  → `api_endpoint = os.getenv("TEST_ERROR_LOGGER_API_ENDPOINT_131")`
  → 环境变量: `TEST_ERROR_LOGGER_API_ENDPOINT_131`

- 行 133: `error_message = "]]Not Found["`
  → `error_message = os.getenv("TEST_ERROR_LOGGER_ERROR_MESSAGE_133")`
  → 环境变量: `TEST_ERROR_LOGGER_ERROR_MESSAGE_133`

- 行 149: `task_name="test_task["`
  → `task_name = os.getenv("TEST_ERROR_LOGGER_TASK_NAME_149")`
  → 环境变量: `TEST_ERROR_LOGGER_TASK_NAME_149`

- 行 149: `api_endpoint="]/api/test["`
  → `api_endpoint = os.getenv("TEST_ERROR_LOGGER_API_ENDPOINT_149")`
  → 环境变量: `TEST_ERROR_LOGGER_API_ENDPOINT_149`

- 行 149: `error_message="]Test error["`
  → `error_message = os.getenv("TEST_ERROR_LOGGER_ERROR_MESSAGE_149")`
  → 环境变量: `TEST_ERROR_LOGGER_ERROR_MESSAGE_149`

- 行 155: `task_name="]test_task["`
  → `task_name = os.getenv("TEST_ERROR_LOGGER_TASK_NAME_155")`
  → 环境变量: `TEST_ERROR_LOGGER_TASK_NAME_155`

- 行 156: `api_endpoint="]/api/test["`
  → `api_endpoint = os.getenv("TEST_ERROR_LOGGER_API_ENDPOINT_156")`
  → 环境变量: `TEST_ERROR_LOGGER_API_ENDPOINT_156`

- 行 156: `error_message="]Server Error["`
  → `error_message = os.getenv("TEST_ERROR_LOGGER_ERROR_MESSAGE_156")`
  → 环境变量: `TEST_ERROR_LOGGER_ERROR_MESSAGE_156`

- 行 190: `value = "]failed["`
  → `value = os.getenv("TEST_ERROR_LOGGER_VALUE_190")`
  → 环境变量: `TEST_ERROR_LOGGER_VALUE_190`

- 行 191: `data_source="]api.test.com["`
  → `data_source = os.getenv("TEST_ERROR_LOGGER_DATA_SOURCE_191")`
  → 环境变量: `TEST_ERROR_LOGGER_DATA_SOURCE_191`

- 行 192: `collection_type="]fixtures["`
  → `collection_type = os.getenv("TEST_ERROR_LOGGER_COLLECTION_TYPE_192")`
  → 环境变量: `TEST_ERROR_LOGGER_COLLECTION_TYPE_192`

- 行 193: `error_message="]API timeout["`
  → `error_message = os.getenv("TEST_ERROR_LOGGER_ERROR_MESSAGE_193")`
  → 环境变量: `TEST_ERROR_LOGGER_ERROR_MESSAGE_193`

- 行 209: `value = "]failed["`
  → `value = os.getenv("TEST_ERROR_LOGGER_VALUE_209")`
  → 环境变量: `TEST_ERROR_LOGGER_VALUE_209`

- 行 211: `data_source="]api.test.com["`
  → `data_source = os.getenv("TEST_ERROR_LOGGER_DATA_SOURCE_211")`
  → 环境变量: `TEST_ERROR_LOGGER_DATA_SOURCE_211`

- 行 211: `collection_type="]fixtures["`
  → `collection_type = os.getenv("TEST_ERROR_LOGGER_COLLECTION_TYPE_211")`
  → 环境变量: `TEST_ERROR_LOGGER_COLLECTION_TYPE_211`

- 行 212: `error_message="]Test error["`
  → `error_message = os.getenv("TEST_ERROR_LOGGER_ERROR_MESSAGE_212")`
  → 环境变量: `TEST_ERROR_LOGGER_ERROR_MESSAGE_212`

- 行 225: `data_source="]api.test.com["`
  → `data_source = os.getenv("TEST_ERROR_LOGGER_DATA_SOURCE_225")`
  → 环境变量: `TEST_ERROR_LOGGER_DATA_SOURCE_225`

- 行 225: `collection_type="]fixtures["`
  → `collection_type = os.getenv("TEST_ERROR_LOGGER_COLLECTION_TYPE_225")`
  → 环境变量: `TEST_ERROR_LOGGER_COLLECTION_TYPE_225`

- 行 225: `error_message="]Test error["`
  → `error_message = os.getenv("TEST_ERROR_LOGGER_ERROR_MESSAGE_225")`
  → 环境变量: `TEST_ERROR_LOGGER_ERROR_MESSAGE_225`

- 行 231: `data_source="]api.test.com["`
  → `data_source = os.getenv("TEST_ERROR_LOGGER_DATA_SOURCE_231")`
  → 环境变量: `TEST_ERROR_LOGGER_DATA_SOURCE_231`

- 行 232: `collection_type="]fixtures["`
  → `collection_type = os.getenv("TEST_ERROR_LOGGER_COLLECTION_TYPE_232")`
  → 环境变量: `TEST_ERROR_LOGGER_COLLECTION_TYPE_232`

- 行 233: `error_message="]Test error["`
  → `error_message = os.getenv("TEST_ERROR_LOGGER_ERROR_MESSAGE_233")`
  → 环境变量: `TEST_ERROR_LOGGER_ERROR_MESSAGE_233`

- 行 308: `task_name="]integration_test["`
  → `task_name = os.getenv("TEST_ERROR_LOGGER_TASK_NAME_308")`
  → 环境变量: `TEST_ERROR_LOGGER_TASK_NAME_308`

- 行 309: `task_id="]integration-123["`
  → `task_id = os.getenv("TEST_ERROR_LOGGER_TASK_ID_309")`
  → 环境变量: `TEST_ERROR_LOGGER_TASK_ID_309`

### tests/legacy/unit/tasks/test_task_scheduler.py

- 行 164: `main = "football_prediction_tasks["`
  → `main = os.getenv("TEST_TASK_SCHEDULER_MAIN_164")`
  → 环境变量: `TEST_TASK_SCHEDULER_MAIN_164`

- 行 164: `broker_url = "]redis://localhost6379/0["`
  → `broker_url = os.getenv("TEST_TASK_SCHEDULER_BROKER_URL_164")`
  → 环境变量: `TEST_TASK_SCHEDULER_BROKER_URL_164`

- 行 164: `result_backend = "]redis://localhost6379/0["`
  → `result_backend = os.getenv("TEST_TASK_SCHEDULER_RESULT_BACKEND_164")`
  → 环境变量: `TEST_TASK_SCHEDULER_RESULT_BACKEND_164`

- 行 276: `task_serializer = "]json["`
  → `task_serializer = os.getenv("TEST_TASK_SCHEDULER_TASK_SERIALIZER_276")`
  → 环境变量: `TEST_TASK_SCHEDULER_TASK_SERIALIZER_276`

- 行 276: `result_serializer = "]json["`
  → `result_serializer = os.getenv("TEST_TASK_SCHEDULER_RESULT_SERIALIZER_276")`
  → 环境变量: `TEST_TASK_SCHEDULER_RESULT_SERIALIZER_276`

- 行 324: `status = "]success["`
  → `status = os.getenv("TEST_TASK_SCHEDULER_STATUS_324")`
  → 环境变量: `TEST_TASK_SCHEDULER_STATUS_324`

- 行 352: `status = "]success["`
  → `status = os.getenv("TEST_TASK_SCHEDULER_STATUS_352")`
  → 环境变量: `TEST_TASK_SCHEDULER_STATUS_352`

- 行 379: `status = "]success["`
  → `status = os.getenv("TEST_TASK_SCHEDULER_STATUS_379")`
  → 环境变量: `TEST_TASK_SCHEDULER_STATUS_379`

- 行 494: `task_name="]]collect_fixtures_task["`
  → `task_name = os.getenv("TEST_TASK_SCHEDULER_TASK_NAME_494")`
  → 环境变量: `TEST_TASK_SCHEDULER_TASK_NAME_494`

- 行 495: `task_id="]task-123["`
  → `task_id = os.getenv("TEST_TASK_SCHEDULER_TASK_ID_495")`
  → 环境变量: `TEST_TASK_SCHEDULER_TASK_ID_495`

- 行 507: `task_name="]]collect_odds_task["`
  → `task_name = os.getenv("TEST_TASK_SCHEDULER_TASK_NAME_507")`
  → 环境变量: `TEST_TASK_SCHEDULER_TASK_NAME_507`

- 行 507: `api_endpoint = "]https_/api-football.com/v3/odds["`
  → `api_endpoint = os.getenv("TEST_TASK_SCHEDULER_API_ENDPOINT_507")`
  → 环境变量: `TEST_TASK_SCHEDULER_API_ENDPOINT_507`

- 行 509: `error_message="]Service Unavailable["`
  → `error_message = os.getenv("TEST_TASK_SCHEDULER_ERROR_MESSAGE_509")`
  → 环境变量: `TEST_TASK_SCHEDULER_ERROR_MESSAGE_509`

- 行 533: `data_source="]]API-FOOTBALL["`
  → `data_source = os.getenv("TEST_TASK_SCHEDULER_DATA_SOURCE_533")`
  → 环境变量: `TEST_TASK_SCHEDULER_DATA_SOURCE_533`

- 行 534: `collection_type="]fixtures["`
  → `collection_type = os.getenv("TEST_TASK_SCHEDULER_COLLECTION_TYPE_534")`
  → 环境变量: `TEST_TASK_SCHEDULER_COLLECTION_TYPE_534`

- 行 535: `error_message="]解析JSON失败["`
  → `error_message = os.getenv("TEST_TASK_SCHEDULER_ERROR_MESSAGE_535")`
  → 环境变量: `TEST_TASK_SCHEDULER_ERROR_MESSAGE_535`

- 行 545: `task_name="collect_odds_task["`
  → `task_name = os.getenv("TEST_TASK_SCHEDULER_TASK_NAME_545")`
  → 环境变量: `TEST_TASK_SCHEDULER_TASK_NAME_545`

- 行 546: `task_name="]collect_scores_task["`
  → `task_name = os.getenv("TEST_TASK_SCHEDULER_TASK_NAME_546")`
  → 环境变量: `TEST_TASK_SCHEDULER_TASK_NAME_546`

- 行 549: `error_type="]API_FAILURE["`
  → `error_type = os.getenv("TEST_TASK_SCHEDULER_ERROR_TYPE_549")`
  → 环境变量: `TEST_TASK_SCHEDULER_ERROR_TYPE_549`

- 行 550: `error_type="]DATABASE_ERROR["`
  → `error_type = os.getenv("TEST_TASK_SCHEDULER_ERROR_TYPE_550")`
  → 环境变量: `TEST_TASK_SCHEDULER_ERROR_TYPE_550`

- 行 759: `task_name="]collect_odds_task["`
  → `task_name = os.getenv("TEST_TASK_SCHEDULER_TASK_NAME_759")`
  → 环境变量: `TEST_TASK_SCHEDULER_TASK_NAME_759`

- 行 761: `task_name="]]collect_scores_task["`
  → `task_name = os.getenv("TEST_TASK_SCHEDULER_TASK_NAME_761")`
  → 环境变量: `TEST_TASK_SCHEDULER_TASK_NAME_761`

- 行 869: `match_status = "scheduled["`
  → `match_status = os.getenv("TEST_TASK_SCHEDULER_MATCH_STATUS_869")`
  → 环境变量: `TEST_TASK_SCHEDULER_MATCH_STATUS_869`

- 行 875: `match_status = "]]]scheduled["`
  → `match_status = os.getenv("TEST_TASK_SCHEDULER_MATCH_STATUS_875")`
  → 环境变量: `TEST_TASK_SCHEDULER_MATCH_STATUS_875`

- 行 983: `task_name="]test_task["`
  → `task_name = os.getenv("TEST_TASK_SCHEDULER_TASK_NAME_983")`
  → 环境变量: `TEST_TASK_SCHEDULER_TASK_NAME_983`

- 行 984: `task_id="]test-123["`
  → `task_id = os.getenv("TEST_TASK_SCHEDULER_TASK_ID_984")`
  → 环境变量: `TEST_TASK_SCHEDULER_TASK_ID_984`

### tests/legacy/unit/data/test_data_collectors.py

- 行 82: `data_source="test_api["`
  → `data_source = os.getenv("TEST_DATA_COLLECTORS_DATA_SOURCE_82")`
  → 环境变量: `TEST_DATA_COLLECTORS_DATA_SOURCE_82`

- 行 82: `collection_type="]fixtures["`
  → `collection_type = os.getenv("TEST_DATA_COLLECTORS_COLLECTION_TYPE_82")`
  → 环境变量: `TEST_DATA_COLLECTORS_COLLECTION_TYPE_82`

- 行 82: `status="]partial["`
  → `status = os.getenv("TEST_DATA_COLLECTORS_STATUS_82")`
  → 环境变量: `TEST_DATA_COLLECTORS_STATUS_82`

- 行 82: `error_message="]Some errors occurred["`
  → `error_message = os.getenv("TEST_DATA_COLLECTORS_ERROR_MESSAGE_82")`
  → 环境变量: `TEST_DATA_COLLECTORS_ERROR_MESSAGE_82`

- 行 226: `data_source="]]scores_api["`
  → `data_source = os.getenv("TEST_DATA_COLLECTORS_DATA_SOURCE_226")`
  → 环境变量: `TEST_DATA_COLLECTORS_DATA_SOURCE_226`

- 行 227: `collection_type="]live_scores["`
  → `collection_type = os.getenv("TEST_DATA_COLLECTORS_COLLECTION_TYPE_227")`
  → 环境变量: `TEST_DATA_COLLECTORS_COLLECTION_TYPE_227`

- 行 231: `status="]success["`
  → `status = os.getenv("TEST_DATA_COLLECTORS_STATUS_231")`
  → 环境变量: `TEST_DATA_COLLECTORS_STATUS_231`

### tests/legacy/unit/data/test_data_quality_core.py

- 行 108: `table_name="test_table["`
  → `table_name = os.getenv("TEST_DATA_QUALITY_CORE_TABLE_NAME_108")`
  → 环境变量: `TEST_DATA_QUALITY_CORE_TABLE_NAME_108`

- 行 108: `error_type="]test_error["`
  → `error_type = os.getenv("TEST_DATA_QUALITY_CORE_ERROR_TYPE_108")`
  → 环境变量: `TEST_DATA_QUALITY_CORE_ERROR_TYPE_108`

- 行 108: `severity="]high["`
  → `severity = os.getenv("TEST_DATA_QUALITY_CORE_SEVERITY_108")`
  → 环境变量: `TEST_DATA_QUALITY_CORE_SEVERITY_108`

- 行 110: `error_type="]test["`
  → `error_type = os.getenv("TEST_DATA_QUALITY_CORE_ERROR_TYPE_110")`
  → 环境变量: `TEST_DATA_QUALITY_CORE_ERROR_TYPE_110`

- 行 117: `table_name="]]test2["`
  → `table_name = os.getenv("TEST_DATA_QUALITY_CORE_TABLE_NAME_117")`
  → 环境变量: `TEST_DATA_QUALITY_CORE_TABLE_NAME_117`

- 行 117: `error_type="]test2["`
  → `error_type = os.getenv("TEST_DATA_QUALITY_CORE_ERROR_TYPE_117")`
  → 环境变量: `TEST_DATA_QUALITY_CORE_ERROR_TYPE_117`

- 行 138: `table_name="test_table["`
  → `table_name = os.getenv("TEST_DATA_QUALITY_CORE_TABLE_NAME_138")`
  → 环境变量: `TEST_DATA_QUALITY_CORE_TABLE_NAME_138`

- 行 138: `error_type="]test_error["`
  → `error_type = os.getenv("TEST_DATA_QUALITY_CORE_ERROR_TYPE_138")`
  → 环境变量: `TEST_DATA_QUALITY_CORE_ERROR_TYPE_138`

- 行 138: `severity="]medium["`
  → `severity = os.getenv("TEST_DATA_QUALITY_CORE_SEVERITY_138")`
  → 环境变量: `TEST_DATA_QUALITY_CORE_SEVERITY_138`

- 行 138: `error_message="]测试错误消息["`
  → `error_message = os.getenv("TEST_DATA_QUALITY_CORE_ERROR_MESSAGE_138")`
  → 环境变量: `TEST_DATA_QUALITY_CORE_ERROR_MESSAGE_138`

- 行 220: `expected_status = "]PASSED["`
  → `expected_status = os.getenv("TEST_DATA_QUALITY_CORE_EXPECTED_STATUS_220")`
  → 环境变量: `TEST_DATA_QUALITY_CORE_EXPECTED_STATUS_220`

### tests/legacy/unit/data/test_streaming_collector.py

- 行 36: `kafka_bootstrap_servers = "localhost9092["`
  → `kafka_bootstrap_servers = os.getenv("TEST_STREAMING_COLLECTOR_KAFKA_BOOTSTRAP_SERVERS_3")`
  → 环境变量: `TEST_STREAMING_COLLECTOR_KAFKA_BOOTSTRAP_SERVERS_3`

- 行 36: `topic_prefix = "]football["`
  → `topic_prefix = os.getenv("TEST_STREAMING_COLLECTOR_TOPIC_PREFIX_36")`
  → 环境变量: `TEST_STREAMING_COLLECTOR_TOPIC_PREFIX_36`

- 行 71: `data_source="]custom_source["`
  → `data_source = os.getenv("TEST_STREAMING_COLLECTOR_DATA_SOURCE_71")`
  → 环境变量: `TEST_STREAMING_COLLECTOR_DATA_SOURCE_71`

- 行 75: `data_source="test_source["`
  → `data_source = os.getenv("TEST_STREAMING_COLLECTOR_DATA_SOURCE_75")`
  → 环境变量: `TEST_STREAMING_COLLECTOR_DATA_SOURCE_75`

- 行 88: `data_source="]test_source["`
  → `data_source = os.getenv("TEST_STREAMING_COLLECTOR_DATA_SOURCE_88")`
  → 环境变量: `TEST_STREAMING_COLLECTOR_DATA_SOURCE_88`

- 行 102: `data_source="]test_source["`
  → `data_source = os.getenv("TEST_STREAMING_COLLECTOR_DATA_SOURCE_102")`
  → 环境变量: `TEST_STREAMING_COLLECTOR_DATA_SOURCE_102`

- 行 103: `collection_type="]fixtures["`
  → `collection_type = os.getenv("TEST_STREAMING_COLLECTOR_COLLECTION_TYPE_103")`
  → 环境变量: `TEST_STREAMING_COLLECTOR_COLLECTION_TYPE_103`

- 行 105: `status="]success["`
  → `status = os.getenv("TEST_STREAMING_COLLECTOR_STATUS_105")`
  → 环境变量: `TEST_STREAMING_COLLECTOR_STATUS_105`

- 行 112: `data_source="test_source["`
  → `data_source = os.getenv("TEST_STREAMING_COLLECTOR_DATA_SOURCE_112")`
  → 环境变量: `TEST_STREAMING_COLLECTOR_DATA_SOURCE_112`

- 行 117: `data_source="]test_source["`
  → `data_source = os.getenv("TEST_STREAMING_COLLECTOR_DATA_SOURCE_117")`
  → 环境变量: `TEST_STREAMING_COLLECTOR_DATA_SOURCE_117`

- 行 117: `collection_type="]fixtures["`
  → `collection_type = os.getenv("TEST_STREAMING_COLLECTOR_COLLECTION_TYPE_117")`
  → 环境变量: `TEST_STREAMING_COLLECTOR_COLLECTION_TYPE_117`

- 行 120: `status="]success["`
  → `status = os.getenv("TEST_STREAMING_COLLECTOR_STATUS_120")`
  → 环境变量: `TEST_STREAMING_COLLECTOR_STATUS_120`

- 行 132: `data_source="]]test_source["`
  → `data_source = os.getenv("TEST_STREAMING_COLLECTOR_DATA_SOURCE_132")`
  → 环境变量: `TEST_STREAMING_COLLECTOR_DATA_SOURCE_132`

- 行 138: `data_source="]test_source["`
  → `data_source = os.getenv("TEST_STREAMING_COLLECTOR_DATA_SOURCE_138")`
  → 环境变量: `TEST_STREAMING_COLLECTOR_DATA_SOURCE_138`

- 行 139: `collection_type="]fixtures["`
  → `collection_type = os.getenv("TEST_STREAMING_COLLECTOR_COLLECTION_TYPE_139")`
  → 环境变量: `TEST_STREAMING_COLLECTOR_COLLECTION_TYPE_139`

- 行 141: `status="]success["`
  → `status = os.getenv("TEST_STREAMING_COLLECTOR_STATUS_141")`
  → 环境变量: `TEST_STREAMING_COLLECTOR_STATUS_141`

- 行 151: `data_source="]test_source["`
  → `data_source = os.getenv("TEST_STREAMING_COLLECTOR_DATA_SOURCE_151")`
  → 环境变量: `TEST_STREAMING_COLLECTOR_DATA_SOURCE_151`

- 行 168: `data_source="]test_source["`
  → `data_source = os.getenv("TEST_STREAMING_COLLECTOR_DATA_SOURCE_168")`
  → 环境变量: `TEST_STREAMING_COLLECTOR_DATA_SOURCE_168`

- 行 168: `collection_type="]fixtures["`
  → `collection_type = os.getenv("TEST_STREAMING_COLLECTOR_COLLECTION_TYPE_168")`
  → 环境变量: `TEST_STREAMING_COLLECTOR_COLLECTION_TYPE_168`

- 行 172: `status="]success["`
  → `status = os.getenv("TEST_STREAMING_COLLECTOR_STATUS_172")`
  → 环境变量: `TEST_STREAMING_COLLECTOR_STATUS_172`

- 行 183: `data_source="]test_source["`
  → `data_source = os.getenv("TEST_STREAMING_COLLECTOR_DATA_SOURCE_183")`
  → 环境变量: `TEST_STREAMING_COLLECTOR_DATA_SOURCE_183`

- 行 198: `data_source="test_source["`
  → `data_source = os.getenv("TEST_STREAMING_COLLECTOR_DATA_SOURCE_198")`
  → 环境变量: `TEST_STREAMING_COLLECTOR_DATA_SOURCE_198`

- 行 213: `data_source="]test_source["`
  → `data_source = os.getenv("TEST_STREAMING_COLLECTOR_DATA_SOURCE_213")`
  → 环境变量: `TEST_STREAMING_COLLECTOR_DATA_SOURCE_213`

- 行 230: `data_source="]test_source["`
  → `data_source = os.getenv("TEST_STREAMING_COLLECTOR_DATA_SOURCE_230")`
  → 环境变量: `TEST_STREAMING_COLLECTOR_DATA_SOURCE_230`

- 行 245: `data_source="]custom_source["`
  → `data_source = os.getenv("TEST_STREAMING_COLLECTOR_DATA_SOURCE_245")`
  → 环境变量: `TEST_STREAMING_COLLECTOR_DATA_SOURCE_245`

- 行 263: `data_source="]test_source["`
  → `data_source = os.getenv("TEST_STREAMING_COLLECTOR_DATA_SOURCE_263")`
  → 环境变量: `TEST_STREAMING_COLLECTOR_DATA_SOURCE_263`

- 行 290: `data_source="]test_source["`
  → `data_source = os.getenv("TEST_STREAMING_COLLECTOR_DATA_SOURCE_290")`
  → 环境变量: `TEST_STREAMING_COLLECTOR_DATA_SOURCE_290`

- 行 323: `data_source="]]test_source["`
  → `data_source = os.getenv("TEST_STREAMING_COLLECTOR_DATA_SOURCE_323")`
  → 环境变量: `TEST_STREAMING_COLLECTOR_DATA_SOURCE_323`

- 行 332: `data_source="]test_source["`
  → `data_source = os.getenv("TEST_STREAMING_COLLECTOR_DATA_SOURCE_332")`
  → 环境变量: `TEST_STREAMING_COLLECTOR_DATA_SOURCE_332`

- 行 333: `collection_type="]fixtures["`
  → `collection_type = os.getenv("TEST_STREAMING_COLLECTOR_COLLECTION_TYPE_333")`
  → 环境变量: `TEST_STREAMING_COLLECTOR_COLLECTION_TYPE_333`

- 行 337: `status="]success["`
  → `status = os.getenv("TEST_STREAMING_COLLECTOR_STATUS_337")`
  → 环境变量: `TEST_STREAMING_COLLECTOR_STATUS_337`

- 行 349: `data_source="test_source["`
  → `data_source = os.getenv("TEST_STREAMING_COLLECTOR_DATA_SOURCE_349")`
  → 环境变量: `TEST_STREAMING_COLLECTOR_DATA_SOURCE_349`

- 行 355: `data_source="]test_source["`
  → `data_source = os.getenv("TEST_STREAMING_COLLECTOR_DATA_SOURCE_355")`
  → 环境变量: `TEST_STREAMING_COLLECTOR_DATA_SOURCE_355`

- 行 375: `data_source="]]test_source["`
  → `data_source = os.getenv("TEST_STREAMING_COLLECTOR_DATA_SOURCE_375")`
  → 环境变量: `TEST_STREAMING_COLLECTOR_DATA_SOURCE_375`

- 行 382: `data_source="]test_source["`
  → `data_source = os.getenv("TEST_STREAMING_COLLECTOR_DATA_SOURCE_382")`
  → 环境变量: `TEST_STREAMING_COLLECTOR_DATA_SOURCE_382`

- 行 382: `collection_type="]fixtures["`
  → `collection_type = os.getenv("TEST_STREAMING_COLLECTOR_COLLECTION_TYPE_382")`
  → 环境变量: `TEST_STREAMING_COLLECTOR_COLLECTION_TYPE_382`

- 行 382: `status="]success["`
  → `status = os.getenv("TEST_STREAMING_COLLECTOR_STATUS_382")`
  → 环境变量: `TEST_STREAMING_COLLECTOR_STATUS_382`

- 行 406: `data_source="]enriched_source["`
  → `data_source = os.getenv("TEST_STREAMING_COLLECTOR_DATA_SOURCE_406")`
  → 环境变量: `TEST_STREAMING_COLLECTOR_DATA_SOURCE_406`

### tests/legacy/unit/data/test_odds_collector.py

- 行 23: `api_key="]test_api_key["`
  → `api_key = os.getenv("TEST_ODDS_COLLECTOR_API_KEY_23")`
  → 环境变量: `TEST_ODDS_COLLECTOR_API_KEY_23`

- 行 23: `base_url = "]https//api.test-odds.com/v4["`
  → `base_url = os.getenv("TEST_ODDS_COLLECTOR_BASE_URL_23")`
  → 环境变量: `TEST_ODDS_COLLECTOR_BASE_URL_23`

- 行 254: `odds_id = "]match_1:bet365h2h["`
  → `odds_id = os.getenv("TEST_ODDS_COLLECTOR_ODDS_ID_254")`
  → 环境变量: `TEST_ODDS_COLLECTOR_ODDS_ID_254`

### tests/legacy/unit/data/test_scores_collector.py

- 行 167: `return_value = "invalid json string["`
  → `return_value = os.getenv("TEST_SCORES_COLLECTOR_RETURN_VALUE_167")`
  → 环境变量: `TEST_SCORES_COLLECTOR_RETURN_VALUE_167`

### tests/legacy/unit/data/test_football_data_cleaner_simple.py

- 行 102: `venue = ": Old Trafford  "`
  → `venue = os.getenv("TEST_FOOTBALL_DATA_CLEANER_SIMPLE_VENUE_102")`
  → 环境变量: `TEST_FOOTBALL_DATA_CLEANER_SIMPLE_VENUE_102`

- 行 135: `string_input = "not a list["`
  → `string_input = os.getenv("TEST_FOOTBALL_DATA_CLEANER_SIMPLE_STRING_INPUT_135")`
  → 环境变量: `TEST_FOOTBALL_DATA_CLEANER_SIMPLE_STRING_INPUT_135`

- 行 172: `local_time = "]2024-01-15T15:00:00+0800["`
  → `local_time = os.getenv("TEST_FOOTBALL_DATA_CLEANER_SIMPLE_LOCAL_TIME_172")`
  → 环境变量: `TEST_FOOTBALL_DATA_CLEANER_SIMPLE_LOCAL_TIME_172`

- 行 174: `invalid_time = "]2024-01-15 15:0000["`
  → `invalid_time = os.getenv("TEST_FOOTBALL_DATA_CLEANER_SIMPLE_INVALID_TIME_174")`
  → 环境变量: `TEST_FOOTBALL_DATA_CLEANER_SIMPLE_INVALID_TIME_174`

### tests/legacy/unit/data/collectors/test_fixtures_collector.py

- 行 25: `data_source="test_api["`
  → `data_source = os.getenv("TEST_FIXTURES_COLLECTOR_DATA_SOURCE_25")`
  → 环境变量: `TEST_FIXTURES_COLLECTOR_DATA_SOURCE_25`

- 行 25: `api_key="]test_key["`
  → `api_key = os.getenv("TEST_FIXTURES_COLLECTOR_API_KEY_25")`
  → 环境变量: `TEST_FIXTURES_COLLECTOR_API_KEY_25`

- 行 25: `base_url = "]https//api.test.com/v4["`
  → `base_url = os.getenv("TEST_FIXTURES_COLLECTOR_BASE_URL_25")`
  → 环境变量: `TEST_FIXTURES_COLLECTOR_BASE_URL_25`

- 行 31: `data_source="custom_api["`
  → `data_source = os.getenv("TEST_FIXTURES_COLLECTOR_DATA_SOURCE_31")`
  → 环境变量: `TEST_FIXTURES_COLLECTOR_DATA_SOURCE_31`

- 行 32: `api_key="]custom_key["`
  → `api_key = os.getenv("TEST_FIXTURES_COLLECTOR_API_KEY_32")`
  → 环境变量: `TEST_FIXTURES_COLLECTOR_API_KEY_32`

- 行 33: `base_url = "]https//custom.api.com["`
  → `base_url = os.getenv("TEST_FIXTURES_COLLECTOR_BASE_URL_33")`
  → 环境变量: `TEST_FIXTURES_COLLECTOR_BASE_URL_33`

### tests/legacy/unit/data/collectors/test_base_collector.py

- 行 27: `data_source="test_source["`
  → `data_source = os.getenv("TEST_BASE_COLLECTOR_DATA_SOURCE_27")`
  → 环境变量: `TEST_BASE_COLLECTOR_DATA_SOURCE_27`

- 行 27: `collection_type="]fixtures["`
  → `collection_type = os.getenv("TEST_BASE_COLLECTOR_COLLECTION_TYPE_27")`
  → 环境变量: `TEST_BASE_COLLECTOR_COLLECTION_TYPE_27`

- 行 27: `status="]success["`
  → `status = os.getenv("TEST_BASE_COLLECTOR_STATUS_27")`
  → 环境变量: `TEST_BASE_COLLECTOR_STATUS_27`

- 行 33: `data_source="test_source["`
  → `data_source = os.getenv("TEST_BASE_COLLECTOR_DATA_SOURCE_33")`
  → 环境变量: `TEST_BASE_COLLECTOR_DATA_SOURCE_33`

- 行 33: `collection_type="]odds["`
  → `collection_type = os.getenv("TEST_BASE_COLLECTOR_COLLECTION_TYPE_33")`
  → 环境变量: `TEST_BASE_COLLECTOR_COLLECTION_TYPE_33`

- 行 36: `status="]partial["`
  → `status = os.getenv("TEST_BASE_COLLECTOR_STATUS_36")`
  → 环境变量: `TEST_BASE_COLLECTOR_STATUS_36`

- 行 36: `error_message="]Some data failed to collect["`
  → `error_message = os.getenv("TEST_BASE_COLLECTOR_ERROR_MESSAGE_36")`
  → 环境变量: `TEST_BASE_COLLECTOR_ERROR_MESSAGE_36`

- 行 43: `collection_type="]fixtures["`
  → `collection_type = os.getenv("TEST_BASE_COLLECTOR_COLLECTION_TYPE_43")`
  → 环境变量: `TEST_BASE_COLLECTOR_COLLECTION_TYPE_43`

- 行 44: `status="]success["`
  → `status = os.getenv("TEST_BASE_COLLECTOR_STATUS_44")`
  → 环境变量: `TEST_BASE_COLLECTOR_STATUS_44`

- 行 45: `collection_type="]odds["`
  → `collection_type = os.getenv("TEST_BASE_COLLECTOR_COLLECTION_TYPE_45")`
  → 环境变量: `TEST_BASE_COLLECTOR_COLLECTION_TYPE_45`

- 行 46: `status="]success["`
  → `status = os.getenv("TEST_BASE_COLLECTOR_STATUS_46")`
  → 环境变量: `TEST_BASE_COLLECTOR_STATUS_46`

- 行 47: `collection_type="]live_scores["`
  → `collection_type = os.getenv("TEST_BASE_COLLECTOR_COLLECTION_TYPE_47")`
  → 环境变量: `TEST_BASE_COLLECTOR_COLLECTION_TYPE_47`

- 行 48: `status="]success["`
  → `status = os.getenv("TEST_BASE_COLLECTOR_STATUS_48")`
  → 环境变量: `TEST_BASE_COLLECTOR_STATUS_48`

- 行 49: `data_source="test_source["`
  → `data_source = os.getenv("TEST_BASE_COLLECTOR_DATA_SOURCE_49")`
  → 环境变量: `TEST_BASE_COLLECTOR_DATA_SOURCE_49`

- 行 57: `data_source="test_source["`
  → `data_source = os.getenv("TEST_BASE_COLLECTOR_DATA_SOURCE_57")`
  → 环境变量: `TEST_BASE_COLLECTOR_DATA_SOURCE_57`

- 行 63: `data_source="test_source["`
  → `data_source = os.getenv("TEST_BASE_COLLECTOR_DATA_SOURCE_63")`
  → 环境变量: `TEST_BASE_COLLECTOR_DATA_SOURCE_63`

- 行 77: `url = "]https//api.test.com/data["`
  → `url = os.getenv("TEST_BASE_COLLECTOR_URL_77")`
  → 环境变量: `TEST_BASE_COLLECTOR_URL_77`

- 行 81: `data_source="test_source["`
  → `data_source = os.getenv("TEST_BASE_COLLECTOR_DATA_SOURCE_81")`
  → 环境变量: `TEST_BASE_COLLECTOR_DATA_SOURCE_81`

- 行 94: `data_source="test_source["`
  → `data_source = os.getenv("TEST_BASE_COLLECTOR_DATA_SOURCE_94")`
  → 环境变量: `TEST_BASE_COLLECTOR_DATA_SOURCE_94`

- 行 100: `url = "]https//api.test.com/data["`
  → `url = os.getenv("TEST_BASE_COLLECTOR_URL_100")`
  → 环境变量: `TEST_BASE_COLLECTOR_URL_100`

- 行 104: `data_source="test_source["`
  → `data_source = os.getenv("TEST_BASE_COLLECTOR_DATA_SOURCE_104")`
  → 环境变量: `TEST_BASE_COLLECTOR_DATA_SOURCE_104`

- 行 118: `data_source="test_source["`
  → `data_source = os.getenv("TEST_BASE_COLLECTOR_DATA_SOURCE_118")`
  → 环境变量: `TEST_BASE_COLLECTOR_DATA_SOURCE_118`

- 行 123: `match = "]Always fails["`
  → `match = os.getenv("TEST_BASE_COLLECTOR_MATCH_123")`
  → 环境变量: `TEST_BASE_COLLECTOR_MATCH_123`

- 行 128: `data_source="test_source["`
  → `data_source = os.getenv("TEST_BASE_COLLECTOR_DATA_SOURCE_128")`
  → 环境变量: `TEST_BASE_COLLECTOR_DATA_SOURCE_128`

- 行 151: `data_source="test_source["`
  → `data_source = os.getenv("TEST_BASE_COLLECTOR_DATA_SOURCE_151")`
  → 环境变量: `TEST_BASE_COLLECTOR_DATA_SOURCE_151`

- 行 156: `data_source="test_source["`
  → `data_source = os.getenv("TEST_BASE_COLLECTOR_DATA_SOURCE_156")`
  → 环境变量: `TEST_BASE_COLLECTOR_DATA_SOURCE_156`

- 行 158: `match = "]Unsupported table name["`
  → `match = os.getenv("TEST_BASE_COLLECTOR_MATCH_158")`
  → 环境变量: `TEST_BASE_COLLECTOR_MATCH_158`

- 行 164: `data_source="test_source["`
  → `data_source = os.getenv("TEST_BASE_COLLECTOR_DATA_SOURCE_164")`
  → 环境变量: `TEST_BASE_COLLECTOR_DATA_SOURCE_164`

- 行 178: `data_source="test_source["`
  → `data_source = os.getenv("TEST_BASE_COLLECTOR_DATA_SOURCE_178")`
  → 环境变量: `TEST_BASE_COLLECTOR_DATA_SOURCE_178`

- 行 198: `data_source="test_source["`
  → `data_source = os.getenv("TEST_BASE_COLLECTOR_DATA_SOURCE_198")`
  → 环境变量: `TEST_BASE_COLLECTOR_DATA_SOURCE_198`

- 行 205: `data_source="test_source["`
  → `data_source = os.getenv("TEST_BASE_COLLECTOR_DATA_SOURCE_205")`
  → 环境变量: `TEST_BASE_COLLECTOR_DATA_SOURCE_205`

- 行 213: `data_source="test_source["`
  → `data_source = os.getenv("TEST_BASE_COLLECTOR_DATA_SOURCE_213")`
  → 环境变量: `TEST_BASE_COLLECTOR_DATA_SOURCE_213`

- 行 220: `data_source="test_source["`
  → `data_source = os.getenv("TEST_BASE_COLLECTOR_DATA_SOURCE_220")`
  → 环境变量: `TEST_BASE_COLLECTOR_DATA_SOURCE_220`

- 行 234: `data_source="test_source["`
  → `data_source = os.getenv("TEST_BASE_COLLECTOR_DATA_SOURCE_234")`
  → 环境变量: `TEST_BASE_COLLECTOR_DATA_SOURCE_234`

- 行 248: `data_source="test_source["`
  → `data_source = os.getenv("TEST_BASE_COLLECTOR_DATA_SOURCE_248")`
  → 环境变量: `TEST_BASE_COLLECTOR_DATA_SOURCE_248`

- 行 261: `data_source="]test_source["`
  → `data_source = os.getenv("TEST_BASE_COLLECTOR_DATA_SOURCE_261")`
  → 环境变量: `TEST_BASE_COLLECTOR_DATA_SOURCE_261`

- 行 261: `collection_type="]fixtures["`
  → `collection_type = os.getenv("TEST_BASE_COLLECTOR_COLLECTION_TYPE_261")`
  → 环境变量: `TEST_BASE_COLLECTOR_COLLECTION_TYPE_261`

- 行 261: `status="]success["`
  → `status = os.getenv("TEST_BASE_COLLECTOR_STATUS_261")`
  → 环境变量: `TEST_BASE_COLLECTOR_STATUS_261`

- 行 267: `data_source="test_source["`
  → `data_source = os.getenv("TEST_BASE_COLLECTOR_DATA_SOURCE_267")`
  → 环境变量: `TEST_BASE_COLLECTOR_DATA_SOURCE_267`

- 行 268: `data_source="]test_source["`
  → `data_source = os.getenv("TEST_BASE_COLLECTOR_DATA_SOURCE_268")`
  → 环境变量: `TEST_BASE_COLLECTOR_DATA_SOURCE_268`

- 行 269: `collection_type="]fixtures["`
  → `collection_type = os.getenv("TEST_BASE_COLLECTOR_COLLECTION_TYPE_269")`
  → 环境变量: `TEST_BASE_COLLECTOR_COLLECTION_TYPE_269`

- 行 271: `status="]success["`
  → `status = os.getenv("TEST_BASE_COLLECTOR_STATUS_271")`
  → 环境变量: `TEST_BASE_COLLECTOR_STATUS_271`

- 行 279: `data_source="test_source["`
  → `data_source = os.getenv("TEST_BASE_COLLECTOR_DATA_SOURCE_279")`
  → 环境变量: `TEST_BASE_COLLECTOR_DATA_SOURCE_279`

- 行 284: `data_source="]test_source["`
  → `data_source = os.getenv("TEST_BASE_COLLECTOR_DATA_SOURCE_284")`
  → 环境变量: `TEST_BASE_COLLECTOR_DATA_SOURCE_284`

- 行 284: `collection_type="]fixtures["`
  → `collection_type = os.getenv("TEST_BASE_COLLECTOR_COLLECTION_TYPE_284")`
  → 环境变量: `TEST_BASE_COLLECTOR_COLLECTION_TYPE_284`

- 行 286: `status="]success["`
  → `status = os.getenv("TEST_BASE_COLLECTOR_STATUS_286")`
  → 环境变量: `TEST_BASE_COLLECTOR_STATUS_286`

- 行 288: `data_source="test_source["`
  → `data_source = os.getenv("TEST_BASE_COLLECTOR_DATA_SOURCE_288")`
  → 环境变量: `TEST_BASE_COLLECTOR_DATA_SOURCE_288`

- 行 303: `data_source="test_source["`
  → `data_source = os.getenv("TEST_BASE_COLLECTOR_DATA_SOURCE_303")`
  → 环境变量: `TEST_BASE_COLLECTOR_DATA_SOURCE_303`

- 行 325: `data_source="test_source["`
  → `data_source = os.getenv("TEST_BASE_COLLECTOR_DATA_SOURCE_325")`
  → 环境变量: `TEST_BASE_COLLECTOR_DATA_SOURCE_325`

### tests/legacy/unit/data/collectors/test_streaming_collector.py

- 行 32: `data_source="]test_source["`
  → `data_source = os.getenv("TEST_STREAMING_COLLECTOR_DATA_SOURCE_32")`
  → 环境变量: `TEST_STREAMING_COLLECTOR_DATA_SOURCE_32`

- 行 44: `data_source="]test_source["`
  → `data_source = os.getenv("TEST_STREAMING_COLLECTOR_DATA_SOURCE_44")`
  → 环境变量: `TEST_STREAMING_COLLECTOR_DATA_SOURCE_44`

- 行 115: `data_source="test_source["`
  → `data_source = os.getenv("TEST_STREAMING_COLLECTOR_DATA_SOURCE_115")`
  → 环境变量: `TEST_STREAMING_COLLECTOR_DATA_SOURCE_115`

- 行 117: `collection_type="]fixtures["`
  → `collection_type = os.getenv("TEST_STREAMING_COLLECTOR_COLLECTION_TYPE_117")`
  → 环境变量: `TEST_STREAMING_COLLECTOR_COLLECTION_TYPE_117`

- 行 117: `status="]success["`
  → `status = os.getenv("TEST_STREAMING_COLLECTOR_STATUS_117")`
  → 环境变量: `TEST_STREAMING_COLLECTOR_STATUS_117`

- 行 120: `data_source="test_source["`
  → `data_source = os.getenv("TEST_STREAMING_COLLECTOR_DATA_SOURCE_120")`
  → 环境变量: `TEST_STREAMING_COLLECTOR_DATA_SOURCE_120`

- 行 120: `collection_type="]odds["`
  → `collection_type = os.getenv("TEST_STREAMING_COLLECTOR_COLLECTION_TYPE_120")`
  → 环境变量: `TEST_STREAMING_COLLECTOR_COLLECTION_TYPE_120`

- 行 121: `status="]success["`
  → `status = os.getenv("TEST_STREAMING_COLLECTOR_STATUS_121")`
  → 环境变量: `TEST_STREAMING_COLLECTOR_STATUS_121`

- 行 126: `data_source="test_source["`
  → `data_source = os.getenv("TEST_STREAMING_COLLECTOR_DATA_SOURCE_126")`
  → 环境变量: `TEST_STREAMING_COLLECTOR_DATA_SOURCE_126`

- 行 126: `collection_type="]scores["`
  → `collection_type = os.getenv("TEST_STREAMING_COLLECTOR_COLLECTION_TYPE_126")`
  → 环境变量: `TEST_STREAMING_COLLECTOR_COLLECTION_TYPE_126`

- 行 126: `status="]success["`
  → `status = os.getenv("TEST_STREAMING_COLLECTOR_STATUS_126")`
  → 环境变量: `TEST_STREAMING_COLLECTOR_STATUS_126`

- 行 134: `data_source="test_source["`
  → `data_source = os.getenv("TEST_STREAMING_COLLECTOR_DATA_SOURCE_134")`
  → 环境变量: `TEST_STREAMING_COLLECTOR_DATA_SOURCE_134`

- 行 135: `collection_type="]batch["`
  → `collection_type = os.getenv("TEST_STREAMING_COLLECTOR_COLLECTION_TYPE_135")`
  → 环境变量: `TEST_STREAMING_COLLECTOR_COLLECTION_TYPE_135`

- 行 135: `status="]success["`
  → `status = os.getenv("TEST_STREAMING_COLLECTOR_STATUS_135")`
  → 环境变量: `TEST_STREAMING_COLLECTOR_STATUS_135`

- 行 135: `error_message = "]流处理 - 成功["`
  → `error_message = os.getenv("TEST_STREAMING_COLLECTOR_ERROR_MESSAGE_135")`
  → 环境变量: `TEST_STREAMING_COLLECTOR_ERROR_MESSAGE_135`

- 行 144: `data_source="test_source["`
  → `data_source = os.getenv("TEST_STREAMING_COLLECTOR_DATA_SOURCE_144")`
  → 环境变量: `TEST_STREAMING_COLLECTOR_DATA_SOURCE_144`

- 行 146: `collection_type="]batch["`
  → `collection_type = os.getenv("TEST_STREAMING_COLLECTOR_COLLECTION_TYPE_146")`
  → 环境变量: `TEST_STREAMING_COLLECTOR_COLLECTION_TYPE_146`

- 行 147: `status="]success["`
  → `status = os.getenv("TEST_STREAMING_COLLECTOR_STATUS_147")`
  → 环境变量: `TEST_STREAMING_COLLECTOR_STATUS_147`

- 行 148: `error_message = "]流处理 - 成功["`
  → `error_message = os.getenv("TEST_STREAMING_COLLECTOR_ERROR_MESSAGE_148")`
  → 环境变量: `TEST_STREAMING_COLLECTOR_ERROR_MESSAGE_148`

- 行 211: `data_source="test_source["`
  → `data_source = os.getenv("TEST_STREAMING_COLLECTOR_DATA_SOURCE_211")`
  → 环境变量: `TEST_STREAMING_COLLECTOR_DATA_SOURCE_211`

- 行 212: `collection_type="]odds["`
  → `collection_type = os.getenv("TEST_STREAMING_COLLECTOR_COLLECTION_TYPE_212")`
  → 环境变量: `TEST_STREAMING_COLLECTOR_COLLECTION_TYPE_212`

- 行 213: `status="]success["`
  → `status = os.getenv("TEST_STREAMING_COLLECTOR_STATUS_213")`
  → 环境变量: `TEST_STREAMING_COLLECTOR_STATUS_213`

- 行 223: `data_source="test_source["`
  → `data_source = os.getenv("TEST_STREAMING_COLLECTOR_DATA_SOURCE_223")`
  → 环境变量: `TEST_STREAMING_COLLECTOR_DATA_SOURCE_223`

- 行 224: `collection_type="]fixtures["`
  → `collection_type = os.getenv("TEST_STREAMING_COLLECTOR_COLLECTION_TYPE_224")`
  → 环境变量: `TEST_STREAMING_COLLECTOR_COLLECTION_TYPE_224`

- 行 225: `status="]failed["`
  → `status = os.getenv("TEST_STREAMING_COLLECTOR_STATUS_225")`
  → 环境变量: `TEST_STREAMING_COLLECTOR_STATUS_225`

- 行 227: `error_message="]采集失败["`
  → `error_message = os.getenv("TEST_STREAMING_COLLECTOR_ERROR_MESSAGE_227")`
  → 环境变量: `TEST_STREAMING_COLLECTOR_ERROR_MESSAGE_227`

### tests/legacy/unit/data/collectors/test_odds_collector.py

- 行 26: `data_source="test_odds_api["`
  → `data_source = os.getenv("TEST_ODDS_COLLECTOR_DATA_SOURCE_26")`
  → 环境变量: `TEST_ODDS_COLLECTOR_DATA_SOURCE_26`

- 行 26: `api_key="]test_key["`
  → `api_key = os.getenv("TEST_ODDS_COLLECTOR_API_KEY_26")`
  → 环境变量: `TEST_ODDS_COLLECTOR_API_KEY_26`

- 行 26: `base_url = "]https//api.test.com/v4["`
  → `base_url = os.getenv("TEST_ODDS_COLLECTOR_BASE_URL_26")`
  → 环境变量: `TEST_ODDS_COLLECTOR_BASE_URL_26`

- 行 33: `data_source="custom_odds_api["`
  → `data_source = os.getenv("TEST_ODDS_COLLECTOR_DATA_SOURCE_33")`
  → 环境变量: `TEST_ODDS_COLLECTOR_DATA_SOURCE_33`

- 行 34: `api_key="]custom_key["`
  → `api_key = os.getenv("TEST_ODDS_COLLECTOR_API_KEY_34")`
  → 环境变量: `TEST_ODDS_COLLECTOR_API_KEY_34`

- 行 35: `base_url = "]https//custom.api.com["`
  → `base_url = os.getenv("TEST_ODDS_COLLECTOR_BASE_URL_35")`
  → 环境变量: `TEST_ODDS_COLLECTOR_BASE_URL_35`

### tests/legacy/unit/data/collectors/test_scores_collector.py

- 行 29: `data_source="test_scores_api["`
  → `data_source = os.getenv("TEST_SCORES_COLLECTOR_DATA_SOURCE_29")`
  → 环境变量: `TEST_SCORES_COLLECTOR_DATA_SOURCE_29`

- 行 29: `api_key="]test_key["`
  → `api_key = os.getenv("TEST_SCORES_COLLECTOR_API_KEY_29")`
  → 环境变量: `TEST_SCORES_COLLECTOR_API_KEY_29`

- 行 29: `base_url = "]https//api.test.com/v4["`
  → `base_url = os.getenv("TEST_SCORES_COLLECTOR_BASE_URL_29")`
  → 环境变量: `TEST_SCORES_COLLECTOR_BASE_URL_29`

- 行 29: `websocket_url = "]wss//api.test.com/ws["`
  → `websocket_url = os.getenv("TEST_SCORES_COLLECTOR_WEBSOCKET_URL_29")`
  → 环境变量: `TEST_SCORES_COLLECTOR_WEBSOCKET_URL_29`

- 行 38: `data_source="custom_scores_api["`
  → `data_source = os.getenv("TEST_SCORES_COLLECTOR_DATA_SOURCE_38")`
  → 环境变量: `TEST_SCORES_COLLECTOR_DATA_SOURCE_38`

- 行 38: `api_key="]custom_key["`
  → `api_key = os.getenv("TEST_SCORES_COLLECTOR_API_KEY_38")`
  → 环境变量: `TEST_SCORES_COLLECTOR_API_KEY_38`

- 行 39: `base_url = "]https//custom.api.com["`
  → `base_url = os.getenv("TEST_SCORES_COLLECTOR_BASE_URL_39")`
  → 环境变量: `TEST_SCORES_COLLECTOR_BASE_URL_39`

- 行 40: `websocket_url = "]wss//custom.api.com/ws["`
  → `websocket_url = os.getenv("TEST_SCORES_COLLECTOR_WEBSOCKET_URL_40")`
  → 环境变量: `TEST_SCORES_COLLECTOR_WEBSOCKET_URL_40`

- 行 244: `match = "WebSocket URL not configured["`
  → `match = os.getenv("TEST_SCORES_COLLECTOR_MATCH_244")`
  → 环境变量: `TEST_SCORES_COLLECTOR_MATCH_244`

- 行 331: `data_source="]test["`
  → `data_source = os.getenv("TEST_SCORES_COLLECTOR_DATA_SOURCE_331")`
  → 环境变量: `TEST_SCORES_COLLECTOR_DATA_SOURCE_331`

- 行 332: `collection_type="]live_scores["`
  → `collection_type = os.getenv("TEST_SCORES_COLLECTOR_COLLECTION_TYPE_332")`
  → 环境变量: `TEST_SCORES_COLLECTOR_COLLECTION_TYPE_332`

- 行 334: `status="]success["`
  → `status = os.getenv("TEST_SCORES_COLLECTOR_STATUS_334")`
  → 环境变量: `TEST_SCORES_COLLECTOR_STATUS_334`

- 行 337: `websocket_url="wss//test.com/ws["`
  → `websocket_url = os.getenv("TEST_SCORES_COLLECTOR_WEBSOCKET_URL_337")`
  → 环境变量: `TEST_SCORES_COLLECTOR_WEBSOCKET_URL_337`

- 行 443: `data_source="]test["`
  → `data_source = os.getenv("TEST_SCORES_COLLECTOR_DATA_SOURCE_443")`
  → 环境变量: `TEST_SCORES_COLLECTOR_DATA_SOURCE_443`

- 行 443: `collection_type="]live_scores["`
  → `collection_type = os.getenv("TEST_SCORES_COLLECTOR_COLLECTION_TYPE_443")`
  → 环境变量: `TEST_SCORES_COLLECTOR_COLLECTION_TYPE_443`

- 行 446: `status="]failed["`
  → `status = os.getenv("TEST_SCORES_COLLECTOR_STATUS_446")`
  → 环境变量: `TEST_SCORES_COLLECTOR_STATUS_446`

- 行 446: `error_message="]API Error["`
  → `error_message = os.getenv("TEST_SCORES_COLLECTOR_ERROR_MESSAGE_446")`
  → 环境变量: `TEST_SCORES_COLLECTOR_ERROR_MESSAGE_446`

### tests/legacy/unit/data/features/test_examples.py

- 行 59: `project_name="football_prediction_demo["`
  → `project_name = os.getenv("TEST_EXAMPLES_PROJECT_NAME_59")`
  → 环境变量: `TEST_EXAMPLES_PROJECT_NAME_59`

- 行 67: `match = "]连接失败["`
  → `match = os.getenv("TEST_EXAMPLES_MATCH_67")`
  → 环境变量: `TEST_EXAMPLES_MATCH_67`

- 行 79: `match = "]写入失败["`
  → `match = os.getenv("TEST_EXAMPLES_MATCH_79")`
  → 环境变量: `TEST_EXAMPLES_MATCH_79`

- 行 101: `match = "]获取失败["`
  → `match = os.getenv("TEST_EXAMPLES_MATCH_101")`
  → 环境变量: `TEST_EXAMPLES_MATCH_101`

### tests/legacy/unit/lineage/test_metadata_manager_basic.py

- 行 15: `custom_url = "http:_/custom-marquez8080["`
  → `custom_url = os.getenv("TEST_METADATA_MANAGER_BASIC_CUSTOM_URL_15")`
  → 环境变量: `TEST_METADATA_MANAGER_BASIC_CUSTOM_URL_15`

- 行 31: `namespace="]]test_namespace["`
  → `namespace = os.getenv("TEST_METADATA_MANAGER_BASIC_NAMESPACE_31")`
  → 环境变量: `TEST_METADATA_MANAGER_BASIC_NAMESPACE_31`

- 行 32: `name="]test_dataset["`
  → `name = os.getenv("TEST_METADATA_MANAGER_BASIC_NAME_32")`
  → 环境变量: `TEST_METADATA_MANAGER_BASIC_NAME_32`

- 行 32: `source_name="]test_source["`
  → `source_name = os.getenv("TEST_METADATA_MANAGER_BASIC_SOURCE_NAME_32")`
  → 环境变量: `TEST_METADATA_MANAGER_BASIC_SOURCE_NAME_32`

- 行 46: `namespace="]]test_namespace["`
  → `namespace = os.getenv("TEST_METADATA_MANAGER_BASIC_NAMESPACE_46")`
  → 环境变量: `TEST_METADATA_MANAGER_BASIC_NAMESPACE_46`

- 行 46: `name="]test_job["`
  → `name = os.getenv("TEST_METADATA_MANAGER_BASIC_NAME_46")`
  → 环境变量: `TEST_METADATA_MANAGER_BASIC_NAME_46`

- 行 46: `job_type="]batch["`
  → `job_type = os.getenv("TEST_METADATA_MANAGER_BASIC_JOB_TYPE_46")`
  → 环境变量: `TEST_METADATA_MANAGER_BASIC_JOB_TYPE_46`

- 行 89: `return_value = "http:_/localhost5000/api/v1/test["`
  → `return_value = os.getenv("TEST_METADATA_MANAGER_BASIC_RETURN_VALUE_89")`
  → 环境变量: `TEST_METADATA_MANAGER_BASIC_RETURN_VALUE_89`

### tests/legacy/unit/lineage/test_metadata_manager.py

- 行 21: `marquez_url="]]http://test5000["`
  → `marquez_url = os.getenv("TEST_METADATA_MANAGER_MARQUEZ_URL_21")`
  → 环境变量: `TEST_METADATA_MANAGER_MARQUEZ_URL_21`

- 行 31: `marquez_url="]http://custom8080["`
  → `marquez_url = os.getenv("TEST_METADATA_MANAGER_MARQUEZ_URL_31")`
  → 环境变量: `TEST_METADATA_MANAGER_MARQUEZ_URL_31`

- 行 50: `name="]]test_namespace["`
  → `name = os.getenv("TEST_METADATA_MANAGER_NAME_50")`
  → 环境变量: `TEST_METADATA_MANAGER_NAME_50`

- 行 50: `description="]Test namespace["`
  → `description = os.getenv("TEST_METADATA_MANAGER_DESCRIPTION_50")`
  → 环境变量: `TEST_METADATA_MANAGER_DESCRIPTION_50`

- 行 51: `owner_name="]test_owner["`
  → `owner_name = os.getenv("TEST_METADATA_MANAGER_OWNER_NAME_51")`
  → 环境变量: `TEST_METADATA_MANAGER_OWNER_NAME_51`

- 行 51: `expected_url = "]http://test5000/api/v1/namespaces["`
  → `expected_url = os.getenv("TEST_METADATA_MANAGER_EXPECTED_URL_51")`
  → 环境变量: `TEST_METADATA_MANAGER_EXPECTED_URL_51`

- 行 65: `name="]]minimal_namespace["`
  → `name = os.getenv("TEST_METADATA_MANAGER_NAME_65")`
  → 环境变量: `TEST_METADATA_MANAGER_NAME_65`

- 行 73: `match = "]Namespace already exists["`
  → `match = os.getenv("TEST_METADATA_MANAGER_MATCH_73")`
  → 环境变量: `TEST_METADATA_MANAGER_MATCH_73`

- 行 74: `name="]existing_namespace["`
  → `name = os.getenv("TEST_METADATA_MANAGER_NAME_74")`
  → 环境变量: `TEST_METADATA_MANAGER_NAME_74`

- 行 77: `match = "]Connection failed["`
  → `match = os.getenv("TEST_METADATA_MANAGER_MATCH_77")`
  → 环境变量: `TEST_METADATA_MANAGER_MATCH_77`

- 行 78: `name="]test_namespace["`
  → `name = os.getenv("TEST_METADATA_MANAGER_NAME_78")`
  → 环境变量: `TEST_METADATA_MANAGER_NAME_78`

- 行 85: `expected_url = "]http://test5000/api/v1/namespaces/test_namespace["`
  → `expected_url = os.getenv("TEST_METADATA_MANAGER_EXPECTED_URL_85")`
  → 环境变量: `TEST_METADATA_MANAGER_EXPECTED_URL_85`

- 行 90: `match = "]]Not found["`
  → `match = os.getenv("TEST_METADATA_MANAGER_MATCH_90")`
  → 环境变量: `TEST_METADATA_MANAGER_MATCH_90`

- 行 117: `namespace="]]test_namespace["`
  → `namespace = os.getenv("TEST_METADATA_MANAGER_NAMESPACE_117")`
  → 环境变量: `TEST_METADATA_MANAGER_NAMESPACE_117`

- 行 117: `name="]test_dataset["`
  → `name = os.getenv("TEST_METADATA_MANAGER_NAME_117")`
  → 环境变量: `TEST_METADATA_MANAGER_NAME_117`

- 行 118: `description="]Test dataset["`
  → `description = os.getenv("TEST_METADATA_MANAGER_DESCRIPTION_118")`
  → 环境变量: `TEST_METADATA_MANAGER_DESCRIPTION_118`

- 行 119: `expected_url = "]http://test5000/api/v1/namespaces/test_namespace/datasets["`
  → `expected_url = os.getenv("TEST_METADATA_MANAGER_EXPECTED_URL_119")`
  → 环境变量: `TEST_METADATA_MANAGER_EXPECTED_URL_119`

- 行 125: `namespace="test_namespace["`
  → `namespace = os.getenv("TEST_METADATA_MANAGER_NAMESPACE_125")`
  → 环境变量: `TEST_METADATA_MANAGER_NAMESPACE_125`

- 行 125: `name="]test_dataset["`
  → `name = os.getenv("TEST_METADATA_MANAGER_NAME_125")`
  → 环境变量: `TEST_METADATA_MANAGER_NAME_125`

- 行 149: `expected_url = "]http://test5000/api/v1/namespaces/test_namespace/datasets["`
  → `expected_url = os.getenv("TEST_METADATA_MANAGER_EXPECTED_URL_149")`
  → 环境变量: `TEST_METADATA_MANAGER_EXPECTED_URL_149`

- 行 160: `namespace="]]test_namespace["`
  → `namespace = os.getenv("TEST_METADATA_MANAGER_NAMESPACE_160")`
  → 环境变量: `TEST_METADATA_MANAGER_NAMESPACE_160`

- 行 161: `name="]test_job["`
  → `name = os.getenv("TEST_METADATA_MANAGER_NAME_161")`
  → 环境变量: `TEST_METADATA_MANAGER_NAME_161`

- 行 162: `description="]Test job["`
  → `description = os.getenv("TEST_METADATA_MANAGER_DESCRIPTION_162")`
  → 环境变量: `TEST_METADATA_MANAGER_DESCRIPTION_162`

- 行 163: `job_type="]BATCH["`
  → `job_type = os.getenv("TEST_METADATA_MANAGER_JOB_TYPE_163")`
  → 环境变量: `TEST_METADATA_MANAGER_JOB_TYPE_163`

- 行 163: `expected_url = "]http://test5000/api/v1/namespaces/test_namespace/jobs["`
  → `expected_url = os.getenv("TEST_METADATA_MANAGER_EXPECTED_URL_163")`
  → 环境变量: `TEST_METADATA_MANAGER_EXPECTED_URL_163`

- 行 170: `expected_url = "]http://test5000/api/v1/namespaces/test_namespace/jobs/test_job["`
  → `expected_url = os.getenv("TEST_METADATA_MANAGER_EXPECTED_URL_170")`
  → 环境变量: `TEST_METADATA_MANAGER_EXPECTED_URL_170`

- 行 179: `expected_url = "]http://test5000/api/v1/namespaces/test_namespace/jobs["`
  → `expected_url = os.getenv("TEST_METADATA_MANAGER_EXPECTED_URL_179")`
  → 环境变量: `TEST_METADATA_MANAGER_EXPECTED_URL_179`

- 行 191: `namespace="]]test_namespace["`
  → `namespace = os.getenv("TEST_METADATA_MANAGER_NAMESPACE_191")`
  → 环境变量: `TEST_METADATA_MANAGER_NAMESPACE_191`

- 行 192: `job_name="]test_job["`
  → `job_name = os.getenv("TEST_METADATA_MANAGER_JOB_NAME_192")`
  → 环境变量: `TEST_METADATA_MANAGER_JOB_NAME_192`

- 行 192: `nominal_start_time = "]2024-01-01T00:0000Z["`
  → `nominal_start_time = os.getenv("TEST_METADATA_MANAGER_NOMINAL_START_TIME_192")`
  → 环境变量: `TEST_METADATA_MANAGER_NOMINAL_START_TIME_192`

- 行 193: `nominal_end_time = "]2024-01-01T01:0000Z["`
  → `nominal_end_time = os.getenv("TEST_METADATA_MANAGER_NOMINAL_END_TIME_193")`
  → 环境变量: `TEST_METADATA_MANAGER_NOMINAL_END_TIME_193`

- 行 206: `expected_url = "]http://test5000/api/v1/namespaces/test_namespace/jobs/test_job/runs/test_run_id["`
  → `expected_url = os.getenv("TEST_METADATA_MANAGER_EXPECTED_URL_206")`
  → 环境变量: `TEST_METADATA_MANAGER_EXPECTED_URL_206`

- 行 231: `expected_url = "]http://test5000/api/v1/namespaces/test_namespace/jobs/test_job/runs/latest["`
  → `expected_url = os.getenv("TEST_METADATA_MANAGER_EXPECTED_URL_231")`
  → 环境变量: `TEST_METADATA_MANAGER_EXPECTED_URL_231`

- 行 240: `expected_url = "]http://test5000/api/v1/search["`
  → `expected_url = os.getenv("TEST_METADATA_MANAGER_EXPECTED_URL_240")`
  → 环境变量: `TEST_METADATA_MANAGER_EXPECTED_URL_240`

- 行 260: `expected_url = "]http://test5000/api/v1/health["`
  → `expected_url = os.getenv("TEST_METADATA_MANAGER_EXPECTED_URL_260")`
  → 环境变量: `TEST_METADATA_MANAGER_EXPECTED_URL_260`

- 行 275: `match = "]]Internal server error["`
  → `match = os.getenv("TEST_METADATA_MANAGER_MATCH_275")`
  → 环境变量: `TEST_METADATA_MANAGER_MATCH_275`

- 行 277: `match = "]Connection refused["`
  → `match = os.getenv("TEST_METADATA_MANAGER_MATCH_277")`
  → 环境变量: `TEST_METADATA_MANAGER_MATCH_277`

- 行 281: `match = "]Request timeout["`
  → `match = os.getenv("TEST_METADATA_MANAGER_MATCH_281")`
  → 环境变量: `TEST_METADATA_MANAGER_MATCH_281`

### tests/legacy/unit/lineage/test_metadata_manager_comprehensive.py

- 行 76: `custom_url = "http:_/custom-marquez8080["`
  → `custom_url = os.getenv("TEST_METADATA_MANAGER_COMPREHENSIVE_CUSTOM_URL_76")`
  → 环境变量: `TEST_METADATA_MANAGER_COMPREHENSIVE_CUSTOM_URL_76`

- 行 98: `name="test_namespace["`
  → `name = os.getenv("TEST_METADATA_MANAGER_COMPREHENSIVE_NAME_98")`
  → 环境变量: `TEST_METADATA_MANAGER_COMPREHENSIVE_NAME_98`

- 行 104: `text = "Bad Request["`
  → `text = os.getenv("TEST_METADATA_MANAGER_COMPREHENSIVE_TEXT_104")`
  → 环境变量: `TEST_METADATA_MANAGER_COMPREHENSIVE_TEXT_104`

- 行 106: `name="]]existing_namespace["`
  → `name = os.getenv("TEST_METADATA_MANAGER_COMPREHENSIVE_NAME_106")`
  → 环境变量: `TEST_METADATA_MANAGER_COMPREHENSIVE_NAME_106`

- 行 109: `name="]test_namespace["`
  → `name = os.getenv("TEST_METADATA_MANAGER_COMPREHENSIVE_NAME_109")`
  → 环境变量: `TEST_METADATA_MANAGER_COMPREHENSIVE_NAME_109`

- 行 192: `text = "Dataset not found["`
  → `text = os.getenv("TEST_METADATA_MANAGER_COMPREHENSIVE_TEXT_192")`
  → 环境变量: `TEST_METADATA_MANAGER_COMPREHENSIVE_TEXT_192`

- 行 204: `keyword="]test["`
  → `keyword = os.getenv("TEST_METADATA_MANAGER_COMPREHENSIVE_KEYWORD_204")`
  → 环境变量: `TEST_METADATA_MANAGER_COMPREHENSIVE_KEYWORD_204`

- 行 211: `namespace="]]test_namespace["`
  → `namespace = os.getenv("TEST_METADATA_MANAGER_COMPREHENSIVE_NAMESPACE_211")`
  → 环境变量: `TEST_METADATA_MANAGER_COMPREHENSIVE_NAMESPACE_211`

- 行 212: `keyword="]football["`
  → `keyword = os.getenv("TEST_METADATA_MANAGER_COMPREHENSIVE_KEYWORD_212")`
  → 环境变量: `TEST_METADATA_MANAGER_COMPREHENSIVE_KEYWORD_212`

- 行 243: `namespace="]]test_namespace["`
  → `namespace = os.getenv("TEST_METADATA_MANAGER_COMPREHENSIVE_NAMESPACE_243")`
  → 环境变量: `TEST_METADATA_MANAGER_COMPREHENSIVE_NAMESPACE_243`

- 行 243: `job_name="]test_job["`
  → `job_name = os.getenv("TEST_METADATA_MANAGER_COMPREHENSIVE_JOB_NAME_243")`
  → 环境变量: `TEST_METADATA_MANAGER_COMPREHENSIVE_JOB_NAME_243`

- 行 243: `status="]completed["`
  → `status = os.getenv("TEST_METADATA_MANAGER_COMPREHENSIVE_STATUS_243")`
  → 环境变量: `TEST_METADATA_MANAGER_COMPREHENSIVE_STATUS_243`

- 行 254: `text = "Dataset not found["`
  → `text = os.getenv("TEST_METADATA_MANAGER_COMPREHENSIVE_TEXT_254")`
  → 环境变量: `TEST_METADATA_MANAGER_COMPREHENSIVE_TEXT_254`

- 行 269: `text = "]]Resource already exists["`
  → `text = os.getenv("TEST_METADATA_MANAGER_COMPREHENSIVE_TEXT_269")`
  → 环境变量: `TEST_METADATA_MANAGER_COMPREHENSIVE_TEXT_269`

- 行 279: `text = "Internal Server Error["`
  → `text = os.getenv("TEST_METADATA_MANAGER_COMPREHENSIVE_TEXT_279")`
  → 环境变量: `TEST_METADATA_MANAGER_COMPREHENSIVE_TEXT_279`

- 行 279: `name="]]test_namespace["`
  → `name = os.getenv("TEST_METADATA_MANAGER_COMPREHENSIVE_NAME_279")`
  → 环境变量: `TEST_METADATA_MANAGER_COMPREHENSIVE_NAME_279`

- 行 286: `name="]test_namespace["`
  → `name = os.getenv("TEST_METADATA_MANAGER_COMPREHENSIVE_NAME_286")`
  → 环境变量: `TEST_METADATA_MANAGER_COMPREHENSIVE_NAME_286`

- 行 289: `text = "]Invalid response["`
  → `text = os.getenv("TEST_METADATA_MANAGER_COMPREHENSIVE_TEXT_289")`
  → 环境变量: `TEST_METADATA_MANAGER_COMPREHENSIVE_TEXT_289`

- 行 292: `name="]]test_namespace["`
  → `name = os.getenv("TEST_METADATA_MANAGER_COMPREHENSIVE_NAME_292")`
  → 环境变量: `TEST_METADATA_MANAGER_COMPREHENSIVE_NAME_292`

- 行 330: `name="]]test["`
  → `name = os.getenv("TEST_METADATA_MANAGER_COMPREHENSIVE_NAME_330")`
  → 环境变量: `TEST_METADATA_MANAGER_COMPREHENSIVE_NAME_330`

- 行 343: `namespace="]]test_workflow["`
  → `namespace = os.getenv("TEST_METADATA_MANAGER_COMPREHENSIVE_NAMESPACE_343")`
  → 环境变量: `TEST_METADATA_MANAGER_COMPREHENSIVE_NAMESPACE_343`

- 行 344: `name="]test_dataset["`
  → `name = os.getenv("TEST_METADATA_MANAGER_COMPREHENSIVE_NAME_344")`
  → 环境变量: `TEST_METADATA_MANAGER_COMPREHENSIVE_NAME_344`

- 行 344: `description="]Test dataset["`
  → `description = os.getenv("TEST_METADATA_MANAGER_COMPREHENSIVE_DESCRIPTION_34")`
  → 环境变量: `TEST_METADATA_MANAGER_COMPREHENSIVE_DESCRIPTION_34`

- 行 344: `namespace="test_workflow["`
  → `namespace = os.getenv("TEST_METADATA_MANAGER_COMPREHENSIVE_NAMESPACE_344")`
  → 环境变量: `TEST_METADATA_MANAGER_COMPREHENSIVE_NAMESPACE_344`

- 行 346: `name="]test_job["`
  → `name = os.getenv("TEST_METADATA_MANAGER_COMPREHENSIVE_NAME_346")`
  → 环境变量: `TEST_METADATA_MANAGER_COMPREHENSIVE_NAME_346`

- 行 346: `description="]Test job["`
  → `description = os.getenv("TEST_METADATA_MANAGER_COMPREHENSIVE_DESCRIPTION_34")`
  → 环境变量: `TEST_METADATA_MANAGER_COMPREHENSIVE_DESCRIPTION_34`

- 行 346: `type="]batch["`
  → `type = os.getenv("TEST_METADATA_MANAGER_COMPREHENSIVE_TYPE_346")`
  → 环境变量: `TEST_METADATA_MANAGER_COMPREHENSIVE_TYPE_346`

### tests/legacy/unit/lineage/test_lineage_reporter_batch_omega_006.py

- 行 75: `marquez_url = "http//localhost5000["`
  → `marquez_url = os.getenv("TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_MARQUEZ_URL_")`
  → 环境变量: `TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_MARQUEZ_URL_`

- 行 111: `marquez_url = "http:_/localhost5000["`
  → `marquez_url = os.getenv("TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_MARQUEZ_URL_")`
  → 环境变量: `TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_MARQUEZ_URL_`

- 行 112: `namespace="]test_namespace["`
  → `namespace = os.getenv("TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_NAMESPACE_11")`
  → 环境变量: `TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_NAMESPACE_11`

- 行 123: `job_name="test_job["`
  → `job_name = os.getenv("TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_JOB_NAME_123")`
  → 环境变量: `TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_JOB_NAME_123`

- 行 123: `job_type="]BATCH["`
  → `job_type = os.getenv("TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_JOB_TYPE_123")`
  → 环境变量: `TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_JOB_TYPE_123`

- 行 135: `job_name="test_job["`
  → `job_name = os.getenv("TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_JOB_NAME_135")`
  → 环境变量: `TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_JOB_NAME_135`

- 行 135: `job_type="]BATCH["`
  → `job_type = os.getenv("TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_JOB_TYPE_135")`
  → 环境变量: `TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_JOB_TYPE_135`

- 行 135: `description="]Test job description["`
  → `description = os.getenv("TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_DESCRIPTION_")`
  → 环境变量: `TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_DESCRIPTION_`

- 行 137: `source_location = "]https_/github.com/test/repo["`
  → `source_location = os.getenv("TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_SOURCE_LOCAT")`
  → 环境变量: `TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_SOURCE_LOCAT`

- 行 139: `job_name="test_job["`
  → `job_name = os.getenv("TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_JOB_NAME_139")`
  → 环境变量: `TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_JOB_NAME_139`

- 行 141: `job_type="]BATCH["`
  → `job_type = os.getenv("TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_JOB_TYPE_141")`
  → 环境变量: `TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_JOB_TYPE_141`

- 行 141: `transformation_sql="]SELECT * FROM table["`
  → `transformation_sql = os.getenv("TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_TRANSFORMATI")`
  → 环境变量: `TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_TRANSFORMATI`

- 行 149: `job_name="test_job["`
  → `job_name = os.getenv("TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_JOB_NAME_149")`
  → 环境变量: `TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_JOB_NAME_149`

- 行 157: `match = "]Emit error["`
  → `match = os.getenv("TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_MATCH_157")`
  → 环境变量: `TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_MATCH_157`

- 行 158: `job_name="]test_job["`
  → `job_name = os.getenv("TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_JOB_NAME_158")`
  → 环境变量: `TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_JOB_NAME_158`

- 行 164: `job_name="test_job["`
  → `job_name = os.getenv("TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_JOB_NAME_164")`
  → 环境变量: `TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_JOB_NAME_164`

- 行 165: `job_name="]test_job["`
  → `job_name = os.getenv("TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_JOB_NAME_165")`
  → 环境变量: `TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_JOB_NAME_165`

- 行 169: `job_name="test_job["`
  → `job_name = os.getenv("TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_JOB_NAME_169")`
  → 环境变量: `TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_JOB_NAME_169`

- 行 171: `job_name="]test_job["`
  → `job_name = os.getenv("TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_JOB_NAME_171")`
  → 环境变量: `TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_JOB_NAME_171`

- 行 177: `job_name="test_job["`
  → `job_name = os.getenv("TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_JOB_NAME_177")`
  → 环境变量: `TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_JOB_NAME_177`

- 行 181: `job_name="nonexistent_job["`
  → `job_name = os.getenv("TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_JOB_NAME_181")`
  → 环境变量: `TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_JOB_NAME_181`

- 行 186: `job_name="test_job["`
  → `job_name = os.getenv("TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_JOB_NAME_186")`
  → 环境变量: `TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_JOB_NAME_186`

- 行 192: `job_name="]test_job["`
  → `job_name = os.getenv("TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_JOB_NAME_192")`
  → 环境变量: `TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_JOB_NAME_192`

- 行 198: `job_name="test_job["`
  → `job_name = os.getenv("TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_JOB_NAME_198")`
  → 环境变量: `TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_JOB_NAME_198`

- 行 199: `job_name="]test_job["`
  → `job_name = os.getenv("TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_JOB_NAME_199")`
  → 环境变量: `TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_JOB_NAME_199`

- 行 199: `error_message="]Test error["`
  → `error_message = os.getenv("TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_ERROR_MESSAG")`
  → 环境变量: `TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_ERROR_MESSAG`

- 行 206: `job_name="test_job["`
  → `job_name = os.getenv("TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_JOB_NAME_206")`
  → 环境变量: `TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_JOB_NAME_206`

- 行 206: `error_message="]Test error["`
  → `error_message = os.getenv("TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_ERROR_MESSAG")`
  → 环境变量: `TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_ERROR_MESSAG`

- 行 210: `job_name="nonexistent_job["`
  → `job_name = os.getenv("TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_JOB_NAME_210")`
  → 环境变量: `TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_JOB_NAME_210`

- 行 211: `error_message="]Test error["`
  → `error_message = os.getenv("TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_ERROR_MESSAG")`
  → 环境变量: `TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_ERROR_MESSAG`

- 行 213: `job_name="test_job["`
  → `job_name = os.getenv("TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_JOB_NAME_213")`
  → 环境变量: `TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_JOB_NAME_213`

- 行 219: `job_name="]test_job["`
  → `job_name = os.getenv("TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_JOB_NAME_219")`
  → 环境变量: `TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_JOB_NAME_219`

- 行 219: `error_message="]Test error["`
  → `error_message = os.getenv("TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_ERROR_MESSAG")`
  → 环境变量: `TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_ERROR_MESSAG`

- 行 229: `return_value = "test_run_id["`
  → `return_value = os.getenv("TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_RETURN_VALUE")`
  → 环境变量: `TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_RETURN_VALUE`

- 行 230: `source_name="]api_source["`
  → `source_name = os.getenv("TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_SOURCE_NAME_")`
  → 环境变量: `TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_SOURCE_NAME_`

- 行 231: `target_table="]raw_data["`
  → `target_table = os.getenv("TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_TARGET_TABLE")`
  → 环境变量: `TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_TARGET_TABLE`

- 行 243: `return_value = "]test_run_id["`
  → `return_value = os.getenv("TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_RETURN_VALUE")`
  → 环境变量: `TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_RETURN_VALUE`

- 行 245: `source_name="]api_source["`
  → `source_name = os.getenv("TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_SOURCE_NAME_")`
  → 环境变量: `TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_SOURCE_NAME_`

- 行 246: `target_table="]raw_data["`
  → `target_table = os.getenv("TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_TARGET_TABLE")`
  → 环境变量: `TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_TARGET_TABLE`

- 行 254: `return_value = "test_run_id["`
  → `return_value = os.getenv("TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_RETURN_VALUE")`
  → 环境变量: `TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_RETURN_VALUE`

- 行 254: `target_table="]target_table["`
  → `target_table = os.getenv("TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_TARGET_TABLE")`
  → 环境变量: `TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_TARGET_TABLE`

- 行 255: `transformation_sql="]SELECT * FROM source1["`
  → `transformation_sql = os.getenv("TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_TRANSFORMATI")`
  → 环境变量: `TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_TRANSFORMATI`

- 行 267: `return_value = "test_run_id["`
  → `return_value = os.getenv("TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_RETURN_VALUE")`
  → 环境变量: `TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_RETURN_VALUE`

- 行 267: `target_table="]target_table["`
  → `target_table = os.getenv("TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_TARGET_TABLE")`
  → 环境变量: `TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_TARGET_TABLE`

- 行 267: `transformation_sql="]SELECT * FROM source1["`
  → `transformation_sql = os.getenv("TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_TRANSFORMATI")`
  → 环境变量: `TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_TRANSFORMATI`

- 行 267: `transformation_type="]CLEANING["`
  → `transformation_type = os.getenv("TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_TRANSFORMATI")`
  → 环境变量: `TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_TRANSFORMATI`

- 行 275: `job_name="]job2["`
  → `job_name = os.getenv("TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_JOB_NAME_275")`
  → 环境变量: `TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_JOB_NAME_275`

- 行 277: `job_name="]job2["`
  → `job_name = os.getenv("TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_JOB_NAME_277")`
  → 环境变量: `TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_JOB_NAME_277`

- 行 285: `job_name="]job2["`
  → `job_name = os.getenv("TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_JOB_NAME_285")`
  → 环境变量: `TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_JOB_NAME_285`

- 行 289: `job_name="test_job["`
  → `job_name = os.getenv("TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_JOB_NAME_289")`
  → 环境变量: `TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_JOB_NAME_289`

- 行 291: `job_name="test_job["`
  → `job_name = os.getenv("TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_JOB_NAME_291")`
  → 环境变量: `TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_JOB_NAME_291`

- 行 296: `job_name="]]test_job["`
  → `job_name = os.getenv("TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_JOB_NAME_296")`
  → 环境变量: `TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_JOB_NAME_296`

- 行 301: `job_name="test_job["`
  → `job_name = os.getenv("TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_JOB_NAME_301")`
  → 环境变量: `TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_JOB_NAME_301`

- 行 304: `job_name="]]test_job["`
  → `job_name = os.getenv("TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_JOB_NAME_304")`
  → 环境变量: `TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_JOB_NAME_304`

- 行 304: `error_message="]Test error["`
  → `error_message = os.getenv("TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_ERROR_MESSAG")`
  → 环境变量: `TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_ERROR_MESSAG`

- 行 318: `job_name="]test_job["`
  → `job_name = os.getenv("TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_JOB_NAME_318")`
  → 环境变量: `TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_JOB_NAME_318`

- 行 324: `job_name="test_job["`
  → `job_name = os.getenv("TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_JOB_NAME_324")`
  → 环境变量: `TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_JOB_NAME_324`

- 行 324: `description="]Test description["`
  → `description = os.getenv("TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_DESCRIPTION_")`
  → 环境变量: `TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_DESCRIPTION_`

- 行 324: `source_location = "]https_/github.com/test/repo["`
  → `source_location = os.getenv("TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_SOURCE_LOCAT")`
  → 环境变量: `TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_SOURCE_LOCAT`

- 行 326: `transformation_sql="]SELECT * FROM table["`
  → `transformation_sql = os.getenv("TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_TRANSFORMATI")`
  → 环境变量: `TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_TRANSFORMATI`

- 行 327: `url="]https//github.com/test/repo["`
  → `url = os.getenv("TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_URL_327")`
  → 环境变量: `TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_URL_327`

- 行 327: `query="]SELECT * FROM table["`
  → `query = os.getenv("TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_QUERY_327")`
  → 环境变量: `TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_QUERY_327`

- 行 330: `job_name="test_job["`
  → `job_name = os.getenv("TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_JOB_NAME_330")`
  → 环境变量: `TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_JOB_NAME_330`

- 行 334: `job_name = "]test_job["`
  → `job_name = os.getenv("TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_JOB_NAME_334")`
  → 环境变量: `TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_JOB_NAME_334`

- 行 335: `job_name="test_job["`
  → `job_name = os.getenv("TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_JOB_NAME_335")`
  → 环境变量: `TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_JOB_NAME_335`

- 行 338: `job_name="]test_job["`
  → `job_name = os.getenv("TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_JOB_NAME_338")`
  → 环境变量: `TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_JOB_NAME_338`

- 行 338: `error_message="]Test error["`
  → `error_message = os.getenv("TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_ERROR_MESSAG")`
  → 环境变量: `TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_ERROR_MESSAG`

- 行 340: `message="]Test error["`
  → `message = os.getenv("TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_MESSAGE_340")`
  → 环境变量: `TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_MESSAGE_340`

- 行 341: `programmingLanguage="]PYTHON["`
  → `programmingLanguage = os.getenv("TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_PROGRAMMINGL")`
  → 环境变量: `TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_PROGRAMMINGL`

- 行 345: `job_name="test_job["`
  → `job_name = os.getenv("TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_JOB_NAME_345")`
  → 环境变量: `TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_JOB_NAME_345`

- 行 350: `namespace="]custom_namespace["`
  → `namespace = os.getenv("TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_NAMESPACE_35")`
  → 环境变量: `TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_NAMESPACE_35`

- 行 354: `job_name="test_job["`
  → `job_name = os.getenv("TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_JOB_NAME_354")`
  → 环境变量: `TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_JOB_NAME_354`

- 行 363: `job_name="]]test_job["`
  → `job_name = os.getenv("TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_JOB_NAME_363")`
  → 环境变量: `TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_JOB_NAME_363`

- 行 367: `job_name="]job2["`
  → `job_name = os.getenv("TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_JOB_NAME_367")`
  → 环境变量: `TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_JOB_NAME_367`

- 行 369: `job_name="]job3["`
  → `job_name = os.getenv("TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_JOB_NAME_369")`
  → 环境变量: `TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_JOB_NAME_369`

- 行 376: `job_name="]]job2["`
  → `job_name = os.getenv("TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_JOB_NAME_376")`
  → 环境变量: `TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_JOB_NAME_376`

- 行 381: `job_name="test_job["`
  → `job_name = os.getenv("TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_JOB_NAME_381")`
  → 环境变量: `TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_JOB_NAME_381`

- 行 383: `job_name="]]test_job["`
  → `job_name = os.getenv("TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_JOB_NAME_383")`
  → 环境变量: `TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_JOB_NAME_383`

- 行 383: `job_name="test_job["`
  → `job_name = os.getenv("TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_JOB_NAME_383")`
  → 环境变量: `TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_JOB_NAME_383`

- 行 385: `job_name="]test_job["`
  → `job_name = os.getenv("TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_JOB_NAME_385")`
  → 环境变量: `TEST_LINEAGE_REPORTER_BATCH_OMEGA_006_JOB_NAME_385`

### tests/legacy/unit/lineage/test_lineage_reporter_phase5.py

- 行 30: `marquez_url = "]http:_/localhost8080["`
  → `marquez_url = os.getenv("TEST_LINEAGE_REPORTER_PHASE5_MARQUEZ_URL_30")`
  → 环境变量: `TEST_LINEAGE_REPORTER_PHASE5_MARQUEZ_URL_30`

- 行 30: `namespace="]test_namespace["`
  → `namespace = os.getenv("TEST_LINEAGE_REPORTER_PHASE5_NAMESPACE_30")`
  → 环境变量: `TEST_LINEAGE_REPORTER_PHASE5_NAMESPACE_30`

- 行 33: `url = "]http://localhost8080["`
  → `url = os.getenv("TEST_LINEAGE_REPORTER_PHASE5_URL_33")`
  → 环境变量: `TEST_LINEAGE_REPORTER_PHASE5_URL_33`

- 行 92: `match = "]Connection failed["`
  → `match = os.getenv("TEST_LINEAGE_REPORTER_PHASE5_MATCH_92")`
  → 环境变量: `TEST_LINEAGE_REPORTER_PHASE5_MATCH_92`

- 行 210: `source_name="]football_api["`
  → `source_name = os.getenv("TEST_LINEAGE_REPORTER_PHASE5_SOURCE_NAME_210")`
  → 环境变量: `TEST_LINEAGE_REPORTER_PHASE5_SOURCE_NAME_210`

- 行 210: `target_table="]raw_matches["`
  → `target_table = os.getenv("TEST_LINEAGE_REPORTER_PHASE5_TARGET_TABLE_210")`
  → 环境变量: `TEST_LINEAGE_REPORTER_PHASE5_TARGET_TABLE_210`

- 行 230: `target_table="]processed_matches["`
  → `target_table = os.getenv("TEST_LINEAGE_REPORTER_PHASE5_TARGET_TABLE_230")`
  → 环境变量: `TEST_LINEAGE_REPORTER_PHASE5_TARGET_TABLE_230`

- 行 231: `transformation_sql="]SELECT * FROM raw_matches JOIN raw_teams..."`
  → `transformation_sql = os.getenv("TEST_LINEAGE_REPORTER_PHASE5_TRANSFORMATION_SQL_23")`
  → 环境变量: `TEST_LINEAGE_REPORTER_PHASE5_TRANSFORMATION_SQL_23`

- 行 232: `transformation_type="CLEANING["`
  → `transformation_type = os.getenv("TEST_LINEAGE_REPORTER_PHASE5_TRANSFORMATION_TYPE_2")`
  → 环境变量: `TEST_LINEAGE_REPORTER_PHASE5_TRANSFORMATION_TYPE_2`

- 行 456: `source_name="test_source["`
  → `source_name = os.getenv("TEST_LINEAGE_REPORTER_PHASE5_SOURCE_NAME_456")`
  → 环境变量: `TEST_LINEAGE_REPORTER_PHASE5_SOURCE_NAME_456`

- 行 457: `target_table="]test_table["`
  → `target_table = os.getenv("TEST_LINEAGE_REPORTER_PHASE5_TARGET_TABLE_457")`
  → 环境变量: `TEST_LINEAGE_REPORTER_PHASE5_TARGET_TABLE_457`

- 行 471: `target_table="]target_table["`
  → `target_table = os.getenv("TEST_LINEAGE_REPORTER_PHASE5_TARGET_TABLE_471")`
  → 环境变量: `TEST_LINEAGE_REPORTER_PHASE5_TARGET_TABLE_471`

- 行 472: `transformation_sql="]SELECT 1["`
  → `transformation_sql = os.getenv("TEST_LINEAGE_REPORTER_PHASE5_TRANSFORMATION_SQL_47")`
  → 环境变量: `TEST_LINEAGE_REPORTER_PHASE5_TRANSFORMATION_SQL_47`

### tests/legacy/unit/lineage/test_metadata_manager_batch_omega_005.py

- 行 49: `marquez_url="http:_/localhost5000["`
  → `marquez_url = os.getenv("TEST_METADATA_MANAGER_BATCH_OMEGA_005_MARQUEZ_URL_")`
  → 环境变量: `TEST_METADATA_MANAGER_BATCH_OMEGA_005_MARQUEZ_URL_`

- 行 59: `name="test_namespace["`
  → `name = os.getenv("TEST_METADATA_MANAGER_BATCH_OMEGA_005_NAME_59")`
  → 环境变量: `TEST_METADATA_MANAGER_BATCH_OMEGA_005_NAME_59`

- 行 59: `description="]Test namespace["`
  → `description = os.getenv("TEST_METADATA_MANAGER_BATCH_OMEGA_005_DESCRIPTION_")`
  → 环境变量: `TEST_METADATA_MANAGER_BATCH_OMEGA_005_DESCRIPTION_`

- 行 60: `owner_name="]test_owner["`
  → `owner_name = os.getenv("TEST_METADATA_MANAGER_BATCH_OMEGA_005_OWNER_NAME_6")`
  → 环境变量: `TEST_METADATA_MANAGER_BATCH_OMEGA_005_OWNER_NAME_6`

- 行 72: `name="minimal_namespace["`
  → `name = os.getenv("TEST_METADATA_MANAGER_BATCH_OMEGA_005_NAME_72")`
  → 环境变量: `TEST_METADATA_MANAGER_BATCH_OMEGA_005_NAME_72`

- 行 83: `name="]error_namespace["`
  → `name = os.getenv("TEST_METADATA_MANAGER_BATCH_OMEGA_005_NAME_83")`
  → 环境变量: `TEST_METADATA_MANAGER_BATCH_OMEGA_005_NAME_83`

- 行 85: `namespace="]test_namespace["`
  → `namespace = os.getenv("TEST_METADATA_MANAGER_BATCH_OMEGA_005_NAMESPACE_85")`
  → 环境变量: `TEST_METADATA_MANAGER_BATCH_OMEGA_005_NAMESPACE_85`

- 行 86: `name="]test_dataset["`
  → `name = os.getenv("TEST_METADATA_MANAGER_BATCH_OMEGA_005_NAME_86")`
  → 环境变量: `TEST_METADATA_MANAGER_BATCH_OMEGA_005_NAME_86`

- 行 87: `description="]Test dataset["`
  → `description = os.getenv("TEST_METADATA_MANAGER_BATCH_OMEGA_005_DESCRIPTION_")`
  → 环境变量: `TEST_METADATA_MANAGER_BATCH_OMEGA_005_DESCRIPTION_`

- 行 89: `source_name="]test_source["`
  → `source_name = os.getenv("TEST_METADATA_MANAGER_BATCH_OMEGA_005_SOURCE_NAME_")`
  → 环境变量: `TEST_METADATA_MANAGER_BATCH_OMEGA_005_SOURCE_NAME_`

- 行 94: `namespace="test_namespace["`
  → `namespace = os.getenv("TEST_METADATA_MANAGER_BATCH_OMEGA_005_NAMESPACE_94")`
  → 环境变量: `TEST_METADATA_MANAGER_BATCH_OMEGA_005_NAMESPACE_94`

- 行 94: `name="]minimal_dataset["`
  → `name = os.getenv("TEST_METADATA_MANAGER_BATCH_OMEGA_005_NAME_94")`
  → 环境变量: `TEST_METADATA_MANAGER_BATCH_OMEGA_005_NAME_94`

- 行 104: `namespace="test_namespace["`
  → `namespace = os.getenv("TEST_METADATA_MANAGER_BATCH_OMEGA_005_NAMESPACE_10")`
  → 环境变量: `TEST_METADATA_MANAGER_BATCH_OMEGA_005_NAMESPACE_10`

- 行 105: `name="]schema_dataset["`
  → `name = os.getenv("TEST_METADATA_MANAGER_BATCH_OMEGA_005_NAME_105")`
  → 环境变量: `TEST_METADATA_MANAGER_BATCH_OMEGA_005_NAME_105`

- 行 120: `namespace="]test_namespace["`
  → `namespace = os.getenv("TEST_METADATA_MANAGER_BATCH_OMEGA_005_NAMESPACE_12")`
  → 环境变量: `TEST_METADATA_MANAGER_BATCH_OMEGA_005_NAMESPACE_12`

- 行 120: `name="]error_dataset["`
  → `name = os.getenv("TEST_METADATA_MANAGER_BATCH_OMEGA_005_NAME_120")`
  → 环境变量: `TEST_METADATA_MANAGER_BATCH_OMEGA_005_NAME_120`

- 行 125: `namespace="test_namespace["`
  → `namespace = os.getenv("TEST_METADATA_MANAGER_BATCH_OMEGA_005_NAMESPACE_12")`
  → 环境变量: `TEST_METADATA_MANAGER_BATCH_OMEGA_005_NAMESPACE_12`

- 行 125: `name="]test_job["`
  → `name = os.getenv("TEST_METADATA_MANAGER_BATCH_OMEGA_005_NAME_125")`
  → 环境变量: `TEST_METADATA_MANAGER_BATCH_OMEGA_005_NAME_125`

- 行 125: `description="]Test job["`
  → `description = os.getenv("TEST_METADATA_MANAGER_BATCH_OMEGA_005_DESCRIPTION_")`
  → 环境变量: `TEST_METADATA_MANAGER_BATCH_OMEGA_005_DESCRIPTION_`

- 行 126: `job_type="]BATCH["`
  → `job_type = os.getenv("TEST_METADATA_MANAGER_BATCH_OMEGA_005_JOB_TYPE_126")`
  → 环境变量: `TEST_METADATA_MANAGER_BATCH_OMEGA_005_JOB_TYPE_126`

- 行 126: `location="]_path/to/job.py["`
  → `location = os.getenv("TEST_METADATA_MANAGER_BATCH_OMEGA_005_LOCATION_126")`
  → 环境变量: `TEST_METADATA_MANAGER_BATCH_OMEGA_005_LOCATION_126`

- 行 139: `namespace="test_namespace["`
  → `namespace = os.getenv("TEST_METADATA_MANAGER_BATCH_OMEGA_005_NAMESPACE_13")`
  → 环境变量: `TEST_METADATA_MANAGER_BATCH_OMEGA_005_NAMESPACE_13`

- 行 139: `name="]minimal_job["`
  → `name = os.getenv("TEST_METADATA_MANAGER_BATCH_OMEGA_005_NAME_139")`
  → 环境变量: `TEST_METADATA_MANAGER_BATCH_OMEGA_005_NAME_139`

- 行 144: `namespace="test_namespace["`
  → `namespace = os.getenv("TEST_METADATA_MANAGER_BATCH_OMEGA_005_NAMESPACE_14")`
  → 环境变量: `TEST_METADATA_MANAGER_BATCH_OMEGA_005_NAMESPACE_14`

- 行 144: `name="]stream_job["`
  → `name = os.getenv("TEST_METADATA_MANAGER_BATCH_OMEGA_005_NAME_144")`
  → 环境变量: `TEST_METADATA_MANAGER_BATCH_OMEGA_005_NAME_144`

- 行 144: `job_type="]STREAM["`
  → `job_type = os.getenv("TEST_METADATA_MANAGER_BATCH_OMEGA_005_JOB_TYPE_144")`
  → 环境变量: `TEST_METADATA_MANAGER_BATCH_OMEGA_005_JOB_TYPE_144`

- 行 154: `namespace="]test_namespace["`
  → `namespace = os.getenv("TEST_METADATA_MANAGER_BATCH_OMEGA_005_NAMESPACE_15")`
  → 环境变量: `TEST_METADATA_MANAGER_BATCH_OMEGA_005_NAMESPACE_15`

- 行 154: `name="]error_job["`
  → `name = os.getenv("TEST_METADATA_MANAGER_BATCH_OMEGA_005_NAME_154")`
  → 环境变量: `TEST_METADATA_MANAGER_BATCH_OMEGA_005_NAME_154`

- 行 159: `namespace="test_namespace["`
  → `namespace = os.getenv("TEST_METADATA_MANAGER_BATCH_OMEGA_005_NAMESPACE_15")`
  → 环境变量: `TEST_METADATA_MANAGER_BATCH_OMEGA_005_NAMESPACE_15`

- 行 159: `name="]test_dataset["`
  → `name = os.getenv("TEST_METADATA_MANAGER_BATCH_OMEGA_005_NAME_159")`
  → 环境变量: `TEST_METADATA_MANAGER_BATCH_OMEGA_005_NAME_159`

- 行 168: `namespace="test_namespace["`
  → `namespace = os.getenv("TEST_METADATA_MANAGER_BATCH_OMEGA_005_NAMESPACE_16")`
  → 环境变量: `TEST_METADATA_MANAGER_BATCH_OMEGA_005_NAMESPACE_16`

- 行 169: `name="]test_dataset["`
  → `name = os.getenv("TEST_METADATA_MANAGER_BATCH_OMEGA_005_NAME_169")`
  → 环境变量: `TEST_METADATA_MANAGER_BATCH_OMEGA_005_NAME_169`

- 行 174: `namespace="]test_namespace["`
  → `namespace = os.getenv("TEST_METADATA_MANAGER_BATCH_OMEGA_005_NAMESPACE_17")`
  → 环境变量: `TEST_METADATA_MANAGER_BATCH_OMEGA_005_NAMESPACE_17`

- 行 175: `name="]error_dataset["`
  → `name = os.getenv("TEST_METADATA_MANAGER_BATCH_OMEGA_005_NAME_175")`
  → 环境变量: `TEST_METADATA_MANAGER_BATCH_OMEGA_005_NAME_175`

- 行 184: `query="test_query["`
  → `query = os.getenv("TEST_METADATA_MANAGER_BATCH_OMEGA_005_QUERY_184")`
  → 环境变量: `TEST_METADATA_MANAGER_BATCH_OMEGA_005_QUERY_184`

- 行 184: `namespace="]test_namespace["`
  → `namespace = os.getenv("TEST_METADATA_MANAGER_BATCH_OMEGA_005_NAMESPACE_18")`
  → 环境变量: `TEST_METADATA_MANAGER_BATCH_OMEGA_005_NAMESPACE_18`

- 行 195: `query="]]test["`
  → `query = os.getenv("TEST_METADATA_MANAGER_BATCH_OMEGA_005_QUERY_195")`
  → 环境变量: `TEST_METADATA_MANAGER_BATCH_OMEGA_005_QUERY_195`

- 行 207: `query="]test["`
  → `query = os.getenv("TEST_METADATA_MANAGER_BATCH_OMEGA_005_QUERY_207")`
  → 环境变量: `TEST_METADATA_MANAGER_BATCH_OMEGA_005_QUERY_207`

- 行 217: `namespace="test_namespace["`
  → `namespace = os.getenv("TEST_METADATA_MANAGER_BATCH_OMEGA_005_NAMESPACE_21")`
  → 环境变量: `TEST_METADATA_MANAGER_BATCH_OMEGA_005_NAMESPACE_21`

- 行 217: `name="]test_dataset["`
  → `name = os.getenv("TEST_METADATA_MANAGER_BATCH_OMEGA_005_NAME_217")`
  → 环境变量: `TEST_METADATA_MANAGER_BATCH_OMEGA_005_NAME_217`

- 行 224: `namespace="]test_namespace["`
  → `namespace = os.getenv("TEST_METADATA_MANAGER_BATCH_OMEGA_005_NAMESPACE_22")`
  → 环境变量: `TEST_METADATA_MANAGER_BATCH_OMEGA_005_NAMESPACE_22`

- 行 224: `name="]error_dataset["`
  → `name = os.getenv("TEST_METADATA_MANAGER_BATCH_OMEGA_005_NAME_224")`
  → 环境变量: `TEST_METADATA_MANAGER_BATCH_OMEGA_005_NAME_224`

- 行 229: `namespace="test_namespace["`
  → `namespace = os.getenv("TEST_METADATA_MANAGER_BATCH_OMEGA_005_NAMESPACE_22")`
  → 环境变量: `TEST_METADATA_MANAGER_BATCH_OMEGA_005_NAMESPACE_22`

- 行 230: `job_name="]test_job["`
  → `job_name = os.getenv("TEST_METADATA_MANAGER_BATCH_OMEGA_005_JOB_NAME_230")`
  → 环境变量: `TEST_METADATA_MANAGER_BATCH_OMEGA_005_JOB_NAME_230`

- 行 246: `namespace="]]test_namespace["`
  → `namespace = os.getenv("TEST_METADATA_MANAGER_BATCH_OMEGA_005_NAMESPACE_24")`
  → 环境变量: `TEST_METADATA_MANAGER_BATCH_OMEGA_005_NAMESPACE_24`

- 行 246: `job_name="]test_job["`
  → `job_name = os.getenv("TEST_METADATA_MANAGER_BATCH_OMEGA_005_JOB_NAME_246")`
  → 环境变量: `TEST_METADATA_MANAGER_BATCH_OMEGA_005_JOB_NAME_246`

- 行 252: `namespace="]test_namespace["`
  → `namespace = os.getenv("TEST_METADATA_MANAGER_BATCH_OMEGA_005_NAMESPACE_25")`
  → 环境变量: `TEST_METADATA_MANAGER_BATCH_OMEGA_005_NAMESPACE_25`

- 行 252: `job_name="]error_job["`
  → `job_name = os.getenv("TEST_METADATA_MANAGER_BATCH_OMEGA_005_JOB_NAME_252")`
  → 环境变量: `TEST_METADATA_MANAGER_BATCH_OMEGA_005_JOB_NAME_252`

- 行 260: `namespace="test_namespace["`
  → `namespace = os.getenv("TEST_METADATA_MANAGER_BATCH_OMEGA_005_NAMESPACE_26")`
  → 环境变量: `TEST_METADATA_MANAGER_BATCH_OMEGA_005_NAMESPACE_26`

- 行 260: `name="]test_dataset["`
  → `name = os.getenv("TEST_METADATA_MANAGER_BATCH_OMEGA_005_NAME_260")`
  → 环境变量: `TEST_METADATA_MANAGER_BATCH_OMEGA_005_NAME_260`

- 行 262: `tag="]test_tag["`
  → `tag = os.getenv("TEST_METADATA_MANAGER_BATCH_OMEGA_005_TAG_262")`
  → 环境变量: `TEST_METADATA_MANAGER_BATCH_OMEGA_005_TAG_262`

- 行 273: `namespace="]test_namespace["`
  → `namespace = os.getenv("TEST_METADATA_MANAGER_BATCH_OMEGA_005_NAMESPACE_27")`
  → 环境变量: `TEST_METADATA_MANAGER_BATCH_OMEGA_005_NAMESPACE_27`

- 行 273: `name="]test_dataset["`
  → `name = os.getenv("TEST_METADATA_MANAGER_BATCH_OMEGA_005_NAME_273")`
  → 环境变量: `TEST_METADATA_MANAGER_BATCH_OMEGA_005_NAME_273`

- 行 273: `tag="]error_tag["`
  → `tag = os.getenv("TEST_METADATA_MANAGER_BATCH_OMEGA_005_TAG_273")`
  → 环境变量: `TEST_METADATA_MANAGER_BATCH_OMEGA_005_TAG_273`

- 行 321: `marquez_url="http:_/custom5000["`
  → `marquez_url = os.getenv("TEST_METADATA_MANAGER_BATCH_OMEGA_005_MARQUEZ_URL_")`
  → 环境变量: `TEST_METADATA_MANAGER_BATCH_OMEGA_005_MARQUEZ_URL_`

- 行 329: `marquez_url="http:_/localhost5000/"`
  → `marquez_url = os.getenv("TEST_METADATA_MANAGER_BATCH_OMEGA_005_MARQUEZ_URL_")`
  → 环境变量: `TEST_METADATA_MANAGER_BATCH_OMEGA_005_MARQUEZ_URL_`

- 行 376: `name="]]test_namespace["`
  → `name = os.getenv("TEST_METADATA_MANAGER_BATCH_OMEGA_005_NAME_376")`
  → 环境变量: `TEST_METADATA_MANAGER_BATCH_OMEGA_005_NAME_376`

- 行 392: `name="]test_namespace["`
  → `name = os.getenv("TEST_METADATA_MANAGER_BATCH_OMEGA_005_NAME_392")`
  → 环境变量: `TEST_METADATA_MANAGER_BATCH_OMEGA_005_NAME_392`

### tests/legacy/unit/lineage/test_lineage_reporter.py

- 行 45: `marquez_url="]http//test["`
  → `marquez_url = os.getenv("TEST_LINEAGE_REPORTER_MARQUEZ_URL_45")`
  → 环境变量: `TEST_LINEAGE_REPORTER_MARQUEZ_URL_45`

- 行 46: `job_name="]]unit_test_job["`
  → `job_name = os.getenv("TEST_LINEAGE_REPORTER_JOB_NAME_46")`
  → 环境变量: `TEST_LINEAGE_REPORTER_JOB_NAME_46`

- 行 47: `description="]demo["`
  → `description = os.getenv("TEST_LINEAGE_REPORTER_DESCRIPTION_47")`
  → 环境变量: `TEST_LINEAGE_REPORTER_DESCRIPTION_47`

- 行 48: `job_name="]finish_job["`
  → `job_name = os.getenv("TEST_LINEAGE_REPORTER_JOB_NAME_48")`
  → 环境变量: `TEST_LINEAGE_REPORTER_JOB_NAME_48`

- 行 50: `job_name="]finish_job["`
  → `job_name = os.getenv("TEST_LINEAGE_REPORTER_JOB_NAME_50")`
  → 环境变量: `TEST_LINEAGE_REPORTER_JOB_NAME_50`

- 行 60: `source_name="]]api["`
  → `source_name = os.getenv("TEST_LINEAGE_REPORTER_SOURCE_NAME_60")`
  → 环境变量: `TEST_LINEAGE_REPORTER_SOURCE_NAME_60`

- 行 61: `target_table="]raw_matches["`
  → `target_table = os.getenv("TEST_LINEAGE_REPORTER_TARGET_TABLE_61")`
  → 环境变量: `TEST_LINEAGE_REPORTER_TARGET_TABLE_61`

- 行 64: `target_table="]silver_fixtures["`
  → `target_table = os.getenv("TEST_LINEAGE_REPORTER_TARGET_TABLE_64")`
  → 环境变量: `TEST_LINEAGE_REPORTER_TARGET_TABLE_64`

- 行 64: `transformation_sql="]SELECT * FROM bronze_fixtures["`
  → `transformation_sql = os.getenv("TEST_LINEAGE_REPORTER_TRANSFORMATION_SQL_64")`
  → 环境变量: `TEST_LINEAGE_REPORTER_TRANSFORMATION_SQL_64`

- 行 68: `job_name="]]tmp["`
  → `job_name = os.getenv("TEST_LINEAGE_REPORTER_JOB_NAME_68")`
  → 环境变量: `TEST_LINEAGE_REPORTER_JOB_NAME_68`

### tests/legacy/unit/scheduler/test_task_scheduler_basic.py

- 行 22: `task_id="test_task["`
  → `task_id = os.getenv("TEST_TASK_SCHEDULER_BASIC_TASK_ID_22")`
  → 环境变量: `TEST_TASK_SCHEDULER_BASIC_TASK_ID_22`

- 行 22: `name="]测试任务["`
  → `name = os.getenv("TEST_TASK_SCHEDULER_BASIC_NAME_22")`
  → 环境变量: `TEST_TASK_SCHEDULER_BASIC_NAME_22`

- 行 22: `cron_expression="]0 0 * * *"`
  → `cron_expression = os.getenv("TEST_TASK_SCHEDULER_BASIC_CRON_EXPRESSION_22")`
  → 环境变量: `TEST_TASK_SCHEDULER_BASIC_CRON_EXPRESSION_22`

- 行 144: `new_cron = "*/30 * * * *"`
  → `new_cron = os.getenv("TEST_TASK_SCHEDULER_BASIC_NEW_CRON_144")`
  → 环境变量: `TEST_TASK_SCHEDULER_BASIC_NEW_CRON_144`

- 行 152: `task_id="test_task["`
  → `task_id = os.getenv("TEST_TASK_SCHEDULER_BASIC_TASK_ID_152")`
  → 环境变量: `TEST_TASK_SCHEDULER_BASIC_TASK_ID_152`

- 行 153: `name="]测试任务["`
  → `name = os.getenv("TEST_TASK_SCHEDULER_BASIC_NAME_153")`
  → 环境变量: `TEST_TASK_SCHEDULER_BASIC_NAME_153`

- 行 153: `cron_expression="]0 0 * * *"`
  → `cron_expression = os.getenv("TEST_TASK_SCHEDULER_BASIC_CRON_EXPRESSION_153")`
  → 环境变量: `TEST_TASK_SCHEDULER_BASIC_CRON_EXPRESSION_153`

- 行 157: `task_id="test_task["`
  → `task_id = os.getenv("TEST_TASK_SCHEDULER_BASIC_TASK_ID_157")`
  → 环境变量: `TEST_TASK_SCHEDULER_BASIC_TASK_ID_157`

- 行 157: `name="]测试任务["`
  → `name = os.getenv("TEST_TASK_SCHEDULER_BASIC_NAME_157")`
  → 环境变量: `TEST_TASK_SCHEDULER_BASIC_NAME_157`

- 行 157: `cron_expression="]0 0 * * *"`
  → `cron_expression = os.getenv("TEST_TASK_SCHEDULER_BASIC_CRON_EXPRESSION_157")`
  → 环境变量: `TEST_TASK_SCHEDULER_BASIC_CRON_EXPRESSION_157`

- 行 167: `task_id="test_task["`
  → `task_id = os.getenv("TEST_TASK_SCHEDULER_BASIC_TASK_ID_167")`
  → 环境变量: `TEST_TASK_SCHEDULER_BASIC_TASK_ID_167`

- 行 167: `name="]测试任务["`
  → `name = os.getenv("TEST_TASK_SCHEDULER_BASIC_NAME_167")`
  → 环境变量: `TEST_TASK_SCHEDULER_BASIC_NAME_167`

- 行 167: `cron_expression="]0 0 * * *"`
  → `cron_expression = os.getenv("TEST_TASK_SCHEDULER_BASIC_CRON_EXPRESSION_167")`
  → 环境变量: `TEST_TASK_SCHEDULER_BASIC_CRON_EXPRESSION_167`

- 行 176: `task_id="test_task["`
  → `task_id = os.getenv("TEST_TASK_SCHEDULER_BASIC_TASK_ID_176")`
  → 环境变量: `TEST_TASK_SCHEDULER_BASIC_TASK_ID_176`

- 行 176: `name="]测试任务["`
  → `name = os.getenv("TEST_TASK_SCHEDULER_BASIC_NAME_176")`
  → 环境变量: `TEST_TASK_SCHEDULER_BASIC_NAME_176`

- 行 176: `cron_expression="]0 0 * * *"`
  → `cron_expression = os.getenv("TEST_TASK_SCHEDULER_BASIC_CRON_EXPRESSION_176")`
  → 环境变量: `TEST_TASK_SCHEDULER_BASIC_CRON_EXPRESSION_176`

- 行 181: `task_id="]failing_task["`
  → `task_id = os.getenv("TEST_TASK_SCHEDULER_BASIC_TASK_ID_181")`
  → 环境变量: `TEST_TASK_SCHEDULER_BASIC_TASK_ID_181`

- 行 182: `name="]失败任务["`
  → `name = os.getenv("TEST_TASK_SCHEDULER_BASIC_NAME_182")`
  → 环境变量: `TEST_TASK_SCHEDULER_BASIC_NAME_182`

- 行 182: `cron_expression="]0 0 * * *"`
  → `cron_expression = os.getenv("TEST_TASK_SCHEDULER_BASIC_CRON_EXPRESSION_182")`
  → 环境变量: `TEST_TASK_SCHEDULER_BASIC_CRON_EXPRESSION_182`

- 行 187: `task_id="workflow_task["`
  → `task_id = os.getenv("TEST_TASK_SCHEDULER_BASIC_TASK_ID_187")`
  → 环境变量: `TEST_TASK_SCHEDULER_BASIC_TASK_ID_187`

- 行 188: `name="]工作流测试任务["`
  → `name = os.getenv("TEST_TASK_SCHEDULER_BASIC_NAME_188")`
  → 环境变量: `TEST_TASK_SCHEDULER_BASIC_NAME_188`

- 行 188: `cron_expression="]0 0 * * *"`
  → `cron_expression = os.getenv("TEST_TASK_SCHEDULER_BASIC_CRON_EXPRESSION_188")`
  → 环境变量: `TEST_TASK_SCHEDULER_BASIC_CRON_EXPRESSION_188`

### tests/legacy/unit/scheduler/test_celery_integration.py

- 行 55: `broker_url = "redis://localhost6379/0["`
  → `broker_url = os.getenv("TEST_CELERY_INTEGRATION_BROKER_URL_55")`
  → 环境变量: `TEST_CELERY_INTEGRATION_BROKER_URL_55`

- 行 55: `result_backend = "]redis://localhost6379/0["`
  → `result_backend = os.getenv("TEST_CELERY_INTEGRATION_RESULT_BACKEND_55")`
  → 环境变量: `TEST_CELERY_INTEGRATION_RESULT_BACKEND_55`

- 行 110: `topic = "]test_topic["`
  → `topic = os.getenv("TEST_CELERY_INTEGRATION_TOPIC_110")`
  → 环境变量: `TEST_CELERY_INTEGRATION_TOPIC_110`

- 行 138: `home_team="Team A["`
  → `home_team = os.getenv("TEST_CELERY_INTEGRATION_HOME_TEAM_138")`
  → 环境变量: `TEST_CELERY_INTEGRATION_HOME_TEAM_138`

- 行 138: `away_team="]Team B["`
  → `away_team = os.getenv("TEST_CELERY_INTEGRATION_AWAY_TEAM_138")`
  → 环境变量: `TEST_CELERY_INTEGRATION_AWAY_TEAM_138`

- 行 139: `date="]2024-01-01["`
  → `date = os.getenv("TEST_CELERY_INTEGRATION_DATE_139")`
  → 环境变量: `TEST_CELERY_INTEGRATION_DATE_139`

- 行 140: `home_team="]Team C["`
  → `home_team = os.getenv("TEST_CELERY_INTEGRATION_HOME_TEAM_140")`
  → 环境变量: `TEST_CELERY_INTEGRATION_HOME_TEAM_140`

- 行 140: `away_team="]Team D["`
  → `away_team = os.getenv("TEST_CELERY_INTEGRATION_AWAY_TEAM_140")`
  → 环境变量: `TEST_CELERY_INTEGRATION_AWAY_TEAM_140`

- 行 140: `date="]2024-01-02["`
  → `date = os.getenv("TEST_CELERY_INTEGRATION_DATE_140")`
  → 环境变量: `TEST_CELERY_INTEGRATION_DATE_140`

- 行 143: `season="]2024["`
  → `season = os.getenv("TEST_CELERY_INTEGRATION_SEASON_143")`
  → 环境变量: `TEST_CELERY_INTEGRATION_SEASON_143`

- 行 180: `home_team="Team A["`
  → `home_team = os.getenv("TEST_CELERY_INTEGRATION_HOME_TEAM_180")`
  → 环境变量: `TEST_CELERY_INTEGRATION_HOME_TEAM_180`

- 行 181: `away_team="]Team B["`
  → `away_team = os.getenv("TEST_CELERY_INTEGRATION_AWAY_TEAM_181")`
  → 环境变量: `TEST_CELERY_INTEGRATION_AWAY_TEAM_181`

- 行 182: `status="]LIVE["`
  → `status = os.getenv("TEST_CELERY_INTEGRATION_STATUS_182")`
  → 环境变量: `TEST_CELERY_INTEGRATION_STATUS_182`

- 行 182: `home_team="]Team C["`
  → `home_team = os.getenv("TEST_CELERY_INTEGRATION_HOME_TEAM_182")`
  → 环境变量: `TEST_CELERY_INTEGRATION_HOME_TEAM_182`

- 行 183: `away_team="]Team D["`
  → `away_team = os.getenv("TEST_CELERY_INTEGRATION_AWAY_TEAM_183")`
  → 环境变量: `TEST_CELERY_INTEGRATION_AWAY_TEAM_183`

- 行 183: `status="]LIVE["`
  → `status = os.getenv("TEST_CELERY_INTEGRATION_STATUS_183")`
  → 环境变量: `TEST_CELERY_INTEGRATION_STATUS_183`

- 行 300: `status = "SUCCESS["`
  → `status = os.getenv("TEST_CELERY_INTEGRATION_STATUS_300")`
  → 环境变量: `TEST_CELERY_INTEGRATION_STATUS_300`

- 行 308: `status = "FAILURE["`
  → `status = os.getenv("TEST_CELERY_INTEGRATION_STATUS_308")`
  → 环境变量: `TEST_CELERY_INTEGRATION_STATUS_308`

- 行 309: `traceback = "]]Traceback ... error details ..."`
  → `traceback = os.getenv("TEST_CELERY_INTEGRATION_TRACEBACK_309")`
  → 环境变量: `TEST_CELERY_INTEGRATION_TRACEBACK_309`

- 行 331: `task_name = "]]collect_fixtures["`
  → `task_name = os.getenv("TEST_CELERY_INTEGRATION_TASK_NAME_331")`
  → 环境变量: `TEST_CELERY_INTEGRATION_TASK_NAME_331`

- 行 364: `failure_reason = "Database connection failed["`
  → `failure_reason = os.getenv("TEST_CELERY_INTEGRATION_FAILURE_REASON_364")`
  → 环境变量: `TEST_CELERY_INTEGRATION_FAILURE_REASON_364`

- 行 365: `exception_type = "]ConnectionError["`
  → `exception_type = os.getenv("TEST_CELERY_INTEGRATION_EXCEPTION_TYPE_365")`
  → 环境变量: `TEST_CELERY_INTEGRATION_EXCEPTION_TYPE_365`

### tests/legacy/unit/scheduler/test_batch_execution.py

- 行 54: `cron_expression="]0 8 * * *"`
  → `cron_expression = os.getenv("TEST_BATCH_EXECUTION_CRON_EXPRESSION_54")`
  → 环境变量: `TEST_BATCH_EXECUTION_CRON_EXPRESSION_54`

- 行 63: `cron_expression="]0 8 * * *"`
  → `cron_expression = os.getenv("TEST_BATCH_EXECUTION_CRON_EXPRESSION_63")`
  → 环境变量: `TEST_BATCH_EXECUTION_CRON_EXPRESSION_63`

- 行 94: `task_id="valid_task["`
  → `task_id = os.getenv("TEST_BATCH_EXECUTION_TASK_ID_94")`
  → 环境变量: `TEST_BATCH_EXECUTION_TASK_ID_94`

- 行 94: `name="]Valid Task["`
  → `name = os.getenv("TEST_BATCH_EXECUTION_NAME_94")`
  → 环境变量: `TEST_BATCH_EXECUTION_NAME_94`

- 行 96: `cron_expression="]0 8 * * *"`
  → `cron_expression = os.getenv("TEST_BATCH_EXECUTION_CRON_EXPRESSION_96")`
  → 环境变量: `TEST_BATCH_EXECUTION_CRON_EXPRESSION_96`

- 行 96: `name="]Invalid Task["`
  → `name = os.getenv("TEST_BATCH_EXECUTION_NAME_96")`
  → 环境变量: `TEST_BATCH_EXECUTION_NAME_96`

- 行 96: `cron_expression="]invalid_cron["`
  → `cron_expression = os.getenv("TEST_BATCH_EXECUTION_CRON_EXPRESSION_96")`
  → 环境变量: `TEST_BATCH_EXECUTION_CRON_EXPRESSION_96`

- 行 182: `status="]success["`
  → `status = os.getenv("TEST_BATCH_EXECUTION_STATUS_182")`
  → 环境变量: `TEST_BATCH_EXECUTION_STATUS_182`

- 行 287: `task_id="performance_test["`
  → `task_id = os.getenv("TEST_BATCH_EXECUTION_TASK_ID_287")`
  → 环境变量: `TEST_BATCH_EXECUTION_TASK_ID_287`

- 行 288: `status="]success["`
  → `status = os.getenv("TEST_BATCH_EXECUTION_STATUS_288")`
  → 环境变量: `TEST_BATCH_EXECUTION_STATUS_288`

- 行 289: `result="]test_completed["`
  → `result = os.getenv("TEST_BATCH_EXECUTION_RESULT_289")`
  → 环境变量: `TEST_BATCH_EXECUTION_RESULT_289`

### tests/legacy/unit/scheduler/test_recovery_handler_batch_omega_004.py

- 行 35: `task_id = "test_task_001["`
  → `task_id = os.getenv("TEST_RECOVERY_HANDLER_BATCH_OMEGA_004_TASK_ID_35")`
  → 环境变量: `TEST_RECOVERY_HANDLER_BATCH_OMEGA_004_TASK_ID_35`

- 行 35: `name = "]测试任务["`
  → `name = os.getenv("TEST_RECOVERY_HANDLER_BATCH_OMEGA_004_NAME_35")`
  → 环境变量: `TEST_RECOVERY_HANDLER_BATCH_OMEGA_004_NAME_35`

- 行 35: `cron_expression = "]0 * * * *"`
  → `cron_expression = os.getenv("TEST_RECOVERY_HANDLER_BATCH_OMEGA_004_CRON_EXPRESS")`
  → 环境变量: `TEST_RECOVERY_HANDLER_BATCH_OMEGA_004_CRON_EXPRESS`

- 行 37: `task_id="test_task_001["`
  → `task_id = os.getenv("TEST_RECOVERY_HANDLER_BATCH_OMEGA_004_TASK_ID_37")`
  → 环境变量: `TEST_RECOVERY_HANDLER_BATCH_OMEGA_004_TASK_ID_37`

- 行 42: `error_message="]Task timeout["`
  → `error_message = os.getenv("TEST_RECOVERY_HANDLER_BATCH_OMEGA_004_ERROR_MESSAG")`
  → 环境变量: `TEST_RECOVERY_HANDLER_BATCH_OMEGA_004_ERROR_MESSAG`

- 行 59: `task_id="test_task_001["`
  → `task_id = os.getenv("TEST_RECOVERY_HANDLER_BATCH_OMEGA_004_TASK_ID_59")`
  → 环境变量: `TEST_RECOVERY_HANDLER_BATCH_OMEGA_004_TASK_ID_59`

- 行 61: `error_message="]Task timeout["`
  → `error_message = os.getenv("TEST_RECOVERY_HANDLER_BATCH_OMEGA_004_ERROR_MESSAG")`
  → 环境变量: `TEST_RECOVERY_HANDLER_BATCH_OMEGA_004_ERROR_MESSAG`

- 行 66: `task_id="test_task_001["`
  → `task_id = os.getenv("TEST_RECOVERY_HANDLER_BATCH_OMEGA_004_TASK_ID_66")`
  → 环境变量: `TEST_RECOVERY_HANDLER_BATCH_OMEGA_004_TASK_ID_66`

- 行 67: `error_message="]Task timeout["`
  → `error_message = os.getenv("TEST_RECOVERY_HANDLER_BATCH_OMEGA_004_ERROR_MESSAG")`
  → 环境变量: `TEST_RECOVERY_HANDLER_BATCH_OMEGA_004_ERROR_MESSAG`

- 行 73: `details="]立即重试成功["`
  → `details = os.getenv("TEST_RECOVERY_HANDLER_BATCH_OMEGA_004_DETAILS_73")`
  → 环境变量: `TEST_RECOVERY_HANDLER_BATCH_OMEGA_004_DETAILS_73`

- 行 80: `task_id="test_task_001["`
  → `task_id = os.getenv("TEST_RECOVERY_HANDLER_BATCH_OMEGA_004_TASK_ID_80")`
  → 环境变量: `TEST_RECOVERY_HANDLER_BATCH_OMEGA_004_TASK_ID_80`

- 行 83: `error_message="]Task timeout["`
  → `error_message = os.getenv("TEST_RECOVERY_HANDLER_BATCH_OMEGA_004_ERROR_MESSAG")`
  → 环境变量: `TEST_RECOVERY_HANDLER_BATCH_OMEGA_004_ERROR_MESSAG`

- 行 312: `__name__ = "test_handler["`
  → `__name__ = os.getenv("TEST_RECOVERY_HANDLER_BATCH_OMEGA_004___NAME___312")`
  → 环境变量: `TEST_RECOVERY_HANDLER_BATCH_OMEGA_004___NAME___312`

- 行 313: `level="]WARNING["`
  → `level = os.getenv("TEST_RECOVERY_HANDLER_BATCH_OMEGA_004_LEVEL_313")`
  → 环境变量: `TEST_RECOVERY_HANDLER_BATCH_OMEGA_004_LEVEL_313`

- 行 313: `message="]Test alert["`
  → `message = os.getenv("TEST_RECOVERY_HANDLER_BATCH_OMEGA_004_MESSAGE_313")`
  → 环境变量: `TEST_RECOVERY_HANDLER_BATCH_OMEGA_004_MESSAGE_313`

- 行 325: `__name__ = "]error_handler["`
  → `__name__ = os.getenv("TEST_RECOVERY_HANDLER_BATCH_OMEGA_004___NAME___325")`
  → 环境变量: `TEST_RECOVERY_HANDLER_BATCH_OMEGA_004___NAME___325`

- 行 330: `__name__ = "test_handler["`
  → `__name__ = os.getenv("TEST_RECOVERY_HANDLER_BATCH_OMEGA_004___NAME___330")`
  → 环境变量: `TEST_RECOVERY_HANDLER_BATCH_OMEGA_004___NAME___330`

- 行 360: `task_id="old_task["`
  → `task_id = os.getenv("TEST_RECOVERY_HANDLER_BATCH_OMEGA_004_TASK_ID_360")`
  → 环境变量: `TEST_RECOVERY_HANDLER_BATCH_OMEGA_004_TASK_ID_360`

- 行 360: `error_message="]Old error["`
  → `error_message = os.getenv("TEST_RECOVERY_HANDLER_BATCH_OMEGA_004_ERROR_MESSAG")`
  → 环境变量: `TEST_RECOVERY_HANDLER_BATCH_OMEGA_004_ERROR_MESSAG`

- 行 363: `task_id="]new_task["`
  → `task_id = os.getenv("TEST_RECOVERY_HANDLER_BATCH_OMEGA_004_TASK_ID_363")`
  → 环境变量: `TEST_RECOVERY_HANDLER_BATCH_OMEGA_004_TASK_ID_363`

- 行 365: `error_message="]New error["`
  → `error_message = os.getenv("TEST_RECOVERY_HANDLER_BATCH_OMEGA_004_ERROR_MESSAG")`
  → 环境变量: `TEST_RECOVERY_HANDLER_BATCH_OMEGA_004_ERROR_MESSAG`

- 行 373: `task_id="new_task["`
  → `task_id = os.getenv("TEST_RECOVERY_HANDLER_BATCH_OMEGA_004_TASK_ID_373")`
  → 环境变量: `TEST_RECOVERY_HANDLER_BATCH_OMEGA_004_TASK_ID_373`

- 行 375: `error_message="]New error["`
  → `error_message = os.getenv("TEST_RECOVERY_HANDLER_BATCH_OMEGA_004_ERROR_MESSAG")`
  → 环境变量: `TEST_RECOVERY_HANDLER_BATCH_OMEGA_004_ERROR_MESSAG`

- 行 393: `__name__ = "integration_test_handler["`
  → `__name__ = os.getenv("TEST_RECOVERY_HANDLER_BATCH_OMEGA_004___NAME___393")`
  → 环境变量: `TEST_RECOVERY_HANDLER_BATCH_OMEGA_004___NAME___393`

- 行 420: `__name__ = "handler1["`
  → `__name__ = os.getenv("TEST_RECOVERY_HANDLER_BATCH_OMEGA_004___NAME___420")`
  → 环境变量: `TEST_RECOVERY_HANDLER_BATCH_OMEGA_004___NAME___420`

- 行 421: `__name__ = "]handler2["`
  → `__name__ = os.getenv("TEST_RECOVERY_HANDLER_BATCH_OMEGA_004___NAME___421")`
  → 环境变量: `TEST_RECOVERY_HANDLER_BATCH_OMEGA_004___NAME___421`

- 行 429: `task_id = "invalid_task["`
  → `task_id = os.getenv("TEST_RECOVERY_HANDLER_BATCH_OMEGA_004_TASK_ID_429")`
  → 环境变量: `TEST_RECOVERY_HANDLER_BATCH_OMEGA_004_TASK_ID_429`

### tests/legacy/unit/scheduler/test_recovery_handler_basic.py

- 行 26: `task_id = "test_task["`
  → `task_id = os.getenv("TEST_RECOVERY_HANDLER_BASIC_TASK_ID_26")`
  → 环境变量: `TEST_RECOVERY_HANDLER_BASIC_TASK_ID_26`

- 行 26: `name = "]测试任务["`
  → `name = os.getenv("TEST_RECOVERY_HANDLER_BASIC_NAME_26")`
  → 环境变量: `TEST_RECOVERY_HANDLER_BASIC_NAME_26`

- 行 90: `error_message="数据库连接失败["`
  → `error_message = os.getenv("TEST_RECOVERY_HANDLER_BASIC_ERROR_MESSAGE_90")`
  → 环境变量: `TEST_RECOVERY_HANDLER_BASIC_ERROR_MESSAGE_90`

- 行 104: `error_message="数据格式错误["`
  → `error_message = os.getenv("TEST_RECOVERY_HANDLER_BASIC_ERROR_MESSAGE_104")`
  → 环境变量: `TEST_RECOVERY_HANDLER_BASIC_ERROR_MESSAGE_104`

- 行 128: `task_id = "test_task["`
  → `task_id = os.getenv("TEST_RECOVERY_HANDLER_BASIC_TASK_ID_128")`
  → 环境变量: `TEST_RECOVERY_HANDLER_BASIC_TASK_ID_128`

- 行 129: `name = "]测试任务["`
  → `name = os.getenv("TEST_RECOVERY_HANDLER_BASIC_NAME_129")`
  → 环境变量: `TEST_RECOVERY_HANDLER_BASIC_NAME_129`

- 行 131: `cron_expression = "]]0 0 * * *"`
  → `cron_expression = os.getenv("TEST_RECOVERY_HANDLER_BASIC_CRON_EXPRESSION_131")`
  → 环境变量: `TEST_RECOVERY_HANDLER_BASIC_CRON_EXPRESSION_131`

- 行 133: `__name__ = "custom_handler["`
  → `__name__ = os.getenv("TEST_RECOVERY_HANDLER_BASIC___NAME___133")`
  → 环境变量: `TEST_RECOVERY_HANDLER_BASIC___NAME___133`

- 行 167: `task_id="test_task["`
  → `task_id = os.getenv("TEST_RECOVERY_HANDLER_BASIC_TASK_ID_167")`
  → 环境变量: `TEST_RECOVERY_HANDLER_BASIC_TASK_ID_167`

- 行 169: `error_message="]网络错误["`
  → `error_message = os.getenv("TEST_RECOVERY_HANDLER_BASIC_ERROR_MESSAGE_169")`
  → 环境变量: `TEST_RECOVERY_HANDLER_BASIC_ERROR_MESSAGE_169`

- 行 176: `task_id="test_task["`
  → `task_id = os.getenv("TEST_RECOVERY_HANDLER_BASIC_TASK_ID_176")`
  → 环境变量: `TEST_RECOVERY_HANDLER_BASIC_TASK_ID_176`

- 行 176: `error_message="]网络错误["`
  → `error_message = os.getenv("TEST_RECOVERY_HANDLER_BASIC_ERROR_MESSAGE_176")`
  → 环境变量: `TEST_RECOVERY_HANDLER_BASIC_ERROR_MESSAGE_176`

- 行 182: `task_id="test_task["`
  → `task_id = os.getenv("TEST_RECOVERY_HANDLER_BASIC_TASK_ID_182")`
  → 环境变量: `TEST_RECOVERY_HANDLER_BASIC_TASK_ID_182`

- 行 182: `error_message="]网络错误["`
  → `error_message = os.getenv("TEST_RECOVERY_HANDLER_BASIC_ERROR_MESSAGE_182")`
  → 环境变量: `TEST_RECOVERY_HANDLER_BASIC_ERROR_MESSAGE_182`

### tests/legacy/unit/scheduler/test_task_scheduler.py

- 行 33: `task_id="test_task["`
  → `task_id = os.getenv("TEST_TASK_SCHEDULER_TASK_ID_33")`
  → 环境变量: `TEST_TASK_SCHEDULER_TASK_ID_33`

- 行 33: `name="]Test Task["`
  → `name = os.getenv("TEST_TASK_SCHEDULER_NAME_33")`
  → 环境变量: `TEST_TASK_SCHEDULER_NAME_33`

- 行 33: `cron_expression="]0 * * * *"`
  → `cron_expression = os.getenv("TEST_TASK_SCHEDULER_CRON_EXPRESSION_33")`
  → 环境变量: `TEST_TASK_SCHEDULER_CRON_EXPRESSION_33`

- 行 33: `description = "]Test task for unit testing["`
  → `description = os.getenv("TEST_TASK_SCHEDULER_DESCRIPTION_33")`
  → 环境变量: `TEST_TASK_SCHEDULER_DESCRIPTION_33`

- 行 60: `last_error = "Previous error["`
  → `last_error = os.getenv("TEST_TASK_SCHEDULER_LAST_ERROR_60")`
  → 环境变量: `TEST_TASK_SCHEDULER_LAST_ERROR_60`

- 行 67: `error="Task failed["`
  → `error = os.getenv("TEST_TASK_SCHEDULER_ERROR_67")`
  → 环境变量: `TEST_TASK_SCHEDULER_ERROR_67`

- 行 76: `task_id="invalid_task["`
  → `task_id = os.getenv("TEST_TASK_SCHEDULER_TASK_ID_76")`
  → 环境变量: `TEST_TASK_SCHEDULER_TASK_ID_76`

- 行 77: `name="]Invalid Task["`
  → `name = os.getenv("TEST_TASK_SCHEDULER_NAME_77")`
  → 环境变量: `TEST_TASK_SCHEDULER_NAME_77`

- 行 77: `cron_expression="]invalid_cron["`
  → `cron_expression = os.getenv("TEST_TASK_SCHEDULER_CRON_EXPRESSION_77")`
  → 环境变量: `TEST_TASK_SCHEDULER_CRON_EXPRESSION_77`

- 行 115: `task_id="test_task["`
  → `task_id = os.getenv("TEST_TASK_SCHEDULER_TASK_ID_115")`
  → 环境变量: `TEST_TASK_SCHEDULER_TASK_ID_115`

- 行 116: `name="]Test Task["`
  → `name = os.getenv("TEST_TASK_SCHEDULER_NAME_116")`
  → 环境变量: `TEST_TASK_SCHEDULER_NAME_116`

- 行 116: `cron_expression="]0 * * * *"`
  → `cron_expression = os.getenv("TEST_TASK_SCHEDULER_CRON_EXPRESSION_116")`
  → 环境变量: `TEST_TASK_SCHEDULER_CRON_EXPRESSION_116`

- 行 135: `task_id="invalid_task["`
  → `task_id = os.getenv("TEST_TASK_SCHEDULER_TASK_ID_135")`
  → 环境变量: `TEST_TASK_SCHEDULER_TASK_ID_135`

- 行 135: `name="]Invalid Task["`
  → `name = os.getenv("TEST_TASK_SCHEDULER_NAME_135")`
  → 环境变量: `TEST_TASK_SCHEDULER_NAME_135`

- 行 136: `cron_expression="]invalid["`
  → `cron_expression = os.getenv("TEST_TASK_SCHEDULER_CRON_EXPRESSION_136")`
  → 环境变量: `TEST_TASK_SCHEDULER_CRON_EXPRESSION_136`

- 行 257: `new_cron = "*/30 * * * *"`
  → `new_cron = os.getenv("TEST_TASK_SCHEDULER_NEW_CRON_257")`
  → 环境变量: `TEST_TASK_SCHEDULER_NEW_CRON_257`

- 行 307: `task_id="test_job["`
  → `task_id = os.getenv("TEST_TASK_SCHEDULER_TASK_ID_307")`
  → 环境变量: `TEST_TASK_SCHEDULER_TASK_ID_307`

- 行 317: `task_id="async_test_job["`
  → `task_id = os.getenv("TEST_TASK_SCHEDULER_TASK_ID_317")`
  → 环境变量: `TEST_TASK_SCHEDULER_TASK_ID_317`

- 行 324: `task_id="slow_job["`
  → `task_id = os.getenv("TEST_TASK_SCHEDULER_TASK_ID_324")`
  → 环境变量: `TEST_TASK_SCHEDULER_TASK_ID_324`

- 行 333: `task_id="]failing_job["`
  → `task_id = os.getenv("TEST_TASK_SCHEDULER_TASK_ID_333")`
  → 环境变量: `TEST_TASK_SCHEDULER_TASK_ID_333`

- 行 344: `task_id="]duplicate_job["`
  → `task_id = os.getenv("TEST_TASK_SCHEDULER_TASK_ID_344")`
  → 环境变量: `TEST_TASK_SCHEDULER_TASK_ID_344`

- 行 417: `job_id="test_job["`
  → `job_id = os.getenv("TEST_TASK_SCHEDULER_JOB_ID_417")`
  → 环境变量: `TEST_TASK_SCHEDULER_JOB_ID_417`

- 行 420: `result="]task_completed["`
  → `result = os.getenv("TEST_TASK_SCHEDULER_RESULT_420")`
  → 环境变量: `TEST_TASK_SCHEDULER_RESULT_420`

- 行 443: `job_id="failed_job["`
  → `job_id = os.getenv("TEST_TASK_SCHEDULER_JOB_ID_443")`
  → 环境变量: `TEST_TASK_SCHEDULER_JOB_ID_443`

- 行 445: `error="]Task failed due to timeout["`
  → `error = os.getenv("TEST_TASK_SCHEDULER_ERROR_445")`
  → 环境变量: `TEST_TASK_SCHEDULER_ERROR_445`

### tests/legacy/coverage/coverage_dashboard_generator.py

- 行 258: `charset="]UTF-8["`
  → `charset = os.getenv("COVERAGE_DASHBOARD_GENERATOR_CHARSET_258")`
  → 环境变量: `COVERAGE_DASHBOARD_GENERATOR_CHARSET_258`

- 行 258: `name="]viewport["`
  → `name = os.getenv("COVERAGE_DASHBOARD_GENERATOR_NAME_258")`
  → 环境变量: `COVERAGE_DASHBOARD_GENERATOR_NAME_258`

- 行 258: `content="]width=device-width, initial-scale=1.0["`
  → `content = os.getenv("COVERAGE_DASHBOARD_GENERATOR_CONTENT_258")`
  → 环境变量: `COVERAGE_DASHBOARD_GENERATOR_CONTENT_258`

- 行 347: `class="]container["`
  → `class = os.getenv("COVERAGE_DASHBOARD_GENERATOR_CLASS_347")`
  → 环境变量: `COVERAGE_DASHBOARD_GENERATOR_CLASS_347`

- 行 348: `class="]header["`
  → `class = os.getenv("COVERAGE_DASHBOARD_GENERATOR_CLASS_348")`
  → 环境变量: `COVERAGE_DASHBOARD_GENERATOR_CLASS_348`

- 行 354: `class="]metrics["`
  → `class = os.getenv("COVERAGE_DASHBOARD_GENERATOR_CLASS_354")`
  → 环境变量: `COVERAGE_DASHBOARD_GENERATOR_CLASS_354`

- 行 355: `class="]metric coverage-overall["`
  → `class = os.getenv("COVERAGE_DASHBOARD_GENERATOR_CLASS_355")`
  → 环境变量: `COVERAGE_DASHBOARD_GENERATOR_CLASS_355`

- 行 357: `class="]metric-label["`
  → `class = os.getenv("COVERAGE_DASHBOARD_GENERATOR_CLASS_357")`
  → 环境变量: `COVERAGE_DASHBOARD_GENERATOR_CLASS_357`

- 行 360: `class="]metric-value["`
  → `class = os.getenv("COVERAGE_DASHBOARD_GENERATOR_CLASS_360")`
  → 环境变量: `COVERAGE_DASHBOARD_GENERATOR_CLASS_360`

- 行 361: `class="]metric-label["`
  → `class = os.getenv("COVERAGE_DASHBOARD_GENERATOR_CLASS_361")`
  → 环境变量: `COVERAGE_DASHBOARD_GENERATOR_CLASS_361`

- 行 362: `class="]metric["`
  → `class = os.getenv("COVERAGE_DASHBOARD_GENERATOR_CLASS_362")`
  → 环境变量: `COVERAGE_DASHBOARD_GENERATOR_CLASS_362`

- 行 362: `class="]metric-label["`
  → `class = os.getenv("COVERAGE_DASHBOARD_GENERATOR_CLASS_362")`
  → 环境变量: `COVERAGE_DASHBOARD_GENERATOR_CLASS_362`

- 行 363: `class="]metric-value["`
  → `class = os.getenv("COVERAGE_DASHBOARD_GENERATOR_CLASS_363")`
  → 环境变量: `COVERAGE_DASHBOARD_GENERATOR_CLASS_363`

- 行 363: `class="]metric-label["`
  → `class = os.getenv("COVERAGE_DASHBOARD_GENERATOR_CLASS_363")`
  → 环境变量: `COVERAGE_DASHBOARD_GENERATOR_CLASS_363`

- 行 364: `class="]metric["`
  → `class = os.getenv("COVERAGE_DASHBOARD_GENERATOR_CLASS_364")`
  → 环境变量: `COVERAGE_DASHBOARD_GENERATOR_CLASS_364`

- 行 364: `class="]metric-label["`
  → `class = os.getenv("COVERAGE_DASHBOARD_GENERATOR_CLASS_364")`
  → 环境变量: `COVERAGE_DASHBOARD_GENERATOR_CLASS_364`

- 行 366: `class = "]metric-value["`
  → `class = os.getenv("COVERAGE_DASHBOARD_GENERATOR_CLASS_366")`
  → 环境变量: `COVERAGE_DASHBOARD_GENERATOR_CLASS_366`

- 行 367: `class="]metric-label["`
  → `class = os.getenv("COVERAGE_DASHBOARD_GENERATOR_CLASS_367")`
  → 环境变量: `COVERAGE_DASHBOARD_GENERATOR_CLASS_367`

- 行 368: `class="]section["`
  → `class = os.getenv("COVERAGE_DASHBOARD_GENERATOR_CLASS_368")`
  → 环境变量: `COVERAGE_DASHBOARD_GENERATOR_CLASS_368`

- 行 369: `class="]modules-table["`
  → `class = os.getenv("COVERAGE_DASHBOARD_GENERATOR_CLASS_369")`
  → 环境变量: `COVERAGE_DASHBOARD_GENERATOR_CLASS_369`

- 行 378: `style = "]color["`
  → `style = os.getenv("COVERAGE_DASHBOARD_GENERATOR_STYLE_378")`
  → 环境变量: `COVERAGE_DASHBOARD_GENERATOR_STYLE_378`

- 行 383: `class="]coverage-bar["`
  → `class = os.getenv("COVERAGE_DASHBOARD_GENERATOR_CLASS_383")`
  → 环境变量: `COVERAGE_DASHBOARD_GENERATOR_CLASS_383`

- 行 384: `class = "]coverage-fill["`
  → `class = os.getenv("COVERAGE_DASHBOARD_GENERATOR_CLASS_384")`
  → 环境变量: `COVERAGE_DASHBOARD_GENERATOR_CLASS_384`

- 行 385: `style="]width["`
  → `style = os.getenv("COVERAGE_DASHBOARD_GENERATOR_STYLE_385")`
  → 环境变量: `COVERAGE_DASHBOARD_GENERATOR_STYLE_385`

- 行 396: `class="section["`
  → `class = os.getenv("COVERAGE_DASHBOARD_GENERATOR_CLASS_396")`
  → 环境变量: `COVERAGE_DASHBOARD_GENERATOR_CLASS_396`

- 行 400: `class="]timestamp["`
  → `class = os.getenv("COVERAGE_DASHBOARD_GENERATOR_CLASS_400")`
  → 环境变量: `COVERAGE_DASHBOARD_GENERATOR_CLASS_400`

- 行 404: `encoding = "]utf-8["`
  → `encoding = os.getenv("COVERAGE_DASHBOARD_GENERATOR_ENCODING_404")`
  → 环境变量: `COVERAGE_DASHBOARD_GENERATOR_ENCODING_404`

- 行 442: `trend_direction = "]insufficient_data["`
  → `trend_direction = os.getenv("COVERAGE_DASHBOARD_GENERATOR_TREND_DIRECTION_442")`
  → 环境变量: `COVERAGE_DASHBOARD_GENERATOR_TREND_DIRECTION_442`

- 行 534: `encoding = "]utf-8["`
  → `encoding = os.getenv("COVERAGE_DASHBOARD_GENERATOR_ENCODING_534")`
  → 环境变量: `COVERAGE_DASHBOARD_GENERATOR_ENCODING_534`

- 行 542: `table = "| Date | Coverage | Commit | CI Run |\n["`
  → `table = os.getenv("COVERAGE_DASHBOARD_GENERATOR_TABLE_542")`
  → 环境变量: `COVERAGE_DASHBOARD_GENERATOR_TABLE_542`

### tests/legacy/mocks/data_quality_mocks.py

- 行 63: `errors="]raise["`
  → `errors = os.getenv("DATA_QUALITY_MOCKS_ERRORS_63")`
  → 环境变量: `DATA_QUALITY_MOCKS_ERRORS_63`

### tests/legacy/mocks/database_mocks.py

- 行 189: `host = "localhost["`
  → `host = os.getenv("DATABASE_MOCKS_HOST_189")`
  → 环境变量: `DATABASE_MOCKS_HOST_189`

- 行 189: `database = "]]test_db["`
  → `database = os.getenv("DATABASE_MOCKS_DATABASE_189")`
  → 环境变量: `DATABASE_MOCKS_DATABASE_189`

- 行 189: `username = "]test_user["`
  → `username = os.getenv("DATABASE_MOCKS_USERNAME_189")`
  → 环境变量: `DATABASE_MOCKS_USERNAME_189`

- 行 189: `password = "]test_password["`
  → `password = os.getenv("DATABASE_MOCKS_PASSWORD_189")`
  → 环境变量: `DATABASE_MOCKS_PASSWORD_189`

### tests/legacy/mocks/service_mocks.py

- 行 98: `current_model = "]v1.2["`
  → `current_model = os.getenv("SERVICE_MOCKS_CURRENT_MODEL_98")`
  → 环境变量: `SERVICE_MOCKS_CURRENT_MODEL_98`

### tests/legacy/e2e/test_prediction_pipeline.py

- 行 78: `match="]]Data processing failed["`
  → `match = os.getenv("TEST_PREDICTION_PIPELINE_MATCH_78")`
  → 环境变量: `TEST_PREDICTION_PIPELINE_MATCH_78`

### tests/legacy/e2e/conftest.py

- 行 9: `scope="session"`
  → `scope = os.getenv("CONFTEST_SCOPE_9")`
  → 环境变量: `CONFTEST_SCOPE_9`

- 行 12: `scope="session"`
  → `scope = os.getenv("CONFTEST_SCOPE_12")`
  → 环境变量: `CONFTEST_SCOPE_12`

- 行 18: `scope="session"`
  → `scope = os.getenv("CONFTEST_SCOPE_18")`
  → 环境变量: `CONFTEST_SCOPE_18`

### tests/legacy/e2e/test_model_training_pipeline.py

- 行 161: `match="Insufficient training data["`
  → `match = os.getenv("TEST_MODEL_TRAINING_PIPELINE_MATCH_161")`
  → 环境变量: `TEST_MODEL_TRAINING_PIPELINE_MATCH_161`

- 行 227: `version="]]v1.0["`
  → `version = os.getenv("TEST_MODEL_TRAINING_PIPELINE_VERSION_227")`
  → 环境变量: `TEST_MODEL_TRAINING_PIPELINE_VERSION_227`

### tests/legacy/mutation/run_mutation_tests.py

- 行 177: `encoding="]utf-8["`
  → `encoding = os.getenv("RUN_MUTATION_TESTS_ENCODING_177")`
  → 环境变量: `RUN_MUTATION_TESTS_ENCODING_177`

- 行 180: `table = "| File | Category | Threshold | Status |\n["`
  → `table = os.getenv("RUN_MUTATION_TESTS_TABLE_180")`
  → 环境变量: `RUN_MUTATION_TESTS_TABLE_180`

- 行 180: `status = "]✅ Tested["`
  → `status = os.getenv("RUN_MUTATION_TESTS_STATUS_180")`
  → 环境变量: `RUN_MUTATION_TESTS_STATUS_180`

### tests/legacy/factories/odds_factory.py

- 行 20: `sqlalchemy_session_persistence = "flush["`
  → `sqlalchemy_session_persistence = os.getenv("ODDS_FACTORY_SQLALCHEMY_SESSION_PERSISTENCE_20")`
  → 环境变量: `ODDS_FACTORY_SQLALCHEMY_SESSION_PERSISTENCE_20`

- 行 97: `sqlalchemy_session_persistence = "flush["`
  → `sqlalchemy_session_persistence = os.getenv("ODDS_FACTORY_SQLALCHEMY_SESSION_PERSISTENCE_97")`
  → 环境变量: `ODDS_FACTORY_SQLALCHEMY_SESSION_PERSISTENCE_97`

- 行 108: `sqlalchemy_session_persistence = "flush["`
  → `sqlalchemy_session_persistence = os.getenv("ODDS_FACTORY_SQLALCHEMY_SESSION_PERSISTENCE_108")`
  → 环境变量: `ODDS_FACTORY_SQLALCHEMY_SESSION_PERSISTENCE_108`

- 行 120: `sqlalchemy_session_persistence = "flush["`
  → `sqlalchemy_session_persistence = os.getenv("ODDS_FACTORY_SQLALCHEMY_SESSION_PERSISTENCE_120")`
  → 环境变量: `ODDS_FACTORY_SQLALCHEMY_SESSION_PERSISTENCE_120`

- 行 124: `sqlalchemy_session_persistence = "flush["`
  → `sqlalchemy_session_persistence = os.getenv("ODDS_FACTORY_SQLALCHEMY_SESSION_PERSISTENCE_124")`
  → 环境变量: `ODDS_FACTORY_SQLALCHEMY_SESSION_PERSISTENCE_124`

### tests/legacy/factories/match_factory.py

- 行 20: `sqlalchemy_session_persistence = "flush["`
  → `sqlalchemy_session_persistence = os.getenv("MATCH_FACTORY_SQLALCHEMY_SESSION_PERSISTENCE_20")`
  → 环境变量: `MATCH_FACTORY_SQLALCHEMY_SESSION_PERSISTENCE_20`

- 行 70: `sqlalchemy_session_persistence = "flush["`
  → `sqlalchemy_session_persistence = os.getenv("MATCH_FACTORY_SQLALCHEMY_SESSION_PERSISTENCE_70")`
  → 环境变量: `MATCH_FACTORY_SQLALCHEMY_SESSION_PERSISTENCE_70`

- 行 81: `sqlalchemy_session_persistence = "flush["`
  → `sqlalchemy_session_persistence = os.getenv("MATCH_FACTORY_SQLALCHEMY_SESSION_PERSISTENCE_81")`
  → 环境变量: `MATCH_FACTORY_SQLALCHEMY_SESSION_PERSISTENCE_81`

- 行 82: `status = "]scheduled["`
  → `status = os.getenv("MATCH_FACTORY_STATUS_82")`
  → 环境变量: `MATCH_FACTORY_STATUS_82`

- 行 87: `sqlalchemy_session_persistence = "flush["`
  → `sqlalchemy_session_persistence = os.getenv("MATCH_FACTORY_SQLALCHEMY_SESSION_PERSISTENCE_87")`
  → 环境变量: `MATCH_FACTORY_SQLALCHEMY_SESSION_PERSISTENCE_87`

- 行 95: `status = "]finished["`
  → `status = os.getenv("MATCH_FACTORY_STATUS_95")`
  → 环境变量: `MATCH_FACTORY_STATUS_95`

- 行 95: `sqlalchemy_session_persistence = "flush["`
  → `sqlalchemy_session_persistence = os.getenv("MATCH_FACTORY_SQLALCHEMY_SESSION_PERSISTENCE_95")`
  → 环境变量: `MATCH_FACTORY_SQLALCHEMY_SESSION_PERSISTENCE_95`

- 行 96: `status = "]finished["`
  → `status = os.getenv("MATCH_FACTORY_STATUS_96")`
  → 环境变量: `MATCH_FACTORY_STATUS_96`

### tests/legacy/factories/team_factory.py

- 行 19: `sqlalchemy_session_persistence = "flush["`
  → `sqlalchemy_session_persistence = os.getenv("TEAM_FACTORY_SQLALCHEMY_SESSION_PERSISTENCE_19")`
  → 环境变量: `TEAM_FACTORY_SQLALCHEMY_SESSION_PERSISTENCE_19`

### tests/unit/test_main.py

- 行 144: `return_value = "test_value"`
  → `return_value = os.getenv("TEST_MAIN_RETURN_VALUE_144")`
  → 环境变量: `TEST_MAIN_RETURN_VALUE_144`

### tests/unit/config/test_settings_comprehensive.py

- 行 33: `str = "sqlite:///./test.db"`
  → `str = os.getenv("TEST_SETTINGS_COMPREHENSIVE_STR_33")`
  → 环境变量: `TEST_SETTINGS_COMPREHENSIVE_STR_33`

- 行 39: `str = "redis://localhost:6379/0"`
  → `str = os.getenv("TEST_SETTINGS_COMPREHENSIVE_STR_39")`
  → 环境变量: `TEST_SETTINGS_COMPREHENSIVE_STR_39`

- 行 46: `str = "football_prediction"`
  → `str = os.getenv("TEST_SETTINGS_COMPREHENSIVE_STR_46")`
  → 环境变量: `TEST_SETTINGS_COMPREHENSIVE_STR_46`

- 行 47: `str = "Football Prediction API"`
  → `str = os.getenv("TEST_SETTINGS_COMPREHENSIVE_STR_47")`
  → 环境变量: `TEST_SETTINGS_COMPREHENSIVE_STR_47`

- 行 55: `str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"`
  → `str = os.getenv("TEST_SETTINGS_COMPREHENSIVE_STR_55")`
  → 环境变量: `TEST_SETTINGS_COMPREHENSIVE_STR_55`

- 行 66: `str = "development"`
  → `str = os.getenv("TEST_SETTINGS_COMPREHENSIVE_STR_66")`
  → 环境变量: `TEST_SETTINGS_COMPREHENSIVE_STR_66`

- 行 278: `url = "new_url"`
  → `url = os.getenv("TEST_SETTINGS_COMPREHENSIVE_URL_278")`
  → 环境变量: `TEST_SETTINGS_COMPREHENSIVE_URL_278`

### tests/unit/api/test_features_enhanced.py

- 行 220: `message=",
            "`
  → `message = os.getenv("TEST_FEATURES_ENHANCED_MESSAGE_220")`
  → 环境变量: `TEST_FEATURES_ENHANCED_MESSAGE_220`

- 行 220: `data=",
            "`
  → `data = os.getenv("TEST_FEATURES_ENHANCED_DATA_220")`
  → 环境变量: `TEST_FEATURES_ENHANCED_DATA_220`

### tests/unit/api/test_features_api.py

- 行 106: `team_name = "Test Team"`
  → `team_name = os.getenv("TEST_FEATURES_API_TEAM_NAME_106")`
  → 环境变量: `TEST_FEATURES_API_TEAM_NAME_106`

### tests/unit/api/test_schemas.py

- 行 27: `status="healthy"`
  → `status = os.getenv("TEST_SCHEMAS_STATUS_27")`
  → 环境变量: `TEST_SCHEMAS_STATUS_27`

- 行 38: `status="unhealthy"`
  → `status = os.getenv("TEST_SCHEMAS_STATUS_38")`
  → 环境变量: `TEST_SCHEMAS_STATUS_38`

- 行 76: `status="healthy"`
  → `status = os.getenv("TEST_SCHEMAS_STATUS_76")`
  → 环境变量: `TEST_SCHEMAS_STATUS_76`

- 行 92: `status="healthy"`
  → `status = os.getenv("TEST_SCHEMAS_STATUS_92")`
  → 环境变量: `TEST_SCHEMAS_STATUS_92`

- 行 95: `status="healthy"`
  → `status = os.getenv("TEST_SCHEMAS_STATUS_95")`
  → 环境变量: `TEST_SCHEMAS_STATUS_95`

- 行 95: `status="degraded"`
  → `status = os.getenv("TEST_SCHEMAS_STATUS_95")`
  → 环境变量: `TEST_SCHEMAS_STATUS_95`

- 行 97: `status="healthy"`
  → `status = os.getenv("TEST_SCHEMAS_STATUS_97")`
  → 环境变量: `TEST_SCHEMAS_STATUS_97`

- 行 97: `service="football-prediction-api"`
  → `service = os.getenv("TEST_SCHEMAS_SERVICE_97")`
  → 环境变量: `TEST_SCHEMAS_SERVICE_97`

- 行 114: `status="unhealthy"`
  → `status = os.getenv("TEST_SCHEMAS_STATUS_114")`
  → 环境变量: `TEST_SCHEMAS_STATUS_114`

- 行 117: `status="healthy"`
  → `status = os.getenv("TEST_SCHEMAS_STATUS_117")`
  → 环境变量: `TEST_SCHEMAS_STATUS_117`

- 行 120: `status="unhealthy"`
  → `status = os.getenv("TEST_SCHEMAS_STATUS_120")`
  → 环境变量: `TEST_SCHEMAS_STATUS_120`

- 行 120: `service="football-prediction-api"`
  → `service = os.getenv("TEST_SCHEMAS_SERVICE_120")`
  → 环境变量: `TEST_SCHEMAS_SERVICE_120`

- 行 134: `status="healthy"`
  → `status = os.getenv("TEST_SCHEMAS_STATUS_134")`
  → 环境变量: `TEST_SCHEMAS_STATUS_134`

- 行 149: `status="healthy"`
  → `status = os.getenv("TEST_SCHEMAS_STATUS_149")`
  → 环境变量: `TEST_SCHEMAS_STATUS_149`

- 行 153: `status="healthy"`
  → `status = os.getenv("TEST_SCHEMAS_STATUS_153")`
  → 环境变量: `TEST_SCHEMAS_STATUS_153`

- 行 156: `service="test-service"`
  → `service = os.getenv("TEST_SCHEMAS_SERVICE_156")`
  → 环境变量: `TEST_SCHEMAS_SERVICE_156`

- 行 173: `status="degraded"`
  → `status = os.getenv("TEST_SCHEMAS_STATUS_173")`
  → 环境变量: `TEST_SCHEMAS_STATUS_173`

- 行 190: `status="healthy"`
  → `status = os.getenv("TEST_SCHEMAS_STATUS_190")`
  → 环境变量: `TEST_SCHEMAS_STATUS_190`

- 行 204: `status="healthy"`
  → `status = os.getenv("TEST_SCHEMAS_STATUS_204")`
  → 环境变量: `TEST_SCHEMAS_STATUS_204`

- 行 229: `status="healthy"`
  → `status = os.getenv("TEST_SCHEMAS_STATUS_229")`
  → 环境变量: `TEST_SCHEMAS_STATUS_229`

- 行 256: `status="healthy"`
  → `status = os.getenv("TEST_SCHEMAS_STATUS_256")`
  → 环境变量: `TEST_SCHEMAS_STATUS_256`

- 行 276: `status="healthy"`
  → `status = os.getenv("TEST_SCHEMAS_STATUS_276")`
  → 环境变量: `TEST_SCHEMAS_STATUS_276`

- 行 291: `service="Football Prediction API"`
  → `service = os.getenv("TEST_SCHEMAS_SERVICE_291")`
  → 环境变量: `TEST_SCHEMAS_SERVICE_291`

- 行 293: `status="healthy"`
  → `status = os.getenv("TEST_SCHEMAS_STATUS_293")`
  → 环境变量: `TEST_SCHEMAS_STATUS_293`

- 行 314: `service="Test API"`
  → `service = os.getenv("TEST_SCHEMAS_SERVICE_314")`
  → 环境变量: `TEST_SCHEMAS_SERVICE_314`

- 行 315: `status="healthy"`
  → `status = os.getenv("TEST_SCHEMAS_STATUS_315")`
  → 环境变量: `TEST_SCHEMAS_STATUS_315`

- 行 324: `service="Test API"`
  → `service = os.getenv("TEST_SCHEMAS_SERVICE_324")`
  → 环境变量: `TEST_SCHEMAS_SERVICE_324`

- 行 337: `message="Resource not found"`
  → `message = os.getenv("TEST_SCHEMAS_MESSAGE_337")`
  → 环境变量: `TEST_SCHEMAS_MESSAGE_337`

- 行 370: `special_chars = "中文消息 & émoji 🚨 & special chars: <>&\"`
  → `special_chars = os.getenv("TEST_SCHEMAS_SPECIAL_CHARS_370")`
  → 环境变量: `TEST_SCHEMAS_SPECIAL_CHARS_370`

- 行 391: `status="healthy"`
  → `status = os.getenv("TEST_SCHEMAS_STATUS_391")`
  → 环境变量: `TEST_SCHEMAS_STATUS_391`

- 行 406: `status="healthy"`
  → `status = os.getenv("TEST_SCHEMAS_STATUS_406")`
  → 环境变量: `TEST_SCHEMAS_STATUS_406`

- 行 409: `status="healthy"`
  → `status = os.getenv("TEST_SCHEMAS_STATUS_409")`
  → 环境变量: `TEST_SCHEMAS_STATUS_409`

- 行 430: `service="Test API"`
  → `service = os.getenv("TEST_SCHEMAS_SERVICE_430")`
  → 环境变量: `TEST_SCHEMAS_SERVICE_430`

- 行 431: `status="healthy"`
  → `status = os.getenv("TEST_SCHEMAS_STATUS_431")`
  → 环境变量: `TEST_SCHEMAS_STATUS_431`

- 行 449: `status="healthy"`
  → `status = os.getenv("TEST_SCHEMAS_STATUS_449")`
  → 环境变量: `TEST_SCHEMAS_STATUS_449`

- 行 455: `status="healthy"`
  → `status = os.getenv("TEST_SCHEMAS_STATUS_455")`
  → 环境变量: `TEST_SCHEMAS_STATUS_455`

- 行 464: `status="healthy"`
  → `status = os.getenv("TEST_SCHEMAS_STATUS_464")`
  → 环境变量: `TEST_SCHEMAS_STATUS_464`

- 行 471: `status="healthy"`
  → `status = os.getenv("TEST_SCHEMAS_STATUS_471")`
  → 环境变量: `TEST_SCHEMAS_STATUS_471`

- 行 480: `status="healthy"`
  → `status = os.getenv("TEST_SCHEMAS_STATUS_480")`
  → 环境变量: `TEST_SCHEMAS_STATUS_480`

### tests/unit/api/test_health_comprehensive.py

- 行 236: `state = "closed"`
  → `state = os.getenv("TEST_HEALTH_COMPREHENSIVE_STATE_236")`
  → 环境变量: `TEST_HEALTH_COMPREHENSIVE_STATE_236`

- 行 300: `state = "closed"`
  → `state = os.getenv("TEST_HEALTH_COMPREHENSIVE_STATE_300")`
  → 环境变量: `TEST_HEALTH_COMPREHENSIVE_STATE_300`

- 行 347: `state = "closed"`
  → `state = os.getenv("TEST_HEALTH_COMPREHENSIVE_STATE_347")`
  → 环境变量: `TEST_HEALTH_COMPREHENSIVE_STATE_347`

### tests/unit/api/test_models_enhanced.py

- 行 62: `status="active"`
  → `status = os.getenv("TEST_MODELS_ENHANCED_STATUS_62")`
  → 环境变量: `TEST_MODELS_ENHANCED_STATUS_62`

- 行 119: `model_id="model_001"`
  → `model_id = os.getenv("TEST_MODELS_ENHANCED_MODEL_ID_119")`
  → 环境变量: `TEST_MODELS_ENHANCED_MODEL_ID_119`

- 行 150: `model_id="nonexistent_model"`
  → `model_id = os.getenv("TEST_MODELS_ENHANCED_MODEL_ID_150")`
  → 环境变量: `TEST_MODELS_ENHANCED_MODEL_ID_150`

- 行 244: `model_id="model_001"`
  → `model_id = os.getenv("TEST_MODELS_ENHANCED_MODEL_ID_244")`
  → 环境变量: `TEST_MODELS_ENHANCED_MODEL_ID_244`

- 行 274: `model_id="model_001"`
  → `model_id = os.getenv("TEST_MODELS_ENHANCED_MODEL_ID_274")`
  → 环境变量: `TEST_MODELS_ENHANCED_MODEL_ID_274`

- 行 295: `model_id="nonexistent_model"`
  → `model_id = os.getenv("TEST_MODELS_ENHANCED_MODEL_ID_295")`
  → 环境变量: `TEST_MODELS_ENHANCED_MODEL_ID_295`

- 行 340: `model_id="model_002"`
  → `model_id = os.getenv("TEST_MODELS_ENHANCED_MODEL_ID_340")`
  → 环境变量: `TEST_MODELS_ENHANCED_MODEL_ID_340`

- 行 382: `model_id="model_002"`
  → `model_id = os.getenv("TEST_MODELS_ENHANCED_MODEL_ID_382")`
  → 环境变量: `TEST_MODELS_ENHANCED_MODEL_ID_382`

- 行 418: `model_id="model_002"`
  → `model_id = os.getenv("TEST_MODELS_ENHANCED_MODEL_ID_418")`
  → 环境变量: `TEST_MODELS_ENHANCED_MODEL_ID_418`

- 行 526: `model_id="model_001"`
  → `model_id = os.getenv("TEST_MODELS_ENHANCED_MODEL_ID_526")`
  → 环境变量: `TEST_MODELS_ENHANCED_MODEL_ID_526`

- 行 583: `model_id="model_001"`
  → `model_id = os.getenv("TEST_MODELS_ENHANCED_MODEL_ID_583")`
  → 环境变量: `TEST_MODELS_ENHANCED_MODEL_ID_583`

- 行 626: `model_id="model_001"`
  → `model_id = os.getenv("TEST_MODELS_ENHANCED_MODEL_ID_626")`
  → 环境变量: `TEST_MODELS_ENHANCED_MODEL_ID_626`

- 行 688: `model_id="model_001"`
  → `model_id = os.getenv("TEST_MODELS_ENHANCED_MODEL_ID_688")`
  → 环境变量: `TEST_MODELS_ENHANCED_MODEL_ID_688`

- 行 770: `model_id="model_001"`
  → `model_id = os.getenv("TEST_MODELS_ENHANCED_MODEL_ID_770")`
  → 环境变量: `TEST_MODELS_ENHANCED_MODEL_ID_770`

### tests/unit/api/test_monitoring_api.py

- 行 170: `return_value = "# HELP test_metric\n"`
  → `return_value = os.getenv("TEST_MONITORING_API_RETURN_VALUE_170")`
  → 环境变量: `TEST_MONITORING_API_RETURN_VALUE_170`

### tests/unit/api/test_predictions_simple.py

- 行 149: `status="completed"`
  → `status = os.getenv("TEST_PREDICTIONS_SIMPLE_STATUS_149")`
  → 环境变量: `TEST_PREDICTIONS_SIMPLE_STATUS_149`

### tests/unit/api/test_models_simple2.py

- 行 201: `model_name = "nonexistent_model"`
  → `model_name = os.getenv("TEST_MODELS_SIMPLE2_MODEL_NAME_201")`
  → 环境变量: `TEST_MODELS_SIMPLE2_MODEL_NAME_201`

### tests/unit/api/test_models_api.py

- 行 23: `name = "test_model"`
  → `name = os.getenv("TEST_MODELS_API_NAME_23")`
  → 环境变量: `TEST_MODELS_API_NAME_23`

- 行 28: `run_id = "run_123"`
  → `run_id = os.getenv("TEST_MODELS_API_RUN_ID_28")`
  → 环境变量: `TEST_MODELS_API_RUN_ID_28`

- 行 29: `current_stage = "Production"`
  → `current_stage = os.getenv("TEST_MODELS_API_CURRENT_STAGE_29")`
  → 环境变量: `TEST_MODELS_API_CURRENT_STAGE_29`

- 行 90: `name = "test_model"`
  → `name = os.getenv("TEST_MODELS_API_NAME_90")`
  → 环境变量: `TEST_MODELS_API_NAME_90`

- 行 94: `run_id = "run_123"`
  → `run_id = os.getenv("TEST_MODELS_API_RUN_ID_94")`
  → 环境变量: `TEST_MODELS_API_RUN_ID_94`

- 行 133: `name = "test_model"`
  → `name = os.getenv("TEST_MODELS_API_NAME_133")`
  → 环境变量: `TEST_MODELS_API_NAME_133`

- 行 152: `name = "model_v1"`
  → `name = os.getenv("TEST_MODELS_API_NAME_152")`
  → 环境变量: `TEST_MODELS_API_NAME_152`

- 行 154: `name = "model_v2"`
  → `name = os.getenv("TEST_MODELS_API_NAME_154")`
  → 环境变量: `TEST_MODELS_API_NAME_154`

- 行 159: `run_id = "run_123"`
  → `run_id = os.getenv("TEST_MODELS_API_RUN_ID_159")`
  → 环境变量: `TEST_MODELS_API_RUN_ID_159`

- 行 205: `name = "test_model"`
  → `name = os.getenv("TEST_MODELS_API_NAME_205")`
  → 环境变量: `TEST_MODELS_API_NAME_205`

- 行 212: `run_id = "run_456"`
  → `run_id = os.getenv("TEST_MODELS_API_RUN_ID_212")`
  → 环境变量: `TEST_MODELS_API_RUN_ID_212`

- 行 265: `model_name="test_model"`
  → `model_name = os.getenv("TEST_MODELS_API_MODEL_NAME_265")`
  → 环境变量: `TEST_MODELS_API_MODEL_NAME_265`

- 行 285: `model_name="test_model"`
  → `model_name = os.getenv("TEST_MODELS_API_MODEL_NAME_285")`
  → 环境变量: `TEST_MODELS_API_MODEL_NAME_285`

- 行 302: `model_name="test_model"`
  → `model_name = os.getenv("TEST_MODELS_API_MODEL_NAME_302")`
  → 环境变量: `TEST_MODELS_API_MODEL_NAME_302`

- 行 349: `name = "test_experiment"`
  → `name = os.getenv("TEST_MODELS_API_NAME_349")`
  → 环境变量: `TEST_MODELS_API_NAME_349`

- 行 371: `view_type="ACTIVE_ONLY"`
  → `view_type = os.getenv("TEST_MODELS_API_VIEW_TYPE_371")`
  → 环境变量: `TEST_MODELS_API_VIEW_TYPE_371`

- 行 375: `view_type="ACTIVE_ONLY"`
  → `view_type = os.getenv("TEST_MODELS_API_VIEW_TYPE_375")`
  → 环境变量: `TEST_MODELS_API_VIEW_TYPE_375`

### tests/unit/api/test_cache_complete.py

- 行 128: `pattern="test:*"`
  → `pattern = os.getenv("TEST_CACHE_COMPLETE_PATTERN_128")`
  → 环境变量: `TEST_CACHE_COMPLETE_PATTERN_128`

- 行 327: `pattern="test:*"`
  → `pattern = os.getenv("TEST_CACHE_COMPLETE_PATTERN_327")`
  → 环境变量: `TEST_CACHE_COMPLETE_PATTERN_327`

### tests/unit/api/test_cache_comprehensive.py

- 行 195: `pattern="test:*"`
  → `pattern = os.getenv("TEST_CACHE_COMPREHENSIVE_PATTERN_195")`
  → 环境变量: `TEST_CACHE_COMPREHENSIVE_PATTERN_195`

### tests/unit/api/test_predictions_comprehensive.py

- 行 33: `match_status = "scheduled"`
  → `match_status = os.getenv("TEST_PREDICTIONS_COMPREHENSIVE_MATCH_STATUS_33")`
  → 环境变量: `TEST_PREDICTIONS_COMPREHENSIVE_MATCH_STATUS_33`

- 行 33: `season = "2024-25"`
  → `season = os.getenv("TEST_PREDICTIONS_COMPREHENSIVE_SEASON_33")`
  → 环境变量: `TEST_PREDICTIONS_COMPREHENSIVE_SEASON_33`

- 行 42: `model_name = "baseline"`
  → `model_name = os.getenv("TEST_PREDICTIONS_COMPREHENSIVE_MODEL_NAME_42")`
  → 环境变量: `TEST_PREDICTIONS_COMPREHENSIVE_MODEL_NAME_42`

- 行 224: `model_name = "baseline"`
  → `model_name = os.getenv("TEST_PREDICTIONS_COMPREHENSIVE_MODEL_NAME_224")`
  → 环境变量: `TEST_PREDICTIONS_COMPREHENSIVE_MODEL_NAME_224`

- 行 258: `model_name = "baseline"`
  → `model_name = os.getenv("TEST_PREDICTIONS_COMPREHENSIVE_MODEL_NAME_258")`
  → 环境变量: `TEST_PREDICTIONS_COMPREHENSIVE_MODEL_NAME_258`

- 行 267: `match_status = "finished"`
  → `match_status = os.getenv("TEST_PREDICTIONS_COMPREHENSIVE_MATCH_STATUS_267")`
  → 环境变量: `TEST_PREDICTIONS_COMPREHENSIVE_MATCH_STATUS_267`

### tests/unit/api/test_data_comprehensive.py

- 行 30: `season = "2024-25"`
  → `season = os.getenv("TEST_DATA_COMPREHENSIVE_SEASON_30")`
  → 环境变量: `TEST_DATA_COMPREHENSIVE_SEASON_30`

- 行 31: `match_status = "scheduled"`
  → `match_status = os.getenv("TEST_DATA_COMPREHENSIVE_MATCH_STATUS_31")`
  → 环境变量: `TEST_DATA_COMPREHENSIVE_MATCH_STATUS_31`

- 行 39: `team_name = "Manchester United"`
  → `team_name = os.getenv("TEST_DATA_COMPREHENSIVE_TEAM_NAME_39")`
  → 环境变量: `TEST_DATA_COMPREHENSIVE_TEAM_NAME_39`

- 行 41: `name = "Manchester United FC"`
  → `name = os.getenv("TEST_DATA_COMPREHENSIVE_NAME_41")`
  → 环境变量: `TEST_DATA_COMPREHENSIVE_NAME_41`

- 行 43: `country = "England"`
  → `country = os.getenv("TEST_DATA_COMPREHENSIVE_COUNTRY_43")`
  → 环境变量: `TEST_DATA_COMPREHENSIVE_COUNTRY_43`

- 行 44: `stadium = "Old Trafford"`
  → `stadium = os.getenv("TEST_DATA_COMPREHENSIVE_STADIUM_44")`
  → 环境变量: `TEST_DATA_COMPREHENSIVE_STADIUM_44`

- 行 49: `league_name = "Premier League"`
  → `league_name = os.getenv("TEST_DATA_COMPREHENSIVE_LEAGUE_NAME_49")`
  → 环境变量: `TEST_DATA_COMPREHENSIVE_LEAGUE_NAME_49`

- 行 50: `name = "English Premier League"`
  → `name = os.getenv("TEST_DATA_COMPREHENSIVE_NAME_50")`
  → 环境变量: `TEST_DATA_COMPREHENSIVE_NAME_50`

- 行 53: `country = "England"`
  → `country = os.getenv("TEST_DATA_COMPREHENSIVE_COUNTRY_53")`
  → 环境变量: `TEST_DATA_COMPREHENSIVE_COUNTRY_53`

- 行 62: `season = "2024-25"`
  → `season = os.getenv("TEST_DATA_COMPREHENSIVE_SEASON_62")`
  → 环境变量: `TEST_DATA_COMPREHENSIVE_SEASON_62`

- 行 65: `match_status = "scheduled"`
  → `match_status = os.getenv("TEST_DATA_COMPREHENSIVE_MATCH_STATUS_65")`
  → 环境变量: `TEST_DATA_COMPREHENSIVE_MATCH_STATUS_65`

- 行 95: `team_name = "Test Team"`
  → `team_name = os.getenv("TEST_DATA_COMPREHENSIVE_TEAM_NAME_95")`
  → 环境变量: `TEST_DATA_COMPREHENSIVE_TEAM_NAME_95`

- 行 97: `name = "Test Team FC"`
  → `name = os.getenv("TEST_DATA_COMPREHENSIVE_NAME_97")`
  → 环境变量: `TEST_DATA_COMPREHENSIVE_NAME_97`

- 行 100: `country = "Test Country"`
  → `country = os.getenv("TEST_DATA_COMPREHENSIVE_COUNTRY_100")`
  → 环境变量: `TEST_DATA_COMPREHENSIVE_COUNTRY_100`

- 行 101: `stadium = "Test Stadium"`
  → `stadium = os.getenv("TEST_DATA_COMPREHENSIVE_STADIUM_101")`
  → 环境变量: `TEST_DATA_COMPREHENSIVE_STADIUM_101`

- 行 127: `league_name = "Test League"`
  → `league_name = os.getenv("TEST_DATA_COMPREHENSIVE_LEAGUE_NAME_127")`
  → 环境变量: `TEST_DATA_COMPREHENSIVE_LEAGUE_NAME_127`

- 行 128: `country = "Test Nation"`
  → `country = os.getenv("TEST_DATA_COMPREHENSIVE_COUNTRY_128")`
  → 环境变量: `TEST_DATA_COMPREHENSIVE_COUNTRY_128`

- 行 174: `season="2024-25"`
  → `season = os.getenv("TEST_DATA_COMPREHENSIVE_SEASON_174")`
  → 环境变量: `TEST_DATA_COMPREHENSIVE_SEASON_174`

- 行 283: `country="England"`
  → `country = os.getenv("TEST_DATA_COMPREHENSIVE_COUNTRY_283")`
  → 环境变量: `TEST_DATA_COMPREHENSIVE_COUNTRY_283`

- 行 319: `feature_name = "home_win_rate"`
  → `feature_name = os.getenv("TEST_DATA_COMPREHENSIVE_FEATURE_NAME_319")`
  → 环境变量: `TEST_DATA_COMPREHENSIVE_FEATURE_NAME_319`

### tests/unit/api/test_monitoring.py

- 行 96: `metric_type="counter"`
  → `metric_type = os.getenv("TEST_MONITORING_METRIC_TYPE_96")`
  → 环境变量: `TEST_MONITORING_METRIC_TYPE_96`

- 行 102: `metric_type="histogram"`
  → `metric_type = os.getenv("TEST_MONITORING_METRIC_TYPE_102")`
  → 环境变量: `TEST_MONITORING_METRIC_TYPE_102`

- 行 341: `trace_id = "trace_12345"`
  → `trace_id = os.getenv("TEST_MONITORING_TRACE_ID_341")`
  → 环境变量: `TEST_MONITORING_TRACE_ID_341`

### tests/unit/api/test_features_improved_enhanced.py

- 行 214: `default=",
            "`
  → `default = os.getenv("TEST_FEATURES_IMPROVED_ENHANCED_DEFAULT_214")`
  → 环境变量: `TEST_FEATURES_IMPROVED_ENHANCED_DEFAULT_214`

### tests/unit/api/test_models_comprehensive.py

- 行 24: `name = "football_prediction_v1"`
  → `name = os.getenv("TEST_MODELS_COMPREHENSIVE_NAME_24")`
  → 环境变量: `TEST_MODELS_COMPREHENSIVE_NAME_24`

- 行 24: `description = "足球预测模型"`
  → `description = os.getenv("TEST_MODELS_COMPREHENSIVE_DESCRIPTION_24")`
  → 环境变量: `TEST_MODELS_COMPREHENSIVE_DESCRIPTION_24`

- 行 32: `name = "football_prediction_v1"`
  → `name = os.getenv("TEST_MODELS_COMPREHENSIVE_NAME_32")`
  → 环境变量: `TEST_MODELS_COMPREHENSIVE_NAME_32`

- 行 38: `run_id = "run_123"`
  → `run_id = os.getenv("TEST_MODELS_COMPREHENSIVE_RUN_ID_38")`
  → 环境变量: `TEST_MODELS_COMPREHENSIVE_RUN_ID_38`

- 行 151: `name = "model_1"`
  → `name = os.getenv("TEST_MODELS_COMPREHENSIVE_NAME_151")`
  → 环境变量: `TEST_MODELS_COMPREHENSIVE_NAME_151`

- 行 155: `name = "model_2"`
  → `name = os.getenv("TEST_MODELS_COMPREHENSIVE_NAME_155")`
  → 环境变量: `TEST_MODELS_COMPREHENSIVE_NAME_155`

### tests/unit/api/test_data_api.py

- 行 28: `value = "finished"`
  → `value = os.getenv("TEST_DATA_API_VALUE_28")`
  → 环境变量: `TEST_DATA_API_VALUE_28`

- 行 64: `team_name = "Test Team"`
  → `team_name = os.getenv("TEST_DATA_API_TEAM_NAME_64")`
  → 环境变量: `TEST_DATA_API_TEAM_NAME_64`

- 行 67: `country = "Test Country"`
  → `country = os.getenv("TEST_DATA_API_COUNTRY_67")`
  → 环境变量: `TEST_DATA_API_COUNTRY_67`

- 行 68: `stadium = "Test Stadium"`
  → `stadium = os.getenv("TEST_DATA_API_STADIUM_68")`
  → 环境变量: `TEST_DATA_API_STADIUM_68`

- 行 97: `league_name = "Test League"`
  → `league_name = os.getenv("TEST_DATA_API_LEAGUE_NAME_97")`
  → 环境变量: `TEST_DATA_API_LEAGUE_NAME_97`

- 行 99: `country = "Test Country"`
  → `country = os.getenv("TEST_DATA_API_COUNTRY_99")`
  → 环境变量: `TEST_DATA_API_COUNTRY_99`

- 行 209: `team_name = "Test Team"`
  → `team_name = os.getenv("TEST_DATA_API_TEAM_NAME_209")`
  → 环境变量: `TEST_DATA_API_TEAM_NAME_209`

- 行 228: `team_name = "Test Team"`
  → `team_name = os.getenv("TEST_DATA_API_TEAM_NAME_228")`
  → 环境变量: `TEST_DATA_API_TEAM_NAME_228`

- 行 306: `league_name = "Test League"`
  → `league_name = os.getenv("TEST_DATA_API_LEAGUE_NAME_306")`
  → 环境变量: `TEST_DATA_API_LEAGUE_NAME_306`

- 行 325: `league_name = "Test League"`
  → `league_name = os.getenv("TEST_DATA_API_LEAGUE_NAME_325")`
  → 环境变量: `TEST_DATA_API_LEAGUE_NAME_325`

### tests/unit/api/test_cache_api_endpoints.py

- 行 156: `pattern="test:*"`
  → `pattern = os.getenv("TEST_CACHE_API_ENDPOINTS_PATTERN_156")`
  → 环境变量: `TEST_CACHE_API_ENDPOINTS_PATTERN_156`

- 行 394: `pattern="test:*"`
  → `pattern = os.getenv("TEST_CACHE_API_ENDPOINTS_PATTERN_394")`
  → 环境变量: `TEST_CACHE_API_ENDPOINTS_PATTERN_394`

### tests/unit/api/test_health.py

- 行 41: `return_value = "Connection timeout"`
  → `return_value = os.getenv("TEST_HEALTH_RETURN_VALUE_41")`
  → 环境变量: `TEST_HEALTH_RETURN_VALUE_41`

- 行 74: `return_value = "abc123"`
  → `return_value = os.getenv("TEST_HEALTH_RETURN_VALUE_74")`
  → 环境变量: `TEST_HEALTH_RETURN_VALUE_74`

### tests/unit/api/test_buggy_api_enhanced.py

- 行 93: `default=",
            "`
  → `default = os.getenv("TEST_BUGGY_API_ENHANCED_DEFAULT_93")`
  → 环境变量: `TEST_BUGGY_API_ENHANCED_DEFAULT_93`

- 行 94: `description="
        }

        found_validations = []
        for validation, pattern in query_validations.items():
            if pattern in content:
                found_validations.append(validation)

        coverage_rate = len(found_validations) / len(query_validations) * 100
        print(f"`
  → `description = os.getenv("TEST_BUGGY_API_ENHANCED_DESCRIPTION_94")`
  → 环境变量: `TEST_BUGGY_API_ENHANCED_DESCRIPTION_94`

- 行 205: `default=",
            "`
  → `default = os.getenv("TEST_BUGGY_API_ENHANCED_DEFAULT_205")`
  → 环境变量: `TEST_BUGGY_API_ENHANCED_DEFAULT_205`

- 行 251: `default=",
            "`
  → `default = os.getenv("TEST_BUGGY_API_ENHANCED_DEFAULT_251")`
  → 环境变量: `TEST_BUGGY_API_ENHANCED_DEFAULT_251`

- 行 255: `description=",
            "`
  → `description = os.getenv("TEST_BUGGY_API_ENHANCED_DESCRIPTION_255")`
  → 环境变量: `TEST_BUGGY_API_ENHANCED_DESCRIPTION_255`

- 行 300: `return_value="mocked_status"`
  → `return_value = os.getenv("TEST_BUGGY_API_ENHANCED_RETURN_VALUE_300")`
  → 环境变量: `TEST_BUGGY_API_ENHANCED_RETURN_VALUE_300`

- 行 355: `description=",
            "`
  → `description = os.getenv("TEST_BUGGY_API_ENHANCED_DESCRIPTION_355")`
  → 环境变量: `TEST_BUGGY_API_ENHANCED_DESCRIPTION_355`

### tests/unit/api/test_models.py

- 行 29: `SCHEDULED = "scheduled"`
  → `SCHEDULED = os.getenv("TEST_MODELS_SCHEDULED_29")`
  → 环境变量: `TEST_MODELS_SCHEDULED_29`

- 行 30: `FINISHED = "finished"`
  → `FINISHED = os.getenv("TEST_MODELS_FINISHED_30")`
  → 环境变量: `TEST_MODELS_FINISHED_30`

- 行 31: `CANCELLED = "cancelled"`
  → `CANCELLED = os.getenv("TEST_MODELS_CANCELLED_31")`
  → 环境变量: `TEST_MODELS_CANCELLED_31`

- 行 32: `HOME_WIN = "home_win"`
  → `HOME_WIN = os.getenv("TEST_MODELS_HOME_WIN_32")`
  → 环境变量: `TEST_MODELS_HOME_WIN_32`

- 行 34: `AWAY_WIN = "away_win"`
  → `AWAY_WIN = os.getenv("TEST_MODELS_AWAY_WIN_34")`
  → 环境变量: `TEST_MODELS_AWAY_WIN_34`

- 行 81: `reason="Models not available"`
  → `reason = os.getenv("TEST_MODELS_REASON_81")`
  → 环境变量: `TEST_MODELS_REASON_81`

- 行 204: `reason="Models not available"`
  → `reason = os.getenv("TEST_MODELS_REASON_204")`
  → 环境变量: `TEST_MODELS_REASON_204`

- 行 269: `reason="Models not available"`
  → `reason = os.getenv("TEST_MODELS_REASON_269")`
  → 环境变量: `TEST_MODELS_REASON_269`

- 行 374: `reason="Models not available"`
  → `reason = os.getenv("TEST_MODELS_REASON_374")`
  → 环境变量: `TEST_MODELS_REASON_374`

- 行 425: `reason="Models not available"`
  → `reason = os.getenv("TEST_MODELS_REASON_425")`
  → 环境变量: `TEST_MODELS_REASON_425`

- 行 480: `reason="Models not available"`
  → `reason = os.getenv("TEST_MODELS_REASON_480")`
  → 环境变量: `TEST_MODELS_REASON_480`

- 行 584: `id="invalid"`
  → `id = os.getenv("TEST_MODELS_ID_584")`
  → 环境变量: `TEST_MODELS_ID_584`

- 行 601: `match_date="invalid_date"`
  → `match_date = os.getenv("TEST_MODELS_MATCH_DATE_601")`
  → 环境变量: `TEST_MODELS_MATCH_DATE_601`

### tests/unit/api/test_cache_api_complete.py

- 行 75: `pattern="test:*"`
  → `pattern = os.getenv("TEST_CACHE_API_COMPLETE_PATTERN_75")`
  → 环境变量: `TEST_CACHE_API_COMPLETE_PATTERN_75`

- 行 178: `pattern="test:*"`
  → `pattern = os.getenv("TEST_CACHE_API_COMPLETE_PATTERN_178")`
  → 环境变量: `TEST_CACHE_API_COMPLETE_PATTERN_178`

- 行 235: `pattern="temp:*"`
  → `pattern = os.getenv("TEST_CACHE_API_COMPLETE_PATTERN_235")`
  → 环境变量: `TEST_CACHE_API_COMPLETE_PATTERN_235`

- 行 686: `pattern="*:special:*"`
  → `pattern = os.getenv("TEST_CACHE_API_COMPLETE_PATTERN_686")`
  → 环境变量: `TEST_CACHE_API_COMPLETE_PATTERN_686`

### tests/unit/api/test_predictions_enhanced.py

- 行 219: `ge=",
            "`
  → `ge = os.getenv("TEST_PREDICTIONS_ENHANCED_GE_219")`
  → 环境变量: `TEST_PREDICTIONS_ENHANCED_GE_219`

- 行 219: `le=",
            "`
  → `le = os.getenv("TEST_PREDICTIONS_ENHANCED_LE_219")`
  → 环境变量: `TEST_PREDICTIONS_ENHANCED_LE_219`

- 行 219: `default=",
            "`
  → `default = os.getenv("TEST_PREDICTIONS_ENHANCED_DEFAULT_219")`
  → 环境变量: `TEST_PREDICTIONS_ENHANCED_DEFAULT_219`

- 行 219: `description="
        }

        found_validations = []
        for validation, pattern in param_validations.items():
            if pattern in content:
                found_validations.append(validation)

        coverage_rate = len(found_validations) / len(param_validations) * 100
        print(f"`
  → `description = os.getenv("TEST_PREDICTIONS_ENHANCED_DESCRIPTION_219")`
  → 环境变量: `TEST_PREDICTIONS_ENHANCED_DESCRIPTION_219`

### tests/unit/api/test_data.py

- 行 138: `status="finished"`
  → `status = os.getenv("TEST_DATA_STATUS_138")`
  → 环境变量: `TEST_DATA_STATUS_138`

### tests/unit/api/test_predictions.py

- 行 131: `prediction="invalid_prediction"`
  → `prediction = os.getenv("TEST_PREDICTIONS_PREDICTION_131")`
  → 环境变量: `TEST_PREDICTIONS_PREDICTION_131`

### tests/unit/utils/test_i18n.py

- 行 118: `accept_language = "fr-FR,en-US;q=0.9,zh-CN;q=0.8"`
  → `accept_language = os.getenv("TEST_I18N_ACCEPT_LANGUAGE_118")`
  → 环境变量: `TEST_I18N_ACCEPT_LANGUAGE_118`

- 行 124: `accept_language = "en-US;q=0.9,zh-CN;q=0.8"`
  → `accept_language = os.getenv("TEST_I18N_ACCEPT_LANGUAGE_124")`
  → 环境变量: `TEST_I18N_ACCEPT_LANGUAGE_124`

### tests/unit/utils/test_crypto_utils.py

- 行 73: `text = "test string"`
  → `text = os.getenv("TEST_CRYPTO_UTILS_TEXT_73")`
  → 环境变量: `TEST_CRYPTO_UTILS_TEXT_73`

- 行 92: `text = "test string"`
  → `text = os.getenv("TEST_CRYPTO_UTILS_TEXT_92")`
  → 环境变量: `TEST_CRYPTO_UTILS_TEXT_92`

- 行 108: `match="不支持的哈希算法"`
  → `match = os.getenv("TEST_CRYPTO_UTILS_MATCH_108")`
  → 环境变量: `TEST_CRYPTO_UTILS_MATCH_108`

- 行 110: `match="不支持的哈希算法"`
  → `match = os.getenv("TEST_CRYPTO_UTILS_MATCH_110")`
  → 环境变量: `TEST_CRYPTO_UTILS_MATCH_110`

- 行 113: `password = "my_secure_password"`
  → `password = os.getenv("TEST_CRYPTO_UTILS_PASSWORD_113")`
  → 环境变量: `TEST_CRYPTO_UTILS_PASSWORD_113`

- 行 130: `password = "my_password"`
  → `password = os.getenv("TEST_CRYPTO_UTILS_PASSWORD_130")`
  → 环境变量: `TEST_CRYPTO_UTILS_PASSWORD_130`

- 行 131: `salt = "custom_salt"`
  → `salt = os.getenv("TEST_CRYPTO_UTILS_SALT_131")`
  → 环境变量: `TEST_CRYPTO_UTILS_SALT_131`

- 行 138: `password = "test_password"`
  → `password = os.getenv("TEST_CRYPTO_UTILS_PASSWORD_138")`
  → 环境变量: `TEST_CRYPTO_UTILS_PASSWORD_138`

- 行 147: `password = "test_password"`
  → `password = os.getenv("TEST_CRYPTO_UTILS_PASSWORD_147")`
  → 环境变量: `TEST_CRYPTO_UTILS_PASSWORD_147`

- 行 148: `wrong_password = "wrong_password"`
  → `wrong_password = os.getenv("TEST_CRYPTO_UTILS_WRONG_PASSWORD_148")`
  → 环境变量: `TEST_CRYPTO_UTILS_WRONG_PASSWORD_148`

- 行 167: `invalid_hash = "invalid_hash_format"`
  → `invalid_hash = os.getenv("TEST_CRYPTO_UTILS_INVALID_HASH_167")`
  → 环境变量: `TEST_CRYPTO_UTILS_INVALID_HASH_167`

- 行 215: `password = "test_password_123"`
  → `password = os.getenv("TEST_CRYPTO_UTILS_PASSWORD_215")`
  → 环境变量: `TEST_CRYPTO_UTILS_PASSWORD_215`

- 行 229: `unicode_password = "密码🔒123"`
  → `unicode_password = os.getenv("TEST_CRYPTO_UTILS_UNICODE_PASSWORD_229")`
  → 环境变量: `TEST_CRYPTO_UTILS_UNICODE_PASSWORD_229`

- 行 271: `text1 = "hello world"`
  → `text1 = os.getenv("TEST_CRYPTO_UTILS_TEXT1_271")`
  → 环境变量: `TEST_CRYPTO_UTILS_TEXT1_271`

- 行 273: `text2 = "hello  world"`
  → `text2 = os.getenv("TEST_CRYPTO_UTILS_TEXT2_273")`
  → 环境变量: `TEST_CRYPTO_UTILS_TEXT2_273`

- 行 274: `text3 = "hello world "`
  → `text3 = os.getenv("TEST_CRYPTO_UTILS_TEXT3_274")`
  → 环境变量: `TEST_CRYPTO_UTILS_TEXT3_274`

- 行 309: `special_chars = "!@#$%^&*()_+-=[]{}|;'`
  → `special_chars = os.getenv("TEST_CRYPTO_UTILS_SPECIAL_CHARS_309")`
  → 环境变量: `TEST_CRYPTO_UTILS_SPECIAL_CHARS_309`

- 行 317: `text_with_newlines = "line1\nline2\nline3"`
  → `text_with_newlines = os.getenv("TEST_CRYPTO_UTILS_TEXT_WITH_NEWLINES_317")`
  → 环境变量: `TEST_CRYPTO_UTILS_TEXT_WITH_NEWLINES_317`

- 行 318: `text_with_tabs = "col1\tcol2\tcol3"`
  → `text_with_tabs = os.getenv("TEST_CRYPTO_UTILS_TEXT_WITH_TABS_318")`
  → 环境变量: `TEST_CRYPTO_UTILS_TEXT_WITH_TABS_318`

### tests/unit/utils/test_crypto_utils_complete.py

- 行 22: `password = "my_secure_password"`
  → `password = os.getenv("TEST_CRYPTO_UTILS_COMPLETE_PASSWORD_22")`
  → 环境变量: `TEST_CRYPTO_UTILS_COMPLETE_PASSWORD_22`

- 行 39: `password = "test_password"`
  → `password = os.getenv("TEST_CRYPTO_UTILS_COMPLETE_PASSWORD_39")`
  → 环境变量: `TEST_CRYPTO_UTILS_COMPLETE_PASSWORD_39`

- 行 41: `salt = "testsalt"`
  → `salt = os.getenv("TEST_CRYPTO_UTILS_COMPLETE_SALT_41")`
  → 环境变量: `TEST_CRYPTO_UTILS_COMPLETE_SALT_41`

- 行 86: `match="不支持的哈希算法"`
  → `match = os.getenv("TEST_CRYPTO_UTILS_COMPLETE_MATCH_86")`
  → 环境变量: `TEST_CRYPTO_UTILS_COMPLETE_MATCH_86`

- 行 120: `password = "password123"`
  → `password = os.getenv("TEST_CRYPTO_UTILS_COMPLETE_PASSWORD_120")`
  → 环境变量: `TEST_CRYPTO_UTILS_COMPLETE_PASSWORD_120`

- 行 159: `test_string = "consistency_test"`
  → `test_string = os.getenv("TEST_CRYPTO_UTILS_COMPLETE_TEST_STRING_159")`
  → 环境变量: `TEST_CRYPTO_UTILS_COMPLETE_TEST_STRING_159`

- 行 189: `password_str = "test_password"`
  → `password_str = os.getenv("TEST_CRYPTO_UTILS_COMPLETE_PASSWORD_STR_189")`
  → 环境变量: `TEST_CRYPTO_UTILS_COMPLETE_PASSWORD_STR_189`

- 行 204: `password = "correct_password"`
  → `password = os.getenv("TEST_CRYPTO_UTILS_COMPLETE_PASSWORD_204")`
  → 环境变量: `TEST_CRYPTO_UTILS_COMPLETE_PASSWORD_204`

- 行 205: `wrong_password = "wrong_password"`
  → `wrong_password = os.getenv("TEST_CRYPTO_UTILS_COMPLETE_WRONG_PASSWORD_205")`
  → 环境变量: `TEST_CRYPTO_UTILS_COMPLETE_WRONG_PASSWORD_205`

- 行 245: `password = "sensitive_password_123!"`
  → `password = os.getenv("TEST_CRYPTO_UTILS_COMPLETE_PASSWORD_245")`
  → 环境变量: `TEST_CRYPTO_UTILS_COMPLETE_PASSWORD_245`

### tests/unit/utils/test_mlflow_security.py

- 行 129: `match="模型签名验证失败"`
  → `match = os.getenv("TEST_MLFLOW_SECURITY_MATCH_129")`
  → 环境变量: `TEST_MLFLOW_SECURITY_MATCH_129`

- 行 151: `match="加载的对象不是有效的模型"`
  → `match = os.getenv("TEST_MLFLOW_SECURITY_MATCH_151")`
  → 环境变量: `TEST_MLFLOW_SECURITY_MATCH_151`

- 行 159: `match="模型加载失败"`
  → `match = os.getenv("TEST_MLFLOW_SECURITY_MATCH_159")`
  → 环境变量: `TEST_MLFLOW_SECURITY_MATCH_159`

- 行 292: `match="无效的模型对象"`
  → `match = os.getenv("TEST_MLFLOW_SECURITY_MATCH_292")`
  → 环境变量: `TEST_MLFLOW_SECURITY_MATCH_292`

- 行 299: `match="无效的模型路径"`
  → `match = os.getenv("TEST_MLFLOW_SECURITY_MATCH_299")`
  → 环境变量: `TEST_MLFLOW_SECURITY_MATCH_299`

- 行 304: `match="无效的模型路径"`
  → `match = os.getenv("TEST_MLFLOW_SECURITY_MATCH_304")`
  → 环境变量: `TEST_MLFLOW_SECURITY_MATCH_304`

- 行 312: `registered_model_name="test_model"`
  → `registered_model_name = os.getenv("TEST_MLFLOW_SECURITY_REGISTERED_MODEL_NAME_312")`
  → 环境变量: `TEST_MLFLOW_SECURITY_REGISTERED_MODEL_NAME_312`

- 行 314: `signature="test_signature"`
  → `signature = os.getenv("TEST_MLFLOW_SECURITY_SIGNATURE_314")`
  → 环境变量: `TEST_MLFLOW_SECURITY_SIGNATURE_314`

- 行 315: `extra_param="should_be_ignored"`
  → `extra_param = os.getenv("TEST_MLFLOW_SECURITY_EXTRA_PARAM_315")`
  → 环境变量: `TEST_MLFLOW_SECURITY_EXTRA_PARAM_315`

### tests/unit/utils/test_response.py

- 行 18: `code="SUCCESS"`
  → `code = os.getenv("TEST_RESPONSE_CODE_18")`
  → 环境变量: `TEST_RESPONSE_CODE_18`

- 行 77: `message="自定义成功消息"`
  → `message = os.getenv("TEST_RESPONSE_MESSAGE_77")`
  → 环境变量: `TEST_RESPONSE_MESSAGE_77`

- 行 152: `code="INVALID_INPUT"`
  → `code = os.getenv("TEST_RESPONSE_CODE_152")`
  → 环境变量: `TEST_RESPONSE_CODE_152`

- 行 250: `message="服务器内部错误"`
  → `message = os.getenv("TEST_RESPONSE_MESSAGE_250")`
  → 环境变量: `TEST_RESPONSE_MESSAGE_250`

### tests/unit/utils/test_mlflow_security_simple.py

- 行 113: `match="模型签名验证失败"`
  → `match = os.getenv("TEST_MLFLOW_SECURITY_SIMPLE_MATCH_113")`
  → 环境变量: `TEST_MLFLOW_SECURITY_SIMPLE_MATCH_113`

- 行 187: `match="无效的模型对象"`
  → `match = os.getenv("TEST_MLFLOW_SECURITY_SIMPLE_MATCH_187")`
  → 环境变量: `TEST_MLFLOW_SECURITY_SIMPLE_MATCH_187`

- 行 194: `match="无效的模型路径"`
  → `match = os.getenv("TEST_MLFLOW_SECURITY_SIMPLE_MATCH_194")`
  → 环境变量: `TEST_MLFLOW_SECURITY_SIMPLE_MATCH_194`

- 行 197: `match="无效的模型路径"`
  → `match = os.getenv("TEST_MLFLOW_SECURITY_SIMPLE_MATCH_197")`
  → 环境变量: `TEST_MLFLOW_SECURITY_SIMPLE_MATCH_197`

### tests/unit/utils/test_crypto_utils_enhanced.py

- 行 155: `test_data = "test message"`
  → `test_data = os.getenv("TEST_CRYPTO_UTILS_ENHANCED_TEST_DATA_155")`
  → 环境变量: `TEST_CRYPTO_UTILS_ENHANCED_TEST_DATA_155`

- 行 177: `test_data = "test message"`
  → `test_data = os.getenv("TEST_CRYPTO_UTILS_ENHANCED_TEST_DATA_177")`
  → 环境变量: `TEST_CRYPTO_UTILS_ENHANCED_TEST_DATA_177`

- 行 203: `test_data = "Hello, World! 你好世界"`
  → `test_data = os.getenv("TEST_CRYPTO_UTILS_ENHANCED_TEST_DATA_203")`
  → 环境变量: `TEST_CRYPTO_UTILS_ENHANCED_TEST_DATA_203`

- 行 246: `password = "my_secure_password"`
  → `password = os.getenv("TEST_CRYPTO_UTILS_ENHANCED_PASSWORD_246")`
  → 环境变量: `TEST_CRYPTO_UTILS_ENHANCED_PASSWORD_246`

- 行 254: `different_password = "different_password"`
  → `different_password = os.getenv("TEST_CRYPTO_UTILS_ENHANCED_DIFFERENT_PASSWORD_254")`
  → 环境变量: `TEST_CRYPTO_UTILS_ENHANCED_DIFFERENT_PASSWORD_254`

- 行 263: `data = "secret message"`
  → `data = os.getenv("TEST_CRYPTO_UTILS_ENHANCED_DATA_263")`
  → 环境变量: `TEST_CRYPTO_UTILS_ENHANCED_DATA_263`

- 行 300: `data = "important data"`
  → `data = os.getenv("TEST_CRYPTO_UTILS_ENHANCED_DATA_300")`
  → 环境变量: `TEST_CRYPTO_UTILS_ENHANCED_DATA_300`

- 行 302: `received_data = "important data"`
  → `received_data = os.getenv("TEST_CRYPTO_UTILS_ENHANCED_RECEIVED_DATA_302")`
  → 环境变量: `TEST_CRYPTO_UTILS_ENHANCED_RECEIVED_DATA_302`

- 行 308: `modified_data = "important data modified"`
  → `modified_data = os.getenv("TEST_CRYPTO_UTILS_ENHANCED_MODIFIED_DATA_308")`
  → 环境变量: `TEST_CRYPTO_UTILS_ENHANCED_MODIFIED_DATA_308`

- 行 316: `password = "user_password"`
  → `password = os.getenv("TEST_CRYPTO_UTILS_ENHANCED_PASSWORD_316")`
  → 环境变量: `TEST_CRYPTO_UTILS_ENHANCED_PASSWORD_316`

- 行 317: `salt = "random_salt"`
  → `salt = os.getenv("TEST_CRYPTO_UTILS_ENHANCED_SALT_317")`
  → 环境变量: `TEST_CRYPTO_UTILS_ENHANCED_SALT_317`

- 行 371: `data = "test data"`
  → `data = os.getenv("TEST_CRYPTO_UTILS_ENHANCED_DATA_371")`
  → 环境变量: `TEST_CRYPTO_UTILS_ENHANCED_DATA_371`

- 行 404: `sensitive_data = "user secret information"`
  → `sensitive_data = os.getenv("TEST_CRYPTO_UTILS_ENHANCED_SENSITIVE_DATA_404")`
  → 环境变量: `TEST_CRYPTO_UTILS_ENHANCED_SENSITIVE_DATA_404`

- 行 428: `original = "password123"`
  → `original = os.getenv("TEST_CRYPTO_UTILS_ENHANCED_ORIGINAL_428")`
  → 环境变量: `TEST_CRYPTO_UTILS_ENHANCED_ORIGINAL_428`

- 行 434: `similar1 = "password123"`
  → `similar1 = os.getenv("TEST_CRYPTO_UTILS_ENHANCED_SIMILAR1_434")`
  → 环境变量: `TEST_CRYPTO_UTILS_ENHANCED_SIMILAR1_434`

- 行 436: `similar2 = "password124"`
  → `similar2 = os.getenv("TEST_CRYPTO_UTILS_ENHANCED_SIMILAR2_436")`
  → 环境变量: `TEST_CRYPTO_UTILS_ENHANCED_SIMILAR2_436`

### tests/unit/monitoring/test_alert_manager_simple.py

- 行 28: `title="Test Alert"`
  → `title = os.getenv("TEST_ALERT_MANAGER_SIMPLE_TITLE_28")`
  → 环境变量: `TEST_ALERT_MANAGER_SIMPLE_TITLE_28`

- 行 28: `message="This is a test"`
  → `message = os.getenv("TEST_ALERT_MANAGER_SIMPLE_MESSAGE_28")`
  → 环境变量: `TEST_ALERT_MANAGER_SIMPLE_MESSAGE_28`

- 行 29: `source="test_source"`
  → `source = os.getenv("TEST_ALERT_MANAGER_SIMPLE_SOURCE_29")`
  → 环境变量: `TEST_ALERT_MANAGER_SIMPLE_SOURCE_29`

- 行 42: `title="CPU High"`
  → `title = os.getenv("TEST_ALERT_MANAGER_SIMPLE_TITLE_42")`
  → 环境变量: `TEST_ALERT_MANAGER_SIMPLE_TITLE_42`

- 行 43: `message="CPU usage is high"`
  → `message = os.getenv("TEST_ALERT_MANAGER_SIMPLE_MESSAGE_43")`
  → 环境变量: `TEST_ALERT_MANAGER_SIMPLE_MESSAGE_43`

- 行 45: `source="monitor"`
  → `source = os.getenv("TEST_ALERT_MANAGER_SIMPLE_SOURCE_45")`
  → 环境变量: `TEST_ALERT_MANAGER_SIMPLE_SOURCE_45`

- 行 77: `title="Test Alert"`
  → `title = os.getenv("TEST_ALERT_MANAGER_SIMPLE_TITLE_77")`
  → 环境变量: `TEST_ALERT_MANAGER_SIMPLE_TITLE_77`

- 行 130: `rule_id="test_rule"`
  → `rule_id = os.getenv("TEST_ALERT_MANAGER_SIMPLE_RULE_ID_130")`
  → 环境变量: `TEST_ALERT_MANAGER_SIMPLE_RULE_ID_130`

- 行 131: `name="Test Rule"`
  → `name = os.getenv("TEST_ALERT_MANAGER_SIMPLE_NAME_131")`
  → 环境变量: `TEST_ALERT_MANAGER_SIMPLE_NAME_131`

- 行 132: `condition="test > 100"`
  → `condition = os.getenv("TEST_ALERT_MANAGER_SIMPLE_CONDITION_132")`
  → 环境变量: `TEST_ALERT_MANAGER_SIMPLE_CONDITION_132`

- 行 146: `rule_id = "data_freshness_warning"`
  → `rule_id = os.getenv("TEST_ALERT_MANAGER_SIMPLE_RULE_ID_146")`
  → 环境变量: `TEST_ALERT_MANAGER_SIMPLE_RULE_ID_146`

- 行 150: `message="Test message"`
  → `message = os.getenv("TEST_ALERT_MANAGER_SIMPLE_MESSAGE_150")`
  → 环境变量: `TEST_ALERT_MANAGER_SIMPLE_MESSAGE_150`

- 行 158: `message="Test message"`
  → `message = os.getenv("TEST_ALERT_MANAGER_SIMPLE_MESSAGE_158")`
  → 环境变量: `TEST_ALERT_MANAGER_SIMPLE_MESSAGE_158`

### tests/unit/monitoring/test_system_monitor_simple.py

- 行 127: `return_value = "test_process"`
  → `return_value = os.getenv("TEST_SYSTEM_MONITOR_SIMPLE_RETURN_VALUE_127")`
  → 环境变量: `TEST_SYSTEM_MONITOR_SIMPLE_RETURN_VALUE_127`

### tests/unit/models/test_prediction_service_comprehensive.py

- 行 77: `model_name="football_predictor_v1"`
  → `model_name = os.getenv("TEST_PREDICTION_SERVICE_COMPREHENSIVE_MODEL_NAME_7")`
  → 环境变量: `TEST_PREDICTION_SERVICE_COMPREHENSIVE_MODEL_NAME_7`

- 行 105: `status = "finished"`
  → `status = os.getenv("TEST_PREDICTION_SERVICE_COMPREHENSIVE_STATUS_105")`
  → 环境变量: `TEST_PREDICTION_SERVICE_COMPREHENSIVE_STATUS_105`

- 行 372: `model_name = "test_model"`
  → `model_name = os.getenv("TEST_PREDICTION_SERVICE_COMPREHENSIVE_MODEL_NAME_3")`
  → 环境变量: `TEST_PREDICTION_SERVICE_COMPREHENSIVE_MODEL_NAME_3`

- 行 616: `batch_id = "batch_12345"`
  → `batch_id = os.getenv("TEST_PREDICTION_SERVICE_COMPREHENSIVE_BATCH_ID_616")`
  → 环境变量: `TEST_PREDICTION_SERVICE_COMPREHENSIVE_BATCH_ID_616`

### tests/unit/middleware/test_security.py

- 行 27: `key = "test_key"`
  → `key = os.getenv("TEST_SECURITY_KEY_27")`
  → 环境变量: `TEST_SECURITY_KEY_27`

- 行 35: `key = "test_key"`
  → `key = os.getenv("TEST_SECURITY_KEY_35")`
  → 环境变量: `TEST_SECURITY_KEY_35`

- 行 47: `key = "test_key"`
  → `key = os.getenv("TEST_SECURITY_KEY_47")`
  → 环境变量: `TEST_SECURITY_KEY_47`

- 行 228: `input_str = "  test input  "`
  → `input_str = os.getenv("TEST_SECURITY_INPUT_STR_228")`
  → 环境变量: `TEST_SECURITY_INPUT_STR_228`

- 行 231: `input_str = "user@example.com"`
  → `input_str = os.getenv("TEST_SECURITY_INPUT_STR_231")`
  → 环境变量: `TEST_SECURITY_INPUT_STR_231`

### tests/unit/middleware/test_performance.py

- 行 105: `query = "match_id=12345"`
  → `query = os.getenv("TEST_PERFORMANCE_QUERY_105")`
  → 环境变量: `TEST_PERFORMANCE_QUERY_105`

### tests/unit/database/test_optimization.py

- 行 50: `query = "SELECT * FROM predictions WHERE match_id = $1"`
  → `query = os.getenv("TEST_OPTIMIZATION_QUERY_50")`
  → 环境变量: `TEST_OPTIMIZATION_QUERY_50`

- 行 128: `schemaname = "public"`
  → `schemaname = os.getenv("TEST_OPTIMIZATION_SCHEMANAME_128")`
  → 环境变量: `TEST_OPTIMIZATION_SCHEMANAME_128`

- 行 128: `relname = "idx_predictions_match_model"`
  → `relname = os.getenv("TEST_OPTIMIZATION_RELNAME_128")`
  → 环境变量: `TEST_OPTIMIZATION_RELNAME_128`

- 行 138: `schemaname = "public"`
  → `schemaname = os.getenv("TEST_OPTIMIZATION_SCHEMANAME_138")`
  → 环境变量: `TEST_OPTIMIZATION_SCHEMANAME_138`

- 行 139: `relname = "predictions"`
  → `relname = os.getenv("TEST_OPTIMIZATION_RELNAME_139")`
  → 环境变量: `TEST_OPTIMIZATION_RELNAME_139`

- 行 207: `datname = "football_prediction"`
  → `datname = os.getenv("TEST_OPTIMIZATION_DATNAME_207")`
  → 环境变量: `TEST_OPTIMIZATION_DATNAME_207`

- 行 296: `query = "SELECT * FROM matches ORDER BY id"`
  → `query = os.getenv("TEST_OPTIMIZATION_QUERY_296")`
  → 环境变量: `TEST_OPTIMIZATION_QUERY_296`

- 行 305: `query = "SELECT * FROM matches ORDER BY id"`
  → `query = os.getenv("TEST_OPTIMIZATION_QUERY_305")`
  → 环境变量: `TEST_OPTIMIZATION_QUERY_305`

- 行 313: `query = "SELECT * FROM matches WHERE date > '`
  → `query = os.getenv("TEST_OPTIMIZATION_QUERY_313")`
  → 环境变量: `TEST_OPTIMIZATION_QUERY_313`

- 行 322: `query = "SELECT * FROM matches"`
  → `query = os.getenv("TEST_OPTIMIZATION_QUERY_322")`
  → 环境变量: `TEST_OPTIMIZATION_QUERY_322`

- 行 327: `table_name = "predictions"`
  → `table_name = os.getenv("TEST_OPTIMIZATION_TABLE_NAME_327")`
  → 环境变量: `TEST_OPTIMIZATION_TABLE_NAME_327`

- 行 342: `table_name = "predictions"`
  → `table_name = os.getenv("TEST_OPTIMIZATION_TABLE_NAME_342")`
  → 环境变量: `TEST_OPTIMIZATION_TABLE_NAME_342`

- 行 413: `cache_key = "db_stats:2023-10-03"`
  → `cache_key = os.getenv("TEST_OPTIMIZATION_CACHE_KEY_413")`
  → 环境变量: `TEST_OPTIMIZATION_CACHE_KEY_413`

### tests/unit/database/test_connection_extended.py

- 行 38: `test_url = "sqlite+aiosqlite:///test.db"`
  → `test_url = os.getenv("TEST_CONNECTION_EXTENDED_TEST_URL_38")`
  → 环境变量: `TEST_CONNECTION_EXTENDED_TEST_URL_38`

### tests/unit/database/test_connection_simple.py

- 行 46: `driver="sqlite"`
  → `driver = os.getenv("TEST_CONNECTION_SIMPLE_DRIVER_46")`
  → 环境变量: `TEST_CONNECTION_SIMPLE_DRIVER_46`

- 行 53: `driver="postgresql"`
  → `driver = os.getenv("TEST_CONNECTION_SIMPLE_DRIVER_53")`
  → 环境变量: `TEST_CONNECTION_SIMPLE_DRIVER_53`

- 行 56: `database="testdb"`
  → `database = os.getenv("TEST_CONNECTION_SIMPLE_DATABASE_56")`
  → 环境变量: `TEST_CONNECTION_SIMPLE_DATABASE_56`

- 行 67: `database_url="sqlite:///./test.db"`
  → `database_url = os.getenv("TEST_CONNECTION_SIMPLE_DATABASE_URL_67")`
  → 环境变量: `TEST_CONNECTION_SIMPLE_DATABASE_URL_67`

- 行 81: `database_url="sqlite:///./test.db"`
  → `database_url = os.getenv("TEST_CONNECTION_SIMPLE_DATABASE_URL_81")`
  → 环境变量: `TEST_CONNECTION_SIMPLE_DATABASE_URL_81`

- 行 87: `database_url="sqlite+aiosqlite:///./test.db"`
  → `database_url = os.getenv("TEST_CONNECTION_SIMPLE_DATABASE_URL_87")`
  → 环境变量: `TEST_CONNECTION_SIMPLE_DATABASE_URL_87`

- 行 130: `database_url="sqlite:///./test.db"`
  → `database_url = os.getenv("TEST_CONNECTION_SIMPLE_DATABASE_URL_130")`
  → 环境变量: `TEST_CONNECTION_SIMPLE_DATABASE_URL_130`

- 行 143: `database_url="sqlite:///./test.db"`
  → `database_url = os.getenv("TEST_CONNECTION_SIMPLE_DATABASE_URL_143")`
  → 环境变量: `TEST_CONNECTION_SIMPLE_DATABASE_URL_143`

- 行 179: `database_url="sqlite:///./test.db"`
  → `database_url = os.getenv("TEST_CONNECTION_SIMPLE_DATABASE_URL_179")`
  → 环境变量: `TEST_CONNECTION_SIMPLE_DATABASE_URL_179`

- 行 189: `database_url="sqlite:///./test.db"`
  → `database_url = os.getenv("TEST_CONNECTION_SIMPLE_DATABASE_URL_189")`
  → 环境变量: `TEST_CONNECTION_SIMPLE_DATABASE_URL_189`

- 行 244: `database_url="sqlite:///./test.db"`
  → `database_url = os.getenv("TEST_CONNECTION_SIMPLE_DATABASE_URL_244")`
  → 环境变量: `TEST_CONNECTION_SIMPLE_DATABASE_URL_244`

- 行 287: `database_url="sqlite:///./test.db"`
  → `database_url = os.getenv("TEST_CONNECTION_SIMPLE_DATABASE_URL_287")`
  → 环境变量: `TEST_CONNECTION_SIMPLE_DATABASE_URL_287`

- 行 320: `readonly_url = "postgresql://readonly_user:pass@localhost:5432/db?readonly=true"`
  → `readonly_url = os.getenv("TEST_CONNECTION_SIMPLE_READONLY_URL_320")`
  → 环境变量: `TEST_CONNECTION_SIMPLE_READONLY_URL_320`

- 行 488: `default_level = "READ_COMMITTED"`
  → `default_level = os.getenv("TEST_CONNECTION_SIMPLE_DEFAULT_LEVEL_488")`
  → 环境变量: `TEST_CONNECTION_SIMPLE_DEFAULT_LEVEL_488`

- 行 56: `password="pass"`
  → `password = os.getenv("TEST_CONNECTION_SIMPLE_PASSWORD_56")`
  → 环境变量: `TEST_CONNECTION_SIMPLE_PASSWORD_56`

### tests/unit/database/test_sql_compatibility_complete.py

- 行 22: `url = "sqlite:///test.db"`
  → `url = os.getenv("TEST_SQL_COMPATIBILITY_COMPLETE_URL_22")`
  → 环境变量: `TEST_SQL_COMPATIBILITY_COMPLETE_URL_22`

- 行 24: `url = "sqlite:///:memory:"`
  → `url = os.getenv("TEST_SQL_COMPATIBILITY_COMPLETE_URL_24")`
  → 环境变量: `TEST_SQL_COMPATIBILITY_COMPLETE_URL_24`

- 行 38: `url = "postgresql://user:pass@localhost/test"`
  → `url = os.getenv("TEST_SQL_COMPATIBILITY_COMPLETE_URL_38")`
  → 环境变量: `TEST_SQL_COMPATIBILITY_COMPLETE_URL_38`

- 行 42: `url = "postgresql+psycopg3://user:pass@localhost/test"`
  → `url = os.getenv("TEST_SQL_COMPATIBILITY_COMPLETE_URL_42")`
  → 环境变量: `TEST_SQL_COMPATIBILITY_COMPLETE_URL_42`

- 行 52: `url = "mysql://user:pass@localhost/test"`
  → `url = os.getenv("TEST_SQL_COMPATIBILITY_COMPLETE_URL_52")`
  → 环境变量: `TEST_SQL_COMPATIBILITY_COMPLETE_URL_52`

- 行 56: `url = "mysql+pymysql://user:pass@localhost/test"`
  → `url = os.getenv("TEST_SQL_COMPATIBILITY_COMPLETE_URL_56")`
  → 环境变量: `TEST_SQL_COMPATIBILITY_COMPLETE_URL_56`

- 行 65: `url = "oracle://user:pass@localhost/test"`
  → `url = os.getenv("TEST_SQL_COMPATIBILITY_COMPLETE_URL_65")`
  → 环境变量: `TEST_SQL_COMPATIBILITY_COMPLETE_URL_65`

- 行 79: `base_time="created_at"`
  → `base_time = os.getenv("TEST_SQL_COMPATIBILITY_COMPLETE_BASE_TIME_79")`
  → 环境变量: `TEST_SQL_COMPATIBILITY_COMPLETE_BASE_TIME_79`

- 行 146: `expected = "((julianday(created_at) - julianday('`
  → `expected = os.getenv("TEST_SQL_COMPATIBILITY_COMPLETE_EXPECTED_146")`
  → 环境变量: `TEST_SQL_COMPATIBILITY_COMPLETE_EXPECTED_146`

- 行 302: `pg_sql = "SELECT * FROM users WHERE created_at > NOW() - INTERVAL '`
  → `pg_sql = os.getenv("TEST_SQL_COMPATIBILITY_COMPLETE_PG_SQL_302")`
  → 环境变量: `TEST_SQL_COMPATIBILITY_COMPLETE_PG_SQL_302`

- 行 310: `simple_sql = "SELECT * FROM users"`
  → `simple_sql = os.getenv("TEST_SQL_COMPATIBILITY_COMPLETE_SIMPLE_SQL_310")`
  → 环境变量: `TEST_SQL_COMPATIBILITY_COMPLETE_SIMPLE_SQL_310`

- 行 445: `url = "postgresql://user:pass@localhost/test"`
  → `url = os.getenv("TEST_SQL_COMPATIBILITY_COMPLETE_URL_445")`
  → 环境变量: `TEST_SQL_COMPATIBILITY_COMPLETE_URL_445`

- 行 460: `url = "postgresql://user:pass@localhost/test"`
  → `url = os.getenv("TEST_SQL_COMPATIBILITY_COMPLETE_URL_460")`
  → 环境变量: `TEST_SQL_COMPATIBILITY_COMPLETE_URL_460`

- 行 670: `base_query = "SELECT * FROM events WHERE "`
  → `base_query = os.getenv("TEST_SQL_COMPATIBILITY_COMPLETE_BASE_QUERY_670")`
  → 环境变量: `TEST_SQL_COMPATIBILITY_COMPLETE_BASE_QUERY_670`

### tests/unit/database/test_base.py

- 行 30: `__tablename__ = "test_timestamp_models"`
  → `__tablename__ = os.getenv("TEST_BASE___TABLENAME___30")`
  → 环境变量: `TEST_BASE___TABLENAME___30`

- 行 66: `__tablename__ = "test_concrete_models"`
  → `__tablename__ = os.getenv("TEST_BASE___TABLENAME___66")`
  → 环境变量: `TEST_BASE___TABLENAME___66`

- 行 82: `__tablename__ = "test_to_dict_models"`
  → `__tablename__ = os.getenv("TEST_BASE___TABLENAME___82")`
  → 环境变量: `TEST_BASE___TABLENAME___82`

- 行 108: `__tablename__ = "test_exclude_models"`
  → `__tablename__ = os.getenv("TEST_BASE___TABLENAME___108")`
  → 环境变量: `TEST_BASE___TABLENAME___108`

- 行 114: `secret="hidden"`
  → `secret = os.getenv("TEST_BASE_SECRET_114")`
  → 环境变量: `TEST_BASE_SECRET_114`

- 行 129: `__tablename__ = "test_datetime_models"`
  → `__tablename__ = os.getenv("TEST_BASE___TABLENAME___129")`
  → 环境变量: `TEST_BASE___TABLENAME___129`

- 行 149: `__tablename__ = "test_none_models"`
  → `__tablename__ = os.getenv("TEST_BASE___TABLENAME___149")`
  → 环境变量: `TEST_BASE___TABLENAME___149`

- 行 166: `__tablename__ = "test_from_dict_models"`
  → `__tablename__ = os.getenv("TEST_BASE___TABLENAME___166")`
  → 环境变量: `TEST_BASE___TABLENAME___166`

- 行 186: `__tablename__ = "test_partial_models"`
  → `__tablename__ = os.getenv("TEST_BASE___TABLENAME___186")`
  → 环境变量: `TEST_BASE___TABLENAME___186`

- 行 200: `__tablename__ = "test_update_models"`
  → `__tablename__ = os.getenv("TEST_BASE___TABLENAME___200")`
  → 环境变量: `TEST_BASE___TABLENAME___200`

- 行 206: `name="Original"`
  → `name = os.getenv("TEST_BASE_NAME_206")`
  → 环境变量: `TEST_BASE_NAME_206`

- 行 221: `__tablename__ = "test_update_exclude_models"`
  → `__tablename__ = os.getenv("TEST_BASE___TABLENAME___221")`
  → 环境变量: `TEST_BASE___TABLENAME___221`

- 行 228: `name="Original"`
  → `name = os.getenv("TEST_BASE_NAME_228")`
  → 环境变量: `TEST_BASE_NAME_228`

- 行 242: `__tablename__ = "test_default_exclude_models"`
  → `__tablename__ = os.getenv("TEST_BASE___TABLENAME___242")`
  → 环境变量: `TEST_BASE___TABLENAME___242`

- 行 248: `name="Original"`
  → `name = os.getenv("TEST_BASE_NAME_248")`
  → 环境变量: `TEST_BASE_NAME_248`

- 行 262: `__tablename__ = "test_invalid_field_models"`
  → `__tablename__ = os.getenv("TEST_BASE___TABLENAME___262")`
  → 环境变量: `TEST_BASE___TABLENAME___262`

- 行 266: `name="Original"`
  → `name = os.getenv("TEST_BASE_NAME_266")`
  → 环境变量: `TEST_BASE_NAME_266`

- 行 282: `__tablename__ = "test_repr_models"`
  → `__tablename__ = os.getenv("TEST_BASE___TABLENAME___282")`
  → 环境变量: `TEST_BASE___TABLENAME___282`

- 行 292: `__tablename__ = "test_repr_no_id_models"`
  → `__tablename__ = os.getenv("TEST_BASE___TABLENAME___292")`
  → 环境变量: `TEST_BASE___TABLENAME___292`

- 行 305: `__tablename__ = "test_all_exclude_models"`
  → `__tablename__ = os.getenv("TEST_BASE___TABLENAME___305")`
  → 环境变量: `TEST_BASE___TABLENAME___305`

- 行 326: `__tablename__ = "test_empty_dict_models"`
  → `__tablename__ = os.getenv("TEST_BASE___TABLENAME___326")`
  → 环境变量: `TEST_BASE___TABLENAME___326`

- 行 336: `__tablename__ = "test_empty_update_models"`
  → `__tablename__ = os.getenv("TEST_BASE___TABLENAME___336")`
  → 环境变量: `TEST_BASE___TABLENAME___336`

- 行 339: `original_name = "Original"`
  → `original_name = os.getenv("TEST_BASE_ORIGINAL_NAME_339")`
  → 环境变量: `TEST_BASE_ORIGINAL_NAME_339`

- 行 353: `__tablename__ = "test_special_models"`
  → `__tablename__ = os.getenv("TEST_BASE___TABLENAME___353")`
  → 环境变量: `TEST_BASE___TABLENAME___353`

- 行 356: `special_text = "特殊字符: 中文, ñ, é, ü, 🚀"`
  → `special_text = os.getenv("TEST_BASE_SPECIAL_TEXT_356")`
  → 环境变量: `TEST_BASE_SPECIAL_TEXT_356`

- 行 370: `__tablename__ = "test_microsec_models"`
  → `__tablename__ = os.getenv("TEST_BASE___TABLENAME___370")`
  → 环境变量: `TEST_BASE___TABLENAME___370`

### tests/unit/database/test_sql_compatibility_final.py

- 行 22: `url = "sqlite:///test.db"`
  → `url = os.getenv("TEST_SQL_COMPATIBILITY_FINAL_URL_22")`
  → 环境变量: `TEST_SQL_COMPATIBILITY_FINAL_URL_22`

- 行 26: `url = "sqlite:///:memory:"`
  → `url = os.getenv("TEST_SQL_COMPATIBILITY_FINAL_URL_26")`
  → 环境变量: `TEST_SQL_COMPATIBILITY_FINAL_URL_26`

- 行 38: `url = "postgresql://user:pass@localhost/test"`
  → `url = os.getenv("TEST_SQL_COMPATIBILITY_FINAL_URL_38")`
  → 环境变量: `TEST_SQL_COMPATIBILITY_FINAL_URL_38`

- 行 43: `url = "postgresql+psycopg3://user:pass@localhost/test"`
  → `url = os.getenv("TEST_SQL_COMPATIBILITY_FINAL_URL_43")`
  → 环境变量: `TEST_SQL_COMPATIBILITY_FINAL_URL_43`

- 行 52: `url = "mysql://user:pass@localhost/test"`
  → `url = os.getenv("TEST_SQL_COMPATIBILITY_FINAL_URL_52")`
  → 环境变量: `TEST_SQL_COMPATIBILITY_FINAL_URL_52`

- 行 56: `url = "mysql+pymysql://user:pass@localhost/test"`
  → `url = os.getenv("TEST_SQL_COMPATIBILITY_FINAL_URL_56")`
  → 环境变量: `TEST_SQL_COMPATIBILITY_FINAL_URL_56`

- 行 66: `url = "oracle://user:pass@localhost/test"`
  → `url = os.getenv("TEST_SQL_COMPATIBILITY_FINAL_URL_66")`
  → 环境变量: `TEST_SQL_COMPATIBILITY_FINAL_URL_66`

- 行 85: `base_time="created_at"`
  → `base_time = os.getenv("TEST_SQL_COMPATIBILITY_FINAL_BASE_TIME_85")`
  → 环境变量: `TEST_SQL_COMPATIBILITY_FINAL_BASE_TIME_85`

- 行 151: `expected = "((julianday(created_at) - julianday('`
  → `expected = os.getenv("TEST_SQL_COMPATIBILITY_FINAL_EXPECTED_151")`
  → 环境变量: `TEST_SQL_COMPATIBILITY_FINAL_EXPECTED_151`

- 行 398: `url = "postgresql://user:pass@localhost/test"`
  → `url = os.getenv("TEST_SQL_COMPATIBILITY_FINAL_URL_398")`
  → 环境变量: `TEST_SQL_COMPATIBILITY_FINAL_URL_398`

- 行 413: `url = "postgresql://user:pass@localhost/test"`
  → `url = os.getenv("TEST_SQL_COMPATIBILITY_FINAL_URL_413")`
  → 环境变量: `TEST_SQL_COMPATIBILITY_FINAL_URL_413`

### tests/unit/cache/test_redis_manager_simple.py

- 行 28: `redis_url = "redis://localhost:6379/0"`
  → `redis_url = os.getenv("TEST_REDIS_MANAGER_SIMPLE_REDIS_URL_28")`
  → 环境变量: `TEST_REDIS_MANAGER_SIMPLE_REDIS_URL_28`

### tests/unit/core/test_core_modules.py

- 行 32: `msg = "Test error message"`
  → `msg = os.getenv("TEST_CORE_MODULES_MSG_32")`
  → 环境变量: `TEST_CORE_MODULES_MSG_32`

- 行 41: `msg = "Validation failed"`
  → `msg = os.getenv("TEST_CORE_MODULES_MSG_41")`
  → 环境变量: `TEST_CORE_MODULES_MSG_41`

- 行 47: `msg = "Prediction failed"`
  → `msg = os.getenv("TEST_CORE_MODULES_MSG_47")`
  → 环境变量: `TEST_CORE_MODULES_MSG_47`

- 行 54: `msg = "Database connection failed"`
  → `msg = os.getenv("TEST_CORE_MODULES_MSG_54")`
  → 环境变量: `TEST_CORE_MODULES_MSG_54`

- 行 61: `msg = "Configuration missing"`
  → `msg = os.getenv("TEST_CORE_MODULES_MSG_61")`
  → 环境变量: `TEST_CORE_MODULES_MSG_61`

- 行 66: `msg = "Error occurred"`
  → `msg = os.getenv("TEST_CORE_MODULES_MSG_66")`
  → 环境变量: `TEST_CORE_MODULES_MSG_66`

### tests/unit/services/test_audit_service_comprehensive.py

- 行 52: `test_user_id = "user123"`
  → `test_user_id = os.getenv("TEST_AUDIT_SERVICE_COMPREHENSIVE_TEST_USER_ID_52")`
  → 环境变量: `TEST_AUDIT_SERVICE_COMPREHENSIVE_TEST_USER_ID_52`

- 行 52: `test_action = "PREDICTION_REQUEST"`
  → `test_action = os.getenv("TEST_AUDIT_SERVICE_COMPREHENSIVE_TEST_ACTION_52")`
  → 环境变量: `TEST_AUDIT_SERVICE_COMPREHENSIVE_TEST_ACTION_52`

- 行 53: `test_resource = "match/12345"`
  → `test_resource = os.getenv("TEST_AUDIT_SERVICE_COMPREHENSIVE_TEST_RESOURCE_53")`
  → 环境变量: `TEST_AUDIT_SERVICE_COMPREHENSIVE_TEST_RESOURCE_53`

- 行 106: `event="MODEL_LOADED"`
  → `event = os.getenv("TEST_AUDIT_SERVICE_COMPREHENSIVE_EVENT_106")`
  → 环境变量: `TEST_AUDIT_SERVICE_COMPREHENSIVE_EVENT_106`

- 行 127: `event_type="UNAUTHORIZED_ACCESS"`
  → `event_type = os.getenv("TEST_AUDIT_SERVICE_COMPREHENSIVE_EVENT_TYPE_127")`
  → 环境变量: `TEST_AUDIT_SERVICE_COMPREHENSIVE_EVENT_TYPE_127`

- 行 128: `user_id="unknown"`
  → `user_id = os.getenv("TEST_AUDIT_SERVICE_COMPREHENSIVE_USER_ID_128")`
  → 环境变量: `TEST_AUDIT_SERVICE_COMPREHENSIVE_USER_ID_128`

- 行 166: `user_id="user123"`
  → `user_id = os.getenv("TEST_AUDIT_SERVICE_COMPREHENSIVE_USER_ID_166")`
  → 环境变量: `TEST_AUDIT_SERVICE_COMPREHENSIVE_USER_ID_166`

- 行 195: `user_agent="TestAgent/1.0"`
  → `user_agent = os.getenv("TEST_AUDIT_SERVICE_COMPREHENSIVE_USER_AGENT_195")`
  → 环境变量: `TEST_AUDIT_SERVICE_COMPREHENSIVE_USER_AGENT_195`

- 行 237: `action="FAILED_LOGIN"`
  → `action = os.getenv("TEST_AUDIT_SERVICE_COMPREHENSIVE_ACTION_237")`
  → 环境变量: `TEST_AUDIT_SERVICE_COMPREHENSIVE_ACTION_237`

- 行 246: `action="LOGOUT"`
  → `action = os.getenv("TEST_AUDIT_SERVICE_COMPREHENSIVE_ACTION_246")`
  → 环境变量: `TEST_AUDIT_SERVICE_COMPREHENSIVE_ACTION_246`

- 行 270: `resource_id = "resource_123"`
  → `resource_id = os.getenv("TEST_AUDIT_SERVICE_COMPREHENSIVE_RESOURCE_ID_270")`
  → 环境变量: `TEST_AUDIT_SERVICE_COMPREHENSIVE_RESOURCE_ID_270`

- 行 311: `action="PREDICTION"`
  → `action = os.getenv("TEST_AUDIT_SERVICE_COMPREHENSIVE_ACTION_311")`
  → 环境变量: `TEST_AUDIT_SERVICE_COMPREHENSIVE_ACTION_311`

- 行 371: `user_id="attacker"`
  → `user_id = os.getenv("TEST_AUDIT_SERVICE_COMPREHENSIVE_USER_ID_371")`
  → 环境变量: `TEST_AUDIT_SERVICE_COMPREHENSIVE_USER_ID_371`

- 行 371: `action="UNAUTHORIZED_ACCESS"`
  → `action = os.getenv("TEST_AUDIT_SERVICE_COMPREHENSIVE_ACTION_371")`
  → 环境变量: `TEST_AUDIT_SERVICE_COMPREHENSIVE_ACTION_371`

- 行 398: `user_id = "attacker"`
  → `user_id = os.getenv("TEST_AUDIT_SERVICE_COMPREHENSIVE_USER_ID_398")`
  → 环境变量: `TEST_AUDIT_SERVICE_COMPREHENSIVE_USER_ID_398`

- 行 517: `user_id = "user123"`
  → `user_id = os.getenv("TEST_AUDIT_SERVICE_COMPREHENSIVE_USER_ID_517")`
  → 环境变量: `TEST_AUDIT_SERVICE_COMPREHENSIVE_USER_ID_517`

- 行 527: `quarter="2024Q3"`
  → `quarter = os.getenv("TEST_AUDIT_SERVICE_COMPREHENSIVE_QUARTER_527")`
  → 环境变量: `TEST_AUDIT_SERVICE_COMPREHENSIVE_QUARTER_527`

- 行 534: `patient_id="patient456"`
  → `patient_id = os.getenv("TEST_AUDIT_SERVICE_COMPREHENSIVE_PATIENT_ID_534")`
  → 环境变量: `TEST_AUDIT_SERVICE_COMPREHENSIVE_PATIENT_ID_534`

### tests/unit/services/test_data_processing_comprehensive.py

- 行 86: `errors='coerce'`
  → `errors = os.getenv("TEST_DATA_PROCESSING_COMPREHENSIVE_ERRORS_86")`
  → 环境变量: `TEST_DATA_PROCESSING_COMPREHENSIVE_ERRORS_86`

- 行 172: `group_by='team_id'`
  → `group_by = os.getenv("TEST_DATA_PROCESSING_COMPREHENSIVE_GROUP_BY_172")`
  → 环境变量: `TEST_DATA_PROCESSING_COMPREHENSIVE_GROUP_BY_172`

- 行 222: `errors='coerce'`
  → `errors = os.getenv("TEST_DATA_PROCESSING_COMPREHENSIVE_ERRORS_222")`
  → 环境变量: `TEST_DATA_PROCESSING_COMPREHENSIVE_ERRORS_222`

- 行 271: `strategy='constant'`
  → `strategy = os.getenv("TEST_DATA_PROCESSING_COMPREHENSIVE_STRATEGY_271")`
  → 环境变量: `TEST_DATA_PROCESSING_COMPREHENSIVE_STRATEGY_271`

- 行 274: `fill_value='UNKNOWN'`
  → `fill_value = os.getenv("TEST_DATA_PROCESSING_COMPREHENSIVE_FILL_VALUE_274")`
  → 环境变量: `TEST_DATA_PROCESSING_COMPREHENSIVE_FILL_VALUE_274`

- 行 286: `method='zscore'`
  → `method = os.getenv("TEST_DATA_PROCESSING_COMPREHENSIVE_METHOD_286")`
  → 环境变量: `TEST_DATA_PROCESSING_COMPREHENSIVE_METHOD_286`

- 行 296: `method='minmax'`
  → `method = os.getenv("TEST_DATA_PROCESSING_COMPREHENSIVE_METHOD_296")`
  → 环境变量: `TEST_DATA_PROCESSING_COMPREHENSIVE_METHOD_296`

- 行 301: `method='zscore'`
  → `method = os.getenv("TEST_DATA_PROCESSING_COMPREHENSIVE_METHOD_301")`
  → 环境变量: `TEST_DATA_PROCESSING_COMPREHENSIVE_METHOD_301`

- 行 391: `method='onehot'`
  → `method = os.getenv("TEST_DATA_PROCESSING_COMPREHENSIVE_METHOD_391")`
  → 环境变量: `TEST_DATA_PROCESSING_COMPREHENSIVE_METHOD_391`

- 行 526: `method='quantile'`
  → `method = os.getenv("TEST_DATA_PROCESSING_COMPREHENSIVE_METHOD_526")`
  → 环境变量: `TEST_DATA_PROCESSING_COMPREHENSIVE_METHOD_526`

- 行 696: `columns='result'`
  → `columns = os.getenv("TEST_DATA_PROCESSING_COMPREHENSIVE_COLUMNS_696")`
  → 环境变量: `TEST_DATA_PROCESSING_COMPREHENSIVE_COLUMNS_696`

- 行 738: `timestamp_col='timestamp'`
  → `timestamp_col = os.getenv("TEST_DATA_PROCESSING_COMPREHENSIVE_TIMESTAMP_COL_7")`
  → 环境变量: `TEST_DATA_PROCESSING_COMPREHENSIVE_TIMESTAMP_COL_7`

- 行 744: `timestamp_col='timestamp'`
  → `timestamp_col = os.getenv("TEST_DATA_PROCESSING_COMPREHENSIVE_TIMESTAMP_COL_7")`
  → 环境变量: `TEST_DATA_PROCESSING_COMPREHENSIVE_TIMESTAMP_COL_7`

- 行 761: `group_by='category'`
  → `group_by = os.getenv("TEST_DATA_PROCESSING_COMPREHENSIVE_GROUP_BY_761")`
  → 环境变量: `TEST_DATA_PROCESSING_COMPREHENSIVE_GROUP_BY_761`

### tests/unit/data/collectors/test_base_collector_simple.py

- 行 24: `str = "test_source"`
  → `str = os.getenv("TEST_BASE_COLLECTOR_SIMPLE_STR_24")`
  → 环境变量: `TEST_BASE_COLLECTOR_SIMPLE_STR_24`

- 行 29: `collection_type="fixtures"`
  → `collection_type = os.getenv("TEST_BASE_COLLECTOR_SIMPLE_COLLECTION_TYPE_29")`
  → 环境变量: `TEST_BASE_COLLECTOR_SIMPLE_COLLECTION_TYPE_29`

- 行 31: `status="success"`
  → `status = os.getenv("TEST_BASE_COLLECTOR_SIMPLE_STATUS_31")`
  → 环境变量: `TEST_BASE_COLLECTOR_SIMPLE_STATUS_31`

- 行 40: `status="success"`
  → `status = os.getenv("TEST_BASE_COLLECTOR_SIMPLE_STATUS_40")`
  → 环境变量: `TEST_BASE_COLLECTOR_SIMPLE_STATUS_40`

- 行 45: `collection_type="live_scores"`
  → `collection_type = os.getenv("TEST_BASE_COLLECTOR_SIMPLE_COLLECTION_TYPE_45")`
  → 环境变量: `TEST_BASE_COLLECTOR_SIMPLE_COLLECTION_TYPE_45`

- 行 49: `status="success"`
  → `status = os.getenv("TEST_BASE_COLLECTOR_SIMPLE_STATUS_49")`
  → 环境变量: `TEST_BASE_COLLECTOR_SIMPLE_STATUS_49`

- 行 54: `collection_type="fixtures"`
  → `collection_type = os.getenv("TEST_BASE_COLLECTOR_SIMPLE_COLLECTION_TYPE_54")`
  → 环境变量: `TEST_BASE_COLLECTOR_SIMPLE_COLLECTION_TYPE_54`

- 行 61: `status="partial"`
  → `status = os.getenv("TEST_BASE_COLLECTOR_SIMPLE_STATUS_61")`
  → 环境变量: `TEST_BASE_COLLECTOR_SIMPLE_STATUS_61`

- 行 74: `collection_type="fixtures"`
  → `collection_type = os.getenv("TEST_BASE_COLLECTOR_SIMPLE_COLLECTION_TYPE_74")`
  → 环境变量: `TEST_BASE_COLLECTOR_SIMPLE_COLLECTION_TYPE_74`

- 行 77: `status="success"`
  → `status = os.getenv("TEST_BASE_COLLECTOR_SIMPLE_STATUS_77")`
  → 环境变量: `TEST_BASE_COLLECTOR_SIMPLE_STATUS_77`

- 行 101: `data_source="custom_api"`
  → `data_source = os.getenv("TEST_BASE_COLLECTOR_SIMPLE_DATA_SOURCE_101")`
  → 环境变量: `TEST_BASE_COLLECTOR_SIMPLE_DATA_SOURCE_101`

### tests/unit/data/collectors/test_base_collector.py

- 行 26: `str = "test_source"`
  → `str = os.getenv("TEST_BASE_COLLECTOR_STR_26")`
  → 环境变量: `TEST_BASE_COLLECTOR_STR_26`

- 行 32: `collection_type="fixtures"`
  → `collection_type = os.getenv("TEST_BASE_COLLECTOR_COLLECTION_TYPE_32")`
  → 环境变量: `TEST_BASE_COLLECTOR_COLLECTION_TYPE_32`

- 行 34: `status="partial"`
  → `status = os.getenv("TEST_BASE_COLLECTOR_STATUS_34")`
  → 环境变量: `TEST_BASE_COLLECTOR_STATUS_34`

- 行 36: `error_message="Some records failed"`
  → `error_message = os.getenv("TEST_BASE_COLLECTOR_ERROR_MESSAGE_36")`
  → 环境变量: `TEST_BASE_COLLECTOR_ERROR_MESSAGE_36`

- 行 46: `status="success"`
  → `status = os.getenv("TEST_BASE_COLLECTOR_STATUS_46")`
  → 环境变量: `TEST_BASE_COLLECTOR_STATUS_46`

- 行 54: `collection_type="live_scores"`
  → `collection_type = os.getenv("TEST_BASE_COLLECTOR_COLLECTION_TYPE_54")`
  → 环境变量: `TEST_BASE_COLLECTOR_COLLECTION_TYPE_54`

- 行 57: `status="partial"`
  → `status = os.getenv("TEST_BASE_COLLECTOR_STATUS_57")`
  → 环境变量: `TEST_BASE_COLLECTOR_STATUS_57`

- 行 58: `error_message="Connection timeout"`
  → `error_message = os.getenv("TEST_BASE_COLLECTOR_ERROR_MESSAGE_58")`
  → 环境变量: `TEST_BASE_COLLECTOR_ERROR_MESSAGE_58`

- 行 63: `data_source="test_api"`
  → `data_source = os.getenv("TEST_BASE_COLLECTOR_DATA_SOURCE_63")`
  → 环境变量: `TEST_BASE_COLLECTOR_DATA_SOURCE_63`

- 行 64: `collection_type="fixtures"`
  → `collection_type = os.getenv("TEST_BASE_COLLECTOR_COLLECTION_TYPE_64")`
  → 环境变量: `TEST_BASE_COLLECTOR_COLLECTION_TYPE_64`

- 行 71: `status="success"`
  → `status = os.getenv("TEST_BASE_COLLECTOR_STATUS_71")`
  → 环境变量: `TEST_BASE_COLLECTOR_STATUS_71`

- 行 84: `data_source="test_api"`
  → `data_source = os.getenv("TEST_BASE_COLLECTOR_DATA_SOURCE_84")`
  → 环境变量: `TEST_BASE_COLLECTOR_DATA_SOURCE_84`

- 行 87: `status="partial"`
  → `status = os.getenv("TEST_BASE_COLLECTOR_STATUS_87")`
  → 环境变量: `TEST_BASE_COLLECTOR_STATUS_87`

- 行 88: `error_message="Some API calls failed"`
  → `error_message = os.getenv("TEST_BASE_COLLECTOR_ERROR_MESSAGE_88")`
  → 环境变量: `TEST_BASE_COLLECTOR_ERROR_MESSAGE_88`

- 行 112: `data_source="football_api"`
  → `data_source = os.getenv("TEST_BASE_COLLECTOR_DATA_SOURCE_112")`
  → 环境变量: `TEST_BASE_COLLECTOR_DATA_SOURCE_112`

- 行 295: `match="Persistent failure"`
  → `match = os.getenv("TEST_BASE_COLLECTOR_MATCH_295")`
  → 环境变量: `TEST_BASE_COLLECTOR_MATCH_295`

- 行 350: `match="Unsupported table name"`
  → `match = os.getenv("TEST_BASE_COLLECTOR_MATCH_350")`
  → 环境变量: `TEST_BASE_COLLECTOR_MATCH_350`

- 行 476: `collection_type="fixtures"`
  → `collection_type = os.getenv("TEST_BASE_COLLECTOR_COLLECTION_TYPE_476")`
  → 环境变量: `TEST_BASE_COLLECTOR_COLLECTION_TYPE_476`

- 行 481: `status="success"`
  → `status = os.getenv("TEST_BASE_COLLECTOR_STATUS_481")`
  → 环境变量: `TEST_BASE_COLLECTOR_STATUS_481`

- 行 496: `SUCCESS = "SUCCESS"`
  → `SUCCESS = os.getenv("TEST_BASE_COLLECTOR_SUCCESS_496")`
  → 环境变量: `TEST_BASE_COLLECTOR_SUCCESS_496`

- 行 507: `collection_type="fixtures"`
  → `collection_type = os.getenv("TEST_BASE_COLLECTOR_COLLECTION_TYPE_507")`
  → 环境变量: `TEST_BASE_COLLECTOR_COLLECTION_TYPE_507`

- 行 508: `status="failed"`
  → `status = os.getenv("TEST_BASE_COLLECTOR_STATUS_508")`
  → 环境变量: `TEST_BASE_COLLECTOR_STATUS_508`

### tests/unit/lineage/test_lineage_reporter.py

- 行 102: `start_node = 'source_table'`
  → `start_node = os.getenv("TEST_LINEAGE_REPORTER_START_NODE_102")`
  → 环境变量: `TEST_LINEAGE_REPORTER_START_NODE_102`

- 行 113: `changed_table = 'source_table'`
  → `changed_table = os.getenv("TEST_LINEAGE_REPORTER_CHANGED_TABLE_113")`
  → 环境变量: `TEST_LINEAGE_REPORTER_CHANGED_TABLE_113`

- 行 164: `source = 'table_a'`
  → `source = os.getenv("TEST_LINEAGE_REPORTER_SOURCE_164")`
  → 环境变量: `TEST_LINEAGE_REPORTER_SOURCE_164`

- 行 165: `target = 'table_b'`
  → `target = os.getenv("TEST_LINEAGE_REPORTER_TARGET_165")`
  → 环境变量: `TEST_LINEAGE_REPORTER_TARGET_165`

- 行 173: `source = 'table_a'`
  → `source = os.getenv("TEST_LINEAGE_REPORTER_SOURCE_173")`
  → 环境变量: `TEST_LINEAGE_REPORTER_SOURCE_173`

- 行 174: `target = 'table_b'`
  → `target = os.getenv("TEST_LINEAGE_REPORTER_TARGET_174")`
  → 环境变量: `TEST_LINEAGE_REPORTER_TARGET_174`

- 行 185: `table = 'target_table'`
  → `table = os.getenv("TEST_LINEAGE_REPORTER_TABLE_185")`
  → 环境变量: `TEST_LINEAGE_REPORTER_TABLE_185`

- 行 197: `table = 'source_table'`
  → `table = os.getenv("TEST_LINEAGE_REPORTER_TABLE_197")`
  → 环境变量: `TEST_LINEAGE_REPORTER_TABLE_197`

### tests/e2e/test_mock_pipeline.py

- 行 19: `title="Mock Football API"`
  → `title = os.getenv("TEST_MOCK_PIPELINE_TITLE_19")`
  → 环境变量: `TEST_MOCK_PIPELINE_TITLE_19`

### tests/e2e/test_complete_prediction_flow.py

- 行 45: `value="scheduled"`
  → `value = os.getenv("TEST_COMPLETE_PREDICTION_FLOW_VALUE_45")`
  → 环境变量: `TEST_COMPLETE_PREDICTION_FLOW_VALUE_45`

- 行 45: `season = "2024-25"`
  → `season = os.getenv("TEST_COMPLETE_PREDICTION_FLOW_SEASON_45")`
  → 环境变量: `TEST_COMPLETE_PREDICTION_FLOW_SEASON_45`

### tests/e2e/test_monitoring_pipeline.py

- 行 27: `title="数据质量告警"`
  → `title = os.getenv("TEST_MONITORING_PIPELINE_TITLE_27")`
  → 环境变量: `TEST_MONITORING_PIPELINE_TITLE_27`

- 行 27: `message="测试数据完整性低于阈值"`
  → `message = os.getenv("TEST_MONITORING_PIPELINE_MESSAGE_27")`
  → 环境变量: `TEST_MONITORING_PIPELINE_MESSAGE_27`

- 行 28: `source="e2e_test"`
  → `source = os.getenv("TEST_MONITORING_PIPELINE_SOURCE_28")`
  → 环境变量: `TEST_MONITORING_PIPELINE_SOURCE_28`

- 行 31: `title="系统性能告警"`
  → `title = os.getenv("TEST_MONITORING_PIPELINE_TITLE_31")`
  → 环境变量: `TEST_MONITORING_PIPELINE_TITLE_31`

- 行 31: `message="API响应时间过长"`
  → `message = os.getenv("TEST_MONITORING_PIPELINE_MESSAGE_31")`
  → 环境变量: `TEST_MONITORING_PIPELINE_MESSAGE_31`

- 行 34: `source="e2e_test"`
  → `source = os.getenv("TEST_MONITORING_PIPELINE_SOURCE_34")`
  → 环境变量: `TEST_MONITORING_PIPELINE_SOURCE_34`

### tests/e2e/test_prediction_pipeline.py

- 行 12: `scope="module"`
  → `scope = os.getenv("TEST_PREDICTION_PIPELINE_SCOPE_12")`
  → 环境变量: `TEST_PREDICTION_PIPELINE_SCOPE_12`

- 行 20: `scope="module"`
  → `scope = os.getenv("TEST_PREDICTION_PIPELINE_SCOPE_20")`
  → 环境变量: `TEST_PREDICTION_PIPELINE_SCOPE_20`

- 行 47: `value="scheduled"`
  → `value = os.getenv("TEST_PREDICTION_PIPELINE_VALUE_47")`
  → 环境变量: `TEST_PREDICTION_PIPELINE_VALUE_47`

- 行 48: `season = "2024-25"`
  → `season = os.getenv("TEST_PREDICTION_PIPELINE_SEASON_48")`
  → 环境变量: `TEST_PREDICTION_PIPELINE_SEASON_48`

### reports/model_performance_report.py

- 行 46: `str = "reports/generated"`
  → `str = os.getenv("MODEL_PERFORMANCE_REPORT_STR_46")`
  → 环境变量: `MODEL_PERFORMANCE_REPORT_STR_46`

- 行 362: `loc="upper left"`
  → `loc = os.getenv("MODEL_PERFORMANCE_REPORT_LOC_362")`
  → 环境变量: `MODEL_PERFORMANCE_REPORT_LOC_362`

- 行 463: `autopct="%1.1f%%"`
  → `autopct = os.getenv("MODEL_PERFORMANCE_REPORT_AUTOPCT_463")`
  → 环境变量: `MODEL_PERFORMANCE_REPORT_AUTOPCT_463`

- 行 513: `ha="center"`
  → `ha = os.getenv("MODEL_PERFORMANCE_REPORT_HA_513")`
  → 环境变量: `MODEL_PERFORMANCE_REPORT_HA_513`

- 行 514: `va="center"`
  → `va = os.getenv("MODEL_PERFORMANCE_REPORT_VA_514")`
  → 环境变量: `MODEL_PERFORMANCE_REPORT_VA_514`

- 行 532: `va="center"`
  → `va = os.getenv("MODEL_PERFORMANCE_REPORT_VA_532")`
  → 环境变量: `MODEL_PERFORMANCE_REPORT_VA_532`

- 行 644: `trend_desc = "📈 上升趋势"`
  → `trend_desc = os.getenv("MODEL_PERFORMANCE_REPORT_TREND_DESC_644")`
  → 环境变量: `MODEL_PERFORMANCE_REPORT_TREND_DESC_644`

- 行 645: `trend_desc = "📉 下降趋势"`
  → `trend_desc = os.getenv("MODEL_PERFORMANCE_REPORT_TREND_DESC_645")`
  → 环境变量: `MODEL_PERFORMANCE_REPORT_TREND_DESC_645`

- 行 647: `trend_desc = "➡️ 稳定趋势"`
  → `trend_desc = os.getenv("MODEL_PERFORMANCE_REPORT_TREND_DESC_647")`
  → 环境变量: `MODEL_PERFORMANCE_REPORT_TREND_DESC_647`

- 行 648: `trend_desc = "📊 数据不足"`
  → `trend_desc = os.getenv("MODEL_PERFORMANCE_REPORT_TREND_DESC_648")`
  → 环境变量: `MODEL_PERFORMANCE_REPORT_TREND_DESC_648`

- 行 870: `help="分析回看天数"`
  → `help = os.getenv("MODEL_PERFORMANCE_REPORT_HELP_870")`
  → 环境变量: `MODEL_PERFORMANCE_REPORT_HELP_870`

- 行 873: `help="移动窗口大小"`
  → `help = os.getenv("MODEL_PERFORMANCE_REPORT_HELP_873")`
  → 环境变量: `MODEL_PERFORMANCE_REPORT_HELP_873`

- 行 873: `default="reports/generated"`
  → `default = os.getenv("MODEL_PERFORMANCE_REPORT_DEFAULT_873")`
  → 环境变量: `MODEL_PERFORMANCE_REPORT_DEFAULT_873`

## 错误列表

- 处理文件失败 /home/user/projects/FootballPrediction/tests/legacy/unit/models/test_prediction_service_comprehensive.py: [Errno 32] Broken pipe
- 处理文件失败 /home/user/projects/FootballPrediction/tests/unit/api/test_models_simple2.py: [Errno 32] Broken pipe

## 后续步骤

1. 复制 `.env.template` 为 `.env.local`
2. 填写实际的配置值
3. 确保 `.env.local` 在 `.gitignore` 中
4. 运行测试验证修复效果
