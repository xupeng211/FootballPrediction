"""
Docker部署集成示例
将 docker-devops Skill 应用于现有的足球预测系统
"""

import os
import sys
import subprocess
import yaml
from pathlib import Path

class DockerDeploymentManager:
    """Docker部署管理器"""

    def __init__(self):
        self.project_root = Path(__file__).parent.parent.parent.parent
        self.docker_compose_file = self.project_root / "docker-compose.yml"
        self.production_compose = self.project_root / "docker-compose.prod.yml"

    def setup_production_deployment(self):
        """设置生产环境部署"""
        print("🚀 设置生产环境Docker部署...")

        # 创建生产环境配置
        self._create_production_configs()

        # 设置环境变量
        self._setup_environment_variables()

        # 配置监控
        self._setup_monitoring()

        # 设置SSL证书
        self._setup_ssl()

        print("✅ 生产环境部署配置完成")

    def _create_production_configs(self):
        """创建生产环境配置文件"""

        # 生产环境 docker-compose
        prod_compose = {
            'version': '3.8',
            'services': {
                'app': {
                    'image': 'football-prediction:latest',
                    'restart': 'always',
                    'deploy': {
                        'replicas': 3,
                        'resources': {
                            'limits': {'cpus': '1.0', 'memory': '1G'},
                            'reservations': {'cpus': '0.5', 'memory': '512M'}
                        }
                    },
                    'environment': [
                        'DATABASE_URL=${DATABASE_URL}',
                        'REDIS_URL=${REDIS_URL}',
                        'ENVIRONMENT=production'
                    ],
                    'networks': ['production-network']
                },
                'nginx': {
                    'image': 'nginx:alpine',
                    'restart': 'always',
                    'ports': ['80:80', '443:443'],
                    'volumes': ['./nginx:/etc/nginx:ro'],
                    'depends_on': ['app'],
                    'networks': ['production-network']
                }
            },
            'networks': {
                'production-network': {'external': True}
            }
        }

        with open(self.production_compose, 'w') as f:
            yaml.dump(prod_compose, f)

    def _setup_environment_variables(self):
        """设置环境变量"""
        env_file = self.project_root / ".env.production"

        env_vars = {
            'DATABASE_URL': 'postgresql://user:pass@postgres:5432/football',
            'REDIS_URL': 'redis://redis:6379',
            'SECRET_KEY': 'your-super-secret-key',
            'ENVIRONMENT': 'production'
        }

        with open(env_file, 'w') as f:
            for key, value in env_vars.items():
                f.write(f"{key}={value}\n")

    def _setup_monitoring(self):
        """设置监控配置"""
        monitoring_dir = self.project_root / "monitoring"
        monitoring_dir.mkdir(exist_ok=True)

        # Prometheus配置
        prometheus_config = {
            'global': {'scrape_interval': '15s'},
            'scrape_configs': [
                {
                    'job_name': 'football-api',
                    'static_configs': [{'targets': ['app:8000']}]
                }
            ]
        }

        with open(monitoring_dir / "prometheus.yml", 'w') as f:
            yaml.dump(prometheus_config, f)

    def _setup_ssl(self):
        """设置SSL证书"""
        nginx_dir = self.project_root / "nginx"
        nginx_dir.mkdir(exist_ok=True)

        ssl_dir = nginx_dir / "ssl"
        ssl_dir.mkdir(exist_ok=True)

        # 这里应该放置真实的SSL证书
        # cert.pem 和 key.pem

    def deploy(self, environment='development'):
        """部署应用"""
        print(f"🚀 部署到 {environment} 环境...")

        if environment == 'production':
            compose_file = self.production_compose
        else:
            compose_file = self.docker_compose_file

        # 构建和启动
        subprocess.run(['docker-compose', '-f', str(compose_file), 'build'], check=True)
        subprocess.run(['docker-compose', '-f', str(compose_file), 'up', '-d'], check=True)

        print(f"✅ 部署到 {environment} 环境完成")

def main():
    """主函数"""
    print("🐳 Docker部署集成演示")
    print("=" * 50)

    manager = DockerDeploymentManager()

    # 设置生产环境
    manager.setup_production_deployment()

    # 部署到开发环境
    manager.deploy('development')

if __name__ == "__main__":
    main()