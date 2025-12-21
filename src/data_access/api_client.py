"""
FootballPrediction V7.0 API客户端模块
封装FotMob API的所有请求，带UA伪装、错误重试和速率限制
"""

import time
import random
import logging
import requests
from typing import Dict, Any, Optional, List
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from src.core.config import get_config

logger = logging.getLogger(__name__)

class FotMobAPIClient:
    """FotMob API客户端 - 统一API请求管理"""

    def __init__(self, config=None):
        self.config = config or get_config()
        self.session = self._create_session()
        self.request_count = 0
        self.last_request_time = 0

    def _create_session(self) -> requests.Session:
        """创建带有重试策略的session"""
        session = requests.Session()

        # 配置重试策略
        retry_strategy = Retry(
            total=self.config.api.retry_attempts,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"]
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        # 设置请求头
        session.headers.update(self.config.api.fotmob_headers)

        return session

    def _rate_limit(self):
        """速率限制"""
        current_time = time.time()
        delay_range = self.config.api.rate_limit_delay

        if self.last_request_time > 0:
            elapsed = current_time - self.last_request_time
            min_delay = delay_range[0]

            if elapsed < min_delay:
                sleep_time = min_delay - elapsed + random.uniform(0, delay_range[1] - min_delay)
                logger.debug(f"Rate limiting: sleeping {sleep_time:.2f} seconds")
                time.sleep(sleep_time)

        self.last_request_time = time.time()
        self.request_count += 1

    def _make_request(self, url: str, params: Dict[str, Any] = None, timeout: int = None) -> Optional[Dict[str, Any]]:
        """发起API请求"""
        self._rate_limit()

        if timeout is None:
            timeout = self.config.api.request_timeout

        try:
            logger.debug(f"API请求: {url} 参数={params}")
            response = self.session.get(url, params=params, timeout=timeout)
            response.raise_for_status()

            data = response.json()
            self.request_count += 1
            logger.debug(f"API响应成功: {len(str(data))} bytes")

            return data

        except requests.exceptions.RequestException as e:
            logger.error(f"API请求失败 {url}: {e}")
            return None
        except ValueError as e:
            logger.error(f"JSON解析失败 {url}: {e}")
            return None

    def get_league_matches(self, league_id: str = None, tab: str = "results") -> Optional[Dict[str, Any]]:
        """获取联赛比赛列表"""
        if league_id is None:
            league_id = self.config.harvest.league_id

        url = f"{self.config.api.fotmob_base_url}/leagues"
        params = {
            "id": league_id,
            "tab": tab
        }

        return self._make_request(url, params)

    def get_match_details(self, match_id: str) -> Optional[Dict[str, Any]]:
        """获取比赛详情"""
        url = f"{self.config.api.fotmob_base_url}/matchDetails"
        params = {"matchId": match_id}

        return self._make_request(url, params)

    def get_team_stats(self, team_id: str, league_id: str = None) -> Optional[Dict[str, Any]]:
        """获取球队统计"""
        if league_id is None:
            league_id = self.config.harvest.league_id

        url = f"{self.config.api.fotmob_base_url}/teamStats"
        params = {
            "teamId": team_id,
            "leagueId": league_id
        }

        return self._make_request(url, params)

    def get_player_stats(self, player_id: str) -> Optional[Dict[str, Any]]:
        """获取球员统计"""
        url = f"{self.config.api.fotmob_base_url}/playerData"
        params = {"id": player_id}

        return self._make_request(url, params)

    def search_team(self, team_name: str) -> Optional[List[Dict[str, Any]]]:
        """搜索球队"""
        url = f"{self.config.api.fotmob_base_url}/searchAPI"
        params = {
            "term": team_name,
            "type": "team"
        }

        result = self._make_request(url, params)
        if result and 'teams' in result:
            return result['teams']
        return None

    def get_season_matches(self, league_id: str = None, season: str = None) -> List[Dict[str, Any]]:
        """获取赛季所有已完成比赛"""
        if league_id is None:
            league_id = self.config.harvest.league_id
        if season is None:
            season = self.config.harvest.season

        logger.info(f"获取联赛 {league_id} 赛季 {season} 比赛列表")

        data = self.get_league_matches(league_id, "results")
        if not data:
            logger.warning("未能获取联赛数据")
            return []

        # 提取比赛数据
        fixtures = data.get('fixtures', {})
        matches_data = fixtures.get('allMatches', []) or []

        if not matches_data:
            logger.warning("未找到比赛数据")
            return []

        # 过滤已完成的比赛
        completed_matches = []
        for match in matches_data:
            match_id = match.get('id')
            status = match.get('status', {})

            if match_id and isinstance(status, dict):
                finished = status.get('finished', False)

                if finished:
                    completed_matches.append({
                        'match_id': str(match_id),
                        'home_team': match.get('home', {}).get('name', 'Unknown'),
                        'away_team': match.get('away', {}).get('name', 'Unknown'),
                        'status': 'finished',
                        'league_id': league_id,
                        'season': season
                    })

        logger.info(f"获取到 {len(completed_matches)} 场已完成比赛")
        return completed_matches

    def get_request_stats(self) -> Dict[str, Any]:
        """获取请求统计信息"""
        return {
            "total_requests": self.request_count,
            "last_request_time": self.last_request_time,
            "session_id": id(self.session)
        }

    def close(self):
        """关闭session"""
        if self.session:
            self.session.close()
            logger.info("API客户端已关闭")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# 便利函数
def get_api_client() -> FotMobAPIClient:
    """获取API客户端实例"""
    return FotMobAPIClient()

def api_request_wrapper(func):
    """API请求装饰器，添加日志和错误处理"""
    def wrapper(*args, **kwargs):
        try:
            result = func(*args, **kwargs)
            if result is None:
                logger.warning(f"API请求返回None: {func.__name__}")
            return result
        except Exception as e:
            logger.error(f"API请求异常 {func.__name__}: {e}")
            return None
    return wrapper