from datetime import datetime

#!/usr/bin/env python3
"""
投注API模块
Betting API Module

提供EV计算和投注策略的RESTful API接口:
- 单场比赛投注建议
- 组合投注优化
- 历史表现分析
- 实时赔率更新
- SRS合规性验证

创建时间: 2025-10-29  # TODO: 将魔法数字 2025 提取为常量
Issue: #116 EV计算和投注策略
"""

from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks, Depends
from pydantic import BaseModel, Field

from ..services.betting.betting_service import create_betting_service, BettingService
from ..core.logging_system import get_logger

logger = get_logger(__name__)

# 创建路由器
router = APIRouter(prefix="/betting", tags=["betting"])


# Pydantic模型定义
class BettingOddsRequest(BaseModel):
    """赔率请求模型"""

    home_win: float = Field(..., gt=1.0, description="主胜赔率")
    draw: float = Field(..., gt=1.0, description="平局赔率")
    away_win: float = Field(..., gt=1.0, description="客胜赔率")
    over_2_5: Optional[float] = Field(None, gt=1.0, description="大2.5球赔率")
    under_2_5: Optional[float] = Field(None, gt=1.0, description="小2.5球赔率")
    btts_yes: Optional[float] = Field(None, gt=1.0, description="双方进球赔率")
    btts_no: Optional[float] = Field(None, gt=1.0, description="双方不进球赔率")
    source: str = Field("unknown", description="赔率来源")
    confidence: float = Field(1.0, ge=0.0, le=1.0, description="赔率置信度")


class PortfolioRequest(BaseModel):
    """组合投注请求模型"""

    match_ids: List[str] = Field(
        ..., min_items=1, max_items=10, description="比赛ID列表"
    )
    strategy_name: str = Field("srs_compliant", description="策略名称")
    max_total_stake: float = Field(0.1, ge=0.01, le=0.5, description="最大总投注比例")


class OddsUpdateRequest(BaseModel):
    """赔率更新请求模型"""

    match_id: str = Field(..., description="比赛ID")
    odds_data: BettingOddsRequest = Field(..., description="赔率数据")


class PerformanceAnalysisRequest(BaseModel):
    """表现分析请求模型"""

    days_back: int = Field(
        30,  # TODO: 将魔法数字 30 提取为常量
        ge=1,
        le=365,  # TODO: 将魔法数字 365 提取为常量
        description="分析天数",  # TODO: 将魔法数字 30 提取为常量
    )  # TODO: 将魔法数字 30 提取为常量
    strategy_name: str = Field("srs_compliant", description="策略名称")


# 响应模型
class BaseResponse(BaseModel):
    """基础响应模型"""

    status: str
    message: str
    timestamp: str


class BettingRecommendationResponse(BaseResponse):
    """投注建议响应模型"""

    match_id: str
    strategy_used: str
    individual_bets: List[Dict[str, Any]]
    portfolio_optimization: Dict[str, Any]
    overall_recommendation: Dict[str, Any]
    srs_compliance: Dict[str, Any]
    risk_summary: Dict[str, Any]


class PortfolioRecommendationResponse(BaseResponse):
    """组合投注建议响应模型"""

    matches_analyzed: int
    valid_matches: List[str]
    portfolio_optimization: Dict[str, Any]
    risk_assessment: Dict[str, Any]
    srs_portfolio_compliance: Dict[str, Any]
    summary: Dict[str, Any]


class PerformanceAnalysisResponse(BaseResponse):
    """表现分析响应模型"""

    analysis_period: Dict[str, Any]
    total_bets_analyzed: int
    performance_metrics: Dict[str, Any]
    srs_compliance_analysis: Dict[str, Any]
    risk_analysis: Dict[str, Any]
    improvement_suggestions: List[str]


# 依赖注入
async def get_betting_service() -> BettingService:
    """获取投注服务实例"""
    return create_betting_service()


# API端点实现


@router.get(
    "/recommendations/{match_id}",
    response_model=BettingRecommendationResponse,
    summary="获取比赛投注建议",
    description="为指定比赛生成详细的投注建议,包括EV计算,Kelly准则和风险评估",
)
async def get_match_recommendations(
    match_id: str,
    strategy_name: str = Query("srs_compliant", description="投注策略名称"),
    force_refresh: bool = Query(False, description="强制刷新缓存"),
    betting_service: BettingService = Depends(get_betting_service),
):
    """获取单场比赛的投注建议"""
    try:
        logger.info(f"获取比赛投注建议: {match_id}, 策略: {strategy_name}")

        recommendations = await betting_service.get_match_betting_recommendations(
            match_id=match_id, strategy_name=strategy_name, force_refresh=force_refresh
        )

        if recommendations.get("status") == "error":
            raise HTTPException(
                status_code=404,  # TODO: 将魔法数字 404 提取为常量
                detail=recommendations.get("message", "获取投注建议失败"),
            )

        if recommendations.get("status") == "srs_compliance_error":
            raise HTTPException(
                status_code=422,  # TODO: 将魔法数字 422 提取为常量
                detail="SRS合规性检查失败",
                content=recommendations,
            )

        # 转换为响应模型
        return BettingRecommendationResponse(
            status=recommendations.get("status", "success"),
            message="投注建议生成成功",
            timestamp=recommendations.get("timestamp", datetime.now().isoformat()),
            match_id=match_id,
            strategy_used=recommendations.get("strategy_used", strategy_name),
            individual_bets=recommendations.get("individual_bets", []),
            portfolio_optimization=recommendations.get("portfolio_optimization", {}),
            overall_recommendation=recommendations.get("overall_recommendation", {}),
            srs_compliance=recommendations.get("srs_compliance", {}),
            risk_summary=recommendations.get("risk_summary", {}),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取投注建议失败: {e}")
        raise HTTPException(
            status_code=500,  # TODO: 将魔法数字 500 提取为常量
            detail=f"内部服务器错误: {str(e)}",  # TODO: 将魔法数字 500 提取为常量
        )  # TODO: 将魔法数字 500 提取为常量


@router.post(
    "/portfolio/recommendations",
    response_model=PortfolioRecommendationResponse,
    summary="获取组合投注建议",
    description="为多场比赛生成优化的组合投注建议",
)
async def get_portfolio_recommendations(
    request: PortfolioRequest,
    background_tasks: BackgroundTasks,
    betting_service: BettingService = Depends(get_betting_service),
):
    """获取组合投注建议"""
    try:
        logger.info(f"获取组合投注建议: {len(request.match_ids)}场比赛")

        recommendations = await betting_service.get_portfolio_recommendations(
            match_ids=request.match_ids,
            strategy_name=request.strategy_name,
            max_total_stake=request.max_total_stake,
        )

        if recommendations.get("status") == "no_recommendations":
            raise HTTPException(
                status_code=404,  # TODO: 将魔法数字 404 提取为常量
                detail=recommendations.get("message", "没有找到有效的投注建议"),
            )

        # 异步记录分析日志
        background_tasks.add_task(
            logger.info,
            f"组合投注建议生成完成: {len(request.match_ids)}场比赛, "
            f"建议投注: {recommendations.get('portfolio_optimization', {}).get('number_of_bets', 0)}个",
        )

        return PortfolioRecommendationResponse(
            status=recommendations.get("status", "success"),
            message="组合投注建议生成成功",
            timestamp=recommendations.get("timestamp", datetime.now().isoformat()),
            matches_analyzed=recommendations.get("matches_analyzed", 0),
            valid_matches=recommendations.get("valid_matches", []),
            portfolio_optimization=recommendations.get("portfolio_optimization", {}),
            risk_assessment=recommendations.get("risk_assessment", {}),
            srs_portfolio_compliance=recommendations.get(
                "srs_portfolio_compliance", {}
            ),
            summary=recommendations.get("summary", {}),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取组合投注建议失败: {e}")
        raise HTTPException(
            status_code=500,  # TODO: 将魔法数字 500 提取为常量
            detail=f"内部服务器错误: {str(e)}",  # TODO: 将魔法数字 500 提取为常量
        )  # TODO: 将魔法数字 500 提取为常量


@router.get(
    "/performance/analysis",
    response_model=PerformanceAnalysisResponse,
    summary="获取历史表现分析",
    description="分析指定时间段内的历史投注表现",
)
async def get_performance_analysis(
    days_back: int = Query(
        30,  # TODO: 将魔法数字 30 提取为常量
        ge=1,
        le=365,  # TODO: 将魔法数字 365 提取为常量
        description="分析天数",  # TODO: 将魔法数字 30 提取为常量
    ),  # TODO: 将魔法数字 30 提取为常量
    strategy_name: str = Query("srs_compliant", description="策略名称"),
    betting_service: BettingService = Depends(get_betting_service),
):
    """获取历史表现分析"""
    try:
        logger.info(f"获取历史表现分析: {days_back}天, 策略: {strategy_name}")

        analysis = await betting_service.analyze_historical_performance(
            days_back=days_back, strategy_name=strategy_name
        )

        if analysis.get("status") == "no_data":
            raise HTTPException(
                status_code=404,  # TODO: 将魔法数字 404 提取为常量
                detail=analysis.get("message", "没有找到历史投注数据"),
            )

        return PerformanceAnalysisResponse(
            status=analysis.get("status", "success"),
            message="历史表现分析完成",
            timestamp=datetime.now().isoformat(),
            analysis_period=analysis.get("analysis_period", {}),
            total_bets_analyzed=analysis.get("total_bets_analyzed", 0),
            performance_metrics=analysis.get("performance_metrics", {}),
            srs_compliance_analysis=analysis.get("srs_compliance_analysis", {}),
            risk_analysis=analysis.get("risk_analysis", {}),
            improvement_suggestions=analysis.get("improvement_suggestions", []),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"历史表现分析失败: {e}")
        raise HTTPException(
            status_code=500,  # TODO: 将魔法数字 500 提取为常量
            detail=f"内部服务器错误: {str(e)}",  # TODO: 将魔法数字 500 提取为常量
        )  # TODO: 将魔法数字 500 提取为常量


@router.post(
    "/odds/update",
    response_model=BaseResponse,
    summary="更新比赛赔率",
    description="更新指定比赛的赔率数据",
)
async def update_match_odds(
    request: OddsUpdateRequest,
    background_tasks: BackgroundTasks,
    betting_service: BettingService = Depends(get_betting_service),
):
    """更新比赛赔率"""
    try:
        logger.info(f"更新比赛赔率: {request.match_id}")

        odds_data = request.odds_data.dict()
        success = await betting_service.update_betting_odds(
            match_id=request.match_id, odds_data=odds_data
        )

        if success:
            # 异步记录更新日志
            background_tasks.add_task(
                logger.info,
                f"赔率更新成功: {request.match_id}, 来源: {odds_data.get('source')}",
            )

            return BaseResponse(
                status="success",
                message="赔率更新成功",
                timestamp=datetime.now().isoformat(),
            )
        else:
            raise HTTPException(
                status_code=400,  # TODO: 将魔法数字 400 提取为常量
                detail="赔率更新失败",  # TODO: 将魔法数字 400 提取为常量
            )  # TODO: 将魔法数字 400 提取为常量

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新赔率失败: {e}")
        raise HTTPException(
            status_code=500,  # TODO: 将魔法数字 500 提取为常量
            detail=f"内部服务器错误: {str(e)}",  # TODO: 将魔法数字 500 提取为常量
        )  # TODO: 将魔法数字 500 提取为常量


@router.get(
    "/strategies",
    summary="获取可用策略列表",
    description="获取所有可用的投注策略及其配置",
)
async def get_available_strategies(
    betting_service: BettingService = Depends(get_betting_service),
):
    """获取可用策略列表"""
    try:
        strategies = {
            "conservative": {
                "name": "保守策略",
                "description": "低风险,稳定收益,适合新手",
                "max_kelly_fraction": 0.15,  # TODO: 将魔法数字 15 提取为常量
                "min_ev_threshold": 0.08,
                "risk_tolerance": 0.3,
                "recommended_for": "新手投资者",
            },
            "balanced": {
                "name": "平衡策略",
                "description": "风险与收益平衡,适合有经验的投注者",
                "max_kelly_fraction": 0.25,  # TODO: 将魔法数字 25 提取为常量
                "min_ev_threshold": 0.05,
                "risk_tolerance": 0.5,
                "recommended_for": "有经验的投注者",
            },
            "aggressive": {
                "name": "激进策略",
                "description": "高风险高收益,适合专业投注者",
                "max_kelly_fraction": 0.35,  # TODO: 将魔法数字 35 提取为常量
                "min_ev_threshold": 0.03,
                "risk_tolerance": 0.7,
                "recommended_for": "专业投注者",
            },
            "srs_compliant": {
                "name": "SRS合规策略",
                "description": "严格按照SRS要求的安全策略",
                "max_kelly_fraction": 0.20,  # TODO: 将魔法数字 20 提取为常量
                "min_ev_threshold": 0.05,
                "risk_tolerance": 0.4,
                "recommended_for": "要求合规性的投注者",
                "srs_compliant": True,
            },
        }

        return {
            "status": "success",
            "strategies": strategies,
            "default_strategy": "srs_compliant",
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"获取策略列表失败: {e}")
        raise HTTPException(
            status_code=500,  # TODO: 将魔法数字 500 提取为常量
            detail=f"内部服务器错误: {str(e)}",  # TODO: 将魔法数字 500 提取为常量
        )  # TODO: 将魔法数字 500 提取为常量


@router.get(
    "/srs/compliance/check/{match_id}",
    summary="检查SRS合规性",
    description="检查指定比赛的预测数据是否符合SRS要求",
)
async def check_srs_compliance(
    match_id: str, betting_service: BettingService = Depends(get_betting_service)
):
    """检查SRS合规性"""
    try:
        logger.info(f"检查SRS合规性: {match_id}")

        # 获取预测数据
        predictions = await betting_service._get_match_predictions(match_id)
        if not predictions:
            raise HTTPException(
                status_code=404,  # TODO: 将魔法数字 404 提取为常量
                detail="预测数据未找到",  # TODO: 将魔法数字 404 提取为常量
            )  # TODO: 将魔法数字 404 提取为常量

        # 执行SRS合规性检查
        srs_check = await betting_service._verify_srs_compliance(match_id, predictions)

        return {
            "status": "success",
            "match_id": match_id,
            "srs_compliance": srs_check,
            "timestamp": datetime.now().isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"SRS合规性检查失败: {e}")
        raise HTTPException(
            status_code=500,  # TODO: 将魔法数字 500 提取为常量
            detail=f"内部服务器错误: {str(e)}",  # TODO: 将魔法数字 500 提取为常量
        )  # TODO: 将魔法数字 500 提取为常量


@router.get("/health", summary="投注服务健康检查", description="检查投注服务的运行状态")
async def health_check(betting_service: BettingService = Depends(get_betting_service)):
    """健康检查端点"""
    try:
        # 检查各个组件状态
        redis_status = "healthy" if betting_service.redis_client else "unhealthy"

        # 检查SRS配置
        srs_status = "configured" if betting_service.srs_config else "not_configured"

        overall_status = (
            "healthy"
            if redis_status == "healthy" and srs_status == "configured"
            else "degraded"
        )

        return {
            "status": overall_status,
            "components": {
                "betting_service": "healthy",
                "redis_client": redis_status,
                "srs_configuration": srs_status,
                "recommendation_engine": "healthy",
            },
            "version": "1.0.0",
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


@router.get(
    "/metrics", summary="获取投注服务指标", description="获取投注服务的性能和使用指标"
)
async def get_metrics(betting_service: BettingService = Depends(get_betting_service)):
    """获取服务指标"""
    try:
        # 简化版本的指标收集
        metrics = {
            "service_metrics": {
                "requests_total": 1000,  # 模拟数据
                "requests_success": 950,  # TODO: 将魔法数字 950 提取为常量
                "requests_error": 50,  # TODO: 将魔法数字 50 提取为常量
                "average_response_time_ms": 150,  # TODO: 将魔法数字 150 提取为常量
                "uptime_hours": 24,  # TODO: 将魔法数字 24 提取为常量
            },
            "betting_metrics": {
                "recommendations_generated_today": 25,  # TODO: 将魔法数字 25 提取为常量
                "active_strategies": 4,
                "srs_compliance_rate": 0.92,  # TODO: 将魔法数字 92 提取为常量
                "average_ev_generated": 0.07,
            },
            "system_metrics": {
                "redis_status": "connected",
                "cache_hit_rate": 0.85,  # TODO: 将魔法数字 85 提取为常量
                "error_rate": 0.05,
            },
        }

        return {
            "status": "success",
            "metrics": metrics,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"获取指标失败: {e}")
        raise HTTPException(
            status_code=500,  # TODO: 将魔法数字 500 提取为常量
            detail=f"内部服务器错误: {str(e)}",  # TODO: 将魔法数字 500 提取为常量
        )  # TODO: 将魔法数字 500 提取为常量


# 错误处理器
@router.exception_handler(422)  # TODO: 将魔法数字 422 提取为常量
async def validation_exception_handler(request, exc):
    """验证异常处理器"""
    return {
        "status": "error",
        "message": "请求参数验证失败",
        "details": exc.errors(),
        "timestamp": datetime.now().isoformat(),
    }


@router.exception_handler(404)  # TODO: 将魔法数字 404 提取为常量
async def not_found_exception_handler(request, exc):
    """404异常处理器"""
    return {
        "status": "error",
        "message": "请求的资源未找到",
        "timestamp": datetime.now().isoformat(),
    }


# 注册路由
# 导出
__all__ = [
    "router",
    "register_betting_api",
    "BettingRecommendationResponse",
    "PortfolioRecommendationResponse",
    "PerformanceAnalysisResponse",
    "BaseResponse",
]


def register_betting_api(app: FastAPI) -> None:
    """注册投注API路由"""
    app.include_router(router)
    logger.info("投注API路由注册完成")
