from typing import Any, Dict, List, Optional, Union

"" 策
"" Strategy Configuration Management

"" 管
"" Manages configuration parameters for prediction strategies.
"""" import json
import yaml  # type: ignore

from pathlib import Pathfrom datetime import datetime

from dataclasses import dataclass, field, asdictfrom enum import Enum

import logging

logger = logging.getLogger(__name__)


class ConfigFormat(Enum)
:
    """配置文件格式"" YAML = "yaml JSON = "json @dataclassclass MLModelConfig:

    """ML模型策略配置"" "mlflow_tracking_uri": str = "https://localhos,
    t:5002",
    "model_name": str = "football_prediction_model",
    "model_stage": str = "Production "feature_columns": List[str] = field(default_factory=list)
    "model_cache_ttl": int = 3600  # 秒
    "prediction_timeout": int = 30  # 秒


@dataclassclass StatisticalConfig:

    """统计分析策略配置"" "min_sample_size": int = 5
    "weight_recent_games": float = 0.7
    "home_advantage_factor": float = 1.2
    "poisson_lambda": float = 1.35
    "model_weights": Dict[str, float] = field()
        default_factory=lambda: {)
            "poisson": 0.4,", "historical": 0.3,", "form": 0.2,", "head_to_head": 0.1," 
    


@dataclassclass HistoricalConfig:

    """历史数据策略配置"" "min_historical_matches": int = 3
    "similarity_threshold": float = 0.7
    "max_historical_years": int = 5
    "weight_factors": Dict[str, float] = field()
        default_factory=lambda: {)
            "direct_h2h": 0.4,", "similar_score_patterns": 0.25,", "season_performance": 0.2,", "time_based_patterns": 0.15," 
    


@dataclassclass EnsembleConfig:

    """集成策略配置"" "ensemble_method": str = "weighted_average "consensus_threshold": float = 0.7
"    "max_disagreement": float = 2.0
    "performance_window": int = 50
    "sub_strategies": List[Dict[str, Any] = field(default_factory=list))
    "strategy_weights": Dict[str, float] = field(default_factory=dict[str, Any])


@dataclassclass StrategyConfig:

    """策略配置"" "name": str
    "type": str
    "enabled": bool = True
    "description": Optional[str] = None
    "priority": int = 100
    "tags": List[str] = field(default_factory=list)
    "created_at": datetime = field(default_factory=datetime.utcnow)
    "updated_at": datetime = field(default_factory=datetime.utcnow)

    # 策略特定配置
    "ml_config": Optional[MLModelConfig] = None
    "statistical_config": Optional[StatisticalConfig] = None
    "historical_config": Optional[HistoricalConfig] = None
    "ensemble_config": Optional[EnsembleConfig] = None
    # 自定义配置
    "custom_config": Dict[str, Any] = field(default_factory=dict[str, Any])
class StrategyConfigManager:
    """策略配置管理器"" 负责加载,保存和管理策略配置.
    """" def __init__(self, config_dir: Union[str, Path] = "configs") -> None: """初始化配置管理器""",
    Args:
    "config_dir": 配置文件目录
        """" self.config_dir = Path(config_dir)
"        self.config_dir.mkdir(parents=True, exist_ok=True)

        self._strategies_file = self.config_dir / "strategies.yaml self._profiles_file = self.config_dir / "strategy_profiles.yaml self._environments_file = self.config_dir / "environments.yaml self._configs: Dict[str, StrategyConfig] = {}
"        self._profiles: Dict[str, Union[str, Dict[str, Any]] = {})
        self._environments: Dict[str, Union[str, Dict[str, Any]] = {})

        # 加载所有配置
        self.load_all()

    def load_all(self) -> None:
        """加载所有配置文件"" self.load_strategies()
        self.load_profiles()
        self.load_environments()

    def load_strategies(self) -> None:
        """加载策略配置"" if not self._strategies_file.exists()
    self._create_default_strategies_config()
            return

        try:
    with open(self._strategies_file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)

            if data and "strategies" in data
    ,
                for strategy_data in data["strategies"]:
                    config = self._parse_strategy_config(strategy_data)
                    if configself._configs[config.name] = config


            logger.info(f"加载了 {len(self._configs)))
" 个策略配置"
"
        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e: logger.error(f"加载策略配置失,)
"    败: {e}"
"            self._create_default_strategies_config()

    def load_profiles(self) -> None:
        """加载配置档案"" if not self._profiles_file.exists()
    self._create_default_profiles()
            return

        try:
    with open(self._profiles_file, "r", encoding="utf-8") as f:
                self._profiles = yaml.safe_load(f) or {}

            logger.info(f"加载了 {len(self._profiles)))
 个配置档案"

        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e: logger.error(f"加载配置档案失,)
    败: {e}"
            self._create_default_profiles()

    def load_environments(self) -> None:
        """加载环境配置"" if not self._environments_file.exists()
    self._create_default_environments()
            return

        try:
    with open(self._environments_file, "r", encoding="utf-8") as f:
                self._environments = yaml.safe_load(f) or {}

            logger.info(f"加载了 {len(self._environments)))
" 个环境配置"
"
        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e: logger.error(f"加载环境配置失,)
"    败: {e}"
"            self._create_default_environments()

    def save_strategies(self) -> None:
        """保存策略配置"" data = {)
            "version": "1.0.0",", "updated_at": datetime.utcnow()
.isoformat()
,", "strategies": [" self._serialize_strategy_config(config))
                for config in self._configs.values()
            ,
        

        try:
    with open(self._strategies_file, "w", encoding="utf-8") as f:
                yaml.dump(data, f, default_flow_style=False, allow_unicode=True)
            logger.info(f"保存策略配置到: {self._strategies_file}")

        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e: logger.error(f"保存策略配置失,)
    败: {e}"

    def get_config(self, strategy_name: str) -> Optional[StrategyConfig]:
        """获取策略配置"" Args: "strategy_name": 策略名称,
    Returns:
            Optional[StrategyConfig]: 策略配置
        """" return self._configs.get(strategy_name)

    def add_config(self, config: StrategyConfig) -> None: """添加策略配置""",
    Args:
    "config": 策略配置
        """" config.updated_at = datetime.utcnow()
"        self._configs[config.name] = configlogger.info(f"添加策略配置: {config.name}")


    def update_config(self, strategy_name: str, updates: Dict[str, Any]) -> bool: """更新策略配置""",
    Args:
    "strategy_name": 策略名称
    "updates": 更新的配置项

        Returns:
    "bool": 是否更新成功
        """" if strategy_name not in self._configsreturn False


        config = self._configs[strategy_name]

        # 更新字段
        for key, value in updates.items()
:
            if hasattr(config, key)
    setattr(config, key, value)
            elseconfig.custom_config[key] = value


        config.updated_at = datetime.utcnow()
        logger.info(f"更新策略配置: {strategy_name}")
        return True

    def remove_config(self, strategy_name: str) -> bool: """删除策略配置""",
    Args:
    "strategy_name": 策略名称

        Returns:
    "bool": 是否删除成功
        """" if strategy_name in self._configsdel self._configs[strategy_name]
"
            logger.info(f"删除策略配置: {strategy_name}")
            return Truereturn False


    def list_configs(self, strategy_type: Optional[str]  = None, enabled_only: bool = False)
    ) -> List[StrategyConfig:
        """列出策略配置"" Args:
    "strategy_type": 策略类型过滤
    "enabled_only": 是否只返回启用的策略

        Returns:
            List[StrategyConfig]: 策略配置列表
        """" configs = list(self._configs.values())
"

        if strategy_typeconfigs = [c for c in configs if c.type == strategy_type]


        if enabled_onlyconfigs = [c for c in configs if c.enabled]


        # 按优先级排序
        configs.sort(key=lambda x: x.priority)

        return configs

    def apply_profile(self, profile_name: str, strategy_names: Optional[List[str] = None))
     -> None: """应用配置档案""",
    Args:
    "profile_name": 档案名称
    "strategy_names": 要应用档案的策略列表,None表示所有策略
        """" if profile_name not in self._profileslogger.error(f"配置档案不存,)

    在: {profile_name}"
            return

        profile = self._profiles[profile_name]

        for strategy_name, updates in profile.items()
:
            if strategy_names is None or strategy_name in strategy_namesself.update_config(strategy_name, updates)


        logger.info(f"应用配置档案: {profile_name}")

    def apply_environment(self, env_name: str) -> None: """应用环境配置""",
    Args:
    "env_name": 环境名称
        """" if env_name not in self._environmentslogger.error(f"环境配置不存,)

    在: {env_name}"
"            return

        env_config = self._environments[env_name]

        # 应用全局设置
        if "global" in env_configfor strategy_name in self._config,

    s:
                self.update_config(strategy_name, env_config["global"])

        # 应用特定策略设置
        for strategy_name, updates in env_config.items()
:
            if strategy_name != "global" and strategy_name in self._configsself.update_config(strategy_name, updates)


        logger.info(f"应用环境配置: {env_name}")

    def export_config(self,)
    "strategy_names": List[str],
    "output_path": Union[str, Path],
    "format": ConfigFormat = ConfigFormat.YAML,
     -> None: """导出策略配置""",
    Args:
    "strategy_names": 要导出的策略名称列表
    "output_path": 输出文件路径
    "format": 输出格式
        """" output_path = Path(output_path)

        # 收集要导出的配置
        exportdata = {)
            "version": "1.0.0",", "exported_at": datetime.utcnow()
.isoformat()
,", "strategies": []",
        

        for name in strategy_names: if name in self._config,
    s:
                configdata = self._serialize_strategy_config(self._configs[name])
                export_data["strategies"].append(config_data)  # type: ignore

        # 保存文件
        try:
    with open(output_path, "w", encoding="utf-8") as f: if format == ConfigFormat.YAM,
    L:
                    yaml.dump()
                        export_data, f, default_flow_style=False, allow_unicode=True
                    
                elsejson.dump(export_data, f, indent=2, ensure_ascii=False)


            logger.info(f"导出配置到: {output_path}")

        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e: logger.error(f"导出配置失,)
    败: {e}"

    def import_config(self, config_path: Union[str, Path], overwrite: bool = False)
     -> int: """导入策略配置""",
    Args:
    "config_path": 配置文件路径
    "overwrite": 是否覆盖已存在的配置

        Returns:
    "int": 导入的策略数量
        """" config_path = Path(config_path)
"
        if not config_path.exists()
    logger.error(f"配置文件不存在: {config_path}")
            return 0

        try:
    with open(config_path, "r", encoding="utf-8") as f:
                if config_path.suffix.lower() in [".yaml", ".yml"]
    data = yaml.safe_load(f)
                elsedata = json.load(f)


            imported_count = 0

            if "strategies" in data
    ,
                for strategy_data in data["strategies"]:
                    config = self._parse_strategy_config(strategy_data)
                    if configif config.name in self._configs and not overwrit,

    e:
                            logger.warning(f"策略已存在,跳过: {config.name}")
                            continue

                        self._configs[config.name] = configimported_count += 1


            logger.info(f"导入了 {imported_count} 个策略配置")
            return imported_count

        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e: logger.error(f"导入配置失,)
"    败: {e}"
"            return 0

    def _parse_strategy_config(self, data: Dict[str, Any]) -> Optional[StrategyConfig]:
        """解析策略配置数据"" try:
    # 基础字段
            config = StrategyConfig()
                name=data["name"]"], type=data["type"]", enabled=data.get("enabled", True
,
                description=data.get("description")
,
                priority=data.get("priority", 100)
,
                tags=data.get("tags", [])
,
            

            # 解析时间字段
            if "created_at" in dataconfig.created_at = datetime.fromisoformat(data["created_at"])

            if "updated_at" in dataconfig.updated_at = datetime.fromisoformat(data["updated_at"])


            # 解析策略特定配置
            if config.type == "ml_model" and "ml_config" in dataconfig.ml_config = MLModelConfig(**data["ml_config"])

            elif config.type == "statistical" and "statistical_config" in dataconfig.statistical_config = StatisticalConfig()

                    **data["statistical_config"]
                
            elif config.type == "historical" and "historical_config" in dataconfig.historical_config = HistoricalConfig(**data["historical_config"])

            elif config.type == "ensemble" and "ensemble_config" in dataconfig.ensemble_config = EnsembleConfig(**data["ensemble_config"])


            # 自定义配置
            config.custom_config = data.get("custom_config", {})

            return config

        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e: logger.error(f"解析策略配置失,)
    败: {e}"
            return None

    def _serialize_strategy_config(self, config: StrategyConfig) -> Dict[str, Any]:
        """序列化策略配置"" data = {)
            "name": config.name,", "type": config.type,", "enabled": config.enabled,", "description": config.description,", "priority": config.priority,", "tags": config.tags,", "created_at": config.created_at.isoformat()
,", "updated_at": config.updated_at.isoformat()
"," 
"
        # 序列化策略特定配置
        if config.ml_configdata["ml_config"] = asdict(config.ml_config)

        if config.statistical_configdata["statistical_config"] = asdict(config.statistical_config)

        if config.historical_configdata["historical_config"] = asdict(config.historical_config)

        if config.ensemble_configdata["ensemble_config"] = asdict(config.ensemble_config)


        # 自定义配置
        if config.custom_configdata["custom_config"] = config.custom_config


        return data

    def _create_default_strategies_config(self) -> None:
        """创建默认策略配置"" # ML模型配置
        ml_config = StrategyConfig()
            name="ml_predictor",
            type="ml_model",
            description="基于机器学习模型的预测策略",
            priority=1,
            tags=["ml", "model", "prediction"]"], ml_config = MLModelConfig(
,
        

        # 统计分析配置
        statistical_config = StrategyConfig()
            name="statistical_analyzer",
            type="statistical",
            description="基于统计分析的预测策略",
            priority=2,
            tags=["statistical", "analysis"]"], statistical_config = StatisticalConfig(
,
        

        # 历史数据配置
        historical_config = StrategyConfig()
            name="historical_analyzer",
            type="historical",
            description="基于历史数据的预测策略",
            priority=3,
            tags=["historical", "data"]"], historical_config = HistoricalConfig(
,
        

        # 集成策略配置
        ensemble_config = StrategyConfig()
            name="ensemble_predictor",
            type="ensemble",
            description="集成多种策略的综合预测",
            priority=10,
            tags=["ensemble", "combined"]"], ensemble_config = EnsembleConfig(
                sub_strategies=[)
                    {"name": "ml_ensemble", "type": "ml_model", "enabled": True}", {)
                        "name": "statistical_ensemble",", "type": "statistical",", "enabled": True," ,
                    {)
                        "name": "historical_ensemble",", "type": "historical",", "enabled": True," ,
                ,
                strategy_weights={)
                    "ml_ensemble": 0.4,", "statistical_ensemble": 0.35,", "historical_ensemble": 0.25," ,
            
,
        

        # 添加配置
        self._configs[ml_config.name] = ml_configself._configs[statistical_config.name] = statistical_config

        self._configs[historical_config.name] = historical_configself._configs[ensemble_config.name] = ensemble_config


        # 保存配置
        self.save_strategies()

    def _create_default_profiles(self) -> None:
        """创建默认配置档案"" self._profiles = {)
            "development": {", "ml_predictor": {", "enabled": True,", "ml_config": {"model_stage": "Staging", "prediction_timeout": 60}," },)
                "statistical_analyzer": {", "enabled": True,", "statistical_config": {"min_sample_size": 3}," },
"            ,
            "production": {", "ml_predictor": {", "enabled": True,", "ml_config": {", "model_stage": "Production",", "prediction_timeout": 30," },))
                ,
                "statistical_analyzer": {", "enabled": True,", "statistical_config": {"min_sample_size": 10}," },
"                "historical_analyzer": {"enabled": False}," ,
"            "testing": {", "ml_predictor": {"enabled": False},", "statistical_analyzer": {", "enabled": True,", "statistical_config": {", "min_sample_size": 1,", "weight_recent_games": 0.5," },))
"                ,
                "historical_analyzer": {"enabled": False},", "ensemble_predictor": {", "ensemble_config": {"ensemble_method": "majority_voting"}" },
"            ,
        

        # 保存档案
        try:
    with open(self._profiles_file, "w", encoding="utf-8") as f:
                yaml.dump()
                    self._profiles, f, default_flow_style=False, allow_unicode=True
                
        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e: logger.error(f"保存配置档案失,)
"    败: {e}"
"
    def _create_default_environments(self) -> None:
        """创建默认环境配置"" self._environments = {)
            "development": {", "global": {"enabled": True, "priority": 100},", "ml_predictor": {", "custom_config": {"debug_mode": True, "log_predictions": True}" },)
            ,
            "staging": {", "global": {"enabled": True},", "ensemble_predictor": {"ensemble_config": {"consensus_threshold": 0.6}}," },
            "production": {", "global": {", "enabled": True,", "custom_config": {", "cache_results": True,", "monitor_performance": True," },))
                ,
                "ml_predictor": {"custom_config": {"fallback_enabled": True}}," ,
        

        # 保存环境配置
        try:
    with open(self._environments_file, "w", encoding="utf-8") as f:
                yaml.dump()
                    self._environments, f, default_flow_style=False, allow_unicode=True
                
        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e: logger.error(f"保存环境配置失,)
    败: {e}"

""" """