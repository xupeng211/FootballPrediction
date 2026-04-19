'use strict';

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
    return {
      attempt: attempt + 1,
      breakerKey: context.breakerKey || 'default',
      currentPort: currentProxy?.port || null,
      errorType: failure?.statusCode === 503 ? '503' : 'other',
      reason: context.operationName || 'retry_after_http_failure',
      statusCode: failure?.statusCode || 503,
      url: context.inspectUrl || null
    };
  }

  shouldRotateProxy(failure = {}) {
    return Number(failure?.statusCode) === 503;
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

    rotator.reportFailure(currentProxy.port, failure?.statusCode === 503 ? '503' : 'other');
  }

  applyRotatedProxy(nextProxy) {
    this.navigator.proxy = nextProxy;
    this.navigator.browserContext.proxy = nextProxy;
    this.navigator.lastLaunchOptions = {
      ...(this.navigator.lastLaunchOptions || {}),
      proxy: nextProxy
    };
  }

  logProxyRotation(context, attempt, currentProxy, nextProxy) {
    this.logger.warn('navigator_proxy_rotated_for_503', {
      traceId: this.traceId,
      breakerKey: context.breakerKey || 'default',
      operation: context.operationName || 'unknown',
      attempt: attempt + 1,
      previousProxyPort: currentProxy?.port || null,
      nextProxyPort: nextProxy.port || null
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
    this.logProxyRotation(context, attempt, currentProxy, nextProxy);

    try {
      await this.relaunchAfterProxyRotation(context);
    } catch (error) {
      this.logProxyRotationFailure(context, error);
    }

    return nextProxy;
  }

  async scheduleRetry(failure, context, attempt, error = null) {
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
          throw this.buildRetryError(context, failure);
        }

        await this.scheduleRetry(failure, context, attempt);
        continue;
      } catch (error) {
        const failure = await this.resolveRetryableHttpFailureFromError(error, context);
        if (!failure.retryable || attempt >= retryDelays.length) {
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
