'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');

const { ReconEngine } = require('../../src/infrastructure/recon/ReconEngine');

test('ReconEngine._persistReconBatches 应输出带 recon_run_id 的批次持久化日志', async () => {
  const logs = [];
  const repositoryCalls = [];

  const engine = new ReconEngine({
    repository: {
      async batchSaveOddsPortalMappings(batch) {
        repositoryCalls.push({ type: 'linked', size: batch.length });
        return { success: true, inserted: batch.length, updated: batch.length };
      },
      async batchUpdateMatchPipelineStatus(batch, status, options) {
        repositoryCalls.push({ type: 'mismatch', size: batch.length, status, options });
        return { success: true, updated: batch.length };
      }
    },
    logger: {
      info(event, data) {
        logs.push({ event, data });
      },
      warn() {},
      error() {}
    }
  });

  await engine._persistReconBatches(
    [
      { match_id: 'm2' },
      { match_id: 'm1' },
      { match_id: 'm3' }
    ],
    ['x2', 'x1'],
    2,
    {
      reconRunId: 'recon-run-elite',
      season: '2024/2025',
      league: 'Premier League',
      sourceSeason: '2024-2025',
      sourceUrl: 'https://example.com/epl/results/'
    }
  );

  assert.deepEqual(repositoryCalls, [
    { type: 'linked', size: 2 },
    { type: 'linked', size: 1 },
    {
      type: 'mismatch',
      size: 2,
      status: 'RECON_MISMATCH',
      options: {
        season: '2024/2025',
        expectedCurrentStatus: 'harvested'
      }
    }
  ]);

  const startLogs = logs.filter((entry) => entry.event === 'recon_batch_persist_start');
  const completeLogs = logs.filter((entry) => entry.event === 'recon_batch_persist_complete');

  assert.equal(startLogs.length, 3);
  assert.equal(completeLogs.length, 3);
  assert.deepEqual(
    startLogs.map((entry) => ({
      recon_run_id: entry.data.recon_run_id,
      batch_type: entry.data.batch_type,
      batch_index: entry.data.batch_index,
      total_batches: entry.data.total_batches,
      match_ids: entry.data.match_ids
    })),
    [
      {
        recon_run_id: 'recon-run-elite',
        batch_type: 'linked',
        batch_index: 1,
        total_batches: 2,
        match_ids: { count: 2, preview: ['m1', 'm2'], first: 'm1', last: 'm2', truncated: false }
      },
      {
        recon_run_id: 'recon-run-elite',
        batch_type: 'linked',
        batch_index: 2,
        total_batches: 2,
        match_ids: { count: 1, preview: ['m3'], first: 'm3', last: 'm3', truncated: false }
      },
      {
        recon_run_id: 'recon-run-elite',
        batch_type: 'mismatch',
        batch_index: 1,
        total_batches: 1,
        match_ids: { count: 2, preview: ['x1', 'x2'], first: 'x1', last: 'x2', truncated: false }
      }
    ]
  );
});

test('ReconEngine 在高成功率阶段应降低 RECON_PROGRESS 日志频率，但结束时仍必须落最终快照', () => {
  const logs = [];
  const engine = new ReconEngine({
    logger: {
      info(event, data) {
        logs.push({ event, data });
      },
      warn() {},
      error() {}
    },
    progressLogEvery: 2,
    progressHighSuccessThreshold: 0.8,
    progressSampleMultiplier: 3
  });

  const progress = {
    processed: 0,
    linked: 0,
    mismatched: 0,
    total: 6,
    startedAt: Date.now() - 1000
  };

  for (let index = 0; index < 6; index++) {
    progress.processed++;
    progress.linked++;
    if (engine._shouldEmitReconProgressSnapshot(progress)) {
      engine._emitReconProgressSnapshot({ league: { name: 'Premier League' }, dbSeason: '2024/2025' }, progress);
    }
  }

  const snapshots = logs.filter((entry) => entry.event === 'recon_progress_snapshot');
  assert.equal(snapshots.length, 1);
  assert.equal(snapshots[0].data.processed, 6);
  assert.equal(snapshots[0].data.total, 6);
});

test('ReconEngine 在批次持久化遇到 hash 冲突时必须输出冲突审计日志', async () => {
  const logs = [];
  const engine = new ReconEngine({
    repository: {
      async batchSaveOddsPortalMappings() {
        const error = new Error('hash_conflict');
        error.code = 'HASH_CONFLICT';
        error.details = {
          season: '2024/2025',
          oddsportal_hash: 'samehash',
          incoming_match_ids: ['m1', 'm2']
        };
        throw error;
      },
      async batchUpdateMatchPipelineStatus() {
        return { success: true, updated: 0 };
      }
    },
    logger: {
      info(event, data) {
        logs.push({ level: 'info', event, data });
      },
      warn(event, data) {
        logs.push({ level: 'warn', event, data });
      },
      error(event, data) {
        logs.push({ level: 'error', event, data });
      }
    }
  });

  await assert.rejects(
    () => engine._persistReconBatches(
      [{ match_id: 'm2' }, { match_id: 'm1' }],
      [],
      50,
      {
        reconRunId: 'recon-run-conflict',
        season: '2024/2025',
        league: 'Premier League'
      }
    ),
    /hash_conflict/
  );

  const conflictLog = logs.find((entry) => entry.event === 'recon_batch_conflict');
  assert.ok(conflictLog);
  assert.equal(conflictLog.data.recon_run_id, 'recon-run-conflict');
  assert.deepEqual(conflictLog.data.match_ids, {
    count: 2,
    preview: ['m1', 'm2'],
    first: 'm1',
    last: 'm2',
    truncated: false
  });
  assert.deepEqual(conflictLog.data.conflict, {
    season: '2024/2025',
    oddsportal_hash: 'samehash',
    incoming_match_ids: ['m1', 'm2']
  });
});
