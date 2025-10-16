#!/usr/bin/env python3
"""
分析项目中所有Python文件的语法错误
"""

import ast
import os
import re
from collections import defaultdict, Counter
from pathlib import Path
import json

def check_syntax(file_path):
    """检查单个文件的语法错误"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        ast.parse(content)
        return True, None, None, None
    except SyntaxError as e:
        return False, e.msg, e.lineno, e.text
    except Exception as e:
        return False, str(e), None, None

def categorize_error(error_msg):
    """将错误消息分类"""
    error_msg_lower = error_msg.lower()

    if 'unterminated string literal' in error_msg_lower:
        return '未闭合的字符串'
    elif 'unmatched' in error_msg_lower and ("'" in error_msg_lower or '"' in error_msg_lower):
        return '引号不匹配'
    elif 'unmatched' in error_msg_lower and ('[' in error_msg_lower or ']' in error_msg_lower):
        return '方括号不匹配'
    elif 'unmatched' in error_msg_lower and ('{' in error_msg_lower or '}' in error_msg_lower):
        return '大括号不匹配'
    elif 'unmatched' in error_msg_lower and ('(' in error_msg_lower or ')' in error_msg_lower):
        return '圆括号不匹配'
    elif 'does not match opening' in error_msg_lower:
        return '括号不匹配'
    elif 'closing parenthesis' in error_msg_lower:
        return '括号不匹配'
    elif 'expected' in error_msg_lower and ':' in error_msg:
        return '缺少冒号'
    elif 'invalid syntax' in error_msg_lower:
        if 'comma' in error_msg_lower:
            return '缺少逗号'
        elif 'indent' in error_msg_lower:
            return '缩进错误'
        else:
            return '语法错误（其他）'
    elif 'cannot assign to subscript' in error_msg_lower:
        return '赋值语法错误'
    elif 'f-string' in error_msg_lower:
        return 'f-string错误'
    elif 'perhaps you forgot' in error_msg_lower:
        return '建议性错误'
    else:
        return '其他错误'

def analyze_all_syntax_errors():
    """分析所有语法错误"""
    project_root = Path('.')

    # 统计数据
    total_files = 0
    error_files = 0
    errors_by_type = Counter()
    errors_by_module = defaultdict(list)
    error_details = []

    # 需要检查的模块
    modules_to_check = [
        'src/core',
        'src/api',
        'src/domain',
        'src/services',
        'src/database',
        'src/cache',
        'src/collectors',
        'src/data',
        'src/events',
        'src/repositories',
        'src/models',
        'src/adapters',
        'src/cqrs',
        'src/facades',
        'src/ml',
        'src/monitoring',
        'src/observers',
        'src/patterns',
        'src/scheduler',
        'src/security',
        'src/streaming',
        'src/tasks',
        'src/utils',
        'src/dependencies',
        'src/decorators',
        'src/facades',
        'src/features',
        'src/lineage',
        'src/middleware',
        'src/repositories',
        'src/stubs',
        'src/testing',
        'src/utils'
    ]

    print("🔍 正在扫描Python文件的语法错误...\n")

    for module in modules_to_check:
        module_path = project_root / module
        if not module_path.exists():
            continue

        for py_file in module_path.rglob('*.py'):
            if py_file.name == '__pycache__':
                continue

            total_files += 1
            relative_path = str(py_file.relative_to(project_root))

            is_valid, error_msg, line_no, line_text = check_syntax(py_file)

            if not is_valid:
                error_files += 1
                error_category = categorize_error(error_msg)
                errors_by_type[error_category] += 1

                # 提取模块名
                module_name = relative_path.split('/')[1] if len(relative_path.split('/')) > 1 else 'root'
                errors_by_module[module_name].append({
                    'file': relative_path,
                    'error': error_msg,
                    'category': error_category,
                    'line': line_no,
                    'line_text': line_text
                })

                error_details.append({
                    'file': relative_path,
                    'error': error_msg,
                    'category': error_category,
                    'line': line_no
                })

    return {
        'total_files': total_files,
        'error_files': error_files,
        'success_rate': ((total_files - error_files) / total_files * 100) if total_files > 0 else 0,
        'errors_by_type': dict(errors_by_type),
        'errors_by_module': dict(errors_by_module),
        'error_details': error_details
    }

def generate_report(analysis_result):
    """生成详细的错误报告"""

    # 创建报告目录
    os.makedirs('reports', exist_ok=True)

    # 1. 生成控制台报告
    print("=" * 80)
    print("📊 语法错误统计报告")
    print("=" * 80)

    print(f"\n📈 总体统计:")
    print(f"  总文件数: {analysis_result['total_files']}")
    print(f"  有错误文件: {analysis_result['error_files']}")
    print(f"  成功率: {analysis_result['success_rate']:.1f}%")
    print(f"  错误率: {100 - analysis_result['success_rate']:.1f}%")

    print(f"\n🔍 错误类型分布 (前10):")
    for error_type, count in sorted(analysis_result['errors_by_type'].items(),
                                   key=lambda x: x[1], reverse=True)[:10]:
        print(f"  {error_type}: {count} 个")

    print(f"\n📁 按模块分布 (前10):")
    module_counts = {module: len(errors) for module, errors in analysis_result['errors_by_module'].items()}
    for module, count in sorted(module_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  {module}: {count} 个错误")

    # 2. 生成JSON详细报告
    with open('reports/syntax_errors_detailed.json', 'w', encoding='utf-8') as f:
        json.dump(analysis_result, f, ensure_ascii=False, indent=2)

    # 3. 生成Markdown报告
    md_content = []
    md_content.append("# 语法错误分析报告\n")
    md_content.append(f"生成时间: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # 总体统计
    md_content.append("## 📊 总体统计\n")
    md_content.append(f"- **总文件数**: {analysis_result['total_files']}\n")
    md_content.append(f"- **有错误文件**: {analysis_result['error_files']}\n")
    md_content.append(f"- **成功率**: {analysis_result['success_rate']:.1f}%\n")
    md_content.append(f"- **错误率**: {100 - analysis_result['success_rate']:.1f}%\n")

    # 错误类型分布
    md_content.append("\n## 🔍 错误类型分布\n")
    md_content.append("| 错误类型 | 数量 | 占比 |\n")
    md_content.append("|---------|------|------|\n")
    total_errors = sum(analysis_result['errors_by_type'].values())
    for error_type, count in sorted(analysis_result['errors_by_type'].items(),
                                   key=lambda x: x[1], reverse=True):
        percentage = (count / total_errors * 100) if total_errors > 0 else 0
        md_content.append(f"| {error_type} | {count} | {percentage:.1f}% |\n")

    # 按模块分布
    md_content.append("\n## 📁 按模块分布\n")
    md_content.append("| 模块 | 错误数 | 占比 |\n")
    md_content.append("|------|--------|------|\n")
    for module, errors in sorted(analysis_result['errors_by_module'].items(),
                                 key=lambda x: len(x[1]), reverse=True)[:20]:
        count = len(errors)
        percentage = (count / analysis_result['error_files'] * 100) if analysis_result['error_files'] > 0 else 0
        md_content.append(f"| {module} | {count} | {percentage:.1f}% |\n")

    # 详细错误列表（前100个）
    md_content.append("\n## 📝 详细错误列表（前100个）\n")
    md_content.append("| 文件 | 行号 | 错误类型 | 错误信息 |\n")
    md_content.append("|------|------|----------|----------|\n")

    for error in analysis_result['error_details'][:100]:
        file_path = error['file']
        line = error['line'] or 'N/A'
        category = error['category']
        msg = error['error'].replace('|', '\\|').replace('\n', ' ')[:100]
        md_content.append(f"| `{file_path}` | {line} | {category} | {msg} |\n")

    # 修复建议
    md_content.append("\n## 💡 修复建议\n")
    md_content.append("\n### 优先级1：批量修复\n")
    md_content.append("1. **未闭合的字符串** - 使用正则表达式批量修复\n")
    md_content.append("2. **缺少冒号** - 在def、if、for、while行末添加冒号\n")
    md_content.append("3. **括号不匹配** - 使用括号平衡算法修复\n")

    md_content.append("\n### 优先级2：逐个修复\n")
    md_content.append("1. **f-string错误** - 需要手动检查和修复\n")
    md_content.append("2. **赋值语法错误** - 将 `=` 改为 `==` 或修复索引\n")
    md_content.append("3. **缩进错误** - 调整代码缩进\n")

    md_content.append("\n### 优先级3：重点模块\n")
    md_content.append("优先修复以下核心模块：\n")
    priority_modules = ['core', 'api', 'services', 'database']
    for module in priority_modules:
        if module in analysis_result['errors_by_module']:
            count = len(analysis_result['errors_by_module'][module])
            md_content.append(f"- **src/{module}**: {count} 个错误\n")

    # 保存Markdown报告
    with open('reports/syntax_errors_report.md', 'w', encoding='utf-8') as f:
        f.writelines(md_content)

    print(f"\n✅ 报告已生成:")
    print(f"  - reports/syntax_errors_detailed.json (完整数据)")
    print(f"  - reports/syntax_errors_report.md (可读报告)")

    return analysis_result

def generate_fix_plan(analysis_result):
    """生成修复计划"""

    # 按错误类型分组
    fix_plan = {
        'easy_fixes': [],
        'medium_fixes': [],
        'hard_fixes': []
    }

    # 容易修复的错误
    easy_patterns = {
        '缺少冒号': r'(def|if|for|while|class|try|except|with|elif)([^:]*$)',
        '未闭合的字符串': r'(["\'])([^"\']*$)',
        '缺少逗号': r'([a-zA-Z0-9_])\s*([a-zA-Z_])',
    }

    # 中等难度修复
    medium_patterns = {
        '括号不匹配': '需要检查括号平衡',
        '引号不匹配': '需要检查引号配对',
        '赋值语法错误': '需要检查赋值语句',
    }

    # 困难的修复
    hard_patterns = {
        'f-string错误': '需要手动检查f-string语法',
        '缩进错误': '需要调整代码缩进',
        '语法错误（其他）': '需要仔细检查代码逻辑',
    }

    # 按文件生成修复计划
    for error in analysis_result['error_details']:
        category = error['category']
        file_path = error['file']

        item = {
            'file': file_path,
            'line': error['line'],
            'error': error['error'],
            'category': category
        }

        if category in easy_patterns:
            fix_plan['easy_fixes'].append(item)
        elif category in medium_patterns:
            fix_plan['medium_fixes'].append(item)
        else:
            fix_plan['hard_fixes'].append(item)

    # 生成修复计划文件
    plan_content = []
    plan_content.append("# 语法错误修复计划\n")
    plan_content.append(f"生成时间: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    plan_content.append(f"## 📊 修复统计\n")
    plan_content.append(f"- 容易修复: {len(fix_plan['easy_fixes'])} 个\n")
    plan_content.append(f"- 中等难度: {len(fix_plan['medium_fixes'])} 个\n")
    plan_content.append(f"- 困难修复: {len(fix_plan['hard_fixes'])} 个\n")

    # 详细计划
    for difficulty in ['easy_fixes', 'medium_fixes', 'hard_fixes']:
        difficulty_name = {
            'easy_fixes': '容易修复',
            'medium_fixes': '中等难度',
            'hard_fixes': '困难修复'
        }[difficulty]

        plan_content.append(f"\n## {difficulty_name} ({len(fix_plan[difficulty])} 个)\n")

        for item in fix_plan[difficulty][:20]:  # 只显示前20个
            plan_content.append(f"### `{item['file']}`\n")
            plan_content.append(f"- **行号**: {item['line']}\n")
            plan_content.append(f"- **错误**: {item['error']}\n")
            plan_content.append(f"- **类型**: {item['category']}\n\n")

    # 保存修复计划
    with open('reports/syntax_errors_fix_plan.md', 'w', encoding='utf-8') as f:
        f.writelines(plan_content)

    print(f"  - reports/syntax_errors_fix_plan.md (修复计划)")

    return fix_plan

def main():
    """主函数"""
    print("🚀 开始分析项目语法错误...\n")

    # 执行分析
    result = analyze_all_syntax_errors()

    # 生成报告
    generate_report(result)
    generate_fix_plan(result)

    print("\n✨ 分析完成！")

if __name__ == "__main__":
    main()
