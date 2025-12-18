#!/usr/bin/env python3
"""
影子实战测试守护进程
48小时连续运行，每15分钟执行一次预测闭环

功能：
1. 数据热身 (首次运行)
2. 15分钟间隔的FotMob数据抓取
3. AI预测和Kelly公式计算
4. 影子模式结果存储
5. 性能监控和健康检查
"""

import asyncio
import logging
import signal
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from src.config_unified import get_settings
from src.services.core_inference import CoreInferenceService
from src.strategy.kelly_criterion import KellyCriterionStrategy
from src.utils.intelligent_logging import get_logger

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ShadowTestDaemon:
    """影子测试守护进程"""

    def __init__(self):
        self.settings = get_settings()
        self.logger = get_logger(__name__)
        self.running = True
        self.start_time = datetime.now()

        # 核心服务初始化
        self.inference_service: Optional[CoreInferenceService] = None
        self.kelly_strategy: Optional[KellyCriterionStrategy] = None

        # 统计信息
        self.stats = {
            "total_predictions": 0,
            "successful_predictions": 0,
            "failed_predictions": 0,
            "kelly_recommendations": 0,
            "data_collection_errors": 0,
            "uptime_hours": 0,
            "last_prediction": None
        }

        # 注册信号处理器
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """信号处理器"""
        self.logger.info(f"收到信号 {signum}，准备优雅关闭...")
        self.running = False

    async def initialize(self) -> bool:
        """初始化守护进程"""
        try:
            self.logger.info("🚀 初始化影子测试守护进程...")

            # 验证环境配置
            if not self.settings.environment.value == "shadow_test":
                self.logger.error("环境配置错误，必须是shadow_test模式")
                return False

            # 初始化推理服务
            from src.ml.inference.model_loader import ModelLoader
            model_loader = ModelLoader()

            # 这里应该加载实际训练的模型
            # 暂时使用模拟模型进行测试
            self.inference_service = CoreInferenceService(
                model_service=model_loader,  # 临时使用ModelLoader作为model_service
                cache_service=None
            )

            await self.inference_service.initialize()
            self.logger.info("✅ 推理服务初始化完成")

            # 初始化Kelly策略
            self.kelly_strategy = KellyCriterionStrategy()
            self.logger.info("✅ Kelly策略初始化完成")

            return True

        except Exception as e:
            self.logger.error(f"❌ 初始化失败: {e}")
            return False

    async def warmup_data(self) -> bool:
        """数据热身 - 获取最近7天的比赛数据"""
        try:
            self.logger.info("🔥 开始数据热身 - 获取最近7天比赛数据...")

            # 这里应该调用数据收集服务
            # 暂时模拟数据热身过程
            warmup_days = getattr(self.settings, 'shadow_warmup_days', 7)
            self.logger.info(f"  📊 热身天数: {warmup_days}")

            # 模拟数据收集过程
            for day in range(warmup_days):
                date = datetime.now() - timedelta(days=day)
                self.logger.info(f"  📅 收集 {date.strftime('%Y-%m-%d')} 的数据...")
                await asyncio.sleep(0.1)  # 模拟处理时间

            self.logger.info("✅ 数据热身完成")
            return True

        except Exception as e:
            self.logger.error(f"❌ 数据热身失败: {e}")
            return False

    async def collect_fotmob_data(self) -> Dict[str, Any]:
        """收集FotMob数据"""
        try:
            self.logger.info("📡 收集FotMob实时数据...")

            # 这里应该调用实际的FotMob API
            # 暂时返回模拟数据
            mock_data = {
                "timestamp": datetime.now().isoformat(),
                "matches": [
                    {
                        "match_id": f"match_{int(time.time())}",
                        "home_team": "Manchester United",
                        "away_team": "Arsenal",
                        "league_id": 39,
                        "odds": {
                            "home_win": 2.1,
                            "draw": 3.4,
                            "away_win": 3.8
                        }
                    }
                ]
            }

            self.logger.info(f"  📊 收集到 {len(mock_data['matches'])} 场比赛数据")
            return mock_data

        except Exception as e:
            self.logger.error(f"❌ FotMob数据收集失败: {e}")
            self.stats["data_collection_errors"] += 1
            return {}

    async def run_prediction_cycle(self) -> Dict[str, Any]:
        """执行一次完整的预测闭环"""
        try:
            cycle_start = time.time()
            self.logger.info("🎯 执行预测闭环...")

            # 1. 收集数据
            fotmob_data = await self.collect_fotmob_data()
            if not fotmob_data.get("matches"):
                return {"success": False, "error": "无比赛数据"}

            # 2. 执行AI预测
            predictions = []
            kelly_recommendations = []

            for match in fotmob_data["matches"]:
                try:
                    # AI预测
                    from src.services.core_inference import PredictionRequest
                    request = PredictionRequest(
                        match_id=match["match_id"],
                        home_team=match["home_team"],
                        away_team=match["away_team"],
                        include_metadata=True
                    )

                    prediction_response = await self.inference_service.predict_single_match(request)

                    if prediction_response.success:
                        predictions.append({
                            "match_id": match["match_id"],
                            "prediction": prediction_response.prediction,
                            "probabilities": prediction_response.probabilities,
                            "confidence": prediction_response.confidence
                        })

                        # 3. Kelly公式计算
                        if prediction_response.confidence >= self.settings.default_confidence_threshold:
                            odds = match["odds"]
                            kelly_result = self.kelly_strategy.calculate_kelly_fraction(
                                prediction_response.probabilities,
                                odds
                            )

                            kelly_recommendations.append({
                                "match_id": match["match_id"],
                                "kelly_fraction": kelly_result["kelly_fraction"],
                                "recommended_stake": kelly_result["recommended_stake"],
                                "expected_value": kelly_result["expected_value"],
                                "home_team": match["home_team"],
                                "away_team": match["away_team"]
                            })

                    self.stats["successful_predictions"] += 1

                except Exception as e:
                    self.logger.error(f"  ❌ 比赛 {match['match_id']} 预测失败: {e}")
                    self.stats["failed_predictions"] += 1

            # 4. 存储结果 (影子模式)
            await self.store_shadow_results(predictions, kelly_recommendations)

            cycle_time = time.time() - cycle_start
            self.stats["total_predictions"] += len(predictions)
            self.stats["kelly_recommendations"] += len(kelly_recommendations)
            self.stats["last_prediction"] = datetime.now().isoformat()

            result = {
                "success": True,
                "cycle_time_seconds": cycle_time,
                "predictions_count": len(predictions),
                "kelly_recommendations_count": len(kelly_recommendations),
                "timestamp": datetime.now().isoformat()
            }

            self.logger.info(f"✅ 预测闭环完成 - 耗时 {cycle_time:.2f}s, "
                           f"预测 {len(predictions)} 场, Kelly建议 {len(kelly_recommendations)} 个")

            return result

        except Exception as e:
            self.logger.error(f"❌ 预测闭环失败: {e}")
            self.stats["failed_predictions"] += 1
            return {"success": False, "error": str(e)}

    async def store_shadow_results(self, predictions: list, kelly_recommendations: list):
        """存储影子模式结果"""
        try:
            # 这里应该存储到realtime_predictions表
            # 暂时只记录日志
            self.logger.info(f"💾 存储影子模式结果 - 预测: {len(predictions)}, Kelly: {len(kelly_recommendations)}")

            # 模拟数据库存储
            for pred in predictions:
                self.logger.debug(f"  📊 预测: {pred['match_id']} -> {pred['prediction']} "
                                f"(置信度: {pred['confidence']:.2f})")

            for kelly in kelly_recommendations:
                self.logger.debug(f"  💰 Kelly: {kelly['match_id']} -> "
                                f"{kelly['kelly_fraction']:.3f} ({kelly['recommended_stake']:.2f})")

        except Exception as e:
            self.logger.error(f"❌ 存储影子结果失败: {e}")

    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        uptime = (datetime.now() - self.start_time).total_seconds()
        self.stats["uptime_hours"] = uptime / 3600

        return {
            "status": "healthy" if self.running else "shutdown",
            "uptime_seconds": uptime,
            "uptime_hours": self.stats["uptime_hours"],
            "stats": self.stats,
            "services": {
                "inference_service": self.inference_service.is_initialized if self.inference_service else False,
                "kelly_strategy": self.kelly_strategy is not None
            },
            "timestamp": datetime.now().isoformat()
        }

    async def run(self):
        """主运行循环"""
        try:
            self.logger.info("🚀 启动影子测试守护进程...")

            # 初始化
            if not await self.initialize():
                return False

            # 数据热身
            if not await self.warmup_data():
                self.logger.warning("⚠️ 数据热身失败，但继续运行...")

            # 主循环
            prediction_interval = getattr(self.settings, 'shadow_prediction_interval_minutes', 15)
            test_duration = getattr(self.settings, 'shadow_test_duration_hours', 48)

            self.logger.info(f"⏰ 预测间隔: {prediction_interval} 分钟")
            self.logger.info(f"⏰ 测试持续时间: {test_duration} 小时")

            last_prediction_time = time.time()

            while self.running:
                current_time = time.time()

                # 检查是否需要执行预测
                if current_time - last_prediction_time >= prediction_interval * 60:
                    await self.run_prediction_cycle()
                    last_prediction_time = current_time

                # 检查测试时间
                if (current_time - self.start_time.timestamp()) >= test_duration * 3600:
                    self.logger.info("🏁 影子测试时间结束")
                    break

                # 短暂休眠
                await asyncio.sleep(5)

                # 定期健康检查日志
                if int(current_time) % 300 == 0:  # 每5分钟
                    health = await self.health_check()
                    self.logger.info(f"❤️ 健康检查 - 运行时间: {health['uptime_hours']:.1f}h, "
                                   f"总预测: {health['stats']['total_predictions']}, "
                                   f"成功率: {health['stats']['successful_predictions']}/{health['stats']['total_predictions']}")

            self.logger.info("🎉 影子测试守护进程正常结束")
            return True

        except Exception as e:
            self.logger.error(f"❌ 守护进程运行失败: {e}")
            return False

    async def shutdown(self):
        """优雅关闭"""
        self.logger.info("🛑 开始优雅关闭...")

        try:
            if self.inference_service:
                await self.inference_service.shutdown()

            # 打印最终统计
            final_stats = await self.health_check()
            self.logger.info(f"📊 最终统计: {final_stats['stats']}")

        except Exception as e:
            self.logger.error(f"❌ 关闭过程中出现错误: {e}")

async def main():
    """主函数"""
    daemon = ShadowTestDaemon()

    try:
        success = await daemon.run()
        return 0 if success else 1
    except KeyboardInterrupt:
        logger.info("收到中断信号，正在关闭...")
    finally:
        await daemon.shutdown()

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)