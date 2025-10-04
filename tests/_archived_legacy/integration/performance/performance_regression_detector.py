"""""""
Performance regression detection utility.

This script compares current performance metrics against established baselines
and detects performance regressions in the football prediction system.
"""""""

import json
import asyncio
import time
import statistics
from datetime import datetime
from typing import Dict, List, Any
from pathlib import Path
import logging

import psutil
import numpy as np

from tests.factories import FeatureFactory
from tests.mocks import MockRedisManager, MockPredictionService


class PerformanceRegressionDetector:
    """Detects performance regressions by comparing against baselines."""""""

    def __init__(self, baseline_file = str "tests/performance/baseline_metrics.json["):": self.baseline_file = Path(baseline_file)": self.baseline_metrics = self._load_baseline_metrics()": self.logger = logging.getLogger(__name__)"

    def _load_baseline_metrics(self) -> Dict[str, Any]:
        "]""Load baseline metrics from file."""""""
        try:
            if self.baseline_file.exists():
                with open(self.baseline_file, "r[") as f:": data = json.load(f)": return data.get("]metrics[", {})": else:": self.logger.warning(f["]Baseline file not found["]: [{self.baseline_file}])": return {}": except Exception as e:": self.logger.error(f["]Error loading baseline metrics["]: [{e}])": return {}": def _save_baseline_metrics(self, metrics: Dict[str, Any]) -> None:""
        "]""Save current metrics as new baseline."""""""
        baseline_data = {
            "timestamp[": datetime.now().isoformat(),""""
            "]metrics[": metrics,""""
            "]system_info[": {""""
                "]cpu_count[": psutil.cpu_count(),""""
                "]memory_total_gb[": psutil.virtual_memory().total / (1024**3),""""
                "]python_version[": f["]{psutil.python_version()}"],""""
                "platform[": str(psutil.Platform.uname()),""""
            },
            "]test_configuration[": {""""
                "]benchmark_rounds[": 50,""""
                "]warmup_rounds[": 5,""""
                "]timeout_seconds[": 30,""""
            },
        }

        try:
            with open(self.baseline_file, "]w[") as f:": json.dump(baseline_data, f, indent=2)": self.logger.info(f["]Baseline metrics saved to {self.baseline_file}"])": except Exception as e:": self.logger.error(f["Error saving baseline metrics["]: [{e}])"]": async def measure_single_prediction_performance(": self, num_samples = int 50"
    ) -> Dict[str, float]:
        """Measure single prediction performance."""""""
        services = {"prediction_service[" : MockPredictionService()}": response_times = []": for i in range(num_samples):": features = ("
                FeatureFactory.generate_comprehensive_features(num_samples=1)
                .iloc[0]
                .to_dict()
            )
            features["]match_id["] = 15000 + i[": start_time = time.time()": await services["]]prediction_service["].predict_match_outcome(": features["""
            )
            response_time = (time.time() - start_time) * 1000  # Convert to ms
            response_times.append(response_time)

        return {
            "]]mean_ms[": statistics.mean(response_times),""""
            "]std_ms[": (": statistics.stdev(response_times) if len(response_times) > 1 else 0["""
            ),
            "]]median_ms[": statistics.median(response_times),""""
            "]min_ms[": min(response_times),""""
            "]max_ms[": max(response_times),""""
            "]p95_ms[": np.percentile(response_times, 95),""""
            "]p99_ms[": np.percentile(response_times, 99),""""
            "]samples[": num_samples,""""
        }

    async def measure_batch_prediction_performance(
        self, batch_sizes: List[int] = None
    ) -> Dict[str, float]:
        "]""Measure batch prediction performance."""""""
        if batch_sizes is None = batch_sizes [1, 5, 10, 20, 50]

        services = {"prediction_service[" : MockPredictionService()}": results = {}": for batch_size in batch_sizes = features_list []": for i in range(batch_size):"
                features = (
                    FeatureFactory.generate_comprehensive_features(num_samples=1)
                    .iloc[0]
                    .to_dict()
                )
                features["]match_id["] = 15100 + i[": features_list.append(features)": response_times = []": for _ in range(20):  # 20 iterations per batch size"
                start_time = time.time()
                await services["]]prediction_service["].batch_predict(": features_list["""
                )
                response_time = time.time() - start_time
                response_times.append(response_time)

            avg_time = statistics.mean(response_times)
            results[f["]]batch_{batch_size}_mean_ms["]] = avg_time * 1000[": results[f["]]batch_{batch_size}_pps["]] = batch_size / avg_time[": return results[": async def measure_cache_performance(": self, num_samples = int 100"
    ) -> Dict[str, float]:
        "]]]""Measure cache read/write performance."""""""
        services = {"redis[" : MockRedisManager()}""""

        # Test cache write performance
        write_times = []
        for i in range(num_samples):
            test_data = {"]prediction[: "home_win"", "confidence] : 0.85}": cache_key = f["perf_test_{i}"]": start_time = time.time()": await services["redis["].set(cache_key, test_data, ttl=300)": write_time = (time.time() - start_time) * 1000[": write_times.append(write_time)""

        # Test cache read performance
        read_times = []
        for i in range(num_samples):
            cache_key = f["]]perf_test_{i}"]: start_time = time.time()": await services["redis["].get(cache_key)": read_time = (time.time() - start_time) * 1000[": read_times.append(read_time)": return {"
            "]]write_mean_ms[": statistics.mean(write_times),""""
            "]write_std_ms[": (": statistics.stdev(write_times) if len(write_times) > 1 else 0["""
            ),
            "]]read_mean_ms[": statistics.mean(read_times),""""
            "]read_std_ms[": statistics.stdev(read_times) if len(read_times) > 1 else 0,""""
            "]samples[": num_samples,""""
        }

    async def measure_memory_usage(
        self, prediction_volumes: List[int] = None
    ) -> Dict[str, float]:
        "]""Measure memory usage scaling."""""""
        if prediction_volumes is None = prediction_volumes [10, 50, 100, 500, 1000]

        process = psutil.Process()
        memory_results = {}

        for volume in prediction_volumes:
            # Clear memory before test
            initial_memory = process.memory_info().rss / 1024 / 1024  # MB

            # Generate and process predictions
            features = FeatureFactory.generate_comprehensive_features(
                num_samples=volume
            )

            # Simulate prediction processing
            predictions = []
            for _, row in features.iterrows():
                prediction = {
                    "match_id[": row.get("]match_id[", 0),""""
                    "]home_win_prob[": 0.5,""""
                    "]draw_prob[": 0.3,""""
                    "]away_win_prob[": 0.2,""""
                }
                predictions.append(prediction)

            final_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_increase = final_memory - initial_memory

            memory_results[f["]memory_{volume}_predictions_mb["]] = memory_increase[": memory_results[f["]]memory_{volume}_per_prediction_mb["]] = (": memory_increase / volume["""
            )

            # Clean up
            del features
            del predictions

        return memory_results

    async def measure_concurrent_performance(
        self, concurrent_levels: List[int] = None
    ) -> Dict[str, float]:
        "]]""Measure concurrent prediction performance."""""""
        if concurrent_levels is None = concurrent_levels [5, 10, 20, 50]

        services = {"prediction_service[" : MockPredictionService()}": results = {}": for concurrent_count in concurrent_levels = features_list []": for i in range(concurrent_count):"
                features = (
                    FeatureFactory.generate_comprehensive_features(num_samples=1)
                    .iloc[0]
                    .to_dict()
                )
                features["]match_id["] = 15200 + i[": features_list.append(features)"""

            # Create concurrent tasks
            tasks = [
                services["]]prediction_service["].predict_match_outcome(features)": for features in features_list["""
            ]

            # Measure concurrent execution
            start_time = time.time()
            await asyncio.gather(*tasks)
            total_time = time.time() - start_time

            results[f["]]concurrent_{concurrent_count}_total_time_ms["]] = total_time * 1000[": results[f["]]concurrent_{concurrent_count}_pps["]] = (": concurrent_count / total_time["""
            )

        return results

    def detect_regressions(
        self, current_metrics: Dict[str, float]
    ) -> List[Dict[str, Any]]:
        "]]""Detect performance regressions by comparing with baselines."""""""
        regressions = []

        # Define regression thresholds (percentage increase from baseline)
        regression_thresholds = {
            "single_prediction_mean_ms[": 0.20,  # 20% increase[""""
            "]]batch_predictions_per_second[": -0.15,  # 15% decrease[""""
            "]]cache_read_mean_ms[": 0.30,  # 30% increase[""""
            "]]memory_usage_per_100_predictions_mb[": 0.25,  # 25% increase[""""
        }

        for metric_name, threshold in regression_thresholds.items():
            if metric_name in self.baseline_metrics and metric_name in current_metrics = baseline_value self.baseline_metrics[metric_name]
                current_value = current_metrics[metric_name]

                if baseline_value > 0:  # Avoid division by zero
                    change_ratio = (current_value - baseline_value) / baseline_value

                    # Check for regression
                    if (threshold > 0 and change_ratio > threshold) or (
                        threshold < 0 and change_ratio < threshold
                    ):
                        regressions.append(
                            {
                                "]]metric[": metric_name,""""
                                "]baseline_value[": baseline_value,""""
                                "]current_value[": current_value,""""
                                "]change_ratio[": change_ratio,""""
                                "]threshold[": threshold,""""
                                "]severity[": (""""
                                    "]high[" "]: "if abs(change_ratio) > 0.5 else "medium["""""
                                ),
                            }
                        )

        return regressions

    async def run_full_performance_analysis(self) -> Dict[str, Any]:
        "]""Run complete performance analysis and regression detection."""""""
        self.logger.info("Starting comprehensive performance analysis...")""""

        # Collect current metrics
        single_pred_metrics = await self.measure_single_prediction_performance()
        batch_pred_metrics = await self.measure_batch_prediction_performance()
        cache_metrics = await self.measure_cache_performance()
        memory_metrics = await self.measure_memory_usage()
        concurrent_metrics = await self.measure_concurrent_performance()

        # Combine all metrics
        current_metrics = {}
        current_metrics.update(single_pred_metrics)
        current_metrics.update(batch_pred_metrics)
        current_metrics.update(cache_metrics)
        current_metrics.update(memory_metrics)
        current_metrics.update(concurrent_metrics)

        # Add memory per prediction metric for baseline comparison
        if "memory_100_predictions_mb[": in current_metrics:": current_metrics["]memory_usage_per_100_predictions_mb["] = current_metrics[""""
                "]memory_100_predictions_mb["""""
            ]

        # Extract key batch prediction metric
        batch_pps_metrics = {
            k: v for k, v in current_metrics.items() if "]pps[" "]: "in k and "batch[": in k[""""
        }
        if batch_pps_metrics:
            current_metrics["]]batch_predictions_per_second["] = list(": batch_pps_metrics.values()"""
            )[
                0
            ]  # Use first batch size

        # Detect regressions
        regressions = self.detect_regressions(current_metrics)

        # Generate report
        report = {
            "]timestamp[": datetime.now().isoformat(),""""
            "]baseline_timestamp[": self.baseline_metrics.get("]timestamp[", "]unknown["),""""
            "]current_metrics[": current_metrics,""""
            "]baseline_metrics[": self.baseline_metrics,""""
            "]regressions[": regressions,""""
            "]summary[": {""""
                "]total_metrics_tested[": len(current_metrics),""""
                "]regressions_detected[": len(regressions),""""
                "]regression_severity[": (""""
                    "]high["""""
                    : if any(r["]severity["] =="]high[" : for r in regressions)": else "]medium[" "]: "if regressions else "none["""""
                ),
            },
        }

        # Save report
        report_file = Path("]tests/performance/performance_report.json[")": try:": with open(report_file, "]w[") as f:": json.dump(report, f, indent=2)": self.logger.info(f["]Performance report saved to {report_file}"])": except Exception as e:": self.logger.error(f["Error saving performance report["]: [{e}])"]"""

        # Log summary
        if regressions:
            self.logger.warning(f["Performance regressions detected["]: [{len(regressions)}])"]": for regression in regressions:": self.logger.warning("
                    f["  - {regression['metric']}: {regression['change_ratio']:.1%} change["]"]"""
                )
        else:
            self.logger.info("No performance regressions detected[")": return report[": async def update_baselines(self) -> None:""
        "]]""Update baseline metrics with current performance."""""""
        self.logger.info("Updating performance baselines...")""""

        # Collect comprehensive metrics
        single_pred_metrics = await self.measure_single_prediction_performance()
        batch_pred_metrics = await self.measure_batch_prediction_performance()
        cache_metrics = await self.measure_cache_performance()
        memory_metrics = await self.measure_memory_usage()

        # Create baseline metrics
        baseline_metrics = {}
        baseline_metrics.update(single_pred_metrics)
        baseline_metrics.update(batch_pred_metrics)
        baseline_metrics.update(cache_metrics)
        baseline_metrics.update(memory_metrics)

        # Add memory per prediction metric
        if "memory_100_predictions_mb[": in baseline_metrics:": baseline_metrics["]memory_usage_per_100_predictions_mb["] = baseline_metrics[""""
                "]memory_100_predictions_mb["""""
            ]

        # Extract key batch prediction metric
        batch_pps_metrics = {
            k: v for k, v in baseline_metrics.items() if "]pps[" "]: "in k and "batch[": in k[""""
        }
        if batch_pps_metrics:
            baseline_metrics["]]batch_predictions_per_second["] = list(": batch_pps_metrics.values()"""
            )[0]

        # Save new baselines
        self._save_baseline_metrics(baseline_metrics)


async def main():
    "]""Main function to run performance regression detection."""""""
    logging.basicConfig(level=logging.INFO)

    detector = PerformanceRegressionDetector()

    # Run performance analysis
    report = await detector.run_full_performance_analysis()

    # Print summary
    print("\n[" + "]=" * 50)": print("PERFORMANCE REGRESSION ANALYSIS SUMMARY[")": print("]=" * 50)": print(f["Test Run: {report['timestamp']}"])": print(f["Baseline: {report['baseline_timestamp']}"])": print(f["Metrics Tested: {report['summary']['total_metrics_tested']}"])": print(f["Regressions Detected: {report['summary']['regressions_detected']}"])": print(f["Severity: {report['summary']['regression_severity'].upper()}"])": if report["regressions["]:": print("]\nREGRESSIONS FOUND:")": for regression in report["regressions["]:": print(": f["]  - {regression['metric']}: {regression['change_ratio']:+.1%} "]: f["(threshold: {regression['threshold']:+.1%})"]""""
            )
    else:
        print("\n✅ No performance regressions detected!")": print("\nDetailed report saved to[": [tests/performance/performance_report.json])": if __name__ =="]__main__[":"]"""
    : asyncio.run(main())
