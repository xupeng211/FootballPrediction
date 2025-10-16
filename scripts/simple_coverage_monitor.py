#!/usr/bin/env python3
"""简化的覆盖率监控"""

import json
from pathlib import Path
from datetime import datetime

def save_coverage_data():
    """保存覆盖率数据"""

    # 运行测试获取覆盖率
    import subprocess
    result = subprocess.run(
        ["python", "-m", "pytest", "tests/unit/utils/test_helpers.py",
         "tests/unit/utils/test_predictions_tdd.py",
         "--cov=src.utils", "--cov-report=json", "--tb=no", "-q"],
        capture_output=True,
        text=True
    )

    # 解析覆盖率报告
    coverage_file = Path("coverage.json")
    if coverage_file.exists():
        with open(coverage_file) as f:
            data = json.load(f)

        # 创建记录
        record = {
            'timestamp': datetime.now().isoformat(),
            'coverage': {
                'helpers': data['files'].get('src/utils/helpers.py', {}).get('summary', {}).get('percent_covered', 0),
                'predictions': data['files'].get('src/utils/predictions.py', {}).get('summary', {}).get('percent_covered', 0),
                'string_utils': data['files'].get('src/utils/string_utils.py', {}).get('summary', {}).get('percent_covered', 0),
                'total': data['totals']['percent_covered']
            }
        }

        # 保存到历史
        history_file = Path("coverage_history.json")
        history = []
        if history_file.exists():
            with open(history_file) as f:
                history = json.load(f)

        history.append(record)
        history = history[-7:]  # 保留7天

        with open(history_file, 'w') as f:
            json.dump(history, f, indent=2)

        # 打印结果
        print(f"覆盖率: {record['coverage']['total']:.1f}%")
        print(f"  helpers: {record['coverage']['helpers']:.1f}%")
        print(f"  predictions: {record['coverage']['predictions']:.1f}%")
        print(f"  string_utils: {record['coverage']['string_utils']:.1f}%")

        # 计算趋势
        if len(history) > 1:
            prev = history[-2]['coverage']['total']
            curr = history[-1]['coverage']['total']
            change = curr - prev
            trend = "📈" if change > 0 else "📉" if change < 0 else "➡️"
            print(f"变化: {trend} {change:+.1f}%")

            if curr >= 50:
                print("✅ 优秀！覆盖率已达标")
            elif curr >= 30:
                print("💡 良好！继续努力")
            else:
                print("⚠️ 需要提升覆盖率")

if __name__ == "__main__":
    save_coverage_data()
