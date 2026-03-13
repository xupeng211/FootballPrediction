/**
 * AutoAuthManager - V4.51 自动身份管理器
 * =========================================
 *
 * 核心功能：
 * - 启动可见浏览器捕获 Cookie
 * - 访问 FotMob 绕过 Turnstile
 * - 自动保存 Cookie 到 data/sessions/
 * - 支持多端口身份隔离
 * - V4.51.1: 支持 Session 热刷新
 *
 * @module infrastructure/auth/AutoAuthManager
 * @version V4.51.1
 */

'use strict';

const { chromium } = require('playwright');
const fs = require('fs').promises;
const path = require('path');
const { getPathResolver } = require('../utils/PathResolver');
const { logger } = require('../utils/Logger');

// ============================================================================
// 单例模式
// ============================================================================

let _instance = null;

class AutoAuthManager {
    /**
     * 创建 AutoAuthManager 实例
     * @param {Object} [config={}] - 配置选项
     * @param {number} [config.timeout=60000] - 浏览器超时时间（毫秒）
     * @param {boolean} [config.headless=false] - 是否无头模式（默认可见）
     * @param {string} [config.targetUrl='https://www.fotmob.com'] - 目标 URL
     */
    constructor(config = {}) {
        this.config = {
            timeout: config.timeout || 60000,
            headless: config.headless || false,  // 默认可见浏览器
            targetUrl: config.targetUrl || 'https://www.fotmob.com',
            ...config
        };

        this.browser = null;
        this.context = null;
        this.page = null;
    }

    /**
     * V4.51.1: 刷新指定端口的 Session
     * 尝试从磁盘重新加载已有的 Session 文件
     *
     * @param {number} workerId - Worker ID
     * @param {number} port - 代理端口
     * @returns {Promise<{success: boolean, cookieCount: number, error?: string}>}
     */
    async refreshSession(workerId, port) {
        console.log(`\n🔄 [AutoAuth] W${workerId} 刷新 Session (Port ${port})...`);

        try {
            const pathResolver = getPathResolver();
            const sessionDir = pathResolver.getSessionsPath();
            const sessionFile = path.join(sessionDir, `session_port_${port}.json`);

            // 检查 Session 文件是否存在
            try {
                await fs.access(sessionFile);
            } catch {
                console.log(`  ⚠️ [AutoAuth] Port ${port} 无现有 Session 文件`);
                return {
                    success: false,
                    cookieCount: 0,
                    error: 'NO_SESSION_FILE'
                };
            }

            // 读取并验证 Session 文件
            const content = await fs.readFile(sessionFile, 'utf8');
            const sessionData = JSON.parse(content);

            if (!sessionData.cookies || sessionData.cookies.length === 0) {
                console.log(`  ⚠️ [AutoAuth] Port ${port} Session 文件无有效 Cookie`);
                return {
                    success: false,
                    cookieCount: 0,
                    error: 'EMPTY_SESSION'
                };
            }

            // 更新时间戳，标记为已刷新
            sessionData.lastRefreshed = new Date().toISOString();
            sessionData.refreshedBy = 'AutoAuthManager.refreshSession';

            await fs.writeFile(sessionFile, JSON.stringify(sessionData, null, 2), 'utf8');

            console.log(`  ✅ [AutoAuth] Port ${port} Session 已刷新 (${sessionData.cookies.length} cookies)`);

            return {
                success: true,
                cookieCount: sessionData.cookies.length
            };

        } catch (error) {
            console.error(`  ❌ [AutoAuth] 刷新 Session 失败: ${error.message}`);
            return {
                success: false,
                cookieCount: 0,
                error: error.message
            };
        }
    }

    /**
     * V4.51.1: 检查是否支持可见浏览器（需要 X Server）
     * @returns {boolean}
     */
    static canLaunchVisibleBrowser() {
        // 检查 DISPLAY 环境变量
        return !!process.env.DISPLAY;
    }

    /**
     * 启动浏览器（可见模式）
     * @returns {Promise<void>}
     */
    async launchBrowser() {
        console.log('🚀 [AutoAuth] 启动可见浏览器...');

        this.browser = await chromium.launch({
            headless: this.config.headless,  // 可见模式
            args: [
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-blink-features=AutomationControlled',
                '--disable-gpu',
                '--start-maximized'  // 最大化窗口
            ]
        });

        console.log('✅ [AutoAuth] 浏览器已启动');
    }

    /**
     * 创建浏览器上下文
     * @param {number} [port] - 代理端口（可选）
     * @returns {Promise<void>}
     */
    async createContext(port = null) {
        if (!this.browser) {
            throw new Error('浏览器未启动');
        }

        const contextOptions = {
            viewport: { width: 1920, height: 1080 },
            userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            locale: 'en-US',
            timezoneId: 'Europe/London'
        };

        // 如果指定了代理端口，配置代理
        if (port) {
            contextOptions.proxy = {
                server: `http://172.25.16.1:${port}`
            };
            console.log(`🌐 [AutoAuth] 使用代理端口: ${port}`);
        }

        this.context = await this.browser.newContext(contextOptions);
        console.log('✅ [AutoAuth] 浏览器上下文已创建');
    }

    /**
     * 创建新页面
     * @returns {Promise<void>}
     */
    async createPage() {
        if (!this.context) {
            throw new Error('浏览器上下文未创建');
        }

        this.page = await this.context.newPage();
        console.log('✅ [AutoAuth] 新页面已创建');
    }

    /**
     * 访问目标网站并等待用户手动过 Turnstile
     * @returns {Promise<void>}
     */
    async navigateAndWait() {
        if (!this.page) {
            throw new Error('页面未创建');
        }

        console.log(`\n📍 [AutoAuth] 导航到: ${this.config.targetUrl}`);

        await this.page.goto(this.config.targetUrl, {
            waitUntil: 'domcontentloaded',
            timeout: this.config.timeout
        });

        console.log('✅ [AutoAuth] 页面已加载');
        console.log('\n');
        console.log('═══════════════════════════════════════════════════════════════');
        console.log('  ⚠️  请在浏览器中手动完成以下操作：');
        console.log('  1. 如果出现 Turnstile 验证码，请完成验证');
        console.log('  2. 等待页面完全加载（显示比赛列表）');
        console.log('  3. 等待 30 秒后系统将自动捕获 Cookie');
        console.log('═══════════════════════════════════════════════════════════════');
        console.log('\n');

        // 等待用户完成操作（30 秒）
        await this.page.waitForTimeout(30000);
    }

    /**
     * 捕获当前 Cookie
     * @returns {Promise<Array>} Cookie 数组
     */
    async captureCookies() {
        if (!this.context) {
            throw new Error('浏览器上下文未创建');
        }

        console.log('\n🔑 [AutoAuth] 捕获 Cookie...');

        const cookies = await this.context.cookies();

        console.log(`✅ [AutoAuth] 捕获到 ${cookies.length} 个 Cookie`);

        // 打印前 5 个 Cookie 的名称
        const cookieNames = cookies.slice(0, 5).map(c => c.name);
        if (cookieNames.length > 0) {
            console.log(`   前 5 个: ${cookieNames.join(', ')}`);
        }

        return cookies;
    }

    /**
     * 保存 Cookie 到文件
     * @param {Array} cookies - Cookie 数组
     * @param {number} [port] - 代理端口（用于文件命名）
     * @returns {Promise<string>} 保存的文件路径
     */
    async saveCookies(cookies, port = null) {
        const pathResolver = getPathResolver();
        const sessionDir = pathResolver.getSessionDir();

        // 确保目录存在
        await fs.mkdir(sessionDir, { recursive: true });

        // 生成文件名
        const filename = port
            ? `session_port_${port}.json`
            : `session_${Date.now()}.json`;
        const filePath = path.join(sessionDir, filename);

        // 保存 Cookie
        const cookieData = {
            cookies: cookies,
            capturedAt: new Date().toISOString(),
            port: port || null,
            source: 'AutoAuthManager'
        };

        await fs.writeFile(filePath, JSON.stringify(cookieData, null, 2), 'utf8');

        console.log(`💾 [AutoAuth] Cookie 已保存到: ${filePath}`);

        return filePath;
    }

    /**
     * 一键执行完整的身份捕获流程
     * @param {number} [port] - 代理端口（可选）
     * @returns {Promise<{success: boolean, cookieCount: number, filePath: string, error?: string}>}
     */
    async captureAuth(port = null) {
        try {
            console.log('\n');
            console.log('═══════════════════════════════════════════════════════════════');
            console.log('  🤖 [AutoAuth] 开始自动身份捕获流程');
            console.log('═══════════════════════════════════════════════════════════════');
            console.log('\n');

            // 1. 启动浏览器
            await this.launchBrowser();

            // 2. 创建上下文（带代理）
            await this.createContext(port);

            // 3. 创建新页面
            await this.createPage();

            // 4. 导航并等待用户操作
            await this.navigateAndWait();

            // 5. 捕获 Cookie
            const cookies = await this.captureCookies();

            // 6. 保存 Cookie
            const filePath = await this.saveCookies(cookies, port);

            console.log('\n');
            console.log('═══════════════════════════════════════════════════════════════');
            console.log('  ✅ [AutoAuth] 身份捕获完成！');
            console.log(`  📊 捕获 Cookie: ${cookies.length} 个`);
            console.log(`  📁 保存位置: ${filePath}`);
            console.log('═══════════════════════════════════════════════════════════════');
            console.log('\n');

            return {
                success: true,
                cookieCount: cookies.length,
                filePath: filePath
            };

        } catch (error) {
            console.error(`\n❌ [AutoAuth] 身份捕获失败: ${error.message}\n`);

            return {
                success: false,
                cookieCount: 0,
                filePath: null,
                error: error.message
            };
        } finally {
            // 清理资源
            await this.cleanup();
        }
    }

    /**
     * 批量捕获多个端口的身份
     * @param {number[]} ports - 端口列表
     * @returns {Promise<Object>} 捕获结果统计
     */
    async captureMultiplePorts(ports) {
        console.log(`\n🎯 [AutoAuth] 批量捕获 ${ports.length} 个端口的身份\n`);

        const results = {
            total: ports.length,
            success: 0,
            failed: 0,
            details: []
        };

        for (const port of ports) {
            console.log(`\n📍 [AutoAuth] 开始捕获端口 ${port}...`);

            const result = await this.captureAuth(port);

            results.details.push({
                port: port,
                ...result
            });

            if (result.success) {
                results.success++;
            } else {
                results.failed++;
            }

            // 端口之间休息 5 秒
            if (ports.indexOf(port) < ports.length - 1) {
                console.log('⏳ 等待 5 秒后继续...');
                await new Promise(resolve => setTimeout(resolve, 5000));
            }
        }

        console.log('\n');
        console.log('═══════════════════════════════════════════════════════════════');
        console.log('  📊 [AutoAuth] 批量捕获完成报告');
        console.log('═══════════════════════════════════════════════════════════════');
        console.log(`  总计: ${results.total} 个端口`);
        console.log(`  成功: ${results.success} 个`);
        console.log(`  失败: ${results.failed} 个`);
        console.log('═══════════════════════════════════════════════════════════════');
        console.log('\n');

        return results;
    }

    /**
     * 清理资源
     */
    async cleanup() {
        if (this.page) {
            try {
                await this.page.close();
                console.log('🧹 [AutoAuth] 页面已关闭');
            } catch (e) {
                // 忽略关闭错误
            }
        }

        if (this.context) {
            try {
                await this.context.close();
                console.log('🧹 [AutoAuth] 上下文已关闭');
            } catch (e) {
                // 忽略关闭错误
            }
        }

        if (this.browser) {
            try {
                await this.browser.close();
                console.log('🧹 [AutoAuth] 浏览器已关闭');
            } catch (e) {
                // 忽略关闭错误
            }
        }

        this.browser = null;
        this.context = null;
        this.page = null;
    }
}

// ============================================================================
// 单例模式辅助函数
// ============================================================================

/**
 * 获取 AutoAuthManager 单例
 * @param {Object} [config={}] - 配置选项
 * @returns {AutoAuthManager}
 */
function getAutoAuthManager(config = {}) {
    if (!_instance) {
        _instance = new AutoAuthManager(config);
    }
    return _instance;
}

/**
 * 重置单例（用于测试）
 */
function resetAutoAuthManager() {
    _instance = null;
}

module.exports = { AutoAuthManager, getAutoAuthManager, resetAutoAuthManager };
