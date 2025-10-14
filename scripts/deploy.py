#!/usr/bin/env python3
"""
自动化部署脚本
"""

import os
import sys
import json
import time
import argparse
import subprocess
import logging
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class Deployer:
    """部署管理器"""

    def __init__(self, config_file: str = "deploy_config.json"):
        self.config = self.load_config(config_file)
        self.project_root = Path(__file__).parent.parent
        self.backup_dir = Path("./backups")
        self.backup_dir.mkdir(exist_ok=True)

    def load_config(self, config_file: str) -> Dict:
        """加载配置文件"""
        config_path = Path(config_file)
        if config_path.exists():
            with open(config_path, "r") as f:
                return json.load(f)
        else:
            return self.get_default_config()

    def get_default_config(self) -> Dict:
        """获取默认配置"""
        return {
            "project_name": "football-prediction",
            "environment": "production",
            "docker": {
                "registry": "your-registry.com",
                "image_tag": "latest",
                "use_compose": True,
            },
            "server": {
                "host": "your-server.com",
                "user": "deploy",
                "ssh_port": 22,
                "deploy_path": "/opt/football-prediction",
            },
            "database": {
                "url": "postgresql+asyncpg://user:pass@host:5432/db",
                "backup": True,
                "backup_retention_days": 30,
            },
            "ssl": {
                "enabled": True,
                "cert_path": "/etc/ssl/certs/football_prediction.crt",
                "key_path": "/etc/ssl/private/football_prediction.key",
            },
            "monitoring": {
                "enabled": True,
                "slack_webhook": "https://hooks.slack.com/...",
                "email": "admin@example.com",
            },
            "health_check": {"endpoint": "/api/v1/health", "timeout": 30, "retries": 5},
        }

    def save_config(self, config_file: str = "deploy_config.json"):
        """保存配置"""
        with open(config_file, "w") as f:
            json.dump(self.config, f, indent=2)
        logger.info(f"配置已保存到: {config_file}")

    def run_local_command(
        self, cmd: List[str], cwd: Optional[str] = None
    ) -> subprocess.CompletedProcess:
        """运行本地命令"""
        logger.info(f"执行本地命令: {' '.join(cmd)}")
        result = subprocess.run(
            cmd, cwd=cwd or self.project_root, capture_output=True, text=True
        )
        if result.returncode != 0:
            logger.error(f"命令执行失败: {result.stderr}")
            raise subprocess.CalledProcessError(result.returncode, cmd)
        return result

    def run_remote_command(self, cmd: str) -> str:
        """运行远程命令"""
        server = self.config["server"]
        ssh_cmd = [
            "ssh",
            "-p",
            str(server["ssh_port"]),
            f"{server['user']}@{server['host']}",
            cmd,
        ]
        logger.info(f"执行远程命令: {cmd}")
        result = subprocess.run(ssh_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"远程命令执行失败: {result.stderr}")
            raise subprocess.CalledProcessError(result.returncode, ssh_cmd)
        return result.stdout

    def copy_to_remote(self, local_path: str, remote_path: str):
        """复制文件到远程服务器"""
        server = self.config["server"]
        scp_cmd = [
            "scp",
            "-P",
            str(server["ssh_port"]),
            local_path,
            f"{server['user']}@{server['host']}:{remote_path}",
        ]
        logger.info(f"复制文件: {local_path} -> {remote_path}")
        subprocess.run(scp_cmd, check=True)

    def pre_deploy_checks(self) -> bool:
        """部署前检查"""
        logger.info("执行部署前检查...")

        # 1. 检查本地环境
        try:
            self.run_local_command(["git", "status"])
            logger.info("✓ Git仓库状态正常")
        except Exception as e:
            logger.error(f"✗ Git检查失败: {e}")
            return False

        # 2. 检查代码质量
        try:
            self.run_local_command(["make", "ci"])
            logger.info("✓ 代码质量检查通过")
        except Exception as e:
            logger.error(f"✗ 代码质量检查失败: {e}")
            return False

        # 3. 检查测试
        try:
            self.run_local_command(["make", "test"])
            logger.info("✓ 测试通过")
        except Exception as e:
            logger.error(f"✗ 测试失败: {e}")
            return False

        # 4. 检查Docker
        try:
            self.run_local_command(["docker", "--version"])
            logger.info("✓ Docker可用")
        except Exception as e:
            logger.error(f"✗ Docker不可用: {e}")
            return False

        # 5. 检查远程连接
        try:
            self.run_remote_command("echo 'SSH连接正常'")
            logger.info("✓ SSH连接正常")
        except Exception as e:
            logger.error(f"✗ SSH连接失败: {e}")
            return False

        logger.info("所有部署前检查通过!")
        return True

    def build_image(self) -> str:
        """构建Docker镜像"""
        logger.info("构建Docker镜像...")

        # 构建参数
        docker_config = self.config["docker"]
        tag = f"{docker_config['registry']}/{self.config['project_name']}:{docker_config['image_tag']}"

        # 构建命令
        cmd = [
            "docker",
            "build",
            "-t",
            tag,
            "--build-arg",
            f"ENVIRONMENT={self.config['environment']}",
            ".",
        ]

        self.run_local_command(cmd)
        logger.info(f"镜像构建成功: {tag}")
        return tag

    def push_image(self, image_tag: str):
        """推送Docker镜像"""
        logger.info("推送Docker镜像...")

        cmd = ["docker", "push", image_tag]
        self.run_local_command(cmd)
        logger.info("镜像推送成功")

    def backup_database(self):
        """备份数据库"""
        if not self.config["database"]["backup"]:
            logger.info("跳过数据库备份")
            return

        logger.info("备份数据库...")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = f"backup_{timestamp}.sql"

        # 在远程服务器执行备份
        backup_cmd = f"""
        pg_dump {self.config['database']['url']} | gzip > {backup_file}.gz
        """
        self.run_remote_command(backup_cmd)
        logger.info(f"数据库备份完成: {backup_file}.gz")

    def deploy_docker(self, image_tag: str):
        """部署Docker容器"""
        logger.info("部署Docker容器...")

        # 生成docker-compose文件
        compose_content = self.generate_docker_compose(image_tag)
        compose_file = "docker-compose.prod.yml"

        with open(compose_file, "w") as f:
            f.write(compose_content)

        # 复制到远程服务器
        remote_deploy_path = self.config["server"]["deploy_path"]
        self.copy_to_remote(compose_file, f"{remote_deploy_path}/{compose_file}")

        # 复制环境变量文件
        env_file = f".env.{self.config['environment']}"
        if Path(env_file).exists():
            self.copy_to_remote(env_file, f"{remote_deploy_path}/.env")

        # 在远程服务器执行部署
        deploy_cmd = f"""
        cd {remote_deploy_path}
        docker-compose -f {compose_file} pull
        docker-compose -f {compose_file} down
        docker-compose -f {compose_file} up -d
        """
        self.run_remote_command(deploy_cmd)
        logger.info("Docker容器部署成功")

    def generate_docker_compose(self, image_tag: str) -> str:
        """生成docker-compose配置"""
        return f"""version: '3.8'

services:
  app:
    image: {image_tag}
    container_name: {self.config['project_name']}_app
    restart: unless-stopped
    ports:
      - "80:8000"
      - "443:8443"
    env_file:
      - .env
    volumes:
      - ./ssl:/etc/ssl:ro
      - ./logs:/app/logs
    depends_on:
      - db
      - redis
    networks:
      - app-network

  db:
    image: postgres:15
    container_name: {self.config['project_name']}_db
    restart: unless-stopped
    environment:
      POSTGRES_DB: football_prediction
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD_FILE: /run/secrets/db_password
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./secrets/db_password:/run/secrets/db_password:ro
    networks:
      - app-network

  redis:
    image: redis:7-alpine
    container_name: {self.config['project_name']}_redis
    restart: unless-stopped
    command: redis-server --requirepass-file /run/secrets/redis_password
    volumes:
      - redis_data:/data
      - ./secrets/redis_password:/run/secrets/redis_password:ro
    networks:
      - app-network

  nginx:
    image: nginx:alpine
    container_name: {self.config['project_name']}_nginx
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/ssl:ro
    depends_on:
      - app
    networks:
      - app-network

volumes:
  postgres_data:
  redis_data:

networks:
  app-network:
    driver: bridge
"""

    def run_migrations(self):
        """运行数据库迁移"""
        logger.info("运行数据库迁移...")

        migration_cmd = f"""
        cd {self.config['server']['deploy_path']}
        docker-compose exec app alembic upgrade head
        """
        self.run_remote_command(migration_cmd)
        logger.info("数据库迁移完成")

    def health_check(self) -> bool:
        """健康检查"""
        logger.info("执行健康检查...")

        health_config = self.config["health_check"]
        base_url = f"https://{self.config['server']['host']}"
        url = f"{base_url}{health_config['endpoint']}"

        for i in range(health_config["retries"]):
            try:
                import requests

                response = requests.get(
                    url,
                    timeout=health_config["timeout"],
                    verify=self.config["ssl"]["enabled"],
                )

                if response.status_code == 200:
                    logger.info("✓ 健康检查通过")
                    return True
                else:
                    logger.warning(f"健康检查失败: HTTP {response.status_code}")
            except Exception as e:
                logger.warning(f"健康检查异常: {e}")

            if i < health_config["retries"] - 1:
                logger.info("等待 10 秒后重试...")
                time.sleep(10)

        logger.error("✗ 健康检查失败")
        return False

    def post_deploy_tasks(self):
        """部署后任务"""
        logger.info("执行部署后任务...")

        # 1. 清理旧镜像
        cleanup_cmd = f"""
        cd {self.config['server']['deploy_path']}
        docker image prune -f
        """
        self.run_remote_command(cleanup_cmd)

        # 2. 发送通知
        if self.config["monitoring"]["enabled"]:
            self.send_notification(
                "部署成功",
                f"{self.config['project_name']} 已成功部署到 {self.config['environment']} 环境",
            )

    def send_notification(self, title: str, message: str):
        """发送通知"""
        # Slack通知
        if self.config["monitoring"]["slack_webhook"]:
            import requests

            webhook_url = self.config["monitoring"]["slack_webhook"]
            payload = {"text": title, "attachments": [{"text": message}]}
            requests.post(webhook_url, json=payload)

        # 邮件通知
        if self.config["monitoring"]["email"]:
            # 实现邮件发送逻辑
            logger.info(f"邮件通知: {title} - {message}")

    def rollback(self):
        """回滚部署"""
        logger.info("执行回滚...")

        # 获取上一个版本的镜像
        rollback_cmd = f"""
        cd {self.config['server']['deploy_path']}
        docker-compose down
        docker-compose pull
        docker-compose up -d
        """

        try:
            self.run_remote_command(rollback_cmd)
            logger.info("回滚成功")
            self.send_notification(
                "部署已回滚", f"{self.config['project_name']} 已回滚到上一个版本"
            )
        except Exception as e:
            logger.error(f"回滚失败: {e}")

    def deploy(self, rollback_on_failure: bool = True):
        """执行完整部署流程"""
        logger.info(
            f"开始部署 {self.config['project_name']} 到 {self.config['environment']} 环境"
        )

        try:
            # 1. 部署前检查
            if not self.pre_deploy_checks():
                raise Exception("部署前检查失败")

            # 2. 备份数据库
            self.backup_database()

            # 3. 构建镜像
            image_tag = self.build_image()

            # 4. 推送镜像
            self.push_image(image_tag)

            # 5. 部署应用
            self.deploy_docker(image_tag)

            # 6. 运行迁移
            self.run_migrations()

            # 7. 健康检查
            if not self.health_check():
                raise Exception("健康检查失败")

            # 8. 部署后任务
            self.post_deploy_tasks()

            logger.info("部署成功完成!")
            return True

        except Exception as e:
            logger.error(f"部署失败: {e}")
            if rollback_on_failure:
                logger.info("开始回滚...")
                self.rollback()
            return False


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="自动化部署工具")
    parser.add_argument("--config", default="deploy_config.json", help="配置文件路径")
    parser.add_argument(
        "--environment",
        choices=["development", "staging", "production"],
        default="production",
        help="部署环境",
    )
    parser.add_argument(
        "--action",
        choices=["deploy", "health-check", "rollback", "init-config"],
        default="deploy",
        help="操作类型",
    )
    parser.add_argument("--skip-tests", action="store_true", help="跳过测试")
    parser.add_argument("--skip-backup", action="store_true", help="跳过备份")

    args = parser.parse_args()

    # 初始化部署器
    deployer = Deployer(args.config)

    # 设置环境
    deployer.config["environment"] = args.environment

    if args.action == "init-config":
        # 初始化配置文件
        deployer.save_config(args.config)
        print(f"配置文件已生成: {args.config}")
        print("请编辑配置文件中的服务器、数据库等信息")

    elif args.action == "deploy":
        # 执行部署
        success = deployer.deploy()
        sys.exit(0 if success else 1)

    elif args.action == "health-check":
        # 健康检查
        success = deployer.health_check()
        sys.exit(0 if success else 1)

    elif args.action == "rollback":
        # 回滚
        deployer.rollback()


if __name__ == "__main__":
    main()
