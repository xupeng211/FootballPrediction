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

  async resolveRetryableHttpFailureFromError(error, context = {}) {
    const message = String(error?.message || '');
    const normalizedMessage = message.toLowerCase();
    let statusCode = Number(error?.statusCode) || null;
    let retryAfterMs = Number(error?.retryAfterMs) || 0;
    let retryAfterRaw = error?.retryAfterRaw || '';
    const isResponseCodeFailure = normalizedMessage.includes('err_http_response_code_failure')
      || normalizedMessage.includes('http_response_code_failure');
    const statusMatch = normalizedMessage.match(/\b(5\d{2})\b/);

    if (!statusCode && statusMatch) {
      statusCode = Number(statusMatch[1]);
    }

    if ((!statusCode || retryAfterMs <= 0) && context.inspectUrl) {
      const inspectedFailure = await this.inspectHttpFailure(context.inspectUrl, context.timeoutMs);
      if (inspectedFailure?.statusCode) {
        statusCode = inspectedFailure.statusCode;
      }
      if (inspectedFailure?.retryAfterMs > 0) {
        retryAfterMs = inspectedFailure.retryAfterMs;
      }
      if (inspectedFailure?.retryAfterRaw) {
        retryAfterRaw = inspectedFailure.retryAfterRaw;
      }
    }

    const retryable = statusCode === 503
      || normalizedMessage.includes('503')
      || normalizedMessage.includes('service unavailable')
      || isResponseCodeFailure;

    return {
      retryable,
      statusCode: statusCode || (isResponseCodeFailure ? 503 : null),
      retryAfterMs,
      retryAfterRaw
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
      retryable: statusCode === 503,
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

  async rotateProxyForRetry(failure, context = {}, attempt = 0) {
    const rotator = this.navigator.proxyRotator;
    if (!rotator || typeof rotator.rotate !== 'function') {
      return null;
    }

    const currentProxy = this.navigator.proxy || this.navigator.browserContext?.proxy || null;
    if (currentProxy?.port && typeof rotator.reportFailure === 'function') {
      rotator.reportFailure(currentProxy.port, failure?.statusCode === 503 ? '503' : 'other');
    }

    const nextProxy = rotator.rotate({
      attempt: attempt + 1,
      breakerKey: context.breakerKey || 'default',
      currentPort: currentProxy?.port || null,
      errorType: failure?.statusCode === 503 ? '503' : 'other',
      reason: context.operationName || 'retry_after_503',
      statusCode: failure?.statusCode || 503,
      url: context.inspectUrl || null
    });

    if (!nextProxy) {
      return null;
    }

    this.navigator.proxy = nextProxy;
    this.navigator.browserContext.proxy = nextProxy;
    this.navigator.lastLaunchOptions = {
      ...(this.navigator.lastLaunchOptions || {}),
      proxy: nextProxy
    };

    this.logger.warn('navigator_proxy_rotated_for_503', {
      traceId: this.traceId,
      breakerKey: context.breakerKey || 'default',
      operation: context.operationName || 'unknown',
      attempt: attempt + 1,
      previousProxyPort: currentProxy?.port || null,
      nextProxyPort: nextProxy.port || null
    });

    try {
      await this.navigator.close();
      await this.navigator.launch(this.navigator.lastLaunchOptions || {});

      if (context.retryNavigateUrl) {
        await this.navigator.browserContext.navigate(context.retryNavigateUrl, {
          timeout: context.timeoutMs || this.navigator.navigationTimeoutMs,
          waitUntil: 'domcontentloaded',
          contentReadySelector: context.retryReadySelector || ''
        });
        if (this.navigator.page && typeof this.navigator.page.waitForTimeout === 'function') {
          await this.navigator.page.waitForTimeout(this.navigator.postApiDiscoveryWaitMs);
        }
      }
    } catch (error) {
      this.logger.warn('navigator_proxy_rotation_failed', {
        traceId: this.traceId,
        breakerKey: context.breakerKey || 'default',
        operation: context.operationName || 'unknown',
        error: error.message
      });
    }

    return nextProxy;
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

        await this.rotateProxyForRetry(failure, context, attempt);
        const scheduledDelayMs = Math.max(retryDelays[attempt], failure.retryAfterMs || 0);
        this.logger.warn('navigator_http_503_retry_scheduled', {
          traceId: this.traceId,
          operation: context.operationName || 'unknown',
          breakerKey: context.breakerKey || 'default',
          url: context.inspectUrl || null,
          attempt: attempt + 1,
          maxRetries: retryDelays.length,
          statusCode: failure.statusCode,
          retryAfterMs: failure.retryAfterMs || 0,
          delayMs: scheduledDelayMs
        });
        await this.navigator._waitBeforeRetry(scheduledDelayMs);
        continue;
      } catch (error) {
        const failure = await this.resolveRetryableHttpFailureFromError(error, context);
        if (!failure.retryable || attempt >= retryDelays.length) {
          if (failure.statusCode) {
            error.statusCode = failure.statusCode;
          }
          if (failure.retryAfterMs) {
            error.retryAfterMs = failure.retryAfterMs;
          }
          if (failure.retryAfterRaw) {
            error.retryAfterRaw = failure.retryAfterRaw;
          }
          throw error;
        }

        await this.rotateProxyForRetry(failure, context, attempt);
        const scheduledDelayMs = Math.max(retryDelays[attempt], failure.retryAfterMs || 0);
        this.logger.warn('navigator_http_503_retry_scheduled', {
          traceId: this.traceId,
          operation: context.operationName || 'unknown',
          breakerKey: context.breakerKey || 'default',
          url: context.inspectUrl || null,
          attempt: attempt + 1,
          maxRetries: retryDelays.length,
          statusCode: failure.statusCode || 503,
          retryAfterMs: failure.retryAfterMs || 0,
          delayMs: scheduledDelayMs,
          error: error.message
        });
        await this.navigator._waitBeforeRetry(scheduledDelayMs);
      }
    }

    throw new Error(`${context.operationName || 'operation'} retry_exhausted`);
  }
}

module.exports = {
  ReconRetryCoordinator
};
