#!/usr/bin/env python3
"""
批量修复脚本 - 使用sed和正则表达式
Batch Fix Script - Using sed and regex
"""

import subprocess
import re
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_sed(pattern: str, replacement: str, file_path: Path) -> bool:
    """运行sed命令进行替换"""
    try:
        # 转义特殊字符
        pattern = pattern.replace('/', r'\/')
        replacement = replacement.replace('/', r'\/')

        cmd = ['sed', '-i', f's/{pattern}/{replacement}/g', str(file_path)]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode == 0
    except Exception as e:
        logger.error(f"sed命令失败: {e}")
        return False


def fix_with_python(content: str) -> str:
    """使用Python进行复杂修复"""
    # 修复开头的文档字符串
    if content.startswith('""') and not content.startswith('"""'):
        content = '"""' + content[2:]

    # 修复单引号开始的文档字符串
    if content.startswith("''") and not content.startswith("'''"):
        content = "'''" + content[2:]

    # 修复连接的import语句
    content = re.sub(r'^(["\'][^"\']*["\'])\s*import', r'\1\nimport', content)
    content = re.sub(r'import\s+([a-zA-Z_][a-zA-Z0-9_]*)import', r'import \1\nimport', content)
    content = re.sub(r'from\s+([^\s]+)import', r'from \1 import', content)

    # 修复中文标点后的代码
    content = re.sub(r'([。)！））;；])([^#\s\n])', r'\1\n\2', content)
    content = re.sub(r'([。）！））；；])\s*import', r'\1\nimport', content)

    return content


def batch_fix_module(module_name: str):
    """批量修复模块"""
    src_dir = Path('src')
    module_dir = src_dir / module_name

    if not module_dir.exists():
        logger.error(f"模块不存在: {module_name}")
        return

    logger.info(f"开始批量修复模块: {module_name}")

    py_files = list(module_dir.rglob('*.py'))
    fixed_count = 0

    for py_file in py_files:
        try:
            # 读取文件
            with open(py_file, 'r', encoding='utf-8') as f:
                original_content = f.read()

            # 使用Python修复
            content = fix_with_python(original_content)

            # 写回修复后的内容
            if content != original_content:
                with open(py_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                logger.info(f"✅ 修复: {py_file.relative_to(src_dir)}")
                fixed_count += 1

        except Exception as e:
            logger.error(f"❌ 处理文件失败 {py_file}: {e}")

    logger.info(f"模块 {module_name} 批量修复完成: {fixed_count}/{len(py_files)}")


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='批量语法修复工具')
    parser.add_argument('modules', nargs='*', default=['api', 'core', 'database', 'services', 'domain', 'cache'],
                       help='要修复的模块列表')

    args = parser.parse_args()

    for module in args.modules:
        batch_fix_module(module)


if __name__ == '__main__':
    main()