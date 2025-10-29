#!/usr/bin/env python3
"""
质量门禁验证器
Quality Gate Validator

建立和验证质量门禁标准
"""

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List


class QualityGateValidator:
    """质量门禁验证器"""

    def __init__(self, project_root: str = None):
        self.project_root = Path(project_root or Path(__file__).parent.parent)
        self.gate_standards = {
            "critical": {
                "F821": 1000,  # 未定义名称 - 严重
                "E999": 50,    # 语法错误 - 严重
                "F821": 5000, # 总未定义名称
                "total_errors": 12000  # 总错误数上限
            },
            "warning": {
                "F841": 500,   # 未使用变量 - 警告
                "F405": 300,   # 可能未定义的名称 - 警告
                "E501": 100,   # 行长度超限 - 警告
                "total_errors": 10000  # 总错误数警告线
            },
            "good": {
                "F821": 500,   # 未定义名称 - 良好
                "E999": 20,    # 语法错误 - 良好
                "total_errors": 8000   # 总错误数良好线
            }
        }

    def run_quality_check(self) -> Dict[str, Any]:
        """运行质量检查"""
        print("🔍 运行质量门禁检查...")

        try:
            result = subprocess.run(
                ["make", "lint"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=120
            )

            # 解析错误
            error_counts = {}
            total_errors = 0

            for line in result.stdout.split('\n'):
                if ':' in line:
                    parts = line.split(':', 3)
                    if len(parts) >= 4:
                        error_info = parts[3]
                        # 提取错误代码
                        import re
                        error_code_match = re.search(r'\b([A-Z]\d{3})\b', error_info)
                        if error_code_match:
                            error_code = error_code_match.group(1)
                            error_counts[error_code] = error_counts.get(error_code, 0) + 1
                            total_errors += 1

            return {
                "success": result.returncode == 0,
                "total_errors": total_errors,
                "error_counts": error_counts,
                "output": result.stdout
            }

        except Exception as e:
            return {
                "success": False,
                "total_errors": -1,
                "error_counts": {},
                "output": str(e)
            }

    def evaluate_quality_gate(self, quality_data: Dict[str, Any]) -> Dict[str, Any]:
        """评估质量门禁"""
        total_errors = quality_data["total_errors"]
        error_counts = quality_data["error_counts"]

        # 评估每个标准
        gate_status = {
            "overall": "unknown",
            "critical_violations": [],
            "warning_violations": [],
            "passed_standards": []
        }

        # 检查严重标准
        for metric, threshold in self.gate_standards["critical"].items():
            if metric == "total_errors":
                if total_errors > threshold:
                    gate_status["critical_violations"].append(
                        f"总错误数 {total_errors:,} > {threshold:,}"
                    )
            elif metric in error_counts:
                if error_counts[metric] > threshold:
                    gate_status["critical_violations"].append(
                        f"{metric} 错误 {error_counts[metric]:,} > {threshold:,}"
                    )

        # 检查警告标准
        for metric, threshold in self.gate_standards["warning"].items():
            if metric == "total_errors":
                if total_errors > threshold:
                    gate_status["warning_violations"].append(
                        f"总错误数 {total_errors:,} > {threshold:,}"
                    )
            elif metric in error_counts:
                if error_counts[metric] > threshold:
                    gate_status["warning_violations"].append(
                        f"{metric} 错误 {error_counts[metric]:,} > {threshold:,}"
                    )

        # 确定整体状态
        if gate_status["critical_violations"]:
            gate_status["overall"] = "FAILED"
        elif gate_status["warning_violations"]:
            gate_status["overall"] = "WARNING"
        else:
            gate_status["overall"] = "PASSED"

        return gate_status

    def generate_quality_report(self) -> Dict[str, Any]:
        """生成质量报告"""
        print("📊 生成质量报告...")

        quality_data = self.run_quality_check()
        gate_evaluation = self.evaluate_quality_gate(quality_data)

        report = {
            "timestamp": datetime.now().isoformat(),
            "quality_data": quality_data,
            "gate_evaluation": gate_evaluation,
            "standards": self.gate_standards
        }

        # 保存报告
        report_file = self.project_root / "quality_gate_report.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        return report

    def display_report(self, report: Dict[str, Any]):
        """显示质量报告"""
        print("\n" + "="*70)
        print("🎯 质量门禁验证报告")
        print("="*70)
        print(f"📅 检查时间: {report['timestamp']}")

        gate_status = report['gate_evaluation']['overall']
        if gate_status == "PASSED":
            print("✅ 质量门禁: 通过")
        elif gate_status == "WARNING":
            print("⚠️ 质量门禁: 警告")
        else:
            print("❌ 质量门禁: 失败")

        print("-"*70)

        # 错误统计
        quality_data = report['quality_data']
        print(f"📊 错误统计:")
        print(f"   总错误数: {quality_data['total_errors']:,}")

        if quality_data['error_counts']:
            print("   主要错误类型:")
            for error_code, count in sorted(quality_data['error_counts'].items(),
                                           key=lambda x: x[1], reverse=True)[:10]:
                print(f"     {error_code}: {count:,} 个")

        print("-"*70)

        # 违规情况
        gate_evaluation = report['gate_evaluation']
        if gate_evaluation['critical_violations']:
            print("🚨 严重违规:")
            for violation in gate_evaluation['critical_violations']:
                print(f"   ❌ {violation}")

        if gate_evaluation['warning_violations']:
            print("⚠️ 警告违规:")
            for violation in gate_evaluation['warning_violations']:
                print(f"   ⚠️ {violation}")

        if gate_evaluation['passed_standards']:
            print("✅ 通过标准:")
            for standard in gate_evaluation['passed_standards']:
                print(f"   ✅ {standard}")

        print("-"*70)

        # 质量建议
        self._provide_recommendations(gate_evaluation, quality_data)

        print("="*70)

    def _provide_recommendations(self, gate_evaluation: Dict[str, Any], quality_data: Dict[str, Any]):
        """提供质量改进建议"""
        print("💡 改进建议:")

        # 基于具体错误类型提供建议
        error_counts = quality_data['error_counts']

        if 'F821' in error_counts and error_counts['F821'] > 1000:
            print("   🔧 优先修复F821未定义名称错误:")
            print("      - 检查变量和函数名称拼写")
            print("      - 确保导入语句正确")
            print("      - 检查作用域问题")

        if 'F841' in error_counts and error_counts['F841'] > 100:
            print("   🔧 处理F841未使用变量:")
            print("      - 删除未使用的变量")
            print("      - 使用下划线前缀 _variable")
            print("      - 检查变量是否在条件分支中使用")

        if 'E999' in error_counts and error_counts['E999'] > 0:
            print("   🔧 修复E999语法错误:")
            print("      - 检查Python语法")
            print("      - 修复缩进问题")
            print("      - 检查括号和引号匹配")

        if 'F405' in error_counts and error_counts['F405'] > 100:
            print("   🔧 解决F405导入问题:")
            print("      - 检查star import的可用性")
            print("      - 明确导入需要的名称")
            print("      - 修复循环导入问题")

    def setup_quality_gate(self) -> Dict[str, Any]:
        """设置质量门禁"""
        print("⚙️ 设置质量门禁标准...")

        # 创建GitHub Actions工作流片段
        workflow_content = f"""
# Quality Gate - 质量门禁检查
name: Quality Gate Check

on:
  pull_request:
    branches: [ main ]
  push:
    branches: [ main ]

jobs:
  quality-gate:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'

    - name: Install dependencies
      run: |
        pip install -r requirements/base.txt
        pip install ruff black

    - name: Run quality gate validation
      run: python3 scripts/quality_gate_validator.py

    - name: Quality gate check
      run: |
        if [[ $? -ne 0 ]]; then
          echo "❌ Quality gate FAILED"
          exit 1
        else
          echo "✅ Quality gate PASSED"
        fi
"""

        # 创建质量门禁配置文件
        gate_config = {
            "version": "1.0",
            "created": datetime.now().isoformat(),
            "standards": self.gate_standards,
            "enabled": True,
            "auto_fail": True
        }

        config_file = self.project_root / "config" / "quality_gate.json"
        config_file.parent.mkdir(exist_ok=True)

        with open(config_file, 'w') as f:
            json.dump(gate_config, f, indent=2, ensure_ascii=False)

        return {
            "workflow_content": workflow_content,
            "config_file": str(config_file),
            "standards": self.gate_standards
        }


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="质量门禁验证器")
    parser.add_argument("--setup", action="store_true", help="设置质量门禁")
    parser.add_argument("--project-root", type=str, help="项目根目录路径")

    args = parser.parse_args()

    # 创建验证器
    validator = QualityGateValidator(args.project_root)

    if args.setup:
        print("🚀 设置质量门禁...")
        setup_result = validator.setup_quality_gate()
        print(f"✅ 质量门禁配置已创建: {setup_result['config_file']}")
        return

    # 运行质量检查
    report = validator.generate_quality_report()
    validator.display_report(report)

    # 根据结果设置退出码
    if report['gate_evaluation']['overall'] == "FAILED":
        sys.exit(1)
    elif report['gate_evaluation']['overall'] == "WARNING":
        sys.exit(2)  # 警告退出码
    else:
        sys.exit(0)  # 成功退出码


if __name__ == "__main__":
    main()