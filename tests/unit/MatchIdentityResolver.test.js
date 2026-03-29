'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');

const { MatchIdentityResolver } = require('../../src/infrastructure/services/recon/MatchIdentityResolver');
const { RepositoryError } = require('../../src/infrastructure/services/FixtureRepository');

test('MatchIdentityResolver.resolveCanonicalFixtures 应优先复用已存在的 RECON_LINKED canonical 实体', async () => {
  let releaseCalls = 0;

  const pool = {
    async connect() {
      return {
        async query(sql) {
          if (!sql.includes('SELECT match_id, season, data_source, external_id, pipeline_status, created_at')) {
            throw new Error(`unexpected_query:${sql}`);
          }

          return {
            rows: [
              {
                match_id: '130_20252026_5025527',
                season: '2025/2026',
                data_source: 'FotMob',
                external_id: '5071062',
                pipeline_status: 'RECON_LINKED',
                created_at: '2026-03-27T07:59:05.995Z'
              },
              {
                match_id: '130_20252026_4694245',
                season: '2025/2026',
                data_source: 'FotMob',
                external_id: '5071062',
                pipeline_status: 'failed',
                created_at: '2026-03-27T07:59:05.927Z'
              }
            ]
          };
        },
        release() {
          releaseCalls++;
        }
      };
    }
  };

  const resolver = new MatchIdentityResolver({
    getDbPool: () => pool,
    executeWithRetry: async (operation) => operation(),
    logger: { info() {}, warn() {}, error() {} },
    RepositoryError
  });

  const resolved = await resolver.resolveCanonicalFixtures([
    {
      match_id: '130_20252026_4694245',
      external_id: '5071062',
      season: '2025/2026',
      data_source: 'FotMob'
    }
  ]);

  assert.equal(resolved[0].match_id, '130_20252026_5025527');
  assert.equal(resolved[0].external_id, '5071062');
  assert.equal(resolved[0].data_source, 'FotMob');
  assert.equal(releaseCalls, 1);
});

test('MatchIdentityResolver.resolveCanonicalFixtures 在 data_source 缺失时必须 fail-fast', async () => {
  const resolver = new MatchIdentityResolver({
    getDbPool: () => ({ async connect() { throw new Error('should_not_connect'); } }),
    executeWithRetry: async (operation) => operation(),
    logger: { info() {}, warn() {}, error() {} },
    RepositoryError
  });

  await assert.rejects(
    resolver.resolveCanonicalFixtures([
      {
        match_id: '130_20252026_4694245',
        external_id: '5071062',
        season: '2025/2026',
        data_source: null
      }
    ]),
    (error) => {
      assert.equal(error instanceof RepositoryError, true);
      assert.equal(error.code, 'CANONICAL_IDENTITY_INVALID');
      assert.equal(error.details.field, 'data_source');
      return true;
    }
  );
});

test('MatchIdentityResolver.resolveCanonicalFixtures 在 external_id 缺失时必须 fail-fast', async () => {
  const resolver = new MatchIdentityResolver({
    getDbPool: () => ({ async connect() { throw new Error('should_not_connect'); } }),
    executeWithRetry: async (operation) => operation(),
    logger: { info() {}, warn() {}, error() {} },
    RepositoryError
  });

  await assert.rejects(
    resolver.resolveCanonicalFixtures([
      {
        match_id: '130_20252026_4694245',
        external_id: '',
        season: '2025/2026',
        data_source: 'FotMob'
      }
    ]),
    (error) => {
      assert.equal(error instanceof RepositoryError, true);
      assert.equal(error.code, 'CANONICAL_IDENTITY_INVALID');
      assert.equal(error.details.field, 'external_id');
      return true;
    }
  );
});
