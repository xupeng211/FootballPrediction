#!/usr/bin/env python3
"""
测试主应用启动和基本功能
"""

import sys

sys.path.insert(0, '/home/user/projects/FootballPrediction')

def test_main_app():
    """测试主应用"""
    print("🧪 开始测试主应用...")

    try:
        # 测试导入
        print("1. 测试模块导入...")
        from src.main import app
        print("   ✅ 主应用导入成功")

        # 测试FastAPI应用对象
        print("2. 测试FastAPI应用对象...")
        assert hasattr(app, 'title'), "应用应该有title属性"
        assert hasattr(app, 'routes'), "应用应该有routes属性"
        print("   ✅ FastAPI应用对象正常")

        # 测试路由
        print("3. 测试API路由...")
        routes = [route.path for route in app.routes if hasattr(route, 'path')]
        print(f"   📋 发现路由: {len(routes)}个")
        for route in routes:
            print(f"   - {route}")

        # 测试健康检查路由
        health_route = '/health' in routes
        assert health_route, "应该有健康检查路由"
        print("   ✅ 健康检查路由存在")

        print("\n🎉 主应用测试通过！")
        return True

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_main_app()
    sys.exit(0 if success else 1)
