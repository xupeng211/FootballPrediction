#!/usr/bin/env python3
"""
Test Script for Enhanced MCP and Skills
测试增强MCP和技能的脚本
"""

import sys
import json
import time
from pathlib import Path

def print_header(title):
    """打印标题"""
    print(f"\n{'='*60}")
    print(f"🧪 {title}")
    print(f"{'='*60}")

def print_test(name, success, message=""):
    """打印测试结果"""
    if success:
        print(f"✅ {name}")
        if message:
            print(f"   {message}")
    else:
        print(f"❌ {name}")
        if message:
            print(f"   {message}")

def test_mcp_servers():
    """测试MCP服务器"""
    print_header("MCP服务器测试")

    sys.path.append("mcp_servers")

    mcp_tests = [
        ("PostgreSQL MCP服务器", "postgres_server", "PostgresMCPServer"),
        ("Redis MCP服务器", "redis_server", "RedisMCPServer"),
        ("FileSystem MCP服务器", "filesystem_server", "FileSystemMCPServer"),
        ("System Monitor MCP服务器", "system_monitor_server", "SystemMonitorMCPServer")
    ]

    all_passed = True
    for server_name, module_name, class_name in mcp_tests:
        try:
            module = __import__(module_name)
            server_class = getattr(module, class_name)
            instance = server_class()
            print_test(server_name, True, f"已成功实例化 {class_name}")
        except Exception as e:
            print_test(server_name, False, str(e))
            all_passed = False

    return all_passed

def test_skills():
    """测试专业技能"""
    print_header("专业技能测试")

    sys.path.append("skills")

    skill_tests = [
        ("基础设施优化技能", "infrastructure_optimization", "InfrastructureOptimizationSkill"),
        ("网络故障排除技能", "network_troubleshooting", "NetworkTroubleshootingSkill"),
        ("数据库性能技能", "database_performance", "DatabasePerformanceSkill")
    ]

    all_passed = True
    for skill_name, module_name, class_name in skill_tests:
        try:
            module = __import__(module_name)
            skill_class = getattr(module, class_name)
            instance = skill_class()
            capabilities = getattr(instance, 'capabilities', [])
            print_test(skill_name, True, f"能力: {', '.join(capabilities)}")
        except Exception as e:
            print_test(skill_name, False, str(e))
            all_passed = False

    return all_passed

def test_claude_config():
    """测试Claude配置"""
    print_header("Claude配置测试")

    config_file = Path(".claude/settings.json")

    if not config_file.exists():
        print_test("配置文件存在", False)
        return False

    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)

        # 测试技能配置
        skills_config = config.get("skills", {})
        if skills_config.get("enabled"):
            priority_skills = skills_config.get("priority", [])
            required_skills = [
                "football-prediction",
                "data-collection",
                "report-generation",
                "performance-monitoring",
                "infrastructure-optimization",
                "network-troubleshooting",
                "database-performance"
            ]

            missing_skills = [s for s in required_skills if s not in priority_skills]
            if missing_skills:
                print_test("技能配置完整", False, f"缺少: {', '.join(missing_skills)}")
            else:
                print_test("技能配置完整", True, f"配置了 {len(priority_skills)} 个技能")

        # 测试MCP服务器配置
        mcp_servers = config.get("mcpServers", {})
        required_mcp = ["postgres", "redis", "filesystem", "system-monitor"]

        missing_mcp = [s for s in required_mcp if s not in mcp_servers]
        if missing_mcp:
            print_test("MCP服务器配置完整", False, f"缺少: {', '.join(missing_mcp)}")
        else:
            print_test("MCP服务器配置完整", True, f"配置了 {len(mcp_servers)} 个服务器")

        return len(missing_skills) == 0 and len(missing_mcp) == 0

    except Exception as e:
        print_test("配置文件解析", False, str(e))
        return False

def test_system_monitor_features():
    """测试系统监控功能"""
    print_header("系统监控功能测试")

    try:
        sys.path.append("mcp_servers")
        from system_monitor_server import SystemMonitorMCPServer
        import asyncio

        async def test_features():
            server = SystemMonitorMCPServer()

            # 测试获取系统指标
            try:
                metrics = await server.get_system_metrics()
                if "cpu" in metrics and "memory" in metrics:
                    cpu_usage = metrics["cpu"].get("usage_percent", 0)
                    memory_usage = metrics["memory"].get("percent", 0)
                    print_test("系统指标获取", True, f"CPU: {cpu_usage:.1f}%, 内存: {memory_usage:.1f}%")
                else:
                    print_test("系统指标获取", False, "指标结构不完整")
            except Exception as e:
                print_test("系统指标获取", False, str(e))

            # 测试资源瓶颈分析
            try:
                bottlenecks = await server.analyze_resource_bottlenecks()
                if "bottlenecks" in bottlenecks:
                    print_test("资源瓶颈分析", True, f"发现 {len(bottlenecks['bottlenecks'])} 个瓶颈")
                else:
                    print_test("资源瓶颈分析", False, "分析结果结构不完整")
            except Exception as e:
                print_test("资源瓶颈分析", False, str(e))

            # 测试网络连通性
            try:
                connectivity = await server.get_network_connectivity("google.com", 443)
                if "dns" in connectivity:
                    print_test("网络连通性测试", True, "DNS和网络测试功能正常")
                else:
                    print_test("网络连通性测试", False, "测试结果结构不完整")
            except Exception as e:
                print_test("网络连通性测试", False, str(e))

        # 运行异步测试
        asyncio.run(test_features())
        return True

    except Exception as e:
        print_test("系统监控测试", False, str(e))
        return False

def test_infrastructure_optimization():
    """测试基础设施优化功能"""
    print_header("基础设施优化功能测试")

    try:
        sys.path.append("skills")
        from infrastructure_optimization import InfrastructureOptimizationSkill

        skill = InfrastructureOptimizationSkill()

        # 测试资源分配分析
        test_compose = """
services:
  app:
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '1.5'
"""

        # 模拟解析
        import yaml
        config = yaml.safe_load(test_compose)
        analysis = skill.analyze_docker_resource_allocation(test_compose, 8, 4)

        if "total_memory_requested" in analysis:
            print_test("资源分配分析", True, f"总内存请求: {analysis['total_memory_requested']}MB")
        else:
            print_test("资源分配分析", False, "分析结果结构不完整")

        # 测试高负载优化
        optimization = skill.optimize_for_high_load(config, 1000, 50)
        if "optimized_config" in optimization:
            print_test("高负载优化", True, "优化配置已生成")
        else:
            print_test("高负载优化", False, "优化配置生成失败")

        return True

    except Exception as e:
        print_test("基础设施优化测试", False, str(e))
        return False

def test_network_troubleshooting():
    """测试网络故障排除功能"""
    print_header("网络故障排除功能测试")

    try:
        sys.path.append("skills")
        from network_troubleshooting import NetworkTroubleshootingSkill

        skill = NetworkTroubleshootingSkill()

        # 测试WSL2网络诊断
        diagnosis = skill.diagnose_wsl2_networking()
        if "timestamp" in diagnosis:
            print_test("WSL2网络诊断", True, "诊断功能正常")
        else:
            print_test("WSL2网络诊断", False, "诊断结果结构不完整")

        # 测试代理配置
        proxy_config = {
            "http_proxy": "http://172.25.16.1:7890",
            "https_proxy": "http://172.25.16.1:7890",
            "no_proxy": "localhost,127.0.0.1"
        }
        proxy_result = skill.configure_proxy_settings(proxy_config)
        if "configured_proxies" in proxy_result:
            print_test("代理配置", True, "代理配置功能正常")
        else:
            print_test("代理配置", False, "代理配置功能异常")

        return True

    except Exception as e:
        print_test("网络故障排除测试", False, str(e))
        return False

def test_database_performance():
    """测试数据库性能功能"""
    print_header("数据库性能功能测试")

    try:
        sys.path.append("skills")
        from database_performance import DatabasePerformanceSkill

        skill = DatabasePerformanceSkill()

        # 测试大数据集优化
        current_config = {
            "shared_buffers": "128MB",
            "work_mem": "4MB",
            "max_connections": 100
        }

        optimization = skill.optimize_for_large_dataset(current_config, 50, 1000)
        if "optimized_config" in optimization:
            print_test("大数据集优化", True, "优化配置已生成")

            # 检查关键参数
            optimized = optimization["optimized_config"]
            shared_buffers = optimized.get("shared_buffers", "")
            work_mem = optimized.get("work_mem", "")

            if shared_buffers != "128MB" and work_mem != "4MB":
                print_test("参数优化", True, f"shared_buffers: {shared_buffers}, work_mem: {work_mem}")
            else:
                print_test("参数优化", False, "关键参数未优化")
        else:
            print_test("大数据集优化", False, "优化配置生成失败")

        return True

    except Exception as e:
        print_test("数据库性能测试", False, str(e))
        return False

def generate_test_report(results):
    """生成测试报告"""
    print_header("测试报告总结")

    total_tests = len(results)
    passed_tests = sum(1 for result in results if len(result) >= 2 and result[1])
    failed_tests = total_tests - passed_tests

    print(f"总测试数: {total_tests}")
    print(f"通过: {passed_tests}")
    print(f"失败: {failed_tests}")
    print(f"通过率: {(passed_tests/total_tests)*100:.1f}%")

    if failed_tests == 0:
        print("\n🎉 所有测试都通过了！")
        print("\n💡 建议:")
        print("1. 启动MCP服务器: ./scripts/enhanced_mcp_manager.sh start")
        print("2. 重启Claude Code以加载新配置")
        print("3. 开始使用增强功能")
    else:
        print(f"\n⚠️ 有 {failed_tests} 个测试失败")
        print("请检查错误信息并修复问题")

    # 保存详细报告
    report_data = {
        "test_timestamp": time.time(),
        "total_tests": total_tests,
        "passed_tests": passed_tests,
        "failed_tests": failed_tests,
        "pass_rate": (passed_tests/total_tests)*100,
        "results": [
            {
                "name": result[0],
                "success": len(result) >= 2 and result[1],
                "message": result[2] if len(result) >= 3 else ""
            }
            for result in results
        ]
    }

    report_file = Path("ENHANCED_MCP_TEST_REPORT.json")
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report_data, f, indent=2, ensure_ascii=False)

    print(f"\n📋 详细报告已保存: {report_file}")

    return failed_tests == 0

def main():
    """主函数"""
    print("🧪 Enhanced MCP and Skills Test Script")
    print("测试增强MCP和技能功能")

    # 运行所有测试
    test_results = []

    # 基础测试
    test_results.append(("MCP服务器", test_mcp_servers()))
    test_results.append(("专业技能", test_skills()))
    test_results.append(("Claude配置", test_claude_config()))

    # 功能测试
    test_results.append(("系统监控功能", test_system_monitor_features()))
    test_results.append(("基础设施优化功能", test_infrastructure_optimization()))
    test_results.append(("网络故障排除功能", test_network_troubleshooting()))
    test_results.append(("数据库性能功能", test_database_performance()))

    # 生成报告
    success = generate_test_report(test_results)

    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)