'use strict';

const fs = require('fs');
const path = require('path');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const COVERAGE_SUMMARY_PATH = path.join(
  PROJECT_ROOT,
  'reports',
  'coverage',
  'recon-core',
  'coverage-summary.json'
);
const CRITICAL_LINE_THRESHOLD = 90;
const CRITICAL_FILES = Object.freeze([
  'src/infrastructure/recon/services/ReconDecryptorSourceExtractor.js',
  'src/infrastructure/recon/services/ReconSourceProber.js',
  'src/infrastructure/recon/services/ReconMatrixTargetRunner.js',
  'src/infrastructure/recon/ReconDistributedLock.js',
  'src/infrastructure/recon/services/ReconPureDecryptorRuntime.js',
]);

function fail(message) {
  console.error(`[TEST-GATE] ${message}`);
  process.exit(1);
}

if (!fs.existsSync(COVERAGE_SUMMARY_PATH)) {
  fail(`缺少 Recon 核心覆盖率汇总: ${path.relative(PROJECT_ROOT, COVERAGE_SUMMARY_PATH)}`);
}

const summary = JSON.parse(fs.readFileSync(COVERAGE_SUMMARY_PATH, 'utf8'));
const failures = [];

for (const relativeFile of CRITICAL_FILES) {
  const entry = Object.entries(summary).find(([key]) =>
    key === relativeFile
    || key.endsWith(`/${relativeFile}`)
    || key.endsWith(`/${path.basename(relativeFile)}`)
  );

  if (!entry) {
    failures.push(`${relativeFile}: missing`);
    continue;
  }

  const [, metrics] = entry;
  const linePct = Number(metrics?.lines?.pct || 0);
  if (linePct < CRITICAL_LINE_THRESHOLD) {
    failures.push(`${relativeFile}: lines=${linePct.toFixed(2)} < ${CRITICAL_LINE_THRESHOLD}`);
  }
}

if (failures.length > 0) {
  fail(`Recon 核心文件覆盖率未达标:\n- ${failures.join('\n- ')}`);
}

console.log(
  `[TEST-GATE] Recon 核心文件行覆盖率通过: ${CRITICAL_FILES.length} 个文件均 >= ${CRITICAL_LINE_THRESHOLD}%`
);
