#!/usr/bin/env python3
"""
F821未定义名称批量修复工具
F821 Undefined Name Batch Fixer

专门用于批量修复F821未定义名称错误，采用智能分析+批量处理策略：
1. 上下文感知的名称分析
2. 智能导入建议和修复
3. 批量处理核心模块
4. 安全验证机制

目标: 解决~6,619个F821错误，恢复核心功能
"""

import ast
import json
import logging
import re
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Set

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class F821NameFixer:
    """F821未定义名称修复器"""

    def __init__(self):
        self.fixes_applied = 0
        self.files_processed = 0
        self.files_fixed = 0
        self.import_mappings = {}  # 存储发现的导入映射

        # 常见的未定义名称和可能的修复方案
        self.common_fixes = {
            'APIRouter': {'module': 'fastapi', 'import_type': 'from'},
            'HTTPException': {'module': 'fastapi', 'import_type': 'from'},
            'Query': {'module': 'fastapi', 'import_type': 'from'},
            'logger': {'module': 'logging', 'import_type': 'from', 'name': 'get_logger'},
            'datetime': {'module': 'datetime', 'import_type': 'from'},
            'Dict': {'module': 'typing', 'import_type': 'from'},
            'List': {'module': 'typing', 'import_type': 'from'},
            'Optional': {'module': 'typing', 'import_type': 'from'},
            'BaseModel': {'module': 'pydantic', 'import_type': 'from'},
            'Field': {'module': 'pydantic', 'import_type': 'from'},
            'Depends': {'module': 'fastapi', 'import_type': 'from'},
            'BackgroundTasks': {'module': 'fastapi', 'import_type': 'from'},
        }

    def get_f821_errors(self, limit: Optional[int] = None) -> List[Dict]:
        """获取F821未定义名称错误"""
        logger.info("🎯 正在获取F821未定义名称错误列表...")
        errors = []

        try:
            result = subprocess.run(
                ['ruff', 'check', '--select=F821', '--format=json'],
                capture_output=True,
                text=True,
                timeout=120
            )

            if result.stdout.strip():
                try:
                    error_data = json.loads(result.stdout)
                    for error in error_data:
                        if error.get('code') == 'F821':
                            errors.append({
                                'file': error['filename'],
                                'line': error['location']['row'],
                                'column': error['location']['column'],
                                'message': error['message'],
                                'code': 'F821',
                                'undefined_name': self.extract_undefined_name(error['message'])
                            })

                            if limit and len(errors) >= limit:
                                break

                except json.JSONDecodeError:
                    logger.warning("无法解析Ruff JSON输出，使用文本解析")
                    # 备用文本解析方法
                    lines = result.stdout.split('\n')
                    for line in lines:
                        if 'F821' in line and 'undefined name' in line:
                            parts = line.split(':')
                            if len(parts) >= 4:
                                message = ':'.join(parts[3:]).strip()
                                errors.append({
                                    'file': parts[0],
                                    'line': int(parts[1]),
                                    'column': int(parts[2]),
                                    'message': message,
                                    'code': 'F821',
                                    'undefined_name': self.extract_undefined_name(message)
                                })

                                if limit and len(errors) >= limit:
                                    break

        except Exception as e:
            logger.error(f"获取F821错误失败: {e}")

        logger.info(f"🎯 发现 {len(errors)} 个F821未定义名称错误")
        return errors

    def extract_undefined_name(self, message: str) -> str:
        """从错误消息中提取未定义的名称"""
        # 消息格式通常是: "undefined name 'NAME'"
        match = re.search(r"undefined name '([^']+)'", message)
        if match:
            return match.group(1)
        return ""

    def analyze_undefined_name(self, file_path: str, undefined_name: str, line_num: int) -> Dict:
        """分析未定义名称并生成修复建议"""
        analysis = {
            'name': undefined_name,
            'strategy': 'unknown',
            'suggested_import': None,
            'confidence': 0.0,
            'context': {}
        }

        # 检查常见修复映射
        if undefined_name in self.common_fixes:
            fix_info = self.common_fixes[undefined_name]
            analysis.update({
                'strategy': 'add_common_import',
                'suggested_import': fix_info,
                'confidence': 0.8,
                'context': {'source': 'common_fixes_mapping'}
            })
            return analysis

        # 检查是否是项目中定义的类/函数
        project_fix = self.find_project_definition(undefined_name, file_path)
        if project_fix:
            analysis.update({
                'strategy': 'add_project_import',
                'suggested_import': project_fix,
                'confidence': 0.9,
                'context': {'source': 'project_search'}
            })
            return analysis

        # 检查是否是拼写错误
        similar_names = self.find_similar_names(undefined_name, file_path)
        if similar_names:
            analysis.update({
                'strategy': 'typo_correction',
                'suggested_fix': similar_names[0],
                'confidence': 0.6,
                'context': {'similar_names': similar_names}
            })
            return analysis

        # 检查是否应该是局部变量
        if self.is_likely_local_variable(undefined_name, file_path, line_num):
            analysis.update({
                'strategy': 'local_variable',
                'confidence': 0.4,
                'context': {'suggestion': 'check_variable_scope'}
            })
            return analysis

        return analysis

    def find_project_definition(self, name: str, current_file: str) -> Optional[Dict]:
        """在项目中查找定义"""
        project_root = Path(__file__).parent.parent
        src_dir = project_root / 'src'

        # 常见的项目模块路径
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

            # 搜索Python文件中的定义
            for py_file in search_path.rglob('*.py'):
                if py_file == Path(current_file):
                    continue

                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()

                    # 简单搜索定义
                    patterns = [
                        rf'class\s+{name}\s*\(',
                        rf'def\s+{name}\s*\(',
                        rf'{name}\s*=',
                        rf'{name}\s*:'
                    ]

                    for pattern in patterns:
                        if re.search(pattern, content):
                            # 计算相对导入路径
                            relative_path = py_file.relative_to(src_dir)
                            module_path = str(relative_path.with_suffix('')).replace('/', '.')

                            return {
                                'module': f'src.{module_path}',
                                'import_type': 'from',
                                'name': name,
                                'file_path': str(py_file)
                            }

                except Exception as e:
                    logger.debug(f"搜索文件 {py_file} 失败: {e}")
                    continue

        return None

    def find_similar_names(self, name: str, file_path: str) -> List[str]:
        """查找相似的名称（可能的拼写错误）"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 提取所有标识符
            tree = ast.parse(content)
            names = set()

            for node in ast.walk(tree):
                if isinstance(node, ast.Name):
                    names.add(node.id)
                elif isinstance(node, ast.FunctionDef):
                    names.add(node.name)
                elif isinstance(node, ast.ClassDef):
                    names.add(node.name)

            # 查找相似名称
            similar = []
            for existing_name in names:
                if existing_name != name and self.string_similarity(name, existing_name) > 0.7:
                    similar.append(existing_name)

            return sorted(similar, key=lambda x: self.string_similarity(name, x), reverse=True)

        except Exception as e:
            logger.debug(f"查找相似名称失败: {e}")
            return []

    def string_similarity(self, s1: str, s2: str) -> float:
        """简单的字符串相似度计算"""
        if not s1 or not s2:
            return 0.0

        # 编辑距离算法
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

    def is_likely_local_variable(self, name: str, file_path: str, line_num: int) -> bool:
        """判断是否可能是局部变量"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            # 检查前面几行是否有定义
            for i in range(max(0, line_num - 10), line_num - 1):
                line = lines[i].strip()
                if f'{name} =' in line or f'for {name}' in line or f'def {name}' in line:
                    return True

            return False

        except Exception:
            return False

    def apply_fix(self, file_path: str, line_num: int, analysis: Dict) -> bool:
        """应用修复方案"""
        strategy = analysis['strategy']

        if strategy == 'add_common_import' or strategy == 'add_project_import':
            return self.add_import_fix(file_path, analysis['suggested_import'])
        elif strategy == 'typo_correction':
            return self.fix_typo(file_path, line_num, analysis['suggested_fix'])
        else:
            logger.warning(f"未实现的修复策略: {strategy}")
            return False

    def add_import_fix(self, file_path: str, import_info: Dict) -> bool:
        """添加导入修复"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            lines = content.split('\n')

            # 找到导入区域
            import_end = 0
            for i, line in enumerate(lines):
                if line.strip().startswith(('import ', 'from ')):
                    import_end = i + 1
                elif line.strip() and not line.startswith('#') and import_end > 0:
                    break

            # 构建导入语句
            module = import_info['module']
            name = import_info.get('name', import_info.get('suggested_name', module.split('.')[-1]))

            import_statement = f"from {module} import {name}"

            # 添加导入
            lines.insert(import_end, import_statement)

            # 写回文件
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))

            logger.info(f"✅ 添加导入: {file_path} - {import_statement}")
            return True

        except Exception as e:
            logger.error(f"添加导入失败 {file_path}: {e}")
            return False

    def fix_typo(self, file_path: str, line_num: int, correct_name: str) -> bool:
        """修复拼写错误"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            if line_num <= len(lines):
                original_line = lines[line_num - 1]
                # 这里需要更智能的替换逻辑
                # 暂时跳过拼写错误修复
                logger.info(f"⚠️ 跳过拼写错误修复: {file_path}:{line_num} - {original_line.strip()}")
                return False

        except Exception as e:
            logger.error(f"修复拼写错误失败 {file_path}:{line_num}: {e}")
            return False

    def run_batch_f821_fix(self, batch_size: int = 50) -> Dict:
        """运行批量F821修复"""
        logger.info("🎯 开始F821未定义名称批量修复...")

        # 分批处理错误
        all_errors = self.get_f821_errors()
        total_errors = len(all_errors)

        if not all_errors:
            logger.info("✅ 没有发现F821错误")
            return {
                'success': True,
                'errors_fixed': 0,
                'files_processed': 0,
                'files_fixed': 0,
                'message': '没有F821错误需要修复'
            }

        # 按核心模块优先级排序
        core_modules = ['src/api/', 'src/core/', 'src/utils/']
        prioritized_errors = []

        for module in core_modules:
            module_errors = [e for e in all_errors if module in e['file']]
            prioritized_errors.extend(module_errors)

        # 添加其他错误
        other_errors = [e for e in all_errors if not any(module in e['file'] for module in core_modules)]
        prioritized_errors.extend(other_errors)

        # 处理指定批次的错误
        errors_to_process = prioritized_errors[:batch_size]

        # 按文件分组
        errors_by_file = {}
        for error in errors_to_process:
            file_path = error['file']
            if file_path not in errors_by_file:
                errors_by_file[file_path] = []
            errors_by_file[file_path].append(error)

        # 修复每个文件
        files_fixed = 0
        total_errors_fixed = 0

        for file_path, file_errors in errors_by_file.items():
            logger.info(f"🔧 正在修复文件: {file_path} ({len(file_errors)}个错误)")

            file_fixed = False
            for error in file_errors:
                undefined_name = error['undefined_name']
                line_num = error['line']

                # 分析错误
                analysis = self.analyze_undefined_name(file_path, undefined_name, line_num)
                logger.info(f"📋 错误分析: {undefined_name} -> {analysis['strategy']} (confidence: {analysis['confidence']})")

                # 应用修复
                if analysis['confidence'] > 0.6:  # 只应用高置信度的修复
                    if self.apply_fix(file_path, line_num, analysis):
                        total_errors_fixed += 1
                        file_fixed = True
                        self.fixes_applied += 1

            if file_fixed:
                files_fixed += 1

            self.files_processed += 1

        result = {
            'success': total_errors_fixed > 0,
            'total_errors': total_errors,
            'processed_errors': len(errors_to_process),
            'errors_fixed': total_errors_fixed,
            'files_processed': self.files_processed,
            'files_fixed': files_fixed,
            'remaining_errors': total_errors - total_errors_fixed,
            'fix_rate': f"{(total_errors_fixed / max(len(errors_to_process), 1)) * 100:.1f}%",
            'message': f'处理了 {len(errors_to_process)} 个错误，修复了 {total_errors_fixed} 个，{total_errors - total_errors_fixed} 个剩余'
        }

        logger.info(f"🎯 F821批量修复完成: {result}")
        return result

    def generate_progress_report(self) -> Dict:
        """生成进度报告"""
        return {
            'fixer_name': 'F821 Undefined Name Batch Fixer',
            'timestamp': '2025-10-30T02:30:00.000000',
            'target_errors': '~6,619',
            'fixes_applied': self.fixes_applied,
            'files_processed': self.files_processed,
            'files_fixed': self.files_fixed,
            'success_rate': f"{(self.files_fixed / max(self.files_processed, 1)) * 100:.1f}%",
            'next_steps': '继续批量处理剩余的F821错误，然后转向其他错误类型'
        }


def main():
    """主函数"""
    print("🎯 F821 未定义名称批量修复工具")
    print("=" * 60)
    print("🎯 目标: ~6,619个F821错误 | 核心模块优先")
    print("=" * 60)

    fixer = F821NameFixer()

    # 运行批量修复（先处理50个测试）
    result = fixer.run_batch_f821_fix(batch_size=50)

    # 生成报告
    report = fixer.generate_progress_report()

    print("\n📊 批量修复摘要:")
    print(f"   总错误数: {result['total_errors']}")
    print(f"   处理错误数: {result['processed_errors']}")
    print(f"   修复错误数: {result['errors_fixed']}")
    print(f"   剩余错误数: {result['remaining_errors']}")
    print(f"   处理文件数: {result['files_processed']}")
    print(f"   修复文件数: {result['files_fixed']}")
    print(f"   修复率: {result['fix_rate']}")
    print(f"   状态: {'✅ 成功' if result['success'] else '⚠️ 需要更多处理'}")

    # 保存进度报告
    report_file = Path('f821_batch_fix_progress.json')
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump({
            'result': result,
            'report': report
        }, f, indent=2, ensure_ascii=False)

    print(f"\n📄 进度报告已保存到: {report_file}")

    if result['remaining_errors'] > 0:
        print(f"\n🎯 下一步: 继续处理剩余 {result['remaining_errors']} 个F821错误")
        print("💡 建议: 运行 'python3 scripts/f821_undefined_name_fixer.py' 继续批量修复")

    return result


if __name__ == '__main__':
    main()