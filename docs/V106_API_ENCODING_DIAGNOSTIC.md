# V106 API 响应编码格式诊断报告

## 执行版本
- V106.004-V106.015
- 日期: 2026-01-26

## 测试 URL
```
https://www.oddsportal.com/football/england/premier-league/brighton-everton-vPKFVEM6/
```

## API 端点
```
https://www.oddsportal.com/match-event/1-1-vPKFVEM6-1-2-d701c6fd183b732f2bbc1a71...
```

---

## 编码流程分析

### 第一层：Base64 (33384 字符)
```
原始响应: d3VYdCtFNDBTc3VNMGVZUmtnVzkyYjgxMmd1dElXZFFZNTUvdXVqcVlPUFk...
```

**响应头**:
- `Content-Type: application/json`
- `Content-Encoding: gzip`

**重要发现**: 浏览器/Playwright 已自动解压 gzip，Base64 是解压后的结果。

### 第二层：Base64 → Base64 文本 (25037 字节)
```
第一次解码: wuXt+E40SsuM0eYRkgW92b812gutIWdQY55/uujqYOPY7Idy7f...
```

**验证**: 字符符合 `/^[A-Za-z0-9+/=]+$/` 模式（除1个字符外）

### 第三层：Base64 → 二进制数据 (18752 字节)
```
第二次解码: [二进制数据，magic bytes: c2e5edf8]
```

**Magic Bytes 分析**:
```
c2e5edf8
- 0xc2 = 194 (Latin-1 Â)
- 0xe5 = 229 (Latin-1 å)
- 0xed = 237 (Latin-1 í)
- 0xf8 = 248 (Latin-1 ø)
```

**与标准格式对比**:
| 格式 | Magic Bytes | 匹配 |
|------|-------------|------|
| Raw Deflate | 78 da | ❌ |
| Zlib | 78 9c | ❌ |
| Gzip | 1f 8b | ❌ |
| ZIP | 50 4b | ❌ |

---

## 解码尝试

### 1. 标准 Zlib 解压
```javascript
zlib.inflateRawSync(buf2)  // "invalid distance too far back"
zlib.inflateSync(buf2)      // "incorrect header check"
zlib.gunzipSync(buf2)       // "incorrect header check"
```

### 2. JXG.decompress
```javascript
// JXG library from https://www.oddsportal.com/js/lscompressor.min.js
new JXG.Util.Unzip(array).unzip()  // 返回 [] (空数组)
```

### 3. URL 解码
```javascript
// 发现 61 个 '%' 符号，但都是无效转义序列
// 例如: %B7, %ӡ, %c... (hex 不是有效的 [0-9A-Fa-f]{2})
decodeURIComponent(asUtf8)  // "URI malformed"
```

---

## 数据特征

### 熵值分析
```
唯一字节值: 256 / 256 (100%)
熵值比例: 100%
结论: 高度压缩或加密的数据
```

### 字符分析
```
可打印 ASCII: 32.6%
控制字符: 15.4%
二进制数据: 52.0%
```

### 模式检测
```
包含 {  或 }  ✓
包含 [  或 ]  ✓
包含 "       ✓
包含 %       ✓ (但不是 URL 编码)
```

---

## 可能的解释

### 1. 加密数据 ⭐ (最可能)
- Magic bytes `c2e5edf8` 可能是加密盐/IV
- 100% 熵值符合加密特征
- OddsPortal 可能使用私有加密算法

### 2. 自定义压缩格式
- 非 Zlib/Gzip/Deflate
- 需要 JXG 的自定义解压器

### 3. 数据损坏
- Base64 解码过程中丢失了某些字节
- 25037 → 25036 (清理掉1个字符)

### 4. API 已更新
- JXG 库版本可能过时
- OddsPortal 更新了 API 但未更新文档

---

## 下一步建议

### 方案 A: 浏览器内拦截解码后的数据 ⭐ (推荐)
```javascript
// 在页面加载后，从 JavaScript 变量中读取已解码的数据
// 而不是拦截原始网络响应
await page.evaluate(() => {
    // 查找存储 match data 的全局变量
    return window.__INITIAL_STATE__ || window.matchData;
});
```

### 方案 B: 使用 JXG 库的完整版本
```javascript
// 可能需要加载额外的解密/解压库
await page.addScriptTag({ url: 'https://www.oddsportal.com/js/lscompressor.min.js' });
// 然后在浏览器上下文中使用 JXG.decompress
```

### 方案 C: 分析页面主应用包
```javascript
// 从 https://www.oddsportal.com/build/assets/app-Db9gAttz.js
// 查找实际的解码逻辑
```

### 方案 D: 回归 Hover + Modal 方案
- 如果 API 解密无法突破
- 回到原始的 OddsHarvester 方案
- 牺牲一些效率换取稳定性

---

## 技术债务

### 已完成
- ✅ V106.002/V106.003: 发现 match-event API
- ✅ V106.005-V106.015: 完整编码格式分析
- ✅ V106.014: JXG 库调试

### 待解决
- ⏸️ API 响应解码方案
- ⏸️ 数据提取引擎实现

---

## 附录

### 测试文件
```
scripts/tests/v106_002_dom_diagnostic.js
scripts/tests/v106_003_api_interception.js
scripts/tests/v106_005_format_diagnostic.js
scripts/tests/v106_006_raw_body_diagnostic.js
scripts/tests/v106_008_route_intercept.js
scripts/tests/v106_009_browser_context.js
scripts/tests/v106_010_js_analysis.js
scripts/tests/v106_011_correct_decode.js
scripts/tests/v106_012_decode_analysis.js
scripts/tests/v106_013_browser_decode.js
scripts/tests/v106_014_jxg_debug.js
scripts/tests/v106_015_manual_decode.js
```

### 捕获数据
```
logs/v106_diagnostic/
├── match_event_response_*.txt      # V106.005 捕获
├── match_event_raw_*.bin           # V106.006 捕获
└── route_raw_*.bin                 # V106.008 捕获
```

### JXG 库源码
```
https://www.oddsportal.com/js/lscompressor.min.js?v=260126090850
```

---

**结论**: OddsPortal 的 match-event API 使用了**自定义编码/加密**方案，需要进一步分析或在浏览器上下文中获取已解码的数据。
