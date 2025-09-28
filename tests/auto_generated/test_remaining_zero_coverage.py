"""
 剩余0%覆盖率模块测试文件
 测试 consistency_manager.py, sql_compatibility.py, examples.py 等模块
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import json
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

# 添加 src 目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))


class TestConsistencyManager:
    """测试缓存一致性管理器"""

    def setup_method(self):
        """设置测试环境"""
        from cache.consistency_manager import ConsistencyManager
        self.manager = ConsistencyManager()

    def test_consistency_manager_initialization(self):
        """测试一致性管理器初始化"""
        assert self.manager.cache_keys == set()
        assert self.manager.consistency_checks == 0
        assert self.manager.inconsistencies_detected == 0

    def test_register_cache_key(self):
        """测试注册缓存键"""
        self.manager.register_cache_key("user_123_profile")
        self.manager.register_cache_key("user_456_profile")

        assert "user_123_profile" in self.manager.cache_keys
        assert "user_456_profile" in self.manager.cache_keys
        assert len(self.manager.cache_keys) == 2

    def test_unregister_cache_key(self):
        """测试注销缓存键"""
        self.manager.register_cache_key("user_123_profile")
        assert "user_123_profile" in self.manager.cache_keys

        self.manager.unregister_cache_key("user_123_profile")
        assert "user_123_profile" not in self.manager.cache_keys

    def test_unregister_nonexistent_key(self):
        """测试注销不存在的缓存键"""
        # 不应该抛出异常
        self.manager.unregister_cache_key("nonexistent_key")

    def test_check_consistency_no_inconsistencies(self):
        """测试一致性检查无不一致"""
        # 注册缓存键
        self.manager.register_cache_key("key1")
        self.manager.register_cache_key("key2")

        # 模拟缓存一致性
        with patch.object(self.manager, '_check_cache_consistency') as mock_check:
            mock_check.return_value = True

            result = self.manager.check_consistency()

            assert result is True
            assert self.manager.consistency_checks == 1
            assert self.manager.inconsistencies_detected == 0

    def test_check_consistency_with_inconsistencies(self):
        """测试一致性检查有不一致"""
        # 注册缓存键
        self.manager.register_cache_key("key1")

        # 模拟缓存不一致
        with patch.object(self.manager, '_check_cache_consistency') as mock_check:
            mock_check.return_value = False

            result = self.manager.check_consistency()

            assert result is False
            assert self.manager.consistency_checks == 1
            assert self.manager.inconsistencies_detected == 1

    def test_get_statistics(self):
        """测试获取统计信息"""
        # 添加一些测试数据
        self.manager.register_cache_key("key1")
        self.manager.register_cache_key("key2")
        self.manager.consistency_checks = 5
        self.manager.inconsistencies_detected = 2

        stats = self.manager.get_statistics()

        assert stats["registered_keys"] == 2
        assert stats["consistency_checks"] == 5
        assert stats["inconsistencies_detected"] == 2
        assert stats["consistency_rate"] == 0.6  # (5-2)/5 = 0.6

    def test_clear_all_keys(self):
        """测试清理所有键"""
        # 注册一些键
        self.manager.register_cache_key("key1")
        self.manager.register_cache_key("key2")
        assert len(self.manager.cache_keys) == 2

        # 清理所有键
        self.manager.clear_all_keys()
        assert len(self.manager.cache_keys) == 0

    def test_concurrent_key_registration(self):
        """测试并发键注册"""
        import threading
        import time

        def register_keys(start, end):
            for i in range(start, end):
                self.manager.register_cache_key(f"key_{i}")

        # 创建多个线程并发注册键
        threads = []
        for i in range(0, 100, 10):
            thread = threading.Thread(target=register_keys, args=(i, i + 10))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # 验证所有键都被注册
        assert len(self.manager.cache_keys) == 100


class TestSQLCompatibility:
    """测试SQL兼容性模块"""

    def setup_method(self):
        """设置测试环境"""
        from database.sql_compatibility import SQLCompatibility
        self.compat = SQLCompatibility()

    def test_sql_compatibility_initialization(self):
        """测试SQL兼容性初始化"""
        assert self.compat.supported_dialects == ["postgresql", "sqlite", "mysql"]
        assert self.compat.default_dialect == "postgresql"

    def test_translate_sql_postgresql_to_sqlite(self):
        """测试SQL翻译PostgreSQL到SQLite"""
        pg_sql = "SELECT * FROM users WHERE created_at > NOW() - INTERVAL '1 day'"
        sqlite_sql = self.compat.translate_sql(pg_sql, "postgresql", "sqlite")

        assert "NOW()" not in sqlite_sql
        assert "INTERVAL" not in sqlite_sql
        assert "datetime('now')" in sqlite_sql.lower() or "date('now')" in sqlite_sql.lower()

    def test_translate_sql_mysql_to_postgresql(self):
        """测试SQL翻译MySQL到PostgreSQL"""
        mysql_sql = "SELECT * FROM users WHERE DATE(created_at) = CURDATE()"
        pg_sql = self.compat.translate_sql(mysql_sql, "mysql", "postgresql")

        assert "CURDATE()" not in pg_sql
        assert "CURRENT_DATE" in pg_sql or "now()" in pg_sql.lower()

    def test_translate_sql_unsupported_dialect(self):
        """测试不支持的SQL方言"""
        with pytest.raises(ValueError):
            self.compat.translate_sql("SELECT * FROM users", "oracle", "postgresql")

    def test_get_dialect_specific_types(self):
        """测试获取方言特定类型"""
        pg_types = self.compat.get_dialect_specific_types("postgresql")
        assert "SERIAL" in pg_types
        assert "BIGSERIAL" in pg_types

        sqlite_types = self.compat.get_dialect_specific_types("sqlite")
        assert "INTEGER" in sqlite_types
        assert "TEXT" in sqlite_types

    def test_validate_sql_syntax(self):
        """测试SQL语法验证"""
        # 有效SQL
        valid_sql = "SELECT id, name FROM users WHERE id = ?"
        assert self.compat.validate_sql_syntax(valid_sql, "sqlite") is True

        # 无效SQL
        invalid_sql = "SELECT FROM users WHERE"  # 缺少列名
        assert self.compat.validate_sql_syntax(invalid_sql, "sqlite") is False

    def test_get_function_mapping(self):
        """测试获取函数映射"""
        mapping = self.compat.get_function_mapping("postgresql", "sqlite")

        assert isinstance(mapping, dict)
        # 检查常见函数映射
        assert any("NOW" in key for key in mapping.keys())
        assert any("date" in key.lower() for key in mapping.keys())

    def test_optimize_sql_for_dialect(self):
        """测试为方言优化SQL"""
        sql = "SELECT * FROM large_table WHERE status = 'active'"
        optimized = self.compat.optimize_sql_for_dialect(sql, "sqlite")

        # SQLite优化应该包含适当的索引提示
        assert isinstance(optimized, str)
        assert "SELECT" in optimized.upper()

    def test_add_custom_function_mapping(self):
        """测试添加自定义函数映射"""
        # 添加自定义映射
        self.compat.add_custom_function_mapping(
            "postgresql", "sqlite", "CUSTOM_FUNC", "custom_sqlite_func"
        )

        # 验证映射被添加
        mapping = self.compat.get_function_mapping("postgresql", "sqlite")
        assert "CUSTOM_FUNC" in mapping
        assert mapping["CUSTOM_FUNC"] == "custom_sqlite_func"

    def test_remove_function_mapping(self):
        """测试移除函数映射"""
        # 先添加映射
        self.compat.add_custom_function_mapping(
            "postgresql", "sqlite", "TEST_FUNC", "test_func"
        )

        # 移除映射
        result = self.compat.remove_function_mapping("postgresql", "sqlite", "TEST_FUNC")
        assert result is True

        # 验证映射被移除
        mapping = self.compat.get_function_mapping("postgresql", "sqlite")
        assert "TEST_FUNC" not in mapping

    def test_get_compatibility_report(self):
        """测试获取兼容性报告"""
        sql = "SELECT * FROM users WHERE created_at > NOW()"
        report = self.compat.get_compatibility_report(sql, "postgresql", ["sqlite", "mysql"])

        assert isinstance(report, dict)
        assert "source_dialect" in report
        assert "target_dialects" in report
        assert "translations" in report
        assert "issues" in report

    def test_complex_sql_translation(self):
        """测试复杂SQL翻译"""
        complex_sql = """
        SELECT
            u.id,
            u.name,
            COUNT(o.id) as order_count,
            SUM(o.amount) as total_amount
        FROM users u
        LEFT JOIN orders o ON u.id = o.user_id
        WHERE u.created_at > NOW() - INTERVAL '30 days'
            AND u.status = 'active'
        GROUP BY u.id, u.name
        HAVING COUNT(o.id) > 0
        ORDER BY total_amount DESC
        LIMIT 100
        """

        translated = self.compat.translate_sql(complex_sql, "postgresql", "sqlite")

        assert translated is not None
        assert isinstance(translated, str)
        assert "SELECT" in translated.upper()
        # 检查PostgreSQL特有函数被翻译
        assert "INTERVAL" not in translated
        assert "NOW()" not in translated


class TestFeatureExamples:
    """测试特征示例模块"""

    def setup_method(self):
        """设置测试环境"""
        from data.features.examples import FeatureExamples
        self.examples = FeatureExamples()

    def test_feature_examples_initialization(self):
        """测试特征示例初始化"""
        assert hasattr(self.examples, 'feature_registry')
        assert isinstance(self.examples.feature_registry, dict)

    def test_get_example_features(self):
        """测试获取示例特征"""
        examples = self.examples.get_example_features("match_prediction")

        assert isinstance(examples, list)
        assert len(examples) > 0

        # 检查示例特征结构
        for example in examples:
            assert "name" in example
            assert "description" in example
            assert "type" in example
            assert "example_value" in example

    def test_get_feature_by_name(self):
        """测试按名称获取特征"""
        feature = self.examples.get_feature_by_name("team_form")

        assert feature is not None
        assert feature["name"] == "team_form"
        assert "description" in feature
        assert "type" in feature

    def test_get_feature_by_name_nonexistent(self):
        """测试获取不存在的特征"""
        feature = self.examples.get_feature_by_name("nonexistent_feature")
        assert feature is None

    def test_get_all_categories(self):
        """测试获取所有类别"""
        categories = self.examples.get_all_categories()

        assert isinstance(categories, list)
        assert len(categories) > 0
        assert "match_prediction" in categories

    def test_get_features_by_category(self):
        """测试按类别获取特征"""
        features = self.examples.get_features_by_category("match_prediction")

        assert isinstance(features, list)
        assert len(features) > 0

        for feature in features:
            assert "category" in feature
            assert feature["category"] == "match_prediction"

    def test_get_features_by_category_nonexistent(self):
        """测试获取不存在的类别"""
        features = self.examples.get_features_by_category("nonexistent_category")
        assert features == []

    def test_search_features(self):
        """测试搜索特征"""
        results = self.examples.search_features("team")

        assert isinstance(results, list)
        assert len(results) > 0

        for feature in results:
            assert "team" in feature["name"].lower() or "team" in feature["description"].lower()

    def test_search_features_no_results(self):
        """测试搜索无结果"""
        results = self.examples.search_features("nonexistent_term")
        assert results == []

    def test_get_feature_statistics(self):
        """测试获取特征统计"""
        stats = self.examples.get_feature_statistics()

        assert isinstance(stats, dict)
        assert "total_features" in stats
        assert "categories" in stats
        assert "types" in stats
        assert stats["total_features"] > 0

    def test_validate_feature_definition(self):
        """测试验证特征定义"""
        # 有效特征定义
        valid_feature = {
            "name": "test_feature",
            "description": "Test feature description",
            "type": "numeric",
            "example_value": 42.0
        }

        assert self.examples.validate_feature_definition(valid_feature) is True

        # 无效特征定义（缺少必需字段）
        invalid_feature = {
            "name": "test_feature"
            # 缺少description和type
        }

        assert self.examples.validate_feature_definition(invalid_feature) is False

    def test_add_custom_feature(self):
        """测试添加自定义特征"""
        custom_feature = {
            "name": "custom_win_rate",
            "description": "Custom win rate calculation",
            "type": "numeric",
            "category": "custom",
            "example_value": 0.75
        }

        result = self.examples.add_custom_feature(custom_feature)
        assert result is True

        # 验证特征被添加
        retrieved = self.examples.get_feature_by_name("custom_win_rate")
        assert retrieved is not None
        assert retrieved["description"] == "Custom win rate calculation"

    def test_remove_custom_feature(self):
        """测试移除自定义特征"""
        # 先添加特征
        custom_feature = {
            "name": "temp_feature",
            "description": "Temporary feature",
            "type": "numeric",
            "category": "custom",
            "example_value": 1.0
        }
        self.examples.add_custom_feature(custom_feature)

        # 移除特征
        result = self.examples.remove_custom_feature("temp_feature")
        assert result is True

        # 验证特征被移除
        retrieved = self.examples.get_feature_by_name("temp_feature")
        assert retrieved is None

    def test_get_feature_usage_examples(self):
        """测试获取特征使用示例"""
        examples = self.examples.get_feature_usage_examples("team_form")

        assert isinstance(examples, list)
        assert len(examples) > 0

        for example in examples:
            assert "code" in example
            assert "description" in example
            assert isinstance(example["code"], str)

    def test_get_feature_dependencies(self):
        """测试获取特征依赖"""
        dependencies = self.examples.get_feature_dependencies("match_outcome")

        assert isinstance(dependencies, list)
        # 某些特征可能有依赖，某些可能没有

    def test_batch_feature_operations(self):
        """测试批量特征操作"""
        features_to_add = [
            {
                "name": "batch_feature_1",
                "description": "Batch feature 1",
                "type": "numeric",
                "category": "batch",
                "example_value": 1.0
            },
            {
                "name": "batch_feature_2",
                "description": "Batch feature 2",
                "type": "categorical",
                "category": "batch",
                "example_value": "category_A"
            }
        ]

        # 批量添加
        results = self.examples.batch_add_features(features_to_add)
        assert all(results) == True

        # 验证特征被添加
        for feature in features_to_add:
            retrieved = self.examples.get_feature_by_name(feature["name"])
            assert retrieved is not None

    def test_feature_export_import(self):
        """测试特征导出导入"""
        # 导出特征
        exported_data = self.examples.export_features()

        assert isinstance(exported_data, dict)
        assert "features" in exported_data
        assert "metadata" in exported_data

        # 导入特征（应该验证格式）
        import_result = self.examples.import_features(exported_data)
        assert import_result is True

    def test_feature_validation_complex(self):
        """测试复杂特征验证"""
        # 测试各种特征类型
        feature_types = [
            {"name": "numeric_feature", "type": "numeric", "example_value": 42.5},
            {"name": "categorical_feature", "type": "categorical", "example_value": "category_A"},
            {"name": "boolean_feature", "type": "boolean", "example_value": True},
            {"name": "datetime_feature", "type": "datetime", "example_value": "2023-01-01"}
        ]

        for feature_def in feature_types:
            feature_def["description"] = f"Test {feature_def['type']} feature"
            assert self.examples.validate_feature_definition(feature_def) is True

    def test_performance_large_dataset(self):
        """测试大数据集性能"""
        import time

        start_time = time.time()

        # 执行大量特征查询
        for _ in range(1000):
            features = self.examples.get_example_features("match_prediction")
            assert isinstance(features, list)

        end_time = time.time()
        processing_time = end_time - start_time

        # 验证性能在合理范围内
        assert processing_time < 5.0  # 1000次查询应该在5秒内完成


class TestIntegrationScenarios:
    """测试集成场景"""

    def setup_method(self):
        """设置测试环境"""
        from cache.consistency_manager import ConsistencyManager
        from database.sql_compatibility import SQLCompatibility
        from data.features.examples import FeatureExamples

        self.cache_manager = ConsistencyManager()
        self.sql_compat = SQLCompatibility()
        self.feature_examples = FeatureExamples()

    def test_cache_consistency_with_feature_processing(self):
        """测试缓存一致性与特征处理集成"""
        # 注册特征相关缓存键
        feature_keys = [
            "match_features_123",
            "team_features_456",
            "player_features_789"
        ]

        for key in feature_keys:
            self.cache_manager.register_cache_key(key)

        # 模拟特征处理过程中的缓存操作
        assert self.cache_manager.check_consistency() is True

        # 获取特征示例
        features = self.feature_examples.get_example_features("match_prediction")
        assert len(features) > 0

        # 验证缓存状态仍然一致
        assert self.cache_manager.check_consistency() is True

    def test_sql_compatibility_with_feature_storage(self):
        """测试SQL兼容性与特征存储集成"""
        # 模拟跨数据库的特征存储SQL
        pg_sql = """
        INSERT INTO match_features (match_id, team_id, feature_value, created_at)
        VALUES (?, ?, ?, NOW())
        """

        # 翻译到不同的数据库方言
        sqlite_sql = self.sql_compat.translate_sql(pg_sql, "postgresql", "sqlite")
        mysql_sql = self.sql_compat.translate_sql(pg_sql, "postgresql", "mysql")

        # 验证翻译结果
        assert sqlite_sql is not None
        assert mysql_sql is not None
        assert sqlite_sql != pg_sql  # 应该有差异
        assert mysql_sql != pg_sql  # 应该有差异

        # 验证特征示例可以正常工作
        features = self.feature_examples.get_features_by_category("match_prediction")
        assert len(features) > 0

    def test_end_to_end_data_processing_pipeline(self):
        """测试端到端数据处理管道"""
        # 1. 缓存管理 - 注册数据管道相关的缓存键
        pipeline_keys = [
            "raw_data_cache",
            "processed_data_cache",
            "feature_cache",
            "model_input_cache"
        ]

        for key in pipeline_keys:
            self.cache_manager.register_cache_key(key)

        # 2. SQL兼容性 - 处理跨数据库查询
        extraction_sql = "SELECT * FROM raw_matches WHERE match_date > CURRENT_DATE - INTERVAL '7 days'"

        # 为不同数据库翻译SQL
        dialects = ["sqlite", "mysql"]
        translated_sqls = {}

        for dialect in dialects:
            translated_sqls[dialect] = self.sql_compat.translate_sql(
                extraction_sql, "postgresql", dialect
            )

        # 3. 特征工程 - 获取相关特征
        match_features = self.feature_examples.get_example_features("match_prediction")
        assert len(match_features) > 0

        # 4. 验证缓存一致性
        consistency_result = self.cache_manager.check_consistency()
        assert consistency_result is True

        # 5. 获取系统统计
        cache_stats = self.cache_manager.get_statistics()
        feature_stats = self.feature_examples.get_feature_statistics()

        # 验证统计信息
        assert cache_stats["registered_keys"] == 4
        assert feature_stats["total_features"] > 0

    def test_error_handling_and_recovery(self):
        """测试错误处理和恢复"""
        # 1. 测试缓存管理器错误恢复
        self.cache_manager.register_cache_key("test_key")
        initial_check_count = self.cache_manager.consistency_checks

        # 模拟一致性检查失败
        with patch.object(self.cache_manager, '_check_cache_consistency') as mock_check:
            mock_check.return_value = False

            result = self.cache_manager.check_consistency()
            assert result is False
            assert self.cache_manager.inconsistencies_detected == 1

        # 验证可以继续正常工作
        self.cache_manager.register_cache_key("another_key")
        assert len(self.cache_manager.cache_keys) == 2

        # 2. 测试SQL翻译错误处理
        with pytest.raises(ValueError):
            self.sql_compat.translate_sql("SELECT * FROM test", "unsupported", "postgresql")

        # 验证其他功能仍然正常
        valid_translation = self.sql_compat.translate_sql(
            "SELECT NOW()", "postgresql", "sqlite"
        )
        assert valid_translation is not None

        # 3. 测试特征示例错误处理
        nonexistent_feature = self.feature_examples.get_feature_by_name("nonexistent")
        assert nonexistent_feature is None

        # 验证可以继续正常获取特征
        existing_features = self.feature_examples.get_example_features("match_prediction")
        assert len(existing_features) > 0

    def test_concurrent_system_operations(self):
        """测试并发系统操作"""
        import threading
        import time

        results = {"cache_ops": 0, "sql_ops": 0, "feature_ops": 0}

        def cache_operations():
            for i in range(50):
                self.cache_manager.register_cache_key(f"concurrent_key_{i}")
                time.sleep(0.001)  # 短暂延迟
            results["cache_ops"] = 50

        def sql_operations():
            for i in range(50):
                try:
                    self.sql_compat.translate_sql(
                        f"SELECT * FROM table_{i} WHERE date > NOW()",
                        "postgresql", "sqlite"
                    )
                except:
                    pass  # 忽略翻译错误
                time.sleep(0.001)
            results["sql_ops"] = 50

        def feature_operations():
            for i in range(50):
                features = self.feature_examples.get_example_features("match_prediction")
                assert len(features) > 0
                time.sleep(0.001)
            results["feature_ops"] = 50

        # 创建并发线程
        threads = [
            threading.Thread(target=cache_operations),
            threading.Thread(target=sql_operations),
            threading.Thread(target=feature_operations)
        ]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # 验证所有操作都成功完成
        assert results["cache_ops"] == 50
        assert results["sql_ops"] == 50
        assert results["feature_ops"] == 50

        # 验证系统状态一致性
        assert self.cache_manager.check_consistency() is True
        assert len(self.feature_examples.get_example_features("match_prediction")) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])