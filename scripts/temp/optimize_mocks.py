#!/usr/bin/env python3
"""
Mock与依赖隔离优化脚本
统一Mock导入使用，隔离外部依赖
"""

import re
from pathlib import Path
from typing import List, Dict, Set

class MockOptimizer:
    def __init__(self, tests_dir: str = "tests"):
        self.tests_dir = Path(tests_dir)
        self.optimized_count = 0
        self.errors = []

    def standardize_mock_imports(self, file_path: Path) -> bool:
        """标准化Mock导入语句"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            original_content = content

            # 标准化Mock导入
            mock_imports = [
                "from unittest.mock import Mock",
                "from unittest.mock import patch",
                "from unittest.mock import AsyncMock",
                "from unittest.mock import MagicMock",
                "from unittest.mock import call",
                "from unittest.mock import PropertyMock",
                "from unittest.mock import Mock, patch",
                "from unittest.mock import Mock, AsyncMock",
                "from unittest.mock import Mock, MagicMock",
                "from unittest.mock import patch, AsyncMock",
                "from unittest.mock import Mock, patch, AsyncMock, MagicMock",
                "from unittest.mock import Mock, patch, AsyncMock, MagicMock, call",
                "from unittest.mock import Mock, patch, AsyncMock, MagicMock, call, PropertyMock"
            ]

            # 移除重复的Mock导入
            lines = content.split('\n')
            mock_lines = []
            other_lines = []
            seen_mock_imports = set()

            for line in lines:
                stripped = line.strip()
                if any(stripped.startswith(mock_imp) for mock_imp in mock_imports):
                    if stripped not in seen_mock_imports:
                        mock_lines.append(line)
                        seen_mock_imports.add(stripped)
                else:
                    other_lines.append(line)

            # 构建标准化的Mock导入
            if mock_lines:
                # 提取已使用的Mock组件
                used_mock_components = set()
                for mock_line in mock_lines:
                    # 解析导入语句
                    match = re.search(r'from unittest\.mock import (.+)', mock_line.strip())
                    if match:
                        imports = match.group(1).split(', ')
                        used_mock_components.update(imp.strip() for imp in imports)

                # 按标准顺序排序
                standard_order = ['Mock', 'patch', 'AsyncMock', 'MagicMock', 'call', 'PropertyMock']
                sorted_imports = [comp for comp in standard_order if comp in used_mock_components]

                # 添加其他不在标准列表中的组件
                other_components = [comp for comp in used_mock_components if comp not in standard_order]
                sorted_imports.extend(other_components)

                # 生成标准导入行
                standard_mock_import = f"from unittest.mock import {', '.join(sorted_imports)}"

                # 重新组装文件内容
                # 找到import部分
                import_section_end = 0
                for i, line in enumerate(other_lines):
                    if line.strip() and not (line.strip().startswith('import ') or line.strip().startswith('from ') or line.strip().startswith('#')):
                        import_section_end = i
                        break
                else:
                    import_section_end = len(other_lines)

                # 插入标准Mock导入
                other_lines.insert(import_section_end, standard_mock_import)
                content = '\n'.join(other_lines)

            # 检查内容是否变化
            if content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                return True

            return False

        except Exception as e:
            self.errors.append(f"Error optimizing mocks in {file_path}: {e}")
            return False

    def isolate_external_dependencies(self, file_path: Path) -> bool:
        """隔离外部依赖，添加patch装饰器"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            original_content = content

            # 外部依赖模式
            external_patterns = [
                (r'requests\.', '@patch("requests.get")'),
                (r'requests\.', '@patch("requests.post")'),
                (r'asyncio\.sleep', '@patch("asyncio.sleep")'),
                (r'time\.sleep', '@patch("time.sleep")'),
                (r'datetime\.datetime\.now', '@patch("datetime.datetime.now")'),
                (r'os\.environ', '@patch.dict("os.environ")'),
                (r'sqlalchemy\.create_engine', '@patch("sqlalchemy.create_engine")'),
                (r'redis\.Redis', '@patch("redis.Redis")'),
                (r'fastapi\.HTTPException', '@patch("fastapi.HTTPException")'),
            ]

            # 查找需要隔离的外部调用
            lines = content.split('\n')
            modified_lines = []

            for i, line in enumerate(lines):
                modified_line = line
                for pattern, patch_decorator in external_patterns:
                    if re.search(pattern, line) and not any('patch' in prev_line for prev_line in lines[max(0, i-5):i]):
                        # 检查是否在测试函数中
                        in_test_function = False
                        for j in range(max(0, i-10), i):
                            if re.search(r'def test_', lines[j]):
                                in_test_function = True
                                break

                        if in_test_function:
                            # 在函数前添加patch装饰器
                            # 找到函数定义行
                            for j in range(max(0, i-10), i):
                                if re.search(r'def test_', lines[j]):
                                    # 在函数定义前插入patch
                                    if j == 0 or not lines[j-1].strip().startswith('@patch'):
                                        lines.insert(j, patch_decorator)
                                        break
                            break

                modified_lines.append(modified_line)

            content = '\n'.join(modified_lines)

            if content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                return True

            return False

        except Exception as e:
            self.errors.append(f"Error isolating dependencies in {file_path}: {e}")
            return False

    def optimize_fixture_usage(self, file_path: Path) -> bool:
        """优化fixture使用，减少重复代码"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            original_content = content

            # 查找重复的Mock创建模式
            lines = content.split('\n')
            mock_patterns = {}

            # 收集Mock创建模式
            for i, line in enumerate(lines):
                if 'Mock(' in line or 'MagicMock(' in line:
                    # 简单的模式识别
                    mock_type = 'Mock' if 'Mock(' in line else 'MagicMock'
                    mock_patterns[mock_type] = mock_patterns.get(mock_type, 0) + 1

            # 如果有大量重复的Mock创建，建议使用fixture
            for mock_type, count in mock_patterns.items():
                if count > 3:  # 如果有超过3个相同的Mock创建
                    # 在文件开头添加fixture建议注释
                    if "# TODO: Consider creating a fixture for repeated Mock creation" not in content:
                        lines.insert(0, "")
                        lines.insert(0, f"# TODO: Consider creating a fixture for {count} repeated {mock_type} creations")
                        content = '\n'.join(lines)
                        break

            if content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                return True

            return False

        except Exception as e:
            self.errors.append(f"Error optimizing fixtures in {file_path}: {e}")
            return False

    def process_file(self, file_path: Path) -> Dict[str, bool]:
        """处理单个文件的所有优化"""
        results = {
            'mock_imports_optimized': False,
            'dependencies_isolated': False,
            'fixtures_optimized': False
        }

        # 1. 标准化Mock导入
        if self.standardize_mock_imports(file_path):
            results['mock_imports_optimized'] = True

        # 2. 隔离外部依赖
        if self.isolate_external_dependencies(file_path):
            results['dependencies_isolated'] = True

        # 3. 优化fixture使用
        if self.optimize_fixture_usage(file_path):
            results['fixtures_optimized'] = True

        return results

    def run(self) -> Dict[str, any]:
        """执行Mock优化流程"""
        print("🎭 开始Mock与依赖隔离优化...")

        if not self.tests_dir.exists():
            raise FileNotFoundError(f"Tests directory {self.tests_dir} not found")

        total_stats = {
            'files_processed': 0,
            'mock_imports_optimized': 0,
            'dependencies_isolated': 0,
            'fixtures_optimized': 0,
            'errors': 0
        }

        # 处理所有Python文件
        for file_path in self.tests_dir.rglob("*.py"):
            if file_path.name in ["__init__.py", "conftest.py"]:
                continue

            total_stats['files_processed'] += 1
            results = self.process_file(file_path)

            if any(results.values()):
                self.optimized_count += 1
                print(f"优化完成: {file_path}")
                for key, value in results.items():
                    if value:
                        stat_key = key.replace('_optimized', '')
                        if stat_key in total_stats:
                            total_stats[stat_key] += 1

        total_stats['errors'] = len(self.errors)

        return {
            'stats': total_stats,
            'optimized_count': self.optimized_count,
            'errors': self.errors
        }

def main():
    """主函数"""
    optimizer = MockOptimizer()

    try:
        result = optimizer.run()

        print("\n✅ Mock优化完成!")
        print(f"📊 处理文件总数: {result['stats']['files_processed']}")
        print(f"🏷️  优化导入文件: {result['stats']['mock_imports_optimized']}")
        print(f"🔒 隔离依赖文件: {result['stats']['dependencies_isolated']}")
        print(f"🛠️  优化fixture文件: {result['stats']['fixtures_optimized']}")
        print(f"⚠️  错误数量: {result['stats']['errors']}")

        if result['errors']:
            print("\n⚠️ 错误详情:")
            for error in result['errors'][:5]:
                print(f"  - {error}")

        return result

    except Exception as e:
        print(f"❌ Mock优化失败: {e}")
        return None

if __name__ == "__main__":
    main()