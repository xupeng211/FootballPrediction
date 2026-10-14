'use strict';
// lifecycle: permanent — Node 测试批次的临时数据分配、worker 环境及整体清理。

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

// 原生 runner 在主进程的 TMPDIR 中汇总覆盖率；只有测试 worker 将普通
// 夹具切回仓库外。NODE_V8_COVERAGE 保持原值，所有子进程数据仍参与汇总。
if (process.env.NODE_TEST_CONTEXT === 'child-v8' && process.env.FP_TEST_TMP_DIR) {
  process.env.TMPDIR = path.join(process.env.FP_TEST_TMP_DIR, 'tmp');
}

/**
 * 分配彼此独立的外部夹具目录和原生覆盖率目录。
 * @param {boolean} coverage
 * @param {string} coverageReportDir
 * @returns {{testTempDir: string, nodeTempDir: string, cleanup: Function}}
 */
function createTestTempDirs(coverage, coverageReportDir) {
  const testTempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'footballprediction-node-tests-'));
  const roots = [testTempDir];
  const cleanup = () => {
    for (const root of roots) fs.rmSync(root, { recursive: true, force: true });
  };
  try {
    let nodeTempDir = path.join(testTempDir, 'tmp');
    fs.mkdirSync(nodeTempDir);
    if (coverage) {
      fs.mkdirSync(coverageReportDir, { recursive: true });
      const coverageTempDir = fs.mkdtempSync(path.join(coverageReportDir, 'footballprediction-coverage-'));
      roots.push(coverageTempDir);
      nodeTempDir = path.join(coverageTempDir, 'tmp');
      fs.mkdirSync(nodeTempDir);
    }
    return { testTempDir, nodeTempDir, cleanup };
  } catch (error) {
    cleanup();
    throw error;
  }
}

module.exports = { createTestTempDirs };
