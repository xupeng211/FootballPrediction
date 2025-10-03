# AI编程工具参考指南

**本文档为AI编程工具提供完整的项目工具使用指南**

## 📋 目录
- [核心命令](#核心命令)
- [依赖管理工具](#依赖管理工具)
- [测试覆盖率工具](#测试覆盖率工具)
- [环境管理工具](#环境管理工具)
- [任务管理工具](#任务管理工具)
- [诊断工具](#诊断工具)
- [使用场景](#使用场景)

## 🔧 核心命令

### 基础开发命令
```bash
make install          # 安装项目依赖
make context          # 加载项目上下文（最重要！）
make test             # 运行测试
make test-quick       # 快速测试
make test-unit        # 只运行单元测试
make test-coverage    # 运行测试覆盖率
make ci               # 完整CI检查
make prepush          # 提交前检查
make fmt              # 代码格式化
make lint             # 代码检查
make env-check        # 检查环境
```

### 何时使用
- **开始工作前**: `make context` - 必须首先运行
- **开发完成后**: `make test` 或 `make test-quick`
- **提交代码前**: `make prepush`
- **需要完整检查**: `make ci`

## 📦 依赖管理工具

### 1. 创建干净环境
**工具**: `scripts/dependency_manager/create_clean_env.py`
```bash
# 使用场景：需要创建全新的虚拟环境
python scripts/dependency_manager/create_clean_env.py
```
**使用时机**：
- 发现依赖冲突时
- 需要隔离测试环境时
- 环境被污染需要重建时

### 2. 备份当前环境
**工具**: `scripts/dependency_manager/backup_environment.py`
```bash
# 使用场景：备份现有环境
python scripts/dependency_manager/backup_environment.py
```
**使用时机**：
- 进行重大更改前
- 升级依赖版本前
- 需要回滚能力时

### 3. 解决依赖冲突
**工具**: `scripts/dependency_manager/resolve_conflicts.py`
```bash
# 使用场景：检测和解决依赖冲突
python scripts/dependency_manager/resolve_conflicts.py
```
**使用时机**：
- 遇到ImportError时
- 包版本冲突时
- 测试失败因为依赖问题时

### 4. 验证核心功能
**工具**: `scripts/dependency_manager/verify_core_functionality.py`
```bash
# 使用场景：验证环境是否正常工作
python scripts/dependency_manager/verify_core_functionality.py
```
**使用时机**：
- 安装新环境后
- 修改依赖后
- 测试前验证

### 5. 激活环境脚本
**工具**: `activate_clean_env.sh`
```bash
# 使用场景：快速激活干净环境
source activate_clean_env.sh
```

### 6. PYTHONPATH配置
**工具**: `scripts/setup_pythonpath.sh`
```bash
# 使用场景：设置Python路径
source scripts/setup_pythonpath.sh
```
**使用时机**：
- 遇到模块导入错误时
- 运行测试前
- 切换环境后

## 🧪 测试覆盖率工具

### 1. 运行完整测试覆盖率
```bash
# 使用场景：获取完整测试覆盖率报告
source scripts/setup_pythonpath.sh
source venv_clean/bin/activate
pytest tests/unit/ --cov=src --cov-report=term --cov-report=html --cov-report=json
```
**使用时机**：
- 需要了解代码测试情况时
- PR审查前
- 定期质量检查时

### 2. 查看覆盖率摘要
**工具**: `scripts/quick_coverage_view.py`
```bash
# 使用场景：快速查看覆盖率统计
python scripts/quick_coverage_view.py
```
**使用时机**：
- 需要快速了解覆盖率情况
- 不需要详细报告时
- 命令行快速查看时

### 3. 查看HTML报告
```bash
# 使用场景：查看详细的交互式覆盖率报告
open htmlcov/index.html  # macOS
# 或
xdg-open htmlcov/index.html  # Linux
```
**使用时机**：
- 需要查看具体哪些行未覆盖
- 需要深入了解覆盖情况
- 制定测试计划时

## 📊 任务管理工具

### 1. 任务看板
**工具**: `scripts/dependency_manager/task_board.py`
```bash
# 使用场景：管理依赖解决任务
python scripts/dependency_manager/task_board.py
```
**使用时机**：
- 系统性解决依赖问题时
- 需要跟踪任务进度时
- 多步骤复杂任务时

### 2. 更新任务状态
```bash
# 使用示例
python scripts/dependency_manager/task_board.py update PH2-3 in_progress
python scripts/dependency_manager/task_board.py update PH2-3 completed
```

### 3. 生成任务报告
```bash
# 使用场景：生成任务完成报告
python scripts/dependency_manager/task_board.py generate_report
```

## 🔍 诊断工具

### 1. 依赖树分析
```bash
# 使用场景：查看依赖关系
pipdeptree
```

### 2. 包冲突检测
**工具**: `scripts/dependency_manager/compatibility_matrix.py`
```bash
# 使用场景：分析版本兼容性
python scripts/dependency_manager/compatibility_matrix.py
```

### 3. 环境信息
```bash
# 使用场景：查看当前环境信息
pip list
pip freeze
python --version
```

## 🎯 使用场景

### 场景1：首次设置项目
```bash
# 1. 加载项目上下文
make context

# 2. 检查环境
make env-check

# 3. 安装依赖
make install

# 4. 运行测试验证
make test
```

### 场景2：遇到依赖问题
```bash
# 1. 备份当前环境
python scripts/dependency_manager/backup_environment.py

# 2. 创建干净环境
python scripts/dependency_manager/create_clean_env.py

# 3. 解决冲突
python scripts/dependency_manager/resolve_conflicts.py

# 4. 验证功能
python scripts/dependency_manager/verify_core_functionality.py
```

### 场景3：需要测试覆盖率
```bash
# 1. 设置环境
source scripts/setup_pythonpath.sh
source venv_clean/bin/activate

# 2. 运行测试
pytest tests/unit/ --cov=src --cov-report=html

# 3. 查看报告
python scripts/quick_coverage_view.py
open htmlcov/index.html
```

### 场景4：提交代码前
```bash
# 1. 格式化代码
make fmt

# 2. 代码检查
make lint

# 3. 运行测试
make test-quick

# 4. 完整检查
make prepush
```

### 场景5：模块导入错误
```bash
# 1. 设置PYTHONPATH
source scripts/setup_pythonpath.sh

# 2. 检查模块
python -c "import src.main"

# 3. 如果失败，检查依赖
python scripts/dependency_manager/verify_core_functionality.py
```

## 📝 重要提醒

### 必须记住的规则
1. **始终先运行** `make context`
2. **遇到问题先检查** `make env-check`
3. **提交前必须运行** `make prepush`
4. **依赖问题使用** venv_clean环境
5. **导入错误检查** PYTHONPATH

### 环境优先级
1. **干净环境** (venv_clean) - 用于解决依赖问题
2. **开发环境** (当前venv) - 用于日常开发
3. **生产环境** (Docker) - 用于部署

### 常见问题映射
- **ImportError** → 检查PYTHONPATH + verify_core_functionality
- **版本冲突** → create_clean_env + resolve_conflicts
- **测试失败** → 检查依赖 + 使用干净环境
- **覆盖率低** → 查看htmlcov报告 + 优先测试核心模块

## 🚀 快速参考卡片

### 紧急情况
```bash
# 环境全乱了？快速重建
python scripts/dependency_manager/backup_environment.py
python scripts/dependency_manager/create_clean_env.py
source activate_clean_env.sh
```

### 日常开发
```bash
make context && make test-quick
```

### 提交前
```bash
make fmt && make lint && make prepush
```

### 查看覆盖
```bash
python scripts/quick_coverage_view.py
```

---

**记住**: 这些工具都是为了让开发更顺畅。遇到问题时，先查看这个指南，选择合适的工具。