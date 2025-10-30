#!/usr/bin/env python3
"""
全面语法错误修复工具
批量修复常见的Python语法错误，支持多种错误类型
"""

import os
import re
import ast
from pathlib import Path
from typing import List, Tuple, Dict
import subprocess
import json

class SyntaxErrorFixer:
    def __init__(self):
        self.fixes_applied = 0
        self.files_processed = 0
        self.errors_fixed = {}

    def fix_invalid_syntax_patterns(self, content: str, file_path: str) -> str:
        """修复无效语法模式"""
        original_content = content
        fixes_count = 0

        # 修复模式1: isinstance参数错误
        content = re.sub(r'isinstance\([^,]+,\s*\(([^)]+)\)\)', r'isinstance(\1, \2)', content)
        if content != original_content:
            fixes_count += 1

        # 修复模式2: 多余的右括号
        content = re.sub(r'\)\)+', ')', content)
        if content != original_content:
            fixes_count += 1

        # 修复模式3: 未闭合的字符串
        content = re.sub(r'"([^"]*)\)\s*\)', r'"\1")', content)
        if content != original_content:
            fixes_count += 1

        # 修复模式4: 函数参数中的语法错误
        content = re.sub(r'def\s+(\w+)\([^)]*:\)\)', r'def \1():', content)
        if content != original_content:
            fixes_count += 1

        # 修复模式5: except语句缩进问题
        content = re.sub(r'\s+except Exception:\s*return None', '\n    except Exception:\n        return None', content)
        if content != original_content:
            fixes_count += 1

        # 修复模式6: 类型注解中的语法错误
        content = re.sub(r': Dict\[str\)\)', ': Dict[str, Any]', content)
        content = re.sub(r': List\[.*\)\)', ': List[Any]', content)
        content = re.sub(r': Optional\[.*\)\)', ': Optional[Any]', content)
        if content != original_content:
            fixes_count += 1

        # 修复模式7: Redis连接语法错误
        content = re.sub(r'redis\.Redis\([^)]*\)\)', 'redis.Redis()', content)
        if content != original_content:
            fixes_count += 1

        # 修复模式8: 逗号和分号语法错误
        content = re.sub(r',\s*else\s*:', ':', content)
        content = re.sub(r':\s*else\s*,\s*', ',\n        ', content)
        if content != original_content:
            fixes_count += 1

        return content, fixes_count

    def fix_specific_file(self, file_path: str) -> bool:
        """修复特定文件的语法错误"""
        try:
            path = Path(file_path)
            if not path.exists():
                return False

            content = path.read_text(encoding='utf-8')
            original_content = content

            # 应用语法修复
            content, fixes_count = self.fix_invalid_syntax_patterns(content, file_path)

            # 验证修复效果
            try:
                ast.parse(content)
                if content != original_content:
                    path.write_text(content, encoding='utf-8')
                    print(f"✅ 修复了 {file_path} ({fixes_count}个修复)")
                    self.errors_fixed[file_path] = fixes_count
                    self.fixes_applied += fixes_count
                    return True
                else:
                    return False
            except SyntaxError as e:
                # 如果还有语法错误，记录并尝试简单修复
                print(f"⚠️  {file_path} 仍有语法错误: {e}")
                return False

        except Exception as e:
            print(f"❌ 修复 {file_path} 时出错: {e}")
            return False

    def fix_multiple_files(self, patterns: List[str]) -> Dict[str, int]:
        """批量修复多个文件"""
        print(f"🔧 开始批量修复，模式: {patterns}")
        
        files_to_fix = []
        for pattern in patterns:
            files_to_fix.extend(Path('.').glob(pattern))
        
        print(f"📁 找到 {len(files_to_fix)} 个文件")
        
        success_count = 0
        for file_path in files_to_fix:
            if self.fix_specific_file(str(file_path)):
                success_count += 1
            self.files_processed += 1
        
        return {
            'total_files': len(files_to_fix),
            'successful_fixes': success_count,
            'total_fixes': self.fixes_applied,
            'files_processed': self.files_processed,
            'errors_fixed': self.errors_fixed
        }

def run_ruff_check_before_fix() -> int:
    """运行Ruff检查获取基准错误数"""
    try:
        result = subprocess.run(
            ['ruff', 'check', 'src/', '--output-format=json'],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.stdout:
            errors = result.stdout.strip()
            if errors.startswith('[') and errors.endswith(']'):
                error_list = json.loads(errors)
                return len(error_list)
        return 0
    except:
        return 0

def run_ruff_check_after_fix() -> Dict:
    """运行Ruff检查验证修复效果"""
    try:
        result = subprocess.run(
            ['ruff', 'check', 'src/', '--output-format=json'],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.stdout and result.stdout.strip():
            errors = result.stdout.strip()
            if errors.startswith('[') and errors.endswith(']'):
                error_list = json.loads(errors)
                
                error_types = {}
                for error in error_list:
                    code = error.get('code', 'unknown')
                    error_types[code] = error_types.get(code, 0) + 1
                
                return {
                    'total_errors': len(error_list),
                    'error_types': error_types,
                    'sample_errors': error_list[:10]
                }
        
        return {'total_errors': 0}
    except Exception as e:
        return {'total_errors': -1, 'error': str(e)}

def main():
    """主函数"""
    print("🚀 全面语法错误修复工具")
    print("=" * 50)
    
    # 获取基准错误数
    print("📊 获取基准错误数...")
    baseline_errors = run_ruff_check_before_fix()
    print(f"基准Ruff错误数: {baseline_errors}")
    
    # 创建修复器实例
    fixer = SyntaxErrorFixer()
    
    # 优先修复关键文件
    priority_files = [
        "src/alerting/*.py",
        "src/adapters/*.py", 
        "src/utils/*.py",
        "src/config/*.py",
        "src/api/*.py"
    ]
    
    print("\n🔧 修复优先文件...")
    priority_results = fixer.fix_multiple_files(priority_files)
    
    # 如果还有时间，修复更多文件
    if priority_results['total_fixes'] > 0:
        print(f"\n✅ 优先文件修复完成:")
        print(f"   - 处理文件: {priority_results['successful_fixes']}/{priority_results['total_files']}")
        print(f"   - 总修复数: {priority_results['total_fixes']}")
        
        print("\n🔧 修复更多文件...")
        all_files = [
            "src/**/*.py"
        ]
        all_results = fixer.fix_multiple_files(all_files)
        
        total_fixes = priority_results['total_fixes'] + all_results['total_fixes']
        total_files = priority_results['total_files'] + all_results['total_files']
        
        print(f"\n📊 总修复结果:")
        print(f"   - 总处理文件: {total_files}")
        print(f"   - 成功修复: {priority_results['successful_fixes'] + all_results['successful_fixes']}")
        print(f"   - 总修复数: {total_fixes}")
    else:
        print("\n⚠️  没有需要修复的文件")
    
    # 验证修复效果
    print("\n🔍 验证修复效果...")
    after_fix = run_ruff_check_after_fix()
    
    if after_fix.get('total_errors') >= 0:
        reduction = baseline_errors - after_fix['total_errors']
        reduction_rate = (reduction / baseline_errors * 100) if baseline_errors > 0 else 0
        
        print(f"\n📈 修复效果:")
        print(f"   - 修复前错误: {baseline_errors}")
        print(f"   - 修复后错误: {after_fix['total_errors']}")
        print(f"   - 错误减少: {reduction}")
        print(f"   - 减少率: {reduction_rate:.1f}%")
        
        if reduction_rate > 50:
            print("🎉 语法错误修复非常成功！")
        elif reduction_rate > 20:
            print("✅ 语法错误修复成功")
        else:
            print("⚠️  语法错误修复效果有限")
    else:
        print("❌ 无法验证修复效果")
    
    return fixer.fixes_applied

if __name__ == "__main__":
    main()
