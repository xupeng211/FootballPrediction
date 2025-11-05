"""
适配器API路由
"""

router = APIRouter(prefix="/adapters", tags=["adapters"])

@router.get("/info")
async def get_adapter_info() -> Dict[str, Any]:
    """获取适配器信息"""
    return {
        "endpoints": {
            "football_matches": "/football/matches",
            "football_teams": "/football/teams",
            "football_team_players": "/football/teams/{team_id}/players",
            "demo_comparison": "/demo/comparison",
            "demo_fallback": "/demo/fallback",
            "demo_transformation": "/demo/transformation",
            "health": "/health",
        },
        "features": [
            "多数据源适配",
            "智能缓存",
            "错误恢复",
            "性能监控"
        ],
        "version": "1.0.0"
    }

@router.get("/health")
async def adapter_health() -> Dict[str, str]:
    """适配器健康检查"""
    return {"status": "healthy", "service": "adapters"}