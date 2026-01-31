# [Genesis.Inventory] 源代码全量职能审计报告

**版本**: V1.0 (2026-01-31)
**审计范围**: `src/` 目录下所有核心文件
**文件总数**: 147+ 个文件
**架构版本**: [Golden Layout] V1.0

---

## 执行摘要

| 目录 | 文件数 | 状态 | 关键发现 |
|------|--------|------|----------|
| **src/collectors/** | 28 | ✅ 良好 | 版本演进有序，职责分离清晰 |
| **src/infrastructure/** | 8 | ⚠️ 需关注 | SurgicalInteraction.js 过大 (859行)，版本混入 |
| **src/ml/** | 66 | ⚠️ 需优化 | 存在数据加载器、模式定义重复 |
| **src/processors/** | 21 | ⚠️ 需优化 | 存在多个提取器版本重叠 |
| **src/bridge/** | 6 | 🚨 严重冗余 | JSExecutor 类重复定义 |
| **src/services/** | 19 | 🚨 严重冗余 | 多个服务功能重叠 |

---

## 冗余预警清单 [待清理]

### 🚨 严重冗余（需立即处理）

| 冗余类型 | 涉及文件 | 建议操作 |
|----------|----------|----------|
| **JSExecutor 重复定义** | `src/bridge/adapters/__init__.py` + `js_executor.py` | 统一到 `js_executor.py`，删除 `__init__.py` 中的实现 |
| **协议入口重复** | `src/bridge/protocols/__init__.py` + `schemas/__init__.py` | 删除 `protocols/` 目录，统一使用 `schemas/` |
| **数据采集重叠** | `src/services/collection_service.py` + `crawler_service.py` | 合并为单一采集服务 |
| **哈希对齐重叠** | `src/services/hash_alignment_service.py` + `match_aligner.py` + `match_linker.py` | 三文件功能高度重叠，需合并 |
| **推理/预测重叠** | `src/services/inference_service.py` + `prediction_service.py` | 合并为单一预测服务 |
| **配置文件重复** | `src/services/harvest_config.py` + `harvester_config.py` | 统一配置管理 |

### ⚠️ 中度冗余（建议优化）

| 冗余类型 | 涉及文件 | 建议操作 |
|----------|----------|----------|
| **数据加载器** | `src/ml/data/loader.py` + `postgres_loader.py` | 统一使用 `postgres_loader.py` |
| **特征模式** | `src/ml/feature_schema.py` + `models/feature_extraction_schema.py` | 统一模式定义 |
| **特征提取器** | `src/processors/v25_production_extractor.py` + `v26_sparsity_filter.py` + `ultimate_extractor.py` | 版本演进遗留，建议合并 |

---

## 详细审计报告

### [src/collectors/] - 数据采集层 (28 文件)

| 文件名 | 职能描述 | 生产版本/状态 | 备注 |
| :--- | :--- | :--- | :--- |
| **base_extractor.py** | V150.0 反爬虫基础类，集成 Ghost Protocol | 生产就绪 (V150.0) | 被 fotmob_core.py, lineup_collector.py 调用 |
| **fotmob_core.py** | V144.5 FotMob 核心数据采集器，自适应解码 | 生产就绪 (V144.5) | 被 main.py 调用 |
| **lineup_collector.py** | V41.284 阵容数据采集器，启发式路径发现 | 生产就绪 (V41.284) | 被 harvester_service.py 调用 |
| **v41_500_pipeline_integration.py** | V41.500 流水线集成器，自动集成 FeatureFactory | 生产就绪 (V41.500) | 被 main.py 调用 |
| **odds_models.py** | V41.570 赔率数据模型定义 | 生产就绪 (V41.570) | 被 odds_api_interceptor.py 调用 |
| **odds_api_interceptor.py** | V59.0 API 拦截器，直接提取赔率数据 | 生产就绪 (V59.0) | 被 temporal_sync_engine_v49.js 调用 |
| **circuit_breaker.py** | V26.7 采集熔断器，分类锁定 | 生产就绪 (V26.7) | 被 base_extractor.py 调用 |
| **collection_sentry.py** | V26.5 自动巡航哨兵，健康监控 | 生产就绪 (V26.5) | 被 main.py 调用 |
| **failover_collector.py** | 故障转移收集器 | 生产就绪 | 被 harvester_service.py 调用 |
| **levenshtein_matcher.py** | Levenshtein 距离匹配器 | 生产就绪 | 被 semantic_matcher.py 调用 |
| **semantic_matcher.py** | 语义匹配器，高级团队名称匹配 | 生产就绪 | 被 harvester_service.py 调用 |
| **semantic_refiner.py** | 语义精炼器，优化匹配结果 | 生产就绪 | 被 semantic_matcher.py 调用 |
| **market_data_engine.py** | 市场数据引擎 | 生产就绪 | 被 odds_production_extractor.py 调用 |
| **season_discoverer.py** | 赛季发现器，自动发现新赛季 | 生产就绪 | 被 main.py 调用 |
| **season_manifest_generator.py** | 赛季清单生成器 | 生产就绪 | 被 main.py 调用 |
| **proxy_health_manager.py** | 代理健康管理器 | 生产就绪 | 被 base_extractor.py 调用 |
| **resilience.py** | 弹性处理模块，重试和熔断 | 生产就绪 | 被 odds_api_interceptor.py 调用 |
| **rollback_manager.py** | 回滚管理器 | 生产就绪 | 被 harvester_service.py 调用 |
| **metadata_manager.py** | 元数据管理器 | 生产就绪 | 被 fotmob_core.py 调用 |
| **odds_api_client.py** | 赔率 API 客户端 | 生产就绪 | ⚠️ 与 odds_api_interceptor.py 部分重叠 |
| **bayesian_delay_engine.py** | 贝叶斯延迟引擎 | 生产就绪 | 被 harvester_service.py 调用 |
| **l3_feature_processor.py** | L3 特征处理器 | 生产就绪 | 被 main.py 调用 |
| **fotmob_historical_id_scanner.py** | FotMob 历史 ID 扫描器 | 生产就绪 | 被 main.py 调用 |
| **fotmob_league_registry.py** | FotMob 联赛注册表 | 生产就绪 | 被 main.py 调用 |
| **js_templates.py** | JavaScript 模板管理器 | 生产就绪 | 被 odds_api_interceptor.py 调用 |
| **prometheus_metrics.py** | Prometheus 指标收集器 | 生产就绪 | 被 harvester_service.py 调用 |
| **schemas/l1_match_schema.py** | L1 采集器 Pydantic Schema | 生产就绪 (V37.0) | Schema 定义 |
| **schemas/l2_match_schema.py** | L2 采集器 Pydantic Schema | 生产就绪 (V37.0) | 被 fotmob_core.py 调用 |

---

### [src/infrastructure/] - JavaScript 基础设施层 (8 文件)

| 文件名 | 职能描述 | 生产版本/状态 | 备注 |
| :--- | :--- | :--- | :--- |
| **engines/QuantHarvester.js** | V164.TitanSlayer 工业级量化价格轨迹收割机 | 生产就绪 (V164.TitanSlayer) | ⚠️ 与 SurgicalInteraction 模块存在逻辑共享 |
| **engines/parsers/TrajectoryParser.js** | V150.002 DOM-based 轨迹提取器 | 生产就绪 (V150.002) | 被 QuantHarvester.js 调用 |
| **engines/services/SurgicalInteraction.js** | V158.000 浏览器交互工具库 | 生产就绪 (V158.000) | 🚨 文件过大 (859行)，需拆分 |
| **engines/services/SignalRadar.js** | V141.000 网络流量监测器 | 生产就绪 (V141.000) | 被 QuantHarvester.js 调用 |
| **engines/services/TelemetryService.js** | V141.000 实时指标仪表板 | 生产就绪 (V141.000) | 被 QuantHarvester.js 调用 |
| **engines/selectors/OddsPortalSelectors.js** | V138.000 CSS 选择器中央管理 | 生产就绪 (V138.000) | 被 SurgicalInteraction.js 调用 |
| **engines/config/ModalSelectorConfig.js** | V148.000 Modal 选择器配置 | 生产就绪 (V148.000) | 被 SurgicalInteraction.js 调用 |
| **engines/config/ReactIndexConfig.js** | V146.000 React SPA 索引配置 | 生产就绪 (V146.000) | 配置文件 |

---

### [src/ml/] - 机器学习与推理层 (66 文件)

#### 推理模块 (inference/)

| 文件名 | 职能描述 | 生产版本/状态 | 备注 |
| :--- | :--- | :--- | :--- |
| **model_dispatcher.py** | V26.8 联赛专项模型分发器 | 生产就绪 (V26.8) | 被 engine.py, 外部代码调用 |
| **predictor.py** | 足球比赛预测器 | 生产就绪 (Phase 5) | 被 model_dispatcher.py 调用 |
| **model_loader.py** | 模型生命周期管理 | 生产就绪 | 被 predictor.py 调用 |
| **cache_manager.py** | 预测结果缓存管理器 | 生产就绪 | 被 predictor.py 调用 |

#### 特征工程 (feature_engine/)

| 文件名 | 职能描述 | 生产版本/状态 | 备注 |
| :--- | :--- | :--- | :--- |
| **engine.py** | 模块化特征工程框架 | 生产就绪 (V23.0) | 统一入口 |
| **base.py** | 基础处理器抽象 | 生产就绪 (V23.0) | 被所有 processors 调用 |
| **processors/atomic.py** | 原子特征处理器 | 生产就绪 (V23.0) | 基础特征计算 |
| **processors/context.py** | 比赛上下文特征处理器 | 生产就绪 (V23.0) | |
| **processors/history.py** | 历史特征处理器 | 生产就绪 (V23.0) | |
| **processors/injury_impact.py** | 战损与伤停深度处理器 (40+维) | 生产就绪 (V23.0) | |
| **processors/lineup.py** | 阵容特征处理器 | 生产就绪 (V23.0) | |
| **processors/lineup_value.py** | 阵容价值处理器 (50+维) | 生产就绪 (V22.0) | |
| **processors/market_odds.py** | 市场赔率与偏见处理器 (30+维) | 生产就绪 (V23.0) | |
| **processors/referee.py** | 裁判特征处理器 | 生产就绪 (V23.0) | |
| **processors/tactical.py** | 战术特征处理器 | 生产就绪 (V23.0) | |
| **processors/tactical_cross.py** | 战术交叉特征处理器 | 生产就绪 (V23.0) | |
| **processors/passing_dna.py** | 传球 DNA 深度处理器 (60+维) | 生产就绪 (V22.0) | |
| **models/match_schema.py** | 比赛数据模式定义 | 生产就绪 | Pydantic 模型 |
| **models/feature_extraction_schema.py** | 特征提取模式定义 | 生产就绪 | ⚠️ 与 feature_schema.py 重叠 |

#### 特征计算 (features/)

| 文件名 | 职能描述 | 生产版本/状态 | 备注 |
| :--- | :--- | :--- | :--- |
| **extractor.py** | 特征提取器 | 生产就绪 (V25.1) | 被 feature_engine/engine.py 调用 |
| **h2h_calculator.py** | 历史交锋计算器 | 生产就绪 (V25.1) | |
| **poisson_features.py** | 泊松分布特征计算 | 生产就绪 (V25.1) | |
| **prematch_features.py** | 赛前特征准备 | 生产就绪 (V25.1) | |
| **odds_movement_features.py** | 赔率变动特征计算 | 生产就绪 (V25.1) | |
| **value_bet_features.py** | 价值下注特征计算 | 生产就绪 (V25.1) | |
| **elo_rating_system.py** | ELO 评分系统实现 | 生产就绪 (V25.1) | |
| **standings_calculator.py** | 积分榜计算器 | 生产就绪 (V25.1) | |
| **venue_analyzer.py** | 场地分析器 | 生产就绪 (V25.1) | |
| **hash_resolver.py** | 哈希解析器，特征名称映射 | 生产就绪 (V25.1) | 被 feature_adapter.py 调用 |
| **l3_pre_match_extractor.py** | L3 赛前特征提取器 | 生产就绪 (V25.1) | |
| **advanced_feature_transformer.py** | 高级特征转换器 | 生产就绪 (V25.1) | |

#### 训练与回测

| 文件名 | 职能描述 | 生产版本/状态 | 备注 |
| :--- | :--- | :--- | :--- |
| **engine.py** | 向后兼容接口，已拆分到其他模块 | 生产就绪 (V26.8) | 仅作为兼容层 |
| **training/v17_engine.py** | V17.0 ML 训练引擎 | 生产就绪 (V17.0) | |
| **backtest_engine.py** | V36.0 生产级回测引擎 | 生产就绪 (V36.0) | |
| **backtest/fractional_kelly_backtest.py** | 分数式 Kelly 回测引擎 | 生产就绪 | |
| **backtest/v3_roi_backtest.py** | V3 ROI 回测引擎 | 生产就绪 | ⚠️ 与 fractional_kelly 版本重叠 |
| **models/xgboost_classifier.py** | XGBoost 分类器封装 | 生产就绪 | |
| **models/enhanced_xgboost_optimizer.py** | 增强 XGBoost 优化器 | 生产就绪 | ⚠️ 与基础分类器功能重叠 |
| **strategy/fractional_kelly.py** | 分数式 Kelly 策略 | 生产就绪 | |

#### 数据与配置

| 文件名 | 职能描述 | 生产版本/状态 | 备注 |
| :--- | :--- | :--- | :--- |
| **data/loader.py** | 数据加载器 | 生产就绪 | ⚠️ 与 postgres_loader.py 重叠 |
| **data/postgres_loader.py** | PostgreSQL 专用数据加载器 | 生产就绪 | 建议统一使用此文件 |
| **dataset/dataset_generator.py** | 数据集生成器 | 生产就绪 | |
| **dataset/target_labels.py** | 目标标签生成器 | 生产就绪 | |
| **feature_adapter.py** | 特征适配层 | 生产就绪 (V26.4) | 被 model_dispatcher.py 调用 |
| **feature_schema.py** | 特征模式定义 | 生产就绪 | ⚠️ 与 models/feature_extraction_schema.py 重叠 |
| **harvester_config.py** | 收割配置管理 | 生产就绪 | |
| **model_handler.py** | 模型处理器 | 生产就绪 | ⚠️ 与 model_loader.py 功能可能重叠 |
| **model_trainer.py** | 模型训练器 | 生产就绪 | |
| **mappers.py** | 数据映射器 | 生产就绪 | |
| **data_guard.py** | 数据守护器 | 生产就绪 | |
| **fault_tolerance.py** | 容错处理器 | 生产就绪 | |
| **shotmap_aggregator.py** | 射门图聚合器 | 生产就绪 | |
| **harvester_db.py** | 收割数据库操作 | 生产就绪 | |

---

### [src/processors/] - 数据工厂层 (21 文件)

| 文件名 | 职能描述 | 生产版本/状态 | 备注 |
| :--- | :--- | :--- | :--- |
| **base_processor.py** | V79.000 基础特征处理器抽象类 | 生产就绪 (V79.000) | 被所有处理器继承 |
| **feature_factory.py** | V41.500 自动化特征加工厂 | 生产就绪 (V41.500) | 被 main.py 调用 |
| **v41_380_golden_extractor.py** | V41.380 黄金特征提取器 | 生产就绪 (V41.380) | ⭐ 核心模块：身价/伤病/评分 |
| **ultimate_extractor.py** | V79.200 协调器模式 | 生产就绪 (V79.200) | ⚠️ 仅作为"协调者"，委托专用模块 |
| **v25_production_extractor.py** | V26.7 生产级收割流水线 | 生产就绪 (V26.7) | 零缺陷设计，支持 6346+ 维 |
| **path_resolver.py** | Schema-Agnostic 路径解析器 | 生产就绪 | 被 feature_factory.py 调用 |
| **fatigue_calculator.py** | 疲劳度计算器 | 生产就绪 | 被 ultimate_extractor.py 调用 |
| **injury_parser.py** | 伤病解析器 | 生产就绪 | |
| **odds_trend_analyzer.py** | 赔率动向分析器 | 生产就绪 | 被 ultimate_extractor.py 调用 |
| **rolling_feature_calculator.py** | 滚动特征计算器 | 生产就绪 | |
| **starting_11_delta.py** | 首发战力差计算器 | 生产就绪 | |
| **starting_quality_assessor.py** | 首发质量评估器 | 生产就绪 | 被 ultimate_extractor.py 调用 |
| **pre_match_feature_extractor.py** | 赛前特征提取器 | 生产就绪 | |
| **pure_feature_filter.py** | 纯净特征过滤器 | 生产就绪 | 被 ultimate_extractor.py 调用 |
| **v26_sparsity_filter.py** | V26 稀疏度过滤器 | 生产就绪 | ⚠️ 与 v25 生产提取器功能重叠 |
| **technical_parser.py** | 技术解析器 (PreMatchFeaturePlugin) | 生产就绪 | 被 ultimate_extractor.py 调用 |
| **feature_interaction_engine.py** | 特征交互引擎 | 生产就绪 | |
| **feature_manifest.py** | 特征清单 | 生产就绪 | |
| **base_extractor.py** | 基础提取器 | 生产就绪 | ⚠️ 与 collectors/base_extractor.py 名称冲突 |
| **extraction_decorators.py** | 提取装饰器 | 生产就绪 | |
| **integrity_guard.py** | 完整性守护 | 生产就绪 | |

---

### [src/bridge/] - 跨语言通信层 (6 文件)

| 文件名 | 职能描述 | 生产版本/状态 | 备注 |
| :--- | :--- | :--- | :--- |
| **adapters/js_executor.py** | JavaScript 执行器，调用 QuantHarvester.js | 生产就绪 (V1.0) | 被 production_harvest_batch.py 调用 |
| **schemas/harvest.py** | 收割任务数据结构定义 | 生产就绪 (V1.0) | 核心数据结构 |
| **schemas/__init__.py** | 数据结构层统一入口 | 生产就绪 (V1.0) | 导出所有 schemas |
| **protocols/__init__.py** | 协议层入口 | 生产就绪 (V1.0) | ⚠️ 与 schemas/__init__.py 功能重复 |
| **adapters/__init__.py** | 适配器入口 | 生产就绪 (V1.0) | 🚨 包含与 js_executor.py 重复的 JSExecutor 类 |
| **__init__.py** | 桥接模块统一入口 | 生产就绪 (V1.0) | 导出核心类和协议 |

---

### [src/services/] - 业务逻辑编排层 (19 文件)

| 文件名 | 职能描述 | 生产版本/状态 | 备注 |
| :--- | :--- | :--- | :--- |
| **base_service.py** | 基础服务抽象类 | 生产就绪 | 被 service_manager.py 调用 |
| **service_manager.py** | 服务生命周期管理器 | 生产就绪 | 被 main.py 调用 |
| **dependency_injection.py** | 依赖注入容器 | 生产就绪 | 被 service_container.py 调用 |
| **service_container.py** | 服务容器 | 生产就绪 | ⚠️ 主要用于测试 |
| **collection_service.py** | FotMob 数据收集服务 | 生产就绪 | 🚨 文件过大 (1843行)，需拆分 |
| **crawler_service.py** | 网页爬虫服务 | 生产就绪 (V41.83) | ⚠️ 与 collection_service 功能重叠 |
| **data_harvest_service.py** | 赔率数据收割服务 | 生产就绪 (V41.285) | ⚠️ 与 hash_alignment 重叠 |
| **event_bus.py** | 事件总线服务 | 生产就绪 (V38.0) | ⚠️ 版本较旧 |
| **explainability_service.py** | 预测可解释性服务 | 生产就绪 | 被 prediction_service.py 调用 |
| **harvest_config.py** | 反爬虫配置管理 | 生产就绪 (V41.66) | ⚠️ 与 harvester_config 重叠 |
| **harvester_config.py** | 收割器配置管理 | 生产就绪 (V41.262) | ⚠️ 与 harvest_config 重叠 |
| **hash_alignment_service.py** | 哈希对齐服务 | 生产就绪 (V41.50) | 🚨 文件过大 (2088行)，与 match_aligner/match_linker 重叠 |
| **inference_service.py** | 模型推理服务 | 生产就绪 | ⚠️ 与 prediction_service 功能重叠 |
| **league_router.py** | 联赛路由服务 | 生产就绪 (V41.243) | |
| **match_aligner.py** | 比赛对齐服务 | 生产就绪 (V41.186) | ⚠️ 与 hash_alignment/match_linker 重叠 |
| **match_linker.py** | 比赛链接服务 | 生产就绪 (V41.232) | ⚠️ 与 hash_alignment/match_aligner 重叠 |
| **odds_filter.py** | 赔率过滤服务 | 生产就绪 (V41.186) | |
| **prediction_service.py** | 预测服务 | 生产就绪 | ⚠️ 与 inference_service 功能重叠 |
| **mlops/retraining_service.py** | MLOps 重训练服务 | 生产就绪 (v2.1) | |

---

## 架构评估

### 优点

1. **模块化设计良好** - collectors/ 和 infrastructure/ 目录职责分离清晰
2. **版本演进有序** - 采用 V26.x、V41.x、V144.x 等版本号体系
3. **反爬虫机制先进** - Ghost Protocol (V150.0) 实现业界领先
4. **ML 模块完整** - 从特征工程到推理的全链路覆盖

### 问题

1. **服务层职责不清** - 多个服务处理相同功能（采集、对齐、预测）
2. **文件过大** - 部分文件超过 1000 行，难以维护
3. **版本管理混乱** - 缺乏统一的版本号规范
4. **配置分散** - 配置文件散布在多个目录

### 改进建议

| 优先级 | 改进项 | 预期效果 |
|--------|--------|----------|
| P0 | 合并 bridge/ 重复代码 | 消除 JSExecutor 重复定义 |
| P0 | 合并 services/ 重叠服务 | 减少 30% 代码冗余 |
| P1 | 拆分超大文件 | 提高可维护性 |
| P1 | 统一版本号规范 | 便于追踪演进 |
| P2 | 整合配置文件 | 集中配置管理 |

---

## 附录：调用关系图

```
main.py
  ├─> collectors/
  │   ├─> fotmob_core.py (V144.5)
  │   └─> lineup_collector.py (V41.284)
  ├─> services/
  │   ├─> harvester_service.py
  │   ├─> collection_service.py [1843行]
  │   └─> prediction_service.py
  ├─> processors/
  │   ├─> feature_factory.py (V41.500)
  │   ├─> v41_380_golden_extractor.py (V41.380)
  │   └─> v25_production_extractor.py (V26.7)
  ├─> ml/
  │   ├─> engine.py (V26.8) [兼容层]
  │   ├─> inference/model_dispatcher.py (V26.8)
  │   └─> feature_engine/engine.py (V23.0)
  └─> bridge/
      └─> adapters/js_executor.py
          └─> infrastructure/engines/QuantHarvester.js (V164.TitanSlayer)
```

---

**审计完成时间**: 2026-01-31
**审计人员**: Genesis.Inventory Team
**下次审计建议**: 3 个月后或下次重大架构变更后
