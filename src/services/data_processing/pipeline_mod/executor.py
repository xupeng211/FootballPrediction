"""
executor
执行器

此模块从原始文件拆分而来。
This module was split from the original file.
"""

import asyncio
import logging
from typing import Any, Dict, List

from src.core.logging import get_logger

logger = get_logger(__name__)


class PipelineExecutor:
    """管道执行器"""

    def __init__(self, max_workers: int = 4):
        """初始化执行器"""
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.max_workers = max_workers
        self.semaphore = asyncio.Semaphore(max_workers)

    async def execute(self, pipeline, data: Dict[str, Any]) -> Dict[str, Any]:
        """执行单个管道"""
        async with self.semaphore:
            try:
                result = await pipeline.process(data)
                return {"success": True, "result": result, "error": None}
            except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
                self.logger.error(f"Pipeline execution failed: {str(e)}")
                return {"success": False, "result": None, "error": str(e)}

    async def execute_batch(
        self, pipeline, data_list: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """批量执行管道"""
        tasks = [self.execute(pipeline, data) for data in data_list]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 处理异常
        processed_results = []
        for result in results:
            if isinstance(result, Exception):
                processed_results.append(
                    {"success": False, "result": None, "error": str(result)}
                )
            else:
                processed_results.append(result)  # type: ignore

        return processed_results

    async def execute_parallel(
        self, pipelines: List[Any], data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """并行执行多个管道"""
        tasks = [self.execute(pipeline, data) for pipeline in pipelines]
        return await asyncio.gather(*tasks, return_exceptions=True)  # type: ignore
