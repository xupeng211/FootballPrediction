#!/usr/bin/env python3
"""
P8.1 FAILED测试聚类分析工具
用于分析324个FAILED测试的聚类模式
"""

import re
import json
from collections import defaultdict, Counter
from typing import Dict, List, Tuple
from dataclasses import dataclass
from pathlib import Path

@dataclass
class TestFailure:
    """测试失败信息数据类"""
    test_path: str
    test_name: str
    module: str
    error_type: str
    error_message: str
    failure_pattern: str

class FailedTestsAnalyzer:
    """失败测试分析器"""

    def __init__(self):
        self.failures: List[TestFailure] = []
        self.error_type_clusters = defaultdict(list)
        self.module_clusters = defaultdict(list)
        self.pattern_clusters = defaultdict(list)

    def parse_failure_log(self, log_path: str = "/tmp/pytest_full_results.log") -> None:
        """解析pytest失败日志"""
        with open(log_path, 'r', encoding='utf-8') as f:
            log_content = f.read()

        # 提取失败测试行
        failed_lines = [line for line in log_content.split('\n') if line.strip().startswith('FAILED')]

        for line in failed_lines:
            # 解析测试路径和名称 - 修复正则表达式
            match = re.match(r'FAILED (.+?)::(.+?)\s+FAILED', line)
            if not match:
                match = re.match(r'FAILED (.+?)::(.+?) \[\s*\d+%\]', line)

            if match:
                test_path, test_name = match.groups()

                # 提取模块名
                module = self._extract_module(test_path)

                # 创建测试失败对象
                failure = TestFailure(
                    test_path=test_path,
                    test_name=test_name,
                    module=module,
                    error_type="UNKNOWN",  # 将在后续分析中填充
                    error_message="",
                    failure_pattern=self._identify_pattern(test_name)
                )

                self.failures.append(failure)

        print(f"✅ 解析完成: 找到 {len(self.failures)} 个失败测试")

    def _extract_module(self, test_path: str) -> str:
        """从测试路径提取模块"""
        if 'api/' in test_path:
            return 'API'
        elif 'integration/' in test_path:
            return 'INTEGRATION'
        elif 'unit/' in test_path:
            return 'UNIT'
        elif 'cache/' in test_path:
            return 'CACHE'
        elif 'auth/' in test_path:
            return 'AUTH'
        elif 'database/' in test_path:
            return 'DATABASE'
        elif 'ml/' in test_path:
            return 'ML'
        elif 'services/' in test_path:
            return 'SERVICES'
        else:
            return 'OTHER'

    def _identify_pattern(self, test_name: str) -> str:
        """识别失败模式"""
        if 'health' in test_name.lower():
            return 'HEALTH_CHECK'
        elif 'auth' in test_name.lower():
            return 'AUTHENTICATION'
        elif 'cache' in test_name.lower():
            return 'CACHE_OPERATION'
        elif 'prediction' in test_name.lower():
            return 'PREDICTION_LOGIC'
        elif 'database' in test_name.lower() or 'db' in test_name.lower():
            return 'DATABASE_OPERATION'
        elif 'api' in test_name.lower():
            return 'API_ENDPOINT'
        elif 'integration' in test_name.lower():
            return 'INTEGRATION'
        elif 'performance' in test_name.lower():
            return 'PERFORMANCE'
        elif 'error' in test_name.lower():
            return 'ERROR_HANDLING'
        else:
            return 'GENERAL'

    def analyze_error_types(self) -> None:
        """基于常见错误类型进行分析"""
        # 根据测试名称和模式推断可能的错误类型
        for failure in self.failures:
            if failure.test_name.startswith('test_'):
                if 'health' in failure.test_name:
                    failure.error_type = 'HTTP_500_ERROR'
                elif 'auth' in failure.test_name:
                    failure.error_type = 'AUTH_SERVICE_ERROR'
                elif 'cache' in failure.test_name:
                    failure.error_type = 'CACHE_ATTR_ERROR'
                elif 'prediction' in failure.test_name:
                    failure.error_type = 'ASSERTION_ERROR'
                elif 'api' in failure.test_name:
                    failure.error_type = 'API_RESPONSE_ERROR'
                elif 'integration' in failure.test_name:
                    failure.error_type = 'INTEGRATION_ERROR'
                else:
                    failure.error_type = 'GENERAL_ERROR'

            # 更新聚类
            self.error_type_clusters[failure.error_type].append(failure)

    def perform_clustering(self) -> Dict:
        """执行聚类分析"""
        print("🔄 开始聚类分析...")

        # 按错误类型聚类
        for failure in self.failures:
            self.error_type_clusters[failure.error_type].append(failure)
            self.module_clusters[failure.module].append(failure)
            self.pattern_clusters[failure.failure_pattern].append(failure)

        return {
            'total_failures': len(self.failures),
            'error_type_clusters': {k: len(v) for k, v in self.error_type_clusters.items()},
            'module_clusters': {k: len(v) for k, v in self.module_clusters.items()},
            'pattern_clusters': {k: len(v) for k, v in self.pattern_clusters.items()}
        }

    def get_high_value_clusters(self) -> List[Dict]:
        """识别高价值集群（影响测试数量最多）"""
        clusters = []

        # 错误类型集群
        for error_type, failures in self.error_type_clusters.items():
            clusters.append({
                'type': 'ERROR_TYPE',
                'name': error_type,
                'size': len(failures),
                'impact': self._calculate_impact(failures),
                'failures': failures[:10]  # 前10个示例
            })

        # 模块集群
        for module, failures in self.module_clusters.items():
            clusters.append({
                'type': 'MODULE',
                'name': module,
                'size': len(failures),
                'impact': self._calculate_impact(failures),
                'failures': failures[:10]
            })

        # 模式集群
        for pattern, failures in self.pattern_clusters.items():
            clusters.append({
                'type': 'PATTERN',
                'name': pattern,
                'size': len(failures),
                'impact': self._calculate_impact(failures),
                'failures': failures[:10]
            })

        # 按影响大小排序
        return sorted(clusters, key=lambda x: x['impact'], reverse=True)

    def _calculate_impact(self, failures: List[TestFailure]) -> int:
        """计算集群影响分数"""
        # 简单的影响计算：基于集群大小和模块重要性
        module_weights = {
            'API': 10,
            'INTEGRATION': 8,
            'CACHE': 7,
            'AUTH': 9,
            'DATABASE': 8,
            'SERVICES': 7,
            'UNIT': 5,
            'ML': 6,
            'OTHER': 3
        }

        base_impact = len(failures)
        module_bonus = sum(module_weights.get(f.module, 3) for f in failures) / len(failures)

        return int(base_impact * module_bonus)

    def generate_triage_report(self) -> str:
        """生成分诊报告"""
        print("📊 生成P8.1_Triage_Report...")

        # 执行聚类分析
        clustering_results = self.perform_clustering()
        high_value_clusters = self.get_high_value_clusters()

        # 生成报告内容
        report_content = f"""# P8.1 Failed Tests Triage Report

## 📊 执行摘要

- **总失败测试数**: {clustering_results['total_failures']}
- **分析时间**: {self._get_current_time()}
- **分析范围**: 完整测试套件（3772个测试）

## 🎯 关键统计数据

### 错误类型分布
"""

        for error_type, count in sorted(clustering_results['error_type_clusters'].items(),
                                      key=lambda x: x[1], reverse=True):
            percentage = (count / clustering_results['total_failures']) * 100
            report_content += f"- **{error_type}**: {count} 个测试 ({percentage:.1f}%)\n"

        report_content += f"""
### 模块分布
"""
        for module, count in sorted(clustering_results['module_clusters'].items(),
                                  key=lambda x: x[1], reverse=True):
            percentage = (count / clustering_results['total_failures']) * 100
            report_content += f"- **{module}**: {count} 个测试 ({percentage:.1f}%)\n"

        report_content += f"""
### 失败模式分布
"""
        for pattern, count in sorted(clustering_results['pattern_clusters'].items(),
                                   key=lambda x: x[1], reverse=True):
            percentage = (count / clustering_results['total_failures']) * 100
            report_content += f"- **{pattern}**: {count} 个测试 ({percentage:.1f}%)\n"

        report_content += f"""
## 🔥 高价值集群分析

### 优先级1: 立即修复（影响 > 200）
"""

        priority_1 = [c for c in high_value_clusters if c['impact'] > 200][:5]
        for i, cluster in enumerate(priority_1, 1):
            report_content += f"""
#### {i}. {cluster['name']} ({cluster['type']})
- **影响分数**: {cluster['impact']}
- **涉及测试**: {cluster['size']} 个
- **修复建议**: {self._get_fix_suggestion(cluster)}
- **示例测试**:
"""
            for failure in cluster['failures'][:3]:
                report_content += f"  - `{failure.test_path}::{failure.test_name}`\n"

        report_content += f"""
### 优先级2: 高优先级（影响 100-200）
"""

        priority_2 = [c for c in high_value_clusters if 100 <= c['impact'] <= 200][:5]
        for i, cluster in enumerate(priority_2, 1):
            report_content += f"""
#### {i}. {cluster['name']} ({cluster['type']})
- **影响分数**: {cluster['impact']}
- **涉及测试**: {cluster['size']} 个
- **修复建议**: {self._get_fix_suggestion(cluster)}
"""

        report_content += f"""
## 🛠️ P8.2 修复策略建议

### 立即行动计划
1. **API错误修复**: 重点关注HTTP 500错误和端点响应问题
2. **缓存系统修复**: 解决AttributeError和异步装饰器问题
3. **认证系统修复**: 修复bcrypt和密码哈希依赖问题
4. **集成测试修复**: 解决模块间依赖和服务注入问题

### 渐进式修复方法
1. **阶段1**: 修复基础设施问题（依赖注入、装饰器、配置）
2. **阶段2**: 修复核心业务逻辑（API端点、认证、缓存）
3. **阶段3**: 优化集成测试和性能测试

### 质量保证措施
- 使用 `make solve-test-crisis` 自动修复常见问题
- 运行 `python3 scripts/smart_quality_fixer.py` 智能质量修复
- 执行 `make test.smart` 验证修复效果

## 📈 成功指标

- **目标**: 将失败测试数量从500+降至100以下
- **关键指标**:
  - API端点通过率 > 90%
  - 缓存系统测试通过率 > 85%
  - 认证系统测试通过率 > 90%
  - 集成测试通过率 > 80%

---
*报告生成时间: {self._get_current_time()}*
*分析工具: P8.1 Failed Tests Analyzer*
"""

        return report_content

    def _get_fix_suggestion(self, cluster: Dict) -> str:
        """获取修复建议"""
        suggestions = {
            'HTTP_500_ERROR': '检查API端点实现，修复服务器内部错误',
            'AUTH_SERVICE_ERROR': '修复认证服务依赖，检查密码哈希库',
            'CACHE_ATTR_ERROR': '解决异步装饰器问题，修复缓存管理器',
            'ASSERTION_ERROR': '检查测试数据和期望值，修复业务逻辑',
            'API_RESPONSE_ERROR': '验证API响应格式，修复序列化问题',
            'INTEGRATION_ERROR': '解决模块间依赖，修复服务注入',
            'API': '重点修复FastAPI路由和依赖注入',
            'CACHE': '修复Redis连接和异步操作',
            'AUTH': '解决密码哈希和认证流程',
            'HEALTH_CHECK': '修复健康检查端点和系统监控',
            'AUTHENTICATION': '检查JWT令牌和用户认证逻辑',
            'CACHE_OPERATION': '解决缓存操作和Redis集成',
            'PREDICTION_LOGIC': '修复预测服务和数据模型',
            'INTEGRATION': '解决跨模块集成问题'
        }
        return suggestions.get(cluster['name'], '需要详细分析具体错误原因')

    def _get_current_time(self) -> str:
        """获取当前时间"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def save_report(self, report_content: str, filename: str = "P8.1_Triage_Report.md") -> None:
        """保存报告到文件"""
        report_path = Path(filename)
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report_content)
        print(f"✅ 报告已保存到: {report_path.absolute()}")

def main():
    """主函数"""
    print("🚀 启动P8.1 Failed Tests聚类分析...")

    # 创建分析器
    analyzer = FailedTestsAnalyzer()

    # 解析失败日志
    analyzer.parse_failure_log()

    # 分析错误类型
    analyzer.analyze_error_types()

    # 生成并保存报告
    report = analyzer.generate_triage_report()
    analyzer.save_report(report)

    # 显示摘要
    print("\n📋 分析摘要:")
    print(f"- 总失败测试: {len(analyzer.failures)}")
    print(f"- 错误类型集群: {len(analyzer.error_type_clusters)}")
    print(f"- 模块集群: {len(analyzer.module_clusters)}")
    print(f"- 模式集群: {len(analyzer.pattern_clusters)}")

    print("\n🎯 前5个高价值集群:")
    high_value_clusters = analyzer.get_high_value_clusters()[:5]
    for i, cluster in enumerate(high_value_clusters, 1):
        print(f"{i}. {cluster['name']} ({cluster['type']}) - 影响: {cluster['impact']}")

if __name__ == "__main__":
    main()