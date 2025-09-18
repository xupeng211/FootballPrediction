from typing import Any, Dict, Optional

from pydantic_settings import BaseSettings

class Config:
    config_dir: Any
    config_file: Any
    _config: Dict[str, Any]

    def __init__(self) -> None: ...
    def _load_config(self) -> None: ...
    def get(self, key: str, default: Any = ...) -> Any: ...
    def set(self, key: str, value: Any) -> None: ...
    def save(self) -> None: ...

class Settings(BaseSettings):
    database_url: str
    test_database_url: str
    redis_url: str
    api_host: str
    api_port: int
    environment: str
    log_level: str
    mlflow_tracking_uri: str
    api_football_key: Optional[str]
    api_football_url: str

    class Config:
        env_file: str
        env_file_encoding: str
        case_sensitive: bool

config: Config

def get_settings() -> Settings: ...
