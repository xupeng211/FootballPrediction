#!/usr/bin/env python3
"""
V26.5 复工自检脚本 - IP 冷却期后的健康检查
==============================================

功能：
    A. 检查当前时间是否已过 COLLECTION_PAUSE_UNTIL
    B. 尝试极小规模抓取（1场）验证 IP 连通性
    C. 验证入库的 l2_raw_json 和特征是否完整

使用场景：
    - 2026-01-09 冷却期结束后执行
    - 验证 IP 是否解封
    - 验证数据采集是否正常

Author: TDD Expert & SRE Architect
Version: V26.5
Date: 2026-01-06
"""

from __future__ import annotations

import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import psycopg2
from psycopg2.extras import RealDictCursor

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.config_unified import get_settings
from src.api.collectors.fotmob_core import FotMobCoreCollector
from src.api.collectors.failover_collector import FailoverCollector

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("logs/v26_5_resume_check.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# ============================================================================
# 复工自检器
# ============================================================================

class ResumeCheckResult:
    """复工自检结果"""

    def __init__(
        self,
        cooling_period_passed: bool = False,
        ip_connected: bool = False,
        data_complete: bool = False,
        errors: list[str] | None = None,
    ):
        self.cooling_period_passed = cooling_period_passed
        self.ip_connected = ip_connected
        self.data_complete = data_complete
        self.errors = errors or []

    @property
    def is_success(self) -> bool:
        """自检是否成功"""
        return (
            self.cooling_period_passed and
            self.ip_connected and
            self.data_complete
        )

    def get_summary(self) -> dict[str, Any]:
        """获取自检摘要"""
        return {
            "cooling_period_passed": self.cooling_period_passed,
            "ip_connected": self.ip_connected,
            "data_complete": self.data_complete,
            "is_success": self.is_success,
            "errors": self.errors,
        }


class ResumeChecker:
    """
    V26.5 复工自检器

    功能：
        1. 检查冷却期是否结束
        2. 测试 IP 连通性（1场采集）
        3. 验证数据完整性
    """

    def __init__(self):
        """初始化复工自检器"""
        self.settings = get_settings()
        self.collector = FotMobCoreCollector()

    def check_cooling_period(self) -> tuple[bool, str | None]:
        """
        A. 检查冷却期是否结束

        Returns:
            (是否已过期, 错误信息)
        """
        logger.info("="*80)
        logger.info("📅 检查冷却期状态")
        logger.info("="*80)

        pause_until_str = os.getenv("COLLECTION_PAUSE_UNTIL")

        if not pause_until_str:
            logger.warning("⚠️  未设置 COLLECTION_PAUSE_UNTIL，认为冷却期已结束")
            return True, None

        try:
            pause_until = datetime.fromisoformat(pause_until_str.replace("Z", "+00:00"))
            current_time = datetime.now().astimezone()

            if current_time < pause_until:
                # 冷却期仍激活
                remaining = pause_until - current_time
                logger.error(f"❌ 冷却期仍激活")
                logger.error(f"   当前时间: {current_time.isoformat()}")
                logger.error(f"   冷却截止: {pause_until.isoformat()}")
                logger.error(f"   剩余时间: {self._format_timedelta(remaining)}")
                return False, f"冷却期仍激活，剩余 {self._format_timedelta(remaining)}"
            else:
                # 冷却期已过期
                elapsed = current_time - pause_until
                logger.info(f"✅ 冷却期已过期")
                logger.info(f"   当前时间: {current_time.isoformat()}")
                logger.info(f"   冷却截止: {pause_until.isoformat()}")
                logger.info(f"   已过期: {self._format_timedelta(elapsed)}")
                return True, None

        except ValueError as e:
            error_msg = f"COLLECTION_PAUSE_UNTIL 格式错误: {e}"
            logger.error(f"❌ {error_msg}")
            return False, error_msg

    def check_ip_connectivity(
        self, match_id: int = 3901276, league_id: int = 47, season: str = "2324"
    ) -> tuple[bool, str | None]:
        """
        B. 测试 IP 连通性（1场采集）

        Args:
            match_id: 测试比赛 ID（默认 3901276）
            league_id: 联赛 ID
            season: 赛季代码

        Returns:
            (是否连通, 错误信息)
        """
        logger.info("="*80)
        logger.info("🌐 测试 IP 连通性")
        logger.info("="*80)

        logger.info(f"📝 测试参数:")
        logger.info(f"   Match ID: {match_id}")
        logger.info(f"   League ID: {league_id}")
        logger.info(f"   Season: {season}")

        try:
            # 使用 Failover 采集器
            collector = FailoverCollector(
                primary_source="fotmob",
                fallback_source="oddsportal",  # 实际不会用到
            )

            success = collector.harvest_match_with_league(
                match_id=match_id,
                league_id=league_id,
                season=season,
            )

            if success:
                logger.info(f"✅ IP 连通性测试成功")
                logger.info(f"   数据源: FotMob")
                logger.info(f"   Match ID: {match_id}")
                return True, None
            else:
                error_msg = "采集失败，IP 可能仍被封禁"
                logger.error(f"❌ {error_msg}")
                return False, error_msg

        except Exception as e:
            error_msg = f"IP 连通性测试异常: {e}"
            logger.error(f"❌ {error_msg}")
            return False, error_msg

    def check_data_integrity(self, match_id: int) -> tuple[bool, str | None]:
        """
        C. 验证数据完整性

        Args:
            match_id: 比赛 ID

        Returns:
            (数据是否完整, 错误信息)
        """
        logger.info("="*80)
        logger.info("🔍 验证数据完整性")
        logger.info("="*80)

        try:
            # 查询数据库
            conn = self._get_db_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            query = """
                SELECT
                    match_id,
                    home_team,
                    away_team,
                    l2_raw_json IS NOT NULL as has_l2_raw,
                    l2_extracted_features IS NOT NULL as has_features,
                    data_source
                FROM matches
                WHERE match_id = %s;
            """

            cursor.execute(query, (match_id,))
            result = cursor.fetchone()

            cursor.close()
            conn.close()

            if not result:
                error_msg = f"未找到 Match ID {match_id} 的记录"
                logger.error(f"❌ {error_msg}")
                return False, error_msg

            has_l2_raw = result["has_l2_raw"]
            has_features = result["has_features"]
            data_source = result["data_source"]

            logger.info(f"📊 数据完整性检查结果:")
            logger.info(f"   Match ID: {result['match_id']}")
            logger.info(f"   比赛: {result['home_team']} vs {result['away_team']}")
            logger.info(f"   数据源: {data_source}")
            logger.info(f"   l2_raw_json: {'✅' if has_l2_raw else '❌'}")
            logger.info(f"   l2_extracted_features: {'✅' if has_features else '❌'}")

            if has_l2_raw and has_features:
                logger.info(f"✅ 数据完整性验证通过")
                return True, None
            else:
                missing = []
                if not has_l2_raw:
                    missing.append("l2_raw_json")
                if not has_features:
                    missing.append("l2_extracted_features")

                error_msg = f"数据不完整，缺少: {', '.join(missing)}"
                logger.error(f"❌ {error_msg}")
                return False, error_msg

        except Exception as e:
            error_msg = f"数据完整性验证异常: {e}"
            logger.error(f"❌ {error_msg}")
            return False, error_msg

    def run_full_check(
        self,
        test_match_id: int = 3901276,
        league_id: int = 47,
        season: str = "2324",
    ) -> ResumeCheckResult:
        """
        执行完整的自检流程

        Args:
            test_match_id: 测试比赛 ID
            league_id: 联赛 ID
            season: 赛季代码

        Returns:
            ResumeCheckResult
        """
        logger.info("")
        logger.info("╔══════════════════════════════════════════════════════════════════════╗")
        logger.info("║         V26.5 复工自检 - IP 冷却期后的健康检查                    ║")
        logger.info("╚══════════════════════════════════════════════════════════════════════╝")
        logger.info("")

        result = ResumeCheckResult()
        errors = []

        # Step A: 检查冷却期
        cooling_passed, cooling_error = self.check_cooling_period()
        result.cooling_period_passed = cooling_passed

        if not cooling_passed:
            errors.append(cooling_error or "冷却期检查失败")
            result.errors = errors
            return result

        # Step B: 测试 IP 连通性
        ip_connected, ip_error = self.check_ip_connectivity(
            match_id=test_match_id,
            league_id=league_id,
            season=season,
        )
        result.ip_connected = ip_connected

        if not ip_connected:
            errors.append(ip_error or "IP 连通性测试失败")

        # Step C: 验证数据完整性（只在 IP 连通时执行）
        if ip_connected:
            data_complete, data_error = self.check_data_integrity(test_match_id)
            result.data_complete = data_complete

            if not data_complete:
                errors.append(data_error or "数据完整性验证失败")

        result.errors = errors

        # 输出最终结果
        logger.info("")
        logger.info("="*80)
        logger.info("📊 复工自检最终结果")
        logger.info("="*80)

        if result.is_success:
            logger.info("✅ 自检全部通过")
            logger.info("   冷却期: 已过期 ✅")
            logger.info("   IP 连通性: 正常 ✅")
            logger.info("   数据完整性: 完整 ✅")
            logger.info("")
            logger.info("🎉 系统已准备好复工！")
            logger.info("")
            logger.info("💡 数据已入库，结构正确，可以开火")
            logger.info("")
            logger.info("🚀 您现在可以安全地执行全量收割：")
            logger.info("   python main.py --source fotmob --mode single --limit 100")
            logger.info("   # 或者巡航模式：")
            logger.info("   python main.py --source fotmob --mode cruise")
        else:
            logger.error("❌ 自检未完全通过")
            logger.error(f"   冷却期: {'✅' if result.cooling_period_passed else '❌'}")
            logger.error(f"   IP 连通性: {'✅' if result.ip_connected else '❌'}")
            logger.error(f"   数据完整性: {'✅' if result.data_complete else '❌'}")

            if errors:
                logger.error("")
                logger.error("错误列表:")
                for i, error in enumerate(errors, 1):
                    logger.error(f"  {i}. {error}")

            logger.info("")
            logger.info("⚠️  建议:")
            if not result.cooling_period_passed:
                logger.info("  - 等待冷却期结束后重试")
            if not result.ip_connected:
                logger.info("  - IP 可能仍被封禁，建议更换代理或延长等待时间")
            if not result.data_complete:
                logger.info("  - 数据完整性验证失败，检查数据库连接")

        logger.info("="*80)

        return result

    # ========================================
    # 辅助方法
    # ========================================

    def _get_db_connection(self):
        """获取数据库连接"""
        return psycopg2.connect(
            host=self.settings.database.host,
            port=self.settings.database.port,
            database=self.settings.database.name,
            user=self.settings.database.user,
            password=self.settings.database.password.get_secret_value(),
            cursor_factory=RealDictCursor,
        )

    @staticmethod
    def _format_timedelta(td) -> str:
        """格式化时间差"""
        total_seconds = int(td.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60

        if hours > 0:
            return f"{hours}小时 {minutes}分钟"
        elif minutes > 0:
            return f"{minutes}分钟 {seconds}秒"
        else:
            return f"{seconds}秒"


# ============================================================================
# 命令行入口
# ============================================================================

def main():
    """命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(
        description="V26.5 复工自检脚本 - IP 冷却期后的健康检查"
    )
    parser.add_argument(
        "--match-id",
        type=int,
        default=3901276,
        help="测试比赛 ID（默认: 3901276）",
    )
    parser.add_argument(
        "--league-id",
        type=int,
        default=47,
        help="联赛 ID（默认: 47 - Premier League）",
    )
    parser.add_argument(
        "--season",
        type=str,
        default="2324",
        help="赛季代码（默认: 2324）",
    )

    args = parser.parse_args()

    # 执行自检
    checker = ResumeChecker()
    result = checker.run_full_check(
        test_match_id=args.match_id,
        league_id=args.league_id,
        season=args.season,
    )

    # 返回退出码
    sys.exit(0 if result.is_success else 1)


if __name__ == "__main__":
    main()
