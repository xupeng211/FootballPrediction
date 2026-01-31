#!/usr/bin/env python3
"""
服务容器配置 - Sprint 3 依赖注入设置

配置和初始化依赖注入容器，注册所有服务。
实现企业级服务组装和依赖管理。

Sprint 3 功能:
- 服务注册和配置
- 依赖关系管理
- 生命周期管理
- 配置注入
"""

import logging

from src.ml.features.elo_rating_system import EloRatingSystem
from src.ml.features.odds_movement_features import OddsMovementAnalyzer
from src.ml.features.poisson_features import PoissonFeatureCalculator
from src.strategy.kelly_criterion import KellyCriterion

# Sprint 5 新增导入
from src.testing.backtester import BacktestConfig, BacktestEngine

from .dependency_injection import container_context, get_container
from .inference_service import InferenceService
from .prediction_service import PredictionService

logger = logging.getLogger(__name__)


async def setup_services() -> None:
    """
    设置所有服务 - Sprint 3 架构组装

    注册所有服务到依赖注入容器，配置依赖关系。
    """
    logger.info("🔄 开始设置服务容器")

    container = get_container()

    try:
        # 1. 注册基础服务配置
        container.register(
            service_name="inference_config",
            service_type=InferenceServiceConfig,
            factory=lambda: InferenceServiceConfig(
                model_path="models/football_xgboost_classifier.pkl",
                enable_cache=True,
                cache_ttl_seconds=300,
                max_cache_size=1000,
                enable_fallback=True,
                default_probabilities={
                    "HOME_WIN_PROBA": 0.46,
                    "DRAW_PROBA": 0.26,
                    "AWAY_WIN_PROBA": 0.28,
                },
            ),
        )

        # 2. 注册模型服务 (示例工厂函数)
        container.register(
            service_name="model_service",
            service_type=object,  # 实际应该是具体的模型服务类型
            factory=create_model_service,
            dependencies=["inference_config"],
        )

        # 3. 注册特征提取器服务
        container.register(
            service_name="feature_extractor",
            service_type=object,  # 实际应该是具体的特征提取器类型
            factory=create_feature_extractor,
            dependencies=["inference_config"],
        )

        # 4. 注册数据库服务
        container.register(
            service_name="database_service",
            service_type=object,  # 实际应该是具体的数据库服务类型
            factory=create_database_service,
        )

        # 5. 注册推理服务 - 使用依赖注入
        container.register(
            service_name="inference_service",
            service_type=InferenceService,
            dependencies=["model_service", "feature_extractor", "database_service"],
            config={"config_factory": lambda: InferenceServiceConfig()},
        )

        # 6. 注册预测服务 - 使用依赖注入
        container.register(
            service_name="prediction_service",
            service_type=PredictionService,
            dependencies=["inference_service", "explainability_service"],
        )

        # Sprint 5: 注册高级分析和策略服务
        # 7. 注册Elo评级系统
        container.register(
            service_name="elo_rating_system",
            service_type=EloRatingSystem,
            factory=create_elo_rating_system,
        )

        # 8. 注册泊松特征计算器
        container.register(
            service_name="poisson_calculator",
            service_type=PoissonFeatureCalculator,
            factory=create_poisson_calculator,
        )

        # 9. 注册赔率变动分析器
        container.register(
            service_name="odds_analyzer",
            service_type=OddsMovementAnalyzer,
            factory=create_odds_analyzer,
        )

        # 10. 注册凯利准则系统
        container.register(
            service_name="kelly_criterion",
            service_type=KellyCriterion,
            factory=create_kelly_criterion,
        )

        # 11. 注册回测引擎 - Sprint 5 核心组件
        container.register(
            service_name="backtest_engine",
            service_type=BacktestEngine,
            factory=create_backtest_engine,
            dependencies=[
                "elo_rating_system",
                "poisson_calculator",
                "odds_analyzer",
                "kelly_criterion",
            ],
        )

        logger.info("✅ 服务容器设置完成 (包含Sprint 5高级分析服务)")

    except Exception as e:
        logger.exception(f"❌ 服务容器设置失败: {e}")
        raise


# 服务工厂函数
async def create_model_service(inference_config: InferenceServiceConfig) -> object:
    """创建模型服务"""
    # 这里应该是实际的模型服务创建逻辑
    # 示例：加载XGBoost模型
    logger.info("📦 创建模型服务")

    # 模拟模型服务
    class MockModelService:
        def __init__(self, config: InferenceServiceConfig):
            self.config = config
            self.is_trained = True

        async def predict(self, features):
            # 模拟预测逻辑
            return "HOME_WIN"

        async def predict_proba(self, features):
            # 模拟概率预测
            return {"HOME_WIN_PROBA": 0.65, "DRAW_PROBA": 0.25, "AWAY_WIN_PROBA": 0.10}

        def get_model_info(self):
            return {
                "model_name": "football_xgboost_classifier",
                "model_version": "1.0.0",
                "is_trained": True,
            }

    return MockModelService(inference_config)


async def create_feature_extractor(inference_config: InferenceServiceConfig) -> object:
    """创建特征提取器服务"""
    logger.info("📦 创建特征提取器服务")

    # 模拟特征提取器
    class MockFeatureExtractor:
        def __init__(self, config: InferenceServiceConfig):
            self.config = config

        async def extract_features(self, match_id: str, historical_data):
            # 模拟特征提取
            return {
                "feature_vector": [0.1, 0.2, 0.3, 0.4, 0.5],
                "feature_names": ["f1", "f2", "f3", "f4", "f5"],
                "completeness_score": 0.95,
            }

    return MockFeatureExtractor(inference_config)


async def create_database_service() -> object:
    """创建数据库服务"""
    logger.info("📦 创建数据库服务")

    # 模拟数据库服务
    class MockDatabaseService:
        async def fetchrow(self, query: str, *args):
            # 模拟单行查询
            if "match_id" in query and args:
                return {
                    "match_id": args[0],
                    "home_team_id": "team_1",
                    "away_team_id": "team_2",
                    "match_date": "2024-01-15",
                    "home_score": 2,
                    "away_score": 1,
                    "status": "FINISHED",
                    "venue": "Stadium A",
                    "league_id": "EPL",
                }
            return None

        async def fetch(self, query: str, *args):
            # 模拟多行查询
            return [
                {
                    "match_id": f"match_{i}",
                    "home_team_id": "team_1",
                    "away_team_id": "team_2",
                    "match_date": "2024-01-10",
                    "home_score": 1,
                    "away_score": 1,
                    "status": "FINISHED",
                }
                for i in range(10)
            ]

    return MockDatabaseService()


async def create_explainability_service() -> object:
    """创建可解释性服务"""
    logger.info("📦 创建可解释性服务")

    # 模拟可解释性服务
    class MockExplainabilityService:
        async def get_shap_contributions(self, features, model):
            # 模拟SHAP贡献度计算
            return {
                "feature_1": 0.1,
                "feature_2": -0.05,
                "feature_3": 0.08,
                "feature_4": -0.02,
                "feature_5": 0.03,
            }

    return MockExplainabilityService()


# Sprint 5: 高级分析服务工厂函数
async def create_elo_rating_system() -> EloRatingSystem:
    """创建Elo评级系统"""
    logger.info("🏆 创建Elo评级系统")
    return EloRatingSystem(
        initial_rating=1500.0,
        home_advantage=50.0,
        base_k_factor=40.0,
        enable_goal_margin=True,
        enable_dynamic_k=True,
        rating_decay_days=365,
    )


async def create_poisson_calculator() -> PoissonFeatureCalculator:
    """创建泊松特征计算器"""
    logger.info("📊 创建泊松特征计算器")
    return PoissonFeatureCalculator(
        home_lambda_default=1.5,
        away_lambda_default=1.2,
        league_avg_goals=2.7,
        enable_team_strength_adjustment=True,
        enable_venue_adjustment=True,
        enable_time_decay=True,
        max_goals_calc=10,
    )


async def create_odds_analyzer() -> OddsMovementAnalyzer:
    """创建赔率变动分析器"""
    logger.info("📈 创建赔率变动分析器")
    return OddsMovementAnalyzer(
        steam_threshold=0.15,
        significant_move_threshold=0.10,
        time_window_hours=24,
        enable_anomaly_detection=True,
        enable_trend_analysis=True,
        smoothing_window=5,
    )


async def create_kelly_criterion() -> KellyCriterion:
    """创建凯利准则系统"""
    logger.info("💰 创建凯利准则系统")
    return KellyCriterion(
        initial_bankroll=10000.0,
        kelly_strategy=KellyStrategy.FRACTIONAL_KELLY,
        fraction_multiplier=0.25,
        min_edge_threshold=0.05,
        max_stake_percentage=0.10,
        enable_dynamic_adjustment=True,
        enable_risk_management=True,
    )


async def create_backtest_engine(
    elo_rating_system: EloRatingSystem,
    poisson_calculator: PoissonFeatureCalculator,
    odds_analyzer: OddsMovementAnalyzer,
    kelly_criterion: KellyCriterion,
) -> BacktestEngine:
    """创建回测引擎"""
    logger.info("🔄 创建回测引擎")

    # 配置回测参数
    config = BacktestConfig(
        data_path="./data/historical/",
        strategies=["kelly_fractional", "elo_based", "poisson_based", "ensemble"],
        initial_bankroll=10000.0,
        n_workers=4,  # 限制工作线程数
        chunk_size=5000,
        memory_limit_gb=4.0,
        use_streaming=True,
        cache_features=True,
        output_path="./results/backtest/",
        save_intermediate=True,
    )

    # 创建回测引擎实例
    engine = BacktestEngine(config)

    # 注入已配置的子系统
    engine.elo_system = elo_rating_system
    engine.poisson_calculator = poisson_calculator
    engine.odds_analyzer = odds_analyzer
    engine.stream_processor.elo_system = elo_rating_system
    engine.stream_processor.poisson_calculator = poisson_calculator
    engine.stream_processor.odds_analyzer = odds_analyzer

    logger.info("✅ 回测引擎创建完成")
    return engine


async def initialize_services() -> None:
    """
    初始化所有服务

    这个函数应该在应用启动时调用。
    """
    async with container_context():
        await setup_services()

        container = get_container()

        # 预热核心服务
        try:
            logger.info("🔥 预热核心服务...")

            # 初始化推理服务
            await container.resolve("inference_service")
            logger.info("✅ 推理服务初始化完成")

            # 初始化预测服务
            await container.resolve("prediction_service")
            logger.info("✅ 预测服务初始化完成")

            # Sprint 5: 预热高级分析服务
            logger.info("🔥 预热Sprint 5高级分析服务...")

            # 初始化Elo评级系统
            await container.resolve("elo_rating_system")
            logger.info("✅ Elo评级系统预热完成")

            # 初始化泊松计算器
            await container.resolve("poisson_calculator")
            logger.info("✅ 泊松特征计算器预热完成")

            # 初始化赔率分析器
            await container.resolve("odds_analyzer")
            logger.info("✅ 赔率变动分析器预热完成")

            # 初始化凯利准则系统
            await container.resolve("kelly_criterion")
            logger.info("✅ 凯利准则系统预热完成")

            # 初始化回测引擎
            await container.resolve("backtest_engine")
            logger.info("✅ 回测引擎预热完成")

            logger.info("🎉 所有服务预热完成! (包含Sprint 5高级分析功能)")

        except Exception as e:
            logger.exception(f"❌ 服务预热失败: {e}")
            raise


# 使用示例
async def example_usage():
    """
    使用示例 - 展示如何使用依赖注入容器
    """
    # 初始化服务
    await initialize_services()

    container = get_container()

    # 解析并使用预测服务
    prediction_service = await container.resolve("prediction_service")

    # 进行预测
    await prediction_service.predict_single_match(
        match_id="example_match_123", include_features=True, include_metadata=True
    )

    # 健康检查
    await prediction_service.get_service_health()


if __name__ == "__main__":
    # 示例运行
    import asyncio

    asyncio.run(example_usage())
