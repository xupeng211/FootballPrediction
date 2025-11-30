#!/usr/bin/env python3
"""
使用训练好的模型和生成的特征数据直接生成预测结果
"""

import sys
import pandas as pd
import numpy as np
import joblib
from datetime import datetime
from pathlib import Path
from collections import defaultdict

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 导入数据库连接
import sqlalchemy
from sqlalchemy import create_engine, text
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("🎯 简化预测器启动")
    logger.info("📊 目标：使用特征数据生成预测结果")
    logger.info("=" * 60)

    try:
        # 1. 加载生成的特征数据
        logger.info("📂 加载特征数据...")
        features_file = "/app/data/features_direct.csv"

        try:
            features_df = pd.read_csv(features_file)
            logger.info(f"✅ 成功加载 {len(features_df)} 条特征记录")
        except FileNotFoundError:
            logger.error(f"❌ 特征文件不存在: {features_file}")
            return

        # 2. 加载训练好的模型
        logger.info("🤖 加载训练模型...")
        model_path = "/app/models/football_prediction_direct.pkl"

        try:
            model = joblib.load(model_path)
            logger.info(f"✅ 成功加载模型: {model_path}")
        except FileNotFoundError:
            logger.error(f"❌ 模型文件不存在: {model_path}")
            return

        # 3. 准备预测特征
        logger.info("🔧 准备预测特征...")

        # 选择与训练时相同的特征
        feature_columns = [
            "home_team_encoded",
            "away_team_encoded",
            "league_encoded",
            "day_of_week",
            "month",
        ]

        # 检查特征列是否存在
        available_features = []
        for col in feature_columns:
            if col in features_df.columns:
                available_features.append(col)
            else:
                logger.warning(f"⚠️ 特征列 {col} 不存在，尝试创建...")

                # 创建缺失的特征
                if col == "home_team_encoded":
                    features_df[col] = features_df["home_team_name"].apply(
                        lambda x: hash(str(x)) % 1000
                    )
                    available_features.append(col)
                elif col == "away_team_encoded":
                    features_df[col] = features_df["away_team_name"].apply(
                        lambda x: hash(str(x)) % 1000
                    )
                    available_features.append(col)
                elif col == "league_encoded":
                    features_df[col] = features_df["league_name"].apply(
                        lambda x: hash(str(x)) % 100
                    )
                    available_features.append(col)
                elif col == "day_of_week":
                    features_df["collection_date"] = pd.to_datetime(
                        features_df["collection_date"]
                    )
                    features_df[col] = features_df["collection_date"].dt.dayofweek
                    available_features.append(col)
                elif col == "month":
                    features_df["collection_date"] = pd.to_datetime(
                        features_df["collection_date"]
                    )
                    features_df[col] = features_df["collection_date"].dt.month
                    available_features.append(col)

        X = features_df[available_features]
        logger.info(f"✅ 特征准备完成，维度: {X.shape}")

        # 4. 生成预测
        logger.info("🔮 生成预测结果...")

        # 获取预测概率和类别
        y_pred = model.predict(X)
        y_proba = model.predict_proba(X)

        logger.info(f"✅ 预测完成，生成 {len(y_pred)} 条预测结果")

        # 5. 构建预测结果DataFrame
        logger.info("📋 构建预测结果...")

        label_names = ["平局", "主队胜", "客队胜"]
        predictions = []

        for i, (_idx, row) in enumerate(features_df.iterrows()):
            pred_label = y_pred[i]
            proba = y_proba[i]

            # 获取实际结果（如果有）
            actual_result = None
            if "match_result" in row and not pd.isna(row["match_result"]):
                if row["match_result"] == 1:
                    actual_result = "主队胜"
                elif row["match_result"] == -1:
                    actual_result = "客队胜"
                elif row["match_result"] == 0:
                    actual_result = "平局"

            prediction = {
                "match_id": i + 1,
                "home_team": row["home_team_name"],
                "away_team": row["away_team_name"],
                "league": row["league_name"],
                "match_time": row.get("match_time", ""),
                "home_score": row.get("home_score", 0),
                "away_score": row.get("away_score", 0),
                "actual_result": actual_result,
                "predicted_label": int(pred_label),
                "predicted_result": label_names[pred_label + 1],  # 转换 -1,0,1 到索引
                "confidence": float(np.max(proba)),
                "prob_draw": float(proba[0]),
                "prob_home_win": float(proba[1]),
                "prob_away_win": float(proba[2]),
                "total_goals": row.get("total_goals", 0),
                "goal_difference": row.get("goal_difference", 0),
                "collection_date": row["collection_date"],
                "prediction_date": datetime.now().isoformat(),
            }
            predictions.append(prediction)

        predictions_df = pd.DataFrame(predictions)

        # 6. 分析预测结果
        logger.info("📈 分析预测结果...")

        total_predictions = len(predictions_df)
        high_confidence = predictions_df[predictions_df["confidence"] > 0.6]
        completed_matches = predictions_df[predictions_df["actual_result"].notna()]

        logger.info(f"  - 总预测数: {total_predictions}")
        logger.info(
            f"  - 高信心预测 (>60%): {len(high_confidence)} ({len(high_confidence) / total_predictions * 100:.1f}%)"
        )
        logger.info(f"  - 已完成比赛: {len(completed_matches)}")

        # 预测分布统计
        result_counts = predictions_df["predicted_result"].value_counts()
        logger.info("  - 预测结果分布:")
        for result, count in result_counts.items():
            percentage = count / total_predictions * 100
            logger.info(f"    * {result}: {count} ({percentage:.1f}%)")

        # 准确率分析（针对已完成的比赛）
        if len(completed_matches) > 0:
            correct_predictions = completed_matches[
                completed_matches["predicted_result"]
                == completed_matches["actual_result"]
            ]
            accuracy = len(correct_predictions) / len(completed_matches)
            logger.info(
                f"  - 已完成比赛预测准确率: {accuracy:.3f} ({len(correct_predictions)}/{len(completed_matches)})"
            )

        # 7. 保存预测结果
        logger.info("💾 保存预测结果...")

        # 保存完整预测结果
        predictions_file = "/app/data/match_predictions.csv"
        predictions_df.to_csv(predictions_file, index=False, encoding="utf-8")
        logger.info(f"✅ 完整预测结果已保存到: {predictions_file}")

        # 保存高信心预测
        high_conf_file = "/app/data/high_confidence_predictions.csv"
        high_confidence.to_csv(high_conf_file, index=False, encoding="utf-8")
        logger.info(f"✅ 高信心预测已保存到: {high_conf_file}")

        # 8. 展示高信心预测示例
        logger.info("🎯 高信心预测示例 (>65%):")
        top_predictions = high_confidence[high_confidence["confidence"] > 0.65].head(10)

        for _, pred in top_predictions.iterrows():
            match_info = f"{pred['home_team']} vs {pred['away_team']}"
            score_info = (
                f"({pred['home_score']}-{pred['away_score']})"
                if pred["home_score"] > 0
                else ""
            )
            actual_info = (
                f" [实际: {pred['actual_result']}]" if pred["actual_result"] else ""
            )

            logger.info(
                f"  📊 {match_info} {score_info}: {pred['predicted_result']} "
                f"(信心度: {pred['confidence']:.3f}){actual_info}"
            )

        # 9. 生成统计报告
        logger.info("📊 生成统计报告...")

        stats_report = {
            "总预测数": total_predictions,
            "高信心预测数": len(high_confidence),
            "高信心预测比例": f"{len(high_confidence) / total_predictions * 100:.1f}%",
            "已完成比赛数": len(completed_matches),
            "平均置信度": f"{predictions_df['confidence'].mean():.3f}",
            "最高置信度": f"{predictions_df['confidence'].max():.3f}",
            "预测生成时间": datetime.now().isoformat(),
        }

        if len(completed_matches) > 0:
            correct_predictions = completed_matches[
                completed_matches["predicted_result"]
                == completed_matches["actual_result"]
            ]
            accuracy = len(correct_predictions) / len(completed_matches)
            stats_report["已完成比赛准确率"] = f"{accuracy:.3f}"
            stats_report["正确预测数"] = len(correct_predictions)

        # 保存统计报告
        stats_file = "/app/data/prediction_stats.txt"
        with open(stats_file, "w", encoding="utf-8") as f:
            f.write("足球预测系统统计报告\n")
            f.write("=" * 30 + "\n")
            f.write(f"生成时间: {datetime.now().isoformat()}\n\n")
            for key, value in stats_report.items():
                f.write(f"{key}: {value}\n")

        logger.info(f"✅ 统计报告已保存到: {stats_file}")

        # 10. 最终总结
        logger.info("🎉 预测任务完成！")
        logger.info(f"📈 成功生成 {total_predictions} 条预测结果")
        logger.info(f"🎯 高信心预测: {len(high_confidence)} 条")
        logger.info(f"📊 平均置信度: {predictions_df['confidence'].mean():.3f}")

        if len(completed_matches) > 0:
            correct_predictions = completed_matches[
                completed_matches["predicted_result"]
                == completed_matches["actual_result"]
            ]
            accuracy = len(correct_predictions) / len(completed_matches)
            logger.info(f"🏆 已完成比赛准确率: {accuracy:.3f}")

        logger.info("=" * 60)

    except Exception:
        logger.error(f"❌ 预测生成失败: {str(e)}")
        import traceback

        logger.error(f"详细错误: {traceback.format_exc()}")


if __name__ == "__main__":
    main()
