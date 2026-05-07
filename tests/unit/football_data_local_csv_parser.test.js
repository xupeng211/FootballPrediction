'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const http = require('node:http');
const https = require('node:https');
const childProcess = require('node:child_process');
const Module = require('node:module');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const PARSER_PATH = path.join(PROJECT_ROOT, 'scripts/lib/football_data_local_csv_parser.js');
const LEGACY_PATH = path.join(PROJECT_ROOT, 'scripts/ops/fetch_and_adapt_euro_leagues.js');
const FIXTURE_PATH = path.join(PROJECT_ROOT, 'tests/fixtures/football_data/football_data_sample_phase462c.csv');
const PARSER_OPTIONS = {
    sourceName: 'football_data_local_fixture',
    dataVersion: 'PHASE4.62C_LOCAL_PARSER',
    defaultSeason: '2024/2025',
    timezone: 'UTC',
};

function installExecutionGuards(t) {
    const originalHttpRequest = http.request;
    const originalHttpsRequest = https.request;
    const originalFetch = global.fetch;
    const originalSpawn = childProcess.spawn;
    const originalExec = childProcess.exec;
    const originalExecFile = childProcess.execFile;
    const originalLoad = Module._load;
    const fail = name => () => {
        throw new Error(`${name} should not be called by football_data_local_csv_parser`);
    };

    http.request = fail('http.request');
    https.request = fail('https.request');
    global.fetch = fail('global.fetch');
    childProcess.spawn = fail('child_process.spawn');
    childProcess.exec = fail('child_process.exec');
    childProcess.execFile = fail('child_process.execFile');
    Module._load = function patchedLoad(request, parent, isMain) {
        const blockedImports = new Set([
            'pg',
            'fs',
            'node:fs',
            'http',
            'node:http',
            'https',
            'node:https',
            'child_process',
            'node:child_process',
        ]);
        if (blockedImports.has(request) || String(request || '').includes('fetch_and_adapt_euro_leagues')) {
            throw new Error(`blocked import: ${request}`);
        }
        return originalLoad.call(this, request, parent, isMain);
    };

    t.after(() => {
        http.request = originalHttpRequest;
        https.request = originalHttpsRequest;
        global.fetch = originalFetch;
        childProcess.spawn = originalSpawn;
        childProcess.exec = originalExec;
        childProcess.execFile = originalExecFile;
        Module._load = originalLoad;
    });
}

function loadParserFresh() {
    delete require.cache[PARSER_PATH];
    return require(PARSER_PATH);
}

function loadFixtureCsv() {
    return fs.readFileSync(FIXTURE_PATH, 'utf8');
}

test('parser module 可以 import 且无 side effects', t => {
    installExecutionGuards(t);
    const parser = loadParserFresh();

    assert.equal(typeof parser.parseFootballDataCsv, 'function');
    assert.equal(typeof parser.normalizeFootballDataRow, 'function');
    assert.equal(typeof parser.mapFtrToActualResult, 'function');
    assert.equal(typeof parser.parseFootballDataDate, 'function');
    assert.equal(typeof parser.detectOddsColumns, 'function');
    assert.equal(typeof parser.classifyFootballDataRows, 'function');
    assert.equal(require.cache[LEGACY_PATH], undefined);
});

test('parser 可以成功解析本地 synthetic fixture CSV', t => {
    installExecutionGuards(t);
    const parser = loadParserFresh();
    const parsed = parser.parseFootballDataCsv(loadFixtureCsv(), PARSER_OPTIONS);
    const actualResults = parsed.candidate_rows.map(row => row.actual_result);
    const warningCodes = parsed.warnings.map(item => item.code);

    assert.equal(parsed.parser_version, 'PHASE4.62C_FOOTBALL_DATA_LOCAL_CSV_PARSER');
    assert.equal(parsed.source_name, 'football_data_local_fixture');
    assert.equal(parsed.total_rows, 5);
    assert.equal(parsed.parsed_rows, 5);
    assert.equal(parsed.candidate_rows.length, 3);
    assert.deepEqual(actualResults, ['home_win', 'draw', 'away_win']);
    assert.deepEqual(parsed.row_classification, {
        finished_rows: 3,
        trainable_label_rows: 3,
        skipped_rows: 2,
        invalid_date_rows: 1,
        missing_team_rows: 0,
        missing_score_rows: 1,
        invalid_result_rows: 0,
        odds_preview_rows: 3,
    });
    assert.ok(warningCodes.includes('invalid_date'));
    assert.ok(warningCodes.includes('missing_score'));
});

test('candidate rows 应保持 preview only 且不产生任何写入意图', t => {
    installExecutionGuards(t);
    const parser = loadParserFresh();
    const parsed = parser.parseFootballDataCsv(loadFixtureCsv(), PARSER_OPTIONS);
    const firstCandidate = parsed.candidate_rows[0];
    const thirdCandidate = parsed.candidate_rows[2];

    for (const candidate of parsed.candidate_rows) {
        assert.equal(candidate.would_insert_matches, false);
        assert.equal(candidate.would_insert_odds, false);
        assert.equal(candidate.odds_preview.odds_preview_only, true);
        assert.equal(candidate.odds_preview.available, true);
        assert.equal(candidate.data_source, 'football_data_local_fixture');
        assert.equal(candidate.data_version, 'PHASE4.62C_LOCAL_PARSER');
    }

    assert.deepEqual(
        firstCandidate.odds_preview.bookmakers.map(item => item.bookmaker),
        ['Bet365', 'Pinnacle']
    );
    assert.equal(firstCandidate.odds_preview.bookmakers[0].complete_triplet, true);
    assert.equal(thirdCandidate.odds_preview.bookmakers[0].has_any_value, false);
});

test('non_execution_confirmations 必须覆盖 no-network / no-db / no-file-write / no-legacy-runtime', t => {
    installExecutionGuards(t);
    const parser = loadParserFresh();
    const parsed = parser.parseFootballDataCsv(loadFixtureCsv(), PARSER_OPTIONS);

    assert.ok(parsed.non_execution_confirmations.includes('no_external_network'));
    assert.ok(parsed.non_execution_confirmations.includes('no_db_reads'));
    assert.ok(parsed.non_execution_confirmations.includes('no_db_writes'));
    assert.ok(parsed.non_execution_confirmations.includes('no_file_writes'));
    assert.ok(parsed.non_execution_confirmations.includes('no_legacy_runtime'));
    assert.equal(require.cache[LEGACY_PATH], undefined);
});

test('helper functions 支持 FTR label mapping 与日期解析', t => {
    installExecutionGuards(t);
    const parser = loadParserFresh();

    assert.equal(parser.mapFtrToActualResult('H'), 'home_win');
    assert.equal(parser.mapFtrToActualResult('D'), 'draw');
    assert.equal(parser.mapFtrToActualResult('A'), 'away_win');
    assert.equal(parser.mapFtrToActualResult('X'), null);
    assert.equal(parser.parseFootballDataDate('17/08/2024', '17:30', { timezone: 'UTC' }), '2024-08-17T17:30:00.000Z');
    assert.equal(parser.parseFootballDataDate('17/08/24', '07:05', { timezone: 'UTC' }), '2024-08-17T07:05:00.000Z');
    assert.equal(parser.parseFootballDataDate('not-a-date', '17:30', { timezone: 'UTC' }), null);
});

test('FTR 缺失但比分完整时应使用 score-derived fallback', t => {
    installExecutionGuards(t);
    const parser = loadParserFresh();
    const parsed = parser.parseFootballDataCsv(
        'Div,Date,Time,HomeTeam,AwayTeam,FTHG,FTAG,FTR\nSP2,21/08/2024,20:00,Fallback Home,Fallback Away,2,1,',
        PARSER_OPTIONS
    );
    const candidate = parsed.candidate_rows[0];

    assert.equal(parsed.total_rows, 1);
    assert.equal(parsed.row_classification.trainable_label_rows, 1);
    assert.equal(candidate.actual_result, 'home_win');
    assert.equal(candidate.result_source, 'score_derived');
    assert.equal(candidate.would_insert_matches, false);
    assert.equal(candidate.would_insert_odds, false);
    assert.ok(parsed.non_execution_confirmations.includes('no_external_network'));
    assert.ok(parsed.non_execution_confirmations.includes('no_db_reads'));
    assert.ok(parsed.non_execution_confirmations.includes('no_db_writes'));
    assert.ok(parsed.non_execution_confirmations.includes('no_file_writes'));
    assert.ok(parsed.non_execution_confirmations.includes('no_legacy_runtime'));
});

test('非法 FTR 和 FTR/比分冲突必须标记 invalid_result', t => {
    installExecutionGuards(t);
    const parser = loadParserFresh();
    const parsed = parser.parseFootballDataCsv(
        [
            {
                Div: 'SP2',
                Date: '22/08/2024',
                Time: '20:00',
                HomeTeam: 'Bad FTR FC',
                AwayTeam: 'Other FC',
                FTHG: '1',
                FTAG: '1',
                FTR: 'Z',
            },
            {
                Div: 'SP2',
                Date: '22/08/2024',
                Time: '20:00',
                HomeTeam: 'Mismatch FC',
                AwayTeam: 'Other FC',
                FTHG: '2',
                FTAG: '0',
                FTR: 'A',
            },
        ],
        PARSER_OPTIONS
    );

    assert.equal(parsed.total_rows, 2);
    assert.equal(parsed.candidate_rows.length, 0);
    assert.equal(parsed.row_classification.invalid_result_rows, 2);
    assert.equal(parsed.row_classification.skipped_rows, 2);
    assert.deepEqual(
        parsed.warnings.map(item => item.code),
        ['invalid_result', 'result_score_mismatch']
    );
});

test('missing team 行应跳过并记录 warning', t => {
    installExecutionGuards(t);
    const parser = loadParserFresh();
    const parsed = parser.parseFootballDataCsv(
        'Div,Date,Time,HomeTeam,AwayTeam,FTHG,FTAG,FTR\nSP2,23/08/2024,20:00,,Away FC,1,0,H',
        PARSER_OPTIONS
    );

    assert.equal(parsed.candidate_rows.length, 0);
    assert.equal(parsed.row_classification.missing_team_rows, 1);
    assert.equal(parsed.row_classification.skipped_rows, 1);
    assert.equal(parsed.warnings[0].code, 'missing_team');
});

test('无 odds columns 与 partial odds columns 都只能 preview，不写 odds', t => {
    installExecutionGuards(t);
    const parser = loadParserFresh();
    const noOdds = parser.parseFootballDataCsv(
        'Div,Date,Time,HomeTeam,AwayTeam,FTHG,FTAG,FTR\nSP2,24/08/2024,20:00,No Odds Home,No Odds Away,0,0,D',
        PARSER_OPTIONS
    );
    const partialOdds = parser.parseFootballDataCsv(
        'Div,Date,Time,HomeTeam,AwayTeam,FTHG,FTAG,FTR,B365H\nSP2,24/08/2024,20:00,Partial Odds Home,Partial Odds Away,0,0,D,2.10',
        PARSER_OPTIONS
    );
    const partialBookmaker = partialOdds.candidate_rows[0].odds_preview.bookmakers[0];

    assert.equal(noOdds.candidate_rows[0].odds_preview.available, false);
    assert.equal(noOdds.candidate_rows[0].would_insert_odds, false);
    assert.equal(noOdds.row_classification.odds_preview_rows, 0);
    assert.equal(partialOdds.candidate_rows[0].odds_preview.available, true);
    assert.equal(partialBookmaker.supported_columns_present, false);
    assert.equal(partialBookmaker.has_any_value, true);
    assert.equal(partialBookmaker.complete_triplet, false);
    assert.equal(partialOdds.candidate_rows[0].odds_preview_only, true);
    assert.equal(partialOdds.candidate_rows[0].would_insert_odds, false);
});

test('rows 输入、默认 options、短年份、缺失 Time 和空 CSV 分支应稳定', t => {
    installExecutionGuards(t);
    const parser = loadParserFresh();
    const parsed = parser.parseFootballDataCsv([
        {
            Div: 'SP2',
            Date: '25/08/24',
            Time: '',
            HomeTeam: 'Short Year Home',
            AwayTeam: 'Short Year Away',
            FTHG: '0',
            FTAG: '1',
            FTR: 'A',
        },
    ]);
    const empty = parser.parseFootballDataCsv('\n\n');
    const candidate = parsed.candidate_rows[0];

    assert.equal(parsed.source_name, 'football_data_local_csv');
    assert.equal(candidate.match_date, '2024-08-25T00:00:00.000Z');
    assert.equal(candidate.season, '2024/2025');
    assert.equal(candidate.actual_result, 'away_win');
    assert.equal(empty.total_rows, 0);
    assert.equal(empty.parsed_rows, 0);
    assert.equal(empty.row_classification.finished_rows, 0);
});
