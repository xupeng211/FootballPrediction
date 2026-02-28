/**
 * V173-PROXY-OVERHAUL: 诊断实验脚本
 * ===================================
 *
 * 目的: 确认是 IP 被封还是 Cookie 被标记
 *
 * 实验设计:
 * - 步骤 A: 纯净 IP 测试 (禁用 Cookie)
 * - 步骤 B: 新 IP + 旧 Cookie 测试
 *
 * @module scripts/ops/diagnostic_experiment
 * @version V173.0.0
 */

'use strict';

const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

// ============================================================================
// 配置
// ============================================================================

const CONFIG = {
    // 使用之前没用过的端口
    testPort: process.env.TEST_PORT || 7905,
    proxyHost: process.env.PROXY_HOST || '172.25.16.1',

    // 测试比赛 ID (意甲比赛)
    testMatchId: '4513266',  // 使用一个真实的 FotMob match ID

    // Cookie 状态文件路径
    cookiePath: '/app/data/browser_profile/browser_state.json',
    cookieBackupPath: '/app/data/browser_profile/browser_state.json.old',

    // User-Agent
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36'
};

// ============================================================================
// 实验执行器
// ============================================================================

class DiagnosticExperiment {
    constructor() {
        this.results = [];
    }

    log(message, type = 'info') {
        const timestamp = new Date().toISOString();
        const prefix = {
            'info': '📋',
            'success': '✅',
            'error': '❌',
            'warn': '⚠️',
            'experiment': '🔬'
        }[type] || '📋';
        console.log(`${prefix} [${timestamp}] ${message}`);
    }

    /**
     * 步骤 A: 纯净 IP 测试 (禁用 Cookie)
     */
    async runExperimentA() {
        this.log('=== 实验 A: 纯净 IP 测试 ===', 'experiment');
        this.log(`使用端口: ${CONFIG.testPort}`, 'info');
        this.log('Cookie 状态: 禁用', 'info');

        let browser, context, page;
        try {
            browser = await chromium.launch({
                headless: true,
                proxy: { server: `http://${CONFIG.proxyHost}:${CONFIG.testPort}` },
                args: ['--disable-blink-features=AutomationControlled']
            });

            // 不加载任何 Cookie - 纯净会话
            context = await browser.newContext({
                userAgent: CONFIG.userAgent,
                viewport: { width: 1920, height: 1080 },
                locale: 'en-US',
                timezoneId: 'America/New_York'
            });

            page = await context.newPage();

            // 访问 FotMob 首页预热
            this.log('访问 FotMob 首页预热...', 'info');
            await page.goto('https://www.fotmob.com/', {
                waitUntil: 'domcontentloaded',
                timeout: 30000
            });
            await page.waitForTimeout(3000);

            // 尝试调用 API
            this.log('尝试获取比赛数据...', 'info');
            const apiData = await page.evaluate(async (matchId) => {
                try {
                    const res = await fetch(`https://www.fotmob.com/api/matchDetails?matchId=${matchId}`, {
                        credentials: 'include'
                    });
                    const data = await res.json();
                    return {
                        success: true,
                        size: JSON.stringify(data).length,
                        hasContent: !!data?.content,
                        hasError: !!data?.error,
                        errorType: data?.error || data?.code || null
                    };
                } catch (e) {
                    return { success: false, error: e.message };
                }
            }, CONFIG.testMatchId);

            await browser.close();
            browser = null;

            // 分析结果
            if (apiData.success && apiData.hasContent && apiData.size > 5000) {
                this.log(`实验 A 成功! 数据大小: ${apiData.size} bytes`, 'success');
                return { experiment: 'A', result: 'SUCCESS', dataSize: apiData.size };
            } else if (apiData.hasError || apiData.errorType) {
                this.log(`实验 A 失败 - API 返回错误: ${apiData.errorType}`, 'error');
                return { experiment: 'A', result: 'BLOCKED', error: apiData.errorType };
            } else {
                this.log(`实验 A 失败 - 数据太小: ${apiData.size} bytes`, 'error');
                return { experiment: 'A', result: 'SMALL_DATA', dataSize: apiData.size };
            }

        } catch (error) {
            if (browser) await browser.close();
            this.log(`实验 A 异常: ${error.message}`, 'error');
            return { experiment: 'A', result: 'ERROR', error: error.message };
        }
    }

    /**
     * 步骤 B: 新 IP + 旧 Cookie 测试
     */
    async runExperimentB() {
        this.log('=== 实验 B: 新 IP + 旧 Cookie 测试 ===', 'experiment');
        this.log(`使用端口: ${CONFIG.testPort}`, 'info');
        this.log('Cookie 状态: 加载旧 Cookie', 'info');

        // 检查 Cookie 文件是否存在
        if (!fs.existsSync(CONFIG.cookiePath)) {
            this.log('Cookie 文件不存在，跳过实验 B', 'warn');
            return { experiment: 'B', result: 'SKIPPED', reason: 'No cookie file' };
        }

        let browser, context, page;
        try {
            browser = await chromium.launch({
                headless: true,
                proxy: { server: `http://${CONFIG.proxyHost}:${CONFIG.testPort}` },
                args: ['--disable-blink-features=AutomationControlled']
            });

            // 加载旧 Cookie
            const cookieState = JSON.parse(fs.readFileSync(CONFIG.cookiePath, 'utf8'));
            this.log(`加载 Cookie: ${cookieState.cookies?.length || 0} 个`, 'info');

            context = await browser.newContext({
                userAgent: CONFIG.userAgent,
                viewport: { width: 1920, height: 1080 },
                locale: 'en-US',
                timezoneId: 'America/New_York',
                storageState: cookieState
            });

            page = await context.newPage();

            // 访问 FotMob 首页预热
            this.log('访问 FotMob 首页预热...', 'info');
            await page.goto('https://www.fotmob.com/', {
                waitUntil: 'domcontentloaded',
                timeout: 30000
            });
            await page.waitForTimeout(3000);

            // 尝试调用 API
            this.log('尝试获取比赛数据...', 'info');
            const apiData = await page.evaluate(async (matchId) => {
                try {
                    const res = await fetch(`https://www.fotmob.com/api/matchDetails?matchId=${matchId}`, {
                        credentials: 'include'
                    });
                    const data = await res.json();
                    return {
                        success: true,
                        size: JSON.stringify(data).length,
                        hasContent: !!data?.content,
                        hasError: !!data?.error,
                        errorType: data?.error || data?.code || null
                    };
                } catch (e) {
                    return { success: false, error: e.message };
                }
            }, CONFIG.testMatchId);

            await browser.close();
            browser = null;

            // 分析结果
            if (apiData.success && apiData.hasContent && apiData.size > 5000) {
                this.log(`实验 B 成功! 数据大小: ${apiData.size} bytes`, 'success');
                return { experiment: 'B', result: 'SUCCESS', dataSize: apiData.size };
            } else if (apiData.hasError || apiData.errorType) {
                this.log(`实验 B 失败 - API 返回错误: ${apiData.errorType}`, 'error');
                return { experiment: 'B', result: 'BLOCKED', error: apiData.errorType };
            } else {
                this.log(`实验 B 失败 - 数据太小: ${apiData.size} bytes`, 'error');
                return { experiment: 'B', result: 'SMALL_DATA', dataSize: apiData.size };
            }

        } catch (error) {
            if (browser) await browser.close();
            this.log(`实验 B 异常: ${error.message}`, 'error');
            return { experiment: 'B', result: 'ERROR', error: error.message };
        }
    }

    /**
     * 分析实验结果
     */
    analyzeResults(resultA, resultB) {
        this.log('', 'info');
        this.log('═'.repeat(60), 'info');
        this.log('📊 实验结论分析', 'experiment');
        this.log('═'.repeat(60), 'info');
        this.log(`实验 A (纯净 IP):     ${resultA.result}`, 'info');
        this.log(`实验 B (新 IP+旧 Cookie): ${resultB.result}`, 'info');
        this.log('', 'info');

        // 诊断逻辑
        if (resultA.result === 'SUCCESS' && resultB.result !== 'SUCCESS') {
            this.log('🔍 诊断结论: COOKIE 被标记!', 'error');
            this.log('   原因: 纯净 IP 成功，但加载旧 Cookie 后失败', 'warn');
            this.log('   建议: 清除 browser_state.json，重新生成会话', 'warn');
            return {
                diagnosis: 'COOKIE_POISONED',
                action: 'CLEAR_COOKIE',
                confidence: 'HIGH'
            };
        } else if (resultA.result !== 'SUCCESS' && resultB.result !== 'SUCCESS') {
            this.log('🔍 诊断结论: IP 被封 (或 FotMob 全局防护)', 'error');
            this.log('   原因: 无论是否使用 Cookie 都失败', 'warn');
            this.log('   建议: 更换代理端口或等待冷却', 'warn');
            return {
                diagnosis: 'IP_BLOCKED',
                action: 'CHANGE_PROXY',
                confidence: 'HIGH'
            };
        } else if (resultA.result === 'SUCCESS' && resultB.result === 'SUCCESS') {
            this.log('🔍 诊断结论: 系统正常!', 'success');
            this.log('   建议: 可能是之前代理端口有问题', 'info');
            return {
                diagnosis: 'SYSTEM_OK',
                action: 'CONTINUE',
                confidence: 'HIGH'
            };
        } else {
            this.log('🔍 诊断结论: 不确定', 'warn');
            this.log('   建议: 需要更多实验', 'warn');
            return {
                diagnosis: 'INCONCLUSIVE',
                action: 'MORE_TESTS',
                confidence: 'LOW'
            };
        }
    }

    /**
     * 执行完整诊断
     */
    async runFullDiagnosis() {
        this.log('═'.repeat(60), 'experiment');
        this.log('🔬 V173 诊断实验开始', 'experiment');
        this.log('═'.repeat(60), 'experiment');

        const resultA = await this.runExperimentA();
        const resultB = await this.runExperimentB();
        const diagnosis = this.analyzeResults(resultA, resultB);

        this.log('', 'info');
        this.log('═'.repeat(60), 'experiment');
        this.log('🔬 诊断实验完成', 'experiment');
        this.log('═'.repeat(60), 'experiment');

        return diagnosis;
    }
}

// ============================================================================
// 主函数
// ============================================================================

async function main() {
    const experiment = new DiagnosticExperiment();
    const diagnosis = await experiment.runFullDiagnosis();

    // 根据诊断结果执行自动修复
    if (diagnosis.action === 'CLEAR_COOKIE') {
        console.log('');
        console.log('🔧 执行自动修复: 备份并清除 Cookie...');
        if (fs.existsSync(CONFIG.cookiePath)) {
            fs.renameSync(CONFIG.cookiePath, CONFIG.cookieBackupPath);
            console.log('✅ Cookie 已备份到: ' + CONFIG.cookieBackupPath);
        }
    }

    process.exit(diagnosis.diagnosis === 'SYSTEM_OK' ? 0 : 1);
}

// 导出
module.exports = { DiagnosticExperiment };

// 直接运行
if (require.main === module) {
    main().catch(console.error);
}
