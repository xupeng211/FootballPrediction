#!/usr/bin/env python3
"""
GitHub Issues最佳实践分析和拆分方案
GitHub Issues Best Practices Analysis and Breakdown Strategy

分析当前M2规划的任务粒度，提供符合最佳实践的GitHub Issues管理方案
"""

import json
from datetime import datetime


class GitHubIssuesBestPracticesAnalyzer:
    """GitHub Issues最佳实践分析器"""

    def __init__(self):
        self.analysis_results = {
            "current_planning_analysis": {},
            "best_principles": [],
            "recommendations": [],
            "issue_breakdown": [],
            "management_strategy": {},
            "tools_and_templates": []
        }

    def analyze_current_m2_planning(self):
        """分析当前M2规划的任务粒度"""

        current_analysis = {
            "phases_count": 4,
            "total_weeks": 4,
            "tasks_per_phase": 3,
            "total_high_level_tasks": 12,
            "granularity_assessment": "COARSE - 需要细化",
            "issues": []
        }

        # 分析每个阶段的粒度
        for phase_num in range(1, 5):
            phase_issues = {
                "phase": f"M2-Phase {phase_num}",
                "current_tasks": 3,
                "estimated_effort": "1周",
                "granularity_issues": [
                    "任务过于宽泛，缺乏具体的执行步骤",
                    "没有明确的验收标准",
                    "缺乏具体的模块和文件列表",
                    "没有预估的具体测试数量",
                    "缺乏依赖关系和前后置条件"
                ],
                "recommended_breakdown": 5-8  # 建议拆分数量
            }
            current_analysis["issues"].append(phase_issues)

        self.analysis_results["current_planning_analysis"] = current_analysis
        return current_analysis

    def define_best_principles(self):
        """定义GitHub Issues最佳实践原则"""

        principles = [
            {
                "principle": "单一职责原则",
                "description": "每个Issue应该只解决一个具体问题或完成一个特定功能",
                "examples": [
                    "✅ '为core.di模块添加依赖注入容错测试'",
                    "❌ '完善所有core模块的测试'"
                ]
            },
            {
                "principle": "具体可执行原则",
                "description": "Issue描述必须包含足够的具体信息，让人可以直接执行",
                "examples": [
                    "✅ '为core.di.py第45-80行的DIContainer类添加5个测试用例，覆盖单例、作用域、瞬态三种生命周期'",
                    "❌ '改进DI容器测试'"
                ]
            },
            {
                "principle": "明确验收标准原则",
                "description": "每个Issue必须有明确的完成标准和验收条件",
                "examples": [
                    "✅ '验收标准：所有新测试通过，覆盖率提升至少5%，CI/CD成功运行'",
                    "❌ '完成相关测试'"
                ]
            },
            {
                "principle": "可估算工作量原则",
                "description": "Issue的工作量应该可以在1-3天内完成，便于排期和跟踪",
                "examples": [
                    "✅ '预计工作量：1-2天，包含测试编写、运行、调试'",
                    "❌ '改进测试质量（工作量未知）'"
                ]
            },
            {
                "principle": "依赖关系明确原则",
                "description": "Issue之间的依赖关系应该清晰，便于确定执行顺序",
                "examples": [
                    "✅ '依赖：#123完成后才能开始'",
                    "❌ '需要其他工作支持'"
                ]
            },
            {
                "principle": "可测试验证原则",
                "description": "Issue的完成结果应该是可以通过自动化方式验证的",
                "examples": [
                    "✅ '验证方式：pytest tests/unit/core/test_di.py::test_di_container_scoped -v'",
                    "❌ '手动测试验证功能'"
                ]
            }
        ]

        self.analysis_results["best_principles"] = principles
        return principles

    def create_recommendations(self):
        """创建改进建议"""

        recommendations = [
            {
                "category": "任务拆分策略",
                "recommendations": [
                    "将每个阶段的3个大任务拆分为5-8个小Issue",
                    "按模块和功能细分，每个Issue对应1-2个具体的测试文件",
                    "按照测试类型细分：单元测试、集成测试、Mock测试",
                    "按照复杂度细分：简单测试、复杂业务逻辑测试、边界条件测试"
                ]
            },
            {
                "category": "Issue模板标准化",
                "recommendations": [
                    "创建标准化的Issue模板，包含所有必要信息字段",
                    "统一标题格式：[M2-P1-XX] 功能描述",
                    "统一描述格式：背景、任务、验收标准、验证方式",
                    "统一标签系统：阶段、优先级、模块、类型"
                ]
            },
            {
                "category": "依赖关系管理",
                "recommendations": [
                    "使用Issue编号建立明确的依赖关系",
                    "创建里程碑(Milestone)来组织相关Issue",
                    "使用项目板(Board)来可视化进度",
                    "设置Issue依赖关系插件来自动化管理"
                ]
            },
            {
                "category": "质量控制",
                "recommendations": [
                    "每个Issue创建时必须包含验收标准",
                    "Issue完成后必须有代码审查",
                    "建立Issue质量检查清单",
                    "定期Review Issue进度和质量"
                ]
            }
        ]

        self.analysis_results["recommendations"] = recommendations
        return recommendations

    def create_detailed_issue_breakdown(self):
        """创建详细的Issue拆分方案"""

        breakdown = []

        # 阶段1拆分：基础覆盖率扩展 (目标15%)
        phase1_issues = [
            {
                "title": "[M2-P1-01] 扩展core.di模块依赖注入测试",
                "description": """## 背景
core.di模块当前覆盖率30%，需要扩展测试以提升到50%+

## 任务
1. 为DIContainer类添加单例模式测试
2. 为ServiceDescriptor添加序列化测试
3. 为依赖注入解析添加边界条件测试
4. 为循环依赖添加检测测试

## 验收标准
- 新增测试≥15个
- core.di模块覆盖率≥50%
- 所有测试通过""",
                "file": "src/core/di.py",
                "estimated_hours": 16,
                "priority": "high",
                "dependencies": [],
                "labels": ["M2-P1", "core", "testing", "dependency-injection"]
            },
            {
                "title": "[M2-P1-02] 完善core.config_di配置管理测试",
                "description": """## 背景
core.config_di模块当前覆盖率31%，需要扩展配置解析和验证测试

## 任务
1. 为ConfigurationBinder添加配置文件解析测试
2. 为DIConfiguration添加环境变量测试
3. 为配置验证添加边界条件测试
4. 为配置错误处理添加异常测试

## 验收标准
- 新增测试≥12个
- core.config_di模块覆盖率≥45%
- 配置错误处理覆盖完整""",
                "file": "src/core/config_di.py",
                "estimated_hours": 12,
                "priority": "high",
                "dependencies": [],
                "labels": ["M2-P1", "core", "testing", "configuration"]
            },
            {
                "title": "[M2-P1-03] 优化core.service_lifecycle生命周期测试",
                "description": """## 背景
core.service_lifecycle模块当前覆盖率26%，需要完善服务生命周期管理测试

## 任务
1. 为ServiceLifecycleManager添加服务注册/注销测试
2. 为服务状态监控添加状态变化测试
3. 为服务启动/停止添加异常处理测试
4. 为服务依赖关系添加依赖解析测试

## 验收标准
- 新增测试≥10个
- core.service_lifecycle模块覆盖率≥40%
- 生命周期管理功能测试完整""",
                "file": "src/core/service_lifecycle.py",
                "estimated_hours": 10,
                "priority": "medium",
                "dependencies": [],
                "labels": ["M2-P1", "core", "testing", "lifecycle"]
            },
            {
                "title": "[M2-P1-04] 扩展core.auto_binding自动绑定测试",
                "description": """## 背景
core.auto_binding模块当前覆盖率23%，需要扩展自动绑定功能测试

## 任务
1. 为AutoBinder添加绑定规则测试
2. 为约定绑定添加策略测试
3. 为自动扫描添加模块发现测试
4. 为绑定失败添加异常处理测试

## 验收标准
- 新增测试≥12个
- core.auto_binding模块覆盖率≥35%
- 自动绑定功能测试完整""",
                "file": "src/core/auto_binding.py",
                "estimated_hours": 12,
                "priority": "medium",
                "dependencies": [],
                "labels": ["M2-P1", "core", "testing", "auto-binding"]
            },
            {
                "title": "[M2-P1-05] 完善测试工具链和报告自动化",
                "description": """## 背景
当前测试工具链需要完善，提升测试执行和报告的自动化水平

## 任务
1. 完善coverage_analysis.py覆盖率分析功能
2. 优化测试报告生成和格式化
3. 添加测试执行时间监控
4. 集成测试结果到GitHub Actions

## 验收标准
- 测试工具链功能完整
- 覆盖率报告自动生成
- CI/CD集成成功运行""",
                "file": "scripts/",
                "estimated_hours": 8,
                "priority": "high",
                "dependencies": [],
                "labels": ["M2-P1", "tools", "automation", "ci-cd"]
            }
        ]

        # 阶段2拆分：API层覆盖率提升 (目标25%)
        phase2_issues = [
            {
                "title": "[M2-P2-01] 实现api.auth认证系统测试",
                "description": """## 背景
api.auth模块是API层的核心认证组件，需要建立完整的测试覆盖

## 任务
1. 为JWT令牌生成和验证添加测试
2. 为OAuth2授权码流程添加测试
3. 为权限检查和角色验证添加测试
4. 为认证异常处理添加测试

## 验收标准
- 新增测试≥15个
- api.auth模块覆盖率≥40%
- 认证流程端到端测试通过""",
                "file": "src/api/auth/",
                "estimated_hours": 16,
                "priority": "high",
                "dependencies": [],
                "labels": ["M2-P2", "api", "auth", "testing"]
            },
            {
                "title": "[M2-P2-02] 建立api.predictions预测服务测试",
                "description": """## 背景
api.predictions是核心的预测服务API，需要建立完整的测试体系

## 任务
1. 为预测请求验证添加测试
2. 为预测结果格式化添加测试
3. 为批量预测添加测试
4. 为预测错误处理添加测试

## 验收标准
- 新增测试≥12个
- api.predictions模块覆盖率≥35%
- 预测API功能测试完整""",
                "file": "src/api/predictions/",
                "estimated_hours": 12,
                "priority": "high",
                "dependencies": [],
                "labels": ["M2-P2", "api", "predictions", "testing"]
            },
            {
                "title": "[M2-P2-03] 实现API集成测试套件",
                "description": """## 背景
API层需要集成测试来验证组件间的交互和数据流

## 任务
1. 创建认证到预测的集成测试
2. 创建API到数据库的集成测试
3. 创建API错误处理的集成测试
4. 创建API性能基准测试

## 验收标准
- 新增集成测试≥10个
- API集成测试通过率≥90%
- 集成测试覆盖主要业务流程""",
                "file": "tests/integration/",
                "estimated_hours": 14,
                "priority": "medium",
                "dependencies": ["M2-P2-01", "M2-P2-02"],
                "labels": ["M2-P2", "api", "integration", "testing"]
            },
            {
                "title": "[M2-P2-04] 建立Mock数据和服务系统",
                "description": """## 背景
测试需要可靠的Mock数据和服务来隔离依赖

## 任务
1. 创建用户认证Mock服务
2. 创建预测模型Mock服务
3. 创建数据库Mock仓储
4. 创建API测试数据生成器

## 验收标准
- Mock系统功能完整
- Mock数据覆盖主要场景
- Mock服务稳定性测试通过""",
                "file": "tests/mocks/",
                "estimated_hours": 10,
                "priority": "high",
                "dependencies": [],
                "labels": ["M2-P2", "mock", "testing", "data"]
            },
            {
                "title": "[M2-P2-05] 完善API文档和测试报告",
                "description": """## 背景
API层需要完整的文档和测试报告支持

## 任务
1. 更新API文档覆盖测试场景
2. 创建API测试覆盖率报告
3. 建立API性能监控报告
4. 创建API安全测试报告

## 验收标准
- API文档完整性≥95%
- 测试报告自动化生成
- 监控报告准确可靠""",
                "file": "docs/",
                "estimated_hours": 8,
                "priority": "medium",
                "dependencies": [],
                "labels": ["M2-P2", "api", "documentation", "reporting"]
            }
        ]

        # 阶段3和4的详细拆分可以继续，但为了演示，我们先展示前两个阶段的拆分
        breakdown.extend(phase1_issues)
        breakdown.extend(phase2_issues)

        self.analysis_results["issue_breakdown"] = breakdown
        return breakdown

    def create_management_strategy(self):
        """创建Issues管理策略"""

        strategy = {
            "milestone_setup": {
                "name": "Milestone M2: 50% Coverage Target",
                "description": "Achieve 50% code coverage through systematic testing",
                "due_date": "2025-12-01",  # 4周后
                "issues_count": len(self.create_detailed_issue_breakdown())
            },
            "board_setup": {
                "columns": [
                    {"name": "Backlog", "status": "planned"},
                    {"name": "In Progress", "status": "in_progress"},
                    {"name": "Review", "status": "review"},
                    {"name": "Done", "status": "completed"}
                ]
            },
            "label_system": {
                "phases": ["M2-P1", "M2-P2", "M2-P3", "M2-P4"],
                "priorities": ["critical", "high", "medium", "low"],
                "modules": ["core", "api", "database", "domain", "ml", "services", "utils"],
                "types": ["testing", "integration", "mock", "documentation", "tools"],
                "status": ["planned", "in_progress", "review", "completed", "blocked"]
            },
            "workflow": {
                "creation": "创建Issue时必须使用模板，包含所有必要信息",
                "assignment": "Issue分配给具体负责人",
                "review": "每个Issue完成后需要代码审查",
                "closure": "满足验收标准后关闭Issue",
                "tracking": "使用项目板跟踪进度"
            },
            "quality_gates": {
                "creation": "Issue描述必须具体可执行",
                "estimation": "工作量必须可估算（1-3天）",
                "acceptance": "必须包含明确的验收标准",
                "testing": "完成结果必须可自动化验证"
            }
        }

        self.analysis_results["management_strategy"] = strategy
        return strategy

    def create_templates_and_tools(self):
        """创建模板和工具"""

        # Issue模板
        issue_template = """## 任务描述
**Issue类型**: [测试开发/文档/工具/配置]
**预估工时**: X小时
**优先级**: [critical/high/medium/low]

### 背景
(简要说明为什么要做这个任务)

### 具体任务
1.
2.
3.

### 验收标准
- [ ] 新增测试≥X个
- [ ] 覆盖率达到X%
- [ ] 所有测试通过

### 验证方式
```bash
# 运行测试命令
pytest tests/unit/test_module.py -v

# 检查覆盖率
pytest --cov=module --cov-report=term-missing
```

### 依赖关系
- 前置Issue: #XXX
- 后续Issue: #XXX

### 备注
(任何需要注意的事项)

**标签**:
"""

        # Issue创建工具
        tools = [
            {
                "name": "issue_creator.py",
                "description": "Issue创建工具，基于模板快速创建标准化Issue",
                "features": ["模板选择", "自动编号", "依赖检查", "标签分配"]
            },
            {
                "name": "issue_tracker.py",
                "description": "Issue跟踪工具，监控Issue进度和质量",
                "features": ["进度监控", "质量检查", "报告生成"]
            },
            {
                "name": "coverage_monitor.py",
                "description": "覆盖率监控工具，实时跟踪覆盖率变化",
                "features": ["实时监控", "趋势分析", "预警通知"]
            }
        ]

        templates_and_tools = {
            "issue_template": issue_template,
            "tools": tools
        }

        self.analysis_results["tools_and_templates"] = templates_and_tools
        return templates_and_tools

    def generate_analysis_report(self):
        """生成分析报告"""
        report = f"""# GitHub Issues最佳实践分析报告

**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**分析范围**: M2规划任务粒度和拆分方案

## 📊 当前规划分析

### 粒度评估
- **当前规划**: 4个阶段，12个高层次任务
- **粒度评估**: COARSE - 需要细化
- **建议拆分**: 每个阶段拆分为5-8个小Issue
- **总计Issue**: {len(self.create_detailed_issue_breakdown())}个具体Issue

### 主要问题
1. **任务过于宽泛**: 缺乏具体的执行步骤
2. **验收标准不明确**: 缺乏量化的完成标准
3. **工作量难估算**: 无法准确预估时间和资源
4. **依赖关系模糊**: 缺乏清晰的依赖管理
5. **验证方式缺失**: 缺乏自动化验证手段

## 📋 GitHub Issues最佳实践原则

### 1. 单一职责原则
每个Issue应该只解决一个具体问题或完成一个特定功能

**示例**:
- ✅ "为core.di模块添加依赖注入容错测试"
- ❌ "完善所有core模块的测试"

### 2. 具体可执行原则
Issue描述必须包含足够的具体信息

**示例**:
- ✅ "为core.di.py第45-80行的DIContainer类添加5个测试用例"
- ❌ "改进DI容器测试"

### 3. 明确验收标准原则
每个Issue必须有明确的完成标准

**示例**:
- ✅ "验收标准：所有新测试通过，覆盖率提升至少5%"
- ❌ "完成相关测试"

### 4. 可估算工作量原则
Issue的工作量应该在1-3天内完成

**示例**:
- ✅ "预计工作量：1-2天，包含测试编写、运行、调试"
- ❌ "改进测试质量（工作量未知）"

## 🔧 推荐的拆分方案

### 阶段1：基础覆盖率扩展 (目标15%)
"""

        # 添加阶段1的详细拆分
        phase1_issues = [issue for issue in self.create_detailed_issue_breakdown() if "M2-P1" in issue["title"]]
        for i, issue in enumerate(phase1_issues, 1):
            report += f"{i}. {issue['title']}\n"

        report += """
### 阶段2：API层覆盖率提升 (目标25%)
"""

        phase2_issues = [issue for issue in self.create_detailed_issue_breakdown() if "M2-P2" in issue["title"]]
        for i, issue in enumerate(phase2_issues, 1):
            report += f"{i}. {issue['title']}\n"

        report += f"""
## 🗂️ Issues管理策略

### Milestone设置
- **名称**: {self.create_management_strategy()['milestone_setup']['name']}
- **截止日期**: {self.create_management_strategy()['milestone_setup']['due_date']}
- **包含Issue**: {len(self.create_detailed_issue_breakdown())}个具体Issue

### 项目板设置
- **列**: Backlog → In Progress → Review → Done
- **标签系统**: 阶段、优先级、模块、类型、状态

### 工作流程
1. **创建**: 使用标准化模板创建Issue
2. **分配**: 分配给具体负责人
3. **执行**: 按照计划执行任务
4. **审查**: 代码审查和质量检查
5. **关闭**: 满足验收标准后关闭

## 🛠️ 推荐的工具和模板

### Issue模板
创建了标准化的Issue模板，包含：
- 任务描述
- 具体任务列表
- 验收标准
- 验证方式
- 依赖关系
- 标签系统

### 管理工具
1. **Issue创建工具**: 基于模板快速创建Issue
2. **Issue跟踪工具**: 监控进度和质量
3. **覆盖率监控工具**: 实时跟踪覆盖率变化

## 📈 预期效果

### 工作效率提升
- **明确性**: 每个Issue都有明确的任务和验收标准
- **可执行性**: 任务描述具体，可以直接执行
- **可追踪性**: 进度和质量都可以实时跟踪

### 质量保障
- **质量门控**: 每个Issue都有质量检查点
- **自动化验证**: 完成结果可自动验证
- **持续监控**: 覆盖率变化实时监控

### 团队协作
- **标准化**: 统一的Issue模板和工作流程
- **透明化**: 进度和状态对所有团队成员可见
- **可扩展**: 基于模板可快速创建新Issue

## 🎯 实施建议

### 立即行动
1. **拆分现有任务**: 将大任务拆分为具体的小Issue
2. **创建Milestone**: 设置M2目标Milestone
3. **设置项目板**: 创建GitHub项目板
4. **培训团队**: 培训团队使用新的Issue模板

### 持续改进
1. **定期Review**: 定期Review Issue质量和进度
2. **模板优化**: 根据使用情况优化模板
3. **工具完善**: 根据需要完善管理工具
4. **最佳实践**: 总结和分享最佳实践

---

**报告版本**: v1.0
**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**分析工具**: GitHub Issues Best Practices Analyzer
"""

        return report

    def main(self):
        """主函数"""

        # 执行分析
        current_analysis = self.analyze_current_m2_planning()
        principles = self.define_best_principles()
        self.create_recommendations()
        breakdown = self.create_detailed_issue_breakdown()
        self.create_management_strategy()
        self.create_templates_and_tools()

        # 生成报告
        report = self.generate_analysis_report()

        # 保存结果
        self.analysis_results.update({
            "generated_at": datetime.now().isoformat(),
            "total_issues_recommended": len(breakdown),
            "phases_count": current_analysis["phases_count"],
            "best_principles_count": len(principles)
        })

        with open("github_issues_best_practices_analysis.json",
    "w",
    encoding="utf-8") as f:
            json.dump(self.analysis_results,
    f,
    indent=2,
    ensure_ascii=False,
    default=str)

        with open("github_issues_best_practices_report.md", "w", encoding="utf-8") as f:
            f.write(report)


        return self.analysis_results

if __name__ == "__main__":
    analyzer = GitHubIssuesBestPracticesAnalyzer()
    analyzer.main()
