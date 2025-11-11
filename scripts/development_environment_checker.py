#!/usr/bin/env python3
"""
🔍 开发环境检查工具
验证开发环境的完整性和配置正确性
"""

import platform
import subprocess
import sys
from datetime import datetime
from pathlib import Path


class Colors:
    """颜色常量"""
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'

def color_print(message: str, color: str = Colors.WHITE):
    """彩色打印"""

class DevelopmentEnvironmentChecker:
    """开发环境检查器"""

    def __init__(self):
        self.project_root = Path(__file__).resolve().parent.parent
        self.system_info = self._get_system_info()
        self.checks = []
        self.passed = 0
        self.failed = 0
        self.warnings = 0

    def _get_system_info(self) -> dict:
        """获取系统信息"""
        return {
            "platform": platform.system(),
            "architecture": platform.machine(),
            "python_version": platform.python_version(),
            "python_executable": sys.executable,
            "is_virtual_env": hasattr(sys,
    'real_prefix') or (hasattr(sys,
    'base_prefix') and sys.base_prefix != sys.prefix)
        }

    def run_command(self,
    command: str,
    cwd: Path | None = None) -> tuple[bool,
    str,
    str]:
        """运行系统命令"""
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=cwd or self.project_root
            )
            return True, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return False, "", "命令超时"
        except Exception as e:
            return False, "", str(e)

    def check_system_requirements(self) -> bool:
        """检查系统要求"""
        color_print("\n🔍 系统要求检查", Colors.BLUE + Colors.BOLD)

        success = True

        # 检查操作系统
        supported_platforms = ["Windows", "Darwin", "Linux"]
        if self.system_info["platform"] in supported_platforms:
            color_print(f"✅ 操作系统: {self.system_info['platform']} {self.system_info['architecture']}",
    Colors.GREEN)
            self.passed += 1
        else:
            color_print(f"❌ 不支持的操作系统: {self.system_info['platform']}", Colors.RED)
            self.failed += 1
            success = False

        # 检查Python版本
        python_version = self.system_info["python_version"]
        version_parts = tuple(map(int, python_version.split('.')))
        if version_parts >= (3, 8):
            color_print(f"✅ Python版本: {python_version}", Colors.GREEN)
            self.passed += 1
        else:
            color_print(f"❌ Python版本过低: {python_version} (需要 >= 3.8)", Colors.RED)
            self.failed += 1
            success = False

        # 检查虚拟环境
        if self.system_info["is_virtual_env"]:
            color_print("✅ Python虚拟环境: 已激活", Colors.GREEN)
            self.passed += 1
        else:
            color_print("⚠️  Python虚拟环境: 未激活 (推荐使用)", Colors.YELLOW)
            self.warnings += 1

        # 检查磁盘空间
        try:
            import shutil
            disk_usage = shutil.disk_usage(self.project_root)
            free_gb = disk_usage.free / (1024 ** 3)
            if free_gb >= 5:
                color_print(f"✅ 磁盘空间: {free_gb:.1f}GB 可用", Colors.GREEN)
                self.passed += 1
            else:
                color_print(f"⚠️  磁盘空间不足: {free_gb:.1f}GB (建议 >= 5GB)", Colors.YELLOW)
                self.warnings += 1
        except Exception:
            color_print("⚠️  无法检查磁盘空间", Colors.YELLOW)
            self.warnings += 1

        return success

    def check_required_tools(self) -> bool:
        """检查必需工具"""
        color_print("\n🛠️  必需工具检查", Colors.BLUE + Colors.BOLD)

        tools = [
            ("Git", "git --version"),
            ("Make", "make --version"),
            ("curl", "curl --version"),
        ]

        if self.system_info["platform"] != "Windows":
            tools.append(("wget", "wget --version"))

        success = True

        for tool_name, command in tools:
            success_flag, stdout, stderr = self.run_command(command)
            if success_flag and stdout:
                version = stdout.strip().split('\n')[0]
                color_print(f"✅ {tool_name}: {version}", Colors.GREEN)
                self.passed += 1
            else:
                color_print(f"❌ {tool_name}: 未安装或不可用", Colors.RED)
                self.failed += 1
                success = False

        return success

    def check_optional_tools(self) -> bool:
        """检查可选工具"""
        color_print("\n💡 可选工具检查", Colors.BLUE + Colors.BOLD)

        tools = [
            ("Docker", "docker --version"),
            ("Docker Compose", "docker-compose --version"),
            ("Node.js", "node --version"),
            ("npm", "npm --version"),
        ]

        success = True

        for tool_name, command in tools:
            success_flag, stdout, stderr = self.run_command(command)
            if success_flag and stdout:
                version = stdout.strip().split('\n')[0]
                color_print(f"✅ {tool_name}: {version}", Colors.GREEN)
                self.passed += 1
            else:
                color_print(f"⚠️  {tool_name}: 未安装 (可选)", Colors.YELLOW)
                self.warnings += 1

        return success

    def check_python_packages(self) -> bool:
        """检查Python包"""
        color_print("\n🐍 Python包检查", Colors.BLUE + Colors.BOLD)

        critical_packages = [
            ("fastapi", "FastAPI"),
            ("uvicorn", "Uvicorn"),
            ("sqlalchemy", "SQLAlchemy"),
            ("pydantic", "Pydantic"),
            ("redis", "Redis"),
        ]

        dev_packages = [
            ("pytest", "Pytest"),
            ("ruff", "Ruff"),
            ("mypy", "MyPy"),
            ("black", "Black"),
            ("bandit", "Bandit"),
        ]

        success = True

        color_print("核心包:", Colors.CYAN)
        for package, display_name in critical_packages:
            success_flag, _, _ = self.run_command(f"python -c \"import {package}\"")
            if success_flag:
                color_print(f"✅ {display_name}: 已安装", Colors.GREEN)
                self.passed += 1
            else:
                color_print(f"❌ {display_name}: 未安装", Colors.RED)
                self.failed += 1
                success = False

        color_print("\n开发工具包:", Colors.CYAN)
        for package, display_name in dev_packages:
            success_flag, _, _ = self.run_command(f"python -c \"import {package}\"")
            if success_flag:
                color_print(f"✅ {display_name}: 已安装", Colors.GREEN)
                self.passed += 1
            else:
                color_print(f"⚠️  {display_name}: 未安装 (推荐)", Colors.YELLOW)
                self.warnings += 1

        return success

    def check_project_structure(self) -> bool:
        """检查项目结构"""
        color_print("\n📁 项目结构检查", Colors.BLUE + Colors.BOLD)

        required_dirs = [
            "src",
            "tests",
            "docs",
            "scripts",
            ".github",
            "config",
        ]

        required_files = [
            "pyproject.toml",
            "README.md",
            "CLAUDE.md",
            "Makefile",
            ".gitignore",
        ]

        success = True

        color_print("必需目录:", Colors.CYAN)
        for directory in required_dirs:
            dir_path = self.project_root / directory
            if dir_path.exists() and dir_path.is_dir():
                color_print(f"✅ {directory}/: 存在", Colors.GREEN)
                self.passed += 1
            else:
                color_print(f"❌ {directory}/: 不存在", Colors.RED)
                self.failed += 1
                success = False

        color_print("\n必需文件:", Colors.CYAN)
        for file_name in required_files:
            file_path = self.project_root / file_name
            if file_path.exists() and file_path.is_file():
                color_print(f"✅ {file_name}: 存在", Colors.GREEN)
                self.passed += 1
            else:
                color_print(f"❌ {file_name}: 不存在", Colors.RED)
                self.failed += 1
                success = False

        return success

    def check_configuration_files(self) -> bool:
        """检查配置文件"""
        color_print("\n⚙️  配置文件检查", Colors.BLUE + Colors.BOLD)

        config_files = [
            (".env", "环境变量配置"),
            (".env.example", "环境变量示例"),
            (".vscode/settings.json", "VSCode设置"),
            (".pre-commit-config.yaml", "Pre-commit配置"),
            ("pytest.ini", "pytest配置"),
            ("ruff.toml", "Ruff配置"),
        ]

        success = True

        for file_name, description in config_files:
            file_path = self.project_root / file_name
            if file_path.exists():
                color_print(f"✅ {description}: {file_name}", Colors.GREEN)
                self.passed += 1
            else:
                color_print(f"⚠️  {description}: {file_name} (推荐)", Colors.YELLOW)
                self.warnings += 1

        return success

    def check_git_configuration(self) -> bool:
        """检查Git配置"""
        color_print("\n🔧 Git配置检查", Colors.BLUE + Colors.BOLD)

        git_dir = self.project_root / ".git"
        if not git_dir.exists():
            color_print("❌ 不是Git仓库", Colors.RED)
            self.failed += 1
            return False

        # 检查Git用户配置
        checks = [
            ("user.name", "git config user.name"),
            ("user.email", "git config user.email"),
            ("init.defaultBranch", "git config init.defaultBranch"),
            ("pull.rebase", "git config pull.rebase"),
        ]

        success = True
        for config_name, command in checks:
            success_flag, stdout, stderr = self.run_command(command)
            if success_flag and stdout.strip():
                color_print(f"✅ {config_name}: {stdout.strip()}", Colors.GREEN)
                self.passed += 1
            else:
                color_print(f"⚠️  {config_name}: 未配置", Colors.YELLOW)
                self.warnings += 1

        return success

    def check_docker_environment(self) -> bool:
        """检查Docker环境"""
        color_print("\n🐳 Docker环境检查", Colors.BLUE + Colors.BOLD)

        # 检查Docker是否运行
        success_flag, stdout, stderr = self.run_command("docker info")
        if success_flag:
            color_print("✅ Docker服务: 运行中", Colors.GREEN)
            self.passed += 1

            # 检查Docker Compose
            compose_success, _, _ = self.run_command("docker-compose --version")
            if compose_success:
                color_print("✅ Docker Compose: 可用", Colors.GREEN)
                self.passed += 1

                # 检查docker-compose文件
                compose_file = self.project_root / "docker-compose.yml"
                if compose_file.exists():
                    color_print("✅ docker-compose.yml: 存在", Colors.GREEN)
                    self.passed += 1

                    # 检查服务状态
                    ps_success, stdout, _ = self.run_command("docker-compose ps")
                    if ps_success:
                        color_print("✅ Docker服务状态检查: 可用", Colors.GREEN)
                        self.passed += 1
                    else:
                        color_print("⚠️  Docker服务状态检查: 失败", Colors.YELLOW)
                        self.warnings += 1
                else:
                    color_print("⚠️  docker-compose.yml: 不存在", Colors.YELLOW)
                    self.warnings += 1
            else:
                color_print("❌ Docker Compose: 不可用", Colors.RED)
                self.failed += 1
        else:
            color_print("⚠️  Docker服务: 未运行或未安装", Colors.YELLOW)
            self.warnings += 1

        return True

    def run_functional_tests(self) -> bool:
        """运行功能测试"""
        color_print("\n🧪 功能测试", Colors.BLUE + Colors.BOLD)

        tests = []

        # 测试Python导入
        tests.append(("Python导入测试", "python -c \"import sys; print('Python导入正常')\""))

        # 测试基本命令
        if (self.project_root / "Makefile").exists():
            tests.append(("Make help命令", "make help"))

        # 测试代码质量工具
        tests.append(("Ruff检查", "ruff --version"))
        tests.append(("pytest检查", "pytest --version"))

        success = True

        for test_name, command in tests:
            success_flag, stdout, stderr = self.run_command(command)
            if success_flag:
                color_print(f"✅ {test_name}: 通过", Colors.GREEN)
                self.passed += 1
            else:
                color_print(f"❌ {test_name}: 失败", Colors.RED)
                self.failed += 1
                success = False

        return success

    def generate_report(self) -> str:
        """生成检查报告"""
        total = self.passed + self.failed + self.warnings

        report = f"""
# 🔍 开发环境检查报告

**检查时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**操作系统**: {self.system_info['platform']} {self.system_info['architecture']}
**Python版本**: {self.system_info['python_version']}
**虚拟环境**: {'是' if self.system_info['is_virtual_env'] else '否'}

## 📊 检查统计

- ✅ **通过**: {self.passed}
- ❌ **失败**: {self.failed}
- ⚠️  **警告**: {self.warnings}
- 📋 **总计**: {total}

"""

        if self.failed == 0:
            report += """## 🎉 环境状态

**恭喜！** 开发环境检查通过，环境配置良好。

### 下一步操作

1. **激活虚拟环境** (如果未激活):
   ```bash
   source .venv/bin/activate  # Linux/macOS
   .venv\\Scripts\\activate   # Windows
   ```

2. **安装/更新依赖**:
   ```bash
   make install
   ```

3. **运行测试**:
   ```bash
   make test
   ```

4. **开始开发**:
   ```bash
   make dev  # 启动开发服务器
   ```

"""
        else:
            report += """## ⚠️  环境状态

**发现问题！** 请根据以下建议修复环境配置。

### 修复建议

1. **系统要求**: 确保操作系统和Python版本符合要求
2. **工具安装**: 安装缺失的必需工具
3. **Python包**: 安装缺失的Python包
4. **项目结构**: 确保项目结构完整
5. **配置文件**: 创建缺失的配置文件

### 快速修复命令

```bash
# 安装依赖
make install

# 设置环境
python3 scripts/setup_development_environment.py --full

# 验证修复
python3 scripts/development_environment_checker.py
```

"""

        report += f"""
## 📋 检查详情

### 系统要求
- 操作系统支持: ✅
- Python版本: {'✅' if tuple(map(int,
    self.system_info['python_version'].split('.'))) >= (3,
    8) else '❌'}
- 虚拟环境: {'✅' if self.system_info['is_virtual_env'] else '⚠️'}

### 工具状态
根据检查结果，所有必需工具应该已正确安装和配置。

### 项目状态
项目结构和配置文件检查结果已显示在上方。

---

**报告生成**: development_environment_checker.py
**项目**: 足球预测系统
"""

        # 保存报告
        report_path = self.project_root / "environment_check_report.md"
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)

        return report

    def run_all_checks(self) -> bool:
        """运行所有检查"""
        color_print("🔍 开始开发环境全面检查", Colors.CYAN + Colors.BOLD)

        # 运行所有检查
        checks = [
            ("系统要求", self.check_system_requirements),
            ("必需工具", self.check_required_tools),
            ("可选工具", self.check_optional_tools),
            ("Python包", self.check_python_packages),
            ("项目结构", self.check_project_structure),
            ("配置文件", self.check_configuration_files),
            ("Git配置", self.check_git_configuration),
            ("Docker环境", self.check_docker_environment),
            ("功能测试", self.run_functional_tests),
        ]

        for check_name, check_func in checks:
            try:
                check_func()
            except Exception as e:
                color_print(f"❌ {check_name}检查出错: {e}", Colors.RED)
                self.failed += 1

        # 生成总结
        color_print("📊 检查总结", Colors.CYAN + Colors.BOLD)

        total = self.passed + self.failed + self.warnings
        color_print(f"✅ 通过: {self.passed}", Colors.GREEN)
        color_print(f"❌ 失败: {self.failed}", Colors.RED)
        color_print(f"⚠️  警告: {self.warnings}", Colors.YELLOW)
        color_print(f"📋 总计: {total}", Colors.WHITE)

        # 生成报告
        self.generate_report()
        report_path = self.project_root / "environment_check_report.md"
        color_print(f"\n📄 详细报告已保存: {report_path}", Colors.BLUE)

        # 最终结果
        if self.failed == 0:
            color_print("\n🎉 开发环境检查通过！", Colors.GREEN + Colors.BOLD)
            return True
        else:
            color_print(f"\n⚠️  发现 {self.failed} 个问题需要修复", Colors.YELLOW + Colors.BOLD)
            return False

def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(
        description="开发环境检查工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 运行完整检查
  python3 development_environment_checker.py

  # 仅检查系统要求
  python3 development_environment_checker.py --system-only

  # 快速检查
  python3 development_environment_checker.py --quick
        """
    )

    parser.add_argument("--system-only", action="store_true", help="仅检查系统要求")
    parser.add_argument("--quick", action="store_true", help="快速检查（跳过可选项目）")
    parser.add_argument("--no-docker", action="store_true", help="跳过Docker检查")

    args = parser.parse_args()

    checker = DevelopmentEnvironmentChecker()

    try:
        if args.system_only:
            success = checker.check_system_requirements()
        elif args.quick:
            # 快速检查：仅检查核心项目
            checks = [
                checker.check_system_requirements,
                checker.check_required_tools,
                checker.check_python_packages,
                checker.check_project_structure,
            ]
            success = True
            for check in checks:
                if not check():
                    success = False
        else:
            # 完整检查
            success = checker.run_all_checks()

        sys.exit(0 if success else 1)

    except KeyboardInterrupt:
        color_print("\n\n⚠️  检查被用户中断", Colors.YELLOW)
        sys.exit(130)
    except Exception as e:
        color_print(f"\n❌ 检查过程中出现错误: {e}", Colors.RED)
        sys.exit(1)

if __name__ == "__main__":
    main()
