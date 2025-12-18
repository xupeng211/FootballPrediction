#!/usr/bin/env python3
"""
配置迁移脚本 - 工业级纯净重构

将所有文件从旧的配置系统迁移到新的统一配置系统。
"""

import os
import re
from pathlib import Path
import sys
from typing import List, Dict, Set, Any

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

class ConfigMigrator:
    """配置迁移器"""

    def __init__(self):
        self.project_root = project_root
        self.processed_files = []
        self.errors = []

        # 迁移映射
        self.import_mappings = {
            "from src.config_unified import": "from src.config_unified import",
            "import src.config_unified": "import src.config_unified_unified",
            "from src.config_unified import": "from src.config_unified import",
            "import src.config_unified_secure": "import src.config_unified_unified",
        }

        # 类名映射
        self.class_mappings = {
            "UnifiedSettings": "UnifiedSettings",
        }

        # 函数映射
        self.function_mappings = {
            "get_settings": "get_settings",
            "get_database_url": "get_database_url",
            "get_redis_url": "get_redis_url",
            "is_production": "is_production",
            "is_development": "is_development",
        }

    def find_files_to_migrate(self) -> List[Path]:
        """查找需要迁移的Python文件"""
        files_to_migrate = []

        # 搜索Python文件
        for py_file in self.project_root.rglob("*.py"):
            # 跳过缓存文件
            if "__pycache__" in str(py_file):
                continue
            # 跳过配置文件本身
            if py_file.name in ["config.py", "config_secure.py", "config_unified.py"]:
                continue

            files_to_migrate.append(py_file)

        return files_to_migrate

    def migrate_file(self, file_path: Path) -> bool:
        """迁移单个文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            original_content = content
            modified = False

            # 1. 迁移导入语句
            for old_import, new_import in self.import_mappings.items():
                if old_import in content:
                    content = content.replace(old_import, new_import)
                    modified = True
                    print(f"  🔄 {file_path.relative_to(self.project_root)}: {old_import} -> {new_import}")

            # 2. 迁移类名引用
            for old_class, new_class in self.class_mappings.items():
                # 匹配完整的单词边界
                pattern = rf'\b{re.escape(old_class)}\b'
                if re.search(pattern, content):
                    content = re.sub(pattern, new_class, content)
                    modified = True
                    print(f"  🔄 {file_path.relative_to(self.project_root)}: {old_class} -> {new_class}")

            # 3. 验证配置完整性
            if self._verify_migrated_content(content, file_path):
                print(f"  ✅ {file_path.relative_to(self.project_root)}: 配置完整性检查通过")
            else:
                print(f"  ⚠️  {file_path.relative_to(self.project_root)}: 配置完整性检查警告")

            # 4. 写回文件
            if modified:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                self.processed_files.append(file_path)
                return True
            else:
                # 没有修改也认为处理成功
                return True

        except Exception as e:
            self.errors.append(f"迁移 {file_path} 失败: {e}")
            print(f"  ❌ {file_path.relative_to(self.project_root)}: {e}")
            return False

    def _verify_migrated_content(self, content: str, file_path: Path) -> bool:
        """验证迁移后的内容"""
        # 检查是否还有旧的导入
        old_imports_found = []
        for old_import in self.import_mappings.keys():
            if old_import in content:
                old_imports_found.append(old_import)

        if old_imports_found:
            print(f"    ⚠️  仍有旧导入: {', '.join(old_imports_found)}")
            return False

        # 对于某些文件，进行额外的逻辑验证
        if "services/" in str(file_path) or "api/" in str(file_path):
            # 检查配置使用模式
            if "get_settings()" in content:
                # 确保有try-catch处理
                if "try:" not in content and "get_settings()" in content:
                    print(f"    ⚠️  建议为get_settings()添加try-catch处理")

            return True

        return True

    def update_main_config_file(self) -> bool:
        """更新主配置文件"""
        config_py = self.project_root / "src" / "config.py"
        config_secure_py = self.project_root / "src" / "config_secure.py"

        try:
            # 备份旧配置文件
            if config_py.exists():
                backup_file = config_py.with_suffix(".py.backup")
                config_py.rename(backup_file)
                print(f"  📦 备份: {config_py.relative_to(self.project_root)} -> {backup_file.name}")

            if config_secure_py.exists():
                backup_file = config_secure_py.with_suffix(".py.backup")
                config_secure_py.rename(backup_file)
                print(f"  📦 备份: {config_secure_py.relative_to(self.project_root)} -> {backup_file.name}")

            # 创建重定向文件（指向新的统一配置）
            redirect_content = '''#!/usr/bin/env python3
"""
配置重定向文件 - 指向统一配置系统

此文件存在是为了向后兼容。
请直接使用 src/config_unified.py
"""

# 重定向到统一配置
from src.config_unified import *  # noqa: F401,F403

# 向后兼容导出
if 'UnifiedSettings' not in locals():
    UnifiedSettings = UnifiedSettings

print("⚠️  此文件已重定向到 src/config_unified.py")
print("请直接导入: from src.config_unified import UnifiedSettings")
'''

            with open(config_py, 'w', encoding='utf-8') as f:
                f.write(redirect_content)

            print(f"  🔄 创建重定向: {config_py.relative_to(self.project_root)} -> config_unified.py")

            return True

        except Exception as e:
            self.errors.append(f"更新主配置文件失败: {e}")
            print(f"  ❌ 更新主配置文件失败: {e}")
            return False

    def cleanup_environment_files(self) -> bool:
        """清理环境配置文件"""
        env_files = [
            self.project_root / ".env",
            self.project_root / ".env.dev",
            self.project_root / ".env.test",
            self.project_root / ".env.production",
        ]

        cleaned_files = []
        for env_file in env_files:
            if env_file.exists():
                try:
                    # 检查是否有问题字段
                    with open(env_file, 'r', encoding='utf-8') as f:
                        content = f.read()

                    # 简单验证：检查是否有明显的格式错误
                    if '"' in content and "=" in content and "allowed_hosts" in content:
                        backup_file = env_file.with_suffix(".env.backup")
                        env_file.rename(backup_file)
                        print(f"  📦 备份问题环境文件: {env_file.name} -> {backup_file.name}")

                        # 创建简化版环境文件
                        simple_content = '''# 环境配置文件
# 复杂的配置已迁移到 src/config_unified.py

# 数据库配置
DB_HOST=localhost
DB_PORT=5432
DB_NAME=football_prediction
DB_USER=football_user
DB_PASSWORD=football_pass

# Redis配置
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# 应用配置
DEBUG=true
SECRET_KEY=your-secret-key-at-least-32-characters
PORT=8000
'''

                        with open(env_file, 'w', encoding='utf-8') as f:
                            f.write(simple_content)

                        print(f"  🔄 创建简化环境文件: {env_file.name}")
                        cleaned_files.append(env_file)

                except Exception as e:
                    print(f"  ⚠️  清理环境文件失败: {env_file.name} - {e}")

        return len(cleaned_files) > 0

    def run_migration(self) -> Dict[str, Any]:
        """运行配置迁移"""
        print("🚀 开始配置系统迁移...")
        print("=" * 50)

        # 1. 查找需要迁移的文件
        print("🔍 扫描Python文件...")
        files_to_migrate = self.find_files_to_migrate()
        print(f"📁 找到 {len(files_to_migrate)} 个Python文件需要检查")

        # 2. 迁移文件
        print("\n🔄 迁移配置引用...")
        migrated_count = 0
        for file_path in files_to_migrate:
            if self.migrate_file(file_path):
                migrated_count += 1

        # 3. 更新主配置文件
        print("\n🗂️  更新主配置文件...")
        config_updated = self.update_main_config_file()

        # 4. 清理环境文件
        print("\n🧹 清理环境配置文件...")
        env_cleaned = self.cleanup_environment_files()

        # 5. 生成报告
        print("\n📊 迁移报告:")
        print("=" * 50)
        print(f"✅ 成功处理文件: {migrated_count}")
        print(f"🔧 更新主配置文件: {'成功' if config_updated else '失败'}")
        print(f"🧹 清理环境文件: {'完成' if env_cleaned else '跳过'}")

        if self.errors:
            print(f"\n❌ 错误列表 ({len(self.errors)} 个):")
            for error in self.errors:
                print(f"   - {error}")

        return {
            "total_files": len(files_to_migrate),
            "migrated_files": migrated_count,
            "config_updated": config_updated,
            "env_cleaned": env_cleaned,
            "errors": self.errors,
            "processed_files": self.processed_files,
        }

def main():
    """主函数"""
    migrator = ConfigMigrator()
    result = migrator.run_migration()

    # 返回结果用于脚本退出码
    if result["errors"]:
        return 1  # 有错误，返回非零退出码
    else:
        return 0  # 成功，返回零退出码

if __name__ == "__main__":
    exit(main())