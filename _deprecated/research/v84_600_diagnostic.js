#!/usr/bin/env node
/**
 * V84.600 - 单点爆破调试工具
 * =============================
 *
 * 用于诊断 temporal_sync_engine 的挂起问题
 *
 * Usage:
 *   DEBUG=pw:api node v84_600_diagnostic.js "<URL>" "<SOURCE_ID>"
 *
 * @file v84_600_diagnostic
 * @version V84.600
 * @since 2026-01-25
 */

'use strict';

const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

// ============================================================================
// CONFIGURATION
// ============================================================================

const DIAG_CONFIG = {
    headless: false,  // V84.700: 使用非 headless 模式绕过检测
    timeout: 90000,  // 增加到 90 秒
    slowMo: 50,     // 放慢操作以便观察
    debug: true,
    logsPath: path.join(__dirname, '../../logs')
};

// ============================================================================
// LOGGING
// ============================================================================

const log = {
    info: (msg) => console.log(`[INFO] ${new Date().toISOString()} - ${msg}`),
    error: (msg) => console.error(`[ERROR] ${new Date().toISOString()} - ${msg}`),
    debug: (msg) => console.log(`[DEBUG] ${new Date().toISOString()} - ${msg}`),
    step: (step, msg) => console.log(`[STEP ${step}] ${msg}`)
};

// ============================================================================
// V84.700: DOM 离线化和属性探测
// ============================================================================

async function performDomOfflineAnalysis(page, sourceId) {
    log.info("");
    log.info("[V84.700] ========================================");
    log.info("[V84.700] DOM 结构深度分析");
    log.info("[V84.700] ========================================");
    log.info("");

    // V84.700: 动作 B - DOM 离线化
    log.info("[动作 B] DOM 离线化 - 导出实时 HTML 结构...");

    try {
        const htmlContent = await page.content();
        const outputPath = path.join(__dirname, '../../logs/temp_snapshot.html');
        fs.writeFileSync(outputPath, htmlContent, 'utf8');
        log.info(`  ✓ HTML 已导出: ${outputPath}`);
        log.info(`    文件大小: ${(htmlContent.length / 1024).toFixed(2)} KB`);
    } catch (e) {
        log.error(`  ✗ HTML 导出失败: ${e.message}`);
    }

    // V84.700: 动作 C - 影子属性探测
    log.info("");
    log.info("[动作 C] 影子属性探测 - 遍历数值节点...");

    try {
        // 查找所有包含数值的 div 元素
        const numericDivs = await page.$$eval('div', (divs, sourceId) => {
            const results = [];

            for (let i = 0; i < divs.length; i++) {
                const div = divs[i];

                // 检查是否包含数值
                const textContent = div.textContent || '';
                const hasNumber = /\d/.test(textContent);

                // 检查是否为 Pinnacle 节点 (通过 sourceId)
                const attributes = {};
                for (const attr of div.attributes) {
                    if (attr.name.startsWith('data-')) {
                        attributes[attr.name] = attr.value;
                    }
                }

                // 获取所有类名
                const classNames = Array.from(div.classList);

                if (hasNumber || Object.keys(attributes).length > 0) {
                    results.push({
                        index: i,
                        text: textContent.substring(0, 50), // 前50字符
                        dataAttributes: attributes,
                        classNames: classNames,
                        id: div.id,
                        role: div.getAttribute('role'),
                        ariaLabel: div.getAttribute('aria-label')
                    });
                }

                // 限制结果数量
                if (results.length > 50) break;
            }

            return results;
        }, sourceId);

        log.info(`  ✓ 找到 ${numericDivs.length} 个包含数值的 div 节点`);

        // 打印核心发现
        if (numericDivs.length > 0) {
            log.info("");
            log.info("  [核心发现] 前 5 个数值节点:");

            for (let i = 0; i < Math.min(5, numericDivs.length); i++) {
                const node = numericDivs[i];
                log.info("");
                log.info(`    节点 ${i}:`);
                log.info(`      文本: "${node.text}"`);
                log.info(`      ID: ${node.id || '(none)'}`);
                log.info(`      Role: ${node.role || '(none)'}`);
                log.info(`      ARIA: ${node.ariaLabel || '(none)'}`);
                log.info(`      类名: ${node.classNames.slice(0, 3).join(' ') || '(none)'}`);
                if (Object.keys(node.dataAttributes).length > 0) {
                    log.info(`      data-* 属性: ${JSON.stringify(node.dataAttributes)}`);
                }
            }
        }

        // 检查 Shadow DOM
        log.info("");
        log.info("[Shadow DOM 探测]");

        const shadowHosts = await page.$$('[data-testid*="over-under"], [data-testid*="game-row"]');
        log.info(`  找到 ${shadowHosts.length} 个可能的 Shadow Host 节点`);

        // 检查 "Odds movement" 锚点
        const anchorExists = await page.$('h3:text("Odds movement")');
        log.info(`  "Odds movement" 锚点存在: ${anchorExists ? '✓ Yes' : '✗ No'}`);

        // 检查 tooltip 容器
        const tooltipSelectors = [
            'div[class*="tooltip"]',
            'div[class*="bottom-"]',
            '[role="tooltip"]',
            '[data-testid*="tooltip"]'
        ];

        for (const selector of tooltipSelectors) {
            const elements = await page.$$(selector);
            if (elements.length > 0) {
                log.info(`  找到 tooltip-like 节点: ${selector} (${elements.length} 个)`);
            }
        }

    } catch (e) {
        log.error(`  ✗ DOM 探测失败: ${e.message}`);
    }

    log.info("");
    log.info("[V84.700] ========================================");
    log.info("");
}

// ============================================================================
// DIAGNOSTIC FUNCTIONS
// ============================================================================

async function diagnoseBrowserLaunch(url, sourceId) {
    log.step(1, "浏览器启动诊断");
    log.info(`目标 URL: ${url}`);
    log.info(`Source ID: ${sourceId}`);

    let browser = null;

    try {
        const launchStart = Date.now();

        log.debug("启动 Chromium (headless=false, 增强反检测)...");
        browser = await chromium.launch({
            headless: DIAG_CONFIG.headless,
            timeout: DIAG_CONFIG.timeout,
            slowMo: DIAG_CONFIG.slowMo,
            args: [
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-gpu',
                '--disable-blink-features=AutomationControlled',
                '--disable-infobars',
                '--window-size=1920,1080',
                '--start-maximized'
            ],
            // V84.700: 绕过 headless 检测
            ignoreDefaultArgs: ['--enable-automation']
        });

        const launchTime = Date.now() - launchStart;
        log.info(`✓ 浏览器启动成功 (${launchTime}ms)`);

        // 创建上下文
        const contextStart = Date.now();
        log.debug("创建浏览器上下文...");
        const context = await browser.newContext({
            viewport: { width: 1920, height: 1080 },
            userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            // V84.700: 额外的反检测配置
            locale: 'en-US',
            timezoneId: 'America/New_York',
            permissions: ['geolocation'],
            extraHTTPHeaders: {
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }
        });
        const contextTime = Date.now() - contextStart;
        log.info(`✓ 上下文创建成功 (${contextTime}ms)`);

        // 创建页面
        const pageStart = Date.now();
        log.debug("创建新页面...");
        const page = await context.newPage();

        // V84.700: 移除 webdriver 追踪以绕过反爬虫检测
        await page.addInitScript(() => {
            // 覆盖 navigator.webdriver
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });

            // 覆盖 Chrome 对象
            window.chrome = {
                runtime: {}
            };

            // 覆盖 permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );

            // 覆盖 plugins 长度
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });

            // 覆盖 languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en']
            });
        });

        const pageTime = Date.now() - pageStart;
        log.info(`✓ 页面创建成功 (${pageTime}ms)`);

        // 导航到目标 URL
        const navStart = Date.now();
        let navTime = 0;  // V84.700: 在外部声明以避免作用域错误
        log.info(`导航到: ${url.substring(0, 60)}...`);

        try {
            // V84.700: 等待网络空闲（确保 JS 执行完成）
            await page.goto(url, {
                waitUntil: 'networkidle',
                timeout: DIAG_CONFIG.timeout
            });
            navTime = Date.now() - navStart;
            log.info(`✓ 页面加载成功 (${navTime}ms)`);
        } catch (navError) {
            log.error(`✗ 页面加载失败: ${navError.message}`);
            throw navError;
        }

        // V84.700: 额外等待 JS 渲染
        try {
            await page.waitForTimeout(3000);
            log.debug("额外等待 3 秒以确保 JS 渲染完成");
        } catch (e) {
            // 忽略超时
        }

        // 页面快照
        log.debug("获取页面快照...");
        const snapshot = {
            url: page.url(),
            title: await page.title(),
            contentLength: (await page.content()).length
        };
        log.info(`页面快照:`);
        log.info(`  URL: ${snapshot.url}`);
        log.info(`  Title: ${snapshot.title}`);
        log.info(`  Content: ${snapshot.contentLength} bytes`);

        // V84.700: 动作 B - DOM 离线化
        await performDomOfflineAnalysis(page, sourceId);

        // 清理
        await context.close();
        await browser.close();

        return {
            success: true,
            timing: {
                launch: launchTime,
                context: contextTime,
                page: pageTime,
                navigation: navTime,
                total: Date.now() - launchStart
            },
            snapshot: snapshot
        };

    } catch (error) {
        log.error(`诊断失败: ${error.message}`);

        if (browser) {
            try {
                await browser.close();
            } catch (e) {
                // 忽略清理错误
            }
        }

        return {
            success: false,
            error: error.message,
            stack: error.stack
        };
    }
}

async function diagnoseDatabaseConnection() {
    log.step(2, "数据库连接诊断");

    const { Client } = require('pg');
    const client = new Client({
        connectionString: 'postgresql://football_user:football_pass@172.25.16.1:5432/football_db',
        connectTimeoutMS: 5000
    });

    try {
        const connectStart = Date.now();
        await client.connect();
        const connectTime = Date.now() - connectStart;
        log.info(`✓ 数据库连接成功 (${connectTime}ms)`);

        const result = await client.query('SELECT NOW() as current_time');
        log.info(`✓ 数据库查询成功: ${result.rows[0].current_time}`);

        await client.end();
        return { success: true };
    } catch (error) {
        log.error(`✗ 数据库连接失败: ${error.message}`);
        return { success: false, error: error.message };
    }
}

async function checkLogFileAccess() {
    log.step(3, "日志文件权限诊断");

    const logsDir = path.join(__dirname, '../../logs');

    try {
        if (!fs.existsSync(logsDir)) {
            fs.mkdirSync(logsDir, { recursive: true });
            log.info(`✓ 创建 logs/ 目录: ${logsDir}`);
        }

        const testFile = path.join(logsDir, 'v84_600_diagnostic.log');
        fs.writeFileSync(testFile, `[V84.600] Diagnostic test at ${new Date().toISOString()}\n`);
        log.info(`✓ 日志写入成功: ${testFile}`);

        const stats = fs.statSync(logsDir);
        log.info(`目录权限: ${stats.mode.toString(8)}`);
        log.info(`  可写: ${(stats.mode & 0o200).toString(8) === '200' ? 'Yes' : 'No'}`);

        return { success: true };
    } catch (error) {
        log.error(`✗ 日志文件访问失败: ${error.message}`);
        return { success: false, error: error.message };
    }
}

async function runDiagnostic(url, sourceId) {
    log.info("=" .repeat(60));
    log.info("V84.600 诊断工具启动");
    log.info("=" .repeat(60));
    log.info(`URL: ${url}`);
    log.info(`Source ID: ${sourceId}`);
    log.info("");

    const results = {
        browser: null,
        database: null,
        logs: null,
        overall: false
    };

    // 步骤 1: 日志文件诊断
    results.logs = await checkLogFileAccess();

    // 步骤 2: 数据库连接诊断
    results.database = await diagnoseDatabaseConnection();

    // 步骤 3: 浏览器启动诊断（仅在前两步成功时）
    if (results.logs.success && results.database.success) {
        results.browser = await diagnoseBrowserLaunch(url, sourceId);
    }

    // 最终报告
    log.info("");
    log.info("=" .repeat(60));
    log.info("V84.600 诊断报告");
    log.info("=" .repeat(60));
    log.info(`日志文件: ${results.logs.success ? '✓ 正常' : '✗ 异常'}`);
    log.info(`数据库连接: ${results.database.success ? '✓ 正常' : '✗ 异常'}`);
    log.info(`浏览器启动: ${results.browser ? (results.browser.success ? '✓ 正常' : '✗ 异常') : '⊘ 跳过'}`);
    log.info("");

    // 根因分析
    if (results.logs && !results.logs.success) {
        log.error("[根因] 日志文件权限不足");
        log.error("  修复: chmod 755 logs/");
    } else if (results.database && !results.database.success) {
        log.error("[根因] 数据库连接失败");
        log.error("  修复: 检查 172.25.16.1:5432 连通性和凭证");
    } else if (results.browser && !results.browser.success) {
        if (results.browser.error && results.browser.error.includes('timeout')) {
            log.error("[根因] 网络超时 - 目标网站可能被封锁或响应缓慢");
            log.error("  修复: 检查代理配置，尝试增加 timeout 或使用不同的网络环境");
        } else if (results.browser.error && results.browser.error.includes('net::ERR_')) {
            log.error("[根因] 网络错误 - DNS 或连接问题");
            log.error("  修复: 检查网络连通性，尝试 ping 目标域名");
        }
    } else {
        log.info("[状态] ✓ 所有诊断项通过 - 系统运行正常");
    }

    log.info("");
    log.info("=" .repeat(60));
    log.info("[V84.600] Diagnostic COMPLETE");
    log.info("=" .repeat(60));

    return results;
}

// ============================================================================
// CLI ENTRY POINT
// ============================================================================

if (require.main === module) {
    const args = process.argv.slice(2);
    const url = args[0];
    const sourceId = args[1] || 'test';

    if (!url) {
        console.error('Usage:');
        console.error('  DEBUG=pw:api node v84_600_diagnostic.js "<URL>" "[SOURCE_ID]');
        console.error('');
        console.error('Example:');
        console.error('  DEBUG=pw:api node v84_600_diagnostic.js "https://www.oddsportal.com/soccer/england/premier-league/" "4507128"');
        process.exit(1);
    }

    runDiagnostic(url, sourceId)
        .then(() => process.exit(0))
        .catch(error => {
            console.error('[FATAL]', error);
            process.exit(1);
        });
}

module.exports = { runDiagnostic };
