"""

"""



    """服务工厂 - 负责创建和配置服务实例"""


        """注册服务构建器"""

        """注册服务类"""

        """设置服务配置"""

        """创建服务实例"""


        """应用配置到服务"""

        """从设置创建服务"""





        """获取所有注册的服务"""



from typing import Dict, Any, Callable
from ..base import BaseService
from src.core import logger
from src.core.config import get_settings

服务工厂
提供服务创建和配置的工厂模式实现。
class ServiceFactory:
    def __init__(self) -> None:
        self._builders: Dict[str, Callable[[], BaseService]] = {}
        self._configs: Dict[str, Dict[str, Any]] = {}
        self.logger = logger
    def register_builder(self, name: str, builder: Callable[[], BaseService]) -> None:
        if name in self._builders:
            self.logger.warning(f"替换服务构建器: {name}")
        self._builders[name] = builder
        self.logger.debug(f"已注册服务构建器: {name}")
    def register_class(self, name: str, service_class: Type[BaseService]) -> None:
        def builder() -> BaseService:
            return service_class()
        self.register_builder(name, builder)
    def set_config(self, name: str, config: Dict[str, Any]) -> None:
        self._configs[name] = config
        self.logger.debug(f"已设置服务配置: {name}")
    def create_service(self, name: str) -> Optional[BaseService]:
        builder = self._builders.get(name)
        if not builder:
            self.logger.error(f"未找到服务构建器: {name}")
            return None
        try:
            service = builder()
            # 应用配置
            if name in self._configs:
                self._apply_config(service, self._configs[name])
            return service
        except Exception as e:
            self.logger.error(f"创建服务失败: {name}, {e}")
            return None
    def _apply_config(self, service: BaseService, config: Dict[str, Any]) -> None:
        for key, value in config.items():
            if hasattr(service, key):
                setattr(service, key, value)
            else:
                self.logger.warning(f"服务没有配置属性: {service.name}.{key}")
    def create_from_settings(self, service_name: str) -> Optional[BaseService]:
        settings = get_settings()
        service_settings = getattr(settings, 'services', {})
        if service_name not in service_settings:
            self.logger.warning(f"设置中未找到服务配置: {service_name}")
            return self.create_service(service_name)
        config = service_settings[service_name]
        service_type = config.get('type', service_name)
        # 创建服务
        service = self.create_service(service_type)
        if service:
            # 应用额外配置
            extra_config = {k: v for k, v in config.items() if k != 'type'}
            if extra_config:
                self._apply_config(service, extra_config)
        return service
    def get_registered_services(self) -> list:
        return list(self._builders.keys())