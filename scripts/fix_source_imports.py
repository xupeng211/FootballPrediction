#!/usr/bin/env python3
"""
修复源代码中的导入错误
"""

from pathlib import Path


def fix_source_file_imports(file_path: Path):
    """修复源代码文件的导入错误"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        modified = False

        # 需要修复的导入映射
        import_fixes = {
            # Streaming 模块
            "from .consumer import FootballKafkaConsumer": "# from .consumer import FootballKafkaConsumer  # 不存在",
            # Monitoring 模块
            "from .health_checks import HealthChecker": "# from .health_checks import HealthChecker  # 不存在",
            "from .system_monitor import SystemMonitor": "# from .system_monitor import SystemMonitor  # 不存在",
            "from .metrics_collector import MetricsCollector": "# from .metrics_collector import MetricsCollector  # 不存在",
            # Services 模块
            "from .manager import ServiceRegistry": "# from .manager import ServiceRegistry  # 不存在",
            "from .manager import ServiceManager": "# from .manager import ServiceManager  # 不存在",
            "from .manager import BaseService": "# from .manager import BaseService  # 不存在",
            # Database 模块
            "from src.database.repositories import TeamRepository": "# from src.database.repositories import TeamRepository  # 不存在",
            # Audit 服务
            "from src.services.audit_service import AuditService": "# from src.services.audit_service import AuditService  # 不存在",
            "from src.services.audit_service_new import AuditService": "# from src.services.audit_service_new import AuditService  # 不存在",
            "from src.services.audit_service_refactored import AuditService": "# from src.services.audit_service_refactored import AuditService  # 不存在",
        }

        # 应用修复
        lines = content.split("\n")
        new_lines = []

        for line in lines:
            line_modified = False

            # 检查每个需要修复的导入
            for old_import, new_import in import_fixes.items():
                if old_import in line and not line.strip().startswith("#"):
                    new_lines.append(new_import)
                    modified = True
                    line_modified = True
                    break

            if not line_modified:
                new_lines.append(line)

        # 写入文件
        if modified:
            final_content = "\n".join(new_lines)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(final_content)
            return True

        return False

    except Exception as e:
        print(f"处理文件 {file_path} 时出错: {e}")
        return False


def main():
    """主函数"""
    # 需要修复的源代码文件
    source_files = [
        "src/streaming/kafka_consumer.py",
        "src/monitoring/system_monitor_mod/monitor.py",
        "src/services/manager_mod.py",
        "src/api/repositories.py",
    ]

    fixed_count = 0

    for file_path in source_files:
        full_path = Path(file_path)
        if full_path.exists():
            if fix_source_file_imports(full_path):
                print(f"✅ 修复了: {file_path}")
                fixed_count += 1
        else:
            print(f"❌ 文件不存在: {file_path}")

    print(f"\n总计修复了 {fixed_count} 个源代码文件")


if __name__ == "__main__":
    main()
