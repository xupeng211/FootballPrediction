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

  async extractDecryptor(page, sampleEncryptedData = null) {
    if (!page) {
      throw new Error('Page instance required');
    }

    if (this._isPageUnavailable(page)) {
      const pageClosedError = new Error('PAGE_CONTEXT_CLOSED');
      pageClosedError.code = 'PAGE_CONTEXT_CLOSED';
      throw pageClosedError;
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
        const appScriptDecryptFn = await this._extractFromAppScript(page, samplePool, {
          hasPrimarySample: typeof sampleEncryptedData === 'string' && sampleEncryptedData.trim().length > 0
        });
        if (appScriptDecryptFn) {
          this.decryptFn = appScriptDecryptFn;
          if (!this.algorithmVersion && appScriptDecryptFn.__algorithmVersion) {
            this.algorithmVersion = appScriptDecryptFn.__algorithmVersion;
          }
          this.logger.info('decryptor_extracted', {
            method: 'app_script',
            version: this.algorithmVersion,
            validated: this.decryptFn.__validated !== false,
            bestEffort: this.decryptFn.__bestEffort === true
          });
          return this.decryptFn;
        }

        const hasPrimarySample = typeof sampleEncryptedData === 'string' && sampleEncryptedData.trim().length > 0;
        if (hasPrimarySample && samplePool.length === 0) {
          const fallbackDecryptFn = await this._extractFromAppScript(page, null, {
            hasPrimarySample: false
          });
          if (fallbackDecryptFn) {
            this.decryptFn = fallbackDecryptFn;
            if (!this.algorithmVersion && fallbackDecryptFn.__algorithmVersion) {
              this.algorithmVersion = fallbackDecryptFn.__algorithmVersion;
            }
            this.logger.warn('decryptor_extracted_without_primary_sample', {
              method: 'app_script',
              version: this.algorithmVersion
            });
            return this.decryptFn;
          }
        }

        const inlineFn = await this._extractFromInlineScripts(page);
        if (inlineFn) {
          this.decryptFn = inlineFn;
          this.logger.info('decryptor_extracted', { method: 'inline_script', version: this.algorithmVersion });
          return inlineFn;
        }

        const globalFn = await this._extractFromGlobalScope(page);
        if (globalFn) {
          this.decryptFn = globalFn;
          this.logger.info('decryptor_extracted', { method: 'global_scope', version: this.algorithmVersion });
          return globalFn;
        }

        if (this._isPageUnavailable(page)) {
          const pageClosedError = new Error('PAGE_CONTEXT_CLOSED');
          pageClosedError.code = 'PAGE_CONTEXT_CLOSED';
          throw pageClosedError;
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
