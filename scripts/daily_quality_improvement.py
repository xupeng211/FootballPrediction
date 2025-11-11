#!/usr/bin/env python3
"""每日代码质量改进执行脚本"""

import json
import subprocess
import sys
from datetime import datetime


def load_daily_target(target_minutes=60):
    """加载每日任务目标"""
    try:
        with open('quality_plan.json') as f:
            plan_data = json.load(f)

        tasks = plan_data['plan']
        # 按优先级排序
        priority_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
        tasks.sort(key=lambda x: (priority_order.get(x['priority'], 99), x['estimated_time']))

        # 选择今天的任务
        daily_tasks = []
        total_time = 0

        for task in tasks:
            if total_time + task['estimated_time'] <= target_minutes:
                daily_tasks.append(task)
                total_time += task['estimated_time']

        return daily_tasks
    except Exception:
        return []

def execute_task(task):
    """执行单个质量改进任务"""

    # 使用智能修复工具
    try:
        result = subprocess.run([
            'python3', 'scripts/code_quality_fixer.py',
            '--file', task['file_path'],
            '--category', task['category']
        ], capture_output=True, text=True, timeout=task['estimated_time']*60)

        if result.returncode == 0:
            return True
        else:
            return False
    except subprocess.TimeoutExpired:
        return False
    except Exception:
        return False

def main():
    target_minutes = int(sys.argv[1]) if len(sys.argv) > 1 else 60


    daily_tasks = load_daily_target(target_minutes)

    if not daily_tasks:
        return


    completed_tasks = 0
    for task in daily_tasks:
        if execute_task(task):
            completed_tasks += 1


    # 更新执行记录
    record = {
        'date': datetime.now().strftime('%Y-%m-%d'),
        'target_minutes': target_minutes,
        'total_tasks': len(daily_tasks),
        'completed_tasks': completed_tasks,
        'completion_rate': completed_tasks/len(daily_tasks)*100
    }

    with open('quality_improvement_log.json', 'a') as f:
        f.write(json.dumps(record) + '\n')

if __name__ == '__main__':
    main()
