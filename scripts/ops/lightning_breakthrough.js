/**
 * V173: 闪电突围测试 (Lightning Breakthrough Test)
 * ================================================
 *
 * 最严苛的单点测试：新 IP + 新指纹 + 零 Cookie
 * 验证"零信任"身份重置后的突破能力
 *
 * @module scripts/ops/lightning_breakthrough
 * @version V173.0.0
 */

'use strict';

const path = require('path');
const fs = require('fs');

const PROJECT_ROOT = process.env.PROJECT_ROOT || '/app';
const FactoryConfig = require(path.join(PROJECT_ROOT, 'config/factory_config'));
const { chromium } = require('playwright');

// ============================================================================
// 配置
// ============================================================================

// 使用一个较不常用的端口（7911）进行测试
const TEST_PROXY_PORT = parseInt(process.env.TEST_PROXY_PORT) || 7911;
const TEST_MATCH_ID = process.env.TEST_MATCH_ID || null;  // 如果不指定，会从数据库获取一场意甲比赛

// ============================================================================
// Logger
// ============================================================================

const log = {
    _ts: () => {
        const d = new Date();
        return `${d.toISOString().slice(0, 10)} ${d.toTimeString().slice(0, 8)}`;
    },
    info: (msg) => console.log(`${log._ts()} [LIGHTNING] [INFO] ${msg}`),
    success: (msg) => console.log(`${log._ts()} [LIGHTNING] [OK] ✅ ${msg}`),
    warn: (msg) => console.log(`${log._ts()} [LIGHTNING] [WARN] ⚠️  ${msg}`),
    error: (msg) => console.error(`${log._ts()} [LIGHTNING] [ERR] ❌ ${msg}`)
};

// ============================================================================
// 闪电测试类
// ============================================================================

class LightningBreakthrough {
    constructor() {
        this.browser = null;
        this.context = null;
        this.page = null;
    }

    /**
     * 预清理 - 杀死僵尸进程
     */
    preFlightCleanup() {
        const { execSync } = require('child_process');

        try {
            const zombiePids = execSync('pgrep -f "chromium|chrome" 2>/dev/null || true', {
                encoding: 'utf8',
                timeout: 5000
            }).trim();

            if (zombiePids) {
                const pids = zombiePids.split('\n').filter(p => p);
                log.info(`🧹 发现 ${pids.length} 个僵尸进程，正在清理...`);

                for (const pid of pids) {
                    try {
                        execSync(`kill -9 ${pid} 2>/dev/null || true`, { timeout: 1000 });
                    } catch (e) { /* 忽略 */ }
                }
                log.success('僵尸进程已清理');
            }
        } catch (e) {
            log.warn(`清理检查失败: ${e.message}`);
        }
    }

    /**
     * 启动浏览器 - 零 Cookie 模式
     */
    async launchBrowser() {
        const proxyServer = FactoryConfig.PROXY_CONFIG.getServer(TEST_PROXY_PORT);

        // V173: 使用一致的桌面端 UA（避免 UA/Viewport 不匹配）
        const desktopUA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36';
        const desktopViewport = { width: 1920, height: 1080 };

        log.info(`📡 代理: ${proxyServer}`);
        log.info(`🎭 UA: ${desktopUA.substring(0, 60)}...`);
        log.info(`📐 Viewport: ${desktopViewport.width}x${desktopViewport.height}`);
        log.info(`🍪 Cookie: 零信任模式（不加载任何旧身份）`);

        this.browser = await chromium.launch({
            headless: FactoryConfig.BROWSER.headless,
            proxy: { server: proxyServer },
            args: FactoryConfig.BROWSER.launchArgs
        });

        // 零信任：不加载任何 storageState
        this.context = await this.browser.newContext({
            userAgent: desktopUA,
            viewport: desktopViewport,
            locale: 'en-US',
            timezoneId: 'Europe/London'
        });

        // 注入 Stealth 脚本
        await this.context.addInitScript(() => {
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            Object.defineProperty(navigator, 'hardwareConcurrency', { get: () => 8 });
            Object.defineProperty(navigator, 'deviceMemory', { get: () => 8 });
            window.chrome = { runtime: {} };
        });

        log.success('浏览器已启动（零信任模式）');
    }

    /**
     * 访问 FotMob 首页 - 建立新会话
     */
    async visitHomepage() {
        this.page = await this.context.newPage();

        log.info('🌐 访问 FotMob 首页...');
        const startTime = Date.now();

        await this.page.goto('https://www.fotmob.com/', {
            timeout: 60000,
            waitUntil: 'domcontentloaded'
        });

        // V173: 等待 Turnstile 自动验证（最多等待 15 秒）
        log.info('⏳ 等待页面完全加载（可能包含 Turnstile 验证）...');

        let turnstilePassed = false;
        const maxWaitTime = 15000;
        const checkInterval = 1000;
        let waitedTime = 0;

        while (waitedTime < maxWaitTime) {
            await this.page.waitForTimeout(checkInterval);
            waitedTime += checkInterval;

            const content = await this.page.content();
            const hasTurnstile = content.includes('turnstile') || content.includes('challenge') || content.includes('cf-');

            // 检查是否有正常的 FotMob 内容
            const hasFotMobContent = content.includes('fotmob') && (content.includes('match') || content.includes('league') || content.includes('team'));

            if (hasFotMobContent && !hasTurnstile) {
                turnstilePassed = true;
                break;
            }

            if (waitedTime % 3000 === 0) {
                log.info(`   已等待 ${waitedTime / 1000}s...`);
            }
        }

        const loadTime = Date.now() - startTime;
        log.success(`页面加载完成 (${loadTime}ms)`);

        // 最终检查
        const finalContent = await this.page.content();
        const finalUrl = this.page.url();

        log.info(`📍 最终 URL: ${finalUrl}`);

        if (finalContent.includes('turnstile') && !finalContent.includes('match')) {
            log.warn('⚠️ Turnstile 验证未自动通过，尝试手动处理...');

            // 尝试等待更长时间
            await this.page.waitForTimeout(5000);

            // 检查是否有验证 checkbox
            const checkbox = await this.page.$('input[type="checkbox"]');
            if (checkbox) {
                await checkbox.click();
                log.info('已点击验证 checkbox');
                await this.page.waitForTimeout(3000);
            }
        }

        // 检查页面是否有实际内容
        const bodyText = await this.page.evaluate(() => document.body?.innerText || '');
        const hasContent = bodyText.length > 500;

        if (!hasContent) {
            log.warn('页面内容过少，可能被拦截');
            return false;
        }

        log.success(`页面内容正常 (${bodyText.length} 字符)`);
        return true;
    }

    /**
     * 测试 API 请求 - 获取比赛数据
     */
    async testApiRequest(matchId) {
        log.info(`📊 测试 API 请求 (Match ID: ${matchId})...`);

        const apiData = await this.page.evaluate(async (id) => {
            try {
                const res = await fetch(`https://www.fotmob.com/api/matchDetails?matchId=${id}`, {
                    credentials: 'include'
                });
                return await res.json();
            } catch (e) {
                return { error: e.message };
            }
        }, matchId);

        // 打印实际响应内容（用于诊断）
        const rawStr = JSON.stringify(apiData);
        log.info(`📥 API 响应: ${rawStr.substring(0, 200)}${rawStr.length > 200 ? '...' : ''}`);

        // 质量门禁检查
        const validation = FactoryConfig.QUALITY_GATE.isValid(apiData);

        if (!validation.valid) {
            log.error(`质量门禁失败: ${validation.reason} (size: ${validation.size || 0})`);
            return { success: false, reason: validation.reason, data: apiData };
        }

        const rawSize = JSON.stringify(apiData).length;
        log.success(`API 请求成功！数据大小: ${rawSize} bytes`);

        // 提取关键数据
        const periods = apiData?.content?.stats?.Periods;
        const allStats = periods?.All?.stats || [];

        const xgGroup = allStats.find(g => (g.title || '').toLowerCase().includes('expected goals'));
        let xgHome = null, xgAway = null;

        if (xgGroup?.stats) {
            const xgRow = xgGroup.stats.find(s => (s.key || '').toLowerCase() === 'expected_goals');
            if (xgRow?.stats?.length >= 2) {
                xgHome = parseFloat(xgRow.stats[0]);
                xgAway = parseFloat(xgRow.stats[1]);
            }
        }

        log.success(`xG: 主队 ${xgHome} - 客队 ${xgAway}`);

        return {
            success: true,
            size: rawSize,
            xg: { home: xgHome, away: xgAway }
        };
    }

    /**
     * 清理资源
     */
    async cleanup() {
        const errors = [];

        if (this.page) {
            try { await this.page.close(); } catch (e) { errors.push(`page: ${e.message}`); }
            this.page = null;
        }

        if (this.context) {
            try { await this.context.close(); } catch (e) { errors.push(`context: ${e.message}`); }
            this.context = null;
        }

        if (this.browser) {
            try { await this.browser.close(); } catch (e) { errors.push(`browser: ${e.message}`); }
            this.browser = null;
        }

        if (errors.length > 0) {
            log.warn(`清理时有错误: ${errors.join(', ')}`);
        } else {
            log.success('资源已完全释放');
        }
    }

    /**
     * 运行完整测试
     */
    async run(matchId) {
        console.log('\n' + '='.repeat(70));
        console.log('⚡ V173 闪电突围测试 (Lightning Breakthrough Test)');
        console.log('='.repeat(70) + '\n');

        try {
            // 1. 预清理
            this.preFlightCleanup();

            // 2. 启动浏览器（零 Cookie）
            await this.launchBrowser();

            // 3. 访问首页
            const homepageOk = await this.visitHomepage();
            if (!homepageOk) {
                log.error('首页访问失败，可能被 Turnstile 拦截');
                return { success: false, reason: 'HOMEPAGE_BLOCKED' };
            }

            // 4. 测试 API
            const result = await this.testApiRequest(matchId);

            // 5. 保存新 Cookie（如果成功）
            if (result.success) {
                const profilePath = FactoryConfig.BROWSER.profilePath;
                const statePath = FactoryConfig.BROWSER.getStatePath();

                if (!fs.existsSync(profilePath)) {
                    fs.mkdirSync(profilePath, { recursive: true });
                }

                const state = await this.context.storageState();
                fs.writeFileSync(statePath, JSON.stringify(state, null, 2));
                log.success('新 Cookie 已保存');
            }

            return result;

        } catch (error) {
            log.error(`测试失败: ${error.message}`);
            return { success: false, reason: error.message };

        } finally {
            await this.cleanup();
        }
    }
}

// ============================================================================
// 获取测试比赛 ID
// ============================================================================

async function getTestMatchId() {
    if (TEST_MATCH_ID) {
        log.info(`使用指定的 Match ID: ${TEST_MATCH_ID}`);
        return TEST_MATCH_ID;
    }

    // 从数据库获取一场意甲比赛
    const { Client } = require('pg');
    const { DatabaseConfig } = require(path.join(PROJECT_ROOT, 'src/infrastructure/database/PostgresClient'));

    const client = new Client({
        host: DatabaseConfig.host,
        port: DatabaseConfig.port,
        database: DatabaseConfig.database,
        user: DatabaseConfig.user,
        password: DatabaseConfig.password,
        connectionTimeoutMillis: 10000
    });

    try {
        await client.connect();

        // 查询一场有意甲比赛数据的记录
        const query = `
            SELECT external_id, home_team, away_team
            FROM matches
            WHERE external_id IS NOT NULL
              AND league_name ILIKE '%Serie A%'
            ORDER BY match_date DESC
            LIMIT 1
        `;

        const result = await client.query(query);

        if (result.rows.length === 0) {
            // 如果没有意甲，尝试任意比赛
            const fallbackQuery = `
                SELECT external_id, home_team, away_team
                FROM matches
                WHERE external_id IS NOT NULL
                ORDER BY match_date DESC
                LIMIT 1
            `;
            const fallbackResult = await client.query(fallbackQuery);

            if (fallbackResult.rows.length === 0) {
                throw new Error('没有可用的比赛记录');
            }

            const match = fallbackResult.rows[0];
            log.info(`使用比赛: ${match.home_team} vs ${match.away_team} (ID: ${match.external_id})`);
            return match.external_id;
        }

        const match = result.rows[0];
        log.info(`使用意甲比赛: ${match.home_team} vs ${match.away_team} (ID: ${match.external_id})`);
        return match.external_id;

    } finally {
        await client.end();
    }
}

// ============================================================================
// 主函数
// ============================================================================

async function main() {
    const test = new LightningBreakthrough();

    try {
        const matchId = await getTestMatchId();
        const result = await test.run(matchId);

        console.log('\n' + '='.repeat(70));
        if (result.success) {
            console.log('🏆 闪电突围测试成功！');
            console.log(`   数据大小: ${result.size} bytes`);
            console.log(`   xG: ${result.xg.home} - ${result.xg.away}`);
        } else {
            console.log('💥 闪电突围测试失败！');
            console.log(`   原因: ${result.reason}`);
        }
        console.log('='.repeat(70) + '\n');

        process.exit(result.success ? 0 : 1);

    } catch (error) {
        console.error(`\n❌ 测试异常: ${error.message}\n`);
        process.exit(1);
    }
}

main();
