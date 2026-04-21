'use strict';

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');
const assert = require('node:assert/strict');

const {
  parseArgs,
  getDefaultReconLimit,
  getDefaultReconThreshold,
  getTotalWarLogSettings
} = require('../../scripts/ops/total_war_pipeline');

function restoreEnv(key, value) {
  if (typeof value === 'undefined') {
    delete process.env[key];
    return;
  }

  process.env[key] = value;
}

test('TotalWarPipeline 默认 reconThreshold 应优先读取环境变量 RECON_THRESHOLD', () => {
  const originalThreshold = process.env.RECON_THRESHOLD;

  try {
    process.env.RECON_THRESHOLD = '17';
    const options = parseArgs(['--season', '2025/2026', '--once']);
    assert.equal(options.reconThreshold, 17);
  } finally {
    if (originalThreshold === undefined) {
      delete process.env.RECON_THRESHOLD;
    } else {
      process.env.RECON_THRESHOLD = originalThreshold;
    }
  }
});

test('TotalWarPipeline 默认 reconThreshold 应在无环境变量时回退到 recon_config.json', () => {
  const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'total-war-config-'));
  const configPath = path.join(tempDir, 'recon_config.json');
  const originalThreshold = process.env.RECON_THRESHOLD;
  const originalConfigPath = process.env.RECON_CONFIG_PATH;

  fs.writeFileSync(configPath, JSON.stringify({
    automation: {
      total_war: {
        recon_threshold: 23
      }
    }
  }), 'utf8');

  try {
    delete process.env.RECON_THRESHOLD;
    process.env.RECON_CONFIG_PATH = configPath;
    assert.equal(getDefaultReconThreshold(), 23);

    const options = parseArgs(['--season', '2025/2026', '--once']);
    assert.equal(options.reconThreshold, 23);
  } finally {
    if (originalThreshold === undefined) {
      delete process.env.RECON_THRESHOLD;
    } else {
      process.env.RECON_THRESHOLD = originalThreshold;
    }

    if (originalConfigPath === undefined) {
      delete process.env.RECON_CONFIG_PATH;
    } else {
      process.env.RECON_CONFIG_PATH = originalConfigPath;
    }
  }
});

test('TotalWarPipeline 默认 reconLimit 应优先读取环境变量 RECON_LIMIT，并在缺省时回退到 recon_config.json', () => {
  const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'total-war-limit-config-'));
  const configPath = path.join(tempDir, 'recon_config.json');
  const originalLimit = process.env.RECON_LIMIT;
  const originalConfigPath = process.env.RECON_CONFIG_PATH;

  fs.writeFileSync(configPath, JSON.stringify({
    automation: {
      total_war: {
        recon_limit: 8000
      }
    }
  }), 'utf8');

  try {
    delete process.env.RECON_LIMIT;
    process.env.RECON_CONFIG_PATH = configPath;
    assert.equal(getDefaultReconLimit(), 8000);

    const options = parseArgs(['--season', '2025/2026', '--once']);
    assert.equal(options.reconLimit, 8000);

    process.env.RECON_LIMIT = '3200';
    assert.equal(getDefaultReconLimit(), 3200);

    const overridden = parseArgs(['--season', '2025/2026', '--once']);
    assert.equal(overridden.reconLimit, 3200);
  } finally {
    if (originalLimit === undefined) {
      delete process.env.RECON_LIMIT;
    } else {
      process.env.RECON_LIMIT = originalLimit;
    }

    if (originalConfigPath === undefined) {
      delete process.env.RECON_CONFIG_PATH;
    } else {
      process.env.RECON_CONFIG_PATH = originalConfigPath;
    }
  }
});

test('TotalWarPipeline 日志轮转配置应优先读取环境变量，其次回退到 recon_config.json', () => {
  const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'total-war-log-config-'));
  const configPath = path.join(tempDir, 'recon_config.json');
  const originalConfigPath = process.env.RECON_CONFIG_PATH;
  const originalMaxBytes = process.env.TOTAL_WAR_LOG_MAX_BYTES;
  const originalRetainedFiles = process.env.TOTAL_WAR_LOG_RETAINED_FILES;

  fs.writeFileSync(configPath, JSON.stringify({
    automation: {
      total_war: {
        log_max_bytes: 2048,
        log_retained_files: 7
      }
    }
  }), 'utf8');

  try {
    process.env.RECON_CONFIG_PATH = configPath;
    delete process.env.TOTAL_WAR_LOG_MAX_BYTES;
    delete process.env.TOTAL_WAR_LOG_RETAINED_FILES;

    assert.deepEqual(getTotalWarLogSettings(), {
      maxBytes: 2048,
      retainedFiles: 7
    });

    process.env.TOTAL_WAR_LOG_MAX_BYTES = '4096';
    process.env.TOTAL_WAR_LOG_RETAINED_FILES = '3';

    assert.deepEqual(getTotalWarLogSettings(), {
      maxBytes: 4096,
      retainedFiles: 3
    });
  } finally {
    if (originalConfigPath === undefined) {
      delete process.env.RECON_CONFIG_PATH;
    } else {
      process.env.RECON_CONFIG_PATH = originalConfigPath;
    }

    if (originalMaxBytes === undefined) {
      delete process.env.TOTAL_WAR_LOG_MAX_BYTES;
    } else {
      process.env.TOTAL_WAR_LOG_MAX_BYTES = originalMaxBytes;
    }

    if (originalRetainedFiles === undefined) {
      delete process.env.TOTAL_WAR_LOG_RETAINED_FILES;
    } else {
      process.env.TOTAL_WAR_LOG_RETAINED_FILES = originalRetainedFiles;
    }
  }
});

test('TotalWarPipeline 应从环境变量读取子进程监管超时参数', () => {
  const originalMaxRuntime = process.env.TOTAL_WAR_MAX_RUNTIME_MS;
  const originalKillGrace = process.env.TOTAL_WAR_KILL_GRACE_MS;

  try {
    process.env.TOTAL_WAR_MAX_RUNTIME_MS = '100';
    process.env.TOTAL_WAR_KILL_GRACE_MS = '25';

    const options = parseArgs(['--season', '2025/2026', '--once']);
    assert.equal(options.maxRuntimeMs, 100);
    assert.equal(options.killGraceMs, 25);
  } finally {
    if (originalMaxRuntime === undefined) {
      delete process.env.TOTAL_WAR_MAX_RUNTIME_MS;
    } else {
      process.env.TOTAL_WAR_MAX_RUNTIME_MS = originalMaxRuntime;
    }

    if (originalKillGrace === undefined) {
      delete process.env.TOTAL_WAR_KILL_GRACE_MS;
    } else {
      process.env.TOTAL_WAR_KILL_GRACE_MS = originalKillGrace;
    }
  }
});

test('TotalWarPipeline 应在配置与环境变量无效时回退到安全默认值', () => {
  const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'total-war-default-fallback-'));
  const configPath = path.join(tempDir, 'recon_config.json');
  const snapshot = {
    RECON_CONFIG_PATH: process.env.RECON_CONFIG_PATH,
    RECON_LIMIT: process.env.RECON_LIMIT,
    RECON_THRESHOLD: process.env.RECON_THRESHOLD,
    TOTAL_WAR_LOG_MAX_BYTES: process.env.TOTAL_WAR_LOG_MAX_BYTES,
    TOTAL_WAR_LOG_RETAINED_FILES: process.env.TOTAL_WAR_LOG_RETAINED_FILES
  };

  fs.writeFileSync(configPath, JSON.stringify({
    automation: {
      total_war: {
        recon_limit: 0,
        recon_threshold: 0,
        log_max_bytes: 0,
        log_retained_files: 0
      }
    }
  }), 'utf8');

  try {
    process.env.RECON_CONFIG_PATH = configPath;
    process.env.RECON_LIMIT = '0';
    process.env.RECON_THRESHOLD = '0';
    process.env.TOTAL_WAR_LOG_MAX_BYTES = '0';
    process.env.TOTAL_WAR_LOG_RETAINED_FILES = '0';

    assert.equal(getDefaultReconThreshold(), 50);
    assert.equal(getDefaultReconLimit(), 50);
    assert.deepEqual(getTotalWarLogSettings(), {
      maxBytes: 100 * 1024 * 1024,
      retainedFiles: 5
    });
  } finally {
    for (const [key, value] of Object.entries(snapshot)) {
      restoreEnv(key, value);
    }
  }
});

test('TotalWarPipeline 应从 recon_config.json 读取 defer/ttl/preflight/skip 默认值，并允许环境变量覆盖', () => {
  const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'total-war-runtime-defaults-'));
  const configPath = path.join(tempDir, 'recon_config.json');
  const snapshot = {
    RECON_CONFIG_PATH: process.env.RECON_CONFIG_PATH,
    RECON_SESSION_BUFFER_TTL_MS: process.env.RECON_SESSION_BUFFER_TTL_MS,
    RECON_PREFLIGHT_WAIT_MS: process.env.RECON_PREFLIGHT_WAIT_MS
  };

  fs.writeFileSync(configPath, JSON.stringify({
    automation: {
      total_war: {
        recon_limit: 120,
        recon_threshold: 9,
        recon_defer_cooldown_ms: 4321,
        recon_session_buffer_ttl_ms: 8765,
        recon_preflight_wait_ms: 250,
        skip_list: ['J1', 'J2']
      }
    }
  }), 'utf8');

  try {
    process.env.RECON_CONFIG_PATH = configPath;
    delete process.env.RECON_SESSION_BUFFER_TTL_MS;
    delete process.env.RECON_PREFLIGHT_WAIT_MS;

    const configDriven = parseArgs(['--season', '2025/2026', '--once']);
    assert.equal(configDriven.reconDeferCooldownMs, 4321);
    assert.equal(configDriven.reconSessionBufferTtlMs, 8765);
    assert.equal(configDriven.reconPreflightWaitMs, 250);
    assert.deepEqual(configDriven.skipLeagues, ['J1', 'J2']);

    process.env.RECON_SESSION_BUFFER_TTL_MS = '9100';
    process.env.RECON_PREFLIGHT_WAIT_MS = '0';

    const envDriven = parseArgs(['--season', '2025/2026', '--once']);
    assert.equal(envDriven.reconSessionBufferTtlMs, 9100);
    assert.equal(envDriven.reconPreflightWaitMs, 0);
  } finally {
    for (const [key, value] of Object.entries(snapshot)) {
      restoreEnv(key, value);
    }
  }
});

test('TotalWarPipeline parseArgs 应规范化赛季、合并联赛并处理主并发别名', () => {
  const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'total-war-parse-args-'));
  const configPath = path.join(tempDir, 'recon_config.json');
  const originalConfigPath = process.env.RECON_CONFIG_PATH;

  fs.writeFileSync(configPath, JSON.stringify({
    automation: {
      total_war: {
        skip_list: ['J1', 'J2']
      }
    }
  }), 'utf8');

  try {
    process.env.RECON_CONFIG_PATH = configPath;

    const merged = parseArgs([
      'node',
      'scripts/ops/total_war_pipeline.js',
      '--season',
      '2025-2026',
      '--concurrency',
      '8',
      '--task-stage',
      'harvest',
      '--skip-leagues',
      'J2, EPL, , LaLiga',
      '--skip-leagues=LaLiga,Bundesliga'
    ]);

    assert.equal(merged.dbSeason, '2025/2026');
    assert.equal(merged.reconSeason, '2025-2026');
    assert.equal(merged.harvestConcurrency, 8);
    assert.equal(merged.reconConcurrency, 8);
    assert.equal(merged.taskStage, 'harvest');
    assert.deepEqual(merged.skipLeagues, ['J1', 'J2', 'EPL', 'LaLiga', 'Bundesliga']);

    const includeAll = parseArgs([
      '--season',
      '2025/2026',
      '--include-all-leagues',
      '--concurrency',
      '0',
      '--threshold',
      'bad'
    ]);

    assert.deepEqual(includeAll.skipLeagues, []);
    assert.equal(includeAll.harvestConcurrency, 10);
    assert.equal(includeAll.reconConcurrency, 5);
    assert.equal(includeAll.threshold, null);
  } finally {
    restoreEnv('RECON_CONFIG_PATH', originalConfigPath);
  }
});

test('TotalWarPipeline parseArgs 应在参数非法时抛错或回退默认值', () => {
  const originalConfigPath = process.env.RECON_CONFIG_PATH;
  delete process.env.RECON_CONFIG_PATH;

  try {
    const options = parseArgs([
      '--season',
      '2025/2026',
      '--loop-ms',
      'abc',
      '--recon-limit',
      'NaN',
      '--failure-limit=0'
    ]);

    assert.equal(options.loopMs, 60_000);
    assert.equal(options.reconLimit, getDefaultReconLimit());
    assert.equal(options.failureLimit, 3);
    assert.throws(() => parseArgs(['--season', '2025/2026', '--task-stage', 'invalid']), /不支持的 --task-stage/);
    assert.throws(() => parseArgs(['--season']), /参数 --season 缺少取值/);
  } finally {
    restoreEnv('RECON_CONFIG_PATH', originalConfigPath);
  }
});

test('TotalWarPipeline parseArgs 应在 --help 时输出帮助并退出 0', () => {
  const originalExit = process.exit;
  const originalLog = console.log;
  const logs = [];

  process.exit = (code) => {
    throw new Error(`EXIT:${code}`);
  };
  console.log = (message) => {
    logs.push(String(message));
  };

  try {
    assert.throws(() => parseArgs(['--help']), /EXIT:0/);
    assert.ok(logs.some((line) => line.includes('TOTAL WAR PIPELINE')));
  } finally {
    process.exit = originalExit;
    console.log = originalLog;
  }
});

test('TotalWarPipeline parseArgs 应在缺少 season 时输出错误并退出 1', () => {
  const originalExit = process.exit;
  const originalLog = console.log;
  const originalError = console.error;
  const logs = [];
  const errors = [];

  process.exit = (code) => {
    throw new Error(`EXIT:${code}`);
  };
  console.log = (message) => {
    logs.push(String(message));
  };
  console.error = (message) => {
    errors.push(String(message));
  };

  try {
    assert.throws(() => parseArgs([]), /EXIT:1/);
    assert.ok(errors.some((line) => line.includes('--season 参数是必需的')));
    assert.ok(logs.some((line) => line.includes('TOTAL WAR PIPELINE')));
  } finally {
    process.exit = originalExit;
    console.log = originalLog;
    console.error = originalError;
  }
});
