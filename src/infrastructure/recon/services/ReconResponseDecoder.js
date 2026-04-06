'use strict';

const vm = require('node:vm');

function isAjaxPayloadUrl(context, url = '') {
  const rawUrl = String(url || '');
  if (!rawUrl) {
    return false;
  }

  if (rawUrl.includes('/ajax-') || rawUrl.includes('://ajax-')) {
    return true;
  }

  return typeof context?.isPotentialMatchApi === 'function'
    ? context.isPotentialMatchApi(rawUrl)
    : false;
}

const reconResponseDecoder = {
  async parseApiResponse(body, url = '') {
    if (!body || typeof body !== 'string') {
      this.logger.debug('[ReconNetworkMonitor] 响应体为空或非字符串', { traceId: this.traceId });
      return [];
    }

    const trimmed = body.trim();
    if (!trimmed) {
      this.logger.debug('[ReconNetworkMonitor] 响应体为空', { traceId: this.traceId });
      return [];
    }

    try {
      const decoded = await this.decodeResponsePayload(trimmed, url);
      if (!decoded?.parsed || typeof decoded.parsed !== 'object') {
        return [];
      }

      const matches = this.extractMatchesFromJson(decoded.parsed, 'api_intercept');
      this.logger.debug('[ReconNetworkMonitor] 响应解析成功', {
        traceId: this.traceId,
        source: decoded.source,
        matchCount: matches.length
      });
      return matches;
    } catch (error) {
      if (this._isPageContextClosedError(error)) {
        this.logger.debug('[ReconNetworkMonitor] 页面已关闭，忽略解密错误', {
          traceId: this.traceId
        });
        return [];
      }

      if (!isAjaxPayloadUrl(this, url)) {
        this.logger.debug('[ReconNetworkMonitor] 非 ajax 响应解析失败', {
          traceId: this.traceId,
          error: error.message
        });
        return [];
      }

      this.stats.decryptedFailed++;
      this.logger.warn('[ReconNetworkMonitor] 解密失败，返回空数组', {
        traceId: this.traceId,
        url: url.substring(0, 60),
        error: error.message
      });
      return [];
    }
  },

  async decodeResponsePayload(body, url = '') {
    const trimmed = typeof body === 'string' ? body.trim() : '';
    if (!trimmed) {
      return { parsed: null, source: 'empty' };
    }

    const directJson = this.safeJsonParse(trimmed);
    if (directJson !== null) {
      return { parsed: directJson, source: 'json' };
    }

    const wrappedPayload = this.parseScriptWrappedPayload(trimmed);
    if (wrappedPayload.matched) {
      return {
        parsed: wrappedPayload.parsed,
        source: wrappedPayload.source
      };
    }

    if (this.isKnownErrorPayload(trimmed)) {
      return { parsed: null, source: 'error_payload' };
    }

    if (this.isArchivePlaceholderPayload(trimmed)) {
      return { parsed: null, source: 'archive_placeholder_payload' };
    }

    if (!isAjaxPayloadUrl(this, url)) {
      return { parsed: null, source: 'unsupported' };
    }

    if (this.isPageUnavailable()) {
      return { parsed: null, source: 'page_unavailable' };
    }

    if (typeof this.decryptor.rememberSample === 'function') {
      this.decryptor.rememberSample(trimmed);
    }

    this.logger.debug('[ReconNetworkMonitor] 检测到加密响应，尝试解密', { traceId: this.traceId });

    let decrypted;
    try {
      if (!this.decryptor.getAlgorithmVersion()) {
        await this.decryptor.extractDecryptor(this.page, trimmed);
      }
      decrypted = await this.decryptor.decrypt(trimmed);
    } catch (initialError) {
      if (
        initialError?.code === 'INVALID_ENCRYPTED_PAYLOAD'
        || this._isPageContextClosedError(initialError)
      ) {
        throw initialError;
      }

      await this.decryptor.extractDecryptor(this.page, trimmed);
      decrypted = await this.decryptor.decrypt(trimmed);
    }

    const parsed = typeof decrypted === 'string' ? this.safeJsonParse(decrypted.trim()) : decrypted;
    if (!parsed || typeof parsed !== 'object') {
      throw new Error('decrypt_result_not_json');
    }

    this.stats.decryptedSuccess++;
    return { parsed, source: 'decrypted' };
  },

  safeJsonParse(text) {
    try {
      return JSON.parse(text);
    } catch {
      return null;
    }
  },

  parseScriptWrappedPayload(text) {
    const body = String(text || '').trim();
    if (!body) {
      return { matched: false, parsed: null, source: 'script_wrapper' };
    }

    const looksLikeWrapper = this.scriptWrapperPatterns.some((pattern) => pattern.test(body));
    if (!looksLikeWrapper) {
      return { matched: false, parsed: null, source: 'script_wrapper' };
    }

    const candidates = [];
    const jsonLiteralPattern = /JSON\.parse\((['"])((?:\\.|(?!\1)[\s\S])*)\1\)/g;

    for (const match of body.matchAll(jsonLiteralPattern)) {
      const quote = match[1];
      const literal = match[2];
      if (!literal) {
        continue;
      }

      try {
        const decodedText = vm.runInNewContext(`${quote}${literal}${quote}`, Object.create(null), {
          timeout: this.scriptEvalTimeoutMs
        });
        const parsed = JSON.parse(decodedText);
        if (parsed && typeof parsed === 'object') {
          candidates.push(parsed);
        }
      } catch (_error) {
        // 当前片段无法反序列化则继续
      }
    }

    if (candidates.length === 0) {
      return { matched: true, parsed: {}, source: 'script_wrapper_empty' };
    }

    const payloadWithMatches = candidates.find((candidate) => (
      this.extractMatchesFromJson(candidate, 'script_probe').length > 0
    ));

    return {
      matched: true,
      parsed: payloadWithMatches || this.mergeScriptPayloads(candidates),
      source: 'script_wrapper'
    };
  },

  mergeScriptPayloads(candidates) {
    const merged = {};

    for (const candidate of candidates) {
      if (!candidate || typeof candidate !== 'object' || Array.isArray(candidate)) {
        continue;
      }

      Object.assign(merged, candidate);
    }

    return Object.keys(merged).length > 0 ? merged : candidates[0];
  },

  isKnownErrorPayload(text) {
    const trimmed = String(text || '').trim();
    if (!trimmed) {
      return true;
    }

    return this.knownErrorPatterns.some((pattern) => pattern.test(trimmed));
  },

  isArchivePlaceholderPayload(text) {
    const trimmed = String(text || '').trim();
    if (!trimmed) {
      return false;
    }

    const normalized = trimmed.replace(/^['"]|['"]$/g, '');
    const obviousPathPlaceholder = /^\/\d+\/(?:[^/]*\/)?X(?:\d+X){3,}\d+(?:\/|$)/i.test(normalized)
      || /^\/\d+\/\/X(?:\d+X){3,}\d+(?:\/|$)/i.test(normalized)
      || /^\/ajax-sport-country-tournament-archive_\/\d+\/(?:[^/]*\/)?X(?:\d+X){3,}\d+/i.test(normalized)
      || /\/\d+\/\/X\d+X\d+X\d+/i.test(normalized)
      || /\/\d+\/[a-z0-9_-]+\/X\d+X\d+X\d+/i.test(normalized);

    if (obviousPathPlaceholder) {
      return true;
    }

    return /^URL:\s*\/\d+\/(?:[^/]*\/)?X(?:\d+X){3,}\d+/i.test(normalized);
  },

  isPageUnavailable() {
    if (!this.page) {
      return true;
    }

    if (typeof this.page.isClosed === 'function' && this.page.isClosed()) {
      return true;
    }

    return false;
  },

  _isPageContextClosedError(error) {
    const message = String(error?.message || '').toLowerCase();
    return (
      message.includes('target page, context or browser has been closed')
      || message.includes('page has been closed')
      || message.includes('browser has been closed')
      || message.includes('execution context was destroyed')
    );
  }
};

module.exports = { reconResponseDecoder };
