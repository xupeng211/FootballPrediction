# 🧪 测试指南

本目录包含项目的测试相关文档。

## 📚 核心文档

### 🌟 [TEST_GUIDE.md](./TEST_GUIDE.md) - **主要测试指南** ⭐

全新的测试体系文档，包含：

- 三层测试架构说明
- Mock 架构使用方法
- 详细的运行命令
- 故障排除指南
- 测试最佳实践

**这是您最需要的文档！**

## 📋 其他文档

### [examples.md](./examples.md) - 测试示例

- 单元测试示例
- 集成测试示例
- 性能测试示例

### [ci_config.md](./ci_config.md) - CI/CD 配置

- GitHub Actions 配置
- 覆盖率报告
- 自动化流水线

### [performance_tests.md](./performance_tests.md) - 性能测试

- 基准测试
- 负载测试
- 性能监控

### [fixtures_factories.md](./fixtures_factories.md) - 测试工具

- 测试数据工厂
- Mock 配置
- Fixtures 使用

### [CI_GUARDIAN_GUIDE.md](./CI_GUARDIAN_GUIDE.md) - CI 问题排查

- CI 失败排查
- 常见问题解决

## 🚀 快速开始

### 运行测试

```bash
# 快速测试（推荐日常使用）
make test-quick

# 完整测试 + 覆盖率
make test-full

# 只运行单元测试
pytest tests/unit -v
```

### 测试架构

```
tests/
├── unit/      # Mock 测试（快速）
├── legacy/    # 真实服务测试（慢）
└── e2e/       # 端到端测试
```

## 📁 文档归档

过时的测试文档已归档至：
`[archive/](./archive/)`

## 🔗 相关链接

- [主文档目录](../INDEX.md)
- [API 参考](../reference/API_REFERENCE.md)
- [开发指南](../reference/DEVELOPMENT_GUIDE.md)

---

*最后更新：2025-01-04*
