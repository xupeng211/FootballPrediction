# 🤖 FootballPrediction 24小时自动化实战指南

FootballPrediction v2.3.0-production 工业级自动化系统

## 📖 概述

24小时自动化实战系统是FootballPrediction的核心功能，提供完全自动化的预测生成、系统监控和报告管理。支持多种运行模式，满足不同场景的需求。

## 🚀 快速开始

### 基础使用

```bash
# 默认启动24小时自动化（内部循环模式）
./scripts/start_24h_automation.sh

# 影子测试模式（48小时）
./scripts/start_24h_automation.sh -m shadow_test -d 48

# Crontab任务模式（7天连续运行）
./scripts/start_24h_automation.sh -m crontab -d 168
```

### Docker环境使用

```bash
# Docker环境启动
./scripts/start_24h_automation.sh --docker -m internal_loop

# Docker影子测试
./scripts/start_24h_automation.sh --docker -m shadow_test --env-file .env.shadow
```

## 🔧 运行模式详解

### 1. 内部循环模式 (internal_loop)

**特点**: 单进程内定时执行，适合开发测试
```bash
# 30分钟间隔，运行12小时
./scripts/start_24h_automation.sh -m internal_loop -i 30 -d 12
```

**优势**:
- 简单易用，无需额外配置
- 实时日志输出
- 资源占用低
- 支持优雅停止

### 2. Crontab任务模式 (crontab)

**特点**: 系统级定时任务，适合生产环境
```bash
# 设置crontab，每10分钟执行一次
./scripts/start_24h_automation.sh -m crontab -i 10
```

**自动化任务**:
- 预测执行: 每10分钟执行预测
- 健康检查: 每小时系统检查
- 日报生成: 每日自动报告

**优势**:
- 系统级可靠性
- 进程隔离
- 自动重启
- 历史记录保存

### 3. 影子测试模式 (shadow_test)

**特点**: 集成现有影子测试系统，验证预测准确性
```bash
# 48小时影子测试，15分钟间隔
./scripts/start_24h_automation.sh -m shadow_test -d 48
```

**功能**:
- Brier Score计算
- 预测准确性评估
- 性能监控
- 盈亏模拟分析

## 📊 监控和日志

### 日志文件位置

```
logs/
├── automation_24h.log        # 主要运行日志
├── cron_predictions.log      # Crontab预测日志
├── cron_health.log          # Crontab健康检查日志
├── cron_daily.log           # Crontab日报日志
└── daily_report_YYYYMMDD.json # 每日JSON报告
```

### 实时监控

```bash
# 查看实时日志
tail -f logs/automation_24h.log

# 查看预测统计
grep "预测成功" logs/automation_24h.log | wc -l

# 查看错误日志
grep "ERROR" logs/automation_24h.log
```

### 系统状态查询

```bash
# 检查crontab任务
crontab -l | grep football

# 检查进程状态
ps aux | grep automation_daemon_24h

# 检查Docker容器状态
docker-compose ps
```

## 🛠️ 高级配置

### 环境变量配置

创建自定义环境文件：
```bash
# .env.custom
PREDICTION_INTERVAL_MINUTES=20
TEST_DURATION_HOURS=36
ENABLE_MONITORING=true
KELLY_FRACTION=0.3
```

使用自定义配置：
```bash
./scripts/start_24h_automation.sh --env-file .env.custom
```

### 直接使用Python脚本

```bash
# 运行单次预测
python3 scripts/automation_daemon_24h.py --mode single_prediction

# 健康检查
python3 scripts/automation_daemon_24h.py --mode health_check

# 生成日报
python3 scripts/automation_daemon_24h.py --mode daily_report
```

## 📈 性能优化

### 推荐配置

**开发环境**:
- 间隔: 15-30分钟
- 时长: 2-8小时
- 模式: internal_loop

**测试环境**:
- 间隔: 15分钟
- 时长: 24-48小时
- 模式: shadow_test

**生产环境**:
- 间隔: 10-15分钟
- 时长: 持续运行
- 模式: crontab

### 资源要求

**最小配置**:
- CPU: 1核心
- 内存: 1GB
- 磁盘: 5GB

**推荐配置**:
- CPU: 2核心
- 内存: 2GB
- 磁盘: 10GB

## 🚨 故障排除

### 常见问题

**1. 权限问题**
```bash
chmod +x scripts/start_24h_automation.sh
chmod +x scripts/automation_daemon_24h.py
```

**2. Python路径问题**
```bash
export PYTHONPATH="$(pwd):$(pwd)/src:$(pwd)/scripts"
```

**3. 依赖缺失**
```bash
pip install -r requirements.txt
```

**4. 日志权限问题**
```bash
mkdir -p logs
chmod 755 logs
```

### 应急处理

**停止自动化**:
```bash
# Ctrl+C 停止内部循环模式
pkill -f automation_daemon_24h.py

# 清理crontab任务
crontab -r
```

**重启系统**:
```bash
# 重启Docker服务
docker-compose restart

# 重新启动自动化
./scripts/start_24h_automation.sh
```

## 📋 最佳实践

### 1. 定期维护
- 每周检查日志文件大小
- 定期清理旧报告文件
- 监控磁盘使用情况

### 2. 监控建议
- 设置关键指标告警
- 定期查看成功率统计
- 监控系统资源使用

### 3. 安全考虑
- 定期更新依赖包
- 限制文件访问权限
- 定期备份重要数据

## 🎯 生产部署建议

### 1. 使用Docker Compose
```bash
# 生产环境启动
docker-compose --env-file .env.production up -d
./scripts/start_24h_automation.sh --docker -m crontab
```

### 2. 配置监控
- 集成Prometheus/Grafana
- 设置邮件告警
- 配置日志轮转

### 3. 数据备份
- 定期备份数据库
- 保存重要日志文件
- 建立灾难恢复计划

---

## 📞 技术支持

如有问题，请检查：
1. 日志文件中的错误信息
2. 系统资源使用情况
3. 网络连接状态
4. 配置文件正确性

**版本**: v2.3.0-production
**更新时间**: 2025-12-19
**维护者**: FootballPrediction DevOps Team