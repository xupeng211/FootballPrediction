#!/usr/bin/env python3
"""
安全评分计算器
根据各种安全扫描结果计算总体安全评分
"""

import json
import argparse
import sys
from typing import Dict, Any, List, Tuple
from pathlib import Path


class SecurityScoreCalculator:
    """安全评分计算器"""

    def __init__(self):
        self.weights = {
            "dependency": 0.25,
            "code": 0.25,
            "secrets": 0.30,
            "container": 0.20,
        }
        self.thresholds = {"critical": 90, "good": 70, "moderate": 50, "poor": 30}

    def calculate_score(self, reports: Dict[str, str]) -> Dict[str, Any]:
        """计算安全评分"""
        scores = {}

        # 计算各项评分
        scores["dependency_score"] = self._calculate_dependency_score(
            reports.get("safety_report")
        )
        scores["code_score"] = self._calculate_code_score(
            reports.get("bandit_report"), reports.get("semgrep_report")
        )
        scores["secrets_score"] = self._calculate_secrets_score(
            reports.get("trufflehog_report"), reports.get("gitsecrets_report")
        )
        scores["container_score"] = self._calculate_container_score(
            reports.get("trivy_report")
        )

        # 计算加权总分
        overall_score = (
            scores["dependency_score"] * self.weights["dependency"]
            + scores["code_score"] * self.weights["code"]
            + scores["secrets_score"] * self.weights["secrets"]
            + scores["container_score"] * self.weights["container"]
        )

        scores["overall_score"] = round(overall_score, 1)
        scores["grade"] = self._get_grade(overall_score)
        scores["recommendations"] = self._generate_recommendations(scores)
        scores["top_issues"] = self._extract_top_issues(reports)

        return scores

    def _calculate_dependency_score(self, safety_file: str) -> int:
        """计算依赖安全评分"""
        if not safety_file or not Path(safety_file).exists():
            return 0

        try:
            with open(safety_file, "r") as f:
                data = json.load(f)

            vulnerabilities = data.get("vulnerabilities", [])
            total_score = 100

            for vuln in vulnerabilities:
                severity = vuln.get("severity", "unknown").lower()
                if severity == "critical":
                    total_score -= 20
                elif severity == "high":
                    total_score -= 10
                elif severity == "medium":
                    total_score -= 5
                elif severity == "low":
                    total_score -= 2

            return max(0, total_score)

        except Exception as e:
            print(f"Error calculating dependency score: {e}")
            return 0

    def _calculate_code_score(self, bandit_file: str, semgrep_file: str) -> int:
        """计算代码安全评分"""
        score = 100

        # Bandit评分
        if bandit_file and Path(bandit_file).exists():
            try:
                with open(bandit_file, "r") as f:
                    bandit_data = json.load(f)

                results = bandit_data.get("results", [])
                for result in results:
                    issue_severity = result.get("issue_severity", "UNKNOWN")
                    if issue_severity == "HIGH":
                        score -= 10
                    elif issue_severity == "MEDIUM":
                        score -= 5
                    elif issue_severity == "LOW":
                        score -= 2
            except Exception as e:
                print(f"Error parsing bandit report: {e}")

        # Semgrep评分
        if semgrep_file and Path(semgrep_file).exists():
            try:
                with open(semgrep_file, "r") as f:
                    semgrep_data = json.load(f)

                results = semgrep_data.get("results", [])
                for result in results:
                    metadata = result.get("metadata", {})
                    severity = metadata.get("severity", "INFO")
                    if severity == "ERROR":
                        score -= 10
                    elif severity == "WARNING":
                        score -= 5
                    elif severity == "INFO":
                        score -= 2
            except Exception as e:
                print(f"Error parsing semgrep report: {e}")

        return max(0, score)

    def _calculate_secrets_score(
        self, trufflehog_file: str, gitsecrets_file: str
    ) -> int:
        """计算密钥安全评分"""
        score = 100

        # TruffleHog评分
        if trufflehog_file and Path(trufflehog_file).exists():
            try:
                with open(trufflehog_file, "r") as f:
                    trufflehog_data = json.load(f)

                found_secrets = trufflehog_data.get("FoundSecrets", [])
                score -= len(found_secrets) * 20
            except Exception as e:
                print(f"Error parsing trufflehog report: {e}")

        # Git-secrets评分
        if gitsecrets_file and Path(gitsecrets_file).exists():
            # git-secrets的输出通常是文本格式
            try:
                with open(gitsecrets_file, "r") as f:
                    content = f.read()
                    # 计算发现的问题数量
                    issues = content.count("!!")
                    score -= issues * 15
            except Exception as e:
                print(f"Error parsing git-secrets report: {e}")

        return max(0, score)

    def _calculate_container_score(self, trivy_file: str) -> int:
        """计算容器安全评分"""
        if not trivy_file or not Path(trivy_file).exists():
            return 50  # 中等分数，如果没有扫描

        try:
            with open(trivy_file, "r") as f:
                data = json.load(f)

            results = data.get("Results", [])
            total_score = 100

            for result in results:
                severity = result.get("Severity", "UNKNOWN")
                if severity == "CRITICAL":
                    total_score -= 15
                elif severity == "HIGH":
                    total_score -= 10
                elif severity == "MEDIUM":
                    total_score -= 5
                elif severity == "LOW":
                    total_score -= 2

            return max(0, total_score)

        except Exception as e:
            print(f"Error calculating container score: {e}")
            return 0

    def _get_grade(self, score: float) -> str:
        """获取评分等级"""
        if score >= self.thresholds["critical"]:
            return "A+"
        elif score >= self.thresholds["good"]:
            return "A"
        elif score >= self.thresholds["moderate"]:
            return "B"
        elif score >= self.thresholds["poor"]:
            return "C"
        else:
            return "D"

    def _generate_recommendations(self, scores: Dict[str, Any]) -> List[str]:
        """生成改进建议"""
        recommendations = []

        if scores["dependency_score"] < 70:
            recommendations.append("定期更新依赖项，修复已知漏洞")

        if scores["code_score"] < 70:
            recommendations.append("修复代码安全问题，使用安全的编码实践")

        if scores["secrets_score"] < 80:
            recommendations.append("移除硬编码的密钥，使用环境变量或密钥管理系统")

        if scores["container_score"] < 70:
            recommendations.append("使用安全的容器基础镜像，修复容器配置问题")

        if scores["overall_score"] < 50:
            recommendations.append("实施全面的安全改进计划")

        return recommendations

    def _extract_top_issues(self, reports: Dict[str, str]) -> List[str]:
        """提取主要问题"""
        issues = []

        # 从Safety报告中提取
        if reports.get("safety_report") and Path(reports["safety_report"]).exists():
            try:
                with open(reports["safety_report"], "r") as f:
                    data = json.load(f)
                    vulnerabilities = data.get("vulnerabilities", [])
                    for vuln in vulnerabilities[:3]:
                        issues.append(
                            f"依赖漏洞: {vuln.get('advisory')} ({vuln.get('severity')})"
                        )
            except Exception:
                pass

        # 从Bandit报告中提取
        if reports.get("bandit_report") and Path(reports["bandit_report"]).exists():
            try:
                with open(reports["bandit_report"], "r") as f:
                    data = json.load(f)
                    results = data.get("results", [])
                    for result in results[:3]:
                        issues.append(
                            f"代码问题: {result.get('test_name')} ({result.get('issue_severity')})"
                        )
            except Exception:
                pass

        return issues[:5]  # 返回最多5个问题


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="计算安全评分")
    parser.add_argument("--bandit-report", default="bandit-report.json")
    parser.add_argument("--safety-report", default="safety-report.json")
    parser.add_argument("--semgrep-report", default="semgrep-report.json")
    parser.add_argument("--trufflehog-report", default="trufflehog-report.json")
    parser.add_argument("--gitsecrets-report", default="gitsecrets-report.txt")
    parser.add_argument("--trivy-report", default="trivy-results.sarif")
    parser.add_argument("--output", default="security-score.json")

    args = parser.parse_args()

    # 构建报告文件映射
    reports = {
        "bandit_report": args.bandit_report,
        "safety_report": args.safety_report,
        "semgrep_report": args.semgrep_report,
        "trufflehog_report": args.trufflehog_report,
        "gitsecrets_report": args.gitsecrets_report,
        "trivy_report": args.trivy_report,
    }

    # 计算评分
    calculator = SecurityScoreCalculator()
    scores = calculator.calculate_score(reports)

    # 保存结果
    with open(args.output, "w") as f:
        json.dump(scores, f, indent=2)

    # 打印结果
    print("\n" + "=" * 50)
    print("SECURITY SCORE REPORT")
    print("=" * 50)
    print(f"Overall Score: {scores['overall_score']}/100 ({scores['grade']})")
    print("\nBreakdown:")
    print(f"  Dependencies: {scores['dependency_score']}/100")
    print(f"  Code Analysis: {scores['code_score']}/100")
    print(f"  Secrets: {scores['secrets_score']}/100")
    print(f"  Container: {scores['container_score']}/100")

    if scores["recommendations"]:
        print("\nRecommendations:")
        for rec in scores["recommendations"]:
            print(f"  • {rec}")

    if scores["top_issues"]:
        print("\nTop Issues:")
        for issue in scores["top_issues"]:
            print(f"  • {issue}")

    print(f"\nFull report saved to: {args.output}")
    print("=" * 50)

    # 返回状态码
    sys.exit(0 if scores["overall_score"] >= 70 else 1)


if __name__ == "__main__":
    main()
