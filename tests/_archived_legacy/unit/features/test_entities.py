from datetime import datetime

from src.features.entities import MatchEntity, TeamEntity, FeatureKey
import pytest

"""
特征实体测试套件

覆盖src/features/entities.py的所有实体类：
- MatchEntity
- TeamEntity
- FeatureKey

目标：实现100%覆盖率
"""

class TestMatchEntity:
    """MatchEntity测试类"""
    @pytest.fixture
    def sample_match_data(self):
        """示例比赛数据"""
        return {
            "match_id[": 12345,""""
            "]home_team_id[": 1,""""
            "]away_team_id[": 2,""""
            "]league_id[": 10,""""
            "]match_time[: "2025-09-29T15:00:00[","]"""
            "]season[: "2024-25["}"]"""
    @pytest.fixture
    def sample_datetime(self):
        "]""示例datetime对象"""
        return datetime(2025, 9, 29, 15, 0, 0)
    def test_match_entity_creation_success(self, sample_datetime):
        """测试成功创建MatchEntity"""
        match = MatchEntity(
            match_id=12345,
            home_team_id=1,
            away_team_id=2,
            league_id=10,
            match_time=sample_datetime,
            season="2024-25[")": assert match.match_id ==12345[" assert match.home_team_id ==1[""
        assert match.away_team_id ==2
        assert match.league_id ==10
        assert match.match_time ==sample_datetime
        assert match.season =="]]]2024-25[" def test_match_entity_to_dict("
    """"
        "]""测试MatchEntity转字典"""
        match = MatchEntity(
            match_id=12345,
            home_team_id=1,
            away_team_id=2,
            league_id=10,
            match_time=sample_datetime,
            season="2024-25[")": result = match.to_dict()": expected = {""
            "]match_id[": 12345,""""
            "]home_team_id[": 1,""""
            "]away_team_id[": 2,""""
            "]league_id[": 10,""""
            "]match_time[: "2025-09-29T15:00:00[","]"""
            "]season[: "2024-25["}"]": assert result ==expected[" def test_match_entity_from_dict(self, sample_match_data):"
        "]]""测试从字典创建MatchEntity"""
        match = MatchEntity.from_dict(sample_match_data)
        assert match.match_id ==12345
        assert match.home_team_id ==1
        assert match.away_team_id ==2
        assert match.league_id ==10
        assert match.match_time ==datetime(2025, 9, 29, 15, 0, 0)
        assert match.season =="2024-25[" def test_match_entity_round_trip("
    """"
        "]""测试MatchEntity序列化和反序列化往返"""
        original = MatchEntity(
            match_id=99999,
            home_team_id=100,
            away_team_id=200,
            league_id=50,
            match_time=sample_datetime,
            season="2025-26[")""""
        # 序列化
        dict_data = original.to_dict()
        # 反序列化
        restored = MatchEntity.from_dict(dict_data)
        # 验证往返一致性
        assert restored.match_id ==original.match_id
        assert restored.home_team_id ==original.home_team_id
        assert restored.away_team_id ==original.away_team_id
        assert restored.league_id ==original.league_id
        assert restored.match_time ==original.match_time
        assert restored.season ==original.season
    def test_match_entity_boundary_values(self):
        "]""测试MatchEntity边界值"""
        # 测试最小ID值
        match_min = MatchEntity(
            match_id=0,
            home_team_id=0,
            away_team_id=0,
            league_id=0,
            match_time=datetime.now(),
            season="0[")": assert match_min.match_id ==0["""
        # 测试大数值
        match_max = MatchEntity(
            match_id=999999999,
            home_team_id=999999999,
            away_team_id=999999999,
            league_id=999999999,
            match_time=datetime.now(),
            season="]]9999-99[")": assert match_max.match_id ==999999999[" def test_match_entity_datetime_formats(self):""
        "]]""测试不同的datetime格式"""
        # 测试带毫秒的datetime
        dt_with_ms = datetime(2025, 9, 29, 15, 30, 45, 123456)
        match = MatchEntity(
            match_id=1,
            home_team_id=1,
            away_team_id=2,
            league_id=1,
            match_time=dt_with_ms,
            season="2024-25[")": dict_result = match.to_dict()": assert "]2025-09-29T153045[" in dict_result["]match_time["]""""
        # 测试UTC时间
        dt_utc = datetime(2025, 9, 29, 12, 0, 0)
        match_utc = MatchEntity(
            match_id=2,
            home_team_id=1,
            away_team_id=2,
            league_id=1,
            match_time=dt_utc,
            season="]2024-25[")": assert match_utc.match_time ==dt_utc[" class TestTeamEntity:""
    "]]""TeamEntity测试类"""
    @pytest.fixture
    def sample_team_data(self):
        """示例球队数据"""
        return {
            "team_id[": 100,""""
            "]team_name[: "Test FC[","]"""
            "]league_id[": 10,""""
            "]home_venue[: "Test Stadium["}"]": def test_team_entity_creation_success(self):""
        "]""测试成功创建TeamEntity"""
        team = TeamEntity(
            team_id=100, team_name="Test FC[", league_id=10, home_venue="]Test Stadium["""""
        )
        assert team.team_id ==100
        assert team.team_name =="]Test FC[" assert team.league_id ==10[""""
        assert team.home_venue =="]]Test Stadium[" def test_team_entity_creation_without_venue("
    """"
        "]""测试不包含主场的TeamEntity创建"""
        team = TeamEntity(
            team_id=100,
            team_name="Test FC[",": league_id=10,"""
            # home_venue 使用默认值 None
        )
        assert team.team_id ==100
        assert team.team_name =="]Test FC[" assert team.league_id ==10[""""
        assert team.home_venue is None
    def test_team_entity_to_dict(self):
        "]]""测试TeamEntity转字典"""
        team = TeamEntity(
            team_id=100, team_name="Test FC[", league_id=10, home_venue="]Test Stadium["""""
        )
        result = team.to_dict()
        expected = {
            "]team_id[": 100,""""
            "]team_name[: "Test FC[","]"""
            "]league_id[": 10,""""
            "]home_venue[: "Test Stadium["}"]": assert result ==expected[" def test_team_entity_to_dict_without_venue(self):"
        "]]""测试不包含主场的TeamEntity转字典"""
        team = TeamEntity(team_id=100, team_name="Test FC[", league_id=10)": result = team.to_dict()": expected = {""
            "]team_id[": 100,""""
            "]team_name[: "Test FC[","]"""
            "]league_id[": 10,""""
            "]home_venue[": None}": assert result ==expected[" def test_team_entity_from_dict(self, sample_team_data):""
        "]]""测试从字典创建TeamEntity"""
        team = TeamEntity.from_dict(sample_team_data)
        assert team.team_id ==100
        assert team.team_name =="Test FC[" assert team.league_id ==10[""""
        assert team.home_venue =="]]Test Stadium[" def test_team_entity_from_dict_without_venue("
    """"
        "]""测试从不包含主场的字典创建TeamEntity"""
        data_without_venue = {"team_id[": 100, "]team_name[": "]Test FC[", "]league_id[": 10}": team = TeamEntity.from_dict(data_without_venue)": assert team.team_id ==100[" assert team.team_name =="]]Test FC[" assert team.league_id ==10[""""
        assert team.home_venue is None
    def test_team_entity_round_trip(self):
        "]]""测试TeamEntity序列化和反序列化往返"""
        original = TeamEntity(
            team_id=999, team_name="Test Team FC[", league_id=50, home_venue="]Test Arena["""""
        )
        # 序列化
        dict_data = original.to_dict()
        # 反序列化
        restored = TeamEntity.from_dict(dict_data)
        # 验证往返一致性
        assert restored.team_id ==original.team_id
        assert restored.team_name ==original.team_name
        assert restored.league_id ==original.league_id
        assert restored.home_venue ==original.home_venue
    def test_team_entity_unicode_names(self):
        "]""测试Unicode球队名称"""
        team = TeamEntity(
            team_id=100,
            team_name="测试球队 FC 中文 español 日本語[",": league_id=10,": home_venue="]测试体育场 🏟️")": assert team.team_name =="测试球队 FC 中文 español 日本語[" assert team.home_venue =="]测试体育场 🏟️" def test_team_entity_special_characters("
    """"
        """测试特殊字符"""
        team = TeamEntity(
            team_id=100,
            team_name='Special "Chars[": FC\'s & Co.',": league_id=10,": home_venue='Stadium "]The[": Ground\'s')": assert team.team_name =='Special "]Chars[" FC\'s & Co.'""""
        assert team.home_venue =='Stadium "]The[" Ground\'s'""""
class TestFeatureKey:
    "]""FeatureKey测试类"""
    @pytest.fixture
    def sample_datetime(self):
        """示例datetime对象"""
        return datetime(2025, 9, 29, 15, 0, 0)
    def test_feature_key_creation_match(self, sample_datetime):
        """测试创建比赛特征的FeatureKey"""
        key = FeatureKey(
            entity_type="match[", entity_id=12345, feature_timestamp=sample_datetime[""""
        )
        assert key.entity_type =="]]match[" assert key.entity_id ==12345[""""
        assert key.feature_timestamp ==sample_datetime
    def test_feature_key_creation_team(self, sample_datetime):
        "]]""测试创建球队特征的FeatureKey"""
        key = FeatureKey(
            entity_type="team[", entity_id=100, feature_timestamp=sample_datetime[""""
        )
        assert key.entity_type =="]]team[" assert key.entity_id ==100[""""
        assert key.feature_timestamp ==sample_datetime
    def test_feature_key_hash(self, sample_datetime):
        "]]""测试FeatureKey哈希"""
        key1 = FeatureKey("match[", 12345, sample_datetime)": key2 = FeatureKey("]match[", 12345, sample_datetime)": key3 = FeatureKey("]team[", 12345, sample_datetime)""""
        # 相同的key应该有相同的哈希值
        assert hash(key1) ==hash(key2)
        # 不同的key应该有不同的哈希值
        assert hash(key1) != hash(key3)
    def test_feature_key_equality(self, sample_datetime):
        "]""测试FeatureKey相等性"""
        key1 = FeatureKey("match[", 12345, sample_datetime)": key2 = FeatureKey("]match[", 12345, sample_datetime)": key3 = FeatureKey("]team[", 12345, sample_datetime)": key4 = FeatureKey("]match[", 54321, sample_datetime)": key5 = FeatureKey("]match[", 12345, datetime(2025, 9, 30, 15, 0, 0))""""
        # 相同的key应该相等
        assert key1 ==key2
        assert key1 is not key2  # 但不是同一个对象
        # 不同的key不应该相等
        assert key1 != key3  # 不同的entity_type
        assert key1 != key4  # 不同的entity_id
        assert key1 != key5  # 不同的timestamp
    def test_feature_key_equality_with_other_types(self, sample_datetime):
        "]""测试FeatureKey与其他类型的相等性"""
        key = FeatureKey("match[", 12345, sample_datetime)""""
        # 与None比较
        assert key is not None
        # 与字符串比较
        assert key != "]match["""""
        # 与字典比较
        assert key != {"]entity_type[ "match"", "entity_id] 12345}" def test_feature_key_hash_consistency(self, sample_datetime):"""
        """测试FeatureKey哈希一致性"""
        key = FeatureKey("match[", 12345, sample_datetime)""""
        # 多次调用hash应该返回相同的结果
        hash1 = hash(key)
        hash2 = hash(key)
        hash3 = hash(key)
        assert hash1 ==hash2 ==hash3
    def test_feature_key_different_timestamps(self):
        "]""测试不同时间戳的FeatureKey"""
        dt1 = datetime(2025, 9, 29, 15, 0, 0)
        dt2 = datetime(2025, 9, 29, 15, 0, 1)  # 相差1秒
        key1 = FeatureKey("match[", 12345, dt1)": key2 = FeatureKey("]match[", 12345, dt2)""""
        # 时间戳不同，所以key不同
        assert key1 != key2
        assert hash(key1) != hash(key2)
    def test_feature_key_entity_types(self):
        "]""测试不同的实体类型"""
        dt = datetime(2025, 9, 29, 15, 0, 0)
        # 测试各种实体类型
        for entity_type in ["match[", "]team[", "]player[", "]league[", "]season["]:": key = FeatureKey(entity_type, 12345, dt)": assert key.entity_type ==entity_type[" def test_feature_key_boundary_values(self):"
        "]]""测试FeatureKey边界值"""
        dt = datetime(2025, 9, 29, 15, 0, 0)
        # 测试最小entity_id
        key_min = FeatureKey("match[", 0, dt)": assert key_min.entity_id ==0["""
        # 测试最大entity_id
        key_max = FeatureKey("]]match[", 999999999999999999, dt)": assert key_max.entity_id ==999999999999999999["""
        # 测试远古时间戳
        dt_past = datetime(1970, 1, 1, 0, 0, 0)
        key_past = FeatureKey("]]match[", 12345, dt_past)": assert key_past.feature_timestamp ==dt_past["""
        # 测试未来时间戳
        dt_future = datetime(2099, 12, 31, 23, 59, 59)
        key_future = FeatureKey("]]match[", 12345, dt_future)": assert key_future.feature_timestamp ==dt_future[" class TestEntitiesIntegration:""
    "]]""实体集成测试"""
    def test_entities_together(self):
        """测试多个实体一起使用"""
        dt = datetime(2025, 9, 29, 15, 0, 0)
        # 创建比赛实体
        match = MatchEntity(
            match_id=12345,
            home_team_id=1,
            away_team_id=2,
            league_id=10,
            match_time=dt,
            season="2024-25[")""""
        # 创建球队实体
        home_team = TeamEntity(
            team_id=1, team_name="]Home FC[", league_id=10, home_venue="]Home Stadium["""""
        )
        away_team = TeamEntity(
            team_id=2, team_name="]Away FC[", league_id=10, home_venue="]Away Stadium["""""
        )
        # 创建特征键
        match_key = FeatureKey("]match[", match.match_id, dt)": home_team_key = FeatureKey("]team[", home_team.team_id, dt)": away_team_key = FeatureKey("]team[", away_team.team_id, dt)""""
        # 验证数据一致性
        assert match.home_team_id ==home_team.team_id
        assert match.away_team_id ==away_team.team_id
        assert match.league_id ==home_team.league_id ==away_team.league_id
        assert match_key.entity_id ==match.match_id
        assert home_team_key.entity_id ==home_team.team_id
        assert away_team_key.entity_id ==away_team.team_id
    def test_entities_serialization_integration(self):
        "]""测试实体序列化集成"""
        dt = datetime(2025, 9, 29, 15, 0, 0)
        # 创建实体
        match = MatchEntity(
            match_id=12345,
            home_team_id=1,
            away_team_id=2,
            league_id=10,
            match_time=dt,
            season="2024-25[")": team = TeamEntity(team_id=1, team_name="]Test FC[", league_id=10)""""
        # 序列化为字典
        match_dict = match.to_dict()
        team_dict = team.to_dict()
        # 验证序列化结果
        assert isinstance(match_dict, dict)
        assert isinstance(team_dict, dict)
        assert "]match_id[" in match_dict[""""
        assert "]]team_id[" in team_dict[""""
        # 反序列化
        match_restored = MatchEntity.from_dict(match_dict)
        team_restored = TeamEntity.from_dict(team_dict)
        # 验证往返一致性
        assert match_restored.match_id ==match.match_id
        assert team_restored.team_id ==team.team_id
if __name__ =="]]__main__[": pytest.main(""""
        ["]__file__[", "]-v[", "]--cov=src.features.entities[", "]--cov-report=term-missing["]"]"""
    )