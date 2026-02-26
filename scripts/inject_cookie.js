/**
 * V172-L2-06 手动 Cookie 注入工具
 * ================================
 *
 * 用途：将浏览器导出的 Cookie 字符串转换为 Playwright 兼容格式
 *
 * 使用方法：
 *   node scripts/inject_cookie.js "cookie_string_here"
 *
 * Cookie 字符串格式示例：
 *   "name1=value1; name2=value2; name3=value3"
 *
 * 从浏览器获取 Cookie 的方法：
 *   1. 打开 Chrome DevTools (F12)
 *   2. 进入 Application > Cookies > https://www.fotmob.com
 *   3. 复制所有 Cookie 或使用 EditThisCookie 扩展导出
 *
 * @module scripts/inject_cookie
 */

const fs = require('fs');
const path = require('path');

// ============================================================================
// 配置
// ============================================================================

const OUTPUT_PATH = './data/browser_profile/browser_state.json';
const DEFAULT_DOMAIN = '.fotmob.com';

// ============================================================================
// 权限处理
// ============================================================================

function ensureDirectoryExists(dir) {
    if (!fs.existsSync(dir)) {
        try {
            fs.mkdirSync(dir, { recursive: true });
            // 尝试设置权限
            try {
                fs.chmodSync(dir, 0o777);
            } catch (e) {
                // 忽略权限错误
            }
        } catch (e) {
            console.log(`⚠️  无法创建目录 ${dir}: ${e.message}`);
            console.log('   尝试使用当前目录...');
            return '.';
        }
    }
    return dir;
}

function writeFile(path, content) {
    try {
        fs.writeFileSync(path, content);
        return true;
    } catch (e) {
        if (e.code === 'EACCES') {
            // 权限问题，尝试删除后重写
            try {
                fs.unlinkSync(path);
                fs.writeFileSync(path, content);
                fs.chmodSync(path, 0o666);
                return true;
            } catch (e2) {
                return false;
            }
        }
        throw e;
    }
}

// ============================================================================
// 解析 Cookie 字符串
// ============================================================================

function parseCookieString(cookieStr) {
    const cookies = [];

    // 分割 Cookie
    const pairs = cookieStr.split(';').map(s => s.trim()).filter(s => s && s.includes('='));

    for (const pair of pairs) {
        const [name, ...valueParts] = pair.split('=');
        const value = valueParts.join('='); // 处理值中包含 = 的情况

        cookies.push({
            name: name.trim(),
            value: value.trim(),
            domain: DEFAULT_DOMAIN,
            path: '/',
            expires: Math.floor(Date.now() / 1000) + 86400 * 30, // 30天后过期
            httpOnly: false,
            secure: true,
            sameSite: 'Lax'
        });
    }

    return cookies;
}

// ============================================================================
// 主函数
// ============================================================================

function main() {
    const args = process.argv.slice(2);

    if (args.length === 0) {
        console.log('');
        console.log('═'.repeat(60));
        console.log('  V172-L2-06 手动 Cookie 注入工具');
        console.log('═'.repeat(60));
        console.log('');
        console.log('使用方法:');
        console.log('  node scripts/inject_cookie.js "cookie_string"');
        console.log('');
        console.log('示例:');
        console.log('  node scripts/inject_cookie.js "_ga=GA1.1.xxx; _gcl_au=1.1.xxx"');
        console.log('');
        console.log('从浏览器获取 Cookie:');
        console.log('  1. 打开 Chrome DevTools (F12)');
        console.log('  2. Application > Cookies > https://www.fotmob.com');
        console.log('  3. 复制 Cookie 值（格式: name=value; name2=value2）');
        console.log('');
        console.log('═'.repeat(60));
        process.exit(1);
    }

    const cookieStr = args.join(' ');
    console.log('');
    console.log('═'.repeat(60));
    console.log('  V172-L2-06 手动 Cookie 注入');
    console.log('═'.repeat(60));
    console.log('');
    console.log('📋 输入 Cookie 字符串:');
    console.log(`   ${cookieStr.substring(0, 60)}${cookieStr.length > 60 ? '...' : ''}`);
    console.log(`   长度: ${cookieStr.length} 字符`);

    // 解析
    const cookies = parseCookieString(cookieStr);
    console.log('');
    console.log(`✅ 解析到 ${cookies.length} 个 Cookie:`);

    cookies.forEach((c, i) => {
        console.log(`   ${i + 1}. ${c.name} = ${c.value.substring(0, 30)}${c.value.length > 30 ? '...' : ''}`);
    });

    // 构建 Playwright storageState
    const storageState = {
        cookies: cookies,
        origins: []
    };

    // 确保目录存在
    const dir = ensureDirectoryExists(path.dirname(OUTPUT_PATH));
    const outputPath = dir === '.' ? './browser_state.json' : OUTPUT_PATH;

    // 保存
    const content = JSON.stringify(storageState, null, 2);
    const success = writeFile(outputPath, content);

    if (success) {
        console.log('');
        console.log(`✅ 已保存到: ${outputPath}`);
        console.log('');
        console.log('🚀 下一步:');
        console.log('   docker exec football_prediction_dev node scripts/ops/test_stealth_v2.js');
    } else {
        console.log('');
        console.log('⚠️  无法保存到目标目录，输出到控制台:');
        console.log('');
        console.log('--- browser_state.json ---');
        console.log(content);
        console.log('--- END ---');
        console.log('');
        console.log('请手动复制上面的 JSON 到 ./data/browser_profile/browser_state.json');
    }

    console.log('');
    console.log('═'.repeat(60));
}

main();
