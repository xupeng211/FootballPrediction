#!/usr/bin/env python3
"""
演示远程Issues创建流程
Demo Remote Issues Creation Process
"""

import json
import subprocess
import sys


def check_prerequisites():
    """检查先决条件"""
    print("🔍 检查先决条件...")

    # 检查GitHub CLI
    try:
        result = subprocess.run(["gh", "--version"], capture_output=True, check=True)
        print(f"✅ GitHub CLI: {result.stdout.strip()}")
    except:
        print("❌ GitHub CLI未安装")
        return False

    # 检查认证
    try:
        result = subprocess.run(["gh", "auth", "status"], capture_output=True, check=True)
        print("✅ GitHub CLI已认证")
    except:
        print("❌ GitHub CLI未认证")
        return False

    # 检查Issues数据文件
    files_exist = True
    for filename in ["generated_issues.json", "test_improvement_issues.json"]:
        try:
            with open(filename) as f:
                data = json.load(f)
                print(f"✅ {filename}: {len(data)}个Issues")
        except FileNotFoundError:
            print(f"❌ {filename}: 文件不存在")
            files_exist = False

    return files_exist


def show_preview():
    """显示预览信息"""
    print("\n📊 Issues预览:")
    print("=" * 50)

    # 加载Issues数据
    try:
        with open("generated_issues.json") as f:
            main_issues = json.load(f)

        with open("test_improvement_issues.json") as f:
            test_issues = json.load(f)

        all_issues = main_issues + test_issues

        # 统计
        critical_count = sum(1 for i in all_issues if "critical" in i.get("labels", []))
        high_count = sum(1 for i in all_issues if "high" in i.get("labels", []))
        medium_count = sum(1 for i in all_issues if "medium" in i.get("labels", []))

        print(f"📈 总计: {len(all_issues)}个Issues")
        print(f"🚨 Critical: {critical_count}个")
        print(f"🔥 High: {high_count}个")
        print(f"⚡ Medium: {medium_count}个")

        print("\n📝 前5个Issues预览:")
        for i, issue in enumerate(all_issues[:5], 1):
            print(f"{i}. {issue['title']}")
            print(f"   🏷️  {', '.join(issue['labels'])}")

    except Exception as e:
        print(f"❌ 预览失败: {e}")


def show_sample_commands():
    """显示示例命令"""
    print("\n🛠️ 使用示例:")
    print("=" * 50)

    print("1. 交互式创建（推荐首次使用）:")
    print("   python3 create_remote_github_issues.py")
    print()

    print("2. 直接指定仓库:")
    print("   python3 create_remote_github_issues.py --repo yourusername/yourrepo")
    print()

    print("3. 批量模式（跳过确认）:")
    print("   python3 create_remote_github_issues.py --repo yourusername/yourrepo --batch")
    print()

    print("4. 查看帮助:")
    print("   python3 create_remote_github_issues.py --help")
    print()

    print("⚠️  注意事项:")
    print("- 确保对目标仓库有写入权限")
    print("- Issues一旦创建需要手动删除")
    print("- 脚本内置延迟机制避免API限制")


def main():
    """主函数"""
    print("🚀 远程GitHub Issues创建演示")
    print("=" * 50)

    # 检查先决条件
    if not check_prerequisites():
        print("\n❌ 先决条件不满足，请解决后重试")
        print("💡 参考: CREATE_REMOTE_ISSUES_GUIDE.md")
        return False

    # 显示预览
    show_preview()

    # 显示示例命令
    show_sample_commands()

    print("\n🎯 准备完成！")
    print("💡 现在可以运行以下命令开始创建Issues:")
    print("   python3 create_remote_github_issues.py")

    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
