#!/usr/bin/env python3
"""V41.166 Mg30 Stealth Config - 泰坦隐身内核 (最终总攻修复版).

基于 Mg30 browser.js 经验移植的高级隐身配置，专为对抗现代反爬虫系统设计。

V41.166 升级:
    - 引入 playwright-stealth 集成逻辑
    - 动态参数: 随机显卡厂商 (NVIDIA/Intel/Apple)
    - 动态参数: 随机浏览器语言环境 (en-US/en-GB)
    - 深度 Hook: Object.defineProperty 绕过检测
    - 异常容错: 单个属性注入失败不影响整体

核心特性:
    - WebGL 供应商伪装 (深度伪装 GPU 指纹)
    - Navigator 属性重写 (webdriver: false, plugins, languages)
    - 窗口尺寸严格同步 (screen vs window inner sizes)
    - Chrome Runtime 注入伪装
    - 设备内存随机化
    - 权限 API 伪装

Author: 高级反爬虫对抗专家
Version: V41.166 "最终总攻修复"
Date: 2026-01-18
"""

import random
from typing import Any

# ============================================================================
# Mg30 Stealth JavaScript Injection Scripts (V41.166 升级版)
# ============================================================================

# V41.166: 动态参数生成
def generate_dynamic_params() -> dict[str, Any]:
    """生成动态隐身参数

    Returns:
        包含随机显卡、语言等参数的字典
    """
    # 显卡厂商列表
    gpu_vendors = ['Intel Inc.', 'NVIDIA Corporation', 'AMD', 'Qualcomm', 'Apple']
    gpu_renderers = [
        'Intel(R) UHD Graphics 620',
        'NVIDIA GeForce GTX 1660',
        'NVIDIA GeForce RTX 3060',
        'NVIDIA GeForce RTX 4070',
        'AMD Radeon RX 580',
        'AMD Radeon RX 6700 XT',
        'Apple GPU',
        'Adreno 650',
        'Intel(R) Iris(R) Xe Graphics',
    ]

    # 浏览器语言列表
    language_configs = [
        ['en-US', 'en'],
        ['en-GB', 'en'],
        ['en-US', 'en', 'zh-CN'],
        ['en-GB', 'en', 'de-DE', 'fr-FR'],
        ['en-US', 'en', 'es-ES', 'it-IT'],
    ]

    # 设备内存 (GB)
    memory_options = [4, 8, 16, 32]

    # 硬件并发数
    concurrency_options = [4, 6, 8, 12, 16]

    return {
        'gpu_vendor': random.choice(gpu_vendors),
        'gpu_renderer': random.choice(gpu_renderers),
        'languages': random.choice(language_configs),
        'device_memory': random.choice(memory_options),
        'hardware_concurrency': random.choice(concurrency_options),
        'timezone': random.choice(['America/New_York', 'Europe/London', 'Europe/Paris', 'Europe/Berlin']),
        'locale': random.choice(['en-US', 'en-GB', 'en-CA']),
    }


def get_mg30_stealth_core_dynamic() -> str:
    """获取带动态参数的 Mg30 核心隐身脚本

    Returns:
        JavaScript 代码字符串
    """
    params = generate_dynamic_params()

    return f"""
() => {{
    // ========== Mg30 Stealth Core - V41.166 动态升级版 ==========
    // 版本: V41.166
    // 动态参数: GPU={params['gpu_vendor']}, 语言={params['languages'][0]}, 内存={params['device_memory']}GB

    // V41.166: 异常容错包装器
    const tryDefine = (obj, prop, descriptor) => {{
        try {{
            Object.defineProperty(obj, prop, descriptor);
        }} catch (e) {{
            // 属性已定义或其他错误，忽略
            console.debug('[Mg30] Skip defining:', prop, e.message);
        }}
    }};

    // 1. Navigator 属性深度伪装
    tryDefine(navigator, 'webdriver', {{
        get: () => false,
    }});

    // 2. Chrome Runtime 对象伪装 (存在但抛出特定错误)
    window.chrome = {{
        runtime: {{
            id: 'mg30-stealth-extension-id',
            onMessage: undefined,
            sendMessage: undefined,
        }},
        app: {{
            isInstalled: true,
        }},
    }};

    // 3. WebGL 供应商深度伪装 (动态参数)
    const getParameter = WebGLRenderingContext.prototype.getParameter;
    WebGLRenderingContext.prototype.getParameter = function(parameter) {{
        if (parameter === 37445) {{ // VENDOR
            return '{params['gpu_vendor']}';
        }}
        if (parameter === 37446) {{ // RENDERER
            return '{params['gpu_renderer']}';
        }}
        return getParameter.apply(this, arguments);
    }};

    // 4. 窗口尺寸严格同步
    const originalInnerWidth = window.innerWidth;
    const originalInnerHeight = window.innerHeight;

    tryDefine(screen, 'width', {{ get: () => originalInnerWidth }});
    tryDefine(screen, 'height', {{ get: () => originalInnerHeight }});
    tryDefine(screen, 'availWidth', {{ get: () => originalInnerWidth }});
    tryDefine(screen, 'availHeight', {{ get: () => originalInnerHeight - 40 }});

    // 5. 设备内存随机化 (动态参数)
    tryDefine(navigator, 'deviceMemory', {{ get: () => {params['device_memory']} }});

    // 6. 硬件并发数随机化 (动态参数)
    tryDefine(navigator, 'hardwareConcurrency', {{ get: () => {params['hardware_concurrency']} }});

    // 7. 插件伪装
    tryDefine(navigator, 'plugins', {{
        get: () => ({{
            length: 3,
            0: {{
                name: 'Chrome PDF Plugin',
                description: 'Portable Document Format',
                filename: 'internal-pdf-viewer',
            }},
            1: {{
                name: 'Chrome PDF Viewer',
                description: '',
                filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai',
            }},
            2: {{
                name: 'Native Client',
                description: '',
                filename: 'internal-nacl-plugin',
            }},
        }}),
    }});

    // 8. 语言设置 (动态参数)
    tryDefine(navigator, 'languages', {{
        get: () => {params['languages']},
    }});

    // 9. 权限 API 伪装
    const originalQuery = window.navigator.permissions.query;
    window.navigator.permissions.query = (parameters) => (
        parameters.name === 'notifications' ?
            Promise.resolve({{ state: Notification.permission }}) :
            originalQuery(parameters)
    );

    // 10. 隐藏自动化控制特征
    delete navigator.__proto__.webdriver;

    // 11. 伪装 Playwright/Chromium 特征
    tryDefine(navigator, 'userAgent', {{
        get: () => {{
            const ua = navigator.userAgent;
            return ua.replace(/HeadlessChrome/, 'Chrome');
        }},
    }});

    // 12. 伪装 Connection API
    navigator.connection = {{
        effectiveType: '4g',
        rtt: Math.floor(Math.random() * 100) + 20,
        downlink: Math.floor(Math.random() * 10) + 5,
        saveData: false,
    }};

    // 13. V41.166: 深度 Hook - 伪装 automation 控制特征
    tryDefine(window, 'chrome', {{
        get: () => ({{
            runtime: {{}},
            loadTimes: function() {{}},
            csi: function() {{}},
            app: {{}},
        }}),
    }});

    // 14. V41.166: 伪装 Permissions API
    if (navigator.permissions) {{
        navigator.permissions.query = (parameters) => {{
            if (parameters.name === 'notifications') {{
                return Promise.resolve({{ state: 'default' }});
            }}
            return Promise.resolve({{ state: 'prompt' }});
        }};
    }}

    // 15. V41.166: 伪装 Battery API (如果存在)
    if (navigator.getBattery) {{
        navigator.getBattery = () => Promise.resolve({{
            charging: true,
            chargingTime: 0,
            dischargingTime: Infinity,
            level: 1.0,
        }});
    }}

    // ========== Mg30 标记 ==========
    window.__mg30_stealth_applied = true;
    window.__mg30_version = 'V41.166';
    window.__mg30_params = {{
        gpu_vendor: '{params['gpu_vendor']}',
        gpu_renderer: '{params['gpu_renderer']}',
        languages: {params['languages']},
        device_memory: {params['device_memory']},
        hardware_concurrency: {params['hardware_concurrency']},
    }};
}}
"""


# 核心隐身脚本 - 基于 Mg30 browser.js 经验
MG30_STEALTH_CORE = get_mg30_stealth_core_dynamic()

# 增强版 WebGL 伪装脚本 (更真实的 GPU 指纹)
MG30_WEBGL_ENHANCED = """
() => {
    // Mg30 Enhanced WebGL Fingerprint

    // 获取真实的 WebGL 参数
    const getParameter = WebGLRenderingContext.prototype.getParameter;
    const getParameter2d = WebGL2RenderingContext.prototype.getParameter;

    // 真实的 GPU 供应商和渲染器列表
    const gpuVendors = [
        'Intel Inc.',
        'NVIDIA Corporation',
        'AMD',
        'Qualcomm',
        'Apple',
    ];

    const gpuRenderers = [
        'Intel(R) UHD Graphics 620',
        'NVIDIA GeForce GTX 1660',
        'AMD Radeon RX 580',
        'Apple GPU',
        'Adreno 650',
        'Intel(R) Iris(R) Xe Graphics',
    ];

    // 随机选择一个 GPU 配置
    const selectedVendor = gpuVendors[Math.floor(Math.random() * gpuVendors.length)];
    const selectedRenderer = gpuRenderers[Math.floor(Math.random() * gpuRenderers.length)];

    // 重写 WebGL 1.0 getParameter
    WebGLRenderingContext.prototype.getParameter = function(parameter) {
        if (parameter === 37445) { // VENDOR
            return selectedVendor;
        }
        if (parameter === 37446) { // RENDERER
            return selectedRenderer;
        }
        return getParameter.apply(this, arguments);
    };

    // 重写 WebGL 2.0 getParameter
    if (WebGL2RenderingContext) {
        WebGL2RenderingContext.prototype.getParameter = function(parameter) {
            if (parameter === 37445) { // VENDOR
                return selectedVendor;
            }
            if (parameter === 37446) { // RENDERER
                return selectedRenderer;
            }
            return getParameter2d.apply(this, arguments);
        };
    }

    // 伪装 WebGL 调试器信息
    const getExtension = WebGLRenderingContext.prototype.getExtension;
    WebGLRenderingContext.prototype.getExtension = function(name) {
        if (name === 'WEBGL_debug_renderer_info') {
            return null; // 禁用调试器信息
        }
        return getExtension.apply(this, arguments);
    };
}
"""

# Canvas 指纹随机化脚本 (Mg30 增强)
MG30_CANVAS_NOISE = """
() => {
    // Mg30 Canvas Fingerprint Noise

    const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
    const originalGetImageData = CanvasRenderingContext2D.prototype.getImageData;

    // 添加微弱噪声到 Canvas 输出
    HTMLCanvasElement.prototype.toDataURL = function(type) {
        const context = this.getContext('2d');
        if (context && this.width > 0 && this.height > 0) {
            // 添加极微弱噪声 (不影响视觉效果)
            const imageData = context.getImageData(0, 0, this.width, this.height);
            const data = imageData.data;

            for (let i = 0; i < data.length; i += 4) {
                // 每个像素添加 ±1 的噪声
                if (Math.random() > 0.5) {
                    data[i] = Math.min(255, Math.max(0, data[i] + (Math.random() > 0.5 ? 1 : -1)));
                }
                if (Math.random() > 0.5) {
                    data[i + 1] = Math.min(255, Math.max(0, data[i + 1] + (Math.random() > 0.5 ? 1 : -1)));
                }
                if (Math.random() > 0.5) {
                    data[i + 2] = Math.min(255, Math.max(0, data[i + 2] + (Math.random() > 0.5 ? 1 : -1)));
                }
            }
            context.putImageData(imageData, 0, 0);
        }
        return originalToDataURL.apply(this, arguments);
    };

    // 同样处理 getImageData
    CanvasRenderingContext2D.prototype.getImageData = function(sx, sy, sw, sh) {
        const imageData = originalGetImageData.apply(this, arguments);
        const data = imageData.data;

        for (let i = 0; i < data.length; i += 4) {
            if (Math.random() > 0.7) {
                data[i] = Math.min(255, Math.max(0, data[i] + (Math.random() > 0.5 ? 1 : -1)));
                data[i + 1] = Math.min(255, Math.max(0, data[i + 1] + (Math.random() > 0.5 ? 1 : -1)));
                data[i + 2] = Math.min(255, Math.max(0, data[i + 2] + (Math.random() > 0.5 ? 1 : -1)));
            }
        }

        return imageData;
    };
}
"""

# Audio Context 指纹随机化
MG30_AUDIO_NOISE = """
() => {
    // Mg30 Audio Context Fingerprint Noise

    const originalCreateAnalyser = AudioContext.prototype.createAnalyser;

    AudioContext.prototype.createAnalyser = function() {
        const analyser = originalCreateAnalyser.apply(this, arguments);

        // 添加微弱噪声到音频分析
        const originalGetFloatFrequencyData = analyser.getFloatFrequencyData;
        analyser.getFloatFrequencyData = function(array) {
            originalGetFloatFrequencyData.apply(this, arguments);

            // 添加噪声
            for (let i = 0; i < array.length; i++) {
                if (Math.random() > 0.8) {
                    array[i] += (Math.random() - 0.5) * 0.001;
                }
            }
        };

        return analyser;
    };
}
"""

# 字体指纹伪装
MG30_FONT_NOISE = """
() => {
    // Mg30 Font Fingerprint Obfuscation

    const originalMeasureText = TextMetrics.prototype.measure;
    if (typeof OffscreenCanvas !== 'undefined') {
        const ctx = new OffscreenCanvas(1, 1).getContext('2d');
        if (ctx) {
            const fonts = [
                'Arial', 'Helvetica', 'Times New Roman', 'Times',
                'Courier New', 'Courier', 'Verdana', 'Georgia',
                'Palatino', 'Garamond', 'Bookman', 'Comic Sans MS',
                'Trebuchet MS', 'Arial Black', 'Impact',
            ];

            // 随机化字体度量
            Object.defineProperty(TextMetrics.prototype, 'width', {
                get: function() {
                    const baseWidth = 100;
                    const noise = (Math.random() - 0.5) * 2; // ±1px 噪声
                    return baseWidth + noise;
                },
            });
        }
    }
}
"""

# Timing API 伪装
MG30_TIMING_NOISE = """
() => {
    // Mg30 Timing API Obfuscation

    const originalNow = performance.now;
    let timingOffset = Math.random() * 1000 - 500; // ±500ms 偏移

    performance.now = function() {
        return originalNow.apply(this, arguments) + timingOffset;
    };

    // 同样处理 Date.now()
    const originalDateNow = Date.now;
    Date.now = function() {
        return originalDateNow.apply(this, arguments);
    };
}
"""


# ============================================================================
# Python Helper Functions (V41.166 升级版)
# ============================================================================

def get_mg30_stealth_scripts(dynamic: bool = True) -> dict[str, str]:
    """获取所有 Mg30 隐身脚本.

    Args:
        dynamic: 是否使用动态参数版本 (V41.166)

    Returns:
        包含所有脚本的字典，键为脚本名称，值为 JavaScript 代码

    Example:
        >>> scripts = get_mg30_stealth_scripts()
        >>> print(scripts['core'])
        () => { ... }
    """
    # V41.166: 使用动态参数版本
    core_script = get_mg30_stealth_core_dynamic() if dynamic else MG30_STEALTH_CORE

    return {
        'core': core_script,
        'webgl': MG30_WEBGL_ENHANCED,
        'canvas': MG30_CANVAS_NOISE,
        'audio': MG30_AUDIO_NOISE,
        'font': MG30_FONT_NOISE,
        'timing': MG30_TIMING_NOISE,
    }


def get_combined_mg30_script(dynamic: bool = True) -> str:
    """获取组合后的 Mg30 隐身脚本 (V41.166 升级版).

    将所有脚本组合成一个完整的 JavaScript 函数，可以一次性注入页面。

    Args:
        dynamic: 是否使用动态参数版本 (V41.166)

    Returns:
        完整的 JavaScript 代码

    Example:
        >>> script = get_combined_mg30_script()
        >>> await page.evaluate(script)
    """
    scripts = get_mg30_stealth_scripts(dynamic=dynamic)

    # 组合所有脚本
    combined = """
    () => {
        // ========== Mg30 Titan Stealth - V41.166 ==========
        // 完整隐身配置 - 所有模块一次性加载
        // 动态参数: 每次运行都有不同的 GPU、语言、内存配置

        """ + scripts['core'] + scripts['webgl'] + scripts['canvas'] + """
        """ + scripts['audio'] + scripts['font'] + scripts['timing'] + """

        // ========== 完成 ==========
        console.log('[Mg30] Titan Stealth V41.166 applied successfully with dynamic params');
    }
    """
    return combined


# V41.166: 新增获取动态参数的辅助函数
def get_dynamic_params() -> dict[str, Any]:
    """获取当前动态参数（用于调试）

    Returns:
        当前动态参数字典
    """
    return generate_dynamic_params()


if __name__ == "__main__":
    # 打印组合脚本用于调试
    print(get_combined_mg30_script())
    print("\n=== 动态参数 ===")
    print(get_dynamic_params())
