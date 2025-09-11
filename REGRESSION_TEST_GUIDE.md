# 🎯 最小回归测试指南

## 📋 **阶段1: 最小核心回归测试**

立即运行以下3个关键测试来验证主要修复效果：

### 🔍 **测试 1.1: ERROR 测试 (数据库连接相关)**
```bash
# 测试模型训练工作流 - 验证数据库连接初始化修复
pytest tests/test_model_training/test_training_workflow.py::TestModelTrainingWorkflow::test_model_training_workflow -v --tb=short

# 期望结果: 通过 ✅ (如果失败，检查数据库管理器初始化)
```

### 🔍 **测试 1.2: AttributeError 测试 (异步数据库fixture)**
```bash
# 测试数据库索引 - 验证异步fixture修复
pytest tests/test_database_performance_optimization.py::TestDatabaseIndexes::test_index_existence -v --tb=short

# 期望结果: 通过 ✅ (如果失败，检查 @pytest_asyncio.fixture 装饰器)
```

### 🔍 **测试 1.3: 500错误测试 (API Mock配置)**
```bash
# 测试API特征获取 - 验证Mock配置修复
pytest tests/test_features/test_api_features.py::TestFeaturesAPI::test_get_match_features_success -v --tb=short

# 期望结果: 通过 ✅ (如果失败，检查Mock配置和SQL构造函数)
```

### 🚦 **阶段1一键执行命令**
```bash
# 运行所有核心回归测试
echo "🔍 核心回归测试开始..." && \
pytest tests/test_model_training/test_training_workflow.py::TestModelTrainingWorkflow::test_model_training_workflow -v --tb=short && \
echo "✅ 测试1通过" && \
pytest tests/test_database_performance_optimization.py::TestDatabaseIndexes::test_index_existence -v --tb=short && \
echo "✅ 测试2通过" && \
pytest tests/test_features/test_api_features.py::TestFeaturesAPI::test_get_match_features_success -v --tb=short && \
echo "🎉 核心回归测试全部通过！"
```

---

## 📋 **阶段2: 扩展模块测试**

如果阶段1全部通过，运行以下测试组：

### 🔍 **测试 2.1: 特征存储模块测试**
```bash
# 测试特征存储相关功能 (排除原始问题文件)
pytest tests/test_features/ -v --tb=short -k "not test_feature_store.py"

# 如果使用了修复版本，可以运行:
pytest tests/test_features/test_feature_store_fixed.py -v --tb=short
```

### 🔍 **测试 2.2: 数据库模型集成测试**
```bash
# 测试模型字段名修复效果
pytest tests/test_model_integration.py -v --tb=short

# 期望结果: 无 TypeError: 'name' is an invalid keyword argument
```

### 🔍 **测试 2.3: 数据库性能优化测试**
```bash
# 测试异步数据库操作修复
pytest tests/test_database_performance_optimization.py -v --tb=short

# 期望结果: 无 'async_generator' object has no attribute 'execute'
```

### 🚦 **阶段2一键执行命令**
```bash
echo "🔍 扩展模块测试开始..." && \
pytest tests/test_features/ -v --tb=short -k "not test_feature_store.py" && \
pytest tests/test_model_integration.py -v --tb=short && \
pytest tests/test_database_performance_optimization.py -v --tb=short && \
echo "🎉 扩展模块测试完成！"
```

---

## 📋 **阶段3: 完整测试套件验证**

### 🔍 **测试 3.1: 渐进式完整测试**
```bash
# 运行完整测试套件，但排除已知问题文件，限制失败数量
pytest tests/ -v --tb=short -x --maxfail=5 --ignore=tests/test_features/test_feature_store.py

# -x: 遇到第一个失败就停止
# --maxfail=5: 最多允许5个失败
# --ignore: 排除原始问题文件
```

### 🔍 **测试 3.2: 分类别测试验证**
```bash
# API相关测试
pytest tests/test_api/ -v --tb=short

# 数据库相关测试
pytest tests/test_database* tests/test_model* -v --tb=short

# 特征相关测试
pytest tests/test_features/ -v --tb=short
```

---

## 📋 **阶段4: make test 恢复**

### 🔍 **准备工作**
```bash
# 1. 确保上下文加载正常
make context

# 2. 检查测试配置
cat pytest.ini

# 3. 检查是否有测试数据需求
ls tests/fixtures/ tests/data/ 2>/dev/null || echo "无测试数据目录"
```

### 🔍 **尝试 make test**
```bash
# 设置超时，避免无限等待
timeout 300 make test

# 如果失败，查看具体错误
make test 2>&1 | tee make_test_debug.log
```

---

## 🔧 **可能需要的额外修复**

### **Mock数据更新**
如果测试失败提示数据相关问题：
```bash
# 检查是否需要更新测试fixture数据
find tests/ -name "*.json" -o -name "*.yaml" -o -name "*.sql" | head -10

# 检查数据库seed文件
find . -name "*seed*" -o -name "*fixture*" | grep -v __pycache__
```

### **环境配置检查**
```bash
# 检查测试环境变量
env | grep -i test

# 检查数据库配置
cat config/test_config.py 2>/dev/null || echo "测试配置文件不存在"

# 检查是否需要数据库迁移
ls migrations/ 2>/dev/null || echo "无迁移目录"
```

---

## 🚀 **快速执行脚本**

将以下内容保存为 `run_regression_tests.sh`:

```bash
#!/bin/bash
set -e

echo "🚀 开始最小回归测试..."

# 阶段1: 核心回归测试
echo "📍 阶段1: 核心回归测试"
pytest tests/test_model_training/test_training_workflow.py::TestModelTrainingWorkflow::test_model_training_workflow -v --tb=short
pytest tests/test_database_performance_optimization.py::TestDatabaseIndexes::test_index_existence -v --tb=short
pytest tests/test_features/test_api_features.py::TestFeaturesAPI::test_get_match_features_success -v --tb=short

echo "✅ 阶段1完成"

# 阶段2: 扩展测试
echo "📍 阶段2: 扩展模块测试"
pytest tests/test_features/ -v --tb=short -k "not test_feature_store.py"
pytest tests/test_model_integration.py -v --tb=short
pytest tests/test_database_performance_optimization.py -v --tb=short

echo "✅ 阶段2完成"

# 阶段3: 尝试make test
echo "📍 阶段3: 尝试make test"
timeout 300 make test || echo "make test需要进一步修复"

echo "🎉 回归测试完成！"
```

**使用方法**:
```bash
chmod +x run_regression_tests.sh
./run_regression_tests.sh
```

---

## 📊 **成功标准**

- **阶段1通过**: 核心修复生效，可以进行阶段2
- **阶段2通过**: 大部分功能正常，可以尝试完整测试
- **阶段3通过**: 系统基本稳定，可以尝试make test
- **make test通过**: 完全恢复正常开发流程

每个阶段失败时，请参考错误信息和之前的修复指南进行针对性修复！
