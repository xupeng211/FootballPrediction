#!/usr/bin/env python3
"""
2026 赛程自动监听器 (2026 Fixtures Auto Watcher)
================================================

功能:
1. 每 4 小时检查一次 FotMob API 是否有 2026 年赛程数据
2. 一旦检测到数据，自动触发跨年更新编排器
3. 预测完成后通过 AlertManager 发送邮件通知

运行方式:
    # 前台运行（测试）
    python scripts/production/watch_2026_api.py

    # 后台运行（生产）
    nohup python scripts/production/watch_2026_api.py > logs/watch_2026.log 2>&1 &

    # 使用 systemd 服务（推荐）
    sudo systemctl enable football-watcher@$(whoami).service
    sudo systemctl start football-watcher@$(whoami).service

Author: Senior DevOps Engineer
Version: 1.0.0
Date: 2025-12-31
"""

import asyncio
import logging
import os
import signal
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import aiohttp

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.config_unified import get_settings
from src.ops.alert_manager import AlertManager, AlertSeverity

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(PROJECT_ROOT / "logs" / "watch_2026.log"),
    ],
)
logger = logging.getLogger(__name__)

# ============================================================================
# 配置
# ============================================================================

# 五大联赛配置
TARGET_LEAGUES = [
    (47, "Premier League"),
    (87, "La Liga"),
    (82, "Bundesliga"),
    (73, "Serie A"),
    (71, "Ligue 1"),
]

SEASON_2026 = "2526"  # 2025/2026 赛季

# 监听间隔（秒）
CHECK_INTERVAL = 4 * 60 * 60  # 4 小时

# API 端点
API_BASE_URL = "https://www.fotmob.com/api/leagues"

# 状态文件（记录是否已触发过）
STATE_FILE = PROJECT_ROOT / "data" / "watch_2026_state.txt"

# ============================================================================
# 监听器类
# ============================================================================


class Fixtures2026Watcher:
    """
    2026 赛程自动监听器

    工作流程:
    1. 每 4 小时调用一次 FotMob API
    2. 检查是否有 2026-01-01 之后的比赛
    3. 如果有数据，触发完整更新流程
    4. 发送邮件通知
    """

    def __init__(self, check_interval: int = CHECK_INTERVAL):
        """初始化监听器"""
        self.settings = get_settings()
        self.check_interval = check_interval
        self.alert_manager = AlertManager()
        self._running = True
        self._orchestrator_triggered = False

        # 确保状态文件目录存在
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)

        # 读取之前的状态
        self._load_state()

    def _load_state(self) -> None:
        """加载状态文件"""
        if STATE_FILE.exists():
            try:
                content = STATE_FILE.read_text().strip()
                if content == "triggered":
                    logger.info("检测到之前已触发过编排器，将跳过自动触发")
                    self._orchestrator_triggered = True
            except Exception as e:
                logger.warning(f"读取状态文件失败: {e}")

    def _save_state(self, state: str) -> None:
        """保存状态文件"""
        try:
            STATE_FILE.write_text(state)
        except Exception as e:
            logger.error(f"保存状态文件失败: {e}")

    async def _check_2026_fixtures(self, session: aiohttp.ClientSession, league_id: int, league_name: str) -> int:
        """
        检查单个联赛的 2026 赛程

        Args:
            session: aiohttp 会话
            league_id: 联赛 ID
            league_name: 联赛名称

        Returns:
            该联赛 2026 年的比赛数量
        """
        url = API_BASE_URL
        params = {
            "id": str(league_id),
            "season": SEASON_2026,
        }

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json",
            "Referer": "https://www.fotmob.com/",
        }

        try:
            async with session.get(url, params=params, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status == 200:
                    data = await response.json()
                    matches = data.get("matches", [])

                    # 筛选 2026-01-01 之后的比赛
                    count_2026 = 0
                    for match in matches:
                        match_date_str = match.get("status", {}).get("starttimeStr", "")
                        if match_date_str:
                            try:
                                match_date = datetime.fromisoformat(match_date_str.replace("+00:00", "+00:00"))
                                if match_date.year >= 2026:
                                    count_2026 += 1
                            except ValueError:
                                continue

                    if count_2026 > 0:
                        logger.info(f"✓ {league_name}: 发现 {count_2026} 场 2026 年比赛")

                    return count_2026

                elif response.status == 404:
                    logger.debug(f"⏳ {league_name}: 2026 赛季尚未开放")
                    return 0
                else:
                    logger.warning(f"⚠️  {league_name}: HTTP {response.status}")
                    return 0

        except asyncio.TimeoutError:
            logger.error(f"❌ {league_name}: 请求超时")
            return 0
        except Exception as e:
            logger.error(f"❌ {league_name}: {e}")
            return 0

    async def _check_all_leagues(self) -> int:
        """
        检查所有联赛的 2026 赛程

        Returns:
            总共发现的 2026 年比赛数量
        """
        total_count = 0

        async with aiohttp.ClientSession() as session:
            tasks = []
            for league_id, league_name in TARGET_LEAGUES:
                task = self._check_2026_fixtures(session, league_id, league_name)
                tasks.append((league_name, task))

            for league_name, task in tasks:
                count = await task
                total_count += count

        return total_count

    async def _trigger_orchestrator(self) -> bool:
        """
        触发跨年更新编排器

        Returns:
            是否成功触发并完成
        """
        logger.info("")
        logger.info("=" * 60)
        logger.info("🎯 触发跨年数据更新编排器")
        logger.info("=" * 60)

        orchestrator_path = PROJECT_ROOT / "scripts" / "production" / "trans_year_update_orchestrator.py"

        try:
            # 执行编排器
            result = subprocess.run(
                [sys.executable, str(orchestrator_path)],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                timeout=1800,  # 30 分钟超时
            )

            # 输出日志
            if result.stdout:
                for line in result.stdout.split("\n"):
                    if line.strip():
                        logger.info(line)

            if result.stderr:
                for line in result.stderr.split("\n"):
                    if line.strip() and "level=warning" not in line.lower():
                        logger.warning(line)

            success = result.returncode == 0

            if success:
                logger.info("✓ 跨年更新编排器执行成功")

                # 保存状态
                self._save_state("triggered")
                self._orchestrator_triggered = True

            else:
                logger.error(f"✗ 跨年更新编排器执行失败 (退出码: {result.returncode})")

            return success

        except subprocess.TimeoutExpired:
            logger.error("✗ 跨年更新编排器执行超时")
            return False
        except Exception as e:
            logger.error(f"✗ 跨年更新编排器执行异常: {e}")
            return False

    async def _send_success_notification(self, total_matches: int, prediction_file: str) -> None:
        """
        发送成功通知

        Args:
            total_matches: 抓取到的比赛总数
            prediction_file: 预测结果文件路径
        """
        # 读取预测摘要
        summary_file = prediction_file.replace(".csv", "_summary.txt")
        summary_content = ""
        if Path(summary_file).exists():
            try:
                summary_content = Path(summary_file).read_text(encoding="utf-8")
            except Exception:
                pass

        # 构建邮件内容
        message = f"""
🎉 <b>2026 实战预测已就绪！</b>

<hr>

<h3>数据统计</h3>
<ul>
    <li><b>抓取时间</b>: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</li>
    <li><b>抓取场次</b>: {total_matches} 场</li>
    <li><b>数据来源</b>: FotMob API</li>
</ul>

<h3>预测文件</h3>
<ul>
    <li><b>预测结果</b>: <code>{prediction_file}</code></li>
    <li><b>摘要报告</b>: <code>{summary_file}</code></li>
</ul>

<h3>下一步</h3>
<ol>
    <li>查看预测结果文件，分析高价值投注信号</li>
    <li>使用 <code>scripts/production/update_live_ledger.py</code> 开始每日对账</li>
    <li>监控预测准确率，及时调整策略</li>
</ol>

<hr>
<p style="color: #6c757d; font-size: 12px;">
    FootballPrediction 自动监听系统 | V26.8 Production<br>
    本邮件由 2026 赛程自动监听器发送
</p>
"""

        # 读取摘要内容作为附件
        if summary_content:
            message += f"""
<h3>预测摘要</h3>
<pre style="background-color: #f8f9fa; padding: 10px; border-radius: 5px;">
{summary_content}
</pre>
"""

        await self.alert_manager.send_alert(
            title="🎉 2026 实战预测已就绪",
            message=message,
            severity=AlertSeverity.INFO,
            alert_type="2026_predictions_ready",
            metadata={
                "total_matches": str(total_matches),
                "prediction_file": prediction_file,
                "triggered_at": datetime.now().isoformat(),
            }
        )

        logger.info("✓ 成功通知已发送")

    async def run_once(self) -> bool:
        """
        执行一次检查

        Returns:
            是否检测到 2026 数据并完成处理
        """
        logger.info("")
        logger.info("=" * 60)
        logger.info("🔍 检查 2026 赛程数据")
        logger.info("=" * 60)
        logger.info(f"检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"目标联赛: {[name for _, name in TARGET_LEAGUES]}")
        logger.info("")

        # 检查所有联赛
        total_count = await self._check_all_leagues()

        logger.info("")
        logger.info("=" * 60)
        logger.info(f"检查结果: 共发现 {total_count} 场 2026 年比赛")
        logger.info("=" * 60)

        if total_count > 0:
            logger.info("🎯 检测到 2026 年数据，准备触发更新流程...")

            # 如果已经触发过，跳过
            if self._orchestrator_triggered:
                logger.info("⏭️  编排器已在之前触发过，跳过本次执行")
                logger.info("💡 提示: 如需重新触发，请删除状态文件:")
                logger.info(f"   rm {STATE_FILE}")
                return False

            # 触发编排器
            success = await self._trigger_orchestrator()

            if success:
                # 检查预测文件
                prediction_file = PROJECT_ROOT / "predictions" / "v26_smart_predict_results.csv"

                if prediction_file.exists():
                    logger.info(f"✓ 预测文件已生成: {prediction_file}")

                    # 发送通知
                    await self._send_success_notification(total_count, str(prediction_file))

                    return True
                else:
                    logger.warning("⚠️  预测文件未生成，可能流程未完全成功")
                    return False
            else:
                logger.error("❌ 编排器执行失败，未生成预测")
                return False
        else:
            logger.info("⏳ 暂未发现 2026 年数据，将继续监听...")
            return False

    async def run(self) -> None:
        """持续运行监听器"""
        logger.info("")
        logger.info("=" * 60)
        logger.info("2026 赛程自动监听器启动")
        logger.info("=" * 60)
        logger.info(f"检查间隔: {self.check_interval // 3600} 小时")
        logger.info(f"状态文件: {STATE_FILE}")
        logger.info("")

        # 注册信号处理
        loop = asyncio.get_event_loop()

        def signal_handler():
            logger.info("收到停止信号，正在优雅退出...")
            self._running = False

        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, signal_handler)

        # 首次检查
        await self.run_once()

        # 持续监听
        check_count = 1
        while self._running:
            try:
                # 等待下次检查
                logger.info("")
                logger.info(f"⏰ 下次检查时间: {(datetime.now().timestamp() + self.check_interval)}")
                logger.info(f"   即 {datetime.fromtimestamp(datetime.now().timestamp() + self.check_interval).strftime('%Y-%m-%d %H:%M:%S')}")

                await asyncio.sleep(self.check_interval)

                if not self._running:
                    break

                check_count += 1
                logger.info("")
                logger.info("=" * 60)
                logger.info(f"第 {check_count} 次检查")
                logger.info("=" * 60)

                await self.run_once()

            except asyncio.CancelledError:
                logger.info("监听器已取消")
                break
            except Exception as e:
                logger.error(f"监听器异常: {e}", exc_info=True)
                # 继续运行，不退出

        logger.info("2026 赛程自动监听器已停止")


# ============================================================================
# 主函数
# ============================================================================


async def main():
    """主函数"""
    # 解析命令行参数
    import argparse

    parser = argparse.ArgumentParser(description="2026 赛程自动监听器")
    parser.add_argument("--once", action="store_true", help="只执行一次检查")
    parser.add_argument("--interval", type=int, default=CHECK_INTERVAL, help="检查间隔（秒）")
    parser.add_argument("--reset-state", action="store_true", help="重置状态文件")
    args = parser.parse_args()

    # 重置状态
    if args.reset_state:
        if STATE_FILE.exists():
            STATE_FILE.unlink()
            logger.info("✓ 状态文件已删除")
        else:
            logger.info("状态文件不存在，无需删除")
        return

    # 创建监听器
    watcher = Fixtures2026Watcher(check_interval=args.interval)

    if args.once:
        # 只执行一次
        success = await watcher.run_once()
        sys.exit(0 if success else 1)
    else:
        # 持续监听
        await watcher.run()


if __name__ == "__main__":
    asyncio.run(main())
