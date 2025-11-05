#!/usr/bin/env python3
"""
代码质量门禁脚本
确保代码符合质量标准才能通过CI/CD
"""

import subprocess
import sys
import json
from pathlib import Path

class QualityGate:
    def __init__(self):
        self.results = {}
        self.thresholds = {
            'b904_max': 50,  # B904错误最大数量
            'e402_max': 100,  # E402错误最大数量
            'syntax_max': 0,   # 语法错误最大数量
            'type_errors_max': 20,  # 类型错误最大数量
        }

    def run_command(self, cmd, description):
        """运行命令并返回结果"""
        print(f"🔍 {description}...")
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=60
            )
            return {
                'success': result.returncode == 0,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'returncode': result.returncode
            }
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'stdout': '',
                'stderr': 'Command timeout',
                'returncode': 124
            }

    def check_syntax_errors(self):
        """检查语法错误"""
        cmd = "python -m py_compile src/**/*.py"
        result = self.run_command(cmd, "检查语法错误")

        # 计算语法错误数量
        syntax_errors = 0
        if not result['success']:
            # 解析Python编译错误
            for line in result['stderr'].split('\n'):
                if 'SyntaxError' in line or 'IndentationError' in line:
                    syntax_errors += 1

        self.results['syntax_errors'] = {
            'count': syntax_errors,
            'threshold': self.thresholds['syntax_max'],
            'passed': syntax_errors <= self.thresholds['syntax_max']
        }

        return self.results['syntax_errors']['passed']

    def check_b904_errors(self):
        """检查B904错误"""
        cmd = "ruff check src/ --select=B904 --output-format=json"
        result = self.run_command(cmd, "检查B904异常处理错误")

        b904_count = 0
        if result['success'] and result['stdout']:
            try:
                errors = json.loads(result['stdout'])
                b904_count = len(errors)
            except json.JSONDecodeError:
                # 如果不是JSON格式，计算行数
                b904_count = len([line for line in result['stdout'].split('\n') if line.strip()])

        self.results['b904_errors'] = {
            'count': b904_count,
            'threshold': self.thresholds['b904_max'],
            'passed': b904_count <= self.thresholds['b904_max']
        }

        return self.results['b904_errors']['passed']

    def check_e402_errors(self):
        """检查E402错误"""
        cmd = "ruff check src/ --select=E402 --output-format=json"
        result = self.run_command(cmd, "检查E402导入位置错误")

        e402_count = 0
        if result['success'] and result['stdout']:
            try:
                errors = json.loads(result['stdout'])
                e402_count = len(errors)
            except json.JSONDecodeError:
                e402_count = len([line for line in result['stdout'].split('\n') if line.strip()])

        self.results['e402_errors'] = {
            'count': e402_count,
            'threshold': self.thresholds['e402_max'],
            'passed': e402_count <= self.thresholds['e402_max']
        }

        return self.results['e402_errors']['passed']

    def check_type_errors(self):
        """检查类型错误"""
        cmd = "mypy src/ --ignore-missing-imports --no-error-summary"
        result = self.run_command(cmd, "检查类型错误")

        type_errors = 0
        if not result['success']:
            # 计算mypy错误行数
            type_errors = len([line for line in result['stderr'].split('\n') if line.strip() and not line.startswith('note:')])

        self.results['type_errors'] = {
            'count': type_errors,
            'threshold': self.thresholds['type_errors_max'],
            'passed': type_errors <= self.thresholds['type_errors_max']
        }

        return self.results['type_errors']['passed']

    def run_all_checks(self):
        """运行所有质量检查"""
        print("🚀 启动代码质量门禁检查...")
        print("=" * 50)

        checks = [
            ('syntax_errors', self.check_syntax_errors),
            ('b904_errors', self.check_b904_errors),
            ('e402_errors', self.check_e402_errors),
            ('type_errors', self.check_type_errors),
        ]

        all_passed = True
        for check_name, check_func in checks:
            passed = check_func()
            status = "✅ PASS" if passed else "❌ FAIL"
            result = self.results[check_name]
            print(f"{status} {check_name}: {result['count']}/{result['threshold']}")

            if not passed:
                all_passed = False

        print("=" * 50)

        if all_passed:
            print("🎉 所有质量检查通过！代码质量门禁PASS")
            return 0
        else:
            print("🚫 质量检查失败！代码质量门禁FAIL")
            print("\n📊 详细结果:")
            for check_name, result in self.results.items():
                if not result['passed']:
                    print(f"  - {check_name}: {result['count']} > {result['threshold']}")
            return 1

    def generate_report(self):
        """生成质量报告"""
        report = {
            'timestamp': '2025-11-05 16:00',
            'results': self.results,
            'summary': {
                'total_checks': len(self.results),
                'passed_checks': sum(1 for r in self.results.values() if r['passed']),
                'failed_checks': sum(1 for r in self.results.values() if not r['passed'])
            }
        }

        # 保存报告
        report_file = Path('quality_report.json')
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)

        print(f"📄 质量报告已生成: {report_file}")
        return report

def main():
    """主函数"""
    quality_gate = QualityGate()

    # 运行所有检查
    exit_code = quality_gate.run_all_checks()

    # 生成报告
    quality_gate.generate_report()

    sys.exit(exit_code)

if __name__ == "__main__":
    main()