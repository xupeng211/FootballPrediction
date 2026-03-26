'use strict';

const fs = require('fs');
const path = require('path');
const { spawnSync } = require('child_process');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const TEST_ROOT = path.join(PROJECT_ROOT, 'tests');
const UNIT_DIR = path.join(TEST_ROOT, 'unit');
const INTEGRATION_DIR = path.join(TEST_ROOT, 'integration');

const mode = process.argv[2] || 'default';

const RISK_RULES = [
  {
    id: 'hardcoded_path',
    label: '硬编码绝对路径',
    pattern: /\/app\/|auth_gold\.json|\/data\/debug/i,
  },
  {
    id: 'live_url',
    label: '外网 URL 依赖',
    pattern: /https?:\/\/[^\s"'`]+/i,
  },
  {
    id: 'browser_dependency',
    label: '真实浏览器依赖',
    pattern: /\bplaywright\b|\bchromium\b|\bpuppeteer\b/i,
  },
];

/**
 * 递归收集测试文件。
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
 * 分析单个测试文件的风险标签。
 * @param {string} filePath
 * @returns {{ file: string, tags: string[] }}
 */
function analyzeRisk(filePath) {
  const content = fs.readFileSync(filePath, 'utf8');
  const tags = RISK_RULES.filter(rule => rule.pattern.test(content)).map(rule => rule.label);

  return {
    file: filePath,
    tags,
  };
}

/**
 * 输出门禁报告。
 * @param {string} title
 * @param {{ file: string, tags: string[] }[]} riskyFiles
 */
function printRiskReport(title, riskyFiles) {
  console.log(`\n[TEST-GATE] ${title}`);

  if (riskyFiles.length === 0) {
    console.log('[TEST-GATE] 未发现环境依赖测试。');
    return;
  }

  for (const entry of riskyFiles) {
    const relativePath = path.relative(PROJECT_ROOT, entry.file);
    console.log(`[TEST-GATE] SKIP ${relativePath} -> ${entry.tags.join(' / ')}`);
  }
}

/**
 * 执行 node --test。
 * @param {string[]} files
 * @param {boolean} [coverage=false]
 * @returns {number}
 */
function runNodeTests(files, coverage = false) {
  if (files.length === 0) {
    console.log('[TEST-GATE] 没有可执行的测试文件。');
    return 0;
  }

  const args = ['--test', '--test-concurrency=1'];
  if (coverage) {
    args.push('--experimental-test-coverage');
  }
  args.push(...files.map(file => path.relative(PROJECT_ROOT, file)));

  const result = spawnSync('node', args, {
    cwd: PROJECT_ROOT,
    stdio: 'inherit',
  });

  return result.status ?? 1;
}

const unitFiles = collectTestFiles(UNIT_DIR);
const analyzedUnitFiles = unitFiles.map(analyzeRisk);
const riskyUnitFiles = analyzedUnitFiles.filter(entry => entry.tags.length > 0);
const safeUnitFiles = analyzedUnitFiles.filter(entry => entry.tags.length === 0).map(entry => entry.file);
const integrationFiles = collectTestFiles(INTEGRATION_DIR);
const explicitIntegrationFiles = [
  ...integrationFiles,
  ...riskyUnitFiles.map(entry => entry.file),
];

if (mode === 'default' || mode === 'unit') {
  printRiskReport('默认门禁已隔离环境依赖测试', riskyUnitFiles);
  process.exit(runNodeTests(safeUnitFiles, mode === 'coverage'));
}

if (mode === 'integration') {
  printRiskReport('显式执行环境依赖测试', riskyUnitFiles);
  process.exit(runNodeTests(explicitIntegrationFiles));
}

if (mode === 'coverage') {
  printRiskReport('覆盖率模式已隔离环境依赖测试', riskyUnitFiles);
  process.exit(runNodeTests(safeUnitFiles, true));
}

console.error(`[TEST-GATE] 未知模式: ${mode}`);
process.exit(1);
