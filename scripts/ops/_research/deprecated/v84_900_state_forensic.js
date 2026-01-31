#!/usr/bin/env node
/**
 * V84.900 - State Data 深度取证工具
 * ====================================
 *
 * 针对 OddsPortal 页面的隐藏状态数据 (State Data) 深度探测
 *
 * 探测动作:
 *   A. 脚本标签扫描 - 查找 __NEXT_DATA__, __STATE__, initial-state 等
 *   B. 隐藏属性审计 - 扫描 div[data-*] 属性
 *   C. 全局变量倾倒 - 检查 window 对象上的状态变量
 *
 * Usage:
 *   DEBUG=pw:api node v84_900_state_forensic.js "<URL>" "[SOURCE_ID]"
 *
 * @file v84_900_state_forensic
 * @version V84.900
 * @since 2026-01-25
 */

'use strict';

const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

// ============================================================================
// CONFIGURATION
// ============================================================================

const FORENSIC_CONFIG = {
    headless: false,
    timeout: 90000,
    slowMo: 50,
    logsPath: path.join(__dirname, '../../logs'),
    targetUrl: 'https://www.oddsportal.com/football/germany/bundesliga-2023-2024/bayern-munich-augsburg-f3e2PS0c/',
    sourceId: '4221909'
};

// ============================================================================
// LOGGING
// ============================================================================

const log = {
    info: (msg) => console.log(`[INFO] ${new Date().toISOString()} - ${msg}`),
    error: (msg) => console.error(`[ERROR] ${new Date().toISOString()} - ${msg}`),
    debug: (msg) => console.log(`[DEBUG] ${new Date().toISOString()} - ${msg}`),
    step: (step, msg) => console.log(`[STEP ${step}] ${msg}`),
    success: (msg) => console.log(`[✓] ${msg}`),
    fail: (msg) => console.log(`[✗] ${msg}`)
};

// ============================================================================
// FORENSIC ACTION A: Script Tag Scanner
// ============================================================================

async function performScriptTagScan(page) {
    log.info("");
    log.info("[动作 A] 脚本标签扫描 - Script Tag Scanner");
    log.info("  目标: 查找 type='application/json' 或包含 __NEXT_DATA__, __STATE__ 的内容");
    log.info("");

    const results = {
        jsonScripts: [],
        nextDataScripts: [],
        stateScripts: [],
        initialPropsScripts: [],
        suspiciousScripts: []
    };

    try {
        // 扫描所有 script 标签
        const scriptAnalysis = await page.evaluate(() => {
            const findings = {
                jsonScripts: [],
                nextDataScripts: [],
                stateScripts: [],
                initialPropsScripts: [],
                suspiciousScripts: []
            };

            const scripts = Array.from(document.querySelectorAll('script'));
            const totalScripts = scripts.length;

            for (let i = 0; i < scripts.length; i++) {
                const script = scripts[i];
                const type = script.type || '';
                const id = script.id || '';
                const className = script.className || '';
                const text = script.textContent || '';

                // 检查 type="application/json"
                if (type === 'application/json') {
                    findings.jsonScripts.push({
                        index: i,
                        id: id || '(none)',
                        className: className || '(none)',
                        contentPreview: text.substring(0, 200),
                        contentLength: text.length,
                        parseSuccess: false,
                        parsedData: null
                    });

                    // 尝试解析 JSON
                    try {
                        const parsed = JSON.parse(text);
                        findings.jsonScripts[findings.jsonScripts.length - 1].parseSuccess = true;
                        findings.jsonScripts[findings.jsonScripts.length - 1].parsedData = parsed;
                    } catch (e) {
                        findings.jsonScripts[findings.jsonScripts.length - 1].parseError = e.message;
                    }
                }

                // 检查 __NEXT_DATA__
                if (id.includes('__NEXT_DATA__') || id.includes('__NEXT')) {
                    findings.nextDataScripts.push({
                        index: i,
                        id: id,
                        contentPreview: text.substring(0, 200),
                        contentLength: text.length
                    });
                }

                // 检查 __STATE__
                if (id.includes('__STATE__') || id.includes('__INITIAL_STATE__')) {
                    findings.stateScripts.push({
                        index: i,
                        id: id,
                        contentPreview: text.substring(0, 200),
                        contentLength: text.length
                    });
                }

                // 检查 initial props
                if (id.includes('initial') || id.includes('props') || id.includes('config')) {
                    findings.initialPropsScripts.push({
                        index: i,
                        id: id,
                        contentPreview: text.substring(0, 200),
                        contentLength: text.length
                    });
                }

                // 检查可疑的长字符串内容
                if (text.length > 1000 && (text.includes('{') || text.includes('['))) {
                    findings.suspiciousScripts.push({
                        index: i,
                        id: id || '(none)',
                        type: type || '(none)',
                        contentLength: text.length,
                        contentPreview: text.substring(0, 200)
                    });
                }
            }

            findings.totalScripts = totalScripts;
            return findings;
        });

        results.jsonScripts = scriptAnalysis.jsonScripts;
        results.nextDataScripts = scriptAnalysis.nextDataScripts;
        results.stateScripts = scriptAnalysis.stateScripts;
        results.initialPropsScripts = scriptAnalysis.initialPropsScripts;
        results.suspiciousScripts = scriptAnalysis.suspiciousScripts;

        // 输出结果
        log.info(`  扫描完成: 共检查 ${scriptAnalysis.totalScripts || 0} 个 script 标签`);
        log.info("");

        if (results.jsonScripts.length > 0) {
            log.success(`  找到 ${results.jsonScripts.length} 个 application/json 脚本`);
            for (const script of results.jsonScripts) {
                log.info(`    ID: ${script.id}, 解析: ${script.parseSuccess ? '✓' : '✗'}, 长度: ${script.contentLength}`);
                if (script.parseSuccess) {
                    // 检查关键词
                    const jsonStr = JSON.stringify(script.parsedData);
                    const keywords = ['pinnacle', 'opening', 'movement', '18', 'bet365'];
                    const foundKeywords = keywords.filter(k => jsonStr.toLowerCase().includes(k.toLowerCase()));
                    if (foundKeywords.length > 0) {
                        log.info(`      关键词匹配: ${foundKeywords.join(', ')}`);
                    }
                }
            }
            log.info("");
        }

        if (results.nextDataScripts.length > 0) {
            log.success(`  找到 ${results.nextDataScripts.length} 个 __NEXT_DATA__ 脚本`);
            for (const script of results.nextDataScripts) {
                log.info(`    ID: ${script.id}, 长度: ${script.contentLength}`);
            }
            log.info("");
        }

        if (results.stateScripts.length > 0) {
            log.success(`  找到 ${results.stateScripts.length} 个 __STATE__ 脚本`);
            for (const script of results.stateScripts) {
                log.info(`    ID: ${script.id}, 长度: ${script.contentLength}`);
            }
            log.info("");
        }

        if (results.suspiciousScripts.length > 0) {
            log.info(`  找到 ${results.suspiciousScripts.length} 个可疑的长字符串脚本`);
            for (const script of results.suspiciousScripts.slice(0, 3)) {
                log.info(`    ID: ${script.id}, 类型: ${script.type}, 长度: ${script.contentLength}`);
            }
            log.info("");
        }

    } catch (e) {
        log.error(`  脚本扫描失败: ${e.message}`);
    }

    return results;
}

// ============================================================================
// FORENSIC ACTION B: Hidden Attributes Audit
// ============================================================================

async function performHiddenAttributesAudit(page) {
    log.info("");
    log.info("[动作 B] 隐藏属性审计 - Hidden Attributes Audit");
    log.info("  目标: 扫描 div[data-*] 属性，寻找序列化的长字符串");
    log.info("");

    const results = {
        dataAttributes: [],
        longDataStrings: [],
        interestingData: []
    };

    try {
        const audit = await page.evaluate(() => {
            const findings = {
                dataAttributes: [],
                longDataStrings: [],
                interestingData: [],
                totalDivs: 0
            };

            // 目标 ID 模式
            const targetIdPatterns = ['app', 'root', 'event', 'match', 'game', 'data', 'state'];
            const divs = Array.from(document.querySelectorAll('div'));
            findings.totalDivs = divs.length;

            for (let i = 0; i < divs.length; i++) {
                const div = divs[i];
                const id = div.id || '';
                const className = div.className || '';

                // 检查 ID 是否匹配目标模式
                const idMatches = targetIdPatterns.some(pattern =>
                    id.toLowerCase().includes(pattern) ||
                    className.toLowerCase().includes(pattern)
                );

                if (!idMatches) continue;

                // 提取所有 data-* 属性
                const dataAttrs = {};
                for (const attr of div.attributes) {
                    if (attr.name.startsWith('data-')) {
                        dataAttrs[attr.name] = attr.value;
                    }
                }

                if (Object.keys(dataAttrs).length > 0) {
                    findings.dataAttributes.push({
                        index: i,
                        id: id || '(none)',
                        className: typeof className === 'string' ? className.substring(0, 50) : '(complex)',
                        dataAttributes: dataAttrs
                    });
                }

                // 检查长字符串属性
                for (const attr of div.attributes) {
                    if (attr.name.startsWith('data-') && attr.value && attr.value.length > 100) {
                        findings.longDataStrings.push({
                            index: i,
                            id: id || '(none)',
                            attributeName: attr.name,
                            valueLength: attr.value.length,
                            valuePreview: attr.value.substring(0, 200)
                        });
                    }
                }

                // 限制检查数量
                if (findings.dataAttributes.length > 50) break;
            }

            return findings;
        });

        results.dataAttributes = audit.dataAttributes;
        results.longDataStrings = audit.longDataStrings;

        log.info(`  审计完成: 检查了 ${audit.totalDivs || 0} 个 div 节点`);
        log.info("");

        if (results.dataAttributes.length > 0) {
            log.success(`  找到 ${results.dataAttributes.length} 个包含 data-* 属性的节点`);

            // 显示前 5 个
            for (const item of results.dataAttributes.slice(0, 5)) {
                log.info(`    节点 #${item.index}: id=${item.id}`);
                for (const [attrName, attrValue] of Object.entries(item.dataAttributes)) {
                    const preview = attrValue.length > 50 ?
                        attrValue.substring(0, 50) + '...' :
                        attrValue;
                    log.info(`      ${attrName}: "${preview}"`);
                }
            }
            log.info("");
        }

        if (results.longDataStrings.length > 0) {
            log.success(`  找到 ${results.longDataStrings.length} 个长字符串 data-* 属性`);

            for (const item of results.longDataStrings) {
                log.info(`    ${item.attributeName} (${item.valueLength} chars)`);

                // 检查关键词
                const keywords = ['pinnacle', 'opening', 'movement', '18', 'bet365', 'json', 'data'];
                const foundKeywords = keywords.filter(k =>
                    item.valuePreview.toLowerCase().includes(k.toLowerCase())
                );

                if (foundKeywords.length > 0) {
                    log.info(`      关键词匹配: ${foundKeywords.join(', ')}`);
                    results.interestingData.push(item);
                }
            }
            log.info("");
        }

    } catch (e) {
        log.error(`  属性审计失败: ${e.message}`);
    }

    return results;
}

// ============================================================================
// FORENSIC ACTION C: Global Variables Dump
// ============================================================================

async function performGlobalVariablesDump(page) {
    log.info("");
    log.info("[动作 C] 全局变量倾倒 - Global Variables Dump");
    log.info("  目标: 检查 window 对象上的状态变量");
    log.info("");

    const results = {
        stateVariables: [],
        configVariables: [],
        dataVariables: [],
        suspiciousVariables: []
    };

    try {
        const globalDump = await page.evaluate(() => {
            const findings = {
                stateVariables: [],
                configVariables: [],
                dataVariables: [],
                suspiciousVariables: []
            };

            // 目标变量名模式
            const statePatterns = ['STATE', 'state', 'INITIAL', 'initial', 'PROPS', 'props'];
            const configPatterns = ['CONFIG', 'config', 'SETTINGS', 'settings'];
            const dataPatterns = ['DATA', 'data', 'STORE', 'store'];

            // 扫描 window 对象属性
            for (const key of Object.keys(window)) {
                const value = window[key];

                // 跳过函数和原生属性
                if (typeof value === 'function') continue;
                if (key.startsWith('_webkit') || key.startsWith('_moz')) continue;

                // 检查状态变量
                if (statePatterns.some(p => key.includes(p))) {
                    findings.stateVariables.push({
                        name: key,
                        type: typeof value,
                        value: typeof value === 'object' ? JSON.stringify(value).substring(0, 200) : String(value).substring(0, 200)
                    });
                }

                // 检查配置变量
                if (configPatterns.some(p => key.includes(p))) {
                    findings.configVariables.push({
                        name: key,
                        type: typeof value,
                        value: typeof value === 'object' ? JSON.stringify(value).substring(0, 200) : String(value).substring(0, 200)
                    });
                }

                // 检查数据变量
                if (dataPatterns.some(p => key.includes(p))) {
                    let valueStr = '';
                    try {
                        valueStr = typeof value === 'object' ? JSON.stringify(value).substring(0, 200) : String(value).substring(0, 200);
                    } catch (e) {
                        valueStr = '[Circular or Complex Object]';
                    }
                    findings.dataVariables.push({
                        name: key,
                        type: typeof value,
                        value: valueStr
                    });
                }

                // 检查可疑的大对象
                if (typeof value === 'object' && value !== null) {
                    let jsonStr = '';
                    try {
                        jsonStr = JSON.stringify(value);
                        if (jsonStr.length > 5000 && key.length < 30) {
                            findings.suspiciousVariables.push({
                                name: key,
                                type: typeof value,
                                size: jsonStr.length,
                                preview: jsonStr.substring(0, 300)
                            });
                        }
                    } catch (e) {
                        // 跳过无法序列化的对象（如 window, document 等）
                    }
                }
            }

            findings.totalWindowProps = Object.keys(window).length;
            return findings;
        });

        results.stateVariables = globalDump.stateVariables;
        results.configVariables = globalDump.configVariables;
        results.dataVariables = globalDump.dataVariables;
        results.suspiciousVariables = globalDump.suspiciousVariables;

        log.info(`  倾倒完成: 检查了 ${globalDump.totalWindowProps || 0} 个 window 属性`);
        log.info("");

        if (results.stateVariables.length > 0) {
            log.success(`  找到 ${results.stateVariables.length} 个状态变量`);
            for (const variable of results.stateVariables) {
                log.info(`    window.${variable.name} (${variable.type})`);
                log.info(`      ${variable.value.substring(0, 100)}...`);
            }
            log.info("");
        }

        if (results.configVariables.length > 0) {
            log.success(`  找到 ${results.configVariables.length} 个配置变量`);
            for (const variable of results.configVariables.slice(0, 3)) {
                log.info(`    window.${variable.name}: ${variable.value.substring(0, 80)}...`);
            }
            log.info("");
        }

        if (results.dataVariables.length > 0) {
            log.success(`  找到 ${results.dataVariables.length} 个数据变量`);
            for (const variable of results.dataVariables.slice(0, 3)) {
                log.info(`    window.${variable.name}: ${variable.value.substring(0, 80)}...`);
            }
            log.info("");
        }

        if (results.suspiciousVariables.length > 0) {
            log.success(`  找到 ${results.suspiciousVariables.length} 个可疑大对象`);
            for (const variable of results.suspiciousVariables) {
                log.info(`    window.${variable.name} (${variable.size} bytes)`);

                // 检查关键词
                const keywords = ['pinnacle', 'opening', 'movement', '18', 'bet365', 'odds'];
                const foundKeywords = keywords.filter(k =>
                    variable.preview.toLowerCase().includes(k.toLowerCase())
                );

                if (foundKeywords.length > 0) {
                    log.info(`      关键词匹配: ${foundKeywords.join(', ')}`);
                }
            }
            log.info("");
        }

    } catch (e) {
        log.error(`  全局变量倾倒失败: ${e.message}`);
    }

    return results;
}

// ============================================================================
// DATA VALIDATION
// ============================================================================

function validateFindings(scriptResults, attrResults, globalResults) {
    log.info("");
    log.info("[数据校验] Data Validation");
    log.info("");

    let totalAnchors = 0;
    let highStabilityAnchors = 0;
    const anchors = [];

    // 检查脚本标签结果
    if (scriptResults.jsonScripts.length > 0) {
        log.info("  [验证] application/json 脚本:");
        for (const script of scriptResults.jsonScripts) {
            if (script.parseSuccess) {
                const jsonStr = JSON.stringify(script.parsedData);
                const keywords = ['pinnacle', 'opening', 'movement', '18', 'timestamp'];
                const found = keywords.filter(k => jsonStr.toLowerCase().includes(k.toLowerCase()));

                if (found.length > 0) {
                    log.success(`    ✓ script#${script.id} 包含关键词: ${found.join(', ')}`);
                    anchors.push({
                        type: 'script',
                        selector: `script#${script.id}`,
                        stability: 'High',
                        keywords: found
                    });
                    totalAnchors++;
                    highStabilityAnchors++;
                }
            }
        }
        log.info("");
    }

    // 检查 data-* 属性结果
    if (attrResults.interestingData.length > 0) {
        log.info("  [验证] data-* 属性:");
        for (const item of attrResults.interestingData) {
            log.success(`    ✓ div${item.id ? '#' + item.id : ''}[${item.attributeName}] 包含关键词`);
            anchors.push({
                type: 'attribute',
                selector: `div${item.id ? '#' + item.id : ''}[${item.attributeName}]`,
                stability: 'Medium',
                keywords: item.valuePreview
            });
            totalAnchors++;
        }
        log.info("");
    }

    // 检查全局变量结果
    if (globalResults.suspiciousVariables.length > 0) {
        log.info("  [验证] 全局变量:");
        for (const variable of globalResults.suspiciousVariables) {
            const keywords = ['pinnacle', 'opening', 'movement', '18', 'odds'];
            const found = keywords.filter(k =>
                variable.preview.toLowerCase().includes(k.toLowerCase())
            );

            if (found.length > 0) {
                log.success(`    ✓ window.${variable.name} 包含关键词: ${found.join(', ')}`);
                anchors.push({
                    type: 'global',
                    selector: `window.${variable.name}`,
                    stability: 'Low',
                    keywords: found
                });
                totalAnchors++;
            }
        }
        log.info("");
    }

    // 结构验证 - 检查时序数组
    log.info("  [验证] 时序结构检查:");
    const hasTemporalStructure = anchors.some(anchor => {
        // 简单检查：是否包含时间戳模式
        return anchor.keywords && (
            Array.isArray(anchor.keywords) &&
            anchor.keywords.some(k => k.includes('timestamp') || k.includes('time'))
        );
    });

    if (hasTemporalStructure) {
        log.success(`    ✓ 检测到时序数据结构`);
    } else {
        log.info(`    ⚠ 未检测到明显的时序数据结构`);
    }
    log.info("");

    return {
        totalAnchors,
        highStabilityAnchors,
        anchors,
        hasTemporalStructure
    };
}

// ============================================================================
// MAIN FORENSIC FUNCTION
// ============================================================================

async function performStateForensic(url, sourceId) {
    log.info("=".repeat(70));
    log.info("V84.900 - State Data 深度取证工具");
    log.info("=".repeat(70));
    log.info(`URL: ${url}`);
    log.info(`Source ID: ${sourceId}`);
    log.info("");

    let browser = null;
    const report = {
        url,
        sourceId,
        timestamp: new Date().toISOString(),
        scriptScan: null,
        attributeAudit: null,
        globalDump: null,
        validation: null
    };

    try {
        // 启动浏览器
        log.step(1, "启动浏览器...");
        browser = await chromium.launch({
            headless: FORENSIC_CONFIG.headless,
            timeout: FORENSIC_CONFIG.timeout,
            slowMo: FORENSIC_CONFIG.slowMo,
            args: [
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-blink-features=AutomationControlled',
                '--window-size=1920,1080'
            ]
        });

        const context = await browser.newContext({
            viewport: { width: 1920, height: 1080 },
            userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        });

        const page = await context.newPage();

        // 反检测
        await page.addInitScript(() => {
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        });

        log.success("浏览器启动完成");
        log.info("");

        // 导航到目标页面
        log.step(2, "导航到目标页面...");
        log.info(`URL: ${url}`);
        await page.goto(url, {
            waitUntil: 'networkidle',
            timeout: FORENSIC_CONFIG.timeout
        });
        await page.waitForTimeout(5000);
        log.success("页面加载完成");
        log.info("");

        // 执行三个探测动作
        log.step(3, "执行探测动作...");
        log.info("");

        // 动作 A: 脚本标签扫描
        report.scriptScan = await performScriptTagScan(page);

        // 动作 B: 隐藏属性审计
        report.attributeAudit = await performHiddenAttributesAudit(page);

        // 动作 C: 全局变量倾倒
        report.globalDump = await performGlobalVariablesDump(page);

        // 数据校验
        log.step(4, "数据校验...");
        log.info("");
        report.validation = validateFindings(
            report.scriptScan,
            report.attributeAudit,
            report.globalDump
        );

        // 保存报告
        const reportPath = path.join(FORENSIC_CONFIG.logsPath, `v84_900_forensic_${sourceId}.json`);
        fs.writeFileSync(reportPath, JSON.stringify(report, null, 2), 'utf8');
        log.info(`  报告已保存: ${reportPath}`);
        log.info("");

        // 截图
        const screenshotPath = path.join(FORENSIC_CONFIG.logsPath, `v84_900_screenshot_${sourceId}.png`);
        await page.screenshot({ path: screenshotPath, fullPage: true });
        log.info(`  截图已保存: ${screenshotPath}`);
        log.info("");

        // 清理
        await context.close();
        await browser.close();

        // 最终汇报
        log.info("=".repeat(70));
        log.info("[V84.900] State Discovery COMPLETE");
        log.info("=".repeat(70));
        log.info(`Data Found: ${report.validation.totalAnchors > 0 ? 'YES' : 'NO'}`);
        log.info(`Total Anchors: ${report.validation.totalAnchors}`);
        log.info(`High Stability: ${report.validation.highStabilityAnchors}`);
        log.info("");

        if (report.validation.totalAnchors > 0) {
            log.info("Entry Points:");
            for (const anchor of report.validation.anchors) {
                log.info(`  - ${anchor.selector} (Stability: ${anchor.stability})`);
                if (anchor.keywords && Array.isArray(anchor.keywords)) {
                    log.info(`    Keywords: ${anchor.keywords.join(', ')}`);
                }
            }
            log.info("");
        }

        log.info(`Report: ${reportPath}`);
        log.info("=".repeat(70));

        return report;

    } catch (error) {
        log.error(`取证失败: ${error.message}`);
        if (browser) {
            try { await browser.close(); } catch (e) {}
        }
        throw error;
    }
}

// ============================================================================
// CLI ENTRY POINT
// ============================================================================

if (require.main === module) {
    const args = process.argv.slice(2);
    const url = args[0] || FORENSIC_CONFIG.targetUrl;
    const sourceId = args[1] || FORENSIC_CONFIG.sourceId;

    performStateForensic(url, sourceId)
        .then(() => process.exit(0))
        .catch(error => {
            console.error('[FATAL]', error);
            process.exit(1);
        });
}

module.exports = { performStateForensic };
