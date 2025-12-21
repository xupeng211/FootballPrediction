# API错误代码说明文档

## API错误代码完整参考

足球比赛结果预测系统 - 详细错误处理指南

Version: 1.0.0
Update: 2025-11-10
Author: Claude Code

---

## 📋 目录

- [错误概述](#错误概述)
- [错误分类体系](#错误分类体系)
- [认证与授权错误](#认证与授权错误)
- [请求验证错误](#请求验证错误)
- [业务逻辑错误](#业务逻辑错误)
- [系统与基础设施错误](#系统与基础设施错误)
- [第三方服务错误](#第三方服务错误)
- [错误处理最佳实践](#错误处理最佳实践)
- [开发者工具](#开发者工具)

---

## 🎯 错误概述

### 错误响应结构

所有API错误都遵循统一的响应格式：

```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "错误描述信息",
    "details": {
      "field": "相关字段名",
      "reason": "详细错误原因",
      "suggestion": "解决建议"
    },
    "context": {
      "request_id": "req_123456789",
      "timestamp": "2025-11-10T14:30:00Z",
      "endpoint": "/api/predictions"
    }
  },
  "meta": {
    "version": "v1.0.0",
    "documentation": "https://docs.football-prediction.com/errors"
  }
}
```

### HTTP状态码映射

| 状态码范围 | 错误类型 | 说明 |
|------------|----------|------|
| 400-499 | 客户端错误 | 请求格式、参数、权限等问题 |
| 500-599 | 服务器错误 | 系统内部、基础设施、第三方服务问题 |

### 错误严重级别

- **🔴 Critical**: 系统级错误，影响所有用户
- **🟠 High**: 功能级错误，影响特定功能使用
- **🟡 Medium**: 数据级错误，影响具体请求
- **🟢 Low**: 提示级错误，不影响核心功能

---

## 🏷️ 错误分类体系

### 分类原则

1. **按来源分类**: 客户端 vs 服务器 vs 第三方
2. **按功能分类**: 认证、验证、业务、系统
3. **按严重性分类**: Critical、High、Medium、Low
4. **按可恢复性分类**: 可自动重试 vs 需用户干预

### 错误代码命名规范

```
[CATEGORY]_[SUBCATEGORY]_[NUMBER]
```

- **CATEGORY**: 主要分类 (AUTH, VALIDATION, BUSINESS, SYSTEM)
- **SUBCATEGORY**: 子分类 (TOKEN, INPUT, PREDICTION, DATABASE)
- **NUMBER**: 三位数字编号 (001-999)

### 错误代码总览

| 分类 | 代码范围 | 说明 |
|------|----------|------|
| AUTH_* | 001-099 | 认证与授权相关错误 |
| VALIDATION_* | 100-199 | 请求数据验证错误 |
| BUSINESS_* | 200-299 | 业务逻辑错误 |
| SYSTEM_* | 300-399 | 系统基础设施错误 |
| EXTERNAL_* | 400-499 | 第三方服务错误 |
| RATE_LIMIT_* | 500-599 | 限流和配额错误 |

---

## 🔐 认证与授权错误 (AUTH_*)

### AUTH_001: Token缺失或格式错误

**严重级别**: 🟠 High
**HTTP状态码**: 401 Unauthorized

**描述**: 请求中缺少Authorization头或Token格式不正确

**触发条件**:
- 请求头中缺少Authorization字段
- Token格式不符合"Bearer <token>"规范
- Token中包含非法字符

**错误示例**:
```json
{
  "success": false,
  "error": {
    "code": "AUTH_001",
    "message": "认证Token缺失或格式错误",
    "details": {
      "reason": "请求头中缺少Authorization字段",
      "suggestion": "请在请求头中添加Authorization: Bearer <your_token>"
    }
  }
}
```

**解决方案**:
```python
# ✅ 正确的Token设置方式
headers = {
    "Authorization": "Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "Content-Type": "application/json"
}

# ❌ 错误的方式
headers = {
    "Authorization": "token eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",  # 错误格式
    # 或者缺少Authorization字段
}
```

### AUTH_002: Token已过期

**严重级别**: 🟡 Medium
**HTTP状态码**: 401 Unauthorized

**描述**: 认证Token已超过有效期

**触发条件**:
- Token过期时间已到
- 系统时间与Token签发时间差异过大

**解决方案**:
```python
import requests
from datetime import datetime

def make_authenticated_request(url, token):
    headers = {"Authorization": f"Bearer {token}"}

    response = requests.get(url, headers=headers)

    if response.status_code == 401:
        error_data = response.json()
        if error_data.get("error", {}).get("code") == "AUTH_002":
            # Token过期，重新获取
            new_token = refresh_token()
            headers["Authorization"] = f"Bearer {new_token}"
            response = requests.get(url, headers=headers)

    return response

def refresh_token():
    """刷新Token"""
    # 实现Token刷新逻辑
    pass
```

### AUTH_003: Token无效

**严重级别**: 🟠 High
**HTTP状态码**: 401 Unauthorized

**描述**: Token签名验证失败或已被撤销

**触发条件**:
- Token被管理员撤销
- Token签名被篡改
- Token格式解析失败

### AUTH_004: 用户名或密码错误

**严重级别**: 🟡 Medium
**HTTP状态码**: 401 Unauthorized

**描述**: 登录凭据不正确

**解决方案**:
```python
def login_with_retry(username, password, max_attempts=3):
    for attempt in range(max_attempts):
        response = requests.post("/auth/token", json={
            "username": username,
            "password": password
        })

        if response.status_code == 200:
            return response.json()
        elif response.status_code == 401:
            error_data = response.json()
            if error_data.get("error", {}).get("code") == "AUTH_004":
                print(f"登录失败，剩余尝试次数: {max_attempts - attempt - 1}")
                if attempt == max_attempts - 1:
                    raise Exception("账号或密码错误次数过多，请稍后再试")
            else:
                raise Exception(f"登录失败: {error_data.get('error', {}).get('message')}")
        else:
            response.raise_for_status()

    return None
```

### AUTH_005: 账户已被禁用

**严重级别**: 🟠 High
**HTTP状态码**: 403 Forbidden

**描述**: 用户账户被管理员禁用

**解决方案**: 联系客服或等待账户重新启用

---

## ✅ 请求验证错误 (VALIDATION_*)

### VALIDATION_001: 必填字段缺失

**严重级别**: 🟡 Medium
**HTTP状态码**: 422 Unprocessable Entity

**描述**: 请求体中缺少必需的字段

**常见缺失字段**:
- `match_id`: 比赛ID
- `home_team`: 主队名称
- `away_team`: 客队名称
- `match_date`: 比赛日期

**错误示例**:
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_001",
    "message": "必填字段缺失",
    "details": {
      "missing_fields": ["match_id", "home_team"],
      "required_fields": [
        "match_id", "home_team", "away_team",
        "match_date", "league"
      ],
      "suggestion": "请确保所有必填字段都已提供"
    }
  }
}
```

**解决方案**:
```python
def validate_prediction_request(data):
    """验证预测请求数据"""
    required_fields = [
        "match_id", "home_team", "away_team",
        "match_date", "league"
    ]

    missing_fields = [field for field in required_fields
                     if field not in data or not data[field]]

    if missing_fields:
        raise ValueError(f"缺少必填字段: {', '.join(missing_fields)}")

    return True

# 使用示例
try:
    validate_prediction_request(request_data)
    # 继续处理请求
except ValueError as e:
    print(f"验证失败: {e}")
    # 返回错误给用户
```

### VALIDATION_002: 字段格式错误

**严重级别**: 🟡 Medium
**HTTP状态码**: 422 Unprocessable Entity

**描述**: 字段值格式不符合要求

**常见格式错误**:
- `match_date`: 日期时间格式错误
- `email`: 邮箱格式错误
- `phone`: 电话号码格式错误

**解决方案**:
```python
import re
from datetime import datetime

def validate_field_formats(data):
    """验证字段格式"""
    errors = []

    # 验证日期时间格式
    if "match_date" in data:
        try:
            datetime.fromisoformat(data["match_date"].replace("Z", "+00:00"))
        except ValueError:
            errors.append("match_date格式错误，请使用ISO 8601格式")

    # 验证邮箱格式
    if "email" in data:
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, data["email"]):
            errors.append("email格式错误")

    if errors:
        raise ValueError("; ".join(errors))

    return True

# 日期格式示例
valid_dates = [
    "2025-11-15T20:00:00Z",
    "2025-11-15T20:00:00+08:00",
    "2025-11-15T20:00:00.123Z"
]

invalid_dates = [
    "2025-11-15",  # 缺少时间
    "20:00:00",    # 缺少日期
    "2025/11/15"   # 分隔符错误
]
```

### VALIDATION_003: 字段值超出范围

**严重级别**: 🟡 Medium
**HTTP状态码**: 422 Unprocessable Entity

**描述**: 字段值超出了允许的范围

**常见范围限制**:
- `page`: 1-1000
- `page_size`: 1-100
- `confidence_score`: 0-1
- `probability`: 0-1

**错误示例**:
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_003",
    "message": "字段值超出范围",
    "details": {
      "field": "page_size",
      "value": 200,
      "allowed_range": "1-100",
      "suggestion": "请使用1-100之间的值"
    }
  }
}
```

### VALIDATION_004: 数据类型错误

**严重级别**: 🟡 Medium
**HTTP状态码**: 422 Unprocessable Entity

**描述**: 字段数据类型不正确

**常见类型错误**:
- 数字字段提供了字符串
- 布尔字段提供了非布尔值
- 数组字段提供了单个值

**解决方案**:
```python
def validate_data_types(data):
    """验证数据类型"""
    type_requirements = {
        "page": int,
        "page_size": int,
        "confidence_score": (int, float),
        "is_active": bool,
        "tags": list
    }

    errors = []

    for field, expected_type in type_requirements.items():
        if field in data:
            value = data[field]
            if not isinstance(value, expected_type):
                if isinstance(expected_type, tuple):
                    type_names = "或".join(t.__name__ for t in expected_type)
                else:
                    type_names = expected_type.__name__
                errors.append(f"{field}应该是{type_names}类型，实际是{type(value).__name__}")

    if errors:
        raise ValueError("; ".join(errors))

    return True
```

---

## 🏢 业务逻辑错误 (BUSINESS_*)

### BUSINESS_001: 比赛不存在

**严重级别**: 🟡 Medium
**HTTP状态码**: 404 Not Found

**描述**: 请求的比赛ID在系统中不存在

**解决方案**:
```python
def get_match_safely(match_id):
    """安全获取比赛信息"""
    try:
        response = requests.get(f"/matches/{match_id}")

        if response.status_code == 404:
            error_data = response.json()
            if error_data.get("error", {}).get("code") == "BUSINESS_001":
                # 比赛不存在，尝试搜索相似的比赛
                similar_matches = search_similar_matches(match_id)
                if similar_matches:
                    return {
                        "suggestion": f"未找到比赛 {match_id}，是否指的是：{similar_matches[0]['id']}",
                        "similar_matches": similar_matches
                    }

        response.raise_for_status()
        return response.json()

    except requests.exceptions.RequestException as e:
        print(f"获取比赛信息失败: {e}")
        return None

def search_similar_matches(partial_id):
    """搜索相似的比赛ID"""
    # 实现相似比赛搜索逻辑
    pass
```

### BUSINESS_002: 预测服务暂时不可用

**严重级别**: 🟠 High
**HTTP状态码**: 503 Service Unavailable

**描述**: 机器学习模型服务暂时无法使用

**解决方案**:
```python
import time
from datetime import datetime, timedelta

def create_prediction_with_retry(data, max_retries=3, base_delay=5):
    """创建预测请求，支持重试"""
    for attempt in range(max_retries):
        try:
            response = requests.post("/predictions/enhanced", json=data)

            if response.status_code == 503:
                error_data = response.json()
                if error_data.get("error", {}).get("code") == "BUSINESS_002":
                    # 预测服务不可用，等待后重试
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt)  # 指数退避
                        print(f"预测服务暂时不可用，{delay}秒后重试...")
                        time.sleep(delay)
                        continue

            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            if attempt == max_retries - 1:
                # 提供替代方案
                return {
                    "error": "预测服务暂时不可用",
                    "alternative": "您可以稍后重试或使用简化预测功能",
                    "retry_after": datetime.now() + timedelta(minutes=30)
                }

    return None
```

### BUSINESS_003: 重复预测请求

**严重级别**: 🟡 Medium
**HTTP状态码**: 409 Conflict

**描述**: 相同的比赛已经创建了预测请求

**解决方案**:
```python
def create_unique_prediction(match_data):
    """创建唯一的预测请求"""
    # 首先检查是否已存在预测
    existing_prediction = check_existing_prediction(match_data["match_id"])

    if existing_prediction:
        return {
            "success": True,
            "message": "预测已存在",
            "prediction_id": existing_prediction["id"],
            "prediction": existing_prediction["prediction"],
            "created_at": existing_prediction["created_at"]
        }

    # 创建新预测
    return create_new_prediction(match_data)

def check_existing_prediction(match_id):
    """检查已存在的预测"""
    response = requests.get(f"/predictions", params={"match_id": match_id})

    if response.status_code == 200:
        predictions = response.json().get("data", [])
        return predictions[0] if predictions else None

    return None
```

### BUSINESS_004: 超出预测限额

**严重级别**: 🟡 Medium
**HTTP状态码**: 429 Too Many Requests

**描述**: 用户的预测请求次数超出配额限制

**解决方案**:
```python
def check_prediction_quota(user_id):
    """检查用户预测配额"""
    response = requests.get(f"/users/{user_id}/quota")

    if response.status_code == 200:
        quota_data = response.json()
        return {
            "used": quota_data["predictions_used"],
            "limit": quota_data["predictions_limit"],
            "remaining": quota_data["predictions_limit"] - quota_data["predictions_used"],
            "reset_time": quota_data["quota_reset_time"]
        }

    return None

def make_prediction_with_quota_check(match_data):
    """创建预测前检查配额"""
    quota = check_prediction_quota(get_current_user_id())

    if quota and quota["remaining"] <= 0:
        return {
            "error": "预测配额已用完",
            "message": f"您已达到今日预测限额 ({quota['limit']}次)",
            "reset_time": quota["reset_time"],
            "upgrade_suggestion": "升级到高级计划以获得更多预测次数"
        }

    # 配额充足，创建预测
    return create_prediction(match_data)
```

---

## ⚙️ 系统与基础设施错误 (SYSTEM_*)

### SYSTEM_001: 数据库连接失败

**严重级别**: 🔴 Critical
**HTTP状态码**: 503 Service Unavailable

**描述**: 无法连接到数据库

**解决方案**:
```python
import time
from functools import wraps

def with_database_retry(max_retries=3, delay=1):
    """数据库操作重试装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except DatabaseConnectionError as e:
                    if attempt == max_retries - 1:
                        # 最后一次尝试失败，提供缓存数据
                        return get_cached_data_or_error()

                    print(f"数据库连接失败，{delay}秒后重试... (尝试 {attempt + 1}/{max_retries})")
                    time.sleep(delay * (2 ** attempt))  # 指数退避

            return None
        return wrapper
    return decorator

@with_database_retry(max_retries=3)
def get_user_data(user_id):
    """获取用户数据，支持重试"""
    # 数据库操作
    pass

def get_cached_data_or_error():
    """获取缓存数据或返回错误"""
    cached_data = get_from_cache()
    if cached_data:
        return {
            "data": cached_data,
            "warning": "使用缓存数据，实时数据暂时不可用"
        }
    else:
        return {
            "error": "数据库连接失败且无可用缓存数据",
            "retry_after": "5分钟"
        }
```

### SYSTEM_002: 外部服务不可用

**严重级别**: 🟠 High
**HTTP状态码**: 502 Bad Gateway

**描述**: 依赖的外部API或服务不可用

### SYSTEM_003: 缓存服务异常

**严重级别**: 🟠 High
**HTTP状态码**: 503 Service Unavailable

**描述**: Redis缓存服务出现问题

**解决方案**:
```python
class CacheManager:
    def __init__(self):
        self.cache_available = True
        self.fallback_cache = {}

    def get(self, key, fallback_func=None, ttl=300):
        """获取缓存数据，支持降级"""
        try:
            if self.cache_available:
                # 尝试从Redis获取
                value = self.redis_client.get(key)
                if value:
                    return json.loads(value)

            # Redis不可用或无数据，使用fallback
            if fallback_func:
                value = fallback_func()
                self.set(key, value, ttl)  # 尝试设置缓存
                return value

            return None

        except RedisError:
            self.cache_available = False
            if fallback_func:
                return fallback_func()
            return None

    def set(self, key, value, ttl=300):
        """设置缓存，支持降级"""
        try:
            if self.cache_available:
                self.redis_client.setex(key, ttl, json.dumps(value))
            else:
                # 使用内存缓存作为fallback
                self.fallback_cache[key] = {
                    "value": value,
                    "expires": time.time() + ttl
                }
        except RedisError:
            self.cache_available = False
            # 记录错误但不中断服务
            pass

# 使用示例
cache_manager = CacheManager()

def get_match_data(match_id):
    """获取比赛数据，支持缓存降级"""
    def fetch_from_db():
        # 从数据库获取数据
        pass

    return cache_manager.get(
        f"match:{match_id}",
        fallback_func=fetch_from_db,
        ttl=600
    )
```

### SYSTEM_004: 内存不足

**严重级别**: 🔴 Critical
**HTTP状态码**: 503 Service Unavailable

**描述**: 系统内存资源不足

---

## 🌐 第三方服务错误 (EXTERNAL_*)

### EXTERNAL_001: 外部API限流

**严重级别**: 🟡 Medium
**HTTP状态码**: 429 Too Many Requests

**描述**: 外部API服务限流

### EXTERNAL_002: 外部API数据格式变更

**严重级别**: 🟠 High
**HTTP状态码**: 502 Bad Gateway

**描述**: 外部服务返回的数据格式不符合预期

**解决方案**:
```python
def safe_parse_external_data(response_data, expected_schema):
    """安全解析外部数据，支持格式兼容"""
    try:
        # 尝试使用当前格式解析
        return parse_data_with_schema(response_data, expected_schema)
    except DataFormatError as e:
        # 格式错误，尝试兼容性解析
        compatible_data = try_compatible_parsing(response_data)
        if compatible_data:
            log_format_change(response_data, e)
            return compatible_data

        # 无法兼容，使用默认数据
        return get_default_data()
```

---

## 🚦 限流和配额错误 (RATE_LIMIT_*)

### RATE_LIMIT_001: 请求频率超限

**严重级别**: 🟡 Medium
**HTTP状态码**: 429 Too Many Requests

**描述**: 客户端请求频率超出限制

**错误响应包含**:
```json
{
  "success": false,
  "error": {
    "code": "RATE_LIMIT_001",
    "message": "请求频率超出限制",
    "details": {
      "limit": 100,
      "window": 3600,
      "retry_after": 300,
      "reset_time": "2025-11-10T15:00:00Z"
    }
  },
  "headers": {
    "X-RateLimit-Limit": "100",
    "X-RateLimit-Remaining": "0",
    "X-RateLimit-Reset": "1699646400",
    "Retry-After": "300"
  }
}
```

**智能重试解决方案**:
```python
import time
import random
from datetime import datetime

class RateLimitHandler:
    def __init__(self):
        self.retry_after_cache = {}

    def make_request_with_limit_handling(self, url, headers=None, max_retries=3):
        """处理限流的请求方法"""
        for attempt in range(max_retries):
            response = requests.get(url, headers=headers)

            if response.status_code == 429:
                # 解析限流信息
                retry_after = self.extract_retry_after(response)

                if retry_after:
                    # 等待指定时间后重试
                    print(f"限流中，{retry_after}秒后重试...")
                    time.sleep(retry_after)
                    continue
                else:
                    # 使用指数退避 + 随机抖动
                    base_delay = 2 ** attempt
                    jitter = random.uniform(0, 0.1) * base_delay
                    delay = base_delay + jitter

                    print(f"限流中，{delay:.1f}秒后重试...")
                    time.sleep(delay)
                    continue

            # 其他情况直接返回
            return response

        return response  # 最后一次尝试的结果

    def extract_retry_after(self, response):
        """提取重试等待时间"""
        # 1. 优先使用Retry-After头
        if "Retry-After" in response.headers:
            try:
                return int(response.headers["Retry-After"])
            except ValueError:
                pass

        # 2. 使用错误响应中的信息
        try:
            error_data = response.json()
            details = error_data.get("error", {}).get("details", {})
            if "retry_after" in details:
                return int(details["retry_after"])
        except:
            pass

        # 3. 使用X-RateLimit-Reset计算
        if "X-RateLimit-Reset" in response.headers:
            try:
                reset_time = int(response.headers["X-RateLimit-Reset"])
                current_time = int(time.time())
                return max(1, reset_time - current_time)
            except:
                pass

        # 4. 默认等待时间
        return 60

# 使用示例
rate_handler = RateLimitHandler()

def fetch_with_limit_handling(url):
    response = rate_handler.make_request_with_limit_handling(url)

    if response.status_code == 429:
        print("达到重试上限，请稍后再试")
        return None

    return response.json()
```

---

## 🛠️ 错误处理最佳实践

### 1. 统一错误处理框架

```python
class APIErrorHandler:
    def __init__(self):
        self.error_handlers = {
            "AUTH_001": self.handle_auth_error,
            "VALIDATION_001": self.handle_validation_error,
            "BUSINESS_001": self.handle_business_error,
            "SYSTEM_001": self.handle_system_error,
            "RATE_LIMIT_001": self.handle_rate_limit_error
        }

    def handle_error(self, response):
        """统一错误处理入口"""
        if response.status_code >= 400:
            try:
                error_data = response.json()
                error_code = error_data.get("error", {}).get("code")

                if error_code in self.error_handlers:
                    return self.error_handlers[error_code](error_data, response)
                else:
                    return self.handle_unknown_error(error_data, response)

            except json.JSONDecodeError:
                return self.handle_invalid_response(response)

        return {"success": True, "data": response.json()}

    def handle_auth_error(self, error_data, response):
        """处理认证错误"""
        if error_data["error"]["code"] == "AUTH_002":
            # Token过期，自动刷新
            new_token = self.refresh_token()
            if new_token:
                # 重试原请求
                return self.retry_request(response.request, new_token)

        return {"success": False, "error": error_data}

    def handle_rate_limit_error(self, error_data, response):
        """处理限流错误"""
        retry_after = self.extract_retry_after(response)

        return {
            "success": False,
            "error": error_data,
            "retry_after": retry_after,
            "can_retry": True
        }

# 全局错误处理器实例
error_handler = APIErrorHandler()

def api_request(method, url, **kwargs):
    """统一API请求函数"""
    response = requests.request(method, url, **kwargs)
    return error_handler.handle_error(response)
```

### 2. 智能重试机制

```python
import time
import random
from functools import wraps
from typing import Dict, List, Callable, Optional

class RetryConfig:
    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        retryable_status_codes: List[int] = None
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.retryable_status_codes = retryable_status_codes or [429, 500, 502, 503, 504]

def retry_with_config(config: RetryConfig = None):
    """通用重试装饰器"""
    if config is None:
        config = RetryConfig()

    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(config.max_retries + 1):
                try:
                    return func(*args, **kwargs)

                except requests.exceptions.RequestException as e:
                    last_exception = e

                    if attempt == config.max_retries:
                        break

                    # 检查是否应该重试
                    if hasattr(e, 'response') and e.response is not None:
                        status_code = e.response.status_code
                        if status_code not in config.retryable_status_codes:
                            break

                    # 计算延迟时间
                    delay = min(
                        config.base_delay * (config.exponential_base ** attempt),
                        config.max_delay
                    )

                    # 添加随机抖动
                    if config.jitter:
                        delay = delay * (0.5 + random.random() * 0.5)

                    print(f"请求失败，{delay:.1f}秒后重试... (尝试 {attempt + 1}/{config.max_retries})")
                    time.sleep(delay)

            raise last_exception

        return wrapper
    return decorator

# 使用示例
@retry_with_config(RetryConfig(max_retries=5, base_delay=2.0))
def create_prediction_with_retry(data):
    return requests.post("/predictions/enhanced", json=data)
```

### 3. 错误监控和告警

```python
import logging
from datetime import datetime, timedelta
from collections import defaultdict, Counter

class ErrorMonitor:
    def __init__(self):
        self.error_counts = Counter()
        self.error_history = defaultdict(list)
        self.alert_thresholds = {
            "AUTH_001": 10,    # 认证错误10次/分钟
            "SYSTEM_001": 5,   # 系统错误5次/分钟
            "RATE_LIMIT_001": 20  # 限流错误20次/分钟
        }

    def record_error(self, error_code: str, context: Dict = None):
        """记录错误"""
        timestamp = datetime.now()

        # 更新计数
        self.error_counts[error_code] += 1
        self.error_history[error_code].append(timestamp)

        # 清理过期的错误记录（1小时前）
        cutoff_time = timestamp - timedelta(hours=1)
        self.error_history[error_code] = [
            ts for ts in self.error_history[error_code] if ts > cutoff_time
        ]

        # 检查是否需要告警
        self.check_alerts(error_code)

    def check_alerts(self, error_code: str):
        """检查告警条件"""
        if error_code in self.alert_thresholds:
            recent_count = len(self.error_history[error_code])
            threshold = self.alert_thresholds[error_code]

            if recent_count >= threshold:
                self.send_alert(error_code, recent_count, threshold)

    def send_alert(self, error_code: str, count: int, threshold: int):
        """发送告警"""
        alert_message = (
            f"🚨 错误告警\n"
            f"错误代码: {error_code}\n"
            f"最近1小时发生次数: {count}\n"
            f"告警阈值: {threshold}\n"
            f"时间: {datetime.now().isoformat()}"
        )

        # 发送到日志
        logging.error(alert_message)

        # 可以集成其他告警渠道
        # self.send_to_slack(alert_message)
        # self.send_to_email(alert_message)

# 全局错误监控器
error_monitor = ErrorMonitor()

def monitored_api_request(method: str, url: str, **kwargs):
    """带监控的API请求"""
    try:
        response = requests.request(method, url, **kwargs)

        if response.status_code >= 400:
            try:
                error_data = response.json()
                error_code = error_data.get("error", {}).get("code")
                if error_code:
                    error_monitor.record_error(error_code, {
                        "url": url,
                        "method": method,
                        "status_code": response.status_code
                    })
            except:
                pass

        return response

    except Exception as e:
        error_monitor.record_error("UNKNOWN_ERROR", {
            "url": url,
            "method": method,
            "exception": str(e)
        })
        raise
```

### 4. 用户友好的错误提示

```python
class UserFriendlyErrors:
    """用户友好的错误消息映射"""

    ERROR_MESSAGES = {
        "AUTH_001": {
            "title": "登录已过期",
            "message": "您的登录状态已过期，请重新登录",
            "action": "重新登录",
            "action_url": "/login"
        },
        "VALIDATION_001": {
            "title": "信息不完整",
            "message": "请填写所有必填信息后再试",
            "action": "检查填写内容",
            "action_url": None
        },
        "BUSINESS_001": {
            "title": "比赛不存在",
            "message": "找不到您请求的比赛信息",
            "action": "浏览其他比赛",
            "action_url": "/matches"
        },
        "RATE_LIMIT_001": {
            "title": "请求过于频繁",
            "message": "请稍等片刻后再试",
            "action": "稍后重试",
            "action_url": None
        },
        "SYSTEM_001": {
            "title": "系统维护中",
            "message": "系统正在维护，请稍后再试",
            "action": "查看系统状态",
            "action_url": "/status"
        }
    }

    @classmethod
    def get_friendly_message(cls, error_code: str, default_message: str = None):
        """获取用户友好的错误消息"""
        if error_code in cls.ERROR_MESSAGES:
            return cls.ERROR_MESSAGES[error_code]

        return {
            "title": "操作失败",
            "message": default_message or "发生了未知错误，请稍后再试",
            "action": "重试",
            "action_url": None
        }

def format_error_for_user(error_data: Dict):
    """为用户格式化错误信息"""
    error_code = error_data.get("error", {}).get("code", "UNKNOWN")
    technical_message = error_data.get("error", {}).get("message", "")

    friendly_info = UserFriendlyErrors.get_friendly_message(
        error_code,
        technical_message
    )

    return {
        "success": False,
        "user_error": friendly_info,
        "technical_error": error_data  # 保留技术细节用于调试
    }
```

---

## 🔧 开发者工具

### 1. 错误代码查询工具

```python
class ErrorCodeLookup:
    """错误代码查询工具"""

    ERROR_DATABASE = {
        "AUTH_001": {
            "category": "认证",
            "severity": "High",
            "http_status": 401,
            "description": "认证Token缺失或格式错误",
            "causes": [
                "请求头中缺少Authorization字段",
                "Token格式不符合Bearer规范",
                "Token中包含非法字符"
            ],
            "solutions": [
                "在请求头中添加Authorization: Bearer <token>",
                "检查Token格式是否正确",
                "重新获取有效的Token"
            ],
            "code_examples": {
                "python": 'headers = {"Authorization": "Bearer your_token"}',
                "javascript": 'headers: {"Authorization": "Bearer your_token"}',
                "curl": '-H "Authorization: Bearer your_token"'
            }
        }
        # ... 更多错误代码定义
    }

    @classmethod
    def lookup_error(cls, error_code: str):
        """查询错误代码详情"""
        return cls.ERROR_DATABASE.get(error_code, {
            "category": "未知",
            "severity": "Unknown",
            "http_status": 500,
            "description": f"未知错误代码: {error_code}",
            "causes": [],
            "solutions": ["联系技术支持"],
            "code_examples": {}
        })

    @classmethod
    def list_errors_by_category(cls, category: str):
        """按分类列出错误"""
        return {
            code: info for code, info in cls.ERROR_DATABASE.items()
            if info["category"] == category
        }

    @classmethod
    def list_errors_by_severity(cls, severity: str):
        """按严重级别列出错误"""
        return {
            code: info for code, info in cls.ERROR_DATABASE.items()
            if info["severity"] == severity
        }

# 命令行工具
def main():
    import sys

    if len(sys.argv) < 2:
        print("用法: python error_lookup.py <error_code|category|severity>")
        print("示例:")
        print("  python error_lookup.py AUTH_001")
        print("  python error_lookup.py category 认证")
        print("  python error_lookup.py severity High")
        return

    query_type = sys.argv[1]

    if query_type in ["category", "severity"]:
        if len(sys.argv) < 3:
            print(f"请指定{query_type}")
            return

        value = sys.argv[2]
        if query_type == "category":
            errors = ErrorCodeLookup.list_errors_by_category(value)
        else:
            errors = ErrorCodeLookup.list_errors_by_severity(value)

        for code, info in errors.items():
            print(f"{code}: {info['description']}")

    else:
        error_code = query_type.upper()
        error_info = ErrorCodeLookup.lookup_error(error_code)

        print(f"错误代码: {error_code}")
        print(f"分类: {error_info['category']}")
        print(f"严重级别: {error_info['severity']}")
        print(f"HTTP状态码: {error_info['http_status']}")
        print(f"描述: {error_info['description']}")

        if error_info['causes']:
            print("\n可能原因:")
            for cause in error_info['causes']:
                print(f"  • {cause}")

        if error_info['solutions']:
            print("\n解决方案:")
            for solution in error_info['solutions']:
                print(f"  • {solution}")

if __name__ == "__main__":
    main()
```

### 2. API错误模拟工具

```python
class ErrorSimulator:
    """API错误模拟工具，用于测试错误处理"""

    def __init__(self, base_url: str):
        self.base_url = base_url

    def simulate_error(self, error_code: str, endpoint: str = "/test"):
        """模拟特定错误"""
        error_responses = {
            "AUTH_001": (401, {"error": {"code": "AUTH_001", "message": "Token缺失"}}),
            "VALIDATION_001": (422, {"error": {"code": "VALIDATION_001", "message": "字段缺失"}}),
            "BUSINESS_001": (404, {"error": {"code": "BUSINESS_001", "message": "比赛不存在"}}),
            "RATE_LIMIT_001": (429, {"error": {"code": "RATE_LIMIT_001", "message": "请求过频"}}),
            "SYSTEM_001": (503, {"error": {"code": "SYSTEM_001", "message": "系统错误"}})
        }

        if error_code not in error_responses:
            raise ValueError(f"未知错误代码: {error_code}")

        status_code, response_data = error_responses[error_code]

        # 创建模拟响应
        mock_response = MockResponse(status_code, response_data)
        return mock_response

    def test_error_handling(self, error_code: str, handler_func):
        """测试错误处理函数"""
        mock_response = self.simulate_error(error_code)

        try:
            result = handler_func(mock_response)
            return {
                "error_code": error_code,
                "handled": True,
                "result": result
            }
        except Exception as e:
            return {
                "error_code": error_code,
                "handled": False,
                "exception": str(e)
            }

class MockResponse:
    """模拟HTTP响应"""
    def __init__(self, status_code: int, json_data: Dict):
        self.status_code = status_code
        self._json_data = json_data
        self.headers = {}

    def json(self):
        return self._json_data

# 使用示例
simulator = ErrorSimulator("https://api.football-prediction.com")

def test_all_error_handlers():
    """测试所有错误处理器"""
    results = {}

    error_codes = ["AUTH_001", "VALIDATION_001", "BUSINESS_001", "RATE_LIMIT_001", "SYSTEM_001"]

    for error_code in error_codes:
        result = simulator.test_error_handling(error_code, error_handler.handle_error)
        results[error_code] = result

    return results
```

---

## 🛠️ 开发者工具

### 错误代码查询工具

```python
class ErrorCodeLookup:
    """错误代码查询工具"""

    ERROR_DATABASE = {
        "AUTH_001": {
            "category": "认证",
            "severity": "High",
            "http_status": 401,
            "description": "认证Token缺失或格式错误",
            "causes": [
                "请求头中缺少Authorization字段",
                "Token格式不符合Bearer规范",
                "Token中包含非法字符"
            ],
            "solutions": [
                "在请求头中添加Authorization: Bearer <token>",
                "检查Token格式是否正确",
                "重新获取有效的Token"
            ]
        }
        # ... 更多错误代码定义
    }

    @classmethod
    def lookup_error(cls, error_code: str):
        """查询错误代码详情"""
        return cls.ERROR_DATABASE.get(error_code, {
            "category": "未知",
            "severity": "Unknown",
            "http_status": 500,
            "description": f"未知错误代码: {error_code}",
            "causes": [],
            "solutions": ["联系技术支持"]
        })
```

### API错误模拟工具

```python
class ErrorSimulator:
    """API错误模拟工具，用于测试错误处理"""

    def simulate_error(self, error_code: str, endpoint: str = "/test"):
        """模拟特定错误"""
        error_responses = {
            "AUTH_001": (401, {"error": {"code": "AUTH_001", "message": "Token缺失"}}),
            "VALIDATION_001": (422, {"error": {"code": "VALIDATION_001", "message": "字段缺失"}}),
            "BUSINESS_001": (404, {"error": {"code": "BUSINESS_001", "message": "比赛不存在"}}),
            "RATE_LIMIT_001": (429, {"error": {"code": "RATE_LIMIT_001", "message": "请求过频"}}),
            "SYSTEM_001": (503, {"error": {"code": "SYSTEM_001", "message": "系统错误"}})
        }

        if error_code not in error_responses:
            raise ValueError(f"未知错误代码: {error_code}")

        status_code, response_data = error_responses[error_code]
        return MockResponse(status_code, response_data)
```

---

## 📞 支持与帮助

### 获取帮助
- **API文档**: https://docs.football-prediction.com
- **错误代码查询**: 使用上述开发者工具
- **技术支持邮箱**: support@football-prediction.com
- **系统状态页面**: https://status.football-prediction.com

### 报告问题
如果遇到未在本文档中说明的错误，请提供以下信息：
1. 错误代码和HTTP状态码
2. 完整的错误响应体
3. 请求的URL和方法
4. 请求头和请求体（敏感信息可脱敏）
5. 发生时间和复现步骤

### 常见问题解答
- Q: 如何获取API密钥？
  A: 在用户控制台的"API设置"页面生成API密钥。

- Q: 请求频率限制是多少？
  A: 免费用户100请求/小时，付费用户1000请求/小时。

- Q: 如何获取实时比赛更新？
  A: 使用WebSocket连接 `wss://api.football-prediction.com/v1/ws`

- Q: 预测准确率如何？
  A: 平均预测准确率约为75-85%，具体取决于联赛和数据质量。

### 联系方式
- **技术支持**: support@football-prediction.com
- **问题反馈**: https://github.com/football-prediction/issues
- **功能请求**: https://github.com/football-prediction/discussions

---

*文档版本: v1.0.0 | 最后更新: 2025-11-10 | 维护者: Claude Code*
