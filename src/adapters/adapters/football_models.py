from datetime import datetime

"""
数据模型类 - 足球相关数据结构
"""

SCHEDULED = "SCHEDULED"
LIVE = "LIVE"
FINISHED = "FINISHED"
POSTPONED = "POSTPONED"
CANCELLED = "CANCELLED"


class MatchStatus:
    """比赛状态枚举类"""

    status: str

    @classmethod
    def scheduled(cls) -> "MatchStatus":
        return cls(SCHEDULED)

    @classmethod
    def live(cls) -> "MatchStatus":
        return cls(LIVE)

    @classmethod
    def finished(cls) -> "MatchStatus":
        return cls(FINISHED)


class FootballTeam:
    """足球队数据模型"""

    id: int | None = None
    name: str | None = None
    league: str | None = None
    country: str | None = None
    founded_year: int | None = None

    def __post_init__(self):
        if self.name is None:
            self.name = "Unknown Team"


class FootballPlayer:
    """足球运动员数据模型"""

    id: int | None = None
    name: str | None = None
    team_id: int | None = None
    position: str | None = None
    age: int | None = None
    jersey_number: int | None = None

    def __post_init__(self):
        if self.name is None:
            self.name = "Unknown Player"


class FootballMatch:
    """足球比赛数据模型"""

    id: int | None = None
    home_team: FootballTeam | None = None
    away_team: FootballTeam | None = None
    status: MatchStatus | None = None
    home_score: int | None = None
    away_score: int | None = None
    match_date: datetime | None = None
    venue: str | None = None

    def __post_init__(self):
        if self.status is None:
            self.status = MatchStatus.scheduled()
        if self.home_score is None:
            self.home_score = 0
        if self.away_score is None:
            self.away_score = 0


class FootballApiAdaptee:
    """足球API被适配者基类"""

    def fetch_match_data(self, match_id: int) -> dict | None:
        """获取比赛数据"""
        raise NotImplementedError("子类必须实现此方法")

    def fetch_team_data(self, team_id: int) -> dict | None:
        """获取球队数据"""
        raise NotImplementedError("子类必须实现此方法")

    def fetch_player_data(self, player_id: int) -> dict | None:
        """获取球员数据"""
        raise NotImplementedError("子类必须实现此方法")


class ApiFootballAdaptee(FootballApiAdaptee):
    """API-Football被适配者"""

    def __init__(
        self, api_key: str, base_url: str = "https://api-football-v1.p.rapidapi.com"
    ):
        self.api_key = api_key
        self.base_url = base_url

    def fetch_match_data(self, match_id: int) -> dict | None:
        """从API-Football获取比赛数据"""
        # TODO: 实现API调用逻辑
        return {"id": match_id, "source": "api-football"}

    def fetch_team_data(self, team_id: int) -> dict | None:
        """从API-Football获取球队数据"""
        # TODO: 实现API调用逻辑
        return {"id": team_id, "source": "api-football"}


class OptaDataAdaptee(FootballApiAdaptee):
    """Opta数据被适配者"""

    def __init__(self, api_key: str, base_url: str = "https://api.opta.com"):
        self.api_key = api_key
        self.base_url = base_url

    def fetch_match_data(self, match_id: int) -> dict | None:
        """从Opta获取比赛数据"""
        # TODO: 实现API调用逻辑
        return {"id": match_id, "source": "opta"}

    def fetch_player_data(self, player_id: int) -> dict | None:
        """从Opta获取球员数据"""
        # TODO: 实现API调用逻辑
        return {"id": player_id, "source": "opta"}


class FootballDataTransformer:
    """足球数据转换器"""

    @staticmethod
    def transform_to_match(data: dict) -> FootballMatch:
        """将API数据转换为FootballMatch对象"""
        # TODO: 实现数据转换逻辑
        return FootballMatch(id=data.get("id"))

    @staticmethod
    def transform_to_team(data: dict) -> FootballTeam:
        """将API数据转换为FootballTeam对象"""
        # TODO: 实现数据转换逻辑
        return FootballTeam(id=data.get("id"), name=data.get("name"))

    @staticmethod
    def transform_to_player(data: dict) -> FootballPlayer:
        """将API数据转换为FootballPlayer对象"""
        # TODO: 实现数据转换逻辑
        return FootballPlayer(id=data.get("id"), name=data.get("name"))


class FootballApiAdapter:
    """足球API适配器基类"""

    def __init__(
        self, adaptee: FootballApiAdaptee, transformer: FootballDataTransformer
    ):
        self.adaptee = adaptee
        self.transformer = transformer

    def get_match(self, match_id: int) -> FootballMatch | None:
        """获取比赛信息"""
        data = self.adaptee.fetch_match_data(match_id)
        if data:
            return self.transformer.transform_to_match(data)
        return None

    def get_team(self, team_id: int) -> FootballTeam | None:
        """获取球队信息"""
        data = self.adaptee.fetch_team_data(team_id)
        if data:
            return self.transformer.transform_to_team(data)
        return None

    def get_player(self, player_id: int) -> FootballPlayer | None:
        """获取球员信息"""
        data = self.adaptee.fetch_player_data(player_id)
        if data:
            return self.transformer.transform_to_player(data)
        return None


class ApiFootballAdapter(FootballApiAdapter):
    """API-Football适配器"""

    def __init__(self, api_key: str):
        adaptee = ApiFootballAdaptee(api_key)
        transformer = FootballDataTransformer()
        super().__init__(adaptee, transformer)


class OptaDataAdapter(FootballApiAdapter):
    """Opta数据适配器"""

    def __init__(self, api_key: str):
        adaptee = OptaDataAdaptee(api_key)
        transformer = FootballDataTransformer()
        super().__init__(adaptee, transformer)


class CompositeFootballAdapter:
    """复合适配器,集成多个足球数据源"""

    def __init__(self, adapters: list[FootballApiAdapter]):
        self.adapters = adapters

    def get_match(self, match_id: int) -> FootballMatch | None:
        """从多个数据源获取比赛信息"""
        for adapter in self.adapters:
            try:
                match = adapter.get_match(match_id)
                if match:
                    return match
            except Exception:
                continue
        return None

    def get_team(self, team_id: int) -> FootballTeam | None:
        """从多个数据源获取球队信息"""
        for adapter in self.adapters:
            try:
                team = adapter.get_team(team_id)
                if team:
                    return team
            except Exception:
                continue
        return None


class FootballDataAdapter:
    """足球数据适配器（简化版用于测试）"""

    def __init__(self):
        self.matches = {}
        self.teams = {}
        self.players = {}

    def add_match(self, match: FootballMatch) -> None:
        """添加比赛数据"""
        if match.id:
            self.matches[match.id] = match

    def add_team(self, team: FootballTeam) -> None:
        """添加球队数据"""
        if team.id:
            self.teams[team.id] = team

    def add_player(self, player: FootballPlayer) -> None:
        """添加球员数据"""
        if player.id:
            self.players[player.id] = player

    def get_match(self, match_id: int) -> FootballMatch | None:
        """获取比赛数据"""
        return self.matches.get(match_id)

    def get_team(self, team_id: int) -> FootballTeam | None:
        """获取球队数据"""
        return self.teams.get(team_id)

    def get_player(self, player_id: int) -> FootballPlayer | None:
        """获取球员数据"""
        return self.players.get(player_id)
