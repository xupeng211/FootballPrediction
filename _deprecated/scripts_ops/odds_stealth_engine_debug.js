#!/usr/bin/env node
/**
 * [Genesis.Diagnostic] V1.0 - Debug L3 Odds Extraction Engine
 * ===============================================================
 *
 * 诊断模式增强功能：
 *   1. 保存页面源码到 logs/debug_source_<match_id>.html
 *   2. 截图保存到 logs/debug_screenshot_<match_id>.png
 *   3. 打印所有网络请求状态码
 *   4. 详细诊断日志
 *
 * Usage:
 *   node odds_stealth_engine_debug.js "<TARGET_URL>" "<MATCH_ID>" [--proxy <PROXY_URL>]
 *
 * @module odds_stealth_engine_debug
 * @author Genesis.DiagnosticTeam
 * @version V1.0
 * @since 2026-02-01
 */

'use strict';

const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

// ============================================================================
// UA 指纹池 (30+ 真实浏览器)
// ============================================================================

const UA_POOL = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 11.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
];

function getRandomUA() {
    return UA_POOL[Math.floor(Math.random() * UA_POOL.length)];
}

// ============================================================================
// DEBUG CONFIGURATION
// ============================================================================

const CONFIG = {
    headless: false,  // Debug mode: show browser
    timeout: 60000,
    proxyServer: null,
    debug: true,  // Always true for diagnostic version
    saveSource: true,
    saveScreenshot: true,
    logNetwork: true
};

// ============================================================================
// STATE
// ============================================================================

let currentBrowser = null;
let currentContext = null;
let currentPage = null;
let networkRequests = [];

const stats = {
    url: '',
    matchId: '',
    startTime: null,
    endTime: null,
    success: false,
    networkRequests: [],
    errors: []
};

// ============================================================================
// LOGGING
// ============================================================================

function log(msg) {
    const timestamp = new Date().toISOString().substring(11, 19);
    console.log(`[${timestamp}] ${msg}`);
}

function logError(error) {
    const errorInfo = {
        timestamp: new Date().toISOString(),
        message: error.message || String(error),
        type: error.name || 'Unknown'
    };
    stats.errors.push(errorInfo);
    console.error(`[ERROR] ${errorInfo.type}: ${errorInfo.message}`);
}

// ============================================================================
// DEBUG: Save Page Source
// ============================================================================

async function savePageSource() {
    try {
        const logsDir = path.join(process.cwd(), 'logs');
        if (!fs.existsSync(logsDir)) {
            fs.mkdirSync(logsDir, { recursive: true });
        }

        const filename = path.join(logsDir, `debug_source_${stats.matchId}.html`);
        const content = await currentPage.content();

        fs.writeFileSync(filename, content, 'utf8');
        log(`[DEBUG] Page source saved to: ${filename}`);

        // Check for common indicators
        const contentLower = content.toLowerCase();

        const indicators = {
            '403 Forbidden': contentLower.includes('403') || contentLower.includes('forbidden'),
            'Access Denied': contentLower.includes('access denied'),
            'Cloudflare': contentLower.includes('cloudflare') || contentLower.includes('cf-browser-verification'),
            'Akamai': contentLower.includes('akamai'),
            'CAPTCHA': contentLower.includes('captcha') || contentLower.includes('challenge platform'),
            'Rate Limit': contentLower.includes('rate limit') || contentLower.includes('too many requests'),
            'OddsPortal': contentLower.includes('oddsportal'),
            'Table element': contentLower.includes('<table'),
            'Odds data': contentLower.includes('odds') || contentLower.includes('betting')
        };

        log('[DEBUG] Page content analysis:');
        for (const [indicator, found] of Object.entries(indicators)) {
            log(`  ${found ? '✓' : '✗'} ${indicator}`);
        }

        // Check title
        const title = await currentPage.title();
        log(`[DEBUG] Page title: "${title}"`);

        // Check URL
        const currentUrl = currentPage.url();
        log(`[DEBUG] Current URL: ${currentUrl}`);

        return filename;

    } catch (error) {
        logError(error);
        return null;
    }
}

// ============================================================================
// DEBUG: Save Screenshot
// ============================================================================

async function saveScreenshot() {
    try {
        const logsDir = path.join(process.cwd(), 'logs');
        if (!fs.existsSync(logsDir)) {
            fs.mkdirSync(logsDir, { recursive: true });
        }

        const filename = path.join(logsDir, `debug_screenshot_${stats.matchId}.png`);
        await currentPage.screenshot({ path: filename, fullPage: true });

        log(`[DEBUG] Screenshot saved to: ${filename}`);
        return filename;

    } catch (error) {
        logError(error);
        return null;
    }
}

// ============================================================================
// DEBUG: Network Monitoring
// ============================================================================

function setupNetworkMonitoring() {
    // Log all network requests
    currentPage.on('request', request => {
        const url = request.url();
        const method = request.method();
        const resourceType = request.resourceType();

        const reqInfo = {
            timestamp: new Date().toISOString(),
            method,
            url: url.substring(0, 100),
            resourceType,
            status: 'pending'
        };

        stats.networkRequests.push(reqInfo);

        if (CONFIG.logNetwork && (resourceType === 'document' || resourceType === 'xhr' || resourceType === 'fetch')) {
            log(`[NETWORK] → ${method} ${url.substring(0, 80)}... [${resourceType}]`);
        }
    });

    currentPage.on('response', response => {
        const url = response.url();
        const status = response.status();
        const method = request => request ? request.method() : 'N/A';

        const reqInfo = stats.networkRequests.find(r => r.url === url.substring(0, 100));
        if (reqInfo) {
            reqInfo.status = status;
        }

        if (CONFIG.logNetwork) {
            const statusIcon = status >= 200 && status < 300 ? '✓' : (status >= 400 ? '✗' : '•');
            log(`[NETWORK] ${statusIcon} ${status} ${method(response.request())} ${url.substring(0, 60)}...`);
        }
    });

    currentPage.on('requestfailed', request => {
        const failure = request.failure();
        const url = request.url();

        log(`[NETWORK] ✗ FAILED ${url.substring(0, 60)}... (${failure ? failure.errorText : 'unknown'})`);
    });
}

// ============================================================================
// BROWSER LAUNCH
// ============================================================================

async function launchBrowser() {
    stats.attempts = (stats.attempts || 0) + 1;

    try {
        log('[STEALTH] Launching browser (DEBUG MODE)...');

        const launchArgs = [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-blink-features=AutomationControlled',
            '--disable-web-security',
            '--disable-features=VizDisplayCompositor'
        ];

        if (CONFIG.proxyServer) {
            launchArgs.push(`--proxy-server=${CONFIG.proxyServer}`);
            log(`[PROXY] Using: ${CONFIG.proxyServer}`);
        }

        currentBrowser = await chromium.launch({
            headless: CONFIG.headless,
            args: launchArgs,
        });

        const viewports = [
            { width: 1920, height: 1080 },
            { width: 1680, height: 1050 },
        ];
        const viewport = viewports[Math.floor(Math.random() * viewports.length)];
        const ua = getRandomUA();

        const contextOptions = {
            viewport: viewport,
            userAgent: ua,
            locale: 'en-US',
            timezoneId: 'America/New_York',
            permissions: ['geolocation']
        };

        if (CONFIG.proxyServer) {
            contextOptions.proxy = { server: CONFIG.proxyServer };
        }

        currentContext = await currentBrowser.newContext(contextOptions);
        currentPage = await currentContext.newPage();
        currentPage.setDefaultTimeout(CONFIG.timeout);

        // Anti-detection
        await currentPage.addInitScript(() => {
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
            Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
            window.chrome = { runtime: {} };

            // Block WebRTC
            const originalRTCPeerConnection = window.RTCPeerConnection || window.webkitRTCPeerConnection;
            if (originalRTCPeerConnection) {
                window.RTCPeerConnection = function(...args) {
                    throw new Error('WebRTC blocked');
                };
            }
        });

        // Setup network monitoring
        setupNetworkMonitoring();

        log(`[STEALTH] UA: ${ua.substring(0, 60)}...`);
        log(`[STEALTH] Viewport: ${viewport.width}x${viewport.height}`);

        return true;

    } catch (error) {
        logError(error);
        return false;
    }
}

// ============================================================================
// NAVIGATION
// ============================================================================

async function navigateToUrl(url) {
    try {
        log(`[NAV] Navigating to: ${url.substring(0, 80)}...`);

        await currentPage.goto(url, {
            waitUntil: 'networkidle',
            timeout: CONFIG.timeout
        });

        // Wait for page to stabilize
        await currentPage.waitForTimeout(3000);

        // Check for blocked pages
        const pageContent = await currentPage.content();
        const blockedPatterns = ['access denied', '403 forbidden', 'rate limit', 'blocked'];
        const isPageBlocked = blockedPatterns.some(p => pageContent.toLowerCase().includes(p));

        if (isPageBlocked) {
            log('[NAV] ⛔ PAGE APPEARS TO BE BLOCKED');
        }

        return true;

    } catch (error) {
        logError(error);
        return false;
    }
}

// ============================================================================
// DIAGNOSTIC EXTRACTION
// ============================================================================

async function extractOddsData() {
    try {
        log('[EXTRACT] Waiting for page stabilization...');
        await currentPage.waitForTimeout(3000);

        // DEBUG: Save page source and screenshot
        if (CONFIG.saveSource) {
            await savePageSource();
        }
        if (CONFIG.saveScreenshot) {
            await saveScreenshot();
        }

        // Analyze page structure
        const pageContent = await currentPage.content();

        // Check for various indicators
        const checks = {
            'Has <body>': pageContent.includes('<body'),
            'Has <table>': pageContent.includes('<table'),
            'Has "odds"': pageContent.toLowerCase().includes('odds'),
            'Has "betting"': pageContent.toLowerCase().includes('betting'),
            'Has "1x2" or "h2h"': pageContent.toLowerCase().includes('1x2') || pageContent.toLowerCase().includes('h2h'),
            'Has decimal odds': /\d+\.\d+/.test(pageContent),
        };

        log('[EXTRACT] Page structure check:');
        for (const [check, passed] of Object.entries(checks)) {
            log(`  ${passed ? '✓' : '✗'} ${check}`);
        }

        // Try to find common selectors
        const selectors = [
            '#oddsData',
            '.odds-container',
            '[data-odds]',
            'table',
            '.table-main',
            '.odds-table',
            '[class*="odds"]',
            '[id*="odds"]'
        ];

        log('[EXTRACT] Checking for common selectors:');
        for (const selector of selectors) {
            try {
                const element = await currentPage.$(selector);
                if (element) {
                    log(`  ✓ Found: ${selector}`);
                } else {
                    log(`  ✗ Not found: ${selector}`);
                }
            } catch (e) {
                log(`  ✗ Error checking ${selector}: ${e.message}`);
            }
        }

        // Sample page text
        const bodyText = await currentPage.evaluate(() => {
            return document.body ? document.body.innerText.substring(0, 500) : '';
        });

        log('[EXTRACT] Page text sample (first 500 chars):');
        log('  ' + bodyText.substring(0, 200).replace(/\n/g, ' '));
        log('  ...');

        // Try to extract any odds-like patterns
        const oddsPattern = /\d+\.\d{2,}/g;
        const odds = pageContent.match(oddsPattern);

        if (odds && odds.length > 0) {
            log(`[EXTRACT] Found ${odds.length} potential odds values`);
            log(`[EXTRACT] Sample odds: ${odds.slice(0, 10).join(', ')}`);

            return {
                success: true,
                matchId: stats.matchId,
                timestamp: new Date().toISOString(),
                rawData: {
                    oddsCount: odds.length,
                    sampleOdds: odds.slice(0, 20)
                }
            };
        }

        log('[EXTRACT] No odds patterns found');
        return { success: false, error: 'NO_ODDS_FOUND', pageAnalysis: checks };

    } catch (error) {
        logError(error);
        return { success: false, error: error.message };
    }
}

// ============================================================================
// CLEANUP
// ============================================================================

async function cleanup() {
    try {
        if (currentPage) {
            await currentPage.close();
            currentPage = null;
        }
        if (currentContext) {
            await currentContext.close();
            currentContext = null;
        }
        if (currentBrowser) {
            await currentBrowser.close();
            currentBrowser = null;
        }
    } catch (error) {
        console.error('[CLEANUP] Error:', error.message);
    }
}

// ============================================================================
// DIAGNOSTIC REPORT
// ============================================================================

function printDiagnosticReport() {
    log('');
    log('=' .repeat(60));
    log('[DIAGNOSTIC REPORT]');
    log('=' .repeat(60));
    log(`Match ID: ${stats.matchId}`);
    log(`URL: ${stats.url}`);
    log(`Duration: ${stats.endTime ? ((stats.endTime - stats.startTime) / 1000).toFixed(1) : 'N/A'}s`);
    log(`Success: ${stats.success}`);
    log(``);
    log(`Network Requests: ${stats.networkRequests.length}`);
    log(`Errors: ${stats.errors.length}`);

    if (stats.networkRequests.length > 0) {
        log('');
        log('[Network Status Summary]:');
        const statusGroups = {};
        for (const req of stats.networkRequests) {
            const status = req.status || 'unknown';
            statusGroups[status] = (statusGroups[status] || 0) + 1;
        }
        for (const [status, count] of Object.entries(statusGroups)) {
            log(`  ${status}: ${count} requests`);
        }
    }

    if (stats.errors.length > 0) {
        log('');
        log('[Errors]:');
        for (const err of stats.errors) {
            log(`  ${err.type}: ${err.message}`);
        }
    }

    log('=' .repeat(60));
}

// ============================================================================
// MAIN
// ============================================================================

async function main() {
    const args = process.argv.slice(2);

    let targetUrl = null;
    let matchId = null;
    let proxyServer = null;

    for (let i = 0; i < args.length; i++) {
        if (args[i] === '--proxy' && i + 1 < args.length) {
            proxyServer = args[++i];
        } else if (!targetUrl) {
            targetUrl = args[i];
        } else if (!matchId) {
            matchId = args[i];
        }
    }

    if (!targetUrl || !matchId) {
        console.error('Usage: node odds_stealth_engine_debug.js "<TARGET_URL>" "<MATCH_ID>" [--proxy <PROXY_URL>]');
        process.exit(1);
    }

    CONFIG.proxyServer = proxyServer;

    stats.url = targetUrl;
    stats.matchId = matchId;
    stats.startTime = new Date();

    log('=' .repeat(60));
    log('[Genesis.Diagnostic] V1.0 - DEBUG MODE');
    log('=' .repeat(60));
    log(`Target: ${matchId}`);
    log(`URL: ${targetUrl.substring(0, 60)}...`);
    log(`Debug: ${CONFIG.debug}`);
    log(`Save Source: ${CONFIG.saveSource}`);
    log(`Save Screenshot: ${CONFIG.saveScreenshot}`);
    log(`Log Network: ${CONFIG.logNetwork}`);
    if (proxyServer) {
        log(`Proxy: ${proxyServer}`);
    }
    log('=' .repeat(60));

    try {
        // 1. Launch browser
        if (!await launchBrowser()) {
            throw new Error('Failed to launch browser');
        }

        // 2. Navigate
        if (!await navigateToUrl(targetUrl)) {
            throw new Error('Navigation failed');
        }

        // 3. Extract with diagnostics
        const result = await extractOddsData();

        stats.success = result.success;
        stats.endTime = new Date();

        // 4. Print diagnostic report
        printDiagnosticReport();

        if (result.success) {
            log('');
            log('[SUCCESS] Extraction completed');
            log(`  Odds found: ${result.rawData.oddsCount}`);
            process.exit(0);
        } else {
            log('');
            log('[FAILED] Extraction failed');
            log(`  Error: ${result.error}`);
            process.exit(1);
        }

    } catch (error) {
        stats.success = false;
        stats.endTime = new Date();
        logError(error);
        printDiagnosticReport();
        process.exit(1);

    } finally {
        await cleanup();
    }
}

// Run
if (require.main === module) {
    main().catch(error => {
        console.error('[FATAL]', error);
        process.exit(1);
    });
}

module.exports = { getRandomUA };
