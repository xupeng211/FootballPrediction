#!/usr/bin/env python3
"""
综合测试运行器
Comprehensive Test Runner
"""

import subprocess
import sys
import time
from pathlib import Path


class TestRunner:
    """测试运行器"""

    def __init__(self):
        self.results = {}
        self.start_time = time.time()

    def run_command(self, name: str, cmd: list[str], description: str) -> bool:
        """运行命令并记录结果"""
        print(f"\n{'='*60}")
        print(f"运行: {description}")
        print(f"命令: {' '.join(cmd)}")
        print("=" * 60)

        try:
            start = time.time()
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            duration = time.time() - start

            success = result.returncode == 0

            self.results[name] = {
                "success": success,
                "duration": duration,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "description": description,
            }

            # 打印结果摘要
            if success:
                print(f"✅ 成功 ({duration:.2f}秒)")
                if result.stdout:
                    # 提取关键信息
                    lines = result.stdout.split("\n")
                    for line in lines[-20:]:  # 显示最后20行
                        if line.strip():
                            print(f"  {line}")
            else:
                print(f"❌ 失败 ({duration:.2f}秒)")
                if result.stderr:
                    print("错误信息:")
                    for line in result.stderr.split("\n")[:10]:
                        if line.strip():
                            print(f"  {line}")

            return success

        except subprocess.TimeoutExpired:
            print("⏰ 超时（300秒）")
            self.results[name] = {
                "success": False,
                "duration": 300,
                "stdout": "",
                "stderr": "Timeout after 300 seconds",
                "description": description,
            }
            return False
        except Exception as e:
            print(f"❌ 异常: {e}")
            self.results[name] = {
                "success": False,
                "duration": 0,
                "stdout": "",
                "stderr": str(e),
                "description": description,
            }
            return False

    def run_tests(self):
        """运行所有测试"""
        print("\n🚀 开始综合测试")
        print(f"开始时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")

        # 1. 基础模块测试
        self.run_command(
            "unit_tests",
            ["python", "-m", "pytest", "tests/unit/utils/", "-v", "--tb=short"],
            "单元测试 - utils模块",
        )

        # 2. 代码质量检查
        self.run_command(
            "lint_check",
            ["python", "-m", "ruff", "check", "src/utils/", "--no-fix"],
            "代码质量检查 - ruff",
        )

        # 3. 类型检查
        self.run_command(
            "type_check",
            ["python", "-m", "mypy", "src/utils/", "--ignore-missing-imports"],
            "类型检查 - MyPy",
        )

        # 4. 测试覆盖率
        self.run_command(
            "coverage",
            [
                "python",
                "-m",
                "pytest",
                "tests/unit/utils/",
                "--cov=src.utils",
                "--cov-report=term-missing",
                "--cov-report=html",
            ],
            "测试覆盖率",
        )

        # 5. 缓存功能测试
        self.run_command(
            "cache_test", ["python", "src/utils/cached_operations.py"], "缓存功能测试"
        )

        # 6. Redis连接测试（如果有Redis）
        print("\n" + "=" * 60)
        print("测试Redis连接...")
        try:
            from src.utils.redis_cache import get_redis_client

            redis = get_redis_client()
            if redis.ping():
                print("✅ Redis连接成功")
                self.results["redis"] = {
                    "success": True,
                    "description": "Redis连接测试",
                }
            else:
                print("⚠️ Redis连接失败（可能未启动）")
                self.results["redis"] = {
                    "success": False,
                    "description": "Redis连接失败",
                }
        except Exception as e:
            print(f"⚠️ Redis测试跳过: {e}")
            self.results["redis"] = {
                "success": False,
                "description": f"Redis不可用: {e}",
            }

    def generate_report(self):
        """生成测试报告"""
        total_duration = time.time() - self.start_time
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results.values() if r["success"])

        print("\n" + "=" * 60)
        print("           测试报告摘要")
        print("=" * 60)
        print(f"总耗时: {total_duration:.2f}秒")
        print(f"测试项目: {total_tests}")
        print(f"通过: {passed_tests}")
        print(f"失败: {total_tests - passed_tests}")
        print(f"成功率: {passed_tests/total_tests*100:.1f}%")

        print("\n详细结果:")
        for name, result in self.results.items():
            status = "✅ 通过" if result["success"] else "❌ 失败"
            duration = result.get("duration", 0)
            print(
                f"  {name:20} {status:10} ({duration:.2f}s) - {result['description']}"
            )

        # 生成Markdown报告
        self.generate_markdown_report()

    def generate_markdown_report(self):
        """生成Markdown格式的报告"""
        report_path = Path("test_report.md")

        with open(report_path, "w", encoding="utf-8") as f:
            f.write("# 综合测试报告\n\n")
            f.write(f"**测试时间**: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")

            # 摘要
            total_tests = len(self.results)
            passed_tests = sum(1 for r in self.results.values() if r["success"])

            f.write("## 测试摘要\n\n")
            f.write("| 指标 | 值 |\n")
            f.write("|------|----|\n")
            f.write(f"| 总测试数 | {total_tests} |\n")
            f.write(f"| 通过数 | {passed_tests} |\n")
            f.write(f"| 失败数 | {total_tests - passed_tests} |\n")
            f.write(f"| 成功率 | {passed_tests/total_tests*100:.1f}% |\n\n")

            # 详细结果
            f.write("## 详细结果\n\n")
            for name, result in self.results.items():
                status = "✅ 通过" if result["success"] else "❌ 失败"
                f.write(f"### {name}\n\n")
                f.write(f"- **状态**: {status}\n")
                f.write(f"- **描述**: {result['description']}\n")
                f.write(f"- **耗时**: {result.get('duration', 0):.2f}秒\n\n")

                if not result["success"] and result["stderr"]:
                    f.write("**错误信息**:\n```\n")
                    f.write(result["stderr"][:500])
                    if len(result["stderr"]) > 500:
                        f.write("\n...")
                    f.write("\n```\n\n")

        print(f"\n📄 测试报告已保存到: {report_path}")


def main():
    """主函数"""
    runner = TestRunner()

    # 运行所有测试
    runner.run_tests()

    # 生成报告
    runner.generate_report()

    # 返回适当的退出码
    failed_count = sum(1 for r in runner.results.values() if not r["success"])
    if failed_count > 0:
        print(f"\n⚠️ 有 {failed_count} 个测试失败")
        sys.exit(1)
    else:
        print("\n🎉 所有测试通过！")
        sys.exit(0)


if __name__ == "__main__":
    main()
