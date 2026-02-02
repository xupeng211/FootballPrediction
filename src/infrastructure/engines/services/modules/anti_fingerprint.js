/**
 * Anti-Fingerprint - V158.000 Overlay Removal & Detection Avoidance
 * ================================================================
 *
 * Anti-detection features for avoiding bot detection.
 * Extracted from SurgicalInteraction.js for modular architecture.
 *
 * V145.000 Features:
 * - Scroll settle delay (800ms) for page rendering
 *
 * V146.000 Features:
 * - React async rendering wait (waitForSelector)
 *
 * V158.000 Features:
 * - OneTrust cookie banner aggressive removal
 * - Z-index based overlay purge (>1000 non-data containers)
 *
 * @module services/modules/anti_fingerprint
 * @version V1.0
 * @since 2026-01-31
 * @author [Genesis.Standardization]
 */

'use strict';

const { OddsPortalSelectors } = require('../../selectors/OddsPortalSelectors');

/**
 * Anti-Fingerprint - Anti-detection features
 */
class AntiFingerprint {
    /**
     * @param {Object} page - Playwright page object
     * @param {Object} config - Configuration object
     * @param {boolean} config.forceRemoveOverlays - Enable brute force overlay removal
     * @param {boolean} config.scrollIntoViewBeforeHover - Enable scroll before hover
     * @param {number} config.scrollSettleDelayMs - Scroll settle delay (ms)
     * @param {number} config.reactRenderTimeoutMs - React render timeout (ms)
     * @param {string} config.logLevel - Logging level
     */
    constructor(page, config = {}) {
        this.page = page;

        const scrollSettleDelayMs = parseInt(process.env.SCROLL_SETTLE_DELAY_MS) || 800;

        this.config = {
            forceRemoveOverlays: config.forceRemoveOverlays !== undefined
                ? config.forceRemoveOverlays
                : (process.env.FORCE_REMOVE_OVERLAYS === 'true'),
            scrollIntoViewBeforeHover: config.scrollIntoViewBeforeHover !== undefined
                ? config.scrollIntoViewBeforeHover
                : (process.env.SCROLL_INTO_VIEW_BEFORE_HOVER === 'true'),
            scrollSettleDelayMs,
            reactRenderTimeoutMs: config.reactRenderTimeoutMs || 10000,
            logLevel: config.logLevel || 'info'
        };
    }

    /**
     * V145.000: Scroll settle - give page time to render after scrolling
     * @returns {Promise<void>}
     */
    async scrollSettle() {
        const delay = this.config.scrollSettleDelayMs;

        if (this.config.logLevel === 'debug') {
            console.log(`[V145.000] 📜 Scroll settling: ${delay}ms...`);
        }

        await this.page.waitForTimeout(delay);
    }

    /**
     * V146.000: Wait for React async rendering to complete
     *
     * @param {number} timeout - Maximum wait time (milliseconds), default from config
     * @returns {Promise<boolean>} True if cells rendered successfully
     */
    async waitForReactRender(timeout = null) {
        const waitTimeout = timeout || this.config.reactRenderTimeoutMs;

        if (this.config.logLevel === 'debug') {
            console.log(`[V146.000] ⏳ Waiting for React render: ${waitTimeout}ms timeout...`);
        }

        try {
            // V146.000: Wait for odds cells to be present in DOM
            await this.page.waitForSelector('[class*="odds-cell"]', {
                timeout: waitTimeout,
                state: 'attached'
            });

            if (this.config.logLevel === 'debug') {
                console.log(`[V146.000] ✅ React render complete - odds cells detected`);
            }

            return true;
        } catch (error) {
            console.log(`[V146.000] ⚠️  React render timeout: ${error.message}`);
            return false;
        }
    }

    /**
     * V145.000: Handle overlays - BRUTE FORCE PURGE with detailed logging
     * V158.000: Enhanced OneTrust cookie banner aggressive removal
     * V158.000: Z-index based overlay purge (>1000 non-data containers)
     *
     * @returns {Promise<boolean>} True if overlays were removed
     */
    async handleOverlays() {
        try {
            console.log('[V145.000] 🧹 PHYSICAL CLEANUP START');
            console.log('[V145.000] Force remove config:', this.config.forceRemoveOverlays);

            // [V162.Precision] Environment Initialization: CSS Hiding (Surgical Mode)
            await this.page.addStyleTag({
                content: `
                    #onetrust-banner-sdk, .onetrust-pc-dark-filter,
                    [id*="onetrust"], [class*="ot-sdk"] {
                        display: none !important;
                        visibility: hidden !important;
                        pointer-events: none !important;
                    }
                `
            });
            console.log('[V162.Precision] 🛡️ CSS Shield Activated: OneTrust hidden');

            // Wait briefly for overlay to appear
            await this.page.waitForTimeout(500);

            let removedCount = 0;
            const removedElements = [];

            if (this.config.forceRemoveOverlays) {
                console.log('[V145.000] 💀 BRUTE FORCE MODE ENGAGED');

                // V158.000: AGGRESSIVE OneTrust Removal
                console.log('[V158.000] 🎯 TARGET: OneTrust Cookie Banner (z-index: 2147483645)');

                // Method 1: Try clicking "Reject All" button
                const oneTrustReject = await this.page.evaluate(() => {
                    const rejectBtn = document.querySelector('#onetrust-reject-all-handler');
                    if (rejectBtn && rejectBtn.offsetParent !== null) {
                        rejectBtn.click();
                        return true;
                    }
                    return false;
                });

                if (oneTrustReject) {
                    console.log('[V158.000] ✅ OneTrust: Clicked "Reject All" button');
                    await this.page.waitForTimeout(1000);
                }

                // Method 2: Remove OneTrust container directly
                const oneTrustPurge = await this.page.evaluate(() => {
                    const selectors = [
                        '#onetrust-banner-sdk',
                        '#onetrust-consent-sdk',
                        '.ot-sdk-container',
                        '[id*="onetrust"]',
                        '[class*="ot-sdk"]'
                    ];

                    let count = 0;
                    for (const sel of selectors) {
                        const elements = document.querySelectorAll(sel);
                        elements.forEach(el => {
                            el.remove();
                            count++;
                        });
                    }
                    return count;
                });

                if (oneTrustPurge > 0) {
                    console.log(`[V158.000] 🔥 OneTrust: Purged ${oneTrustPurge} containers`);
                    removedCount += oneTrustPurge;
                    removedElements.push('OneTrust containers');
                }

                // V158.000: Z-INDEX BASED OVERLAY PURGE
                const zIndexPurge = await this.page.evaluate(() => {
                    const allElements = document.querySelectorAll('*');
                    const removed = [];
                    const dataKeywords = ['odds', 'bet', 'match', 'team', 'score', 'time', 'league', 'sport'];

                    for (const el of allElements) {
                        try {
                            const style = window.getComputedStyle(el);
                            const zIndex = parseInt(style.zIndex);

                            if (zIndex > 1000 && el.offsetParent !== null) {
                                const text = el.textContent?.toLowerCase() || '';
                                const className = el.className?.toLowerCase() || '';

                                const isDataContainer = dataKeywords.some(kw =>
                                    text.includes(kw) || className.includes(kw)
                                );

                                if (!isDataContainer) {
                                    removed.push({
                                        tag: el.tagName,
                                        class: className,
                                        zIndex: zIndex,
                                        text: text.substring(0, 50)
                                    });
                                    el.remove();
                                }
                            }
                        } catch (e) {
                            // Continue on error
                        }
                    }

                    return removed;
                });

                if (zIndexPurge.length > 0) {
                    console.log(`[V158.000] 🔥 Z-INDEX PURGE: Removed ${zIndexPurge.length} high-z overlays`);
                    zIndexPurge.slice(0, 5).forEach(item => {
                        console.log(`[V158.000]   - ${item.tag}.${item.class} (z-index: ${item.zIndex})`);
                    });
                    removedCount += zIndexPurge.length;
                    removedElements.push('High-z-index overlays');
                }

                // V166.000: Sticky Header Suppression
                // Hide fixed headers that might intercept clicks/hovers
                const stickyHeaderPurge = await this.page.evaluate(() => {
                    const fixedElements = Array.from(document.querySelectorAll('*')).filter(el => {
                        const style = window.getComputedStyle(el);
                        return style.position === 'fixed' && style.top === '0px' && el.offsetHeight < 150;
                    });
                    
                    let count = 0;
                    fixedElements.forEach(el => {
                        el.style.display = 'none';
                        el.style.visibility = 'hidden';
                        el.style.pointerEvents = 'none';
                        count++;
                    });
                    return count;
                });
                
                if (stickyHeaderPurge > 0) {
                     console.log(`[V166.000] 🛡️ Sticky Header Suppression: Hidden ${stickyHeaderPurge} elements`);
                     removedCount += stickyHeaderPurge;
                }

                // V145.000: Use OddsPortalSelectors for general overlay purge
                const purgeScript = OddsPortalSelectors.generatePurgeScript();
                const purgeResult = await this.page.evaluate(purgeScript);

                removedCount += purgeResult.count;
                removedElements.push(...purgeResult.removed);

                // V145.000: Enhanced logging
                console.log(`[V145.000] 🔪 PHYSICAL PURGE COMPLETE`);
                console.log(`[V145.000] ✅ 已物理粉碎遮罩层: ${removedElements.slice(0, 5).join(', ')}${removedElements.length > 5 ? '...' : ''}`);
                console.log(`[V145.000] Total nodes removed: ${removedCount}`);

                // Log specific overlay types
                if (removedElements.some(r => r.includes('bookie'))) {
                    console.log('[V145.000] 🔥 SMOKED: .overlay-bookie-modal');
                }
                if (removedElements.some(r => r.includes('onetrust'))) {
                    console.log('[V145.000] 🔥 SMOKED: #onetrust-banner');
                }
                if (removedElements.some(r => r.includes('consent'))) {
                    console.log('[V145.000] 🔥 SMOKED: Cookie consent banner');
                }

                if (removedCount > 0) {
                    console.log(`[V145.000] ✅ OVERLAY PURGE: ${removedCount} nodes eliminated`);
                } else {
                    console.log('[V145.000] ℹ️  No overlays detected - clean slate');
                }
            } else {
                console.log('[V145.000] ⚠️  WARNING: Force remove DISABLED - using click fallback');
            }

            return removedCount > 0;

        } catch (error) {
            console.warn(`[V145.000] ❌ Overlay handling error: ${error.message}`);
            return false;
        }
    }
}

module.exports = { AntiFingerprint };
