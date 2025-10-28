# mypy: ignore-errors
"""
仓储模式API端点
Repository Pattern API Endpoints

展示仓储模式的查询和管理功能。
Demonstrates query and management features of the repository pattern.
"""

from datetime import date
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Query

from ..repositories import (
    MatchRepoDep,
    PredictionRepoDep,
    QuerySpec,
    ReadOnlyMatchRepoDep,
    ReadOnlyPredictionRepoDep,
    ReadOnlyUserRepoDep,
    UserRepoDep,
)

router = APIRouter(prefix="/repositories", tags=["仓储模式"])

# ==================== 预测仓储端点 ====================


@router.get("/predictions", summary="获取预测列表")
async def get_predictions(
    repo: ReadOnlyPredictionRepoDep,
    limit: int = Query(100, ge=1, le=1000, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
    user_id: Optional[int] = Query(None, description="用户ID筛选"),
    match_id: Optional[int] = Query(None, description="比赛ID筛选"),
) -> Dict[str, Any]:
    """获取预测列表（使用只读仓储）"""
    filters = {}
    if user_id:
        filters["user_id"] = user_id
    if match_id:
        filters["match_id"] = match_id

    query_spec = QuerySpec(
        filters=filters, order_by=["-created_at"], limit=limit, offset=offset
    )

    predictions = await repo.find_many(query_spec)
    return {
        "total": len(predictions),
        "predictions": [
            {
                "id": p.id,
                "user_id": p.user_id,
                "match_id": p.match_id,
                "predicted_home": p.predicted_home,
                "predicted_away": p.predicted_away,
                "confidence": float(p.confidence),
                "created_at": p.created_at,
            }
            for p in predictions
        ],
    }


@router.get("/predictions/{prediction_id}", summary="获取单个预测")
async def get_prediction(
    prediction_id: int, repo: ReadOnlyPredictionRepoDep
) -> Dict[str, Any]:
    """获取单个预测详情"""
    _prediction = await repo.get_by_id(prediction_id)
    if not prediction:
        raise HTTPException(status_code=404, detail="预测不存在")

    return {
        "id": prediction.id,
        "user_id": prediction.user_id,
        "match_id": prediction.match_id,
        "predicted_home": prediction.predicted_home,
        "predicted_away": prediction.predicted_away,
        "confidence": float(prediction.confidence),
        "strategy_used": prediction.strategy_used,
        "notes": prediction.notes,
        "created_at": prediction.created_at,
        "updated_at": prediction.updated_at,
    }


@router.get("/predictions/user/{user_id}/statistics", summary="获取用户预测统计")
async def get_user_prediction_statistics(
    user_id: int,
    repo: ReadOnlyPredictionRepoDep,
    days: Optional[int] = Query(None, ge=1, le=365, description="统计天数"),
) -> Dict[str, Any]:
    """获取用户预测统计信息"""
    stats = await repo.get_user_statistics(user_id, period_days=days)
    return stats


@router.get("/predictions/match/{match_id}/statistics", summary="获取比赛预测统计")
async def get_match_prediction_statistics(
    match_id: int, repo: ReadOnlyPredictionRepoDep
) -> Dict[str, Any]:
    """获取比赛预测统计信息"""
    stats = await repo.get_match_statistics(match_id)
    return stats


@router.post("/predictions", summary="创建预测")
async def create_prediction(
    prediction_data: Dict[str, Any],
    repo: PredictionRepoDep,
) -> Dict[str, Any]:
    """创建新预测（使用写仓储）"""
    try:
        _prediction = await repo.create(prediction_data)
        return {
            "message": "预测创建成功",
            "prediction": {
                "id": prediction.id,
                "user_id": prediction.user_id,
                "match_id": prediction.match_id,
                "predicted_home": prediction.predicted_home,
                "predicted_away": prediction.predicted_away,
                "confidence": float(prediction.confidence),
                "created_at": prediction.created_at,
            },
        }
    except (ValueError, KeyError, AttributeError, HTTPError, RequestException) as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/predictions/{prediction_id}", summary="更新预测")
async def update_prediction(
    prediction_id: int, update_data: Dict[str, Any], repo: PredictionRepoDep
) -> Dict[str, Any]:
    """更新预测（使用写仓储）"""
    _prediction = await repo.update_by_id(prediction_id, update_data)
    if not prediction:
        raise HTTPException(status_code=404, detail="预测不存在")

    return {
        "message": "预测更新成功",
        "prediction": {"id": prediction.id, "updated_at": prediction.updated_at},
    }


# ==================== 用户仓储端点 ====================


@router.get("/users", summary="获取用户列表")
async def get_users(
    repo: ReadOnlyUserRepoDep,
    limit: int = Query(100, ge=1, le=1000, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
    is_active: Optional[bool] = Query(None, description="是否活跃"),
) -> Dict[str, Any]:
    """获取用户列表"""
    filters = {}
    if is_active is not None:
        filters["is_active"] = is_active

    query_spec = QuerySpec(
        filters=filters, order_by=["username"], limit=limit, offset=offset
    )

    users = await repo.find_many(query_spec)
    return {
        "total": len(users),
        "users": [
            {
                "id": u.id,
                "username": u.username,
                "email": u.email,
                "display_name": u.display_name,
                "role": u.role,
                "is_active": u.is_active,
                "created_at": u.created_at,
            }
            for u in users
        ],
    }


@router.get("/users/{user_id}", summary="获取用户详情")
async def get_user(user_id: int, repo: ReadOnlyUserRepoDep) -> Dict[str, Any]:
    """获取用户详情"""
    _user = await repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "display_name": user.display_name,
        "role": user.role,
        "is_active": user.is_active,
        "last_login_at": user.last_login_at,
        "created_at": user.created_at,
    }


@router.get("/users/{user_id}/statistics", summary="获取用户完整统计")
async def get_user_statistics(user_id: int, repo: UserRepoDep) -> Dict[str, Any]:
    """获取用户完整统计信息（使用读写仓储的统计方法）"""
    stats = await repo.get_user_statistics(user_id)
    return stats


@router.get("/users/search", summary="搜索用户")
async def search_users(
    repo: ReadOnlyUserRepoDep,
    keyword: str = Query(..., min_length=1, description="搜索关键词"),
    limit: int = Query(20, ge=1, le=100, description="返回数量限制"),
) -> Dict[str, Any]:
    """搜索用户"""
    users = await repo.search_users(keyword)
    return {
        "keyword": keyword,
        "total": len(users[:limit]),
        "users": [
            {
                "id": u.id,
                "username": u.username,
                "display_name": u.display_name,
                "email": u.email,
            }
            for u in users[:limit]
        ],
    }


@router.get("/users/active", summary="获取活跃用户")
async def get_active_users(
    repo: ReadOnlyUserRepoDep,
    limit: int = Query(50, ge=1, le=100, description="返回数量限制"),
) -> Dict[str, Any]:
    """获取活跃用户列表"""
    users = await repo.get_active_users(limit)
    return {
        "total": len(users),
        "active_users": [
            {
                "id": u.id,
                "username": u.username,
                "display_name": u.display_name,
                "last_login_at": u.last_login_at,
            }
            for u in users
        ],
    }


@router.post("/users", summary="创建用户")
async def create_user(user_data: Dict[str, Any], repo: UserRepoDep) -> Dict[str, Any]:
    """创建新用户"""
    try:
        _user = await repo.create(user_data)
        return {
            "message": "用户创建成功",
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "created_at": user.created_at,
            },
        }
    except (ValueError, KeyError, AttributeError, HTTPError, RequestException) as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==================== 比赛仓储端点 ====================


@router.get("/matches", summary="获取比赛列表")
async def get_matches(
    repo: ReadOnlyMatchRepoDep,
    limit: int = Query(100, ge=1, le=1000, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
    status: Optional[str] = Query(None, description="比赛状态筛选"),
) -> Dict[str, Any]:
    """获取比赛列表"""
    filters = {}
    if status:
        filters["status"] = status

    query_spec = QuerySpec(
        filters=filters, order_by=["-match_date"], limit=limit, offset=offset
    )

    _matches = await repo.find_many(query_spec)
    return {
        "total": len(matches),
        "matches": [
            {
                "id": m.id,
                "home_team_name": m.home_team_name,
                "away_team_name": m.away_team_name,
                "competition_name": m.competition_name,
                "match_date": m.match_date,
                "status": m.status,
                "score": (
                    {"home": m.home_score, "away": m.away_score}
                    if m.home_score is not None
                    else None
                ),
            }
            for m in matches
        ],
    }


@router.get("/matches/upcoming", summary="获取即将到来的比赛")
async def get_upcoming_matches(
    repo: ReadOnlyMatchRepoDep,
    days: int = Query(7, ge=1, le=30, description="未来天数"),
    limit: int = Query(50, ge=1, le=100, description="返回数量限制"),
) -> Dict[str, Any]:
    """获取即将到来的比赛"""
    _matches = await repo.get_upcoming_matches(days, limit)
    return {
        "days": days,
        "total": len(matches),
        "matches": [
            {
                "id": m.id,
                "home_team": m.home_team_name,
                "away_team": m.away_team_name,
                "competition": m.competition_name,
                "match_date": m.match_date,
            }
            for m in matches
        ],
    }


@router.get("/matches/live", summary="获取正在进行的比赛")
async def get_live_matches(repo: ReadOnlyMatchRepoDep) -> Dict[str, Any]:
    """获取正在进行的比赛"""
    _matches = await repo.get_live_matches()
    return {
        "total": len(matches),
        "live_matches": [
            {
                "id": m.id,
                "home_team": m.home_team_name,
                "away_team": m.away_team_name,
                "score": (
                    {"home": m.home_score, "away": m.away_score}
                    if m.home_score is not None
                    else None
                ),
                "started_at": m.started_at,
            }
            for m in matches
        ],
    }


@router.get("/matches/{match_id}", summary="获取比赛详情")
async def get_match(match_id: int, repo: ReadOnlyMatchRepoDep) -> Dict[str, Any]:
    """获取比赛详情"""
    match = await repo.get_by_id(match_id)
    if not match:
        raise HTTPException(status_code=404, detail="比赛不存在")

    return {
        "id": match.id,
        "home_team_name": match.home_team_name,
        "away_team_name": match.away_team_name,
        "competition_name": match.competition_name,
        "season": match.season,
        "match_date": match.match_date,
        "status": match.status,
        "score": (
            {"home": match.home_score, "away": match.away_score}
            if match.home_score is not None
            else None
        ),
        "created_at": match.created_at,
    }


@router.get("/matches/{match_id}/statistics", summary="获取比赛统计")
async def get_match_statistics(match_id: int, repo: MatchRepoDep) -> Dict[str, Any]:
    """获取比赛统计信息"""
    stats = await repo.get_match_statistics(match_id)
    return stats


@router.get("/matches/search", summary="搜索比赛")
async def search_matches(
    repo: ReadOnlyMatchRepoDep,
    keyword: str = Query(..., min_length=1, description="搜索关键词"),
    limit: int = Query(20, ge=1, le=100, description="返回数量限制"),
) -> Dict[str, Any]:
    """搜索比赛"""
    _matches = await repo.search_matches(keyword)
    return {
        "keyword": keyword,
        "total": len(matches[:limit]),
        "matches": [
            {
                "id": m.id,
                "home_team": m.home_team_name,
                "away_team": m.away_team_name,
                "competition": m.competition_name,
                "match_date": m.match_date,
                "status": m.status,
            }
            for m in matches[:limit]
        ],
    }


@router.get("/matches/date-range", summary="获取日期范围内的比赛")
async def get_matches_by_date_range(
    repo: ReadOnlyMatchRepoDep,
    start_date: date = Query(..., description="开始日期"),
    end_date: date = Query(..., description="结束日期"),
    status: Optional[str] = Query(None, description="比赛状态"),
    limit: int = Query(100, ge=1, le=1000, description="返回数量限制"),
) -> Dict[str, Any]:
    """获取指定日期范围内的比赛"""
    _matches = await repo.get_matches_by_date_range(start_date, end_date, status, limit)
    return {
        "start_date": start_date,
        "end_date": end_date,
        "status": status,
        "total": len(matches),
        "matches": [
            {
                "id": m.id,
                "home_team": m.home_team_name,
                "away_team": m.away_team_name,
                "competition": m.competition_name,
                "match_date": m.match_date,
                "status": m.status,
            }
            for m in matches
        ],
    }


@router.post("/matches/{match_id}/start", summary="开始比赛")
async def start_match(match_id: int, repo: MatchRepoDep) -> Dict[str, Any]:
    """开始比赛（更新状态为LIVE）"""
    match = await repo.start_match(match_id)
    if not match:
        raise HTTPException(status_code=404, detail="比赛不存在")

    return {
        "message": "比赛已开始",
        "match_id": match.id,
        "status": match.status,
        "started_at": match.started_at,
    }


@router.post("/matches/{match_id}/finish", summary="结束比赛")
async def finish_match(
    match_id: int,
    repo: MatchRepoDep,
    home_score: int = Query(..., ge=0, description="主队得分"),
    away_score: int = Query(..., ge=0, description="客队得分"),
) -> Dict[str, Any]:
    """结束比赛并记录比分"""
    match = await repo.finish_match(match_id, home_score, away_score)
    if not match:
        raise HTTPException(status_code=404, detail="比赛不存在")

    return {
        "message": "比赛已结束",
        "match_id": match.id,
        "final_score": {"home": match.home_score, "away": match.away_score},
        "finished_at": match.finished_at,
    }


# ==================== 仓储模式演示端点 ====================


@router.get("/demo/query-spec", summary="QuerySpec查询演示")
async def demo_query_spec(
    repo: ReadOnlyPredictionRepoDep,
) -> Dict[str, Any]:
    """演示QuerySpec的灵活查询能力"""
    from datetime import date, timedelta

    # 示例1：基础筛选
    basic_filters = {"user_id": 1, "confidence": {"$gte": 0.8}}
    query_spec1 = QuerySpec(filters=basic_filters, order_by=["-created_at"], limit=10)
    results1 = await repo.find_many(query_spec1)

    # 示例2：复杂筛选
    complex_filters = {
        "$and": [
            {"created_at": {"$gte": date.today() - timedelta(days=7)}},
            {"$or": [{"predicted_home": {"$gt": 2}}, {"predicted_away": {"$gt": 2}}]},
        ]
    }
    query_spec2 = QuerySpec(
        filters=complex_filters, order_by=["confidence", "-created_at"], limit=20
    )
    results2 = await repo.find_many(query_spec2)

    return {
        "demo": "QuerySpec灵活查询演示",
        "examples": [
            {
                "name": "基础筛选",
                "filters": basic_filters,
                "results_count": len(results1),
            },
            {
                "name": "复杂筛选",
                "filters": complex_filters,
                "results_count": len(results2),
            },
        ],
    }


@router.get("/demo/read-only-vs-write", summary="只读与读写仓储对比")
async def demo_read_only_vs_write(
    read_only_repo: ReadOnlyPredictionRepoDep,
    write_repo: PredictionRepoDep,
    prediction_id: int = Query(1, ge=1, description="预测ID"),
) -> Dict[str, Any]:
    """演示只读仓储和读写仓储的区别"""
    # 只读仓储查询
    _prediction = await read_only_repo.get_by_id(prediction_id)

    # 尝试使用只读仓储写入（会抛出异常）
    can_write = False
    error_message = None
    try:
        await read_only_repo.save(prediction)
    except NotImplementedError as e:
        error_message = str(e)
    except (ValueError, KeyError, AttributeError, HTTPError, RequestException):
        can_write = True

    return {
        "prediction_id": prediction_id,
        "prediction_exists": prediction is not None,
        "read_only_repository": {
            "can_read": True,
            "can_write": can_write,
            "error_on_write": error_message,
        },
        "write_repository": {"can_read": True, "can_write": True},
    }
