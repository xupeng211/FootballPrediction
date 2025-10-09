"""
"""







    """


    """







    """转换Odds对象为OddsInfo"""



赔率数据路由
Odds Data Routes
logger = get_logger(__name__)
router = APIRouter()
@router.get("/matches/{match_id}", response_model=List[OddsInfo])
async def get_match_odds(
    match_id: int = Path(..., description="比赛ID", gt=0),
    bookmaker: Optional[str] = Query(None, description="博彩公司"),
    market_type: Optional[str] = Query(None, description="市场类型"),
    limit: int = Query(50, description="返回数量限制", ge=1, le=1000),
    current_user: Dict = Depends(get_current_user),
):
    获取比赛赔率
    Args:
        match_id: 比赛ID
        bookmaker: 博彩公司
        market_type: 市场类型
        limit: 返回数量限制
        current_user: 当前用户
    Returns:
        List[OddsInfo]: 赔率列表
    try:
        async with get_async_session() as session:
            query = select(Odds).where(Odds.match_id == match_id)
            # 应用过滤条件
            if bookmaker:
                query = query.where(Odds.bookmaker.ilike(f"%{bookmaker}%"))
            if market_type:
                query = query.where(Odds.market_type == market_type)
            # 排序和分页
            query = query.order_by(Odds.created_at.desc()).limit(limit)
            result = await session.execute(query)
            odds_list = result.scalars().all()
            # 转换为响应模型
            return [_convert_odds_to_info(odds) for odds in odds_list]
    except Exception as e:
        logger.error(f"获取比赛 {match_id} 赔率失败: {e}")
        raise HTTPException(status_code=500, detail="获取赔率失败")
def _convert_odds_to_info(odds: Odds) -> OddsInfo:
    return OddsInfo(
        match_id=odds.match_id,
        bookmaker=odds.bookmaker,
        market_type=odds.market_type.value,
        home_win_odds=odds.home_win_odds,
        draw_odds=odds.draw_odds,
        away_win_odds=odds.away_win_odds,
        over_line=odds.over_line, List, Optional
        over_odds=odds.over_odds,
        under_odds=odds.under_odds,
        created_at=odds.created_at,
    )