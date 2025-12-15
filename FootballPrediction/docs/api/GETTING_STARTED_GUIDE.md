# 🚀 足球预测系统API快速入门指南

## 📋 目录
1. [环境准备](#环境准备)
2. [基础认证](#基础认证)
3. [第一个API调用](#第一个api调用)
4. [常用场景示例](#常用场景示例)
5. [错误处理](#错误处理)
6. [最佳实践](#最佳实践)

---

## 🔧 环境准备

### 1. 获取API密钥
```bash
# 注册开发者账户
curl -X POST "http://localhost:8000/api/users/register" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "your_username",
    "email": "your_email@example.com",
    "password": "SecurePassword123!",
    "full_name": "Your Name"
  }'

# 登录获取token
curl -X POST "http://localhost:8000/api/users/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "your_username",
    "password": "SecurePassword123!"
  }'
```

### 2. 安装开发工具
```bash
# Python (推荐)
pip install requests football-prediction-sdk

# Node.js
npm install axios football-prediction-js-sdk

# 其他工具
# Postman: https://www.postman.com/downloads/
# Insomnia: https://insomnia.rest/download/
```

---

## 🔐 基础认证

### JWT Token认证 (推荐)
```python
import requests

# 获取token
auth_response = requests.post(
    "http://localhost:8000/auth/token",
    data={
        "username": "your_username",
        "password": "your_password"
    }
)

token = auth_response.json()["access_token"]

# 设置认证头
headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}
```

### API Key认证
```python
headers = {
    "X-API-Key": "your_api_key",
    "Content-Type": "application/json"
}
```

---

## 🎯 第一个API调用

### 创建你的第一个预测
```python
import requests
import json

# API端点
url = "http://localhost:8000/api/predictions"

# 预测数据
prediction_data = {
    "match_id": 12345,
    "home_team": "Manchester United",
    "away_team": "Liverpool",
    "home_score_prediction": 2,
    "away_score_prediction": 1,
    "confidence_score": 0.85,
    "prediction_type": "exact_score"
}

# 发送请求
response = requests.post(url, json=prediction_data, headers=headers)

if response.status_code == 201:
    prediction = response.json()
    print(f"✅ 预测创建成功! ID: {prediction['id']}")
    print(f"🎯 比分预测: {prediction['home_team']} {prediction['home_score_prediction']} - {prediction['away_score_prediction']} {prediction['away_team']}")
    print(f"📊 置信度: {prediction['confidence_score']:.1%}")
else:
    print(f"❌ 创建失败: {response.status_code}")
    print(f"错误信息: {response.text}")
```

**输出示例**:
```
✅ 预测创建成功! ID: 789
🎯 比分预测: Manchester United 2 - 1 Liverpool
📊 置信度: 85.0%
```

---

## 📚 常用场景示例

### 场景1: 获取预测历史
```python
# 获取最近10个预测
response = requests.get(
    "http://localhost:8000/api/predictions",
    headers=headers,
    params={"limit": 10, "status": "completed"}
)

predictions = response.json()["items"]
for pred in predictions:
    print(f"📅 {pred['created_at'][:10]}: {pred['home_team']} vs {pred['away_team']}")
    print(f"   预测: {pred['home_score_prediction']}-{pred['away_score_prediction']}")
    print(f"   实际: {pred.get('actual_home_score', '?')}-{pred.get('actual_away_score', '?')}")
    print()
```

### 场景2: 系统健康检查
```python
import requests

# 基础健康检查
health_response = requests.get("http://localhost:8000/health/")

if health_response.status_code == 200:
    health_data = health_response.json()
    print(f"🟢 系统状态: {health_data['status']}")
    print(f"⏰ 运行时间: {health_data['uptime']}秒")
else:
    print("🔴 系统不可用")

# 详细健康检查
detailed_response = requests.get("http://localhost:8000/health/detailed")
if detailed_response.status_code == 200:
    details = detailed_response.json()
    print("\n📊 组件状态:")
    for component, status in details["components"].items():
        status_icon = "🟢" if status["status"] == "healthy" else "🔴"
        print(f"   {status_icon} {component}: {status['status']}")
```

### 场景3: 实时数据获取
```python
# 获取实时比赛数据
match_id = 12345
response = requests.get(
    f"http://localhost:8000/api/data/matches/{match_id}/live",
    headers=headers
)

if response.status_code == 200:
    match_data = response.json()
    print(f"⚽ {match_data['home_team']} {match_data['home_score']} - {match_data['away_score']} {match_data['away_team']}")
    print(f"⏱️ 比赛时间: {match_data['match_time']}")
    print(f"🏟️ 场地: {match_data['stadium']}")
```

### 场景4: 批量预测分析
```python
# 批量分析多个比赛
match_ids = [12345, 12346, 12347, 12348]
analysis_request = {
    "match_ids": match_ids,
    "analysis_type": "team_form",
    "include_confidence": True
}

response = requests.post(
    "http://localhost:8000/api/predictions/batch-analyze",
    json=analysis_request,
    headers=headers
)

if response.status_code == 200:
    analysis = response.json()
    print("📊 批量分析结果:")
    for match_id, result in analysis["results"].items():
        print(f"   比赛 {match_id}:")
        print(f"   - 主队胜率: {result['probabilities']['home_win']:.1%}")
        print(f"   - 平局概率: {result['probabilities']['draw']:.1%}")
        print(f"   - 客队胜率: {result['probabilities']['away_win']:.1%}")
```

### 场景5: 用户配置管理
```python
# 更新用户偏好
preferences = {
    "language": "zh-CN",
    "timezone": "Asia/Shanghai",
    "notification_preferences": {
        "email": True,
        "push": True,
        "sms": False
    },
    "default_confidence_threshold": 0.70
}

response = requests.put(
    "http://localhost:8000/api/users/preferences",
    json=preferences,
    headers=headers
)

if response.status_code == 200:
    print("✅ 用户偏好更新成功")
    print(f"🌐 语言: {preferences['language']}")
    print(f"🕐 时区: {preferences['timezone']}")
```

---

## ⚠️ 错误处理

### 基础错误处理模式
```python
def safe_api_call(method, url, **kwargs):
    """安全的API调用封装"""
    try:
        response = requests.request(method, url, headers=headers, **kwargs)

        if response.status_code == 401:
            raise Exception("认证失败，请检查token是否有效")
        elif response.status_code == 403:
            raise Exception("权限不足，无法访问此资源")
        elif response.status_code == 404:
            raise Exception("请求的资源不存在")
        elif response.status_code == 429:
            raise Exception("请求频率过高，请稍后重试")
        elif response.status_code >= 500:
            raise Exception("服务器内部错误，请稍后重试")

        return response.json()

    except requests.exceptions.ConnectionError:
        raise Exception("无法连接到API服务器")
    except requests.exceptions.Timeout:
        raise Exception("请求超时，请检查网络连接")
    except requests.exceptions.JSONDecodeError:
        raise Exception("响应格式错误")

# 使用示例
try:
    prediction = safe_api_call(
        "POST",
        "http://localhost:8000/api/predictions",
        json=prediction_data
    )
    print("✅ API调用成功")
except Exception as e:
    print(f"❌ API调用失败: {e}")
```

### 高级错误处理
```python
from enum import Enum

class APIError(Enum):
    AUTHENTICATION_FAILED = "认证失败"
    PERMISSION_DENIED = "权限不足"
    RESOURCE_NOT_FOUND = "资源不存在"
    RATE_LIMIT_EXCEEDED = "请求频率超限"
    SERVER_ERROR = "服务器错误"

class FootballPredictionAPI:
    def __init__(self, base_url, api_key=None):
        self.base_url = base_url
        self.api_key = api_key
        self.session = requests.Session()

        if api_key:
            self.session.headers.update({"X-API-Key": api_key})

    def handle_response(self, response):
        """处理API响应"""
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 201:
            return response.json()
        elif response.status_code == 401:
            raise Exception(APIError.AUTHENTICATION_FAILED.value)
        elif response.status_code == 403:
            raise Exception(APIError.PERMISSION_DENIED.value)
        elif response.status_code == 404:
            raise Exception(APIError.RESOURCE_NOT_FOUND.value)
        elif response.status_code == 429:
            raise Exception(APIError.RATE_LIMIT_EXCEEDED.value)
        elif response.status_code >= 500:
            raise Exception(APIError.SERVER_ERROR.value)
        else:
            raise Exception(f"未知错误: {response.status_code}")

# 使用高级API客户端
api = FootballPredictionAPI("http://localhost:8000", api_key="your_key")

try:
    predictions = api.handle_response(
        api.session.get(f"{api.base_url}/api/predictions")
    )
    print(f"✅ 获取到 {len(predictions)} 个预测")
except Exception as e:
    print(f"❌ 错误: {e}")
```

---

## 💡 最佳实践

### 1. 缓存API响应
```python
import time
from functools import lru_cache

class CachedAPI:
    def __init__(self, api_client):
        self.api = api_client
        self.cache = {}
        self.cache_timeout = 300  # 5分钟缓存

    @lru_cache(maxsize=100)
    def get_prediction(self, prediction_id, use_cache=True):
        cache_key = f"prediction_{prediction_id}"

        if use_cache and cache_key in self.cache:
            cached_item = self.cache[cache_key]
            if time.time() - cached_item['timestamp'] < self.cache_timeout:
                return cached_item['data']

        # 从API获取
        prediction = self.api.get_prediction(prediction_id)

        # 缓存结果
        self.cache[cache_key] = {
            'data': prediction,
            'timestamp': time.time()
        }

        return prediction

# 使用缓存API
cached_api = CachedAPI(api_client)
prediction = cached_api.get_prediction(12345)  # 首次调用，从API获取
prediction = cached_api.get_prediction(12345)  # 从缓存获取
```

### 2. 批量请求优化
```python
import asyncio
import aiohttp
from concurrent.futures import ThreadPoolExecutor

class BatchAPI:
    def __init__(self, api_client):
        self.api = api_client

    def create_predictions_batch(self, predictions_data):
        """批量创建预测"""
        MAX_CONCURRENT = 10

        with ThreadPoolExecutor(max_workers=MAX_CONCURRENT) as executor:
            futures = []
            for pred_data in predictions_data:
                future = executor.submit(
                    self.api.create_prediction,
                    pred_data
                )
                futures.append(future)

            results = []
            for future in futures:
                try:
                    result = future.result(timeout=30)
                    results.append(result)
                except Exception as e:
                    print(f"批量创建中出错: {e}")
                    results.append(None)

        return [r for r in results if r is not None]

# 使用批量API
batch_api = BatchAPI(api_client)
predictions_data = [
    {"match_id": i, "home_team": f"Team A{i}", "away_team": f"Team B{i}"}
    for i in range(1, 21)
]

results = batch_api.create_predictions_batch(predictions_data)
print(f"✅ 成功创建 {len(results)} 个预测")
```

### 3. 智能重试机制
```python
import time
import random
from requests.exceptions import RequestException

class RetryAPI:
    def __init__(self, api_client):
        self.api = api_client

    def call_with_retry(self, method, url, max_retries=3, backoff_factor=2, **kwargs):
        """带重试的API调用"""
        last_exception = None

        for attempt in range(max_retries + 1):
            try:
                return self.api.session.request(method, url, **kwargs)

            except RequestException as e:
                last_exception = e

                if attempt < max_retries:
                    # 指数退避 + 随机抖动
                    wait_time = (backoff_factor ** attempt) + random.uniform(0, 1)
                    print(f"第 {attempt + 1} 次尝试失败，等待 {wait_time:.1f} 秒后重试")
                    time.sleep(wait_time)
                else:
                    break

        raise last_exception

# 使用重试API
retry_api = RetryAPI(api_client)
response = retry_api.call_with_retry("GET", "http://localhost:8000/api/predictions")
```

### 4. 配置管理
```python
import os
from dataclasses import dataclass

@dataclass
class APIConfig:
    base_url: str
    api_key: str = None
    timeout: int = 30
    max_retries: int = 3
    cache_timeout: int = 300

    @classmethod
    def from_env(cls):
        return cls(
            base_url=os.getenv("API_BASE_URL", "http://localhost:8000"),
            api_key=os.getenv("API_KEY"),
            timeout=int(os.getenv("API_TIMEOUT", "30")),
            max_retries=int(os.getenv("API_MAX_RETRIES", "3")),
            cache_timeout=int(os.getenv("API_CACHE_TIMEOUT", "300"))
        )

# 环境变量配置
# export API_BASE_URL="http://localhost:8000"
# export API_KEY="your_api_key"
# export API_TIMEOUT="30"

config = APIConfig.from_env()
api = FootballPredictionAPI(config.base_url, config.api_key)
```

---

## 🔧 开发工具推荐

### 1. Postman集合
```json
{
  "info": {
    "name": "Football Prediction API",
    "description": "足球预测系统API集合"
  },
  "variable": [
    {
      "key": "base_url",
      "value": "http://localhost:8000",
      "type": "string"
    },
    {
      "key": "token",
      "value": "",
      "type": "string"
    }
  ]
}
```

### 2. Python环境配置
```bash
# requirements.txt
requests>=2.31.0
python-dotenv>=1.0.0
pydantic>=2.5.0
football-prediction-sdk>=1.0.0

# .env
API_BASE_URL=http://localhost:8000
API_KEY=your_api_key_here
```

### 3. 项目结构
```
your-project/
├── .env
├── requirements.txt
├── config.py
├── api_client.py
├── predictions.py
├── main.py
└── tests/
    ├── test_predictions.py
    └── test_health.py
```

---

## 📞 技术支持

- **文档**: https://github.com/xupeng211/FootballPrediction/docs
- **API参考**: [COMPLETE_API_REFERENCE.md](COMPLETE_API_REFERENCE.md)
- **错误代码**: [errors.md](errors.md)
- **社区支持**: https://github.com/xupeng211/FootballPrediction/discussions
- **报告问题**: https://github.com/xupeng211/FootballPrediction/issues

---

**文档版本**: v1.0.0
**最后更新**: 2025-11-10
**支持邮箱**: api-support@footballprediction.com
