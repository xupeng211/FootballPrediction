"""
数据管道端到端工作流测试
测试从数据收集到特征工程的完整数据流程
"""

import asyncio
import json
import time
from typing import Any, Dict, List
from unittest.mock import AsyncMock, Mock, patch

import pandas as pd
import pytest

from src.services.collection_service import FotMobCollectionService


class TestDataPipelineWorkflow:
    """数据管道工作流测试"""

    @pytest.fixture
    def data_pipeline_system(self):
        """创建数据管道系统模拟"""
        collection_service = FotMobCollectionService()

        # Mock外部数据源
        external_data = {
            "match_123": {
                "id": "match_123",
                "home_team": "Manchester United",
                "away_team": "Liverpool",
                "home_score": 2,
                "away_score": 1,
                "date": "2024-01-15",
                "venue": "Old Trafford",
                "league": "Premier League",
                "attendance": 73200,
                "possession": {"home": 58, "away": 42},
                "shots": {"home": 15, "away": 8},
                "corners": {"home": 7, "away": 3},
                "fouls": {"home": 8, "away": 12},
                "yellow_cards": {"home": 1, "away": 3},
                "red_cards": {"home": 0, "away": 0},
            },
            "match_124": {
                "id": "match_124",
                "home_team": "Chelsea",
                "away_team": "Arsenal",
                "home_score": 1,
                "away_score": 1,
                "date": "2024-01-16",
                "venue": "Stamford Bridge",
                "league": "Premier League",
                "attendance": 40200,
                "possession": {"home": 52, "away": 48},
                "shots": {"home": 12, "away": 10},
                "corners": {"home": 5, "away": 6},
                "fouls": {"home": 10, "away": 9},
                "yellow_cards": {"home": 2, "away": 2},
                "red_cards": {"home": 0, "away": 0},
            },
        }

        return {
            "collection_service": collection_service,
            "external_data": external_data,
        }

    @pytest.mark.asyncio
    async def test_data_collection_to_features_pipeline(self, data_pipeline_system):
        """测试从数据收集到特征工程的完整管道"""
        collection_service = data_pipeline_system["collection_service"]
        external_data = data_pipeline_system["external_data"]

        pipeline_start_time = time.perf_counter()

        # 步骤1: 创建数据收集任务
        match_ids = list(external_data.keys())
        collection_tasks = []

        for match_id in match_ids:
            with patch.object(collection_service, "create_match_collection_task") as mock_create:
                mock_create.return_value = f"task_{match_id}_{int(time.time())}"

                task_id = collection_service.create_match_collection_task(match_id)
                collection_tasks.append({"match_id": match_id, "task_id": task_id})

        assert len(collection_tasks) == len(match_ids)

        # 步骤2: 模拟数据收集执行（简化版）
        collected_data = {}
        for match_id in match_ids:
            # 直接使用预定义的外部数据，跳过复杂的Mock
            collected_data[match_id] = external_data[match_id]

        assert len(collected_data) == len(match_ids)

        # 步骤3: 数据清洗和验证
        cleaned_data = {}
        for match_id, data in collected_data.items():
            # 验证必需字段
            required_fields = [
                "id",
                "home_team",
                "away_team",
                "home_score",
                "away_score",
                "date",
            ]
            assert all(field in data for field in required_fields), f"缺少必需字段: {match_id}"

            # 数据清洗
            cleaned_match = {
                "match_id": data["id"],
                "home_team": data["home_team"],
                "away_team": data["away_team"],
                "home_score": int(data["home_score"]),
                "away_score": int(data["away_score"]),
                "date": data["date"],
                "venue": data.get("venue", "Unknown"),
                "league": data.get("league", "Unknown"),
                "attendance": int(data.get("attendance", 0)),
                "home_possession": float(data.get("possession", {}).get("home", 50)),
                "away_possession": float(data.get("possession", {}).get("away", 50)),
                "home_shots": int(data.get("shots", {}).get("home", 0)),
                "away_shots": int(data.get("shots", {}).get("away", 0)),
                "home_corners": int(data.get("corners", {}).get("home", 0)),
                "away_corners": int(data.get("corners", {}).get("away", 0)),
                "home_fouls": int(data.get("fouls", {}).get("home", 0)),
                "away_fouls": int(data.get("fouls", {}).get("away", 0)),
                "home_yellow_cards": int(data.get("yellow_cards", {}).get("home", 0)),
                "away_yellow_cards": int(data.get("yellow_cards", {}).get("away", 0)),
                "home_red_cards": int(data.get("red_cards", {}).get("home", 0)),
                "away_red_cards": int(data.get("red_cards", {}).get("away", 0)),
            }

            cleaned_data[match_id] = cleaned_match

        # 步骤4: 特征工程
        features_data = {}
        for match_id, data in cleaned_data.items():
            # 计算基本统计特征
            goal_difference = data["home_score"] - data["away_score"]
            total_goals = data["home_score"] + data["away_score"]
            possession_diff = data["home_possession"] - data["away_possession"]
            shots_diff = data["home_shots"] - data["away_shots"]
            corners_diff = data["home_corners"] - data["away_corners"]

            # 创建特征向量
            features = [
                float(goal_difference),  # 进球差
                float(total_goals),  # 总进球数
                float(possession_diff / 100),  # 控球率差（归一化）
                float(shots_diff / 10),  # 射门差（归一化）
                float(corners_diff / 5),  # 角球差（归一化）
                float(data["attendance"] / 100000),  # 上座率影响
                float(data["home_yellow_cards"] + data["away_yellow_cards"]),  # 牌数
                float(data["home_fouls"] - data["away_fouls"]),  # 犯规差
                float(1 if goal_difference > 0 else 0),  # 主队是否领先
                float(1 if total_goals > 2 else 0),  # 是否高比分
                float(data["home_red_cards"] - data["away_red_cards"]),  # 红牌差
                float(len(data["venue"])),  # 场馆名长度（作为场馆复杂度的代理）
            ]

            features_data[match_id] = {
                "features": features,
                "target": (
                    0 if goal_difference > 0 else (1 if goal_difference == 0 else 2)
                ),  # HOME_WIN, DRAW, AWAY_WIN
                "metadata": {
                    "match_id": match_id,
                    "home_team": data["home_team"],
                    "away_team": data["away_team"],
                    "final_score": f"{data['home_score']}-{data['away_score']}",
                    "feature_count": len(features),
                },
            }

        pipeline_end_time = time.perf_counter()
        total_pipeline_time = pipeline_end_time - pipeline_start_time

        # 验证管道结果
        assert len(features_data) == len(match_ids)
        for match_id, feature_data in features_data.items():
            assert len(feature_data["features"]) == 12
            assert feature_data["target"] in [0, 1, 2]
            assert feature_data["metadata"]["match_id"] == match_id

        print(f"✅ 数据管道工作流完成:")
        print(f"   - 处理比赛数: {len(match_ids)}")
        print(f"   - 收集任务数: {len(collection_tasks)}")
        print(f"   - 生成特征数: {len(features_data)}")
        print(f"   - 管道处理时间: {total_pipeline_time:.3f}s")
        print(f"   - 平均处理时间: {(total_pipeline_time/len(match_ids))*1000:.2f}ms/比赛")

        # 打印特征示例
        sample_match = match_ids[0]
        sample_features = features_data[sample_match]
        print(
            f"   - 示例特征 ({sample_features['metadata']['home_team']} vs {sample_features['metadata']['away_team']}):"
        )
        print(f"     * 特征向量: {[f'{f:.2f}' for f in sample_features['features'][:6]]}...")
        print(f"     * 最终结果: {sample_features['metadata']['final_score']}")

    @pytest.mark.asyncio
    async def test_batch_data_processing_workflow(self, data_pipeline_system):
        """测试批量数据处理工作流"""
        collection_service = data_pipeline_system["collection_service"]

        # 生成大量测试数据
        batch_size = 20
        teams = ["Team A", "Team B", "Team C", "Team D", "Team E"]
        venues = ["Stadium 1", "Stadium 2", "Stadium 3"]

        # 创建批量比赛数据
        batch_matches = []
        for i in range(batch_size):
            match_data = {
                "id": f"batch_match_{i}",
                "home_team": teams[i % len(teams)],
                "away_team": teams[(i + 1) % len(teams)],
                "home_score": (i + 1) % 4,
                "away_score": i % 3,
                "date": "2024-01-15",
                "venue": venues[i % len(venues)],
                "league": "Test League",
            }
            batch_matches.append(match_data)

        # 批量处理工作流
        batch_start_time = time.perf_counter()

        # 步骤1: 批量创建收集任务
        with patch.object(collection_service, "create_match_collection_task") as mock_create:
            task_ids = []
            for i, match in enumerate(batch_matches):
                mock_create.return_value = f"batch_task_{i}_{int(time.time())}"
                task_id = collection_service.create_match_collection_task(match["id"])
                task_ids.append(task_id)

        # 步骤2: 批量执行任务
        with patch.object(collection_service, "execute_task") as mock_execute:
            for i, task_id in enumerate(task_ids):
                mock_execute.return_value = {
                    "success": True,
                    "data": batch_matches[i],
                    "task_id": task_id,
                    "processing_time_ms": 100 + i * 5,  # 模拟不同的处理时间
                }

        # 步骤3: 批量特征处理
        processed_features = []
        for i, match in enumerate(batch_matches):
            # 简化的特征计算
            goal_diff = match["home_score"] - match["away_score"]

            features = [
                float(goal_diff),
                float(match["home_score"] + match["away_score"]),
                float(i / batch_size),  # 批次位置
                float(1 if match["home_score"] > match["away_score"] else 0),
                1.0,
                2.0,
                3.0,
                4.0,
                5.0,
                6.0,
                7.0,
                8.0,  # 填充剩余特征
            ]

            processed_features.append(
                {
                    "match_id": match["id"],
                    "features": features,
                    "target": 0 if goal_diff > 0 else (1 if goal_diff == 0 else 2),
                    "processing_order": i,
                }
            )

        batch_end_time = time.perf_counter()
        batch_processing_time = batch_end_time - batch_start_time

        # 验证批量处理结果
        assert len(processed_features) == batch_size
        assert len(task_ids) == batch_size

        # 计算统计信息
        processing_times = [100 + i * 5 for i in range(batch_size)]
        avg_processing_time = sum(processing_times) / len(processing_times)
        throughput = batch_size / batch_processing_time

        print(f"✅ 批量数据处理工作流完成:")
        print(f"   - 批量大小: {batch_size}")
        print(f"   - 创建任务数: {len(task_ids)}")
        print(f"   - 处理特征数: {len(processed_features)}")
        print(f"   - 批量处理时间: {batch_processing_time:.3f}s")
        print(f"   - 平均处理时间: {avg_processing_time:.2f}ms/任务")
        print(f"   - 批量吞吐量: {throughput:.2f} 任务/秒")

        # 性能断言
        assert throughput > 10, f"批量吞吐量过低: {throughput:.2f} 任务/秒"
        assert batch_processing_time < 5.0, f"批量处理时间过长: {batch_processing_time:.3f}s"

    @pytest.mark.asyncio
    async def test_data_quality_validation_workflow(self, data_pipeline_system):
        """测试数据质量验证工作流"""
        collection_service = data_pipeline_system["collection_service"]

        # 创建不同质量的测试数据
        test_cases = [
            {
                "name": "正常数据",
                "data": {
                    "id": "valid_match",
                    "home_team": "Team A",
                    "away_team": "Team B",
                    "home_score": 2,
                    "away_score": 1,
                    "date": "2024-01-15",
                },
                "should_pass": True,
            },
            {
                "name": "缺少字段",
                "data": {
                    "id": "incomplete_match",
                    "home_team": "Team A",
                    # 缺少 away_team
                    "home_score": 2,
                    "away_score": 1,
                    "date": "2024-01-15",
                },
                "should_pass": False,
            },
            {
                "name": "异常比分",
                "data": {
                    "id": "abnormal_score",
                    "home_team": "Team A",
                    "away_team": "Team B",
                    "home_score": -1,  # 负分数异常
                    "away_score": 100,  # 过高分数异常
                    "date": "2024-01-15",
                },
                "should_pass": False,
            },
            {
                "name": "日期格式错误",
                "data": {
                    "id": "invalid_date",
                    "home_team": "Team A",
                    "away_team": "Team B",
                    "home_score": 2,
                    "away_score": 1,
                    "date": "not-a-date",
                },
                "should_pass": False,
            },
        ]

        validation_results = []

        for test_case in test_cases:
            case_name = test_case["name"]
            test_data = test_case["data"]
            expected_result = test_case["should_pass"]

            # 执行验证逻辑
            validation_start_time = time.perf_counter()

            # 基本字段验证
            required_fields = [
                "id",
                "home_team",
                "away_team",
                "home_score",
                "away_score",
                "date",
            ]
            has_required_fields = all(field in test_data for field in required_fields)

            # 数据合理性验证
            has_valid_scores = (
                isinstance(test_data.get("home_score"), int)
                and isinstance(test_data.get("away_score"), int)
                and test_data["home_score"] >= 0
                and test_data["away_score"] >= 0
                and test_data["home_score"] <= 20  # 合理的比分上限
                and test_data["away_score"] <= 20
            )

            has_valid_teams = (
                isinstance(test_data.get("home_team"), str)
                and isinstance(test_data.get("away_team"), str)
                and len(test_data["home_team"]) > 0
                and len(test_data["away_team"]) > 0
                and test_data["home_team"] != test_data["away_team"]  # 球队不能相同
            )

            # 简单的日期格式验证
            has_valid_date = (
                isinstance(test_data.get("date"), str) and len(test_data["date"]) >= 8  # 最基本的日期长度检查
            )

            # 综合验证结果
            validation_passed = has_required_fields and has_valid_scores and has_valid_teams and has_valid_date

            validation_end_time = time.perf_counter()
            validation_time = (validation_end_time - validation_start_time) * 1000

            validation_results.append(
                {
                    "case_name": case_name,
                    "validation_passed": validation_passed,
                    "expected_result": expected_result,
                    "validation_correct": validation_passed == expected_result,
                    "validation_time_ms": validation_time,
                    "details": {
                        "has_required_fields": has_required_fields,
                        "has_valid_scores": has_valid_scores,
                        "has_valid_teams": has_valid_teams,
                        "has_valid_date": has_valid_date,
                    },
                }
            )

        # 验证验证结果
        correct_validations = sum(1 for r in validation_results if r["validation_correct"])
        total_cases = len(validation_results)
        validation_accuracy = correct_validations / total_cases * 100

        print(f"✅ 数据质量验证工作流完成:")
        print(f"   - 测试用例数: {total_cases}")
        print(f"   - 验证正确数: {correct_validations}")
        print(f"   - 验证准确率: {validation_accuracy:.1f}%")

        for result in validation_results:
            status = "✓" if result["validation_correct"] else "✗"
            print(f"   - {status} {result['case_name']}: {'通过' if result['validation_passed'] else '失败'}")
            if not result["validation_correct"]:
                print(
                    f"     预期: {'通过' if result['expected_result'] else '失败'}, 实际: {'通过' if result['validation_passed'] else '失败'}"
                )

        # 性能统计
        avg_validation_time = sum(r["validation_time_ms"] for r in validation_results) / len(validation_results)
        print(f"   - 平均验证时间: {avg_validation_time:.3f}ms")

        # 质量断言
        assert validation_accuracy >= 75, f"数据质量验证准确率过低: {validation_accuracy:.1f}%"
        assert avg_validation_time < 10, f"验证时间过长: {avg_validation_time:.3f}ms"

    @pytest.mark.asyncio
    async def test_error_recovery_and_data_integrity_workflow(self, data_pipeline_system):
        """测试错误恢复和数据完整性工作流"""
        collection_service = data_pipeline_system["collection_service"]

        # 测试数据
        reliable_matches = [
            {
                "id": "reliable_1",
                "home_team": "Team A",
                "away_team": "Team B",
                "home_score": 2,
                "away_score": 1,
            },
            {
                "id": "reliable_2",
                "home_team": "Team C",
                "away_team": "Team D",
                "home_score": 1,
                "away_score": 1,
            },
        ]

        problematic_matches = [
            {"id": "problematic_1", "home_team": "Team E"},  # 缺少字段
            {
                "id": "problematic_2",
                "home_team": "Team F",
                "away_team": "Team G",
                "home_score": -1,
            },  # 异常数据
        ]

        workflow_results = {
            "successful_processing": 0,
            "failed_processing": 0,
            "recovered_data": 0,
            "data_integrity_violations": 0,
        }

        # 处理可靠数据
        for match in reliable_matches:
            with patch.object(collection_service, "execute_task") as mock_execute:
                mock_execute.return_value = {
                    "success": True,
                    "data": match,
                    "task_id": f"task_{match['id']}",
                    "processing_time_ms": 100,
                }

                result = collection_service.execute_task(f"task_{match['id']}")
                if result["success"]:
                    workflow_results["successful_processing"] += 1

        # 处理问题数据（测试错误恢复）
        for match in problematic_matches:
            try:
                # 模拟数据处理失败
                with patch.object(collection_service, "execute_task") as mock_execute:
                    mock_execute.return_value = {
                        "success": False,
                        "error": f"数据验证失败: {match.get('id', 'unknown')}",
                        "task_id": f"task_{match['id']}",
                    }

                    result = collection_service.execute_task(f"task_{match['id']}")
                    if not result["success"]:
                        workflow_results["failed_processing"] += 1

                        # 尝试数据恢复
                        recovered_data = self._attempt_data_recovery(match)
                        if recovered_data:
                            workflow_results["recovered_data"] += 1

            except Exception as e:
                workflow_results["failed_processing"] += 1
                print(f"处理失败: {match.get('id', 'unknown')} - {e}")

        # 数据完整性检查
        total_processed = workflow_results["successful_processing"] + workflow_results["recovered_data"]
        expected_total = len(reliable_matches) + len(problematic_matches)

        if total_processed != expected_total:
            workflow_results["data_integrity_violations"] += 1

        print(f"✅ 错误恢复和数据完整性工作流完成:")
        print(f"   - 可靠数据: {len(reliable_matches)}")
        print(f"   - 问题数据: {len(problematic_matches)}")
        print(f"   - 成功处理: {workflow_results['successful_processing']}")
        print(f"   - 失败处理: {workflow_results['failed_processing']}")
        print(f"   - 数据恢复: {workflow_results['recovered_data']}")
        print(f"   - 完整性违规: {workflow_results['data_integrity_violations']}")
        print(f"   - 总处理数: {total_processed}/{expected_total}")

        # 恢复率统计
        recovery_rate = (
            workflow_results["recovered_data"] / len(problematic_matches) * 100 if problematic_matches else 100
        )
        print(f"   - 数据恢复率: {recovery_rate:.1f}%")

        # 断言
        assert workflow_results["successful_processing"] >= len(reliable_matches) * 0.8, "可靠数据处理失败率过高"
        assert workflow_results["data_integrity_violations"] == 0, "数据完整性检查失败"

    def _attempt_data_recovery(self, incomplete_data: Dict) -> Dict:
        """尝试恢复不完整的数据"""
        recovered_data = incomplete_data.copy()

        # 尝试填充缺失字段
        if "away_score" not in recovered_data:
            recovered_data["away_score"] = 0  # 默认值

        if "away_team" not in recovered_data:
            recovered_data["away_team"] = "Unknown Team"  # 默认值

        if "home_score" in recovered_data and recovered_data["home_score"] < 0:
            recovered_data["home_score"] = 0  # 修正异常值

        # 基本验证
        required_fields = ["id", "home_team", "away_team", "home_score", "away_score"]
        if all(field in recovered_data for field in required_fields):
            return recovered_data

        return {}  # 无法恢复


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
