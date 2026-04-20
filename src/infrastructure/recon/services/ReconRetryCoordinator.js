'use strict';

const { JA3_CIPHER_SUITES, JA3_SIGALGS } = require('./ReconProtocolAdapter');

const BROWSER_TLS_DISCONNECT_ERROR_RE = /err_connection_closed|secure tls connection was established|econnreset|socket hang up|proxy connection ended before receiving connect response/i;

class ReconRetryCoordinator {
  constructor(navigator) {
    this.navigator = navigator;
  }

  get logger() {
    return this.navigator.logger;
  }

  get traceId() {
    return this.navigator.traceId;
  }

  get page() {
    return this.navigator.page;
  }

  get context() {
    return this.navigator.context;
  }

  get http503RetryDelaysMs() {
    return this.navigator.http503RetryDelaysMs;
  }

  get proxyProvider() {
    return this.navigator.proxyProvider;
  }

  get proxyLease() {
    return this.navigator.proxyLease;
  }

  get sessionManager() {
    return this.navigator.browserContext?.sessionManager || null;
  }

  parseRetryAfterMs(value) {
    const raw = String(value || '').trim();
    if (!raw) {
      return 0;
    }

    if (/^\d+$/.test(raw)) {
      return Math.max(0, Number(raw) * 1000);
    }

    const parsedDate = Date.parse(raw);
    if (Number.isNaN(parsedDate)) {
      return 0;
    }

    return Math.max(0, parsedDate - Date.now());
  }

  async waitBeforeRetry(delayMs) {
    const waitMs = Math.max(0, Number(delayMs) || 0);
    if (waitMs === 0) {
      return;
    }

    if (this.page && typeof this.page.waitForTimeout === 'function' && !this.page.isClosed?.()) {
      await this.page.waitForTimeout(waitMs);
      return;
    }

    await new Promise((resolve) => {
      setTimeout(resolve, waitMs);
    });
  }

  async inspectHttpFailure(url, timeoutMs) {
    if (!this.context?.request || typeof this.context.request.get !== 'function') {
      return null;
    }

    try {
      const response = await this.context.request.get(url, {
        failOnStatusCode: false,
        timeout: Math.min(Number(timeoutMs) || this.navigator.navigationTimeoutMs, 15000)
      });
      const headers = typeof response.allHeaders === 'function'
        ? await response.allHeaders()
        : {};
      const retryAfterRaw = headers?.['retry-after'] || headers?.['Retry-After'] || '';
      return {
        statusCode: typeof response.status === 'function' ? response.status() : null,
        retryAfterRaw,
        retryAfterMs: this.parseRetryAfterMs(retryAfterRaw)
      };
    } catch (error) {
      this.logger.debug('navigator_http_failure_inspect_failed', {
        traceId: this.traceId,
        url,
        error: error.message
      });
      return null;
    }
  }

  extractFailureFromError(error, context = {}) {
    const message = String(error?.message || '');
    const normalizedMessage = message.toLowerCase();
    const statusMatch = normalizedMessage.match(/\b(5\d{2})\b/);
    const isResponseCodeFailure = normalizedMessage.includes('err_http_response_code_failure')
      || normalizedMessage.includes('http_response_code_failure');

    return {
      normalizedMessage,
      retryable: false,
      isResponseCodeFailure,
      statusCode: Number(error?.statusCode) || (statusMatch ? Number(statusMatch[1]) : null),
      retryAfterMs: Number(error?.retryAfterMs) || 0,
      retryAfterRaw: error?.retryAfterRaw || '',
      inspectUrl: context.inspectUrl
    };
  }

  mergeInspectedFailure(failure, inspectedFailure) {
    if (inspectedFailure?.statusCode) {
      failure.statusCode = inspectedFailure.statusCode;
    }
    if (inspectedFailure?.retryAfterMs > 0) {
      failure.retryAfterMs = inspectedFailure.retryAfterMs;
    }
    if (inspectedFailure?.retryAfterRaw) {
      failure.retryAfterRaw = inspectedFailure.retryAfterRaw;
    }
  }

  isRetryableFailure(failure) {
    if (failure.statusCode === 429 || failure.statusCode === 502 || failure.statusCode === 503 || failure.statusCode === 504) {
      return true;
    }

    return failure.normalizedMessage.includes('503')
      || failure.normalizedMessage.includes('429')
      || failure.normalizedMessage.includes('service unavailable')
      || (failure.isResponseCodeFailure && failure.statusCode >= 500);
  }

  async resolveRetryableHttpFailureFromError(error, context = {}) {
    const failure = this.extractFailureFromError(error, context);
    if ((!failure.statusCode || failure.retryAfterMs <= 0) && failure.inspectUrl) {
      const inspectedFailure = await this.inspectHttpFailure(context.inspectUrl, context.timeoutMs);
      this.mergeInspectedFailure(failure, inspectedFailure);
    }

    return {
      retryable: this.isRetryableFailure(failure),
      statusCode: failure.statusCode || (failure.isResponseCodeFailure ? 503 : null),
      retryAfterMs: failure.retryAfterMs,
      retryAfterRaw: failure.retryAfterRaw
    };
  }

  resolveRetryableHttpFailureFromResult(result) {
    const failure = result?.httpFailure;
    if (!failure) {
      return { retryable: false, statusCode: null, retryAfterMs: 0, retryAfterRaw: '' };
    }

    const retryAfterRaw = failure.retryAfterRaw || '';
    const retryAfterMs = Number(failure.retryAfterMs) || this.parseRetryAfterMs(retryAfterRaw);
    const statusCode = Number(failure.statusCode) || null;
    return {
      retryable: statusCode === 429 || statusCode === 502 || statusCode === 503 || statusCode === 504,
      statusCode,
      retryAfterMs,
      retryAfterRaw
    };
  }

  buildRetryError(context = {}, failure = {}) {
    const error = new Error(
      `${context.operationName || 'operation'} failed with HTTP_${failure.statusCode || '503'} after retries`
    );
    error.code = `HTTP_${failure.statusCode || '503'}`;
    error.statusCode = failure.statusCode || 503;
    error.retryAfterMs = failure.retryAfterMs || 0;
    error.retryAfterRaw = failure.retryAfterRaw || '';
    error.circuitBreakerKey = context.breakerKey || 'default';
    return error;
  }

  buildRotationPayload(failure, context = {}, attempt = 0, currentProxy = null) {
    const statusCode = Number(failure?.statusCode) || 503;
    return {
      attempt: attempt + 1,
      breakerKey: context.breakerKey || 'default',
      currentPort: currentProxy?.port || null,
      errorType: statusCode === 429 ? '429' : (statusCode === 503 ? '503' : 'other'),
      reason: context.operationName || 'retry_after_http_failure',
      statusCode,
      url: context.inspectUrl || null
    };
  }

  shouldRotateProxy(failure = {}) {
    const statusCode = Number(failure?.statusCode) || 0;
    return statusCode === 429 || statusCode === 503;
  }

  async reportCurrentProxyFailure(failure = {}, context = {}) {
    if (!this.proxyProvider || typeof this.proxyProvider.reportFailure !== 'function') {
      return false;
    }

    const lease = this.proxyLease;
    const currentProxy = this.getCurrentProxy();
    const target = lease?.id ? lease.id : null;
    const port = Number(lease?.proxy?.port || currentProxy?.port || 0) || null;

    try {
      await this.proxyProvider.reportFailure(target, {
        ...(port ? { port } : {}),
        statusCode: failure?.statusCode || null,
        reason: context.operationName || `HTTP_${failure?.statusCode || 'failure'}`
      });
      return true;
    } catch (error) {
      this.logger.debug?.('navigator_proxy_failure_report_failed', {
        traceId: this.traceId,
        breakerKey: context.breakerKey || 'default',
        port,
        error: error.message
      });
      return false;
    }
  }

  async relaunchAfterProxyRotation(context = {}) {
    await this.navigator.close();
    await this.navigator.launch(this.navigator.lastLaunchOptions || {});

    if (!context.retryNavigateUrl) {
      return;
    }

    await this.navigator.browserContext.navigate(context.retryNavigateUrl, {
      timeout: context.timeoutMs || this.navigator.navigationTimeoutMs,
      waitUntil: 'domcontentloaded',
      contentReadySelector: context.retryReadySelector || ''
    });
    if (this.navigator.page && typeof this.navigator.page.waitForTimeout === 'function') {
      await this.navigator.page.waitForTimeout(this.navigator.postApiDiscoveryWaitMs);
    }
  }

  getProxyRotator() {
    const rotator = this.navigator.proxyRotator;
    return rotator && typeof rotator.rotate === 'function' ? rotator : null;
  }

  getCurrentProxy() {
    return this.navigator.proxy || this.navigator.browserContext?.proxy || null;
  }

  reportProxyFailure(rotator, currentProxy, failure) {
    if (!currentProxy?.port || typeof rotator?.reportFailure !== 'function') {
      return;
    }

    const statusCode = Number(failure?.statusCode) || 0;
    rotator.reportFailure(currentProxy.port, statusCode === 429 ? '429' : (statusCode === 503 ? '503' : 'other'));
  }

  applyRotatedProxy(nextProxy) {
    this.navigator.proxy = nextProxy;
    this.navigator.browserContext.proxy = nextProxy;
    this.navigator.lastLaunchOptions = {
      ...(this.navigator.lastLaunchOptions || {}),
      proxy: nextProxy
    };
  }

  logProxyRotation(context, attempt, currentProxy, nextProxy, failure = {}) {
    const statusCode = Number(failure?.statusCode) || 503;
    const eventName = statusCode === 429
      ? 'navigator_proxy_rotated_for_429'
      : 'navigator_proxy_rotated_for_503';
    this.logger.warn(eventName, {
      traceId: this.traceId,
      breakerKey: context.breakerKey || 'default',
      operation: context.operationName || 'unknown',
      attempt: attempt + 1,
      previousProxyPort: currentProxy?.port || null,
      nextProxyPort: nextProxy.port || null,
      statusCode
    });
  }

  logProxyRotationFailure(context, error) {
    this.logger.warn('navigator_proxy_rotation_failed', {
      traceId: this.traceId,
      breakerKey: context.breakerKey || 'default',
      operation: context.operationName || 'unknown',
      error: error.message
    });
  }

  _normalizeCookieCount(cookies) {
    return Array.isArray(cookies)
      ? cookies.filter((cookie) => cookie && typeof cookie === 'object' && String(cookie.name || '').trim()).length
      : 0;
  }

  async log503CookieState(failure = {}, context = {}) {
    if (Number(failure?.statusCode) !== 503) {
      return;
    }

    const runtimeSnapshotCookies = this._normalizeCookieCount(this.sessionManager?.runtimeSnapshot?.cookies);
    let contextCookies = null;
    let contextCookieReadError = '';

    if (this.context && typeof this.context.cookies === 'function') {
      try {
        contextCookies = this._normalizeCookieCount(await this.context.cookies());
      } catch (error) {
        contextCookieReadError = error.message;
      }
    }

    this.logger.warn('navigator_http_503_cookie_state', {
      traceId: this.traceId,
      breakerKey: context.breakerKey || 'default',
      operation: context.operationName || 'unknown',
      url: context.inspectUrl || null,
      proxyPort: Number(this.proxyLease?.proxy?.port || this.getCurrentProxy()?.port || 0) || null,
      contextCookies,
      hasContextCookies: Number(contextCookies) > 0,
      runtimeSnapshotCookies,
      hasRuntimeSnapshotCookies: runtimeSnapshotCookies > 0,
      ...(contextCookieReadError ? { contextCookieReadError } : {})
    });
  }

  resolveSessionSourceFormat() {
    const sourceFormat = String(this.sessionManager?.load?.()?.sourceFormat || '').trim();
    return sourceFormat || 'unknown';
  }

  resolveCurrentJa3Identity(proxyPort = null) {
    const normalizedProxyPort = Number(proxyPort || this.proxyLease?.proxy?.port || this.getCurrentProxy()?.port || 0) || null;
    if (!normalizedProxyPort || !this.sessionManager || typeof this.sessionManager.resolveProtocolIdentity !== 'function') {
      return null;
    }

    return this.sessionManager.resolveProtocolIdentity({
      proxyPort: normalizedProxyPort,
      ciphersCount: JA3_CIPHER_SUITES.length,
      sigalgsCount: JA3_SIGALGS.length
    });
  }

  _extractBrowserNavigationFailureMeta(failure = {}, error = null) {
    const statusCode = Number(failure?.statusCode || error?.statusCode) || null;
    const errorMessage = String(
      error?.message
      || failure?.reason
      || failure?.normalizedMessage
      || ''
    ).trim();
    const normalizedError = errorMessage.toLowerCase();
    const tlsDisconnect = BROWSER_TLS_DISCONNECT_ERROR_RE.test(normalizedError);

    return {
      statusCode,
      errorMessage,
      tlsDisconnect,
      shouldAudit: statusCode === 429
        || statusCode === 503
        || normalizedError.includes('503')
        || tlsDisconnect
    };
  }

  _markBrowserFailureAudited(error = null) {
    if (!error || typeof error !== 'object') {
      return;
    }

    try {
      error._browserFailureProfileAudited = true;
    } catch (_error) {
      // Error 对象不可扩展时静默跳过，避免影响主链路
    }
  }

  // eslint-disable-next-line complexity
  auditBrowserNavigationFailure(failure = {}, context = {}, error = null) {
    if (String(context.operationName || '').trim() !== 'navigate') {
      return false;
    }

    if (error && error._browserFailureProfileAudited === true) {
      return false;
    }

    const {
      statusCode,
      errorMessage,
      tlsDisconnect,
      shouldAudit
    } = this._extractBrowserNavigationFailureMeta(failure, error);

    if (!shouldAudit) {
      return false;
    }

    const proxyPort = Number(this.proxyLease?.proxy?.port || this.getCurrentProxy()?.port || 0) || null;
    const ja3Identity = this.resolveCurrentJa3Identity(proxyPort);

    this.logger.warn('navigator_http_503_profile_audit', {
      traceId: this.traceId,
      breakerKey: context.breakerKey || 'default',
      operation: context.operationName || 'unknown',
      stage: context.stage || 'page_goto',
      url: context.inspectUrl || null,
      proxyPort,
      ja3ProfileId: ja3Identity?.ja3ProfileId || null,
      lineageKey: ja3Identity?.lineageKey || null,
      ja3Source: ja3Identity?.source || null,
      statusCode,
      tlsDisconnect,
      sourceFormat: this.resolveSessionSourceFormat(),
      ...(errorMessage ? { error: errorMessage } : {})
    });

    this._markBrowserFailureAudited(error);

    return true;
  }

  async rotateProxyForRetry(failure, context = {}, attempt = 0) {
    if (!this.shouldRotateProxy(failure)) {
      return null;
    }

    const rotator = this.getProxyRotator();
    if (!rotator) {
      return null;
    }

    const currentProxy = this.getCurrentProxy();
    this.reportProxyFailure(rotator, currentProxy, failure);
    const nextProxy = rotator.rotate(this.buildRotationPayload(failure, context, attempt, currentProxy));
    if (!nextProxy) {
      return null;
    }

    this.applyRotatedProxy(nextProxy);
    this.logProxyRotation(context, attempt, currentProxy, nextProxy, failure);

    try {
      await this.relaunchAfterProxyRotation(context);
    } catch (error) {
      this.logProxyRotationFailure(context, error);
    }

    return nextProxy;
  }

  async scheduleRetry(failure, context, attempt, error = null) {
    this.auditBrowserNavigationFailure(failure, context, error);
    await this.log503CookieState(failure, context);
    await this.reportCurrentProxyFailure(failure, context);
    await this.rotateProxyForRetry(failure, context, attempt);
    const scheduledDelayMs = Math.max(this.http503RetryDelaysMs[attempt], failure.retryAfterMs || 0);
    this.logger.warn('navigator_http_retry_scheduled', {
      traceId: this.traceId,
      operation: context.operationName || 'unknown',
      breakerKey: context.breakerKey || 'default',
      url: context.inspectUrl || null,
      attempt: attempt + 1,
      maxRetries: this.http503RetryDelaysMs.length,
      statusCode: failure.statusCode || 503,
      retryAfterMs: failure.retryAfterMs || 0,
      delayMs: scheduledDelayMs,
      ...(error ? { error: error.message } : {})
    });
    await this.navigator._waitBeforeRetry(scheduledDelayMs);
  }

  decorateRetryError(error, failure) {
    if (failure.statusCode) {
      error.statusCode = failure.statusCode;
    }
    if (failure.retryAfterMs) {
      error.retryAfterMs = failure.retryAfterMs;
    }
    if (failure.retryAfterRaw) {
      error.retryAfterRaw = failure.retryAfterRaw;
    }
  }

  async executeWith503Retry(operation, context = {}) {
    const retryDelays = this.http503RetryDelaysMs;

    for (let attempt = 0; attempt <= retryDelays.length; attempt++) {
      try {
        const result = await operation();
        const failure = this.resolveRetryableHttpFailureFromResult(result);
        if (!failure.retryable) {
          return result;
        }

        if (attempt >= retryDelays.length) {
          const retryError = this.buildRetryError(context, failure);
          this.auditBrowserNavigationFailure(failure, context, retryError);
          throw retryError;
        }

        await this.scheduleRetry(failure, context, attempt);
        continue;
      } catch (error) {
        const failure = await this.resolveRetryableHttpFailureFromError(error, context);
        if (!failure.retryable || attempt >= retryDelays.length) {
          this.auditBrowserNavigationFailure(failure, context, error);
          this.decorateRetryError(error, failure);
          throw error;
        }

        await this.scheduleRetry(failure, context, attempt, error);
      }
    }

    throw new Error(`${context.operationName || 'operation'} retry_exhausted`);
  }
}

module.exports = {
  ReconRetryCoordinator
};
