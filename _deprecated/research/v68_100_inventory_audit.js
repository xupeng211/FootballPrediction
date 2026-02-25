/**
 * V68.100 - FotMob Index Layer Inventory Audit
 * ============================================
 *
 * Complete census of the matches table to identify data gaps
 * and assess Golden Data (L2) completeness.
 *
 * @file v68_100_inventory_audit.js
 * @version V68.100
 * @since 2026-01-25
 */

'use strict';

const { Pool } = require('pg');

// ============================================================================
// CONFIGURATION
// ============================================================================

const AUDIT_CONFIG = {
    dbConfig: {
        host: process.env.DB_HOST || '172.25.16.1',
        port: parseInt(process.env.DB_PORT) || 5432,
        database: process.env.DB_NAME || 'football_db',
        user: process.env.DB_USER || 'football_user',
        password: process.env.DB_PASSWORD || 'football_pass'
    },
    targetLeagues: [
        'Premier League',
        'La Liga',
        'Serie A',
        'Bundesliga',
        'Ligue 1'
    ],
    targetSeasons: [
        '2020/2021',
        '2021/2022',
        '2022/2023',
        '2023/2024',
        '2024/2025'
    ]
};

// ============================================================================
// STRUCTURED LOGGER
// ============================================================================

function log(level, message, data = {}) {
    const entry = {
        level,
        module: 'v68_100_inventory_audit',
        version: 'V68.100',
        message,
        ...data,
        timestamp: new Date().toISOString()
    };
    console.log(JSON.stringify(entry));
}

// ============================================================================
// INVENTORY AUDITOR
// ============================================================================

class InventoryAuditor {
    constructor(config) {
        this.config = config;
        this.pool = null;
    }

    async initialize() {
        this.pool = new Pool(this.config.dbConfig);
        log('info', 'Database connection established');
    }

    /**
     * Step A: 维度大盘点 (The Big Count)
     * - Count matches by league_name and season
     * - Focus on Big 5 leagues, seasons 2020/2021 to 2024/2025
     */
    async stepA_BigCount() {
        log('info', 'Starting Step A: 维度大盘点 (The Big Count)');

        const client = await this.pool.connect();
        try {
            // Get league and season combinations
            const countQuery = `
                SELECT
                    league_name,
                    season,
                    COUNT(*) as total_matches,
                    COUNT(CASE WHEN match_id IS NOT NULL THEN 1 END) as with_match_id,
                    MIN(match_date) as earliest_match,
                    MAX(match_date) as latest_match
                FROM matches
                WHERE league_name = ANY($1)
                    AND season = ANY($2)
                GROUP BY league_name, season
                ORDER BY league_name, season;
            `;

            const result = await client.query(countQuery, [
                this.config.targetLeagues,
                this.config.targetSeasons
            ]);

            const summary = {
                total_groups: result.rows.length,
                total_matches: 0,
                by_league: {}
            };

            for (const row of result.rows) {
                summary.total_matches += parseInt(row.total_matches);

                if (!summary.by_league[row.league_name]) {
                    summary.by_league[row.league_name] = {
                        total_matches: 0,
                        seasons: []
                    };
                }

                summary.by_league[row.league_name].total_matches += parseInt(row.total_matches);
                summary.by_league[row.league_name].seasons.push({
                    season: row.season,
                    matches: parseInt(row.total_matches),
                    earliest: row.earliest_match,
                    latest: row.latest_match
                });
            }

            log('info', 'Big Count complete', {
                total_groups: summary.total_groups,
                total_matches: summary.total_matches,
                leagues: Object.keys(summary.by_league)
            });

            return { summary, rows: result.rows };

        } finally {
            client.release();
        }
    }

    /**
     * Step B: 详情完备度审计 (Detail Integrity Check)
     * - Calculate l2_raw_json completeness percentage
     * - Formula: Count(l2_raw_json IS NOT NULL) / Total_Count * 100%
     */
    async stepB_DetailIntegrity() {
        log('info', 'Starting Step B: 详情完备度审计 (Detail Integrity Check)');

        const client = await this.pool.connect();
        try {
            const integrityQuery = `
                SELECT
                    league_name,
                    season,
                    COUNT(*) as total_matches,
                    COUNT(CASE WHEN l2_raw_json IS NOT NULL THEN 1 END) as with_l2_data,
                    ROUND(
                        (COUNT(CASE WHEN l2_raw_json IS NOT NULL THEN 1 END)::numeric /
                         COUNT(*) * 100),
                    2) as completeness_pct,
                    COUNT(CASE WHEN l2_raw_json IS NULL THEN 1 END) as missing_l2_data
                FROM matches
                WHERE league_name = ANY($1)
                    AND season = ANY($2)
                GROUP BY league_name, season
                ORDER BY league_name, season;
            `;

            const result = await client.query(integrityQuery, [
                this.config.targetLeagues,
                this.config.targetSeasons
            ]);

            const summary = {
                total_groups: result.rows.length,
                total_matches: 0,
                total_with_l2: 0,
                avg_completeness: 0,
                by_league: {}
            };

            let completenessSum = 0;

            for (const row of result.rows) {
                summary.total_matches += parseInt(row.total_matches);
                summary.total_with_l2 += parseInt(row.with_l2_data);
                completenessSum += parseFloat(row.completeness_pct);

                if (!summary.by_league[row.league_name]) {
                    summary.by_league[row.league_name] = {
                        total_matches: 0,
                        with_l2_data: 0,
                        seasons: []
                    };
                }

                summary.by_league[row.league_name].total_matches += parseInt(row.total_matches);
                summary.by_league[row.league_name].with_l2_data += parseInt(row.with_l2_data);
                summary.by_league[row.league_name].seasons.push({
                    season: row.season,
                    total: parseInt(row.total_matches),
                    with_l2: parseInt(row.with_l2_data),
                    completeness: row.completeness_pct,
                    missing: parseInt(row.missing_l2_data)
                });
            }

            summary.avg_completeness = result.rows.length > 0
                ? (completenessSum / result.rows.length).toFixed(2)
                : 0;

            log('info', 'Detail Integrity check complete', {
                total_matches: summary.total_matches,
                total_with_l2: summary.total_with_l2,
                avg_completeness: summary.avg_completeness + '%'
            });

            return { summary, rows: result.rows };

        } finally {
            client.release();
        }
    }

    /**
     * Step C: 待补货清单 (The Shopping List)
     * - Identify matches with index but missing details
     * - Compare with matches_mapping to find unbridged records
     */
    async stepC_ShoppingList() {
        log('info', 'Starting Step C: 待补货清单 (The Shopping List)');

        const client = await this.pool.connect();
        try {
            // Get gaps by league and season
            const gapsQuery = `
                WITH index_summary AS (
                    SELECT
                        league_name,
                        season,
                        COUNT(*) as total_index,
                        COUNT(CASE WHEN l2_raw_json IS NOT NULL THEN 1 END) as with_details,
                        COUNT(CASE WHEN l2_raw_json IS NULL THEN 1 END) as missing_details
                    FROM matches
                    WHERE league_name = ANY($1)
                        AND season = ANY($2)
                    GROUP BY league_name, season
                ),
                mapping_summary AS (
                    SELECT
                        mm.league_name,
                        COUNT(*) as mapped_count
                    FROM matches_mapping mm
                    WHERE mm.league_name = ANY($1)
                        AND mm.status IS NULL OR mm.status != 'abandoned'
                    GROUP BY mm.league_name
                )
                SELECT
                    i.league_name,
                    i.season,
                    i.total_index,
                    i.with_details,
                    i.missing_details,
                    ROUND((i.with_details::numeric / i.total_index * 100), 2) as coverage_pct,
                    COALESCE(m.mapped_count, 0) as mapped_to_bridge,
                    i.total_index - COALESCE(m.mapped_count, 0) as unbridged_count
                FROM index_summary i
                LEFT JOIN mapping_summary m ON i.league_name = m.league_name
                ORDER BY i.league_name, i.season;
            `;

            const result = await client.query(gapsQuery, [
                this.config.targetLeagues,
                this.config.targetSeasons
            ]);

            // Get specific sample of missing detail matches (limit 50)
            const missingDetailsQuery = `
                SELECT
                    match_id,
                    league_name,
                    season,
                    home_team,
                    away_team,
                    match_date,
                    l2_raw_json IS NOT NULL as has_l2_data,
                    data_source
                FROM matches
                WHERE league_name = ANY($1)
                    AND season = ANY($2)
                    AND l2_raw_json IS NULL
                ORDER BY league_name, season, match_date DESC
                LIMIT 50;
            `;

            const missingResult = await client.query(missingDetailsQuery, [
                this.config.targetLeagues,
                this.config.targetSeasons
            ]);

            // Calculate total gaps
            const totalGaps = result.rows.reduce((sum, row) =>
                sum + parseInt(row.missing_details), 0);

            const totalUnbridged = result.rows.reduce((sum, row) =>
                sum + parseInt(row.unbridged_count), 0);

            const summary = {
                total_groups: result.rows.length,
                total_missing_details: totalGaps,
                total_unbridged: totalUnbridged,
                sample_missing: missingResult.rows.length
            };

            log('info', 'Shopping List generated', {
                total_groups: summary.total_groups,
                total_missing_details: summary.total_missing_details,
                total_unbridged: summary.total_unbridged,
                sample_size: summary.sample_missing
            });

            return {
                summary,
                gaps: result.rows,
                sampleMissing: missingResult.rows
            };

        } finally {
            client.release();
        }
    }

    /**
     * Get overall matches table statistics (including non-target leagues)
     */
    async getOverallStatistics() {
        log('info', 'Getting overall matches table statistics');

        const client = await this.pool.connect();
        try {
            const statsQuery = `
                SELECT
                    COUNT(*) as total_matches,
                    COUNT(CASE WHEN l2_raw_json IS NOT NULL THEN 1 END) as with_l2_data,
                    COUNT(DISTINCT league_name) as total_leagues,
                    COUNT(DISTINCT season) as total_seasons,
                    MIN(match_date) as earliest_match,
                    MAX(match_date) as latest_match
                FROM matches;
            `;

            const result = await client.query(statsQuery);
            const stats = result.rows[0];

            // Get top leagues by match count
            const topLeaguesQuery = `
                SELECT
                    league_name,
                    COUNT(*) as match_count
                FROM matches
                GROUP BY league_name
                ORDER BY match_count DESC
                LIMIT 10;
            `;

            const leaguesResult = await client.query(topLeaguesQuery);

            log('info', 'Overall statistics retrieved', {
                total_matches: stats.total_matches,
                with_l2_data: stats.with_l2_data,
                total_leagues: stats.total_leagues,
                completeness: ((stats.with_l2_data / stats.total_matches) * 100).toFixed(2) + '%'
            });

            return {
                stats,
                topLeagues: leaguesResult.rows
            };

        } finally {
            client.release();
        }
    }

    /**
     * Run complete audit
     */
    async runAudit() {
        await this.initialize();

        const startTime = Date.now();

        log('info', 'V68.100 Inventory Audit Started');

        // Get overall statistics first
        const overallStats = await this.getOverallStatistics();

        // Step A: Big Count
        const bigCount = await this.stepA_BigCount();

        // Step B: Detail Integrity
        const detailIntegrity = await this.stepB_DetailIntegrity();

        // Step C: Shopping List
        const shoppingList = await this.stepC_ShoppingList();

        const duration = Date.now() - startTime;

        const finalResult = {
            version: 'V68.100',
            status: 'COMPLETED',
            duration_ms: duration,
            overall: {
                total_records: overallStats.stats.total_matches,
                total_with_l2: overallStats.stats.with_l2_data,
                total_leagues: overallStats.stats.total_leagues,
                avg_completeness: ((overallStats.stats.with_l2_data / overallStats.stats.total_matches) * 100).toFixed(2) + '%'
            },
            target_audit: {
                big5_leagues: this.config.targetLeagues.length,
                target_seasons: this.config.targetSeasons.length,
                total_groups: detailIntegrity.rows.length,
                total_matches: detailIntegrity.summary.total_matches,
                total_with_l2: detailIntegrity.summary.total_with_l2,
                avg_completeness: detailIntegrity.summary.avg_completeness + '%',
                total_gaps: shoppingList.summary.total_missing_details,
                total_unbridged: shoppingList.summary.total_unbridged
            },
            report: detailIntegrity.rows.map(row => ({
                league: row.league_name,
                season: row.season,
                total_index: row.total_matches,
                detail_coverage: row.completeness_pct + '%',
                gaps: row.missing_l2_data,
                status: this.getStatusRating(parseFloat(row.completeness_pct))
            }))
        };

        log('info', 'V68.100 Inventory Audit Complete', finalResult);

        await this.cleanup();

        return finalResult;
    }

    /**
     * Get status rating based on completeness
     */
    getStatusRating(completeness) {
        if (completeness >= 90) return 'EXCELLENT';
        if (completeness >= 70) return 'GOOD';
        if (completeness >= 50) return 'FAIR';
        return 'POOR';
    }

    async cleanup() {
        if (this.pool) {
            await this.pool.end();
            log('info', 'Database connection closed');
        }
    }
}

// ============================================================================
// MAIN ENTRY POINT
// ============================================================================

async function main() {
    const auditor = new InventoryAuditor(AUDIT_CONFIG);

    try {
        const result = await auditor.runAudit();

        // Print Golden Data Inventory table
        console.log('\n=== Golden Data Inventory (Big 5 Leagues) ===\n');
        console.log('League'.padEnd(20) + 'Season'.padEnd(12) + 'Total'.padEnd(10) + 'Detail %'.padEnd(12) + 'Gaps'.padEnd(10) + 'Status');
        console.log('='.repeat(84));

        for (const row of result.report) {
            console.log(
                row.league.padEnd(20) +
                row.season.padEnd(12) +
                row.total_index.toString().padEnd(10) +
                row.detail_coverage.padEnd(12) +
                row.gaps.toString().padEnd(10) +
                row.status
            );
        }

        // Print overall summary
        console.log('\n=== Overall Matches Table Statistics ===\n');
        console.log(`Total Records: ${result.overall.total_records}`);
        console.log(`With L2 Data: ${result.overall.total_with_l2}`);
        console.log(`Avg Completeness: ${result.overall.avg_completeness}`);
        console.log(`Total Leagues: ${result.overall.total_leagues}`);

        const gapRate = ((result.target_audit.total_gaps / result.target_audit.total_matches) * 100).toFixed(1);

        console.log(`\n[V68.100] Inventory Audit Complete. Total: ${result.overall.total_records} records. ` +
            `Average Completeness: ${result.overall.avg_completeness}. Gaps: ${result.target_audit.total_gaps} (${gapRate}%).`);

        // Print top gaps recommendation
        if (result.target_audit.total_gaps > 0) {
            console.log('\n=== Priority Gaps for Detail Harvest ===');
            const priorityGaps = result.report
                .filter(r => parseInt(r.gaps) > 0)
                .sort((a, b) => parseInt(b.gaps) - parseInt(a.gaps))
                .slice(0, 5);

            for (const gap of priorityGaps) {
                console.log(`  ${gap.league} ${gap.season}: ${gap.gaps} missing details`);
            }
        }

        process.exit(0);

    } catch (error) {
        log('error', 'Fatal error in inventory audit', {
            error: error.message,
            stack: error.stack
        });
        process.exit(1);
    }
}

if (require.main === module) {
    main();
}

module.exports = { InventoryAuditor, AUDIT_CONFIG };
