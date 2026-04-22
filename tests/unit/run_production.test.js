'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');

const {
  getFlagValue,
  parseCliArgs,
  parseLeagueIds
} = require('../../scripts/ops/run_production');

test('getFlagValue 应读取命令行旗标值', () => {
  const argv = ['--season', '2025/2026', '--date-from', '2025-08-01'];

  assert.equal(getFlagValue(argv, '--season'), '2025/2026');
  assert.equal(getFlagValue(argv, '--date-from'), '2025-08-01');
  assert.equal(getFlagValue(argv, '--missing'), null);
});

test('parseLeagueIds 应过滤非法值并去空', () => {
  assert.deepEqual(parseLeagueIds('47, 87,foo,54,,55'), [47, 87, 54, 55]);
  assert.deepEqual(parseLeagueIds(null), []);
});

test('parseCliArgs 应解析回填过滤参数', () => {
  const options = parseCliArgs([
    '--limit', '796',
    '--workers', '15',
    '--league-ids', '47,87,54,55,53',
    '--season', '2025/2026',
    '--date-from', '2025-08-01',
    '--date-to', '2026-01-01',
    '--progress-every', '25',
    '--finished-only',
    '--dry-run'
  ]);

  assert.equal(options.limit, 796);
  assert.equal(options.concurrency, 15);
  assert.deepEqual(options.leagueIds, [47, 87, 54, 55, 53]);
  assert.equal(options.season, '2025/2026');
  assert.equal(options.dateFrom, '2025-08-01');
  assert.equal(options.dateTo, '2026-01-01');
  assert.equal(options.progressEvery, 25);
  assert.equal(options.finishedOnly, true);
  assert.equal(options.dryRun, true);
});
