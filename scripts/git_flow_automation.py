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
                pass

            result = subprocess.run(
                command,
                check=True,
                capture_output=True,
                text=True
            )

            if show_output and result.stdout:
                pass

            return True
        except subprocess.CalledProcessError as e:
            if show_output:
                if e.stderr:
                    pass
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
            return False

        feature_branch = f"{self.config['feature_prefix']}{name}"

        if self.current_branch != self.config["develop_branch"]:
            if not self.run_git_command(['git',
    'checkout',
    self.config['develop_branch']]):
                return False

        if not self.run_git_command(['git',
    'pull',
    'origin',
    self.config['develop_branch']]):
            return False

        if not self.run_git_command(['git', 'checkout', '-b', feature_branch]):
            return False


        return True

    def finish_feature(self, name: str) -> bool:
        """完成功能开发"""
        feature_branch = f"{self.config['feature_prefix']}{name}"

        if self.current_branch == feature_branch:
            if not self.run_git_command(['git',
    'checkout',
    self.config['develop_branch']]):
                return False

        if not self.run_git_command(['git',
    'pull',
    'origin',
    self.config['develop_branch']]):
            return False

        if not self.run_git_command(['git', 'merge', feature_branch, '--no-ff']):
            return False

        self.run_git_command(['git', 'branch', '-d', feature_branch])

        if not self.run_git_command(['git',
    'push',
    'origin',
    self.config['develop_branch']]):
            return False

        return True

    def start_release(self, version: str) -> bool:
        """开始发布准备"""
        if not re.match(r'^v\d+\.\d+\.\d+(-.+)?$', version):
            return False

        release_branch = f"{self.config['release_prefix']}{version}"

        if self.current_branch != self.config["develop_branch"]:
            if not self.run_git_command(['git',
    'checkout',
    self.config['develop_branch']]):
                return False

        if not self.run_git_command(['git',
    'pull',
    'origin',
    self.config['develop_branch']]):
            return False

        if not self.run_git_command(['git', 'checkout', '-b', release_branch]):
            return False


        return True

    def finish_release(self, version: str) -> bool:
        """完成发布"""
        release_branch = f"{self.config['release_prefix']}{version}"

        if not self.run_git_command(['git', 'checkout', self.config['main_branch']]):
            return False

        if not self.run_git_command(['git',
    'pull',
    'origin',
    self.config['main_branch']]):
            return False

        if not self.run_git_command(['git', 'merge', release_branch, '--no-ff']):
            return False

        if not self.run_git_command(['git', 'tag', version]):
            return False

        if not self.run_git_command(['git',
    'push',
    'origin',
    self.config['main_branch']]):
            return False
        if not self.run_git_command(['git', 'push', 'origin', version]):
            return False

        if not self.run_git_command(['git', 'checkout', self.config['develop_branch']]):
            return False
        if not self.run_git_command(['git', 'merge', release_branch, '--no-ff']):
            return False
        if not self.run_git_command(['git',
    'push',
    'origin',
    self.config['develop_branch']]):
            return False

        self.run_git_command(['git', 'branch', '-d', release_branch])

        return True

    def start_hotfix(self, name: str) -> bool:
        """开始热修复"""
        if not self.validate_branch_name(name, self.config["hotfix_prefix"]):
            return False

        hotfix_branch = f"{self.config['hotfix_prefix']}{name}"

        if self.current_branch != self.config["main_branch"]:
            if not self.run_git_command(['git',
    'checkout',
    self.config['main_branch']]):
                return False

        if not self.run_git_command(['git',
    'pull',
    'origin',
    self.config['main_branch']]):
            return False

        if not self.run_git_command(['git', 'checkout', '-b', hotfix_branch]):
            return False


        return True

    def finish_hotfix(self, name: str) -> bool:
        """完成热修复"""
        hotfix_branch = f"{self.config['hotfix_prefix']}{name}"

        if not self.run_git_command(['git', 'checkout', self.config['main_branch']]):
            return False

        if not self.run_git_command(['git',
    'pull',
    'origin',
    self.config['main_branch']]):
            return False

        if not self.run_git_command(['git', 'merge', hotfix_branch, '--no-ff']):
            return False

        # 生成版本号
        import datetime
        today = datetime.datetime.now().strftime("%Y.%m.%d")
        patch_version = f"v{today}-hotfix"

        if not self.run_git_command(['git', 'tag', patch_version]):
            return False

        if not self.run_git_command(['git',
    'push',
    'origin',
    self.config['main_branch']]):
            return False
        if not self.run_git_command(['git', 'push', 'origin', patch_version]):
            return False

        if not self.run_git_command(['git', 'checkout', self.config['develop_branch']]):
            return False
        if not self.run_git_command(['git', 'merge', hotfix_branch, '--no-ff']):
            return False
        if not self.run_git_command(['git',
    'push',
    'origin',
    self.config['develop_branch']]):
            return False

        self.run_git_command(['git', 'branch', '-d', hotfix_branch])

        return True

    def show_status(self) -> bool:
        """显示当前Git状态"""

        # 获取所有分支
        try:
            result = subprocess.run(
                ["git", "branch", "-a"],
                capture_output=True,
                text=True,
                check=True
            )
            branches = result.stdout.strip().split('\n')

            for branch in branches:
                branch = branch.replace('*', '').strip()
                if branch.startswith('remotes/origin/'):
                    branch = branch[13:]  # 移除 'remotes/origin/'

                if branch == self.config['main_branch']:
                    pass
                elif branch == self.config['develop_branch']:
                    pass
                elif branch.startswith(self.config['feature_prefix']):
                    pass
                elif branch.startswith(self.config['release_prefix']):
                    pass
                elif branch.startswith(self.config['hotfix_prefix']):
                    pass

        except subprocess.CalledProcessError:
            pass

        return True

    def init_git_flow(self) -> bool:
        """初始化Git Flow配置"""

        # 检查是否为Git仓库
        if not Path('.git').exists():
            return False

        # 创建配置文件
        config_file = Path(__file__).parent / "git_flow_config.json"
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)


        for _key, _value in self.config.items():
            pass

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
            sys.exit(1)

    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
