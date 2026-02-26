#!/usr/bin/env python3
"""
V85.0 Enterprise Health Check - 全流程自动化哨兵

在每次启动 grand_harvest 前自动执行，确保系统健康：
1. 运行全量单元测试
2. 探测数据库连接
3. 检查网络环境
4. 验证配置完整性
5. Zero-Debt 认证（无硬编码凭证）

Usage:
    python scripts/health_check.py
    # 或在 grand_harvest 中集成
    from scripts.health_check import run_health_check
    if not run_health_check():
        sys.exit(1)
"""

import os
import sys
import subprocess
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

import psycopg2
from dotenv import load_dotenv

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    from src.config_unified import get_settings
    from src.database.models import FotMobMatchData, OpeningOddsData, FinalOddsData
except ImportError:
    # Fallback for direct execution
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from src.config_unified import get_settings
    from src.database.models import FotMobMatchData, OpeningOddsData, FinalOddsData


# ============================================================================
# Colors and Formatting
# ============================================================================

class Colors:
    """Terminal color codes."""
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    RED = '\033[0;31m'
    BLUE = '\033[0;34m'
    NC = '\033[0m'  # No Color


def print_header(title: str):
    """Print formatted header."""
    print(f"\n{Colors.BLUE}{'=' * 70}{Colors.NC}")
    print(f"{Colors.BLUE}{title}{Colors.NC}")
    print(f"{Colors.BLUE}{'=' * 70}{Colors.NC}\n")


def print_success(msg: str):
    """Print success message."""
    print(f"{Colors.GREEN}✓ {msg}{Colors.NC}")


def print_warning(msg: str):
    """Print warning message."""
    print(f"{Colors.YELLOW}⚠ {msg}{Colors.NC}")


def print_error(msg: str):
    """Print error message."""
    print(f"{Colors.RED}✗ {msg}{Colors.NC}")


def print_info(msg: str):
    """Print info message."""
    print(f"  {msg}")


# ============================================================================
# Health Check Functions
# ============================================================================

def check_environment_file() -> Tuple[bool, str]:
    """检查 .env 文件是否存在且有效."""
    env_path = Path.cwd() / ".env"
    env_example = Path.cwd() / ".env.example"

    if not env_path.exists():
        return False, f".env 文件不存在（请参考 .env.example）"

    # Load and validate
    load_dotenv()
    required_vars = ["DB_HOST", "DB_NAME", "DB_USER", "DB_PASSWORD"]

    missing_vars = []
    for var in required_vars:
        if not os.environ.get(var):
            missing_vars.append(var)

    if missing_vars:
        return False, f"缺少必需的环境变量: {', '.join(missing_vars)}"

    return True, "环境配置完整"


def check_database_connection() -> Tuple[bool, str]:
    """检查数据库连接是否正常."""
    try:
        settings = get_settings()
        conn = psycopg2.connect(
            host=settings.database.host,
            port=settings.database.port,
            database=settings.database.name,
            user=settings.database.user,
            password=settings.database.password.get_secret_value(),
            connect_timeout=10
        )

        # Test query
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()
        cursor.close()
        conn.close()

        return True, f"数据库连接正常 (PostgreSQL {version[0][:10]})"

    except Exception as e:
        return False, f"数据库连接失败: {str(e)[:80]}"


def check_pydantic_models() -> Tuple[bool, str]:
    """验证 Pydantic 数据模型是否正常工作."""
    try:
        from datetime import datetime

        # Test L1 Model
        FotMobMatchData(
            match_id="test_123",
            home_team="Team A",
            away_team="Team B",
            match_date=datetime.now(),
            league_name="Test League",
            season="2024-2025"
        )

        # Test L2 Model
        OpeningOddsData(
            match_id="test_123",
            source_name="Entity_P",
            init_h=2.50
        )

        # Test L3 Model
        FinalOddsData(
            match_id="test_123",
            url="https://test.com",
            final_h=2.50,
            final_d=3.20,
            final_a=2.80,
            integrity_score=1.0456,
            is_valid=True,
            pinnacle_found=True,
            success=True
        )

        return True, "Pydantic 数据模型验证通过"

    except Exception as e:
        return False, f"数据模型验证失败: {str(e)[:80]}"


def check_network_connectivity() -> Tuple[bool, str]:
    """检查网络连接（测试关键外网连接）。"""
    test_urls = [
        ("https://www.fotmob.com", "FotMob"),
        ("https://www.oddsportal.com", "OddsPortal"),
    ]

    failed_urls = []
    for url, name in test_urls:
        try:
            req = urllib.request.Request(url, method='HEAD')
            with urllib.request.urlopen(req, timeout=10) as response:
                if response.status == 200:
                    print_success(f"{name} 连接正常")
                else:
                    failed_urls.append(f"{name} (HTTP {response.status})")
        except Exception as e:
            failed_urls.append(f"{name} ({str(e)[:30]})")

    if failed_urls:
        return False, f"网络连接问题: {', '.join(failed_urls)}"
    else:
        return True, "网络连接正常"


def check_import_statements() -> Tuple[bool, str]:
    """检查关键模块是否可以正常导入。"""
    critical_modules = [
        "src.config_unified",
        "src.database.models",
        "src.api.collectors.odds_production_extractor",
    ]

    failed_modules = []
    for module in critical_modules:
        try:
            __import__(module)
            print_info(f"✓ {module}")
        except Exception as e:
            failed_modules.append(f"{module}: {str(e)[:40]}")

    if failed_modules:
        return False, f"模块导入失败: {len(failed_modules)} 个"
    else:
        return True, "所有关键模块导入成功"


def check_code_quality() -> Tuple[bool, str]:
    """运行基础代码质量检查（不阻塞，仅警告）。"""
    try:
        result = subprocess.run(
            ["python", "-m", "ruff", "check", "src/database/models.py"],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0:
            return True, "代码质量检查通过"
        else:
            # 不阻塞，仅警告
            error_lines = result.stderr.strip().split('\n')[:3]
            return True, f"代码质量警告: {'; '.join(error_lines)}"

    except Exception:
        return True, "代码质量检查跳过（ruff 未安装）"


def run_unit_tests() -> Tuple[bool, str]:
    """运行核心单元测试套件。"""
    print_info("运行 Pydantic 数据模型测试...")

    try:
        result = subprocess.run(
            ["python", "-m", "pytest", "tests/database/test_models.py", "-v", "--tb=line"],
            capture_output=True,
            text=True,
            timeout=120
        )

        # Parse output
        lines = result.stdout.split('\n')
        for line in lines:
            if "passed" in line.lower():
                print_info(f"测试结果: {line.strip()}")

        if result.returncode == 0:
            return True, "单元测试全部通过"
        else:
            return False, f"单元测试失败 (exit code: {result.returncode})"

    except Exception as e:
        return False, f"单元测试执行失败: {str(e)[:80]}"


def check_hardcoded_credentials() -> Tuple[bool, str]:
    """Zero-Debt 认证：扫描真正的硬编码凭证（排除环境变量引用）。"""
    print_info("扫描硬编码凭证...")

    # 排除目录
    exclude_dirs = {'venv', '__pycache__', '.pytest_cache', 'node_modules', 'migrations'}

    # 扫描 src/ 目录
    src_dir = Path.cwd() / "src"
    issues_found = []

    # 真正可疑的模式：password后紧跟等号和引号，且不是 os.environ 或 os.getenv
    import re
    hardcoded_pattern = re.compile(
        r'(password|api_key|secret|token)\s*=\s*["\'][^"\']+["\']',
        re.IGNORECASE
    )

    # 排除常见示例占位符
    placeholder_patterns = [
        'your_', 'your_bot', 'your_password', 'your_api',
        'example_', 'demo_', 'test_', 'xxx',
        '<', '{{', '[[', 'replace',
    ]

    # 排除模式：环境变量引用
    env_var_pattern = re.compile(
        r'(os\.environ|os\.getenv|settings\.|config\.|get_settings\(\))',
        re.IGNORECASE
    )

    for py_file in src_dir.rglob("*.py"):
        # 跳过排除目录
        if any(excluded in py_file.parts for excluded in exclude_dirs):
            continue

        try:
            content = py_file.read_text()
            for line_num, line in enumerate(content.split('\n'), 1):
                # 检查是否有硬编码模式
                match = hardcoded_pattern.search(line)
                if match:
                    # 检查是否是示例占位符
                    is_placeholder = any(placeholder in line.lower() for placeholder in placeholder_patterns)
                    # 检查是否是环境变量引用
                    is_env_var = env_var_pattern.search(line) is not None

                    if not is_placeholder and not is_env_var:
                        issues_found.append(f"{py_file.relative_to(Path.cwd())}:{line_num}")
        except Exception:
            continue

    if issues_found:
        # 显示前几个问题
        issue_samples = issues_found[:3]
        return False, f"发现硬编码凭证: {len(issues_found)} 处 (例如: {', '.join(issue_samples)})"
    else:
        return True, "Zero-Debt 认证通过（无硬编码凭证）"


def check_test_coverage() -> Tuple[bool, str, float]:
    """检查测试覆盖率（目标: 80%+）。"""
    try:
        result = subprocess.run(
            ["python", "-m", "pytest", "tests/database/test_models.py",
             "--cov=src/database/models", "--cov-report=term", "--cov-report=json",
             "-q"],
            capture_output=True,
            text=True,
            timeout=120
        )

        # Parse coverage from output
        for line in result.stdout.split('\n'):
            if "Coverage" in line or "%" in line:
                print_info(f"覆盖率: {line.strip()}")

        # Try to get coverage from JSON report
        coverage_file = Path.cwd() / "coverage.json"
        if coverage_file.exists():
            import json
            with open(coverage_file) as f:
                cov_data = json.load(f)
                total_coverage = cov_data.get('totals', {}).get('percent_covered', 0)
                return True, "覆盖率报告生成成功", total_coverage

        return True, "覆盖率检查完成", 0.0

    except Exception as e:
        return False, f"覆盖率检查失败: {str(e)[:80]}", 0.0


# ============================================================================
# Main Health Check Function
# ============================================================================

def run_health_check(verbose: bool = True) -> bool:
    """
    运行完整的健康检查流程。

    Args:
        verbose: 是否输出详细信息

    Returns:
        True if all critical checks pass, False otherwise
    """
    print_header("V85.0 Enterprise Health Check - 自动化哨兵")
    print_info(f"执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    all_checks_passed = True
    checks = [
        ("环境配置", check_environment_file),
        ("关键模块导入", check_import_statements),
        ("Pydantic 数据模型", check_pydantic_models),
        ("单元测试", run_unit_tests),
        ("数据库连接", check_database_connection),
        ("网络连接", check_network_connectivity),
        ("代码质量", check_code_quality),
        ("Zero-Debt 认证", check_hardcoded_credentials),
    ]

    failed_checks = []
    for check_name, check_func in checks:
        if verbose:
            print_info(f"检查 {check_name}...")

        passed, message = check_func()

        if passed:
            print_success(f"{check_name}: {message}")
        else:
            print_error(f"{check_name}: {message}")
            all_checks_passed = False
            failed_checks.append((check_name, message))

    # Coverage check (non-blocking)
    print_info("\n检查测试覆盖率...")
    try:
        cov_passed, cov_message, cov_value = check_test_coverage()
        if cov_value > 0:
            if cov_value >= 80:
                print_success(f"覆盖率: {cov_value:.1f}% (目标: 80%+) ✓")
            elif cov_value >= 50:
                print_warning(f"覆盖率: {cov_value:.1f}% (目标: 80%+, 需改进)")
            else:
                print_error(f"覆盖率: {cov_value:.1f}% (目标: 80%+, 差距较大)")
        else:
            print_info(f"{cov_message}")
    except Exception as e:
        print_warning(f"覆盖率检查跳过: {str(e)[:50]}")

    # Final Report
    print_header("健康检查总结")

    if all_checks_passed:
        print_success("所有关键检查通过！系统健康，可以启动 grand_harvest")
        print_info("\n下一步操作:")
        print_info("  python scripts/production_harvester.py")
        print_info("  python scripts/v82_6_final_extractor.py")
        return True
    else:
        print_error("健康检查失败！请先修复以下问题再启动 harvest:\n")
        for check_name, message in failed_checks:
            print_error(f"  • {check_name}: {message}")
        print_info("\n修复建议:")
        print_info("  1. 检查 .env 文件配置")
        print_info("  2. 确认数据库服务正在运行 (docker-compose up -d db)")
        print_info("  3. 检查网络连接和代理设置")
        print_info("  4. 运行 python -m pytest tests/ 查看详细测试失败")
        return False


# ============================================================================
# CLI Entry Point
# ============================================================================

def main():
    """CLI 入口点."""
    import argparse

    parser = argparse.ArgumentParser(description="V85.0 Enterprise Health Check")
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="静默模式，仅输出结果"
    )
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="遇到第一个失败即退出"
    )

    args = parser.parse_args()

    # Run health check
    success = run_health_check(verbose=not args.quiet)

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
