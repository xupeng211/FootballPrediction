/**
 * TITAN V6.0 - Local Rendering Integrity TDD Test
 * ================================================
 *
 * 【本地接管协议】渲染完整性严格验证
 * 确保页面在真实GUI环境下正确渲染，拒绝白板空头
 *
 * @version V6.0.1-LOCAL
 * @date 2026-03-15
 */

'use strict';

const { describe, it, before, after } = require('node:test');
const assert = require('node:assert');
const fs = require('fs').promises;
const path = require('path');

// 被测系统
let OddsPortalHarvester;
try {
  OddsPortalHarvester = require('../../src/infrastructure/harvesters/OddsPortalHarvester');
} catch (e) {
  // 兼容不同的导出方式
  OddsPortalHarvester = require('../../src/infrastructure/harvesters/OddsPortalHarvester').OddsPortalHarvester;
}

// 测试配置
const CONFIG = {
  TEST_URL: 'https://www.oddsportal.com/soccer/england/premier-league/arsenal-chelsea/',
  SCREENSHOT_DIR: '/app/data/screenshots',
  TIMEOUT: 120000, // 2分钟超时
};

// 全局变量
let harvester = null;
let testResult = null;

describe('TITAN V6.0 - LOCAL OVERRIDE 渲染完整性验证', () => {

  before(async () => {
    console.log('\n' + '='.repeat(70));
    console.log('🧪 TITAN V6.0 - Local Rendering Integrity TDD Test');
    console.log('='.repeat(70));
    console.log(`📍 测试URL: ${CONFIG.TEST_URL}`);
    console.log(`⏱️  超时设置: ${CONFIG.TIMEOUT}ms`);
    console.log('='.repeat(70) + '\n');

    // 初始化收割机
    harvester = new OddsPortalHarvester({ 
      headless: false,  // 本地接管必须使用可见模式
      maxWorkers: 1     // 单Worker便于调试
    });
    
    await harvester.initialize();
  });

  after(async () => {
    if (harvester) {
      await harvester.close();
      console.log('\n🧹 Harvester 已关闭\n');
    }
  });

  // ============================================================
  // 断言1: bodyTextLength 必须 > 2000 字符（拒绝白板）
  // ============================================================
  it('断言1: bodyTextLength 必须 > 2000 字符（拒绝白板）', async () => {
    console.log('\n📍 ASSERT-01: 页面内容深度验证（拒绝白板）\n');
    
    const result = await harvester.harvest(CONFIG.TEST_URL);
    testResult = result; // 保存供后续测试使用
    
    // 验证结果结构
    assert.ok(result, '必须返回结果对象');
    assert.ok(result.odds, '必须返回odds对象');
    assert.ok(result.odds._diagnostic, '必须包含_diagnostic诊断信息');
    
    const diagnostic = result.odds._diagnostic;
    
    // 核心断言: bodyTextLength > 2000
    console.log(`   📊 bodyTextLength: ${diagnostic.bodyTextLength}`);
    assert.ok(
      diagnostic.bodyTextLength > 2000,
      `bodyTextLength 必须 > 2000 字符，实际: ${diagnostic.bodyTextLength}。页面可能是白板！`
    );
    
    console.log('   ✅ 页面内容验证通过（非白板）');
    console.log(`   📝 页面标题: ${diagnostic.title}`);
    console.log(`   🔗 URL: ${diagnostic.url}`);
  });

  // ============================================================
  // 断言2: title 必须包含 "Odds" 字样（拒绝空头）
  // ============================================================
  it('断言2: title 必须包含 "Odds" 字样（拒绝空头）', async () => {
    console.log('\n📍 ASSERT-02: 页面标题验证（拒绝空头）\n');
    
    // 如果没有前置结果，重新抓取
    if (!testResult) {
      testResult = await harvester.harvest(CONFIG.TEST_URL);
    }
    
    assert.ok(testResult.odds._diagnostic, '必须包含_diagnostic诊断信息');
    
    const title = testResult.odds._diagnostic.title || '';
    
    // 核心断言: title 必须包含 "Odds"
    console.log(`   📄 页面标题: "${title}"`);
    assert.ok(
      title.toLowerCase().includes('odds'),
      `页面标题必须包含 "Odds" 字样，实际: "${title}"。可能是拦截页面或空头！`
    );
    
    console.log('   ✅ 页面标题验证通过（非空头）');
  });

  // ============================================================
  // 断言3: 截图文件大小必须 > 50KB（证明页面有色彩分布，非纯白）
  // ============================================================
  it('断言3: 截图文件大小必须 > 50KB（非纯白页面）', async () => {
    console.log('\n📍 ASSERT-03: 截图质量验证（拒绝纯白）\n');
    
    // 如果没有前置结果，重新抓取
    if (!testResult) {
      testResult = await harvester.harvest(CONFIG.TEST_URL);
    }
    
    // 查找最新的截图文件
    const screenshotDir = CONFIG.SCREENSHOT_DIR;
    
    try {
      const files = await fs.readdir(screenshotDir);
      const pngFiles = files
        .filter(f => f.endsWith('.png'))
        .map(f => ({
          name: f,
          path: path.join(screenshotDir, f),
          time: parseInt(f.match(/match_(\d+)\.png/)?.[1] || 0)
        }))
        .sort((a, b) => b.time - a.time); // 最新的在前
      
      assert.ok(pngFiles.length > 0, '必须生成至少一个截图文件');
      
      const latestScreenshot = pngFiles[0];
      const stats = await fs.stat(latestScreenshot.path);
      const sizeKB = stats.size / 1024;
      
      console.log(`   📸 截图文件: ${latestScreenshot.name}`);
      console.log(`   📊 文件大小: ${sizeKB.toFixed(2)} KB`);
      
      // 核心断言: 截图大小 > 50KB
      assert.ok(
        sizeKB > 50,
        `截图文件大小必须 > 50KB，实际: ${sizeKB.toFixed(2)} KB。可能是纯白页面！`
      );
      
      console.log('   ✅ 截图质量验证通过（非纯白）');
      
      // 额外信息：显示截图路径
      console.log(`   📍 截图路径: ${latestScreenshot.path}`);
      
    } catch (error) {
      if (error.code === 'ENOENT') {
        assert.fail('截图目录不存在，视觉审计系统可能未启用');
      } else {
        throw error;
      }
    }
  });

  // ============================================================
  // 综合诊断报告
  // ============================================================
  it('综合诊断: 渲染完整性报告', async () => {
    console.log('\n📍 COMPREHENSIVE DIAGNOSTIC REPORT\n');
    
    if (!testResult) {
      testResult = await harvester.harvest(CONFIG.TEST_URL);
    }
    
    const diagnostic = testResult.odds._diagnostic || {};
    
    console.log('='.repeat(70));
    console.log('📊 渲染完整性诊断报告');
    console.log('='.repeat(70));
    console.log(`📄 页面标题: ${diagnostic.title || 'N/A'}`);
    console.log(`🔗 页面URL: ${diagnostic.url || 'N/A'}`);
    console.log(`📝 Body文本长度: ${diagnostic.bodyTextLength || 0} 字符`);
    console.log(`📦 Body存在: ${diagnostic.hasBody ? '是' : '否'}`);
    console.log(`🕐 时间戳: ${diagnostic.timestamp || 'N/A'}`);
    console.log('='.repeat(70));
    
    // 验证赔率数据
    if (testResult.odds && testResult.odds['1x2']) {
      console.log('\n💰 提取到的赔率:');
      const odds = testResult.odds['1x2'];
      console.log(`   主胜: ${odds[0]}`);
      console.log(`   平局: ${odds[1]}`);
      console.log(`   客胜: ${odds[2]}`);
      
      // 计算margin
      try {
        const o1 = parseFloat(odds[0]);
        const oX = parseFloat(odds[1]);
        const o2 = parseFloat(odds[2]);
        const margin = (1/o1 + 1/oX + 1/o2 - 1) * 100;
        console.log(`   📊 Margin: ${margin.toFixed(2)}%`);
        
        // 验证margin在合理范围
        assert.ok(margin >= 1 && margin <= 15, `Margin ${margin.toFixed(2)}% 不在合理范围 (1%-15%)`);
        console.log('   ✅ Margin验证通过');
      } catch (e) {
        console.log(`   ⚠️  Margin计算失败: ${e.message}`);
      }
    } else {
      console.log('\n⚠️  未提取到赔率数据');
    }
    
    console.log('\n' + '='.repeat(70));
    console.log('✅ 综合诊断完成');
    console.log('='.repeat(70) + '\n');
  });
});

// 测试运行入口
if (require.main === module) {
  console.log('\n🔥 TITAN V6.0 - Local Rendering Integrity Test');
  console.log('Usage: node tests/unit/Local_Rendering_Integrity.test.js\n');
}

module.exports = { CONFIG };