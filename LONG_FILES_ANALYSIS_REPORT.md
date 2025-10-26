
📊 长文件分析报告 - Issue #87
=============================

发现 233 个需要关注的长文件 (> 100 行)

优先级分布:
- Critical: 17 个文件
- High: 58 个文件
- Medium: 98 个文件
- Low: 60 个文件

详细分析:
--------------------------------------------------

1. total
   行数: 84773
   优先级: HIGH
   错误: [Errno 2] No such file or directory: 'total'

2. src/monitoring/anomaly_detector.py
   行数: 761
   优先级: CRITICAL
   类数: 4
   函数数: 0
   复杂度: 68
   拆分建议:
     - 文件过长(>500行)，建议立即拆分
     - 类'AnomalyDetector'过于复杂，建议拆分为多个类
     - 监控模块建议按监控类型拆分（异常检测、性能监控、指标收集等）

3. src/performance/analyzer.py
   行数: 750
   优先级: CRITICAL
   类数: 3
   函数数: 0
   复杂度: 69
   拆分建议:
     - 文件过长(>500行)，建议立即拆分
     - 类'PerformanceAnalyzer'过于复杂，建议拆分为多个类

4. src/scheduler/recovery_handler.py
   行数: 747
   优先级: CRITICAL
   类数: 4
   函数数: 0
   复杂度: 52
   拆分建议:
     - 文件过长(>500行)，建议立即拆分
     - 类'RecoveryHandler'过于复杂，建议拆分为多个类

5. src/features/feature_store.py
   行数: 722
   优先级: CRITICAL
   类数: 10
   函数数: 0
   复杂度: 53
   拆分建议:
     - 文件过长(>500行)，建议立即拆分
     - 类过多(10个)，建议按功能拆分到多个模块
     - 类'FootballFeatureStore'过于复杂，建议拆分为多个类

6. src/collectors/scores_collector_improved.py
   行数: 699
   优先级: CRITICAL
   类数: 2
   函数数: 1
   复杂度: 75
   拆分建议:
     - 文件过长(>500行)，建议立即拆分
     - 类'ScoresCollector'过于复杂，建议拆分为多个类

7. src/database/migrations/versions/d6d814cc1078_database_performance_optimization_.py
   行数: 693
   优先级: CRITICAL
   类数: 0
   函数数: 2
   复杂度: 13
   拆分建议:
     - 文件过长(>500行)，建议立即拆分

8. src/domain/strategies/historical.py
   行数: 674
   优先级: CRITICAL
   类数: 3
   函数数: 0
   复杂度: 87
   拆分建议:
     - 文件过长(>500行)，建议立即拆分
     - 类'HistoricalStrategy'过于复杂，建议拆分为多个类
     - 策略模块建议按策略类型拆分（历史策略、ML策略、统计策略等）

9. src/cache/decorators.py
   行数: 669
   优先级: CRITICAL
   类数: 3
   函数数: 14
   复杂度: 159
   拆分建议:
     - 文件过长(>500行)，建议立即拆分
     - 独立函数过多(14个)，建议按职责分组
     - 复杂度过高(159)，建议拆分复杂类和函数
     - 存在5个复杂函数，建议拆分或重构
     - 装饰器模块建议按功能拆分（缓存装饰器、验证装饰器、监控装饰器等）

10. src/domain/strategies/ensemble.py
   行数: 667
   优先级: CRITICAL
   类数: 4
   函数数: 0
   复杂度: 60
   拆分建议:
     - 文件过长(>500行)，建议立即拆分
     - 类'EnsembleStrategy'过于复杂，建议拆分为多个类
     - 策略模块建议按策略类型拆分（历史策略、ML策略、统计策略等）

11. src/facades/facades.py
   行数: 660
   优先级: CRITICAL
   类数: 10
   函数数: 0
   复杂度: 62
   拆分建议:
     - 文件过长(>500行)，建议立即拆分
     - 类过多(10个)，建议按功能拆分到多个模块

12. src/domain/strategies/config.py
   行数: 657
   优先级: CRITICAL
   类数: 7
   函数数: 0
   复杂度: 86
   拆分建议:
     - 文件过长(>500行)，建议立即拆分
     - 类过多(7个)，建议按功能拆分到多个模块
     - 类'StrategyConfigManager'过于复杂，建议拆分为多个类
     - 策略模块建议按策略类型拆分（历史策略、ML策略、统计策略等）

13. src/decorators/decorators.py
   行数: 636
   优先级: CRITICAL
   类数: 8
   函数数: 0
   复杂度: 103
   拆分建议:
     - 文件过长(>500行)，建议立即拆分
     - 类过多(8个)，建议按功能拆分到多个模块
     - 复杂度过高(103)，建议拆分复杂类和函数
     - 类'LoggingDecorator'过于复杂，建议拆分为多个类
     - 装饰器模块建议按功能拆分（缓存装饰器、验证装饰器、监控装饰器等）

14. src/adapters/football.py
   行数: 618
   优先级: CRITICAL
   类数: 13
   函数数: 0
   复杂度: 97
   拆分建议:
     - 文件过长(>500行)，建议立即拆分
     - 类过多(13个)，建议按功能拆分到多个模块

15. src/api/adapters.py
   行数: 618
   优先级: CRITICAL
   类数: 0
   函数数: 0
   复杂度: 0
   拆分建议:
     - 文件过长(>500行)，建议立即拆分

16. src/api/facades.py
   行数: 615
   优先级: CRITICAL
   类数: 0
   函数数: 0
   复杂度: 0
   拆分建议:
     - 文件过长(>500行)，建议立即拆分

17. src/features/feature_calculator.py
   行数: 605
   优先级: CRITICAL
   类数: 1
   函数数: 0
   复杂度: 69
   拆分建议:
     - 文件过长(>500行)，建议立即拆分
     - 类'FeatureCalculator'过于复杂，建议拆分为多个类

18. src/patterns/facade.py
   行数: 601
   优先级: CRITICAL
   类数: 7
   函数数: 0
   复杂度: 32
   拆分建议:
     - 文件过长(>500行)，建议立即拆分
     - 类过多(7个)，建议按功能拆分到多个模块

19. src/database/repositories/prediction.py
   行数: 591
   优先级: HIGH
   类数: 2
   函数数: 0
   复杂度: 47
   拆分建议:
     - 文件过长(>500行)，建议立即拆分
     - 类'PredictionRepository'过于复杂，建议拆分为多个类

20. src/monitoring/metrics_exporter.py
   行数: 578
   优先级: HIGH
   类数: 1
   函数数: 2
   复杂度: 49
   拆分建议:
     - 文件过长(>500行)，建议立即拆分
     - 类'MetricsExporter'过于复杂，建议拆分为多个类
     - 监控模块建议按监控类型拆分（异常检测、性能监控、指标收集等）

21. src/performance/api.py
   行数: 573
   优先级: HIGH
   类数: 3
   函数数: 0
   复杂度: 3
   拆分建议:
     - 文件过长(>500行)，建议立即拆分

22. src/events/types.py
   行数: 557
   优先级: HIGH
   类数: 15
   函数数: 0
   复杂度: 49
   拆分建议:
     - 文件过长(>500行)，建议立即拆分
     - 类过多(15个)，建议按功能拆分到多个模块

23. src/ml/model_training.py
   行数: 556
   优先级: HIGH
   类数: 5
   函数数: 1
   复杂度: 32
   拆分建议:
     - 文件过长(>500行)，建议立即拆分

24. src/cqrs/handlers.py
   行数: 555
   优先级: HIGH
   类数: 14
   函数数: 0
   复杂度: 56
   拆分建议:
     - 文件过长(>500行)，建议立即拆分
     - 类过多(14个)，建议按功能拆分到多个模块

25. src/core/service_lifecycle.py
   行数: 555
   优先级: HIGH
   类数: 4
   函数数: 4
   复杂度: 95
   拆分建议:
     - 文件过长(>500行)，建议立即拆分
     - 类'ServiceLifecycleManager'过于复杂，建议拆分为多个类

26. src/config/openapi_config.py
   行数: 550
   优先级: HIGH
   类数: 1
   函数数: 1
   复杂度: 10
   拆分建议:
     - 文件过长(>500行)，建议立即拆分

27. src/api/repositories.py
   行数: 549
   优先级: HIGH
   类数: 0
   函数数: 0
   复杂度: 0
   拆分建议:
     - 文件过长(>500行)，建议立即拆分

28. src/performance/profiler.py
   行数: 544
   优先级: HIGH
   类数: 7
   函数数: 10
   复杂度: 74
   拆分建议:
     - 文件过长(>500行)，建议立即拆分
     - 类过多(7个)，建议按功能拆分到多个模块

29. src/observers/observers.py
   行数: 539
   优先级: HIGH
   类数: 4
   函数数: 0
   复杂度: 66
   拆分建议:
     - 文件过长(>500行)，建议立即拆分

30. src/domain/strategies/factory.py
   行数: 537
   优先级: HIGH
   类数: 3
   函数数: 0
   复杂度: 68
   拆分建议:
     - 文件过长(>500行)，建议立即拆分
     - 类'PredictionStrategyFactory'过于复杂，建议拆分为多个类
     - 策略模块建议按策略类型拆分（历史策略、ML策略、统计策略等）

31. src/patterns/adapter.py
   行数: 535
   优先级: HIGH
   类数: 11
   函数数: 0
   复杂度: 70
   拆分建议:
     - 文件过长(>500行)，建议立即拆分
     - 类过多(11个)，建议按功能拆分到多个模块

32. src/database/repositories/match.py
   行数: 525
   优先级: HIGH
   类数: 1
   函数数: 0
   复杂度: 35
   拆分建议:
     - 文件过长(>500行)，建议立即拆分
     - 类'MatchRepository'过于复杂，建议拆分为多个类

33. src/data/quality/great_expectations_config.py
   行数: 525
   优先级: HIGH
   类数: 3
   函数数: 0
   复杂度: 25
   拆分建议:
     - 文件过长(>500行)，建议立即拆分

34. src/scheduler/job_manager.py
   行数: 515
   优先级: HIGH
   类数: 3
   函数数: 0
   复杂度: 38
   拆分建议:
     - 文件过长(>500行)，建议立即拆分

35. src/repositories/match.py
   行数: 512
   优先级: HIGH
   类数: 4
   函数数: 0
   复杂度: 55
   拆分建议:
     - 文件过长(>500行)，建议立即拆分
     - 类'MatchRepository'过于复杂，建议拆分为多个类

36. src/observers/subjects.py
   行数: 507
   优先级: HIGH
   类数: 4
   函数数: 0
   复杂度: 47
   拆分建议:
     - 文件过长(>500行)，建议立即拆分

37. src/data/collectors/base_collector.py
   行数: 506
   优先级: HIGH
   类数: 2
   函数数: 0
   复杂度: 31
   拆分建议:
     - 文件过长(>500行)，建议立即拆分

38. src/data/features/feature_store.py
   行数: 506
   优先级: HIGH
   类数: 1
   函数数: 2
   复杂度: 46
   拆分建议:
     - 文件过长(>500行)，建议立即拆分
     - 类'FootballFeatureStore'过于复杂，建议拆分为多个类

39. src/database/models/predictions.py
   行数: 503
   优先级: HIGH
   类数: 2
   函数数: 0
   复杂度: 36
   拆分建议:
     - 文件过长(>500行)，建议立即拆分
     - 类'Predictions'过于复杂，建议拆分为多个类

40. src/database/migrations/versions/d56c8d0d5aa0_initial_database_schema.py
   行数: 498
   优先级: HIGH
   类数: 0
   函数数: 2
   复杂度: 2

41. src/domain/strategies/statistical.py
   行数: 495
   优先级: HIGH
   类数: 1
   函数数: 0
   复杂度: 46
   拆分建议:
     - 类'StatisticalStrategy'过于复杂，建议拆分为多个类
     - 策略模块建议按策略类型拆分（历史策略、ML策略、统计策略等）

42. src/patterns/facade_simple.py
   行数: 492
   优先级: HIGH
   类数: 8
   函数数: 0
   复杂度: 31
   拆分建议:
     - 类过多(8个)，建议按功能拆分到多个模块

43. src/data/collectors/scores_collector.py
   行数: 490
   优先级: HIGH
   类数: 3
   函数数: 0
   复杂度: 35
   拆分建议:
     - 类'ScoresCollector'过于复杂，建议拆分为多个类

44. src/database/repositories/user.py
   行数: 480
   优先级: HIGH
   类数: 1
   函数数: 0
   复杂度: 26

45. src/tasks/monitoring.py
   行数: 479
   优先级: HIGH
   类数: 1
   函数数: 0
   复杂度: 36
   拆分建议:
     - 类'TaskMonitor'过于复杂，建议拆分为多个类
     - 监控模块建议按监控类型拆分（异常检测、性能监控、指标收集等）

46. src/services/processing/validators/data_validator.py
   行数: 476
   优先级: HIGH
   类数: 1
   函数数: 0
   复杂度: 64
   拆分建议:
     - 类'DataValidator'过于复杂，建议拆分为多个类

47. src/services/strategy_prediction_service.py
   行数: 475
   优先级: HIGH
   类数: 1
   函数数: 1
   复杂度: 25

48. src/domain/strategies/ml_model.py
   行数: 471
   优先级: HIGH
   类数: 1
   函数数: 0
   复杂度: 50
   拆分建议:
     - 类'MLModelStrategy'过于复杂，建议拆分为多个类
     - 策略模块建议按策略类型拆分（历史策略、ML策略、统计策略等）

49. src/domain/models/prediction.py
   行数: 468
   优先级: HIGH
   类数: 5
   函数数: 0
   复杂度: 80
   拆分建议:
     - 类'Prediction'过于复杂，建议拆分为多个类

50. src/data/features/examples.py
   行数: 468
   优先级: HIGH
   类数: 0
   函数数: 11
   复杂度: 17
   拆分建议:
     - 独立函数过多(11个)，建议按职责分组

51. src/database/models/audit_log.py
   行数: 467
   优先级: HIGH
   类数: 4
   函数数: 0
   复杂度: 37
   拆分建议:
     - 类'AuditLog'过于复杂，建议拆分为多个类

52. src/config/config_manager.py
   行数: 465
   优先级: HIGH
   类数: 6
   函数数: 5
   复杂度: 81
   拆分建议:
     - 类过多(6个)，建议按功能拆分到多个模块
     - 类'ConfigManager'过于复杂，建议拆分为多个类

53. src/domain/models/team.py
   行数: 464
   优先级: HIGH
   类数: 4
   函数数: 0
   复杂度: 97
   拆分建议:
     - 类'Team'过于复杂，建议拆分为多个类

54. src/tasks/backup/executor/backup_executor.py
   行数: 462
   优先级: HIGH
   类数: 1
   函数数: 0
   复杂度: 46
   拆分建议:
     - 类'BackupExecutor'过于复杂，建议拆分为多个类

55. src/services/event_prediction_service.py
   行数: 458
   优先级: HIGH
   类数: 3
   函数数: 1
   复杂度: 17

56. src/tasks/streaming_tasks.py
   行数: 458
   优先级: HIGH
   类数: 1
   函数数: 6
   复杂度: 35

57. src/domain/models/league.py
   行数: 457
   优先级: HIGH
   类数: 5
   函数数: 0
   复杂度: 96
   拆分建议:
     - 类'League'过于复杂，建议拆分为多个类

58. src/database/migrations/versions/004_configure_database_permissions.py
   行数: 456
   优先级: HIGH
   类数: 0
   函数数: 2
   复杂度: 9

59. src/data/quality/data_quality_monitor.py
   行数: 454
   优先级: HIGH
   类数: 1
   函数数: 0
   复杂度: 33
   拆分建议:
     - 类'DataQualityMonitor'过于复杂，建议拆分为多个类

60. src/database/repositories/base.py
   行数: 453
   优先级: HIGH
   类数: 1
   函数数: 0
   复杂度: 32
   拆分建议:
     - 类'BaseRepository'过于复杂，建议拆分为多个类

61. src/database/migrations/versions/09d03cebf664_implement_partitioned_tables_and_indexes.py
   行数: 449
   优先级: HIGH
   类数: 0
   函数数: 12
   复杂度: 44
   拆分建议:
     - 独立函数过多(12个)，建议按职责分组

62. src/core/di.py
   行数: 442
   优先级: HIGH
   类数: 5
   函数数: 6
   复杂度: 76
   拆分建议:
     - 类'DIContainer'过于复杂，建议拆分为多个类

63. src/patterns/decorator.py
   行数: 433
   优先级: HIGH
   类数: 8
   函数数: 7
   复杂度: 67
   拆分建议:
     - 类过多(8个)，建议按功能拆分到多个模块

64. src/data/collectors/odds_collector.py
   行数: 432
   优先级: HIGH
   类数: 1
   函数数: 0
   复杂度: 37
   拆分建议:
     - 类'OddsCollector'过于复杂，建议拆分为多个类

65. src/lineage/lineage_reporter.py
   行数: 431
   优先级: HIGH
   类数: 1
   函数数: 0
   复杂度: 30

66. src/performance/middleware.py
   行数: 429
   优先级: HIGH
   类数: 4
   函数数: 0
   复杂度: 51

67. src/cache/ttl_cache_enhanced/ttl_cache.py
   行数: 429
   优先级: HIGH
   类数: 1
   函数数: 0
   复杂度: 63
   拆分建议:
     - 类'TTLCache'过于复杂，建议拆分为多个类

68. src/core/config_di.py
   行数: 421
   优先级: HIGH
   类数: 4
   函数数: 3
   复杂度: 57
   拆分建议:
     - 类'ConfigurationBinder'过于复杂，建议拆分为多个类

69. src/data/collectors/fixtures_collector.py
   行数: 420
   优先级: HIGH
   类数: 1
   函数数: 0
   复杂度: 22

70. src/tasks/maintenance_tasks.py
   行数: 414
   优先级: HIGH
   类数: 0
   函数数: 4
   复杂度: 26
   拆分建议:
     - 存在1个复杂函数，建议拆分或重构

71. src/services/processing/caching/processing_cache.py
   行数: 412
   优先级: HIGH
   类数: 1
   函数数: 0
   复杂度: 48
   拆分建议:
     - 类'ProcessingCache'过于复杂，建议拆分为多个类

72. src/api/data_router.py
   行数: 407
   优先级: HIGH
   类数: 6
   函数数: 0
   复杂度: 6
   拆分建议:
     - 类过多(6个)，建议按功能拆分到多个模块

73. src/monitoring/alert_manager_mod/__init__.py
   行数: 406
   优先级: HIGH
   类数: 16
   函数数: 0
   复杂度: 80
   拆分建议:
     - 类过多(16个)，建议按功能拆分到多个模块
     - 监控模块建议按监控类型拆分（异常检测、性能监控、指标收集等）

74. src/security/middleware.py
   行数: 406
   优先级: HIGH
   类数: 5
   函数数: 1
   复杂度: 48

75. src/events/bus.py
   行数: 402
   优先级: HIGH
   类数: 1
   函数数: 5
   复杂度: 51
   拆分建议:
     - 类'EventBus'过于复杂，建议拆分为多个类

76. src/observers/manager.py
   行数: 398
   优先级: MEDIUM
   类数: 1
   函数数: 1
   复杂度: 44
   拆分建议:
     - 类'ObserverManager'过于复杂，建议拆分为多个类

77. src/database/migrations/versions/d3bf28af22ff_add_performance_critical_indexes.py
   行数: 396
   优先级: MEDIUM
   类数: 0
   函数数: 7
   复杂度: 28

78. src/events/handlers.py
   行数: 394
   优先级: MEDIUM
   类数: 6
   函数数: 0
   复杂度: 43
   拆分建议:
     - 类过多(6个)，建议按功能拆分到多个模块

79. src/domain_simple/services.py
   行数: 385
   优先级: MEDIUM
   类数: 6
   函数数: 1
   复杂度: 60
   拆分建议:
     - 类过多(6个)，建议按功能拆分到多个模块

80. src/database/models/odds.py
   行数: 380
   优先级: MEDIUM
   类数: 2
   函数数: 0
   复杂度: 47
   拆分建议:
     - 类'Odds'过于复杂，建议拆分为多个类

81. src/stubs/mocks/confluent_kafka.py
   行数: 379
   优先级: MEDIUM
   类数: 9
   函数数: 3
   复杂度: 92
   拆分建议:
     - 类过多(9个)，建议按功能拆分到多个模块

82. src/api/decorators.py
   行数: 378
   优先级: MEDIUM
   类数: 0
   函数数: 0
   复杂度: 0
   拆分建议:
     - 装饰器模块建议按功能拆分（缓存装饰器、验证装饰器、监控装饰器等）

83. src/utils/date_utils.py
   行数: 375
   优先级: MEDIUM
   类数: 1
   函数数: 4
   复杂度: 84
   拆分建议:
     - 类'DateUtils'过于复杂，建议拆分为多个类

84. src/core/auto_binding.py
   行数: 375
   优先级: MEDIUM
   类数: 3
   函数数: 6
   复杂度: 86
   拆分建议:
     - 类'AutoBinder'过于复杂，建议拆分为多个类

85. src/models/prediction_model.py
   行数: 374
   优先级: MEDIUM
   类数: 4
   函数数: 3
   复杂度: 28

86. src/adapters/registry.py
   行数: 372
   优先级: MEDIUM
   类数: 2
   函数数: 0
   复杂度: 53
   拆分建议:
     - 类'AdapterRegistry'过于复杂，建议拆分为多个类

87. src/database/models/match.py
   行数: 368
   优先级: MEDIUM
   类数: 3
   函数数: 0
   复杂度: 43
   拆分建议:
     - 类'Match'过于复杂，建议拆分为多个类

88. src/middleware/cors_config.py
   行数: 367
   优先级: MEDIUM
   类数: 6
   函数数: 4
   复杂度: 64
   拆分建议:
     - 类过多(6个)，建议按功能拆分到多个模块

89. src/services/processing/processors/match_processor.py
   行数: 367
   优先级: MEDIUM
   类数: 1
   函数数: 0
   复杂度: 44
   拆分建议:
     - 类'MatchProcessor'过于复杂，建议拆分为多个类

90. src/api/predictions/router.py
   行数: 365
   优先级: MEDIUM
   类数: 7
   函数数: 0
   复杂度: 7
   拆分建议:
     - 类过多(7个)，建议按功能拆分到多个模块

91. src/api/observers.py
   行数: 365
   优先级: MEDIUM
   类数: 2
   函数数: 0
   复杂度: 2

92. src/tasks/error_logger.py
   行数: 364
   优先级: MEDIUM
   类数: 1
   函数数: 0
   复杂度: 16

93. src/adapters/base.py
   行数: 358
   优先级: MEDIUM
   类数: 7
   函数数: 0
   复杂度: 34
   拆分建议:
     - 类过多(7个)，建议按功能拆分到多个模块

94. src/cqrs/application.py
   行数: 356
   优先级: MEDIUM
   类数: 5
   函数数: 0
   复杂度: 13

95. src/repositories/prediction.py
   行数: 355
   优先级: MEDIUM
   类数: 3
   函数数: 0
   复杂度: 45

96. src/repositories/user.py
   行数: 349
   优先级: MEDIUM
   类数: 3
   函数数: 0
   复杂度: 41

97. src/api/monitoring.py
   行数: 348
   优先级: MEDIUM
   类数: 0
   函数数: 2
   复杂度: 8
   拆分建议:
     - 监控模块建议按监控类型拆分（异常检测、性能监控、指标收集等）

98. src/observers/base.py
   行数: 347
   优先级: MEDIUM
   类数: 5
   函数数: 0
   复杂度: 48

99. src/domain_simple/rules.py
   行数: 342
   优先级: MEDIUM
   类数: 5
   函数数: 1
   复杂度: 69
   拆分建议:
     - 类'ValidationEngine'过于复杂，建议拆分为多个类

100. src/domain_simple/odds.py
   行数: 340
   优先级: MEDIUM
   类数: 5
   函数数: 0
   复杂度: 76
   拆分建议:
     - 类'Odds'过于复杂，建议拆分为多个类

101. src/stubs/mocks/feast.py
   行数: 337
   优先级: MEDIUM
   类数: 8
   函数数: 5
   复杂度: 60
   拆分建议:
     - 类过多(8个)，建议按功能拆分到多个模块
     - 类'MockFeatureStore'过于复杂，建议拆分为多个类

102. src/patterns/observer.py
   行数: 333
   优先级: MEDIUM
   类数: 7
   函数数: 1
   复杂度: 51
   拆分建议:
     - 类过多(7个)，建议按功能拆分到多个模块

103. src/core/config.py
   行数: 329
   优先级: MEDIUM
   类数: 3
   函数数: 3
   复杂度: 25

104. src/tasks/data_collection_core.py
   行数: 327
   优先级: MEDIUM
   类数: 1
   函数数: 11
   复杂度: 41
   拆分建议:
     - 独立函数过多(11个)，建议按职责分组

105. src/monitoring/apm_integration.py
   行数: 325
   优先级: MEDIUM
   类数: 3
   函数数: 9
   复杂度: 43
   拆分建议:
     - 监控模块建议按监控类型拆分（异常检测、性能监控、指标收集等）

106. src/domain_simple/user.py
   行数: 324
   优先级: MEDIUM
   类数: 5
   函数数: 0
   复杂度: 55

107. src/facades/factory.py
   行数: 322
   优先级: MEDIUM
   类数: 2
   函数数: 0
   复杂度: 47
   拆分建议:
     - 类'FacadeFactory'过于复杂，建议拆分为多个类

108. src/realtime/websocket.py
   行数: 321
   优先级: MEDIUM
   类数: 4
   函数数: 1
   复杂度: 29

109. src/domain/models/match.py
   行数: 321
   优先级: MEDIUM
   类数: 4
   函数数: 0
   复杂度: 67
   拆分建议:
     - 类'Match'过于复杂，建议拆分为多个类

110. src/database/models/team.py
   行数: 321
   优先级: MEDIUM
   类数: 2
   函数数: 0
   复杂度: 28

111. src/tasks/backup/manual/utilities.py
   行数: 321
   优先级: MEDIUM
   类数: 3
   函数数: 0
   复杂度: 46
   拆分建议:
     - 类'BackupFileManager'过于复杂，建议拆分为多个类

112. src/services/base_unified.py
   行数: 318
   优先级: MEDIUM
   类数: 2
   函数数: 0
   复杂度: 29

113. src/cqrs/commands.py
   行数: 317
   优先级: MEDIUM
   类数: 7
   函数数: 0
   复杂度: 43
   拆分建议:
     - 类过多(7个)，建议按功能拆分到多个模块

114. src/database/models/raw_data.py
   行数: 315
   优先级: MEDIUM
   类数: 4
   函数数: 0
   复杂度: 51

115. src/database/migrations/versions/005_create_audit_logs_table.py
   行数: 315
   优先级: MEDIUM
   类数: 0
   函数数: 2
   复杂度: 7

116. src/performance/integration.py
   行数: 314
   优先级: MEDIUM
   类数: 1
   函数数: 6
   复杂度: 44
   拆分建议:
     - 类'PerformanceMonitoringIntegration'过于复杂，建议拆分为多个类

117. src/data/processing/missing_data_handler.py
   行数: 314
   优先级: MEDIUM
   类数: 1
   函数数: 0
   复杂度: 40
   拆分建议:
     - 类'MissingDataHandler'过于复杂，建议拆分为多个类

118. src/monitoring/health_checker.py
   行数: 312
   优先级: MEDIUM
   类数: 2
   函数数: 0
   复杂度: 44
   拆分建议:
     - 类'HealthChecker'过于复杂，建议拆分为多个类
     - 监控模块建议按监控类型拆分（异常检测、性能监控、指标收集等）

119. src/collectors/fixtures_collector.py
   行数: 311
   优先级: MEDIUM
   类数: 2
   函数数: 0
   复杂度: 24

120. src/data/quality/exception_handler_mod/__init__.py
   行数: 311
   优先级: MEDIUM
   类数: 15
   函数数: 0
   复杂度: 75
   拆分建议:
     - 类过多(15个)，建议按功能拆分到多个模块

121. src/services/content_analysis.py
   行数: 307
   优先级: MEDIUM
   类数: 6
   函数数: 0
   复杂度: 48
   拆分建议:
     - 类过多(6个)，建议按功能拆分到多个模块
     - 类'ContentAnalysisService'过于复杂，建议拆分为多个类

122. src/api/cqrs.py
   行数: 305
   优先级: MEDIUM
   类数: 5
   函数数: 4
   复杂度: 9

123. src/decorators/factory.py
   行数: 302
   优先级: MEDIUM
   类数: 4
   函数数: 0
   复杂度: 34
   拆分建议:
     - 装饰器模块建议按功能拆分（缓存装饰器、验证装饰器、监控装饰器等）

124. src/features/feature_definitions.py
   行数: 299
   优先级: MEDIUM
   类数: 5
   函数数: 0
   复杂度: 25

125. src/domain/services/prediction_service.py
   行数: 298
   优先级: MEDIUM
   类数: 1
   函数数: 0
   复杂度: 44
   拆分建议:
     - 类'PredictionDomainService'过于复杂，建议拆分为多个类

126. src/events/base.py
   行数: 295
   优先级: MEDIUM
   类数: 7
   函数数: 0
   复杂度: 44
   拆分建议:
     - 类过多(7个)，建议按功能拆分到多个模块

127. src/streaming/kafka_components_simple.py
   行数: 294
   优先级: MEDIUM
   类数: 6
   函数数: 0
   复杂度: 31
   拆分建议:
     - 类过多(6个)，建议按功能拆分到多个模块

128. src/cache/examples.py
   行数: 289
   优先级: MEDIUM
   类数: 1
   函数数: 9
   复杂度: 17

129. src/dependencies/optional.py
   行数: 289
   优先级: MEDIUM
   类数: 1
   函数数: 12
   复杂度: 31
   拆分建议:
     - 独立函数过多(12个)，建议按职责分组

130. src/adapters/factory.py
   行数: 288
   优先级: MEDIUM
   类数: 3
   函数数: 0
   复杂度: 41
   拆分建议:
     - 类'AdapterFactory'过于复杂，建议拆分为多个类

131. src/main.py
   行数: 288
   优先级: MEDIUM
   类数: 0
   函数数: 0
   复杂度: 0

132. src/facades/base.py
   行数: 285
   优先级: MEDIUM
   类数: 4
   函数数: 0
   复杂度: 37

133. src/decorators/service.py
   行数: 283
   优先级: MEDIUM
   类数: 1
   函数数: 8
   复杂度: 48
   拆分建议:
     - 类'DecoratorService'过于复杂，建议拆分为多个类
     - 装饰器模块建议按功能拆分（缓存装饰器、验证装饰器、监控装饰器等）

134. src/streaming/stream_processor_simple.py
   行数: 281
   优先级: MEDIUM
   类数: 3
   函数数: 0
   复杂度: 45
   拆分建议:
     - 类'StreamProcessor'过于复杂，建议拆分为多个类

135. src/api/app.py
   行数: 280
   优先级: MEDIUM
   类数: 1
   函数数: 0
   复杂度: 2

136. src/database/migrations/versions/f48d412852cc_add_data_collection_logs_and_bronze_layer_tables.py
   行数: 280
   优先级: MEDIUM
   类数: 0
   函数数: 2
   复杂度: 8

137. src/database/migrations/versions/002_add_raw_scores_data_and_upgrade_jsonb.py
   行数: 279
   优先级: MEDIUM
   类数: 0
   函数数: 2
   复杂度: 14

138. src/decorators/base.py
   行数: 278
   优先级: MEDIUM
   类数: 7
   函数数: 0
   复杂度: 46
   拆分建议:
     - 类过多(7个)，建议按功能拆分到多个模块
     - 装饰器模块建议按功能拆分（缓存装饰器、验证装饰器、监控装饰器等）

139. src/services/enhanced_core.py
   行数: 278
   优先级: MEDIUM
   类数: 5
   函数数: 0
   复杂度: 36

140. src/tasks/backup/manual/validators.py
   行数: 277
   优先级: MEDIUM
   类数: 1
   函数数: 0
   复杂度: 50
   拆分建议:
     - 类'BackupValidator'过于复杂，建议拆分为多个类

141. src/streaming/stream_config_simple.py
   行数: 274
   优先级: MEDIUM
   类数: 4
   函数数: 0
   复杂度: 58

142. src/tasks/backup/cleanup/backup_cleaner.py
   行数: 273
   优先级: MEDIUM
   类数: 1
   函数数: 0
   复杂度: 34
   拆分建议:
     - 类'BackupCleaner'过于复杂，建议拆分为多个类

143. src/cache/mock_redis.py
   行数: 270
   优先级: MEDIUM
   类数: 2
   函数数: 8
   复杂度: 43

144. src/cqrs/queries.py
   行数: 266
   优先级: MEDIUM
   类数: 8
   函数数: 0
   复杂度: 43
   拆分建议:
     - 类过多(8个)，建议按功能拆分到多个模块

145. src/services/data_processing.py
   行数: 265
   优先级: MEDIUM
   类数: 12
   函数数: 0
   复杂度: 40
   拆分建议:
     - 类过多(12个)，建议按功能拆分到多个模块

146. src/tasks/celery_app.py
   行数: 265
   优先级: MEDIUM
   类数: 3
   函数数: 0
   复杂度: 10

147. src/models/metrics_exporter.py
   行数: 262
   优先级: MEDIUM
   类数: 1
   函数数: 0
   复杂度: 17

148. src/database/migrations/versions/006_add_missing_database_indexes.py
   行数: 262
   优先级: MEDIUM
   类数: 0
   函数数: 2
   复杂度: 16
   拆分建议:
     - 存在1个复杂函数，建议拆分或重构

149. src/domain_simple/team.py
   行数: 262
   优先级: MEDIUM
   类数: 2
   函数数: 0
   复杂度: 48
   拆分建议:
     - 类'Team'过于复杂，建议拆分为多个类

150. src/scheduler/celery_config.py
   行数: 260
   优先级: MEDIUM
   类数: 2
   函数数: 4
   复杂度: 9

151. src/monitoring/system_metrics.py
   行数: 258
   优先级: MEDIUM
   类数: 1
   函数数: 0
   复杂度: 16
   拆分建议:
     - 监控模块建议按监控类型拆分（异常检测、性能监控、指标收集等）

152. src/database/migrations/versions/007_improve_phase3_implementations.py
   行数: 253
   优先级: MEDIUM
   类数: 0
   函数数: 2
   复杂度: 6

153. src/domain/services/scoring_service.py
   行数: 250
   优先级: MEDIUM
   类数: 1
   函数数: 0
   复杂度: 38
   拆分建议:
     - 类'ScoringService'过于复杂，建议拆分为多个类

154. src/tasks/utils.py
   行数: 250
   优先级: MEDIUM
   类数: 0
   函数数: 3
   复杂度: 10

155. src/data/storage/lake.py
   行数: 246
   优先级: MEDIUM
   类数: 5
   函数数: 0
   复杂度: 48

156. src/database/compatibility.py
   行数: 245
   优先级: MEDIUM
   类数: 3
   函数数: 0
   复杂度: 24

157. src/database/migrations/versions/a20f91c49306_add_business_constraints.py
   行数: 242
   优先级: MEDIUM
   类数: 0
   函数数: 2
   复杂度: 4

158. src/domain_simple/prediction.py
   行数: 241
   优先级: MEDIUM
   类数: 3
   函数数: 0
   复杂度: 38
   拆分建议:
     - 类'Prediction'过于复杂，建议拆分为多个类

159. src/repositories/base.py
   行数: 230
   优先级: MEDIUM
   类数: 5
   函数数: 0
   复杂度: 37

160. src/domain/strategies/base.py
   行数: 228
   优先级: MEDIUM
   类数: 6
   函数数: 0
   复杂度: 19
   拆分建议:
     - 类过多(6个)，建议按功能拆分到多个模块
     - 策略模块建议按策略类型拆分（历史策略、ML策略、统计策略等）

161. src/cache/redis/__init__.py
   行数: 228
   优先级: MEDIUM
   类数: 1
   函数数: 8
   复杂度: 20

162. src/utils/string_utils.py
   行数: 227
   优先级: MEDIUM
   类数: 1
   函数数: 3
   复杂度: 42
   拆分建议:
     - 类'StringUtils'过于复杂，建议拆分为多个类

163. src/cache/ttl_cache_enhanced/async_cache.py
   行数: 227
   优先级: MEDIUM
   类数: 1
   函数数: 0
   复杂度: 6

164. src/monitoring/alert_handlers.py
   行数: 221
   优先级: MEDIUM
   类数: 6
   函数数: 0
   复杂度: 27
   拆分建议:
     - 类过多(6个)，建议按功能拆分到多个模块
     - 监控模块建议按监控类型拆分（异常检测、性能监控、指标收集等）

165. src/api/features.py
   行数: 211
   优先级: MEDIUM
   类数: 0
   函数数: 4
   复杂度: 11

166. src/data/quality/exception_handler.py
   行数: 211
   优先级: MEDIUM
   类数: 14
   函数数: 0
   复杂度: 39
   拆分建议:
     - 类过多(14个)，建议按功能拆分到多个模块

167. src/api/events.py
   行数: 209
   优先级: MEDIUM
   类数: 0
   函数数: 1
   复杂度: 4

168. src/cqrs/bus.py
   行数: 205
   优先级: MEDIUM
   类数: 5
   函数数: 2
   复杂度: 31

169. src/tasks/backup/tasks/backup_tasks.py
   行数: 205
   优先级: MEDIUM
   类数: 1
   函数数: 0
   复杂度: 12

170. src/api/middleware.py
   行数: 204
   优先级: MEDIUM
   类数: 8
   函数数: 0
   复杂度: 27
   拆分建议:
     - 类过多(8个)，建议按功能拆分到多个模块

171. src/domain/services/match_service.py
   行数: 203
   优先级: MEDIUM
   类数: 1
   函数数: 0
   复杂度: 38
   拆分建议:
     - 类'MatchDomainService'过于复杂，建议拆分为多个类

172. src/core/di_setup.py
   行数: 203
   优先级: MEDIUM
   类数: 1
   函数数: 5
   复杂度: 35

173. src/security/key_manager.py
   行数: 203
   优先级: MEDIUM
   类数: 1
   函数数: 5
   复杂度: 23

174. src/services/user_profile.py
   行数: 199
   优先级: LOW
   类数: 3
   函数数: 0
   复杂度: 25

175. src/database/dependencies.py
   行数: 198
   优先级: LOW
   类数: 0
   函数数: 4
   复杂度: 8

176. src/data/features/feature_definitions.py
   行数: 189
   优先级: LOW
   类数: 5
   函数数: 0
   复杂度: 10

177. src/streaming/kafka_consumer_simple.py
   行数: 188
   优先级: LOW
   类数: 2
   函数数: 0
   复杂度: 32
   拆分建议:
     - 类'KafkaMessageConsumer'过于复杂，建议拆分为多个类

178. src/cqrs/dto.py
   行数: 186
   优先级: LOW
   类数: 6
   函数数: 0
   复杂度: 13
   拆分建议:
     - 类过多(6个)，建议按功能拆分到多个模块

179. src/database/models/data_collection_log.py
   行数: 186
   优先级: LOW
   类数: 3
   函数数: 0
   复杂度: 19

180. src/tasks/backup/__init__.py
   行数: 186
   优先级: LOW
   类数: 1
   函数数: 16
   复杂度: 19
   拆分建议:
     - 独立函数过多(16个)，建议按职责分组

181. src/repositories/provider.py
   行数: 185
   优先级: LOW
   类数: 3
   函数数: 6
   复杂度: 32

182. src/cache/ttl_cache_enhanced/cache_factory.py
   行数: 185
   优先级: LOW
   类数: 1
   函数数: 0
   复杂度: 15

183. src/utils/_retry/__init__.py
   行数: 183
   优先级: LOW
   类数: 4
   函数数: 6
   复杂度: 30

184. src/domain/services/team_service.py
   行数: 180
   优先级: LOW
   类数: 5
   函数数: 0
   复杂度: 33

185. src/api/predictions/models.py
   行数: 178
   优先级: LOW
   类数: 17
   函数数: 0
   复杂度: 17
   拆分建议:
     - 类过多(17个)，建议按功能拆分到多个模块

186. src/domain_simple/match.py
   行数: 177
   优先级: LOW
   类数: 3
   函数数: 0
   复杂度: 33
   拆分建议:
     - 类'Match'过于复杂，建议拆分为多个类

187. src/domain/events/prediction_events.py
   行数: 176
   优先级: LOW
   类数: 6
   函数数: 0
   复杂度: 18
   拆分建议:
     - 类过多(6个)，建议按功能拆分到多个模块

188. src/database/migrations/versions/c1d8ae5075f0_add_jsonb_sqlite_compatibility.py
   行数: 173
   优先级: LOW
   类数: 0
   函数数: 6
   复杂度: 20

189. src/api/dependencies.py
   行数: 171
   优先级: LOW
   类数: 1
   函数数: 2
   复杂度: 5

190. src/database/models/data_quality_log.py
   行数: 171
   优先级: LOW
   类数: 1
   函数数: 0
   复杂度: 12

191. src/services/audit_service.py
   行数: 170
   优先级: LOW
   类数: 9
   函数数: 0
   复杂度: 24
   拆分建议:
     - 类过多(9个)，建议按功能拆分到多个模块

192. src/models/raw_data.py
   行数: 168
   优先级: LOW
   类数: 12
   函数数: 0
   复杂度: 12
   拆分建议:
     - 类过多(12个)，建议按功能拆分到多个模块

193. src/database/definitions.py
   行数: 168
   优先级: LOW
   类数: 3
   函数数: 13
   复杂度: 31
   拆分建议:
     - 独立函数过多(13个)，建议按职责分组

194. src/cache/__init__.py
   行数: 167
   优先级: LOW
   类数: 0
   函数数: 3
   复杂度: 3

195. src/decorators/implementations/logging.py
   行数: 166
   优先级: LOW
   类数: 1
   函数数: 0
   复杂度: 32
   拆分建议:
     - 类'LoggingDecorator'过于复杂，建议拆分为多个类

196. src/database/migrations/env.py
   行数: 165
   优先级: LOW
   类数: 0
   函数数: 3
   复杂度: 4

197. src/streaming/stream_config.py
   行数: 164
   优先级: LOW
   类数: 3
   函数数: 0
   复杂度: 12

198. src/api/health/utils.py
   行数: 159
   优先级: LOW
   类数: 1
   函数数: 0
   复杂度: 7

199. src/domain_simple/league.py
   行数: 159
   优先级: LOW
   类数: 3
   函数数: 0
   复杂度: 22

200. src/tasks/backup/metrics/backup_metrics.py
   行数: 159
   优先级: LOW
   类数: 0
   函数数: 3
   复杂度: 6

201. src/core/event_application.py
   行数: 156
   优先级: LOW
   类数: 2
   函数数: 1
   复杂度: 14

202. src/utils/crypto_utils.py
   行数: 155
   优先级: LOW
   类数: 1
   函数数: 0
   复杂度: 33
   拆分建议:
     - 类'CryptoUtils'过于复杂，建议拆分为多个类

203. src/database/config.py
   行数: 154
   优先级: LOW
   类数: 1
   函数数: 6
   复杂度: 24

204. src/database/types.py
   行数: 153
   优先级: LOW
   类数: 2
   函数数: 1
   复杂度: 27

205. src/utils/data_validator.py
   行数: 149
   优先级: LOW
   类数: 1
   函数数: 0
   复杂度: 29

206. src/tasks/backup_tasks.py
   行数: 149
   优先级: LOW
   类数: 0
   函数数: 0
   复杂度: 0

207. src/monitoring/alert_manager.py
   行数: 148
   优先级: LOW
   类数: 13
   函数数: 0
   复杂度: 18
   拆分建议:
     - 类过多(13个)，建议按功能拆分到多个模块

208. src/database/models/features.py
   行数: 147
   优先级: LOW
   类数: 5
   函数数: 0
   复杂度: 8

209. src/cache/consistency_manager.py
   行数: 147
   优先级: LOW
   类数: 2
   函数数: 0
   复杂度: 16

210. src/streaming/stream_processor.py
   行数: 145
   优先级: LOW
   类数: 4
   函数数: 0
   复杂度: 20

211. src/adapters/registry_simple.py
   行数: 139
   优先级: LOW
   类数: 1
   函数数: 2
   复杂度: 34
   拆分建议:
     - 类'AdapterRegistry'过于复杂，建议拆分为多个类

212. src/models/common_models.py
   行数: 139
   优先级: LOW
   类数: 4
   函数数: 0
   复杂度: 11

213. src/models/prediction.py
   行数: 139
   优先级: LOW
   类数: 6
   函数数: 0
   复杂度: 24
   拆分建议:
     - 类过多(6个)，建议按功能拆分到多个模块

214. src/streaming/kafka_producer_simple.py
   行数: 136
   优先级: LOW
   类数: 1
   函数数: 0
   复杂度: 19

215. src/cqrs/base.py
   行数: 129
   优先级: LOW
   类数: 8
   函数数: 0
   复杂度: 18
   拆分建议:
     - 类过多(8个)，建议按功能拆分到多个模块

216. src/database/connection.py
   行数: 129
   优先级: LOW
   类数: 0
   函数数: 0
   复杂度: 0

217. src/services/manager/manager.py
   行数: 127
   优先级: LOW
   类数: 1
   函数数: 1
   复杂度: 19

218. src/services/manager.py
   行数: 127
   优先级: LOW
   类数: 1
   函数数: 1
   复杂度: 19

219. src/core/exceptions.py
   行数: 126
   优先级: LOW
   类数: 28
   函数数: 0
   复杂度: 29
   拆分建议:
     - 类过多(28个)，建议按功能拆分到多个模块

220. src/api/health/__init__.py
   行数: 123
   优先级: LOW
   类数: 0
   函数数: 1
   复杂度: 1

221. src/collectors/scores_collector.py
   行数: 123
   优先级: LOW
   类数: 2
   函数数: 0
   复杂度: 11

222. src/core/logging.py
   行数: 120
   优先级: LOW
   类数: 2
   函数数: 4
   复杂度: 17

223. src/models/prediction_service.py
   行数: 118
   优先级: LOW
   类数: 0
   函数数: 0
   复杂度: 0

224. src/tasks/backup/tasks/task_definitions.py
   行数: 118
   优先级: LOW
   类数: 0
   函数数: 2
   复杂度: 7

225. src/features/entities.py
   行数: 117
   优先级: LOW
   类数: 4
   函数数: 0
   复杂度: 13

226. src/database/base.py
   行数: 116
   优先级: LOW
   类数: 3
   函数数: 0
   复杂度: 15

227. src/monitoring/metrics_collector_enhanced.py
   行数: 113
   优先级: LOW
   类数: 3
   函数数: 3
   复杂度: 18

228. src/data/processing/football_data_cleaner_mod/__init__.py
   行数: 112
   优先级: LOW
   类数: 2
   函数数: 0
   复杂度: 19

229. src/utils/file_utils.py
   行数: 110
   优先级: LOW
   类数: 1
   函数数: 0
   复杂度: 22

230. src/domain/__init__.py
   行数: 110
   优先级: LOW
   类数: 0
   函数数: 0
   复杂度: 0

231. src/cache/ttl_cache_enhanced/cache_entry.py
   行数: 106
   优先级: LOW
   类数: 1
   函数数: 0
   复杂度: 15

232. src/middleware/performance_monitoring.py
   行数: 105
   优先级: LOW
   类数: 2
   函数数: 0
   复杂度: 7

233. src/services/audit_service_mod/audit_service.py
   行数: 104
   优先级: LOW
   类数: 3
   函数数: 0
   复杂度: 18
