# Staging 环境验证指南

## 概述

本文档定义了 FootballPrediction 系统在 Staging 环境中的部署、验证和监控流程，确保生产上线前的充分验证。

## 🚀 Staging 环境部署

### 1. 环境配置

#### 基础设施要求
- **计算资源**: 至少 2 CPU 核心，4GB RAM
- **存储**: 20GB 可用磁盘空间
- **网络**: 支持外网访问用于 API 数据获取
- **容器运行时**: Docker 20.10+ 和 Docker Compose 2.0+

#### 环境变量配置
```bash
# 复制并配置 Staging 环境变量
cp env.template .env.staging

# 关键配置项
ENVIRONMENT=staging
DB_HOST=staging-db.example.com
DB_NAME=football_prediction_staging
REDIS_URL=redis://staging-redis:6379/0
API_SPORTS_KEY=${STAGING_API_KEY}
LOG_LEVEL=info
```

### 2. 部署步骤

#### 方式 1：Docker Compose 部署
```bash
# 1. 克隆代码到 Staging 服务器
git clone https://github.com/xupeng211/FootballPrediction.git
cd FootballPrediction

# 2. 切换到指定版本/分支
git checkout main  # 或指定的 tag/commit

# 3. 配置环境变量
source .env.staging

# 4. 启动服务
docker-compose -f docker-compose.yml -f docker-compose.staging.yml up -d

# 5. 初始化数据库
docker-compose exec web python -m alembic upgrade head

# 6. 验证服务状态
docker-compose ps
curl -f http://localhost:8000/health
```

#### 方式 2：K8s 部署（如适用）
```bash
# 1. 应用 Kubernetes 配置
kubectl apply -f k8s/staging/

# 2. 等待 Pod 就绪
kubectl rollout status deployment/football-prediction-staging

# 3. 验证服务
kubectl port-forward svc/football-prediction-staging 8000:8000
curl -f http://localhost:8000/health
```

## 📊 72小时验证周期

### 第一阶段：部署验证（0-2小时）

#### 1.1 服务启动检查
- [ ] 所有容器/Pod 正常启动
- [ ] 数据库连接成功
- [ ] Redis 缓存可用
- [ ] API 健康检查通过
- [ ] 日志正常输出

#### 1.2 基础功能测试
```bash
# API 端点测试
curl -X GET "http://staging.example.com/api/v1/health"
curl -X GET "http://staging.example.com/api/v1/matches/today"
curl -X POST "http://staging.example.com/api/v1/predictions" \
  -H "Content-Type: application/json" \
  -d '{"home_team_id": 1, "away_team_id": 2}'

# 数据库查询测试
docker-compose exec db psql -U football_user -d football_prediction_staging \
  -c "SELECT COUNT(*) FROM matches WHERE created_at > NOW() - INTERVAL '24 HOURS';"
```

### 第二阶段：功能验证（2-24小时）

#### 2.1 数据采集验证
- [ ] 自动数据采集任务正常运行
- [ ] API 数据源连接稳定
- [ ] 数据入库正常，无格式错误
- [ ] 数据质量检查通过

#### 2.2 预测模型验证
- [ ] 模型加载和推理正常
- [ ] 预测 API 响应时间 < 2秒
- [ ] 预测结果格式正确
- [ ] 特征计算无异常

#### 2.3 监控指标验证
```bash
# 检查关键指标
curl -s "http://staging.example.com/metrics" | grep -E "(response_time|error_rate|prediction_count)"

# 查看应用日志
docker-compose logs --tail=100 web | grep -E "(ERROR|WARN)"
```

### 第三阶段：稳定性验证（24-72小时）

#### 3.1 性能压力测试
```bash
# 使用 wrk 进行负载测试
wrk -t4 -c100 -d30s --script=scripts/load_test.lua http://staging.example.com/api/v1/health

# 数据库连接池测试
docker-compose exec web python -c "
from src.database.connection import DatabaseManager
import asyncio

async def test_connections():
    for i in range(50):
        db = DatabaseManager()
        result = await db.execute_query('SELECT 1')
        print(f'Connection {i}: OK')

asyncio.run(test_connections())
"
```

#### 3.2 故障恢复测试
- [ ] 数据库重启恢复测试
- [ ] Redis 重启恢复测试
- [ ] 应用进程重启测试
- [ ] 网络中断恢复测试

#### 3.3 数据一致性检查
```sql
-- 检查数据一致性
SELECT
    COUNT(*) as total_matches,
    COUNT(CASE WHEN status = 'finished' THEN 1 END) as finished_matches,
    AVG(CASE WHEN predictions.confidence > 0.7 THEN 1.0 ELSE 0.0 END) as high_confidence_rate
FROM matches
LEFT JOIN predictions ON matches.id = predictions.match_id
WHERE matches.created_at > NOW() - INTERVAL '72 HOURS';
```

## 🔍 监控指标收集

### 系统指标
```bash
# CPU 使用率
docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}"

# 磁盘使用率
df -h

# 网络连接数
netstat -an | grep :8000 | wc -l
```

### 应用指标
- **响应时间**: P95 < 1s, P99 < 3s
- **错误率**: < 1%
- **数据库连接**: 池利用率 < 80%
- **缓存命中率**: > 85%
- **预测准确率**: > 60%（历史基准）

### 业务指标
- **每日预测数量**: > 50
- **数据采集成功率**: > 95%
- **用户 API 调用**: 记录访问模式
- **特征计算延迟**: < 500ms

## 📋 验证检查清单

### P0 验证项（必须通过）
- [ ] 所有 API 端点返回正确响应
- [ ] 数据库读写正常
- [ ] 预测模型正常运行
- [ ] 日志无严重错误
- [ ] 72小时运行无宕机

### P1 验证项（推荐通过）
- [ ] 性能指标达到预期
- [ ] 缓存系统正常工作
- [ ] 监控告警配置生效
- [ ] 数据质量检查通过
- [ ] 自动化任务正常执行

### P2 验证项（可选验证）
- [ ] 负载测试通过
- [ ] 故障恢复测试通过
- [ ] 安全扫描无高危问题
- [ ] 兼容性测试通过

## 📁 验证报告存档

### 报告目录结构
```
reports/staging/
├── YYYY-MM-DD_deployment_report.md
├── YYYY-MM-DD_performance_metrics.json
├── YYYY-MM-DD_error_logs.txt
├── YYYY-MM-DD_test_results.xml
└── screenshots/
    ├── monitoring_dashboard.png
    ├── api_response_times.png
    └── error_rate_chart.png
```

### 报告模板
```markdown
# Staging 验证报告 - YYYY-MM-DD

## 部署信息
- **版本**: git-commit-hash
- **部署时间**: YYYY-MM-DD HH:MM:SS
- **验证人员**: 姓名
- **验证周期**: 72小时

## 验证结果
- **P0 项目**: X/X 通过
- **P1 项目**: X/X 通过
- **P2 项目**: X/X 通过

## 关键指标
- **平均响应时间**: Xms
- **错误率**: X%
- **可用性**: XX.XX%

## 发现问题
1. 问题描述 - 影响等级 - 状态
2. ...

## 推荐措施
1. 建议内容
2. ...

## 上线建议
[ ] 推荐上线
[ ] 需要修复后上线
[ ] 不推荐上线

## 附件
- 性能报告: performance_metrics.json
- 错误日志: error_logs.txt
- 测试结果: test_results.xml
```

## 🚨 问题升级流程

### 问题等级定义
- **P0 - 致命**: 系统无法启动或核心功能完全不可用
- **P1 - 严重**: 核心功能受影响，但系统可用
- **P2 - 一般**: 非核心功能异常或性能问题
- **P3 - 轻微**: 界面问题或优化建议

### 升级联系方式
- **P0/P1**: 立即通知技术负责人
- **P2**: 24小时内提交问题报告
- **P3**: 周报中汇总报告

## 🔧 常见问题排查

### 服务启动失败
```bash
# 检查容器状态
docker-compose ps

# 查看错误日志
docker-compose logs web

# 检查端口占用
netstat -tlnp | grep :8000

# 检查环境变量
docker-compose exec web env | grep -E "(DB_|REDIS_|API_)"
```

### 数据库连接问题
```bash
# 测试数据库连接
docker-compose exec db psql -U football_user -d football_prediction_staging -c "SELECT 1;"

# 检查连接池状态
docker-compose exec web python -c "
from src.database.connection import DatabaseManager
print(DatabaseManager().get_pool_status())
"
```

### API 响应异常
```bash
# 检查API健康状态
curl -v "http://staging.example.com/health"

# 检查应用日志
docker-compose logs --tail=50 web | grep -i error

# 验证模型加载
curl -X POST "http://staging.example.com/api/v1/models/test" \
  -H "Content-Type: application/json" \
  -d '{"test": true}'
```

## 📞 支持联系

- **技术支持**: tech-support@example.com
- **紧急热线**: +86-xxx-xxxx-xxxx
- **文档更新**: 提交 PR 到 docs/STAGING_VALIDATION.md

---

**注意**: 本文档应根据实际部署环境和业务需求进行调整。建议每季度审查并更新验证流程。