"""
使用缓存的操作示例
Cached Operations Examples

展示如何在实际应用中使用缓存装饰器。
"""

import time
from typing import Dict, List, Optional
from .cache_decorators import memory_cache, redis_cache, batch_cache, cache_invalidate
from .dict_utils import DictUtils

class DataProcessor:
    """数据处理器，使用缓存优化性能"""

    @memory_cache(ttl=300)  # 缓存5分钟
    def process_user_data(self, user_id: int) -> Dict:
        """处理用户数据"""
        print(f"处理用户数据: {user_id}")
        # 模拟耗时操作
        time.sleep(0.1)
        return {
            "user_id": user_id,
            "processed": True,
            "timestamp": time.time()
        }

    @batch_cache(ttl=600)  # 批量操作缓存10分钟
    def batch_process_users(self, user_ids: List[int]) -> List[Dict]:
        """批量处理用户数据"""
        print(f"批量处理 {len(user_ids)} 个用户")
        results = []
        for uid in user_ids:
            results.append(self.process_user_data(uid))
        return results

    @cache_invalidate(pattern="user_data")
    def update_user(self, user_id: int, data: Dict) -> Dict:
        """更新用户数据并清除缓存"""
        print(f"更新用户数据: {user_id}")
        # 执行更新操作
        return {"updated": True, "user_id": user_id}

# 使用缓存的工具函数
@memory_cache(ttl=1800)  # 缓存30分钟
def get_nested_config(data: Dict, path: str, default=None):
    """获取嵌套配置（带缓存）"""
    return DictUtils.get_nested(data, path, default)

@memory_cache(ttl=300)
def flatten_dict_cached(data: Dict, sep="."):
    """扁平化字典（带缓存）"""
    return DictUtils.flatten(data, sep)

@redis_cache(key_prefix="dict_merge", ttl=600)
def merge_dicts_cached(dict1: Dict, dict2: Dict) -> Dict:
    """合并字典（带Redis缓存）"""
    return DictUtils.merge(dict1, dict2)

# 缓存统计
class CacheStats:
    """缓存统计信息"""

    @staticmethod
    def get_hit_ratio() -> float:
        """获取缓存命中率"""
        from .cache_decorators import _memory_cache
        # 简化实现，实际应该跟踪命中次数
        return len(_memory_cache) * 0.1  # 模拟值

    @staticmethod
    def get_memory_usage() -> int:
        """获取内存使用量（字节）"""
        from .cache_decorators import _memory_cache
        import sys
        return sum(sys.getsizeof(v) for v in _memory_cache.values())

# 缓存预热
def warm_up_cache():
    """预热缓存"""
    print("预热缓存...")

    # 预加载常用数据
    sample_data = {
        "database": {
            "host": "localhost",
            "port": 5432,
            "credentials": {
                "username": "user",
                "password": "pass"
            }
        },
        "api": {
            "version": "v1",
            "timeout": 30
        }
    }

    # 预热嵌套配置获取
    get_nested_config(sample_data, "database.host")
    get_nested_config(sample_data, "database.credentials.username")
    get_nested_config(sample_data, "api.version")

    print("缓存预热完成")

if __name__ == "__main__":
    # 示例使用
    processor = DataProcessor()

    # 第一次调用（计算）
    result1 = processor.process_user_data(123)
    print("结果:", result1)

    # 第二次调用（从缓存）
    result2 = processor.process_user_data(123)
    print("结果:", result2)

    # 批量处理
    batch_results = processor.batch_process_users([1, 2, 3, 4, 5])
    print(f"批量处理结果: {len(batch_results)} 项")

    # 缓存失效
    processor.update_user(123, {"name": "John"})

    # 预热缓存
    warm_up_cache()