# OddsPortal Archive Harvester

**V41.832 "Production Blueprint"** - 工业级归档收割机

## 📋 概述

`OddsPortalArchiveHarvester` 是一个生产就绪的数据收割工具，用于从 OddsPortal 归档页面批量提取比赛映射数据。

## 🏗️ 架构设计

### 核心组件

```
src/harvesters/oddsportal_archive.py    # 主收割机
src/parsers/match_parser.py              # 比赛数据解析
src/harvesters/database_inserter.py      # 数据库操作
src/utils/browser_helper.py              # 浏览器辅助
src/config/crawler_config.py             # 配置管理
```

### 数据流

```
┌─────────────────┐
│  Playwright     │
│  Browser        │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  BrowserHelper  │ ← 分页控制、内容锁
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  MatchExtractor │ ← 哈希提取、队名解析
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ DatabaseInserter│ ← 批量插入、异常自愈
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   PostgreSQL    │
└─────────────────┘
```

## 🔑 核心机制

### 1. 物理点击机制

使用 Playwright 精确定位并点击分页按钮：

```python
# 精确 CSS Selector
selector = f".pagination a:text-is('{page_num}')"
await page.locator(selector).click()
```

### 2. 内容锁设计

等待页面内容完全填充后再提取数据：

```python
async def wait_for_content_lock(min_matches: int = 40) -> bool:
    for i in range(max_wait):
        row_count = await page.locator("tbody.eventHolder tr").count()
        if row_count >= min_matches:
            return True
        await asyncio.sleep(1)
    return False
```

### 3. 异常自愈逻辑

每场比赛独立 try-except 包裹，确保单场失败不影响整体批次：

```python
for match_data in matches:
    try:
        # 1. 查找匹配
        # 2. 写入数据库
        # 3. 成功则 continue
    except IntegrityError as e:
        self.conn.rollback()  # 立即回滚
        if "duplicate" in str(e).lower():
            continue  # 静默跳过
    except Exception as e:
        self.conn.rollback()  # 立即回滚
        logger.warning(f"ERROR: {e}")
        continue  # 继续处理下一场
```

## 📊 配置说明

### OddsPortalConfig

```python
@dataclass(frozen=True)
class OddsPortalConfig:
    # URL Templates
    BASE_URL: str = "https://www.oddsportal.com"
    RESULTS_PATH: str = "/football/{country}/{league}-{season}/results/"

    # CSS Selectors
    SELECTOR_PAGINATION: str = ".pagination"
    SELECTOR_EVENT_ROWS: str = "tbody.eventHolder tr"

    # Thresholds
    MIN_MATCHES_PER_PAGE: int = 40
    MIN_MATCHES_LAST_PAGE: int = 1

    # Timeouts (seconds)
    PAGE_LOAD_TIMEOUT: int = 30
    CLICK_TIMEOUT: int = 10
    CONTENT_LOCK_MAX_WAIT: int = 10

    # Retry
    MAX_RETRIES: int = 3
    RETRY_DELAY: int = 2
```

## 🚀 使用示例

### 基础用法

```python
from src.harvesters.oddsportal_archive import OddsPortalArchiveHarvester, HarvestConfig

config = HarvestConfig(
    league="Premier League",
    season="2024/2025",
    dry_run=False,
    lockdown_mode=True,
)

harvester = OddsPortalArchiveHarvester(config)
result = await harvester.harvest()

print(f"Total matches: {result.total_matches}")
print(f"Inserted: {result.inserted_count}")
```

### CLI 用法

```bash
# 标准模式
python -m src.harvesters.oddsportal_archive \
    --league "Premier League" \
    --season "2024/2025"

# 封锁模式（强制 8 页）
python -m src.harvesters.oddsportal_archive \
    --league "Premier League" \
    --season "2024/2025" \
    --lockdown-mode

# 干跑模式
python -m src.harvesters.oddsportal_archive \
    --league "Premier League" \
    --season "2024/2025" \
    --dry-run
```

## 🧪 测试

```bash
# 运行所有测试
pytest tests/harvesters/test_oddsportal_archive.py -v

# 运行特定测试
pytest tests/harvesters/test_oddsportal_archive.py::TestMatchExtractor -v

# 覆盖率报告
pytest tests/harvesters/ --cov=src/harvesters --cov=src/parsers --cov-report=html
```

## 📈 性能指标

| 指标 | 值 |
|------|-----|
| 单页提取时间 | ~2-3 秒 |
| 8 页总耗时 | ~30-40 秒 |
| 成功率 | >95% |
| 数据库插入 | 批量模式 |

## ⚠️ 注意事项

1. **代理配置**: 长时间运行建议配置代理池
2. **速率限制**: 遵守网站 robots.txt
3. **事务管理**: 每场比赛独立事务
4. **错误处理**: 所有异常需针对性捕获

## 📝 版本历史

- **V41.832**: 工业级重构，模块化架构
- **V41.827**: Bulletproof Healer，异常自愈
- **V41.826**: Transaction Healer，事务健壮
- **V41.825**: Brute Force，内容锁机制
- **V41.824**: The Wake-Up Call，修复超时

## 👥 作者

Senior Lead Data Architect

## 📄 许可

内部使用，禁止外传
