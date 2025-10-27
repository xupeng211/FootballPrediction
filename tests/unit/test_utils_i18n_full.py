# 国际化工具测试
import pytest

from src.utils.i18n import I18nUtils


@pytest.mark.unit
def test_get_translation():
    text = I18nUtils.get_translation("hello", "zh")
    assert isinstance(text, str)
    assert len(text) > 0


def test_format_currency():
    amount = 100.50
    formatted = I18nUtils.format_currency(amount, "zh")
    assert "¥" in formatted or "100" in formatted


def test_format_date():
    import datetime

    date = datetime.date(2024, 1, 1)
    formatted = I18nUtils.format_date(date, "zh")
    assert "2024" in formatted
