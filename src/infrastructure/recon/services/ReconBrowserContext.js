'use strict';

const { chromium: playwrightChromium } = require('playwright');

const { browserManager } = require('./BrowserManager');
const { createPageContextState, pageContextState } = require('./PageContextState');

class ReconBrowserContext {
  constructor(options = {}) {
    this.chromium = options.chromium || playwrightChromium;
    Object.assign(this, createPageContextState(options));
  }
}

Object.assign(
  ReconBrowserContext.prototype,
  pageContextState,
  browserManager
);

module.exports = { ReconBrowserContext };
