# FotMob爬虫部署指南

## 🎯 概述

本指南提供FotMob历史数据批量回填的完整部署方案，支持后台运行和Docker容器化部署。

## 📦 方案一：后台运行（推荐用于快速测试）

### 1. 使用 nohup 运行
```bash
# 基本用法 - 回填2024年数据
nohup python scripts/batch_backfill.py --start 20240101 --end 20241231 > logs/backfill_2024.log 2>&1 &

# 带详细日志运行
nohup python scripts/batch_backfill.py --start 20240101 --end 20241231 --verbose > logs/backfill_2024_detailed.log 2>&1 &

# 查看进程
ps aux | grep batch_backfill

# 查看实时日志
tail -f logs/backfill_2024.log

# 停止进程
kill <PID>
```

### 2. 使用 screen 运行
```bash
# 创建新的screen会话
screen -S fotmob_backfill

# 在screen中运行脚本
python scripts/batch_backfill.py --start 20230101 --end 20241231

# 分离screen会话（按Ctrl+A然后按D）
# 重新连接到screen会话
screen -r fotmob_backfill

# 查看所有screen会话
screen -ls

# 杀死screen会话
screen -X -S fotmob_backfill quit
```

### 3. 使用 tmux 运行（推荐）
```bash
# 创建新的tmux会话
tmux new-session -d -s fotmob_backfill 'python scripts/batch_backfill.py --start 20230101 --end 20241231'

# 查看会话
tmux list-sessions

# 连接到会话
tmux attach-session -t fotmob_backfill

# 分离会话（按Ctrl+B然后按D）
# 杀死会话
tmux kill-session -t fotmob_backfill
```

## 🐳 方案二：Docker Compose 部署（推荐用于生产环境）

### 1. 一键部署
```bash
# 使用提供的部署脚本
./scripts/deploy_crawler.sh

# 或手动部署
docker-compose -f docker-compose.crawler.yml up -d
```

### 2. 服务管理
```bash
# 查看服务状态
docker-compose -f docker-compose.crawler.yml ps

# 查看日志
docker-compose -f docker-compose.crawler.yml logs -f fotmob-crawler

# 进入爬虫容器
docker-compose -f docker-compose.crawler.yml exec fotmob-crawler bash

# 停止服务
docker-compose -f docker-compose.crawler.yml down

# 重新构建镜像
docker-compose -f docker-compose.crawler.yml build --no-cache fotmob-crawler
```

### 3. 监控面板
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3001 (admin/admin123)

## 🔧 核心特性

### 智能IP保护
- ✅ **随机休眠**: 每次采集后休眠10-30秒
- ✅ **错误重试**: 失败后自动重试，间隔30-60秒
- ✅ **断点续传**: 支持中断后继续执行
- ✅ **进度跟踪**: 实时保存采集状态

### 数据质量保证
- ✅ **100%真实数据**: 基于Playwright浏览器自动化
- ✅ **完整API拦截**: 拦截真实FotMob API响应
- ✅ **结构化输出**: 标准JSON格式，易于处理
- ✅ **元数据支持**: 包含采集时间和来源信息

### 运维友好
- ✅ **详细日志**: 分级日志输出，支持调试
- ✅ **状态持久化**: JSON文件保存采集进度
- ✅ **错误恢复**: 单日失败不影响整体进程
- ✅ **资源控制**: CPU和内存限制，防止过度消耗

## 📊 使用场景

### 1. 快速测试（本地运行）
```bash
# 采集今天数据
python scripts/run_fotmob_scraper.py --date today --no-export

# 采集最近7天数据
python scripts/run_fotmob_scraper.py --batch --days 7
```

### 2. 批量回填（后台运行）
```bash
# 回填2024年全年数据
nohup python scripts/batch_backfill.py --start 20240101 --end 20241231 --verbose > logs/backfill_2024.log 2>&1 &
```

### 3. 生产部署（Docker）
```bash
# 完整容器化部署
./scripts/deploy_crawler.sh

# 监控采集状态
docker-compose -f docker-compose.crawler.yml logs -f fotmob-crawler
```

## 📁 文件结构

```
scripts/
├── batch_backfill.py              # 🎯 批量回填脚本
├── run_fotmob_scraper.py          # 🎯 单日采集CLI
└── deploy_crawler.sh              # 🎯 一键部署脚本

docker-compose.crawler.yml         # 🐳 爬虫专用Docker配置
Dockerfile.crawler                 # 🐳 爬虫镜像构建文件
monitoring/
└── prometheus.yml                 # 📊 监控配置

data/fotmob/historical/            # 📂 历史数据存储
logs/                              # 📝 日志文件
```

## 🔍 监控和故障排除

### 查看采集状态
```bash
# 查看状态文件
cat data/fotmob/historical/backfill_status.json

# 查看日志文件
tail -f logs/backfill.log

# 检查数据文件
ls -la data/fotmob/historical/fotmob_matches_*.json
```

### 常见问题

#### 1. 采集失败率高
- 检查网络连接
- 增加休眠时间
- 查看FotMob网站是否正常访问

#### 2. 容器启动失败
- 检查Docker和Docker Compose版本
- 确保端口未被占用
- 查看容器日志排查具体错误

#### 3. 数据质量验证
```python
# 验证数据真实性
import json
with open('data/fotmob/historical/fotmob_matches_20241201.json') as f:
    data = json.load(f)
    print(f"采集时间: {data['collection_time']}")
    print(f"比赛数量: {data['total_matches']}")
    print(f"示例比赛: {data['matches'][0] if data['matches'] else '无数据'}")
```

## 🎉 部署验证

部署完成后，可通过以下方式验证：

1. **检查进程状态**
   ```bash
   ps aux | grep batch_backfill  # 本地运行
   docker-compose -f docker-compose.crawler.yml ps  # Docker运行
   ```

2. **查看采集日志**
   ```bash
   tail -f logs/backfill.log  # 本地运行
   docker-compose -f docker-compose.crawler.yml logs fotmob-crawler  # Docker运行
   ```

3. **验证数据文件**
   ```bash
   ls -la data/fotmob/historical/
   ```

4. **检查监控面板**
   - Prometheus: http://localhost:9090
   - Grafana: http://localhost:3001

---

**⚡ 提醒**: 无论使用哪种部署方式，爬虫都会自动执行智能休眠策略，保护IP避免被FotMob封锁。这是确保长期稳定运行的关键特性。