# 📚 AICultureKit API 参考文档

## 🎯 概览

本文档提供 AICultureKit 各模块的详细API参考信息。

## 📦 核心模块 (src.core)

### Config 类

配置管理类，用于处理应用程序配置。

```python
from src.core import Config, config

# 创建配置实例
cfg = Config()

# 或使用全局实例
from src.core import config
```

**方法:**

- `get(key: str, default: Any = None) -> Any`: 获取配置项
- `set(key: str, value: Any) -> None`: 设置配置项
- `save() -> None`: 保存配置到文件

### Logger 类

日志管理类，提供统一的日志接口。

```python
from src.core import Logger, logger

# 创建日志器
custom_logger = Logger.setup_logger("my_module", "DEBUG")

# 或使用默认日志器
from src.core import logger
logger.info("这是一条信息")
```

### 异常类

```python
from src.core import AICultureKitError, ConfigError, DataError

# 基础异常
raise AICultureKitError("基础错误")

# 配置相关异常
raise ConfigError("配置错误")

# 数据处理异常
raise DataError("数据错误")
```

## 🗄️ 数据模型 (src.models)

### User 类

用户数据模型。

```python
from src.models import User, UserRole

user = User(
    id="user_123",
    username="testuser",
    email="test@example.com",
    role=UserRole.CREATOR
)

# 转换为字典
user_dict = user.to_dict()
```

**属性:**

- `id: str`: 用户唯一标识
- `username: str`: 用户名
- `email: str`: 邮箱地址
- `role: UserRole`: 用户角色
- `created_at: datetime`: 创建时间
- `metadata: Dict[str, Any]`: 元数据

### Content 类

内容数据模型。

```python
from src.models import Content, ContentType

content = Content(
    id="content_123",
    title="示例内容",
    content_type=ContentType.TEXT,
    content_data="这是内容数据",
    author_id="user_123"
)
```

**属性:**

- `id: str`: 内容唯一标识
- `title: str`: 内容标题
- `content_type: ContentType`: 内容类型
- `content_data: Union[str, bytes, Dict]`: 内容数据
- `author_id: str`: 作者ID
- `tags: List[str]`: 标签列表

### AnalysisResult 类

分析结果数据模型。

```python
from src.models import AnalysisResult

result = AnalysisResult(
    id="analysis_123",
    content_id="content_123",
    analysis_type="sentiment",
    result_data={"sentiment": "positive", "confidence": 0.95},
    confidence_score=0.95
)
```

## ⚙️ 业务服务 (src.services)

### ContentAnalysisService

内容分析服务，提供内容分析功能。

```python
from src.services import service_manager
import asyncio

async def analyze_content():
    # 获取服务实例
    analysis_service = service_manager.get_service("ContentAnalysisService")

    # 初始化服务
    await analysis_service.initialize()

    # 分析内容
    result = await analysis_service.analyze_content(content)

    return result
```

**主要方法:**

- `analyze_content(content: Content) -> Optional[AnalysisResult]`: 分析单个内容
- `batch_analyze(contents: List[Content]) -> List[AnalysisResult]`: 批量分析

### UserProfileService

用户画像服务，生成和管理用户画像。

```python
async def generate_profile():
    profile_service = service_manager.get_service("UserProfileService")
    await profile_service.initialize()

    # 生成用户画像
    profile = await profile_service.generate_profile(user)

    return profile
```

**主要方法:**

- `generate_profile(user: User) -> UserProfile`: 生成用户画像
- `get_profile(user_id: str) -> Optional[UserProfile]`: 获取用户画像
- `update_profile(user_id: str, updates: Dict) -> Optional[UserProfile]`: 更新画像

### ServiceManager

服务管理器，管理所有业务服务。

```python
from src.services import service_manager

# 初始化所有服务
await service_manager.initialize_all()

# 获取特定服务
service = service_manager.get_service("ContentAnalysisService")

# 关闭所有服务
await service_manager.shutdown_all()
```

## 🛠️ 工具模块 (src.utils)

### FileUtils

文件处理工具类。

```python
from src.utils import FileUtils
from pathlib import Path

# 确保目录存在
FileUtils.ensure_dir("data/uploads")

# 读写JSON文件
data = FileUtils.read_json("config.json")
FileUtils.write_json(data, "output.json")

# 获取文件信息
hash_value = FileUtils.get_file_hash("document.pdf")
size = FileUtils.get_file_size("document.pdf")
```

### DataValidator

数据验证工具类。

```python
from src.utils import DataValidator

# 验证邮箱和URL
is_valid = DataValidator.is_valid_email("test@example.com")
is_url_valid = DataValidator.is_valid_url("https://example.com")

# 验证必需字段
missing = DataValidator.validate_required_fields(
    data={"name": "test"},
    required_fields=["name", "email"]
)  # 返回 ["email"]

# 验证数据类型
invalid = DataValidator.validate_data_types(
    data={"age": "25"},
    type_specs={"age": int}
)  # 返回类型错误信息
```

### TimeUtils

时间处理工具类。

```python
from src.utils import TimeUtils
from datetime import datetime

# 获取当前UTC时间
now = TimeUtils.now_utc()

# 时间戳转换
dt = TimeUtils.timestamp_to_datetime(1625097600)
timestamp = TimeUtils.datetime_to_timestamp(now)

# 格式化和解析
formatted = TimeUtils.format_datetime(now, "%Y-%m-%d")
parsed = TimeUtils.parse_datetime("2023-01-01", "%Y-%m-%d")
```

### CryptoUtils

加密和ID生成工具类。

```python
from src.utils import CryptoUtils

# 生成ID
uuid = CryptoUtils.generate_uuid()
short_id = CryptoUtils.generate_short_id(8)

# 字符串哈希
md5_hash = CryptoUtils.hash_string("hello", "md5")
sha256_hash = CryptoUtils.hash_string("hello", "sha256")

# 密码哈希
hashed_password = CryptoUtils.hash_password("mypassword")
```

### StringUtils

字符串处理工具类。

```python
from src.utils import StringUtils

# 截断字符串
truncated = StringUtils.truncate("very long text", 10)

# URL友好化
slug = StringUtils.slugify("Hello World!")  # "hello-world"

# 命名转换
snake_case = StringUtils.camel_to_snake("camelCase")  # "camel_case"
camel_case = StringUtils.snake_to_camel("snake_case")  # "snakeCase"

# 文本清理和数字提取
clean = StringUtils.clean_text("  hello   world  ")  # "hello world"
numbers = StringUtils.extract_numbers("Price: $12.34")  # [12.34]
```

### DictUtils

字典处理工具类。

```python
from src.utils import DictUtils

# 深度合并字典
dict1 = {"a": {"b": 1}}
dict2 = {"a": {"c": 2}}
merged = DictUtils.deep_merge(dict1, dict2)  # {"a": {"b": 1, "c": 2}}

# 扁平化字典
nested = {"user": {"name": "John", "age": 30}}
flat = DictUtils.flatten_dict(nested)  # {"user.name": "John", "user.age": 30}

# 过滤None值
filtered = DictUtils.filter_none_values({"a": 1, "b": None})  # {"a": 1}
```

## 🧪 测试示例

```python
# 运行所有测试
python -m pytest tests/ -v

# 运行特定测试
python -m pytest tests/test_basic.py -v

# 运行覆盖率测试
python -m pytest tests/ --cov=src --cov-report=html
```

## 🔧 使用示例

### 完整工作流示例

```python
import asyncio
from src.core import logger
from src.models import User, Content, ContentType, UserRole
from src.services import service_manager
from src.utils import CryptoUtils

async def main():
    # 初始化服务
    await service_manager.initialize_all()

    # 创建用户
    user = User(
        id=CryptoUtils.generate_uuid(),
        username="ai_creator",
        email="creator@aiculture.com",
        role=UserRole.CREATOR
    )

    # 创建内容
    content = Content(
        id=CryptoUtils.generate_uuid(),
        title="AI文化产业分析",
        content_type=ContentType.TEXT,
        content_data="这是一篇关于AI在文化产业应用的分析文章...",
        author_id=user.id
    )

    # 分析内容
    analysis_service = service_manager.get_service("ContentAnalysisService")
    result = await analysis_service.analyze_content(content)

    # 生成用户画像
    profile_service = service_manager.get_service("UserProfileService")
    profile = await profile_service.generate_profile(user)

    logger.info(f"分析结果: {result.result_data}")
    logger.info(f"用户画像: {profile.interests}")

    # 清理
    await service_manager.shutdown_all()

if __name__ == "__main__":
    asyncio.run(main())
```

---

**📝 注意**: 这是基础版本的API文档。随着功能的扩展，将持续更新此文档。
