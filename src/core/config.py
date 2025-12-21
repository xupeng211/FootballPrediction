"""
FootballPrediction V7.0 统一配置管理系统
管理所有环境变量、路径、API配置和数据库凭证
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

@dataclass
class DatabaseConfig:
    """数据库配置"""
    host: str = os.getenv('DB_HOST', 'localhost')
    port: int = int(os.getenv('DB_PORT', '5432'))
    name: str = os.getenv('DB_NAME', 'football_db')
    user: str = os.getenv('DB_USER', 'football_user')
    password: str = os.getenv('DB_PASSWORD', 'football_pass')

    def get_connection_string(self) -> str:
        """获取数据库连接字符串"""
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"

@dataclass
class APIConfig:
    """API配置"""
    fotmob_base_url: str = "https://www.fotmob.com/api"
    fotmob_headers: Dict[str, str] = None
    request_timeout: int = 15
    retry_attempts: int = 3
    rate_limit_delay: tuple = (1.0, 3.0)  # 随机延迟范围（秒）

    def __post_init__(self):
        if self.fotmob_headers is None:
            self.fotmob_headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }

@dataclass
class PathConfig:
    """路径配置"""
    project_root: Path = Path(__file__).parent.parent.parent

    @property
    def data_dir(self) -> Path:
        return self.project_root / "data"

    @property
    def models_dir(self) -> Path:
        return self.data_dir / "models"

    @property
    def logs_dir(self) -> Path:
        return self.project_root / "logs"

    @property
    def src_dir(self) -> Path:
        return self.project_root / "src"

    @property
    def final_features_path(self) -> Path:
        return self.data_dir / "final_v7_solid_features.csv"

    @property
    def current_model_path(self) -> Path:
        return self.project_root / "lightgbm_v7.model"

@dataclass
class ModelConfig:
    """模型配置"""
    model_type: str = "lightgbm"
    feature_version: str = "v7.0"
    target_accuracy: float = 0.74
    feature_columns: list = None

    def __post_init__(self):
        if self.feature_columns is None:
            # 106维特征标准
            self.feature_columns = [
                # 基础特征 (20维)
                'home_avg_rating', 'away_avg_rating',
                'home_big_chances_created', 'away_big_chances_created',
                'home_total_shots', 'away_total_shots',
                'home_shots_on_target', 'away_shots_on_target',
                'home_possession', 'away_possession',
                'home_xg', 'away_xg',
                'home_corners', 'away_corners',
                'home_red_cards', 'away_red_cards',
                'home_substitutions', 'away_substitutions',
                'home_early_goal', 'away_early_goal',
                'home_penalties', 'away_penalties',

                # 衍生特征 (86维)
                'home_xg_per_shot', 'away_xg_per_shot',
                'rating_diff', 'xg_diff', 'xg_total',
                'possession_diff', 'shots_diff', 'corners_diff',
                # ... 其他特征列根据实际需要补充
            ]

@dataclass
class LoggingConfig:
    """日志配置"""
    level: str = os.getenv('LOG_LEVEL', 'INFO')
    format: str = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    file_name: str = 'football_prediction.log'
    max_bytes: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5

@dataclass
class HarvestConfig:
    """数据收割配置"""
    league_id: str = "47"  # 英超
    season: str = "2024/2025"
    batch_size: int = 50
    max_workers: int = 4
    save_interval: int = 10  # 每收割N场保存一次

class Config:
    """主配置类"""

    def __init__(self):
        self.database = DatabaseConfig()
        self.api = APIConfig()
        self.paths = PathConfig()
        self.model = ModelConfig()
        self.logging = LoggingConfig()
        self.harvest = HarvestConfig()

        # 确保目录存在
        self._ensure_directories()

    def _ensure_directories(self):
        """确保必要的目录存在"""
        directories = [
            self.paths.data_dir,
            self.paths.models_dir,
            self.paths.logs_dir,
        ]

        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)

    def get_environment(self) -> str:
        """获取当前环境"""
        return os.getenv('ENVIRONMENT', 'development')

    def is_production(self) -> bool:
        """是否为生产环境"""
        return self.get_environment() == 'production'

    def is_development(self) -> bool:
        """是否为开发环境"""
        return self.get_environment() == 'development'

    def validate(self) -> Dict[str, Any]:
        """验证配置完整性"""
        issues = []

        # 检查关键路径
        if not self.paths.project_root.exists():
            issues.append(f"项目根目录不存在: {self.paths.project_root}")

        if not self.paths.current_model_path.exists():
            issues.append(f"模型文件不存在: {self.paths.current_model_path}")

        # 检查数据库配置
        if not all([self.database.host, self.database.name, self.database.user]):
            issues.append("数据库配置不完整")

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "environment": self.get_environment()
        }

# 全局配置实例
config = Config()

def get_config() -> Config:
    """获取配置实例"""
    return config

def reload_config() -> Config:
    """重新加载配置"""
    global config
    config = Config()
    return config