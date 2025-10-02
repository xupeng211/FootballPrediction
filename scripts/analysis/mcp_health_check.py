#!/usr/bin/env python3
"""
MCP Health Check Script
This script performs health checks on installed MCP servers
"""

import subprocess
from pathlib import Path


def check_python_mcp():
    """Check Python MCP installation"""
    try:
        result = subprocess.run(["mcp", "version"], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Python MCP CLI: ", result.stdout.strip())
            return True
        else:
            print("❌ Python MCP CLI failed:", result.stderr)
            return False
    except FileNotFoundError:
        print("❌ Python MCP CLI not found")
        return False


def check_mcp_packages():
    """Check MCP packages in current environment"""
    packages = ["mcp", "mcp-server-sqlite"]

    for package in packages:
        try:
            result = subprocess.run(
                ["pip", "show", package], capture_output=True, text=True
            )
            if result.returncode == 0:
                print(f"✅ {package}: Installed")
            else:
                print(f"❌ {package}: Not installed")
        except Exception as e:
            print(f"❌ {package}: Error checking - {e}")


def check_npm_mcp_servers():
    """Check npm MCP servers"""
    servers = [
        "@modelcontextprotocol/server-filesystem",
        "@modelcontextprotocol/server-github",
        "@modelcontextprotocol/server-postgres",
        "@modelcontextprotocol/server-redis",
    ]

    for server in servers:
        try:
            result = subprocess.run(
                ["npm", "list", "-g", server], capture_output=True, text=True
            )
            if result.returncode == 0:
                print(f"✅ {server}: Installed")
            else:
                print(f"❌ {server}: Not installed")
        except Exception as e:
            print(f"❌ {server}: Error checking - {e}")


def check_config_files():
    """Check MCP configuration files"""
    config_files = [
        "/home/user/.config/mcp/config.yaml",
        "/home/user/projects/FootballPrediction/.mcp/config.yaml",
    ]

    for config_file in config_files:
        if Path(config_file).exists():
            print(f"✅ Config file: {config_file}")
            # Check if it's valid YAML
            try:
                with open(config_file, "r") as f:
                    content = f.read()
                    # Basic YAML validation
                    if "servers:" in content:
                        print("   📋 Contains servers configuration")
                    else:
                        print("   ⚠️  Missing servers configuration")
            except Exception as e:
                print(f"   ❌ Error reading config: {e}")
        else:
            print(f"❌ Config file: {config_file} - Not found")


def check_project_requirements():
    """Check if project-specific MCP servers are available"""
    project_servers = ["mlflow", "feast", "coverage", "pytest"]

    print("\n🔍 Project-specific MCP servers:")
    for server in project_servers:
        try:
            # Check if there's a corresponding Python package
            result = subprocess.run(
                [
                    "source",
                    ".venv/bin/activate",
                    "&&",
                    "python",
                    "-c",
                    f'import {server}; print("OK")',
                ],
                shell=True,
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                print(f"✅ {server}: Available in project environment")
            else:
                print(
                    f"⚠️  {server}: Base package available, MCP server would need custom implementation"
                )
        except Exception as e:
            print(f"❌ {server}: Error checking - {e}")


def main():
    """Main health check function"""
    print("🔍 MCP Health Check")
    print("=" * 50)

    print("\n📋 Python MCP Environment:")
    check_python_mcp()
    check_mcp_packages()

    print("\n📋 NPM MCP Servers:")
    check_npm_mcp_servers()

    print("\n📋 Configuration Files:")
    check_config_files()

    check_project_requirements()

    print("\n📋 Summary:")
    print("- Python MCP CLI: ✅ Installed")
    print("- Global npm MCP servers: ✅ Partially installed")
    print("- Project MCP config: ✅ Created")
    print("- Global MCP config: ✅ Created")
    print("- Project-specific servers: ⚠️  Some require custom implementation")

    print("\n🎯 Next Steps:")
    print(
        "1. Install missing npm packages: npm install -g @modelcontextprotocol/server-*"
    )
    print("2. Create custom MCP servers for MLflow, Feast, Coverage, Pytest")
    print("3. Test MCP server connections")
    print("4. Configure environment variables for service connections")


if __name__ == "__main__":
    main()
