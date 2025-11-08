#!/usr/bin/env python3
"""
M2规划GitHub Issues生成器
M2 Planning GitHub Issues Generator

基于最佳实践分析，生成细粒度的GitHub Issues用于M2执行
"""

import json
from datetime import datetime
from typing import Any


class M2GitHubIssuesGenerator:
    """M2规划GitHub Issues生成器"""

    def __init__(self):
        self.issues = []
        self.milestone_info = {
            "title": "M2: 50% Coverage Target",
            "description": "Achieve 50% code coverage through systematic testing across 4 phases",
            "due_date": "2025-12-01"
        }

    def generate_phase1_issues(self) -> list[dict[str, Any]]:
        """生成阶段1的Issues"""
        print("📝 生成阶段1 Issues: 基础覆盖率扩展 (目标15%)")

        phase1_issues = [
            {
                "title": "[M2-P1-01] 扩展core.di模块依赖注入测试",
                "body": """## 任务描述
**Issue类型**: 测试开发
**预估工时**: 16小时
**优先级**: high

### 背景
core.di模块当前覆盖率30%，需要扩展测试以提升到50%+。这是M2阶段最核心的基础设施工作，依赖注入容器的稳定性直接影响整个系统。

### 具体任务
1. 为DIContainer类添加单例模式测试（5个测试用例）
2. 为ServiceDescriptor添加序列化测试（4个测试用例）
3. 为依赖注入解析添加边界条件测试（3个测试用例）
4. 为循环依赖添加检测测试（3个测试用例）

### 验收标准
- [ ] 新增测试≥15个
- [ ] core.di模块覆盖率≥50%
- [ ] 所有测试通过
- [ ] 测试覆盖所有主要功能路径

### 验证方式
```bash
# 运行测试
pytest tests/unit/test_core_di.py -v

# 检查覆盖率
pytest --cov=src.core.di --cov-report=term-missing

# 检查具体覆盖率数据
python3 scripts/coverage_improvement_executor.py --module core.di
```

### 依赖关系
- 前置Issue: 无
- 后续Issue: #M2-P1-02, #M2-P1-03

### 备注
- 重点关注容器生命周期管理
- 测试边界条件和异常处理
- 确保线程安全性""",
                "labels": ["M2-P1", "core", "testing", "dependency-injection", "high-priority"],
                "assignees": [],
                "milestone": self.milestone_info["title"],
                "estimated_hours": 16,
                "priority": "high"
            },
            {
                "title": "[M2-P1-02] 完善core.config_di配置管理测试",
                "body": """## 任务描述
**Issue类型**: 测试开发
**预估工时**: 12小时
**优先级**: high

### 背景
core.config_di模块当前覆盖率31%，需要扩展配置解析和验证测试。配置系统是应用启动的关键组件，需要确保各种配置场景的稳定性。

### 具体任务
1. 为ConfigurationBinder添加配置文件解析测试（4个测试用例）
2. 为DIConfiguration添加环境变量测试（3个测试用例）
3. 为配置验证添加边界条件测试（3个测试用例）
4. 为配置错误处理添加异常测试（2个测试用例）

### 验收标准
- [ ] 新增测试≥12个
- [ ] core.config_di模块覆盖率≥45%
- [ ] 配置错误处理覆盖完整
- [ ] 环境变量配置测试通过

### 验证方式
```bash
# 运行配置测试
pytest tests/unit/test_core_config_di.py -v

# 检查覆盖率
pytest --cov=src.core.config_di --cov-report=term-missing

# 测试不同配置环境
ENV=test pytest tests/unit/test_core_config_di.py::test_env_config -v
```

### 依赖关系
- 前置Issue: #M2-P1-01
- 后续Issue: #M2-P1-03

### 备注
- 测试多种配置文件格式（JSON, YAML, ENV）
- 验证配置热重载功能
- 确保配置安全性""",
                "labels": ["M2-P1", "core", "testing", "configuration", "high-priority"],
                "assignees": [],
                "milestone": self.milestone_info["title"],
                "estimated_hours": 12,
                "priority": "high"
            },
            {
                "title": "[M2-P1-03] 优化core.service_lifecycle生命周期测试",
                "body": """## 任务描述
**Issue类型**: 测试开发
**预估工时**: 10小时
**优先级**: medium

### 背景
core.service_lifecycle模块当前覆盖率26%，需要完善服务生命周期管理测试。服务的生命周期管理影响系统的稳定性和资源利用效率。

### 具体任务
1. 为ServiceLifecycleManager添加服务注册/注销测试（3个测试用例）
2. 为服务状态监控添加状态变化测试（3个测试用例）
3. 为服务启动/停止添加异常处理测试（2个测试用例）
4. 为服务依赖关系添加依赖解析测试（2个测试用例）

### 验收标准
- [ ] 新增测试≥10个
- [ ] core.service_lifecycle模块覆盖率≥40%
- [ ] 生命周期管理功能测试完整
- [ ] 异常处理场景覆盖

### 验证方式
```bash
# 运行生命周期测试
pytest tests/unit/test_core_service_lifecycle.py -v

# 检查覆盖率
pytest --cov=src.core.service_lifecycle --cov-report=term-missing

# 测试服务依赖
pytest tests/unit/test_core_service_lifecycle.py::test_service_dependencies -v
```

### 依赖关系
- 前置Issue: #M2-P1-01, #M2-P1-02
- 后续Issue: #M2-P1-04

### 备注
- 关注服务启动顺序
- 测试资源清理机制
- 验证并发安全性""",
                "labels": ["M2-P1", "core", "testing", "lifecycle", "medium-priority"],
                "assignees": [],
                "milestone": self.milestone_info["title"],
                "estimated_hours": 10,
                "priority": "medium"
            },
            {
                "title": "[M2-P1-04] 扩展core.auto_binding自动绑定测试",
                "body": """## 任务描述
**Issue类型**: 测试开发
**预估工时**: 12小时
**优先级**: medium

### 背景
core.auto_binding模块当前覆盖率23%，需要扩展自动绑定功能测试。自动绑定是依赖注入系统的高级特性，需要确保各种绑定场景的正确性。

### 具体任务
1. 为AutoBinder添加绑定规则测试（3个测试用例）
2. 为约定绑定添加策略测试（3个测试用例）
3. 为自动扫描添加模块发现测试（3个测试用例）
4. 为绑定失败添加异常处理测试（3个测试用例）

### 验收标准
- [ ] 新增测试≥12个
- [ ] core.auto_binding模块覆盖率≥35%
- [ ] 自动绑定功能测试完整
- [ ] 绑定失败处理正确

### 验证方式
```bash
# 运行自动绑定测试
pytest tests/unit/test_core_auto_binding.py -v

# 检查覆盖率
pytest --cov=src.core.auto_binding --cov-report=term-missing

# 测试绑定冲突处理
pytest tests/unit/test_core_auto_binding.py::test_binding_conflicts -v
```

### 依赖关系
- 前置Issue: #M2-P1-01, #M2-P1-03
- 后续Issue: #M2-P1-05

### 备注
- 测试多种绑定策略
- 验证绑定性能
- 确保绑定结果的确定性""",
                "labels": ["M2-P1", "core", "testing", "auto-binding", "medium-priority"],
                "assignees": [],
                "milestone": self.milestone_info["title"],
                "estimated_hours": 12,
                "priority": "medium"
            },
            {
                "title": "[M2-P1-05] 完善测试工具链和报告自动化",
                "body": """## 任务描述
**Issue类型**: 工具开发
**预估工时**: 8小时
**优先级**: high

### 背景
当前测试工具链需要完善，提升测试执行和报告的自动化水平。这是整个M2项目的基础设施，需要确保工具链的稳定性和易用性。

### 具体任务
1. 完善coverage_analysis.py覆盖率分析功能（2小时）
2. 优化测试报告生成和格式化（2小时）
3. 添加测试执行时间监控（2小时）
4. 集成测试结果到GitHub Actions（2小时）

### 验收标准
- [ ] 测试工具链功能完整
- [ ] 覆盖率报告自动生成
- [ ] CI/CD集成成功运行
- [ ] 工具链文档完善

### 验证方式
```bash
# 运行工具链测试
python3 scripts/coverage_analysis.py --test

# 测试报告生成
python3 scripts/generate_test_report.py

# 验证CI集成
make ci-test
```

### 依赖关系
- 前置Issue: #M2-P1-01, #M2-P1-02, #M2-P1-03, #M2-P1-04
- 后续Issue: #M2-P2-01

### 备注
- 确保工具链兼容性
- 优化报告格式
- 添加错误处理机制""",
                "labels": ["M2-P1", "tools", "automation", "ci-cd", "high-priority"],
                "assignees": [],
                "milestone": self.milestone_info["title"],
                "estimated_hours": 8,
                "priority": "high"
            }
        ]

        return phase1_issues

    def generate_phase2_issues(self) -> list[dict[str, Any]]:
        """生成阶段2的Issues"""
        print("📝 生成阶段2 Issues: API层覆盖率提升 (目标25%)")

        phase2_issues = [
            {
                "title": "[M2-P2-01] 实现api.auth认证系统测试",
                "body": """## 任务描述
**Issue类型**: 测试开发
**预估工时**: 16小时
**优先级**: high

### 背景
api.auth模块是API层的核心认证组件，需要建立完整的测试覆盖。认证系统是安全的第一道防线，必须确保各种认证场景的正确性和安全性。

### 具体任务
1. 为JWT令牌生成和验证添加测试（4个测试用例）
2. 为OAuth2授权码流程添加测试（4个测试用例）
3. 为权限检查和角色验证添加测试（4个测试用例）
4. 为认证异常处理添加测试（3个测试用例）

### 验收标准
- [ ] 新增测试≥15个
- [ ] api.auth模块覆盖率≥40%
- [ ] 认证流程端到端测试通过
- [ ] 安全性测试通过

### 验证方式
```bash
# 运行认证测试
pytest tests/unit/test_api_auth.py -v

# 检查覆盖率
pytest --cov=src.api.auth --cov-report=term-missing

# 端到端认证测试
pytest tests/integration/test_auth_flow.py -v
```

### 依赖关系
- 前置Issue: #M2-P1-05
- 后续Issue: #M2-P2-02, #M2-P2-03

### 备注
- 测试各种令牌过期场景
- 验证权限继承机制
- 确保认证性能""",
                "labels": ["M2-P2", "api", "auth", "testing", "high-priority"],
                "assignees": [],
                "milestone": self.milestone_info["title"],
                "estimated_hours": 16,
                "priority": "high"
            },
            {
                "title": "[M2-P2-02] 建立api.predictions预测服务测试",
                "body": """## 任务描述
**Issue类型**: 测试开发
**预估工时**: 12小时
**优先级**: high

### 背景
api.predictions是核心的预测服务API，需要建立完整的测试体系。预测服务是业务的核心功能，需要确保预测结果的准确性和API的稳定性。

### 具体任务
1. 为预测请求验证添加测试（3个测试用例）
2. 为预测结果格式化添加测试（3个测试用例）
3. 为批量预测添加测试（3个测试用例）
4. 为预测错误处理添加测试（3个测试用例）

### 验收标准
- [ ] 新增测试≥12个
- [ ] api.predictions模块覆盖率≥35%
- [ ] 预测API功能测试完整
- [ ] 性能测试通过

### 验证方式
```bash
# 运行预测测试
pytest tests/unit/test_api_predictions.py -v

# 检查覆盖率
pytest --cov=src.api.predictions --cov-report=term-missing

# 批量预测测试
pytest tests/integration/test_batch_predictions.py -v
```

### 依赖关系
- 前置Issue: #M2-P2-01
- 后续Issue: #M2-P2-03, #M2-P2-04

### 备注
- 测试预测准确性
- 验证并发预测处理
- 确保预测结果一致性""",
                "labels": ["M2-P2", "api", "predictions", "testing", "high-priority"],
                "assignees": [],
                "milestone": self.milestone_info["title"],
                "estimated_hours": 12,
                "priority": "high"
            },
            {
                "title": "[M2-P2-03] 实现API集成测试套件",
                "body": """## 任务描述
**Issue类型**: 集成测试
**预估工时**: 14小时
**优先级**: medium

### 背景
API层需要集成测试来验证组件间的交互和数据流。集成测试确保各组件能够正确协作，是保证系统整体稳定性的关键。

### 具体任务
1. 创建认证到预测的集成测试（3个测试用例）
2. 创建API到数据库的集成测试（3个测试用例）
3. 创建API错误处理的集成测试（2个测试用例）
4. 创建API性能基准测试（2个测试用例）

### 验收标准
- [ ] 新增集成测试≥10个
- [ ] API集成测试通过率≥90%
- [ ] 集成测试覆盖主要业务流程
- [ ] 性能基准达标

### 验证方式
```bash
# 运行集成测试
pytest tests/integration/ -v

# 检查集成覆盖率
pytest --cov=src.api --cov-report=term-missing tests/integration/

# 性能测试
pytest tests/performance/test_api_performance.py -v
```

### 依赖关系
- 前置Issue: #M2-P2-01, #M2-P2-02
- 后续Issue: #M2-P2-05

### 备注
- 模拟真实业务场景
- 测试数据一致性
- 验证错误传播机制""",
                "labels": ["M2-P2", "api", "integration", "testing", "medium-priority"],
                "assignees": [],
                "milestone": self.milestone_info["title"],
                "estimated_hours": 14,
                "priority": "medium"
            },
            {
                "title": "[M2-P2-04] 建立Mock数据和服务系统",
                "body": """## 任务描述
**Issue类型**: 工具开发
**预估工时**: 10小时
**优先级**: high

### 背景
测试需要可靠的Mock数据和服务来隔离依赖。Mock系统是测试基础设施的重要组成部分，需要确保Mock数据的真实性和Mock服务的稳定性。

### 具体任务
1. 创建用户认证Mock服务（3个测试用例）
2. 创建预测模型Mock服务（3个测试用例）
3. 创建数据库Mock仓储（2个测试用例）
4. 创建API测试数据生成器（2个测试用例）

### 验收标准
- [ ] Mock系统功能完整
- [ ] Mock数据覆盖主要场景
- [ ] Mock服务稳定性测试通过
- [ ] Mock数据生成器可用

### 验证方式
```bash
# 运行Mock测试
pytest tests/mocks/ -v

# 测试Mock服务
python3 tests/mocks/test_mock_services.py

# 验证数据生成器
python3 tests/mocks/test_data_generator.py
```

### 依赖关系
- 前置Issue: #M2-P1-05
- 后续Issue: #M2-P2-03, #M2-P2-05

### 备注
- 确保Mock数据真实性
- 优化Mock服务性能
- 支持动态Mock配置""",
                "labels": ["M2-P2", "mock", "testing", "data", "high-priority"],
                "assignees": [],
                "milestone": self.milestone_info["title"],
                "estimated_hours": 10,
                "priority": "high"
            },
            {
                "title": "[M2-P2-05] 完善API文档和测试报告",
                "body": """## 任务描述
**Issue类型**: 文档开发
**预估工时**: 8小时
**优先级**: medium

### 背景
API层需要完整的文档和测试报告支持。良好的文档和报告是项目可维护性的重要保障，也是团队协作的基础。

### 具体任务
1. 更新API文档覆盖测试场景（2小时）
2. 创建API测试覆盖率报告（2小时）
3. 建立API性能监控报告（2小时）
4. 创建API安全测试报告（2小时）

### 验收标准
- [ ] API文档完整性≥95%
- [ ] 测试报告自动化生成
- [ ] 监控报告准确可靠
- [ ] 文档和报告同步更新

### 验证方式
```bash
# 生成API文档
python3 scripts/generate_api_docs.py

# 生成测试报告
python3 scripts/generate_test_report.py

# 验证文档覆盖率
python3 scripts/check_doc_coverage.py
```

### 依赖关系
- 前置Issue: #M2-P2-01, #M2-P2-02, #M2-P2-03
- 后续Issue: #M2-P3-01

### 备注
- 确保文档与代码同步
- 优化报告格式
- 添加自动化更新机制""",
                "labels": ["M2-P2", "api", "documentation", "reporting", "medium-priority"],
                "assignees": [],
                "milestone": self.milestone_info["title"],
                "estimated_hours": 8,
                "priority": "medium"
            }
        ]

        return phase2_issues

    def generate_phase3_issues(self) -> list[dict[str, Any]]:
        """生成阶段3的Issues"""
        print("📝 生成阶段3 Issues: 数据层覆盖率攻坚 (目标35%)")

        phase3_issues = [
            {
                "title": "[M2-P3-01] 数据库操作测试",
                "body": """## 任务描述
**Issue类型**: 测试开发
**预估工时**: 16小时
**优先级**: high

### 背景
数据库层是系统的数据持久化基础，需要建立完整的测试覆盖。数据操作的准确性和性能直接影响整个系统的稳定性。

### 具体任务
1. 为数据库连接池添加测试（4个测试用例）
2. 为事务管理添加测试（4个测试用例）
3. 为查询优化器添加测试（4个测试用例）
4. 为数据库迁移添加测试（4个测试用例）

### 验收标准
- [ ] 新增测试≥16个
- [ ] database模块覆盖率≥30%
- [ ] 数据库操作测试完整
- [ ] 性能测试通过

### 验证方式
```bash
# 运行数据库测试
pytest tests/unit/test_database.py -v

# 检查覆盖率
pytest --cov=src.database --cov-report=term-missing

# 数据库性能测试
pytest tests/performance/test_db_performance.py -v
```

### 依赖关系
- 前置Issue: #M2-P2-05
- 后续Issue: #M2-P3-02, #M2-P3-03

### 备注
- 测试并发数据库操作
- 验证数据一致性
- 确保事务完整性""",
                "labels": ["M2-P3", "database", "testing", "high-priority"],
                "assignees": [],
                "milestone": self.milestone_info["title"],
                "estimated_hours": 16,
                "priority": "high"
            },
            {
                "title": "[M2-P3-02] 数据模型验证测试",
                "body": """## 任务描述
**Issue类型**: 测试开发
**预估工时**: 12小时
**优先级**: high

### 背景
数据模型是业务逻辑的基础，需要建立完整的验证测试。模型验证确保数据的完整性和业务规则的正确执行。

### 具体任务
1. 为模型字段验证添加测试（4个测试用例）
2. 为模型关系验证添加测试（3个测试用例）
3. 为模型序列化添加测试（3个测试用例）
4. 为模型缓存添加测试（2个测试用例）

### 验收标准
- [ ] 新增测试≥12个
- [ ] 数据模型覆盖率≥40%
- [ ] 模型验证测试完整
- [ ] 序列化测试通过

### 验证方式
```bash
# 运行模型测试
pytest tests/unit/test_models.py -v

# 检查覆盖率
pytest --cov=src.database.models --cov-report=term-missing

# 模型验证测试
pytest tests/unit/test_model_validation.py -v
```

### 依赖关系
- 前置Issue: #M2-P3-01
- 后续Issue: #M2-P3-04

### 备注
- 测试复杂验证规则
- 验证模型继承关系
- 确保验证性能""",
                "labels": ["M2-P3", "database", "models", "testing", "high-priority"],
                "assignees": [],
                "milestone": self.milestone_info["title"],
                "estimated_hours": 12,
                "priority": "high"
            },
            {
                "title": "[M2-P3-03] 业务规则测试",
                "body": """## 任务描述
**Issue类型**: 测试开发
**预估工时**: 14小时
**优先级**: high

### 背景
业务规则是系统的核心逻辑，需要建立完整的测试覆盖。业务规则测试确保系统按照预期执行业务逻辑。

### 具体任务
1. 为业务规则引擎添加测试（4个测试用例）
2. 为规则条件评估添加测试（4个测试用例）
3. 为规则执行顺序添加测试（3个测试用例）
4. 为规则冲突处理添加测试（3个测试用例）

### 验收标准
- [ ] 新增测试≥14个
- [ ] 业务规则覆盖率≥35%
- [ ] 规则测试完整
- [ ] 冲突处理正确

### 验证方式
```bash
# 运行业务规则测试
pytest tests/unit/test_business_rules.py -v

# 检查覆盖率
pytest --cov=src.domain.rules --cov-report=term-missing

# 规则引擎测试
pytest tests/integration/test_rule_engine.py -v
```

### 依赖关系
- 前置Issue: #M2-P3-01, #M2-P3-02
- 后续Issue: #M2-P3-05

### 备注
- 测试复杂业务场景
- 验证规则执行性能
- 确保规则一致性""",
                "labels": ["M2-P3", "domain", "business-rules", "testing", "high-priority"],
                "assignees": [],
                "milestone": self.milestone_info["title"],
                "estimated_hours": 14,
                "priority": "high"
            },
            {
                "title": "[M2-P3-04] ML模型测试",
                "body": """## 任务描述
**Issue类型**: 测试开发
**预估工时**: 12小时
**优先级**: medium

### 背景
ML模型是预测系统的核心组件，需要建立完整的测试覆盖。模型测试确保预测的准确性和模型训练的稳定性。

### 具体任务
1. 为模型训练添加测试（3个测试用例）
2. 为模型预测添加测试（3个测试用例）
3. 为模型评估添加测试（3个测试用例）
4. 为模型版本管理添加测试（3个测试用例）

### 验收标准
- [ ] 新增测试≥12个
- [ ] ML模块覆盖率≥30%
- [ ] 模型测试完整
- [ ] 预测准确性达标

### 验证方式
```bash
# 运行ML测试
pytest tests/unit/test_ml_models.py -v

# 检查覆盖率
pytest --cov=src.ml --cov-report=term-missing

# 模型训练测试
pytest tests/integration/test_model_training.py -v
```

### 依赖关系
- 前置Issue: #M2-P3-02
- 后续Issue: #M2-P3-05

### 备注
- 测试模型训练稳定性
- 验证预测一致性
- 确保模型性能""",
                "labels": ["M2-P3", "ml", "models", "testing", "medium-priority"],
                "assignees": [],
                "milestone": self.milestone_info["title"],
                "estimated_hours": 12,
                "priority": "medium"
            },
            {
                "title": "[M2-P3-05] 集成测试完善",
                "body": """## 任务描述
**Issue类型**: 集成测试
**预估工时**: 10小时
**优先级**: high

### 背景
集成测试是确保系统各组件正确协作的关键。需要完善集成测试覆盖，确保系统整体稳定性。

### 具体任务
1. 创建端到端业务流程测试（3个测试用例）
2. 创建数据一致性测试（3个测试用例）
3. 创建系统性能测试（2个测试用例）
4. 创建故障恢复测试（2个测试用例）

### 验收标准
- [ ] 新增集成测试≥10个
- [ ] 集成测试覆盖率≥25%
- [ ] 端到端测试通过
- [ ] 性能指标达标

### 验证方式
```bash
# 运行集成测试
pytest tests/integration/ -v

# 端到端测试
pytest tests/e2e/ -v

# 性能测试
pytest tests/performance/ -v
```

### 依赖关系
- 前置Issue: #M2-P3-01, #M2-P3-02, #M2-P3-03, #M2-P3-04
- 后续Issue: #M2-P4-01

### 备注
- 模拟真实用户场景
- 测试系统边界条件
- 验证故障恢复机制""",
                "labels": ["M2-P3", "integration", "testing", "high-priority"],
                "assignees": [],
                "milestone": self.milestone_info["title"],
                "estimated_hours": 10,
                "priority": "high"
            }
        ]

        return phase3_issues

    def generate_phase4_issues(self) -> list[dict[str, Any]]:
        """生成阶段4的Issues"""
        print("📝 生成阶段4 Issues: 业务逻辑层覆盖 (目标50%)")

        phase4_issues = [
            {
                "title": "[M2-P4-01] 领域服务测试",
                "body": """## 任务描述
**Issue类型**: 测试开发
**预估工时**: 16小时
**优先级**: high

### 背景
领域服务是业务逻辑的核心，需要建立完整的测试覆盖。领域服务测试确保业务逻辑的正确性和可维护性。

### 具体任务
1. 为预测服务添加测试（4个测试用例）
2. 为分析服务添加测试（4个测试用例）
3. 为报表服务添加测试（4个测试用例）
4. 为通知服务添加测试（4个测试用例）

### 验收标准
- [ ] 新增测试≥16个
- [ ] 领域服务覆盖率≥45%
- [ ] 服务测试完整
- [ ] 业务逻辑正确

### 验证方式
```bash
# 运行领域服务测试
pytest tests/unit/test_domain_services.py -v

# 检查覆盖率
pytest --cov=src.domain.services --cov-report=term-missing

# 服务集成测试
pytest tests/integration/test_services.py -v
```

### 依赖关系
- 前置Issue: #M2-P3-05
- 后续Issue: #M2-P4-02, #M2-P4-03

### 备注
- 测试服务边界条件
- 验证服务组合逻辑
- 确保服务性能""",
                "labels": ["M2-P4", "domain", "services", "testing", "high-priority"],
                "assignees": [],
                "milestone": self.milestone_info["title"],
                "estimated_hours": 16,
                "priority": "high"
            },
            {
                "title": "[M2-P4-02] 策略模式测试",
                "body": """## 任务描述
**Issue类型**: 测试开发
**预估工时**: 12小时
**优先级**: high

### 背景
策略模式是系统的核心设计模式，需要建立完整的测试覆盖。策略测试确保不同预测策略的正确性和可扩展性。

### 具体任务
1. 为ML预测策略添加测试（3个测试用例）
2. 为统计预测策略添加测试（3个测试用例）
3. 为历史数据策略添加测试（3个测试用例）
4. 为集成策略添加测试（3个测试用例）

### 验收标准
- [ ] 新增测试≥12个
- [ ] 策略模式覆盖率≥40%
- [ ] 策略测试完整
- [ ] 策略切换正确

### 验证方式
```bash
# 运行策略测试
pytest tests/unit/test_strategies.py -v

# 检查覆盖率
pytest --cov=src.domain.strategies --cov-report=term-missing

# 策略集成测试
pytest tests/integration/test_strategies.py -v
```

### 依赖关系
- 前置Issue: #M2-P4-01
- 后续Issue: #M2-P4-04

### 备注
- 测试策略选择逻辑
- 验证策略参数配置
- 确保策略性能""",
                "labels": ["M2-P4", "domain", "strategies", "testing", "high-priority"],
                "assignees": [],
                "milestone": self.milestone_info["title"],
                "estimated_hours": 12,
                "priority": "high"
            },
            {
                "title": "[M2-P4-03] 事件驱动测试",
                "body": """## 任务描述
**Issue类型**: 测试开发
**预估工时**: 10小时
**优先级**: medium

### 背景
事件驱动是系统架构的重要组成部分，需要建立完整的测试覆盖。事件测试确保系统各组件间的松耦合和高内聚。

### 具体任务
1. 为事件发布添加测试（3个测试用例）
2. 为事件订阅添加测试（3个测试用例）
3. 为事件处理添加测试（2个测试用例）
4. 为事件持久化添加测试（2个测试用例）

### 验收标准
- [ ] 新增测试≥10个
- [ ] 事件系统覆盖率≥35%
- [ ] 事件测试完整
- [ ] 事件处理正确

### 验证方式
```bash
# 运行事件测试
pytest tests/unit/test_events.py -v

# 检查覆盖率
pytest --cov=src.domain.events --cov-report=term-missing

# 事件集成测试
pytest tests/integration/test_events.py -v
```

### 依赖关系
- 前置Issue: #M2-P4-01, #M2-P4-02
- 后续Issue: #M2-P4-05

### 备注
- 测试事件顺序
- 验证事件幂等性
- 确保事件性能""",
                "labels": ["M2-P4", "domain", "events", "testing", "medium-priority"],
                "assignees": [],
                "milestone": self.milestone_info["title"],
                "estimated_hours": 10,
                "priority": "medium"
            },
            {
                "title": "[M2-P4-04] CQRS模式测试",
                "body": """## 任务描述
**Issue类型**: 测试开发
**预估工时**: 12小时
**优先级**: high

### 背景
CQRS模式是系统架构的核心模式，需要建立完整的测试覆盖。CQRS测试确保命令查询分离的正确性和系统性能。

### 具体任务
1. 为命令处理添加测试（3个测试用例）
2. 为查询处理添加测试（3个测试用例）
3. 为命令验证添加测试（3个测试用例）
4. 为查询优化添加测试（3个测试用例）

### 验收标准
- [ ] 新增测试≥12个
- [ ] CQRS模块覆盖率≥40%
- [ ] CQRS测试完整
- [ ] 性能指标达标

### 验证方式
```bash
# 运行CQRS测试
pytest tests/unit/test_cqrs.py -v

# 检查覆盖率
pytest --cov=src.cqrs --cov-report=term-missing

# CQRS集成测试
pytest tests/integration/test_cqrs.py -v
```

### 依赖关系
- 前置Issue: #M2-P4-02
- 后续Issue: #M2-P4-05

### 备注
- 测试命令执行顺序
- 验证查询缓存机制
- 确保读写分离""",
                "labels": ["M2-P4", "cqrs", "testing", "high-priority"],
                "assignees": [],
                "milestone": self.milestone_info["title"],
                "estimated_hours": 12,
                "priority": "high"
            },
            {
                "title": "[M2-P4-05] 系统集成和性能优化",
                "body": """## 任务描述
**Issue类型**: 集成测试
**预估工时**: 14小时
**优先级**: high

### 背景
系统集成和性能优化是M2的最终阶段，需要建立完整的集成测试和性能监控。确保系统达到50%覆盖率目标并满足性能要求。

### 具体任务
1. 创建完整系统集成测试（4个测试用例）
2. 创建性能基准测试（3个测试用例）
3. 创建负载测试（3个测试用例）
4. 创建覆盖率达标验证（4个测试用例）

### 验收标准
- [ ] 新增集成测试≥14个
- [ ] 整体系统覆盖率≥50%
- [ ] 性能指标全部达标
- [ ] M2目标完全实现

### 验证方式
```bash
# 运行完整系统测试
pytest tests/e2e/ -v

# 检查整体覆盖率
pytest --cov=src --cov-report=term-missing

# 性能测试
pytest tests/performance/ -v

# 覆盖率验证
python3 scripts/verify_m2_coverage.py
```

### 依赖关系
- 前置Issue: #M2-P4-01, #M2-P4-02, #M2-P4-03, #M2-P4-04
- 后续Issue: 无（M2完成）

### 备注
- 这是M2的最终Issue
- 验证所有M2目标达成
- 为M3阶段做准备""",
                "labels": ["M2-P4", "integration", "performance", "testing", "high-priority"],
                "assignees": [],
                "milestone": self.milestone_info["title"],
                "estimated_hours": 14,
                "priority": "high"
            }
        ]

        return phase4_issues

    def generate_all_issues(self) -> list[dict[str, Any]]:
        """生成所有Issues"""
        print("🚀 生成M2规划的所有GitHub Issues...")

        all_issues = []

        # 生成各阶段的Issues
        all_issues.extend(self.generate_phase1_issues())
        all_issues.extend(self.generate_phase2_issues())
        all_issues.extend(self.generate_phase3_issues())
        all_issues.extend(self.generate_phase4_issues())

        self.issues = all_issues

        return all_issues

    def create_issue_templates(self) -> dict[str, Any]:
        """创建Issue模板"""
        print("📋 创建标准化Issue模板...")

        templates = {
            "task_template": """## 任务描述
**Issue类型**: {issue_type}
**预估工时**: {estimated_hours}小时
**优先级**: {priority}

### 背景
{background}

### 具体任务
{tasks}

### 验收标准
{acceptance_criteria}

### 验证方式
```bash
{verification_commands}
```

### 依赖关系
- 前置Issue: {dependencies}
- 后续Issue: {successors}

### 备注
{notes}

**标签**: {labels}""",

            "milestone_template": """# {title}

## 描述
{description}

## 时间线
- **开始日期**: {start_date}
- **截止日期**: {due_date}
- **总工期**: {total_duration}

## 目标
- **主要目标**: {main_goal}
- **覆盖率目标**: {coverage_target}%
- **质量目标**: {quality_target}

## 包含的Issues
{issues_summary}

## 成功标准
{success_criteria}

## 风险和缓解措施
{risk_mitigation}"""
        }

        return templates

    def save_issues_to_files(self):
        """保存Issues到文件"""
        print("💾 保存Issues到文件...")

        # 保存完整的Issues数据
        issues_data = {
            "milestone": self.milestone_info,
            "total_issues": len(self.issues),
            "issues": self.issues,
            "generated_at": datetime.now().isoformat()
        }

        with open("m2_github_issues.json", "w", encoding="utf-8") as f:
            json.dump(issues_data, f, indent=2, ensure_ascii=False)

        # 保存Issue创建脚本
        self.create_issue_creation_script()

        # 保存Markdown版本
        self.create_markdown_summary()

        print(f"✅ 已保存 {len(self.issues)} 个Issues到文件")
        return issues_data

    def create_issue_creation_script(self):
        """创建Issue创建脚本"""
        script_content = """#!/usr/bin/env python3
\"\"\"
M2 GitHub Issues创建脚本
M2 GitHub Issues Creation Script

自动创建M2规划的所有GitHub Issues
\"\"\"

import json
import requests
from pathlib import Path

# 配置GitHub API
GITHUB_TOKEN = "YOUR_GITHUB_TOKEN"  # 需要替换为实际的token
REPO_OWNER = "your-username"       # 需要替换为实际的用户名
REPO_NAME = "FootballPrediction"   # 仓库名称

def create_issue(issue_data):
    \"\"\"创建单个Issue\"\"\"
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/issues"

    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }

    payload = {
        "title": issue_data["title"],
        "body": issue_data["body"],
        "labels": issue_data["labels"],
        "milestone": issue_data.get("milestone")
    }

    response = requests.post(url, headers=headers, json=payload)

    if response.status_code == 201:
        issue = response.json()
        print(f"✅ 创建成功: {issue['title']} (#{issue['number']})")
        return issue
    else:
        print(f"❌ 创建失败: {issue_data['title']}")
        print(f"错误: {response.text}")
        return None

def main():
    \"\"\"主函数\"\"\"
    # 加载Issues数据
    with open("m2_github_issues.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    issues = data["issues"]

    print(f"🚀 开始创建 {len(issues)} 个GitHub Issues...")

    created_issues = []
    for issue in issues:
        created_issue = create_issue(issue)
        if created_issue:
            created_issues.append(created_issue)

    print(f"\\n🎉 成功创建 {len(created_issues)} 个Issues!")

    # 保存创建结果
    result = {
        "created_issues": len(created_issues),
        "total_issues": len(issues),
        "success_rate": len(created_issues) / len(issues) * 100,
        "created_at": datetime.now().isoformat(),
        "issues": [
            {
                "number": issue["number"],
                "title": issue["title"],
                "url": issue["html_url"]
            }
            for issue in created_issues
        ]
    }

    with open("m2_issues_creation_result.json", "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    main()
"""

        with open("create_m2_issues.py", "w", encoding="utf-8") as f:
            f.write(script_content)

    def create_markdown_summary(self):
        """创建Markdown摘要"""
        summary = f"""# M2 GitHub Issues创建计划

**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Milestone**: {self.milestone_info['title']}
**截止日期**: {self.milestone_info['due_date']}

## 📊 统计信息

- **总Issues数**: {len(self.issues)}
- **预估总工时**: {sum(issue['estimated_hours'] for issue in self.issues)}小时
- **平均工时**: {sum(issue['estimated_hours'] for issue in self.issues) / len(self.issues):.1f}小时

## 🎯 阶段分布

### 阶段1: 基础覆盖率扩展 (目标15%)
- **Issues数量**: 5个
- **预估工时**: 58小时
- **主要模块**: core.di, core.config_di, core.service_lifecycle, core.auto_binding, tools

### 阶段2: API层覆盖率提升 (目标25%)
- **Issues数量**: 5个
- **预估工时**: 60小时
- **主要模块**: api.auth, api.predictions, integration, mock, documentation

### 阶段3: 数据层覆盖率攻坚 (目标35%)
- **Issues数量**: 5个
- **预估工时**: 64小时
- **主要模块**: database, models, domain.rules, ml, integration

### 阶段4: 业务逻辑层覆盖 (目标50%)
- **Issues数量**: 5个
- **预估工时**: 64小时
- **主要模块**: domain.services, strategies, events, cqrs, integration

## 📋 Issues清单

"""

        for i, issue in enumerate(self.issues, 1):
            priority_icon = "🔴" if issue["priority"] == "high" else "🟡" if issue["priority"] == "medium" else "🟢"
            summary += f"{i}. {priority_icon} {issue['title']} ({issue['estimated_hours']}h)\n"

        summary += f"""

## 🚀 使用说明

### 1. 配置GitHub API
编辑 `create_m2_issues.py` 文件，设置：
- `GITHUB_TOKEN`: 你的GitHub Personal Access Token
- `REPO_OWNER`: GitHub用户名或组织名
- `REPO_NAME`: 仓库名称

### 2. 创建Milestone
在GitHub仓库中手动创建Milestone：
- **标题**: {self.milestone_info['title']}
- **描述**: {self.milestone_info['description']}
- **截止日期**: {self.milestone_info['due_date']}

### 3. 执行创建脚本
```bash
python3 create_m2_issues.py
```

### 4. 验证创建结果
检查 `m2_issues_creation_result.json` 文件中的创建结果。

## 📈 预期效果

通过这{len(self.issues)}个细粒度Issues，M2规划将实现：

- **明确的任务分解**: 每个Issue都有具体的任务和验收标准
- **可追踪的进度**: 通过GitHub项目板实时跟踪进度
- **质量保障**: 每个Issue都有自动化验证方式
- **团队协作**: 标准化的Issue模板和工作流程

---

**生成工具**: M2 GitHub Issues Generator
**版本**: v1.0
"""

        with open("M2_GitHub_Issues_Plan.md", "w", encoding="utf-8") as f:
            f.write(summary)

    def main(self):
        """主函数"""
        print("🚀 M2 GitHub Issues生成器启动...")

        # 生成所有Issues
        issues = self.generate_all_issues()

        # 创建模板
        templates = self.create_issue_templates()

        # 保存到文件
        data = self.save_issues_to_files()

        print("\\n🎉 M2 GitHub Issues生成完成!")
        print(f"   总Issues数: {len(issues)}")
        print(f"   预估总工时: {sum(issue['estimated_hours'] for issue in issues)}小时")
        print("   覆盖4个阶段，从1.42%到50%覆盖率目标")
        print("\\n📄 生成的文件:")
        print("   - m2_github_issues.json (完整数据)")
        print("   - create_m2_issues.py (创建脚本)")
        print("   - M2_GitHub_Issues_Plan.md (执行计划)")

        return data

if __name__ == "__main__":
    generator = M2GitHubIssuesGenerator()
    generator.main()
