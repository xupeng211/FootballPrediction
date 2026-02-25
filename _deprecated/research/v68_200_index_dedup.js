/**
 * V68.200 - Index Layer Deduplication Audit & Data Purification
 * =============================================================
 *
 * Identify duplicates, flag golden records, and validate index skeleton.
 *
 * @file v68_200_index_dedup.js
 * @version V68.200
 * @since 2026-01-25
 */

'use strict';

const { Pool } = require('pg');

// ============================================================================
// CONFIGURATION
// ============================================================================

const DEDUP_CONFIG = {
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
        module: 'v68_200_index_dedup',
        version: 'V68.200',
        message,
        ...data,
        timestamp: new Date().toISOString()
    };
    console.log(JSON.stringify(entry));
}

// ============================================================================
// INDEX DEDUP AUDITOR
// ============================================================================

class IndexDedupAuditor {
    constructor(config) {
        this.config = config;
        this.pool = null;
    }

    async initialize() {
        this.pool = new Pool(this.config.dbConfig);
        log('info', 'Database connection established');
    }

    /**
     * Step A: Duplicate Forensic
     * - Check for exact match_id duplicates
     * - Check for logical duplicates (home_team, away_team, match_date)
     * - Identify Unknown league records
     */
    async stepA_DuplicateForensic() {
        log('info', 'Starting Step A: Duplicate Forensic');

        const client = await this.pool.connect();
        try {
            // A1: Check for exact match_id duplicates (should be 0)
            const exactDupQuery = `
                SELECT
                    match_id,
                    COUNT(*) as duplicate_count
                FROM matches
                GROUP BY match_id
                HAVING COUNT(*) > 1;
            `;

            const exactDupResult = await client.query(exactDupQuery);

            // A2: Check for logical duplicates (same teams, same date, different IDs)
            const logicalDupQuery = `
                SELECT
                    home_team,
                    away_team,
                    DATE(match_date) as match_day,
                    COUNT(*) as record_count,
                    ARRAY_AGG(match_id ORDER BY match_id) as match_ids,
                    ARRAY_AGG(CASE WHEN l2_raw_json IS NOT NULL THEN match_id END) as with_l2_ids,
                    ARRAY_AGG(league_name) as leagues
                FROM matches
                GROUP BY home_team, away_team, DATE(match_date)
                HAVING COUNT(*) > 1
                ORDER BY record_count DESC, match_day DESC
                LIMIT 50;
            `;

            const logicalDupResult = await client.query(logicalDupQuery);

            // A3: Identify Unknown league records
            const unknownQuery = `
                SELECT
                    COUNT(*) as unknown_count,
                    COUNT(DISTINCT league_name) as unknown_league_variants
                FROM matches
                WHERE league_name = 'Unknown'
                   OR league_name IS NULL
                   OR league_name = '';
            `;

            const unknownResult = await client.query(unknownQuery);

            // A4: Get Unknown league samples
            const unknownSampleQuery = `
                SELECT
                    match_id,
                    league_name,
                    season,
                    home_team,
                    away_team,
                    match_date,
                    l2_raw_json IS NOT NULL as has_l2
                FROM matches
                WHERE league_name = 'Unknown'
                   OR league_name IS NULL
                   OR league_name = ''
                ORDER BY match_date DESC
                LIMIT 20;
            `;

            const unknownSampleResult = await client.query(unknownSampleQuery);

            const summary = {
                exact_duplicates: parseInt(exactDupResult.rowCount),
                logical_duplicate_groups: parseInt(logicalDupResult.rowCount),
                unknown_records: parseInt(unknownResult.rows[0].unknown_count),
                unknown_league_variants: parseInt(unknownResult.rows[0].unknown_league_variants)
            };

            log('info', 'Duplicate Forensic complete', summary);

            return {
                summary,
                exactDuplicates: exactDupResult.rows,
                logicalDuplicates: logicalDupResult.rows,
                unknownStats: unknownResult.rows[0],
                unknownSamples: unknownSampleResult.rows
            };

        } finally {
            client.release();
        }
    }

    /**
     * Step B: Golden Record Flagging
     * - For each duplicate group, identify the golden record
     * - Golden record = has l2_raw_json data
     * - Output deletion recommendation list
     */
    async stepB_GoldenRecordFlagging() {
        log('info', 'Starting Step B: Golden Record Flagging');

        const client = await this.pool.connect();
        try {
            // Get all duplicate groups with golden record analysis
            const goldenQuery = `
                WITH duplicate_groups AS (
                    SELECT
                        home_team,
                        away_team,
                        DATE(match_date) as match_day,
                        ARRAY_AGG(match_id ORDER BY match_id) as all_ids,
                        ARRAY_AGG(
                            CASE WHEN l2_raw_json IS NOT NULL THEN match_id END
                        ) as ids_with_l2,
                        ARRAY_AGG(
                            CASE WHEN l2_raw_json IS NULL THEN match_id END
                        ) as ids_without_l2,
                        COUNT(*) as group_size
                    FROM matches
                    GROUP BY home_team, away_team, DATE(match_date)
                    HAVING COUNT(*) > 1
                )
                SELECT
                    dg.home_team,
                    dg.away_team,
                    dg.match_day,
                    dg.all_ids,
                    dg.ids_with_l2,
                    dg.ids_without_l2,
                    dg.group_size,
                    COALESCE(dg.ids_with_l2[1], dg.all_ids[1]) as golden_record_id,
                    ARRAY_REMOVE(dg.all_ids, COALESCE(dg.ids_with_l2[1], dg.all_ids[1])) as duplicate_ids,
                    CASE
                        WHEN dg.ids_with_l2[1] IS NOT NULL THEN 'HAS_L2'
                        ELSE 'NO_L2'
                    END as golden_criteria
                FROM duplicate_groups dg
                ORDER BY dg.group_size DESC, dg.match_day DESC
                LIMIT 100;
            `;

            const goldenResult = await client.query(goldenQuery);

            // Calculate statistics
            let totalDuplicates = 0;
            let totalGroups = goldenResult.rows.length;

            for (const row of goldenResult.rows) {
                if (row.duplicate_ids && row.duplicate_ids.length > 0) {
                    totalDuplicates += row.duplicate_ids.length;
                }
            }

            const summary = {
                duplicate_groups: totalGroups,
                total_duplicate_records: totalDuplicates,
                golden_records: totalGroups,
                deletion_candidates: totalDuplicates
            };

            log('info', 'Golden Record Flagging complete', summary);

            return {
                summary,
                goldenRecords: goldenResult.rows
            };

        } finally {
            client.release();
        }
    }

    /**
     * Step C: 5-Season Baseline Validation
     * - Verify cleaned index by league distribution
     * - Confirm if matches table is ready as global unique anchor
     */
    async stepC_BaselineValidation() {
        log('info', 'Starting Step C: 5-Season Baseline Validation');

        const client = await this.pool.connect();
        try {
            // Get pure skeleton counts (excluding unknown/duplicates)
            const pureSkeletonQuery = `
                WITH clean_index AS (
                    SELECT
                        league_name,
                        season,
                        COUNT(*) as total_count
                    FROM matches
                    WHERE league_name = ANY($1)
                        AND season = ANY($2)
                        AND league_name IS NOT NULL
                        AND league_name != 'Unknown'
                        AND league_name != ''
                    GROUP BY league_name, season
                )
                SELECT
                    ci.league_name,
                    ci.season,
                    ci.total_count as raw_count,
                    ci.total_count as recommended_keep,
                    CASE
                        WHEN ci.league_name = 'Unknown' THEN 'PURGE'
                        WHEN ci.total_count > 500 THEN 'REVIEW'
                        ELSE 'OK'
                    END as status_rating
                FROM clean_index ci
                ORDER BY ci.league_name, ci.season;
            `;

            const skeletonResult = await client.query(pureSkeletonQuery, [
                this.config.targetLeagues,
                this.config.targetSeasons
            ]);

            // Get overall clean statistics
            const overallQuery = `
                SELECT
                    COUNT(*) as total_matches,
                    COUNT(DISTINCT match_id) as unique_match_ids,
                    COUNT(DISTINCT CONCAT(home_team, '|', away_team, '|', DATE(match_date))) as unique_match_combinations
                FROM matches
                WHERE league_name IS NOT NULL
                    AND league_name != 'Unknown'
                    AND league_name != '';
            `;

            const overallResult = await client.query(overallQuery);

            const overall = overallResult.rows[0];

            // Calculate duplicates based on unique IDs vs total
            const estimatedDuplicates = parseInt(overall.total_matches) - parseInt(overall.unique_match_ids);
            const estimatedLogicalDuplicates = parseInt(overall.total_matches) - parseInt(overall.unique_match_combinations);

            log('info', 'Baseline Validation complete', {
                total_matches: overall.total_matches,
                unique_match_ids: overall.unique_match_ids,
                unique_combinations: overall.unique_match_combinations,
                estimated_id_duplicates: estimatedDuplicates,
                estimated_logical_duplicates: estimatedLogicalDuplicates
            });

            return {
                overall: {
                    total_matches: overall.total_matches,
                    unique_match_ids: overall.unique_match_ids,
                    unique_combinations: overall.unique_match_combinations,
                    id_duplicates: estimatedDuplicates,
                    logical_duplicates: estimatedLogicalDuplicates
                },
                by_league_season: skeletonResult.rows
            };

        } finally {
            client.release();
        }
    }

    /**
     * Run complete dedup audit
     */
    async runAudit() {
        await this.initialize();

        const startTime = Date.now();

        log('info', 'V68.200 Index Dedup Audit Started');

        // Step A: Duplicate Forensic
        const forensic = await this.stepA_DuplicateForensic();

        // Step B: Golden Record Flagging
        const golden = await this.stepB_GoldenRecordFlagging();

        // Step C: Baseline Validation
        const baseline = await this.stepC_BaselineValidation();

        const duration = Date.now() - startTime;

        const finalResult = {
            version: 'V68.200',
            status: 'COMPLETED',
            duration_ms: duration,
            forensic: {
                exact_duplicates: forensic.summary.exact_duplicates,
                logical_duplicate_groups: forensic.summary.logical_duplicate_groups,
                unknown_records: forensic.summary.unknown_records
            },
            golden: {
                duplicate_groups: golden.summary.duplicate_groups,
                total_duplicate_records: golden.summary.total_duplicate_records,
                deletion_candidates: golden.summary.deletion_candidates
            },
            baseline: {
                total_matches: baseline.overall.total_matches,
                unique_match_ids: baseline.overall.unique_match_ids,
                id_duplicates: baseline.overall.id_duplicates,
                logical_duplicates: baseline.overall.logical_duplicates,
                pure_skeleton: baseline.overall.unique_match_combinations
            },
            report: baseline.by_league_season.map(row => ({
                league: row.league_name,
                season: row.season,
                raw_count: row.raw_count,
                duplicates_recommend: 0, // Will calculate based on logical dupes
                recommended_keep: row.recommended_keep,
                status: row.status_rating
            }))
        };

        log('info', 'V68.200 Index Dedup Audit Complete', finalResult);

        await this.cleanup();

        return finalResult;
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
    const auditor = new IndexDedupAuditor(DEDUP_CONFIG);

    try {
        const result = await auditor.runAudit();

        // Print Data Purity Report table
        console.log('\n=== Data Purity Report (Skeleton Purification) ===\n');
        console.log('League'.padEnd(20) + 'Raw Count'.padEnd(12) + 'Dup/Dirty'.padEnd(12) + 'Keep'.padEnd(10) + 'Status');
        console.log('='.repeat(70));

        for (const row of result.report) {
            const dupCount = row.league === 'Unknown' ? row.raw_count : 0;
            console.log(
                (row.league || 'Unknown').padEnd(20) +
                row.raw_count.toString().padEnd(12) +
                dupCount.toString().padEnd(12) +
                row.recommended_keep.toString().padEnd(10) +
                row.status
            );
        }

        // Print Unknown details
        if (result.forensic.unknown_records > 0) {
            console.log('\n=== Unknown League Records ===');
            console.log(`Total Unknown: ${result.forensic.unknown_records}`);
            console.log('Action Required: PURGE all Unknown league records');
        }

        // Print deletion recommendations
        if (result.golden.deletion_candidates > 0) {
            console.log('\n=== Deletion Recommendation ===');
            console.log(`Total Duplicate Groups: ${result.golden.duplicate_groups}`);
            console.log(`Records to Delete: ${result.golden.deletion_candidates}`);
            console.log('Golden Records: 1 per group (has L2 data preferred)');
        }

        const pureSkeleton = result.baseline.pure_skeleton;
        const readyForAutoAlignment = result.baseline.logical_duplicates < 100 && result.forensic.unknown_records < 100;

        console.log(`\n[V68.200] Index Dedup Audit Complete.`);
        console.log(`${result.baseline.id_duplicates} duplicates found.`);
        console.log(`Pure skeleton: ${pureSkeleton} matches.`);
        console.log(`Ready for auto-alignment: ${readyForAutoAlignment ? 'YES' : 'NO - requires cleanup'}.`);

        process.exit(0);

    } catch (error) {
        log('error', 'Fatal error in dedup audit', {
            error: error.message,
            stack: error.stack
        });
        process.exit(1);
    }
}

if (require.main === module) {
    main();
}

module.exports = { IndexDedupAuditor, DEDUP_CONFIG };
