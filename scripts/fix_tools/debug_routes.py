#!/usr/bin/env python3
"""
调试路由配置脚本
用于打印实际的API路由配置，帮助修复测试中的路由验证问题
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))


def print_router_info():
    """打印路由器信息"""
    try:
        from src.api.predictions import router

        print("=== 预测API路由器信息 ===")
        print(f"路由器前缀: {router.prefix}")
        print(f"路由器标签: {router.tags}")
        print(f"路由总数: {len(router.routes)}")

        print("\n=== 实际路由列表 ===")
        for i, route in enumerate(router.routes, 1):
            print(f"{i:2d}. {route.path} [{', '.join(route.methods)}]")
            if hasattr(route, "name") and route.name:
                print(f"     名称: {route.name}")

        print("\n=== 路径列表（用于测试断言）===")
        routes = [route.path for route in router.routes]
        for route in sorted(routes):
            print(f'    "{route}",')

    except Exception as e:
        print(f"错误: {e}")
        import traceback

        traceback.print_exc()


def print_app_routes():
    """打印应用程序所有路由"""
    try:
        from fastapi import FastAPI

        from src.api.health import router as health_router
        from src.api.predictions import router as predictions_router

        app = FastAPI()
        app.include_router(health_router)
        app.include_router(predictions_router)

        print("\n=== 应用程序所有路由 ===")
        print(f"应用程序路由总数: {len(app.routes)}")

        for i, route in enumerate(app.routes, 1):
            print(f"{i:2d}. {route.path} [{', '.join(route.methods)}]")

    except Exception as e:
        print(f"错误: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    print_router_info()
    print_app_routes()
