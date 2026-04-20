'use strict';

const fs = require('fs');
const path = require('path');
const { spawnSync } = require('child_process');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const TEST_ROOT = path.join(PROJECT_ROOT, 'tests');
const UNIT_DIR = path.join(TEST_ROOT, 'unit');
const INTEGRATION_DIR = path.join(TEST_ROOT, 'integration');
const STRESS_DIR = path.join(TEST_ROOT, 'stress');
const COVERAGE_REPORT_DIR = path.join(PROJECT_ROOT, 'reports', 'coverage', 'node');
const DEFAULT_MAX_BUFFER = 1024 * 1024 * 100;

const mode = process.argv[2] || 'default';
const modeArgs = process.argv.slice(3);
const COVERAGE_THRESHOLDS = Object.freeze({
  lines: 80,
  functions: 80,
  branches: 80,
});
const CRITICAL_SMOKE_TESTS = Object.freeze([
  'tests/unit/HttpClient.test.js',
  'tests/unit/BrowserProvider.test.js',
  'tests/unit/DatabaseConfig.test.js',
  'tests/unit/ReconBrowserContext.test.js',
]);
const RECON_CORE_TESTS = Object.freeze([
  'tests/unit/ReconDecryptor.test.js',
  'tests/unit/ReconDecryptorSourceExtractor.test.js',
  'tests/unit/ReconPureDecryptorRuntime.test.js',
  'tests/unit/ReconDistributedLock.test.js',
  'tests/unit/ReconSourceProber.test.js',
  'tests/unit/ReconMatrixFlow.test.js',
  'tests/unit/ReconMatrixTargetRunner.test.js',
]);
const PROJECT_JS_ROOTS = Object.freeze([
  path.join(PROJECT_ROOT, 'src'),
  path.join(PROJECT_ROOT, 'config'),
  path.join(PROJECT_ROOT, 'scripts'),
  UNIT_DIR,
  INTEGRATION_DIR,
  STRESS_DIR,
]);
let nativeCoverageThresholdSupport = null;
let dependencyGraphCache = null;

function safeReadDir(dir) {
  try {
    return fs.readdirSync(dir, { withFileTypes: true });
  } catch {
    return [];
  }
}

/**
 * 收集测试文件。
 * @param {string} dir
 * @returns {string[]}
 */
function collectTestFiles(dir) {
  if (!fs.existsSync(dir)) {
    return [];
  }

  return safeReadDir(dir)
    .filter(entry => entry.isFile() && entry.name.endsWith('.test.js'))
    .map(entry => path.join(dir, entry.name))
    .sort();
}

function walkJsFiles(dir, files = []) {
  if (!fs.existsSync(dir)) {
    return files;
  }

  for (const entry of safeReadDir(dir)) {
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      walkJsFiles(fullPath, files);
      continue;
    }

    if (entry.isFile() && entry.name.endsWith('.js')) {
      files.push(fullPath);
    }
  }

  return files;
}

function collectProjectJsFiles() {
  return [...new Set(
    PROJECT_JS_ROOTS.flatMap(root => walkJsFiles(root))
  )].sort();
}

function normalizeProjectPath(filePath) {
  if (!filePath) {
    return '';
  }

  return path.resolve(PROJECT_ROOT, filePath);
}

function resolveLocalModulePath(fromFile, specifier) {
  if (!specifier) {
    return null;
  }

  const rawSpecifier = String(specifier).trim();
  if (!rawSpecifier.startsWith('.') && !path.isAbsolute(rawSpecifier)) {
    return null;
  }

  const basePath = path.isAbsolute(rawSpecifier)
    ? rawSpecifier
    : path.resolve(path.dirname(fromFile), rawSpecifier);
  const candidates = [
    basePath,
    `${basePath}.js`,
    `${basePath}.json`,
    path.join(basePath, 'index.js'),
    path.join(basePath, 'index.json'),
  ];

  for (const candidate of candidates) {
    if (!candidate.startsWith(PROJECT_ROOT)) {
      continue;
    }
    if (fs.existsSync(candidate) && fs.statSync(candidate).isFile()) {
      return candidate;
    }
  }

  return null;
}

function collectDependencySpecifiers(sourceText) {
  const specifiers = new Set();
  const patterns = [
    /\brequire\(\s*['"]([^'"]+)['"]\s*\)/g,
    /\bimport(?:[^'"]*from\s*)?['"]([^'"]+)['"]/g,
    /\bimport\(\s*['"]([^'"]+)['"]\s*\)/g,
  ];

  for (const pattern of patterns) {
    let match = pattern.exec(sourceText);
    while (match) {
      specifiers.add(match[1]);
      match = pattern.exec(sourceText);
    }
  }

  return [...specifiers];
}

function buildDependencyGraph() {
  if (dependencyGraphCache) {
    return dependencyGraphCache;
  }

  const graph = new Map();
  for (const file of collectProjectJsFiles()) {
    let sourceText = '';
    try {
      sourceText = fs.readFileSync(file, 'utf8');
    } catch {
      graph.set(file, new Set());
      continue;
    }

    const deps = new Set();
    for (const specifier of collectDependencySpecifiers(sourceText)) {
      const resolved = resolveLocalModulePath(file, specifier);
      if (resolved) {
        deps.add(resolved);
      }
    }

    graph.set(file, deps);
  }

  dependencyGraphCache = graph;
  return graph;
}

function collectDependencyClosure(entryFile, graph, cache = new Map()) {
  if (cache.has(entryFile)) {
    return cache.get(entryFile);
  }

  const closure = new Set([entryFile]);
  const queue = [entryFile];

  while (queue.length > 0) {
    const current = queue.pop();
    for (const dependency of graph.get(current) || []) {
      if (closure.has(dependency)) {
        continue;
      }

      closure.add(dependency);
      queue.push(dependency);
    }
  }

  cache.set(entryFile, closure);
  return closure;
}

function resolveOrderedFiles(relativeFiles, availableFiles) {
  const fileMap = new Map(
    availableFiles.map(file => [path.relative(PROJECT_ROOT, file), file])
  );

  return relativeFiles
    .map(relativeFile => fileMap.get(relativeFile))
    .filter(Boolean);
}

function dedupeFiles(files) {
  const ordered = [];
  const seen = new Set();

  for (const file of files) {
    if (!file || seen.has(file)) {
      continue;
    }

    seen.add(file);
    ordered.push(file);
  }

  return ordered;
}

function resolveAffectedTestFiles(changedFiles, allTestFiles) {
  const normalizedChangedFiles = dedupeFiles(
    changedFiles
      .map(file => normalizeProjectPath(file))
      .filter(Boolean)
  );
  if (normalizedChangedFiles.length === 0) {
    return [];
  }

  const graph = buildDependencyGraph();
  const closureCache = new Map();
  const affected = [];
  const changedSet = new Set(normalizedChangedFiles);
  const hasReconChange = normalizedChangedFiles.some(file =>
    file.startsWith(path.join(PROJECT_ROOT, 'src', 'infrastructure', 'recon'))
    || file.startsWith(path.join(PROJECT_ROOT, 'tests', 'unit', 'Recon'))
  );

  for (const testFile of allTestFiles) {
    if (changedSet.has(testFile)) {
      affected.push(testFile);
      continue;
    }

    const closure = collectDependencyClosure(testFile, graph, closureCache);
    if (normalizedChangedFiles.some(file => closure.has(file))) {
      affected.push(testFile);
    }
  }

  const smokeFiles = resolveCriticalSmokeFiles(allTestFiles);
  const reconCoreFiles = hasReconChange
    ? resolveOrderedFiles(RECON_CORE_TESTS, allTestFiles)
    : [];

  return dedupeFiles([
    ...smokeFiles,
    ...reconCoreFiles,
    ...affected,
  ]);
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
 * 格式化耗时。
 * @param {number} durationMs
 * @returns {string}
 */
function formatDuration(durationMs) {
  if (!Number.isFinite(durationMs) || durationMs < 1000) {
    return `${Math.max(0, Math.round(durationMs))}ms`;
  }

  return `${(durationMs / 1000).toFixed(2)}s`;
}

/**
 * 从 TAP 输出中提取首个失败摘要。
 * @param {string[]} lines
 * @param {number} failureIndex
 * @returns {string[]}
 */
function collectSubtestTrail(lines, failureIndex) {
  const subtests = [];
  const failureIndent = (lines[failureIndex].match(/^(\s*)/) || ['', ''])[1].length;
  let maxIndent = failureIndent;

  for (let index = failureIndex - 1; index >= 0; index -= 1) {
    const match = lines[index].match(/^(\s*)# Subtest: (.+)$/);
    if (!match) {
      continue;
    }

    const indent = match[1].length;
    if (indent <= maxIndent) {
      subtests.unshift(match[2].trim());
      maxIndent = Math.max(-1, indent - 1);
    }
  }

  return subtests;
}

function extractFailureDetails(lines, failureIndex) {
  let location = null;
  let error = null;

  for (let index = failureIndex + 1; index < Math.min(lines.length, failureIndex + 30); index += 1) {
    const locationMatch = lines[index].match(/location:\s*'([^']+)'/);
    if (locationMatch && !location) {
      location = locationMatch[1];
    }

    const errorMatch = lines[index].match(/error:\s*(.+)$/);
    if (!errorMatch || error) {
      continue;
    }

    const raw = errorMatch[1].trim();
    if (raw && !['|-', '|', '>-', '>'].includes(raw)) {
      error = raw.replace(/^['"]|['"]$/g, '');
      continue;
    }

    for (let detailIndex = index + 1; detailIndex < Math.min(lines.length, index + 6); detailIndex += 1) {
      const detail = lines[detailIndex].trim();
      if (detail && detail !== '---' && !detail.startsWith('stack:')) {
        error = detail;
        break;
      }
    }
  }

  return { error, location };
}

function extractFailureSummary(text) {
  const lines = text.split(/\r?\n/);
  const failureIndex = lines.findIndex(line => /^\s*not ok \d+ - /.test(line));
  if (failureIndex === -1) {
    return null;
  }

  const testName = lines[failureIndex].replace(/^\s*not ok \d+ - /, '').trim();
  const subtests = collectSubtestTrail(lines, failureIndex);
  const titleParts = [];
  for (const part of [...subtests.slice(-3), testName]) {
    if (part && titleParts[titleParts.length - 1] !== part) {
      titleParts.push(part);
    }
  }
  const { location, error } = extractFailureDetails(lines, failureIndex);

  return {
    title: titleParts.join(' > '),
    location,
    error,
  };
}

/**
 * 打印失败摘要。
 * @param {string[]} files
 * @param {string} output
 * @param {string} label
 * @param {number} durationMs
 */
function printFailureSummary(files, output, label, durationMs) {
  const summary = extractFailureSummary(output);
  console.error(`[TEST-GATE] ${label}失败，门禁已拦截，用时 ${formatDuration(durationMs)}。`);

  if (!summary) {
    console.error('[TEST-GATE] 未能提取失败摘要，请查看上方 TAP 输出。');
    return;
  }

  console.error(`[TEST-GATE] 首个失败用例: ${summary.title}`);
  const normalizedLocation = summary.location
    ? summary.location.replace(/^\/app\//, '')
    : null;

  if (normalizedLocation) {
    console.error(`[TEST-GATE] 定位: ${normalizedLocation}`);
  }
  if (summary.error) {
    console.error(`[TEST-GATE] 错误: ${summary.error}`);
  }

  const suggestedFile = normalizedLocation
    ? normalizedLocation.split(':')[0]
    : path.relative(PROJECT_ROOT, files[0]);
  if (suggestedFile) {
    console.error(`[TEST-GATE] 快速复现: node --test ${suggestedFile}`);
  }
}

/**
 * 获取关键烟雾测试文件。
 * @param {string[]} files
 * @returns {string[]}
 */
function resolveCriticalSmokeFiles(files) {
  const fileMap = new Map(
    files.map(file => [path.relative(PROJECT_ROOT, file), file])
  );

  return CRITICAL_SMOKE_TESTS
    .map(relativeFile => fileMap.get(relativeFile))
    .filter(Boolean);
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

function writeCoverageSummary(summary) {
  if (!summary) {
    return;
  }

  fs.mkdirSync(COVERAGE_REPORT_DIR, { recursive: true });
  const payload = {
    total: {
      lines: {
        total: 0,
        covered: 0,
        skipped: 0,
        pct: summary.lines,
      },
      statements: {
        total: 0,
        covered: 0,
        skipped: 0,
        pct: summary.lines,
      },
      functions: {
        total: 0,
        covered: 0,
        skipped: 0,
        pct: summary.functions,
      },
      branches: {
        total: 0,
        covered: 0,
        skipped: 0,
        pct: summary.branches,
      },
    },
  };
  fs.writeFileSync(
    path.join(COVERAGE_REPORT_DIR, 'coverage-summary.json'),
    JSON.stringify(payload, null, 2),
    'utf8',
  );
}

/**
 * 执行 node --test。
 * @param {string[]} files
 * @param {{ coverage?: boolean, label?: string }} [options]
 * @returns {number}
 */
function runNodeTests(files, options = {}) {
  const { coverage = false, label = '测试阶段' } = options;

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

  const startTime = Date.now();
  const result = spawnSync('node', args, {
    cwd: PROJECT_ROOT,
    encoding: 'utf8',
    maxBuffer: DEFAULT_MAX_BUFFER,
  });
  const durationMs = Date.now() - startTime;
  const stdout = result.stdout || '';
  const stderr = result.stderr || '';
  const combinedOutput = `${stdout}\n${stderr}`;

  process.stdout.write(stdout);
  process.stderr.write(stderr);

  if (result.error) {
    console.error(`[TEST-GATE] ${label}启动失败: ${result.error.message}`);
    return 1;
  }

  const exitCode = result.status ?? 1;
  if (exitCode !== 0) {
    printFailureSummary(files, combinedOutput, label, durationMs);
    return exitCode;
  }

  if (coverage && !supportsNativeCoverageThresholds()) {
    const summary = parseCoverageSummary(combinedOutput);
    writeCoverageSummary(summary);
    const coverageExitCode = enforceCoverageThresholds(summary);
    if (coverageExitCode !== 0) {
      console.error(`[TEST-GATE] ${label}已完成，但覆盖率门禁失败。`);
      return coverageExitCode;
    }
  }

  console.log(`[TEST-GATE] ${label}通过，用时 ${formatDuration(durationMs)}。`);
  return 0;
}

const unitFiles = collectTestFiles(UNIT_DIR);
const integrationFiles = collectTestFiles(INTEGRATION_DIR);
const stressFiles = collectTestFiles(STRESS_DIR);
const allTestFiles = dedupeFiles([
  ...unitFiles,
  ...integrationFiles,
  ...stressFiles,
]);

if (mode === 'default' || mode === 'unit') {
  console.log('[TEST-GATE] 默认门禁执行: 关键烟雾测试 + 全量单元测试。');
  const smokeFiles = resolveCriticalSmokeFiles(unitFiles);
  if (smokeFiles.length > 0) {
    const smokeExitCode = runNodeTests(smokeFiles, { label: '关键烟雾测试' });
    if (smokeExitCode !== 0) {
      process.exit(smokeExitCode);
    }
  }

  const smokeSet = new Set(smokeFiles);
  const remainingUnitFiles = unitFiles.filter(file => !smokeSet.has(file));
  process.exit(runNodeTests(remainingUnitFiles, { label: '全量单元测试' }));
}

if (mode === 'affected') {
  const affectedFiles = resolveAffectedTestFiles(modeArgs, allTestFiles);
  const selectedFiles = affectedFiles.length > 0
    ? affectedFiles
    : resolveCriticalSmokeFiles(allTestFiles);

  console.log(
    `[TEST-GATE] 增量门禁执行: 变更文件 ${modeArgs.length} 个，命中测试 ${selectedFiles.length} 个。`
  );
  process.exit(runNodeTests(selectedFiles, { label: '增量 JS 测试' }));
}

if (mode === 'integration') {
  process.exit(runNodeTests(integrationFiles, { label: '集成测试' }));
}

if (mode === 'coverage') {
  console.log(
    `[TEST-GATE] 覆盖率门禁已启用: lines>=${COVERAGE_THRESHOLDS.lines}, `
    + `functions>=${COVERAGE_THRESHOLDS.functions}, branches>=${COVERAGE_THRESHOLDS.branches}`,
  );
  process.exit(runNodeTests(unitFiles, { coverage: true, label: '覆盖率测试' }));
}

if (mode === 'recon-core') {
  const reconCoreFiles = resolveOrderedFiles(RECON_CORE_TESTS, allTestFiles);
  process.exit(runNodeTests(reconCoreFiles, { label: 'Recon 核心测试' }));
}

console.error(`[TEST-GATE] 未知模式: ${mode}`);
process.exit(1);
