#!/usr/bin/env python3
"""
V36.0 纯净破冰收割器 - 直接从 Manifest 收割历史数据
=======================================================
突破发现: 现有 manifest 文件已包含 22/23、23/24 赛季 Match IDs
直接收割，无需发现
"""

import asyncio
import aiohttp
import csv
import json
import logging
import random
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set

logger = logging.getLogger(__name__)

# V35.2 继承: UA 池
UA_POOL = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
]

LANGUAGE_POOL = [
    'en-US,en;q=0.9,en-GB;q=0.8',
    'en-GB,en;q=0.9',
    'fr-FR,fr;q=0.9,en;q=0.8',
]


@dataclass
class HarvestStats:
    """收割统计"""
    total_targets: int = 0
    successful_harvests: int = 0
    failed_harvests: int = 0
    rejected_dirty: int = 0
    high_quality_data: int = 0  # > 100KB 响应
    medium_quality_data: int = 0  # 50-100KB
    low_quality_data: int = 0  # < 50KB
    start_time: float = field(default_factory=time.time)

    def get_elapsed(self) -> float:
        return time.time() - self.start_time

    def get_rate(self) -> float:
        elapsed = self.get_elapsed()
        if elapsed > 0:
            return self.successful_harvests / elapsed * 60
        return 0


class IceBreakerHarvester:
    """
    V36.0 纯净破冰收割器

    策略:
    1. 从现有 manifest 读取 Match IDs
    2. 使用 /matchDetails 端点获取完整数据
    3. 零容忍校验 + V35.2 反爬机制
    """

    def __init__(self, concurrency: int = 3):
        self.concurrency = concurrency
        self.session: Optional[aiohttp.ClientSession] = None
        self.stats = HarvestStats()
        self.harvested_ids: Set[int] = set()

    def _get_random_headers(self) -> Dict[str, str]:
        return {
            'User-Agent': random.choice(UA_POOL),
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': random.choice(LANGUAGE_POOL),
            'Accept-Encoding': 'gzip, deflate, br',
            'Cache-Control': 'no-cache',
            'Referer': 'https://www.fotmob.com/',
            'Origin': 'https://www.fotmob.com',
        }

    def validate_payload(self, data: Dict, match_id: int) -> tuple[bool, str]:
        """零容忍数据校验"""
        # 检查 1: 必须有 content
        if 'content' not in data:
            return False, "Missing 'content' field"

        content = data['content']

        # 检查 2: 必须有 stats 或 shotmap
        has_stats = 'stats' in content
        has_shotmap = 'shotmap' in content

        if not (has_stats or has_shotmap):
            return False, f"Missing both 'stats' and 'shotmap'"

        # 检查 3: 必须有 header
        if 'header' not in data:
            return False, "Missing 'header' field"

        # 检查 4: header 必须有球队信息
        header = data['header']
        if 'teams' not in header or len(header['teams']) < 2:
            return False, "Invalid header structure"

        return True, "OK"

    async def fetch_match_details(
        self,
        match_id: int,
        max_retries: int = 3
    ) -> Optional[Dict]:
        """获取比赛详情"""
        url = f"https://www.fotmob.com/api/matchDetails?matchId={match_id}"

        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    delay = random.uniform(1.0, 2.0) * (1.5 ** attempt)
                    await asyncio.sleep(delay)

                # 首次请求也加随机延迟
                if attempt == 0:
                    await asyncio.sleep(random.uniform(0.3, 0.8))

                headers = self._get_random_headers()

                async with self.session.get(
                    url,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status != 200:
                        logger.warning(f"HTTP {response.status}: Match {match_id}")
                        continue

                    content_bytes = await response.read()
                    data = await response.json()

                    # V35.2 哨兵检查: 响应大小
                    size = len(content_bytes)
                    if size < 50000:  # 50KB 最低阈值
                        logger.warning(f"⚠️ 响应过小: Match {match_id} ({size} bytes)")
                        self.stats.rejected_dirty += 1
                        return None

                    # 零容忍校验
                    is_valid, reason = self.validate_payload(data, match_id)
                    if not is_valid:
                        logger.warning(f"🚫 校验失败: Match {match_id} - {reason}")
                        self.stats.rejected_dirty += 1
                        return None

                    # 记录质量等级
                    if size > 100000:
                        self.stats.high_quality_data += 1
                    elif size > 50000:
                        self.stats.medium_quality_data += 1
                    else:
                        self.stats.low_quality_data += 1

                    self.stats.successful_harvests += 1
                    logger.info(f"✅ Match {match_id}: {size:,} bytes")

                    return data

            except asyncio.TimeoutError:
                logger.warning(f"⏰ 超时: Match {match_id}")
            except Exception as e:
                logger.warning(f"❌ 错误: Match {match_id} - {e}")

        self.stats.failed_harvests += 1
        return None

    def load_manifest(self, manifest_path: str) -> List[Dict]:
        """加载 manifest 文件"""
        matches = []

        with open(manifest_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                match_id = row.get('match_id') or row.get('id')
                if match_id:
                    matches.append({
                        'match_id': int(match_id),
                        'home_team': row.get('home_team') or row.get('home'),
                        'away_team': row.get('away_team') or row.get('away'),
                        'league_id': int(row.get('league_id', 47)),
                        'season': row.get('season', '2223'),
                    })

        logger.info(f"✓ 加载 manifest: {len(matches)} 场比赛")
        return matches

    async def harvest_batch(self, matches: List[Dict]) -> None:
        """批量收割"""
        semaphore = asyncio.Semaphore(self.concurrency)

        async def harvest_with_semaphore(match_info: Dict):
            async with semaphore:
                match_id = match_info['match_id']

                # 跳过已收割
                if match_id in self.harvested_ids:
                    return

                data = await self.fetch_match_details(match_id)
                if data:
                    self.harvested_ids.add(match_id)

                    # TODO: 存储到数据库
                    # 这里可以调用 V35.2 的净水收割机存储逻辑

        tasks = [harvest_with_semaphore(m) for m in matches]
        await asyncio.gather(*tasks, return_exceptions=True)

    def print_progress(self, total: int, remaining: int):
        """打印进度"""
        elapsed = self.stats.get_elapsed()
        rate = self.stats.get_rate()
        progress = (total - remaining) / total * 100

        print(f"\r💧 收割中: {progress:.1f}% "
              f"| 成功: {self.stats.successful_harvests} "
              f"| 拒绝: {self.stats.rejected_dirty} "
              f"| 失败: {self.stats.failed_harvests} "
              f"| 高质量: {self.stats.high_quality_data} "
              f"| 速度: {rate:.1f} 场/分", end='', flush=True)

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=60),
            connector=aiohttp.TCPConnector(limit=5)
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()


async def main():
    """主函数"""
    logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')

    print("\n" + "=" * 70)
    print("🧊 V36.0 纯净破冰收割器")
    print("=" * 70)
    print("策略: 从现有 manifest 直接收割历史数据")
    print("=" * 70 + "\n")

    # 目标 manifest 文件
    manifests = [
        'data/production/manifest_47_2223.csv',  # 英超 22/23
        'data/production/manifest_47_2324.csv',  # 英超 23/24
    ]

    all_matches = []

    for manifest_path in manifests:
        path = Path(manifest_path)
        if path.exists():
            print(f"📂 加载: {manifest_path}")

            async with IceBreakerHarvester(concurrency=3) as harvester:
                matches = harvester.load_manifest(manifest_path)
                all_matches.extend(matches)

                harvester.stats.total_targets = len(matches)

                print(f"\n🚀 开始收割 {len(matches)} 场比赛...\n")

                batch_size = 50
                for i in range(0, len(matches), batch_size):
                    batch = matches[i:i + batch_size]
                    remaining = len(matches) - i

                    await harvester.harvest_batch(batch)
                    harvester.print_progress(len(matches), remaining)

    # 最终统计
    print(f"\n\n{'=' * 70}")
    print("收割完成统计")
    print(f"{'=' * 70}")
    print(f"总目标: {sum(m['match_id'] for m in all_matches) % 1000000} 场")
    print(f"成功收割: {sum(h.stats.successful_harvests for h in [all_matches[0] if all_matches else None] if h) or 0} 场")
    print(f"拒绝脏数据: {sum(h.stats.rejected_dirty for h in [all_matches[0] if all_matches else None] if h) or 0}")
    print(f"失败: {sum(h.stats.failed_harvests for h in [all_matches[0] if all_matches else None] if h) or 0}")
    print(f"{'=' * 70}\n")


if __name__ == "__main__":
    asyncio.run(main())
