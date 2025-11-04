#!/usr/bin/env python3
"""
🔧 代码质量问题GitHub Issues创建工具（最终版）
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

    def create_all_issues(self):
        """创建所有Issues"""
        print("🔧 开始创建GitHub Issues...")

        # Issue 1: 修复API模块语法错误
        issue1 = {
            "title": "修复API模块语法错误 - auth_dependencies.py",
            "body": "## 🚨 严重语法错误修复\n\n### 📋 问题描述\n`src/api/auth_dependencies.py`文件存在多个语法错误，阻止模块正常导入和API服务启动。\n\n### 🔍 具体错误\n1. **函数定义格式错误** (第181行附近)\n   ```python\n   async def add_security_headers():\n   ) -> AuthContext:  # 缺少函数体\n   ```\n\n2. **重复类定义** (第187-228行)\n   - `SecurityHeaders` 类被重复定义\n   - 函数定义不完整，缺少函数体\n\n### 🎯 修复目标\n- [x] 移除重复的类定义\n- [ ] 修复函数定义格式\n- [ ] 确保所有函数有正确的类型注解\n- [ ] 验证模块可以正常导入\n\n### 📋 验收标准\n- [x] `python -m py_compile src/api/auth_dependencies.py` 无错误\n- [ ] `from src.api.auth_dependencies import SecurityHeaders` 成功\n- [ ] 应用启动时该模块无错误\n\n### 🔗 影响范围\n- **模块**: `src/api/auth_dependencies.py`\n- **影响**: API服务、安全头部处理\n- **优先级**: 🔴 紧急 (阻塞应用启动)\n- **预估时间**: 30分钟 - 1小时\n\n---\n\n**标签**: `bug`,
    
    `syntax`,
    `urgent`,
    `blocking`\n**优先级**: 🔴 P0 - 阻塞",
    
            "labels": ["bug", "syntax", "urgent", "blocking"]
        }

        # Issue 2: 修复适配器模块语法错误
        issue2 = {
            "title": "修复适配器模块语法错误 - registry.py",
            "body": "## 🔧 适配器模块语法错误修复\n\n### 📋 问题描述\n`src/adapters/registry.py`文件存在语法错误，影响适配器注册表功能。\n\n### 🔍 具体错误\n1. **括号不匹配** (第65行附近)\n   ```python\n   def clear(self) -> None:  # TODO: 添加函数文档\n       \"\"\"清空注册表\"\"\"    # 缺少右括号\n   ```\n\n### 🎯 修复目标\n- [ ] 修复括号匹配问题\n- [ ] 完善函数定义\n- [ ] 添加缺失的类型注解\n- [ ] 确保模块可以正常使用\n\n### 📋 验收标准\n- [x] `python -m py_compile src/adapters/registry.py` 无错误\n- [ ] `from src.adapters.registry import AdapterRegistry` 成功\n- [ ] 适配器注册功能正常工作\n\n### 🔗 影响范围\n- **模块**: `src/adapters/registry.py`\n- **影响**: 适配器注册表、服务注册\n- **优先级**: 🔴 高优先级\n- **预估时间**: 15-30分钟\n\n---\n\n**标签**: `bug`,
    
    `syntax`,
    `high-priority`\n**优先级**: 🟡 P1 - 高优先级",
    
            "labels": ["bug", "syntax", "high-priority"]
        }

        # Issue 3: 修复依赖注入模块错误
        issue3 = {
            "title": "修复依赖注入模块导入错误 - dependencies.py",
            "body": "## 🔧 依赖注入模块错误修复\n\n### 📋 问题描述\n`src/api/dependencies.py`文件存在语法错误和导入问题，影响依赖注入容器功能。\n\n### 🔍 具体错误\n1. **缩进不一致** (第32行附近)\n   ```python\n          def jwt(*args,
    
    **kwargs):\n              \"\"\"JWT函数占位符\"\"\"\n              raise ImportError(\"Please install python-jose: pip install python-jose\")\n   ```\n\n### 🎯 修复目标\n- [ ] 修复缩进问题\n- [ ] 完善JWT占位符实现\n- [ ] 修复导入路径问题\n- [ ] 确保依赖注入功能正常\n\n### 📋 验收标准\n- [x] `python -m py_compile src/api/dependencies.py` 无错误\n- [ ] JWT功能正常工作\n- [ ] 依赖注入容器可以正常创建\n\n### 🔗 影响范围\n- **模块**: `src/api/dependencies.py`\n- **影响**: JWT认证、依赖注入、API认证\n- **优先级**: 🔴 高优先级\n- **预估时间**: 30-60分钟\n\n---\n\n**标签**: `bug`,
    
    `dependencies`,
    `jwt`,
    `high-priority`\n**优先级**: 🟡 P1 - 高优先级",
    
            "labels": ["bug", "dependencies", "jwt", "high-priority"]
        }

        # Issue 4: 修复主应用导入错误
        issue4 = {
            "title": "修复主应用导入错误 - core模块",
            "body": "## 🚨 主应用导入错误修复\n\n### 📋 问题描述\n主应用`src/main.py`无法正常导入，核心模块存在运行时错误。\n\n### 🔍 具体错误\n```\nTypeError: unsupported operand type(s) for |: 'builtin_function_or_method' and 'NoneType'\n```\n\n### 🎯 修复目标\n- [ ] 修复配置系统运行时错误\n- [ ] 修复依赖注入容器问题\n- [ ] 确保主应用可以正常启动\n- [ ] 验证核心功能模块导入\n\n### 📋 验收标准\n- [x] `python src/main.py` 无错误启动\n- [x] `from src.main import app` 成功\n- [x] FastAPI应用可以正常接收请求\n- [x] 健康检查端点正常响应\n\n### 🔗 影响范围\n- **模块**: `src/main.py`,
    
    `src/core/`\n- **影响**: 应用启动、核心功能\n- **优先级**: 🔴 紧急 (阻塞应用运行)\n- **预估时间**: 1-2小时\n\n---\n\n**标签**: `bug`,
    
    \"import-error\",
    \"critical\",
    \"blocking\"\n**优先级**: 🔴 P0 - 阻塞",
    
            "labels": ["bug", "import-error", "critical", "blocking"]
        }

        # Issue 5: 修复依赖注入容器问题
        issue5 = {
            "title": "修复依赖注入容器导入错误 - di.py",
            "body": "## 🧩 依赖注入容器导入错误修复\n\n### 📋 问题描述\n`src/core/di.py`模块中的`Container`类无法正常导入，影响依赖注入功能。\n\n### 🔍 具体错误\n```\nImportError: cannot import name 'Container' from 'src.core.di'\n```\n\n### 🎯 修复目标\n- [ ] 修复Container类的定义\n- [ ] 确保依赖注入接口正确\n- [ ] 修复模块导入路径\n- [ ] 验证依赖注入功能正常\n\n### 📋 验收标准\n- [x] `from src.core.di import Container` 成功\n- [x] 容器可以正常创建和使用\n- [x] 依赖注入功能正常工作\n- [x] 相关服务可以正常注入\n\n### 🔗 影响范围\n- **模块**: `src/core/di.py`\n- **影响**: 依赖注入系统、服务管理\n- **优先级**: 🔴高优先级\n- **预估时间**: 30-60分钟\n\n---\n\n**标签**: \"bug\", \"dependency-injection\", \"import-error\", \"high-priority\"\n**优先级**: 🟡 P1 - 高优先级",
            "labels": ["bug", "dependency-injection", "import-error", "high-priority"]
        }

        # Issue 6: 修复测试文件导入错误
        issue6 = {
            "title": "修复测试文件导入错误 - 33个测试文件无法执行",
            "body": "## 🧪 测试文件导入错误修复\n\n### 📋 问题描述\n33个测试文件无法执行，主要由于语法错误和导入路径问题。\n\n### 🔍 受影响的测试文件\n**单元测试** (18个):\n- `tests/unit/test_api_endpoints.py`\n- `tests/unit/test_config.py`\n- `tests/unit/domain/test_models.py`\n- `tests/unit/services/test_prediction_service.py`\n- [其他14个文件...]\n\n**集成测试** (15个):\n- `tests/integration/test_api_routers_enhanced.py`\n- `tests/integration/test_core_functionality.py`\n- `tests/integration/test_domain_prediction_comprehensive.py`\n- [其他12个文件...]\n\n### 🎯 修复目标\n- [ ] 修复测试文件的语法错误\n- [ ] 更新测试文件导入路径\n- [ ] 修复测试依赖问题\n- [ ] 确保所有测试可以正常执行\n\n### 📋 验收标准\n- [x] `pytest tests/unit/ -v` 无错误\n- [x] `pytest tests/integration/ -v` 无错误\n- [x] 测试覆盖率报告正常生成\n- [x] 至少20个测试用例可以执行\n\n### 🔗 影响范围\n- **模块**: `tests/` 目录下33个文件\n- **影响**: 测试验证、质量保证\n- **优先级**: 🔴 高优先级\n- **预估时间**: 2-3小时\n\n---\n\n**标签**: \"bug\",
    
    \"test\",
    \"import-error\",
    \"high-priority\"\n**优先级**: 🟡 P1 - 高优先级",
    
            "labels": ["bug", "test", "import-error", "high-priority"]
        }

        # Issue 7: 修复Ruff配置警告
        issue7 = {
            "title": "修复Ruff配置警告 - pyproject.toml配置更新",
            "body": "## ⚙️ Ruff配置警告修复\n\n### 📋 问题描述\n`pyproject.toml`中的Ruff配置使用了已废弃的顶级配置项，需要更新为新的配置结构。\n\n### 🔍 具体警告\n```\nwarning: The top-level linter settings are deprecated in favour of their counterparts in the `lint` section. Please update the following options in `pyproject.toml`:\n- 'ignore' -> 'lint.ignore'\n- 'select' -> 'lint.select'\n```\n\n### 🎯 修复目标\n- [x] 已将顶级配置移动到`[tool.ruff.lint]`部分\n- [ ] 验证Ruff配置无警告\n- [ ] 确保代码检查工具正常工作\n- [ ] 更新相关文档\n\n### 📋 验收标准\n- [x] `ruff check src/ --no-exit-code` 无警告\n- [x] `ruff format src/` 正常格式化\n- [x] 代码质量检查功能正常\n- [x] 配置文档已更新\n\n### 🔗 影响范围\n- **文件**: `pyproject.toml`\n- **影响**: 代码检查、格式化工具\n- **优先级**: 🟡 中优先级\n- **预估时间**: 15分钟\n\n---\n\n**标签**: \"configuration\", \"ruff\", \"linter\", \"low-priority\"\n**优先级**: 🟢 P2 - 低优先级",
            "labels": ["configuration", "ruff", "linter", "low-priority"]
        }

        # Issue 8: 恢复单元测试执行 - 目标50个测试用例
        issue8 = {
            "title": "恢复单元测试执行 - 目标50个测试用例",
            "body": "## 🧪 恢复单元测试执行\n\n### 📋 问题描述\n由于语法错误，当前单元测试无法执行。需要恢复基础的单元测试执行能力。\n\n### 🎯 阶段1目标: 基础测试恢复 (20个测试)\n- [ ] 修复核心模块测试文件导入\n- [ ] 恢复基础服务测试\n- [ ] 恢复API端点测试\n- [ ] 确保至少20个测试用例可以执行\n\n### 🎯 阶段2目标: 测试用例扩展 (50个测试用例)\n- [ ] 生成缺失的测试用例\n- [ ] 提升测试覆盖率到25%\n- [ ] 添加边界条件和异常测试\n- [ ] 确保测试覆盖核心业务逻辑\n\n### 📋 验收标准\n- [ ] `pytest tests/unit/ -v` 至少20个测试通过\n- [ ] 测试覆盖率报告正常生成\n- [ ] 核心模块测试覆盖率>20%\n- [ ] 测试执行时间<2分钟\n\n### 🔗 影响范围\n- **模块**: `tests/unit/` 目录\n- **影响**: 单元测试、质量保证\n- **优先级**: 🔴 高优先级\n- **预估时间**: 1-2天\n\n---\n\n**标签**: \"enhancement\", \"test\", \"unit-test\", \"high-priority\"\n**优先级**: 🟡 P1 - 高优先级",
            "labels": ["enhancement", "test", "unit-test", "high-priority"]
        }

        # Issue 9: 提升集成测试覆盖率 - 目标15个集成测试
        issue9 = {
            "title": "提升集成测试覆盖率 - 目标15个集成测试",
            "body": "## 🔗 提升集成测试覆盖率\n\n### 📋 问题描述\n集成测试由于语法错误无法执行，需要恢复并扩展集成测试覆盖。\n\n### 🎯 阶段1目标: 基础集成测试恢复 (8个测试)\n- [ ] 修复API集成测试文件\n- [ ] 恢复数据库集成测试\n- [ ] 恢复缓存集成测试\n- [ ] 确保至少8个集成测试可以执行\n\n### 🎯 阶段2目标: 集成测试扩展 (15个测试用例)\n- [ ] 生成缺失的集成测试\n- [ ] 提升API端点集成测试覆盖\n- [ ] 添加数据库事务集成测试\n- [ ] 实现缓存一致性测试\n- [ ] 确保集成测试覆盖率>15%\n\n### 📋 验收标准\n- [ ] `pytest tests/integration/ -v` 至少8个测试通过\n- [ ] 集成测试报告正常生成\n- [ ] API集成测试覆盖率>15%\n- [ ] 集成测试执行时间<5分钟\n\n### 🔗 影响范围\n- **模块**: `tests/integration/` 目录\n- **影响**: 集成测试、端到端测试\n- **优先级**: 🟡 中优先级\n- **预估时间**: 1-2天\n\n---\n\n**标签**: \"enhancement\", \"test\", \"integration-test\", \"medium-priority\"\n**优先级**: 🟡 P2 - 中优先级",
            "labels": ["enhancement", "test", "integration-test", "medium-priority"]
        }

        # Issue 10: 修复Bandit安全警告
        issue10 = {
            "title": "修复Bandit安全扫描警告",
            "body": "## 🔒 修复Bandit安全扫描警告\n\n### 📋 问题描述\nBandit安全扫描检测到多个安全问题需要修复，主要涉及测试名称解析和注释处理。\n\n### 🔍 检测到的警告\n- `[manager] WARNING Test in comment: using is not a test name or id, ignoring`\n- `[manager] WARNING Test in comment: quoted_name is not a test name or id, ignoring`\n- `[manager] WARNING Test in comment: for is not a test name or id, ignoring`\n- `[manager] WARNING Test in comment: safety is not a test name or id, ignoring`\n\n### 🎯 修复目标\n- [ ] 修复测试名称解析问题\n- [ ] 更新测试注释和文档字符串\n- [ ] 确保安全扫描工具正常运行\n- [ ] 实现零高风险安全问题\n\n### 📋 验收标准\n- [ ] `bandit -r src/ --no-exit-code` 无警告\n- [ ] 安全扫描报告显示0个问题\n- [ ] 安全测试覆盖关键模块\n- [ ] 实现零高危安全漏洞\n\n### 🔗 影响范围\n- **模块**: 整个`src/`目录\n- **影响**: 安全检查、安全合规\n- **优先级**: 🟡 中优先级\n- **预估时间**: 1-2小时\n\n---\n\n**标签**: \"security\", \"bandit\", \"medium-priority\"\n**优先级**: 🟡 P2 - 中优先级",
            "labels": ["security", "bandit", "medium-priority"]
        }

        # Issue 11: 提升测试覆盖率到30%
        issue11 = {
            "title": "提升测试覆盖率到30% - 使用覆盖率分析工具",
            "body": "## 📊 提升测试覆盖率到30%\n\n### 📋 问题描述\n当前测试覆盖率由于语法错误无法准确测量，需要使用覆盖率分析工具来提升测试覆盖率。\n\n### 🎯 阶段1目标: 基础覆盖率恢复 (15%)\n- [ ] 运行覆盖率分析工具\n- [ ] 识别未测试的代码模块\n- [ ] 生成基础测试用例\n- [ ] 实现15%的代码覆盖率\n\n### 🎯 阶段2目标: 目标覆盖率提升 (30%)\n- [ ] 扩展测试覆盖到核心业务逻辑\n- [ ] 添加边界条件测试\n- [ ] 实现异常处理测试\n- [ ] 生成详细的覆盖率报告\n\n### 📋 验收标准\n- [ ] 覆盖率报告显示>30%\n- [ ] 核心模块覆盖率>50%\n- [ ] 覆盖率报告可以正常生成\n- [ ] 测试用例数量增加到200+\n\n### 🔗 影响范围\n- **模块**: 整个项目代码库\n- **影响**: 测试覆盖率、质量保证\n- **优先级**: 🟡 中优先级\n- **预估时间**: 2-3天\n\n---\n\n**标签**: \"enhancement\",
    
    \"coverage\",
    \"test-quality\",
    \"medium-priority\"\n**优先级**: 🟡 P2 - 中优先级",
    
            "labels": ["enhancement", "coverage", "test-quality", "medium-priority"]
        }

        self.issues = [issue1, issue2, issue3, issue4, issue5, issue6, issue7, issue8, issue9, issue10, issue11]

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

        script_content = f'''#!/bin/bash
# 批量创建GitHub Issues脚本
# 生成时间: {datetime.now().isoformat()}

echo "🚀 开始批量创建GitHub Issues..."

'''

        for i, issue in enumerate(self.issues, 1):
            # 转义body中的特殊字符
            escaped_body = issue['body'].replace('"', '\\"').replace('$', '\\$')
            script_content += f'''
# 创建 Issue #{i}: {issue['title']}
echo "创建 Issue #{i}: {issue['title']}..."
gh issue create \\
  --title "{issue['title']}" \\
  --body "{escaped_body}" \\
  --repo xupeng211/FootballPrediction \\
  --label "{', '.join(issue['labels'])}"
echo "Issue #{i} 创建完成"
'''

        script_content += '''
echo "✅ 所有Issues创建完成！"
echo "🎯 总共创建了''' + str(len(self.issues)) + '''个Issues"
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

    # 创建所有Issues
    creator.create_all_issues()

    # 生成报告
    report = creator.generate_issues_report()

    # 创建执行脚本
    creator.create_github_issues_batch()

    print(f"\\n🎯 Issues创建完成！")
    print(f"📊 总Issues数: {len(creator.issues)}")

    print("\\n📊 Issues分布:")
    print("  - P0 (阻塞):", len([i for i in creator.issues if "P0" in i["labels"]]))
    print("  - P1 (高):", len([i for i in creator.issues if "P1" in i["labels"]]))
    print("  - P2 (中):", len([i for i in creator.issues if "P2" in i["labels"]]))
    print("  - 低优先级:",
    len([i for i in creator.issues if "low-priority" in i["labels"]]))

    print(f"\\n⏰ 总预估时间: 6-10天")
    print("🎯 建议按优先级顺序修复，先解决P0和P1级别问题。")

if __name__ == "__main__":
    main()