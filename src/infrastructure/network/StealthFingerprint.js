/**
 * StealthFingerprint - V4.46 隐身指纹生成器
 * ==========================================
 *
 * 从 ProductionHarvester 剥离的隐身指纹逻辑
 * 统一管理浏览器指纹、UA池、视口配置
 *
 * @module infrastructure/network/StealthFingerprint
 * @version V4.46.0
 */

'use strict';

// ============================================================================
// V180: 深度隐身配置 - 完整硬件指纹
// ============================================================================

/**
 * V185: WebGL 渲染器池 - 用于指纹随机化
 */
const WEBGL_RENDERER_POOL = [
    'ANGLE (AMD, AMD Radeon(TM) Graphics (0x000013C0) Direct3D11 vs_5_0 ps_5_0, D3D11)',
    'ANGLE (NVIDIA, NVIDIA GeForce GTX 1660 (0x00002183) Direct3D11 vs_5_0 ps_5_0, D3D11)',
    'ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 (0x00002503) Direct3D11 vs_5_0 ps_5_0, D3D11)',
    'ANGLE (NVIDIA, NVIDIA GeForce RTX 3070 (0x00002484) Direct3D11 vs_5_0 ps_5_0, D3D11)',
    'ANGLE (NVIDIA, NVIDIA GeForce GTX 1080 (0x00001B80) Direct3D11 vs_5_0 ps_5_0, D3D11)',
    'ANGLE (Intel, Intel(R) UHD Graphics 630 (0x00003E9B) Direct3D11 vs_5_0 ps_5_0, D3D11)',
    'ANGLE (Intel, Intel(R) Iris(R) Xe Graphics (0x000049A5) Direct3D11 vs_5_0 ps_5_0, D3D11)',
    'ANGLE (AMD, AMD Radeon RX 580 Series (0x000067DF) Direct3D11 vs_5_0 ps_5_0, D3D11)'
];

/**
 * V179.2: 固定指纹 - 必须与 capture_auth.js 中使用的指纹完全一致
 */
const FIXED_FINGERPRINT = {
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    viewport: { width: 1920, height: 1080 },
    deviceScaleFactor: 1,
    locale: 'en-US',
    timezoneId: 'Europe/London',
    platform: 'Win32'
};

/**
 * V177: Ghost Protocol - 30+ 浏览器指纹池
 */
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

// ============================================================================
// 指纹生成函数
// ============================================================================

/**
 * 获取随机 UA
 * @returns {string} 随机 User-Agent
 */
function getRandomUA() {
    return GHOST_UA_POOL[Math.floor(Math.random() * GHOST_UA_POOL.length)];
}

/**
 * 获取随机视口
 * @returns {Object} 视口配置
 */
function getRandomViewport() {
    return GHOST_VIEWPORTS[Math.floor(Math.random() * GHOST_VIEWPORTS.length)];
}

/**
 * V185: 生成随机化的深度隐身配置
 * @param {number} workerId - Worker ID，用于确定性随机
 * @returns {Object} 随机化的隐身配置
 */
function generateStealthConfig(workerId = 1) {
    const seed = workerId * 17 + 42;
    const hardwareConcurrency = 8 + (seed % 17);
    const memoryOptions = [4, 8, 8, 16, 16, 16, 32];
    const deviceMemory = memoryOptions[seed % memoryOptions.length];
    const renderer = WEBGL_RENDERER_POOL[seed % WEBGL_RENDERER_POOL.length];
    const vendor = renderer.includes('NVIDIA') ? 'Google Inc. (NVIDIA)' :
                   renderer.includes('Intel') ? 'Google Inc. (Intel)' :
                   'Google Inc. (AMD)';
    const viewportWidth = 1920 + ((seed % 5) - 2) * 20;
    const viewportHeight = 1080 + ((seed % 5) - 2) * 15;

    return {
        userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        viewport: { width: viewportWidth, height: viewportHeight },
        deviceScaleFactor: 1,
        locale: 'en-US',
        timezoneId: 'Europe/London',
        platform: 'Win32',
        hardwareConcurrency,
        deviceMemory,
        webgl: { vendor, renderer },
        fonts: [
            'Arial', 'Arial Unicode MS', 'Calibri', 'Cambria', 'Georgia', 'Times New Roman',
            'Segoe UI', 'Tahoma', 'Verdana', 'Helvetica Neue', 'Helvetica', 'Helvetica Neue Cyr'
        ]
    };
}

/**
 * V179.2: 生成固定指纹 Headers - 与 capture_auth.js 一致
 * @param {boolean} useFixed - 是否使用固定指纹 (默认 true)
 * @returns {Object} 包含 userAgent, viewport, extraHTTPHeaders 的对象
 */
function generateStealthHeaders(useFixed = true) {
    if (useFixed) {
        const ua = FIXED_FINGERPRINT.userAgent;
        const viewport = FIXED_FINGERPRINT.viewport;

        return {
            userAgent: ua,
            viewport,
            locale: FIXED_FINGERPRINT.locale,
            timezoneId: FIXED_FINGERPRINT.timezoneId,
            extraHTTPHeaders: {
                'sec-ch-ua': '"Chromium";v="131", "Google Chrome";v="131", "Not-A.Brand";v="99"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"',
                'sec-fetch-dest': 'document',
                'sec-fetch-mode': 'navigate',
                'sec-fetch-site': 'none',
                'sec-fetch-user': '?1',
                'accept-language': 'en-US,en;q=0.9',
                'accept-encoding': 'gzip, deflate, br'
            }
        };
    }

    // 备用：随机指纹
    const ua = getRandomUA();
    const viewport = getRandomViewport();
    const isChrome = ua.includes('Chrome') && !ua.includes('Edg');
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
// 导出
// ============================================================================

module.exports = {
    // 常量
    WEBGL_RENDERER_POOL,
    FIXED_FINGERPRINT,
    GHOST_UA_POOL,
    GHOST_VIEWPORTS,

    // 函数
    getRandomUA,
    getRandomViewport,
    generateStealthConfig,
    generateStealthHeaders
};
