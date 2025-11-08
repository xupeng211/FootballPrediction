#!/usr/bin/env python3
"""
简化版GitHub Issues最佳实践分析器
Simplified GitHub Issues Best Practices Analyzer

分析当前M2规划，提供GitHub Issues拆分和管理建议
"""

import json
from datetime import datetime


def analyze_m2_planning():
    """分析M2规划"""
    print("📊 分析当前M2规划...")

    # 当前M2规划分析
    analysis = {
        "phases": 4,
        "current_tasks_per_phase": 3,
        "total_current_tasks": 12,
        "granularity": "COARSE - 需要细化",
        "issues": []
    }

    # 分析每个阶段
    for phase_num in range(1, 5):
        phase_issues = {
            "phase": f"M2-Phase {phase_num}",
            "target_coverage": [15, 25, 35, 50][phase_num-1],
            "current_tasks": 3,
            "recommended_breakdown": 5-8,
            "issues": []
        }

        # 阶段1的具体Issue
        if phase_num == 1:
            phase1_issues = [
                "[M2-P1-01] 扩展core.di模块依赖注入测试",
                "[M2-P1-02] 完善core.config_di配置管理测试",
                "[M2-P1-03] 优化core.service_lifecycle生命周期测试",
                "[M2-P1-04] 扩展core.auto_binding自动绑定测试",
                "[M2-P1-05] 完善测试工具链和报告自动化"
            ]
        # 阶段2的具体Issue
        elif phase_num == 2:
            phase2_issues = [
                "[M2-P2-01] 实现api.auth认证系统测试",
                "[M2-P2-02] 建立api.predictions预测服务测试",
                "[M2-P2-03] 实现API集成测试套件",
                "[M2-P2-04] 建立Mock数据和服务系统",
                "[M2-P2-05] 完善API文档和测试报告"
            ]
        # 阶段3和4的基础Issue（简化版）
        else:
            phase3_issues = [
                f"[M2-P{phase_num}-01] 数据库操作测试",
                f"[M2-P{phase_num}-02] 数据模型验证测试",
                f"[M2-P{phase_num}-03] 业务规则测试",
                f"[M2-P{phase_num}-04] ML模型测试",
                f"[M2-P{phase_num}-05] 集成测试完善"
            ]

        phase_issues["issues"] = phase1_issues if phase_num == 1 else (phase2_issues if phase_num == 2 else phase3_issues)
        analysis["issues"].append(phase_issues)

    return analysis

def define_best_practices():
    """定义最佳实践"""
    print("📋 定义GitHub Issues最佳实践...")

    principles = [
        {
            "name": "单一职责",
            "description": "每个Issue只解决一个具体问题",
            "good": "为core.di模块添加依赖注入测试",
            "bad": "完善所有core模块的测试"
        },
        {
            "name": "具体可执行",
            "description": "Issue描述必须包含具体信息",
            "good": "为core.di.py第45-80行添加5个测试用例",
            "bad": "改进DI容器测试"
        },
        {
            "name": "明确验收标准",
            "description": "每个Issue都有明确的完成标准",
            "good": "覆盖率提升至少5%，所有测试通过",
            "bad": "完成相关测试"
        },
        {
            "name": "可估算工作量",
            "description": "工作量应该在1-3天内完成",
            "good": "预计1-2天，包含编写、运行、调试",
            "bad": "改进测试质量（工作量未知）"
        }
    ]
    return principles

def create_issue_recommendations():
    """创建Issue推荐"""
    print("💡 创建Issue推荐...")

    recommendations = [
        {
            "category": "任务拆分",
            "recommendation": "将12个大任务拆分为25-30个具体Issue",
            "details": [
                "按模块细分（每个模块1-2个Issue）",
                "按功能细分（单元测试、集成测试、Mock测试）",
                "按复杂度细分（简单、复杂、边界条件）"
            ]
        },
        {
            "category": "模板标准化",
            "recommendation": "使用标准化的Issue模板",
            "details": [
                "统一标题格式：[M2-P1-XX] 具体功能描述",
                "统一描述格式：背景、任务、验收标准、验证方式",
                "统一标签系统：阶段、优先级、模块、类型"
            ]
        },
        {
            "category": "依赖管理",
            "recommendation": "建立清晰的依赖关系管理",
            "details": [
                "使用GitHub Milestone组织相关Issue",
                "使用项目板可视化进度",
                "设置Issue依赖关系"
            ]
        }
    ]
    return recommendations

def create_management_strategy():
    """创建管理策略"""
    print("🗂️ 创建管理策略...")

    strategy = {
        "milestone": {
            "name": "M2: 50% Coverage Target",
            "due_date": "2025-12-01",
            "issues_count": 25
        },
        "labels": {
            "phases": ["M2-P1", "M2-P2", "M2-P3", "M2-P4"],
            "priorities": ["critical", "high", "medium"],
            "modules": ["core", "api", "database", "domain", "ml"],
            "types": ["testing", "integration", "mock", "tools"]
        },
        "workflow": {
            "creation": "使用模板创建Issue",
            "assignment": "分配给负责人",
            "review": "代码审查",
            "tracking": "项目板跟踪"
        }
    }
    return strategy

def generate_report():
    """生成分析报告"""
    print("📄 生成分析报告...")

    analysis = analyze_m2_planning()
    principles = define_best_practices()
    recommendations = create_issue_recommendations()
    strategy = create_management_strategy()

    report = f"""# GitHub Issues最佳实践分析报告

**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 📊 当前M2规划分析

### 粒度评估
- **当前规划**: {analysis['phases']}个阶段，{analysis['total_current_tasks']}个任务
- **粒度评估**: {analysis['granularity']}
- **建议拆分**: 每个阶段5-8个Issue
- **总计Issue**: {sum(len(phase['issues']) for phase in analysis['issues'])}个具体Issue

### 主要问题
1. **任务过于宽泛**: 缺乏具体执行步骤
2. **验收标准不明确**: 缺少量化标准
3. **工作量难估算**: 无法准确预估时间
4. **依赖关系模糊**: 缺乏清晰依赖管理

## 📋 GitHub Issues最佳实践原则

### 1. 单一职责原则
- **✅ 好**: 为core.di模块添加依赖注入测试
- **❌ 差**: 完善所有core模块的测试

### 2. 具体可执行原则
- **✅ 好**: 为core.di.py第45-80行添加5个测试用例
- **❌ 差**: 改进DI容器测试

### 3. 明确验收标准原则
- **✅ 好**: 覆盖率提升至少5%，所有测试通过
- **❌ 差**: 完成相关测试

### 4. 可估算工作量原则
- **✅ 好**: 预计1-2天，包含编写、运行、调试
- **❌ 差**: 改进测试质量（工作量未知）

## 🔧 推荐的Issue拆分方案

### 阶段1: 基础覆盖率扩展 (目标15%)
"""

    for i, issue in enumerate(analysis['issues'][0]['issues'], 1):
        report += f"{i}. {issue}\n"

    report += """
### 阶段2: API层覆盖率提升 (目标25%)
"""

    for i, issue in enumerate(analysis['issues'][1]['issues'], 6):
        report += f"{i}. {issue}\n"

    report += """
### 阶段3: 数据层覆盖率攻坚 (目标35%)
"""

    for i, issue in enumerate(analysis['issues'][2]['issues'], 11):
        report += f"{i}. {issue}\n"

    report += """
### 阶段4: 业务逻辑层覆盖 (目标50%)
"""

    for i, issue in enumerate(analysis['issues'][3]['issues'], 16):
        report += f"{i}. {issue}\n"

    report += f"""
## 🗂️ Issues管理策略

### Milestone设置
- **名称**: {strategy['milestone']['name']}
- **截止日期**: {strategy['milestone']['due_date']}
- **包含Issue**: {strategy['milestone']['issues_count']}个

### 标签系统
- **阶段标签**: {', '.join(strategy['labels']['phases'])}
- **优先级标签**: {', '.join(strategy['labels']['priorities'])}
- **模块标签**: {', '.join(strategy['labels']['modules'])}
- **类型标签**: {', '.join(strategy['labels']['types'])}

## 💡 实施建议

### 立即行动
1. **拆分任务**: 将大任务拆分为具体的小Issue
2. **创建Milestone**: 在GitHub设置M2 Milestone
3. **使用模板**: 创建标准化Issue模板
4. **培训团队**: 培训团队使用新的Issue流程

### 最佳实践
1. **Issue创建**: 使用模板确保信息完整
2. **工作量估算**: 1-3天内可完成的任务
3. **验收标准**: 必须包含量化的完成条件
4. **依赖管理**: 清晰的依赖关系

## 🎯 预期效果

### 工作效率提升
- **明确性**: 每个Issue都有清晰的任务描述
- **可执行性**: 任务描述具体，可以直接执行
- **可追踪性**: 进度和质量可实时监控

### 质量保障
- **质量门控**: 每个Issue都有质量检查点
- **自动化验证**: 完成结果可自动验证
- **持续监控**: 覆盖率变化实时跟踪

---

## 📝 Issue模板示例

```markdown
## 任务描述
**Issue类型**: 测试开发
**预估工时**: 16小时
**优先级**: high

### 背景
为提升core.di模块的测试覆盖率，需要添加依赖注入相关的测试用例。

### 具体任务
1. 为DIContainer类添加单例模式测试
2. 为ServiceDescriptor添加序列化测试
3. 为依赖注入解析添加边界条件测试
4. 为循环依赖添加检测测试

### 验收标准
- [ ] 新增测试≥15个
- [ ] core.di模块覆盖率≥50%
- [ ] 所有测试通过

### 验证方式
```bash
# 运行测试
pytest tests/unit/test_core_di.py -v

# 检查覆盖率
pytest --cov=src.core.di --cov-report=term-missing
```

### 依赖关系
- 前置Issue: 无
- 后续Issue: #123

### 标签
M2-P1, core, testing, dependency-injection
```

---

**报告版本**: v1.0
**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

    return report

def main():
    """主函数"""
    print("🚀 启动GitHub Issues最佳实践分析器...")

    # 执行分析
    report = generate_report()

    # 保存报告
    with open("github_issues_best_practices_report.md", "w", encoding="utf-8") as f:
        f.write(report)

    # 保存分析数据
    analysis = analyze_m2_planning()
    recommendations = create_issue_recommendations()
    strategy = create_management_strategy()

    data = {
        "generated_at": datetime.now().isoformat(),
        "analysis": analysis,
        "recommendations": recommendations,
        "strategy": strategy
    }

    with open("github_issues_analysis_data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)

    print("\\n🎉 GitHub Issues最佳实践分析完成!")
    print(f"   当前规划: {analysis['phases']}个阶段")
    print(f"   任务数量: {analysis['total_current_tasks']}个")
    print(f"   粒度评估: {analysis['granularity']}")
    print(f"   推荐Issue: {sum(len(phase['issues']) for phase in analysis['issues'])}个")
    print("\\n📄 报告已保存:")
    print("   - github_issues_best_practices_report.md")
    print("   - github_issues_analysis_data.json")

if __name__ == "__main__":
    main()
