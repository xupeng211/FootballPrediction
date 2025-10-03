import os
#!/usr/bin/env python3
"""
覆盖率持续监控脚本
自动跟踪测试覆盖率变化并生成改进建议
"""

import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

class CoverageMonitor:
    """覆盖率监控器"""

    def __init__(self, data_file: str = "coverage_data.json"):
        self.data_file = Path(data_file)
        self.load_history()

    def load_history(self):
        """加载历史数据"""
        if self.data_file.exists():
            try:
                with open(self.data_file, 'r') as f:
                    self.history = json.load(f)
            except Exception as e:
                print(f"⚠️ 加载历史数据失败: {e}")
                self.history = []
        else:
            self.history = []

    def save_history(self):
        """保存历史数据"""
        try:
            with open(self.data_file, 'w') as f:
                json.dump(self.history, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"❌ 保存历史数据失败: {e}")

    def run_coverage_analysis(self) -> Optional[Dict]:
        """运行覆盖率分析"""
        print("🔍 分析测试覆盖率...")

        # 使用简化的分析工具
        cmd = [sys.executable, "simple_coverage_check.py"]
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120
            )

            if result.returncode == 0:
                # 解析输出
                coverage_data = self.parse_coverage_output(result.stdout)
                return coverage_data
            else:
                print(f"⚠️ 覆盖率分析失败: {result.stderr}")
                return None
        except subprocess.TimeoutExpired:
            print("❌ 覆盖率分析超时")
            return None
        except Exception as e:
            print(f"❌ 运行覆盖率分析失败: {e}")
            return None

    def parse_coverage_output(self, output: str) -> Dict:
        """解析覆盖率输出"""
        lines = output.split('\n')
        coverage_data = {
            "timestamp": datetime.now().isoformat(),
            "modules": {},
            "average_coverage": 0.0
        }

        # 解析每个模块的覆盖率
        for line in lines:
            if "🟢" in line or "🟡" in line or "🔴" in line:
                parts = line.strip().split()
                if len(parts) >= 2:
                    module_name = parts[1]
                    coverage_str = parts[2].rstrip('%')
                    try:
                        coverage = float(coverage_str)
                        coverage_data["modules"][module_name] = coverage
                    except ValueError:
                        continue
            elif "📈 平均覆盖率:" in line:
                try:
                    coverage = float(line.split(':')[1].strip().rstrip('%'))
                    coverage_data["average_coverage"] = coverage
                except (IndexError, ValueError):
                    pass

        return coverage_data

    def generate_improvement_suggestions(self, coverage_data: Dict) -> List[Dict]:
        """生成改进建议"""
        suggestions = []

        for module, coverage in coverage_data["modules"].items():
            if coverage < 20:
                suggestions.append({
                    "priority": "high",
                    "module": module,
                    "current_coverage": coverage,
                    "target_coverage": 30,
                    "suggestion": f"为{module}模块创建基础测试框架",
                    "actions": [
                        f"创建 tests/unit/api/test_{module}.py",
                        "测试主要函数和类",
                        "模拟外部依赖"
                    ]
                })
            elif coverage < 50:
                suggestions.append({
                    "priority": "medium",
                    "module": module,
                    "current_coverage": coverage,
                    "target_coverage": 50,
                    "suggestion": f"提升{module}模块的测试覆盖率",
                    "actions": [
                        f"补充 tests/unit/api/test_{module}.py 中的测试用例",
                        "测试边界条件和异常情况",
                        "增加集成测试"
                    ]
                })

        # 按优先级排序
        suggestions.sort(key=lambda x: (x["priority"] != "high", x["current_coverage"]))
        return suggestions

    def generate_report(self, coverage_data: Dict, suggestions: List[Dict]) -> str:
        """生成覆盖率报告"""
        report = []
        report.append("=" * 60)
        report.append("📊 测试覆盖率监控报告")
        report.append("=" * 60)
        report.append(f"📅 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"📈 平均覆盖率: {coverage_data['average_coverage']:.1f}%")
        report.append("")

        # 模块覆盖率排名
        report.append("📋 模块覆盖率排名:")
        sorted_modules = sorted(
            coverage_data["modules"].items(),
            key=lambda x: x[1],
            reverse=True
        )

        for module, coverage in sorted_modules:
            if coverage >= 50:
                icon = "🟢"
            elif coverage >= 20:
                icon = "🟡"
            else:
                icon = "🔴"
            report.append(f"  {icon} {module:<25} {coverage:>5.1f}%")

        # 改进建议
        if suggestions:
            report.append("")
            report.append("💡 改进建议:")
            for i, suggestion in enumerate(suggestions[:5], 1):
                report.append(f"\n{i}. 【{suggestion['priority'].upper()}】{suggestion['module']}")
                report.append(f"   当前: {suggestion['current_coverage']:.1f}% → 目标: {suggestion['target_coverage']}%")
                report.append(f"   建议: {suggestion['suggestion']}")
                report.append("   行动:")
                for action in suggestion['actions']:
                    report.append(f"     • {action}")

        # 历史趋势
        if len(self.history) > 1:
            report.append("")
            report.append("📈 历史趋势:")
            last_data = self.history[-1]
            if last_data["modules"]:
                last_avg = sum(last_data["modules"].values()) / len(last_data["modules"])
                change = coverage_data["average_coverage"] - last_avg
                if change > 0:
                    report.append(f"  ↗️ 提升 +{change:.1f}%")
                elif change < 0:
                    report.append(f"  ↘️ 下降 {change:.1f}%")
                else:
                    report.append(f"  ➡️ 持平 {change:.1f}%")

        return "\n".join(report)

    def monitor(self):
        """执行监控"""
        print("🚀 开始覆盖率监控...")

        # 分析当前覆盖率
        coverage_data = self.run_coverage_analysis()
        if not coverage_data:
            print("❌ 无法获取覆盖率数据")
            return False

        # 生成改进建议
        suggestions = self.generate_improvement_suggestions(coverage_data)

        # 生成报告
        report = self.generate_report(coverage_data, suggestions)
        print(report)

        # 保存数据
        self.history.append(coverage_data)
        # 只保留最近30条记录
        if len(self.history) > 30:
            self.history = self.history[-30:]
        self.save_history()

        # 保存报告
        report_file = Path(f"coverage_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md")
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"\n📄 报告已保存到: {report_file}")

        return True

    def continuous_monitor(self, interval_minutes: int = 60):
        """持续监控"""
        print(f"🔄 启动持续监控模式 (间隔: {interval_minutes} 分钟)")

        try:
            while True:
                print(f"\n{'='*60}")
                print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - 执行监控")

                success = self.monitor()

                if success:
                    print("✅ 监控完成")
                else:
                    print("❌ 监控失败")

                print(f"⏳ 等待 {interval_minutes} 分钟后执行下一次监控...")
                time.sleep(interval_minutes * 60)

        except KeyboardInterrupt:
            print("\n🛑 监控已停止")
        except Exception as e:
            print(f"\n❌ 监控出错: {e}")


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description = os.getenv("COVERAGE_MONITOR_DESCRIPTION_253"))
    parser.add_argument(
        "--continuous",
        action = os.getenv("COVERAGE_MONITOR_ACTION_254"),
        help = os.getenv("COVERAGE_MONITOR_HELP_255")
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=60,
        help = os.getenv("COVERAGE_MONITOR_HELP_258")
    )
    parser.add_argument(
        "--data-file",
        default="coverage_data.json",
        help = os.getenv("COVERAGE_MONITOR_HELP_263")
    )

    args = parser.parse_args()

    monitor = CoverageMonitor(args.data_file)

    if args.continuous:
        monitor.continuous_monitor(args.interval)
    else:
        success = monitor.monitor()
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()