'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const path = require('node:path');

const { FOOTBALL_DATA_LEAGUES, parseArgs } = require('../../scripts/ops/fetch_and_adapt_euro_leagues');

test('fetch_and_adapt_euro_leagues 应支持横向扩军 football-data 代码', () => {
    assert.deepEqual(Object.keys(FOOTBALL_DATA_LEAGUES).sort(), [
        'D1',
        'D2',
        'E0',
        'E1',
        'F1',
        'F2',
        'I1',
        'I2',
        'N1',
        'P1',
        'SP1',
        'SP2',
    ]);
    assert.equal(FOOTBALL_DATA_LEAGUES.D2, '2. Bundesliga');
    assert.equal(FOOTBALL_DATA_LEAGUES.SP2, 'Segunda División');
});

test('fetch_and_adapt_euro_leagues 应解析自定义输出路径', () => {
    const options = parseArgs(['--league-code', 'D2', '--season-code', '2223', '--output', 'tmp/d2.csv']);

    assert.equal(options.leagueCode, 'D2');
    assert.equal(options.seasonCode, '2223');
    assert.equal(options.outputPath, path.resolve(__dirname, '../../tmp/d2.csv'));
});
