# V41.235 赔率数据同步系统 - 生产运维手册

## 文档信息

| 属性 | 值 |
|------|-----|
| **系统名称** | Odds Sync System (赔率数据同步系统) |
| **版本** | V41.235 Production Ready |
| **发布日期** | 2026-01-19 |
| **维护团队** | Football Prediction Engineering |
| **状态** | Production Ready |

---

## 1. 系统架构

### 1.1 拓扑结构

```
┌─────────────────────────────────────────────────────────────────────┐
│                        数据采集层 (Data Collection)                  │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  IndustrialAuditor (src/core/scrapers/industrial_auditor.py) │  │
│  │  • Playwright 无头浏览器                                     │  │
│  │  • 懒滚动 + 智能轮询                                         │  │
│  │  • 33 位矩阵提取                                             │  │
│  │  • V41.231 网络韧性 (domcontentloaded + 3次重试)             │  │
│  │  • V41.232 视觉失效存证 (自动截图)                           │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────────────┐
│                        数据处理层 (Data Processing)                  │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  SequenceProcessor (industrial_auditor.py)                   │  │
│  │  • 三位一组切片算法                                          │  │
│  │  • [0:3] → Closing_Price (当前状态)                          │  │
│  │  • [-3:] → Initial_Price (初始状态)                          │  │
│  │  • 中间 → Movement_History (27 个中间态)                     │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────────────┐
│                        数据对齐层 (Data Alignment)                   │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  MatchLinker (src/services/match_linker.py)                  │  │
│  │  • 队名相似度匹配 (SequenceMatcher)                          │  │
│  │  • V41.232 队名缩写扩展 (80+ 欧洲俱乐部映射)                 │  │
│  │  • 时间窗口过滤 (48 小时)                                     │  │
│  │  • PostgreSQL 持久化                                         │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────────────┐
│                        数据存储层 (Data Storage)                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  PostgreSQL 15 + match_odds_intelligence 表                  │  │
│  │  • initial_price: JSONB (初盘赔率 [3 个])                    │  │
│  │  • closing_price: JSONB (终盘赔率 [3 个])                    │  │
│  │  • movement_history: JSONB (变动历史 [27 个])                │  │
│  │  • similarity_score: FLOAT (相似度 0-1)                     │  │
│  │  • link_method: VARCHAR (exact/fuzzy/none)                   │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

### 1.2 核心组件说明

| 组件 | 文件位置 | 职责 |
|------|----------|------|
| **IndustrialAuditor** | `src/core/scrapers/industrial_auditor.py` | 数据提取与序列处理 |
| **SequenceProcessor** | `industrial_auditor.py` (内部类) | 33 位矩阵切片算法 |
| **MatchLinker** | `src/services/match_linker.py` | 队名模糊匹配与数据库映射 |
| **run_odds_sync.py** | `run_odds_sync.py` | 生产入口脚本 |

---

## 2. 核心数据对齐逻辑

### 2.1 33 位矩阵业务含义

```
┌─────────────────────────────────────────────────────────────────┐
│                    33-Element Price Matrix                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  [0:3]   Closing_Price  ────────────► 当前状态 (终盘赔率)      │
│           [P1_home, PX_draw, P2_away]                          │
│                                                                 │
│  [3:30]  Movement_History ───────────► 中间态 (27 个时间点)    │
│           [t1, t2, t3, ..., t27]                               │
│                                                                 │
│  [30:33] Initial_Price  ────────────► 初始状态 (初盘赔率)      │
│           [P1_home, PX_draw, P2_away]                          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 序列切片算法

```python
# V41.230 标准算法 (SequenceProcessor.process)

# 标准模式 (33 元素)
if len(values) == 33:
    closing = values[0:3]      # [0, 1, 2]
    movement = values[3:-3]    # [3:30] = 27 个元素
    initial = values[-3:]      # [30, 31, 32]

# 降级模式 (非标准长度)
elif len(values) >= 6:
    closing = values[0:3]
    movement = values[3:-3] if len(values) > 6 else []
    initial = values[-3:]

# 极简模式 (3-5 元素)
elif len(values) >= 3:
    closing = values[:3]
    movement = []
    initial = []
```

### 2.3 队名相似度匹配

```python
# V41.232 队名标准化流程

def normalize_team_name(name: str) -> str:
    """
    步骤 1: 缩写扩展 (Man City → Manchester City)
    步骤 2: 转小写
    步骤 3: 移除特殊字符
    步骤 4: 移除后缀 (FC, United, City 等)
    步骤 5: 压缩多余空格
    """
```

**支持的缩写映射** (部分示例):
- `Man City` → `manchester city`
- `Barca` → `barcelona`
- `PSG` → `paris saint germain`
- `Bayern` → `bayern munich`
- `Juve` → `juventus`
- ... 80+ 欧洲俱乐部映射

---

## 3. 快速开始

### 3.1 环境准备

```bash
# 1. 启动数据库
make up

# 2. 安装依赖
pip install playwright curl-cffi psycopg2-binary
playwright install chromium

# 3. 验证代理连通性
python tests/smoke/test_proxy_connectivity.py
```

### 3.2 基础运行

```bash
# 提取数据（不存储）
python run_odds_sync.py --url "https://example.com/match" --extract-only

# 提取并存储（需要队名和时间）
python run_odds_sync.py --url "https://example.com/match" --output logs/odds.json

# 指定模式
python run_odds_sync.py --url "..." --patterns "Opening" "Closing"

# 调试模式（非无头）
python run_odds_sync.py --url "..." --no-headless

# 自定义代理端口
python run_odds_sync.py --url "..." --proxy-port 7893
```

### 3.3 V41.234 数据合龙测试

```bash
# 执行端到端测试
python scripts/ops/v41_234_great_alignment.py

# 输出示例:
# Step 1: Auto-Provisioning ✓
# Step 2: Query FotMob Data ✓ (20 matches)
# Step 3: Extract & Link ✓ (33-element matrix)
# Step 4: Final Commit ✓ (Records: 1)
```

---

## 4. 故障排除手册

### 4.1 常见问题诊断

#### 问题 1: 零实体提取 (entities_extracted == 0)

**现象**:
```
[INFO] Extraction complete: 0 entities
[INFO] Forensic screenshot saved: logs/last_extraction_failure_*.png
```

**诊断步骤**:
1. 检查截图文件 `logs/last_extraction_failure_*.png`
2. 确认目标页面是否有反爬检测（验证码、登录墙）
3. 检查网络延迟（90s 超时可能不够）

**解决方案**:
```bash
# 方案 A: 增加超时
python run_odds_sync.py --url "..." --timeout 60000

# 方案 B: 禁用无头模式调试
python run_odds_sync.py --url "..." --no-headless

# 方案 C: 切换代理端口
python run_odds_sync.py --url "..." --proxy-port 7893
```

#### 问题 2: 数据库连接失败

**现象**:
```
[ERROR] connection to server at "localhost", port 5432 failed
```

**诊断步骤**:
```bash
# 1. 检查容器状态
make ps

# 2. 检查数据库健康
make health

# 3. 进入数据库 Shell
make db-shell
```

**解决方案**:
```bash
# 重启数据库
docker-compose restart db

# 完全重建（谨慎！会删除数据）
docker-compose down -v
docker-compose up -d db
```

#### 问题 3: 相似度匹配失败 (link_method == 'none')

**现象**:
```
Similarity: 0.00%
Method: none
Stored: False
```

**诊断步骤**:
1. 检查队名是否在缩写映射表中
2. 确认时间窗口是否合理（默认 48 小时）
3. 查询 matches 表是否存在相近时间的比赛

**解决方案**:
```python
# 方案 A: 降低相似度阈值
linker_config = LinkerConfig(
    time_window_hours=72,  # 扩大时间窗口
    similarity_threshold=0.65,  # 降低阈值 (默认 0.75)
)

# 方案 B: 添加新的队名映射
# 编辑 src/services/match_linker.py
ABBREVIATION_MAP = {
    "新缩写": "完整队名",
    ...
}
```

### 4.2 日志与取证

#### 日志文件位置

```
logs/
├── odds_sync_YYYYMMDD.log          # 主日志
├── industrial_audit_result.json    # 提取结果
└── last_extraction_failure_*.png   # 失效截图 (V41.232)
```

#### 截图分析 (V41.232)

当提取失败时，系统会自动保存截图：

```bash
# 查看最新截图
ls -lt logs/*.png | head -1

# 截图命名规则
# last_extraction_failure_YYYYMMDD_HHMMSS_attemptN.png
#                                         ↑ 时间    ↑ 重试次数
```

**截图分析检查点**:
- [ ] 页面是否完全加载？
- [ ] 是否出现验证码/登录墙？
- [ ] 目标元素是否在视口中？
- [ ] 是否有 Cookie 同意弹窗遮挡？

### 4.3 健康度检查

```bash
# 运行健康度检查脚本
python scripts/ops/check_sync_health.py

# 输出示例:
# ═══════════════════════════════════════
# V41.235 合龙健康度报告
# ═══════════════════════════════════════
# 📊 总记录数: 1,234
# 📈 平均相似度: 94.5%
# ⚠️  异常场次 (link_method=none): 12
```

---

## 5. 配置参考

### 5.1 AuditorConfig 完整参数

```python
from src.core.scrapers.industrial_auditor import AuditorConfig

config = AuditorConfig(
    # 基础配置
    target_url="https://example.com/match",
    target_patterns=["Opening", "Closing", "Movement"],

    # 网络配置
    headless=True,
    proxy_port=7892,
    navigation_timeout=90000,        # V41.231: 90s 超时
    max_retries=3,                   # V41.231: 最大重试
    wait_after_load=5000,            # V41.231: 加载后等待
    wait_strategy="domcontentloaded", # V41.231: 导航策略

    # 提取配置
    scroll_iterations=5,
    scroll_delay_ms=800,
    network_idle_timeout=30000,

    # 阈值配置
    min_value_threshold=1.01,
    max_value_threshold=50.00,
    enable_degraded_mode=True,

    # V41.235: 输出目录
    output_dir="logs",
)
```

### 5.2 LinkerConfig 完整参数

```python
from src.services.match_linker import LinkerConfig

config = LinkerConfig(
    time_window_hours=48.0,          # 时间窗口（小时）
    similarity_threshold=0.75,        # V41.232: 相似度阈值
    max_candidates=10,                # 最大候选数
    enable_fuzzy_match=True,          # 启用模糊匹配
    enable_abbreviation_expansion=True,  # V41.232: 启用缩写扩展

    # 数据库表配置
    matches_table="matches",
    odds_table="match_odds_intelligence",
)
```

---

## 6. 生产部署建议

### 6.1 环境变量

```bash
# .env 文件
PROXY_PORTS=7892,7893,7894,7895,7896
PROXY_WSL2_HOST=172.25.16.1
DB_HOST=localhost
DB_NAME=football_db
DB_USER=football_user
DB_PASSWORD=your_secure_password
```

### 6.2 定时任务 (Crontab)

```bash
# 每 4 小时采集一次
0 */4 * * * cd /path/to/FootballPrediction && \
    python run_odds_sync.py --url "https://example.com/match" \
    >> logs/cron_odds_sync.log 2>&1

# 每日健康检查
0 8 * * * cd /path/to/FootballPrediction && \
    python scripts/ops/check_sync_health.py
```

### 6.3 监控告警

建议监控指标:
- `entities_extracted` < 1 → 告警（零提取）
- `similarity_score` < 0.75 → 警告（低相似度）
- `link_method` == 'none' → 告警（匹配失败）

---

## 7. 版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| **V41.235** | 2026-01-19 | 配置深度解耦、生产文档化 |
| **V41.234** | 2026-01-19 | 数据合龙测试 (The Great Alignment) |
| **V41.232** | 2026-01-19 | 队名缩写映射、相似度阈值优化 |
| **V41.231** | 2026-01-19 | 网络韧性补丁 (90s 超时 + 3 次重试) |
| **V41.230** | 2026-01-19 | 项目里程碑 - 生产级代码重构 |
| **V41.226** | 2026-01-19 | 信号序列对齐 - 33 位矩阵算法 |

---

## 8. 附录

### 8.1 数据库 Schema

```sql
CREATE TABLE match_odds_intelligence (
    id SERIAL PRIMARY KEY,
    match_id VARCHAR(50) UNIQUE NOT NULL,
    initial_price JSONB,      -- [P1, PX, P2]
    closing_price JSONB,      -- [P1, PX, P2]
    movement_history JSONB,   -- [27 个中间态]
    quality_rating VARCHAR(20),
    deviation_percentage FLOAT,
    similarity_score FLOAT,
    link_method VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_odds_intel_match_id ON match_odds_intelligence(match_id);
CREATE INDEX idx_odds_intel_quality ON match_odds_intelligence(quality_rating);
```

### 8.2 支持与反馈

- **文档更新**: 2026-01-19
- **维护团队**: Football Prediction Engineering
- **问题反馈**: GitHub Issues
- **技术支持**: 查阅 `docs/troubleshooting.md`

---

**本文档遵循 V41.235 工业级交付标准**
