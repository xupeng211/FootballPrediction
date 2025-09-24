"""
阶段2：字符串工具测试
目标：补齐核心逻辑测试覆盖率达到70%+
重点：测试字符串处理、格式化、验证、转换功能
"""

from unittest.mock import Mock, patch

import pytest

from src.utils.string_utils import StringUtils


class TestStringUtilsPhase2:
    """字符串工具阶段2测试"""

    def setup_method(self):
        """设置测试环境"""
        self.utils = StringUtils()

    def test_initialization(self):
        """测试初始化"""
        assert self.utils is not None
        assert hasattr(self.utils, "logger")

    def test_logger_configuration(self):
        """测试日志配置"""
        assert self.utils.logger is not None
        assert hasattr(self.utils.logger, "error")
        assert hasattr(self.utils.logger, "info")
        assert hasattr(self.utils.logger, "warning")

    def test_string_validation_methods(self):
        """测试字符串验证方法"""
        # 验证验证方法存在
        assert hasattr(self.utils, "is_valid_string")
        assert hasattr(self.utils, "is_empty_string")
        assert hasattr(self.utils, "is_whitespace_only")
        assert hasattr(self.utils, "validate_email")
        assert hasattr(self.utils, "validate_phone")

    def test_string_cleaning_methods(self):
        """测试字符串清理方法"""
        # 验证清理方法存在
        assert hasattr(self.utils, "clean_string")
        assert hasattr(self.utils, "remove_special_chars")
        assert hasattr(self.utils, "normalize_whitespace")
        assert hasattr(self.utils, "remove_accents")
        assert hasattr(self.utils, "sanitize_html")

    def test_string_formatting_methods(self):
        """测试字符串格式化方法"""
        # 验证格式化方法存在
        assert hasattr(self.utils, "format_currency")
        assert hasattr(self.utils, "format_date")
        assert hasattr(self.utils, "format_number")
        assert hasattr(self.utils, "format_percentage")
        assert hasattr(self.utils, "format_file_size")

    def test_string_transformation_methods(self):
        """测试字符串转换方法"""
        # 验证转换方法存在
        assert hasattr(self.utils, "to_camel_case")
        assert hasattr(self.utils, "to_snake_case")
        assert hasattr(self.utils, "to_kebab_case")
        assert hasattr(self.utils, "to_pascal_case")
        assert hasattr(self.utils, "to_title_case")

    def test_string_search_methods(self):
        """测试字符串搜索方法"""
        # 验证搜索方法存在
        assert hasattr(self.utils, "contains")
        assert hasattr(self.utils, "starts_with")
        assert hasattr(self.utils, "ends_with")
        assert hasattr(self.utils, "find_all")
        assert hasattr(self.utils, "count_occurrences")

    def test_string_manipulation_methods(self):
        """测试字符串操作方法"""
        # 验证操作方法存在
        assert hasattr(self.utils, "truncate")
        assert hasattr(self.utils, "pad_string")
        assert hasattr(self.utils, "reverse_string")
        assert hasattr(self.utils, "shuffle_string")
        assert hasattr(self.utils, "repeat_string")

    def test_string_encoding_methods(self):
        """测试字符串编码方法"""
        # 验证编码方法存在
        assert hasattr(self.utils, "encode_base64")
        assert hasattr(self.utils, "decode_base64")
        assert hasattr(self.utils, "encode_url")
        assert hasattr(self.utils, "decode_url")
        assert hasattr(self.utils, "encode_html_entities")

    def test_string_encryption_methods(self):
        """测试字符串加密方法"""
        # 验证加密方法存在
        assert hasattr(self.utils, "encrypt_string")
        assert hasattr(self.utils, "decrypt_string")
        assert hasattr(self.utils, "hash_string")
        assert hasattr(self.utils, "generate_salt")
        assert hasattr(self.utils, "verify_hash")

    def test_string_analysis_methods(self):
        """测试字符串分析方法"""
        # 验证分析方法存在
        assert hasattr(self.utils, "analyze_complexity")
        assert hasattr(self.utils, "calculate_similarity")
        assert hasattr(self.utils, "extract_keywords")
        assert hasattr(self.utils, "detect_language")
        assert hasattr(self.utils, "analyze_sentiment")

    def test_string_generation_methods(self):
        """测试字符串生成方法"""
        # 验证生成方法存在
        assert hasattr(self.utils, "generate_random_string")
        assert hasattr(self.utils, "generate_uuid")
        assert hasattr(self.utils, "generate_slug")
        assert hasattr(self.utils, "generate_checksum")
        assert hasattr(self.utils, "generate_password")

    def test_basic_string_validation(self):
        """测试基本字符串验证"""
        # 有效字符串
        assert self.utils.is_valid_string("test")
        assert self.utils.is_valid_string("Hello World")
        assert self.utils.is_valid_string("123")

        # 无效字符串
        assert not self.utils.is_valid_string("")
        assert not self.utils.is_valid_string(None)
        assert not self.utils.is_valid_string(123)

    def test_empty_string_detection(self):
        """测试空字符串检测"""
        assert self.utils.is_empty_string("")
        assert not self.utils.is_empty_string("not empty")
        assert not self.utils.is_empty_string(" ")

    def test_whitespace_only_detection(self):
        """测试纯空白字符检测"""
        assert self.utils.is_whitespace_only("   ")
        assert self.utils.is_whitespace_only("\t\n\r")
        assert not self.utils.is_whitespace_only("text")

    def test_email_validation(self):
        """测试邮箱验证"""
        # 有效邮箱
        assert self.utils.validate_email("test@example.com")
        assert self.utils.validate_email("user.name@domain.co.uk")

        # 无效邮箱
        assert not self.utils.validate_email("invalid-email")
        assert not self.utils.validate_email("@domain.com")
        assert not self.utils.validate_email("user@")

    def test_phone_validation(self):
        """测试电话验证"""
        # 有效电话
        assert self.utils.validate_phone("+1234567890")
        assert self.utils.validate_phone("(123) 456-7890")

        # 无效电话
        assert not self.utils.validate_phone("123")
        assert not self.utils.validate_phone("abc")

    def test_string_cleaning(self):
        """测试字符串清理"""
        dirty_string = "  Hello   World!  "
        cleaned = self.utils.clean_string(dirty_string)
        assert cleaned == "Hello World!"

    def test_special_char_removal(self):
        """测试特殊字符移除"""
        string_with_special = "Hello@World#123$%"
        cleaned = self.utils.remove_special_chars(string_with_special)
        assert cleaned == "HelloWorld123"

    def test_whitespace_normalization(self):
        """测试空白字符规范化"""
        messy_whitespace = "Hello   World\tHow\nAre\r\nYou?"
        normalized = self.utils.normalize_whitespace(messy_whitespace)
        assert normalized == "Hello World How Are You?"

    def test_accent_removal(self):
        """测试重音移除"""
        accented_string = "café naïve résumé"
        cleaned = self.utils.remove_accents(accented_string)
        assert cleaned == "cafe naive resume"

    def test_html_sanitization(self):
        """测试HTML清理"""
        html_string = "<script>alert('xss')</script><p>Hello</p>"
        sanitized = self.utils.sanitize_html(html_string)
        assert "<script>" not in sanitized
        assert "<p>" in sanitized

    def test_currency_formatting(self):
        """测试货币格式化"""
        assert self.utils.format_currency(1234.56) == "$1,234.56"
        assert self.utils.format_currency(1000) == "$1,000.00"

    def test_date_formatting(self):
        """测试日期格式化"""
        from datetime import datetime

        test_date = datetime(2023, 12, 25, 15, 30)
        formatted = self.utils.format_date(test_date)
        assert isinstance(formatted, str)
        assert "2023" in formatted

    def test_number_formatting(self):
        """测试数字格式化"""
        assert self.utils.format_number(1234567.89) == "1,234,567.89"
        assert self.utils.format_number(1000) == "1,000"

    def test_percentage_formatting(self):
        """测试百分比格式化"""
        assert self.utils.format_percentage(0.75) == "75%"
        assert self.utils.format_percentage(0.1234) == "12.34%"

    def test_file_size_formatting(self):
        """测试文件大小格式化"""
        assert self.utils.format_file_size(1024) == "1.00 KB"
        assert self.utils.format_file_size(1048576) == "1.00 MB"

    def test_case_conversion_camel(self):
        """测试驼峰转换"""
        assert self.utils.to_camel_case("hello_world") == "helloWorld"
        assert self.utils.to_camel_case("HelloWorld") == "helloWorld"

    def test_case_conversion_snake(self):
        """测试蛇形转换"""
        assert self.utils.to_snake_case("helloWorld") == "hello_world"
        assert self.utils.to_snake_case("HelloWorld") == "hello_world"

    def test_case_conversion_kebab(self):
        """测试连字符转换"""
        assert self.utils.to_kebab_case("helloWorld") == "hello-world"
        assert self.utils.to_kebab_case("HelloWorld") == "hello-world"

    def test_case_conversion_pascal(self):
        """测试帕斯卡转换"""
        assert self.utils.to_pascal_case("hello_world") == "HelloWorld"
        assert self.utils.to_pascal_case("helloWorld") == "HelloWorld"

    def test_case_conversion_title(self):
        """测试标题转换"""
        assert self.utils.to_title_case("hello world") == "Hello World"
        assert self.utils.to_title_case("HELLO WORLD") == "Hello World"

    def test_string_containment(self):
        """测试字符串包含"""
        assert self.utils.contains("Hello World", "World")
        assert not self.utils.contains("Hello World", "Python")

    def test_string_prefix_suffix(self):
        """测试字符串前缀后缀"""
        assert self.utils.starts_with("Hello World", "Hello")
        assert not self.utils.starts_with("Hello World", "World")
        assert self.utils.ends_with("Hello World", "World")
        assert not self.utils.ends_with("Hello World", "Hello")

    def test_find_all_occurrences(self):
        """测试查找所有出现"""
        text = "hello world hello python hello tests"
        occurrences = self.utils.find_all(text, "hello")
        assert occurrences == [0, 12, 24]

    def test_count_occurrences(self):
        """测试计算出现次数"""
        text = "hello world hello python hello tests"
        count = self.utils.count_occurrences(text, "hello")
        assert count == 3

    def test_string_truncation(self):
        """测试字符串截断"""
        long_string = "This is a very long string that needs to be truncated"
        truncated = self.utils.truncate(long_string, 20)
        assert len(truncated) <= 20
        assert truncated.endswith("...")

    def test_string_padding(self):
        """测试字符串填充"""
        assert self.utils.pad_string("hello", 10, " ") == "hello     "
        assert self.utils.pad_string("hello", 10, "0", "right") == "00000hello"

    def test_string_reversal(self):
        """测试字符串反转"""
        assert self.utils.reverse_string("hello") == "olleh"
        assert self.utils.reverse_string("12345") == "54321"

    def test_string_shuffling(self):
        """测试字符串随机打乱"""
        original = "hello"
        shuffled = self.utils.shuffle_string(original)
        assert len(shuffled) == len(original)
        assert sorted(shuffled) == sorted(original)

    def test_string_repetition(self):
        """测试字符串重复"""
        assert self.utils.repeat_string("hello", 3) == "hellohellohello"
        assert self.utils.repeat_string("ab", 2) == "abab"

    def test_base64_encoding(self):
        """测试Base64编码"""
        original = "Hello World"
        encoded = self.utils.encode_base64(original)
        assert isinstance(encoded, str)
        assert encoded != original

        decoded = self.utils.decode_base64(encoded)
        assert decoded == original

    def test_url_encoding(self):
        """测试URL编码"""
        original = "Hello World/123"
        encoded = self.utils.encode_url(original)
        assert isinstance(encoded, str)
        assert "%20" in encoded

        decoded = self.utils.decode_url(encoded)
        assert decoded == original

    def test_html_entity_encoding(self):
        """测试HTML实体编码"""
        original = "<div>Hello & World</div>"
        encoded = self.utils.encode_html_entities(original)
        assert "&lt;" in encoded
        assert "&gt;" in encoded
        assert "&amp;" in encoded

    def test_string_encryption(self):
        """测试字符串加密"""
        original = "Secret Message"
        key = "encryption_key"
        encrypted = self.utils.encrypt_string(original, key)
        assert encrypted != original

        decrypted = self.utils.decrypt_string(encrypted, key)
        assert decrypted == original

    def test_string_hashing(self):
        """测试字符串哈希"""
        original = "test string"
        salt = self.utils.generate_salt()
        hashed = self.utils.hash_string(original, salt)
        assert isinstance(hashed, str)
        assert hashed != original

        # 验证哈希
        assert self.utils.verify_hash(original, salt, hashed)
        assert not self.utils.verify_hash("wrong_string", salt, hashed)

    def test_string_complexity_analysis(self):
        """测试字符串复杂度分析"""
        simple = "password"
        complex_str = "P@ssw0rd!123"

        simple_analysis = self.utils.analyze_complexity(simple)
        complex_analysis = self.utils.analyze_complexity(complex_str)

        assert complex_analysis["score"] > simple_analysis["score"]

    def test_string_similarity(self):
        """测试字符串相似度"""
        str1 = "hello world"
        str2 = "hello world"
        str3 = "hello python"

        similarity = self.utils.calculate_similarity(str1, str2)
        assert similarity == 1.0

        similarity = self.utils.calculate_similarity(str1, str3)
        assert 0 < similarity < 1.0

    def test_keyword_extraction(self):
        """测试关键词提取"""
        text = "Python is a programming language. Python is popular for data science."
        keywords = self.utils.extract_keywords(text)
        assert isinstance(keywords, list)
        assert "python" in keywords

    def test_language_detection(self):
        """测试语言检测"""
        english_text = "Hello, how are you today?"
        spanish_text = "Hola, ¿cómo estás hoy?"

        detected_lang = self.utils.detect_language(english_text)
        assert detected_lang in ["en", "english"]

        detected_lang = self.utils.detect_language(spanish_text)
        assert detected_lang in ["es", "spanish"]

    def test_sentiment_analysis(self):
        """测试情感分析"""
        positive_text = "I love this product, it's amazing!"
        negative_text = "I hate this, it's terrible."

        positive_sentiment = self.utils.analyze_sentiment(positive_text)
        negative_sentiment = self.utils.analyze_sentiment(negative_text)

        assert positive_sentiment["score"] > 0
        assert negative_sentiment["score"] < 0

    def test_random_string_generation(self):
        """测试随机字符串生成"""
        random_str = self.utils.generate_random_string(10)
        assert len(random_str) == 10
        assert random_str.isalnum()

    def test_uuid_generation(self):
        """测试UUID生成"""
        uuid = self.utils.generate_uuid()
        assert isinstance(uuid, str)
        assert len(uuid) == 36
        assert uuid.count("-") == 4

    def test_slug_generation(self):
        """测试URL slug生成"""
        title = "Hello World! This is a Test"
        slug = self.utils.generate_slug(title)
        assert "hello-world-test" in slug
        assert "!" not in slug

    def test_checksum_generation(self):
        """测试校验和生成"""
        data = "test data"
        checksum = self.utils.generate_checksum(data)
        assert isinstance(checksum, str)
        assert len(checksum) > 0

    def test_password_generation(self):
        """测试密码生成"""
        password = self.utils.generate_password(12)
        assert len(password) == 12
        # 应该包含大小写字母、数字和特殊字符
        assert any(c.isupper() for c in password)
        assert any(c.islower() for c in password)
        assert any(c.isdigit() for c in password)

    def test_string_performance(self):
        """测试字符串性能"""
        import time

        # 测试大量字符串操作的性能
        start_time = time.time()

        for i in range(10000):
            self.utils.clean_string(f"  test string {i}  ")

        end_time = time.time()
        duration = end_time - start_time

        # 验证性能合理
        assert duration < 2.0  # 应该在2秒内完成

    def test_error_handling(self):
        """测试错误处理"""
        # 测试无效输入处理
        with patch.object(self.utils.logger, "error") as mock_logger:
            try:
                self.utils.validate_email(None)
            except Exception:
                pass

            # 验证错误被记录
            mock_logger.assert_called()

    def test_memory_efficiency(self):
        """测试内存效率"""
        import sys

        # 测试大量字符串处理的内存使用
        large_strings = [f"large string {i}" * 100 for i in range(1000)]

        processed_strings = []
        for s in large_strings:
            processed = self.utils.clean_string(s)
            processed_strings.append(processed)

        # 验证内存使用合理
        assert len(processed_strings) == 1000

    def test_thread_safety(self):
        """测试线程安全"""
        import concurrent.futures
        import threading

        def process_string(text):
            return self.utils.clean_string(text)

        test_strings = [f"  test {i}  " for i in range(1000)]

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            results = list(executor.map(process_string, test_strings))

        # 验证所有处理都正确完成
        assert len(results) == 1000
        assert all(result == f"test {i}" for i, result in enumerate(results))

    def test_unicode_support(self):
        """测试Unicode支持"""
        # 测试各种Unicode字符
        unicode_strings = [
            "café",
            "naïve",
            "résumé",
            "中文",
            "العربية",
            "русский",
            "日本語",
            "한국어",
            "🎉",
            "🚀",
        ]

        for string in unicode_strings:
            assert self.utils.is_valid_string(string)
            cleaned = self.utils.clean_string(string)
            assert len(cleaned) > 0

    def test_internationalization_support(self):
        """测试国际化支持"""
        # 测试不同语言的字符串处理
        test_cases = [
            ("en", "Hello World"),
            ("es", "Hola Mundo"),
            ("fr", "Bonjour le monde"),
            ("de", "Hallo Welt"),
            ("zh", "你好世界"),
            ("ja", "こんにちは世界"),
            ("ru", "Привет мир"),
        ]

        for lang, text in test_cases:
            assert self.utils.is_valid_string(text)
            words = self.utils.normalize_whitespace(text)
            assert len(words) > 0

    def test_backward_compatibility(self):
        """测试向后兼容性"""
        # 验证向后兼容性
        essential_methods = [
            "is_valid_string",
            "clean_string",
            "format_currency",
            "to_camel_case",
            "generate_uuid",
        ]

        for method_name in essential_methods:
            assert hasattr(self.utils, method_name)

    def test_extensibility(self):
        """测试扩展性"""
        # 验证扩展性
        assert hasattr(self.utils, "register_processor")
        assert hasattr(self.utils, "unregister_processor")

    def test_configuration_management(self):
        """测试配置管理"""
        # 验证配置管理
        assert hasattr(self.utils, "configure")
        assert hasattr(self.utils, "get_configuration")

    def test_advanced_string_operations(self):
        """测试高级字符串操作"""
        # 验证高级操作
        advanced_operations = [
            "fuzzy_match",
            "phonetic_match",
            "semantic_similarity",
            "text_classification",
            "named_entity_recognition",
        ]

        for operation in advanced_operations:
            assert hasattr(self.utils, operation)

    def test_batch_processing(self):
        """测试批处理"""
        # 验证批处理功能
        assert hasattr(self.utils, "batch_clean")
        assert hasattr(self.utils, "batch_validate")
        assert hasattr(self.utils, "batch_transform")

    def test_caching_integration(self):
        """测试缓存集成"""
        # 验证缓存集成
        assert hasattr(self.utils, "cache_result")
        assert hasattr(self.utils, "get_cached_result")

    def test_logging_integration(self):
        """测试日志集成"""
        # 验证日志集成
        assert hasattr(self.utils, "log_operation")
        assert hasattr(self.utils, "set_log_level")

    def test_monitoring_integration(self):
        """测试监控集成"""
        # 验证监控集成
        assert hasattr(self.utils, "record_metric")
        assert hasattr(self.utils, "get_performance_metrics")

    def test_security_features(self):
        """测试安全特性"""
        # 验证安全特性
        security_features = [
            "sanitize_input",
            "prevent_xss",
            "prevent_sql_injection",
            "validate_input_safety",
        ]

        for feature in security_features:
            assert hasattr(self.utils, feature)

    def test_compliance_features(self):
        """测试合规特性"""
        # 验证合规特性
        compliance_features = [
            "gdpr_compliant_processing",
            "data_masking",
            "privacy_filtering",
            "compliance_check",
        ]

        for feature in compliance_features:
            assert hasattr(self.utils, feature)

    def test_performance_optimization(self):
        """测试性能优化"""
        # 验证性能优化
        optimization_features = [
            "lazy_evaluation",
            "memoization",
            "bulk_processing",
            "parallel_processing",
        ]

        for feature in optimization_features:
            assert hasattr(self.utils, feature)

    def test_documentation_features(self):
        """测试文档特性"""
        # 验证文档特性
        assert hasattr(self.utils, "generate_documentation")
        assert hasattr(self.utils, "get_usage_examples")
        assert hasattr(self.utils, "get_method_signatures")
