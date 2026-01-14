#!/usr/bin/env python3
"""
V41.63: 物理链路对齐 - 全链路连通性测试
==========================================
用途: 验证 6 个代理端口 (7891-7896) 的连通性和 IP 唯一性
"""

import asyncio
import socket
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# V41.67: Import from centralized config
from src.services.harvest_config import AntiScrapingConfig


class V41_63_ProxyChecker:
    """V41.63: 代理连通性检查器"""

    # WSL2 代理配置（与 Clash 脚本严格一致）
    WSL2_PROXY_HOST = "172.25.16.1"
    # V41.67: Use centralized config
    PROXY_PORTS = AntiScrapingConfig.PROXY_PORTS

    # 测试端点
    IP_CHECK_URLS = [
        "http://ip-api.com/json/",
        "http://ifconfig.me/ip",
        "https://api.ipify.org?format=text",
        "http://icanhazip.com",
    ]

    # 超时配置
    TIMEOUT = 10  # 秒

    def __init__(self):
        self.results = []
        self.start_time = datetime.now()

    def log_banner(self, text: str, char: str = "="):
        """打印横幅"""
        width = 80
        print(f"\n{char * width}")
        print(f"{text:^{width}}")
        print(f"{char * width}\n")

    def log_info(self, text: str):
        """打印信息"""
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {text}")

    def log_success(self, text: str):
        """打印成功信息"""
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ {text}")

    def log_warning(self, text: str):
        """打印警告"""
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️  {text}")

    def log_error(self, text: str):
        """打印错误"""
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ {text}")

    def check_port_connectivity(self, port: int) -> bool:
        """检查端口 TCP 连通性

        Args:
            port: 代理端口

        Returns:
            True 如果端口可连接
        """
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex((self.WSL2_PROXY_HOST, port))
            sock.close()
            return result == 0
        except Exception:
            return False

    def get_external_ip(self, port: int) -> dict[str, Any]:
        """通过代理获取外部 IP

        Args:
            port: 代理端口

        Returns:
            结果字典 {"ip": str, "country": str, "status": str, "error": str}
        """
        result = {
            "port": port,
            "status": "unknown",
            "ip": None,
            "country": None,
            "region": None,
            "error": None
        }

        proxy_url = f"http://{self.WSL2_PROXY_HOST}:{port}"

        # 创建带重试的 session
        session = requests.Session()
        retry = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[500, 502, 503, 504]
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount('http://', adapter)
        session.mount('https://', adapter)

        # 尝试不同的端点
        for url in self.IP_CHECK_URLS:
            try:
                response = session.get(
                    url,
                    proxies={
                        "http": proxy_url,
                        "https": proxy_url
                    },
                    timeout=self.TIMEOUT,
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                    }
                )

                if response.status_code == 200:
                    content = response.text.strip()

                    # 解析响应
                    if "ip-api.com" in url:
                        data = response.json()
                        result["ip"] = data.get("query")
                        result["country"] = data.get("country")
                        result["region"] = data.get("regionName")
                        result["status"] = "ok"
                        break
                    else:
                        # 纯 IP 响应
                        result["ip"] = content
                        result["status"] = "ok"
                        break

            except requests.exceptions.ProxyError as e:
                result["error"] = f"代理错误: {str(e)}"
                result["status"] = "proxy_error"
                break
            except requests.exceptions.Timeout:
                result["error"] = "请求超时"
                result["status"] = "timeout"
                continue
            except requests.exceptions.RequestException as e:
                result["error"] = f"请求失败: {str(e)}"
                result["status"] = "error"
                continue
            except Exception as e:
                result["error"] = f"未知错误: {str(e)}"
                result["status"] = "unknown_error"
                break

        return result

    def check_single_port(self, port: int) -> dict[str, Any]:
        """检查单个端口

        Args:
            port: 代理端口

        Returns:
            检查结果字典
        """
        self.log_info(f"正在检查端口 {port}...")

        result = {
            "port": port,
            "tcp_connected": False,
            "ip_info": None
        }

        # 步骤 1: TCP 连通性检查
        if not self.check_port_connectivity(port):
            self.log_error(f"端口 {port} - TCP 连接失败")
            result["tcp_connected"] = False
            return result

        result["tcp_connected"] = True
        self.log_success(f"端口 {port} - TCP 连接成功")

        # 步骤 2: 外部 IP 获取
        ip_info = self.get_external_ip(port)
        result["ip_info"] = ip_info

        if ip_info["status"] == "ok":
            ip = ip_info["ip"]
            country = ip_info.get("country", "Unknown")
            region = ip_info.get("region", "")

            self.log_success(
                f"端口 {port} - IP: {ip} | "
                f"国家: {country} {f'({region})' if region else ''}"
            )
        else:
            self.log_error(f"端口 {port} - 获取 IP 失败: {ip_info.get('error', 'Unknown')}")

        return result

    def run_all_checks(self):
        """运行所有端口检查"""
        self.log_banner("V41.63 物理链路对齐 - 代理连通性测试", "═")

        print(f"🔍 测试配置:")
        print(f"   代理主机: {self.WSL2_PROXY_HOST}")
        print(f"   测试端口: {self.PROXY_PORTS}")
        print(f"   超时时间: {self.TIMEOUT} 秒")
        print(f"\n📋 开始测试...\n")

        # 逐个测试端口
        for port in self.PROXY_PORTS:
            result = self.check_single_port(port)
            self.results.append(result)
            time.sleep(1)  # 端口间延迟，避免过快请求

        # 生成报告
        self._generate_report()

    def _generate_report(self):
        """生成测试报告"""
        self.log_banner("V41.63 链路健康报告", "═")

        # 统计结果
        tcp_connected = sum(1 for r in self.results if r["tcp_connected"])
        ip_retrieved = sum(1 for r in self.results if r["ip_info"] and r["ip_info"]["status"] == "ok")

        # 收集所有 IP
        ips = []
        for r in self.results:
            if r["ip_info"] and r["ip_info"]["status"] == "ok":
                ips.append({
                    "port": r["port"],
                    "ip": r["ip_info"]["ip"],
                    "country": r["ip_info"].get("country", "Unknown")
                })

        # 检查 IP 重复
        ip_set = set(ip["ip"] for ip in ips)
        has_duplicates = len(ips) != len(ip_set)

        # 打印详细结果
        print(f"\n┌{'─' * 79}┐")
        print(f"│ {'端口':^8} │ {'TCP 连接':^12} │ {'IP 地址':^20} │ {'国家/地区':^25} │")
        print(f"├{'─' * 79}┤")

        for result in self.results:
            port = result["port"]
            tcp_status = "✅ 成功" if result["tcp_connected"] else "❌ 失败"

            if result["ip_info"] and result["ip_info"]["status"] == "ok":
                ip = result["ip_info"]["ip"]
                country = result["ip_info"].get("country", "Unknown")
                region = result["ip_info"].get("region", "")
                location = f"{country} {f'({region})' if region else ''}"
            else:
                ip = "N/A"
                location = result["ip_info"].get("error", "Unknown")[:20] if result["ip_info"] else "N/A"

            # 检查 IP 是否重复
            ip_display = ip
            if ip != "N/A" and has_duplicates:
                count = sum(1 for i in ips if i["ip"] == ip)
                if count > 1:
                    ip_display = f"{ip} ⚠️  重复"

            print(f"│ {port:^8} │ {tcp_status:^12} │ {ip_display:^20} │ {location:^25} │")

        print(f"└{'─' * 79}┘")

        # 打印汇总统计
        print(f"\n📊 汇总统计:")
        print(f"   TCP 连接成功率: {tcp_connected}/{len(self.PROXY_PORTS)} ({tcp_connected/len(self.PROXY_PORTS)*100:.1f}%)")
        print(f"   IP 获取成功率: {ip_retrieved}/{len(self.PROXY_PORTS)} ({ip_retrieved/len(self.PROXY_PORTS)*100:.1f}%)")

        # IP 唯一性检查
        if has_duplicates:
            print(f"\n🚨 警告: 发现 IP 重复！")
            for ip in ip_set:
                count = sum(1 for i in ips if i["ip"] == ip)
                if count > 1:
                    ports = ", ".join(str(i["port"]) for i in ips if i["ip"] == ip)
                    print(f"   IP {ip} 出现在端口: {ports} ({count} 次)")
        else:
            print(f"\n✅ IP 唯一性检查通过: 所有 {len(ips)} 个端口返回独立 IP")

        # 最终结论
        print(f"\n{'=' * 80}")
        if tcp_connected == len(self.PROXY_PORTS) and ip_retrieved == len(self.PROXY_PORTS) and not has_duplicates:
            print("🎉 V41.63 链路健康检查: 全部通过！")
            print("   6 个代理端口全部可用，IP 独立，可以开始收割！")
        else:
            print("⚠️  V41.63 链路健康检查: 发现问题")
            if tcp_connected < len(self.PROXY_PORTS):
                print(f"   - {len(self.PROXY_PORTS) - tcp_connected} 个端口无法连接")
            if ip_retrieved < len(self.PROXY_PORTS):
                print(f"   - {len(self.PROXY_PORTS) - ip_retrieved} 个端口无法获取 IP")
            if has_duplicates:
                print(f"   - 发现 IP 重复，代理配置可能有问题")
        print(f"{'=' * 80}\n")

        # 保存结果到文件
        self._save_results()

    def _save_results(self):
        """保存测试结果到文件"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_dir = Path(__file__).parent.parent.parent / "logs"
        log_dir.mkdir(exist_ok=True)
        log_file = log_dir / f"v41_63_proxy_check_{timestamp}.txt"

        with open(log_file, 'w', encoding='utf-8') as f:
            f.write(f"V41.63 代理链路检查报告\n")
            f.write(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"代理主机: {self.WSL2_PROXY_HOST}\n")
            f.write(f"测试端口: {self.PROXY_PORTS}\n")
            f.write(f"\n详细结果:\n")
            f.write(f"{'-' * 80}\n")

            for result in self.results:
                f.write(f"端口 {result['port']}:\n")
                f.write(f"  TCP 连接: {'成功' if result['tcp_connected'] else '失败'}\n")

                if result['ip_info']:
                    ip_info = result['ip_info']
                    f.write(f"  IP 获取状态: {ip_info['status']}\n")
                    if ip_info['status'] == 'ok':
                        f.write(f"  IP 地址: {ip_info['ip']}\n")
                        f.write(f"  国家: {ip_info.get('country', 'Unknown')}\n")
                        f.write(f"  地区: {ip_info.get('region', 'Unknown')}\n")
                    else:
                        f.write(f"  错误: {ip_info.get('error', 'Unknown')}\n")
                f.write("\n")

        self.log_info(f"📄 测试结果已保存: {log_file}")


def main():
    """主函数"""
    checker = V41_63_ProxyChecker()
    checker.run_all_checks()


if __name__ == "__main__":
    main()
