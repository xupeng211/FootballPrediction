# 语法错误修复指南

剩余需要手动修复的文件数: 222

## src/adapters/factory_simple.py
错误: 第93行: invalid syntax

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/adapters/factory_simple.py').read()))"
```

## src/adapters/factory.py
错误: 第30行: illegal target for annotation

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/adapters/factory.py').read()))"
```

## src/adapters/registry.py
错误: 第261行: illegal target for annotation

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/adapters/registry.py').read()))"
```

## src/adapters/football.py
错误: 第37行: illegal target for annotation

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/adapters/football.py').read()))"
```

## src/config/openapi_config.py
错误: 第473行: closing parenthesis '}' does not match opening parenthesis '[' on line 454

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/config/openapi_config.py').read()))"
```

## src/api/schemas.py
错误: 第16行: illegal target for annotation

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/api/schemas.py').read()))"
```

## src/api/cqrs.py
错误: 第25行: illegal target for annotation

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/api/cqrs.py').read()))"
```

## src/api/buggy_api.py
错误: 第11行: invalid syntax

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/api/buggy_api.py').read()))"
```

## src/api/dependencies.py
错误: 第37行: invalid syntax

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/api/dependencies.py').read()))"
```

## src/api/data_router.py
错误: 第33行: illegal target for annotation

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/api/data_router.py').read()))"
```

## src/api/features.py
错误: 第26行: unexpected indent

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/api/features.py').read()))"
```

## src/api/facades.py
错误: 第20行: unexpected indent

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/api/facades.py').read()))"
```

## src/api/deps.py
错误: 第25行: invalid syntax

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/api/deps.py').read()))"
```

## src/api/app.py
错误: 第33行: unexpected indent

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/api/app.py').read()))"
```

## src/api/decorators.py
错误: 第61行: invalid syntax

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/api/decorators.py').read()))"
```

## src/api/observers.py
错误: 第25行: illegal target for annotation

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/api/observers.py').read()))"
```

## src/api/repositories.py
错误: 第34行: invalid syntax

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/api/repositories.py').read()))"
```

## src/api/events.py
错误: 第64行: invalid syntax

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/api/events.py').read()))"
```

## src/api/adapters.py
错误: 第116行: invalid syntax

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/api/adapters.py').read()))"
```

## src/api/monitoring.py
错误: 第51行: illegal target for annotation

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/api/monitoring.py').read()))"
```

## src/api/auth.py
错误: 第27行: invalid syntax

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/api/auth.py').read()))"
```

## src/api/predictions/models.py
错误: 第12行: illegal target for annotation

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/api/predictions/models.py').read()))"
```

## src/api/predictions/router.py
错误: 第32行: illegal target for annotation

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/api/predictions/router.py').read()))"
```

## src/api/data/__init__.py
错误: 第24行: expected an indented block after class definition on line 23

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/api/data/__init__.py').read()))"
```

## src/api/data/models/odds_models.py
错误: 第13行: illegal target for annotation

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/api/data/models/odds_models.py').read()))"
```

## src/api/data/models/match_models.py
错误: 第14行: illegal target for annotation

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/api/data/models/match_models.py').read()))"
```

## src/api/data/models/__init__.py
错误: 第21行: expected an indented block after class definition on line 20

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/api/data/models/__init__.py').read()))"
```

## src/api/data/models/league_models.py
错误: 第14行: illegal target for annotation

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/api/data/models/league_models.py').read()))"
```

## src/api/data/models/team_models.py
错误: 第13行: illegal target for annotation

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/api/data/models/team_models.py').read()))"
```

## src/utils/validators.py
错误: 第29行: invalid syntax

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/utils/validators.py').read()))"
```

## src/utils/response.py
错误: 第17行: illegal target for annotation

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/utils/response.py').read()))"
```

## src/utils/dict_utils.py
错误: 第61行: invalid syntax

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/utils/dict_utils.py').read()))"
```

## src/utils/time_utils.py
错误: 第35行: invalid syntax

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/utils/time_utils.py').read()))"
```

## src/utils/data_validator.py
错误: 第38行: invalid syntax

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/utils/data_validator.py').read()))"
```

## src/utils/file_utils.py
错误: 第43行: invalid syntax

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/utils/file_utils.py').read()))"
```

## src/utils/redis_cache.py
错误: 第19行: invalid syntax

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/utils/redis_cache.py').read()))"
```

## src/utils/_retry/__init__.py
错误: 第21行: invalid syntax

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/utils/_retry/__init__.py').read()))"
```

## src/repositories/base.py
错误: 第26行: illegal target for annotation

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/repositories/base.py').read()))"
```

## src/repositories/prediction.py
错误: 第134行: unmatched ')'

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/repositories/prediction.py').read()))"
```

## src/repositories/user.py
错误: 第281行: closing parenthesis ')' does not match opening parenthesis '[' on line 272

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/repositories/user.py').read()))"
```

## src/repositories/provider.py
错误: 第53行: invalid syntax

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/repositories/provider.py').read()))"
```

## src/repositories/di.py
错误: 第29行: invalid syntax

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/repositories/di.py').read()))"
```

## src/repositories/match.py
错误: 第144行: closing parenthesis '}' does not match opening parenthesis '['

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/repositories/match.py').read()))"
```

## src/stubs/mocks/feast.py
错误: 第112行: closing parenthesis ')' does not match opening parenthesis '[' on line 111

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/stubs/mocks/feast.py').read()))"
```

## src/stubs/mocks/confluent_kafka.py
错误: 第21行: closing parenthesis ')' does not match opening parenthesis '[' on line 20

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/stubs/mocks/confluent_kafka.py').read()))"
```

## src/facades/base.py
错误: 第82行: closing parenthesis ')' does not match opening parenthesis '[' on line 81

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/facades/base.py').read()))"
```

## src/facades/facades.py
错误: 第52行: closing parenthesis ')' does not match opening parenthesis '[' on line 51

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/facades/facades.py').read()))"
```

## src/facades/factory.py
错误: 第4行: invalid syntax

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/facades/factory.py').read()))"
```

## src/patterns/decorator.py
错误: 第87行: closing parenthesis ')' does not match opening parenthesis '[' on line 86

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/patterns/decorator.py').read()))"
```

## src/patterns/facade.py
错误: 第223行: closing parenthesis ')' does not match opening parenthesis '[' on line 222

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/patterns/facade.py').read()))"
```

## src/patterns/observer.py
错误: 第21行: unexpected indent

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/patterns/observer.py').read()))"
```

## src/patterns/facade_simple.py
错误: 第181行: closing parenthesis ')' does not match opening parenthesis '[' on line 180

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/patterns/facade_simple.py').read()))"
```

## src/patterns/adapter.py
错误: 第23行: illegal target for annotation

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/patterns/adapter.py').read()))"
```

## src/monitoring/alert_handlers.py
错误: 第139行: closing parenthesis ')' does not match opening parenthesis '['

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/monitoring/alert_handlers.py').read()))"
```

## src/monitoring/metrics_exporter.py
错误: 第47行: invalid syntax

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/monitoring/metrics_exporter.py').read()))"
```

## src/monitoring/anomaly_detector.py
错误: 第52行: invalid syntax

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/monitoring/anomaly_detector.py').read()))"
```

## src/monitoring/alert_manager_mod/__init__.py
错误: 第172行: closing parenthesis ')' does not match opening parenthesis '[' on line 171

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/monitoring/alert_manager_mod/__init__.py').read()))"
```

## src/performance/profiler.py
错误: 第200行: closing parenthesis ')' does not match opening parenthesis '[' on line 199

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/performance/profiler.py').read()))"
```

## src/performance/middleware.py
错误: 第258行: closing parenthesis '}' does not match opening parenthesis '[' on line 254

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/performance/middleware.py').read()))"
```

## src/performance/api.py
错误: 第45行: illegal target for annotation

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/performance/api.py').read()))"
```

## src/performance/analyzer.py
错误: 第115行: closing parenthesis '}' does not match opening parenthesis '[' on line 114

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/performance/analyzer.py').read()))"
```

## src/performance/integration.py
错误: 第205行: expected 'except' or 'finally' block

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/performance/integration.py').read()))"
```

## src/ml/model_training.py
错误: 第117行: closing parenthesis ')' does not match opening parenthesis '[' on line 116

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/ml/model_training.py').read()))"
```

## src/models/prediction_model.py
错误: 第5行: invalid syntax

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/models/prediction_model.py').read()))"
```

## src/models/common_models.py
错误: 第6行: invalid syntax

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/models/common_models.py').read()))"
```

## src/models/metrics_exporter.py
错误: 第137行: invalid syntax

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/models/metrics_exporter.py').read()))"
```

## src/models/prediction.py
错误: 第21行: illegal target for annotation

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/models/prediction.py').read()))"
```

## src/models/base_models.py
错误: 第16行: illegal target for annotation

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/models/base_models.py').read()))"
```

## src/decorators/service.py
错误: 第57行: closing parenthesis ')' does not match opening parenthesis '[' on line 56

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/decorators/service.py').read()))"
```

## src/decorators/base.py
错误: 第147行: closing parenthesis '}' does not match opening parenthesis '['

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/decorators/base.py').read()))"
```

## src/decorators/factory.py
错误: 第24行: illegal target for annotation

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/decorators/factory.py').read()))"
```

## src/decorators/decorators.py
错误: 第277行: closing parenthesis ')' does not match opening parenthesis '[' on line 275

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/decorators/decorators.py').read()))"
```

## src/decorators/implementations/logging.py
错误: 第25行: invalid syntax

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/decorators/implementations/logging.py').read()))"
```

## src/realtime/websocket.py
错误: 第117行: closing parenthesis ')' does not match opening parenthesis '[' on line 116

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/realtime/websocket.py').read()))"
```

## src/domain/user.py
错误: 第14行: illegal target for annotation

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/domain/user.py').read()))"
```

## src/domain/models/league.py
错误: 第4行: invalid syntax

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/domain/models/league.py').read()))"
```

## src/domain/models/prediction.py
错误: 第426行: unterminated triple-quoted string literal (detected at line 466)

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/domain/models/prediction.py').read()))"
```

## src/domain/models/team.py
错误: 第243行: closing parenthesis ')' does not match opening parenthesis '[' on line 242

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/domain/models/team.py').read()))"
```

## src/domain/models/match.py
错误: 第4行: invalid syntax

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/domain/models/match.py').read()))"
```

## src/domain/strategies/config.py
错误: 第303行: closing parenthesis ')' does not match opening parenthesis '[' on line 302

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/domain/strategies/config.py').read()))"
```

## src/domain/strategies/base.py
错误: 第113行: closing parenthesis ')' does not match opening parenthesis '[' on line 112

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/domain/strategies/base.py').read()))"
```

## src/domain/strategies/historical.py
错误: 第207行: closing parenthesis '}' does not match opening parenthesis '[' on line 206

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/domain/strategies/historical.py').read()))"
```

## src/domain/strategies/ensemble.py
错误: 第98行: closing parenthesis ')' does not match opening parenthesis '[' on line 74

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/domain/strategies/ensemble.py').read()))"
```

## src/domain/strategies/statistical.py
错误: 第6行: invalid syntax

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/domain/strategies/statistical.py').read()))"
```

## src/domain/strategies/ml_model.py
错误: 第4行: invalid syntax

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/domain/strategies/ml_model.py').read()))"
```

## src/domain/strategies/factory.py
错误: 第45行: closing parenthesis ')' does not match opening parenthesis '['

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/domain/strategies/factory.py').read()))"
```

## src/domain/services/prediction_service.py
错误: 第37行: invalid syntax

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/domain/services/prediction_service.py').read()))"
```

## src/domain/services/match_service.py
错误: 第31行: invalid syntax

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/domain/services/match_service.py').read()))"
```

## src/domain/services/scoring_service.py
错误: 第18行: closing parenthesis ')' does not match opening parenthesis '['

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/domain/services/scoring_service.py').read()))"
```

## src/domain/services/team_service.py
错误: 第87行: unmatched '}'

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/domain/services/team_service.py').read()))"
```

## src/domain/events/base.py
错误: 第56行: unterminated string literal (detected at line 56)

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/domain/events/base.py').read()))"
```

## src/domain/events/prediction_events.py
错误: 第4行: invalid syntax

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/domain/events/prediction_events.py').read()))"
```

## src/domain/events/match_events.py
错误: 第39行: invalid syntax

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/domain/events/match_events.py').read()))"
```

## src/cqrs/queries.py
错误: 第21行: invalid syntax

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/cqrs/queries.py').read()))"
```

## src/cqrs/dto.py
错误: 第4行: invalid syntax

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/cqrs/dto.py').read()))"
```

## src/cqrs/commands.py
错误: 第22行: invalid syntax

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/cqrs/commands.py').read()))"
```

## src/cqrs/base.py
错误: 第25行: illegal target for annotation

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/cqrs/base.py').read()))"
```

## src/cqrs/bus.py
错误: 第139行: illegal target for annotation

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/cqrs/bus.py').read()))"
```

## src/cqrs/handlers.py
错误: 第284行: expected 'except' or 'finally' block

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/cqrs/handlers.py').read()))"
```

## src/cqrs/application.py
错误: 第6行: invalid syntax

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/cqrs/application.py').read()))"
```

## src/streaming/kafka_components.py
错误: 第43行: illegal target for annotation

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/streaming/kafka_components.py').read()))"
```

## src/streaming/kafka_consumer_simple.py
错误: 第76行: closing parenthesis '}' does not match opening parenthesis '[' on line 67

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/streaming/kafka_consumer_simple.py').read()))"
```

## src/streaming/stream_config.py
错误: 第22行: illegal target for annotation

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/streaming/stream_config.py').read()))"
```

## src/streaming/stream_processor_simple.py
错误: 第119行: closing parenthesis '}' does not match opening parenthesis '['

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/streaming/stream_processor_simple.py').read()))"
```

## src/streaming/stream_config_simple.py
错误: 第110行: invalid syntax

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/streaming/stream_config_simple.py').read()))"
```

## src/streaming/kafka_producer_simple.py
错误: 第51行: closing parenthesis '}' does not match opening parenthesis '[' on line 50

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/streaming/kafka_producer_simple.py').read()))"
```

## src/streaming/kafka_components_simple.py
错误: 第133行: closing parenthesis '}' does not match opening parenthesis '['

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/streaming/kafka_components_simple.py').read()))"
```

## src/database/config.py
错误: 第12行: illegal target for annotation

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/database/config.py').read()))"
```

## src/database/base.py
错误: 第62行: illegal target for annotation

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/database/base.py').read()))"
```

## src/database/pool_config.py
错误: 第45行: invalid syntax

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/database/pool_config.py').read()))"
```

## src/database/query_optimizer.py
错误: 第23行: illegal target for annotation

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/database/query_optimizer.py').read()))"
```

## src/database/compatibility.py
错误: 第244行: unterminated triple-quoted string literal (detected at line 245)

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/database/compatibility.py').read()))"
```

## src/database/repositories/base.py
错误: 第32行: closing parenthesis ')' does not match opening parenthesis '[' on line 31

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/database/repositories/base.py').read()))"
```

## src/database/repositories/prediction.py
错误: 第126行: closing parenthesis ')' does not match opening parenthesis '[' on line 125

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/database/repositories/prediction.py').read()))"
```

## src/database/repositories/user.py
错误: 第71行: closing parenthesis ')' does not match opening parenthesis '[' on line 69

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/database/repositories/user.py').read()))"
```

## src/database/repositories/match.py
错误: 第489行: closing parenthesis '}' does not match opening parenthesis '[' on line 488

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/database/repositories/match.py').read()))"
```

## src/database/models/audit_log.py
错误: 第265行: invalid syntax

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/database/models/audit_log.py').read()))"
```

## src/database/models/features.py
错误: 第60行: illegal target for annotation

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/database/models/features.py').read()))"
```

## src/database/models/data_collection_log.py
错误: 第138行: invalid syntax

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/database/models/data_collection_log.py').read()))"
```

## src/database/models/predictions.py
错误: 第64行: illegal target for annotation

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/database/models/predictions.py').read()))"
```

## src/database/models/raw_data.py
错误: 第32行: illegal target for annotation

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/database/models/raw_data.py').read()))"
```

## src/database/models/odds.py
错误: 第79行: illegal target for annotation

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/database/models/odds.py').read()))"
```

## src/database/models/match.py
错误: 第71行: illegal target for annotation

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/database/models/match.py').read()))"
```

## src/database/migrations/versions/d3bf28af22ff_add_performance_critical_indexes.py
错误: 第18行: invalid decimal literal

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/database/migrations/versions/d3bf28af22ff_add_performance_critical_indexes.py').read()))"
```

## src/database/migrations/versions/d6d814cc1078_database_performance_optimization_.py
错误: 第23行: unexpected indent

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/database/migrations/versions/d6d814cc1078_database_performance_optimization_.py').read()))"
```

## src/database/migrations/versions/09d03cebf664_implement_partitioned_tables_and_indexes.py
错误: 第13行: invalid decimal literal

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/database/migrations/versions/09d03cebf664_implement_partitioned_tables_and_indexes.py').read()))"
```

## src/database/migrations/versions/006_add_missing_database_indexes.py
错误: 第25行: unexpected indent

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/database/migrations/versions/006_add_missing_database_indexes.py').read()))"
```

## src/database/migrations/versions/a20f91c49306_add_business_constraints.py
错误: 第21行: unexpected indent

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/database/migrations/versions/a20f91c49306_add_business_constraints.py').read()))"
```

## src/database/migrations/versions/f48d412852cc_add_data_collection_logs_and_bronze_layer_tables.py
错误: 第17行: unexpected indent

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/database/migrations/versions/f48d412852cc_add_data_collection_logs_and_bronze_layer_tables.py').read()))"
```

## src/database/migrations/versions/c1d8ae5075f0_add_jsonb_sqlite_compatibility.py
错误: 第27行: unexpected indent

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/database/migrations/versions/c1d8ae5075f0_add_jsonb_sqlite_compatibility.py').read()))"
```

## src/database/migrations/versions/9ac2aff86228_merge_multiple_migration_heads.py
错误: 第4行: invalid decimal literal

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/database/migrations/versions/9ac2aff86228_merge_multiple_migration_heads.py').read()))"
```

## src/database/migrations/versions/002_add_raw_scores_data_and_upgrade_jsonb.py
错误: 第17行: unexpected indent

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/database/migrations/versions/002_add_raw_scores_data_and_upgrade_jsonb.py').read()))"
```

## src/database/migrations/versions/d56c8d0d5aa0_initial_database_schema.py
错误: 第7行: leading zeros in decimal integer literals are not permitted; use an 0o prefix for octal integers

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/database/migrations/versions/d56c8d0d5aa0_initial_database_schema.py').read()))"
```

## src/cache/mock_redis.py
错误: 第211行: closing parenthesis ')' does not match opening parenthesis '['

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/cache/mock_redis.py').read()))"
```

## src/cache/consistency_manager.py
错误: 第125行: invalid syntax

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/cache/consistency_manager.py').read()))"
```

## src/cache/optimizer.py
错误: 第39行: illegal target for annotation

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/cache/optimizer.py').read()))"
```

## src/cache/examples.py
错误: 第100行: closing parenthesis ')' does not match opening parenthesis '['

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/cache/examples.py').read()))"
```

## src/cache/decorators.py
错误: 第42行: closing parenthesis ')' does not match opening parenthesis '[' on line 39

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/cache/decorators.py').read()))"
```

## src/cache/redis/__init__.py
错误: 第58行: illegal target for annotation

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/cache/redis/__init__.py').read()))"
```

## src/cache/redis/warmup/warmup_manager.py
错误: 第25行: closing parenthesis ')' does not match opening parenthesis '[' on line 24

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/cache/redis/warmup/warmup_manager.py').read()))"
```

## src/cache/ttl_cache_enhanced/async_cache.py
错误: 第26行: invalid syntax

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/cache/ttl_cache_enhanced/async_cache.py').read()))"
```

## src/cache/ttl_cache_enhanced/cache_factory.py
错误: 第25行: invalid syntax

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/cache/ttl_cache_enhanced/cache_factory.py').read()))"
```

## src/cache/ttl_cache_enhanced/ttl_cache.py
错误: 第35行: invalid syntax

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/cache/ttl_cache_enhanced/ttl_cache.py').read()))"
```

## src/cache/ttl_cache_enhanced/cache_entry.py
错误: 第24行: invalid syntax

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/cache/ttl_cache_enhanced/cache_entry.py').read()))"
```

## src/domain_simple/league.py
错误: 第23行: cannot assign to subscript here. Maybe you meant '==' instead of '='?

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/domain_simple/league.py').read()))"
```

## src/domain_simple/prediction.py
错误: 第35行: invalid syntax

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/domain_simple/prediction.py').read()))"
```

## src/domain_simple/user.py
错误: 第66行: invalid syntax

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/domain_simple/user.py').read()))"
```

## src/domain_simple/odds.py
错误: 第71行: invalid syntax

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/domain_simple/odds.py').read()))"
```

## src/domain_simple/team.py
错误: 第63行: invalid syntax

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/domain_simple/team.py').read()))"
```

## src/domain_simple/rules.py
错误: 第68行: closing parenthesis ']' does not match opening parenthesis '(' on line 65

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/domain_simple/rules.py').read()))"
```

## src/domain_simple/services.py
错误: 第27行: illegal target for annotation

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/domain_simple/services.py').read()))"
```

## src/domain_simple/match.py
错误: 第37行: invalid syntax

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/domain_simple/match.py').read()))"
```

## src/collectors/scores_collector_improved.py
错误: 第409行: closing parenthesis '}' does not match opening parenthesis '[' on line 408

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/collectors/scores_collector_improved.py').read()))"
```

## src/collectors/fixtures_collector.py
错误: 第141行: closing parenthesis ')' does not match opening parenthesis '[' on line 130

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/collectors/fixtures_collector.py').read()))"
```

## src/core/config.py
错误: 第79行: illegal target for annotation

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/core/config.py').read()))"
```

## src/core/service_lifecycle.py
错误: 第42行: illegal target for annotation

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/core/service_lifecycle.py').read()))"
```

## src/core/auto_binding.py
错误: 第30行: illegal target for annotation

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/core/auto_binding.py').read()))"
```

## src/core/di_setup.py
错误: 第32行: invalid syntax

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/core/di_setup.py').read()))"
```

## src/core/config_di.py
错误: 第29行: illegal target for annotation

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/core/config_di.py').read()))"
```

## src/core/di.py
错误: 第41行: illegal target for annotation

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/core/di.py').read()))"
```

## src/core/event_application.py
错误: 第130行: illegal target for annotation

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/core/event_application.py').read()))"
```

## src/core/tracing.py
错误: 第35行: invalid syntax

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/core/tracing.py').read()))"
```

## src/core/logging/advanced_filters.py
错误: 第35行: unterminated string literal (detected at line 35)

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/core/logging/advanced_filters.py').read()))"
```

## src/core/prediction/config/__init__.py
错误: 第14行: illegal target for annotation

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/core/prediction/config/__init__.py').read()))"
```

## src/observers/subjects.py
错误: 第48行: invalid syntax

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/observers/subjects.py').read()))"
```

## src/observers/base.py
错误: 第38行: illegal target for annotation

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/observers/base.py').read()))"
```

## src/observers/observers.py
错误: 第271行: invalid syntax

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/observers/observers.py').read()))"
```

## src/observers/manager.py
错误: 第267行: invalid syntax

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/observers/manager.py').read()))"
```

## src/services/enhanced_core.py
错误: 第25行: closing parenthesis ')' does not match opening parenthesis '[' on line 24

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/services/enhanced_core.py').read()))"
```

## src/services/audit_service.py
错误: 第4行: invalid syntax

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/services/audit_service.py').read()))"
```

## src/services/data_processing.py
错误: 第206行: closing parenthesis ')' does not match opening parenthesis '[' on line 205

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/services/data_processing.py').read()))"
```

## src/services/content_analysis.py
错误: 第58行: invalid syntax

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/services/content_analysis.py').read()))"
```

## src/services/event_prediction_service.py
错误: 第133行: closing parenthesis ')' does not match opening parenthesis '[' on line 132

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/services/event_prediction_service.py').read()))"
```

## src/services/strategy_prediction_service.py
错误: 第143行: closing parenthesis ')' does not match opening parenthesis '[' on line 142

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/services/strategy_prediction_service.py').read()))"
```

## src/services/base_unified.py
错误: 第156行: invalid syntax

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/services/base_unified.py').read()))"
```

## src/services/audit/__init__.py
错误: 第42行: closing parenthesis ')' does not match opening parenthesis '[' on line 41

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/services/audit/__init__.py').read()))"
```

## src/services/audit_service_mod/audit_service.py
错误: 第24行: invalid syntax

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/services/audit_service_mod/audit_service.py').read()))"
```

## src/services/audit_service_mod/__init__.py
错误: 第4行: invalid syntax

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/services/audit_service_mod/__init__.py').read()))"
```

## src/services/audit_service_mod/models.py
错误: 第38行: illegal target for annotation

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/services/audit_service_mod/models.py').read()))"
```

## src/services/processing/processors/match_processor.py
错误: 第298行: closing parenthesis ')' does not match opening parenthesis '[' on line 296

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/services/processing/processors/match_processor.py').read()))"
```

## src/services/processing/validators/data_validator.py
错误: 第39行: closing parenthesis '}' does not match opening parenthesis '[' on line 36

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/services/processing/validators/data_validator.py').read()))"
```

## src/services/processing/caching/processing_cache.py
错误: 第398行: closing parenthesis ')' does not match opening parenthesis '['

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/services/processing/caching/processing_cache.py').read()))"
```

## src/services/processing/caching/config/cache_config.py
错误: 第14行: illegal target for annotation

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/services/processing/caching/config/cache_config.py').read()))"
```

## src/features/feature_store.py
错误: 第74行: closing parenthesis ')' does not match opening parenthesis '[' on line 73

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/features/feature_store.py').read()))"
```

## src/features/feature_calculator.py
错误: 第46行: closing parenthesis ')' does not match opening parenthesis '['

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/features/feature_calculator.py').read()))"
```

## src/features/entities.py
错误: 第23行: illegal target for annotation

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/features/entities.py').read()))"
```

## src/features/feature_definitions.py
错误: 第29行: illegal target for annotation

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/features/feature_definitions.py').read()))"
```

## src/tasks/streaming_tasks.py
错误: 第54行: closing parenthesis ')' does not match opening parenthesis '[' on line 51

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/tasks/streaming_tasks.py').read()))"
```

## src/tasks/utils.py
错误: 第5行: invalid syntax

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/tasks/utils.py').read()))"
```

## src/tasks/data_collection_core.py
错误: 第158行: invalid syntax

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/tasks/data_collection_core.py').read()))"
```

## src/tasks/error_logger.py
错误: 第42行: invalid syntax

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/tasks/error_logger.py').read()))"
```

## src/tasks/monitoring.py
错误: 第332行: illegal target for annotation

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/tasks/monitoring.py').read()))"
```

## src/tasks/backup/executor/backup_executor.py
错误: 第35行: closing parenthesis ')' does not match opening parenthesis '[' on line 34

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/tasks/backup/executor/backup_executor.py').read()))"
```

## src/tasks/backup/manual/validators.py
错误: 第69行: closing parenthesis ')' does not match opening parenthesis '['

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/tasks/backup/manual/validators.py').read()))"
```

## src/tasks/backup/manual/utilities.py
错误: 第23行: invalid syntax

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/tasks/backup/manual/utilities.py').read()))"
```

## src/tasks/backup/cleanup/backup_cleaner.py
错误: 第36行: invalid syntax

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/tasks/backup/cleanup/backup_cleaner.py').read()))"
```

## src/data/storage/lake.py
错误: 第209行: closing parenthesis '}' does not match opening parenthesis '[' on line 207

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/data/storage/lake.py').read()))"
```

## src/data/processing/missing_data_handler.py
错误: 第46行: illegal target for annotation

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/data/processing/missing_data_handler.py').read()))"
```

## src/data/processing/football_data_cleaner.py
错误: 第5行: invalid syntax

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/data/processing/football_data_cleaner.py').read()))"
```

## src/data/quality/data_quality_monitor.py
错误: 第60行: closing parenthesis '}' does not match opening parenthesis '[' on line 58

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/data/quality/data_quality_monitor.py').read()))"
```

## src/data/quality/great_expectations_config.py
错误: 第199行: closing parenthesis '}' does not match opening parenthesis '[' on line 198

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/data/quality/great_expectations_config.py').read()))"
```

## src/data/quality/anomaly_detector.py
错误: 第44行: closing parenthesis ')' does not match opening parenthesis '[' on line 43

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/data/quality/anomaly_detector.py').read()))"
```

## src/data/quality/prometheus.py
错误: 第41行: illegal target for annotation

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/data/quality/prometheus.py').read()))"
```

## src/data/quality/exception_handler.py
错误: 第5行: invalid syntax

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/data/quality/exception_handler.py').read()))"
```

## src/data/quality/exception_handler_mod/__init__.py
错误: 第74行: closing parenthesis ')' does not match opening parenthesis '[' on line 73

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/data/quality/exception_handler_mod/__init__.py').read()))"
```

## src/data/collectors/scores_collector.py
错误: 第115行: closing parenthesis ')' does not match opening parenthesis '[' on line 112

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/data/collectors/scores_collector.py').read()))"
```

## src/data/collectors/odds_collector.py
错误: 第75行: closing parenthesis ')' does not match opening parenthesis '[' on line 73

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/data/collectors/odds_collector.py').read()))"
```

## src/data/collectors/base_collector.py
错误: 第130行: closing parenthesis ')' does not match opening parenthesis '[' on line 129

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/data/collectors/base_collector.py').read()))"
```

## src/data/collectors/fixtures_collector.py
错误: 第60行: closing parenthesis ')' does not match opening parenthesis '[' on line 56

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/data/collectors/fixtures_collector.py').read()))"
```

## src/data/features/feature_store.py
错误: 第73行: closing parenthesis ')' does not match opening parenthesis '[' on line 72

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/data/features/feature_store.py').read()))"
```

## src/data/features/examples.py
错误: 第237行: invalid syntax

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/data/features/examples.py').read()))"
```

## src/data/features/feature_definitions.py
错误: 第61行: unterminated string literal (detected at line 61)

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/data/features/feature_definitions.py').read()))"
```

## src/lineage/lineage_reporter.py
错误: 第58行: closing parenthesis ')' does not match opening parenthesis '[' on line 53

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/lineage/lineage_reporter.py').read()))"
```

## src/scheduler/recovery_handler.py
错误: 第50行: closing parenthesis ')' does not match opening parenthesis '[' on line 49

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/scheduler/recovery_handler.py').read()))"
```

## src/scheduler/job_manager.py
错误: 第87行: closing parenthesis '}' does not match opening parenthesis '[' on line 86

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/scheduler/job_manager.py').read()))"
```

## src/events/base.py
错误: 第29行: invalid syntax

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/events/base.py').read()))"
```

## src/events/bus.py
错误: 第54行: expected an indented block after 'if' statement on line 53

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/events/bus.py').read()))"
```

## src/events/handlers.py
错误: 第255行: invalid syntax

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/events/handlers.py').read()))"
```

## src/events/types.py
错误: 第22行: invalid syntax

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/events/types.py').read()))"
```

## src/security/key_manager.py
错误: 第168行: illegal target for annotation

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/security/key_manager.py').read()))"
```

## src/security/secret_manager.py
错误: 第224行: illegal target for annotation

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/security/secret_manager.py').read()))"
```

## src/security/auth.py
错误: 第116行: invalid syntax

修复建议:
```bash
# 使用Python检查详细错误
python -c "import ast; print(ast.parse(open('src/security/auth.py').read()))"
```
