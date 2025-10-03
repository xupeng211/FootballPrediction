# 测试工具使用说明书

## 📋 目录
1. [工具概览](#工具概览)
2. [快速开始](#快速开始)
3. [核心工具详解](#核心工具详解)
4. [命令行工具](#命令行工具)
5. [Web界面工具](#web界面工具)
6. [监控和分析](#监控和分析)
7. [故障排除](#故障排除)
8. [最佳实践](#最佳实践)

## 🎯 工具概览

### 工具分类

| 类别 | 工具名称 | 文件路径 | 功能描述 |
|------|---------|----------|----------|
| **测试运行器** | Test Runner | `scripts/test_runner.py` | 智能分层测试执行 |
| **质量监控器** | Quality Monitor | `tests/monitoring/test_quality_monitor.py` | 实时质量指标收集 |
| **质量仪表板** | Quality Dashboard | `tests/monitoring/quality_dashboard.py` | Web可视化界面 |
| **覆盖率优化器** | Coverage Optimizer | `tests/monitoring/coverage_optimization.py` | 覆盖率分析和优化 |
| **报告生成器** | Report Generator | `scripts/generate_test_report.py` | 综合质量报告 |

### Make快捷命令

| 命令 | 功能 | 适用场景 |
|------|------|----------|
| `make test.layered` | 运行分层测试 | 日常开发 |
| `make test.unit` | 仅运行单元测试 | 快速验证 |
| `make test.monitor` | 生成质量报告 | 质量检查 |
| `make test.report` | 生成综合报告 | 深度分析 |
| `make test.coverage-plan` | 覆盖率优化计划 | 覆盖率提升 |

## 🚀 快速开始

### 安装依赖
```bash
# 激活虚拟环境
source .venv/bin/activate

# 安装测试依赖
pip install -r requirements-dev.txt
```

### 基础使用

1. **运行测试**
```bash
# 最简单的测试命令
make test

# 分层测试
make test.layered
```

2. **查看质量**
```bash
# 生成质量报告
make test.monitor

# 查看HTML仪表板
make test.dashboard
```

3. **优化覆盖率**
```bash
# 查看需要优化的模块
make test.coverage-plan
```

## 📦 核心工具详解

### 1. Test Runner - 智能测试运行器

**位置**: `scripts/test_runner.py`

**功能**:
- 分层执行测试（单元/集成/E2E）
- 并行运行提高效率
- 自动质量门禁检查

**基础用法**:
```bash
# 运行所有测试
python scripts/test_runner.py

# 运行特定层级
python scripts/test_runner.py --layers unit integration

# 并行执行
python scripts/test_runner.py --parallel

# 仅运行失败的测试
python scripts/test_runner.py --failing-only

# 质量门禁检查
python scripts/test_runner.py --quality-gate
```

**高级选项**:
```bash
# 生成测试矩阵（用于CI）
python scripts/test_runner.py --matrix

# 设置质量标准
python scripts/test_runner.py --quality-gate --coverage 25 --success-rate 95

# 输出结果到文件
python scripts/test_runner.py --output results.json
```

### 2. Quality Monitor - 质量监控器

**位置**: `tests/monitoring/test_quality_monitor.py`

**功能**:
- 自动收集覆盖率、性能、稳定性指标
- 生成A-F质量评分
- 提供改进建议

**基础用法**:
```bash
# 生成质量报告
python tests/monitoring/test_quality_monitor.py

# 静默模式
python tests/monitoring/test_quality_monitor.py --quiet

# 输出到指定文件
python tests/monitoring/test_quality_monitor.py --output my_report.json
```

**输出示例**:
```
📊 测试质量报告摘要
============================================================
🎯 总体评分: 85/100 (A)
📈 覆盖率: 25.3%
⚡ 执行时间: 45.2秒
🛡️ 稳定性: 99.5%

💡 改进建议:
  📊 覆盖率偏低，建议增加单元测试以达到25%基线
  ⚡ 最慢的测试需要优化: test_slow_operation (8.5s)
```

### 3. Quality Dashboard - 质量仪表板

**位置**: `tests/monitoring/quality_dashboard.py`

**功能**:
- Web界面展示质量指标
- 实时监控和趋势分析
- 交互式图表

**使用方法**:

**静态HTML报告**:
```bash
# 生成静态HTML文件
python tests/monitoring/quality_dashboard.py --static

# 指定输出文件名
python tests/monitoring/quality_dashboard.py --static -o dashboard.html
```

**Web服务器模式**:
```bash
# 启动Web服务器
python tests/monitoring/quality_dashboard.py --serve

# 指定端口
python tests/monitoring/quality_dashboard.py --serve --port 8080

# 调试模式
python tests/monitoring/quality_dashboard.py --serve --debug
```

**访问仪表板**:
- 打开浏览器访问 `http://localhost:8080`
- 查看质量指标、趋势图表、改进建议

### 4. Coverage Optimizer - 覆盖率优化器

**位置**: `tests/monitoring/coverage_optimization.py`

**功能**:
- 分析代码覆盖率
- 识别低覆盖率模块
- 生成测试模板

**基础用法**:
```bash
# 分析当前覆盖率
python tests/monitoring/coverage_optimization.py

# 生成优化计划
python tests/monitoring/coverage_optimization.py --plan
```

**生成测试模板**:
```bash
# 为特定模块生成测试模板
python tests/monitoring/coverage_optimization.py -m src.api.predictions

# 保存模板到文件
python tests/monitoring/coverage_optimization.py -m src.api.predictions -t test_predictions.py
```

**输出示例**:
```
📈 覆盖率优化计划
============================================================
📊 当前状态:
  当前覆盖率: 18.5%
  目标覆盖率: 30.0%
  需要提升: 11.5%

📋 执行阶段:
  1. 阶段1：关键模块覆盖
     模块数量: 5
     预期提升: +5.0%
     预估工时: 10小时
```

### 5. Report Generator - 报告生成器

**位置**: `scripts/generate_test_report.py`

**功能**:
- 生成综合质量报告
- 支持多种格式（JSON/HTML/Markdown）
- 包含趋势分析和行动项

**使用方法**:
```bash
# 生成完整报告
python scripts/generate_test_report.py

# 静默模式
python scripts/generate_test_report.py --quiet

# 指定输出目录
python scripts/generate_test_report.py --output ./reports
```

**生成的文件**:
- `test_quality_report_YYYYMMDD_HHMMSS.json` - JSON格式
- `test_quality_report_YYYYMMDD_HHMMSS.html` - HTML格式
- `test_quality_report_YYYYMMDD_HHMMSS.md` - Markdown格式

## ⌨️ 命令行工具详解

### 完整命令参考

#### test_runner.py
```bash
python scripts/test_runner.py [选项]

选项:
  --layers LAYERS         测试层级 (unit, integration, e2e)
  --parallel             并行执行测试
  --failing-only         仅运行失败的测试
  --quality-gate         执行质量门禁
  --coverage COVERAGE    最小覆盖率要求 (默认: 20)
  --success-rate RATE    最小成功率要求 (默认: 90)
  --matrix               输出测试矩阵
  --output OUTPUT        输出文件路径
```

#### test_quality_monitor.py
```bash
python tests/monitoring/test_quality_monitor.py [选项]

选项:
  --output OUTPUT        输出文件路径
  --quiet                静默模式
```

#### quality_dashboard.py
```bash
python tests/monitoring/quality_dashboard.py [选项]

选项:
  --static               生成静态HTML
  --output OUTPUT        输出文件名
  --serve                启动Web服务器
  --host HOST            服务器地址 (默认: 0.0.0.0)
  --port PORT            服务器端口 (默认: 8080)
  --debug                调试模式
```

#### coverage_optimization.py
```bash
python tests/monitoring/coverage_optimization.py [选项]

选项:
  --module MODULE         为指定模块生成测试模板
  --template TEMPLATE     保存模板到文件
  --plan                 生成优化计划
```

#### generate_test_report.py
```bash
python scripts/generate_test_report.py [选项]

选项:
  --output OUTPUT        输出目录
  --quiet                静默模式
```

### Make命令详解

```bash
# 测试执行
make test                 # 运行所有测试
make test.layered         # 分层测试执行
make test.unit            # 仅单元测试
make test.integration     # 仅集成测试
make test.e2e            # 仅E2E测试
make test.fast           # 快速测试（仅标记为fast的）

# 质量检查
make test.quality-gate    # 质量门禁检查
make test.monitor         # 生成监控报告
make test.report          # 生成综合报告
make test.coverage-plan   # 覆盖率优化计划

# 覆盖率
make test.cov            # 生成覆盖率报告
make cov.html            # 生成HTML覆盖率
make cov.enforce         # 强制覆盖率检查

# 工具和仪表板
make test.dashboard      # 启动质量仪表板（静态）

# 调试
make test.failed         # 仅运行失败的测试
make test.slow           # 仅运行慢速测试
make test.debug          # 调试模式运行测试
```

## 🌐 Web界面工具

### 质量仪表板功能

1. **实时指标展示**
   - 质量评分和等级
   - 测试覆盖率
   - 执行性能
   - 稳定性指标

2. **趋势图表**
   - 覆盖率趋势图
   - 性能趋势图
   - 历史数据对比

3. **改进建议**
   - 分类的改进建议
   - 优先级排序
   - 具体行动项

### 启动和使用

1. **快速启动**
```bash
# 方法1: 使用Make命令
make test.dashboard

# 方法2: 直接运行
python tests/monitoring/quality_dashboard.py --static
```

2. **访问仪表板**
```bash
# 找到生成的HTML文件
ls test_quality_dashboard_*.html

# 在浏览器中打开
# 或者使用本地服务器
python -m http.server 8000
# 访问 http://localhost:8000
```

3. **实时监控模式**
```bash
# 启动Web服务器
python tests/monitoring/quality_dashboard.py --serve

# 访问 http://localhost:8080
# 仪表板会自动刷新（每5分钟）
```

## 📊 监控和分析

### 日常监控工作流

1. **每日检查**
```bash
# 1. 运行测试
make test.layered

# 2. 查看质量
make test.monitor

# 3. 如果质量下降，查看详细报告
make test.report
```

2. **每周分析**
```bash
# 1. 生成综合报告
python scripts/generate_test_report.py

# 2. 查看优化计划
make test.coverage-plan

# 3. 更新测试策略
# 根据报告调整测试计划
```

3. **每月回顾**
```bash
# 1. 查看历史趋势
python tests/monitoring/quality_dashboard.py

# 2. 分析低覆盖率模块
python tests/monitoring/coverage_optimization.py

# 3. 制定改进计划
# 根据分析结果制定下月计划
```

### 关键指标解释

| 指标 | 说明 | 良好值 | 需关注 |
|------|------|--------|--------|
| **质量评分** | 综合评分(0-100) | 80+ | <60 |
| **覆盖率** | 代码覆盖率(%) | 20+ | <15 |
| **执行时间** | 测试总耗时(秒) | <60 | >120 |
| **稳定性** | 测试通过率(%) | 99+ | <95 |
| **成功率** | 成功测试比例(%) | 90+ | <85 |

### 诊断流程

1. **质量评分低**
```bash
# 查看详细报告
python tests/generate_test_report.py

# 检查具体问题
python tests/monitoring/test_quality_monitor.py

# 根据建议改进
```

2. **覆盖率不足**
```bash
# 分析覆盖率
make test.coverage-plan

# 生成测试模板
python tests/monitoring/coverage_optimization.py -m <module>

# 添加测试
```

3. **测试执行慢**
```bash
# 找出慢速测试
pytest --durations=10 tests/unit/

# 优化慢速测试
# - 减少Mock使用
# - 使用更快的测试数据
# - 并行执行
```

## 🛠️ 故障排除

### 常见问题

#### 1. 测试运行失败
```bash
# 问题：pytest command not found
# 解决：
source .venv/bin/activate
pip install pytest pytest-asyncio pytest-cov

# 问题：ModuleNotFoundError
# 解决：
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

#### 2. 覆盖率报告错误
```bash
# 问题：无法生成coverage.json
# 解决：
pip install pytest-cov
# 或
python -m pytest --cov=src --cov-report=json
```

#### 3. Web仪表板无法访问
```bash
# 问题：端口被占用
# 解决：
python tests/monitoring/quality_dashboard.py --serve --port 8081

# 问题：Flask未安装
# 解决：
pip install flask flask-cors matplotlib seaborn pandas
```

#### 4. 权限错误
```bash
# 问题：Permission denied
# 解决：
chmod +x scripts/*.py
chmod +x tests/monitoring/*.py
```

### 调试技巧

1. **查看详细输出**
```bash
# 使用-v选项
pytest -v tests/unit/

# 使用-s选项打印输出
pytest -s tests/unit/

# 使用--tb=short查看错误堆栈
pytest --tb=short tests/unit/
```

2. **运行特定测试**
```bash
# 运行特定文件
pytest tests/unit/api/test_cache.py

# 运行特定测试类
pytest tests/unit/api/test_cache.py::TestCacheAPI

# 运行特定测试方法
pytest tests/unit/api/test_cache.py::TestCacheAPI::test_cache_stats
```

3. **调试模式**
```bash
# 使用pdb调试
pytest --pdb tests/unit/api/test_cache.py

# 使用ipdb（需要安装）
pip install ipdb
pytest --pdb cls=IPdb.interactive
```

## 💡 最佳实践

### 开发工作流

1. **开始开发前**
```bash
# 1. 拉取最新代码
git pull

# 2. 激活环境
source .venv/bin/activate

# 3. 运行快速测试
make test.fast
```

2. **开发过程中**
```bash
# 1. 频繁运行单元测试
make test.unit

# 2. 保持高测试通过率
# 每提交前至少运行一次
```

3. **提交前检查**
```bash
# 1. 运行质量门禁
make test.quality-gate

# 2. 生成质量报告
make test.monitor

# 3. 确保所有测试通过
make test
```

### 性能优化

1. **并行测试**
```bash
# 使用pytest-xdist
pip install pytest-xdist

# 自动并行
pytest -n auto tests/unit/

# 指定进程数
pytest -n 4 tests/unit/
```

2. **选择性测试**
```bash
# 只运行修改的文件
pytest tests/unit/api/test_modified.py

# 使用标记
pytest -m "not slow"
pytest -m "unit and not integration"
```

3. **缓存测试数据**
```bash
# 使用pytest-cache
pip install pytest-cache

# 缓存数据库操作
pytest --cache-clear  # 清除缓存
pytest --cache-show   # 显示缓存统计
```

### 持续改进

1. **定期检查**
```bash
# 每周一
make test.report

# 每月1号
make test.coverage-plan
```

2. **团队协作**
- 分享测试最佳实践
- 代码审查关注测试质量
- 定期更新测试文档

3. **工具更新**
```bash
# 定期更新工具
pip install --upgrade pytest pytest-cov pytest-asyncio

# 检查工具新功能
pytest --version
```

## 📞 获取帮助

### 文档资源
- 本文档：`docs/testing/TEST_TOOLS_USER_GUIDE.md`
- 测试策略：`docs/testing/TEST_LAYERING_STRATEGY.md`
- 最佳实践：`docs/testing/TESTING_BEST_PRACTICES_GUIDE.md`

### 命令行帮助
```bash
# 查看所有Make命令
make help

# 查看pytest帮助
pytest --help

# 查看特定工具帮助
python scripts/test_runner.py --help
```

### 问题反馈
1. 查看错误日志
2. 检查依赖是否安装
3. 参考故障排除部分
4. 创建Issue描述问题

---

**文档版本**: 1.0
**最后更新**: 2025-01-03
**维护者**: 开发团队

祝您使用愉快！如果需要帮助，请随时联系我们。