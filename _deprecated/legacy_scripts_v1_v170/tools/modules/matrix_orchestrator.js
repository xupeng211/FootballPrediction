const { chromium } = require('playwright');
const path = require('path');

class MatrixOrchestrator {
    constructor(config) {
        this.config = config;
    }

    async createWorker(workerId) {
        const port = 7891 + workerId;
        const proxyServer = `http://172.25.16.1:${port}`;
        
        const browser = await chromium.launch({
            headless: true,
            args: ['--disable-dev-shm-usage', '--no-sandbox']
        });

        const context = await browser.newContext({
            proxy: { server: proxyServer }
        });

        // 注入 V86.131 Stealth 逻辑
        await context.addInitScript(() => {
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        });

        const page = await context.newPage();
        return { browser, context, page, port, workerId };
    }
}

module.exports = MatrixOrchestrator;
