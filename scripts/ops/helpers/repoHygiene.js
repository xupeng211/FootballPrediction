#!/usr/bin/env node
'use strict';

const fs = require('fs');
const path = require('path');
const { spawnSync } = require('child_process');

const REPO_ROOT = path.resolve(__dirname, '../../..');
const MIGRATIONS_DIR = normalizeRepoPath(path.join(REPO_ROOT, 'database/migrations'));
const SQL_ALLOWLIST = new Set([
  'deploy/docker/init_db.sql',
  'deploy/docker/init_claude_reader.sql'
]);
const DATA_ALLOWLIST_PREFIXES = [
  'data/production/',
  'data/processed/',
  'data/regression/',
  'data/snapshots/'
];
const DATA_ALLOWLIST_FILES = new Set([
  'data/.gitkeep',
  'data/manual_html/.gitkeep',
  'data/manual_html/test_sample.html',
  'data/mock/sample_history.csv',
  'data/processed/.gitkeep',
  'data/snapshots/.gitkeep'
]);
const OPS_WARNING_EXCLUDE = new Set([
  'scripts/ops/gatekeeper.js'
]);
const REFERENCE_ROOTS = [
  'package.json',
  '.github/workflows',
  'scripts/devops',
  'scripts/ops/total_war_pipeline.js',
  'scripts/ops/run_production.js',
  'scripts/ops/recon_scanner.js',
  'scripts/ops/recon_scanner_impl.js',
  'scripts/ops/ReconCLIHandler.js',
  'scripts/ops/titan_discovery.js',
  'scripts/ops/smelt_all.js',
  'scripts/ops/check_health.js',
  'scripts/ops/db_vault.js'
];
const WALK_EXCLUDED_DIRS = new Set([
  '.git',
  '.cache',
  'archive_vault_2026',
  'node_modules',
  'venv',
  '.venv',
  '__pycache__',
  '.pytest_cache',
  '.ruff_cache',
  '.mypy_cache'
]);
const CORE_TABLE_DDL_RE = /\bCREATE\s+TABLE(?:\s+IF\s+NOT\s+EXISTS)?\s+"?(matches|raw_match_data|matches_oddsportal_mapping)"?\b/i;

function normalizeRepoPath(targetPath) {
  const relativePath = path.relative(REPO_ROOT, targetPath);
  return relativePath.split(path.sep).join('/');
}

function git(args, options = {}) {
  const result = spawnSync('git', args, {
    cwd: REPO_ROOT,
    encoding: 'utf8',
    ...options
  });

  if (result.error) {
    throw result.error;
  }

  return result;
}

function gitLines(args) {
  const result = git(args);
  if (result.status !== 0) {
    return [];
  }

  return String(result.stdout || '')
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean);
}

function isTracked(relativePath, trackedFiles = null) {
  if (trackedFiles instanceof Set) {
    return trackedFiles.has(relativePath);
  }

  const result = git(['ls-files', '--error-unmatch', relativePath]);
  return result.status === 0;
}

function isIgnored(relativePath) {
  const result = git(['check-ignore', '--no-index', '-q', relativePath]);
  if (result.status === 0) {
    return true;
  }
  if (result.status === 1) {
    return false;
  }

  const stderr = String(result.stderr || '').trim();
  throw new Error(`git check-ignore 执行失败: ${stderr || relativePath}`);
}

function summarizeList(items = [], limit = 8) {
  if (!Array.isArray(items) || items.length === 0) {
    return '';
  }

  const preview = items.slice(0, limit).join(', ');
  const remainder = items.length - Math.min(items.length, limit);
  return remainder > 0 ? `${preview} ... 还有 ${remainder} 个` : preview;
}

function walkFiles(rootDir, predicate, files = []) {
  if (!fs.existsSync(rootDir)) {
    return files;
  }

  const entries = fs.readdirSync(rootDir, { withFileTypes: true });
  for (const entry of entries) {
    const absolutePath = path.join(rootDir, entry.name);
    const relativePath = normalizeRepoPath(absolutePath);

    if (entry.isDirectory()) {
      if (
        WALK_EXCLUDED_DIRS.has(entry.name)
        || relativePath.startsWith('data/postgres/')
        || relativePath.startsWith('data/redis/')
      ) {
        continue;
      }

      walkFiles(absolutePath, predicate, files);
      continue;
    }

    if (predicate(absolutePath, relativePath)) {
      files.push(relativePath);
    }
  }

  return files;
}

function collectReferenceFiles() {
  const files = [];
  for (const relativePath of REFERENCE_ROOTS) {
    const absolutePath = path.join(REPO_ROOT, relativePath);
    if (!fs.existsSync(absolutePath)) {
      continue;
    }

    const stat = fs.statSync(absolutePath);
    if (stat.isDirectory()) {
      walkFiles(absolutePath, (_absolutePath, nestedRelativePath) => {
        files.push(nestedRelativePath);
        return false;
      });
      continue;
    }

    files.push(relativePath);
  }

  return [...new Set(files)];
}

function collectReferencedOpsScripts() {
  const references = new Set();
  const referenceFiles = collectReferenceFiles();

  for (const relativePath of referenceFiles) {
    const absolutePath = path.join(REPO_ROOT, relativePath);
    let content = '';
    try {
      content = fs.readFileSync(absolutePath, 'utf8');
    } catch {
      continue;
    }

    const pathMatches = content.match(/scripts\/ops\/[A-Za-z0-9_.-]+\.js/g) || [];
    pathMatches.forEach((match) => references.add(match));
  }

  const candidates = gitLines(['ls-files', '--', 'scripts/ops/*.js']);
  for (const candidate of candidates) {
    if (references.has(candidate)) {
      continue;
    }

    const baseName = path.basename(candidate);
    const stem = path.basename(candidate, '.js');
    const referenceFilesContent = referenceFiles.some((relativePath) => {
      const absolutePath = path.join(REPO_ROOT, relativePath);
      try {
        const content = fs.readFileSync(absolutePath, 'utf8');
        return content.includes(baseName) || content.includes(stem);
      } catch {
        return false;
      }
    });

    if (referenceFilesContent) {
      references.add(candidate);
    }
  }

  return references;
}

function scanOpsScriptReferences() {
  const trackedOpsScripts = gitLines(['ls-files', '--', 'scripts/ops/*.js'])
    .filter((relativePath) => (
      fs.existsSync(path.join(REPO_ROOT, relativePath))
      && path.dirname(relativePath) === 'scripts/ops'
    ));
  const referencedScripts = collectReferencedOpsScripts();
  const suspects = trackedOpsScripts.filter((relativePath) => (
    !OPS_WARNING_EXCLUDE.has(relativePath) && !referencedScripts.has(relativePath)
  ));

  if (suspects.length === 0) {
    return [];
  }

  return [
    `疑似脱离主流程的 scripts/ops 脚本 ${suspects.length} 个: ${summarizeList(suspects)}`
  ];
}

function scanSqlTruthSource() {
  const sqlFiles = walkFiles(REPO_ROOT, (_absolutePath, relativePath) => relativePath.endsWith('.sql'));
  const violations = [];

  for (const relativePath of sqlFiles) {
    if (relativePath.startsWith(`${MIGRATIONS_DIR}/`) || SQL_ALLOWLIST.has(relativePath)) {
      continue;
    }

    const absolutePath = path.join(REPO_ROOT, relativePath);
    const content = fs.readFileSync(absolutePath, 'utf8');
    if (CORE_TABLE_DDL_RE.test(content)) {
      violations.push(relativePath);
    }
  }

  if (violations.length === 0) {
    return [];
  }

  return [
    `发现 migrations 之外的核心表 DDL 副本: ${summarizeList(violations)}`
  ];
}

function isAllowedDataFile(relativePath) {
  if (DATA_ALLOWLIST_FILES.has(relativePath)) {
    return true;
  }

  return DATA_ALLOWLIST_PREFIXES.some((prefix) => relativePath.startsWith(prefix));
}

function scanDataArtifacts() {
  const dataRoot = path.join(REPO_ROOT, 'data');
  const trackedDataFiles = new Set(gitLines(['ls-files', '--', 'data']));
  const files = walkFiles(dataRoot, (_absolutePath, relativePath) => relativePath.startsWith('data/'));
  const trackedViolations = [];
  const ignoreViolations = [];

  for (const relativePath of files) {
    if (isAllowedDataFile(relativePath)) {
      continue;
    }

    if (isTracked(relativePath, trackedDataFiles)) {
      trackedViolations.push(relativePath);
      continue;
    }

    if (!isIgnored(relativePath)) {
      ignoreViolations.push(relativePath);
    }
  }

  const failures = [];
  if (trackedViolations.length > 0) {
    failures.push(`运行态 data 产物已被纳入版本控制: ${summarizeList(trackedViolations)}`);
  }
  if (ignoreViolations.length > 0) {
    failures.push(`发现未被 .gitignore 捕获的 data 运行产物: ${summarizeList(ignoreViolations)}`);
  }

  return failures;
}

function runRepoHygieneCheck(options = {}) {
  const warnings = scanOpsScriptReferences();
  const failures = [
    ...scanSqlTruthSource(),
    ...scanDataArtifacts()
  ];
  const result = {
    passed: failures.length === 0,
    warnings,
    failures
  };

  if (options.emit !== false) {
    warnings.forEach((message) => {
      process.stdout.write(`[REPO-HYGIENE] WARN - ${message}\n`);
    });
    failures.forEach((message) => {
      process.stderr.write(`[REPO-HYGIENE] FAIL - ${message}\n`);
    });
    if (result.passed) {
      process.stdout.write('[REPO-HYGIENE] PASS - 仓库卫生检查通过\n');
    }
  }

  return result;
}

if (require.main === module) {
  try {
    const result = runRepoHygieneCheck({ emit: true });
    process.exit(result.passed ? 0 : 1);
  } catch (error) {
    process.stderr.write(`[REPO-HYGIENE] FAIL - ${error.message}\n`);
    process.exit(1);
  }
}

module.exports = {
  runRepoHygieneCheck
};
