# 🚀 1小时无人值守试运行监控器

## 概述

`monitor_pilot_run.py` 是一个专为FootballPrediction系统设计的无人值守监控脚本，用于：

- 自动启动后台回填任务
- 实时监控任务进程状态
- 追踪数据库记录增长情况
- 计算采集速度和性能指标
- 生成详细的Markdown格式报告

## 功能特性

### ✅ 核心功能
- **自动进程管理**: 智能启动和停止回填任务
- **实时监控**: 每分钟检查进程状态和数据增长
- **性能指标**: 计算采集速度(条/分钟)和峰值性能
- **日志管理**: 自动创建日志目录和文件
- **异常处理**: 进程崩溃时自动报警和日志分析
- **详细报告**: 生成包含所有监控数据的Markdown报告

### 🛡️ 安全机制
- **优雅停止**: SIGTERM → SIGKILL 的两阶段停止策略
- **进程监控**: 每分钟检查进程存活状态
- **异常捕获**: 完整的错误处理和日志记录
- **超时保护**: 防止数据库查询等操作无限等待

## 使用方法

### 基本使用

```bash
# 运行默认60分钟监控
python scripts/monitor_pilot_run.py
```

### 自定义监控时长

```python
# 修改脚本中的duration_minutes参数
monitor = PilotRunMonitor(duration_minutes=120)  # 2小时监控
```

## 输出示例

### 实时控制台输出
```
[  5/60] Status: ✅ Running | Total:  150 | Added: + 45 | Speed:  9.0/min
[ 10/60] Status: ✅ Running | Total:  298 | Added: +193 | Speed: 19.3/min
...
[ 60/60] Status: ✅ Running | Total: 1247 | Added: +1142 | Speed: 19.0/min
```

### 生成的Markdown报告包含：

1. **执行摘要** - 时间范围、任务状态
2. **数据采集统计** - 总记录数、平均速度、峰值速度
3. **详细监控数据表** - 每分钟的具体指标
4. **日志分析** - 日志文件信息和最后20行预览
5. **结论和建议** - 系统评估和优化建议

## 文件结构

执行后会在 `logs/` 目录下生成：

```
logs/
├── backfill_pilot.log                    # 回填任务实时日志
└── pilot_run_report_YYYYMMDD_HHMMSS.md   # 监控分析报告
```

## 监控指标说明

| 指标 | 说明 |
|------|------|
| Total | 数据库matches表总记录数 |
| Added | 相比初始状态新增的记录数 |
| Speed | 每分钟平均新增记录数 |

## 故障处理

### 进程崩溃
- 自动检测进程死亡状态
- 显示最后20行错误日志
- 立即停止监控并报告错误

### 数据库连接问题
- 30秒超时保护
- 自动重试机制
- 详细的错误日志记录

## 技术实现

### 依赖项
- Python 3.7+
- Docker & Docker Compose
- PostgreSQL客户端工具
- 标准库: subprocess, time, os, sys, signal

### 架构设计
- **面向对象**: `PilotRunMonitor` 类封装所有功能
- **异步安全**: 避免阻塞操作和死锁
- **资源管理**: 自动进程清理和文件管理
- **日志分离**: 监控日志 vs 回填任务日志

## 最佳实践

1. **执行前检查**:
   ```bash
   make status  # 确保所有服务正常
   make test.fast  # 验证系统健康状态
   ```

2. **监控期间**:
   - 保持SSH连接稳定
   - 监控磁盘空间(日志文件增长)
   - 定期检查控制台输出

3. **完成后**:
   - 查看生成的Markdown报告
   - 分析性能指标和异常情况
   - 根据建议优化系统配置

## 故障排查

### 权限问题
```bash
chmod +x scripts/monitor_pilot_run.py
```

### 日志目录权限
```bash
mkdir -p logs
chmod 755 logs
```

### Docker服务状态
```bash
docker-compose ps
docker-compose logs app
```

---

*此监控器专为FootballPrediction系统设计，确保数据回填任务的稳定性和可靠性。*