'use strict';

const { afterEach, describe, it } = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const {
  loadActiveRegistry,
  normalizeSeasonTag,
  resolveSeasonContext
} = require('../../scripts/ops/helpers/seasonRuntimeConfig');

const ENV_KEYS = [
  'ACTIVE_REGISTRY_PATH',
  'ACTIVE_SEASON',
  'ACTIVE_SEASON_TAG',
  'ODDS_HARVEST_SEASON',
  'ODDS_HARVEST_SEASON_TAG'
];

const ENV_SNAPSHOT = Object.fromEntries(ENV_KEYS.map((key) => [key, process.env[key]]));

function restoreEnv() {
  for (const [key, value] of Object.entries(ENV_SNAPSHOT)) {
    if (typeof value === 'undefined') {
      delete process.env[key];
      continue;
    }
    process.env[key] = value;
  }
}

function createRegistryFixture(activeContext = {}) {
  const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'season-runtime-config-'));
  const fixturePath = path.join(tempDir, 'active_registry.json');
  fs.writeFileSync(fixturePath, JSON.stringify({
    registry_id: 'REG-TEST',
    active_context: activeContext,
    registry_config: {}
  }, null, 2));
  return fixturePath;
}

afterEach(() => {
  restoreEnv();
});

describe('seasonRuntimeConfig', () => {
  it('应该从 active_registry.json 读取当前赛季', () => {
    const registry = loadActiveRegistry();
    assert.ok(registry.path.endsWith('config/active_registry.json'));

    const context = resolveSeasonContext({
      seasonEnvVar: 'ODDS_HARVEST_SEASON',
      seasonTagEnvVar: 'ODDS_HARVEST_SEASON_TAG'
    });

    assert.strictEqual(context.season, '2024/2025');
    assert.strictEqual(context.seasonTag, '20242025');
    assert.match(context.source, /^registry:/);
  });

  it('应该优先采用环境变量并自动推导 seasonTag', () => {
    process.env.ODDS_HARVEST_SEASON = '2025-2026';
    delete process.env.ODDS_HARVEST_SEASON_TAG;

    const context = resolveSeasonContext({
      seasonEnvVar: 'ODDS_HARVEST_SEASON',
      seasonTagEnvVar: 'ODDS_HARVEST_SEASON_TAG'
    });

    assert.strictEqual(context.season, '2025/2026');
    assert.strictEqual(context.seasonTag, '20252026');
    assert.strictEqual(context.source, 'env:ODDS_HARVEST_SEASON');
  });

  it('应该在 season 与 seasonTag 不一致时抛错', () => {
    process.env.ODDS_HARVEST_SEASON = '2024/2025';
    process.env.ODDS_HARVEST_SEASON_TAG = '20252026';

    assert.throws(() => {
      resolveSeasonContext({
        seasonEnvVar: 'ODDS_HARVEST_SEASON',
        seasonTagEnvVar: 'ODDS_HARVEST_SEASON_TAG'
      });
    }, /赛季配置不一致/);
  });

  it('应该在缺少赛季配置时抛错', () => {
    const fixturePath = createRegistryFixture({});
    process.env.ACTIVE_REGISTRY_PATH = fixturePath;

    assert.throws(() => {
      resolveSeasonContext();
    }, /缺少赛季配置/);
  });

  it('normalizeSeasonTag 应接受多种赛季格式', () => {
    assert.strictEqual(normalizeSeasonTag('2024/2025'), '20242025');
    assert.strictEqual(normalizeSeasonTag('20242025'), '20242025');
    assert.strictEqual(normalizeSeasonTag('2024-2025'), '20242025');
  });
});
