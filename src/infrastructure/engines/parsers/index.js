/**
 * Parsers Module - Unified Export Entry Point
 * =============================================
 *
 * [Genesis.Architect] V168.002 模块化重构 - 统一导出入口
 *
 * 提供 parsers 目录下所有模块的统一导出接口。
 *
 * @module parsers
 * @version V168.002
 * @since 2026-02-02
 * @author [Genesis.Architect]
 */

'use strict';

// Calculators - 赔率数学计算
const { PayoutCalculator } = require('./calculators/PayoutCalculator');

// Temporal - 时间处理
const { SyncTimestamp, alignTimestamp } = require('./temporal/SyncTimestamp');

// Main Parser - 主控制器
const { TrajectoryParser } = require('./TrajectoryParser');

/**
 * V168.002: 统一导出所有解析器模块
 */
module.exports = {
    // Calculators
    PayoutCalculator,

    // Temporal
    SyncTimestamp,
    alignTimestamp,

    // Main Parser
    TrajectoryParser,

    // Legacy exports (向后兼容)
    PayoutCalculator,  // 直接导出以支持直接引用
    SyncTimestamp: SyncTimestamp,
    alignTimestamp: alignTimestamp
};
