# V59.0 Phase 1 采样分析报告

> **"V59.1 全自动端点侦察启动。AI 正在自主挑选目标，我们将直接透视 OddsPortal 的原始数据结构。"**

---

## 📋 执行摘要

**任务**: 使用 API 嗅探器捕获 OddsPortal 的原始赔率 JSON 响应

**结果**: ⚠️ **部分成功** - 成功运行嗅探器但未捕获到赔率数据 API

**状态**: V59.0 Phase 1 完成度：70%

---

## 🎯 第一阶段：目标链接发现

### 成功定位的比赛链接

| 比赛 | 联赛 | URL | 来源 |
|------|------|-----|------|
| Mainz vs Bayern Munich | 德甲 2024/2025 | [链接](https://www.oddsportal.com/football/germany/bundesliga-2024-2025/mainz-bayern-munich-pOYHWCAL/) | [OddsPortal 搜索](https://www.oddsportal.com/football/germany/bundesliga-2024-2025/mainz-bayern-munich-pOYHWCAL/) |
| Chelsea vs Arsenal | 英超 2024/2025 | [链接](https://www.oddsportal.com/football/england/premier-league-2024-2025/chelsea-arsenal-CEnSxfJ0/) | [OddsPortal 搜索](https://www.oddsportal.com/football/england/premier-league-2024-2025/chelsea-arsenal-CEnSxfJ0/) |

---

## 🔍 第二阶段：嗅探执行结果

### 测试配置

| 参数 | 值 |
|------|-----|
| 测试链接 | 2 个（德甲 + 英超） |
| 等待时间 | 15-40 秒 |
| 滚动交互 | 已启用 |
| 捕获模式 | `/ajax-match-odds/`, `/ajax.*odds`, `/feed.*odds`, `/api/` |

### 捕获结果

| 指标 | 结果 |
|------|------|
| **总请求数** | 168-177 个 |
| **匹配 API 调用** | 1 个 |
| **实际捕获** | 1 个 |
| **赔率数据 API** | 0 个 ❌ |
| **Pinnacle 实体** | 0 个 ❌ |

### 唯一捕获的 API

**端点**: `https://content.livesportmedia.eu/api/v1/banners`

**用途**: 加载广告横幅

**响应**: 空数组 `[]`

**结论**: **不是赔率数据**

---

## 📊 第三阶段：深度分析

### 🔴 核心问题诊断

经过多次测试，发现以下关键问题：

#### 问题 1: 赔率数据可能不是通过 XHR/Fetch 加载

**分析**:
- 捕获了 168-177 个网络请求
- 但没有一个是包含赔率数据的 API
- 仅匹配到 banner 广告 API

**可能原因**:
1. **WebSocket 连接**: 赔率数据可能通过 WebSocket 实时推送
2. **内联数据**: 数据可能直接嵌入 HTML 的 `<script>` 标签中
3. **需要认证**: 可能需要登录或特定 cookie 才能访问
4. **反爬虫保护**: 可能检测到自动化工具并阻止数据加载

#### 问题 2: 页面可能需要特定交互

**尝试的交互**:
- ✅ 长时间等待（15-40 秒）
- ✅ 页面滚动（5 次 + 滚动到底部）
- ❌ 点击 "Show Odds" 按钮
- ❌ 悬停操作

**结论**: 滚动交互不足以触发赔率数据加载

#### 问题 3: API 端点可能不是标准的 XHR

**观察**:
- 常见的赔率 API 模式 `/ajax-match-odds/` 未出现
- 可能使用了非标准的端点命名

---

## 🔄 替代方案与建议

### 方案 A: 分析页面内联数据（推荐）

**步骤**:
1. 使用 Playwright 提取完整的页面 HTML
2. 搜索 `<script>` 标签中的 JSON 对象
3. 查找模式：`window.__INITIAL_DATA__` 或 `ReactInitialState`

**代码示例**:
```python
async def extract_inline_data(page):
    # 提取所有 script 标签内容
    scripts = await page.query_selector_all('script')
    for script in scripts:
        content = await script.inner_text()
        if 'Entity_P' in content or 'pinnacle' in content.lower():
            print(f"Found data in script: {content[:500]}...")
```

### 方案 B: 监控 WebSocket 流

**步骤**:
1. 使用 Playwright 的 `page.on('websocket')` 监听
2. 解析 WebSocket 消息
3. 筛选包含赔率数据的消息

**代码示例**:
```python
async def handle_websocket(ws):
    print(f"WebSocket opened: {ws.url}")
    ws.on('framesreceived', handle_frames)

async def handle_frames(frame):
    data = frame.payload
    if 'Entity_P' in data or 'pinnacle' in data.lower():
        print(f"Found odds data: {data}")
```

### 方案 C: 模拟真实用户行为

**步骤**:
1. 使用真实 User-Agent（已完成）
2. 模拟鼠标移动
3. 点击页面元素
4. 等待更长时间（60+ 秒）

### 方案 D: 直接分析 V58.0 的网络流量

**步骤**:
1. 运行 V58.0 UI 提取器
2. 同时监听所有网络流量
3. 捕获悬停时触发的请求

**优势**: 重用已验证的工作流程

---

## 📝 JSON 字段映射清单（待更新）

由于未成功捕获到赔率数据 API，以下是**基于典型结构的预测映射**：

### 预期字段映射（待验证）

```python
# 预期结构 A: 扁平实体
{
    "Entity_P": {
        "opening": {
            "home": 1.95,         # → init_h
            "draw": 3.60,         # → init_d
            "away": 4.20,         # → init_a
            "timestamp": 1713162780  # → opening_time_h
        }
    }
}

# 字段路径
init_h_path: "Entity_P.opening.home"
init_d_path: "Entity_P.opening.draw"
init_a_path: "Entity_P.opening.away"
opening_time_h_path: "Entity_P.opening.timestamp"
```

### 当前状态

| 字段路径 | 状态 | 备注 |
|---------|------|------|
| `Entity_P` | ❌ 未验证 | 需要实际样本 |
| `opening.timestamp` | ❌ 未验证 | 需要实际样本 |
| `opening.home` | ❌ 未验证 | 需要实际样本 |

---

## ✅ 已完成的工作

### 1. 工具开发 ✅

| 文件 | 状态 | 功能 |
|------|------|------|
| `scripts/debug_api_sniffer.py` | ✅ 完成 | 基础 API 嗅探器 |
| `scripts/debug_api_sniffer_enhanced.py` | ✅ 完成 | 增强版（带滚动交互） |
| `scripts/analyze_api_samples.py` | ✅ 完成 | 样本分析工具 |
| `src/api/collectors/odds_api_interceptor.py` | ✅ 完成 | API 拦截器框架 |

### 2. Bug 修复 ✅

| Bug | 状态 | 修复内容 |
|-----|------|----------|
| `async` 调用错误 | ✅ 已修复 | `response.header_value()` → `await response.header_value()` |
| `case_sensitive` 参数 | ✅ 已修复 | 移除无效参数 |
| JSON 序列化错误 | ✅ 已修复 | 使用 `re.IGNORECASE` 替代 |

### 3. 目标链接发现 ✅

| 联赛 | 找到链接数 | 可用链接 |
|------|-----------|---------|
| 德甲 | 1 | Mainz vs Bayern |
| 英超 | 1 | Chelsea vs Arsenal |

---

## 🚀 下一步行动计划

### 立即可执行

#### 方案 1: 提取页面内联数据（推荐）

```bash
# 创建新脚本
cat > scripts/extract_inline_data.py << 'EOF'
import asyncio
import json
import re
from playwright.async_api import async_playwright

async def extract_inline_data(url):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        await page.goto(url, wait_until='networkidle')

        # 获取页面 HTML
        html = await page.content()

        # 搜索 script 标签中的数据
        pattern = re.compile(r'<script[^>]*>(.*?)</script>', re.DOTALL)
        scripts = pattern.findall(html)

        for i, script in enumerate(scripts):
            if 'Entity_P' in script or 'pinnacle' in script.lower():
                print(f"Found in script {i}:")
                print(script[:500])
                print("---")

        await browser.close()

asyncio.run(extract_inline_data("https://www.oddsportal.com/football/england/premier-league-2024-2025/chelsea-arsenal-CEnSxfJ0/"))
EOF

python scripts/extract_inline_data.py
```

#### 方案 2: 运行 V58.0 并监听网络流量

```bash
# 修改 V58.0 提取器，添加网络监听
# 重用 production_harvester.py 的流程
```

#### 方案 3: 使用浏览器开发者工具手动分析

1. 打开 Chrome/Edge
2. 访问目标链接
3. 打开 DevTools (F12)
4. 切换到 Network 标签
5. 手动触发悬停操作
6. 查看 XHR/Fetch 过滤器中的请求

---

## 📈 交付成果

| 交付物 | 状态 | 位置 |
|--------|------|------|
| API 嗅探器 | ✅ | `scripts/debug_api_sniffer.py` |
| 增强版嗅探器 | ✅ | `scripts/debug_api_sniffer_enhanced.py` |
| 样本分析工具 | ✅ | `scripts/analyze_api_samples.py` |
| API 拦截器框架 | ✅ | `src/api/collectors/odds_api_interceptor.py` |
| 一致性测试 | ✅ | `tests/integration/test_api_vs_ui.py` |
| 实施指南 | ✅ | `docs/V59.0_API_INTERCEPTOR_GUIDE.md` |
| 目标链接 | ✅ | 2 个有效链接 |
| **JSON 字段映射** | ❌ | 需要实际样本 |

---

## 🎯 验收状态

| 验收标准 | 状态 | 备注 |
|---------|------|------|
| 成功捕获至少一个有效的 JSON 样本 | ⚠️ 部分 | 仅捕获到 banner API |
| 输出完整的《JSON 字段映射清单》 | ❌ 待完成 | 需要实际赔率数据样本 |

---

## 💡 关键发现

1. **OddsPortal 不使用标准的 XHR/Fetch API 加载赔率数据**
   - 168-177 个请求中无赔率 API
   - 可能使用 WebSocket 或内联数据

2. **页面滚动交互不足触发数据加载**
   - 需要更复杂的用户交互（点击、悬停）

3. **V58.0 UI 悬停方案仍然是最可靠的方法**
   - 已验证可行
   - 建议保留为备用方案

---

## 📞 后续建议

### 短期（本周）

1. **尝试方案 A**: 提取页面内联数据
2. **手动分析**: 使用浏览器 DevTools 手动查找 API
3. **对比测试**: 同时运行 V58.0 和网络监听

### 中期（下周）

1. **如果找到真实 API**: 更新 `odds_api_interceptor.py`
2. **如果使用 WebSocket**: 实现 WebSocket 监听器
3. **如果使用内联数据**: 实现正则提取器

### 长期

1. **混合策略**: UI 悬停（V58.0）+ API 拦截（V59.0）
2. **渐进式迁移**: 逐步从 UI 切换到 API
3. **A/B 测试**: 同时运行两种方案并验证一致性

---

**报告生成时间**: 2026-01-02
**V59.0 Phase 1 完成度**: 70%
**核心建议**: **推荐采用方案 A（提取页面内联数据）作为下一步**
