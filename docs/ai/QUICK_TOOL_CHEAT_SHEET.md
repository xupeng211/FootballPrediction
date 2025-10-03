# 工具速查表

**一页纸AI编程工具参考**

## 🚀 最常用命令

```bash
# 开发必备
make context          # 了解项目
make test-quick       # 快速测试
make prepush         # 提交前检查

# 环境问题
source scripts/setup_pythonpath.sh    # 导入错误
source activate_clean_env.sh          # 切换干净环境
python scripts/dependency_manager/verify_core_functionality.py  # 验证环境

# 覆盖率
python scripts/quick_coverage_view.py  # 查看覆盖率
open htmlcov/index.html               # 详细报告
```

## 📊 按问题类型查找工具

### 🚨 错误类型
| 错误 | 工具 |
|------|------|
| ImportError | `source scripts/setup_pythonpath.sh` |
| ModuleNotFoundError | `verify_core_functionality.py` |
| Version Conflict | `create_clean_env.py` |
| Test Failed | `make test-quick` |
| Coverage Low | `quick_coverage_view.py` |
| Environment Broken | `backup_environment.py` + `create_clean_env.py` |

### 🎯 任务类型
| 任务 | 工具 |
|------|------|
| 新功能开发 | `make context` → 查文档 → 写代码 |
| Bug修复 | 查Issue → 复现 → 修复 → 测试 |
| 提升覆盖率 | `quick_coverage_view.py` → 选模块 → 写测试 |
| 依赖升级 | `backup_environment.py` → 升级 → 测试 |
| 代码审查 | `open htmlcov/index.html` |
| 环境清理 | `create_clean_env.py` |

## 🔧 工具功能速查

### Make命令
```bash
make help            # 查看所有命令
make install         # 安装依赖
make context         # 加载项目上下文 ⭐
make env-check       # 检查环境
make test            # 完整测试
make test-quick      # 快速测试
make test-unit       # 单元测试
make test-coverage   # 测试覆盖率
make fmt             # 代码格式化
make lint            # 代码检查
make prepush         # 提交前检查 ⭐
make ci              # CI检查
```

### 依赖管理
```bash
# 备份
python scripts/dependency_manager/backup_environment.py

# 创建干净环境
python scripts/dependency_manager/create_clean_env.py

# 解决冲突
python scripts/dependency_manager/resolve_conflicts.py

# 验证功能
python scripts/dependency_manager/verify_core_functionality.py

# 兼容性分析
python scripts/dependency_manager/compatibility_matrix.py

# 任务管理
python scripts/dependency_manager/task_board.py
```

### 环境管理
```bash
# 激活环境
source activate_clean_env.sh           # 干净环境
source venv_clean/bin/activate         # 直接激活
source venv/bin/activate               # 开发环境

# 设置路径
source scripts/setup_pythonpath.sh     # 解决导入问题
export PYTHONPATH=$PWD:$PYTHONPATH     # 临时设置
```

### 测试覆盖率
```bash
# 快速查看
python scripts/quick_coverage_view.py

# 完整报告
pytest tests/unit/ --cov=src --cov-report=html --cov-report=json

# 特定模块
pytest tests/unit/test_main.py --cov=src.main --cov-report=term

# HTML报告
open htmlcov/index.html
```

## 🎲 随机问题解决

### 问题：模块导入失败
```bash
1. source scripts/setup_pythonpath.sh
2. python -c "import src.module"  # 测试
3. 如果失败，运行 verify_core_functionality.py
4. 查看报告，安装缺失包
```

### 问题：测试覆盖率低
```bash
1. python scripts/quick_coverage_view.py  # 查看当前
2. 打开 htmlcov/index.html  # 查看细节
3. 选择覆盖率<10%的模块
4. 使用"working test"方法写测试
```

### 问题：依赖冲突
```bash
1. python scripts/dependency_manager/backup_environment.py
2. python scripts/dependency_manager/create_clean_env.py
3. source activate_clean_env.sh
4. python scripts/dependency_manager/resolve_conflicts.py
```

### 问题：提交失败
```bash
1. make fmt          # 格式化
2. make lint         # 检查
3. make test-quick   # 测试
4. make prepush      # 完整检查
```

## 📁 重要文件位置

```
docs/ai/
├── TOOLS_REFERENCE_GUIDE.md      # 完整工具指南
├── DECISION_TREE_FOR_TOOLS.md    # 决策树
└── QUICK_TOOL_CHEAT_SHEET.md     # 本速查表

scripts/
├── setup_pythonpath.sh           # PYTHONPATH设置
├── quick_coverage_view.py        # 覆盖率查看
└── dependency_manager/
    ├── task_board.py             # 任务管理
    ├── backup_environment.py     # 环境备份
    ├── create_clean_env.py       # 创建环境
    ├── resolve_conflicts.py      # 解决冲突
    └── verify_core_functionality.py  # 功能验证

htmlcov/
└── index.html                    # 覆盖率报告

coverage.json                     # 覆盖率数据
venv_clean/                       # 干净环境
activate_clean_env.sh             # 环境激活
```

## 💡 Pro Tips

1. **永远先运行** `make context`
2. **导入错误先检查** PYTHONPATH
3. **环境问题用** venv_clean
4. **提交前必须** `make prepush`
5. **看覆盖率用** `quick_coverage_view.py`
6. **紧急情况** 备份后重建

## 🆘 救急命令

```bash
# 一键环境恢复
python scripts/dependency_manager/backup_environment.py && \
python scripts/dependency_manager/create_clean_env.py && \
source activate_clean_env.sh && \
python scripts/dependency_manager/verify_core_functionality.py

# 快速状态检查
make env-check && make test-quick

# 覆盖率快照
python scripts/quick_coverage_view.py > coverage_snapshot.txt
```

---

**打印此页或保存到书签，随时查阅！**