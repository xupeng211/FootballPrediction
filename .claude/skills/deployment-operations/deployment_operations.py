#!/usr/bin/env python3
"""
Deployment & Operations Skill for Claude Code
部署与运维专业技能 - 容器化部署和自动化运维专家
"""

from typing import Dict, List, Any, Optional
import subprocess
import os
import signal
from pathlib import Path
from datetime import datetime
import psutil

class DeploymentOperationsSkill:
    """
    Deployment & Operations Skill - 专注于容器化部署和自动化运维
    """

    def __init__(self):
        self.skill_name = "deployment-operations"
        self.capabilities = [
            "containerization-deployment",
            "docker-orchestration",
            "multi-environment-management",
            "security-hardening",
            "health-monitoring",
            "troubleshooting-recovery",
            "automation-ops",
            "permission-management",
            "network-configuration",
            "resource-optimization"
        ]

        # 实战经验常量
        self.APPUSER_UID = 999
        self.APPUSER_GID = 999

    def generate_docker_compose_template(self, environment: str = "production") -> str:
        """
        生成Docker Compose模板

        Returns:
            Docker Compose配置内容
        """
        template = f"""# FootballPrediction v2.3.0-{environment} - 容器化部署配置
# Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

services:
  app:
    image: footballprediction:latest
    container_name: footballprediction-app-{environment}
    ports:
      - "${{API_PORT:-8000}}:8000"
    env_file:
      - .env.{environment}
    environment:
      - ENVIRONMENT={environment}
      - TZ=UTC
      - PYTHONPATH=/app:/app/src:/app/scripts
      - DB_HOST=db
      - REDIS_HOST=redis
      - SHADOW_MODE=${{SHADOW_MODE:-false}}
    volumes:
      - ./src:/app/src:ro
      - ./scripts:/app/scripts:ro
      - ./data:/app/data
      - ./logs:/app/logs
      - ./reports:/app/reports
    depends_on:
      - db
      - redis
    healthcheck:
      test: ["CMD-SHELL", "ps aux | grep automation_daemon_24h.py | grep -v grep || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped
    networks:
      - football-network

  db:
    image: postgres:15-alpine
    container_name: footballprediction-db-{environment}
    ports:
      - "${{DB_PORT:-5432}}:5432"
    environment:
      - POSTGRES_DB=${{DB_NAME:-football_prediction_{environment}}}
      - POSTGRES_USER=${{DB_USER:-football_user}}
      - POSTGRES_PASSWORD=${{DB_PASSWORD}}
    volumes:
      - db_data_{environment}:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${{DB_USER:-football_user}}"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped
    networks:
      - football-network

  redis:
    image: redis:7-alpine
    container_name: footballprediction-redis-{environment}
    ports:
      - "${{REDIS_PORT:-6379}}:6379"
    command: redis-server --appendonly yes --maxmemory 512mb
    volumes:
      - redis_data_{environment}:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 3
    restart: unless-stopped
    networks:
      - football-network

volumes:
  db_data_{environment}:
    driver: local
  redis_data_{environment}:
    driver: local

networks:
  football-network:
    driver: bridge
"""
        return template

    def fix_container_permissions(self, project_root: str) -> Dict[str, Any]:
        """
        修复容器权限问题

        Returns:
            修复结果报告
        """
        try:
            project_path = Path(project_root)
            permission_fixes = []

            directories = ["logs", "scripts", "data"]
            for dir_name in directories:
                dir_path = project_path / dir_name
                if dir_path.exists():
                    subprocess.run(['chown', '-R', f'{self.APPUSER_UID}:{self.APPUSER_GID}', str(dir_path)],
                                  capture_output=True)
                    permission_fixes.append(f"Fixed {dir_name} permissions to {self.APPUSER_UID}:{self.APPUSER_GID}")

            return {
                'success': True,
                'fixed_permissions': permission_fixes,
                'appuser_uid': self.APPUSER_UID,
                'appuser_gid': self.APPUSER_GID,
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

    def cleanup_host_processes(self, process_names: List[str]) -> Dict[str, Any]:
        """
        清理宿主机"违章建筑"进程

        Returns:
            清理结果
        """
        try:
            killed_processes = []

            for process_name in process_names:
                result = subprocess.run(['pgrep', '-f', process_name], capture_output=True, text=True)

                if result.returncode == 0:
                    pids = result.stdout.strip().split('\n')
                    for pid in pids:
                        if pid and pid.isdigit():
                            try:
                                os.kill(int(pid), signal.SIGTERM)
                                killed_processes.append({
                                    'process': process_name,
                                    'pid': int(pid),
                                    'signal': 'SIGTERM'
                                })
                            except (ProcessLookupError, ValueError):
                                continue
                            except:
                                try:
                                    os.kill(int(pid), signal.SIGKILL)
                                    killed_processes.append({
                                        'process': process_name,
                                        'pid': int(pid),
                                        'signal': 'SIGKILL'
                                    })
                                except:
                                    pass

            # 验证清理结果
            remaining_processes = []
            for process_name in process_names:
                result = subprocess.run(['pgrep', '-f', process_name], capture_output=True, text=True)
                if result.returncode == 0:
                    remaining_processes.extend([p for p in result.stdout.strip().split('\n') if p])

            return {
                'success': len(remaining_processes) == 0,
                'killed_processes': killed_processes,
                'remaining_processes': remaining_processes,
                'total_killed': len(killed_processes),
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

    def check_container_health(self, container_name: str) -> Dict[str, Any]:
        """
        检查容器健康状态

        Returns:
            健康检查结果
        """
        try:
            result = subprocess.run(['docker', 'ps', '-a', '--filter', f'name={container_name}'],
                                  capture_output=True, text=True)

            if container_name not in result.stdout:
                return {
                    'exists': False,
                    'status': 'not_found',
                    'timestamp': datetime.now().isoformat()
                }

            lines = result.stdout.strip().split('\n')[1:]
            if lines:
                status_line = lines[0]
                if 'Up' in status_line:
                    status = 'running'
                    health_status = 'unknown'
                    if 'healthy' in status_line:
                        health_status = 'healthy'
                    elif 'unhealthy' in status_line:
                        health_status = 'unhealthy'
                    elif 'health: starting' in status_line:
                        health_status = 'starting'

                    return {
                        'exists': True,
                        'status': status,
                        'health_status': health_status,
                        'timestamp': datetime.now().isoformat()
                    }
                else:
                    return {
                        'exists': True,
                        'status': 'stopped',
                        'timestamp': datetime.now().isoformat()
                    }

            return {
                'exists': True,
                'status': 'unknown',
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            return {
                'exists': False,
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

    def generate_deployment_script(self, environment: str) -> str:
        """
        生成一键部署脚本

        Returns:
            部署脚本内容
        """
        script_content = f"""#!/bin/bash
# FootballPrediction {environment} - 一键部署脚本
# Generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

set -e

RED='\\033[0;31m'
GREEN='\\033[0;32m'
YELLOW='\\033[1;33m'
BLUE='\\033[0;34m'
NC='\\033[0m'

log_info() {{ echo -e "${{GREEN}}[INFO]${{NC}} $1"; }}
log_warning() {{ echo -e "${{YELLOW}}[WARNING]${{NC}} $1"; }}
log_error() {{ echo -e "${{RED}}[ERROR]${{NC}} $1"; }}

log_header() {{
    echo -e "${{BLUE}}================================${{NC}}"
    echo -e "${{BLUE}}$1${{NC}}"
    echo -e "${{BLUE}}================================${{NC}}"
}}

log_header "FootballPrediction {environment} 一键部署"

# 清理宿主机进程
processes=("automation_daemon_24h.py" "shadow_daemon_production.py" "automation_timer.py")
for process in "${{processes[@]}}"; do
    if pgrep -f "$process" > /dev/null; then
        log_info "停止进程: $process"
        pkill -f "$process" || true
        sleep 2
    fi
done

# 修复权限
sudo chown -R 999:999 logs/ scripts/ data/ || true

# 启动服务
docker-compose -f docker-compose.{environment}.yml up -d

# 健康检查
sleep 30
docker-compose -f docker-compose.{environment}.yml ps

log_info "🎉 部署完成！"
echo "🚀 应用: http://localhost:${{API_PORT:-8000}}"
echo "🗄️ 数据库: localhost:${{DB_PORT:-5432}}"
echo "🔴 Redis: localhost:${{REDIS_PORT:-6379}}"
"""
        return script_content

    def troubleshoot_container_issues(self, container_name: str) -> Dict[str, Any]:
        """
        容器故障诊断和排除

        Returns:
            诊断结果
        """
        try:
            issues = []
            recommendations = []

            health_result = self.check_container_health(container_name)

            if not health_result['exists']:
                issues.append("容器不存在")
                recommendations.append("检查容器名称或重新创建容器")
                return {
                    'container_name': container_name,
                    'issues': issues,
                    'recommendations': recommendations,
                    'status': 'container_not_found'
                }

            if health_result['status'] == 'stopped':
                logs_result = subprocess.run(['docker', 'logs', '--tail', '20', container_name],
                                           capture_output=True, text=True)
                if logs_result.returncode == 0:
                    logs = logs_result.stdout
                    if 'permission denied' in logs:
                        issues.append("权限问题")
                        recommendations.append("修复文件挂载权限，检查UID/GID不匹配")
                    elif 'Connection refused' in logs:
                        issues.append("网络连接问题")
                        recommendations.append("检查服务依赖和网络配置")

                recommendations.append("重启容器: docker restart " + container_name)

            elif health_result['health_status'] == 'unhealthy':
                issues.append("容器健康检查失败")
                recommendations.append("查看容器日志: docker logs " + container_name)

            return {
                'container_name': container_name,
                'health_result': health_result,
                'issues': issues,
                'recommendations': recommendations,
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            return {
                'container_name': container_name,
                'issues': [f"诊断失败: {str(e)}"],
                'recommendations': ["检查Docker服务状态"],
                'status': 'troubleshooting_failed',
                'timestamp': datetime.now().isoformat()
            }

    def generate_monitoring_dashboard(self) -> Dict[str, Any]:
        """
        生成监控仪表板数据

        Returns:
            监控数据
        """
        try:
            system_info = {
                'timestamp': datetime.now().isoformat(),
                'system_metrics': {
                    'cpu_usage': psutil.cpu_percent(interval=1),
                    'memory_usage': psutil.virtual_memory()._asdict(),
                    'disk_usage': psutil.disk_usage('/')._asdict()
                }
            }

            container_info = {}
            result = subprocess.run(['docker', 'ps', '--format', 'table "{{.Names}}\\t{{.Status}}\\t{{.Ports}}'],
                                  capture_output=True, text=True)

            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')[1:]  # 跳过标题行
                for line in lines:
                    if line.strip():
                        parts = line.split()
                        if len(parts) >= 2:
                            container_name = parts[0]
                            status = parts[1]
                            container_info[container_name] = {
                                'status': status,
                                'ports': parts[2] if len(parts) > 2 else '',
                            }

                            health_result = self.check_container_name(container_name)
                            container_info[container_name]['health'] = health_result.get('status', 'unknown')

            # 计算健康评分
            total_containers = len(container_info)
            healthy_containers = sum(1 for c in container_info.values()
                                    if c.get('status') == 'Up')

            health_score = (healthy_containers / total_containers * 100) if total_containers > 0 else 0

            return {
                'system_info': system_info,
                'container_info': container_info,
                'summary': {
                    'total_containers': total_containers,
                    'healthy_containers': healthy_containers,
                    'health_score': round(health_score, 2),
                    'status': 'healthy' if health_score >= 80 else 'warning' if health_score >= 60 else 'critical'
                },
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            return {
                'error': str(e),
                'timestamp': datetime.now().isoformat(),
                'status': 'monitoring_failed'
            }

    def check_container_name(self, container_name: str) -> Dict[str, Any]:
        """检查容器名称是否存在"""
        try:
            result = subprocess.run(['docker', 'ps', '-a', '--filter', f'name={container_name}'],
                                  capture_output=True, text=True)

            exists = container_name in result.stdout
            status = 'running' if exists and 'Up' in result.stdout else 'stopped' if exists else 'not_found'

            return {
                'exists': exists,
                'status': status
            }
        except Exception as e:
            return {
                'exists': False,
                'status': 'error',
                'error': str(e)
            }

    def generate_deployment_report(self, environment: str) -> Dict[str, Any]:
        """
        生成部署报告

        Returns:
            部署报告
        """
        try:
            monitoring_data = self.generate_monitoring_dashboard()

            containers_to_check = [
                f"footballprediction-app-{environment}",
                f"footballprediction-db-{environment}",
                f"footballprediction-redis-{environment}"
            ]

            container_health_results = {}
            for container in containers_to_check:
                container_health_results[container] = self.troubleshoot_container_issues(container)

            report = {
                'deployment_info': {
                    'environment': environment,
                    'timestamp': datetime.now().isoformat(),
                    'version': 'v2.3.0-production',
                    'deployment_type': 'full_containerization'
                },
                'container_health': container_health_results,
                'monitoring_data': monitoring_data,
                'summary': {
                    'overall_status': monitoring_data.get('summary', {}).get('status', 'unknown'),
                    'health_score': monitoring_data.get('summary', {}).get('health_score', 0),
                    'recommendations': self._generate_recommendations(container_health_results)
                },
                'success': True
            }

            return report

        except Exception as e:
            return {
                'error': str(e),
                'timestamp': datetime.now().isoformat(),
                'status': 'report_generation_failed',
                'success': False
            }

    def _generate_recommendations(self, container_health_results: Dict[str, Any]) -> List[str]:
        """生成建议"""
        recommendations = []

        issues_found = sum(len(result.get('issues', [])) for result in container_health_results.values())

        if issues_found == 0:
            recommendations.append("所有容器运行正常，系统状态良好")
        else:
            recommendations.append(f"发现 {issues_found} 个问题，建议及时处理")

        # 通用建议
        recommendations.extend([
            "定期执行 docker ps 检查容器状态",
            "使用 docker logs 监控容器日志",
            "监控系统资源使用情况"
        ])

        return recommendations

# 技能示例使用说明
def get_skill_info():
    """获取技能信息"""
    skill = DeploymentOperationsSkill()
    return {
        'name': skill.skill_name,
        'capabilities': skill.capabilities,
        'total_capabilities': len(skill.capabilities),
        'version': 'v2.3.0',
        'description': '基于实战经验的容器化部署和自动化运维技能'
    }