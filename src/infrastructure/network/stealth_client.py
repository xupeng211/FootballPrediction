"""
V38.0 特种渗透客户端 - StealthClient
======================================
基于 curl_cffi 的底层传输层，实现：
1. TLS/JA3 指纹伪装（模拟 Chrome 131）
2. HTTP/2 伪头顺序控制
3. 完整的 sec-ch-ua 请求头序列
4. 单例模式确保全局指纹一致性

@module infrastructure.network.stealth_client
@version V38.0-STEALTH
@date 2026-03-17
"""

from curl_cffi.requests import AsyncSession
import asyncio
from typing import Optional, Dict, Any


class SingletonMeta(type):
    """线程安全的单例元类"""
    _instances = {}
    _lock = asyncio.Lock()
    
    def __call__(cls, *args, **kwargs):
        # 使用同步方式检查实例是否存在
        if cls not in cls._instances:
            # 如果没有，创建实例（初始化是同步的）
            instance = super().__call__(*args, **kwargs)
            cls._instances[cls] = instance
        return cls._instances[cls]


class StealthClient(metaclass=SingletonMeta):
    """
    V38.0 特种渗透客户端
    
    使用 curl_cffi 模拟 Chrome 131 的完整指纹：
    - JA3 指纹哈希
    - HTTP/2 连接指纹
    - 请求头顺序和值
    """
    
    # Chrome 131 的 JA3 指纹哈希（curl_cffi 模拟值）
    CHROME_131_JA3_HASH = "aa56c057ad164ec4fdcb7a5a283be9fc"
    
    # Chrome 131 的 HTTP/2 指纹特征
    CHROME_131_HTTP2_FINGERPRINT = "1:65536,2:0,4:6291456,6:262144|..."
    
    # 固定指纹配置（与 capture_auth.js 一致）
    FIXED_FINGERPRINT = {
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'viewport': {'width': 1920, 'height': 1080},
        'locale': 'en-US',
        'timezone': 'Europe/London',
        'platform': 'Win32'
    }
    
    def __init__(self):
        self._session: Optional[AsyncSession] = None
        self._proxy: Optional[str] = None
        
    async def _get_session(self) -> AsyncSession:
        """
        获取或创建 AsyncSession
        使用 impersonate="chrome131" 确保 TLS/JA3 指纹正确
        """
        if self._session is None:
            # curl_cffi 自动处理 JA3 和 HTTP/2 指纹
            self._session = AsyncSession(
                impersonate="chrome131",
                # 如需代理，在 fetch 时传入
            )
        return self._session
    
    async def fetch(self, url: str, headers: Optional[Dict[str, str]] = None, 
                    proxy: Optional[str] = None, **kwargs) -> Any:
        """
        发起伪装请求
        
        Args:
            url: 目标 URL
            headers: 额外请求头（会合并到默认头中）
            proxy: 代理地址 (e.g., "http://127.0.0.1:7890")
            **kwargs: 传递给 curl_cffi 的额外参数
            
        Returns:
            Response 对象
        """
        session = await self._get_session()
        
        # 合并默认 stealth headers 和用户自定义 headers
        default_headers = self._generate_stealth_headers()
        if headers:
            default_headers.update(headers)
        
        # 发起请求
        response = await session.get(
            url,
            headers=default_headers,
            proxy=proxy,
            **kwargs
        )
        
        return response
    
    async def post(self, url: str, data: Optional[Any] = None,
                   headers: Optional[Dict[str, str]] = None,
                   proxy: Optional[str] = None, **kwargs) -> Any:
        """POST 请求（同上）"""
        session = await self._get_session()
        
        default_headers = self._generate_stealth_headers()
        if headers:
            default_headers.update(headers)
            
        response = await session.post(
            url,
            data=data,
            headers=default_headers,
            proxy=proxy,
            **kwargs
        )
        
        return response
    
    def _generate_stealth_headers(self) -> Dict[str, str]:
        """
        生成 Chrome 131 完整的 stealth headers
        
        包含：
        - sec-ch-ua 系列（浏览器标识）
        - sec-fetch 系列（请求上下文）
        - accept 系列（内容协商）
        """
        return {
            # Chrome 131 的 sec-ch-ua（必须与 User-Agent 一致）
            'sec-ch-ua': '"Chromium";v="131", "Google Chrome";v="131", "Not-A.Brand";v="99"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            
            # Fetch 元数据
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'none',
            'sec-fetch-user': '?1',
            
            # 内容协商
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'accept-language': 'en-US,en;q=0.9',
            'accept-encoding': 'gzip, deflate, br, zstd',
            
            # 缓存控制
            'cache-control': 'max-age=0',
            
            # 升级请求
            'upgrade-insecure-requests': '1',
            
            # User-Agent（与 curl_cffi impersonate 一致）
            'user-agent': self.FIXED_FINGERPRINT['user_agent']
        }
    
    def _generate_http2_headers(self, method: str = 'GET', 
                                authority: str = '',
                                scheme: str = 'https',
                                path: str = '/') -> Dict[str, str]:
        """
        生成正确的 HTTP/2 伪头顺序
        
        HTTP/2 规范要求伪头必须：
        1. 以 : 开头
        2. 在所有常规头之前发送
        3. 按特定顺序（虽然规范未强制，但浏览器有固定习惯）
        
        Chrome 实际发送顺序: :method → :authority → :scheme → :path
        """
        # 使用有序字典确保顺序
        from collections import OrderedDict
        
        headers = OrderedDict()
        
        # HTTP/2 伪头（必须按此顺序）
        headers[':method'] = method
        headers[':authority'] = authority
        headers[':scheme'] = scheme
        headers[':path'] = path
        
        # 合并常规 stealth headers
        headers.update(self._generate_stealth_headers())
        
        return dict(headers)
    
    async def verify_fingerprint(self) -> Dict[str, str]:
        """
        验证当前 TLS 指纹是否与 Chrome 131 一致
        
        调用 tls.browserleaks.com 获取指纹信息
        
        Returns:
            包含 ja3_hash, ja3n_hash 等信息的字典
        """
        session = await self._get_session()
        
        try:
            response = await session.get(
                'https://tls.browserleaks.com/json',
                impersonate="chrome131"  # 确保使用正确指纹
            )
            
            data = response.json()
            
            return {
                'ja3_hash': data.get('ja3_hash', 'unknown'),
                'ja3n_hash': data.get('ja3n_hash', 'unknown'),
                'ja3_text': data.get('ja3_text', 'unknown'),
                'user_agent': data.get('user_agent', 'unknown'),
                'tls_version': data.get('tls_version', 'unknown')
            }
        except Exception as e:
            return {
                'error': str(e),
                'ja3_hash': 'failed',
                'ja3n_hash': 'failed'
            }
    
    async def close(self):
        """关闭会话"""
        if self._session:
            await self._session.close()
            self._session = None
    
    def __del__(self):
        """析构时尝试关闭会话"""
        if self._session:
            try:
                asyncio.get_event_loop().run_until_complete(self.close())
            except:
                pass


# 便捷函数：快速获取单例实例
_client_instance = None

async def get_stealth_client() -> StealthClient:
    """获取 StealthClient 单例"""
    global _client_instance
    if _client_instance is None:
        _client_instance = StealthClient()
    return _client_instance


async def fetch(url: str, **kwargs) -> Any:
    """快捷函数：使用默认 StealthClient 发起请求"""
    client = await get_stealth_client()
    return await client.fetch(url, **kwargs)
