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
