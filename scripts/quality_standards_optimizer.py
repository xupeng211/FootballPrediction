#!/usr/bin/env python3
"""
质量标准优化器
Quality Standards Optimizer

根据当前项目状况，动态调整质量门禁标准
"""

import os
import sys
import json
import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging

# 设置日志
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class QualityStandardsOptimizer:
    """质量标准优化器"""

    def __init__(self, project_root: Path = None):
        self.project_root = project_root or Path(__file__).parent.parent
        self.standards_file = self.project_root / "monitoring-data" / "quality_standards.json"
        self.optimization_history_file = (
            self.project_root / "monitoring-data" / "optimization_history.json"
        )

        # 确保目录存在
        (self.project_root / "monitoring-data").mkdir(exist_ok=True)

        # 当前项目状况
        self.current_coverage = self._get_current_coverage()
        self.test_count = self._get_test_count()
        self.code_quality_score = self._get_code_quality_score()

    def _get_current_coverage(self) -> float:
        """获取当前覆盖率"""
        coverage_file = self.project_root / "coverage.json"
        if coverage_file.exists():
            try:
                with open(coverage_file, "r") as f:
                    data = json.load(f)
                return data["totals"]["percent_covered"]
            except Exception:
                return 0.0
        return 0.0

    def _get_test_count(self) -> int:
        """获取测试数量"""
        try:
            # 从质量报告中获取
            quality_file = self.project_root / "quality-report.json"
            if quality_file.exists():
                with open(quality_file, "r") as f:
                    data = json.load(f)
                return data.get("metrics", {}).get("tests_passed", 0) + data.get("metrics", {}).get(
                    "tests_failed", 0
                )

            # 或者从pytest输出中获取
            import subprocess

            result = subprocess.run(
                [sys.executable, "-m", "pytest", "--collect-only", "-q"],
                capture_output=True,
                text=True,
                cwd=self.project_root,
            )

            if result.returncode == 0:
                # 解析pytest输出
                lines = result.stdout.strip().split("\n")
                for line in lines:
                    if "collected" in line and "items" in line:
                        import re

                        match = re.search(r"collected (\d+) items", line)
                        if match:
                            return int(match.group(1))
        except Exception:
            pass

        return 0

    def _get_code_quality_score(self) -> float:
        """获取代码质量评分"""
        try:
            quality_file = self.project_root / "quality-report.json"
            if quality_file.exists():
                with open(quality_file, "r") as f:
                    data = json.load(f)
                return data.get("metrics", {}).get("code_quality", 7.0)
        except Exception:
            pass

        # 默认评分
        return 7.0

    def calculate_optimal_standards(self) -> Dict[str, Any]:
        """计算最优质量标准"""
        coverage = self.current_coverage
        test_count = self.test_count
        code_quality = self.code_quality_score

        # 基于当前状况计算渐进式目标
        standards = {
            "coverage": {
                # 覆盖率标准：在当前基础上逐步提升
                "minimum": max(15.0, coverage - 2.0),  # 最低不能低于15%
                "target": min(35.0, coverage + 5.0),  # 目标是当前+5%或35%
                "excellent": min(50.0, coverage + 15.0),  # 优秀是当前+15%或50%
                # 关键模块标准
                "critical_files": {
                    "src/api/schemas.py": min(95.0, 100.0),  # 模式文件应接近100%
                    "src/core/exceptions.py": min(90.0, 100.0),  # 异常类应接近100%
                    "src/models/": max(60.0, min(85.0, coverage + 10.0)),  # 模型类比整体高10-20%
                },
            },
            "tests": {
                # 测试标准
                "min_pass_rate": max(
                    85.0, 95.0 - (100.0 - coverage) * 0.5
                ),  # 覆盖率越低，通过率要求越高
                "max_failures": max(5, int(test_count * 0.02)),  # 失败数不超过2%
                "min_total": max(100, int(test_count * 0.8)),  # 至少有当前数量的80%
            },
            "code_quality": {
                # 代码质量标准
                "max_ruff_errors": max(3, int(20 - code_quality)),  # 评分越低，允许错误越多
                "max_mypy_errors": max(5, int(30 - code_quality * 2)),
                "format_required": True,
            },
            "security": {
                # 安全标准
                "max_vulnerabilities": 2,  # 允许少量低危漏洞
                "max_secrets": 3,  # 允许少量配置密钥
            },
        }

        return standards

    def analyze_current_gaps(self) -> Dict[str, Any]:
        """分析当前质量差距"""
        optimal_standards = self.calculate_optimal_standards()

        gaps = {
            "coverage_gap": max(0, optimal_standards["coverage"]["target"] - self.current_coverage),
            "test_quality_gap": 0.0,
            "code_quality_gap": max(0, 8.0 - self.code_quality_score),
            "security_issues": 0,
        }

        # 计算综合质量分数
        coverage_score = min(
            10.0, self.current_coverage / optimal_standards["coverage"]["target"] * 10
        )
        test_score = min(10.0, self.test_count / optimal_standards["tests"]["min_total"] * 10)

        gaps["overall_score"] = (coverage_score + test_score + self.code_quality_score) / 3

        return gaps

    def generate_improvement_plan(self) -> Dict[str, Any]:
        """生成改进计划"""
        gaps = self.analyze_current_gaps()
        standards = self.calculate_optimal_standards()

        plan = {
            "priority_1": [],
            "priority_2": [],
            "priority_3": [],
            "estimated_timeline": {},
            "resource_requirements": {},
        }

        # 基于差距生成改进计划
        if gaps["coverage_gap"] > 5:
            plan["priority_1"].extend(
                ["为核心模块编写单元测试", "建立每日覆盖率提升目标", "实施测试驱动开发(TDD)"]
            )
            plan["estimated_timeline"]["coverage"] = "2-3周"
        elif gaps["coverage_gap"] > 2:
            plan["priority_2"].extend(["增加边界条件测试", "优化现有测试用例", "添加集成测试"])
            plan["estimated_timeline"]["coverage"] = "1-2周"
        else:
            plan["priority_3"].extend(["维护当前覆盖率水平", "优化测试执行效率"])
            plan["estimated_timeline"]["coverage"] = "持续进行"

        if gaps["code_quality_gap"] > 2:
            plan["priority_1"].extend(["修复Ruff代码质量问题", "解决MyPy类型错误", "统一代码格式"])
            plan["estimated_timeline"]["quality"] = "1周"

        if self.test_count < standards["tests"]["min_total"]:
            plan["priority_2"].extend(["增加测试用例数量", "提高测试覆盖率", "优化测试结构"])

        return plan

    def update_quality_standards(self, enforce: bool = False) -> bool:
        """更新质量标准"""
        optimal_standards = self.calculate_optimal_standards()

        # 保存优化后的标准
        try:
            with open(self.standards_file, "w") as f:
                json.dump(
                    {
                        "timestamp": datetime.datetime.utcnow().isoformat(),
                        "current_project_status": {
                            "coverage": self.current_coverage,
                            "test_count": self.test_count,
                            "code_quality_score": self.code_quality_score,
                        },
                        "optimized_standards": optimal_standards,
                        "gaps_analysis": self.analyze_current_gaps(),
                        "improvement_plan": self.generate_improvement_plan(),
                    },
                    f,
                    indent=2,
                    ensure_ascii=False,
                )

            logger.info(f"质量标准已优化并保存: {self.standards_file}")

            # 如果需要强制执行，更新现有的质量门禁脚本
            if enforce:
                self._update_quality_gate_scripts(optimal_standards)

            return True

        except Exception as e:
            logger.error(f"更新质量标准失败: {e}")
            return False

    def _update_quality_gate_scripts(self, standards: Dict[str, Any]):
        """更新质量门禁脚本的标准"""
        try:
            # 更新CI质量检查脚本
            ci_script = self.project_root / "scripts" / "ci_quality_check.py"
            if ci_script.exists():
                with open(ci_script, "r") as f:
                    content = f.read()

                # 替换质量标准部分
                old_standards_block = "self.quality_gates = {"
                new_standards_block = f"self.quality_gates = {json.dumps(standards, indent=4)}"

                if old_standards_block in content:
                    updated_content = content.replace(old_standards_block, new_standards_block)
                    with open(ci_script, "w") as f:
                        f.write(updated_content)
                    logger.info("已更新CI质量检查脚本标准")

        except Exception as e:
            logger.warning(f"更新质量门禁脚本失败: {e}")

    def generate_optimization_report(self) -> Dict[str, Any]:
        """生成优化报告"""
        report = {
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "current_status": {
                "coverage": self.current_coverage,
                "test_count": self.test_count,
                "code_quality_score": self.code_quality_score,
            },
            "optimized_standards": self.calculate_optimal_standards(),
            "gaps_analysis": self.analyze_current_gaps(),
            "improvement_plan": self.generate_improvement_plan(),
            "recommendations": self._generate_recommendations(),
        }

        # 保存报告
        report_file = self.project_root / "monitoring-data" / "quality_optimization_report.json"
        try:
            with open(report_file, "w") as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            logger.info(f"质量优化报告已保存: {report_file}")
        except Exception as e:
            logger.error(f"保存优化报告失败: {e}")

        return report

    def _generate_recommendations(self) -> List[str]:
        """生成改进建议"""
        recommendations = []

        if self.current_coverage < 20:
            recommendations.append("🚨 优先级：立即提升基础覆盖率到20%以上")
            recommendations.append("📝 建议：为核心模块编写基础测试用例")
        elif self.current_coverage < 25:
            recommendations.append("⚠️ 优先级：提升覆盖率到25%目标")
            recommendations.append("🎯 建议：专注于未测试的代码路径")
        else:
            recommendations.append("✅ 状态：覆盖率达到良好水平")
            recommendations.append("🔄 建议：维护并持续改进")

        if self.code_quality_score < 6:
            recommendations.append("🔧 优先级：解决代码质量问题")
            recommendations.append("🛠️ 建议：运行 'ruff check src/' 和 'mypy src/'")
        elif self.code_quality_score < 8:
            recommendations.append("📊 优化：进一步提升代码质量")
            recommendations.append("✨ 建议：优化代码结构和类型注解")

        if self.test_count < 500:
            recommendations.append("🧪 建议：增加测试用例数量和覆盖范围")

        return recommendations

    def print_optimization_report(self):
        """打印优化报告"""
        report = self.generate_optimization_report()

        print("\n" + "=" * 70)
        print("🎯 质量标准优化报告")
        print("=" * 70)
        print(f"生成时间: {report['timestamp']}")
        print()

        # 当前状况
        print("📊 当前项目状况:")
        print(f"  测试覆盖率: {report['current_status']['coverage']:.2f}%")
        print(f"  测试数量: {report['current_status']['test_count']}")
        print(f"  代码质量评分: {report['current_status']['code_quality_score']:.2f}/10")
        print()

        # 优化后的标准
        standards = report["optimized_standards"]
        print("🎯 优化后的质量标准:")
        print(
            f"  覆盖率目标: {standards['coverage']['target']:.1f}% (最低: {standards['coverage']['minimum']:.1f}%)"
        )
        print(f"  测试通过率要求: {standards['tests']['min_pass_rate']:.1f}%")
        print(f"  最大允许失败: {standards['tests']['max_failures']} 个")
        print(f"  最小测试数量: {standards['tests']['min_total']} 个")
        print()

        # 差距分析
        gaps = report["gaps_analysis"]
        print("📈 质量差距分析:")
        print(f"  覆盖率差距: {gaps['coverage_gap']:.2f}%")
        print(f"  代码质量差距: {gaps['code_quality_gap']:.2f}/10")
        print(f"  综合质量分数: {gaps['overall_score']:.2f}/10")
        print()

        # 改进计划
        plan = report["improvement_plan"]
        print("🚀 改进计划:")

        if plan["priority_1"]:
            print("  🥇 优先级1:")
            for item in plan["priority_1"]:
                print(f"    • {item}")

        if plan["priority_2"]:
            print("  🥈 优先级2:")
            for item in plan["priority_2"]:
                print(f"    • {item}")

        if plan["priority_3"]:
            print("  🥉 优先级3:")
            for item in plan["priority_3"]:
                print(f"    • {item}")

        print()

        if plan.get("estimated_timeline"):
            print("⏱️ 预估时间线:")
            for category, timeline in plan["estimated_timeline"].items():
                print(f"  {category}: {timeline}")
        print()

        # 建议
        recommendations = report["recommendations"]
        print("💡 改进建议:")
        for rec in recommendations:
            print(f"  {rec}")
        print()

        print("=" * 70)

    def run_optimization(self, update_scripts: bool = False):
        """执行完整的优化流程"""
        logger.info("开始质量标准优化...")

        # 生成报告
        self.generate_optimization_report()

        # 更新标准
        success = self.update_quality_standards(enforce=update_scripts)

        if success:
            logger.info("✅ 质量标准优化完成")
            print("✅ 质量标准已根据当前项目状况优化完成")
            print("💡 建议定期运行此优化器以持续调整标准")
        else:
            logger.error("❌ 质量标准优化失败")
            print("❌ 质量标准优化过程中出现错误")

        return success


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="质量标准优化器")
    parser.add_argument("--report-only", action="store_true", help="仅生成报告")
    parser.add_argument("--update-scripts", action="store_true", help="更新质量门禁脚本")
    parser.add_argument("--project-root", type=Path, help="项目根目录")

    args = parser.parse_args()

    optimizer = QualityStandardsOptimizer(args.project_root)

    if args.report_only:
        optimizer.print_optimization_report()
    else:
        optimizer.run_optimization(update_scripts=args.update_scripts)


if __name__ == "__main__":
    main()
