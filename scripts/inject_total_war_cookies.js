#!/usr/bin/env node
/**
 * @file TOTAL WAR Cookie 物理注入脚本
 * @description 将原始 Cookie 数据直接写入 Playwright storageState 格式
 * @version 1.0.0
 */

const fs = require('fs').promises;
const path = require('path');

const LOG_PREFIX = '[TOTAL-WAR-INJECT]';

/**
 * 原始 Cookie 数据 (Chrome Extension 导出格式)
 */
const RAW_COOKIES = [
  {
    "domain": ".fotmob.com",
    "expirationDate": 1779604292,
    "hostOnly": false,
    "httpOnly": false,
    "name": "__eoi",
    "path": "/",
    "sameSite": "no_restriction",
    "secure": true,
    "session": false,
    "storeId": "0",
    "value": "ID=489d7718b9688a8a:T=1764052292:RT=1764055716:S=AA-AfjbcEeT-YD_G1fI_PPDN2MlE",
    "id": 1
  },
  {
    "domain": ".fotmob.com",
    "expirationDate": 1797748292,
    "hostOnly": false,
    "httpOnly": false,
    "name": "__gads",
    "path": "/",
    "sameSite": "no_restriction",
    "secure": true,
    "session": false,
    "storeId": "0",
    "value": "ID=6c2e5d5466bad63c:T=1764052292:RT=1764055716:S=ALNI_MbbSZAozSqs9vT4QC2vdsC-oXXHMg",
    "id": 2
  },
  {
    "domain": ".fotmob.com",
    "expirationDate": 1797748292,
    "hostOnly": false,
    "httpOnly": false,
    "name": "__gpi",
    "path": "/",
    "sameSite": "no_restriction",
    "secure": true,
    "session": false,
    "storeId": "0",
    "value": "UID=000011bc5e971d16:T=1764052292:RT=1764055716:S=ALNI_MZJ5v_vQ7dU5YOIzsCi9cNSIW96VQ",
    "id": 3
  },
  {
    "domain": ".fotmob.com",
    "expirationDate": 1787380298,
    "hostOnly": false,
    "httpOnly": false,
    "name": "_cc_id",
    "path": "/",
    "sameSite": "lax",
    "secure": false,
    "session": false,
    "storeId": "0",
    "value": "dc083b9ce6d19cf07d9f3937028b99b8",
    "id": 4
  },
  {
    "domain": ".fotmob.com",
    "expirationDate": 1807827978.700578,
    "hostOnly": false,
    "httpOnly": false,
    "name": "_ga",
    "path": "/",
    "sameSite": "unspecified",
    "secure": false,
    "session": false,
    "storeId": "0",
    "value": "GA1.1.1566902830.1764052285",
    "id": 5
  },
  {
    "domain": ".fotmob.com",
    "expirationDate": 1807827978.699633,
    "hostOnly": false,
    "httpOnly": false,
    "name": "_ga_G0V1WDW9B2",
    "path": "/",
    "sameSite": "unspecified",
    "secure": false,
    "session": false,
    "storeId": "0",
    "value": "GS2.1.s1773267978$o20$g0$t1773267978$j60$l0$h1047605236",
    "id": 6
  },
  {
    "domain": ".fotmob.com",
    "expirationDate": 1806609939.651024,
    "hostOnly": false,
    "httpOnly": false,
    "name": "_ga_K2ECMCJBFQ",
    "path": "/",
    "sameSite": "unspecified",
    "secure": false,
    "session": false,
    "storeId": "0",
    "value": "GS2.1.s1772049937$o3$g0$t1772049939$j59$l0$h0",
    "id": 7
  },
  {
    "domain": ".fotmob.com",
    "expirationDate": 1806609939.649284,
    "hostOnly": false,
    "httpOnly": false,
    "name": "_ga_SQ24F7Q7YW",
    "path": "/",
    "sameSite": "unspecified",
    "secure": false,
    "session": false,
    "storeId": "0",
    "value": "GS2.1.s1772049937$o3$g0$t1772049939$j60$l0$h0",
    "id": 8
  },
  {
    "domain": ".fotmob.com",
    "expirationDate": 1780277319,
    "hostOnly": false,
    "httpOnly": false,
    "name": "_gcl_au",
    "path": "/",
    "sameSite": "unspecified",
    "secure": false,
    "session": false,
    "storeId": "0",
    "value": "1.1.1911414541.1772501319",
    "id": 9
  },
  {
    "domain": ".fotmob.com",
    "expirationDate": 1773269845,
    "hostOnly": false,
    "httpOnly": false,
    "name": "_hjSession_2585474",
    "path": "/",
    "sameSite": "no_restriction",
    "secure": true,
    "session": false,
    "storeId": "0",
    "value": "eyJpZCI6IjcwMTU0MTE5LWVmNzctNDJhMy05ZDMyLTRjYTY5NzI3ZjlmMCIsImMiOjE3NzMyNjc5ODE0MDksInMiOjAsInIiOjAsInNiIjowLCJzciI6MCwic2UiOjAsImZzIjowLCJzcCI6MH0=",
    "id": 10
  },
  {
    "domain": ".fotmob.com",
    "expirationDate": 1804803981,
    "hostOnly": false,
    "httpOnly": false,
    "name": "_hjSessionUser_2585474",
    "path": "/",
    "sameSite": "no_restriction",
    "secure": true,
    "session": false,
    "storeId": "0",
    "value": "eyJpZCI6ImQ4M2NkMWM2LTQxNTYtNTJkNC1iYWU4LTk5MmU5NzE5MDI1OCIsImNyZWF0ZWQiOjE3NjQwNTIyOTI0OTQsImV4aXN0aW5nIjp0cnVlfQ==",
    "id": 11
  },
  {
    "domain": ".fotmob.com",
    "expirationDate": 1797748297,
    "hostOnly": false,
    "httpOnly": false,
    "name": "cto_bundle",
    "path": "/",
    "sameSite": "unspecified",
    "secure": false,
    "session": false,
    "storeId": "0",
    "value": "IzVzDV96cGR1Tjc3SE9LalB6RFNSUVMySCUyQnczZiUyRkxUQmtMdGFiWnF4UjdFTUJRSXBHOXlSQUJ4Q2Q0VFlzJTJCVUNPN2ZxcyUyRiUyRmxuUXlQWlUlMkJHQkE5U2plQlJzdkwxOGFZUUdaVDQ5aDVpMHZPeTJRNCUyRnhvTjVzNmhrU0hHaUVQTm96U0ZUcmoybllHTXAxOHplTE9aM2szbWlNQSUzRCUzRA",
    "id": 12
  },
  {
    "domain": ".fotmob.com",
    "expirationDate": 1802678236,
    "hostOnly": false,
    "httpOnly": false,
    "name": "FCCDCF",
    "path": "/",
    "sameSite": "unspecified",
    "secure": false,
    "session": false,
    "storeId": "0",
    "value": "%5Bnull%2Cnull%2Cnull%2Cnull%2Cnull%2Cnull%2C%5B%5B32%2C%22%5B%5C%225574c635-de60-4ed1-a194-c6f6627f31aa%5C%22%2C%5B1764052294%2C906000000%5D%5D%22%5D%5D%5D",
    "id": 13
  },
  {
    "domain": ".fotmob.com",
    "expirationDate": 1800518237,
    "hostOnly": false,
    "httpOnly": false,
    "name": "FCNEC",
    "path": "/",
    "sameSite": "unspecified",
    "secure": false,
    "session": false,
    "storeId": "0",
    "value": "%5B%5B%22AKsRol-AIOQbN5W3mY6v10b9vOtTBJ_T8S5Bc-TmKJyKfLGjYXBUEjz_zvSg-yolPVMPdraERYlCZeoKpTLrC1o2n48UqfgPFGc7uq8xLW_rE43ibB5cvvCCqTtASxdhkJD9-olj09m8Mms-K1JWOsIPXPF8jwIGKg%3D%3D%22%5D%5D",
    "id": 14
  },
  {
    "domain": "www.fotmob.com",
    "expirationDate": 1788819981,
    "hostOnly": true,
    "httpOnly": false,
    "name": "g_state",
    "path": "/",
    "sameSite": "unspecified",
    "secure": false,
    "session": false,
    "storeId": "0",
    "value": "{\"i_l\":0,\"i_ll\":1773267981283,\"i_b\":\"ff5I/yKP4ae8THJ8HAOoLmeFq/kkjrLRW512wFY+bME\",\"i_e\":{\"enable_itp_optimization\":0}}",
    "id": 15
  },
  {
    "domain": "www.fotmob.com",
    "expirationDate": 1803603639.790072,
    "hostOnly": true,
    "httpOnly": false,
    "name": "NEXT_LOCALE",
    "path": "/",
    "sameSite": "unspecified",
    "secure": false,
    "session": false,
    "storeId": "0",
    "value": "zh-Hans",
    "id": 16
  },
  {
    "domain": "www.fotmob.com",
    "expirationDate": 1773354380.79269,
    "hostOnly": true,
    "httpOnly": false,
    "name": "turnstile_verified",
    "path": "/",
    "sameSite": "strict",
    "secure": true,
    "session": false,
    "storeId": "0",
    "value": "1.1773267979.1cb17147acc924ea870db9768d71e88d5e060f4b72b6779129d8900de787c07d",
    "id": 17
  },
  {
    "domain": "www.fotmob.com",
    "expirationDate": 1773354377,
    "hostOnly": true,
    "httpOnly": false,
    "name": "u:location",
    "path": "/",
    "sameSite": "unspecified",
    "secure": false,
    "session": false,
    "storeId": "0",
    "value": "%7B%22countryCode%22%3A%22TW%22%2C%22regionId%22%3A%22TPE%22%2C%22ip%22%3A%22127.0.0.1%22%2C%22ccode3%22%3A%22TWN%22%2C%22ccode3NoRegion%22%3A%22TWN%22%2C%22timezone%22%3A%22Asia%2FShanghai%22%7D",
    "id": 18
  }
];

/**
 * 转换 Cookie 格式为 Playwright storageState
 * @param cookies
 */
function convertToStorageState(cookies) {
  const convertedCookies = cookies.map(cookie => {
    // 统一 domain 为 .fotmob.com (处理 www.fotmob.com)
    const domain = cookie.domain.startsWith('.')
      ? cookie.domain
      : '.' + cookie.domain.replace('www.', '');

    // 转换 sameSite 格式
    let sameSite = 'Lax';
    if (cookie.sameSite === 'no_restriction' || cookie.sameSite === 'None') {
      sameSite = 'None';
    } else if (cookie.sameSite === 'strict' || cookie.sameSite === 'Strict') {
      sameSite = 'Strict';
    } else if (cookie.sameSite === 'lax' || cookie.sameSite === 'Lax') {
      sameSite = 'Lax';
    }

    // 转换 expires (秒级时间戳)
    const expires = cookie.expirationDate
      ? Math.floor(cookie.expirationDate)
      : Math.floor(Date.now() / 1000) + 86400 * 7;

    return {
      name: cookie.name,
      value: cookie.value,
      domain: domain,
      path: cookie.path || '/',
      expires: expires,
      httpOnly: cookie.httpOnly || false,
      secure: cookie.secure !== false,
      sameSite: sameSite
    };
  });

  return {
    cookies: convertedCookies,
    origins: [
      {
        origin: 'https://www.fotmob.com',
        localStorage: []
      }
    ]
  };
}

/**
 * 主函数
 */
async function main() {
  console.log(`${LOG_PREFIX} 启动 TOTAL WAR Cookie 物理注入`);
  console.log(`${LOG_PREFIX} 原始 Cookie 数量: ${RAW_COOKIES.length}`);

  try {
    // 转换格式
    const storageState = convertToStorageState(RAW_COOKIES);
    console.log(`${LOG_PREFIX} ✓ 格式转换完成`);

    // V4.51-TOTAL-WAR: 使用 /tmp 目录避免权限问题
    const sessionsDir = '/tmp/titan_sessions';
    await fs.mkdir(sessionsDir, { recursive: true });

    // 写入文件
    const outputPath = path.join(sessionsDir, 'manual_bridge_session_TOTAL_WAR.json');
    await fs.writeFile(outputPath, JSON.stringify(storageState, null, 2));

    console.log(`${LOG_PREFIX} ✓ Cookie 已物理注入`);
    console.log(`${LOG_PREFIX} 输出文件: ${outputPath}`);
    console.log(`${LOG_PREFIX} Cookie 总数: ${storageState.cookies.length}`);
    console.log(`${LOG_PREFIX} 包含关键 Cookie:`);
    console.log(`  - turnstile_verified (人机验证通过标记)`);
    console.log(`  - __eoi, __gads, __gpi (广告/追踪)`);
    console.log(`  - _ga* (Google Analytics)`);
    console.log(`  - g_state (登录状态)`);
    console.log(`  - NEXT_LOCALE (语言设置)`);

    return outputPath;

  } catch (error) {
    console.error(`${LOG_PREFIX} ✗ 注入失败:`, error.message);
    process.exit(1);
  }
}

// 执行
main().then(path => {
  console.log(`\n✓ TOTAL WAR 会话文件已生成: ${path}`);
  process.exit(0);
}).catch(err => {
  console.error('致命错误:', err);
  process.exit(1);
});
