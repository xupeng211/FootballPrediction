'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');

const { MatchCanonicalJanitor } = require('../../src/infrastructure/services/recon/MatchCanonicalJanitor');
const { RepositoryError } = require('../../src/infrastructure/services/FixtureRepository');

test('MatchCanonicalJanitor.consolidateDuplicateGroups 应收敛重复实体并把 mapping 重绑到赢家', async () => {
  const logs = [];
  const state = {
    matches: new Map([
      ['130_20252026_5025527', {
        match_id: '130_20252026_5025527',
        external_id: '5025527',
        league_name: 'MLS',
        season: '2025/2026',
        home_team: 'Inter Miami Cf',
        away_team: 'New York City Fc',
        match_date: '2025-11-29T23:00:00.000Z',
        status: 'finished',
        data_source: 'FotMob',
        pipeline_status: 'RECON_LINKED',
        created_at: '2026-03-27T07:59:05.995Z',
        updated_at: '2026-03-27T18:00:47.184Z'
      }],
      ['130_20252026_4694245', {
        match_id: '130_20252026_4694245',
        external_id: '4694245',
        league_name: 'MLS',
        season: '2025/2026',
        home_team: 'Inter Miami Cf',
        away_team: 'New York City Fc',
        match_date: '2025-02-23T00:30:00.000Z',
        status: 'finished',
        data_source: 'FotMob',
        pipeline_status: 'harvested',
        created_at: '2026-03-27T07:59:05.927Z',
        updated_at: '2026-03-29T04:24:40.198Z'
      }]
    ]),
    rawRows: new Map([
      ['130_20252026_5025527', {
        raw_match_id: '5071062',
        raw_match_time: '2026-03-22T17:00:00.000Z',
        raw_home_team: 'New York City FC',
        raw_away_team: 'Inter Miami CF',
        raw_table_external_id: '5025527',
        collected_at: '2026-03-27T09:13:23.956Z'
      }],
      ['130_20252026_4694245', {
        raw_match_id: '5071062',
        raw_match_time: '2026-03-22T17:00:00.000Z',
        raw_home_team: 'New York City FC',
        raw_away_team: 'Inter Miami CF',
        raw_table_external_id: '4694245',
        collected_at: '2026-03-27T08:45:51.835Z'
      }]
    ]),
    mappings: [
      {
        match_id: '130_20252026_4694245',
        season: '2025/2026',
        oddsportal_hash: 'xOjdHR6C',
        full_url: 'https://www.oddsportal.com/football/usa/mls/new-york-city-inter-miami-xOjdHR6C/',
        home_team: 'New York City FC',
        away_team: 'Inter Miami CF',
        status: 'pending',
        created_at: '2026-03-29T12:00:00.000Z',
        updated_at: '2026-03-29T12:05:00.000Z'
      }
    ],
    releaseCalls: 0,
    commitCompleted: false
  };

  const pool = {
    async connect() {
      return {
        async query(sql, params = []) {
          const compact = sql.trim().replace(/\s+/g, ' ');

          if (compact === 'BEGIN') {
            state.commitCompleted = false;
            return { rows: [], rowCount: 0 };
          }

          if (compact === 'COMMIT') {
            state.commitCompleted = true;
            return { rows: [], rowCount: 0 };
          }

          if (compact === 'ROLLBACK') {
            return { rows: [], rowCount: 0 };
          }

          if (compact.includes('WITH grouped AS')) {
            return {
              rows: [{
                season: '2025/2026',
                league_name: 'MLS',
                source_provider: 'FotMob',
                raw_match_id: '5071062',
                duplicate_count: 2,
                match_ids: ['130_20252026_4694245', '130_20252026_5025527']
              }]
            };
          }

          if (compact.includes('GROUP BY m.season, m.data_source, m.external_id')) {
            return { rows: [] };
          }

          if (compact.includes('FROM matches m JOIN raw_match_data r')) {
            return {
              rows: params[0].map((matchId) => {
                const matchRow = state.matches.get(matchId);
                const rawRow = state.rawRows.get(matchId);
                return {
                  ...matchRow,
                  ...rawRow
                };
              })
            };
          }

          if (compact.includes('FROM matches_oddsportal_mapping')) {
            return {
              rows: state.mappings
                .filter((row) => params[0].includes(row.match_id))
                .map((row) => ({ ...row }))
            };
          }

          if (compact.startsWith('UPDATE matches_oddsportal_mapping SET match_id = $1')) {
            const [winnerId, season, hash, oldMatchId] = params;
            const mapping = state.mappings.find((row) =>
              row.match_id === oldMatchId && row.season === season && row.oddsportal_hash === hash
            );
            if (!mapping) {
              return { rows: [], rowCount: 0 };
            }
            mapping.match_id = winnerId;
            return { rows: [], rowCount: 1 };
          }

          if (compact.startsWith('DELETE FROM matches_oddsportal_mapping')) {
            const loserIds = new Set(params[0]);
            const before = state.mappings.length;
            state.mappings = state.mappings.filter((row) => !loserIds.has(row.match_id));
            return { rows: [], rowCount: before - state.mappings.length };
          }

          if (compact.startsWith('UPDATE matches SET external_id = $2')) {
            const [winnerId, externalId, homeTeam, awayTeam, matchTime, pipelineStatus] = params;
            const winner = state.matches.get(winnerId);
            winner.external_id = externalId;
            winner.home_team = homeTeam;
            winner.away_team = awayTeam;
            winner.match_date = matchTime;
            winner.pipeline_status = pipelineStatus;
            return { rows: [], rowCount: 1 };
          }

          if (compact.startsWith("UPDATE matches SET pipeline_status = 'failed'")) {
            for (const loserId of params[0]) {
              const loser = state.matches.get(loserId);
              loser.pipeline_status = 'failed';
            }
            return { rows: [], rowCount: params[0].length };
          }

          if (compact.startsWith('CREATE UNIQUE INDEX IF NOT EXISTS idx_matches_season_source_external_active_unique')) {
            return { rows: [], rowCount: 0 };
          }

          throw new Error(`unexpected_query:${compact}`);
        },
        release() {
          state.releaseCalls++;
        }
      };
    }
  };

  const janitor = new MatchCanonicalJanitor({
    getDbPool: () => pool,
    executeWithRetry: async (operation) => operation(),
    logger: {
      info() {},
          warn(message, data) {
        logs.push({ message, data, commitCompleted: state.commitCompleted });
          },
          error() {}
        },
    RepositoryError,
    identityInactiveStatuses: ['failed', 'archived', 'duplicate', 'merged']
  });

  const result = await janitor.consolidateDuplicateGroups({
    season: '2025/2026',
    sourceProvider: 'FotMob'
  });

  assert.equal(result.duplicate_groups, 1);
  assert.equal(result.winners_updated, 1);
  assert.equal(result.losers_failed, 1);
  assert.equal(result.mappings_rebound, 1);
  assert.equal(state.matches.get('130_20252026_5025527').external_id, '5071062');
  assert.equal(state.matches.get('130_20252026_5025527').home_team, 'New York City FC');
  assert.equal(state.matches.get('130_20252026_5025527').away_team, 'Inter Miami CF');
  assert.equal(state.matches.get('130_20252026_5025527').match_date, '2026-03-22T17:00:00.000Z');
  assert.equal(state.matches.get('130_20252026_5025527').pipeline_status, 'RECON_LINKED');
  assert.equal(state.matches.get('130_20252026_4694245').pipeline_status, 'failed');
  assert.equal(state.mappings.length, 1);
  assert.equal(state.mappings[0].match_id, '130_20252026_5025527');
  assert.equal(state.releaseCalls, 1);
  const healLog = logs.find((entry) => /Canonical identity 已收敛重复实体/.test(entry.message));
  assert.ok(healLog);
  assert.equal(healLog.commitCompleted, true);
  assert.equal(healLog.data.decision_reason, 'Winner has RECON_LINKED status');
  assert.equal(healLog.data.snapshot.winner_before.match_id, '130_20252026_5025527');
  assert.deepEqual(healLog.data.snapshot.losers_before.map((row) => row.match_id), ['130_20252026_4694245']);
});

test('MatchCanonicalJanitor.ensureSourceIdentityUniquenessIndex 应先自动收敛 exact external_id 重复，再创建唯一索引', async () => {
  const state = {
    matches: new Map([
      ['87_20252026_4837216', {
        match_id: '87_20252026_4837216',
        external_id: '5173359',
        league_name: 'La Liga',
        season: '2025/2026',
        home_team: 'Real Sociedad',
        away_team: 'Athletic Club',
        match_date: '2026-03-04T20:00:00.000Z',
        status: 'finished',
        data_source: 'FotMob',
        pipeline_status: 'RECON_MISMATCH',
        created_at: '2026-03-26T10:00:00.000Z',
        updated_at: '2026-03-29T00:00:00.000Z'
      }],
      ['138_20252026_5173359', {
        match_id: '138_20252026_5173359',
        external_id: '5173359',
        league_name: 'Copa del Rey',
        season: '2025/2026',
        home_team: 'Real Sociedad',
        away_team: 'Athletic Club',
        match_date: '2026-03-04T20:00:00.000Z',
        status: 'finished',
        data_source: 'FotMob',
        pipeline_status: 'RECON_LINKED',
        created_at: '2026-03-26T11:00:00.000Z',
        updated_at: '2026-03-29T00:10:00.000Z'
      }]
    ]),
    releaseCalls: 0,
    indexCreated: false
  };

  const pool = {
    async connect() {
      return {
        async query(sql, params = []) {
          const compact = sql.trim().replace(/\s+/g, ' ');

          if (/^BEGIN|^COMMIT|^ROLLBACK/.test(compact)) {
            return { rows: [], rowCount: 0 };
          }

          if (compact.includes('GROUP BY m.season, m.data_source, m.external_id')) {
            return {
              rows: [{
                season: '2025/2026',
                source_provider: 'FotMob',
                external_id: '5173359',
                duplicate_count: 2,
                match_ids: ['87_20252026_4837216', '138_20252026_5173359']
              }]
            };
          }

          if (compact.startsWith('SELECT match_id, external_id, league_name, season, home_team, away_team, match_date, status, data_source, pipeline_status, created_at, updated_at FROM matches')) {
            return {
              rows: params[0].map((matchId) => ({ ...state.matches.get(matchId) }))
            };
          }

          if (compact.includes('FROM matches_oddsportal_mapping')) {
            return { rows: [] };
          }

          if (compact.startsWith('UPDATE matches SET pipeline_status = $2')) {
            const [winnerId, pipelineStatus] = params;
            state.matches.get(winnerId).pipeline_status = pipelineStatus;
            return { rows: [], rowCount: 1 };
          }

          if (compact.startsWith("UPDATE matches SET pipeline_status = 'failed'")) {
            for (const loserId of params[0]) {
              state.matches.get(loserId).pipeline_status = 'failed';
            }
            return { rows: [], rowCount: params[0].length };
          }

          if (compact.startsWith('CREATE UNIQUE INDEX IF NOT EXISTS idx_matches_season_source_external_active_unique')) {
            assert.match(compact, /pipeline_status = ANY\(ARRAY\['failed', 'archived', 'duplicate', 'merged'\]::text\[\]\)/);
            state.indexCreated = true;
            return { rows: [], rowCount: 0 };
          }

          throw new Error(`unexpected_query:${compact}`);
        },
        release() {
          state.releaseCalls++;
        }
      };
    }
  };

  const janitor = new MatchCanonicalJanitor({
    getDbPool: () => pool,
    executeWithRetry: async (operation) => operation(),
    logger: { info() {}, warn() {}, error() {} },
    RepositoryError,
    identityInactiveStatuses: ['failed', 'archived', 'duplicate', 'merged']
  });

  await janitor.ensureSourceIdentityUniquenessIndex();

  assert.equal(state.matches.get('138_20252026_5173359').pipeline_status, 'RECON_LINKED');
  assert.equal(state.matches.get('87_20252026_4837216').pipeline_status, 'failed');
  assert.equal(state.indexCreated, true);
  assert.equal(state.releaseCalls, 1);
});
