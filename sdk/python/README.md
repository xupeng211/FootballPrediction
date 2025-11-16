# Football Prediction Python SDK

[![PyPI version](https://badge.fury.io/py/football-prediction-sdk.svg)](https://badge.fury.io/py/football-prediction-sdk)
[![Python versions](https://img.shields.io/pypi/pyversions/football-prediction-sdk.svg)](https://pypi.org/project/football-prediction-sdk/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

足球比赛结果预测系统 - 官方Python SDK，提供完整的API访问功能。

## 🚀 快速开始

### 安装

```bash
pip install football-prediction-sdk
```

### 基础使用

```python
from football_prediction_sdk import FootballPredictionClient
from datetime import datetime

# 初始化客户端
client = FootballPredictionClient(
    api_key="your_api_key",
    base_url="https://api.football-prediction.com/v1"
)

# 创建预测
request = PredictionRequest(
    match_id="match_123",
    home_team="Manchester United",
    away_team="Liverpool",
    match_date=datetime(2025, 11, 15, 20, 0),
    league="Premier League"
)

try:
    response = client.predictions.create(request)
    prediction = response.prediction

    print(f"预测ID: {prediction.prediction_id}")
    print(f"主胜概率: {prediction.probabilities['home_win']:.2%}")
    print(f"平局概率: {prediction.probabilities['draw']:.2%}")
    print(f"客胜概率: {prediction.probabilities['away_win']:.2%}")
    print(f"推荐投注: {prediction.recommended_bet}")
    print(f"置信度: {prediction.confidence_score:.2%}")

except Exception as e:
    print(f"预测失败: {e}")
```

## 📚 功能特性

- ✅ **完整的API覆盖** - 支持所有API端点
- ✅ **自动认证管理** - JWT Token自动刷新
- ✅ **智能重试机制** - 自动处理限流和临时错误
- ✅ **类型安全** - 完整的类型提示
- ✅ **异常处理** - 详细的错误信息和解决方案
- ✅ **数据验证** - 请求数据自动验证
- ✅ **批量操作** - 支持批量预测创建
- ✅ **异步支持** - 高性能异步请求

## 🔧 配置选项

### 基础配置

```python
client = FootballPredictionClient(
    api_key="your_api_key",
    base_url="https://api.football-prediction.com/v1",
    timeout=30,                    # 请求超时时间
    auto_retry=True,               # 自动重试失败请求
    user_agent="my-app/1.0"        # 自定义User-Agent
)
```

### 高级配置

```python
from football_prediction_sdk.auth import AuthManager

# 使用自定义认证管理器
auth_manager = AuthManager(
    api_key="your_api_key",
    base_url="https://api.football-prediction.com/v1",
    timeout=60,
    auto_refresh=True
)

client = FootballPredictionClient(
    api_key="your_api_key",
    auth_manager=auth_manager
)
```

## 📖 API使用示例

### 预测服务

```python
# 创建单个预测
request = PredictionRequest(
    match_id="match_123",
    home_team="Manchester United",
    away_team="Liverpool",
    match_date=datetime(2025, 11, 15, 20, 0),
    league="Premier League",
    features={
        "team_form": {
            "home_last_5": [3, 1, 0, 3, 1],
            "away_last_5": [1, 0, 3, 1, 0]
        }
    },
    include_explanation=True
)

response = client.predictions.create(request)
prediction = response.prediction

# 获取预测结果
prediction = client.predictions.get("pred_12345")
if prediction:
    print(f"预测状态: {prediction.status}")
    print(f"实际结果: {prediction.actual_result}")
    print(f"预测正确: {prediction.is_correct}")

# 获取预测历史
predictions = client.predictions.list(
    status="completed",
    page=1,
    page_size=20,
    date_from=datetime(2025, 11, 1),
    date_to=datetime(2025, 11, 30)
)

# 批量创建预测
requests = [
    PredictionRequest(
        match_id="match_123",
        home_team="Team A",
        away_team="Team B",
        match_date=datetime(2025, 11, 15, 20, 0),
        league="Premier League"
    ),
    PredictionRequest(
        match_id="match_124",
        home_team="Team C",
        away_team="Team D",
        match_date=datetime(2025, 11, 16, 15, 0),
        league="Premier League"
    )
]

batch_result = client.predictions.batch_create(requests)
print(f"批量ID: {batch_result['batch_id']}")
```

### 比赛数据

```python
# 获取比赛详情
match = client.matches.get("match_123")
if match:
    print(f"比赛: {match.home_team.name} vs {match.away_team.name}")
    print(f"联赛: {match.league}")
    print(f"状态: {match.status}")
    print(f"场地: {match.venue}")

# 获取比赛列表
response = client.matches.list(
    league="Premier League",
    status="scheduled",
    page=1,
    page_size=10
)

for match in response.matches:
    print(f"{match.home_team.name} vs {match.away_team.name} - {match.match_date}")

# 获取联赛列表
leagues = client.matches.get_leagues()
for league in leagues:
    print(f"{league['name']} - {league['country']}")
```

### 用户管理

```python
# 获取用户配置
response = client.users.get_profile()
user = response.user

print(f"用户名: {user.username}")
print(f"订阅计划: {user.subscription.plan}")
print(f"收藏球队: {user.preferences.favorite_teams}")

# 更新用户偏好
success = client.users.update_profile({
    "favorite_teams": ["Manchester United", "Liverpool"],
    "notification_settings": {
        "predictions": True,
        "match_results": False
    },
    "language": "zh-CN"
})

# 获取用户统计
stats = client.users.get_statistics()
print(f"总预测数: {stats.total_predictions}")
print(f"成功预测: {stats.successful_predictions}")
print(f"成功率: {stats.success_percentage}")
print(f"当前连胜: {stats.current_streak}")
```

## ⚠️ 错误处理

### 基础错误处理

```python
from football_prediction_sdk.exceptions import (
    AuthenticationError,
    ValidationError,
    BusinessError,
    RateLimitError,
    SystemError
)

try:
    response = client.predictions.create(request)

except AuthenticationError as e:
    print(f"认证失败: {e}")
    # 重新认证

except ValidationError as e:
    print(f"数据验证失败: {e}")
    # 检查请求数据

except BusinessError as e:
    print(f"业务逻辑错误: {e}")
    # 处理业务问题

except RateLimitError as e:
    print(f"请求频率超限: {e}")
    retry_after = e.get_retry_after_seconds()
    if retry_after:
        print(f"{retry_after}秒后重试")

except SystemError as e:
    print(f"系统错误: {e}")
    # 联系技术支持
```

### 高级错误处理

```python
from football_prediction_sdk.utils import retry_with_backoff

@retry_with_backoff(max_retries=5, base_delay=2.0)
def create_prediction_with_retry(request):
    return client.predictions.create(request)

try:
    response = create_prediction_with_retry(request)
except Exception as e:
    print(f"重试后仍然失败: {e}")
```

## 🔍 认证管理

### API密钥认证

```python
# 使用API密钥自动认证
client = FootballPredictionClient(api_key="your_api_key")

# 检查认证状态
if client.is_authenticated:
    print("认证成功")
else:
    print("认证失败")
```

### 用户名密码认证

```python
# 使用用户名密码认证
client.authenticate(
    username="your_username",
    password="your_password"
)
```

### Token管理

```python
# 手动刷新Token
client.auth.refresh_token_if_needed()

# 登出
client.auth.logout()

# 获取用户信息
user_info = client.auth.get_user_info()
```

## 🛠️ 高级功能

### 自定义重试策略

```python
from football_prediction_sdk.utils import retry_with_backoff

@retry_with_backoff(
    max_retries=5,
    base_delay=2.0,
    max_delay=60.0,
    exponential_base=2.0,
    jitter=True
)
def custom_api_call():
    return client.predictions.create(request)
```

### 性能监控

```python
from football_prediction_sdk.utils import Timer

with Timer("prediction_request"):
    response = client.predictions.create(request)

print(f"请求耗时: {timer.elapsed_ms:.0f}ms")
```

### 请求追踪

```python
from football_prediction_sdk.utils import generate_request_id

request_id = generate_request_id()
headers = {"X-Request-ID": request_id}

response = client._make_request(
    "POST",
    "/predictions/enhanced",
    json=request.to_dict(),
    headers=headers
)
```

## 📊 性能优化

### 异步请求

```python
import asyncio
import aiohttp
from football_prediction_sdk import AsyncFootballPredictionClient

async def async_predictions():
    client = AsyncFootballPredictionClient(api_key="your_api_key")

    tasks = []
    for i in range(10):
        request = PredictionRequest(...)
        task = client.predictions.create_async(request)
        tasks.append(task)

    results = await asyncio.gather(*tasks)
    return results

results = asyncio.run(async_predictions())
```

### 批量处理

```python
# 批量创建预测（推荐）
requests = [PredictionRequest(...) for _ in range(50)]
batch_result = client.predictions.batch_create(requests)

# 串行处理（不推荐）
predictions = []
for request in requests:
    response = client.predictions.create(request)
    predictions.append(response.prediction)
```

## 🧪 测试

### 单元测试

```python
import pytest
from football_prediction_sdk import FootballPredictionClient
from unittest.mock import Mock, patch

@pytest.fixture
def client():
    return FootballPredictionClient(api_key="test_key")

@patch('football_prediction_sdk.client.requests.Session.post')
def test_create_prediction(mock_post, client):
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "success": True,
        "data": {
            "prediction_id": "test_123",
            "prediction": {
                "probabilities": {"home_win": 0.6, "draw": 0.25, "away_win": 0.15},
                "recommended_bet": "home_win",
                "confidence_score": 0.8
            }
        }
    }
    mock_post.return_value = mock_response

    request = PredictionRequest(
        match_id="test_match",
        home_team="Team A",
        away_team="Team B",
        match_date=datetime(2025, 11, 15, 20, 0),
        league="Test League"
    )

    response = client.predictions.create(request)
    assert response.success
    assert response.prediction.prediction_id == "test_123"
```

### 集成测试

```python
import pytest
from football_prediction_sdk import FootballPredictionClient

@pytest.mark.integration
def test_real_api_call():
    client = FootballPredictionClient(
        api_key=os.getenv("API_KEY"),
        base_url="https://api.football-prediction.com/v1"
    )

    # 健康检查
    health = client.health_check()
    assert health["status"] == "healthy"

    # API信息
    info = client.get_api_info()
    assert "api_version" in info
```

## 📋 系统要求

- Python 3.8+
- requests >= 2.25.0
- python-dateutil >= 2.8.0

## 📄 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件

## 🔗 相关链接

- [API文档](https://docs.football-prediction.com/)
- [错误代码参考](https://docs.football-prediction.com/errors)
- [GitHub仓库](https://github.com/football-prediction/python-sdk)
- [问题反馈](https://github.com/football-prediction/python-sdk/issues)
- [技术支持](mailto:support@football-prediction.com)

## 🤝 贡献指南

欢迎贡献代码！请查看 [CONTRIBUTING.md](CONTRIBUTING.md) 了解详细信息。

### 开发环境设置

```bash
# 克隆仓库
git clone https://github.com/football-prediction/python-sdk.git
cd python-sdk

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows

# 安装开发依赖
pip install -e .[dev]

# 运行测试
pytest

# 代码格式化
black football_prediction_sdk/
isort football_prediction_sdk/

# 类型检查
mypy football_prediction_sdk/
```

---

*Football Prediction SDK v1.0.0 - 让足球预测更简单*
