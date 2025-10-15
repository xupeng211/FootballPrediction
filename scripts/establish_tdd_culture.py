#!/usr/bin/env python3
"""建立TDD文化 - 创建TDD推广材料和工具"""

import os
from pathlib import Path
from datetime import datetime

def create_tdd_resources():
    """创建TDD相关资源"""

    print("📚 建立TDD文化")
    print("=" * 60)

    # 1. 创建TDD检查清单
    checklist_content = """# TDD开发检查清单

## 编写代码前的检查 ✅

- [ ] 编写了失败的测试用例
- [ ] 测试确实失败（不是语法错误）
- [ ] 测试名称清晰地描述了功能
- [ ] 测试覆盖了边界条件

## 编写代码中的检查 🔄

- [ ] 只写了刚好让测试通过的代码
- [ ] 没有过度设计或添加不需要的功能
- [ ] 代码保持了简洁性

## 重构阶段的检查 🔧

- [ ] 所有测试仍然通过
- [ ] 改进了代码设计
- [ ] 消除了重复代码
- [ ] 提高了代码可读性

## 代码质量检查 📋

- [ ] 运行了完整测试套件
- [ ] 检查了代码覆盖率
- [ ] 进行了代码审查
- [ ] 更新了相关文档

## 提交前的检查 ✨

- [ ] 测试覆盖率达到要求
- [ ] 代码符合团队规范
- [ ] 提交信息清晰明确
- [ ] CI/CD检查通过
"""

    with open("docs/TDD_CHECKLIST.md", "w", encoding="utf-8") as f:
        f.write(checklist_content)
    print("✓ 创建TDD检查清单: docs/TDD_CHECKLIST.md")

    # 2. 创建TDD模板生成器
    template_content = '''"""TDD测试模板生成器

用于快速生成符合TDD原则的测试模板。
"""

import os
from pathlib import Path
from typing import Optional


class TDDTemplateGenerator:
    """TDD测试模板生成器"""

    @staticmethod
    def create_test_template(
        module_name: str,
        function_name: str,
        test_type: str = "unit",
        output_dir: Optional[str] = None
    ) -> str:
        """创建测试模板"""

        # 输出目录默认值
        if output_dir is None:
            output_dir = f"tests/unit/{module_name}"

        # 确保目录存在
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        # 生成测试文件路径
        test_file = Path(output_dir) / f"test_{function_name}.py"

        # 生成测试内容
        template = f'''"""
测试 {module_name}.{function_name}
遵循TDD原则：先写失败的测试，再实现功能
"""

import pytest
from unittest.mock import Mock, patch


class Test{function_name.title().replace("_", "")}:
    """测试 {function_name} 功能"""

    def test_{function_name}_basic_case(self):
        """
        测试场景：基本功能测试
        期望：功能正常工作
        """
        # Arrange - 准备测试数据

        # Act - 执行要测试的功能

        # Assert - 验证结果
        assert True  # TODO: 实现具体的测试逻辑

    def test_{function_name}_edge_case(self):
        """
        测试场景：边界条件测试
        期望：正确处理边界情况
        """
        # TODO: 添加边界条件测试
        pass

    def test_{function_name}_error_case(self):
        """
        测试场景：错误处理测试
        期望：优雅地处理错误情况
        """
        # TODO: 添加错误处理测试
        pass

    # TODO: 根据需要添加更多测试用例
'''

        # 写入文件
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(template)

        return str(test_file)

    @staticmethod
    def create_feature_template(
        feature_name: str,
        user_story: str,
        acceptance_criteria: list,
        output_dir: Optional[str] = None
    ) -> str:
        """创建功能测试模板"""

        if output_dir is None:
            output_dir = "tests/features"

        Path(output_dir).mkdir(parents=True, exist_ok=True)

        test_file = Path(output_dir) / f"test_{feature_name}.py"

        criteria_str = "\n        ".join([f"- {c}" for c in acceptance_criteria])

        template = f'''"""
功能测试：{feature_name}

用户故事：{user_story}

验收标准：
        {criteria_str}
"""

import pytest
from unittest.mock import Mock, patch


class Test{feature_name.title().replace(" ", "")}:
    """功能测试：{feature_name}"""

    def test_user_story_fulfilled(self):
        """
        测试完整的用户故事流程
        """
        # TODO: 实现用户故事测试
        pass
'''

        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(template)

        return str(test_file)


# 使用示例
if __name__ == "__main__":
    generator = TDDTemplateGenerator()

    # 创建功能测试模板
    test_file = generator.create_test_template(
        module_name="utils",
        function_name="calculate_prediction",
        test_type="unit"
    )
    print(f"✓ 创建测试模板: {test_file}")

    # 创建功能测试
    feature_file = generator.create_feature_template(
        feature_name="match_prediction",
        user_story="作为一个用户，我想要获取比赛预测结果，以便做出投注决策",
        acceptance_criteria=[
            "系统提供准确的预测结果",
            "预测包含概率信息",
            "响应时间小于1秒"
        ]
    )
    print(f"✓ 创建功能测试模板: {feature_file}")
'''

    with open("scripts/tdd_template_generator.py", "w", encoding="utf-8") as f:
        f.write(template_content)
    print("✓ 创建TDD模板生成器: scripts/tdd_template_generator.py")

    # 3. 创建TDD工作流配置
    workflow_content = """name: TDD Workflow

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  tdd-validation:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements/requirements.txt
        pip install pytest pytest-cov pytest-mock

    - name: Run TDD Validation
      run: |
        # 1. 检查测试是否先于代码
        python scripts/validate_tdd_workflow.py

        # 2. 运行测试套件
        python -m pytest tests/ -v --cov=src --cov-report=xml

        # 3. 检查覆盖率
        python scripts/check_coverage.py --threshold=30

        # 4. 生成TDD报告
        python scripts/generate_tdd_report.py

    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
        flags: unittests
        name: codecov-umbrella
"""

    with open(".github/workflows/tdd-validation.yml", "w", encoding="utf-8") as f:
        f.write(workflow_content)
    print("✓ 创建TDD工作流: .github/workflows/tdd-validation.yml")

    # 4. 创建TDD验证脚本
    validation_content = '''#!/usr/bin/env python3
"""验证TDD工作流程
确保测试先于实现"""

import os
import subprocess
from pathlib import Path
from datetime import datetime


def validate_tdd_workflow():
    """验证TDD工作流程"""

    print("🔍 TDD工作流程验证")
    print("=" * 50)

    # 1. 检查测试覆盖率
    print("\n1. 检查测试覆盖率...")
    result = subprocess.run(
        ["python", "-m", "pytest", "--cov=src", "--cov-report=term-missing", "--tb=no", "-q"],
        capture_output=True,
        text=True
    )

    if result.returncode == 0:
        print("✓ 所有测试通过")
        # 提取覆盖率
        for line in result.stdout.split('\n'):
            if 'TOTAL' in line:
                coverage = line.split()[-1]
                coverage_num = int(coverage.rstrip('%'))
                if coverage_num >= 30:
                    print(f"✓ 覆盖率达到 {coverage}%（超过30%）")
                else:
                    print(f"⚠️ 覆盖率仅 {coverage}%（需要达到30%）")
                break
    else:
        print("✗ 测试失败")
        return False

    # 2. 检查TDD最佳实践
    print("\n2. 检查TDD最佳实践...")

    test_files = list(Path("tests").rglob("test_*.py"))
    src_files = list(Path("src").rglob("*.py"))

    if len(test_files) > 0:
        ratio = len(test_files) / len(src_files) * 100
        print(f"✓ 测试/源代码比率: {ratio:.1f}%")

    # 3. 生成报告
    report = {
        "timestamp": datetime.now().isoformat(),
        "total_tests": len(test_files),
        "total_sources": len(src_files),
        "test_ratio": ratio,
        "status": "PASSED" if result.returncode == 0 else "FAILED"
    }

    with open("tdd_validation_report.json", "w") as f:
        import json
        json.dump(report, f, indent=2)

    print("\n✓ TDD验证完成")
    return True


if __name__ == "__main__":
    validate_tdd_workflow()
'''

    with open("scripts/validate_tdd_workflow.py", "w", encoding="utf-8") as f:
        f.write(validation_content)
    print("✓ 创建TDD验证脚本: scripts/validate_tdd_workflow.py")

    # 5. 创建团队TDD培训材料
    training_content = """# TDD团队培训计划

## 第一周：TDD基础
- [ ] TDD概念介绍
- [ ] Red-Green-Refactor循环
- [ ] 编写第一个TDD测试
- [ ] 练习：简单功能的TDD实现

## 第二周：实践TDD
- [ ] 选择一个实际功能
- [ ] 编写失败的测试
- [ ] 实现最小可工作代码
- [ ] 重构优化

## 第三周：高级TDD
- [ ] Mock和Stub的使用
- [ ] 测试边界条件
- [ ] 异步代码测试
- [ ] 性能测试集成

## 第四周：TDD在项目中
- [ ] 代码审查中的TDD
- [ ] 持续集成中的TDD
- [ ] TDD最佳实践分享
- [ ] 制定团队TDD规范

## 资源
- [TDD指南](docs/TDD_GUIDE.md)
- [TDD检查清单](docs/TDD_CHECKLIST.md)
- [测试模板生成器](scripts/tdd_template_generator.py)
"""

    with open("docs/TDD_TRAINING_PLAN.md", "w", encoding="utf-8") as f:
        f.write(training_content)
    print("✓ 创建TDD培训计划: docs/TDD_TRAINING_PLAN.md")

    print("\n✅ TDD文化建立资源创建完成！")

    # 创建总结
    summary = f"""
# TDD文化建立总结

创建时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 创建的资源：

1. **文档类**
   - TDD检查清单 (docs/TDD_CHECKLIST.md)
   - TDD培训计划 (docs/TDD_TRAINING_PLAN.md)

2. **工具类**
   - TDD模板生成器 (scripts/tdd_template_generator.py)
   - TDD验证脚本 (scripts/validate_tdd_workflow.py)

3. **流程类**
   - GitHub Actions工作流 (.github/workflows/tdd-validation.yml)

## 使用建议：

1. 团队成员阅读TDD指南和检查清单
2. 使用模板生成器快速创建测试
3. 在PR中运行TDD验证
4. 定期进行TDD培训

## 下一步：

1. 推广TDD文化到团队
2. 监控TDD实践情况
3. 持续改进TDD流程
"""

    with open("TDD_CULTURE_SUMMARY.md", "w", encoding="utf-8") as f:
        f.write(summary)
    print("✓ 创建TDD文化总结: TDD_CULTURE_SUMMARY.md")


def run_tdd_workshop():
    """运行TDD工作坊示例"""

    print("\n🎯 运行TDD工作坊示例")
    print("=" * 50)

    # 创建一个简单的TDD示例
    example_dir = Path("examples/tdd_example")
    example_dir.mkdir(parents=True, exist_ok=True)

    # Step 1: Red - 写一个失败的测试
    red_test = '''"""
Step 1: Red - 写一个失败的测试
"""
import pytest


def test_calculator_add():
    """测试计算器加法功能"""
    calc = Calculator()
    result = calc.add(2, 3)
    assert result == 5
'''

    with open(example_dir / "test_calculator_step1.py", "w") as f:
        f.write(red_test)

    # Step 2: Green - 实现最小代码
    green_code = '''"""
Step 2: Green - 实现最小可工作代码
"""
class Calculator:
    def add(self, a, b):
        return a + b
'''

    with open(example_dir / "calculator_step2.py", "w") as f:
        f.write(green_code)

    # Step 3: Refactor - 改进代码
    refactor_code = '''"""
Step 3: Refactor - 改进代码设计
"""
from typing import Union


class Calculator:
    """简单的计算器类"""

    def add(self, a: Union[int, float], b: Union[int, float]) -> Union[int, float]:
        """两数相加"""
        return a + b

    def subtract(self, a: Union[int, float], b: Union[int, float]) -> Union[int, float]:
        """两数相减"""
        return a - b
'''

    with open(example_dir / "calculator_step3.py", "w") as f:
        f.write(refactor_code)

    print("✓ 创建TDD工作坊示例: examples/tdd_example/")
    print("\n📚 TDD示例步骤：")
    print("  1. 失败的测试 (test_calculator_step1.py)")
    print("  2. 最小实现 (calculator_step2.py)")
    print("  3. 重构改进 (calculator_step3.py)")


if __name__ == "__main__":
    create_tdd_resources()
    run_tdd_workshop()

    print("\n🎉 TDD文化建立完成！")
    print("\n📋 后续行动：")
    print("  1. 向团队介绍TDD资源")
    print("  2. 开始使用TDD模板")
    print("  3. 在新功能中实践TDD")
    print("  4. 定期审查TDD实践情况")