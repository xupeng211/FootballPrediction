#!/usr/bin/env python3
"""
智能批量类型修复工具
基于错误分析自动选择最优修复策略
"""

import subprocess
import re
import os
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple, Set, Optional, Any

class SmartBatchFixer:
    """智能批量修复器"""

    def __init__(self, project_root: str = "/home/user/projects/FootballPrediction"):
        self.project_root = Path(project_root)
        self.fix_history = []
        self.error_patterns = self._load_error_patterns()

    def _load_error_patterns(self) -> Dict[str, Dict]:
        """加载错误模式和修复策略"""
        return {
            'missing_import': {
                'patterns': [
                    r'error: Name "([^"]+)" is not defined',
                    r'error: Cannot find implementation or library stub for module named "([^"]+)"'
                ],
                'fixes': {
                    'Optional': 'from typing import Optional',
                    'Dict': 'from typing import Dict',
                    'List': 'from typing import List',
                    'Union': 'from typing import Union',
                    'Any': 'from typing import Any',
                    'Tuple': 'from typing import Tuple',
                    'Type': 'from typing import Type',
                    'TypeVar': 'from typing import TypeVar',
                    'Callable': 'from typing import Callable',
                }
            },
            'attr_defined': {
                'patterns': [
                    r'error: Module "([^"]+)" has no attribute "([^"]+)"'
                ],
                'fixes': {
                    # 基于模块属性错误的修复策略
                }
            },
            'assignment': {
                'patterns': [
                    r'error: Incompatible types in assignment \(expression has type "([^"]+)", variable has type "([^"]+)"\)'
                ],
                'fixes': {
                    # 类型不匹配的修复策略
                }
            },
            'arg_type': {
                'patterns': [
                    r'error: Argument \d+ has incompatible type "([^"]+)"; expected "([^"]+)"'
                ],
                'fixes': {
                    # 参数类型错误的修复策略
                }
            },
            'return_value': {
                'patterns': [
                    r'error: Incompatible return value type \(got "([^"]+)", expected "([^"]+)"\)'
                ],
                'fixes': {
                    # 返回值类型错误的修复策略
                }
            }
        }

    def analyze_file_errors(self, file_path: str) -> Dict[str, List[str]]:
        """分析文件的错误类型"""
        try:
            result = subprocess.run([
                'mypy', file_path, '--show-error-codes', '--no-error-summary'
            ], capture_output=True, text=True, cwd=str(self.project_root))

            errors = []
            for line in result.stdout.strip().split('\n'):
                if ': error:' in line:
                    errors.append(line)

            # 按错误类型分类
            categorized_errors = {
                'missing_import': [],
                'attr_defined': [],
                'assignment': [],
                'arg_type': [],
                'return_value': [],
                'other': []
            }

            for error in errors:
                categorized = False
                for error_type, config in self.error_patterns.items():
                    for pattern in config['patterns']:
                        if re.search(pattern, error):
                            categorized_errors[error_type].append(error)
                            categorized = True
                            break
                    if categorized:
                        break

                if not categorized:
                    categorized_errors['other'].append(error)

            return categorized_errors
        except Exception as e:
            return {'error': [f"Analysis failed: {e}"]}

    def smart_fix_file(self, file_path: str, error_analysis: Dict[str, List[str]]) -> Tuple[str, List[str], int]:
        """智能修复文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            return content, [f"读取文件失败: {e}"], 0

        changes_made = []
        fixes_applied = 0

        # 1. 修复缺失的导入
        if error_analysis.get('missing_import'):
            content, import_changes = self._fix_missing_imports(content, error_analysis['missing_import'])
            changes_made.extend(import_changes)
            fixes_applied += len(import_changes)

        # 2. 修复函数签名问题
        if error_analysis.get('return_value') or error_analysis.get('assignment'):
            content, signature_changes = self._fix_function_signatures(content,
                                                                 error_analysis.get('return_value', []) +
                                                                 error_analysis.get('assignment', []))
            changes_made.extend(signature_changes)
            fixes_applied += len(signature_changes)

        # 3. 修复Optional类型问题
        content, optional_changes = self._fix_optional_types(content)
        changes_made.extend(optional_changes)
        fixes_applied += len(optional_changes)

        # 4. 修复字典和列表返回类型
        content, collection_changes = self._fix_collection_types(content)
        changes_made.extend(collection_changes)
        fixes_applied += len(collection_changes)

        return content, changes_made, fixes_applied

    def _fix_missing_imports(self, content: str, errors: List[str]) -> Tuple[str, List[str]]:
        """修复缺失的导入"""
        changes = []
        imports_needed = set()

        # 分析错误，确定需要的导入
        for error in errors:
            for match in re.finditer(r'Name "([^"]+)" is not defined', error):
                name = match.group(1)
                if name in self.error_patterns['missing_import']['fixes']:
                    imports_needed.add(name)

        if not imports_needed:
            return content, changes

        # 检查现有导入
        existing_imports = set()
        import_match = re.search(r'from typing import ([^\n]+)', content)
        if import_match:
            existing_imports = set(name.strip() for name in import_match.group(1).split(','))

        # 确定需要添加的导入
        new_imports = imports_needed - existing_imports
        if not new_imports:
            return content, changes

        # 添加新导入
        if import_match:
            # 扩展现有导入
            import_match.group(1)
            all_imports = existing_imports.union(new_imports)
            new_import_line = f"from typing import {', '.join(sorted(all_imports))}"
            content = content.replace(import_match.group(0), new_import_line)
            changes.append(f"Added imports: {', '.join(new_imports)}")
        else:
            # 添加新的导入行
            import_line = f"from typing import {', '.join(sorted(new_imports))}\n\n"
            # 在文件开头添加（跳过shebang和文档字符串）
            lines = content.split('\n')
            insert_index = 0
            for i, line in enumerate(lines):
                if line.startswith('#!'):
                    insert_index = i + 1
                elif line.startswith('"""') and i == 0:
                    # 跳过模块文档字符串
                    for j in range(i+1, len(lines)):
                        if lines[j].strip() == '"""':
                            insert_index = j + 1
                            break
                    break
                elif line.strip() and not line.startswith('#'):
                    insert_index = i
                    break

            lines.insert(insert_index, import_line.strip())
            content = '\n'.join(lines)
            changes.append(f"Added imports: {', '.join(new_imports)}")

        return content, changes

    def _fix_function_signatures(self, content: str, errors: List[str]) -> Tuple[str, List[str]]:
        """修复函数签名问题"""
        changes = []

        # 修复返回类型不匹配问题
        for error in errors:
            if 'Incompatible return value type' in error:
                # 提取期望类型和实际类型
                match = re.search(r'got "([^"]+)", expected "([^"]+)"', error)
                if match:
                    actual_type, expected_type = match.group(1), match.group(2)

                    # 如果实际是None，期望不是Optional，添加Optional
                    if 'None' in actual_type and 'Optional' not in expected_type:
                        # 查找对应的函数定义
                        line_num = int(error.split(':')[1]) - 1
                        lines = content.split('\n')
                        if 0 <= line_num < len(lines):
                            func_line = lines[line_num]
                            # 简单的修复：添加Optional
                            if '-> ' in func_line and 'Optional' not in func_line:
                                fixed_line = func_line.replace(f'-> {expected_type}', f'-> Optional[{expected_type}]')
                                lines[line_num] = fixed_line
                                content = '\n'.join(lines)
                                changes.append(f"Fixed return type: {expected_type} -> Optional[{expected_type}]")

        return content, changes

    def _fix_optional_types(self, content: str) -> Tuple[str, List[str]]:
        """修复Optional类型问题"""
        changes = []

        # 检查是否有Optional但未导入
        if 'Optional' in content and 'from typing import' in content:
            if 'Optional' not in content.split('from typing import')[1].split('\n')[0]:
                # 添加Optional到现有导入
                import_line = re.search(r'from typing import ([^\n]+)', content)
                if import_line:
                    current_imports = import_line.group(1)
                    if 'Optional' not in current_imports:
                        new_imports = current_imports.rstrip() + ', Optional'
                        content = content.replace(import_line.group(0), f"from typing import {new_imports}")
                        changes.append("Added Optional import")

        return content, changes

    def _fix_collection_types(self, content: str) -> Tuple[str, List[str]]:
        """修复集合类型问题"""
        changes = []

        # 修复字典类型
        dict_pattern = r'return\s*\{([^}]+)\}\s*$'
        if re.search(dict_pattern, content, re.MULTILINE):
            # 确保Dict已导入
            if 'Dict' not in content:
                import_line = re.search(r'from typing import ([^\n]+)', content)
                if import_line:
                    current_imports = import_line.group(1)
                    if 'Dict' not in current_imports:
                        new_imports = current_imports.rstrip() + ', Dict'
                        content = content.replace(import_line.group(0), f"from typing import {new_imports}")
                        changes.append("Added Dict import")

        # 修复列表类型
        list_pattern = r'return\s*\[([^\]]+)\]\s*$'
        if re.search(list_pattern, content, re.MULTILINE):
            # 确保List已导入
            if 'List' not in content:
                import_line = re.search(r'from typing import ([^\n]+)', content)
                if import_line:
                    current_imports = import_line.group(1)
                    if 'List' not in current_imports:
                        new_imports = current_imports.rstrip() + ', List'
                        content = content.replace(import_line.group(0), f"from typing import {new_imports}")
                        changes.append("Added List import")

        return content, changes

    def select_high_impact_files(self, limit: int = 8) -> List[str]:
        """选择高影响的文件进行修复"""
        # 基于错误分析和模块重要性选择文件
        priority_files = [
            # 高优先级：核心API
            'src/api/middleware.py',
            'src/api/monitoring.py',
            'src/api/adapters.py',
            'src/api/cqrs.py',
            'src/api/dependencies.py',

            # 高优先级：核心服务
            'src/services/data_processing.py',
            'src/services/event_prediction_service.py',
            'src/services/audit_service.py',

            # 中优先级：数据层
            'src/collectors/odds_collector.py',
            'src/collectors/scores_collector_improved.py',
            'src/repositories/base.py',
            'src/repositories/prediction.py',

            # 中优先级：工具层
            'src/utils/helpers.py',
            'src/utils/config_loader.py',
            'src/utils/dict_utils.py',

            # 基础层
            'src/core/di.py',
            'src/core/config.py',
            'src/core/logging.py'
        ]

        # 只返回存在的文件
        existing_files = []
        for file_path in priority_files:
            if os.path.exists(file_path):
                # 分析错误数量，优先处理错误较多但可修复的文件
                error_analysis = self.analyze_file_errors(file_path)
                total_errors = sum(len(errors) for errors in error_analysis.values() if isinstance(errors, list))

                if total_errors > 0 and total_errors < 500:  # 避免错误太多的文件
                    existing_files.append((file_path, total_errors))

        # 按错误数量排序，优先处理中等复杂度的文件
        existing_files.sort(key=lambda x: x[1])
        return [file_path for file_path, _ in existing_files[:limit]]

    def run_smart_batch_fix(self) -> Dict[str, Any]:
        """运行智能批量修复"""
        print("🧠 启动智能批量类型修复...")
        print("=" * 60)

        # 选择高影响文件
        target_files = self.select_high_impact_files()
        print(f"📋 目标文件 ({len(target_files)}个):")
        for i, file_path in enumerate(target_files, 1):
            short_path = file_path.replace('/home/user/projects/FootballPrediction/', '')
            print(f"  {i}. {short_path}")

        print("\n🔄 开始智能修复...")

        results = {
            'timestamp': datetime.now().isoformat(),
            'files_processed': [],
            'total_fixes': 0,
            'total_files': len(target_files),
            'success_count': 0,
            'failed_count': 0
        }

        for file_path in target_files:
            short_path = file_path.replace('/home/user/projects/FootballPrediction/', '')
            print(f"\n🔧 智能修复: {short_path}")

            # 分析错误
            error_analysis = self.analyze_file_errors(file_path)
            if 'error' in error_analysis:
                print(f"   ❌ 分析失败: {error_analysis['error'][0]}")
                results['failed_count'] += 1
                continue

            total_errors = sum(len(errors) for errors in error_analysis.values() if isinstance(errors, list))
            print(f"   📊 分析结果: {total_errors} 个错误")

            # 显示错误类型分布
            for error_type, errors in error_analysis.items():
                if errors and isinstance(errors, list):
                    print(f"      • {error_type}: {len(errors)} 个")

            # 智能修复
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    f.read()

                fixed_content, changes, fixes_count = self.smart_fix_file(file_path, error_analysis)

                if fixes_count > 0:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(fixed_content)

                    # 验证修复效果
                    new_analysis = self.analyze_file_errors(file_path)
                    new_total_errors = sum(len(errors) for errors in new_analysis.values() if isinstance(errors, list))
                    improvement = total_errors - new_total_errors

                    results['success_count'] += 1
                    results['total_fixes'] += fixes_count

                    print(f"   ✅ 修复成功: {fixes_count} 项修复")
                    print(f"   📈 错误减少: {improvement} 个 ({total_errors} → {new_total_errors})")
                    print(f"   🔧 修复内容: {'; '.join(changes[:3])}")

                    if len(changes) > 3:
                        print(f"      ... 还有 {len(changes) - 3} 项修复")

                else:
                    print("   ⚠️ 无需修复或无法自动修复")
                    results['failed_count'] += 1

                # 记录处理结果
                results['files_processed'].append({
                    'file_path': file_path,
                    'original_errors': total_errors,
                    'fixes_applied': fixes_count,
                    'changes_made': changes,
                    'success': fixes_count > 0
                })

            except Exception as e:
                print(f"   ❌ 修复失败: {e}")
                results['failed_count'] += 1

        # 输出总结
        print("\n📊 智能批量修复结果:")
        print(f"✅ 成功处理: {results['success_count']} 个文件")
        print(f"❌ 处理失败: {results['failed_count']} 个文件")
        print(f"🔧 总修复数: {results['total_fixes']} 项")

        # 保存详细报告
        reports_dir = self.project_root / "reports" / "quality"
        reports_dir.mkdir(parents=True, exist_ok=True)

        report_file = reports_dir / f"smart_fix_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        print(f"💾 详细报告: {report_file}")

        # 给出下一步建议
        if results['success_count'] > 0:
            print("\n🎯 下一步建议:")
            print("1. 运行质量检查验证修复效果")
            print("2. 测试核心功能确保正常运行")
            print("3. 提交修复成果")
        else:
            print("\n💡 建议:")
            print("1. 检查剩余错误类型，考虑手动修复")
            print("2. 调整修复策略，处理更复杂的类型问题")

        return results

def main():
    """主函数"""
    fixer = SmartBatchFixer()
    results = fixer.run_smart_batch_fix()

    # 返回适当的退出码
    if results['success_count'] > 0:
        return 0
    else:
        return 1

if __name__ == '__main__':
    import sys
    sys.exit(main())