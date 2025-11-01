#!/usr/bin/env python3
"""
深入分析 skipped 测试
"""

import subprocess
import re
import sys
import os
import json
from pathlib import Path


def analyze_skipped_tests():
    """分析 skipped 测试的详细信息"""
    print("\n🔍 深入分析 skipped 测试...")
    print("=" * 80)

    env = os.environ.copy()
    env["PYTHONPATH"] = "tests:src"
    env["TESTING"] = "true"

    # 1. 收集所有 skipped 测试
    print("\n1. 收集 skipped测试信息...")

    # 运行pytest收集所有测试，包括skipped的
    cmd = [
        "pytest",
        "-v",
        "--disable-warnings",
        "--rs",  # 显示跳过原因
        "--collect-only",
        "tests",
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300, env=env)
    output = result.stdout + result.stderr

    # 收集测试详情
    test_details = []
    lines = output.split("\n")

    for line in lines:
        # 检查是否是测试行
        if "::" in line and ("SKIPPED" in line or "skipif" in line):
            if "SKIP" in line:
                parts = line.split()
                test_name = parts[0].strip()
                status = "SKIPPED"

                # 查找跳过原因
                skip_reason = "未知原因"
                i = lines.index(line)
                # 查看后面的行以获取详细原因
                for j in range(i + 1, min(i + 10, len(lines))):
                    if lines[j].strip().startswith("[Skipped]"):
                        skip_reason = lines[j].strip()
                        break
                    elif lines[j].strip().startswith("Reason:"):
                        skip_reason = lines[j].strip()
                        break

                test_details.append(
                    {
                        "test": test_name,
                        "status": status,
                        "reason": skip_reason,
                        "module": test_name.split("::")[0],
                    }
                )

    print(f"收集到 {len(test_details)} 个 skipped 测试")

    # 2. 分类分析
    print("\n2. 分类分析...")

    categories = {
        "占位测试": [],
        "依赖缺失": [],
        "配置相关": [],
        "环境相关": [],
        "条件不满足": [],
        "其他": [],
    }

    for test in test_details:
        reason = test["reason"].lower()
        module = test["module"]

        # 根据原因分类
        if any(keyword in reason for keyword in ["placeholder", "占位", "not implemented"]):
            categories["占位测试"].append(test)
        elif any(keyword in reason for keyword in ["not available", "不可用", "missing", "依赖"]):
            categories["依赖缺失"].append(test)
        elif any(keyword in reason for keyword in ["config", "配置", "env", "环境"]):
            categories["配置相关"].append(test)
        elif any(keyword in reason for keyword in ["condition", "条件", "false", "true"]):
            categories["条件不满足"].append(test)
        else:
            categories["其他"].append(test)

    # 打印分类结果
    for category, tests in categories.items():
        if tests:
            print(f"\n{category} ({len(tests)} 个):")
            for test in tests[:5]:  # 只显示前5个
                print(f"  - {test['test']}")
                print(f"    原因: {test['reason']}")
            if len(tests) > 5:
                print(f"  ... 还有 {len(tests)-5} 个")

    # 3. 识别可以修复的测试
    print("\n3. 识别可以修复的测试...")

    fixable_tests = []

    for test in test_details:
        reason = test["reason"].lower()
        module = test["module"]

        # 这些原因的测试可能可以通过修复来解决
        if any(
            keyword in reason
            for keyword in [
                "import",
                "missing",
                "依赖",
                "dependency",
                "not available",
                "config",
                "配置",
                "环境",
                "skipif",
                "临时禁用",
            ]
        ):
            fixable_tests.append(test)

    print(f"\n可以尝试修复的测试: {len(fixable_tests)}")

    # 4. 生成修复建议
    print("\n4. 修复建议...")

    fix_suggestions = {}

    for test in fixable_tests:
        module = test["module"]
        test_name = test["test"]
        reason = test["reason"]

        # 根据模块生成修复建议
        if module not in fix_suggestions:
            fix_suggestions[module] = {
                "tests": [],
                "common_issues": set(),
                "suggested_fixes": set(),
            }

        fix_suggestions[module]["tests"].append(test)

        # 分析常见问题
        if "import" in reason:
            fix_suggestions[module]["common_issues"].add("导入错误")
            fix_suggestions[module]["suggested_fixes"].add("添加必要的导入或mock")
        elif "missing" in reason or "依赖" in reason:
            fix_suggestions[module]["common_issues"].add("依赖缺失")
            fix_suggestions[module]["suggested_fixes"].add("添加依赖的mock")
        elif "config" in reason or "配置" in reason:
            fix_suggestions[module]["common_issues"].add("配置问题")
            fix_suggestions[module]["suggested_fixes"].add("修复配置或mock")
        elif "skipif" in reason:
            fix_suggestions[module]["common_issues"].add("skipif条件")
            fix_suggestions[module]["suggested_fixes"].add("��化或移除skipif")

    # 打印修复建议
    print("\n按模块的修复建议:")
    for module, info in fix_suggestions.items():
        print(f"\n{module}:")
        print(f"  待修复测试数: {len(info['tests'])}")
        if info["common_issues"]:
            print(f"  常见问题: {', '.join(info['common_issues'])}")
        if info["suggested_fixes"]:
            print(f"  建议修复: {', '.join(info['suggested_fixes'])}")

    return {
        "total_skipped": len(test_details),
        "categories": categories,
        "fixable": fixable_tests,
        "fix_suggestions": fix_suggestions,
    }


def create_fix_plan(skipped_data):
    """创建修复计划"""
    print("\n📋 创建修复计划...")

    plan_content = f"""# Skipped 测试修复计划

生成时间: {subprocess.check_output(['date'], text=True).strip()}

## 📊 统计信息

- 总 skipped 测试数: {skipped_data['total_skipped']}
- 可修复测试数: {len(skipped_data['fixable'])}
- 占位测试数: {len(skipped_data['categories']['占位测试'])}

## 🎯 修复目标

1. **目标1**: 将 skipped 测试数减少到 10 个以下
2. **目标2**: 修复所有可修复的测试
3. **目标3**: 保留必要的占位测试

## 🔧 修复任务

"""

    # 按模块组织修复任务
    task_number = 1
    for module, info in skipped_data["fix_suggestions"].items():
        plan_content += f"\n### {task_number}. 修复 {module} 模块\n\n"

        plan_content += "待修复的测试:\n"
        for test in info["tests"][:5]:  # 最多显示5个
            plan_content += f"- `{test['test']}` - {test['reason']}\n"

        if len(info["tests"]) > 5:
            plan_content += f"- ... 还有 {len(info['tests'])-5} 个\n"

        plan_content += "\n修复建议:\n"
        for fix in info["suggested_fixes"]:
            plan_content += f"- {fix}\n"

        plan_content += "\n" + "-" * 50 + "\n"
        task_number += 1

    plan_content += """
## 📝 修复步骤

### 步骤 1: 添加缺失的导入和Mock
```python
# 在测试文件顶部添加
import sys
sys.path.insert(0, 'src')

# 在conftest.py或测试文件中添加mock
from unittest.mock import MagicMock, patch
```

### 步骤 2: 简化或移除不必要的skipif
```python
# 将
@pytest.mark.skipif(not CONDITION, reason="...")
# 改为
@pytest.mark.skipif(False, reason="临时禁用 - 待修复")
```

### 步骤 3: 添加必要的fixture
```python
@pytest.fixture
def mock_service():
    return MagicMock()
```

## ✅ 验证清单

- [ ] 修复所有依赖缺失的测试
- [ ] 移除临时禁用的skipif
- [ ] 确保修复后的测试能够通过
- [ ] 运行验证：skipped < 10

## 🚀 执行命令

```bash
# 验证skipped测试数量
python scripts/count_skipped_tests.py

# 运行特定模块的测试
pytest tests/unit/path/to/module.py -v

# 运行所有测试并检查
pytest -v --tb=short | grep "SKIPPED"
```

## 📝 备注

- 优先修复核心业务逻辑的测试
- 占位测试可以保留，但应该标记清楚
- 每修复一批测试后，更新此计划
- 使用 Claude Code 可以自动生成修复代码
"""

    # 写入文件
    os.makedirs("docs/_reports", exist_ok=True)
    with open("docs/_reports/SKIPPED_TESTS_FIX_PLAN.md", "w", encoding="utf-8") as f:
        f.write(plan_content)

    print("✅ 修复计划已生成: docs/_reports/SKIPPED_TESTS_FIX_PLAN.md")


def create_count_script():
    """创建计数脚本"""
    script_content = '''#!/usr/bin/env python3
"""
统计 skipped测试数量
"""

import subprocess
import re
import sys
import os

def count_skipped_tests():
    """统计 skipped测试数量"""
    env = os.environ.copy()
    env['PYTHONPATH'] = 'tests:src'
    env['TESTING'] = 'true'

    # 运行测试
    cmd = [
        "pytest",
        "-v",
        "--disable-warnings",
        "--tb=no"
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=180, env=env)
    output = result.stdout + result.stderr

    # 统计
    skipped = len(re.findall(r"SKIPPED", output))
    total = len(re.findall(r"(PASSED|FAILED|ERROR|SKIPPED)", output))

    print(f"\\n跳过测试统计:")
    print(f"  跳过: {skipped}")
    print(f"  总计: {total}")
    print(f"  跳过率: {skipped/total*100:.1f}%" if total > 0 else "0.0%")

    # 如果设置阈值
    if len(sys.argv) > 1 and sys.argv[1] == "--fail-threshold":
        threshold = int(sys.argv[2])
        if skipped > threshold:
            print(f"\\n❌ 跳过测试数 ({skipped}) 超过阈值 ({threshold})")
            sys.exit(1)
        else:
            print(f"\\n✅ 跳过测试数 ({skipped}) 在阈值范围内 ({threshold})")

    return skipped

if __name__ == "__main__":
    count_skipped_tests()
'''

    with open("scripts/count_skipped_tests.py", "w", encoding="utf-8") as f:
        f.write(script_content)

    print("✅ 创建了计数脚本: scripts/count_skipped_tests.py")


def main():
    """主函数"""
    print("=" * 80)
    print("Phase 6.2: 分析并减少 skipped 测试")
    print("=" * 80)
    print("目标：跳过测试数 < 10")
    print("-" * 80)

    # 1. 分析 skipped 测试
    skipped_data = analyze_skipped_tests()

    # 2. 创建修复计划
    create_fix_plan(skipped_data)

    # 3. 创建计数脚本
    create_count_script()

    # 4. 运行验证
    print("\n" + "=" * 80)
    print("当前 skipped 测试数验证:")

    os.chmod("scripts/count_skipped_tests.py", 0o755)
    result = subprocess.run(
        ["python", "scripts/count_skipped_tests.py"], capture_output=True, text=True
    )
    print(result.stdout)

    # 5. 总结
    print("\n" + "=" * 80)
    print("Phase 6.2 分析完成:")
    print(f"  - 总 skipped 测试: {skipped_data['total_skipped']}")
    print(f"  - 可修复测试: {len(skipped_data['fixable'])}")
    print(f"  - 占位测试: {len(skipped_data['categories']['占位测试'])}")
    print("\n下一步:")
    print("   1. 查看修复计划: docs/_reports/SKIPPED_TESTS_FIX_PLAN.md")
    print("  2. 按计划修复测试")
    print("  3. 使用: python scripts/count_skipped_tests.py 验证")

    if skipped_data["total_skipped"] <= 20:
        print("\n✅ Skipped 测试数量较少，可以开始修复")
    else:
        print("\n⚠️  Skipped 测试较多，建议分批修复")


if __name__ == "__main__":
    main()
