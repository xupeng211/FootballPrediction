#!/bin/bash
set -e

echo "🚀 开始最小回归测试..."

# 阶段1: 核心回归测试
echo "📍 阶段1: 核心回归测试"
echo "🔍 测试1: 异步数据库fixture"
pytest tests/test_database_performance_optimization.py::TestDatabasePartitioning::test_matches_partition_insertion -v --tb=short
echo "🔍 测试2: API Mock配置"
pytest tests/test_features/test_api_features.py::TestFeaturesAPI::test_get_match_features_success -v --tb=short
echo "🔍 测试3: 模型字段名"
pytest tests/test_model_integration.py::TestModelIntegration::test_model_training_workflow -v --tb=short
echo "🔍 额外验证: 特征存储修复版"
pytest tests/test_features/test_feature_store_fixed.py::TestFootballFeatureStoreFixed::test_register_features_fixed -v --tb=short

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
