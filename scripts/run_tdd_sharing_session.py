#!/usr/bin/env python3
"""TDD分享会执行助手
协助主持人顺利执行TDD分享会
"""

import time
from datetime import datetime, timedelta
from pathlib import Path

class TDDSharingSessionRunner:
    """TDD分享会执行助手"""

    def __init__(self):
        self.agenda = [
            {"time": "16:00", "duration": 5, "title": "开场 & TDD进展汇报", "speaker": "主持人"},
            {"time": "16:05", "duration": 5, "title": "TDD小贴士：测试命名艺术", "speaker": "志愿者"},
            {"time": "16:10", "duration": 20, "title": "主题分享：Mock vs Stub", "speaker": "主讲人"},
            {"time": "16:30", "duration": 10, "title": "实战演练", "speaker": "全体参与"},
            {"time": "16:40", "duration": 5, "title": "自由讨论 & 总结", "speaker": "全体"}
        ]
        self.materials_dir = Path("docs/tdd_presentations")

    def show_session_info(self):
        """显示分享会信息"""
        print("🎪 TDD分享会：Mock与Stub在测试中的艺术")
        print("=" * 60)
        print(f"日期：{datetime.now().strftime('%Y-%m-%d')}")
        print(f"时间：16:00-16:45（45分钟）")
        print(f"主题：Mock与Stub在测试中的艺术")
        print("=" * 60)

    def show_agenda(self):
        """显示议程"""
        print("\n📋 会议议程：")
        print("-" * 60)

        current_time = datetime.now().replace(hour=16, minute=0, second=0)

        for item in self.agenda:
            start_time = current_time.strftime("%H:%M")
            end_time = (current_time + timedelta(minutes=item["duration"])).strftime("%H:%M")

            print(f"{start_time}-{end_time} | {item['title']} ({item['duration']}分钟)")
            print(f"           分享人：{item['speaker']}")

            current_time += timedelta(minutes=item["duration"])

    def show_materials(self):
        """显示需要准备的材料"""
        print("\n📁 所需材料：")
        print("-" * 60)

        materials = [
            "first_tdd_sharing_session.md - 主演示文稿",
            "workshop_solutions.py - 实战演练代码",
            "feedback_form.md - 反馈表",
            "meeting_announcement.md - 会议通知模板"
        ]

        for material in materials:
            file_path = self.materials_dir / material
            status = "✅" if file_path.exists() else "❌"
            print(f"{status} {material}")

    def show_tips(self):
        """显示主持技巧"""
        print("\n💡 主持技巧：")
        print("-" * 60)

        tips = [
            "1. 控制时间：每个环节严格按时间表进行",
            "2. 鼓励参与：主动点名让安静的同学发言",
            "3. 记录要点：指定专人记录关键讨论点",
            "4. 营造氛围：保持轻松、鼓励犯错和提问",
            "5. 准备备用：准备好应对技术故障的方案"
        ]

        for tip in tips:
            print(f"   {tip}")

    def run_timer(self, segment_name, duration_minutes):
        """运行计时器"""
        print(f"\n⏱️  {segment_name} 开始！({duration_minutes}分钟)")
        print("按Enter开始计时...")
        input()

        start_time = time.time()
        end_time = start_time + duration_minutes * 60

        print(f"\n⏰ 计时中...剩余时间：")

        while time.time() < end_time:
            remaining = int(end_time - time.time())
            minutes = remaining // 60
            seconds = remaining % 60

            # 使用\r覆盖上一行
            print(f"\r   {minutes:02d}:{seconds:02d}", end="", flush=True)
            time.sleep(1)

        print("\n\n✅ 时间到！")

    def generate_session_summary(self):
        """生成会议纪要模板"""
        summary = f"""# TDD分享会纪要

**日期**：{datetime.now().strftime('%Y年%m月%d日')}
**主题**：Mock与Stub在测试中的艺术
**参与人数**：[待填写]
**主持人**：[待填写]

## 📊 出席情况

- 开发团队：[ ]人
- 测试团队：[ ]人
- 其他：[ ]人

## 🎯 主要内容

### 1. TDD进展汇报
- string_utils模块：100%覆盖率 ✅
- helpers模块：100%覆盖率 ✅
- predictions模块：93%覆盖率 ✅
- 下一步目标：提升dict_utils覆盖率

### 2. TDD小贴士：测试命名艺术
- 使用描述性命名
- 遵循"should/when"模式
- 避免模糊的测试名称

### 3. Mock vs 核心概念
- **Stub**：提供测试数据，不验证交互
- **Mock**：验证行为和交互
- 选择原则：根据测试目的选择合适的工具

### 4. 实战演练
- 天气预报服务测试
- 文件上传功能测试
- 邮件发送服务测试

## 💡 关键讨论点

1.
2.
3.

## 📝 行动项

| 事项 | 负责人 | 截止日期 |
|------|--------|----------|
|      |        |          |
|      |        |          |

## 🎯 下次会议

**主题**：[待定]
**时间**：[待定]
**分享人**：[待报名]

## 📎 附件

- [演示文稿](first_tdd_sharing_session.md)
- [实战代码](workshop_solutions.py)
- [反馈汇总](feedback_summary.md)

---
*纪要整理人：[姓名]*
*整理时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""

        summary_file = Path("docs/tdd_presentations/session_summary_template.md")
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write(summary)

        print(f"\n📝 会议纪要模板已生成：{summary_file}")

    def check_preparation(self):
        """检查准备工作"""
        print("\n✅ 准备工作检查清单：")
        print("-" * 60)

        checklist = [
            ("✅", "演示材料准备完成"),
            ("✅", "实战代码测试通过"),
            ("✅", "会议通知已发送"),
            ("⏳", "会议室已预订"),
            ("⏳", "线上链接已准备"),
            ("⏳", "参会人员已确认"),
            ("⏳", "技术设备已测试")
        ]

        for status, item in checklist:
            print(f"   {status} {item}")

        print("\n📌 注意事项：")
        print("   - 提前15分钟进入会议室")
        print("   - 测试屏幕共享功能")
        print("   - 准备备用网络连接")
        print("   - 打开所有需要的文件和标签页")

def main():
    """主函数"""
    runner = TDDSharingSessionRunner()

    print("🚀 TDD分享会执行助手")
    print("=" * 60)

    while True:
        print("\n请选择操作：")
        print("1. 查看分享会信息")
        print("2. 查看会议议程")
        print("3. 检查材料准备")
        print("4. 查看主持技巧")
        print("5. 运行计时器")
        print("6. 生成会议纪要模板")
        print("7. 检查准备工作")
        print("0. 退出")

        choice = input("\n请输入选项（0-7）：")

        if choice == "1":
            runner.show_session_info()
        elif choice == "2":
            runner.show_agenda()
        elif choice == "3":
            runner.show_materials()
        elif choice == "4":
            runner.show_tips()
        elif choice == "5":
            segment = input("请输入环节名称：")
            duration = int(input("请输入时长（分钟）："))
            runner.run_timer(segment, duration)
        elif choice == "6":
            runner.generate_session_summary()
        elif choice == "7":
            runner.check_preparation()
        elif choice == "0":
            print("\n祝分享会成功！🎉")
            break
        else:
            print("\n无效选项，请重新选择。")

if __name__ == "__main__":
    main()
