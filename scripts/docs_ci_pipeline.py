#!/usr/bin/env python3
"""
文档CI/CD流水线脚本
Documentation CI/CD Pipeline Script

这个脚本提供了完整的文档构建、验证和部署功能，
支持本地开发和CI/CD自动化。

作者: Claude AI Assistant
版本: v1.0.0
创建时间: 2025-10-24
"""

import os
import sys
import json
import subprocess
import argparse
import shutil
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
import asyncio
import aiohttp
import yaml

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class DocsCIPipeline:
    """文档CI/CD流水线管理器"""

    def __init__(self, config_path: str = "mkdocs.yml"):
        """
        初始化CI/CD流水线

        Args:
            config_path: MkDocs配置文件路径
        """
        self.config_path = Path(config_path)
        self.project_root = Path.cwd()
        self.docs_dir = self.project_root / "docs"
        self.site_dir = self.project_root / "site"
        self.build_dir = self.project_root / ".build" / "docs"

        # 确保构建目录存在
        self.build_dir.mkdir(parents=True, exist_ok=True)

        # 加载配置
        self.config = self._load_config()

        # 初始化状态
        self.pipeline_state = {
            "start_time": datetime.now().isoformat(),
            "stages": {},
            "errors": [],
            "warnings": [],
            "success": False,
        }

    def _load_config(self) -> Dict[str, Any]:
        """加载MkDocs配置"""
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
            logger.info(f"✅ 成功加载配置文件: {self.config_path}")
            return config
        except Exception as e:
            logger.error(f"❌ 加载配置文件失败: {e}")
            raise

    async def run_full_pipeline(
        self,
        build: bool = True,
        deploy: bool = False,
        quality_check: bool = True,
        deploy_target: str = "github-pages",
    ) -> Dict[str, Any]:
        """
        运行完整的CI/CD流水线

        Args:
            build: 是否构建文档
            deploy: 是否部署文档
            quality_check: 是否进行质量检查
            deploy_target: 部署目标 (github-pages, s3, custom)

        Returns:
            流水线执行结果
        """
        logger.info("🚀 开始执行文档CI/CD流水线")

        try:
            # 阶段1: 环境检查
            await self._stage_environment_check()

            # 阶段2: 依赖检查
            await self._stage_dependency_check()

            # 阶段3: 文档验证
            await self._stage_docs_validation()

            # 阶段4: 构建文档
            if build:
                await self._stage_build()

            # 阶段5: 质量检查
            if quality_check:
                await self._stage_quality_check()

            # 阶段6: 部署文档
            if deploy:
                await self._stage_deploy(deploy_target)

            # 完成流水线
            self.pipeline_state["success"] = True
            self.pipeline_state["end_time"] = datetime.now().isoformat()
            logger.info("🎉 文档CI/CD流水线执行成功")

        except Exception as e:
            self.pipeline_state["errors"].append(str(e))
            self.pipeline_state["success"] = False
            self.pipeline_state["end_time"] = datetime.now().isoformat()
            logger.error(f"❌ 流水线执行失败: {e}")

        return self.pipeline_state

    async def _stage_environment_check(self) -> None:
        """阶段1: 环境检查"""
        stage_name = "environment_check"
        logger.info("🔍 阶段1: 环境检查")

        stage_result = {"start_time": datetime.now().isoformat(), "checks": {}}

        try:
            # 检查Python版本
            python_version = sys.version_info
            stage_result["checks"]["python_version"] = {
                "version": f"{python_version.major}.{python_version.minor}.{python_version.micro}",
                "valid": python_version >= (3, 8),
            }

            # 检查必需的目录
            required_dirs = ["docs", ".build"]
            for dir_name in required_dirs:
                dir_path = self.project_root / dir_name
                stage_result["checks"][f"directory_{dir_name}"] = {
                    "exists": dir_path.exists(),
                    "path": str(dir_path),
                }

            # 检查必需的文件
            required_files = ["mkdocs.yml", "docs/INDEX.md"]
            for file_name in required_files:
                file_path = self.project_root / file_name
                stage_result["checks"][f"file_{file_name.replace('/', '_')}"] = {
                    "exists": file_path.exists(),
                    "path": str(file_path),
                }

            # 检查Git状态
            try:
                git_result = subprocess.run(
                    ["git", "status", "--porcelain"],
                    capture_output=True,
                    text=True,
                    cwd=self.project_root,
                )
                stage_result["checks"]["git_status"] = {
                    "clean": len(git_result.stdout.strip()) == 0,
                    "status": git_result.stdout.strip()[:100] if git_result.stdout else "",
                }
            except Exception:
                stage_result["checks"]["git_status"] = {"error": "Git not available"}

            stage_result["success"] = True
            stage_result["end_time"] = datetime.now().isoformat()

        except Exception as e:
            stage_result["success"] = False
            stage_result["error"] = str(e)
            stage_result["end_time"] = datetime.now().isoformat()
            raise

        self.pipeline_state["stages"][stage_name] = stage_result
        logger.info("✅ 环境检查完成")

    async def _stage_dependency_check(self) -> None:
        """阶段2: 依赖检查"""
        stage_name = "dependency_check"
        logger.info("📦 阶段2: 依赖检查")

        stage_result = {"start_time": datetime.now().isoformat(), "dependencies": {}}

        try:
            # 检查必需的Python包
            required_packages = [
                "mkdocs",
                "mkdocs_material",
                "pymdown_extensions",
                "markdown_extensions",
            ]

            for package in required_packages:
                try:
                    result = subprocess.run(
                        [sys.executable, "-c", f"import {package}"], capture_output=True, text=True
                    )
                    stage_result["dependencies"][package] = {
                        "installed": result.returncode == 0,
                        "version": (
                            self._get_package_version(package) if result.returncode == 0 else None
                        ),
                    }
                except Exception as e:
                    stage_result["dependencies"][package] = {"installed": False, "error": str(e)}

            # 检查可选依赖
            optional_packages = ["mkdocs-minify-plugin", "mkdocs-git-revision-date-plugin"]
            for package in optional_packages:
                try:
                    result = subprocess.run(
                        [sys.executable, "-c", f"import {package}"], capture_output=True, text=True
                    )
                    stage_result["dependencies"][f"optional_{package}"] = {
                        "installed": result.returncode == 0,
                        "version": (
                            self._get_package_version(package) if result.returncode == 0 else None
                        ),
                    }
                except Exception:
                    stage_result["dependencies"][f"optional_{package}"] = {"installed": False}

            stage_result["success"] = True
            stage_result["end_time"] = datetime.now().isoformat()

        except Exception as e:
            stage_result["success"] = False
            stage_result["error"] = str(e)
            stage_result["end_time"] = datetime.now().isoformat()
            raise

        self.pipeline_state["stages"][stage_name] = stage_result
        logger.info("✅ 依赖检查完成")

    def _get_package_version(self, package_name: str) -> Optional[str]:
        """获取包版本"""
        try:
            result = subprocess.run(
                [sys.executable, "-c", f"import {package_name}; print({package_name}.__version__)"],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass
        return None

    async def _stage_docs_validation(self) -> None:
        """阶段3: 文档验证"""
        stage_name = "docs_validation"
        logger.info("📋 阶段3: 文档验证")

        stage_result = {"start_time": datetime.now().isoformat(), "validation": {}}

        try:
            # 检查文档目录结构
            stage_result["validation"]["structure"] = self._validate_docs_structure()

            # 检查文档内容质量
            stage_result["validation"]["content"] = await self._validate_docs_content()

            # 检查文档链接
            stage_result["validation"]["links"] = await self._validate_docs_links()

            # 检查文档配置
            stage_result["validation"]["config"] = self._validate_docs_config()

            stage_result["success"] = True
            stage_result["end_time"] = datetime.now().isoformat()

        except Exception as e:
            stage_result["success"] = False
            stage_result["error"] = str(e)
            stage_result["end_time"] = datetime.now().isoformat()
            raise

        self.pipeline_state["stages"][stage_name] = stage_result
        logger.info("✅ 文档验证完成")

    def _validate_docs_structure(self) -> Dict[str, Any]:
        """验证文档结构"""
        result = {
            "total_files": 0,
            "total_directories": 0,
            "index_exists": False,
            "readme_exists": False,
            "issues": [],
        }

        try:
            # 统计文件和目录
            for root, dirs, files in os.walk(self.docs_dir):
                result["total_directories"] += len(dirs)
                result["total_files"] += len([f for f in files if f.endswith(".md")])

            # 检查关键文件
            index_file = self.docs_dir / "INDEX.md"
            result["index_exists"] = index_file.exists()

            readme_file = self.docs_dir / "README.md"
            result["readme_exists"] = readme_file.exists()

            # 检查必需的子目录
            required_subdirs = ["architecture", "reference", "how-to", "testing"]
            for subdir in required_subdirs:
                subdir_path = self.docs_dir / subdir
                if not subdir_path.exists():
                    result["issues"].append(f"缺少必需目录: {subdir}")

        except Exception as e:
            result["issues"].append(f"结构验证错误: {e}")

        return result

    async def _validate_docs_content(self) -> Dict[str, Any]:
        """验证文档内容"""
        result = {
            "total_words": 0,
            "total_lines": 0,
            "files_with_frontmatter": 0,
            "files_with_toc": 0,
            "issues": [],
        }

        try:
            # 遍历所有Markdown文件
            md_files = list(self.docs_dir.rglob("*.md"))

            for md_file in md_files:
                try:
                    with open(md_file, "r", encoding="utf-8") as f:
                        content = f.read()

                    lines = content.split("\n")
                    result["total_lines"] += len(lines)
                    result["total_words"] += len(content.split())

                    # 检查Front Matter
                    if content.startswith("---"):
                        result["files_with_frontmatter"] += 1

                    # 检查目录
                    if "## 📑 目录" in content or "## 目录" in content:
                        result["files_with_toc"] += 1

                    # 检查内容长度
                    if len(content.strip()) < 100:
                        result["issues"].append(
                            f"文件内容过少: {md_file.relative_to(self.docs_dir)}"
                        )

                except Exception as e:
                    result["issues"].append(f"读取文件失败 {md_file}: {e}")

        except Exception as e:
            result["issues"].append(f"内容验证错误: {e}")

        return result

    async def _validate_docs_links(self) -> Dict[str, Any]:
        """验证文档链接"""
        result = {
            "total_links": 0,
            "internal_links": 0,
            "external_links": 0,
            "broken_links": [],
            "issues": [],
        }

        try:
            md_files = list(self.docs_dir.rglob("*.md"))

            for md_file in md_files:
                try:
                    with open(md_file, "r", encoding="utf-8") as f:
                        content = f.read()

                    # 简单的链接检查（可以扩展）
                    import re

                    # 查找Markdown链接
                    link_pattern = r"\[([^\]]+)\]\(([^)]+)\)"
                    matches = re.findall(link_pattern, content)

                    for text, url in matches:
                        result["total_links"] += 1

                        if url.startswith("http"):
                            result["external_links"] += 1
                        elif url.startswith("#") or url.startswith("./") or url.startswith("../"):
                            result["internal_links"] += 1
                        else:
                            result["issues"].append(f"不明确的链接格式: {url} in {md_file}")

                except Exception as e:
                    result["issues"].append(f"链接验证失败 {md_file}: {e}")

        except Exception as e:
            result["issues"].append(f"链接验证错误: {e}")

        return result

    def _validate_docs_config(self) -> Dict[str, Any]:
        """验证文档配置"""
        result = {
            "config_valid": False,
            "theme_configured": False,
            "plugins_configured": False,
            "nav_configured": False,
            "issues": [],
        }

        try:
            # 检查配置基本结构
            if "theme" in self.config:
                result["theme_configured"] = True
                if self.config["theme"].get("name") == "material":
                    result["theme_name"] = "material"
                else:
                    result["issues"].append("建议使用material主题")
            else:
                result["issues"].append("缺少主题配置")

            # 检查插件配置
            if "plugins" in self.config:
                result["plugins_configured"] = True
            else:
                result["issues"].append("缺少插件配置")

            # 检查导航配置
            if "nav" in self.config:
                result["nav_configured"] = True
            else:
                result["issues"].append("缺少导航配置")

            result["config_valid"] = len(result["issues"]) == 0

        except Exception as e:
            result["issues"].append(f"配置验证错误: {e}")

        return result

    async def _stage_build(self) -> None:
        """阶段4: 构建文档"""
        stage_name = "build"
        logger.info("🔨 阶段4: 构建文档")

        stage_result = {"start_time": datetime.now().isoformat(), "build": {}}

        try:
            # 清理之前的构建
            if self.site_dir.exists():
                shutil.rmtree(self.site_dir)
                logger.info("🧹 清理之前的构建文件")

            # 执行MkDocs构建
            cmd = ["mkdocs", "build", "--verbose"]
            result = subprocess.run(cmd, cwd=self.project_root, capture_output=True, text=True)

            if result.returncode == 0:
                # 统计构建结果
                html_files = list(self.site_dir.rglob("*.html"))
                css_files = list(self.site_dir.rglob("*.css"))
                js_files = list(self.site_dir.rglob("*.js"))

                stage_result["build"] = {
                    "success": True,
                    "html_pages": len(html_files),
                    "css_files": len(css_files),
                    "js_files": len(js_files),
                    "site_size": self._get_directory_size(self.site_dir),
                    "build_output": result.stdout[-500:] if result.stdout else "",
                    "build_time": datetime.now().isoformat(),
                }

                logger.info(f"✅ 构建成功: {len(html_files)} HTML页面")
            else:
                stage_result["build"] = {
                    "success": False,
                    "error": result.stderr,
                    "return_code": result.returncode,
                }
                raise Exception(f"MkDocs构建失败: {result.stderr}")

            stage_result["success"] = True
            stage_result["end_time"] = datetime.now().isoformat()

        except Exception as e:
            stage_result["success"] = False
            stage_result["error"] = str(e)
            stage_result["end_time"] = datetime.now().isoformat()
            raise

        self.pipeline_state["stages"][stage_name] = stage_result
        logger.info("✅ 文档构建完成")

    def _get_directory_size(self, directory: Path) -> str:
        """获取目录大小"""
        try:
            result = subprocess.run(["du", "-sh", str(directory)], capture_output=True, text=True)
            if result.returncode == 0:
                return result.stdout.split()[0]
        except Exception:
            pass
        return "未知"

    async def _stage_quality_check(self) -> None:
        """阶段5: 质量检查"""
        stage_name = "quality_check"
        logger.info("📈 阶段5: 质量检查")

        stage_result = {"start_time": datetime.now().isoformat(), "quality": {}}

        try:
            # 检查页面大小
            stage_result["quality"]["page_sizes"] = self._check_page_sizes()

            # 检查图片优化
            stage_result["quality"]["images"] = self._check_images()

            # 检查SEO优化
            stage_result["quality"]["seo"] = self._check_seo()

            # 检查性能
            stage_result["quality"]["performance"] = self._check_performance()

            stage_result["success"] = True
            stage_result["end_time"] = datetime.now().isoformat()

        except Exception as e:
            stage_result["success"] = False
            stage_result["error"] = str(e)
            stage_result["end_time"] = datetime.now().isoformat()
            raise

        self.pipeline_state["stages"][stage_name] = stage_result
        logger.info("✅ 质量检查完成")

    def _check_page_sizes(self) -> Dict[str, Any]:
        """检查页面大小"""
        result = {"total_pages": 0, "large_pages": [], "average_size": 0, "max_size": 0}

        try:
            html_files = list(self.site_dir.rglob("*.html"))
            sizes = []

            for html_file in html_files:
                size = html_file.stat().st_size
                sizes.append(size)

                if size > 50000:  # 大于50KB
                    result["large_pages"].append(
                        {"file": str(html_file.relative_to(self.site_dir)), "size": size}
                    )

            result["total_pages"] = len(html_files)
            if sizes:
                result["average_size"] = sum(sizes) / len(sizes)
                result["max_size"] = max(sizes)

        except Exception as e:
            logger.error(f"页面大小检查失败: {e}")

        return result

    def _check_images(self) -> Dict[str, Any]:
        """检查图片"""
        result = {"total_images": 0, "image_types": {}, "large_images": []}

        try:
            image_extensions = [".png", ".jpg", ".jpeg", ".gif", ".svg"]
            image_files = []

            for ext in image_extensions:
                files = list(self.site_dir.rglob(f"*{ext}"))
                image_files.extend(files)
                result["image_types"][ext.lstrip(".")] = len(files)

            result["total_images"] = len(image_files)

            # 检查大图片
            for img_file in image_files:
                size = img_file.stat().st_size
                if size > 1024 * 1024:  # 大于1MB
                    result["large_images"].append(
                        {"file": str(img_file.relative_to(self.site_dir)), "size": size}
                    )

        except Exception as e:
            logger.error(f"图片检查失败: {e}")

        return result

    def _check_seo(self) -> Dict[str, Any]:
        """检查SEO优化"""
        result = {
            "pages_with_title": 0,
            "pages_with_description": 0,
            "pages_with_h1": 0,
            "issues": [],
        }

        try:
            html_files = list(self.site_dir.rglob("*.html"))

            for html_file in html_files[:10]:  # 检查前10个页面作为样本
                try:
                    with open(html_file, "r", encoding="utf-8") as f:
                        content = f.read()

                    if "<title>" in content:
                        result["pages_with_title"] += 1

                    if 'name="description"' in content:
                        result["pages_with_description"] += 1

                    if "<h1" in content:
                        result["pages_with_h1"] += 1

                except Exception as e:
                    result["issues"].append(f"SEO检查失败 {html_file}: {e}")

        except Exception as e:
            logger.error(f"SEO检查失败: {e}")

        return result

    def _check_performance(self) -> Dict[str, Any]:
        """检查性能"""
        result = {"css_files": 0, "js_files": 0, "external_resources": 0, "issues": []}

        try:
            result["css_files"] = len(list(self.site_dir.rglob("*.css")))
            result["js_files"] = len(list(self.site_dir.rglob("*.js")))

            # 简单的外部资源检查
            index_file = self.site_dir / "index.html"
            if index_file.exists():
                with open(index_file, "r", encoding="utf-8") as f:
                    content = f.read()

                import re

                external_links = re.findall(r'https?://[^\s"\'<>]+', content)
                result["external_resources"] = len(external_links)

        except Exception as e:
            result["issues"].append(f"性能检查失败: {e}")

        return result

    async def _stage_deploy(self, deploy_target: str) -> None:
        """阶段6: 部署文档"""
        stage_name = "deploy"
        logger.info(f"🚀 阶段6: 部署到 {deploy_target}")

        stage_result = {"start_time": datetime.now().isoformat(), "deploy": {}}

        try:
            if deploy_target == "github-pages":
                await self._deploy_to_github_pages(stage_result)
            elif deploy_target == "s3":
                await self._deploy_to_s3(stage_result)
            elif deploy_target == "local":
                await self._deploy_local(stage_result)
            else:
                raise ValueError(f"不支持的部署目标: {deploy_target}")

            stage_result["success"] = True
            stage_result["end_time"] = datetime.now().isoformat()

        except Exception as e:
            stage_result["success"] = False
            stage_result["error"] = str(e)
            stage_result["end_time"] = datetime.now().isoformat()
            raise

        self.pipeline_state["stages"][stage_name] = stage_result
        logger.info("✅ 文档部署完成")

    async def _deploy_to_github_pages(self, stage_result: Dict[str, Any]) -> None:
        """部署到GitHub Pages"""
        try:
            # 检查是否在GitHub Actions环境中
            if os.getenv("GITHUB_ACTIONS"):
                logger.info("📝 检测到GitHub Actions环境，使用内置部署")
                stage_result["deploy"] = {
                    "method": "github_actions",
                    "url": f"https://{os.getenv('GITHUB_REPOSITORY_OWNER')}.github.io/{os.getenv('GITHUB_REPOSITORY_NAME')}/",
                }
            else:
                # 本地部署到gh-pages分支
                logger.info("📝 本地部署到gh-pages分支")

                # 检查gh-pages分支是否存在
                result = subprocess.run(["git", "branch", "-a"], capture_output=True, text=True)

                if "gh-pages" not in result.stdout:
                    # 创建gh-pages分支
                    subprocess.run(["git", "checkout", "--orphan", "gh-pages"], check=True)
                    subprocess.run(["git", "rm", "-rf", "."], check=True)
                else:
                    subprocess.run(["git", "checkout", "gh-pages"], check=True)

                # 复制构建文件
                if self.site_dir.exists():
                    subprocess.run(["cp", "-r", f"{self.site_dir}/.", "."], check=True)

                # 提交并推送
                subprocess.run(["git", "add", "."], check=True)
                subprocess.run(["git", "commit", "-m", "Deploy documentation"], check=True)
                subprocess.run(["git", "push", "origin", "gh-pages"], check=True)

                stage_result["deploy"] = {"method": "local_gh_pages", "branch": "gh-pages"}

        except Exception as e:
            raise Exception(f"GitHub Pages部署失败: {e}")

    async def _deploy_to_s3(self, stage_result: Dict[str, Any]) -> None:
        """部署到S3"""
        # 这里可以实现S3部署逻辑
        logger.warning("S3部署功能尚未实现")
        stage_result["deploy"] = {"method": "s3", "status": "not_implemented"}

    async def _deploy_local(self, stage_result: Dict[str, Any]) -> None:
        """本地部署"""
        try:
            # 创建本地部署目录
            deploy_dir = self.project_root / "deploy" / "docs"
            deploy_dir.mkdir(parents=True, exist_ok=True)

            # 复制文件
            if self.site_dir.exists():
                shutil.rmtree(deploy_dir)
                shutil.copytree(self.site_dir, deploy_dir)

            stage_result["deploy"] = {"method": "local", "path": str(deploy_dir)}

            logger.info(f"📁 文档已部署到本地: {deploy_dir}")

        except Exception as e:
            raise Exception(f"本地部署失败: {e}")

    def save_pipeline_report(self, output_path: Optional[str] = None) -> str:
        """
        保存流水线报告

        Args:
            output_path: 输出文件路径

        Returns:
            报告文件路径
        """
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = self.build_dir / f"pipeline_report_{timestamp}.json"

        try:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(self.pipeline_state, f, indent=2, ensure_ascii=False, default=str)

            logger.info(f"📄 流水线报告已保存: {output_path}")
            return str(output_path)

        except Exception as e:
            logger.error(f"保存报告失败: {e}")
            raise

    def print_pipeline_summary(self) -> None:
        """打印流水线摘要"""
        print("\n" + "=" * 60)
        print("📊 文档CI/CD流水线执行摘要")
        print("=" * 60)

        print(f"开始时间: {self.pipeline_state.get('start_time')}")
        print(f"结束时间: {self.pipeline_state.get('end_time')}")
        print(f"执行状态: {'✅ 成功' if self.pipeline_state.get('success') else '❌ 失败'}")

        if self.pipeline_state.get("errors"):
            print("\n❌ 错误信息:")
            for error in self.pipeline_state["errors"]:
                print(f"  - {error}")

        if self.pipeline_state.get("warnings"):
            print("\n⚠️ 警告信息:")
            for warning in self.pipeline_state["warnings"]:
                print(f"  - {warning}")

        print("\n📋 阶段执行情况:")
        for stage_name, stage_result in self.pipeline_state.get("stages", {}).items():
            status = "✅ 成功" if stage_result.get("success") else "❌ 失败"
            print(f"  - {stage_name}: {status}")

        print("=" * 60)


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="文档CI/CD流水线")
    parser.add_argument("--build", action="store_true", help="构建文档")
    parser.add_argument("--deploy", action="store_true", help="部署文档")
    parser.add_argument("--quality-check", action="store_true", help="质量检查")
    parser.add_argument(
        "--deploy-target",
        choices=["github-pages", "s3", "local"],
        default="github-pages",
        help="部署目标",
    )
    parser.add_argument("--config", default="mkdocs.yml", help="MkDocs配置文件")
    parser.add_argument("--report-output", help="报告输出路径")
    parser.add_argument("--full-pipeline", action="store_true", help="执行完整流水线")

    args = parser.parse_args()

    # 创建流水线实例
    pipeline = DocsCIPipeline(args.config)

    # 执行流水线
    if args.full_pipeline:
        result = await pipeline.run_full_pipeline(
            build=args.build or True,
            deploy=args.deploy,
            quality_check=args.quality_check,
            deploy_target=args.deploy_target,
        )
    else:
        # 默认执行完整流水线
        result = await pipeline.run_full_pipeline(
            build=True, deploy=args.deploy, quality_check=True, deploy_target=args.deploy_target
        )

    # 保存报告
    pipeline.save_pipeline_report(args.report_output)

    # 打印摘要
    pipeline.print_pipeline_summary()

    # 设置退出码
    sys.exit(0 if result.get("success") else 1)


if __name__ == "__main__":
    asyncio.run(main())
