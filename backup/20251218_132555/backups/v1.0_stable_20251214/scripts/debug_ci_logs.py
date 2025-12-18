#!/usr/bin/env python3
"""
CI日志调取和分析工具
CI Log Extraction and Analysis Tool

用于自主调取GitHub Actions CI日志并分析失败的根因
For autonomous extraction and analysis of GitHub Actions CI failure logs

作者: AI Assistant
版本: 1.0.0
创建时间: 2025-12-12
"""

import os
import sys
import json
import requests
import subprocess
import re
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

class CILogAnalyzer:
    """CI日志分析器"""

    def __init__(self, repo_owner: str = "xupeng211", repo_name: str = "FootballPrediction"):
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.base_url = "https://api.github.com"
        self.session = requests.Session()
        self._setup_auth()

    def _setup_auth(self):
        """设置GitHub API认证"""
        # 尝试多种方法获取token
        token = None

        # 方法1: 环境变量
        if 'GITHUB_TOKEN' in os.environ:
            token = os.environ['GITHUB_TOKEN']

        # 方法2: 从git remote URL提取
        if not token:
            try:
                remote_url = subprocess.check_output(
                    ["git", "remote", "get-url", "origin"],
                    stderr=subprocess.DEVNULL
                ).decode().strip()

                # 匹配格式: https://token@github.com/owner/repo.git
                match = re.search(r'https://([^@]+)@github\.com/', remote_url)
                if match:
                    token = match.group(1)
            except Exception:
                pass

        # 方法3: 尝试gh CLI获取token
        if not token:
            try:
                result = subprocess.run(
                    ["gh", "auth", "token"],
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    token = result.stdout.strip()
            except Exception:
                pass

        if token:
            self.session.headers.update({"Authorization": f"token {token}"})
            print(f"✅ GitHub API认证已配置")
        else:
            print("⚠️ 无法获取GitHub token，将使用未认证请求（可能有速率限制）")

    def get_recent_workflows(self, limit: int = 10) -> List[Dict]:
        """获取最近的工作流程运行"""
        url = f"{self.base_url}/repos/{self.repo_owner}/{self.repo_name}/actions/workflows"

        try:
            response = self.session.get(url, params={"per_page": limit})
            response.raise_for_status()

            workflows = response.json().get("workflows", [])
            print(f"📋 获取到 {len(workflows)} 个工作流程")

            return workflows[:limit]
        except Exception as e:
            print(f"❌ 获取工作流程失败: {e}")
            return []

    def get_workflow_runs(self, workflow_id: str, limit: int = 5) -> List[Dict]:
        """获取特定工作流程的运行记录"""
        url = f"{self.base_url}/repos/{self.repo_owner}/{self.repo_name}/actions/workflows/{workflow_id}/runs"

        try:
            response = self.session.get(url, params={"per_page": limit})
            response.raise_for_status()

            runs = response.json().get("workflow_runs", [])
            print(f"🏃 获取到 {len(runs)} 次运行记录")

            return runs[:limit]
        except Exception as e:
            print(f"❌ 获取运行记录失败: {e}")
            return []

    def get_recent_failed_runs(self, limit: int = 3) -> List[Dict]:
        """获取最近的失败运行"""
        url = f"{self.base_url}/repos/{self.repo_owner}/{self.repo_name}/actions/runs"

        try:
            response = self.session.get(
                url,
                params={
                    "per_page": 50,  # 获取更多记录以筛选失败
                    "status": "failure"
                }
            )
            response.raise_for_status()

            all_runs = response.json().get("workflow_runs", [])
            failed_runs = [run for run in all_runs if run.get("conclusion") == "failure"]

            print(f"❌ 找到 {len(failed_runs)} 次失败运行")

            return failed_runs[:limit]
        except Exception as e:
            print(f"❌ 获取失败运行失败: {e}")
            return []

    def get_run_jobs(self, run_id: int) -> List[Dict]:
        """获取运行的所有任务"""
        url = f"{self.base_url}/repos/{self.repo_owner}/{self.repo_name}/actions/runs/{run_id}/jobs"

        try:
            response = self.session.get(url)
            response.raise_for_status()

            jobs = response.json().get("jobs", [])
            failed_jobs = [job for job in jobs if job.get("conclusion") == "failure"]

            print(f"💼 运行 {run_id} 有 {len(jobs)} 个任务，其中 {len(failed_jobs)} 个失败")

            return jobs
        except Exception as e:
            print(f"❌ 获取任务失败: {e}")
            return []

    def get_job_logs(self, job_id: int) -> Optional[str]:
        """获取任务日志"""
        url = f"{self.base_url}/repos/{self.repo_owner}/{self.repo_name}/actions/jobs/{job_id}/logs"

        try:
            response = self.session.get(url)
            if response.status_code == 302:
                # GitHub API返回重定向到实际的日志文件
                log_url = response.headers.get("location")
                if log_url:
                    response = self.session.get(log_url)

            if response.status_code == 200:
                # 日志通常以.gz格式提供
                if isinstance(response.content, bytes):
                    try:
                        import gzip
                        logs = gzip.decompress(response.content).decode('utf-8')
                    except Exception:
                        logs = response.content.decode('utf-8', errors='ignore')
                else:
                    logs = response.text

                return logs
            else:
                print(f"⚠️ 获取日志失败，状态码: {response.status_code}")
                return None

        except Exception as e:
            print(f"❌ 获取任务日志失败: {e}")
            return None

    def analyze_failure_logs(self, logs: str) -> Dict[str, Any]:
        """分析失败日志，提取关键错误信息"""
        if not logs:
            return {"errors": [], "warnings": [], "key_info": []}

        lines = logs.split('\n')
        analysis = {
            "errors": [],
            "warnings": [],
            "key_info": [],
            "test_failures": [],
            "import_errors": [],
            "syntax_errors": []
        }

        # 错误模式
        error_patterns = [
            r"ERROR:\s*(.+)",
            r"Traceback \(most recent call last\):",
            r"Exception:\s*(.+)",
            r"Failed:\s*(.+)",
            r"AssertionError:\s*(.+)"
        ]

        # 警告模式
        warning_patterns = [
            r"WARNING:\s*(.+)",
            r"warning:\s*(.+)",
            r"DeprecationWarning:\s*(.+)"
        ]

        # 测试失败模式
        test_failure_patterns = [
            r"FAILED\s+(.+::.+)",
            r"tests? \.\.\. failed",
            r"pytest.*failed"
        ]

        # 导入错误模式
        import_error_patterns = [
            r"ImportError:\s*(.+)",
            r"ModuleNotFoundError:\s*(.+)",
            r"No module named ['\"]([^'\"]+)['\"]"
        ]

        # 语法错误模式
        syntax_error_patterns = [
            r"SyntaxError:\s*(.+)",
            r"invalid syntax",
            r"unexpected EOF"
        ]

        for line in lines:
            line_stripped = line.strip()

            # 检查各种错误模式
            for pattern in error_patterns:
                matches = re.findall(pattern, line_stripped)
                if matches:
                    analysis["errors"].extend(matches)

            for pattern in warning_patterns:
                matches = re.findall(pattern, line_stripped)
                if matches:
                    analysis["warnings"].extend(matches)

            for pattern in test_failure_patterns:
                matches = re.findall(pattern, line_stripped)
                if matches:
                    analysis["test_failures"].extend(matches)

            for pattern in import_error_patterns:
                matches = re.findall(pattern, line_stripped)
                if matches:
                    analysis["import_errors"].extend(matches)

            for pattern in syntax_error_patterns:
                matches = re.findall(pattern, line_stripped)
                if matches:
                    analysis["syntax_errors"].extend(matches)

        # 去重和统计
        for key in analysis:
            analysis[key] = list(set(analysis[key]))

        return analysis

    def print_analysis_summary(self, analysis: Dict[str, Any]):
        """打印分析摘要"""
        print("\n" + "="*60)
        print("🔍 CI失败日志分析摘要")
        print("="*60)

        if analysis["errors"]:
            print(f"\n❌ 发现 {len(analysis['errors'])} 个错误:")
            for i, error in enumerate(analysis["errors"][:10], 1):
                print(f"   {i}. {error}")

        if analysis["syntax_errors"]:
            print(f"\n🔤 发现 {len(analysis['syntax_errors'])} 个语法错误:")
            for i, error in enumerate(analysis["syntax_errors"][:5], 1):
                print(f"   {i}. {error}")

        if analysis["import_errors"]:
            print(f"\n📦 发现 {len(analysis['import_errors'])} 个导入错误:")
            for i, error in enumerate(analysis["import_errors"][:5], 1):
                print(f"   {i}. {error}")

        if analysis["test_failures"]:
            print(f"\n🧪 发现 {len(analysis['test_failures'])} 个测试失败:")
            for i, failure in enumerate(analysis["test_failures"][:5], 1):
                print(f"   {i}. {failure}")

        if analysis["warnings"]:
            print(f"\n⚠️ 发现 {len(analysis['warnings'])} 个警告:")
            for i, warning in enumerate(analysis["warnings"][:5], 1):
                print(f"   {i}. {warning}")

        print("\n" + "="*60)

    def suggest_fixes(self, analysis: Dict[str, Any]) -> List[str]:
        """基于分析结果建议修复方案"""
        suggestions = []

        if analysis["syntax_errors"]:
            suggestions.append("🔧 修复语法错误 - 检查代码中的语法问题")
            suggestions.append("   建议: 运行 'python -m py_compile src/**/*.py' 检查语法")

        if analysis["import_errors"]:
            suggestions.append("📦 修复导入错误 - 检查缺失的依赖和模块路径")
            suggestions.append("   建议: 检查 requirements.txt 和 Python 路径配置")

        if any("prometheus" in str(err).lower() for err in analysis["errors"]):
            suggestions.append("📊 修复Prometheus相关错误 - 检查prometheus-fastapi-instrumentator版本兼容性")

        if any("loguru" in str(err).lower() for err in analysis["errors"]):
            suggestions.append("📝 修复Loguru日志配置 - 检查颜色标签格式")

        if analysis["test_failures"]:
            suggestions.append("🧪 修复测试失败 - 检查测试用例和依赖环境")
            suggestions.append("   建议: 运行 'pytest --tb=short' 查看详细错误")

        if not suggestions:
            suggestions.append("✅ 未发现明显的错误模式，可能需要更详细的日志分析")

        return suggestions


def main():
    """主函数"""
    print("🚀 启动CI日志分析工具")
    print("="*50)

    analyzer = CILogAnalyzer()

    # 获取最近的失败运行
    print("1. 获取最近的失败CI运行...")
    failed_runs = analyzer.get_recent_failed_runs(limit=3)

    if not failed_runs:
        print("🎉 没有发现失败的运行")
        return

    # 分析每个失败的运行
    for i, run in enumerate(failed_runs, 1):
        print(f"\n{i}. 分析失败运行: {run.get('name', 'Unknown')} (ID: {run.get('id')})")
        print(f"   时间: {run.get('created_at', 'Unknown')}")
        print(f"   状态: {run.get('conclusion', 'Unknown')}")

        # 获取运行的任务
        jobs = analyzer.get_run_jobs(run['id'])
        failed_jobs = [job for job in jobs if job.get('conclusion') == 'failure']

        if not failed_jobs:
            print("   ℹ️ 没有失败的任务")
            continue

        # 分析每个失败的任务
        for job in failed_jobs:
            print(f"\n   🔍 分析失败任务: {job.get('name', 'Unknown')} (ID: {job.get('id')})")

            # 获取任务日志
            logs = analyzer.get_job_logs(job['id'])
            if logs:
                # 分析日志
                analysis = analyzer.analyze_failure_logs(logs)
                analyzer.print_analysis_summary(analysis)

                # 提供修复建议
                suggestions = analyzer.suggest_fixes(analysis)
                if suggestions:
                    print("💡 修复建议:")
                    for suggestion in suggestions:
                        print(f"   {suggestion}")
            else:
                print("   ⚠️ 无法获取任务日志")

        print("\n" + "="*80)


if __name__ == "__main__":
    main()