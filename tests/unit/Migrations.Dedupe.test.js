'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');

const {
  dedupeMappings
} = require('../../src/infrastructure/services/migrations/dedupeMappings');

test('dedupeMappings 应按 updated_at 保留最新映射并且不误伤正常数据', async () => {
  const normalRows = Array.from({ length: 4934 }, (_, index) => ({
    match_id: `normal-${index + 1}`,
    season: '2024/2025',
    oddsportal_hash: `hash-${index + 1}`,
    updated_at: `2026-01-01T00:${String(index % 60).padStart(2, '0')}:00.000Z`,
    created_at: `2025-12-31T23:${String(index % 60).padStart(2, '0')}:00.000Z`
  }));

  const state = {
    rows: [
      ...normalRows,
      {
        match_id: 'dup-a-keep',
        season: '2024/2025',
        oddsportal_hash: 'dup-a',
        updated_at: '2026-01-03T10:00:00.000Z',
        created_at: '2026-01-01T10:00:00.000Z'
      },
      {
        match_id: 'dup-a-drop',
        season: '2024/2025',
        oddsportal_hash: 'dup-a',
        updated_at: '2026-01-02T10:00:00.000Z',
        created_at: '2026-01-01T09:00:00.000Z'
      },
      {
        match_id: 'dup-b-drop-2',
        season: '2024/2025',
        oddsportal_hash: 'dup-b',
        updated_at: '2026-01-03T08:00:00.000Z',
        created_at: '2026-01-01T08:00:00.000Z'
      },
      {
        match_id: 'dup-b-keep',
        season: '2024/2025',
        oddsportal_hash: 'dup-b',
        updated_at: '2026-01-04T08:00:00.000Z',
        created_at: '2026-01-01T08:00:00.000Z'
      },
      {
        match_id: 'dup-b-drop-1',
        season: '2024/2025',
        oddsportal_hash: 'dup-b',
        updated_at: '2026-01-03T12:00:00.000Z',
        created_at: '2026-01-01T08:00:00.000Z'
      }
    ],
    matches: [
      ...normalRows.map((row, index) => ({
        match_id: row.match_id,
        pipeline_status: index < 10 ? 'RECON_LINKED' : 'harvested'
      })),
      { match_id: 'dup-a-keep', pipeline_status: 'RECON_LINKED' },
      { match_id: 'dup-a-drop', pipeline_status: 'RECON_LINKED' },
      { match_id: 'dup-b-keep', pipeline_status: 'RECON_LINKED' },
      { match_id: 'dup-b-drop-1', pipeline_status: 'RECON_LINKED' },
      { match_id: 'dup-b-drop-2', pipeline_status: 'harvested' }
    ]
  };
  const auditLogs = [];

  const queryable = {
    async query(sql, params = []) {
      if (sql.includes('HAVING COUNT(*) > 1')) {
        const counts = new Map();
        for (const row of state.rows) {
          const key = `${row.season}::${row.oddsportal_hash}`;
          counts.set(key, (counts.get(key) || 0) + 1);
        }

        return {
          rows: state.rows.filter((row) => counts.get(`${row.season}::${row.oddsportal_hash}`) > 1)
        };
      }

      if (sql.includes('DELETE FROM matches_oddsportal_mapping')) {
        const [season, oddsportalHash, matchIds] = params;
        const before = state.rows.length;
        state.rows = state.rows.filter((row) => !(
          row.season === season
          && row.oddsportal_hash === oddsportalHash
          && matchIds.includes(row.match_id)
        ));
        return { rowCount: before - state.rows.length };
      }

      if (sql.includes('UPDATE matches m')) {
        const [matchIds] = params;
        let repairedCount = 0;

        for (const match of state.matches) {
          if (matchIds.includes(match.match_id) && match.pipeline_status === 'RECON_LINKED') {
            match.pipeline_status = 'harvested';
            repairedCount++;
          }
        }

        return { rowCount: repairedCount };
      }

      throw new Error(`unexpected_query:${sql}`);
    }
  };

  const result = await dedupeMappings({
    queryable,
    logger: {
      info(message, data) {
        auditLogs.push({ message, data });
      }
    }
  });

  assert.equal(result.deletedCount, 3);
  assert.equal(result.groupCount, 2);
  assert.equal(result.repairedCount, 2);
  assert.deepEqual(
    result.groups.map((group) => ({
      season: group.season,
      oddsportal_hash: group.oddsportal_hash,
      kept_match_id: group.kept_match_id,
      removed_match_ids: group.removed_match_ids
    })),
    [
      {
        season: '2024/2025',
        oddsportal_hash: 'dup-a',
        kept_match_id: 'dup-a-keep',
        removed_match_ids: ['dup-a-drop']
      },
      {
        season: '2024/2025',
        oddsportal_hash: 'dup-b',
        kept_match_id: 'dup-b-keep',
        removed_match_ids: ['dup-b-drop-1', 'dup-b-drop-2']
      }
    ]
  );
  assert.equal(state.rows.length, 4936);
  assert.equal(state.rows.some((row) => row.match_id === 'dup-a-keep'), true);
  assert.equal(state.rows.some((row) => row.match_id === 'dup-a-drop'), false);
  assert.equal(state.rows.some((row) => row.match_id === 'dup-b-keep'), true);
  assert.equal(state.rows.some((row) => row.match_id === 'dup-b-drop-1'), false);
  assert.equal(state.rows.some((row) => row.match_id === 'dup-b-drop-2'), false);
  assert.equal(state.matches.find((match) => match.match_id === 'dup-a-drop')?.pipeline_status, 'harvested');
  assert.equal(state.matches.find((match) => match.match_id === 'dup-b-drop-1')?.pipeline_status, 'harvested');
  assert.equal(state.matches.find((match) => match.match_id === 'dup-b-drop-2')?.pipeline_status, 'harvested');
  assert.equal(state.matches.find((match) => match.match_id === 'dup-a-keep')?.pipeline_status, 'RECON_LINKED');

  for (const row of normalRows) {
    assert.equal(
      state.rows.some((candidate) => candidate.match_id === row.match_id),
      true,
      `normal row should survive: ${row.match_id}`
    );
  }

  for (const index of [0, 3, 9]) {
    assert.equal(
      state.matches.find((match) => match.match_id === `normal-${index + 1}`)?.pipeline_status,
      'RECON_LINKED'
    );
  }

  assert.equal(auditLogs.length, 2);
  assert.match(auditLogs[0].message, /已清理历史 season\/hash 重复映射/);
});
