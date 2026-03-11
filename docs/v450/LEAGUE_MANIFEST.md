# LEAGUE MANIFEST V4.50.0-GLOBAL

**版本**: V4.50.0-GLOBAL
**最后验证**: 2026-03-11
**验证方式**: FotMob API 实时核对 (`https://www.fotmob.com/api/leagues?id=xxx`)

---

## 优先级定义

| 级别 | 定义 | 说明 |
|:-----|:-----|:-----|
| **P0** | 核心赛事 | 五大联赛 + 欧冠 + 欧联，必须 100% 数据完整性 |
| **P1** | 重要赛事 | 次级联赛 + 杯赛 + 欧协联 + 巴甲 + 世俱杯 |
| **P2** | 补充赛事 | 国内超级杯，单场制 |

---

## P0 核心赛事 (7 项)

| 赛事名称 | FotMob ID | 国家 | 验证状态 |
|:---------|:----------|:-----|:---------|
| Premier League | 47 | England | ✅ 已验证 |
| La Liga | 87 | Spain | ✅ 已验证 |
| Bundesliga | 54 | Germany | ✅ 已验证 |
| Serie A | 55 | Italy | ✅ 已验证 |
| Ligue 1 | 53 | France | ✅ 已验证 |
| Champions League | 42 | Europe | ✅ 已验证 |
| Europa League | 73 | Europe | ✅ 已验证 |

---

## P1 重要赛事 (11 项)

### 次级联赛

| 赛事名称 | FotMob ID | 国家 | 验证状态 |
|:---------|:----------|:-----|:---------|
| Championship | 48 | England | ✅ 已验证 |
| Brasileirão | 268 | Brazil | ✅ 已验证 |

### 欧战

| 赛事名称 | FotMob ID | 国家 | 验证状态 |
|:---------|:----------|:-----|:---------|
| Conference League | 10216 | Europe | ✅ 已验证 |
| UEFA Super Cup | 74 | Europe | ✅ 已验证 |
| FIFA Club World Cup | 78 | World | ✅ 已验证 |

### 国内杯赛

| 赛事名称 | FotMob ID | 国家 | 验证状态 |
|:---------|:----------|:-----|:---------|
| FA Cup | 132 | England | ✅ 已验证 |
| EFL Cup | 133 | England | ✅ 已验证 |
| Copa del Rey | 138 | Spain | ✅ 已验证 |
| DFB Pokal | 209 | Germany | ✅ 已验证 |
| Coppa Italia | 141 | Italy | ✅ 已验证 |
| Coupe de France | 134 | France | ✅ 已验证 |

---

## P2 补充赛事 (4 项)

| 赛事名称 | FotMob ID | 国家 | 验证状态 |
|:---------|:----------|:-----|:---------|
| Community Shield | 247 | England | ✅ 已验证 |
| Supercopa de España | 139 | Spain | ✅ 已验证 |
| Supercoppa Italiana | 222 | Italy | ✅ 已验证 |
| DFL-Supercup | 8924 | Germany | ✅ 已验证 |

---

## 历史错误 ID 记录

以下 ID 已确认为错误映射，**严禁使用**：

| 错误 ID | 曾被误认为 | 实际对应 | 正确 ID |
|:--------|:-----------|:---------|:--------|
| 56 | FA Cup | Serie B Qualification (意大利) | 132 |
| 57 | EFL Cup | 未知 | 133 |
| 59 | Copa del Rey | 未知 | 138 |
| 61 | DFB Pokal | 未知 | 209 |
| 63 | Coppa Italia | 未知 | 141 |
| 65 | Coupe de France | 未知 | 134 |
| 43 | Europa League | Confederations Cup | 73 |
| 44 | Conference League | 未知 | 10216 |
| 105 | UEFA Super Cup | 不存在 | 74 |
| 136 | Community Shield | 1. Division (塞浦路斯) | 247 |
| 135 | Supercopa de España | Super League 1 (希腊) | 139 |
| 137 | Supercoppa Italiana | Scottish Cup (苏格兰) | 222 |
| 156 | DFL-Supercup | 不存在 | 8924 |
| 1000079 | Club World Cup | 不存在 | 78 |

---

## 验证命令

```bash
# 验证单个 ID
curl -s "https://www.fotmob.com/api/leagues?id=47" | grep -o '"name":"[^"]*"' | head -1

# 批量验证
for id in 47 87 54 55 53 42 73 10216 74 132 133 138 209 141 134 247 139 222 8924 268 78; do
  result=$(curl -s "https://www.fotmob.com/api/leagues?id=$id" | grep -o '"name":"[^"]*"' | head -1 | sed 's/"name":"//;s/"$//')
  echo "ID $id: $result"
done
```

---

## 更新日志

| 日期 | 版本 | 变更内容 |
|:-----|:-----|:---------|
| 2026-03-11 | V4.50.0 | 初始建档，完成 22 项赛事 ID 验证 |

---

**维护者**: Claude Code
**下次验证周期**: 每赛季开始前
