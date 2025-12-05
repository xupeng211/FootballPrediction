# FotMob 数据采集寻路指南
# FotMob Data Collection Roadmap

> **🚨 重要警告**：本文档包含**绝对真理**和**血泪教训**，所有后续开发必须严格遵守！
>
> **⚡ 核心成就**：经过漫长的攻坚，我们终于打通了 FotMob 的全链路采集，从 API 废墟中杀出了一条血路！

---

## 🎯 战略总览 (Strategic Overview)

### 📊 采集架构
```
FotMob 数据采集 = L1 (赛程) + L2 (详情) + 核心技术栈
    ↓              ↓              ↓
联赛页面策略    HTML 解析策略    统一技术栈
```

### 🏆 核心突破
- **L1 赛程采集**: 弃用按日期查询，改用**直接解析联赛总览页**
- **L2 详情采集**: HTML 解析 + 手动 GZIP 解压，从 `__NEXT_DATA__` 中提取
- **统一技术**: `requests` + `manual_decompress_response` + 隐身 Header

---

## 🔥 绝对真理 (Absolute Truths)

### ❌ 严禁尝试 (Do NOT Attempt)

#### 1. **严禁 API 路径**
```bash
# 这些都是死亡陷阱！全部返回 404/401
/api/matches/xxxxxx
/api/leagues/47/matches
/api/teams/xxxxxx
/api/fixtures?date=20240217

# 结果：404 Not Found 或 401 Unauthorized
```

#### 2. **严禁 Playwright**
```python
# 🚫 错误示例：Playwright 太慢且不稳定
from playwright import sync_playwright
# 问题：
# - 启动慢 (3-5秒)
# - 资源消耗大
# - Docker 环境不稳定
# - 容易被反爬检测
```

#### 3. **严禁复杂 User-Agent 轮换**
```python
# 🚫 错误：过于复杂的伪装
user_agents = [...100个不同UA...]
headers = {"User-Agent": random.choice(user_agents)}
# 问题：过度工程化，反而增加被检测风险
```

### ✅ 必须遵守 (Must Follow)

#### 1. **GZIP 陷阱处理**
```python
# ✅ 正确：必须手动处理 GZIP
def _manual_decompress_response(self, response) -> str:
    """FotMob 返回的 HTML 可能是 GZIP 压缩的二进制流"""
    if response.content[:2] == b'\x1f\x8b':  # GZIP 魔数
        import gzip, io
        decompressed = gzip.GzipFile(fileobj=io.BytesIO(response.content)).read().decode('utf-8')
        return decompressed
    return response.text  # 回退到正常文本
```

#### 2. **纯 HTTP 解析 HTML**
```python
# ✅ 正确：纯 HTTP 请求 + HTML 解析
import requests
response = requests.get(url, headers=get_stealth_headers(), verify=False)
html_content = _manual_decompress_response(response)
nextjs_data = extract_nextjs_data(html_content)  # 提取 __NEXT_DATA__
```

#### 3. **标准隐身 Header**
```python
# ✅ 正确：简洁有效的请求头
def get_stealth_headers():
    return {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-GB,en;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
    }
```

---

## 🛣️ 数据路径 (Data Paths)

### L1 赛程数据提取路径
```javascript
// URL: https://www.fotmob.com/leagues/47/overview/premier-league
// 数据路径：
props.pageProps.overview.matches.fixtureInfo.teams[]

// 示例数据结构：
{
  "id": 8456,
  "name": "Manchester City"
}
// 获取：完整的 20 支英超球队列表
```

### L2 详情数据提取路径
```javascript
// URL: https://www.fotmob.com/match/{match_id}
// 数据路径：
props.pageProps.content.matchFacts  // 比赛事实
props.pageProps.content.stats        // 统计数据 (含 xG)
props.pageProps.content.lineup       // 阵容信息
props.pageProps.content.shotmap      // 射门图
props.pageProps.content.playerStats  // 球员统计

// xG 数据位置：
props.pageProps.content.stats.Periods.All.stats[].stats[]
{
  "title": "Expected Goals (xG)",
  "stats": [home_xg, away_xg]  // 主客队 xG 值
}
```

---

## ⚡ 生产工具链 (Production Toolchain)

### 核心文件 (Core Files)
```bash
# 🎯 生产脚本 (切勿修改)
src/jobs/run_season_backfill.py          # L1 赛程回填
src/collectors/html_fotmob_collector.py   # 核心采集器 (含 GZIP 处理)
scripts/run_fotmob_scraper.py            # 主采集入口
scripts/backfill_details_fotmob.py       # L2 详情采集

# 🔧 配置文件
.env.example                              # 环境变量模板
src/config/                              # 配置目录
```

### 执行命令 (Execution Commands)
```bash
# 🚀 启动完整采集
make dev                                  # 启动开发环境
python scripts/run_fotmob_scraper.py     # 采集主入口

# 📊 赛季回填 (L1)
python src/jobs/run_season_backfill.py   # 完整赛季数据

# 🎯 详情采集 (L2)
python scripts/backfill_details_fotmob.py # 单场比赛详情
```

---

## 🔧 技术细节 (Technical Details)

### GZIP 压缩处理
```python
# FotMob 的 GZIP 陷阱
# 问题：某些情况下返回 GZIP 压缩的二进制流，而不是 HTML 文本
# 解决：检测魔数 0x1f8b，手动解压

def handle_fotmob_response(response):
    if response.content and response.content[:2] == b'\x1f\x8b':
        # GZIP 压缩
        return manual_decompress(response)
    else:
        # 正常 HTML
        return response.text
```

### Next.js SSR 数据提取
```python
# 从 HTML 中提取 __NEXT_DATA__
def extract_nextjs_data(html):
    pattern = r'<script[^>]*id=["\']__NEXT_DATA__["\'][^>]*>(.*?)</script>'
    matches = re.findall(pattern, html, re.DOTALL)
    if matches:
        return json.loads(matches[0])
    return None
```

### Docker 环境优化
```python
# Docker 环境反爬检测对抗
# 1. 禁用 SSL 验证 (避免证书问题)
# 2. 使用标准浏览器 Header (避免异常特征)
# 3. 简化请求头 (避免过度伪装)
# 4. 不使用 Session (避免连接池特征)

requests.get(url, verify=False, headers=standard_headers)
```

---

## 🎯 成功案例 (Success Stories)

### 完整工作流程
```python
# 1. 初始化采集器
collector = HTMLFotMobCollector(enable_stealth=True)
await collector.initialize()

# 2. 采集 L1 赛程数据
season_url = "https://www.fotmob.com/leagues/47/overview/premier-league"
response = requests.get(season_url, headers=collector._get_current_headers())
html_content = collector._manual_decompress_response(response)
nextjs_data = extract_nextjs_data(html_content)
teams = nextjs_data["props"]["pageProps"]["overview"]["matches"]["fixtureInfo"]["teams"]

# 3. 采集 L2 详情数据
for team in teams:
    match_url = f"https://www.fotmob.com/match/{match_id}"
    # 同样的流程，提取 xG 等详细数据
```

### 验证结果
```bash
# 成功标志
✅ 20/20 支球队完整获取
✅ GZIP 解压正常工作
✅ Next.js 数据成功解析
✅ xG 数据提取完整
```

---

## ⚠️ 常见陷阱 (Common Pitfalls)

### 1. API 404 错误
```python
# ❌ 错误：尝试已废弃的 API
url = "https://www.fotmob.com/api/matches/123456"
# 结果：404 Not Found

# ✅ 正确：使用 HTML 页面
url = "https://www.fotmob.com/match/123456"
```

### 2. GZIP 乱码
```python
# ❌ 错误：直接使用 response.text
html = response.text  # 可能是乱码二进制

# ✅ 正确：检测并处理 GZIP
html = collector._manual_decompress_response(response)
```

### 3. 数据路径错误
```python
# ❌ 错误：API 路径思维
matches = data["matches"]  # API 才有的结构

# ✅ 正确：Next.js 路径
matches = data["props"]["pageProps"]["content"]  # HTML SSR 结构
```

---

## 🚀 未来扩展 (Future Extensions)

### 其他联赛支持
```bash
# 英超: /leagues/47/overview/premier-league
# 西甲: /leagues/87/overview/laliga
# 德甲: /leagues/54/overview/bundesliga
# 意甲: /leagues/55/overview/serie-a
# 法甲: /leagues/60/overview/ligue-1
```

### 历史数据采集
```python
# 利用 pageProps 中的赛季信息
seasons = data["props"]["pageProps"]["allAvailableSeasons"]
for season in seasons:
    # 切换赛季采集历史数据
    season_url = f"/leagues/47/overview/premier-league?season={season['id']}"
```

---

## 📋 检查清单 (Checklist)

### 开发前必读
- [ ] 熟读本文档 **3 遍**
- [ ] 理解 **GZIP 陷阱**
- [ ] 记住 **数据路径**
- [ ] 确认 **不使用 API**

### 代码审查要点
- [ ] 是否包含 `_manual_decompress_response`？
- [ ] 是否使用正确的数据路径？
- [ ] 是否避免了 Playwright？
- [ ] 是否使用了标准隐身 Header？

### 测试验证
- [ ] 能获取 20 支英超球队？
- [ ] GZIP 解压是否正常？
- [ ] xG 数据是否完整？
- [ ] Docker 环境是否稳定？

---

## 💡 终极原则 (Ultimate Principles)

1. **简单胜过复杂**：纯 HTTP 请求 > Playwright
2. **稳定胜过速度**：正确解压 > 快速失败
3. **直接胜过间接**：HTML 页面 > 废弃 API
4. **标准胜过伪装**：正常 Header > 过度 UA 轮换

> **🎯 记住**：我们是从失败中找到的唯一成功路径，不要轻易偏离！

---

**📅 文档版本**: v1.0
**🏷️ 标签**: 血泪经验 | 绝对真理 | 生产就绪
**🔒 状态**: 绝对稳定 | 严禁修改