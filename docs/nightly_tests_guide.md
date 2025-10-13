# 🌙 Nightly 测试指南

## 概述

Nightly 测试是一个自动化的测试套件，每天定时运行，确保系统的持续稳定性和质量。它包括单元测试、集成测试、端到端测试和性能测试。

## 🎯 目标

1. **持续质量保证**：每天自动运行完整测试套件
2. **早期问题发现**：在问题影响生产环境前发现并修复
3. **性能监控**：跟踪系统性能趋势
4. **覆盖率跟踪**：确保测试覆盖率保持在目标水平
5. **自动化反馈**：通过多种渠道发送测试结果通知

## 📋 测试套件组成

### 1. 单元测试 (Unit Tests)
- **目标**：验证单个组件的功能
- **标记**：`@pytest.mark.unit`
- **超时**：10分钟
- **并发**：4个进程
- **覆盖率要求**：≥30%

### 2. 集成测试 (Integration Tests)
- **目标**：验证组件间的交互
- **标记**：`@pytest.mark.integration`
- **超时**：20分钟
- **并发**：2个进程
- **依赖服务**：PostgreSQL, Redis, Kafka

### 3. 端到端测试 (E2E Tests)
- **目标**：验证完整的业务流程
- **标记**：`@pytest.mark.e2e`
- **超时**：30分钟
- **环境**：Staging
- **测试场景**：
  - 用户注册到预测完整流程
  - 比赛实时更新流程
  - 批量数据处理流程

### 4. 性能测试 (Performance Tests)
- **目标**：验证系统性能指标
- **标记**：`@pytest.mark.performance`
- **超时**：15分钟
- **基准对比**：自动对比历史基准
- **关键指标**：
  - API 响应时间 < 1s
  - P95 响应时间 < 2s
  - 并发处理能力 ≥ 50 用户

## 🚀 快速开始

### 本地运行 Nightly 测试

```bash
# 1. 激活虚拟环境
source .venv/bin/activate

# 2. 运行完整测试套件
make nightly-test

# 3. 或者分别运行各个部分
make test-unit          # 单元测试
make test-integration   # 集成测试（需要Docker）
make test-e2e          # E2E测试（需要Staging环境）
make test-performance   # 性能测试
```

### 启动调度器

```bash
# 启动调度器（将在每天指定时间自动运行）
make nightly-schedule

# 查看调度器状态
make nightly-status

# 停止调度器
# 按 Ctrl+C 停止
```

### 生成报告

```bash
# 生成测试报告
make nightly-report

# 查看测试监控
make nightly-monitor

# 清理旧报告
make nightly-cleanup
```

## ⚙️ 配置

### 环境变量

创建 `.env` 文件并配置以下变量：

```bash
# GitHub 配置
GITHUB_TOKEN=your_github_token
GITHUB_REPOSITORY=your_org/your_repo

# Slack 通知（可选）
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...

# 邮件通知（可选）
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASS=your_app_password
EMAIL_TO=dev-team@example.com,qa@example.com

# 测试环境
TESTING=true
TEST_ENV=nightly
```

### 测试调度配置

编辑 `config/nightly_tests.json` 来自定义配置：

```json
{
  "test_schedule": {
    "timezone": "UTC",
    "time": "18:00",        // 每天UTC 18:00（北京时间凌晨2点）
    "weekends": false,      // 周末不运行
    "holidays": ["2024-12-25", "2025-01-01"]
  },
  "quality_gate": {
    "min_success_rate": 95.0,
    "max_failed_tests": 0,
    "required_coverage": 30.0
  }
}
```

## 📊 质量门禁

### 通过条件

1. **总体成功率** ≥ 95%
2. **关键测试失败数** = 0
3. **单元测试成功率** ≥ 98%
4. **测试覆盖率** ≥ 30%

### 失败处理

1. **自动创建 GitHub Issue**
2. **发送失败通知**
3. **记录到问题跟踪系统**
4. **触发回滚流程（如果在部署后）**

## 📈 报告和监控

### 测试报告位置

- **JSON报告**：`reports/nightly-test-report.json`
- **Markdown报告**：`reports/nightly-test-report.md`
- **HTML报告**：`reports/` 目录下各类HTML文件
- **历史记录**：`logs/nightly-test-history.json`

### 监控指标

1. **测试趋势**
   - 成功率变化
   - 覆盖率变化
   - 执行时间变化

2. **性能趋势**
   - 响应时间趋势
   - 吞吐量趋势
   - 错误率趋势

3. **质量趋势**
   - 缺陷发现率
   - 修复时间
   - 回归率

## 🔔 通知系统

### Slack 通知

成功：
```
✅ Nightly Test Report - #1234
成功率: 98.5%
总测试数: 350
覆盖率: 32.1%
```

失败：
```
❌ Nightly Test Report - #1234
成功率: 89.2%
质量门禁问题:
- Integration tests have 5 failures
```

### 邮件通知

邮件包含完整的测试报告，包括：
- 执行概要
- 测试结果详情
- 性能指标
- 改进建议

### GitHub Issue

测试失败时自动创建 Issue，包含：
- 失败详情
- 日志链接
- 修复建议
- 责任人

## 🛠️ 故障排除

### 常见问题

#### 1. 测试超时

```bash
# 检查测试执行时间
grep "duration" reports/nightly-test-report.json

# 增加超时时间
# 编辑 config/nightly_tests.json
{
  "test_types": {
    "e2e": {
      "timeout": 1800  // 30分钟
    }
  }
}
```

#### 2. Docker 服务问题

```bash
# 检查Docker状态
docker ps

# 重启服务
docker-compose -f docker-compose.test.yml down -v
docker-compose -f docker-compose.test.yml up -d

# 查看日志
docker-compose -f docker-compose.test.yml logs
```

#### 3. 通知发送失败

```bash
# 检查配置
python scripts/nightly_test_monitor.py --dry-run

# 测试Slack webhook
curl -X POST -H 'Content-type: application/json' \
  --data '{"text":"Test notification"}' \
  $SLACK_WEBHOOK_URL
```

#### 4. 覆盖率下降

```bash
# 查看覆盖率报告
open reports/html-unit/index.html

# 找出未覆盖的模块
grep -E "class|def" src/your_module.py | head -20

# 添加缺失的测试
```

### 调试模式

```bash
# 运行单个测试类型
pytest tests/unit/ -v -s --tb=long

# 运行特定测试
pytest tests/unit/api/test_predictions.py::test_create_prediction -v -s

# 使用pdb调试
pytest tests/unit/api/test_predictions.py -v -s --pdb
```

## 📅 最佳实践

### 1. 测试编写

- 保持测试独立和可重复
- 使用有意义的测试名称
- 添加清晰的断言消息
- 使用工厂模式生成测试数据

### 2. 性能优化

- 使用并行执行
- 优化数据库查询
- 重用测试数据
- 避免不必要的I/O操作

### 3. 维护

- 定期更新测试数据
- 清理过期的测试
- 重构重复的测试代码
- 更新基准数据

### 4. 监控

- 设置关键指标告警
- 定期审查测试趋势
- 分析失败模式
- 持续改进测试策略

## 📚 相关文档

- [测试运行指南](../TEST_RUN_GUIDE.md)
- [集成测试指南](integration_test_guide.md)
- [E2E测试指南](e2e_test_guide.md)
- [性能测试指南](performance_test_guide.md)
- [CI/CD配置](../.github/workflows/)

## 🆘 获取帮助

1. 查看测试日志：`logs/nightly-test-history.json`
2. 运行健康检查：`make nightly-monitor`
3. 查看调度状态：`make nightly-status`
4. 联系团队：在 GitHub Issue 中标记 `@qa-team`

---

*最后更新：2025-01-12*