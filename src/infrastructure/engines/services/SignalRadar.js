/**
 * SignalRadar - V141.000 Refactored Module
 * ===============================================
 *
 * Network traffic monitoring for trajectory data packet signals.
 * Extracted from QuantHarvester.js for modular architecture.
 *
 * @module services/SignalRadar
 * @version V141.000
 * @since 2026-01-27
 * @author Senior Lead Software Architect (Refactoring Specialist)
 *
 * Features:
 * - Adaptive signal detection (V136.000)
 * - .dat file response monitoring
 * - Pre-loaded data bypass
 * - Configurable timeouts
 */

'use strict';

/**
 * SignalRadar - Monitors network traffic for trajectory data signals
 */
class SignalRadar {
    /**
     * @param {Object} page - Playwright page object
     * @param {Object} config - Configuration object
     * @param {number} config.signalWaitTimeout - Full timeout for signal wait (ms)
     * @param {number} config.adaptiveSignalTimeout - Quick adaptive check timeout (ms)
     * @param {string} config.logLevel - Logging level
     */
    constructor(page, config = {}) {
        this.page = page;
        this.config = {
            signalWaitTimeout: config.signalWaitTimeout || 15000,
            adaptiveSignalTimeout: config.adaptiveSignalTimeout || 5000,
            logLevel: config.logLevel || 'info'
        };
    }

    /**
     * V127.000: Randomized jitter wait (human behavior simulation)
     * @param {number} min - Minimum wait time (ms)
     * @param {number} jitter - Jitter range (ms)
     * @returns {Promise<void>}
     */
    async jitterWait(min = 2000, jitter = 1500) {
        const delay = Math.floor(Math.random() * jitter) + min;
        await this.page.waitForTimeout(delay);
    }

    /**
     * V136.000: Adaptive wait for trajectory data packet signal
     * V133.000: Monitors network traffic for OddsPortal's .dat file response
     * V136.000: Adaptive bypass - if odds visible but no .dat signal, proceed anyway
     *
     * @returns {Promise<Object>} Result object with detected, bypass, and method flags
     */
    async waitForTrajectorySignal() {
        try {
            // V134.000: Instrumentation - Log signal radar activation
            console.log('[V136.000] ========== ADAPTIVE SIGNAL RADAR ==========');
            console.log('[V136.000] Adaptive timeout:', this.config.adaptiveSignalTimeout, 'ms');
            console.log('[V136.000] Fallback timeout:', this.config.signalWaitTimeout, 'ms');
            console.log('[V136.000] 📡 Signal radar NOW MONITORING for .dat packets...');

            let signalDetected = false;
            let adaptiveBypass = false;

            // V136.000: Phase 1 - Quick adaptive check (5 seconds)
            const adaptiveSignalPromise = this.page.waitForResponse(
                response => {
                    const url = response.url();
                    const isDatFile = /.*\.dat.*/i.test(url);
                    const isStatusOk = response.status() === 200;

                    if (isDatFile && isStatusOk) {
                        console.log(`[V136.000] 🔒 SIGNAL LOCKED (Adaptive): ${url}`);
                        return true;
                    }
                    return false;
                },
                { timeout: this.config.adaptiveSignalTimeout }
            ).then(() => {
                signalDetected = true;
                console.log('[V136.000] ✅ Signal found in adaptive window');
                return true;
            }).catch(async () => {
                // V136.000: Adaptive bypass - check if odds cells are visible
                console.log('[V136.000] ⏱️  Adaptive timeout - checking if data is pre-loaded...');

                const oddsCellCount = await this.page.$$eval('[class*="odds-cell"]', els => els.length);

                if (oddsCellCount > 0) {
                    console.log(`[V136.000] ✅ ADAPTIVE BYPASS: ${oddsCellCount} odds cells visible, proceeding anyway`);
                    adaptiveBypass = true;
                    return true;  // Continue despite no .dat signal
                } else {
                    console.log('[V136.000] ⏳  No odds cells yet, waiting for full timeout...');
                    // Fall through to Phase 2
                    return false;
                }
            });

            await adaptiveSignalPromise;

            // V136.000: Phase 2 - Full timeout wait (only if adaptive bypass failed)
            if (!signalDetected && !adaptiveBypass) {
                console.log('[V136.000] Entering Phase 2: Full timeout wait...');

                const remainingTimeout = this.config.signalWaitTimeout - this.config.adaptiveSignalTimeout;

                await this.page.waitForResponse(
                    response => {
                        const url = response.url();
                        const isDatFile = /.*\.dat.*/i.test(url);
                        const isStatusOk = response.status() === 200;

                        if (isDatFile && isStatusOk) {
                            console.log(`[V136.000] 🔒 SIGNAL LOCKED (Full): ${url}`);
                            return true;
                        }
                        return false;
                    },
                    { timeout: remainingTimeout }
                ).then(() => {
                    signalDetected = true;
                    console.log('[V136.000] ✅ Signal found in full window');
                    return true;
                }).catch(() => {
                    console.log('[V136.000] ⏱️  Full timeout - data may be pre-loaded or no .dat packets');
                    return false;
                });
            }

            // Additional wait for DOM to stabilize after signal
            if (signalDetected) {
                console.log('[V136.000] 📊 Signal detected, waiting for DOM stabilization...');
                await this.jitterWait(1000, 500);
            } else if (adaptiveBypass) {
                console.log('[V136.000] 📊 Adaptive bypass active, brief stabilization wait...');
                await this.page.waitForTimeout(500);  // Shorter wait for bypass
            }

            const result = {
                detected: signalDetected,
                bypass: adaptiveBypass,
                success: signalDetected || adaptiveBypass,
                method: signalDetected ? 'LOCKED' : adaptiveBypass ? 'BYPASS' : 'TIMEOUT'
            };

            console.log(`[V136.000] Signal result: ${result.method}`);
            return result;

        } catch (error) {
            console.log(`[V136.000] ❌ Signal detection error: ${error.message}`);
            return {
                detected: false,
                bypass: false,
                success: false,
                method: 'ERROR',
                error: error.message
            };
        }
    }

    /**
     * Wait for odds content to appear on page
     * @param {number} maxAttempts - Maximum wait attempts (default: 30)
     * @returns {Promise<boolean>} True if odds content found
     */
    async waitForOddsContent(maxAttempts = 30) {
        let waitAttempts = 0;
        while (waitAttempts < maxAttempts) {
            const oddsCellCount = await this.page.$$eval('[class*="odds-cell"]', els => els.length);
            if (oddsCellCount > 0) {
                console.log(`[V136.000] ✅ Odds content found: ${oddsCellCount} cells`);
                return true;
            }
            await this.jitterWait(1000, 500);
            waitAttempts++;
        }
        console.log('[V136.000] ⚠️  No odds content found after ' + maxAttempts + ' attempts');
        return false;
    }
}

module.exports = { SignalRadar };
