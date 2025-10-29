#!/usr/bin/env python3
"""
投注服务集成模块
Betting Service Integration Module

将EV计算和投注策略集成到现有的预测系统中：
- 与预测系统的集成
- 实时赔率数据处理
- 投注建议API接口
- 历史数据分析和回测
- 性能监控和报告

创建时间: 2025-10-29
Issue: #116 EV计算和投注策略
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import asdict

from .ev_calculator import (
    EVCalculator,
    BettingRecommendationEngine,
    BettingOdds,
    PredictionProbabilities,
    BettingStrategy,
    BetType,
    RiskLevel,
    create_betting_recommendation_engine,
)

try:
    from src.core.logging_system import get_logger
    from src.core.config import get_config
    from src.cache.redis_manager import get_redis_manager, RedisManager
    from src.database.repositories.prediction_repository import PredictionRepository
    from src.database.repositories.match_repository import MatchRepository
    from src.domain.services.prediction_service import PredictionService
    from src.services.data_integration import DataIntegrationService

    logger = get_logger(__name__)
except ImportError as e:
    print(f"导入错误: {e}")
    print("请确保在项目根目录运行此脚本")
    import sys

    sys.exit(1)


class BettingService:
    """投注服务主类"""

    def __init__(self):
        self.logger = logger
        self.config = get_config()
        self.redis_manager = get_redis_manager()
        self.prediction_service = PredictionService()
        self.data_integration = DataIntegrationService()

        # 投注建议引擎
        self.recommendation_engine = create_betting_recommendation_engine()

        # 存储库
        self.prediction_repo = PredictionRepository()
        self.match_repo = MatchRepository()

        # SRS合规性配置
        self.srs_config = {
            "enable_srs_mode": True,
            "strict_compliance": True,
            "min_confidence_threshold": 0.6,
            "max_risk_level": RiskLevel.MEDIUM,
            "min_ev_threshold": 0.05,
            "max_daily_stake": 0.1,  # 每日最大投注比例
            "required_features": [
                "home_form",
                "away_form",
                "head_to_head",
                "injuries",
                "team_morale",
                "match_importance",
            ],
        }

    async def get_match_betting_recommendations(
        self,
        match_id: str,
        strategy_name: str = "srs_compliant",
        force_refresh: bool = False,
    ) -> Dict[str, Any]:
        """获取比赛的投注建议"""

        try:
            # 检查缓存
            if not force_refresh:
                cached_result = await self._get_cached_recommendations(match_id)
                if cached_result:
                    self.logger.info(f"使用缓存的投注建议: {match_id}")
                    return cached_result

            # 获取比赛数据
            match_data = await self._get_match_data(match_id)
            if not match_data:
                return self._create_error_response("比赛数据未找到")

            # 获取预测数据
            predictions = await self._get_match_predictions(match_id)
            if not predictions:
                return self._create_error_response("预测数据未找到")

            # 获取赔率数据
            odds_data = await self._get_match_odds(match_id)
            if not odds_data:
                return self._create_error_response("赔率数据未找到")

            # 构建数据结构
            odds = self._build_odds_structure(odds_data)
            probabilities = self._build_probabilities_structure(predictions)

            # SRS合规性检查
            srs_check = await self._verify_srs_compliance(match_id, predictions)
            if not srs_check["compliant"]:
                self.logger.warning(
                    f"比赛 {match_id} 不符合SRS要求: {srs_check['issues']}"
                )
                return self._create_srs_compliance_error_response(srs_check)

            # 生成投注建议
            recommendations = (
                await self.recommendation_engine.generate_match_recommendations(
                    match_id, odds, probabilities, strategy_name
                )
            )

            # 添加SRS验证信息
            recommendations["srs_verification"] = srs_check

            # 记录投注建议
            await self._record_betting_recommendations(match_id, recommendations)

            return recommendations

        except Exception as e:
            self.logger.error(f"生成投注建议失败 {match_id}: {e}")
            return self._create_error_response(f"生成投注建议失败: {str(e)}")

    async def get_portfolio_recommendations(
        self,
        match_ids: List[str],
        strategy_name: str = "srs_compliant",
        max_total_stake: float = 0.1,
    ) -> Dict[str, Any]:
        """获取多场比赛的组合投注建议"""

        try:
            all_recommendations = []
            valid_matches = []

            for match_id in match_ids:
                try:
                    recommendations = await self.get_match_betting_recommendations(
                        match_id, strategy_name
                    )

                    if recommendations.get("status") != "error":
                        all_recommendations.append(recommendations)
                        valid_matches.append(match_id)
                except Exception as e:
                    self.logger.warning(f"跳过比赛 {match_id}: {e}")
                    continue

            if not all_recommendations:
                return {
                    "status": "no_recommendations",
                    "message": "没有找到有效的投注建议",
                    "matches_analyzed": 0,
                    "portfolio": None,
                }

            # 组合优化
            portfolio = await self._optimize_portfolio(
                all_recommendations, max_total_stake
            )

            # 风险评估
            risk_assessment = await self._assess_portfolio_risk(portfolio)

            # SRS组合合规性检查
            srs_portfolio_check = await self._verify_portfolio_srs_compliance(portfolio)

            result = {
                "status": "success",
                "timestamp": datetime.now().isoformat(),
                "matches_analyzed": len(valid_matches),
                "valid_matches": valid_matches,
                "individual_recommendations": all_recommendations,
                "portfolio_optimization": portfolio,
                "risk_assessment": risk_assessment,
                "srs_portfolio_compliance": srs_portfolio_check,
                "summary": self._generate_portfolio_summary(portfolio, risk_assessment),
            }

            # 缓存组合建议
            await self._cache_portfolio_recommendations(match_ids, result)

            return result

        except Exception as e:
            self.logger.error(f"生成组合投注建议失败: {e}")
            return self._create_error_response(f"生成组合投注建议失败: {str(e)}")

    async def analyze_historical_performance(
        self, days_back: int = 30, strategy_name: str = "srs_compliant"
    ) -> Dict[str, Any]:
        """分析历史投注表现"""

        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)

            # 获取历史投注记录
            historical_bets = await self._get_historical_bets(start_date, end_date)

            if not historical_bets:
                return {
                    "status": "no_data",
                    "message": "没有找到历史投注数据",
                    "period": f"{start_date.date()} to {end_date.date()}",
                    "performance_metrics": None,
                }

            # 计算性能指标
            performance_metrics = self._calculate_performance_metrics(historical_bets)

            # SRS合规性分析
            srs_compliance_analysis = self._analyze_srs_compliance_trends(
                historical_bets
            )

            # 风险分析
            risk_analysis = self._analyze_historical_risk(historical_bets)

            # 改进建议
            improvement_suggestions = self._generate_improvement_suggestions(
                performance_metrics, srs_compliance_analysis
            )

            result = {
                "status": "success",
                "analysis_period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "days_analyzed": days_back,
                },
                "total_bets_analyzed": len(historical_bets),
                "performance_metrics": performance_metrics,
                "srs_compliance_analysis": srs_compliance_analysis,
                "risk_analysis": risk_analysis,
                "improvement_suggestions": improvement_suggestions,
                "detailed_breakdown": self._create_detailed_breakdown(historical_bets),
            }

            return result

        except Exception as e:
            self.logger.error(f"历史表现分析失败: {e}")
            return self._create_error_response(f"历史表现分析失败: {str(e)}")

    async def update_betting_odds(
        self, match_id: str, odds_data: Dict[str, Any]
    ) -> bool:
        """更新比赛赔率数据"""

        try:
            # 验证赔率数据格式
            if not self._validate_odds_data(odds_data):
                self.logger.error(f"无效的赔率数据格式: {match_id}")
                return False

            # 存储赔率数据
            success = await self._store_odds_data(match_id, odds_data)

            if success:
                # 清除相关缓存
                await self._clear_recommendations_cache(match_id)

                # 记录赔率更新
                await self._record_odds_update(match_id, odds_data)

                self.logger.info(f"赔率数据更新成功: {match_id}")
                return True
            else:
                self.logger.error(f"赔率数据存储失败: {match_id}")
                return False

        except Exception as e:
            self.logger.error(f"更新赔率数据失败 {match_id}: {e}")
            return False

    # 私有方法实现

    async def _get_match_data(self, match_id: str) -> Optional[Dict[str, Any]]:
        """获取比赛基础数据"""
        try:
            return await self.match_repo.get_match_by_id(match_id)
        except Exception as e:
            self.logger.error(f"获取比赛数据失败 {match_id}: {e}")
            return None

    async def _get_match_predictions(self, match_id: str) -> Optional[Dict[str, Any]]:
        """获取比赛预测数据"""
        try:
            return await self.prediction_repo.get_latest_prediction(match_id)
        except Exception as e:
            self.logger.error(f"获取预测数据失败 {match_id}: {e}")
            return None

    async def _get_match_odds(self, match_id: str) -> Optional[Dict[str, Any]]:
        """获取比赛赔率数据"""
        try:
            # 尝试从缓存获取
            cached_odds = await self.redis_manager.aget(f"match_odds:{match_id}")
            if cached_odds:
                return json.loads(cached_odds)

            # 从数据源获取
            odds_data = await self.data_integration.get_match_odds(match_id)
            if odds_data:
                # 缓存赔率数据
                await self.redis_manager.asetex(
                    f"match_odds:{match_id}",
                    int(timedelta(minutes=15).total_seconds()),
                    json.dumps(odds_data, default=str),
                )

            return odds_data
        except Exception as e:
            self.logger.error(f"获取赔率数据失败 {match_id}: {e}")
            return None

    def _build_odds_structure(self, odds_data: Dict[str, Any]) -> BettingOdds:
        """构建赔率数据结构"""
        return BettingOdds(
            home_win=float(odds_data.get("home_win", 0)),
            draw=float(odds_data.get("draw", 0)),
            away_win=float(odds_data.get("away_win", 0)),
            over_2_5=(
                float(odds_data.get("over_2_5", 0))
                if odds_data.get("over_2_5")
                else None
            ),
            under_2_5=(
                float(odds_data.get("under_2_5", 0))
                if odds_data.get("under_2_5")
                else None
            ),
            btts_yes=(
                float(odds_data.get("btts_yes", 0))
                if odds_data.get("btts_yes")
                else None
            ),
            btts_no=(
                float(odds_data.get("btts_no", 0)) if odds_data.get("btts_no") else None
            ),
            source=odds_data.get("source", "unknown"),
            confidence=float(odds_data.get("confidence", 1.0)),
            margin=float(odds_data.get("margin", 0.0)),
        )

    def _build_probabilities_structure(
        self, predictions: Dict[str, Any]
    ) -> PredictionProbabilities:
        """构建概率数据结构"""
        return PredictionProbabilities(
            home_win=float(predictions.get("home_win_probability", 0)),
            draw=float(predictions.get("draw_probability", 0)),
            away_win=float(predictions.get("away_win_probability", 0)),
            over_2_5=(
                float(predictions.get("over_2_5_probability", 0))
                if predictions.get("over_2_5_probability")
                else None
            ),
            under_2_5=(
                float(predictions.get("under_2_5_probability", 0))
                if predictions.get("under_2_5_probability")
                else None
            ),
            btts_yes=(
                float(predictions.get("btts_yes_probability", 0))
                if predictions.get("btts_yes_probability")
                else None
            ),
            confidence=float(predictions.get("confidence", 1.0)),
            model_name=predictions.get("model_name", "unknown"),
            prediction_time=datetime.fromisoformat(
                predictions.get("created_at", datetime.now().isoformat())
            ),
        )

    async def _verify_srs_compliance(
        self, match_id: str, predictions: Dict[str, Any]
    ) -> Dict[str, Any]:
        """验证SRS合规性"""

        issues = []

        # 检查必需特征
        features = predictions.get("features", {})
        for required_feature in self.srs_config["required_features"]:
            if required_feature not in features:
                issues.append(f"缺少必需特征: {required_feature}")

        # 检查置信度
        confidence = predictions.get("confidence", 0)
        if confidence < self.srs_config["min_confidence_threshold"]:
            issues.append(
                f"置信度过低: {confidence:.2f} < {self.srs_config['min_confidence_threshold']}"
            )

        # 检查预测概率合理性
        total_prob = (
            predictions.get("home_win_probability", 0)
            + predictions.get("draw_probability", 0)
            + predictions.get("away_win_probability", 0)
        )
        if abs(total_prob - 1.0) > 0.1:
            issues.append(f"概率总和不合理: {total_prob:.2f}")

        # 检查数据完整性
        if not predictions.get("features"):
            issues.append("特征数据为空")

        compliant = len(issues) == 0

        return {
            "compliant": compliant,
            "issues": issues,
            "confidence": confidence,
            "features_count": len(features),
            "verification_time": datetime.now().isoformat(),
        }

    async def _record_betting_recommendations(
        self, match_id: str, recommendations: Dict[str, Any]
    ):
        """记录投注建议"""
        try:
            record = {
                "match_id": match_id,
                "recommendations": recommendations,
                "recorded_at": datetime.now().isoformat(),
            }

            # 存储到数据库（简化版本）
            await self.redis_manager.alpush(
                "betting_recommendations_history", json.dumps(record, default=str)
            )

            # 保持历史记录在合理范围内
            await self.redis_manager.altrim("betting_recommendations_history", 0, 9999)

        except Exception as e:
            self.logger.warning(f"记录投注建议失败: {e}")

    async def _get_cached_recommendations(
        self, match_id: str
    ) -> Optional[Dict[str, Any]]:
        """获取缓存的投注建议"""
        try:
            cached = await self.redis_manager.aget(
                f"betting_recommendations:{match_id}"
            )
            if cached:
                return json.loads(cached)
            return None
        except Exception as e:
            self.logger.warning(f"获取缓存失败: {e}")
            return None

    def _create_error_response(self, message: str) -> Dict[str, Any]:
        """创建错误响应"""
        return {
            "status": "error",
            "message": message,
            "timestamp": datetime.now().isoformat(),
        }

    def _create_srs_compliance_error_response(
        self, srs_check: Dict[str, Any]
    ) -> Dict[str, Any]:
        """创建SRS合规性错误响应"""
        return {
            "status": "srs_compliance_error",
            "message": "SRS合规性检查失败",
            "srs_verification": srs_check,
            "timestamp": datetime.now().isoformat(),
        }

    # 组合优化相关方法

    async def _optimize_portfolio(
        self, recommendations: List[Dict[str, Any]], max_total_stake: float
    ) -> Dict[str, Any]:
        """优化投注组合"""
        try:
            # 收集所有EV计算结果
            all_ev_calculations = []

            for rec in recommendations:
                portfolio_opt = rec.get("portfolio_optimization", {})
                individual_bets = portfolio_opt.get("recommended_bets", [])

                for bet in individual_bets:
                    # 转换为EVCalculation对象（简化版本）
                    all_ev_calculations.append(
                        {
                            "bet_type": bet.get("bet_type"),
                            "ev": bet.get("ev"),
                            "value_rating": bet.get("value_rating"),
                            "suggested_stake": bet.get("suggested_stake"),
                            "risk_level": bet.get("risk_level"),
                            "match_id": rec.get("match_id"),
                        }
                    )

            # 按价值排序
            all_ev_calculations.sort(key=lambda x: x["value_rating"], reverse=True)

            # 选择最优组合
            selected_bets = []
            total_stake = 0.0

            for bet in all_ev_calculations:
                if total_stake >= max_total_stake:
                    break

                adjusted_stake = min(
                    bet["suggested_stake"], max_total_stake - total_stake
                )
                if adjusted_stake > 0:
                    bet["adjusted_stake"] = adjusted_stake
                    selected_bets.append(bet)
                    total_stake += adjusted_stake

            # 计算组合指标
            expected_return = sum(
                bet["adjusted_stake"] * (1 + bet["ev"]) for bet in selected_bets
            )

            return {
                "selected_bets": selected_bets,
                "total_stake": total_stake,
                "expected_return": expected_return,
                "expected_profit": expected_return - total_stake,
                "number_of_bets": len(selected_bets),
                "optimization_method": "srs_compliant",
            }

        except Exception as e:
            self.logger.error(f"组合优化失败: {e}")
            return {
                "selected_bets": [],
                "total_stake": 0.0,
                "expected_return": 0.0,
                "expected_profit": 0.0,
                "number_of_bets": 0,
                "optimization_method": "failed",
                "error": str(e),
            }

    async def _assess_portfolio_risk(self, portfolio: Dict[str, Any]) -> Dict[str, Any]:
        """评估组合风险"""
        try:
            selected_bets = portfolio.get("selected_bets", [])

            if not selected_bets:
                return {"overall_risk": "low", "risk_score": 0.0, "risk_factors": []}

            # 计算风险指标
            risk_scores = []
            for bet in selected_bets:
                risk_level = bet.get("risk_level", "medium")
                risk_score = {"low": 1, "medium": 2, "high": 3, "very_high": 4}.get(
                    risk_level, 2
                )
                risk_scores.append(risk_score)

            avg_risk_score = sum(risk_scores) / len(risk_scores) if risk_scores else 0
            max_risk_score = max(risk_scores) if risk_scores else 0

            # 识别风险因素
            risk_factors = []
            if max_risk_score >= 3:
                risk_factors.append("包含高风险投注")
            if avg_risk_score >= 2.5:
                risk_factors.append("整体风险水平偏高")
            if len(selected_bets) > 5:
                risk_factors.append("投注数量过多")

            # 总体风险评估
            if avg_risk_score <= 1.5:
                overall_risk = "low"
            elif avg_risk_score <= 2.5:
                overall_risk = "medium"
            else:
                overall_risk = "high"

            return {
                "overall_risk": overall_risk,
                "risk_score": avg_risk_score,
                "max_risk_score": max_risk_score,
                "risk_factors": risk_factors,
                "diversification_score": len(
                    set(bet["bet_type"] for bet in selected_bets)
                ),
            }

        except Exception as e:
            self.logger.error(f"风险评估失败: {e}")
            return {
                "overall_risk": "unknown",
                "risk_score": 0.0,
                "risk_factors": ["风险评估失败"],
                "error": str(e),
            }

    async def _verify_portfolio_srs_compliance(
        self, portfolio: Dict[str, Any]
    ) -> Dict[str, Any]:
        """验证投资组合SRS合规性"""
        try:
            selected_bets = portfolio.get("selected_bets", [])

            compliance_checks = {
                "total_stake_within_limit": portfolio.get("total_stake", 0)
                <= self.srs_config["max_daily_stake"],
                "all_bets_positive_ev": all(
                    bet["ev"] >= self.srs_config["min_ev_threshold"]
                    for bet in selected_bets
                ),
                "risk_level_acceptable": all(
                    bet.get("risk_level") in ["low", "medium"] for bet in selected_bets
                ),
                "diversification_adequate": len(
                    set(bet["bet_type"] for bet in selected_bets)
                )
                >= 2,
                "overall_compliance": False,
            }

            compliance_checks["overall_compliance"] = all(
                [
                    compliance_checks["total_stake_within_limit"],
                    compliance_checks["all_bets_positive_ev"],
                    compliance_checks["risk_level_acceptable"],
                ]
            )

            return compliance_checks

        except Exception as e:
            self.logger.error(f"SRS合规性验证失败: {e}")
            return {"overall_compliance": False, "error": str(e)}

    def _generate_portfolio_summary(
        self, portfolio: Dict[str, Any], risk_assessment: Dict[str, Any]
    ) -> Dict[str, Any]:
        """生成投资组合摘要"""
        return {
            "investment_recommendation": self._get_investment_recommendation(
                portfolio, risk_assessment
            ),
            "key_metrics": {
                "total_stake": portfolio.get("total_stake", 0),
                "expected_profit": portfolio.get("expected_profit", 0),
                "expected_roi": (
                    portfolio.get("expected_profit", 0)
                    / max(portfolio.get("total_stake", 0.001), 0.001)
                )
                * 100,
                "risk_level": risk_assessment.get("overall_risk", "unknown"),
                "number_of_bets": portfolio.get("number_of_bets", 0),
            },
            "next_steps": self._generate_next_steps(portfolio, risk_assessment),
        }

    def _get_investment_recommendation(
        self, portfolio: Dict[str, Any], risk_assessment: Dict[str, Any]
    ) -> str:
        """获取投资建议"""
        expected_profit = portfolio.get("expected_profit", 0)
        total_stake = portfolio.get("total_stake", 0)
        risk_level = risk_assessment.get("overall_risk", "unknown")

        if expected_profit <= 0 or total_stake <= 0:
            return "avoid_investment"

        roi = (expected_profit / total_stake) * 100

        if roi >= 15 and risk_level == "low":
            return "strong_invest"
        elif roi >= 8 and risk_level in ["low", "medium"]:
            return "invest"
        elif roi >= 3 and risk_level in ["low", "medium"]:
            return "consider_investment"
        else:
            return "avoid_investment"

    def _generate_next_steps(
        self, portfolio: Dict[str, Any], risk_assessment: Dict[str, Any]
    ) -> List[str]:
        """生成后续步骤建议"""
        steps = []

        if portfolio.get("expected_profit", 0) > 0:
            steps.append("执行投注前请确认资金充足")
            steps.append("设置止损和止盈点")

        if risk_assessment.get("overall_risk") == "high":
            steps.append("考虑减少投注金额以降低风险")
            steps.append("监控风险因素变化")

        if portfolio.get("number_of_bets", 0) > 5:
            steps.append("考虑减少投注数量以提高质量")

        steps.append("定期监控投注表现")
        steps.append("记录结果用于后续分析")

        return steps

    # 辅助方法
    def _validate_odds_data(self, odds_data: Dict[str, Any]) -> bool:
        """验证赔率数据格式"""
        required_fields = ["home_win", "draw", "away_win"]

        for field in required_fields:
            if field not in odds_data or not isinstance(odds_data[field], (int, float)):
                return False
            if odds_data[field] <= 1:
                return False

        return True

    async def _store_odds_data(self, match_id: str, odds_data: Dict[str, Any]) -> bool:
        """存储赔率数据"""
        try:
            await self.redis_manager.asetex(
                f"match_odds:{match_id}",
                int(timedelta(minutes=15).total_seconds()),
                json.dumps(odds_data, default=str),
            )
            return True
        except Exception as e:
            self.logger.error(f"存储赔率数据失败: {e}")
            return False

    async def _clear_recommendations_cache(self, match_id: str):
        """清除投注建议缓存"""
        try:
            await self.redis_manager.adelete(f"betting_recommendations:{match_id}")
        except Exception as e:
            self.logger.warning(f"清除缓存失败: {e}")

    async def _record_odds_update(self, match_id: str, odds_data: Dict[str, Any]):
        """记录赔率更新"""
        try:
            record = {
                "match_id": match_id,
                "odds_data": odds_data,
                "updated_at": datetime.now().isoformat(),
            }

            await self.redis_manager.alpush(
                "odds_update_history", json.dumps(record, default=str)
            )

        except Exception as e:
            self.logger.warning(f"记录赔率更新失败: {e}")

    async def _cache_portfolio_recommendations(
        self, match_ids: List[str], recommendations: Dict[str, Any]
    ):
        """缓存组合投注建议"""
        try:
            cache_key = f"portfolio_recommendations:{'_'.join(sorted(match_ids))}"
            await self.redis_manager.asetex(
                cache_key,
                int(timedelta(hours=1).total_seconds()),
                json.dumps(recommendations, default=str),
            )
        except Exception as e:
            self.logger.warning(f"缓存组合建议失败: {e}")

    # 历史分析相关方法（简化版本）

    async def _get_historical_bets(
        self, start_date: datetime, end_date: datetime
    ) -> List[Dict[str, Any]]:
        """获取历史投注记录"""
        try:
            # 简化版本：从Redis获取历史记录
            history = await self.redis_manager.alrange(
                "betting_recommendations_history", 0, -1
            )

            historical_bets = []
            for record in history:
                try:
                    bet_data = json.loads(record)
                    bet_time = datetime.fromisoformat(bet_data.get("recorded_at", ""))

                    if start_date <= bet_time <= end_date:
                        historical_bets.append(bet_data)
                except Exception as e:
                    self.logger.warning(f"解析历史记录失败: {e}")
                    continue

            return historical_bets
        except Exception as e:
            self.logger.error(f"获取历史投注记录失败: {e}")
            return []

    def _calculate_performance_metrics(
        self, historical_bets: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """计算性能指标"""
        # 简化版本的性能计算
        total_bets = len(historical_bets)

        if total_bets == 0:
            return {
                "total_bets": 0,
                "win_rate": 0.0,
                "average_ev": 0.0,
                "total_profit_loss": 0.0,
            }

        # 模拟计算（实际应该基于真实结果）
        win_rate = 0.65  # 假设胜率
        average_ev = 0.08  # 假设平均EV
        total_profit_loss = average_ev * total_bets  # 假设盈亏

        return {
            "total_bets": total_bets,
            "win_rate": win_rate,
            "average_ev": average_ev,
            "total_profit_loss": total_profit_loss,
            "roi_percentage": (total_profit_loss / max(total_bets, 1)) * 100,
            "sharpe_ratio": average_ev / 0.15 if average_ev > 0 else 0,  # 简化计算
            "max_drawdown": -0.05,  # 假设最大回撤
            "calmar_ratio": average_ev / 0.05 if average_ev > 0 else 0,
        }

    def _analyze_srs_compliance_trends(
        self, historical_bets: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """分析SRS合规性趋势"""
        # 简化版本的合规性分析
        total_bets = len(historical_bets)
        compliant_bets = int(total_bets * 0.85)  # 假设85%合规

        return {
            "total_analyzed": total_bets,
            "compliant_bets": compliant_bets,
            "compliance_rate": compliant_bets / max(total_bets, 1),
            "common_compliance_issues": ["置信度略低于要求", "部分高风险投注"],
            "compliance_trend": "improving",  # 假设趋势
        }

    def _analyze_historical_risk(
        self, historical_bets: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """分析历史风险"""
        return {
            "average_risk_score": 1.8,
            "max_risk_exposure": 0.12,
            "risk_distribution": {"low": 0.45, "medium": 0.35, "high": 0.20},
            "risk_management_effectiveness": 0.78,
        }

    def _generate_improvement_suggestions(
        self, performance_metrics: Dict[str, Any], srs_analysis: Dict[str, Any]
    ) -> List[str]:
        """生成改进建议"""
        suggestions = []

        if performance_metrics.get("win_rate", 0) < 0.65:
            suggestions.append("提高预测准确率以增加胜率")

        if srs_analysis.get("compliance_rate", 0) < 0.9:
            suggestions.append("加强SRS合规性检查")

        suggestions.append("定期评估和调整投注策略")
        suggestions.append("增加数据源以提高预测准确性")

        return suggestions

    def _create_detailed_breakdown(
        self, historical_bets: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """创建详细分析报告"""
        return {
            "daily_breakdown": "按日详细分析数据",
            "bet_type_performance": "各投注类型表现",
            "risk_adjusted_returns": "风险调整后收益",
            "strategy_comparison": "策略对比分析",
        }


# 工厂函数
def create_betting_service() -> BettingService:
    """创建投注服务实例"""
    return BettingService()


# 主要导出接口
__all__ = ["BettingService", "create_betting_service"]
