"""
测试模板文件
Test Template File

使用说明：
1. 复制此文件到适当的测试目录
2. 替换 [ModuleName] 为实际的模块名
3. 根据测试需求调整模板内容

遵循最佳实践：
- 使用精确的patch而不是全局mock
- 明确的断言和错误验证
- 统一的测试命名约定
"""

import pytest
from unittest.mock import patch, Mock, AsyncMock
import sys
import os

# 添加src到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../..", "src"))

# 导入要测试的模块
# 示例：from src.utils.validators import Validator


@pytest.mark.unit
class TestExample:
    """示例测试类

    测试目标：演示如何使用测试模板
    测试策略：展示各种测试模式和最佳实践
    """

    # ======== Fixtures ========

    @pytest.fixture
    def sample_data(self):
        """示例数据fixture"""
        return {
            "id": 123,
            "name": "Test Name",
            # 添加更多字段
        }

    @pytest.fixture
    def mock_service(self):
        """模拟服务fixture"""
        service = Mock()
        service.method.return_value = "mocked_result"
        return service

    # ======== 测试方法 ========

    def test_example_function_with_valid_data_returns_success(self, sample_data):
        """
        测试：使用有效数据调用example_function返回success

        测试场景：
        - 输入：有效的sample_data
        - 期望：返回成功结果
        """
        # Arrange - 准备测试数据和环境

        # Act - 执行被测试的操作
        # result = example_function(test_input)

        # Assert - 验证结果
        # assert result["status"] == "success", f"Expected success, got {result['status']}"

        pytest.skip("TODO: 实现测试逻辑 - 替换为实际的测试代码")

    def test_example_function_with_invalid_parameter_returns_error(self):
        """
        测试：使用无效的parameter调用example_function返回error

        测试场景：
        - 输入：无效的parameter：空值或None
        - 期望：返回ValueError
        """
        # Arrange

        # Act & Assert
        # with pytest.raises(ValueError):
        #     example_function(invalid_data)

        pytest.skip("TODO: 实现测试逻辑 - 替换为实际的测试代码")

    @patch("src.utils.validators.external_service")
    def test_example_function_with_mocked_dependency_returns_expected_result(
        self, mock_dep
    ):
        """
        测试：使用模拟依赖调用example_function返回expected_result

        测试场景：
        - 模拟：外部服务调用
        - 期望：返回处理后的结果
        """
        # Arrange
        mock_dep.return_value = {"status": "ok", "data": "mocked"}

        # Act
        # result = example_function_with_dependency()

        # Assert
        # assert result["data"] == "mocked"
        # mock_dep.assert_called_once()

        pytest.skip("TODO: 实现测试逻辑 - 替换为实际的测试代码")

    # ======== 边界测试 ========

    @pytest.mark.parametrize(
        "input_value,expected",
        [
            ("valid@email.com", True),
            ("invalid-email", False),
            ("", False),
            (None, False),
        ],
    )
    def test_email_validator_with_various_inputs_returns_expected(
        self, input_value, expected
    ):
        """
        测试：使用各种输入调用email_validator返回期望结果

        参数化测试覆盖多种场景
        """
        # Arrange & Act & Assert
        # assert is_valid_email(input_value) == expected

        pytest.skip("TODO: 实现测试逻辑 - 替换为实际的验证函数")

    # ======== 异步测试（如需要） ========

    @pytest.mark.asyncio
    async def test_async_fetch_data_with_valid_data_returns_success(self):
        """
        测试：异步函数fetch_data使用有效数据返回success
        """
        # Arrange
        # url = "https://api.example.com/data"

        # Act
        # result = await fetch_data(url)

        # Assert
        # assert result["status"] == "success"

        pytest.skip("TODO: 实现异步测试逻辑 - 替换为实际的异步函数")

    # ======== 性能测试（如需要） ========

    def test_data_processing_performance_under_limit(self):
        """
        测试：data_processing执行时间在限制内

        性能要求：执行时间 < 1秒
        """
        import time

        # Arrange
        # test_data = [生成大量测试数据]

        # Act
        # start_time = time.time()
        # result = process_data(test_data)
        # end_time = time.time()

        # Assert
        # execution_time = end_time - start_time
        # assert execution_time < 1.0, f"Too slow: {execution_time}s"

        pytest.skip("TODO: 实现性能测试 - 替换为实际的性能关键函数")


# ======== 辅助函数 ========


def create_test_data(**kwargs):
    """创建测试数据的辅助函数"""
    default_data = {
        "id": 123,
        "name": "Test",
    }
    default_data.update(kwargs)
    return default_data


def assert_valid_response_format(response, expected_status=200):
    """验证响应格式的辅助函数"""
    assert response.status_code == expected_status
    data = response.json()
    assert isinstance(data, dict)
    return data


# ======== 测试类配置 ========


def pytest_configure(config):
    """配置pytest标记"""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "slow: Slow tests")


# ======== 模板使用说明 ========

"""
如何使用此测试模板：

1. 复制模板：
   cp tests/templates/test_template.py tests/unit/your_module/test_your_feature.py

2. 替换占位符：
   - TestExample -> TestYourFeature
   - example_function -> actual_function_name
   - 根据需要修改类名和方法名

3. 导入实际模块：
   # 示例：from src.utils.validators import is_valid_email

4. 实现测试：
   - 移除 pytest.skip() 调用
   - 取消注释并修改测试代码
   - 根据实际API调整断言

5. 运行测试：
   pytest tests/unit/your_module/test_your_feature.py -v

最佳实践：
- 使用描述性的测试方法名
- 遵循 Arrange-Act-Assert 模式
- 使用精确的 Mock 而不是全局 Mock
- 测试边界条件和错误情况
- 使用参数化测试覆盖多种场景

示例实现：
def test_email_validator_with_valid_email_returns_true(self):
    # Arrange
    valid_email = "user@example.com"

    # Act
    result = is_valid_email(valid_email)

    # Assert
    assert result is True
"""
