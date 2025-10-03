#!/usr/bin/env python3
"""
敏感文件保护工具
保护敏感文件不被提交到版本控制
"""

import os
import subprocess
from pathlib import Path

class SensitiveFileProtector:
    def __init__(self):
        self.project_root = Path.cwd()
        self.protected_files = []

    def update_gitignore(self):
        """更新.gitignore文件"""
        gitignore_path = self.project_root / ".gitignore"

        # 需要保护的文件模式
        sensitive_patterns = [
            "# 敏感文件保护",
            "*.env",
            "*.env.*",
            "*.env.local",
            "*.env.production",
            "!*.env.example",
            "!*.env.template",
            "",
            "# 证书和密钥",
            "*.pem",
            "*.key",
            "*.p12",
            "*.pfx",
            "*.crt",
            "*.cer",
            "secrets/",
            "config/secrets.yaml",
            "config/secrets.yml",
            "",
            "# AWS/云服务配置",
            ".aws/",
            "aws-credentials.json",
            "google-credentials.json",
            "*.keytab",
            "",
            "# SSH密钥",
            "id_rsa*",
            "id_ed25519*",
            "ssh_host_*",
            "",
            "# 数据库文件",
            "*.db",
            "*.sqlite",
            "*.sqlite3",
            "",
            "# 备份文件",
            "*.backup",
            "*.bak",
            "*~",
            "",
            "# 日志文件（可能包含敏感信息）",
            "*.log",
            "logs/*.log",
            "",
            "# 临时文件",
            ".tmp/",
            "temp/",
            "tmp/",
            "",
            "# IDE配置（可能包含密码）",
            ".vscode/settings.json",
            ".idea/workspace.xml",
            "",
            "# 系统文件",
            ".DS_Store",
            "Thumbs.db",
            "",
            "# Python缓存",
            "__pycache__/",
            "*.py[cod]",
            "*$py.class",
            "",
            "# 虚拟环境",
            ".venv/",
            "venv/",
            "env/",
            "ENV/",
            "",
            "# 测试覆盖率",
            ".coverage",
            "htmlcov/",
            "",
            "# 构建产物",
            "build/",
            "dist/",
            "*.egg-info/",
            "",
            "# 报告文件（可能包含敏感信息）",
            "*_report.json",
            "coverage*.json",
            "bandit*.json",
            "",
            "# MLflow（可能包含敏感配置）",
            "mlruns/",
            ".mlflow/",
        ]

        # 读取现有内容
        existing_content = ""
        if gitignore_path.exists():
            with open(gitignore_path, 'r') as f:
                existing_content = f.read()

        # 添加新模式（避免重复）
        new_patterns = []
        for pattern in sensitive_patterns:
            if pattern and pattern not in existing_content:
                new_patterns.append(pattern)

        if new_patterns:
            with open(gitignore_path, 'a') as f:
                f.write('\n')
                for pattern in new_patterns:
                    f.write(f"{pattern}\n")

            print(f"✅ 已添加 {len(new_patterns)} 个保护规则到 .gitignore")
            self.protected_files.extend(new_patterns)
        else:
            print("ℹ️ .gitignore 已包含所有必要的规则")

    def check_tracked_sensitive_files(self):
        """检查是否有敏感文件被git跟踪"""
        try:
            result = subprocess.run(
                ["git", "ls-files"],
                capture_output=True,
                text=True,
                check=True
            )
            tracked_files = result.stdout.split('\n')

            # 敏感文件模式
            sensitive_extensions = ['.pem', '.key', '.p12', '.pfx', '.env']
            sensitive_names = [
                'password', 'secret', 'key', 'token', 'credential',
                'aws-credentials', 'google-credentials', 'id_rsa'
            ]

            tracked_sensitive = []
            for file in tracked_files:
                if not file:
                    continue

                file_path = Path(file)
                file_name = file_path.name.lower()

                # 检查扩展名
                if any(file.endswith(ext) for ext in sensitive_extensions):
                    tracked_sensitive.append(file)
                    continue

                # 检查文件名
                if any(sensitive in file_name for sensitive in sensitive_names):
                    tracked_sensitive.append(file)

            if tracked_sensitive:
                print("⚠️ 发现被跟踪的敏感文件：")
                for file in tracked_sensitive:
                    print(f"  - {file}")
                    print(f"    建议执行: git rm --cached {file}")
                    print(f"    然后确保 .gitignore 包含相应的规则")

                return tracked_sensitive
            else:
                print("✅ 没有发现被跟踪的敏感文件")

        except subprocess.CalledProcessError:
            print("❌ 无法获取git跟踪的文件列表")

        return []

    def fix_file_permissions(self):
        """修复敏感文件权限"""
        sensitive_files = [
            ".env",
            ".env.local",
            ".env.production",
            ".env.template",
        ]

        for file in sensitive_files:
            file_path = self.project_root / file
            if file_path.exists():
                # 设置权限为仅所有者可读写
                os.chmod(file_path, 0o600)
                print(f"✅ {file} 权限已设置为 600 (仅所有者可访问)")

    def create_env_example(self):
        """创建安全的 .env.example 文件"""
        example_content = """# 环境变量示例
# 复制此文件为 .env.local 并填写实际值
# 注意：.env.local 不应该提交到版本控制

# 数据库配置
DB_HOST=localhost
DB_PORT=5432
DB_NAME=football_prediction
DB_USER=postgres
DB_PASSWORD=your-database-password-here

# Redis配置
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=your-redis-password-here

# API配置
FOOTBALL_API_KEY=your-football-api-key-here
ODDS_API_KEY=your-odds-api-key-here

# 应用安全配置
SECRET_KEY=your-secret-key-here-should-be-long-and-random
JWT_SECRET=your-jwt-secret-here
ENCRYPTION_KEY=your-encryption-key-here

# 第三方服务
MLFLOW_TRACKING_URI=http://localhost:5000
PROMETHEUS_URL=http://localhost:9090

# 环境设置
ENVIRONMENT=development
DEBUG=False
LOG_LEVEL=INFO
"""

        example_path = self.project_root / ".env.example"
        if not example_path.exists():
            with open(example_path, 'w') as f:
                f.write(example_content)
            print("✅ 已创建 .env.example 示例文件")

    def run(self):
        """运行所有保护措施"""
        print("🔒 开始保护敏感文件...")

        # 1. 更新 .gitignore
        print("\n1. 更新 .gitignore...")
        self.update_gitignore()

        # 2. 检查被跟踪的敏感文件
        print("\n2. 检查被跟踪的敏感文件...")
        tracked_sensitive = self.check_tracked_sensitive_files()

        # 3. 修复文件权限
        print("\n3. 修复文件权限...")
        self.fix_file_permissions()

        # 4. 创建示例文件
        print("\n4. 创建环境变量示例...")
        self.create_env_example()

        # 总结
        print("\n" + "=" * 50)
        print("敏感文件保护完成！")
        print(f"保护的规则数: {len(self.protected_files)}")

        if tracked_sensitive:
            print("\n⚠️ 警告: 发现被跟踪的敏感文件！")
            print("请立即执行以下命令：")
            for file in tracked_sensitive:
                print(f"  git rm --cached {file}")
            print("\n然后提交更改：")
            print("  git add .gitignore")
            print("  git commit -m 'security: 保护敏感文件'")
        else:
            print("\n✅ 所有敏感文件已得到保护！")

        print("\n最佳实践：")
        print("1. 使用 .env.example 作为模板")
        print("2. 创建 .env.local 并填写实际值")
        print("3. 确保 .env.local 在 .gitignore 中")
        print("4. 定期检查敏感文件泄露")


if __name__ == "__main__":
    protector = SensitiveFileProtector()
    protector.run()