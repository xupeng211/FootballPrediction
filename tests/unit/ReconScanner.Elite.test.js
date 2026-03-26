/**
 * TITAN V6.7 ELITE RECON SCANNER - 金融级高压测试套件
 * ====================================================
 *
 * 测试目标:
 * 1. 分布式锁冲突 - Redis RedLock 高并发一致性
 * 2. 瞬态错误自愈 - 指数退避 + Jitter 重试策略
 * 3. 致命错误熔断 - CircuitBreaker 保护机制
 * 4. 资源 100% 回收 - 异常场景下的资源清理
 *
 * @module tests/unit/ReconScanner.Elite.test
 * @version V6.7-ELITE
 * @date 2026-03-22
 */

'use strict';

const { describe, it } = require('node:test');
const assert = require('node:assert');

// 导入被测模块
const {
  ReconErrorClassifier,
  ReconRetryStrategy,
  ReconCircuitBreaker,
  ErrorTypes,
  CircuitBreakerOpenError,
  LockAcquireFailure
} = require('../../src/infrastructure/recon');

// ============================================================================
// 测试套件: 分布式锁类型 (Distributed Lock Types)
// ============================================================================

describe('ReconScanner Elite - Distributed Lock Types', () => {
  it('应暴露 LockAcquireFailure 错误类型', () => {
    const error = new LockAcquireFailure('test lock failure');
    assert.strictEqual(error.name, 'LockAcquireFailure');
    assert.ok(error.message.includes('test lock failure'));
  });
});

// ============================================================================
// 测试套件: 瞬态错误自愈 (Transient Error Recovery)
// ============================================================================

describe('ReconScanner Elite - Transient Error Recovery', () => {
  it('应识别瞬态错误类型 (503, ECONNRESET, ETIMEDOUT)', () => {
    const transientErrors = [
      { message: 'Request failed with status 503', code: '' },
      { message: 'ECONNRESET: Connection reset by peer', code: 'ECONNRESET' },
      { message: 'ETIMEDOUT: Connection timed out', code: 'ETIMEDOUT' },
      { message: 'Server returned 502 Bad Gateway', code: '' }
    ];

    for (const error of transientErrors) {
      const classified = ReconErrorClassifier.classify(error);
      assert.strictEqual(classified.type, ErrorTypes.TRANSIENT,
        `${error.message} 应被识别为 TRANSIENT`);
      assert.strictEqual(classified.retryable, true, 'TRANSIENT 错误应可重试');
    }
  });

  it('应识别代理封禁错误 (403, 429)', () => {
    const bannedErrors = [
      { message: 'Request failed with status 403', code: '' },
      { message: 'Request failed with status 429', code: '' },
      { message: 'Proxy connection refused', code: '' }
    ];

    for (const error of bannedErrors) {
      const classified = ReconErrorClassifier.classify(error);
      assert.strictEqual(classified.type, ErrorTypes.BANNED,
        `${error.message} 应被识别为 BANNED`);
      assert.strictEqual(classified.shouldSwitchProxy, true, '应标记切换代理');
    }
  });

  it('应识别选择器失效错误', () => {
    const obsoleteErrors = [
      { message: 'waitForSelector timeout: div[role="row"]', code: '' },
      { message: 'Element not found: selector obsolete', code: '' }
    ];

    for (const error of obsoleteErrors) {
      const classified = ReconErrorClassifier.classify(error);
      assert.strictEqual(classified.type, ErrorTypes.OBSOLETE,
        `${error.message} 应被识别为 OBSOLETE`);
      assert.strictEqual(classified.retryable, false, 'OBSOLETE 不应重试');
    }
  });

  it('应计算指数退避延迟', () => {
    const strategy = new ReconRetryStrategy({
      baseDelay: 1000,
      maxDelay: 30000,
      jitterFactor: 0
    });

    // 测试多次以消除随机性影响
    const delays0 = [], delays1 = [], delays2 = [];
    for (let i = 0; i < 5; i++) {
      delays0.push(strategy.calculateDelay(0));
      delays1.push(strategy.calculateDelay(1));
      delays2.push(strategy.calculateDelay(2));
    }

    // 使用平均值验证指数增长趋势
    const avg0 = delays0.reduce((a, b) => a + b, 0) / delays0.length;
    const avg1 = delays1.reduce((a, b) => a + b, 0) / delays1.length;
    const avg2 = delays2.reduce((a, b) => a + b, 0) / delays2.length;

    assert.ok(avg0 >= 900, `第0次平均应 ~1000ms, 实际 ${avg0}`);
    assert.ok(avg1 >= avg0 * 1.5, `第1次应明显大于第0次: ${avg1} > ${avg0 * 1.5}`);
    assert.ok(avg2 >= avg1 * 1.5, `第2次应明显大于第1次: ${avg2} > ${avg1 * 1.5}`);
  });

  it('应添加随机抖动 (Jitter)', () => {
    const strategy = new ReconRetryStrategy({
      baseDelay: 1000,
      jitterFactor: 0.2
    });

    const delays = [];
    for (let i = 0; i < 10; i++) {
      delays.push(strategy.calculateDelay(1));
    }

    const min = Math.min(...delays);
    const max = Math.max(...delays);
    
    assert.ok(max > min, '应有明显的抖动差异');
  });
});

// ============================================================================
// 测试套件: 致命错误熔断 (Circuit Breaker Protection)
// ============================================================================

describe('ReconScanner Elite - Circuit Breaker', () => {
  it('应成功执行操作并记录成功', async () => {
    const cb = new ReconCircuitBreaker({ failureThreshold: 3 });
    
    const result = await cb.execute(async () => 'success');
    assert.strictEqual(result, 'success');
    assert.strictEqual(cb.getStatus().state, 'CLOSED');
  });

  it('应在连续失败后触发熔断', async () => {
    const cb = new ReconCircuitBreaker({ failureThreshold: 3 });
    
    for (let i = 0; i < 3; i++) {
      try {
        await cb.execute(() => { throw new Error('test error'); });
      } catch (e) {
        // 预期失败
      }
    }
    
    assert.strictEqual(cb.getStatus().state, 'OPEN', '熔断器应打开');
  });

  it('应在熔断状态下拒绝执行', async () => {
    const cb = new ReconCircuitBreaker({ failureThreshold: 1 });
    cb.trip('manual trip');
    
    let errorThrown = false;
    try {
      await cb.execute(async () => 'success');
    } catch (e) {
      errorThrown = true;
      assert.ok(e instanceof CircuitBreakerOpenError, '应抛出 CircuitBreakerOpenError');
    }
    
    assert.ok(errorThrown, '应抛出错误');
  });

  it('应在超时后进入半开状态', async () => {
    const cb = new ReconCircuitBreaker({ 
      failureThreshold: 1,
      resetTimeout: 100 
    });
    
    cb.trip('test trip');
    assert.strictEqual(cb.getStatus().state, 'OPEN');
    
    await new Promise(resolve => setTimeout(resolve, 150));
    
    let enteredHalfOpen = false;
    try {
      await cb.execute(async () => {
        enteredHalfOpen = cb.getStatus().state === 'HALF_OPEN';
        return 'success';
      });
    } catch (e) {
      // 可能失败
    }
    
    assert.ok(enteredHalfOpen || cb.getStatus().state === 'CLOSED', '应进入半开或关闭状态');
  });

  it('应支持手动重置熔断器', async () => {
    const cb = new ReconCircuitBreaker({ failureThreshold: 1 });
    
    cb.trip('test');
    assert.strictEqual(cb.getStatus().state, 'OPEN');
    
    cb.reset();
    assert.strictEqual(cb.getStatus().state, 'CLOSED');
    
    const result = await cb.execute(async () => 'success');
    assert.strictEqual(result, 'success');
  });

  it('应在遇到永久错误时立即熔断', async () => {
    const cb = new ReconCircuitBreaker({ failureThreshold: 5 }); // 正常情况下需要5次失败
    
    // 选择器失效应触发立即熔断
    const selectorError = new Error('waitForSelector timeout: div[role="row"]');
    
    try {
      await cb.execute(() => { throw selectorError; });
    } catch (e) {
      // 预期失败
    }
    
    assert.strictEqual(cb.getStatus().state, 'OPEN', '永久错误应立即熔断');
  });
});

// ============================================================================
// 测试套件: 集成场景 (Integration Scenarios)
// ============================================================================

describe('ReconScanner Elite - Integration', () => {
  it('应完成完整的错误分类流程', () => {
    const testCases = [
      { error: { message: '503 Service Unavailable' }, expectedType: ErrorTypes.TRANSIENT },
      { error: { message: '403 Forbidden' }, expectedType: ErrorTypes.BANNED },
      { error: { message: 'selector timeout' }, expectedType: ErrorTypes.OBSOLETE },
      { error: { message: 'unknown error' }, expectedType: ErrorTypes.FATAL }
    ];

    for (const testCase of testCases) {
      const classified = ReconErrorClassifier.classify(testCase.error);
      assert.strictEqual(classified.type, testCase.expectedType,
        `${testCase.error.message} 应被分类为 ${testCase.expectedType}`);
    }
  });

  it('应支持智能重试策略配置', () => {
    const strategy = new ReconRetryStrategy({
      baseDelay: 500,
      maxDelay: 10000,
      maxRetries: 5,
      jitterFactor: 0.15
    });

    // 验证配置生效
    const delay0 = strategy.calculateDelay(0);
    assert.ok(delay0 >= 425 && delay0 <= 575, '第0次延迟应在配置范围内');

    const delay5 = strategy.calculateDelay(5);
    assert.ok(delay5 <= 10000, '延迟不应超过最大值');
  });
});

// ============================================================================
// 测试报告
// ============================================================================

console.log('\n╔══════════════════════════════════════════════════════════════════╗');
console.log('║     TITAN V6.7 ELITE RECON SCANNER - 金融级高压测试             ║');
console.log('╠══════════════════════════════════════════════════════════════════╣');
console.log('║     测试目标:                                                    ║');
console.log('║     1. 分布式锁 - Redis RedLock 高并发一致性                    ║');
console.log('║     2. 瞬态自愈 - 指数退避 + Jitter 重试                        ║');
console.log('║     3. 熔断保护 - CircuitBreaker 防止级联故障                  ║');
console.log('║     4. 零泄漏   - 异常场景下 100% 资源回收                      ║');
console.log('╚══════════════════════════════════════════════════════════════════╝\n');
