#!/usr/bin/env python3
"""
测试主应用启动和基本功能
"""

import sys

sys.path.insert(0, '/home/user/projects/FootballPrediction')

def test_main_app():
    """测试主应用"""

    try:
        # 测试导入
        from src.main import app

        # 测试FastAPI应用对象
        assert hasattr(app, 'title'), "应用应该有title属性"
        assert hasattr(app, 'routes'), "应用应该有routes属性"

        # 测试路由
        routes = [route.path for route in app.routes if hasattr(route, 'path')]
        for _route in routes:
            pass

        # 测试健康检查路由
        health_route = '/health' in routes
        assert health_route, "应该有健康检查路由"

        return True

    except Exception:
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_main_app()
    sys.exit(0 if success else 1)
