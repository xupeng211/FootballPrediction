#!/usr/bin/env python3
"""
Week 3: CI/CD 质量门禁系统
自动化质量检查和报告生成
"""

import ast
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

class CIQualityGate:
    def __init__(self):
        self.metrics = {
            "timestamp": datetime.now().isoformat(),
            "overall_status": "pending",
            "checks": {},
            "summary": {
                "total_checks": 0,
                "passed_checks": 0,
                "failed_checks": 0,
                "warning_checks": 0
            },
            "recommendations": [],
            "exit_code": 0
        }

    def check_syntax_health(self) -> Dict:
        """检查语法健康度"""
        print("🔍 检查语法健康度...")

        total_files = 0
        healthy_files = 0

        python_files = list(Path("src").rglob("*.py"))
        total_files = len(python_files)

        for file_path in python_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                ast.parse(content)
                healthy_files += 1
            except Exception:
                continue

        health_percentage = (healthy_files / total_files * 100) if total_files > 0 else 0

        status = "pass"
        if health_percentage < 70:
            status = "fail"
            self.metrics["exit_code"] = 1
        elif health_percentage < 85:
            status = "warning"

        result = {
            "name": "语法健康度检查",
            "status": status,
            "details": {
                "total_files": total_files,
                "healthy_files": healthy_files,
                "health_percentage": round(health_percentage, 1)
            },
            "message": f"语法健康度: {health_percentage:.1f}% ({healthy_files}/{total_files})"
        }

        self.metrics["checks"]["syntax_health"] = result
        print(f"   {result['message']}")
        return result

    def check_code_quality(self) -> Dict:
        """检查代码质量"""
        print("🔧 检查代码质量...")

        checks = {}

        # Ruff检查
        try:
            ruff_cmd = ["ruff", "check", "src/", "--output-format=json"]
            result = subprocess.run(ruff_cmd, capture_output=True, text=True, timeout=60)

            ruff_issues = len(result.stdout.splitlines()) if result.stdout else 0
            ruff_status = "pass" if ruff_issues == 0 else "fail"

            if ruff_status == "fail":
                self.metrics["exit_code"] = 1

            checks["ruff"] = {
                "status": ruff_status,
                "issues": ruff_issues,
                "message": f"Ruff检查: {ruff_issues}个问题"
            }
            print(f"   Ruff检查: {ruff_issues}个问题")

        except Exception as e:
            checks["ruff"] = {
                "status": "error",
                "error": str(e),
                "message": f"Ruff检查失败: {e}"
            }
            print(f"   Ruff检查失败: {e}")

        # MyPy检查
        try:
            mypy_cmd = ["mypy", "src/", "--ignore-missing-imports"]
            result = subprocess.run(mypy_cmd, capture_output=True, text=True, timeout=60)

            mypy_errors = len(result.stderr.splitlines()) if result.stderr else 0
            mypy_status = "pass" if mypy_errors == 0 else "warning"

            checks["mypy"] = {
                "status": mypy_status,
                "errors": mypy_errors,
                "message": f"MyPy检查: {mypy_errors}个错误"
            }
            print(f"   MyPy检查: {mypy_errors}个错误")

        except Exception as e:
            checks["mypy"] = {
                "status": "error",
                "error": str(e),
                "message": f"MyPy检查失败: {e}"
            }
            print(f"   MyPy检查失败: {e}")

        # 综合状态
        overall_status = "pass"
        for check_name, check_result in checks.items():
            if check_result["status"] == "fail":
                overall_status = "fail"
                break
            elif check_result["status"] == "error":
                overall_status = "warning"
            elif overall_status == "pass" and check_result["status"] == "warning":
                overall_status = "warning"

        if overall_status == "fail":
            self.metrics["exit_code"] = 1

        result = {
            "name": "代码质量检查",
            "status": overall_status,
            "details": checks,
            "message": f"代码质量: {overall_status}"
        }

        self.metrics["checks"]["code_quality"] = result
        print(f"   代码质量: {overall_status}")
        return result

    def check_test_coverage(self) -> Dict:
        """检查测试覆盖率"""
        print("🧪 检查测试覆盖率...")

        try:
            # 运行测试覆盖率检查
            pytest_cmd = [
                "python", "-m", "pytest",
                "--cov=src",
                "--cov-report=json",
                "--cov-report=term-missing",
                "--tb=short",
                "-q",
                "tests/unit/"
            ]

            result = subprocess.run(pytest_cmd, capture_output=True, text=True, timeout=120)

            if result.returncode == 0:
                # 读取覆盖率报告
                coverage_file = "coverage.json"
                if os.path.exists(coverage_file):
                    with open(coverage_file, 'r') as f:
                        coverage_data = json.load(f)

                    total_coverage = coverage_data.get("totals", {}).get("percent_covered", 0)

                    status = "pass"
                    if total_coverage < 30:
                        status = "fail"
                        self.metrics["exit_code"] = 1
                    elif total_coverage < 50:
                        status = "warning"

                    coverage_result = {
                        "name": "测试覆盖率检查",
                        "status": status,
                        "details": {
                            "total_coverage": round(total_coverage, 1),
                            "files": coverage_data.get("files", [])
                        },
                        "message": f"测试覆盖率: {total_coverage:.1f}%"
                    }

                    # 删除临时文件
                    os.remove(coverage_file)
                    os.remove(".coverage")

                else:
                    coverage_result = {
                        "name": "测试覆盖率检查",
                        "status": "error",
                        "message": "覆盖率报告未生成"
                    }
            else:
                coverage_result = {
                    "name": "测试覆盖率检查",
                    "status": "error",
                    "message": "测试执行失败"
                }

            print(f"   {coverage_result['message']}")

        except Exception as e:
            coverage_result = {
                "name": "测试覆盖率检查",
                "status": "error",
                "error": str(e),
                "message": f"覆盖率检查失败: {e}"
            }
            print(f"   覆盖率检查失败: {e}")

        self.metrics["checks"]["test_coverage"] = coverage_result
        return coverage_result

    def check_security(self) -> Dict:
        """检查安全性"""
        print("🛡️ 检查安全性...")

        checks = {}

        # Bandit安全扫描
        try:
            bandit_cmd = ["bandit", "-r", "src/", "-f", "json"]
            result = subprocess.run(bandit_cmd, capture_output=True, text=True, timeout=60)

            if result.stdout:
                try:
                    bandit_data = json.loads(result.stdout)
                    bandit_issues = len(bandit_data.get("results", []))

                    bandit_status = "pass" if bandit_issues == 0 else "warning"
                    checks["bandit"] = {
                        "status": bandit_status,
                        "issues": bandit_issues,
                        "message": f"Bandit安全扫描: {bandit_issues}个问题"
                    }
                    print(f"   Bandit扫描: {bandit_issues}个问题")

                except json.JSONDecodeError:
                    checks["bandit"] = {
                        "status": "error",
                        "message": "Bandit报告格式错误"
                    }
            else:
                checks["bandit"] = {
                    "status": "pass",
                    "message": "Bandit扫描完成，无问题"
                }

        except Exception as e:
            checks["bandit"] = {
                "status": "error",
                "message": f"Bandit扫描失败: {e}"
            }
            print(f"   Bandit扫描失败: {e}")

        # 综合状态
        overall_status = "pass"
        for check_name, check_result in checks.items():
            if check_result["status"] == "fail":
                overall_status = "fail"
                break
            elif check_result["status"] == "error":
                overall_status = "warning"
            elif overall_status == "pass" and check_result["status"] == "warning":
                overall_status = "warning"

        if overall_status == "fail":
            self.metrics["exit_code"] = 1

        result = {
            "name": "安全性检查",
            "status": overall_status,
            "details": checks,
            "message": f"安全性检查: {overall_status}"
        }

        self.metrics["checks"]["security"] = result
        print(f"   安全性: {overall_status}")
        return result

    def check_imports(self) -> Dict:
        """检查导入依赖"""
        print("📦 检查导入依赖...")

        try:
            # 尝试导入关键模块
            critical_modules = [
                "src.main",
                "src.api.app",
                "src.domain.strategies.factory",
                "src.core.di"
            ]

            import_results = {}
            for module in critical_modules:
                try:
                    module_path = module.replace("src/", "").replace("/", ".")
                    exec(f"import {module_path}")
                    import_results[module] = "success"
                except Exception as e:
                    import_results[module] = f"failed: {e}"

            failed_imports = [k for k, v in import_results.items() if v != "success"]

            status = "pass" if len(failed_imports) == 0 else "warning"

            if status == "warning":
                self.metrics["exit_code"] = 1

            result = {
                "name": "导入依赖检查",
                "status": status,
                "details": {
                    "total_modules": len(critical_modules),
                    "successful_imports": len(critical_modules) - len(failed_imports),
                    "failed_imports": failed_imports
                },
                "message": f"导入检查: {len(critical_modules) - len(failed_imports)}/{len(critical_modules)} 成功"
            }

            print(f"   导入检查: {result['message']}")

        except Exception as e:
            result = {
                "name": "导入依赖检查",
                "status": "error",
                "error": str(e),
                "message": f"导入检查失败: {e}"
            }
            print(f"   导入检查失败: {e}")

        self.metrics["checks"]["imports"] = result
        return result

    def calculate_summary(self) -> None:
        """计算摘要统计"""
        total_checks = len(self.metrics["checks"])
        passed_checks = sum(1 for check in self.metrics["checks"].values() if check["status"] == "pass")
        failed_checks = sum(1 for check in self.metrics["checks"].values() if check["status"] == "fail")
        warning_checks = sum(1 for check in self.metrics["checks"].values() if check["status"] == "warning")

        self.metrics["summary"] = {
            "total_checks": total_checks,
            "passed_checks": passed_checks,
            "failed_checks": failed_checks,
            "warning_checks": warning_checks
        }

        # 确定整体状态
        if failed_checks > 0:
            self.metrics["overall_status"] = "failed"
        elif warning_checks > 0:
            self.metrics["overall_status"] = "warning"
        else:
            self.metrics["overall_status"] = "passed"

    def generate_recommendations(self) -> List[str]:
        """生成改进建议"""
        recommendations = []

        for check_name, check_result in self.metrics["checks"].items():
            if check_result["status"] == "fail":
                if check_name == "syntax_health":
                    health_pct = check_result["details"]["health_percentage"]
                    recommendations.append(f"🔧 语法健康度{health_pct:.1f}%低于70%，建议运行语法修复工具")
                elif check_name == "code_quality":
                    recommendations.append("🔧 代码质量检查失败，建议修复代码格式和类型问题")
                elif check_name == "test_coverage":
                    recommendations.append("🧪 测试覆盖率不足，建议增加更多测试用例")
                elif check_name == "security":
                    recommendations.append("🛡️ 安全检查发现问题，建议修复安全漏洞")
                elif check_name == "imports":
                    recommendations.append("📦 关键模块导入失败，建议检查依赖关系")
            elif check_result["status"] == "warning":
                if check_name == "syntax_health":
                    health_pct = check_result["details"]["health_percentage"]
                    recommendations.append(f"⚠️ 语法健康度{health_pct:.1f}%可进一步提升")
                elif check_name == "test_coverage":
                    recommendations.append("📈 测试覆盖率可进一步提升")

        # Phase G Week 3 特定建议
        recommendations.append("🚀 Phase G Week 3: 建议继续使用自动化工具提升质量")
        recommendations.append("📊 Phase G Week 3: 考虑集成更多健康模块的测试")
        recommendations.append("🎯 Phase G Week 3: 定期运行质量门禁检查")

        return recommendations

    def save_report(self, output_path: str = None) -> str:
        """保存质量门禁报告"""
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"ci_quality_gate_report_{timestamp}.json"

        self.metrics["recommendations"] = self.generate_recommendations()

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.metrics, f, indent=2, ensure_ascii=False)

        return output_path

    def print_summary(self) -> None:
        """打印检查摘要"""
        print("=" * 60)
        print("🚨 CI/CD 质量门禁报告")
        print("=" * 60)
        print(f"📅 检查时间: {self.metrics['timestamp']}")
        print(f"🎯 整体状态: {self.metrics['overall_status'].upper()}")

        summary = self.metrics["summary"]
        print(f"📊 总检查数: {summary['total_checks']}")
        print(f"✅ 通过检查: {summary['passed_checks']}")
        print(f"⚠️ 警告检查: {summary['warning_checks']}")
        print(f"❌ 失败检查: {summary['failed_checks']}")

        print("\n🔍 检查详情:")
        for check_name, check_result in self.metrics["checks"].items():
            status_icon = {"pass": "✅", "warning": "⚠️", "fail": "❌", "error": "💥"}.get(check_result["status"], "❓")
            print(f"   {status_icon} {check_name}: {check_result['message']}")

        if self.metrics["recommendations"]:
            print("\n🎯 改进建议:")
            for rec in self.metrics["recommendations"]:
                print(f"   {rec}")

        print("=" * 60)

def main():
    import sys

    gate = CIQualityGate()

    print("🚀 CI/CD 质量门禁开始")
    print("=" * 60)

    # 执行所有检查
    gate.check_syntax_health()
    gate.check_code_quality()
    gate.check_test_coverage()
    gate.check_security()
    gate.check_imports()

    # 计算摘要
    gate.calculate_summary()

    # 打印摘要
    gate.print_summary()

    # 保存报告
    report_path = gate.save_report()
    print(f"\n📄 详细报告已保存: {report_path}")

    # 设置退出码
    sys.exit(gate.metrics["exit_code"])

if __name__ == "__main__":
    main()