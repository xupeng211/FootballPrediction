# 🔧 目录维护工具集

本目录包含了FootballPrediction项目的完整目录维护工具集，用于自动化维护项目目录结构的健康和规范。

## 📁 工具文件说明

### 🤖 核心维护脚本

1. **`directory_maintenance.py`** - 目录维护自动化脚本
   - 功能：清理临时文件、缓存目录、归档旧报告、自动修复问题
   - 用法：`python3 scripts/maintenance/directory_maintenance.py [选项]`

2. **`scheduled_maintenance.py`** - 定期维护任务调度器
   - 功能：按计划执行定期维护任务（每日/每周/每月）
   - 用法：`python3 scripts/maintenance/scheduled_maintenance.py --daemon`

3. **`maintenance_logger.py`** - 维护日志系统
   - 功能：记录和维护维护历史数据，生成趋势分析
   - 用法：被其他脚本调用，也可独立运行

4. **`health_monitor.py`** - 目录健康监控系统
   - 功能：实时监控目录健康状态，生成警报和趋势分析
   - 用法：`python3 scripts/maintenance/health_monitor.py [选项]`

## 🚀 快速开始

### 1. 单次维护检查
```bash
# 检查当前目录健康状况
python3 scripts/maintenance/directory_maintenance.py --check-only

# 运行完整维护（模拟）
python3 scripts/maintenance/directory_maintenance.py --dry-run

# 运行完整维护（实际执行）
python3 scripts/maintenance/directory_maintenance.py --auto-fix
```

### 2. 健康监控
```bash
# 运行健康监控
python3 scripts/maintenance/health_monitor.py

# 查看健康趋势
python3 scripts/maintenance/health_monitor.py --trends

# 生成健康仪表板
python3 scripts/maintenance/health_monitor.py --dashboard
```

### 3. 定期维护调度
```bash
# 单次检查维护任务
python3 scripts/maintenance/scheduled_maintenance.py --once

# 启动守护进程（推荐）
python3 scripts/maintenance/scheduled_maintenance.py --daemon

# 自定义检查间隔（分钟）
python3 scripts/maintenance/scheduled_maintenance.py --daemon --interval 30
```

## 📊 维护配置

### 健康监控阈值
默认阈值配置在 `logs/monitoring/monitoring_config.json` 中：

```json
{
  "thresholds": {
    "max_root_files": 400,        // 最大根目录文件数
    "max_empty_dirs": 5,          // 最大空目录数
    "min_health_score": 70,       // 最低健康评分
    "max_naming_violations": 10,  // 最大命名违规数
    "max_misplaced_files": 20,    // 最大错误放置文件数
    "max_project_size_gb": 5.0,   // 最大项目大小(GB)
    "max_old_reports_days": 30    // 最大旧报告保留天数
  }
}
```

### 定期维护计划
- **每日维护**：清理临时文件和缓存
- **每周维护**：完整维护包括归档和自动修复
- **每月维护**：深度清理和归档

## 📈 监控报告

### 报告存储位置
- **健康报告**: `logs/monitoring/health_monitoring_*.json`
- **维护日志**: `logs/maintenance/maintenance_log_*.json`
- **维护历史**: `logs/maintenance/maintenance_history.db` (SQLite)
- **警报记录**: `logs/monitoring/health_alerts.json`

### 查看历史数据
```bash
# 查看最近的维护历史
python3 scripts/maintenance/maintenance_logger.py

# 查看健康趋势
python3 scripts/maintenance/health_monitor.py --trends
```

## ⚠️ 使用建议

### 🎯 推荐的工作流程

1. **开发阶段**：
   ```bash
   # 定期检查目录健康
   python3 scripts/maintenance/health_monitor.py

   # 清理临时文件
   python3 scripts/maintenance/directory_maintenance.py --clean-only
   ```

2. **提交前**：
   ```bash
   # 运行完整维护
   python3 scripts/maintenance/directory_maintenance.py --auto-fix
   ```

3. **生产环境**：
   ```bash
   # 启动守护进程进行定期维护
   python3 scripts/maintenance/scheduled_maintenance.py --daemon
   ```

### ⚡ 快速命令别名
可以在 `.bashrc` 或 `.zshrc` 中添加别名：

```bash
# 目录维护快捷命令
alias pm-clean="python3 scripts/maintenance/directory_maintenance.py --auto-fix"
alias pm-check="python3 scripts/maintenance/health_monitor.py"
alias pm-daemon="python3 scripts/maintenance/scheduled_maintenance.py --daemon"
```

## 🛠️ 故障排除

### 常见问题

1. **权限错误**：
   ```bash
   chmod +x scripts/maintenance/*.py
   ```

2. **模块导入错误**：
   ```bash
   # 确保在项目根目录执行
   cd /home/user/projects/FootballPrediction
   python3 scripts/maintenance/directory_maintenance.py
   ```

3. **数据库锁定错误**：
   ```bash
   # 等待几秒钟后重试，或删除锁定文件
   rm logs/maintenance/maintenance_history.db-journal
   ```

### 调试模式
```bash
# 启用详细日志
python3 scripts/maintenance/directory_maintenance.py --dry-run -v
```

## 📝 日志级别

脚本支持不同的日志输出级别：
- **静默模式**: 只显示关键错误
- **正常模式**: 显示操作摘要（默认）
- **详细模式**: 显示每个操作的详细信息
- **调试模式**: 显示所有调试信息

## 🔄 集成到CI/CD

### GitHub Actions 示例
```yaml
name: Directory Maintenance
on:
  schedule:
    - cron: '0 2 * * *'  # 每天凌晨2点运行

jobs:
  maintenance:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2
    - name: Setup Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.11'
    - name: Run Directory Maintenance
      run: |
        python3 scripts/maintenance/directory_maintenance.py --auto-fix
        python3 scripts/maintenance/health_monitor.py
```

## 📊 性能影响

- **内存使用**: < 50MB
- **CPU使用**: 日常维护 < 30秒
- **存储影响**: 维护日志 < 10MB/月
- **网络使用**: 无外部网络请求

## 🔗 相关文档

- [目录结构文档](../../docs/DIRECTORY_STRUCTURE.md)
- [命名规范文档](../../docs/NAMING_CONVENTIONS.md)
- [维护指南](../../docs/MAINTENANCE_GUIDE.md)
- [GitHub Issue #200](https://github.com/xupeng211/FootballPrediction/issues/200)

---

**版本**: v1.0
**最后更新**: 2025-11-03
**维护者**: Claude AI Assistant