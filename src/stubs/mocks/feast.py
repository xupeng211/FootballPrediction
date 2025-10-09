



    """特征视图"""



    """实体"""



    """特征服务"""



    """值类型常量"""



    """模拟特征存储"""


        """初始化特征存储"""

        """应用特征定义"""

        """获取特征视图"""

        """获取实体"""

        """获取特征服务"""

        """列出所有特征视图"""

        """列出所有实体"""

        """列出所有特征服务"""

        """获取在线特征"""







        """获取特征的默认值"""

        """写入在线存储"""

        """增量物化"""

        """清理特征存储"""

        """添加测试数据"""

        """清除测试数据"""


    """模拟特征服务"""


        """获取特征向量"""


    """模拟Feast客户端"""


        """应用特征定义"""

        """获取在线特征"""

        """启动服务"""

        """获取特征服务"""


    """模拟在线特征响应"""


        """转换为字典"""

        """转换为DataFrame(mock)"""


        """获取特征名称列表"""

        """返回响应长度"""

        """迭代器"""


    """创建特征存储"""


    """创建Feast客户端"""


    """生成测试特征数据"""




    """获取全局特征存储实例"""


    """重置全局特征存储"""



        import pandas as pd
from collections import defaultdict
from typing import Dict, List, Optional, Any

Feast Feature Store Mock 实现
用于测试环境,避免真实的Feast依赖
logger = logging.getLogger(__name__)
@dataclass
class FeatureView:
    name: str
    entities: List[str]
    features: List[str]
    ttl: Optional[timedelta] = None
    batch_source: Optional[str] = None
    stream_source: Optional[str] = None
    tags: Optional[Dict[str, str]] = None
@dataclass
class Entity:
    name: str
    value_type: str
    description: Optional[str] = None
    tags: Optional[Dict[str, str]] = None
@dataclass
class FeatureService:
    name: str
    features: List[str]
    tags: Optional[Dict[str, str]] = None
class ValueType:
    INT64 = "INT64"
    INT32 = "INT32"
    FLOAT = "FLOAT"
    DOUBLE = "DOUBLE"
    STRING = "STRING"
    BYTES = "BYTES"
    BOOL = "BOOL"
    UNIX_TIMESTAMP = "UNIX_TIMESTAMP"
class MockFeatureStore:
    def __init__(
        self, repo_path: Optional[str] = None, config_path: Optional[str] = None
    ):
        self.repo_path = repo_path
        self.config_path = config_path
        self._feature_views: Dict[str, FeatureView] = {}
        self._entities: Dict[str, Entity] = {}
        self._feature_services: Dict[str, FeatureService] = {}
        self._feature_data: Dict[str, Dict[str, Any]] = defaultdict(dict)
        self._initialized = False
    def init(self) -> None:
        self._initialized = True
        logger.info("Mock Feature Store initialized")
    def apply(self, objects: List[Any]) -> None:
        for obj in objects:
            if isinstance(obj, FeatureView):
                self._feature_views[obj.name] = obj
                logger.info(f"Applied FeatureView: {obj.name}")
            elif isinstance(obj, Entity):
                self._entities[obj.name] = obj
                logger.info(f"Applied Entity: {obj.name}")
            elif isinstance(obj, FeatureService):
                self._feature_services[obj.name] = obj
                logger.info(f"Applied FeatureService: {obj.name}")
    def get_feature_view(self, name: str) -> Optional[FeatureView]:
        return self._feature_views.get(name)
    def get_entity(self, name: str) -> Optional[Entity]:
        return self._entities.get(name)
    def get_feature_service(self, name: str) -> Optional[FeatureService]:
        return self._feature_services.get(name)
    def list_feature_views(self) -> List[FeatureView]:
        return list(self._feature_views.values())
    def list_entities(self) -> List[Entity]:
        return list(self._entities.values())
    def list_feature_services(self) -> List[FeatureService]:
        return list(self._feature_services.values())
    def get_online_features(
        self, feature_refs: List[str], entity_rows: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], List[str]]:
        features: List[Any] = []
        field_names = []
        # 解析特征引用
        for ref in feature_refs:
            parts = ref.split(":")
            feature_view = parts[0]
            feature_name = parts[1] if len(parts) > 1 else parts[0]
            field_names.append(f"{feature_view}__{feature_name}")
        # 为每个实体行生成特征
        for entity_row in entity_rows:
            row_features = {}
            entity_key = str(entity_row.get("entity_id", "unknown"))
            # 获取特征数据
            for ref in feature_refs:
                parts = ref.split(":")
                feature_view = parts[0]
                feature_name = parts[1] if len(parts) > 1 else parts[0]
                key = f"{feature_view}__{feature_name}"
                # 查找特征值
                if (
                    entity_key in self._feature_data
                    and key in self._feature_data[entity_key]
                ):
                    row_features[key] = self._feature_data[entity_key][key]
                else:
                    # 返回默认值
                    row_features[key] = self._get_default_value(feature_name)
            features.append(row_features)
        return features, field_names
    def _get_default_value(self, feature_name: str) -> Any:
        if "count" in feature_name.lower() or "num" in feature_name.lower():
            return 0
        elif "ratio" in feature_name.lower() or "rate" in feature_name.lower():
            return 0.0
        elif "is" in feature_name.lower() or "has" in feature_name.lower():
            return False
        else:
            return None
    def write_to_online_store(
        self,
        feature_view_name: str,
        df: Any,  # DataFrame-like object
        registry: Any = None,
    ) -> None:
        logger.info(f"Writing to online store for {feature_view_name}")
        # Mock实现 - 不实际写入
    def materialize_incremental(
        self, start_date: datetime, end_date: datetime, feature_views: List[str] = None
    ) -> None:
        logger.info(
            f"Materializing incremental features from {start_date} to {end_date}"
        )
    def teardown(self) -> None:
        self._feature_views.clear()
        self._entities.clear()
        self._feature_services.clear()
        self._feature_data.clear()
        self._initialized = False
        logger.info("Mock Feature Store torn down")
    def add_test_data(self, entity_id: str, features: Dict[str, Any]) -> None:
        self._feature_data[entity_id].update(features)
    def clear_test_data(self) -> None:
        self._feature_data.clear()
class MockFeatureService:
    def __init__(self, name: str, feature_store: MockFeatureStore):
        self.name = name
        self.feature_store = feature_store
        self._service_config: Optional[Dict[str, Any]] = None
    def get_feature_vector(
        self, entity_id: str, feature_refs: List[str]
    ) -> Dict[str, Any]:
        entity_rows = [{"entity_id": entity_id}]
        features, _ = self.feature_store.get_online_features(feature_refs, entity_rows)
        return features[0] if features else {}
class MockFeastClient:
    def __init__(
        self, repo_path: Optional[str] = None, config_path: Optional[str] = None
    ):
        self.feature_store = MockFeatureStore(repo_path, config_path)
        self._services: Dict[str, MockFeatureService] = {}
    def apply(self, objects: List[Any]) -> None:
        self.feature_store.apply(objects)
    def get_online_features(
        self, feature_refs: List[str], entity_rows: List[Dict[str, Any]]
    ) -> "MockOnlineResponse":
        features, field_names = self.feature_store.get_online_features(
            feature_refs, entity_rows
        )
        return MockOnlineResponse(features, field_names)
    def serve(self, port: int = 6566) -> None:
        logger.info(f"Mock Feast client serving on port {port}")
    def get_feature_service(self, name: str) -> MockFeatureService:
        if name not in self._services:
            self._services[name] = MockFeatureService(name, self.feature_store)
        return self._services[name]
class MockOnlineResponse:
    def __init__(self, features: List[Dict[str, Any]], field_names: List[str]):
        self._features = features
        self._field_names = field_names
        self._to_dict_called = False
    def to_dict(self) -> List[Dict[str, Any]]:
        self._to_dict_called = True
        return self._features
    def to_df(self) -> Any:
        return pd.DataFrame(self._features, columns=self._field_names)
    @property
    def feature_names(self) -> List[str]:
        return self._field_names
    def __len__(self) -> int:
        return len(self._features)
    def __iter__(self):
        return iter(self._features)
# 便捷函数
def FeatureStore(repo_path: str = None, config_path: str = None) -> MockFeatureStore:
    return MockFeatureStore(repo_path, config_path)
def Client(repo_path: str = None, config_path: str = None) -> MockFeastClient:
    return MockFeastClient(repo_path, config_path)
# 测试数据生成器
def generate_test_features(entity_id: str) -> Dict[str, Any]:
    return {
        "match_stats__goals_scored": 2,
        "match_stats__goals_conceded": 1,
        "match_stats__possession": 65.5,
        "match_stats__shots": 12,
        "match_stats__shots_on_target": 5,
        "team_form__last_5_matches_wins": 3,
        "team_form__last_5_matches_draws": 1,
        "team_form__last_5_matches_losses": 1,
        "team_form__current_streak": "W",
        "player_stats__avg_rating": 7.2,
        "player_stats__goals": 8,
        "player_stats__assists": 3,
        "historical__head_to_head_wins": 5,
        "historical__head_to_head_losses": 3,
        "historical__head_to_head_draws": 2,
    }
# 创建全局实例
global_feast_store: Optional[MockFeatureStore] = None
def get_feast_store() -> MockFeatureStore:
    global global_feast_store
    if global_feast_store is None:
        global_feast_store = MockFeatureStore()
        global_feast_store.init()
    return global_feast_store
def reset_feast_store() -> None:
    global global_feast_store
    if global_feast_store:
        global_feast_store.teardown()
    global_feast_store = None