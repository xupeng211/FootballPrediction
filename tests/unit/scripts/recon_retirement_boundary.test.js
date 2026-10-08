// lifecycle: permanent
// scope: retired Recon discovery boundary; active source checks remain enforced
'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');

const ROOT = path.resolve(__dirname, '../../..');
const RETIRED_ROOT = 'archive/recon_v2_research';
const { scanSqlTruthSource } = require('../../../scripts/ops/helpers/repoHygiene');
const { auditRepoNoise } = require('../../../scripts/ops/technical_debt_workflow_audit_dry_run');

function writeFixture(root, relative, text) {
  const target = path.join(root, relative);
  fs.mkdirSync(path.dirname(target), { recursive: true });
  fs.writeFileSync(target, text);
}

test('SQL hygiene prunes retired probes before reading, while active and adjacent SQL still fail', () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'recon-boundary-'));
  const originalReadDir = fs.readdirSync;
  try {
    const sql = 'CREATE TABLE matches (match_id text);\n';
    writeFixture(root, `${RETIRED_ROOT}/historical.sql`, sql);
    writeFixture(root, 'archive/recon_v2_research_active/current.sql', sql);
    writeFixture(root, 'src/current.sql', sql);
    const historical = path.join(root, RETIRED_ROOT);
    fs.readdirSync = (target, ...args) => {
      assert.notEqual(path.resolve(String(target)), historical, 'must prune before descending');
      return originalReadDir(target, ...args);
    };
    assert.deepEqual(scanSqlTruthSource({ repoRoot: root }), [
      '发现 migrations 之外的核心表 DDL 副本: archive/recon_v2_research_active/current.sql, src/current.sql'
    ]);
  } finally {
    fs.readdirSync = originalReadDir;
    fs.rmSync(root, { recursive: true, force: true });
  }
});

test('legacy-test size inventory does not stat unrelated retired probe files', () => {
  const originalStat = fs.statSync;
  const historical = path.join(ROOT, RETIRED_ROOT) + path.sep;
  const historicalStats = [];
  try {
    fs.statSync = (target, ...args) => {
      if (path.resolve(String(target)).startsWith(historical)) historicalStats.push(String(target));
      return originalStat(target, ...args);
    };
    const result = auditRepoNoise();
    assert.deepEqual(historicalStats, [], 'retired probes must never enter legacy size inventory');
    assert.ok(Array.isArray(result.findings));
    assert.ok(result.findings.some(row => row.id === 'RN-005'), 'valuable legacy-test inventory is retained');
  } finally {
    fs.statSync = originalStat;
  }
});
