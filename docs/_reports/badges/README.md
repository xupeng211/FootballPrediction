# 🏅 质量徽章索引

本项目支持自动生成的质量状态徽章，用于在README、文档和GitHub中展示项目质量状态。

## 📋 可用徽章

| 徽章 | 文件名 | 描述 | 数据来源 |
|------|--------|------|----------|
| ![测试覆盖率](coverage.svg) | coverage.svg | 测试覆盖率 | 质量快照 |
| ![质量分数](quality.svg) | quality.svg | 质量分数 | 质量快照 |
| ![测试状态](tests.svg) | tests.svg | 测试状态 | 质量快照 |
| ![AI驱动指标](ai.svg) | ai.svg | AI驱动指标 | 质量快照 |
| ![安全状态](security.svg) | security.svg | 安全状态 | 质量快照 |
| ![文档状态](docs.svg) | docs.svg | 文档状态 | 质量快照 |
| ![Docker就绪状态](docker.svg) | docker.svg | Docker就绪状态 | 质量快照 |
| ![Python版本](python.svg) | python.svg | Python版本 | 质量快照 |
| ![质量趋势](trend.svg) | trend.svg | 质量趋势 | 质量快照 |


## 📝 使用方法

### 在Markdown中使用
```markdown
![Coverage](docs/_reports/badges/coverage.svg)
![Quality](docs/_reports/badges/quality.svg)
![Tests](docs/_reports/badges/tests.svg)
```

### 在HTML中使用
```html
<img src="docs/_reports/badges/coverage.svg" alt="Coverage">
<img src="docs/_reports/badges/quality.svg" alt="Quality">
<img src="docs/_reports/badges/tests.svg" alt="Tests">
```

### 在GitHub README中使用
```markdown
[![Coverage](https://raw.githubusercontent.com/username/repo/main/docs/_reports/badges/coverage.svg)](docs/_reports/TEST_COVERAGE_KANBAN.md)
[![Quality](https://raw.githubusercontent.com/username/repo/main/docs/_reports/badges/quality.svg)](docs/_reports/TEST_COVERAGE_KANBAN.md)
[![Tests](https://raw.githubusercontent.com/username/repo/main/docs/_reports/badges/tests.svg)](docs/_reports/TEST_COVERAGE_KANBAN.md)
```

## 🔄 自动更新

徽章通过以下方式自动更新：
- **CI/CD**: 在GitHub Actions中自动生成和更新
- **本地命令**: 运行 `make generate-badges`
- **质量检查**: 运行 `make quality-dashboard` 时自动生成

## 🎨 自定义徽章

如需自定义徽章样式或添加新徽章类型，请编辑 `scripts/generate_badges.py`。

### 添加新徽章类型
1. 在 `BadgeGenerator` 类中添加新的生成方法
2. 在 `generate_all_quality_badges` 中调用新方法
3. 更新本索引文件

---

*最后更新: 2025-09-28 07:59:48
*自动生成 by: scripts/generate_badges.py*
