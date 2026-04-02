/**
 * Recon Infrastructure - 侦察基础设施
 * ===================================
 *
 * 金融级数据侦察组件库 - V6.7 满分架构
 *
 * @module infrastructure/recon
 * @version V6.7-OBSERVABILITY
 * @date 2026-03-22
 */

'use strict';

const { ReconNavigator } = require('./ReconNavigator');
const { ReconParser } = require('./ReconParser');
const { ReconStitcher } = require('./ReconStitcher');
const { ReconEngine } = require('./ReconEngine');
const { ReconDecryptor } = require('./ReconDecryptor');
const { ReconDistributedLock, LockAcquireFailure } = require('./ReconDistributedLock');
const {
  ReconErrorClassifier,
  ReconRetryStrategy,
  ReconCircuitBreaker,
  ReconCircuitBreakerPool,
  ErrorTypes,
  CircuitBreakerOpenError
} = require('./ReconResilience');
const { ReconMetrics } = require('./ReconMetrics');
const { ReconGuardian } = require('./ReconGuardian');
const { ReconHealthServer } = require('./ReconHealthServer');

module.exports = {
  // 核心组件
  ReconNavigator,
  ReconParser,
  ReconStitcher,
  ReconEngine,
  ReconDecryptor,

  // 分布式锁
  ReconDistributedLock,
  LockAcquireFailure,

  // 弹性与容错
  ReconErrorClassifier,
  ReconRetryStrategy,
  ReconCircuitBreaker,
  ReconCircuitBreakerPool,
  ErrorTypes,
  CircuitBreakerOpenError,

  // 可观测性
  ReconMetrics,
  ReconGuardian,
  ReconHealthServer
};
