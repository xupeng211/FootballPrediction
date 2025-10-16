#!/usr/bin/env python3
"""检查TDD分享会准备情况"""

from pathlib import Path
import json
from datetime import datetime

def check_tdd_session_prep():
    """检查TDD分享会准备情况"""

    print("🎪 TDD分享会准备情况检查")
    print("=" * 60)
    print(f"检查时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # 检查核心材料
    print("📁 核心材料检查：")
    print("-" * 40)

    materials = {
        "docs/tdd_presentations/first_tdd_sharing_session.md": "主演示文稿",
        "docs/tdd_presentations/workshop_solutions.py": "实战演练代码",
        "docs/tdd_presentations/meeting_announcement.md": "会议通知模板",
        "docs/tdd_presentations/feedback_form.md": "反馈表",
        "docs/tdd_presentations/organizing_checklist.md": "组织清单",
        "ANNOUNCEMENT_First_TDD_Sharing_Session.md": "正式会议通知",
        "docs/tdd_presentations/execution_record.md": "执行记录",
        "scripts/run_tdd_sharing_session.py": "执行助手"
    }

    all_ready = True
    for file_path, description in materials.items():
        path = Path(file_path)
        if path.exists():
            size = path.stat().st_size
            print(f"✅ {description}")
            print(f"   路径：{file_path}")
            print(f"   大小：{size} bytes")
        else:
            print(f"❌ {description} - 缺失！")
            all_ready = False
        print()

    # 检查演示代码
    print("\n🔬 演示代码检查：")
    print("-" * 40)

    import subprocess
    try:
        result = subprocess.run(
            ["python", "-m", "pytest",
             "docs/tdd_presentations/workshop_solutions.py",
             "-q", "--tb=no"],
            capture_output=True, text=True,
            cwd="/home/user/projects/FootballPrediction"
        )

        if result.returncode == 0:
            print("✅ 所有演示代码测试通过")
            # 提取测试数量
            output_lines = result.stdout.strip().split('\n')
            for line in output_lines:
                if "passed in" in line:
                    # 提取类似 "9 passed in 0.04s" 中的测试数量
                    import re
                    match = re.search(r'(\d+)\s+passed', line)
                    if match:
                        num_tests = int(match.group(1))
                        print(f"   测试数量：{num_tests}个")
        else:
            print("❌ 演示代码测试失败")
            print(f"   错误：{result.stderr}")
            all_ready = False
    except Exception as e:
        print(f"❌ 无法运行测试：{e}")
        all_ready = False

    # 检查知识库
    print("\n📚 知识库检查：")
    print("-" * 40)

    knowledge_base = {
        "docs/TDD_QUICK_START.md": "TDD快速指南",
        "docs/TDD_KNOWLEDGE_BASE.md": "TDD知识库",
        "docs/TDD_SHARING_SESSION_GUIDE.md": "分享会指南",
        "docs/TDD_CODE_REVIEW_CHECKLIST.md": "代码审查清单",
        "docs/TDD_WEEKLY_REPORT_TEMPLATE.md": "周报模板"
    }

    for file_path, description in knowledge_base.items():
        path = Path(file_path)
        if path.exists():
            print(f"✅ {description}")
        else:
            print(f"⚠️ {description} - 建议准备")

    # 准备就绪总结
    print("\n" + "=" * 60)
    if all_ready:
        print("🎉 准备就绪！可以立即组织TDD分享会")
        print("\n📋 下一步行动：")
        print("1. 发送会议通知（ANNOUNCEMENT_First_TDD_Sharing_Session.md）")
        print("2. 收集参会确认")
        print("3. 会前24小时发送提醒")
        print("4. 使用run_tdd_sharing_session.py协助主持")
    else:
        print("⚠️ 还有材料需要准备")
        print("\n📋 待完成事项：")
        print("1. 补充缺失的材料")
        print("2. 确保演示代码通过")
        print("3. 完成准备后再发送通知")

    # 生成准备报告
    report = {
        "timestamp": datetime.now().isoformat(),
        "all_materials_ready": all_ready,
        "materials_checked": len(materials),
        "materials_ready": sum(1 for f in materials.keys() if Path(f).exists()),
        "knowledge_base_ready": sum(1 for f in knowledge_base.keys() if Path(f).exists())
    }

    report_file = Path("docs/tdd_presentations/prep_report.json")
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)

    print(f"\n📊 准备报告已保存：{report_file}")

if __name__ == "__main__":
    check_tdd_session_prep()
