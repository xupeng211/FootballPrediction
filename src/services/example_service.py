"""
示例服务

演示如何使用新的EnhancedBaseService基类。
"""

from typing import Any, Dict, List, Optional
import asyncio

from .core import EnhancedBaseService, ServiceConfig


class ExampleService(EnhancedBaseService):
    """示例服务类"""

    def __init__(self, config: Optional[ServiceConfig] = None):
        """初始化示例服务"""
        if config is None:
            config = ServiceConfig(
                name="example",
                version="1.0.0",
                description="示例服务，演示EnhancedBaseService的使用",
                dependencies=["cache", "database"],
            )
        super().__init__(config)

        # 服务特定数据
        self._data: Dict[str, Any] = {}
        self._processing_count = 0

    async def initialize(self) -> None:
        """初始化服务"""
        self.logger.info("Initializing ExampleService...")

        # 模拟初始化工作
        await asyncio.sleep(0.1)

        # 加载配置
        self.max_items = self.get_config("max_items", 100)
        self.enable_cache = self.get_config("enable_cache", True)

        # 初始化数据
        self._data = {
            "initialized_at": self.config.created_at.isoformat(),
            "settings": {
                "max_items": self.max_items,
                "enable_cache": self.enable_cache,
            },
        }

        self._initialized = True
        self.logger.info("ExampleService initialized successfully")

    async def shutdown(self) -> None:
        """关闭服务"""
        self.logger.info("Shutting down ExampleService...")

        # 清理资源
        self._data.clear()

        await super().shutdown()
        self.logger.info("ExampleService shut down successfully")

    async def process_data(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """处理数据项

        Args:
            item: 要处理的数据项

        Returns:
            处理后的数据项
        """
        return await self.execute_with_metrics(
            "process_data", self._process_data_impl, item
        )

    async def _process_data_impl(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """处理数据的具体实现"""
        # 检查容量限制
        if len(self._data) >= self.max_items:
            raise ValueError(f"Maximum capacity ({self.max_items}) reached")

        # 处理数据
        self._processing_count += 1
        processed_item = {
            "id": self._processing_count,
            "data": item,
            "processed_at": self._get_current_timestamp(),
            "service": self.name,
        }

        # 存储结果
        key = f"item_{self._processing_count}"
        self._data[key] = processed_item

        self.logger.debug(f"Processed item {self._processing_count}")
        return processed_item

    async def get_item(self, item_id: int) -> Optional[Dict[str, Any]]:
        """获取处理过的数据项

        Args:
            item_id: 数据项ID

        Returns:
            数据项或None
        """
        key = f"item_{item_id}"
        return self._data.get(key)

    async def get_all_items(self) -> List[Dict[str, Any]]:
        """获取所有处理过的数据项"""
        return list(self._data.values())

    async def clear_data(self) -> int:
        """清空所有数据

        Returns:
            清除的数据项数量
        """
        count = len(self._data)
        self._data.clear()
        self._processing_count = 0
        self.logger.info(f"Cleared {count} items")
        return count

    async def health_check(self) -> Dict[str, Any]:
        """执行健康检查"""
        health_info = await super().health_check()

        # 添加服务特定的健康检查
        if self._initialized:
            health_info["details"].update(
                {
                    "data_count": len(self._data),
                    "processing_count": self._processing_count,
                    "memory_usage": self._estimate_memory_usage(),
                    "status": "healthy",
                }
            )
        else:
            health_info["details"]["status"] = "not_initialized"

        return health_info

    def _get_current_timestamp(self) -> str:
        """获取当前时间戳"""
        from datetime import datetime

        return datetime.now().isoformat()

    def _estimate_memory_usage(self) -> str:
        """估算内存使用量"""
        import sys

        size = sys.getsizeof(self._data)
        if size < 1024:
            return f"{size} bytes"
        elif size < 1024 * 1024:
            return f"{size / 1024:.2f} KB"
        else:
            return f"{size / (1024 * 1024):.2f} MB"


# 示例使用函数
async def example_usage():
    """演示如何使用ExampleService"""
    # 创建服务
    service = ExampleService()

    try:
        # 启动服务
        if await service.start():
            print("Service started successfully")

            # 处理一些数据
            for i in range(5):
                item = {"message": f"Test item {i}", "value": i * 10}
                result = await service.process_data(item)
                print(f"Processed: {result}")

            # 获取健康状态
            health = await service.health_check()
            print(f"\nHealth Status: {health}")

            # 获取所有数据
            items = await service.get_all_items()
            print(f"\nTotal items: {len(items)}")

        # 停止服务
        await service.stop()
        print("\nService stopped")

    except Exception as e:
        print(f"Error: {e}")
        await service.stop()


if __name__ == "__main__":
    # 运行示例
    asyncio.run(example_usage())
