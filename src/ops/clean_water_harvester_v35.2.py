#!/usr/bin/env python3
"""
V35.2 净水收割器 (Clean Water Harvester)
==========================================
具备高强度反爬和严苛校验的收割流水线

核心特性:
1. 深度反爬盔甲: UA池 + 随机延迟 + 指数退避
2. 零容忍校验: validatePayload 严格数据质量检查
3. 跨赛季正确抓取: 修正 season 参数格式
4. 慢速生产模式: concurrency=3 稳健收割
"""

import asyncio
import aiohttp
import json
import logging
import sys
import time
import random
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

# Add src to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import psycopg2
from psycopg2.extras import RealDictCursor
from src.config_unified import get_settings
from src.ml.miners_v34.greedy_miner import GreedyMiner

logger = logging.getLogger(__name__)


# V35.2: 扩展 UA 池 - 模拟真实浏览器
UA_POOL = [
    # Chrome 120 (Windows)
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',

    # Chrome 119 (Windows)
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',

    # Chrome 120 (Mac)
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',

    # Firefox 121 (Windows)
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',

    # Firefox 120 (Mac)
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:120.0) Gecko/20100101 Firefox/120.0',

    # Safari 17 (Mac)
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',

    # Edge 120 (Windows)
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',
]


# V35.2: Accept-Language 池
LANGUAGE_POOL = [
    'en-US,en;q=0.9,en-GB;q=0.8',
    'en-GB,en;q=0.9',
    'fr-FR,fr;q=0.9,en;q=0.8',
    'de-DE,de;q=0.9,en;q=0.8',
    'es-ES,es;q=0.9,en;q=0.8',
    'it-IT,it;q=0.9,en;q=0.8',
]


@dataclass
class HarvestStats:
    """收割统计"""
    total_matches: int = 0
    successful_harvests: int = 0
    failed_harvests: int = 0
    rejected_dirty: int = 0  # V35.2: 脏数据被拒绝
    holographic_data: int = 0
    legacy_data: int = 0
    retry_count: int = 0  # V35.2: 重试次数
    start_time: float = 0

    def __post_init__(self):
        if self.start_time == 0:
            self.start_time = time.time()

    def get_elapsed(self) -> float:
        return time.time() - self.start_time

    def get_rate(self) -> float:
        elapsed = self.get_elapsed()
        if elapsed > 0:
            return (self.successful_harvests / elapsed) * 60
        return 0


class CleanWaterHarvester:
    """
    V35.2 净水收割器

    核心改进:
    1. 深度反爬: UA轮换 + 随机延迟 + 指数退避
    2. 零容忍校验: validatePayload 严格检查
    3. 慢速生产: 低并发度, 高稳定性
    """

    def __init__(self, concurrency: int = 3):
        """初始化净水收割器"""
        self.concurrency = concurrency
        self.session: Optional[aiohttp.ClientSession] = None
        self.miner = GreedyMiner()
        self.stats = HarvestStats()
        self.db_conn = None
        self.match_index: List[Dict] = []

        # V35.2: 脏数据日志
        self.bad_matches_log = Path("data/logs/bad_matches_v35.2.log")
        self.bad_matches_log.parent.mkdir(parents=True, exist_ok=True)

    def _get_random_headers(self) -> Dict[str, str]:
        """V35.2: 生成随机请求头"""
        return {
            'User-Agent': random.choice(UA_POOL),
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': random.choice(LANGUAGE_POOL),
            'Accept-Encoding': 'gzip, deflate, br',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache',
            'Referer': 'https://www.fotmob.com/',
            'Origin': 'https://www.fotmob.com',
            'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Windows"',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-site',
        }

    def validate_payload(self, l2_data: Dict, match_id: int) -> Tuple[bool, str]:
        """
        V35.2: 零容忍数据校验

        规则:
        1. 必须包含 content.stats 或 content.shotmap
        2. 关键字段不能为空
        3. 数据结构必须完整

        Returns:
            (is_valid, reason): 是否通过校验及原因
        """
        # 检查 1: 必须有 content
        content = l2_data.get('content')
        if not content or not isinstance(content, dict):
            return False, "Missing or invalid 'content' field"

        # 检查 2: 必须有 stats 或 shotmap
        has_stats = bool(content.get('stats'))
        has_shotmap = bool(content.get('shotmap'))

        if not (has_stats or has_shotmap):
            return False, f"Missing both 'stats' and 'shotmap' (has_stats={has_stats}, has_shotmap={has_shotmap})"

        # 检查 3: 关键字段不能为空
        general = l2_data.get('general', {})
        if not general.get('homeTeam') or not general.get('awayTeam'):
            return False, "Missing home_team or away_team in general data"

        # 检查 4: match_id 必须存在且匹配
        api_match_id = general.get('matchId') or general.get('id')
        if api_match_id and int(api_match_id) != match_id:
            return False, f"Match ID mismatch: requested={match_id}, response={api_match_id}"

        # 检查 5: stats 数据质量检查
        if has_stats:
            stats = content['stats']
            if not isinstance(stats, dict):
                return False, "Invalid 'stats' format (not a dict)"

            # 至少要有一些统计组
            if len(stats) < 2:
                return False, f"Insufficient stats groups ({len(stats)} < 2)"

        return True, "OK"

    def _log_dirty_match(self, match_id: int, reason: str, l2_data: Dict):
        """记录脏数据到日志文件"""
        timestamp = datetime.now().isoformat()
        log_entry = {
            'timestamp': timestamp,
            'match_id': match_id,
            'rejection_reason': reason,
            'data_preview': {
                'has_content': bool(l2_data.get('content')),
                'has_stats': bool(l2_data.get('content', {}).get('stats')),
                'has_shotmap': bool(l2_data.get('content', {}).get('shotmap')),
                'has_general': bool(l2_data.get('general')),
            }
        }

        with open(self.bad_matches_log, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')

        logger.warning(f"🚫 脏数据拦截: MatchID {match_id} - {reason}")

    async def fetch_match_l2_with_retry(
        self,
        match_id: int,
        max_retries: int = 3
    ) -> Optional[Dict]:
        """
        V35.2: 带指数退避的 L2 数据获取

        Args:
            match_id: 比赛 ID
            max_retries: 最大重试次数

        Returns:
            L2 数据或 None
        """
        url = f"https://www.fotmob.com/api/matchDetails?matchId={match_id}"

        for attempt in range(max_retries):
            try:
                # V35.2: 随机延迟 (1-3 秒)
                if attempt > 0:
                    delay = random.uniform(1.0, 3.0) * (2 ** attempt)  # 指数退避
                    logger.info(f"⏳ 重试 {attempt + 1}/{max_retries}: MatchID {match_id}, 延迟 {delay:.1f}s")
                    await asyncio.sleep(delay)
                else:
                    # 首次请求也加一点随机延迟
                    await asyncio.sleep(random.uniform(0.5, 1.5))

                # V35.2: 随机 UA
                headers = self._get_random_headers()

                async with self.session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    if response.status != 200:
                        logger.warning(f"HTTP {response.status}: MatchID {match_id}")
                        continue

                    data = await response.json()

                    # V35.2: 零容忍校验
                    is_valid, reason = self.validate_payload(data, match_id)
                    if not is_valid:
                        self._log_dirty_match(match_id, reason, data)
                        self.stats.rejected_dirty += 1
                        return None  # 不重试脏数据

                    # 判断是否为 LEGACY_DATA
                    content = data.get('content', {})
                    is_legacy = not bool(content.get('stats'))

                    return {
                        'match_id': match_id,
                        'l2_json': data,
                        'is_legacy': is_legacy,
                    }

            except asyncio.TimeoutError:
                logger.warning(f"超时: MatchID {match_id} (尝试 {attempt + 1}/{max_retries})")
                self.stats.retry_count += 1
            except Exception as e:
                logger.error(f"获取失败: MatchID {match_id} - {e} (尝试 {attempt + 1}/{max_retries})")
                self.stats.retry_count += 1

        logger.error(f"❌ 达到最大重试次数: MatchID {match_id}")
        return None

    async def harvest_single_match(self, match_info: Dict) -> bool:
        """收割单场比赛"""
        match_id = match_info['match_id']

        try:
            # 获取 L2 JSON (带重试)
            l2_data = await self.fetch_match_l2_with_retry(match_id)
            if not l2_data:
                self.stats.failed_harvests += 1
                return False

            # 使用 GreedyMiner 提取全息特征
            holographic_features = self.miner.extract_all_features(
                l2_data['l2_json'],
                match_id=match_id
            )

            # 确定数据版本
            extraction_version = 'V35.2-HOLOGRAPHIC' if not l2_data['is_legacy'] else 'V35.2-LEGACY'

            if not l2_data['is_legacy']:
                self.stats.holographic_data += 1
            else:
                self.stats.legacy_data += 1

            # 计算版本指纹
            extraction_hash = self.miner.get_extraction_hash(l2_data['l2_json'])

            # 存储到数据库
            self.save_to_database(
                match_info,
                holographic_features,
                extraction_version,
                extraction_hash
            )

            self.stats.successful_harvests += 1
            return True

        except Exception as e:
            logger.error(f"收割失败: MatchID {match_id} - {e}")
            self.stats.failed_harvests += 1
            return False

    def save_to_database(self, match_info: Dict, holographic_features: Dict,
                        extraction_version: str, extraction_hash: str):
        """保存到数据库"""
        cursor = self.db_conn.cursor()

        enriched_data = {
            'holographic_features': holographic_features,
            'raw_match_info': match_info,
        }

        match_time = match_info.get('match_time')
        if match_time:
            try:
                match_time = datetime.fromisoformat(match_time.replace('Z', '+00:00'))
            except:
                match_time = datetime.now()
        else:
            match_time = datetime.now()

        cursor.execute("""
            INSERT INTO match_features_training (
                match_id, league_id, season_id, home_team, away_team,
                match_time, home_score, away_score, total_goals,
                enriched_features, extraction_version, extraction_logic_hash,
                extraction_timestamp, created_at, updated_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            ON CONFLICT (match_id) DO UPDATE SET
                enriched_features = EXCLUDED.enriched_features,
                extraction_version = EXCLUDED.extraction_version,
                extraction_logic_hash = EXCLUDED.extraction_logic_hash,
                extraction_timestamp = EXCLUDED.extraction_timestamp,
                updated_at = CURRENT_TIMESTAMP
        """, (
            int(match_info['match_id']),
            match_info.get('league_id'),
            match_info.get('season', ''),
            match_info['home_team'],
            match_info['away_team'],
            match_time,
            match_info.get('home_score'),
            match_info.get('away_score'),
            (match_info.get('home_score') or 0) + (match_info.get('away_score') or 0),
            json.dumps(enriched_data),
            extraction_version,
            extraction_hash,
            datetime.now(),
            datetime.now(),
            datetime.now(),
        ))

        self.db_conn.commit()
        cursor.close()

    def connect_db(self):
        """连接数据库"""
        import socket

        is_docker = os.getenv('DOCKER_ENV', 'false').lower() == 'true'
        db_host_env = os.getenv('DB_HOST', 'db')
        db_port = int(os.getenv('DB_PORT', 5432))
        db_name = os.getenv('DB_NAME', 'football_db')
        db_user = os.getenv('DB_USER', 'football_user')
        db_pass = os.getenv('DB_PASSWORD', 'football_pass')

        if not is_docker and db_host_env in ['db', 'database', 'postgres']:
            try:
                socket.create_connection(('localhost', 5432), timeout=1)
                db_host = 'localhost'
            except:
                db_host = db_host_env
        else:
            db_host = db_host_env

        self.db_conn = psycopg2.connect(
            host=db_host,
            port=db_port,
            database=db_name,
            user=db_user,
            password=db_pass
        )
        logger.info(f"✓ 数据库连接成功 (host={db_host})")

    def load_match_index(self, index_file: Path) -> int:
        """加载比赛索引"""
        with open(index_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        self.match_index = data.get('match_index', [])
        self.stats.total_matches = len(self.match_index)
        logger.info(f"✓ 加载比赛索引: {self.stats.total_matches:,} 场")
        return self.stats.total_matches

    def filter_harvested_matches(self) -> List[Dict]:
        """过滤已收割的比赛"""
        cursor = self.db_conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute("""
            SELECT match_id, league_id, season_id
            FROM match_features_training
            WHERE extraction_version LIKE 'V35.2%'
        """)

        harvested_keys = set()
        for row in cursor.fetchall():
            harvested_keys.add(f"{row['match_id']}_{row['league_id']}_{row['season_id']}")

        pending_matches = [
            m for m in self.match_index
            if f"{m['match_id']}_{m['league_id']}_{m['season']}" not in harvested_keys
        ]

        logger.info(f"✓ 已收割: {len(harvested_keys):,} 场")
        logger.info(f"✓ 待收割: {len(pending_matches):,} 场")

        cursor.close()
        return pending_matches

    async def harvest_batch(self, matches: List[Dict]) -> None:
        """批量收割"""
        semaphore = asyncio.Semaphore(self.concurrency)

        async def harvest_with_semaphore(match_info: Dict):
            async with semaphore:
                return await self.harvest_single_match(match_info)

        tasks = [harvest_with_semaphore(m) for m in matches]
        await asyncio.gather(*tasks, return_exceptions=True)

    async def __aenter__(self):
        """异步上下文管理器入口"""
        timeout = aiohttp.ClientTimeout(total=60)
        connector = aiohttp.TCPConnector(limit=5)  # V35.2: 降低连接池
        self.session = aiohttp.ClientSession(
            timeout=timeout,
            connector=connector
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器退出"""
        if self.session:
            await self.session.close()

    def print_progress(self, remaining: int):
        """打印进度"""
        elapsed = self.stats.get_elapsed()
        rate = self.stats.get_rate()

        print(f"\r💧 收割中: {self.stats.successful_harvests}/{self.stats.total_matches} "
              f"| 成功: {self.stats.successful_harvests} | 拒绝: {self.stats.rejected_dirty} | "
              f"全息: {self.stats.holographic_data} | 遗留: {self.stats.legacy_data} | "
              f"重试: {self.stats.retry_count} | "
              f"速度: {rate:.1f} 场/分", end='', flush=True)


async def main():
    """主函数"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    # 查找最新索引文件
    index_dir = Path("data/production/global_manifest_v34")
    v35_files = sorted(index_dir.glob("global_match_index_v35.1_*.json"))
    index_files = v35_files if v35_files else sorted(index_dir.glob("global_match_index_v34_*.json"))

    if not index_files:
        print("❌ 未找到索引文件")
        return

    index_file = index_files[-1]
    print(f"📂 使用索引文件: {index_file}")
    print(f"🎯 V35.2 净水收割模式 - 慢速生产")
    print(f"   - 并发度: 3 (稳健模式)")
    print(f"   - 随机延迟: 1-3 秒/请求")
    print(f"   - 零容忍校验: 启用")

    async with CleanWaterHarvester(concurrency=3) as harvester:
        harvester.load_match_index(index_file)
        harvester.connect_db()

        pending_matches = harvester.filter_harvested_matches()

        if not pending_matches:
            print("✅ 所有比赛已收割完成！")
            return

        print(f"\n🚀 开始收割 {len(pending_matches):,} 场比赛...")

        # 分批收割
        batch_size = 50
        for i in range(0, len(pending_matches), batch_size):
            batch = pending_matches[i:i + batch_size]
            remaining = len(pending_matches) - i

            await harvester.harvest_batch(batch)
            harvester.print_progress(remaining)

        # 最终统计
        print(f"\n\n{'=' * 70}")
        print("收割完成统计")
        print(f"{'=' * 70}")
        print(f"总比赛数: {harvester.stats.total_matches:,}")
        print(f"成功收割: {harvester.stats.successful_harvests:,}")
        print(f"拒绝脏数据: {harvester.stats.rejected_dirty:,}")
        print(f"失败: {harvester.stats.failed_harvests:,}")
        print(f"全息数据: {harvester.stats.holographic_data:,}")
        print(f"遗留数据: {harvester.stats.legacy_data:,}")
        print(f"重试次数: {harvester.stats.retry_count:,}")
        print(f"用时: {harvester.stats.get_elapsed() / 60:.1f} 分钟")
        print(f"平均速度: {harvester.stats.get_rate():.1f} 场/分钟")
        print(f"{'=' * 70}")


if __name__ == "__main__":
    asyncio.run(main())
