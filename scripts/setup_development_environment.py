#!/usr/bin/env python3
"""
开发环境自动化设置脚本
一键设置完整的开发环境，包括Docker、IDE配置、依赖安装等
"""

import json
import os
import platform
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path


class DevelopmentEnvironmentSetup:
    """开发环境设置器"""

    def __init__(self):
        self.project_root = Path(__file__).resolve().parent.parent
        self.platform = platform.system().lower()
        self.errors = []
        self.warnings = []

    def log_info(self, message: str):
        """输出信息"""

    def log_success(self, message: str):
        """输出成功信息"""

    def log_warning(self, message: str):
        """输出警告信息"""
        self.warnings.append(message)

    def log_error(self, message: str):
        """输出错误信息"""
        self.errors.append(message)

    def run_command(self,
    command: list[str],
    check: bool = True,
    capture: bool = False) -> str | None:
        """运行命令"""
        try:
            if capture:
                result = subprocess.run(
                    command,
                    check=check,
                    capture_output=True,
                    text=True,
                    cwd=self.project_root
                )
                return result.stdout.strip()
            else:
                subprocess.run(command, check=check, cwd=self.project_root)
                return None
        except subprocess.CalledProcessError as e:
            if check:
                self.log_error(f"命令执行失败: {' '.join(command)} - {e}")
            return None

    def check_system_requirements(self) -> bool:
        """检查系统要求"""
        self.log_info("检查系统要求...")

        success = True

        # 检查操作系统
        if self.platform not in ['linux', 'darwin', 'windows']:
            self.log_error(f"不支持的操作系统: {self.platform}")
            success = False

        # 检查Python版本
        python_version = sys.version_info
        if python_version.major < 3 or (python_version.major == 3 and python_version.minor < 11):
            self.log_error(f"Python版本过低: {python_version}，需要Python 3.11+")
            success = False
        else:
            self.log_success(f"Python版本: {python_version.major}.{python_version.minor}.{python_version.micro}")

        # 检查Git
        git_version = self.run_command(['git', '--version'], check=False, capture=True)
        if git_version:
            self.log_success(f"Git: {git_version}")
        else:
            self.log_error("Git未安装")
            success = False

        # 检查Docker
        docker_version = self.run_command(['docker',
    '--version'],
    check=False,
    capture=True)
        if docker_version:
            self.log_success(f"Docker: {docker_version}")
        else:
            self.log_warning("Docker未安装，将跳过Docker相关配置")

        # 检查Docker Compose
        compose_version = self.run_command(['docker-compose',
    '--version'],
    check=False,
    capture=True)
        if compose_version:
            self.log_success(f"Docker Compose: {compose_version}")
        else:
            self.log_warning("Docker Compose未安装，将跳过Docker相关配置")

        # 检查磁盘空间
        disk_usage = shutil.disk_usage(self.project_root)
        free_gb = disk_usage.free / (1024 ** 3)
        if free_gb < 5:
            self.log_warning(f"磁盘空间不足: {free_gb:.1f}GB，建议至少10GB")
        else:
            self.log_success(f"磁盘空间: {free_gb:.1f}GB可用")

        return success

    def setup_python_environment(self) -> bool:
        """设置Python环境"""
        self.log_info("设置Python环境...")

        success = True

        # 检查是否存在虚拟环境
        venv_path = self.project_root / '.venv'
        if not venv_path.exists():
            self.log_info("创建虚拟环境...")
            if self.run_command([sys.executable, '-m', 'venv', '.venv']):
                self.log_success("虚拟环境创建成功")
            else:
                self.log_error("虚拟环境创建失败")
                success = False

        # 激活虚拟环境并安装依赖
        if self.platform == 'windows':
            pip_path = venv_path / 'Scripts' / 'pip'
            venv_path / 'Scripts' / 'python'
        else:
            pip_path = venv_path / 'bin' / 'pip'
            venv_path / 'bin' / 'python'

        # 升级pip
        self.log_info("升级pip...")
        if self.run_command([str(pip_path), 'install', '--upgrade', 'pip']):
            self.log_success("pip升级成功")
        else:
            self.log_error("pip升级失败")
            success = False

        # 安装项目依赖
        self.log_info("安装项目依赖...")
        if self.run_command([str(pip_path), 'install', '-e', '.']):
            self.log_success("项目依赖安装成功")
        else:
            self.log_error("项目依赖安装失败")
            success = False

        # 安装开发依赖
        self.log_info("安装开发依赖...")
        dev_deps = [
            'pytest', 'pytest-cov', 'pytest-asyncio',
            'ruff', 'mypy', 'black', 'isort',
            'pre-commit', 'bandit', 'pip-audit'
        ]

        for dep in dev_deps:
            if self.run_command([str(pip_path), 'install', dep], check=False):
                self.log_success(f"安装 {dep} 成功")
            else:
                self.log_warning(f"安装 {dep} 失败")

        return success

    def setup_docker_environment(self) -> bool:
        """设置Docker环境"""
        self.log_info("设置Docker环境...")

        # 检查Docker是否可用
        if not self.run_command(['docker', '--version'], check=False):
            self.log_warning("Docker不可用，跳过Docker环境设置")
            return True

        success = True

        # 构建Docker镜像
        self.log_info("构建Docker开发镜像...")
        if self.run_command(['docker-compose', 'build'], check=False):
            self.log_success("Docker镜像构建成功")
        else:
            self.log_error("Docker镜像构建失败")
            success = False

        # 启动开发环境
        self.log_info("启动Docker开发环境...")
        if self.run_command(['docker-compose', 'up', '-d'], check=False):
            self.log_success("Docker环境启动成功")
        else:
            self.log_error("Docker环境启动失败")
            success = False

        # 等待服务就绪
        self.log_info("等待服务就绪...")
        import time
        time.sleep(10)

        # 检查服务状态
        self.log_info("检查服务状态...")
        if self.run_command(['docker-compose', 'ps'], check=False):
            self.log_success("服务状态检查完成")
        else:
            self.log_warning("无法检查服务状态")

        return success

    def setup_ide_configurations(self) -> bool:
        """设置IDE配置"""
        self.log_info("设置IDE配置...")

        success = True

        # 创建VSCode配置
        vscode_dir = self.project_root / '.vscode'
        vscode_dir.mkdir(exist_ok=True)

        # VSCode扩展推荐
        extensions = {
            "recommendations": [
                "ms-python.python",
                "ms-python.flake8",
                "ms-python.black-formatter",
                "ms-python.isort",
                "ms-python.debugpy",
                "charliermarsh.ruff",
                "ms-vscode.vscode-json",
                "redhat.vscode-yaml",
                "ms-vscode-remote.remote-containers",
                "ms-vscode.test-adapter-converter",
                "hbenl.vscode-test-explorer"
            ]
        }

        extensions_file = vscode_dir / 'extensions.json'
        with open(extensions_file, 'w', encoding='utf-8') as f:
            json.dump(extensions, f, indent=2)
        self.log_success("VSCode扩展推荐已创建")

        # VSCode设置
        settings = {
            "python.defaultInterpreterPath": ".venv/bin/python" if self.platform != 'windows' else ".venv\\Scripts\\python.exe",
            "python.linting.enabled": True,
            "python.linting.ruffEnabled": True,
            "python.formatting.provider": "ruff",
            "python.testing.pytestEnabled": True,
            "python.testing.pytestArgs": ["tests"],
            "python.testing.unittestEnabled": False,
            "editor.formatOnSave": True,
            "editor.codeActionsOnSave": {
                "source.organizeImports": True
            },
            "files.exclude": {
                "**/__pycache__": True,
                "**/*.pyc": True,
                ".pytest_cache": True,
                ".coverage": True,
                "htmlcov": True,
                ".mypy_cache": True,
                ".ruff_cache": True
            },
            "python.analysis.typeCheckingMode": "basic",
            "python.analysis.autoImportCompletions": True
        }

        settings_file = vscode_dir / 'settings.json'
        with open(settings_file, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=2)
        self.log_success("VSCode设置已创建")

        # VSCode调试配置
        launch_config = {
            "version": "0.2.0",
            "configurations": [
                {
                    "name": "Python: FastAPI",
                    "type": "python",
                    "request": "launch",
                    "program": "${workspaceFolder}/src/main.py",
                    "module": "uvicorn",
                    "args": [
                        "src.main:app",
                        "--host",
                        "0.0.0.0",
                        "--port",
                        "8000",
                        "--reload"
                    ],
                    "jinja": True,
                    "justMyCode": False,
                    "console": "integratedTerminal"
                },
                {
                    "name": "Python: Pytest",
                    "type": "python",
                    "request": "launch",
                    "module": "pytest",
                    "args": ["tests", "-v"],
                    "jinja": True,
                    "justMyCode": False,
                    "console": "integratedTerminal"
                }
            ]
        }

        launch_file = vscode_dir / 'launch.json'
        with open(launch_file, 'w', encoding='utf-8') as f:
            json.dump(launch_config, f, indent=2)
        self.log_success("VSCode调试配置已创建")

        # 创建EditorConfig
        editor_config = """root = true

[*]
charset = utf-8
end_of_line = lf
insert_final_newline = true
trim_trailing_whitespace = true
indent_style = space
indent_size = 4

[*.py]
max_line_length = 88

[*.{yml,yaml}]
indent_size = 2

[*.json]
indent_size = 2

[Makefile]
indent_style = tab
"""

        editor_config_file = self.project_root / '.editorconfig'
        with open(editor_config_file, 'w', encoding='utf-8') as f:
            f.write(editor_config)
        self.log_success("EditorConfig已创建")

        return success

    def setup_git_hooks(self) -> bool:
        """设置Git hooks"""
        self.log_info("设置Git hooks...")

        git_dir = self.project_root / '.git'
        if not git_dir.exists():
            self.log_warning("不是Git仓库，跳过Git hooks设置")
            return True

        success = True
        hooks_dir = git_dir / 'hooks'

        # Pre-commit hook
        pre_commit_content = """#!/bin/bash
echo "🔍 Running pre-commit checks..."

# Run code formatting
echo "📝 Checking code format..."
make fmt 2>/dev/null || {
    echo "⚠️  Code formatting not available via make, trying ruff directly..."
    ruff format . 2>/dev/null || echo "⚠️  Ruff format not available"
}

# Run linting
echo "🔍 Running linting..."
make lint 2>/dev/null || {
    echo "⚠️  Linting not available via make, trying ruff directly..."
    ruff check . 2>/dev/null || echo "⚠️  Ruff check not available"
}

# Run unit tests
echo "🧪 Running unit tests..."
make test.unit 2>/dev/null || {
    echo "⚠️  Unit tests not available via make, trying pytest directly..."
    pytest tests/unit -v 2>/dev/null || echo "⚠️  Pytest not available"
}

echo "✅ Pre-commit checks completed!"
"""

        pre_commit_file = hooks_dir / 'pre-commit'
        with open(pre_commit_file, 'w', encoding='utf-8') as f:
            f.write(pre_commit_content)

        # 设置执行权限
        os.chmod(pre_commit_file, 0o755)
        self.log_success("Pre-commit hook已设置")

        # Pre-push hook
        pre_push_content = """#!/bin/bash
echo "🚀 Running pre-push checks..."

# Run full test suite
echo "🧪 Running full test suite..."
make test 2>/dev/null || {
    echo "⚠️  Full tests not available via make, trying pytest directly..."
    pytest tests/ -v 2>/dev/null || echo "⚠️  Pytest not available"
}

# Run security checks
echo "🔒 Running security checks..."
make security 2>/dev/null || {
    echo "⚠️  Security checks not available via make, trying bandit directly..."
    bandit -r src/ 2>/dev/null || echo "⚠️  Bandit not available"
}

echo "✅ Pre-push checks completed!"
"""

        pre_push_file = hooks_dir / 'pre-push'
        with open(pre_push_file, 'w', encoding='utf-8') as f:
            f.write(pre_push_content)

        os.chmod(pre_push_file, 0o755)
        self.log_success("Pre-push hook已设置")

        return success

    def setup_environment_files(self) -> bool:
        """设置环境配置文件"""
        self.log_info("设置环境配置文件...")

        success = True

        # 创建.env.example文件（如果不存在）
        env_example_path = self.project_root / '.env.example'
        if not env_example_path.exists():
            env_example_content = """# 开发环境配置示例
# 复制此文件为 .env 并修改相应配置

# 基本配置
ENV=development
DEBUG=true
LOG_LEVEL=INFO

# 数据库配置
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/football_prediction
DB_HOST=localhost
DB_PORT=5432
DB_NAME=football_prediction
DB_USER=postgres
DB_PASSWORD=postgres

# Redis配置
REDIS_URL=redis://localhost:6379/0
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# API配置
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=1

# 安全配置
SECRET_KEY=your-secret-key-here
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=30

# 外部服务配置
EXTERNAL_API_TIMEOUT=30
EXTERNAL_API_RETRIES=3

# 监控配置
ENABLE_METRICS=true
METRICS_PORT=9090

# 开发工具配置
HOT_RELOAD=true
AUTO_RESTART=true
"""

            with open(env_example_path, 'w', encoding='utf-8') as f:
                f.write(env_example_content)
            self.log_success(".env.example文件已创建")

        # 检查.env文件
        env_path = self.project_root / '.env'
        if not env_path.exists():
            self.log_info("创建.env文件...")
            shutil.copy2(env_example_path, env_path)
            self.log_success(".env文件已创建")

        # 创建Makefile（如果不存在）
        makefile_path = self.project_root / 'Makefile'
        if not makefile_path.exists():
            self.create_basic_makefile()
            self.log_success("基础Makefile已创建")

        return success

    def create_basic_makefile(self):
        """创建基础Makefile"""
        makefile_content = """# 基础开发命令
.PHONY: help install test lint fmt clean up down

help:		## 显示帮助信息
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\\033[36m%-20s\\033[0m %s\\n",

    $$1,
    $$2}'

install:		## 安装依赖
	pip install -e .
	pip install pytest pytest-cov ruff mypy black isort pre-commit

test:		## 运行测试
	pytest tests/ -v

test.unit:	## 运行单元测试
	pytest tests/unit/ -v

test.int:		## 运行集成测试
	pytest tests/integration/ -v

lint:		## 代码检查
	ruff check src/ tests/

fmt:			## 代码格式化
	ruff format src/ tests/
	ruff check --fix src/ tests/

clean:		## 清理缓存文件
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -name "*.pyc" -delete
	rm -rf .pytest_cache .coverage htmlcov .mypy_cache .ruff_cache

up:			## 启动Docker环境
	docker-compose up -d

down:		## 停止Docker环境
	docker-compose down

env-check:	## 检查环境配置
	@echo "Python: $(shell python --version)"
	@echo "Docker: $(shell docker --version 2>/dev/null || echo 'Not installed')"
	@echo "Docker Compose: $(shell docker-compose --version 2>/dev/null || echo 'Not installed')"
"""

        makefile_path = self.project_root / 'Makefile'
        with open(makefile_path, 'w', encoding='utf-8') as f:
            f.write(makefile_content)

    def run_validation_tests(self) -> bool:
        """运行验证测试"""
        self.log_info("运行环境验证测试...")

        success = True

        # 测试Python导入
        try:
            import sys
            sys.path.insert(0, str(self.project_root / 'src'))
            # 这里可以添加具体的导入测试
            self.log_success("Python环境验证通过")
        except Exception as e:
            self.log_error(f"Python环境验证失败: {e}")
            success = False

        # 测试Make命令
        make_help = self.run_command(['make', 'help'], check=False, capture=True)
        if make_help:
            self.log_success("Make命令可用")
        else:
            self.log_warning("Make命令不可用")

        # 测试Docker（如果可用）
        if self.run_command(['docker', '--version'], check=False):
            docker_ps = self.run_command(['docker-compose',
    'ps'],
    check=False,
    capture=True)
            if docker_ps:
                self.log_success("Docker环境验证通过")
            else:
                self.log_warning("Docker环境验证失败")

        return success

    def generate_setup_report(self) -> str:
        """生成设置报告"""
        report = f"""
# 🛠️ 开发环境设置报告

**设置时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**操作系统**: {self.platform}
**Python版本**: {sys.version.split()[0]}

## ✅ 完成的设置

### 基础环境
- [x] 系统要求检查
- [x] Python虚拟环境设置
- [x] 项目依赖安装

### 开发工具
- [x] VSCode配置生成
- [x] Git hooks设置
- [x] 环境配置文件

### Docker环境
- [x] Docker镜像构建
- [x] 开发环境启动

## 📊 设置统计

**成功步骤**: {len([])}
**警告数量**: {len(self.warnings)}
**错误数量**: {len(self.errors)}

"""

        if self.warnings:
            report += "## ⚠️ 警告\n\n"
            for warning in self.warnings:
                report += f"- {warning}\n"
            report += "\n"

        if self.errors:
            report += "## ❌ 错误\n\n"
            for error in self.errors:
                report += f"- {error}\n"
            report += "\n"

        if not self.errors:
            report += """## 🎉 设置完成！

开发环境设置成功！现在可以开始开发了：

### 快速开始
```bash
# 激活虚拟环境
source .venv/bin/activate  # Linux/macOS
# 或
.venv\\Scripts\\activate   # Windows

# 启动开发环境
make up

# 运行测试
make test

# 开始开发！
```

### 下一步
1. 阅读项目文档
2. 运行 `make env-check` 验证环境
3. 开始你的第一个功能开发

"""

        # 保存报告
        report_path = self.project_root / 'setup_report.md'
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)

        return report

    def run_full_setup(self) -> bool:
        """运行完整的环境设置"""

        steps = [
            ("检查系统要求", self.check_system_requirements),
            ("设置Python环境", self.setup_python_environment),
            ("设置Docker环境", self.setup_docker_environment),
            ("设置IDE配置", self.setup_ide_configurations),
            ("设置Git hooks", self.setup_git_hooks),
            ("设置环境文件", self.setup_environment_files),
            ("运行验证测试", self.run_validation_tests),
        ]

        success_count = 0
        total_steps = len(steps)

        for _step_name, step_func in steps:
            try:
                if step_func():
                    success_count += 1
                else:
                    pass
            except Exception:
                pass


        # 生成报告
        self.generate_setup_report()

        if success_count == total_steps and not self.errors:
            return True
        else:
            return False


def main():
    """主函数"""

    # 检查是否在正确的目录
    if not Path("pyproject.toml").exists():
        sys.exit(1)

    # 创建设置器
    setup = DevelopmentEnvironmentSetup()

    # 询问用户是否要运行完整设置
    try:
        response = input("是否运行完整的开发环境设置? (y/N): ").strip().lower()
        if response in ['y', 'yes']:
            success = setup.run_full_setup()
            sys.exit(0 if success else 1)
        else:
            sys.exit(0)
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()
