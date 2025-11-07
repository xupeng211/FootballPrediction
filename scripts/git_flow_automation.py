#!/usr/bin/env python3
"""
🌊 Git Flow 自动化工具
简化Git Flow工作流程的常用操作
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path


class GitFlowAutomation:
    """Git Flow自动化工具"""

    def __init__(self):
        self.current_branch = self._get_current_branch()
        self.config = self._load_config()

    def _load_config(self) -> dict:
        """加载配置文件"""
        config_file = Path(__file__).parent / "git_flow_config.json"
        if config_file.exists():
            with open(config_file, encoding='utf-8') as f:
                return json.load(f)
        return {
            "main_branch": "main",
            "develop_branch": "develop",
            "feature_prefix": "feature/",
            "release_prefix": "release/",
            "hotfix_prefix": "hotfix/",
            "support_prefix": "support/"
        }

    def _get_current_branch(self) -> str:
        """获取当前分支名称"""
        try:
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return "unknown"

    def run_git_command(self, command: list[str], show_output: bool = True) -> bool:
        """执行Git命令"""
        try:
            if show_output:
                print(f"🔄 执行: {' '.join(command)}")

            result = subprocess.run(
                command,
                check=True,
                capture_output=True,
                text=True
            )

            if show_output and result.stdout:
                print(result.stdout)

            return True
        except subprocess.CalledProcessError as e:
            if show_output:
                print(f"❌ 命令失败: {' '.join(command)}")
                if e.stderr:
                    print(f"错误信息: {e.stderr}")
            return False

    def validate_branch_name(self, name: str, prefix: str) -> bool:
        """验证分支名称格式"""
        if not name:
            return False

        # 检查是否已包含前缀
        if name.startswith(prefix):
            name = name[len(prefix):]

        # 基本验证：只允许字母、数字、连字符和下划线
        pattern = r'^[a-zA-Z0-9][a-zA-Z0-9_-]*[a-zA-Z0-9]$|^v\d+\.\d+\.\d+$'
        return bool(re.match(pattern, name))

    def start_feature(self, name: str) -> bool:
        """开始功能开发"""
        if not self.validate_branch_name(name, self.config["feature_prefix"]):
            print(f"❌ 无效的功能分支名称: {name}")
            print("分支名称应该只包含字母、数字、连字符和下划线")
            return False

        feature_branch = f"{self.config['feature_prefix']}{name}"

        if self.current_branch != self.config["develop_branch"]:
            print(f"🔄 切换到 {self.config['develop_branch']} 分支...")
            if not self.run_git_command(['git',
    'checkout',
    self.config['develop_branch']]):
                return False

        print(f"📥 拉取最新的 {self.config['develop_branch']} 分支...")
        if not self.run_git_command(['git',
    'pull',
    'origin',
    self.config['develop_branch']]):
            return False

        print(f"🚀 创建功能分支: {feature_branch}")
        if not self.run_git_command(['git', 'checkout', '-b', feature_branch]):
            return False

        print(f"✅ 功能分支 {feature_branch} 创建成功！")
        print("\n📝 后续步骤:")
        print("1. 进行功能开发")
        print("2. 定期提交代码:")
        print("   git add .")
        print("   git commit -m 'feat: 描述你的变更'")
        print("3. 开发完成后推送分支:")
        print(f"   git push origin {feature_branch}")
        print("4. 创建Pull Request到develop分支")

        return True

    def finish_feature(self, name: str) -> bool:
        """完成功能开发"""
        feature_branch = f"{self.config['feature_prefix']}{name}"

        if self.current_branch == feature_branch:
            print("🔄 切换到develop分支...")
            if not self.run_git_command(['git',
    'checkout',
    self.config['develop_branch']]):
                return False

        print("📥 拉取最新的develop分支...")
        if not self.run_git_command(['git',
    'pull',
    'origin',
    self.config['develop_branch']]):
            return False

        print(f"🔄 合并功能分支 {feature_branch} 到 develop...")
        if not self.run_git_command(['git', 'merge', feature_branch, '--no-ff']):
            return False

        print(f"🗑️  删除功能分支 {feature_branch}...")
        self.run_git_command(['git', 'branch', '-d', feature_branch])

        print("📤 推送更新到远程develop分支...")
        if not self.run_git_command(['git',
    'push',
    'origin',
    self.config['develop_branch']]):
            return False

        print("✅ 功能开发完成！")
        return True

    def start_release(self, version: str) -> bool:
        """开始发布准备"""
        if not re.match(r'^v\d+\.\d+\.\d+(-.+)?$', version):
            print(f"❌ 无效的版本号格式: {version}")
            print("版本号格式示例: v1.0.0, v1.2.3-beta.1")
            return False

        release_branch = f"{self.config['release_prefix']}{version}"

        if self.current_branch != self.config["develop_branch"]:
            print(f"🔄 切换到 {self.config['develop_branch']} 分支...")
            if not self.run_git_command(['git',
    'checkout',
    self.config['develop_branch']]):
                return False

        print("📥 拉取最新的develop分支...")
        if not self.run_git_command(['git',
    'pull',
    'origin',
    self.config['develop_branch']]):
            return False

        print(f"🚀 创建发布分支: {release_branch}")
        if not self.run_git_command(['git', 'checkout', '-b', release_branch]):
            return False

        print(f"✅ 发布分支 {release_branch} 创建成功！")
        print("\n📝 后续步骤:")
        print("1. 更新版本号和CHANGELOG")
        print("2. 修复发现的发布问题")
        print("3. 进行最终测试")
        print("4. 完成发布:")
        print(f"   python3 {__file__} release-finish {version}")

        return True

    def finish_release(self, version: str) -> bool:
        """完成发布"""
        release_branch = f"{self.config['release_prefix']}{version}"

        print(f"🔄 切换到 {self.config['main_branch']} 分支...")
        if not self.run_git_command(['git', 'checkout', self.config['main_branch']]):
            return False

        print(f"📥 拉取最新的 {self.config['main_branch']} 分支...")
        if not self.run_git_command(['git',
    'pull',
    'origin',
    self.config['main_branch']]):
            return False

        print(f"🔄 合并发布分支 {release_branch} 到 main...")
        if not self.run_git_command(['git', 'merge', release_branch, '--no-ff']):
            return False

        print(f"🏷️  创建标签 {version}...")
        if not self.run_git_command(['git', 'tag', version]):
            return False

        print("📤 推送main分支和标签到远程...")
        if not self.run_git_command(['git',
    'push',
    'origin',
    self.config['main_branch']]):
            return False
        if not self.run_git_command(['git', 'push', 'origin', version]):
            return False

        print("🔄 同步到develop分支...")
        if not self.run_git_command(['git', 'checkout', self.config['develop_branch']]):
            return False
        if not self.run_git_command(['git', 'merge', release_branch, '--no-ff']):
            return False
        if not self.run_git_command(['git',
    'push',
    'origin',
    self.config['develop_branch']]):
            return False

        print(f"🗑️  删除发布分支 {release_branch}...")
        self.run_git_command(['git', 'branch', '-d', release_branch])

        print(f"✅ 版本 {version} 发布完成！")
        return True

    def start_hotfix(self, name: str) -> bool:
        """开始热修复"""
        if not self.validate_branch_name(name, self.config["hotfix_prefix"]):
            print(f"❌ 无效的热修复分支名称: {name}")
            return False

        hotfix_branch = f"{self.config['hotfix_prefix']}{name}"

        if self.current_branch != self.config["main_branch"]:
            print(f"🔄 切换到 {self.config['main_branch']} 分支...")
            if not self.run_git_command(['git',
    'checkout',
    self.config['main_branch']]):
                return False

        print(f"📥 拉取最新的 {self.config['main_branch']} 分支...")
        if not self.run_git_command(['git',
    'pull',
    'origin',
    self.config['main_branch']]):
            return False

        print(f"🚀 创建热修复分支: {hotfix_branch}")
        if not self.run_git_command(['git', 'checkout', '-b', hotfix_branch]):
            return False

        print(f"✅ 热修复分支 {hotfix_branch} 创建成功！")
        print("\n📝 后续步骤:")
        print("1. 快速修复问题")
        print("2. 本地测试验证")
        print("3. 完成热修复:")
        print(f"   python3 {__file__} hotfix-finish {name}")

        return True

    def finish_hotfix(self, name: str) -> bool:
        """完成热修复"""
        hotfix_branch = f"{self.config['hotfix_prefix']}{name}"

        print(f"🔄 切换到 {self.config['main_branch']} 分支...")
        if not self.run_git_command(['git', 'checkout', self.config['main_branch']]):
            return False

        print(f"📥 拉取最新的 {self.config['main_branch']} 分支...")
        if not self.run_git_command(['git',
    'pull',
    'origin',
    self.config['main_branch']]):
            return False

        print(f"🔄 合并热修复分支 {hotfix_branch} 到 main...")
        if not self.run_git_command(['git', 'merge', hotfix_branch, '--no-ff']):
            return False

        # 生成版本号
        import datetime
        today = datetime.datetime.now().strftime("%Y.%m.%d")
        patch_version = f"v{today}-hotfix"

        print(f"🏷️  创建热修复标签 {patch_version}...")
        if not self.run_git_command(['git', 'tag', patch_version]):
            return False

        print("📤 紧急推送到远程...")
        if not self.run_git_command(['git',
    'push',
    'origin',
    self.config['main_branch']]):
            return False
        if not self.run_git_command(['git', 'push', 'origin', patch_version]):
            return False

        print("🔄 同步到develop分支...")
        if not self.run_git_command(['git', 'checkout', self.config['develop_branch']]):
            return False
        if not self.run_git_command(['git', 'merge', hotfix_branch, '--no-ff']):
            return False
        if not self.run_git_command(['git',
    'push',
    'origin',
    self.config['develop_branch']]):
            return False

        print(f"🗑️  删除热修复分支 {hotfix_branch}...")
        self.run_git_command(['git', 'branch', '-d', hotfix_branch])

        print(f"✅ 热修复 {name} 完成并发布！")
        print(f"🏷️  标签: {patch_version}")
        return True

    def show_status(self) -> bool:
        """显示当前Git状态"""
        print("🌊 Git Flow 状态")
        print("=" * 50)
        print(f"当前分支: {self.current_branch}")

        # 获取所有分支
        try:
            result = subprocess.run(
                ["git", "branch", "-a"],
                capture_output=True,
                text=True,
                check=True
            )
            branches = result.stdout.strip().split('\n')

            print("\n📋 分支状态:")
            for branch in branches:
                branch = branch.replace('*', '').strip()
                if branch.startswith('remotes/origin/'):
                    branch = branch[13:]  # 移除 'remotes/origin/'

                if branch == self.config['main_branch']:
                    print(f"  🔵 {branch} (main)")
                elif branch == self.config['develop_branch']:
                    print(f"  🟡 {branch} (develop)")
                elif branch.startswith(self.config['feature_prefix']):
                    print(f"  🟢 {branch} (feature)")
                elif branch.startswith(self.config['release_prefix']):
                    print(f"  🟠 {branch} (release)")
                elif branch.startswith(self.config['hotfix_prefix']):
                    print(f"  🔴 {branch} (hotfix)")

        except subprocess.CalledProcessError:
            print("❌ 无法获取分支信息")

        return True

    def init_git_flow(self) -> bool:
        """初始化Git Flow配置"""
        print("🚀 初始化Git Flow配置...")

        # 检查是否为Git仓库
        if not Path('.git').exists():
            print("❌ 当前目录不是Git仓库")
            return False

        # 创建配置文件
        config_file = Path(__file__).parent / "git_flow_config.json"
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)

        print("✅ Git Flow配置初始化完成！")
        print(f"配置文件: {config_file}")

        print("\n📋 配置:")
        for key, value in self.config.items():
            print(f"  {key}: {value}")

        return True

def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='Git Flow 自动化工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 开始功能开发
  python3 git_flow_automation.py feature-start user-authentication

  # 开始发布准备
  python3 git_flow_automation.py release-start v1.2.0

  # 开始热修复
  python3 git_flow_automation.py hotfix-start security-fix

  # 查看状态
  python3 git_flow_automation.py status

  # 初始化配置
  python3 git_flow_automation.py init
        """
    )

    parser.add_argument('command', choices=[
        'feature-start', 'feature-finish',
        'release-start', 'release-finish',
        'hotfix-start', 'hotfix-finish',
        'status', 'init'
    ], help='Git Flow命令')

    parser.add_argument('name', nargs='?', help='功能/发布/修复名称')

    args = parser.parse_args()

    automation = GitFlowAutomation()

    if args.command == 'init':
        success = automation.init_git_flow()
    elif args.command == 'status':
        success = automation.show_status()
    elif args.name is None:
        print(f"❌ 命令 '{args.command}' 需要名称参数")
        parser.print_help()
        sys.exit(1)
    else:
        command_map = {
            'feature-start': automation.start_feature,
            'feature-finish': automation.finish_feature,
            'release-start': automation.start_release,
            'release-finish': automation.finish_release,
            'hotfix-start': automation.start_hotfix,
            'hotfix-finish': automation.finish_hotfix,
        }

        if args.command in command_map:
            success = command_map[args.command](args.name)
        else:
            print(f"❌ 未知命令: {args.command}")
            sys.exit(1)

    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
