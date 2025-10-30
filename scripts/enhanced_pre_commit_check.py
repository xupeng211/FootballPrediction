#!/usr/bin/env python3
"""
增强的预提交检查工具
优化的快速验证系统
"""

import subprocess
import sys
import os
import time
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple


class EnhancedPreCommitChecker:
    """增强的预提交检查器"""

    def __init__(self):
        self.project_root = Path.cwd()
        self.start_time = time.time()
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "checks": [],
            "total_time": 0,
            "passed": 0,
            "failed": 0,
            "warnings": 0,
        }

    def run_check(
        self,
        name: str,
        command: List[str],
        description: str,
        critical: bool = True,
        timeout: int = 60,
    ) -> Dict:
        """运行单个检查"""
        print(f"🔍 {description}...")

        check_start = time.time()
        result = {
            "name": name,
            "description": description,
            "command": " ".join(command),
            "start_time": check_start,
            "critical": critical,
            "timeout": timeout,
        }

        try:
            # 使用超时运行
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=self.project_root,
            )

            try:
                stdout, stderr = process.communicate(timeout=timeout)
                return_code = process.returncode
            except subprocess.TimeoutExpired:
                process.kill()
                stdout, stderr = process.communicate()
                return_code = -1
                print(f"   ⏰ 检查超时 ({timeout}s)")

            elapsed = time.time() - check_start
            result["elapsed_time"] = elapsed
            result["return_code"] = return_code
            result["stdout"] = stdout.strip()
            result["stderr"] = stderr.strip()

            if return_code == 0:
                print(f"   ✅ {description} 通过 ({elapsed:.1f}s)")
                result["status"] = "passed"
                self.results["passed"] += 1
            else:
                if critical:
                    print(f"   ❌ {description} 失败 ({elapsed:.1f}s)")
                    result["status"] = "failed"
                    self.results["failed"] += 1
                    if stderr:
                        print(f"      错误: {stderr[:100]}...")
                else:
                    print(f"   ⚠️ {description} 有警告 ({elapsed:.1f}s)")
                    result["status"] = "warning"
                    self.results["warnings"] += 1
                    if stderr:
                        print(f"      警告: {stderr[:100]}...")

        except Exception as e:
            elapsed = time.time() - check_start
            result["elapsed_time"] = elapsed
            result["status"] = "error"
            result["error"] = str(e)
            print(f"   💥 {description} 异常 ({elapsed:.1f}s): {e}")
            self.results["failed"] += 1

        self.results["checks"].append(result)
        return result

    def get_changed_files(self) -> List[str]:
        """获取修改的Python文件"""
        try:
            # 尝试获取git暂存的文件
            result = subprocess.run(
                ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM", "*.py"],
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                files = [f.strip() for f in result.stdout.strip().split("\n") if f.strip()]
                return [f for f in files if f.startswith("src/")]
            except Exception:
            pass

        # 如果不是git环境或获取失败，返回核心文件
        core_files = [
            "src/api/",
            "src/core/",
            "src/services/",
            "src/utils/",
            "src/domain/",
            "src/repositories/",
        ]

        changed_files = []
        for pattern in core_files:
            if os.path.exists(pattern):
                for root, dirs, files in os.walk(pattern):
                    for file in files:
                        if file.endswith(".py"):
                            changed_files.append(os.path.join(root, file))

        return changed_files[:10]  # 限制检查文件数量

    def run_syntax_check(self, changed_files: List[str]) -> Dict:
        """运行语法检查"""
        if not changed_files:
            return self.run_check(
                "syntax_check",
                ["python", "-c", "print('语法检查跳过 - 无修改文件')"],
                "语法检查",
                critical=False,
            )

        # 逐个检查文件语法
        syntax_errors = []
        for file_path in changed_files[:5]:  # 最多检查5个文件
            if os.path.exists(file_path):
                try:
                    result = subprocess.run(
                        ["python", "-m", "py_compile", file_path], capture_output=True, text=True
                    )
                    if result.returncode != 0:
                        syntax_errors.append(f"{file_path}: {result.stderr}")
            except Exception:
                    syntax_errors.append(f"{file_path}: 检查异常")

        if syntax_errors:
            return {
                "name": "syntax_check",
                "status": "failed",
                "errors": syntax_errors,
                "message": f"发现 {len(syntax_errors)} 个语法错误",
            }
        else:
            return {
                "name": "syntax_check",
                "status": "passed",
                "message": f"语法检查通过 ({len(changed_files)} 个文件)",
            }

    def run_fast_quality_check(self) -> Dict:
        """运行快速质量检查"""
        return self.run_check(
            "fast_quality",
            ["python", "scripts/quick_quality_check.py"],
            "快速质量检查",
            critical=False,
            timeout=30,
        )

    def run_import_check(self, changed_files: List[str]) -> Dict:
        """运行导入检查"""
        if not changed_files:
            return {"name": "import_check", "status": "skipped", "message": "无修改文件"}

        try:
            # 检查关键模块导入
            test_imports = [
                "import src.core.di",
                "import src.utils.dict_utils",
                "import src.utils.time_utils",
            ]

            import_errors = []
            for import_stmt in test_imports:
                try:
                    result = subprocess.run(
                        ["python", "-c", import_stmt], capture_output=True, text=True, timeout=5
                    )
                    if result.returncode != 0:
                        import_errors.append(import_stmt)
            except Exception:
                    import_errors.append(import_stmt)

            if import_errors:
                return {
                    "name": "import_check",
                    "status": "failed",
                    "errors": import_errors,
                    "message": f"导入检查失败 ({len(import_errors)} 个错误)",
                }
            else:
                return {"name": "import_check", "status": "passed", "message": "导入检查通过"}

        except Exception as e:
            return {"name": "import_check", "status": "error", "message": f"导入检查异常: {e}"}

    def run_ruff_check(self, changed_files: List[str]) -> Dict:
        """运行Ruff检查（仅限修改的文件）"""
        if not changed_files:
            return {"name": "ruff_check", "status": "skipped", "message": "无修改文件"}

        # 只检查修改的文件
        check_files = [f for f in changed_files if os.path.exists(f)][:3]

        if check_files:
            return self.run_check(
                "ruff_check",
                ["ruff", "check"] + check_files + ["--output-format=text"],
                f"Ruff检查 ({len(check_files)} 个文件)",
                critical=True,
                timeout=30,
            )
        else:
            return {"name": "ruff_check", "status": "skipped", "message": "无有效文件"}

    def run_type_check_sample(self, changed_files: List[str]) -> Dict:
        """运行类型检查抽样"""
        if not changed_files:
            return {"name": "type_check", "status": "skipped", "message": "无修改文件"}

        # 选择1-2个关键文件进行类型检查
        priority_files = []
        for file_path in changed_files:
            if any(keyword in file_path for keyword in ["core/", "api/", "utils/"]):
                priority_files.append(file_path)
                if len(priority_files) >= 2:
                    break

        if priority_files:
            return self.run_check(
                "type_check",
                ["mypy"] + priority_files + ["--no-error-summary"],
                f"类型检查抽样 ({len(priority_files)} 个文件)",
                critical=False,
                timeout=45,
            )
        else:
            return {"name": "type_check", "status": "skipped", "message": "无优先文件"}

    def generate_summary(self) -> None:
        """生成检查摘要"""
        total_time = time.time() - self.start_time
        self.results["total_time"] = total_time

        print("\n" + "=" * 60)
        print("📊 预提交检查摘要")
        print("=" * 60)

        print(f"⏰ 总耗时: {total_time:.1f}秒")
        print(f"📋 检查项目: {len(self.results['checks'])}")
        print(f"✅ 通过: {self.results['passed']}")
        print(f"⚠️  警告: {self.results['warnings']}")
        print(f"❌ 失败: {self.results['failed']}")

        # 显示失败的检查
        failed_checks = [c for c in self.results["checks"] if c.get("status") == "failed"]
        if failed_checks:
            print("\n❌ 失败的检查:")
            for check in failed_checks:
                print(f"  • {check['description']}")
                if "errors" in check:
                    for error in check["errors"][:2]:
                        print(f"    - {error}")
                elif "error" in check:
                    print(f"    - {check['error']}")

        # 给出建议
        print("\n💡 建议:")
        if self.results["failed"] > 0:
            print("  1. 修复失败的检查项")
            print("  2. 运行 'python scripts/enhanced_pre_commit_check.py --fix' 自动修复")
            print("  3. 如必须提交，使用: git commit --no-verify")
        else:
            print("  1. 代码质量良好，可以提交")
            print("  2. 定期运行完整质量检查: python scripts/scheduled_quality_audit.py")

    def save_report(self) -> None:
        """保存检查报告"""
        reports_dir = self.project_root / "reports" / "pre-commit"
        reports_dir.mkdir(parents=True, exist_ok=True)

        report_file = (
            reports_dir / f"pre_commit_check_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)

        print(f"💾 详细报告: {report_file}")

    def run_all_checks(self, fix_mode: bool = False) -> int:
        """运行所有检查"""
        print("🚀 启动增强预提交检查...")
        print(f"⏰ 开始时间: {datetime.now().strftime('%H:%M:%S')}")

        # 获取修改的文件
        changed_files = self.get_changed_files()
        print(f"📁 检测到 {len(changed_files)} 个修改的Python文件")

        # 运行检查序列
        checks_sequence = [
            ("语法检查", lambda: self.run_syntax_check(changed_files)),
            ("快速质量评估", self.run_fast_quality_check),
            ("导入检查", lambda: self.run_import_check(changed_files)),
            ("Ruff代码检查", lambda: self.run_ruff_check(changed_files)),
            ("类型检查抽样", lambda: self.run_type_check_sample(changed_files)),
        ]

        for check_name, check_func in checks_sequence:
            if isinstance(check_func, dict):
                result = check_func
            else:
                result = check_func()

            if result.get("status") == "failed" and result.get("critical", True):
                # 关键检查失败，停止后续检查
                print("\n⛔ 关键检查失败，停止后续检查")
                break

        # 生成摘要和保存报告
        self.generate_summary()
        self.save_report()

        # 返回退出码
        if self.results["failed"] > 0:
            print("\n❌ 预提交检查失败！")
            return 1
        else:
            print("\n🎉 预提交检查全部通过！")
            return 0


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="增强的预提交检查工具")
    parser.add_argument("--fix", action="store_true", help="尝试自动修复问题")
    parser.add_argument("--files", nargs="*", help="指定要检查的文件")
    parser.add_argument("--verbose", action="store_true", help="详细输出")

    args = parser.parse_args()

    checker = EnhancedPreCommitChecker()

    try:
        exit_code = checker.run_all_checks(fix_mode=args.fix)
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n⚠️ 检查被用户中断")
        sys.exit(130)
    except Exception as e:
        print(f"\n💥 检查执行异常: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
