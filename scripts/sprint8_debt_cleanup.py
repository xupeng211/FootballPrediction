#!/usr/bin/env python3
"""
Sprint 8 技术债务清理脚本

执行系统性的技术债务清理，包括：
1. 硬编码路径替换为环境变量
2. 调试语句清理
3. 不安全配置检查
4. 代码质量审计

Author: Football Prediction Team
Version: 1.0.0 (Sprint 8 - Production Ready)
"""

import ast
import os
import re
import sys
import logging
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
import json
from datetime import datetime

# 设置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class TechnicalDebtCleaner:
    """技术债务清理器"""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.src_root = project_root / "src"
        self.config_root = project_root / "src" / "config_secure.py"

        # 硬编码模式检测规则
        self.hardcoded_patterns = {
            "fotmob_api": r"https://www\.fotmob\.com/api",
            "localhost": r"localhost|127\.0\.0\.1",
            "file_paths": r'"/(app|tmp|var|usr|etc)/[^"]*"|\'/(app|tmp|var|usr|etc)/[^\']*\'',
            "debug_prints": r"print\s*\(",
            "debug_logs": r"logger\.debug\(",
            "hardcoded_ports": r":\d{4,5}",
        }

        # 需要环境变量化的路径映射
        self.path_mappings = {
            "/app/data": "DATA_DIR",
            "/app/logs": "LOG_DIR",
            "/app/models": "MODEL_DIR",
            "/app/cache": "CACHE_DIR",
        }

        # 已被正确环境变量化的配置文件
        self.safe_files = {
            "src/config_secure.py",
            "src/config.py",
        }

        self.cleanup_results = {
            "files_scanned": 0,
            "issues_found": 0,
            "issues_fixed": 0,
            "files_modified": [],
            "remaining_issues": [],
            "security_issues": [],
        }

    def run_full_cleanup(self) -> Dict[str, any]:
        """执行完整的技术债务清理"""
        logger.info("🚀 开始Sprint 8技术债务清理")

        # 1. 扫描所有Python文件
        python_files = self._find_python_files()
        self.cleanup_results["files_scanned"] = len(python_files)

        logger.info(f"📁 找到 {len(python_files)} 个Python文件")

        # 2. 检查配置文件的完整性
        self._verify_configuration_integrity()

        # 3. 清理硬编码路径
        self._cleanup_hardcoded_paths(python_files)

        # 4. 清理调试语句
        self._cleanup_debug_statements(python_files)

        # 5. 检查安全问题
        self._check_security_issues(python_files)

        # 6. 生成清理报告
        report = self._generate_cleanup_report()

        logger.info(
            f"✅ 技术债务清理完成: {self.cleanup_results['issues_fixed']}/{self.cleanup_results['issues_found']} 问题已修复"
        )

        return report

    def _find_python_files(self) -> List[Path]:
        """查找所有Python文件（排除tests和examples目录）"""
        python_files = []

        for py_file in self.src_root.rglob("*.py"):
            # 排除测试文件和示例文件
            if not any(
                part in str(py_file) for part in ["tests/", "examples/", "__pycache__"]
            ):
                python_files.append(py_file)

        return python_files

    def _verify_configuration_integrity(self):
        """验证配置文件的完整性"""
        logger.info("🔍 验证配置文件完整性")

        required_config_vars = [
            "FOTMOB_BASE_URL",
            "DB_HOST",
            "DB_PORT",
            "DB_NAME",
            "DB_USER",
            "DB_PASSWORD",
            "REDIS_HOST",
            "REDIS_PORT",
            "LOG_DIR",
            "DATA_DIR",
            "MODEL_DIR",
            "CACHE_DIR",
            "API_HOST",
            "API_PORT",
            "ENVIRONMENT",
        ]

        config_file = self.project_root / ".env.example"
        if config_file.exists():
            with open(config_file, "r") as f:
                env_content = f.read()

            missing_vars = []
            for var in required_config_vars:
                if var not in env_content:
                    missing_vars.append(var)

            if missing_vars:
                logger.warning(f"⚠️ 配置文件中缺少环境变量: {missing_vars}")
                self.cleanup_results["security_issues"].append(
                    {"type": "missing_config_vars", "details": missing_vars}
                )
            else:
                logger.info("✅ 配置文件完整性检查通过")
        else:
            logger.error("❌ 未找到 .env.example 配置文件")
            self.cleanup_results["security_issues"].append(
                {"type": "missing_env_example", "details": "Missing .env.example file"}
            )

    def _cleanup_hardcoded_paths(self, python_files: List[Path]):
        """清理硬编码路径"""
        logger.info("🔧 清理硬编码路径")

        for py_file in python_files:
            if str(py_file) in self.safe_files:
                continue

            try:
                with open(py_file, "r", encoding="utf-8") as f:
                    content = f.read()

                original_content = content
                file_modified = False

                # 检查并修复FotMob API硬编码
                fotmob_matches = re.findall(
                    self.hardcoded_patterns["fotmob_api"], content
                )
                if fotmob_matches:
                    logger.warning(f"📍 在 {py_file} 中发现硬编码的FotMob API地址")

                    # 替换为配置变量引用
                    content = re.sub(
                        r"https://www\.fotmob\.com/api",
                        "settings.fotmob.base_url",
                        content,
                    )

                    # 添加必要的导入
                    if "from src.config_unified import get_settings" not in content:
                        content = self._add_config_import(content)

                    file_modified = True
                    self.cleanup_results["issues_found"] += len(fotmob_matches)

                # 检查并修复文件路径硬编码
                path_matches = re.findall(
                    self.hardcoded_patterns["file_paths"], content
                )
                if path_matches:
                    logger.warning(
                        f"📍 在 {py_file} 中发现硬编码文件路径: {path_matches}"
                    )

                    for match in path_matches:
                        # 清理引号
                        clean_path = match.strip("\"'")
                        # 查找对应的映射
                        for hardcoded, env_var in self.path_mappings.items():
                            if clean_path.startswith(hardcoded):
                                # 替换为环境变量
                                replacement = f"os.path.join(os.getenv('{env_var}', '{hardcoded}'), '{clean_path[len(hardcoded)+1]}')"
                                content = content.replace(match, replacement)

                                # 添加os导入
                                if "import os" not in content:
                                    content = "import os\n" + content

                                file_modified = True
                                self.cleanup_results["issues_found"] += 1
                                break

                # 检查并修复localhost硬编码
                localhost_matches = re.findall(
                    self.hardcoded_patterns["localhost"], content
                )
                if localhost_matches and "config_secure" not in str(py_file):
                    # 只在非配置文件中报告localhost硬编码
                    for match in localhost_matches:
                        if "localhost" in match or "127.0.0.1" in match:
                            logger.info(
                                f"📝 {py_file} 中发现localhost引用，但已在配置中处理"
                            )
                            # 这些通常通过配置处理，不需要修改代码

                if file_modified:
                    with open(py_file, "w", encoding="utf-8") as f:
                        f.write(content)

                    self.cleanup_results["files_modified"].append(str(py_file))
                    self.cleanup_results["issues_fixed"] += content.count(
                        "os.path.join(os.getenv"
                    )

            except Exception as e:
                logger.error(f"❌ 处理文件 {py_file} 时出错: {e}")

    def _cleanup_debug_statements(self, python_files: List[Path]):
        """清理调试语句"""
        logger.info("🧹 清理调试语句")

        for py_file in python_files:
            if str(py_file) in self.safe_files or "examples/" in str(py_file):
                # 保留示例文件中的print语句
                continue

            try:
                with open(py_file, "r", encoding="utf-8") as f:
                    content = f.read()

                original_content = content
                file_modified = False

                # 移除调试print语句（保留示例代码中的）
                lines = content.split("\n")
                cleaned_lines = []

                for i, line in enumerate(lines):
                    # 检查是否为调试print语句
                    if re.search(self.hardcoded_patterns["debug_prints"], line):
                        # 排除示例和文档中的print语句
                        if not any(
                            keyword in line.lower()
                            for keyword in [
                                "example",
                                "demo",
                                "example:",
                                "usage:",
                                "todo:",
                            ]
                        ):
                            logger.info(f"🗑️ 移除调试语句: {line.strip()}")
                            file_modified = True
                            self.cleanup_results["issues_found"] += 1
                            continue

                    # 移除debug日志语句（保留重要的调试信息）
                    if re.search(self.hardcoded_patterns["debug_logs"], line):
                        # 保留包含重要信息的debug日志
                        if any(
                            keyword in line.lower()
                            for keyword in [
                                "error",
                                "exception",
                                "critical",
                                "security",
                            ]
                        ):
                            cleaned_lines.append(line)
                        else:
                            logger.info(f"🗑️ 移除debug日志: {line.strip()}")
                            file_modified = True
                            self.cleanup_results["issues_found"] += 1
                            continue

                    cleaned_lines.append(line)

                if file_modified:
                    content = "\n".join(cleaned_lines)
                    with open(py_file, "w", encoding="utf-8") as f:
                        f.write(content)

                    self.cleanup_results["files_modified"].append(str(py_file))
                    self.cleanup_results["issues_fixed"] += 1

            except Exception as e:
                logger.error(f"❌ 处理文件 {py_file} 时出错: {e}")

    def _check_security_issues(self, python_files: List[Path]):
        """检查安全问题"""
        logger.info("🔒 检查安全问题")

        security_patterns = {
            "sql_injection": r'execute\s*\(\s*["\'].*%.*["\']',
            "eval_usage": r"eval\s*\(",
            "exec_usage": r"exec\s*\(",
            "shell_command": r"system\s*\(|subprocess\.call\s*\(|os\.popen\s*\(",
            "hardcoded_secrets": r'password\s*=\s*["\'][^"\']*["\']|secret\s*=\s*["\'][^"\']*["\']|key\s*=\s*["\'][^"\']*["\']',
        }

        for py_file in python_files:
            try:
                with open(py_file, "r", encoding="utf-8") as f:
                    content = f.read()

                for issue_type, pattern in security_patterns.items():
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    if matches:
                        # 检查是否在注释中或测试中
                        for match in matches:
                            line_num = content[: content.find(match)].count("\n") + 1
                            line_content = content.split("\n")[line_num - 1]

                            # 排除注释和测试代码
                            if (
                                not line_content.strip().startswith("#")
                                and "test" not in str(py_file).lower()
                            ):
                                self.cleanup_results["security_issues"].append(
                                    {
                                        "type": issue_type,
                                        "file": str(py_file),
                                        "line": line_num,
                                        "content": line_content.strip(),
                                    }
                                )
                                logger.warning(
                                    f"🚨 安全问题发现 ({issue_type}): {py_file}:{line_num}"
                                )

            except Exception as e:
                logger.error(f"❌ 检查文件 {py_file} 安全性时出错: {e}")

    def _add_config_import(self, content: str) -> str:
        """添加配置导入语句"""
        # 检查是否已有导入语句
        if (
            "from src.config_unified import" in content
            or "import src.config_unified_secure" in content
        ):
            return content

        # 找到合适的导入位置
        lines = content.split("\n")
        import_position = 0

        for i, line in enumerate(lines):
            if line.startswith("import ") or line.startswith("from "):
                import_position = i + 1
            elif line.strip() == "" and import_position > 0:
                break

        # 添加导入语句
        lines.insert(import_position, "from src.config_unified import get_settings")
        lines.insert(import_position + 1, "settings = get_settings()")
        lines.insert(import_position + 2, "")

        return "\n".join(lines)

    def _generate_cleanup_report(self) -> Dict[str, any]:
        """生成清理报告"""
        logger.info("📊 生成清理报告")

        report = {
            "timestamp": datetime.now().isoformat(),
            "summary": self.cleanup_results,
            "recommendations": [],
        }

        # 生成建议
        if self.cleanup_results["issues_found"] > self.cleanup_results["issues_fixed"]:
            report["recommendations"].append("部分问题需要手动修复，请查看剩余问题列表")

        if self.cleanup_results["security_issues"]:
            report["recommendations"].append("发现安全问题需要立即处理")

        if len(self.cleanup_results["files_modified"]) > 0:
            report["recommendations"].append("已修复技术债务，建议运行完整测试套件验证")

        # 保存报告
        report_file = self.project_root / "sprint8_cleanup_report.json"
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False, default=str)

        logger.info(f"📄 清理报告已保存: {report_file}")

        return report

    def generate_production_checklist(self) -> str:
        """生成生产环境检查清单"""
        logger.info("📋 生成生产环境检查清单")

        checklist = """# Sprint 8 生产环境就绪检查清单

## 🔒 安全检查
- [ ] 所有硬编码路径已替换为环境变量
- [ ] 所有调试语句已清理
- [ ] 安全漏洞已修复
- [ ] API密钥已通过环境变量配置
- [ ] 数据库连接使用加密
- [ ] CORS配置正确

## 🏗️ 配置检查
- [ ] 环境变量配置完整 (.env.production)
- [ ] 数据库连接测试通过
- [ ] Redis连接测试通过
- [ ] 外部API连接测试通过
- [ ] 日志配置正确
- [ ] 监控配置正确

## 📊 性能检查
- [ ] 应用启动时间正常
- [ ] 内存使用在预期范围
- [ ] CPU使用在预期范围
- [ ] 响应时间符合要求
- [ ] 并发处理能力测试通过
- [ ] 数据库查询优化完成

## 🧪 测试检查
- [ ] 单元测试通过率 100%
- [ ] 集成测试通过率 100%
- [ ] 覆盖率达到目标 (>85%)
- [ ] 性能测试通过
- [ ] 安全测试通过
- [ ] 压力测试通过

## 🚀 部署检查
- [ ] Docker镜像构建成功
- [ ] 容器启动正常
- [ ] 健康检查通过
- [ ] 日志收集正常
- [ ] 监控指标正常
- [ ] 备份策略就绪

## 📝 文档检查
- [ ] API文档完整
- [ ] 部署文档完整
- [ ] 运维手册完整
- [ ] 故障排查文档完整
- [ ] 紧急响应计划就绪

---

生成时间: {timestamp}
版本: Sprint 8 v1.0.0
""".format(
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )

        checklist_file = self.project_root / "PRODUCTION_READINESS_CHECKLIST.md"
        with open(checklist_file, "w", encoding="utf-8") as f:
            f.write(checklist)

        logger.info(f"📄 生产环境检查清单已保存: {checklist_file}")
        return str(checklist_file)


def main():
    """主函数"""
    project_root = Path(__file__).parent.parent

    if not project_root.exists():
        logger.error(f"❌ 项目根目录不存在: {project_root}")
        sys.exit(1)

    cleaner = TechnicalDebtCleaner(project_root)

    try:
        # 执行完整清理
        report = cleaner.run_full_cleanup()

        # 生成检查清单
        checklist_file = cleaner.generate_production_checklist()

        print(f"\n🎉 Sprint 8 技术债务清理完成!")
        print(f"📁 扫描文件数: {report['summary']['files_scanned']}")
        print(f"🔍 发现问题数: {report['summary']['issues_found']}")
        print(f"✅ 修复问题数: {report['summary']['issues_fixed']}")
        print(f"📝 修改文件数: {len(report['summary']['files_modified'])}")
        print(f"🚨 安全问题数: {len(report['summary']['security_issues'])}")
        print(f"📋 检查清单: {checklist_file}")

        if report["recommendations"]:
            print(f"\n💡 建议:")
            for rec in report["recommendations"]:
                print(f"   • {rec}")

        if report["summary"]["security_issues"]:
            print(f"\n⚠️ 安全问题需要立即处理:")
            for issue in report["summary"]["security_issues"]:
                print(
                    f"   • {issue['type']}: {issue['file']}:{issue.get('line', 'N/A')}"
                )

        return 0 if len(report["summary"]["security_issues"]) == 0 else 1

    except Exception as e:
        logger.error(f"❌ 技术债务清理失败: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
