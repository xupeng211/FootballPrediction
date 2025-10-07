# API 使用示例

本文档提供了足球预测系统 API 的详细使用示例。

## 目录

1. [认证](#认证)
2. [预测接口](#预测接口)
3. [数据查询](#数据查询)
4. [批量操作](#批量操作)
5. [实时流](#实时流)
6. [错误处理](#错误处理)

## 认证

所有 API 请求都需要在请求头中包含认证令牌：

```bash
# 获取访问令牌
curl -X POST "https://api.football-prediction.com/auth/token" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "your_username",
    "password": "your_password"
  }'

# 响应示例
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

使用令牌访问 API：

```bash
curl -X GET "https://api.football-prediction.com/api/v1/predictions/12345" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

## 预测接口

### 1. 预测单场比赛

```bash
curl -X POST "https://api.football-prediction.com/api/v1/predictions/predict" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "match_id": 12345,
    "force_refresh": false,
    "include_features": true
  }'
```

**响应示例：**

```json
{
  "match_id": 12345,
  "prediction": "home",
  "probabilities": {
    "home_win": 0.52,
    "draw": 0.28,
    "away_win": 0.20
  },
  "confidence": 0.68,
  "model_version": "1.2.0",
  "model_name": "football_baseline_model",
  "prediction_time": "2024-01-01T14:30:00Z",
  "match_info": {
    "id": 12345,
    "home_team": "Manchester United",
    "away_team": "Liverpool",
    "league": "Premier League",
    "match_time": "2024-01-01T15:00:00Z",
    "venue": "Old Trafford"
  },
  "features": {
    "home_recent_wins": 3,
    "away_recent_wins": 2,
    "h2h_home_advantage": 0.55,
    "home_implied_probability": 0.45
  },
  "odds": {
    "home_win": 2.1,
    "draw": 3.4,
    "away_win": 3.6,
    "bookmaker": "Bet365"
  }
}
```

### 2. 批量预测

```bash
curl -X POST "https://api.football-prediction.com/api/v1/predictions/predict/batch" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "match_ids": [12345, 12346, 12347, 12348],
    "force_refresh": false,
    "include_features": false
  }'
```

**响应示例：**

```json
{
  "total": 4,
  "successful": 4,
  "failed": 0,
  "results": [
    {
      "match_id": 12345,
      "prediction": "home",
      "probabilities": {"home_win": 0.52, "draw": 0.28, "away_win": 0.20},
      "confidence": 0.68
    },
    {
      "match_id": 12346,
      "prediction": "draw",
      "probabilities": {"home_win": 0.35, "draw": 0.40, "away_win": 0.25},
      "confidence": 0.72
    },
    {
      "match_id": 12347,
      "prediction": "away",
      "probabilities": {"home_win": 0.30, "draw": 0.30, "away_win": 0.40},
      "confidence": 0.65
    },
    {
      "match_id": 12348,
      "prediction": "home",
      "probabilities": {"home_win": 0.48, "draw": 0.32, "away_win": 0.20},
      "confidence": 0.60
    }
  ]
}
```

### 3. 预测即将开始的比赛

```bash
curl -X POST "https://api.football-prediction.com/api/v1/predictions/predict/upcoming" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "hours_ahead": 24,
    "league_ids": [39, 140],  # Premier League, La Liga
    "force_refresh": false
  }'
```

### 4. 获取比赛预测

```bash
curl -X GET "https://api.football-prediction.com/api/v1/predictions/match/12345?include_features=true" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 5. 验证预测结果

```bash
curl -X POST "https://api.football-prediction.com/api/v1/predictions/verify/12345" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## 数据查询

### 1. 获取比赛列表

```bash
# 获取所有比赛
curl -X GET "https://api.football-prediction.com/api/v1/data/matches?limit=10" \
  -H "Authorization: Bearer YOUR_TOKEN"

# 按联赛筛选
curl -X GET "https://api.football-prediction.com/api/v1/data/matches?league_id=39" \
  -H "Authorization: Bearer YOUR_TOKEN"

# 按状态筛选
curl -X GET "https://api.football-prediction.com/api/v1/data/matches?status=SCHEDULED" \
  -H "Authorization: Bearer YOUR_TOKEN"

# 按日期范围筛选
curl -X GET "https://api.football-prediction.com/api/v1/data/matches?start_date=2024-01-01T00:00:00Z&end_date=2024-01-02T00:00:00Z" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 2. 获取球队信息

```bash
# 获取所有球队
curl -X GET "https://api.football-prediction.com/api/v1/data/teams" \
  -H "Authorization: Bearer YOUR_TOKEN"

# 搜索球队
curl -X GET "https://api.football-prediction.com/api/v1/data/teams?search=United" \
  -H "Authorization: Bearer YOUR_TOKEN"

# 获取特定球队
curl -X GET "https://api.football-prediction.com/api/v1/data/teams/100" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 3. 获取联赛信息

```bash
# 获取所有联赛
curl -X GET "https://api.football-prediction.com/api/v1/data/leagues" \
  -H "Authorization: Bearer YOUR_TOKEN"

# 按国家筛选
curl -X GET "https://api.football-prediction.com/api/v1/data/leagues?country=England" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 4. 获取比赛赔率

```bash
curl -X GET "https://api.football-prediction.com/api/v1/data/matches/12345/odds?bookmaker=Bet365" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 5. 获取数据统计

```bash
curl -X GET "https://api.football-prediction.com/api/v1/data/statistics/overview" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 6. 搜索数据

```bash
curl -X GET "https://api.football-prediction.com/api/v1/data/search?q=Manchester&type=teams" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## 批量操作

### 批量预测最佳实践

```python
import asyncio
import aiohttp

async def batch_predict(match_ids, token):
    """批量预测示例"""
    url = "https://api.football-prediction.com/api/v1/predictions/predict/batch"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # 分批处理（每次最多100场）
    batch_size = 100
    results = []

    for i in range(0, len(match_ids), batch_size):
        batch = match_ids[i:i + batch_size]
        payload = {
            "match_ids": batch,
            "force_refresh": False,
            "include_features": False
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    results.extend(data["results"])
                else:
                    print(f"Batch {i//batch_size + 1} failed: {response.status}")

    return results

# 使用示例
match_ids = list(range(10000, 10500))
results = asyncio.run(batch_predict(match_ids, "YOUR_TOKEN"))
print(f"预测完成: {len(results)} 场比赛")
```

## 实时流

### Server-Sent Events (SSE)

```javascript
// JavaScript 示例：订阅比赛预测更新
const eventSource = new EventSource(
  'https://api.football-prediction.com/api/v1/predictions/stream/matches/12345',
  {
    headers: {
      'Authorization': 'Bearer YOUR_TOKEN'
    }
  }
);

eventSource.onmessage = function(event) {
  const prediction = JSON.parse(event.data);
  console.log('新预测:', prediction);

  // 更新UI
  updatePredictionUI(prediction);
};

eventSource.onerror = function(event) {
  console.error('流连接错误:', event);
};

eventSource.onopen = function(event) {
  console.log('流连接已建立');
};
```

```python
# Python 示例：使用 SSE客户端
import sseclient
import requests

def subscribe_to_match(match_id, token):
    """订阅比赛预测流"""
    url = f"https://api.football-prediction.com/api/v1/predictions/stream/matches/{match_id}"
    headers = {"Authorization": f"Bearer {token}"}

    response = requests.get(url, headers=headers, stream=True)
    client = sseclient.SSEClient(response)

    for event in client.events():
        if event.event == 'message':
            prediction = json.loads(event.data)
            print(f"收到预测更新: {prediction}")
        elif event.event == 'error':
            print(f"错误: {event.data}")

# 使用示例
subscribe_to_match(12345, "YOUR_TOKEN")
```

## 错误处理

### 错误响应格式

所有错误都遵循统一的响应格式：

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "请求参数验证失败",
    "type": "validation_error",
    "details": [
      {
        "loc": ["body", "match_id"],
        "msg": "field required",
        "type": "value_error.missing"
      }
    ],
    "timestamp": "2024-01-01T14:30:00Z"
  }
}
```

### 常见错误代码

| 错误代码 | HTTP状态码 | 描述 |
|---------|------------|------|
| VALIDATION_ERROR | 400 | 请求参数验证失败 |
| UNAUTHORIZED | 401 | 未授权或令牌无效 |
| FORBIDDEN | 403 | 权限不足 |
| NOT_FOUND | 404 | 资源不存在 |
| MATCH_NOT_FOUND | 404 | 比赛不存在 |
| PREDICTION_FAILED | 500 | 预测失败 |
| RATE_LIMIT_EXCEEDED | 429 | 请求频率超限 |

### 错误处理示例

```python
import requests
from requests.exceptions import RequestException

def safe_predict_match(match_id, token):
    """安全的预测请求示例"""
    url = f"https://api.football-prediction.com/api/v1/predictions/predict"
    headers = {"Authorization": f"Bearer {token}"}
    payload = {"match_id": match_id}

    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            print(f"比赛 {match_id} 不存在")
        elif e.response.status_code == 401:
            print("认证失败，请检查令牌")
        else:
            error_data = e.response.json()
            print(f"预测失败: {error_data['error']['message']}")
        return None
    except RequestException as e:
        print(f"网络错误: {e}")
        return None

# 使用示例
result = safe_predict_match(12345, "YOUR_TOKEN")
if result:
    print(f"预测结果: {result['prediction']}")
```

## Python SDK 示例

```python
from football_prediction_client import FootballPredictionClient

# 初始化客户端
client = FootballPredictionClient(
    base_url="https://api.football-prediction.com",
    api_key="YOUR_TOKEN"
)

# 预测单场比赛
prediction = client.predict_match(
    match_id=12345,
    include_features=True
)
print(f"预测: {prediction.prediction} (置信度: {prediction.confidence})")

# 批量预测
predictions = client.batch_predict(
    match_ids=[12345, 12346, 12347],
    force_refresh=False
)

# 获取即将开始的比赛
upcoming = client.predict_upcoming_matches(
    hours_ahead=24,
    league_ids=[39]
)

# 订阅实时更新
def on_prediction_update(prediction):
    print(f"预测更新: {prediction}")

client.subscribe_match_updates(
    match_id=12345,
    callback=on_prediction_update
)
```

## SDK 安装

```bash
pip install football-prediction-client
```

或使用 Poetry：

```bash
poetry add football-prediction-client
```

## 更多示例

更多示例和高级用法请参考：

- [Python SDK 文档](./PYTHON_SDK.md)
- [JavaScript SDK 文档](./JAVASCRIPT_SDK.md)
- [最佳实践指南](./BEST_PRACTICES.md)
- [性能优化建议](./PERFORMANCE_OPTIMIZATION.md)