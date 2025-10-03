"""
环境变量验证模块
Environment Variable Validation Module

提供环境变量的验证、类型转换和默认值管理
"""

import os
import re
import logging
from typing import Any, Dict, List, Optional, Type, Union, get_type_hints
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class ValidationSeverity(Enum):
    """验证严重程度"""
    INFO = "info"
    WARNING = os.getenv("ENV_VALIDATOR_WARNING_23")
    ERROR = "error"
    CRITICAL = os.getenv("ENV_VALIDATOR_CRITICAL_23")


@dataclass
class ValidationResult:
    """验证结果"""
    is_valid: bool
    severity: ValidationSeverity
    message: str
    var_name: str
    actual_value: Any = None
    expected_value: Any = None
    suggestion: Optional[str] = None


@dataclass
class EnvVarDefinition:
    """环境变量定义"""
    name: str
    type: Type
    required: bool = True
    default: Any = None
    description: str = ""
    choices: Optional[List[Any]] = None
    min_value: Optional[Union[int, float]] = None
    max_value: Optional[Union[int, float]] = None
    pattern: Optional[str] = None
    validator: Optional[callable] = None
    secret: bool = False
    category: str = os.getenv("ENV_VALIDATOR_STR_52")


class EnvironmentValidator:
    """环境变量验证器"""

    def __init__(self):
        """初始化验证器"""
        self.definitions: Dict[str, EnvVarDefinition] = {}
        self._setup_default_definitions()
        self.validation_results: List[ValidationResult] = []

    def _setup_default_definitions(self):
        """设置默认的环境变量定义"""
        # 基础配置
        self.add_definition(EnvVarDefinition(
            name = os.getenv("ENV_VALIDATOR_NAME_67"),
            type=str,
            required=True,
            default = os.getenv("ENV_VALIDATOR_DEFAULT_70"),
            choices=["development", "testing", "staging", "production"],
            description="运行环境",
            category="基础配置"
        ))

        # 数据库配置
        self.add_definition(EnvVarDefinition(
            name = os.getenv("ENV_VALIDATOR_NAME_75"),
            type=str,
            required=True,
            description = os.getenv("ENV_VALIDATOR_DESCRIPTION_80"),
            validator=self._validate_database_url,
            secret=True,
            category="数据库"
        ))

        self.add_definition(EnvVarDefinition(
            name = os.getenv("ENV_VALIDATOR_NAME_84"),
            type=int,
            required=False,
            default=10,
            min_value=1,
            max_value=100,
            description = os.getenv("ENV_VALIDATOR_DESCRIPTION_90"),
            category="数据库"
        ))

        self.add_definition(EnvVarDefinition(
            name = os.getenv("ENV_VALIDATOR_NAME_94"),
            type=int,
            required=False,
            default=20,
            min_value=0,
            max_value=100,
            description = os.getenv("ENV_VALIDATOR_DESCRIPTION_98"),
            category="数据库"
        ))

        # Redis配置
        self.add_definition(EnvVarDefinition(
            name = os.getenv("ENV_VALIDATOR_NAME_103"),
            type=str,
            required=False,
            default="localhost"  # 生产环境应通过环境变量HOST配置,
            description = os.getenv("ENV_VALIDATOR_DESCRIPTION_108"),
            category="Redis"
        ))

        self.add_definition(EnvVarDefinition(
            name = os.getenv("ENV_VALIDATOR_NAME_113"),
            type=int,
            required=False,
            default=6379,
            min_value=1,
            max_value=65535,
            description = os.getenv("ENV_VALIDATOR_DESCRIPTION_117"),
            category="Redis"
        ))

        self.add_definition(EnvVarDefinition(
            name = os.getenv("ENV_VALIDATOR_NAME_120"),
            type=str,
            required=False,
            default=None,
            description = os.getenv("ENV_VALIDATOR_DESCRIPTION_124"),
            secret=True,
            category="Redis"
        ))

        # API配置
        self.add_definition(EnvVarDefinition(
            name = os.getenv("ENV_VALIDATOR_NAME_129"),
            type=str,
            required=False,
            default="localhost"  # 生产环境应通过环境变量HOST配置,
            validator=self._validate_host,
            description = os.getenv("ENV_VALIDATOR_DESCRIPTION_134"),
            category="API"
        ))

        self.add_definition(EnvVarDefinition(
            name = os.getenv("ENV_VALIDATOR_NAME_138"),
            type=int,
            required=False,
            default=8000,
            min_value=1,
            max_value=65535,
            description = os.getenv("ENV_VALIDATOR_DESCRIPTION_144"),
            category="API"
        ))

        self.add_definition(EnvVarDefinition(
            name = os.getenv("ENV_VALIDATOR_NAME_147"),
            type=str,
            required=False,
            default="info",
            choices=["debug", "info", "warning", "error", "critical"],
            description="日志级别",
            category="API"
        ))

        # 安全配置
        self.add_definition(EnvVarDefinition(
            name = os.getenv("ENV_VALIDATOR_NAME_157"),
            type=str,
            required=True,
            description = os.getenv("ENV_VALIDATOR_DESCRIPTION_160"),
            validator=self._validate_secret_key,
            secret=True,
            category="安全"
        ))

        self.add_definition(EnvVarDefinition(
            name = os.getenv("ENV_VALIDATOR_NAME_166"),
            type=str,
            required=True,
            description="应用密钥",
            validator=self._validate_secret_key,
            secret=True,
            category="安全"
        ))

        self.add_definition(EnvVarDefinition(
            name = os.getenv("ENV_VALIDATOR_NAME_175"),
            type=int,
            required=False,
            default=30,
            min_value=1,
            max_value=1440,  # 24小时
            description = os.getenv("ENV_VALIDATOR_DESCRIPTION_180"),
            category="安全"
        ))

        # 缓存配置
        self.add_definition(EnvVarDefinition(
            name = os.getenv("ENV_VALIDATOR_NAME_183"),
            type=bool,
            required=False,
            default=True,
            description = os.getenv("ENV_VALIDATOR_DESCRIPTION_187"),
            category="缓存"
        ))

        self.add_definition(EnvVarDefinition(
            name = os.getenv("ENV_VALIDATOR_NAME_191"),
            type=int,
            required=False,
            default=300,
            min_value=0,
            description = os.getenv("ENV_VALIDATOR_DESCRIPTION_197"),
            category="缓存"
        ))

        # CORS配置
        self.add_definition(EnvVarDefinition(
            name = os.getenv("ENV_VALIDATOR_NAME_201"),
            type=str,
            required=False,
            default=None,
            validator=self._validate_cors_origins,
            description = os.getenv("ENV_VALIDATOR_DESCRIPTION_207"),
            category="API"
        ))

        # 监控配置
        self.add_definition(EnvVarDefinition(
            name = os.getenv("ENV_VALIDATOR_NAME_211"),
            type=bool,
            required=False,
            default=True,
            description = os.getenv("ENV_VALIDATOR_DESCRIPTION_213"),
            category="监控"
        ))

        self.add_definition(EnvVarDefinition(
            name = os.getenv("ENV_VALIDATOR_NAME_218"),
            type=str,
            required=False,
            default=None,
            validator=self._validate_sentry_dsn,
            secret=True,
            description = os.getenv("ENV_VALIDATOR_DESCRIPTION_223"),
            category="监控"
        ))

        # 性能配置
        self.add_definition(EnvVarDefinition(
            name = os.getenv("ENV_VALIDATOR_NAME_229"),
            type=float,
            required=False,
            default=1.0,
            min_value=0.1,
            max_value=10.0,
            description = os.getenv("ENV_VALIDATOR_DESCRIPTION_234"),
            category="性能"
        ))

        # Celery配置
        self.add_definition(EnvVarDefinition(
            name = os.getenv("ENV_VALIDATOR_NAME_239"),
            type=str,
            required=False,
            default=None,
            description = os.getenv("ENV_VALIDATOR_DESCRIPTION_242"),
            category="任务队列"
        ))

    def add_definition(self, definition: EnvVarDefinition):
        """添加环境变量定义"""
        self.definitions[definition.name] = definition

    def validate_all(self, env_file: Optional[Path] = None) -> List[ValidationResult]:
        """
        验证所有环境变量

        Args:
            env_file: 环境文件路径（可选）

        Returns:
            验证结果列表
        """
        self.validation_results = []

        # 加载环境文件
        if env_file and env_file.exists():
            self._load_env_file(env_file)

        # 验证每个定义的变量
        for var_name, definition in self.definitions.items():
            self._validate_variable(var_name, definition)

        # 检查额外的环境变量
        self._check_extra_variables()

        # 检查依赖关系
        self._check_dependencies()

        return self.validation_results

    def _load_env_file(self, env_file: Path):
        """加载环境文件"""
        try:
            from dotenv import load_dotenv
            load_dotenv(env_file)
            logger.info(f"已加载环境文件: {env_file}")
        except ImportError:
            logger.warning("python-dotenv未安装，无法加载.env文件")

    def _validate_variable(self, var_name: str, definition: EnvVarDefinition):
        """验证单个变量"""
        raw_value = os.getenv(var_name)

        # 检查必需的变量
        if definition.required and raw_value is None:
            if definition.default is not None:
                raw_value = str(definition.default)
                os.environ[var_name] = raw_value
                self.validation_results.append(ValidationResult(
                    is_valid=True,
                    severity=ValidationSeverity.INFO,
                    message=f"使用默认值: {definition.default}",
                    var_name=var_name,
                    actual_value=definition.default
                ))
            else:
                self.validation_results.append(ValidationResult(
                    is_valid=False,
                    severity=ValidationSeverity.ERROR,
                    message = os.getenv("ENV_VALIDATOR_MESSAGE_315"),
                    var_name=var_name,
                    suggestion=f"请设置 {var_name} 环境变量"
                ))
                return

        # 使用默认值或跳过
        if raw_value is None:
            if definition.default is not None:
                os.environ[var_name] = str(definition.default)
                self.validation_results.append(ValidationResult(
                    is_valid=True,
                    severity=ValidationSeverity.INFO,
                    message=f"使用默认值: {definition.default}",
                    var_name=var_name,
                    actual_value=definition.default
                ))
            return

        # 类型转换
        try:
            if definition.type == bool:
                value = self._convert_to_bool(raw_value)
            elif definition.type == int:
                value = int(raw_value)
            elif definition.type == float:
                value = float(raw_value)
            else:
                value = raw_value
        except (ValueError, TypeError) as e:
            self.validation_results.append(ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.ERROR,
                message=f"类型转换失败: {e}",
                var_name=var_name,
                actual_value=raw_value,
                expected_value=definition.type.__name__
            ))
            return

        # 自定义验证
        if definition.validator:
            try:
                result = definition.validator(value)
                if isinstance(result, ValidationResult):
                    self.validation_results.append(result)
                    if not result.is_valid:
                        return
            except Exception as e:
                self.validation_results.append(ValidationResult(
                    is_valid=False,
                    severity=ValidationSeverity.ERROR,
                    message=f"验证失败: {e}",
                    var_name=var_name,
                    actual_value=value
                ))
                return

        # 选择验证
        if definition.choices and value not in definition.choices:
            self.validation_results.append(ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.ERROR,
                message=f"值不在允许的选项中: {definition.choices}",
                var_name=var_name,
                actual_value=value,
                suggestion=f"请选择: {', '.join(map(str, definition.choices))}"
            ))
            return

        # 范围验证
        if definition.min_value is not None and value < definition.min_value:
            self.validation_results.append(ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.ERROR,
                message=f"值小于最小值: {definition.min_value}",
                var_name=var_name,
                actual_value=value,
                expected_value=f">= {definition.min_value}"
            ))
            return

        if definition.max_value is not None and value > definition.max_value:
            self.validation_results.append(ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.ERROR,
                message=f"值大于最大值: {definition.max_value}",
                var_name=var_name,
                actual_value=value,
                expected_value=f"<= {definition.max_value}"
            ))
            return

        # 正则验证
        if definition.pattern and not re.match(definition.pattern, str(value)):
            self.validation_results.append(ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.ERROR,
                message=f"值不符合要求的格式",
                var_name=var_name,
                actual_value=value,
                expected_value=definition.pattern
            ))
            return

        # 成功
        self.validation_results.append(ValidationResult(
            is_valid=True,
            severity=ValidationSeverity.INFO,
            message="验证通过",
            var_name=var_name,
            actual_value = os.getenv("ENV_VALIDATOR_ACTUAL_VALUE_421") if definition.secret else value
        ))

    def _convert_to_bool(self, value: str) -> bool:
        """转换字符串为布尔值"""
        return value.lower() in ('true', '1', 'yes', 'on', 'enabled', 'y')

    def _validate_database_url(self, value: str) -> ValidationResult:
        """验证数据库URL"""
        try:
            parsed = urlparse(value)

            if parsed.scheme not in ('postgresql', 'sqlite', 'mysql'):
                return ValidationResult(
                    is_valid=False,
                    severity=ValidationSeverity.ERROR,
                    message=f"不支持的数据库类型: {parsed.scheme}",
                    var_name = os.getenv("ENV_VALIDATOR_NAME_75"),
                    actual_value=value,
                    suggestion = os.getenv("ENV_VALIDATOR_SUGGESTION_440")
                )

            if parsed.scheme == 'postgresql':
                if not all([parsed.hostname, parsed.path]):
                    return ValidationResult(
                        is_valid=False,
                        severity=ValidationSeverity.ERROR,
                        message = os.getenv("ENV_VALIDATOR_MESSAGE_451"),
                        var_name = os.getenv("ENV_VALIDATOR_NAME_75"),
                        actual_value=value
                    )

            return ValidationResult(
                is_valid=True,
                severity=ValidationSeverity.INFO,
                message = os.getenv("ENV_VALIDATOR_MESSAGE_458"),
                var_name = os.getenv("ENV_VALIDATOR_NAME_75")
            )

        except Exception as e:
            return ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.ERROR,
                message=f"数据库URL解析失败: {e}",
                var_name = os.getenv("ENV_VALIDATOR_NAME_75"),
                actual_value=value
            )

    def _validate_host(self, value: str) -> ValidationResult:
        """验证主机地址"""
        if value in ('0.0.0.0', '127.0.0.1', 'localhost'):
            return ValidationResult(
                is_valid=True,
                severity=ValidationSeverity.INFO,
                message = os.getenv("ENV_VALIDATOR_MESSAGE_475"),
                var_name = os.getenv("ENV_VALIDATOR_NAME_129")
            )

        # 简单的IP验证
        ip_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
        if re.match(ip_pattern, value):
            return ValidationResult(
                is_valid=True,
                severity=ValidationSeverity.INFO,
                message = os.getenv("ENV_VALIDATOR_MESSAGE_475"),
                var_name = os.getenv("ENV_VALIDATOR_NAME_129")
            )

        # 域名验证
        domain_pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$'
        if re.match(domain_pattern, value):
            return ValidationResult(
                is_valid=True,
                severity=ValidationSeverity.INFO,
                message = os.getenv("ENV_VALIDATOR_MESSAGE_475"),
                var_name = os.getenv("ENV_VALIDATOR_NAME_129")
            )

        return ValidationResult(
            is_valid=False,
            severity=ValidationSeverity.WARNING,
            message = os.getenv("ENV_VALIDATOR_MESSAGE_496"),
            var_name = os.getenv("ENV_VALIDATOR_NAME_129"),
            actual_value=value,
            suggestion = os.getenv("ENV_VALIDATOR_SUGGESTION_498")
        )

    def _validate_secret_key(self, value: str) -> ValidationResult:
        """验证密钥强度"""
        if len(value) < 32:
            return ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.ERROR,
                message=f"密钥长度不足: {len(value)} < 32",
                var_name = os.getenv("ENV_VALIDATOR_VAR_NAME_508"),
                actual_value=f"长度:{len(value)}",
                suggestion = os.getenv("ENV_VALIDATOR_SUGGESTION_511")
            )

        # 检查是否为弱密钥
        weak_patterns = [
            'password', 'secret', 'key', 'admin', 'test', 'dev',
            '123', 'abc', 'qwerty', 'letmein'
        ]

        value_lower = value.lower()
        for pattern in weak_patterns:
            if pattern in value_lower:
                return ValidationResult(
                    is_valid=False,
                    severity=ValidationSeverity.CRITICAL,
                    message = os.getenv("ENV_VALIDATOR_MESSAGE_522"),
                    var_name = os.getenv("ENV_VALIDATOR_VAR_NAME_508"),
                    actual_value="weak",
                    suggestion = os.getenv("ENV_VALIDATOR_SUGGESTION_525")
                )

        return ValidationResult(
            is_valid=True,
            severity=ValidationSeverity.INFO,
            message = os.getenv("ENV_VALIDATOR_MESSAGE_528"),
            var_name = os.getenv("ENV_VALIDATOR_VAR_NAME_508")
        )

    def _validate_cors_origins(self, value: str) -> ValidationResult:
        """验证CORS源"""
        if not value:
            return ValidationResult(
                is_valid=True,
                severity=ValidationSeverity.INFO,
                message = os.getenv("ENV_VALIDATOR_MESSAGE_537"),
                var_name = os.getenv("ENV_VALIDATOR_NAME_201")
            )

        origins = [o.strip() for o in value.split(',')]
        invalid_origins = []

        for origin in origins:
            if origin == '*':
                continue  # 允许所有源
            if not (origin.startswith('http://') or origin.startswith('https://')):
                invalid_origins.append(origin)

        if invalid_origins:
            return ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.WARNING,
                message=f"CORS源格式不正确: {invalid_origins}",
                var_name = os.getenv("ENV_VALIDATOR_NAME_201"),
                actual_value=value,
                suggestion = os.getenv("ENV_VALIDATOR_SUGGESTION_555")
            )

        return ValidationResult(
            is_valid=True,
            severity=ValidationSeverity.INFO,
            message = os.getenv("ENV_VALIDATOR_MESSAGE_561"),
            var_name = os.getenv("ENV_VALIDATOR_NAME_201")
        )

    def _validate_sentry_dsn(self, value: str) -> ValidationResult:
        """验证Sentry DSN"""
        if not value:
            return ValidationResult(
                is_valid=True,
                severity=ValidationSeverity.INFO,
                message = os.getenv("ENV_VALIDATOR_MESSAGE_567"),
                var_name = os.getenv("ENV_VALIDATOR_NAME_218")
            )

        if not value.startswith('https://'):
            return ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.ERROR,
                message = os.getenv("ENV_VALIDATOR_MESSAGE_574"),
                var_name = os.getenv("ENV_VALIDATOR_NAME_218"),
                actual_value=value[:20] + "..."
            )

        return ValidationResult(
            is_valid=True,
            severity=ValidationSeverity.INFO,
            message = os.getenv("ENV_VALIDATOR_MESSAGE_582"),
            var_name = os.getenv("ENV_VALIDATOR_NAME_218")
        )

    def _check_extra_variables(self):
        """检查额外的环境变量"""
        # 这里可以添加对未定义但存在的环境变量的检查
        pass

    def _check_dependencies(self):
        """检查变量依赖关系"""
        # 检查CORS_ORIGINS是否在生产环境配置
        env = os.getenv('ENVIRONMENT', 'development')
        if env == 'production':
            cors_origins = os.getenv('CORS_ORIGINS')
            if not cors_origins or cors_origins == '*':
                self.validation_results.append(ValidationResult(
                    is_valid=False,
                    severity=ValidationSeverity.ERROR,
                    message = os.getenv("ENV_VALIDATOR_MESSAGE_600"),
                    var_name = os.getenv("ENV_VALIDATOR_NAME_201"),
                    actual_value=cors_origins,
                    suggestion = os.getenv("ENV_VALIDATOR_SUGGESTION_602")
                ))

    def get_summary(self) -> Dict[str, Any]:
        """获取验证摘要"""
        total = len(self.validation_results)
        errors = sum(1 for r in self.validation_results if r.severity == ValidationSeverity.ERROR)
        warnings = sum(1 for r in self.validation_results if r.severity == ValidationSeverity.WARNING)
        critical = sum(1 for r in self.validation_results if r.severity == ValidationSeverity.CRITICAL)

        return {
            'total': total,
            'valid': total - errors - warnings - critical,
            'errors': errors,
            'warnings': warnings,
            'critical': critical,
            'success': critical == 0 and errors == 0
        }

    def print_report(self):
        """打印验证报告"""
        summary = self.get_summary()

        print("\n" + "=" * 60)
        print("环境变量验证报告")
        print("=" * 60)
        print(f"总计: {summary['total']}")
        print(f"✅ 通过: {summary['valid']}")
        print(f"⚠️ 警告: {summary['warnings']}")
        print(f"❌ 错误: {summary['errors']}")
        print(f"🚨 严重: {summary['critical']}")
        print()

        # 按严重程度分组显示
        grouped = {}
        for result in self.validation_results:
            severity = result.severity.value
            if severity not in grouped:
                grouped[severity] = []
            grouped[severity].append(result)

        for severity in ['critical', 'error', 'warning', 'info']:
            if severity in grouped:
                icon = {'critical': '🚨', 'error': '❌', 'warning': '⚠️', 'info': '✅'}[severity]
                print(f"{icon} {severity.upper()}:")
                for result in grouped[severity]:
                    print(f"  {result.var_name}: {result.message}")
                    if result.suggestion:
                        print(f"    建议: {result.suggestion}")
                print()

        # 总结
        if summary['success']:
            print("🎉 所有必需的环境变量配置正确！")
        else:
            print("⚠️ 请修复上述问题后继续。")

    def export_to_dict(self) -> Dict[str, Any]:
        """导出验证后的配置为字典"""
        config = {}
        for var_name, definition in self.definitions.items():
            value = os.getenv(var_name)
            if value is not None:
                # 类型转换
                if definition.type == bool:
                    config[var_name] = self._convert_to_bool(value)
                elif definition.type == int:
                    config[var_name] = int(value)
                elif definition.type == float:
                    config[var_name] = float(value)
                else:
                    config[var_name] = value
            elif definition.default is not None:
                config[var_name] = definition.default

        return config