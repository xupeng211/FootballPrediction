#!/usr/bin/env node
/**
 * v3.0.0 发布验证测试脚本
 * 验证前端页面和基本功能
 */

const http = require('http');
const https = require('https');

console.log('🚀 开始 v3.0.0 发布验证测试...\n');

const testResults = {
  frontend: [],
  backend: [],
  integration: []
};

let totalTests = 0;
let passedTests = 0;

// 测试 HTTP 服务
function testHttpService(url, description, category) {
  return new Promise((resolve) => {
    totalTests++;
    const isHttps = url.startsWith('https://');
    const client = isHttps ? https : http;

    const req = client.get(url, (res) => {
      let data = '';
      res.on('data', (chunk) => data += chunk);
      res.on('end', () => {
        const success = res.statusCode >= 200 && res.statusCode < 300;
        const result = {
          url,
          description,
          category,
          status: success ? '✅' : '❌',
          statusCode: res.statusCode,
          success
        };
        testResults[category].push(result);
        if (success) passedTests++;
        console.log(`${result.status} ${description} (${res.statusCode})`);
        resolve(result);
      });
    });

    req.on('error', (err) => {
      const result = {
        url,
        description,
        category,
        status: '❌',
        error: err.message,
        success: false
      };
      testResults[category].push(result);
      console.log(`❌ ${description} - ${err.message}`);
      resolve(result);
    });

    req.setTimeout(5000, () => {
      req.destroy();
      const result = {
        url,
        description,
        category,
        status: '❌',
        error: 'Timeout',
        success: false
      };
      testResults[category].push(result);
      console.log(`❌ ${description} - Timeout`);
      resolve(result);
    });
  });
}

// 测试前端服务
async function testFrontend() {
  console.log('📱 测试前端服务...\n');

  await testHttpService('http://localhost:5174', '前端主页加载', 'frontend');
  await testHttpService('http://localhost:5174/favicon.ico', '前端静态资源', 'frontend');
  await testHttpService('http://localhost:5174/src/main.ts', '前端源码访问', 'frontend');
}

// 测试后端服务
async function testBackend() {
  console.log('\n🔧 测试后端服务...\n');

  await testHttpService('http://localhost:8000/health', '后端健康检查', 'backend');
  await testHttpService('http://localhost:8000/docs', 'API 文档', 'backend');
  await testHttpService('http://localhost:8000/api/v1/metrics', 'Prometheus 指标', 'backend');
}

// 测试集成功能
async function testIntegration() {
  console.log('\n🔗 测试集成功能...\n');

  // 测试 API 访问性
  await testHttpService('http://localhost:8000/api/v1/predictions', '预测 API 端点', 'integration');
  await testHttpService('http://localhost:8000/api/v1/matches', '比赛 API 端点', 'integration');
}

// 主测试函数
async function runTests() {
  try {
    await testFrontend();
    await testBackend();
    await testIntegration();

    console.log('\n🎯 测试结果摘要\n');
    console.log(`总测试数: ${totalTests}`);
    console.log(`通过测试数: ${passedTests}`);
    console.log(`通过率: ${((passedTests / totalTests) * 100).toFixed(1)}%\n`);

    // 按类别显示结果
    ['frontend', 'backend', 'integration'].forEach(category => {
      const results = testResults[category];
      if (results.length > 0) {
        console.log(`${category.toUpperCase()} 测试结果:`);
        results.forEach(result => {
          console.log(`  ${result.status} ${result.description} (${result.statusCode || result.error || 'N/A'})`);
        });
        console.log('');
      }
    });

    if (passedTests === totalTests) {
      console.log('🎉 所有测试通过！v3.0.0 发布验证成功！\n');
      process.exit(0);
    } else {
      console.log('❌ 部分测试失败，请检查上述问题。\n');
      process.exit(1);
    }

  } catch (error) {
    console.error('❌ 测试执行过程中出现错误:', error.message);
    process.exit(1);
  }
}

// 运行测试
runTests();