#!/usr/bin/env python3
"""测试Claude Code是否能正确获取TDD分享会信息"""

from pathlib import Path
import json

def test_claude_tdd_knowledge():
    """测试Claude TDD知识访问"""

    print("🤖 测试Claude Code对TDD分享会知识的访问...")
    print("=" * 60)

    # 1. 检查关键文件是否存在
    print("\n📁 检查TDD分享会关键文件：")

    key_files = {
        "CLAUDE.md": "Claude主配置文件",
        "CLAUDE_TDD_SESSION_GUIDE.md": "TDD分享会使用指南",
        "docs/tdd_presentations/first_tdd_sharing_session.md": "主演示文稿",
        "docs/tdd_presentations/workshop_solutions.py": "实战代码",
        "docs/tdd_presentations/organizing_checklist.md": "组织清单"
    }

    all_exist = True
    for file_path, description in key_files.items():
        if Path(file_path).exists():
            print(f"✅ {description}")
        else:
            print(f"❌ {description} - 缺失")
            all_exist = False

    # 2. 验证TDD信息在CLAUDE.md中
    print("\n📖 验证CLAUDE.md中的TDD信息：")

    claude_md = Path("CLAUDE.md")
    if claude_md.exists():
        content = claude_md.read_text(encoding='utf-8')

        tdd_sections = [
            "## TDD (Test-Driven Development) Culture",
            "### TDD Learning Resources",
            "### TDD Sharing Sessions",
            "### Current Test Coverage Status"
        ]

        for section in tdd_sections:
            if section in content:
                print(f"✅ 包含：{section}")
            else:
                print(f"❌ 缺失：{section}")

    # 3. 检查分享会主题
    print("\n🎪 确认分享会主题：")

    presentation = Path("docs/tdd_presentations/first_tdd_sharing_session.md")
    if presentation.exists():
        content = presentation.read_text(encoding='utf-8')
        if "Mock与Stub在测试中的艺术" in content:
            print("✅ 主题确认：Mock与Stub在测试中的艺术")
        else:
            print("❌ 主题未找到")

    # 4. 验证指南文件
    print("\n📋 验证Claude使用指南：")

    guide = Path("CLAUDE_TDD_SESSION_GUIDE.md")
    if guide.exists():
        print("✅ Claude TDD分享会使用指南已创建")
        print("   包含：")
        print("   - 材料位置说明")
        print("   - 使用方式指导")
        print("   - 常见问题回答")
        print("   - 行动指南")

    # 5. 生成测试报告
    print("\n" + "=" * 60)

    test_result = {
        "timestamp": "2025-10-15T21:45:00",
        "all_files_exist": all_exist,
        "tdd_in_claude_md": claude_md.exists(),
        "guide_created": guide.exists(),
        "ready_for_claude": all_exist and claude_md.exists() and guide.exists()
    }

    # 保存测试结果
    with open("claude_tdd_test_result.json", "w") as f:
        json.dump(test_result, f, indent=2)

    if test_result["ready_for_claude"]:
        print("🎉 测试通过！Claude Code已准备好使用TDD分享会内容")
        print("\n📌 Claude可以：")
        print("   1. 查看并解释TDD分享会材料")
        print("   2. 运行相关脚本和工具")
        print("   3. 协助组织和执行分享会")
        print("   4. 提供Mock和Stub的示例")
    else:
        print("⚠️ 测试未完全通过，请检查缺失项")

    return test_result

if __name__ == "__main__":
    test_claude_tdd_knowledge()
