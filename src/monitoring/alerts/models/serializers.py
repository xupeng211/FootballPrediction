"""

"""





    """

    """

        """


        """

        """


        """


        """


        """

        """


        """



    """

    """

        """


        """

        """


        """


        """


        """

        """


        """



    """

    """

        """


        """

        """


        """


        """


        """

        """


        """



    """

    """

        """


        """

        """


        """


        """


        """

        """


        """



    """

    """

        """


        """

        """


        """

        """

        """
        with open(file_path, 'w', encoding='utf-8') as f:

        """


        """
        with open(file_path, 'r', encoding='utf-8') as f:


    """

    """

        """


        """

        """


        """

        """


        """

        """


        """

        """


        """

        """


        """

        """


        """

        """


        """

        """


        """


    """

    """

        """


        """




        """


        """




        """


        """








告警序列化工具
Alert Serialization Tools
提供告警对象的序列化和反序列化功能。
Provides serialization and deserialization functionality for alert objects.
    AlertChannel,
    AlertLevel,
    AlertSeverity,
    AlertStatus,
    AlertType,
    EscalationStatus,
    IncidentSeverity,
    IncidentStatus,
    NotificationStatus,
)
T = TypeVar('T')
class AlertSerializer:
    告警序列化器
    Alert Serializer
    提供告警对象的序列化功能。
    Provides serialization functionality for alert objects.
    @staticmethod
    def serialize_alert(alert: Alert) -> Dict[str, Any]:
        序列化告警对象
        Serialize Alert Object
        Args:
            alert: 告警对象 / Alert object
        Returns:
            Dict[str, Any]: 序列化结果 / Serialized result
        return alert.to_dict()
    @staticmethod
    def deserialize_alert(data: Union[Dict[str, Any], str]) -> Alert:
        反序列化告警对象
        Deserialize Alert Object
        Args:
            data: 数据 / Data
        Returns:
            Alert: 告警对象 / Alert object
        if isinstance(data, str):
            data = json.loads(data)
        return Alert.from_dict(data)
    @staticmethod
    def serialize_alerts(alerts: List[Alert]) -> List[Dict[str, Any]]:
        序列化告警列表
        Serialize Alert List
        Args:
            alerts: 告警列表 / Alert list
        Returns:
            List[Dict[str, Any]]: 序列化结果 / Serialized result
        return [alert.to_dict() for alert in alerts]
    @staticmethod
    def deserialize_alerts(data: Union[List[Dict[str, Any]], str]) -> List[Alert]:
        反序列化告警列表
        Deserialize Alert List
        Args:
            data: 数据 / Data
        Returns:
            List[Alert]: 告警列表 / Alert list
        if isinstance(data, str):
            data = json.loads(data)
        return [Alert.from_dict(alert_data) for alert_data in data]
class RuleSerializer:
    规则序列化器
    Rule Serializer
    提供告警规则的序列化功能。
    Provides serialization functionality for alert rules.
    @staticmethod
    def serialize_rule(rule: AlertRule) -> Dict[str, Any]:
        序列化告警规则
        Serialize Alert Rule
        Args:
            rule: 告警规则 / Alert rule
        Returns:
            Dict[str, Any]: 序列化结果 / Serialized result
        return rule.to_dict()
    @staticmethod
    def deserialize_rule(data: Union[Dict[str, Any], str]) -> AlertRule:
        反序列化告警规则
        Deserialize Alert Rule
        Args:
            data: 数据 / Data
        Returns:
            AlertRule: 告警规则 / Alert rule
        if isinstance(data, str):
            data = json.loads(data)
        return AlertRule.from_dict(data)
    @staticmethod
    def serialize_rules(rules: List[AlertRule]) -> List[Dict[str, Any]]:
        序列化告警规则列表
        Serialize Alert Rule List
        Args:
            rules: 告警规则列表 / Alert rule list
        Returns:
            List[Dict[str, Any]]: 序列化结果 / Serialized result
        return [rule.to_dict() for rule in rules]
    @staticmethod
    def deserialize_rules(data: Union[List[Dict[str, Any]], str]) -> List[AlertRule]:
        反序列化告警规则列表
        Deserialize Alert Rule List
        Args:
            data: 数据 / Data
        Returns:
            List[AlertRule]: 告警规则列表 / Alert rule list
        if isinstance(data, str):
            data = json.loads(data)
        return [AlertRule.from_dict(rule_data) for rule_data in data]
class IncidentSerializer:
    事件序列化器
    Incident Serializer
    提供告警事件的序列化功能。
    Provides serialization functionality for alert incidents.
    @staticmethod
    def serialize_incident(incident: Incident) -> Dict[str, Any]:
        序列化告警事件
        Serialize Incident
        Args:
            incident: 告警事件 / Incident
        Returns:
            Dict[str, Any]: 序列化结果 / Serialized result
        return incident.to_dict()
    @staticmethod
    def deserialize_incident(data: Union[Dict[str, Any], str]) -> Incident:
        反序列化告警事件
        Deserialize Incident
        Args:
            data: 数据 / Data
        Returns:
            Incident: 告警事件 / Incident
        if isinstance(data, str):
            data = json.loads(data)
        return Incident.from_dict(data)
    @staticmethod
    def serialize_incidents(incidents: List[Incident]) -> List[Dict[str, Any]]:
        序列化告警事件列表
        Serialize Incident List
        Args:
            incidents: 告警事件列表 / Incident list
        Returns:
            List[Dict[str, Any]]: 序列化结果 / Serialized result
        return [incident.to_dict() for incident in incidents]
    @staticmethod
    def deserialize_incidents(data: Union[List[Dict[str, Any]], str]) -> List[Incident]:
        反序列化告警事件列表
        Deserialize Incident List
        Args:
            data: 数据 / Data
        Returns:
            List[Incident]: 告警事件列表 / Incident list
        if isinstance(data, str):
            data = json.loads(data)
        return [Incident.from_dict(incident_data) for incident_data in data]
class EscalationSerializer:
    升级序列化器
    Escalation Serializer
    提供告警升级的序列化功能。
    Provides serialization functionality for alert escalations.
    @staticmethod
    def serialize_escalation_rule(rule: EscalationRule) -> Dict[str, Any]:
        序列化升级规则
        Serialize Escalation Rule
        Args:
            rule: 升级规则 / Escalation rule
        Returns:
            Dict[str, Any]: 序列化结果 / Serialized result
        return rule.to_dict()
    @staticmethod
    def deserialize_escalation_rule(data: Union[Dict[str, Any], str]) -> EscalationRule:
        反序列化升级规则
        Deserialize Escalation Rule
        Args:
            data: 数据 / Data
        Returns:
            EscalationRule: 升级规则 / Escalation rule
        if isinstance(data, str):
            data = json.loads(data)
        return EscalationRule(
            rule_id=data["rule_id"],
            name=data["name"],
            trigger_condition=data["trigger_condition"],
            trigger_after_minutes=data["trigger_after_minutes"],
            target_channels=[AlertChannel(c) for c in data["target_channels"]],
            target_recipients=data.get("target_recipients", []),
            severity_threshold=AlertSeverity(data["severity_threshold"]),
            enabled=data.get("enabled", True),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None,
        )
    @staticmethod
    def serialize_escalation(escalation: Escalation) -> Dict[str, Any]:
        序列化告警升级
        Serialize Escalation
        Args:
            escalation: 告警升级 / Escalation
        Returns:
            Dict[str, Any]: 序列化结果 / Serialized result
        return escalation.to_dict()
    @staticmethod
    def deserialize_escalation(data: Union[Dict[str, Any], str]) -> Escalation:
        反序列化告警升级
        Deserialize Escalation
        Args:
            data: 数据 / Data
        Returns:
            Escalation: 告警升级 / Escalation
        if isinstance(data, str):
            data = json.loads(data)
        return Escalation.from_dict(data)
class JSONSerializer:
    JSON序列化器
    JSON Serializer
    提供通用的JSON序列化功能。
    Provides generic JSON serialization functionality.
    @staticmethod
    def serialize(obj: Any, pretty: bool = False) -> str:
        序列化为JSON
        Serialize to JSON
        Args:
            obj: 对象 / Object
            pretty: 是否格式化 / Whether to format
        Returns:
            str: JSON字符串 / JSON string
        if pretty:
            return json.dumps(obj, indent=2, ensure_ascii=False, default=str)
        else:
            return json.dumps(obj, ensure_ascii=False, default=str)
    @staticmethod
    def deserialize(data: str) -> Any:
        从JSON反序列化
        Deserialize from JSON
        Args:
            data: JSON字符串 / JSON string
        Returns:
            Any: 对象 / Object
        return json.loads(data)
    @staticmethod
    def serialize_to_file(obj: Any, file_path: str, pretty: bool = True) -> None:
        序列化到文件
        Serialize to File
        Args:
            obj: 对象 / Object
            file_path: 文件路径 / File path
            pretty: 是否格式化 / Whether to format
            if pretty:
                json.dump(obj, f, indent=2, ensure_ascii=False, default=str)
            else:
                json.dump(obj, f, ensure_ascii=False, default=str)
    @staticmethod
    def deserialize_from_file(file_path: str) -> Any:
        从文件反序列化
        Deserialize from File
        Args:
            file_path: 文件路径 / File path
        Returns:
            Any: 对象 / Object
            return json.load(f)
class EnumSerializer:
    枚举序列化器
    Enum Serializer
    提供枚举类型的序列化功能。
    Provides serialization functionality for enum types.
    @staticmethod
    def serialize_enum(enum_obj) -> str:
        序列化枚举
        Serialize Enum
        Args:
            enum_obj: 枚举对象 / Enum object
        Returns:
            str: 枚举值 / Enum value
        return enum_obj.value
    @staticmethod
    def deserialize_alert_level(value: str) -> AlertLevel:
        反序列化告警级别
        Deserialize Alert Level
        Args:
            value: 值 / Value
        Returns:
            AlertLevel: 告警级别 / Alert level
        return AlertLevel(value)
    @staticmethod
    def deserialize_alert_type(value: str) -> AlertType:
        反序列化告警类型
        Deserialize Alert Type
        Args:
            value: 值 / Value
        Returns:
            AlertType: 告警类型 / Alert type
        return AlertType(value)
    @staticmethod
    def deserialize_alert_severity(value: str) -> AlertSeverity:
        反序列化告警严重程度
        Deserialize Alert Severity
        Args:
            value: 值 / Value
        Returns:
            AlertSeverity: 告警严重程度 / Alert severity
        return AlertSeverity(value)
    @staticmethod
    def deserialize_alert_status(value: str) -> AlertStatus:
        反序列化告警状态
        Deserialize Alert Status
        Args:
            value: 值 / Value
        Returns:
            AlertStatus: 告警状态 / Alert status
        return AlertStatus(value)
    @staticmethod
    def deserialize_alert_channel(value: str) -> AlertChannel:
        反序列化告警渠道
        Deserialize Alert Channel
        Args:
            value: 值 / Value
        Returns:
            AlertChannel: 告警渠道 / Alert channel
        return AlertChannel(value)
    @staticmethod
    def deserialize_incident_severity(value: str) -> IncidentSeverity:
        反序列化事件严重程度
        Deserialize Incident Severity
        Args:
            value: 值 / Value
        Returns:
            IncidentSeverity: 事件严重程度 / Incident severity
        return IncidentSeverity(value)
    @staticmethod
    def deserialize_incident_status(value: str) -> IncidentStatus:
        反序列化事件状态
        Deserialize Incident Status
        Args:
            value: 值 / Value
        Returns:
            IncidentStatus: 事件状态 / Incident status
        return IncidentStatus(value)
    @staticmethod
    def deserialize_escalation_status(value: str) -> EscalationStatus:
        反序列化升级状态
        Deserialize Escalation Status
        Args:
            value: 值 / Value
        Returns:
            EscalationStatus: 升级状态 / Escalation status
        return EscalationStatus(value)
class ValidationSerializer:
    验证序列化器
    Validation Serializer
    提供数据验证和序列化功能。
    Provides data validation and serialization functionality.
    @staticmethod
    def validate_alert_data(data: Dict[str, Any]) -> bool:
        验证告警数据
        Validate Alert Data
        Args:
            data: 数据 / Data
        Returns:
            bool: 是否有效 / Whether valid
        required_fields = ["alert_id", "title", "message", "level", "source"]
        for field in required_fields:
            if field not in data:
                return False
        # 验证枚举值
        try:
            AlertLevel(data["level"])
            if "type" in data:
                AlertType(data["type"])
            if "severity" in data:
                AlertSeverity(data["severity"])
            if "status" in data:
                AlertStatus(data["status"])
        except ValueError:
            return False
        return True
    @staticmethod
    def validate_rule_data(data: Dict[str, Any]) -> bool:
        验证规则数据
        Validate Rule Data
        Args:
            data: 数据 / Data
        Returns:
            bool: 是否有效 / Whether valid
        required_fields = ["rule_id", "name", "condition", "level", "channels"]
        for field in required_fields:
            if field not in data:
                return False
        # 验证枚举值
        try:
            AlertLevel(data["level"])
            if isinstance(data["channels"], list):
                [AlertChannel(c) for c in data["channels"]]
        except (ValueError, TypeError):
            return False
        return True
    @staticmethod
    def validate_incident_data(data: Dict[str, Any]) -> bool:
        验证事件数据
        Validate Incident Data
        Args:
            data: 数据 / Data
        Returns:
            bool: 是否有效 / Whether valid
        required_fields = ["incident_id", "title", "severity"]
        for field in required_fields:
            if field not in data:
                return False
        # 验证枚举值
        # Import moved to top
        # Import moved to top
        try: Dict, List, Optional, Type, TypeVar, Union
            IncidentSeverity(data["severity"])
            if "status" in data:
                IncidentStatus(data["status"])
        except ValueError:
            return False
        return True