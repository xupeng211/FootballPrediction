/**
 * V194.3 增强版隐身配置
 * =====================
 *
 * 针对 Cloudflare 的深度反检测优化
 *
 * 问题：Headless 模式下被 Cloudflare 检测为机器人
 * 解决方案：
 * 1. WebGL 指纹深度伪装
 * 2. 硬件并发伪装 (GPU 并发数)
 * 3. 更真实的 User-Agent (与平台匹配)
 * 4. 添加更多反检测规避脚本
 *
 * V194.3 升级:
 * - 时间种子: 指纹每小时动态变化
 * - Canvas 噪声扩展: 支持常见检测尺寸
 * - Audio 噪声增强: 更自然的随机性
 * @module infrastructure/network/enhanced_stealth_config
 * @version V194.3.0
 */

'use strict';

// ============================================================================
// WebGL 深度伪装配置
// ============================================================================

/**
 * WebGL 配置
 * 必须要与 Chrome WebGL 参数保持一致
 * 避免通过 WebGL 指纹识别为无头浏览器
 */
const WEBGL_CONFIG = {
    // 常见 GPU 配置
    vendors: [
        'Google Inc. (NVIDIA)',
        'Google Inc. (AMD)',
        'Google Inc. (Intel)'
    ],
    renderers: [
        'ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0, D3D11)',
        'ANGLE (NVIDIA, NVIDIA GeForce RTX 3070 Direct3D11 vs_5_0 ps_5_0, D3D11)',
        'ANGLE (AMD, AMD Radeon RX 580 Series Direct3D11 vs_5_0 ps_5_0, D3D11)',
        'ANGLE (Intel, Intel(R) UHD Graphics 630 Direct3D11 vs_5_0 ps_5_0, D3D11)',
        'ANGLE (Intel, Intel(R) Iris(R) Xe Graphics Direct3D11 vs_5_0 ps_5_0, D3D11)'
    ],

    // 真实 GPU 参数
    maxTextureSize: 8192,
    maxRenderbufferSize: 16384,
    maxSamples: 4,

    // 扩展功能
    extensions: [
        'EXT_color_buffer_half_float',
        'EXT_texture_filter_anisotropic',
        'EXT_frag_depth',
        'WEBGL_depth_texture',
        'OES_texture_float',
        'OES_standard_derivatives'
    ]
};

// ============================================================================
// 平台配置
// ============================================================================

/**
 * 获取增强版隐身配置
 * @param {object} options - 可选项
 * @param {string} [options.platform] - 平台类型
 * @returns {object} 隐身配置
 */
function getEnhancedStealthConfig(options = {}) {
    const platform = options.platform || 'win32';

    // 基础 UA
    const baseUA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36';

    // 平台特定配置
    const platformConfig = {
        'win32': {
            userAgent: baseUA,
            platform: 'Win32',
            platformVersion: '10.0',
            viewport: { width: 1920, height: 1080 },
            deviceScaleFactor: 1,
            hasTouch: false,
            isMobile: false,
        },
        'mac': {
            userAgent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            platform: 'MacIntel',
            platformVersion: '10_15_7',
            viewport: { width: 1680, height: 1050 },
            deviceScaleFactor: 2,
            hasTouch: false,
            isMobile: false,
        },
        'linux': {
            userAgent: 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            platform: 'Linux x86_64',
            platformVersion: '',
            viewport: { width: 1920, height: 1080 },
            deviceScaleFactor: 1,
            hasTouch: false,
            isMobile: false,
        }
    };

    return platformConfig[platform] || platformConfig.win32;
}

/**
 * V194.3: 获取高级反检测脚本 (用于 Playwright addInitScript)
 *
 * 新增功能:
 * - 时间种子: 基于 UTC 小时的确定性随机，每小时指纹自动变化
 * - Canvas 噪声扩展: 支持多种常见指纹检测尺寸
 * @param {number} [workerId] - Worker ID，用于确定性随机
 * @returns {string} JavaScript 代码
 */
function resolveStealthScriptProfile(workerIdOrOptions = 1) {
    const payload = (workerIdOrOptions && typeof workerIdOrOptions === 'object')
        ? workerIdOrOptions
        : { workerId: workerIdOrOptions };
    const currentHour = Math.floor(Date.now() / (1000 * 60 * 60));
    const workerId = Number(payload.workerId || 1) || 1;
    const seed = workerId * 17 + 42 + currentHour * 7;
    const vendorIndex = seed % WEBGL_CONFIG.vendors.length;
    const rendererIndex = seed % WEBGL_CONFIG.renderers.length;
    const memoryOptions = [4, 8, 8, 16, 16];

    return {
        fingerprintSeed: String(payload.fingerprintSeed || `seed-${workerId}-${currentHour}`),
        vendor: String(payload.webglVendor || WEBGL_CONFIG.vendors[vendorIndex]),
        renderer: String(payload.webglRenderer || WEBGL_CONFIG.renderers[rendererIndex]),
        hardwareConcurrency: Number(payload.hardwareConcurrency || (8 + (seed % 17))) || 8,
        deviceMemory: Number(payload.deviceMemory || memoryOptions[seed % memoryOptions.length]) || 8,
        platform: String(payload.platform || 'Win32'),
        canvasSalt: String(payload.canvasSalt || `canvas-${seed}`),
        audioSalt: String(payload.audioSalt || `audio-${seed}`),
        webglSalt: String(payload.webglSalt || `webgl-${seed}`),
        maxTextureSize: Number(payload.maxTextureSize || WEBGL_CONFIG.maxTextureSize) || WEBGL_CONFIG.maxTextureSize,
        maxRenderbufferSize: Number(payload.maxRenderbufferSize || WEBGL_CONFIG.maxRenderbufferSize) || WEBGL_CONFIG.maxRenderbufferSize,
        maxSamples: Number(payload.maxSamples || WEBGL_CONFIG.maxSamples) || WEBGL_CONFIG.maxSamples
    };
}

function getAntiDetectionScripts(workerIdOrOptions = 1) {
    const profile = resolveStealthScriptProfile(workerIdOrOptions);
    const vendor = profile.vendor;
    const renderer = profile.renderer;
    const hardwareConcurrency = profile.hardwareConcurrency;
    const deviceMemory = profile.deviceMemory;
    const platform = profile.platform;
    const canvasSalt = profile.canvasSalt;
    const audioSalt = profile.audioSalt;
    const webglSalt = profile.webglSalt;
    const fingerprintSeed = profile.fingerprintSeed;
    const maxTextureSize = profile.maxTextureSize;
    const maxRenderbufferSize = profile.maxRenderbufferSize;
    const maxSamples = profile.maxSamples;

    return `
        // ============================================================
        // V193.1 高级反检测脚本
        // ============================================================

        // 1. WebGL 深度伪装
        const webglVendor = '${vendor}';
        const webglRenderer = '${renderer}';
        const webglSalt = '${webglSalt}';
        const fingerprintSeed = '${fingerprintSeed}';

        const stableNoise = (key, modulus, offset = 0) => {
            const source = String(key || '');
            let hash = 0;
            for (let index = 0; index < source.length; index += 1) {
                hash = ((hash << 5) - hash + source.charCodeAt(index)) | 0;
            }
            const normalized = Math.abs(hash + offset);
            return modulus > 0 ? normalized % modulus : normalized;
        };

        const getParameterProxyHandler = {
            apply: function(target, thisArg, args) {
                const param = args[0];
                // UNMASKED_VENDOR_WEBGL (37445)
                if (param === 37445) {
                    return webglVendor;
                }
                // UNMASKED_RENDERER_WEBGL (37446)
                if (param === 37446) {
                    return webglRenderer;
                }
                // MAX_TEXTURE_SIZE
                if (param === 3379) {
                    return ${maxTextureSize};
                }
                // MAX_RENDERBUFFER_SIZE
                if (param === 34024) {
                    return ${maxRenderbufferSize};
                }
                // MAX_SAMPLES
                if (param === 36183) {
                    return ${maxSamples};
                }
                if (param === 34921) {
                    return 16 + stableNoise(webglSalt + ':max-attribs', 8);
                }
                if (param === 35660) {
                    return 16 + stableNoise(webglSalt + ':combined-units', 16);
                }
                return target.apply(thisArg, args);
            }
        };

        // 伪装 WebGL
        if (typeof WebGLRenderingContext !== 'undefined') {
            const originalGetParameter = WebGLRenderingContext.prototype.getParameter;
            WebGLRenderingContext.prototype.getParameter = new Proxy(originalGetParameter, getParameterProxyHandler);
        }

        // 伪装 WebGL2
        if (typeof WebGL2RenderingContext !== 'undefined') {
            const originalGetParameter2 = WebGL2RenderingContext.prototype.getParameter;
            WebGL2RenderingContext.prototype.getParameter = new Proxy(originalGetParameter2, getParameterProxyHandler);
        }

        // 2. 硬件并发伪装
        Object.defineProperty(navigator, 'hardwareConcurrency', {
            get: () => ${hardwareConcurrency},
            configurable: true
        });

        // 3. 设备内存伪装
        Object.defineProperty(navigator, 'deviceMemory', {
            get: () => ${deviceMemory},
            configurable: true
        });

        // 4. 插件检测规避
        Object.defineProperty(navigator, 'plugins', {
            get: () => [
                {
                    0: { type: 'application/pdf' },
                    description: 'Portable Document Format',
                    filename: 'internal-pdf-viewer',
                    length: 1,
                    name: 'Chrome PDF Plugin'
                },
                {
                    0: { type: 'application/pdf' },
                    description: '',
                    filename: 'mhjfbmdgcfiopnnflcobghgdghlmchgn',
                    length: 1,
                    name: 'Chrome PDF Viewer'
                },
                {
                    0: { type: 'application/x-nacl' },
                    1: { type: 'application/x-pnacl' },
                    description: 'Native Client Executable',
                    filename: 'internal-nacl-plugin',
                    length: 2,
                    name: 'Native Client'
                }
            ],
            configurable: true
        });

        // 5. 语言伪装
        Object.defineProperty(navigator, 'languages', {
            get: () => ['en-US', 'en', 'en-GB'],
            configurable: true
        });

        // 6. 平台伪装
        Object.defineProperty(navigator, 'platform', {
            get: () => '${platform}',
            configurable: true
        });

        // 7. webdriver 标志移除
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined,
            configurable: true
        });

        // 8. 连接信息伪装
        if (navigator.connection) {
            Object.defineProperty(navigator.connection, 'effectiveType', {
                get: () => '4g',
                configurable: true
            });
            Object.defineProperty(navigator.connection, 'downlink', {
                get: () => 10,
                configurable: true
            });
        }

        // 9. Canvas 指纹噪声 - V194.3: 扩展到常见检测尺寸
        const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
        const originalToBlob = HTMLCanvasElement.prototype.toBlob;
        const CANVAS_FINGERPRINT_SIZES = [
            [280, 60],    // FingerprintJS
            [220, 30],    // ClientJS
            [200, 100],   // 常见尺寸
            [240, 140],   // 常见尺寸
            [300, 150],   // 常见尺寸
            [400, 200],   // 常见尺寸
            [500, 500]    // 大型指纹
        ];
        const applyCanvasNoise = (canvas) => {
            const context = canvas.getContext('2d');
            if (!context) {
                return;
            }
            const imageData = context.getImageData(0, 0, canvas.width, canvas.height);
            for (let i = 0; i < imageData.data.length; i += 4) {
                const noise = stableNoise('${canvasSalt}' + ':' + canvas.width + ':' + canvas.height + ':' + i, 5) - 2;
                imageData.data[i] = Math.max(0, Math.min(255, imageData.data[i] + noise));
                imageData.data[i + 1] = Math.max(0, Math.min(255, imageData.data[i + 1] + (noise % 3)));
            }
            context.putImageData(imageData, 0, 0);
        };
        HTMLCanvasElement.prototype.toDataURL = function(type) {
            // 检查是否为指纹检测尺寸
            const isFingerprintSize = CANVAS_FINGERPRINT_SIZES.some(
                ([w, h]) => Math.abs(this.width - w) <= 20 && Math.abs(this.height - h) <= 20
            ) || (this.width > 0 && this.width <= 500 && this.height > 0 && this.height <= 500);

            if (type === 'image/png' && isFingerprintSize) {
                applyCanvasNoise(this);
            }
            return originalToDataURL.apply(this, arguments);
        };
        HTMLCanvasElement.prototype.toBlob = function() {
            applyCanvasNoise(this);
            if (typeof originalToBlob === 'function') {
                return originalToBlob.apply(this, arguments);
            }
            return undefined;
        };

        // 10. Audio 指纹噪声
        const originalGetChannelData = AudioBuffer.prototype.getChannelData;
        AudioBuffer.prototype.getChannelData = function(channel) {
            const data = originalGetChannelData.call(this, channel);
            // 添加微小噪声
            for (let i = 0; i < data.length; i += 100) {
                const drift = (stableNoise('${audioSalt}' + ':' + channel + ':' + i, 11) - 5) / 100000;
                data[i] = data[i] + drift;
            }
            return data;
        };

        // 11. 隐藏自动化标志
        delete window.__webdriver_evaluate;
        delete window.__webdriver_script_function;
        delete window.__webdriver_script_fn;
        delete window.__webdriver_unwrapped;
        delete window.__driver_evaluate;
        delete window.__selenium_evaluate;
        delete window.__fxdriver_evaluate;

        // 12. 覆盖 toString 防止检测
        const oldToString = Function.prototype.toString;
        Function.prototype.toString = function() {
            if (this === navigator.permissions?.query) {
                return 'function query() { [native code] }';
            }
            return oldToString.call(this);
        };

        // 13. permissions 查询伪装
        const originalQuery = navigator.permissions?.query;
        if (originalQuery) {
            navigator.permissions.query = (parameters) => {
                if (parameters.name === 'notifications') {
                    return Promise.resolve({ state: Notification.permission });
                }
                if (parameters.name === 'geolocation') {
                    return Promise.resolve({ state: 'prompt' });
                }
                return originalQuery.call(navigator.permissions, parameters);
            };
        }

        console.log('[V193.1] 高级隐身装甲已激活: WebGL=' + webglRenderer + ', CPU=' + ${hardwareConcurrency} + '核, RAM=' + ${deviceMemory} + 'GB, Seed=' + fingerprintSeed);
    `;
}

/**
 * V193.1: 获取随机 WebGL 配置
 * @param {number} [workerId] - Worker ID
 * @returns {object} WebGL 配置
 */
function getRandomWebGLConfig(workerId = 1) {
    const seed = workerId * 17 + 42;
    return {
        vendor: WEBGL_CONFIG.vendors[seed % WEBGL_CONFIG.vendors.length],
        renderer: WEBGL_CONFIG.renderers[seed % WEBGL_CONFIG.renderers.length],
        maxTextureSize: WEBGL_CONFIG.maxTextureSize,
        maxRenderbufferSize: WEBGL_CONFIG.maxRenderbufferSize,
        maxSamples: WEBGL_CONFIG.maxSamples,
        extensions: WEBGL_CONFIG.extensions
    };
}

/**
 * V193.1: 获取硬件配置
 * @param {number} [workerId] - Worker ID
 * @returns {object} 硬件配置
 */
function getHardwareConfig(workerId = 1) {
    const seed = workerId * 17 + 42;
    const memoryOptions = [4, 8, 8, 16, 16, 32];

    return {
        hardwareConcurrency: 8 + (seed % 17), // 8-24 核
        deviceMemory: memoryOptions[seed % memoryOptions.length], // 4-32 GB
    };
}

module.exports = {
    WEBGL_CONFIG,
    getEnhancedStealthConfig,
    getAntiDetectionScripts,
    getRandomWebGLConfig,
    getHardwareConfig
};
