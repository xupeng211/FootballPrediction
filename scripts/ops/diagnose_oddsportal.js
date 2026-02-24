/**
 * OddsPortal 页面诊断脚本
 */

const { chromium } = require('playwright');

async function findRealMatch() {
    console.log('=== 查找真实比赛 ===\n');

    const browser = await chromium.launch({
        headless: true,
        args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-blink-features=AutomationControlled']
    });

    const context = await browser.newContext({
        userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    });

    const page = await context.newPage();

    // 访问英超联赛列表
    const url = 'https://www.oddsportal.com/football/england/premier-league/';
    console.log('📡 访问:', url);

    try {
        await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 30000 });

        // 等待更长时间让 JS 渲染
        console.log('⏳ 等待页面渲染...');
        await page.waitForTimeout(10000);

        // 检查页面标题
        const title = await page.title();
        console.log('📄 页面标题:', title);

        // 获取所有链接
        const allLinks = await page.evaluate(() => {
            const links = document.querySelectorAll('a[href]');
            const result = [];
            links.forEach(a => {
                const href = a.getAttribute('href') || '';
                const text = (a.innerText || '').trim();
                if (href.length > 10 && text.length > 3 && !href.includes('#')) {
                    result.push({ text: text.substring(0, 60), href: href });
                }
            });
            return result;
        });

        // 过滤出比赛链接
        const matchLinks = allLinks.filter(l => {
            const href = l.href;
            const parts = href.split('/').filter(p => p.length > 0);
            if (parts.length >= 5) {
                const lastPart = parts[parts.length - 1];
                if (lastPart.includes('-') && !lastPart.includes('league') && !lastPart.includes('oddsportal')) {
                    return true;
                }
            }
            return false;
        });

        console.log('\n🔗 比赛链接 (前10个):');
        const uniqueHrefs = [...new Set(matchLinks.map(l => l.href))];
        const topLinks = uniqueHrefs.slice(0, 10);

        topLinks.forEach((href, i) => {
            const link = matchLinks.find(l => l.href === href);
            console.log(`  ${i + 1}. ${link ? link.text : 'N/A'}`);
            console.log(`      -> ${href}`);
        });

        // 获取页面完整内容
        const bodyText = await page.evaluate(() => document.body.innerText);

        console.log('\n📝 页面内容 (前1000字符):');
        console.log(bodyText.substring(0, 1000));

        // 如果找到比赛链接，访问第一个
        if (topLinks.length > 0) {
            const matchUrl = topLinks[0];
            console.log('\n🎯 尝试访问比赛页面:', matchUrl);

            await page.goto(matchUrl, { waitUntil: 'domcontentloaded', timeout: 30000 });
            await page.waitForTimeout(10000);

            const matchTitle = await page.title();
            const matchBody = await page.evaluate(() => document.body.innerText);

            console.log('📄 比赛页面标题:', matchTitle);
            console.log('\n📝 比赛页面内容 (前1200字符):');
            console.log(matchBody.substring(0, 1200));

            // 检查关键字
            const matchKeywords = ['bet365', 'Pinnacle', '1X2', 'odds', 'Opening', 'Closing'];
            console.log('\n🔍 比赛页面关键字:');
            matchKeywords.forEach(kw => {
                const found = matchBody.toLowerCase().includes(kw.toLowerCase());
                console.log(`  ${kw}: ${found ? '✅' : '❌'}`);
            });

            // 检查表格行
            const tableInfo = await page.evaluate(() => {
                const rows = document.querySelectorAll('tr, div.border-b, div.border-black-borders, div.flex');
                return {
                    rowCount: rows.length,
                    samples: Array.from(rows).slice(0, 3).map(r => r.innerText.substring(0, 100))
                };
            });

            console.log('\n📊 表格信息:');
            console.log('  行数:', tableInfo.rowCount);
            tableInfo.samples.forEach((s, i) => {
                console.log(`  示例 ${i + 1}:`, s);
            });
        }

    } catch (e) {
        console.error('❌ 错误:', e.message);
        console.error(e.stack);
    }

    await browser.close();
}

findRealMatch();
