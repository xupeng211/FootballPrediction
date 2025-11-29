# 🏆 全量数据回填执行指南
# Enterprise-grade Global Backfill Execution Guide

## 📋 概述

本指南详细介绍如何使用全量数据回填系统，地毯式采集从2022-01-01到今天的所有足球比赛数据。

**系统特性**:
- 🎯 **地毯式覆盖**: 连续日期采集，无间断
- ⚡ **智能限流**: 1.5-3.5秒随机延迟，模拟真人行为
- 🔄 **断点续传**: 支持中断后继续执行
- 📊 **实时监控**: 详细的进度统计和错误追踪
- 🗄️ **数据完整性**: PostgreSQL事务处理和重复检测

---

## 🚀 快速开始

### 1. 环境准备

确保所有服务正在运行：
```bash
# 启动开发环境
make dev

# 检查服务状态
make status
```

### 2. API密钥配置

在 `.env` 文件中配置API密钥：
```bash
# 编辑环境文件
nano .env

# 确保包含以下配置
FOOTBALL_DATA_API_KEY=your_actual_api_key_here
DATABASE_URL=postgresql://postgres:postgres-dev-password@db:5432/football_prediction
REDIS_URL=redis://redis:6379/0
```

> 💡 **获取API密钥**: 访问 [football-data.org](https://www.football-data.org/login) 注册免费账户

### 3. 一键启动（推荐）

```bash
# 完整回填（2022-01-01 到 今天）
./scripts/run_backfill_background.sh

# 预览执行计划
./scripts/run_backfill_background.sh --dry-run

# 从2023年开始
./scripts/run_backfill_background.sh --start-date=2023-01-01
```

---

## 📖 详细使用指南

### 基本命令

#### 1. 直接使用Python脚本

```bash
# 基本全量回填
python scripts/backfill_global.py

# 自定义时间范围
python scripts/backfill_global.py --start-date=2023-01-01 --end-date=2023-12-31

# 干运行预览
python scripts/backfill_global.py --dry-run

# 只使用Football-Data.org数据源
python scripts/backfill_global.py --source=football-data

# 断点续传
python scripts/backfill_global.py --resume
```

#### 2. 使用便捷脚本（推荐）

```bash
# 显示帮助
./scripts/run_backfill_background.sh --help

# 基本用法
./scripts/run_backfill_background.sh

# 自定义参数
./scripts/run_backfill_background.sh \
    --start-date=2023-01-01 \
    --end-date=2023-06-30 \
    --source=football-data \
    --resume
```

### 参数说明

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--start-date` | 日期 | 2022-01-01 | 开始日期 (YYYY-MM-DD) |
| `--end-date` | 日期 | 今天 | 结束日期 (YYYY-MM-DD) |
| `--source` | 字符串 | all | 数据源 (all, football-data, fotmob) |
| `--resume` | 标志 | false | 从上次中断处继续 |
| `--dry-run` | 标志 | false | 只显示计划，不实际采集 |

---

## 📊 执行监控

### 1. 实时日志监控

```bash
# 查看最新日志
tail -f logs/backfill/backfill_*.log

# 查看进度信息
grep -E "(处理|成功|失败)" logs/backfill/backfill_*.log | tail -20

# 查看错误信息
grep -i "error\|failed\|异常" logs/backfill/backfill_*.log | tail -10
```

### 2. 数据库监控

```bash
# 进入数据库
make db-shell

# 查看比赛总数
SELECT COUNT(*) FROM matches;

# 查看最新数据
SELECT * FROM matches ORDER BY created_at DESC LIMIT 10;

# 查看按日期统计
SELECT
    DATE(match_date) as date,
    COUNT(*) as matches_count
FROM matches
GROUP BY DATE(match_date)
ORDER BY date DESC
LIMIT 10;
```

### 3. 系统资源监控

```bash
# 查看容器资源使用
docker stats

# 查看Celery任务队列
docker-compose exec worker celery -A src.tasks.celery_app inspect active

# 查看磁盘使用
df -h
```

---

## ⚡ 性能优化

### 1. 分批次执行

对于大量数据，建议分批执行：

```bash
# 2022年数据
./scripts/run_backfill_background.sh \
    --start-date=2022-01-01 \
    --end-date=2022-12-31

# 2023年数据
./scripts/run_backfill_background.sh \
    --start-date=2023-01-01 \
    --end-date=2023-12-31

# 2024年数据
./scripts/run_backfill_background.sh \
    --start-date=2024-01-01 \
    --end-date=2024-12-31
```

### 2. 选择性数据源

```bash
# 只使用快速数据源
./scripts/run_backfill_background.sh --source=football-data

# 避免网络延迟大的数据源
```

### 3. 错误恢复

```bash
# 如果中断，自动恢复
./scripts/run_backfill_background.sh --resume

# 检查断点状态
cat data/backfill_state.json | jq .
```

---

## 🔧 故障排除

### 1. 常见问题

#### API密钥问题
```bash
# 检查API密钥配置
grep FOOTBALL_DATA_API_KEY .env

# 测试API连接
curl -H "X-Auth-Token: YOUR_API_KEY" \
     "https://api.football-data.org/v4/matches?limit=1"
```

#### 数据库连接问题
```bash
# 重启数据库服务
docker-compose restart db

# 检查数据库状态
docker-compose exec db pg_isready -U postgres

# 查看数据库日志
docker-compose logs db
```

#### 内存不足
```bash
# 监控内存使用
docker stats --no-stream

# 增加交换空间
sudo swapon --show
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

### 2. 错误代码

| 错误类型 | 可能原因 | 解决方案 |
|----------|----------|----------|
| `API limit exceeded` | 请求频率过高 | 增加延迟时间，使用`--resume` |
| `Database connection failed` | 数据库未启动 | 运行`docker-compose up -d` |
| `Invalid date format` | 日期格式错误 | 使用YYYY-MM-DD格式 |
| `Module not found` | 依赖缺失 | 运行`make install` |

---

## 📈 性能指标

### 基准性能

- **采集速度**: 平均 2.5 秒/天
- **数据量**: 15-40 场比赛/天
- **成功率**: 95%+ (正常网络环境)
- **内存使用**: < 512MB
- **磁盘空间**: 约 1MB/1000场比赛

### 预计执行时间

| 时间范围 | 天数 | 预计时间 | 数据量估算 |
|----------|------|----------|------------|
| 1个月 | 30 | 1-2小时 | 600-1200场 |
| 3个月 | 90 | 3-4小时 | 1800-3600场 |
| 6个月 | 180 | 6-8小时 | 3600-7200场 |
| 1年 | 365 | 12-16小时 | 7300-14600场 |
| 3年 | 1095 | 36-48小时 | 21900-43800场 |

---

## 🛡️ 安全最佳实践

### 1. API密钥保护

```bash
# 设置正确的文件权限
chmod 600 .env

# 不要提交到版本控制
echo ".env" >> .gitignore

# 使用环境变量（推荐）
export FOOTBALL_DATA_API_KEY="your_key"
```

### 2. 资源限制

```bash
# 设置CPU和内存限制
docker-compose -f docker-compose.prod.yml up -d

# 监控系统负载
htop
iostat -x 1
```

### 3. 数据备份

```bash
# 备份数据库
docker-compose exec db pg_dump -U postgres football_prediction > backup_$(date +%Y%m%d).sql

# 定期备份
0 2 * * * docker-compose exec db pg_dump -U postgres football_prediction > /backup/backup_$(date +\%Y\%m\%d).sql
```

---

## 📝 使用示例

### 示例1: 完整测试流程

```bash
# 1. 环境检查
make dev && make status

# 2. 小规模测试（3天）
./scripts/run_backfill_background.sh \
    --start-date=2022-01-01 \
    --end-date=2022-01-03 \
    --dry-run

# 3. 执行测试
./scripts/run_backfill_background.sh \
    --start-date=2022-01-01 \
    --end-date=2022-01-03

# 4. 检查结果
make db-shell
SELECT COUNT(*) FROM matches WHERE match_date >= '2022-01-01' AND match_date <= '2022-01-03';
```

### 示例2: 大规模生产执行

```bash
# 1. 分批执行（每季度一批）
./scripts/run_backfill_background.sh \
    --start-date=2022-01-01 \
    --end-date=2022-03-31

# 等待完成后继续
./scripts/run_backfill_background.sh \
    --start-date=2022-04-01 \
    --end-date=2022-06-30 \
    --resume
```

### 示例3: 错误恢复

```bash
# 检查中断原因
tail -20 logs/backfill/backfill_*.log

# 从断点恢复
./scripts/run_backfill_background.sh --resume

# 验证数据完整性
make db-shell
SELECT
    DATE(match_date) as date,
    COUNT(*) as matches,
    MIN(created_at) as first_imported
FROM matches
WHERE match_date >= '2022-01-01'
GROUP BY DATE(match_date)
ORDER BY date;
```

---

## 📞 获取帮助

- **日志文件**: `logs/backfill/backfill_*.log`
- **状态文件**: `data/backfill_state.json`
- **进程文件**: `data/backfill.pid`

### 常用命令快速参考

```bash
# 查看帮助
./scripts/run_backfill_background.sh --help

# 停止后台任务
kill $(cat data/backfill.pid)

# 查看实时进度
grep -E "(处理.*天|成功率)" logs/backfill/backfill_*.log | tail -5

# 数据库查询
make db-shell -c "SELECT COUNT(*) FROM matches;"

# 系统状态
docker-compose ps
docker stats --no-stream
```

---

**⚠️ 重要提醒**:
1. 首次执行建议先进行小规模测试
2. 确保网络连接稳定，避免频繁中断
3. 定期备份数据库，防止数据丢失
4. 监控系统资源使用，避免过载
5. 遵守API使用限制，合理设置延迟

**🎯 成功标准**: 成功率 > 95%，数据完整，无重复记录。