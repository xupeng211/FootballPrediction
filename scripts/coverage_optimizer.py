#!/usr/bin/env python3
"""
覆盖率测量和优化工具
建立准确的覆盖率测量机制，提供覆盖率提升策略
"""

import os
import sys
import json
import subprocess
import coverage
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import argparse


@dataclass
class CoverageReport:
    """覆盖率报告数据类"""
    total_statements: int
    missing_statements: int
    coverage_percent: float
    file_reports: Dict[str, Dict[str, Any]]

    @property
    def covered_statements(self) -> int:
        return self.total_statements - self.missing_statements


class CoverageOptimizer:
    """覆盖率优化器"""

    def __init__(self, project_root: Path = None):
        self.project_root = project_root or Path(__file__).parent.parent
        self.src_dir = self.project_root / "src"
        self.tests_dir = self.project_root / "tests"
        self.coverage_dir = self.project_root / "htmlcov"
        self.coverage_file = self.project_root / ".coverage"

    def run_coverage_analysis(self, test_pattern: str = None) -> CoverageReport:
        """运行覆盖率分析"""
        print("🔍 开始覆盖率分析...")

        # 清理旧的覆盖率数据
        self._cleanup_coverage_files()

        # 构建pytest命令
        cmd = [
            sys.executable, "-m", "pytest",
            "--cov=src",
            "--cov-report=term-missing",
            "--cov-report=json",
            "--cov-report=html:htmlcov",
            "-v"
        ]

        if test_pattern:
            cmd.append(test_pattern)

        try:
            print(f"📊 执行命令: {' '.join(cmd)}")
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=300
            )

            # 即使测试失败，也可能生成了覆盖率报告
            coverage_file = self.project_root / "coverage.json"
            if coverage_file.exists():
                return self._parse_coverage_report()
            else:
                print(f"❌ 覆盖率分析失败: {result.stderr}")
                return self._get_empty_report()

        except subprocess.TimeoutExpired:
            print("⏰ 覆盖率分析超时")
            return self._get_empty_report()
        except Exception as e:
            print(f"❌ 覆盖率分析异常: {e}")
            return self._get_empty_report()

    def _parse_coverage_report(self) -> CoverageReport:
        """解析覆盖率报告"""
        coverage_file = self.project_root / "coverage.json"

        if not coverage_file.exists():
            return self._get_empty_report()

        try:
            with open(coverage_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            files = data.get('files', {})
            totals = data.get('totals', {})

            file_reports = {}
            for filename, file_data in files.items():
                # 只包含src目录下的文件
                if filename.startswith('src/'):
                    file_reports[filename] = {
                        'statements': file_data.get('summary',
    {}).get('num_statements',
    0),
    
                        'missing': len(file_data.get('missing_lines', [])),
                        'coverage': file_data.get('summary',
    {}).get('percent_covered',
    0),
    
                        'missing_lines': file_data.get('missing_lines', [])
                    }

            return CoverageReport(
                total_statements=totals.get('num_statements', 0),
                missing_statements=totals.get('missing_lines', 0),
                coverage_percent=totals.get('percent_covered', 0),
                file_reports=file_reports
            )

        except Exception as e:
            print(f"❌ 解析覆盖率报告失败: {e}")
            return self._get_empty_report()

    def _get_empty_report(self) -> CoverageReport:
        """获取空的覆盖率报告"""
        return CoverageReport(
            total_statements=0,
            missing_statements=0,
            coverage_percent=0.0,
            file_reports={}
        )

    def _cleanup_coverage_files(self):
        """清理旧的覆盖率文件"""
        files_to_clean = [
            self.coverage_file,
            self.project_root / "coverage.json",
            self.coverage_dir
        ]

        for file_path in files_to_clean:
            if file_path.exists():
                if file_path.is_dir():
                    import shutil
                    shutil.rmtree(file_path)
                else:
                    file_path.unlink()

    def analyze_coverage_gaps(self, report: CoverageReport) -> List[Dict[str, Any]]:
        """分析覆盖率缺口"""
        print("🔍 分析覆盖率缺口...")

        gaps = []

        # 按覆盖率排序文件
        sorted_files = sorted(
            report.file_reports.items(),
            key=lambda x: x[1]['coverage']
        )

        for filename, file_data in sorted_files:
            if file_data['coverage'] < 50:  # 覆盖率低于50%的文件
                priority = "high" if file_data['coverage'] < 20 else "medium"

                # 分析文件类型
                if 'api' in filename:
                    module_type = "API"
                elif 'services' in filename:
                    module_type = "Service"
                elif 'domain' in filename:
                    module_type = "Domain"
                elif 'utils' in filename:
                    module_type = "Utils"
                else:
                    module_type = "Other"

                gaps.append({
                    'file': filename,
                    'coverage': file_data['coverage'],
                    'missing_lines': len(file_data['missing_lines']),
                    'priority': priority,
                    'module_type': module_type,
                    'test_suggestions': self._suggest_tests_for_file(filename,
    module_type)
                })

        return gaps

    def _suggest_tests_for_file(self, filename: str, module_type: str) -> List[str]:
        """为文件建议测试类型"""
        suggestions = []

        if module_type == "API":
            suggestions.extend([
                "创建API端点测试",
                "添加请求验证测试",
                "测试错误响应处理",
                "添加认证授权测试"
            ])
        elif module_type == "Service":
            suggestions.extend([
                "创建业务逻辑测试",
                "测试数据转换逻辑",
                "添加异常处理测试",
                "测试依赖注入"
            ])
        elif module_type == "Domain":
            suggestions.extend([
                "创建实体行为测试",
                "测试业务规则验证",
                "添加领域服务测试",
                "测试策略模式实现"
            ])
        elif module_type == "Utils":
            suggestions.extend([
                "创建工具函数测试",
                "测试边界条件",
                "添加异常情况测试",
                "测试参数验证"
            ])
        else:
            suggestions.extend([
                "创建基础单元测试",
                "测试主要功能函数",
                "添加错误处理测试"
            ])

        return suggestions

    def generate_improvement_plan(self,
    coverage_report: CoverageReport) -> Dict[str,
    Any]:
        """生成覆盖率改进计划"""
        print("📋 生成覆盖率改进计划...")

        gaps = self.analyze_coverage_gaps(coverage_report)

        # 按优先级分组
        high_priority = [g for g in gaps if g['priority'] == 'high']
        medium_priority = [g for g in gaps if g['priority'] == 'medium']

        # 计算目标覆盖率
        current_coverage = coverage_report.coverage_percent
        target_coverage = min(50, current_coverage + 20)  # 目标是50%或增加20%

        plan = {
            'current_status': {
                'total_coverage': current_coverage,
                'total_files': len(coverage_report.file_reports),
                'tested_files': len([f for f in coverage_report.file_reports.values() if f['coverage'] > 0]),
    
                'total_statements': coverage_report.total_statements,
                'covered_statements': coverage_report.covered_statements
            },
            'targets': {
                'target_coverage': target_coverage,
                'coverage_needed': target_coverage - current_coverage,
                'estimated_tests_needed': len(high_priority) * 2 + len(medium_priority)
            },
            'action_plan': {
                'immediate_actions': [
                    f"优先修复{len(high_priority)}个高优先级文件",
                    "为核心API和服务创建基础测试",
                    "建立测试模板和工具"
                ],
                'short_term_goals': [
                    f"覆盖所有{len(high_priority)}个高优先级文件",
                    "为中等优先级文件创建基础测试",
                    "建立持续集成覆盖率检查"
                ],
                'long_term_goals': [
                    "达到50%以上覆盖率",
                    "建立完整的测试体系",
                    "实现自动化测试生成"
                ]
            },
            'priority_files': high_priority[:5],  # 前5个高优先级文件
            'recommended_tools': [
                "使用create_api_tests.py生成API测试",
                "使用create_service_tests.py生成服务测试",
                "使用coverage_improvement_executor.py执行改进",
                "使用smart_quality_fixer.py修复质量问题"
            ]
        }

        return plan

    def create_targeted_tests(self,
    gaps: List[Dict[str,
    Any]],
    max_tests: int = 5) -> List[str]:
        """为高优先级缺口创建针对性测试"""
        print(f"🎯 为前{max_tests}个高优先级文件创建测试...")

        created_tests = []
        high_priority_gaps = [g for g in gaps if g['priority'] == 'high'][:max_tests]

        for gap in high_priority_gaps:
            filename = gap['file']
            module_type = gap['module_type']

            # 确定测试文件路径
            if filename.startswith('src/'):
                relative_path = filename[4:]  # 移除'src/'前缀
                test_path = self.tests_dir / "unit" / relative_path.replace('.py',
    '_test.py')
            else:
                test_path = self.tests_dir / "unit" / filename.replace('.py',
    '_test.py')

            # 确保目录存在
            test_path.parent.mkdir(parents=True, exist_ok=True)

            # 生成测试内容
            test_content = self._generate_basic_test(filename, module_type, test_path)

            try:
                with open(test_path, 'w', encoding='utf-8') as f:
                    f.write(test_content)
                created_tests.append(str(test_path))
                print(f"✅ 创建测试文件: {test_path}")
            except Exception as e:
                print(f"❌ 创建测试失败 {test_path}: {e}")

        return created_tests

    def _generate_basic_test(self,
    filename: str,
    module_type: str,
    test_path: Path) -> str:
        """生成基础测试内容"""
        module_name = Path(filename).stem

        template = f'''"""
{module_name}模块测试
自动生成的测试文件 - 需要手动完善
"""

import pytest
from unittest.mock import Mock, patch
import asyncio

# TODO: 添加正确的导入
# from {filename.replace('.py', '').replace('/', '.')} import {module_name.title()}

class Test{module_name.title()}:
    """
    {module_name}模块测试类
    模块类型: {module_type}
    """

    @pytest.fixture
    def mock_service(self):
        """模拟服务对象"""
        return Mock()

    def test_module_imports(self):
        """测试模块导入"""
        # TODO: 实现具体的模块导入测试
        assert True

    @pytest.mark.asyncio
    async def test_basic_functionality(self, mock_service):
        """测试基本功能"""
        # TODO: 实现具体的功能测试
        mock_service.process.return_value = {{"status": "success"}}
        result = await mock_service.process({{}})
        assert result["status"] == "success"

    def test_error_handling(self):
        """测试错误处理"""
        # TODO: 实现错误处理测试
        with pytest.raises(Exception):
            raise Exception("Test exception")

    # TODO: 根据模块功能添加更多测试用例
    # def test_specific_feature(self):
    #     """测试特定功能"""
    #     pass

    # @pytest.mark.integration
    # def test_integration_scenario(self):
    #     """测试集成场景"""
    #     pass

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
'''

        return template


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="覆盖率测量和优化工具")
    parser.add_argument("--test-pattern", help="测试模式匹配")
    parser.add_argument("--create-tests", action="store_true", help="创建针对性测试")
    parser.add_argument("--max-tests", type=int, default=5, help="最大创建测试数量")
    parser.add_argument("--analyze-only", action="store_true", help="仅分析不创建测试")

    args = parser.parse_args()

    optimizer = CoverageOptimizer()

    print("🚀 启动覆盖率测量和优化工具")
    print("=" * 50)

    # 1. 运行覆盖率分析
    coverage_report = optimizer.run_coverage_analysis(args.test_pattern)

    print(f"\n📊 当前覆盖率状态:")
    print(f"   总覆盖率: {coverage_report.coverage_percent:.2f}%")
    print(f"   总语句数: {coverage_report.total_statements}")
    print(f"   已覆盖语句: {coverage_report.covered_statements}")
    print(f"   测试文件数: {len(coverage_report.file_reports)}")

    if coverage_report.coverage_percent == 0:
        print("\n⚠️  当前无覆盖率，需要从零开始建立测试体系")
        return

    # 2. 生成改进计划
    improvement_plan = optimizer.generate_improvement_plan(coverage_report)

    print(f"\n📋 改进计划:")
    print(f"   当前覆盖率: {improvement_plan['current_status']['total_coverage']:.2f}%")
    print(f"   目标覆盖率: {improvement_plan['targets']['target_coverage']:.2f}%")
    print(f"   需要提升: {improvement_plan['targets']['coverage_needed']:.2f}%")
    print(f"   预计需要测试: {improvement_plan['targets']['estimated_tests_needed']}个")

    # 3. 分析覆盖率缺口
    gaps = optimizer.analyze_coverage_gaps(coverage_report)
    high_priority_count = len([g for g in gaps if g['priority'] == 'high'])
    medium_priority_count = len([g for g in gaps if g['priority'] == 'medium'])

    print(f"\n🎯 覆盖率缺口分析:")
    print(f"   高优先级文件: {high_priority_count}个")
    print(f"   中等优先级文件: {medium_priority_count}个")

    if improvement_plan['priority_files']:
        print(f"\n🔥 优先处理文件:")
        for i, file_info in enumerate(improvement_plan['priority_files'][:3], 1):
            print(f"   {i}. {file_info['file']} (覆盖率: {file_info['coverage']:.1f}%)")

    # 4. 创建针对性测试（如果需要）
    if not args.analyze_only and args.create_tests and gaps:
        created_tests = optimizer.create_targeted_tests(gaps, args.max_tests)
        print(f"\n✅ 创建了 {len(created_tests)} 个测试文件:")
        for test_path in created_tests:
            print(f"   📝 {test_path}")

    print(f"\n💡 推荐下一步行动:")
    for action in improvement_plan['action_plan']['immediate_actions'][:3]:
        print(f"   • {action}")

    print(f"\n🛠️  推荐工具:")
    for tool in improvement_plan['recommended_tools'][:3]:
        print(f"   • {tool}")

    print(f"\n📊 详细报告已生成:")
    print(f"   HTML报告: {optimizer.coverage_dir}/index.html")
    print(f"   JSON报告: {optimizer.project_root}/coverage.json")


if __name__ == "__main__":
    main()