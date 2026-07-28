// lifecycle: test-fixture
'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');

const { scanSqlTruthSource } = require('../../../scripts/ops/helpers/repoHygiene');

function writeSql(rootDir, relativePath) {
  const targetPath = path.join(rootDir, relativePath);
  fs.mkdirSync(path.dirname(targetPath), { recursive: true });
  fs.writeFileSync(targetPath, 'CREATE TABLE matches (match_id text);\n', 'utf8');
}

test('SQL hygiene 排除 Claude worktree，但继续拦截当前工作树中的核心表 DDL', () => {
  const fixtureRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'repo-hygiene-'));

  try {
    writeSql(fixtureRoot, '.claude/worktrees/other-worktree/illegal.sql');
    writeSql(fixtureRoot, 'scratch/illegal.sql');

    assert.deepEqual(scanSqlTruthSource({ repoRoot: fixtureRoot }), [
      '发现 migrations 之外的核心表 DDL 副本: scratch/illegal.sql'
    ]);
  } finally {
    fs.rmSync(fixtureRoot, { recursive: true, force: true });
  }
});
