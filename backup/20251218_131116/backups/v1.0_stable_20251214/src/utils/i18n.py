"""国际化支持
Internationalization Support.
"""

import gettext
import os
from pathlib import Path

# 支持的语言
supported_languages = {
    "zh": "zh_CN",
    "zh-CN": "zh_CN",
    "en": "en_US",
    "en-US": "en_US",
}

# 翻译文件目录
LOCALE_DIR = Path(__file__).parent / "locales"


def init_i18n():
    """函数文档字符串."""
    pass  # 添加pass语句
    """初始化国际化"""
    # 确保翻译目录存在
    LOCALE_DIR.mkdir(exist_ok=True)

    # 设置默认语言
    os.getenv("LANGUAGE", "zh_CN")

    try:
        # 设置gettext
        gettext.bindtextdomain("football_prediction", str(LOCALE_DIR))
        gettext.textdomain("football_prediction")

        # 安装gettext
        gettext.install("football_prediction", localedir=str(LOCALE_DIR))
    except (ValueError, KeyError, RuntimeError):
        # 如果初始化失败,使用默认语言
        pass


# 全局语言状态
_current_language = "zh"


def get_text(key: str, default: str = None) -> str:
    """获取翻译文本".

    Args:
        key: 翻译键
        default: 默认文本

    Returns:
        翻译后的文本或默认值
    """
    # 简化实现:直接返回默认值或键名
    return default or key


def set_language(language: str) -> None:
    """设置当前语言".

    Args:
        language: 语言代码
    """
    global _current_language
    # 检查类型和有效性
    if not isinstance(language, str):
        return
    if language in supported_languages:
        _current_language = language


def get_current_language() -> str:
    """获取当前语言".

    Returns:
        当前语言代码
    """
    return _current_language


class I18nUtils:
    """类文档字符串."""

    pass  # 添加pass语句
    """国际化工具类"""

    @staticmethod
    def translate(key: str, language: str = "zh") -> str:
        """翻译文本."""
        return key  # 简化实现

    @staticmethod
    def get_supported_languages() -> dict:
        """获取支持的语言."""
        return supported_languages


# 初始化
init_i18n()
