"""
测试数据生成器
生成各种类型测试数据的工具类
"""

import random
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import uuid


class TestDataGenerator:
    """测试数据生成器"""

    def __init__(self, seed: Optional[int] = None):
        """初始化生成器

        Args:
            seed: 随机种子，用于可重现的数据生成
        """
        if seed is not None:
            random.seed(seed)

        # 足球相关数据
        self.teams = [
            "Manchester United",
            "Manchester City",
            "Liverpool",
            "Chelsea",
            "Arsenal",
            "Tottenham",
            "Leicester City",
            "West Ham",
            "Everton",
            "Aston Villa",
            "Newcastle United",
            "Wolves",
            "Leeds United",
            "Southampton",
            "Brighton",
            "Burnley",
        ]

        self.leagues = ["Premier League", "La Liga", "Serie A", "Bundesliga", "Ligue 1"]

        # 预测结果类型
        self.outcomes = ["HOME_WIN", "DRAW", "AWAY_WIN"]

    def generate_match_data(self) -> Dict[str, Any]:
        """生成比赛数据"""
        home_team, away_team = random.sample(self.teams, 2)
        league = random.choice(self.leagues)

        # 生成未来日期（用于预测）
        days_ahead = random.randint(1, 30)
        match_date = datetime.now() + timedelta(days=days_ahead)

        return {
            "match_id": str(uuid.uuid4()),
            "home_team": home_team,
            "away_team": away_team,
            "league": league,
            "match_date": match_date.isoformat(),
            "venue": f"{home_team} Stadium",
            "season": f"{match_date.year-1}/{match_date.year}",
            "round": random.randint(1, 38),
            "status": "scheduled",
        }

    def generate_features(self, feature_count: int = 12) -> List[float]:
        """生成特征数据"""
        # 生成足球相关的特征值
        features = []

        # 主队相关特征
        features.append(random.uniform(0.0, 3.0))  # 主队近期进球数
        features.append(random.uniform(0.0, 3.0))  # 主队近期失球数
        features.append(random.uniform(0.0, 1.0))  # 主队胜率
        features.append(random.uniform(10.0, 50.0))  # 主队积分

        # 客队相关特征
        features.append(random.uniform(0.0, 3.0))  # 客队近期进球数
        features.append(random.uniform(0.0, 3.0))  # 客队近期失球数
        features.append(random.uniform(0.0, 1.0))  # 客队胜率
        features.append(random.uniform(10.0, 50.0))  # 客队积分

        # 历史交锋特征
        features.append(random.randint(0, 10))  # 历史交锋次数
        features.append(random.uniform(0.0, 1.0))  # 主队历史胜率
        features.append(random.uniform(0.0, 1.0))  # 平局概率
        features.append(random.uniform(0.0, 1.0))  # 客队历史胜率

        # 如果需要更多特征，添加随机值
        while len(features) < feature_count:
            features.append(random.uniform(-1.0, 1.0))

        return features[:feature_count]

    def generate_prediction_result(
        self, model_name: str = "xgboost_v2"
    ) -> Dict[str, Any]:
        """生成预测结果"""
        # 生成随机概率，确保总和为1
        probs = [random.random() for _ in range(3)]
        total = sum(probs)
        probs = [p / total for p in probs]

        # 选择预测结果（最高概率）
        outcome_idx = probs.index(max(probs))
        predicted_outcome = self.outcomes[outcome_idx]

        return {
            "match_id": str(uuid.uuid4()),
            "home_team": random.choice(self.teams),
            "away_team": random.choice(
                [t for t in self.teams if t != random.choice(self.teams)]
            ),
            "prediction": predicted_outcome,
            "probabilities": {
                "HOME_WIN": probs[0],
                "DRAW": probs[1],
                "AWAY_WIN": probs[2],
            },
            "confidence": max(probs),
            "model_name": model_name,
            "model_version": "2.1.0",
            "prediction_time": datetime.now().isoformat(),
            "processing_time_ms": random.uniform(10.0, 100.0),
            "features_count": random.randint(8, 15),
            "feature_names": [f"feature_{i}" for i in range(random.randint(8, 15))],
        }

    def generate_batch_predictions(self, batch_size: int = 10) -> Dict[str, Any]:
        """生成批量预测结果"""
        predictions = []

        for _ in range(batch_size):
            prediction = self.generate_prediction_result()
            predictions.append(prediction)

        return {
            "batch_id": str(uuid.uuid4()),
            "batch_size": batch_size,
            "predictions": predictions,
            "status": "completed",
            "created_time": datetime.now().isoformat(),
            "completed_time": datetime.now().isoformat(),
            "total_processing_time_ms": sum(
                p["processing_time_ms"] for p in predictions
            ),
        }

    def generate_model_info(self) -> Dict[str, Any]:
        """生成模型信息"""
        return {
            "model_name": random.choice(
                ["xgboost_v2", "neural_net_v1", "random_forest_v3"]
            ),
            "version": f"{random.randint(1, 5)}.{random.randint(0, 9)}.{random.randint(0, 9)}",
            "type": random.choice(["classifier", "regressor"]),
            "algorithm": random.choice(["XGBoost", "Neural Network", "Random Forest"]),
            "features_count": random.randint(10, 50),
            "training_samples": random.randint(10000, 100000),
            "accuracy": random.uniform(0.6, 0.8),
            "precision": random.uniform(0.6, 0.8),
            "recall": random.uniform(0.6, 0.8),
            "f1_score": random.uniform(0.6, 0.8),
            "training_date": (
                datetime.now() - timedelta(days=random.randint(1, 30))
            ).isoformat(),
            "last_updated": datetime.now().isoformat(),
            "model_path": f"/models/xgboost_v2_{random.randint(1, 100)}.pkl",
            "size_mb": random.uniform(5.0, 50.0),
        }

    def generate_health_check_data(self) -> Dict[str, Any]:
        """生成健康检查数据"""
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "service": "football-prediction-api",
            "version": "2.0.0",
            "uptime_seconds": random.randint(3600, 86400),  # 1小时到24小时
            "response_time_ms": random.uniform(5.0, 50.0),
            "checks": {
                "database": {
                    "status": "healthy" if random.random() > 0.1 else "unhealthy",
                    "response_time_ms": random.uniform(1.0, 20.0),
                    "details": {
                        "connection_pool": "active",
                        "active_connections": random.randint(1, 10),
                        "max_connections": 20,
                    },
                },
                "redis": {
                    "status": "healthy",
                    "response_time_ms": random.uniform(0.5, 5.0),
                    "details": {
                        "memory_usage": f"{random.randint(50, 200)}MB",
                        "connected_clients": random.randint(1, 5),
                    },
                },
                "model_service": {
                    "status": "healthy",
                    "response_time_ms": random.uniform(10.0, 100.0),
                    "details": {
                        "loaded_models": random.randint(1, 5),
                        "cache_hit_rate": random.uniform(0.7, 0.95),
                    },
                },
            },
        }

    def generate_error_data(self, error_type: str = "validation") -> Dict[str, Any]:
        """生成错误数据"""
        error_messages = {
            "validation": [
                "Invalid input features",
                "Missing required fields",
                "Feature dimension mismatch",
            ],
            "model": [
                "Model not found",
                "Model loading failed",
                "Model inference error",
            ],
            "database": [
                "Connection timeout",
                "Query execution failed",
                "Database unavailable",
            ],
            "external_api": [
                "Rate limit exceeded",
                "API unavailable",
                "Invalid response format",
            ],
        }

        return {
            "error_id": str(uuid.uuid4()),
            "error_type": error_type,
            "message": random.choice(error_messages.get(error_type, ["Unknown error"])),
            "timestamp": datetime.now().isoformat(),
            "status_code": random.choice([400, 404, 429, 500, 503]),
            "details": {
                "request_id": str(uuid.uuid4()),
                "user_id": random.randint(1000, 9999),
                "endpoint": random.choice(["/predict", "/models", "/health"]),
                "method": random.choice(["GET", "POST", "PUT"]),
            },
        }

    def generate_metrics_data(self) -> Dict[str, Any]:
        """生成指标数据"""
        return {
            "prediction_requests_total": random.randint(1000, 10000),
            "prediction_accuracy": random.uniform(0.6, 0.8),
            "average_response_time_ms": random.uniform(20.0, 100.0),
            "cache_hit_rate": random.uniform(0.7, 0.95),
            "model_load_count": random.randint(10, 100),
            "error_rate": random.uniform(0.01, 0.05),
            "active_models": random.randint(1, 5),
            "memory_usage_mb": random.uniform(100.0, 500.0),
            "cpu_usage_percent": random.uniform(10.0, 80.0),
            "last_updated": datetime.now().isoformat(),
        }

    def generate_config_data(self) -> Dict[str, Any]:
        """生成配置数据"""
        return {
            "database": {
                "host": "localhost",
                "port": 5432,
                "name": "football_prediction_test",
                "user": "test_user",
                "pool_size": random.randint(5, 20),
                "max_overflow": random.randint(10, 30),
            },
            "redis": {
                "host": "localhost",
                "port": 6379,
                "db": 0,
                "password": None,
                "max_connections": random.randint(10, 50),
            },
            "model": {
                "default_model": "xgboost_v2",
                "model_path": "/app/data/models",
                "cache_ttl": random.randint(3600, 7200),
                "max_features": random.randint(20, 50),
            },
            "api": {
                "host": "0.0.0.0",
                "port": 8000,
                "debug": False,
                "workers": random.randint(1, 4),
                "timeout": random.randint(30, 120),
            },
            "monitoring": {
                "enabled": True,
                "metrics_port": 9090,
                "health_check_interval": random.randint(10, 60),
                "log_level": random.choice(["DEBUG", "INFO", "WARNING", "ERROR"]),
            },
        }

    def save_test_data(
        self, data: Dict[str, Any], filename: str, data_type: str = "json"
    ):
        """保存测试数据到文件

        Args:
            data: 要保存的数据
            filename: 文件名（不含扩展名）
            data_type: 数据类型 (json, csv等)
        """
        from pathlib import Path

        # 确保数据目录存在
        data_dir = Path(__file__).parent.parent / "fixtures"
        data_dir.mkdir(exist_ok=True)

        # 保存文件
        if data_type.lower() == "json":
            filepath = data_dir / f"{filename}.json"
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)
            print(f"✅ 测试数据已保存到: {filepath}")
        else:
            raise ValueError(f"不支持的数据类型: {data_type}")

    def generate_test_dataset(
        self, dataset_name: str = "test_dataset", size: int = 100
    ):
        """生成完整的测试数据集

        Args:
            dataset_name: 数据集名称
            size: 数据集大小
        """
        dataset = {
            "metadata": {
                "name": dataset_name,
                "created_time": datetime.now().isoformat(),
                "size": size,
                "version": "1.0.0",
            },
            "matches": [self.generate_match_data() for _ in range(size)],
            "predictions": [
                self.generate_prediction_result() for _ in range(size // 2)
            ],
            "health_checks": [self.generate_health_check_data() for _ in range(5)],
            "models": [self.generate_model_info() for _ in range(3)],
            "errors": [
                self.generate_error_data(
                    random.choice(["validation", "model", "database"])
                )
                for _ in range(10)
            ],
            "metrics": self.generate_metrics_data(),
            "config": self.generate_config_data(),
        }

        self.save_test_data(dataset, dataset_name)
        return dataset


# 便捷函数
def create_test_data_generator(seed: Optional[int] = 42) -> TestDataGenerator:
    """创建测试数据生成器

    Args:
        seed: 随机种子

    Returns:
        TestDataGenerator实例
    """
    return TestDataGenerator(seed)


def generate_quick_test_data() -> Dict[str, Any]:
    """快速生成基础测试数据"""
    generator = TestDataGenerator(42)

    return {
        "match": generator.generate_match_data(),
        "features": generator.generate_features(),
        "prediction": generator.generate_prediction_result(),
        "health_check": generator.generate_health_check_data(),
        "model_info": generator.generate_model_info(),
    }


if __name__ == "__main__":
    # 示例用法
    generator = TestDataGenerator(42)

    # 生成测试数据集
    dataset = generator.generate_test_dataset("example_dataset", 50)

    # 生成快速测试数据
    quick_data = generate_quick_test_data()
    print("快速测试数据:")
    print(json.dumps(quick_data, indent=2, ensure_ascii=False, default=str))
