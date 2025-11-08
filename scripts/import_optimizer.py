#!/usr/bin/env python3
"""
模块导入优化工具
解决E402错误和循环依赖问题
"""

import ast
from pathlib import Path


class ImportOptimizer:
    def __init__(self):
        self.import_order = [
            'standard_library',  # 标准库
            'third_party',       # 第三方库
            'local'             # 本地模块
        ]

    def analyze_imports(self, file_path: Path) -> dict:
        """分析文件的导入结构"""
        with open(file_path, encoding='utf-8') as f:
            content = f.read()

        # 解析AST
        try:
            tree = ast.parse(content)
        except SyntaxError as e:
            return {'error': f'语法错误: {e}'}

        imports = []
        imports_in_functions = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append({
                        'line': node.lineno,
                        'module': alias.name,
                        'alias': alias.asname,
                        'type': 'import'
                    })
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    for alias in node.names:
                        imports.append({
                            'line': node.lineno,
                            'module': f'{node.module}.{alias.name}',
                            'alias': alias.asname,
                            'type': 'from',
                            'level': node.level
                        })

            # 检查函数内的导入
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for child in ast.walk(node):
                    if isinstance(child, (ast.Import, ast.ImportFrom)):
                        imports_in_functions.append({
                            'function': node.name,
                            'line': child.lineno
                        })

        return {
            'imports': imports,
            'imports_in_functions': imports_in_functions,
            'total_imports': len(imports),
            'function_imports': len(imports_in_functions)
        }

    def suggest_import_refactoring(self, analysis: dict) -> list[str]:
        """建议导入重构方案"""
        suggestions = []

        if analysis.get('error'):
            suggestions.append(f"❌ {analysis['error']}")
            return suggestions

        function_imports = analysis.get('imports_in_functions', [])

        if function_imports:
            suggestions.append("🔧 发现函数内导入，建议重构:")
            for imp in function_imports[:5]:  # 只显示前5个
                suggestions.append(f"   - 函数 '{imp['function']}' 第{imp['line']}行")

            suggestions.append("\n💡 重构建议:")
            suggestions.append("   1. 将导入移到文件顶部")
            suggestions.append("   2. 使用依赖注入替代延迟导入")
            suggestions.append("   3. 考虑工厂模式管理复杂依赖")

        return suggestions

    def generate_import_fix_plan(self, file_path: Path) -> dict:
        """生成导入修复计划"""
        analysis = self.analyze_imports(file_path)
        suggestions = self.suggest_import_refactoring(analysis)

        return {
            'file': str(file_path),
            'analysis': analysis,
            'suggestions': suggestions,
            'priority': 'high' if analysis.get('function_imports', 0) > 0 else 'low'
        }

def analyze_key_files():
    """分析关键文件的导入问题"""
    optimizer = ImportOptimizer()

    key_files = [
        'src/main.py',
        'src/services/betting/ev_calculator.py',
        'src/collectors/oddsportal_integration.py',
        'src/tasks/maintenance_tasks.py'
    ]

    report = {
        'timestamp': '2025-11-05 16:01',
        'files': {}
    }

    print("🔍 分析关键文件的导入问题...")
    print("=" * 60)

    for file_path in key_files:
        path = Path(file_path)
        if path.exists():
            plan = optimizer.generate_import_fix_plan(path)
            report['files'][file_path] = plan

            print(f"\n📁 {file_path}")
            print(f"   优先级: {plan['priority']}")
            print(f"   总导入数: {plan['analysis'].get('total_imports', 0)}")
            print(f"   函数内导入: {plan['analysis'].get('function_imports', 0)}")

            for suggestion in plan['suggestions'][:3]:  # 只显示前3个建议
                print(f"   {suggestion}")
        else:
            print(f"\n⚠️  文件不存在: {file_path}")

    print("\n" + "=" * 60)

    # 生成修复建议
    high_priority_files = [
        f for f, plan in report['files'].items()
        if plan.get('priority') == 'high'
    ]

    if high_priority_files:
        print(f"\n🚨 高优先级修复文件 ({len(high_priority_files)}个):")
        for file_path in high_priority_files:
            print(f"   - {file_path}")

        print("\n💡 推荐修复顺序:")
        print("   1. 先修复 main.py (影响启动)")
        print("   2. 修复服务层文件 (核心业务)")
        print("   3. 修复工具和任务文件")
    else:
        print("\n✅ 没有发现高优先级的导入问题")

    return report

def main():
    """主函数"""
    print("🚀 启动模块导入优化分析...")

    report = analyze_key_files()

    # 保存报告
    import json
    with open('import_analysis_report.json', 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print("\n📄 详细报告已保存: import_analysis_report.json")

if __name__ == "__main__":
    main()
