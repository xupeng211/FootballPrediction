"""
国际化工具函数
"""

import gettext
import os
from pathlib import Path
from typing import Optional, cast

# 翻译目录
LOCALE_DIR = Path(__file__).parent.parent / "locales"

# 全局翻译器
_translator = None


def init_i18n(language: str = "zh_CN") -> None:
    """初始化国际化设置"""
    global _translator

    try:
        _translator = gettext.translation(
            "messages", localedir=LOCALE_DIR, languages=[language], fallback=True
        )
        _translator.install()
    except Exception:
        # 如果翻译文件不存在，使用默认
        _translator = gettext.NullTranslations()


def _(message: str) -> str:
    """翻译函数"""
    global _translator
    if _translator is None:
        init_i18n()

    if _translator:
        return _translator.gettext(message)
    return message


def get_language_from_request(accept_language: Optional[str] = None) -> str:
    """从请求头获取语言设置"""
    if not accept_language:
        accept_language = os.getenv("HTTP_ACCEPT_LANGUAGE", "zh-CN")

    # 支持的语言列表
    supported_languages = {
        "zh": "zh_CN",
        "zh-CN": "zh_CN",
        "zh_CN": "zh_CN",
        "en": "en_US",
        "en-US": "en_US",
    }

    # 解析 Accept-Language 头
    languages = accept_language.split(",")
    for lang in languages:
        lang = lang.split(";")[0].strip()
        if lang in supported_languages:
            return supported_languages[lang]

    # 默认返回中文
    return "zh_CN"


# 初始化
init_i18n()
