/**
 * QuantHarvester - V164.TitanSlayer - V26.1 Brute Logic & Decryption
 * ================================================================
 */

'use strict';

const { chromium } = require('playwright');
const {
    createConnection,
    getOrCreateEntity,
    upsertTemporalRecords
} = require('../../scripts/ops/modules/storage');
const { TrajectoryParser } = require('./parsers/TrajectoryParser');
const { TelemetryService } = require('./services/TelemetryService');
const { SurgicalInteraction } = require('./services/SurgicalInteraction');
const { SignalRadar } = require('./services/SignalRadar');

// [V164.Sanitization] Load configuration from environment variables
const PROXY_HOST = process.env.WSL2_PROXY_HOST || '172.25.16.1';
const PROXY_PORT = process.env.DEFAULT_PROXY_PORT || '7892';
const DB_HOST = process.env.DB_HOST || '172.25.16.1';

const DEFAULT_CONFIG = {
    timeout: 60000,
    headless: true,
    axes: ['home', 'draw', 'away'],
    axisDimensions: { home: 'A', draw: 'B', away: 'C' },
    maxConcurrency: 1
};

class QuantHarvester {
    constructor(config = {}) {
        this.config = { ...DEFAULT_CONFIG, ...config };
        this.trajectoryParser = new TrajectoryParser();
        this.telemetryService = new TelemetryService(this.config);
        this.isInitialized = false;
        this.rawArteryBuffer = [];
        // [V164.Sanitization] Use env-based proxy URL
        this.proxyUrl = `http://${PROXY_HOST}:${PROXY_PORT}`;
    }

    async init() {
        if (this.isInitialized) return;
        this.dbClient = await createConnection();
        const browserOptions = {
            headless: this.config.headless,
            // [V164.Sanitization] Use env-based proxy configuration
            proxy: { server: this.proxyUrl },
            args: ['--no-sandbox', '--disable-setuid-sandbox']
        };
        this.browser = await chromium.launch(browserOptions);
        
        // [V164.Safety] Single Context per Initialization
        this.context = await this.browser.newContext({
            viewport: { width: 1920, height: 1080 },
            locale: 'en-GB',
            timezoneId: 'Europe/London',
            userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36'
        });

        this.page = await this.context.newPage();
        this.surgicalInteraction = new SurgicalInteraction(this.page, this.config);
        this.signalRadar = new SignalRadar(this.page, this.config);
        this.isInitialized = true;
    }

    /**
     * [V164.VaultBreaker] V26.1 Brute Force UI Interaction
     */
    async vaultBreaker() {
        console.log('[V164.VaultBreaker] 🔨 Initiating Brute Force UI Blast...');
        try {
            // 1. Keyword-based Button Smashing
            await this.page.evaluate(() => {
                const keywords = ['show all', 'more', 'comparison', 'all bookmakers', 'bookmakers'];
                const allElements = Array.from(document.querySelectorAll('a, button, span, li, div[role="tab"]'));
                
                allElements.forEach(el => {
                    const text = (el.innerText || '').toLowerCase();
                    if (keywords.some(kw => text.includes(kw))) {
                        if (el.offsetParent !== null) { // Visible
                            el.click();
                        }
                    }
                });
            });
            await this.page.waitForTimeout(2000);

            // 2. Turbo Scroll (Force React Hydration)
            console.log('[V164.VaultBreaker] 🚀 Turbo Scrolling...');
            await this.page.evaluate(async () => {
                const scrollStep = 500;
                const totalHeight = document.body.scrollHeight;
                for (let i = 0; i < totalHeight; i += scrollStep) {
                    window.scrollTo(0, i);
                    await new Promise(r => setTimeout(r, 100));
                }
                window.scrollTo(0, 0);
            });
            await this.page.waitForTimeout(2000);
        } catch (e) {
            console.log('[V164.VaultBreaker] Blast Warning:', e.message);
        }
    }

    async decompressInBrowser(rawData) {
        return await this.page.evaluate((raw) => {
            try {
                if (typeof window.JXG !== 'undefined' && JXG.decompress) {
                    return JXG.decompress(raw);
                }
                return null;
            } catch (e) { return null; }
        }, rawData);
    }

    async harvestMatch(url, sourceId) {
        if (!this.isInitialized) await this.init();
        const result = { sourceId, url, entityId: null, success: false, providerCount: 0, startTime: Date.now() };
        
        this.rawArteryBuffer = [];
        const responseHandler = async (resp) => {
            try {
                const u = resp.url();
                if (u.includes('.dat')) {
                    const text = await resp.text();
                    if (text.length > 100) {
                        this.rawArteryBuffer.push({ url: u, data: text });
                    }
                }
            } catch (e) {}
        };
        this.page.on('response', responseHandler);

        try {
            console.log(`[V164.Nav] Engaged: ${url}`);
            await this.page.goto(url, { timeout: this.config.timeout, waitUntil: 'networkidle' });
            
            // [V164.VaultBreaker] Restore V26.1 Logic
            await this.vaultBreaker();

            result.entityId = await getOrCreateEntity(this.dbClient, sourceId, url, 'match');
            const axesData = { home: [], draw: [], away: [] };
            const capturedTitans = new Set();

            console.log(`[V164.TitanSlayer] ⚔️  Decrypting ${this.rawArteryBuffer.length} triggered streams...`);
            for (const stream of this.rawArteryBuffer) {
                const decrypted = await this.decompressInBrowser(stream.data);
                if (decrypted) {
                    const arteryResults = this.parseArteryData(decrypted);
                    arteryResults.forEach(art => {
                        if (!axesData[art.axis]) axesData[art.axis] = [];
                        axesData[art.axis].push(art);
                        capturedTitans.add(art.standardVenueId);
                    });
                }
            }

            const records = [];
            Object.keys(axesData).forEach(axis => {
                axesData[axis].forEach(prov => {
                    prov.trajectory.forEach((pt, seq) => {
                        records.push({
                            provider_name: prov.standardVenueId,
                            metric_type: `quant_price_trajectory_${axis}`,
                            dimension: prov.dimension,
                            value: pt.value,
                            occurred_at: pt.time,
                            sequence: seq,
                            is_baseline: seq === 0,
                            raw_data: { axis, source: 'cipher_breaker', protocol: 'ghost_slayer' }
                        });
                    });
                });
            });

            if (records.length > 0) {
                await upsertTemporalRecords(this.dbClient, result.entityId, records);
                result.success = true;
                result.providerCount = capturedTitans.size;
                console.log(`[V164.TitanSlayer] ✅ Slain: [${Array.from(capturedTitans).join(', ')}]`);
            }

            // [V164.Safety] Memory Guard
            await this.context.clearCookies();
            console.log('[V164.Safety] Context cleared.');

        } catch (e) { result.error = e.message; }
        
        this.page.removeListener('response', responseHandler);
        return result;
    }

    parseArteryData(decryptedData) {
        const results = [];
        try {
            const json = typeof decryptedData === 'string' ? JSON.parse(decryptedData) : decryptedData;
            const data = json.d || json;
            const TITAN_ID_MAP = { '18': 'Entity_P', '32': 'Entity_WH', '2': 'Entity_B365', '25679340': 'Entity_1XBT' };
            const AXIS_MAP = { '1': 'home', '2': 'draw', '3': 'away' };

            const find = (obj) => {
                if (!obj || typeof obj !== 'object') return;
                for (const k of Object.keys(obj)) {
                    if (TITAN_ID_MAP[k]) {
                        const titanId = TITAN_ID_MAP[k];
                        const node = obj[k];
                        Object.keys(node).forEach(typeId => {
                            const axis = AXIS_MAP[typeId];
                            if (!axis) return;
                            const pts = Array.isArray(node[typeId]) ? node[typeId] : Object.values(node[typeId]);
                            const trajectory = pts.filter(p => p.t && p.v).map(p => ({
                                time: new Date(p.t * 1000).toISOString(),
                                value: p.v
                            }));
                            if (trajectory.length > 0) {
                                results.push({ axis, dimension: axis === 'home' ? 'A' : axis === 'draw' ? 'B' : 'C', standardVenueId: titanId, trajectory });
                            }
                        });
                    } else find(obj[k]);
                }
            };
            find(data);
        } catch (e) {}
        return results;
    }

    async shutdown() {
        if (this.page) await this.page.close();
        if (this.context) await this.context.close();
        if (this.browser) await this.browser.close();
        if (this.dbClient) await this.dbClient.end();
    }
}

module.exports = { QuantHarvester };
