#!/usr/bin/env python3
"""
🚀 测试覆盖率危机解决方案启动器
一键启动所有修复工具和改进流程
"""

import sys
import subprocess
import time
from pathlib import Path

class TestCrisisSolutionLauncher:
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.scripts = {
            "fix_test_crisis.py": "紧急修复测试错误",
            "github_issue_manager.py": "维护GitHub issues",
            "test_quality_improvement_engine.py": "质量提升引擎"
        }

    def show_banner(self):
        """显示启动横幅"""
        print("""
╔══════════════════════════════════════════════════════════════╗
║                 🚨 测试覆盖率危机解决方案                      ║
║                                                              ║
║  当前状态: 8.21%覆盖率 | 7,992个测试用例 | 5个错误           ║
║  目标状态: 30%覆盖率 | 高质量测试 | 0个错误                   ║
╚══════════════════════════════════════════════════════════════╝
        """)

    def show_menu(self):
        """显示操作菜单"""
        print("🎯 选择要执行的操作:")
        print()

        print("🔥 紧急修复 (推荐先执行)")
        print("  1. 修复测试收集错误 (P0优先级)")
        print("  2. 修复Import冲突问题")
        print("  3. 清理Python缓存文件")
        print()

        print("📊 分析和规划")
        print("  4. 分析测试质量和覆盖率")
        print("  5. 生成改进计划")
        print("  6. 查看当前状态报告")
        print()

        print("🚀 质量提升")
        print("  7. 执行阶段1: 修复问题测试")
        print("  8. 执行阶段2: 核心模块深度测试")
        print("  9. 执行阶段3: 边界条件测试")
        print(" 10. 执行阶段4: 集成测试增强")
        print()

        print("🔧 维护工具")
        print(" 11. 更新GitHub Issues")
        print(" 12. 生成完整报告")
        print()

        print("🎯 完整流程")
        print(" 13. 运行完整的4阶段改进流程")
        print(" 14. 一键修复+改进 (推荐)")
        print()

        print("  0. 退出")
        print()

    def run_script(self, script_name: str, args: list = None) -> bool:
        """运行指定脚本"""
        script_path = self.project_root / script_name
        if not script_path.exists():
            print(f"❌ 脚本不存在: {script_path}")
            return False

        cmd = ["python", str(script_path)]
        if args:
            cmd.extend(args)

        print(f"🚀 执行: {' '.join(cmd)}")
        print("-" * 50)

        try:
            result = subprocess.run(cmd, cwd=self.project_root, text=True)

            if result.returncode == 0:
                print("✅ 执行成功")
                return True
            else:
                print(f"⚠️ 执行有警告或错误 (返回码: {result.returncode})")
                if result.stderr:
                    print(f"错误信息: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            print("⏰ 执行超时")
            return False
        except Exception as e:
            print(f"❌ 执行异常: {e}")
            return False
        finally:
            print("-" * 50)
            time.sleep(1)  # 短暂暂停，便于观察结果

    def execute_option(self, choice: str):
        """执行用户选择的操作"""
        if choice == "0":
            print("👋 退出解决方案")
            return False

        try:
            choice_num = int(choice)
        except ValueError:
            print("❌ 无效选择，请输入数字")
            return True

        if choice_num == 1:
            # 修复测试收集错误
            self.run_script("fix_test_crisis.py")

        elif choice_num == 2:
            # 修复Import冲突
            print("🔧 修复Import冲突...")
            self.run_script("fix_test_crisis.py")

        elif choice_num == 3:
            # 清理缓存
            print("🧹 清理Python缓存...")
            subprocess.run(["find", ".", "-name", "__pycache__", "-type", "d", "-exec", "rm", "-rf", "{}", "+"],
                         cwd=self.project_root, capture_output=True)
            subprocess.run(["find", ".", "-name", "*.pyc", "-delete"],
                         cwd=self.project_root, capture_output=True)
            print("✅ 缓存清理完成")

        elif choice_num == 4:
            # 分析测试质量
            print("📊 分析测试质量...")
            self.run_script("test_quality_improvement_engine.py", ["--analyze"])

        elif choice_num == 5:
            # 生成改进计划
            print("📋 生成改进计划...")
            self.run_script("test_quality_improvement_engine.py", ["--analyze"])

        elif choice_num == 6:
            # 查看状态报告
            print("📈 生成状态报告...")
            self.run_script("github_issue_manager.py", ["--generate-report"])

        elif choice_num == 7:
            # 执行阶段1
            print("🚀 执行阶段1: 修复问题测试")
            self.run_script("test_quality_improvement_engine.py", ["--execute-phase", "1"])

        elif choice_num == 8:
            # 执行阶段2
            print("🎯 执行阶段2: 核心模块深度测试")
            self.run_script("test_quality_improvement_engine.py", ["--execute-phase", "2"])

        elif choice_num == 9:
            # 执行阶段3
            print("🔍 执行阶段3: 边界条件测试")
            self.run_script("test_quality_improvement_engine.py", ["--execute-phase", "3"])

        elif choice_num == 10:
            # 执行阶段4
            print("🔗 执行阶段4: 集成测试增强")
            self.run_script("test_quality_improvement_engine.py", ["--execute-phase", "4"])

        elif choice_num == 11:
            # 更新GitHub Issues
            print("🔧 更新GitHub Issues...")
            self.run_script("github_issue_manager.py")

        elif choice_num == 12:
            # 生成完整报告
            print("📊 生成完整报告...")
            print("🔍 生成测试质量报告...")
            self.run_script("test_quality_improvement_engine.py", ["--report"])
            print("📋 生成状态报告...")
            self.run_script("github_issue_manager.py", ["--generate-report"])

        elif choice_num == 13:
            # 完整4阶段流程
            print("🚀 运行完整的4阶段改进流程...")
            for phase in range(1, 5):
                print(f"\n{'='*60}")
                print(f"执行阶段 {phase}/4")
                print('='*60)
                if not self.run_script("test_quality_improvement_engine.py", ["--execute-phase", str(phase)]):
                    print(f"⚠️ 阶段 {phase} 执行有问题，但继续执行下一阶段")
                time.sleep(2)

            print("\n🎉 完整流程执行完成!")
            print("📊 建议运行 'make coverage' 查看改进效果")

        elif choice_num == 14:
            # 一键修复+改进
            print("🚀 一键修复+改进流程...")
            print("="*60)

            # 步骤1: 紧急修复
            print("步骤 1/4: 紧急修复测试错误")
            self.run_script("fix_test_crisis.py")

            # 步骤2: 分析和规划
            print("\n步骤 2/4: 分析和规划")
            self.run_script("test_quality_improvement_engine.py", ["--analyze"])

            # 步骤3: 执行改进
            print("\n步骤 3/4: 执行质量改进")
            self.run_script("test_quality_improvement_engine.py", ["--execute-phase", "1"])
            self.run_script("test_quality_improvement_engine.py", ["--execute-phase", "2"])

            # 步骤4: 更新问题跟踪
            print("\n步骤 4/4: 更新问题跟踪")
            self.run_script("github_issue_manager.py")

            print("\n" + "="*60)
            print("🎉 一键修复+改进完成!")
            print("\n📊 验证改进效果:")
            print("  make coverage    # 查看覆盖率")
            print("  make test        # 运行测试")
            print("  make test-quick  # 快速测试")

        else:
            print("❌ 无效选择")

        return True

    def run(self):
        """运行启动器"""
        self.show_banner()

        while True:
            self.show_menu()
            choice = input("请选择操作 (0-14): ").strip()

            if not choice:
                continue

            if not self.execute_option(choice):
                break

            print("\n按Enter键继续...")
            input()

def main():
    """主函数"""
    launcher = TestCrisisSolutionLauncher()

    # 支持命令行参数直接执行
    if len(sys.argv) > 1:
        if sys.argv[1] == "--quick-fix":
            launcher.execute_option("14")  # 一键修复
        elif sys.argv[1] == "--analyze":
            launcher.execute_option("4")  # 分析测试质量
        elif sys.argv[1] == "--improve":
            launcher.execute_option("13")  # 完整改进流程
        else:
            print("用法:")
            print("  python launch_test_crisis_solution.py           # 交互模式")
            print("  python launch_test_crisis_solution.py --quick-fix   # 一键修复")
            print("  python launch_test_crisis_solution.py --analyze     # 分析模式")
            print("  python launch_test_crisis_solution.py --improve     # 改进模式")
    else:
        launcher.run()

if __name__ == "__main__":
    main()