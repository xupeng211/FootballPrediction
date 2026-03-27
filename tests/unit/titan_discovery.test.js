/**
 * @file titan_discovery.test.js
 * @description titan_discovery CLI 参数解析测试
 */

'use strict';

const { describe, it } = require('node:test');
const assert = require('node:assert');

const { parseArgs } = require('../../scripts/ops/titan_discovery');

describe('titan_discovery CLI', () => {
  it('应识别 --all-leagues 与 --full-sync', () => {
    const options = parseArgs(['--all-leagues', '--full-sync', '--season=2025/2026']);

    assert.strictEqual(options.allLeagues, true);
    assert.strictEqual(options.fullSync, true);
    assert.strictEqual(options.season, '2025/2026');
    assert.strictEqual(options.all, false);
  });

  it('无参数时应默认扫描 P0 联赛', () => {
    const options = parseArgs([]);

    assert.strictEqual(options.all, true);
    assert.strictEqual(options.allLeagues, false);
    assert.strictEqual(options.fullSync, false);
  });
});
