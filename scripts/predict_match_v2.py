#!/usr/bin/env python3
"""
⚽ 足球比赛预测CLI工具 v2.0 - 服务层解耦版本

基于服务层架构的预测工具，实现高内聚低耦合设计。
不再直接调用src模块，而是通过src.services提供的业务接口。

主要改进：
1. 服务层依赖：使用InferenceServiceV2而不是直接调用inference模块
2. 解耦设计：CLI逻辑与业务逻辑分离
3. 错误处理：统一的错误处理和降级策略
4. 配置管理：集中的配置管理
5. 可扩展性：易于添加新的服务功能

使用示例:
    python scripts/predict_match_v2.py --home "Arsenal" --away "Chelsea"
    python scripts/predict_match_v2.py --home "Manchester United" --away "Liverpool" --date "2024-01-15"
"""

import argparse
import asyncio
import sys
import os
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List
import json

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class PredictionConfig:
    """预测配置管理"""

    def __init__(self):
        # 从环境变量或默认值加载配置
        self.model_path = os.getenv(
            "MODEL_PATH", "models/football_prediction_model.pkl"
        )
        self.database_url = os.getenv(
            "DATABASE_URL", "postgresql://localhost:5432/football_prediction"
        )
        self.use_real_data = os.getenv("USE_REAL_DATA", "true").lower() == "true"
        self.cache_enabled = os.getenv("CACHE_ENABLED", "true").lower() == "true"
        self.log_level = os.getenv("LOG_LEVEL", "INFO").upper()

        # 业务配置
        self.confidence_threshold = 0.55
        self.max_retries = 3
        self.timeout_seconds = 30

    def load_from_file(self, config_file: Path) -> None:
        """从文件加载配置"""
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                config_data = json.load(f)
                for key, value in config_data.items():
                    if hasattr(self, key):
                        setattr(self, key, value)
            logger.info(f"配置已从文件加载: {config_file}")
        except Exception as e:
            logger.warning(f"配置文件加载失败，使用默认配置: {e}")


class PredictionDisplay:
    """预测结果展示器"""

    @staticmethod
    def format_confidence_bar(probability: float, width: int = 30) -> str:
        """格式化概率条形图"""
        filled_width = int(width * probability)
        empty_width = width - filled_width
        return "█" * filled_width + "░" * empty_width

    @staticmethod
    def display_prediction_result(result: Dict[str, Any]) -> None:
        """展示预测结果"""
        print("\n" + "=" * 60)
        print("⚽  足球比赛预测结果")
        print("=" * 60)

        # 比赛信息
        print("\n📅 比赛信息:")
        print(f"   主队: {result.get('home_team', 'Unknown')}")
        print(f"   客队: {result.get('away_team', 'Unknown')}")
        print(f"   日期: {result.get('match_date', 'Unknown')}")

        # 预测状态
        success = result.get("success", False)
        if not success:
            print(f"\n❌ 预测失败: {result.get('error', 'Unknown error')}")
            return

        # 预测概率
        prediction = result.get("prediction", {})
        if (
            "home_win_prob" in prediction
            and "draw_prob" in prediction
            and "away_win_prob" in prediction
        ):
            print("\n🎯 预测概率:")
            home_prob = prediction["home_win_prob"]
            draw_prob = prediction["draw_prob"]
            away_prob = prediction["away_win_prob"]

            print(
                f"主胜      : {home_prob:6.1%} |{PredictionDisplay.format_confidence_bar(home_prob)}|"
            )
            print(
                f"平局      : {draw_prob:6.1%} |{PredictionDisplay.format_confidence_bar(draw_prob)}|"
            )
            print(
                f"客胜      : {away_prob:6.1%} |{PredictionDisplay.format_confidence_bar(away_prob)}|"
            )

        # 投注建议
        predicted_outcome = prediction.get("predicted_outcome", "UNKNOWN")
        confidence = prediction.get("confidence", 0.0)

        print("\n💡 投注建议:")
        if confidence > 0.7:
            strength = "💰 强烈推荐"
            risk = "低风险"
        elif confidence > 0.6:
            strength = "📈 推荐"
            risk = "中等风险"
        elif confidence > 0.5:
            strength = "🤔 谨慎考虑"
            risk = "较高风险"
        else:
            strength = "⚠️ 不建议投注"
            risk = "高风险"

        print(f"   {strength}: {predicted_outcome} (置信度 {confidence:.1%})")
        print(f"   风险等级: {risk}")

        # 详细信息
        print("\n📊 预测详情:")
        print(f"   最终预测: {predicted_outcome}")
        print(f"   置信度: {confidence:.3f}")
        print(f"   处理时间: {result.get('processing_time_ms', 0):.1f}ms")
        print(f"   缓存命中: {'是' if result.get('cached', False) else '否'}")

        # 模型信息
        model_info = result.get("model_info", {})
        if model_info:
            print("\n🤖 模型信息:")
            print(f"   模型版本: {model_info.get('model_version', 'Unknown')}")
            print(f"   特征数量: {model_info.get('feature_count', 'Unknown')}")
            print(f"   模型状态: {model_info.get('status', 'Unknown')}")

        print("\n" + "=" * 60)


class MatchPredictorCLI:
    """足球比赛预测CLI工具 - 服务层版本"""

    def __init__(self, config: PredictionConfig):
        self.config = config
        self.inference_service = None
        self.simulation_mode = False

        # 设置日志级别
        logging.getLogger().setLevel(getattr(logging, config.log_level))

    async def initialize(self) -> bool:
        """初始化服务"""
        try:
            # 导入服务层
            from src.services.inference_service import InferenceService

            self.inference_service = InferenceService()

            # 初始化服务
            success = await self.inference_service.initialize()
            if not success:
                logger.warning("服务初始化失败，启用模拟模式")
                self.simulation_mode = True
                return True

            # 尝试加载模型
            if Path(self.config.model_path).exists():
                model_loaded = self.inference_service.load_model(
                    "football_model", self.config.model_path
                )
                if model_loaded:
                    logger.info(f"模型加载成功: {self.config.model_path}")
                else:
                    logger.warning("模型加载失败，使用降级模式")
            else:
                logger.info(f"模型文件不存在，使用降级模式: {self.config.model_path}")

            return True

        except Exception as e:
            logger.error("初始化失败: {e}")
            logger.exception("完整初始化错误堆栈:")  # 增加完整的traceback
            self.simulation_mode = True
            return True  # 继续运行，使用模拟模式

    async def predict_match(
        self,
        home_team: str,
        away_team: str,
        match_date: Optional[datetime] = None,
        match_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        预测比赛结果

        Args:
            home_team: 主队名称
            away_team: 客队名称
            match_date: 比赛日期
            match_id: 比赛ID（可选）

        Returns:
            Dict[str, Any]: 预测结果
        """
        if match_id is None:
            # 生成比赛ID
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            match_id = f"match_{timestamp}_{hash(home_team + away_team) % 10000}"

        if self.simulation_mode:
            return await self._simulate_prediction(
                match_id, home_team, away_team, match_date
            )

        try:
            # 使用服务层进行预测
            result = await self.inference_service.predict_match_simple(
                match_id=match_id,
                home_team=home_team,
                away_team=away_team,
                match_date=match_date,
            )

            return result

        except Exception as e:
            logger.error(f"预测失败: {e}")
            logger.exception("完整预测错误堆栈:")  # 增加完整的traceback
            return {
                "match_id": match_id,
                "home_team": home_team,
                "away_team": away_team,
                "match_date": match_date.isoformat() if match_date else None,
                "success": False,
                "error": str(e),
                "prediction": {},
                "processing_time_ms": 0,
                "cached": False,
            }

    async def _simulate_prediction(
        self,
        match_id: str,
        home_team: str,
        away_team: str,
        match_date: Optional[datetime],
    ) -> Dict[str, Any]:
        """模拟预测结果"""
        import random

        # 生成模拟概率
        probabilities = [
            random.uniform(0.1, 0.5),
            random.uniform(0.2, 0.4),
            random.uniform(0.2, 0.6),
        ]
        probabilities = [p / sum(probabilities) for p in probabilities]  # 归一化

        max_prob_idx = probabilities.index(max(probabilities))
        outcomes = ["AWAY_WIN", "DRAW", "HOME_WIN"]
        predicted_outcome = outcomes[max_prob_idx]

        result = {
            "match_id": match_id,
            "home_team": home_team,
            "away_team": away_team,
            "match_date": match_date.isoformat() if match_date else None,
            "success": True,
            "prediction": {
                "away_win_prob": probabilities[0],
                "draw_prob": probabilities[1],
                "home_win_prob": probabilities[2],
                "predicted_outcome": predicted_outcome,
                "predicted_class": max_prob_idx,
                "probabilities": probabilities,
                "confidence": max(probabilities),
                "model_version": "simulation-1.0",
                "prediction_time": datetime.now().isoformat(),
            },
            "processing_time_ms": random.uniform(50, 200),
            "cached": False,
            "model_info": {
                "status": "simulation",
                "model_version": "simulation-1.0",
                "feature_count": 12,
            },
        }

        return result

    async def batch_predict(
        self, matches: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """批量预测"""
        results = []

        if self.simulation_mode:
            for match in matches:
                result = await self._simulate_prediction(
                    match.get("match_id", f"match_{len(results)}"),
                    match["home_team"],
                    match["away_team"],
                    match.get("match_date"),
                )
                results.append(result)
        else:
            # 使用服务层批量预测
            from src.services.inference_service_v2 import PredictionRequest

            requests = []
            for match in matches:
                request = PredictionRequest(
                    match_id=match.get("match_id", f"match_{len(requests)}"),
                    home_team=match["home_team"],
                    away_team=match["away_team"],
                    match_date=match.get("match_date"),
                )
                requests.append(request)

            responses = await self.inference_service.batch_predict(requests)
            results = [response.to_dict() for response in responses]

        return results

    def get_service_stats(self) -> Dict[str, Any]:
        """获取服务统计信息"""
        if self.simulation_mode:
            return {
                "service_name": "MatchPredictorCLI",
                "mode": "simulation",
                "status": "running",
            }

        return self.inference_service.get_service_stats()

    async def shutdown(self) -> None:
        """关闭服务"""
        if self.inference_service:
            await self.inference_service.shutdown()


def create_arg_parser() -> argparse.ArgumentParser:
    """创建命令行参数解析器"""
    parser = argparse.ArgumentParser(
        description="足球比赛预测CLI工具 v2.0 - 服务层解耦版本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 基本预测
  python scripts/predict_match_v2.py --home "Arsenal" --away "Chelsea"

  # 指定日期预测
  python scripts/predict_match_v2.py --home "Manchester United" --away "Liverpool" --date "2024-01-15"

  # 使用自定义模型
  python scripts/predict_match_v2.py --home "Barcelona" --away "Real Madrid" --model-path "models/custom_model.pkl"

  # 详细模式
  python scripts/predict_match_v2.py --home "Bayern Munich" --away "Borussia Dortmund" --verbose

  # 查看服务状态
  python scripts/predict_match_v2.py --stats
        """,
    )

    parser.add_argument("--home", "-H", type=str, help="主队名称")

    parser.add_argument("--away", "-A", type=str, help="客队名称")

    parser.add_argument("--date", "-d", type=str, help="比赛日期 (YYYY-MM-DD)")

    parser.add_argument("--match-id", type=str, help="比赛ID (可选，会自动生成)")

    parser.add_argument(
        "--model-path",
        type=str,
        default="models/football_prediction_model.pkl",
        help="模型文件路径",
    )

    parser.add_argument("--config", type=str, help="配置文件路径")

    parser.add_argument("--verbose", "-v", action="store_true", help="详细输出模式")

    parser.add_argument("--stats", action="store_true", help="显示服务统计信息")

    parser.add_argument("--batch-file", type=str, help="批量预测文件路径 (JSON格式)")

    return parser


def parse_date(date_str: str) -> Optional[datetime]:
    """解析日期字符串"""
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        logger.error(f"日期格式错误: {date_str}，请使用 YYYY-MM-DD 格式")
        return None


def load_batch_matches(file_path: str) -> List[Dict[str, Any]]:
    """加载批量预测文件"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, list):
            return data
        elif isinstance(data, dict) and "matches" in data:
            return data["matches"]
        else:
            raise ValueError("无效的批量文件格式")

    except Exception as e:
        logger.error(f"批量文件加载失败: {e}")
        return []


async def main():
    """主函数"""
    parser = create_arg_parser()
    args = parser.parse_args()

    # 加载配置
    config = PredictionConfig()
    if args.config:
        config.load_from_file(Path(args.config))
    if args.model_path:
        config.model_path = args.model_path
    if args.verbose:
        config.log_level = "DEBUG"

    # 验证参数注入 - 增加调试信息
    logger.info(f"Container Mode Active: 参数验证开始")
    logger.info(f"解析到的参数: home={args.home}, away={args.away}, verbose={args.verbose}")
    logger.info(f"模型路径: {config.model_path}")
    logger.info(f"容器环境变量: MODEL_PATH={os.getenv('MODEL_PATH', 'NOT_SET')}")

    # 创建CLI实例
    cli = MatchPredictorCLI(config)

    try:
        # 初始化服务
        if not await cli.initialize():
            logger.error("服务初始化失败")
            return 1

        # 显示统计信息
        if args.stats:
            stats = cli.get_service_stats()
            print("\n📊 服务统计信息:")
            print(json.dumps(stats, indent=2, ensure_ascii=False))
            return 0

        # 批量预测
        if args.batch_file:
            matches = load_batch_matches(args.batch_file)
            if not matches:
                logger.error("批量文件为空或格式错误")
                return 1

            logger.info(f"开始批量预测 {len(matches)} 场比赛")
            results = await cli.batch_predict(matches)

            print(f"\n📈 批量预测完成 ({len(results)} 场比赛)")
            success_count = sum(1 for r in results if r.get("success", False))
            print(f"成功: {success_count}, 失败: {len(results) - success_count}")

            # 显示每个结果
            for i, result in enumerate(results, 1):
                print(f"\n--- 比赛 {i} ---")
                PredictionDisplay.display_prediction_result(result)

            return 0

        # 单场预测
        if not args.home or not args.away:
            parser.error("请提供主队和客队名称 (--home 和 --away)")

        # 解析日期
        match_date = None
        if args.date:
            match_date = parse_date(args.date)
            if match_date is None:
                return 1

        # 执行预测
        logger.info(f"开始预测比赛: {args.home} vs {args.away}")
        result = await cli.predict_match(
            home_team=args.home,
            away_team=args.away,
            match_date=match_date,
            match_id=args.match_id,
        )

        # 显示结果
        PredictionDisplay.display_prediction_result(result)

        # 返回状态码
        return 0 if result.get("success", False) else 1

    except KeyboardInterrupt:
        logger.info("用户中断操作")
        return 130
    except Exception as e:
        logger.error(f"程序异常: {e}")
        logger.exception("完整程序异常堆栈:")  # 增加完整的traceback
        return 1
    finally:
        # 清理资源
        await cli.shutdown()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
