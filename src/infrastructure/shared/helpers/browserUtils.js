'use strict';

function pageClosed(page) {
  return !page || (typeof page.isClosed === 'function' && page.isClosed());
}

async function waitForDelay(page, delayMs = 0) {
  const waitMs = Math.max(0, Number(delayMs) || 0);
  if (waitMs === 0) {
    return;
  }

  if (page && typeof page.waitForTimeout === 'function' && !pageClosed(page)) {
    await page.waitForTimeout(waitMs);
    return;
  }

  await new Promise((resolve) => {
    setTimeout(resolve, waitMs);
  });
}

function buildHttpStatusError(statusCode, message, meta = {}) {
  const error = new Error(message);
  error.statusCode = statusCode;
  Object.assign(error, meta);
  return error;
}

function resolveBrowserProcessHandle(browser, context) {
  const candidates = [
    browser,
    context && typeof context.browser === 'function' ? context.browser() : null
  ];

  for (const candidate of candidates) {
    if (!candidate || typeof candidate.process !== 'function') {
      continue;
    }

    const processHandle = candidate.process();
    if (processHandle) {
      return processHandle;
    }
  }

  return null;
}

async function closeTargetWithTimeout(label, target, options = {}) {
  if (!target || typeof target.close !== 'function' || options.skip === true) {
    return false;
  }

  const timeoutMs = Math.max(1, Number(options.timeoutMs) || 5000);
  let timedOut = false;
  let timer = null;

  try {
    await Promise.race([
      Promise.resolve().then(() => target.close()),
      new Promise((_, reject) => {
        timer = setTimeout(() => {
          timedOut = true;
          reject(new Error(`${label}_close_timeout`));
        }, timeoutMs);
      })
    ]);
    return false;
  } catch (error) {
    options.logger?.warn?.(options.eventName || 'browser_close_failed', {
      ...(options.meta || {}),
      target: label,
      timeoutMs,
      timedOut,
      error: error.message
    });
    return true;
  } finally {
    if (timer) {
      clearTimeout(timer);
    }
  }
}

module.exports = {
  buildHttpStatusError,
  closeTargetWithTimeout,
  pageClosed,
  resolveBrowserProcessHandle,
  waitForDelay
};
