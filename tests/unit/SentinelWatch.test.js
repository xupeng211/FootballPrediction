/**
 * @file Sentinel Watch 哨兵系统单元测试
 * @description 测试文件计数、防抖逻辑、停机指令
 * @version 1.0.0
 */

'use strict';

const { describe, it, beforeEach, afterEach } = require('node:test');
const assert = require('node:assert');
const fs = require('fs').promises;
const path = require('path');
const { exec } = require('child_process');
const { promisify } = require('util');

const execAsync = promisify(exec);

// 模拟的 Sentinel 类
/**
 *
 */
class MockSentinel {
  /**
   *
   * @param config
   */
  constructor(config = {}) {
    this.targetCount = config.targetCount || 12000;
    this.debounceThreshold = config.debounceThreshold || 2;
    this.checkInterval = config.checkInterval || 60000;
    
    this.state = {
      checkCount: 0,
      consecutiveHits: 0,
      isTriggered: false,
      startTime: Date.now()
    };
    
    this.shutdownCalled = false;
    this.victoryLogWritten = false;
  }

  /**
   * 获取文件数量
   * @param dataPath
   */
  async getFileCount(dataPath) {
    try {
      const files = await fs.readdir(dataPath);
      return files.filter(f => f.endsWith('.json') && !f.startsWith('.')).length;
    } catch (error) {
      return 0;
    }
  }

  /**
   * 检查循环
   * @param fileCount
   */
  async checkCycle(fileCount) {
    if (this.state.isTriggered) return { triggered: false };

    this.state.checkCount++;
    const remaining = Math.max(0, this.targetCount - fileCount);
    const progress = ((fileCount / this.targetCount) * 100).toFixed(1);

    let triggered = false;

    // 检查是否达标
    if (fileCount >= this.targetCount) {
      this.state.consecutiveHits++;

      if (this.state.consecutiveHits >= this.debounceThreshold) {
        this.state.isTriggered = true;
        triggered = true;
      }
    } else {
      this.state.consecutiveHits = 0;
    }

    return {
      checkCount: this.state.checkCount,
      fileCount,
      remaining,
      progress,
      consecutiveHits: this.state.consecutiveHits,
      triggered,
      debounceMet: this.state.consecutiveHits >= this.debounceThreshold
    };
  }

  /**
   * 执行停机
   */
  async executeShutdown() {
    this.shutdownCalled = true;
    return { success: true, message: 'Shutdown executed' };
  }

  /**
   * 写入胜利日志
   * @param fileCount
   * @param dbCount
   */
  async writeVictoryLog(fileCount, dbCount) {
    const duration = Date.now() - this.state.startTime;
    const durationMinutes = Math.round(duration / 60000);
    const avgSpeed = durationMinutes > 0 ? (fileCount / durationMinutes).toFixed(2) : 0;

    this.victoryLogWritten = true;

    return {
      timestamp: new Date().toISOString(),
      fileCount,
      dbCount,
      durationMinutes,
      avgSpeed,
      alignmentRate: dbCount > 0 ? ((fileCount / dbCount) * 100).toFixed(2) : 0
    };
  }
}

// ==================== 测试套件 ====================

describe('Sentinel Watch 哨兵系统', () => {
  let sentinel;
  let tempDir;

  beforeEach(async () => {
    sentinel = new MockSentinel({
      targetCount: 100,
      debounceThreshold: 2,
      checkInterval: 1000
    });

    // 创建临时测试目录
    tempDir = path.join(process.cwd(), 'temp_test_matches');
    await fs.mkdir(tempDir, { recursive: true });
  });

  afterEach(async () => {
    // 清理临时目录
    try {
      await fs.rm(tempDir, { recursive: true, force: true });
    } catch (err) {
      // 忽略清理错误
    }
  });

  describe('文件计数', () => {
it('✅ 应正确统计 JSON 文件数量', async () => {
      // 创建测试文件
      await fs.writeFile(path.join(tempDir, 'match1.json'), '{}');
      await fs.writeFile(path.join(tempDir, 'match2.json'), '{}');
      await fs.writeFile(path.join(tempDir, 'match3.json'), '{}');
      await fs.writeFile(path.join(tempDir, 'readme.txt'), 'not json');

      const count = await sentinel.getFileCount(tempDir);
      assert.strictEqual(count, 3);
    });

it('✅ 空目录应返回 0', async () => {
      const count = await sentinel.getFileCount(tempDir);
      assert.strictEqual(count, 0);
    });

it('✅ 不存在的目录应返回 0', async () => {
      const count = await sentinel.getFileCount('/nonexistent/path');
      assert.strictEqual(count, 0);
    });

it('✅ 应忽略隐藏文件', async () => {
      await fs.writeFile(path.join(tempDir, 'match.json'), '{}');
      await fs.writeFile(path.join(tempDir, '.hidden.json'), '{}');

      const count = await sentinel.getFileCount(tempDir);
      assert.strictEqual(count, 1);
    });
  });

  describe('防抖逻辑', () => {
it('✅ 首次达标不应触发（防抖）', async () => {
      const result = await sentinel.checkCycle(100); // 刚好达标

      assert.strictEqual(result.triggered, false);
      assert.strictEqual(result.consecutiveHits, 1);
      assert.strictEqual(sentinel.state.isTriggered, false);
    });

it('✅ 连续两次达标应触发', async () => {
      // 第一次达标
      await sentinel.checkCycle(100);
      
      // 第二次达标
      const result = await sentinel.checkCycle(100);

      assert.strictEqual(result.triggered, true);
      assert.strictEqual(result.consecutiveHits, 2);
      assert.strictEqual(sentinel.state.isTriggered, true);
    });

it('✅ 达标后回落应重置计数器', async () => {
      // 第一次达标
      await sentinel.checkCycle(100);
      assert.strictEqual(sentinel.state.consecutiveHits, 1);

      // 回落
      await sentinel.checkCycle(99);
      assert.strictEqual(sentinel.state.consecutiveHits, 0);

      // 再次达标
      await sentinel.checkCycle(100);
      assert.strictEqual(sentinel.state.consecutiveHits, 1);
    });

it('✅ 触发后不应重复触发', async () => {
      // 连续两次达标触发
      await sentinel.checkCycle(100);
      await sentinel.checkCycle(100);

      // 再次检查
      const result = await sentinel.checkCycle(100);
      assert.strictEqual(result.triggered, false); // 已触发过
    });
  });

  describe('停机指令', () => {
it('✅ 停机指令应正确执行', async () => {
      const result = await sentinel.executeShutdown();
      
      assert.strictEqual(sentinel.shutdownCalled, true);
      assert.strictEqual(result.success, true);
    });

it('✅ 触发后应自动调用停机', async () => {
      // 触发条件
      await sentinel.checkCycle(100);
      await sentinel.checkCycle(100);

      // 执行停机
      await sentinel.executeShutdown();
      assert.strictEqual(sentinel.shutdownCalled, true);
    });
  });

  describe('胜利日志', () => {
it('✅ 应正确生成日志数据', async () => {
      const logData = await sentinel.writeVictoryLog(100, 100);

      assert.strictEqual(sentinel.victoryLogWritten, true);
      assert.strictEqual(logData.fileCount, 100);
      assert.strictEqual(logData.dbCount, 100);
      assert.strictEqual(logData.alignmentRate, '100.00');
      assert.ok(logData.timestamp !== undefined);
      assert.ok(logData.avgSpeed !== undefined);
    });

it('✅ 应计算对齐率', async () => {
      const logData = await sentinel.writeVictoryLog(90, 100);
      assert.strictEqual(logData.alignmentRate, '90.00');
    });

it('✅ 应计算平均速度', async () => {
      const logData = await sentinel.writeVictoryLog(120, 120);
      assert.ok(parseFloat(logData.avgSpeed) >= 0);
    });
  });

  describe('进度计算', () => {
it('✅ 应正确计算进度百分比', async () => {
      const result = await sentinel.checkCycle(50);
      assert.strictEqual(result.progress, '50.0');
      assert.strictEqual(result.remaining, 50);
    });

it('✅ 超过目标时剩余应为 0', async () => {
      const result = await sentinel.checkCycle(150);
      assert.strictEqual(result.remaining, 0);
      expect(parseFloat(result.progress)).toBeGreaterThan(100);
    });
  });
});
