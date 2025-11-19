"""预测引擎配置模块
Prediction Engine Configuration Module.
"""


from pydantic import BaseModel, Field


class PredictionConfig(BaseModel):
    """预测引擎配置类."""

    # 模型配置
    model_version: str = Field(default="v1.0", description="模型版本")
    model_path: str | None = Field(default=None, description="模型文件路径")

    # 性能配置
    batch_size: int = Field(default=32, description="批处理大小")
    max_workers: int = Field(default=4, description="最大工作线程数")
    timeout: int = Field(default=30, description="超时时间（秒）")

    # 缓存配置
    enable_cache: bool = Field(default=True, description="启用缓存")
    cache_ttl: int = Field(default=3600, description="缓存过期时间（秒）")

    # 特征配置
    feature_window: int = Field(default=10, description="特征时间窗口（比赛数）")
    min_matches: int = Field(default=5, description="最小比赛数要求")

    # 阈值配置
    confidence_threshold: float = Field(
        default=0.6, ge=0, le=1, description="置信度阈值"
    )
    min_probability: float = Field(default=0.1, ge=0, le=1, description="最小概率阈值")

    class Config:
        """Pydantic配置."""

        frozen = False  # 允许修改配置


class DatabaseConfig(BaseModel):
    """数据库配置类."""

    host: str = Field(default="localhost", description="数据库主机")
    port: int = Field(default=5432, description="数据库端口")
    database: str = Field(default="football_prediction", description="数据库名")
    user: str = Field(default="postgres", description="用户名")
    password: str = Field(default="", description="密码")

    # 连接池配置
    pool_size: int = Field(default=10, description="连接池大小")
    max_overflow: int = Field(default=20, description="连接池溢出数")

    @property
    def connection_string(self) -> str:
        """获取数据库连接字符串."""
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"


__all__ = ["PredictionConfig", "DatabaseConfig"]
