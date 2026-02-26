/**
 * V104.000 Configuration Module - Stealth Mode & Page Verification
 * ================================================================
 *
 * V104.000: Professional-grade stealth mode for detail page extraction
 *   - Stealth Mode: ignoreDefaultArgs + Real Chrome User Agent
 *   - Page Content Verification: Access Denied detection + force refresh
 *   - Precision Click Anchor: (0,0) click before tab activation
 *   - Single URL validation for high-fidelity extraction
 *
 * @version V104.000
 * @since 2026-01-26
 */

'use strict';

const path = require('path');

// V172: 使用统一数据库配置
const { DatabaseConfig } = require(path.resolve(__dirname, '../../config/database'));

// ============================================================================
// V104.000 CONFIGURATION
// ============================================================================

const CONFIG = {
    version: 'V104.000',  // Stealth Mode + Page Verification + Precision Click

    // V104.000: Single URL validation test - High precision extraction
    targetUrls: [
        // V104.000: Known valid detail page URL for validation
        process.env.TARGET_URL_1 || 'https://www.oddsportal.com/football/england/premier-league/everton-arsenal-83299048/'
    ],

    // V104.000: SINGLE URL HIGH-PRECISION MODE - Force MAX_CONCURRENT=1
    concurrency: {
        maxConcurrent: 1,  // V104.000: FORCED to 1 for high-precision validation
        browserPoolSize: 1,
        pageTimeout: 45000   // V104.000: 45s timeout for detail page loading
    },

    // V104.000: Stealth Mode Browser Configuration
    // Bypass OddsPortal Playwright detection with professional-grade stealth
    browser: {
        headless: true,
        viewport: { width: 1280, height: 800 },
        // V104.000: Stealth args - hide automation indicators
        args: [
            '--disable-blink-features=AutomationControlled',
            '--disable-dev-shm-usage',
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-web-security',
            '--disable-features=IsolateOrigins,site-per-process'
        ],
        // V104.000: Real Chrome User Agent string (Windows 10 + Chrome 131)
        userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        // V104.000: Ignore default args to remove automation flags
        ignoreDefaultArgs: ['--enable-automation']
    },

    // Database configuration - V172: 使用统一配置
    database: {
        host: DatabaseConfig.host,
        port: DatabaseConfig.port,
        database: DatabaseConfig.database,
        user: DatabaseConfig.user,
        password: DatabaseConfig.password,
        pool: {
            min: 2,
            max: 20,
            idleTimeoutMillis: 30000
        }
    },

    // Extraction parameters
    extraction: {
        minNumericValue: 1.01,
        maxNumericValue: 1000,
        targetFieldCount: 5,
        minPointsRequired: 10,
        timePattern: /\d{1,2}:\d{2}/,
        minFloatCountRequired: 1,
        debugSampleSize: 1000,
        decimalPatterns: [/\d+\.\d+/, /\d+,\d+/],
        maxParentDepth: 3,
        targetYieldPerPage: 15,
        temporalPointPreviewSize: 100,
        zIndexCrushThreshold: 1000,
        structureSampleDepth: 3,
        structureSampleMaxNodes: 100
    },

    // V100.000: Vendor Identity Mapping (Type_B/P/U/W/X/S series)
    vendorMap: [
        { name: 'Type_P', aliases: ['pinnacle', 'pinny', 'pinnacle sports', 'ps3838'], hexColor: '#009933' },
        { name: 'Type_B', aliases: ['bet365', 'b365', '365', 'bet 365'], hexColor: '#007700' },
        { name: 'Type_W', aliases: ['bwin', 'b win', 'william hill', 'willhill', 'wh'], hexColor: '#003399' },
        { name: 'Type_X', aliases: ['1xbet', '1x', '1 xbet'], hexColor: '#EB5E28' },
        { name: 'Type_U', aliases: ['unibet', 'uni'], hexColor: '#FF6600' },
        { name: 'Type_S', aliases: ['betfair', 'sporting', 'bet fair', 'bf'], hexColor: '#FFFF00' }
    ],

    // V100.000: Enhanced vendor signatures with text, alt, src, and title patterns
    vendorSignatures: {
        'Type_B': {
            text: ['b365', '365', 'bet365'],
            imgAlt: ['bet365', 'b365 logo'],
            imgSrc: ['bet365', 'b365'],
            title: ['Bet365', 'bet 365']
        },
        'Type_P': {
            text: ['pinna', 'pinnacle', 'ps3838'],
            imgAlt: ['pinnacle', 'pinny'],
            imgSrc: ['pinnacle', 'ps3838'],
            title: ['Pinnacle', 'Pinny']
        },
        'Type_U': {
            text: ['uni', 'unibet'],
            imgAlt: ['unibet', 'uni'],
            imgSrc: ['unibet'],
            title: ['Unibet']
        },
        'Type_W': {
            text: ['bwin', 'william', 'hill', 'wh'],
            imgAlt: ['bwin', 'william hill', 'willhill'],
            imgSrc: ['bwin', 'williamhill', 'wh'],
            title: ['Bwin', 'William Hill']
        },
        'Type_X': {
            text: ['1x', 'xbet', '1xbet'],
            imgAlt: ['1xbet', '1x'],
            imgSrc: ['1xbet', '1x'],
            title: ['1xBet', '1X']
        },
        'Type_S': {
            text: ['betfair', 'sporting', 'bet fair'],
            imgAlt: ['betfair', 'sporting', 'bf'],
            imgSrc: ['betfair', 'sporting', 'bf'],
            title: ['Betfair', 'Sporting']
        }
    },

    // V103.000: ENHANCED RADAR SELECTORS - Attribute matching + text-based click
    // Detail pages have different structure than league pages
    detailPageSelectors: [
        'div#odds-data-table',           // V103.000: Primary odds data table
        '[data-id="odds-table"]',         // V103.000: Data attribute selector
        'table#odds-table',               // V103.000: Table with odds data
        'div[class*="odds-table"]',       // V103.000: Any odds-table variant
        'div[data-tab="odds"]',           // V103.000: Tab-based odds container
        'div[class*="betting-odds"]',     // V103.000: Betting odds container
        'table.betting-table',            // V103.000: Betting table
        'div[class*="odd-history"]',      // V103.000: Odds history container
        // V103.000: RADAR selectors - attribute contains matching
        'div[class*="odds"]',             // V103.000: Any div with "odds" in class
        'table[class*="odds"]',           // V103.000: Any table with "odds" in class
        '[data-testid*="odds"]',          // V103.000: Any element with "odds" in testid
        'section[class*="odds"]',         // V103.000: Section with odds
        'div[id*="odds"]',                // V103.000: Any div with "odds" in id
        '[data-component*="odds"]'        // V103.000: Component-based odds
    ],

    // V103.000: Text-based click selectors for "Odds" tab
    oddsTabTextSelectors: [
        'text="Odds"',
        'text="1X2"',
        'text="Full Time"',
        'text="Full time"',
        'text="Home/Draw/Away"'
    ],

    // V103.000: Tab activation selectors for detail pages
    // Need to ensure "Full time" or "1X2" tab is active
    tabActivationSelectors: [
        '[data-tab="1x2"]',
        '[data-tab="full-time"]',
        'a[href*="1x2"]',
        'a[href*="full-time"]',
        'button[data-tab="1x2"]',
        'button[data-tab="full-time"]',
        'div[class*="tab-1x2"]',
        'div[class*="tab-full-time"]'
    ],

    // Original league page selectors (fallback)
    leaguePageSelectors: [
        'div.border-black-borders',
        'div[class*="border-black"]',
        'div[class*="tournament"]',
        'div[class*="event"]',
        'div[data-testid="event-name"]',
        'table[class*="table"]',
        'div.main-content',
        'div#tournamentTable'
    ],

    // Privacy wall keywords
    obstacleKeywords: [
        'Privacy', 'Cookie', 'Partners', 'Consent', 'Agree', 'Accept',
        'privacy', 'cookie', 'consent', 'agree', 'accept',
        'PRIVACY', 'COOKIE', 'CONSENT', 'AGREE', 'ACCEPT'
    ],

    // Modal attributes to target
    modalAttributes: ['aria-modal', 'role', 'class'],
    modalClassPrefixes: ['cmp-', 'consent-', 'cookie-', 'privacy-'],

    // V91.000: Anchor selectors for DOM stabilization
    anchorSelectors: [
        '.border-black-borders',
        '.border-black-borders *',
        '[class*="border"]',
        '[class*="modal"]',
        '[class*="popup"]',
        '[class*="overlay"]'
    ],

    // Precision clicking offsets
    clickOffset: {
        x: 0,
        y: -5
    },

    // Logging configuration
    logDir: path.join(__dirname, '../../logs/debug'),
    dumpOnFailure: true,
    debug: true
};

// ============================================================================
// LOGGING - V104.000
// ============================================================================

const log = {
    info: (msg) => console.log(`[V104.000] [INFO] ${msg}`),
    success: (msg) => console.log(`[V104.000] [SUCCESS] ${msg}`),
    warn: (msg) => console.warn(`[V104.000] [WARN] ${msg}`),
    error: (msg) => console.error(`[V104.000] [ERROR] ${msg}`),
    debug: (msg) => CONFIG.debug ? console.log(`[V104.000] [DEBUG] ${msg}`) : null
};

module.exports = {
    CONFIG,
    log
};
