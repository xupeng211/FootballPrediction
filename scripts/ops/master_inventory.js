#!/usr/bin/env node
'use strict';

const { Pool } = require('pg');

const { buildDbConnectionConfig } = require('./helpers/dbBlueprint');

async function withPool(callback) {
    const pool = new Pool(buildDbConnectionConfig());
    try {
        return await callback(pool);
    } finally {
        await pool.end();
    }
}

async function querySourceComposition(pool) {
    const result = await pool.query(`
        SELECT
            COALESCE(data_source, 'UNKNOWN') AS data_source,
            COUNT(*)::int AS match_count
        FROM matches
        GROUP BY COALESCE(data_source, 'UNKNOWN')
        ORDER BY match_count DESC, data_source ASC
    `);

    return result.rows;
}

async function queryBusinessCoverageMap(pool) {
    const result = await pool.query(`
        WITH match_groups AS (
            SELECT
                m.league_name,
                m.season,
                COALESCE(m.data_source, 'UNKNOWN') AS data_source,
                COUNT(*)::int AS total_matches,
                COUNT(*) FILTER (
                    WHERE EXISTS (
                        SELECT 1
                        FROM bookmaker_odds_history h
                        WHERE h.match_id = m.match_id
                    )
                )::int AS with_odds_count,
                MIN(m.match_date) AS earliest_match,
                MAX(m.match_date) AS latest_match
            FROM matches m
            GROUP BY
                m.league_name,
                m.season,
                COALESCE(m.data_source, 'UNKNOWN')
        ),
        odds_groups AS (
            SELECT
                m.league_name,
                m.season,
                COALESCE(m.data_source, 'UNKNOWN') AS data_source,
                COUNT(*)::int AS odds_rows
            FROM matches m
            JOIN bookmaker_odds_history h
                ON h.match_id = m.match_id
            GROUP BY
                m.league_name,
                m.season,
                COALESCE(m.data_source, 'UNKNOWN')
        )
        SELECT
            mg.league_name,
            mg.season,
            mg.data_source,
            mg.total_matches,
            mg.with_odds_count,
            COALESCE(og.odds_rows, 0)::int AS odds_rows,
            mg.earliest_match,
            mg.latest_match
        FROM match_groups mg
        LEFT JOIN odds_groups og
            ON og.league_name = mg.league_name
           AND og.season = mg.season
           AND og.data_source = mg.data_source
        ORDER BY
            mg.league_name ASC,
            mg.season ASC,
            mg.data_source ASC
    `);

    return result.rows;
}

async function queryBookmakerQuality(pool) {
    const result = await pool.query(`
        SELECT
            bookmaker_name,
            COUNT(*)::int AS odds_rows,
            COUNT(DISTINCT match_id)::int AS match_count
        FROM bookmaker_odds_history
        GROUP BY bookmaker_name
        ORDER BY odds_rows DESC, bookmaker_name ASC
    `);

    return result.rows;
}

async function queryMarketQuality(pool) {
    const result = await pool.query(`
        SELECT
            market_type,
            COUNT(*)::int AS odds_rows,
            COUNT(DISTINCT match_id)::int AS match_count
        FROM bookmaker_odds_history
        GROUP BY market_type
        ORDER BY odds_rows DESC, market_type ASC
    `);

    return result.rows;
}

function formatValue(value) {
    if (value === null || value === undefined) {
        return '';
    }

    if (value instanceof Date) {
        return value.toISOString();
    }

    if (typeof value === 'object') {
        return JSON.stringify(value);
    }

    return String(value).replace(/\|/g, '\\|');
}

function formatMarkdownTable(headers, rows) {
    const headerLine = `| ${headers.join(' | ')} |`;
    const separatorLine = `| ${headers.map(() => '---').join(' | ')} |`;
    const bodyLines = rows.map((row) => (
        `| ${row.map((value) => formatValue(value)).join(' | ')} |`
    ));

    return [headerLine, separatorLine, ...bodyLines].join('\n');
}

function renderSection(title, headers, rows) {
    return [`## ${title}`, '', formatMarkdownTable(headers, rows), ''].join('\n');
}

function findDirtyGroups(rows) {
    return rows.filter((row) => Number(row.total_matches) > Number(row.with_odds_count));
}

async function buildInventoryReport() {
    return withPool(async (pool) => {
        const [
            sourceComposition,
            businessCoverage,
            bookmakerQuality,
            marketQuality,
        ] = await Promise.all([
            querySourceComposition(pool),
            queryBusinessCoverageMap(pool),
            queryBookmakerQuality(pool),
            queryMarketQuality(pool),
        ]);

        return {
            sourceComposition,
            businessCoverage,
            bookmakerQuality,
            marketQuality,
            dirtyGroups: findDirtyGroups(businessCoverage),
        };
    });
}

function renderReport(report) {
    const sections = [
        '# Titan 5.0 全景清单',
        '',
        renderSection(
            '数据源构成',
            ['data_source', 'match_count'],
            report.sourceComposition.map((row) => [row.data_source, row.match_count])
        ),
        renderSection(
            'Titan 5.0 资产分布全景图',
            [
                'league_name',
                'season',
                'data_source',
                'total_matches',
                'with_odds_count',
                'odds_rows',
                'earliest_match',
                'latest_match',
            ],
            report.businessCoverage.map((row) => [
                row.league_name,
                row.season,
                row.data_source,
                row.total_matches,
                row.with_odds_count,
                row.odds_rows,
                row.earliest_match,
                row.latest_match,
            ])
        ),
        renderSection(
            '赔率质量检测 - Bookmakers',
            ['bookmaker_name', 'odds_rows', 'match_count'],
            report.bookmakerQuality.map((row) => [
                row.bookmaker_name,
                row.odds_rows,
                row.match_count,
            ])
        ),
        renderSection(
            '赔率质量检测 - Markets',
            ['market_type', 'odds_rows', 'match_count'],
            report.marketQuality.map((row) => [
                row.market_type,
                row.odds_rows,
                row.match_count,
            ])
        ),
    ];

    if (report.dirtyGroups.length === 0) {
        sections.push('## 结论', '', '当前库里不存在“有比赛无赔率”的残留脏数据。', '');
    } else {
        sections.push(
            '## 结论',
            '',
            '当前库里仍存在“有比赛无赔率”的残留脏数据，命中分组如下：',
            '',
            formatMarkdownTable(
                ['league_name', 'season', 'data_source', 'total_matches', 'with_odds_count'],
                report.dirtyGroups.map((row) => [
                    row.league_name,
                    row.season,
                    row.data_source,
                    row.total_matches,
                    row.with_odds_count,
                ])
            ),
            ''
        );
    }

    return sections.join('\n');
}

async function main() {
    const report = await buildInventoryReport();
    console.log(renderReport(report));
}

if (require.main === module) {
    main().catch((error) => {
        console.error(`[MASTER-INVENTORY] 失败: ${error.message}`);
        process.exit(1);
    });
}

module.exports = {
    buildInventoryReport,
    formatMarkdownTable,
    queryBookmakerQuality,
    queryBusinessCoverageMap,
    queryMarketQuality,
    querySourceComposition,
    renderReport,
};
