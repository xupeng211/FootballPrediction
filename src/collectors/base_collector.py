"""
基础数据采集器
Base Data Collector for Football-Data.org API
"""

import asyncio
import aiohttp
import time
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import os
from abc import ABC, abstractmethod
import json
import logging

logger = logging.getLogger(__name__)


class BaseCollector(ABC):
    """基础数据采集器抽象类"""

    def __init__(self):
        self.api_key = os.getenv('FOOTBALL_DATA_API_KEY', 'ed809154dc1f422da46a18d8961a98a0')
        self.base_url = os.getenv('FOOTBALL_DATA_BASE_URL', 'https://api.football-data.org/v4')
        self.rate_limit = int(os.getenv('FOOTBALL_DATA_RATE_LIMIT', '10'))
        self.cache_ttl = int(os.getenv('FOOTBALL_DATA_CACHE_TTL', '3600'))
        self.last_request_time = 0
        self.session = None

    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self._init_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        if self.session:
            await self.session.close()

    async def _init_session(self):
        """初始化HTTP会话"""
        if not self.session:
            timeout = aiohttp.ClientTimeout(total=30)
            headers = {
                'X-Auth-Token': self.api_key,
                'Content-Type': 'application/json'
            }
            self.session = aiohttp.ClientSession(
                timeout=timeout,
                headers=headers
            )

    async def _rate_limit(self):
        """API调用限流控制"""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time

        min_interval = 60 / self.rate_limit  # 每次请求最小间隔(秒)
        if time_since_last_request < min_interval:
            sleep_time = min_interval - time_since_last_request
            logger.info(f"Rate limiting: sleeping for {sleep_time:.2f} seconds")
            await asyncio.sleep(sleep_time)

        self.last_request_time = time.time()

    async def _make_request(self, endpoint: str, params: Optional[Dict[str, Any]] = None, max_retries: int = 3) -> Dict[str, Any]:
        """
        发起API请求（带重试机制）

        Args:
            endpoint: API端点
            params: 请求参数
            max_retries: 最大重试次数

        Returns:
            API响应数据
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        for attempt in range(max_retries + 1):
            try:
                await self._rate_limit()

                logger.debug(f"Attempt {attempt + 1}/{max_retries + 1}: Making request to {url}")

                async with self.session.get(url, params=params) as response:
                    # 检查HTTP状态码
                    if response.status == 200:
                        data = await response.json()
                        logger.debug(f"Successfully fetched data from {url}")
                        return data
                    elif response.status == 429:  # Rate limit exceeded
                        retry_after = int(response.headers.get('Retry-After', 60))
                        logger.warning(f"Rate limit exceeded. Waiting {retry_after} seconds...")
                        await asyncio.sleep(retry_after)
                        continue
                    elif response.status == 404:  # Not found
                        logger.warning(f"Resource not found: {url}")
                        return {"error": "Not found", "status": 404, "url": url}
                    elif response.status >= 500:  # Server error
                        if attempt < max_retries:
                            wait_time = 2 ** attempt  # Exponential backoff
                            logger.warning(f"Server error {response.status}. Retrying in {wait_time} seconds...")
                            await asyncio.sleep(wait_time)
                            continue
                        else:
                            logger.error(f"Server error {response.status} after {max_retries} retries")
                            raise aiohttp.ClientResponseError(response.status, response.reason)
                    else:
                        logger.error(f"HTTP error {response.status}: {response.reason}")
                        raise aiohttp.ClientResponseError(response.status, response.reason)

            except aiohttp.ClientError as e:
                if attempt < max_retries:
                    wait_time = 2 ** attempt
                    logger.warning(f"Network error (attempt {attempt + 1}): {e}. Retrying in {wait_time} seconds...")
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    logger.error(f"Network error after {max_retries} retries: {e}")
                    raise
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error: {e}")
                raise
            except asyncio.TimeoutError as e:
                if attempt < max_retries:
                    wait_time = 2 ** attempt
                    logger.warning(f"Timeout error (attempt {attempt + 1}): {e}. Retrying in {wait_time} seconds...")
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    logger.error(f"Timeout error after {max_retries} retries: {e}")
                    raise
            except Exception as e:
                logger.error(f"Unexpected error occurred: {e}")
                raise

        # 这里不应该到达，但作为安全网
        raise Exception("Unexpected: All retries exhausted without success")

    async def fetch_competitions(self) -> List[Dict[str, Any]]:
        """获取所有可用的比赛"""
        try:
            data = await self._make_request('competitions')
            return data.get('competitions', [])
        except Exception as e:
            logger.error(f"Failed to fetch competitions: {e}")
            return []

    async def fetch_teams(self, competition_id: str) -> List[Dict[str, Any]]:
        """获取指定比赛的球队列表"""
        try:
            data = await self._make_request(f'competitions/{competition_id}/teams')
            return data.get('teams', [])
        except Exception as e:
            logger.error(f"Failed to fetch teams for competition {competition_id}: {e}")
            return []

    async def fetch_matches(self, competition_id: str, **kwargs) -> List[Dict[str, Any]]:
        """
        获取比赛数据

        Args:
            competition_id: 比赛ID
            **kwargs: 其他过滤参数 (status, matchday, dateFrom, dateTo等)
        """
        try:
            data = await self._make_request(f'competitions/{competition_id}/matches', params=kwargs)
            return data.get('matches', [])
        except Exception as e:
            logger.error(f"Failed to fetch matches for competition {competition_id}: {e}")
            return []

    async def fetch_standings(self, competition_id: str) -> List[Dict[str, Any]]:
        """获取联赛积分榜"""
        try:
            data = await self._make_request(f'competitions/{competition_id}/standings')
            return data.get('standings', [])
        except Exception as e:
            logger.error(f"Failed to fetch standings for competition {competition_id}: {e}")
            return []

    async def fetch_team_matches(self, team_id: str, **kwargs) -> List[Dict[str, Any]]:
        """获取指定球队的比赛"""
        try:
            data = await self._make_request(f'teams/{team_id}/matches', params=kwargs)
            return data.get('matches', [])
        except Exception as e:
            logger.error(f"Failed to fetch matches for team {team_id}: {e}")
            return []

    @abstractmethod
    async def collect_data(self) -> Dict[str, Any]:
        """抽象方法：子类必须实现具体的数据采集逻辑"""
        pass

    def validate_api_key(self) -> bool:
        """验证API密钥格式"""
        return bool(self.api_key and len(self.api_key) == 32)

    def get_supported_competitions(self) -> List[str]:
        """获取支持的联赛列表"""
        competitions_str = os.getenv('FOOTBALL_DATA_COMPETITIONS', 'PL,CL,BL,SA,PD,FL1,ELC')
        return [comp.strip() for comp in competitions_str.split(',') if comp.strip()]

    def validate_response_data(self, data: Dict[str, Any], data_type: str) -> Dict[str, Any]:
        """
        验证API响应数据

        Args:
            data: API响应数据
            data_type: 数据类型 (competitions, teams, matches, standings)

        Returns:
            验证后的数据
        """
        try:
            if not isinstance(data, dict):
                raise ValueError(f"Expected dict for {data_type}, got {type(data)}")

            # 通用验证
            if 'error' in data:
                logger.warning(f"API returned error for {data_type}: {data['error']}")
                return data

            # 特定数据类型验证
            if data_type == 'competitions':
                return self._validate_competitions_data(data)
            elif data_type == 'teams':
                return self._validate_teams_data(data)
            elif data_type == 'matches':
                return self._validate_matches_data(data)
            elif data_type == 'standings':
                return self._validate_standings_data(data)
            else:
                return data

        except Exception as e:
            logger.error(f"Error validating {data_type} data: {e}")
            return {'error': f'Validation failed: {str(e)}', 'raw_data': data}

    def _validate_competitions_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """验证联赛数据"""
        competitions = data.get('competitions', [])
        if not isinstance(competitions, list):
            raise ValueError("Expected competitions to be a list")

        validated_competitions = []
        for comp in competitions:
            if self._validate_competition(comp):
                validated_competitions.append(comp)
            else:
                logger.warning(f"Invalid competition data: {comp}")

        return {'competitions': validated_competitions, 'count': len(validated_competitions)}

    def _validate_teams_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """验证球队数据"""
        teams = data.get('teams', [])
        if not isinstance(teams, list):
            raise ValueError("Expected teams to be a list")

        validated_teams = []
        for team in teams:
            if self._validate_team(team):
                validated_teams.append(team)
            else:
                logger.warning(f"Invalid team data: {team}")

        return {'teams': validated_teams, 'count': len(validated_teams)}

    def _validate_matches_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """验证比赛数据"""
        matches = data.get('matches', [])
        if not isinstance(matches, list):
            raise ValueError("Expected matches to be a list")

        validated_matches = []
        for match in matches:
            if self._validate_match(match):
                validated_matches.append(match)
            else:
                logger.warning(f"Invalid match data: {match}")

        return {'matches': validated_matches, 'count': len(validated_matches)}

    def _validate_standings_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """验证积分榜数据"""
        standings = data.get('standings', [])
        if not isinstance(standings, list):
            raise ValueError("Expected standings to be a list")

        validated_standings = []
        for standing in standings:
            if self._validate_standing(standing):
                validated_standings.append(standing)
            else:
                logger.warning(f"Invalid standing data: {standing}")

        return {'standings': validated_standings, 'count': len(validated_standings)}

    def _validate_competition(self, competition: Dict[str, Any]) -> bool:
        """验证单个联赛数据"""
        required_fields = ['id', 'name', 'code']
        return all(competition.get(field) is not None for field in required_fields)

    def _validate_team(self, team: Dict[str, Any]) -> bool:
        """验证单个球队数据"""
        required_fields = ['id', 'name']
        return all(team.get(field) is not None for field in required_fields)

    def _validate_match(self, match: Dict[str, Any]) -> bool:
        """验证单个比赛数据"""
        required_fields = ['id', 'homeTeam', 'awayTeam', 'status']
        return all(match.get(field) is not None for field in required_fields)

    def _validate_standing(self, standing: Dict[str, Any]) -> bool:
        """验证单个积分榜数据"""
        return 'table' in standing and isinstance(standing['table'], list)

    def clean_data(self, data: Dict[str, Any], data_type: str) -> Dict[str, Any]:
        """
        清洗数据

        Args:
            data: 原始数据
            data_type: 数据类型

        Returns:
            清洗后的数据
        """
        try:
            if data_type == 'competitions':
                return self._clean_competitions_data(data)
            elif data_type == 'teams':
                return self._clean_teams_data(data)
            elif data_type == 'matches':
                return self._clean_matches_data(data)
            elif data_type == 'standings':
                return self._clean_standings_data(data)
            else:
                return data

        except Exception as e:
            logger.error(f"Error cleaning {data_type} data: {e}")
            return data

    def _clean_competitions_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """清洗联赛数据"""
        competitions = data.get('competitions', [])
        cleaned_competitions = []

        for comp in competitions:
            cleaned_comp = {
                'id': comp.get('id'),
                'name': comp.get('name'),
                'code': comp.get('code'),
                'type': comp.get('type', 'LEAGUE'),
                'emblem': comp.get('emblem'),
                'area': {
                    'id': comp.get('area', {}).get('id'),
                    'name': comp.get('area', {}).get('name'),
                    'code': comp.get('area', {}).get('code')
                }
            }
            cleaned_competitions.append(cleaned_comp)

        return {'competitions': cleaned_competitions}

    def _clean_teams_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """清洗球队数据"""
        teams = data.get('teams', [])
        cleaned_teams = []

        for team in teams:
            cleaned_team = {
                'id': team.get('id'),
                'name': team.get('name'),
                'short_name': team.get('shortName'),
                'tla': team.get('tla'),
                'crest': team.get('crest'),
                'address': team.get('address'),
                'website': team.get('website'),
                'founded': team.get('founded'),
                'club_colors': team.get('clubColors'),
                'venue': team.get('venue'),
                'area': team.get('area', {}),
                'coach': team.get('coach', {}),
                'squad': team.get('squad', [])
            }
            cleaned_teams.append(cleaned_team)

        return {'teams': cleaned_teams}

    def _clean_matches_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """清洗比赛数据"""
        matches = data.get('matches', [])
        cleaned_matches = []

        for match in matches:
            cleaned_match = {
                'id': match.get('id'),
                'utcDate': match.get('utcDate'),
                'status': match.get('status'),
                'matchday': match.get('matchday'),
                'stage': match.get('stage'),
                'group': match.get('group'),
                'lastUpdated': match.get('lastUpdated'),
                'homeTeam': match.get('homeTeam', {}),
                'awayTeam': match.get('awayTeam', {}),
                'score': match.get('score', {}),
                'odds': match.get('odds'),
                'referees': match.get('referees', [])
            }
            cleaned_matches.append(cleaned_match)

        return {'matches': cleaned_matches}

    def _clean_standings_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """清洗积分榜数据"""
        standings = data.get('standings', [])
        cleaned_standings = []

        for standing in standings:
            cleaned_standing = {
                'stage': standing.get('stage'),
                'type': standing.get('type', 'TOTAL'),
                'group': standing.get('group'),
                'table': standing.get('table', [])
            }
            cleaned_standings.append(cleaned_standing)

        return {'standings': cleaned_standings}


class FootballDataCollector(BaseCollector):
    """Football-Data.org 数据采集器"""

    def __init__(self):
        super().__init__()
        self.supported_competitions = self.get_supported_competitions()

    async def collect_data(self) -> Dict[str, Any]:
        """
        收集所有支持的比赛数据

        Returns:
            包含比赛、球队、比赛数据等的字典
        """
        results = {
            'timestamp': datetime.utcnow().isoformat(),
            'competitions': [],
            'teams': {},
            'matches': {},
            'standings': {},
            'errors': []
        }

        if not self.validate_api_key():
            results['errors'].append("Invalid API key")
            return results

        try:
            # 获取支持的联赛信息
            all_competitions = await self.fetch_competitions()
            supported_competitions = [
                comp for comp in all_competitions
                if comp.get('code') in self.supported_competitions
            ]
            results['competitions'] = supported_competitions

            # 为每个联赛收集数据
            for competition in supported_competitions:
                comp_id = competition['id']
                comp_code = competition['code']

                try:
                    logger.info(f"Collecting data for competition: {comp_code}")

                    # 收集球队数据
                    teams = await self.fetch_teams(str(comp_id))
                    results['teams'][comp_code] = teams

                    # 收集比赛数据（包含已结束、进行中、即将开始的比赛）
                    matches = await self.fetch_matches(
                        str(comp_id),
                        status='FINISHED',  # 已结束的比赛
                        limit=50
                    )
                    results['matches'][f"{comp_code}_finished"] = matches

                    scheduled_matches = await self.fetch_matches(
                        str(comp_id),
                        status='SCHEDULED',  # 即将开始的比赛
                        limit=20
                    )
                    results['matches'][f"{comp_code}_scheduled"] = scheduled_matches

                    # 收集积分榜数据
                    standings = await self.fetch_standings(str(comp_id))
                    results['standings'][comp_code] = standings

                    logger.info(f"Successfully collected data for {comp_code}")

                except Exception as e:
                    error_msg = f"Failed to collect data for {comp_code}: {e}"
                    logger.error(error_msg)
                    results['errors'].append(error_msg)
                    continue

        except Exception as e:
            error_msg = f"General collection error: {e}"
            logger.error(error_msg)
            results['errors'].append(error_msg)

        return results

    async def collect_competition_data(self, competition_code: str) -> Dict[str, Any]:
        """
        收集特定联赛的数据

        Args:
            competition_code: 联赛代码 (如 PL, CL等)
        """
        if competition_code not in self.supported_competitions:
            raise ValueError(f"Unsupported competition: {competition_code}")

        # 获取联赛信息
        all_competitions = await self.fetch_competitions()
        competition = next((comp for comp in all_competitions if comp.get('code') == competition_code), None)

        if not competition:
            raise ValueError(f"Competition {competition_code} not found")

        comp_id = competition['id']

        results = {
            'competition': competition,
            'teams': await self.fetch_teams(str(comp_id)),
            'matches': await self.fetch_matches(str(comp_id), limit=100),
            'standings': await self.fetch_standings(str(comp_id)),
            'timestamp': datetime.utcnow().isoformat()
        }

        return results