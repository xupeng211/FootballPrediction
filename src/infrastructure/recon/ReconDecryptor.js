/**
 * ReconDecryptor - 协议解密专家 (V11.0 Clean Sweep)
 * ================================================
 *
 * 职责: 动态提取并执行 OddsPortal 的解密逻辑
 *
 * @module infrastructure/recon/ReconDecryptor
 */

'use strict';

const { randomInt } = require('node:crypto');
const { reconAlgorithmLibrary } = require('./services/ReconAlgorithmLibrary');
const { reconDecryptorSourceExtractor } = require('./services/ReconDecryptorSourceExtractor');

class ReconDecryptor {
  constructor(options = {}) {
    this.logger = options.logger || console;
    this.traceId = options.traceId || 'no-trace';
    this.decryptFn = null;
    this.algorithmVersion = null;
    this.allowBestEffortCandidate = options.allowBestEffortCandidate === true;
    this.sampleCrossValidateCount = Math.max(1, Number(options.sampleCrossValidateCount ?? 3));
    this.maxCachedSamples = Math.max(2, Number(options.maxCachedSamples ?? 8));
    this.readinessTimeoutMs = Math.max(1000, Number(options.readinessTimeoutMs ?? 12000));
    this.readinessPollMs = Math.max(50, Number(options.readinessPollMs ?? 250));
    this.randomInt = typeof options.randomInt === 'function' ? options.randomInt : randomInt;
    this._extractPromise = null;
    this._recentSamples = [];
  }

  _createPageClosedError() {
    const pageClosedError = new Error('PAGE_CONTEXT_CLOSED');
    pageClosedError.code = 'PAGE_CONTEXT_CLOSED';
    return pageClosedError;
  }

  _storeDecryptor(decryptFn) {
    this.decryptFn = decryptFn;
    if (!this.algorithmVersion && decryptFn?.__algorithmVersion) {
      this.algorithmVersion = decryptFn.__algorithmVersion;
    }
    return decryptFn;
  }

  _logExtractedDecryptor(method, payload = {}, level = 'info') {
    this.logger[level]('decryptor_extracted', {
      method,
      version: this.algorithmVersion,
      ...payload
    });
  }

  async _tryPrimaryAppScript(page, sampleEncryptedData, samplePool) {
    const decryptFn = await this._extractFromAppScript(page, samplePool, {
      hasPrimarySample: typeof sampleEncryptedData === 'string' && sampleEncryptedData.trim().length > 0
    });
    if (!decryptFn) {
      return null;
    }

    this._storeDecryptor(decryptFn);
    this._logExtractedDecryptor(decryptFn.__extractMethod || 'app_script', {
      validated: this.decryptFn.__validated !== false,
      bestEffort: this.decryptFn.__bestEffort === true
    });
    return this.decryptFn;
  }

  async _tryFallbackAppScript(page, sampleEncryptedData, samplePool) {
    const hasPrimarySample = typeof sampleEncryptedData === 'string' && sampleEncryptedData.trim().length > 0;
    if (!hasPrimarySample || samplePool.length > 0) {
      return null;
    }

    const decryptFn = await this._extractFromAppScript(page, null, {
      hasPrimarySample: false
    });
    if (!decryptFn) {
      return null;
    }

    this._storeDecryptor(decryptFn);
    this.logger.warn('decryptor_extracted_without_primary_sample', {
      method: decryptFn.__extractMethod || 'app_script',
      version: this.algorithmVersion
    });
    return this.decryptFn;
  }

  async _trySecondarySources(page) {
    const attempts = [
      ['inline_script', this._extractFromInlineScripts.bind(this)],
      ['global_scope', this._extractFromGlobalScope.bind(this)]
    ];

    for (const [method, extractor] of attempts) {
      const decryptFn = await extractor(page);
      if (!decryptFn) {
        continue;
      }

      this._storeDecryptor(decryptFn);
      this._logExtractedDecryptor(method);
      return decryptFn;
    }

    return null;
  }

  async _extractWithFallbackStrategies(page, sampleEncryptedData, samplePool) {
    return this._tryPrimaryAppScript(page, sampleEncryptedData, samplePool)
      || this._tryFallbackAppScript(page, sampleEncryptedData, samplePool)
      || this._trySecondarySources(page);
  }

  async extractDecryptor(page, sampleEncryptedData = null) {
    if (!page) {
      throw new Error('Page instance required');
    }

    if (this._isPageUnavailable(page)) {
      throw this._createPageClosedError();
    }

    if (typeof this.decryptFn === 'function' && this.algorithmVersion) {
      return this.decryptFn;
    }

    if (this._extractPromise) {
      return this._extractPromise;
    }

    this.rememberSample(sampleEncryptedData);
    const samplePool = this._buildSamplePool(sampleEncryptedData);

    this._extractPromise = (async () => {
      try {
        const decryptFn = await this._extractWithFallbackStrategies(page, sampleEncryptedData, samplePool);
        if (decryptFn) {
          return decryptFn;
        }
        if (this._isPageUnavailable(page)) {
          throw this._createPageClosedError();
        }

        throw new Error('Failed to extract decryptor from any source');
      } catch (error) {
        if (this._isPageContextClosedError(error)) {
          this.logger.debug('decryptor_extraction_skipped_page_closed', {
            traceId: this.traceId
          });
        } else {
          this.logger.error('decryptor_extraction_failed', { error: error.message });
        }
        throw error;
      } finally {
        this._extractPromise = null;
      }
    })();

    return this._extractPromise;
  }

  async decrypt(encryptedData) {
    if (!this.decryptFn) {
      throw new Error('Decryptor not initialized. Call extractDecryptor first.');
    }

    try {
      const cleanedData = this._cleanPayload(encryptedData);
      const payloadProbe = this._probeEncryptedPayload(cleanedData);
      if (!payloadProbe.valid) {
        const invalidPayloadError = new Error(payloadProbe.reason || 'INVALID_ENCRYPTED_PAYLOAD');
        invalidPayloadError.code = 'INVALID_ENCRYPTED_PAYLOAD';
        invalidPayloadError.payloadPreview = payloadProbe.preview || '';
        throw invalidPayloadError;
      }

      return await this.decryptFn(cleanedData);
    } catch (error) {
      this.logger.error('[ReconDecryptor] 解密失败', {
        traceId: this.traceId,
        error: error.message,
        code: error.code || null,
        payloadPreview: error.payloadPreview || null,
        algorithmVersion: this.algorithmVersion
      });
      throw error;
    }
  }

  getAlgorithmVersion() {
    return this.algorithmVersion;
  }

  async canDecrypt(page) {
    try {
      const fn = await this.extractDecryptor(page);
      return fn !== null;
    } catch {
      return false;
    }
  }
}

Object.assign(
  ReconDecryptor.prototype,
  reconAlgorithmLibrary,
  reconDecryptorSourceExtractor
);

module.exports = { ReconDecryptor };
