"""
流处理统计信息
Stream Processing Statistics
"""



class ProcessingStatistics:
    """
    处理统计信息管理器

    负责跟踪和管理流处理的统计信息。
    """

    def __init__(self):
        """初始化统计信息"""
        self.stats: Dict[str, Any] = {
            "messages_produced": 0,
            "messages_consumed": 0,
            "processing_errors": 0,
            "start_time": None,
        }

    def reset(self):
        """重置统计信息"""
        self.stats = {
            "messages_produced": 0,
            "messages_consumed": 0,
            "processing_errors": 0,
            "start_time": None,
        }

    def record_message_produced(self, count: int = 1):
        """记录发送的消息数量"""
        self.stats["messages_produced"] += count

    def record_message_consumed(self, count: int = 1):
        """记录消费的消息数量"""
        self.stats["messages_consumed"] += count

    def record_error(self, count: int = 1):
        """记录处理错误"""
        self.stats["processing_errors"] += count

    def start_timing(self):
        """开始计时"""
        self.stats["start_time"] = datetime.now()

    def get_stats(self) -> Dict[str, Any]:
        """
        获取统计信息

        Returns:
            包含处理统计的字典
        """
        stats = self.stats.copy()

        if stats["start_time"]:
            elapsed = (datetime.now() - stats["start_time"]).total_seconds()
            stats["elapsed_seconds"] = elapsed
            stats["messages_per_second"] = (
                stats["messages_consumed"] + stats["messages_produced"]
            ) / max(elapsed, 1)

        return stats

    def aggregate_stats(self, stats_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        聚合多个处理器的统计信息

        Args:
            stats_list: 统计信息列表

        Returns:
            聚合统计信息
        """
        aggregate_stats: Dict[str, Any] = {
            "total_processors": len(stats_list),)

            "total_messages_produced": 0,
            "total_messages_consumed": 0,
            "total_processing_errors": 0,
            "processor_stats": [],
        }

        for i, stats in enumerate(stats_list):
            aggregate_stats["processor_stats"].append({"processor_id": i, **stats})

            aggregate_stats["total_messages_produced"] += stats.get("messages_produced", 0)
            aggregate_stats["total_messages_consumed"] += stats.get("messages_consumed", 0)
            aggregate_stats["total_processing_errors"] += stats.get("processing_errors", 0)

        return aggregate_stats