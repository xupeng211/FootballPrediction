#!/usr/bin/env python3
"""
使用sys.meta_hooks追踪导入
"""
import sys
import time
from functools import wraps

class ImportTracer:
    """导入追踪器"""
    def __init__(self):
        self.times = {}
        self.original_import = __builtins__.__import__

    def __call__(self, name, globals=None, locals=None, fromlist=(), level=0):
        """追踪导入"""
        if name.startswith('src'):
            start = time.time()
            module = self.original_import(name, globals, locals, fromlist, level)
            elapsed = time.time() - start
            if elapsed > 0.01:  # 只记录超过10ms的导入
                self.times[name] = elapsed
                print(f"  [导入] {name}: {elapsed:.3f}秒")
        else:
            module = self.original_import(name, globals, locals, fromlist, level)
        return module

def main():
    tracer = ImportTracer()
    __builtins__.__import__ = tracer

    print("开始追踪导入...\n")

    start = time.time()
    from src.core import exceptions
    total = time.time() - start

    print(f"\n总导入时间: {total:.3f}秒")
    print("\n详细导入时间:")
    for module, elapsed in sorted(tracer.times.items(), key=lambda x: x[1], reverse=True):
        print(f"  {module}: {elapsed:.3f}秒")

if __name__ == "__main__":
    main()