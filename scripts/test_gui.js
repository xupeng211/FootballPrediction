#!/usr/bin/env node
/**
 * @fileoverview 极简 GUI 连通性探测脚本
 * @description 零伪装、零代理，纯验证 Chromium 能否正常启动
 * @version 1.0.0
 */

const { chromium } = require('playwright');

const LOG_PREFIX = '[GUI-PROBE]';

/**
 * 主函数：极简启动，5秒自动退出
 */
async function main() {
  console.log(`${LOG_PREFIX} 启动 GUI 连通性探测...`);
  console.log(`${LOG_PREFIX} 模式: 无伪装 | 无代理 | headless: false`);

  let browser = null;

  try {
    // 极简配置：零伪装，零代理
    browser = await chromium.launch({
      headless: false,
      args: ['--no-sandbox', '--disable-setuid-sandbox']
    });

    const context = await browser.newContext();
    const page = await context.newPage();

    // 打开空白页面
    await page.goto('about:blank');
    console.log(`${LOG_PREFIX} ✓ 浏览器成功启动，页面已打开`);

    // 等待 5 秒
    console.log(`${LOG_PREFIX} 页面停留 5 秒后自动关闭...`);
    await new Promise(resolve => setTimeout(resolve, 5000));

    console.log(`${LOG_PREFIX} ✓ 探测完成，正常关闭`);

  } catch (error) {
    console.error(`${LOG_PREFIX} ✗ 探测失败:`, error.message);
    process.exit(1);

  } finally {
    if (browser) {
      await browser.close();
      console.log(`${LOG_PREFIX} 浏览器已关闭`);
    }
  }
}

// 执行主函数
main();
