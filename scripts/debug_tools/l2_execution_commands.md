# L2批处理作业执行命令指南

## 🚀 推荐执行策略

### 阶段1: 试运行 (1000场比赛)
```bash
# 启动试运行 - 前1000场比赛
docker-compose run -d --name l2-batch-test \
  --restart unless-stopped \
  -e ENV=production \
  -e LOG_LEVEL=INFO \
  -e PYTHONPATH=/app/src \
  app python run_l2_batch_production.py \
    --max-matches 1000 \
    --monitor \
    --monitor-interval 30
```

### 阶段2: 分批次处理 (每批2000场)
```bash
# 批次1: 比赛 1-2000
docker-compose run -d --name l2-batch-1 \
  --restart unless-stopped \
  -e ENV=production \
  -e LOG_LEVEL=INFO \
  -e PYTHONPATH=/app/src \
  app python run_l2_batch_production.py \
    --max-matches 2000 \
    --monitor \
    --monitor-interval 60

# 批次2: 比赛 2001-4000 (在批次1完成后运行)
docker-compose run -d --name l2-batch-2 \
  --restart unless-stopped \
  -e ENV=production \
  -e LOG_LEVEL=INFO \
  -e PYTHONPATH=/app/src \
  app python run_l2_batch_production.py \
    --max-matches 2000 \
    --monitor \
    --monitor-interval 60
```

### 阶段3: 全量处理
```bash
# 处理剩余所有比赛
docker-compose run -d --name l2-batch-remaining \
  --restart unless-stopped \
  -e ENV=production \
  -e LOG_LEVEL=INFO \
  -e PYTHONPATH=/app/src \
  app python run_l2_batch_production.py \
    --monitor \
    --monitor-interval 120
```

## 📊 监控命令

### 实时日志监控
```bash
# 监控特定批次
docker-compose logs -f l2-batch-test

# 监控所有L2相关容器
docker-compose logs -f | grep l2-batch
```

### 进度查询
```bash
# 数据库进度查询
docker-compose exec db psql -U postgres -d football_prediction -c "
SELECT
  COUNT(*) as total,
  COUNT(CASE WHEN data_completeness = 'complete' THEN 1 END) as completed,
  COUNT(CASE WHEN data_completeness = 'partial' THEN 1 END) as pending,
  ROUND(COUNT(CASE WHEN data_completeness = 'complete' THEN 1 END) * 100.0 / COUNT(*), 2) as completion_rate
FROM matches
WHERE fotmob_id IS NOT NULL;"

# 数据质量检查
docker-compose exec db psql -U postgres -d football_prediction -c "
SELECT
  COUNT(*) as matches_with_xg
FROM matches
WHERE fotmob_id IS NOT NULL
  AND data_completeness = 'complete'
  AND home_xg IS NOT NULL
  AND away_xg IS NOT NULL;"
```

## ⚡ 性能调优

### 速率限制配置
- 并发数: 8 (保守设置，避免封禁)
- 基础延迟: 2.5秒
- 随机抖动: ±20%

### 预估执行时间
- 总比赛数: 11,526场
- 预估速度: ~15-20场/分钟
- 预估总时间: ~10-12小时

## 🛡️ 安全特性

1. **自动重试**: 最多3次重试
2. **速率限制**: 内置令牌桶算法
3. **错误处理**: 单场比赛失败不影响整体
4. **进度保存**: 每50场比赛保存进度
5. **监控报告**: 每30-60秒报告进度

## 🚨 故障处理

### 检查作业状态
```bash
# 查看容器状态
docker-compose ps | grep l2-batch

# 查看容器资源使用
docker stats l2-batch-test
```

### 重启失败的作业
```bash
# 停止现有容器
docker-compose stop l2-batch-test
docker-compose rm -f l2-batch-test

# 重新启动
docker-compose run -d --name l2-batch-test-restart \
  --restart unless-stopped \
  -e ENV=production \
  app python run_l2_batch_production.py --max-matches 1000
```