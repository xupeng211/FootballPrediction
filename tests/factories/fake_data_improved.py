"""
改进的Faker数据工厂
Improved Faker Data Factory

分离数据生成和验证逻辑，提高可维护性。
"""

import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union, Any
from faker import Faker
from pydantic import BaseModel, validator
import logging

# 初始化Faker
fake = Faker("zh_CN")
Faker.seed(42)  # 确保可重现

logger = logging.getLogger(__name__)


class DataValidationError(Exception):
    """数据验证错误"""

    pass


class PredictionData(BaseModel):
    """预测数据模型（带验证）"""

    match_id: int
    home_win_prob: float
    draw_prob: float
    away_win_prob: float
    predicted_outcome: str
    confidence: float
    model_version: str
    predicted_at: datetime
    features: Optional[Dict[str, Any]] = None

    @validator("match_id")
    def validate_match_id(cls, v):
        if v < 1 or v > 999999:
            raise ValueError("match_id must be between 1 and 999999")
        return v

    @validator("home_win_prob", "draw_prob", "away_win_prob")
    def validate_probabilities(cls, v):
        if not 0 <= v <= 1:
            raise ValueError("Probability must be between 0 and 1")
        return round(v, 2)

    @validator("predicted_outcome")
    def validate_outcome(cls, v):
        if v not in ["home", "draw", "away"]:
            raise ValueError("Outcome must be home, draw, or away")
        return v

    @validator("confidence")
    def validate_confidence(cls, v):
        if not 0 <= v <= 1:
            raise ValueError("Confidence must be between 0 and 1")
        return round(v, 2)

    @validator("model_version")
    def validate_model_version(cls, v):
        if not v or len(v) > 100:
            raise ValueError("Model version must be non-empty and <= 100 chars")
        return v


class MatchData(BaseModel):
    """比赛数据模型（带验证）"""

    match_id: int
    home_team: str
    away_team: str
    home_score: int
    away_score: int
    match_date: datetime
    league: str
    venue: Optional[str] = None
    attendance: Optional[int] = None

    @validator("match_id")
    def validate_match_id(cls, v):
        if v < 1:
            raise ValueError("match_id must be positive")
        return v

    @validator("home_team", "away_team")
    def validate_team_names(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError("Team name cannot be empty")
        return v.strip()

    @validator("home_score", "away_score")
    def validate_scores(cls, v):
        if v < 0 or v > 99:
            raise ValueError("Score must be between 0 and 99")
        return v

    @validator("match_date")
    def validate_match_date(cls, v):
        if v > datetime.now() + timedelta(days=365):
            raise ValueError("Match date cannot be more than 1 year in future")
        return v


class DataValidator:
    """数据验证器"""

    @staticmethod
    def validate_probabilities_sum(probs: List[float], tolerance: float = 0.02) -> bool:
        """验证概率总和"""
        total = sum(probs)
        return abs(total - 1.0) <= tolerance

    @staticmethod
    def validate_prediction_consistency(data: Dict) -> bool:
        """验证预测数据一致性"""
        # 验证概率和与预测结果一致
        probs = [data["home_win_prob"], data["draw_prob"], data["away_win_prob"]]
        if not DataValidator.validate_probabilities_sum(probs):
            return False

        # 验证预测结果对应最高概率
        max_prob_index = probs.index(max(probs))
        outcomes = ["home", "draw", "away"]
        return data["predicted_outcome"] == outcomes[max_prob_index]

    @staticmethod
    def validate_team_relationship(home: str, away: str) -> bool:
        """验证球队关系"""
        return home != away

    @staticmethod
    def validate_score_reasonableness(home_score: int, away_score: int) -> bool:
        """验证比分合理性"""
        # 简单规则：避免极端比分
        total = home_score + away_score
        return total <= 15  # 足球比赛很少超过15个球


class ImprovedFootballDataFactory:
    """改进的足球数据工厂"""

    @staticmethod
    def generate_match() -> MatchData:
        """生成单个比赛数据"""
        data = {
            "match_id": fake.random_int(min=1000, max=999999),
            "home_team": fake.company(),
            "away_team": fake.company(),
            "home_score": fake.random_int(min=0, max=5),
            "away_score": fake.random_int(min=0, max=5),
            "match_date": fake.date_time_between(start_date="-30d", end_date="+30d"),
            "league": fake.company_suffix() + "联赛",
            "venue": f"{fake.company()}体育场",
            "attendance": fake.random_int(min=1000, max=50000)
            if fake.boolean()
            else None,
        }

        # 使用Pydantic验证
        try:
            return MatchData(**data)
        except Exception as e:
            logger.warning(f"Validation failed for match data: {e}")
            # 修复并重试
            if data["home_team"] == data["away_team"]:
                data["away_team"] += " B"
            return MatchData(**data)

    @staticmethod
    def generate_prediction(match_id: Optional[int] = None) -> PredictionData:
        """生成单个预测数据"""
        # 生成概率并归一化
        probs = [fake.random.uniform(0.1, 0.8) for _ in range(3)]
        total = sum(probs)
        probs = [round(p / total, 2) for p in probs]

        # 修正舍入误差
        diff = round(1.0 - sum(probs), 2)
        probs[0] += diff

        # 确定预测结果
        outcomes = ["home", "draw", "away"]
        predicted_outcome = outcomes[probs.index(max(probs))]

        data = {
            "match_id": match_id or fake.random_int(min=1000, max=999999),
            "home_win_prob": probs[0],
            "draw_prob": probs[1],
            "away_win_prob": probs[2],
            "predicted_outcome": predicted_outcome,
            "confidence": round(fake.random.uniform(0.5, 0.95), 2),
            "model_version": f"v{fake.random_int(min=1, max=3)}.{fake.random_int(min=0, max=9)}",
            "predicted_at": fake.date_time_between(start_date="-7d", end_date="now"),
            "features": {
                "team_form": {
                    "home": fake.random_elements(elements=("W", "D", "L"), length=5),
                    "away": fake.random_elements(elements=("W", "D", "L"), length=5),
                },
                "head_to_head": {
                    "wins": fake.random_int(min=0, max=5),
                    "draws": fake.random_int(min=0, max=5),
                    "losses": fake.random_int(min=0, max=5),
                },
                "injuries": {
                    "home": fake.random_int(min=0, max=3),
                    "away": fake.random_int(min=0, max=3),
                },
            },
        }

        # 使用Pydantic验证
        try:
            return PredictionData(**data)
        except Exception as e:
            logger.error(f"Failed to generate valid prediction: {e}")
            raise DataValidationError(f"Invalid prediction data: {e}")

    @staticmethod
    def generate_batch_predictions(
        count: int, ensure_consistency: bool = True
    ) -> List[PredictionData]:
        """生成批量预测数据"""
        predictions = []
        errors = []

        for _ in range(count):
            try:
                pred = ImprovedFootballDataFactory.generate_prediction()

                # 额外一致性检查
                if ensure_consistency:
                    if not DataValidator.validate_prediction_consistency(pred.dict()):
                        logger.warning("Generated inconsistent prediction data")
                        continue

                predictions.append(pred)
            except Exception as e:
                errors.append(str(e))
                logger.error(f"Failed to generate prediction: {e}")

        if errors:
            logger.warning(f"Generated {count} predictions with {len(errors)} errors")

        return predictions

    @staticmethod
    def generate_batch_matches(
        count: int, unique_teams: bool = True
    ) -> List[MatchData]:
        """生成批量比赛数据"""
        matches = []
        used_teams = set()

        for _ in range(count):
            max_attempts = 10
            for attempt in range(max_attempts):
                try:
                    match = ImprovedFootballDataFactory.generate_match()

                    # 确保球队唯一性（如果需要）
                    if unique_teams:
                        team_pair = (match.home_team, match.away_team)
                        if team_pair in used_teams:
                            continue
                        used_teams.add(team_pair)

                    matches.append(match)
                    break
                except Exception as e:
                    if attempt == max_attempts - 1:
                        logger.error(
                            f"Failed to generate match after {max_attempts} attempts: {e}"
                        )

        return matches

    @staticmethod
    def generate_realistic_season(
        num_teams: int = 20, matches_per_team: int = 38
    ) -> List[MatchData]:
        """生成真实的赛季数据"""
        # 生成球队
        teams = [fake.company() for _ in range(num_teams)]
        matches = []

        # 简单的轮次生成
        for round_num in range(matches_per_team // 2):
            for i in range(num_teams // 2):
                home_idx = (i + round_num) % num_teams
                away_idx = (num_teams - 1 - i + round_num) % num_teams

                if home_idx == away_idx:
                    continue

                # 生成比赛日期
                match_date = datetime.now() + timedelta(days=round_num * 7 + i)

                try:
                    match = MatchData(
                        match_id=len(matches) + 1,
                        home_team=teams[home_idx],
                        away_team=teams[away_idx],
                        home_score=fake.random_int(min=0, max=4),
                        away_score=fake.random_int(min=0, max=4),
                        match_date=match_date,
                        league="超级联赛",
                    )
                    matches.append(match)
                except Exception as e:
                    logger.warning(f"Skipped invalid match: {e}")

        return matches


class TestDataGenerator:
    """测试数据生成器"""

    @staticmethod
    def create_test_scenario(
        num_matches: int = 10, predictions_per_match: int = 3
    ) -> Dict[str, Any]:
        """创建测试场景"""
        # 生成比赛
        matches = ImprovedFootballDataFactory.generate_batch_matches(num_matches)

        # 为每场比赛生成多个预测
        all_predictions = []
        for match in matches:
            for i in range(predictions_per_match):
                pred = ImprovedFootballDataFactory.generate_prediction(match.match_id)
                all_predictions.append(pred)

        return {
            "matches": [m.dict() for m in matches],
            "predictions": [p.dict() for p in all_predictions],
            "summary": {
                "total_matches": len(matches),
                "total_predictions": len(all_predictions),
                "predictions_per_match": predictions_per_match,
            },
        }

    @staticmethod
    def create_edge_cases() -> Dict[str, List[Dict]]:
        """创建边界情况数据"""
        edge_cases = {
            "extreme_scores": [],
            "edge_probabilities": [],
            "boundary_dates": [],
        }

        # 极端比分
        for score in [(0, 0), (10, 0), (0, 10), (7, 7)]:
            try:
                match = MatchData(
                    match_id=fake.random_int(),
                    home_team=fake.company(),
                    away_team=fake.company(),
                    home_score=score[0],
                    away_score=score[1],
                    match_date=datetime.now(),
                    league="测试联赛",
                )
                edge_cases["extreme_scores"].append(match.dict())
            except:
                pass

        # 边界概率
        for probs in [(0.99, 0.01, 0), (0.5, 0.5, 0), (0.34, 0.33, 0.33)]:
            outcomes = ["home", "draw", "away"]
            max_idx = probs.index(max(probs))

            try:
                pred = PredictionData(
                    match_id=fake.random_int(),
                    home_win_prob=probs[0],
                    draw_prob=probs[1],
                    away_win_prob=probs[2],
                    predicted_outcome=outcomes[max_idx],
                    confidence=0.9,
                    model_version="edge_case",
                    predicted_at=datetime.now(),
                )
                edge_cases["edge_probabilities"].append(pred.dict())
            except:
                pass

        return edge_cases


# 便捷函数
def create_valid_prediction(**kwargs) -> Dict:
    """创建有效的预测数据"""
    pred = ImprovedFootballDataFactory.generate_prediction()
    if kwargs:
        data = pred.dict()
        data.update(kwargs)
        pred = PredictionData(**data)
    return pred.dict()


def create_valid_match(**kwargs) -> Dict:
    """创建有效的比赛数据"""
    match = ImprovedFootballDataFactory.generate_match()
    if kwargs:
        data = match.dict()
        data.update(kwargs)
        match = MatchData(**data)
    return match.dict()


def create_test_batch(data_type: str, count: int = 10, **options) -> List[Dict]:
    """创建测试批次"""
    generators = {
        "predictions": lambda: ImprovedFootballDataFactory.generate_batch_predictions(
            count, ensure_consistency=options.get("ensure_consistency", True)
        ),
        "matches": lambda: ImprovedFootballDataFactory.generate_batch_matches(
            count, unique_teams=options.get("unique_teams", True)
        ),
    }

    if data_type not in generators:
        raise ValueError(f"Unknown data type: {data_type}")

    data = generators[data_type]()
    return [item.dict() for item in data]
