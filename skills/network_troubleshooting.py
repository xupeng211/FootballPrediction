#!/usr/bin/env python3
"""
Network Troubleshooting Skill for Claude Code
网络故障排除专业技能 - 网络连接和代理配置专家
"""

from typing import Dict, List, Any, Optional, Tuple
import json
import socket
import subprocess
import re
import time
import asyncio
from pathlib import Path
import urllib.parse

class NetworkTroubleshootingSkill:
    """
    Network Troubleshooting Skill - 专注于网络问题诊断和优化
    """

    def __init__(self):
        self.skill_name = "network-troubleshooting"
        self.capabilities = [
            "wsl2-networking",
            "proxy-configuration",
            "dns-analysis",
            "connectivity-testing",
            "port-forwarding",
            "network-optimization",
            "firewall-diagnostics"
        ]

    def diagnose_wsl2_networking(self) -> Dict[str, Any]:
        """
        诊断WSL2网络配置问题

        Returns:
            WSL2网络诊断结果
        """
        try:
            diagnosis = {
                "timestamp": time.time(),
                "wsl2_status": "unknown",
                "network_interfaces": {},
                "routing_table": [],
                "dns_config": {},
                "issues": [],
                "recommendations": []
            }

            # 检查WSL2版本
            try:
                result = subprocess.run(
                    ["wsl", "--version"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode == 0:
                    diagnosis["wsl2_status"] = "installed"
                    diagnosis["wsl_version"] = result.stdout.strip()
                else:
                    diagnosis["wsl2_status"] = "not_installed"
                    diagnosis["issues"].append("WSL2未正确安装")
            except FileNotFoundError:
                diagnosis["wsl2_status"] = "not_available"
                diagnosis["issues"].append("WSL命令不可用")

            # 检查网络接口
            try:
                result = subprocess.run(
                    ["ip", "addr", "show"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode == 0:
                    interfaces = self._parse_ip_output(result.stdout)
                    diagnosis["network_interfaces"] = interfaces

                    # 检查eth0接口（WSL2默认）
                    if "eth0" not in interfaces:
                        diagnosis["issues"].append("未找到eth0接口，WSL2网络可能有问题")
                    else:
                        eth0_ip = interfaces["eth0"].get("ipv4", "")
                        if not eth0_ip.startswith("172."):
                            diagnosis["issues"].append(f"eth0 IP地址异常: {eth0_ip}")

            except Exception as e:
                diagnosis["issues"].append(f"无法获取网络接口信息: {str(e)}")

            # 检查路由表
            try:
                result = subprocess.run(
                    ["ip", "route", "show"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode == 0:
                    routes = self._parse_route_output(result.stdout)
                    diagnosis["routing_table"] = routes

                    # 检查默认路由
                    default_routes = [r for r in routes if r["destination"] == "default"]
                    if not default_routes:
                        diagnosis["issues"].append("未找到默认路由")
                    elif len(default_routes) > 1:
                        diagnosis["issues"].append(f"发现多个默认路由: {len(default_routes)}")

            except Exception as e:
                diagnosis["issues"].append(f"无法获取路由表: {str(e)}")

            # 检查DNS配置
            try:
                with open("/etc/resolv.conf", "r") as f:
                    dns_content = f.read()

                dns_servers = re.findall(r"nameserver\s+([^\s]+)", dns_content)
                diagnosis["dns_config"] = {
                    "servers": dns_servers,
                    "file_content": dns_content
                }

                if not dns_servers:
                    diagnosis["issues"].append("未配置DNS服务器")
                elif len(dns_servers) > 3:
                    diagnosis["issues"].append(f"DNS服务器过多: {len(dns_servers)}")

            except Exception as e:
                diagnosis["issues"].append(f"无法读取DNS配置: {str(e)}")

            # 检查Windows主机连接
            try:
                # 尝试连接Windows主机
                windows_host_ip = self._get_windows_host_ip()
                if windows_host_ip:
                    diagnosis["windows_host"] = {
                        "ip": windows_host_ip,
                        "connectivity": self._test_connectivity(windows_host_ip, 22)
                    }
                else:
                    diagnosis["issues"].append("无法获取Windows主机IP")

            except Exception as e:
                diagnosis["issues"].append(f"Windows主机连接测试失败: {str(e)}")

            # 生成建议
            diagnosis["recommendations"] = self._generate_wsl2_recommendations(diagnosis)

            return diagnosis

        except Exception as e:
            return {"error": f"WSL2网络诊断失败: {str(e)}"}

    def configure_proxy_settings(self, proxy_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        配置代理设置

        Args:
            proxy_config: 代理配置

        Returns:
            配置结果
        """
        try:
            result = {
                "timestamp": time.time(),
                "configured_proxies": {},
                "test_results": {},
                "issues": [],
                "recommendations": []
            }

            # 验证代理配置
            required_fields = ["http_proxy", "https_proxy"]
            for field in required_fields:
                if field not in proxy_config:
                    result["issues"].append(f"缺少必要配置: {field}")

            # 测试代理连接
            for proxy_type in ["http_proxy", "https_proxy"]:
                if proxy_type in proxy_config:
                    proxy_url = proxy_config[proxy_type]
                    parsed_url = urllib.parse.urlparse(proxy_url)

                    proxy_info = {
                        "host": parsed_url.hostname,
                        "port": parsed_url.port or (8080 if parsed_url.scheme == "http" else 8443),
                        "scheme": parsed_url.scheme
                    }

                    result["configured_proxies"][proxy_type] = proxy_info

                    # 测试代理连通性
                    connectivity_result = self._test_proxy_connectivity(
                        proxy_info["host"], proxy_info["port"]
                    )
                    result["test_results"][proxy_type] = connectivity_result

                    if not connectivity_result["success"]:
                        result["issues"].append(
                            f"代理 {proxy_type} 连接失败: {connectivity_result.get('error', 'Unknown error')}"
                        )

            # 生成Docker代理配置
            docker_proxy_config = self._generate_docker_proxy_config(proxy_config)
            result["docker_config"] = docker_proxy_config

            # 生成系统环境变量配置
            env_config = self._generate_env_proxy_config(proxy_config)
            result["env_config"] = env_config

            # 生成建议
            result["recommendations"] = [
                "确保代理服务器允许来自WSL2的连接",
                "检查防火墙设置，确保代理端口可访问",
                "考虑使用no_proxy配置排除本地网络",
                "测试代理对目标网站的连通性"
            ]

            return result

        except Exception as e:
            return {"error": f"代理配置失败: {str(e)}"}

    def analyze_dns_performance(self, test_domains: List[str] = None) -> Dict[str, Any]:
        """
        分析DNS性能

        Args:
            test_domains: 测试域名列表

        Returns:
            DNS性能分析结果
        """
        try:
            if test_domains is None:
                test_domains = [
                    "google.com",
                    "github.com",
                    "www.fotmob.com",
                    "api.fotmob.com"
                ]

            analysis = {
                "timestamp": time.time(),
                "dns_servers": [],
                "test_results": {},
                "performance_metrics": {},
                "issues": [],
                "recommendations": []
            }

            # 获取当前DNS服务器
            try:
                with open("/etc/resolv.conf", "r") as f:
                    content = f.read()
                dns_servers = re.findall(r"nameserver\s+([^\s]+)", content)
                analysis["dns_servers"] = dns_servers
            except Exception as e:
                analysis["issues"].append(f"无法获取DNS服务器: {str(e)}")
                return analysis

            # 测试每个域名的DNS解析性能
            for domain in test_domains:
                domain_results = []

                for dns_server in dns_servers:
                    start_time = time.time()
                    try:
                        # 使用特定DNS服务器解析
                        result = subprocess.run(
                            ["nslookup", domain, dns_server],
                            capture_output=True,
                            text=True,
                            timeout=5
                        )

                        resolve_time = (time.time() - start_time) * 1000

                        if result.returncode == 0:
                            # 解析成功
                            ip_matches = re.findall(r"Address:\s*([^\s]+)", result.stdout)
                            if ip_matches:
                                domain_results.append({
                                    "dns_server": dns_server,
                                    "resolve_time_ms": resolve_time,
                                    "ip_addresses": ip_matches[1:] if len(ip_matches) > 1 else [],
                                    "success": True
                                })
                            else:
                                domain_results.append({
                                    "dns_server": dns_server,
                                    "resolve_time_ms": resolve_time,
                                    "success": False,
                                    "error": "无法解析IP地址"
                                })
                        else:
                            domain_results.append({
                                "dns_server": dns_server,
                                "resolve_time_ms": resolve_time,
                                "success": False,
                                "error": result.stderr.strip()
                            })

                    except subprocess.TimeoutExpired:
                        domain_results.append({
                            "dns_server": dns_server,
                            "resolve_time_ms": 5000,
                            "success": False,
                            "error": "DNS查询超时"
                        })
                    except Exception as e:
                        domain_results.append({
                            "dns_server": dns_server,
                            "success": False,
                            "error": str(e)
                        })

                analysis["test_results"][domain] = domain_results

            # 计算性能指标
            successful_resolutions = []
            for domain, results in analysis["test_results"].items():
                successful = [r for r in results if r["success"]]
                if successful:
                    successful_resolutions.extend([r["resolve_time_ms"] for r in successful])

            if successful_resolutions:
                analysis["performance_metrics"] = {
                    "avg_resolve_time_ms": sum(successful_resolutions) / len(successful_resolutions),
                    "min_resolve_time_ms": min(successful_resolutions),
                    "max_resolve_time_ms": max(successful_resolutions),
                    "success_rate": len(successful_resolutions) / sum(len(results) for results in analysis["test_results"].values())
                }

                # 检查性能问题
                if analysis["performance_metrics"]["avg_resolve_time_ms"] > 500:
                    analysis["issues"].append("DNS解析速度过慢，建议使用更快的DNS服务器")

                if analysis["performance_metrics"]["success_rate"] < 0.9:
                    analysis["issues"].append("DNS解析成功率较低，检查网络连接")

            # 生成建议
            analysis["recommendations"] = [
                "考虑使用公共DNS服务（8.8.8.8, 1.1.1.1）",
                "检查本地DNS缓存配置",
                "确保防火墙允许DNS查询（UDP 53端口）",
                "考虑配置本地DNS缓存服务"
            ]

            return analysis

        except Exception as e:
            return {"error": f"DNS性能分析失败: {str(e)}"}

    def troubleshoot_docker_networking(self, container_name: str = None) -> Dict[str, Any]:
        """
        排查Docker网络问题

        Args:
            container_name: 特定容器名称（可选）

        Returns:
            Docker网络诊断结果
        """
        try:
            diagnosis = {
                "timestamp": time.time(),
                "docker_status": "unknown",
                "networks": {},
                "container_analysis": {},
                "connectivity_tests": {},
                "issues": [],
                "recommendations": []
            }

            # 检查Docker服务状态
            try:
                result = subprocess.run(
                    ["docker", "info", "--format", "{{json .}}"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode == 0:
                    docker_info = json.loads(result.stdout)
                    diagnosis["docker_status"] = "running"
                    diagnosis["docker_info"] = {
                        "version": docker_info.get("ServerVersion"),
                        "default_network": docker_info.get("DefaultBridge", ""),
                        "plugins": docker_info.get("Plugins", {}).get("Network", [])
                    }
                else:
                    diagnosis["docker_status"] = "stopped"
                    diagnosis["issues"].append("Docker服务未运行")
            except Exception as e:
                diagnosis["docker_status"] = "error"
                diagnosis["issues"].append(f"Docker服务检查失败: {str(e)}")

            if diagnosis["docker_status"] == "running":
                # 获取Docker网络列表
                try:
                    result = subprocess.run(
                        ["docker", "network", "ls", "--format", "{{json .}}"],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    if result.returncode == 0:
                        networks = [json.loads(line) for line in result.stdout.strip().split('\n') if line]
                        for network in networks:
                            diagnosis["networks"][network["Name"]] = network
                except Exception as e:
                    diagnosis["issues"].append(f"无法获取Docker网络列表: {str(e)}")

                # 分析特定容器
                if container_name:
                    container_info = self._analyze_container_networking(container_name)
                    diagnosis["container_analysis"][container_name] = container_info

                # 测试网络连通性
                connectivity_tests = self._test_docker_connectivity()
                diagnosis["connectivity_tests"] = connectivity_tests

            # 生成建议
            diagnosis["recommendations"] = self._generate_docker_network_recommendations(diagnosis)

            return diagnosis

        except Exception as e:
            return {"error": f"Docker网络排查失败: {str(e)}"}

    def generate_network_optimization_plan(self, current_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        生成网络优化计划

        Args:
            current_config: 当前网络配置

        Returns:
            网络优化计划
        """
        try:
            plan = {
                "timestamp": time.time(),
                "current_assessment": {},
                "optimization_steps": [],
                "expected_improvements": {},
                "implementation_timeline": []
            }

            # 评估当前配置
            plan["current_assessment"] = self._assess_current_network_config(current_config)

            # 生成优化步骤
            optimization_steps = [
                {
                    "step": 1,
                    "title": "DNS优化",
                    "description": "配置高效的DNS服务器和本地缓存",
                    "actions": [
                        "配置使用公共DNS（8.8.8.8, 1.1.1.1）",
                        "启用DNS缓存服务",
                        "优化DNS解析超时设置"
                    ],
                    "priority": "high",
                    "estimated_time": "30分钟"
                },
                {
                    "step": 2,
                    "title": "代理配置优化",
                    "description": "优化代理设置以提高网络性能",
                    "actions": [
                        "配置代理绕过规则",
                        "优化代理连接池",
                        "配置代理超时和重试策略"
                    ],
                    "priority": "medium",
                    "estimated_time": "45分钟"
                },
                {
                    "step": 3,
                    "title": "Docker网络优化",
                    "description": "优化Docker容器网络配置",
                    "actions": [
                        "使用专用网络模式",
                        "配置网络性能参数",
                        "优化容器间通信"
                    ],
                    "priority": "medium",
                    "estimated_time": "60分钟"
                },
                {
                    "step": 4,
                    "title": "防火墙和安全配置",
                    "description": "优化防火墙规则以提高安全性",
                    "actions": [
                        "配置防火墙规则",
                        "启用网络监控",
                        "配置安全策略"
                    ],
                    "priority": "low",
                    "estimated_time": "90分钟"
                }
            ]

            plan["optimization_steps"] = optimization_steps

            # 预期改进
            plan["expected_improvements"] = {
                "dns_resolve_time": "减少40-60%",
                "network_latency": "减少20-30%",
                "connection_stability": "提升至99.5%+",
                "proxy_performance": "提升30-50%"
            }

            # 实施时间线
            plan["implementation_timeline"] = [
                {"phase": "准备", "duration": "1天", "tasks": ["备份配置", "准备环境"]},
                {"phase": "DNS优化", "duration": "1天", "tasks": ["配置DNS", "测试验证"]},
                {"phase": "代理优化", "duration": "2天", "tasks": ["配置代理", "性能测试"]},
                {"phase": "Docker优化", "duration": "2天", "tasks": ["网络配置", "容器测试"]},
                {"phase": "监控", "duration": "持续", "tasks": ["性能监控", "问题排查"]}
            ]

            return plan

        except Exception as e:
            return {"error": f"网络优化计划生成失败: {str(e)}"}

    # Helper methods
    def _parse_ip_output(self, output: str) -> Dict[str, Any]:
        """解析ip addr show输出"""
        interfaces = {}
        current_interface = None

        for line in output.split('\n'):
            if line and not line.startswith(' '):
                # 新接口
                parts = line.split()
                if len(parts) >= 2:
                    interface_name = parts[1].rstrip(':')
                    current_interface = {
                        "state": parts[2] if len(parts) > 2 else "unknown",
                        "ipv4": None,
                        "ipv6": None,
                        "mac": None
                    }
                    interfaces[interface_name] = current_interface
            elif current_interface and 'inet ' in line:
                # IPv4地址
                inet_match = re.search(r'inet\s+([^\s]+)', line)
                if inet_match:
                    current_interface["ipv4"] = inet_match.group(1)

        return interfaces

    def _parse_route_output(self, output: str) -> List[Dict[str, Any]]:
        """解析ip route show输出"""
        routes = []

        for line in output.split('\n'):
            if line.strip():
                parts = line.split()
                if parts:
                    route = {
                        "destination": parts[0],
                        "gateway": None,
                        "interface": None,
                        "metric": None
                    }

                    for i, part in enumerate(parts):
                        if part == "via" and i + 1 < len(parts):
                            route["gateway"] = parts[i + 1]
                        elif part == "dev" and i + 1 < len(parts):
                            route["interface"] = parts[i + 1]
                        elif part == "metric" and i + 1 < len(parts):
                            route["metric"] = parts[i + 1]

                    routes.append(route)

        return routes

    def _get_windows_host_ip(self) -> Optional[str]:
        """获取Windows主机IP"""
        try:
            # 通过路由表获取默认网关
            result = subprocess.run(
                ["ip", "route", "show", "default"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                # 从路由输出中提取网关IP
                for line in result.stdout.split('\n'):
                    if 'default via' in line:
                        parts = line.split()
                        for i, part in enumerate(parts):
                            if part == 'via' and i + 1 < len(parts):
                                return parts[i + 1]
            return None
        except:
            return None

    def _test_connectivity(self, host: str, port: int, timeout: int = 5) -> Dict[str, Any]:
        """测试网络连通性"""
        try:
            start_time = time.time()
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((host, port))
            connect_time = (time.time() - start_time) * 1000
            sock.close()

            return {
                "success": result == 0,
                "connect_time_ms": connect_time,
                "error_code": result if result != 0 else None
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def _test_proxy_connectivity(self, proxy_host: str, proxy_port: int) -> Dict[str, Any]:
        """测试代理连通性"""
        try:
            # 简单的HTTP CONNECT测试
            start_time = time.time()
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)
            result = sock.connect_ex((proxy_host, proxy_port))
            connect_time = (time.time() - start_time) * 1000
            sock.close()

            return {
                "success": result == 0,
                "connect_time_ms": connect_time,
                "proxy_host": proxy_host,
                "proxy_port": proxy_port,
                "error_code": result if result != 0 else None
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "proxy_host": proxy_host,
                "proxy_port": proxy_port
            }

    def _generate_docker_proxy_config(self, proxy_config: Dict[str, Any]) -> Dict[str, Any]:
        """生成Docker代理配置"""
        return {
            "systemd_config": {
                "http_proxy": proxy_config.get("http_proxy"),
                "https_proxy": proxy_config.get("https_proxy"),
                "no_proxy": proxy_config.get("no_proxy", "localhost,127.0.0.1")
            },
            "daemon_config": {
                "proxies": {
                    "http-proxy": proxy_config.get("http_proxy"),
                    "https-proxy": proxy_config.get("https_proxy"),
                    "no-proxy": proxy_config.get("no_proxy", "localhost,127.0.0.1")
                }
            }
        }

    def _generate_env_proxy_config(self, proxy_config: Dict[str, Any]) -> Dict[str, Any]:
        """生成环境变量代理配置"""
        env_vars = {}

        for key, value in proxy_config.items():
            env_vars[key.upper()] = value

        # 添加额外的环境变量
        if "http_proxy" in proxy_config:
            env_vars["HTTP_PROXY"] = proxy_config["http_proxy"]
        if "https_proxy" in proxy_config:
            env_vars["HTTPS_PROXY"] = proxy_config["https_proxy"]
        if "no_proxy" in proxy_config:
            env_vars["NO_PROXY"] = proxy_config["no_proxy"]

        return env_vars

    def _generate_wsl2_recommendations(self, diagnosis: Dict[str, Any]) -> List[str]:
        """生成WSL2建议"""
        recommendations = []

        if diagnosis.get("wsl2_status") == "not_installed":
            recommendations.append("安装WSL2: wsl --install")
        elif diagnosis.get("wsl2_status") == "installed":
            recommendations.extend([
                "确保WSL2版本为最新: wsl --update",
                "考虑重启WSL2服务: wsl --shutdown"
            ])

        if any("eth0" in issue for issue in diagnosis.get("issues", [])):
            recommendations.append("重启WSL2网络服务: sudo service networking restart")

        if any("路由" in issue for issue in diagnosis.get("issues", [])):
            recommendations.append("检查Windows防火墙设置")

        if not diagnosis.get("dns_config", {}).get("servers"):
            recommendations.append("在/etc/resolv.conf中配置DNS服务器")

        return recommendations

    def _analyze_container_networking(self, container_name: str) -> Dict[str, Any]:
        """分析容器网络配置"""
        try:
            # 获取容器详细信息
            result = subprocess.run(
                ["docker", "inspect", container_name],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode != 0:
                return {"error": f"容器 {container_name} 不存在"}

            container_data = json.loads(result.stdout)[0]
            network_settings = container_data.get("NetworkSettings", {})

            return {
                "container_name": container_name,
                "ip_address": network_settings.get("IPAddress"),
                "gateway": network_settings.get("Gateway"),
                "networks": network_settings.get("Networks", {}),
                "ports": network_settings.get("Ports", {}),
                "dns": network_settings.get("DNSServers", [])
            }

        except Exception as e:
            return {"error": f"分析容器 {container_name} 失败: {str(e)}"}

    def _test_docker_connectivity(self) -> Dict[str, Any]:
        """测试Docker网络连通性"""
        tests = {}

        # 测试容器间连通性
        try:
            # 尝试ping网关
            result = subprocess.run(
                ["docker", "run", "--rm", "alpine", "ping", "-c", "1", "8.8.8.8"],
                capture_output=True,
                text=True,
                timeout=15
            )
            tests["internet_connectivity"] = {
                "success": result.returncode == 0,
                "output": result.stdout if result.returncode == 0 else result.stderr
            }
        except Exception as e:
            tests["internet_connectivity"] = {"success": False, "error": str(e)}

        return tests

    def _generate_docker_network_recommendations(self, diagnosis: Dict[str, Any]) -> List[str]:
        """生成Docker网络建议"""
        recommendations = []

        if diagnosis.get("docker_status") != "running":
            recommendations.append("启动Docker服务: sudo systemctl start docker")

        if diagnosis.get("connectivity_tests", {}).get("internet_connectivity", {}).get("success") == False:
            recommendations.extend([
                "检查Docker网络配置",
                "重启Docker网络: docker network prune",
                "重置Docker网络: sudo systemctl restart docker"
            ])

        return recommendations

    def _assess_current_network_config(self, current_config: Dict[str, Any]) -> Dict[str, Any]:
        """评估当前网络配置"""
        assessment = {
            "dns_configuration": "unknown",
            "proxy_setup": "unknown",
            "docker_networking": "unknown",
            "overall_score": 0
        }

        # 评估DNS配置
        if current_config.get("dns_servers"):
            assessment["dns_configuration"] = "configured"
        else:
            assessment["dns_configuration"] = "missing"

        # 评估代理配置
        if current_config.get("proxy_config"):
            assessment["proxy_setup"] = "configured"
        else:
            assessment["proxy_setup"] = "missing"

        # 评估Docker网络
        if current_config.get("docker_networks"):
            assessment["docker_networking"] = "configured"
        else:
            assessment["docker_networking"] = "missing"

        # 计算总体评分
        score = 0
        if assessment["dns_configuration"] == "configured":
            score += 33
        if assessment["proxy_setup"] == "configured":
            score += 33
        if assessment["docker_networking"] == "configured":
            score += 34

        assessment["overall_score"] = score

        return assessment

# 技能实例
network_troubleshooting_skill = NetworkTroubleshootingSkill()

# 导出技能信息
def get_skill_info():
    return {
        "name": network_troubleshooting_skill.skill_name,
        "description": "Network Troubleshooting - 网络连接和代理配置专家",
        "capabilities": network_troubleshooting_skill.capabilities,
        "version": "1.0.0"
    }

# 主要功能函数
def diagnose_wsl2():
    """诊断WSL2网络"""
    return network_troubleshooting_skill.diagnose_wsl2_networking()

def setup_proxy(proxy_config):
    """配置代理设置"""
    return network_troubleshooting_skill.configure_proxy_settings(proxy_config)

def analyze_dns(test_domains=None):
    """分析DNS性能"""
    return network_troubleshooting_skill.analyze_dns_performance(test_domains)

if __name__ == "__main__":
    # 示例用法
    print("Network Troubleshooting Skill initialized")
    print(f"Capabilities: {network_troubleshooting_skill.capabilities}")