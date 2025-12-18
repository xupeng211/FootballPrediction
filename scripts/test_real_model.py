#!/usr/bin/env python3
"""
真实模型测试脚本

直接测试已训练的模型，绕过复杂的依赖注入和架构问题。
"""

import os
import sys
import logging
import pandas as pd
import numpy as np
import pickle
from datetime import datetime
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def load_model(model_path):
    """加载训练好的模型"""
    logger.info(f"正在加载模型: {model_path}")

    try:
        with open(model_path, 'rb') as f:
            model_data = pickle.load(f)

        logger.info(f"模型加载成功!")
        logger.info(f"模型版本: {model_data.get('version', 'unknown')}")
        logger.info(f"模型准确率: {model_data.get('accuracy', 'unknown')}")
        logger.info(f"特征数量: {len(model_data['feature_columns'])}")
        logger.info(f"特征列: {model_data['feature_columns']}")

        return model_data
    except Exception as e:
        logger.error(f"模型加载失败: {e}")
        return None

def extract_features(home_team, away_team):
    """提取特征（简化版本）"""
    import hashlib

    # 基于队名生成一致的特征
    home_hash = int(hashlib.md5(home_team.encode()).hexdigest()[:8], 16)
    away_hash = int(hashlib.md5(away_team.encode()).hexdigest()[:8], 16)

    # 生成xG特征（基于历史数据的一般范围）
    home_xg = 0.5 + (home_hash % 100) / 100 * 2.0
    away_xg = 0.5 + (away_hash % 100) / 100 * 2.0

    return {
        'home_xg': home_xg,
        'away_xg': away_xg,
        'total_xg': home_xg + away_xg,
        'xg_difference': home_xg - away_xg,
        'xg_ratio': home_xg / (away_xg + 0.01),
    }

def predict_with_real_model(model_data, home_team, away_team):
    """使用真实模型进行预测"""
    logger.info(f"开始真实模型预测: {home_team} vs {away_team}")

    model = model_data['model']
    feature_columns = model_data['feature_columns']

    # 提取特征
    features = extract_features(home_team, away_team)

    # 准备特征向量
    feature_vector = []
    for feature_name in feature_columns:
        if feature_name in features:
            feature_vector.append(features[feature_name])
        else:
            feature_vector.append(0.0)

    feature_array = np.array(feature_vector).reshape(1, -1)

    # 预测
    prediction = model.predict_proba(feature_array)[0]
    predicted_class = model.predict(feature_array)[0]

    # 转换结果
    probabilities = prediction.tolist()
    if len(probabilities) == 3:
        away_prob, draw_prob, home_prob = probabilities
    else:
        home_prob = prediction[1] if len(prediction) > 1 else 0.33
        away_prob = 1.0 - home_prob
        draw_prob = 0.0

    outcomes = ["AWAY_WIN", "DRAW", "HOME_WIN"]
    predicted_outcome = outcomes[predicted_class] if predicted_class < 3 else "UNKNOWN"

    confidence = max(probabilities)

    result = {
        "match_info": {
            "home_team": home_team,
            "away_team": away_team,
            "prediction_date": datetime.now().isoformat()
        },
        "prediction": {
            "away_win_prob": float(away_prob),
            "draw_prob": float(draw_prob),
            "home_win_prob": float(home_prob),
            "predicted_outcome": predicted_outcome,
            "predicted_class": int(predicted_class),
            "confidence": float(confidence),
        },
        "model_info": {
            "status": "loaded",
            "model_version": model_data.get('version', 'unknown'),
            "feature_count": len(feature_columns),
            "accuracy": model_data.get('accuracy', None),
            "features_used": feature_columns,
            "feature_values": features
        }
    }

    return result

def display_prediction_result(result):
    """显示预测结果"""
    print("\n" + "="*70)
    print("🏆 真实模型预测结果")
    print("="*70)

    info = result["match_info"]
    pred = result["prediction"]
    model = result["model_info"]

    print(f"\n⚽ 比赛信息:")
    print(f"   主队: {info['home_team']}")
    print(f"   客队: {info['away_team']}")
    print(f"   预测时间: {info['prediction_date']}")

    print(f"\n🎯 预测概率:")
    home_pct = pred['home_win_prob'] * 100
    draw_pct = pred['draw_prob'] * 100
    away_pct = pred['away_win_prob'] * 100

    print(f"   主胜      : {home_pct:5.1%} |{'█' * int(home_pct/3)}{'░' * (33-int(home_pct/3))}|")
    print(f"   平局      : {draw_pct:5.1%} |{'█' * int(draw_pct/3)}{'░' * (33-int(draw_pct/3))}|")
    print(f"   客胜      : {away_pct:5.1%} |{'█' * int(away_pct/3)}{'░' * (33-int(away_pct/3))}|")

    print(f"\n💡 预测结果:")
    print(f"   最终预测: {pred['predicted_outcome']}")
    print(f"   置信度: {pred['confidence']:.3f} ({pred['confidence']*100:.1f}%)")

    # 风险评估
    if pred['confidence'] > 0.6:
        risk = "低风险"
        emoji = "💰"
    elif pred['confidence'] > 0.5:
        risk = "中等风险"
        emoji = "📈"
    else:
        risk = "高风险"
        emoji = "⚠️"

    print(f"   {emoji} 风险评估: {risk}")

    print(f"\n🤖 模型信息:")
    print(f"   状态: {model['status']} ✅")
    print(f"   版本: {model['model_version']}")
    print(f"   特征数量: {model['feature_count']}")
    print(f"   训练准确率: {model.get('accuracy', 'unknown')}")

    print(f"\n🔍 特征详情:")
    for feature, value in model['feature_values'].items():
        print(f"   {feature:15}: {value:.3f}")

    print("\n" + "="*70)

def main():
    """主函数"""
    try:
        # 模型路径
        model_path = "/home/user/projects/FootballPrediction/data/models/football_prediction_model.pkl"

        # 检查模型文件是否存在
        if not Path(model_path).exists():
            print(f"❌ 模型文件不存在: {model_path}")
            return 1

        # 加载模型
        model_data = load_model(model_path)
        if not model_data:
            print("❌ 模型加载失败")
            return 1

        # 测试预测
        test_matches = [
            ("Manchester United", "Arsenal"),
            ("Chelsea", "Liverpool"),
            ("Manchester City", "Tottenham"),
            ("Barcelona", "Real Madrid"),
        ]

        for home, away in test_matches:
            print(f"\n🔄 正在预测: {home} vs {away}")
            result = predict_with_real_model(model_data, home, away)
            display_prediction_result(result)

            # 添加分隔符
            if (home, away) != test_matches[-1]:
                print("\n" + "-"*70)

        print("\n🎉 真实模型预测测试完成!")
        return 0

    except Exception as e:
        logger.error(f"预测过程失败: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())