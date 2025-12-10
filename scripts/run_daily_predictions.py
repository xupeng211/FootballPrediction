#!/usr/bin/env python3
"""
每日预测运行脚本
自动为即将进行的比赛生成预测结果

功能:
1. 获取未来3天内的预定比赛
2. 动态计算滚动特征
3. 调用推理API进行预测
4. 保存预测结果到数据库
5. 生成预测报告

作者: Full Stack Automation Engineer
创建时间: 2025-01-10
版本: 1.0.0 - Phase 4 Daily Automation
"""

import asyncio
import sys
import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import requests
from sqlalchemy import text

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.database.async_manager import get_db_session, initialize_database
from src.features.dynamic_rolling import get_features_for_upcoming_match
from src.inference.schemas import PredictionRequest
from src.core.config import get_settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DailyPredictionRunner:
    """每日预测运行器"""

    def __init__(self, inference_api_url: str = "http://app:8000"):
        self.inference_api_url = inference_api_url.rstrip('/')
        self.settings = get_settings()
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json"
        })

        # 预测统计
        self.stats = {
            'total_matches': 0,
            'successful_predictions': 0,
            'failed_predictions': 0,
            'skipped_matches': 0,
            'prediction_distribution': {"Home": 0, "Draw": 0, "Away": 0}
        }

    async def run_daily_predictions(self, days_ahead: int = 3) -> Dict[str, Any]:
        """
        运行每日预测流程

        Args:
            days_ahead: 预测未来几天的比赛

        Returns:
            预测结果统计
        """
        logger.info(f"🚀 开始运行每日预测 (未来 {days_ahead} 天)")

        try:
            # 1. 获取即将进行的比赛
            upcoming_matches = await self._get_upcoming_matches(days_ahead)
            self.stats['total_matches'] = len(upcoming_matches)

            logger.info(f"📋 找到 {len(upcoming_matches)} 场即将进行的比赛")

            if not upcoming_matches:
                logger.info("⚠️ 没有找到即将进行的比赛")
                return self._generate_report()

            # 2. 为每场比赛生成预测
            await self._process_matches_batch(upcoming_matches)

            # 3. 生成报告
            report = self._generate_report()

            logger.info("🎉 每日预测流程完成!")
            return report

        except Exception as e:
            logger.error(f"❌ 每日预测流程失败: {e}")
            self.stats['failed_predictions'] = self.stats['total_matches']
            return self._generate_report()

    async def _get_upcoming_matches(self, days_ahead: int) -> List[Dict[str, Any]]:
        """获取即将进行的比赛"""
        start_date = datetime.now()
        end_date = start_date + timedelta(days=days_ahead)

        sql = """
        SELECT
            m.id,
            m.home_team_id,
            m.away_team_id,
            m.home_team_name,
            m.away_team_name,
            m.match_date,
            m.league_id,
            m.status,
            -- 检查是否已有预测
            CASE WHEN p.id IS NOT NULL THEN true ELSE false END as has_prediction
        FROM matches m
        LEFT JOIN match_predictions p ON m.id = p.match_id
            AND p.model_version = :model_version
            AND p.created_at >= CURRENT_DATE
        WHERE m.match_date BETWEEN :start_date AND :end_date
            AND m.status = 'scheduled'
        ORDER BY m.match_date ASC;
        """

        async with get_db_session() as session:
            result = await session.execute(text(sql), {
                "start_date": start_date,
                "end_date": end_date,
                "model_version": "v1.0.0"
            })

            matches = []
            for row in result.fetchall():
                matches.append({
                    'match_id': row.id,
                    'home_team_id': row.home_team_id,
                    'away_team_id': row.away_team_id,
                    'home_team_name': row.home_team_name,
                    'away_team_name': row.away_team_name,
                    'match_date': row.match_date,
                    'league_id': row.league_id,
                    'league_name': None,  # 数据库中没有这个字段
                    'status': row.status,
                    'has_prediction': row.has_prediction
                })

            return matches

    async def _process_matches_batch(self, matches: List[Dict[str, Any]]):
        """批量处理比赛预测"""
        logger.info(f"🔄 开始处理 {len(matches)} 场比赛")

        async with get_db_session() as session:
            for i, match in enumerate(matches, 1):
                try:
                    logger.info(f"📊 处理第 {i}/{len(matches)} 场比赛: "
                               f"{match['home_team_name']} vs {match['away_team_name']}")

                    # 跳过已有预测的比赛
                    if match.get('has_prediction'):
                        logger.info(f"   ⏭️ 跳过 (已有今日预测)")
                        self.stats['skipped_matches'] += 1
                        continue

                    # 1. 计算动态特征
                    features = await get_features_for_upcoming_match(match['match_id'])
                    if not features.get('match_date'):
                        logger.warning(f"   ⚠️ 特征计算失败，跳过此比赛")
                        self.stats['failed_predictions'] += 1
                        continue

                    # 2. 调用推理API
                    prediction_result = await self._call_inference_api(match, features)
                    if not prediction_result:
                        self.stats['failed_predictions'] += 1
                        continue

                    # 3. 保存预测结果
                    await self._save_prediction(session, match, prediction_result)
                    self.stats['successful_predictions'] += 1

                    # 更新统计
                    prediction = prediction_result['prediction']
                    self.stats['prediction_distribution'][prediction] += 1

                    logger.info(f"   ✅ 预测成功: {prediction} "
                               f"(置信度: {prediction_result['confidence']:.3f})")

                except Exception as e:
                    logger.error(f"   ❌ 处理比赛失败: {e}")
                    self.stats['failed_predictions'] += 1

            # 提交所有预测
            await session.commit()

    async def _call_inference_api(
        self,
        match: Dict[str, Any],
        features: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """调用推理API进行预测"""
        try:
            # 构建预测请求
            prediction_request = {
                "match_id": int(match['match_id']) if isinstance(match['match_id'], (int, str)) else 12345,  # 确保是数字ID
                "home_team_name": match['home_team_name'],
                "away_team_name": match['away_team_name'],
                "match_date": features['match_date'],
                "home_score": 0,  # 即将进行的比赛，比分为0
                "away_score": 0,
                "home_xg": features.get('home_last_5_avg_xg_for', 0),
                "away_xg": features.get('away_last_5_avg_xg_for', 0),
                "home_total_shots": int(features.get('home_last_5_avg_goals_scored', 0) * 10),
                "away_total_shots": int(features.get('away_last_5_avg_goals_scored', 0) * 10),
                "home_shots_on_target": int(features.get('home_last_5_avg_goals_scored', 0) * 4),
                "away_shots_on_target": int(features.get('away_last_5_avg_goals_scored', 0) * 4),
                "league_id": match['league_id'],
                "league_name": match['league_name'],
                "stats_json": {
                    "feature_source": features['feature_source'],
                    "home_matches_used": features['home_team_matches_used'],
                    "away_matches_used": features['away_team_matches_used']
                }
            }

            # 调用API
            response = self.session.post(
                f"{self.inference_api_url}/api/v1/inference/predict",
                json=prediction_request,
                timeout=30
            )

            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"   ❌ API调用失败: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"   ❌ 调用推理API失败: {e}")
            return None

    async def _save_prediction(
        self,
        session,
        match: Dict[str, Any],
        prediction_result: Dict[str, Any]
    ):
        """保存预测结果到数据库"""
        sql = """
        INSERT INTO match_predictions (
            match_id, prediction, confidence, probabilities,
            model_version, feature_count, missing_features,
            processing_time_ms, prediction_source
        ) VALUES (
            :match_id, :prediction, :confidence, :probabilities,
            :model_version, :feature_count, :missing_features,
            :processing_time_ms, :prediction_source
        );
        """

        params = {
            "match_id": match['match_id'],
            "prediction": prediction_result['prediction'],
            "confidence": prediction_result['confidence'],
            "probabilities": json.dumps(prediction_result['probabilities']),
            "model_version": prediction_result.get('model_version', 'v1.0.0'),
            "feature_count": prediction_result.get('feature_count', 0),
            "missing_features": prediction_result.get('missing_features', 0),
            "processing_time_ms": prediction_result.get('processing_time_ms'),
            "prediction_source": "daily_automation"
        }

        await session.execute(text(sql), params)

    def _generate_report(self) -> Dict[str, Any]:
        """生成预测报告"""
        total_processed = self.stats['successful_predictions'] + self.stats['failed_predictions']
        success_rate = (self.stats['successful_predictions'] / total_processed * 100) if total_processed > 0 else 0

        report = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_matches_found": self.stats['total_matches'],
                "matches_processed": total_processed,
                "successful_predictions": self.stats['successful_predictions'],
                "failed_predictions": self.stats['failed_predictions'],
                "skipped_matches": self.stats['skipped_matches'],
                "success_rate": round(success_rate, 2)
            },
            "prediction_distribution": self.stats['prediction_distribution'],
            "model_version": "v1.0.0",
            "automation_source": "daily_runner"
        }

        return report

    def print_report(self, report: Dict[str, Any]):
        """打印预测报告"""
        print("\n" + "=" * 60)
        print("📊 每日预测报告")
        print("=" * 60)

        summary = report['summary']
        print(f"\n📈 预测统计:")
        print(f"   发现比赛总数: {summary['total_matches_found']}")
        print(f"   处理比赛数: {summary['matches_processed']}")
        print(f"   ✅ 成功预测: {summary['successful_predictions']}")
        print(f"   ❌ 失败预测: {summary['failed_predictions']}")
        print(f"   ⏭️ 跳过比赛: {summary['skipped_matches']}")
        print(f"   📊 成功率: {summary['success_rate']}%")

        dist = report['prediction_distribution']
        if sum(dist.values()) > 0:
            print(f"\n🎯 预测分布:")
            print(f"   主胜 (Home): {dist['Home']}")
            print(f"   平局 (Draw): {dist['Draw']}")
            print(f"   客胜 (Away): {dist['Away']}")

        print(f"\n🤖 模型信息:")
        print(f"   版本: {report['model_version']}")
        print(f"   自动化来源: {report['automation_source']}")
        print(f"   报告时间: {report['timestamp']}")

        print("=" * 60)


async def main():
    """主函数"""
    logger.info("🌅 启动每日预测自动化系统")

    try:
        # 0. 初始化数据库管理器
        logger.info("🔧 初始化数据库管理器...")
        initialize_database()

        # 1. 检查推理服务状态
        runner = DailyPredictionRunner()

        # 简单的健康检查
        try:
            response = requests.get(f"{runner.inference_api_url}/health", timeout=5)
            if response.status_code != 200:
                logger.error(f"❌ 推理服务不可用: {runner.inference_api_url}")
                return False
        except Exception as e:
            logger.error(f"❌ 无法连接到推理服务: {e}")
            return False

        logger.info("✅ 推理服务状态正常")

        # 运行预测流程
        report = await runner.run_daily_predictions(days_ahead=3)

        # 打印报告
        runner.print_report(report)

        # 返回成功状态
        success = report['summary']['success_rate'] >= 80  # 80%以上成功率算成功
        return success

    except KeyboardInterrupt:
        logger.info("⚠️ 用户中断操作")
        return False
    except Exception as e:
        logger.error(f"❌ 系统异常: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)