#!/usr/bin/env python3
"""
模块导入完整性验证脚本
Module Import Integrity Validator

全面验证整个项目的模块导入关系完整性.
"""

import sys
import importlib
import traceback
import time
from pathlib import Path
from typing import Dict, List, Tuple, Any
from dataclasses import dataclass
import json

# 添加src路径到Python路径
src_path = Path(__file__).parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))


@dataclass
class ModuleValidationResult:
    """模块验证结果"""
    module_path: str
    success: bool = False
    error_message: str = ""
    import_time: float = 0.0
    dependencies: List[str] = None
    issues: List[str] = None

    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []
        if self.issues is None:
            self.issues = []


class ModuleIntegrityValidator:
    """模块完整性验证器"""

    def __init__(self):
        """初始化验证器"""
        self.src_path = Path("src")
        self.results: Dict[str, ModuleValidationResult] = {}
        self.total_modules = 0
        self.success_count = 0
        self.failure_count = 0
        self.start_time = 0

    def validate_module_import(self, module_path: str) -> ModuleValidationResult:
        """验证单个模块导入

        Args:
            module_path: 模块路径 (如 'domain.models.match')

        Returns:
            ModuleValidationResult: 验证结果
        """
        result = ModuleValidationResult(module_path=module_path)

        try:
            start_time = time.time()

            # 尝试导入模块
            module = importlib.import_module(module_path)

            # 记录导入时间
            result.import_time = time.time() - start_time
            result.success = True

            # 收集依赖信息
            if hasattr(module, '__all__'):
                result.dependencies = list(module.__all__)

            # 检查常见问题
            result.issues = self._check_module_issues(module)

        except ImportError as e:
            result.success = False
            result.error_message = f"导入错误: {str(e)}"
        except SyntaxError as e:
            result.success = False
            result.error_message = f"语法错误: {str(e)}"
        except Exception as e:
            result.success = False
            result.error_message = f"未知错误: {str(e)}"
            # 记录详细错误信息
            result.error_message += f"\n详细错误:\n{traceback.format_exc()}"

        return result

    def _check_module_issues(self, module) -> List[str]:
        """检查模块的常见问题

        Args:
            module: 已导入的模块对象

        Returns:
            List[str]: 发现的问题列表
        """
        issues = []

        # 检查是否有空的__all__
        if hasattr(module, '__all__') and not module.__all__:
            issues.append("__all__为空")

        # 检查模块文档
        if not hasattr(module, '__doc__') or not module.__doc__:
            issues.append("缺少模块文档")

        # 检查是否有未处理的导入
        try:
            import inspect
            members = inspect.getmembers(module)
            classes = [name for name, obj in members if inspect.isclass(obj)]

            if not classes and hasattr(module, '__all__'):
                issues.append("模块可能缺少核心类定义")
        except:
            pass

        return issues

    def validate_directory(self, directory: Path, prefix: str = "") -> List[ModuleValidationResult]:
        """验证目录中的所有Python模块

        Args:
            directory: 目录路径
            prefix: 模块前缀

        Returns:
            List[ModuleValidationResult]: 验证结果列表
        """
        results = []

        for py_file in directory.rglob("*.py"):
            if py_file.name == "__init__.py":
                continue

            # 构建模块路径
            relative_path = py_file.relative_to(self.src_path)
            module_path = str(relative_path.with_suffix("")).replace("/", ".")

            if prefix:
                module_path = f"{prefix}.{module_path}"

            result = self.validate_module_import(module_path)
            results.append(result)

            # 更新计数器
            self.total_modules += 1
            if result.success:
                self.success_count += 1
            else:
                self.failure_count += 1

        return results

    def run_validation(self) -> Dict[str, Any]:
        """运行完整验证

        Returns:
            Dict[str, Any]: 验证报告
        """
        self.start_time = time.time()
        print("🚀 开始模块导入完整性验证...")
        print("=" * 60)

        # 定义验证范围
        validation_areas = [
            ("核心模块 (P0)", [
                "src/domain",
                "src/api",
                "src/services",
                "src/database"
            ]),
            ("支撑模块 (P1)", [
                "src/facades",
                "src/patterns",
                "src/cache",
                "src/middleware"
            ]),
            ("工具模块 (P2)", [
                "src/utils",
                "src/config",
                "src/core"
            ])
        ]

        area_results = {}

        for area_name, directories in validation_areas:
            print(f"\n📋 验证 {area_name}")
            print("-" * 40)

            area_success = 0
            area_total = 0

            for directory in directories:
                dir_path = Path(directory)
                if dir_path.exists():
                    print(f"  🔍 检查目录: {directory}")

                    results = self.validate_directory(dir_path)
                    area_success += sum(1 for r in results if r.success)
                    area_total += len(results)

                    # 记录失败的模块
                    failed_results = [r for r in results if not r.success]
                    if failed_results:
                        print(f"    ❌ 失败模块: {len(failed_results)} 个")
                        for fail in failed_results[:3]:  # 只显示前3个
                            print(f"      - {fail.module_path}: {fail.error_message[:80]}...")
                    else:
                        print(f"    ✅ 全部成功: {len(results)} 个模块")

                    # 保存结果
                    for result in results:
                        self.results[result.module_path] = result
                else:
                    print(f"  ⚠️  目录不存在: {directory}")

            # 计算区域统计
            success_rate = (area_success / area_total * 100) if area_total > 0 else 0
            area_results[area_name] = {
                "total": area_total,
                "success": area_success,
                "success_rate": success_rate,
                "failed": area_total - area_success
            }

            print(f"  📊 {area_name} 成功率: {success_rate:.1f}% ({area_success}/{area_total})")

        # 生成最终报告
        total_time = time.time() - self.start_time
        overall_success_rate = (self.success_count / self.total_modules * 100) if self.total_modules > 0 else 0

        report = {
            "summary": {
                "total_modules": self.total_modules,
                "success_count": self.success_count,
                "failure_count": self.failure_count,
                "success_rate": overall_success_rate,
                "validation_time": total_time
            },
            "area_results": area_results,
            "failed_modules": self._get_failed_modules(),
            "issues_summary": self._get_issues_summary()
        }

        return report

    def _get_failed_modules(self) -> List[Dict[str, Any]]:
        """获取失败的模块列表

        Returns:
            List[Dict[str, Any]]: 失败模块信息
        """
        failed = []

        for result in self.results.values():
            if not result.success:
                failed.append({
                    "module": result.module_path,
                    "error": result.error_message,
                    "import_time": result.import_time
                })

        return failed

    def _get_issues_summary(self) -> Dict[str, Any]:
        """获取问题摘要

        Returns:
            Dict[str, Any]: 问题摘要
        """
        total_issues = 0
        issue_types = {}

        for result in self.results.values():
            if result.issues:
                total_issues += len(result.issues)
                for issue in result.issues:
                    issue_types[issue] = issue_types.get(issue, 0) + 1

        return {
            "total_issues": total_issues,
            "issue_types": issue_types,
            "modules_with_issues": len([r for r in self.results.values() if r.issues])
        }

    def print_report(self, report: Dict[str, Any]) -> None:
        """打印验证报告

        Args:
            report: 验证报告
        """
        print("\n" + "=" * 60)
        print("📊 模块导入完整性验证报告")
        print("=" * 60)

        # 总体统计
        summary = report["summary"]
        print(f"\n📈 总体统计:")
        print(f"  ✅ 总模块数: {summary['total_modules']}")
        print(f"  ✅ 成功导入: {summary['success_count']}")
        print(f"  ❌ 导入失败: {summary['failure_count']}")
        print(f"  📊 成功率: {summary['success_rate']:.1f}%")
        print(f"  ⏱️  验证耗时: {summary['validation_time']:.2f} 秒")

        # 区域统计
        print(f"\n📂 各区域统计:")
        for area_name, stats in report["area_results"].items():
            status_icon = "✅" if stats["success_rate"] >= 90 else "⚠️" if stats["success_rate"] >= 70 else "❌"
            print(f"  {status_icon} {area_name}:")
            print(f"    成功率: {stats['success_rate']:.1f}% ({stats['success']}/{stats['total']})")
            if stats["failed"] > 0:
                print(f"    失败数: {stats['failed']}")

        # 失败模块
        failed_modules = report["failed_modules"]
        if failed_modules:
            print(f"\n🚨 失败模块列表 ({len(failed_modules)} 个):")
            for i, fail in enumerate(failed_modules[:10]):  # 只显示前10个
                print(f"  {i+1:2d}. {fail['module']}")
                print(f"      错误: {fail['error'][:80]}...")

            if len(failed_modules) > 10:
                print(f"  ... 还有 {len(failed_modules) - 10} 个失败模块")
        else:
            print(f"\n🎉 恭喜！所有模块导入成功！")

        # 问题摘要
        issues = report["issues_summary"]
        if issues["total_issues"] > 0:
            print(f"\n⚠️  发现的问题 ({issues['total_issues']} 个):")
            for issue_type, count in issues["issue_types"].items():
                print(f"  - {issue_type}: {count} 次")
        else:
            print(f"\n✅ 未发现明显问题")

        # 健康度评估
        print(f"\n🏥 健康度评估:")
        success_rate = summary["success_rate"]
        if success_rate >= 95:
            print("  🟢 优秀: 系统健康状况极佳")
        elif success_rate >= 85:
            print("  🟡 良好: 系统基本健康，有少量问题")
        elif success_rate >= 70:
            print("  🟠 一般: 系统存在较多问题，需要关注")
        else:
            print("  🔴 较差: 系统存在严重问题，需要立即处理")


def main():
    """主函数"""
    validator = ModuleIntegrityValidator()

    try:
        # 运行验证
        report = validator.run_validation()

        # 打印报告
        validator.print_report(report)

        # 保存详细报告到文件
        report_file = Path("module_integrity_validation_report.json")
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        print(f"\n📄 详细报告已保存到: {report_file}")

        # 返回退出码
        if report["summary"]["success_rate"] >= 90:
            print("\n✅ 验证通过！")
            return 0
        else:
            print("\n⚠️  验证发现问题，建议修复后重新验证")
            return 1

    except Exception as e:
        print(f"\n❌ 验证过程出错: {e}")
        traceback.print_exc()
        return 2


if __name__ == "__main__":
    exit(main())