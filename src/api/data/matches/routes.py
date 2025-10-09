"""
比赛数据路由
Match Data Routes
"""




logger = get_logger(__name__)

router = APIRouter()


@router.get("/", response_model=List[MatchInfo])
async def get_matches(
    league_id: Optional[int] = Query(None, description="联赛ID"),
    team_id: Optional[int] = Query(None, description="球队ID"),
    status: Optional[str] = Query(None, description="比赛状态"),
    start_date: Optional[datetime] = Query(None, description="开始日期"),
    end_date: Optional[datetime] = Query(None, description="结束日期"),
    limit: int = Query(50, description="返回数量限制", ge=1, le=1000),
    offset: int = Query(0, description="偏移量", ge=0),
    current_user: Dict = Depends(get_current_user),
):
    """
    获取比赛列表

    Args:
        league_id: 联赛ID
        team_id: 球队ID
        status: 比赛状态
        start_date: 开始日期
        end_date: 结束日期
        limit: 返回数量限制
        offset: 偏移量
        current_user: 当前用户

    Returns:
        List[MatchInfo]: 比赛列表
    """
    try:
        async with get_async_session() as session:
            # 构建查询
            query = select(Match).options(
                selectinload(Match.home_team),
                selectinload(Match.away_team),
                selectinload(Match.league),
            )

            # 应用过滤条件
            filters = []
            if league_id:
                filters.append(Match.league_id == league_id)
            if team_id:
                filters.append(
                    or_(
                        Match.home_team_id == team_id,
                        Match.away_team_id == team_id,
                    )
                )
            if status:
                try:
                    match_status = MatchStatus(status)
                    filters.append(Match.match_status == match_status)
                except ValueError:
                    raise HTTPException(
                        status_code=400, detail=f"无效的比赛状态: {status}"
                    )
            if start_date:
                filters.append(Match.match_time >= start_date)
            if end_date:
                filters.append(Match.match_time <= end_date)

            if filters:
                query = query.where(and_(*filters))

            # 排序和分页
            query = query.order_by(Match.match_time.desc()).offset(offset).limit(limit)

            result = await session.execute(query)
            matches = result.scalars().all()

            # 转换为响应模型
            return [_convert_match_to_info(match) for match in matches]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取比赛列表失败: {e}")
        raise HTTPException(status_code=500, detail="获取比赛列表失败")


@router.get("/{match_id}", response_model=MatchInfo)
async def get_match_details(
    match_id: int = Path(..., description="比赛ID", gt=0),
    current_user: Dict = Depends(get_current_user),
):
    """
    获取比赛详情

    Args:
        match_id: 比赛ID
        current_user: 当前用户

    Returns:
        MatchInfo: 比赛详情
    """
    try:
        async with get_async_session() as session:
            query = (
                select(Match)
                .options(
                    selectinload(Match.home_team),
                    selectinload(Match.away_team),
                    selectinload(Match.league),
                )
                .where(Match.id == match_id)
            )

            result = await session.execute(query)
            match = result.scalar_one_or_none()

            if not match:
                raise HTTPException(status_code=404, detail="比赛不存在")

            return _convert_match_to_info(match)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取比赛 {match_id} 详情失败: {e}")
        raise HTTPException(status_code=500, detail="获取比赛详情失败")


def _convert_match_to_info(match: Match) -> MatchInfo:
    """转换Match对象为MatchInfo"""
    return MatchInfo(
        id=match.id,
        home_team=TeamInfo(
            id=match.home_team.id,
            name=match.home_team.team_name,
            country=match.home_team.country,
            founded_year=match.home_team.founded_year,
            stadium=match.home_team.stadium,
            logo_url=match.home_team.logo_url,
            is_active=match.home_team.is_active, List, Optional



        ),
        away_team=TeamInfo(
            id=match.away_team.id,
            name=match.away_team.team_name,
            country=match.away_team.country,
            founded_year=match.away_team.founded_year,
            stadium=match.away_team.stadium,
            logo_url=match.away_team.logo_url,
            is_active=match.away_team.is_active,
        ),
        league=LeagueInfo(
            id=match.league.id,
            name=match.league.league_name,
            country=match.league.country,
            season=match.league.season,
            start_date=match.league.start_date,
            end_date=match.league.end_date,
            is_active=match.league.is_active,
        ),
        match_time=match.match_time,
        match_status=match.match_status.value,
        venue=match.venue,
        home_score=match.home_score,
        away_score=match.away_score,
        home_half_score=match.home_half_score,
        away_half_score=match.away_half_score,
    )