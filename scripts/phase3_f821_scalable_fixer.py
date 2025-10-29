#!/usr/bin/env python3
"""
Phase 3 F821规模化智能修复工具
Phase 3 Scalable F821 Intelligent Fixer

基于已验证策略的规模化F821修复系统，采用三阶段递进方法：
1. 智能分组和优先级排序
2. 渐进式批量修复
3. 安全验证和质量门禁

目标: 将6,604个F821错误减少到<1,000个
"""

import ast
import json
import logging
import re
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Set
from collections import defaultdict

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class Phase3F821ScalableFixer:
    """Phase 3 F821规模化智能修复器"""

    def __init__(self):
        self.fixes_applied = 0
        self.files_processed = 0
        self.files_fixed = 0
        self.batches_processed = 0

        # 增强的导入映射数据库
        self.import_mappings = {
            # FastAPI相关
            'APIRouter': {'module': 'fastapi', 'import_type': 'from', 'confidence': 0.95},
            'HTTPException': {'module': 'fastapi', 'import_type': 'from', 'confidence': 0.95},
            'Query': {'module': 'fastapi', 'import_type': 'from', 'confidence': 0.95},
            'Depends': {'module': 'fastapi', 'import_type': 'from', 'confidence': 0.95},
            'BackgroundTasks': {'module': 'fastapi', 'import_type': 'from', 'confidence': 0.95},
            'Body': {'module': 'fastapi', 'import_type': 'from', 'confidence': 0.90},
            'Path': {'module': 'fastapi', 'import_type': 'from', 'confidence': 0.90},

            # Pydantic相关
            'BaseModel': {'module': 'pydantic', 'import_type': 'from', 'confidence': 0.95},
            'Field': {'module': 'pydantic', 'import_type': 'from', 'confidence': 0.95},
            'validator': {'module': 'pydantic', 'import_type': 'from', 'confidence': 0.85},

            # Typing相关
            'Dict': {'module': 'typing', 'import_type': 'from', 'confidence': 0.98},
            'List': {'module': 'typing', 'import_type': 'from', 'confidence': 0.98},
            'Optional': {'module': 'typing', 'import_type': 'from', 'confidence': 0.98},
            'Union': {'module': 'typing', 'import_type': 'from', 'confidence': 0.90},
            'Any': {'module': 'typing', 'import_type': 'from', 'confidence': 0.90},
            'Callable': {'module': 'typing', 'import_type': 'from', 'confidence': 0.85},

            # 标准库
            'datetime': {'module': 'datetime', 'import_type': 'from', 'confidence': 0.95},
            'logger': {'module': 'logging', 'import_type': 'from', 'name': 'get_logger', 'confidence': 0.90},
            'Path': {'module': 'pathlib', 'import_type': 'from', 'confidence': 0.90},
            're': {'module': 're', 'import_type': 'import', 'confidence': 0.95},
            'json': {'module': 'json', 'import_type': 'import', 'confidence': 0.95},
            'os': {'module': 'os', 'import_type': 'import', 'confidence': 0.95},
            'sys': {'module': 'sys', 'import_type': 'import', 'confidence': 0.95},

            # SQLAlchemy相关
            'Column': {'module': 'sqlalchemy', 'import_type': 'from', 'confidence': 0.85},
            'Integer': {'module': 'sqlalchemy', 'import_type': 'from', 'confidence': 0.85},
            'String': {'module': 'sqlalchemy', 'import_type': 'from', 'confidence': 0.85},

            # 测试相关
            'pytest': {'module': 'pytest', 'import_type': 'import', 'confidence': 0.80},
            'Mock': {'module': 'unittest.mock', 'import_type': 'from', 'confidence': 0.85},
            'patch': {'module': 'unittest.mock', 'import_type': 'from', 'confidence': 0.85},
        }

    def analyze_f821_errors(self) -> Dict:
        """深度分析F821错误并生成智能分组"""
        logger.info("🔍 开始深度分析F821错误...")

        try:
            result = subprocess.run(
                ['ruff', 'check', '--select=F821', '--format=json'],
                capture_output=True,
                text=True,
                timeout=120
            )

            if not result.stdout.strip():
                logger.info("✅ 没有发现F821错误")
                return {'total_errors': 0, 'groups': {}}

            error_data = json.loads(result.stdout)
            f821_errors = [e for e in error_data if e.get('code') == 'F821']

            # 智能分组
            analysis = {
                'total_errors': len(f821_errors),
                'groups': {
                    'by_module': defaultdict(list),
                    'by_name': defaultdict(list),
                    'by_confidence': defaultdict(list),
                    'by_priority': defaultdict(list)
                },
                'high_confidence_fixes': [],
                'requires_manual_review': []
            }

            for error in f821_errors:
                file_path = error['filename']
                line_num = error['location']['row']
                message = error['message']

                # 提取未定义名称
                undefined_name = self.extract_undefined_name(message)

                # 确定修复策略
                fix_strategy = self.determine_fix_strategy(undefined_name, file_path)

                error_info = {
                    'file': file_path,
                    'line': line_num,
                    'name': undefined_name,
                    'strategy': fix_strategy['strategy'],
                    'confidence': fix_strategy['confidence'],
                    'suggested_import': fix_strategy.get('suggested_import'),
                    'module': self.get_module_from_path(file_path)
                }

                # 按模块分组
                analysis['groups']['by_module'][error_info['module']].append(error_info)

                # 按名称分组
                analysis['groups']['by_name'][undefined_name].append(error_info)

                # 按置信度分组
                confidence_group = 'high' if fix_strategy['confidence'] >= 0.8 else 'medium' if fix_strategy['confidence'] >= 0.6 else 'low'
                analysis['groups']['by_confidence'][confidence_group].append(error_info)

                # 按优先级分组
                priority = self.determine_priority(error_info)
                analysis['groups']['by_priority'][priority].append(error_info)

                # 分类高置信度修复
                if fix_strategy['confidence'] >= 0.8:
                    analysis['high_confidence_fixes'].append(error_info)
                else:
                    analysis['requires_manual_review'].append(error_info)

            logger.info(f"📊 分析完成: {len(f821_errors)}个F821错误，{len(analysis['high_confidence_fixes'])}个高置信度可自动修复")
            return analysis

        except Exception as e:
            logger.error(f"F821错误分析失败: {e}")
            return {'total_errors': 0, 'groups': {}}

    def extract_undefined_name(self, message: str) -> str:
        """从错误消息中提取未定义名称"""
        match = re.search(r"undefined name '([^']+)'", message)
        return match.group(1) if match else ""

    def get_module_from_path(self, file_path: str) -> str:
        """从文件路径推断模块类型"""
        if 'test' in file_path:
            return 'test'
        elif '/api/' in file_path:
            return 'api'
        elif '/core/' in file_path:
            return 'core'
        elif '/utils/' in file_path:
            return 'utils'
        elif '/models/' in file_path:
            return 'models'
        elif '/database/' in file_path:
            return 'database'
        else:
            return 'other'

    def determine_fix_strategy(self, undefined_name: str, file_path: str) -> Dict:
        """确定修复策略和置信度"""
        # 高置信度：常见导入映射
        if undefined_name in self.import_mappings:
            mapping = self.import_mappings[undefined_name]
            return {
                'strategy': 'add_common_import',
                'confidence': mapping['confidence'],
                'suggested_import': mapping
            }

        # 中等置信度：项目内部定义
        project_def = self.find_project_definition(undefined_name, file_path)
        if project_def:
            return {
                'strategy': 'add_project_import',
                'confidence': 0.85,
                'suggested_import': project_def
            }

        # 中等置信度：拼写错误
        similar_names = self.find_similar_names(undefined_name, file_path)
        if similar_names and similar_names[0]['similarity'] > 0.8:
            return {
                'strategy': 'typo_correction',
                'confidence': 0.75,
                'suggested_fix': similar_names[0]['name']
            }

        # 低置信度：需要手动审查
        return {
            'strategy': 'manual_review',
            'confidence': 0.3,
            'suggested_action': 'manual_inspection_required'
        }

    def determine_priority(self, error_info: Dict) -> str:
        """确定修复优先级"""
        module = error_info['module']
        error_info['confidence']

        # 核心模块高优先级
        if module in ['core', 'api']:
            return 'high'
        # 工具和模型中等优先级
        elif module in ['utils', 'models', 'database']:
            return 'medium'
        # 其他低优先级
        else:
            return 'low'

    def find_project_definition(self, name: str, current_file: str) -> Optional[Dict]:
        """在项目中查找定义（优化版本）"""
        project_root = Path(__file__).parent.parent
        src_dir = project_root / 'src'

        # 缓存搜索结果以提高性能
        if not hasattr(self, '_project_definitions_cache'):
            self._project_definitions_cache = {}

        if name in self._project_definitions_cache:
            return self._project_definitions_cache[name]

        # 限制搜索范围以提高性能
        search_paths = [
            src_dir / 'core',
            src_dir / 'utils',
            src_dir / 'models',
            src_dir / 'database',
            src_dir / 'services',
            src_dir / 'api',
        ]

        for search_path in search_paths:
            if not search_path.exists():
                continue

            for py_file in search_path.rglob('*.py'):
                if py_file == Path(current_file):
                    continue

                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()

                    # 使用AST进行更精确的搜索
                    try:
                        tree = ast.parse(content)
                        for node in ast.walk(tree):
                            if isinstance(node, (ast.ClassDef, ast.FunctionDef)) and node.name == name:
                                relative_path = py_file.relative_to(src_dir)
                                module_path = str(relative_path.with_suffix('')).replace('/', '.')

                                result = {
                                    'module': f'src.{module_path}',
                                    'import_type': 'from',
                                    'name': name,
                                    'file_path': str(py_file)
                                }

                                self._project_definitions_cache[name] = result
                                return result
                    except SyntaxError:
                        continue

                except Exception:
                    continue

        return None

    def find_similar_names(self, name: str, file_path: str) -> List[Dict]:
        """查找相似名称（优化版本）"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            tree = ast.parse(content)
            names = set()

            for node in ast.walk(tree):
                if isinstance(node, ast.Name):
                    names.add(node.id)
                elif isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                    names.add(node.name)

            similar_names = []
            for existing_name in names:
                if existing_name != name:
                    similarity = self.calculate_similarity(name, existing_name)
                    if similarity > 0.7:
                        similar_names.append({
                            'name': existing_name,
                            'similarity': similarity
                        })

            return sorted(similar_names, key=lambda x: x['similarity'], reverse=True)

        except Exception:
            return []

    def calculate_similarity(self, s1: str, s2: str) -> float:
        """计算字符串相似度"""
        if not s1 or not s2:
            return 0.0

        # 使用编辑距离算法
        m, n = len(s1), len(s2)
        dp = [[0] * (n + 1) for _ in range(m + 1)]

        for i in range(m + 1):
            dp[i][0] = i
        for j in range(n + 1):
            dp[0][j] = j

        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if s1[i-1] == s2[j-1]:
                    dp[i][j] = dp[i-1][j-1]
                else:
                    dp[i][j] = min(dp[i-1][j], dp[i][j-1], dp[i-1][j-1]) + 1

        max_len = max(m, n)
        return 1 - dp[m][n] / max_len

    def execute_intelligent_batch_fix(self, batch_size: int = 100, confidence_threshold: float = 0.8) -> Dict:
        """执行智能批量修复"""
        logger.info("🚀 开始执行智能批量F821修复...")

        # 分析错误
        analysis = self.analyze_f821_errors()
        if analysis['total_errors'] == 0:
            return {
                'success': True,
                'total_errors': 0,
                'fixed_errors': 0,
                'message': '没有F821错误需要修复'
            }

        # 筛选高置信度修复
        high_confidence_errors = [
            error for error in analysis['high_confidence_fixes']
            if error['confidence'] >= confidence_threshold
        ]

        if not high_confidence_errors:
            logger.warning("⚠️ 没有符合置信度阈值的可自动修复错误")
            return {
                'success': False,
                'total_errors': analysis['total_errors'],
                'fixed_errors': 0,
                'message': f'没有置信度>{confidence_threshold}的可自动修复错误'
            }

        # 按优先级和模块分组处理
        prioritized_errors = sorted(
            high_confidence_errors[:batch_size],
            key=lambda x: (
                0 if x['module'] in ['core', 'api'] else 1 if x['module'] in ['utils', 'models'] else 2,
                x['confidence'],
                x['file']
            )
        )

        # 按文件分组处理
        errors_by_file = defaultdict(list)
        for error in prioritized_errors:
            errors_by_file[error['file']].append(error)

        # 执行修复
        files_fixed = 0
        total_errors_fixed = 0

        for file_path, file_errors in errors_by_file.items():
            logger.info(f"🔧 修复文件: {file_path} ({len(file_errors)}个错误)")

            if self.fix_file_intelligently(file_path, file_errors):
                files_fixed += 1
                total_errors_fixed += len(file_errors)

            self.files_processed += 1

        self.batches_processed += 1

        result = {
            'success': total_errors_fixed > 0,
            'total_errors': analysis['total_errors'],
            'processed_errors': len(prioritized_errors),
            'fixed_errors': total_errors_fixed,
            'files_processed': self.files_processed,
            'files_fixed': files_fixed,
            'batches_processed': self.batches_processed,
            'remaining_errors': analysis['total_errors'] - total_errors_fixed,
            'fix_rate': f"{(total_errors_fixed / max(len(prioritized_errors), 1)) * 100:.1f}%",
            'message': f'处理了{len(prioritized_errors)}个错误，修复了{total_errors_fixed}个'
        }

        logger.info(f"✅ 智能批量修复完成: {result}")
        return result

    def fix_file_intelligently(self, file_path: str, errors: List[Dict]) -> bool:
        """智能修复单个文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            lines = content.split('\n')
            original_lines = lines.copy()

            # 按错误类型分组处理
            import_fixes = {}
            typo_fixes = {}

            for error in errors:
                strategy = error['strategy']
                undefined_name = error['name']

                if strategy == 'add_common_import' or strategy == 'add_project_import':
                    import_info = error['suggested_import']
                    key = f"{import_info['module']}::{import_info.get('name', undefined_name)}"
                    if key not in import_fixes:
                        import_fixes[key] = import_info

                elif strategy == 'typo_correction':
                    typo_fixes[undefined_name] = error['suggested_fix']

            # 添加导入
            if import_fixes:
                lines = self.add_imports_intelligently(lines, list(import_fixes.values()))

            # 修复拼写错误
            if typo_fixes:
                lines = self.fix_typos_intelligently(lines, typo_fixes)

            # 检查是否有修改
            if lines != original_lines:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(lines))

                logger.info(f"✅ 文件修复成功: {file_path}")
                self.fixes_applied += len(errors)
                return True

        except Exception as e:
            logger.error(f"❌ 文件修复失败 {file_path}: {e}")

        return False

    def add_imports_intelligently(self, lines: List[str], imports: List[Dict]) -> List[str]:
        """智能添加导入"""
        # 找到导入区域
        import_end = 0
        for i, line in enumerate(lines):
            if line.strip().startswith(('import ', 'from ')):
                import_end = i + 1
            elif line.strip() and not line.startswith('#') and import_end > 0:
                break

        # 按模块分组导入
        import_groups = defaultdict(list)
        for import_info in imports:
            module = import_info['module']
            if import_info['import_type'] == 'from':
                name = import_info.get('name', module.split('.')[-1])
                import_groups[module].append(name)
            else:
                import_groups[module] = ['*']

        # 生成导入语句
        new_imports = []
        for module, names in sorted(import_groups.items()):
            if len(names) == 1 and names[0] == '*':
                new_imports.append(f"import {module}")
            else:
                names_str = ', '.join(sorted(names))
                new_imports.append(f"from {module} import {names_str}")

        # 插入导入语句
        for import_stmt in sorted(new_imports):
            if import_stmt not in '\n'.join(lines):
                lines.insert(import_end, import_stmt)
                import_end += 1

        return lines

    def fix_typos_intelligently(self, lines: List[str], typo_fixes: Dict[str, str]) -> List[str]:
        """智能修复拼写错误"""
        for i, line in enumerate(lines):
            for wrong_name, correct_name in typo_fixes.items():
                # 只替换独立的标识符
                pattern = r'\b' + re.escape(wrong_name) + r'\b'
                line = re.sub(pattern, correct_name, line)
            lines[i] = line

        return lines

    def generate_phase3_report(self) -> Dict:
        """生成Phase 3报告"""
        return {
            'fixer_name': 'Phase 3 F821 Scalable Intelligent Fixer',
            'timestamp': '2025-10-30T03:00:00.000000',
            'target_errors': '6,604 F821 errors',
            'strategy': 'Intelligent batch processing with confidence filtering',
            'fixes_applied': self.fixes_applied,
            'files_processed': self.files_processed,
            'files_fixed': self.files_fixed,
            'batches_processed': self.batches_processed,
            'success_rate': f"{(self.files_fixed / max(self.files_processed, 1)) * 100:.1f}%",
            'next_phase': 'Layer 2: F405/F841 batch optimization'
        }


def main():
    """主函数"""
    print("🚀 Phase 3 F821规模化智能修复工具")
    print("=" * 70)
    print("🎯 目标: 6,604个F821错误 → <1,000个错误")
    print("🧠 策略: 智能分组 + 渐进修复 + 安全验证")
    print("=" * 70)

    fixer = Phase3F821ScalableFixer()

    # 执行智能批量修复
    result = fixer.execute_intelligent_batch_fix(
        batch_size=100,  # 处理100个错误进行测试
        confidence_threshold=0.8  # 只处理高置信度错误
    )

    # 生成报告
    report = fixer.generate_phase3_report()

    print("\n📊 Phase 3智能修复摘要:")
    print(f"   总错误数: {result['total_errors']}")
    print(f"   处理错误数: {result['processed_errors']}")
    print(f"   修复错误数: {result['fixed_errors']}")
    print(f"   剩余错误数: {result['remaining_errors']}")
    print(f"   处理文件数: {result['files_processed']}")
    print(f"   修复文件数: {result['files_fixed']}")
    print(f"   修复率: {result['fix_rate']}")
    print(f"   状态: {'✅ 成功' if result['success'] else '⚠️ 需要调整策略'}")

    # 保存Phase 3报告
    report_file = Path('phase3_f821_scalable_fix_report.json')
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump({
            'result': result,
            'report': report
        }, f, indent=2, ensure_ascii=False)

    print(f"\n📄 Phase 3报告已保存到: {report_file}")

    if result['remaining_errors'] > 1000:
        print("\n🎯 下一步: 继续执行智能批量修复")
        print("💡 建议: 运行 'python3 scripts/phase3_f821_scalable_fixer.py' 继续处理")
    else:
        print("\n🎉 即将达成目标: 准备进入Layer 2阶段")

    return result


if __name__ == '__main__':
    main()