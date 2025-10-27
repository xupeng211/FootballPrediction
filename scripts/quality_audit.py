#!/usr/bin/env python3
"""
代码质量定期审计工具
自动化质量检查和报告生成
"""

import subprocess
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

class QualityAuditor:
    """代码质量审计器"""

    def __init__(self, project_root: str = "/home/user/projects/FootballPrediction"):
        self.project_root = Path(project_root)
        self.report_dir = self.project_root / "reports" / "quality"
        self.report_dir.mkdir(parents=True, exist_ok=True)
        self.timestamp = datetime.now().isoformat()

    def run_mypy_analysis(self) -> Dict[str, Any]:
        """运行MyPy类型检查分析"""
        try:
            result = subprocess.run([
                'mypy', 'src/', '--json-report', str(self.report_dir / 'mypy')
            ],
            cwd=self.project_root,
            capture_output=True,
            text=True
            )

            # 尝试读取MyPy报告
            mypy_report_path = self.report_dir / 'mypy' / 'index.json'
            if mypy_report_path.exists():
                with open(mypy_report_path, 'r', encoding='utf-8') as f:
                    mypy_data = json.load(f)
                    return {
                        'status': 'success',
                        'total_errors': len(mypy_data.get('files', {})),
                        'errors_by_file': mypy_data.get('files', {}),
                        'summary': mypy_data.get('summary', {})
                    }
            else:
                return {
                    'status': 'failed',
                    'error': result.stderr,
                    'total_errors': 0
                }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'total_errors': 0
            }

    def run_ruff_analysis(self) -> Dict[str, Any]:
        """运行Ruff代码质量分析"""
        try:
            result = subprocess.run([
                'ruff', 'check', 'src/', '--format=json', '--output-file',
                str(self.report_dir / 'ruff.json')
            ],
            cwd=self.project_root,
            capture_output=True,
            text=True
            )

            ruff_report_path = self.report_dir / 'ruff.json'
            if ruff_report_path.exists():
                with open(ruff_report_path, 'r', encoding='utf-8') as f:
                    ruff_data = json.load(f)
                    return {
                        'status': 'success',
                        'total_issues': len(ruff_data),
                        'issues': ruff_data,
                        'error_count': len([i for i in ruff_data if i.get('fix', {}).get('applicability') == 'unspecified'])
                    }
            else:
                return {
                    'status': 'failed',
                    'error': result.stderr,
                    'total_issues': 0
                }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'total_issues': 0
            }

    def run_test_coverage_analysis(self) -> Dict[str, Any]:
        """运行测试覆盖率分析"""
        try:
            result = subprocess.run([
                'python', '-m', 'pytest',
                '--cov=src',
                '--cov-report=json:' + str(self.report_dir / 'coverage.json'),
                '--cov-report=term-missing',
                'tests/unit/'
            ],
            cwd=self.project_root,
            capture_output=True,
            text=True
            )

            coverage_report_path = self.report_dir / 'coverage.json'
            if coverage_report_path.exists():
                with open(coverage_report_path, 'r', encoding='utf-8') as f:
                    coverage_data = json.load(f)
                    total_coverage = coverage_data.get('totals', {}).get('percent_covered', 0)

                    return {
                        'status': 'success',
                        'total_coverage': total_coverage,
                        'coverage_by_file': coverage_data.get('files', {}),
                        'summary': coverage_data.get('totals', {}),
                        'meets_threshold': total_coverage >= 80.0
                    }
            else:
                return {
                    'status': 'failed',
                    'error': result.stderr,
                    'total_coverage': 0
                }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'total_coverage': 0
            }

    def analyze_code_complexity(self) -> Dict[str, Any]:
        """分析代码复杂度"""
        try:
            # 使用radon分析复杂度
            result = subprocess.run([
                'radon', 'cc', 'src/', '--json'
            ],
            cwd=self.project_root,
            capture_output=True,
            text=True
            )

            if result.returncode == 0:
                complexity_data = json.loads(result.stdout)

                # 计算平均复杂度
                all_scores = []
                for file_data in complexity_data.values():
                    for func_data in file_data:
                        all_scores.append(func_data.get('complexity', 0))

                avg_complexity = sum(all_scores) / len(all_scores) if all_scores else 0
                high_complexity_funcs = [
                    f for f_data in complexity_data.values()
                    for f in f_data
                    if f.get('complexity', 0) > 10
                ]

                return {
                    'status': 'success',
                    'average_complexity': avg_complexity,
                    'total_functions': len(all_scores),
                    'high_complexity_count': len(high_complexity_funcs),
                    'high_complexity_functions': high_complexity_funcs[:10],  # 只显示前10个
                    'complexity_by_file': complexity_data
                }
            else:
                return {
                    'status': 'failed',
                    'error': result.stderr,
                    'average_complexity': 0
                }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'average_complexity': 0
            }

    def check_security_issues(self) -> Dict[str, Any]:
        """检查安全问题"""
        try:
            # 使用bandit进行安全检查
            result = subprocess.run([
                'bandit', '-r', 'src/', '-f', 'json', '-o',
                str(self.report_dir / 'security.json')
            ],
            cwd=self.project_root,
            capture_output=True,
            text=True
            )

            security_report_path = self.report_dir / 'security.json'
            if security_report_path.exists():
                with open(security_report_path, 'r', encoding='utf-8') as f:
                    security_data = json.load(f)

                    high_severity = len([r for r in security_data.get('results', [])
                                       if r.get('issue_severity') == 'HIGH'])
                    medium_severity = len([r for r in security_data.get('results', [])
                                         if r.get('issue_severity') == 'MEDIUM'])
                    low_severity = len([r for r in security_data.get('results', [])
                                      if r.get('issue_severity') == 'LOW'])

                    return {
                        'status': 'success',
                        'total_issues': len(security_data.get('results', [])),
                        'high_severity': high_severity,
                        'medium_severity': medium_severity,
                        'low_severity': low_severity,
                        'has_critical_issues': high_severity > 0,
                        'issues': security_data.get('results', [])
                    }
            else:
                return {
                    'status': 'failed',
                    'error': result.stderr,
                    'total_issues': 0
                }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'total_issues': 0
            }

    def generate_quality_score(self, analysis_results: Dict[str, Any]) -> Dict[str, Any]:
        """生成质量评分"""
        scores = {}

        # 类型安全评分 (40%)
        mypy_result = analysis_results.get('mypy', {})
        type_errors = mypy_result.get('total_errors', 0)
        type_score = max(0, 100 - type_errors * 0.1)  # 每个错误扣0.1分
        scores['type_safety'] = type_score

        # 代码质量评分 (25%)
        ruff_result = analysis_results.get('ruff', {})
        code_issues = ruff_result.get('total_issues', 0)
        code_score = max(0, 100 - code_issues * 0.5)  # 每个问题扣0.5分
        scores['code_quality'] = code_score

        # 测试覆盖率评分 (20%)
        coverage_result = analysis_results.get('coverage', {})
        coverage = coverage_result.get('total_coverage', 0)
        scores['test_coverage'] = coverage

        # 代码复杂度评分 (10%)
        complexity_result = analysis_results.get('complexity', {})
        avg_complexity = complexity_result.get('average_complexity', 0)
        complexity_score = max(0, 100 - avg_complexity * 5)  # 平均复杂度每增加1扣5分
        scores['complexity'] = complexity_score

        # 安全性评分 (5%)
        security_result = analysis_results.get('security', {})
        security_issues = security_result.get('total_issues', 0)
        high_severity = security_result.get('high_severity', 0)
        security_score = max(0, 100 - security_issues * 2 - high_severity * 10)
        scores['security'] = security_score

        # 计算加权总分
        weights = {
            'type_safety': 0.4,
            'code_quality': 0.25,
            'test_coverage': 0.2,
            'complexity': 0.1,
            'security': 0.05
        }

        total_score = sum(scores[category] * weight for category, weight in weights.items())

        # 确定等级
        if total_score >= 90:
            grade = 'A+'
        elif total_score >= 80:
            grade = 'A'
        elif total_score >= 70:
            grade = 'B'
        elif total_score >= 60:
            grade = 'C'
        else:
            grade = 'D'

        return {
            'total_score': round(total_score, 2),
            'grade': grade,
            'category_scores': scores,
            'weights': weights,
            'recommendations': self._generate_recommendations(scores, analysis_results)
        }

    def _generate_recommendations(self, scores: Dict[str, Any], results: Dict[str, Any]) -> List[str]:
        """生成改进建议"""
        recommendations = []

        if scores['type_safety'] < 80:
            recommendations.append("增加类型注解覆盖率，修复MyPy错误")

        if scores['code_quality'] < 80:
            ruff_issues = results.get('ruff', {}).get('total_issues', 0)
            recommendations.append(f"修复Ruff发现的{ruff_issues}个代码问题")

        if scores['test_coverage'] < 80:
            coverage = results.get('coverage', {}).get('total_coverage', 0)
            recommendations.append(f"提高测试覆盖率至80%以上（当前{coverage:.1f}%）")

        if scores['complexity'] < 70:
            avg_complexity = results.get('complexity', {}).get('average_complexity', 0)
            recommendations.append(f"降低代码复杂度（当前平均复杂度{avg_complexity:.1f}）")

        if scores['security'] < 80:
            high_issues = results.get('security', {}).get('high_severity', 0)
            if high_issues > 0:
                recommendations.append(f"优先修复{high_issues}个高危安全问题")

        return recommendations

    def run_full_audit(self) -> Dict[str, Any]:
        """运行完整的质量审计"""
        print("🔍 开始代码质量审计...")

        # 运行各项分析
        analysis_results = {
            'timestamp': self.timestamp,
            'mypy': self.run_mypy_analysis(),
            'ruff': self.run_ruff_analysis(),
            'coverage': self.run_test_coverage_analysis(),
            'complexity': self.analyze_code_complexity(),
            'security': self.check_security_issues()
        }

        # 生成质量评分
        quality_score = self.generate_quality_score(analysis_results)
        analysis_results['quality_score'] = quality_score

        # 保存详细报告
        report_path = self.report_dir / f'quality_audit_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(analysis_results, f, indent=2, ensure_ascii=False)

        # 生成简明报告
        self._generate_summary_report(analysis_results)

        print(f"✅ 审计完成！详细报告已保存至: {report_path}")
        return analysis_results

    def _generate_summary_report(self, results: Dict[str, Any]) -> None:
        """生成简明报告"""
        score = results['quality_score']

        summary = f"""
# 代码质量审计报告

**时间**: {results['timestamp']}
**总体评分**: {score['total_score']}/100 ({score['grade']}级)

## 分项评分

- **类型安全**: {score['category_scores']['type_safety']:.1f}/100 (权重40%)
- **代码质量**: {score['category_scores']['code_quality']:.1f}/100 (权重25%)
- **测试覆盖率**: {score['category_scores']['test_coverage']:.1f}/100 (权重20%)
- **代码复杂度**: {score['category_scores']['complexity']:.1f}/100 (权重10%)
- **安全性**: {score['category_scores']['security']:.1f}/100 (权重5%)

## 关键指标

- **MyPy错误数**: {results['mypy'].get('total_errors', 0)}
- **Ruff问题数**: {results['ruff'].get('total_issues', 0)}
- **测试覆盖率**: {results['coverage'].get('total_coverage', 0):.1f}%
- **平均复杂度**: {results['complexity'].get('average_complexity', 0):.1f}
- **安全问题**: {results['security'].get('total_issues', 0)}个 ({results['security'].get('high_severity', 0)}个高危)

## 改进建议

{chr(10).join(f"- {rec}" for rec in score['recommendations'])}
"""

        summary_path = self.report_dir / 'latest_summary.md'
        with open(summary_path, 'w', encoding='utf-8') as f:
            f.write(summary)

def main():
    """主函数"""
    auditor = QualityAuditor()
    results = auditor.run_full_audit()

    # 输出关键信息
    score = results['quality_score']
    print(f"\n📊 质量评分: {score['total_score']}/100 ({score['grade']}级)")

    if score['recommendations']:
        print("\n💡 改进建议:")
        for rec in score['recommendations']:
            print(f"   • {rec}")

    # 如果评分较低，建议采取行动
    if score['total_score'] < 70:
        print("\n⚠️  质量评分偏低，建议立即采取改进措施")
    elif score['total_score'] < 85:
        print("\n📈 质量良好，但仍有改进空间")
    else:
        print("\n🎉 质量优秀，继续保持！")

if __name__ == '__main__':
    main()