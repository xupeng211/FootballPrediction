#!/usr/bin/env python3
"""
质量守护工具
Quality Guardian

集成的代码质量守护系统，提供全面的质量检查、修复和监控功能
"""

import os
import sys
import json
import subprocess
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import logging

# 导入其他修复工具
try:
    from quality_standards_optimizer import QualityStandardsOptimizer
    from smart_quality_fixer import SmartQualityFixer
except ImportError as e:
    print(f"导入工具模块失败: {e}")
    sys.exit(1)

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class QualityGuardian:
    """质量守护者"""

    def __init__(self, project_root: Path = None):
        self.project_root = project_root or Path(__file__).parent.parent
        self.monitoring_dir = self.project_root / "monitoring-data"
        self.reports_dir = self.project_root / "quality-reports"

        # 确保目录存在
        self.monitoring_dir.mkdir(exist_ok=True)
        self.reports_dir.mkdir(exist_ok=True)

        # 初始化组件
        self.optimizer = QualityStandardsOptimizer(self.project_root)
        self.fixer = SmartQualityFixer(self.project_root)

        # 质量状态
        self.quality_status = {
            "timestamp": datetime.now().isoformat(),
            "overall_score": 0,
            "coverage": 0,
            "code_quality": 0,
            "test_health": 0,
            "security": 0,
            "recommendations": [],
            "action_items": []
        }

    def run_full_quality_check(self) -> Dict[str, Any]:
        """运行完整的质量检查"""
        print("🛡️ 质量守护系统")
        print("=" * 60)
        print("📊 执行全面质量检查...")
        print()

        # 1. 基础质量指标收集
        print("1️⃣ 收集质量指标...")
        metrics = self._collect_quality_metrics()

        # 2. 代码质量分析
        print("2️⃣ 分析代码质量...")
        code_quality = self._analyze_code_quality()

        # 3. 测试健康度检查
        print("3️⃣ 检查测试健康度...")
        test_health = self._check_test_health()

        # 4. 安全性检查
        print("4️⃣ 执行安全性检查...")
        security = self._check_security()

        # 5. 综合评估
        print("5️⃣ 综合质量评估...")
        self._assess_overall_quality(metrics, code_quality, test_health, security)

        # 6. 生成报告
        print("6️⃣ 生成质量报告...")
        report = self._generate_quality_report()

        # 7. 提供行动建议
        print("7️⃣ 生成行动建议...")
        self._generate_action_items()

        print()
        print("✅ 质量检查完成！")
        self._print_quality_summary()

        return self.quality_status

    def _collect_quality_metrics(self) -> Dict[str, Any]:
        """收集基础质量指标"""
        metrics = {
            "timestamp": datetime.now().isoformat(),
            "coverage": 0,
            "ruff_errors": 0,
            "mypy_errors": 0,
            "test_count": 0,
            "test_pass_rate": 0,
            "files_count": 0
        }

        # 覆盖率
        try:
            result = subprocess.run([
                sys.executable, "-m", "pytest", "tests/unit/api/test_health.py",
                "--cov=src/", "--cov-report=json", "--tb=short", "-q"
            ], capture_output=True, text=True, timeout=60)

            coverage_file = self.project_root / "coverage.json"
            if coverage_file.exists():
                with open(coverage_file) as f:
                    coverage_data = json.load(f)
                metrics["coverage"] = coverage_data.get("totals", {}).get("percent_covered", 0)
        except Exception as e:
            logger.warning(f"覆盖率检查失败: {e}")

        # Ruff错误
        try:
            result = subprocess.run([
                "ruff", "check", "src/", "--output-format=json"
            ], capture_output=True, text=True, timeout=30)
            if result.stdout.strip():
                ruff_data = json.loads(result.stdout)
                metrics["ruff_errors"] = len(ruff_data)
        except Exception as e:
            logger.warning(f"Ruff检查失败: {e}")

        # MyPy错误
        try:
            result = subprocess.run([
                sys.executable, "-m", "mypy", "src/", "--show-error-codes"
            ], capture_output=True, text=True, timeout=60)
            mypy_output = result.stderr
            metrics["mypy_errors"] = mypy_output.count("error:")
        except Exception as e:
            logger.warning(f"MyPy检查失败: {e}")

        # 文件数量
        metrics["files_count"] = len(list(self.project_root.glob("src/**/*.py")))

        self.quality_status.update(metrics)
        return metrics

    def _analyze_code_quality(self) -> Dict[str, Any]:
        """分析代码质量"""
        quality = {
            "score": 0,
            "complexity": "unknown",
            "maintainability": "unknown",
            "duplication": "unknown",
            "issues": []
        }

        # 基于Ruff和MyPy结果计算质量分数
        ruff_errors = self.quality_status.get("ruff_errors", 0)
        mypy_errors = self.quality_status.get("mypy_errors", 0)

        # 质量分数计算 (0-10)
        ruff_score = max(0, 10 - ruff_errors * 0.5)
        mypy_score = max(0, 10 - mypy_errors * 0.01)
        quality["score"] = (ruff_score + mypy_score) / 2

        # 识别质量问题
        if ruff_errors > 20:
            quality["issues"].append("Ruff代码问题过多，需要代码清理")
        if mypy_errors > 100:
            quality["issues"].append("MyPy类型错误过多，需要类型注解改进")

        self.quality_status["code_quality"] = quality["score"]
        return quality

    def _check_test_health(self) -> Dict[str, Any]:
        """检查测试健康度"""
        health = {
            "score": 0,
            "coverage_adequacy": "insufficient",
            "test_distribution": "unknown",
            "flaky_tests": 0,
            "recommendations": []
        }

        coverage = self.quality_status.get("coverage", 0)

        # 覆盖率评估
        if coverage >= 80:
            health["coverage_adequacy"] = "excellent"
            health["score"] = 10
        elif coverage >= 60:
            health["coverage_adequacy"] = "good"
            health["score"] = 8
        elif coverage >= 40:
            health["coverage_adequacy"] = "moderate"
            health["score"] = 6
        elif coverage >= 20:
            health["coverage_adequacy"] = "insufficient"
            health["score"] = 4
        else:
            health["coverage_adequacy"] = "poor"
            health["score"] = 2

        # 生成建议
        if coverage < 40:
            health["recommendations"].append("测试覆盖率过低，需要增加测试用例")
        if coverage < 60:
            health["recommendations"].append("重点关注核心业务逻辑的测试覆盖")

        self.quality_status["test_health"] = health["score"]
        return health

    def _check_security(self) -> Dict[str, Any]:
        """检查安全性"""
        security = {
            "score": 0,
            "vulnerabilities": 0,
            "secrets_found": 0,
            "dependencies_risk": "unknown",
            "recommendations": []
        }

        # 基础安全检查（简化版）
        try:
            # 检查明显的安全问题
            result = subprocess.run([
                "bandit", "-r", "src/", "-f", "json"
            ], capture_output=True, text=True, timeout=30)

            if result.stdout.strip():
                try:
                    bandit_data = json.loads(result.stdout)
                    security["vulnerabilities"] = len(bandit_data.get("results", []))
                except:
                    pass
        except Exception as e:
            logger.warning(f"安全检查失败: {e}")

        # 安全分数计算
        if security["vulnerabilities"] == 0:
            security["score"] = 10
        elif security["vulnerabilities"] <= 5:
            security["score"] = 8
        elif security["vulnerabilities"] <= 10:
            security["score"] = 6
        else:
            security["score"] = 4

        if security["vulnerabilities"] > 0:
            security["recommendations"].append("发现安全漏洞，需要及时修复")

        self.quality_status["security"] = security["score"]
        return security

    def _assess_overall_quality(self, metrics, code_quality, test_health, security):
        """评估综合质量"""
        # 计算综合分数
        weights = {
            "code_quality": 0.3,
            "test_health": 0.4,
            "security": 0.2,
            "coverage": 0.1
        }

        overall_score = (
            code_quality["score"] * weights["code_quality"] +
            test_health["score"] * weights["test_health"] +
            security["score"] * weights["security"] +
            (metrics.get("coverage", 0) / 10) * weights["coverage"]
        )

        self.quality_status["overall_score"] = round(overall_score, 2)

    def _generate_quality_report(self) -> Dict[str, Any]:
        """生成质量报告"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "quality_status": self.quality_status,
            "trends": self._analyze_quality_trends(),
            "benchmarks": self._compare_with_benchmarks()
        }

        # 保存报告
        report_file = self.reports_dir / f"quality_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        logger.info(f"质量报告已保存: {report_file}")
        return report

    def _analyze_quality_trends(self) -> Dict[str, Any]:
        """分析质量趋势"""
        trends = {
            "coverage_trend": "stable",
            "quality_trend": "stable",
            "recommendation": "持续监控"
        }

        # 查找历史数据
        history_files = sorted(self.monitoring_dir.glob("quality_optimization_report.json"))
        if len(history_files) >= 2:
            try:
                with open(history_files[-1]) as f:
                    latest_data = json.load(f)
                with open(history_files[-2]) as f:
                    previous_data = json.load(f)

                latest_coverage = latest_data.get("current_status", {}).get("coverage", 0)
                previous_coverage = previous_data.get("current_status", {}).get("coverage", 0)

                if latest_coverage > previous_coverage + 2:
                    trends["coverage_trend"] = "improving"
                elif latest_coverage < previous_coverage - 2:
                    trends["coverage_trend"] = "declining"

            except Exception as e:
                logger.warning(f"趋势分析失败: {e}")

        return trends

    def _compare_with_benchmarks(self) -> Dict[str, Any]:
        """与基准比较"""
        benchmarks = {
            "industry_average": {
                "coverage": 75,
                "code_quality": 7,
                "security": 8
            },
            "project_targets": {
                "coverage": 40,
                "code_quality": 8,
                "security": 9
            }
        }

        current = {
            "coverage": self.quality_status.get("coverage", 0),
            "code_quality": self.quality_status.get("code_quality", 0),
            "security": self.quality_status.get("security", 0)
        }

        comparison = {
            "vs_industry": {},
            "vs_targets": {}
        }

        for metric in ["coverage", "code_quality", "security"]:
            comparison["vs_industry"][metric] = current[metric] - benchmarks["industry_average"][metric]
            comparison["vs_targets"][metric] = current[metric] - benchmarks["project_targets"][metric]

        return comparison

    def _generate_action_items(self):
        """生成行动项"""
        action_items = []

        # 基于质量分数生成行动项
        overall_score = self.quality_status["overall_score"]
        coverage = self.quality_status.get("coverage", 0)
        code_quality = self.quality_status.get("code_quality", 0)
        mypy_errors = self.quality_status.get("mypy_errors", 0)

        if overall_score < 5:
            action_items.append({
                "priority": "HIGH",
                "category": "overall",
                "action": "整体质量需要重大改进",
                "details": "建议制定详细的质量改进计划"
            })

        if coverage < 20:
            action_items.append({
                "priority": "HIGH",
                "category": "coverage",
                "action": "提升测试覆盖率",
                "details": f"当前覆盖率{coverage:.1f}%，建议优先为核心模块添加测试"
            })

        if mypy_errors > 500:
            action_items.append({
                "priority": "HIGH",
                "category": "type_safety",
                "action": "修复MyPy类型错误",
                "details": f"当前有{mypy_errors}个类型错误，建议分批修复"
            })

        if code_quality < 6:
            action_items.append({
                "priority": "MEDIUM",
                "category": "code_quality",
                "action": "改进代码质量",
                "details": "运行代码格式化和清理工具"
            })

        # 添加预防性建议
        action_items.extend([
            {
                "priority": "LOW",
                "category": "prevention",
                "action": "建立质量门禁",
                "details": "在CI/CD中集成质量检查"
            },
            {
                "priority": "LOW",
                "category": "monitoring",
                "action": "定期质量监控",
                "details": "建立定期质量检查和报告机制"
            }
        ])

        # 按优先级排序
        priority_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
        action_items.sort(key=lambda x: priority_order.get(x["priority"], 3))

        self.quality_status["action_items"] = action_items
        self.quality_status["recommendations"] = [item["action"] for item in action_items[:5]]

    def _print_quality_summary(self):
        """打印质量摘要"""
        print("\n" + "=" * 60)
        print("📊 质量检查摘要")
        print("=" * 60)

        print(f"📈 综合质量分数: {self.quality_status['overall_score']}/10")
        print(f"🧪 测试覆盖率: {self.quality_status.get('coverage', 0):.1f}%")
        print(f"🔍 代码质量分数: {self.quality_status.get('code_quality', 0):.1f}/10")
        print(f"🛡️ 安全分数: {self.quality_status.get('security', 0):.1f}/10")

        print("\n🎯 关键指标:")
        print(f"  - Ruff错误: {self.quality_status.get('ruff_errors', 0)}")
        print(f"  - MyPy错误: {self.quality_status.get('mypy_errors', 0)}")
        print(f"  - 文件数量: {self.quality_status.get('files_count', 0)}")

        if self.quality_status.get("recommendations"):
            print("\n💡 主要建议:")
            for rec in self.quality_status["recommendations"][:3]:
                print(f"  • {rec}")

        if self.quality_status.get("action_items"):
            print("\n📋 高优先级行动项:")
            high_priority_items = [item for item in self.quality_status["action_items"] if item["priority"] == "HIGH"]
            for item in high_priority_items[:3]:
                print(f"  🚨 {item['action']}: {item['details']}")

        print("\n" + "=" * 60)

    def run_auto_fix(self, fix_types: List[str] = None) -> Dict[str, Any]:
        """运行自动修复"""
        if fix_types is None:
            fix_types = ["syntax", "imports", "mypy", "ruff", "tests"]

        print("🔧 启动自动修复...")
        fix_results = {}

        if "syntax" in fix_types:
            print("修复语法错误...")
            fix_results["syntax"] = self.fixer.fix_syntax_errors()

        if "imports" in fix_types:
            print("修复导入错误...")
            fix_results["imports"] = self.fixer.fix_import_errors()

        if "mypy" in fix_types:
            print("修复MyPy错误...")
            fix_results["mypy"] = self.fixer.fix_mypy_errors()

        if "ruff" in fix_types:
            print("修复Ruff问题...")
            fix_results["ruff"] = self.fixer.fix_ruff_issues()

        if "tests" in fix_types:
            print("修复测试问题...")
            fix_results["tests"] = self.fixer.fix_test_issues()

        total_fixes = sum(fix_results.values())
        print(f"\n✅ 自动修复完成！总修复数: {total_fixes}")

        return fix_results

    def optimize_quality_standards(self) -> bool:
        """优化质量标准"""
        print("🎯 优化质量标准...")
        return self.optimizer.run_optimization()

    def run_guardian_cycle(self) -> Dict[str, Any]:
        """运行完整的守护周期"""
        print("🛡️ 启动质量守护周期")
        print("=" * 60)

        # 1. 质量检查
        quality_status = self.run_full_quality_check()

        # 2. 自动修复（可选）
        if quality_status["overall_score"] < 6:
            print("\n🔧 质量分数较低，启动自动修复...")
            fix_results = self.run_auto_fix()
            quality_status["auto_fixes"] = fix_results

        # 3. 标准优化（如需要）
        if quality_status.get("mypy_errors", 0) > 1000 or quality_status.get("coverage", 0) < 15:
            print("\n🎯 质量标准需要调整...")
            optimization_success = self.optimize_quality_standards()
            quality_status["standards_optimized"] = optimization_success

        return quality_status


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="质量守护工具")
    parser.add_argument("--project-root", type=Path, help="项目根目录")
    parser.add_argument("--check-only", action="store_true", help="仅执行质量检查")
    parser.add_argument("--fix-only", action="store_true", help="仅执行自动修复")
    parser.add_argument("--optimize-only", action="store_true", help="仅优化质量标准")
    parser.add_argument("--fix-types", nargs="+", choices=["syntax", "imports", "mypy", "ruff", "tests"], help="指定修复类型")

    args = parser.parse_args()

    guardian = QualityGuardian(args.project_root)

    if args.check_only:
        guardian.run_full_quality_check()
    elif args.fix_only:
        guardian.run_auto_fix(args.fix_types)
    elif args.optimize_only:
        guardian.optimize_quality_standards()
    else:
        # 运行完整守护周期
        guardian.run_guardian_cycle()


if __name__ == "__main__":
    main()