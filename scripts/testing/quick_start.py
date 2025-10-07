#!/usr/bin/env python3
"""
测试覆盖率提升快速启动脚本
执行第一阶段的自动化改进任务
"""

import sys
import subprocess
import json
from datetime import datetime
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))


def run_command(cmd, description, shell=True):
    """运行命令并记录结果"""
    print(f"\n{'='*60}")
    print(f"执行: {description}")
    print(f"命令: {cmd}")
    print("=" * 60)

    try:
        result = subprocess.run(
            cmd, shell=shell, capture_output=True, text=True, cwd=project_root
        )

        if result.stdout:
            print("输出:")
            print(result.stdout)

        if result.stderr:
            print("错误:")
            print(result.stderr)

        if result.returncode != 0:
            print(f"❌ 失败 (退出码: {result.returncode})")
            return False
        else:
            print("✅ 成功")
            return True

    except Exception as e:
        print(f"❌ 异常: {e}")
        return False


def check_environment():
    """检查环境准备情况"""
    print("\n🔍 检查环境准备情况...")

    checks = {
        "Python版本": "python --version",
        "pytest版本": "pytest --version",
        "pip依赖": "pip list | grep -E '(pytest|coverage|fastapi)'",
        "测试目录": "ls -la tests/ | head -10",
    }

    results = {}
    for name, cmd in checks.items():
        print(f"\n检查 {name}:")
        success = run_command(cmd, f"检查{name}", shell=True)
        results[name] = success

    return results


def create_test_env_file():
    """创建测试环境配置文件"""
    print("\n📝 创建测试环境配置...")

    env_content = """# 测试环境配置
ENVIRONMENT=test
TESTING=true
DEBUG=true
LOG_LEVEL=DEBUG

# 数据库配置（TestContainers将自动设置）
DATABASE_URL=postgresql://test:test@localhost:5432/test_db
TEST_DATABASE_URL=sqlite:///:memory:

# Redis配置
REDIS_URL=redis://localhost:6379/1
TEST_REDIS_URL=redis://localhost:6379/15

# 外部服务Mock
ENABLE_FEAST=false
ENABLE_KAFKA=false
ENABLE_MLFLOW=false
ENABLE_PROMETHEUS=false

# API配置
API_HOST=127.0.0.1
API_PORT=8001

# 安全配置（测试用）
SECRET_KEY=test_secret_key_for_testing_only
JWT_SECRET_KEY=test_jwt_secret_for_testing_only

# 缓存配置
CACHE_TTL=60
CACHE_MAX_SIZE=1000

# 测试配置
FAST_FAIL=false
ENABLE_METRICS=false
MINIMAL_API_MODE=true

# Mock配置
MOCK_EXTERNAL_APIS=true
MOCK_DATABASE=true
"""

    env_file = project_root / ".env.test"
    with open(env_file, "w") as f:
        f.write(env_content)

    print(f"✅ 创建文件: {env_file}")
    return True


def run_basic_tests():
    """运行基础测试"""
    print("\n🧪 运行基础测试...")

    # 1. 运行单个测试验证环境
    success = run_command(
        "python -m pytest tests/unit/api/test_health.py::TestHealthAPI::test_health_check_success -v",
        "验证健康检查测试",
    )

    if not success:
        print("❌ 基础测试失败，请检查环境配置")
        return False

    # 2. 运行覆盖率测试（低阈值）
    success = run_command(
        "python -m pytest tests/unit/test_simple_functional.py --cov=src --cov-report=term-missing --cov-fail-under=10 -v",
        "运行简单功能测试（覆盖率阈值10%）",
    )

    # 3. 生成覆盖率报告
    run_command(
        "python -m pytest tests/unit/test_simple_functional.py --cov=src --cov-report=html --cov-report=term",
        "生成HTML覆盖率报告",
    )

    return True


def analyze_current_coverage():
    """分析当前覆盖率状况"""
    print("\n📊 分析当前覆盖率状况...")

    # 运行覆盖率分析
    success = run_command(
        "python -m pytest --cov=src --cov-report=json --cov-report=term -q",
        "生成覆盖率JSON报告",
    )

    if not success:
        print("❌ 无法生成覆盖率报告")
        return None

    # 读取覆盖率报告
    coverage_file = project_root / "coverage.json"
    if coverage_file.exists():
        with open(coverage_file, "r") as f:
            coverage_data = json.load(f)

        total_coverage = coverage_data["totals"]["percent_covered"]
        print(f"\n📈 当前总覆盖率: {total_coverage:.2f}%")

        # 分析各模块覆盖率
        print("\n📋 模块覆盖率详情:")
        files = coverage_data["files"]
        low_coverage = []

        for filename, file_data in files.items():
            coverage = file_data["summary"]["percent_covered"]
            print(f"  {filename}: {coverage:.2f}%")

            if coverage < 20:
                low_coverage.append((filename, coverage))

        # 找出低覆盖率模块
        if low_coverage:
            print("\n⚠️  低覆盖率模块 (<20%):")
            for filename, coverage in sorted(low_coverage, key=lambda x: x[1]):
                print(f"  - {filename}: {coverage:.2f}%")

        return {"total": total_coverage, "files": files, "low_coverage": low_coverage}

    return None


def generate_improvement_plan(coverage_data):
    """生成改进计划"""
    print("\n📋 生成改进计划...")

    if not coverage_data:
        print("❌ 无覆盖率数据，无法生成计划")
        return

    # 优先级矩阵
    priority_modules = []

    for filename, file_data in coverage_data["files"].items():
        coverage = file_data["summary"]["percent_covered"]
        lines = file_data["summary"]["num_statements"]

        # 计算提升潜力
        uncovered_lines = lines * (1 - coverage / 100)

        # 模块重要性评估（基于路径）
        importance = 0
        if "api" in filename:
            importance = 9
        elif "core" in filename or "utils" in filename:
            importance = 8
        elif "services" in filename:
            importance = 7
        elif "database" in filename:
            importance = 6
        else:
            importance = 5

        # 测试难度评估（基于文件大小）
        difficulty = min(10, lines / 50)

        # 优先级分数 = 重要性 * 提升潜力 / 难度
        priority_score = (
            (importance * uncovered_lines) / difficulty if difficulty > 0 else 0
        )

        priority_modules.append(
            {
                "filename": filename,
                "coverage": coverage,
                "lines": lines,
                "uncovered_lines": uncovered_lines,
                "importance": importance,
                "difficulty": difficulty,
                "priority_score": priority_score,
            }
        )

    # 按优先级排序
    priority_modules.sort(key=lambda x: x["priority_score"], reverse=True)

    # 生成建议
    print("\n🎯 优先改进建议（前10个）:")
    print("-" * 80)
    print(f"{'模块':<40} {'当前覆盖率':<12} {'提升潜力':<10} {'优先级':<8}")
    print("-" * 80)

    for i, module in enumerate(priority_modules[:10], 1):
        print(
            f"{i:2d}. {module['filename']:<40} "
            f"{module['coverage']:.1f}%{'':<7} "
            f"{module['uncovered_lines']:.0f}行{'':<6} "
            f"{module['priority_score']:.1f}"
        )

    # 保存改进计划
    plan_file = project_root / "test_improvement_plan.json"
    with open(plan_file, "w") as f:
        json.dump(priority_modules, f, indent=2)

    print(f"\n✅ 改进计划已保存到: {plan_file}")

    return priority_modules


def create_weekly_tasks(priority_modules):
    """创建第一周任务列表"""
    print("\n📅 创建第一周任务列表...")

    week_tasks = {
        "Day 1-2 (环境准备)": [
            "✅ 创建 .env.test 文件",
            "⏳ 安装 testcontainers-python",
            "⏳ 配置 CI/CD 基础流水线",
            "⏳ 修复循环导入问题",
        ],
        "Day 3-4 (核心模块)": [
            "提升 src/core/config.py 覆盖率到 90%",
            "提升 src/utils/time_utils.py 覆盖率到 85%",
            "提升 src/utils/response.py 覆盖率到 80%",
        ],
        "Day 5 (API层)": [
            "提升 src/api/health.py 覆盖率到 75%",
            "创建 API 测试基类",
        ],
        "Day 6-7 (服务层)": [
            "提升 src/services/base.py 覆盖率到 85%",
            "创建测试数据工厂",
        ],
    }

    for phase, tasks in week_tasks.items():
        print(f"\n{phase}:")
        for task in tasks:
            print(f"  {task}")

    # 创建任务文件
    tasks_file = project_root / "test_week_1_tasks.md"
    with open(tasks_file, "w") as f:
        f.write("# 第一周测试改进任务\n\n")
        for phase, tasks in week_tasks.items():
            f.write(f"## {phase}\n\n")
            for task in tasks:
                f.write(f"- [ ] {task}\n")
            f.write("\n")

    print(f"\n✅ 任务列表已保存到: {tasks_file}")


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("🚀 测试覆盖率提升快速启动脚本")
    print("=" * 60)
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"项目根目录: {project_root}")

    # 1. 检查环境
    env_results = check_environment()

    # 2. 创建测试环境配置
    create_test_env_file()

    # 3. 运行基础测试
    if not run_basic_tests():
        print("\n❌ 基础测试失败，请先解决环境问题")
        sys.exit(1)

    # 4. 分析覆盖率
    coverage_data = analyze_current_coverage()

    # 5. 生成改进计划
    priority_modules = generate_improvement_plan(coverage_data)

    # 6. 创建任务列表
    create_weekly_tasks(priority_modules)

    # 7. 生成总结报告
    print("\n" + "=" * 60)
    print("📊 快速启动完成！")
    print("=" * 60)

    if coverage_data:
        print(f"当前覆盖率: {coverage_data['total']:.2f}%")
        print(f"建议优先改进模块数: {len(priority_modules)}")

    print("\n下一步行动:")
    print("1. 查看 test_improvement_plan.json 了解详细改进计划")
    print("2. 查看 test_week_1_tasks.md 了解本周任务")
    print("3. 运行 'make coverage-local' 查看详细覆盖率报告")
    print("4. 开始执行第一周任务")

    print("\n有用命令:")
    print("- 运行所有测试: make test")
    print("- 运行单元测试: make test.unit")
    print("- 生成覆盖率报告: make coverage-local")
    print("- 查看覆盖率报告: open htmlcov/index.html")


if __name__ == "__main__":
    main()
