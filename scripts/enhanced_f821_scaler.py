#!/usr/bin/env python3
"""
增强F821规模化修复器
Enhanced F821 Scaler

基于成功验证的策略，规模化处理F821未定义名称错误
采用智能分组、批量处理、安全验证的方法
"""

import ast
import json
import logging
import re
import subprocess
from pathlib import Path
from typing import Dict, List, Set, Tuple
from collections import defaultdict

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class EnhancedF821Scaler:
    """增强F821规模化修复器"""

    def __init__(self):
        self.fixes_applied = 0
        self.files_processed = 0
        self.files_fixed = 0

        # 增强的导入映射数据库
        self.import_mappings = {
            # FastAPI - 高频使用
            'APIRouter': {'module': 'fastapi', 'import_type': 'from', 'confidence': 0.95},
            'HTTPException': {'module': 'fastapi', 'import_type': 'from', 'confidence': 0.95},
            'Query': {'module': 'fastapi', 'import_type': 'from', 'confidence': 0.95},
            'Depends': {'module': 'fastapi', 'import_type': 'from', 'confidence': 0.95},
            'BackgroundTasks': {'module': 'fastapi', 'import_type': 'from', 'confidence': 0.95},
            'Body': {'module': 'fastapi', 'import_type': 'from', 'confidence': 0.90},
            'Path': {'module': 'fastapi', 'import_type': 'from', 'confidence': 0.90},

            # Pydantic - 高频使用
            'BaseModel': {'module': 'pydantic', 'import_type': 'from', 'confidence': 0.98},
            'Field': {'module': 'pydantic', 'import_type': 'from', 'confidence': 0.98},
            'validator': {'module': 'pydantic', 'import_type': 'from', 'confidence': 0.90},

            # Typing - 高频使用
            'Dict': {'module': 'typing', 'import_type': 'from', 'confidence': 0.99},
            'List': {'module': 'typing', 'import_type': 'from', 'confidence': 0.99},
            'Optional': {'module': 'typing', 'import_type': 'from', 'confidence': 0.99},
            'Union': {'module': 'typing', 'import_type': 'from', 'confidence': 0.90},
            'Any': {'module': 'typing', 'import_type': 'from', 'confidence': 0.90},
            'Callable': {'module': 'typing', 'import_type': 'from', 'confidence': 0.85},
            'Tuple': {'module': 'typing', 'import_type': 'from', 'confidence': 0.85},

            # 标准库 - 中频使用
            'datetime': {'module': 'datetime', 'import_type': 'from', 'confidence': 0.95},
            'Path': {'module': 'pathlib', 'import_type': 'from', 'confidence': 0.90},
            're': {'module': 're', 'import_type': 'import', 'confidence': 0.95},
            'json': {'module': 'json', 'import_type': 'import', 'confidence': 0.95},
            'os': {'module': 'os', 'import_type': 'import', 'confidence': 0.95},
            'sys': {'module': 'sys', 'import_type': 'import', 'confidence': 0.95},
            'time': {'module': 'time', 'import_type': 'import', 'confidence': 0.85},
            'uuid': {'module': 'uuid', 'import_type': 'import', 'confidence': 0.85},

            # Logging - 中频使用
            'logger': {'module': 'logging', 'import_type': 'from', 'name': 'get_logger', 'confidence': 0.90},
            'logging': {'module': 'logging', 'import_type': 'import', 'confidence': 0.90},

            # SQLAlchemy - 低频使用
            'Column': {'module': 'sqlalchemy', 'import_type': 'from', 'confidence': 0.85},
            'Integer': {'module': 'sqlalchemy', 'import_type': 'from', 'confidence': 0.85},
            'String': {'module': 'sqlalchemy', 'import_type': 'from', 'confidence': 0.85},

            # 测试相关
            'pytest': {'module': 'pytest', 'import_type': 'import', 'confidence': 0.80},
            'Mock': {'module': 'unittest.mock', 'import_type': 'from', 'confidence': 0.85},
            'patch': {'module': 'unittest.mock', 'import_type': 'from', 'confidence': 0.85},

            # HTTP相关
            'requests': {'module': 'requests', 'import_type': 'import', 'confidence': 0.85},
            'httpx': {'module': 'httpx', 'import_type': 'import', 'confidence': 0.80},

            # 数据处理
            'pandas': {'module': 'pandas', 'import_type': 'import', 'confidence': 0.80},
            'numpy': {'module': 'numpy', 'import_type': 'import', 'confidence': 0.80},
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
                return {'total_errors': 0, 'high_confidence_errors': []}

            error_data = json.loads(result.stdout)
            f821_errors = [e for e in error_data if e.get('code') == 'F821']

            logger.info(f"📊 发现 {len(f821_errors)} 个F821错误")

            # 分析每个错误
            high_confidence_errors = []
            medium_confidence_errors = []
            low_confidence_errors = []

            for error in f821_errors:
                file_path = error['filename']
                line_num = error['location']['row']
                message = error['message']

                # 提取未定义名称
                undefined_name = self.extract_undefined_name(message)

                # 确定修复策略和置信度
                fix_strategy = self.determine_fix_strategy(undefined_name, file_path)

                error_info = {
                    'file': file_path,
                    'line': line_num,
                    'name': undefined_name,
                    'strategy': fix_strategy['strategy'],
                    'confidence': fix_strategy['confidence'],
                    'suggested_import': fix_strategy.get('suggested_import'),
                    'module_type': self.get_module_type(file_path)
                }

                # 按置信度分类
                if fix_strategy['confidence'] >= 0.9:
                    high_confidence_errors.append(error_info)
                elif fix_strategy['confidence'] >= 0.7:
                    medium_confidence_errors.append(error_info)
                else:
                    low_confidence_errors.append(error_info)

            logger.info(f"📈 分析结果: 高置信度 {len(high_confidence_errors)}, 中置信度 {len(medium_confidence_errors)}, 低置信度 {len(low_confidence_errors)}")

            return {
                'total_errors': len(f821_errors),
                'high_confidence_errors': high_confidence_errors,
                'medium_confidence_errors': medium_confidence_errors,
                'low_confidence_errors': low_confidence_errors
            }

        except Exception as e:
            logger.error(f"F821错误分析失败: {e}")
            return {'total_errors': 0, 'high_confidence_errors': []}

    def extract_undefined_name(self, message: str) -> str:
        """从错误消息中提取未定义名称"""
        match = re.search(r"undefined name '([^']+)'", message)
        return match.group(1) if match else ""

    def get_module_type(self, file_path: str) -> str:
        """获取模块类型"""
        if '/test' in file_path:
            return 'test'
        elif '/src/api/' in file_path:
            return 'api'
        elif '/src/core/' in file_path:
            return 'core'
        elif '/src/utils/' in file_path:
            return 'utils'
        elif '/src/models/' in file_path:
            return 'models'
        elif '/src/database/' in file_path:
            return 'database'
        elif '/src/services/' in file_path:
            return 'services'
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

        # 中等置信度：检查文件类型特定模式
        module_type = self.get_module_type(file_path)

        if module_type == 'test':
            # 测试文件的特殊处理
            if undefined_name in ['Mock', 'patch', 'pytest', 'fixture']:
                return {
                    'strategy': 'add_test_import',
                    'confidence': 0.85,
                    'suggested_import': self.get_test_import(undefined_name)
                }

        elif module_type == 'api':
            # API文件的特殊处理
            if undefined_name in ['router', 'app', 'service']:
                return {
                    'strategy': 'add_api_import',
                    'confidence': 0.8,
                    'suggested_import': self.get_api_import(undefined_name)
                }

        # 低置信度：需要手动审查
        return {
            'strategy': 'manual_review',
            'confidence': 0.3,
            'suggested_action': 'manual_inspection_required'
        }

    def get_test_import(self, name: str) -> Dict:
        """获取测试相关的导入"""
        test_imports = {
            'Mock': {'module': 'unittest.mock', 'import_type': 'from'},
            'patch': {'module': 'unittest.mock', 'import_type': 'from'},
            'pytest': {'module': 'pytest', 'import_type': 'import'},
            'fixture': {'module': 'pytest', 'import_type': 'from'},
        }
        return test_imports.get(name, {})

    def get_api_import(self, name: str) -> Dict:
        """获取API相关的导入"""
        # 这里可以根据项目的实际情况扩展
        return {}

    def execute_batch_fix(self, batch_size: int = 50, confidence_threshold: float = 0.9) -> Dict:
        """执行批量修复"""
        logger.info("🚀 开始执行批量F821修复...")

        # 分析错误
        analysis = self.analyze_f821_errors()
        if analysis['total_errors'] == 0:
            return {
                'success': True,
                'total_errors': 0,
                'fixed_errors': 0,
                'message': '没有F821错误需要修复'
            }

        # 筛选符合条件的错误
        target_errors = []
        for error in analysis['high_confidence_errors']:
            if error['confidence'] >= confidence_threshold:
                target_errors.append(error)

        # 如果高置信度错误不够，添加中置信度错误
        if len(target_errors) < batch_size:
            remaining_needed = batch_size - len(target_errors)
            target_errors.extend(analysis['medium_confidence_errors'][:remaining_needed])

        # 限制批次大小
        target_errors = target_errors[:batch_size]

        logger.info(f"📋 准备修复 {len(target_errors)} 个错误")

        # 按文件分组处理
        errors_by_file = defaultdict(list)
        for error in target_errors:
            errors_by_file[error['file']].append(error)

        # 执行修复
        files_fixed = 0
        total_errors_fixed = 0

        for file_path, file_errors in errors_by_file.items():
            logger.info(f"🔧 修复文件: {file_path} ({len(file_errors)}个错误)")

            if self.fix_file_smartly(file_path, file_errors):
                files_fixed += 1
                total_errors_fixed += len(file_errors)
                self.fixes_applied += len(file_errors)

            self.files_processed += 1

        # 验证修复效果
        remaining_errors = self.get_remaining_f821_count()

        result = {
            'success': total_errors_fixed > 0,
            'total_errors_before': analysis['total_errors'],
            'processed_errors': len(target_errors),
            'fixed_errors': total_errors_fixed,
            'files_processed': self.files_processed,
            'files_fixed': files_fixed,
            'remaining_errors': remaining_errors,
            'reduction': analysis['total_errors'] - remaining_errors,
            'fix_rate': f"{(total_errors_fixed / max(len(target_errors), 1)) * 100:.1f}%",
            'message': f'处理了 {len(target_errors)} 个错误，修复了 {total_errors_fixed} 个'
        }

        logger.info(f"✅ 批量修复完成: {result}")
        return result

    def get_remaining_f821_count(self) -> int:
        """获取剩余F821错误数量"""
        try:
            result = subprocess.run(
                ['ruff', 'check', '--select=F821'],
                capture_output=True,
                text=True,
                timeout=60
            )

            return result.stdout.count('F821')

        except Exception:
            return -1

    def fix_file_smartly(self, file_path: str, errors: List[Dict]) -> bool:
        """智能修复单个文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            lines = content.split('\n')
            original_lines = lines.copy()

            # 按错误类型分组处理
            import_fixes = set()

            for error in errors:
                strategy = error['strategy']
                if strategy in ['add_common_import', 'add_test_import']:
                    import_info = error['suggested_import']
                    if import_info:
                        key = f"{import_info['module']}::{import_info.get('name', error['name'])}"
                        import_fixes.add(key)

            # 智能添加导入
            if import_fixes:
                lines = self.add_imports_intelligently(lines, list(import_fixes))

            # 检查是否有修改
            if lines != original_lines:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(lines))

                logger.info(f"✅ 文件修复成功: {file_path}")
                return True

        except Exception as e:
            logger.error(f"❌ 文件修复失败 {file_path}: {e}")

        return False

    def add_imports_intelligently(self, lines: List[str], import_keys: List[str]) -> List[str]:
        """智能添加导入语句"""
        # 解析导入键值
        imports_to_add = []
        for key in import_keys:
            module, name = key.split('::')
            if name == module:
                imports_to_add.append(('import', module, None))
            else:
                imports_to_add.append(('from', module, name))

        # 查找导入区域
        import_end = 0
        in_import_section = False

        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith(('import ', 'from ')):
                import_end = i + 1
                in_import_section = True
            elif stripped and not stripped.startswith('#') and in_import_section:
                break

        # 按类型分组导入
        import_stmts = []
        from_imports = defaultdict(list)

        for import_type, module, name in imports_to_add:
            if import_type == 'import':
                import_stmts.append(f"import {module}")
            else:  # from import
                from_imports[module].append(name)

        # 生成from import语句
        for module, names in from_imports.items():
            names_str = ', '.join(sorted(names))
            import_stmts.append(f"from {module} import {names_str}")

        # 插入导入语句
        for import_stmt in sorted(import_stmts):
            if import_stmt not in '\n'.join(lines):
                lines.insert(import_end, import_stmt)
                import_end += 1

        return lines

    def generate_scaler_report(self) -> Dict:
        """生成修复器报告"""
        return {
            'scaler_name': 'Enhanced F821 Scaler',
            'timestamp': '2025-10-30T02:30:00.000000',
            'target_errors': '6,604 F821 errors',
            'strategy': 'Smart grouping + batch processing + confidence filtering',
            'fixes_applied': self.fixes_applied,
            'files_processed': self.files_processed,
            'files_fixed': self.files_fixed,
            'success_rate': f"{(self.files_fixed / max(self.files_processed, 1)) * 100:.1f}%",
            'next_step': 'Continue with medium confidence errors or F405/F841 cleanup'
        }


def main():
    """主函数"""
    print("🚀 增强F821规模化修复器")
    print("=" * 60)
    print("🎯 目标: 6,604个F821错误 → 智能批量修复")
    print("🧠 策略: 高置信度优先 + 安全批量处理")
    print("=" * 60)

    scaler = EnhancedF821Scaler()

    # 执行批量修复
    result = scaler.execute_batch_fix(
        batch_size=50,  # 每批处理50个错误
        confidence_threshold=0.9  # 只处理高置信度错误
    )

    # 生成报告
    report = scaler.generate_scaler_report()

    print("\n📊 规模化修复摘要:")
    print(f"   修复前错误数: {result['total_errors_before']}")
    print(f"   处理错误数: {result['processed_errors']}")
    print(f"   修复错误数: {result['fixed_errors']}")
    print(f"   剩余错误数: {result['remaining_errors']}")
    print(f"   错误减少量: {result['reduction']}")
    print(f"   处理文件数: {result['files_processed']}")
    print(f"   修复文件数: {result['files_fixed']}")
    print(f"   修复率: {result['fix_rate']}")
    print(f"   状态: {'✅ 成功' if result['success'] else '⚠️ 需要调整策略'}")

    # 保存报告
    report_file = Path('enhanced_f821_scaler_report.json')
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump({
            'result': result,
            'report': report
        }, f, indent=2, ensure_ascii=False)

    print(f"\n📄 规模化修复报告已保存到: {report_file}")

    if result['remaining_errors'] > 5000:
        print("\n🎯 下一步: 继续执行规模化修复")
        print("💡 建议: 运行 'python3 scripts/enhanced_f821_scaler.py' 继续处理")
    elif result['remaining_errors'] > 1000:
        print("\n🎯 进展良好: 即将达到<5,000错误目标")
        print("💡 建议: 准备转向F405/F841清理")
    else:
        print("\n🎉 即将达成目标: 准备最终质量门禁验证")

    return result


if __name__ == '__main__':
    main()