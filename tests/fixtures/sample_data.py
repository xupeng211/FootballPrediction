"""示例测试数据"""

# 用户数据
SAMPLE_USERS = [
    {
        "email": "john.doe@example.com",
        "username": "johndoe",
        "full_name": "John Doe",
        "password": "SecurePass123!",
        "is_active": True,
        "is_verified": True
    },
    {
        "email": "jane.smith@example.com",
        "username": "janesmith",
        "full_name": "Jane Smith",
        "password": "SecurePass456!",
        "is_active": True,
        "is_verified": False
    },
    {
        "email": "admin@example.com",
        "username": "admin",
        "full_name": "Admin User",
        "password": "AdminPass789!",
        "is_active": True,
        "is_verified": True,
        "is_admin": True
    }
]

# 比赛数据
SAMPLE_MATCHES = [
    {
        "id": 1001,
        "home_team": "Manchester United",
        "away_team": "Liverpool",
        "match_date": "2025-10-10T20:00:00Z",
        "league": "Premier League",
        "season": 2025
    },
    {
        "id": 1002,
        "home_team": "Barcelona",
        "away_team": "Real Madrid",
        "match_date": "2025-10-12T21:00:00Z",
        "league": "La Liga",
        "season": 2025
    },
    {
        "id": 1003,
        "home_team": "Bayern Munich",
        "away_team": "Paris Saint-Germain",
        "match_date": "2025-10-15T19:45:00Z",
        "league": "Champions League",
        "season": 2025
    }
]

# 预测数据
SAMPLE_PREDICTIONS = [
    {
        "match_id": 1001,
        "predicted_home_score": 2,
        "predicted_away_score": 1,
        "confidence": 0.75,
        "reasoning": "Home team advantage"
    },
    {
        "match_id": 1002,
        "predicted_home_score": 1,
        "predicted_away_score": 1,
        "confidence": 0.60,
        "reasoning": "Even match"
    },
    {
        "match_id": 1003,
        "predicted_home_score": 3,
        "predicted_away_score": 2,
        "confidence": 0.80,
        "reasoning": "Strong attack"
    }
]

# API测试载荷
API_REQUESTS = {
    "create_user": {
        "email": "test@example.com",
        "username": "testuser",
        "password": "TestPass123!",
        "full_name": "Test User"
    },
    "login": {
        "username": "testuser",
        "password": "TestPass123!"
    },
    "create_prediction": {
        "match_id": 1001,
        "home_team": "Team A",
        "away_team": "Team B",
        "predicted_home_score": 2,
        "predicted_away_score": 1,
        "confidence": 0.75
    },
    "update_prediction": {
        "predicted_home_score": 3,
        "predicted_away_score": 1,
        "confidence": 0.85
    }
}
