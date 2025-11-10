#!/usr/bin/env python3
"""
API文档验证脚本
验证文档中描述的API端点与代码中的实际端点是否一致
"""

import ast
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Set

class APIEndpointValidator:
    def __init__(self, api_dir: str = "src/api", docs_dir: str = "docs/api"):
        self.api_dir = Path(api_dir)
        self.docs_dir = Path(docs_dir)
        self.endpoints_in_code = set()
        self.endpoints_in_docs = set()

    def extract_endpoints_from_code(self):
        """从Python代码中提取API端点"""
        print("🔍 从代码中提取API端点...")

        for py_file in self.api_dir.rglob("*.py"):
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                # 解析AST
                try:
                    tree = ast.parse(content)
                    self._extract_from_ast(tree, py_file)
                except SyntaxError:
                    # 如果AST解析失败，使用正则表达式
                    self._extract_with_regex(content, py_file)

            except Exception as e:
                print(f"⚠️ 处理文件 {py_file} 时出错: {e}")

    def _extract_from_ast(self, tree: ast.AST, file_path: Path):
        """从AST中提取API端点"""
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # 检查是否是API路由函数
                for decorator in node.decorator_list:
                    if isinstance(decorator, ast.Attribute):
                        # 检查 @app.get, @router.post 等
                        if hasattr(decorator.func, 'id') and decorator.func.id in ['get', 'post', 'put', 'delete', 'patch']:
                            if hasattr(decorator.value, 'id') and decorator.value.id in ['app', 'router']:
                                # 提取路径参数
                                if decorator.args:
                                    path = decorator.args[0].s if hasattr(decorator.args[0], 's') else str(decorator.args[0])
                                else:
                                    path = "/"
                                method = decorator.func.id.upper()
                                self.endpoints_in_code.add(f"{method} {path}")

                    elif isinstance(decorator, ast.Call):
                        # 检查 @app.get("/path") 形式
                        if hasattr(decorator.func, 'attr') and decorator.func.attr in ['get', 'post', 'put', 'delete', 'patch']:
                            if hasattr(decorator.func, 'value') and hasattr(decorator.func.value, 'id'):
                                if decorator.func.value.id in ['app', 'router']:
                                    if decorator.args:
                                        path = decorator.args[0].s if hasattr(decorator.args[0], 's') else str(decorator.args[0])
                                    else:
                                        path = "/"
                                    method = decorator.func.attr.upper()
                                    self.endpoints_in_code.add(f"{method} {path}")

    def _extract_with_regex(self, content: str, file_path: Path):
        """使用正则表达式提取API端点"""
        patterns = [
            r'@(app|router)\.(get|post|put|delete|patch)\([\'"]([^\'"]+)[\'"]',
            r'@(app|router)\.(get|post|put|delete|patch)\(\s*[\'"]([^\'"]+)[\'"]',
        ]

        for pattern in patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                method = match.group(2).upper()
                path = match.group(3)
                self.endpoints_in_code.add(f"{method} {path}")

    def extract_endpoints_from_docs(self):
        """从文档中提取API端点"""
        print("🔍 从文档中提取API端点...")

        complete_api_ref = self.docs_dir / "COMPLETE_API_REFERENCE.md"
        getting_started = self.docs_dir / "GETTING_STARTED_GUIDE.md"

        for doc_file in [complete_api_ref, getting_started]:
            if doc_file.exists():
                with open(doc_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                # 提取API端点模式
                patterns = [
                    r'(GET|POST|PUT|DELETE|PATCH)\s+([^\s]+)',
                    r'```http\s*\n(POST|GET|PUT|DELETE|PATCH)\s+([^\s\n]+)',
                    r'curl\s+-X\s+(GET|POST|PUT|DELETE|PATCH).*["\']([^"\']+)["\']',
                ]

                for pattern in patterns:
                    matches = re.finditer(pattern, content, re.IGNORECASE | re.MULTILINE | re.DOTALL)
                    for match in matches:
                        method = match.group(1).upper()
                        path = match.group(2)
                        # 清理路径
                        path = path.strip().rstrip('\\')
                        if path and not path.startswith('http'):
                            self.endpoints_in_docs.add(f"{method} {path}")

    def validate_coverage(self) -> Dict[str, Set[str]]:
        """验证API端点覆盖率"""
        print("📊 验证API端点覆盖率...")

        code_only = self.endpoints_in_code - self.endpoints_in_docs
        docs_only = self.endpoints_in_docs - self.endpoints_in_code
        common = self.endpoints_in_code & self.endpoints_in_docs

        return {
            "code_only": code_only,
            "docs_only": docs_only,
            "common": common,
            "total_code": self.endpoints_in_code,
            "total_docs": self.endpoints_in_docs
        }

    def generate_report(self, results: Dict[str, Set[str]]) -> str:
        """生成验证报告"""
        report = f"""
# API文档验证报告

## 📊 统计信息
- **代码中的端点**: {len(results['total_code'])} 个
- **文档中的端点**: {len(results['total_docs'])} 个
- **共同端点**: {len(results['common'])} 个
- **覆盖率**: {len(results['common']) / max(len(results['total_code']), 1) * 100:.1f}%

## ✅ 已覆盖的端点
"""

        for endpoint in sorted(results['common']):
            report += f"- {endpoint}\n"

        if results['code_only']:
            report += f"\n## ⚠️ 代码中有但文档中缺失的端点\n"
            for endpoint in sorted(results['code_only']):
                report += f"- {endpoint}\n"

        if results['docs_only']:
            report += f"\n## 📝 文档中有但代码中不存在的端点\n"
            for endpoint in sorted(results['docs_only']):
                report += f"- {endpoint}\n"

        return report

def main():
    """主函数"""
    print("🚀 开始API文档验证...")

    validator = APIEndpointValidator()

    # 提取端点
    validator.extract_endpoints_from_code()
    validator.extract_endpoints_from_docs()

    # 验证覆盖率
    results = validator.validate_coverage()

    # 生成报告
    report = validator.generate_report(results)

    # 保存报告
    report_file = Path("docs/api_validation_report.md")
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"📄 验证报告已保存到: {report_file}")
    print(f"📊 覆盖率: {len(results['common']) / max(len(results['total_code']), 1) * 100:.1f}%")

    # 如果覆盖率低于90%，返回错误代码
    coverage_rate = len(results['common']) / max(len(results['total_code']), 1) * 100
    if coverage_rate < 90:
        print("⚠️ API文档覆盖率低于90%，建议完善文档")
        sys.exit(1)
    else:
        print("✅ API文档覆盖率良好")
        sys.exit(0)

if __name__ == "__main__":
    main()