#!/usr/bin/env python3
"""
V41.266 "Firepower Recon" - 网络节点探测与配置对齐
===================================================

任务背景：
    Windows 端已通过 V41.265 脚本激活了端口 7891-7912 的多端口监听。
    需在 WSL2 中验证哪些端口可顺畅访问 OddsPortal 并更新主干配置。

核心功能：
    1. 矩阵扫描 (Matrix Scan) - 遍历端口 7891-7915
    2. 连通性测试 (Connectivity Test) - 向 oddsportal.com 发送轻量级请求
    3. 自动配置同步 (Auto Config Sync) - 重写 harvester_v2.yaml
    4. 并发承载评估 (Concurrency Audit) - 计算最佳并发数

Usage:
    python scripts/ops/v41_266_firepower_recon.py [--update-config]

Author: V41.266 Network Team
Date: 2026-01-20
Version: V41.266 "Firepower Recon"
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import requests
import yaml

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.config_unified import get_config

# =============================================================================
# 配置与日志
# =============================================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("V41.266_Firepower_Recon")


# =============================================================================
# 数据模型
# =============================================================================


@dataclass
class EndpointTestResult:
    """端点测试结果"""
    port: int
    status: str  # "SUCCESS", "FAILED", "TIMEOUT", "ERROR"
    latency_ms: float = 0.0
    status_code: Optional[int] = None
    error_message: str = ""
    verdict: str = ""  # "COMBAT_READY", "UNUSABLE", "SLOW"

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "Port": self.port,
            "Status": self.status,
            "Latency_ms": round(self.latency_ms, 2),
            "Status_Code": self.status_code,
            "Error": self.error_message,
            "Verdict": self.verdict,
        }


@dataclass
class ReconReport:
    """探测报告"""
    timestamp: str
    target_url: str
    scan_range: tuple[int, int]
    total_tested: int = 0
    combat_ready: int = 0
    unusable: int = 0
    slow: int = 0
    results: List[EndpointTestResult] = field(default_factory=list)
    config_path: str = "config/harvester_v2.yaml"

    def get_combat_ready_ports(self) -> List[int]:
        """获取战斗就绪的端口列表"""
        return [r.port for r in self.results if r.verdict == "COMBAT_READY"]


# =============================================================================
# 核心探测引擎
# =============================================================================


class FirepowerReconEngine:
    """
    V41.266 网络节点探测引擎

    核心功能：
    1. 矩阵扫描 - 遍历所有端口
    2. 连通性测试 - 验证到目标网站的可达性
    3. 性能评估 - 延迟和响应时间分析
    4. 自动配置同步 - 更新 harvester_v2.yaml
    """

    # 目标测试 URL（轻量级页面）
    TEST_URL = "https://www.oddsportal.com"

    # 测试超时（毫秒）
    TIMEOUT_MS = 5000

    # 判定标准
    MAX_LATENCY_MS = 3000.0  # 最大可接受延迟
    MIN_STATUS_CODE = 200
    MAX_STATUS_CODE = 299

    def __init__(self, start_port: int = 7891, end_port: int = 7915):
        """
        初始化探测引擎

        Args:
            start_port: 起始端口
            end_port: 结束端口
        """
        self.start_port = start_port
        self.end_port = end_port
        self.config = get_config()
        self.report = ReconReport(
            timestamp=datetime.now().isoformat(),
            target_url=self.TEST_URL,
            scan_range=(start_port, end_port),
        )

    def _test_endpoint(self, port: int) -> EndpointTestResult:
        """
        测试单个端点

        Args:
            port: 代理端口号

        Returns:
            端点测试结果
        """
        proxy_url = f"http://{self.config.proxy.wsl2_bridge_host}:{port}"

        result = EndpointTestResult(port=port, status="PENDING")

        try:
            start_time = time.time()

            response = requests.get(
                self.TEST_URL,
                proxies={"http": proxy_url, "https": proxy_url},
                timeout=self.TIMEOUT_MS / 1000.0,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                },
            )

            latency_ms = (time.time() - start_time) * 1000.0

            result.latency_ms = latency_ms
            result.status_code = response.status_code

            # 判定标准
            if response.status_code >= self.MIN_STATUS_CODE and response.status_code <= self.MAX_STATUS_CODE:
                if latency_ms <= self.MAX_LATENCY_MS:
                    result.status = "SUCCESS"
                    result.verdict = "COMBAT_READY"
                else:
                    result.status = "SUCCESS"
                    result.verdict = "SLOW"
                    result.error_message = f"Latency {latency_ms:.0f}ms exceeds threshold"
            else:
                result.status = "FAILED"
                result.verdict = "UNUSABLE"
                result.error_message = f"Status code {response.status_code}"

        except requests.exceptions.Timeout:
            result.status = "TIMEOUT"
            result.verdict = "UNUSABLE"
            result.error_message = f"Timeout after {self.TIMEOUT_MS}ms"
            result.latency_ms = self.TIMEOUT_MS

        except requests.exceptions.ConnectionError as e:
            result.status = "FAILED"
            result.verdict = "UNUSABLE"
            result.error_message = f"Connection error: {str(e)[:50]}"

        except Exception as e:
            result.status = "ERROR"
            result.verdict = "UNUSABLE"
            result.error_message = f"Unexpected error: {str(e)[:50]}"

        return result

    def run_matrix_scan(self, concurrent: int = 10) -> ReconReport:
        """
        运行矩阵扫描 - 并发测试所有端口

        Args:
            concurrent: 并发数

        Returns:
            探测报告
        """
        ports_to_test = list(range(self.start_port, self.end_port + 1))
        self.report.total_tested = len(ports_to_test)

        logger.info(f"V41.266: Starting matrix scan of {len(ports_to_test)} ports (concurrent={concurrent})")
        logger.info(f"Target: {self.TEST_URL}")
        logger.info(f"Proxy host: {self.config.proxy.wsl2_bridge_host}")

        results = []

        with ThreadPoolExecutor(max_workers=concurrent) as executor:
            futures = {executor.submit(self._test_endpoint, port): port for port in ports_to_test}

            for future in as_completed(futures):
                port = futures[future]
                try:
                    result = future.result(timeout=10)
                    results.append(result)

                    # 实时输出
                    verdict_symbol = {
                        "COMBAT_READY": "✅",
                        "SLOW": "⚠️",
                        "UNUSABLE": "❌",
                    }.get(result.verdict, "❓")

                    logger.info(
                        f"  Port {port:4d}: {result.status:8s} | "
                        f"{result.latency_ms:6.0f}ms | {verdict_symbol} {result.verdict}"
                    )

                except Exception as e:
                    logger.error(f"  Port {port}: Test error - {e}")
                    results.append(EndpointTestResult(
                        port=port,
                        status="ERROR",
                        verdict="UNUSABLE",
                        error_message=str(e)[:50]
                    ))

        # 排序（按端口号）
        self.report.results = sorted(results, key=lambda r: r.port)

        # 统计
        self.report.combat_ready = sum(1 for r in self.report.results if r.verdict == "COMBAT_READY")
        self.report.unusable = sum(1 for r in self.report.results if r.verdict == "UNUSABLE")
        self.report.slow = sum(1 for r in self.report.results if r.verdict == "SLOW")

        return self.report

    def print_report(self):
        """打印探测报告"""
        print("\n" + "=" * 80)
        print("V41.266 \"Firepower Recon\" - 网络节点探测报告")
        print("=" * 80)
        print(f"时间戳: {self.report.timestamp}")
        print(f"目标 URL: {self.report.target_url}")
        print(f"扫描范围: 端口 {self.report.scan_range[0]}-{self.report.scan_range[1]}")
        print(f"\n📊 总体统计:")
        print(f"  总测试: {self.report.total_tested}")
        print(f"  战斗就绪: {self.report.combat_ready} ✅")
        print(f"  延迟过高: {self.report.slow} ⚠️")
        print(f"  不可用: {self.report.unusable} ❌")
        print(f"\n🔍 详细结果:")
        print("-" * 80)
        print(f"{'Port':>6} | {'Status':<10} | {'Latency':>10} | {'Status':>6} | {'Verdict':<15}")
        print("-" * 80)

        for result in self.report.results:
            verdict_symbol = {
                "COMBAT_READY": "✅",
                "SLOW": "⚠️",
                "UNUSABLE": "❌",
            }.get(result.verdict, "❓")

            print(
                f"{result.port:6d} | {result.status:<10} | "
                f"{result.latency_ms:8.1f}ms | "
                f"{str(result.status_code or 'N/A'):>6} | "
                f"{verdict_symbol} {result.verdict}"
            )

        # 战斗就绪端口列表
        combat_ports = self.report.get_combat_ready_ports()
        if combat_ports:
            print("\n" + "=" * 80)
            print(f"✅ Combat Ready Ports: {combat_ports}")
            print(f"Total Reliable IPs: {len(combat_ports)}")

            # 计算最佳并发数
            optimal_concurrency = max(1, int(len(combat_ports) / 1.5))
            print(f"Optimal Concurrency: {optimal_concurrency}")
        else:
            print("\n" + "=" * 80)
            print("⚠️  Warning: No combat ready ports found!")

        print("=" * 80 + "\n")

    def update_config(self) -> bool:
        """
        自动同步主干配置 - 重写 harvester_v2.yaml

        Returns:
            是否成功更新
        """
        combat_ports = self.report.get_combat_ready_ports()

        if not combat_ports:
            logger.warning("V41.266: No combat ready ports to update config")
            return False

        # 读取现有配置
        config_path = Path(self.report.config_path)
        if not config_path.exists():
            logger.error(f"V41.266: Config file not found: {config_path}")
            return False

        with open(config_path, 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f)

        # 更新代理端口列表
        config_data['proxy']['ports'] = combat_ports

        # 计算并更新最佳并发数
        optimal_concurrency = max(1, int(len(combat_ports) / 1.5))
        config_data['concurrency']['default_workers'] = min(optimal_concurrency, config_data['concurrency']['max_workers'])
        config_data['concurrency']['max_workers'] = max(optimal_concurrency, config_data['concurrency']['default_workers'])

        # 写回配置文件
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config_data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

        logger.info(f"V41.266: Config updated: {config_path}")
        logger.info(f"  - Ports: {combat_ports}")
        logger.info(f"  - Concurrency: {config_data['concurrency']['default_workers']} (default), {config_data['concurrency']['max_workers']} (max)")

        return True


# =============================================================================
# 主程序
# =============================================================================


def main():
    """主程序入口"""
    parser = argparse.ArgumentParser(
        description="V41.266 \"Firepower Recon\" - 网络节点探测与配置对齐"
    )
    parser.add_argument(
        "--start-port",
        type=int,
        default=7891,
        help="起始端口（默认: 7891）"
    )
    parser.add_argument(
        "--end-port",
        type=int,
        default=7915,
        help="结束端口（默认: 7915）"
    )
    parser.add_argument(
        "--concurrent",
        type=int,
        default=10,
        help="并发测试数（默认: 10）"
    )
    parser.add_argument(
        "--update-config",
        action="store_true",
        help="自动更新 harvester_v2.yaml 配置文件"
    )

    args = parser.parse_args()

    print("\n" + "=" * 80)
    print("V41.266 \"Firepower Recon\" - 网络节点探测")
    print("=" * 80)
    print(f"扫描范围: 端口 {args.start_port}-{args.end_port}")
    print(f"并发测试: {args.concurrent}")
    print()

    # 创建探测引擎
    engine = FirepowerReconEngine(
        start_port=args.start_port,
        end_port=args.end_port
    )

    # 运行矩阵扫描
    report = engine.run_matrix_scan(concurrent=args.concurrent)

    # 打印报告
    engine.print_report()

    # 自动更新配置
    if args.update_config:
        print("\n" + "=" * 80)
        print("V41.266: 自动配置同步")
        print("=" * 80)

        if engine.update_config():
            print("✅ 配置已更新到 config/harvester_v2.yaml")
        else:
            print("❌ 配置更新失败")

    return 0


if __name__ == "__main__":
    sys.exit(main())
