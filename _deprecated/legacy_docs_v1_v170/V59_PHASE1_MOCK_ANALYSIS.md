# V59.0 Phase 1 - API 结构分析（模拟）

## 典型 OddsPortal API 响应结构

### 1. 主要 API 端点

| 端点模式 | 预期内容 | 优先级 |
|---------|---------|--------|
| `/ajax-match-odds/` | 完整赔率数据（包含开盘赔率） | ⭐⭐⭐ |
| `/feed/` | 实时更新流 | ⭐⭐ |
| `/api/` | 通用 API 调用 | ⭐ |

---

### 2. 预期 JSON 结构（基于典型模式）

#### 结构 A: 扁平实体结构

```json
{
  "Entity_P": {
    "opening": {
      "home": 1.95,
      "draw": 3.60,
      "away": 4.20,
      "timestamp": 1713162780
    },
    "current": {
      "home": 2.10,
      "draw": 3.40,
      "away": 3.80
    }
  },
  "Entity_B3": {
    "initial": {
      "h": 1.98,
      "d": 3.55,
      "a": 4.10,
      "time": "2024-04-15T08:13:00Z"
    }
  }
}
```

**字段路径**: `Entity_P.opening.timestamp`

---

#### 结构 B: 嵌套 OddsPortal 格式

```json
{
  "odds": {
    "bookmakers": [
      {
        "id": "Entity_P",
        "name": "Pinnacle",
        "opening": {
          "odds": [1.95, 3.60, 4.20],
          "time": 1713162780
        }
      }
    ]
  }
}
```

**字段路径**: `odds.bookmakers[?(@.id=='Entity_P')].opening.time`

---

#### 结构 C: 时间序列格式

```json
{
  " Entity_P": {
    "history": [
      {
        "timestamp": 1713162780,
        "odds": {"1": 1.95, "X": 3.60, "2": 4.20},
        "is_opening": true
      },
      {
        "timestamp": 1713162840,
        "odds": {"1": 2.00, "X": 3.55, "2": 4.10}
      }
    ]
  }
}
```

**字段路径**: `Entity_P.history[?(@.is_opening==true)].timestamp`

---

### 3. 关键字段名候选

#### 开盘赔率字段

| 模式 | 候选字段名 |
|------|-----------|
| 标准型 | `opening`, `initial`, `first` |
| 简写型 | `init`, `open`, `start` |
| 描述型 | `opening_odds`, `initial_odds`, `first_odds` |

#### 时间戳字段

| 模式 | 候选字段名 |
|------|-----------|
| Unix 时间戳 | `timestamp`, `time`, `unixtime` |
| ISO 格式 | `opening_time`, `created_at`, `published_at` |
| 自定义格式 | `first_seen`, `date`, `datetime` |

#### 主客胜字段

| 类型 | 主胜 | 平局 | 客胜 |
|------|------|------|------|
| 完整 | `home`, `draw`, `away` |
| 简写 | `h`, `d`, `a` |
| 欧式 | `1`, `X`, `2` |

---

### 4. Pinnacle Entity Code 变体

可能的表示形式：
- `Entity_P` (V58.0 标准)
- `pinnacle` (小写)
- `Pinnacle` (完整名称)
- `PN` (简写)

---

### 5. 提取路径优先级

根据 V58.0 的经验，优先检查以下路径：

```python
# 优先级 1: 直接 Entity_P.opening.timestamp
json_data['Entity_P']['opening']['timestamp']

# 优先级 2: Entity_P.initial.time
json_data['Entity_P']['initial']['time']

# 优先级 3: 嵌套搜索
# 搜索包含 'Entity_P' 的键，然后查找 'timestamp' 子字段

# 优先级 4: 正则匹配
# 搜索所有值为整数且范围在 1000000000-9999999999999 的字段
```

---

## 下一步

1. 运行 `debug_api_sniffer.py` 捕获真实 JSON
2. 检查 `logs/api_samples/` 中的样本文件
3. 根据实际结构更新 `odds_api_interceptor.py` 中的字段映射
