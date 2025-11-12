#!/usr/bin/env python3
"""
项目上下文加载器 - Claude Code 专用
用于快速了解项目结构、架构和关键信息
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Any
import argparse


class ProjectContextLoader:
    """项目上下文加载器"""

    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.context_data = {}

    def load_basic_info(self) -> Dict[str, Any]:
        """加载基础项目信息"""
        print("📋 加载基础项目信息...")

        basic_info = {
            "project_name": "FootballPrediction",
            "description": "企业级足球预测系统",
            "python_version": sys.version.split()[0],
            "root_directory": str(self.project_root),
            "git_branch": self._get_git_branch(),
            "git_commit": self._get_git_commit(),
        }

        return basic_info

    def load_project_structure(self) -> Dict[str, Any]:
        """加载项目结构信息"""
        print("🏗️ 加载项目结构...")

        structure = {
            "src_modules": self._get_src_modules(),
            "test_structure": self._get_test_structure(),
            "key_files": self._get_key_files(),
            "directories": self._get_directories(),
        }

        return structure

    def load_architecture_info(self) -> Dict[str, Any]:
        """加载架构信息"""
        print("🎯 加载架构信息...")

        architecture = {
            "tech_stack": {
                "backend": "FastAPI",
                "database": "PostgreSQL + SQLAlchemy 2.0",
                "cache": "Redis",
                "architecture_patterns": ["DDD", "CQRS", "依赖注入", "事件驱动"]
            },
            "core_modules": self._analyze_core_modules(),
            "design_patterns": self._get_design_patterns(),
        }

        return architecture

    def load_testing_info(self) -> Dict[str, Any]:
        """加载测试信息"""
        print("🧪 加载测试信息...")

        testing_info = {
            "test_count": self._count_tests(),
            "test_types": self._get_test_types(),
            "coverage_threshold": 30,
            "recent_test_status": self._get_recent_test_status(),
        }

        return testing_info

    def load_development_info(self) -> Dict[str, Any]:
        """加载开发信息"""
        print("🛠️ 加载开发信息...")

        dev_info = {
            "makefile_commands": self._get_makefile_summary(),
            "key_scripts": self._get_key_scripts(),
            "environment_files": self._get_environment_files(),
            "docker_support": self._check_docker_support(),
        }

        return dev_info

    def _get_git_branch(self) -> str:
        """获取当前Git分支"""
        try:
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                capture_output=True,
                text=True,
                cwd=self.project_root
            )
            return result.stdout.strip() if result.returncode == 0 else "unknown"
        except:
            return "unknown"

    def _get_git_commit(self) -> str:
        """获取当前Git提交"""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                capture_output=True,
                text=True,
                cwd=self.project_root
            )
            return result.stdout.strip() if result.returncode == 0 else "unknown"
        except:
            return "unknown"

    def _get_src_modules(self) -> List[str]:
        """获取src目录下的模块"""
        src_path = self.project_root / "src"
        if not src_path.exists():
            return []

        modules = []
        for item in src_path.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                modules.append(item.name)

        return sorted(modules)

    def _get_test_structure(self) -> Dict[str, Any]:
        """获取测试结构"""
        tests_path = self.project_root / "tests"
        if not tests_path.exists():
            return {"exists": False}

        test_dirs = []
        for item in tests_path.iterdir():
            if item.is_dir():
                test_dirs.append(item.name)

        return {
            "exists": True,
            "test_directories": sorted(test_dirs),
            "pytest_config": (self.project_root / "pytest.ini").exists(),
        }

    def _get_key_files(self) -> List[str]:
        """获取关键文件"""
        key_files = [
            "README.md",
            "CLAUDE.md",
            "Makefile",
            "requirements.txt",
            "docker-compose.yml",
            ".env.example",
            "pytest.ini",
            "pyproject.toml"
        ]

        existing_files = []
        for file in key_files:
            if (self.project_root / file).exists():
                existing_files.append(file)

        return existing_files

    def _get_directories(self) -> List[str]:
        """获取重要目录"""
        important_dirs = [
            "src",
            "tests",
            "docs",
            "scripts",
            "config",
            ".github",
            "frontend"
        ]

        existing_dirs = []
        for dir_name in important_dirs:
            if (self.project_root / dir_name).exists():
                existing_dirs.append(dir_name)

        return existing_dirs

    def _analyze_core_modules(self) -> Dict[str, Any]:
        """分析核心模块"""
        src_path = self.project_root / "src"
        core_modules = {}

        important_modules = ["api", "core", "database", "domain", "services", "cache"]

        for module in important_modules:
            module_path = src_path / module
            if module_path.exists():
                file_count = len(list(module_path.glob("**/*.py")))
                core_modules[module] = {
                    "exists": True,
                    "python_files": file_count
                }
            else:
                core_modules[module] = {"exists": False}

        return core_modules

    def _get_design_patterns(self) -> List[str]:
        """获取设计模式"""
        return [
            "Domain-Driven Design (DDD)",
            "CQRS (Command Query Responsibility Segregation)",
            "依赖注入容器",
            "策略工厂模式",
            "仓储模式",
            "事件驱动架构",
            "适配器模式"
        ]

    def _count_tests(self) -> int:
        """统计测试数量"""
        try:
            result = subprocess.run(
                ["python", "-m", "pytest", "--collect-only", "-q"],
                capture_output=True,
                text=True,
                cwd=self.project_root
            )
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    if 'test session starts' in line.lower() or 'collected' in line.lower():
                        continue
                    # 提取数字（简单的测试计数）
                    if line.strip().isdigit():
                        return int(line.strip())
            return 0
        except:
            return 0

    def _get_test_types(self) -> List[str]:
        """获取测试类型"""
        pytest_ini = self.project_root / "pytest.ini"
        if not pytest_ini.exists():
            return []

        markers = []
        try:
            with open(pytest_ini, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')

                in_markers = False
                for line in lines:
                    line = line.strip()
                    if 'markers =' in line:
                        in_markers = True
                        continue
                    if in_markers:
                        if line and not line.startswith('#'):
                            if ':' in line:
                                marker_name = line.split(':')[0].strip()
                                markers.append(marker_name)
                        elif line.startswith('['):
                            break
        except:
            pass

        return markers

    def _get_recent_test_status(self) -> Dict[str, Any]:
        """获取最近的测试状态"""
        # 这里可以添加更复杂的逻辑来检查最近的测试运行结果
        return {
            "last_check": "manual_verification_needed",
            "status": "partially_working",
            "issues": ["some_test_failures", "missing_scripts"]
        }

    def _get_makefile_summary(self) -> Dict[str, Any]:
        """获取Makefile摘要"""
        makefile_path = self.project_root / "Makefile"
        if not makefile_path.exists():
            return {"exists": False}

        try:
            with open(makefile_path, 'r', encoding='utf-8') as f:
                content = f.read()
                line_count = len(content.split('\n'))

                # 统计目标数量
                targets = []
                lines = content.split('\n')
                for line in lines:
                    if ':' in line and not line.startswith('\t') and not line.startswith('#'):
                        target = line.split(':')[0].strip()
                        if target and target.isidentifier():
                            targets.append(target)

                return {
                    "exists": True,
                    "line_count": line_count,
                    "target_count": len(set(targets)),
                    "key_targets": ["install", "test.unit", "coverage", "ci-check", "help"]
                }
        except:
            return {"exists": True, "error": "failed_to_parse"}

    def _get_key_scripts(self) -> List[str]:
        """获取关键脚本"""
        scripts_path = self.project_root / "scripts"
        if not scripts_path.exists():
            return []

        important_scripts = [
            "smart_quality_fixer.py",
            "emergency_syntax_fixer.py",
            "comprehensive_syntax_fixer.py"
        ]

        existing_scripts = []
        for script in important_scripts:
            if (scripts_path / script).exists():
                existing_scripts.append(script)

        return existing_scripts

    def _get_environment_files(self) -> List[str]:
        """获取环境文件"""
        env_files = [".env.example", ".env", ".env.ci", ".env.local"]
        existing = []

        for env_file in env_files:
            if (self.project_root / env_file).exists():
                existing.append(env_file)

        return existing

    def _check_docker_support(self) -> Dict[str, Any]:
        """检查Docker支持"""
        docker_files = [
            "docker-compose.yml",
            "Dockerfile",
            ".dockerignore"
        ]

        existing = []
        for docker_file in docker_files:
            if (self.project_root / docker_file).exists():
                existing.append(docker_file)

        return {
            "supported": len(existing) > 0,
            "files": existing
        }

    def print_summary(self) -> None:
        """打印项目摘要"""
        print("\n" + "="*60)
        print("🚀 足球预测系统 - 项目上下文摘要")
        print("="*60)

        # 基础信息
        basic = self.load_basic_info()
        print(f"\n📋 基础信息:")
        print(f"  项目名称: {basic['project_name']}")
        print(f"  描述: {basic['description']}")
        print(f"  Python版本: {basic['python_version']}")
        print(f"  Git分支: {basic['git_branch']}")
        print(f"  当前提交: {basic['git_commit']}")

        # 项目结构
        structure = self.load_project_structure()
        print(f"\n🏗️ 项目结构:")
        print(f"  源码模块: {', '.join(structure['src_modules'])}")
        print(f"  测试目录: {', '.join(structure['test_structure'].get('test_directories', []))}")
        print(f"  关键文件: {len(structure['key_files'])}个")

        # 架构信息
        arch = self.load_architecture_info()
        print(f"\n🎯 技术架构:")
        print(f"  后端框架: {arch['tech_stack']['backend']}")
        print(f"  数据库: {arch['tech_stack']['database']}")
        print(f"  缓存: {arch['tech_stack']['cache']}")
        print(f"  架构模式: {', '.join(arch['tech_stack']['architecture_patterns'])}")

        # 测试信息
        testing = self.load_testing_info()
        print(f"\n🧪 测试体系:")
        print(f"  测试数量: {testing['test_count']}个")
        print(f"  覆盖率阈值: {testing['coverage_threshold']}%")
        print(f"  测试类型: {len(testing['test_types'])}种标记")

        # 开发信息
        dev = self.load_development_info()
        print(f"\n🛠️ 开发工具:")
        print(f"  Makefile: {dev['makefile_commands']['line_count']}行, {dev['makefile_commands']['target_count']}个命令")
        print(f"  关键脚本: {len(dev['key_scripts'])}个")
        print(f"  Docker支持: {'✅' if dev['docker_support']['supported'] else '❌'}")

        print(f"\n📚 快速开始:")
        print(f"  make install && make env-check          # 环境准备")
        print(f"  make test.unit                          # 运行测试")
        print(f"  make coverage                           # 查看覆盖率")
        print(f"  make help                               # 查看所有命令")

        print(f"\n🚨 常见问题解决:")
        print(f"  python3 scripts/emergency_syntax_fixer.py  # 语法修复")
        print(f"  make solve-test-crisis                      # 测试危机解决")

        print("\n" + "="*60)
        print("✅ 项目上下文加载完成！")
        print("="*60)

    def save_context(self, output_file: str = None) -> None:
        """保存上下文到文件"""
        if not output_file:
            output_file = self.project_root / "project_context.json"

        context = {
            "basic_info": self.load_basic_info(),
            "project_structure": self.load_project_structure(),
            "architecture": self.load_architecture_info(),
            "testing": self.load_testing_info(),
            "development": self.load_development_info(),
            "generated_at": str(Path.cwd()),
            "python_version": sys.version
        }

        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(context, f, indent=2, ensure_ascii=False)
            print(f"✅ 项目上下文已保存到: {output_file}")
        except Exception as e:
            print(f"❌ 保存上下文失败: {e}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="项目上下文加载器")
    parser.add_argument("--summary", action="store_true", help="显示项目摘要")
    parser.add_argument("--save", action="store_true", help="保存上下文到文件")
    parser.add_argument("--output", help="输出文件路径")
    parser.add_argument("--full", action="store_true", help="显示完整上下文")

    args = parser.parse_args()

    loader = ProjectContextLoader()

    if args.summary or (not args.save and not args.full):
        loader.print_summary()

    if args.save:
        loader.save_context(args.output)

    if args.full:
        print("\n🔍 完整项目上下文:")
        print(json.dumps({
            "basic_info": loader.load_basic_info(),
            "project_structure": loader.load_project_structure(),
            "architecture": loader.load_architecture_info(),
            "testing": loader.load_testing_info(),
            "development": loader.load_development_info()
        }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()