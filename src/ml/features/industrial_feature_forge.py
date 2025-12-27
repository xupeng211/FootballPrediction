#!/usr/bin/env python3
"""
工业级特征锻造器 V12.1
废弃基于文件大小的伪特征，从playerStats提取真正的185维技术特征

V12.1 更新:
- C-01: 统一 NaN 填充机制
- C-03: 使用 SafeExpressionEvaluator 替换 eval()
"""

import json
import logging
from datetime import datetime

import numpy as np
import pandas as pd
import psycopg2

logger = logging.getLogger(__name__)


class IndustrialFeatureForge:
    """
    工业级特征锻造器 - V12.0

    核心功能:
    1. 从数据库读取已解析的player_stats数据
    2. 锻造185维纯技术特征
    3. 支持增量更新和批量处理
    4. 输出标准化的特征矩阵
    """

    def __init__(self):
        """初始化工业级特征锻造器"""
        self.feature_definitions = self._build_feature_definitions()
        self.feature_count = len(self.feature_definitions)
        logger.info(f"🏭 初始化工业级特征锻造器，支持 {self.feature_count} 维特征")

    def _build_feature_definitions(self) -> list[dict]:
        """
        构建185维特征定义

        Returns:
            特征定义列表
        """
        # 基础技术指标 (14个指标 × 5种计算方式 = 70维)
        base_metrics = [
            "shotsontarget",
            "shotstotal",
            "xg",
            "xa",
            "keypasses",
            "successfulpasses",
            "totalpasses",
            "touches",
            "aerialduelswon",
            "tackles",
            "interceptions",
            "clearances",
            "blocks",
            "bigchancescreated",
        ]

        # 高级技术指标 (15个指标 × 5种计算方式 = 75维)
        advanced_metrics = [
            "expectedgoals",
            "expectedassists",
            "progressivepasses",
            "progressivecarries",
            "dribblescompleted",
            "pressureevents",
            "carrydistance",
            "carriesintofinalthird",
            "carriesintopenaltyarea",
            "passesintofinalthird",
            "passesintopenaltyarea",
            "shotcreatingactions",
            "goalcreatingactions",
            "cornerkicks",
            "fouls",
        ]

        # 时间序列指标 (20个维度)
        temporal_metrics = [
            "first_half_xg",
            "second_half_xg",
            "first_half_shots",
            "second_half_shots",
            "home_xg_progression",
            "away_xg_progression",
            "momentum_shifts",
            "critical_minutes",
            "possession_control_periods",
            "high_pressure_periods",
        ]

        # 位置分布指标 (20个维度)
        positional_metrics = [
            "defensive_third_actions",
            "middle_third_actions",
            "attacking_third_actions",
            "left_wing_actions",
            "right_wing_actions",
            "central_actions",
            "box_actions",
            "penalty_area_actions",
            "set_piece_actions",
            "counter_attack_actions",
            "possession_buildup_actions",
            "final_third_entries",
        ]

        features = []

        # 构建基础指标特征
        for metric in base_metrics + advanced_metrics:
            # 主队、客队、总计、差值、比率
            features.extend(
                [
                    {"name": f"home_{metric}", "type": "numeric", "source": "player_stats"},
                    {"name": f"away_{metric}", "type": "numeric", "source": "player_stats"},
                    {"name": f"total_{metric}", "type": "derived", "formula": "home + away"},
                    {"name": f"diff_{metric}", "type": "derived", "formula": "home - away"},
                    {"name": f"ratio_{metric}", "type": "derived", "formula": "home / (away + 1e-6)"},
                ]
            )

        # 添加时间序列特征
        for metric in temporal_metrics:
            features.append({"name": metric, "type": "temporal", "source": "player_stats"})

        # 添加位置分布特征
        for metric in positional_metrics:
            features.append({"name": metric, "type": "positional", "source": "player_stats"})

        # 添加衍生计算特征 (40维)
        derived_features = [
            # 射门效率
            ("shot_accuracy", "shotsontarget / (shotstotal + 1e-6)"),
            ("xg_efficiency", "xg / (shotstotal + 1e-6)"),
            ("conversion_rate", "goals / (shotsontarget + 1e-6)"),
            # 传球效率
            ("pass_accuracy", "successfulpasses / (totalpasses + 1e-6)"),
            ("key_pass_rate", "keypasses / (totalpasses + 1e-6)"),
            ("progressive_pass_rate", "progressivepasses / (totalpasses + 1e-6)"),
            # 控球指标
            ("possession_domination", "touches - (touches_away if exists else 0)"),
            ("aerial_dominance", "aerialduelswon - (aerialduelswon_away if exists else 0)"),
            # 创造力指标
            ("chance_creation_rate", "bigchancescreated / (keypasses + 1e-6)"),
            ("assist_potential", "xa / (keypasses + 1e-6)"),
            # 防守效率
            ("defensive_efficiency", "(tackles + interceptions + blocks) / (touches_opponent + 1e-6)"),
            ("pressing_efficiency", "pressureevents / (touches_away + 1e-6)"),
        ]

        for name, formula in derived_features:
            features.append({"name": name, "type": "derived_formula", "formula": formula})

        logger.info(f"🎯 特征定义构建完成: {len(features)} 维")
        return features

    def forge_feature_matrix(self, match_ids: list[int] = None, limit: int = 1000) -> pd.DataFrame:
        """
        锻造特征矩阵

        Args:
            match_ids: 指定比赛ID列表，为None则自动查询
            limit: 处理记录数限制

        Returns:
            特征矩阵DataFrame
        """
        logger.info("🔥 开始工业级特征锻造")

        conn = None
        try:
            conn = self.get_database_connection()

            # 查询有player_stats数据的比赛
            if match_ids:
                id_filter = f"AND id IN ({','.join(map(str, match_ids))})"
            else:
                id_filter = ""

            query = f"""
                SELECT id, external_id, home_team, away_team, match_time,
                       home_score, away_score, actual_result, player_stats
                FROM matches
                WHERE player_stats IS NOT NULL
                AND home_score IS NOT NULL
                AND away_score IS NOT NULL
                {id_filter}
                ORDER BY match_time DESC
                LIMIT {limit}
            """

            df = pd.read_sql(query, conn)
            logger.info(f"📊 从数据库加载 {len(df)} 场比赛")

            if len(df) == 0:
                logger.warning("⚠️ 未找到有效的比赛数据")
                return pd.DataFrame()

            # 锻造特征
            features_data = []
            for idx, row in df.iterrows():
                try:
                    # 解析player_stats JSON
                    if row["player_stats"]:
                        player_stats = json.loads(row["player_stats"])

                        # 锻造单场比赛的特征
                        match_features = self._forge_match_features(row, player_stats)

                        if match_features:
                            features_data.append(match_features)

                except Exception as e:
                    logger.error(f"❌ 特征锻造失败 {row['external_id']}: {e}")
                    continue

            # 转换为DataFrame
            if features_data:
                feature_df = pd.DataFrame(features_data)

                # 添加基础信息
                feature_df["match_id"] = df["id"].values[: len(feature_df)]
                feature_df["external_id"] = df["external_id"].values[: len(feature_df)]
                feature_df["home_team"] = df["home_team"].values[: len(feature_df)]
                feature_df["away_team"] = df["away_team"].values[: len(feature_df)]
                feature_df["match_time"] = df["match_time"].values[: len(feature_df)]
                feature_df["actual_result"] = df["actual_result"].values[: len(feature_df)]
                feature_df["home_score"] = df["home_score"].values[: len(feature_df)]
                feature_df["away_score"] = df["away_score"].values[: len(feature_df)]

                logger.info(f"🎉 特征锻造完成！输出 {len(feature_df)} 行 x {len(feature_df.columns)} 列")
                logger.info(
                    f"📈 技术特征维度: {len([col for col in feature_df.columns if col not in ['match_id', 'external_id', 'home_team', 'away_team', 'match_time', 'actual_result', 'home_score', 'away_score']])}"
                )

                return feature_df
            else:
                logger.error("❌ 特征锻造失败，无有效数据")
                return pd.DataFrame()

        except Exception as e:
            logger.error(f"❌ 特征矩阵锻造失败: {e}")
            return pd.DataFrame()
        finally:
            if conn:
                conn.close()

    def _forge_match_features(self, match_row: pd.Series, player_stats: dict) -> dict:
        """
        锻造单场比赛的特征

        Args:
            match_row: 比赛基础信息
            player_stats: 玩家统计数据

        Returns:
            特征字典
        """
        features = {}

        try:
            # 提取技术指标
            tech_metrics = self._extract_technical_metrics(player_stats)

            # 应用特征定义
            for feature_def in self.feature_definitions:
                feature_name = feature_def["name"]
                feature_type = feature_def["type"]

                if feature_type == "numeric":
                    # C-01 修复: 统一使用 NaN 填充缺失值
                    # 模型需要能区分"真0"和"数据缺失"
                    value = tech_metrics.get(feature_name, None)
                    if value is None:
                        features[feature_name] = np.nan
                    else:
                        try:
                            features[feature_name] = float(value)
                        except (ValueError, TypeError):
                            features[feature_name] = np.nan

                elif feature_type == "derived":
                    # C-01 修复: derived 类型也需要 NaN 安全处理
                    metric_name = feature_name.split("_")[1]
                    home_val = tech_metrics.get(f"home_{metric_name}", None)
                    away_val = tech_metrics.get(f"away_{metric_name}", None)

                    # 处理 None/NaN 值
                    if home_val is None:
                        home_val = np.nan
                    else:
                        try:
                            home_val = float(home_val)
                        except (ValueError, TypeError):
                            home_val = np.nan

                    if away_val is None:
                        away_val = np.nan
                    else:
                        try:
                            away_val = float(away_val)
                        except (ValueError, TypeError):
                            away_val = np.nan

                    if feature_name.startswith("total_"):
                        # 如果任一值为 NaN，总计为 NaN
                        if np.isnan(home_val) or np.isnan(away_val):
                            features[feature_name] = np.nan
                        else:
                            features[feature_name] = float(home_val + away_val)
                    elif feature_name.startswith("diff_"):
                        # 如果任一值为 NaN，差值为 NaN
                        if np.isnan(home_val) or np.isnan(away_val):
                            features[feature_name] = np.nan
                        else:
                            features[feature_name] = float(home_val - away_val)
                    elif feature_name.startswith("ratio_"):
                        # C-01 修复: ratio 计算必须处理 NaN
                        if np.isnan(home_val) or np.isnan(away_val):
                            features[feature_name] = np.nan
                        else:
                            # 使用小的 epsilon 避免除零，但仅当分母为 0 时
                            denominator = away_val if abs(away_val) > 1e-10 else 1e-10
                            features[feature_name] = float(home_val / denominator)

                elif feature_type == "derived_formula":
                    # 复杂公式计算
                    features[feature_name] = self._calculate_derived_feature(feature_def["formula"], tech_metrics)

                else:
                    # 其他类型特征 - C-01 修复: 使用 NaN 填充
                    value = tech_metrics.get(feature_name, None)
                    if value is None:
                        features[feature_name] = np.nan
                    else:
                        try:
                            features[feature_name] = float(value)
                        except (ValueError, TypeError):
                            features[feature_name] = np.nan

        except Exception as e:
            logger.error(f"❌ 单场比赛特征锻造失败: {e}")

        return features

    def _extract_technical_metrics(self, player_stats: dict) -> dict:
        """
        从player_stats中提取技术指标

        Args:
            player_stats: 玩家统计数据

        Returns:
            技术指标字典
        """
        metrics = {}

        # 标准化所有指标名称为小写
        for key, value in player_stats.items():
            metrics[key.lower()] = value

        return metrics

    def _calculate_derived_feature(self, formula: str, tech_metrics: dict) -> float:
        """
        计算衍生特征 (C-03 修复版)

        使用 SafeExpressionEvaluator 替代不安全的 eval()

        Args:
            formula: 计算公式
            tech_metrics: 技术指标

        Returns:
            计算结果 (NaN 表示缺失值)
        """
        try:
            # C-03: 使用安全求值器
            from src.utils.safe_eval import safe_eval

            # 确保所有指标值都是数字类型
            safe_metrics = {}
            for key, value in tech_metrics.items():
                if value is None:
                    safe_metrics[key] = np.nan
                elif isinstance(value, (int, float)):
                    safe_metrics[key] = float(value)
                else:
                    try:
                        safe_metrics[key] = float(value)
                    except (ValueError, TypeError):
                        safe_metrics[key] = np.nan

            # 使用安全求值器计算
            result = safe_eval(formula, safe_metrics)

            return float(result) if not np.isnan(result) else np.nan

        except Exception as e:
            logger.error(f"❌ 衍生特征计算失败: {formula} -> {e}")
            return np.nan  # C-01: 失败时返回 NaN 而非 0

    def get_database_connection(self):
        """获取数据库连接"""
        try:
            from src.config_unified import get_settings

            settings = get_settings()
            db = settings.database

            return psycopg2.connect(
                host=db.host, port=db.port, database=db.name, user=db.user, password=db.password.get_secret_value()
            )
        except Exception:
            # 备用直接连接
            return psycopg2.connect(
                host="localhost", port="5432", database="football_db", user="football_user", password="football_pass"
            )

    def save_feature_matrix(self, feature_df: pd.DataFrame, filename: str = None) -> str:
        """
        保存特征矩阵

        Args:
            feature_df: 特征矩阵
            filename: 文件名，为None则自动生成

        Returns:
            保存的文件路径
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"industrial_feature_matrix_{timestamp}.csv"

        feature_df.to_csv(filename, index=False)
        logger.info(f"💾 特征矩阵已保存: {filename}")

        return filename

    def generate_feature_report(self, feature_df: pd.DataFrame) -> dict:
        """
        生成特征质量报告

        Args:
            feature_df: 特征矩阵

        Returns:
            质量报告字典
        """
        report = {
            "total_matches": len(feature_df),
            "total_features": len(feature_df.columns),
            "numeric_features": len(feature_df.select_dtypes(include=[np.number]).columns),
            "missing_values": feature_df.isnull().sum().sum(),
            "result_distribution": feature_df["actual_result"].value_counts().to_dict(),
            "feature_stats": {},
        }

        # 技术特征统计
        numeric_cols = feature_df.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            if col not in ["match_id", "home_score", "away_score"]:
                report["feature_stats"][col] = {
                    "mean": feature_df[col].mean(),
                    "std": feature_df[col].std(),
                    "min": feature_df[col].min(),
                    "max": feature_df[col].max(),
                }

        return report


def main():
    """测试工业级特征锻造器"""
    logger.info("🚀 测试工业级特征锻造器")

    forge = IndustrialFeatureForge()

    # 锻造特征矩阵
    feature_df = forge.forge_feature_matrix(limit=50)

    if not feature_df.empty:
        # 保存结果
        forge.save_feature_matrix(feature_df)

        # 生成报告
        report = forge.generate_feature_report(feature_df)

        logger.info("📊 特征质量报告:")
        logger.info(f"   总比赛数: {report['total_matches']}")
        logger.info(f"   特征维度: {report['total_features']}")
        logger.info(f"   数值特征: {report['numeric_features']}")
        logger.info(f"   缺失值: {report['missing_values']}")
        logger.info(f"   结果分布: {report['result_distribution']}")

        return True
    else:
        logger.error("❌ 特征锻造失败")
        return False


if __name__ == "__main__":
    import logging

    logging.basicConfig(level=logging.INFO)
    main()
