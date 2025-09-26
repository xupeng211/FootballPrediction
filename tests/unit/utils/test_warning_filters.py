import pytest
import warnings
from unittest.mock import MagicMock, patch

# Import the module to be tested
from src.utils import warning_filters

pytestmark = pytest.mark.unit


# A dummy Marshmallow warning class for mocking
class MockMarshmallowWarning(Warning):
    pass


def test_setup_warning_filters_marshmallow_present():
    """
    测试当 marshmallow.warnings 可用时，过滤器是否正确设置
    """
    mock_marshmallow = MagicMock()
    mock_marshmallow.warnings.ChangedInMarshmallow4Warning = MockMarshmallowWarning

    with patch.dict("sys.modules", {"marshmallow": mock_marshmallow}):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            warning_filters.setup_warning_filters()
            warnings.warn(
                "Number field should not be instantiated.", MockMarshmallowWarning
            )
    assert len(w) == 0


def test_setup_warning_filters_marshmallow_absent():
    """
    测试当 marshmallow.warnings 不可用时，是否回退到通用过滤器
    """
    with patch.dict("sys.modules", {"marshmallow": None}):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            warning_filters.setup_warning_filters()
            warnings.warn("A Number field should not be instantiated.", UserWarning)
    assert len(w) == 0


def test_setup_third_party_warning_filters():
    """
    测试第三方库警告是否被抑制
    """
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        warning_filters._setup_third_party_warning_filters()
        warnings.warn("A great_expectations warning", DeprecationWarning)
        warnings.warn("A sqlalchemy warning", DeprecationWarning)
    assert len(w) == 0


def test_setup_test_warning_filters():
    """
    测试测试环境的警告过滤器是否正确设置
    """
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        warning_filters.setup_test_warning_filters()
        warnings.warn("Some deprecation warning", DeprecationWarning)
        warnings.warn("Some pending deprecation warning", PendingDeprecationWarning)
        warnings.warn("A user-facing warning", UserWarning)
    assert len(w) == 1
    assert issubclass(w[-1].category, UserWarning)


@patch("src.utils.warning_filters.setup_warning_filters")
def test_auto_setup_failure_handling(mock_setup, capsys):
    """
    测试 _auto_setup 中的异常处理是否正常工作
    """
    mock_setup.side_effect = Exception("Test Error")
    warning_filters._auto_setup()
    captured = capsys.readouterr()
    assert "警告过滤器自动设置失败: Test Error" in captured.out


def test_suppress_marshmallow_warnings_decorator():
    """
    测试 suppress_marshmallow_warnings 装饰器是否有效
    """
    mock_marshmallow = MagicMock()
    mock_marshmallow.warnings.ChangedInMarshmallow4Warning = MockMarshmallowWarning

    @warning_filters.suppress_marshmallow_warnings
    def function_with_marshmallow_warning():
        warnings.warn("Marshmallow warning here", MockMarshmallowWarning)

    with patch.dict("sys.modules", {"marshmallow": mock_marshmallow}):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            function_with_marshmallow_warning()
    assert len(w) == 0
