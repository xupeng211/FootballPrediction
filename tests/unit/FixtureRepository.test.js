'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');

const {
  FixtureRepository,
  RepositoryError
} = require('../../src/infrastructure/services/FixtureRepository');

test('FixtureRepository.batchUpdateMatchPipelineStatus 应在竞争更新下只允许一个任务将 harvested 改为 RECON_MISMATCH', async () => {
  const state = {
    status: 'harvested',
    releaseCalls: 0
  };

  const pool = {
    async connect() {
      return {
        async query(sql, params = []) {
          if (/^BEGIN|^COMMIT|^ROLLBACK/.test(sql.trim())) {
            return { rows: [], rowCount: 0 };
          }

          if (!sql.includes('UPDATE matches m')) {
            throw new Error(`unexpected_query:${sql}`);
          }

          await Promise.resolve();

          const [, nextStatus, expectedCurrentStatus] = params;
          if (state.status === expectedCurrentStatus) {
            state.status = nextStatus;
            return { rowCount: 1 };
          }

          return { rowCount: 0 };
        },
        release() {
          state.releaseCalls++;
        }
      };
    }
  };

  const repository = new FixtureRepository({
    dbPool: pool,
    maxRetries: 1,
    logger: { info() {}, warn() {}, error() {} }
  });

  const [first, second] = await Promise.all([
    repository.batchUpdateMatchPipelineStatus(['m1'], 'RECON_MISMATCH', {
      season: '2024/2025',
      expectedCurrentStatus: 'harvested'
    }),
    repository.batchUpdateMatchPipelineStatus(['m1'], 'RECON_MISMATCH', {
      season: '2024/2025',
      expectedCurrentStatus: 'harvested'
    })
  ]);

  assert.deepEqual(
    [first.updated, second.updated].sort((left, right) => left - right),
    [0, 1]
  );
  assert.equal(state.status, 'RECON_MISMATCH');
  assert.equal(state.releaseCalls, 2);
});

test('FixtureRepository.batchUpdateMatchPipelineStatus 在同赛季已存在 mapping 时必须拒绝写入 RECON_MISMATCH', async () => {
  let capturedSql = '';
  let capturedParams = [];

  const pool = {
    async connect() {
      return {
        async query(sql, params = []) {
          if (/^BEGIN|^COMMIT|^ROLLBACK/.test(sql.trim())) {
            return { rows: [], rowCount: 0 };
          }

          capturedSql = sql;
          capturedParams = params;
          return { rowCount: 0 };
        },
        release() {}
      };
    }
  };

  const repository = new FixtureRepository({
    dbPool: pool,
    maxRetries: 1,
    logger: { info() {}, warn() {}, error() {} }
  });

  const result = await repository.batchUpdateMatchPipelineStatus(['m1'], 'RECON_MISMATCH', {
    season: '2024/2025',
    expectedCurrentStatus: 'harvested'
  });

  assert.equal(result.updated, 0);
  assert.match(capturedSql, /NOT EXISTS/);
  assert.match(capturedSql, /map\.season = \$4/);
  assert.deepEqual(capturedParams, [['m1'], 'RECON_MISMATCH', 'harvested', '2024/2025']);
});

test('FixtureRepository._executeWithRetry 应在 30 秒窗口内持续重试并支持数据库自动恢复', async () => {
  let now = 0;
  let attempt = 0;
  const sleepCalls = [];

  const repository = new FixtureRepository({
    dbPool: { async query() {} },
    maxRetries: 10,
    retryDelayMs: 5000,
    maxRetryWindowMs: 30000,
    retryBackoffMultiplier: 0,
    now: () => now,
    sleep: async (ms) => {
      sleepCalls.push(ms);
      now += ms;
    },
    logger: { info() {}, warn() {}, error() {} }
  });

  const result = await repository._executeWithRetry(async () => {
    attempt++;
    if (attempt <= 6) {
      throw new Error('db_temporarily_unavailable');
    }
    return { ok: true };
  }, 'retry_window_probe');

  assert.deepEqual(result, { ok: true });
  assert.equal(attempt, 7);
  assert.equal(sleepCalls.length, 6);
  assert.equal(sleepCalls.reduce((sum, value) => sum + value, 0), 30000);
});

test('FixtureRepository.batchSaveOddsPortalMappings 在两个 match_id 争抢同一 season/hash 时必须拒绝写入', async () => {
  const conflictLogs = [];
  const events = [];

  const pool = {
    async query() {
      return {
        rows: [
          { column_name: 'match_confidence' },
          { column_name: 'mapping_method' },
          { column_name: 'is_reversed' }
        ]
      };
    },
    async connect() {
      return {
        async query(sql) {
          const normalized = sql.trim().split(/\s+/).slice(0, 4).join(' ');
          events.push(normalized);

          if (/^BEGIN|^COMMIT|^ROLLBACK/.test(sql.trim())) {
            return { rows: [], rowCount: 0 };
          }

          if (sql.includes('SELECT season, oddsportal_hash')) {
            return { rows: [] };
          }

          throw new Error(`unexpected_query:${sql}`);
        },
        release() {
          events.push('RELEASE');
        }
      };
    }
  };

  const repository = new FixtureRepository({
    dbPool: pool,
    maxRetries: 1,
    logger: {
      info() {},
      warn() {},
      error(message, data) {
        conflictLogs.push({ message, data });
      }
    }
  });

  await assert.rejects(
    () => repository.batchSaveOddsPortalMappings([
      {
        match_id: 'm1',
        oddsportal_hash: 'samehash',
        full_url: 'https://example.com/1',
        season: '2024/2025',
        league_name: 'Bundesliga',
        home_team: 'A',
        away_team: 'B'
      },
      {
        match_id: 'm2',
        oddsportal_hash: 'samehash',
        full_url: 'https://example.com/2',
        season: '2024/2025',
        league_name: 'Bundesliga',
        home_team: 'C',
        away_team: 'D'
      }
    ]),
    (error) => {
      assert.equal(error instanceof RepositoryError, true);
      assert.equal(error.code, 'HASH_CONFLICT');
      assert.deepEqual(error.details, {
        season: '2024/2025',
        oddsportal_hash: 'samehash',
        incoming_match_ids: ['m1', 'm2']
      });
      return true;
    }
  );

  assert.deepEqual(events, ['BEGIN', 'ROLLBACK', 'RELEASE']);
  assert.equal(conflictLogs.length, 1);
  assert.match(conflictLogs[0].message, /批内 hash 冲突/);
});

test('FixtureRepository.ensureOddsPortalMappingSchema 在历史 hash 冲突导致建索引失败时应自动清理并重试', async () => {
  const healLogs = [];
  let createIndexAttempts = 0;
  const migrationCalls = [];

  const pool = {
    async query(sql) {
      if (sql.includes('ALTER TABLE matches_oddsportal_mapping')) {
        return { rows: [], rowCount: 0 };
      }

      if (sql.includes('CREATE UNIQUE INDEX IF NOT EXISTS idx_mapping_season_hash_unique')) {
        createIndexAttempts++;
        if (createIndexAttempts === 1) {
          const error = new Error('could not create unique index "idx_mapping_season_hash_unique"');
          error.code = '23505';
          throw error;
        }
        return { rows: [], rowCount: 0 };
      }

      throw new Error(`unexpected_query:${sql}`);
    }
  };

  const repository = new FixtureRepository({
    dbPool: pool,
    maxRetries: 1,
    mappingMigration: {
      async findDuplicateSeasonHashGroups() {
        migrationCalls.push('find');
        return [];
      },
      async dedupeMappings() {
        migrationCalls.push('dedupe');
        return {
          deletedCount: 3,
          groupCount: 2,
          groups: [
            {
              season: '2024/2025',
              oddsportal_hash: 'dup-a',
              kept_match_id: 'keep-a',
              removed_match_ids: ['drop-a']
            }
          ]
        };
      }
    },
    logger: {
      info() {},
      warn(message, data) {
        healLogs.push({ message, data });
      },
      error() {}
    }
  });

  await repository.ensureOddsPortalMappingSchema();

  assert.equal(createIndexAttempts, 2);
  assert.deepEqual(migrationCalls, ['find', 'dedupe']);
  assert.equal(repository._mappingHashUniquenessEnsured, true);

  const healLog = healLogs.find((entry) => /\[HEAL\]/.test(entry.message));
  assert.ok(healLog);
  assert.match(healLog.message, /自动清理了 3 条脏数据以固化唯一索引/);
  assert.equal(healLog.data.reason, 'create_index_conflict');
  assert.equal(healLog.data.duplicate_groups, 2);
});
