#!/usr/bin/env python3
"""
V26.0 生产环境预检脚本 (Final Pre-flight Audit)
====================================================

自动扫描并确认 4 项关键指标：
1. 权限: scripts/ 目录执行权限
2. 连接: 数据库连接池支持
3. 版本: 所有文件版本一致性
4. 存储: raw_match_data 表健康度

Author: Chief Quality Officer
Version: V26.0 (Stable)
Date: 2025-12-27
"""

import os
import stat
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

import psycopg2

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config_unified import get_settings


class CheckStatus(Enum):
    """检查状态枚举"""

    PASS = "✅ PASS"
    FAIL = "❌ FAIL"
    WARN = "⚠️  WARN"


@dataclass
class CheckResult:
    """检查结果"""

    name: str
    status: CheckStatus
    message: str
    details: dict[str, Any] = None
    score: int = 100  # 100 = 完美, 0 = 失败


class ReadinessChecker:
    """生产环境预检器"""

    def __init__(self):
        self.settings = get_settings()
        self.results: list[CheckResult] = []

    def run_all_checks(self) -> bool:
        """
        运行所有预检项

        Returns:
            bool: 所有检查是否通过
        """
        print("=" * 60)
        print("V26.0 生产环境预检 (Final Pre-flight Audit)")
        print("=" * 60)

        checks = [
            self._check_permissions,
            self._check_database_pool,
            self._check_version_consistency,
            self._check_storage_health,
        ]

        for check in checks:
            try:
                result = check()
                self.results.append(result)
                self._print_result(result)
            except Exception as e:
                self.results.append(CheckResult(name=check.__name__, status=CheckStatus.FAIL, message=f"检查异常: {e}"))
                self._print_result(self.results[-1])

        return self._generate_final_report()

    def _check_permissions(self) -> CheckResult:
        """检查 1: scripts/ 目录执行权限"""
        scripts_dir = Path("scripts")

        if not scripts_dir.exists():
            return CheckResult(name="权限检查", status=CheckStatus.FAIL, message="scripts/ 目录不存在")

        issues = []
        checked = 0

        # 检查所有 .sh 文件
        for script in scripts_dir.rglob("*.sh"):
            checked += 1
            st = script.stat()
            mode = st.st_mode

            # 检查是否可执行
            if not (mode & stat.S_IXUSR):
                issues.append(f"{script}: 所有者不可执行")
            if not (mode & stat.S_IXGRP):
                issues.append(f"{script}: 组不可执行")
            if not (mode & stat.S_IXOTH):
                issues.append(f"{script}: 其他人不可执行")

            # 检查权限是否为 755
            perm = stat.S_IMODE(mode)
            expected = stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH  # 755
            if perm != expected:
                issues.append(f"{script}: 权限 {oct(perm)} != 755")

        if issues:
            return CheckResult(
                name="权限检查",
                status=CheckStatus.WARN,
                message=f"发现 {len(issues)} 个权限问题",
                details={
                    "checked_files": checked,
                    "issues": issues[:5],  # 只显示前 5 个
                    "fix_command": "chmod -R 755 scripts/",
                },
                score=80,
            )

        return CheckResult(
            name="权限检查",
            status=CheckStatus.PASS,
            message=f"所有 {checked} 个脚本权限正常",
            details={"checked_files": checked},
            score=100,
        )

    def _check_database_pool(self) -> CheckResult:
        """检查 2: 数据库连接池支持"""
        try:
            # 测试单个连接
            conn = psycopg2.connect(
                host=self.settings.database.host,
                port=self.settings.database.port,
                database=self.settings.database.name,
                user=self.settings.database.user,
                password=self.settings.database.password.get_secret_value(),
                connect_timeout=5,
            )

            # 测试连接池参数
            pool_size = self.settings.database.pool_size
            max_overflow = self.settings.database.max_overflow
            max_connections = pool_size + max_overflow

            if max_connections < 10:
                return CheckResult(
                    name="连接池检查",
                    status=CheckStatus.WARN,
                    message=f"连接池配置较小: {max_connections}",
                    details={
                        "pool_size": pool_size,
                        "max_overflow": max_overflow,
                        "total": max_connections,
                        "recommended": "至少 10",
                    },
                    score=70,
                )

            conn.close()

            return CheckResult(
                name="连接池检查",
                status=CheckStatus.PASS,
                message=f"连接池支持 {max_connections} 个并发连接",
                details={"pool_size": pool_size, "max_overflow": max_overflow, "total": max_connections},
                score=100,
            )

        except Exception as e:
            return CheckResult(name="连接池检查", status=CheckStatus.FAIL, message=f"数据库连接失败: {e}", score=0)

    def _check_version_consistency(self) -> CheckResult:
        """检查 3: 版本一致性"""
        import re

        expected_version = "V26.0"
        version_pattern = re.compile(r'(?:VERSION|version|Version)[^:]*[:\s]*["\']?([Vv]\d+\.\d+)')

        issues = []
        checked = 0

        # 检查关键文件
        key_files = [
            "src/config_unified.py",
            "src/processors/__init__.py",
            "src/processors/base_extractor.py",
            "src/processors/v25_production_extractor.py",
            "src/ops/data_pipeline_v25.py",
            "src/core/types.py",
            "src/ops/performance_engine.py",
        ]

        for file_path in key_files:
            path = Path(file_path)
            if not path.exists():
                continue

            checked += 1
            content = path.read_text()

            # 查找版本声明
            matches = version_pattern.findall(content)

            if not matches:
                issues.append(f"{file_path}: 未找到版本声明")
                continue

            # 检查版本一致性
            for match in matches:
                if not match.startswith("V"):
                    match = "V" + match

                if match != expected_version:
                    issues.append(f"{file_path}: 版本 {match} != {expected_version}")

        if issues:
            return CheckResult(
                name="版本检查",
                status=CheckStatus.WARN,
                message=f"发现 {len(issues)} 个版本不一致",
                details={"expected": expected_version, "issues": issues[:5]},
                score=80,
            )

        return CheckResult(
            name="版本检查",
            status=CheckStatus.PASS,
            message=f"所有 {checked} 个文件版本一致 ({expected_version})",
            details={"checked_files": checked},
            score=100,
        )

    def _check_storage_health(self) -> CheckResult:
        """检查 4: raw_match_data 表健康度"""
        try:
            conn = psycopg2.connect(
                host=self.settings.database.host,
                port=self.settings.database.port,
                database=self.settings.database.name,
                user=self.settings.database.user,
                password=self.settings.database.password.get_secret_value(),
            )
            cur = conn.cursor()

            # 统计总记录数
            cur.execute("SELECT COUNT(*) as total FROM raw_match_data")
            total = cur.fetchone()[0]

            # 检查损坏的 JSON (raw_data 是 jsonb 类型)
            cur.execute("""
                SELECT COUNT(*) as corrupted
                FROM raw_match_data
                WHERE raw_data IS NULL
                   OR jsonb_typeof(raw_data) IS NULL
                   OR pg_column_size(raw_data) < 20
            """)
            corrupted = cur.fetchone()[0]

            # 检查 NULL 值
            cur.execute("""
                SELECT COUNT(*) as null_match_ids
                FROM raw_match_data
                WHERE match_id IS NULL OR match_id = ''
            """)
            null_ids = cur.fetchone()[0]

            conn.close()

            if total == 0:
                return CheckResult(
                    name="存储检查",
                    status=CheckStatus.WARN,
                    message="raw_match_data 表为空",
                    details={"total": 0},
                    score=50,
                )

            # 计算健康分数
            score = 100
            messages = []

            if corrupted > 0:
                score -= 30
                messages.append(f"{corrupted} 条损坏的 JSON")

            if null_ids > 0:
                score -= 20
                messages.append(f"{null_ids} 条空的 match_id")

            if total < 9000:
                score -= 10
                messages.append(f"记录数 {total} < 9000")

            if score < 70:
                status = CheckStatus.FAIL
            elif score < 90:
                status = CheckStatus.WARN
            else:
                status = CheckStatus.PASS

            message = f"总计 {total} 条记录"
            if messages:
                message += "; " + ", ".join(messages)

            return CheckResult(
                name="存储检查",
                status=status,
                message=message,
                details={"total": total, "corrupted": corrupted, "null_ids": null_ids},
                score=score,
            )

        except Exception as e:
            return CheckResult(name="存储检查", status=CheckStatus.FAIL, message=f"检查失败: {e}", score=0)

    def _print_result(self, result: CheckResult):
        """打印检查结果"""
        status_symbol = result.status.value
        score_str = f"({result.score}/100)" if result.score < 100 else ""
        print(f"{status_symbol} {result.name}{score_str}")
        print(f"   {result.message}")
        if result.details:
            for key, value in result.details.items():
                if isinstance(value, list):
                    print(f"   - {key}: {len(value)} 项")
                    for item in value[:3]:
                        print(f"     • {item}")
                else:
                    print(f"   - {key}: {value}")
        print()

    def _generate_final_report(self) -> bool:
        """生成最终报告"""
        print("=" * 60)
        print("预检报告 (Final Report)")
        print("=" * 60)

        pass_count = sum(1 for r in self.results if r.status == CheckStatus.PASS)
        warn_count = sum(1 for r in self.results if r.status == CheckStatus.WARN)
        fail_count = sum(1 for r in self.results if r.status == CheckStatus.FAIL)

        total_score = sum(r.score for r in self.results) / len(self.results) if self.results else 0

        print(f"✅ 通过: {pass_count}")
        print(f"⚠️  警告: {warn_count}")
        print(f"❌ 失败: {fail_count}")
        print()
        print(f"综合评分: {total_score:.1f}/100")

        # 最终判断
        if fail_count > 0 or total_score < 70:
            print()
            print("=" * 60)
            print("🚫 结论: 仍需修复 (NOT READY)")
            print("=" * 60)
            return False
        elif warn_count > 0:
            print()
            print("=" * 60)
            print("⚠️  结论: 准予生产 (带警告) (READY WITH WARNINGS)")
            print("=" * 60)
            return True
        else:
            print()
            print("=" * 60)
            print("✅ 结论: 准予生产 (READY FOR PRODUCTION)")
            print("=" * 60)
            return True


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="V26.0 生产环境预检")
    parser.add_argument("--fix-permissions", action="store_true", help="自动修复权限问题")

    args = parser.parse_args()

    checker = ReadinessChecker()
    success = checker.run_all_checks()

    # 自动修复权限（如果请求）
    if args.fix_permissions:
        print("\n🔧 自动修复权限...")
        os.system("chmod -R 755 scripts/")
        print("✅ 权限修复完成")

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
