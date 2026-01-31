const fs = require('fs');
const path = require('path');
const file = path.join(__dirname, 'verify_component_sync.js');
let content = fs.readFileSync(file, 'utf8');

// 注入更深层的 DOM 抓取逻辑
content = content.replace(
    /const contentSelectors = \[([\s\S]*?)\];/,
    `const contentSelectors = [
        '.odd-row', '.odds-wrap', '.provider-name', 
        '.odds-now', '.odds-old', '.odds-change'
    ];`
);

fs.writeFileSync(file, content);
console.log('✓ 解析器准星已修正到赔率层级');
