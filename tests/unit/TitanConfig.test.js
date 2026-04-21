const { describe, it } = require('node:test');
const assert = require('node:assert');
const { TitanConfig } = require('../../src/infrastructure/config/TitanConfig');

describe('TitanConfig', () => {
  it('应该加载默认配置', () => {
    const config = new TitanConfig();
    const db = config.getDatabase();

    assert.strictEqual(db.name, 'football_db');
    assert.strictEqual(db.user, 'football_user');
    assert.strictEqual(db.port, 5432);
  });

  it('应该验证必填配置', () => {
    const originalPassword = process.env.DB_PASSWORD;
    delete process.env.DB_PASSWORD;

    const config = new TitanConfig();

    assert.throws(() => {
      config.validateConfig();
    }, /DB_PASSWORD 未设置/);

    if (originalPassword) process.env.DB_PASSWORD = originalPassword;
  });

  it('应该通过路径访问配置', () => {
    const config = new TitanConfig();
    const db = config.get('database');

    assert.ok(db);
    assert.strictEqual(db.name, 'football_db');
  });

  it('应该返回环境信息', () => {
    const config = new TitanConfig();
    const env = config.getEnvironment();

    assert.strictEqual(typeof env.nodeEnv, 'string');
    assert.strictEqual(typeof env.dockerEnv, 'boolean');
  });

  it('应该加载代理配置', () => {
    const config = new TitanConfig();
    const proxy = config.getProxy();

    assert.ok(proxy.host);
    assert.ok(Array.isArray(proxy.ports));
  });
});
