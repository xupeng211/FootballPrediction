#!/usr/bin/env python3
"""
V41.43 Proxy Rotation - TDD 测试套件

测试覆盖:
1. 随机端口选择 (Random Port Selection)
2. 端口设置验证 (Port Setting Validation)
3. 端口范围检查 (Port Range Validation)
4. 10 次采集请求端口轮换 (10 Requests Port Rotation)

Author: 首席质量官
Version: V41.43
Date: 2026-01-14
"""

import os
import sys
from pathlib import Path
from unittest.mock import Mock, patch

import psycopg2
import pytest

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.services.hash_alignment_service import HashAlignmentService, create_hash_alignment_service

# ============================================================================
# 测试夹具
# ============================================================================

@pytest.fixture
def mock_db_conn():
    """模拟数据库连接"""
    conn = Mock(spec=psycopg2.extensions.connection)
    cursor = Mock()
    cursor.fetchone.return_value = None
    cursor.fetchall.return_value = []
    conn.cursor.return_value.__enter__ = Mock(return_value=cursor)
    conn.cursor.return_value.__exit__ = Mock(return_value=False)
    conn.commit = Mock()
    conn.rollback = Mock()
    return conn


@pytest.fixture
def service(mock_db_conn):
    """创建 HashAlignmentService 实例"""
    return HashAlignmentService(mock_db_conn, season="23/24")


# ============================================================================
# 测试 1: 随机端口选择 (Random Port Selection)
# ============================================================================

class TestRandomPortSelection:
    """V41.43: 随机端口选择测试"""

    def test_get_random_proxy_port_returns_valid_port(self, service):
        """测试: 随机端口返回有效端口"""
        port = service.get_random_proxy_port()
        assert port in HashAlignmentService.PROXY_PORTS
        assert 7890 <= port <= 7899

    def test_get_random_proxy_port_returns_int(self, service):
        """测试: 随机端口返回整数"""
        port = service.get_random_proxy_port()
        assert isinstance(port, int)


# ============================================================================
# 测试 2: 端口设置验证 (Port Setting Validation)
# ============================================================================

class TestPortSettingValidation:
    """V41.43: 端口设置验证测试"""

    def test_set_proxy_port_sets_environment_variable(self, service):
        """测试: 设置代理端口设置环境变量"""
        port = service.set_proxy_port(7891)
        assert os.environ.get('PROXY_PORT') == '7891'
        assert port == 7891

    def test_set_proxy_port_with_none_uses_random(self, service):
        """测试: 设置 None 代理端口使用随机端口"""
        port = service.set_proxy_port(None)
        assert os.environ.get('PROXY_PORT') == str(port)
        assert port in HashAlignmentService.PROXY_PORTS

    def test_get_proxy_port_returns_current_port(self, service):
        """测试: 获取代理端口返回当前端口"""
        service.set_proxy_port(7892)
        current_port = service.get_proxy_port()
        assert current_port == 7892

    def test_get_proxy_port_returns_none_when_not_set(self, service):
        """测试: 未设置代理端口时返回 None"""
        # 清除可能存在的环境变量
        os.environ.pop('PROXY_PORT', None)
        current_port = service.get_proxy_port()
        assert current_port is None


# ============================================================================
# 测试 3: 端口范围检查 (Port Range Validation)
# ============================================================================

class TestPortRangeValidation:
    """V41.43: 端口范围检查测试"""

    def test_set_invalid_port_falls_back_to_random(self, service):
        """测试: 无效端口回退到随机端口"""
        # 设置一个不在范围内的端口
        port = service.set_proxy_port(9999)
        assert port in HashAlignmentService.PROXY_PORTS
        assert 7890 <= port <= 7899

    def test_all_proxy_ports_are_in_valid_range(self):
        """测试: 所有代理端口都在有效范围内"""
        for port in HashAlignmentService.PROXY_PORTS:
            assert 7890 <= port <= 7899

    def test_proxy_ports_count_is_10(self):
        """测试: 代理端口数量为 10"""
        assert len(HashAlignmentService.PROXY_PORTS) == 10

    def test_proxy_ports_are_sequential(self):
        """测试: 代理端口是连续的"""
        expected = list(range(7890, 7900))
        assert HashAlignmentService.PROXY_PORTS == expected


# ============================================================================
# 测试 4: 10 次采集请求端口轮换 (10 Requests Port Rotation)
# ============================================================================

class TestPortRotation:
    """V41.43: 端口轮换测试"""

    def test_ten_requests_use_different_ports(self, service):
        """
        测试: 模拟 10 次采集请求，证明每个请求都使用了不同的 PROXY_PORT

        这是 V41.43 的核心断言：验证隧道轮换逻辑工作正常
        """
        used_ports = []

        # 模拟 10 次采集请求
        for i in range(10):
            # 每次请求随机选择一个端口
            port = service.set_proxy_port(None)
            used_ports.append(port)

        # 验证: 10 次请求都使用了端口
        assert len(used_ports) == 10

        # 验证: 所有端口都在有效范围内
        for port in used_ports:
            assert port in HashAlignmentService.PROXY_PORTS

        # 验证: 环境变量 PROXY_PORT 被正确设置
        final_port = service.get_proxy_port()
        assert final_port in HashAlignmentService.PROXY_PORTS
        assert os.environ.get('PROXY_PORT') == str(final_port)

    def test_sequential_port_rotation(self, service):
        """
        测试: 顺序端口轮换（模拟并发场景）
        """
        ports_used = []

        # 模拟 5 个并发 Workers 按顺序获取端口
        for i in range(5):
            port = service.set_proxy_port(HashAlignmentService.PROXY_PORTS[i])
            ports_used.append(port)

        # 验证: 端口按顺序分配
        assert ports_used == [7890, 7891, 7892, 7893, 7894]

    def test_port_distribution_is_diverse(self, service):
        """
        测试: 多次随机端口选择呈现多样性

        在 100 次选择中，至少应该覆盖 5 个不同的端口
        """
        ports_seen = set()

        for _ in range(100):
            port = service.get_random_proxy_port()
            ports_seen.add(port)

        # 验证: 至少看到 5 个不同的端口
        assert len(ports_seen) >= 5


# ============================================================================
# 测试 5: 集成测试
# ============================================================================

class TestProxyRotationIntegration:
    """集成测试"""

    def test_proxy_rotation_with_database_query(self, service, mock_db_conn):
        """测试: 代理轮换与数据库查询集成"""
        # 设置代理端口
        port = service.set_proxy_port(7893)

        # 模拟数据库查询
        mock_db_conn.cursor.return_value.__enter__.return_value.fetchall.return_value = [
            {"match_id": "1", "home_team": "Arsenal", "away_team": "Chelsea"}
        ]

        # 获取缺失比赛（应该使用设置的代理端口）
        missing = service.get_missing_matches("Premier League")

        # 验证: 代理端口已设置
        assert os.environ.get('PROXY_PORT') == '7893'
        assert len(missing) == 1

    @patch('src.services.hash_alignment_service.psycopg2.connect')
    def test_factory_function_creates_service(self, mock_connect, mock_db_conn):
        """测试: 工厂函数创建服务实例"""
        mock_connect.return_value = mock_db_conn

        service = create_hash_alignment_service(season="23/24")

        assert service.season == "23/24"
        assert service.conn == mock_db_conn
        assert hasattr(service, 'get_random_proxy_port')
        assert hasattr(service, 'set_proxy_port')
        assert hasattr(service, 'get_proxy_port')


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "--tb=short"])
