'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');

const {
  FixtureRepository,
  RepositoryError
} = require('../../src/infrastructure/services/FixtureRepository');
const reconConfig = require('../../config/recon_config.json');
const { ReconMappingStore } = require('../../src/infrastructure/services/recon/ReconMappingStore');
const { ReconSchemaJanitor } = require('../../src/infrastructure/services/recon/ReconSchemaJanitor');

test('FixtureRepository.batchUpdateMatchPipelineStatus 应在竞争更新下只允许一个任务将 harvested 改为 RECON_MISMATCH', async () => {
  const state = {
    status: 'harvested',
    releaseCalls: 0
  };

  const pool = {
    async connect() {
      return {
        async query(sql, _params = []) {
          if (/^BEGIN|^COMMIT|^ROLLBACK/.test(sql.trim())) {
            return { rows: [], rowCount: 0 };
          }

          if (!sql.includes('UPDATE matches m')) {
            throw new Error(`unexpected_query:${sql}`);
          }

          await Promise.resolve();

          const [, nextStatus, expectedCurrentStatus] = _params;
          const allowedStatuses = Array.isArray(expectedCurrentStatus)
            ? expectedCurrentStatus
            : [expectedCurrentStatus];
          if (allowedStatuses.includes(state.status)) {
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
        async query(sql, _params = []) {
          if (/^BEGIN|^COMMIT|^ROLLBACK/.test(sql.trim())) {
            return { rows: [], rowCount: 0 };
          }

          capturedSql = sql;
          capturedParams = _params;
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
  assert.match(capturedSql, /COALESCE\(map\.is_evidence_only, FALSE\) = FALSE/);
  assert.deepEqual(capturedParams, [['m1'], 'RECON_MISMATCH', ['harvested'], '2024/2025']);
});

test('FixtureRepository.batchSaveMismatchEvidence 应将最佳候选证据写入 evidence_only 行', async () => {
  let capturedSql = '';
  let capturedParams = [];

  const pool = {
    async query() {
      return {
        rows: [
          { column_name: 'match_confidence' },
          { column_name: 'mapping_method' },
          { column_name: 'is_reversed' },
          { column_name: 'candidate_name' },
          { column_name: 'is_evidence_only' }
        ]
      };
    },
    async connect() {
      return {
        async query(sql, params = []) {
          const compactSql = sql.trim().replace(/\s+/g, ' ');

          if (/^BEGIN|^COMMIT|^ROLLBACK/.test(compactSql)) {
            return { rows: [], rowCount: 0 };
          }

          capturedSql = compactSql;
          capturedParams = params;
          return { rows: [{ match_id: params[0] }], rowCount: 1 };
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
  repository._mappingSchemaEnsured = true;

  const result = await repository.batchSaveMismatchEvidence([
    {
      match_id: '130_20252026_4694299',
      season: '2025/2026',
      league_name: 'MLS',
      home_team: 'Inter Miami CF',
      away_team: 'New York City FC',
      full_url: 'https://www.oddsportal.com/football/usa/mls/inter-miami-new-york-city-8hbZloRi/',
      candidate_name: 'Inter Miami CF vs New York City FC',
      match_confidence: 0.44,
      mapping_method: 'fuzzy'
    }
  ]);

  assert.equal(result.success, true);
  assert.equal(result.saved, 1);
  assert.match(capturedSql, /candidate_name/);
  assert.match(capturedSql, /is_evidence_only/);
  assert.match(capturedSql, /WHERE COALESCE\(matches_oddsportal_mapping\.is_evidence_only, FALSE\) = TRUE/);
  assert.equal(capturedParams[0], '130_20252026_4694299');
  assert.match(String(capturedParams[1]), /^~/);
  assert.equal(capturedParams[2], 'https://www.oddsportal.com/football/usa/mls/inter-miami-new-york-city-8hbZloRi/');
  assert.equal(capturedParams[8], 0.44);
  assert.equal(capturedParams[11], 'Inter Miami CF vs New York City FC');
  assert.equal(capturedParams[12], true);
});

test('FixtureRepository.batchSaveMismatchEvidence 在未显式传入 mapping_method 时应回退到 valid_method 白名单内的 unknown', async () => {
  let capturedParams = [];

  const pool = {
    async query() {
      return {
        rows: [
          { column_name: 'match_confidence' },
          { column_name: 'mapping_method' },
          { column_name: 'is_reversed' },
          { column_name: 'candidate_name' },
          { column_name: 'is_evidence_only' }
        ]
      };
    },
    async connect() {
      return {
        async query(sql, params = []) {
          const compactSql = sql.trim().replace(/\s+/g, ' ');

          if (/^BEGIN|^COMMIT|^ROLLBACK/.test(compactSql)) {
            return { rows: [], rowCount: 0 };
          }

          capturedParams = params;
          return { rows: [{ match_id: params[0] }], rowCount: 1 };
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
  repository._mappingSchemaEnsured = true;

  await repository.batchSaveMismatchEvidence([
    {
      match_id: 'mismatch-default-method',
      season: '2025/2026',
      league_name: 'MLS',
      home_team: 'Inter Miami CF',
      away_team: 'New York City FC',
      match_confidence: 0.31
    }
  ]);

  assert.equal(capturedParams[9], 'unknown');
});

test('FixtureRepository.replaceLeagueDictionaryEntries 应按联赛+赛季整表替换字典内容', async () => {
  const events = [];

  const pool = {
    async connect() {
      return {
        async query(sql, params = []) {
          const compactSql = sql.trim().replace(/\s+/g, ' ');
          events.push({ sql: compactSql, params });

          if (/^BEGIN|^COMMIT|^ROLLBACK/.test(compactSql)) {
            return { rows: [], rowCount: 0 };
          }

          return { rows: [], rowCount: 1 };
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
  repository._mappingSchemaEnsured = true;

  const result = await repository.replaceLeagueDictionaryEntries([
    {
      league_id: 140,
      season: '2025/2026',
      remote_name: 'Dep La Coruna',
      local_team_id: '9783'
    },
    {
      league_id: 140,
      season: '2025/2026',
      remote_name: 'Gijon',
      local_team_id: '9869'
    }
  ], {
    leagueId: 140,
    season: '2025/2026'
  });

  assert.equal(result.success, true);
  assert.equal(result.replacedLeagues, 1);
  assert.equal(result.inserted, 2);
  assert.match(events[1].sql, /DELETE FROM recon_league_dictionary/);
  assert.deepEqual(events[1].params, [140, '2025/2026']);
  assert.match(events[2].sql, /INSERT INTO recon_league_dictionary/);
  assert.deepEqual(events[2].params, [140, '2025/2026', 'Dep La Coruna', '9783']);
  assert.deepEqual(events[3].params, [140, '2025/2026', 'Gijon', '9869']);
});

test('FixtureRepository.getLeagueDictionaryEntries 应优先命中同赛季字典并补回 local_team_name', async () => {
  const pool = {
    async query(sql, params = []) {
      const compactSql = sql.trim().replace(/\s+/g, ' ');
      if (compactSql.startsWith('SELECT DISTINCT ON (LOWER(remote_name))')) {
        assert.deepEqual(params, [140, '2025/2026']);
        return {
          rows: [
            { league_id: 140, season: '2025/2026', remote_name: 'Dep La Coruna', local_team_id: '9783' },
            { league_id: 140, season: '', remote_name: 'Gijon', local_team_id: '9869' }
          ]
        };
      }

      throw new Error(`unexpected_query:${compactSql}`);
    }
  };

  const repository = new FixtureRepository({
    dbPool: pool,
    maxRetries: 1,
    logger: { info() {}, warn() {}, error() {} }
  });
  repository._mappingSchemaEnsured = true;
  repository.getLeagueTeamCatalog = async () => ([
    { team_id: '9783', team_name: 'Deportivo La Coruna' },
    { team_id: '9869', team_name: 'Sporting Gijon' }
  ]);

  const rows = await repository.getLeagueDictionaryEntries(140, { season: '2025/2026' });

  assert.deepEqual(rows, [
    {
      league_id: 140,
      season: '2025/2026',
      remote_name: 'Dep La Coruna',
      local_team_id: '9783',
      local_team_name: 'Deportivo La Coruna'
    },
    {
      league_id: 140,
      season: '',
      remote_name: 'Gijon',
      local_team_id: '9869',
      local_team_name: 'Sporting Gijon'
    }
  ]);
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

test('FixtureRepository.batchSaveOddsPortalMappings 在既有 hash 被错误绑到反向赛程时应自动重绑到更匹配的 match_id', async () => {
  const healLogs = [];
  const events = [];
  const statusByMatchId = new Map([
    ['47_20252026_4813728', 'RECON_LINKED'],
    ['47_20252026_4813435', 'harvested']
  ]);

  const existingMappingRow = {
    season: '2025/2026',
    oddsportal_hash: '2JX0U1gT',
    match_id: '47_20252026_4813728',
    full_url: 'https://www.oddsportal.com/football/england/premier-league/bournemouth-fulham-2JX0U1gT/',
    home_team: 'Fulham',
    away_team: 'AFC Bournemouth',
    match_confidence: 0.48,
    updated_at: '2026-03-27T05:34:32.308Z'
  };

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
        async query(sql, _params = []) {
          const compactSql = sql.trim().replace(/\s+/g, ' ');
          events.push(compactSql);

          if (/^BEGIN|^COMMIT|^ROLLBACK/.test(compactSql)) {
            return { rows: [], rowCount: 0 };
          }

          if (compactSql.includes('SELECT season, oddsportal_hash, match_id, full_url, home_team, away_team, match_confidence, updated_at')) {
            return { rows: [existingMappingRow] };
          }

          if (compactSql.includes('SELECT match_id, season, match_date, home_team, away_team, pipeline_status FROM matches')) {
            return {
              rows: [
                {
                  match_id: '47_20252026_4813728',
                  season: '2025/2026',
                  match_date: '2026-05-09T14:00:00.000Z',
                  home_team: 'Fulham',
                  away_team: 'AFC Bournemouth',
                  pipeline_status: statusByMatchId.get('47_20252026_4813728')
                },
                {
                  match_id: '47_20252026_4813435',
                  season: '2025/2026',
                  match_date: '2025-10-03T19:00:00.000Z',
                  home_team: 'AFC Bournemouth',
                  away_team: 'Fulham',
                  pipeline_status: statusByMatchId.get('47_20252026_4813435')
                }
              ]
            };
          }

          if (compactSql.startsWith('UPDATE matches_oddsportal_mapping')) {
            return { rows: [], rowCount: 1 };
          }

          if (compactSql.startsWith('UPDATE matches m')) {
            const [matchId, nextStatus, expectedCurrentStatus] = _params;
            const allowedStatuses = Array.isArray(expectedCurrentStatus)
              ? expectedCurrentStatus
              : expectedCurrentStatus
                ? [expectedCurrentStatus]
                : [];
            if (allowedStatuses.length > 0 && !allowedStatuses.includes(statusByMatchId.get(matchId))) {
              return { rows: [], rowCount: 0 };
            }
            statusByMatchId.set(matchId, nextStatus);
            return { rows: [], rowCount: 1 };
          }

          if (compactSql.startsWith('INSERT INTO matches_oddsportal_mapping')) {
            throw new Error('should_not_insert_when_conflict_is_healed');
          }

          throw new Error(`unexpected_query:${compactSql}`);
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
      warn(message, data) {
        healLogs.push({ message, data });
      },
      error() {}
    }
  });
  repository._mappingSchemaEnsured = true;

  const result = await repository.batchSaveOddsPortalMappings([
    {
      match_id: '47_20252026_4813435',
      oddsportal_hash: '2JX0U1gT',
      full_url: 'https://www.oddsportal.com/football/england/premier-league/bournemouth-fulham-2JX0U1gT/',
      season: '2025/2026',
      league_name: 'Premier League',
      home_team: 'AFC Bournemouth',
      away_team: 'Fulham',
      match_confidence: 0.91
    }
  ], {
    pipelineStatus: 'RECON_LINKED'
  });

  assert.equal(result.success, true);
  assert.equal(result.inserted, 0);
  assert.equal(result.updated, 1);
  assert.equal(statusByMatchId.get('47_20252026_4813728'), 'harvested');
  assert.equal(statusByMatchId.get('47_20252026_4813435'), 'RECON_LINKED');
  assert.equal(events.some((entry) => String(entry).startsWith('INSERT INTO matches_oddsportal_mapping')), false);

  const healLog = healLogs.find((entry) => /season\/hash 映射误绑/.test(entry.message));
  assert.ok(healLog);
  assert.equal(healLog.data.previous_match_id, '47_20252026_4813728');
  assert.equal(healLog.data.rebound_match_id, '47_20252026_4813435');
});

test('FixtureRepository.batchSaveOddsPortalMappings 在 preserve_linked_status 开启且新证据不足时必须保留既有 RECON_LINKED', async () => {
  const healLogs = [];
  const statusByMatchId = new Map([
    ['47_20252026_4813728', 'RECON_LINKED'],
    ['47_20252026_4813435', 'harvested']
  ]);

  const existingMappingRow = {
    season: '2025/2026',
    oddsportal_hash: '2JX0U1gT',
    match_id: '47_20252026_4813728',
    full_url: 'https://www.oddsportal.com/football/england/premier-league/bournemouth-fulham-2JX0U1gT/',
    home_team: 'Fulham',
    away_team: 'AFC Bournemouth',
    match_confidence: 0.88,
    updated_at: '2026-03-27T05:34:32.308Z'
  };

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
        async query(sql, _params = []) {
          const compactSql = sql.trim().replace(/\s+/g, ' ');

          if (/^BEGIN|^COMMIT|^ROLLBACK/.test(compactSql)) {
            return { rows: [], rowCount: 0 };
          }

          if (compactSql.includes('SELECT season, oddsportal_hash, match_id, full_url, home_team, away_team, match_confidence, updated_at')) {
            return { rows: [existingMappingRow] };
          }

          if (compactSql.includes('SELECT match_id, season, match_date, home_team, away_team, pipeline_status FROM matches')) {
            return {
              rows: [
                {
                  match_id: '47_20252026_4813728',
                  season: '2025/2026',
                  match_date: '2026-05-09T14:00:00.000Z',
                  home_team: 'Fulham',
                  away_team: 'AFC Bournemouth',
                  pipeline_status: statusByMatchId.get('47_20252026_4813728')
                },
                {
                  match_id: '47_20252026_4813435',
                  season: '2025/2026',
                  match_date: '2025-10-03T19:00:00.000Z',
                  home_team: 'AFC Bournemouth',
                  away_team: 'Fulham',
                  pipeline_status: statusByMatchId.get('47_20252026_4813435')
                }
              ]
            };
          }

          if (compactSql.startsWith('UPDATE matches_oddsportal_mapping')
            || compactSql.startsWith('UPDATE matches m')
            || compactSql.startsWith('INSERT INTO matches_oddsportal_mapping')) {
            throw new Error(`should_not_mutate_when_linked_status_is_preserved:${compactSql}:${JSON.stringify(_params)}`);
          }

          throw new Error(`unexpected_query:${compactSql}`);
        },
        release() {}
      };
    }
  };

  const repository = new FixtureRepository({
    dbPool: pool,
    maxRetries: 1,
    logger: {
      info() {},
      warn(message, data) {
        healLogs.push({ message, data });
      },
      error() {}
    }
  });
  repository._mappingSchemaEnsured = true;

  const result = await repository.batchSaveOddsPortalMappings([
    {
      match_id: '47_20252026_4813435',
      oddsportal_hash: '2JX0U1gT',
      full_url: 'https://www.oddsportal.com/football/england/premier-league/bournemouth-fulham-2JX0U1gT/',
      season: '2025/2026',
      league_name: 'Premier League',
      home_team: 'AFC Bournemouth',
      away_team: 'Fulham',
      match_confidence: 0.9
    }
  ], {
    pipelineStatus: 'RECON_LINKED',
    preserve_linked_status: true
  });

  assert.equal(result.success, true);
  assert.equal(result.inserted, 0);
  assert.equal(result.updated, 0);
  assert.equal(statusByMatchId.get('47_20252026_4813728'), 'RECON_LINKED');
  assert.equal(statusByMatchId.get('47_20252026_4813435'), 'harvested');

  const healLog = healLogs.find((entry) => /新证据不足以推翻既有 RECON_LINKED/.test(entry.message));
  assert.ok(healLog);
  assert.equal(healLog.data.existing_match_id, '47_20252026_4813728');
  assert.equal(healLog.data.incoming_match_id, '47_20252026_4813435');
  assert.equal(healLog.data.preserve_linked_status, true);
});

test('FixtureRepository.batchSaveOddsPortalMappings 在 preserve_linked_status 开启且 incoming 分数未超过 existing 时也必须跳过冲突而非整批失败', async () => {
  const healLogs = [];
  const statusByMatchId = new Map([
    ['130_20252026_4694406', 'RECON_LINKED'],
    ['130_20252026_4694299', 'harvested']
  ]);

  const existingMappingRow = {
    season: '2025/2026',
    oddsportal_hash: '8hbZloRi',
    match_id: '130_20252026_4694406',
    full_url: 'https://www.oddsportal.com/football/usa/mls/st-louis-city-seattle-sounders-8hbZloRi/',
    home_team: 'Seattle Sounders Fc',
    away_team: 'St Louis City',
    match_confidence: 0.82,
    updated_at: '2026-03-27T18:00:47.107Z'
  };

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
        async query(sql, _params = []) {
          const compactSql = sql.trim().replace(/\s+/g, ' ');

          if (/^BEGIN|^COMMIT|^ROLLBACK/.test(compactSql)) {
            return { rows: [], rowCount: 0 };
          }

          if (compactSql.includes('SELECT season, oddsportal_hash, match_id, full_url, home_team, away_team, match_confidence, updated_at')) {
            return { rows: [existingMappingRow] };
          }

          if (compactSql.includes('SELECT match_id, season, match_date, home_team, away_team, pipeline_status FROM matches')) {
            return {
              rows: [
                {
                  match_id: '130_20252026_4694406',
                  season: '2025/2026',
                  match_date: '2026-03-08T01:30:00.000Z',
                  home_team: 'St. Louis City',
                  away_team: 'Seattle Sounders FC',
                  pipeline_status: statusByMatchId.get('130_20252026_4694406')
                },
                {
                  match_id: '130_20252026_4694299',
                  season: '2025/2026',
                  match_date: '2025-03-16T00:30:00.000Z',
                  home_team: 'St Louis City',
                  away_team: 'Seattle Sounders Fc',
                  pipeline_status: statusByMatchId.get('130_20252026_4694299')
                }
              ]
            };
          }

          if (compactSql.startsWith('UPDATE matches_oddsportal_mapping')
            || compactSql.startsWith('UPDATE matches m')
            || compactSql.startsWith('INSERT INTO matches_oddsportal_mapping')) {
            throw new Error(`should_not_mutate_when_existing_link_must_win:${compactSql}:${JSON.stringify(_params)}`);
          }

          throw new Error(`unexpected_query:${compactSql}`);
        },
        release() {}
      };
    }
  };

  const repository = new FixtureRepository({
    dbPool: pool,
    maxRetries: 1,
    logger: {
      info() {},
      warn(message, data) {
        healLogs.push({ message, data });
      },
      error() {}
    }
  });
  repository._mappingSchemaEnsured = true;

  const result = await repository.batchSaveOddsPortalMappings([
    {
      match_id: '130_20252026_4694299',
      oddsportal_hash: '8hbZloRi',
      full_url: 'https://www.oddsportal.com/football/usa/mls/st-louis-city-seattle-sounders-8hbZloRi/',
      season: '2025/2026',
      league_name: 'MLS',
      home_team: 'St Louis City',
      away_team: 'Seattle Sounders Fc',
      match_confidence: 0.78
    }
  ], {
    pipelineStatus: 'RECON_LINKED',
    preserve_linked_status: true
  });

  assert.equal(result.success, true);
  assert.equal(result.inserted, 0);
  assert.equal(result.updated, 0);
  assert.equal(statusByMatchId.get('130_20252026_4694406'), 'RECON_LINKED');
  assert.equal(statusByMatchId.get('130_20252026_4694299'), 'harvested');

  const healLog = healLogs.find((entry) => /新证据不足以推翻既有 RECON_LINKED/.test(entry.message));
  assert.ok(healLog);
  assert.equal(healLog.data.existing_match_id, '130_20252026_4694406');
  assert.equal(healLog.data.incoming_match_id, '130_20252026_4694299');
  assert.equal(healLog.data.preserve_linked_status, true);
});

test('FixtureRepository.saveOddsPortalMapping 在 season/hash 冲突无法仲裁时必须强制覆盖既有映射并切换到新 match_id', async () => {
  const healLogs = [];
  const statusByMatchId = new Map([
    ['140_20252026_old', 'RECON_LINKED'],
    ['140_20252026_new', 'harvested']
  ]);

  const existingMappingRow = {
    season: '2025/2026',
    oddsportal_hash: 'force123',
    match_id: '140_20252026_old',
    full_url: 'https://www.oddsportal.com/football/spain/segunda-division/old-garbage-force123/',
    league_name: 'Segunda División',
    home_team: 'Old Garbage Home',
    away_team: 'Old Garbage Away',
    match_confidence: 0.11,
    updated_at: '2026-04-01T10:00:00.000Z'
  };

  const pool = {
    async query() {
      return {
        rows: [
          { column_name: 'match_confidence' },
          { column_name: 'mapping_method' },
          { column_name: 'is_reversed' },
          { column_name: 'candidate_name' },
          { column_name: 'is_evidence_only' }
        ]
      };
    },
    async connect() {
      return {
        async query(sql, params = []) {
          const compactSql = sql.trim().replace(/\s+/g, ' ');

          if (/^BEGIN|^COMMIT|^ROLLBACK/.test(compactSql)) {
            return { rows: [], rowCount: 0 };
          }

          if (compactSql.includes('SELECT season, oddsportal_hash, match_id, full_url, home_team, away_team, match_confidence, updated_at')) {
            return { rows: [existingMappingRow] };
          }

          if (compactSql.includes('SELECT match_id, season, match_date, home_team, away_team, pipeline_status FROM matches')) {
            return {
              rows: [
                {
                  match_id: '140_20252026_old',
                  season: '2025/2026',
                  match_date: '2025-09-01T19:00:00.000Z',
                  home_team: 'Old Garbage Home',
                  away_team: 'Old Garbage Away',
                  pipeline_status: statusByMatchId.get('140_20252026_old')
                },
                {
                  match_id: '140_20252026_new',
                  season: '2025/2026',
                  match_date: '2025-10-01T19:00:00.000Z',
                  home_team: 'Different Fixture Home',
                  away_team: 'Different Fixture Away',
                  pipeline_status: statusByMatchId.get('140_20252026_new')
                }
              ]
            };
          }

          if (compactSql.startsWith('DELETE FROM matches_oddsportal_mapping')) {
            return { rows: [], rowCount: 0 };
          }

          if (compactSql.startsWith('UPDATE matches_oddsportal_mapping')) {
            assert.equal(params[0], '140_20252026_new');
            assert.equal(params[3], 'Levante');
            assert.equal(params[4], 'Mirandes');
            return { rows: [{ match_id: '140_20252026_new' }], rowCount: 1 };
          }

          if (compactSql.startsWith('UPDATE matches m')) {
            const [matchId, nextStatus, expectedCurrentStatus] = params;
            const allowedStatuses = Array.isArray(expectedCurrentStatus)
              ? expectedCurrentStatus
              : expectedCurrentStatus
                ? [expectedCurrentStatus]
                : [];
            if (allowedStatuses.length > 0 && !allowedStatuses.includes(statusByMatchId.get(matchId))) {
              return { rows: [], rowCount: 0 };
            }
            statusByMatchId.set(matchId, nextStatus);
            return { rows: [], rowCount: 1 };
          }

          if (compactSql.startsWith('INSERT INTO matches_oddsportal_mapping')) {
            throw new Error('should_not_insert_when_force_overwrite_is_used');
          }

          throw new Error(`unexpected_query:${compactSql}`);
        },
        release() {}
      };
    }
  };

  const repository = new FixtureRepository({
    dbPool: pool,
    maxRetries: 1,
    logger: {
      info() {},
      warn(message, data) {
        healLogs.push({ message, data });
      },
      error() {}
    }
  });
  repository._mappingSchemaEnsured = true;

  const result = await repository.saveOddsPortalMapping({
    match_id: '140_20252026_new',
    oddsportal_hash: 'force123',
    full_url: 'https://www.oddsportal.com/football/spain/segunda-division/levante-mirandes-force123/',
    season: '2025/2026',
    league_name: 'Segunda División',
    home_team: 'Levante',
    away_team: 'Mirandes',
    match_confidence: 0.18,
    mapping_method: 'recon_matrix',
    status: 'pending'
  }, {
    pipelineStatus: 'RECON_LINKED'
  });

  assert.equal(result.success, true);
  assert.equal(result.wasInsert, false);
  assert.equal(result.updated, 1);
  assert.equal(statusByMatchId.get('140_20252026_old'), 'harvested');
  assert.equal(statusByMatchId.get('140_20252026_new'), 'RECON_LINKED');

  const healLog = healLogs.find((entry) => /SQL 强制覆盖/.test(entry.message));
  assert.ok(healLog);
  assert.equal(healLog.data.previous_match_id, '140_20252026_old');
  assert.equal(healLog.data.rebound_match_id, '140_20252026_new');
});

test('FixtureRepository.batchSaveOddsPortalMappings 在重绑命中 0 行时必须抛出 HASH_CONFLICT_REBIND_FAILED 并回滚事务', async () => {
  const statusByMatchId = new Map([
    ['47_20252026_4813728', 'RECON_LINKED'],
    ['47_20252026_4813435', 'harvested']
  ]);
  const events = [];

  const existingMappingRow = {
    season: '2025/2026',
    oddsportal_hash: '2JX0U1gT',
    match_id: '47_20252026_4813728',
    full_url: 'https://www.oddsportal.com/football/england/premier-league/bournemouth-fulham-2JX0U1gT/',
    home_team: 'Fulham',
    away_team: 'AFC Bournemouth',
    match_confidence: 0.48,
    updated_at: '2026-03-27T05:34:32.308Z'
  };

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
        async query(sql, _params = []) {
          const compactSql = sql.trim().replace(/\s+/g, ' ');
          events.push(compactSql);

          if (/^BEGIN|^COMMIT|^ROLLBACK/.test(compactSql)) {
            return { rows: [], rowCount: 0 };
          }

          if (compactSql.includes('SELECT season, oddsportal_hash, match_id, full_url, home_team, away_team, match_confidence, updated_at')) {
            return { rows: [existingMappingRow] };
          }

          if (compactSql.includes('SELECT match_id, season, match_date, home_team, away_team, pipeline_status FROM matches')) {
            return {
              rows: [
                {
                  match_id: '47_20252026_4813728',
                  season: '2025/2026',
                  match_date: '2026-05-09T14:00:00.000Z',
                  home_team: 'Fulham',
                  away_team: 'AFC Bournemouth',
                  pipeline_status: statusByMatchId.get('47_20252026_4813728')
                },
                {
                  match_id: '47_20252026_4813435',
                  season: '2025/2026',
                  match_date: '2025-10-03T19:00:00.000Z',
                  home_team: 'AFC Bournemouth',
                  away_team: 'Fulham',
                  pipeline_status: statusByMatchId.get('47_20252026_4813435')
                }
              ]
            };
          }

          if (compactSql.startsWith('UPDATE matches_oddsportal_mapping')) {
            return { rows: [], rowCount: 0 };
          }

          if (compactSql.startsWith('UPDATE matches m') || compactSql.startsWith('INSERT INTO matches_oddsportal_mapping')) {
            throw new Error('should_not_update_status_or_insert_when_rebind_confirmation_fails');
          }

          throw new Error(`unexpected_query:${compactSql}`);
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
    logger: { info() {}, warn() {}, error() {} }
  });
  repository._mappingSchemaEnsured = true;

  await assert.rejects(
    () => repository.batchSaveOddsPortalMappings([
      {
        match_id: '47_20252026_4813435',
        oddsportal_hash: '2JX0U1gT',
        full_url: 'https://www.oddsportal.com/football/england/premier-league/bournemouth-fulham-2JX0U1gT/',
        season: '2025/2026',
        league_name: 'Premier League',
        home_team: 'AFC Bournemouth',
        away_team: 'Fulham',
        match_confidence: 0.91
      }
    ], {
      pipelineStatus: 'RECON_LINKED'
    }),
    (error) => {
      assert.equal(error instanceof RepositoryError, true);
      assert.equal(error.code, 'HASH_CONFLICT_REBIND_FAILED');
      assert.equal(error.details.previous_match_id, '47_20252026_4813728');
      assert.equal(error.details.rebound_match_id, '47_20252026_4813435');
      return true;
    }
  );

  assert.equal(statusByMatchId.get('47_20252026_4813728'), 'RECON_LINKED');
  assert.equal(statusByMatchId.get('47_20252026_4813435'), 'harvested');
  assert.deepEqual(events.slice(-2), ['ROLLBACK', 'RELEASE']);
});

test('FixtureRepository.batchSaveOddsPortalMappings 在同场重复 ID 争抢同一 season/hash 时应保留较小 match_id 并将另一条标记 failed', async () => {
  const healLogs = [];
  const statusByMatchId = new Map([
    ['47_20252026_500001', 'RECON_LINKED'],
    ['47_20252026_500002', 'harvested']
  ]);

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
        async query(sql, params = []) {
          const compactSql = sql.trim().replace(/\s+/g, ' ');

          if (/^BEGIN|^COMMIT|^ROLLBACK/.test(compactSql)) {
            return { rows: [], rowCount: 0 };
          }

          if (compactSql.includes('SELECT season, oddsportal_hash, match_id, full_url, home_team, away_team, match_confidence, updated_at')) {
            return {
              rows: [{
                season: '2025/2026',
                oddsportal_hash: 'dup-fixture',
                match_id: '47_20252026_500001',
                full_url: 'https://www.oddsportal.com/football/england/premier-league/arsenal-chelsea-dup-fixture/',
                home_team: 'Arsenal',
                away_team: 'Chelsea',
                match_confidence: 0.82,
                updated_at: '2026-03-29T12:00:00.000Z'
              }]
            };
          }

          if (compactSql.includes('SELECT match_id, season, match_date, home_team, away_team, pipeline_status FROM matches')) {
            return {
              rows: [
                {
                  match_id: '47_20252026_500001',
                  season: '2025/2026',
                  match_date: '2025-08-15T19:00:00.000Z',
                  home_team: 'Arsenal',
                  away_team: 'Chelsea',
                  pipeline_status: statusByMatchId.get('47_20252026_500001')
                },
                {
                  match_id: '47_20252026_500002',
                  season: '2025/2026',
                  match_date: '2025-08-15T20:00:00.000Z',
                  home_team: 'Arsenal FC',
                  away_team: 'Chelsea FC',
                  pipeline_status: statusByMatchId.get('47_20252026_500002')
                }
              ]
            };
          }

          if (compactSql.startsWith('UPDATE matches m')) {
            const [matchId, nextStatus, expectedCurrentStatus] = params;
            const allowedStatuses = Array.isArray(expectedCurrentStatus)
              ? expectedCurrentStatus
              : expectedCurrentStatus
                ? [expectedCurrentStatus]
                : [];
            if (allowedStatuses.length > 0 && !allowedStatuses.includes(statusByMatchId.get(matchId))) {
              return { rows: [], rowCount: 0 };
            }
            statusByMatchId.set(matchId, nextStatus);
            return { rows: [], rowCount: 1 };
          }

          if (compactSql.startsWith('UPDATE matches_oddsportal_mapping') || compactSql.startsWith('INSERT INTO matches_oddsportal_mapping')) {
            throw new Error('should_not_rebind_or_insert_when_existing_duplicate_wins');
          }

          throw new Error(`unexpected_query:${compactSql}`);
        },
        release() {}
      };
    }
  };

  const repository = new FixtureRepository({
    dbPool: pool,
    maxRetries: 1,
    logger: {
      info() {},
      warn(message, data) {
        healLogs.push({ message, data });
      },
      error() {}
    }
  });
  repository._mappingSchemaEnsured = true;

  const result = await repository.batchSaveOddsPortalMappings([
    {
      match_id: '47_20252026_500002',
      oddsportal_hash: 'dup-fixture',
      full_url: 'https://www.oddsportal.com/football/england/premier-league/arsenal-chelsea-dup-fixture/',
      season: '2025/2026',
      league_name: 'Premier League',
      home_team: 'Arsenal',
      away_team: 'Chelsea'
    }
  ], {
    pipelineStatus: 'RECON_LINKED'
  });

  assert.equal(result.success, true);
  assert.equal(result.inserted, 0);
  assert.equal(result.updated, 0);
  assert.equal(statusByMatchId.get('47_20252026_500001'), 'RECON_LINKED');
  assert.equal(statusByMatchId.get('47_20252026_500002'), 'failed');

  const healLog = healLogs.find((entry) => /同场重复 ID/.test(entry.message));
  assert.ok(healLog);
  assert.equal(healLog.data.winner_match_id, '47_20252026_500001');
  assert.equal(healLog.data.loser_match_id, '47_20252026_500002');
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

      if (sql.includes('DROP CONSTRAINT IF EXISTS valid_method')) {
        return { rows: [], rowCount: 0 };
      }

      if (sql.includes('ADD CONSTRAINT valid_method CHECK')) {
        return { rows: [], rowCount: 0 };
      }

      if (sql.includes('CREATE TABLE IF NOT EXISTS recon_league_dictionary')) {
        return { rows: [], rowCount: 0 };
      }

      if (sql.includes('ALTER TABLE recon_league_dictionary')) {
        return { rows: [], rowCount: 0 };
      }

      if (sql.includes('DROP INDEX IF EXISTS idx_recon_league_dictionary_unique')) {
        return { rows: [], rowCount: 0 };
      }

      if (sql.includes('CREATE UNIQUE INDEX IF NOT EXISTS idx_recon_league_dictionary_unique')) {
        return { rows: [], rowCount: 0 };
      }

      if (sql.includes('DROP INDEX IF EXISTS idx_recon_league_dictionary_team')) {
        return { rows: [], rowCount: 0 };
      }

      if (sql.includes('CREATE INDEX IF NOT EXISTS idx_recon_league_dictionary_team')) {
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
          ],
          repairedCount: 1
        };
      },
      async repairLinkedStatusesWithoutMapping() {
        migrationCalls.push('repair');
        return { repairedCount: 0, matchIds: [] };
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
  assert.deepEqual(migrationCalls, ['find', 'dedupe', 'repair']);
  assert.equal(repository._mappingHashUniquenessEnsured, true);

  const healLog = healLogs.find((entry) => /\[HEAL\]/.test(entry.message));
  assert.ok(healLog);
  assert.match(healLog.message, /自动清理了 3 条脏数据以固化唯一索引/);
  assert.equal(healLog.data.reason, 'create_index_conflict');
  assert.equal(healLog.data.duplicate_groups, 2);
  assert.equal(healLog.data.repaired_linked_count, 1);
});

test('FixtureRepository.ensureOddsPortalMappingSchema 在存在 RECON_LINKED 残留时应自动回退为 harvested', async () => {
  const healLogs = [];
  const migrationCalls = [];

  const pool = {
    async query(sql) {
      if (sql.includes('ALTER TABLE matches_oddsportal_mapping')) {
        return { rows: [], rowCount: 0 };
      }

      if (sql.includes('DROP CONSTRAINT IF EXISTS valid_method')) {
        return { rows: [], rowCount: 0 };
      }

      if (sql.includes('ADD CONSTRAINT valid_method CHECK')) {
        return { rows: [], rowCount: 0 };
      }

      if (sql.includes('CREATE TABLE IF NOT EXISTS recon_league_dictionary')) {
        return { rows: [], rowCount: 0 };
      }

      if (sql.includes('ALTER TABLE recon_league_dictionary')) {
        return { rows: [], rowCount: 0 };
      }

      if (sql.includes('DROP INDEX IF EXISTS idx_recon_league_dictionary_unique')) {
        return { rows: [], rowCount: 0 };
      }

      if (sql.includes('CREATE UNIQUE INDEX IF NOT EXISTS idx_recon_league_dictionary_unique')) {
        return { rows: [], rowCount: 0 };
      }

      if (sql.includes('DROP INDEX IF EXISTS idx_recon_league_dictionary_team')) {
        return { rows: [], rowCount: 0 };
      }

      if (sql.includes('CREATE INDEX IF NOT EXISTS idx_recon_league_dictionary_team')) {
        return { rows: [], rowCount: 0 };
      }

      if (sql.includes('CREATE UNIQUE INDEX IF NOT EXISTS idx_mapping_season_hash_unique')) {
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
        return { deletedCount: 0, groupCount: 0, groups: [], repairedCount: 0 };
      },
      async repairLinkedStatusesWithoutMapping() {
        migrationCalls.push('repair');
        return {
          repairedCount: 2,
          matchIds: ['m1', 'm2']
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

  assert.deepEqual(migrationCalls, ['find', 'repair']);

  const healLog = healLogs.find((entry) => /RECON_LINKED 残留/.test(entry.message));
  assert.ok(healLog);
  assert.match(healLog.message, /已自动回退为 harvested/);
  assert.equal(healLog.data.repaired_count, 2);
  assert.deepEqual(healLog.data.sample_match_ids, ['m1', 'm2']);
});

test('FixtureRepository 应默认把 conflict arbiter 阈值从 recon_config.json 注入仓储子服务', () => {
  const repository = new FixtureRepository({
    dbPool: { async query() {} },
    maxRetries: 1,
    logger: { info() {}, warn() {}, error() {} }
  });

  assert.equal(
    repository.conflictArbiter.sameFixtureThreshold,
    reconConfig.repository.conflict_arbiter.same_fixture_threshold
  );
  assert.equal(
    repository.conflictArbiter.sameFixtureWindowMs,
    reconConfig.repository.conflict_arbiter.same_fixture_window_ms
  );
  assert.deepEqual(
    repository.matchCanonicalJanitor.identityInactiveStatuses,
    reconConfig.repository.identity_inactive_statuses
  );
});

test('ReconMappingStore constructor 在核心依赖缺失时必须 fail-fast', () => {
  assert.throws(
    () => new ReconMappingStore({}),
    /ReconMappingStore.*getDbPool/
  );
});

test('ReconSchemaJanitor constructor 在核心依赖缺失时必须 fail-fast', () => {
  assert.throws(
    () => new ReconSchemaJanitor({}),
    /ReconSchemaJanitor.*getDbPool/
  );
});

test('FixtureRepository.persist 应在入库前复用 canonical match_id，避免按同一 provider 原始 ID 重复插入', async () => {
  let capturedBatch = null;

  const repository = new FixtureRepository({
    dbPool: { async query() {}, async connect() { return { release() {} }; } },
    maxRetries: 1,
    logger: { info() {}, warn() {}, error() {} },
    matchIdentityResolver: {
      async resolveCanonicalFixtures(fixtures) {
        return fixtures.map((fixture) => ({
          ...fixture,
          match_id: '130_20252026_5025527'
        }));
      }
    }
  });

  repository.init = async () => {};
  repository._persistBatch = async (batch) => {
    capturedBatch = batch;
    return { inserted: 0, updated: batch.length };
  };

  const result = await repository.persist([
    {
      match_id: '130_20252026_4694245',
      external_id: '5071062',
      league_name: 'MLS',
      season: '2025/2026',
      home_team: 'Inter Miami Cf',
      away_team: 'New York City Fc',
      match_date: '2026-03-22T17:00:00.000Z',
      status: 'finished',
      is_finished: true,
      data_source: 'FotMob'
    }
  ]);

  assert.equal(result.inserted, 0);
  assert.equal(result.updated, 1);
  assert.equal(capturedBatch.length, 1);
  assert.equal(capturedBatch[0].match_id, '130_20252026_5025527');
  assert.equal(capturedBatch[0].external_id, '5071062');
});

test('FixtureRepository.persist 在 data_source 缺失时必须 fail-fast，而不是静默回退到默认 provider', async () => {
  const repository = new FixtureRepository({
    dbPool: { async query() {}, async connect() { return { release() {} }; } },
    maxRetries: 1,
    logger: { info() {}, warn() {}, error() {} },
    matchIdentityResolver: {
      async resolveCanonicalFixtures(fixtures) {
        return fixtures;
      }
    }
  });

  repository.init = async () => {};

  await assert.rejects(
    repository.persist([
      {
        match_id: '130_20252026_4694245',
        external_id: '5071062',
        league_name: 'MLS',
        season: '2025/2026',
        home_team: 'Inter Miami Cf',
        away_team: 'New York City Fc',
        match_date: '2026-03-22T17:00:00.000Z',
        status: 'finished',
        is_finished: true,
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

test('FixtureRepository.persist 应在 L1 入库前统一中超别名与缩写大小写', async () => {
  let capturedBatch = null;

  const repository = new FixtureRepository({
    dbPool: { async query() {}, async connect() { return { release() {} }; } },
    maxRetries: 1,
    logger: { info() {}, warn() {}, error() {} },
    matchIdentityResolver: {
      async resolveCanonicalFixtures(fixtures) {
        return fixtures;
      }
    }
  });

  repository.init = async () => {};
  repository._persistBatch = async (batch) => {
    capturedBatch = batch;
    return { inserted: batch.length, updated: 0 };
  };

  await repository.persist([
    {
      match_id: '120_20252026_4723000',
      external_id: '4723000',
      league_name: 'CSL',
      season: '2025/2026',
      home_team: 'Henan Fc',
      away_team: 'Shenzhen Peng City',
      match_date: '2025-09-01T12:00:00.000Z',
      status: 'scheduled',
      is_finished: false,
      data_source: 'FotMob'
    }
  ]);

  assert.equal(capturedBatch.length, 1);
  assert.equal(capturedBatch[0].home_team, 'Henan Songshan Longmen');
  assert.equal(capturedBatch[0].away_team, 'Shenzhen Xinpengcheng');
});

test('FixtureRepository.getReconEligibleMatches 开启 allowMismatchRetry 时应同时捞取 harvested 与 RECON_MISMATCH', async () => {
  let capturedSql = '';
  let capturedParams = [];

  const pool = {
    async connect() {
      return {
        async query(sql, params = []) {
          capturedSql = sql;
          capturedParams = params;
          return { rows: [], rowCount: 0 };
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

  await repository.getReconEligibleMatches('2025/2026', 'Premier League', {
    allowMismatchRetry: true,
    limit: 5
  });

  assert.match(capturedSql, /m\.pipeline_status = ANY\(\$3::text\[\]\)/);
  assert.match(capturedSql, /COALESCE\(map\.is_evidence_only, FALSE\) = FALSE/);
  assert.match(capturedSql, /LIMIT \$4/);
  assert.deepEqual(capturedParams, [
    'Premier League',
    '2025/2026',
    ['harvested', 'RECON_MISMATCH'],
    5
  ]);
});
