"""
V38.0 "特种渗透版" Odds API 客户端
==================================
基于 stealth_client 的重构实现，补齐 TLS/JA3 指纹伪装

核心改进:
1. 使用 curl_cffi (AsyncSession) 替代 aiohttp
2. 强制启用 impersonate="chrome131"
3. 完整的 sec-ch-ua 请求头序列
4. 集成 TeamAliasResolver 进行队名对齐
5. 智能代理轮换 + 指纹绑定

@module api.collectors.odds_api_client_v38
@version V38.0-STEALTH
@date 2026-03-17
"""

import asyncio
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
import importlib.util
import os

# V38.0: 使用 stealth_client 替代 aiohttp
# 使用直接文件导入避免包依赖问题
def _load_module(module_name, file_path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

_base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_stealth_module = _load_module(
    'stealth_client',
    os.path.join(_base_path, 'infrastructure/network/stealth_client.py')
)
_resolver_module = _load_module(
    'team_alias_resolver',
    os.path.join(_base_path, 'core/matching/team_alias_resolver.py')
)

StealthClient = _stealth_module.StealthClient
get_stealth_client = _stealth_module.get_stealth_client
TeamAliasResolver = _resolver_module.TeamAliasResolver
get_resolver = _resolver_module.get_resolver


class OddsAPIClientV38:
    """
    V38.0 特种渗透版 API 客户端
    
    使用 stealth_client 突破服务器防御:
    - JA3/TLS 指纹伪装
    - HTTP/2 头顺序控制
    - 智能队名映射
    """
    
    def __init__(self, proxy_pool: Optional[List[str]] = None):
        """
        初始化 V38 客户端
        
        Args:
            proxy_pool: 代理池列表 (e.g., ["http://127.0.0.1:7890", ...])
        """
        self.stealth_client: StealthClient = None
        self.team_resolver: TeamAliasResolver = None
        self.proxy_pool = proxy_pool or []
        self.proxy_index = 0
        
    async def __aenter__(self):
        """异步上下文管理器入口"""
        self.stealth_client = await get_stealth_client()
        self.team_resolver = get_resolver()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        if self.stealth_client:
            await self.stealth_client.close()
    
    def _get_next_proxy(self) -> Optional[str]:
        """轮询获取下一个代理"""
        if not self.proxy_pool:
            return None
        proxy = self.proxy_pool[self.proxy_index]
        self.proxy_index = (self.proxy_index + 1) % len(self.proxy_pool)
        return proxy
    
    async def fetch_odds(self, match_id: str, source: str = "oddsportal") -> Optional[Dict]:
        """
        获取比赛赔率数据
        
        Args:
            match_id: 比赛 ID
            source: 数据源 (oddsportal, bet365, etc.)
            
        Returns:
            赔率数据字典，或 None（如果失败）
        """
        # 构造请求 URL
        url = f"https://www.oddsportal.com/soccer/match/{match_id}/"
        
        # 使用 stealth_client 发起请求（自动携带 Chrome 131 指纹）
        proxy = self._get_next_proxy()
        
        try:
            response = await self.stealth_client.fetch(
                url,
                proxy=proxy,
                headers={
                    # 额外的特定请求头
                    'referer': 'https://www.oddsportal.com/soccer/',
                    'accept': 'application/json, text/plain, */*'
                }
            )
            
            if response.status_code != 200:
                print(f"⚠️  请求失败: {response.status_code}")
                return None
            
            # 解析响应
            data = response.json() if 'json' in response.headers.get('content-type', '') else {}
            
            return {
                'match_id': match_id,
                'source': source,
                'data': data,
                'fetched_at': datetime.now().isoformat(),
                'proxy_used': proxy
            }
            
        except Exception as e:
            print(f"❌ 获取赔率失败: {e}")
            return None
    
    async def fetch_match_list(self, league: str, date: str) -> List[Dict]:
        """
        获取比赛列表
        
        Args:
            league: 联赛名称 (标准化后的)
            date: 日期 (YYYY-MM-DD)
            
        Returns:
            比赛列表
        """
        # 使用队名解析器确保联赛名正确
        standard_league = self.team_resolver.resolve(league) or league
        
        # 构造 API URL
        url = f"https://api.example.com/matches?league={standard_league}&date={date}"
        
        try:
            response = await self.stealth_client.fetch(url)
            
            if response.status_code == 200:
                data = response.json()
                matches = data.get('matches', [])
                
                # 标准化所有队名
                for match in matches:
                    match['home_team_std'] = self.team_resolver.resolve(
                        match.get('home_team', '')
                    )
                    match['away_team_std'] = self.team_resolver.resolve(
                        match.get('away_team', '')
                    )
                
                return matches
            else:
                print(f"⚠️  获取比赛列表失败: {response.status_code}")
                return []
                
        except Exception as e:
            print(f"❌ 获取比赛列表异常: {e}")
            return []
    
    async def validate_tls_fingerprint(self) -> Dict[str, Any]:
        """
        验证当前 TLS 指纹是否与 Chrome 131 一致
        
        Returns:
            指纹验证结果
        """
        result = await self.stealth_client.verify_fingerprint()
        
        expected_ja3 = "aa56c057ad164ec4fdcb7a5a283be9fc"
        actual_ja3 = result.get('ja3n_hash', 'unknown')
        
        return {
            'valid': actual_ja3 == expected_ja3,
            'expected_ja3': expected_ja3,
            'actual_ja3': actual_ja3,
            'tls_version': result.get('tls_version'),
            'user_agent': result.get('user_agent'),
            'timestamp': datetime.now().isoformat()
        }
    
    async def stealth_health_check(self) -> Dict[str, Any]:
        """
        执行全面的隐身健康检查
        
        检查项目:
        1. TLS 指纹匹配
        2. HTTP 连通性
        3. 队名解析器状态
        4. 代理池状态
        
        Returns:
            健康检查报告
        """
        print("🔍 执行 V38 隐身健康检查...")
        
        # 1. TLS 指纹检查
        tls_check = await self.validate_tls_fingerprint()
        print(f"   {'✅' if tls_check['valid'] else '❌'} TLS 指纹: {tls_check['actual_ja3'][:16]}...")
        
        # 2. HTTP 连通性检查
        http_check = {'status': 'unknown'}
        try:
            response = await self.stealth_client.fetch('https://httpbin.org/get')
            http_check = {
                'status': 'ok',
                'status_code': response.status_code,
                'latency_ms': getattr(response, 'elapsed', 0)
            }
            print(f"   ✅ HTTP 连通性: {response.status_code}")
        except Exception as e:
            http_check = {'status': 'error', 'error': str(e)}
            print(f"   ❌ HTTP 连通性: {e}")
        
        # 3. 队名解析器检查
        resolver_check = {
            'teams_count': len(self.team_resolver.get_all_teams()),
            'test_match': self.team_resolver.resolve('Man Utd')
        }
        print(f"   ✅ 队名解析器: {resolver_check['teams_count']} 支球队")
        
        # 4. 代理池检查
        proxy_check = {
            'pool_size': len(self.proxy_pool),
            'current_index': self.proxy_index
        }
        print(f"   ✅ 代理池: {proxy_check['pool_size']} 个节点")
        
        return {
            'tls_fingerprint': tls_check,
            'http_connectivity': http_check,
            'resolver': resolver_check,
            'proxy_pool': proxy_check,
            'overall_status': 'healthy' if tls_check['valid'] and http_check['status'] == 'ok' else 'degraded'
        }


# 便捷函数
async def fetch_odds_v38(match_id: str, proxy: Optional[str] = None) -> Optional[Dict]:
    """快捷函数：使用 V38 客户端获取赔率"""
    async with OddsAPIClientV38(proxy_pool=[proxy] if proxy else []) as client:
        return await client.fetch_odds(match_id)


async def health_check_v38() -> Dict[str, Any]:
    """快捷函数：执行 V38 健康检查"""
    async with OddsAPIClientV38() as client:
        return await client.stealth_health_check()


# 向后兼容：旧版 OddsAPIClient 的替代方案
class OddsAPIClient:
    """
    向后兼容包装器
    
    将旧版 OddsAPIClient 调用转发到 V38 实现
    """
    
    def __init__(self, *args, **kwargs):
        self._v38 = None
        self._args = args
        self._kwargs = kwargs
    
    async def __aenter__(self):
        self._v38 = await OddsAPIClientV38(*self._args, **self._kwargs).__aenter__()
        return self
    
    async def __aexit__(self, *args):
        return await self._v38.__aexit__(*args)
    
    async def fetch_odds(self, *args, **kwargs):
        """转发到 V38 实现"""
        return await self._v38.fetch_odds(*args, **kwargs)
    
    async def fetch_match_list(self, *args, **kwargs):
        """转发到 V38 实现"""
        return await self._v38.fetch_match_list(*args, **kwargs)
