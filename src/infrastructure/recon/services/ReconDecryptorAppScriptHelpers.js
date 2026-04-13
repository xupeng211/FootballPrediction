'use strict';

function hasValidSample(extractor, samplePool) {
  return samplePool.some((sample) => {
    const probe = extractor._probeEncryptedPayload(extractor._cleanPayload(sample));
    return probe.valid;
  });
}

async function prepareSamplePool(extractor, page, sampleInput, options = {}) {
  let samplePool = Array.isArray(sampleInput)
    ? sampleInput.filter((sample) => typeof sample === 'string' && sample.trim())
    : extractor._buildSamplePool(sampleInput);
  const hasPrimarySample = options.hasPrimarySample === true
    || (typeof sampleInput === 'string' && sampleInput.trim().length > 0);
  let primarySample = samplePool[0] || null;
  let hasValidPrimarySample = hasValidSample(extractor, samplePool);

  if (!hasValidPrimarySample || samplePool.length < extractor.sampleCrossValidateCount) {
    const randomCrossSampleTarget = 2 + extractor.randomInt(2);
    const desiredSampleCount = Math.max(extractor.sampleCrossValidateCount, randomCrossSampleTarget + 1);
    const extraSamples = await extractor._collectCrossValidationSamples(page, desiredSampleCount);
    for (const extraSample of extraSamples) {
      extractor.rememberSample(extraSample);
    }

    samplePool = extractor._buildSamplePool(primarySample);
    primarySample = samplePool[0] || null;
    hasValidPrimarySample = hasValidSample(extractor, samplePool);
  }

  return {
    hasPrimarySample,
    hasValidPrimarySample,
    primarySample,
    samplePool
  };
}

function inspectModuleCandidatesInPage({ url, samplePool, allowBestEffort, candidateNames }) {
  const collectCandidates = (module, names) => {
    const candidates = [];
    const seen = new Set();
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

    for (const name of names) {
      addCandidate(name, 'named_export');
    }
    addCandidate('default', 'default_export');
    for (const key of Object.keys(module)) {
      addCandidate(key, 'auto_detected');
    }

    return candidates;
  };

  const isValidPayload = (value) => {
    try {
      const raw = typeof value === 'string' ? value : JSON.stringify(value);
      if (!raw || typeof raw !== 'string') {
        return false;
      }

      const trimmed = raw.trim();
      if (!trimmed.startsWith('{') && !trimmed.startsWith('[')) {
        return false;
      }

      const parsed = typeof value === 'object' && value !== null ? value : JSON.parse(trimmed);
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

  const validateCandidateSamples = async (module, candidate, encryptedSamples) => {
    const fn = candidate.name === 'default' ? module.default : module[candidate.name];
    let validatedSamples = 0;
    for (const sample of encryptedSamples) {
      try {
        const output = await fn(sample);
        if (isValidPayload(output)) {
          validatedSamples++;
        }
      } catch {
        continue;
      }
    }

    return validatedSamples;
  };

  const selectBestEffortCandidate = (candidates) => {
    const bestEffortCandidate = candidates.find((candidate) => candidate.name === 'ai')
      || candidates.find((candidate) => candidate.type === 'named_export')
      || candidates[0];
    return bestEffortCandidate
      ? {
          found: true,
          name: bestEffortCandidate.name,
          type: bestEffortCandidate.type,
          validated: false,
          bestEffort: true
        }
      : { found: false, validated: false };
  };

  return (async () => {
    try {
      const module = await import(url);
      const possibleNames = Array.isArray(candidateNames) && candidateNames.length > 0
        ? candidateNames
        : ['ai', 'decrypt', 'decode', 'parse', 'unpack', 'transform', 'deserialize', 'unzip'];
      const candidates = collectCandidates(module, possibleNames);

      if (Array.isArray(samplePool) && samplePool.length > 0) {
        for (const candidate of candidates) {
          const validatedSamples = await validateCandidateSamples(module, candidate, samplePool);
          if (validatedSamples > 0) {
            return {
              found: true,
              name: candidate.name,
              type: candidate.type,
              validated: true,
              validatedSamples,
              sampleCount: samplePool.length
            };
          }
        }
      }

      return allowBestEffort ? selectBestEffortCandidate(candidates) : { found: false, validated: false };
    } catch (error) {
      return { found: false, error: error.message };
    }
  })();
}

async function probeAppScriptCandidate(extractor, page, appScriptUrl, sampleState, candidateNames) {
  return page.evaluate(inspectModuleCandidatesInPage, {
    url: appScriptUrl,
    samplePool: sampleState.samplePool,
    allowBestEffort: extractor.allowBestEffortCandidate && (!sampleState.hasPrimarySample || sampleState.hasValidPrimarySample),
    candidateNames
  });
}

function logInvalidPrimarySample(extractor, sampleState) {
  const sampleProbe = sampleState.primarySample
    ? extractor._probeEncryptedPayload(extractor._cleanPayload(sampleState.primarySample))
    : null;
  if (!sampleState.primarySample || !sampleProbe || sampleProbe.valid) {
    return;
  }

  extractor.logger.debug('app_script_sample_invalid_skip_best_effort', {
    traceId: extractor.traceId,
    preview: sampleProbe.preview || '',
    samplePoolSize: sampleState.samplePool.length
  });
}

function wrapDecryptFunction(page, appScriptUrl, decryptFn, algorithmVersion) {
  const wrappedDecryptFn = async (encryptedData) => page.evaluate(async ({ url, fnName, data }) => {
    const mod = await import(url);
    const fn = fnName === 'default' ? mod.default : mod[fnName];
    return fn(data);
  }, {
    url: appScriptUrl,
    fnName: decryptFn.name,
    data: encryptedData
  });

  wrappedDecryptFn.__validated = decryptFn.validated !== false;
  wrappedDecryptFn.__bestEffort = decryptFn.bestEffort === true;
  wrappedDecryptFn.__algorithmVersion = algorithmVersion;
  return wrappedDecryptFn;
}

async function extractFromAppScript(page, sampleInput = null, options = {}) {
  try {
    const sampleState = await prepareSamplePool(this, page, sampleInput, options);
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

    const bundleSource = await this._fetchBundleSource(page, appScriptUrl);
    const decryptFn = await probeAppScriptCandidate(
      this,
      page,
      appScriptUrl,
      sampleState,
      this._extractFromBundle(bundleSource)
    );
    logInvalidPrimarySample(this, sampleState);

    if (!decryptFn || !decryptFn.found) {
      if (sampleState.samplePool.length > 0) {
        this.logger.warn('app_script_candidate_rejected', {
          reason: 'sample_validation_failed',
          samplePoolSize: sampleState.samplePool.length
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

    return wrapDecryptFunction(page, appScriptUrl, decryptFn, algorithmVersion);
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
}

function collectCrossSamplesInPage({ sampleLimit }) {
  const collected = [];
  const seen = new Set();
  const endpoints = [];
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
    if (typeof entry?.name === 'string' && /ajax-sport-country-tournament-archive_/i.test(entry.name)) {
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

  return (async () => {
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

        pushSample(await response.text());
      } catch {
        continue;
      }
    }

    return collected.slice(0, sampleLimit);
  })();
}

async function collectCrossValidationSamples(page, maxSamples = 3) {
  if (!page || typeof page.evaluate !== 'function' || typeof page.waitForFunction !== 'function') {
    return [];
  }

  try {
    const samples = await page.evaluate(collectCrossSamplesInPage, {
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
}

module.exports = {
  extractFromAppScript,
  collectCrossValidationSamples
};
