'use strict';

const { ReconDistributedLock } = require('./ReconDistributedLock');
const { ReconArbitrationStrategy } = require('./services/ReconArbitrationStrategy');
const { reconMatchValidator } = require('./services/ReconMatchValidator');
const { reconStitcherPersistence } = require('./services/ReconStitcherPersistence');
const { reconStitcherFlow } = require('./services/ReconStitcherFlow');

class ReconStitcher {
  constructor(options = {}) {
    this.repository = options.repository;
    this.logger = options.logger || console;
    this.parser = options.parser;
    this.enableLocking = options.enableLocking !== false;

    if (!this.repository) {
      throw new Error('ReconStitcher requires a repository instance');
    }

    if (this.enableLocking) {
      if (options.lockManager) {
        this.lockManager = options.lockManager;
      } else if (options.redisClient) {
        this.lockManager = new ReconDistributedLock(options.redisClient, { logger: this.logger });
      } else {
        throw new Error('ReconStitcher requires lockManager or redisClient when locking is enabled');
      }

      this.logger.info('distributed_lock_enabled', {
        backend: options.lockManager ? 'custom' : 'redis'
      });
    }

    this.arbitrationStrategy = options.arbitrationStrategy || new ReconArbitrationStrategy({
      logger: this.logger
    });
    this.processedHashes = new Set();
    this.unmatchedCache = [];
  }
}

Object.assign(
  ReconStitcher.prototype,
  reconMatchValidator,
  reconStitcherPersistence,
  reconStitcherFlow
);

module.exports = { ReconStitcher };
