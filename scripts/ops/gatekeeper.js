#!/usr/bin/env node
/**
 * Gatekeeper - 工业级质量门禁系统
 * ================================
 *
 * 职责: 自动化质量准入标准验证
 * - 单元测试通过率 100%
 * - 代码覆盖率 ≥ 80% (Lines) / 81% (Branches)
 * - ESLint 零错误
 * - 冷启动蓝图可回放
 * - 架构边界检查
 *
 * @module scripts/ops/gatekeeper
 * @version V11.6-INDUSTRIAL
 */

'use strict';

const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');
const { TitanLogger } = require('../../src/infrastructure/utils/TitanLogger');
const { runColdStartBlueprintCheck } = require('./helpers/dbBlueprint');

function writeToStream(stream, message = '') {
  const normalizedMessage = String(message);
  const payload = normalizedMessage.endsWith('\n')
    ? normalizedMessage
    : `${normalizedMessage}\n`;
  if (stream && typeof stream.write === 'function') {
    stream.write(payload);
    return;
  }

  process.stdout.write(payload);
}

function countConsoleStatements(targetPath) {
  if (!targetPath || !fs.existsSync(targetPath)) {
    return 0;
  }

  const stat = fs.statSync(targetPath);
  if (stat.isFile()) {
    const content = fs.readFileSync(targetPath, 'utf8');
    const matches = content.match(/console\.(log|info|warn|error)/g);
    return matches ? matches.length : 0;
  }

  if (!stat.isDirectory()) {
    return 0;
  }

  return fs.readdirSync(targetPath).reduce((count, entry) => (
    count + countConsoleStatements(path.join(targetPath, entry))
  ), 0);
}

class Gatekeeper {
  constructor(options = {}) {
    this.stdout = options.stdout || process.stdout;
    this.stderr = options.stderr || process.stderr;
    this.logger = options.logger || new TitanLogger({
      serviceName: 'gatekeeper',
      enableFileLogging: false
    });
    this.results = {
      tests: { passed: false, message: '' },
      coverage: { passed: false, message: '', metrics: {} },
      lint: { passed: false, message: '' },
      coldStart: { passed: false, message: '' },
      architecture: { passed: false, message: '' }
    };
    this.exitCode = 0;
  }

  log(level, message) {
    const timestamp = new Date().toISOString();
    const prefix = {
      info: '✓',
      warn: '⚠',
      error: '✗',
      success: '🎯'
    }[level] || 'ℹ';

    const payload = `[${timestamp}] ${prefix} ${message}`;
    const logMethod = typeof this.logger?.[level] === 'function'
      ? this.logger[level].bind(this.logger)
      : this.logger.info.bind(this.logger);
    logMethod('gatekeeper_status', { gateMessage: message, gatePrefix: prefix, gateTimestamp: timestamp });
    writeToStream(this.stdout, payload);
  }

  exec(command, options = {}) {
    try {
      const output = execSync(command, {
        encoding: 'utf8',
        stdio: options.silent ? 'pipe' : 'inherit',
        ...options
      });
      return { success: true, output };
    } catch (error) {
      return {
        success: false,
        output: error.stdout || error.stderr || error.message,
        code: error.status
      };
    }
  }

  async checkTests() {
    this.log('info', '【门禁 1/5】执行单元测试...');

    const result = this.exec('npm run test:unit', { silent: false });

    if (result.success) {
      this.results.tests.passed = true;
      this.results.tests.message = '所有单元测试通过';
      this.log('success', '单元测试: PASS');
    } else {
      this.results.tests.passed = false;
      this.results.tests.message = `测试失败 (退出码: ${result.code})`;
      this.log('error', `单元测试: FAIL - ${this.results.tests.message}`);
      this.exitCode = 1;
    }
  }

  async checkCoverage() {
    this.log('info', '【门禁 2/5】验证代码覆盖率...');

    const coverageCandidates = [
      path.join(process.cwd(), 'reports/coverage/node/coverage-summary.json'),
      path.join(process.cwd(), 'coverage/coverage-summary.json')
    ];
    const coveragePath = coverageCandidates.find(candidate => fs.existsSync(candidate));
    const thresholds = {
      lines: Number.parseFloat(process.env.GATEKEEPER_LINES_THRESHOLD || '80'),
      branches: Number.parseFloat(process.env.GATEKEEPER_BRANCH_THRESHOLD || '81')
    };

    if (!coveragePath) {
      this.results.coverage.passed = false;
      this.results.coverage.message = '覆盖率报告不存在，请先运行 npm run test:coverage';
      this.log('warn', this.results.coverage.message);
      return;
    }

    try {
      const coverageData = JSON.parse(fs.readFileSync(coveragePath, 'utf8'));
      const total = coverageData.total;

      const metrics = {
        lines: total.lines.pct,
        branches: total.branches.pct,
        functions: total.functions.pct,
        statements: total.statements.pct
      };

      this.results.coverage.metrics = metrics;

      const failed = [];

      if (metrics.lines < thresholds.lines) {
        failed.push(`Lines: ${metrics.lines.toFixed(2)}% < ${thresholds.lines.toFixed(2)}%`);
      }
      if (metrics.branches < thresholds.branches) {
        failed.push(`Branches: ${metrics.branches.toFixed(2)}% < ${thresholds.branches.toFixed(2)}%`);
      }

      if (failed.length > 0) {
        this.results.coverage.passed = false;
        this.results.coverage.message = `覆盖率不足 - ${failed.join(', ')}`;
        this.log('error', `代码覆盖率: FAIL - ${this.results.coverage.message}`);
        this.exitCode = 1;
      } else {
        this.results.coverage.passed = true;
        this.results.coverage.message = `覆盖率达标 - Lines: ${metrics.lines.toFixed(2)}%, Branches: ${metrics.branches.toFixed(2)}%`;
        this.log('success', `代码覆盖率: PASS - ${this.results.coverage.message}`);
      }
    } catch (error) {
      this.results.coverage.passed = false;
      this.results.coverage.message = `解析覆盖率报告失败: ${error.message}`;
      this.log('error', this.results.coverage.message);
      this.exitCode = 1;
    }
  }

  async checkLint() {
    this.log('info', '【门禁 3/5】执行 ESLint 检查...');

    const result = this.exec('npm run lint', { silent: true });

    if (result.success) {
      this.results.lint.passed = true;
      this.results.lint.message = 'ESLint 检查通过';
      this.log('success', 'ESLint: PASS');
    } else {
      this.results.lint.passed = false;
      this.results.lint.message = 'ESLint 发现错误';
      this.log('error', `ESLint: FAIL - ${this.results.lint.message}`);
      this.log('warn', '运行 npm run lint:fix 自动修复部分问题');
      this.exitCode = 1;
    }
  }

  async checkColdStart() {
    this.log('info', '【门禁 4/5】执行 [GATE-COLD-START] 冷启动蓝图校验...');

    try {
      const result = await runColdStartBlueprintCheck();
      this.results.coldStart.passed = true;
      this.results.coldStart.message = `空库回放成功 - 临时库 ${result.databaseName}，蓝图 ${result.appliedFiles.length} 个文件`;
      this.log('success', `[GATE-COLD-START] PASS - ${this.results.coldStart.message}`);
    } catch (error) {
      this.results.coldStart.passed = false;
      this.results.coldStart.message = `冷启动蓝图失败: ${error.message}`;
      this.log('error', `[GATE-COLD-START] FAIL - ${this.results.coldStart.message}`);
      this.exitCode = 1;
    }
  }

  async checkArchitecture() {
    this.log('info', '【门禁 5/5】验证架构边界...');

    const violations = [];

    const reconEngineImpl = path.join(process.cwd(), 'src/infrastructure/recon/ReconEngineImpl.js');
    if (fs.existsSync(reconEngineImpl)) {
      const content = fs.readFileSync(reconEngineImpl, 'utf8');
      if (content.includes("require('../services/L1ConfigManager')")) {
        violations.push('ReconEngineImpl 直接依赖 L1ConfigManager (跨层依赖)');
      }
    }

    const criticalPaths = [
      path.join(process.cwd(), 'src/infrastructure/recon'),
      path.join(process.cwd(), 'scripts/ops/total_war_pipeline.js')
    ];
    const consoleLogCount = criticalPaths.reduce((count, targetPath) => (
      count + countConsoleStatements(targetPath)
    ), 0);

    if (consoleLogCount > 0) {
      violations.push(`关键路径仍存在 ${consoleLogCount} 处 console 输出`);
    }

    if (violations.length > 0) {
      this.results.architecture.passed = false;
      this.results.architecture.message = violations.join('; ');
      this.log('warn', `架构检查: WARN - ${this.results.architecture.message}`);
    } else {
      this.results.architecture.passed = true;
      this.results.architecture.message = '架构边界检查通过';
      this.log('success', '架构检查: PASS');
    }
  }

  printSummary() {
    writeToStream(this.stdout, `\n${'='.repeat(60)}`);
    writeToStream(this.stdout, '🎯 Gatekeeper 质量门禁报告');
    writeToStream(this.stdout, '='.repeat(60));

    const checks = [
      { name: '单元测试', result: this.results.tests },
      { name: '代码覆盖率', result: this.results.coverage },
      { name: 'ESLint', result: this.results.lint },
      { name: '冷启动蓝图', result: this.results.coldStart },
      { name: '架构边界', result: this.results.architecture }
    ];

    checks.forEach(({ name, result }) => {
      const status = result.passed ? '✓ PASS' : '✗ FAIL';
      writeToStream(this.stdout, `${status.padEnd(10)} | ${name.padEnd(15)} | ${result.message}`);
    });

    writeToStream(this.stdout, '='.repeat(60));

    const allPassed = checks.every(c => c.result.passed);
    if (allPassed) {
      writeToStream(this.stdout, '🎉 【准予准入】所有质量门禁检查通过！');
      writeToStream(this.stdout, '='.repeat(60));
      return 0;
    } else {
      writeToStream(this.stdout, '🚫 【拒绝准入】存在未通过的质量检查');
      writeToStream(this.stdout, '='.repeat(60));
      return 1;
    }
  }

  async run() {
    writeToStream(this.stdout, '🚀 启动 Gatekeeper 质量门禁系统...\n');

    await this.checkTests();
    await this.checkCoverage();
    await this.checkLint();
    await this.checkColdStart();
    await this.checkArchitecture();

    const exitCode = this.printSummary();
    process.exit(exitCode);
  }
}

if (require.main === module) {
  const gatekeeper = new Gatekeeper();
  gatekeeper.run().catch(error => {
    gatekeeper.logger.error('gatekeeper_run_failed', {
      error: error.message,
      stack: error.stack
    });
    writeToStream(gatekeeper.stderr, `Gatekeeper 执行失败: ${error.message}`);
    process.exit(1);
  });
}

module.exports = Gatekeeper;
