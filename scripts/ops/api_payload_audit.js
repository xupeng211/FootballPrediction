/**
 * TITAN V6.0 - API Payload Audit Tool
 * ===================================
 * 
 * 深度审计API截获的原始报文结构
 * 识别初盘、变盘曲线、时间戳字段
 * 
 * @version V6.0-DEEP-AUDIT
 * @date 2026-03-16
 */

'use strict';

const { chromium } = require('playwright');
const fs = require('fs').promises;
const path = require('path');

// 配置
const CONFIG = {
  TARGET_URL: 'https://www.oddsportal.com/football/england/premier-league/arsenal-bournemouth-jcHwYvNG/',
  SESSION_FILE: '/app/data/sessions/auth_gold.json',
  OUTPUT_DIR: '/app/data/audit'
};

async function auditApiPayload() {
  console.log('\n' + '='.repeat(70));
  console.log('🔬 TITAN V6.0 - API Payload Deep Audit');
  console.log('='.repeat(70) + '\n');
  
  // 存储所有拦截的API数据
  const interceptedApis = [];
  
  // 启动浏览器
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();
  
  // 设置API拦截 - 捕获所有XHR请求和响应
  await page.route('**/*', async (route, request) => {
    const requestUrl = request.url();
    const resourceType = request.resourceType();
    
    // 拦截所有可能的API端点
    if (resourceType === 'xhr' || /ajax|feed|api|odds|bet/.test(requestUrl.toLowerCase())) {
      console.log(`📡 Intercepted: ${requestUrl.substring(0, 70)}...`);
      
      try {
        const response = await route.fetch();
        const responseBody = await response.text();
        
        // 尝试解析JSON
        let jsonData = null;
        let isValidJson = false;
        try {
          jsonData = JSON.parse(responseBody);
          isValidJson = true;
        } catch (e) {
          // 不是JSON
        }
        
        // 存储拦截数据
        const apiRecord = {
          url: requestUrl,
          timestamp: new Date().toISOString(),
          contentType: response.headers()['content-type'],
          bodyLength: responseBody.length,
          isJson: isValidJson,
          data: jsonData
        };
        
        interceptedApis.push(apiRecord);
        
        // 如果是JSON，进行深度分析
        if (isValidJson) {
          analyzePayloadStructure(jsonData, requestUrl);
        }
        
      } catch (e) {
        console.log(`   ⚠️  Failed to fetch response: ${e.message}`);
      }
    }
    
    route.continue();
  });
  
  // 导航到目标页面
  console.log(`🔍 Navigating to: ${CONFIG.TARGET_URL}\n`);
  await page.goto(CONFIG.TARGET_URL, {
    waitUntil: 'networkidle',
    timeout: 60000
  });
  
  // 等待JS渲染和额外API调用
  console.log('⏳ Waiting for additional API calls...');
  await page.waitForTimeout(10000);
  
  // 保存完整的审计报告
  await fs.mkdir(CONFIG.OUTPUT_DIR, { recursive: true });
  const auditFile = path.join(CONFIG.OUTPUT_DIR, `api_audit_${Date.now()}.json`);
  await fs.writeFile(auditFile, JSON.stringify(interceptedApis, null, 2));
  
  console.log(`\n💾 Audit report saved: ${auditFile}`);
  console.log(`📊 Total APIs intercepted: ${interceptedApis.length}`);
  
  // 生成结构分析报告
  generateStructureReport(interceptedApis);
  
  await browser.close();
  
  console.log('\n' + '='.repeat(70));
  console.log('✅ API Payload Audit Complete');
  console.log('='.repeat(70) + '\n');
}

/**
 * 分析单个payload的结构
 */
function analyzePayloadStructure(data, url) {
  console.log(`\n🔍 Analyzing: ${url.substring(url.lastIndexOf('/') + 1)}`);
  
  // 递归扫描对象结构
  const findings = [];
  scanObject(data, '', findings);
  
  // 输出关键发现
  const keyFindings = findings.filter(f => 
    /odds|open|close|start|time|hist|move|curve|pinnacle|bet365/i.test(f.path)
  );
  
  if (keyFindings.length > 0) {
    console.log('   Key findings:');
    keyFindings.slice(0, 5).forEach(f => {
      console.log(`   - ${f.path}: ${f.type}${f.sample ? ' = ' + JSON.stringify(f.sample).substring(0, 50) : ''}`);
    });
  }
}

/**
 * 递归扫描对象
 */
function scanObject(obj, path, findings) {
  if (typeof obj !== 'object' || obj === null) return;
  
  if (Array.isArray(obj)) {
    findings.push({
      path: path || 'root',
      type: `array[${obj.length}]`,
      sample: obj[0]
    });
    
    // 扫描数组元素（限制前3个）
    obj.slice(0, 3).forEach((item, idx) => {
      scanObject(item, `${path}[${idx}]`, findings);
    });
  } else {
    Object.keys(obj).forEach(key => {
      const value = obj[key];
      const currentPath = path ? `${path}.${key}` : key;
      
      findings.push({
        path: currentPath,
        type: typeof value,
        sample: typeof value !== 'object' ? value : null
      });
      
      // 递归扫描嵌套对象
      if (typeof value === 'object' && value !== null) {
        scanObject(value, currentPath, findings);
      }
    });
  }
}

/**
 * 生成结构分析报告
 */
function generateStructureReport(apis) {
  console.log('\n' + '='.repeat(70));
  console.log('📊 Structure Analysis Report');
  console.log('='.repeat(70));
  
  // 按类型分组
  const jsonApis = apis.filter(api => api.isJson);
  console.log(`\nJSON APIs: ${jsonApis.length}/${apis.length}`);
  
  // 查找包含特定关键词的API
  const oddsApis = apis.filter(api => 
    /odds|bet|market|bookie/i.test(api.url)
  );
  console.log(`Odds-related APIs: ${oddsApis.length}`);
  
  // 查找最大payload
  const largestApi = apis.reduce((max, api) => 
    api.bodyLength > max.bodyLength ? api : max
  , apis[0]);
  
  if (largestApi) {
    console.log(`\nLargest payload: ${(largestApi.bodyLength / 1024).toFixed(2)} KB`);
    console.log(`URL: ${largestApi.url.substring(0, 80)}...`);
  }
  
  // 推荐关键API端点
  console.log('\n🔑 Recommended API endpoints to analyze:');
  oddsApis.slice(0, 5).forEach((api, idx) => {
    console.log(`  ${idx + 1}. ${api.url.substring(api.url.lastIndexOf('/') + 1)}`);
  });
  
  console.log('\n' + '='.repeat(70));
}

// 执行审计
auditApiPayload().catch(err => {
  console.error('❌ Audit failed:', err);
  process.exit(1);
});
