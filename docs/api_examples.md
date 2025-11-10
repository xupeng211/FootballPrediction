# API 使用示例和教程

## 📖 概述

本文档提供了足球预测系统API的详细使用示例，涵盖各种编程语言和常见使用场景。

## 🚀 快速开始

### 基础API地址
- **开发环境**: `http://localhost:8000`
- **预发布环境**: `https://staging-api.footballprediction.com`
- **生产环境**: `https://api.footballprediction.com`

### API文档
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **OpenAPI JSON**: `http://localhost:8000/openapi.json`

## 🔐 认证方式

### JWT认证
```http
Authorization: Bearer <your_jwt_token>
```

### 获取认证令牌
```bash
curl -X POST "https://api.footballprediction.com/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "your_username",
    "password": "your_password"
  }'
```

## 📝 API使用示例

### 1. 获取比赛预测结果

#### cURL示例
```bash
# 基础预测请求
curl -X GET "https://api.footballprediction.com/api/v2/predictions/matches/12345/prediction" \
  -H "Authorization: Bearer your_token"

# 包含详细分析的预测
curl -X GET "https://api.footballprediction.com/api/v2/predictions/matches/12345/prediction?include_details=true" \
  -H "Authorization: Bearer your_token"
```

#### Python示例
```python
import requests
import json

# 基础配置
BASE_URL = "https://api.footballprediction.com"
API_TOKEN = "your_jwt_token"

# 获取预测结果
def get_prediction(match_id: int, include_details: bool = False):
    """获取比赛预测结果"""
    url = f"{BASE_URL}/api/v2/predictions/matches/{match_id}/prediction"

    headers = {
        "Authorization": f"Bearer {API_TOKEN}",
        "Content-Type": "application/json"
    }

    params = {
        "include_details": include_details
    }

    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()

        data = response.json()

        if data["status"] == "success":
            prediction = data["data"]
            print(f"预测结果: {prediction['predicted_outcome']}")
            print(f"置信度: {prediction['confidence_score']}")
            print(f"概率分布: {prediction['probabilities']}")

            if include_details and "analysis" in prediction:
                print(f"详细分析: {prediction['analysis']}")

            return prediction
        else:
            print(f"API错误: {data}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"请求失败: {e}")
        return None

# 使用示例
if __name__ == "__main__":
    result = get_prediction(12345, include_details=True)
    if result:
        print("预测获取成功!")
```

#### JavaScript示例
```javascript
// 获取预测结果
async function getPrediction(matchId, includeDetails = false) {
    const baseUrl = "https://api.footballprediction.com";
    const token = "your_jwt_token";

    const url = new URL(`${baseUrl}/api/v2/predictions/matches/${matchId}/prediction`);
    url.searchParams.append('include_details', includeDetails);

    try {
        const response = await fetch(url, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        if (data.status === 'success') {
            console.log('预测结果:', data.data.predicted_outcome);
            console.log('置信度:', data.data.confidence_score);
            console.log('概率分布:', data.data.probabilities);

            if (includeDetails && data.data.analysis) {
                console.log('详细分析:', data.data.analysis);
            }

            return data.data;
        } else {
            console.error('API错误:', data);
            return null;
        }
    } catch (error) {
        console.error('请求失败:', error);
        return null;
    }
}

// 使用示例
getPrediction(12345, true).then(result => {
    if (result) {
        console.log('预测获取成功!');
    }
});
```

#### Java示例
```java
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import com.fasterxml.jackson.databind.ObjectMapper;

public class FootballPredictionAPI {
    private static final String BASE_URL = "https://api.footballprediction.com";
    private static final String API_TOKEN = "your_jwt_token";
    private static final ObjectMapper objectMapper = new ObjectMapper();

    public static PredictionResult getPrediction(int matchId, boolean includeDetails) {
        HttpClient client = HttpClient.newBuilder()
            .connectTimeout(Duration.ofSeconds(10))
            .build();

        String url = String.format("%s/api/v2/predictions/matches/%d/prediction?include_details=%b",
                              BASE_URL, matchId, includeDetails);

        HttpRequest request = HttpRequest.newBuilder()
            .uri(URI.create(url))
            .header("Authorization", "Bearer " + API_TOKEN)
            .header("Content-Type", "application/json")
            .timeout(Duration.ofSeconds(5))
            .GET()
            .build();

        try {
            HttpResponse<String> response = client.send(request,
                HttpResponse.BodyHandlers.ofString());

            if (response.statusCode() == 200) {
                ApiResponse apiResponse = objectMapper.readValue(response.body(), ApiResponse.class);
                if ("success".equals(apiResponse.getStatus())) {
                    return apiResponse.getData();
                }
            }
        } catch (Exception e) {
            e.printStackTrace();
        }

        return null;
    }

    // 数据模型类
    public static class ApiResponse {
        private String status;
        private PredictionResult data;

        // getters and setters
        public String getStatus() { return status; }
        public void setStatus(String status) { this.status = status; }
        public PredictionResult getData() { return data; }
        public void setData(PredictionResult data) { this.data = data; }
    }

    public static class PredictionResult {
        private int matchId;
        private String predictedOutcome;
        private double confidenceScore;
        private Probabilities probabilities;

        // getters and setters
        public int getMatchId() { return matchId; }
        public void setMatchId(int matchId) { this.matchId = matchId; }
        public String getPredictedOutcome() { return predictedOutcome; }
        public void setPredictedOutcome(String predictedOutcome) { this.predictedOutcome = predictedOutcome; }
        public double getConfidenceScore() { return confidenceScore; }
        public void setConfidenceScore(double confidenceScore) { this.confidenceScore = confidenceScore; }
        public Probabilities getProbabilities() { return probabilities; }
        public void setProbabilities(Probabilities probabilities) { this.probabilities = probabilities; }
    }

    public static class Probabilities {
        private double homeWin;
        private double draw;
        private double awayWin;

        // getters and setters
        public double getHomeWin() { return homeWin; }
        public void setHomeWin(double homeWin) { this.homeWin = homeWin; }
        public double getDraw() { return draw; }
        public void setDraw(double draw) { this.draw = draw; }
        public double getAwayWin() { return awayWin; }
        public void setAwayWin(double awayWin) { this.awayWin = awayWin; }
    }

    // 使用示例
    public static void main(String[] args) {
        PredictionResult result = getPrediction(12345, true);
        if (result != null) {
            System.out.println("预测结果: " + result.getPredictedOutcome());
            System.out.println("置信度: " + result.getConfidenceScore());
            System.out.println("概率分布: " + result.getProbabilities());
        }
    }
}
```

### 2. 获取热门预测

#### Python示例
```python
def get_popular_predictions(limit: int = 10, time_range: str = "24h"):
    """获取热门预测"""
    url = f"{BASE_URL}/api/v2/predictions/popular"

    headers = {
        "Authorization": f"Bearer {API_TOKEN}",
        "Content-Type": "application/json"
    }

    params = {
        "limit": limit,
        "time_range": time_range
    }

    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()

        data = response.json()

        if data["status"] == "success":
            predictions = data["data"]
            print(f"获取到 {len(predictions)} 个热门预测")

            for i, pred in enumerate(predictions, 1):
                print(f"\n{i}. 比赛 {pred['match_id']}")
                print(f"   预测: {pred['predicted_outcome']}")
                print(f"   置信度: {pred['confidence_score']}")
                print(f"   热度: {pred['popularity_score']}")

            return predictions
        else:
            print(f"API错误: {data}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"请求失败: {e}")
        return None

# 使用示例
popular = get_popular_predictions(limit=5, time_range="24h")
```

### 3. 获取用户预测历史

#### Python示例
```python
def get_user_prediction_history(user_id: int, page: int = 1, size: int = 20, status_filter: str = None):
    """获取用户预测历史"""
    url = f"{BASE_URL}/api/v2/predictions/user/{user_id}/history"

    headers = {
        "Authorization": f"Bearer {API_TOKEN}",
        "Content-Type": "application/json"
    }

    params = {
        "page": page,
        "size": size
    }

    if status_filter:
        params["status_filter"] = status_filter

    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()

        data = response.json()

        if data["status"] == "success":
            predictions = data["data"]
            pagination = data["pagination"]
            statistics = data["statistics"]

            print(f"用户 {user_id} 的预测历史:")
            print(f"总预测数: {statistics['total_predictions']}")
            print(f"准确率: {statistics['accuracy_rate']:.1%}")
            print(f"平均置信度: {statistics['confidence_avg']:.2f}")

            for pred in predictions:
                status = pred["status"]
                outcome = pred.get("actual_outcome", "待定")
                print(f"\n比赛 {pred['match_id']}: {pred['predicted_outcome']} -> {outcome} ({status})")

            return data
        else:
            print(f"API错误: {data}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"请求失败: {e}")
        return None

# 使用示例
history = get_user_prediction_history(123, page=1, size=10, status_filter="correct")
```

### 4. 获取统计信息

#### Python示例
```python
def get_prediction_statistics(time_range: str = "7d"):
    """获取预测统计信息"""
    url = f"{BASE_URL}/api/v2/predictions/statistics"

    headers = {
        "Authorization": f"Bearer {API_TOKEN}",
        "Content-Type": "application/json"
    }

    params = {
        "time_range": time_range
    }

    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()

        data = response.json()

        if data["status"] == "success":
            stats = data["data"]

            print(f"预测统计 ({time_range}):")
            print(f"总预测数: {stats['total_predictions']}")
            print(f"准确率: {stats['accuracy_rate']:.1%}")
            print(f"平均置信度: {stats['average_confidence']:.2f}")

            print(f"\n结果分布:")
            outcomes = stats['popular_outcomes']
            for outcome, count in outcomes.items():
                print(f"  {outcome}: {count}")

            print(f"\n性能指标:")
            perf = stats['performance_metrics']
            print(f"  平均响应时间: {perf['avg_response_time_ms']:.1f}ms")
            print(f"  缓存命中率: {perf['cache_hit_rate']:.1%}")

            return stats
        else:
            print(f"API错误: {data}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"请求失败: {e}")
        return None

# 使用示例
stats = get_prediction_statistics("7d")
```

### 5. 缓存管理

#### 缓存预热 (管理员权限)
```python
def warmup_cache():
    """缓存预热"""
    url = f"{BASE_URL}/api/v2/predictions/cache/warmup"

    headers = {
        "Authorization": f"Bearer {ADMIN_TOKEN}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(url, headers=headers)
        response.raise_for_status()

        data = response.json()
        print(f"缓存预热任务已启动: {data['message']}")
        print(f"预计耗时: {data.get('estimated_duration', '未知')}")

        return data
    except requests.exceptions.RequestException as e:
        print(f"请求失败: {e}")
        return None

# 使用示例
warmup_result = warmup_cache()
```

#### 清除缓存 (管理员权限)
```python
def clear_cache(pattern: str = None):
    """清除缓存"""
    url = f"{BASE_URL}/api/v2/predictions/cache/clear"

    headers = {
        "Authorization": f"Bearer {ADMIN_TOKEN}",
        "Content-Type": "application/json"
    }

    params = {}
    if pattern:
        params["pattern"] = pattern

    try:
        response = requests.delete(url, headers=headers, params=params)
        response.raise_for_status()

        data = response.json()
        print(f"缓存清除成功: {data['message']}")
        print(f"清除的键数量: {data.get('cleared_keys', 0)}")
        print(f"释放内存: {data.get('memory_freed', '0MB')}")

        return data
    except requests.exceptions.RequestException as e:
        print(f"请求失败: {e}")
        return None

# 使用示例
# 清除所有缓存
clear_all = clear_cache()

# 只清除预测结果缓存
clear_predictions = clear_cache("prediction_result")
```

## 🔧 错误处理

### 通用错误处理模式
```python
import requests
from typing import Optional, Dict, Any

class FootballAPIError(Exception):
    """自定义API异常"""
    def __init__(self, message: str, status_code: int = None, response_data: Dict = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data or {}

def make_api_request(url: str, method: str = "GET", headers: Dict = None,
                     params: Dict = None, data: Dict = None) -> Optional[Dict]:
    """通用API请求处理"""
    default_headers = {
        "Content-Type": "application/json",
        "User-Agent": "FootballPredictionAPI/1.0"
    }

    if headers:
        default_headers.update(headers)

    try:
        response = requests.request(
            method=method,
            url=url,
            headers=default_headers,
            params=params,
            json=data,
            timeout=30
        )

        # 处理HTTP错误状态码
        if response.status_code == 401:
            raise FootballAPIError("认证失败，请检查令牌", 401)
        elif response.status_code == 403:
            raise FootballAPIError("权限不足", 403)
        elif response.status_code == 404:
            raise FootballAPIError("资源不存在", 404)
        elif response.status_code == 429:
            raise FootballAPIError("请求频率过高", 429)
        elif response.status_code >= 500:
            raise FootballAPIError("服务器内部错误", response.status_code)

        response.raise_for_status()

        data = response.json()

        # 检查API响应状态
        if data.get("status") != "success":
            raise FootballAPIError(
                f"API错误: {data.get('detail', '未知错误')}",
                response.status_code,
                data
            )

        return data

    except requests.exceptions.Timeout:
        raise FootballAPIError("请求超时")
    except requests.exceptions.ConnectionError:
        raise FootballAPIError("网络连接错误")
    except requests.exceptions.RequestException as e:
        raise FootballAPIError(f"请求异常: {str(e)}")
    except ValueError as e:
        raise FootballAPIError(f"JSON解析错误: {str(e)}")

# 使用示例
try:
    result = make_api_request(
        f"{BASE_URL}/api/v2/predictions/matches/12345/prediction",
        headers={"Authorization": f"Bearer {API_TOKEN}"}
    )
    print("API调用成功:", result)
except FootballAPIError as e:
    print(f"API错误: {e}")
    if e.response_data:
        print(f"错误详情: {e.response_data}")
```

## 📊 性能优化建议

### 1. 使用缓存
```python
import time
from functools import lru_cache
import requests_cache

# 启用requests缓存
requests_cache.install_cache(
    'football_api_cache',
    expire_after=300,  # 5分钟缓存
    allowable_methods=('GET', 'HEAD')
)

# 使用内存缓存
@lru_cache(maxsize=128)
def get_prediction_cached(match_id: int, include_details: bool = False):
    """带缓存的预测获取"""
    return get_prediction(match_id, include_details)
```

### 2. 批量请求
```python
import asyncio
import aiohttp
from typing import List

async def get_multiple_predictions(match_ids: List[int]) -> List[Dict]:
    """批量获取多个预测结果"""
    async with aiohttp.ClientSession() as session:
        tasks = []
        for match_id in match_ids:
            task = get_prediction_async(session, match_id)
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        predictions = []
        for result in results:
            if isinstance(result, Exception):
                print(f"预测获取失败: {result}")
            else:
                predictions.append(result)

        return predictions

async def get_prediction_async(session, match_id: int):
    """异步获取单个预测"""
    url = f"{BASE_URL}/api/v2/predictions/matches/{match_id}/prediction"
    headers = {"Authorization": f"Bearer {API_TOKEN}"}

    async with session.get(url, headers=headers) as response:
        response.raise_for_status()
        data = await response.json()
        return data.get("data") if data.get("status") == "success" else None

# 使用示例
import asyncio
match_ids = [12345, 12346, 12347, 12348, 12349]
predictions = asyncio.run(get_multiple_predictions(match_ids))
print(f"批量获取到 {len(predictions)} 个预测结果")
```

### 3. 连接池配置
```python
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# 创建带有重试机制的会话
session = requests.Session()

# 重试策略
retry_strategy = Retry(
    total=3,
    backoff_factor=1,
    status_forcelist=[429, 500, 502, 503, 504],
)

# 适配器配置
adapter = HTTPAdapter(
    max_retries=retry_strategy,
    pool_connections=20,
    pool_maxsize=20
)

session.mount("http://", adapter)
session.mount("https://", adapter)

# 使用会话进行请求
def get_prediction_with_session(match_id: int):
    """使用会话获取预测"""
    url = f"{BASE_URL}/api/v2/predictions/matches/{match_id}/prediction"
    headers = {"Authorization": f"Bearer {API_TOKEN}"}

    response = session.get(url, headers=headers)
    response.raise_for_status()

    data = response.json()
    return data.get("data") if data.get("status") == "success" else None
```

## 🧪 测试示例

### 单元测试示例
```python
import unittest
from unittest.mock import Mock, patch
import requests

class TestFootballPredictionAPI(unittest.TestCase):
    def setUp(self):
        self.base_url = "https://api.footballprediction.com"
        self.token = "test_token"
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

    @patch('requests.get')
    def test_get_prediction_success(self, mock_get):
        """测试成功获取预测"""
        # 模拟API响应
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": {
                "match_id": 12345,
                "predicted_outcome": "home_win",
                "confidence_score": 0.85,
                "probabilities": {
                    "home_win": 0.65,
                    "draw": 0.20,
                    "away_win": 0.15
                }
            }
        }
        mock_get.return_value = mock_response

        # 调用API
        result = get_prediction(12345)

        # 验证结果
        self.assertIsNotNone(result)
        self.assertEqual(result["predicted_outcome"], "home_win")
        self.assertEqual(result["confidence_score"], 0.85)

        # 验证请求参数
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        self.assertIn("Authorization", call_args[1]["headers"])

    @patch('requests.get')
    def test_get_prediction_error(self, mock_get):
        """测试API错误处理"""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.json.return_value = {
            "detail": "Match not found: 99999",
            "error_code": "MATCH_NOT_FOUND"
        }
        mock_get.return_value = mock_response

        # 调用API
        result = get_prediction(99999)

        # 验证结果
        self.assertIsNone(result)

if __name__ == '__main__':
    unittest.main()
```

### 集成测试示例
```python
import pytest
import requests

class TestFootballPredictionAPIIntegration:
    @pytest.fixture(scope="module")
    def api_config(self):
        return {
            "base_url": "http://localhost:8000",
            "token": "test_token"
        }

    def test_health_check(self, api_config):
        """测试健康检查端点"""
        response = requests.get(f"{api_config['base_url']}/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data

    def test_get_prediction(self, api_config):
        """测试获取预测"""
        headers = {"Authorization": f"Bearer {api_config['token']}"}

        response = requests.get(
            f"{api_config['base_url']}/api/v2/predictions/matches/12345/prediction",
            headers=headers
        )

        # 根据实际API行为调整断言
        if response.status_code == 200:
            data = response.json()
            assert data["status"] == "success"
            assert "data" in data
        elif response.status_code == 404:
            # 测试数据不存在的情况
            pass
        else:
            pytest.fail(f"意外的状态码: {response.status_code}")

if __name__ == '__main__':
    pytest.main([__file__])
```

## 📚 更多资源

- **API参考文档**: [完整API文档](./api_reference.md)
- **错误代码说明**: [错误代码列表](./error_codes.md)
- **最佳实践指南**: [API最佳实践](./best_practices.md)
- **SDK和工具**: [官方SDK](./sdks.md)

## 🆘 获取帮助

如果在使用API过程中遇到问题，请：

1. 查看 [API文档](http://localhost:8000/docs)
2. 检查 [错误代码列表](./error_codes.md)
3. 联系技术支持: api-support@footballprediction.com
4. 提交Issue到 [GitHub仓库](https://github.com/xupeng211/FootballPrediction/issues)

---

*最后更新: 2025-11-10*