"""
元数据管理器

管理数据集、作业、运行等元数据信息，提供统一的元数据访问接口。
与 Marquez 服务配合，实现完整的数据治理功能。
"""

import logging
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import requests

logger = logging.getLogger(__name__)


class MetadataManager:
    """
    元数据管理器

    提供数据集、作业、运行等元数据的管理功能。
    与 Marquez API 交互，实现元数据的增删改查。
    """

    def __init__(self, marquez_url: str = "http://localhost:5000"):
        """
        初始化元数据管理器

        Args:
            marquez_url: Marquez 服务URL
        """
        self.marquez_url = marquez_url
        self.base_url = marquez_url
        self.api_url = urljoin(marquez_url, "/api/v1/")
        self.session = requests.Session()
        self.session.headers.update(
            {"Content-Type": "application/json", "Accept": "application/json"}
        )

    def create_namespace(
        self,
        name: str,
        description: Optional[str] = None,
        owner_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        创建命名空间

        Args:
            name: 命名空间名称
            description: 描述
            owner_name: 所有者名称

        Returns:
            Dict[str, Any]: 创建结果
        """
        payload = {"name": name, "description": description or f"命名空间: {name}"}

        if owner_name:
            payload["ownerName"] = owner_name

        try:
            response = self.session.put(
                urljoin(self.api_url, f"namespaces/{name}"), json=payload
            )
            response.raise_for_status()

            result = response.json()
            logger.info(f"创建命名空间成功: {name}")
            return result

        except requests.exceptions.RequestException as e:
            logger.error(f"创建命名空间失败 {name}: {e}")
            raise

    def create_dataset(
        self,
        namespace: str,
        name: str,
        description: Optional[str] = None,
        schema_fields: Optional[List[Dict[str, str]]] = None,
        source_name: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        创建数据集

        Args:
            namespace: 命名空间
            name: 数据集名称
            description: 描述
            schema_fields: Schema字段定义
            source_name: 数据源名称
            tags: 标签列表

        Returns:
            Dict[str, Any]: 创建结果
        """
        payload: Dict[str, Any] = {
            "name": name,
            "description": description or f"数据集: {name}",
            "type": "DB_TABLE",
        }

        # 添加Schema信息
        if schema_fields:
            fields_list: List[Dict[str, Any]] = []
            for field in schema_fields:
                field_def = {"name": field["name"], "type": field["type"]}
                if "description" in field:
                    field_def["description"] = field["description"]
                fields_list.append(field_def)
            payload["fields"] = fields_list

        # 添加标签
        if tags:
            payload["tags"] = tags

        # 添加数据源信息
        if source_name:
            payload["sourceName"] = source_name

        try:
            response = self.session.put(
                urljoin(self.api_url, f"namespaces/{namespace}/datasets/{name}"),
                json=payload,
            )
            response.raise_for_status()

            result = response.json()
            logger.info(f"创建数据集成功: {namespace}.{name}")
            return result

        except requests.exceptions.RequestException as e:
            logger.error(f"创建数据集失败 {namespace}.{name}: {e}")
            raise

    def create_job(
        self,
        namespace: str,
        name: str,
        description: Optional[str] = None,
        job_type: str = "BATCH",
        input_datasets: Optional[List[Dict[str, str]]] = None,
        output_datasets: Optional[List[Dict[str, str]]] = None,
        location: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        创建作业

        Args:
            namespace: 命名空间
            name: 作业名称
            description: 描述
            job_type: 作业类型（BATCH/STREAM）
            input_datasets: 输入数据集列表
            output_datasets: 输出数据集列表
            location: 代码位置

        Returns:
            Dict[str, Any]: 创建结果
        """
        payload: Dict[str, Any] = {
            "name": name,
            "description": description or f"作业: {name}",
            "type": job_type,
        }

        # 添加输入数据集
        if input_datasets:
            inputs_list: List[Dict[str, str]] = []
            for dataset in input_datasets:
                inputs_list.append(
                    {"namespace": dataset["namespace"], "name": dataset["name"]}
                )
            payload["inputs"] = inputs_list

        # 添加输出数据集
        if output_datasets:
            outputs_list: List[Dict[str, str]] = []
            for dataset in output_datasets:
                outputs_list.append(
                    {"namespace": dataset["namespace"], "name": dataset["name"]}
                )
            payload["outputs"] = outputs_list

        # 添加代码位置
        if location:
            payload["location"] = location

        try:
            response = self.session.put(
                urljoin(self.api_url, f"namespaces/{namespace}/jobs/{name}"),
                json=payload,
            )
            response.raise_for_status()

            result = response.json()
            logger.info(f"创建作业成功: {namespace}.{name}")
            return result

        except requests.exceptions.RequestException as e:
            logger.error(f"创建作业失败 {namespace}.{name}: {e}")
            raise

    def get_dataset_lineage(
        self, namespace: str, name: str, depth: int = 3
    ) -> Dict[str, Any]:
        """
        获取数据集血缘关系

        Args:
            namespace: 命名空间
            name: 数据集名称
            depth: 血缘深度

        Returns:
            Dict[str, Any]: 血缘关系图
        """
        try:
            response = self.session.get(
                urljoin(self.api_url, "lineage"),
                params={"nodeId": f"dataset:{namespace}:{name}", "depth": str(depth)},
            )
            response.raise_for_status()

            result = response.json()
            logger.info(f"获取数据集血缘成功: {namespace}.{name}")
            return result

        except requests.exceptions.RequestException as e:
            logger.error(f"获取数据集血缘失败 {namespace}.{name}: {e}")
            raise

    def search_datasets(
        self, query: str, namespace: Optional[str] = None, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        搜索数据集

        Args:
            query: 搜索关键词
            namespace: 限制在特定命名空间
            limit: 返回结果数量限制

        Returns:
            List[Dict[str, Any]]: 搜索结果列表
        """
        params = {"q": query, "limit": str(limit)}

        if namespace:
            params["namespace"] = namespace

        try:
            response = self.session.get(urljoin(self.api_url, "search"), params=params)
            response.raise_for_status()

            result = response.json()
            datasets = result.get("results", [])
            logger.info(f"搜索数据集成功，找到 {len(datasets)} 个结果")
            return datasets

        except requests.exceptions.RequestException as e:
            logger.error(f"搜索数据集失败: {e}")
            raise

    def get_dataset_versions(self, namespace: str, name: str) -> List[Dict[str, Any]]:
        """
        获取数据集版本历史

        Args:
            namespace: 命名空间
            name: 数据集名称

        Returns:
            List[Dict[str, Any]]: 版本历史列表
        """
        try:
            response = self.session.get(
                urljoin(
                    self.api_url, f"namespaces/{namespace}/datasets/{name}/versions"
                )
            )
            response.raise_for_status()

            result = response.json()
            versions = result.get("versions", [])
            logger.info(
                f"获取数据集版本成功: {namespace}.{name}, 共 {len(versions)} 个版本"
            )
            return versions

        except requests.exceptions.RequestException as e:
            logger.error(f"获取数据集版本失败 {namespace}.{name}: {e}")
            raise

    def get_job_runs(
        self, namespace: str, job_name: str, limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        获取作业运行历史

        Args:
            namespace: 命名空间
            job_name: 作业名称
            limit: 返回数量限制

        Returns:
            List[Dict[str, Any]]: 运行历史列表
        """
        try:
            response = self.session.get(
                urljoin(self.api_url, f"namespaces/{namespace}/jobs/{job_name}/runs"),
                params={"limit": limit},
            )
            response.raise_for_status()

            result = response.json()
            runs = result.get("runs", [])
            logger.info(
                f"获取作业运行历史成功: {namespace}.{job_name}, 共 {len(runs)} 条记录"
            )
            return runs

        except requests.exceptions.RequestException as e:
            logger.error(f"获取作业运行历史失败 {namespace}.{job_name}: {e}")
            raise

    def add_dataset_tag(self, namespace: str, name: str, tag: str) -> Dict[str, Any]:
        """
        为数据集添加标签

        Args:
            namespace: 命名空间
            name: 数据集名称
            tag: 标签名称

        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            response = self.session.post(
                urljoin(
                    self.api_url, f"namespaces/{namespace}/datasets/{name}/tags/{tag}"
                )
            )
            response.raise_for_status()

            result = response.json()
            logger.info(f"添加数据集标签成功: {namespace}.{name} -> {tag}")
            return result

        except requests.exceptions.RequestException as e:
            logger.error(f"添加数据集标签失败 {namespace}.{name} -> {tag}: {e}")
            raise

    def setup_football_metadata(self) -> None:
        """
        初始化足球预测平台的元数据结构
        """
        try:
            # 创建命名空间
            namespaces = [
                {
                    "name": "football_prediction",
                    "description": "足球预测平台核心数据",
                    "owner": "data_team",
                },
                {
                    "name": "external_apis",
                    "description": "外部API数据源",
                    "owner": "data_team",
                },
                {
                    "name": "football_db.bronze",
                    "description": "原始数据层（Bronze）",
                    "owner": "data_team",
                },
                {
                    "name": "football_db.silver",
                    "description": "清洗数据层（Silver）",
                    "owner": "data_team",
                },
                {
                    "name": "football_db.gold",
                    "description": "特征数据层（Gold）",
                    "owner": "data_team",
                },
            ]

            for ns in namespaces:
                try:
                    self.create_namespace(
                        name=ns["name"],
                        description=ns["description"],
                        owner_name=ns["owner"],
                    )
                except Exception as e:
                    logger.warning(f"命名空间 {ns['name']} 可能已存在: {e}")

            # 创建核心数据集
            datasets = [
                # Bronze 层
                {
                    "namespace": "football_db.bronze",
                    "name": "raw_match_data",
                    "description": "原始比赛数据",
                    "schema": [
                        {"name": "id", "type": "INTEGER", "description": "主键"},
                        {
                            "name": "data_source",
                            "type": "VARCHAR",
                            "description": "数据源",
                        },
                        {
                            "name": "raw_data",
                            "type": "JSONB",
                            "description": "原始数据",
                        },
                        {
                            "name": "collected_at",
                            "type": "TIMESTAMP",
                            "description": "采集时间",
                        },
                    ],
                    "tags": ["bronze", "raw", "matches"],
                },
                # Silver 层
                {
                    "namespace": "football_db.silver",
                    "name": "matches",
                    "description": "清洗后的比赛数据",
                    "schema": [
                        {"name": "id", "type": "INTEGER", "description": "比赛ID"},
                        {
                            "name": "home_team_id",
                            "type": "INTEGER",
                            "description": "主队ID",
                        },
                        {
                            "name": "away_team_id",
                            "type": "INTEGER",
                            "description": "客队ID",
                        },
                        {
                            "name": "match_time",
                            "type": "TIMESTAMP",
                            "description": "比赛时间",
                        },
                    ],
                    "tags": ["silver", "cleaned", "matches"],
                },
                # Gold 层
                {
                    "namespace": "football_db.gold",
                    "name": "features",
                    "description": "机器学习特征数据",
                    "schema": [
                        {"name": "id", "type": "INTEGER", "description": "特征ID"},
                        {
                            "name": "match_id",
                            "type": "INTEGER",
                            "description": "比赛ID",
                        },
                        {"name": "team_id", "type": "INTEGER", "description": "球队ID"},
                        {
                            "name": "recent_5_wins",
                            "type": "INTEGER",
                            "description": "近5场胜利",
                        },
                    ],
                    "tags": ["gold", "features", "ml"],
                },
            ]

            for dataset in datasets:
                try:
                    # Type annotations to help mypy understand the correct types
                    namespace_str: str = dataset["namespace"]  # type: ignore
                    name_str: str = dataset["name"]  # type: ignore
                    description_str: Optional[str] = dataset["description"]  # type: ignore
                    schema_list: Optional[List[Dict[str, str]]] = dataset["schema"]  # type: ignore
                    tags_list: Optional[List[str]] = dataset["tags"]  # type: ignore

                    self.create_dataset(
                        namespace=namespace_str,
                        name=name_str,
                        description=description_str,
                        schema_fields=schema_list,
                        tags=tags_list,
                    )
                except Exception as e:
                    logger.warning(
                        f"数据集 {dataset['namespace']}.{dataset['name']} 可能已存在: {e}"
                    )

            logger.info("足球预测平台元数据初始化完成")

        except Exception as e:
            logger.error(f"元数据初始化失败: {e}")
            raise


# 全局元数据管理器实例
_metadata_manager: Optional[MetadataManager] = None


def get_metadata_manager() -> MetadataManager:
    """
    获取全局元数据管理器实例

    Returns:
        MetadataManager: 元数据管理器实例
    """
    global _metadata_manager
    if _metadata_manager is None:
        _metadata_manager = MetadataManager()
    return _metadata_manager
