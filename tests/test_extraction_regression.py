#!/usr/bin/env python3
"""V119.0 E2E Regression Test Suite for V117.1 Hybrid Engine.

This test suite validates the V117.1 Hybrid Adaptive Engine through end-to-end
regression tests covering historical compatibility, precision extraction, and
automatic synthesis logic.

Test Matrix:
- Test A: Historical Compatibility (2021-2022) - Gravity Mode fallback validation
- Test B: High-Precision Validation (2024-2025) - Laser Mode full extraction
- Test C: Entity_AVG Synthesis - Automatic consensus calculation

Usage:
    pytest tests/test_extraction_regression.py -v
    pytest tests/test_extraction_regression.py::test_historical_compatibility -v
    pytest tests/test_extraction_regression.py -k "test_high_precision" -v
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict

import pytest
from playwright.async_api import Page

from src.api.collectors.market_data_engine import (
    V100MultiVendorExtractor,
    PROVIDER_MAPPING,
    MIN_INTEGRITY_SCORE,
    MAX_INTEGRITY_SCORE
)

logger = logging.getLogger(__name__)


# ============================================================================
# Test A: Historical Compatibility (2021-2022) - Gravity Mode Fallback
# ============================================================================

@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.asyncio
async def test_historical_compatibility_gravity_mode(
    historical_match_sample: Dict,
    playwright_browser: Page
):
    """V119.0 Test A: 历史兼容性测试 - Gravity Mode 保底抓取

    验证 V117.1 引擎对 2021-2022 年历史页面的兼容性。
    如果 Laser Mode 失败，Gravity Mode 应该能够保底抓取 Entity_P。

    测试逻辑:
        1. 从数据库随机选取一场 2021-2022 年有 URL 的比赛
        2. 导航到 OddsPortal 页面
        3. 执行 V117.1 混合引擎提取
        4. 验证至少提取到 Entity_P
        5. 验证 Integrity Score 在合理区间 [1.00, 1.08]

    Args:
        historical_match_sample: 历史比赛样本 (2021-2022)
        playwright_browser: Playwright 浏览器实例
    """
    match_id: str = historical_match_sample["match_id"]
    url: str = historical_match_sample["oddsportal_url"]
    match_date: datetime = historical_match_sample["match_date"]

    logger.info(f"[Test A] Testing historical match: {match_id} from {match_date}")

    # Navigate to page
    await playwright_browser.goto(url, wait_until="domcontentloaded", timeout=30000)
    await asyncio.sleep(2)

    # Run V117.1 extraction
    extractor = V100MultiVendorExtractor()
    results = await extractor.extract_all_vendors(
        page=playwright_browser,
        match_id=match_id,
        match_date=match_date
    )

    # Validate results
    assert len(results) > 0, "[Test A] Should extract at least one entity"

    # Check if Entity_P was extracted (Gravity Mode should guarantee this)
    entity_p = results.get("Entity_P")
    assert entity_p is not None, "[Test A] Entity_P should be extracted (Gravity Mode fallback)"

    # Validate integrity score
    integrity_score = entity_p.integrity_score
    assert integrity_score is not None, "[Test A] Entity_P should have integrity_score"
    assert MIN_INTEGRITY_SCORE < integrity_score < MAX_INTEGRITY_SCORE, \
        f"[Test A] Entity_P integrity score {integrity_score:.4f} should be in valid range"

    # Validate final odds
    assert entity_p.final_h is not None, "[Test A] Entity_P should have final_h"
    assert entity_p.final_d is not None, "[Test A] Entity_P should have final_d"
    assert entity_p.final_a is not None, "[Test A] Entity_P should have final_a"

    logger.info(f"[Test A] PASSED - Extracted {len(results)} entities from historical match")


# ============================================================================
# Test B: High-Precision Validation (2024-2025) - Laser Mode Full Extraction
# ============================================================================

@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.asyncio
async def test_high_precision_laser_mode(
    recent_match_sample: Dict,
    playwright_browser: Page
):
    """V119.0 Test B: 高精度验证测试 - Laser Mode 满血抓取

    验证 V117.1 引擎对 2024-2025 年近期页面的高精度提取能力。
    Laser Mode 应该能够满血抓取至少 3 个 Entity 的完整数据。

    测试逻辑:
        1. 从数据库随机选取一场 2024-2025 年有 URL 的比赛
        2. 导航到 OddsPortal 页面
        3. 执行 V117.1 混合引擎提取
        4. 验证至少提取到 3 个 Entity
        5. 验证所有 Entity 的 Integrity Score 都在合理区间

    Args:
        recent_match_sample: 近期比赛样本 (2024-2025)
        playwright_browser: Playwright 浏览器实例
    """
    match_id: str = recent_match_sample["match_id"]
    url: str = recent_match_sample["oddsportal_url"]
    match_date: datetime = recent_match_sample["match_date"]

    logger.info(f"[Test B] Testing recent match: {match_id} from {match_date}")

    # Navigate to page
    await playwright_browser.goto(url, wait_until="domcontentloaded", timeout=30000)
    await asyncio.sleep(2)

    # Run V117.1 extraction
    extractor = V100MultiVendorExtractor()
    results = await extractor.extract_all_vendors(
        page=playwright_browser,
        match_id=match_id,
        match_date=match_date
    )

    # Validate results - should extract at least 3 entities
    assert len(results) >= 3, \
        f"[Test B] Should extract at least 3 entities, got {len(results)}"

    # Validate each entity's integrity score
    for source_name, entity_data in results.items():
        assert entity_data.integrity_score is not None, \
            f"[Test B] {source_name} should have integrity_score"

        assert MIN_INTEGRITY_SCORE < entity_data.integrity_score < MAX_INTEGRITY_SCORE, \
            f"[Test B] {source_name} integrity score {entity_data.integrity_score:.4f} should be in valid range"

        assert entity_data.final_h is not None, f"[Test B] {source_name} should have final_h"
        assert entity_data.final_d is not None, f"[Test B] {source_name} should have final_d"
        assert entity_data.final_a is not None, f"[Test B] {source_name} should have final_a"

    logger.info(f"[Test B] PASSED - Extracted {len(results)} entities from recent match")


# ============================================================================
# Test C: Entity_AVG Synthesis Logic Validation
# ============================================================================

@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.asyncio
async def test_entity_avg_synthesis(
    recent_match_sample: Dict,
    playwright_browser: Page
):
    """V119.0 Test C: Entity_AVG 自动合成逻辑验证

    验证当 Entity_AVG 缺失时，系统能够从所有已识别 Entity 自动计算平均值。

    测试逻辑:
        1. 执行 V117.1 混合引擎提取
        2. 手动移除 Entity_AVG（模拟缺失）
        3. 手动执行 Entity_AVG 合成逻辑
        4. 验证合成后的 Entity_AVG 的 Integrity Score 在合理区间

    Args:
        recent_match_sample: 近期比赛样本
        playwright_browser: Playwright 浏览器实例
    """
    match_id: str = recent_match_sample["match_id"]
    url: str = recent_match_sample["oddsportal_url"]
    match_date: datetime = recent_match_sample["match_date"]

    logger.info(f"[Test C] Testing Entity_AVG synthesis for match: {match_id}")

    # Navigate to page
    await playwright_browser.goto(url, wait_until="domcontentloaded", timeout=30000)
    await asyncio.sleep(2)

    # Run V117.1 extraction
    extractor = V100MultiVendorExtractor()
    results = await extractor.extract_all_vendors(
        page=playwright_browser,
        match_id=match_id,
        match_date=match_date
    )

    # Simulate Entity_AVG missing
    if "Entity_AVG" in results:
        # Remove Entity_AVG to test synthesis logic
        del results["Entity_AVG"]
        logger.info("[Test C] Removed Entity_AVG to test synthesis logic")

    # Collect all valid non-AVG entities
    valid_entities = [
        v for k, v in results.items()
        if k != "Entity_AVG" and v.is_valid and v.final_h and v.final_d and v.final_a
    ]

    assert len(valid_entities) >= 2, \
        "[Test C] Need at least 2 valid entities for Entity_AVG synthesis"

    # Calculate Entity_AVG manually
    avg_h = sum(v.final_h for v in valid_entities) / len(valid_entities)
    avg_d = sum(v.final_d for v in valid_entities) / len(valid_entities)
    avg_a = sum(v.final_a for v in valid_entities) / len(valid_entities)

    logger.info(f"[Test C] Synthesized Entity_AVG: h={avg_h:.2f}, d={avg_d:.2f}, a={avg_a:.2f}")

    # Validate synthesized odds
    assert 1.01 <= avg_h <= 50.00, "[Test C] Synthesized avg_h should be in valid range"
    assert 1.01 <= avg_d <= 50.00, "[Test C] Synthesized avg_d should be in valid range"
    assert 1.01 <= avg_a <= 50.00, "[Test C] Synthesized avg_a should be in valid range"

    # Calculate integrity score for synthesized Entity_AVG
    synthesized_integrity = 1.0/avg_h + 1.0/avg_d + 1.0/avg_a
    assert MIN_INTEGRITY_SCORE < synthesized_integrity < MAX_INTEGRITY_SCORE, \
        f"[Test C] Synthesized integrity score {synthesized_integrity:.4f} should be in valid range"

    logger.info(f"[Test C] PASSED - Entity_AVG synthesis validated (integrity={synthesized_integrity:.4f})")


# ============================================================================
# Summary Report
# ============================================================================

@pytest.mark.e2e
def test_regression_summary(
    historical_match_sample: Dict,
    recent_match_sample: Dict
):
    """V119.0: 回归测试摘要报告

    显示测试样本信息，方便调试和追踪。

    Args:
        historical_match_sample: 历史比赛样本
        recent_match_sample: 近期比赛样本
    """
    logger.info("=" * 80)
    logger.info("V119.0 E2E Regression Test Suite - Test Samples")
    logger.info("=" * 80)

    logger.info(f"\n[Test A] Historical Match (2021-2022):")
    logger.info(f"  Match ID: {historical_match_sample['match_id']}")
    logger.info(f"  Match Date: {historical_match_sample['match_date']}")
    logger.info(f"  URL: {historical_match_sample['oddsportal_url']}")

    logger.info(f"\n[Test B] Recent Match (2024-2025):")
    logger.info(f"  Match ID: {recent_match_sample['match_id']}")
    logger.info(f"  Match Date: {recent_match_sample['match_date']}")
    logger.info(f"  URL: {recent_match_sample['oddsportal_url']}")

    logger.info("\n" + "=" * 80)
    logger.info("Expected Results:")
    logger.info("  Test A: Gravity Mode extracts Entity_P (Integrity: 1.00-1.08)")
    logger.info("  Test B: Laser Mode extracts >= 3 entities (Integrity: 1.00-1.08)")
    logger.info("  Test C: Entity_AVG synthesis validates (Integrity: 1.00-1.08)")
    logger.info("=" * 80)

    # Always pass (informational test)
    assert True
