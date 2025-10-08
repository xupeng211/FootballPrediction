# 📊 足球数据采集配置指南

**项目名称**: 足球预测系统 (Football Prediction System)
**配置类型**: 数据采集API设置
**更新时间**: 2025-09-25

---

## 📋 概述

足球预测系统支持多种足球数据源的实时采集，包括赛程、比分、赔率等数据。要实现真实的数据采集，需要配置相应的API密钥和服务。

### 🔧 支持的数据源

| 数据源 | 数据类型 | API提供商 | 免费额度 | 认证方式 |
|--------|----------|------------|----------|----------|
| **Football-Data.org** | 赛程、比分、球队信息 | football-data.org | 100次/天 | API Key |
| **The-Odds-API.com** | 赔率数据、博彩公司 | the-odds-api.com | 500次/天 | API Key |
| **API-Football** | 全面足球数据 | api-football.com | 100次/天 | API Key |
| **SportsDataIO** | 专业体育数据 | sportsdataio.com | 有限免费 | API Key |

---

## 🔑 API密钥配置

### 1. Football-Data.org 配置

#### 注册和获取API密钥

1. 访问 <https://www.football-data.org/>
2. 点击 "Sign Up" 注册账户
3. 验证邮箱后登录
4. 在账户页面找到API密钥

#### 环境变量配置

```bash
# 在 .env.staging 或 .env 文件中添加
FOOTBALL_DATA_API_KEY=your_actual_api_key_here
FOOTBALL_DATA_API_URL=https://api.football-data.org/v4
```

#### API限制和特性

- **免费额度**: 每日100次API调用
- **付费计划**: €10/月 无限制调用
- **数据覆盖**: 200+联赛，实时比分
- **更新频率**: 实时更新
- **支持格式**: JSON

#### 使用示例

```python
# 测试API连接
import requests

api_key = "your_api_key_here"
headers = {"X-Auth-Token": api_key}
url = "https://api.football-data.org/v4/competitions/PL/matches"

response = requests.get(url, headers=headers)
print(response.json())
```

### 2. The-Odds-API.com 配置

#### 注册和获取API密钥

1. 访问 <https://the-odds-api.com/>
2. 注册免费账户
3. 登录后在Dashboard获取API密钥
4. 选择需要的订阅计划

#### 环境变量配置

```bash
# 在 .env.staging 或 .env 文件中添加
ODDS_API_KEY=your_actual_odds_api_key_here
ODDS_API_URL=https://api.the-odds-api.com/v4
```

#### API限制和特性

- **免费额度**: 每日500次API调用
- **付费计划**: $10/月 25,000次调用
- **数据覆盖**: 30+博彩公司，赔率历史
- **更新频率**: 每5分钟更新
- **支持市场**: 1x2、让球、大小球等

#### 使用示例

```python
# 测试API连接
import requests

api_key = "your_odds_api_key_here"
url = f"https://api.the-odds-api.com/v4/sports/soccer_epl/odds/?apiKey={api_key}&regions=uk&markets=h2h,spreads,totals"

response = requests.get(url)
print(response.json())
```

### 3. 可选数据源配置

#### API-Football (备用数据源)

```bash
# 环境变量配置
API_FOOTBALL_KEY=your_api_football_key
API_FOOTBALL_URL=https://v3.football.api-sports.io

# 特性
- 免费额度: 每日100次调用
- 覆盖: 1000+联赛
- 数据: 赛程、比分、统计、伤病
```

#### SportsDataIO (专业数据源)

```bash
# 环境变量配置
SPORTSDATAIO_KEY=your_sportsdataio_key
SPORTSDATAIO_URL=https://api.sportsdata.io

# 特性
- 免费额度: 有限免费调用
- 覆盖: 主要联赛
- 数据: 专业级数据和分析
```

---

## 🔧 系统配置步骤

### 步骤1: 获取API密钥

#### 推荐方案 (免费开发)

```bash
# 1. Football-Data.org (主要用于赛程和比分)
FOOTBALL_DATA_API_KEY=your_free_key_here

# 2. The-Odds-API.com (主要用于赔率数据)
ODDS_API_KEY=your_free_odds_key_here
```

#### 高级方案 (付费生产)

```bash
# 1. Football-Data.org 付费版 (€10/月)
# 无限制调用，实时数据

# 2. The-Odds-API.com 付费版 ($10/月)
# 25,000次调用/月，更多博彩公司
```

### 步骤2: 配置环境变量

#### 更新 .env.staging 文件

```bash
# 足球数据API配置
FOOTBALL_DATA_API_KEY=your_actual_api_key_here
FOOTBALL_DATA_API_URL=https://api.football-data.org/v4

ODDS_API_KEY=your_actual_odds_api_key_here
ODDS_API_URL=https://api.the-odds-api.com/v4

# API调用配置
API_REQUEST_TIMEOUT=30
API_RATE_LIMIT_DELAY=1
API_RETRY_COUNT=3
```

#### 创建生产环境配置 (.env.production)

```bash
# 生产环境配置示例
FOOTBALL_DATA_API_KEY=production_api_key_here
ODDS_API_KEY=production_odds_key_here

# 生产环境更严格的限制
API_REQUEST_TIMEOUT=10
API_RATE_LIMIT_DELAY=0.5
API_RETRY_COUNT=2
```

### 步骤3: 验证配置

#### 测试API连接

```python
# 创建测试脚本 test_api_connection.py
import os
import asyncio
import aiohttp
from dotenv import load_dotenv

load_dotenv()

async def test_football_data_api():
    """测试Football Data API连接"""
    api_key = os.getenv('FOOTBALL_DATA_API_KEY')
    if not api_key:
        print("❌ FOOTBALL_DATA_API_KEY not configured")
        return False

    headers = {"X-Auth-Token": api_key}
    url = "https://api.football-data.org/v4/competitions"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Football Data API connected successfully")
                    print(f"   Available competitions: {len(data.get('competitions', []))}")
                    return True
                else:
                    print(f"❌ Football Data API error: {response.status}")
                    return False
    except Exception as e:
        print(f"❌ Football Data API connection failed: {e}")
        return False

async def test_odds_api():
    """测试The Odds API连接"""
    api_key = os.getenv('ODDS_API_KEY')
    if not api_key:
        print("❌ ODDS_API_KEY not configured")
        return False

    url = f"https://api.the-odds-api.com/v4/sports/soccer_epl/odds/?apiKey={api_key}&regions=uk"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ The Odds API connected successfully")
                    print(f"   Available matches: {len(data) if isinstance(data, list) else 0}")
                    return True
                else:
                    print(f"❌ The Odds API error: {response.status}")
                    return False
    except Exception as e:
        print(f"❌ The Odds API connection failed: {e}")
        return False

async def main():
    """主测试函数"""
    print("🔍 Testing API connections...\n")

    football_result = await test_football_data_api()
    odds_result = await test_odds_api()

    print(f"\n📊 Test Results:")
    print(f"   Football Data API: {'✅' if football_result else '❌'}")
    print(f"   The Odds API: {'✅' if odds_result else '❌'}")

    if football_result and odds_result:
        print("\n🎉 All APIs are working! You can start real data collection.")
    else:
        print("\n⚠️  Some APIs need configuration. Please check your API keys.")

if __name__ == "__main__":
    asyncio.run(main())
```

### 步骤4: 运行数据采集任务

#### 手动测试采集

```bash
# 激活虚拟环境
source .venv/bin/activate

# 设置环境变量
export PYTHONPATH="$(pwd):${PYTHONPATH}"

# 运行测试脚本
python test_api_connection.py

# 运行单个采集任务
python -m celery -A src.tasks worker -l info -Q fixtures -P solo
```

#### 启动定时采集

```bash
# 启动Celery Beat和Worker
python -m celery -A src.tasks beat --loglevel=info
python -m celery -A src.tasks worker --loglevel=info
```

---

## 📊 采集任务配置

### 任务类型和调度

| 任务类型 | 执行频率 | 数据源 | 用途 |
|---------|----------|--------|------|
| **collect_fixtures_task** | 每日1次 | Football-Data.org | 采集未来赛程 |
| **collect_odds_task** | 每小时1次 | The-Odds-API | 采集赔率变化 |
| **collect_scores_task** | 实时/每5分钟 | Football-Data.org | 采集实时比分 |

### 自定义配置示例

#### 修改采集频率 (src/tasks/beat_schedule.py)

```python
# 在 beat_schedule 中修改
beat_schedule = {
    'collect-daily-fixtures': {
        'task': 'tasks.data_collection_tasks.collect_fixtures_task',
        'schedule': crontab(minute=0, hour=8),  # 每天8点
        'options': {'leagues': ['PL', 'BL', 'SA'], 'days_ahead': 7}
    },
    'collect-odds-regular': {
        'task': 'tasks.data_collection_tasks.collect_odds_task',
        'schedule': crontab(minute=0, '*/1'),  # 每小时
        'options': {'bookmakers': ['bet365', 'williamhill']}
    },
    'collect-live-scores': {
        'task': 'tasks.data_collection_tasks.collect_scores_task',
        'schedule': crontab(minute='*/5'),  # 每5分钟
        'options': {'live_only': True}
    },
}
```

---

## 🚨 常见问题和解决方案

### 问题1: API调用频率限制

**错误信息**:

```
429 Too Many Requests
```

**解决方案**:

```bash
# 增加API调用间隔
API_RATE_LIMIT_DELAY=2  # 从1秒增加到2秒

# 减少采集频率
# 修改beat_schedule中的执行间隔
```

### 问题2: API密钥无效

**错误信息**:

```
401 Unauthorized
403 Forbidden
```

**解决方案**:

```bash
# 检查API密钥是否正确
echo $FOOTBALL_DATA_API_KEY

# 重新生成API密钥
# 登录相应的API提供商网站重新获取密钥
```

### 问题3: 网络连接问题

**错误信息**:

```
ConnectionError: Failed to establish connection
```

**解决方案**:

```bash
# 检查网络连接
ping api.football-data.org

# 增加超时时间
API_REQUEST_TIMEOUT=60  # 从30秒增加到60秒

# 配置代理（如果需要）
HTTP_PROXY=http://proxy.example.com:8080
HTTPS_PROXY=http://proxy.example.com:8080
```

### 问题4: 数据格式变化

**错误信息**:

```
KeyError: 'matches'
JSONDecodeError
```

**解决方案**:

```python
# 在数据采集器中添加错误处理
try:
    data = await response.json()
    matches = data.get('matches', [])
    if not matches:
        self.logger.warning("No matches found in response")
except Exception as e:
    self.logger.error(f"Data parsing error: {e}")
    return CollectionResult(status="error", error_count=1)
```

---

## 💡 最佳实践建议

### 1. API密钥管理

#### 安全存储

```bash
# 使用环境变量，不要硬编码在代码中
# 不要将API密钥提交到版本控制
# 定期轮换API密钥
```

#### 配置分离

```bash
# 开发环境使用测试密钥
# 生产环境使用付费密钥
# 不同环境使用不同的配置文件
```

### 2. 错误处理和重试

#### 指数退避重试

```python
async def fetch_with_retry(url, headers, max_retries=3):
    """带重试机制的数据获取"""
    for attempt in range(max_retries):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        return await response.json()
                    elif response.status == 429:
                        wait_time = 2 ** attempt  # 指数退避
                        await asyncio.sleep(wait_time)
                    else:
                        response.raise_for_status()
        except Exception as e:
            if attempt == max_retries - 1:
                raise e
            await asyncio.sleep(2 ** attempt)
    return None
```

### 3. 数据验证

#### 数据质量检查

```python
def validate_fixture_data(fixture):
    """验证赛程数据质量"""
    required_fields = ['id', 'homeTeam', 'awayTeam', 'utcDate']
    return all(field in fixture for field in required_fields)

def validate_odds_data(odds):
    """验证赔率数据质量"""
    required_fields = ['match_id', 'bookmaker', 'market', 'odds']
    return all(field in odds for field in required_fields)
```

### 4. 成本控制

#### API调用监控

```python
# 记录API调用次数和成本
class APICallTracker:
    def __init__(self, daily_limit=1000):
        self.daily_calls = 0
        self.daily_limit = daily_limit

    def can_make_call(self):
        return self.daily_calls < self.daily_limit

    def record_call(self):
        self.daily_calls += 1

    def get_usage_percentage(self):
        return (self.daily_calls / self.daily_limit) * 100
```

---

## 📈 性能优化建议

### 1. 缓存策略

#### Redis缓存配置

```python
# 配置Redis缓存API响应
CACHE_TTL = 300  # 5分钟缓存
CACHE_PREFIX = "football_api:"

async def get_cached_data(key, fetch_func, ttl=CACHE_TTL):
    """获取缓存数据或从API获取"""
    cached_data = await redis.get(f"{CACHE_PREFIX}{key}")
    if cached_data:
        return json.loads(cached_data)

    data = await fetch_func()
    await redis.setex(f"{CACHE_PREFIX}{key}", ttl, json.dumps(data))
    return data
```

### 2. 批量处理

#### 批量API调用

```python
async def batch_collect_fixtures(league_list):
    """批量采集多个联赛的数据"""
    tasks = []
    for league in league_list:
        task = collect_fixtures_for_league(league)
        tasks.append(task)

    results = await asyncio.gather(*tasks, return_exceptions=True)
    return [r for r in results if not isinstance(r, Exception)]
```

### 3. 异步优化

#### 并发控制

```python
import asyncio
from aiohttp import ClientSession, ClientTimeout

class AsyncDataCollector:
    def __init__(self, max_concurrent=10):
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.timeout = ClientTimeout(total=30)

    async def collect_with_semaphore(self, url, headers):
        async with self.semaphore:
            async with ClientSession(timeout=self.timeout) as session:
                async with session.get(url, headers=headers) as response:
                    return await response.json()
```

---

## 🔄 监控和维护

### 1. 采集任务监控

#### 监控指标

```python
# 关键监控指标
COLLECTION_METRICS = {
    'api_calls_total': Counter('api_calls_total', 'Total API calls'),
    'api_errors_total': Counter('api_errors_total', 'Total API errors'),
    'collection_duration': Histogram('collection_duration_seconds', 'Collection duration'),
    'data_quality_score': Gauge('data_quality_score', 'Data quality score')
}
```

### 2. 告警配置

#### 告警规则

```yaml
# Prometheus告警规则
groups:
- name: data_collection
  rules:
  - alert: HighAPIErrorRate
    expr: rate(api_errors_total[5m]) / rate(api_calls_total[5m]) > 0.1
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "High API error rate detected"

  - alert: LowDataQuality
    expr: data_quality_score < 0.8
    for: 10m
    labels:
      severity: critical
    annotations:
      summary: "Low data quality detected"
```

---

## 📞 技术支持

### API提供商支持

| 服务 | 支持网站 | 文档 | 状态页面 |
|------|----------|------|----------|
| **Football-Data.org** | <https://www.football-data.org/> | API Docs | Status Page |
| **The-Odds-API.com** | <https://the-odds-api.com/> | API Docs | Status Page |
| **API-Football** | <https://api-football.com/> | API Docs | Status Page |

### 常见问题资源

1. **API文档**:
   - Football-Data.org: <https://www.football-data.org/documentation>
   - The-Odds-API: <https://the-odds-api.com/liveapidocs>

2. **社区支持**:
   - Stack Overflow
   - Reddit r/sportsdata
   - GitHub Issues

3. **工具推荐**:
   - Postman (API测试)
   - Insomnia (API调试)
   - Prometheus (监控)

---

**配置指南完成时间**: 2025-09-25
**指南版本**: v1.0
**适用版本**: 所有版本

*本配置指南提供了足球数据采集的完整设置说明，包括API密钥获取、环境配置、测试验证和最佳实践。*
