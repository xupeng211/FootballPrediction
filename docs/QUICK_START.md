# 🚀 Football Prediction System - 快速开始指南

## 📋 目录

- [5分钟快速体验](#5分钟快速体验)
- [10分钟本地开发环境](#10分钟本地开发环境)
- [30分钟完整部署](#30分钟完整部署)
- [SDK快速上手](#sdk快速上手)
- [第一个API调用](#第一个api调用)
- [常见问题](#常见问题)

---

## ⚡ 5分钟快速体验

### 使用在线演示
无需安装，直接体验系统功能：

1. **访问演示环境**
   ```
   https://demo.football-prediction.com
   ```

2. **测试API**
   ```bash
   curl -X GET "https://api.football-prediction.com/v1/health"
   ```

3. **查看文档**
   ```
   https://docs.football-prediction.com
   ```

### Docker快速运行
```bash
# 克隆项目
git clone https://github.com/your-org/football-prediction.git
cd football-prediction

# 一键启动
make quick-start

# 访问API文档
open http://localhost:8000/docs
```

---

## 🛠️ 10分钟本地开发环境

### 环境要求
- Python 3.11+
- Git
- 4GB+ 内存

### 快速安装

#### 1. 克隆项目
```bash
git clone https://github.com/your-org/football-prediction.git
cd football-prediction
```

#### 2. 一键环境设置
```bash
# 自动安装依赖和配置环境
make install

# 环境检查
make env-check
```

#### 3. 启动数据库服务
```bash
# 使用Docker启动数据库
docker-compose up -d postgres redis

# 等待服务启动
sleep 10
```

#### 4. 运行数据库迁移
```bash
# 初始化数据库
make db-init

# 填充示例数据
make db-seed
```

#### 5. 启动开发服务器
```bash
# 启动API服务器
make dev

# 服务器将在 http://localhost:8000 启动
```

#### 6. 验证安装
```bash
# 检查API健康状态
curl http://localhost:8000/health

# 运行基础测试
make test.unit
```

### 访问服务
- **API文档**: http://localhost:8000/docs
- **ReDoc文档**: http://localhost:8000/redoc
- **管理界面**: http://localhost:8000/admin
- **API监控**: http://localhost:8000/metrics

---

## 🏗️ 30分钟完整部署

### 生产环境部署

#### 1. 服务器准备
```bash
# 安装Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# 安装Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

#### 2. 环境配置
```bash
# 克隆项目
git clone https://github.com/your-org/football-prediction.git
cd football-prediction

# 复制环境配置
cp .env.example .env.production

# 编辑配置文件
nano .env.production
```

#### 3. 配置环境变量
```bash
# .env.production
DATABASE_URL=postgresql://user:password@postgres:5432/football_pred
REDIS_URL=redis://redis:6379
SECRET_KEY=your-super-secret-key-here
DEBUG=false
ENVIRONMENT=production

# API配置
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=4

# 安全配置
CORS_ORIGINS=https://yourdomain.com
ALLOWED_HOSTS=yourdomain.com
```

#### 4. 构建和部署
```bash
# 构建生产镜像
docker-compose -f docker-compose.prod.yml build

# 启动生产服务
docker-compose -f docker-compose.prod.yml up -d

# 查看服务状态
docker-compose -f docker-compose.prod.yml ps
```

#### 5. 初始化生产数据
```bash
# 运行数据库迁移
docker-compose -f docker-compose.prod.yml exec app alembic upgrade head

# 创建管理员用户
docker-compose -f docker-compose.prod.yml exec app python scripts/create_admin.py
```

#### 6. 配置反向代理
```nginx
# /etc/nginx/sites-available/football-prediction
server {
    listen 80;
    server_name yourdomain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

#### 7. SSL证书配置
```bash
# 使用Let's Encrypt
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com
```

### 验证部署
```bash
# 检查服务状态
curl -f https://yourdomain.com/health || exit 1

# 检查API文档
curl -f https://yourdomain.com/docs || exit 1

# 运行生产环境测试
docker-compose -f docker-compose.prod.yml exec app make test.smoke
```

---

## 🐍 SDK快速上手

### 安装SDK
```bash
# 从PyPI安装
pip install football-prediction-sdk

# 或从源码安装
git clone https://github.com/your-org/football-prediction-sdk.git
cd football-prediction-sdk
pip install -e .
```

### 基础使用

#### 1. 创建客户端
```python
from football_prediction_sdk import FootballPredictionClient

# 使用API密钥创建客户端
client = FootballPredictionClient(
    api_key="your_api_key_here",
    base_url="https://api.football-prediction.com/v1"
)
```

#### 2. 获取比赛信息
```python
# 获取即将进行的比赛
matches = await client.matches.list_upcoming(limit=10)

for match in matches:
    print(f"比赛: {match.home_team} vs {match.away_team}")
    print(f"时间: {match.match_date}")
    print(f"联赛: {match.league}")
```

#### 3. 创建预测
```python
from datetime import datetime

# 创建预测请求
prediction = await client.predictions.create(
    match_id="match_123",
    home_team="Manchester United",
    away_team="Liverpool",
    match_date=datetime(2025, 11, 15, 20, 0),
    features={
        "team_form": {
            "home_last_5": [3, 1, 0, 3, 1],
            "away_last_5": [1, 0, 3, 1, 0]
        },
        "head_to_head": {
            "home_wins": 8,
            "away_wins": 5,
            "draws": 7
        }
    }
)

print(f"预测结果: {prediction.predicted_winner}")
print(f"置信度: {prediction.confidence:.2%}")
print(f"主胜概率: {prediction.home_win_prob:.2%}")
print(f"平局概率: {prediction.draw_prob:.2%}")
print(f"客胜概率: {prediction.away_win_prob:.2%}")
```

#### 4. 批量操作
```python
# 批量创建预测
predictions_data = [
    {
        "match_id": "match_1",
        "home_team": "Team A",
        "away_team": "Team B",
        "match_date": "2025-11-15T20:00:00Z"
    },
    {
        "match_id": "match_2",
        "home_team": "Team C",
        "away_team": "Team D",
        "match_date": "2025-11-16T19:00:00Z"
    }
]

predictions = await client.predictions.create_batch(predictions_data)

for pred in predictions:
    print(f"比赛 {pred.match_id}: {pred.predicted_winner}")
```

#### 5. 错误处理
```python
from football_prediction_sdk.exceptions import (
    AuthenticationError,
    ValidationError,
    RateLimitError,
    BusinessError
)

try:
    prediction = await client.predictions.create(data)
except AuthenticationError:
    print("❌ 认证失败，请检查API密钥")
except ValidationError as e:
    print(f"❌ 数据验证错误: {e}")
except RateLimitError as e:
    print(f"⏰ 请求频率限制，{e.retry_after}秒后重试")
except BusinessError as e:
    print(f"💼 业务逻辑错误: {e}")
except Exception as e:
    print(f"❓ 未知错误: {e}")
```

### 高级功能

#### 实时数据订阅
```python
# WebSocket实时数据
async for update in client.matches.subscribe(match_id="match_123"):
    print(f"📡 实时更新: {update}")

    if update.type == "goal":
        print(f"⚽ 进球! {update.team} {update.player} ({update.minute}')")
    elif update.type == "card":
        print(f"🟨/🟥 牌: {update.team} {update.player}")
    elif update.type == "score_change":
        print(f"📊 比分更新: {update.home_score} - {update.away_score}")
```

#### 数据分析
```python
# 获取预测统计
stats = await client.predictions.get_statistics(
    user_id="user_123",
    start_date="2025-11-01",
    end_date="2025-11-30"
)

print(f"总预测数: {stats.total_predictions}")
print(f"准确率: {stats.accuracy:.2%}")
print(f"最常预测的球队: {stats.most_predicted_teams}")

# 获取联赛信息
leagues = await client.leagues.list()
for league in leagues:
    print(f"联赛: {league.name}")
    print(f"赛季: {league.current_season}")
```

---

## 🌐 第一个API调用

### 使用curl

#### 1. 健康检查
```bash
curl -X GET "http://localhost:8000/health" \
  -H "Accept: application/json"
```

#### 2. 获取API信息
```bash
curl -X GET "http://localhost:8000/v1/info" \
  -H "Accept: application/json"
```

#### 3. 创建预测（无需认证）
```bash
curl -X POST "http://localhost:8000/v1/predictions/simple" \
  -H "Content-Type: application/json" \
  -d '{
    "match_id": "test_match_001",
    "home_team": "Manchester United",
    "away_team": "Liverpool",
    "match_date": "2025-11-15T20:00:00Z"
  }'
```

#### 4. 获取比赛列表
```bash
curl -X GET "http://localhost:8000/v1/matches?status=scheduled&limit=10" \
  -H "Accept: application/json"
```

### 使用Python requests

#### 1. 安装requests
```bash
pip install requests
```

#### 2. API调用示例
```python
import requests
import json

# API基础URL
BASE_URL = "http://localhost:8000/v1"

def create_prediction():
    """创建预测"""
    url = f"{BASE_URL}/predictions/simple"
    data = {
        "match_id": "test_match_001",
        "home_team": "Manchester United",
        "away_team": "Liverpool",
        "match_date": "2025-11-15T20:00:00Z"
    }

    response = requests.post(url, json=data)

    if response.status_code == 201:
        prediction = response.json()
        print(f"✅ 预测创建成功!")
        print(f"预测ID: {prediction['prediction_id']}")
        print(f"预测结果: {prediction['predicted_winner']}")
        print(f"置信度: {prediction['confidence']:.2%}")
    else:
        print(f"❌ 预测创建失败: {response.status_code}")
        print(f"错误信息: {response.text}")

def get_matches():
    """获取比赛列表"""
    url = f"{BASE_URL}/matches"
    params = {
        "status": "scheduled",
        "limit": 5
    }

    response = requests.get(url, params=params)

    if response.status_code == 200:
        matches = response.json()
        print(f"✅ 获取到 {len(matches)} 场比赛")

        for match in matches:
            print(f"\n📅 {match['home_team']} vs {match['away_team']}")
            print(f"⏰ 时间: {match['match_date']}")
            print(f"🏆 联赛: {match['league']}")
    else:
        print(f"❌ 获取比赛失败: {response.status_code}")

# 运行示例
if __name__ == "__main__":
    print("🚀 开始API调用示例...")

    # 创建预测
    create_prediction()

    # 获取比赛列表
    get_matches()
```

### 使用JavaScript

```javascript
// 使用fetch API
const BASE_URL = 'http://localhost:8000/v1';

async function createPrediction() {
    try {
        const response = await fetch(`${BASE_URL}/predictions/simple`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                match_id: 'test_match_001',
                home_team: 'Manchester United',
                away_team: 'Liverpool',
                match_date: '2025-11-15T20:00:00Z'
            })
        });

        if (response.ok) {
            const prediction = await response.json();
            console.log('✅ 预测创建成功!');
            console.log('预测结果:', prediction.predicted_winner);
            console.log('置信度:', (prediction.confidence * 100).toFixed(2) + '%');
        } else {
            console.error('❌ 预测创建失败:', response.status);
        }
    } catch (error) {
        console.error('❌ 请求错误:', error);
    }
}

async function getMatches() {
    try {
        const response = await fetch(`${BASE_URL}/matches?status=scheduled&limit=5`);

        if (response.ok) {
            const matches = await response.json();
            console.log(`✅ 获取到 ${matches.length} 场比赛`);

            matches.forEach(match => {
                console.log(`\n📅 ${match.home_team} vs ${match.away_team}`);
                console.log(`⏰ 时间: ${match.match_date}`);
                console.log(`🏆 联赛: ${match.league}`);
            });
        } else {
            console.error('❌ 获取比赛失败:', response.status);
        }
    } catch (error) {
        console.error('❌ 请求错误:', error);
    }
}

// 运行示例
console.log('🚀 开始API调用示例...');
createPrediction();
getMatches();
```

---

## ❓ 常见问题

### 安装问题

#### Q: Python版本不兼容
```bash
# 检查Python版本
python --version

# 使用正确的Python版本
python3.11 -m venv venv
source venv/bin/activate
```

#### Q: 依赖安装失败
```bash
# 更新pip
pip install --upgrade pip

# 使用国内镜像
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple/
```

#### Q: Docker启动失败
```bash
# 检查Docker状态
docker --version
docker-compose --version

# 重启Docker服务
sudo systemctl restart docker
```

### 运行问题

#### Q: 数据库连接失败
```bash
# 检查数据库服务状态
docker-compose ps

# 查看数据库日志
docker-compose logs postgres

# 重启数据库服务
docker-compose restart postgres
```

#### Q: API服务器无法启动
```bash
# 检查端口占用
lsof -i :8000

# 使用不同端口
uvicorn src.main:app --port 8001

# 查看详细错误
uvicorn src.main:app --log-level debug
```

#### Q: 测试失败
```bash
# 更新测试依赖
pip install pytest pytest-asyncio

# 运行特定测试
pytest tests/unit/test_health.py -v

# 跳过慢速测试
pytest -m "not slow"
```

### API问题

#### Q: 认证失败
```python
# 检查API密钥
client = FootballPredictionClient(
    api_key="your_actual_api_key",  # 确保密钥正确
    base_url="https://api.football-prediction.com/v1"
)

# 验证认证状态
auth_status = await client.auth.verify()
print(f"认证状态: {auth_status}")
```

#### Q: 请求频率限制
```python
# 使用自动重试
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(1))
async def create_prediction_with_retry(data):
    return await client.predictions.create(data)
```

#### Q: 数据验证错误
```python
# 检查数据格式
from football_prediction_sdk.models import PredictionRequest

try:
    request = PredictionRequest(**data)
    print("✅ 数据验证通过")
except ValidationError as e:
    print(f"❌ 数据验证失败: {e}")
```

### 性能问题

#### Q: 响应速度慢
```bash
# 检查系统资源
htop
df -h

# 查看API性能指标
curl http://localhost:8000/metrics
```

#### Q: 内存使用过高
```bash
# 检查内存使用
docker stats

# 重启服务
docker-compose restart app
```

### 开发问题

#### Q: 代码质量检查失败
```bash
# 自动修复格式问题
make fix-code

# 手动运行检查
ruff check src/ --fix
ruff format src/
ruff check src/
```

#### Q: 类型检查错误
```bash
# 更新类型存根
pip install types-requests

# 排除特定文件
mypy src/ --ignore-missing-imports
```

---

## 📞 获取帮助

### 📚 更多资源
- **完整文档**: https://docs.football-prediction.com
- **API参考**: https://docs.football-prediction.com/api
- **SDK文档**: https://docs.football-prediction.com/sdk
- **示例代码**: https://github.com/your-org/football-prediction-examples

### 💬 社区支持
- **GitHub Issues**: 报告bug和功能请求
- **Discord**: 实时聊天和技术支持
- **Stack Overflow**: 技术问题解答

### 📧 联系我们
- **技术支持**: support@football-prediction.com
- **商务合作**: business@football-prediction.com

---

## 🎯 下一步

恭喜！你已经成功设置了Football Prediction System。接下来可以：

1. **探索更多功能**: 阅读[开发者指南](DEVELOPER_GUIDE.md)
2. **部署生产环境**: 参考[部署文档](DEPLOYMENT.md)
3. **贡献代码**: 查看[贡献指南](CONTRIBUTING.md)
4. **监控性能**: 设置监控和告警

---

**快速开始指南版本**: v1.0.0
**最后更新**: 2025-11-10
**适用于**: Football Prediction System v1.0+

祝您使用愉快！🎉
