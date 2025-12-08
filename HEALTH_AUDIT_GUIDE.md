# 🔍 System Health Audit 使用指南

## 📋 概述

本指南介绍如何使用 System Health Audit 工具对 FootballPrediction 数据采集系统进行全面的健康度审计。

## 🎯 审计目标

- **L1 赛程模块**: 验证赛程列表获取能力
- **L2 高阶数据模块**: 验证 Super Greedy Mode 数据采集能力
- **连通性**: 确认 API 连接和数据传输正常
- **完整性**: 验证 11 维度数据采集完整
- **健壮性**: 测试错误处理和恢复机制

## 🚀 快速开始

### 1. 运行健康审计 (推荐)

```bash
# 运行独立版审计脚本 (无需依赖)
python scripts/audit_system_health_standalone.py
```

**预期输出**:
```
🔍 System Health Audit - 系统健康度审计 (独立版)
📊 总体健康度: 100.0%
🏅 系统健康等级: 🟢 🏆 优秀 (A+)
✅ 审计通过 (成功率: 100.0%)
```

### 2. 查看详细审计报告

审计完成后，系统会生成详细的健康诊断报告，包括：

- **总体健康度**: 百分比和等级评估
- **分阶段测试结果**: L1 和 L2 模块的详细测试
- **数据维度验证**: Super Greedy Mode 11维度数据检查
- **连通性测试**: API 连接和数据传输验证
- **审计建议**: 系统优化和改进建议

## 📊 审计结果解读

### 健康度等级

| 健康度 | 等级 | 状态 | 建议 |
|--------|------|------|------|
| 90-100% | 🏆 A+ (优秀) | 🟢 | 立即启动大规模回填 |
| 80-89% | ⭐ A (良好) | 🟡 | 修复警告项后启动 |
| 70-79% | 👍 B (一般) | 🟠 | 需要改进功能 |
| <70% | ⚠️ C (需改进) | 🔴 | 联系技术支持 |

### Super Greedy Mode 数据维度

| 维度 | 数据路径 | 验证内容 |
|------|----------|----------|
| 🏛️ 裁判信息 | `environment_json.referee` | ID、姓名、国籍 |
| 🏟️ 场地信息 | `environment_json.venue` | ID、名称、容量、上座率 |
| 🌤️ 天气信息 | `environment_json.weather` | 温度、状况、风速 |
| 📊 xG数据 | `stats_json.xg` | 期望进球数据 |
| 👥 阵容评分 | `lineups_json.starters[].rating` | 球员评分 |
| 🏥 伤停信息 | `lineups_json.unavailable` | 伤停球员名单 |

## 🔧 故障排除

### 常见问题

1. **模块导入错误**
   ```bash
   # 使用独立版脚本 (无模块依赖)
   python scripts/audit_system_health_standalone.py
   ```

2. **审计失败**
   ```bash
   # 检查错误日志
   python scripts/audit_system_health_standalone.py 2>&1 | grep "❌"

   # 查看详细错误信息
   tail -f /tmp/audit_health.log
   ```

3. **数据验证失败**
   ```bash
   # 检查网络连接
   curl -I https://www.fotmob.com/api/

   # 检查API令牌
   cat .env | grep FOTMOB
   ```

### 性能优化

1. **审计速度优化**
   ```python
   # 修改审计脚本中的延迟
   # await asyncio.sleep(1.0)  # 改为 await asyncio.sleep(0.5)
   ```

2. **内存使用优化**
   ```python
   # 限制测试数据量
   # self.league_fixtures = self.league_fixtures[:3]  # 只测试前3场
   ```

## 📋 定期维护

### 推荐审计频率

| 环境 | 频率 | 触发条件 |
|------|------|----------|
| 开发环境 | 每日 | 代码变更后 |
| 测试环境 | 每周 | 部署前 |
| 生产环境 | 每月 | 重大变更后 |

### 自动化审计

```bash
# 创建 cron 任务
# 编辑 crontab: crontab -e
# 每天早上8点运行健康检查
0 8 * * * cd /path/to/FootballPrediction && python scripts/audit_system_health_standalone.py >> /var/log/health_audit.log 2>&1
```

## 🔄 集成到 CI/CD

### GitHub Actions 示例

```yaml
name: System Health Audit
on: [push, pull_request]

jobs:
  health-audit:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2

    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.10'

    - name: Run Health Audit
      run: |
        python scripts/audit_system_health_standalone.py

    - name: Upload Audit Report
      uses: actions/upload-artifact@v2
      with:
        name: health-audit-report
        path: SYSTEM_HEALTH_AUDIT_REPORT.md
```

## 📊 监控和报警

### 关键指标

1. **健康度百分比**
   ```bash
   # 提取健康度
   python scripts/audit_system_health_standalone.py | grep "总体健康度"
   ```

2. **测试通过率**
   ```bash
   # 统计测试结果
   python scripts/audit_system_health_standalone.py | grep -E "✅|❌|⚠️"
   ```

3. **错误日志监控**
   ```bash
   # 监控错误
   python scripts/audit_system_health_standalone.py 2>&1 | grep "❌\|失败\|异常"
   ```

### 报警设置

```bash
# 创建报警脚本
#!/bin/bash
HEALTH_OUTPUT=$(python scripts/audit_system_health_standalone.py 2>&1)
HEALTH_SCORE=$(echo "$HEALTH_OUTPUT" | grep "总体健康度" | grep -o '[0-9]\+\.[0-9]\+%')

if (( $(echo "$HEALTH_SCORE < 80" | bc -l) )); then
    echo "⚠️ 系统健康度低于80%: $HEALTH_SCORE"
    # 发送邮件/Slack通知
    # curl -X POST -H 'Content-type: application/json' --data '{"text":"系统健康度告警"}' https://hooks.slack.com/...
fi
```

## 📚 相关文档

- **系统健康审计报告**: `SYSTEM_HEALTH_AUDIT_REPORT.md`
- **安全加固回填指南**: `SECURITY_HARDENING_GUIDE.md`
- **Super Greedy Mode 完成报告**: `SUPER_GREEDY_COMPLETION_REPORT.md`
- **全历史回填指南**: `BACKFULL_HISTORY_GUIDE.md`

## 🎯 最佳实践

### 审计前准备
1. 确保网络连接稳定
2. 检查系统资源充足
3. 备份关键配置文件

### 审计过程中
1. 仔细观察输出信息
2. 记录任何警告或错误
3. 检查数据完整性验证结果

### 审计后行动
1. 根据健康度评级决定后续步骤
2. 修复发现的问题
3. 更新系统监控配置

## 🔧 扩展和定制

### 添加新的审计维度

```python
# 在 SystemHealthAuditor 类中添加新方法
async def validate_new_feature(self, match_data):
    """验证新功能"""
    # 新的验证逻辑
    pass
```

### 自定义审计目标

```python
# 修改审计配置
AUDIT_LEAGUE_ID = 87  # 改为西甲
AUDIT_SEASON = "2024/2025"  # 指定赛季
AUDIT_DESCRIPTION = "西甲 2024/2025 赛季"  # 更新描述
```

### 集成外部监控

```python
# 添加到审计报告生成
def send_to_monitoring_system(self, results):
    """发送到监控系统"""
    # 集成 Prometheus、Grafana 等
    pass
```

---

## 📞 技术支持

如遇到问题，请提供以下信息：
1. 审计脚本的完整输出
2. 系统环境信息
3. 错误日志详情
4. 重现步骤

**🔍 System Health Audit - 确保数据采集系统始终处于最佳状态！**