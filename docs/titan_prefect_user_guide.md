# Titan007 Prefect 自动化调度系统使用指南

## 📋 概述

Titan007 Prefect 自动化调度系统是基于 Prefect 2.0 构建的企业级数据采集调度解决方案，实现了完全自动化的足球赔率数据采集、处理和存储。

### 🎯 核心特性

- **智能调度**: 支持常规模式、临场模式和混合模式
- **完全自动化**: 从数据采集到数据库入库的全流程自动化
- **高可靠性**: 内置重试机制、错误处理和故障恢复
- **实时监控**: 基于 Prefect UI 的实时监控和日志追踪
- **企业级架构**: 双表数据架构，支持Latest表和History表分离
- **灵活配置**: 支持多种调度策略和参数配置

---

## 🏗️ 系统架构

### 数据流程
```
FotMob 赛程 → ID 对齐 → 并发采集 → 数据转换 → 双表存储
     ↓            ↓           ↓           ↓           ↓
   定时获取    Titan映射   欧赔/亚盘/大小球   DTO转换  Latest+History
```

### 调度模式
- **常规模式**: 每天 08:00 运行，获取当天比赛的初盘数据
- **临场模式**: 每 10 分钟运行，采集未来 2 小时内开赛比赛的最赔率
- **混合模式**: 结合常规和临场模式的全天候数据采集
- **智能调度**: 基于比赛密度的动态调度

---

## 🚀 快速开始

### 前置条件

1. **Prefect Server 启动**
   ```bash
   # 启动 Prefect Server 和 UI
   prefect server start

   # 或者使用 Docker Compose
   docker-compose -f docker-compose.scheduler.yml up -d
   ```

2. **环境配置**
   ```bash
   # 确保数据库连接正常
   make status

   # 检查 Prefect 服务
   curl http://localhost:4200/health
   ```

### 基本使用

#### 1. 一键启动完整系统
```bash
# 启动包含所有调度策略的完整系统
python scripts/run_titan_pipeline.py --start

# 系统将自动注册所有 Flow 并启动监控
```

#### 2. 启动特定模式
```bash
# 常规模式 - 日常数据采集
python scripts/run_titan_pipeline.py --mode regular

# 临场模式 - 高频实时采集
python scripts/run_titan_pipeline.py --mode live

# 混合模式 - 常规+临场
python scripts/run_titan_pipeline.py --mode hybrid
```

#### 3. 系统监控
```bash
# 实时监控系统状态
python scripts/run_titan_pipeline.py --monitor

# 查看 Prefect UI（浏览器访问）
open http://localhost:4200
```

#### 4. 快速测试
```bash
# 运行小规模测试（5场比赛，3并发）
python scripts/run_titan_pipeline.py --test
```

---

## 📊 高级管理

### Flow 部署管理

使用 `deploy_flow.py` 进行高级部署管理：

```bash
# 注册所有 Flow 到 Prefect Server
python scripts/deploy_flow.py --register

# 查看已注册的部署
python scripts/deploy_flow.py --list

# 验证特定部署的健康状态
python scripts/deploy_flow.py --verify titan-regular-deployment

# 手动触发部署
python scripts/deploy_flow.py --trigger titan-live-deployment

# 清理过期部署（保留30天）
python scripts/deploy_flow.py --clean 30

# 检查 Prefect Server 健康状态
python scripts/deploy_flow.py --health
```

### 部署配置详解

#### 常规模式部署
- **名称**: `titan-regular-deployment`
- **调度**: 每天早上 08:00 (cron: `0 8 * * *`)
- **功能**: 获取当天比赛的初盘数据
- **参数**:
  ```python
  {
      "days_ahead": 1,
      "batch_size": 20,
      "max_concurrency": 15
  }
  ```

#### 临场模式部署
- **名称**: `titan-live-deployment`
- **调度**: 每 10 分钟 (interval: `10 minutes`)
- **功能**: 采集即将开赛比赛的最新赔率
- **参数**:
  ```python
  {
      "hours_ahead": 2,
      "batch_size": 10,
      "max_concurrency": 8
  }
  ```

#### 混合模式部署
- **名称**: `titan-hybrid-deployment`
- **调度**: 手动触发
- **功能**: 结合常规和临场模式
- **参数**:
  ```python
  {
      "regular_hours_ahead": 1,
      "live_hours_ahead": 2,
      "enable_live": True,
      "cleanup_days": 7
  }
  ```

---

## 🔧 配置说明

### 环境变量配置

```bash
# 数据库配置
export DATABASE_URL="postgresql://user:pass@localhost:5432/football_prediction"

# Titan007 API 配置
export TITAN_BASE_URL="https://live.titan007.com/api/odds"
export TITAN_MAX_RETRIES=3
export TITAN_TIMEOUT=30.0
export TITAN_RATE_LIMIT_QPS=2.0

# Prefect 配置
export PREFECT_API_URL="http://localhost:4200/api"
export PREFECT_SERVER_API_HOST="localhost"
export PREFECT_SERVER_API_PORT=4200
```

### 调度参数调优

#### 性能参数
- `batch_size`: ID 对齐批处理大小 (建议: 10-50)
- `max_concurrency`: 最大并发采集数 (建议: 5-20)
- `hours_ahead`: 临场模式提前小时数 (建议: 2-4)
- `days_ahead`: 常规模式提前天数 (建议: 1-3)

#### 重试参数
- `retries`: 任务重试次数 (建议: 1-3)
- `retry_delay_seconds`: 重试间隔 (建议: 60-300)
- `timeout`: HTTP 请求超时 (建议: 30-60)

---

## 📈 监控和运维

### Prefect UI 监控

访问 `http://localhost:4200` 查看：

#### 主要页面
- **Dashboard**: 系统整体状态概览
- **Flow Runs**: 所有运行记录和状态
- **Task Runs**: 任务级别的执行详情
- **Deployments**: 调度配置和管理
- **Work Pools**: 工作队列状态

#### 关键指标
- **成功率**: 数据采集任务成功率 (目标: >95%)
- **执行时间**: 平均任务执行时间
- **并发度**: 当前运行的并发任务数
- **错误率**: 失败任务占比

### 日志监控

```bash
# 查看 Prefect Server 日志
docker-compose logs prefect-server

# 查看特定 Flow 运行日志
prefect flow-run inspect <flow-run-id>

# 实时监控日志
tail -f logs/titan_pipeline.log
```

### 健康检查

```bash
# 检查 Prefect Server
curl http://localhost:4200/health

# 检查部署状态
python scripts/deploy_flow.py --verify titan-regular-deployment

# 系统状态概览
python scripts/run_titan_pipeline.py --monitor
```

---

## 🚨 故障处理

### 常见问题

#### 1. Prefect Server 连接失败
```bash
# 检查服务状态
docker-compose ps

# 重启 Prefect 服务
docker-compose restart prefect-server prefect-agent

# 检查端口占用
lsof -i :4200
```

#### 2. 数据采集失败
```bash
# 检查网络连接
curl -I https://live.titan007.com

# 检查数据库连接
make db-shell

# 运行快速测试
python scripts/run_titan_pipeline.py --test
```

#### 3. 内存或性能问题
```bash
# 调低并发数
export TITAN_MAX_CONCURRENCY=5

# 增加重试间隔
export TITAN_RETRY_DELAY_SECONDS=300

# 监控系统资源
docker stats
```

### 应急恢复

```bash
# 停止所有调度
python scripts/deploy_flow.py --trigger titan-hybrid-deployment

# 清理异常状态
python scripts/deploy_flow.py --clean 7

# 重新部署
python scripts/deploy_flow.py --register
```

---

## 📋 最佳实践

### 生产环境建议

1. **调度策略**
   - 常规模式：每日凌晨业务低峰期运行
   - 临场模式：比赛密集期启用（如周末、节假日）
   - 清理任务：每周日凌晨运行数据清理

2. **性能优化**
   - 根据服务器性能调整并发数
   - 设置合理的超时和重试策略
   - 定期清理历史数据和日志

3. **监控告警**
   - 设置成功率阈值告警 (<95%)
   - 监控 API 调用频率和响应时间
   - 定期检查数据库磁盘空间

4. **数据质量**
   - 定期验证数据完整性
   - 监控 ID 对齐成功率
   - 检查赔率数据合理性

### 安全建议

1. **API 密钥管理**
   ```bash
   # 使用环境变量存储敏感信息
   export TITAN_API_TOKEN="your-token"
   export DATABASE_PASSWORD="your-password"
   ```

2. **网络安全**
   - 使用 HTTPS 连接外部 API
   - 配置防火墙规则限制访问
   - 定期更新依赖包

3. **数据安全**
   - 定期备份数据库
   - 设置数据库访问权限
   - 记录操作审计日志

---

## 🎯 总结

Titan007 Prefect 自动化调度系统提供了企业级的数据采集解决方案，通过智能调度、实时监控和故障恢复机制，确保了数据采集的高可靠性和高可用性。

### 快速命令速查

```bash
# 🚀 启动系统
python scripts/run_titan_pipeline.py --start

# 📊 监控状态
python scripts/run_titan_pipeline.py --monitor

# 🧪 快速测试
python scripts/run_titan_pipeline.py --test

# 📦 部署管理
python scripts/deploy_flow.py --list

# 🏥 健康检查
python scripts/deploy_flow.py --health
```

### 联系支持

如遇到问题，请：
1. 查看 Prefect UI 错误日志
2. 运行健康检查脚本
3. 检查系统资源使用情况
4. 参考本文档故障处理章节

---

**版本**: v1.0.0
**更新时间**: 2024-12-12
**维护团队**: FootballPrediction 开发团队