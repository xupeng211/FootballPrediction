'use strict';

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const DEFAULT_ACCEPT_LANGUAGE = 'en-US,en;q=0.9,ja-JP;q=0.8,ja;q=0.7';
const DEFAULT_CONSENT_LABELS = ['I Accept', 'Accept All', 'Accept', 'Allow All'];

class ReconStealthProvider {
  constructor(options = {}) {
    this.logger = options.logger || console;
    this.traceId = options.traceId || 'trace-unknown';
    this.hardwareConcurrency = Number(options.hardwareConcurrency ?? 8);
    this.deviceMemory = Number(options.deviceMemory ?? 8);
    this.platform = String(options.platform || 'MacIntel');
    this.userDataDirRoot = String(options.userDataDirRoot || os.tmpdir());
    this.playwrightCacheRoot = String(options.playwrightCacheRoot || '/root/.cache/ms-playwright');
  }

  sanitizeTraceId(value) {
    return String(value || 'trace')
      .replace(/[^a-zA-Z0-9_-]+/g, '-')
      .replace(/-+/g, '-')
      .replace(/^-|-$/g, '')
      .slice(0, 80) || 'trace';
  }

  async createUserDataDir() {
    const prefix = path.join(
      this.userDataDirRoot || os.tmpdir(),
      `playwright_profile_${this.sanitizeTraceId(this.traceId)}_`
    );
    return fs.promises.mkdtemp(prefix);
  }

  async cleanupUserDataDir(userDataDir) {
    if (!userDataDir) {
      return;
    }

    try {
      await fs.promises.rm(userDataDir, {
        recursive: true,
        force: true
      });
    } catch (error) {
      this.logger.warn('recon_browser_context_profile_cleanup_failed', {
        traceId: this.traceId,
        userDataDir,
        error: error.message
      });
    }
  }

  resolvePreferredExecutablePath() {
    try {
      if (!this.playwrightCacheRoot || !fs.existsSync(this.playwrightCacheRoot)) {
        return '';
      }

      const entries = fs.readdirSync(this.playwrightCacheRoot, { withFileTypes: true })
        .filter((entry) => entry.isDirectory() && /^chromium-\d+$/i.test(entry.name))
        .map((entry) => entry.name)
        .sort((left, right) => right.localeCompare(left, 'en'));

      for (const entry of entries) {
        const candidate = path.join(this.playwrightCacheRoot, entry, 'chrome-linux64', 'chrome');
        if (fs.existsSync(candidate)) {
          return candidate;
        }
      }
    } catch (error) {
      this.logger.warn('recon_browser_full_chromium_scan_failed', {
        traceId: this.traceId,
        error: error.message
      });
    }

    return '';
  }

  async applyStealthFingerprint(page, enabled = false) {
    if (!enabled || !page || typeof page.addInitScript !== 'function') {
      return false;
    }

    await page.addInitScript(({ injectedHardwareConcurrency, injectedDeviceMemory, injectedPlatform }) => {
      Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
      Object.defineProperty(navigator, 'hardwareConcurrency', { get: () => injectedHardwareConcurrency });
      Object.defineProperty(navigator, 'deviceMemory', { get: () => injectedDeviceMemory });
      Object.defineProperty(navigator, 'platform', { get: () => injectedPlatform });
      Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en', 'ja-JP', 'ja'] });
      Object.defineProperty(navigator, 'language', { get: () => 'en-US' });
      Object.defineProperty(navigator, 'plugins', {
        get: () => [
          { name: 'Chrome PDF Plugin' },
          { name: 'Chrome PDF Viewer' },
          { name: 'Native Client' }
        ]
      });
      window.chrome = window.chrome || { runtime: {} };
    }, {
      injectedHardwareConcurrency: this.hardwareConcurrency,
      injectedDeviceMemory: this.deviceMemory,
      injectedPlatform: this.platform
    });

    return true;
  }

  async dismissConsent(page, options = {}) {
    if (!page || typeof page.getByRole !== 'function') {
      return false;
    }

    const labels = Array.isArray(options.labels) && options.labels.length > 0
      ? options.labels
      : DEFAULT_CONSENT_LABELS;
    const visibilityTimeoutMs = Number(options.visibilityTimeoutMs ?? 1000);
    const clickTimeoutMs = Number(options.clickTimeoutMs ?? 1000);
    const postClickWaitMs = Number(options.postClickWaitMs ?? 1000);

    for (const label of labels) {
      try {
        const button = page.getByRole('button', { name: label }).first();
        if (await button.isVisible({ timeout: visibilityTimeoutMs })) {
          await button.click({ timeout: clickTimeoutMs });
          await page.waitForTimeout(postClickWaitMs);
          this.logger.info('consent_dismissed', { traceId: this.traceId, label });
          return true;
        }
      } catch (_error) {
        // 当前标签未命中时继续探测下一个按钮
      }
    }

    return false;
  }
}

module.exports = {
  ReconStealthProvider,
  DEFAULT_ACCEPT_LANGUAGE,
  DEFAULT_CONSENT_LABELS
};
