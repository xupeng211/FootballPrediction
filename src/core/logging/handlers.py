"""
"""




    """日志处理器管理器"""


        """创建控制台处理器"""

        """创建文件处理器"""



        handler = logging.FileHandler(log_file, encoding="utf-8")
from typing import Optional
import logging

日志处理器
Logging Handlers
class LogHandlerManager:
    def __init__(self, name: str, enable_json: bool = True):
        self.name = name
        self.formatter = StructuredFormatter(enable_json).create_formatter()
    def create_console_handler(self) -> logging.StreamHandler:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(self.formatter)
        return handler
    def create_file_handler(self, log_file: Optional[str] = None) -> logging.FileHandler:
        if not log_file:
            log_dir = os.getenv("LOG_DIR", "logs")
            os.makedirs(log_dir, exist_ok=True)
            log_file = os.path.join(log_dir, f"{self.name}.log")
        handler.setFormatter(self.formatter)
        return handler