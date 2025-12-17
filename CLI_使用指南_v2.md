# ⚽ FootballPrediction v2.0 CLI 使用指南

## 🎯 工具概述

FootballPrediction v2.0 提供了两个主要的命令行工具：

1. **`predict_match_v2.py`** - v2.0 主要预测工具，基于新架构
2. **`docker-manager.sh`** - Docker 管理工具，一键部署和管理

## 🚀 快速开始

### 📋 环境准备

```bash
# 选项1: 使用 Docker (推荐)
./scripts/docker-manager.sh dev

# 选项2: 本地开发
make install
make dev
```

### 🎯 预测比赛 (v2.0)

```bash
# 基本预测
python scripts/predict_match_v2.py --home "Manchester United" --away "Arsenal"

# 批量预测
python scripts/predict_match_v2.py --batch matches.json

# 使用特定模型
python scripts/predict_match_v2.py --home "Chelsea" --away "Liverpool" --model xgboost_v2
```

---

## 📊 主要预测工具 (v2.0)

### 🎯 predict_match_v2.py

#### 基本语法
```bash
python scripts/predict_match_v2.py [OPTIONS]
```

#### 必需参数
- `--home` / `-H`: 主队名称
- `--away` / `-A`: 客队名称

#### 可选参数
- `--model` / `-m`: 指定使用的模型 (默认: xgboost_v2)
- `--date` / `-d`: 比赛日期 (格式: YYYY-MM-DD)
- `--batch` / `-b`: 批量预测模式，指定 JSON 文件
- `--verbose` / `-v`: 显示详细输出
- `--format` / `-f`: 输出格式 (json, table, simple)
- `--save` / `-s`: 保存结果到文件

#### 📝 使用示例

##### 1. 基础预测
```bash
# 曼联联 vs 阿森纳
python scripts/predict_match_v2.py --home "Manchester United" --away "Arsenal"

# 输出示例
🏟️  比赛: Manchester United vs Arsenal
📅  日期: 2024-01-15

📊 预测概率:
主胜 (HOME) : 65.2% |███████████████████████████████████░░░|
平局 (DRAW) : 22.1% |███████████████░░░░░░░░░░░░░░░░░|
客胜 (AWAY) : 12.7% |███████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░|

🎯 预测结果: HOME_WIN
💡 置信度: 65.2%
📈 模型版本: xgboost_v2
```

##### 2. 批量预测
```bash
# 创建批量预测文件
cat > matches.json << EOF
[
    {
        "home_team": "Manchester United",
        "away_team": "Arsenal",
        "match_date": "2024-01-15"
    },
    {
        "home_team": "Chelsea",
        "away_team": "Liverpool",
        "match_date": "2024-01-15"
    },
    {
        "home_team": "Barcelona",
        "away_team": "Real Madrid",
        "match_date": "2024-01-15"
    }
]
EOF

# 执行批量预测
python scripts/predict_match_v2.py --batch matches.json

# 输出 JSON 格式结果
python scripts/predict_match_v2.py --batch matches.json --format json --save results.json
```

##### 3. 使用不同模型
```bash
# 使用默认模型 (xgboost_v2)
python scripts/predict_match_v2.py --home "PSG" --away "Lyon"

# 指定特定模型
python scripts/predict_match_v2.py --home "PSG" --away "Lyon" --model xgboost_advanced

# 查看可用模型
python scripts/predict_match_v2.py --list-models
```

##### 4. 详细输出模式
```bash
# 显示详细预测过程
python scripts/predict_match_v2.py --home "Bayern" --away "Dortmund" --verbose

# 显示模型加载状态
python scripts/predict_match_v2.py --home "Bayern" --away "Dortmund" --verbose --model-info
```

##### 5. 结果保存
```bash
# 保存为 JSON 文件
python scripts/predict_match_v2.py --home "Juventus" --away "Inter Milan" --save prediction_result.json

# 保存为 CSV 文件
python scripts/predict_match_v2.py --batch matches.json --format csv --save predictions.csv
```

---

## 🐳 Docker 管理工具

### 🎮 docker-manager.sh

Docker 管理脚本提供了完整的容器生命周期管理功能。

#### 🔧 构建和部署

```bash
# 构建所有服务镜像
./scripts/docker-manager.sh build

# 启动生产环境
./scripts/docker-manager.sh up

# 启动开发环境 (包含热重载和调试)
./scripts/docker-manager.sh dev

# 启动开发环境 + 数据收集器
./scripts/docker-manager.sh dev --collectors
```

#### 📊 状态监控

```bash
# 查看所有服务状态
./scripts/docker-manager.sh status

# 查看服务健康状态
./scripts/docker-manager.sh health

# 查看应用日志
./scripts/docker-manager.sh logs

# 查看特定服务日志
./scripts/docker-manager.sh logs -f app
./scripts/docker-manager.sh logs -f db
./scripts/docker-manager.sh logs -f redis
```

#### 🧪 测试和质量检查

```bash
# 运行测试套件
./scripts/docker-manager.sh test

# 代码质量检查
./scripts/docker-manager.sh quality

# 安全扫描
./scripts/docker-manager.sh security
```

#### 🔄 服务管理

```bash
# 重启所有服务
./scripts/docker-manager.sh restart

# 重启特定服务
./scripts/docker-manager.sh restart app

# 停止所有服务
./scripts/docker-manager.sh down

# 清理未使用的资源
./scripts/docker-manager.sh clean

# 完全清理 (包括卷数据)
./scripts/docker-manager.sh clean --all
```

#### 🛠️ 开发工具

```bash
# 进入应用容器 shell
./scripts/docker-manager.sh shell

# 查看容器资源使用
./scripts/docker-manager.sh stats

# 执行健康检查
./scripts/docker-manager.sh exec python /app/healthcheck.py

# 在容器中执行命令
./scripts/docker-manager.sh exec python -c "import sys; print(sys.version)"
```

---

## 🔧 高级功能

### 📊 批量操作

#### 1. 批量预测文件格式

**JSON 格式**:
```json
{
  "matches": [
    {
      "home_team": "Manchester United",
      "away_team": "Arsenal",
      "match_date": "2024-01-15",
      "features": {
        "home_form": 3,
        "away_form": 1,
        "h2h_wins": 5
      }
    }
  ]
}
```

**CSV 格式**:
```csv
home_team,away_team,match_date
Manchester United,Arsenal,2024-01-15
Chelsea,Liverpool,2024-01-15
```

#### 2. 批量处理脚本

```bash
#!/bin/bash
# 批量预测示例脚本

# 创建比赛列表
cat > todays_matches.json << EOF
{
  "matches": [
    {"home_team": "Tottenham", "away_team": "West Ham"},
    {"home_team": "Everton", "away_team": "Liverpool"},
    {"home_team": "Newcastle", "away_team": "Aston Villa"},
    {"home_team": "Leicester", "away_team": "Wolverhampton"},
    {"home_team": "Crystal Palace", "away_team": "Southampton"}
  ]
}
EOF

# 执行批量预测
echo "🎯 开始批量预测..."
python scripts/predict_match_v2.py --batch todays_matches.json --format table --save todays_predictions.csv

# 显示结果摘要
echo "📊 预测完成！结果已保存到 todays_predictions.csv"
```

### 🔄 管道自动化

#### 1. 每日预测任务

```bash
#!/bin/bash
# daily_prediction.sh - 每日预测任务

# 日期
DATE=$(date +%Y-%m-%d)

# 创建当天比赛数据文件
cat > ${DATE}_matches.json << EOF
{
  "matches": [
    # 这里可以集成外部数据源
    {"home_team": "Team A", "away_team": "Team B", "match_date": "$DATE"},
    {"home_team": "Team C", "away_team": "Team D", "match_date": "$DATE"}
  ]
}
EOF

# 执行预测
python scripts/predict_match_v2.py --batch ${DATE}_matches.json --save ${DATE}_predictions.json

# 发送通知 (可选)
curl -X POST "https://hooks.slack.com/..." \
  -H 'Content-type: application/json' \
  -d "{\"text\":\"每日预测任务完成: $(date)\"}"
```

#### 2. 性能测试脚本

```bash
#!/bin/bash
# performance_test.sh - 性能测试脚本

echo "🚀 开始性能测试..."

# 记录开始时间
START_TIME=$(date +%s)

# 批量预测测试
python scripts/predict_match_v2.py --batch test_matches.json --format json --save test_results.json

# 记录结束时间
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

# 生成性能报告
cat > performance_report.md << EOF
# 性能测试报告

## 测试时间: $(date)
## 总耗时: ${DURATION} 秒
## 预测数量: $(jq '.matches | length' test_results.json)
## 平均耗时: $((DURATION / $(jq '.matches | length' test_results.json))) 秒/比赛

## 结果详情:
\`\`\`json
$(cat test_results.json)
\`\`\`
EOF

echo "📊 性能测试完成，报告已生成: performance_report.md"
```

### 🌐 API 集成

#### 1. 与外部系统集成

```python
#!/usr/bin/env python3
# api_integration.py - API 集成示例

import requests
import json

def predict_and_notify(match_data, webhook_url):
    """预测比赛并发送通知"""

    # 调用本地预测
    result = requests.post('http://localhost:8000/api/v1/predictions', json=match_data)

    if result.status_code == 200:
        prediction = result.json()

        # 发送到外部系统
        notification = {
            "match": match_data,
            "prediction": prediction,
            "timestamp": datetime.now().isoformat()
        }

        requests.post(webhook_url, json=notification)
        return True

    return False

# 使用示例
match_data = {
    "home_team": "Manchester United",
    "away_team": "Arsenal",
    "match_date": "2024-01-15"
}

webhook_url = "https://your-webhook-url.com/predictions"

success = predict_and_notify(match_data, webhook_url)
print(f"预测和通知: {'成功' if success else '失败'}")
```

---

## 🔧 配置和自定义

### ⚙️ 环境变量配置

#### 预测工具配置
```bash
# 模型配置
export DEFAULT_MODEL="xgboost_v2"
export MODEL_PATH="/app/data/models"

# 输出配置
export PREDICTION_OUTPUT_FORMAT="table"
export PREDICTION_SAVE_PATH="/app/data/predictions"

# API 配置
export API_BASE_URL="http://localhost:8000"
export API_TIMEOUT=30
```

#### Docker 环境配置
```bash
# 服务配置
export INFERENCE_SERVICE_V2_ENABLED=true
export COLLECTION_SERVICE_ENABLED=true
export EXPLAINABILITY_SERVICE_ENABLED=true

# 数据库配置
export DB_HOST=localhost
export DB_PORT=5432
export DB_NAME=football_prediction

# 模型配置
export MODEL_PATH=/app/data/models
export DEFAULT_MODEL_NAME=xgboost_v2
```

### 📁 自定义模型

#### 添加自定义模型
```bash
# 1. 训练模型
python scripts/train_model.py --model-type advanced --data training_data.csv

# 2. 保存模型
cp advanced_model.pkl /app/data/models/xgboost_advanced.pkl

# 3. 使用自定义模型
python scripts/predict_match_v2.py --home "Team A" --away "Team B" --model xgboost_advanced
```

---

## 🔍 故障排除

### ❌ 常见问题

#### 1. 模型加载失败
```bash
# 错误: Model not found
# 解决方案:
./scripts/docker-manager.sh health  # 检查模型加载状态
./scripts/docker-manager.sh logs   # 查看日志

# 或手动检查模型文件
ls -la /app/data/models/
```

#### 2. 数据库连接失败
```bash
# 错误: Database connection failed
# 解决方案:
./scripts/docker-manager.sh health  # 健康检查
./scripts/docker-manager.sh restart db  # 重启数据库

# 或检查数据库配置
docker exec -it footballprediction-db psql -U football_user -d football_prediction_dev -c "\l"
```

#### 3. 预测结果异常
```bash
# 错误: Prediction failed
# 解决方案:
python scripts/predict_match_v2.py --verbose  # 查看详细日志
python scripts/predict_match_v2.py --model-info  # 查看模型信息

# 使用测试模式
python scripts/predict_match_v2.py --home "Test" --away "Team" --debug
```

### 🛠️ 调试模式

#### 详细日志模式
```bash
# 启用详细日志
export LOG_LEVEL=DEBUG
python scripts/predict_match_v2.py --home "Team A" --away "Team B" --verbose
```

#### 模型验证
```bash
# 验证模型文件
python -c "
import pickle
import sys
try:
    model = pickle.load(open('/app/data/models/xgboost_v2.pkl', 'rb'))
    print(f'✅ 模型加载成功: {type(model)}')
    print(f'📊 模型属性: {dir(model)}')
except Exception as e:
    print(f'❌ 模型加载失败: {e}')
    sys.exit(1)
"
```

#### 连接测试
```bash
# 测试 API 连接
curl -f http://localhost:8000/health

# 测试预测 API
curl -X POST http://localhost:8000/api/v1/predictions \
  -H "Content-Type: application/json" \
  -d '{"home_team": "Test", "away_team": "Team"}'
```

---

## 📚 更多资源

### 📖 相关文档
- **主文档**: [README.md](./README.md)
- **API 文档**: http://localhost:8000/docs (启动服务后访问)
- **架构文档**: [src/](./src/) 详细代码注释
- **发布说明**: [RELEASE_NOTES.md](./RELEASE_NOTES.md)

### 🔗 有用链接
- **项目仓库**: https://github.com/xupeng211/FootballPrediction
- **Docker Hub**: https://hub.docker.com/r/footballprediction
- **问题反馈**: https://github.com/xupeng211/FootballPrediction/issues

### 💬 获取帮助

```bash
# 查看工具帮助
python scripts/predict_match_v2.py --help
./scripts/docker-manager.sh --help

# 查看版本信息
python scripts/predict_match_v2.py --version
./scripts/docker-manager.sh version
```

---

**🎉 FootballPrediction v2.0 CLI 工具，让足球预测更简单、更强大！**

*最后更新: 2024-01-15*
*版本: v2.0.0-Stable*