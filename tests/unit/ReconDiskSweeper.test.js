'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const { ReconDiskSweeper } = require('../../src/infrastructure/recon/services/ReconDiskSweeper');

test('ReconDiskSweeper 应删除超过 1 小时的旧 profile 目录并保留新目录', async () => {
  const rootDir = await fs.promises.mkdtemp(path.join(os.tmpdir(), 'recon-disk-sweeper-'));
  const staleDir = path.join(rootDir, 'playwright_profile_stale');
  const freshDir = path.join(rootDir, 'playwright_profile_fresh');

  await fs.promises.mkdir(staleDir, { recursive: true });
  await fs.promises.mkdir(freshDir, { recursive: true });
  await fs.promises.writeFile(path.join(staleDir, 'old.txt'), 'stale');
  await fs.promises.writeFile(path.join(freshDir, 'new.txt'), 'fresh');

  const staleTime = new Date(Date.now() - (2 * 60 * 60 * 1000));
  await fs.promises.utimes(staleDir, staleTime, staleTime);
  await fs.promises.utimes(path.join(staleDir, 'old.txt'), staleTime, staleTime);

  const sweeper = new ReconDiskSweeper({
    logger: { info() {}, warn() {}, error() {}, debug() {} },
    rootDir,
    maxAgeMs: 60 * 60 * 1000
  });

  const result = await sweeper.sweep();

  assert.equal(result.scanned, 2);
  assert.equal(result.removed, 1);
  assert.equal(fs.existsSync(staleDir), false);
  assert.equal(fs.existsSync(freshDir), true);

  await fs.promises.rm(rootDir, { recursive: true, force: true });
});
