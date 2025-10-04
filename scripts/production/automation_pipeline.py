#!/usr/bin/env python3
"""
生产环境自动化流水线脚本
整合所有生产就绪解决方案
"""

import sys
import subprocess
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List
import argparse


class ProductionAutomationPipeline:
    """生产环境自动化流水线"""

    def __init__(self, environment: str = "production"):
        self.environment = environment
        self.project_root = Path.cwd()
        self.reports_dir = self.project_root / "docs/_reports"
        self.scripts_dir = self.project_root / "scripts"

        # 检查报告
        self.check_results = {
            "dependencies": {"status": "unknown", "score": 0},
            "security": {"status": "unknown", "score": 0},
            "tests": {"status": "unknown", "score": 0},
            "configuration": {"status": "unknown", "score": 0},
            "ci_cd": {"status": "unknown", "score": 0}
        }

        # 阈值
        self.thresholds = {
            "pass": 80,
            "warning": 60,
            "fail": 40
        }

    def run_full_pipeline(self) -> bool:
        """运行完整的自动化流水线"""
        print(f"🚀 开始生产环境自动化流水线 - {self.environment.upper()}")
        print("=" * 80)

        success = True

        # 1. 依赖检查和修复
        print("\n1️⃣ 依赖冲突检查和修复...")
        success &= self._run_dependency_check()

        # 2. 安全配置
        print("\n2️⃣ 安全配置设置...")
        success &= self._run_security_setup()

        # 3. 测试框架构建
        print("\n3️⃣ 测试框架构建...")
        success &= self._run_test_framework_setup()

        # 4. 配置验证
        print("\n4️⃣ 环境配置验证...")
        success &= self._run_configuration_validation()

        # 5. CI/CD检查
        print("\n5️⃣ CI/CD配置检查...")
        success &= self._run_cicd_check()

        # 6. 生成最终报告
        print("\n6️⃣ 生成最终评估报告...")
        self._generate_final_report()

        # 总结
        print("\n" + "=" * 80)
        if success:
            total_score = sum(r["score"] for r in self.check_results.values()) / len(self.check_results)
            print(f"✅ 流水线完成! 总分: {total_score:.1f}/100")
            if total_score >= self.thresholds["pass"]:
                print("🎉 项目已达到生产就绪标准!")
            else:
                print("⚠️  项目尚未达到生产就绪标准，请查看报告了解详情")
        else:
            print("❌ 流水线失败，请检查错误信息")

        return success and total_score >= self.thresholds["pass"]

    def _run_dependency_check(self) -> bool:
        """运行依赖检查"""
        try:
            # 运行依赖冲突解决脚本
            result = subprocess.run(
                [sys.executable, str(self.scripts_dir / "dependency/resolve_conflicts.py")],
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                self.check_results["dependencies"]["status"] = "passed"
                self.check_results["dependencies"]["score"] = 95
                print("✅ 依赖检查通过")
                return True
            else:
                self.check_results["dependencies"]["status"] = "failed"
                self.check_results["dependencies"]["score"] = 30
                print(f"❌ 依赖检查失败: {result.stderr}")
                return False

        except Exception as e:
            self.check_results["dependencies"]["status"] = "error"
            self.check_results["dependencies"]["score"] = 0
            print(f"❌ 依赖检查错误: {e}")
            return False

    def _run_security_setup(self) -> bool:
        """运行安全配置"""
        try:
            # 运行安全配置脚本
            env_file = f".env.{self.environment}"
            result = subprocess.run([
                sys.executable,
                str(self.scripts_dir / "security/setup_security.py"),
                "--env", self.environment,
                "--output", env_file
            ], capture_output=True, text=True)

            if result.returncode == 0:
                self.check_results["security"]["status"] = "passed"
                self.check_results["security"]["score"] = 90
                print("✅ 安全配置完成")
                return True
            else:
                self.check_results["security"]["status"] = "failed"
                self.check_results["security"]["score"] = 20
                print(f"❌ 安全配置失败: {result.stderr}")
                return False

        except Exception as e:
            self.check_results["security"]["status"] = "error"
            self.check_results["security"]["score"] = 0
            print(f"❌ 安全配置错误: {e}")
            return False

    def _run_test_framework_setup(self) -> bool:
        """运行测试框架构建"""
        try:
            # 构建测试框架
            result = subprocess.run([
                sys.executable,
                str(self.scripts_dir / "testing/build_test_framework.py")
            ], capture_output=True, text=True)

            if result.returncode == 0:
                # 运行基础测试验证
                test_result = subprocess.run([
                    sys.executable, "-m", "pytest",
                    "tests/unit/api/test_health.py::TestHealthAPI::test_health_check_success",
                    "-v", "--tb=short"
                ], capture_output=True, text=True)

                if test_result.returncode == 0:
                    self.check_results["tests"]["status"] = "passed"
                    self.check_results["tests"]["score"] = 85
                    print("✅ 测试框架构建成功")
                    return True
                else:
                    self.check_results["tests"]["status"] = "warning"
                    self.check_results["tests"]["score"] = 60
                    print("⚠️  测试框架构建完成，但测试需要进一步修复")
                    return True
            else:
                self.check_results["tests"]["status"] = "failed"
                self.check_results["tests"]["score"] = 5
                print(f"❌ 测试框架构建失败: {result.stderr}")
                return False

        except Exception as e:
            self.check_results["tests"]["status"] = "error"
            self.check_results["tests"]["score"] = 0
            print(f"❌ 测试框架构建错误: {e}")
            return False

    def _run_configuration_validation(self) -> bool:
        """运行配置验证"""
        try:
            # 检查环境文件
            env_file = self.project_root / f".env.{self.environment}"
            if not env_file.exists():
                self.check_results["configuration"]["status"] = "failed"
                self.check_results["configuration"]["score"] = 0
                print("❌ 环境配置文件不存在")
                return False

            # 检查文件权限
            if env_file.stat().st_mode & 0o777 != 0o600:
                print("⚠️  环境文件权限不正确，正在修复...")
                env_file.chmod(0o600)

            # 验证配置项
            score = 90
            issues = []

            with open(env_file, "r", encoding="utf-8") as f:
                content = f.read()

            # 检查关键配置
            if "CHANGE_ME" in content:
                issues.append("发现占位符配置")
                score -= 30

            # 检查SECRET_KEY
            if "SECRET_KEY" not in content:
                issues.append("缺少SECRET_KEY")
                score -= 20

            # 检查数据库配置
            if "DATABASE_URL" not in content:
                issues.append("缺少数据库配置")
                score -= 20

            if issues:
                print(f"⚠️  配置问题: {', '.join(issues)}")

            self.check_results["configuration"]["status"] = "passed" if score >= 80 else "warning"
            self.check_results["configuration"]["score"] = score
            print(f"✅ 配置验证完成 (得分: {score})")
            return True

        except Exception as e:
            self.check_results["configuration"]["status"] = "error"
            self.check_results["configuration"]["score"] = 0
            print(f"❌ 配置验证错误: {e}")
            return False

    def _run_cicd_check(self) -> bool:
        """运行CI/CD检查"""
        try:
            score = 85
            issues = []

            # 检查GitHub Actions配置
            workflows_dir = self.project_root / ".github/workflows"
            if not workflows_dir.exists():
                issues.append("缺少GitHub Actions配置")
                score -= 40

            # 检查关键工作流
            required_workflows = ["ci-pipeline.yml", "security-scan.yml"]
            for workflow in required_workflows:
                if not (workflows_dir / workflow).exists():
                    issues.append(f"缺少工作流: {workflow}")
                    score -= 20

            # 检查Makefile
            makefile = self.project_root / "Makefile"
            if not makefile.exists():
                issues.append("缺少Makefile")
                score -= 10

            # 检查Docker配置
            dockerfile = self.project_root / "Dockerfile"
            if not dockerfile.exists():
                issues.append("缺少Dockerfile")
                score -= 15

            if issues:
                print(f"⚠️  CI/CD问题: {', '.join(issues)}")

            self.check_results["ci_cd"]["status"] = "passed" if score >= 80 else "warning"
            self.check_results["ci_cd"]["score"] = score
            print(f"✅ CI/CD检查完成 (得分: {score})")
            return True

        except Exception as e:
            self.check_results["ci_cd"]["status"] = "error"
            self.check_results["ci_cd"]["score"] = 0
            print(f"❌ CI/CD检查错误: {e}")
            return False

    def _generate_final_report(self):
        """生成最终报告"""
        print("\n📊 生成最终评估报告...")

        # 计算总分
        total_score = sum(r["score"] for r in self.check_results.values()) / len(self.check_results)

        # 生成报告
        report = {
            "timestamp": datetime.now().isoformat(),
            "environment": self.environment,
            "overall_score": total_score,
            "overall_status": self._get_status(total_score),
            "thresholds": self.thresholds,
            "details": self.check_results,
            "recommendations": self._generate_recommendations(),
            "next_steps": self._generate_next_steps()
        }

        # 保存报告
        report_file = self.reports_dir / "PRODUCTION_READINESS_FINAL_REPORT.json"
        self.reports_dir.mkdir(parents=True, exist_ok=True)

        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        # 生成markdown报告
        self._generate_markdown_report(report)

        print(f"✅ 报告已生成: {report_file}")

    def _get_status(self, score: float) -> str:
        """根据分数获取状态"""
        if score >= self.thresholds["pass"]:
            return "production_ready"
        elif score >= self.thresholds["warning"]:
            return "needs_attention"
        else:
            return "not_ready"

    def _generate_recommendations(self) -> List[Dict]:
        """生成建议"""
        recommendations = []

        # 依赖建议
        if self.check_results["dependencies"]["score"] < self.thresholds["pass"]:
            recommendations.append({
                "category": "dependencies",
                "priority": "high",
                "action": "解决依赖冲突",
                "details": "运行 python scripts/dependency/resolve_conflicts.py"
            })

        # 安全建议
        if self.check_results["security"]["score"] < self.thresholds["pass"]:
            recommendations.append({
                "category": "security",
                "priority": "high",
                "action": "配置安全密钥",
                "details": "运行 python scripts/security/setup_security.py"
            })

        # 测试建议
        if self.check_results["tests"]["score"] < self.thresholds["warning"]:
            recommendations.append({
                "category": "tests",
                "priority": "high",
                "action": "构建测试框架",
                "details": "运行 python scripts/testing/build_test_framework.py"
            })

        # 配置建议
        if self.check_results["configuration"]["score"] < self.thresholds["pass"]:
            recommendations.append({
                "category": "configuration",
                "priority": "medium",
                "action": "完善环境配置",
                "details": "检查和修复 .env.production 文件"
            })

        # CI/CD建议
        if self.check_results["ci_cd"]["score"] < self.thresholds["pass"]:
            recommendations.append({
                "category": "ci_cd",
                "priority": "medium",
                "action": "完善CI/CD配置",
                "details": "添加GitHub Actions工作流和Makefile命令"
            })

        return recommendations

    def _generate_next_steps(self) -> List[str]:
        """生成下一步行动"""
        next_steps = []

        if self.check_results["dependencies"]["status"] != "passed":
            next_steps.append("1. 解决所有依赖冲突")
            next_steps.append("   - pip install pip-tools")
            next_steps.append("   - pip-compile requirements.txt")

        if self.check_results["security"]["status"] != "passed":
            next_steps.append("2. 设置安全配置")
            next_steps.append("   - 生成安全密钥")
            next_steps.append("   - 配置环境变量")

        if self.check_results["tests"]["status"] != "passed":
            next_steps.append("3. 构建测试框架")
            next_steps.append("   - 创建测试目录结构")
            next_steps.append("   - 编写基础测试用例")
            next_steps.append("   - 配置测试工具")

        next_steps.append("4. 部署准备")
        next_steps.append("   - 设置Docker容器")
        next_steps.append("   - 配置监控和日志")
        next_steps.append("   - 准备生产数据库")

        return next_steps

    def _generate_markdown_report(self, report: Dict):
        """生成Markdown报告"""
        markdown_content = f"""# 生产环境就绪评估报告

**评估时间**: {report["timestamp"]}
**环境**: {report["environment"].upper()}
**总分**: {report["overall_score"]:.1f}/100
**状态**: {self._format_status(report["overall_status"])}

## 📊 各项评分

| 检查项 | 状态 | 得分 | 要求 |
|--------|------|------|------|"""

        for check_name, result in report["details"].items():
            status_icon = "✅" if result["status"] == "passed" else "⚠️" if result["status"] == "warning" else "❌"
            check_name_display = check_name.replace("_", " ").title()
            markdown_content += f"\n| {check_name_display} | {status_icon} | {result['score']} | >={self.thresholds['pass']} |"

        markdown_content += "\n\n## 🎯 关键发现"

        if report["recommendations"]:
            markdown_content += "\n### ⚠️ 需要解决的问题\n"
            for rec in report["recommendations"]:
                priority_icon = "🔴" if rec["priority"] == "high" else "🟡" if rec["priority"] == "medium" else "🟢"
                markdown_content += f"\n{priority_icon} **{rec['action']}** ({rec['category']})\n"
                markdown_content += f"   - {rec['details']}\n"

        markdown_content += "\n## 📋 下一步行动\n"
        for step in report["next_steps"]:
            markdown_content += f"\n{step}\n"

        markdown_content += f"""

## 🎉 成功标准

项目达到生产就绪需要：
- 依赖冲突: ✅ 已解决
- 安全配置: ✅ 已配置
- 测试覆盖率: >80%
- 配置完整性: ✅ 完成
- CI/CD流程: ✅ 完整
- **总分: ≥{self.thresholds['pass']}**

---

*此报告由自动化脚本生成*
"""

        # 保存Markdown报告
        md_file = self.reports_dir / "PRODUCTION_READINESS_FINAL_REPORT.md"
        with open(md_file, "w", encoding="utf-8") as f:
            f.write(markdown_content)

        print(f"✅ Markdown报告已生成: {md_file}")

    def _format_status(self, status: str) -> str:
        """格式化状态显示"""
        status_map = {
            "production_ready": "🎉 生产就绪",
            "needs_attention": "⚠️ 需要关注",
            "not_ready": "❌ 未就绪"
        }
        return status_map.get(status, status)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="生产环境自动化流水线")
    parser.add_argument(
        "--env",
        choices=["development", "testing", "staging", "production"],
        default="production",
        help="目标环境"
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="仅检查，不执行修复"
    )

    args = parser.parse_args()

    pipeline = ProductionAutomationPipeline(args.env)

    if args.check_only:
        print("🔍 仅检查模式...")
        # TODO: 实现仅检查逻辑
    else:
        success = pipeline.run_full_pipeline()
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()