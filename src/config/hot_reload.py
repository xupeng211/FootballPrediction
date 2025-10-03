"""
配置热重载模块
Configuration Hot Reload Module

监控配置文件变化并自动重载配置
"""

import os
import sys
import logging
import asyncio
import signal
from pathlib import Path
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass, field
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent
import yaml
import json
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


@dataclass
class ReloadEvent:
    """重载事件"""
    file_path: Path
    timestamp: float
    changes: Dict[str, Any] = field(default_factory=dict)
    error: Optional[Exception] = None


class ConfigReloadHandler(FileSystemEventHandler):
    """配置文件变化处理器"""

    def __init__(self, callback: Callable[[ReloadEvent], None],
                 extensions: List[str] = None):
        """
        初始化处理器

        Args:
            callback: 回调函数
            extensions: 监控的文件扩展名
        """
        super().__init__()
        self.callback = callback
        self.extensions = extensions or ['.env', '.yml', '.yaml', '.json']
        self.last_reload = 0
        self.debounce_seconds = 1  # 防抖时间

    def on_modified(self, event):
        """文件修改事件"""
        if event.is_directory:
            return

        file_path = Path(event.src_path)
        if file_path.suffix not in self.extensions:
            return

        # 防抖处理
        import time
        current_time = time.time()
        if current_time - self.last_reload < self.debounce_seconds:
            return

        self.last_reload = current_time
        logger.info(f"检测到配置文件变化: {file_path}")

        try:
            # 读取变化
            changes = self._read_changes(file_path)

            # 创建重载事件
            reload_event = ReloadEvent(
                file_path=file_path,
                timestamp=current_time,
                changes=changes
            )

            # 调用回调
            self.callback(reload_event)

        except Exception as e:
            logger.error(f"处理配置文件变化失败: {e}")
            reload_event = ReloadEvent(
                file_path=file_path,
                timestamp=current_time,
                error=e
            )
            self.callback(reload_event)

    def _read_changes(self, file_path: Path) -> Dict[str, Any]:
        """读取文件变化"""
        changes = {}

        if file_path.suffix == '.env':
            # 解析.env文件
            changes['type'] = 'env'
            changes['variables'] = {}
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        changes['variables'][key.strip()] = value.strip()

        elif file_path.suffix in ['.yml', '.yaml']:
            # 解析YAML文件
            changes['type'] = 'yaml'
            with open(file_path, 'r', encoding='utf-8') as f:
                changes['content'] = yaml.safe_load(f)

        elif file_path.suffix == '.json':
            # 解析JSON文件
            changes['type'] = 'json'
            with open(file_path, 'r', encoding='utf-8') as f:
                changes['content'] = json.load(f)

        return changes


class ConfigHotReload:
    """配置热重载管理器"""

    def __init__(self, watch_directories: List[Path] = None):
        """
        初始化热重载管理器

        Args:
            watch_directories: 监控的目录列表
        """
        self.watch_directories = watch_directories or [Path.cwd()]
        self.observers: List[Observer] = []
        self.reload_callbacks: List[Callable[[ReloadEvent], None]] = []
        self.config_cache: Dict[str, Any] = {}
        self.running = False
        self._setup_signal_handlers()

    def _setup_signal_handlers(self):
        """设置信号处理器"""
        # Windows不支持所有信号
        if sys.platform != 'win32':
            signal.signal(signal.SIGUSR1, self._signal_handler)
            signal.signal(signal.SIGHUP, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """信号处理器"""
        logger.info(f"收到信号 {signum}，触发配置重载")
        self.reload_all()

    def add_callback(self, callback: Callable[[ReloadEvent], None]):
        """添加重载回调"""
        self.reload_callbacks.append(callback)

    def add_watch_directory(self, directory: Path):
        """添加监控目录"""
        if directory not in self.watch_directories:
            self.watch_directories.append(directory)

    def start(self):
        """启动热重载监控"""
        if self.running:
            logger.warning("热重载已在运行")
            return

        logger.info("启动配置热重载监控")

        # 创建文件系统观察者
        for directory in self.watch_directories:
            if directory.exists():
                observer = Observer()
                handler = ConfigReloadHandler(self._on_config_changed)
                observer.schedule(handler, str(directory), recursive=False)
                observer.start()
                self.observers.append(observer)
                logger.info(f"监控目录: {directory}")
            else:
                logger.warning(f"目录不存在: {directory}")

        self.running = True

    def stop(self):
        """停止热重载监控"""
        if not self.running:
            return

        logger.info("停止配置热重载监控")

        for observer in self.observers:
            observer.stop()
            observer.join()

        self.observers.clear()
        self.running = False

    def _on_config_changed(self, event: ReloadEvent):
        """配置变化处理"""
        logger.info(f"处理配置变化: {event.file_path}")

        # 更新缓存
        self._update_cache(event)

        # 通知所有回调
        for callback in self.reload_callbacks:
            try:
                callback(event)
            except Exception as e:
                logger.error(f"重载回调执行失败: {e}")

    def _update_cache(self, event: ReloadEvent):
        """更新配置缓存"""
        file_path = event.file_path
        key = str(file_path)

        if event.error:
            logger.error(f"缓存更新失败: {event.error}")
            return

        if event.changes.get('type') == 'env':
            # 更新环境变量
            if key not in self.config_cache:
                self.config_cache[key] = {}

            old_vars = self.config_cache[key].get('variables', {})
            new_vars = event.changes.get('variables', {})

            # 检测变化
            changed_vars = {}
            for var_name, new_value in new_vars.items():
                if old_vars.get(var_name) != new_value:
                    changed_vars[var_name] = {
                        'old': old_vars.get(var_name),
                        'new': new_value
                    }
                    # 更新环境变量
                    os.environ[var_name] = new_value

            self.config_cache[key] = event.changes

            if changed_vars:
                logger.info(f"环境变量变化: {changed_vars}")

        else:
            # 更新配置文件缓存
            self.config_cache[key] = event.changes.get('content', {})
            logger.info(f"配置文件缓存已更新: {file_path}")

    def reload_all(self):
        """手动重载所有配置"""
        logger.info("手动触发配置重载")

        for directory in self.watch_directories:
            for file_path in directory.iterdir():
                if file_path.is_file() and file_path.suffix in ['.env', '.yml', '.yaml', '.json']:
                    try:
                        changes = {}
                        if file_path.suffix == '.env':
                            with open(file_path, 'r', encoding='utf-8') as f:
                                changes['variables'] = {}
                                for line in f:
                                    line = line.strip()
                                    if line and not line.startswith('#') and '=' in line:
                                        key, value = line.split('=', 1)
                                        changes['variables'][key.strip()] = value.strip()
                                        os.environ[key.strip()] = value.strip()
                            changes['type'] = 'env'
                        elif file_path.suffix in ['.yml', '.yaml']:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                changes['content'] = yaml.safe_load(f)
                            changes['type'] = 'yaml'
                        elif file_path.suffix == '.json':
                            with open(file_path, 'r', encoding='utf-8') as f:
                                changes['content'] = json.load(f)
                            changes['type'] = 'json'

                        event = ReloadEvent(
                            file_path=file_path,
                            timestamp=0,
                            changes=changes
                        )
                        self._on_config_changed(event)

                    except Exception as e:
                        logger.error(f"重载配置文件失败 {file_path}: {e}")

    def get_config(self, file_path: Path) -> Any:
        """获取缓存的配置"""
        key = str(file_path)
        return self.config_cache.get(key)

    def is_running(self) -> bool:
        """检查是否正在运行"""
        return self.running


class ConfigReloader:
    """配置重载器（用于应用集成）"""

    def __init__(self, config_file: Path = None):
        """
        初始化配置重载器

        Args:
            config_file: 配置文件路径
        """
        self.config_file = config_file or Path.cwd() / ".env"
        self.hot_reload = ConfigHotReload([self.config_file.parent])
        self.reload_listeners: List[Callable] = []
        self.current_config: Dict[str, Any] = {}
        self._load_initial_config()
        self._setup_hot_reload()

    def _load_initial_config(self):
        """加载初始配置"""
        if self.config_file.exists():
            load_dotenv(self.config_file)
            logger.info(f"已加载初始配置: {self.config_file}")
        else:
            logger.warning(f"配置文件不存在: {self.config_file}")

        # 保存当前配置
        self.current_config = dict(os.environ)

    def _setup_hot_reload(self):
        """设置热重载"""
        self.hot_reload.add_callback(self._on_reload)

    def _on_reload(self, event: ReloadEvent):
        """重载事件处理"""
        if event.file_path == self.config_file:
            logger.info("重载配置文件...")

            # 保存旧配置
            old_config = self.current_config.copy()

            # 通知监听器
            for listener in self.reload_listeners:
                try:
                    listener(old_config, dict(os.environ), event)
                except Exception as e:
                    logger.error(f"配置重载监听器执行失败: {e}")

            # 更新当前配置
            self.current_config = dict(os.environ)

            logger.info("配置重载完成")

    def add_reload_listener(self, listener: Callable[[Dict, Dict, ReloadEvent], None]):
        """
        添加重载监听器

        Args:
            listener: 监听器函数，接收(old_config, new_config, event)参数
        """
        self.reload_listeners.append(listener)

    def start(self):
        """启动热重载"""
        self.hot_reload.start()

    def stop(self):
        """停止热重载"""
        self.hot_reload.stop()

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值"""
        return os.getenv(key, default)

    def reload(self):
        """手动重载配置"""
        self.hot_reload.reload_all()


# 全局配置重载器实例
_config_reloader: Optional[ConfigReloader] = None


def get_config_reloader() -> Optional[ConfigReloader]:
    """获取全局配置重载器"""
    return _config_reloader


def init_config_reloader(config_file: Path = None) -> ConfigReloader:
    """
    初始化全局配置重载器

    Args:
        config_file: 配置文件路径

    Returns:
        配置重载器实例
    """
    global _config_reloader
    _config_reloader = ConfigReloader(config_file)
    return _config_reloader


def start_config_hot_reload(config_file: Path = None) -> ConfigReloader:
    """
    启动配置热重载

    Args:
        config_file: 配置文件路径

    Returns:
        配置重载器实例
    """
    reloader = init_config_reloader(config_file)
    reloader.start()
    return reloader


# 示例使用
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # 创建配置重载器
    reloader = start_config_hot_reload()

    # 添加重载监听器
    def on_config_reload(old_config, new_config, event):
        print("配置已重载！")
        # 检测变化的变量
        for key, new_value in new_config.items():
            if key.startswith('API_') and old_config.get(key) != new_value:
                print(f"  API配置变化: {key} = {new_value}")

    reloader.add_reload_listener(on_config_reload)

    try:
        print("配置热重载已启动，按Ctrl+C停止...")
        while True:
            import time
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n停止配置热重载...")
        reloader.stop()