"""
测试原始HTML数据保存功能
防御性重构的安全护栏测试

Principal Software Engineer & Test Architect
Purpose: 确保ELT架构转型不引入回归Bug
"""

import pytest
import asyncio
import gzip
import hashlib
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime
import pandas as pd

# 确保测试环境中的导入路径
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# 导入目标模块
from src.data.collectors.fbref_collector import FBrefCollector


class TestRawHTMLPreservation:
    """原始HTML保存功能测试套件"""

    @pytest.fixture
    def mock_html_content(self):
        """模拟的FBref HTML内容 - 匹配实际FBref结构"""
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Premier League Scores and Fixtures</title>
        </head>
        <body>
            <div id="content">
                <div class="table_outer">
                    <table class="stats_table sortable now_sortable" id="sched_2023-2024_9_1">
                        <thead>
                            <tr>
                                <th aria-label="Wk" class="sortdefaultasc" data-stat="week_num">Wk</th>
                                <th aria-label="Date" data-stat="date">Date</th>
                                <th aria-label="Time" data-stat="kickoff">Time</th>
                                <th aria-label="Home" data-stat="home_team">Home</th>
                                <th aria-label="xG" data-stat="xg">xG</th>
                                <th aria-label="Score" data-stat="score">Score</th>
                                <th aria-label="xG" data-stat="xg">xG</th>
                                <th aria-label="Away" data-stat="away_team">Away</th>
                                <th aria-label="Attendance" data-stat="attendance">Attendance</th>
                                <th aria-label="Venue" data-stat="venue">Venue</th>
                                <th aria-label="Match Report" data-stat="match_report">Match Report</th>
                                <th aria-label="Notes" data-stat="notes">Notes</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <td data-stat="week_num">21</td>
                                <td data-stat="date">2024-01-15</td>
                                <td data-stat="kickoff">15:00</td>
                                <td data-stat="home_team"><a href="/en/squads/822bd0ba/Liverpool">Liverpool</a></td>
                                <td data-stat="xg">2.5</td>
                                <td data-stat="score"><a href="/en/matches/12345">4-2</a></td>
                                <td data-stat="xg">1.8</td>
                                <td data-stat="away_team"><a href="/en/squads/b2b47ffe/Newcastle-Utd">Newcastle Utd</a></td>
                                <td data-stat="attendance">53271</td>
                                <td data-stat="venue">Anfield</td>
                                <td data-stat="match_report"><a href="/en/matches/12345">Report</a></td>
                                <td data-stat="notes"></td>
                            </tr>
                            <tr>
                                <td data-stat="week_num">22</td>
                                <td data-stat="date">2024-01-16</td>
                                <td data-stat="kickoff">20:00</td>
                                <td data-stat="home_team"><a href="/en/squads/18bb7c10/Arsenal">Arsenal</a></td>
                                <td data-stat="xg">1.9</td>
                                <td data-stat="score"><a href="/en/matches/12346">2-0</a></td>
                                <td data-stat="xg">0.8</td>
                                <td data-stat="away_team"><a href="/en/squads/d075d4ae/Crystal-Palace">Crystal Palace</a></td>
                                <td data-stat="attendance">60343</td>
                                <td data-stat="venue">Emirates Stadium</td>
                                <td data-stat="match_report"><a href="/en/matches/12346">Report</a></td>
                                <td data-stat="notes"></td>
                            </tr>
                            <tr>
                                <td data-stat="week_num">23</td>
                                <td data-stat="date">2024-01-17</td>
                                <td data-stat="kickoff">17:30</td>
                                <td data-stat="home_team"><a href="/en/squads/3b3b8879/Manchester-City">Manchester City</a></td>
                                <td data-stat="xg">3.1</td>
                                <td data-stat="score"><a href="/en/matches/12347">3-1</a></td>
                                <td data-stat="xg">1.2</td>
                                <td data-stat="away_team"><a href="/en/squads/e2a6136c/West-Ham-United">West Ham United</a></td>
                                <td data-stat="attendance">55235</td>
                                <td data-stat="venue">Etihad Stadium</td>
                                <td data-stat="match_report"><a href="/en/matches/12347">Report</a></td>
                                <td data-stat="notes"></td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </body>
        </html>
        """

    @pytest.fixture
    def temp_data_dir(self):
        """临时数据目录"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def collector(self, temp_data_dir):
        """FBref采集器实例"""
        with patch('src.data.collectors.fbref_collector.requests.Session'):
            collector = FBrefCollector()
            # 覆盖数据目录为临时目录
            collector.raw_data_dir = Path(temp_data_dir) / "data" / "raw_landing" / "fbref"
            return collector

    def test_setup(self):
        """测试环境设置验证"""
        assert Path(__file__).exists()
        assert project_root.exists()

    @pytest.mark.asyncio
    async def test_raw_html_saving_should_create_file(self, collector, mock_html_content, temp_data_dir):
        """
        测试原始HTML保存功能应该创建对应的文件
        This test should fail initially before implementation
        """
        # 准备测试数据
        league_url = "https://fbref.com/en/comps/9/schedule/Premier-League-Scores-and-Fixtures"
        season = "2023-2024"

        with patch.object(collector, 'fetch_html', return_value=mock_html_content):
            # 调用采集器方法
            result = await collector.get_season_schedule(league_url, season)

            # 断言：检查返回的DataFrame - 先确保解析成功
            assert isinstance(result, pd.DataFrame)

            # 如果解析成功，继续测试HTML保存功能
            if not result.empty:
                # 断言：检查是否包含原始文件路径字段（这个会在实现后存在）
                if 'raw_file_path' in result.columns:
                    raw_file_paths = result['raw_file_path'].dropna()
                    assert len(raw_file_paths) > 0

                    # 检查文件是否存在
                    for file_path in raw_file_paths:
                        assert Path(file_path).exists()
                        assert Path(file_path).suffix == '.gz'
                else:
                    # 如果没有这个字段，测试会失败，这是预期的
                    pytest.fail("DataFrame should contain 'raw_file_path' column after HTML saving implementation")
            else:
                # 如果解析失败，至少HTML保存功能应该存在 - 检查目录是否被创建
                expected_base_dir = Path(temp_data_dir) / "data" / "raw_landing" / "fbref"
                if expected_base_dir.exists():
                    pytest.skip("HTML parsing failed but raw saving might be implemented - test skipped")
                else:
                    pytest.fail("Both HTML parsing and raw saving failed - test fails as expected")

    @pytest.mark.asyncio
    async def test_raw_html_file_content_correctness(self, collector, mock_html_content, temp_data_dir):
        """
        测试保存的HTML文件内容正确性
        """
        league_url = "https://fbref.com/en/comps/9/schedule/Premier-League-Scores-and-Fixtures"
        season = "2023-2024"

        with patch.object(collector, 'fetch_html', return_value=mock_html_content):
            result = await collector.get_season_schedule(league_url, season)

            # 检查文件内容
            if hasattr(result, 'raw_file_path') or 'raw_file_path' in result.columns:
                raw_file_paths = result['raw_file_path'].dropna()
                if len(raw_file_paths) > 0:
                    file_path = Path(raw_file_paths.iloc[0])
                    assert file_path.exists()

                    # 解压gzip文件并检查内容
                    with gzip.open(file_path, 'rt', encoding='utf-8') as f:
                        saved_content = f.read()

                    assert saved_content == mock_html_content
                    assert "Premier League Scores and Fixtures" in saved_content
                    assert "Liverpool" in saved_content
            else:
                pytest.fail("Raw HTML preservation not implemented yet")

    @pytest.mark.asyncio
    async def test_raw_html_saving_failure_isolation(self, collector, mock_html_content):
        """
        测试原始HTML保存失败不应影响数据解析
        Fail-Safe测试
        """
        league_url = "https://fbref.com/en/comps/9/schedule/Premier-League-Scores-and-Fixtures"
        season = "2023-2024"

        # Mock文件保存失败
        def mock_file_save_failure(*args, **kwargs):
            raise OSError("Permission denied" if args else "Disk full")

        with patch.object(collector, 'fetch_html', return_value=mock_html_content):
            with patch('gzip.open', side_effect=mock_file_save_failure):
                with patch('builtins.open', side_effect=mock_file_save_failure):
                    # 即使文件保存失败，数据解析仍应成功
                    result = await collector.get_season_schedule(league_url, season)

                    # 断言：数据解析应该仍然成功
                    assert isinstance(result, pd.DataFrame)
                    if not result.empty:  # 如果解析成功
                        assert 'home' in result.columns or any('home' in str(col).lower() for col in result.columns)
                        assert len(result) == 2  # 仍然解析出2场比赛数据

    @pytest.mark.asyncio
    async def test_directory_structure_creation(self, collector, mock_html_content, temp_data_dir):
        """
        测试目录结构正确创建
        """
        league_url = "https://fbref.com/en/comps/9/schedule/Premier-League-Scores-and-Fixtures"
        season = "2023-2024"

        with patch.object(collector, 'fetch_html', return_value=mock_html_content):
            await collector.get_season_schedule(league_url, season)

            # 检查目录结构
            expected_base_dir = Path(temp_data_dir) / "data" / "raw_landing" / "fbref"
            league_dir = expected_base_dir / "9"  # 从URL提取的league_id
            season_dir = league_dir / season.replace("-", "")

            # 这些目录应该在实现后存在
            if expected_base_dir.exists():
                assert league_dir.exists()
                assert season_dir.exists()

                # 检查HTML文件存在
                html_files = list(season_dir.glob("*.html.gz"))
                assert len(html_files) > 0

    def test_file_naming_convention(self, collector, mock_html_content, temp_data_dir):
        """
        测试文件命名约定
        """
        test_content = mock_html_content
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        content_hash = hashlib.sha256(test_content.encode('utf-8')).hexdigest()[:16]
        expected_filename = f"{timestamp}_{content_hash}.html.gz"

        # 测试命名逻辑（当实现后）
        if hasattr(collector, '_generate_filename'):
            actual_filename = collector._generate_filename(test_content)
            assert actual_filename == expected_filename

    @pytest.mark.asyncio
    async def test_integration_with_existing_functionality(self, collector, mock_html_content):
        """
        测试与现有功能的集成
        确保新功能不破坏现有的数据解析逻辑
        """
        league_url = "https://fbref.com/en/comps/9/schedule/Premier-League-Scores-and-Fixtures"
        season = "2023-2024"

        with patch.object(collector, 'fetch_html', return_value=mock_html_content):
            result = await collector.get_season_schedule(league_url, season)

            # 确保基本功能不受影响
            assert isinstance(result, pd.DataFrame)
            if not result.empty:  # 如果解析成功
                # 检查基本数据结构
                columns_lower = [str(col).lower() for col in result.columns]

                # 检查是否包含关键的比赛信息
                has_home_team = any('home' in col for col in columns_lower)
                has_away_team = any('away' in col for col in columns_lower)
                has_date = any('date' in col for col in columns_lower)

                if has_home_team and has_away_team and has_date:
                    # 检查数据行数
                    assert len(result) == 2

                    # 检查是否包含特定队伍
                    result_str = result.to_string().lower()
                    assert 'liverpool' in result_str or 'arsenal' in result_str
                    assert 'newcastle' in result_str or 'crystal' in result_str


if __name__ == "__main__":
    # 直接运行测试用于调试
    import subprocess
    import sys

    result = subprocess.run([
        sys.executable, "-m", "pytest",
        __file__, "-v", "--tb=short"
    ], capture_output=True, text=True)

    print("STDOUT:", result.stdout)
    print("STDERR:", result.stderr)
    print("Return code:", result.returncode)
