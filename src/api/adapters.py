from typing import Any, Dict, List, Optional, Union
"""
适配器模式API端点
Adapter Pattern API Endpoints

展示适配器模式的使用和效果。
Demonstrates the usage and effects of the adapter pattern.
"""

from fastapi import APIRouter, HTTPException, Query, Path
from datetime import datetime, date, timedelta
from requests.exceptions import HTTPError, RequestException

from ..adapters import AdapterFactory, AdapterRegistry

router = APIRouter(prefix="/adapters", tags=["适配器模式"])

# 全局适配器工厂和注册表
adapter_factory = AdapterFactory()
adapter_registry = AdapterRegistry()


# ==================== 适配器管理端点 ====================


@router.get("/registry/status", summary="获取适配器注册表状态")
async def get_registry_status() -> Dict[str, Any]:
    """获取适配器注册表的整体状态"""
    if adapter_registry.status.value == "inactive":
        await adapter_registry.initialize()

    health_status = await adapter_registry.get_health_status()
    metrics_summary = adapter_registry.get_metrics_summary()

    return {
        "registry": health_status,
        "metrics": metrics_summary,
    }


@router.post("/registry/initialize", summary="初始化适配器注册表")
async def initialize_registry() -> Dict[str, str]:
    """初始化适配器注册表"""
    await adapter_registry.initialize()
    return {"message": "适配器注册表已初始化"}


@router.post("/registry/shutdown", summary="关闭适配器注册表")
async def shutdown_registry() -> Dict[str, str]:
    """关闭适配器注册表"""
    await adapter_registry.shutdown()
    return {"message": "适配器注册表已关闭"}


# ==================== 适配器配置管理 ====================


@router.get("/configs", summary="获取适配器配置")
async def get_adapter_configs() -> Dict[str, Any]:
    """获取所有适配器配置"""
    configs = {}
    for name in adapter_factory.list_configs():
        config = adapter_factory.get_config(name)
        if config:
            configs[name] = {
                "type": config.adapter_type,
                "enabled": config.enabled,
                "priority": config.priority,
                "rate_limits": config.rate_limits,
                "cache_config": config.cache_config,
            }

    groups = {}
    for name in adapter_factory.list_group_configs():
        group = adapter_factory.get_group_config(name)
        if group:
            groups[name] = {
                "adapters": group.adapters,
                "primary": group.primary_adapter,
                "fallback_strategy": group.fallback_strategy,
            }

    return {
        "adapters": configs,
        "groups": groups,
    }


@router.post("/configs/load", summary="加载适配器配置")
async def load_adapter_config(config_data: Dict[str, Any]) -> Dict[str, str]:
    """加载适配器配置"""
    # 这里简化处理，实际应用中应该从文件加载
    # 创建示例配置
    from ..adapters.factory import AdapterConfig

    if "adapter_name" in config_data:
        config = AdapterConfig(
            name=config_data["adapter_name"],
            adapter_type=config_data.get("adapter_type", "api-football"),
            enabled=config_data.get("enabled", True),
            parameters=config_data.get("parameters", {}),
        )
        adapter_factory._configs[config.name] = config
        return {"message": f"适配器配置 {config.name} 已加载"}

    return {"error": "缺少adapter_name"}


# ==================== 足球数据适配器演示 ====================


@router.get("/football/matches", summary="获取足球比赛数据")
async def get_football_matches(
    date_from: Optional[date] = Query(None, description="开始日期"),
    date_to: Optional[date] = Query(None, description="结束日期"),
    league_id: Optional[str] = Query(None, description="联赛ID"),
    team_id: Optional[str] = Query(None, description="球队ID"),
    live: bool = Query(False, description="仅获取正在进行中的比赛"),
) -> Dict[str, Any]:
    """
    使用适配器获取足球比赛数据

    演示适配器模式如何统一不同API的数据格式。
    """
    # 确保注册表已初始化
    if adapter_registry.status.value == "inactive":
        await adapter_registry.initialize()

    # 尝试获取可用的足球适配器
    adapter = adapter_registry.get_adapter("api_football_main")
    if not adapter:
        # 尝试创建一个模拟适配器
        from ..adapters.football import ApiFootballAdapter

        mock_adapter = ApiFootballAdapter("demo_key")
        await mock_adapter.initialize()

        # 返回模拟数据
        mock_matches = [
            {
                "id": "12345",
                "home_team": "Manchester United",
                "away_team": "Liverpool",
                "competition": "Premier League",
                "match_date": datetime.now().isoformat(),
                "status": "SCHEDULED",
                "home_score": None,
                "away_score": None,
            },
            {
                "id": "12346",
                "home_team": "Barcelona",
                "away_team": "Real Madrid",
                "competition": "La Liga",
                "match_date": (datetime.now() + timedelta(hours=3)).isoformat(),
                "status": "LIVE",
                "home_score": 1,
                "away_score": 1,
            },
        ]

        return {
            "source": "demo_adapter",
            "total_matches": len(mock_matches),
            "matches": mock_matches,
            "filters": {
                "date_from": date_from.isoformat() if date_from else None,
                "date_to": date_to.isoformat() if date_to else None,
                "league_id": league_id,
                "team_id": team_id,
                "live": live,
            },
            "message": "使用演示适配器返回模拟数据",
        }

    try:
        # 转换日期格式
        match_date = date_from or datetime.now().date()

        # 获取比赛数据
        _matches = await adapter.get_matches(
            date=datetime.combine(match_date, datetime.min.time()),
            league_id=league_id,
            team_id=team_id,
            live=live,
        )

        # 转换为字典格式
        match_dicts = []
        for match in matches:
            match_dict = {
                "id": match.id,
                "home_team": match.home_team,
                "away_team": match.away_team,
                "home_team_id": match.home_team_id,
                "away_team_id": match.away_team_id,
                "competition": match.competition,
                "competition_id": match.competition_id,
                "match_date": match.match_date.isoformat()
                if match.match_date
                else None,
                "status": match.status.value if match.status else None,
                "home_score": match.home_score,
                "away_score": match.away_score,
                "venue": match.venue,
                "weather": match.weather,
            }
            match_dicts.append(match_dict)

        # 获取适配器指标
        adapter_metrics = adapter.get_metrics()

        return {
            "source": adapter.name,
            "total_matches": len(match_dicts),
            "matches": match_dicts,
            "adapter_metrics": adapter_metrics,
            "filters": {
                "date_from": date_from.isoformat() if date_from else None,
                "date_to": date_to.isoformat() if date_to else None,
                "league_id": league_id,
                "team_id": team_id,
                "live": live,
            },
        }

    except (ValueError, KeyError, AttributeError, HTTPError, RequestException) as e:
        raise HTTPException(status_code=500, detail=f"获取比赛数据失败: {str(e)}")


@router.get("/football/matches/{match_id}", summary="获取单个比赛详情")
async def get_football_match(
    match_id: str = Path(..., description="比赛ID"),
) -> Dict[str, Any]:
    """获取单个足球比赛的详细信息"""
    if adapter_registry.status.value == "inactive":
        await adapter_registry.initialize()

    adapter = adapter_registry.get_adapter("api_football_main")
    if not adapter:
        # 返回模拟数据
        return {
            "source": "demo_adapter",
            "match": {
                "id": match_id,
                "home_team": "Manchester United",
                "away_team": "Liverpool",
                "competition": "Premier League",
                "match_date": datetime.now().isoformat(),
                "status": "SCHEDULED",
                "home_score": None,
                "away_score": None,
                "venue": "Old Trafford",
                "weather": {
                    "temperature": "15°C",
                    "condition": "Cloudy",
                },
            },
            "message": "使用演示适配器返回模拟数据",
        }

    try:
        match = await adapter.get_match(match_id)
        if not match:
            raise HTTPException(status_code=404, detail="比赛不存在")

        return {
            "source": adapter.name,
            "match": {
                "id": match.id,
                "home_team": match.home_team,
                "away_team": match.away_team,
                "home_team_id": match.home_team_id,
                "away_team_id": match.away_team_id,
                "competition": match.competition,
                "competition_id": match.competition_id,
                "match_date": match.match_date.isoformat()
                if match.match_date
                else None,
                "status": match.status.value if match.status else None,
                "home_score": match.home_score,
                "away_score": match.away_score,
                "venue": match.venue,
                "weather": match.weather,
            },
        }

    except HTTPException:
        raise
    except (ValueError, KeyError, AttributeError, HTTPError, RequestException) as e:
        raise HTTPException(status_code=500, detail=f"获取比赛详情失败: {str(e)}")


@router.get("/football/teams", summary="获取足球队数据")
async def get_football_teams(
    league_id: Optional[str] = Query(None, description="联赛ID"),
    search: Optional[str] = Query(None, description="搜索关键词"),
) -> Dict[str, Any]:
    """获取足球队数据"""
    if adapter_registry.status.value == "inactive":
        await adapter_registry.initialize()

    adapter = adapter_registry.get_adapter("api_football_main")
    if not adapter:
        # 返回模拟数据
        mock_teams = [
            {
                "id": "111",
                "name": "Manchester United",
                "short_name": "MUFC",
                "country": "England",
                "founded": 1878,
                "stadium": "Old Trafford",
            },
            {
                "id": "222",
                "name": "Liverpool",
                "short_name": "LFC",
                "country": "England",
                "founded": 1892,
                "stadium": "Anfield",
            },
        ]

        # 如果有搜索关键词，过滤结果
        if search:
            mock_teams = [t for t in mock_teams if search.lower() in t["name"].lower()]

        return {
            "source": "demo_adapter",
            "total_teams": len(mock_teams),
            "teams": mock_teams,
            "filters": {
                "league_id": league_id,
                "search": search,
            },
            "message": "使用演示适配器返回模拟数据",
        }

    try:
        _teams = await adapter.get_teams(league_id=league_id)

        # 如果有搜索关键词，过滤结果
        if search:
            _teams = [t for t in teams if search.lower() in t.name.lower()]

        # 转换为字典格式
        team_dicts = []
        for team in teams:
            team_dict = {
                "id": team.id,
                "name": team.name,
                "short_name": team.short_name,
                "country": team.country,
                "founded": team.founded,
                "stadium": team.stadium,
                "logo_url": team.logo_url,
            }
            team_dicts.append(team_dict)

        return {
            "source": adapter.name,
            "total_teams": len(team_dicts),
            "teams": team_dicts,
            "filters": {
                "league_id": league_id,
                "search": search,
            },
        }

    except (ValueError, KeyError, AttributeError, HTTPError, RequestException) as e:
        raise HTTPException(status_code=500, detail=f"获取球队数据失败: {str(e)}")


@router.get("/football/teams/{team_id}/players", summary="获取球队球员")
async def get_team_players(
    team_id: str = Path(..., description="球队ID"),
    season: Optional[str] = Query(None, description="赛季"),
) -> Dict[str, Any]:
    """获取球队的球员列表"""
    if adapter_registry.status.value == "inactive":
        await adapter_registry.initialize()

    adapter = adapter_registry.get_adapter("api_football_main")
    if not adapter:
        # 返回模拟数据
        mock_players = [
            {
                "id": "1001",
                "name": "Bruno Fernandes",
                "team_id": team_id,
                "position": "Midfielder",
                "age": 28,
                "nationality": "Portugal",
                "number": 8,
            },
            {
                "id": "1002",
                "name": "Marcus Rashford",
                "team_id": team_id,
                "position": "Forward",
                "age": 25,
                "nationality": "England",
                "number": 10,
            },
        ]

        return {
            "source": "demo_adapter",
            "team_id": team_id,
            "season": season,
            "total_players": len(mock_players),
            "players": mock_players,
            "message": "使用演示适配器返回模拟数据",
        }

    try:
        players = await adapter.get_players(team_id, season=season)

        # 转换为字典格式
        player_dicts = []
        for player in players:
            player_dict = {
                "id": player.id,
                "name": player.name,
                "team_id": player.team_id,
                "position": player.position,
                "age": player.age,
                "nationality": player.nationality,
                "height": player.height,
                "weight": player.weight,
                "photo_url": player.photo_url,
            }
            player_dicts.append(player_dict)

        return {
            "source": adapter.name,
            "team_id": team_id,
            "season": season,
            "total_players": len(player_dicts),
            "players": player_dicts,
        }

    except (ValueError, KeyError, AttributeError, HTTPError, RequestException) as e:
        raise HTTPException(status_code=500, detail=f"获取球员数据失败: {str(e)}")


# ==================== 适配器演示端点 ====================


@router.get("/demo/comparison", summary="多数据源对比演示")
async def demo_adapter_comparison(
    match_id: str = Query("12345", description="比赛ID"),
) -> Dict[str, Any]:
    """
    演示适配器模式如何统一多个数据源

    对比不同API返回的数据格式。
    """
    # 模拟不同API的原始数据格式
    api_footballdata= {
        "fixture": {"id": 12345, "date": "2023-12-01T19:00:00+00:00"},
        "teams": {"home": {"name": "Team A"}, "away": {"name": "Team B"}},
        "goals": {"home": 2, "away": 1},
    }

    optadata= {
        "match_id": "M12345",
        "date": "2023-12-01 19:00",
        "home_team": {"id": "111", "name": "Team A"},
        "away_team": {"id": "222", "name": "Team B"},
        "score": {"home": 2, "away": 1},
    }

    # 统一后的数据格式
    unified_format = {
        "id": "12345",
        "home_team": "Team A",
        "away_team": "Team B",
        "home_team_id": "111",
        "away_team_id": "222",
        "match_date": "2023-12-01T19:00:00+00:00",
        "home_score": 2,
        "away_score": 1,
    }

    return {
        "comparison": {
            "api_football": {
                "raw": api_football_data,
                "issues": ["嵌套结构复杂", "ID在不同层级", "日期格式不统一"],
            },
            "opta": {
                "raw": opta_data,
                "issues": ["字段命名不一致", "日期格式不同", "数据结构扁平化"],
            },
        },
        "unified_format": unified_format,
        "benefits": ["统一的数据接口", "自动格式转换", "屏蔽API差异", "易于切换数据源"],
    }


@router.get("/demo/fallback", summary="故障转移演示")
async def demo_adapter_fallback() -> Dict[str, Any]:
    """
    演示适配器的故障转移机制

    当主数据源失败时，自动切换到备用源。
    """

    # 模拟三个适配器
    adapters_status = {
        "primary": {"status": "failed", "error": "Connection timeout"},
        "secondary": {"status": "failed", "error": "Rate limit exceeded"},
        "tertiary": {"status": "success", "data": "Match data from tertiary source"},
    }

    # 模拟故障转移过程
    timeline = [
        {"time": "0ms", "action": "尝试主数据源", "status": "失败"},
        {"time": "5000ms", "action": "切换到备用源1", "status": "失败"},
        {"time": "10000ms", "action": "切换到备用源2", "status": "成功"},
    ]

    return {
        "scenario": "主数据源故障，自动故障转移",
        "adapters": adapters_status,
        "timeline": timeline,
        "result": {
            "success": True,
            "response_time": "10000ms",
            "data_source": "tertiary",
            "data": "成功获取数据",
        },
        "features": [
            "自动故障检测",
            "无缝切换数据源",
            "提高系统可用性",
            "透明错误处理",
        ],
    }


@router.get("/demo/transformation", summary="数据转换演示")
async def demo_data_transformation() -> Dict[str, Any]:
    """
    演示适配器的数据转换能力

    将不同格式的数据统一转换为标准格式。
    """
    examples = [
        {
            "source": "API-Football",
            "input": {
                "fixture": {"id": 12345},
                "teams": {"home": {"name": "Man Utd"}, "away": {"name": "Liverpool"}},
                "goals": {"home": 2, "away": 1},
            },
            "output": {
                "id": "12345",
                "homeTeam": "Manchester United",
                "awayTeam": "Liverpool",
                "homeScore": 2,
                "awayScore": 1,
                "status": "FINISHED",
            },
            "transformations": [
                "字段重命名 (fixture.id -> id)",
                "团队名称规范化 (Man Utd -> Manchester United)",
                "状态推断 (有比分 -> FINISHED)",
            ],
        },
        {
            "source": "Opta",
            "input": {
                "match_id": "M12345",
                "home": "Manchester United FC",
                "visitor": "Liverpool FC",
                "final_score": "2-1",
            },
            "output": {
                "id": "12345",
                "homeTeam": "Manchester United",
                "awayTeam": "Liverpool",
                "homeScore": 2,
                "awayScore": 1,
                "status": "FINISHED",
            },
            "transformations": [
                "ID格式化 (M12345 -> 12345)",
                "移除后缀 (FC)",
                "比分解析 (2-1 -> home:2, away:1)",
            ],
        },
    ]

    return {
        "examples": examples,
        "benefits": ["数据标准化", "自动字段映射", "类型转换", "数据验证"],
    }
