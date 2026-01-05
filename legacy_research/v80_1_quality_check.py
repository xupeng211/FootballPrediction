#!/usr/bin/env python3
"""
V80.1 质量验证脚本 - 随机抽样检查
"""

import logging
import random
import sys
from datetime import datetime
from pathlib import Path

import psycopg2
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config_unified import get_settings

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('logs/v80_1_quality_check.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def get_db_connection():
    """获取数据库连接"""
    settings = get_settings()
    return psycopg2.connect(
        host=settings.database.host,
        port=settings.database.port,
        database=settings.database.name,
        user=settings.database.user,
        password=settings.database.password.get_secret_value()
    )


def get_recent_urls(limit=30):
    """获取最近添加的 URL"""
    conn = get_db_connection()
    cur = conn.cursor()

    # 获取最近的 URL（按更新时间排序）
    cur.execute("""
        SELECT
            m.match_id,
            m.home_team,
            m.away_team,
            m.match_date,
            m.league_name,
            m.season,
            m.oddsportal_url
        FROM matches m
        WHERE m.oddsportal_url IS NOT NULL
        ORDER BY m.updated_at DESC
        LIMIT %s
    """, (limit,))

    results = cur.fetchall()

    cur.close()
    conn.close()

    return results


def verify_team_name_match(db_home, db_away, url):
    """验证 URL 中的球队名称是否匹配数据库"""
    # 从 URL 中提取球队名称
    # URL 格式: https://www.oddsportal.com/football/country/league-season/home-away-hash/
    try:
        parts = url.strip('/').split('/')
        if len(parts) >= 7:
            # 最后部分包含 home-away-hash
            home_away_hash = parts[-1]

            # 从右向左查找最后一个连字符，分离哈希 ID
            last_dash = home_away_hash.rfind('-')
            if last_dash > 0:
                home_away = home_away_hash[:last_dash]

                # 按第一个连字符分割主客队
                first_dash = home_away.find('-')
                if first_dash > 0:
                    url_home = home_away[:first_dash]
                    url_away = home_away[first_dash + 1:]

                    # 标准化（连字符转空格，首字母大写）
                    url_home_normalized = url_home.replace('-', ' ').title()
                    url_away_normalized = url_away.replace('-', ' ').title()

                    # 检查匹配
                    home_match = (url_home_normalized == db_home) or (url_home_normalized in db_home) or (db_home in url_home_normalized)
                    away_match = (url_away_normalized == db_away) or (url_away_normalized in db_away) or (db_away in url_away_normalized)

                    return home_match, away_match, url_home_normalized, url_away_normalized
    except Exception as e:
        logger.warning(f"解析 URL 失败: {e}")

    return False, False, None, None


def verify_url_accessible(url, timeout=10):
    """验证 URL 是否可访问"""
    try:
        # 配置重试策略
        retry_strategy = Retry(
            total=2,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session = requests.Session()
        session.mount("https://", adapter)
        session.mount("http://", adapter)

        # 发送 HEAD 请求（比 GET 更快）
        response = session.head(url, timeout=timeout, allow_redirects=True)

        # 200, 301, 302 都是正常响应
        return response.status_code in [200, 301, 302], response.status_code
    except Exception as e:
        logger.warning(f"URL 访问检查失败: {e}")
        return False, None


def quality_check(samples=30):
    """执行质量检查"""
    logger.info("=" * 60)
    logger.info("V80.1 质量验证 - 随机抽样检查")
    logger.info("=" * 60)
    logger.info(f"抽样数量: {samples}")
    logger.info("")

    # 获取样本
    records = get_recent_urls(samples)
    logger.info(f"获取到 {len(records)} 条记录")
    logger.info("")

    # 统计变量
    total = len(records)
    name_match_count = 0
    url_accessible_count = 0
    url_errors = []

    # 逐条验证
    for i, record in enumerate(records, 1):
        match_id, home_team, away_team, match_date, league, season, url = record

        logger.info(f"[{i}/{total}] {league} {season}: {home_team} vs {away_team}")

        # 1. 验证球队名称匹配
        home_match, away_match, url_home, url_away = verify_team_name_match(home_team, away_team, url)

        if home_match and away_match:
            name_match_count += 1
            logger.info(f"  ✅ 球队名称匹配: {url_home} vs {url_away}")
        else:
            logger.warning(f"  ⚠️  球队名称不匹配:")
            logger.warning(f"      数据库: {home_team} vs {away_team}")
            logger.warning(f"      URL:    {url_home} vs {url_away}")

        # 2. 验证 URL 可访问性（抽样检查前 10 条）
        if i <= 10:
            accessible, status = verify_url_accessible(url)
            if accessible:
                url_accessible_count += 1
                logger.info(f"  ✅ URL 可访问 (HTTP {status})")
            else:
                url_errors.append((match_id, url, status))
                if status:
                    logger.warning(f"  ⚠️  URL 返回异常状态: HTTP {status}")
                else:
                    logger.warning(f"  ⚠️  URL 无法访问")

        logger.info("")

    # 最终报告
    logger.info("=" * 60)
    logger.info("质量验证最终报告")
    logger.info("=" * 60)
    logger.info(f"总样本数: {total}")
    logger.info(f"球队名称匹配: {name_match_count}/{total} ({100*name_match_count/total:.1f}%)")
    logger.info(f"URL 可访问性: {url_accessible_count}/10 ({100*url_accessible_count/10:.1f}%)")
    logger.info("")

    if url_errors:
        logger.warning("URL 访问错误详情:")
        for match_id, url, status in url_errors:
            logger.warning(f"  Match {match_id}: {url} (HTTP {status})")

    # 结论
    logger.info("")
    if name_match_count == total:
        logger.info("✅ 数据质量: 优秀 - 所有球队名称均匹配")
    elif name_match_count >= total * 0.9:
        logger.info("✅ 数据质量: 良好 - 90%+ 球队名称匹配")
    elif name_match_count >= total * 0.8:
        logger.info("⚠️  数据质量: 一般 - 80-90% 球队名称匹配")
    else:
        logger.info("❌ 数据质量: 需要改进 - <80% 球队名称匹配")

    return {
        'total': total,
        'name_match': name_match_count,
        'name_match_rate': 100 * name_match_count / total,
        'url_accessible': url_accessible_count,
        'url_accessible_rate': 100 * url_accessible_count / 10,
        'url_errors': url_errors
    }


if __name__ == "__main__":
    result = quality_check(samples=30)
