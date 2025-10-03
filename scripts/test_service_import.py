#!/usr/bin/env python3
"""
测试服务管理器导入性能
"""
import time
import sys

def test_import_performance():
    """测试导入性能"""
    print("开始测试服务管理器导入性能...")

    # 测试1: 导入服务管理器
    start_time = time.time()
    from src.services.manager import service_manager
    import_time = time.time() - start_time

    print(f"导入时间: {import_time:.3f}秒")

    # 测试2: 检查服务是否已注册
    start_time = time.time()
    services = service_manager.list_services()
    list_time = time.time() - start_time

    print(f"服务列表获取时间: {list_time:.3f}秒")
    print(f"已注册服务数: {len(services)}")

    # 测试3: 延迟注册
    start_time = time.time()
    from src.services.manager import _register_default_services
    _register_default_services()
    register_time = time.time() - start_time

    print(f"服务注册时间: {register_time:.3f}秒")

    # 再次检查服务
    services = service_manager.list_services()
    print(f"注册后服务数: {len(services)}")

    return import_time < 1.0  # 导入时间应该小于1秒

if __name__ == "__main__":
    success = test_import_performance()
    if success:
        print("\n✅ 导入性能测试通过！")
        sys.exit(0)
    else:
        print("\n❌ 导入性能测试失败！")
        sys.exit(1)