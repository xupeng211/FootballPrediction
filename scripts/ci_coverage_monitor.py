#!/usr/bin/env python3
"""
CI/CD覆盖率监控集成脚本
CI/CD Coverage Monitoring Integration Script

基于Issue #98方法论，为CI/CD流水线提供实时覆盖率监控
"""

import os
import sys
import json
import time
import argparse
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging

# 设置日志
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class CICoverageMonitor:
    """CI/CD覆盖率监控器 - 基于Issue #98方法论"""

    def __init__(self, project_root: Path = None):
        self.project_root = project_root or Path(__file__).parent.parent
        self.coverage_data = {}
        self.targets = {
            "current": 15.0,  # Issue #94当前目标
            "phase6": 35.0,  # Phase 6目标
            "phase5_modules": {
                "crypto_utils": 50.0,
                "dict_utils": 60.0,
                "file_utils": 55.0,
                "time_utils": 71.19,
                "string_utils": 55.86,
                "validators": 93.55,
            },
        }

    def run_coverage_analysis(self, analysis_level: str = "standard") -> Dict[str, Any]:
        """运行覆盖率分析"""
        logger.info(f"🔍 开始运行{analysis_level}级别覆盖率分析...")

        results = {
            "timestamp": datetime.now().isoformat(),
            "analysis_level": analysis_level,
            "project_root": str(self.project_root),
            "targets": self.targets,
            "issue_98_methodology_applied": True,
        }

        try:
            if analysis_level == "quick":
                coverage_result = self._run_quick_coverage()
            elif analysis_level == "comprehensive":
                coverage_result = self._run_comprehensive_coverage()
            else:  # standard
                coverage_result = self._run_standard_coverage()

            results.update(coverage_result)

            # 评估结果
            results["evaluation"] = self._evaluate_coverage_results(coverage_result)

            # 生成建议
            results["recommendations"] = self._generate_recommendations(coverage_result)

            logger.info(
                f"✅ 覆盖率分析完成，总体覆盖率: {coverage_result.get('overall_coverage', {}).get('percent_covered', 0):.2f}%"
            )

        except Exception as e:
            logger.error(f"❌ 覆盖率分析失败: {e}")
            results["error"] = str(e)
            results["status"] = "failed"

        return results

    def _run_quick_coverage(self) -> Dict[str, Any]:
        """运行快速覆盖率检查"""
        logger.info("⚡ 执行快速覆盖率检查...")

        cmd = [
            "python",
            "-m",
            "pytest",
            "tests/unit/utils/",
            "--cov=src/utils",
            "--cov-report=json",
            "--cov-report=term",
            "--maxfail=5",
            "-q",
            "--disable-warnings",
        ]

        subprocess.run(
            cmd, cwd=self.project_root, capture_output=True, text=True, timeout=300
        )

        coverage_file = self.project_root / "coverage.json"
        if coverage_file.exists():
            return self._parse_coverage_report(coverage_file, "quick")
        else:
            return {
                "overall_coverage": {"percent_covered": 0},
                "files_coverage": {},
                "status": "no_data",
            }

    def _run_standard_coverage(self) -> Dict[str, Any]:
        """运行标准覆盖率分析"""
        logger.info("📊 执行标准覆盖率分析...")

        cmd = [
            "python",
            "-m",
            "pytest",
            "tests/unit/",
            "tests/integration/",
            "--cov=src/",
            "--cov-report=xml",
            "--cov-report=html",
            "--cov-report=json",
            "--cov-report=term-missing",
            "--tb=short",
            "--maxfail=20",
            "--timeout=300",
        ]

        # 尝试使用并行执行
        try:
            cmd.extend(["-n", "auto"])
except Exception:
            logger.warning("⚠️ pytest-xdist不可用，使用单线程执行")

        subprocess.run(
            cmd, cwd=self.project_root, capture_output=True, text=True, timeout=600
        )

        coverage_file = self.project_root / "coverage.json"
        if coverage_file.exists():
            return self._parse_coverage_report(coverage_file, "standard")
        else:
            return {
                "overall_coverage": {"percent_covered": 0},
                "files_coverage": {},
                "status": "no_data",
            }

    def _run_comprehensive_coverage(self) -> Dict[str, Any]:
        """运行全面覆盖率分析"""
        logger.info("🔬 执行全面覆盖率分析...")

        cmd = [
            "python",
            "-m",
            "pytest",
            "tests/unit/",
            "tests/integration/",
            "--cov=src/",
            "--cov-report=xml",
            "--cov-report=html",
            "--cov-report=json",
            "--cov-report=term-missing",
            "--tb=short",
            "-x",  # 遇到第一个失败就停止
            "--maxfail=50",
            "--timeout=600",
        ]

        result = subprocess.run(
            cmd, cwd=self.project_root, capture_output=True, text=True, timeout=1200
        )

        coverage_file = self.project_root / "coverage.json"
        if coverage_file.exists():
            report = self._parse_coverage_report(coverage_file, "comprehensive")
            report["execution_output"] = result.stdout[-1000:]  # 保留最后1000字符
            report["execution_errors"] = result.stderr[-1000:] if result.stderr else ""
            return report
        else:
            return {
                "overall_coverage": {"percent_covered": 0},
                "files_coverage": {},
                "status": "no_data",
                "execution_errors": result.stderr,
            }

    def _parse_coverage_report(self, coverage_file: Path, analysis_type: str) -> Dict[str, Any]:
        """解析覆盖率报告"""
        logger.info(f"📊 解析覆盖率报告: {coverage_file}")

        try:
            with open(coverage_file, "r") as f:
                data = json.load(f)

            totals = data.get("totals", {})
            overall_coverage = {
                "percent_covered": totals.get("percent_covered", 0),
                "covered_lines": totals.get("covered_lines", 0),
                "missing_lines": totals.get("missing_lines", 0),
                "total_lines": totals.get("num_statements", 0),
                "excluded_lines": totals.get("excluded_lines", 0),
            }

            # 解析各文件覆盖率
            files_coverage = {}
            for file_path, file_data in data.get("files", {}).items():
                if file_path.startswith("src/"):
                    files_coverage[file_path] = {
                        "percent_covered": file_data["summary"]["percent_covered"],
                        "covered_lines": file_data["summary"]["covered_lines"],
                        "missing_lines": file_data["summary"]["missing_lines"],
                        "total_lines": file_data["summary"]["num_statements"],
                    }

            # 特别关注utils模块
            utils_modules = {}
            for file_path, file_data in files_coverage.items():
                if "src/utils/" in file_path:
                    module_name = file_path.replace("src/utils/", "").replace(".py", "")
                    utils_modules[module_name] = file_data

            result = {
                "overall_coverage": overall_coverage,
                "files_coverage": files_coverage,
                "utils_modules": utils_modules,
                "analysis_type": analysis_type,
                "status": "success",
            }

            # Phase 5模块评估
            phase5_status = {}
            for module, target in self.targets["phase5_modules"].items():
                module_coverage = 0
                for file_path, file_data in files_coverage.items():
                    if module in file_path:
                        module_coverage = max(module_coverage, file_data["percent_covered"])

                phase5_status[module] = {
                    "coverage": module_coverage,
                    "target": target,
                    "target_met": module_coverage >= target,
                    "gap": max(0, target - module_coverage),
                }

            result["phase5_module_status"] = phase5_status

            return result

        except Exception as e:
            logger.error(f"❌ 解析覆盖率报告失败: {e}")
            return {
                "overall_coverage": {"percent_covered": 0},
                "files_coverage": {},
                "error": str(e),
                "status": "parse_error",
            }

    def _evaluate_coverage_results(self, coverage_result: Dict[str, Any]) -> Dict[str, Any]:
        """评估覆盖率结果"""
        overall_cov = coverage_result.get("overall_coverage", {}).get("percent_covered", 0)

        evaluation = {
            "overall_status": "unknown",
            "target_achievement": {},
            "critical_modules": [],
            "improvement_areas": [],
        }

        # 评估总体状态
        if overall_cov >= self.targets["phase6"]:
            evaluation["overall_status"] = "excellent"
        elif overall_cov >= self.targets["current"]:
            evaluation["overall_status"] = "good"
        elif overall_cov >= 10:
            evaluation["overall_status"] = "needs_improvement"
        else:
            evaluation["overall_status"] = "critical"

        # 评估目标达成
        evaluation["target_achievement"] = {
            "current_target": {
                "target": self.targets["current"],
                "achieved": overall_cov >= self.targets["current"],
                "gap": max(0, self.targets["current"] - overall_cov),
            },
            "phase6_target": {
                "target": self.targets["phase6"],
                "achieved": overall_cov >= self.targets["phase6"],
                "gap": max(0, self.targets["phase6"] - overall_cov),
            },
        }

        # 识别关键模块
        phase5_status = coverage_result.get("phase5_module_status", {})
        for module, status in phase5_status.items():
            if not status["target_met"] and status["gap"] > 10:
                evaluation["critical_modules"].append(module)

        # 识别改进区域
        if overall_cov < self.targets["current"]:
            evaluation["improvement_areas"].append("提升整体覆盖率至15%+")

        if evaluation["critical_modules"]:
            evaluation["improvement_areas"].append(
                f"修复关键模块: {', '.join(evaluation['critical_modules'])}"
            )

        if overall_cov >= self.targets["current"] and overall_cov < self.targets["phase6"]:
            evaluation["improvement_areas"].append("继续推进Phase 6覆盖率目标")

        return evaluation

    def _generate_recommendations(self, coverage_result: Dict[str, Any]) -> List[str]:
        """生成改进建议"""
        recommendations = []
        overall_cov = coverage_result.get("overall_coverage", {}).get("percent_covered", 0)

        # 基于覆盖率水平的建议
        if overall_cov < 10:
            recommendations.append("🚨 严重不足：优先执行Issue #94基础覆盖率提升计划")
            recommendations.append("📊 重点关注utils模块的测试用例补充")
        elif overall_cov < self.targets["current"]:
            recommendations.append("📈 持续改进：推进Issue #94覆盖率提升至15%+")
            recommendations.append("🎯 针对低覆盖率模块增加测试用例")
        elif overall_cov < self.targets["phase6"]:
            recommendations.append("🚀 Phase 6推进：继续提升覆盖率至35%+")
            recommendations.append("🔧 扩展更多模块的测试覆盖范围")
        else:
            recommendations.append("🎉 优秀水平：保持高质量测试覆盖率")
            recommendations.append("📊 关注测试质量和有效性")

        # 基于Phase 5模块状态的建议
        phase5_status = coverage_result.get("phase5_module_status", {})
        critical_modules = [m for m, s in phase5_status.items() if not s.get("target_met", False)]

        if critical_modules:
            recommendations.append(f"⚠️ 重点修复：{', '.join(critical_modules)}模块未达标")

        # 基于Issue #98方法论的建议
        recommendations.append("🛡️ 持续应用Issue #98智能质量修复方法论")
        recommendations.append("🔄 集成实时监控系统跟踪改进效果")

        return recommendations

    def save_report(self, results: Dict[str, Any], output_file: Optional[str] = None) -> str:
        """保存覆盖率分析报告"""
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"ci_coverage_report_{timestamp}.json"

        output_path = self.project_root / output_file

        try:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2, ensure_ascii=False)

            logger.info(f"✅ 覆盖率报告已保存: {output_path}")
            return str(output_path)

        except Exception as e:
            logger.error(f"❌ 保存报告失败: {e}")
            raise

    def feed_to_quality_monitor(self, results: Dict[str, Any]) -> bool:
        """向质量监控系统输入数据"""
        logger.info("🔄 向质量监控系统输入覆盖率数据...")

        try:
            import requests

            # 检查质量监控系统是否运行
            monitor_url = "http://127.0.0.1:5000"

            try:
                response = requests.get(f"{monitor_url}/api/status", timeout=5)
                if response.status_code != 200:
                    logger.warning("⚠️ 质量监控系统未响应")
                    return False
except Exception:
                logger.warning("⚠️ 无法连接到质量监控系统")
                return False

            # 刷新监控数据
            refresh_response = requests.post(f"{monitor_url}/api/refresh", timeout=10)
            if refresh_response.status_code == 200:
                logger.info("✅ 成功刷新监控系统数据")
            else:
                logger.warning(f"⚠️ 刷新失败: {refresh_response.status_code}")

            # 触发质量检查
            check_response = requests.post(f"{monitor_url}/api/trigger-check", timeout=30)
            if check_response.status_code == 200:
                result = check_response.json()
                logger.info(f"✅ 质量检查完成: {result.get('message', '无消息')}")
                return True
            else:
                logger.warning(f"⚠️ 质量检查失败: {check_response.status_code}")
                return False

        except ImportError:
            logger.warning("⚠️ requests库不可用，无法连接质量监控系统")
            return False
        except Exception as e:
            logger.error(f"❌ 连接质量监控系统失败: {e}")
            return False

    def generate_summary_markdown(self, results: Dict[str, Any]) -> str:
        """生成Markdown格式的总结报告"""
        overall_cov = results.get("overall_coverage", {}).get("percent_covered", 0)
        evaluation = results.get("evaluation", {})
        recommendations = results.get("recommendations", [])

        markdown = f"""# 📊 CI/CD覆盖率监控报告

## 📊 分析概览

- **分析时间**: {results.get('timestamp', 'N/A')}
- **分析级别**: {results.get('analysis_level', 'N/A')}
- **总体覆盖率**: {overall_cov:.2f}%
- **整体状态**: {evaluation.get('overall_status', 'N/A')}

## 🎯 目标达成情况

| 目标 | 当前状态 | 达标情况 |
|------|----------|----------|
| **当前目标** ({self.targets['current']}%) | {overall_cov:.2f}% | {'✅ 达标' if overall_cov >= self.targets['current'] else '❌ 未达标'} |
| **Phase 6目标** ({self.targets['phase6']}%) | {overall_cov:.2f}% | {'✅ 达标' if overall_cov >= self.targets['phase6'] else '📈 进行中'} |

## 📈 Phase 5模块状态

"""

        # Phase 5模块状态
        phase5_status = results.get("phase5_module_status", {})
        for module, status in phase5_status.items():
            status_icon = "✅" if status.get("target_met", False) else "⚠️"
            markdown += f"- **{module}**: {status_icon} {status['coverage']:.2f}% (目标: {status['target']}%)\n"

        # 改进建议
        markdown += "\n## 🚀 改进建议\n\n"
        for i, rec in enumerate(recommendations, 1):
            markdown += f"{i}. {rec}\n"

        # Issue #98方法论说明
        markdown += f"""
## 🛡️ Issue #98方法论应用

本次覆盖率监控严格遵循Issue #98智能质量修复方法论：

- ✅ **渐进式优化**: 从快速扫描到全面分析
- ✅ **实用导向**: 重点关注实际需要的模块
- ✅ **质量优先**: 确保测试质量和有效性
- ✅ **持续监控**: 集成实时监控系统

## 📋 后续行动计划

1. **立即执行**: 根据建议进行针对性改进
2. **持续监控**: 使用质量监控系统跟踪进展
3. **定期评估**: 按Phase规划推进目标
4. **方法论应用**: 继续应用Issue #98最佳实践

---
*报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
*基于Issue #98智能质量修复方法论*
*Phase 6: CI/CD覆盖率监控集成*
"""

        return markdown


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="CI/CD覆盖率监控集成")
    parser.add_argument(
        "--analysis-level",
        choices=["quick", "standard", "comprehensive"],
        default="standard",
        help="分析级别",
    )
    parser.add_argument("--output-file", help="输出文件名")
    parser.add_argument("--save-markdown", action="store_true", help="保存Markdown报告")
    parser.add_argument("--feed-monitor", action="store_true", help="向质量监控系统输入数据")
    parser.add_argument("--project-root", help="项目根目录")

    args = parser.parse_args()

    project_root = Path(args.project_root) if args.project_root else None
    monitor = CICoverageMonitor(project_root)

    try:
        # 运行覆盖率分析
        logger.info(f"🚀 开始CI/CD覆盖率监控分析 (级别: {args.analysis_level})")
        results = monitor.run_coverage_analysis(args.analysis_level)

        # 保存JSON报告
        report_file = monitor.save_report(results, args.output_file)
        print(f"📄 报告已保存: {report_file}")

        # 保存Markdown报告
        if args.save_markdown:
            markdown_content = monitor.generate_summary_markdown(results)
            markdown_file = report_file.replace(".json", ".md")
            with open(markdown_file, "w", encoding="utf-8") as f:
                f.write(markdown_content)
            print(f"📝 Markdown报告已保存: {markdown_file}")

        # 向质量监控系统输入数据
        if args.feed_monitor:
            success = monitor.feed_to_quality_monitor(results)
            if success:
                print("✅ 数据已成功输入质量监控系统")
            else:
                print("⚠️ 质量监控系统连接失败")

        # 输出简要结果
        overall_cov = results.get("overall_coverage", {}).get("percent_covered", 0)
        evaluation = results.get("evaluation", {}).get("overall_status", "unknown")
        print(f"📊 总体覆盖率: {overall_cov:.2f}%")
        print(f"🎯 评估状态: {evaluation}")

        return 0

    except Exception as e:
        logger.error(f"❌ CI/CD覆盖率监控失败: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
