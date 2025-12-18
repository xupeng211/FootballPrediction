#!/usr/bin/env python3
"""
System Monitor MCP Server for Football Prediction System
为Claude提供系统性能监控和基础设施分析能力
"""

import asyncio
import json
import os
import logging
import subprocess
import psutil
import time
from typing import List, Dict, Any, Optional
from mcp.server import Server
from mcp.types import Resource, Tool, TextContent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SystemMonitorMCPServer:
    def __init__(self):
        self.server = Server("system-monitor")

    async def get_system_metrics(self) -> Dict[str, Any]:
        """获取系统性能指标"""
        try:
            # CPU信息
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            cpu_freq = psutil.cpu_freq()

            # 内存信息
            memory = psutil.virtual_memory()

            # 磁盘信息
            disk = psutil.disk_usage('/')
            disk_io = psutil.disk_io_counters()

            # 网络信息
            network = psutil.net_io_counters()

            # 温度信息（如果可用）
            temps = {}
            try:
                temps = psutil.sensors_temperatures()
            except:
                pass

            return {
                "timestamp": time.time(),
                "cpu": {
                    "usage_percent": cpu_percent,
                    "count": cpu_count,
                    "frequency": {
                        "current": cpu_freq.current if cpu_freq else None,
                        "min": cpu_freq.min if cpu_freq else None,
                        "max": cpu_freq.max if cpu_freq else None
                    }
                },
                "memory": {
                    "total": memory.total,
                    "available": memory.available,
                    "used": memory.used,
                    "percent": memory.percent
                },
                "disk": {
                    "total": disk.total,
                    "used": disk.used,
                    "free": disk.free,
                    "percent": (disk.used / disk.total) * 100
                },
                "disk_io": {
                    "read_bytes": disk_io.read_bytes if disk_io else 0,
                    "write_bytes": disk_io.write_bytes if disk_io else 0,
                    "read_count": disk_io.read_count if disk_io else 0,
                    "write_count": disk_io.write_count if disk_io else 0
                },
                "network": {
                    "bytes_sent": network.bytes_sent,
                    "bytes_recv": network.bytes_recv,
                    "packets_sent": network.packets_sent,
                    "packets_recv": network.packets_recv
                },
                "temperature": temps
            }
        except Exception as e:
            logger.error(f"Failed to get system metrics: {e}")
            return {"error": str(e)}

    async def get_docker_metrics(self) -> Dict[str, Any]:
        """获取Docker容器性能指标"""
        try:
            # 获取所有运行中的容器
            result = subprocess.run(
                ["docker", "stats", "--no-stream", "--format", "json"],
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                return {"error": f"Docker command failed: {result.stderr}"}

            containers = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    try:
                        data = json.loads(line)
                        containers.append({
                            "name": data.get("Name", "").lstrip('/'),
                            "cpu_percent": data.get("CPUPerc", "").replace('%', ''),
                            "memory_usage": data.get("MemUsage", "").split('/')[0].strip(),
                            "memory_limit": data.get("MemUsage", "").split('/')[1].strip() if '/' in data.get("MemUsage", "") else "",
                            "memory_percent": data.get("MemPerc", "").replace('%', ''),
                            "network_io": data.get("NetIO", ""),
                            "block_io": data.get("BlockIO", "")
                        })
                    except json.JSONDecodeError:
                        continue

            return {
                "timestamp": time.time(),
                "containers": containers,
                "count": len(containers)
            }
        except Exception as e:
            logger.error(f"Failed to get docker metrics: {e}")
            return {"error": str(e)}

    async def analyze_resource_bottlenecks(self) -> Dict[str, Any]:
        """分析资源瓶颈"""
        try:
            system_metrics = await self.get_system_metrics()
            docker_metrics = await self.get_docker_metrics()

            bottlenecks = []
            recommendations = []

            # CPU瓶颈分析
            if system_metrics.get("cpu", {}).get("usage_percent", 0) > 80:
                bottlenecks.append({
                    "type": "cpu",
                    "severity": "high",
                    "message": f"CPU使用率过高: {system_metrics['cpu']['usage_percent']:.1f}%",
                    "recommendation": "考虑增加CPU核心数或优化CPU密集型任务"
                })

            # 内存瓶颈分析
            memory_percent = system_metrics.get("memory", {}).get("percent", 0)
            if memory_percent > 85:
                bottlenecks.append({
                    "type": "memory",
                    "severity": "critical",
                    "message": f"内存使用率过高: {memory_percent:.1f}%",
                    "recommendation": "立即优化内存使用或增加内存"
                })
            elif memory_percent > 70:
                bottlenecks.append({
                    "type": "memory",
                    "severity": "medium",
                    "message": f"内存使用率较高: {memory_percent:.1f}%",
                    "recommendation": "监控内存使用趋势，考虑优化"
                })

            # 磁盘空间分析
            disk_percent = system_metrics.get("disk", {}).get("percent", 0)
            if disk_percent > 90:
                bottlenecks.append({
                    "type": "disk_space",
                    "severity": "critical",
                    "message": f"磁盘空间不足: {disk_percent:.1f}%",
                    "recommendation": "清理磁盘空间或扩容"
                })

            # 容器资源分析
            if docker_metrics.get("containers"):
                for container in docker_metrics["containers"]:
                    mem_percent = float(container.get("memory_percent", 0) or 0)
                    if mem_percent > 90:
                        bottlenecks.append({
                            "type": "container_memory",
                            "severity": "high",
                            "container": container["name"],
                            "message": f"容器 {container['name']} 内存使用率: {mem_percent:.1f}%",
                            "recommendation": f"增加 {container['name']} 的内存限制或优化内存使用"
                        })

            return {
                "timestamp": time.time(),
                "bottlenecks": bottlenecks,
                "system_metrics": system_metrics,
                "docker_metrics": docker_metrics,
                "recommendations": recommendations
            }
        except Exception as e:
            logger.error(f"Failed to analyze bottlenecks: {e}")
            return {"error": str(e)}

    async def check_docker_health(self) -> Dict[str, Any]:
        """检查Docker服务健康状态"""
        try:
            health_status = {}

            # 检查Docker守护进程
            docker_info_result = subprocess.run(
                ["docker", "info", "--format", "{{json .}}"],
                capture_output=True,
                text=True
            )

            if docker_info_result.returncode == 0:
                docker_info = json.loads(docker_info_result.stdout)
                health_status["docker_daemon"] = {
                    "status": "healthy",
                    "version": docker_info.get("ServerVersion"),
                    "total_containers": docker_info.get("Containers"),
                    "running_containers": docker_info.get("ContainersRunning"),
                    "paused_containers": docker_info.get("ContainersPaused"),
                    "stopped_containers": docker_info.get("ContainersStopped")
                }
            else:
                health_status["docker_daemon"] = {
                    "status": "unhealthy",
                    "error": docker_info_result.stderr
                }

            # 检查关键容器
            key_containers = [
                "football-prediction-app",
                "football-prediction-db",
                "football-prediction-redis"
            ]

            for container_name in key_containers:
                try:
                    result = subprocess.run(
                        ["docker", "inspect", container_name, "--format", "{{json .State}}"],
                        capture_output=True,
                        text=True
                    )

                    if result.returncode == 0:
                        state = json.loads(result.stdout)
                        health_status[container_name] = {
                            "status": state.get("Status", "unknown"),
                            "health": state.get("Health", {}).get("Status", "no_healthcheck"),
                            "running": state.get("Running", False),
                            "started_at": state.get("StartedAt"),
                            "exit_code": state.get("ExitCode")
                        }
                    else:
                        health_status[container_name] = {
                            "status": "not_found",
                            "error": "Container not found"
                        }
                except Exception as e:
                    health_status[container_name] = {
                        "status": "error",
                        "error": str(e)
                    }

            return {
                "timestamp": time.time(),
                "health_status": health_status
            }
        except Exception as e:
            logger.error(f"Failed to check docker health: {e}")
            return {"error": str(e)}

    async def get_network_connectivity(self, host: str = "google.com", port: int = 443) -> Dict[str, Any]:
        """检查网络连通性"""
        try:
            import socket

            results = {}

            # DNS解析测试
            start_time = time.time()
            try:
                ip_address = socket.gethostbyname(host)
                dns_time = (time.time() - start_time) * 1000
                results["dns"] = {
                    "status": "success",
                    "host": host,
                    "ip_address": ip_address,
                    "resolution_time_ms": dns_time
                }
            except socket.gaierror as e:
                results["dns"] = {
                    "status": "failed",
                    "host": host,
                    "error": str(e)
                }
                return results

            # TCP连接测试
            start_time = time.time()
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5)
                connection_result = sock.connect_ex((ip_address, port))
                connection_time = (time.time() - start_time) * 1000
                sock.close()

                if connection_result == 0:
                    results["tcp"] = {
                        "status": "success",
                        "host": host,
                        "port": port,
                        "connection_time_ms": connection_time
                    }
                else:
                    results["tcp"] = {
                        "status": "failed",
                        "host": host,
                        "port": port,
                        "error": f"Connection failed with code {connection_result}"
                    }
            except Exception as e:
                results["tcp"] = {
                    "status": "error",
                    "host": host,
                    "port": port,
                    "error": str(e)
                }

            # HTTP测试（如果是443端口）
            if port == 443:
                start_time = time.time()
                try:
                    result = subprocess.run(
                        ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", f"https://{host}"],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    http_time = (time.time() - start_time) * 1000
                    results["http"] = {
                        "status": "success" if result.stdout.startswith("2") else "redirect",
                        "host": host,
                        "http_code": result.stdout.strip(),
                        "response_time_ms": http_time
                    }
                except subprocess.TimeoutExpired:
                    results["http"] = {
                        "status": "timeout",
                        "host": host,
                        "error": "Request timeout"
                    }
                except Exception as e:
                    results["http"] = {
                        "status": "error",
                        "host": host,
                        "error": str(e)
                    }

            return results
        except Exception as e:
            logger.error(f"Failed to check network connectivity: {e}")
            return {"error": str(e)}

# 初始化服务器
system_monitor_server = SystemMonitorMCPServer()

# 设置MCP服务器工具
@system_monitor_server.server.list_tools()
async def list_tools() -> List[Tool]:
    """列出可用工具"""
    return [
        Tool(
            name="get_system_metrics",
            description="Get real-time system performance metrics",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="get_docker_metrics",
            description="Get Docker container performance metrics",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="analyze_resource_bottlenecks",
            description="Analyze system resource bottlenecks and provide optimization recommendations",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="check_docker_health",
            description="Check Docker service and container health status",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="test_network_connectivity",
            description="Test network connectivity to external services",
            inputSchema={
                "type": "object",
                "properties": {
                    "host": {
                        "type": "string",
                        "description": "Host to test connectivity to",
                        "default": "google.com"
                    },
                    "port": {
                        "type": "integer",
                        "description": "Port to test",
                        "default": 443
                    }
                }
            }
        )
    ]

@system_monitor_server.server.call_tool()
async def call_tool(name: str, arguments: dict) -> List[TextContent]:
    """执行工具调用"""
    try:
        if name == "get_system_metrics":
            result = await system_monitor_server.get_system_metrics()
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        elif name == "get_docker_metrics":
            result = await system_monitor_server.get_docker_metrics()
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        elif name == "analyze_resource_bottlenecks":
            result = await system_monitor_server.analyze_resource_bottlenecks()
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        elif name == "check_docker_health":
            result = await system_monitor_server.check_docker_health()
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        elif name == "test_network_connectivity":
            host = arguments.get("host", "google.com")
            port = arguments.get("port", 443)
            result = await system_monitor_server.get_network_connectivity(host, port)
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        else:
            raise ValueError(f"Unknown tool: {name}")

    except Exception as e:
        error_msg = f"Tool execution failed: {str(e)}"
        logger.error(error_msg)
        return [TextContent(type="text", text=error_msg)]

@system_monitor_server.server.list_resources()
async def list_resources() -> List[Resource]:
    """列出可用资源"""
    return [
        Resource(
            uri="system://metrics",
            name="System Metrics",
            description="Real-time system performance metrics",
            mimeType="application/json"
        ),
        Resource(
            uri="docker://metrics",
            name="Docker Metrics",
            description="Docker container performance metrics",
            mimeType="application/json"
        ),
        Resource(
            uri="system://bottlenecks",
            name="Resource Bottlenecks",
            description="System resource bottleneck analysis",
            mimeType="application/json"
        )
    ]

@system_monitor_server.server.read_resource()
async def read_resource(uri: str) -> str:
    """读取资源"""
    if uri == "system://metrics":
        result = await system_monitor_server.get_system_metrics()
        return json.dumps(result, indent=2)
    elif uri == "docker://metrics":
        result = await system_monitor_server.get_docker_metrics()
        return json.dumps(result, indent=2)
    elif uri == "system://bottlenecks":
        result = await system_monitor_server.analyze_resource_bottlenecks()
        return json.dumps(result, indent=2)
    else:
        raise ValueError(f"Unknown resource: {uri}")

async def main():
    """启动MCP服务器"""
    logger.info("Starting System Monitor MCP Server...")

    # 检查依赖
    try:
        import psutil
        logger.info(f"psutil version: {psutil.__version__}")
    except ImportError:
        logger.error("psutil is required but not installed. Please install it with: pip install psutil")
        return

    # 启动服务器
    from mcp.server.stdio import stdio_server
    async with stdio_server() as (read_stream, write_stream):
        await system_monitor_server.server.run(
            read_stream,
            write_stream,
            system_monitor_server.server.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main())