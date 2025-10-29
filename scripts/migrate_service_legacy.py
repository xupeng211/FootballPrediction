#!/usr/bin/env python3
"""
迁移service_legacy.py代码到新模块
"""

from pathlib import Path
from typing import Dict, List


def extract_methods_from_file(file_path: Path, method_names: List[str]) -> Dict[str, str]:
    """从文件中提取指定方法的代码"""
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    methods = {}
    current_method = None
    method_lines = []
    method_indent = 0

    for i, line in enumerate(lines):
        # 检查是否是方法定义
        stripped = line.strip()
        if any(
            stripped.startswith(f"def {name}") or stripped.startswith(f"async def {name}")
            for name in method_names
        ):
            # 保存之前的方法
            if current_method:
                methods[current_method] = "".join(method_lines)

            # 开始新方法
            current_method = stripped.split("(")[0].replace("def ", "").replace("async def ", "")
            method_lines = [line]
            method_indent = len(line) - len(line.lstrip())
        elif current_method:
            method_lines.append(line)
            # 检查方法是否结束（遇到相同或更小缩进的类/方法定义）
            if line.strip() and (len(line) - len(line.lstrip())) <= method_indent:
                if stripped.startswith(("class ", "def ", "async def ")):
                    # 方法结束，保存但不包括当前行
                    methods[current_method] = "".join(method_lines[:-1])
                    current_method = None
                    method_lines = []

    # 保存最后一个方法
    if current_method:
        methods[current_method] = "".join(method_lines)

    return methods


def create_data_sanitizer():
    """创建data_sanitizer.py模块"""
    print("创建 data_sanitizer.py...")

    source_file = Path("src/services/audit_service_mod/service_legacy.py")
    method_names = [
        "_hash_sensitive_value",
        "_hash_sensitive_data",
        "_sanitize_data",
        "_is_sensitive_table",
        "_contains_pii",
        "_is_sensitive_data",
    ]

    methods = extract_methods_from_file(source_file, method_names)

    content = '''"""
Data Sanitization and Sensitive Data Handling

提供敏感数据清理、哈希和隐私保护功能。
Provides sensitive data sanitization, hashing and privacy protection.
"""

import hashlib
import json
from typing import Any, Dict

from src.core.logging import get_logger


class DataSanitizer:
    """
    数据清理器

    负责识别和清理敏感数据，确保隐私保护。
    """

    def __init__(self):
        """初始化数据清理器"""
        self.logger = get_logger(__name__)

        # 敏感数据配置
        self.sensitive_tables = {
            "users",
            "permissions",
            "tokens",
            "passwords",
            "api_keys",
            "user_profiles",
            "payment_info",
            "personal_data",
        }

        self.sensitive_columns = {
            "password",
            "token",
            "secret",
            "key",
            "credential",
            "ssn",
            "credit_card",
            "bank_account",
        }

'''

    # 添加方法
    for method_name in method_names:
        if method_name in methods:
            # 移除方法开头的缩进
            method_code = methods[method_name]
            # 调整缩进（减少4个空格）
            method_lines = method_code.split("\n")
            adjusted_lines = []
            for line in method_lines:
                if line.strip():
                    adjusted_lines.append(line[4:] if line.startswith("    ") else line)
                else:
                    adjusted_lines.append(line)
            content += "\n\n" + "\n".join(adjusted_lines)

    # 写入文件
    output_file = Path("src/services/audit_service_mod/data_sanitizer.py")
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"✅ 创建: {output_file}")


def create_severity_analyzer():
    """创建severity_analyzer.py模块"""
    print("\n创建 severity_analyzer.py...")

    source_file = Path("src/services/audit_service_mod/service_legacy.py")
    method_names = ["_determine_severity", "_determine_compliance_category"]

    methods = extract_methods_from_file(source_file, method_names)

    content = '''"""
Severity and Compliance Analysis

提供审计事件严重性评估和合规性分类功能。
Provides audit event severity assessment and compliance classification.
"""

from typing import Any, Dict, Optional
from datetime import datetime

from src.core.logging import get_logger
from .models import AuditSeverity


class SeverityAnalyzer:
    """
    严重性分析器

    负责评估审计事件的严重性和合规性分类。
    """

    def __init__(self):
        """初始化严重性分析器"""
        self.logger = get_logger(__name__)

        # 合规类别映射
        self.compliance_mapping = {
            "users": "user_management",
            "permissions": "access_control",
            "tokens": "authentication",
            "payment": "financial",
            "personal_data": "privacy",
        }

'''

    # 添加方法
    for method_name in method_names:
        if method_name in methods:
            method_code = methods[method_name]
            method_lines = method_code.split("\n")
            adjusted_lines = []
            for line in method_lines:
                if line.strip():
                    adjusted_lines.append(line[4:] if line.startswith("    ") else line)
                else:
                    adjusted_lines.append(line)
            content += "\n\n" + "\n".join(adjusted_lines)

    # 写入文件
    output_file = Path("src/services/audit_service_mod/severity_analyzer.py")
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"✅ 创建: {output_file}")


def update_core_module():
    """更新core.py模块，添加导入和组合"""
    print("\n更新 core.py...")

    content = '''"""
Core Audit Service

提供审计服务的核心功能和统一接口。
Provides core audit service functionality and unified interface.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime

from src.core.logging import get_logger
from src.database.connection_mod import DatabaseManager

from .data_sanitizer import DataSanitizer
from .severity_analyzer import SeverityAnalyzer
from .models import (
    AuditLog,
    AuditAction,
    AuditSeverity,
    AuditContext,
)


class AuditService:
    """
    权限审计服务 / Permission Audit Service

    提供API层面的自动审计功能，记录所有写操作到audit_log表。
    支持装饰器模式，自动捕获操作上下文和数据变更。

    Provides API-level automatic audit functionality, recording all write operations
    to the audit_log table. Supports decorator pattern to automatically capture
    operation context and data changes.
    """

    def __init__(self):
        """初始化审计服务 / Initialize Audit Service"""
        self.db_manager: Optional[DatabaseManager] = None
        self.logger = get_logger(f"audit.{self.__class__.__name__}")

        # 组合其他组件
        self.data_sanitizer = DataSanitizer()
        self.severity_analyzer = SeverityAnalyzer()

    async def initialize(self) -> bool:
        """
        初始化服务 / Initialize Service

        Returns:
            初始化是否成功 / Whether initialization was successful
        """
        try:
            if not self.db_manager:
                self.db_manager = DatabaseManager()
                self.db_manager.initialize()

            self.logger.info("审计服务初始化完成")
            return True

        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
            self.logger.error(f"初始化审计服务失败: {e}")
            return False

    def close(self) -> None:
        """关闭服务 / Close Service"""
        if self.db_manager:
            self.db_manager.close()
        self.logger.info("审计服务已关闭")

    # 委托方法到相应组件
    def _hash_sensitive_value(self, value: str) -> str:
        """委托给data_sanitizer"""
        return self.data_sanitizer._hash_sensitive_value(value)

    def _sanitize_data(self, data: Any) -> Any:
        """委托给data_sanitizer"""
        return self.data_sanitizer._sanitize_data(data)

    def _determine_severity(self, action: str, table: str, user_role: str) -> AuditSeverity:
        """委托给severity_analyzer"""
        return self.severity_analyzer._determine_severity(action, table, user_role)

    # TODO: 迁移其他方法...
    # 这里需要逐步迁移其他方法，暂时保留接口
'''

    # 写入文件
    output_file = Path("src/services/audit_service_mod/core.py")
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"✅ 更新: {output_file}")


def update_init_file():
    """更新__init__.py文件"""
    print("\n更新 __init__.py...")

    content = '''"""
Audit Service Module

提供完整的审计功能，包括数据清理、日志记录、查询和分析。
Provides complete audit functionality including data sanitization,
logging, querying and analysis.
"""

from .core import AuditService
from .data_sanitizer import DataSanitizer
from .severity_analyzer import SeverityAnalyzer

__all__ = [
    "AuditService",
    "DataSanitizer",
    "SeverityAnalyzer",
]
'''

    # 写入文件
    output_file = Path("src/services/audit_service_mod/__init__.py")
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"✅ 更新: {output_file}")


def main():
    """主函数"""
    print("=" * 80)
    print("🔄 迁移 service_legacy.py 到新模块")
    print("=" * 80)

    # 检查源文件
    source_file = Path("src/services/audit_service_mod/service_legacy.py")
    if not source_file.exists():
        print("❌ 源文件不存在！")
        return

    # 创建各个模块
    create_data_sanitizer()
    create_severity_analyzer()
    update_core_module()
    update_init_file()

    print("\n" + "=" * 80)
    print("✅ 第一阶段迁移完成！")
    print("=" * 80)

    print("\n📝 已完成：")
    print("  ✅ data_sanitizer.py - 数据清理模块")
    print("  ✅ severity_analyzer.py - 严重性分析模块")
    print("  ✅ core.py - 核心服务模块（部分）")
    print("  ✅ __init__.py - 模块导出")

    print("\n⏳ 待完成：")
    print("  - audit_logger.py - 日志记录模块")
    print("  - audit_query.py - 查询分析模块")
    print("  - 完善core.py的其余方法")

    print("\n📋 下一步：")
    print("1. 运行测试验证当前更改")
    print("2. 继续迁移剩余的方法")
    print("3. 更新所有导入语句")
    print("4. 删除原始文件")


if __name__ == "__main__":
    main()
