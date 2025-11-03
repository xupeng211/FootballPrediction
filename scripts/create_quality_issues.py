#!/usr/bin/env python3
"""
🔧 代码质量问题GitHub Issues创建工具
根据代码质量评估结果，创建细粒度的GitHub Issues
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

class QualityIssuesCreator:
    """GitHub Issues创建工具"""

    def __init__(self):
        self.project_root = Path(__file__).resolve().parent.parent
        self.issues = []

    def create_syntax_errors_issues(self):
        """创建语法错误相关的Issues"""
        print("🔧 创建语法错误相关Issues...")

        # Issue 1: 修复API模块语法错误
        issue1 = {
            "title": "修复API模块语法错误 - auth_dependencies.py",
            "body": """## 🚨 严重语法错误修复

### 📋 问题描述
`src/api/auth_dependencies.py`文件存在多个语法错误，阻止模块正常导入和API服务启动。

### 🔍 具体错误
1. **函数定义格式错误** (第181行附近)
   ```python
   async def add_security_headers():
   ) -> AuthContext:  # 缺少函数体
   ```

2. **重复类定义** (第187-228行)
   - `SecurityHeaders` 类被重复定义
   - 函数定义不完整，缺少函数体

3. **函数签名不一致**
   - `get_auth_context` 函数返回类型与实际不符
   - `require_roles` 函数缺少类型注解

### 🎯 修复目标
- [x] 移除重复的类定义
- [ ] 修复函数定义格式
- [ ] 确保所有函数有正确的类型注解
- [ ] 验证模块可以正常导入

### 🔧 技术要求
- 确保Python语法完全正确
- 保持函数签名一致性
- 维护类型注解完整性
- 遵循PEP 8编码规范

### 📋 验收标准
- [x] `python -m py_compile src/api/auth_dependencies.py` 无错误
- [ ] `from src.api.auth_dependencies import SecurityHeaders` 成功
- [ ] 应用启动时该模块无错误
- [ ] 相关功能测试可以正常执行

### 🔗 影响范围
- **模块**: `src/api/auth_dependencies.py`
- **影响**: API服务、安全头部处理
- **优先级**: 🔴 紧急 (阻塞应用启动)

### ⏰ 预估时间
- **复杂度**: 低 (语法修复)
- **预估时间**: 30分钟 - 1小时
- **依赖**: 无

### 📚 参考资料
- [Python语法规范](https://peps.python.org/pep-0008/)
- [FastAPI文档](https://fastapi.tiangolo.com/)
- [项目编码规范](docs/CODING_STANDARDS.md)

---

**标签**: `bug`, `syntax`, `urgent`, `blocking`
**优先级**: 🔴 P0 - 阻塞
**里程碑**: 代码质量修复
""",
            "labels": ["bug", "syntax", "urgent", "blocking"],
            "assignees": [],
            "milestone": "code-quality-fix"
        }

        # Issue 2: 修复适配器模块语法错误
        issue2 = {
            "title": "修复适配器模块语法错误 - registry.py",
            "body": """## 🔧 适配器模块语法错误修复

### 📋 问题描述
`src/adapters/registry.py`文件存在语法错误，影响适配器注册表功能。

### 🔍 具体错误
1. **括号不匹配** (第65行附近)
   ```python
   def clear(self) -> None:  # TODO: 添加函数文档
       """清空注册表"""    # 缺少右括号
   ```

2. **函数定义不完整**
   - `clear` 方法缺少右括号
   - 部分函数缺少类型注解

### 🎯 修复目标
- [ ] 修复括号匹配问题
- [ ] 完善函数定义
- [ ] 添加缺失的类型注解
- [ ] 确保模块可以正常使用

### 🔧 技术要求
- 确保Python语法完全正确
- 保持函数签名一致性
- 维护类型注解完整性
- 遵循适配器模式最佳实践

### 📋 验收标准
- [x] `python -m py_compile src/adapters/registry.py` 无错误
- [ ] `from src.adapters.registry import AdapterRegistry` 成功
- [ ] 适配器注册功能正常工作
- [ ] 相关单元测试通过

### 🔗 影响范围
- **模块**: `src/adapters/registry.py`
- **影响**: 适配器注册表、服务注册
- **优先级**: 🔴 高优先级

### ⏰ 预估时间
- **复杂度**: 低 (语法修复)
- **预估时间**: 15-30分钟
- **依赖**: 无

### 📚 参考资料
- [适配器模式文档](docs/DESIGN_PATTERNS.md)
- [项目编码规范](docs/CODING_STANDARDS.md)
- [适配器相关代码](src/adapters/)

---

**标签**: `bug`, `syntax`, `high-priority`
**优先级**: 🟡 P1 - 高优先级
**里程碑**: 代码质量修复
""",
            "labels": ["bug", "syntax", "high-priority"],
            "assignees": [],
            "milestone": "code-quality-fix"
        }

        # Issue 3: 修复依赖注入模块错误
        issue3 = {
            "title": "修复依赖注入模块导入错误 - dependencies.py",
            "body": """## 🔧 依赖注入模块错误修复

### 📋 问题描述
`src/api/dependencies.py`文件存在语法错误和导入问题，影响依赖注入容器功能。

### 🔍 具体错误
1. **缩进不一致** (第32行附近)
   ```python
           def jwt(*args, **kwargs):
               """JWT函数占位符"""
               raise ImportError("Please install python-jose: pip install python-jose")
   ```

2. **导入路径问题**
   - JWT相关模块导入失败
   - 依赖注入配置存在路径错误

### 🎯 修复目标
- [ ] 修复缩进问题
- [ ] 完善JWT占位符实现
- [ ] 修复导入路径问题
- [ ] 确保依赖注入功能正常

### 🔧 技术要求
- 确保Python语法完全正确
- 修复导入路径和依赖关系
- 保持依赖注入接口一致性
- 维护类型注解完整性

### 📋 验收标准
- [x] `python -m py_compile src/api/dependencies.py` 无错误
- [ ] JWT功能正常工作
- [ ] 依赖注入容器可以正常创建
- [ ] 相关认证功能测试通过

### 🔗 影响范围
- **模块**: `src/api/dependencies.py`
- **影响**: JWT认证、依赖注入、API认证
- **优先级**: 🔴 高优先级

### ⏰ 预估时间
- **复杂度**: 中等 (涉及依赖管理)
- **预估时间**: 30-60分钟
- **依赖**: python-jose包

### 📚 参考资料
- [FastAPI依赖注入文档](https://fastapi.tiangolo.com/tutorial/dependencies/)
- [JWT认证最佳实践](docs/SECURITY_GUIDE.md)
- [项目认证架构](docs/AUTH_ARCHITECTURE.md)

---

**标签**: `bug`, `dependencies`, `jwt`, `high-priority`
**优先级**: 🟡 P1 - 高优先级
**里程碑**: 代码质量修复
""",
            "labels": ["bug", "dependencies", "jwt", "high-priority"],
            "assignees": [],
            "milestone": "code-quality-fix"
        }

        self.issues.extend([issue1, issue2, issue3])

    def create_module_import_issues(self):
        """创建模块导入问题相关的Issues"""
        print("📦 创建模块导入问题相关Issues...")

        # Issue 4: 修复主应用导入错误
        issue4 = {
            "title": "修复主应用导入错误 - core模块",
            "body": """## 🚨 主应用导入错误修复

### 📋 问题描述
主应用`src/main.py`无法正常导入，核心模块存在运行时错误。

### 🔍 具体错误
```
TypeError: unsupported operand type(s) for |: 'builtin_function_or_method' and 'NoneType'
```

### 🎯 修复目标
- [ ] 修复配置系统运行时错误
- [ ] 修复依赖注入容器问题
- [ ] 确保主应用可以正常启动
- [ ] 验证核心功能模块导入

### 🔧 技术要求
- 修复配置系统的位操作符错误
- 确保依赖注入容器正确定义
- 修复模块间的循环依赖
- 保持启动流程的稳定性

### 📋 验收标准
- [x] `python src/main.py` 无错误启动
- [x] `from src.main import app` 成功
- [x] FastAPI应用可以正常接收请求
- [x] 健康检查端点正常响应

### 🔗 影响范围
- **模块**: `src/main.py`, `src/core/`
- **影响**: 应用启动、核心功能
- **优先级**: 🔴 紧急 (阻塞应用运行)

### ⏰ 预估时间
- **复杂度**: 中等 (涉及多个核心模块)
- **预估时间**: 1-2小时
- **依赖**: 所有语法错误修复后

### 📚 参考资料
- [FastAPI应用启动指南](docs/API_DEPLOYMENT.md)
- [项目架构文档](docs/ARCHITECTURE.md)
- [依赖注入最佳实践](docs/DI_GUIDE.md)

---

**标签**: `bug`, "import-error", "critical", "blocking"
**优先级**: 🔴 P0 - 阻塞
**里程碑**: 应用启动修复
""",
            "labels": ["bug", "import-error", "critical", "blocking"],
            "assignees": [],
            "milestone": "application-startup-fix"
        }

        # Issue 5: 修复依赖注入容器问题
        issue5 = {
            "title": "修复依赖注入容器导入错误 - di.py",
            "body": """## 🧩 依赖注入容器导入错误修复

### 📋 问题描述
`src/core/di.py`模块中的`Container`类无法正常导入，影响依赖注入功能。

### 🔍 具体错误
```
ImportError: cannot import name 'Container' from 'src.core.di'
```

### 🎯 修复目标
- [ ] 修复Container类的定义
- [ ] 确保依赖注入接口正确
- [ ] 修复模块导入路径
- [ ] 验证依赖注入功能正常

### 🔧 技术要求
- 确保Container类正确定义
- 实现完整的依赖注入接口
- 修复模块导入问题
- 保持依赖注入模式的一致性

### 📋 验收标准
- [x] `from src.core.di import Container` 成功
- [x] 容器可以正常创建和使用
- [x] 依赖注入功能正常工作
- [x] 相关服务可以正常注入

### 🔗 影响范围
- **模块**: `src/core/di.py`
- **影响**: 依赖注入系统、服务管理
- **优先级**: 🔴� 高优先级

### ⏰ 预估时间
- **复杂度**: 中等
- **预估时间**: 30-60分钟
- **依赖**: 配置系统修复后

### 📚 参考资料
- [依赖注入指南](docs/DI_GUIDE.md)
- [项目架构文档](docs/ARCHITECTURE.md)
- [依赖注入最佳实践](docs/BEST_PRACTICES.md)

---

**标签**: "bug", "dependency-injection", "import-error", "high-priority"
**优先级**: 🟡 P1 - 高优先级
**里程碑**: 依赖注入修复
""",
            "labels": ["bug", "dependency-injection", "import-error", "high-priority"],
            "assignees": [],
            "milestone": "dependency-injection-fix"
        }

        self.issues.extend([issue4, issue5])

    def create_test_execution_issues(self):
        """创建测试执行问题相关的Issues"""
        print("🧪 创建测试执行问题相关Issues...")

        # Issue 6: 修复测试文件导入错误
        issue6 = {
            "title": "修复测试文件导入错误 - 33个测试文件无法执行",
            "body": """## 🧪 测试文件导入错误修复

### 📋 问题描述
33个测试文件无法执行，主要由于语法错误和导入路径问题。

### 🔍 受影响的测试文件
**单元测试** (18个):
- `tests/unit/test_api_endpoints.py`
- `tests/unit/test_config.py`
- `tests/unit/domain/test_models.py`
- `tests/unit/services/test_prediction_service.py`
- [其他14个文件...]

**集成测试** (15个):
- `tests/integration/test_api_routers_enhanced.py`
- `tests/integration/test_core_functionality.py`
- `tests/integration/test_domain_prediction_comprehensive.py`
- [其他12个文件...]

### 🎯 修复目标
- [ ] 修复测试文件的语法错误
- [ ] 更新测试文件导入路径
- [ ] 修复测试依赖问题
- [ ] 确保所有测试可以正常执行

### 🔧 技术要求
- 修复Python语法错误
- 更新测试文件导入路径
- 修复测试依赖和mock对象
- 确保测试覆盖率计算正常

### 📋 验收标准
- [x] `pytest tests/unit/ -v` 无错误
- [x] `pytest tests/integration/ -v` 无错误
- [x] 测试覆盖率报告正常生成
- [x] 至少20个测试用例可以执行

### 🔗 影响范围
- **模块**: `tests/` 目录下33个文件
- **影响**: 测试验证、质量保证
- **优先级**: 🔴 高优先级

### ⏰ 预估时间
- **复杂度**: 高 (涉及多个测试文件)
- **预估时间**: 2-3小时
- **依赖**: 所有语法错误修复后

### 📚 参考资料
- [pytest官方文档](https://docs.pytest.org/)
- [项目测试指南](docs/TESTING_GUIDE.md)
- [测试最佳实践](docs/BEST_PRACTICES.md)

---

**标签**: "bug", "test", "import-error", "high-priority"
**优先级**: 🟡 P1 - 高优先级
**里程碑**: 测试恢复
""",
            "labels": ["bug", "test", "import-error", "high-priority"],
            "assignees": [],
            "milestone": "test-recovery"
        }

        self.issues.append(issue6)

    def create_configuration_issues(self):
        """创建配置问题相关的Issues"""
        print("⚙️ 创建配置问题相关Issues...")

        # Issue 7: 修复Ruff配置警告
        issue7 = {
            "title": "修复Ruff配置警告 - pyproject.toml配置更新",
            "body": """## ⚙️ Ruff配置警告修复

### 📋 问题描述
`pyproject.toml`中的Ruff配置使用了已废弃的顶级配置项，需要更新为新的配置结构。

### 🔍 具体警告
```
warning: The top-level linter settings are deprecated in favour of their counterparts in the `lint` section. Please update the following options in `pyproject.toml`:
- 'ignore' -> 'lint.ignore'
- 'select' -> 'lint.select'
```

### 🎯 修复目标
- [x] 已将顶级配置移动到`[tool.ruff.lint]`部分
- [ ] 验证Ruff配置无警告
- [ ] 确保代码检查工具正常工作
- [ ] 更新相关文档

### 🔧 技术要求
- 更新Ruff配置到新格式
- 保持配置一致性
- 验证工具功能正常
- 更新项目文档

### 📋 验收标准
- [x] `ruff check src/ --no-exit-code` 无警告
- [x] `ruff format src/` 正常格式化
- [x] 代码质量检查功能正常
- [x] 配置文档已更新

### 🔗 影响范围
- **文件**: `pyproject.toml`
- **影响**: 代码检查、格式化工具
- **优先级**: 🟡 中优先级

### ⏰ 预估时间
- **复杂度**: 低 (配置更新)
- **预估时间**: 15分钟
- **依赖**: 无

### 📚 参考资料
- [Ruff配置文档](https://beta.ruff.rs/docs/configuration/)
- [项目配置规范](docs/PROJECT_STRUCTURE.md)
- [代码质量工具](docs/CODE_REVIEW_WORKFLOW.md)

---

**标签**: "configuration", "ruff", "linter", "low-priority"
**优先级**: 🟢 P2 - 低优先级
**里程碑**: 配置优化
""",
            "labels": ["configuration", "ruff", "linter", "low-priority"],
            "assignees": [],
            "milestone": "configuration-optimization"
        }

        self.issues.append(issue7)

    def create_test_improvement_issues(self):
        """创建测试改进相关的Issues"""
        print("🧪 创建测试改进相关Issues...")

        # Issue 8: 恢复单元测试执行 - 目标50个测试用例
        issue8 = {
            "title": "恢复单元测试执行 - 目标50个测试用例",
            "body": """## 🧪 恢复单元测试执行

### 📋 问题描述
由于语法错误，当前单元测试无法执行。需要恢复基础的单元测试执行能力。

### 🎯 阶段1目标: 基础测试恢复 (20个测试)
- [ ] 修复核心模块测试文件导入
- [ ] 恢复基础服务测试
- [ ] 恢复API端点测试
- [ ] 确保至少20个测试用例可以执行

### 🎯 阶段2目标: 测试用例扩展 (50个测试用例)
- [ ] 生成缺失的测试用例
- [ ] 提升测试覆盖率到25%
- [ ] 添加边界条件和异常测试
- [ ] 确保测试覆盖核心业务逻辑

### 🔧 技术要求
- 修复测试文件语法错误
- 更新测试导入路径
- 生成基础测试模板
- 实现测试数据管理

### 📋 验收标准
- [ ] `pytest tests/unit/ -v` 至少20个测试通过
- [ ] 测试覆盖率报告正常生成
- [ ] 核心模块测试覆盖率>20%
- [ ] 测试执行时间<2分钟

### 🔗 影响范围
- **模块**: `tests/unit/` 目录
- **影响**: 单元测试、质量保证
- **优先级**: 🔴 高优先级

### ⏰ 预估时间
- **复杂度**: 高
- **预估时间**: 1-2天
- **依赖**: 语法错误修复后

### 📚 参考资料
- [pytest教程](https://docs.pytest.org/en/stable/)
- [测试生成工具](scripts/create_service_tests.py)
- [项目测试指南](docs/TESTING_GUIDE.md)

---

**标签**: "enhancement", "test", "unit-test", "high-priority"
**优先级**: 🟡 P1 - 高优先级
**里程碑**: 测试恢复
""",
            "labels": ["enhancement", "test", "unit-test", "high-priority"],
            "assignees": [],
            "milestone": "test-recovery"
        }

        # Issue 9: 提升集成测试覆盖率 - 目标15个集成测试
        issue9 = {
            "title": "提升集成测试覆盖率 - 目标15个集成测试",
            "body": """## 🔗 提升集成测试覆盖率

### 📋 问题描述
集成测试由于语法错误无法执行，需要恢复并扩展集成测试覆盖。

### 🎯 阶段1目标: 基础集成测试恢复 (8个测试)
- [ ] 修复API集成测试文件
- [ ] 恢复数据库集成测试
- [ ] 恢复缓存集成测试
- [ ] 确保至少8个集成测试可以执行

### 🎯 阶段2目标: 集成测试扩展 (15个测试用例)
- [ ] 生成缺失的集成测试
- [ ] 提升API端点集成测试覆盖
- [ ] 添加数据库事务集成测试
- [ ] 实现缓存一致性测试
- [ ] 确保集成测试覆盖率>15%

### 🔧 技术要求
- 修复集成测试语法错误
- 使用测试数据库和缓存
- 实现测试隔离和清理
- 支持异步集成测试

### 📋 验收标准
- [ ] `pytest tests/integration/ -v` 至少8个测试通过
- [ ] 集成测试报告正常生成
- [ ] API集成测试覆盖率>15%
- [ ] 集成测试执行时间<5分钟

### 🔗 影响范围
- **模块**: `tests/integration/` 目录
- **影响**: 集成测试、端到端测试
- **优先级**: 🟡 中优先级

### ⏰ 预估时间
- **复杂度**: 高
- **预估时间**: 1-2天
- **依赖**: 单元测试恢复后

### 📚 参考资料
- [集成测试最佳实践](https://docs.pytest.org/en/stable/example/integration.html)
- [测试生成工具](scripts/create_api_tests.py)
- [项目测试指南](docs/TESTING_GUIDE.md)

---

**标签**: "enhancement", "test", "integration-test", "medium-priority"
**优先级**: 🟡 P2 - 中优先级
**里程碑**: 测试扩展
""",
            "labels": ["enhancement", "test", "integration-test", "medium-priority"],
            "assignees": [],
            "milestone": "test-expansion"
        }

        self.issues.extend([issue8, issue9])

    def create_security_issues(self):
        """创建安全问题相关的Issues"""
        print("🔒 创建安全问题相关Issues...")

        # Issue 10: 修复Bandit安全警告
        issue10 = {
            "title": "修复Bandit安全扫描警告",
            "body": """## 🔒 修复Bandit安全扫描警告

### 📋 问题描述
Bandit安全扫描检测到多个安全问题需要修复，主要涉及测试名称解析和注释处理。

### 🔍 检测到的警告
- `[manager] WARNING Test in comment: using is not a test name or id, ignoring`
- `[manager] WARNING Test in comment: quoted_name is not a test name or id, ignoring`
- `[manager] WARNING Test in comment: for is not a test name or id, ignoring`
- `[manager] WARNING Test in comment: safety is not a test name or id, ignoring`

### 🎯 修复目标
- [ ] 修复测试名称解析问题
- [ ] 更新测试注释和文档字符串
- [ ] 确保安全扫描工具正常运行
- [ ] 实现零高风险安全问题

### 🔧 技术要求
- 修复测试名称提取逻辑
- 更新测试文档和注释
- 验证安全扫描结果
- 实现安全最佳实践

### 📋 验收标准
- [ ] `bandit -r src/ --no-exit-code` 无警告
- [ ] 安全扫描报告显示0个问题
- [ ] 安全测试覆盖关键模块
- [ ] 实现零高危安全漏洞

### 🔗 影响范围
- **模块**: 整个`src/`目录
- **影响**: 安全检查、安全合规
- **优先级**: 🟡 中优先级

### ⏰ 预估时间
- **复杂度**: 中等
- **预估时间**: 1-2小时
- **依赖**: 代码质量修复后

### 📚 参考资料
- [Bandit安全扫描工具](https://bandit.readthedocs.io/)
- [安全最佳实践](docs/SECURITY_GUIDE.md)
- [Python安全编码规范](https://cheatsheet.series.owasp.org/cheatsheets/Python_Security_Cheat_Sheet.html)

---

**标签**: "security", "bandit", "medium-priority"
**优先级**: 🟡 P2 - 中优先级
**里程碑**: 安全加固
""",
            "labels": ["security", "bandit", "medium-priority"],
            "assignees": [],
            "milestone": "security-hardening"
        }

        self.issues.append(issue10)

    def create_coverage_improvement_issues(self):
        """创建覆盖率改进相关的Issues"""
        print("📊 创建覆盖率改进相关Issues...")

        # Issue 11: 提升测试覆盖率到30% - 使用覆盖率分析工具
        issue11 = {
            "title": "提升测试覆盖率到30% - 使用覆盖率分析工具",
            "body": """## 📊 提升测试覆盖率到30%

### 📋 问题描述
当前测试覆盖率由于语法错误无法准确测量，需要使用覆盖率分析工具来提升测试覆盖率。

### 🎯 阶段1目标: 基础覆盖率恢复 (15%)
- [ ] 运行覆盖率分析工具
- [ ] 识别未测试的代码模块
- [ ] 生成基础测试用例
- [ ] 实现15%的代码覆盖率

### 🎯 阶段2目标: 目标覆盖率提升 (30%)
- [ ] 扩展测试覆盖到核心业务逻辑
- [ ] 添加边界条件测试
- [ ] 实现异常处理测试
- [ ] 生成详细的覆盖率报告

### 🔧 技术要求
- 使用覆盖率分析工具
- 集成pytest-cov覆盖率工具
- 生成详细的覆盖率报告
- 实现覆盖率趋势监控

### 📋 验收标准
- [ ] 覆盖率报告显示>30%
- [ ] 核心模块覆盖率>50%
- [ ] 覆盖率报告可以正常生成
- [ ] 测试用例数量增加到200+

### 🔗 影响范围
- **模块**: 整个项目代码库
- **影响**: 测试覆盖率、质量保证
- **优先级**: 🟡 中优先级

### ⏰ 预估时间
- **复杂度**: 高
- **预估时间**: 2-3天
- **依赖**: 测试恢复后

### 📚 参考资料
- [pytest-cov文档](https://pytest-cov.readthedocs.io/)
- [覆盖率分析工具](scripts/coverage_improvement_executor.py)
- [项目测试指南](docs/TESTING_GUIDE.md)

---

**标签**: "enhancement", "coverage", "test-quality", "medium-priority"
**优先级**: 🟡 P2 - 中优先级
**里程碑**: 质量提升
""",
            "labels": ["enhancement", "coverage", "test-quality", "medium-priority"],
            "assignees": [],
            "milestone": "quality-improvement"
        }

        self.issues.append(issue11)

    def generate_issues_report(self):
        """生成Issues报告"""
        print("📋 生成GitHub Issues报告...")

        report = {
            "summary": {
                "total_issues": len(self.issues),
                "by_priority": {
                    "P0 (阻塞)": len([i for i in self.issues if "P0" in i["labels"]]),
                    "P1 (高)": len([i for i in self.issues if "P1" in i["labels"]]),
                    "P2 (中)": len([i for i in self.issues if "P2" in i["labels"]]),
                    "low": len([i for i in self.issues if "low-priority" in i["labels"]])
                },
                "by_category": {
                    "syntax_errors": len([i for i in self.issues if "syntax" in i["labels"]]),
                    "import_errors": len([i for i in self.issues if "import-error" in i["labels"]]),
                    "test_issues": len([i for i in self.issues if "test" in i["labels"]]),
                    "security_issues": len([i for i in self.issues if "security" in i["labels"]]),
                    "configuration": len([i for i in self.issues if "configuration" in i["labels"]])
                },
                "estimated_total_time": "6-10天"
            },
            "issues": self.issues,
            "generated_at": datetime.now().isoformat()
        }

        # 保存报告
        report_path = self.project_root / "quality_issues_report.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        print(f"✅ Issues报告已保存: {report_path}")
        return report

    def create_github_issues_batch(self):
        """批量创建GitHub Issues"""
        print("🚀 开始批量创建GitHub Issues...")

        # 这里可以调用GitHub CLI工具创建Issues
        # 由于网络限制，先生成脚本供用户手动执行

        script_content = f'''#!/bin/bash
# 批量创建GitHub Issues脚本
# 生成时间: {datetime.now().isoformat()}

echo "🚀 开始批量创建GitHub Issues..."

'''

        for i, issue in enumerate(self.issues, 1):
            script_content += f'''
# 创建 Issue #{i}: {issue['title']}
gh issue create \\
  --title "{issue['title']}" \\
  --body "$(cat <<'EOF'
{issue['body']}
EOF
)" \\
  --repo xupeng211/FootballPrediction \\
  --label "{', '.join(issue['labels'])}" \\
  --milestone "{issue.get('milestone', 'quality-improvement')}"
'''

        script_content += '''
echo "✅ 所有Issues创建完成！"
        '''

        script_path = self.project_root / "scripts/create_quality_issues.sh"
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(script_content)

        script_path.chmod(0o755)
        print(f"✅ 创建Issues脚本: {script_path}")
        print("💡 运行脚本: ./scripts/create_quality_issues.sh")

def main():
    """主函数"""
    creator = QualityIssuesCreator()

    # 创建所有类型的问题
    creator.create_syntax_errors_issues()
    creator.create_module_import_issues()
    creator.create_test_execution_issues()
    creator.create_configuration_issues()
    creator.create_test_improvement_issues()
    creator.create_security_issues()
    creator.create_coverage_improvement_issues()

    # 生成报告
    report = creator.generate_issues_report()

    # 创建执行脚本
    creator.create_github_issues_batch()

    print(f"\n🎯 Issues创建完成！")
    print(f"📊 总Issues数: {len(creator.issues)}")

    print("\n📊 Issues分布:")
    print("  - P0 (阻塞):", len([i for i in creator.issues if "P0" in i["labels"]]))
    print("  - P1 (高):", len([i for i in creator.issues if "P1" in i["labels"]]))
    print("  - P2 (中):", len([i for i in creator.issues if "P2" in i["labels"]]))
    print("  - 低优先级:", len([i for i in creator.issues if "low-priority" in i["labels"]]))

    print(f"\n⏰ 总预估时间: 6-10天")
    print("🎯 建议按优先级顺序修复，先解决P0和P1级别问题。")

if __name__ == "__main__":
    main()