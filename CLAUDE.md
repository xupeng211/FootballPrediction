# CLAUDE.md - AI 助手操作指南

> **版本**: V171.2.0
> **适用对象**: Claude Code, GitHub Copilot, 开源贡献者

---

## 快速命令参考

```bash
# === 核心收割 ===
npm run harvest           # 批量收割 (50 场)
npm run harvest:quick     # 快速收割测试
npm run harvest:limit 10  # 限制收割 10 场
npm run scheduler         # 启动无人值守调度器

# === URL 提取 ===
npm run extract-urls      # 提取真实 OddsPortal URL Hash

# === 代码质量 ===
npm run lint              # ESLint 检查
npm run lint:fix          # ESLint 自动修复
npm run format            # Prettier 格式化
npm run lint:python       # Ruff Python 检查
npm run qa                # 全量检查 (lint + python)

# === 测试 ===
npm run test              # 运行所有测试
npm run test:v171         # V171 专项测试
npm run test:python       # Python 测试

# === 数据库 ===
docker-compose up -d db   # 启动数据库
docker-compose logs db    # 查看数据库日志
```

---

## 代码风格规范

### Node.js (ESLint + Prettier)

```javascript
/**
 * 函数说明
 * @param {string} matchId - 比赛唯一标识符
 * @param {Object} options - 配置选项
 * @param {number} options.timeout - 超时时间 (毫秒)
 * @returns {Promise<MatchPrediction>} 预测结果
 * @throws {Error} 当 matchId 为空时抛出错误
 * @example
 * const prediction = await fetchPrediction('EPL_001', { timeout: 30000 });
 */
async function fetchPrediction(matchId, options = {}) {
    // 实现...
}
```

### Python (Ruff + Type Hints)

```python
def fuzzy_match_teams(
    fotmob_home: str,
    fotportal_home: str,
    *,
    min_threshold: float = 0.65,
) -> FuzzyMatchResult | None:
    """模糊匹配 FotMob 和 OddsPortal 的队名。

    使用 RapidFuzz 计算 Levenshtein 距离，判断是否为同一场比赛。

    Args:
        fotmob_home: FotMob 主队名。
        oddsportal_home: OddsPortal 主队名。
        min_threshold: 最低相似度阈值 (0.0-1.0)。

    Returns:
        匹配结果，如果相似度低于阈值则返回 None。

    Raises:
        ValueError: 当任一参数为空字符串时。
    """
    ...
```

---

## 核心逻辑提示

### ⚠️ 队名匹配必须调用 BridgeRadarEngine

当需要匹配 FotMob 队名到 OddsPortal URL 时，**必须**使用 C++ 桥接引擎：

```python
# ✅ 正确方式
from src.utils.cpp_bridge_radar import BridgeRadarEngine

bridge = BridgeRadarEngine()
result = bridge.dynamic_bridge(
    fotmob_home="Man Utd",
    fotmob_away="Chelsea",
    league_name="Premier League"
)

if result.success:
    url = result.url  # https://www.oddsportal.com/.../manchester-united-chelsea-ABC123/
```

```javascript
// ❌ 错误方式 - 不要手动拼接 URL
const url = `https://oddsportal.com/${home}-${away}/`;  // 危险！
```

### 🔗 数据流顺序

```
L1 Discovery → C++ Bridge → L2/L3 Harvest → V171 Prediction
    │              │              │               │
    ▼              ▼              ▼               ▼
 pending       URL Hash      Odds + xG      Predictions
```

### 🛡️ NetworkShield 代理池

系统使用 22 节点代理池，自动熔断：

```javascript
// 代理配置在 config/active_registry.json
// 端口范围: 7891-7912
// 熔断阈值: 2 次连续失败
// 冷却时间: 15 分钟
```

---

## 环境变量

```bash
# 必须配置
DB_PASSWORD=your_secure_password_here

# 可选配置
LOG_LEVEL=info
ENABLE_PROXY_ROTATION=true
PROXY_HOST=172.25.16.1
```

---

## 常见问题处理

### Q: 代理熔断怎么办？
```bash
# 检查代理状态
curl -x http://172.25.16.1:7891 https://httpbin.org/ip

# 重置熔断器
docker-compose restart dev
```

### Q: 数据库连接超时？
```bash
# 检查数据库状态
docker-compose ps db

# 重启数据库
docker-compose restart db
```

### Q: URL Hash 提取失败？
```bash
# 手动提取
npm run extract-urls -- --limit 50 --update-db
```

---

## 文件结构

```
FootballPrediction/
├── config/
│   ├── database.js      # 统一配置管理
│   └── logger.js        # 结构化日志
├── scripts/ops/
│   ├── v171_scheduler.js     # 调度器
│   ├── v171_mass_harvest.js  # 批量收割
│   └── v171_real_url_extractor.js  # URL 提取
├── src/
│   ├── infrastructure/engines/   # 核心引擎
│   ├── ml/inference/            # ML 模型
│   └── utils/cpp_bridge_radar.py  # C++ 桥接
└── tests/
    └── test_v171_*.py           # V171 测试
```

---

## Git 提交规范

```
feat(V171): 新功能
fix(V171): 修复 Bug
chore(V171-Standard): 基建/文档
test(V171): 测试
```

---

*最后更新: 2026-02-25*
