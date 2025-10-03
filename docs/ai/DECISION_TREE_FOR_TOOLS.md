# 工具选择决策树

**AI编程工具快速决策指南**

## 🚀 快速开始 - 我该做什么？

### 首次接触项目？
```
开始
 └─→ 运行 make context
     └─→ 阅读输出，了解项目状态
         └─→ 根据提示选择下一步
```

### 遇到错误？
```
发现错误
 ├── ImportError/ModuleNotFoundError
 │   └─→ 运行 source scripts/setup_pythonpath.sh
 │       └─→ 如果仍失败 → 运行 verify_core_functionality.py
 │           └─→ 查看报告，安装缺失依赖
 │
 ├── Version Conflict (包版本冲突)
 │   └─→ 运行 backup_environment.py
 │       └─→ 运行 create_clean_env.py
 │           └─→ 运行 resolve_conflicts.py
 │
 ├── Test Failed (测试失败)
 │   └─→ 检查是否是依赖问题 → verify_core_functionality.py
 │       └─→ 如果是代码问题 → 正常debug
 │
 └── 其他错误
     └─→ 运行 make env-check
         └─→ 查看具体错误信息
             └─→ 搜索CLAUDE_TROUBLESHOOTING.md
```

## 📊 需要测试？

### 想运行测试？
```
需要测试
 ├── 快速验证
 │   └─→ make test-quick
 │
 ├── 完整测试
 │   └─→ make test
 │
 ├── 单元测试
 │   └─→ make test-unit
 │
 └── 需要覆盖率报告
     └─→ pytest tests/unit/ --cov=src --cov-report=html
         └─→ python scripts/quick_coverage_view.py
```

### 需要查看覆盖率？
```
查看覆盖率
 ├── 快速看数字
 │   └─→ python scripts/quick_coverage_view.py
 │
 ├── 详细看哪些行没覆盖
 │   └─→ open htmlcov/index.html
 │
 ├── 查看特定模块
 │   └─→ 在htmlcov中搜索文件名
 │
 └── 原始数据
     └─→ 查看 coverage.json
```

## 🔧 环境问题？

### 环境不工作了？
```
环境问题
 ├── 激活失败
 │   └─→ source activate_clean_env.sh
 │       └─→ 如果失败 → 重新创建环境
 │
 ├── 依赖缺失
 │   └─→ 运行 verify_core_functionality.py
 │       └─→ 查看报告，安装缺失包
 │
 ├── 全乱了
 │   └─→ python scripts/dependency_manager/backup_environment.py
 │       └─→ python scripts/dependency_manager/create_clean_env.py
 │           └─── 从备份恢复需要的包
 │
 └── 切换环境
     ├── 开发环境 → source venv/bin/activate
     └── 干净环境 → source venv_clean/bin/activate
```

## 📝 提交代码？

### 准备提交？
```
提交前检查
 ├── 代码写完了？
 │   └─→ make fmt
 │       └─→ make lint
 │           └─→ make test-quick
 │
 ├── 所有检查通过？
 │   └─→ make prepush
 │       └─→ 如果失败 → 修复错误
 │
 └── 确保CI通过？
     └─→ make ci
         └─→ 或运行 ./ci-verify.sh
```

## 🎯 特定任务？

### 做特定任务？
```
特定任务
 ├── 修复依赖
 │   └─→ 使用 task_board.py 跟踪
 │       └─→ PH2: 依赖解决流程
 │
 ├── 提升覆盖率
 │   └─→ 先看当前覆盖率
 │       └─→ 优先选择覆盖率<10%的模块
 │           └─→ 使用"working test"方法
 │
 ├── 添加新功能
 │   └─→ make context
 │       └─→ 查看相关文档
 │           └─→ 写测试前先写功能
 │               └─→ 使用现有模式
 │
 ├── 修复Bug
 │   └─→ 查看Issue Tracker
 │       └─→ 复现错误
 │           └─→ 修复并添加测试
 │
 └── 性能优化
     └─→ 先运行基准测试
         └─→ 优化后对比
             └─── 更新文档
```

## 🆘 紧急情况？

### 一切都崩了？
```
紧急恢复
 ├── 立即备份
 │   └─→ python scripts/dependency_manager/backup_environment.py
 │
 ├── 快速重建
 │   └─→ python scripts/dependency_manager/create_clean_env.py
 │
 ├── 恢复核心包
 │   └─→ 从备份安装必要包
 │
 └── 验证基本功能
     └─→ python scripts/dependency_manager/verify_core_functionality.py
```

## 📋 工具映射表

| 需求 | 工具 | 命令 |
|------|------|------|
| 了解项目 | make | `make context` |
| 检查环境 | make | `make env-check` |
| 安装依赖 | make | `make install` |
| 快速测试 | make | `make test-quick` |
| 完整测试 | make | `make test` |
| 代码格式 | make | `make fmt` |
| 代码检查 | make | `make lint` |
| 提交前检查 | make | `make prepush` |
| CI检查 | make | `make ci` |
| 查看覆盖率 | script | `python scripts/quick_coverage_view.py` |
| 详细覆盖率 | pytest | `pytest --cov=src --cov-report=html` |
| 环境备份 | script | `python scripts/dependency_manager/backup_environment.py` |
| 创建干净环境 | script | `python scripts/dependency_manager/create_clean_env.py` |
| 解决冲突 | script | `python scripts/dependency_manager/resolve_conflicts.py` |
| 验证功能 | script | `python scripts/dependency_manager/verify_core_functionality.py` |
| 设置PYTHONPATH | script | `source scripts/setup_pythonpath.sh` |
| 激活干净环境 | script | `source activate_clean_env.sh` |
| 任务管理 | script | `python scripts/dependency_manager/task_board.py` |
| 兼容性分析 | script | `python scripts/dependency_manager/compatibility_matrix.py` |

## ⚡ 最佳实践

### 开发流程
1. **开始**: `make context`
2. **开发**: 正常编码
3. **测试**: `make test-quick`
4. **格式化**: `make fmt`
5. **检查**: `make lint`
6. **提交**: `make prepush`

### 问题解决流程
1. **识别问题类型**
2. **查找对应工具**
3. **按顺序执行**
4. **验证结果**
5. **记录解决方案**

### 环境管理原则
- 开发用venv
- 测试用venv_clean
- 生产用Docker
- 始终有备份

---

**记住**: 遇到问题先查这个决策树，选择正确的工具会让效率提升10倍！