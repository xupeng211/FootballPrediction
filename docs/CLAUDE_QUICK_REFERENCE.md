# Claude 快速参考手册

本文档提供 Claude Code 开发过程中常用的命令和操作参考。

## 🚀 一键启动

```bash
# 新环境首次设置
make install && make context && make test

# 日常开发流程
make env-check && make test-quick && make ci
```

## 📋 常用命令速查

### 环境管理
| 命令 | 说明 | 使用场景 |
|------|------|----------|
| `make help` | 显示所有命令 | 不确定用什么命令时 |
| `make env-check` | 检查环境健康 | 开发前、遇到问题时 |
| `make install` | 安装依赖 | 新环境、依赖更新后 |
| `make clean` | 清理环境 | 遇到依赖冲突时 |

### 代码质量
| 命令 | 说明 | 使用场景 |
|------|------|----------|
| `make fmt` | 格式化代码 | 提交前 |
| `make lint` | 代码检查 | 提交前 |
| `make type-check` | 类型检查 | 提交前 |
| `make quality` | 完整质量检查 | 重要提交前 |

### 测试相关
| 命令 | 说明 | 使用场景 |
|------|------|----------|
| `make test` | 运行所有测试 | 开发完成后 |
| `make test-quick` | 快速测试（超时保护） | 开发过程中 |
| `make coverage` | 覆盖率报告 | 提交PR前 |
| `make coverage-fast` | 快速覆盖率 | 日常开发 |

### CI/CD
| 命令 | 说明 | 使用场景 |
|------|------|----------|
| `make ci` | 模拟CI流程 | 推送前验证 |
| `make prepush` | 预推送检查 | 推送前必运行 |
| `./ci-verify.sh` | 完整CI验证 | 重要版本发布前 |

## 🎯 开发工作流

### 新功能开发
1. `make context` - 了解项目状态
2. `make env-check` - 验证环境
3. 开发功能（记得更新文档）
4. `make test-quick` - 快速测试
5. `make fmt && make lint` - 代码规范
6. `make coverage` - 验证覆盖率
7. `make prepush` - 完整检查

### Bug修复
1. `make test-quick` - 复现问题
2. 修复代码
3. `make test` - 验证修复
4. 创建 bugfix 报告

### 紧急修复
```bash
# 最小化检查流程
make fmt && make test-quick && git commit -m "fix:紧急修复"
```

## 🔍 常见问题快速解决

### 测试失败
```bash
# 查看详细错误
pytest -v tests/unit/test_specific.py -s

# 运行单个测试
pytest tests/unit/test_module.py::TestClass::test_method
```

### 环境问题
```bash
# 重建环境
make clean && rm -rf .venv && make install

# 检查依赖
pip list | grep fastapi
```

### Docker问题
```bash
# 重启服务
docker-compose down && docker-compose up -d

# 查看日志
docker-compose logs app
```

## 📊 性能优化命令

```bash
# 性能测试
make benchmark

# 内存分析
make profile-memory

# 生成火焰图
make flamegraph
```

## 🏃‍♂️ 效率技巧

### 1. 并行执行
```bash
# 同时运行格式化和检查
make fmt & make lint
```

### 2. 选择性测试
```bash
# 只运行单元测试
pytest tests/unit/

# 排除慢测试
pytest -m "not slow"
```

### 3. 快速迭代
```bash
# 监视文件变化自动测试
ptw --runner "python -m pytest" tests/
```

## 📱 重要文件位置

```
项目配置：
├── .env.example          # 环境变量模板
├── requirements.txt      # 生产依赖
├── requirements-dev.txt  # 开发依赖
└── pytest.ini          # 测试配置

关键代码：
├── src/main.py          # 应用入口
├── src/api/             # API端点
├── src/database/        # 数据库相关
└── src/utils/           # 工具函数

文档：
├── docs/INDEX.md        # 文档索引
├── docs/reference/      # 参考资料
└── docs/AI_DEVELOPMENT_DOCUMENTATION_RULES.md  # AI开发规则
```

## 🚨 紧急联系

遇到无法解决的问题：
1. 检查 `make env-check` 输出
2. 查看测试日志
3. 参考故障排除指南 `CLAUDE_TROUBLESHOOTING.md`
4. 查看项目文档 `docs/`

---
*最后更新：2025-10-02*