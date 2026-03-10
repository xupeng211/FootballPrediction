#!/usr/bin/env python3
"""
TITAN 巡航控制器 - 全自动作战编排器
=====================================

V4.46.8 工业化巡航系统 - 无人值守运行

核心功能:
    1. 编排完整作战流程: 数据收割 → 特征熔炼 → 预测管道
    2. 子进程健康监控: 捕获退出码，自动告警
    3. 熔断保护: 连续失败自动熔断
    4. 结果通知: 成功/失败自动推送

使用方式:
    # 完整巡航 (收割 + 熔炼 + 预测)
    python scripts/ops/titan_cruise_control.py

    # 仅预测
    python scripts/ops/titan_cruise_control.py --phase predict

    # 干运行模式
    python scripts/ops/titan_cruise_control.py --dry-run

Cron 示例:
    # 每 4 小时运行一次
    0 */4 * * * /usr/bin/python3 /app/scripts/ops/titan_cruise_control.py >> /app/logs/cruise.log 2>&1

@module scripts.ops.titan_cruise_control
@version V4.46.8-CRUISE-CONTROL
@updated 2026-03-11
"""

import argparse
import json
import logging
import os
import subprocess
import sys
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ============================================================================
# 路径配置
# ============================================================================

PROJECT_ROOT = Path(__file__).parent.parent.parent
LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)

sys.path.insert(0, str(PROJECT_ROOT))


# ============================================================================
# 日志配置
# ============================================================================

def setup_logging(verbose: bool = False) -> logging.Logger:
    """配置双重日志输出"""
    logger = logging.getLogger("titan_cruise")
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    logger.handlers.clear()

    formatter = logging.Formatter(
        fmt="[%(asctime)s] [%(levelname)s] [titan_cruise] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # 控制台
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.DEBUG if verbose else logging.INFO)
    console.setFormatter(formatter)
    logger.addHandler(console)

    # 文件
    log_file = LOG_DIR / "titan_cruise.log"
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger


logger = setup_logging()


# ============================================================================
# 数据模型
# ============================================================================

class Phase(str, Enum):
    """巡航阶段"""
    HARVEST = "harvest"
    SMELT = "smelt"
    PREDICT = "predict"
    FULL = "full"


@dataclass
class TaskResult:
    """任务执行结果"""
    phase: str
    success: bool
    exit_code: int
    duration_seconds: float
    output: str
    error: str
    timestamp: str


@dataclass
class CruiseReport:
    """巡航报告"""
    started_at: str
    finished_at: str
    total_duration_seconds: float
    phases: List[TaskResult]
    success_count: int
    failure_count: int
    overall_success: bool
    exit_code: int


# ============================================================================
# 巡航控制器
# ============================================================================

class TitanCruiseController:
    """
    TITAN 巡航控制器 - 全自动作战编排器

    编排流程:
        1. 数据收割 (harvest): 从 FotMob 收割 L2 数据
        2. 特征熔炼 (smelt): 构建 L3 特征向量
        3. 预测管道 (predict): 生成比赛预测

    熔断保护:
        - 连续失败阈值: 3 次
        - 熔断后自动发送告警
    """

    # 熔断配置
    CIRCUIT_BREAKER_THRESHOLD = 3
    CIRCUIT_BREAKER_RESET_SECONDS = 3600  # 1 小时后重置

    def __init__(self, dry_run: bool = False, logger: Optional[logging.Logger] = None):
        self.dry_run = dry_run
        self.logger = logger or logging.getLogger("titan_cruise")
        self.results: List[TaskResult] = []
        self.circuit_breaker_file = LOG_DIR / ".circuit_breaker"

    def _get_command(self, phase: Phase) -> List[str]:
        """获取执行命令"""
        commands = {
            Phase.HARVEST: [
                "node", "scripts/ops/run_production.js",
                "--limit", "100"
            ],
            Phase.SMELT: [
                "node", "scripts/ops/smelt_all.js"
            ],
            Phase.PREDICT: [
                "python3", "scripts/ops/predict_pipeline.py",
                "--limit", "100",
                "--json"
            ],
        }
        return commands.get(phase, [])

    def _check_circuit_breaker(self) -> bool:
        """检查熔断器状态"""
        if not self.circuit_breaker_file.exists():
            return False

        try:
            with open(self.circuit_breaker_file, "r") as f:
                data = json.load(f)

            failure_count = data.get("failure_count", 0)
            last_failure = datetime.fromisoformat(data.get("last_failure", datetime.now().isoformat()))

            # 检查是否超过重置时间
            elapsed = (datetime.now() - last_failure).total_seconds()
            if elapsed > self.CIRCUIT_BREAKER_RESET_SECONDS:
                self._reset_circuit_breaker()
                return False

            return failure_count >= self.CIRCUIT_BREAKER_THRESHOLD

        except Exception:
            return False

    def _record_failure(self):
        """记录失败"""
        try:
            data = {"failure_count": 0, "last_failure": datetime.now().isoformat()}
            if self.circuit_breaker_file.exists():
                with open(self.circuit_breaker_file, "r") as f:
                    data = json.load(f)

            data["failure_count"] = data.get("failure_count", 0) + 1
            data["last_failure"] = datetime.now().isoformat()

            with open(self.circuit_breaker_file, "w") as f:
                json.dump(data, f)

        except Exception as e:
            self.logger.error(f"记录熔断状态失败: {e}")

    def _reset_circuit_breaker(self):
        """重置熔断器"""
        if self.circuit_breaker_file.exists():
            self.circuit_breaker_file.unlink()
        self.logger.info("熔断器已重置")

    def run_phase(self, phase: Phase) -> TaskResult:
        """执行单个阶段"""
        self.logger.info(f"{'='*50}")
        self.logger.info(f"  阶段: {phase.value.upper()}")
        self.logger.info(f"{'='*50}")

        if self.dry_run:
            self.logger.info("[DRY-RUN] 跳过执行")
            return TaskResult(
                phase=phase.value,
                success=True,
                exit_code=0,
                duration_seconds=0,
                output="[DRY-RUN]",
                error="",
                timestamp=datetime.now().isoformat()
            )

        command = self._get_command(phase)
        if not command:
            self.logger.error(f"未知的阶段: {phase}")
            return TaskResult(
                phase=phase.value,
                success=False,
                exit_code=127,
                duration_seconds=0,
                output="",
                error=f"Unknown phase: {phase}",
                timestamp=datetime.now().isoformat()
            )

        start_time = datetime.now()
        self.logger.info(f"执行命令: {' '.join(command)}")

        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=1800,  # 30 分钟超时
                cwd=str(PROJECT_ROOT)
            )

            duration = (datetime.now() - start_time).total_seconds()
            success = result.returncode == 0

            if success:
                self.logger.info(f"✅ 阶段完成: {phase.value} ({duration:.1f}s)")
            else:
                self.logger.error(f"❌ 阶段失败: {phase.value} (exit code: {result.returncode})")
                self._record_failure()

            return TaskResult(
                phase=phase.value,
                success=success,
                exit_code=result.returncode,
                duration_seconds=duration,
                output=result.stdout[:2000] if result.stdout else "",
                error=result.stderr[:1000] if result.stderr else "",
                timestamp=datetime.now().isoformat()
            )

        except subprocess.TimeoutExpired:
            duration = (datetime.now() - start_time).total_seconds()
            self.logger.error(f"⏱️ 阶段超时: {phase.value}")
            self._record_failure()

            return TaskResult(
                phase=phase.value,
                success=False,
                exit_code=124,  # timeout
                duration_seconds=duration,
                output="",
                error="Process timeout after 30 minutes",
                timestamp=datetime.now().isoformat()
            )

        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            self.logger.exception(f"阶段异常: {phase.value} - {e}")
            self._record_failure()

            return TaskResult(
                phase=phase.value,
                success=False,
                exit_code=1,
                duration_seconds=duration,
                output="",
                error=str(e),
                timestamp=datetime.now().isoformat()
            )

    def run(self, phase: Phase = Phase.FULL) -> CruiseReport:
        """执行巡航任务"""
        started_at = datetime.now()

        self.logger.info("")
        self.logger.info("╔" + "═"*58 + "╗")
        self.logger.info("║  🚀 TITAN 巡航控制器 - 全自动作战编排器          ║")
        self.logger.info("║  CRUISE CONTROL - UNATTENDED OPERATION           ║")
        self.logger.info("╚" + "═"*58 + "╝")
        self.logger.info(f"  启动时间: {started_at.isoformat()}")
        self.logger.info(f"  模式: {phase.value.upper()}")
        self.logger.info("")

        # 检查熔断器
        if self._check_circuit_breaker():
            self.logger.error("🔴 熔断器已触发 - 跳过巡航")
            self._send_alert("熔断器已触发", "连续失败次数超过阈值，巡航已暂停")
            return CruiseReport(
                started_at=started_at.isoformat(),
                finished_at=datetime.now().isoformat(),
                total_duration_seconds=0,
                phases=[],
                success_count=0,
                failure_count=0,
                overall_success=False,
                exit_code=3  # 熔断器触发
            )

        # 确定执行阶段
        if phase == Phase.FULL:
            phases_to_run = [Phase.HARVEST, Phase.SMELT, Phase.PREDICT]
        elif phase == Phase.PREDICT:
            phases_to_run = [Phase.PREDICT]
        elif phase == Phase.HARVEST:
            phases_to_run = [Phase.HARVEST]
        elif phase == Phase.SMELT:
            phases_to_run = [Phase.SMELT]
        else:
            phases_to_run = [phase]

        # 执行各阶段
        self.results = []
        for p in phases_to_run:
            result = self.run_phase(p)
            self.results.append(result)

            # 如果某阶段失败，停止后续阶段
            if not result.success:
                self.logger.error(f"阶段 {p.value} 失败，停止巡航")
                break

        finished_at = datetime.now()
        total_duration = (finished_at - started_at).total_seconds()

        success_count = sum(1 for r in self.results if r.success)
        failure_count = sum(1 for r in self.results if not r.success)
        overall_success = failure_count == 0

        # 生成报告
        report = CruiseReport(
            started_at=started_at.isoformat(),
            finished_at=finished_at.isoformat(),
            total_duration_seconds=total_duration,
            phases=self.results,
            success_count=success_count,
            failure_count=failure_count,
            overall_success=overall_success,
            exit_code=0 if overall_success else 1
        )

        # 保存报告
        self._save_report(report)

        # 发送通知
        if overall_success:
            self._send_success_notification(report)
        else:
            self._send_alert("巡航任务失败", self._format_failure_report(report))

        # 打印摘要
        self._print_summary(report)

        return report

    def _save_report(self, report: CruiseReport):
        """保存巡航报告"""
        report_file = LOG_DIR / f"cruise_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(asdict(report), f, indent=2, ensure_ascii=False)
        self.logger.info(f"报告已保存: {report_file}")

    def _send_alert(self, title: str, message: str):
        """发送告警通知"""
        try:
            from src.utils.notifier import Notifier
            notifier = Notifier()
            notifier.alert(title, message)
        except ImportError:
            self.logger.warning("通知模块未安装，跳过告警")

        # 同时写入告警日志
        alert_file = LOG_DIR / "alerts.log"
        with open(alert_file, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().isoformat()}] 🔴 {title}\n{message}\n\n")

    def _send_success_notification(self, report: CruiseReport):
        """发送成功通知"""
        try:
            from src.utils.notifier import Notifier
            notifier = Notifier()
            notifier.notify(
                "🟢 TITAN 巡航完成",
                f"耗时: {report.total_duration_seconds:.1f}s | 成功: {report.success_count}/{len(report.phases)}"
            )
        except ImportError:
            pass

    def _format_failure_report(self, report: CruiseReport) -> str:
        """格式化失败报告"""
        lines = [f"总耗时: {report.total_duration_seconds:.1f}s", ""]
        for r in report.phases:
            status = "✅" if r.success else "❌"
            lines.append(f"{status} {r.phase}: exit_code={r.exit_code}, duration={r.duration_seconds:.1f}s")
            if r.error:
                lines.append(f"   错误: {r.error[:200]}")
        return "\n".join(lines)

    def _print_summary(self, report: CruiseReport):
        """打印巡航摘要"""
        self.logger.info("")
        self.logger.info("╔" + "═"*58 + "╗")
        self.logger.info("║  📊 巡航摘要                                      ║")
        self.logger.info("╚" + "═"*58 + "╝")
        self.logger.info(f"  状态: {'🟢 成功' if report.overall_success else '🔴 失败'}")
        self.logger.info(f"  耗时: {report.total_duration_seconds:.1f} 秒")
        self.logger.info(f"  阶段: {report.success_count}/{len(report.phases)} 成功")
        self.logger.info("")

        for r in report.phases:
            status = "✅" if r.success else "❌"
            self.logger.info(f"  {status} {r.phase}: {r.duration_seconds:.1f}s (exit: {r.exit_code})")

        self.logger.info("")
        self.logger.info("="*60)


# ============================================================================
# CLI 入口
# ============================================================================

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="TITAN 巡航控制器 - 全自动作战编排器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 完整巡航 (收割 + 熔炼 + 预测)
  python scripts/ops/titan_cruise_control.py

  # 仅预测
  python scripts/ops/titan_cruise_control.py --phase predict

  # 干运行模式
  python scripts/ops/titan_cruise_control.py --dry-run

Cron 配置:
  # 每 4 小时运行一次
  0 */4 * * * cd /app && python3 scripts/ops/titan_cruise_control.py >> logs/cruise.log 2>&1

退出码:
  0 - 全部成功
  1 - 部分失败
  2 - 配置错误
  3 - 熔断器触发
        """
    )
    parser.add_argument(
        "--phase",
        choices=["harvest", "smelt", "predict", "full"],
        default="full",
        help="执行阶段 (默认: full)"
    )
    parser.add_argument("--dry-run", action="store_true", help="干运行模式，不实际执行")
    parser.add_argument("-v", "--verbose", action="store_true", help="详细日志模式")
    return parser.parse_args()


def main():
    """主入口"""
    global logger
    args = parse_args()
    logger = setup_logging(args.verbose)

    try:
        controller = TitanCruiseController(dry_run=args.dry_run, logger=logger)
        phase = Phase(args.phase)
        report = controller.run(phase)
        sys.exit(report.exit_code)

    except KeyboardInterrupt:
        logger.warning("用户中断执行")
        sys.exit(130)

    except Exception as e:
        logger.exception(f"未捕获的异常: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
