#!/usr/bin/env python3
"""
主启动文件
用于验证包结构和导入
"""

if __name__ == "__main__":
    import sys
    from pathlib import Path

    # 添加项目根目录到Python路径
    project_root = Path(__file__).parent
    sys.path.insert(0, str(project_root))

    # 测试导入
    try:
        from src.config_unified import get_settings
        from src.services.core_inference import CoreInferenceService
        print("✅ 包结构正确，导入成功")

        # 测试设置
        settings = get_settings()
        print(f"  - 环境: {settings.environment}")
        print(f"  - 调试模式: {settings.debug}")

    except ImportError as e:
        print(f"❌ 导入失败: {e}")
        sys.exit(1)