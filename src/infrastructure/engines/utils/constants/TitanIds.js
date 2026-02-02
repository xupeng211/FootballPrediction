/**
 * Titan IDs - V168.002 Constants Module
 * ====================================
 *
 * [Genesis.Architect] Titan ID 签名 - 提取为独立常量模块
 *
 * 这些 ID 是 l3_odds_hash 计算的核心标识。
 *
 * @module utils/constants/TitanIds
 * @version V168.002
 * @since 2026-02-02
 * @author [Genesis.Architect]
 */

'use strict';

/**
 * Titan ID 签名 - 用于识别赔率提供商数据
 * 这些 ID 是 l3_odds_hash 计算的核心标识
 */
const TITAN_ID_SIGNATURES = ['18', '32', '2', '25679340'];

/**
 * Titan ID 到提供商名称的映射
 */
const TITAN_ID_TO_PROVIDER = {
    '18': 'Pinnacle',
    '32': 'William Hill',
    '2': 'bet365',
    '25679340': 'Unibet'
};

module.exports = { TITAN_ID_SIGNATURES, TITAN_ID_TO_PROVIDER };
