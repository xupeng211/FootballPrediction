'use strict';

const path = require('node:path');
const { JSDOM } = require('jsdom');

const { ReconPureDecryptor } = require('./ReconPureDecryptor');
const { reconDecryptorRuntimeUtils } = require('./ReconDecryptorRuntimeUtils');
const {
  extractFromAppScript,
  collectCrossValidationSamples
} = require('./ReconDecryptorAppScriptHelpers');

function normalizeHeaderBag(headers = {}) {
  return Object.fromEntries(
    Object.entries(headers || {})
      .filter(([, value]) => value !== null && value !== undefined && String(value).trim() !== '')
      .map(([key, value]) => [key, String(value).trim()])
  );
}

function buildAssetFetchHeaders(baseUrl = '', headers = {}, accept = '*/*') {
  let origin = '';
  try {
    origin = new URL(baseUrl || headers.referer || 'https://www.oddsportal.com/').origin;
  } catch {
    origin = 'https://www.oddsportal.com';
  }

  return normalizeHeaderBag({
    accept,
    'accept-language': 'en-US,en;q=0.9,ja-JP;q=0.8,ja;q=0.7',
    referer: headers.referer || baseUrl || `${origin}/`,
    origin: headers.origin || origin,
    'user-agent': headers['user-agent'] || headers.userAgent || 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36',
    cookie: headers.cookie || '',
    ...headers
  });
}

async function fetchTextViaNode(url, headers = {}, accept = '*/*') {
  if (typeof globalThis.fetch !== 'function') {
    return { success: false, status: null, text: '', error: 'FETCH_UNAVAILABLE' };
  }

  try {
    const response = await globalThis.fetch(url, {
      headers: buildAssetFetchHeaders(url, headers, accept),
      redirect: 'follow'
    });
    const text = await response.text();
    return {
      success: response.ok,
      status: Number(response.status) || null,
      text,
      finalUrl: response.url || url,
      error: response.ok ? '' : `HTTP_${response.status}:${url}`
    };
  } catch (error) {
    return {
      success: false,
      status: null,
      text: '',
      finalUrl: url,
      error: error.message
    };
  }
}

async function fetchStaticAssetViaNode(url, headers = {}) {
  const result = await fetchTextViaNode(url, headers, 'text/javascript,application/javascript,*/*;q=0.1');
  return result.success ? result.text : '';
}

function extractAppScriptCandidatesFromHtml(html = '', baseUrl = '') {
  if (!html) {
    return [];
  }

  try {
    const dom = new JSDOM(String(html || ''));
    const nodes = Array.from(dom.window.document.querySelectorAll(
      'script[src*="/build/assets/app-"], link[rel="modulepreload"][href*="/build/assets/app-"]'
    ));
    const candidates = [];
    for (const node of nodes) {
      const rawUrl = String(node.getAttribute('src') || node.getAttribute('href') || '').trim();
      if (!/\/build\/assets\/app-[^/]+\.js(?:[?#].*)?$/i.test(rawUrl)) {
        continue;
      }

      try {
        const absoluteUrl = new URL(rawUrl, baseUrl || 'https://www.oddsportal.com/').href;
        if (!candidates.includes(absoluteUrl)) {
          candidates.push(absoluteUrl);
        }
      } catch {
        // ignore malformed asset candidate
      }
    }
    return candidates;
  } catch {
    return [];
  }
}

function resolveManifestBaseUrl(baseUrl = '') {
  try {
    return new URL('/build/manifest.json', baseUrl || 'https://www.oddsportal.com/').href;
  } catch {
    return 'https://www.oddsportal.com/build/manifest.json';
  }
}

async function fetchBuildManifest(baseUrl = '', headers = {}) {
  const manifestUrl = resolveManifestBaseUrl(baseUrl);
  const result = await fetchTextViaNode(manifestUrl, headers, 'application/json,text/plain,*/*');
  if (!result.success || !String(result.text || '').trim()) {
    return { manifestUrl, manifest: null };
  }

  try {
    return { manifestUrl, manifest: JSON.parse(result.text) };
  } catch {
    return { manifestUrl, manifest: null };
  }
}

function buildManifestAssetAliasMap(manifest = {}, manifestUrl = '') {
  const aliasMap = new Map();
  const addAlias = (alias, targetUrl) => {
    const normalizedAlias = String(alias || '').trim();
    const normalizedTargetUrl = String(targetUrl || '').trim();
    if (!normalizedAlias || !normalizedTargetUrl || aliasMap.has(normalizedAlias)) {
      return;
    }
    aliasMap.set(normalizedAlias, normalizedTargetUrl);
  };

  for (const [key, value] of Object.entries(manifest || {})) {
    const file = String(value?.file || '').trim();
    if (!/\.js(?:[?#].*)?$/i.test(file)) {
      continue;
    }

    let absoluteUrl = '';
    try {
      absoluteUrl = new URL(file, manifestUrl || 'https://www.oddsportal.com/build/manifest.json').href;
    } catch {
      continue;
    }

    const fileName = path.posix.basename(file);
    const fileStem = fileName.replace(/\.[^.]+$/u, '');
    const normalizedStem = fileStem.replace(/-[A-Za-z0-9_-]{6,}$/u, '');
    const keyStem = path.posix.basename(String(key || '').trim()).replace(/\.[^.]+$/u, '');
    const manifestName = String(value?.name || '').trim();

    for (const alias of [fileStem, normalizedStem, keyStem, manifestName]) {
      addAlias(alias, absoluteUrl);
    }
  }

  return aliasMap;
}

function extractManifestAppCandidates(manifest = {}, manifestUrl = '') {
  const candidates = [];
  for (const [key, value] of Object.entries(manifest || {})) {
    const file = String(value?.file || '').trim();
    if (!/assets\/app-[^/]+\.js(?:[?#].*)?$/i.test(file)) {
      continue;
    }
    if (
      key !== 'resources/js/app.js'
      && key !== 'resources/js/app.ts'
      && String(value?.name || '').trim() !== 'app'
      && value?.isEntry !== true
    ) {
      continue;
    }

    try {
      const absoluteUrl = new URL(file, manifestUrl || 'https://www.oddsportal.com/build/manifest.json').href;
      if (!candidates.includes(absoluteUrl)) {
        candidates.push(absoluteUrl);
      }
    } catch {
      // ignore malformed manifest asset
    }
  }

  return candidates;
}

async function validateAppScriptCandidate(candidateUrl, baseUrl = '', headers = {}) {
  const result = await fetchTextViaNode(
    candidateUrl,
    {
      ...headers,
      referer: headers.referer || baseUrl || headers.origin || ''
    },
    'text/javascript,application/javascript,*/*;q=0.1'
  );
  if (!result.success || !String(result.text || '').trim()) {
    return {
      success: false,
      appScriptUrl: candidateUrl,
      status: result.status,
      error: result.error || 'APP_SCRIPT_FETCH_FAILED'
    };
  }

  return {
    success: true,
    appScriptUrl: candidateUrl,
    bundleSource: result.text,
    status: result.status
  };
}

// eslint-disable-next-line complexity
async function findLatestAppScript(baseUrl = '', options = {}) {
  const logger = options.logger || console;
  const traceId = options.traceId || 'trace-app-script';
  const requestHeaders = normalizeHeaderBag(options.headers || {});
  const attempted = [];
  const validatedCandidates = [];
  const htmlCandidates = Array.isArray(options.candidateUrls)
    ? options.candidateUrls.map((url) => String(url || '').trim()).filter(Boolean)
    : [];
  const htmlSources = [];

  if (typeof options.html === 'string' && options.html.trim()) {
    htmlSources.push({
      source: 'base_html',
      html: options.html,
      baseUrl
    });
  } else {
    const htmlResult = await fetchTextViaNode(
      baseUrl,
      requestHeaders,
      'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
    );
    if (htmlResult.success && String(htmlResult.text || '').trim()) {
      htmlSources.push({
        source: 'base_html',
        html: htmlResult.text,
        baseUrl
      });
    }
  }

  const rootUrl = (() => {
    try {
      return new URL('/', baseUrl || 'https://www.oddsportal.com/').href;
    } catch {
      return 'https://www.oddsportal.com/';
    }
  })();

  if (options.allowRootFallback !== false) {
    const rootHtmlResult = await fetchTextViaNode(
      rootUrl,
      requestHeaders,
      'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
    );
    if (rootHtmlResult.success && String(rootHtmlResult.text || '').trim()) {
      htmlSources.push({
        source: 'root_html',
        html: rootHtmlResult.text,
        baseUrl: rootUrl
      });
    }
  }

  const { manifestUrl, manifest } = await fetchBuildManifest(baseUrl, requestHeaders);
  const manifestAssetMap = buildManifestAssetAliasMap(manifest || {}, manifestUrl);
  const candidateGroups = [
    {
      source: 'input_candidate',
      urls: htmlCandidates
    },
    ...htmlSources.map((entry) => ({
      source: entry.source,
      urls: extractAppScriptCandidatesFromHtml(entry.html, entry.baseUrl)
    })),
    {
      source: 'build_manifest',
      urls: extractManifestAppCandidates(manifest || {}, manifestUrl)
    }
  ];

  for (const group of candidateGroups) {
    for (const candidateUrl of group.urls) {
      if (validatedCandidates.includes(candidateUrl)) {
        continue;
      }
      validatedCandidates.push(candidateUrl);

      const validation = await validateAppScriptCandidate(candidateUrl, baseUrl, requestHeaders);
      attempted.push({
        source: group.source,
        url: candidateUrl,
        status: validation.status,
        error: validation.error || ''
      });
      if (!validation.success) {
        logger.debug?.('app_script_candidate_rejected', {
          traceId,
          source: group.source,
          url: candidateUrl,
          statusCode: validation.status,
          error: validation.error || ''
        });
        continue;
      }

      logger.info?.('app_script_bundle_fetch_success', {
        traceId,
        source: group.source,
        url: candidateUrl,
        statusCode: validation.status
      });
      return {
        appScriptUrl: candidateUrl,
        bundleSource: validation.bundleSource,
        discoverySource: group.source,
        manifestAssetMap,
        manifestUrl,
        attempted
      };
    }
  }

  return {
    appScriptUrl: '',
    bundleSource: '',
    discoverySource: 'unresolved',
    manifestAssetMap,
    manifestUrl,
    attempted
  };
}

const reconDecryptorSourceExtractor = {
  async _extractFromAppScript(page, sampleInput = null, options = {}) {
    return extractFromAppScript.call(this, page, sampleInput, options);
  },

  async _readPageCookieHeader(page) {
    if (!page || typeof page.evaluate !== 'function') {
      return '';
    }

    try {
      return String(await page.evaluate(() => String(document.cookie || '')) || '').trim();
    } catch {
      return '';
    }
  },

  async _resolveLiveAppScript(page, appScriptUrl = '', options = {}) {
    const baseUrl = typeof page?.url === 'function'
      ? String(page.url() || '').trim()
      : String(options.baseUrl || '').trim();
    const cookieHeader = await this._readPageCookieHeader(page);
    const resolution = await findLatestAppScript(baseUrl || appScriptUrl, {
      ...options,
      candidateUrls: [appScriptUrl, ...(Array.isArray(options.candidateUrls) ? options.candidateUrls : [])],
      logger: this.logger,
      traceId: this.traceId,
      headers: {
        referer: baseUrl || appScriptUrl,
        cookie: cookieHeader,
        ...(options.headers || {})
      }
    });

    this._lastResolvedAppScriptUrl = resolution.appScriptUrl || appScriptUrl || '';
    this._lastResolvedAppScriptManifestMap = resolution.manifestAssetMap || new Map();
    return resolution;
  },

  // eslint-disable-next-line complexity
  async _fetchBundleSource(page, appScriptUrl) {
    const referer = typeof page?.url === 'function'
      ? String(page.url() || '').trim()
      : '';
    const resolution = await this._resolveLiveAppScript(page, appScriptUrl, {
      baseUrl: referer || appScriptUrl
    });
    const resolvedAppScriptUrl = resolution.appScriptUrl || appScriptUrl;
    if (typeof resolution.bundleSource === 'string' && resolution.bundleSource.trim()) {
      return resolution.bundleSource;
    }

    if (page && typeof page.evaluate === 'function' && resolvedAppScriptUrl) {
      try {
        const pageBundleSource = await page.evaluate(async (url) => {
          const response = await fetch(url, { credentials: 'include' });
          if (!response.ok) {
            return '';
          }
          return response.text();
        }, resolvedAppScriptUrl);
        if (typeof pageBundleSource === 'string' && pageBundleSource.trim()) {
          return pageBundleSource;
        }
      } catch (error) {
        this.logger.debug('app_script_bundle_fetch_failed', {
          traceId: this.traceId,
          error: error.message
        });
      }
    }

    const nodeBundleSource = await fetchStaticAssetViaNode(
      resolvedAppScriptUrl,
      referer ? { referer } : {}
    );
    if (typeof nodeBundleSource === 'string' && nodeBundleSource.trim()) {
      this.logger.debug('app_script_bundle_fetch_fallback_node_hit', {
        traceId: this.traceId
      });
      return nodeBundleSource;
    }

    return '';
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

  _createPageBoundModuleLoader(page, referer = '', options = {}) {
    const manifestAssetMap = options.manifestAssetMap instanceof Map
      ? options.manifestAssetMap
      : new Map();
    const entryBundleUrl = String(options.entryBundleUrl || '').trim();
    const resolveRemappedUrl = (targetUrl) => {
      const normalizedUrl = String(targetUrl || '').trim();
      if (!normalizedUrl) {
        return '';
      }

      const absoluteUrl = new URL(normalizedUrl, referer || 'https://www.oddsportal.com/').href;
      if (
        /\/build\/assets\/app-[^/]+\.js(?:[?#].*)?$/i.test(absoluteUrl)
        && entryBundleUrl
        && absoluteUrl !== entryBundleUrl
      ) {
        return entryBundleUrl;
      }

      if (manifestAssetMap.size === 0) {
        return '';
      }

      const fileName = path.posix.basename(new URL(absoluteUrl, referer || 'https://www.oddsportal.com/').pathname);
      const fileStem = fileName.replace(/\.[^.]+$/u, '');
      const normalizedStem = fileStem.replace(/-[A-Za-z0-9_-]{6,}$/u, '');
      return manifestAssetMap.get(fileStem) || manifestAssetMap.get(normalizedStem) || '';
    };

    return async (targetUrl) => {
      if (page && typeof page.evaluate === 'function') {
        try {
          return await page.evaluate(async ({ targetUrl, referer }) => {
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
        } catch (error) {
          this.logger.debug('pure_runtime_module_fetch_failed', {
            traceId: this.traceId,
            error: error.message
          });
        }
      }

      const resolvedUrl = new URL(String(targetUrl || ''), referer || 'https://www.oddsportal.com/').href;
      const fetchHeaders = referer ? { referer } : {};
      const nodeResult = await fetchTextViaNode(
        resolvedUrl,
        fetchHeaders,
        'text/javascript,application/javascript,*/*;q=0.1'
      );
      if (nodeResult.success && typeof nodeResult.text === 'string' && nodeResult.text.trim()) {
        return nodeResult.text;
      }

      const remappedUrl = resolveRemappedUrl(resolvedUrl);
      if (remappedUrl) {
        const remappedResult = await fetchTextViaNode(
          remappedUrl,
          fetchHeaders,
          'text/javascript,application/javascript,*/*;q=0.1'
        );
        if (remappedResult.success && typeof remappedResult.text === 'string' && remappedResult.text.trim()) {
          this.logger.info('app_script_manifest_remap_hit', {
            traceId: this.traceId,
            requestedUrl: resolvedUrl,
            remappedUrl
          });
          return remappedResult.text;
        }
      }

      throw new Error('PURE_RUNTIME_PAGE_UNAVAILABLE');
    };
  },

  // eslint-disable-next-line complexity
  async _extractFromPureRuntime(page, appScriptUrl, sampleState = {}) {
    if (!page || !appScriptUrl) {
      return null;
    }

    try {
      const [runtimeState, html, resolution] = await Promise.all([
        this._readSerializableRuntimeState(page),
        this._readPageHtml(page),
        this._resolveLiveAppScript(page, appScriptUrl)
      ]);
      const bundleSource = resolution.bundleSource || await this._fetchBundleSource(page, appScriptUrl);
      if (!bundleSource) {
        return null;
      }

      const decryptor = new ReconPureDecryptor({
        logger: this.logger,
        traceId: this.traceId
      });
      const resolvedAppScriptUrl = resolution.appScriptUrl || appScriptUrl;
      const referer = String(
        runtimeState?.locationHref
        || (typeof page.url === 'function' ? page.url() : '')
        || ''
      ).trim();
      await decryptor.loadFromBundleUrl(resolvedAppScriptUrl, {
        sampleEncryptedData: sampleState?.primarySample || sampleState?.samplePool?.[0] || null,
        bundleSource,
        sourceLoader: this._createPageBoundModuleLoader(page, referer, {
          manifestAssetMap: resolution.manifestAssetMap,
          entryBundleUrl: resolvedAppScriptUrl
        }),
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

module.exports = {
  reconDecryptorSourceExtractor,
  findLatestAppScript
};
