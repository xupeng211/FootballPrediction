const fs = require('fs');
const { execSync } = require('child_process');
const path = require('path');

const proxyFile = path.join(process.cwd(), 'config/active_proxies.json');
const proxyData = JSON.parse(fs.readFileSync(proxyFile, 'utf8'));
const proxies = proxyData.proxies;

console.log(`[Genesis.Maintenance] Starting physical scan for ${proxies.length} nodes...`);

const cleanProxies = [];

for (const proxy of proxies) {
    try {
        const url = `${proxy.protocol}://${proxy.host}:${proxy.port}`;
        console.log(`Testing Port ${proxy.port}...`);
        
        // 使用 curl --write-out 获取状态码，忽略输出
        const cmd = `curl -s -o /dev/null -w "%{http_code}" --proxy ${url} https://www.oddsportal.com --connect-timeout 10 --max-time 15`;
        const statusCode = execSync(cmd).toString().trim();
        
        // 只要有响应（即使是 403 封锁），说明代理节点本身是活的
        if (statusCode !== "000") {
            console.log(`✅ Port ${proxy.port} is alive (HTTP ${statusCode}).`);
            cleanProxies.push(proxy);
        } else {
            console.log(`❌ Port ${proxy.port} dead (No response).`);
        }
    } catch (err) {
        console.log(`❌ Port ${proxy.port} failed: ${err.message.split('\n')[0]}`);
    }
}

console.log(`[Genesis.Maintenance] Scan complete. Clean nodes: ${cleanProxies.length}/${proxies.length}`);

if (cleanProxies.length > 0) {
    proxyData.proxies = cleanProxies;
    proxyData.scan_summary.active_nodes = cleanProxies.length;
    proxyData.last_updated = new Date().toISOString();
    fs.writeFileSync(proxyFile, JSON.stringify(proxyData, null, 2));
    console.log(`[Genesis.Maintenance] config/active_proxies.json updated.`);
} else {
    console.log(`[Genesis.Maintenance] No clean nodes found. Keeping existing config to avoid total blackout.`);
}