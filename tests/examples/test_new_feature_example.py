"""
新功能测试示例
New Feature Test Example

展示如何为新功能编写符合最佳实践的测试。

假设我们要添加一个新的功能：计算球队的连胜纪录。

功能描述：
- 输入：球队名称和最近的比赛结果列表
- 输出：最长连胜纪录（连胜/连平/连败）
"""

import pytest
from unittest.mock import patch, Mock
from datetime import datetime, timedelta
import sys
import os

# 添加src到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../src"))

# 假设这是我们要测试的新功能
# from src.services.team_stats import TeamStatsService
# from src.models.team import Team

# 为了演示，我们创建一个简单的实现
class TeamStatsService:
    """球队统计服务"""

    @staticmethod
    def calculate_streak(team_name: str, matches: list) -> dict:
        """计算球队的连胜/连败纪录"""
        if not matches:
            return {"team": team_name, "win_streak": 0, "draw_streak": 0, "loss_streak": 0}

        # 初始化纪录
        max_win_streak = max_draw_streak = max_loss_streak = 0
        current_win_streak = current_draw_streak = current_loss_streak = 0

        for match in matches:
            # 查找球队在该场比赛的结果
            result = None
            if match.get("home_team") == team_name:
                if match["home_score"] > match["away_score"]:
                    result = "win"
                elif match["home_score"] == match["away_score"]:
                    result = "draw"
                else:
                    result = "loss"
            elif match.get("away_team") == team_name:
                if match["away_score"] > match["home_score"]:
                    result = "win"
                elif match["away_score"] == match["home_score"]:
                    result = "draw"
                else:
                    result = "loss"

            # 更新当前纪录
            if result == "win":
                current_win_streak += 1
                current_draw_streak = 0
                current_loss_streak = 0
                max_win_streak = max(max_win_streak, current_win_streak)
            elif result == "draw":
                current_draw_streak += 1
                current_win_streak = 0
                current_loss_streak = 0
                max_draw_streak = max(max_draw_streak, current_draw_streak)
            elif result == "loss":
                current_loss_streak += 1
                current_win_streak = 0
                current_draw_streak = 0
                max_loss_streak = max(max_loss_streak, current_loss_streak)

        return {
            "team": team_name,
            "win_streak": max_win_streak,
            "draw_streak": max_draw_streak,
            "loss_streak": max_loss_streak
        }


@pytest.mark.unit
class TestTeamStatsService:
    """球队统计服务测试类"""

    # ======== 基本功能测试 ========

    def test_calculate_streak_with_winning_team_returns_correct_streaks(self):
        """
        测试：计算连胜球队的纪录返回正确的连胜数据

        测试场景：
        - 输入：5场全胜的比赛
        - 期望：5连胜，0连平，0连败
        """
        # Arrange
        team_name = "Winning Team"
        matches = [
            {"home_team": team_name, "away_team": "Team B", "home_score": 2, "away_score": 1},
            {"home_team": "Team C", "away_team": team_name, "home_score": 0, "away_score": 3},
            {"home_team": team_name, "away_team": "Team D", "home_score": 1, "away_score": 0},
            {"home_team": "Team E", "away_team": team_name, "home_score": 1, "away_score": 2},
            {"home_team": team_name, "away_team": "Team F", "home_score": 3, "away_score": 1},
        ]

        # Act
        result = TeamStatsService.calculate_streak(team_name, matches)

        # Assert
        assert result == {
            "team": team_name,
            "win_streak": 5,
            "draw_streak": 0,
            "loss_streak": 0
        }, f"Expected 5 win streak, got {result}"

    def test_calculate_streak_with_mixed_results_returns_correct_streaks(self):
        """
        测试：计算混合结果的纪录返回正确的数据

        测试场景：
        - 输入：胜-胜-平-负-胜-平-平-负-负-负
        - 期望：2连胜，2连平，3连败
        """
        # Arrange
        team_name = "Mixed Team"
        matches = [
            {"home_team": team_name, "away_team": "Team B", "home_score": 2, "away_score": 1},  # 胜
            {"home_team": team_name, "away_team": "Team C", "home_score": 1, "away_score": 0},  # 胜 (2连胜)
            {"home_team": team_name, "away_team": "Team D", "home_score": 1, "away_score": 1},  # 平
            {"home_team": team_name, "away_team": "Team E", "home_score": 0, "away_score": 1},  # 负
            {"home_team": team_name, "away_team": "Team F", "home_score": 2, "away_score": 1},  # 胜
            {"home_team": team_name, "away_team": "Team G", "home_score": 1, "away_score": 1},  # 平 (2连平)
            {"home_team": team_name, "away_team": "Team H", "home_score": 0, "away_score": 0},  # 平
            {"home_team": team_name, "away_team": "Team I", "home_score": 1, "away_score": 2},  # 负
            {"home_team": team_name, "away_team": "Team J", "home_score": 0, "away_score": 1},  # 负
            {"home_team": team_name, "away_team": "Team K", "home_score": 0, "away_score": 2},  # 负 (3连败)
        ]

        # Act
        result = TeamStatsService.calculate_streak(team_name, matches)

        # Assert
        assert result["team"] == team_name
        assert result["win_streak"] == 2, f"Expected 2 win streak, got {result['win_streak']}"
        assert result["draw_streak"] == 2, f"Expected 2 draw streak, got {result['draw_streak']}"
        assert result["loss_streak"] == 3, f"Expected 3 loss streak, got {result['loss_streak']}"

    # ======== 边界条件测试 ========

    def test_calculate_streak_with_empty_matches_returns_zero_streaks(self):
        """
        测试：空的比赛列表返回零连胜纪录

        测试场景：
        - 输入：空的比赛列表
        - 期望：所有纪录都是0
        """
        # Arrange
        team_name = "Empty Team"
        matches = []

        # Act
        result = TeamStatsService.calculate_streak(team_name, matches)

        # Assert
        assert result == {
            "team": team_name,
            "win_streak": 0,
            "draw_streak": 0,
            "loss_streak": 0
        }

    def test_calculate_streak_with_team_not_in_matches_returns_zero_streaks(self):
        """
        测试：球队不在比赛列表中返回零连胜纪录

        测试场景：
        - 输入：球队名称不在任何比赛中出现
        - 期望：所有纪录都是0
        """
        # Arrange
        team_name = "Not Playing Team"
        matches = [
            {"home_team": "Team A", "away_team": "Team B", "home_score": 2, "away_score": 1},
            {"home_team": "Team C", "away_team": "Team D", "home_score": 1, "away_score": 1},
        ]

        # Act
        result = TeamStatsService.calculate_streak(team_name, matches)

        # Assert
        assert result == {
            "team": team_name,
            "win_streak": 0,
            "draw_streak": 0,
            "loss_streak": 0
        }

    def test_calculate_streak_with_single_match_returns_correct_streak(self):
        """
        测试：单场比赛返回正确的纪录

        测试场景：
        - 输入：一场比赛
        - 期望：胜/平/败的纪录都是1（取决于结果）
        """
        # Arrange
        team_name = "Single Match Team"
        matches = [
            {"home_team": team_name, "away_team": "Team B", "home_score": 2, "away_score": 1}
        ]

        # Act
        result = TeamStatsService.calculate_streak(team_name, matches)

        # Assert
        assert result["team"] == team_name
        assert result["win_streak"] == 1
        assert result["draw_streak"] == 0
        assert result["loss_streak"] == 0

    # ======== 参数化测试 ========

    @pytest.mark.parametrize("results,expected_wins,expected_draws,expected_losses", [
        # 5连胜
        (["W", "W", "W", "W", "W"], 5, 0, 0),
        # 3连败
        (["L", "L", "L"], 0, 0, 3),
        # 2连平
        (["D", "D"], 0, 2, 0),
        # 混合结果：W-W-D-L-W-D-D-L-L-L -> 2连胜，2连平，3连败
        (["W", "W", "D", "L", "W", "D", "D", "L", "L", "L"], 2, 2, 3),
        # 交替结果
        (["W", "L", "W", "L", "W"], 1, 0, 1),
    ])
    def test_calculate_streak_with_various_patterns_returns_expected_streaks(
        self, results, expected_wins, expected_draws, expected_losses
    ):
        """
        测试：各种比赛模式返回期望的连胜纪录

        使用参数化测试覆盖多种场景
        """
        # Arrange
        team_name = "Test Team"
        matches = []
        for i, result in enumerate(results):
            if result == "W":
                matches.append({
                    "home_team": team_name,
                    "away_team": f"Team {i}",
                    "home_score": 2,
                    "away_score": 1
                })
            elif result == "D":
                matches.append({
                    "home_team": team_name,
                    "away_team": f"Team {i}",
                    "home_score": 1,
                    "away_score": 1
                })
            else:  # L
                matches.append({
                    "home_team": team_name,
                    "away_team": f"Team {i}",
                    "home_score": 0,
                    "away_score": 1
                })

        # Act
        result = TeamStatsService.calculate_streak(team_name, matches)

        # Assert
        assert result["win_streak"] == expected_wins, \
            f"For results {results}, expected {expected_wins} wins, got {result['win_streak']}"
        assert result["draw_streak"] == expected_draws, \
            f"For results {results}, expected {expected_draws} draws, got {result['draw_streak']}"
        assert result["loss_streak"] == expected_losses, \
            f"For results {results}, expected {expected_losses} losses, got {result['loss_streak']}"

    # ======== 集成测试示例 ========

    @patch('src.services.team_stats.datetime')
    def test_calculate_streak_with_date_filtering_returns_recent_streaks(self, mock_datetime):
        """
        测试：带日期过滤的连胜计算返回最近的纪录

        这是一个集成测试示例，展示如何测试时间相关的功能
        """
        # Arrange
        mock_datetime.now.return_value = datetime(2023, 12, 1)

        team_name = "Date Team"
        matches = [
            {
                "home_team": team_name,
                "away_team": "Team B",
                "home_score": 2,
                "away_score": 1,
                "date": datetime(2023, 11, 1)  # 一个月前
            },
            {
                "home_team": team_name,
                "away_team": "Team C",
                "home_score": 1,
                "away_score": 1,
                "date": datetime(2023, 11, 15)  # 半个月前
            }
        ]

        # Act
        # 注意：当前实现不支持日期过滤，这只是示例
        result = TeamStatsService.calculate_streak(team_name, matches)

        # Assert
        assert result["team"] == team_name

    # ======== 错误处理测试 ========

    def test_calculate_streak_with_invalid_match_data_handles_gracefully(self):
        """
        测试：无效的比赛数据被优雅处理

        测试场景：
        - 输入：缺少必要字段的比赛数据
        - 期望：不崩溃，返回合理的默认值
        """
        # Arrange
        team_name = "Invalid Data Team"
        matches = [
            # 正常比赛
            {"home_team": team_name, "away_team": "Team B", "home_score": 2, "away_score": 1},
            # 缺少比分的比赛
            {"home_team": team_name, "away_team": "Team C"},
            # 缺少球队的比赛
            {"home_team": "Team D", "away_team": "Team E", "home_score": 1, "away_score": 0},
        ]

        # Act & Assert - 应该不崩溃
        result = TeamStatsService.calculate_streak(team_name, matches)

        # 验证至少能处理部分数据
        assert result["team"] == team_name
        assert result["win_streak"] >= 0
        assert result["draw_streak"] >= 0
        assert result["loss_streak"] >= 0

    # ======== 性能测试示例 ========

    def test_calculate_streak_performance_with_large_dataset(self):
        """
        测试：处理大数据集时的性能

        性能要求：1000场比赛在100ms内完成
        """
        import time

        # Arrange - 生成大量比赛数据
        team_name = "Performance Team"
        matches = []
        for i in range(1000):
            result = i % 3  # 0:胜, 1:平, 2:败
            if result == 0:
                matches.append({
                    "home_team": team_name,
                    "away_team": f"Team {i}",
                    "home_score": 2,
                    "away_score": 1
                })
            elif result == 1:
                matches.append({
                    "home_team": team_name,
                    "away_team": f"Team {i}",
                    "home_score": 1,
                    "away_score": 1
                })
            else:
                matches.append({
                    "home_team": team_name,
                    "away_team": f"Team {i}",
                    "home_score": 0,
                    "away_score": 1
                })

        # Act
        start_time = time.time()
        result = TeamStatsService.calculate_streak(team_name, matches)
        end_time = time.time()

        # Assert
        execution_time = end_time - start_time
        assert execution_time < 0.1, f"Too slow: {execution_time:.3f}s (should be < 0.1s)"
        assert result["team"] == team_name


@pytest.mark.integration
class TestTeamStatsServiceIntegration:
    """球队统计服务集成测试"""

    def test_end_to_end_streak_calculation_flow(self):
        """
        测试：端到端连胜计算流程

        完整流程：
        1. 从数据库获取比赛数据
        2. 计算连胜纪录
        3. 返回格式化结果
        """
        # 在实际项目中，这里会使用真实的数据库或TestContainers
        # 这里用模拟数据展示测试结构

        # 1. 模拟从数据库获取数据
        team_name = "Integration Team"
        raw_matches = [
            {"date": "2023-11-01", "home": team_name, "away": "Team B", "home_score": 2, "away_score": 1},
            {"date": "2023-11-05", "home": "Team C", "away": team_name, "home_score": 0, "away_score": 2},
            {"date": "2023-11-10", "home": team_name, "away": "Team D", "home_score": 1, "away_score": 1},
            {"date": "2023-11-15", "home": "Team E", "away": team_name, "home_score": 2, "away_score": 1},
        ]

        # 2. 转换数据格式
        matches = []
        for match in raw_matches:
            if match["home"] == team_name:
                matches.append({
                    "home_team": match["home"],
                    "away_team": match["away"],
                    "home_score": match["home_score"],
                    "away_score": match["away_score"]
                })
            else:
                matches.append({
                    "home_team": match["away"],
                    "away_team": match["home"],
                    "home_score": match["away_score"],
                    "away_score": match["home_score"]
                })

        # 3. 计算连胜纪录
        result = TeamStatsService.calculate_streak(team_name, matches)

        # 4. 验证结果
        assert result["team"] == team_name
        assert result["win_streak"] >= 0
        assert result["draw_streak"] >= 0
        assert result["loss_streak"] >= 0

        # 5. 验证业务逻辑
        # 从数据看：胜-胜-平-负，最长连胜应该是2
        assert result["win_streak"] == 2


# ======== 测试辅助函数 ========

def create_match_data(home_team, away_team, home_score, away_score):
    """创建比赛数据的辅助函数"""
    return {
        "home_team": home_team,
        "away_team": away_team,
        "home_score": home_score,
        "away_score": away_score
    }


def assert_streak_result(result, team, wins, draws, losses):
    """验证连胜结果的辅助函数"""
    assert result["team"] == team
    assert result["win_streak"] == wins
    assert result["draw_streak"] == draws
    assert result["loss_streak"] == losses


# ======== 配置 ========

def pytest_configure(config):
    """配置pytest标记"""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "slow: Slow tests")


# ======== 使用示例 ========

if __name__ == "__main__":
    # 运行特定测试
    print("运行测试示例...")
    print("使用命令：")
    print("  pytest tests/examples/test_new_feature_example.py -v")
    print("  pytest tests/examples/test_new_feature_example.py::TestTeamStatsService::test_calculate_streak_with_winning_team_returns_correct_streaks -v")
    print("  pytest tests/examples/test_new_feature_example.py -k 'streak' -v")
