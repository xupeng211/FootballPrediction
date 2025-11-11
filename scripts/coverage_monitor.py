#!/usr/bin/env python3
"""
测试覆盖率监控工具
Test Coverage Monitoring Tool

提供准确的测试覆盖率统计和监控功能，确保GitHub Issues状态与实际情况一致。
Provides accurate test coverage statistics and monitoring to ensure GitHub Issues status matches reality.
"""

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


class CoverageMonitor:
    """测试覆盖率监控器"""

    def __init__(self, project_root: Path | None = None):
        self.project_root = project_root or Path(__file__).parent.parent
        self.report_dir = self.project_root / "reports"
        self.report_dir.mkdir(exist_ok=True)

    def run_coverage_test(self) -> dict[str, Any]:
        """运行覆盖率测试并返回结果"""
        try:
            cmd = [
                sys.executable, "-m", "pytest",
                "tests/unit", "tests/integration",
                "--cov=src",
                "--cov-report=json",
                "--cov-report=term-missing",
                "--tb=no",
                "-q"
            ]

            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=300  # 5分钟超时
            )

            # 读取覆盖率JSON报告
            coverage_file = self.project_root / "coverage.json"
            if coverage_file.exists():
                with open(coverage_file) as f:
                    coverage_data = json.load(f)

                total_coverage = coverage_data.get('totals', {}).get('percent_covered', 0)

                return {
                    "success": result.returncode == 0,
                    "total_coverage": round(total_coverage, 2),
                    "files_covered": len(coverage_data.get('files', {})),
                    "raw_output": result.stdout,
                    "error_output": result.stderr,
                    "timestamp": datetime.now().isoformat(),
                    "coverage_details": self._analyze_coverage_details(coverage_data)
                }
            else:
                return {
                    "success": False,
                    "error": "Coverage report not generated",
                    "raw_output": result.stdout,
                    "error_output": result.stderr
                }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "Coverage test timed out",
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }

    def _analyze_coverage_details(self, coverage_data: dict[str, Any]) -> dict[str, Any]:
        """分析覆盖率详情"""
        files = coverage_data.get('files', {})

        high_coverage = []
        medium_coverage = []
        low_coverage = []
        no_coverage = []

        for file_path, file_data in files.items():
            coverage_percent = file_data.get('summary', {}).get('percent_covered', 0)

            file_info = {
                "path": file_path,
                "coverage": round(coverage_percent, 2),
                "statements": file_data.get('summary', {}).get('num_statements', 0),
                "missing": file_data.get('summary', {}).get('missing_lines', 0)
            }

            if coverage_percent >= 70:
                high_coverage.append(file_info)
            elif coverage_percent >= 30:
                medium_coverage.append(file_info)
            elif coverage_percent > 0:
                low_coverage.append(file_info)
            else:
                no_coverage.append(file_info)

        return {
            "high_coverage": sorted(high_coverage, key=lambda x: x['coverage'], reverse=True),
            "medium_coverage": sorted(medium_coverage, key=lambda x: x['coverage'], reverse=True),
            "low_coverage": sorted(low_coverage, key=lambda x: x['coverage'], reverse=True),
            "no_coverage": sorted(no_coverage, key=lambda x: x['path'])
        }

    def check_target_achievement(self, target_coverage: float = 30.0) -> dict[str, Any]:
        """检查覆盖率目标达成情况"""
        coverage_result = self.run_coverage_test()

        if not coverage_result["success"]:
            return {
                "target_achieved": False,
                "error": coverage_result.get("error"),
                "current_coverage": 0,
                "target_coverage": target_coverage,
                "gap": target_coverage
            }

        current_coverage = coverage_result["total_coverage"]
        gap = target_coverage - current_coverage

        return {
            "target_achieved": current_coverage >= target_coverage,
            "current_coverage": current_coverage,
            "target_coverage": target_coverage,
            "gap": max(0, gap),
            "progress_percentage": min(100, (current_coverage / target_coverage) * 100),
            "details": coverage_result
        }

    def generate_report(self) -> str:
        """生成覆盖率监控报告"""
        target_check = self.check_target_achievement(30.0)

        report = f"""# 📊 测试覆盖率监控报告

**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**监控工具**: Coverage Monitor v1.0

## 🎯 目标达成情况

| 指标 | 当前值 | 目标值 | 状态 |
|------|--------|--------|------|
| 总覆盖率 | {target_check['current_coverage']:.2f}% | 30.00% | {'✅ 已达成' if target_check['target_achieved'] else '❌ 未达成'} |
| 进度百分比 | {target_check['progress_percentage']:.1f}% | 100% | {'🎉 完成' if target_check['target_achieved'] else f'🔄 进行中 (还差{target_check["gap"]:.2f}%)'} |

## 📈 覆盖率详情分析

"""

        if target_check["details"].get("coverage_details"):
            details = target_check["details"]["coverage_details"]

            report += f"""
### 🟢 高覆盖率模块 (>70%)
{chr(10).join([f"- **{file['path']}**: {file['coverage']}% ({file['statements']} statements)" for file in details['high_coverage'][:5]])}

### 🟡 中等覆盖率模块 (30-70%)
{chr(10).join([f"- **{file['path']}**: {file['coverage']}% ({file['statements']} statements)" for file in details['medium_coverage'][:5]])}

### 🔴 低覆盖率模块 (<30%)
{chr(10).join([f"- **{file['path']}**: {file['coverage']}% ({file['statements']} statements)" for file in details['low_coverage'][:5]])}

### ⚫ 无覆盖率模块
{chr(10).join([f"- **{file['path']}**: 0% ({file['statements']} statements)" for file in details['no_coverage'][:5]])}
"""

        report += f"""
## 🔧 建议改进措施

{'### ✅ 当前状态良好' if target_check['target_achieved'] else '### ⚠️ 需要改进'}

1. **优先处理低覆盖率模块**: 重点提升覆盖率低于30%的模块
2. **修复测试失败问题**: 确保所有测试都能稳定运行
3. **添加API模块测试**: 大部分API模块当前没有测试覆盖
4. **建立持续监控**: 定期运行此监控工具

## 📋 GitHub Issues状态建议

基于当前覆盖率 {target_check['current_coverage']:.2f}%：

- {'✅ Issues状态准确' if abs(target_check['current_coverage'] - 24.09) < 1 else '⚠️ 需要更新Issues状态'}
- {'🎯 可以标记为completed' if target_check['target_achieved'] else '🔄 需要继续工作'}
- 📊 建议创建新的细分Issues处理具体模块

---

**报告结论**: 测试覆盖率{'已达成' if target_check['target_achieved'] else '未达成'}30%目标，当前为{target_check['current_coverage']:.2f}%。
"""

        return report

    def save_report(self, report: str) -> Path:
        """保存报告到文件"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_file = self.report_dir / f"coverage_report_{timestamp}.md"

        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)

        # 也保存为最新的报告
        latest_file = self.report_dir / "latest_coverage_report.md"
        with open(latest_file, 'w', encoding='utf-8') as f:
            f.write(report)

        return report_file


def main():
    """主函数"""
    monitor = CoverageMonitor()


    # 生成报告
    report = monitor.generate_report()

    # 保存报告
    monitor.save_report(report)


    # 检查目标达成情况
    target_check = monitor.check_target_achievement(30.0)

    if target_check['target_achieved']:
        return 0
    else:
        return 1


if __name__ == "__main__":
    sys.exit(main())
