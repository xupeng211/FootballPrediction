#!/usr/bin/env python3
"""
V39.0 Multi-Source Hash Hunter - 自适应映射引擎

核心功能:
1. 多源搜索策略：
   - Level 1: 标准 OddsPortal 站内搜索
   - Level 2: 队名变体搜索（使用 team_alias.py）
   - Level 3: 历史别名库回退
2. TDD 保护：验证映射正确性，防止 "Real Madrid → Almeria" 错误
3. 置信度评分：85% 以上自动准入，以下人工审核

准入红线：禁止存储置信度低于 85% 的映射！

Author: 首席数据采集官 & 算法专家
Version: V39.0 Multi-Source Hash Hunter
Date: 2026-01-12
"""

import asyncio
import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.utils.team_alias import (
    normalize_team_name,
    expand_team_name,
    match_teams,
    is_safe_confidence,
    calculate_similarity,
    CONFIDENCE_THRESHOLD
)
from src.config_unified import get_settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('logs/hunt_league_hashes_v39.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# ============================================================================
# Database Operations
# ============================================================================

def get_missing_matches(limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """从 matches 表获取不在 matches_mapping 中的比赛（所有联赛）

    Args:
        limit: 最大返回数量

    Returns:
        比赛列表
    """
    import psycopg2

    settings = get_settings()
    matches = []

    try:
        conn = psycopg2.connect(
            host=settings.database.host,
            port=settings.database.port,
            database=settings.database.name,
            user=settings.database.user,
            password=settings.database.password.get_secret_value()
        )
        cursor = conn.cursor()

        # V39.0: 查询所有联赛的缺失比赛（不限特定联赛）
        limit_clause = f"LIMIT {limit}" if limit else ""
        query = f"""
            SELECT
                m.match_id as fotmob_id,
                m.home_team,
                m.away_team,
                m.league_name,
                m.match_date,
                m.season
            FROM matches m
            WHERE NOT EXISTS (
                SELECT 1 FROM matches_mapping mm
                WHERE mm.fotmob_id = m.match_id
            )
            ORDER BY m.match_date DESC
            {limit_clause}
        """

        cursor.execute(query)
        columns = ['fotmob_id', 'home_team', 'away_team', 'league_name', 'match_date', 'season']

        for row in cursor.fetchall():
            matches.append(dict(zip(columns, row)))

        cursor.close()
        conn.close()

        logger.info(f"📊 数据库查询结果: 找到 {len(matches)} 场缺失的比赛")

    except Exception as e:
        logger.error(f"❌ 数据库查询失败: {e}")
        raise

    return matches


def insert_match_mapping(record: Dict[str, Any]) -> bool:
    """插入单条映射记录（带 TDD 验证）

    Args:
        record: 映射记录

    Returns:
        是否成功插入
    """
    import psycopg2

    settings = get_settings()

    # V39.0: 准入红线检查
    confidence = record.get('confidence', 0.0)
    if not is_safe_confidence(confidence):
        logger.warning(f"⚠️ 置信度 {confidence:.1f}% 低于准入红线 85%，跳过: {record['fotmob_id']}")
        return False

    try:
        conn = psycopg2.connect(
            host=settings.database.host,
            port=settings.database.port,
            database=settings.database.name,
            user=settings.database.user,
            password=settings.database.password.get_secret_value()
        )
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO matches_mapping (
                fotmob_id,
                home_team,
                away_team,
                league_name,
                match_date,
                oddsportal_url,
                confidence,
                mapping_method,
                review_status,
                status
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            ON CONFLICT (fotmob_id) DO NOTHING
        """, (
            record['fotmob_id'],
            record['home_team'],
            record['away_team'],
            record['league_name'],
            record.get('match_date'),
            record.get('oddsportal_url'),
            confidence,
            record.get('mapping_method', 'multi_source'),
            'auto' if confidence >= 90 else 'pending',
            'pending'
        ))

        conn.commit()
        cursor.close()
        conn.close()

        logger.info(f"💾 成功插入: {record['fotmob_id']} (置信度: {confidence:.1f}%)")
        return True

    except Exception as e:
        logger.error(f"❌ 插入失败 {record['fotmob_id']}: {e}")
        return False


# ============================================================================
# Multi-Source Search
# ============================================================================

async def multi_source_search(
    home_team: str,
    away_team: str,
    league_hint: str,
    scraper
) -> Dict[str, Any]:
    """
    V39.0: 多源搜索策略

    Level 1: 标准 OddsPortal 站内搜索
    Level 2: 队名变体搜索
    Level 3: 历史别名库回退（暂未实现，返回失败）

    Args:
        home_team: 主队名称
        away_team: 客队名称
        league_hint: 联赛提示
        scraper: OddsPortalScraper 实例

    Returns:
        搜索结果字典
    """
    results = []

    # Level 1: 标准搜索
    logger.info(f"[Level 1] 标准搜索: {home_team} vs {away_team} ({league_hint})")
    result = await scraper.search_match_url(
        home_team=home_team,
        away_team=away_team,
        league_hint=league_hint,
        headless=True
    )

    if result.get('success') and result.get('url'):
        # V39.1: TDD 双重校验 - URL + HTML 验证
        validation = await validate_match_from_url(
            result['url'],
            home_team,
            away_team,
            scraper,
            enable_html_verification=True
        )

        if validation['is_valid']:
            logger.info(f"✅ Level 1 成功: {result['url']} (置信度: {validation['confidence']:.1f}%)")
            return {
                'success': True,
                'url': result['url'],
                'match_id': result.get('match_id'),
                'confidence': validation['confidence'],
                'method': 'level_1_standard',
                'validation': validation
            }
        else:
            logger.warning(f"⚠️ Level 1 TDD 验证失败: {validation['reason']}")

    # Level 2: 队名变体搜索
    logger.info(f"[Level 2] 队名变体搜索")
    home_variants = expand_team_name(normalize_team_name(home_team))
    away_variants = expand_team_name(normalize_team_name(away_team))

    for home_variant in home_variants[:3]:  # 限制尝试 3 个变体
        for away_variant in away_variants[:3]:
            if home_variant != normalize_team_name(home_team) or \
               away_variant != normalize_team_name(away_team):
                logger.info(f"   尝试: {home_variant} vs {away_variant}")
                result = await scraper.search_match_url(
                    home_team=home_variant,
                    away_team=away_variant,
                    league_hint=league_hint,
                    headless=True
                )

                if result.get('success') and result.get('url'):
                    # V39.1: TDD 双重校验 - URL + HTML 验证
                    validation = await validate_match_from_url(
                        result['url'],
                        home_team,
                        away_team,
                        scraper,
                        enable_html_verification=True
                    )

                    if validation['is_valid']:
                        logger.info(f"✅ Level 2 成功: {result['url']} (置信度: {validation['confidence']:.1f}%)")
                        return {
                            'success': True,
                            'url': result['url'],
                            'match_id': result.get('match_id'),
                            'confidence': validation['confidence'] * 0.9,  # 变体搜索降权 10%
                            'method': 'level_2_variant',
                            'validation': validation
                        }

    # Level 3: 失败
    logger.warning(f"❌ 所有搜索策略失败")
    return {
        'success': False,
        'url': None,
        'match_id': None,
        'confidence': 0.0,
        'method': 'failed',
        'error': '所有搜索策略失败'
    }


async def extract_real_team_names_from_html(
    url: str,
    scraper
) -> Optional[Dict[str, str]]:
    """
    V39.1: 从 OddsPortal HTML 页面提取真实队名（双重校验）

    通过实际访问页面并解析 HTML，获取页面上显示的真实队名
    这样可以防止 URL 与页面内容不匹配的情况

    Args:
        url: OddsPortal URL
        scraper: OddsPortalScraper 实例

    Returns:
        {'home': 'Real Home Name', 'away': 'Real Away Name'} 或 None
    """
    try:
        from playwright.async_api import async_playwright

        # 使用 scraper 的代理配置
        proxy = scraper.circuit_breaker.get_available_proxy()
        if proxy is None:
            logger.warning("无可用代理，跳过 HTML 验证")
            return None

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                proxy=proxy if proxy and proxy.get('server') else None
            )
            context = await browser.new_context(
                user_agent=scraper.get_random_user_agent(),
                viewport=scraper.get_random_viewport()
            )
            page = await context.new_page()

            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                await page.wait_for_timeout(2000)  # 等待页面加载

                # 尝试多种选择器提取队名
                selectors = [
                    # OddsPortal 比赛页面标题
                    "h1",
                    "div.breadcrumb .last",
                    "div[data-team-name] [data-team-name]",
                    # 备用选择器
                    "title",
                    "meta[property='og:title']",
                ]

                real_home = None
                real_away = None

                for selector in selectors:
                    try:
                        element = await page.query_selector(selector)
                        if element:
                            text = await element.inner_text()
                            if text and text.strip():
                                # 尝试解析队名
                                # 常见格式: "Team A vs Team B", "Team A - Team B", "Team A v Team B"
                                import re
                                # 尝试多种分隔符
                                patterns = [
                                    r'(.+?)\s+vs\s+(.+)',  # "Team A vs Team B"
                                    r'(.+?)\s+-\s+(.+)',   # "Team A - Team B"
                                    r'(.+?)\s+v\s+(.+)',   # "Team A v Team B"
                                ]
                                for pattern in patterns:
                                    match = re.search(pattern, text, re.IGNORECASE)
                                    if match:
                                        real_home = match.group(1).strip()
                                        real_away = match.group(2).strip()
                                        logger.info(f"[HTML] 提取到真实队名: {real_home} vs {real_away}")
                                        break
                                if real_home and real_away:
                                    break
                    except Exception:
                        continue

                await context.close()
                await browser.close()

                if real_home and real_away:
                    return {'home': real_home, 'away': real_away}
                else:
                    logger.warning(f"[HTML] 无法从页面提取队名: {url}")
                    return None

            except Exception as e:
                await context.close()
                await browser.close()
                raise

    except Exception as e:
        logger.error(f"[HTML] 提取真实队名失败: {e}")
        return None


async def validate_match_from_url(
    url: str,
    expected_home: str,
    expected_away: str,
    scraper,
    enable_html_verification: bool = True
) -> Dict[str, Any]:
    """
    V39.1: 双重校验 TDD 验证 - 防止 "Real Madrid → Almeria" 错误

    第一层：从 URL 提取队名并与期望值匹配
    第二层（NEW）：从 HTML 页面提取真实队名并验证（匹配度 > 95%）

    Args:
        url: OddsPortal URL
        expected_home: 期望的主队名（FotMob 队名）
        expected_away: 期望的客队名（FotMob 队名）
        scraper: OddsPortalScraper 实例
        enable_html_verification: 是否启用 HTML 双重校验（默认启用）

    Returns:
        验证结果字典
    """
    try:
        from src.utils.team_alias import extract_team_names_from_url

        # ========== 第一层：URL 提取验证 ==========
        extracted = extract_team_names_from_url(url)
        if not extracted:
            return {
                'is_valid': False,
                'confidence': 0.0,
                'reason': '无法从 URL 提取队名'
            }

        url_home, url_away = extracted

        # 计算置信度
        confidence, details = match_teams(url_home, url_away, expected_home, expected_away)

        # 检查主客颠倒（危险信号）
        home_reverse_sim = calculate_similarity(expected_home, url_away)
        away_reverse_sim = calculate_similarity(expected_away, url_home)
        reverse_score = (home_reverse_sim + away_reverse_sim) / 2

        if reverse_score > 85:
            return {
                'is_valid': False,
                'confidence': reverse_score,
                'reason': f'主客颠倒危险: {expected_home}/{expected_away} → {url_home}/{url_away}',
                'details': details
            }

        # 准入红线检查（第一层）
        if not is_safe_confidence(confidence):
            return {
                'is_valid': False,
                'confidence': confidence,
                'reason': f'置信度 {confidence:.1f}% 低于准入红线 85%',
                'details': details
            }

        # ========== 第二层：HTML 真实队名验证（V39.1 新增）==========
        if enable_html_verification:
            logger.info(f"[HTML] 开始双重校验: {url}")
            real_names = await extract_real_team_names_from_html(url, scraper)

            if real_names:
                real_home = real_names['home']
                real_away = real_names['away']

                # 计算真实队名与期望队名的匹配度
                html_home_sim = calculate_similarity(real_home, expected_home)
                html_away_sim = calculate_similarity(real_away, expected_away)
                html_confidence = (html_home_sim + html_away_sim) / 2

                logger.info(f"[HTML] 真实队名: {real_home} (匹配度: {html_home_sim:.1f}%) vs {real_away} (匹配度: {html_away_sim:.1f}%)")

                # V39.1 准入红线：HTML 匹配度必须 > 95%
                if html_confidence < 95.0:
                    return {
                        'is_valid': False,
                        'confidence': html_confidence,
                        'reason': f'HTML 验证失败: 真实队名 {real_home} vs {real_away} 与期望 {expected_home} vs {expected_away} 匹配度 {html_confidence:.1f}% 低于 95%',
                        'details': f'URL 匹配 {confidence:.1f}% 但 HTML 不匹配',
                        'url_home': url_home,
                        'url_away': url_away,
                        'html_home': real_home,
                        'html_away': real_away
                    }

                logger.info(f"✅ [HTML] 双重校验通过: {html_confidence:.1f}%")
                return {
                    'is_valid': True,
                    'confidence': min(confidence, html_confidence),  # 取最小值
                    'url_home': url_home,
                    'url_away': url_away,
                    'html_home': real_home,
                    'html_away': real_away,
                    'details': details
                }
            else:
                logger.warning(f"[HTML] 无法提取真实队名，跳过双重校验（仅使用 URL 验证）")
                # 如果无法提取 HTML 队名，仍然使用 URL 验证结果

        return {
            'is_valid': True,
            'confidence': confidence,
            'url_home': url_home,
            'url_away': url_away,
            'details': details
        }

    except Exception as e:
        return {
            'is_valid': False,
            'confidence': 0.0,
            'reason': f'验证异常: {str(e)}'
        }


# ============================================================================
# Main Hunting Loop
# ============================================================================

async def hunt_missing_matches(
    scraper,
    limit: Optional[int] = None,
    batch_size: int = 20
) -> Dict[str, Any]:
    """
    V39.0: 狩猎缺失比赛（多源搜索）

    Args:
        scraper: OddsPortalScraper 实例
        limit: 最大处理数量
        batch_size: 批量大小

    Returns:
        统计结果
    """
    matches = get_missing_matches(limit=limit)

    if not matches:
        logger.info("✅ 没有缺失的比赛，映射完整！")
        return {'total': 0, 'success': 0, 'failed': 0, 'skipped': 0}

    stats = {
        'total': len(matches),
        'success': 0,
        'failed': 0,
        'skipped': 0  # 低于准入红线
    }

    logger.info("=" * 70)
    logger.info("🎯 V39.0 Multi-Source Hash Hunter")
    logger.info("=" * 70)
    logger.info(f"总场次: {stats['total']}")
    logger.info(f"批量大小: {batch_size}")
    logger.info(f"准入红线: 置信度 >= {CONFIDENCE_THRESHOLD['SAFE_MIN']}%")
    logger.info("=" * 70)

    for i, match in enumerate(matches, 1):
        fotmob_id = match['fotmob_id']
        home_team = match['home_team']
        away_team = match['away_team']
        league_name = match['league_name']

        logger.info(f"\n[{i}/{stats['total']}] 狩猎: {home_team} vs {away_team} ({league_name})")
        logger.info(f"   Match ID: {fotmob_id}")

        try:
            # 多源搜索
            result = await multi_source_search(
                home_team=home_team,
                away_team=away_team,
                league_hint=league_name,
                scraper=scraper
            )

            if result['success']:
                # 插入数据库
                record = {
                    'fotmob_id': fotmob_id,
                    'home_team': home_team,
                    'away_team': away_team,
                    'league_name': league_name,
                    'match_date': match.get('match_date'),
                    'oddsportal_url': result['url'],
                    'confidence': result['confidence'],
                    'mapping_method': result['method']
                }

                if insert_match_mapping(record):
                    stats['success'] += 1
                else:
                    stats['skipped'] += 1
            else:
                stats['failed'] += 1
                logger.warning(f"⚠️ 搜索失败: {result.get('error', '未知错误')}")

            # 延迟（除了最后一场）
            if i < stats['total']:
                delay = 2.0  # 固定 2 秒延迟
                logger.info(f"⏳ 等待 {delay:.1f}s 后继续...")
                await asyncio.sleep(delay)

        except Exception as e:
            stats['failed'] += 1
            logger.error(f"❌ 异常: {e}")
            continue

    # 汇报战果
    logger.info("\n" + "=" * 70)
    logger.info("📊 V39.0 Multi-Source Hash Hunter 战果报告")
    logger.info("=" * 70)
    logger.info(f"总场次: {stats['total']}")
    logger.info(f"成功: {stats['success']}")
    logger.info(f"失败: {stats['failed']}")
    logger.info(f"跳过 (低于准入红线): {stats['skipped']}")
    logger.info(f"成功率: {100.0 * stats['success'] / stats['total']:.1f}%")
    logger.info("=" * 70)

    return stats


# ============================================================================
# CLI Entry Point
# ============================================================================

async def main():
    """主函数"""
    import argparse
    import random

    from core.scrapers.oddsportal import OddsPortalScraper

    parser = argparse.ArgumentParser(description='V39.0 Multi-Source Hash Hunter')
    parser.add_argument('--limit', type=int, default=None, help='最大处理数量')
    parser.add_argument('--batch-size', type=int, default=20, help='批量大小')
    parser.add_argument('--leagues', nargs='+', default=None, help='指定联赛（默认所有）')
    args = parser.parse_args()

    # 初始化 Scraper
    scraper = OddsPortalScraper()

    # 开始狩猎
    stats = await hunt_missing_matches(
        scraper=scraper,
        limit=args.limit,
        batch_size=args.batch_size
    )

    # 返回状态码
    sys.exit(0 if stats['success'] > 0 else 1)


if __name__ == "__main__":
    asyncio.run(main())
