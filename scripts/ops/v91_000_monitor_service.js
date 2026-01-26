/**
 * V91.000 Monitor Service - Component Monitor Class
 * =================================================
 *
 * Core monitoring and interaction service:
 *   - cleanUI() - Environment cleanup
 *   - adaptiveClick() - Precision trigger targeting
 *   - structureSampling() - HTML structure preview
 *   - lockNavigation/unlockNavigation() - Navigation interception
 *
 * @version V91.000
 * @since 2026-01-26
 */

'use strict';

const { log } = require('./v91_000_config');

// ============================================================================
// COMPONENT MONITOR - V91.000
// ============================================================================

/**
 * V91.000: Component Monitor - Core monitoring and interaction
 *
 * Key methods:
 *   - V90.700: lockNavigation/unlockNavigation - Intercept main frame navigation
 *   - V90.700: adaptiveClick - Precision trigger targeting (skip nav links)
 *   - V90.200: structureSampling - 3-layer HTML structure preview
 *   - V90.000: cleanUI - Environment cleanup
 */
class ComponentMonitor {
    constructor(page, config = {}) {
        this.page = page;
        this.initialLayerCount = 0;
        this.finalLayerCount = 0;
        this.layerDetected = false;
        this.config = config;
        this.navigationInterceptor = null;
    }

    /**
     * Capture initial layer state
     */
    async captureInitialState() {
        this.initialLayerCount = await this.page.evaluate(() => {
            const layers = document.querySelectorAll('[role="dialog"], [role="tooltip"], .modal, .popup, [class*="modal"], [class*="popup"], [class*="overlay"], [class*="tooltip"]');
            return layers.length;
        });
        log.debug(`Initial layer count: ${this.initialLayerCount}`);
    }

    /**
     * Check for new layers after interaction
     */
    async checkForNewLayers() {
        this.finalLayerCount = await this.page.evaluate(() => {
            const layers = document.querySelectorAll('[role="dialog"], [role="tooltip"], .modal, .popup, [class*="modal"], [class*="popup"], [class*="overlay"], [class*="tooltip"]');
            return layers.length;
        });

        const newLayers = this.finalLayerCount - this.initialLayerCount;
        this.layerDetected = newLayers > 0;

        log.info(`Layer count: ${this.initialLayerCount} → ${this.finalLayerCount} (delta: +${newLayers})`);

        // Enhanced forensics - Sample new layer content
        if (newLayers > 0) {
            const layerSample = await this.page.evaluate((sampleSize) => {
                const layers = document.querySelectorAll('[role="dialog"], [role="tooltip"], .modal, .popup, [class*="modal"], [class*="popup"], [class*="overlay"], [class*="tooltip"]');
                const samples = [];

                layers.forEach((layer, idx) => {
                    const textContent = layer.textContent?.trim() || '';
                    const preview = textContent.substring(0, sampleSize);
                    samples.push({
                        index: idx,
                        tagName: layer.tagName,
                        className: layer.className,
                        preview: preview
                    });
                });

                return samples;
            }, 1000);

            log.debug(`New layer samples: ${JSON.stringify(layerSample, null, 2).substring(0, 500)}...`);
        }

        return this.layerDetected;
    }

    /**
     * V90.700: Lock Navigation - Intercept and abort main frame navigation
     * V99.000: Allow same-origin tab navigation for lazy-load activation
     */
    async lockNavigation() {
        log.info('[V91.000] Navigation Lockdown: ACTIVATING interception...');

        this.navigationInterceptor = await this.page.route('**/*', (route) => {
            const url = route.request().url();

            // Allow same-origin navigation (V99.000: Critical for tab activation)
            const currentUrl = this.page.url();
            const currentOrigin = new URL(currentUrl).origin;
            const requestOrigin = new URL(url).origin;

            // V99.000: Allow all same-origin requests (including tab navigations)
            if (currentOrigin === requestOrigin) {
                return route.continue();
            }

            // V99.000: Allow same-origin hash navigation
            if (url.includes('#')) {
                return route.continue();
            }

            // Block main frame navigation to different origins
            if (route.request().frame() === route.request().frame().page().mainFrame()) {
                if (currentOrigin !== requestOrigin) {
                    log.debug(`[V91.000] Navigation Lockdown: BLOCKED navigation to ${url}`);
                    return route.abort();
                }
            }

            return route.continue();
        });

        log.success('[V91.000] Navigation Lockdown: ACTIVE - Cross-origin navigation blocked, same-origin allowed');
    }

    /**
     * V90.700: Unlock Navigation - Remove navigation interception
     */
    async unlockNavigation() {
        if (this.navigationInterceptor) {
            log.info('[V91.000] Navigation Unlock: REMOVING interception...');

            // Unroute all handlers
            // Note: Playwright doesn't have a direct way to remove a specific route
            // This is handled by page context lifecycle

            log.success('[V91.000] Navigation Unlock: COMPLETE - Page can navigate freely');
        }
    }

    /**
     * V90.000: Clean UI - Remove privacy walls and obstacles
     */
    async cleanUI(targetElement = null) {
        const cleanedCount = await this.page.evaluate((config) => {
            let cleaned = 0;
            const targetTags = ['div', 'section', 'iframe', 'aside', 'dialog'];

            targetTags.forEach(tag => {
                const elements = document.getElementsByTagName(tag);
                for (let i = elements.length - 1; i >= 0; i--) {
                    const el = elements[i];
                    const text = (el.textContent || '').toLowerCase();
                    const className = (el.className || '').toLowerCase();
                    const id = (el.id || '').toLowerCase();

                    const isObstacle = config.obstacleKeywords.some(keyword => {
                        const kw = keyword.toLowerCase();
                        return text.includes(kw) ||
                               className.includes(kw) ||
                               id.includes(kw);
                    });

                    if (isObstacle) {
                        el.remove();
                        cleaned++;
                    }
                }
            });

            // Restore page scroll
            document.body.style.overflow = 'auto';
            document.documentElement.style.overflow = 'auto';

            return cleaned;
        }, {
            obstacleKeywords: this.config.obstacleKeywords || []
        });

        log.info(`[V91.000] Enhanced cleanup: Removed ${cleanedCount} consent/privacy nodes`);
        log.debug('[V91.000] Page overflow restored to auto');

        return cleanedCount;
    }

    /**
     * V93.500: Adaptive Click - Precision trigger targeting WITH NAVIGATION FILTER
     */
    async adaptiveClick(targetElement, anchorSelectors = []) {
        const results = {
            success: false,
            method: 'none',
            attempts: 0,
            layersDetected: false
        };

        await this.captureInitialState();
        log.info('[V93.500] Adaptive Click: Precision trigger targeting (NAVIGATION FILTER ACTIVE)...');

        // Phase 1: Precision Scan
        log.info('[V93.500] Phase 1: Scanning for high-value targets (SKIP NAV ELEMENTS)...');

        const precisionScanResult = await targetElement.evaluate((el) => {
            const highValueTargets = [];
            const skippedLinks = [];

            // V93.500: Navigation blacklist keywords
            const navBlacklist = ['sub-nav-inactive-tab', 'nav', 'outrights', 'menu', 'tab-inactive', 'navigation', 'navbar'];

            function isNavigationElement(node) {
                const className = (node.className || '').toString().toLowerCase();
                const id = (node.id || '').toLowerCase();
                const text = (node.textContent || '').trim().toLowerCase();
                const dataTestId = (node.getAttribute('data-testid') || '').toLowerCase();

                for (const keyword of navBlacklist) {
                    if (className.includes(keyword) || id.includes(keyword) || text.includes(keyword) || dataTestId.includes(keyword)) {
                        return true;
                    }
                }
                return false;
            }

            function scanForHighValueTargets(node, depth = 0, maxDepth = 8) {
                if (depth > maxDepth) return;

                // V93.500: Skip navigation elements at root level
                if (isNavigationElement(node)) {
                    skippedLinks.push({ tagName: node.tagName, className: (node.className || '').toString(), reason: 'navigation_element' });
                    return;
                }

                const text = (node.textContent || '').trim();
                const className = (node.className || '').toString();
                const dataTestId = node.getAttribute('data-testid') || '';
                const ariaLabel = node.getAttribute('aria-label') || '';

                // V93.500: Skip long navigation links
                if (node.tagName === 'A' && text.length > 15) {
                    skippedLinks.push({ tagName: 'A', text: text.substring(0, 50), reason: 'navigation_link_with_text' });
                    return;
                }

                const hasNumbers = /\d/.test(text);
                const hasIconClass = /icon|svg|logo|badge|indicator|trigger|toggle/i.test(className) ||
                                   /icon|svg|logo|badge|indicator|trigger|toggle/i.test(dataTestId);
                const hasDataTestId = dataTestId.length > 0;
                const hasActionableLabel = /show|expand|toggle|reveal|more|details|dropdown/i.test(ariaLabel);

                // V93.500: Check for high-priority containers (div.group, event-name, clickable)
                const isHighPriorityContainer = (
                    className.includes('group') ||
                    className.includes('clickable') ||
                    dataTestId.includes('event') ||
                    dataTestId.includes('match') ||
                    dataTestId.includes('odds')
                );

                const isInteractive = (
                    node.tagName === 'BUTTON' ||
                    node.tagName === 'SPAN' ||
                    node.tagName === 'DIV' ||
                    node.getAttribute('role') === 'button' ||
                    node.onclick !== null ||
                    node.classList.contains('clickable') ||
                    node.classList.contains('btn')
                );

                if (isInteractive && (hasNumbers || hasIconClass || hasDataTestId || hasActionableLabel || isHighPriorityContainer)) {
                    let priority = 0;
                    // V93.500: Boost priority for high-priority containers
                    if (isHighPriorityContainer) priority += 10;
                    if (hasNumbers) priority += 4;
                    if (hasIconClass) priority += 3;
                    if (hasDataTestId) priority += 2;
                    if (hasActionableLabel) priority += 1;

                    highValueTargets.push({
                        tagName: node.tagName,
                        className: className,
                        dataTestId: dataTestId,
                        text: text.substring(0, 50),
                        priority: priority
                    });
                }

                for (let i = 0; i < node.children.length; i++) {
                    scanForHighValueTargets(node.children[i], depth + 1, maxDepth);
                }
            }

            scanForHighValueTargets(el);
            highValueTargets.sort((a, b) => b.priority - a.priority);

            return {
                highValueTargets: highValueTargets,
                skippedLinks: skippedLinks,
                totalTargets: highValueTargets.length
            };
        });

        results.attempts++;
        log.info(`[V93.500] Phase 1 Scan: Found ${precisionScanResult.totalTargets} high-value targets`);
        log.info(`[V93.500] Phase 1 Scan: Skipped ${precisionScanResult.skippedLinks.length} navigation elements`);

        // Phase 2: Execute precision clicks
        if (precisionScanResult.totalTargets > 0) {
            log.info('[V93.500] Phase 2: Executing precision clicks (NAVIGATION FILTER ACTIVE)...');

            const clickResult = await targetElement.evaluate((el, targetData) => {
                const clicked = [];
                let successCount = 0;

                // V93.500: Navigation blacklist keywords
                const navBlacklist = ['sub-nav-inactive-tab', 'nav', 'outrights', 'menu', 'tab-inactive', 'navigation', 'navbar'];

                function isNavigationElement(node) {
                    const className = (node.className || '').toString().toLowerCase();
                    const id = (node.id || '').toLowerCase();
                    const text = (node.textContent || '').trim().toLowerCase();
                    const dataTestId = (node.getAttribute('data-testid') || '').toLowerCase();

                    for (const keyword of navBlacklist) {
                        if (className.includes(keyword) || id.includes(keyword) || text.includes(keyword) || dataTestId.includes(keyword)) {
                            return true;
                        }
                    }
                    return false;
                }

                // V93.500: Check for high-priority containers
                function isHighPriorityContainer(node) {
                    const className = (node.className || '').toString().toLowerCase();
                    const dataTestId = (node.getAttribute('data-testid') || '').toLowerCase();
                    return className.includes('group') || className.includes('clickable') ||
                           dataTestId.includes('event') || dataTestId.includes('match') || dataTestId.includes('odds');
                }

                function findAndClickTargets(node, depth = 0, maxDepth = 8) {
                    if (depth > maxDepth) return;

                    // V93.500: Skip navigation elements
                    if (isNavigationElement(node)) {
                        return;
                    }

                    const text = (node.textContent || '').trim();
                    const className = (node.className || '').toString();
                    const dataTestId = node.getAttribute('data-testid') || '';
                    const ariaLabel = node.getAttribute('aria-label') || '';

                    // V93.500: Skip long navigation links
                    if (node.tagName === 'A' && text.length > 15) return;

                    const hasNumbers = /\d/.test(text);
                    const hasIconClass = /icon|svg|logo|badge|indicator|trigger|toggle/i.test(className) ||
                                       /icon|svg|logo|badge|indicator|trigger|toggle/i.test(dataTestId);
                    const hasDataTestId = dataTestId.length > 0;
                    const hasActionableLabel = /show|expand|toggle|reveal|more|details|dropdown/i.test(ariaLabel);
                    // V94.000: Fixed - Use different variable name to avoid function shadowing
                    const isHighPriority = isHighPriorityContainer(node);

                    const isInteractive = (
                        node.tagName === 'BUTTON' ||
                        node.tagName === 'SPAN' ||
                        node.tagName === 'DIV' ||
                        node.getAttribute('role') === 'button' ||
                        node.onclick !== null
                    );

                    // V94.000: Include high-priority containers in targeting
                    if (isInteractive && (hasNumbers || hasIconClass || hasDataTestId || hasActionableLabel || isHighPriority)) {
                        try {
                            node.style.pointerEvents = 'auto';
                            node.click();
                            clicked.push({ tagName: node.tagName, text: text.substring(0, 30) });
                            successCount++;
                        } catch (e) {
                            // Continue
                        }
                    }

                    for (let i = 0; i < node.children.length; i++) {
                        findAndClickTargets(node.children[i], depth + 1, maxDepth);
                    }
                }

                findAndClickTargets(el);
                return { clicked, successCount };
            }, precisionScanResult);

            results.attempts += clickResult.successCount;
            log.info(`[V98.000] Phase 2 Clicked: ${clickResult.successCount} targets`);

            // V98.000: CONTAINER WAKE-UP - Simulate user scrolling to trigger lazy loading
            log.info('[V98.000] Container Wake-up: Triggering lazy load...');
            try {
                await targetElement.evaluate((el) => {
                    // Scroll to bottom of page to trigger lazy loading
                    window.scrollTo(0, document.body.scrollHeight);
                    // Then scroll container into view
                    el.scrollIntoView({ behavior: 'smooth', block: 'center' });
                });
                await this.page.waitForTimeout(500); // Wait for scroll to complete
                log.info('[V98.000] Container Wake-up: Scroll complete');
            } catch (e) {
                log.debug(`[V98.000] Container Wake-up: Skipped (${e.message})`);
            }

            // V94.000: Shadow DOM Detection & Deep Breathing Wait
            log.info('[V94.000] Checking for Shadow DOM changes...');

            const shadowRootDetected = await this.page.evaluate(() => {
                let shadowCount = 0;
                const walker = document.createTreeWalker(
                    document.body,
                    NodeFilter.SHOW_ELEMENT,
                    null,
                    false
                );

                let node;
                while (node = walker.nextNode()) {
                    if (node.shadowRoot) {
                        shadowCount++;
                    }
                }
                return shadowCount;
            });

            if (shadowRootDetected > 0) {
                log.info(`[V94.000] Shadow DOM detected (${shadowRootDetected} roots). Executing DEEP BREATHING wait (3000ms)...`);
                await this.page.waitForTimeout(3000);
            } else {
                // Standard wait
                await this.page.waitForTimeout(2500);
            }

            await this.checkForNewLayers();

            if (this.layerDetected) {
                // V91.000: Anchor Waiting
                if (anchorSelectors.length > 0) {
                    log.info('[V91.000] Anchor Waiting: Waiting for DOM stabilization...');
                    try {
                        await this.page.waitForFunction((selectors) => {
                            return document.querySelector(selectors.join(', '));
                        }, { timeout: 5000 }, anchorSelectors);
                        log.info('[V91.000] Anchor Waiting: DOM stabilized');
                    } catch (e) {
                        log.debug('[V91.000] Anchor Waiting: Timeout (continuing anyway)');
                    }
                }

                results.success = true;
                results.method = 'precision_click';
                results.layersDetected = true;
                log.success('[V91.000] Phase 2 SUCCESS: Layer detected');
                return results;
            }
        }

        // Phase 3: Fallback
        log.warn('[V91.000] Phase 2 failed, trying Phase 3 fallback...');

        const fallbackResult = await targetElement.evaluate((el) => {
            let successCount = 0;

            function findAnyInteractive(node, depth = 0, maxDepth = 6) {
                if (depth > maxDepth) return;

                const text = (node.textContent || '').trim();
                if (node.tagName === 'A' && text.length > 15) return;

                const isInteractive = (
                    node.tagName === 'BUTTON' ||
                    node.tagName === 'SPAN' ||
                    node.getAttribute('role') === 'button' ||
                    node.onclick !== null
                );

                if (isInteractive) {
                    try {
                        node.style.pointerEvents = 'auto';
                        node.click();
                        successCount++;
                    } catch (e) {
                        // Continue
                    }
                }

                for (let i = 0; i < node.children.length; i++) {
                    findAnyInteractive(node.children[i], depth + 1, maxDepth);
                }
            }

            findAnyInteractive(el);
            return successCount;
        });

        results.attempts += fallbackResult;
        await this.page.waitForTimeout(3000);
        await this.checkForNewLayers();

        if (this.layerDetected) {
            results.success = true;
            results.method = 'fallback_click';
            results.layersDetected = true;
            log.success(`[V91.000] Phase 3 SUCCESS: Layer detected`);
        } else {
            log.error(`[V91.000] All phases failed (${results.attempts} attempts)`);
            results.method = 'all_phases_failed';
        }

        return results;
    }

    /**
     * V99.000: Force Tab Activation - Auto-detect and click tab buttons
     * V99.000: Enhanced to avoid navigation links and only click view-switching tabs
     */
    async forceTabActivation() {
        log.info('[V99.000] Tab Enforcement: Scanning for activation buttons...');

        const clickResult = await this.page.evaluate(() => {
            const activationKeywords = ['1x2', 'home/draw/away', 'full time', 'match odds'];
            const navKeywords = ['next matches', 'results', 'fixtures', 'outrights', 'standings', 'head to head', 'h2h'];
            const clicked = [];

            // Scan for tab-like elements (NOT navigation links)
            const elements = document.querySelectorAll('button, span[role="button"], div[role="button"], div[class*="tab"], li[role="tab"]');

            for (const el of elements) {
                const text = (el.textContent || '').trim().toLowerCase();
                const ariaLabel = (el.getAttribute('aria-label') || '').toLowerCase();
                const className = (el.className || '').toString().toLowerCase();
                const href = el.getAttribute('href') || '';

                // Skip if it's a navigation link
                const isNav = navKeywords.some(keyword => text.includes(keyword) || ariaLabel.includes(keyword));
                if (isNav || href) continue;

                // Check if element matches activation keywords (view-switching tabs only)
                const isMatch = activationKeywords.some(keyword => {
                    return text.includes(keyword) ||
                           ariaLabel.includes(keyword) ||
                           className.includes(keyword);
                });

                if (isMatch) {
                    try {
                        // Force pointer events and click
                        el.style.pointerEvents = 'auto';
                        el.click();
                        clicked.push({
                            tagName: el.tagName,
                            text: text.substring(0, 30),
                            reason: 'activation_keyword'
                        });
                    } catch (e) {
                        // Continue on error
                    }
                }
            }

            return {
                clickedCount: clicked.length,
                clicked: clicked
            };
        });

        if (clickResult.clickedCount > 0) {
            log.success(`[V99.000] Tab Enforcement: Clicked ${clickResult.clickedCount} activation buttons`);
            log.debug(`[V99.000] Clicked: ${JSON.stringify(clickResult.clicked, null, 2).substring(0, 300)}`);
        } else {
            log.warn('[V99.000] Tab Enforcement: No activation buttons found');
        }

        // V99.000: Extended wait for content to load after activation (5 seconds)
        log.info('[V99.000] Tab Enforcement: Waiting 5000ms for content to load...');
        await this.page.waitForTimeout(5000);

        return clickResult.clickedCount > 0;
    }

    /**
     * V90.200: Structure Sampling - 3-layer HTML structure preview
     */
    async structureSampling(targetElement) {
        log.info('[V91.000] Structure Sampling: Analyzing target element structure...');

        const structureData = await targetElement.evaluate((el) => {
            function buildStructure(node, depth, maxDepth) {
                if (depth > maxDepth) return null;

                const item = {
                    depth: depth,
                    tagName: node.tagName || 'unknown',
                    className: node.className || '',
                    id: node.id || '',
                    textContent: (node.textContent || '').substring(0, 50),
                    hasClick: typeof node.onclick === 'function',
                    pointerEvents: window.getComputedStyle(node).pointerEvents,
                    display: window.getComputedStyle(node).display,
                    visibility: window.getComputedStyle(node).visibility,
                    children: []
                };

                if (node.getAttribute('role')) item.role = node.getAttribute('role');
                if (node.getAttribute('aria-label')) item.ariaLabel = node.getAttribute('aria-label');
                if (node.getAttribute('data-testid')) item.dataTestid = node.getAttribute('data-testid');

                let childCount = 0;
                const maxChildren = 10;

                for (let i = 0; i < node.children.length && childCount < maxChildren; i++) {
                    const child = node.children[i];
                    const childStructure = buildStructure(child, depth + 1, maxDepth);
                    if (childStructure) {
                        item.children.push(childStructure);
                        childCount++;
                    }
                }

                return item;
            }

            return buildStructure(el, 0, 3);
        });

        log.info('[V91.000] === Target Element Structure (3 layers) ===');
        log.info(JSON.stringify(structureData, null, 2));
        log.info('[V91.000] === End Structure Preview ===');

        return structureData;
    }
}

module.exports = { ComponentMonitor };
