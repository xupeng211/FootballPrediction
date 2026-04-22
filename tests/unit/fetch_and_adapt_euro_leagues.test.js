'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');

const {
  resolveCsvField,
  resolveRawReferee,
  resolveTacticalValues
} = require('../../scripts/ops/fetch_and_adapt_euro_leagues');

test('resolveCsvField 应支持显式列别名回退', () => {
  const row = {
    HomeCorners: '8',
    AwayCorners: '3'
  };

  assert.equal(resolveCsvField(row, ['HC', 'HomeCorners']), '8');
  assert.equal(resolveCsvField(row, ['AC', 'AwayCorners']), '3');
  assert.equal(resolveCsvField(row, ['MissingColumn']), '');
});

test('resolveRawReferee 应读取 FotMob 原始裁判字段', () => {
  assert.equal(resolveRawReferee({ raw_referee: 'Alejandro Hernandez' }), 'Alejandro Hernandez');
  assert.equal(resolveRawReferee({ raw_referee: '' }), '');
});

test('resolveTacticalValues 应在 CSV 裁判缺失时回退到 FotMob raw referee', () => {
  const row = {
    HC: '5',
    AC: '4',
    HY: '2',
    AY: '1',
    HR: '0',
    AR: '0'
  };

  const tactical = resolveTacticalValues(row, {
    raw_referee: 'Marco Guida'
  });

  assert.equal(tactical.home_corners, '5');
  assert.equal(tactical.away_corners, '4');
  assert.equal(tactical.home_yellow_cards, '2');
  assert.equal(tactical.away_yellow_cards, '1');
  assert.equal(tactical.referee, 'Marco Guida');
  assert.equal(tactical.referee_source, 'fotmob_raw');
});
