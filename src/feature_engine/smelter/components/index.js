/**
 * Smelter Components - V4.0 模块化特征提取组件
 * ===============================================
 *
 * 所有特征提取器的统一出口
 * @module feature_engine/smelter/components
 * @version V4.0.0-MODULAR
 * @since 2026-03-14
 */

'use strict';

const { BaseExtractor, ExtractorError, ValidationError, ExtractionError } = require('./BaseExtractor');
const { GoldenExtractor, DEFAULT_CONFIG: GOLDEN_CONFIG, FEATURE_NAMES: GOLDEN_FEATURES } = require('./GoldenExtractor');
const { TacticalExtractor, DEFAULT_CONFIG: TACTICAL_CONFIG, FEATURE_NAMES: TACTICAL_FEATURES } = require('./TacticalExtractor');
const { DataFetcher, DEFAULT_CONFIG: DATAFETCHER_CONFIG } = require('./DataFetcher');
const { L3Writer, DEFAULT_CONFIG: L3WRITER_CONFIG } = require('./L3Writer');

module.exports = {
    // 基类
    BaseExtractor,
    ExtractorError,
    ValidationError,
    ExtractionError,

    // 具体提取器
    GoldenExtractor,
    TacticalExtractor,

    // 数据组件
    DataFetcher,
    L3Writer,

    // 配置
    DEFAULT_CONFIGS: {
        golden: GOLDEN_CONFIG,
        tactical: TACTICAL_CONFIG,
        dataFetcher: DATAFETCHER_CONFIG,
        l3Writer: L3WRITER_CONFIG
    },

    // 特征清单
    FEATURE_NAMES: {
        golden: GOLDEN_FEATURES,
        tactical: TACTICAL_FEATURES
    },

    // 版本
    VERSION: 'V4.0.0-MODULAR'
};
