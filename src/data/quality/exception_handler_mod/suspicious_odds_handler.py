"""
可疑赔率处理模块

负责检测和处理可疑的赔率数据。
"""

import logging
from datetime import datetime
from typing import Any, Dict, List

from .exceptions import SuspiciousOddsException


class SuspiciousOddsHandler:
    """可疑赔率处理器"""

    def __init__(self, db_manager: Any, config: Dict[str, Any] = None):
        """
        初始化可疑赔率处理器

        Args:
            db_manager: 数据库管理器
            config: 配置参数
        """
        self.db_manager = db_manager
        self.logger = logging.getLogger(f"quality.{self.__class__.__name__}")

        # 默认配置
        self.config = config or {
            "min_odds": 1.01,
            "max_odds": 1000.0,
            "probability_range": [0.95, 1.20],
            "mark_suspicious": True,
        }

    async def handle_suspicious_odds(
        self, odds_records: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        处理可疑赔率

        Args:
            odds_records: 赔率记录列表

        Returns:
            Dict: 处理结果统计
        """
        try:
            suspicious_count = 0
            processed_records = []
            suspicious_details = []

            for record in odds_records:
                is_suspicious, reason = self._is_odds_suspicious(record)

                if is_suspicious:
                    # 标记为可疑赔率
                    record["suspicious_odds"] = True
                    suspicious_count += 1
                    suspicious_details.append({
                        "match_id": record.get("match_id"),
                        "bookmaker": record.get("bookmaker"),
                        "reason": reason,
                        "odds": {
                            "home": record.get("home_odds"),
                            "draw": record.get("draw_odds"),
                            "away": record.get("away_odds"),
                        }
                    })
                else:
                    record["suspicious_odds"] = False

                processed_records.append(record)

            # 记录可疑赔率日志
            if suspicious_details:
                await self._log_suspicious_odds(suspicious_details)

            result = {
                "total_processed": len(odds_records),
                "suspicious_count": suspicious_count,
                "suspicious_rate": suspicious_count / len(odds_records) if odds_records else 0,
                "processed_records": processed_records,
                "suspicious_details": suspicious_details,
                "timestamp": datetime.now().isoformat(),
            }

            self.logger.info(
                f"可疑赔率处理完成：{suspicious_count}/{len(odds_records)} "
                f"条记录被标记为可疑（比例：{result['suspicious_rate']:.2%}）"
            )
            return result

        except Exception as e:
            self.logger.error(f"处理可疑赔率失败: {str(e)}")
            raise SuspiciousOddsException(
                f"处理可疑赔率失败: {str(e)}",
                odds_data={"total_records": len(odds_records)}
            )

    def _is_odds_suspicious(self, odds_record: Dict[str, Any]) -> tuple[bool, str]:
        """
        判断赔率是否可疑

        Args:
            odds_record: 赔率记录

        Returns:
            tuple: (是否可疑, 可疑原因)
        """
        try:
            home_odds = odds_record.get("home_odds")
            draw_odds = odds_record.get("draw_odds")
            away_odds = odds_record.get("away_odds")

            # 检查赔率是否为空
            if any(odds is None for odds in [home_odds, draw_odds, away_odds]):
                return False, "missing_values"  # 缺失值不算可疑，由缺失值处理器处理

            # 检查赔率范围
            min_odds = self.config["min_odds"]
            max_odds = self.config["max_odds"]

            for odds_type, odds in [("home", home_odds), ("draw", draw_odds), ("away", away_odds)]:
                if odds < min_odds:
                    return True, f"{odds_type}_odds_too_low"
                if odds > max_odds:
                    return True, f"{odds_type}_odds_too_high"

            # 检查隐含概率总和
            try:
                total_probability = sum(
                    1 / odds for odds in [home_odds, draw_odds, away_odds]
                )
                prob_range = self.config["probability_range"]

                if total_probability < prob_range[0]:
                    return True, "probability_too_low"
                if total_probability > prob_range[1]:
                    return True, "probability_too_high"

            except (ZeroDivisionError, TypeError):
                return True, "invalid_probability_calculation"

            # 检查赔率分布合理性
            # 主队赔率应该低于客队赔率（如果是强队对弱队）
            # 这里可以添加更多业务规则

            return False, "normal"

        except Exception as e:
            self.logger.error(f"判断赔率可疑性失败: {str(e)}")
            return True, "analysis_error"  # 出错时保守处理，标记为可疑

    async def _log_suspicious_odds(self, suspicious_details: List[Dict[str, Any]]) -> None:
        """记录可疑赔率到日志"""
        try:
            from .quality_logger import QualityLogger

            logger = QualityLogger(self.db_manager)
            await logger.log_suspicious_odds(suspicious_details)

        except Exception as e:
            self.logger.error(f"记录可疑赔率日志失败: {str(e)}")

    async def analyze_suspicious_patterns(
        self, odds_records: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        分析可疑赔率模式

        Args:
            odds_records: 赔率记录列表

        Returns:
            Dict: 分析结果
        """
        try:
            analysis = {
                "total_records": len(odds_records),
                "suspicious_by_bookmaker": {},
                "suspicious_by_time": {},
                "common_reasons": {},
                "timestamp": datetime.now().isoformat(),
            }

            # 按博彩商分析
            bookmaker_stats = {}
            for record in odds_records:
                bookmaker = record.get("bookmaker", "unknown")
                if bookmaker not in bookmaker_stats:
                    bookmaker_stats[bookmaker] = {"total": 0, "suspicious": 0}
                bookmaker_stats[bookmaker]["total"] += 1
                if record.get("suspicious_odds", False):
                    bookmaker_stats[bookmaker]["suspicious"] += 1

            # 计算可疑率
            for bookmaker, stats in bookmaker_stats.items():
                suspicious_rate = stats["suspicious"] / stats["total"] if stats["total"] > 0 else 0
                analysis["suspicious_by_bookmaker"][bookmaker] = {
                    "total": stats["total"],
                    "suspicious": stats["suspicious"],
                    "suspicious_rate": suspicious_rate,
                }

            # 识别高风险博彩商
            high_risk_bookmakers = [
                bm for bm, data in analysis["suspicious_by_bookmaker"].items()
                if data["suspicious_rate"] > 0.1  # 可疑率超过10%
            ]
            analysis["high_risk_bookmakers"] = high_risk_bookmakers

            self.logger.info(
                f"可疑赔率模式分析完成，发现 {len(high_risk_bookmakers)} 个高风险博彩商"
            )
            return analysis

        except Exception as e:
            self.logger.error(f"分析可疑赔率模式失败: {str(e)}")
            raise SuspiciousOddsException(
                f"分析可疑赔率模式失败: {str(e)}",
                odds_data={"analysis_error": str(e)}
            )

    def update_config(self, new_config: Dict[str, Any]) -> None:
        """
        更新配置

        Args:
            new_config: 新的配置参数
        """
        self.config.update(new_config)
        self.logger.info(f"可疑赔率处理器配置已更新: {new_config}")

    def get_config_summary(self) -> Dict[str, Any]:
        """
        获取配置摘要

        Returns:
            Dict: 配置摘要
        """
        return {
            "min_odds": self.config["min_odds"],
            "max_odds": self.config["max_odds"],
            "probability_range": self.config["probability_range"],
            "mark_suspicious": self.config["mark_suspicious"],
        }