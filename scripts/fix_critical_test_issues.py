#!/usr/bin/env python3
"""
修复关键测试问题的最佳实践脚本
遵循 TDD 原则：先写测试，再修复代码，最后验证
"""

import os
import sys
import subprocess
from pathlib import Path
from typing import List, Dict, Any
import logging

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CriticalIssuesFixer:
    """关键问题修复器 - 遵循最佳实践"""

    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.fixes_applied = []
        self.tests_run = []

    def run_command(self, cmd: List[str], description: str) -> bool:
        """运行命令并记录结果"""
        logger.info(f"🔧 {description}")
        try:
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                logger.info(f"✅ {description} - 成功")
                return True
            else:
                logger.error(f"❌ {description} - 失败: {result.stderr}")
                return False
        except subprocess.TimeoutExpired:
            logger.error(f"⏰ {description} - 超时")
            return False
        except Exception as e:
            logger.error(f"💥 {description} - 异常: {e}")
            return False

    def create_test_for_dict_utils(self):
        """为 dict_utils 创建失败的测试（TDD第一步）"""
        logger.info("📝 创建 dict_utils 测试用例")

        test_content = '''"""
测试 dict_utils 的深度合并功能
确保修复后的代码满足预期行为
"""

import pytest
from src.utils.dict_utils import DictUtils


class TestDictUtilsFixed:
    """测试修复后的 DictUtils 功能"""

    def test_deep_merge_basic(self):
        """测试基本深度合并"""
        dict1 = {"a": 1, "b": {"x": 10}}
        dict2 = {"b": {"y": 20}, "c": 3}

        result = DictUtils.deep_merge(dict1, dict2)

        expected = {
            "a": 1,
            "b": {"x": 10, "y": 20},
            "c": 3
        }
        assert result == expected

    def test_deep_merge_nested(self):
        """测试嵌套字典合并"""
        dict1 = {
            "level1": {
                "level2": {"a": 1, "b": 2},
                "other": "value1"
            }
        }
        dict2 = {
            "level1": {
                "level2": {"b": 3, "c": 4},
                "new": "value2"
            }
        }

        result = DictUtils.deep_merge(dict1, dict2)

        expected = {
            "level1": {
                "level2": {"a": 1, "b": 3, "c": 4},
                "other": "value1",
                "new": "value2"
            }
        }
        assert result == expected

    def test_deep_merge_no_mutation(self):
        """测试原始字典不被修改"""
        dict1 = {"a": 1, "b": {"x": 10}}
        dict2 = {"b": {"y": 20}}
        dict1_copy = dict1.copy()
        dict1["b"] = dict1["b"].copy()

        result = DictUtils.deep_merge(dict1, dict2)

        # 确保原始字典未被修改
        assert dict1 == dict1_copy
        assert result != dict1

    def test_deep_merge_empty_dicts(self):
        """测试空字典合并"""
        assert DictUtils.deep_merge({}, {}) == {}
        assert DictUtils.deep_merge({"a": 1}, {}) == {"a": 1}
        assert DictUtils.deep_merge({}, {"b": 2}) == {"b": 2}
'''

        test_file = self.project_root / "tests" / "unit" / "utils" / "test_dict_utils_fixed.py"
        test_file.write_text(test_content)
        logger.info("✅ 创建 dict_utils 测试用例完成")

    def fix_dict_utils_variable_name(self):
        """修复 dict_utils.py 的变量名问题"""
        logger.info("🔧 修复 dict_utils.py 变量名错误")

        file_path = self.project_root / "src" / "utils" / "dict_utils.py"

        if not file_path.exists():
            logger.error(f"❌ 文件不存在: {file_path}")
            return False

        content = file_path.read_text()

        # 修复变量名错误：_result -> result
        fixes = [
            ("_result = dict1.copy()", "result = dict1.copy()"),
            ("key in _result", "key in result"),
            ("isinstance(_result[key], dict)", "isinstance(result[key], dict)"),
            ("_result[key] =", "result[key] ="),
            ("return _result", "return result")
        ]

        original_content = content
        for old, new in fixes:
            content = content.replace(old, new)

        if content != original_content:
            file_path.write_text(content)
            logger.info("✅ dict_utils.py 变量名修复完成")
            self.fixes_applied.append("dict_utils_variable_name")
            return True
        else:
            logger.info("ℹ️  dict_utils.py 无需修复")
            return True

    def fix_monitoring_db_query(self):
        """修复 monitoring.py 的数据库查询问题"""
        logger.info("🔧 修复 monitoring.py 数据库查询错误")

        file_path = self.project_root / "src" / "api" / "monitoring.py"

        if not file_path.exists():
            logger.error(f"❌ 文件不存在: {file_path}")
            return False

        content = file_path.read_text()

        # 查找并修复 _get_database_metrics 函数
        lines = content.split('\n')
        fixed_lines = []
        in_function = False

        for i, line in enumerate(lines):
            if 'def _get_database_metrics(' in line:
                in_function = True
                fixed_lines.append(line)
                continue

            if in_function and 'teams = session.execute(' in line:
                # 修复查询逻辑
                fixed_lines.append('        teams_result = session.execute(text("SELECT COUNT(*) as count FROM teams"))')
                fixed_lines.append('        teams_count = teams_result.scalar()')
                fixed_lines.append('')
                fixed_lines.append('        matches_result = session.execute(text("SELECT COUNT(*) as count FROM matches"))')
                fixed_lines.append('        matches_count = matches_result.scalar()')
                fixed_lines.append('')
                fixed_lines.append('        predictions_result = session.execute(text("SELECT COUNT(*) as count FROM predictions"))')
                fixed_lines.append('        predictions_count = predictions_result.scalar()')
                fixed_lines.append('')
                fixed_lines.append('        stats["statistics"] = {')
                fixed_lines.append('            "teams_count": teams_count,')
                fixed_lines.append('            "matches_count": matches_count,')
                fixed_lines.append('            "predictions_count": predictions_count')
                fixed_lines.append('        }')
                continue

            if in_function and 'stats["statistics"]["teams_count"] = _val(teams)' in line:
                # 跳过原来的错误行
                continue

            if in_function and line.strip().startswith('except ') or line.strip().startswith('return '):
                fixed_lines.append(line)
                in_function = False
                continue

            if not in_function or not any(keyword in line for keyword in ['teams_count', 'matches_count', 'predictions_count']):
                fixed_lines.append(line)

        fixed_content = '\n'.join(fixed_lines)

        # 确保导入了 text 函数
        if 'from sqlalchemy import text' not in fixed_content:
            fixed_content = fixed_content.replace(
                'from sqlalchemy.orm import Session',
                'from sqlalchemy.orm import Session\nfrom sqlalchemy import text'
            )

        if fixed_content != content:
            file_path.write_text(fixed_content)
            logger.info("✅ monitoring.py 数据库查询修复完成")
            self.fixes_applied.append("monitoring_db_query")
            return True
        else:
            logger.info("ℹ️  monitoring.py 无需修复")
            return True

    def fix_test_import_paths(self):
        """修复测试文件的导入路径问题"""
        logger.info("🔧 修复测试文件导入路径")

        test_file = self.project_root / "tests" / "unit" / "api" / "test_openapi_config.py"

        if not test_file.exists():
            logger.warning(f"⚠️  测试文件不存在: {test_file}")
            return True

        content = test_file.read_text()

        # 修复导入路径
        original_content = content
        content = content.replace(
            'from src._config.openapi_config import OpenAPIConfig, setup_openapi',
            'from src.config.openapi_config import OpenAPIConfig, setup_openapi'
        )

        if content != original_content:
            test_file.write_text(content)
            logger.info("✅ 测试导入路径修复完成")
            self.fixes_applied.append("test_import_paths")
            return True
        else:
            logger.info("ℹ️  测试导入路径无需修复")
            return True

    def run_test_verification(self, test_path: str) -> bool:
        """运行特定测试验证修复结果"""
        logger.info(f"🧪 运行测试验证: {test_path}")

        cmd = ["python", "-m", "pytest", test_path, "-v", "--tb=short"]
        success = self.run_command(cmd, f"验证测试: {test_path}")

        self.tests_run.append(test_path)
        return success

    def create_quality_check_script(self):
        """创建代码质量检查脚本"""
        logger.info("📝 创建代码质量检查脚本")

        script_content = '''#!/usr/bin/env python3
"""
代码质量检查脚本
防止类似问题再次发生
"""

import subprocess
import sys
from pathlib import Path

def run_command(cmd, description):
    """运行命令并返回结果"""
    print(f"🔧 {description}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        print(f"✅ {description} - 通过")
        return True
    else:
        print(f"❌ {description} - 失败")
        print(f"错误信息: {result.stderr}")
        return False

def main():
    """主检查函数"""
    print("🚀 开始代码质量检查...")

    checks = [
        (["python", "-m", "pytest", "tests/unit/utils/test_dict_utils_fixed.py", "-v"], "dict_utils 功能测试"),
        (["python", "-m", "pytest", "tests/unit/api/test_health.py", "-v"], "健康检查API测试"),
        (["ruff", "check", "src/utils/dict_utils.py"], "dict_utils 代码质量检查"),
        (["ruff", "check", "src/api/monitoring.py"], "monitoring 代码质量检查"),
    ]

    passed = 0
    total = len(checks)

    for cmd, description in checks:
        if run_command(cmd, description):
            passed += 1
        print("-" * 50)

    print(f"\\n📊 检查结果: {passed}/{total} 通过")

    if passed == total:
        print("🎉 所有质量检查通过！")
        return 0
    else:
        print("⚠️  存在质量问题需要修复")
        return 1

if __name__ == "__main__":
    sys.exit(main())
'''

        script_path = self.project_root / "scripts" / "quality_check.py"
        script_path.write_text(script_content)
        script_path.chmod(0o755)
        logger.info("✅ 代码质量检查脚本创建完成")

    def run_complete_fix_process(self):
        """运行完整的修复流程"""
        logger.info("🚀 开始关键问题修复流程")

        # 步骤1: 创建测试用例
        self.create_test_for_dict_utils()

        # 步骤2: 修复代码问题
        fixes = [
            ("修复 dict_utils 变量名", self.fix_dict_utils_variable_name),
            ("修复 monitoring 数据库查询", self.fix_monitoring_db_query),
            ("修复测试导入路径", self.fix_test_import_paths),
        ]

        for desc, fix_func in fixes:
            if not fix_func():
                logger.error(f"❌ {desc} 失败")
                return False

        # 步骤3: 验证修复结果
        verifications = [
            "tests/unit/utils/test_dict_utils_fixed.py",
            "tests/unit/api/test_health.py",
            "tests/unit/utils/test_dict_utils.py::TestDictUtils::test_deep_merge"
        ]

        all_passed = True
        for test in verifications:
            if not self.run_test_verification(test):
                all_passed = False

        # 步骤4: 创建质量检查脚本
        self.create_quality_check_script()

        # 步骤5: 生成修复报告
        self.generate_fix_report(all_passed)

        return all_passed

    def generate_fix_report(self, success: bool):
        """生成修复报告"""
        report = f"""
# 🎯 关键测试问题修复报告

## 修复状态
{'✅ 修复成功' if success else '❌ 修复失败'}

## 应用的修复
{chr(10).join(f'- {fix}' for fix in self.fixes_applied) if self.fixes_applied else '- 无修复应用'}

## 运行的测试
{chr(10).join(f'- {test}' for test in self.tests_run) if self.tests_run else '- 无测试运行'}

## 质量检查脚本
创建了 `scripts/quality_check.py` 用于后续质量检查

## 下一步建议
1. 运行 `python scripts/quality_check.py` 验证修复
2. 运行完整测试套件确保无回归
3. 考虑添加 pre-commit hook 防止类似问题

## 时间戳
{Path(__file__).stat().st_mtime}
"""

        report_path = self.project_root / "test_fixes_report.md"
        report_path.write_text(report)
        logger.info(f"📄 修复报告已生成: {report_path}")


def main():
    """主函数"""
    print("🎯 开始关键测试问题修复...")

    fixer = CriticalIssuesFixer()
    success = fixer.run_complete_fix_process()

    if success:
        print("🎉 所有关键问题修复成功！")
        return 0
    else:
        print("❌ 修复过程中遇到问题，请检查日志")
        return 1


if __name__ == "__main__":
    sys.exit(main())