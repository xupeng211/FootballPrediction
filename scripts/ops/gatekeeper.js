#!/usr/bin/env node
/**
 * Gatekeeper - 工业级质量门禁系统
 * ================================
 *
 * 职责: 自动化质量准入标准验证
 * - 单元测试通过率 100%
 * - 代码覆盖率 ≥ 80% (Lines/Branches)
 * - ESLint 零错误
 * - 架构边界检查
 *
 * @module scripts/ops/gatekeeper
 * @version V11.6-INDUSTRIAL
 */

'use strict';

const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

class Gatekeeper {
  constructor() {
    this.results = {
      tests: { passed: false, message: '' },
      coverage: { passed: false, message: '', metrics: {} },
      lint: { passed: false, message: '' },
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

    console.log(`[${timestamp}] ${prefix} ${message}`);
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
    this.log('info', '【门禁 1/4】执行单元测试...');

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
    this.log('info', '【门禁 2/4】验证代码覆盖率...');

    const coveragePath = path.join(process.cwd(), 'coverage/coverage-summary.json');

    if (!fs.existsSync(coveragePath)) {
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

      const threshold = 80;
      const failed = [];

      if (metrics.lines < threshold) failed.push(`Lines: ${metrics.lines.toFixed(2)}%`);
      if (metrics.branches < threshold) failed.push(`Branches: ${metrics.branches.toFixed(2)}%`);

      if (failed.length > 0) {
        this.results.coverage.passed = false;
        this.results.coverage.message = `覆盖率不足 (阈值: ${threshold}%) - ${failed.join(', ')}`;
        this.log('error', `代码覆盖率: FAIL - ${this.results.coverage.message}`);
        this.exitCode = 1;
      } else {
        this.results.coverage.passed = true;
        this.results.coverage.message = `Lines: ${metrics.lines.toFixed(2)}%, Branches: ${metrics.branches.toFixed(2)}%`;
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
    this.log('info', '【门禁 3/4】执行 ESLint 检查...');

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

  async checkArchitecture() {
    this.log('info', '【门禁 4/4】验证架构边界...');

    const violations = [];

    const reconEngineImpl = path.join(process.cwd(), 'src/infrastructure/recon/ReconEngineImpl.js');
    if (fs.existsSync(reconEngineImpl)) {
      const content = fs.readFileSync(reconEngineImpl, 'utf8');
      if (content.includes("require('../services/L1ConfigManager')")) {
        violations.push('ReconEngineImpl 直接依赖 L1ConfigManager (跨层依赖)');
      }
    }

    const srcFiles = this.exec('find src -name "*.js" -o -name "*.py"', { silent: true });
    if (srcFiles.success) {
      const files = srcFiles.output.trim().split('\n');
      const consoleLogCount = files.reduce((count, file) => {
        if (fs.existsSync(file)) {
          const content = fs.readFileSync(file, 'utf8');
          const matches = content.match(/console\.(log|info|warn|error)/g);
          return count + (matches ? matches.length : 0);
        }
        return count;
      }, 0);

      if (consoleLogCount > 50) {
        violations.push(`发现 ${consoleLogCount} 处 console.log (建议使用结构化日志)`);
      }
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
    console.log('\n' + '='.repeat(60));
    console.log('🎯 Gatekeeper 质量门禁报告');
    console.log('='.repeat(60));

    const checks = [
      { name: '单元测试', result: this.results.tests },
      { name: '代码覆盖率', result: this.results.coverage },
      { name: 'ESLint', result: this.results.lint },
      { name: '架构边界', result: this.results.architecture }
    ];

    checks.forEach(({ name, result }) => {
      const status = result.passed ? '✓ PASS' : '✗ FAIL';
      console.log(`${status.padEnd(10)} | ${name.padEnd(15)} | ${result.message}`);
    });

    console.log('='.repeat(60));

    const allPassed = checks.every(c => c.result.passed);
    if (allPassed) {
      console.log('🎉 【准予准入】所有质量门禁检查通过！');
      console.log('='.repeat(60));
      return 0;
    } else {
      console.log('🚫 【拒绝准入】存在未通过的质量检查');
      console.log('='.repeat(60));
      return 1;
    }
  }

  async run() {
    console.log('🚀 启动 Gatekeeper 质量门禁系统...\n');

    await this.checkTests();
    await this.checkCoverage();
    await this.checkLint();
    await this.checkArchitecture();

    const exitCode = this.printSummary();
    process.exit(exitCode);
  }
}

if (require.main === module) {
  const gatekeeper = new Gatekeeper();
  gatekeeper.run().catch(error => {
    console.error('Gatekeeper 执行失败:', error);
    process.exit(1);
  });
}

module.exports = Gatekeeper;
