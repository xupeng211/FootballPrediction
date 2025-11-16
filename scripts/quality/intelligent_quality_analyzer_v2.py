#!/usr/bin/env python3
"""
企业级智能质量分析引擎 v2.0
基于Issue #159 70.1%覆盖率成果构建AI驱动的质量分析系统
实现自动化缺陷检测、质量评估和改进建议生成
"""

import ast
import time
import json
import os
import re
import threading
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import concurrent.futures
from functools import lru_cache
import hashlib

class QualitySeverity(Enum):
    """质量问题严重程度"""
    CRITICAL = "CRITICAL"    # 严重问题，必须立即修复
    HIGH = "HIGH"           # 高优先级问题
    MEDIUM = "MEDIUM"       # 中等优先级问题
    LOW = "LOW"            # 低优先级问题
    INFO = "INFO"          # 信息性提示

class IssueCategory(Enum):
    """问题分类"""
    SYNTAX = "syntax"           # 语法错误
    IMPORT = "import"           # 导入问题
    COMPLEXITY = "complexity"   # 复杂度过高
    SECURITY = "security"       # 安全漏洞
    PERFORMANCE = "performance" # 性能问题
    TESTING = "testing"         # 测试覆盖
    DOCUMENTATION = "docs"      # 文档缺失
    STYLE = "style"            # 代码风格
    ARCHITECTURE = "arch"      # 架构问题
    DEPENDENCY = "deps"        # 依赖问题

@dataclass
class QualityIssue:
    """质量问题数据结构"""
    issue_id: str
    severity: QualitySeverity
    category: IssueCategory
    title: str
    description: str
    file_path: str
    line_number: Optional[int] = None
    column_number: Optional[int] = None
    end_line_number: Optional[int] = None
    rule_name: str = ""
    effort_estimate: str = "5min"
    auto_fixable: bool = False
    suggestion: str = ""
    code_snippet: Optional[str] = None
    confidence_score: float = 1.0
    tags: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class FileQualityMetrics:
    """文件质量指标"""
    file_path: str
    total_issues: int
    critical_issues: int
    high_issues: int
    medium_issues: int
    low_issues: int
    complexity_score: float
    maintainability_index: float
    test_coverage: float
    documentation_score: float
    security_score: float
    performance_score: float
    overall_quality_score: float
    lines_of_code: int
    technical_debt: float  # 技术债（小时）
    improvement_suggestions: List[str] = field(default_factory=list)

@dataclass
class ProjectQualityReport:
    """项目质量报告"""
    project_name: str
    analysis_time: datetime
    total_files: int
    total_issues: int
    total_lines_of_code: int
    overall_quality_score: float
    grade: str  # A+, A, B+, B, C+, C, D, F
    issue_distribution: Dict[IssueCategory, int]
    severity_distribution: Dict[QualitySeverity, int]
    top_issues: List[QualityIssue]
    file_metrics: List[FileQualityMetrics]
    improvement_roadmap: List[Dict[str, Any]]
    technical_debt_total: float
    quality_trends: Dict[str, float] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)

class QualityRule:
    """质量规则基类"""

    def __init__(self, name: str, description: str, severity: QualitySeverity):
        self.name = name
        self.description = description
        self.severity = severity
        self.enabled = True
        self.patterns = []
        self.exceptions = []

    def analyze(self,
    file_path: Path,
    tree: ast.AST,
    content: str) -> List[QualityIssue]:
        """分析文件并生成质量问题"""
        raise NotImplementedError

    def generate_issue_id(self,
    file_path: str,
    rule_name: str,
    line: int = None) -> str:
        """生成唯一问题ID"""
        content = f"{file_path}:{rule_name}:{line or 0}"
        return hashlib.md5(content.encode()).hexdigest()[:12]

class SyntaxErrorRule(QualityRule):
    """语法错误检测规则"""

    def __init__(self):
        super().__init__(
            name="syntax_error_detection",
            description="检测Python语法错误",
            severity=QualitySeverity.CRITICAL
        )

    def analyze(self,
    file_path: Path,
    tree: ast.AST,
    content: str) -> List[QualityIssue]:
        """检测语法错误"""
        issues = []

        # 如果AST解析失败，说明有语法错误
        if tree is None:
            # 尝试解析错误信息
            try:
                ast.parse(content)
            except SyntaxError as e:
                issue = QualityIssue(
                    issue_id=self.generate_issue_id(str(file_path),
    self.name,
    e.lineno),

                    severity=self.severity,
                    category=IssueCategory.SYNTAX,
                    title="Python语法错误",
                    description=f"语法错误: {e.msg}",
                    file_path=str(file_path),
                    line_number=e.lineno,
                    column_number=e.offset,
                    rule_name=self.name,
                    effort_estimate="30min",
                    auto_fixable=False,
                    suggestion="修复Python语法错误，确保代码符合Python语法规范",
                    code_snippet=self._extract_error_line(content, e.lineno),
                    confidence_score=1.0,
                    tags=["syntax", "parse_error", "blocking"]
                )
                issues.append(issue)

        return issues

    def _extract_error_line(self, content: str, line_num: int) -> str:
        """提取错误代码行"""
        lines = content.split('\n')
        if 1 <= line_num <= len(lines):
            return lines[line_num - 1].strip()
        return ""

class ImportAnalysisRule(QualityRule):
    """导入分析规则"""

    def __init__(self):
        super().__init__(
            name="import_analysis",
            description="分析导入语句质量和潜在问题",
            severity=QualitySeverity.MEDIUM
        )

    def analyze(self,
    file_path: Path,
    tree: ast.AST,
    content: str) -> List[QualityIssue]:
        """分析导入问题"""
        issues = []

        if tree is None:
            return issues

        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append({
                        'type': 'import',
                        'module': alias.name,
                        'alias': alias.asname,
                        'line': node.lineno
                    })
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    imports.append({
                        'type': 'import_from',
                        'module': module,
                        'name': alias.name,
                        'alias': alias.asname,
                        'line': node.lineno
                    })

        # 检测导入问题
        self._check_unused_imports(file_path, imports, content, issues)
        self._check_circular_imports(file_path, imports, issues)
        self._check_import_ordering(file_path, imports, issues)
        self._check_builtin_shadowing(file_path, imports, issues)

        return issues

    def _check_unused_imports(self,
    file_path: Path,
    imports: List[Dict],
    content: str,
    issues: List[QualityIssue]):
        """检测未使用的导入"""
        content_without_imports = content
        for imp in imports:
            if imp['type'] == 'import':
                name = imp['alias'] or imp['module'].split('.')[0]
            else:
                name = imp['alias'] or imp['name']

            # 检查是否在代码中使用
            pattern = r'\b' + re.escape(name) + r'\b'
            matches = re.findall(pattern, content_without_imports)

            # 排除导入语句本身
            if len(matches) <= 1:
                issue = QualityIssue(
                    issue_id=self.generate_issue_id(str(file_path),
    "unused_import",
    imp['line']),

                    severity=QualitySeverity.LOW,
                    category=IssueCategory.IMPORT,
                    title="未使用的导入",
                    description=f"导入的 '{name}' 可能未在代码中使用",
                    file_path=str(file_path),
                    line_number=imp['line'],
                    rule_name="unused_import",
                    effort_estimate="2min",
                    auto_fixable=True,
                    suggestion=f"删除未使用的导入: {name}",
                    tags=["import", "unused", "cleanup"]
                )
                issues.append(issue)

    def _check_circular_imports(self,
    file_path: Path,
    imports: List[Dict],
    content: str,
    issues: List[QualityIssue]):
        """检测循环导入（简化版本）"""
        _file_path_str = str(file_path)

        for imp in imports:
            if imp['type'] == 'import_from':
                module = imp['module']
                if module and module.startswith('.'):
                    # 相对导入可能有循环依赖问题
                    if module.count('.') >= 3:  # 深层相对导入
                        issue = QualityIssue(
                            issue_id=self.generate_issue_id(str(file_path),
    "deep_relative_import",
    imp['line']),

                            severity=QualitySeverity.MEDIUM,
                            category=IssueCategory.IMPORT,
                            title="深层相对导入",
                            description=f"深层相对导入可能导致循环依赖: {module}",
                            file_path=str(file_path),
                            line_number=imp['line'],
                            rule_name="deep_relative_import",
                            effort_estimate="10min",
                            auto_fixable=False,
                            suggestion="考虑重构模块结构以减少相对导入层级",
                            tags=["import", "circular", "architecture"]
                        )
                        issues.append(issue)

    def _check_import_ordering(self,
    file_path: Path,
    imports: List[Dict],
    content: str,
    issues: List[QualityIssue]):
        """检测导入顺序"""
        if len(imports) < 2:
            return

        # 检查导入顺序：标准库 -> 第三方库 -> 本地模块
        standard_libs = {'os', 'sys', 'json', 'datetime', 'pathlib', 'typing', 'dataclasses', 'enum', 'collections', 'functools', 'threading', 'concurrent', 'hashlib', 're'}

        prev_type = None
        for imp in imports:
            if imp['type'] == 'import':
                module_name = imp['module'].split('.')[0]
            else:
                module_name = imp['module'].split('.')[0] if imp['module'] else ''

            if module_name in standard_libs:
                current_type = 'standard'
            elif module_name.startswith(('src', 'tests')):
                current_type = 'local'
            else:
                current_type = 'third_party'

            if prev_type and self._compare_import_types(prev_type, current_type) > 0:
                issue = QualityIssue(
                    issue_id=self.generate_issue_id(str(file_path),
    "import_order",
    imp['line']),

                    severity=QualitySeverity.LOW,
                    category=IssueCategory.STYLE,
                    title="导入顺序不规范",
                    description=f"导入顺序不符合PEP8规范: {module_name}",
                    file_path=str(file_path),
                    line_number=imp['line'],
                    rule_name="import_order",
                    effort_estimate="2min",
                    auto_fixable=True,
                    suggestion="按照标准库、第三方库、本地模块的顺序重新排列导入",
                    tags=["import", "style", "pep8"]
                )
                issues.append(issue)
                break

            prev_type = current_type

    def _compare_import_types(self, type1: str, type2: str) -> int:
        """比较导入类型优先级"""
        order = {'standard': 0, 'third_party': 1, 'local': 2}
        return order[type1] - order[type2]

    def _check_builtin_shadowing(self,
    file_path: Path,
    imports: List[Dict],
    content: str,
    issues: List[QualityIssue]):
        """检测内置函数遮蔽"""
        builtins = {'open', 'len', 'str', 'int', 'list', 'dict', 'set', 'tuple', 'range', 'enumerate', 'zip', 'map', 'filter'}

        for imp in imports:
            if imp['type'] == 'import':
                name = imp['alias'] or imp['module'].split('.')[0]
            else:
                name = imp['alias'] or imp['name']

            if name in builtins:
                issue = QualityIssue(
                    issue_id=self.generate_issue_id(str(file_path),
    "builtin_shadowing",
    imp['line']),

                    severity=QualitySeverity.MEDIUM,
                    category=IssueCategory.IMPORT,
                    title="遮蔽内置函数",
                    description=f"导入遮蔽了Python内置函数: {name}",
                    file_path=str(file_path),
                    line_number=imp['line'],
                    rule_name="builtin_shadowing",
                    effort_estimate="5min",
                    auto_fixable=True,
                    suggestion=f"使用别名避免遮蔽内置函数: import ... as {name}_alias",
                    tags=["import", "builtin", "naming"]
                )
                issues.append(issue)

class ComplexityAnalysisRule(QualityRule):
    """复杂度分析规则"""

    def __init__(self):
        super().__init__(
            name="complexity_analysis",
            description="分析代码复杂度，识别过于复杂的代码",
            severity=QualitySeverity.MEDIUM
        )
        self.max_complexity = 10
        self.max_function_lines = 50
        self.max_class_lines = 200

    def analyze(self,
    file_path: Path,
    tree: ast.AST,
    content: str) -> List[QualityIssue]:
        """分析复杂度问题"""
        issues = []

        if tree is None:
            return issues

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                self._analyze_function_complexity(file_path, node, content, issues)
            elif isinstance(node, ast.ClassDef):
                self._analyze_class_complexity(file_path, node, content, issues)

        return issues

    def _analyze_function_complexity(self,
    file_path: Path,
    node: ast.FunctionDef,
    content: str,
    issues: List[QualityIssue]):
        """分析函数复杂度"""
        # 计算圈复杂度
        complexity = self._calculate_cyclomatic_complexity(node)

        if complexity > self.max_complexity:
            issue = QualityIssue(
                issue_id=self.generate_issue_id(str(file_path),
    "high_complexity",
    node.lineno),

                severity=QualitySeverity.MEDIUM,
                category=IssueCategory.COMPLEXITY,
                title="函数复杂度过高",
                description=f"函数 '{node.name}' 的圈复杂度为 {complexity}，超过推荐值 {self.max_complexity}",
                file_path=str(file_path),
                line_number=node.lineno,
                rule_name="high_complexity",
                effort_estimate=f"{complexity * 5}min",
                auto_fixable=False,
                suggestion="考虑将复杂函数拆分为多个小函数，使用早期返回减少嵌套",
                tags=["complexity", "refactoring", "maintainability"],
                confidence_score=0.9
            )
            issues.append(issue)

        # 检查函数长度
        if hasattr(node, 'end_lineno') and node.end_lineno:
            lines = node.end_lineno - node.lineno + 1
            if lines > self.max_function_lines:
                issue = QualityIssue(
                    issue_id=self.generate_issue_id(str(file_path),
    "long_function",
    node.lineno),

                    severity=QualitySeverity.LOW,
                    category=IssueCategory.COMPLEXITY,
                    title="函数过长",
                    description=f"函数 '{node.name}' 有 {lines} 行代码，超过推荐值 {self.max_function_lines}",
                    file_path=str(file_path),
                    line_number=node.lineno,
                    rule_name="long_function",
                    effort_estimate="15min",
                    auto_fixable=False,
                    suggestion="将长函数拆分为多个职责单一的小函数",
                    tags=["complexity", "length", "refactoring"]
                )
                issues.append(issue)

    def _analyze_class_complexity(self,
    file_path: Path,
    node: ast.ClassDef,
    content: str,
    issues: List[QualityIssue]):
        """分析类复杂度"""
        if hasattr(node, 'end_lineno') and node.end_lineno:
            lines = node.end_lineno - node.lineno + 1
            if lines > self.max_class_lines:
                issue = QualityIssue(
                    issue_id=self.generate_issue_id(str(file_path),
    "large_class",
    node.lineno),

                    severity=QualitySeverity.MEDIUM,
                    category=IssueCategory.COMPLEXITY,
                    title="类过大",
                    description=f"类 '{node.name}' 有 {lines} 行代码，超过推荐值 {self.max_class_lines}",
                    file_path=str(file_path),
                    line_number=node.lineno,
                    rule_name="large_class",
                    effort_estimate="30min",
                    auto_fixable=False,
                    suggestion="考虑将大类拆分为多个职责单一的小类，使用组合模式",
                    tags=["complexity", "design", "refactoring"]
                )
                issues.append(issue)

    def _calculate_cyclomatic_complexity(self, node: ast.FunctionDef) -> int:
        """计算圈复杂度"""
        complexity = 1  # 基础复杂度

        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.AsyncFor)):
                complexity += 1
            elif isinstance(child, ast.ExceptHandler):
                complexity += 1
            elif isinstance(child, ast.With, ast.AsyncWith):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1

        return complexity

class SecurityAnalysisRule(QualityRule):
    """安全分析规则"""

    def __init__(self):
        super().__init__(
            name="security_analysis",
            description="检测潜在的安全漏洞和问题",
            severity=QualitySeverity.HIGH
        )
        self.dangerous_functions = {
            'eval': '代码注入风险',
            'exec': '代码执行风险',
            'compile': '代码编译风险',
            '__import__': '模块导入风险',
            'open': '文件操作风险',
            'input': '输入风险（在特定上下文）'
        }
        self.sensitive_patterns = [
            (r'password\s*=\s*["\'][^"\']+["\']', '硬编码密码'),
            (r'secret\s*=\s*["\'][^"\']+["\']', '硬编码密钥'),
            (r'token\s*=\s*["\'][^"\']+["\']', '硬编码令牌'),
            (r'api_key\s*=\s*["\'][^"\']+["\']', '硬编码API密钥'),
        ]

    def analyze(self,
    file_path: Path,
    tree: ast.AST,
    content: str) -> List[QualityIssue]:
        """检测安全问题"""
        issues = []

        # 检测危险的函数调用
        self._check_dangerous_functions(file_path, tree, content, issues)

        # 检测硬编码敏感信息
        self._check_hardcoded_secrets(file_path, content, issues)

        # 检测SQL注入风险
        self._check_sql_injection(file_path, tree, content, issues)

        return issues

    def _check_dangerous_functions(self,
    file_path: Path,
    tree: ast.AST,
    content: str,
    issues: List[QualityIssue]):
        """检测危险函数调用"""
        if tree is None:
            return

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    func_name = node.func.id
                    if func_name in self.dangerous_functions:
                        risk_desc = self.dangerous_functions[func_name]
                        issue = QualityIssue(
                            issue_id=self.generate_issue_id(str(file_path),
    "dangerous_function",
    node.lineno),

                            severity=QualitySeverity.HIGH,
                            category=IssueCategory.SECURITY,
                            title="使用危险函数",
                            description=f"使用了危险函数 '{func_name}': {risk_desc}",
                            file_path=str(file_path),
                            line_number=node.lineno,
                            rule_name="dangerous_function",
                            effort_estimate="30min",
                            auto_fixable=False,
                            suggestion=f"避免使用 {func_name}，考虑更安全的替代方案",
                            tags=["security", "dangerous", "function"],
                            confidence_score=0.8
                        )
                        issues.append(issue)

    def _check_hardcoded_secrets(self,
    file_path: Path,
    content: str,
    issues: List[QualityIssue]):
        """检测硬编码敏感信息"""
        lines = content.split('\n')
        for line_num, line in enumerate(lines, 1):
            for pattern, desc in self.sensitive_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    # 排除注释行
                    stripped = line.strip()
                    if stripped.startswith('#'):
                        continue

                    issue = QualityIssue(
                        issue_id=self.generate_issue_id(str(file_path),
    "hardcoded_secret",
    line_num),

                        severity=QualitySeverity.CRITICAL,
                        category=IssueCategory.SECURITY,
                        title="硬编码敏感信息",
                        description=f"发现硬编码的敏感信息: {desc}",
                        file_path=str(file_path),
                        line_number=line_num,
                        rule_name="hardcoded_secret",
                        effort_estimate="10min",
                        auto_fixable=False,
                        suggestion="使用环境变量或配置文件存储敏感信息，不要硬编码在代码中",
                        tags=["security", "secrets", "hardcoded"],
                        confidence_score=0.9
                    )
                    issues.append(issue)

    def _check_sql_injection(self,
    file_path: Path,
    tree: ast.AST,
    content: str,
    issues: List[QualityIssue]):
        """检测SQL注入风险（简化版本）"""
        if tree is None:
            return

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                # 检测字符串拼接的SQL查询
                if isinstance(node.func, ast.Attribute):
                    if node.func.attr in ['execute', 'query', 'run']:
                        for arg in node.args:
                            if isinstance(arg,
    ast.BinOp) and isinstance(arg.op,
    ast.Add):
                                issue = QualityIssue(
                                    issue_id=self.generate_issue_id(str(file_path),
    "sql_injection",
    node.lineno),

                                    severity=QualitySeverity.HIGH,
                                    category=IssueCategory.SECURITY,
                                    title="潜在SQL注入风险",
                                    description="检测到使用字符串拼接构造SQL查询，可能存在SQL注入风险",
                                    file_path=str(file_path),
                                    line_number=node.lineno,
                                    rule_name="sql_injection",
                                    effort_estimate="20min",
                                    auto_fixable=True,
                                    suggestion="使用参数化查询或ORM来避免SQL注入",
                                    tags=["security", "sql", "injection"],
                                    confidence_score=0.7
                                )
                                issues.append(issue)

class IntelligentQualityAnalyzerV2:
    """智能质量分析引擎 v2.0"""

    def __init__(self, max_workers: int = 4, cache_size: int = 256):
        self.project_root = Path(__file__).parent.parent
        self.max_workers = max_workers
        self.cache_size = cache_size

        # 质量规则
        self.rules = [
            SyntaxErrorRule(),
            ImportAnalysisRule(),
            ComplexityAnalysisRule(),
            SecurityAnalysisRule(),
        ]

        # 缓存
        self._analysis_cache = {}
        self._cache_lock = threading.Lock()

        # 统计信息
        self.analysis_stats = {
            'files_analyzed': 0,
            'issues_found': 0,
            'analysis_time': 0,
            'cache_hits': 0
        }

        print("🤖 智能质量分析引擎 v2.0 已初始化")
        print(f"📊 分析规则: {len(self.rules)}个")
        print(f"⚡ 并行处理: {max_workers}线程")
        print(f"💾 缓存容量: {cache_size}项")

    @lru_cache(maxsize=256)
    def _is_python_file(self, file_path: Path) -> bool:
        """判断是否为Python文件"""
        return file_path.suffix == '.py' and file_path.is_file()

    def discover_python_files(self, paths: List[Path] = None) -> List[Path]:
        """发现Python文件"""
        if paths is None:
            paths = [self.project_root / "src", self.project_root / "tests"]

        python_files = []
        for path in paths:
            if path.is_dir():
                python_files.extend(path.rglob("*.py"))
            elif path.is_file() and path.suffix == ".py":
                python_files.append(path)

        # 过滤排除文件
        exclude_patterns = {
            "__pycache__", ".pytest_cache", ".git", "venv", ".venv",
            "node_modules", ".tox", "build", "dist"
        }

        filtered_files = []
        for file_path in python_files:
            if any(pattern in str(file_path) for pattern in exclude_patterns):
                continue
            filtered_files.append(file_path)

        return sorted(set(filtered_files))

    def parse_file_cached(self, file_path: Path) -> Tuple[Optional[ast.AST], str]:
        """缓存文件解析"""
        try:
            file_mtime = file_path.stat().st_mtime
            cache_key = str(file_path)

            # 检查缓存
            with self._cache_lock:
                if cache_key in self._analysis_cache:
                    cached_mtime, cached_tree, cached_content = self._analysis_cache[cache_key]
                    if cached_mtime == file_mtime:
                        self.analysis_stats['cache_hits'] += 1
                        return cached_tree, cached_content

            # 解析文件
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            tree = ast.parse(content)

            # 更新缓存
            with self._cache_lock:
                self._analysis_cache[cache_key] = (file_mtime, tree, content)

            return tree, content

        except SyntaxError:
            # 语法错误时返回None和原始内容
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                return None, content
            except Exception:
                return None, ""
        except Exception as e:
            print(f"⚠️ 解析文件失败 {file_path}: {e}")
            return None, ""

    def analyze_single_file(self,
    file_path: Path) -> Tuple[List[QualityIssue],
    FileQualityMetrics]:
        """分析单个文件"""
        start_time = time.time()

        tree, content = self.parse_file_cached(file_path)

        # 执行所有规则
        all_issues = []
        for rule in self.rules:
            if rule.enabled:
                try:
                    issues = rule.analyze(file_path, tree, content)
                    all_issues.extend(issues)
                except Exception as e:
                    print(f"⚠️ 规则 {rule.name} 分析失败 {file_path}: {e}")

        # 计算文件质量指标
        lines_of_code = len([line for line in content.split('\n') if line.strip() and not line.strip().startswith('#')])
        metrics = self._calculate_file_metrics(file_path, all_issues, lines_of_code)

        _analysis_time = time.time() - start_time

        return all_issues, metrics

    def _calculate_file_metrics(self,
    file_path: Path,
    issues: List[QualityIssue],
    lines_of_code: int) -> FileQualityMetrics:
        """计算文件质量指标"""
        # 统计不同严重程度的问题数量
        critical_count = len([i for i in issues if i.severity == QualitySeverity.CRITICAL])
        high_count = len([i for i in issues if i.severity == QualitySeverity.HIGH])
        medium_count = len([i for i in issues if i.severity == QualitySeverity.MEDIUM])
        low_count = len([i for i in issues if i.severity == QualitySeverity.LOW])

        # 计算复杂度分数（简化版本）
        complexity_score = 5.0 + (high_count * 2) + (medium_count * 1) + (low_count * 0.5)

        # 计算可维护性指数（简化版本）
        maintainability_index = max(0,
    100 - (complexity_score * 5) - (critical_count * 20) - (high_count * 10))

        # 测试覆盖率（基于文件名估算）
        test_coverage = 0.0
        if "test" in file_path.name.lower():
            test_coverage = 85.0  # 测试文件假定高覆盖率

        # 文档分数
        documentation_score = self._calculate_documentation_score(file_path)

        # 安全分数
        security_issues = [i for i in issues if i.category == IssueCategory.SECURITY]
        security_score = max(0, 100 - len(security_issues) * 15)

        # 性能分数
        performance_issues = [i for i in issues if i.category == IssueCategory.PERFORMANCE]
        performance_score = max(0, 100 - len(performance_issues) * 10)

        # 综合质量分数
        overall_score = (
            maintainability_index * 0.3 +
            security_score * 0.25 +
            performance_score * 0.2 +
            test_coverage * 0.15 +
            documentation_score * 0.1
        )

        # 技术债（小时）
        technical_debt = (
            critical_count * 8 +    # 8小时修复一个严重问题
            high_count * 4 +        # 4小时修复一个高优先级问题
            medium_count * 2 +      # 2小时修复一个中等问题
            low_count * 0.5         # 30分钟修复一个低优先级问题
        )

        # 生成改进建议
        suggestions = self._generate_suggestions(issues, file_path)

        return FileQualityMetrics(
            file_path=str(file_path),
            total_issues=len(issues),
            critical_issues=critical_count,
            high_issues=high_count,
            medium_issues=medium_count,
            low_issues=low_count,
            complexity_score=complexity_score,
            maintainability_index=maintainability_index,
            test_coverage=test_coverage,
            documentation_score=documentation_score,
            security_score=security_score,
            performance_score=performance_score,
            overall_quality_score=overall_score,
            lines_of_code=lines_of_code,
            technical_debt=technical_debt,
            improvement_suggestions=suggestions
        )

    def _calculate_documentation_score(self, file_path: Path) -> float:
        """计算文档分数"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            score = 50.0  # 基础分

            # 检查模块文档字符串
            if content.startswith('"""') or content.startswith("'''"):
                score += 20.0

            # 检查注释覆盖率
            lines = content.split('\n')
            comment_lines = len([line for line in lines if line.strip().startswith('#')])
            code_lines = len([line for line in lines if line.strip() and not line.strip().startswith('#')])

            if code_lines > 0:
                comment_ratio = comment_lines / code_lines
                score += min(30.0, comment_ratio * 100)

            return min(100.0, score)

        except Exception:
            return 50.0

    def _generate_suggestions(self,
    issues: List[QualityIssue],
    file_path: Path) -> List[str]:
        """生成改进建议"""
        suggestions = []

        if not issues:
            suggestions.append("✨ 代码质量良好，继续保持！")
            return suggestions

        # 按类别统计问题
        category_counts = Counter(issue.category for issue in issues)
        severity_counts = Counter(issue.severity for issue in issues)

        # 生成针对性建议
        if severity_counts[QualitySeverity.CRITICAL] > 0:
            suggestions.append(f"🚨 优先修复 {severity_counts[QualitySeverity.CRITICAL]} 个严重问题")

        if category_counts[IssueCategory.SECURITY] > 0:
            suggestions.append(f"🔒 解决 {category_counts[IssueCategory.SECURITY]} 个安全问题")

        if category_counts[IssueCategory.COMPLEXITY] > 0:
            suggestions.append(f"🔧 重构 {category_counts[IssueCategory.COMPLEXITY]} 个复杂度问题")

        if category_counts[IssueCategory.SYNTAX] > 0:
            suggestions.append(f"📝 修复 {category_counts[IssueCategory.SYNTAX]} 个语法错误")

        # 通用改进建议
        if len(issues) > 10:
            suggestions.append("📈 考虑分批改进，先解决高优先级问题")

        suggestions.append("📊 定期运行质量分析，持续改进代码质量")

        return suggestions

    def analyze_project_parallel(self,
    paths: List[Path] = None) -> ProjectQualityReport:
        """并行分析整个项目"""
        print("🚀 启动项目质量分析...")
        start_time = time.time()

        # 发现Python文件
        python_files = self.discover_python_files(paths)
        total_files = len(python_files)

        print(f"📁 发现 {total_files} 个Python文件")

        if total_files == 0:
            print("⚠️ 未发现Python文件")
            return self._create_empty_report()

        # 并行分析
        all_issues = []
        file_metrics = []

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交分析任务
            future_to_file = {
                executor.submit(self.analyze_single_file, file_path): file_path
                for file_path in python_files
            }

            # 收集结果
            completed = 0
            for future in concurrent.futures.as_completed(future_to_file):
                file_path = future_to_file[future]
                try:
                    issues, metrics = future.result()
                    all_issues.extend(issues)
                    file_metrics.append(metrics)

                    completed += 1
                    progress = (completed / total_files) * 100
                    print(f"  进度: {completed}/{total_files} ({progress:.1f}%) - {file_path.name}: {len(issues)}个问题")

                except Exception as e:
                    print(f"❌ 分析文件失败 {file_path}: {e}")

        # 生成项目报告
        analysis_time = time.time() - start_time
        report = self._generate_project_report(all_issues, file_metrics, analysis_time)

        # 更新统计信息
        self.analysis_stats['files_analyzed'] = total_files
        self.analysis_stats['issues_found'] = len(all_issues)
        self.analysis_stats['analysis_time'] = analysis_time

        return report

    def _generate_project_report(self,
    issues: List[QualityIssue],
    file_metrics: List[FileQualityMetrics],
    analysis_time: float) -> ProjectQualityReport:
        """生成项目质量报告"""
        # 基本统计
        total_files = len(file_metrics)
        total_issues = len(issues)
        total_lines_of_code = sum(m.lines_of_code for m in file_metrics)

        # 按类别和严重程度统计
        issue_distribution = Counter(issue.category for issue in issues)
        severity_distribution = Counter(issue.severity for issue in issues)

        # 计算总体质量分数
        if file_metrics:
            overall_score = sum(m.overall_quality_score for m in file_metrics) / len(file_metrics)
        else:
            overall_score = 0.0

        # 评定等级
        grade = self._calculate_grade(overall_score)

        # 获取最重要的问题
        top_issues = sorted(issues, key=lambda x: (
            self._severity_weight(x.severity),
            x.confidence_score
        ), reverse=True)[:20]

        # 计算技术债
        total_technical_debt = sum(m.technical_debt for m in file_metrics)

        # 生成改进路线图
        improvement_roadmap = self._generate_improvement_roadmap(issues, file_metrics)

        # 生成推荐建议
        recommendations = self._generate_recommendations(issues, file_metrics)

        return ProjectQualityReport(
            project_name=self.project_root.name,
            analysis_time=datetime.now(),
            total_files=total_files,
            total_issues=total_issues,
            total_lines_of_code=total_lines_of_code,
            overall_quality_score=overall_score,
            grade=grade,
            issue_distribution=dict(issue_distribution),
            severity_distribution=dict(severity_distribution),
            top_issues=top_issues,
            file_metrics=file_metrics,
            improvement_roadmap=improvement_roadmap,
            technical_debt_total=total_technical_debt,
            recommendations=recommendations
        )

    def _severity_weight(self, severity: QualitySeverity) -> int:
        """获取严重程度权重"""
        weights = {
            QualitySeverity.CRITICAL: 4,
            QualitySeverity.HIGH: 3,
            QualitySeverity.MEDIUM: 2,
            QualitySeverity.LOW: 1,
            QualitySeverity.INFO: 0
        }
        return weights.get(severity, 0)

    def _calculate_grade(self, score: float) -> str:
        """计算质量等级"""
        if score >= 95:
            return "A+"
        elif score >= 90:
            return "A"
        elif score >= 85:
            return "B+"
        elif score >= 80:
            return "B"
        elif score >= 75:
            return "C+"
        elif score >= 70:
            return "C"
        elif score >= 60:
            return "D"
        else:
            return "F"

    def _generate_improvement_roadmap(self,
    issues: List[QualityIssue],
    file_metrics: List[FileQualityMetrics]) -> List[Dict[str,
    Any]]:
        """生成改进路线图"""
        roadmap = []

        # 按优先级分组问题
        critical_issues = [i for i in issues if i.severity == QualitySeverity.CRITICAL]
        high_issues = [i for i in issues if i.severity == QualitySeverity.HIGH]

        # Phase 1: 修复严重问题
        if critical_issues:
            roadmap.append({
                'phase': 1,
                'title': '修复严重问题',
                'description': f'解决 {len(critical_issues)} 个严重问题',
                'issues': critical_issues[:5],
                'estimated_effort': f"{len(critical_issues) * 8}小时",
                'priority': 'CRITICAL'
            })

        # Phase 2: 修复高优先级问题
        if high_issues:
            roadmap.append({
                'phase': 2,
                'title': '修复高优先级问题',
                'description': f'解决 {len(high_issues)} 个高优先级问题',
                'issues': high_issues[:10],
                'estimated_effort': f"{len(high_issues) * 4}小时",
                'priority': 'HIGH'
            })

        # Phase 3: 重构复杂代码
        complexity_issues = [i for i in issues if i.category == IssueCategory.COMPLEXITY]
        if complexity_issues:
            roadmap.append({
                'phase': 3,
                'title': '重构复杂代码',
                'description': f'重构 {len(complexity_issues)} 个复杂度问题',
                'issues': complexity_issues[:10],
                'estimated_effort': f"{len(complexity_issues) * 6}小时",
                'priority': 'MEDIUM'
            })

        # Phase 4: 提升测试覆盖率
        low_coverage_files = [m for m in file_metrics if m.test_coverage < 50]
        if low_coverage_files:
            roadmap.append({
                'phase': 4,
                'title': '提升测试覆盖率',
                'description': f'为 {len(low_coverage_files)} 个文件增加测试',
                'files': low_coverage_files[:10],
                'estimated_effort': f"{len(low_coverage_files) * 3}小时",
                'priority': 'MEDIUM'
            })

        return roadmap

    def _generate_recommendations(self,
    issues: List[QualityIssue],
    file_metrics: List[FileQualityMetrics]) -> List[str]:
        """生成推荐建议"""
        recommendations = []

        # 基于问题分布的建议
        if len(issues) == 0:
            recommendations.append("🎉 代码质量优秀，继续保持！")
            return recommendations

        issue_types = Counter(issue.category for issue in issues)
        _severity_types = Counter(issue.severity for issue in issues)

        # 安全建议
        if issue_types[IssueCategory.SECURITY] > 0:
            recommendations.append("🔒 建立安全代码审查流程，使用安全扫描工具")

        # 测试建议
        low_coverage_count = len([m for m in file_metrics if m.test_coverage < 30])
        if low_coverage_count > 0:
            recommendations.append(f"🧪 为 {low_coverage_count} 个低覆盖率文件增加单元测试")

        # 复杂度建议
        if issue_types[IssueCategory.COMPLEXITY] > 0:
            recommendations.append("🔧 引入代码重构最佳实践，定期重构复杂代码")

        # 文档建议
        avg_docs = sum(m.documentation_score for m in file_metrics) / len(file_metrics) if file_metrics else 0
        if avg_docs < 70:
            recommendations.append("📚 完善代码文档，增加注释和文档字符串")

        # 工具建议
        recommendations.append("🤖 集成智能质量分析引擎到CI/CD流程")
        recommendations.append("📊 建立质量度量仪表板，实时监控代码质量")

        return recommendations

    def _create_empty_report(self) -> ProjectQualityReport:
        """创建空报告"""
        return ProjectQualityReport(
            project_name=self.project_root.name,
            analysis_time=datetime.now(),
            total_files=0,
            total_issues=0,
            total_lines_of_code=0,
            overall_quality_score=0.0,
            grade="F",
            issue_distribution={},
            severity_distribution={},
            top_issues=[],
            file_metrics=[],
            improvement_roadmap=[],
            technical_debt_total=0.0,
            recommendations=["未发现Python文件，请检查项目结构"]
        )

    def print_report(self, report: ProjectQualityReport):
        """打印质量报告"""
        print("\n" + "="*80)
        print("🤖 企业级智能质量分析引擎 v2.0 - 项目质量报告")
        print("="*80)

        print("\n📊 项目概览:")
        print(f"  🏷️ 项目名称: {report.project_name}")
        print(f"  📅 分析时间: {report.analysis_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  📁 文件总数: {report.total_files}")
        print(f"  📝 代码行数: {report.total_lines_of_code:,}")
        print(f"  🐛 问题总数: {report.total_issues}")
        print(f"  ⏱️ 分析耗时: {self.analysis_stats['analysis_time']:.2f}秒")

        print("\n🏆 质量评分:")
        print(f"  📊 综合分数: {report.overall_quality_score:.1f}/100")
        print(f"  🎯 质量等级: {report.grade}")
        print(f"  ⏰ 技术债务: {report.technical_debt_total:.1f}小时")

        # 问题分布
        if report.issue_distribution:
            print("\n📈 问题分布:")
            for category,
    count in sorted(report.issue_distribution.items(),
    key=lambda x: x[1],
    reverse=True):
                print(f"  {category.value}: {count}个")

        # 严重程度分布
        if report.severity_distribution:
            print("\n🚨 严重程度分布:")
            for severity,
    count in sorted(report.severity_distribution.items(),
    key=lambda x: self._severity_weight(x[0]),
    reverse=True):
                emoji = {"CRITICAL": "🚨", "HIGH": "⚠️", "MEDIUM": "⚡", "LOW": "💡", "INFO": "ℹ️"}
                print(f"  {emoji.get(severity.value, '*')} {severity.value}: {count}个")

        # Top 问题
        if report.top_issues:
            print(f"\n🔍 重点问题 (前{len(report.top_issues)}个):")
            for i, issue in enumerate(report.top_issues[:10], 1):
                severity_emoji = {"CRITICAL": "🚨", "HIGH": "⚠️", "MEDIUM": "⚡", "LOW": "💡", "INFO": "ℹ️"}
                print(f"  {i}. {severity_emoji.get(issue.severity.value,
    '*')} [{issue.category.value}] {issue.title}")
                print(f"     📍 {issue.file_path}:{issue.line_number}")
                print(f"     💡 {issue.suggestion}")
                if i < len(report.top_issues):
                    print()

        # 改进路线图
        if report.improvement_roadmap:
            print("\n🗺️ 改进路线图:")
            for phase in report.improvement_roadmap:
                print(f"  Phase {phase['phase']}: {phase['title']}")
                print(f"    📝 {phase['description']}")
                print(f"    ⏱️ 预估工作量: {phase['estimated_effort']}")
                print(f"    🎯 优先级: {phase['priority']}")
                print()

        # 推荐建议
        if report.recommendations:
            print("\n💡 推荐建议:")
            for i, rec in enumerate(report.recommendations, 1):
                print(f"  {i}. {rec}")

        print("\n" + "="*80)
        print("🎉 智能质量分析完成！基于Issue #159的技术成果构建")
        print("🚀 v2.0引擎实现了AI驱动的自动化质量分析")
        print("="*80)

def main():
    """主函数"""
    print("🤖 启动企业级智能质量分析引擎 v2.0...")

    try:
        # 创建分析器
        analyzer = IntelligentQualityAnalyzerV2(
            max_workers=4,  # 4线程并行分析
            cache_size=256   # 256项缓存
        )

        # 运行项目分析
        report = analyzer.analyze_project_parallel()

        # 打印报告
        analyzer.print_report(report)

        # 返回分析结果
        if report.overall_quality_score >= 80:
            print(f"\n✅ 项目质量优秀: {report.overall_quality_score:.1f}/100")
            return 0
        elif report.overall_quality_score >= 60:
            print(f"\n⚡ 项目质量良好: {report.overall_quality_score:.1f}/100")
            return 1
        else:
            print(f"\n⚠️ 项目质量需要改进: {report.overall_quality_score:.1f}/100")
            return 2

    except Exception as e:
        print(f"❌ 质量分析失败: {e}")
        return 3

if __name__ == "__main__":
    exit(main())
