"""
pipeline
主管道

此模块从原始文件拆分而来。
This module was split from the original file.
"""

import asyncio
import logging
from typing import Any, Dict, List

from .stages import BronzeToSilverProcessor, SilverToGoldProcessor
from src.core.logging import get_logger

logger = get_logger(__name__)


class DataPipeline:
    """数据处理管道"""

    def __init__(self):
        """初始化管道"""
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.stages = []
        self.bronze_to_silver = BronzeToSilverProcessor()
        self.silver_to_gold = SilverToGoldProcessor()

    def add_stage(self, stage):
        """添加处理阶段"""
        self.stages.append(stage)

    async def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """处理数据通过所有阶段"""
        current_data = data

        # Bronze to Silver
        current_data = await self.bronze_to_silver.process(current_data)

        # Process additional stages
        for stage in self.stages:
            if hasattr(stage, "process"):
                current_data = await stage.process(current_data)
            elif callable(stage):
                current_data = await stage(current_data)

        # Silver to Gold
        current_data = await self.silver_to_gold.process(current_data)

        return current_data

    async def process_batch(
        self, data_list: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """批量处理数据"""
        tasks = [self.process(data) for data in data_list]
        return await asyncio.gather(*tasks)


class PipelineBuilder:
    """管道构建器"""

    def __init__(self):
        """初始化构建器"""
        self.pipeline = DataPipeline()

    def add_validator(self, validator):
        """添加验证器"""
        self.pipeline.add_stage(validator)
        return self

    def add_transformer(self, transformer):
        """添加转换器"""
        self.pipeline.add_stage(transformer)
        return self

    def build(self) -> DataPipeline:
        """构建管道"""
        return self.pipeline  # type: ignore
