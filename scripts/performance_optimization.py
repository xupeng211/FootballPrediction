#!/usr/bin/env python3
"""
性能优化脚本
Performance Optimization Script

优化应用程序性能
"""

import cProfile
import pstats
import time
from io import StringIO
from pathlib import Path


class PerformanceProfiler:
    """性能分析器"""

    def __init__(self):
        self.results = {}

    def profile_function(self, func, *args, **kwargs):
        """分析函数性能"""
        pr = cProfile.Profile()
        pr.enable()

        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()

        pr.disable()

        # 获取统计信息
        s = StringIO()
        ps = pstats.Stats(pr, stream=s)
        ps.sort_stats("cumulative")
        ps.print_stats(10)  # 显示前10个最耗时的函数

        self.results[func.__name__] = {
            "execution_time": end_time - start_time,
            "profile_stats": s.getvalue(),
        }

        return result


def benchmark_dict_utils():
    """基准测试DictUtils"""
    import sys

    sys.path.insert(0, "src")
    from utils.dict_utils import DictUtils

    print("\n📊 DictUtils性能基准测试")

    # 测试数据
    small_data = {"a": {"b": {"c": 1}}}
    large_data = {f"key{i}": i for i in range(1000)}
    nested_data = {}
    for i in range(100):
        nested_data[f"level{i}"] = {f"sub{i}": {"value": i}}

    # 1. get_nested性能
    print("\n1. get_nested性能测试...")
    profiler = PerformanceProfiler()

    # 小数据
    result = profiler.profile_function(DictUtils.get_nested, small_data, "a.b.c")
    print(f"   小数据: {result}")

    # 大数据
    for i in range(100):
        DictUtils.get_nested(large_data, f"key{i}")

    # 2. merge性能
    print("\n2. merge性能测试...")
    dict1 = {f"key{i}": i for i in range(500)}
    dict2 = {f"key{i}": i * 2 for i in range(500, 1000)}

    result = profiler.profile_function(DictUtils.merge, dict1, dict2)
    print(f"   合并1000个键: {len(result)}个结果")

    # 3. flatten性能
    print("\n3. flatten性能测试...")
    result = profiler.profile_function(DictUtils.flatten, nested_data)
    print(f"   扁平化结果: {len(result)}个键")


def optimize_imports():
    """优化导入语句"""
    print("\n🔧 优化导入语句...")

    # 检查是否有未使用的导入
    files_to_check = list(Path("src").rglob("*.py"))[:10]  # 只检查前10个文件

    for file_path in files_to_check:
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            # 检查常见的问题
            issues = []

            # 1. 未使用的导入
            if "import " in content:
                lines = content.split("\n")
                for line in lines:
                    if line.strip().startswith("import ") and " # " not in line:
                        module = line.strip().replace("import ", "").split(".")[0]
                        if module not in content[content.find(line) + len(line) :]:
                            issues.append(f"可能未使用的导入: {module}")

            if issues:
                print(f"\n  {file_path.relative_to(Path.cwd())}:")
                for issue in issues[:3]:  # 只显示前3个问题
                    print(f"    - {issue}")

        except Exception as e:
            print(f"  ❌ {file_path}: {e}")


def analyze_code_complexity():
    """分析代码复杂度"""
    print("\n📈 代码复杂度分析...")

    complex_files = []

    for file_path in list(Path("src").rglob("*.py"))[:20]:  # 只分析前20个文件
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            # 简单的复杂度指标
            lines = content.split("\n")
            total_lines = len(lines)
            code_lines = len(
                [l for l in lines if l.strip() and not l.strip().startswith("#")]
            )
            max(len(l) for l in lines) if lines else 0

            # 检查函数数量和长度
            function_count = content.count("def ")
            class_count = content.count("class ")

            # 复杂度评分（简化版）
            complexity_score = code_lines / 10 + function_count * 2 + class_count * 3

            if complexity_score > 50:
                complex_files.append(
                    {
                        "file": str(file_path.relative_to(Path.cwd())),
                        "score": complexity_score,
                        "lines": total_lines,
                        "functions": function_count,
                        "classes": class_count,
                    }
                )

        except Exception as e:
            print(f"  ❌ {file_path}: {e}")

    if complex_files:
        print("\n  复杂度较高的文件（需要重构）:")
        for file_info in sorted(complex_files, key=lambda x: x["score"], reverse=True)[
            :5
        ]:
            print(f"    - {file_info['file']}: 评分={file_info['score']:.1f}")


def suggest_optimizations():
    """建议优化方案"""
    print("\n💡 性能优化建议:")
    print("\n1. 缓存优化")
    print("   - 实现Redis缓存层")
    print("   - 缓存频繁查询的数据")
    print("   - 使用缓存装饰器")

    print("\n2. 数据库优化")
    print("   - 添加数据库索引")
    print("   - 使用连接池")
    print("   - 批量操作代替单个操作")

    print("\n3. 异步优化")
    print("   - 使用async/await处理I/O密集型操作")
    print("   - 并发处理多个请求")

    print("\n4. 算法优化")
    print("   - 避免嵌套循环")
    print("   - 使用生成器处理大数据集")
    print("   - 选用合适的数据结构")


def generate_performance_report():
    """生成性能报告"""
    print("\n" + "=" * 60)
    print("           性能分析报告")
    print("=" * 60)

    # 运行基准测试
    benchmark_dict_utils()

    # 优化分析
    optimize_imports()
    analyze_code_complexity()
    suggest_optimizations()

    print("\n" + "=" * 60)
    print("✅ 性能分析完成！")
    print("\n📊 推荐使用以下工具进行深入分析:")
    print("1. py-spy: Python性能分析")
    print("2. memory-profiler: 内存使用分析")
    print("3. line-profiler: 逐行性能分析")
    print("4. pytest-benchmark: 测试基准")
    print("=" * 60)


def main():
    """主函数"""
    generate_performance_report()


if __name__ == "__main__":
    main()
