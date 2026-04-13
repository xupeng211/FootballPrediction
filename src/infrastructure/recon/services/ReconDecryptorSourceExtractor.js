'use strict';

const { ReconPureDecryptor } = require('./ReconPureDecryptor');
const { reconDecryptorRuntimeUtils } = require('./ReconDecryptorRuntimeUtils');
const {
  extractFromAppScript,
  collectCrossValidationSamples
} = require('./ReconDecryptorAppScriptHelpers');

const reconDecryptorSourceExtractor = {
  async _extractFromAppScript(page, sampleInput = null, options = {}) {
    return extractFromAppScript.call(this, page, sampleInput, options);
  },

  async _fetchBundleSource(page, appScriptUrl) {
    if (!page || typeof page.evaluate !== 'function' || !appScriptUrl) {
      return '';
    }

    try {
      return await page.evaluate(async (url) => {
        const response = await fetch(url, { credentials: 'include' });
        if (!response.ok) {
          return '';
        }
        return response.text();
      }, appScriptUrl);
    } catch (error) {
      this.logger.debug('app_script_bundle_fetch_failed', {
        traceId: this.traceId,
        error: error.message
      });
      return '';
    }
  },

  async _waitForDecryptorReady(page) {
    if (!page || typeof page.waitForFunction !== 'function') {
      return;
    }

    try {
      await page.waitForFunction(
        () => Boolean(document.querySelector('script[src*="/build/assets/app"]')),
        {
          timeout: this.readinessTimeoutMs,
          polling: this.readinessPollMs
        }
      );
    } catch (error) {
      this.logger.debug('decryptor_readiness_wait_script_timeout', {
        traceId: this.traceId,
        error: error.message
      });
    }

    try {
      await page.waitForFunction(
        () => {
          const otCode = typeof window.pageVar?.otCode === 'string'
            ? window.pageVar.otCode.trim()
            : '';
          const pageOutrightsId = typeof window.pageOutrightsVar?.id === 'string'
            ? window.pageOutrightsVar.id.trim()
            : '';
          return otCode.length > 0 || pageOutrightsId.length > 0;
        },
        {
          timeout: this.readinessTimeoutMs,
          polling: this.readinessPollMs
        }
      );
    } catch (error) {
      this.logger.debug('decryptor_readiness_wait_otcode_timeout', {
        traceId: this.traceId,
        error: error.message
      });
    }
  },

  async _collectCrossValidationSamples(page, maxSamples = 3) {
    return collectCrossValidationSamples.call(this, page, maxSamples);
  },

  async _readSerializableRuntimeState(page) {
    if (!page || typeof page.evaluate !== 'function') {
      return {
        locationHref: '',
        pageVar: null,
        pageOutrightsVar: null
      };
    }

    try {
      return await page.evaluate(() => {
        const normalize = (value) => {
          if (value && typeof value === 'object') {
            return value;
          }
          if (typeof value === 'string' && value.trim()) {
            try {
              return JSON.parse(value);
            } catch {
              return null;
            }
          }
          return null;
        };

        const pageVar = normalize(window.pageVar);
        const pageOutrightsVar = normalize(window.pageOutrightsVar);
        return {
          locationHref: String(window.location?.href || ''),
          pageVar: pageVar ? {
            locale: pageVar.locale,
            localeBox: pageVar.localeBox,
            localeUrlPrefix: pageVar.localeUrlPrefix,
            otCode: pageVar.otCode,
            bookiehash: pageVar.bookiehash,
            myot: pageVar.myot,
            myBookmakers: pageVar.myBookmakers,
            userData: pageVar.userData
          } : null,
          pageOutrightsVar: pageOutrightsVar ? {
            id: pageOutrightsVar.id,
            sid: pageOutrightsVar.sid,
            cid: pageOutrightsVar.cid,
            archive: pageOutrightsVar.archive
          } : null
        };
      });
    } catch (error) {
      this.logger.debug('pure_runtime_state_probe_failed', {
        traceId: this.traceId,
        error: error.message
      });
      return {
        locationHref: '',
        pageVar: null,
        pageOutrightsVar: null
      };
    }
  },

  async _readPageHtml(page) {
    if (!page) {
      return '';
    }

    try {
      if (typeof page.content === 'function') {
        return String(await page.content() || '');
      }
    } catch (error) {
      this.logger.debug('pure_runtime_page_content_failed', {
        traceId: this.traceId,
        error: error.message
      });
    }

    if (typeof page.evaluate !== 'function') {
      return '';
    }

    try {
      return await page.evaluate(() => String(document.documentElement?.outerHTML || ''));
    } catch (error) {
      this.logger.debug('pure_runtime_page_html_failed', {
        traceId: this.traceId,
        error: error.message
      });
      return '';
    }
  },

  _createPageBoundModuleLoader(page, referer = '') {
    return async (targetUrl) => {
      if (!page || typeof page.evaluate !== 'function') {
        throw new Error('PURE_RUNTIME_PAGE_UNAVAILABLE');
      }

      return page.evaluate(async ({ targetUrl, referer }) => {
        const resolvedUrl = new URL(String(targetUrl || ''), window.location.origin).href;
        const headers = referer ? { referer } : {};
        const response = await fetch(resolvedUrl, {
          credentials: 'include',
          headers
        });
        if (!response.ok) {
          throw new Error(`HTTP_${response.status}:${resolvedUrl}`);
        }
        return response.text();
      }, {
        targetUrl,
        referer
      });
    };
  },

  async _extractFromPureRuntime(page, appScriptUrl, sampleState = {}) {
    if (!page || !appScriptUrl) {
      return null;
    }

    try {
      const [runtimeState, html, bundleSource] = await Promise.all([
        this._readSerializableRuntimeState(page),
        this._readPageHtml(page),
        this._fetchBundleSource(page, appScriptUrl)
      ]);
      if (!bundleSource) {
        return null;
      }

      const decryptor = new ReconPureDecryptor({
        logger: this.logger,
        traceId: this.traceId
      });
      const referer = String(
        runtimeState?.locationHref
        || (typeof page.url === 'function' ? page.url() : '')
        || ''
      ).trim();
      await decryptor.loadFromBundleUrl(appScriptUrl, {
        sampleEncryptedData: sampleState?.primarySample || sampleState?.samplePool?.[0] || null,
        bundleSource,
        sourceLoader: this._createPageBoundModuleLoader(page, referer),
        html,
        headers: referer ? { referer } : {},
        globals: {
          pageVar: runtimeState?.pageVar || null,
          pageOutrightsVar: runtimeState?.pageOutrightsVar || null,
          location: referer ? { href: referer } : undefined
        }
      });

      const wrappedDecryptFn = async (encryptedData) => decryptor.decrypt(encryptedData);
      wrappedDecryptFn.__validated = decryptor.selectedCandidate?.validated !== false;
      wrappedDecryptFn.__bestEffort = false;
      wrappedDecryptFn.__algorithmVersion = decryptor.getAlgorithmVersion();
      wrappedDecryptFn.__extractMethod = 'pure_runtime';
      return wrappedDecryptFn;
    } catch (error) {
      this.logger.warn('pure_runtime_extraction_failed', {
        traceId: this.traceId,
        error: error.message
      });
      return null;
    }
  },

  async _extractFromInlineScripts(page) {
    try {
      const inlineDecryptor = await page.evaluate(() => {
        const scripts = Array.from(document.querySelectorAll('script:not([src])'));
        for (const script of scripts) {
          const text = script.textContent || '';
          const patterns = [
            /function\s+(\w+)\s*\([^)]*\)\s*\{[^}]*(?:decrypt|decode|parse|unpack)/i,
            /const\s+(\w+)\s*=\s*\([^)]*\)\s*=>\s*\{[^}]*(?:decrypt|decode|parse|unpack)/i,
            /var\s+(\w+)\s*=\s*function\s*\([^)]*\)\s*\{[^}]*(?:decrypt|decode|parse|unpack)/i,
            /window\.(\w+)\s*=\s*function\s*\([^)]*\)/i,
            /window\['(\w+)'\]\s*=\s*function\s*\([^)]*\)/i
          ];

          for (const pattern of patterns) {
            const match = text.match(pattern);
            if (match) {
              return {
                found: true,
                fnName: match[1],
                context: 'inline'
              };
            }
          }
        }

        return { found: false };
      });

      if (!inlineDecryptor.found) {
        return null;
      }

      this.algorithmVersion = `inline_${inlineDecryptor.fnName}`;
      return async (encryptedData) => page.evaluate((fnName, data) => {
        const fn = window[fnName];
        if (typeof fn === 'function') {
          return fn(data);
        }
        throw new Error(`Decryptor function ${fnName} not found in global scope`);
      }, inlineDecryptor.fnName, encryptedData);
    } catch (error) {
      if (this._isPageContextClosedError(error)) {
        this.logger.debug('inline_script_extraction_skipped_page_closed', {
          traceId: this.traceId
        });
      } else {
        this.logger.warn('inline_script_extraction_failed', { error: error.message });
      }
      return null;
    }
  },

  async _extractFromGlobalScope(page) {
    try {
      const globalDecryptor = await page.evaluate(() => {
        const commonNames = [
          'decrypt', 'decode', 'parseData', 'unpack', 'transform',
          'ai', 'process', 'handle', 'convert', '__decrypt',
          'oddsDecrypt', 'dataParser', 'responseHandler', 'deserialize',
          'decodePayload', 'decryptPayload', 'decodeResponse'
        ];

        for (const name of commonNames) {
          if (typeof window[name] === 'function') {
            return { found: true, fnName: name };
          }
        }

        for (const key of Object.keys(window)) {
          if (
            typeof window[key] === 'function'
            && (
              key.toLowerCase().includes('decrypt')
              || key.toLowerCase().includes('decode')
              || key.toLowerCase().includes('parse')
            )
          ) {
            return { found: true, fnName: key, detected: 'heuristic' };
          }
        }

        return { found: false };
      });

      if (!globalDecryptor.found) {
        return null;
      }

      this.algorithmVersion = `global_${globalDecryptor.fnName}`;
      return async (encryptedData) => page.evaluate((fnName, data) => window[fnName](data), globalDecryptor.fnName, encryptedData);
    } catch (error) {
      if (this._isPageContextClosedError(error)) {
        this.logger.debug('global_scope_extraction_skipped_page_closed', {
          traceId: this.traceId
        });
      } else {
        this.logger.warn('global_scope_extraction_failed', { error: error.message });
      }
      return null;
    }
  }
};

Object.assign(reconDecryptorSourceExtractor, reconDecryptorRuntimeUtils);

module.exports = { reconDecryptorSourceExtractor };
