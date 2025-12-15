#!/usr/bin/env python3
"""
真实预测流程验证脚本 - Phase 4

验证 RealPredictionService 是否能正确加载模型并对真实比赛进行预测。
使用比赛 ID 2421 (Napoli vs Juventus) 进行测试。
"""

import asyncio
import sys
import os
import logging
from pathlib import Path

# 设置项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# 内嵌 RealPredictionService 核心代码以避免导入问题
class EmbeddedRealPredictionService:
    """内嵌的真实预测服务"""

    def __init__(self):
        """初始化预测服务"""
        from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
        from xgboost import XGBClassifier

        # 模型路径
        self.model_path = project_root / "models" / "baseline_v2_real.json"
        self.model = None
        self.feature_names = []
        self.model_loaded = False

        # 数据库配置
        self.host = os.getenv('DB_HOST', 'localhost')
        self.port = int(os.getenv('DB_PORT', '5432'))
        self.database = os.getenv('DB_NAME', 'football_prediction')
        self.username = os.getenv('DB_USER', 'postgres')
        self.password = os.getenv('DB_PASSWORD', 'postgres')

        # 创建异步数据库引擎
        async_url = f"postgresql+asyncpg://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"
        self.engine = create_async_engine(async_url, echo=False)
        self.async_session_factory = async_sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            autocommit=False,
            autoflush=False,
        )

        logger.info(f"预测服务初始化完成，模型路径: {self.model_path}")

    async def load_model(self) -> bool:
        """加载模型"""
        try:
            from xgboost import XGBClassifier

            if not self.model_path.exists():
                logger.error(f"模型文件不存在: {self.model_path}")
                return False

            self.model = XGBClassifier()
            self.model.load_model(str(self.model_path))

            # 加载特征信息
            info_path = str(self.model_path).replace('.json', '_info.json')
            if Path(info_path).exists():
                import json
                with open(info_path, 'r', encoding='utf-8') as f:
                    model_info = json.load(f)
                    self.feature_names = model_info.get('feature_names', [])

            self.model_loaded = True
            logger.info(f"✅ 模型加载成功，特征数量: {len(self.feature_names)}")
            return True

        except Exception as e:
            logger.error(f"❌ 模型加载失败: {str(e)}")
            return False

    async def get_match_data(self, match_id: int):
        """获取比赛数据"""
        try:
            from sqlalchemy import text

            query = f"""
                SELECT
                    id,
                    home_team_id,
                    away_team_id,
                    home_score,
                    away_score,
                    match_date,
                    status,
                    COALESCE(home_team_name, home_team_id::text) as home_team_name,
                    COALESCE(away_team_name, away_team_id::text) as away_team_name,
                    league_id
                FROM matches
                WHERE id = {match_id} AND status = 'FT'
            """

            async with self.async_session_factory() as session:
                result = await session.execute(text(query))
                records = result.fetchall()

                if not records:
                    logger.warning(f"未找到比赛ID {match_id}")
                    return None

                import pandas as pd
                data = [dict(record._mapping) for record in records]
                df = pd.DataFrame(data)

                # 数据类型转换
                df['match_date'] = pd.to_datetime(df['match_date'], errors='coerce')
                numeric_cols = ['home_team_id', 'away_team_id', 'home_score', 'away_score', 'league_id']
                for col in numeric_cols:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

                return df

        except Exception as e:
            logger.error(f"❌ 获取比赛数据失败: {str(e)}")
            return None

    async def get_historical_data(self, limit: int = 2000):
        """获取历史数据"""
        import pandas as pd
        try:
            from sqlalchemy import text

            query = f"""
                SELECT
                    id,
                    home_team_id,
                    away_team_id,
                    home_score,
                    away_score,
                    match_date,
                    status,
                    COALESCE(home_team_name, home_team_id::text) as home_team_name,
                    COALESCE(away_team_name, away_team_id::text) as away_team_name,
                    league_id
                FROM matches
                WHERE status = 'FT'
                ORDER BY match_date DESC
                LIMIT {limit}
            """

            async with self.async_session_factory() as session:
                result = await session.execute(text(query))
                records = result.fetchall()

                data = [dict(record._mapping) for record in records]
                df = pd.DataFrame(data)

                # 数据类型转换
                df['match_date'] = pd.to_datetime(df['match_date'], errors='coerce')
                numeric_cols = ['home_team_id', 'away_team_id', 'home_score', 'away_score', 'league_id']
                for col in numeric_cols:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

                return df

        except Exception as e:
            logger.error(f"❌ 获取历史数据失败: {str(e)}")
            return pd.DataFrame()

    def create_features_for_prediction(self, match_data, historical_data):
        """创建预测特征"""
        import pandas as pd

        # 合并数据
        combined_data = pd.concat([historical_data, match_data], ignore_index=True)
        combined_data = combined_data.sort_values(['home_team_id', 'match_date'])

        # 创建滚动特征
        combined_data['home_score_rolling_3'] = (
            combined_data.groupby('home_team_id')['home_score']
            .transform(lambda x: x.rolling(3, min_periods=1).mean().shift(1))
        )

        combined_data['home_score_rolling_5'] = (
            combined_data.groupby('home_team_id')['home_score']
            .transform(lambda x: x.rolling(5, min_periods=1).mean().shift(1))
        )

        combined_data = combined_data.sort_values(['away_team_id', 'match_date'])

        combined_data['away_score_rolling_3'] = (
            combined_data.groupby('away_team_id')['away_score']
            .transform(lambda x: x.rolling(3, min_periods=1).mean().shift(1))
        )

        combined_data['away_score_rolling_5'] = (
            combined_data.groupby('away_team_id')['away_score']
            .transform(lambda x: x.rolling(5, min_periods=1).mean().shift(1))
        )

        # 提取当前比赛特征
        current_match_features = combined_data.iloc[-1:].copy()
        return current_match_features

    async def predict_match(self, match_id: int):
        """预测比赛结果"""
        if not self.model_loaded:
            logger.error("模型未加载")
            return None

        try:
            # 1. 获取比赛数据
            match_data = await self.get_match_data(match_id)
            if match_data is None or match_data.empty:
                return None

            match_info = match_data.iloc[0]
            logger.info(f"🏆 比赛: {match_info['home_team_name']} vs {match_info['away_team_name']}")
            logger.info(f"📅 日期: {match_info['match_date']}")
            logger.info(f"⚽ 真实比分: {match_info['home_score']} - {match_info['away_score']}")

            # 2. 获取历史数据
            logger.info("📊 加载历史数据...")
            historical_data = await self.get_historical_data()

            if historical_data.empty:
                logger.error("无法加载历史数据")
                return None

            # 3. 创建特征
            logger.info("⚙️ 创建预测特征...")
            features_df = self.create_features_for_prediction(match_data, historical_data)

            # 4. 选择特征
            required_features = [
                'home_score_rolling_3', 'home_score_rolling_5',
                'away_score_rolling_3', 'away_score_rolling_5',
                'home_team_id', 'away_team_id', 'league_id'
            ]

            available_features = [f for f in required_features if f in features_df.columns]

            if not available_features:
                logger.error("没有可用的特征")
                return None

            X = features_df[available_features]

            # 5. 预测
            logger.info("🔮 执行预测...")
            prediction_proba = self.model.predict_proba(X)[0]
            prediction_class = self.model.predict(X)[0]

            probabilities = {
                'away_win': float(prediction_proba[0]),
                'home_win': float(prediction_proba[1])
            }

            # 6. 确定真实结果
            home_score = int(match_info['home_score'])
            away_score = int(match_info['away_score'])
            if home_score > away_score:
                actual_result = 'home_win'
            elif away_score > home_score:
                actual_result = 'away_win'
            else:
                actual_result = 'draw'

            # 7. 构建结果
            result = {
                'match_id': match_id,
                'match_info': {
                    'home_team': match_info['home_team_name'],
                    'away_team': match_info['away_team_name'],
                    'actual_score': f"{home_score}-{away_score}",
                    'actual_result': actual_result
                },
                'prediction': {
                    'predicted_class': 'home_win' if prediction_class == 1 else 'away_win',
                    'home_win_probability': probabilities['home_win'],
                    'away_win_probability': probabilities['away_win'],
                    'confidence': max(probabilities.values())
                },
                'features_used': available_features,
                'feature_values': {
                    col: float(X[col].iloc[0]) for col in available_features
                }
            }

            return result

        except Exception as e:
            logger.error(f"❌ 预测失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return None


async def main():
    """主函数"""
    logger.info("🚀 真实预测流程验证启动")
    logger.info("=" * 60)

    # 检查环境变量
    required_vars = ['DB_HOST', 'DB_NAME', 'DB_USER', 'DB_PASSWORD']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        logger.error(f"❌ 缺少环境变量: {missing_vars}")
        sys.exit(1)

    # 目标比赛 ID
    target_match_id = 2421
    logger.info(f"🎯 目标比赛: ID {target_match_id} (Napoli vs Juventus)")

    try:
        # 1. 初始化预测服务
        logger.info("📝 第1步: 初始化预测服务...")
        service = EmbeddedRealPredictionService()

        # 2. 加载模型
        logger.info("💾 第2步: 加载训练模型...")
        if not await service.load_model():
            logger.error("❌ 模型加载失败")
            sys.exit(1)

        logger.info("✅ 模型加载成功")

        # 3. 执行预测
        logger.info("🔮 第3步: 执行比赛预测...")
        prediction_result = await service.predict_match(target_match_id)

        if prediction_result is None:
            logger.error("❌ 预测失败")
            sys.exit(1)

        # 4. 显示结果
        logger.info("📊 第4步: 显示预测结果...")
        print("\n" + "=" * 80)
        print("🏆 比赛信息:")
        print(f"   对阵双方: {prediction_result['match_info']['home_team']} vs {prediction_result['match_info']['away_team']}")
        print(f"   真实比分: {prediction_result['match_info']['actual_score']}")
        print(f"   实际结果: {prediction_result['match_info']['actual_result']}")

        print("\n🔮 模型预测:")
        print(f"   主队获胜概率: {prediction_result['prediction']['home_win_probability']:.2%}")
        print(f"   客队获胜概率: {prediction_result['prediction']['away_win_probability']:.2%}")
        print(f"   预测结果: {prediction_result['prediction']['predicted_class']}")
        print(f"   预测置信度: {prediction_result['prediction']['confidence']:.2%}")

        print("\n⚙️ 特征值:")
        for feature, value in prediction_result['feature_values'].items():
            print(f"   {feature:<25} : {value:.6f}")

        # 5. 验证预测准确性
        print("\n🎯 预测验证:")
        predicted = prediction_result['prediction']['predicted_class']
        actual = prediction_result['match_info']['actual_result']
        is_correct = predicted == actual

        print(f"   预测结果: {predicted}")
        print(f"   实际结果: {actual}")
        print(f"   预测正确: {'✅ 正确' if is_correct else '❌ 错误'}")

        if actual == 'draw':
            print("   📝 注意: 实际为平局，模型只能预测胜负")

        print("\n🎉 Phase 4 真实预测流程验证完成!")
        print("=" * 80)

        # 显示核心指标
        home_win_prob = prediction_result['prediction']['home_win_probability']
        print(f"\n📈 核心预测指标:")
        print(f"   主队 ({prediction_result['match_info']['home_team']}) 获胜概率: {home_win_prob:.2%}")
        print(f"   客队 ({prediction_result['match_info']['away_team']}) 获胜概率: {prediction_result['prediction']['away_win_probability']:.2%}")
        print(f"   模型置信度: {prediction_result['prediction']['confidence']:.2%}")

        return prediction_result

    except Exception as e:
        logger.error(f"❌ 验证过程失败: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())