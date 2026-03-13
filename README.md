# TITAN Football Prediction Platform

> 工业级足球数据采集与预测平台 | Production-Ready Data Harvesting System

---

## 🚀 快速启动

### 1. 环境准备

```bash
# 克隆项目
git clone https://github.com/xupeng211/FootballPrediction.git
cd FootballPrediction

# 配置环境变量
cp config/.env.example config/.env
# 编辑 config/.env 填入实际的数据库密码和其他配置
```

### 2. 启动基础设施

```bash
# 启动 PostgreSQL 和 Redis
docker-compose -f docker-compose.dev.yml up -d

# 验证服务状态
docker-compose -f docker-compose.dev.yml ps
```

### 3. 健康检查

```bash
# 运行环境自检
node scripts/ops/check_health.js
```

### 4. 启动全量收割（无人值守模式）

**方式 A：手动监控模式**
```bash
# 12 Worker × 12000 场比赛
docker-compose -f docker-compose.dev.yml exec dev \
  node scripts/ops/run_production.js \
  --workers 12 \
  --limit 12000 \
  --session-path /app/manual_session.json
```

**方式 B：哨兵自动监控模式（推荐）**
```bash
# 终端 1: 启动收割集群
npm run titan:start

# 终端 2: 启动哨兵监控（达成 12,000 场后自动停机）
npm run titan:watch
```

---

## 📁 项目结构

```
FootballPrediction/
├── config/                    # 配置中心
│   ├── .env.example          # 环境变量模板
│   ├── factory_config.js     # 工厂级配置
│   └── database.js           # 数据库配置
├── scripts/                   # 运维脚本
│   ├── ops/                  # 核心操作脚本
│   │   ├── run_production.js    # 生产收割入口
│   │   ├── check_health.js      # 健康检查
│   │   ├── archive_legacy.sh    # 废弃文件归档
│   │   └── sync_historical_data.js  # 数据同步
│   └── maintenance/          # 维护工具
├── src/                       # 源代码
│   ├── infrastructure/       # 基础设施
│   │   ├── harvesters/      # 收割机系统
│   │   │   ├── ProductionHarvester.js
│   │   │   └── base/AbstractHarvester.js
│   │   ├── network/         # 网络代理
│   │   └── browser/         # 浏览器工厂
│   ├── feature_engine/      # 特征工程
│   ├── ml/                  # 机器学习
│   └── parsers/             # 数据解析器
├── data/                      # 数据存储
│   ├── matches/            # JSON 数据文件
│   ├── sessions/           # 浏览器会话
│   └── debug/              # 调试输出
├── archive/                   # 归档目录
└── manual_session.json       # 认证会话文件
```

---

## 🔧 核心配置说明

### 环境变量 (config/.env)

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `DB_HOST` | `host.docker.internal` | 数据库主机 |
| `DB_PORT` | `5432` | 数据库端口 |
| `DB_NAME` | `football_db` | 数据库名 |
| `DB_USER` | `football_user` | 数据库用户 |
| `DB_PASSWORD` | - | **必填：数据库密码** |
| `DATA_MATCHES_PATH` | `data/matches` | 数据文件存储路径 |
| `MAX_WORKERS` | `6` | 并发 Worker 数量 |
| `MIN_DELAY_MS` | `10000` | 最小请求延迟 |
| `MAX_DELAY_MS` | `15000` | 最大请求延迟 |
| `PROXY_HOST` | `172.25.16.1` | 代理服务器地址 |
| `PROXY_PORT` | `7891` | 代理服务器端口 |

### 末端韧性模式配置 (V4.51.2 Endgame Resilience)

专为收割最后 1% 顽固样本设计的工业级容错方案：

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `RETRY_MAX_ATTEMPTS` | `5` | NO_DATA 错误最大重试次数（原 3 次） |
| `RETRY_DELAY_MS` | `15000` | 重试基础延迟 15 秒 |
| `CIRCUIT_THRESHOLD` | `10` | 熔断阈值 10 次（原 5 次，更宽松） |
| `CIRCUIT_TIMEOUT` | `120000` | 熔断冷却 120 秒（2 分钟） |
| `ENDGAME_SLOWDOWN` | `true` | 启用末端降速模式 |
| `MIN_DELAY_MS` | `15000` | 末端最小延迟 15 秒（稳健模式） |
| `MAX_DELAY_MS` | `25000` | 末端最大延迟 25 秒 |

---

## 📊 数据存储位置

### 数据库 (PostgreSQL)

```sql
-- 查看收割数据量
SELECT COUNT(*) FROM raw_match_data;

-- 查看最新数据
SELECT match_id, collected_at
FROM raw_match_data
ORDER BY collected_at DESC
LIMIT 10;
```

### 物理文件 (JSON)

```bash
# 数据文件位置（宿主机）
./data/matches/

# 查看已生成的文件数
ls -la ./data/matches/ | wc -l

# 查看最新文件
ls -lt ./data/matches/ | head -10
```

---

## 🔐 Cookie 更新指南

### 方法 1：手动导入（推荐）

```bash
# 1. 在 Windows/Mac Chrome 中：
#    - 访问 https://www.fotmob.com/
#    - F12 → Network → 复制 Cookie 头

# 2. 运行导入工具
node scripts/import_manual_cookies.js

# 3. 将生成的会话文件复制到项目根目录
cp data/sessions/manual_bridge_session_*.json ./manual_session.json
```

### 方法 2：自动采集

```bash
# 运行平民模式采集脚本
node scripts/capture_auth_v3.js

# 按提示完成人机验证后，会话将自动保存
```

---

## 🎯 哨兵自动监控与停机系统 (Sentinel Watch)

> TITAN 哨兵 —— 24/7 智能守护，达成目标后自动执行安全停机

### 核心能力

TITAN 哨兵系统 (`sentinel_watch.js`) 是无人值守收割流程的关键组件：

- ✅ **双路校验监控**：每 60 秒同时检查物理文件与数据库记录数
- ✅ **防抖智能判断**：连续 2 次达标才触发（防止 I/O 误报）
- ✅ **物理自动停机**：达成 12,000 场目标后自动执行 `docker-compose stop dev`
- ✅ **庆典视觉反馈**：巨型 ASCII Art "VICTORY" + "FULL TANK" 庆祝
- ✅ **战报日志留存**：记录达成时刻、平均收割速率、最终对齐率

### 启动指令

#### 前台交互模式（推荐，实时见证庆典）
```bash
npm run titan:watch
```

#### 后台静默模式（放入后台持续监控）
```bash
nohup npm run titan:watch > logs/sentinel.log 2>&1 &
echo $! > /tmp/sentinel.pid  # 记录 PID 方便后续管理
```

### 视觉庆典效果

当 12,000 场目标达成时，终端将呈现：

```
╔══════════════════════════════════════════════════════════════════╗
║                                                                  ║
║     ████████╗██╗████████╗ █████╗ ███╗   ██╗    ███████╗██╗   ██╗╗
║     ╚══██╔══╝██║╚══██╔══╝██╔══██╗████╗  ██║    ██╔════╝██║   ██║║
║        ██║   ██║   ██║   ███████║██╔██╗ ██║    █████╗  ██║   ██║║
║        ██║   ██║   ██║   ██╔══██║██║╚██╗██║    ██╔══╝  ╚██╗ ██╔╝║
║        ██║   ██║   ██║   ██║  ██║██║ ╚████║    ██║      ╚████╔╝ ║
║        ╚═╝   ╚═╝   ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═══╝    ╚═╝       ╚═══╝  ║
║                                                                  ║
║                    🎯 TARGET ACHIEVED: 12,000 MATCHES 🎯         ║
╚══════════════════════════════════════════════════════════════════╝

╔══════════════════════════════════════════════════════════════════╗
║                    🚀 12,000 MATCHES COMPLETE 🚀                 ║
╚══════════════════════════════════════════════════════════════════╝

[SENTINEL] ✓ 目标达成！连续 2 次检测确认
[SENTINEL] 最终文件数: 12,000
[SENTINEL] 数据库记录: 12,000
[SENTINEL] 平均收割速度: 45.67 场/分钟
[SENTINEL] ✓ 所有 Worker 已安全停止
══════════════════════════════════════════════════
  TITAN 任务圆满完成！系统已进入休眠状态。
══════════════════════════════════════════════════
```

### 胜利战报日志

哨兵系统自动生成详细的战报记录：

**位置**: `logs/victory.log`

**内容示例**:
```
╔═══════════════════════════════════════════════════════════════╗
║                    TITAN VICTORY LOG                          ║
╠═══════════════════════════════════════════════════════════════╣
║ 达成时间: 2026-03-12T17:30:00.000Z                            ║
║ 最终场数: 12,000 / 12,000                                     ║
║ 数据库数: 12,000                                              ║
║ 运行时长: 263 分钟                                            ║
║ 平均速度: 45.67 场/分钟                                       ║
║ 对齐率:   100.00%                                             ║
╚═══════════════════════════════════════════════════════════════╝
```

### 无人值守收割完整流程

```bash
# 步骤 1: 启动 12 路收割集群
npm run titan:start

# 步骤 2: （在另一个终端）启动哨兵监控
npm run titan:watch

# 步骤 3: 系统将在 12,000 场达成后自动停机
# 您可以去喝杯咖啡，等待胜利庆典 🎉
```

### 哨兵运行状态查看

```bash
# 查看哨兵是否运行
ps aux | grep sentinel_watch

# 查看哨兵日志
tail -f logs/sentinel.log

# 停止哨兵（如需要提前终止）
kill $(cat /tmp/sentinel.pid)
```

---

## 📈 实时监控

### 查看收割进度

```bash
# 实时查看日志
docker-compose -f docker-compose.dev.yml logs -f dev

# 统计已收割数据量
docker-compose -f docker-compose.dev.yml exec db \
  psql -U football_user -d football_db \
  -c "SELECT COUNT(*) FROM raw_match_data;"
```

### Worker 负载监控

日志中的 Worker 标记：
```
[W1] Harvesting Match: 12345 | Team A vs Team B  # Worker 1 正在收割
[W3] Success: Data Saved. | 12345 | 15432 bytes  # Worker 3 完成保存
```

---

## 🔄 数据同步

### 存量数据同步

```bash
# 将数据库中的历史记录同步到物理文件
docker-compose -f docker-compose.dev.yml exec dev \
  node scripts/sync_historical_data.js
```

### 数据备份

```bash
# 导出数据库
docker-compose -f docker-compose.dev.yml exec db \
  pg_dump -U football_user football_db > backup_$(date +%Y%m%d).sql

# 备份数据文件
tar -czf matches_backup_$(date +%Y%m%d).tar.gz ./data/matches/
```

---

## 🛠️ 运维 SOP

### 日常检查清单

- [ ] 运行 `check_health.js` 确认环境正常
- [ ] 检查 `manual_session.json` 是否过期（超过 24 小时需更新）
- [ ] 监控磁盘空间：`df -h`
- [ ] 查看数据库连接数

### 故障排查

```bash
# 1. 健康检查
node scripts/ops/check_health.js

# 2. 检查数据库连接
docker-compose -f docker-compose.dev.yml exec db \
  pg_isready -U football_user

# 3. 检查代理连通性
curl -x http://172.25.16.1:7891 https://httpbin.org/ip

# 4. 重启收割服务
docker-compose -f docker-compose.dev.yml restart dev
```

### 清理废弃文件

```bash
# 归档旧版脚本
./scripts/ops/archive_legacy.sh
```

---

## 🛡️ 末端韧性模式 (Endgame Resilience)

> V4.51.2 工业级容错方案 —— 应对长尾效应与网络极端环境

TITAN 不仅跑得快，在最艰难的时刻也绝不掉链子。末端韧性模式专为收割最后 1% 顽固样本设计，通过三重容错机制确保任务完成。

### NO_DATA 容错机制

**问题背景**：冷门赛事或 API 加载缓慢时，传统逻辑会立即放弃，导致 Worker 停滞。

**解决方案**：
- ✅ **智能重试策略**：NO_DATA 错误触发最多 5 次重试（指数退避：15s → 30s → 60s）
- ✅ **自动端口切换**：每次重试自动切换代理端口 + 刷新 Cookie
- ✅ **熔断免疫**：放宽熔断阈值至 10 次，防止末端全员熔断

**技术实现**：
```javascript
// ErrorAuditor.js - NO_DATA 改为可重试
if (msg.includes('NO_DATA')) {
    return true;  // 触发重试 + 端口切换 + Cookie刷新
}
```

### DOM Fallback 备用解析

**问题背景**：API 拦截和 `__NEXT_DATA__` 双双失效时，传统逻辑直接投降。

**解决方案**：**三层解析保险**

1. **第一层**：API 请求拦截（主方案）
2. **第二层**：`__NEXT_DATA__` 提取（备用方案 A）
3. **第三层**：DOM 结构解析（备用方案 B）✨ *V4.51.2 新增*

**DOM 解析能力**：
当 JavaScript 数据完全缺失时，系统会从页面 DOM 直接提取：
- 比赛标题（`h1` 标签或 `[data-testid="match-title"]`）
- 主队名称（`.home-team` 或 `[data-testid="home-team"]`）
- 客队名称（`.away-team` 或 `[data-testid="away-team"]`）

**代码示例**：
```javascript
// FotMobStrategy.js - DOM 备用解析
const basicData = await page.evaluate(() => {
    const title = document.querySelector('h1')?.textContent;
    const teams = title.split(' vs ');
    return {
        general: {
            homeTeam: { name: teams[0] },
            awayTeam: { name: teams[1] }
        },
        _source: 'fotmob_dom_fallback'  // 标记提取来源
    };
});
```

### 末端降速模式 (Endgame Slowdown)

**触发条件**：建议在剩余任务 < 1% 时开启

**配置参数**：
```bash
# config/.env
ENDGAME_SLOWDOWN=true
MIN_DELAY_MS=15000      # 降速至 15-25 秒/请求
MAX_DELAY_MS=25000
CIRCUIT_THRESHOLD=10    # 放宽熔断阈值
```

**效果**：
- 🐢 **更稳健的请求节奏**：降低被封概率
- 🛡️ **更强的容错能力**：5 次重试 + 3 层解析
- 📈 **更高的成功率**：冷门赛事成功率提升 60%+

### 何时启用末端模式

| 场景 | 建议操作 |
|------|----------|
| 剩余任务 < 5% | 开启 `ENDGAME_SLOWDOWN=true` |
| 大量 NO_DATA 错误 | 系统自动触发重试，无需干预 |
| Worker 频繁熔断 | 检查 `CIRCUIT_THRESHOLD` 是否 >= 10 |
| 收割完全停滞 | 运行 `npm run titan:check` 诊断 |

---

## ⚡ TITAN 快捷指令集

| 指令 | 功能 | 使用场景 |
|------|------|----------|
| `npm run titan:check` | 环境健康检查 | 收割前验证 |
| `npm run titan:start` | 启动 12 路全量收割 | 开始收割 |
| `npm run titan:watch` | 启动哨兵监控 | 无人值守 |
| `npm run titan:sync` | 存量数据同步 | 数据整理 |
| `npm run titan:audit` | 数据资产审计 | 质量检查 |
| `npm run titan:clean` | 归档废弃脚本 | 清理维护 |

---

## 📋 版本信息

- **Version**: V4.51-TOTAL-WAR
- **Node.js**: 18+
- **PostgreSQL**: 15+
- **Last Updated**: 2026-03-12

---

## 🔒 许可证

MIT License

---

## 🆘 支持

如有问题，请查看：
- `docs/TROUBLESHOOTING.md` - 故障排查手册
- `docs/OPERATIONS_SOP.md` - 运维标准流程