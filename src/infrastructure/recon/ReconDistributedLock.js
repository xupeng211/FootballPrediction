/**
 * ReconDistributedLock - 分布式锁管理器
 * =====================================
 *
 * 职责: 基于 Redis RedLock 实现分布式锁，确保高并发下的数据一致性
 * 核心要求: 防止多进程同时缝合同一场比赛，确保幂等性
 *
 * @module infrastructure/recon/ReconDistributedLock
 * @version V6.7-ELITE
 * @date 2026-03-22
 */

'use strict';

const redlockModule = require('redlock');
const RedLock = redlockModule.default || redlockModule;
const { ResourceLockedError, ExecutionError } = redlockModule;

/**
 * 分布式锁管理器类
 * @class ReconDistributedLock
 */
class ReconDistributedLock {
  /**
   * 创建分布式锁管理器
   * @param {Object} redisClient - ioredis 客户端实例
   * @param {Object} options - 配置选项
   * @param {number} options.driftFactor - 时钟漂移因子 (默认: 0.01)
   * @param {number} options.retryCount - 重试次数 (默认: 3)
   * @param {number} options.retryDelay - 重试延迟 ms (默认: 200)
   * @param {number} options.retryJitter - 抖动范围 ms (默认: 200)
   */
  constructor(redisClient, options = {}) {
    if (!redisClient) {
      throw new Error('ReconDistributedLock requires a redis client');
    }

    this.redis = redisClient;
    this.redlock = new RedLock([redisClient], {
      driftFactor: options.driftFactor || 0.01,
      retryCount: options.retryCount || 3,
      retryDelay: options.retryDelay || 200,
      retryJitter: options.retryJitter || 200
    });

    this.logger = options.logger || console;
    this.locks = new Map(); // 追踪当前持有的锁

    if (typeof this.redlock.on === 'function') {
      this.redlock.on('error', (error) => {
        this.logger.warn('redlock_client_error', {
          error: error?.message || String(error || ''),
          name: error?.name || 'Error'
        });
      });
    }
  }

  _extractAttemptErrors(attempts = []) {
    const errors = [];

    for (const attempt of attempts) {
      const votesAgainst = attempt?.votesAgainst;
      if (votesAgainst instanceof Map) {
        for (const vote of votesAgainst.values()) {
          if (vote?.error) {
            errors.push(vote.error);
          } else if (vote instanceof Error) {
            errors.push(vote);
          }
        }
      } else if (Array.isArray(votesAgainst)) {
        for (const vote of votesAgainst) {
          if (vote?.error) {
            errors.push(vote.error);
          } else if (vote instanceof Error) {
            errors.push(vote);
          }
        }
      }
    }

    return errors;
  }

  _isContentionError(error) {
    if (error instanceof ResourceLockedError || error?.name === 'ResourceLockedError') {
      return true;
    }

    if (!(error instanceof ExecutionError) && error?.name !== 'ExecutionError') {
      return /ResourceLockedError|unable to achieve a quorum/i.test(String(error?.message || ''));
    }

    const attemptErrors = this._extractAttemptErrors(error?.attempts || []);
    return attemptErrors.length > 0
      && attemptErrors.every((attemptError) => (
        attemptError instanceof ResourceLockedError
        || attemptError?.name === 'ResourceLockedError'
      ));
  }

  /**
   * 获取比赛行级锁
   * @param {string} hash - 比赛 Hash (如 'lh1OJUtR')
   * @param {number} ttl - 锁有效期 ms (默认: 5000)
   * @returns {Promise<Object>} 锁对象 { release: Function }
   * @throws {Error} LockAcquireFailure - 获取锁失败
   */
  async acquireRowLock(hash, ttl = 5000) {
    const lockKey = `recon:lock:${hash}`;
    
    try {
      const normalizedTtl = Math.max(1, Math.floor(Number(ttl) || 5000));
      this.logger.debug('acquire_lock_attempt', { hash, lockKey, ttl: normalizedTtl });

      const lock = await this.redlock.acquire([lockKey], normalizedTtl);
      
      // 追踪锁
      this.locks.set(hash, {
        lock,
        acquiredAt: Date.now(),
        key: lockKey
      });

      this.logger.info('acquire_lock', { hash, lockKey, ttl: normalizedTtl, backend: 'redis' });
      this.logger.info('lock_acquired', { hash, lockKey });

      // 包装 release 方法以更新追踪状态
      const originalRelease = lock.release.bind(lock);
      lock.release = async () => {
        try {
          await originalRelease();
          this.locks.delete(hash);
          this.logger.info('lock_released', { hash, lockKey });
        } catch (e) {
          this.logger.warn('lock_release_error', { hash, error: e.message });
          throw e;
        }
      };
      
      return lock;
    } catch (e) {
      const isContention = this._isContentionError(e);
      const code = isContention ? 'LOCK_CONTENDED' : 'LOCK_BACKEND_ERROR';
      this.logger.warn(isContention ? 'acquire_lock_contended' : 'lock_acquire_failed', {
        hash,
        lockKey,
        error: e.message,
        code
      });
      throw new LockAcquireFailure(`Failed to acquire lock for hash ${hash}: ${e.message}`, code, e);
    }
  }

  /**
   * 批量获取锁 (带超时控制)
   * @param {Array<string>} hashes - Hash 列表
   * @param {Object} options - 选项
   * @param {number} options.timeout - 总超时 ms (默认: 30000)
   * @returns {Promise<Map<string, Object>>} Hash -> 锁对象映射
   */
  async acquireBatchLocks(hashes, options = {}) {
    const timeout = options.timeout || 30000;
    const startTime = Date.now();
    const acquiredLocks = new Map();
    
    // 按顺序获取锁，避免死锁
    const sortedHashes = [...hashes].sort();
    
    for (const hash of sortedHashes) {
      // 检查总超时
      if (Date.now() - startTime > timeout) {
        // 释放已获取的锁
        await this.releaseBatchLocks(acquiredLocks);
        throw new LockAcquireFailure(`Batch lock acquisition timeout after ${timeout}ms`);
      }
      
      try {
        const lock = await this.acquireRowLock(hash);
        acquiredLocks.set(hash, lock);
      } catch (e) {
        // 释放已获取的锁
        await this.releaseBatchLocks(acquiredLocks);
        throw e;
      }
    }
    
    return acquiredLocks;
  }

  /**
   * 批量释放锁
   * @param {Map<string, Object>} locks - Hash -> 锁对象映射
   */
  async releaseBatchLocks(locks) {
    const releases = [];
    
    for (const [hash, lock] of locks) {
      releases.push(
        lock.release().catch(e => {
          this.logger.warn('batch_release_error', { hash, error: e.message });
        })
      );
    }
    
    await Promise.all(releases);
  }

  /**
   * 检查是否持有某锁
   * @param {string} hash - 比赛 Hash
   * @returns {boolean} 是否持有锁
   */
  hasLock(hash) {
    return this.locks.has(hash);
  }

  /**
   * 获取当前持有的锁数量
   * @returns {number} 锁数量
   */
  getLockCount() {
    return this.locks.size;
  }

  /**
   * 强制释放所有锁 (用于异常恢复)
   */
  async releaseAllLocks() {
    this.logger.warn('releasing_all_locks', { count: this.locks.size });
    
    for (const [hash, lockInfo] of this.locks) {
      try {
        await lockInfo.lock.release();
      } catch (e) {
        this.logger.warn('force_release_error', { hash, error: e.message });
      }
    }
    
    this.locks.clear();
  }

  /**
   * 获取锁状态报告
   * @returns {Object} 锁状态
   */
  getLockStatus() {
    const now = Date.now();
    return {
      totalLocks: this.locks.size,
      locks: Array.from(this.locks.entries()).map(([hash, info]) => ({
        hash,
        acquiredAt: info.acquiredAt,
        heldFor: now - info.acquiredAt,
        key: info.key
      }))
    };
  }

  /**
   * 断开 Redis 连接
   */
  async disconnect() {
    await this.releaseAllLocks();
    if (this.redis) {
      await this.redis.disconnect();
    }
  }
}

/**
 * 锁获取失败错误
 */
class LockAcquireFailure extends Error {
  constructor(message, code = 'LOCK_ACQUIRE_FAILED', cause = null) {
    super(message);
    this.name = 'LockAcquireFailure';
    this.code = code;
    this.cause = cause || null;
  }
}

module.exports = {
  ReconDistributedLock,
  LockAcquireFailure
};
