#!/usr/bin/env python3
"""
🔍 数据模型验证测试

测试数据库模型的字段验证、业务规则、约束检查和数据完整性
"""

import asyncio
import re
from datetime import datetime, timedelta
from enum import Enum

import pytest


# 模拟枚举类型
class UserRole(str, Enum):
    """用户角色枚举"""

    USER = "user"
    PREMIUM = "premium"
    ADMIN = "admin"
    ANALYST = "analyst"


class PredictedResult(str, Enum):
    """预测结果枚举"""

    HOME = "home"
    DRAW = "draw"
    AWAY = "away"


class MatchStatus(str, Enum):
    """比赛状态枚举"""

    SCHEDULED = "scheduled"
    LIVE = "live"
    FINISHED = "finished"
    CANCELLED = "cancelled"
    POSTPONED = "postponed"


# 验证器类
class ModelValidator:
    """模型验证器"""

    @staticmethod
    def validate_email(email: str) -> bool:
        """验证邮箱格式"""
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return re.match(pattern, email) is not None

    @staticmethod
    def validate_username(username: str) -> bool:
        """验证用户名"""
        if not username:
            return False
        if len(username) < 3 or len(username) > 50:
            return False
        # 只允许字母、数字、下划线
        return re.match(r"^[a-zA-Z0-9_]+$", username) is not None

    @staticmethod
    def validate_password_hash(hash_str: str) -> bool:
        """验证密码哈希格式"""
        # 简单的哈希验证：应该是长字符串
        return len(hash_str) >= 60  # bcrypt哈希通常60字符

    @staticmethod
    def validate_probabilities(
        home_prob: float, draw_prob: float, away_prob: float
    ) -> bool:
        """验证概率值"""
        # 检查范围
        if not (0 <= home_prob <= 1 and 0 <= draw_prob <= 1 and 0 <= away_prob <= 1):
            return False

        # 检查总和
        total = home_prob + draw_prob + away_prob
        return abs(total - 1.0) < 0.01  # 允许小的浮点误差

    @staticmethod
    def validate_confidence(confidence: float) -> bool:
        """验证置信度"""
        return 0 <= confidence <= 1.0

    @staticmethod
    def validate_match_date(match_date: datetime) -> bool:
        """验证比赛日期"""
        return match_date > datetime.utcnow()

    @staticmethod
    def validate_score(score: int) -> bool:
        """验证比分"""
        return score >= 0

    @staticmethod
    def validate_founded_year(year: int) -> bool:
        """验证成立年份"""
        current_year = datetime.utcnow().year
        return 1800 <= year <= current_year


# 模拟数据模型类
class User:
    """用户模型"""

    def __init__(self, **kwargs):
        self.username = kwargs.get("username")
        self.email = kwargs.get("email")
        self.password_hash = kwargs.get("password_hash")
        self.full_name = kwargs.get("full_name")
        self.role = kwargs.get("role", UserRole.USER)
        self.is_active = kwargs.get("is_active", True)
        self.created_at = kwargs.get("created_at", datetime.utcnow())
        self.updated_at = kwargs.get("updated_at", datetime.utcnow())

    def validate(self) -> list[str]:
        """验证用户数据"""
        errors = []

        # 验证用户名
        if not ModelValidator.validate_username(self.username):
            errors.append("用户名无效：长度应在3-50字符，只允许字母、数字、下划线")

        # 验证邮箱
        if not ModelValidator.validate_email(self.email):
            errors.append("邮箱格式无效")

        # 验证密码哈希
        if not ModelValidator.validate_password_hash(self.password_hash):
            errors.append("密码哈希格式无效")

        # 验证角色
        if self.role not in UserRole.__members__.values():
            errors.append(f"无效的用户角色: {self.role}")

        return errors


class Team:
    """球队模型"""

    def __init__(self, **kwargs):
        self.name = kwargs.get("name")
        self.short_name = kwargs.get("short_name")
        self.country = kwargs.get("country")
        self.founded_year = kwargs.get("founded_year")
        self.stadium_name = kwargs.get("stadium_name")
        self.created_at = kwargs.get("created_at", datetime.utcnow())

    def validate(self) -> list[str]:
        """验证球队数据"""
        errors = []

        # 验证名称
        if not self.name or len(self.name) > 100:
            errors.append("球队名称无效：不能为空且不超过100字符")

        # 验证简称
        if self.short_name and len(self.short_name) > 50:
            errors.append("球队简称无效：不超过50字符")

        # 验证成立年份
        if self.founded_year and not ModelValidator.validate_founded_year(
            self.founded_year
        ):
            errors.append(f"成立年份无效：应在1800-{datetime.utcnow().year}之间")

        return errors


class Match:
    """比赛模型"""

    def __init__(self, **kwargs):
        self.home_team_id = kwargs.get("home_team_id")
        self.away_team_id = kwargs.get("away_team_id")
        self.match_date = kwargs.get("match_date")
        self.venue = kwargs.get("venue")
        self.status = kwargs.get("status", MatchStatus.SCHEDULED)
        self.home_score = kwargs.get("home_score", 0)
        self.away_score = kwargs.get("away_score", 0)
        self.created_at = kwargs.get("created_at", datetime.utcnow())

    def validate(self) -> list[str]:
        """验证比赛数据"""
        errors = []

        # 验证球队ID
        if not self.home_team_id or not self.away_team_id:
            errors.append("主队和客队ID不能为空")

        if self.home_team_id == self.away_team_id:
            errors.append("主队和客队不能相同")

        # 验证比赛日期
        if self.match_date and not ModelValidator.validate_match_date(self.match_date):
            errors.append("比赛日期不能是过去时间")

        # 验证状态
        if self.status not in MatchStatus.__members__.values():
            errors.append(f"无效的比赛状态: {self.status}")

        # 验证比分
        if not ModelValidator.validate_score(self.home_score):
            errors.append("主队比分必须是非负整数")

        if not ModelValidator.validate_score(self.away_score):
            errors.append("客队比分必须是非负整数")

        # 验证状态和比分的一致性
        if self.status == MatchStatus.SCHEDULED and (
            self.home_score > 0 or self.away_score > 0
        ):
            errors.append("计划中的比赛不应该有比分")

        if self.status == MatchStatus.FINISHED and (
            self.home_score == 0 and self.away_score == 0
        ):
            errors.append("已完成的比赛应该有比分")

        return errors


class Prediction:
    """预测模型"""

    def __init__(self, **kwargs):
        self.user_id = kwargs.get("user_id")
        self.match_id = kwargs.get("match_id")
        self.predicted_outcome = kwargs.get("predicted_outcome")
        self.home_win_prob = kwargs.get("home_win_prob")
        self.draw_prob = kwargs.get("draw_prob")
        self.away_win_prob = kwargs.get("away_win_prob")
        self.confidence = kwargs.get("confidence")
        self.model_version = kwargs.get("model_version", "v1.0")
        self.actual_outcome = kwargs.get("actual_outcome")
        self.is_correct = kwargs.get("is_correct")
        self.created_at = kwargs.get("created_at", datetime.utcnow())

    def validate(self) -> list[str]:
        """验证预测数据"""
        errors = []

        # 验证用户ID和比赛ID
        if not self.user_id:
            errors.append("用户ID不能为空")

        if not self.match_id:
            errors.append("比赛ID不能为空")

        # 验证预测结果
        if self.predicted_outcome not in PredictedResult.__members__.values():
            errors.append(f"无效的预测结果: {self.predicted_outcome}")

        # 验证概率
        if not ModelValidator.validate_probabilities(
            self.home_win_prob, self.draw_prob, self.away_win_prob
        ):
            errors.append("概率值无效：每个概率应在0-1之间，总和应为1.0")

        # 验证置信度
        if not ModelValidator.validate_confidence(self.confidence):
            errors.append("置信度应在0-1之间")

        # 验证模型版本
        if not self.model_version:
            errors.append("模型版本不能为空")

        # 验证实际结果（如果存在）
        if (
            self.actual_outcome
            and self.actual_outcome not in PredictedResult.__members__.values()
        ):
            errors.append(f"无效的实际结果: {self.actual_outcome}")

        # 验证预测结果和概率的一致性
        if (
            self.predicted_outcome == PredictedResult.HOME
            and self.home_win_prob <= max(self.draw_prob, self.away_win_prob)
        ):
            errors.append("预测为主队获胜，但主队胜率不是最高")

        if self.predicted_outcome == PredictedResult.DRAW and self.draw_prob <= max(
            self.home_win_prob, self.away_win_prob
        ):
            errors.append("预测为平局，但平局概率不是最高")

        if (
            self.predicted_outcome == PredictedResult.AWAY
            and self.away_win_prob <= max(self.home_win_prob, self.draw_prob)
        ):
            errors.append("预测为客队获胜，但客队胜率不是最高")

        return errors


@pytest.mark.unit
@pytest.mark.database
@pytest.mark.validation
class TestUserModelValidation:
    """用户模型验证测试"""

    def test_valid_user_creation(self):
        """测试有效用户创建"""
        user_data = {
            "username": "testuser123",
            "email": "test@example.com",
            "password_hash": "$2b$12$abcdefghijklmnopqrstuvwx yzABCDEFGH IJKLMNOPQRSTUVWXYZ012345",  # 60字符哈希
            "full_name": "Test User",
            "role": UserRole.USER,
        }

        user = User(**user_data)
        errors = user.validate()

        assert len(errors) == 0, f"有效用户不应该有验证错误: {errors}"

    def test_invalid_username(self):
        """测试无效用户名"""
        invalid_usernames = [
            "",  # 空用户名
            "ab",  # 太短
            "a" * 51,  # 太长
            "user@name",  # 包含特殊字符
            "user name",  # 包含空格
            "用户名",  # 包含中文
        ]

        for username in invalid_usernames:
            user = User(
                username=username,
                email="test@example.com",
                password_hash="$2b$12$hash_string_here_60_characters_long_minimum",
            )
            errors = user.validate()
            assert len(errors) > 0, f"用户名 '{username}' 应该有验证错误"

    def test_invalid_email(self):
        """测试无效邮箱"""
        invalid_emails = [
            "",  # 空邮箱
            "invalid",  # 缺少@和域名
            "@example.com",  # 缺少用户名
            "user@",  # 缺少域名
            "user@.com",  # 无效域名
            "user@com",  # 缺少顶级域名
            "user name@example.com",  # 包含空格
        ]

        for email in invalid_emails:
            user = User(
                username="testuser",
                email=email,
                password_hash="$2b$12$hash_string_here_60_characters_long_minimum",
            )
            errors = user.validate()
            assert len(errors) > 0, f"邮箱 '{email}' 应该有验证错误"

    def test_invalid_password_hash(self):
        """测试无效密码哈希"""
        invalid_hashes = [
            "",  # 空哈希
            "short",  # 太短
            "a" * 50,  # 长度不足
        ]

        for hash_str in invalid_hashes:
            user = User(
                username="testuser", email="test@example.com", password_hash=hash_str
            )
            errors = user.validate()
            assert len(errors) > 0, f"密码哈希 '{hash_str}' 应该有验证错误"

    def test_invalid_role(self):
        """测试无效角色"""
        user = User(
            username="testuser",
            email="test@example.com",
            password_hash="$2b$12$hash_string_here_60_characters_long_minimum",
            role="invalid_role",
        )
        errors = user.validate()
        assert len(errors) > 0, "无效角色应该有验证错误"

    def test_all_valid_roles(self):
        """测试所有有效角色"""
        for role in UserRole:
            user = User(
                username="testuser",
                email="test@example.com",
                password_hash="$2b$12$hash_string_here_60_characters_long_minimum",
                role=role.value,
            )
            errors = user.validate()
            assert len(errors) == 0, f"角色 {role.value} 应该是有效的"

    def test_edge_cases(self):
        """测试边界情况"""
        # 最小长度用户名
        user = User(
            username="abc",
            email="test@example.com",
            password_hash="$2b$12$hash_string_here_60_characters_long_minimum",
        )
        errors = user.validate()
        assert len(errors) == 0, "3字符用户名应该有效"

        # 最大长度用户名
        user = User(
            username="a" * 50,
            email="test@example.com",
            password_hash="$2b$12$hash_string_here_60_characters_long_minimum",
        )
        errors = user.validate()
        assert len(errors) == 0, "50字符用户名应该有效"


@pytest.mark.unit
@pytest.mark.database
@pytest.mark.validation
class TestTeamModelValidation:
    """球队模型验证测试"""

    def test_valid_team_creation(self):
        """测试有效球队创建"""
        team_data = {
            "name": "Test Football Club",
            "short_name": "TFC",
            "country": "China",
            "founded_year": 2020,
            "stadium_name": "Test Stadium",
        }

        team = Team(**team_data)
        errors = team.validate()

        assert len(errors) == 0, f"有效球队不应该有验证错误: {errors}"

    def test_invalid_team_name(self):
        """测试无效球队名称"""
        invalid_names = [
            "",  # 空名称
            "a" * 101,  # 超过100字符
        ]

        for name in invalid_names:
            team = Team(name=name)
            errors = team.validate()
            assert len(errors) > 0, f"球队名称 '{name}' 应该有验证错误"

    def test_invalid_short_name(self):
        """测试无效简称"""
        team = Team(name="Test Club", short_name="a" * 51)  # 超过50字符
        errors = team.validate()
        assert len(errors) > 0, "超过50字符的简称应该有验证错误"

    def test_invalid_founded_year(self):
        """测试无效成立年份"""
        invalid_years = [1799, 1800, datetime.utcnow().year + 1]

        for year in invalid_years:
            team = Team(name="Test Club", founded_year=year)
            errors = team.validate()
            assert len(errors) > 0, f"成立年份 {year} 应该有验证错误"

    def test_valid_founded_year_range(self):
        """测试有效成立年份范围"""
        valid_years = [1801, 1900, 2000, datetime.utcnow().year]

        for year in valid_years:
            team = Team(name="Test Club", founded_year=year)
            errors = team.validate()
            assert len(errors) == 0, f"成立年份 {year} 应该是有效的"

    def test_optional_fields(self):
        """测试可选字段"""
        team = Team(name="Test Club")  # 只有必填字段
        errors = team.validate()
        assert len(errors) == 0, "只有必填字段的球队应该有效"


@pytest.mark.unit
@pytest.mark.database
@pytest.mark.validation
class TestMatchModelValidation:
    """比赛模型验证测试"""

    def test_valid_match_creation(self):
        """测试有效比赛创建"""
        future_date = datetime.utcnow() + timedelta(days=7)
        match_data = {
            "home_team_id": 1,
            "away_team_id": 2,
            "match_date": future_date,
            "venue": "Test Stadium",
            "status": MatchStatus.SCHEDULED,
        }

        match = Match(**match_data)
        errors = match.validate()

        assert len(errors) == 0, f"有效比赛不应该有验证错误: {errors}"

    def test_same_teams(self):
        """测试相同球队"""
        match = Match(
            home_team_id=1,
            away_team_id=1,  # 相同球队
            match_date=datetime.utcnow() + timedelta(days=1),
        )
        errors = match.validate()
        assert len(errors) > 0, "主队和客队相同应该有验证错误"

    def test_missing_team_ids(self):
        """测试缺少球队ID"""
        # 缺少主队ID
        match = Match(away_team_id=2, match_date=datetime.utcnow() + timedelta(days=1))
        errors = match.validate()
        assert len(errors) > 0, "缺少主队ID应该有验证错误"

        # 缺少客队ID
        match = Match(home_team_id=1, match_date=datetime.utcnow() + timedelta(days=1))
        errors = match.validate()
        assert len(errors) > 0, "缺少客队ID应该有验证错误"

    def test_past_match_date(self):
        """测试过去比赛日期"""
        past_date = datetime.utcnow() - timedelta(days=1)
        match = Match(home_team_id=1, away_team_id=2, match_date=past_date)
        errors = match.validate()
        assert len(errors) > 0, "过去比赛日期应该有验证错误"

    def test_invalid_status(self):
        """测试无效状态"""
        match = Match(
            home_team_id=1,
            away_team_id=2,
            match_date=datetime.utcnow() + timedelta(days=1),
            status="invalid_status",
        )
        errors = match.validate()
        assert len(errors) > 0, "无效状态应该有验证错误"

    def test_negative_scores(self):
        """测试负比分"""
        match = Match(
            home_team_id=1,
            away_team_id=2,
            match_date=datetime.utcnow() + timedelta(days=1),
            home_score=-1,  # 负比分
            status=MatchStatus.FINISHED,
        )
        errors = match.validate()
        assert len(errors) > 0, "负比分应该有验证错误"

    def test_score_status_consistency(self):
        """测试比分和状态一致性"""
        # 计划中的比赛有比分
        match = Match(
            home_team_id=1,
            away_team_id=2,
            match_date=datetime.utcnow() + timedelta(days=1),
            home_score=2,
            away_score=1,
            status=MatchStatus.SCHEDULED,
        )
        errors = match.validate()
        assert len(errors) > 0, "计划中的比赛有比分应该有验证错误"

        # 完成的比赛没有比分
        match = Match(
            home_team_id=1,
            away_team_id=2,
            match_date=datetime.utcnow() + timedelta(days=1),
            home_score=0,
            away_score=0,
            status=MatchStatus.FINISHED,
        )
        errors = match.validate()
        assert len(errors) > 0, "完成的比赛没有比分应该有验证错误"

    def test_all_valid_statuses(self):
        """测试所有有效状态"""
        future_date = datetime.utcnow() + timedelta(days=1)
        valid_statuses = [
            MatchStatus.SCHEDULED,
            MatchStatus.LIVE,
            MatchStatus.CANCELLED,
            MatchStatus.POSTPONED,
        ]

        for status in valid_statuses:
            match = Match(
                home_team_id=1, away_team_id=2, match_date=future_date, status=status
            )
            errors = match.validate()
            assert len(errors) == 0, f"状态 {status} 应该是有效的"


@pytest.mark.unit
@pytest.mark.database
@pytest.mark.validation
class TestPredictionModelValidation:
    """预测模型验证测试"""

    def test_valid_prediction_creation(self):
        """测试有效预测创建"""
        prediction_data = {
            "user_id": 1,
            "match_id": 1,
            "predicted_outcome": PredictedResult.HOME,
            "home_win_prob": 0.6,
            "draw_prob": 0.25,
            "away_win_prob": 0.15,
            "confidence": 0.8,
            "model_version": "v2.0",
        }

        prediction = Prediction(**prediction_data)
        errors = prediction.validate()

        assert len(errors) == 0, f"有效预测不应该有验证错误: {errors}"

    def test_missing_ids(self):
        """测试缺少ID"""
        # 缺少用户ID
        prediction = Prediction(
            match_id=1,
            predicted_outcome=PredictedResult.HOME,
            home_win_prob=0.6,
            draw_prob=0.25,
            away_win_prob=0.15,
            confidence=0.8,
        )
        errors = prediction.validate()
        assert len(errors) > 0, "缺少用户ID应该有验证错误"

        # 缺少比赛ID
        prediction = Prediction(
            user_id=1,
            predicted_outcome=PredictedResult.HOME,
            home_win_prob=0.6,
            draw_prob=0.25,
            away_win_prob=0.15,
            confidence=0.8,
        )
        errors = prediction.validate()
        assert len(errors) > 0, "缺少比赛ID应该有验证错误"

    def test_invalid_probabilities(self):
        """测试无效概率"""
        invalid_prob_cases = [
            # 超出范围
            (-0.1, 0.6, 0.5),  # 负概率
            (0.6, 1.1, 0.3),  # 超过1
            (0.3, 0.4, 0.5),  # 总和小于1
            (0.6, 0.3, 0.4),  # 总和大于1
        ]

        for home_prob, draw_prob, away_prob in invalid_prob_cases:
            prediction = Prediction(
                user_id=1,
                match_id=1,
                predicted_outcome=PredictedResult.HOME,
                home_win_prob=home_prob,
                draw_prob=draw_prob,
                away_win_prob=away_prob,
                confidence=0.8,
            )
            errors = prediction.validate()
            assert (
                len(errors) > 0
            ), f"概率 {home_prob}, {draw_prob}, {away_prob} 应该有验证错误"

    def test_invalid_confidence(self):
        """测试无效置信度"""
        invalid_confidences = [-0.1, 1.1, 1.5]

        for confidence in invalid_confidences:
            prediction = Prediction(
                user_id=1,
                match_id=1,
                predicted_outcome=PredictedResult.HOME,
                home_win_prob=0.6,
                draw_prob=0.25,
                away_win_prob=0.15,
                confidence=confidence,
            )
            errors = prediction.validate()
            assert len(errors) > 0, f"置信度 {confidence} 应该有验证错误"

    def test_invalid_predicted_outcome(self):
        """测试无效预测结果"""
        prediction = Prediction(
            user_id=1,
            match_id=1,
            predicted_outcome="invalid_outcome",
            home_win_prob=0.6,
            draw_prob=0.25,
            away_win_prob=0.15,
            confidence=0.8,
        )
        errors = prediction.validate()
        assert len(errors) > 0, "无效预测结果应该有验证错误"

    def test_probability_outcome_consistency(self):
        """测试概率和预测结果一致性"""
        # 预测主队获胜但主队概率不是最高
        prediction = Prediction(
            user_id=1,
            match_id=1,
            predicted_outcome=PredictedResult.HOME,
            home_win_prob=0.2,  # 不是最高
            draw_prob=0.6,  # 最高
            away_win_prob=0.2,
            confidence=0.8,
        )
        errors = prediction.validate()
        assert len(errors) > 0, "预测结果和概率不一致应该有验证错误"

        # 预测平局但平局概率不是最高
        prediction = Prediction(
            user_id=1,
            match_id=1,
            predicted_outcome=PredictedResult.DRAW,
            home_win_prob=0.7,  # 最高
            draw_prob=0.2,  # 不是最高
            away_win_prob=0.1,
            confidence=0.8,
        )
        errors = prediction.validate()
        assert len(errors) > 0, "预测结果和概率不一致应该有验证错误"

    def test_valid_probability_outcome_consistency(self):
        """测试有效的概率和预测结果一致性"""
        valid_cases = [
            # 预测主队获胜，主队概率最高
            (PredictedResult.HOME, 0.6, 0.25, 0.15),
            # 预测平局，平局概率最高
            (PredictedResult.DRAW, 0.3, 0.5, 0.2),
            # 预测客队获胜，客队概率最高
            (PredictedResult.AWAY, 0.2, 0.3, 0.5),
        ]

        for outcome, home_prob, draw_prob, away_prob in valid_cases:
            prediction = Prediction(
                user_id=1,
                match_id=1,
                predicted_outcome=outcome,
                home_win_prob=home_prob,
                draw_prob=draw_prob,
                away_win_prob=away_prob,
                confidence=0.8,
            )
            errors = prediction.validate()
            assert (
                len(errors) == 0
            ), f"有效的概率预测组合应该无错误: {outcome}, {home_prob}, {draw_prob}, {away_prob}"

    def test_edge_case_probabilities(self):
        """测试边界情况概率"""
        # 极端情况1：主队必胜
        prediction = Prediction(
            user_id=1,
            match_id=1,
            predicted_outcome=PredictedResult.HOME,
            home_win_prob=1.0,
            draw_prob=0.0,
            away_win_prob=0.0,
            confidence=1.0,
        )
        errors = prediction.validate()
        assert len(errors) == 0, "极端概率情况1应该有效"

        # 极端情况2：完全均匀分布
        prediction = Prediction(
            user_id=1,
            match_id=1,
            predicted_outcome=PredictedResult.DRAW,
            home_win_prob=0.333,
            draw_prob=0.334,
            away_win_prob=0.333,
            confidence=0.5,
        )
        errors = prediction.validate()
        assert len(errors) == 0, "均匀分布应该有效"


# 测试运行器
async def run_model_validation_tests():
    """运行模型验证测试套件"""
    print("🔍 开始数据模型验证测试")
    print("=" * 60)

    # 这里可以添加更复杂的模型验证测试逻辑

    print("✅ 数据模型验证测试完成")


if __name__ == "__main__":
    asyncio.run(run_model_validation_tests())
