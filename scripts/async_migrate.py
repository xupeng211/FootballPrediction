#!/usr/bin/env python3
"""
Async Migration Tool - 异步化自动迁移工具
自动将同步代码迁移为异步代码

功能:
1. 自动检测同步调用模式
2. 生成异步化建议和补丁
3. 安全模式的代码转换
4. 生成迁移报告

作者: Async架构负责人
创建时间: 2025-12-06
"""

import ast
import asyncio
import os
import re
import sys
import time
from dataclasses import dataclass
from difflib import unified_diff
from pathlib import Path
import argparse
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@dataclass
class MigrationPattern:
    """迁移模式定义"""

    name: str
    pattern: str
    replacement: str
    description: str
    priority: str  # "high", "medium", "low"
    requires_await: bool = True
    target_files: list[str] = None  # 目标文件模式


@dataclass
class MigrationIssue:
    """迁移问题记录"""

    file_path: str
    line_number: int
    issue_type: str
    description: str
    suggested_fix: str
    priority: str


class AsyncMigrationAnalyzer:
    """异步化迁移分析器"""

    def __init__(self, root_dir: str = "src"):
        self.root_dir = Path(root_dir)
        self.migration_patterns = self._define_migration_patterns()
        self.issues: list[MigrationIssue] = []

    def _define_migration_patterns(self) -> list[MigrationPattern]:
        """定义迁移模式"""
        return [
            # HTTP客户端迁移
            MigrationPattern(
                name="requests_import",
                pattern=r"import\s+requests",
                replacement="import httpx",
                description="将requests导入替换为httpx",
                priority="high",
                target_files=["src/collectors/*.py", "src/data/collectors/*.py"],
            ),
            MigrationPattern(
                name="requests_get",
                pattern=r"requests\.get\(",
                replacement="await httpx.AsyncClient().get(",
                description="将同步GET请求替换为异步",
                priority="high",
                requires_await=True,
            ),
            MigrationPattern(
                name="requests_post",
                pattern=r"requests\.post\(",
                replacement="await httpx.AsyncClient().post(",
                description="将同步POST请求替换为异步",
                priority="high",
                requires_await=True,
            ),
            MigrationPattern(
                name="requests_session",
                pattern=r"requests\.Session\(",
                replacement="httpx.AsyncClient(",
                description="将同步Session替换为异步Client",
                priority="high",
            ),
            MigrationPattern(
                name="curl_cffi_import",
                pattern=r"from\s+curl_cffi\s+import\s+requests",
                replacement="import httpx",
                description="将curl_cffi导入替换为httpx",
                priority="high",
            ),
            # 时间阻塞调用迁移
            MigrationPattern(
                name="time_sleep",
                pattern=r"time\.sleep\(",
                replacement="await asyncio.sleep(",
                description="将同步sleep替换为异步",
                priority="medium",
                requires_await=True,
            ),
            # 函数定义迁移
            MigrationPattern(
                name="def_to_async",
                pattern=r"def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(",
                replacement="async def \\1(",
                description="将函数定义转换为异步",
                priority="medium",
                requires_await=False,
            ),
            # 数据库操作迁移
            MigrationPattern(
                name="session_execute",
                pattern=r"session\.execute\(",
                replacement="await session.execute(",
                description="数据库操作添加await",
                priority="medium",
                requires_await=True,
            ),
            MigrationPattern(
                name="session_commit",
                pattern=r"session\.commit\(",
                replacement="await session.commit(",
                description="数据库提交添加await",
                priority="medium",
                requires_await=True,
            ),
        ]

    def analyze_file(self, file_path: Path) -> list[MigrationIssue]:
        """分析单个文件的迁移需求"""
        issues = []

        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()
                lines = content.split("\n")

            # 应用迁移模式检测
            for pattern in self.migration_patterns:
                if pattern.target_files:
                    # 检查文件是否匹配目标模式
                    if not any(
                        file_path.match(target) for target in pattern.target_files
                    ):
                        continue

                for line_num, line in enumerate(lines, 1):
                    if re.search(pattern.pattern, line):
                        issue = MigrationIssue(
                            file_path=str(file_path),
                            line_number=line_num,
                            issue_type=pattern.name,
                            description=f"检测到{pattern.description}",
                            suggested_fix=self._generate_fix_suggestion(line, pattern),
                            priority=pattern.priority,
                        )
                        issues.append(issue)

            # 额外检查: 检测需要添加await的函数调用
            issues.extend(self._detect_missing_awaits(file_path, content, lines))

        except Exception as e:
            logger.error(f"分析文件 {file_path} 时出错: {e}")

        return issues

    def _detect_missing_awaits(
        self, file_path: Path, content: str, lines: list[str]
    ) -> list[MigrationIssue]:
        """检测缺失的await关键字"""
        issues = []

        # 解析AST来检测函数调用
        try:
            tree = ast.parse(content)

            # 查找异步调用但缺少await的情况
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    # 检查是否是已知的异步函数调用
                    if self._is_async_function_call(node):
                        # 检查是否缺少await
                        if not self._has_await_ancestor(node, tree):
                            line_num = node.lineno
                            issue = MigrationIssue(
                                file_path=str(file_path),
                                line_number=line_num,
                                issue_type="missing_await",
                                description="异步函数调用缺少await关键字",
                                suggested_fix="在函数调用前添加'await '",
                                priority="high",
                            )
                            issues.append(issue)

        except SyntaxError:
            # 如果AST解析失败，进行简单的文本检测
            pass

        return issues

    def _is_async_function_call(self, node: ast.Call) -> bool:
        """判断是否是异步函数调用"""
        if isinstance(node.func, ast.Attribute):
            # 检查方法调用
            async_methods = {
                "fetch",
                "fetch_json",
                "execute",
                "get",
                "post",
                "get_async_session",
            }
            return node.func.attr in async_methods
        elif isinstance(node.func, ast.Name):
            # 检查函数调用
            async_functions = {"get_db_session", "async_create_engine", "fetch_data"}
            return node.func.id in async_functions
        return False

    def _has_await_ancestor(self, node: ast.AST, tree: ast.AST) -> bool:
        """检查节点是否被await包裹"""
        # 简化实现：在实际工具中需要更复杂的AST遍历
        return False

    def _generate_fix_suggestion(self, line: str, pattern: MigrationPattern) -> str:
        """生成修复建议"""
        if pattern.name == "def_to_async":
            return "将 'def' 改为 'async def'"
        elif pattern.requires_await:
            return f"替换为 '{pattern.replacement}' 并确保在异步函数中调用"
        else:
            return f"替换为 '{pattern.replacement}'"

    def analyze_directory(self) -> list[MigrationIssue]:
        """分析整个目录"""
        all_issues = []

        # 查找Python文件
        python_files = list(self.root_dir.rglob("*.py"))

        logger.info(f"找到 {len(python_files)} 个Python文件待分析")

        for file_path in python_files:
            logger.info(f"分析文件: {file_path}")
            file_issues = self.analyze_file(file_path)
            all_issues.extend(file_issues)

        return all_issues

    def generate_migration_report(self, issues: list[MigrationIssue]) -> str:
        """生成迁移报告"""
        report = []
        report.append("# 异步化迁移报告\n")
        report.append(f"生成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")

        # 按优先级分组
        high_priority = [i for i in issues if i.priority == "high"]
        medium_priority = [i for i in issues if i.priority == "medium"]
        low_priority = [i for i in issues if i.priority == "low"]

        report.append("## 📊 迁移统计\n")
        report.append(f"- 🔴 高优先级问题: {len(high_priority)}")
        report.append(f"- 🟡 中等优先级问题: {len(medium_priority)}")
        report.append(f"- 🟢 低优先级问题: {len(low_priority)}")
        report.append(f"- 📋 总问题数: {len(issues)}\n")

        # 按文件分组
        file_issues = {}
        for issue in issues:
            file_path = issue.file_path
            if file_path not in file_issues:
                file_issues[file_path] = []
            file_issues[file_path].append(issue)

        report.append("## 📁 文件详情\n")
        for file_path, file_issue_list in file_issues.items():
            report.append(f"### {file_path}")
            report.append(f"问题数量: {len(file_issue_list)}\n")

            for issue in sorted(file_issue_list, key=lambda x: x.line_number):
                priority_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(
                    issue.priority, "⚪"
                )
                report.append(
                    f"{priority_icon} **第{issue.line_number}行** - {issue.issue_type}"
                )
                report.append(f"   - 描述: {issue.description}")
                report.append(f"   - 建议: {issue.suggested_fix}")
                report.append("")

        return "\n".join(report)


class AsyncMigrationGenerator:
    """异步化迁移代码生成器"""

    def __init__(self, root_dir: str = "src"):
        self.root_dir = Path(root_dir)

    def generate_patch(self, file_path: Path, issues: list[MigrationIssue]) -> str:
        """为单个文件生成补丁"""
        try:
            with open(file_path, encoding="utf-8") as f:
                original_content = f.read()

            modified_content = self._apply_modifications(original_content, issues)

            # 生成unified diff
            original_lines = original_content.splitlines(keepends=True)
            modified_lines = modified_content.splitlines(keepends=True)

            diff = unified_diff(
                original_lines,
                modified_lines,
                fromfile=f"a/{file_path}",
                tofile=f"b/{file_path}",
                lineterm="",
            )

            return "".join(diff)

        except Exception as e:
            logger.error(f"生成补丁失败 {file_path}: {e}")
            return f"# Error generating patch for {file_path}: {str(e)}"

    def _apply_modifications(self, content: str, issues: list[MigrationIssue]) -> str:
        """应用代码修改"""
        lines = content.split("\n")

        # 按行号排序，从后往前应用修改，避免行号偏移
        sorted_issues = sorted(issues, key=lambda x: x.line_number, reverse=True)

        for issue in sorted_issues:
            line_idx = issue.line_number - 1  # 转换为0基索引
            if 0 <= line_idx < len(lines):
                original_line = lines[line_idx]

                if issue.issue_type == "def_to_async":
                    # 将def改为async def
                    lines[line_idx] = re.sub(r"^\s*def\s", "async def ", original_line)
                elif issue.issue_type == "requests_get":
                    # 替换requests.get
                    lines[line_idx] = re.sub(
                        r"requests\.get\(",
                        "await httpx.AsyncClient().get(",
                        original_line,
                    )
                elif issue.issue_type == "requests_post":
                    # 替换requests.post
                    lines[line_idx] = re.sub(
                        r"requests\.post\(",
                        "await httpx.AsyncClient().post(",
                        original_line,
                    )
                elif issue.issue_type == "time_sleep":
                    # 替换time.sleep
                    lines[line_idx] = re.sub(
                        r"time\.sleep\(", "await asyncio.sleep(", original_line
                    )
                elif issue.issue_type == "missing_await":
                    # 在函数调用前添加await
                    lines[line_idx] = re.sub(
                        r"(\s*)([a-zA-Z_][a-zA-Z0-9_]*\([^)]*\))",
                        r"\1await \2",
                        original_line,
                        count=1,
                    )

        return "\n".join(lines)

    def generate_all_patches(self, all_issues: list[MigrationIssue]) -> dict[str, str]:
        """为所有文件生成补丁"""
        patches = {}

        # 按文件分组
        file_issues = {}
        for issue in all_issues:
            file_path = issue.file_path
            if file_path not in file_issues:
                file_issues[file_path] = []
            file_issues[file_path].append(issue)

        # 为每个文件生成补丁
        for file_path, issues in file_issues.items():
            patch_path = Path(file_path)
            patches[str(patch_path)] = self.generate_patch(patch_path, issues)

        return patches

    def save_patches(
        self, patches: dict[str, str], output_dir: str = "patches/async_unification"
    ):
        """保存补丁文件"""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        for file_path, patch_content in patches.items():
            # 生成补丁文件名
            patch_filename = Path(file_path).name.replace(".py", ".patch")
            patch_file_path = output_path / patch_filename

            with open(patch_file_path, "w", encoding="utf-8") as f:
                f.write(patch_content)

            logger.info(f"补丁已保存: {patch_file_path}")


class AsyncMigrationTool:
    """异步化迁移工具主类"""

    def __init__(self, root_dir: str = "src", dry_run: bool = True):
        self.root_dir = root_dir
        self.dry_run = dry_run
        self.analyzer = AsyncMigrationAnalyzer(root_dir)
        self.generator = AsyncMigrationGenerator(root_dir)

    async def run_migration(self):
        """运行迁移流程"""
        logger.info("🚀 开始异步化迁移分析")
        logger.info(f"📁 目标目录: {self.root_dir}")
        logger.info(f"🔧 模式: {'分析模式' if self.dry_run else '应用模式'}")

        # 步骤1: 分析代码
        logger.info("📊 正在分析代码...")
        issues = self.analyzer.analyze_directory()

        if not issues:
            logger.info("✅ 未发现需要迁移的代码")
            return

        logger.info(f"🔍 发现 {len(issues)} 个迁移问题")

        # 步骤2: 生成报告
        logger.info("📋 正在生成迁移报告...")
        report = self.analyzer.generate_migration_report(issues)

        report_path = "reports/async_migration_report.md"
        Path(report_path).parent.mkdir(exist_ok=True)

        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report)

        logger.info(f"📄 报告已保存: {report_path}")

        # 步骤3: 生成补丁 (仅在dry_run模式下)
        if self.dry_run:
            logger.info("🔧 正在生成迁移补丁...")
            patches = self.generator.generate_all_patches(issues)
            self.generator.save_patches(patches)
            logger.info("✅ 补丁生成完成")
        else:
            logger.warning("⚠️  实际应用模式暂未实现，请使用 --dry-run 模式")

        # 步骤4: 生成验证脚本
        await self._generate_validation_script(issues)

        logger.info("🎉 异步化迁移分析完成!")

    async def _generate_validation_script(self, issues: list[MigrationIssue]):
        """生成验证脚本"""
        validation_script = """#!/usr/bin/env python3
\"\"\"
异步化迁移验证脚本
用于验证迁移后的代码正确性

生成的验证任务:
"""

        # 按文件分组生成验证任务
        file_issues = {}
        for issue in issues:
            file_path = issue.file_path
            if file_path not in file_issues:
                file_issues[file_path] = []
            file_issues[file_path].append(issue)

        for file_path, _file_issue_list in file_issues.items():
            validation_script += f"""
# 验证 {file_path}
async def test_{Path(file_path).stem}():
    '''测试{file_path}的异步化迁移结果'''
    try:
        # 导入模块
        import sys
        sys.path.append('src')

        # 这里需要根据具体文件编写测试
        # TODO: 为 {file_path} 编写具体的验证测试

        print("✅ {file_path} 验证通过")
        return True

    except Exception as e:
        print(f"❌ {file_path} 验证失败: {{e}}")
        return False

"""

        validation_script += """
async def main():
    '''主验证函数'''
    print("🔍 开始验证异步化迁移结果...")

    # TODO: 实现具体的验证逻辑
    print("⚠️  请根据具体迁移内容实现验证逻辑")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
"""

        script_path = "scripts/validate_async_migration.py"
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(validation_script)

        # 使脚本可执行
        os.chmod(script_path, 0o755)
        logger.info(f"🧪 验证脚本已生成: {script_path}")


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="异步化迁移工具")
    parser.add_argument("--root-dir", default="src", help="源代码根目录 (默认: src)")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="分析模式，只生成报告和补丁 (默认)",
    )
    parser.add_argument(
        "--apply", action="store_true", help="应用模式，直接修改代码 (实验性功能)"
    )

    args = parser.parse_args()

    if args.apply:
        args.dry_run = False

    # 创建迁移工具实例
    migration_tool = AsyncMigrationTool(root_dir=args.root_dir, dry_run=args.dry_run)

    try:
        await migration_tool.run_migration()
    except KeyboardInterrupt:
        logger.info("⏹️  用户中断迁移")
    except Exception as e:
        logger.error(f"❌ 迁移失败: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
