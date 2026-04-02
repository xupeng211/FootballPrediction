'use strict';

const { ReconDistributedLock } = require('./ReconDistributedLock');
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
        this.logger.warn('distributed_lock_disabled');
        this.enableLocking = false;
      }
    }

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
