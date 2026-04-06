'use strict';

const fs = require('fs');
const path = require('path');
const { spawnSync } = require('child_process');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const TEST_ROOT = path.join(PROJECT_ROOT, 'tests');
const UNIT_DIR = path.join(TEST_ROOT, 'unit');
const INTEGRATION_DIR = path.join(TEST_ROOT, 'integration');

const mode = process.argv[2] || 'default';
const COVERAGE_THRESHOLDS = Object.freeze({
  lines: 80,
  functions: 80,
  branches: 80,
});
let nativeCoverageThresholdSupport = null;

/**
 * 收集测试文件。
 * @param {string} dir
 * @returns {string[]}
 */
function collectTestFiles(dir) {
  if (!fs.existsSync(dir)) {
    return [];
  }

  return fs
    .readdirSync(dir)
    .filter(name => name.endsWith('.test.js'))
    .map(name => path.join(dir, name))
    .sort();
}

/**
 * 判断当前 Node 是否支持原生覆盖率阈值参数。
 * @returns {boolean}
 */
function supportsNativeCoverageThresholds() {
  if (nativeCoverageThresholdSupport !== null) {
    return nativeCoverageThresholdSupport;
  }

  const result = spawnSync('node', ['--help'], {
    cwd: PROJECT_ROOT,
    encoding: 'utf8',
  });
  const helpText = `${result.stdout || ''}\n${result.stderr || ''}`;
  nativeCoverageThresholdSupport = helpText.includes('--test-coverage-lines');
  return nativeCoverageThresholdSupport;
}

/**
 * 解析 Node 内建覆盖率汇总。
 * @param {string} text
 * @returns {{ lines: number, branches: number, functions: number } | null}
 */
function parseCoverageSummary(text) {
  const match = text.match(/# all files\s*\|\s*([\d.]+)\s*\|\s*([\d.]+)\s*\|\s*([\d.]+)\s*\|/);
  if (!match) {
    return null;
  }

  return {
    lines: Number.parseFloat(match[1]),
    branches: Number.parseFloat(match[2]),
    functions: Number.parseFloat(match[3]),
  };
}

/**
 * 校验覆盖率阈值。
 * @param {{ lines: number, branches: number, functions: number } | null} summary
 * @returns {number}
 */
function enforceCoverageThresholds(summary) {
  if (!summary) {
    console.error('[TEST-GATE] 未找到覆盖率汇总，拒绝放行。');
    return 1;
  }

  const failures = [];
  if (summary.lines < COVERAGE_THRESHOLDS.lines) {
    failures.push(`lines=${summary.lines.toFixed(2)} < ${COVERAGE_THRESHOLDS.lines}`);
  }
  if (summary.functions < COVERAGE_THRESHOLDS.functions) {
    failures.push(`functions=${summary.functions.toFixed(2)} < ${COVERAGE_THRESHOLDS.functions}`);
  }
  if (summary.branches < COVERAGE_THRESHOLDS.branches) {
    failures.push(`branches=${summary.branches.toFixed(2)} < ${COVERAGE_THRESHOLDS.branches}`);
  }

  if (failures.length > 0) {
    console.error(`[TEST-GATE] 覆盖率未达标: ${failures.join(', ')}`);
    return 1;
  }

  console.log(
    `[TEST-GATE] 覆盖率通过: lines=${summary.lines.toFixed(2)} `
    + `branches=${summary.branches.toFixed(2)} functions=${summary.functions.toFixed(2)}`
  );
  return 0;
}

/**
 * 执行 node --test。
 * @param {string[]} files
 * @param {{ coverage?: boolean }} [options]
 * @returns {number}
 */
function runNodeTests(files, options = {}) {
  const { coverage = false } = options;

  if (files.length === 0) {
    console.error('[TEST-GATE] 未发现可执行的测试文件，拒绝空跑门禁。');
    return 1;
  }

  const args = ['--test', '--test-concurrency=1'];
  if (coverage) {
    args.push('--experimental-test-coverage');
    if (supportsNativeCoverageThresholds()) {
      args.push(
        `--test-coverage-lines=${COVERAGE_THRESHOLDS.lines}`,
        `--test-coverage-functions=${COVERAGE_THRESHOLDS.functions}`,
        `--test-coverage-branches=${COVERAGE_THRESHOLDS.branches}`,
      );
    }
  }
  args.push(...files.map(file => path.relative(PROJECT_ROOT, file)));

  if (coverage && !supportsNativeCoverageThresholds()) {
    const result = spawnSync('node', args, {
      cwd: PROJECT_ROOT,
      encoding: 'utf8',
      maxBuffer: 1024 * 1024 * 50,
    });
    process.stdout.write(result.stdout || '');
    process.stderr.write(result.stderr || '');

    if ((result.status ?? 1) !== 0) {
      return result.status ?? 1;
    }

    const summary = parseCoverageSummary(`${result.stdout || ''}\n${result.stderr || ''}`);
    return enforceCoverageThresholds(summary);
  }

  const result = spawnSync('node', args, {
    cwd: PROJECT_ROOT,
    stdio: 'inherit',
  });

  return result.status ?? 1;
}

const unitFiles = collectTestFiles(UNIT_DIR);
const integrationFiles = collectTestFiles(INTEGRATION_DIR);

if (mode === 'default' || mode === 'unit') {
  console.log('[TEST-GATE] 默认门禁执行 100% 全量单元测试。');
  process.exit(runNodeTests(unitFiles));
}

if (mode === 'integration') {
  process.exit(runNodeTests(integrationFiles));
}

if (mode === 'coverage') {
  console.log(
    `[TEST-GATE] 覆盖率门禁已启用: lines>=${COVERAGE_THRESHOLDS.lines}, `
    + `functions>=${COVERAGE_THRESHOLDS.functions}, branches>=${COVERAGE_THRESHOLDS.branches}`,
  );
  process.exit(runNodeTests(unitFiles, { coverage: true }));
}

console.error(`[TEST-GATE] 未知模式: ${mode}`);
process.exit(1);
