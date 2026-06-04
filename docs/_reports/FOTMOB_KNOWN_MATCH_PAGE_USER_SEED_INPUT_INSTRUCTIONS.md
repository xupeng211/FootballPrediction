<!-- markdownlint-disable MD013 -->

# FotMob 用户已知比赛页面种子输入指南

- lifecycle: permanent
- phase: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-KNOWN-MATCH-PAGE-PARSE-NO-WRITE-WITH-USER-SEEDS

## 概述

本指南说明如何向系统提供 FotMob 公开比赛详情页链接作为 known_match_page 种子。

## 当前状态

您已经提供了 12 条公开 FotMob 比赛详情页链接，这些链接已经足够作为第一批种子进行离线 URL 解析验证。

系统已验证可以从这些 URL 中解析出：

- match_slug（比赛 slug）
- route_code（FotMob 路由代码）
- fotmob_match_id（FotMob 比赛 ID）

## 后续扩展建议

如果您希望继续扩展种子覆盖，建议按以下优先级提供更多链接：

### Manchester United 当前目标相关

- 1-3 条 Manchester United 新赛季 / 当前目标相关链接
- 示例格式：`https://www.fotmob.com/matches/<slug>/<route_code>#<match_id>`

### England 当前目标相关

- 1-3 条 England 当前目标相关链接

### Kashima Antlers 链接

- 1-2 条 Kashima Antlers 链接

### Leeds United 链接

- 1-2 条 Leeds United 链接

## Local Seed 文件格式

本地种子文件路径：

```text
docs/_local/fotmob_known_match_page_seeds.local.json
```

该文件不需要提交到 Git。`docs/_local/` 目录已加入 `.gitignore`。

文件格式与 `docs/_examples/fotmob_known_match_page_user_seeds.example.json` 相同：

```json
{
  "schema_version": "fotmob_known_match_page_user_seeds_v1",
  "source_type": "user_supplied_known_match_page",
  "seed_records": [
    {
      "seed_id": "local-seed-01",
      "source_url": "https://www.fotmob.com/matches/<slug>/<route_code>#<match_id>",
      "team_hint": "<队名>",
      "opponent_hint": "<对手队名>",
      "expected_match_slug": "<slug>",
      "expected_route_code": "<route_code>",
      "expected_fotmob_match_id": "<match_id>",
      "target_relevance": "current_target_team_related"
    }
  ]
}
```

## 重要说明

### 这些种子不会直接入库

- 本阶段只做离线 URL 字符串解析
- 不会访问 FotMob 网站
- 不会触发 raw JSON write
- 不会写入数据库

### 下一步只会做 controlled JSON probe no-write

- 即使解析出 match_id，也不会直接入库
- 必须先通过 controlled JSON probe no-write 验证
- L2 raw harvesting 仍然 blocked

### 安全要求

- **不要**提供账号、cookie、登录信息
- **不要**提供任何非公开数据
- **只提供公开 FotMob 页面链接即可**
- 链接格式：`https://www.fotmob.com/matches/<slug>/<route_code>#<match_id>`
- 支持带 locale 前缀的链接：`https://www.fotmob.com/zh-Hans/matches/<slug>/<route_code>#<match_id>`

## URL 格式要求

有效的 FotMob 比赛详情页链接必须包含：

1. 域名：`www.fotmob.com`
2. 路径：`/matches/<slug>/<route_code>` 或 `/<locale>/matches/<slug>/<route_code>`
3. Fragment：`#<match_id>`（纯数字，5 位以上）

示例：

- 标准英文：`https://www.fotmob.com/matches/aston-villa-vs-manchester-united/3h9f6s#4506597`
- 中文 locale：`https://www.fotmob.com/zh-Hans/matches/england-vs-croatia/2viayw#4667825`
