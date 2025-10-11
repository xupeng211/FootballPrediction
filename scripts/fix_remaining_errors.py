#!/usr/bin/env python3
"""
修复剩余的语法错误
Fix remaining syntax errors
"""

from pathlib import Path


def fix_specific_files():
    """修复特定的文件"""
    fixes = {
        "src/__init__.py": '''"""
Football Prediction System
足球预测系统
"""

__version__ = "0.1.0"
import os
''',
        "src/api/__init__.py": '''"""
API Module
"""

from .data_api import router as data_router
from .health_api import router as health_router
from .predictions_api import router as predictions_router

__all__ = ["data_router", "health_router", "predictions_router"]
''',
        "src/utils/warning_filters.py": '''"""
警告过滤器设置
Warning Filters Setup
"""

import warnings
import sys

def setup_warning_filters():
    """设置警告过滤器"""
    # 忽略一些常见的警告
    warnings.filterwarnings("ignore", category=UserWarning, module="tensorflow.*")
    warnings.filterwarnings("ignore", category=DeprecationWarning, module="sklearn.*")
    warnings.filterwarnings("ignore", category=FutureWarning, module="pandas.*")
    warnings.filterwarnings("ignore", category=PendingDeprecationWarning)

# 只在非测试环境下自动设置
if "pytest" not in sys.modules:
    try:
        setup_warning_filters()
    except Exception as e:
        # 如果自动设置失败，不要影响应用启动
        print(f"⚠️  警告过滤器自动设置失败: {e}")
''',
        "src/utils/i18n.py": '''"""
国际化支持
Internationalization Support
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
    """初始化国际化"""
    # 确保翻译目录存在
    LOCALE_DIR.mkdir(exist_ok=True)

    # 设置默认语言
    lang = os.getenv("LANGUAGE", "zh_CN")

    try:
        # 设置gettext
        gettext.bindtextdomain("football_prediction", str(LOCALE_DIR))
        gettext.textdomain("football_prediction")

        # 安装gettext
        gettext.install("football_prediction", localedir=str(LOCALE_DIR))
    except Exception:
        # 如果初始化失败，使用默认语言
        pass

# 初始化
init_i18n()
''',
    }

    for file_path, content in fixes.items():
        path = Path(file_path)
        if path.exists():
            print(f"修复 {file_path}")
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)


def fix_indentation_errors():
    """修复缩进错误"""
    files_to_fix = [
        "src/utils/file_utils.py",
        "src/utils/string_utils.py",
        "src/utils/time_utils.py",
        "src/utils/_retry/config.py",
        "src/utils/_retry/strategies.py",
        "src/utils/_retry/decorators.py",
    ]

    for file_path in files_to_fix:
        path = Path(file_path)
        if not path.exists():
            continue

        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        # 移除文件末尾的import语句
        new_lines = []
        for line in lines:
            stripped = line.strip()
            # 如果是import语句且在文件末尾（后几行），跳过
            if (stripped.startswith("import ") or stripped.startswith("from ")) and len(
                new_lines
            ) > 10:
                # 检查是否在文件末尾的10行内
                if len(lines) - lines.index(line) < 10:
                    continue
            new_lines.append(line)

        # 写回文件
        with open(path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)

        print(f"清理 {file_path}")


def main():
    """主函数"""
    print("🔧 修复剩余的语法错误...")

    fix_specific_files()
    fix_indentation_errors()

    print("\n✅ 完成！")


if __name__ == "__main__":
    main()
