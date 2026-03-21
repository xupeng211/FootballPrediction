# 🗺️ TITAN 全球赛事图谱 (Project Atlas)

> **版本**: V6.7-ATLAS  
> **最后更新**: 2026-03-20  
> **总计联赛**: 35 个  
> **覆盖范围**: 全球主要足球市场

---

## 📊 级别分布

| 级别 | 数量 | 描述 |
|------|------|------|
| ⭐ P0 | 7 | 核心联赛 (五大联赛 + 欧冠欧联) |
| 🏆 P1 | 7 | 杯赛与欧战 (国内杯赛 + 欧洲超级杯) |
| 🥈 P2 | 5 | 次级联赛 (英冠、西乙、德乙等) |
| 🌍 P3 | 8 | 全球联赛 (巴甲、阿甲、中超等) |
| 🌐 P4 | 5 | 国际赛事 (世界杯、欧洲杯等) |

---

## ⭐ P0 - 核心联赛 (7)

| ID | 联赛名称 | 国家/地区 | FotMob ID |
|----|----------|-----------|-----------|
| 47 | Premier League | England | 47 |
| 87 | La Liga | Spain | 87 |
| 54 | Bundesliga | Germany | 54 |
| 55 | Serie A | Italy | 55 |
| 53 | Ligue 1 | France | 53 |
| 42 | Champions League | Europe | 42 |
| 73 | Europa League | Europe | 73 |

---

## 🏆 P1 - 杯赛与欧战 (7)

| ID | 联赛名称 | 国家/地区 | FotMob ID |
|----|----------|-----------|-----------|
| 132 | FA Cup | England | 132 |
| 133 | EFL Cup | England | 133 |
| 209 | DFB Pokal | Germany | 209 |
| 138 | Copa del Rey | Spain | 138 |
| 141 | Coppa Italia | Italy | 141 |
| 181 | Coupe de France | France | 181 |
| 10216 | Conference League | Europe | 10216 |
| 74 | UEFA Super Cup | Europe | 74 |

---

## 🥈 P2 - 次级联赛 (5)

| ID | 联赛名称 | 国家/地区 | FotMob ID |
|----|----------|-----------|-----------|
| 48 | Championship | England | 48 |
| 140 | Segunda División | Spain | 140 |
| 146 | 2. Bundesliga | Germany | 146 |
| 156 | Serie B | Italy | 156 |
| 182 | Ligue 2 | France | 182 |

---

## 🌍 P3 - 全球联赛 (8)

| ID | 联赛名称 | 国家/地区 | FotMob ID |
|----|----------|-----------|-----------|
| 268 | Brasileirão | Brazil | 268 |
| 121 | Primera División | Argentina | 121 |
| 57 | Eredivisie | Netherlands | 57 |
| 61 | Primeira Liga | Portugal | 61 |
| 130 | MLS | USA | 130 |
| 110 | CSL | China | 110 |
| 109 | J1 League | Japan | 109 |
| 148 | J2 League | Japan | 148 |
| 71 | Süper Lig | Turkey | 71 |
| 60 | Liga MX | Mexico | 60 |

---

## 🌐 P4 - 国际赛事 (5)

| ID | 联赛名称 | 国家/地区 | FotMob ID |
|----|----------|-----------|-----------|
| 77 | FIFA World Cup | World | 77 |
| 50 | UEFA Euro | Europe | 50 |
| 10148 | UEFA Nations League | Europe | 10148 |
| 131 | Copa América | South America | 131 |
| 10004 | AFC Asian Cup | Asia | 10004 |

---

## 🚀 使用指南

### 扫描指定级别

```bash
# 扫描 P0 核心联赛 (默认)
node scripts/ops/titan_discovery.js --all

# 扫描 P1 杯赛
node scripts/ops/titan_discovery.js --tier=P1

# 扫描 P2 次级联赛
node scripts/ops/titan_discovery.js --tier=P2

# 扫描 P3 全球联赛
node scripts/ops/titan_discovery.js --tier=P3

# 扫描 P4 国际赛事
node scripts/ops/titan_discovery.js --tier=P4

# 扫描所有级别 (全球 30,000+ 赛事)
node scripts/ops/titan_discovery.js --all-tiers
```

### 扫描指定联赛

```bash
# 英超
node scripts/ops/titan_discovery.js --league=47

# 欧冠
node scripts/ops/titan_discovery.js --league=42

# 巴西甲
node scripts/ops/titan_discovery.js --league=268
```

### 列出所有联赛

```bash
node scripts/ops/titan_discovery.js --list
```

---

## 📈 覆盖统计

| 区域 | 覆盖程度 | 联赛数量 |
|------|----------|----------|
| 🇪🇺 欧洲 | 100% | 20 |
| 🌎 南美洲 | High | 2 |
| 🇺🇸 北美洲 | Medium | 2 |
| 🌏 亚洲 | Medium | 2 |
| 🌍 国际赛事 | High | 5 |

---

## 📝 数据来源

- **FotMob API**: 主要数据源
- **配置文件**: `config/leagues.json`
- **最后同步**: 2026-03-20

---

## 🏗️ V6.7 模块化架构说明

### 核心组件 (13 个模块)

L1 发现引擎 (Project Hound) 已从单体架构重构为模块化架构，遵循单一职责原则 (SRP) 和迪米特法则 (Law of Demeter)。

#### 1. 协调层 (Coordinator)
| 组件 | 文件 | 职责 | 行数 |
|------|------|------|------|
| **DiscoveryService** | `src/infrastructure/services/DiscoveryService.js` | 轻量级协调器，负责流程编排和组件调度 | ~480 |

#### 2. 提取层 (Extraction Layer)
| 组件 | 文件 | 职责 | 关键方法 |
|------|------|------|----------|
| **FotMobExtractor** | `src/infrastructure/services/FotMobExtractor.js` | 网页数据提取、DOM扫描、__NEXT_DATA__解析 | `extractFromWebpage()`, `searchViaDOM()`, `scanDOMForMatches()` |
| **DiscoveryParser** | `src/infrastructure/services/DiscoveryParser.js` | API响应解析、多路径嗅探、数据标准化 | `parse()`, `_extractRawMatches()`, `_transformMatches()` |

#### 3. 通信层 (Communication Layer)
| 组件 | 文件 | 职责 | 关键特性 |
|------|------|------|----------|
| **HttpClient** | `src/infrastructure/services/HttpClient.js` | HTTP通信客户端，支持Stealth/Raw双模式 | 快速失败原则、错误传播、HttpClientError |
| **BrowserProvider** | `src/infrastructure/services/BrowserProvider.js` | Playwright生命周期管理 | 反检测配置、会话预热、资源释放 |
| **NetworkInterceptor** | `src/infrastructure/services/NetworkInterceptor.js` | 网络请求监听与API捕获 | 噪音过滤、端点提取、回调通知 |

#### 4. 策略层 (Strategy Layer)
| 组件 | 文件 | 职责 | 关键方法 |
|------|------|------|----------|
| **SeasonStrategy** | `src/infrastructure/services/SeasonStrategy.js` | 赛季格式策略 (单年/双年) | `isSingleYearLeague()`, `format()`, `discover()` |

#### 5. 持久层 (Persistence Layer)
| 组件 | 文件 | 职责 | 关键特性 |
|------|------|------|----------|
| **FixtureRepository** | `src/infrastructure/services/FixtureRepository.js` | PostgreSQL数据持久化 | 批量Upsert、冲突处理、事务管理 |

#### 6. 展示层 (Presentation Layer)
| 组件 | 文件 | 职责 | 关键方法 |
|------|------|------|----------|
| **UIHelper** | `src/infrastructure/services/UIHelper.js` | CLI界面美化和数据格式化 | `printBanner()`, `generateReport()`, `printLeagueList()`, `printSearchResults()` |

### 架构设计原则

1. **单一职责**: 每个模块只负责一个明确的职责领域
2. **依赖注入**: 通过构造函数注入依赖，便于测试和替换
3. **错误传播**: 采用快速失败原则，严禁静默失败
4. **配置驱动**: 国际化数据外置到 `config/leagues.i18n.json`

### 数据流向

```
CLI (titan_discovery.js)
    ↓
DiscoveryService (协调器)
    ↓ 调度
HttpClient / BrowserProvider → FotMobExtractor → DiscoveryParser
    ↓ 数据
FixtureRepository (持久化)
    ↓ 报告
UIHelper (展示)
```

---

## 🔧 维护说明

如需添加新联赛，请编辑 `config/leagues.json` 并更新此文档。

```bash
# 生成此文档
node scripts/ops/titan_discovery.js --list > COMPETITIONS_ATLAS.md
```

---

**TITAN V6.7 - Project Atlas**  
*全球版图已入库，系统已具备横扫全球 30,000+ 赛事的能力*
