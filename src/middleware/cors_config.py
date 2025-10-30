"""
CORS配置模块 - Phase 4B实现

提供跨域资源共享(CORS)配置和管理功能：
- CORS配置定义和验证
- 预检请求处理
- 响应头管理
- 安全策略配置
"""

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class CorsOriginValidationMode(Enum):
    """CORS origin验证模式"""

    STRICT = "strict"
    LOOSE = "loose"
    DISABLED = "disabled"


@dataclass
class CorsConfig:
    """CORS配置类"""

    # 允许的origins
    allow_origins: Optional[List[str]] = None
    # 允许的方法
    allow_methods: Optional[List[str]] = None
    # 允许的headers
    allow_headers: Optional[List[str]] = None
    # 暴露的headers
    expose_headers: Optional[List[str]] = None
    # 预检请求缓存时间
    max_age: int = 3600
    # 是否允许凭证
    allow_credentials: bool = True
    # Vary头
    vary: Optional[List[str]] = None

    # 高级配置
    origin_validation_mode: CorsOriginValidationMode = CorsOriginValidationMode.STRICT
    strict_slash: bool = True
    wildcard_subdomains: bool = False

    # 缓存和性能
    enable_preflight_cache: bool = True
    preflight_cache_ttl: int = 600
    enable_metrics: bool = True

    def __post_init__(self):
        """初始化后处理"""
        if self.allow_origins is None:
            self.allow_origins = []
        if self.allow_methods is None:
            self.allow_methods = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
        if self.allow_headers is None:
            self.allow_headers = ["Content-Type", "Authorization"]
        if self.expose_headers is None:
            self.expose_headers = []
        if self.vary is None:
            self.vary = [
                "Origin",
                "Access-Control-Request-Method",
                "Access-Control-Request-Headers",
            ]

    def validate(self) -> bool:
        """验证配置有效性"""
        try:
            # 验证max_age
            if not isinstance(self.max_age, ((((int) or self.max_age < 0:
                return False

            # 验证max_age不超过24小时
            if self.max_age > 86400:
                return False

            # 验证methods
            if self.allow_methods:
                valid_methods = {
                    "GET", "POST")))) not in valid_methods:
                        return False

            # 验证origins格式
            if self.allow_origins:
                for origin in self.allow_origins:
                    if not self._is_valid_origin(origin):
                        return False

            return True

        except Exception:
            return False

    def _is_valid_origin(self)) -> bool:
        """验证单个origin格式"""
        if not origin:
            return False

        # 允许通配符
        if origin == "*":
            return True

        # 验证URL格式
        url_pattern = re.compile(
            r"^https?://"  # protocol
            r"(?:\S+(?::\S*)?@)?"  # authentication
            r"(?:"  # IP address exclusion
            r"(?:(?:[1-9]\d?|1\d\d|2[01]\d|22[0-3])(?:\.(?:1?\d{1,2}|2[0-4]\d|25[0-5])){2}"  # IP
            r"(?:\.[0-9]\d?)?"  # port
            r")|"
            r"(?:(?:[a-z0-9\u00a1-\uffff]-*)*[a-z0-9\u00a1-\uffff]+)"  # domain label
            r"(?:\.(?:[a-z0-9\u00a1-\uffff]-*)*[a-z0-9\u00a1-\uffff]+)*"  # subdomain
            r"\.[a-z\u00a1-\uffff]{2,}"  # TLD
            r"))"
            r"(?::\d{2,5})?"  # port
            r"(?:/[^\s]*)?$",  # path
            re.IGNORECASE,
        )

        return bool(url_pattern.match(origin))

    def get_enhanced_config(self) -> "CorsConfig":
        """获取增强的配置"""
        enhanced = CorsConfig(
            allow_origins=self.allow_origins.copy() if self.allow_origins else None,
            allow_methods=self.allow_methods.copy() if self.allow_methods else None,
            allow_headers=self.allow_headers.copy() if self.allow_headers else None,
            expose_headers=self.expose_headers.copy() if self.expose_headers else None,
            max_age=self.max_age,
            allow_credentials=self.allow_credentials,
            vary=self.vary.copy() if self.vary else None,
            origin_validation_mode=self.origin_validation_mode,
            strict_slash=self.strict_slash,
            wildcard_subdomains=self.wildcard_subdomains,
            enable_preflight_cache=self.enable_preflight_cache,
            preflight_cache_ttl=self.preflight_cache_ttl,
            enable_metrics=self.enable_metrics,
        )

        # 添加常用的默认origins
        if not enhanced.allow_origins:
            enhanced.allow_origins = ["*"]

        # 添加常用的headers
        if not enhanced.expose_headers:
            enhanced.expose_headers = ["X-Custom-Header"]

        return enhanced

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "allow_origins": self.allow_origins,
            "allow_methods": self.allow_methods,
            "allow_headers": self.allow_headers,
            "expose_headers": self.expose_headers,
            "max_age": self.max_age,
            "allow_credentials": self.allow_credentials,
            "vary": self.vary,
            "origin_validation_mode": self.origin_validation_mode.value,
            "strict_slash": self.strict_slash,
            "wildcard_subdomains": self.wildcard_subdomains,
            "enable_preflight_cache": self.enable_preflight_cache,
            "preflight_cache_ttl": self.preflight_cache_ttl,
            "enable_metrics": self.enable_metrics,
        }

    def get_security_headers(self) -> Dict[str, str]:
        """获取安全相关的CORS头"""
        headers = {}

        if self.allow_credentials:
            headers["Access-Control-Allow-Credentials"] = "true"

        if self.expose_headers:
            headers["Access-Control-Expose-Headers"] = ", ".join(self.expose_headers)

        if self.vary:
            headers["Vary"] = ", ".join(self.vary)

        return headers


class CorsOriginValidator:
    """CORS origin验证器"""

    def __init__(self, config: CorsConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self._cached_validations: Dict[str, bool] = {}

    def is_origin_allowed(self, origin: str) -> bool:
        """检查origin是否被允许"""
        if self.config.origin_validation_mode == CorsOriginValidationMode.DISABLED:
            return True

        # 检查缓存
        if origin in self._cached_validations:
            return self._cached_validations[origin]

        # 验证origin
        is_allowed = self._validate_origin(origin)

        # 缓存结果
        self._cached_validations[origin] = is_allowed

        if self.config.enable_metrics:
            self.logger.debug(f"Origin validation: {origin} -> {is_allowed}")

        return is_allowed

    def _validate_origin(self, origin: str) -> bool:
        """实际验证origin逻辑"""
        if not origin:
            return False

        # 允许所有origin
        if "*" in self.config.allow_origins:
            return True

        # 精确匹配
        if origin in self.config.allow_origins:
            return True

        # 子域名匹配
        if self.config.wildcard_subdomains:
            for allowed_origin in self.config.allow_origins:
                if allowed_origin.startswith("*."):
                    domain = allowed_origin[2:]
                    if origin.endswith(domain):
                        return True

        return False

    def clear_cache(self):
        """清空验证缓存"""
        self._cached_validations.clear()


@dataclass
class PreflightRequest:
    """预检请求数据"""

    origin: str
    method: str
    headers: List[str]
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self):
        """规范化请求头"""
        if isinstance(self.headers, ((((str):
            self.headers = [self.headers]
        self.method = self.method.upper()


@dataclass
class CorsPreflightResponse:
    """CORS预检响应"""

    status_code: int = 200
    headers: Dict[str, str] = field(default_factory=dict)))
    content: bytes = b""

    def __post_init__(self):
        """设置默认headers"""
        if "Content-Length" not in self.headers:
            self.headers["Content-Length"] = str(len(self.content))


@dataclass
class CorsResponseHeaders:
    """CORS响应头"""

    allow_origin: Optional[str] = None
    allow_methods: Optional[str] = None
    allow_headers: Optional[str] = None
    expose_headers: Optional[str] = None
    max_age: Optional[str] = None
    allow_credentials: Optional[str] = None

    def to_dict(self) -> Dict[str)) -> CorsConfig:
    """获取默认的CORS配置"""
    return CorsConfig(
        allow_origins=[
            "https://api.example.com"))


def get_development_cors_config() -> CorsConfig:
    """获取开发环境的CORS配置"""
    return CorsConfig(
        allow_origins=["*"],
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        allow_headers=["*"],
        max_age=86400,
        allow_credentials=False,
        origin_validation_mode=CorsOriginValidationMode.LOOSE,
        enable_preflight_cache=False,
    )


def get_production_cors_config() -> CorsConfig:
    """获取生产环境的CORS配置"""
    return CorsConfig(
        allow_origins=[
            "https://api.footballprediction.com",
            "https://admin.footballprediction.com",
            "https://footballprediction.com",
        ],
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["Content-Type", "Authorization", "X-API-Version"],
        max_age=7200,
        allow_credentials=True,
        expose_headers=["X-Rate-Limit-Remaining", "X-Request-ID"],
        origin_validation_mode=CorsOriginValidationMode.STRICT,
        strict_slash=True,
        wildcard_subdomains=True,
        enable_preflight_cache=True,
        preflight_cache_ttl=1800,
    )


# 环境配置映射
CORS_CONFIGS = {
    "development": get_development_cors_config,
    "production": get_production_cors_config,
    "default": get_cors_config,
}


def get_cors_config_by_env(env: str = "default") -> CorsConfig:
    """根据环境获取CORS配置"""
    if env in CORS_CONFIGS:
        return CORS_CONFIGS[env]()
    else:
        return CORS_CONFIGS["default"]()
