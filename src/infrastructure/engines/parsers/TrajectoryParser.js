/**
 * TrajectoryParser - V168.002 Modular Edition
 * ==============================================
 *
 * [Genesis.Architect] V168.002 模块化重构 - 主控制器
 *
 * 核心变更:
 * - PAYOUT CALCULATOR: 已移至 calculators/PayoutCalculator.js
 * - SYNC TIMESTAMP: 已移至 temporal/SyncTimestamp.js
 * - 本文件只保留 DOM 提取和数据编排逻辑
 *
 * @module parsers/TrajectoryParser
 * @version V168.002
 * @since 2026-02-02
 * @author [Genesis.Architect]
 */

'use strict';

const { JSDOM } = require('jsdom');
const { EngineConfig, TITAN_ID_MAPPING } = require('../config/EngineConfig');
const { PayoutCalculator } = require('./calculators/PayoutCalculator');
const { SyncTimestamp, alignTimestamp } = require('./temporal/SyncTimestamp');

// ============================================================================
// V168.002: MODULAR ARCHITECTURE - Imports from separated modules
// ============================================================================
// PayoutCalculator imported from: ./calculators/PayoutCalculator.js
// SyncTimestamp imported from: ./temporal/SyncTimestamp.js
// ============================================================================

// ============================================================================
// V167.000: CONSOLIDATED TRAJECTORY PARSER (Main Controller)
// ============================================================================

/**
 * TrajectoryParser - V167.000 Consolidated Edition
 *
 * 职责:
 * - DOM 提取 (Opening/Closing/Points)
 * - Payout 计算 (统一逻辑)
 * - 时间戳对齐
 * - 数据验证
 */
class TrajectoryParser {
    /**
     * @param {Object} options - 配置选项
     */
    constructor(options = {}) {
        this.config = new EngineConfig(options);
        this.sync = new SyncTimestamp(options);
    }

    // ========================================================================
    // V167.000: PAYOUT CALCULATION (Consolidated)
    // ========================================================================

    /**
     * V167.000: 计算市场返还率
     * @param {number} h - Home odds
     * @param {number} d - Draw odds
     * @param {number} a - Away odds
     * @returns {number|null} 返还率百分比
     */
    calculatePayout(h, d, a) {
        return PayoutCalculator.calculate(h, d, a);
    }

    /**
     * V167.000: 从赔率对象计算返还率
     * @param {Object} odds - 赔率对象
     * @returns {number|null} 返还率百分比
     */
    calculatePayoutFromObject(odds) {
        return PayoutCalculator.fromOddsObject(odds);
    }

    // ========================================================================
    // V167.000: DOM TRAJECTORY EXTRACTION
    // ========================================================================

    /**
     * V167.000: Extract full trajectory from modal HTML using DOM traversal
     *
     * 核心改进:
     * - Opening/Closing 识别强化
     * - Points 序列生成
     * - Payout 自动计算
     *
     * @param {string} modalHtml - Modal HTML content
     * @returns {Object} Result object with trajectory and metadata
     */
    extractFullTrajectoryDOM(modalHtml) {
        const trajectory = [];
        let dom = null;

        try {
            if (!modalHtml || typeof modalHtml !== 'string') {
                return {
                    trajectory: [],
                    valid: false,
                    warning: 'Invalid input: modalHtml is not a string',
                    recordCount: 0
                };
            }

            dom = new JSDOM(modalHtml);
            const document = dom.window.document;

            // [V164.FullTrajectory] Flexbox Columnar Extraction (OddsPortal 2026)
            const historyContainers = document.querySelectorAll('div.flex.flex-row.gap-3');

            for (const container of historyContainers) {
                const columns = Array.from(container.children).filter(c => c.tagName === 'DIV');

                if (columns.length >= 2) {
                    const timeCol = columns[0];
                    const oddsCol = columns[1];

                    const timeEntries = timeCol.querySelectorAll('div.text-\\[10px\\]');
                    const oddsEntries = oddsCol.querySelectorAll('div.text-\\[10px\\]');

                    const count = Math.min(timeEntries.length, oddsEntries.length);

                    for (let i = 0; i < count; i++) {
                        const timeText = timeEntries[i].textContent.trim();
                        const oddsText = oddsEntries[i].textContent.trim();

                        if (!timeText || !oddsText) continue;

                        const timestamp = this.sync.parse(timeText);
                        const value = parseFloat(oddsText);

                        if (timestamp && !isNaN(value) && value > 1.0) {
                            const exists = trajectory.some(p => p.time === timestamp && p.value === value);
                            if (!exists) {
                                trajectory.push({
                                    time: timestamp,
                                    value: value,
                                    type: 'Historical'
                                });
                            }
                        }
                    }
                }
            }

            // [V164.FullTrajectory] Opening Odds Extraction (Separate Section)
            const openingSection = document.querySelector('div.mt-2.gap-1, div.gap-1.mt-2');
            if (openingSection && openingSection.textContent.includes('Opening')) {
                const flexRow = openingSection.querySelector('div.flex.gap-1');
                if (flexRow) {
                    const divs = flexRow.querySelectorAll('div');
                    if (divs.length >= 2) {
                        const timeText = divs[0].textContent.trim();
                        const oddsText = divs[1].textContent.trim();

                        const timestamp = this.sync.parse(timeText);
                        const value = parseFloat(oddsText);

                        if (timestamp && !isNaN(value)) {
                            trajectory.push({
                                time: timestamp,
                                value: value,
                                type: 'Initial'
                            });
                        }
                    }
                }
            }

            // [V164.DeepSlam] Fallback: Table Extraction (Legacy)
            if (trajectory.length === 0) {
                const tableRows = document.querySelectorAll('tr');
                tableRows.forEach((row) => {
                    try {
                        const cells = row.querySelectorAll('td');
                        if (cells.length >= 2) {
                            const firstCell = cells[0].textContent.trim();
                            const secondCell = cells[1].textContent.trim();
                            if (!firstCell || !secondCell || isNaN(parseFloat(secondCell))) return;

                            const timestamp = this.sync.parse(firstCell);
                            const value = parseFloat(secondCell);

                            if (timestamp && !isNaN(value) && value > 1.0) {
                                const exists = trajectory.some(p => p.time === timestamp && p.value === value);
                                if (!exists) {
                                    trajectory.push({ time: timestamp, value: value, type: 'Historical' });
                                }
                            }
                        }
                    } catch (e) {}
                });
            }

            // [V164.FullTrajectory] Sequence Generation & Time Alignment
            trajectory.sort((a, b) => new Date(a.time) - new Date(b.time));

            // Mark the first point (oldest) as Initial/Opening if not already
            if (trajectory.length > 0) {
                trajectory[0].type = 'Initial';
            }

        } catch (error) {
            console.error('[V164.FullTrajectory TrajectoryParser] Extraction error:', error.message);
            return {
                trajectory: [],
                valid: false,
                error: error.message,
                recordCount: 0
            };
        } finally {
            if (dom) {
                try {
                    dom.window.close();
                } catch (e) {
                    // Ignore cleanup errors
                }
            }
        }

        // [V164.TitanSlayer] Skeleton Enforcement
        const recordCount = trajectory.length;
        let qualityScore;
        if (recordCount >= 5) {
            qualityScore = 'complete';
        } else if (recordCount >= 3) {
            qualityScore = 'partial';
        } else {
            qualityScore = 'skeleton';
        }

        return {
            trajectory,
            valid: recordCount >= 1,
            recordCount,
            quality: recordCount >= 5 ? 'EXCELLENT' : recordCount >= 3 ? 'GOOD' : 'POOR',
            quality_score: qualityScore
        };
    }

    /**
     * V167.000: [Genesis.FinalWall] Parse DOM-Extracted Odds Data
     *
     * V167.000 修复: 统一配置命名为 `conf`
     *
     * @param {Array} semanticData - 从 DOM 提取的语义数据
     * @param {Object} options - 配置选项
     * @returns {Object} 轨迹数据对象
     */
    parseDOMExtractedData(semanticData, options = {}) {
        // V167.000: 统一命名为 conf (消除作用域阴影 bug)
        const conf = {
            matchId: options.matchId || 'unknown',
            matchTime: options.matchTime || new Date().toISOString(),
            source: 'semantic_extraction',
            titanIdMapping: {
                'Pinnacle': '18',
                'bet365': '32',
                'Bwin': '2',
                'William Hill': '25679340'
            },
            ...options
        };

        const results = {
            trajectory: [],
            providers: [],
            l3OddsHash: null,
            valid: false,
            recordCount: 0
        };

        if (!Array.isArray(semanticData)) {
            return {
                ...results,
                error: 'Invalid input: semanticData is not an array'
            };
        }

        try {
            for (const item of semanticData) {
                // Map provider name to Titan ID
                const titanId = conf.titanIdMapping[item.provider] ||
                                 Object.entries(conf.titanIdMapping).find(([_, v]) => v === item.provider)?.[0];

                if (!titanId) {
                    console.warn('[V167.000] Unknown provider:', item.provider);
                    continue;
                }

                // Create trajectory point
                const timestamp = this.sync.parse(item.timestamp || conf.matchTime);

                const trajectoryPoint = {
                    providerId: titanId,
                    providerName: item.provider,
                    matchId: conf.matchId,
                    dimension: '1',
                    occurred_at: timestamp,
                    value: item.home || null,
                    type: 'SemanticSnapshot'
                };

                results.trajectory.push(trajectoryPoint);

                // Add Home/Draw/Away points
                if (item.home !== undefined) {
                    results.trajectory.push({
                        ...trajectoryPoint,
                        dimension: '1',
                        value: item.home
                    });
                }
                if (item.draw !== undefined) {
                    results.trajectory.push({
                        ...trajectoryPoint,
                        dimension: 'X',
                        value: item.draw
                    });
                }
                if (item.away !== undefined) {
                    results.trajectory.push({
                        ...trajectoryPoint,
                        dimension: '2',
                        value: item.away
                    });
                }

                // V167.000: CONSOLIDATED PAYOUT CALCULATION
                if (item.home && item.draw && item.away) {
                    const payout = this.calculatePayout(item.home, item.draw, item.away);
                    if (payout !== null) {
                        results.trajectory.push({
                            ...trajectoryPoint,
                            dimension: 'payout',
                            value: payout,
                            type: 'PayoutPoint'
                        });
                    }
                }

                results.providers.push({
                    providerId: titanId,
                    providerName: item.provider,
                    home: item.home,
                    draw: item.draw,
                    away: item.away,
                    payout: this.calculatePayoutFromObject(item) // V167.000: 统一计算
                });
            }

            // Generate l3_odds_hash (8-digit hex)
            results.l3OddsHash = this._generateL3OddsHash(results.providers);

            results.recordCount = results.trajectory.length;
            results.valid = results.recordCount >= 1;

            console.log('[V167.000] Parsed', results.providers.length, 'providers,',
                results.recordCount, 'trajectory points');

        } catch (e) {
            results.error = e.message;
            console.error('[V167.000] Parse error:', e.message);
        }

        return results;
    }

    /**
     * V167.000: Process Deep L3 Data with Payout Calculation
     *
     * V167.000 修复: 统一配置命名为 `conf`
     *
     * @param {Array} rawData - Raw data from SurgicalInteraction
     * @param {Object} matchConfig - Match context { matchId, matchTime }
     * @returns {Array} Structured L3 data objects
     */
    processDeepL3Data(rawData, matchConfig = {}) {
        // V167.000: 统一命名为 conf
        const conf = {
            matchId: matchConfig.matchId || 'unknown',
            matchTime: matchConfig.matchTime || new Date().toISOString(),
            ...matchConfig
        };

        const results = [];
        const sync = this.sync;
        const now = new Date();
        const matchDate = conf.matchTime ? new Date(conf.matchTime) : now;

        if (!Array.isArray(rawData)) return results;

        for (const item of rawData) {
            try {
                const struct = {
                    match_id: conf.matchId,
                    provider: item.provider,
                    dimension: item.dimension || '1x2',
                    instant: item.instant,
                    curve: [],
                    opening: null,
                    closing: null
                };

                // Process Curve
                if (Array.isArray(item.curve)) {
                    for (const point of item.curve) {
                        let timestamp = null;
                        const raw = point.raw_time;

                        if (raw === 'now') {
                            timestamp = now.toISOString();
                        } else if (raw.match(/^\d{2}:\d{2}$/)) {
                            const [hh, mm] = raw.split(':').map(Number);
                            timestamp = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate(), hh, mm)).toISOString();
                        } else {
                            sync.baseYear = matchDate.getUTCFullYear();
                            timestamp = sync.parse(raw);
                        }

                        if (timestamp) {
                            const dataPoint = {
                                t: new Date(timestamp).getTime() / 1000,
                                v: point.v,
                                iso: timestamp
                            };
                            if (point.payout) {
                                dataPoint.payout = point.payout;
                            }
                            struct.curve.push(dataPoint);
                        }
                    }

                    // Sort curve chronologically
                    struct.curve.sort((a, b) => a.t - b.t);

                    // Identify Opening (Earliest)
                    if (struct.curve.length > 0) {
                        const first = struct.curve[0];
                        struct.opening = {
                            val: first.v,
                            time: first.iso
                        };
                        if (first.payout) struct.opening.payout = first.payout;
                    }

                    // Identify Closing (Latest)
                    if (struct.curve.length > 0) {
                        const last = struct.curve[struct.curve.length - 1];
                        struct.closing = {
                            val: last.v,
                            time: last.iso
                        };
                        if (last.payout) struct.closing.payout = last.payout;

                        // V166.1: Top-level Market Payout (from latest)
                        if (last.payout) struct.market_payout = last.payout;
                    }
                }

                results.push(struct);

            } catch (e) {
                console.warn(`[V167.000] Failed to process L3 item for ${item.provider}: ${e.message}`);
            }
        }

        return results;
    }

    /**
     * V167.000: Generate L3 Odds Hash
     * @param {Array} providers - 提供商数据
     * @returns {string} 8 位十六进制哈希
     */
    _generateL3OddsHash(providers) {
        if (!providers || providers.length === 0) {
            return null;
        }

        try {
            const limit = Math.min(providers.length, 2);
            let hash = '';

            for (let i = 0; i < limit; i++) {
                const p = providers[i];
                const providerId = p.providerId || '00';

                const h = Math.round((p.home || 0) * 100).toString(16).padStart(2, '0');
                const d = Math.round((p.draw || 0) * 100).toString(16).padStart(2, '0');
                const a = Math.round((p.away || 0) * 100).toString(16).padStart(2, '0');

                hash += providerId.toString().padStart(2, '0') + h + d + a;
            }

            while (hash.length < 8) {
                hash += '0';
            }

            return hash.substring(0, 8);

        } catch (e) {
            console.error('[V167.000] Hash generation error:', e.message);
            return null;
        }
    }

    /**
     * V167.000: Validate trajectory state
     * @param {Array} trajectory - Trajectory array
     * @returns {Object} Validation result
     */
    validateTrajectory(trajectory) {
        const trajectoryArray = Array.isArray(trajectory) ? trajectory : trajectory?.trajectory || [];

        if (!Array.isArray(trajectoryArray) || trajectoryArray.length === 0) {
            return {
                valid: false,
                initial: null,
                current: null,
                hasDrift: false,
                error: 'Trajectory is empty'
            };
        }

        if (trajectoryArray.length < 2) {
            return {
                valid: false,
                initial: trajectoryArray[0]?.value || null,
                current: trajectoryArray[trajectoryArray.length - 1]?.value || null,
                hasDrift: false,
                error: `Insufficient points: ${trajectoryArray.length} < 2`
            };
        }

        const initial = trajectoryArray[0].value;
        const current = trajectoryArray[trajectoryArray.length - 1].value;
        const hasDrift = Math.abs(current - initial) > 0.001;

        return {
            valid: true,
            initial,
            current,
            hasDrift,
            trajectoryLength: trajectoryArray.length
        };
    }
}

// ============================================================================
// V168.002: EXPORTS - Modular Architecture
// ============================================================================

module.exports = {
    // V168.002: Main parser (保留主控制器)
    TrajectoryParser,

    // V168.002: Payout calculation (从 calculators/PayoutCalculator.js 导入)
    PayoutCalculator,

    // V168.002: Time alignment (从 temporal/SyncTimestamp.js 导入)
    SyncTimestamp,
    alignTimestamp,

    // V167.000: Configuration
    EngineConfig
};
