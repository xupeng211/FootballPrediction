#!/usr/bin/env python3
"""
V81.0 稳定性准入审计 - 全量收割前的极限压力测试

任务：
1. 深度数据探测：50 条 URL 随机抽样
2. 并发稳定性测试：8 路并行收割 100 场
3. 异常处理审计：无效 URL 容错测试
"""

import asyncio
import logging
import random
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

import psycopg2
from playwright.async_api import async_playwright

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config_unified import get_settings

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('logs/v81_0_stability_audit.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# ============================================================================
# 数据库操作
# ============================================================================

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


def get_sample_urls(sample_size=50):
    """
    获取随机抽样的 URL（覆盖 5 个联赛、5 个赛季）

    Returns:
        List of (match_id, home_team, away_team, league, season, url)
    """
    conn = get_db_connection()
    cur = conn.cursor()

    # 获取按联赛和赛季分组的 URL
    cur.execute("""
        SELECT
            m.match_id,
            m.home_team,
            m.away_team,
            m.league_name,
            m.season,
            m.oddsportal_url
        FROM matches m
        WHERE m.oddsportal_url IS NOT NULL
        ORDER BY RANDOM()
        LIMIT %s
    """, (sample_size * 5,))  # 获取更多样本以确保覆盖

    all_matches = cur.fetchall()

    # 按联赛和赛季分层抽样
    samples_by_league_season = {}

    for match in all_matches:
        league = match[3]
        season = match[4]
        key = f"{league}|{season}"

        if key not in samples_by_league_season:
            samples_by_league_season[key] = []

        if len(samples_by_league_season[key]) < 2:  # 每个联赛赛季至少 2 条
            samples_by_league_season[key].append(match)

    # 随机选择达到目标数量
    flat_samples = []
    for samples in samples_by_league_season.values():
        flat_samples.extend(samples)

    random.shuffle(flat_samples)
    final_samples = flat_samples[:sample_size]

    cur.close()
    conn.close()

    logger.info(f"抽样完成：获取 {len(final_samples)} 条 URL")
    logger.info(f"覆盖联赛数：{len(set(m[3] for m in final_samples))}")
    logger.info(f"覆盖赛季数：{len(set(m[4] for m in final_samples))}")

    return final_samples


# ============================================================================
# Pinnacle 初赔探测逻辑
# ============================================================================

async def detect_pinnacle_opening_odds(url: str, timeout: int = 30000) -> Dict:
    """
    探测页面是否包含 Pinnacle 初赔数据

    Args:
        url: OddsPortal 比赛 URL
        timeout: 超时时间（毫秒）

    Returns:
        {
            'accessible': bool,  # 页面是否可访问
            'has_pinnacle': bool,  # 是否有 Pinnacle 数据
            'has_opening': bool,  # 是否有初赔数据
            'bookmakers': List[str],  # 所有发现的博彩公司
            'error': str or None  # 错误信息
        }
    """
    result = {
        'accessible': False,
        'has_pinnacle': False,
        'has_opening': False,
        'bookmakers': [],
        'error': None
    }

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )

        page = await context.new_page()

        try:
            # 访问页面
            await page.goto(url, wait_until='domcontentloaded', timeout=timeout)

            # 等待页面加载
            await asyncio.sleep(3)

            result['accessible'] = True

            # 探测博彩公司表格
            # OddsPortal 的博彩公司数据通常在特定表格中
            page_content = await page.content()

            # 检查 Pinnacle
            if 'pinnacle' in page_content.lower():
                result['has_pinnacle'] = True

                # 检查初赔数据（opening odds）
                # 通常在 "Opening" 或 "初盘" 相关的行中
                if 'opening' in page_content.lower() or '初' in page_content:
                    result['has_opening'] = True

            # 尝试提取所有博彩公司名称
            try:
                # 使用选择器查找博彩公司
                bookmakers = await page.query_selector_all('[data*="bookmaker"], .bookmaker, [class*="pinnacle"]')
                for bm in bookmakers[:10]:  # 限制数量
                    text = await bm.text_content()
                    if text:
                        result['bookmakers'].append(text.strip())
            except Exception as e:
                logger.debug(f"提取博彩公司列表失败: {e}")

            # 如果找到 Pinnacle，更精确地检查
            if result['has_pinnacle']:
                try:
                    # 查找 Pinnacle 特定元素
                    pinnacle_elem = await page.query_selector('[class*="pinnacle"], [id*="pinnacle"]')
                    if pinnacle_elem:
                        pinnacle_text = await pinnacle_elem.text_content()
                        # 检查是否包含赔率数据（通常包含数字和小数点）
                        if any(c.isdigit() for c in pinnacle_text) and '.' in pinnacle_text:
                            result['has_opening'] = True
                except:
                    pass

        except Exception as e:
            result['error'] = str(e)
            logger.warning(f"访问 {url} 失败: {e}")

        finally:
            await browser.close()

    return result


# ============================================================================
# 第一阶段：深度数据探测
# ============================================================================

async def phase1_sampling_audit(sample_size=50):
    """第一阶段：深度数据探测"""
    logger.info("")
    logger.info("=" * 70)
    logger.info("V81.0 第一阶段：深度数据探测 (Sampling Audit)")
    logger.info("=" * 70)
    logger.info(f"抽样数量: {sample_size}")
    logger.info("")

    # 获取样本
    samples = get_sample_urls(sample_size)

    # 统计变量
    total = len(samples)
    accessible_count = 0
    has_pinnacle_count = 0
    has_opening_count = 0
    errors = []

    # 逐个测试
    for i, (match_id, home, away, league, season, url) in enumerate(samples, 1):
        logger.info(f"[{i}/{total}] {league} {season}: {home} vs {away}")

        # 探测 Pinnacle 数据
        result = await detect_pinnacle_opening_odds(url)

        if result['accessible']:
            accessible_count += 1
            logger.info(f"  ✅ 页面可访问")

            if result['has_pinnacle']:
                has_pinnacle_count += 1
                logger.info(f"  ✅ 发现 Pinnacle 数据")

                if result['has_opening']:
                    has_opening_count += 1
                    logger.info(f"  ✅ 发现初赔数据")
                else:
                    logger.info(f"  ⚠️  未发现初赔数据")
            else:
                logger.info(f"  ⚠️  未发现 Pinnacle 数据")
        else:
            logger.warning(f"  ❌ 页面不可访问: {result['error']}")
            errors.append((match_id, url, result['error']))

        if result['bookmakers']:
            logger.info(f"  📊 博彩公司: {', '.join(result['bookmakers'][:5])}")

        logger.info("")

        # 避免请求过快
        await asyncio.sleep(2)

    # 第一阶段报告
    logger.info("")
    logger.info("=" * 70)
    logger.info("第一阶段：深度数据探测 - 报告")
    logger.info("=" * 70)
    logger.info(f"总样本数: {total}")
    logger.info(f"页面可访问: {accessible_count}/{total} ({100*accessible_count/total:.1f}%)")
    logger.info(f"发现 Pinnacle: {has_pinnacle_count}/{total} ({100*has_pinnacle_count/total:.1f}%)")
    logger.info(f"发现初赔数据: {has_opening_count}/{total} ({100*has_opening_count/total:.1f}%)")

    if errors:
        logger.warning(f"访问错误: {len(errors)} 条")
        for match_id, url, error in errors[:5]:
            logger.warning(f"  Match {match_id}: {error}")

    return {
        'total': total,
        'accessible': accessible_count,
        'has_pinnacle': has_pinnacle_count,
        'has_opening': has_opening_count,
        'accessible_rate': 100 * accessible_count / total,
        'pinnacle_rate': 100 * has_pinnacle_count / total,
        'opening_rate': 100 * has_opening_count / total,
        'errors': errors
    }


# ============================================================================
# 第二阶段：并发稳定性测试
# ============================================================================

async def phase2_concurrency_stress_test(concurrency=8, target_count=100):
    """第二阶段：并发稳定性测试"""
    logger.info("")
    logger.info("=" * 70)
    logger.info("V81.0 第二阶段：并发稳定性测试 (Concurrency Stress Test)")
    logger.info("=" * 70)
    logger.info(f"并发数: {concurrency}")
    logger.info(f"目标数量: {target_count}")
    logger.info("")

    # 获取测试样本
    samples = get_sample_urls(target_count)
    actual_count = len(samples)

    # 分批处理
    batch_size = concurrency
    batches = [samples[i:i + batch_size] for i in range(0, len(samples), batch_size)]

    # 统计变量
    total_processed = 0
    total_success = 0
    total_timeout = 0
    total_forbidden = 0
    total_errors = 0
    start_time = time.time()

    for batch_idx, batch in enumerate(batches, 1):
        logger.info(f"批次 {batch_idx}/{len(batches)} ({len(batch)} 条)...")

        # 并发执行
        tasks = []
        for match_id, home, away, league, season, url in batch:
            task = detect_pinnacle_opening_odds(url)
            tasks.append((match_id, url, task))

        # 等待批次完成
        results = await asyncio.gather(*[task for _, _, task in tasks], return_exceptions=True)

        # 处理结果
        for (match_id, url, _), result in zip(tasks, results):
            total_processed += 1

            if isinstance(result, Exception):
                total_errors += 1
                logger.warning(f"  ❌ Match {match_id}: {result}")
            elif result['error']:
                if 'timeout' in result['error'].lower():
                    total_timeout += 1
                elif '403' in result['error'] or 'forbidden' in result['error'].lower():
                    total_forbidden += 1
                else:
                    total_errors += 1
            elif result['accessible']:
                total_success += 1

            # 避免过载
            await asyncio.sleep(0.5)

        logger.info(f"  批次完成: 成功 {sum(1 for r in results if not isinstance(r, Exception) and r.get('accessible'))}/{len(batch)}")

    # 计算耗时
    total_time = time.time() - start_time
    avg_time_per_match = total_time / actual_count

    # 第二阶段报告
    logger.info("")
    logger.info("=" * 70)
    logger.info("第二阶段：并发稳定性测试 - 报告")
    logger.info("=" * 70)
    logger.info(f"总处理数: {total_processed}")
    logger.info(f"成功访问: {total_success} ({100*total_success/total_processed:.1f}%)")
    logger.info(f"超时次数: {total_timeout} ({100*total_timeout/total_processed:.1f}%)")
    logger.info(f"403 拦截: {total_forbidden} ({100*total_forbidden/total_processed:.1f}%)")
    logger.info(f"其他错误: {total_errors} ({100*total_errors/total_processed:.1f}%)")
    logger.info(f"总耗时: {total_time:.1f} 秒")
    logger.info(f"平均耗时: {avg_time_per_match:.2f} 秒/场")
    logger.info(f"预估 3000 场耗时: {avg_time_per_match * 3000 / 3600:.1f} 小时")

    return {
        'total': total_processed,
        'success': total_success,
        'timeout': total_timeout,
        'forbidden': total_forbidden,
        'errors': total_errors,
        'total_time': total_time,
        'avg_time': avg_time_per_match,
        'success_rate': 100 * total_success / total_processed,
        'timeout_rate': 100 * total_timeout / total_processed,
        'forbidden_rate': 100 * total_forbidden / total_processed
    }


# ============================================================================
# 第三阶段：异常处理审计
# ============================================================================

async def phase3_error_handling_audit():
    """第三阶段：异常处理审计"""
    logger.info("")
    logger.info("=" * 70)
    logger.info("V81.0 第三阶段：异常处理审计 (Error Handling Audit)")
    logger.info("=" * 70)
    logger.info("")

    # 测试无效 URL
    invalid_urls = [
        "https://www.oddsportal.com/football/england/premier-league-2023-2024/invalid-team1-invalid-team2-abcdefg/",
        "https://www.oddsportal.com/football/england/premier-league-2023-2024/",
        "https://www.oddsportal.com/football/invalid-league-2023-2024/team1-team2-hash/",
    ]

    graceful_handling = 0
    total = len(invalid_urls)

    for i, url in enumerate(invalid_urls, 1):
        logger.info(f"[{i}/{total}] 测试无效 URL: {url[:60]}...")

        result = await detect_pinnacle_opening_odds(url)

        if not result['accessible'] and result['error']:
            graceful_handling += 1
            logger.info(f"  ✅ 优雅处理: {result['error']}")
        else:
            logger.warning(f"  ⚠️  意外结果: accessible={result['accessible']}")

        logger.info("")

    # 第三阶段报告
    logger.info("")
    logger.info("=" * 70)
    logger.info("第三阶段：异常处理审计 - 报告")
    logger.info("=" * 70)
    logger.info(f"总测试数: {total}")
    logger.info(f"优雅处理: {graceful_handling}/{total} ({100*graceful_handling/total:.1f}%)")

    if graceful_handling == total:
        logger.info("✅ 异常处理机制正常")
    else:
        logger.warning("⚠️  异常处理机制可能存在问题")

    return {
        'total': total,
        'graceful': graceful_handling,
        'rate': 100 * graceful_handling / total
    }


# ============================================================================
# 主函数
# ============================================================================

async def main():
    """主函数"""
    logger.info("")
    logger.info("=" * 70)
    logger.info("V81.0 稳定性准入审计启动")
    logger.info("全量收割前的极限压力测试")
    logger.info("=" * 70)
    logger.info(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    results = {}

    # 第一阶段：深度数据探测
    results['phase1'] = await phase1_sampling_audit(sample_size=50)

    # 短暂休息
    await asyncio.sleep(5)

    # 第二阶段：并发稳定性测试
    results['phase2'] = await phase2_concurrency_stress_test(concurrency=8, target_count=100)

    # 短暂休息
    await asyncio.sleep(5)

    # 第三阶段：异常处理审计
    results['phase3'] = await phase3_error_handling_audit()

    # 最终报告
    logger.info("")
    logger.info("=" * 70)
    logger.info("V81.0 稳定性准入审计 - 最终报告")
    logger.info("=" * 70)
    logger.info("")

    # 判定标准
    phase1_pass = results['phase1']['accessible_rate'] >= 80
    phase2_pass = (
        results['phase2']['success_rate'] >= 70 and
        results['phase2']['timeout_rate'] < 20 and
        results['phase2']['forbidden_rate'] < 10
    )
    phase3_pass = results['phase3']['rate'] == 100

    all_pass = phase1_pass and phase2_pass and phase3_pass

    logger.info("第一阶段（深度数据探测）:")
    logger.info(f"  页面可访问率: {results['phase1']['accessible_rate']:.1f}%")
    logger.info(f"  Pinnacle 发现率: {results['phase1']['pinnacle_rate']:.1f}%")
    logger.info(f"  初赔数据率: {results['phase1']['opening_rate']:.1f}%")
    logger.info(f"  状态: {'✅ 通过' if phase1_pass else '❌ 未通过'}")
    logger.info("")

    logger.info("第二阶段（并发稳定性测试）:")
    logger.info(f"  成功率: {results['phase2']['success_rate']:.1f}%")
    logger.info(f"  超时率: {results['phase2']['timeout_rate']:.1f}%")
    logger.info(f"  403 拦截率: {results['phase2']['forbidden_rate']:.1f}%")
    logger.info(f"  平均耗时: {results['phase2']['avg_time']:.2f} 秒/场")
    logger.info(f"  状态: {'✅ 通过' if phase2_pass else '❌ 未通过'}")
    logger.info("")

    logger.info("第三阶段（异常处理审计）:")
    logger.info(f"  优雅处理率: {results['phase3']['rate']:.1f}%")
    logger.info(f"  状态: {'✅ 通过' if phase3_pass else '❌ 未通过'}")
    logger.info("")

    logger.info("=" * 70)
    if all_pass:
        logger.info("🎉 V81.0 稳定性准入审计 - 全部通过")
        logger.info("✅ 建议开启 3,000 场全量收割")
    else:
        logger.warning("⚠️  V81.0 稳定性准入审计 - 部分未通过")
        logger.warning("❌ 建议优化后再进行全量收割")

    logger.info(f"结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 70)

    # 保存结果到文件
    report_path = Path('docs/V81.0_STABILITY_AUDIT_REPORT.md')
    report_path.parent.mkdir(exist_ok=True)

    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(f"# V81.0 稳定性准入审计报告\n\n")
        f.write(f"**审计时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"## 执行摘要\n\n")
        f.write(f"| 阶段 | 指标 | 结果 | 状态 |\n")
        f.write(f"|------|------|------|------|\n")
        f.write(f"| 第一阶段 | 页面可访问率 | {results['phase1']['accessible_rate']:.1f}% | {'✅' if phase1_pass else '❌'} |\n")
        f.write(f"| 第一阶段 | Pinnacle 发现率 | {results['phase1']['pinnacle_rate']:.1f}% | {'✅' if phase1_pass else '❌'} |\n")
        f.write(f"| 第一阶段 | 初赔数据率 | {results['phase1']['opening_rate']:.1f}% | {'✅' if phase1_pass else '❌'} |\n")
        f.write(f"| 第二阶段 | 成功率 | {results['phase2']['success_rate']:.1f}% | {'✅' if phase2_pass else '❌'} |\n")
        f.write(f"| 第二阶段 | 超时率 | {results['phase2']['timeout_rate']:.1f}% | {'✅' if phase2_pass else '❌'} |\n")
        f.write(f"| 第二阶段 | 403 拦截率 | {results['phase2']['forbidden_rate']:.1f}% | {'✅' if phase2_pass else '❌'} |\n")
        f.write(f"| 第二阶段 | 平均耗时 | {results['phase2']['avg_time']:.2f} 秒/场 | {'✅' if phase2_pass else '❌'} |\n")
        f.write(f"| 第三阶段 | 优雅处理率 | {results['phase3']['rate']:.1f}% | {'✅' if phase3_pass else '❌'} |\n")
        f.write(f"\n## 最终结论\n\n")
        f.write(f"**审计状态**: {'✅ 全部通过' if all_pass else '⚠️ 部分未通过'}\n\n")
        f.write(f"**建议**: {'可以开启 3,000 场全量收割' if all_pass else '建议优化后再进行全量收割'}\n\n")
        f.write(f"**预估 3000 场耗时**: {results['phase2']['avg_time'] * 3000 / 3600:.1f} 小时\n")

    logger.info("")
    logger.info(f"✅ 审计报告已保存: {report_path}")


if __name__ == "__main__":
    asyncio.run(main())
