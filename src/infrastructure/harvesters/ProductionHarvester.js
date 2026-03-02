/**
 * ProductionHarvester - V177 生产级收割引擎
 * ====================================
 *
 * 从 scripts/ops/run_production_harvest.js 提取核心业务逻辑
 * 封装为可复用的收割器类
 *
 * V177 升级:
 * - Ghost Protocol 隐身衣 (30+ UA 池 + Referer 伪装)
 * - Sec-Ch-Ua 浏览器指纹完整伪装
 *
 * @module infrastructure/harvesters/ProductionHarvester
 * @version V177.0.0
 */

'use strict';

const pLimit = require('p-limit');
const { chromium } = require('playwright');
const { Pool } = require('pg');
const path = require('path');

// 导入核心组件
const { BrowserManager } = require('../../core/browser/BrowserManager');
const { preFlightCleanup } = require('../../core/process/ZombieKiller');
const { transformToApiFormat } = require('../../parsers/fotmob/NextDataParser');

// 导入配置
const FactoryConfig = require('../../../config/factory_config');
const { DatabaseConfig } = require('../database/PostgresClient');

// ============================================================================
// V177: Ghost Protocol - 30+ 浏览器指纹池
// ============================================================================

const GHOST_UA_POOL = [
    // Chrome 桌面端 (Windows)
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36',
    // Chrome 桌面端 (macOS)
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    // Edge 桌面端
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36 Edg/133.0.0.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36 Edg/132.0.0.0',
    // Firefox 桌面端
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:135.0) Gecko/20100101 Firefox/135.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:134.0) Gecko/20100101 Firefox/134.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:135.0) Gecko/20100101 Firefox/135.0',
    // Safari 桌面端 (macOS)
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15'
];

const GHOST_VIEWPORTS = [
    { width: 1920, height: 1080 },
    { width: 1366, height: 768 },
    { width: 1440, height: 900 },
    { width: 1536, height: 864 },
    { width: 1280, height: 720 },
    { width: 1600, height: 900 },
    { width: 2560, height: 1440 },
    { width: 1287, height: 1271 }
];

/**
 * 获取随机 UA
 */
function getRandomUA() {
    return GHOST_UA_POOL[Math.floor(Math.random() * GHOST_UA_POOL.length)];
}

/**
 * 获取随机视口
 */
function getRandomViewport() {
    return GHOST_VIEWPORTS[Math.floor(Math.random() * GHOST_VIEWPORTS.length)];
}

/**
 * V177: 生成完整的隐身 Headers
 */
function generateStealthHeaders() {
    const ua = getRandomUA();
    const viewport = getRandomViewport();
    const isChrome = ua.includes('Chrome') && !ua.includes('Edg');
    const isFirefox = ua.includes('Firefox');
    const isEdge = ua.includes('Edg');

    let secChUa = '';
    if (isChrome) {
        secChUa = '"Chromium";v="133", "Google Chrome";v="133", "Not-A.Brand";v="99"';
    } else if (isEdge) {
        secChUa = '"Chromium";v="133", "Microsoft Edge";v="133", "Not-A.Brand";v="99"';
    }

    return {
        userAgent: ua,
        viewport,
        extraHTTPHeaders: isChrome || isEdge ? {
            'sec-ch-ua': secChUa,
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': ua.includes('Windows') ? '"Windows"' : '"macOS"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'none',
            'sec-fetch-user': '?1',
            'accept-language': 'en-US,en;q=0.9',
            'accept-encoding': 'gzip, deflate, br'
        } : {}
    };
}

// ============================================================================
// ProductionHarvester 类
// ============================================================================

class ProductionHarvester {
    constructor(config = {}) {
        this.config = {
            maxWorkers: parseInt(process.env.MAX_WORKERS) || config.maxWorkers || 2,
            minDelayMs: parseInt(process.env.MIN_DELAY_MS) || config.minDelayMs || 5000,
            maxDelayMs: parseInt(process.env.MAX_DELAY_MS) || config.maxDelayMs || 10000,
            batchSize: parseInt(process.env.BATCH_SIZE) || config.batchSize || 500,
            leagueFilter: config.leagueFilter || process.env.LEAGUE_FILTER || null,
            dryRun: config.dryRun || false,
            ...config
        };

        this.pool = null;
        this.browser = null;
        this.stats = {
                total: 0,
                processed: 0,
                success: 0,
                failed: 0
            };
        this.startTime = null;
    }

    // ========================================================================
    // 生命周期方法
    // ========================================================================

    async init() {
        console.log('🚀 初始化 ProductionHarvester...');

        // 数据库连接池
        this.pool = new Pool({
            host: DatabaseConfig.host,
            port: DatabaseConfig.port,
            database: DatabaseConfig.database,
            user: DatabaseConfig.user,
            password: DatabaseConfig.password,
            max: 20,
            idleTimeoutMillis: 30000
        });

        // 测试连接
        const client = await this.pool.connect();
        await client.query('SELECT 1');
        client.release();
        console.log('✅ 数据库连接池已就绪');

        // 清理僵尸进程
        await preFlightCleanup();

        // 启动浏览器
        this.browser = await chromium.launch({
            headless: true,
            args: [
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-blink-features=AutomationControlled',
                '--disable-gpu'
            ]
        });
        console.log('✅ 浏览器已启动');

        console.log(`📋 配置: MAX_WORKERS=${this.config.maxWorkers}, | DELAY=${this.config.minDelayMs}-${this.config.maxDelayMs}ms`);
    }

    /**
     * 获取待收割的比赛列表
     */
    async getPendingMatches() {
        const query = `
            SELECT
                m.match_id,
                m.external_id,
                m.home_team,
                m.away_team,
                m.match_date
            FROM matches m
            LEFT JOIN raw_match_data r ON m.match_id = r.match_id
            WHERE r.match_id IS NULL
            ORDER BY m.match_date DESC
            LIMIT $1
        `;

        const result = await this.pool.query(query, [this.config.batchSize || 500]);
        return result.rows;
    }

    /**
     * 执行收割
     */
    async run() {
        this.startTime = Date.now();

        console.log('═══════════════════════════════════════════════════════════════');
        console.log('  V176 Production Harvester - 开始收割');
        console.log('═══════════════════════════════════════════════════════════════');

        const matches = await this.getPendingMatches();
        this.stats.total = matches.length;

        console.log(`📋 待收割比赛: ${matches.length} 场`);

        if (matches.length === 0) {
            console.log('🎉 没有待收割的比赛');
            return;
        }

        if (this.config.dryRun) {
            console.log('⚠️ DRY RUN 模式 - 不会写入数据库');
        }

        // 并发收割
        const limit = pLimit(this.config.maxWorkers);

        const tasks = matches.map(match => limit(async () => {
            try {
                const result = await this.harvestMatch(match);
                return result;
            } catch (error) {
                return { success: false, error: error.message };
            }
        }));

        const results = await Promise.all(tasks);

        // 统计
        for (const result of results) {
            this.stats.processed++;
            if (result.success) {
                this.stats.success++;
            } else {
                this.stats.failed++;
            }
        }

        // 报告
        this.printReport();

        return results;
    }

    /**
     * 单场比赛收割
     */
    async harvestMatch(match) {
        const { match_id, external_id, home_team, away_team } = match;

        const startTime = Date.now();

        // 随机延迟
        const delay = this.config.minDelayMs +
            Math.random() * (this.config.maxDelayMs - this.config.minDelayMs);
        await new Promise(r => setTimeout(r, delay));

        // 获取代理端口
        const workerId = (this.stats.processed % this.config.maxWorkers) + 1;
        const proxyPort = FactoryConfig.PROXY_CONFIG.getPortByWorker(workerId);
        const proxyServer = FactoryConfig.PROXY_CONFIG.getServer(proxyPort);

        // V177: Ghost Protocol - 每次请求生成新的隐身指纹
        const stealth = generateStealthHeaders();

        // 创建浏览器上下文 (使用隐身衣)
        const context = await this.browser.newContext({
            viewport: stealth.viewport,
            userAgent: stealth.userAgent,
            extraHTTPHeaders: stealth.extraHTTPHeaders,
            proxy: {
                server: proxyServer
            }
        });

        const page = await context.newPage();

        try {
            // 构建目标 URL
            const matchUrl = `https://www.fotmob.com/match/${external_id}`;
            console.log(`🌐 渗透: ${home_team} vs ${away_team}`);

            // 设置请求拦截
            let capturedData = null;
            await page.route('**/*', async (route) => {
                const url = route.request().url();
                const type = route.request().resourceType();

                // 屏蔽非必要资源
                if (['image', 'media', 'font'].includes(type)) {
                    await route.abort();
                    return;
                }

                // 捕获目标 API
                if (url.includes('matchfacts') || url.includes('matchDetails')) {
                    try {
                        const response = await route.fetch();
                        const body = await response.text();
                        try {
                            capturedData = JSON.parse(body);
                            console.log(`📡 拦截 API: ${url.slice(0, 60)}...`);
                        } catch (e) {}
                        await route.fulfill({ response });
                    } catch (e) {
                        await route.continue();
                    }
                } else {
                    await route.continue();
                }
            });

            // 导航到比赛页面
            await page.goto(matchUrl, {
                waitUntil: 'domcontentloaded',
                timeout: 60000
            });

            // 等待数据
            await page.waitForTimeout(5000);

            // 如果拦截失败，使用 NextDataParser
            if (!capturedData) {
                // 使用 NextDataParser
                const nextData = await page.evaluate(() => {
                    const script = document.getElementById('__NEXT_DATA__');
                    return script ? JSON.parse(script.textContent) : null;
                });
                capturedData = transformToApiFormat(nextData);
                console.log(`📄 使用 __NEXT_DATA__ 解析`);
            }

            // 验证数据
            if (!capturedData) {
                throw new Error('NO_DATA:无法获取数据');
            }

            const size = JSON.stringify(capturedData).length;
            if (size < 1000) {
                throw new Error(`SIZE_TOO_SMALL:${size}`);
            }

            // DRY RUN 模式
            if (this.config.dryRun) {
                console.log(`✅ ${home_team} vs ${away_team} | ${size} bytes | DRY RUN`);
                return { success: true, match_id, size };
            }

            // 写入数据库
            await this.saveRawData(match_id, capturedData);
            console.log(`✅ ${home_team} vs ${away_team} | ${size} bytes | 完成`);

            return { success: true, match_id, size };

        } catch (error) {
            console.error(`❌ ${home_team} vs ${away_team}: ${error.message}`);
            return { success: false, match_id, error: error.message };
        } finally {
            await page.close();
            await context.close();
        }
    }

    /**
     * 保存原始数据
     */
    async saveRawData(matchId, rawData) {
        const client = await this.pool.connect();
        try {
            const query = `
                INSERT INTO raw_match_data (match_id, raw_data, collected_at)
                VALUES ($1, $2, NOW())
                ON CONFLICT (match_id)
                DO UPDATE SET raw_data = EXCLUDED.raw_data, collected_at = NOW()
            `;
            await client.query(query, [JSON.stringify(rawData), matchId]);
        } finally {
            client.release();
        }
    }

    /**
     * 打印报告
     */
    async printReport() {
        const elapsed = ((Date.now() - this.startTime) / 1000).toFixed(1);
        const rate = (this.stats.success / this.stats.total * 100).toFixed(1);

        console.log('═══════════════════════════════════════════════════════════════');
        console.log('  📊 收割完成报告');
        console.log('═══════════════════════════════════════════════════════════════');
        console.log(`  总计: ${this.stats.total} 场`);
        console.log(`  成功: ${this.stats.success} 场`);
        console.log(`  失败: ${this.stats.failed} 场`);
        console.log(`  成功率: ${rate}%`);
        console.log(`  耗时: ${elapsed} 秒`);
        console.log('═══════════════════════════════════════════════════════════════');

        // 清理资源
        if (this.browser) {
            await this.browser.close();
        }
        if (this.pool) {
            await this.pool.end();
        }

        console.log('🛹 资源已清理');
    }
}

module.exports = { ProductionHarvester };
