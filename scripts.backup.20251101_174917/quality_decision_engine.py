#!/usr/bin/env python3
"""
质量改进决策引擎
Quality Improvement Decision Engine

基于最佳实践路径生成具体的质量改进行动计划
"""

import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Tuple


class QualityDecisionEngine:
    """质量改进决策引擎"""

    def __init__(self, project_root: str = None):
        self.project_root = Path(project_root or Path(__file__).parent.parent)
        self.current_assessment = self.assess_current_state()

    def assess_current_state(self) -> Dict[str, Any]:
        """评估当前状态"""
        try:
            # 获取Ruff错误统计
            result = subprocess.run(
                ["make", "lint"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=120
            )

            error_counts = {}
            total_errors = 0

            for line in result.stdout.split('\n'):
                if ':' in line:
                    import re
                    error_code_match = re.search(r'\b([A-Z]\d{3})\b', line)
                    if error_code_match:
                        error_code = error_code_match.group(1)
                        error_counts[error_code] = error_counts.get(error_code, 0) + 1
                        total_errors += 1

            return {
                "total_errors": total_errors,
                "error_counts": error_counts,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            return {
                "total_errors": -1,
                "error_counts": {},
                "error": str(e)
            }

    def calculate_priority_score(self, error_type: str, count: int) -> float:
        """计算问题优先级评分"""
        priority_matrix = {
            "E999": 100,  # 语法错误 - 最高优先级
            "F821": 90,   # 未定义名称 - 高优先级
            "F401": 70,   # 未使用导入 - 中高优先级
            "E402": 60,   # 模块导入位置 - 中等优先级
            "F841": 50,   # 未使用变量 - 中等优先级
            "E501": 40,   # 行长度超限 - 低中等优先级
            "E302": 30,   # 空行格式 - 低优先级
            "F405": 35,   # star import问题 - 低中等优先级
            "default": 25
        }

        base_score = priority_matrix.get(error_type, priority_matrix["default"])

        # 根据数量调整评分
        if count > 1000:
            multiplier = 1.5
        elif count > 100:
            multiplier = 1.2
        else:
            multiplier = 1.0

        return base_score * multiplier

    def generate_action_plan(self) -> Dict[str, Any]:
        """生成行动计划"""
        print("🎯 生成质量改进行动计划...")

        error_counts = self.current_assessment["error_counts"]

        # 计算优先级
        prioritized_issues = []
        for error_type, count in error_counts.items():
            score = self.calculate_priority_score(error_type, count)
            prioritized_issues.append({
                "type": error_type,
                "count": count,
                "priority_score": score
            })

        prioritized_issues.sort(key=lambda x: x["priority_score"], reverse=True)

        # 生成行动计划
        action_plan = {
            "assessment": self.current_assessment,
            "prioritized_issues": prioritized_issues,
            "phases": []
        }

        # Phase 1: 紧急修复
        phase1_tasks = []
        if "E999" in error_counts:
            phase1_tasks.append({
                "task": "修复E999语法错误",
                "count": error_counts["E999"],
                "priority": "CRITICAL",
                "method": "manual_fix",
                "estimated_time": "2-4小时",
                "impact": "恢复代码可解析性",
                "tool": "IDE + 手动修复"
            })

        # Phase 2: 核心问题处理
        phase2_tasks = []
        if "F821" in error_counts:
            phase2_tasks.append({
                "task": "批量处理F821未定义名称错误",
                "count": error_counts["F821"],
                "priority": "HIGH",
                "method": "batch_processing",
                "estimated_time": "1-2天",
                "impact": "恢复代码可执行性",
                "tool": "自定义批量修复脚本"
            })

        # Phase 3: 质量提升
        phase3_tasks = []
        if "F841" in error_counts:
            phase3_tasks.append({
                "task": "处理F841未使用变量",
                "count": error_counts["F841"],
                "priority": "MEDIUM",
                "method": "automated_cleanup",
                "estimated_time": "4-6小时",
                "impact": "代码整洁性",
                "tool": "自动化清理脚本"
            })

        if "F401" in error_counts and error_counts["F401"] > 10:
            phase3_tasks.append({
                "task": "完成F401未使用导入清理",
                "count": error_counts["F401"],
                "priority": "MEDIUM",
                "method": "batch_cleanup",
                "estimated_time": "1-2小时",
                "impact": "导入整洁性",
                "tool": "现有批量修复脚本"
            })

        action_plan["phases"] = [
            {
                "phase": 1,
                "name": "紧急修复 - 恢复可执行性",
                "priority": "CRITICAL",
                "estimated_time": "1-2天",
                "tasks": phase1_tasks,
                "success_criteria": [
                    "E999错误 = 0",
                    "代码可正常解析",
                    "基础功能可运行"
                ]
            },
            {
                "phase": 2,
                "name": "核心问题处理 - F821批量修复",
                "priority": "HIGH",
                "estimated_time": "3-5天",
                "tasks": phase2_tasks,
                "success_criteria": [
                    "F821错误减少70%以上",
                    "主要模块可正常导入",
                    "质量门禁状态改善"
                ]
            },
            {
                "phase": 3,
                "name": "质量提升 - 达到可接受标准",
                "priority": "MEDIUM",
                "estimated_time": "1周",
                "tasks": phase3_tasks,
                "success_criteria": [
                    "通过质量门禁检查",
                    "总错误数 < 8000",
                    "代码质量显著提升"
                ]
            }
        ]

        return action_plan

    def recommend_next_actions(self) -> List[Dict[str, Any]]:
        """推荐下一步行动"""
        self.generate_action_plan()

        recommendations = []

        # 基于当前状态推荐立即行动
        current_errors = self.current_assessment["total_errors"]

        if current_errors > 12000:
            recommendations.append({
                "action": "立即启动紧急修复",
                "reason": "错误数量过多，影响项目健康度",
                "priority": "URGENT",
                "phase": 1
            })
        elif current_errors > 8000:
            recommendations.append({
                "action": "启动批量修复计划",
                "reason": "需要系统性处理大量错误",
                "priority": "HIGH",
                "phase": 1
            })
        else:
            recommendations.append({
                "action": "按计划逐步改进",
                "reason": "项目状态可控，按计划执行",
                "priority": "NORMAL",
                "phase": 1
            })

        # 添加基于具体错误的推荐
        error_counts = self.current_assessment["error_counts"]

        if error_counts.get("E999", 0) > 0:
            recommendations.insert(0, {
                "action": "优先修复语法错误",
                "reason": "语法错误阻止代码运行",
                "priority": "CRITICAL",
                "phase": 1
            })

        if error_counts.get("F821", 0) > 5000:
            recommendations.append({
                "action": "制定F821批量修复策略",
                "reason": "大量未定义名称错误需要系统处理",
                "priority": "HIGH",
                "phase": 2
            })

        return recommendations

    def generate_implementation_script(self, phase: int = 1) -> str:
        """生成实施脚本"""
        if phase == 1:
            return f'''#!/bin/bash
# Phase 1: 紧急修复实施脚本
# 生成时间: {datetime.now().isoformat()}

echo "🚀 开始Phase 1: 紧急修复..."

# 1. 备份当前状态
echo "📋 创建当前状态备份..."
git checkout -b emergency-fix-backup
git add -A
git commit -m "Emergency fix backup - $(date)"

# 2. 修复E999语法错误
echo "🔧 修复E999语法错误..."
# 这里可以添加具体的语法错误修复命令

# 3. 验证修复效果
echo "✅ 验证修复效果..."
make lint
python3 scripts/quality_gate_validator.py

# 4. 生成修复报告
echo "📊 生成修复报告..."
python3 scripts/quality_monitor_dashboard.py > phase1_report.txt

echo "🎉 Phase 1 完成！请检查 phase1_report.txt 了解结果"
'''
        else:
            return f"# Phase {phase} 实施脚本需要根据具体需求生成"

    def save_decision_report(self) -> str:
        """保存决策报告"""
        action_plan = self.generate_action_plan()
        recommendations = self.recommend_next_actions()

        report = {
            "timestamp": datetime.now().isoformat(),
            "assessment": self.current_assessment,
            "action_plan": action_plan,
            "recommendations": recommendations,
            "decision_rationale": self._get_decision_rationale()
        }

        report_file = self.project_root / "quality_decision_report.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        return str(report_file)

    def _get_decision_rationale(self) -> Dict[str, str]:
        """获取决策理由"""
        return {
            "strategy": "风险优先级的渐进式改进",
            "principles": [
                "优先解决影响代码可执行性的问题",
                "使用批量处理提高效率",
                "建立可验证的阶段性目标",
                "持续监控和反馈"
            ],
            "expected_outcomes": [
                "恢复代码可执行性",
                "显著减少关键错误类型",
                "建立可持续的质量改进机制"
            ]
        }

    def display_decision_summary(self):
        """显示决策摘要"""
        print("\n" + "="*70)
        print("🎯 质量改进决策摘要")
        print("="*70)

        print(f"📅 评估时间: {self.current_assessment['timestamp']}")
        print(f"📊 总错误数: {self.current_assessment['total_errors']:,}")

        print("\n🔍 当前主要问题:")
        error_counts = self.current_assessment["error_counts"]
        for i, (error_type, count) in enumerate(sorted(error_counts.items(), key=lambda x: x[1], reverse=True)[:5]):
            print(f"   {i+1}. {error_type}: {count:,} 个")

        recommendations = self.recommend_next_actions()
        print(f"\n🎯 推荐行动 ({len(recommendations)}项):")
        for i, rec in enumerate(recommendations[:3], 1):
            print(f"   {i}. [{rec['priority']}] {rec['action']}")
            print(f"      原因: {rec['reason']}")

        action_plan = self.generate_action_plan()
        print(f"\n📋 改进计划: {len(action_plan['phases'])}个阶段")
        for phase in action_plan['phases']:
            print(f"   Phase {phase['phase']}: {phase['name']}")
            print(f"      优先级: {phase['priority']}")
            print(f"      预估时间: {phase['estimated_time']}")
            print(f"      任务数: {len(phase['tasks'])}")

        print("\n💡 决策理由:")
        rationale = self._get_decision_rationale()
        print(f"   策略: {rationale['strategy']}")
        print(f"   原则: {rationale['principles'][0]}")
        print(f"   预期: {rationale['expected_outcomes'][0]}")

        print("="*70)
        print("📝 详细报告已保存到: quality_decision_report.json")
        print("="*70)


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="质量改进决策引擎")
    parser.add_argument("--project-root", type=str, help="项目根目录路径")
    parser.add_argument("--generate-script", type=int, choices=[1, 2, 3],
                       help="生成指定阶段的实施脚本")

    args = parser.parse_args()

    # 创建决策引擎
    engine = QualityDecisionEngine(args.project_root)

    if args.generate_script:
        script_content = engine.generate_implementation_script(args.generate_script)
        script_file = f"phase_{args.generate_script}_implementation.sh"
        with open(script_file, 'w') as f:
            f.write(script_content)
        print(f"✅ {script_file} 已生成")
        return

    # 生成决策报告
    engine.save_decision_report()
    engine.display_decision_summary()


if __name__ == "__main__":
    main()