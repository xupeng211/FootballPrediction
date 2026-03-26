/**
 * ReconResilience - 弹性与容错模块
 * =================================
 *
 * 职责: 实现错误分类学、指数退避重试策略、熔断器保护
 * 核心要求: 区分瞬态/永久错误，实现自愈重试，防止级联故障
 *
 * @module infrastructure/recon/ReconResilience
 * @version V6.7-ELITE
 * @date 2026-03-22
 */

'use strict';

/**
 * 错误类型枚举
 * @readonly
 * @enum {string}
 */
const ErrorTypes = {
  /** 瞬态错误 - 网络抖动，可重试 */
  TRANSIENT: 'TRANSIENT',
  /** 代理封禁 - 403/429，需切换代理 */
  BANNED: 'BANNED',
  /** 选择器失效 - 页面改版，需人工介入 */
  OBSOLETE: 'OBSOLETE',
  /** 致命错误 - 不可恢复 */
  FATAL: 'FATAL'
};

/**
 * 错误分类器
 * @class ReconErrorClassifier
 */
class ReconErrorClassifier {
  /**
   * 分类错误类型
   * @param {Error} error - 错误对象
   * @returns {Object} 分类结果 { type, retryable, maxRetries, shouldSwitchProxy }
   */
  static classify(error) {
    const message = (error.message || '').toLowerCase();
    const code = error.code || '';
    
    // 1. 代理封禁/限流 (优先级最高)
    if (message.includes('403') || 
        message.includes('429') || 
        message.includes('forbidden') ||
        message.includes('too many requests') ||
        message.includes('proxy banned') ||
        message.includes('proxy connection refused')) {
      return {
        type: ErrorTypes.BANNED,
        retryable: true,
        maxRetries: 1,
        shouldSwitchProxy: true,
        description: 'Proxy banned or rate limited'
      };
    }
    
    // 2. 选择器失效 (页面改版)
    if (message.includes('selector') || 
        message.includes('waitforselector') ||
        message.includes('element not found') ||
        (message.includes('timeout') && message.includes('selector')) ||
        message.includes('page structure changed')) {
      return {
        type: ErrorTypes.OBSOLETE,
        retryable: false,
        shouldSwitchProxy: false,
        description: 'Page structure changed, selectors obsolete'
      };
    }
    
    // 3. 瞬态网络错误
    if (code === 'ECONNRESET' || 
        code === 'ETIMEDOUT' || 
        code === 'ECONNREFUSED' ||
        code === 'ENOTFOUND' ||
        message.includes('503') || 
        message.includes('502') || 
        message.includes('504') ||
        message.includes('service unavailable') ||
        message.includes('bad gateway') ||
        message.includes('gateway timeout') ||
        message.includes('socket hang up') ||
        message.includes('network error')) {
      return {
        type: ErrorTypes.TRANSIENT,
        retryable: true,
        maxRetries: 3,
        shouldSwitchProxy: false,
        description: 'Transient network error'
      };
    }
    
    // 4. 浏览器/上下文崩溃
    if (message.includes('target closed') ||
        message.includes('browser has been closed') ||
        message.includes('context destroyed') ||
        message.includes('page crashed')) {
      return {
        type: ErrorTypes.TRANSIENT,
        retryable: true,
        maxRetries: 2,
        shouldSwitchProxy: false,
        description: 'Browser context crashed'
      };
    }
    
    // 5. 其他视为致命错误
    return {
      type: ErrorTypes.FATAL,
      retryable: false,
      shouldSwitchProxy: false,
      description: 'Fatal error'
    };
  }

  /**
   * 检查是否应触发熔断
   * @param {Error} error - 错误对象
   * @returns {boolean} 是否应熔断
   */
  static shouldTriggerCircuitBreaker(error) {
    const classified = this.classify(error);
    return classified.type === ErrorTypes.OBSOLETE ||
           classified.type === ErrorTypes.FATAL;
  }
}

/**
 * 指数退避重试策略
 * @class ReconRetryStrategy
 */
class ReconRetryStrategy {
  /**
   * 创建重试策略
   * @param {Object} options - 配置选项
   * @param {number} options.baseDelay - 基础延迟 ms (默认: 1000)
   * @param {number} options.maxDelay - 最大延迟 ms (默认: 30000)
   * @param {number} options.jitterFactor - 抖动因子 0-1 (默认: 0.1)
   * @param {number} options.maxRetries - 最大重试次数 (默认: 3)
   */
  constructor(options = {}) {
    this.baseDelay = options.baseDelay || 1000;
    this.maxDelay = options.maxDelay || 30000;
    this.jitterFactor = options.jitterFactor || 0.1;
    this.maxRetries = options.maxRetries || 3;
  }

  /**
   * 计算退避延迟
   * @param {number} attempt - 当前尝试次数 (从 0 开始)
   * @returns {number} 延迟毫秒数
   */
  calculateDelay(attempt) {
    // 指数退避: baseDelay * 2^attempt
    const exponentialDelay = this.baseDelay * Math.pow(2, attempt);
    
    // 添加随机抖动 (±jitterFactor)
    const jitter = (Math.random() - 0.5) * 2 * this.jitterFactor * exponentialDelay;
    
    // 应用上限 (确保最终结果不超过 maxDelay)
    const finalDelay = Math.min(exponentialDelay + jitter, this.maxDelay);
    
    return Math.max(0, Math.floor(finalDelay));
  }

  /**
   * 执行带重试的操作
   * @param {Function} fn - 要执行的异步函数
   * @param {Object} options - 执行选项
   * @param {Function} options.onRetry - 重试回调 (attempt, delay, error) => void
   * @returns {Promise<any>} 操作结果
   * @throws {Error} 最后一次重试的错误
   */
  async execute(fn, options = {}) {
    let lastError;
    
    for (let attempt = 0; attempt <= this.maxRetries; attempt++) {
      try {
        return await fn();
      } catch (error) {
        lastError = error;
        
        // 检查是否还有重试机会
        if (attempt < this.maxRetries) {
          const delay = this.calculateDelay(attempt);
          
          if (options.onRetry) {
            options.onRetry(attempt + 1, delay, error);
          }
          
          await this.sleep(delay);
        }
      }
    }
    
    throw lastError;
  }

  /**
   * 根据错误分类执行智能重试
   * @param {Function} fn - 要执行的异步函数
   * @param {Object} context - 执行上下文
   * @param {Function} context.onTransient - 瞬态错误回调
   * @param {Function} context.onBanned - 代理封禁回调
   * @param {Function} context.onPermanent - 永久错误回调
   * @returns {Promise<any>} 操作结果
   */
  async executeWithClassification(fn, context = {}) {
    let lastError;
    let consecutiveFailures = 0;
    
    while (consecutiveFailures < this.maxRetries) {
      try {
        return await fn();
      } catch (error) {
        lastError = error;
        const classified = ReconErrorClassifier.classify(error);
        
        switch (classified.type) {
          case ErrorTypes.TRANSIENT:
            consecutiveFailures++;
            if (consecutiveFailures < this.maxRetries) {
              const delay = this.calculateDelay(consecutiveFailures - 1);
              if (context.onTransient) {
                context.onTransient(error, consecutiveFailures, delay);
              }
              await this.sleep(delay);
            }
            break;
            
          case ErrorTypes.BANNED:
            if (context.onBanned) {
              context.onBanned(error);
            }
            // 代理封禁不重试，立即抛出
            throw error;
            
          case ErrorTypes.OBSOLETE:
          case ErrorTypes.FATAL:
            if (context.onPermanent) {
              context.onPermanent(error, classified.type);
            }
            // 永久错误不重试
            throw error;
            
          default:
            throw error;
        }
      }
    }
    
    throw lastError;
  }

  /**
   * 休眠
   * @param {number} ms - 毫秒数
   * @returns {Promise<void>}
   */
  sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}

/**
 * 熔断器
 * @class ReconCircuitBreaker
 */
class ReconCircuitBreaker {
  /**
   * 创建熔断器
   * @param {Object} options - 配置选项
   * @param {number} options.failureThreshold - 触发熔断的失败次数 (默认: 5)
   * @param {number} options.resetTimeout - 熔断后重置时间 ms (默认: 60000)
   * @param {number} options.halfOpenMaxCalls - 半开状态最大测试调用数 (默认: 3)
   */
  constructor(options = {}) {
    this.failureThreshold = options.failureThreshold || 5;
    this.resetTimeout = options.resetTimeout || 60000;
    this.halfOpenMaxCalls = options.halfOpenMaxCalls || 3;
    
    this.state = 'CLOSED'; // CLOSED, OPEN, HALF_OPEN
    this.failures = 0;
    this.lastFailureTime = null;
    this.halfOpenCalls = 0;
    
    this.logger = options.logger || console;
  }

  /**
   * 执行受保护的操作
   * @param {Function} fn - 异步操作
   * @param {Object} options - 选项
   * @param {boolean} options.force - 强制绕过熔断检查
   * @returns {Promise<any>} 操作结果
   * @throws {CircuitBreakerOpenError} 熔断器打开时
   */
  async execute(fn, options = {}) {
    if (!options.force) {
      await this.checkState();
    }
    
    try {
      const result = await fn();
      this.onSuccess();
      return result;
    } catch (error) {
      this.onFailure(error);
      throw error;
    }
  }

  /**
   * 检查当前状态并可能转换
   * @private
   */
  async checkState() {
    if (this.state === 'OPEN') {
      const timeSinceLastFailure = Date.now() - this.lastFailureTime;
      
      if (timeSinceLastFailure > this.resetTimeout) {
        this.logger.info('circuit_breaker_half_open');
        this.state = 'HALF_OPEN';
        this.halfOpenCalls = 0;
      } else {
        const remainingTime = this.resetTimeout - timeSinceLastFailure;
        throw new CircuitBreakerOpenError(
          `Circuit breaker is OPEN. Retry after ${remainingTime}ms`
        );
      }
    }
    
    if (this.state === 'HALF_OPEN') {
      if (this.halfOpenCalls >= this.halfOpenMaxCalls) {
        throw new CircuitBreakerOpenError(
          'Circuit breaker HALF_OPEN limit reached'
        );
      }
      this.halfOpenCalls++;
    }
  }

  /**
   * 成功处理
   * @private
   */
  onSuccess() {
    if (this.state === 'HALF_OPEN') {
      this.logger.info('circuit_breaker_closed');
      this.state = 'CLOSED';
    }
    
    this.failures = 0;
    this.lastFailureTime = null;
  }

  /**
   * 失败处理
   * @private
   * @param {Error} error - 错误对象
   */
  onFailure(error) {
    this.failures++;
    this.lastFailureTime = Date.now();
    
    const classified = ReconErrorClassifier.classify(error);
    
    // 永久错误立即熔断
    if (classified.type === ErrorTypes.OBSOLETE || 
        classified.type === ErrorTypes.FATAL) {
      this.trip(`Permanent error: ${classified.type}`);
      return;
    }
    
    // 超过阈值熔断
    if (this.failures >= this.failureThreshold) {
      this.trip(`Failure threshold reached: ${this.failures}`);
    }
  }

  /**
   * 手动触发熔断
   * @param {string} reason - 熔断原因
   */
  trip(reason) {
    this.logger.error('circuit_breaker_tripped', { reason, failures: this.failures });
    this.state = 'OPEN';
    this.lastFailureTime = Date.now();
  }

  /**
   * 手动重置熔断器
   */
  reset() {
    this.logger.info('circuit_breaker_reset');
    this.state = 'CLOSED';
    this.failures = 0;
    this.lastFailureTime = null;
    this.halfOpenCalls = 0;
  }

  /**
   * 获取熔断器状态
   * @returns {Object} 状态信息
   */
  getStatus() {
    return {
      state: this.state,
      failures: this.failures,
      lastFailureTime: this.lastFailureTime,
      timeSinceLastFailure: this.lastFailureTime ? Date.now() - this.lastFailureTime : null,
      halfOpenCalls: this.halfOpenCalls
    };
  }
}

/**
 * 熔断器打开错误
 */
class CircuitBreakerOpenError extends Error {
  constructor(message) {
    super(message);
    this.name = 'CircuitBreakerOpenError';
  }
}

module.exports = {
  ErrorTypes,
  ReconErrorClassifier,
  ReconRetryStrategy,
  ReconCircuitBreaker,
  CircuitBreakerOpenError
};
