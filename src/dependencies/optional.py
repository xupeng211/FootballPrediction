"""
可选依赖管理模块

管理所有可选的、可能不存在的依赖导入。
如果某个依赖不存在，会提供一个安全的替代实现或None值。
"""

import logging
import sys
import warnings
from typing import Any, Optional, TypeVar, Union

logger = logging.getLogger(__name__)

T = TypeVar("T")


class MissingDependency:
    """缺失依赖的占位符"""

    def __init__(self, name: str):
        self.name = name

    def __call__(self, *args, **kwargs):
        warnings.warn(f"依赖 {self.name} 未安装，相关功能将被禁用", ImportWarning)
        return None

    def __getattr__(self, item):
        warnings.warn(f"依赖 {self.name} 未安装，相关功能将被禁用", ImportWarning)
        return MissingDependency(f"{self.name}.{item}")

    def __bool__(self):
        return False


# 尝试导入可选依赖，失败则提供占位符
def try_import(module_name: str, package: str = None) -> Union[Any, MissingDependency]:
    """
    尝试导入模块，失败时返回占位符

    Args:
        module_name: 模块名
        package: 包名（用于相对导入）

    Returns:
        模块对象或占位符
    """
    try:
        if package:
            from importlib import import_module

            return import_module(f"{package}.{module_name}")
        else:
            return __import__(module_name)
    except ImportError:
        return MissingDependency(module_name)
    except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
        # 某些模块导入时可能会有属性错误，但不一定是严重问题
        # 只在调试模式下显示警告
        if __debug__ and module_name == "matplotlib":
            # matplotlib 的 __version__ 属性问题很常见，静默处理
            pass
        elif isinstance(e, AttributeError) and "__version__" in str(e):
            # 版本属性错误，静默处理
            pass
        else:
            warnings.warn(f"导入 {module_name} 时发生意外错误: {e}", RuntimeWarning)
        return MissingDependency(module_name)


# 常见的可选依赖
# 数据处理
pandas = try_import("pandas")
numpy = try_import("numpy")
scipy = try_import("scipy")

# 机器学习
sklearn = try_import("sklearn")
torch = try_import("torch")
tensorflow = try_import("tensorflow")

# 数据可视化
matplotlib = try_import("matplotlib")
seaborn = try_import("seaborn")
plotly = try_import("plotly")

# 数据库驱动
psycopg2 = try_import("psycopg2")
pymongo = try_import("pymongo")
redis = try_import("redis")

# 异步数据库
asyncpg = try_import("asyncpg")
aiomongo = try_import("motor")

# Web爬虫
requests = try_import("requests")
beautifulsoup4 = try_import("bs4")
selenium = try_import("selenium")

# 缓存
redis_client = try_import("redis", "redis.client")

# 消息队列
celery = try_import("celery")
kafka = try_import("kafka-python", "kafka")
pika = try_import("pika")

# 监控
prometheus_client = try_import("prometheus_client")
statsd = try_import("statsd")

# 文档生成
sphinx = try_import("sphinx")
mkdocs = try_import("mkdocs")

# 性能分析
memory_profiler = try_import("memory_profiler")
pyinstrument = try_import("pyinstrument")

# 测试
locust = try_import("locust")
behave = try_import("behave")

# 速率限制
slowapi = try_import("slowapi")

# 验证
cerberus = try_import("cerberus")
pyjwt = try_import("jwt")

# 工具库
click = try_import("click")
rich = try_import("rich")
typer = try_import("typer")
loguru = try_import("loguru")

# 项目特定的可选依赖
# 这些可以根据项目需要添加
openlineage = try_import("openlineage")
mlflow = try_import("mlflow")
dvc = try_import("dvc")
great_expectations = try_import("great_expectations")


def safe_import(module_path: str, default: Optional[T] = None) -> Optional[T]:
    """
    安全地导入模块，返回默认值

    Args:
        module_path: 模块路径（如 'package.module.Class'）
        default: 默认值

    Returns:
        导入的对象或默认值
    """
    try:
        parts = module_path.split(".")
        module = __import__(parts[0])
        for part in parts[1:]:
            module = getattr(module, part)
        return module  # type: ignore[return-value]
    except (ImportError, AttributeError):
        return default


def has_dependency(dependency_name: str) -> bool:
    """
    检查依赖是否存在

    Args:
        dependency_name: 依赖名称（模块路径）

    Returns:
        是否存在
    """
    try:
        parts = dependency_name.split(".")
        module = __import__(parts[0])
        for part in parts[1:]:
            module = getattr(module, part)
        return True
    except (ImportError, AttributeError):
        return False


def get_dependency_version(dependency_name: str) -> Optional[str]:
    """
    获取依赖版本

    Args:
        dependency_name: 依赖名称

    Returns:
        版本号或None
    """
    try:
        module = sys.modules.get(dependency_name)
        if module is None:
            module = __import__(dependency_name)
        return getattr(module, "__version__", None)
    except (ImportError, AttributeError, KeyError, RuntimeError):
        return None


def check_optional_dependencies() -> dict:
    """
    检查所有可选依赖的状态

    Returns:
        依赖状态字典
    """
    dependencies = {
        "pandas": has_dependency("pandas"),
        "numpy": has_dependency("numpy"),
        "sklearn": has_dependency("sklearn"),
        "torch": has_dependency("torch"),
        "matplotlib": has_dependency("matplotlib"),
        "requests": has_dependency("requests"),
        "slowapi": has_dependency("slowapi"),
        "mlflow": has_dependency("mlflow"),
        "great_expectations": has_dependency("great_expectations"),
        "openlineage": has_dependency("openlineage"),
        "redis": has_dependency("redis"),
        "kafka": has_dependency("kafka"),
        "celery": has_dependency("celery"),
    }

    versions = {}
    for dep in dependencies:
        if dependencies[dep]:
            versions[dep] = get_dependency_version(dep)

    return {
        "available": {k: v for k, v in dependencies.items() if v},
        "missing": {k: v for k, v in dependencies.items() if not v},
        "versions": versions,
    }


# 导出便捷的检查函数
def has_pandas() -> bool:
    """检查是否安装了pandas"""
    return has_dependency("pandas")


def has_sklearn() -> bool:
    """检查是否安装了sklearn"""
    return has_dependency("sklearn")


def has_mlflow() -> bool:
    """检查是否安装了mlflow"""
    return has_dependency("mlflow")


def has_slowapi() -> bool:
    """检查是否安装了slowapi"""
    return has_dependency("slowapi")


def has_kafka() -> bool:
    """检查是否安装了kafka-python"""
    return has_dependency("kafka")


def has_redis() -> bool:
    """检查是否安装了redis"""
    return has_dependency("redis")


def has_celery() -> bool:
    """检查是否安装了celery"""
    return has_dependency("celery")


if __name__ == "__main__":
    # 打印依赖状态
    status = check_optional_dependencies()
    logger.info("可选依赖状态:")
    logger.info(f"✅ 可用: {list(status['available'].keys())}")
    logger.info(f"❌ 缺失: {list(status['missing'].keys())}")
    if status["versions"]:
        logger.info("\n版本信息:")
        for dep, version in status["versions"].items():
            if version:
                logger.info(f"  {dep}: {version}")
            else:
                logger.info(f"  {dep}: 未知版本")
