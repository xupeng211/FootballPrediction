#!/usr/bin/env python3
"""
Enhanced MCP Setup Script
增强MCP安装和配置脚本
"""

import os
import sys
import json
import subprocess
import shutil
from pathlib import Path
import time

def run_command(cmd, description=""):
    """执行命令并处理结果"""
    print(f"🔄 {description}")
    print(f"   命令: {cmd}")

    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            print(f"   ✅ 成功")
            if result.stdout.strip():
                print(f"   输出: {result.stdout.strip()}")
            return True
        else:
            print(f"   ❌ 失败: {result.stderr.strip()}")
            return False
    except subprocess.TimeoutExpired:
        print(f"   ⏰ 超时")
        return False
    except Exception as e:
        print(f"   ❌ 异常: {str(e)}")
        return False

def check_python_version():
    """检查Python版本"""
    print("\n🐍 检查Python版本...")

    version = sys.version_info
    if version.major >= 3 and version.minor >= 8:
        print(f"   ✅ Python版本: {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print(f"   ❌ Python版本过低: {version.major}.{version.minor}.{version.micro} (需要3.8+)")
        return False

def install_dependencies():
    """安装必要的依赖"""
    print("\n📦 安装依赖包...")

    dependencies = [
        "asyncpg",
        "psutil",
        "mcp",
        "pyyaml",
        "urllib3"
    ]

    failed_deps = []

    for dep in dependencies:
        if not run_command(f"pip3 install {dep}", f"安装 {dep}"):
            failed_deps.append(dep)

    if failed_deps:
        print(f"\n   ❌ 以下依赖安装失败: {failed_deps}")
        return False
    else:
        print("\n   ✅ 所有依赖安装成功")
        return True

def verify_mcp_servers():
    """验证MCP服务器文件"""
    print("\n🔍 验证MCP服务器文件...")

    mcp_servers_dir = Path("mcp_servers")
    required_servers = [
        "postgres_server.py",
        "redis_server.py",
        "filesystem_server.py",
        "system_monitor_server.py"
    ]

    all_exist = True
    for server in required_servers:
        server_path = mcp_servers_dir / server
        if server_path.exists():
            print(f"   ✅ {server}")
        else:
            print(f"   ❌ {server} - 文件不存在")
            all_exist = False

    return all_exist

def verify_skills():
    """验证专业技能文件"""
    print("\n🎯 验证专业技能文件...")

    skills_dir = Path("skills")
    required_skills = [
        "infrastructure_optimization.py",
        "network_troubleshooting.py",
        "database_performance.py"
    ]

    all_exist = True
    for skill in required_skills:
        skill_path = skills_dir / skill
        if skill_path.exists():
            print(f"   ✅ {skill}")
        else:
            print(f"   ❌ {skill} - 文件不存在")
            all_exist = False

    return all_exist

def setup_claude_config():
    """设置Claude配置"""
    print("\n⚙️ 设置Claude配置...")

    config_dir = Path(".claude")
    config_file = config_dir / "settings.json"

    # 创建配置目录
    config_dir.mkdir(exist_ok=True)

    # 检查配置文件是否存在
    if not config_file.exists():
        print("   ❌ Claude配置文件不存在")
        return False

    # 验证配置文件格式
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)

        # 检查必要字段
        required_sections = ["skills", "mcpServers"]
        for section in required_sections:
            if section not in config:
                print(f"   ❌ 配置缺少必要字段: {section}")
                return False

        # 检查MCP服务器配置
        mcp_servers = config.get("mcpServers", {})
        required_mcp = ["postgres", "redis", "filesystem", "system-monitor"]

        for server in required_mcp:
            if server in mcp_servers:
                print(f"   ✅ MCP服务器配置: {server}")
            else:
                print(f"   ❌ MCP服务器配置缺失: {server}")
                return False

        # 检查技能配置
        skills = config.get("skills", {})
        if skills.get("enabled", False):
            priority_skills = skills.get("priority", [])
            required_skills = [
                "football-prediction",
                "data-collection",
                "report-generation",
                "performance-monitoring",
                "infrastructure-optimization",
                "network-troubleshooting",
                "database-performance"
            ]

            for skill in required_skills:
                if skill in priority_skills:
                    print(f"   ✅ 技能配置: {skill}")
                else:
                    print(f"   ⚠️ 技能未配置: {skill}")

        print("   ✅ Claude配置验证通过")
        return True

    except json.JSONDecodeError as e:
        print(f"   ❌ 配置文件格式错误: {e}")
        return False
    except Exception as e:
        print(f"   ❌ 配置验证失败: {e}")
        return False

def test_mcp_functionality():
    """测试MCP功能"""
    print("\n🧪 测试MCP功能...")

    # 测试导入
    test_results = []

    # 测试系统监控
    try:
        sys.path.append("mcp_servers")
        from system_monitor_server import SystemMonitorMCPServer
        server = SystemMonitorMCPServer()
        test_results.append(("System Monitor", True, ""))
    except Exception as e:
        test_results.append(("System Monitor", False, str(e)))

    # 测试专业技能
    try:
        sys.path.append("skills")
        from infrastructure_optimization import InfrastructureOptimizationSkill
        skill = InfrastructureOptimizationSkill()
        test_results.append(("Infrastructure Optimization", True, ""))
    except Exception as e:
        test_results.append(("Infrastructure Optimization", False, str(e)))

    # 显示测试结果
    for name, success, error in test_results:
        if success:
            print(f"   ✅ {name} - 功能正常")
        else:
            print(f"   ❌ {name} - 功能异常: {error}")

    all_success = all(result[1] for result in test_results)
    return all_success

def setup_environment_variables():
    """设置环境变量"""
    print("\n🌍 设置环境变量...")

    env_vars = {
        "PYTHONPATH": "${PWD}:${PYTHONPATH:-}",
        "DB_HOST": "localhost",
        "DB_PORT": "5432",
        "DB_NAME": "football_prediction_prod",
        "DB_USER": "football_user",
        "REDIS_HOST": "localhost",
        "REDIS_PORT": "6379"
    }

    for var, value in env_vars.items():
        if os.environ.get(var):
            print(f"   ✅ {var}={os.environ[var]}")
        else:
            print(f"   ⚠️ {var} 未设置 (建议: {value})")

    return True

def create_log_directories():
    """创建日志目录"""
    print("\n📁 创建日志目录...")

    log_dirs = [
        "logs",
        "logs/mcp",
        "logs/monitoring",
        "data/postgres",
        "data/redis",
        "data/grafana",
        "data/prometheus"
    ]

    for log_dir in log_dirs:
        Path(log_dir).mkdir(parents=True, exist_ok=True)
        print(f"   ✅ {log_dir}")

    return True

def generate_setup_report():
    """生成安装报告"""
    print("\n📋 生成安装报告...")

    report = {
        "setup_timestamp": time.time(),
        "setup_date": time.strftime("%Y-%m-%d %H:%M:%S"),
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "mcp_servers": {
            "postgres": "✅ 已配置",
            "redis": "✅ 已配置",
            "filesystem": "✅ 已配置",
            "system-monitor": "✅ 新增"
        },
        "skills": {
            "football-prediction": "✅ 已配置",
            "data-collection": "✅ 已配置",
            "report-generation": "✅ 已配置",
            "performance-monitoring": "✅ 已配置",
            "infrastructure-optimization": "✅ 新增",
            "network-troubleshooting": "✅ 新增",
            "database-performance": "✅ 新增"
        },
        "next_steps": [
            "启动MCP服务器: ./scripts/enhanced_mcp_manager.sh start",
            "查看系统监控: ./scripts/enhanced_mcp_manager.sh monitor",
            "测试网络连通性: ./scripts/enhanced_mcp_manager.sh connectivity",
            "执行健康检查: ./scripts/enhanced_mcp_manager.sh health"
        ]
    }

    report_file = Path("ENHANCED_MCP_SETUP_REPORT.json")
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"   ✅ 报告已生成: {report_file}")
    return True

def main():
    """主函数"""
    print("🚀 Enhanced MCP Setup Script")
    print("=" * 50)

    setup_steps = [
        ("检查Python版本", check_python_version),
        ("安装依赖包", install_dependencies),
        ("验证MCP服务器", verify_mcp_servers),
        ("验证专业技能", verify_skills),
        ("设置Claude配置", setup_claude_config),
        ("测试MCP功能", test_mcp_functionality),
        ("设置环境变量", setup_environment_variables),
        ("创建日志目录", create_log_directories)
    ]

    failed_steps = []

    for step_name, step_func in setup_steps:
        print(f"\n{'='*20} {step_name} {'='*20}")
        if not step_func():
            failed_steps.append(step_name)

    print("\n" + "="*60)
    print("📊 安装结果总结")
    print("="*60)

    if not failed_steps:
        print("🎉 所有安装步骤都成功完成！")

        # 生成报告
        generate_setup_report()

        print("\n📋 下一步操作:")
        print("1. 启动MCP服务器:")
        print("   ./scripts/enhanced_mcp_manager.sh start")
        print("\n2. 查看系统监控:")
        print("   ./scripts/enhanced_mcp_manager.sh monitor")
        print("\n3. 测试网络连通性:")
        print("   ./scripts/enhanced_mcp_manager.sh connectivity")
        print("\n4. 执行健康检查:")
        print("   ./scripts/enhanced_mcp_manager.sh health")

        return True
    else:
        print(f"❌ 以下步骤失败: {', '.join(failed_steps)}")
        print("\n请检查错误信息并重新运行安装脚本")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)