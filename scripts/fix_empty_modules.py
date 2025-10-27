#!/usr/bin/env python3
"""
修复空模块的导入问题
"""

import os
from pathlib import Path


def create_router_for_module(module_path):
    """为模块创建基本路由器"""
    module_dir = Path(module_path)
    if not module_dir.exists():
        return False

    # 创建基本的router.py文件
    router_content = '''"""
基本路由器 - 自动生成
"""

from fastapi import APIRouter

router = APIRouter()

@router.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "ok", "module": "%s"}
''' % module_dir.name

    router_file = module_dir / "router.py"

    if not router_file.exists():
        with open(router_file, 'w', encoding='utf-8') as f:
            f.write(router_content)
        print(f"   ✅ 创建路由器: {router_file}")
        return True

    return False


def main():
    """修复所有空模块"""
    print("🔧 修复空模块的导入问题...")

    # 需要修复的模块
    modules_to_fix = [
        'src/api/adapters',
        'src/api/facades',
        'src/cqrs',
        'src/middleware',
        'src/streaming',
        'src/ml',
        'src/monitoring',
        'src/realtime',
        'src/tasks'
    ]

    fixed_count = 0
    for module in modules_to_fix:
        if create_router_for_module(module):
            fixed_count += 1

    print(f"📊 修复了 {fixed_count} 个模块")
    return fixed_count > 0


if __name__ == "__main__":
    main()