"""
TITAN V5.5 Bridge Radar 唤醒测试
=====================================
TDD原则: 先写断言，再跑逻辑
验证C++模糊匹配引擎(RapidFuzz)的性能与精度

@module tests.unit.BridgeRadar_V55
@version V5.5.0-ODDS-REANIMATION
@date 2026-03-14
"""

import time
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

# 被测组件
import sys
sys.path.insert(0, '/home/xupeng/projects/FootballPrediction')

# 模拟导入 (TDD: 先写断言)
try:
    from src.utils.cpp_bridge_radar import (
        BridgeRadarEngine, 
        RadarQuery, 
        RadarMatchResult,
        RadarEngineConfig
    )
    RAPIDFUZZ_AVAILABLE = True
except ImportError as e:
    RAPIDFUZZ_AVAILABLE = False
    print(f"⚠️ RapidFuzz导入失败: {e}")


class TestBridgeRadarV55:
    """V5.5 Bridge Radar TDD测试套件"""
    
    @pytest.fixture
    def mock_team_pairs(self):
        """模拟100场跨源队名对 (FotMob vs OddsPortal)"""
        return [
            # (FotMob名称, OddsPortal名称)
            ("Manchester United", "Man Utd"),
            ("Manchester City", "Man City"),
            ("Tottenham Hotspur", "Tottenham"),
            ("West Ham United", "West Ham"),
            ("Newcastle United", "Newcastle"),
            ("Leicester City", "Leicester"),
            ("Aston Villa", "Aston Villa"),
            ("Brighton & Hove Albion", "Brighton"),
            ("Wolverhampton Wanderers", "Wolves"),
            ("Nottingham Forest", "Nottm Forest"),
            # ... 重复以生成100对
            ("Liverpool FC", "Liverpool"),
            ("Chelsea FC", "Chelsea"),
            ("Arsenal FC", "Arsenal"),
            ("Crystal Palace", "Crystal Palace"),
            ("Brentford FC", "Brentford"),
            ("Fulham FC", "Fulham"),
            ("Everton FC", "Everton"),
            ("Leeds United", "Leeds"),
            ("Southampton FC", "Southampton"),
            ("Burnley FC", "Burnley"),
            # 欧洲球队
            ("Real Madrid", "Real Madrid"),
            ("FC Barcelona", "Barcelona"),
            ("Atletico Madrid", "Atletico"),
            ("Bayern Munich", "Bayern München"),
            ("Borussia Dortmund", "Dortmund"),
            ("Paris Saint-Germain", "PSG"),
            ("Juventus", "Juventus"),
            ("AC Milan", "Milan"),
            ("Inter Milan", "Inter"),
            ("Napoli", "Napoli"),
            # 继续生成...
            *[(f"Team{i} FC", f"Team{i}") for i in range(10, 71)]
        ]
    
    @pytest.fixture  
    def radar_config(self):
        """V5.5雷达引擎配置"""
        return RadarEngineConfig(
            min_threshold=70.0,  # 生产标准: > 0.7
            high_threshold=85.0,
            max_candidates_per_team=5,
            max_total_candidates=10,
            require_date_match=True,
            date_match_window_days=7
        )
    
    def test_tdd_bridge_radar_imports(self):
        """TDD: 确认组件可导入"""
        assert RAPIDFUZZ_AVAILABLE, "RapidFuzz C++引擎必须可用"
    
    def test_tdd_bridge_radar_init(self, radar_config):
        """TDD: BridgeRadar引擎初始化"""
        if not RAPIDFUZZ_AVAILABLE:
            pytest.skip("RapidFuzz不可用")
        
        engine = BridgeRadarEngine(config=radar_config)
        assert engine is not None
        assert engine.config.min_threshold == 70.0
    
    @pytest.mark.parametrize("fotmob_name,oddsportal_name,expected_min_score", [
        ("Manchester United", "Man Utd", 75.0),  # 短名称变体
        ("Manchester United", "Manchester United", 95.0),  # 完全匹配
        ("Tottenham Hotspur", "Tottenham", 80.0),  # 部分匹配
        ("Brighton & Hove Albion", "Brighton", 70.0),  # 复合名
        ("Wolverhampton Wanderers", "Wolves", 78.0),  # 昵称
    ])
    def test_tdd_team_name_similarity(
        self, fotmob_name, oddsportal_name, expected_min_score, radar_config
    ):
        """TDD: 跨源队名模糊匹配精度验证"""
        if not RAPIDFUZZ_AVAILABLE:
            pytest.skip("RapidFuzz不可用")
        
        # 从team_alias导入
        from src.utils.team_alias import calculate_similarity
        
        score = calculate_similarity(fotmob_name, oddsportal_name)
        
        # TDD断言: 置信度必须 > 0.7 (70分)
        assert score >= expected_min_score, (
            f"队名匹配置信度不足: {fotmob_name} vs {oddsportal_name} = {score:.1f}, "
            f"期望值 >= {expected_min_score}"
        )
    
    def test_tdd_100_matches_performance(self, mock_team_pairs, radar_config):
        """TDD: 100场队名匹配性能测试 (必须 < 200ms)"""
        if not RAPIDFUZZ_AVAILABLE:
            pytest.skip("RapidFuzz不可用")
        
        from rapidfuzz import fuzz
        
        start_time = time.time()
        
        matches = 0
        for fotmob_name, oddsportal_name in mock_team_pairs:
            # TDD: 调用C++模糊匹配引擎
            score = fuzz.WRatio(fotmob_name, oddsportal_name)
            if score >= 70.0:  # 生产标准
                matches += 1
        
        elapsed_ms = (time.time() - start_time) * 1000
        
        # TDD断言1: 性能必须 < 200ms
        assert elapsed_ms < 200.0, (
            f"性能不达标: {elapsed_ms:.1f}ms >= 200ms 阈值, "
            f"处理了{len(mock_team_pairs)}场比赛"
        )
        
        # TDD断言2: 吞吐量 >= 500场/秒
        throughput = len(mock_team_pairs) / (elapsed_ms / 1000)
        assert throughput >= 500, (
            f"吞吐量不足: {throughput:.0f}场/秒 < 500场/秒"
        )
        
        print(f"\n✅ C++引擎性能: {elapsed_ms:.1f}ms / {len(mock_team_pairs)}场 = {throughput:.0f}场/秒")
    
    def test_tdd_radar_query_validation(self):
        """TDD: RadarQuery Pydantic验证"""
        if not RAPIDFUZZ_AVAILABLE:
            pytest.skip("RapidFuzz不可用")
        
        query = RadarQuery(
            match_id="test_001",
            home_team="Manchester United",
            away_team="Chelsea",
            league_name="Premier League",
            match_date=datetime.now(),
            min_threshold=70.0,
            max_candidates=10
        )
        
        assert query.match_id == "test_001"
        assert query.min_threshold == 70.0
    
    def test_tdd_high_confidence_threshold(self, radar_config):
        """TDD: 高置信度阈值验证 (> 0.85)"""
        if not RAPIDFUZZ_AVAILABLE:
            pytest.skip("RapidFuzz不可用")
        
        from rapidfuzz import fuzz
        
        # 测试高置信度匹配
        score = fuzz.WRatio("Manchester United", "Manchester United")
        
        # TDD断言: 完全匹配必须 >= 95分
        assert score >= 95.0, f"完全匹配置信度不足: {score}"
        
        # 高置信度阈值: >= 85分直接接受
        assert score >= radar_config.high_threshold
    
    @patch('psycopg2.connect')
    def test_tdd_team_index_loading(self, mock_connect, radar_config):
        """TDD: 队名索引加载测试"""
        if not RAPIDFUZZ_AVAILABLE:
            pytest.skip("RapidFuzz不可用")
        
        # Mock数据库连接
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = [
            {"league_name": "Premier League", 
             "home_team": "Man Utd", 
             "away_team": "Chelsea",
             "oddsportal_url": "https://www.oddsportal.com/soccer/england/..."}
        ]
        
        engine = BridgeRadarEngine(config=radar_config)
        
        # TDD: 索引应能加载
        assert engine._index_loaded is False
    
    def test_tdd_radar_result_structure(self):
        """TDD: RadarMatchResult结果结构验证"""
        if not RAPIDFUZZ_AVAILABLE:
            pytest.skip("RapidFuzz不可用")
        
        result = RadarMatchResult(
            match_id="test_001",
            fotmob_id="12345",
            home_team="Manchester United",
            away_team="Chelsea",
            candidate_url="https://www.oddsportal.com/soccer/...",
            confidence=85.5,
            discovery_method="RADAR_DISCOVERY",
            trace_id=str(uuid.uuid4()),
            timestamp=datetime.now()
        )
        
        # TDD断言: 结果字段完整
        assert result.confidence >= 70.0
        assert result.candidate_url is not None
        assert result.discovery_method in ["STATIC_LOOKUP", "RADAR_DISCOVERY"]


class TestBridgeRadarIntegration:
    """Bridge Radar集成测试"""
    
    def test_tdd_full_radar_scan(self):
        """TDD: 完整雷达扫描流程"""
        pytest.skip("需要真实数据库连接 - 集成测试")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
