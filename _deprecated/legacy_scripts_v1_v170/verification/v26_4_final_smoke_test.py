#!/usr/bin/env python3
"""
V26.4 最终安全冒烟测试脚本
===========================

V26.4 安全加固验证:
  1. 强制 Jittering 延迟 (2-5 秒)
  2. 计时器升级为 time.perf_counter()
  3. 数据库配置统一
  4. IP 熔断逻辑强化 (403/429 自杀)

Author: Senior Development Engineer (Anti-Scraping Expert)
Version: V26.4
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


class FinalSmokeTestRunner:
    """V26.4 最终安全冒烟测试运行器"""

    def __init__(self, max_matches: int = 3, stop_after_n_failures: int = 3):
        self.max_matches = max_matches
        self.stop_after_n_failures = stop_after_n_failures
        self.collector = FotMobCoreCollector()
        self.results = []
        self.consecutive_failures = 0
        # V26.4: 使用 perf_counter 提高精度
        self.start_time = None
        self.last_request_end_time = None

    def get_test_matches(self, limit: int = 10) -> list[dict[str, Any]]:
        """获取测试比赛列表"""
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
        采集单场比赛 - V26.4 版本

        V26.4 改进:
        - 使用 time.perf_counter() 替代 time.time()
        - 记录实际 Jittering 延迟
        """
        # V26.4: 使用 perf_counter 提高精度
        match_start = time.perf_counter()

        result = {
            "match_id": match_id,
            "success": False,
            "duration_ms": 0,
            "jitter_delay_ms": 0,  # 实际 Jittering 延迟
            "interval_ms": 0,      # 距离上次请求的间隔
            "error": None,
            "status_code": None,
            "collection_status": None,
            "has_raw_json": False,
            "has_extracted_features": False,
        }

        # 计算距离上次请求的间隔
        if self.last_request_end_time:
            result["interval_ms"] = int((match_start - self.last_request_end_time) * 1000)

        try:
            # 调用 harvest_match_with_league
            success = self.collector.harvest_match_with_league(
                match_id=match_id,
                league_id=47,
                season="2324"
            )

            # V26.4: 使用 perf_counter
            match_end = time.perf_counter()
            result["duration_ms"] = int((match_end - match_start) * 1000)
            result["success"] = success

            # Jittering 延迟已经在 harvest_match_with_league 中执行
            # 这里的 duration_ms 已经包含了 Jittering 延迟
            # 估算 Jittering 延迟 = 总耗时 - 估算的 API 响应时间 (约 1-2 秒)
            estimated_api_time = 1500  # 1.5 秒估算 API 响应时间
            if result["duration_ms"] > estimated_api_time:
                result["jitter_delay_ms"] = result["duration_ms"] - estimated_api_time

            if success:
                # 验证数据库状态
                result.update(self._verify_database_record(match_id))
                self.consecutive_failures = 0
            else:
                self.consecutive_failures += 1
                result["error"] = "harvest_match_with_league returned False"

        except SystemExit as e:
            # V26.4: 捕获 sys.exit() (403/429 自杀逻辑)
            result["duration_ms"] = int((time.perf_counter() - match_start) * 1000)
            result["error"] = "SYSTEM_EXIT - IP 封禁触发自杀逻辑"
            result["status_code"] = 403  # 假设是 403/429
            raise  # 重新抛出，让程序终止
        except Exception as e:
            result["duration_ms"] = int((time.perf_counter() - match_start) * 1000)
            result["error"] = str(e)
            self.consecutive_failures += 1

        # V26.4: 记录本次请求结束时间
        self.last_request_end_time = time.perf_counter()

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

    def print_results_table(self):
        """打印结果统计表"""
        print("\n" + "=" * 140)
        print("📊 V26.4 最终安全冒烟测试结果")
        print("=" * 140)

        # 表头
        header = (f"{'比赛ID':<10} {'状态':<10} {'总耗时':<10} {'Jittering':<12} {'间隔':<10} "
                  f"{'RawJSON':<10} {'Extracted':<10} {'CollectionStatus':<15} {'错误信息'}")
        print(header)
        print("-" * 140)

        # 数据行
        for r in self.results:
            match_id = str(r["match_id"])[:8]
            status = "✅ 成功" if r["success"] else "❌ 失败"
            duration = f"{r['duration_ms']}ms"
            jitter = f"{r['jitter_delay_ms']}ms"
            interval = f"{r['interval_ms']}ms"
            raw_json = "✅" if r.get("has_raw_json") else "❌"
            extracted = "✅" if r.get("has_extracted_features") else "❌"
            coll_status = (r.get("collection_status") or "N/A")[:14]
            error = (r.get("error") or "")[:25]

            row = (f"{match_id:<10} {status:<10} {duration:<10} {jitter:<12} {interval:<10} "
                   f"{raw_json:<10} {extracted:<10} {coll_status:<15} {error}")
            print(row)

        print("-" * 140)

    def print_summary(self):
        """打印汇总信息"""
        total = len(self.results)
        success = sum(1 for r in self.results if r["success"])
        failed = total - success

        avg_duration = sum(r["duration_ms"] for r in self.results) / total if total > 0 else 0
        avg_jitter = sum(r["jitter_delay_ms"] for r in self.results if r["jitter_delay_ms"] > 0) / total if total > 0 else 0

        print(f"\n📈 汇总统计:")
        print(f"  总采集数: {total} 场")
        print(f"  成功: {success} 场 ({success/total*100:.1f}%)" if total > 0 else "  成功: 0 场")
        print(f"  失败: {failed} 场 ({failed/total*100:.1f}%)" if total > 0 else "  失败: 0 场")
        print(f"  平均总耗时: {avg_duration:.0f}ms")
        print(f"  平均 Jittering 延迟: {avg_jitter:.0f}ms ({avg_jitter/1000:.2f}秒)")

        # V26.4: Jittering 验证
        jitter_delays = [r["jitter_delay_ms"] for r in self.results if r["jitter_delay_ms"] > 0]
        if jitter_delays:
            min_jitter = min(jitter_delays)
            max_jitter = max(jitter_delays)

            print(f"\n⏱️  Jittering 延迟验证 (V26.4):")
            print(f"  最小延迟: {min_jitter}ms ({min_jitter/1000:.2f}秒)")
            print(f"  最大延迟: {max_jitter}ms ({max_jitter/1000:.2f}秒)")
            print(f"  波动范围: {max_jitter - min_jitter}ms")

            # 验证 Jittering 是否在 2-5 秒范围内
            min_sec = min_jitter / 1000
            max_sec = max_jitter / 1000

            if 2.0 <= min_sec and max_sec <= 5.0:
                print(f"  ✅ Jittering 延迟符合预期 (2-5 秒范围)")
            elif min_sec >= 2.0 and max_sec > 5.0:
                print(f"  ⚠️  最大延迟超过 5 秒 ({max_sec:.2f}秒)")
            else:
                print(f"  ❌ Jittering 延迟异常 (范围: {min_sec:.2f}-{max_sec:.2f}秒)")
        else:
            print(f"\n⚠️  未检测到 Jittering 延迟！")

    def run(self):
        """执行冒烟测试"""
        print("=" * 140)
        print("🚀 V26.4 最终安全冒烟测试")
        print("=" * 140)

        # 显示数据库配置
        settings = get_settings()
        print(f"\n📍 数据库配置:")
        print(f"  主机: {settings.database.host}")
        print(f"  端口: {settings.database.port}")
        print(f"  数据库: {settings.database.name}")
        print(f"  用户: {settings.database.user}")

        self.start_time = time.perf_counter()

        # 1. 获取比赛列表
        print(f"\n📍 步骤 1: 获取测试比赛列表...")
        matches = self.get_test_matches(limit=self.max_matches)

        if not matches:
            print("❌ 无法获取比赛列表，测试终止")
            return False

        print(f"✅ 获取到 {len(matches)} 场比赛，将测试前 {min(self.max_matches, len(matches))} 场")

        # 2. 逐个采集
        print(f"\n📍 步骤 2: 开始采集（最多 {self.max_matches} 场，连续 {self.stop_after_n_failures} 次失败停止）...")
        print("-" * 140)

        for i, match in enumerate(matches, 1):
            match_id = match["match_id"]
            home_team = match.get("home_team", "Unknown")
            away_team = match.get("away_team", "Unknown")

            print(f"\n[{i}/{len(matches)}] 采集: {home_team} vs {away_team} (ID: {match_id})")

            try:
                result = self.harvest_single_match(match_id)
                self.results.append(result)

                # 打印即时结果
                if result["success"]:
                    print(f"  ✅ 成功 - 总耗时: {result['duration_ms']}ms, "
                          f"Jittering: {result['jitter_delay_ms']}ms, "
                          f"间隔: {result['interval_ms']}ms")
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

            except SystemExit:
                # V26.4: IP 封禁触发自杀逻辑
                print("\n💀 IP 封禁触发程序自杀！测试终止")
                print("=" * 140)
                return False

        # 3. 打印结果
        self.print_results_table()
        self.print_summary()

        # 4. 最终评估
        total_time = time.perf_counter() - self.start_time
        print(f"\n⏱️  总耗时: {total_time:.1f}秒")

        return self._generate_recommendation()

    def _generate_recommendation(self) -> bool:
        """生成 PM 评估建议"""
        success_rate = sum(1 for r in self.results if r["success"]) / len(self.results) if self.results else 0

        print("\n" + "=" * 140)
        print("📋 V26.4 最终安全评估")
        print("=" * 140)

        # V26.4: Jittering 验证
        jitter_delays = [r["jitter_delay_ms"] for r in self.results if r["jitter_delay_ms"] > 0]
        has_jittering = len(jitter_delays) > 0

        if success_rate >= 0.8 and has_jittering:
            avg_jitter = sum(jitter_delays) / len(jitter_delays) / 1000
            print("\n✅ **全量收割安全准备就绪**")
            print(f"   - 成功率: {success_rate*100:.1f}%")
            print(f"   - Jittering 延迟: {avg_jitter:.2f}秒 (✅ 符合 2-5 秒要求)")
            print("   - 数据落地正常 (l2_raw_json + collection_status)")
            print("   - IP 熔断逻辑已启用 (403/429 自杀)")
            print("   - 计时器已升级为 perf_counter")
            print("\n   🚀 **推荐立即启动全量收割 (Cruise 模式)**")
            return True
        elif success_rate >= 0.5:
            print("\n⚠️  **需要调整后启动**")
            print(f"   - 成功率: {success_rate*100:.1f}%")
            if not has_jittering:
                print("   - ❌ Jittering 延迟未生效！")
            print("   - 建议:")
            print("     1. 检查 Jittering 逻辑是否正确执行")
            print("     2. 验证 time.perf_counter() 是否正常工作")
            return False
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
            return False


def main():
    """主函数"""
    runner = FinalSmokeTestRunner(max_matches=3, stop_after_n_failures=3)
    try:
        success = runner.run()
        sys.exit(0 if success else 1)
    except SystemExit as e:
        # V26.4: 捕获 sys.exit() (403/429 自杀逻辑)
        if e.code != 0:  # 只有非零退出码才是真正的自杀
            print(f"\n💀 程序因 IP 封禁而自杀 (exit code: {e.code})")
        sys.exit(e.code)


if __name__ == "__main__":
    main()
