'use strict';

const DEFAULT_NAVIGATION_HEADERS = Object.freeze({
  'sec-fetch-dest': 'document',
  'sec-fetch-mode': 'navigate',
  'sec-fetch-site': 'none',
  'sec-fetch-user': '?1',
  'accept-encoding': 'gzip, deflate, br'
});

function normalizeHeaderName(name = '') {
  return String(name || '').trim().toLowerCase();
}

function normalizeHeaders(headers = {}) {
  const normalized = {};
  for (const [key, value] of Object.entries(headers || {})) {
    const normalizedKey = normalizeHeaderName(key);
    const normalizedValue = String(value ?? '').trim();
    if (!normalizedKey || !normalizedValue) {
      continue;
    }

    normalized[normalizedKey] = normalizedValue;
  }
  return normalized;
}

function buildClientHintHeaders(userAgent = '', platform = 'Win32') {
  const normalizedUserAgent = String(userAgent || '').trim();
  const edgeVersionMatch = normalizedUserAgent.match(/Edg\/(\d+)\.0\.0\.0/);
  if (edgeVersionMatch) {
    return {
      'sec-ch-ua': `"Chromium";v="${edgeVersionMatch[1]}", "Microsoft Edge";v="${edgeVersionMatch[1]}", "Not_A Brand";v="24"`,
      'sec-ch-ua-mobile': '?0',
      'sec-ch-ua-platform': '"Windows"'
    };
  }

  const chromeVersionMatch = normalizedUserAgent.match(/Chrome\/(\d+)\.0\.0\.0/);
  if (!chromeVersionMatch) {
    return {};
  }

  const platformHeader = /mac/i.test(platform) || /mac os/i.test(normalizedUserAgent)
    ? '"macOS"'
    : /linux/i.test(platform) || /linux/i.test(normalizedUserAgent)
      ? '"Linux"'
      : '"Windows"';

  return {
    'sec-ch-ua': `"Chromium";v="${chromeVersionMatch[1]}", "Google Chrome";v="${chromeVersionMatch[1]}", "Not-A.Brand";v="99"`,
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': platformHeader
  };
}

function mergeContextExtraHTTPHeaders({
  baseHeaders = {},
  extraHeaders = {},
  userAgent = '',
  acceptLanguage = 'en-US,en;q=0.9',
  platform = 'Win32'
} = {}) {
  const normalizedUserAgent = String(userAgent || '').trim();
  const headers = {
    ...normalizeHeaders(baseHeaders),
    ...normalizeHeaders(extraHeaders)
  };

  headers['accept-language'] = String(headers['accept-language'] || acceptLanguage || 'en-US,en;q=0.9');

  for (const [headerName, headerValue] of Object.entries(DEFAULT_NAVIGATION_HEADERS)) {
    if (!headers[headerName]) {
      headers[headerName] = headerValue;
    }
  }

  if (!headers['sec-ch-ua']) {
    Object.assign(headers, buildClientHintHeaders(normalizedUserAgent, platform));
  }

  if (normalizedUserAgent) {
    headers['user-agent'] = normalizedUserAgent;
  }

  return headers;
}

module.exports = {
  buildClientHintHeaders,
  mergeContextExtraHTTPHeaders,
  normalizeHeaderName,
  normalizeHeaders
};
