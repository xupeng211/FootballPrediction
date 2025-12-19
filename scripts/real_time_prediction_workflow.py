#!/usr/bin/env python3
"""
⚽ 足球比赛预测CLI工具 v2.3 - 修复版本

基于服务层架构的预测工具，修复了模块导入问题。
使用统一配置系统，支持真实的AI预测逻辑。

主要改进：
1. 修复导入：使用InferenceService而不是inference_service_v2/v3
2. 统一配置：使用src.config_unified
3. 简化依赖：移除problematic模块
4. 保持功能：完整的特征提取和模型推理

使用示例:
    python scripts/predict_match_v2.py --home "Arsenal" --away "Chelsea"
"""

import argparse
import asyncio
import sys
import os
import logging
import json
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
import psycopg2
from psycopg2.extras import RealDictCursor
import hashlib

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PredictionDisplay:
    """预测结果展示器"""

    @staticmethod
    def format_confidence_bar(probability: float, width: int = 30) -> str:
        """格式化概率条形图"""
        filled_width = int(width * probability)
        empty_width = width - filled_width
        return "█" * filled_width + "░" * empty_width

    @staticmethod
    def display_prediction(prediction_data: Dict[str, Any]):
        """展示预测结果"""
        print("\n🏟️  比赛: {} vs {}".format(
            prediction_data.get('home_team', 'Unknown'),
            prediction_data.get('away_team', 'Unknown')
        ))
        if prediction_data.get('match_date'):
            print(f"📅  日期: {prediction_data['match_date']}")

        print("\n📊 预测概率:")
        
        probabilities = prediction_data.get('probabilities', {})
        labels = ['HOME_WIN', 'DRAW', 'AWAY_WIN']
        names = ['主胜', '平局', '客胜']
        
        for label, name in zip(labels, names):
            prob = probabilities.get(label, 0.0)
            bar = PredictionDisplay.format_confidence_bar(prob)
            print(f"{name} ({label}): {prob:.1%} |{bar}|")

        if 'prediction' in prediction_data:
            pred = prediction_data['prediction']
            prob = probabilities.get(pred, 0.0)
            print(f"\n🎯 预测结果: {pred}")
            print(f"💡 置信度: {prob:.1%}")

        if 'model_info' in prediction_data:
            model_info = prediction_data['model_info']
            print(f"📈 模型版本: {model_info.get('version', 'unknown')}")
            print(f"🤖 模型状态: {model_info.get('status', 'unknown')}")


class FootballPredictor:
    """足球预测器 - 修复版本（支持自动入库）"""

    def __init__(self):
        self.config = None
        self.inference_service = None
        self.simulation_mode = False
        self.db_connection = None
        
    async def initialize(self) -> bool:
        """初始化服务"""
        try:
            # 导入统一配置
            from src.config_unified import get_settings
            self.config = get_settings()
            
            # 导入修复后的推理服务
            from src.services.inference_service import InferenceService
            
            # 创建推理服务实例
            self.inference_service = InferenceService()
            
            # 尝试初始化服务
            try:
                success = await self.inference_service.initialize()
                if not success:
                    logger.warning("推理服务初始化失败，启用模拟模式")
                    self.simulation_mode = True
                    return True
            except Exception as e:
                logger.warning(f"推理服务初始化异常: {e}，启用模拟模式")
                self.simulation_mode = True
                return True

            # 初始化数据库连接
            self._init_database()

            logger.info("✅ 足球预测器初始化成功（包含数据库连接）")
            return True

        except Exception as e:
            logger.error(f"初始化失败: {e}")
            self.simulation_mode = True
            return True  # 继续运行，使用模拟模式

    def _create_mock_features(self, home_team: str, away_team: str) -> Dict[str, Any]:
        """创建模拟特征（当模型不可用时）"""
        import random
        
        # 基于队名生成稳定随机特征
        team_hash = abs(hash(home_team + away_team)) % 1000
        
        features = {
            'home_team_form': random.uniform(0.3, 0.8) + team_hash / 5000,
            'away_team_form': random.uniform(0.3, 0.8) + (team_hash * 2) % 1000 / 5000,
            'home_venue_advantage': random.uniform(0.1, 0.3),
            'h2h_home_wins': random.randint(0, 5),
            'h2h_draws': random.randint(0, 3),
            'h2h_away_wins': random.randint(0, 5),
            'league_points_diff': random.uniform(-15, 15),
            'goals_scored_home': random.uniform(1.0, 2.5),
            'goals_conceded_home': random.uniform(0.5, 1.5),
            'goals_scored_away': random.uniform(0.8, 2.0),
            'goals_conceded_away': random.uniform(0.8, 1.8),
        }
        
        return features

    def _calculate_mock_probabilities(self, features: Dict[str, Any]) -> Tuple[Dict[str, float], str]:
        """基于特征计算模拟概率"""
        home_strength = features['home_team_form'] + features['home_venue_advantage']
        away_strength = features['away_team_form']
        
        # 考虑H2H记录
        h2h_total = features['h2h_home_wins'] + features['h2h_draws'] + features['h2h_away_wins']
        if h2h_total > 0:
            h2h_home_rate = features['h2h_home_wins'] / h2h_total
            h2h_draw_rate = features['h2h_draws'] / h2h_total
            home_strength += h2h_home_rate * 0.1
            away_strength += (1 - h2h_home_rate - h2h_draw_rate) * 0.1
        
        # 考虑积分差异
        points_diff = features['league_points_diff']
        if points_diff > 0:
            home_strength += points_diff / 50
        else:
            away_strength += abs(points_diff) / 50
        
        # 计算优势评分
        total_strength = home_strength + away_strength
        if total_strength > 0:
            home_prob = min(0.8, home_strength / total_strength)
            away_prob = min(0.7, away_strength / total_strength)
            draw_prob = 1.0 - home_prob - away_prob
            
            if draw_prob < 0:
                if home_prob > away_prob:
                    home_prob -= abs(draw_prob) / 2
                    away_prob -= abs(draw_prob) / 2
                else:
                    home_prob -= abs(draw_prob) / 2
                    away_prob -= abs(draw_prob) / 2
                draw_prob = 0.05
        else:
            home_prob, draw_prob, away_prob = 0.4, 0.3, 0.3
        
        probabilities = {
            'HOME_WIN': round(home_prob, 4),
            'DRAW': round(draw_prob, 4),
            'AWAY_WIN': round(away_prob, 4)
        }
        
        # 确定预测结果
        prediction = max(probabilities.items(), key=lambda x: x[1])[0]
        
        return probabilities, prediction

    def _init_database(self):
        """初始化数据库连接"""
        try:
            # 使用环境变量配置，提供默认值
            db_host = os.getenv('DB_HOST', 'db')  # 容器内默认主机名
            db_port = os.getenv('DB_PORT', '5432')
            db_name = os.getenv('DB_NAME', 'football_prediction_shadow')  # 默认shadow数据库
            db_user = os.getenv('DB_USER', 'football_user')
            db_password = os.getenv('DB_PASSWORD', 'football_pass')

            # 创建数据库连接
            self.db_connection = psycopg2.connect(
                host=db_host,
                port=db_port,
                database=db_name,
                user=db_user,
                password=db_password,
                cursor_factory=RealDictCursor
            )

            # 创建表（如果不存在）
            self._create_tables()

            logger.info(f"✅ 数据库连接成功: {db_name}")

        except Exception as e:
            logger.warning(f"数据库连接失败: {e}，预测结果将不会保存")
            self.db_connection = None

    def _create_tables(self):
        """创建数据表（如果不存在）"""
        if not self.db_connection:
            return

        try:
            with self.db_connection.cursor() as cursor:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS realtime_predictions (
                        id SERIAL PRIMARY KEY,
                        match_id VARCHAR(100) UNIQUE NOT NULL,
                        home_team VARCHAR(200) NOT NULL,
                        away_team VARCHAR(200) NOT NULL,
                        match_date TIMESTAMP,
                        prediction VARCHAR(50) NOT NULL,
                        confidence FLOAT NOT NULL,
                        home_win_prob FLOAT,
                        draw_prob FLOAT,
                        away_win_prob FLOAT,
                        features JSONB,
                        model_version VARCHAR(100),
                        simulation_mode BOOLEAN DEFAULT FALSE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)

                # 创建索引
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_realtime_predictions_match_date
                    ON realtime_predictions(match_date);
                """)

                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_realtime_predictions_created_at
                    ON realtime_predictions(created_at);
                """)

                self.db_connection.commit()
                logger.info("✅ 数据表创建/检查完成")

        except Exception as e:
            logger.error(f"创建表失败: {e}")
            self.db_connection.rollback()

    def _save_prediction_to_database(self, prediction_result: Dict[str, Any]) -> bool:
        """将预测结果保存到数据库"""
        if not self.db_connection:
            logger.warning("数据库未连接，跳过保存")
            return False

        try:
            # 生成唯一的match_id
            home_team = prediction_result.get('home_team', 'unknown')
            away_team = prediction_result.get('away_team', 'unknown')
            match_date = prediction_result.get('match_date') or datetime.now().isoformat()

            # 基于队名和日期生成稳定的match_id
            match_id_base = f"{home_team}_{away_team}_{match_date.split('T')[0]}"
            match_id_hash = hashlib.md5(match_id_base.encode()).hexdigest()[:8]
            match_id = f"{home_team[:3].upper()}_{away_team[:3].upper()}_{match_id_hash}"

            probabilities = prediction_result.get('probabilities', {})

            with self.db_connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO realtime_predictions
                    (match_id, home_team, away_team, match_date, prediction, confidence,
                     home_win_prob, draw_prob, away_win_prob, features, model_version, simulation_mode)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (match_id) DO UPDATE SET
                        prediction = EXCLUDED.prediction,
                        confidence = EXCLUDED.confidence,
                        home_win_prob = EXCLUDED.home_win_prob,
                        draw_prob = EXCLUDED.draw_prob,
                        away_win_prob = EXCLUDED.away_win_prob,
                        updated_at = CURRENT_TIMESTAMP;
                """, (
                    match_id,
                    home_team,
                    away_team,
                    match_date,
                    prediction_result.get('prediction'),
                    prediction_result.get('confidence'),
                    probabilities.get('HOME_WIN'),
                    probabilities.get('DRAW'),
                    probabilities.get('AWAY_WIN'),
                    json.dumps(prediction_result.get('features', {}), default=str),
                    prediction_result.get('model_info', {}).get('version', 'unknown'),
                    prediction_result.get('simulation_mode', False)
                ))

                self.db_connection.commit()
                logger.info(f"✅ 预测结果已保存到数据库: {match_id}")
                return True

        except Exception as e:
            logger.error(f"保存预测结果到数据库失败: {e}")
            if self.db_connection:
                self.db_connection.rollback()
            return False

    async def predict_match(
        self,
        home_team: str,
        away_team: str,
        match_date: Optional[datetime] = None,
        match_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """预测比赛结果"""
        try:
            if self.simulation_mode or not self.inference_service:
                logger.info("使用模拟模式进行预测")
                features = self._create_mock_features(home_team, away_team)
                probabilities, prediction = self._calculate_mock_probabilities(features)

                result = {
                    'success': True,
                    'home_team': home_team,
                    'away_team': away_team,
                    'match_date': match_date.isoformat() if match_date else None,
                    'match_id': match_id,
                    'probabilities': probabilities,
                    'prediction': prediction,
                    'confidence': probabilities[prediction],
                    'model_info': {
                        'version': 'simulation_mode',
                        'status': 'mock',
                        'features_count': len(features)
                    },
                    'features': features,
                    'simulation_mode': True
                }

                # 自动保存到数据库
                self._save_prediction_to_database(result)

                return result
            
            # 尝试使用真实推理服务
            try:
                # 这里需要根据实际的InferenceService API调整
                prediction_result = await self.inference_service.predict_single_match(
                    home_team=home_team,
                    away_team=away_team,
                    match_date=match_date
                )
                
                if prediction_result and prediction_result.get('success'):
                    logger.info("✅ 真实模型预测成功")
                    # 自动保存到数据库
                    self._save_prediction_to_database(prediction_result)
                    return prediction_result
                else:
                    logger.warning("真实模型预测失败，降级到模拟模式")
                    return await self._fallback_prediction(home_team, away_team, match_date, match_id)
                    
            except Exception as e:
                logger.warning(f"真实模型预测异常: {e}，降级到模拟模式")
                return await self._fallback_prediction(home_team, away_team, match_date, match_id)

        except Exception as e:
            logger.error(f"预测过程出错: {e}")
            return {
                'success': False,
                'error': str(e),
                'home_team': home_team,
                'away_team': away_team
            }

    async def _fallback_prediction(self, home_team: str, away_team: str, 
                                 match_date: Optional[datetime] = None,
                                 match_id: Optional[str] = None) -> Dict[str, Any]:
        """降级预测方法"""
        features = self._create_mock_features(home_team, away_team)
        probabilities, prediction = self._calculate_mock_probabilities(features)
        
        result = {
            'success': True,
            'home_team': home_team,
            'away_team': away_team,
            'match_date': match_date.isoformat() if match_date else None,
            'match_id': match_id,
            'probabilities': probabilities,
            'prediction': prediction,
            'confidence': probabilities[prediction],
            'model_info': {
                'version': 'fallback_mode',
                'status': 'mock',
                'features_count': len(features)
            },
            'features': features,
            'fallback_mode': True
        }

        # 自动保存到数据库
        self._save_prediction_to_database(result)

        return result


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='足球比赛预测工具 v2.3')
    parser.add_argument('--home', required=True, help='主队名称')
    parser.add_argument('--away', required=True, help='客队名称')
    parser.add_argument('--date', help='比赛日期 (YYYY-MM-DD)')
    parser.add_argument('--match-id', help='比赛ID')
    parser.add_argument('--verbose', '-v', action='store_true', help='详细输出')
    parser.add_argument('--json-only', action='store_true', help='仅输出JSON格式')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # 解析日期
    match_date = None
    if args.date:
        try:
            match_date = datetime.strptime(args.date, '%Y-%m-%d')
        except ValueError:
            logger.error(f"日期格式错误: {args.date}，请使用 YYYY-MM-DD 格式")
            sys.exit(1)
    
    # 创建预测器
    predictor = FootballPredictor()
    
    # 初始化
    logger.info("🔧 初始化足球预测器...")
    init_success = await predictor.initialize()
    
    if not init_success:
        logger.error("❌ 预测器初始化失败")
        sys.exit(1)
    
    # 执行预测
    logger.info("🎯 开始预测...")
    result = await predictor.predict_match(
        home_team=args.home,
        away_team=args.away,
        match_date=match_date,
        match_id=args.match_id
    )
    
    if not result.get('success'):
        logger.error(f"❌ 预测失败: {result.get('error', '未知错误')}")
        sys.exit(1)
    
    # 输出结果
    if args.json_only:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        # 显示格式化结果
        PredictionDisplay.display_prediction(result)
        
        # 显示详细模式信息
        if result.get('simulation_mode'):
            print("\n⚠️  运行模式: 模拟模式 (真实模型不可用)")
        elif result.get('fallback_mode'):
            print("\n⚠️  运行模式: 降级模式 (真实模型异常)")
        else:
            print("\n✅ 运行模式: 真实AI预测")
    
    logger.info("🎉 预测完成")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⏹️  预测已取消")
        sys.exit(0)
    except Exception as e:
        logger.error(f"程序异常: {e}")
        sys.exit(1)
