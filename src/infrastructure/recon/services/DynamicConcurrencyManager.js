'use strict';

function isNetworkFailure(error) {
  const statusCode = Number(error?.statusCode || error?.cause?.statusCode || 0);
  const code = String(error?.code || '').toUpperCase();
  const message = String(error?.message || '').toLowerCase();

  if (statusCode === 403 || statusCode === 503) {
    return true;
  }

  if (code.includes('403') || code.includes('503') || code.includes('TIMEOUT')) {
    return true;
  }

  return message.includes('403')
    || message.includes('503')
    || message.includes('forbidden')
    || message.includes('service unavailable')
    || message.includes('timeout')
    || message.includes('timed out');
}

class DynamicConcurrencyManager {
  constructor(options = {}) {
    this.logger = options.logger || console;
    this.floor = Math.max(1, Number(options.floor) || 1);
    this.ceiling = Math.max(this.floor, Number(options.maxConcurrency) || this.floor);
    this.successWindow = Math.max(1, Number(options.successWindow) || 3);
    this.maxActiveWorkers = Math.min(
      this.ceiling,
      Math.max(this.floor, Number(options.initialConcurrency) || this.floor)
    );
    this.successStreak = 0;
  }

  getMaxActiveWorkers() {
    return this.maxActiveWorkers;
  }

  getState() {
    return {
      floor: this.floor,
      ceiling: this.ceiling,
      successWindow: this.successWindow,
      successStreak: this.successStreak,
      maxActiveWorkers: this.maxActiveWorkers
    };
  }

  setCeiling(nextCeiling, metadata = {}) {
    const normalized = Math.max(this.floor, Number(nextCeiling) || this.floor);
    const previousCeiling = this.ceiling;
    const previousActiveWorkers = this.maxActiveWorkers;

    this.ceiling = normalized;
    if (this.maxActiveWorkers > this.ceiling) {
      this.maxActiveWorkers = this.ceiling;
      this.successStreak = 0;
    }

    if (previousCeiling !== this.ceiling || previousActiveWorkers !== this.maxActiveWorkers) {
      this.logger.info('recon_dynamic_concurrency_adjusted', {
        reason: 'proxy_feedback',
        previousCeiling,
        ceiling: this.ceiling,
        previousMaxActiveWorkers: previousActiveWorkers,
        maxActiveWorkers: this.maxActiveWorkers,
        ...metadata
      });
    }
  }

  recordSuccess(metadata = {}) {
    this.successStreak += 1;

    if (this.maxActiveWorkers >= this.ceiling || this.successStreak < this.successWindow) {
      return false;
    }

    const previous = this.maxActiveWorkers;
    this.maxActiveWorkers = Math.min(this.ceiling, this.maxActiveWorkers + 1);
    this.successStreak = 0;

    if (previous !== this.maxActiveWorkers) {
      this.logger.info('recon_dynamic_concurrency_adjusted', {
        reason: 'success_feedback',
        previousMaxActiveWorkers: previous,
        maxActiveWorkers: this.maxActiveWorkers,
        ceiling: this.ceiling,
        ...metadata
      });
      return true;
    }

    return false;
  }

  recordFailure(error, metadata = {}) {
    this.successStreak = 0;
    if (!isNetworkFailure(error)) {
      return false;
    }

    const previous = this.maxActiveWorkers;
    this.maxActiveWorkers = Math.max(this.floor, Math.floor(this.maxActiveWorkers * 0.5));

    if (previous !== this.maxActiveWorkers) {
      this.logger.warn('recon_dynamic_concurrency_adjusted', {
        reason: 'network_failure',
        previousMaxActiveWorkers: previous,
        maxActiveWorkers: this.maxActiveWorkers,
        ceiling: this.ceiling,
        error: error?.message || null,
        statusCode: Number(error?.statusCode || error?.cause?.statusCode || 0) || null,
        ...metadata
      });
      return true;
    }

    return false;
  }
}

module.exports = {
  DynamicConcurrencyManager,
  isNetworkFailure
};
