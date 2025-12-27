#!/usr/bin/env python3
"""
Docker 容器内全链路冒烟测试
完整运行数据加载、特征提取、模型推理流程
"""

import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

# 配置日志
log_dir = Path(__file__).parent.parent.parent / "logs"
log_dir.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(log_dir / "docker_smoke_test.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


class SmokeTest:
    """全链路冒烟测试"""

    def __init__(self):
        self.results = {"timestamp": datetime.now().isoformat(), "phases": {}, "metrics": {}}

    def phase1_model_loading(self) -> dict:
        """阶段1: 模型加载测试"""
        logger.info("=" * 60)
        logger.info("📦 阶段1: 模型加载测试")
        logger.info("=" * 60)

        start_time = time.time()
        phase_result = {"name": "模型加载", "status": "unknown", "steps": {}}

        try:
            # 1.1 检查模型文件
            logger.info("1.1 检查模型文件...")
            from src.config_unified import get_settings

            settings = get_settings()
            model_path = settings.get_model_path()

            step_start = time.time()
            if model_path.exists():
                file_size = model_path.stat().st_size
                phase_result["steps"]["file_check"] = {"status": "OK", "path": str(model_path), "size_bytes": file_size}
                logger.info(f"✅ 模型文件存在: {file_size} bytes")
            else:
                phase_result["steps"]["file_check"] = {"status": "Fail", "error": "模型文件不存在"}
                raise FileNotFoundError("模型文件不存在")

            # 1.2 加载模型
            logger.info("1.2 加载模型...")
            step_start = time.time()
            import joblib

            model_data = joblib.load(model_path)
            model = model_data["model"]
            scaler = model_data.get("scaler")
            feature_names = model_data.get("feature_names", [])

            phase_result["steps"]["model_load"] = {
                "status": "OK",
                "model_type": type(model).__name__,
                "feature_count": len(feature_names),
                "has_scaler": scaler is not None,
                "load_time_ms": round((time.time() - step_start) * 1000, 2),
            }
            logger.info(f"✅ 模型加载成功: {type(model).__name__}, {len(feature_names)} 维特征")

            # 1.3 验证模型可预测
            logger.info("1.3 验证模型可预测性...")
            step_start = time.time()

            import numpy as np

            X_test = np.random.randn(1, len(feature_names))
            if scaler:
                X_test = scaler.transform(X_test)

            prediction = model.predict(X_test)
            prediction_proba = model.predict_proba(X_test)

            phase_result["steps"]["model_inference"] = {
                "status": "OK",
                "prediction": int(prediction[0]),
                "prediction_proba_shape": list(prediction_proba.shape),
                "inference_time_ms": round((time.time() - step_start) * 1000, 2),
            }
            logger.info(f"✅ 模型推理成功: 预测结果={prediction[0]}")

            phase_result["status"] = "OK"
            phase_result["total_time_ms"] = round((time.time() - start_time) * 1000, 2)

        except Exception as e:
            phase_result["status"] = "Fail"
            phase_result["error"] = str(e)
            phase_result["total_time_ms"] = round((time.time() - start_time) * 1000, 2)
            logger.error(f"❌ 模型加载失败: {e}")

        self.results["phases"]["phase1_model_loading"] = phase_result
        return phase_result

    def phase2_data_loading(self) -> dict:
        """阶段2: 数据加载测试"""
        logger.info("=" * 60)
        logger.info("📊 阶段2: 数据加载测试")
        logger.info("=" * 60)

        start_time = time.time()
        phase_result = {"name": "数据加载", "status": "unknown", "steps": {}}

        try:
            import pandas as pd
            import psycopg2

            from src.config_unified import get_settings

            settings = get_settings()
            db = settings.database

            # 2.1 连接数据库
            logger.info("2.1 连接数据库...")
            step_start = time.time()

            conn = psycopg2.connect(
                host=db.host, port=db.port, database=db.name, user=db.user, password=db.password.get_secret_value()
            )

            phase_result["steps"]["db_connect"] = {
                "status": "OK",
                "host": db.host,
                "connect_time_ms": round((time.time() - step_start) * 1000, 2),
            }
            logger.info(f"✅ 数据库连接成功: {db.host}")

            # 2.2 加载比赛数据
            logger.info("2.2 加载比赛数据...")
            step_start = time.time()

            query = """
                SELECT
                    external_id, match_time, home_team, away_team,
                    home_xg, away_xg, home_possession, away_possession,
                    home_shots_on_target, away_shots_on_target,
                    home_corners, away_corners
                FROM match_features_training
                WHERE home_xg IS NOT NULL
                ORDER BY match_time DESC
                LIMIT 100
            """

            df = pd.read_sql(query, conn)
            conn.close()

            phase_result["steps"]["data_load"] = {
                "status": "OK",
                "record_count": len(df),
                "column_count": len(df.columns),
                "load_time_ms": round((time.time() - step_start) * 1000, 2),
            }
            logger.info(f"✅ 数据加载成功: {len(df)} 场比赛")

            # 2.3 数据质量检查
            logger.info("2.3 数据质量检查...")
            step_start = time.time()

            null_counts = df.isnull().sum()
            critical_columns = ["home_xg", "away_xg", "home_possession", "away_possession"]
            data_quality = {
                col: {
                    "null_count": int(null_counts[col]),
                    "null_percentage": round(null_counts[col] / len(df) * 100, 2),
                }
                for col in critical_columns
            }

            phase_result["steps"]["data_quality"] = {
                "status": "OK",
                "quality_metrics": data_quality,
                "check_time_ms": round((time.time() - step_start) * 1000, 2),
            }
            logger.info("✅ 数据质量检查完成")

            # 保存数据供后续阶段使用
            self.test_data = df

            phase_result["status"] = "OK"
            phase_result["total_time_ms"] = round((time.time() - start_time) * 1000, 2)

        except Exception as e:
            phase_result["status"] = "Fail"
            phase_result["error"] = str(e)
            phase_result["total_time_ms"] = round((time.time() - start_time) * 1000, 2)
            logger.error(f"❌ 数据加载失败: {e}")

        self.results["phases"]["phase2_data_loading"] = phase_result
        return phase_result

    def phase3_feature_extraction(self) -> dict:
        """阶段3: 特征工程测试"""
        logger.info("=" * 60)
        logger.info("🔧 阶段3: 特征工程测试")
        logger.info("=" * 60)

        start_time = time.time()
        phase_result = {"name": "特征工程", "status": "unknown", "steps": {}}

        try:
            if not hasattr(self, "test_data") or self.test_data is None:
                raise ValueError("测试数据未加载，请先运行数据加载阶段")

            from sklearn.preprocessing import StandardScaler

            # 3.1 特征选择
            logger.info("3.1 特征选择...")
            step_start = time.time()

            feature_columns = [
                "home_xg",
                "away_xg",
                "home_possession",
                "away_possession",
                "home_shots_on_target",
                "away_shots_on_target",
                "home_corners",
                "away_corners",
            ]

            available_features = [col for col in feature_columns if col in self.test_data.columns]

            phase_result["steps"]["feature_selection"] = {
                "status": "OK",
                "requested_features": len(feature_columns),
                "available_features": len(available_features),
                "features": available_features,
            }
            logger.info(f"✅ 特征选择: {len(available_features)}/{len(feature_columns)} 可用")

            # 3.2 特征标准化
            logger.info("3.2 特征标准化...")
            step_start = time.time()

            X = self.test_data[available_features].fillna(0).values
            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(X)

            phase_result["steps"]["feature_scaling"] = {
                "status": "OK",
                "sample_count": len(X),
                "feature_count": X_scaled.shape[1],
                "scaling_time_ms": round((time.time() - step_start) * 1000, 2),
            }
            logger.info(f"✅ 特征标准化完成: {X_scaled.shape}")

            # 3.3 衍生特征计算
            logger.info("3.3 衍生特征计算...")
            step_start = time.time()

            # 计算衍生特征
            self.test_data["xg_diff"] = self.test_data["home_xg"] - self.test_data["away_xg"]
            self.test_data["possession_diff"] = self.test_data["home_possession"] - self.test_data["away_possession"]
            self.test_data["shots_diff"] = (
                self.test_data["home_shots_on_target"] - self.test_data["away_shots_on_target"]
            )

            derived_features = {
                "xg_diff": self.test_data["xg_diff"].describe().to_dict(),
                "possession_diff": self.test_data["possession_diff"].describe().to_dict(),
                "shots_diff": self.test_data["shots_diff"].describe().to_dict(),
            }

            phase_result["steps"]["derived_features"] = {
                "status": "OK",
                "derived_feature_count": 3,
                "statistics": derived_features,
                "compute_time_ms": round((time.time() - step_start) * 1000, 2),
            }
            logger.info("✅ 衍生特征计算完成")

            phase_result["status"] = "OK"
            phase_result["total_time_ms"] = round((time.time() - start_time) * 1000, 2)

        except Exception as e:
            phase_result["status"] = "Fail"
            phase_result["error"] = str(e)
            phase_result["total_time_ms"] = round((time.time() - start_time) * 1000, 2)
            logger.error(f"❌ 特征工程失败: {e}")

        self.results["phases"]["phase3_feature_extraction"] = phase_result
        return phase_result

    def phase4_model_prediction(self) -> dict:
        """阶段4: 模型预测测试"""
        logger.info("=" * 60)
        logger.info("🤖 阶段4: 模型预测测试")
        logger.info("=" * 60)

        start_time = time.time()
        phase_result = {"name": "模型预测", "status": "unknown", "steps": {}, "predictions": []}

        try:
            if not hasattr(self, "test_data") or self.test_data is None:
                raise ValueError("测试数据未加载")

            import joblib
            import numpy as np

            from src.config_unified import get_settings

            settings = get_settings()
            model_path = settings.get_model_path()

            # 4.1 加载模型
            logger.info("4.1 加载模型...")
            step_start = time.time()

            model_data = joblib.load(model_path)
            model = model_data["model"]
            scaler = model_data.get("scaler")

            phase_result["steps"]["model_reload"] = {
                "status": "OK",
                "load_time_ms": round((time.time() - step_start) * 1000, 2),
            }

            # 4.2 批量预测
            logger.info("4.2 执行批量预测...")
            step_start = time.time()

            # 准备特征
            feature_columns = [
                "home_xg",
                "away_xg",
                "home_possession",
                "away_possession",
                "home_shots_on_target",
                "away_shots_on_target",
                "home_corners",
                "away_corners",
            ]
            available_features = [col for col in feature_columns if col in self.test_data.columns]
            X = self.test_data[available_features].fillna(0).values

            # 标准化
            if scaler:
                X = scaler.transform(X)

            # 预测
            predictions = model.predict(X)
            prediction_proba = model.predict_proba(X)

            predict_time = (time.time() - step_start) * 1000

            # 4.3 分析预测结果
            logger.info("4.3 分析预测结果...")
            step_start = time.time()

            pred_dist = {
                "away_win": int(np.sum(predictions == 0)),
                "draw": int(np.sum(predictions == 1)),
                "home_win": int(np.sum(predictions == 2)),
            }

            avg_confidence = {
                "away_win": round(float(np.mean(prediction_proba[:, 0])), 4),
                "draw": round(float(np.mean(prediction_proba[:, 1])), 4),
                "home_win": round(float(np.mean(prediction_proba[:, 2])), 4),
            }

            phase_result["steps"]["batch_prediction"] = {
                "status": "OK",
                "prediction_count": len(predictions),
                "prediction_distribution": pred_dist,
                "average_confidence": avg_confidence,
                "predictions_per_second": round(len(predictions) / (predict_time / 1000), 2),
                "total_time_ms": round(predict_time, 2),
            }
            logger.info(f"✅ 预测完成: {pred_dist}")
            logger.info(f"   平均置信度: {avg_confidence}")

            # 保存前5个预测结果
            for i in range(min(5, len(self.test_data))):
                row = self.test_data.iloc[i]
                phase_result["predictions"].append(
                    {
                        "match": f"{row['home_team']} vs {row['away_team']}",
                        "prediction": int(predictions[i]),
                        "confidence": {
                            "away_win": round(float(prediction_proba[i, 0]), 4),
                            "draw": round(float(prediction_proba[i, 1]), 4),
                            "home_win": round(float(prediction_proba[i, 2]), 4),
                        },
                    }
                )

            phase_result["status"] = "OK"
            phase_result["total_time_ms"] = round((time.time() - start_time) * 1000, 2)

        except Exception as e:
            phase_result["status"] = "Fail"
            phase_result["error"] = str(e)
            phase_result["total_time_ms"] = round((time.time() - start_time) * 1000, 2)
            logger.error(f"❌ 模型预测失败: {e}")

        self.results["phases"]["phase4_model_prediction"] = phase_result
        return phase_result

    def phase5_performance_metrics(self) -> dict:
        """阶段5: 性能指标计算"""
        logger.info("=" * 60)
        logger.info("📈 阶段5: 性能指标计算")
        logger.info("=" * 60)

        start_time = time.time()
        phase_result = {"name": "性能指标", "status": "unknown", "steps": {}, "metrics": {}}

        try:
            # 5.1 计算总体耗时
            logger.info("5.1 计算总体耗时...")
            total_time = sum(phase.get("total_time_ms", 0) for phase in self.results["phases"].values())

            phase_result["steps"]["total_time"] = {
                "status": "OK",
                "total_time_ms": total_time,
                "total_time_seconds": round(total_time / 1000, 2),
            }

            # 5.2 计算各阶段耗时占比
            logger.info("5.2 计算各阶段耗时占比...")
            phase_times = {name: phase.get("total_time_ms", 0) for name, phase in self.results["phases"].items()}

            phase_percentages = {
                name: round(time_ms / total_time * 100, 2) if total_time > 0 else 0
                for name, time_ms in phase_times.items()
            }

            phase_result["steps"]["phase_breakdown"] = {
                "status": "OK",
                "phase_times_ms": phase_times,
                "phase_percentages": phase_percentages,
            }

            # 5.3 计算关键指标
            logger.info("5.3 计算关键指标...")

            # 从阶段4获取预测信息
            phase4 = self.results["phases"].get("phase4_model_prediction", {})
            batch_pred = phase4.get("steps", {}).get("batch_prediction", {})

            if batch_pred:
                pred_count = batch_pred.get("prediction_count", 0)
                pred_time = batch_pred.get("total_time_ms", 0)

                phase_result["metrics"] = {
                    "total_predictions": pred_count,
                    "prediction_latency_avg_ms": round(pred_time / pred_count, 2) if pred_count > 0 else 0,
                    "throughput_predictions_per_sec": batch_pred.get("predictions_per_second", 0),
                    "average_confidence_home_win": batch_pred.get("average_confidence", {}).get("home_win", 0),
                    "average_confidence_draw": batch_pred.get("average_confidence", {}).get("draw", 0),
                    "average_confidence_away_win": batch_pred.get("average_confidence", {}).get("away_win", 0),
                }

            phase_result["status"] = "OK"
            phase_result["total_time_ms"] = round((time.time() - start_time) * 1000, 2)

        except Exception as e:
            phase_result["status"] = "Fail"
            phase_result["error"] = str(e)
            phase_result["total_time_ms"] = round((time.time() - start_time) * 1000, 2)
            logger.error(f"❌ 性能指标计算失败: {e}")

        self.results["phases"]["phase5_performance_metrics"] = phase_result
        return phase_result

    def run_full_test(self) -> dict:
        """运行完整测试"""
        logger.info("🚀 开始全链路冒烟测试")
        logger.info("=" * 60)

        overall_start = time.time()

        # 依次执行各阶段
        self.phase1_model_loading()
        self.phase2_data_loading()
        self.phase3_feature_extraction()
        self.phase4_model_prediction()
        self.phase5_performance_metrics()

        # 计算总体状态
        all_ok = all(phase.get("status") == "OK" for phase in self.results["phases"].values())
        self.results["overall_status"] = "OK" if all_ok else "Fail"
        self.results["total_test_time_ms"] = round((time.time() - overall_start) * 1000, 2)

        logger.info("=" * 60)
        logger.info(f"📊 冒烟测试完成: {self.results['overall_status']}")
        logger.info(f"总耗时: {self.results['total_test_time_ms'] / 1000:.2f} 秒")
        logger.info("=" * 60)

        return self.results

    def print_report(self):
        """打印测试报告"""
        print("\n" + "=" * 70)
        print("📋 Docker 容器全链路冒烟测试报告")
        print("=" * 70)

        for phase_name, phase in self.results["phases"].items():
            status = phase.get("status", "Unknown")
            status_icon = "✅" if status == "OK" else "❌"
            time_ms = phase.get("total_time_ms", 0)

            print(f"\n{status_icon} {phase.get('name', phase_name)}: {status} ({time_ms}ms)")

            # 打印关键步骤
            for step_name, step in phase.get("steps", {}).items():
                step_status = step.get("status", "Unknown")
                print(f"   • {step_name}: {step_status}")

                # 打印关键指标
                for key, value in step.items():
                    if key != "status" and not key.endswith("_time"):
                        if isinstance(value, dict):
                            print(f"     - {key}: {list(value.keys())[:3]}...")
                        elif isinstance(value, list) and len(value) > 3:
                            print(f"     - {key}: {len(value)} items")
                        else:
                            print(f"     - {key}: {value}")

        # 打印总体指标
        print("\n" + "=" * 70)
        print("📈 关键指标摘要")
        print("=" * 70)

        phase5 = self.results["phases"].get("phase5_performance_metrics", {})
        metrics = phase5.get("metrics", {})

        for key, value in metrics.items():
            print(f"   • {key}: {value}")

        print("\n" + "=" * 70)
        print(f"总体状态: {self.results['overall_status']}")
        print(f"总测试时间: {self.results['total_test_time_ms'] / 1000:.2f} 秒")
        print("=" * 70 + "\n")

    def save_report(self, output_path: Path | None = None):
        """保存测试报告"""
        if output_path is None:
            output_path = Path("logs") / "docker_smoke_test_report.json"

        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)

        logger.info(f"📄 测试报告已保存: {output_path}")


def main():
    """主函数"""
    tester = SmokeTest()
    results = tester.run_full_test()
    tester.print_report()
    tester.save_report()

    return 0 if results["overall_status"] == "OK" else 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
