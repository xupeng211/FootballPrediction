# 🚀 API使用示例

## 健康检查

检查API服务状态

### Curl
```bash
curl -X GET "http://localhost:8000/api/v1/health/" -H "accept: application/json"
```

### Python
```python
import requests

response = requests.get("http://localhost:8000/api/v1/health/")
if response.status_code == 200:
    print(f"API状态: {response.json()['status']}")
else:
    print(f"健康检查失败: {response.status_code}")
```

### 响应
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

## 获取预测列表

获取所有可用的预测

### Curl
```bash
curl -X GET "http://localhost:8000/predictions/" -H "accept: application/json"
```

### Python
```python
import requests

response = requests.get("http://localhost:8000/predictions/")
if response.status_code == 200:
    predictions = response.json()
    print(f"找到 {len(predictions.get('predictions', []))} 个预测")
else:
    print(f"获取预测失败: {response.status_code}")
```

### 响应
```json
{
  "predictions": [
    {
      "prediction_id": "pred_123",
      "match_id": 1,
      "result": "win",
      "confidence": 0.85,
      "created_at": "2024-01-01T12:00:00Z"
    }
  ],
  "total": 1
}
```

## 生成比赛预测

为指定比赛生成新的预测

### Curl
```bash
curl -X POST "http://localhost:8000/predictions/1/predict" \
  -H "accept: application/json" \
  -H "Content-Type: application/json" \
  -d '{"model_type": "ml", "features": {"team_form": [1, 0, 1], "head_to_head": [2, 1]}}'
```

### Python
```python
import requests

prediction_data = {
    "model_type": "ml",
    "features": {
        "team_form": [1, 0, 1],
        "head_to_head": [2, 1]
    }
}

response = requests.post(
    "http://localhost:8000/predictions/1/predict",
    json=prediction_data
)

if response.status_code == 200:
    prediction = response.json()
    print(f"预测结果: {prediction['result']}")
    print(f"置信度: {prediction['confidence']:.2f}")
else:
    print(f"预测生成失败: {response.status_code}")
```

### 响应
```json
{
  "prediction_id": "pred_456",
  "match_id": 1,
  "result": "win",
  "confidence": 0.87,
  "created_at": "2024-01-01T12:05:00Z"
}
```

## 获取系统指标

获取详细的系统和业务指标

### Curl
```bash
curl -X GET "http://localhost:8000/monitoring/metrics" -H "accept: application/json"
```

### Python
```python
import requests

response = requests.get("http://localhost:8000/monitoring/metrics")
if response.status_code == 200:
    metrics = response.json()
    print(f"系统状态: {metrics['status']}")
    print(f"CPU使用率: {metrics['system']['cpu_percent']:.1f}%")
    print(f"24小时预测数: {metrics['business']['24h_predictions']}")
    print(f"30天准确率: {metrics['business']['model_accuracy_30d']:.1f}%")
else:
    print(f"获取指标失败: {response.status_code}")
```

### 响应
```json
{
  "status": "ok",
  "response_time_ms": 15.2,
  "system": {
    "cpu_percent": 45.2,
    "memory": {
      "total": 8589934592,
      "available": 2705326080,
      "percent": 68.5
    }
  },
  "database": {
    "healthy": true,
    "response_time_ms": 12.5,
    "statistics": {
      "teams_count": 150,
      "matches_count": 2500,
      "predictions_count": 1800
    }
  },
  "business": {
    "24h_predictions": 150,
    "upcoming_matches_7d": 25,
    "model_accuracy_30d": 78.5,
    "last_updated": "2024-01-01T12:00:00Z"
  }
}
```
