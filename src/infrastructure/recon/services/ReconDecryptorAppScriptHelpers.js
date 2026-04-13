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

function buildAppScriptImportUrls(appScriptUrl = '') {
  const urls = [];
  const pushUnique = (value) => {
    const normalized = String(value || '').trim();
    if (normalized && !urls.includes(normalized)) {
      urls.push(normalized);
    }
  };

  pushUnique(appScriptUrl);
  try {
    pushUnique(new URL(appScriptUrl).pathname);
  } catch {
    // keep original absolute URL only
  }

  return urls;
}

function normalizeSerializableState(value) {
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
}

function pushUniqueTrimmed(bucket, value) {
  const normalized = String(value || '').trim();
  if (!normalized || bucket.includes(normalized)) {
    return;
  }
  bucket.push(normalized);
}

function collectReplayEndpoints() {
  const endpoints = [];
  const resourceEntries = Array.isArray(performance.getEntriesByType('resource'))
    ? performance.getEntriesByType('resource')
    : [];

  for (const entry of resourceEntries) {
    if (
      typeof entry?.name === 'string'
      && /ajax-sport-country-tournament(?:-archive)?_/i.test(entry.name)
    ) {
      pushUniqueTrimmed(endpoints, entry.name);
    }
  }

  return endpoints;
}

function collectSeasonTokensFromDom(pathname, documentRef) {
  const seasonTokens = [];
  const pathMatches = String(pathname || '').match(/(\d{4}(?:-\d{4})?)/g) || [];
  for (const match of pathMatches) {
    pushUniqueTrimmed(seasonTokens, match);
  }

  const linkedSeasons = Array.from(
    documentRef.querySelectorAll('a[href*="/results/"], a[href*="/fixtures/"]')
  )
    .map((node) => String(node.getAttribute('href') || ''))
    .flatMap((href) => href.match(/-(\d{4}(?:-\d{4})?)(?:\/|$)/g) || [])
    .map((token) => token.replace(/^-/, '').replace(/\/$/, '').trim());

  for (const token of linkedSeasons) {
    pushUniqueTrimmed(seasonTokens, token);
    if (/^\d{4}$/.test(token)) {
      pushUniqueTrimmed(seasonTokens, String(Number(token) + 1));
      pushUniqueTrimmed(seasonTokens, `${token}-${Number(token) + 1}`);
    }
  }

  return seasonTokens;
}

function collectCandidateHashes(pageVar) {
  const candidateHashes = [];
  if (typeof pageVar?.bookiehash === 'string' && pageVar.bookiehash.trim()) {
    pushUniqueTrimmed(candidateHashes, pageVar.bookiehash);
  }
  if (typeof pageVar?.myot === 'string' && pageVar.myot.trim()) {
    pushUniqueTrimmed(candidateHashes, pageVar.myot);
  }
  pushUniqueTrimmed(candidateHashes, 'X');
  return candidateHashes;
}

function buildTournamentEndpoints(otCode, candidateHashes, seasonTokens) {
  if (!otCode) {
    return [];
  }

  const endpoints = [];
  const cacheBust = Date.now();
  for (const hash of candidateHashes) {
    pushUniqueTrimmed(
      endpoints,
      `https://www.oddsportal.com/ajax-sport-country-tournament_/1/${otCode}/${hash}/1/?_=${cacheBust}`
    );
  }
  for (const seasonToken of seasonTokens) {
    for (const hash of candidateHashes) {
      pushUniqueTrimmed(
        endpoints,
        `https://www.oddsportal.com/ajax-sport-country-tournament-archive_/1/${otCode}/${hash}/${seasonToken}/1/0/?_=${cacheBust}`
      );
    }
  }

  return endpoints;
}

function inspectModuleCandidatesInPage({ urls, samplePool, allowBestEffort, candidateNames }) {
  const normalizeSerializableStateInPage = (value) => {
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

  const normalizeWindowState = () => {
    const pageVar = normalizeSerializableStateInPage(window.pageVar);
    const pageOutrightsVar = normalizeSerializableStateInPage(window.pageOutrightsVar);
    if (pageVar && typeof window.pageVar === 'string') {
      window.pageVar = pageVar;
    }
    if (pageOutrightsVar && typeof window.pageOutrightsVar === 'string') {
      window.pageOutrightsVar = pageOutrightsVar;
    }
  };

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
    normalizeWindowState();
    let lastImportError = '';
    let lastCandidates = [];
    try {
      const possibleNames = Array.isArray(candidateNames) && candidateNames.length > 0
        ? candidateNames
        : ['ai', 'decrypt', 'decode', 'parse', 'unpack', 'transform', 'deserialize', 'unzip'];
      const importUrls = Array.isArray(urls) && urls.length > 0 ? urls : [];

      for (const importUrl of importUrls) {
        try {
          const module = await import(importUrl);
          const candidates = collectCandidates(module, possibleNames);
          lastCandidates = candidates;

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

          if (allowBestEffort) {
            const bestEffort = selectBestEffortCandidate(candidates);
            if (bestEffort.found) {
              return bestEffort;
            }
          }
        } catch (error) {
          lastImportError = error.message;
        }
      }

      return {
        ...(allowBestEffort ? selectBestEffortCandidate(lastCandidates) : { found: false, validated: false }),
        error: lastImportError
      };
    } catch (error) {
      return { found: false, error: error.message };
    }
  })();
}

async function probeAppScriptCandidate(extractor, page, appScriptUrl, sampleState, candidateNames) {
  const importUrls = buildAppScriptImportUrls(appScriptUrl);
  return page.evaluate(inspectModuleCandidatesInPage, {
    url: importUrls[0] || String(appScriptUrl || ''),
    urls: importUrls,
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
      const script = Array.from(document.querySelectorAll('script[src*="/build/assets/app"]'))
        .map((item) => item.src)
        .find(Boolean);
      return script;
    });
    if (!appScriptUrl) {
      return null;
    }

    const appScriptResolution = typeof this._resolveLiveAppScript === 'function'
      ? await this._resolveLiveAppScript(page, appScriptUrl)
      : { appScriptUrl, bundleSource: '' };
    const resolvedAppScriptUrl = appScriptResolution.appScriptUrl || appScriptUrl;
    const bundleSource = appScriptResolution.bundleSource || await this._fetchBundleSource(page, resolvedAppScriptUrl);
    const decryptFn = await probeAppScriptCandidate(
      this,
      page,
      resolvedAppScriptUrl,
      sampleState,
      this._extractFromBundle(bundleSource)
    );
    logInvalidPrimarySample(this, sampleState);

    if (!decryptFn || !decryptFn.found) {
      const pureRuntimeDecryptFn = typeof this._extractFromPureRuntime === 'function'
        ? await this._extractFromPureRuntime(page, resolvedAppScriptUrl, sampleState)
        : null;
      if (pureRuntimeDecryptFn) {
        this.algorithmVersion = pureRuntimeDecryptFn.__algorithmVersion || this.algorithmVersion;
        return pureRuntimeDecryptFn;
      }

      if (sampleState.samplePool.length > 0) {
        this.logger.warn('app_script_candidate_rejected', {
          reason: 'sample_validation_failed',
          samplePoolSize: sampleState.samplePool.length,
          error: decryptFn?.error || null
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

    return wrapDecryptFunction(page, resolvedAppScriptUrl, decryptFn, algorithmVersion);
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
  const normalizeSerializableStateInPage = (value) => {
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
  const pushUniqueTrimmedInPage = (bucket, value) => {
    const normalized = String(value || '').trim();
    if (!normalized || bucket.includes(normalized)) {
      return;
    }
    bucket.push(normalized);
  };
  const collectReplayEndpointsInPage = () => {
    const endpoints = [];
    const resourceEntries = Array.isArray(performance.getEntriesByType('resource'))
      ? performance.getEntriesByType('resource')
      : [];

    for (const entry of resourceEntries) {
      if (
        typeof entry?.name === 'string'
        && /ajax-sport-country-tournament(?:-archive)?_/i.test(entry.name)
      ) {
        pushUniqueTrimmedInPage(endpoints, entry.name);
      }
    }

    return endpoints;
  };
  const collectSeasonTokensFromDomInPage = (pathname, documentRef) => {
    const seasonTokens = [];
    const pathMatches = String(pathname || '').match(/(\d{4}(?:-\d{4})?)/g) || [];
    for (const match of pathMatches) {
      pushUniqueTrimmedInPage(seasonTokens, match);
    }

    const linkedSeasons = Array.from(
      documentRef.querySelectorAll('a[href*="/results/"], a[href*="/fixtures/"]')
    )
      .map((node) => String(node.getAttribute('href') || ''))
      .flatMap((href) => href.match(/-(\d{4}(?:-\d{4})?)(?:\/|$)/g) || [])
      .map((token) => token.replace(/^-/, '').replace(/\/$/, '').trim());

    for (const token of linkedSeasons) {
      pushUniqueTrimmedInPage(seasonTokens, token);
      if (/^\d{4}$/.test(token)) {
        pushUniqueTrimmedInPage(seasonTokens, String(Number(token) + 1));
        pushUniqueTrimmedInPage(seasonTokens, `${token}-${Number(token) + 1}`);
      }
    }

    return seasonTokens;
  };
  const collectCandidateHashesInPage = (pageVar) => {
    const candidateHashes = [];
    if (typeof pageVar?.bookiehash === 'string' && pageVar.bookiehash.trim()) {
      pushUniqueTrimmedInPage(candidateHashes, pageVar.bookiehash);
    }
    if (typeof pageVar?.myot === 'string' && pageVar.myot.trim()) {
      pushUniqueTrimmedInPage(candidateHashes, pageVar.myot);
    }
    pushUniqueTrimmedInPage(candidateHashes, 'X');
    return candidateHashes;
  };
  const buildTournamentEndpointsInPage = (otCode, candidateHashes, seasonTokens) => {
    if (!otCode) {
      return [];
    }

    const endpoints = [];
    const cacheBust = Date.now();
    for (const hash of candidateHashes) {
      pushUniqueTrimmedInPage(
        endpoints,
        `https://www.oddsportal.com/ajax-sport-country-tournament_/1/${otCode}/${hash}/1/?_=${cacheBust}`
      );
    }
    for (const seasonToken of seasonTokens) {
      for (const hash of candidateHashes) {
        pushUniqueTrimmedInPage(
          endpoints,
          `https://www.oddsportal.com/ajax-sport-country-tournament-archive_/1/${otCode}/${hash}/${seasonToken}/1/0/?_=${cacheBust}`
        );
      }
    }

    return endpoints;
  };
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
  const pageVar = normalizeSerializableStateInPage(window.pageVar);
  const pageOutrightsVar = normalizeSerializableStateInPage(window.pageOutrightsVar);
  const otCode = typeof pageVar?.otCode === 'string'
    ? pageVar.otCode.trim()
    : (typeof pageOutrightsVar?.id === 'string' ? pageOutrightsVar.id.trim() : '');
  const seasonTokens = collectSeasonTokensFromDomInPage(window.location?.pathname || '', document);
  const candidateHashes = collectCandidateHashesInPage(pageVar);
  const endpoints = [
    ...collectReplayEndpointsInPage(),
    ...buildTournamentEndpointsInPage(otCode, candidateHashes, seasonTokens)
  ];

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
