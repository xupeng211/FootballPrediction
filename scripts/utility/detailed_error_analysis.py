#!/usr/bin/env python3
"""
详细错误分析脚本
收集更多失败测试的详细信息
"""

import subprocess
import json
import re
from collections import defaultdict

def get_sample_error_details():
    """获取样本测试的详细错误信息"""
    sample_tests = [
        # API端点错误
        "tests/api/test_endpoints.py::TestHealthEndpoints::test_health_check_system_info",
        "tests/api/test_endpoints.py::TestPredictionEndpoints::test_get_predictions_list",

        # 缓存错误
        "tests/integration/test_cache_simple.py::TestSimplifiedCacheOperations::test_basic_cache_operations",
        "tests/integration/test_cache_mock.py::TestMockCacheOperations::test_basic_cache_operations",

        # 认证错误
        "tests/unit/api/test_auth_isolated.py::TestAuthService::test_password_hashing",
        "tests/unit/api/test_auth_simple.py::TestUserAuthModel::test_user_auth_creation",

        # 集成测试错误
        "tests/integration/test_basic_pytest.py::TestBasicFunctionality::test_module_instantiation",
        "tests/integration/test_api_domain_integration.py::TestDomainEventIntegration::test_prediction_created_event",

        # 性能测试错误
        "tests/integration/test_cache_integration.py::TestCachePerformance::test_cache_performance",
    ]

    error_details = []

    for test in sample_tests:
        print(f"🔍 分析: {test}")
        try:
            # 运行测试并捕获错误
            result = subprocess.run([
                'python', '-m', 'pytest', test,
                '-v', '--tb=short', '--no-header', '-q'
            ], capture_output=True, text=True, timeout=30)

            if result.returncode != 0:
                error_output = result.stderr + result.stdout

                # 提取关键错误信息
                error_type = extract_error_type(error_output)
                error_message = extract_error_message(error_output)

                error_details.append({
                    'test': test,
                    'error_type': error_type,
                    'error_message': error_message,
                    'full_output': error_output
                })
            else:
                print(f"  ✅ 测试通过: {test}")

        except subprocess.TimeoutExpired:
            error_details.append({
                'test': test,
                'error_type': 'TIMEOUT',
                'error_message': 'Test execution timeout',
                'full_output': ''
            })
        except Exception as e:
            error_details.append({
                'test': test,
                'error_type': 'ANALYSIS_ERROR',
                'error_message': str(e),
                'full_output': ''
            })

    return error_details

def extract_error_type(output):
    """从错误输出中提取错误类型"""
    patterns = [
        (r'AttributeError:\s*(.+)', 'AttributeError'),
        (r'ImportError:\s*(.+)', 'ImportError'),
        (r'TypeError:\s*(.+)', 'TypeError'),
        (r'ValueError:\s*(.+)', 'ValueError'),
        (r'AssertionError:\s*(.+)', 'AssertionError'),
        (r'RuntimeError:\s*(.+)', 'RuntimeError'),
        (r'DeprecationWarning:\s*(.+)', 'DeprecationWarning'),
        (r'asyncio\.errors\.(.+)', 'AsyncError'),
        (r'sqlalchemy\.(.+)', 'SQLAlchemyError'),
        (r'fastapi\.(.+)', 'FastAPIError'),
        (r'redis\.(.+)', 'RedisError'),
    ]

    for pattern, error_type in patterns:
        if re.search(pattern, output, re.IGNORECASE):
            return error_type

    # 根据错误消息关键词推断
    if 'coroutine object has no attribute' in output:
        return 'AsyncDecoratorError'
    elif 'backend' in output.lower() and 'bcrypt' in output.lower():
        return 'BcryptBackendError'
    elif '500' in output and 'internal server error' in output.lower():
        return 'HTTP500Error'
    elif 'duplicate' in output.lower():
        return 'DuplicateError'
    elif 'validation' in output.lower():
        return 'ValidationError'
    elif 'dependency' in output.lower():
        return 'DependencyError'
    else:
        return 'UnknownError'

def extract_error_message(output):
    """提取关键错误消息"""
    lines = output.split('\n')
    error_lines = []

    for line in lines:
        # 跳过pytest的header和其他非错误信息
        if any(keyword in line for keyword in [
            'test session starts', 'platform', 'plugins', 'cachedir',
            'collecting', 'collected', '=============================',
            'FAILED', 'PASSED', 'SKIPPED'
        ]):
            continue

        # 获取包含错误信息的行
        if any(keyword in line for keyword in [
            'Error', 'Exception', 'Failed', 'AssertionError',
            'AttributeError', 'ImportError', 'TypeError', 'ValueError'
        ]):
            error_lines.append(line.strip())

    # 返回最相关的错误消息
    if error_lines:
        return error_lines[0] if len(error_lines) == 1 else ' | '.join(error_lines[:2])
    else:
        return 'No specific error message extracted'

def analyze_error_patterns(error_details):
    """分析错误模式"""
    error_type_counts = defaultdict(int)
    pattern_counts = defaultdict(int)

    for detail in error_details:
        error_type_counts[detail['error_type']] += 1

        # 分析错误模式
        message = detail['error_message'].lower()
        if 'coroutine' in message and 'attribute' in message:
            pattern_counts['AsyncDecoratorIssue'] += 1
        elif 'backend' in message and 'bcrypt' in message:
            pattern_counts['BcryptBackendIssue'] += 1
        elif '500' in message or 'internal server error' in message:
            pattern_counts['HTTP500Issue'] += 1
        elif 'dependency' in message:
            pattern_counts['DependencyIssue'] += 1
        elif 'validation' in message:
            pattern_counts['ValidationIssue'] += 1
        else:
            pattern_counts['GeneralIssue'] += 1

    return dict(error_type_counts), dict(pattern_counts)

def enhance_triage_report():
    """增强分诊报告"""
    print("🔍 开始详细错误分析...")

    # 获取详细错误信息
    error_details = get_sample_error_details()
    print(f"✅ 获取了 {len(error_details)} 个样本错误详情")

    # 分析错误模式
    error_type_counts, pattern_counts = analyze_error_patterns(error_details)

    print("\n📊 错误类型分析:")
    for error_type, count in sorted(error_type_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  {error_type}: {count}")

    print("\n🎯 错误模式分析:")
    for pattern, count in sorted(pattern_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  {pattern}: {count}")

    # 读取现有报告
    with open('P8.1_Triage_Report.md', 'r', encoding='utf-8') as f:
        report_content = f.read()

    # 在报告末尾添加详细错误分析
    detailed_section = f"""

## 🔍 详细错误分析

### 样本测试错误分析

分析了 {len(error_details)} 个代表性失败的测试，发现以下关键错误模式:

#### 主要错误类型
"""
    for error_type, count in sorted(error_type_counts.items(), key=lambda x: x[1], reverse=True):
        percentage = (count / len(error_details)) * 100
        detailed_section += f"- **{error_type}**: {count} 个测试 ({percentage:.1f}%)\n"

    detailed_section += "\n#### 错误模式分析\n"
    for pattern, count in sorted(pattern_counts.items(), key=lambda x: x[1], reverse=True):
        percentage = (count / len(error_details)) * 100
        detailed_section += f"- **{pattern}**: {count} 个测试 ({percentage:.1f}%)\n"

    detailed_section += "\n#### 具体错误示例\n"

    for detail in error_details[:5]:  # 显示前5个错误示例
        detailed_section += f"""
**测试**: `{detail['test']}`
- **错误类型**: {detail['error_type']}
- **错误消息**: {detail['error_message']}
"""

    # 识别的核心问题和解决方案
    detailed_section += """
### 🔧 核心问题识别

基于详细分析，识别出以下核心问题:

#### 1. 异步装饰器问题 (AsyncDecoratorIssue)
- **症状**: `AttributeError: 'coroutine' object has no attribute 'set'`
- **影响**: 大量缓存相关测试失败
- **解决方案**: 修复异步装饰器实现，确保正确处理协程对象

#### 2. bcrypt后端问题 (BcryptBackendIssue)
- **症状**: bcrypt库后端缺失或配置错误
- **影响**: 认证系统测试完全失败
- **解决方案**: 安装并配置bcrypt后端 `pip install bcrypt`

#### 3. HTTP 500错误 (HTTP500Issue)
- **症状**: API端点返回500内部服务器错误
- **影响**: API测试大量失败
- **解决方案**: 检查API端点实现，修复服务器内部错误

### 🎯 精准修复建议

#### 立即修复 (P8.2阶段)
1. **安装bcrypt后端**:
   ```bash
   pip install bcrypt
   ```

2. **修复异步装饰器**:
   - 检查 `src/cache/decorators.py` 中的异步实现
   - 确保装饰器正确处理协程对象

3. **修复API端点**:
   - 重点检查健康检查端点
   - 修复预测相关API的响应问题

#### 系统性修复 (P8.3阶段)
1. **依赖注入修复**: 解决模块间依赖问题
2. **集成测试优化**: 改进测试隔离和mock策略
3. **配置管理**: 统一环境配置和依赖管理

"""

    # 将详细分析添加到报告中
    updated_report = report_content + detailed_section

    # 保存更新后的报告
    with open('P8.1_Triage_Report.md', 'w', encoding='utf-8') as f:
        f.write(updated_report)

    print("✅ 详细错误分析已添加到报告中")

    return error_details

def main():
    """主函数"""
    print("🚀 启动详细错误分析...")

    error_details = enhance_triage_report()

    print(f"\n📋 分析完成:")
    print(f"- 分析样本数: {len(error_details)}")
    print(f"- 报告已更新: P8.1_Triage_Report.md")

if __name__ == "__main__":
    main()
