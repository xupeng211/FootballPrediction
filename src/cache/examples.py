"""
缓存装饰器使用示例
Cache Decorators Usage Examples

展示如何在项目中使用各种缓存装饰器。
"""

import asyncio
from typing import Any, Dict, List, Optional

from .decorators import (
    cache_by_user,
    cache_invalidate,
    cache_match_data,
    cache_result,
    cache_team_stats,
    cache_user_predictions,
    cache_with_ttl,
)


# 示例1: 基础结果缓存
@cache_result(ttl=3600, prefix="example")
def expensive_computation(x: int, y: int) -> int:
    """模拟耗时的计算"""
    logger.info(f"执行计算: {x} + {y}")
    return x + y


# 示例2: 异步函数缓存
@cache_with_ttl(ttl_seconds=1800, prefix="api_calls")
async def fetch_user_data(user_id: int) -> Dict[str, Any]:
    """模拟API调用获取用户数据"""
    logger.info(f"获取用户数据: {user_id}")
    await asyncio.sleep(1)  # 模拟网络延迟
    return {"id": user_id, "name": f"User {user_id}", "age": 25}


# 示例3: 基于用户的缓存
@cache_by_user(ttl=7200, prefix="user_profile", user_param="user_id")
def get_user_profile(user_id: int, include_sensitive: bool = False) -> Dict[str, Any]:
    """获取用户档案（基于用户缓存）"""
    logger.info(f"获取用户档案: {user_id}, 敏感信息: {include_sensitive}")
    profile = {
        "user_id": user_id,
        "username": f"user_{user_id}",
        "email": f"user{user_id}@example.com",
        "profile_completed": True,
    }
    if include_sensitive:
        profile["phone"] = f"123-456-{user_id:04d}"
        profile["address"] = f"Street {user_id}, City"
    return profile


# 示例4: 带条件缓存的装饰器
@cache_result(
    ttl=600,
    prefix="search_results",
    unless=lambda query, limit: len(query) < 3,  # 查询长度小于3时不缓存
)
def search_documents(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """搜索文档（查询长度小于3时不缓存）"""
    logger.info(f"搜索文档: query='{query}', limit={limit}")
    # 模拟搜索结果
    return [
        {"id": i, "title": f"Document {i} for {query}", "score": 0.9 - i * 0.1}
        for i in range(min(limit, 5))
    ]


# 示例5: 缓存失效装饰器
def generate_invalidation_keys(func, args, kwargs, result):
    """生成缓存失效键的函数"""
    # 如果是更新操作，失效相关缓存
    if "update" in func.__name__:
        user_id = kwargs.get("user_id") or args[0] if args else None
        if user_id:
            return [
                f"user_profile:user:{user_id}:*",
                f"user_predictions:user:{user_id}:*",
            ]
    return []


@cache_invalidate(
    pattern="user_profile:*",  # 失效所有用户档案缓存
    key_generator=generate_invalidation_keys,
)
def update_user_profile(user_id: int, **updates) -> Dict[str, Any]:
    """更新用户档案（会失效相关缓存）"""
    logger.info(f"更新用户档案: {user_id}, 更新: {updates}")
    # 模拟更新操作
    return {"user_id": user_id, "updated_fields": list(updates.keys())}


# 示例6: 便捷装饰器使用
@cache_user_predictions(ttl_seconds=3600)
def get_user_predictions(user_id: int, match_id: Optional[int] = None) -> List[Dict]:
    """获取用户预测（使用便捷装饰器）"""
    logger.info(f"获取用户预测: user_id={user_id}, match_id={match_id}")
    return [
        {"match_id": i, "prediction": "2-1", "confidence": 0.85}
        for i in [1, 2, 3]
        if match_id is None or i == match_id
    ]


@cache_match_data(ttl_seconds=1800)
async def get_match_details(match_id: int) -> Dict:
    """获取比赛详情（使用便捷装饰器）"""
    logger.info(f"获取比赛详情: {match_id}")
    await asyncio.sleep(0.5)
    return {
        "match_id": match_id,
        "home_team": "Team A",
        "away_team": "Team B",
        "kickoff": "2024-01-01T20:00:00Z",
    }


@cache_team_stats(ttl_seconds=7200)
def calculate_team_statistics(team_id: int, season: str) -> Dict:
    """计算球队统计（使用便捷装饰器）"""
    logger.info(f"计算球队统计: team_id={team_id}, season={season}")
    return {
        "team_id": team_id,
        "season": season,
        "played": 20,
        "won": 12,
        "drawn": 5,
        "lost": 3,
        "goals_for": 35,
        "goals_against": 18,
        "points": 41,
    }


# 示例7: 自定义键生成器
def custom_key_generator(func, args, kwargs, user_id=None):
    """自定义缓存键生成器"""
    func_name = func.__qualname__
    # 使用特定的参数组合生成键
    key_parts = [func_name]

    # 添加特定的参数
    if "team_id" in kwargs:
        key_parts.append(f"team_{kwargs['team_id']}")
    if "season" in kwargs:
        key_parts.append(f"season_{kwargs['season']}")

    return ":".join(key_parts)


@cache_result(
    ttl=3600,
    prefix="custom",
    key_generator=custom_key_generator,
)
def get_team_form(team_id: int, season: str, last_n: int = 5) -> List[Dict]:
    """获取球队近期表现（使用自定义键生成器）"""
    logger.info(f"获取球队表现: team_id={team_id}, season={season}, last_n={last_n}")
    return [
        {"result": "W", "goals_for": 2, "goals_against": 1},
        {"result": "D", "goals_for": 1, "goals_against": 1},
        {"result": "W", "goals_for": 3, "goals_against": 0},
        {"result": "L", "goals_for": 0, "goals_against": 2},
        {"result": "W", "goals_for": 2, "goals_against": 0},
    ][:last_n]


# 示例8: 组合使用装饰器
class PredictionService:
    """预测服务类，展示装饰器的组合使用"""

    @cache_match_data(ttl_seconds=600)
    async def get_match_odds(self, match_id: int) -> Dict[str, float]:
        """获取比赛赔率"""
        await asyncio.sleep(0.3)
        return {
            "home_win": 2.10,
            "draw": 3.40,
            "away_win": 3.20,
        }

    @cache_by_user(ttl=300, user_param="user_id")
    async def calculate_user_prediction(
        self, user_id: int, match_id: int, model_type: str = "default"
    ) -> Dict[str, Any]:
        """计算用户预测（基于用户缓存）"""
        # 获取比赛数据
        odds = await self.get_match_odds(match_id)

        # 模拟预测计算
        await asyncio.sleep(0.5)

        return {
            "user_id": user_id,
            "match_id": match_id,
            "model_type": model_type,
            "prediction": "2-1",
            "confidence": 0.78,
            "used_odds": odds,
        }

    @cache_invalidate(pattern="predictions:user:{user_id}:*")
    async def submit_prediction(
        self, user_id: int, match_id: int, prediction: str
    ) -> Dict[str, Any]:
        """提交预测（会失效用户相关缓存）"""
        logger.info(
            f"提交预测: _user ={user_id}, match={match_id}, _prediction ={prediction}"
        )

        # 保存预测到数据库...

        return {
            "success": True,
            "prediction_id": f"pred_{match_id}_{user_id}",
            "invalidated_cache": f"predictions:user:{user_id}:*",
        }


# 运行示例的函数
async def run_examples():
    """运行所有示例"""
    logger.info("=== 缓存装饰器示例 ===\n")

    # 示例1: 基础缓存
    logger.info("1. 基础结果缓存:")
    result1 = expensive_computation(10, 20)
    logger.info(f"结果: {result1}")
    _result2 = expensive_computation(10, 20)  # 应该从缓存获取
    logger.info(f"结果: {result2}\n")

    # 示例2: 异步缓存
    logger.info("2. 异步函数缓存:")
    user_data = await fetch_user_data(100)
    logger.info(f"用户数据: {user_data}")
    user_data2 = await fetch_user_data(100)  # 应该从缓存获取
    logger.info(f"用户数据: {user_data2}\n")

    # 示例3: 用户缓存
    logger.info("3. 基于用户的缓存:")
    profile = get_user_profile(200)
    logger.info(f"用户档案: {profile}")
    profile2 = get_user_profile(200, include_sensitive=True)  # 不同的参数，新缓存
    logger.info(f"用户档案（含敏感信息）: {profile2}\n")

    # 示例4: 条件缓存
    logger.info("4. 条件缓存:")
    docs1 = search_documents("test", limit=5)  # 会被缓存
    logger.info(f"搜索结果: {docs1}")
    docs2 = search_documents("test", limit=5)  # 从缓存获取
    logger.info(f"搜索结果: {docs2}")
    docs3 = search_documents("ab", limit=5)  # 查询太短，不会被缓存
    logger.info(f"搜索结果: {docs3}\n")

    # 示例5: 缓存失效
    logger.info("5. 缓存失效:")
    profile3 = get_user_profile(300)
    logger.info(f"更新前用户档案: {profile3}")
    updated = update_user_profile(300, email="newemail@example.com")
    logger.info(f"更新结果: {updated}")
    profile4 = get_user_profile(300)  # 应该重新计算
    logger.info(f"更新后用户档案: {profile4}\n")

    # 示例6: 便捷装饰器
    logger.info("6. 便捷装饰器:")
    predictions = get_user_predictions(400)
    logger.info(f"用户预测: {predictions}")
    match_details = await get_match_details(501)
    logger.info(f"比赛详情: {match_details}")
    team_stats = calculate_team_statistics(10, "2023-2024")
    logger.info(f"球队统计: {team_stats}\n")

    # 示例7: 预测服务
    logger.info("7. 预测服务示例:")
    service = PredictionService()
    pred = await service.calculate_user_prediction(500, 601)
    logger.info(f"用户预测: {pred}")
    submit = await service.submit_prediction(500, 601, "2-1")
    logger.info(f"提交结果: {submit}\n")


if __name__ == "__main__":
    # 运行示例
    asyncio.run(run_examples())
