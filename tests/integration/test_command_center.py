#!/usr/bin/env python3
"""V144.7 Multi-Source Command Center Integration Tests.

Test suite for main.py multi-source command center functionality:
- Task A1: --source parameter validation
- Task A2: Logic dispatching (oddsportal vs fotmob)
- Task B1: Configuration consistency (daily_workflow.py, run_sync.py)
- Task B2: Debug script archival

Author: V144.7 Integration Test Team
Version: 1.0.0
Date: 2026-01-06
"""

import subprocess
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


# ============================================================================
# Task A1: --source Parameter Validation Tests
# ============================================================================

class TestSourceParameter:
    """Test suite for --source argument parsing."""

    def test_source_default_is_oddsportal(self):
        """Test default source is oddsportal."""
        from main import parse_args

        # Mock sys.argv (parse_args reads from sys.argv internally)
        original_argv = sys.argv
        try:
            sys.argv = ["main.py"]
            args = parse_args()
            assert args.source == "oddsportal"
        finally:
            sys.argv = original_argv

    def test_source_accepts_oddsportal(self):
        """Test source accepts oddsportal."""
        from main import parse_args

        original_argv = sys.argv
        try:
            sys.argv = ["main.py", "--source", "oddsportal"]
            args = parse_args()
            assert args.source == "oddsportal"
        finally:
            sys.argv = original_argv

    def test_source_accepts_fotmob(self):
        """Test source accepts fotmob."""
        from main import parse_args

        original_argv = sys.argv
        try:
            sys.argv = ["main.py", "--source", "fotmob"]
            args = parse_args()
            assert args.source == "fotmob"
        finally:
            sys.argv = original_argv

    def test_source_rejects_invalid_value(self):
        """Test source rejects invalid value."""
        from main import parse_args

        original_argv = sys.argv
        try:
            sys.argv = ["main.py", "--source", "invalid"]
            with pytest.raises(SystemExit):
                parse_args()
        finally:
            sys.argv = original_argv

    def test_source_combines_with_mode(self):
        """Test source combines with mode parameter."""
        from main import parse_args

        original_argv = sys.argv
        try:
            sys.argv = ["main.py", "--source", "fotmob", "--mode", "cruise"]
            args = parse_args()
            assert args.source == "fotmob"
            assert args.mode == "cruise"
        finally:
            sys.argv = original_argv


# ============================================================================
# Task A2: Logic Dispatching Tests
# ============================================================================

class TestLogicDispatching:
    """Test suite for source-based logic routing."""

    @pytest.mark.asyncio
    async def test_oddsportal_mode_dispatch(self):
        """Test oddsportal source routes to run_oddsportal_mode."""
        from main import main

        mock_args = MagicMock()
        mock_args.source = "oddsportal"
        mock_args.mode = "single"
        mock_args.skip_precheck = True
        mock_args.proxy_file = "proxies.txt"
        mock_args.limit = 1
        mock_args.no_ghost = False
        mock_args.no_queue = False
        mock_args.dry_run = True

        with patch("main.parse_args", return_value=mock_args):
            with patch("main.run_oddsportal_mode", new_callable=AsyncMock) as mock_run:
                mock_run.return_value = 0

                with patch("main.print_banner"):
                    with patch("main.check_environment"):
                        with patch("main.check_ip_address", new_callable=AsyncMock) as mock_ip:
                            mock_ip.return_value = "127.0.0.1"

                            result = await main()
                            assert result == 0

    @pytest.mark.asyncio
    async def test_fotmob_mode_dispatch(self):
        """Test fotmob source routes to run_fotmob_mode."""
        from main import main

        mock_args = MagicMock()
        mock_args.source = "fotmob"
        mock_args.mode = "single"
        mock_args.skip_precheck = True
        mock_args.limit = 1
        mock_args.dry_run = True
        mock_args.league = None
        mock_args.season = None

        with patch("main.parse_args", return_value=mock_args):
            with patch("main.run_fotmob_mode", new_callable=AsyncMock) as mock_run:
                mock_run.return_value = 0

                with patch("main.print_banner"):
                    with patch("main.check_environment"):
                        with patch("main.check_ip_address", new_callable=AsyncMock) as mock_ip:
                            mock_ip.return_value = "127.0.0.1"

                            result = await main()
                            assert result == 0

    @pytest.mark.asyncio
    async def test_check_mode_dispatches_correctly(self):
        """Test check mode dispatches correctly."""
        from main import main

        mock_args = MagicMock()
        mock_args.source = "oddsportal"
        mock_args.mode = "check"
        mock_args.skip_precheck = True

        with patch("main.parse_args", return_value=mock_args):
            with patch("main.run_check_mode", new_callable=AsyncMock) as mock_run:
                mock_run.return_value = 0

                with patch("main.print_banner"):
                    with patch("main.check_environment"):
                        with patch("main.check_ip_address", new_callable=AsyncMock) as mock_ip:
                            mock_ip.return_value = "127.0.0.1"

                            result = await main()
                            assert result == 0


# ============================================================================
# Task B1: Configuration Consistency Tests
# ============================================================================

class TestConfigurationConsistency:
    """Test suite for environment variable loading consistency."""

    def test_daily_workflow_loads_dotenv(self):
        """Test daily_workflow.py has load_dotenv(override=True)."""
        daily_workflow_path = Path(__file__).parent.parent.parent / "src" / "ops" / "daily_workflow.py"
        content = daily_workflow_path.read_text()

        # Check for load_dotenv import and usage
        assert "from dotenv import load_dotenv" in content
        assert "load_dotenv(override=True)" in content

    def test_run_sync_loads_dotenv(self):
        """Test run_sync.py has load_dotenv(override=True)."""
        run_sync_path = Path(__file__).parent.parent.parent / "scripts" / "run_sync.py"
        content = run_sync_path.read_text()

        # Check for load_dotenv import and usage
        assert "from dotenv import load_dotenv" in content
        assert "load_dotenv(override=True)" in content

    def test_main_py_loads_dotenv(self):
        """Test main.py has load_dotenv(override=True)."""
        main_path = Path(__file__).parent.parent.parent / "main.py"
        content = main_path.read_text()

        # Check for load_dotenv import and usage
        assert "from dotenv import load_dotenv" in content
        assert "load_dotenv(override=True)" in content


# ============================================================================
# Task B2: Debug Script Archival Tests
# ============================================================================

class TestDebugScriptArchival:
    """V41.84: Test suite for debug script archival (净空行动)."""

    def test_debug_directory_archived(self):
        """V41.84: Verify debug scripts were archived in V41.81 Clean Sky."""
        debug_dir = Path(__file__).parent.parent.parent / "scripts" / "debug"
        # V41.81 净空行动已清理 debug 目录
        assert not debug_dir.exists(), f"Debug directory should be archived, but found at {debug_dir}"

    def test_diagnose_scripts_cleaned(self):
        """V41.84: Verify diagnose_*.py scripts were cleaned from scripts/ root."""
        scripts_dir = Path(__file__).parent.parent.parent / "scripts"

        # V41.81 净空行动清理了所有临时 diagnose 脚本
        assert not (scripts_dir / "diagnose_network.py").exists()
        assert not (scripts_dir / "diagnose_slug_parsing.py").exists()
        assert not (scripts_dir / "diagnose_url_filtering.py").exists()
        assert not (scripts_dir / "debug_ip_reputation.py").exists()
        assert not (scripts_dir / "debug_proxy_rotation.py").exists()

    def test_no_orphan_debug_scripts(self):
        """V41.84: Verify no orphan debug scripts in scripts/ root."""
        scripts_dir = Path(__file__).parent.parent.parent / "scripts"

        # 检查不应存在的 debug/诊断脚本
        debug_patterns = ["diagnose_*.py", "debug_*.py", "capture_*.py"]
        found_debug_scripts = []

        for pattern in debug_patterns:
            for script in scripts_dir.glob(pattern):
                found_debug_scripts.append(script.name)

        assert len(found_debug_scripts) == 0, f"Found orphan debug scripts: {found_debug_scripts}"


# ============================================================================
# Ghost Protocol Verification Tests
# ============================================================================

class TestGhostProtocolIntegration:
    """Test suite for Ghost Protocol V144.2 integration."""

    def test_main_py_ghost_protocol_log(self):
        """Test main.py logs Ghost Protocol initialization."""
        main_path = Path(__file__).parent.parent.parent / "main.py"
        content = main_path.read_text()

        # Check for Ghost Protocol log
        assert "[V144.7] 🛡️ Unified Ghost Protocol initialized" in content

    def test_fotmob_mode_ghost_protocol_log(self):
        """Test run_fotmob_mode logs Ghost Protocol."""
        main_path = Path(__file__).parent.parent.parent / "main.py"
        content = main_path.read_text()

        # Check for Ghost Protocol log in fotmob mode
        assert "Unified Ghost Protocol initialized for fotmob" in content


# ============================================================================
# CLI Integration Tests
# ============================================================================

class TestCLIIntegration:
    """Test suite for CLI command execution."""

    def test_help_displays_source_parameter(self):
        """Test --help displays --source parameter."""
        result = subprocess.run(
            [sys.executable, "main.py", "--help"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent
        )
        assert "--source" in result.stdout
        assert "oddsportal" in result.stdout
        assert "fotmob" in result.stdout

    def test_version_displays_v144_7(self):
        """Test version displays V144.7."""
        main_path = Path(__file__).parent.parent.parent / "main.py"
        content = main_path.read_text()

        # Check for V144.7 in docstring
        assert "V144.7" in content
        assert "Multi-Source Command Center" in content


# ============================================================================
# Pytest Fixtures
# ============================================================================

@pytest.fixture
def mock_settings():
    """Mock settings for testing."""
    with patch("src.config_unified.get_settings") as mock:
        settings = MagicMock()
        settings.database.host = "172.25.16.1"
        settings.database.port = 5432
        settings.database.name = "football_db"
        settings.database.user = "football_user"
        settings.database.password = MagicMock(get_secret_value=MagicMock(return_value="test_pass"))
        mock.return_value = settings
        yield mock


# ============================================================================
# Test Discovery
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
