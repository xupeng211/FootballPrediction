/**
 * V105.000 Diagnostic Probe - Deep Dive & Self-Heal
 * ===================================================
 *
 * V105.000: Autonomous diagnostic system for detail page extraction
 *   - HTTP status code monitoring (403/429 detection)
 *   - Source code snapshot (page.content() analysis)
 *   - Headless mode comparison (true vs false)
 *   - Response interception and analysis
 *   - Cookie/Referer analysis
 *
 * @version V105.000
 * @since 2026-01-26
 */

'use strict';

const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

// ============================================================================
// V105.000 CONFIGURATION
// ============================================================================

const TARGET_URL = process.env.TARGET_URL || 'https://www.oddsportal.com/football/england/premier-league/everton-arsenal-83299048/';

const CONFIG = {
    // User agents to try
    userAgents: [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:132.0) Gecko/20100101 Firefox/132.0'
    ],
    // Browser launch options
    headlessModes: [true, false],
    timeout: 60000,
    outputDir: path.join(__dirname, '../../logs/v105_diagnostic')
};

// ============================================================================
// LOGGING
// ============================================================================

const log = {
    info: (msg) => console.log(`[V105.000] [INFO] ${msg}`),
    success: (msg) => console.log(`[V105.000] [SUCCESS] ${msg}`),
    warn: (msg) => console.warn(`[V105.000] [WARN] ${msg}`),
    error: (msg) => console.error(`[V105.000] [ERROR] ${msg}`),
    section: (title) => {
        console.log('\n' + '='.repeat(70));
        console.log(`[V105.000] ${title}`);
        console.log('='.repeat(70));
    }
};

// ============================================================================
// DIAGNOSTIC PROBE CLASS
// ============================================================================

class DiagnosticProbe {
    constructor() {
        this.results = {
            httpStatuses: [],
            responses: [],
            pageSnapshots: [],
            cookies: [],
            timing: {}
        };
        this.ensureOutputDir();
    }

    ensureOutputDir() {
        if (!fs.existsSync(CONFIG.outputDir)) {
            fs.mkdirSync(CONFIG.outputDir, { recursive: true });
        }
    }

    saveSnapshot(filename, content) {
        const filepath = path.join(CONFIG.outputDir, filename);
        fs.writeFileSync(filepath, content, 'utf8');
        log.info(`Snapshot saved: ${filepath}`);
    }

    /**
     * V105.000: HTTP Status Code Monitor
     * Captures all response status codes during page load
     */
    async captureHttpStatuses(page) {
        const statuses = [];

        page.on('response', async (response) => {
            const url = response.url();
            const status = response.status();
            const headers = response.headers();

            // Only capture relevant responses
            if (url.includes('oddsportal') || status >= 400) {
                statuses.push({
                    url: url,
                    status: status,
                    headers: headers,
                    timestamp: Date.now()
                });

                // Alert on critical status codes
                if (status === 403) {
                    log.error(`[HTTP 403] Forbidden: ${url}`);
                } else if (status === 429) {
                    log.error(`[HTTP 429] Rate Limited: ${url}`);
                }
            }
        });

        return statuses;
    }

    /**
     * V105.000: Source Code Snapshot
     * Captures full page HTML content for analysis
     */
    async captureSourceCode(page) {
        try {
            const content = await page.content();
            const title = await page.title();
            const url = page.url();

            // Check for obfuscation patterns
            const obfuscationIndicators = [
                { pattern: /eval\s*\(/i, name: 'eval() usage' },
                { pattern: /\\x[0-9a-f]{2}/i, name: 'Hex encoding' },
                { pattern: /\\u[0-9a-f]{4}/i, name: 'Unicode escape' },
                { pattern: /atob\s*\(/i, name: 'Base64 decoding' },
                { pattern: /document\.write/i, name: 'document.write' }
            ];

            const detectedObfuscation = [];
            for (const indicator of obfuscationIndicators) {
                if (indicator.pattern.test(content)) {
                    detectedObfuscation.push(indicator.name);
                }
            }

            return {
                url: url,
                title: title,
                content: content,
                contentLength: content.length,
                obfuscationDetected: detectedObfuscation
            };
        } catch (error) {
            log.error(`Failed to capture source code: ${error.message}`);
            return null;
        }
    }

    /**
     * V105.000: Cookie & Referer Analysis
     */
    async captureCookies(context) {
        try {
            const cookies = await context.cookies();
            return {
                count: cookies.length,
                cookies: cookies.map(c => ({
                    name: c.name,
                    domain: c.domain,
                    path: c.path,
                    httpOnly: c.httpOnly,
                    secure: c.secure
                }))
            };
        } catch (error) {
            log.error(`Failed to capture cookies: ${error.message}`);
            return null;
        }
    }

    /**
     * V105.000: Float Number Pattern Search
     * Auto-discover odds patterns in the page
     */
    async discoverOddsPatterns(page) {
        try {
            const oddsData = await page.evaluate(() => {
                // Look for patterns like "2.10 3.50 4.20" (three floats together)
                const bodyText = document.body.innerText || '';

                // Extract potential odds (1.01 - 20.00 range)
                const oddsPattern = /\b([1-9]\.\d{2}|20\.00)\b/g;
                const matches = bodyText.match(oddsPattern) || [];

                // Group consecutive numbers (potential 1X2 odds)
                const groups = [];
                const lines = bodyText.split('\n');
                for (const line of lines) {
                    const lineMatches = line.match(oddsPattern);
                    if (lineMatches && lineMatches.length >= 3) {
                        groups.push({
                            text: line.trim().substring(0, 100),
                            odds: lineMatches.slice(0, 5) // Take first 5
                        });
                    }
                }

                return {
                    totalMatches: matches.length,
                    uniqueOdds: [...new Set(matches)].length,
                    sampleGroups: groups.slice(0, 10) // First 10 groups
                };
            });

            return oddsData;
        } catch (error) {
            log.error(`Failed to discover odds patterns: ${error.message}`);
            return null;
        }
    }

    /**
     * V105.000: Main diagnostic probe
     */
    async probe(headless = true, userAgentIndex = 0) {
        log.section(`PROBE START: headless=${headless}, UA=${userAgentIndex}`);

        const probeResult = {
            headless: headless,
            userAgent: CONFIG.userAgents[userAgentIndex],
            startTime: Date.now(),
            success: false,
            errors: []
        };

        let browser = null;
        let context = null;
        let page = null;

        try {
            // Launch browser with stealth options
            const launchOptions = {
                headless: headless,
                args: [
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                    '--disable-setuid-sandbox'
                ],
                ignoreDefaultArgs: ['--enable-automation']
            };

            browser = await chromium.launch(launchOptions);

            context = await browser.newContext({
                userAgent: CONFIG.userAgents[userAgentIndex],
                viewport: { width: 1280, height: 800 }
            });

            page = await context.newPage();

            // Set up HTTP monitoring
            const httpStatuses = await this.captureHttpStatuses(page);

            // Navigate to target
            log.info(`Navigating to: ${TARGET_URL}`);
            const gotoStart = Date.now();
            const response = await page.goto(TARGET_URL, {
                timeout: CONFIG.timeout,
                waitUntil: 'networkidle'
            });
            const gotoTime = Date.now() - gotoStart;

            probeResult.gotoTime = gotoTime;
            probeResult.httpStatus = response ? response.status() : 'NO_RESPONSE';
            probeResult.httpStatuses = httpStatuses;

            log.info(`Navigation complete: ${probeResult.httpStatus} (${gotoTime}ms)`);

            // Wait for body
            try {
                await page.waitForSelector('body', { state: 'visible', timeout: 10000 });
            } catch (e) {
                log.warn('Body selector timeout');
            }

            // Capture page title
            const pageTitle = await page.title();
            probeResult.pageTitle = pageTitle;
            log.info(`Page title: "${pageTitle}"`);

            // Capture source code
            log.info('Capturing source code...');
            const sourceCode = await this.captureSourceCode(page);
            probeResult.sourceCode = sourceCode;

            // Save source snapshot
            const filename = `snapshot_h${headless ? 1 : 0}_ua${userAgentIndex}_${Date.now()}.html`;
            this.saveSnapshot(filename, sourceCode.content);

            // Capture cookies
            const cookies = await this.captureCookies(context);
            probeResult.cookies = cookies;

            // Discover odds patterns
            log.info('Discovering odds patterns...');
            const oddsPatterns = await this.discoverOddsPatterns(page);
            probeResult.oddsPatterns = oddsPatterns;

            // Analysis
            log.section('ANALYSIS RESULTS');

            // 1. Access Denied Detection
            if (pageTitle.includes('Access Denied') || pageTitle.includes('403') ||
                pageTitle.includes('Forbidden') || pageTitle.trim() === '') {
                log.error('[ACCESS DENIED] Page title indicates blocking');
                probeResult.errors.push('ACCESS_DENIED');
            }

            // 2. HTTP Status Analysis
            const criticalStatuses = httpStatuses.filter(s => s.status >= 400);
            if (criticalStatuses.length > 0) {
                log.warn(`[${criticalStatuses.length}] HTTP errors detected:`);
                criticalStatuses.forEach(s => {
                    log.error(`  [${s.status}] ${s.url.substring(0, 80)}...`);
                });
                probeResult.errors.push('HTTP_ERRORS');
            }

            // 3. Obfuscation Detection
            if (sourceCode.obfuscationDetected.length > 0) {
                log.warn(`[OBFUSCATION] Detected: ${sourceCode.obfuscationDetected.join(', ')}`);
                probeResult.errors.push('OBFUSCATION');
            }

            // 4. Odds Pattern Detection
            if (oddsPatterns && oddsPatterns.sampleGroups && oddsPatterns.sampleGroups.length > 0) {
                log.success(`[ODDS DETECTED] Found ${oddsPatterns.sampleGroups.length} potential odds groups`);
                oddsPatterns.sampleGroups.slice(0, 3).forEach((group, i) => {
                    log.info(`  Group ${i + 1}: ${group.odds.join(', ')}`);
                    log.info(`    Text: ${group.text}`);
                });
                probeResult.success = true;
            } else {
                log.error('[NO ODDS] No odds patterns detected in page content');
                probeResult.errors.push('NO_ODDS');
            }

            // 5. Content Length Analysis
            if (sourceCode.contentLength < 5000) {
                log.warn(`[LOW CONTENT] Page content only ${sourceCode.contentLength} bytes`);
                probeResult.errors.push('LOW_CONTENT');
            }

            probeResult.endTime = Date.now();
            probeResult.totalTime = probeResult.endTime - probeResult.startTime;

            log.info(`Probe complete: ${probeResult.totalTime}ms`);

        } catch (error) {
            log.error(`Probe failed: ${error.message}`);
            probeResult.errors.push('FATAL_ERROR');
            probeResult.fatalError = error.message;
        } finally {
            if (page) await page.close();
            if (context) await context.close();
            if (browser) await browser.close();
        }

        return probeResult;
    }

    /**
     * V105.000: Run comprehensive diagnostic cycle
     */
    async runFullDiagnostic() {
        log.section('V105.000 DEEP DIVE DIAGNOSTIC START');
        log.info(`Target URL: ${TARGET_URL}`);
        log.info(`Output directory: ${CONFIG.outputDir}`);

        const results = [];

        // Test different configurations
        const configurations = [
            { headless: true, uaIndex: 0 },
            { headless: false, uaIndex: 0 },
            { headless: true, uaIndex: 1 },
        ];

        for (let i = 0; i < configurations.length; i++) {
            const config = configurations[i];
            log.section(`TEST ${i + 1}/${configurations.length}`);

            const result = await this.probe(config.headless, config.uaIndex);
            results.push(result);

            // Brief pause between tests
            if (i < configurations.length - 1) {
                log.info('Waiting 5 seconds before next test...');
                await new Promise(resolve => setTimeout(resolve, 5000));
            }
        }

        // Generate summary report
        this.generateSummaryReport(results);

        return results;
    }

    /**
     * V105.000: Generate summary report
     */
    generateSummaryReport(results) {
        log.section('V105.000 DIAGNOSTIC SUMMARY');

        console.log('\n┌─────────────────────────────────────────────────────────────────┐');
        console.log('│                    V105.000 DIAGNOSTIC REPORT                    │');
        console.log('├─────────────────────────────────────────────────────────────────┤');

        results.forEach((result, i) => {
            const status = result.success ? '✓ SUCCESS' : '✗ FAILED';
            const mode = result.headless ? 'HEADLESS' : 'HEADED';
            console.log(`│ Test ${i + 1}: ${mode.padEnd(10)} | ${status.padEnd(12)} | ${result.totalTime}ms │`);
            console.log(`│         HTTP: ${result.httpStatus} | Errors: ${result.errors.join(', ') || 'NONE'}`);
            console.log(`│         Title: "${result.pageTitle?.substring(0, 50) || 'N/A'}..."`);
            console.log('├─────────────────────────────────────────────────────────────────┤');
        });

        console.log('└─────────────────────────────────────────────────────────────────┘\n');

        // Recommendations
        log.section('V105.000 RECOMMENDATIONS');

        const successCount = results.filter(r => r.success).length;
        if (successCount === 0) {
            log.error('[CRITICAL] All tests failed - page is likely blocked');
            log.info('Recommendations:');
            log.info('  1. Try with proxy/VPN');
            log.info('  2. Implement longer delays between requests');
            log.info('  3. Use real browser cookies');
            log.info('  4. Check if OddsPortal requires JavaScript execution');
        } else {
            log.success(`[${successCount}/${results.length}] tests succeeded`);
            const successfulConfig = results.find(r => r.success);
            if (successfulConfig) {
                log.info(`Recommended config: headless=${successfulConfig.headless}, UA index=${CONFIG.userAgents.indexOf(successfulConfig.userAgent)}`);
            }
        }

        // Save report to file
        const reportPath = path.join(CONFIG.outputDir, `diagnostic_report_${Date.now()}.json`);
        fs.writeFileSync(reportPath, JSON.stringify(results, null, 2));
        log.info(`Full report saved: ${reportPath}`);
    }
}

// ============================================================================
// MAIN ENTRY POINT
// ============================================================================

async function main() {
    const probe = new DiagnosticProbe();

    try {
        const results = await probe.runFullDiagnostic();

        // Exit with appropriate code
        const anySuccess = results.some(r => r.success);
        process.exit(anySuccess ? 0 : 1);

    } catch (error) {
        log.error(`Fatal error: ${error.message}`);
        console.error(error.stack);
        process.exit(1);
    }
}

if (require.main === module) {
    main().catch(error => {
        console.error('[V105.000] Fatal error:', error);
        process.exit(1);
    });
}

module.exports = { DiagnosticProbe, main };
