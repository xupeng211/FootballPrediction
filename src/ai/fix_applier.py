#!/usr/bin/env python3
"""
修复应用器

负责将 AI 生成的修复建议安全地应用到代码中。
"""

import os
import shutil
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import subprocess

from .claude_cli_wrapper import FixSuggestion, TestFailure
from .code_analyzer import AnalysisResult

logger = logging.getLogger(__name__)


@dataclass
class FixApplication:
    """修复应用记录"""
    fix_suggestion: FixSuggestion
    original_content: str
    applied_content: str
    timestamp: datetime
    success: bool
    backup_path: Optional[str] = None
    test_results_before: Optional[Dict] = None
    test_results_after: Optional[Dict] = None


@dataclass
class ApplyResult:
    """应用结果"""
    success: bool
    message: str
    backup_path: Optional[str]
    test_results: Optional[Dict]
    rollback_possible: bool


class FixApplier:
    """修复应用器主类"""

    def __init__(self, backup_dir: Optional[Path] = None):
        self.backup_dir = backup_dir or Path("backups/ai_fixes")
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.application_history: List[FixApplication] = []
        logger.info(f"FixApplier initialized with backup directory: {self.backup_dir}")

    def apply_fix_safely(self, fix_suggestion: FixSuggestion,
                         dry_run: bool = True,
                         create_backup: bool = True,
                         run_tests: bool = True) -> ApplyResult:
        """
        安全地应用修复建议

        Args:
            fix_suggestion: 修复建议
            dry_run: 是否为预览模式
            create_backup: 是否创建备份
            run_tests: 是否运行测试验证

        Returns:
            应用结果
        """
        file_path = Path(fix_suggestion.file_path)

        # 1. 验证文件存在
        if not file_path.exists():
            return ApplyResult(
                success=False,
                message=f"File not found: {file_path}",
                backup_path=None,
                test_results=None,
                rollback_possible=False
            )

        try:
            # 2. 记录原始内容
            original_content = file_path.read_text(encoding='utf-8')

            # 3. 如果是预览模式，只显示差异
            if dry_run:
                return self._preview_fix(fix_suggestion, original_content)

            # 4. 创建备份
            backup_path = None
            if create_backup:
                backup_path = self._create_backup(file_path, fix_suggestion)

            # 5. 运行测试前的状态
            test_results_before = None
            if run_tests:
                test_results_before = self._run_tests_for_file(file_path)

            # 6. 应用修复
            file_path.write_text(fix_suggestion.fixed_code, encoding='utf-8')
            logger.info(f"Applied fix to {file_path}")

            # 7. 验证修复后的代码
            validation_result = self._validate_applied_fix(fix_suggestion, file_path)

            # 8. 运行测试验证
            test_results_after = None
            if run_tests:
                test_results_after = self._run_tests_for_file(file_path)

            # 9. 记录应用历史
            application = FixApplication(
                fix_suggestion=fix_suggestion,
                original_content=original_content,
                applied_content=fix_suggestion.fixed_code,
                timestamp=datetime.now(),
                success=validation_result,
                backup_path=backup_path,
                test_results_before=test_results_before,
                test_results_after=test_results_after
            )
            self.application_history.append(application)

            return ApplyResult(
                success=validation_result,
                message="Fix applied successfully" if validation_result else "Fix validation failed",
                backup_path=backup_path,
                test_results=test_results_after,
                rollback_possible=backup_path is not None
            )

        except Exception as e:
            logger.error(f"Failed to apply fix to {file_path}: {e}")
            return ApplyResult(
                success=False,
                message=f"Error applying fix: {str(e)}",
                backup_path=None,
                test_results=None,
                rollback_possible=False
            )

    def rollback_fix(self, backup_path: str) -> bool:
        """
        回滚修复

        Args:
            backup_path: 备份文件路径

        Returns:
            回滚是否成功
        """
        try:
            backup_file = Path(backup_path)
            if not backup_file.exists():
                logger.error(f"Backup file not found: {backup_path}")
                return False

            # 从备份路径恢复原始文件
            # 备份路径格式: backups/ai_fixes/filename_YYYYMMDD_HHMMSS.py
            relative_path = backup_file.name
            # 移除时间戳部分
            original_name = "_".join(relative_path.split("_")[:-2])  # 移除最后两个部分（时间戳）
            original_path = Path(original_name)

            # 恢复文件
            shutil.copy2(backup_file, original_path)
            logger.info(f"Rolled back fix from {backup_path} to {original_path}")

            return True

        except Exception as e:
            logger.error(f"Failed to rollback fix: {e}")
            return False

    def batch_apply_fixes(self, fix_suggestions: List[FixSuggestion],
                         interactive: bool = True) -> Dict[str, ApplyResult]:
        """
        批量应用修复建议

        Args:
            fix_suggestions: 修复建议列表
            interactive: 是否交互式确认

        Returns:
            应用结果字典（文件路径 -> 应用结果）
        """
        results = {}

        for i, fix in enumerate(fix_suggestions, 1):
            print(f"\n📋 Processing fix {i}/{len(fix_suggestions)}:")
            print(f"File: {fix.file_path}")
            print(f"Confidence: {fix.confidence:.1%}")
            print(f"Explanation: {fix.explanation}")

            if interactive:
                response = input("\nApply this fix? [Y/n/skip]: ").strip().lower()
                if response == 'n':
                    print("⏭️  Skipped")
                    continue
                elif response == 'skip':
                    print("⏭️  Skipped")
                    continue

            # 预览修复
            preview_result = self.apply_fix_safely(fix, dry_run=True)
            if interactive:
                response = input("\nApply this fix? [Y/n]: ").strip().lower()
                if response == 'n':
                    print("⏭️  Skipped")
                    continue

            # 应用修复
            result = self.apply_fix_safely(fix, dry_run=False)
            results[fix.file_path] = result

            # 显示结果
            if result.success:
                print(f"✅ Successfully applied fix to {fix.file_path}")
            else:
                print(f"❌ Failed to apply fix to {fix.file_path}: {result.message}")

            # 询问是否继续
            if interactive and i < len(fix_suggestions):
                continue_response = input("\nContinue with next fix? [Y/n]: ").strip().lower()
                if continue_response == 'n':
                    break

        return results

    def get_fix_statistics(self) -> Dict:
        """获取修复统计信息"""
        if not self.application_history:
            return {"total": 0, "successful": 0, "failed": 0}

        total = len(self.application_history)
        successful = len([app for app in self.application_history if app.success])
        failed = total - successful

        return {
            "total": total,
            "successful": successful,
            "failed": failed,
            "success_rate": successful / total if total > 0 else 0
        }

    def cleanup_old_backups(self, days_to_keep: int = 7) -> int:
        """
        清理旧备份文件

        Args:
            days_to_keep: 保留天数

        Returns:
            清理的文件数量
        """
        from datetime import datetime, timedelta

        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        cleaned_count = 0

        for backup_file in self.backup_dir.glob("*"):
            if backup_file.is_file():
                # 从文件名提取时间戳
                try:
                    # 文件名格式: filename_YYYYMMDD_HHMMSS.py
                    parts = backup_file.stem.split("_")
                    if len(parts) >= 3:
                        date_str = parts[-2]  # YYYYMMDD
                        time_str = parts[-1]  # HHMMSS
                        file_date = datetime.strptime(f"{date_str}{time_str}", "%Y%m%d%H%M%S")

                        if file_date < cutoff_date:
                            backup_file.unlink()
                            cleaned_count += 1
                            logger.info(f"Cleaned old backup: {backup_file}")
                except (ValueError, IndexError):
                    # 如果文件名格式不匹配，跳过
                    continue

        logger.info(f"Cleaned {cleaned_count} old backup files")
        return cleaned_count

    def _preview_fix(self, fix_suggestion: FixSuggestion, original_content: str) -> ApplyResult:
        """预览修复"""
        print(f"\n📋 Fix Preview for {fix_suggestion.file_path}:")
        print("=" * 50)
        print("Original code:")
        print("-" * 25)
        print(original_content[:500] + "..." if len(original_content) > 500 else original_content)
        print("\nFixed code:")
        print("-" * 25)
        print(fix_suggestion.fixed_code[:500] + "..." if len(fix_suggestion.fixed_code) > 500 else fix_suggestion.fixed_code)
        print(f"\nExplanation: {fix_suggestion.explanation}")
        print(f"Confidence: {fix_suggestion.confidence:.1%}")

        return ApplyResult(
            success=True,
            message="Preview mode - no changes made",
            backup_path=None,
            test_results=None,
            rollback_possible=False
        )

    def _create_backup(self, file_path: Path, fix_suggestion: FixSuggestion) -> str:
        """创建备份文件"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{file_path.name}_{timestamp}"
        backup_path = self.backup_dir / backup_name

        shutil.copy2(file_path, backup_path)
        logger.info(f"Created backup: {backup_path}")

        return str(backup_path)

    def _validate_applied_fix(self, fix_suggestion: FixSuggestion, file_path: Path) -> bool:
        """验证应用的修复"""
        try:
            # 检查文件语法
            applied_content = file_path.read_text(encoding='utf-8')
            compile(applied_content, str(file_path), 'exec')

            # 检查修复内容不为空
            if not applied_content.strip():
                logger.error("Applied fix resulted in empty file")
                return False

            logger.info(f"Fix validation passed for {file_path}")
            return True

        except SyntaxError as e:
            logger.error(f"Syntax error in applied fix: {e}")
            return False
        except Exception as e:
            logger.error(f"Validation failed: {e}")
            return False

    def _run_tests_for_file(self, file_path: Path) -> Optional[Dict]:
        """运行与文件相关的测试"""
        try:
            # 根据文件路径确定测试命令
            if "tests/" in str(file_path):
                # 如果是测试文件，直接运行它
                test_path = file_path
            else:
                # 如果是源代码文件，运行相关测试
                test_path = self._find_test_file_for_source(file_path)

            if not test_path or not test_path.exists():
                return None

            # 运行测试
            result = subprocess.run(
                ["python", "-m", "pytest", str(test_path), "--tb=short", "-v"],
                capture_output=True,
                text=True,
                timeout=60
            )

            return {
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "success": result.returncode == 0
            }

        except subprocess.TimeoutExpired:
            logger.warning(f"Test timeout for {file_path}")
            return {"returncode": -1, "stdout": "", "stderr": "Test timeout", "success": False}
        except Exception as e:
            logger.error(f"Failed to run tests for {file_path}: {e}")
            return None

    def _find_test_file_for_source(self, source_path: Path) -> Optional[Path]:
        """为源代码文件查找对应的测试文件"""
        try:
            # 简单的映射规则：src/module/file.py -> tests/test_file.py
            relative_path = source_path.relative_to("src")
            test_name = f"test_{relative_path.name}"
            test_path = Path("tests") / relative_path.parent / test_name

            if test_path.exists():
                return test_path

            # 尝试其他可能的测试文件名
            test_name_alt = f"test_{relative_path.stem}.py"
            test_path_alt = Path("tests") / relative_path.parent / test_name_alt

            if test_path_alt.exists():
                return test_path_alt

            return None

        except Exception:
            return None


def main():
    """主函数 - 用于测试"""
    # 设置日志
    logging.basicConfig(level=logging.INFO)

    # 创建修复应用器
    applier = FixApplier()

    # 创建测试修复建议
    from .claude_cli_wrapper import FixSuggestion

    test_fix = FixSuggestion(
        original_code="def test_example():\n    assert False",
        fixed_code="def test_example():\n    assert True",
        explanation="Fixed assertion to always pass",
        confidence=0.9,
        file_path="tests/test_example.py",
        line_range=(1, 2)
    )

    print("🧪 Testing fix application...")

    # 预览修复
    print("\n1. Preview mode:")
    preview_result = applier.apply_fix_safely(test_fix, dry_run=True)
    print(f"Preview result: {preview_result.success} - {preview_result.message}")

    # 创建测试文件
    test_file = Path("tests/test_example.py")
    test_file.parent.mkdir(exist_ok=True)
    test_file.write_text(test_fix.original_content, encoding='utf-8')

    try:
        # 应用修复（非预览模式）
        print("\n2. Apply mode:")
        apply_result = applier.apply_fix_safely(test_fix, dry_run=False, run_tests=False)
        print(f"Apply result: {apply_result.success} - {apply_result.message}")

        # 显示统计信息
        print("\n3. Statistics:")
        stats = applier.get_fix_statistics()
        print(f"Total fixes: {stats['total']}")
        print(f"Successful: {stats['successful']}")
        print(f"Success rate: {stats['success_rate']:.1%}")

    finally:
        # 清理测试文件
        if test_file.exists():
            test_file.unlink()


if __name__ == "__main__":
    main()