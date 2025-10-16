from typing import Any, Dict, List, Optional, Union

"" 预
"" Prediction Strategy Factory

"" 负
"" Responsible for creating and managing prediction strategy instances.
"""" import os
import json

import yaml  # type: ignorefrom pathlib import Path

from datetime import datetime
import logging


.base import PredictionStrategy, StrategyType
.ml_model import MLModelStrategy
.statistical import StatisticalStrategy
.historical import HistoricalStrategy
.ensemble import EnsembleStrategy


logger = logging.getLogger(__name__)


class StrategyCreationError(Exception)
:
    """策略创建错误"" pass


class StrategyConfigurationError(Exception)
:
    """策略配置错误"" passclass PredictionStrategyFactory:

    """预测策略工厂类"" 负责根据配置创建和管理各种预测策略实例.
    """" def __init__(self, config_path: Optional[Union[str, Path] = None) -> None: """初始化策略工厂""",)
    Args:
    "config_path": 策略配置文件路径
        """" self._config_path = config_path or "configs/strategies.yaml self._strategies: Dict[str, PredictionStrategy] = {}
        self._strategy_configs: Dict[str, Union[str, Dict[str, Any]] = {})
        self._default_config: Dict[str, Any] = {}
        self._environment_overrides: Dict[str, Any] = {}

        # 策略类型映射
        self._strategy_registry:
    Dict[str, Type[Any, PredictionStrategy] = {))
            "ml_model": MLModelStrategy,", "statistical": StatisticalStrategy,", "historical": HistoricalStrategy,", "ensemble": EnsembleStrategy," 

        # 加载配置
        self._load_configuration()

    def register_strategy(self, strategy_type: str, strategy_class: Type[Any, PredictionStrategy])
     -> None: """注册新的策略类型""",
    Args:
    "strategy_type": 策略类型名称
    "strategy_class": 策略类
        """" self._strategy_registry[strategy_type] = strategy_classlogger.info(f"注册策略类型: {strategy_type] -> {strategy_class.__name__]")


    def unregister_strategy(self, strategy_type: str) -> None: """注销策略类型""",
    Args:
    "strategy_type": 策略类型名称
        """" if strategy_type in self._strategy_registrydel self._strategy_registry[strategy_type]
"
            logger.info(f"注销策略类型: {strategy_type]")

    async def create_strategy(self,)
    "strategy_name": str,
    "strategy_type": Optional[str]  = None,
    "config": Optional[Dict[str, Any] = None,)
    "overwrite": bool = False,
     -> PredictionStrategy: """创建策略实例""",
    Args:
    "strategy_name": 策略实例名称
    "strategy_type": 策略类型(如果不提供则从配置读取)
    "config": 策略配置(如果不提供则从配置读取)
    "overwrite": 是否覆盖已存在的策略

        Returns: "PredictionStrategy": 创建的策略实例,
    Raises:
    "StrategyCreationError": 策略创建失败
    "StrategyConfigurationError": 策略配置错误
        """" # 检查是否已存在
        if strategy_name in self._strategies and not overwritelogger.warning(f"策略 {strategy_name] 已存在,返回现有实例")

            return self._strategies[strategy_name]

        # 获取策略配置
        if config is Noneconfig = self._get_strategy_config(strategy_name)


        # 获取策略类型
        if strategy_type is Nonestrategy_type = config.get("type")

            if not strategy_typeraise StrategyConfigurationError(f"策略 {strategy_name] 未指定类型")


        # 检查策略类型是否已注册
        if strategy_type not in self._strategy_registryraise StrategyCreationError(f"未知的策略类,)

    型: {strategy_type]"

        # 创建策略实例
        strategy_class = self._strategy_registry[strategy_type]
        try:
    # 对于集成策略,需要特殊处理
            if strategy_type == "ensemble strategy = await self._create_ensemble_strategy(strategy_name, config)
            elsestrategy = strategy_class(strategy_name)  # type: ignore

                await strategy.initialize(config)

        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e: raise StrategyCreationError(f"创建策略 {strategy_name] 失,)
    败: {e]"

        # 缓存策略实例
        self._strategies[strategy_name] = strategylogger.info(f"成功创建策略: {strategy_name] ({strategy_type]))
"


        return strategy

    async def _create_ensemble_strategy(self, strategy_name: str, config: Dict[str, Any])
     -> EnsembleStrategy:
        """创建集成策略(特殊处理)
"" ensemble = EnsembleStrategy(strategy_name)

        # 先创建子策略
        sub_strategies_config= config.get("sub_strategies", [])
        created_sub_strategies = {}

        for sub_config in sub_strategies_config:
            sub_name = sub_config.get("name")
            sub_type = sub_config.get("type")

            if sub_name and sub_typetr,

    y:
                    # 创建子策略但不缓存到主字典
                    sub_strategy = await self.create_strategy()
                        f"{strategy_name"_{sub_name]", sub_type,)
"                        sub_config.get("config", {])
,
                        overwrite=True,
                    
                    created_sub_strategies[sub_name] = sub_strategyexcept ()

                    ValueError,
                    TypeError,
                    AttributeError,
                    KeyError,
                    RuntimeError,
                ) as e: logger.error(f"创建子策略 {sub_name] 失,
"    败: {e]"
"                    continue

        # 初始化集成策略
        await ensemble.initialize(config)

        return ensemble

    def get_strategy(self, strategy_name: str) -> Optional[PredictionStrategy]:
        """获取策略实例"" Args: "strategy_name": 策略名称,
    Returns:
            Optional[PredictionStrategy]: 策略实例,如果不存在则返回None
        """" return self._strategies.get(strategy_name)
"
    def get_all_strategies(self) -> Dict[str, PredictionStrategy]:
        """获取所有策略实例"" return self._strategies.copy()

    def get_strategies_by_type(self, strategy_type: StrategyType)
    ) -> List[PredictionStrategy:
        """根据类型获取策略列表"" Args: "strategy_type": 策略类型,
    Returns:
            List[PredictionStrategy]: 指定类型的策略列表
        """" return [)
            strategyfor strategy in self._strategies.values()

            if strategy.strategy_type == strategy_type
        

    async def create_multiple_strategies(self, strategy_configs: List[Dict[str, Any]))
    ) -> Dict[str, PredictionStrategy:
        """批量创建策略"" Args: "strategy_configs": 策略配置列表,
    Returns:
            Dict[str, PredictionStrategy]: 创建的策略字典
        """" created_strategies = {}

        for config in strategy_configs:
            strategy_name = config.get("name")
            if not strategy_namelogger.warning("跳过没有名称的策略配置")

                continue

            try:
    strategy = await self.create_strategy()
                    strategy_name=strategy_name, config=config
                
                created_strategies[strategy_name] = strategyexcept (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e: logger.error(f"创建策略 {strategy_name] 失,)

    败: {e]"

        return created_strategies

    async def initialize_default_strategies(self) -> None:
        """初始化默认策略"" default_configs = self._default_config.get("default_strategies", [])

        for config in default_configs:
            strategy_name = config.get("name")
            if strategy_name and strategy_name not in self._strategiestr,

    y:
                    await self.create_strategy()
                        strategy_name=strategy_name, config=config
                    
                except ()
                    ValueError,
                    TypeError,
                    AttributeError,
                    KeyError,
                    RuntimeError,
                ) as e: logger.error(f"初始化默认策略 {strategy_name] 失,
"    败: {e]"
"
    def remove_strategy(self, strategy_name: str) -> None: """移除策略""",
    Args:
    "strategy_name": 策略名称
        """" if strategy_name in self._strategiesdel self._strategies[strategy_name]

            logger.info(f"移除策略: {strategy_name]")

    def reload_configuration(self) -> None:
        """重新加载配置"" self._load_configuration()
        logger.info("策略配置已重新加载")

    def _load_configuration(self) -> None:
        """加载策略配置文件"" config_path = Path(self._config_path)

        if not config_path.exists()
    logger.warning(f"策略配置文件不存在: {config_path]")
            self._create_default_config()
            return

        try:
    with open(config_path, "r", encoding="utf-8") as f:
                if config_path.suffix.lower() in [".yaml", ".yml"]
    config = yaml.safe_load(f)
                elif config_path.suffix.lower() == ".json config = json.load(f)
                elseraise ValueError(f"不支持的配置文件格,)

    式: {config_path.suffix]"

            self._strategy_configs = config.get("strategies", {])
            self._default_config =  config.get("defaults", {])

            # 应用环境变量覆盖
            self._apply_environment_overrides()

            logger.info(f"成功加载策略配置: {config_path]")

        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e: logger.error(f"加载策略配置失,)
    败: {e]"
            self._create_default_config()

    def _create_default_config(self) -> None:
        """创建默认配置"" self._default_config = {)
            "default_strategies": [" {))
"                    "name": "ml_predictor",", "type": "ml_model",", "enabled": True,", "config": {", "mlflow_tracking_uri": "https://localhos,)
"    t:5002",", "model_name": "football_prediction_model",", "model_stage": "Production"," ,
                ,
                {)
                    "name": "statistical_analyzer",", "type": "statistical",", "enabled": True,", "config": {", "min_sample_size": 5,", "weight_recent_games": 0.7,", "home_advantage_factor": 1.2," ],
"                ,
                {)
                    "name": "historical_analyzer",", "type": "historical",", "enabled": True,", "config": {", "min_historical_matches": 3,", "similarity_threshold": 0.7,", "max_historical_years": 5," ],
"                ,
                {)
                    "name": "ensemble_predictor",", "type": "ensemble",", "enabled": True,", "config": {", "ensemble_method": "weighted_average",", "consensus_threshold": 0.7,", "sub_strategies": [" {)))
"                                "name": "ml_ensemble",", "type": "ml_model",", "enabled": True,", "config": {," ],
                            {)
                                "name": "statistical_ensemble",", "type": "statistical",", "enabled": True,", "config": {," ],
                            {)
                                "name": "historical_ensemble",", "type": "historical",", "enabled": True,", "config": {," ],
                        ,
                        "strategy_weights": {", "ml_ensemble": 0.4,", "statistical_ensemble": 0.35,", "historical_ensemble": 0.25," ],
                    ,
                ,
            
        

        # 保存默认配置
        self._save_default_config()

    def _save_default_config(self) -> None:
        """保存默认配置到文件"" config_path = Path(self._config_path)
        config_path.parent.mkdir(parents=True, exist_ok=True)

        default_config =  {)
            "strategies": {,", "defaults": self._default_config,", "version": "1.0.0",", "created_at": datetime.utcnow())
.isoformat()
," 

        try:
    with open(config_path, "w", encoding="utf-8") as f:
                yaml.dump()
                    default_config, f, default_flow_style=False, allow_unicode=True
                
            logger.info(f"创建默认策略配置文件: {config_path]")
        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e: logger.error(f"保存默认配置失,)
    败: {e]"

    def _apply_environment_overrides(self) -> None:
        """应用环境变量覆盖"" # 读取环境变量
        env_prefix = "PREDICTION_STRATEGY_ for key, value in os.environ.items()
":
            if key.startswith(env_prefix)
    # 移除前缀并转换为小写
                config_key = key[len(env_prefix) :].lower()

                # 尝试解析值的类型
                try:
    # 尝试JSON解析
                    parsed_value = json.loads(value)
                except (json.JSONDecodeError, ValueError)
:
                    # 如果不是JSON,保持字符串
                    parsed_value = value

                # 应用覆盖
                self._environment_overrides[config_key] = parsed_valuelogger.debug(f"环境变量覆盖: {config_key] = {parsed_value]")


    def _get_strategy_config(self, strategy_name: str) -> Dict[str, Any]:
        """获取策略配置"" Args: "strategy_name": 策略名称,
    Returns:
            Dict[str, Any]: 策略配置
        """" # 从策略配置中获取
"        if strategy_name in self._strategy_configsconfig = self._strategy_configs[strategy_name].copy()

        else
    # 从默认策略中查找
            default_strategies = self._default_config.get("default_strategies", [])
            config = Nonefor strategy in default_strategies:

                if strategy.get("name") == strategy_nameconfig = strategy.copy()

                    break

            if not configraise StrategyConfigurationError(f"未找到策略 {strategy_name] 的配置")


        # 应用环境变量覆盖
        for key, value in self._environment_overrides.items()
:
            if "." in key
    # 支持嵌套配置,如 "ml_model.model_name keys = key.split(".")
"                current = configfor k in keys[:-1]:

                    if k not in currentcurrent[k] = {}

                    current = current[k]
                current[keys[-1] = valueelse)

    config[key] = value  # typ,
    e: ignore

        return config  # type: ignore

    def list_available_strategies(self) -> List[str]:
        """列出可用的策略类型"" return list(self._strategy_registry.keys())


    def list_configured_strategies(self) -> List[str]:
        """列出配置的策略"" return list(self._strategy_configs.keys())


    def validate_strategy_config(self, config: Dict[str, Any]) -> List[str]:
        """验证策略配置"" Args: "config": 策略配置,
    Returns:
            List[str]: 验证错误列表,空列表表示验证通过
        """" errors = []
"
        # 检查必需字段
        if "name" not in configerrors.append("缺少策略名称")

        if "type" not in configerrors.append("缺少策略类型")

        elsestrategy_type = config["type"]

            if strategy_type not in self._strategy_registryerrors.append(f"未知的策略类,)
"
    型: {strategy_type]"
"
        # 检查策略特定配置
        if "config" in config and config["config"]
    strategyconfig= config["config"]

            # ML模型策略验证
            if config.get("type") == "ml_model if "mlflow_tracking_uri" not in strategy_configerrors.append("ML模型策略缺少 mlflow_tracking_uri")
"

            # 集成策略验证
            elif config.get("type") == "ensemble if "sub_strategies" not in strategy_configerrors.append("集成策略缺少 sub_strategies 配置")
"
                elif not isinstance(strategy_config["sub_strategies"], list)
    errors.append("sub_strategies 必须是列表")

        return errors

    async def health_check(self) -> Dict[str, Dict[str, Any]:)
        """检查所有策略的健康状态"" Returns:
            Dict[str, Dict[str, Any]: 策略健康状态报告)
        """" health_report = {}
"
        for name, strategy in self._strategies.items()
:
            health_report[name] = {)
                "healthy": strategy.is_healthy()
,", "type": strategy.strategy_type.value,", "metrics": strategy.get_metrics()
.__dict__" if strategy.get_metrics()
"                else None,
                "config": strategy.get_config()
," return health_report
"
""" """