#!/usr/bin/env python3
"""
🚀 AICultureKit 项目模板生成器

将现有的AICultureKit项目转换为可重用的项目模板，
包含完整的开发基础设施和最佳实践配置。
"""

import argparse
import json
import os
import shutil
from pathlib import Path
from typing import Dict


class ProjectTemplateGenerator:
    """项目模板生成器类"""

    def __init__(self, source_project_path: str):
        self.source_path = Path(source_project_path).resolve()
        self.template_config = self._get_template_config()

    def _get_template_config(self) -> Dict:
        """获取模板配置信息"""
        return {
            "core_files": [
                "Makefile",
                ".pre-commit-config.yaml",
                ".coveragerc",
                ".ruffignore",
                "setup.cfg",
                ".gitignore",
                "env.example",
                "requirements-dev.txt",
                "Dockerfile",
                "Dockerfile.dev",
                "docker-compose.yml",
                "docker-compose.dev.yml",
                ".dockerignore",
                "Makefile.docker",
            ],
            "core_directories": [
                ".github/workflows",
                ".cursor/rules",
                "docs",
                "scripts",
                "tests",
                "src",
            ],
            "ai_guide_files": [
                "AI_WORK_GUIDE.md",
                "AI_PROMPT.md",
                ".cursor/rules/ai.mdc",
            ],
            "exclude_patterns": [
                ".git",
                "venv",
                "__pycache__",
                ".pytest_cache",
                ".mypy_cache",
                ".ruff_cache",
                ".coverage",
                "coverage.json",
                "coverage.xml",
                "logs",
                ".benchmarks",
                "backup",
            ],
            "template_files": [
                "Makefile",
                "README.md",
                ".cursor/rules/ai.mdc",
                "AI_WORK_GUIDE.md",
                "AI_PROMPT.md",
                "setup.cfg",
                "docker-compose.yml",
                "docker-compose.dev.yml",
                "Dockerfile",
                "Dockerfile.dev",
                "setup.py",
            ],
        }

    def generate_template(
        self, output_path: str, template_name: str = "python-project-template"
    ) -> bool:
        """生成项目模板"""
        try:
            output_dir = Path(output_path) / template_name
            print(f"🚀 开始生成项目模板: {template_name}")
            print(f"📁 输出路径: {output_dir}")

            # 创建输出目录
            output_dir.mkdir(parents=True, exist_ok=True)

            # 复制核心文件和目录
            self._copy_core_infrastructure(output_dir)

            # 创建模板项目结构
            self._create_template_structure(output_dir)

            # 生成模板配置文件
            self._generate_template_config(output_dir)

            # 生成项目生成器脚本
            self._generate_project_generator(output_dir)

            # 生成使用文档
            self._generate_documentation(output_dir)

            print("✅ 项目模板生成完成!")
            print(f"📚 使用方法: python {output_dir}/generate_project.py --help")

            return True

        except Exception as e:
            print(f"❌ 模板生成失败: {str(e)}")
            return False

    def _copy_core_infrastructure(self, output_dir: Path):
        """复制核心基础设施文件"""
        print("📋 复制核心基础设施文件...")

        # 复制核心文件
        for file_name in self.template_config["core_files"]:
            source_file = self.source_path / file_name
            if source_file.exists():
                target_file = output_dir / file_name
                target_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source_file, target_file)
                print(f"  ✅ {file_name}")

        # 复制核心目录
        for dir_name in self.template_config["core_directories"]:
            source_dir = self.source_path / dir_name
            if source_dir.exists():
                target_dir = output_dir / dir_name
                if target_dir.exists():
                    shutil.rmtree(target_dir)
                # 使用简单的ignore模式
                ignore_func = shutil.ignore_patterns(*self.template_config["exclude_patterns"])
                shutil.copytree(source_dir, target_dir, ignore=ignore_func)
                print(f"  ✅ {dir_name}/")

    def _create_template_structure(self, output_dir: Path):
        """创建模板项目结构"""
        print("🏗️  创建模板项目结构...")

        directories = [
            "src/{{PROJECT_NAME_LOWER}}",
            "tests/unit",
            "tests/integration",
            "tests/fixtures",
            "docs",
            "scripts",
            "logs",
        ]

        for directory in directories:
            (output_dir / directory).mkdir(parents=True, exist_ok=True)
            print(f"  ✅ {directory}/")

        # 创建基本Python文件
        self._create_basic_python_files(output_dir)

        # 创建setup.py文件
        self._create_setup_py(output_dir)

    def _create_basic_python_files(self, output_dir: Path):
        """创建基本的Python文件"""

        # 主包 __init__.py
        init_content = '''"""
{{PROJECT_DESCRIPTION}}

这是一个基于AICultureKit模板创建的Python项目，
包含完整的开发基础设施和最佳实践配置。
"""

__version__ = "0.1.0"
__author__ = "{{AUTHOR_NAME}}"
__email__ = "{{AUTHOR_EMAIL}}"

__all__ = ["__version__", "__author__", "__email__"]
'''

        init_file = output_dir / "src/{{PROJECT_NAME_LOWER}}/__init__.py"
        with open(init_file, "w", encoding="utf-8") as f:
            f.write(init_content)

        # 核心模块
        core_content = '''"""核心功能模块"""


class ProjectCore:
    """项目核心类"""

    def __init__(self):
        self.name = "{{PROJECT_NAME}}"
        self.version = "0.1.0"

    def get_info(self) -> dict:
        """获取项目信息"""
        return {
            "name": self.name,
            "version": self.version,
            "description": "{{PROJECT_DESCRIPTION}}"
        }
'''

        core_dir = output_dir / "src/{{PROJECT_NAME_LOWER}}/core"
        core_dir.mkdir(parents=True, exist_ok=True)
        with open(core_dir / "__init__.py", "w", encoding="utf-8") as f:
            f.write(core_content)

        # 工具模块
        utils_content = '''"""工具函数模块"""

import logging
from pathlib import Path


def setup_logger(name: str, level: str = "INFO") -> logging.Logger:
    """设置日志记录器"""
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))

    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


def ensure_dir(path: Path) -> Path:
    """确保目录存在"""
    path.mkdir(parents=True, exist_ok=True)
    return path
'''

        utils_dir = output_dir / "src/{{PROJECT_NAME_LOWER}}/utils"
        utils_dir.mkdir(parents=True, exist_ok=True)
        with open(utils_dir / "__init__.py", "w", encoding="utf-8") as f:
            f.write(utils_content)

        # 基本测试文件
        test_content = '''"""基本功能测试"""

import pytest
from {{PROJECT_NAME_LOWER}}.core import ProjectCore
from {{PROJECT_NAME_LOWER}}.utils import setup_logger


class TestCore:
    """核心功能测试类"""

    def test_project_core_initialization(self):
        """测试项目核心初始化"""
        core = ProjectCore()
        assert core.name == "{{PROJECT_NAME}}"
        assert core.version == "0.1.0"

    def test_get_info(self):
        """测试获取项目信息"""
        core = ProjectCore()
        info = core.get_info()

        assert isinstance(info, dict)
        assert "name" in info
        assert "version" in info
        assert "description" in info


class TestUtils:
    """工具函数测试类"""

    def test_setup_logger(self):
        """测试日志记录器设置"""
        logger = setup_logger("test_logger")
        assert logger.name == "test_logger"
        assert logger.level == 20  # INFO level
'''

        with open(output_dir / "tests/test_basic.py", "w", encoding="utf-8") as f:
            f.write(test_content)

        print("  ✅ 基本Python文件")

    def _create_setup_py(self, output_dir: Path):
        """创建setup.py文件"""
        setup_content = '''"""Setup configuration for {{PROJECT_NAME}}"""

from setuptools import setup, find_packages

with open("requirements.txt", "r", encoding="utf-8") as f:
    requirements = [line.strip() for line in f if line.strip() and not line.startswith("#")]

setup(
    name="{{PROJECT_NAME_LOWER}}",
    version="0.1.0",
    description="{{PROJECT_DESCRIPTION}}",
    author="{{AUTHOR_NAME}}",
    author_email="{{AUTHOR_EMAIL}}",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=requirements,
    python_requires=">=3.8",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)
'''

        with open(output_dir / "setup.py", "w", encoding="utf-8") as f:
            f.write(setup_content)

        print("  ✅ setup.py")

    def _generate_template_config(self, output_dir: Path):
        """生成模板配置文件"""
        print("📝 生成模板配置文件...")

        template_config = {
            "name": "Python Project Template",
            "description": "基于AICultureKit的Python项目模板，包含完整的开发基础设施",
            "version": "1.0.0",
            "template_files": self.template_config["template_files"]
            + [
                "src/{{PROJECT_NAME_LOWER}}/__init__.py",
                "src/{{PROJECT_NAME_LOWER}}/core/__init__.py",
                "src/{{PROJECT_NAME_LOWER}}/utils/__init__.py",
                "tests/test_basic.py",
            ],
            "created_by": "AICultureKit Template Generator",
            "features": [
                "完整的CI/CD流程",
                "代码质量检查工具",
                "自动化测试和覆盖率",
                "Docker容器化支持",
                "AI辅助开发工作流",
                "预配置的开发工具链",
                "标准化的项目结构",
            ],
        }

        with open(output_dir / "template_config.json", "w", encoding="utf-8") as f:
            json.dump(template_config, f, ensure_ascii=False, indent=2)

        print("  ✅ template_config.json")

    def _generate_project_generator(self, output_dir: Path):
        """生成项目生成器脚本"""
        print("🔧 生成项目生成器脚本...")

        generator_content = '''#!/usr/bin/env python3
"""
🚀 Python项目生成器

基于AICultureKit模板生成新的Python项目。

使用方法:
    python generate_project.py --name MyProject --description "我的项目描述"
"""

import os
import json
import argparse
import shutil
from pathlib import Path
from typing import Dict


class ProjectGenerator:
    """项目生成器类"""

    def __init__(self, template_dir: str):
        self.template_dir = Path(template_dir)
        self.config = self._load_template_config()

    def _load_template_config(self) -> Dict:
        """加载模板配置"""
        config_file = self.template_dir / "template_config.json"
        if config_file.exists():
            with open(config_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def generate_project(self, project_name: str, output_dir: str, **kwargs):
        """生成新项目"""
        print(f"🚀 开始生成项目: {project_name}")

        variables = self._prepare_variables(project_name, **kwargs)
        project_path = Path(output_dir) / project_name
        project_path.mkdir(parents=True, exist_ok=True)

        self._copy_template_files(project_path, variables)
        self._initialize_git(project_path)
        self._generate_requirements(project_path)

        print(f"✅ 项目生成完成: {project_path}")
        print("\\n📚 接下来的步骤:")
        print(f"   cd {project_name}")
        print("   make install    # 安装依赖")
        print("   make env-check  # 检查环境")
        print("   make test       # 运行测试")

    def _prepare_variables(self, project_name: str, **kwargs) -> Dict[str, str]:
        """准备变量替换字典"""
        return {
            "{{PROJECT_NAME}}": project_name,
            "{{PROJECT_NAME_LOWER}}": project_name.lower().replace("-", "_"),
            "{{PROJECT_DESCRIPTION}}": kwargs.get("description") or f"{project_name} - Python项目",
            "{{AUTHOR_NAME}}": kwargs.get("author") or "Your Name",
            "{{AUTHOR_EMAIL}}": kwargs.get("email") or "your.email@example.com",
            "{{GITHUB_USERNAME}}": kwargs.get("github_user") or "yourusername",
            "{{PYTHON_VERSION}}": kwargs.get("python_version") or "3.11"
        }

    def _copy_template_files(self, project_path: Path, variables: Dict[str, str]):
        """复制并处理模板文件"""
        template_files = self.config.get("template_files", [])

        for root, dirs, files in os.walk(self.template_dir):
            # 跳过配置文件和生成器脚本
            files = [f for f in files if f not in ["template_config.json", "generate_project.py"]]

            for file in files:
                source_path = Path(root) / file
                rel_path = source_path.relative_to(self.template_dir)

                # 替换路径中的变量
                target_rel_path = str(rel_path)
                for var, value in variables.items():
                    target_rel_path = target_rel_path.replace(var, value)

                target_path = project_path / target_rel_path
                target_path.parent.mkdir(parents=True, exist_ok=True)

                # 处理文件内容
                if str(rel_path) in template_files:
                    # 变量替换文件
                    with open(source_path, "r", encoding="utf-8") as f:
                        content = f.read()

                    for var, value in variables.items():
                        content = content.replace(var, value)

                    with open(target_path, "w", encoding="utf-8") as f:
                        f.write(content)
                else:
                    # 直接复制文件
                    shutil.copy2(source_path, target_path)

    def _initialize_git(self, project_path: Path):
        """初始化Git仓库"""
        try:
            import subprocess
            subprocess.run(["git", "init"], cwd=project_path, check=True, capture_output=True)
            subprocess.run(["git", "add", "."], cwd=project_path, check=True, capture_output=True)
            subprocess.run(["git", "commit", "-m", "Initial commit from template"],
                         cwd=project_path, check=True, capture_output=True)
            print("  ✅ Git仓库初始化完成")
        except Exception as e:
            print(f"  ⚠️ Git初始化失败: {e}")

    def _generate_requirements(self, project_path: Path):
        """生成基础requirements.txt"""
        basic_requirements = [
            "# 基础依赖",
            "requests>=2.31.0",
            "click>=8.1.0",
            "pydantic>=2.0.0",
            "",
            "# 开发依赖请参考 requirements-dev.txt"
        ]

        with open(project_path / "requirements.txt", "w", encoding="utf-8") as f:
            f.write("\\n".join(basic_requirements))


def main():
    parser = argparse.ArgumentParser(description="Python项目生成器")
    parser.add_argument("--name", required=True, help="项目名称")
    parser.add_argument("--output", default=".", help="输出目录")
    parser.add_argument("--description", help="项目描述")
    parser.add_argument("--author", help="作者姓名")
    parser.add_argument("--email", help="作者邮箱")
    parser.add_argument("--github-user", help="GitHub用户名")
    parser.add_argument("--python-version", default="3.11", help="Python版本")

    args = parser.parse_args()

    template_dir = Path(__file__).parent
    generator = ProjectGenerator(template_dir)
    generator.generate_project(
        project_name=args.name,
        output_dir=args.output,
        description=args.description,
        author=args.author,
        email=args.email,
        github_user=args.github_user,
        python_version=args.python_version
    )


if __name__ == "__main__":
    main()
'''

        with open(output_dir / "generate_project.py", "w", encoding="utf-8") as f:
            f.write(generator_content)

        # 设置执行权限
        os.chmod(output_dir / "generate_project.py", 0o755)
        print("  ✅ generate_project.py")

    def _generate_documentation(self, output_dir: Path):
        """生成使用文档"""
        print("📚 生成使用文档...")

        readme_content = """# 🚀 Python项目模板

基于AICultureKit的Python项目模板，包含完整的开发基础设施和最佳实践配置。

## ✨ 特性

- 🏗️ **标准化项目结构** - 遵循Python最佳实践
- 🔧 **完整开发工具链** - 代码格式化、检查、测试等工具
- 🤖 **AI辅助开发** - 内置AI工作流程和指引
- 🐳 **Docker支持** - 开发和生产环境容器化
- ⚡ **自动化CI/CD** - GitHub Actions配置
- 📊 **代码质量监控** - 测试覆盖率、复杂度分析
- 🛡️ **安全检查** - 代码安全扫描

## 🚀 快速开始

### 1. 生成新项目

```bash
python generate_project.py --name MyProject --description "我的项目描述"
```

### 2. 初始化环境

```bash
cd MyProject
make install      # 安装依赖
make env-check    # 检查环境
make test         # 运行测试
```

## 📁 项目结构

```
MyProject/
├── src/myproject/          # 源代码
├── tests/                  # 测试文件
├── docs/                   # 文档
├── .github/workflows/      # CI/CD配置
├── Makefile               # 开发工具链
└── requirements.txt       # 依赖定义
```

## 🔧 开发工具链

```bash
make venv         # 创建虚拟环境
make install      # 安装依赖
make format       # 代码格式化
make lint         # 代码检查
make test         # 运行测试
make ci           # 本地CI检查
make prepush      # 提交前检查
```

## 🤖 AI辅助开发

遵循工具优先原则：
1. `make env-check` - 检查环境
2. `make context` - 加载上下文
3. 开发和测试
4. `make ci` - 质量检查
5. `make prepush` - 完整验证

## 🎉 开始使用

```bash
python generate_project.py --name YourProject
```

祝您开发愉快！ 🚀
"""

        with open(output_dir / "README.md", "w", encoding="utf-8") as f:
            f.write(readme_content)

        print("  ✅ README.md")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="AICultureKit项目模板生成器")
    parser.add_argument("--output", "-o", default="./template_output", help="模板输出路径")
    parser.add_argument("--name", "-n", default="python-project-template", help="模板名称")
    parser.add_argument("--source", "-s", default=".", help="源项目路径")

    args = parser.parse_args()

    generator = ProjectTemplateGenerator(args.source)
    success = generator.generate_template(args.output, args.name)

    if success:
        print("\n🎉 模板生成成功!")
        print(f"📁 模板路径: {Path(args.output) / args.name}")
        print("\n📚 使用方法:")
        print(f"   cd {Path(args.output) / args.name}")
        print("   python generate_project.py --name YourProject")
    else:
        print("\n❌ 模板生成失败!")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
