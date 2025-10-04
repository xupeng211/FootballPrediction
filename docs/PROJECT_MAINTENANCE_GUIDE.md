# 项目维护指南

## 📋 定期维护任务

### 每日维护

- [ ] 运行 `make test-quick` 确保系统正常
- [ ] 提交前运行 `make fmt && make lint`
- [ ] 临时文件及时分类

### 每周维护

- [ ] 运行 `./scripts/cleanup_project.sh` 清理项目
- [ ] 运行 `make coverage` 检查测试覆盖率
- [ ] 检查 `docs/_reports/` 中的报告

### 每月维护

- [ ] 归档上月报告到 `docs/_reports/archive/YYYY-MM/`
- [ ] 更新 `CHANGELOG.md`
- [ ] 审查项目依赖是否需要更新

## 📁 目录结构规则

### 根目录只保留核心文件

```
项目根目录/
├── src/                    # 源代码
├── tests/                  # 测试
├── docs/                   # 文档
├── config/                 # 配置文件
├── scripts/                # 脚本
├── requirements*.txt      # 依赖文件（3个）
├── docker-compose*.yml     # Docker配置（核心3个）
├── Makefile               # 构建脚本
└── README.md              # 项目说明
```

### 文档分类规则

```
docs/
├── ai/                    # AI相关文档
├── how-to/                # 操作指南
├── architecture/          # 架构文档
├── reference/             # 参考资料
├── testing/               # 测试文档
├── project/               # 项目管理
├── security/              # 安全文档
├── _reports/              # 报告
│   ├── archive/           # 按月归档
│   └── templates/         # 报告模板
└── legacy/                # 历史文档
```

### 配置文件规则

```
config/
├── docker/                # Docker配置
├── pytest/                # 测试配置
├── coverage/              # 覆盖率配置
├── app/                   # 应用配置
└── monitoring/            # 监控配置
```

## 🔄 新文件处理流程

### 1. 临时报告

- 自动移至 `docs/_reports/`
- 月末归档到 `docs/_reports/archive/YYYY-MM/`

### 2. 新文档

- 根据内容分类到相应目录
- 更新 `docs/INDEX.md`

### 3. 配置文件

- 放入 `config/` 的相应子目录
- 更新相关文档

## 🚀 快速命令

### 清理项目

```bash
./scripts/cleanup_project.sh
```

### 检查项目健康

```bash
make env-check && make test-quick
```

### 完整验证

```bash
make fmt && make lint && make test && make prepush
```

## 📝 文档命名规范

### 报告文件

- 临时报告：`REPORT_TYPE_DATE.md`
- 阶段报告：`PHASE_X_COMPLETION_REPORT.md`
- 月度总结：`MONTHLY_SUMMARY_YYYY-MM.md`

### 文档文件

- 使用英文文件名
- 中文内容
- 使用连字符分隔单词

## 🎯 质量检查清单

### 提交前检查

- [ ] 代码格式化完成
- [ ] 测试通过
- [ ] 文档已更新
- [ ] 临时文件已清理

### 发布前检查

- [ ] 所有测试通过
- [ ] 安全扫描通过
- [ ] 文档完整
- [ ] 版本号更新

---
*最后更新：2025-10-02*
