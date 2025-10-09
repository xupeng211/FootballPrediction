"""
系统资源收集器

收集系统级别的资源使用指标。
"""




logger = logging.getLogger(__name__)


class SystemCollector:
    """系统资源收集器"""

    def __init__(self, metrics: SystemMetrics, start_time: float):
        """
        初始化系统收集器

        Args:
            metrics: 系统指标实例
            start_time: 应用启动时间
        """
        self.metrics = metrics
        self.start_time = start_time
        self.process = psutil.Process()

    async def collect(self) -> Dict[str, float]:
        """
        收集系统资源指标

        Returns:
            收集到的指标值
        """
        try:
            metrics_data = {}

            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=1)
            self.metrics.system_cpu_percent.set(cpu_percent)
            metrics_data["cpu_percent"] = cpu_percent

            # 内存使用率
            memory = psutil.virtual_memory()
            self.metrics.system_memory_percent.set(memory.percent)
            metrics_data["memory_percent"] = memory.percent

            # 磁盘使用率
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            self.metrics.system_disk_percent.set(disk_percent)
            metrics_data["disk_percent"] = disk_percent

            # 进程内存使用
            process_memory = self.process.memory_info()
            self.metrics.process_memory_bytes.set(process_memory.rss)
            metrics_data["process_memory_bytes"] = process_memory.rss

            # 进程CPU使用率
            process_cpu = self.process.cpu_percent()
            self.metrics.process_cpu_percent.set(process_cpu)
            metrics_data["process_cpu_percent"] = process_cpu

            # 应用运行时间
            uptime = time.time() - self.start_time
            self.metrics.app_uptime_seconds.set(uptime)
            metrics_data["uptime_seconds"] = uptime

            logger.debug(f"系统指标收集完成: {metrics_data}")
            return metrics_data

        except Exception as e:
            logger.error(f"收集系统指标失败: {e}")
            return {}

    def get_system_info(self) -> Dict[str, any]:
        """
        获取系统信息

        Returns:
            系统信息字典
        """
        try:
            boot_time = psutil.boot_time()
            uptime = time.time() - boot_time

            return {



                "cpu_count": psutil.cpu_count(),
                "cpu_count_logical": psutil.cpu_count(logical=True),
                "memory_total": psutil.virtual_memory().total,
                "memory_available": psutil.virtual_memory().available,
                "disk_total": psutil.disk_usage('/').total,
                "disk_free": psutil.disk_usage('/').free,
                "boot_time": boot_time,
                "system_uptime": uptime,
                "process_count": len(psutil.pids()),
                "process_pid": self.process.pid,
                "process_create_time": self.process.create_time(),
            }
        except Exception as e:
            logger.error(f"获取系统信息失败: {e}")
            return {}