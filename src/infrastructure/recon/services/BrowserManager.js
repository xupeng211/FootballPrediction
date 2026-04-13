'use strict';

const {
  closeTargetWithTimeout,
  resolveBrowserProcessHandle
} = require('../../shared/helpers/browserUtils');

const browserManager = {
  buildLaunchOptions(options = {}) {
    const launchOptions = {
      headless: this.headless,
      args: this.launchArgs,
      timeout: options.timeout || this.launchTimeoutMs
    };

    if (this.proxy?.host && this.proxy?.port) {
      launchOptions.proxy = { server: `http://${this.proxy.host}:${this.proxy.port}` };
    }

    const explicitExecutablePath = String(options.executablePath || this.explicitExecutablePath || '').trim();
    if (explicitExecutablePath) {
      launchOptions.executablePath = explicitExecutablePath;
    } else if (this.preferFullChromium) {
      const executablePath = this.resolvePreferredExecutablePath();
      if (executablePath) {
        launchOptions.executablePath = executablePath;
        this.logger.info('recon_browser_full_chromium_selected', {
          traceId: this.traceId,
          executablePath
        });
      } else if (typeof this.logger.debug === 'function') {
        this.logger.debug('recon_browser_full_chromium_unavailable', {
          traceId: this.traceId,
          cacheRoot: this.playwrightCacheRoot
        });
      }
    }

    return launchOptions;
  },

  async launch(options = {}) {
    if (
      this.enableFingerprintRotation === true
      && this.contextGeneration > 0
      && this.isClosed === true
      && options.skipAutoRotate !== true
    ) {
      this._applyStealthIdentity(this._buildStealthIdentity());
    }

    const launchOptions = options.launchOptions || this.buildLaunchOptions(options);
    const externalSession = this.sessionManager.load();
    let browser = null;
    let context = null;
    let page = null;
    let userDataDir = null;

    try {
      const contextOptions = this._buildContextOptions(externalSession);

      if (this.persistentProfileEnabled && typeof this.chromium.launchPersistentContext === 'function') {
        userDataDir = await this.stealthProvider.createUserDataDir();
        context = await this.chromium.launchPersistentContext(userDataDir, {
          ...launchOptions,
          ...contextOptions
        });
        browser = typeof context.browser === 'function' ? context.browser() : null;
        this.userDataDir = userDataDir;
        this.logger.info('recon_browser_context_profile_created', {
          traceId: this.traceId,
          userDataDir
        });
      } else {
        browser = await this.chromium.launch(launchOptions);
        context = await browser.newContext(contextOptions);
      }

      page = await this._initializeFreshPage(context, externalSession);
      this.browser = browser;
      this.context = context;
      this.page = page;
      this.isClosed = false;
      this._sessionPrimed = false;
      return this.page;
    } catch (error) {
      await this._cleanupPartialLaunch(browser, context, page);
      if (userDataDir) {
        this.userDataDir = null;
        await this.stealthProvider.cleanupUserDataDir(userDataDir);
      }
      this.browser = null;
      this.context = null;
      this.page = null;
      this.isClosed = true;
      throw error;
    }
  },

  async resetContext(options = {}) {
    this._applyStealthIdentity(this._buildStealthIdentity());

    if (
      !this.browser
      || this.persistentProfileEnabled === true
      || (typeof this.browser.isConnected === 'function' && !this.browser.isConnected())
    ) {
      await this.close();
      return this.launch({
        ...options,
        reason: options.reason || 'batch_reset',
        skipAutoRotate: true
      });
    }

    if (typeof this.browser.newContext !== 'function') {
      this.logger.warn('recon_browser_context_batch_reset_skipped', {
        traceId: this.traceId,
        reason: options.reason || 'batch_reset',
        hasBrowser: Boolean(this.browser),
        hasContext: Boolean(this.context)
      });
      return this.page;
    }

    const contextCloseTimedOut = await this._closeActiveContext();
    if (contextCloseTimedOut) {
      await this.close();
      return this.launch({
        ...options,
        reason: options.reason || 'batch_reset',
        skipAutoRotate: true
      });
    }

    const externalSession = this.sessionManager.load();
    const context = await this.browser.newContext(this._buildContextOptions(externalSession));
    const page = await this._initializeFreshPage(context, externalSession);

    this.context = context;
    this.page = page;
    this.isClosed = false;
    return page;
  },

  async close() {
    this.isClosed = true;

    const browser = this.browser;
    const context = this.context;
    const userDataDir = this.userDataDir;
    this.browser = null;
    this.context = null;
    this.page = null;
    this.userDataDir = null;
    this._sessionPrimed = false;

    try {
      let forceKillRequired = false;
      forceKillRequired = await this._closeTargetWithTimeout('context', context) || forceKillRequired;
      forceKillRequired = await this._closeTargetWithTimeout('browser', browser, {
        skipWhenSameAsContext: browser === context
      }) || forceKillRequired;

      if (forceKillRequired) {
        await this._forceKillBrowserProcess(browser, context);
      }
    } finally {
      await this.stealthProvider.cleanupUserDataDir(userDataDir);
    }
  },

  async _closeTargetWithTimeout(label, target, options = {}) {
    return closeTargetWithTimeout(label, target, {
      timeoutMs: this.closeTimeoutMs,
      logger: this.logger,
      eventName: 'recon_browser_context_close_failed',
      meta: { traceId: this.traceId },
      skip: options.skipWhenSameAsContext === true
    });
  },

  async _forceKillBrowserProcess(browser, context) {
    const processHandle = resolveBrowserProcessHandle(browser, context);
    if (!processHandle || typeof processHandle.kill !== 'function') {
      return false;
    }

    try {
      processHandle.kill('SIGKILL');
      this.logger.warn('recon_browser_context_process_killed', {
        traceId: this.traceId,
        signal: 'SIGKILL'
      });
      return true;
    } catch (error) {
      this.logger.warn('recon_browser_context_process_kill_failed', {
        traceId: this.traceId,
        error: error.message
      });
      return false;
    }
  },

  async _cleanupPartialLaunch(browser, context, page) {
    for (const target of [page, context, browser]) {
      if (!target || typeof target.close !== 'function') {
        continue;
      }

      try {
        await target.close();
      } catch (_error) {
        // 启动补偿阶段不再抛出二次清理异常
      }
    }
  }
};

module.exports = {
  browserManager
};
