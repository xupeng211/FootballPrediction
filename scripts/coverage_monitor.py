#!/usr/bin/env python3
"""
测试覆盖率监控工具
跟踪覆盖率变化趋势，提供持续改进反馈
"""

import sys
import os
import json
import datetime
from pathlib import Path
from typing import Dict, List, Any
import subprocess

# 添加项目根路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / 'src'))

class CoverageMonitor:
    """覆盖率监控器"""

    def __init__(self):
        self.project_root = project_root
        self.data_file = project_root / 'coverage_data.json'
        self.load_historical_data()

    def load_historical_data(self):
        """加载历史数据"""
        if self.data_file.exists():
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    self.historical_data = json.load(f)
            except:
                self.historical_data = []
        else:
            self.historical_data = []

    def save_historical_data(self):
        """保存历史数据"""
        with open(self.data_file, 'w', encoding='utf-8') as f:
            json.dump(self.historical_data, f, indent=2, ensure_ascii=False)

    def measure_current_coverage(self):
        """测量当前覆盖率"""
        coverage_data = {
            'timestamp': datetime.datetime.now().isoformat(),
            'date': datetime.datetime.now().strftime('%Y-%m-%d'),
            'phase': self.detect_current_phase(),
        }

        # 运行真实覆盖率测量
        try:
            result = subprocess.run([
                sys.executable, 'tests/real_coverage_measurement.py'
            ], capture_output=True, text=True, cwd=self.project_root, timeout=60)

            if result.returncode == 0:
                # 解析覆盖率数据
                lines = result.stdout.split('\n')
                for line in lines:
                    if '综合覆盖率:' in line:
                        coverage_str = line.split(':')[-1].strip().rstrip('%')
                        try:
                            coverage_data['overall_coverage'] = float(coverage_str)
                        except ValueError:
                            coverage_data['overall_coverage'] = 0.0
                    elif '函数覆盖率:' in line:
                        func_cov_str = line.split(':')[-1].strip().rstrip('%')
                        try:
                            coverage_data['function_coverage'] = float(func_cov_str)
                        except ValueError:
                            coverage_data['function_coverage'] = 0.0
                    elif '类覆盖率:' in line:
                        class_cov_str = line.split(':')[-1].strip().rstrip('%')
                        try:
                            coverage_data['class_coverage'] = float(class_cov_str)
                        except ValueError:
                            coverage_data['class_coverage'] = 0.0
                    elif '模块导入成功率:' in line:
                        import_str = line.split(':')[-1].strip().rstrip('%')
                        try:
                            coverage_data['import_success_rate'] = float(import_str)
                        except ValueError:
                            coverage_data['import_success_rate'] = 0.0
            else:
                coverage_data['error'] = '覆盖率测量失败'

        except Exception as e:
            coverage_data['error'] = str(e)

        return coverage_data

    def detect_current_phase(self):
        """检测当前阶段"""
        # 基于覆盖率数据判断当前阶段
        if not self.historical_data:
            return 'Phase 0: 初始化'

        latest_data = self.historical_data[-1]
        coverage = latest_data.get('overall_coverage', 0)

        if coverage < 5:
            return 'Phase 1: 基础模块全覆盖'
        elif coverage < 15:
            return 'Phase 2: 服务层核心测试'
        elif coverage < 35:
            return 'Phase 3: API和集成测试'
        elif coverage < 60:
            return 'Phase 4: 全覆盖体系'
        else:
            return 'Phase 5: 维护和优化'

    def quick_status_check(self):
        """快速状态检查"""
        coverage = self.measure_current_coverage()
        self.add_measurement(coverage)

        print(f"📊 快速状态检查:")
        print(f"   覆盖率: {coverage.get('overall_coverage', 0):.1f}%")
        print(f"   阶段: {coverage['phase']}")

        if 'error' in coverage:
            print(f"   ⚠️  错误: {coverage['error']}")

        return coverage

    def add_measurement(self, coverage_data):
        """添加新的测量数据"""
        self.historical_data.append(coverage_data)

        # 保持最近30天的数据
        cutoff_date = datetime.datetime.now() - datetime.timedelta(days=30)
        self.historical_data = [
            data for data in self.historical_data
            if datetime.datetime.fromisoformat(data['timestamp']) > cutoff_date
        ]

        self.save_historical_data()


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='测试覆盖率监控工具')
    parser.add_argument('--quick', action='store_true', help='快速状态检查')

    args = parser.parse_args()

    monitor = CoverageMonitor()

    if args.quick:
        monitor.quick_status_check()
    else:
        # 默认进行快速检查
        monitor.quick_status_check()


if __name__ == "__main__":
    main()