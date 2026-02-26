# V172-L2-08 浏览器指纹提取指令

## 在浏览器 Console 中运行以下代码

复制粘贴到 Chrome DevTools Console (F12 → Console):

```javascript
// ============================================
// V172-L2-08 指纹提取器 - 一键复制
// ============================================

(function() {
    const fingerprint = {
        userAgent: navigator.userAgent,
        viewport: {
            width: window.innerWidth,
            height: window.innerHeight
        },
        deviceScaleFactor: window.devicePixelRatio,
        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
        locale: navigator.language,
        languages: navigator.languages,
        platform: navigator.platform,
        hardwareConcurrency: navigator.hardwareConcurrency,
        deviceMemory: navigator.deviceMemory,
        webgl: {
            vendor: null,
            renderer: null
        }
    };

    // 获取 WebGL 信息
    try {
        const canvas = document.createElement('canvas');
        const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
        if (gl) {
            const debugInfo = gl.getExtension('WEBGL_debug_renderer_info');
            if (debugInfo) {
                fingerprint.webgl.vendor = gl.getParameter(debugInfo.UNMASKED_VENDOR_WEBGL);
                fingerprint.webgl.renderer = gl.getParameter(debugInfo.UNMASKED_RENDERER_WEBGL);
            }
        }
    } catch (e) {}

    // 输出结果
    console.log('\n');
    console.log('═'.repeat(60));
    console.log('  🔍 浏览器指纹提取结果');
    console.log('═'.repeat(60));
    console.log('\n📋 基本信息:');
    console.log('   User-Agent:', fingerprint.userAgent);
    console.log('   Viewport:', `${fingerprint.viewport.width} x ${fingerprint.viewport.height}`);
    console.log('   Scale:', fingerprint.deviceScaleFactor);
    console.log('\n🌍 地理信息:');
    console.log('   Timezone:', fingerprint.timezone);
    console.log('   Locale:', fingerprint.locale);
    console.log('   Languages:', fingerprint.languages.join(', '));
    console.log('\n💻 硬件信息:');
    console.log('   Platform:', fingerprint.platform);
    console.log('   CPU Cores:', fingerprint.hardwareConcurrency);
    console.log('   Memory:', fingerprint.deviceMemory + ' GB');
    console.log('\n🎮 WebGL:');
    console.log('   Vendor:', fingerprint.webgl.vendor);
    console.log('   Renderer:', fingerprint.webgl.renderer);
    console.log('\n═'.repeat(60));

    // 生成配置代码
    const configCode = `
// V172-L2-08 静态指纹配置 (复制到 MatchDetailEngine.js)
const STATIC_FINGERPRINT = {
    userAgent: '${fingerprint.userAgent}',
    viewport: { width: ${fingerprint.viewport.width}, height: ${fingerprint.viewport.height} },
    deviceScaleFactor: ${fingerprint.deviceScaleFactor},
    locale: '${fingerprint.locale}',
    timezoneId: '${fingerprint.timezone}',
    platform: '${fingerprint.platform}',
    hardwareConcurrency: ${fingerprint.hardwareConcurrency},
    deviceMemory: ${fingerprint.deviceMemory || 8},
    webgl: {
        vendor: '${fingerprint.webgl.vendor || 'Google Inc. (NVIDIA)'}',
        renderer: '${fingerprint.webgl.renderer || 'ANGLE (NVIDIA, NVIDIA GeForce RTX 3060)'}'
    }
};
`;

    console.log('\n📝 复制以下配置到 MatchDetailEngine.js:\n');
    console.log(configCode);
    console.log('\n');

    // 复制到剪贴板
    try {
        navigator.clipboard.writeText(configCode).then(() => {
            console.log('✅ 配置已复制到剪贴板！');
        });
    } catch (e) {
        console.log('⚠️  请手动复制上面的配置代码');
    }

    return fingerprint;
})();
```

## 输出示例

```
══════════════════════════════════════════════════════════════════
  🔍 浏览器指纹提取结果
══════════════════════════════════════════════════════════════════

📋 基本信息:
   User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36...
   Viewport: 1920 x 969
   Scale: 1

🌍 地理信息:
   Timezone: Asia/Shanghai
   Locale: zh-CN
   Languages: zh-CN, zh, en

💻 硬件信息:
   Platform: Win32
   CPU Cores: 16
   Memory: 32

🎮 WebGL:
   Vendor: Google Inc. (NVIDIA)
   Renderer: ANGLE (NVIDIA, NVIDIA GeForce RTX 4090...)

══════════════════════════════════════════════════════════════════
```

## 关键对齐项

| 字段 | 捕获环境 | Docker 引擎 | 状态 |
|------|----------|-------------|------|
| User-Agent | Chrome/xxx | **必须一致** | 🔴 |
| Viewport | 1920x969 | **必须一致** | 🔴 |
| Timezone | Asia/Shanghai | **必须一致** | 🔴 |
| Locale | zh-CN | **必须一致** | 🔴 |
| WebGL | RTX 4090 | 可伪装 | 🟢 |
