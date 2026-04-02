'use strict';

const os = require('node:os');
const path = require('node:path');
const { pathToFileURL } = require('node:url');

const { reconAlgorithmLibrary } = require('./ReconAlgorithmLibrary');
const { reconPureDecryptorRuntime } = require('./ReconPureDecryptorRuntime');

class ReconPureDecryptor {
  constructor(options = {}) {
    this.logger = options.logger || console;
    this.traceId = options.traceId || 'trace-unknown';
    this.fetchImpl = options.fetchImpl || globalThis.fetch;
    this.moduleRoot = options.moduleRoot || path.join(os.tmpdir(), 'recon_pure_decryptor');
    this.decryptFn = null;
    this.algorithmVersion = null;
    this.entryUrl = '';
    this.fetchRetries = Math.max(1, Number(options.fetchRetries || 3));
  }

  async loadFromBundleUrl(bundleUrl, options = {}) {
    if (!bundleUrl || typeof bundleUrl !== 'string') {
      throw new Error('bundleUrl is required');
    }

    if (typeof this.fetchImpl !== 'function') {
      throw new Error('fetch implementation unavailable');
    }

    const headers = options.headers || {};
    const bundleSource = await this._fetchText(bundleUrl, headers);
    const candidateNames = this._extractFromBundle(bundleSource);
    const localEntry = await this._materializeModuleTree(bundleUrl, headers);

    this._installBrowserLikeGlobals(options.globals || {});

    const moduleUrl = `${pathToFileURL(localEntry).href}?t=${Date.now()}`;
    const moduleNamespace = await import(moduleUrl);
    const selected = await this._selectCandidate(moduleNamespace, candidateNames, options.sampleEncryptedData);

    if (!selected) {
      throw new Error('PURE_DECRYPTOR_EXPORT_NOT_FOUND');
    }

    this.decryptFn = selected.fn;
    this.algorithmVersion = `pure_${selected.name}`;
    this.entryUrl = bundleUrl;

    this.logger.info('pure_decryptor_loaded', {
      traceId: this.traceId,
      bundleUrl,
      candidate: selected.name,
      validated: selected.validated
    });

    return this.decryptFn;
  }

  async decrypt(encryptedData) {
    if (typeof this.decryptFn !== 'function') {
      throw new Error('Pure decryptor not initialized');
    }

    const cleanedData = this._cleanPayload(encryptedData);
    const probe = this._probeEncryptedPayload(cleanedData);
    if (!probe.valid) {
      const error = new Error(probe.reason || 'INVALID_ENCRYPTED_PAYLOAD');
      error.code = 'INVALID_ENCRYPTED_PAYLOAD';
      error.payloadPreview = probe.preview || '';
      throw error;
    }

    const result = await this.decryptFn(cleanedData);
    return typeof result === 'string' ? JSON.parse(result) : result;
  }

  getAlgorithmVersion() {
    return this.algorithmVersion;
  }
}

Object.assign(
  ReconPureDecryptor.prototype,
  reconAlgorithmLibrary,
  reconPureDecryptorRuntime
);

module.exports = {
  ReconPureDecryptor
};
