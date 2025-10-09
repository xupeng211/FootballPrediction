"""
联赛数据路由
League Data Routes
"""




logger = get_logger(__name__)

router = APIRouter()


@router.get("/", response_model=List[LeagueInfo])
async def get_leagues(
    country: Optional[str] = Query(None, description="国家"),
    season: Optional[str] = Query(None, description="赛季"),
    is_active: Optional[bool] = Query(None, description="是否活跃"),
    limit: int = Query(50, description="返回数量限制", ge=1, le=1000),
    offset: int = Query(0, description="偏移量", ge=0),
    current_user: Dict = Depends(get_current_user),
):
    """
    获取联赛列表

    Args:
        country: 国家
        season: 赛季
        is_active: 是否活跃
        limit: 返回数量限制
        offset: 偏移量
        current_user: 当前用户

    Returns:
        List[LeagueInfo]: 联赛列表
    """
    try:
        async with get_async_session() as session:
            query = select(League)

            # 应用过滤条件
            filters = []
            if country:
                filters.append(League.country.ilike(f"%{country}%"))
            if season:
                filters.append(League.season == season)
            if is_active is not None:
                filters.append(League.is_active == is_active)

            if filters:
                query = query.where(and_(*filters))

            # 排序和分页
            query = query.order_by(League.league_name).offset(offset).limit(limit)

            result = await session.execute(query)
            leagues = result.scalars().all()

            # 转换为响应模型
            return [_convert_league_to_info(league) for league in leagues]

    except Exception as e:
        logger.error(f"获取联赛列表失败: {e}")
        raise HTTPException(status_code=500, detail="获取联赛列表失败")


def _convert_league_to_info(league: League) -> LeagueInfo:
    """转换League对象为LeagueInfo"""
    return LeagueInfo(
        id=league.id,
        name=league.league_name,
        country=league.country,
        season=league.season,
        start_date=league.start_date,
        end_date=league.end_date,
        is_active=league.is_active, List, Optional



    )