'use strict';

const { RECON_CONFIG, getReconConfigSection } = require('./ReconServiceConfig');
const { reconExtractionUtils } = require('./ReconExtractionUtils');
const { reconDomCollectionFlow } = require('./ReconDomCollectionFlow');

const DOM_SCRAPER_CONFIG = getReconConfigSection(['recon_runtime', 'dom_scraper'], {});
const BASE_URL = DOM_SCRAPER_CONFIG.base_url || RECON_CONFIG.oddsportal.base_url;

class ReconDomScraper {
  constructor(options = {}) {
    this.logger = options.logger || console;
    this.traceId = options.traceId || 'trace-unknown';
    this.baseUrl = options.baseUrl || BASE_URL;
    this.page = options.page || null;
    this.scrollAttempts = options.scrollAttempts || DOM_SCRAPER_CONFIG.scroll_attempts;
    this.scrollDelayMs = options.scrollDelayMs || DOM_SCRAPER_CONFIG.scroll_delay_ms;
    this.timeoutMs = Number(options.timeoutMs ?? DOM_SCRAPER_CONFIG.timeout_ms);
    this.maxPages = Number(options.maxPages ?? DOM_SCRAPER_CONFIG.max_pages);
    this.postNavigationWaitMs = Number(options.postNavigationWaitMs ?? DOM_SCRAPER_CONFIG.post_navigation_wait_ms);
    this.minScrollRounds = Number(options.minScrollRounds ?? DOM_SCRAPER_CONFIG.min_scroll_rounds);
    this.stagnantRoundsThreshold = Number(options.stagnantRoundsThreshold ?? DOM_SCRAPER_CONFIG.stagnant_rounds_threshold);
    this.pageScrollFloorPx = Number(options.pageScrollFloorPx ?? DOM_SCRAPER_CONFIG.page_scroll_floor_px);
    this.pageScrollStepBasePx = Number(options.pageScrollStepBasePx ?? DOM_SCRAPER_CONFIG.page_scroll_step_base_px);
    this.pageScrollWaitCapMs = Number(options.pageScrollWaitCapMs ?? DOM_SCRAPER_CONFIG.page_scroll_wait_cap_ms);
    this.pageScrollWaitMs = Number(options.pageScrollWaitMs ?? DOM_SCRAPER_CONFIG.page_scroll_wait_ms);
    this.wakeMouseX = Number(options.wakeMouseX ?? DOM_SCRAPER_CONFIG.wake_mouse_x);
    this.wakeMouseY = Number(options.wakeMouseY ?? DOM_SCRAPER_CONFIG.wake_mouse_y);
    this.wakeScrollStepPx = Number(options.wakeScrollStepPx ?? DOM_SCRAPER_CONFIG.wake_scroll_step_px);
  }

  setPage(page) {
    this.page = page;
  }
}

Object.assign(ReconDomScraper.prototype, reconExtractionUtils, reconDomCollectionFlow);

module.exports = {
  ReconDomScraper
};
