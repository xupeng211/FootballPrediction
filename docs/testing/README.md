# 测试附录索引

本目录包含完整的测试附录文档，提供详细的示例、配置与扩展说明，主文档在 [docs/TESTING_STRATEGY.md](../TESTING_STRATEGY.md)。

## 📚 附录文档索引

### [examples.md](./examples.md) — 完整测试用例示例
- 单元测试（Unit Tests）：数据库模型、API控制器、业务逻辑测试
- 集成测试（Integration Tests）：数据库连接、外部服务集成、API集成测试
- 端到端测试（E2E Tests）：完整业务流程测试、数据管道测试
- 异步测试：AsyncMock使用、异步函数测试、上下文管理器测试
- 性能测试：Locust负载测试、API基准测试、数据库性能测试

### [ci_config.md](./ci_config.md) — CI/CD 配置文件与本地模拟脚本
- GitHub Actions工作流配置：测试、覆盖率、质量检查自动化
- 覆盖率监控：Codecov集成、覆盖率报告生成、趋势监控
- 多环境部署：开发、测试、生产环境配置管理
- 安全扫描：bandit安全检查、依赖漏洞扫描、许可证检查
- 本地CI模拟：ci-verify.sh脚本、Docker环境测试
- 通知系统：Slack通知、邮件告警、状态报告

### [performance_tests.md](./performance_tests.md) — 性能与压力测试的完整代码与说明
- Locust性能测试：用户模拟、负载测试、压力测试场景
- API性能测试：响应时间、吞吐量、并发连接测试
- 数据库性能：查询优化、连接池、索引性能测试
- 性能监控：Prometheus指标、Grafana仪表板、性能分析
- 负载测试策略：逐步加压、峰值测试、长时间稳定性测试
- 性能优化：缓存策略、异步处理、数据库调优

### [fixtures_factories.md](./fixtures_factories.md) — 测试数据工厂与 fixtures 定义
- Factory Boy实现：复杂数据模型工厂、关系数据生成、批量数据创建
- 外部服务Mock：Redis模拟、MLflow模拟、Kafka模拟、API模拟
- 测试数据管理：数据隔离、清理机制、状态管理
- 异步Fixtures：异步数据库连接、外部服务连接、事件循环管理
- 测试工具：统一Mock配置、测试辅助函数、断言扩展

## 📁 目录结构

```plaintext
docs/testing/
├── README.md
├── examples.md
├── ci_config.md
├── performance_tests.md
└── fixtures_factories.md
```