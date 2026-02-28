/**
 * V173: 网页渗透模式测试 (Infiltration Test)
 * ==========================================
 *
 * "狸猫换太子"战术验证
 * 从比赛详情页的 __NEXT_DATA__ 标签提取核心 JSON
 *
 * @module scripts/ops/test_infiltration
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

const TEST_PROXY_PORT = parseInt(process.env.TEST_PROXY_PORT) || 7895;
const TEST_MATCH_ID = process.env.TEST_MATCH_ID || '4803417';  // Hellas Verona vs Roma

// ============================================================================
// Logger
// ============================================================================

const log = {
    _ts: () => {
        const d = new Date();
        return `${d.toISOString().slice(0, 10)} ${d.toTimeString().slice(0, 8)}`;
    },
    info: (msg) => console.log(`${log._ts()} [INFIL] [INFO] ${msg}`),
    success: (msg) => console.log(`${log._ts()} [INFIL] [OK] ✅ ${msg}`),
    warn: (msg) => console.log(`${log._ts()} [INFIL] [WARN] ⚠️  ${msg}`),
    error: (msg) => console.error(`${log._ts()} [INFIL] [ERR] ❌ ${msg}`),
    debug: (msg) => console.log(`${log._ts()} [INFIL] [DBG] 🔍 ${msg}`)
};

// ============================================================================
// 网页渗透测试类
// ============================================================================

class InfiltrationTest {
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
     * 启动浏览器
     */
    async launchBrowser() {
        const proxyServer = FactoryConfig.PROXY_CONFIG.getServer(TEST_PROXY_PORT);

        // 使用一致的桌面端配置
        const desktopUA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36';
        const desktopViewport = { width: 1920, height: 1080 };

        log.info(`📡 代理: ${proxyServer}`);
        log.info(`🎭 UA: ${desktopUA.substring(0, 60)}...`);
        log.info(`📐 Viewport: ${desktopViewport.width}x${desktopViewport.height}`);

        this.browser = await chromium.launch({
            headless: FactoryConfig.BROWSER.headless,
            proxy: { server: proxyServer },
            args: FactoryConfig.BROWSER.launchArgs
        });

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

        log.success('浏览器已启动');
    }

    /**
     * 检测 Cloudflare 拦截
     */
    async checkCloudflareBlock() {
        const content = await this.page.content();
        const title = await this.page.title();

        const cfIndicators = [
            'Just a moment...',
            'Checking your browser',
            'Please Wait...',
            'Cloudflare',
            'cf-browser-verification',
            'challenge-platform'
        ];

        const isBlocked = cfIndicators.some(indicator =>
            content.includes(indicator) || title.includes(indicator)
        );

        return isBlocked;
    }

    /**
     * 模拟真人行为
     */
    async simulateHumanBehavior() {
        // 1. 随机等待 3-6 秒
        const readDelay = 3000 + Math.random() * 3000;
        await this.page.waitForTimeout(readDelay);
        log.info(`📖 模拟阅读 ${Math.round(readDelay / 1000)}s`);

        // 2. 随机滚动
        const scrollAmount = 100 + Math.floor(Math.random() * 300);
        await this.page.evaluate((scroll) => {
            window.scrollBy(0, scroll);
        }, scrollAmount);
        log.info(`📜 模拟滚动 ${scrollAmount}px`);

        // 3. 等待滚动完成
        await this.page.waitForTimeout(500 + Math.random() * 500);
    }

    /**
     * 从 __NEXT_DATA__ 提取 JSON
     */
    async extractNextData() {
        const rawData = await this.page.evaluate(() => {
            const el = document.getElementById('__NEXT_DATA__');
            if (!el) return null;

            try {
                return JSON.parse(el.innerHTML);
            } catch (e) {
                return { error: `JSON 解析失败: ${e.message}` };
            }
        });

        return rawData;
    }

    /**
     * 转换数据格式
     */
    transformData(nextData, matchId) {
        if (!nextData || !nextData.props || !nextData.props.pageProps) {
            return null;
        }

        const pageProps = nextData.props.pageProps;

        // 如果直接有 matchDetails 字段
        if (pageProps.matchDetails) {
            return {
                matchId: matchId,
                ...pageProps.matchDetails
            };
        }

        // 构建兼容格式
        return {
            matchId: matchId,
            content: pageProps.content || {},
            general: pageProps.general || {},
            header: pageProps.header || {},
            _rawNextData: nextData
        };
    }

    /**
     * 运行测试
     */
    async run(matchId) {
        console.log('\n' + '='.repeat(70));
        console.log('🎭 V173 网页渗透模式测试 (Infiltration Test)');
        console.log('='.repeat(70) + '\n');

        const startTime = Date.now();

        try {
            // 1. 预清理
            this.preFlightCleanup();

            // 2. 启动浏览器
            await this.launchBrowser();
            this.page = await this.context.newPage();

            // 3. 构建比赛详情页 URL
            const matchUrl = `https://www.fotmob.com/match/${matchId}`;
            log.info(`🎯 渗透目标: ${matchUrl}`);

            // 4. 访问比赛页面
            await this.page.goto(matchUrl, {
                timeout: 60000,
                waitUntil: 'domcontentloaded'
            });

            // 5. 等待网络空闲
            log.info('⏳ 等待页面完全加载...');
            await this.page.waitForLoadState('networkidle', {
                timeout: 30000
            }).catch(() => {
                log.warn('网络空闲等待超时，继续处理');
            });

            // 6. 检测 Cloudflare 拦截
            const isBlocked = await this.checkCloudflareBlock();
            if (isBlocked) {
                log.warn('检测到 Cloudflare 挑战页面，等待验证...');
                await this.page.waitForTimeout(10000);

                const stillBlocked = await this.checkCloudflareBlock();
                if (stillBlocked) {
                    log.error('Cloudflare 持续拦截，测试失败');
                    return { success: false, reason: 'CF_BLOCK' };
                }
            }

            // 7. 模拟真人行为
            await this.simulateHumanBehavior();

            // 8. 提取 __NEXT_DATA__
            log.info('🔍 搜索 __NEXT_DATA__ 标签...');
            const nextData = await this.extractNextData();

            if (!nextData) {
                log.error('未找到 __NEXT_DATA__ 标签');
                return { success: false, reason: 'NO_NEXT_DATA' };
            }

            // 9. 分析数据结构
            const rawSize = JSON.stringify(nextData).length;
            log.success(`__NEXT_DATA__ 提取成功！原始大小: ${rawSize} bytes (${(rawSize / 1024).toFixed(1)} KB)`);

            // 10. 打印数据结构
            log.info('📊 数据结构分析:');
            log.info(`   - props: ${nextData.props ? '✅' : '❌'}`);
            log.info(`   - pageProps: ${nextData.props?.pageProps ? '✅' : '❌'}`);

            if (nextData.props?.pageProps) {
                const pp = nextData.props.pageProps;
                log.info(`   - matchDetails: ${pp.matchDetails ? '✅' : '❌'}`);
                log.info(`   - content: ${pp.content ? '✅' : '❌'}`);
                log.info(`   - general: ${pp.general ? '✅' : '❌'}`);

                // 打印 pageProps 的所有顶级字段
                log.info('📋 pageProps 顶级字段:');
                Object.keys(pp).forEach(key => {
                    const value = pp[key];
                    const type = typeof value;
                    const size = type === 'object' ? JSON.stringify(value).length : 0;
                    log.info(`   - ${key}: ${type}${size ? ` (${size} bytes)` : ''}`);
                });

                // 检查 content 的结构
                if (pp.content) {
                    log.info('📋 content 子字段:');
                    Object.keys(pp.content).slice(0, 10).forEach(key => {
                        log.info(`   - ${key}`);
                    });
                }

                // 检查是否有错误信息
                const jsonStr = JSON.stringify(pp);
                if (jsonStr.includes('error') || jsonStr.includes('Error')) {
                    log.warn('⚠️ 数据中包含 "error" 关键词，检查具体位置...');
                    // 查找错误位置
                    const errorMatch = jsonStr.match(/"error[^"]*"\s*:\s*"[^"]+"/gi);
                    if (errorMatch) {
                        log.warn(`   发现错误字段: ${errorMatch.slice(0, 3).join(', ')}`);
                    }
                }
            }

            // 11. 转换数据格式
            const apiData = this.transformData(nextData, matchId);

            if (!apiData) {
                log.error('数据格式转换失败');
                return { success: false, reason: 'DATA_TRANSFORM_FAILED' };
            }

            // 12. 质量门禁检查
            const validation = FactoryConfig.QUALITY_GATE.isValid(apiData);
            const transformedSize = JSON.stringify(apiData).length;

            const loadTime = Date.now() - startTime;

            console.log('\n' + '-'.repeat(70));
            console.log('📈 测试结果汇总:');
            console.log(`   - 数据大小: ${transformedSize} bytes (${(transformedSize / 1024).toFixed(1)} KB)`);
            console.log(`   - 质量门禁: ${validation.valid ? '✅ 通过' : '❌ 失败 (' + validation.reason + ')'}`);
            console.log(`   - 总耗时: ${loadTime}ms`);
            console.log('-'.repeat(70) + '\n');

            // 13. 提取关键数据示例
            if (apiData.content?.stats?.Periods?.All?.stats) {
                const allStats = apiData.content.stats.Periods.All.stats;
                const xgGroup = allStats.find(g => (g.title || '').toLowerCase().includes('expected goals'));

                if (xgGroup?.stats) {
                    const xgRow = xgGroup.stats.find(s => (s.key || '').toLowerCase() === 'expected_goals');
                    if (xgRow?.stats?.length >= 2) {
                        log.success(`xG 数据: 主队 ${xgRow.stats[0]} - 客队 ${xgRow.stats[1]}`);
                    }
                }
            }

            return {
                success: validation.valid,
                size: transformedSize,
                loadTime,
                validation
            };

        } catch (error) {
            log.error(`测试异常: ${error.message}`);
            return { success: false, reason: error.message };

        } finally {
            // 清理资源
            if (this.page) {
                try { await this.page.close(); } catch (e) { /* 忽略 */ }
            }
            if (this.context) {
                try { await this.context.close(); } catch (e) { /* 忽略 */ }
            }
            if (this.browser) {
                try { await this.browser.close(); } catch (e) { /* 忽略 */ }
            }
            log.success('资源已释放');
        }
    }
}

// ============================================================================
// 主函数
// ============================================================================

async function main() {
    const test = new InfiltrationTest();
    const matchId = process.argv[2] || TEST_MATCH_ID;

    const result = await test.run(matchId);

    console.log('\n' + '='.repeat(70));
    if (result.success) {
        console.log('🏆 网页渗透测试成功！');
        console.log(`   数据大小: ${result.size} bytes (${(result.size / 1024).toFixed(1)} KB)`);
        console.log(`   耗时: ${result.loadTime}ms`);

        // 检查是否大于 200KB
        if (result.size > 200 * 1024) {
            console.log('   ✅ 数据量符合预期 (>200KB)');
        } else {
            console.log(`   ⚠️ 数据量较小 (${(result.size / 1024).toFixed(1)}KB)，可能不完整`);
        }
    } else {
        console.log('💥 网页渗透测试失败！');
        console.log(`   原因: ${result.reason}`);
    }
    console.log('='.repeat(70) + '\n');

    process.exit(result.success ? 0 : 1);
}

main();
