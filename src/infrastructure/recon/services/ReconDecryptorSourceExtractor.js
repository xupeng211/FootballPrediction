'use strict';

const { reconDecryptorRuntimeUtils } = require('./ReconDecryptorRuntimeUtils');

const reconDecryptorSourceExtractor = {
  async _extractFromAppScript(page, sampleInput = null, options = {}) {
    try {
      let samplePool = Array.isArray(sampleInput)
        ? sampleInput.filter((sample) => typeof sample === 'string' && sample.trim())
        : this._buildSamplePool(sampleInput);
      const hasPrimarySample = options.hasPrimarySample === true
        || (typeof sampleInput === 'string' && sampleInput.trim().length > 0);
      let primarySample = samplePool[0] || null;
      let hasValidSample = samplePool.some((sample) => {
        const probe = this._probeEncryptedPayload(this._cleanPayload(sample));
        return probe.valid;
      });

      if (!hasValidSample || samplePool.length < this.sampleCrossValidateCount) {
        const randomCrossSampleTarget = 2 + this.randomInt(2);
        const desiredSampleCount = Math.max(this.sampleCrossValidateCount, randomCrossSampleTarget + 1);
        const extraSamples = await this._collectCrossValidationSamples(page, desiredSampleCount);
        for (const extraSample of extraSamples) {
          this.rememberSample(extraSample);
        }
        samplePool = this._buildSamplePool(primarySample);
        primarySample = samplePool[0] || null;
        hasValidSample = samplePool.some((sample) => {
          const probe = this._probeEncryptedPayload(this._cleanPayload(sample));
          return probe.valid;
        });
      }

      await this._waitForDecryptorReady(page);

      const appScriptUrl = await page.evaluate(() => {
        const script = Array.from(document.querySelectorAll('script[src*="/build/assets/app-"]'))
          .map((item) => item.src)
          .find(Boolean);
        return script;
      });

      if (!appScriptUrl) {
        return null;
      }

      const sampleProbe = primarySample
        ? this._probeEncryptedPayload(this._cleanPayload(primarySample))
        : null;
      const bundleSource = await this._fetchBundleSource(page, appScriptUrl);
      const bundleCandidateNames = this._extractFromBundle(bundleSource);

      if (primarySample && sampleProbe && !sampleProbe.valid) {
        this.logger.debug('app_script_sample_invalid_skip_best_effort', {
          traceId: this.traceId,
          preview: sampleProbe.preview || '',
          samplePoolSize: samplePool.length
        });
      }

      const decryptFn = await page.evaluate(async ({ url, samplePool: encryptedSamples, allowBestEffort, candidateNames }) => {
        try {
          const module = await import(url);
          const candidates = [];
          const seen = new Set();
          const possibleNames = Array.isArray(candidateNames) && candidateNames.length > 0
            ? candidateNames
            : ['ai', 'decrypt', 'decode', 'parse', 'unpack', 'transform', 'deserialize', 'unzip'];

          const addCandidate = (name, type) => {
            if (!name || seen.has(name)) {
              return;
            }

            const fn = name === 'default' ? module.default : module[name];
            if (typeof fn === 'function') {
              seen.add(name);
              candidates.push({ name, type });
            }
          };

          for (const name of possibleNames) {
            addCandidate(name, 'named_export');
          }

          addCandidate('default', 'default_export');

          for (const key of Object.keys(module)) {
            addCandidate(key, 'auto_detected');
          }

          const isValidPayload = (value) => {
            try {
              const raw = typeof value === 'string' ? value : JSON.stringify(value);
              if (!raw || typeof raw !== 'string') return false;

              const trimmed = raw.trim();
              if (!trimmed.startsWith('{') && !trimmed.startsWith('[')) {
                return false;
              }

              const parsed = typeof value === 'object' && value !== null
                ? value
                : JSON.parse(trimmed);

              return Boolean(parsed && typeof parsed === 'object' && (
                parsed.d
                || parsed.rows
                || parsed.s !== undefined
                || parsed.refresh !== undefined
              ));
            } catch {
              return false;
            }
          };

          if (Array.isArray(encryptedSamples) && encryptedSamples.length > 0) {
            for (const candidate of candidates) {
              let validatedSamples = 0;
              const fn = candidate.name === 'default' ? module.default : module[candidate.name];

              for (const sample of encryptedSamples) {
                try {
                  const output = await fn(sample);
                  if (isValidPayload(output)) {
                    validatedSamples++;
                  }
                } catch {
                  // ignore and continue probing
                }
              }

              if (validatedSamples > 0) {
                return {
                  found: true,
                  name: candidate.name,
                  type: candidate.type,
                  validated: true,
                  validatedSamples,
                  sampleCount: encryptedSamples.length
                };
              }
            }
          }

          if (allowBestEffort && candidates.length > 0) {
            const bestEffortCandidate = candidates.find((candidate) => candidate.name === 'ai')
              || candidates.find((candidate) => candidate.type === 'named_export')
              || candidates[0];

            return {
              found: true,
              name: bestEffortCandidate.name,
              type: bestEffortCandidate.type,
              validated: false,
              bestEffort: true
            };
          }

          return { found: false, validated: false };
        } catch (error) {
          return { found: false, error: error.message };
        }
      }, {
        url: appScriptUrl,
        samplePool,
        allowBestEffort: this.allowBestEffortCandidate && (!hasPrimarySample || hasValidSample),
        candidateNames: bundleCandidateNames
      });

      if (!decryptFn || !decryptFn.found) {
        if (samplePool.length > 0) {
          this.logger.warn('app_script_candidate_rejected', {
            reason: 'sample_validation_failed',
            samplePoolSize: samplePool.length
          });
        }
        return null;
      }

      const algorithmVersion = `app_${decryptFn.name}`;
      this.algorithmVersion = algorithmVersion;
      if (decryptFn.bestEffort) {
        this.logger.warn('app_script_best_effort_selected', {
          candidate: decryptFn.name,
          validated: false
        });
      }

      const wrappedDecryptFn = async (encryptedData) => page.evaluate(async ({ url, fnName, data }) => {
        const mod = await import(url);
        const fn = fnName === 'default' ? mod.default : mod[fnName];
        return fn(data);
      }, { url: appScriptUrl, fnName: decryptFn.name, data: encryptedData });

      wrappedDecryptFn.__validated = decryptFn.validated !== false;
      wrappedDecryptFn.__bestEffort = decryptFn.bestEffort === true;
      wrappedDecryptFn.__algorithmVersion = algorithmVersion;
      return wrappedDecryptFn;
    } catch (error) {
      if (this._isPageContextClosedError(error)) {
        this.logger.debug('app_script_extraction_skipped_page_closed', {
          traceId: this.traceId
        });
      } else {
        this.logger.warn('app_script_extraction_failed', { error: error.message });
      }
      return null;
    }
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
        () => Boolean(document.querySelector('script[src*="/build/assets/app-"]')),
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
    if (!page || typeof page.evaluate !== 'function' || typeof page.waitForFunction !== 'function') {
      return [];
    }

    try {
      const samples = await page.evaluate(async ({ sampleLimit }) => {
        const collected = [];
        const seen = new Set();
        const pushSample = (value) => {
          if (typeof value !== 'string') {
            return;
          }

          const trimmed = value.trim();
          if (!trimmed || seen.has(trimmed)) {
            return;
          }

          seen.add(trimmed);
          collected.push(trimmed);
        };

        const endpoints = [];
        const addEndpoint = (url) => {
          if (!url || typeof url !== 'string') {
            return;
          }

          const normalized = url.trim();
          if (!normalized || endpoints.includes(normalized)) {
            return;
          }

          endpoints.push(normalized);
        };

        const resourceEntries = Array.isArray(performance.getEntriesByType('resource'))
          ? performance.getEntriesByType('resource')
          : [];
        for (const entry of resourceEntries) {
          if (!entry?.name || typeof entry.name !== 'string') {
            continue;
          }
          if (/ajax-sport-country-tournament-archive_/i.test(entry.name)) {
            addEndpoint(entry.name);
          }
        }

        const otCode = typeof window.pageVar?.otCode === 'string'
          ? window.pageVar.otCode.trim()
          : (typeof window.pageOutrightsVar?.id === 'string' ? window.pageOutrightsVar.id.trim() : '');
        const seasonMatch = String(window.location?.pathname || '').match(/(\d{4}-\d{4})/);
        const season = seasonMatch ? seasonMatch[1] : '';
        const candidateHashes = [];
        if (typeof window.pageVar?.bookiehash === 'string' && window.pageVar.bookiehash.trim()) {
          candidateHashes.push(window.pageVar.bookiehash.trim());
        }
        candidateHashes.push('X');

        if (otCode && season) {
          for (const hash of candidateHashes) {
            addEndpoint(`https://www.oddsportal.com/ajax-sport-country-tournament-archive_/1/${otCode}/${hash}/${season}/1/0/?_=${Date.now()}`);
          }
        }

        for (const endpoint of endpoints) {
          if (collected.length >= sampleLimit) {
            break;
          }

          try {
            const response = await fetch(endpoint, {
              credentials: 'include',
              headers: {
                'x-requested-with': 'XMLHttpRequest'
              }
            });
            if (!response.ok) {
              continue;
            }

            const text = await response.text();
            pushSample(text);
          } catch {
            // ignore and continue
          }
        }

        return collected.slice(0, sampleLimit);
      }, {
        sampleLimit: Math.max(1, Number(maxSamples || 3))
      });

      return Array.isArray(samples) ? samples : [];
    } catch (error) {
      this.logger.debug('decryptor_cross_sample_collect_failed', {
        traceId: this.traceId,
        error: error.message
      });
      return [];
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
