/**
 * V79.200 - BridgeEngine (Single Source of Excellence)
 * ======================================================
 *
 * V79.200 更新:
 * - 使用 config_loader.js 加载外部化队名映射
 * - 使用 math_utils.js 的 Levenshtein 算法
 * - 移除硬编码 TEAM_NORMALIZATIONS 常量
 *
 * 核心特性:
 *   - ✅ 修正后的 Levenshtein 算法（V73.000 验证）
 *   - ✅ 队名标准化映射（外部化至 config/team_aliases.json）
 *   - ✅ 英超优先匹配策略（避开数据陷阱）
 *   - ✅ 直接 matches_mapping→matches_mapping 匹配
 *   - ✅ 多特征置信度评分
 *
 * @file bridge_engine.js
 * @version V79.200
 * @since 2026-01-25
 * @author V79.200 Engineering Team
 */

'use strict';

const { Pool } = require('pg');
const path = require('path');
const { spawn } = require('child_process');
const { getTeamAliasesConfig } = require('../../scripts/ops/config_loader.js');
const { similarity, levenshtein } = require('../utils/math_utils.js');

// ============================================================================
// CONFIGURATION
// ============================================================================

const BRIDGE_ENGINE_CONFIG = {
    // 模糊匹配阈值（V73.000 验证优化）
    fuzzyThreshold: 70.0,  // 降低阈值以提高匹配率（85% → 70%）

    // 批次处理大小
    batchSize: 100,

    // 数据库连接配置
    db: {
        host: process.env.DB_HOST || '172.25.16.1',
        port: parseInt(process.env.DB_PORT) || 5432,
        database: process.env.DB_NAME || 'football_db',
        user: process.env.DB_USER || 'football_user',
        password: process.env.DB_PASSWORD || 'football_pass',
        max: 20
    },

    // V81.200 Discovery Radar 配置（持久化至 config/hyper_parameters.yaml）
    discoveryRadar: {
        enabled: true,  // 启用雷达作为标准 Fallback 路径

        // RapidFuzz C++ 引擎配置
        engine: {
            scorer: 'WRatio',  // WRatio: 加权 Levenshtein 距离
            processorCount: 1  // CPU 核心数
        },

        // 阈值配置
        thresholds: {
            autoApprove: 85.0,     // > 85%: 自动批准
            pendingReview: 70.0,   // 70-85%: 待审核
            minThreshold: 65.0,     // < 65%: 拒绝
            highConfidence: 90.0    // 高置信度阈值
        },

        // 候选数限制
        candidates: {
            maxPerTeam: 5,  // 每支球队最多候选数
            maxTotal: 10     // 总候选数限制
        },

        // 验证配置
        verification: {
            requireDateMatch: false,    // 是否要求日期匹配
            dateMatchWindowDays: 7,     // 日期匹配窗口
            requireOddsValidation: false // 是否验证赔率完整性
        }
    },

    // 英超优先策略配置
    premierLeague: {
        // 英超 2020-2022 有充足历史映射数据
        prioritySeasons: ['2020-2021', '2021-2022', '2022-2023'],
        priorityLeague: 'Premier League',
        // 英超队名标准化
        normalizations: {
            'Man Utd': 'Manchester United',
            'Man United': 'Manchester United',
            'Man City': 'Manchester City',
            'Wolves': 'Wolverhampton Wanderers',
            'Spurs': 'Tottenham Hotspur',
            'Newcastle': 'Newcastle United',
            'West Ham': 'West Ham United',
            'Brighton': 'Brighton & Hove Albion',
            'Leicester': 'Leicester City',
            'Leeds': 'Leeds United',
            'Norwich': 'Norwich City',
            'Nottm Forest': 'Nottingham Forest',
            'Sheffield Utd': 'Sheffield United',
            'Aston Villa': 'Aston Villa',
            'Bournemouth': 'AFC Bournemouth',
            'Crystal Palace': 'Crystal Palace',
            'Ipswich': 'Ipswich Town',
            'Fulham': 'Fulham',
            'Brentford': 'Brentford',
            'Everton': 'Everton',
            'Chelsea': 'Chelsea',
            'Arsenal': 'Arsenal',
            'Liverpool': 'Liverpool',
            'Watford': 'Watford',
            'Burnley': 'Burnley',
            'Luton': 'Luton Town',
        }
    }
};

// =============================================================================
// V79.200: Team Name Normalization (使用外部化配置)
// =============================================================================

/**
 * V79.200: 标准化队名（使用 config_loader.js）
 * @param {string} teamName - 原始队名
 * @returns {string} - 标准化后的队名
 */
function normalizeTeamName(teamName) {
    if (!teamName) return '';
    const teamAliasesConfig = getTeamAliasesConfig();
    return teamAliasesConfig.normalizeTeamName(teamName);
}

// ============================================================================
// V81.000: Radar Trigger Functions
// ============================================================================

/**
 * V81.000: Spawn a process asynchronously and return the result
 * @param {string} command - Command to execute
 * @param {Array<string>} args - Arguments array
 * @param {Object} options - Options object
 * @returns {Promise<{stdout: string, stderr: string}>}
 */
function spawnAsync(command, args, options = {}) {
    return new Promise((resolve, reject) => {
        const child = spawn(command, args, options);

        let stdout = '';
        let stderr = '';

        child.stdout.on('data', (data) => {
            stdout += data.toString();
        });

        child.stderr.on('data', (data) => {
            stderr += data.toString();
        });

        child.on('close', (code) => {
            if (code === 0) {
                resolve({ stdout, stderr });
            } else {
                reject(new Error(`Process exited with code ${code}: ${stderr}`));
            }
        });

        child.on('error', (error) => {
            reject(error);
        });
    });
}

/**
 * V81.000: 触发 Python 雷达扫描（使用配置文件阈值）
 * @param {Object} matchData - Match data from database
 * @returns {Promise<Object|null>} - Radar result or null
 */
async function triggerRadar(matchData) {
    // V81.200: 检查雷达是否启用
    if (!BRIDGE_ENGINE_CONFIG.discoveryRadar.enabled) {
        console.log(`[BridgeEngine V81.200] ⚠️ 雷达功能已禁用（配置文件 discoveryRadar.enabled = false）`);
        return null;
    }

    try {
        const radarScript = path.join(__dirname, '../../scripts/ops/v81_000_radar_trigger.py');

        // 格式化比赛日期为 ISO string
        const matchDate = new Date(matchData.match_date).toISOString();

        // V81.200: 从配置文件读取阈值
        const threshold = BRIDGE_ENGINE_CONFIG.discoveryRadar.thresholds.minThreshold;

        const args = [
            radarScript,
            '--match-id', matchData.match_id,
            '--home-team', matchData.home_team,
            '--away-team', matchData.away_team,
            '--league', matchData.league_name,
            '--match-date', matchDate,
            '--threshold', threshold.toString(),
        ];

        console.log(`[BridgeEngine V81.200] 触发雷达: ${matchData.match_id} (${matchData.home_team} vs ${matchData.away_team}) [threshold: ${threshold}%]`);

        const { stdout, stderr } = await spawnAsync('python3', args, {
            cwd: path.join(__dirname, '../..')
        });

        // V82.600: 使用正则提取 JSON_RESULT 标记内容（深度容错）
        let result = null;
        try {
            // 优先使用标记提取（最安全）
            const jsonMatch = stdout.match(/\[JSON_RESULT\](.+?)\[JSON_RESULT\]/s);
            if (jsonMatch && jsonMatch[1]) {
                result = JSON.parse(jsonMatch[1]);
            } else {
                // 降级方案：尝试解析最后一行（向后兼容）
                const lines = stdout.trim().split('\n');
                for (let i = lines.length - 1; i >= 0; i--) {
                    if (lines[i].trim()) {
                        try {
                            result = JSON.parse(lines[i].trim());
                            break;
                        } catch {
                            continue;
                        }
                    }
                }
            }

            if (!result) {
                throw new Error('No valid JSON found in output');
            }
        } catch (parseError) {
            console.error(`[BridgeEngine V82.600] ❌ JSON 解析失败: ${parseError.message}`);
            console.error(`[BridgeEngine V82.600] stderr: ${stderr}`);
            console.error(`[BridgeEngine V82.600] stdout (last 200 chars): ${stdout.slice(-200)}`);
            return null;
        }

        if (result.success) {
            console.log(`[BridgeEngine V81.200] ✅ 雷达发现: ${result.url} (method: ${result.discovery_method})`);
            return {
                fotmob_id: result.match_id,
                url: result.url,
                similarity: threshold,  // 使用配置的阈值
                confidence: threshold / 100,
                discovery_method: result.discovery_method
            };
        } else {
            console.log(`[BridgeEngine V81.200] ⚠️ 雷达未找到匹配: ${result.error}`);
            return null;
        }

    } catch (error) {
        console.error(`[BridgeEngine V81.200] ❌ 雷达触发失败: ${error.message}`);
        return null;
    }
}

// ============================================================================
// BRIDGE ENGINE (CORE CLASS)
// ============================================================================

class BridgeEngine {
    /**
     * @param {Pool} db - Database pool
     */
    constructor(db) {
        this.db = db;
    }

    /**
     * Scan for matches needing bridge mapping (英超优先策略)
     * @param {number} [limit=100] - Maximum matches to process
     * @returns {Promise<Array>} - Matches needing bridge
     */
    async scan(limit = 100) {
        const client = await this.db.connect();
        try {
            // 策略 1: 优先扫描英超 2020-2022（唯一有充足历史映射的区域）
            const premierLeagueQuery = `
                SELECT m.match_id, m.league_name, m.home_team, m.away_team, m.match_date
                FROM matches m
                LEFT JOIN matches_mapping mm ON m.match_id = mm.fotmob_id
                WHERE mm.fotmob_id IS NULL
                  AND m.l2_raw_json IS NOT NULL
                  AND m.league_name = 'Premier League'
                  AND m.match_date >= '2020-08-01'
                  AND m.match_date < '2023-01-01'
                ORDER BY m.match_date DESC
                LIMIT $1
            `;

            const eplResult = await client.query(premierLeagueQuery, [limit]);

            if (eplResult.rows.length > 0) {
                console.log(`[BridgeEngine] 扫描到 ${eplResult.rows.length} 场英超 2020-2022 待映射比赛`);
                return eplResult.rows;
            }

            // 策略 2: 其他联赛（如果英超已处理完）
            const otherLeaguesQuery = `
                SELECT m.match_id, m.league_name, m.home_team, m.away_team, m.match_date
                FROM matches m
                LEFT JOIN matches_mapping mm ON m.match_id = mm.fotmob_id
                WHERE mm.fotmob_id IS NULL
                  AND m.l2_raw_json IS NOT NULL
                  AND m.league_name IN ('La Liga', 'Serie A', 'Bundesliga', 'Ligue 1')
                  AND m.match_date >= '2020-08-01'
                ORDER BY m.league_name, m.match_date DESC
                LIMIT $1
            `;

            const otherResult = await client.query(otherLeaguesQuery, [limit]);
            console.log(`[BridgeEngine] 扫描到 ${otherResult.rows.length} 场其他联赛待映射比赛`);
            return otherResult.rows;

        } finally {
            client.release();
        }
    }

    /**
     * Find best match using fuzzy team name matching
     * @param {Object} matchData - Match data from database
     * @returns {Promise<Object|null>} - Best match result or null
     */
    async findBestMatch(matchData) {
        const client = await this.db.connect();
        try {
            // 查询已有映射（直接从 matches_mapping，绕过 entities_mapping）
            const query = `
                SELECT fotmob_id, oddsportal_url, home_team, away_team, league_name, match_date
                FROM matches_mapping
                WHERE COALESCE(league_name, '') = $1
                  AND oddsportal_url IS NOT NULL
                  AND home_team IS NOT NULL AND away_team IS NOT NULL
                ORDER BY match_date DESC
                LIMIT 100
            `;

            const result = await client.query(query, [matchData.league_name]);

            if (result.rows.length === 0) {
                return null;
            }

            // 计算相似度（使用标准化队名）
            let bestMatch = null;
            let bestScore = 0;

            // 标准化待匹配比赛的队名
            const normalizedHome = normalizeTeamName(matchData.home_team);
            const normalizedAway = normalizeTeamName(matchData.away_team);

            for (const row of result.rows) {
                // 跳过空队名
                if (!row.home_team || !row.away_team) continue;

                // 标准化参考数据的队名
                const refHome = normalizeTeamName(row.home_team);
                const refAway = normalizeTeamName(row.away_team);

                const sim1 = similarity(normalizedHome, refHome);
                const sim2 = similarity(normalizedAway, refAway);
                const avgSimilarity = (sim1 + sim2) / 2;

                if (avgSimilarity > bestScore && avgSimilarity >= BRIDGE_ENGINE_CONFIG.fuzzyThreshold) {
                    bestScore = avgSimilarity;
                    bestMatch = {
                        fotmob_id: row.fotmob_id,
                        url: row.oddsportal_url,
                        similarity: avgSimilarity,
                        confidence: avgSimilarity / 100
                    };
                }
            }

            return bestMatch;

        } finally {
            client.release();
        }
    }

    /**
     * Save mapping to database
     * @param {Object} matchData - Match data
     * @param {Object} mappingResult - Mapping result
     * @returns {Promise<void>}
     */
    async saveMapping(matchData, mappingResult) {
        const client = await this.db.connect();
        try {
            // Get match data from matches table
            const matchQuery = `
                SELECT match_date, home_team, away_team, league_name
                FROM matches
                WHERE match_id = $1
            `;

            const matchResult = await client.query(matchQuery, [matchData.match_id]);

            if (matchResult.rows.length === 0) {
                throw new Error(`Match ${matchData.match_id} not found in matches table`);
            }

            const matchInfo = matchResult.rows[0];

            // Insert into matches_mapping
            const insertQuery = `
                INSERT INTO matches_mapping (
                    fotmob_id, oddsportal_url, confidence, mapping_method,
                    review_status, match_date, home_team, away_team, league_name
                )
                VALUES ($1, $2, $3, 'fuzzy_match', 'approved', $4, $5, $6, $7)
                ON CONFLICT (fotmob_id)
                DO UPDATE SET
                    oddsportal_url = EXCLUDED.oddsportal_url,
                    confidence = EXCLUDED.confidence,
                    updated_at = NOW()
            `;

            await client.query(insertQuery, [
                matchData.match_id,
                mappingResult.url,
                mappingResult.confidence,
                matchInfo.match_date,
                matchInfo.home_team,
                matchInfo.away_team,
                matchInfo.league_name
            ]);

            // Update pipeline state
            await client.query(
                `INSERT INTO match_pipeline_state (match_id, status, updated_at)
                 VALUES ($1, 'MAPPED', NOW())
                 ON CONFLICT (match_id)
                 DO UPDATE SET status = 'MAPPED', updated_at = NOW()`,
                [matchData.match_id]
            );

            console.log(`[BridgeEngine] ✅ 保存映射: ${matchData.match_id} (confidence: ${mappingResult.confidence.toFixed(2)})`);

        } finally {
            client.release();
        }
    }

    /**
     * Execute full bridge flow
     * @param {number} [limit=100] - Maximum matches to process
     * @returns {Promise<Object>} - Execution result
     */
    async execute(limit = 100) {
        console.log(`[BridgeEngine] 开始桥接映射 (limit: ${limit})`);

        const matches = await this.scan(limit);

        if (matches.length === 0) {
            console.log('[BridgeEngine] 没有待映射的比赛');
            return { processed: 0, mapped: 0, failed: 0 };
        }

        let mapped = 0;
        let failed = 0;

        let radarMapped = 0;  // V81.000: 雷达映射计数

        for (const match of matches) {
            try {
                const bestMatch = await this.findBestMatch(match);

                if (bestMatch) {
                    await this.saveMapping(match, bestMatch);
                    mapped++;
                } else {
                    // V81.000: 触发雷达扫描（全量暴力寻址）
                    console.log(`[BridgeEngine] ⚠️ 标准匹配失败，触发雷达: ${match.match_id} (${match.home_team} vs ${match.away_team})`);

                    const radarResult = await triggerRadar(match);

                    if (radarResult) {
                        await this.saveMapping(match, radarResult);
                        mapped++;
                        radarMapped++;
                    } else {
                        failed++;
                        console.log(`[BridgeEngine] ❌ 雷达也未找到匹配: ${match.match_id}`);
                    }
                }

            } catch (error) {
                failed++;
                console.error(`[BridgeEngine] ❌ 错误: ${match.match_id} - ${error.message}`);
            }
        }

        const successRate = matches.length > 0 ? (mapped / matches.length * 100).toFixed(2) : '0.00';

        // V81.000: 输出雷达统计
        console.log(`[BridgeEngine V81.000] 桥接完成: 处理 ${matches.length} 场, 成功 ${mapped} 场 (雷达: ${radarMapped}), 失败 ${failed} 场, 成功率 ${successRate}%`);

        return {
            processed: matches.length,
            mapped,
            failed,
            success_rate: successRate + '%'
        };
    }
}

// ============================================================================
// CONVENIENCE FUNCTIONS
// ============================================================================

/**
 * Create BridgeEngine instance with database connection
 * @param {Object} config - Database configuration
 * @returns {BridgeEngine} - BridgeEngine instance
 */
function createBridgeEngine(config) {
    const db = new Pool(config || BRIDGE_ENGINE_CONFIG.db);
    return new BridgeEngine(db);
}

// ============================================================================
// EXPORTS
// ============================================================================

module.exports = {
    BridgeEngine,
    createBridgeEngine,
    BRIDGE_ENGINE_CONFIG,
    similarity,
    normalizeTeamName,
    levenshtein
};

// ============================================================================
// CLI TEST INTERFACE
// ============================================================================

if (require.main === module) {
    // Test cases
    const testCases = [
        // Man Utd vs Manchester United
        { fotmob: 'Man Utd', oddsportal: 'Manchester United', expected: 100 },
        { fotmob: 'Manchester United', oddsportal: 'Man Utd', expected: 100 },
        // Real Madrid vs R. Madrid
        { fotmob: 'Real Madrid', oddsportal: 'R. Madrid', expected: 85 },
        { fotmob: 'Real Madrid', oddsportal: 'Real Madrid', expected: 100 },
        // Athletic Club variants
        { fotmob: 'Athletic Club', oddsportal: 'Athletic Bilbao', expected: 100 },
        { fotmob: 'Athletic Bilbao', oddsportal: 'Athletic Club', expected: 100 },
    ];

    console.log('=== BridgeEngine CLI Test ===\n');

    for (const tc of testCases) {
        const sim = similarity(tc.fotmob, tc.oddsportal);
        const norm1 = normalizeTeamName(tc.fotmob);
        const norm2 = normalizeTeamName(tc.oddsportal);
        const simNorm = similarity(norm1, norm2);

        console.log(`Test: ${tc.fotmob} vs ${tc.oddsportal}`);
        console.log(`  Original similarity: ${sim.toFixed(2)}%`);
        console.log(`  Normalized: ${norm1} vs ${norm2}`);
        console.log(`  Normalized similarity: ${simNorm.toFixed(2)}%`);
        console.log(`  Expected: ≥${tc.expected}%`);
        console.log(`  Result: ${simNorm >= tc.expected ? '✅ PASS' : '❌ FAIL'}`);
        console.log('---');
    }
}
