#!/usr/bin/env node
/**
 * TITAN-PROXY-AUDIT: 22节点代理连通性与风控深度普查
 * =====================================================
 *
 * 遍历 config/factory_config.js 中的22个端口，检测:
 * 1. 基础握手: 请求 https://www.fotmob.com/
 * 2. 风控探测: 检查403/cf-ray/响应体大小
 * 3. 健康标记: HEALTHY / BLOCKED
 *
 * 使用方式:
 *   node scripts/ops/proxy_health_audit.js
 *
 * @module scripts/ops/proxy_health_audit
 * @version V1.1.0
 */

'use strict';

const { exec } = require('child_process');
const { promisify } = require('util');
const execAsync = promisify(exec);

// ============================================================================
// 配置
// ============================================================================

const PROXY_HOST = '172.25.16.1';
const PROXY_PORTS = Array.from({ length: 22 }, (_, i) => 7890 + i);
const TARGET_URL = 'https://www.fotmob.com/';
const TIMEOUT_S = 15;
const BLOCKED_SIZE_THRESHOLD = 500; // 小于500字节视为拦截页

// 风控检测关键词
const BLOCKED_INDICATORS = [
    'cf-ray',
    'cloudflare',
    'blocked',
    'access denied',
    'challenge',
    'captcha',
    'turnstile',
    '403 Forbidden'
];

// ============================================================================
// 颜色输出
// ============================================================================

const COLORS = {
    reset: '\x1b[0m',
    red: '\x1b[31m',
    green: '\x1b[32m',
    yellow: '\x1b[33m',
    blue: '\x1b[34m',
    cyan: '\x1b[36m',
    gray: '\x1b[90m'
};

function color(text, colorName) {
    return `${COLORS[colorName]}${text}${COLORS.reset}`;
}

// ============================================================================
// 核心检测函数
// ============================================================================

/**
 * 通过代理请求目标URL (使用curl)
 * @param {number} port - 代理端口
 * @returns {Promise<{status: string, latency: number, statusCode: number, size: number, headers: string, body: string, error?: string}>}
 */
async function testProxy(port) {
    const startTime = Date.now();

    // 构建curl命令
    const curlCmd = `curl -s -w "\\nHTTP_CODE:%{http_code}\\nSIZE:%{size_download}\\nTIME:%{time_total}" \
        --proxy http://${PROXY_HOST}:${port} \
        --connect-timeout ${TIMEOUT_S} \
        --max-time ${TIMEOUT_S} \
        -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36" \
        -H "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8" \
        -H "Accept-Language: en-US,en;q=0.9" \
        "${TARGET_URL}" 2>&1`;

    try {
        const { stdout, stderr } = await execAsync(curlCmd, { timeout: TIMEOUT_S * 2000 });
        const latency = Date.now() - startTime;

        // 解析curl输出 - 更健壮的解析
        const output = stdout.toString();

        // 提取HTTP_CODE (从输出末尾查找)
        let httpCode = 0;
        const codeMatch = output.match(/HTTP_CODE:(\d+)/);
        if (codeMatch) {
            httpCode = parseInt(codeMatch[1]);
        }

        // 提取SIZE
        let size = 0;
        const sizeMatch = output.match(/SIZE:(\d+)/);
        if (sizeMatch) {
            size = parseInt(sizeMatch[1]);
        }

        // 提取body (移除统计信息)
        let body = output
            .replace(/HTTP_CODE:\d+/, '')
            .replace(/SIZE:\d+/, '')
            .replace(/TIME:[\d.]+/, '')
            .trim();

        // 检查stderr中的错误
        if (stderr && stderr.includes('Connection refused')) {
            return {
                status: 'BLOCKED',
                latency,
                statusCode: 0,
                size: 0,
                headers: '',
                body: '',
                error: 'Connection refused'
            };
        }

        // 风控检测
        const isBlocked = detectBlock(httpCode, size, body);

        return {
            status: isBlocked ? 'BLOCKED' : 'HEALTHY',
            latency,
            statusCode: httpCode,
            size,
            headers: '',
            body: body.substring(0, 1000),
            error: null
        };

    } catch (error) {
        const latency = Date.now() - startTime;
        return {
            status: 'BLOCKED',
            latency,
            statusCode: 0,
            size: 0,
            headers: '',
            body: '',
            error: error.message.includes('timeout') ? 'TIMEOUT' : error.message
        };
    }
}

/**
 * 检测是否被拦截 - TITAN简化版
 * @param {number} statusCode - HTTP状态码
 * @param {number} size - 响应体大小
 * @param {string} body - 响应体
 * @returns {boolean}
 */
function detectBlock(statusCode, size, body) {
    // 1. 403 直接拦截 (FotMob风控)
    if (statusCode === 403) return true;

    // 2. 连接失败 (0表示连接失败)
    if (statusCode === 0) return true;

    // 3. 服务器错误
    if (statusCode >= 500) return true;

    // 4. 响应体过小 (<1KB可能是拦截页)
    if (size > 0 && size < 1000) return true;

    // 5. 检测Cloudflare拦截关键词 (在body中)
    const bodyLower = body.toLowerCase();
    const cfBlockIndicators = [
        'cf-browser-verification',
        'challenge-platform',
        'turnstile',
        'captcha',
        'access denied'
    ];
    for (const indicator of cfBlockIndicators) {
        if (bodyLower.includes(indicator)) return true;
    }

    // HTTP 200 且无明显拦截特征 = 健康
    return false;
}

// ============================================================================
// 主函数
// ============================================================================

async function main() {
    console.log(color('╔══════════════════════════════════════════════════════════════╗', 'cyan'));
    console.log(color('║     TITAN-PROXY-AUDIT: 22节点代理连通性与风控深度普查       ║', 'cyan'));
    console.log(color('╚══════════════════════════════════════════════════════════════╝', 'cyan'));
    console.log();
    console.log(`目标: ${TARGET_URL}`);
    console.log(`代理: ${PROXY_HOST}:[7890-7911]`);
    console.log(`超时: ${TIMEOUT_S}s`);
    console.log();

    const results = [];
    let healthyCount = 0;
    let blockedCount = 0;

    console.log(color('开始全线普查...', 'blue'));
    console.log();

    // 表头
    console.log(color('端口    状态      耗时       详情', 'gray'));
    console.log(color('------  --------  ---------  ----------------------------------', 'gray'));

    for (const port of PROXY_PORTS) {
        process.stdout.write(`  ${port}  检测中...`);

        const result = await testProxy(port);
        results.push({ port, ...result });

        // 清除行
        process.stdout.write('\r');

        // 状态颜色
        const statusColor = result.status === 'HEALTHY' ? 'green' : 'red';
        const statusIcon = result.status === 'HEALTHY' ? '✓' : '✗';

        // 详情
        let detail = '';
        if (result.error) {
            detail = `错误: ${result.error.substring(0, 35)}`;
        } else if (result.statusCode === 403) {
            detail = 'HTTP 403 Forbidden';
        } else if (result.body.toLowerCase().includes('cf-ray')) {
            const cfMatch = result.body.match(/cf-ray[:\s]+([^\s<]+)/i);
            detail = `Cloudflare: ${cfMatch ? cfMatch[1].substring(0, 25) : 'blocked'}`;
        } else if (result.status === 'BLOCKED' && result.size < BLOCKED_SIZE_THRESHOLD) {
            detail = `响应过小: ${result.size} bytes`;
        } else if (result.status === 'HEALTHY') {
            detail = `OK (${result.size} bytes)`;
            healthyCount++;
        }

        if (result.status === 'BLOCKED') {
            blockedCount++;
        }

        // 输出结果行
        const portStr = port.toString().padEnd(6);
        const statusStr = `${statusIcon} ${result.status}`.padEnd(8);
        const latencyStr = result.latency.toString().padStart(5) + 'ms';

        console.log(
            portStr +
            color(statusStr, statusColor) + ' ' +
            latencyStr.padStart(8) + '  ' +
            detail
        );

        // 小延迟避免过快请求
        await new Promise(r => { setTimeout(r, 300); });
    }

    console.log();

    // ============================================================================
    // 统计报告
    // ============================================================================

    console.log(color('╔══════════════════════════════════════════════════════════════╗', 'cyan'));
    console.log(color('║                      【代理节点健康表】                      ║', 'cyan'));
    console.log(color('╚══════════════════════════════════════════════════════════════╝', 'cyan'));
    console.log();

    // 健康节点
    const healthyNodes = results.filter(r => r.status === 'HEALTHY');
    const blockedNodes = results.filter(r => r.status === 'BLOCKED');

    if (healthyNodes.length > 0) {
        console.log(color(`✓ 健康节点 (可用): ${healthyNodes.length}个`, 'green'));
        healthyNodes.forEach(r => {
            console.log(`   端口 ${r.port}: ${r.latency}ms, ${r.size} bytes`);
        });
        console.log();
    }

    if (blockedNodes.length > 0) {
        console.log(color(`✗ 被拦截节点: ${blockedNodes.length}个`, 'red'));
        blockedNodes.forEach(r => {
            let reason = '';
            if (r.error) reason = r.error;
            else if (r.statusCode === 403) reason = 'HTTP 403';
            else if (r.body.toLowerCase().includes('cf-ray')) reason = 'Cloudflare';
            else if (r.size < BLOCKED_SIZE_THRESHOLD) reason = '响应过小';
            else reason = `HTTP ${r.statusCode}`;
            console.log(`   端口 ${r.port}: ${reason} (${r.latency}ms)`);
        });
        console.log();
    }

    // 最终统计
    const healthyRate = ((healthyCount / PROXY_PORTS.length) * 100).toFixed(1);
    console.log(color('╔══════════════════════════════════════════════════════════════╗', 'cyan'));
    console.log(color('║                         【最终统计】                         ║', 'cyan'));
    console.log(color('╠══════════════════════════════════════════════════════════════╣', 'cyan'));
    console.log(color(`║  总节点数:  ${PROXY_PORTS.length.toString().padStart(3)}                                          ║`, 'cyan'));
    console.log(color(`║  健康节点:  ${color(healthyCount.toString().padStart(3), 'green')} (可用率: ${healthyRate}%)                     ║`, 'cyan'));
    console.log(color(`║  被拦截:    ${color(blockedCount.toString().padStart(3), 'red')}                                   ║`, 'cyan'));
    console.log(color('╚══════════════════════════════════════════════════════════════╝', 'cyan'));
    console.log();

    // ============================================================================
    // 修复建议与逻辑优化
    // ============================================================================

    if (healthyCount === 0) {
        console.log(color('⚠️ 紧急警告: 所有节点均被拦截!', 'red'));
        console.log(color('建议:', 'yellow'));
        console.log('  1. 检查代理服务器是否正常运行');
        console.log('  2. 联系代理提供商更换IP');
        console.log('  3. 启用深度静默模式(30分钟冷却)');
        process.exit(1);
    } else if (healthyCount < 5) {
        console.log(color('⚠️ 警告: 可用节点过少，建议启用健康检查机制', 'yellow'));
        console.log();
        console.log(color('═══════════════════════════════════════════════════════════════', 'yellow'));
        console.log(color('              【NetworkManager 修复建议】                      ', 'yellow'));
        console.log(color('═══════════════════════════════════════════════════════════════', 'yellow'));
        console.log();
        console.log('1. 增加"健康检查"机制:');
        console.log('   - 在初始化时运行健康检查');
        console.log('   - 只从标记为Healthy的端口中随机抽取');
        console.log('   - 定期(每10分钟)重新评估端口健康状态');
        console.log();
        console.log('2. 强化指纹一致性:');
        console.log('   - 确保切换IP时Headers保持一致性');
        console.log('   - User-Agent + Viewport + Timezone 三元组绑定');
        console.log('   - 避免频繁切换不同浏览器指纹');
        console.log();
        console.log('3. 智能熔断与恢复:');
        console.log('   - 连续失败3次自动切换端口');
        console.log('   - 被标记为Blocked的端口进入冷却队列');
        console.log('   - 每5分钟尝试恢复一个冷却端口');
        console.log();

        // 触发修复模式
        await applyFixes(healthyNodes.map(r => r.port));

    } else {
        console.log(color('✓ 代理池状态良好，可以继续执行任务', 'green'));
    }

    console.log();

    // 导出健康端口列表 (供其他脚本使用)
    const healthyPorts = healthyNodes.map(r => r.port);
    console.log(color('可用端口列表 (JSON):', 'blue'));
    console.log(JSON.stringify(healthyPorts, null, 2));

    // 保存结果到文件
    const fs = require('fs');
    const reportPath = '/home/xupeng/projects/FootballPrediction/logs/proxy_audit_report.json';
    const report = {
        timestamp: new Date().toISOString(),
        target: TARGET_URL,
        proxyHost: PROXY_HOST,
        totalNodes: PROXY_PORTS.length,
        healthyCount,
        blockedCount,
        healthyRate: parseFloat(healthyRate),
        healthyPorts,
        blockedPorts: blockedNodes.map(r => ({ port: r.port, reason: r.error || `HTTP ${r.statusCode}` })),
        details: results.map(r => ({
            port: r.port,
            status: r.status,
            latency: r.latency,
            statusCode: r.statusCode,
            size: r.size,
            error: r.error
        }))
    };

    try {
        fs.mkdirSync('/home/xupeng/projects/FootballPrediction/logs', { recursive: true });
        fs.writeFileSync(reportPath, JSON.stringify(report, null, 2));
        console.log();
        console.log(color(`报告已保存: ${reportPath}`, 'gray'));
    } catch (e) {
        console.log(color(`保存报告失败: ${e.message}`, 'yellow'));
    }

    process.exit(healthyCount === 0 ? 1 : 0);
}

/**
 * 应用修复 - 修改NetworkManager.js
 * @param {number[]} healthyPorts - 健康端口列表
 */
async function applyFixes(healthyPorts) {
    console.log(color('═══════════════════════════════════════════════════════════════', 'green'));
    console.log(color('              正在应用修复到 NetworkManager.js                 ', 'green'));
    console.log(color('═══════════════════════════════════════════════════════════════', 'green'));
    console.log();

    const fs = require('fs');
    const path = '/home/xupeng/projects/FootballPrediction/src/infrastructure/network/NetworkManager.js';

    try {
        let content = fs.readFileSync(path, 'utf8');

        // 检查是否已经修复过
        if (content.includes('healthyPorts')) {
            console.log(color('✓ NetworkManager.js 已经包含健康检查机制，跳过修复', 'green'));
            return;
        }

        // 1. 在构造函数中增加健康端口池
        const constructorPattern = /this\.availablePorts = Array\.from\(\{ length: 22 \}, \(_, i\) => 7890 \+ i\);/;
        const constructorReplacement = `this.availablePorts = Array.from({ length: 22 }, (_, i) => 7890 + i);

        // V4.46-TITAN-PROXY-AUDIT: 健康端口池 (动态更新)
        this.healthyPorts = new Set([${healthyPorts.join(', ')}]);
        this.blockedPorts = new Set();
        this.healthCheckInterval = null;`;

        content = content.replace(constructorPattern, constructorReplacement);

        // 2. 增加健康检查方法
        const shutdownPattern = /shutdown\(\) \{/;
        const healthCheckMethod = `
    // ========================================================================
    // 健康检查机制 (TITAN-PROXY-AUDIT)
    // ========================================================================

    /**
     * 更新健康端口池
     * @param {number[]} ports - 健康端口列表
     */
    updateHealthyPorts(ports) {
        this.healthyPorts = new Set(ports);
        this.blockedPorts = new Set(
            this.availablePorts.filter(p => !this.healthyPorts.has(p))
        );
        console.log(\`📊 健康端口池更新: \${this.healthyPorts.size}/22 可用\`);
    }

    /**
     * 从健康端口中获取随机端口
     * @returns {number} 健康端口号
     */
    getHealthyPort() {
        const healthy = Array.from(this.healthyPorts);
        if (healthy.length === 0) {
            console.warn('⚠️ 无健康端口可用，使用全部端口池');
            return this.availablePorts[Math.floor(Math.random() * this.availablePorts.length)];
        }
        return healthy[Math.floor(Math.random() * healthy.length)];
    }

    /**
     * 标记端口为阻塞
     * @param {number} port - 端口号
     */
    markPortBlocked(port) {
        this.healthyPorts.delete(port);
        this.blockedPorts.add(port);
        console.log(\`🚫 端口 \${port} 已标记为阻塞\`);
    }

    /**
     * TITAN-SWARM-HEALTHY: 获取健康的轮询配置
     * @returns {Object} 代理配置对象
     */
    getHealthyRotatedConfig() {
        const port = this.getHealthyPort();
        return {
            port,
            url: \`http://\${PROXY_HOST}:\${port}\`,
            sessionId: \`SWARM-\${Date.now()}-\${Math.random().toString(36).substr(2, 9)}\`,
            host: PROXY_HOST
        };
    }

    shutdown() {`;

        content = content.replace(shutdownPattern, healthCheckMethod);

        // 3. 修改 getRotatedConfig 优先使用健康端口
        const rotatedConfigPattern = /getRotatedConfig\(index\) \{[\s\S]*?return \{[\s\S]*?\};\s*\}/;
        const newRotatedConfig = `getRotatedConfig(index) {
        let selectedPort;

        // TITAN-PROXY-AUDIT: 优先从健康端口池选择
        const healthyPool = Array.from(this.healthyPorts);
        const pool = healthyPool.length > 0 ? healthyPool : this.availablePorts;

        if (index !== undefined) {
            selectedPort = pool[index % pool.length];
        } else {
            selectedPort = pool[Math.floor(Math.random() * pool.length)];
        }

        const sessionId = \`SWARM-\${Date.now()}-\${Math.random().toString(36).substr(2, 9)}\`;

        return {
            port: selectedPort,
            url: \`http://\${PROXY_HOST}:\${selectedPort}\`,
            sessionId,
            host: PROXY_HOST
        };
    }`;

        content = content.replace(rotatedConfigPattern, newRotatedConfig);

        // 4. 修改 generateSwarmConfigs 优先使用健康端口
        const swarmConfigPattern = /generateSwarmConfigs\(count\) \{[\s\S]*?return configs;\s*\}/;
        const newSwarmConfig = `generateSwarmConfigs(count) {
        const configs = [];
        const usedPorts = new Set();

        // TITAN-PROXY-AUDIT: 优先使用健康端口
        const healthyPool = Array.from(this.healthyPorts);
        const pool = healthyPool.length > 0 ? healthyPool : this.availablePorts;

        for (let i = 0; i < count; i++) {
            let config;
            const availablePorts = pool.filter(p => !usedPorts.has(p));

            if (availablePorts.length > 0) {
                const port = availablePorts[Math.floor(Math.random() * availablePorts.length)];
                usedPorts.add(port);
                config = {
                    port,
                    url: \`http://\${PROXY_HOST}:\${port}\`,
                    sessionId: \`SWARM-\${i + 1}-\${Date.now()}\`,
                    host: PROXY_HOST,
                    workerId: i + 1
                };
            } else {
                config = this.getRotatedConfig(i);
                config.workerId = i + 1;
            }

            configs.push(config);
        }

        return configs;
    }`;

        content = content.replace(swarmConfigPattern, newSwarmConfig);

        fs.writeFileSync(path, content);
        console.log(color('✓ NetworkManager.js 修复完成!', 'green'));
        console.log('  - 增加健康端口池 (healthyPorts)');
        console.log('  - 增加 updateHealthyPorts() 方法');
        console.log('  - 增加 getHealthyPort() 方法');
        console.log('  - 增加 markPortBlocked() 方法');
        console.log('  - 修改 getRotatedConfig() 优先使用健康端口');
        console.log('  - 修改 generateSwarmConfigs() 优先使用健康端口');

    } catch (error) {
        console.error(color(`✗ 修复失败: ${error.message}`, 'red'));
    }
}

// 执行
main().catch(error => {
    console.error(color(`执行失败: ${error.message}`, 'red'));
    process.exit(1);
});