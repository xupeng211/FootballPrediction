'use strict';

const reconDecryptorRuntimeUtils = {
  rememberSample(rawSample) {
    if (!rawSample || typeof rawSample !== 'string') {
      return false;
    }

    const cleaned = this._cleanPayload(rawSample);
    const probe = this._probeEncryptedPayload(cleaned);
    if (!probe.valid) {
      return false;
    }

    if (this._recentSamples.includes(cleaned)) {
      return true;
    }

    this._recentSamples.unshift(cleaned);
    if (this._recentSamples.length > this.maxCachedSamples) {
      this._recentSamples.length = this.maxCachedSamples;
    }

    return true;
  },

  _buildSamplePool(primarySample = null) {
    const pool = [];
    const pushUnique = (sample) => {
      if (typeof sample !== 'string' || !sample.trim()) {
        return;
      }

      const cleaned = this._cleanPayload(sample);
      const probe = this._probeEncryptedPayload(cleaned);
      if (!probe.valid) {
        return;
      }

      if (!pool.includes(cleaned)) {
        pool.push(cleaned);
      }
    };

    pushUnique(primarySample);
    for (const sample of this._recentSamples) {
      pushUnique(sample);
    }

    if (pool.length <= 1) {
      return pool;
    }

    const selected = [pool[0]];
    const others = pool.slice(1);
    const targetExtra = Math.min(Math.max(1, this.sampleCrossValidateCount - 1), others.length);

    while (selected.length < targetExtra + 1 && others.length > 0) {
      const index = this.randomInt(others.length);
      const [picked] = others.splice(index, 1);
      selected.push(picked);
    }

    return selected;
  },

  _isPageContextClosedError(error) {
    const message = String(error?.message || '').toLowerCase();
    return (
      error?.code === 'PAGE_CONTEXT_CLOSED'
      || message.includes('page_context_closed')
      || message.includes('target page, context or browser has been closed')
      || message.includes('page has been closed')
      || message.includes('browser has been closed')
      || message.includes('execution context was destroyed')
    );
  },

  _isPageUnavailable(page) {
    if (!page) {
      return true;
    }

    return typeof page.isClosed === 'function' && page.isClosed();
  }
};

module.exports = { reconDecryptorRuntimeUtils };
