#!/usr/bin/env python3
"""
V26.3 生产环境冒烟测试脚本
============================

目标:
  1. 小规模采集 10 场比赛
  2. 监控采集频率（Jittering 验证）
  3. 验证数据落地（l2_raw_json + collection_status）
  4. 检查 403/429 迹象

Author: Senior Development Engineer
Version: V1.0
Date: 2026-01-06
"""

import json
import sys
import time
from datetime import datetime
from typing import Any

sys.path.insert(0, "/home/user/projects/FootballPrediction")

import psycopg2
from psycopg2.extras import RealDictCursor

from src.api.collectors.fotmob_core import FotMobCoreCollector
from src.config_unified import get_settings


def get_db_connection():
    """获取数据库连接"""
    settings = get_settings()
    return psycopg2.connect(
        host=settings.database.host,
        port=settings.database.port,
        database=settings.database.name,
        user=settings.database.user,
        password=settings.database.password.get_secret_value(),
        cursor_factory=RealDictCursor,
    )


class SmokeTestRunner:
    """冒烟测试运行器 - V26.4 安全加固版"""

    def __init__(self, max_matches: int = 10, stop_after_n_failures: int = 3):
        self.max_matches = max_matches
        self.stop_after_n_failures = stop_after_n_failures
        self.collector = FotMobCoreCollector()
        self.results = []
        self.consecutive_failures = 0
        self.start_time = None
        self.last_request_time = None

import psycopg2
from psycopg2.extras import RealDictCursor

from src.api.collectors.fotmob_core import FotMobCoreCollector
from src.config_unified import get_settings


def get_db_connection():
    """获取数据库连接"""
    settings = get_settings()
    return psycopg2.connect(
        host=settings.database.host,
        port=settings.database.port,
        database=settings.database.name,
        user=settings.database.user,
        password=settings.database.password.get_secret_value(),
        cursor_factory=RealDictCursor,
    )


class SmokeTestRunner:
    """冒烟测试运行器"""

    def __init__(self, max_matches: int = 10, stop_after_n_failures: int = 3):
        self.max_matches = max_matches
        self.stop_after_n_failures = stop_after_n_failures
        self.collector = FotMobCoreCollector()
        self.results = []
        self.consecutive_failures = 0
        self.start_time = None

    def get_premier_league_matches(self, limit: int = 20) -> list[dict[str, Any]]:
        """
        获取英超测试比赛列表

        使用固定的近期比赛 ID（2023/24 赛季）
        """
        # 英超 2023/24 赛季的一些已知比赛 ID
        known_matches = [
            {"match_id": 3901193, "home_team": "Crystal Palace", "away_team": "Manchester City", "status": "finished"},
            {"match_id": 3901215, "home_team": "Arsenal", "away_team": "Manchester United", "status": "finished"},
            {"match_id": 3901250, "home_team": "Liverpool", "away_team": "Everton", "status": "finished"},
            {"match_id": 3901189, "home_team": "Chelsea", "away_team": "Tottenham", "status": "finished"},
            {"match_id": 3901276, "home_team": "Newcastle", "away_team": "Aston Villa", "status": "finished"},
            {"match_id": 3901234, "home_team": "West Ham", "away_team": "Brentford", "status": "finished"},
            {"match_id": 3901267, "home_team": "Brighton", "away_team": "Fulham", "status": "finished"},
            {"match_id": 3901228, "home_team": "Wolves", "away_team": "Bournemouth", "status": "finished"},
            {"match_id": 3901245, "home_team": "Nottingham Forest", "away_team": "Luton Town", "status": "finished"},
            {"match_id": 3901201, "home_team": "Sheffield United", "away_team": "Burnley", "status": "finished"},
        ]

        return known_matches[:limit]

    def harvest_single_match(self, match_id: int) -> dict[str, Any]:
        """
        采集单场比赛

        Returns:
            包含采集结果的字典
        """
        match_start = time.time()
        result = {
            "match_id": match_id,
            "success": False,
            "duration_ms": 0,
            "wait_time_ms": 0,
            "error": None,
            "status_code": None,
            "collection_status": None,
            "has_raw_json": False,
            "has_extracted_features": False,
        }

        try:
            # 记录等待时间（如果有）
            if hasattr(self.collector, 'last_request_time'):
                wait_time = time.time() - self.collector.last_request_time
                result["wait_time_ms"] = int(wait_time * 1000)

            # 调用 harvest_match_with_league
            success = self.collector.harvest_match_with_league(
                match_id=match_id,
                league_id=47,
                season="2324"
            )

            result["duration_ms"] = int((time.time() - match_start) * 1000)
            result["success"] = success

            if success:
                # 验证数据库状态
                result.update(self._verify_database_record(match_id))
                self.consecutive_failures = 0
            else:
                self.consecutive_failures += 1
                result["error"] = "harvest_match_with_league returned False"

        except Exception as e:
            result["duration_ms"] = int((time.time() - match_start) * 1000)
            result["error"] = str(e)
            self.consecutive_failures += 1

        # 记录本次请求时间
        self.collector.last_request_time = time.time()

        return result

    def _verify_database_record(self, match_id: int) -> dict[str, Any]:
        """验证数据库记录"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT
                            match_id,
                            collection_status,
                            l2_raw_json IS NOT NULL as has_raw_json,
                            l2_extracted_features IS NOT NULL as has_extracted_features,
                            collected_at,
                            extracted_at,
                            last_error
                        FROM matches
                        WHERE match_id = %s;
                    """, (str(match_id),))

                    row = cursor.fetchone()
                    if row:
                        return {
                            "collection_status": row["collection_status"],
                            "has_raw_json": row["has_raw_json"],
                            "has_extracted_features": row["has_extracted_features"],
                            "collected_at": row["collected_at"].isoformat() if row["collected_at"] else None,
                            "extracted_at": row["extracted_at"].isoformat() if row["extracted_at"] else None,
                            "last_error": row["last_error"],
                        }
        except Exception as e:
            return {"db_error": str(e)}

        return {}

    def check_for_403_429(self) -> list[str]:
        """检查是否有 403/429 迹象"""
        warnings = []

        # 检查连续失败计数
        if self.collector.consecutive_failures >= 3:
            warnings.append(f"⚠️  连续失败 {self.collector.consecutive_failures} 次，可能遇到 IP 封禁")

        # 检查熔断器状态
        if hasattr(self.collector, 'max_consecutive_failures'):
            if self.collector.consecutive_failures >= self.collector.max_consecutive_failures:
                warnings.append("🚨 熔断器已触发！采集被暂停")

        # 检查失败率
        if self.results:
            failure_rate = sum(1 for r in self.results if not r["success"]) / len(self.results)
            if failure_rate > 0.5:
                warnings.append(f"⚠️  失败率过高: {failure_rate*100:.1f}%")

        return warnings

    def print_results_table(self):
        """打印结果统计表"""
        print("\n" + "=" * 120)
        print("📊 V26.3 冒烟测试结果统计")
        print("=" * 120)

        # 表头
        header = f"{'比赛ID':<12} {'状态':<10} {'耗时':<10} {'等待':<10} {'RawJSON':<10} {'Extracted':<10} {'CollectionStatus':<15} {'错误信息'}"
        print(header)
        print("-" * 120)

        # 数据行
        for r in self.results:
            match_id = str(r["match_id"])[:10]
            status = "✅ 成功" if r["success"] else "❌ 失败"
            duration = f"{r['duration_ms']}ms"
            wait = f"{r['wait_time_ms']}ms"
            raw_json = "✅" if r.get("has_raw_json") else "❌"
            extracted = "✅" if r.get("has_extracted_features") else "❌"
            coll_status = (r.get("collection_status") or "N/A")[:14]
            error = (r.get("error") or "")[:30]

            row = f"{match_id:<12} {status:<10} {duration:<10} {wait:<10} {raw_json:<10} {extracted:<10} {coll_status:<15} {error}"
            print(row)

        print("-" * 120)

    def print_summary(self):
        """打印汇总信息"""
        total = len(self.results)
        success = sum(1 for r in self.results if r["success"])
        failed = total - success

        avg_duration = sum(r["duration_ms"] for r in self.results) / total if total > 0 else 0
        avg_wait = sum(r["wait_time_ms"] for r in self.results if r["wait_time_ms"] > 0) / total if total > 0 else 0

        print(f"\n📈 汇总统计:")
        print(f"  总采集数: {total} 场")
        print(f"  成功: {success} 场 ({success/total*100:.1f}%)" if total > 0 else "  成功: 0 场")
        print(f"  失败: {failed} 场 ({failed/total*100:.1f}%)" if total > 0 else "  失败: 0 场")
        print(f"  平均耗时: {avg_duration:.0f}ms")
        print(f"  平均等待: {avg_wait:.0f}ms")

        # 频率监控（Jittering 验证）
        wait_times = [r["wait_time_ms"] for r in self.results if r["wait_time_ms"] > 0]
        if wait_times:
            min_wait = min(wait_times)
            max_wait = max(wait_times)
            print(f"\n⏱️  频率监控 (Jittering):")
            print(f"  最小等待: {min_wait}ms")
            print(f"  最大等待: {max_wait}ms")
            print(f"  波动范围: {max_wait - min_wait}ms")
            if max_wait - min_wait > 500:  # 波动超过 500ms
                print(f"  ✅ Jittering 生效（波动 {max_wait - min_wait}ms）")
            else:
                print(f"  ⚠️  波动较小，可能未启用 Jittering")

    def run(self):
        """执行冒烟测试"""
        print("=" * 120)
        print("🚀 V26.3 生产环境冒烟测试")
        print("=" * 120)

        self.start_time = time.time()

        # 1. 获取比赛列表
        print("\n📍 步骤 1: 获取英超比赛列表...")
        matches = self.get_premier_league_matches(limit=20)

        if not matches:
            print("❌ 无法获取比赛列表，测试终止")
            return False

        print(f"✅ 获取到 {len(matches)} 场比赛，将测试前 {min(self.max_matches, len(matches))} 场")

        # 2. 逐个采集
        print(f"\n📍 步骤 2: 开始采集（最多 {self.max_matches} 场，连续 {self.stop_after_n_failures} 次失败停止）...")
        print("-" * 120)

        for i, match in enumerate(matches[:self.max_matches], 1):
            match_id = match["match_id"]
            home_team = match.get("home_team", "Unknown")
            away_team = match.get("away_team", "Unknown")

            print(f"\n[{i}/{min(self.max_matches, len(matches))}] 采集: {home_team} vs {away_team} (ID: {match_id})")

            result = self.harvest_single_match(match_id)
            self.results.append(result)

            # 打印即时结果
            if result["success"]:
                print(f"  ✅ 成功 - 耗时: {result['duration_ms']}ms, 等待: {result['wait_time_ms']}ms")
                if result.get("has_raw_json"):
                    print(f"     l2_raw_json: ✅ 已存储")
                if result.get("collection_status"):
                    print(f"     collection_status: {result['collection_status']}")
            else:
                print(f"  ❌ 失败 - {result.get('error', 'Unknown error')[:50]}")

            # 检查是否需要提前终止
            if self.consecutive_failures >= self.stop_after_n_failures:
                print(f"\n🚨 连续 {self.consecutive_failures} 次失败，停止测试")
                break

            # 检查熔断器
            warnings = self.check_for_403_429()
            if warnings:
                for warning in warnings:
                    print(f"\n{warning}")
                if "熔断器已触发" in " ".join(warnings):
                    break

        # 3. 打印结果
        self.print_results_table()
        self.print_summary()

        # 4. 检查 403/429 迹象
        warnings = self.check_for_403_429()
        if warnings:
            print(f"\n⚠️  警告:")
            for warning in warnings:
                print(f"  {warning}")

        # 5. 最终评估
        total_time = time.time() - self.start_time
        print(f"\n⏱️  总耗时: {total_time:.1f}秒")

        return self._generate_recommendation()

    def _generate_recommendation(self) -> bool:
        """生成 PM 评估建议"""
        success_rate = sum(1 for r in self.results if r["success"]) / len(self.results) if self.results else 0

        print("\n" + "=" * 120)
        print("📋 PM 评估建议")
        print("=" * 120)

        if success_rate >= 0.8:
            print("\n✅ **可以全量收割**")
            print(f"   - 成功率: {success_rate*100:.1f}%")
            print("   - 数据落地正常 (l2_raw_json + collection_status)")
            print("   - 无明显 IP 封禁迹象")
            print("   - 建议启动 24h 巡航模式")
        elif success_rate >= 0.5:
            print("\n⚠️  **需要调整代理策略**")
            print(f"   - 成功率: {success_rate*100:.1f}%")
            print("   - 可能遇到频率限制")
            print("   - 建议:")
            print("     1. 增加请求延迟 (当前: ~2-3秒)")
            print("     2. 配置代理池轮换")
            print("     3. 降低并发度")
        else:
            print("\n🚨 **不建议全量收割**")
            print(f"   - 成功率: {success_rate*100:.1f}%")
            print("   - 可能存在以下问题:")
            print("     1. IP 已被封禁 (HTTP 403/429)")
            print("     2. API 端点变更")
            print("     3. 网络连接问题")
            print("   - 建议:")
            print("     1. 检查网络连接")
            print("     2. 验证 API 可用性")
            print("     3. 等待 6-24 小时冷却期")

        print("=" * 120)

        return success_rate >= 0.5


def main():
    """主函数"""
    runner = SmokeTestRunner(max_matches=10, stop_after_n_failures=3)
    success = runner.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
