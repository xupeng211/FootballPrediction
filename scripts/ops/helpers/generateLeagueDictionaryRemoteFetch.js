'use strict';

const https = require('https');
const { HttpsProxyAgent } = require('https-proxy-agent');
const { getProxyProvider } = require('../../../src/infrastructure/network/ProxyProvider');

const BASE_URL = 'https://www.oddsportal.com';

function normalizePathSegment(value) {
  return String(value || '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '');
}

function buildStandingsUrl(league, season) {
  const country = normalizePathSegment(league?.country);
  const slug = String(league?.resultsSlug || league?.slug || '').trim().toLowerCase();
  const normalizedSeason = String(season || '').trim();
  const seasonType = String(league?.seasonType || '').trim().toLowerCase();
  const resultsUrlStrategy = String(league?.resultsUrlStrategy || '').trim().toLowerCase();

  if (resultsUrlStrategy === 'seasonless') {
    return `${BASE_URL}/football/${country}/${slug}/standings/`;
  }
  if (seasonType === 'single_year') {
    const singleYear = normalizedSeason.match(/(\d{4})$/)?.[1] || normalizedSeason;
    return `${BASE_URL}/football/${country}/${slug}-${singleYear}/standings/`;
  }

  return `${BASE_URL}/football/${country}/${slug}-${normalizedSeason.replace('/', '-')}/standings/`;
}

function fetchText(url, redirectCount = 0) {
  return new Promise((resolve, reject) => {
    let lease = null;
    const proxyProvider = getProxyProvider({ poolName: 'oddsportal_pool' });
    
    proxyProvider.acquire({
      consumer: 'generate-league-dictionary',
      sticky: false
    }).then((acquiredLease) => {
      lease = acquiredLease;
      const agent = new HttpsProxyAgent(lease.proxy.server);

      const request = https.get(url, {
        agent,
        headers: {
          'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36',
          'accept-language': 'en-US,en;q=0.9',
          accept: 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
        }
      }, (response) => {
        const location = response.headers.location;
        if (response.statusCode >= 300 && response.statusCode < 400 && location) {
          proxyProvider.release(lease.id).catch(() => {});
          if (redirectCount >= 5) {
            reject(new Error(`重定向次数过多: ${url}`));
            response.resume();
            return;
          }

          response.resume();
          resolve(fetchText(new URL(location, url).href, redirectCount + 1));
          return;
        }

        if (response.statusCode !== 200) {
          proxyProvider.release(lease.id).catch(() => {});
          reject(new Error(`HTTP ${response.statusCode}: ${url}`));
          response.resume();
          return;
        }

        const chunks = [];
        response.setEncoding('utf8');
        response.on('data', (chunk) => chunks.push(chunk));
        response.on('end', () => {
          proxyProvider.release(lease.id).catch(() => {});
          resolve(chunks.join(''));
        });
      });

      request.on('error', (e) => {
        if (lease) {
          proxyProvider.release(lease.id).catch(() => {});
        }
        reject(e);
      });
      request.setTimeout(30000, () => {
        if (lease) {
          proxyProvider.release(lease.id).catch(() => {});
        }
        request.destroy(new Error(`请求超时: ${url}`));
      });
    }).catch((e) => {
      if (lease) {
        proxyProvider.release(lease.id).catch(() => {});
      }
      reject(e);
    });
  });
}

module.exports = {
  BASE_URL,
  buildStandingsUrl,
  fetchText
};
