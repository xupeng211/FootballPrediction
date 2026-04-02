'use strict';

const fs = require('node:fs');
const path = require('node:path');

const { ReconBrowserContext } = require('../../src/infrastructure/recon/services/ReconBrowserContext');
const { ReconStateProber } = require('../../src/infrastructure/recon/services/ReconStateProber');
const { ReconNetworkMonitor } = require('../../src/infrastructure/recon/services/ReconNetworkMonitor');
const { ReconDecryptor } = require('../../src/infrastructure/recon/ReconDecryptor');

const TARGET_URL = process.env.TARGET_URL || 'https://www.oddsportal.com/football/england/premier-league-2025-2026/results/';
const OUTPUT_DIR = process.env.OUTPUT_DIR || '/app/tmp/recon_decryptor_debug';
const WAIT_MS = Number(process.env.WAIT_MS || 15000);
const INSPECT_MODULE_KEYS = process.env.INSPECT_MODULE_KEYS !== '0';

function createLogger() {
  const levels = ['info', 'warn', 'error', 'debug'];
  const logger = {};
  for (const level of levels) {
    logger[level] = (message, payload = {}) => {
      const record = {
        ts: new Date().toISOString(),
        level,
        message,
        ...payload
      };
      process.stdout.write(`${JSON.stringify(record)}\n`);
    };
  }
  return logger;
}

function ensureDir(dirPath) {
  fs.mkdirSync(dirPath, { recursive: true });
}

function normalizeBody(body) {
  return typeof body === 'string' ? body.trim() : '';
}

async function main() {
  ensureDir(OUTPUT_DIR);

  const logger = createLogger();
  const decryptor = new ReconDecryptor({ logger, traceId: 'debug-decrypt-failure' });
  const stateProber = new ReconStateProber({ logger, traceId: 'debug-decrypt-failure' });
  const networkMonitor = new ReconNetworkMonitor({ logger, traceId: 'debug-decrypt-failure' });
  const browserContext = new ReconBrowserContext({
    logger,
    traceId: 'debug-decrypt-failure'
  });

  const evidence = {
    targetUrl: TARGET_URL,
    startedAt: new Date().toISOString(),
    appScriptUrl: '',
    appModuleKeys: [],
    invalidPayloads: [],
    validPayloads: []
  };

  let page;
  try {
    page = await browserContext.launch();
    stateProber.setPage(page);
    networkMonitor.setPage(page);

    const archiveEndpoints = new Set();

    page.on('response', async (response) => {
      try {
        const url = response.url();
        if (!url.includes('/ajax-sport-country-tournament-arc')) {
          return;
        }

        archiveEndpoints.add(url);

        const body = normalizeBody(await response.text());
        const cleaned = decryptor._cleanPayload(body);
        const probe = decryptor._probeEncryptedPayload(cleaned);
        const record = {
          url,
          status: response.status(),
          bodyLength: body.length,
          cleanedLength: typeof cleaned === 'string' ? cleaned.length : 0,
          valid: probe.valid,
          preview: probe.preview || '',
          timestamp: new Date().toISOString()
        };

        if (probe.valid) {
          evidence.validPayloads.push(record);
          if (evidence.validPayloads.length === 1) {
            fs.writeFileSync(path.join(OUTPUT_DIR, 'payload.encrypted.bin'), cleaned);
            fs.writeFileSync(path.join(OUTPUT_DIR, 'payload.valid.raw.txt'), body);
          }
        } else {
          evidence.invalidPayloads.push(record);
          if (evidence.invalidPayloads.length === 1) {
            fs.writeFileSync(path.join(OUTPUT_DIR, 'payload.invalid.raw.txt'), body);
          }
        }
      } catch (error) {
        logger.warn('response_capture_failed', { error: error.message });
      }
    });

    await browserContext.navigate(TARGET_URL, {
      waitUntil: 'domcontentloaded'
    });

    evidence.appScriptUrl = await page.evaluate(() => {
      return Array.from(document.querySelectorAll('script[src*="/build/assets/app-"]'))
        .map((node) => node.src)
        .find(Boolean) || '';
    });

    if (!evidence.appScriptUrl) {
      throw new Error('app_script_not_found');
    }

    const bundleResponse = await fetch(evidence.appScriptUrl);
    if (!bundleResponse.ok) {
      throw new Error(`bundle_fetch_failed:${bundleResponse.status}`);
    }

    const bundleText = await bundleResponse.text();
    fs.writeFileSync(path.join(OUTPUT_DIR, 'oddsportal_bundle.js'), bundleText);

    if (INSPECT_MODULE_KEYS) {
      try {
        evidence.appModuleKeys = await page.evaluate(async (url) => {
          const timeout = new Promise((_, reject) => {
            setTimeout(() => reject(new Error('module_import_timeout')), 5000);
          });
          const mod = await Promise.race([import(url), timeout]);
          return Object.keys(mod).sort();
        }, evidence.appScriptUrl);
      } catch (error) {
        evidence.appModuleKeysError = error.message;
      }
    }

    await page.waitForTimeout(WAIT_MS);

    if (evidence.validPayloads.length === 0 && archiveEndpoints.size > 0) {
      const rawEndpoints = Array.from(archiveEndpoints);
      const leagueUrl = stateProber.deriveLeaguePageUrl(TARGET_URL);
      if (leagueUrl) {
        await browserContext.navigate(leagueUrl, { waitUntil: 'domcontentloaded' });
        await page.waitForTimeout(5000);
      }

      const repairedArchiveUrl = await stateProber.resolveCurrentSeasonArchiveEndpoint(rawEndpoints, {
        scoreArchiveUrl: () => 0
      });

      evidence.repairedArchiveUrl = repairedArchiveUrl || '';
      evidence.tournamentToken = await stateProber.extractTournamentToken();

      if (repairedArchiveUrl) {
        const archiveFetchUrl = `${repairedArchiveUrl.split('?')[0]}/?_=1234567890`;
        const fetched = await networkMonitor.fetchText(archiveFetchUrl, 30000);

        evidence.activeFetch = {
          url: archiveFetchUrl,
          success: fetched?.success === true,
          status: fetched?.status || null,
          error: fetched?.error || null
        };

        if (typeof fetched?.text === 'string' && fetched.text.trim()) {
          const body = normalizeBody(fetched.text);
          const cleaned = decryptor._cleanPayload(body);
          const probe = decryptor._probeEncryptedPayload(cleaned);

          fs.writeFileSync(path.join(OUTPUT_DIR, 'payload.active_fetch.raw.txt'), body);

          if (probe.valid) {
            fs.writeFileSync(path.join(OUTPUT_DIR, 'payload.encrypted.bin'), cleaned);
            evidence.validPayloads.push({
              url: archiveFetchUrl,
              status: fetched?.status || null,
              bodyLength: body.length,
              cleanedLength: cleaned.length,
              valid: true,
              preview: probe.preview || '',
              timestamp: new Date().toISOString(),
              source: 'active_fetch'
            });

            await decryptor.extractDecryptor(page, cleaned);
            const decrypted = await decryptor.decrypt(cleaned);
            const parsed = typeof decrypted === 'string' ? JSON.parse(decrypted) : decrypted;
            const rows = Array.isArray(parsed?.d?.rows)
              ? parsed.d.rows
              : Array.isArray(parsed?.rows)
                ? parsed.rows
                : [];
            fs.writeFileSync(
              path.join(OUTPUT_DIR, 'payload.decrypted.json'),
              JSON.stringify(parsed, null, 2)
            );
            fs.writeFileSync(
              path.join(OUTPUT_DIR, 'payload.decrypted.sample.json'),
              JSON.stringify(rows.slice(0, 5), null, 2)
            );
            evidence.decryptedSampleCount = rows.length;
          } else {
            evidence.activeFetchProbe = probe;
          }
        }
      }
    }

    evidence.finishedAt = new Date().toISOString();
    evidence.invalidPayloadCount = evidence.invalidPayloads.length;
    evidence.validPayloadCount = evidence.validPayloads.length;

    fs.writeFileSync(
      path.join(OUTPUT_DIR, 'debug_summary.json'),
      JSON.stringify(evidence, null, 2)
    );

    process.stdout.write(`${JSON.stringify({
      outputDir: OUTPUT_DIR,
      appScriptUrl: evidence.appScriptUrl,
      appModuleKeys: evidence.appModuleKeys,
      invalidPayloadCount: evidence.invalidPayloadCount,
      validPayloadCount: evidence.validPayloadCount
    }, null, 2)}\n`);
  } finally {
    await browserContext.close();
  }
}

main().catch((error) => {
  process.stderr.write(`${error.stack || error.message}\n`);
  process.exitCode = 1;
});
