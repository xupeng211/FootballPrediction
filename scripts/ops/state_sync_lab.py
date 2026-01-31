#!/usr/bin/env python3
"""
V41.206 "Visual State Synchronization" - 视觉锚点水合引擎
============================================================

## 核心能力 - 视觉驱动型 SPA 状态水合

1. **Phase A: Visual Anchor Localization (视觉锚点定位)**
   - 从 ghost_config.json 读取 anchors 数组（文本标签）
   - 使用 page.get_by_text() 精确定位屏幕上的标签
   - 计算相邻数据单元的精确中心坐标

2. **Phase B: Deep Interaction Simulation (深度交互模拟)**
   - 对每个锚定坐标执行高精度鼠标移动序列
   - 长按触发：mouse.down -> 1200ms sleep -> mouse.up
   - 立即发送 Escape 键维持环境稳定性

3. **Phase C: State Snapshotting (状态快照)**
   - 非破坏性审计 __vue_app__
   - 捕获包含 "log"/"history" 数组的目标实体状态

## 技术架构

```
┌─────────────────────────────────────────────────────────────┐
│  V41.206 Visual State Synchronization                        │
│  ┌─────────────────────────────────────────────────────────┐│
│  │  Phase A: Visual Anchor Localization                    ││
│  │  - 读取 ghost_config.json anchors                       ││
│  │  - page.get_by_text() 定位标签                          ││
│  │  - 计算数据单元中心坐标                                  ││
│  └─────────────────────────────────────────────────────────┘│
│                              ↓                               │
│  ┌─────────────────────────────────────────────────────────┐│
│  │  Phase B: Deep Interaction Simulation                   ││
│  │  - 高精度 mouse.move 序列                                ││
│  │  - Long Press (1200ms)                                   ││
│  │  - Escape 键稳定                                         ││
│  └─────────────────────────────────────────────────────────┘│
│                              ↓                               │
│  ┌─────────────────────────────────────────────────────────┐│
│  │  Phase C: State Snapshotting                            ││
│  │  - 审计 __vue_app__                                      ││
│  │  - 捕获 log/history 数组                                 ││
│  │  - 写入 state_debug_output.json                          ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

## 使用方式

# 基础用法：从 ghost_config.json 读取
python scripts/ops/v41_195_spa_state_inspector.py

# 指定 URL
python scripts/ops/v41_195_spa_state_inspector.py --url "TARGET_URL"

# 调试模式：显示浏览器
python scripts/ops/v41_195_spa_state_inspector.py --no-headless

## 输出规格

- **数据流向**: logs/state_debug_output.json
- **终端输出**: 仅 "Entity [X] Hydration Status: SUCCESS/FAIL"
- **脱敏分析**: 严禁打印具体业务数据

Author: V41.206 Observability Engineering
Date: 2026-01-19
Version: V41.206 Production
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, ClassVar

from playwright.async_api import async_playwright, Page, Locator

# 项目路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.config_unified import get_config

# 配置日志
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(log_dir / "v41_195_spa_state_inspector.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("V41.206.VisualHydrationEngine")


# =============================================================================
# JavaScript 代码库（注入到浏览器） - V41.206 State Snapshotting
# =============================================================================

JS_PHASE3_STATE_SNAPSHOT = """
(targetPatterns) => {
    const results = {
        phase: "State Snapshotting",
        captured_entities: {},
        vue_version: null,
        metadata: {}
    };

    const visited = new WeakSet();

    // V41.206: 深拷贝函数，限制递归深度
    function deepClone(obj, maxDepth = 10, currentDepth = 0, path = "root") {
        if (currentDepth >= maxDepth) {
            return { _type: "max_depth_reached", path: path };
        }

        if (obj === null || obj === undefined) {
            return obj;
        }

        if (typeof obj !== 'object') {
            return obj;
        }

        // 处理循环引用
        if (visited.has(obj)) {
            return { _type: "circular_reference", path: path };
        }
        visited.add(obj);

        // 处理数组
        if (Array.isArray(obj)) {
            const cloned = [];
            for (let i = 0; i < Math.min(obj.length, 100); i++) {
                cloned.push(deepClone(obj[i], maxDepth, currentDepth + 1, `${path}[${i}]`));
            }
            if (obj.length > 100) {
                cloned.push({ _type: "array_truncated", original_length: obj.length });
            }
            return cloned;
        }

        // 处理日期
        if (obj instanceof Date) {
            return obj.toISOString();
        }

        // 处理普通对象
        const cloned = {};
        for (const key of Object.keys(obj)) {
            try {
                cloned[key] = deepClone(obj[key], maxDepth, currentDepth + 1, `${path}.${key}`);
            } catch (e) {
                cloned[key] = { _type: "error", message: e.message };
            }
        }

        return cloned;
    }

    // V41.206: 扫描包含目标模式的数组
    function scanForPatternArrays(obj, path = "root", depth = 0) {
        if (depth > 12 || !obj || typeof obj !== 'object') {
            return;
        }

        // 检查当前对象的数组属性
        for (const key of Object.keys(obj)) {
            try {
                const value = obj[key];

                // 检查是否为目标数组类型
                if (Array.isArray(value) && value.length > 0) {
                    for (const pattern of targetPatterns) {
                        if (key.toLowerCase().includes(pattern.toLowerCase())) {
                            // 捕获包含目标数组的对象
                            const captureKey = `${path}_${key}_${value.length}`;
                            results.captured_entities[captureKey] = {
                                capture_path: path,
                                array_key: key,
                                array_length: value.length,
                                pattern_matched: pattern,
                                data: deepClone(value)
                            };
                            break;
                        }
                    }
                }

                // 递归扫描
                if (typeof value === 'object' && value !== null) {
                    scanForPatternArrays(value, `${path}.${key}`, depth + 1);
                }
            } catch (e) {
                // 忽略访问错误
            }
        }
    }

    // V41.206: 从多个入口点开始扫描
    const entryPoints = [
        {
            name: "Vue3_App_Instance",
            accessor: () => document.querySelector('#app')?.__vue_app__
        },
        {
            name: "Vue3_Pinia_State",
            accessor: () => document.querySelector('#app')?.__vue_app__?.config?.globalProperties?.$pinia?.state?.value
        },
        {
            name: "Vue2_Root_Instance",
            accessor: () => document.querySelector('#app')?.__vue__
        },
        {
            name: "Vue2_Vuex_Store",
            accessor: () => document.querySelector('#app')?.__vue__?.$store?.state
        },
        {
            name: "Window_Initial_State",
            accessor: () => window.__INITIAL_STATE__
        },
        {
            name: "Window_Store",
            accessor: () => window.__store__
        },
        {
            name: "Window_PageVar",
            accessor: () => window.pageVar
        },
        {
            name: "Window_OddsPortal",
            accessor: () => window.__oddsportal_api_data__
        }
    ];

    // 检测 Vue 版本
    if (document.querySelector('#app')?.__vue_app__) {
        results.vue_version = "3.x";
    } else if (document.querySelector('#app')?.__vue__) {
        results.vue_version = "2.x";
    } else {
        results.vue_version = "unknown";
    }

    // 执行扫描
    const entryPointsFound = [];
    for (const entry of entryPoints) {
        try {
            const obj = entry.accessor();
            if (obj) {
                scanForPatternArrays(obj, entry.name);
                entryPointsFound.push(entry.name);
            }
        } catch (e) {
            // 忽略访问错误
        }
    }

    // 组装元数据
    results.metadata = {
        target_patterns: targetPatterns,
        captured_count: Object.keys(results.captured_entities).length,
        vue_version: results.vue_version,
        entry_points_found: entryPointsFound
    };

    return results;
}
"""


# =============================================================================
# Python 主程序 - V41.206 Visual State Synchronization
# =============================================================================

class V41_206_VisualHydrationEngine:
    """V41.206 视觉锚点水合引擎 - 工业级实现"""

    DEFAULT_CONFIG_PATH: ClassVar[Path] = Path("logs/ghost_config.json")
    DEFAULT_OUTPUT_PATH: ClassVar[Path] = Path("logs/state_debug_output.json")

    def __init__(
        self,
        headless: bool = True,
        config_path: Path | None = None,
        target_url: str | None = None,
        output_path: Path | None = None,
        proxy_port: int = 7892
    ):
        self.headless = headless
        self.config_path = config_path or self.DEFAULT_CONFIG_PATH
        self.output_path = output_path or self.DEFAULT_OUTPUT_PATH
        self.proxy_port = proxy_port
        self.config = get_config()

        self.target_url = target_url

        self.browser = None
        self.context = None
        self.page = None
        self.playwright = None

        # 三阶段执行结果
        self.phase_a_result = None
        self.phase_b_result = None
        self.phase_c_result = None

        # 加载配置
        self.ghost_config = self._load_ghost_config()

    def _load_ghost_config(self) -> dict[str, Any]:
        """从 ghost_config.json 加载配置"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                if self.target_url is None:
                    self.target_url = config.get("target_url")
                return config
        except FileNotFoundError:
            logger.error(f"❌ 配置文件未找到: {self.config_path}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"❌ 配置文件解析失败: {e}")
            raise

    async def init_browser(self):
        """初始化浏览器"""
        proxy = {"server": f"http://{self.config.proxy.wsl2_bridge_host}:{self.proxy_port}"}

        self.playwright = await async_playwright().start()

        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            proxy=proxy,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
            ]
        )

        self.context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='en-US',
            timezone_id='Europe/London'
        )

        self.page = await self.context.new_page()

        logger.info("✅ 浏览器初始化完成")

    async def _phase_a_visual_anchor_localization(self) -> dict[str, Any]:
        """Phase A: 视觉锚点定位 - 使用 get_by_text() 定位标签并计算坐标"""
        logger.info("🔍 Phase A: Visual Anchor Localization (视觉锚点定位)...")

        anchors = self.ghost_config.get("anchors", [])
        visual_patterns = self.ghost_config.get("visual_patterns", {})

        result = {
            "phase": "Visual Anchor Localization",
            "anchors_found": [],
            "anchors_missing": [],
            "coordinates": [],
            "total_found": 0
        }

        for anchor_text in anchors:
            try:
                # 使用 page.get_by_text() 精确定位
                locator = self.page.get_by_text(anchor_text, exact=True)

                # 检查元素是否存在
                count = await locator.count()
                if count == 0:
                    result["anchors_missing"].append(anchor_text)
                    logger.debug(f"    ⚠️  未找到锚点: {anchor_text}")
                    continue

                # 获取第一个匹配元素
                element = locator.first
                box = await element.bounding_box()

                if box is None:
                    result["anchors_missing"].append(anchor_text)
                    continue

                # 计算中心坐标
                center_x = box['x'] + box['width'] / 2
                center_y = box['y'] + box['height'] / 2

                # 查找相邻数据单元（右侧或下方）
                sibling_coords = await self._find_sibling_data_cells(element, box, visual_patterns)

                coord_data = {
                    "anchor": anchor_text,
                    "anchor_center": {"x": center_x, "y": center_y},
                    "sibling_cells": sibling_coords
                }

                result["anchors_found"].append(anchor_text)
                result["coordinates"].append(coord_data)
                result["total_found"] += 1

            except Exception as e:
                result["anchors_missing"].append(anchor_text)
                logger.debug(f"    ⚠️  锚点异常: {anchor_text} - {e}")

        logger.info(f"  找到锚点: {result['total_found']}/{len(anchors)}")
        return result

    async def _find_sibling_data_cells(
        self,
        element: Locator,
        box: dict,
        patterns: dict
    ) -> list[dict]:
        """查找相邻的数据单元"""
        sibling_cells = []

        try:
            # 尝试查找右侧兄弟元素
            max_distance = patterns.get("max_distance_pixels", 300)

            # 在右侧搜索可能的交互目标
            search_regions = [
                {"x_offset": box['width'] + 10, "y_offset": 0, "direction": "right"},
                {"x_offset": 0, "y_offset": box['height'] + 10, "direction": "down"},
                {"x_offset": -50, "y_offset": 0, "direction": "left"}
            ]

            for region in search_regions:
                target_x = box['x'] + region["x_offset"]
                target_y = box['y'] + region["y_offset"]

                # 确保坐标在视口内
                if 0 <= target_x <= 1920 and 0 <= target_y <= 1080:
                    sibling_cells.append({
                        "x": target_x,
                        "y": target_y,
                        "direction": region["direction"],
                        "distance": abs(region["x_offset"]) + abs(region["y_offset"])
                    })

            # 按距离排序
            sibling_cells.sort(key=lambda x: x["distance"])

            # 只保留最近的 3 个
            return sibling_cells[:3]

        except Exception:
            return []

    async def _phase_b_deep_interaction(self, coords: list[dict]) -> dict[str, Any]:
        """Phase B: 深度交互模拟 - 长按触发 + Escape 稳定"""
        logger.info("🔍 Phase B: Deep Interaction Simulation (深度交互模拟)...")

        interaction = self.ghost_config.get("interaction", {})
        long_press_duration = interaction.get("long_press_duration_ms", 1200)
        hover_duration = interaction.get("hover_duration_ms", 300)
        post_press_delay = interaction.get("post_press_delay_ms", 200)
        escape_after = interaction.get("escape_after", True)

        result = {
            "phase": "Deep Interaction Simulation",
            "interactions_performed": [],
            "interactions_failed": [],
            "total_success": 0,
            "total_failed": 0
        }

        for coord_data in coords:
            anchor = coord_data["anchor"]
            anchor_center = coord_data["anchor_center"]
            sibling_cells = coord_data["sibling_cells"]

            # 优先使用锚点中心，如果没有兄弟单元
            targets = sibling_cells if sibling_cells else [
                {"x": anchor_center["x"], "y": anchor_center["y"], "direction": "anchor_center"}
            ]

            for target in targets:
                try:
                    x, y = target["x"], target["y"]

                    # Step 1: 高精度鼠标移动序列（模拟真实人类轨迹）
                    await self.page.mouse.move(x, y, steps=15)

                    # Step 2: 悬停
                    await asyncio.sleep(hover_duration / 1000)

                    # Step 3: 长按触发 - mouse.down -> 等待 -> mouse.up
                    await self.page.mouse.down()
                    await asyncio.sleep(long_press_duration / 1000)
                    await self.page.mouse.up()

                    # Step 4: 短暂延迟
                    await asyncio.sleep(post_press_delay / 1000)

                    # Step 5: 立即发送 Escape 键
                    if escape_after:
                        await self.page.keyboard.press('Escape')
                        await asyncio.sleep(0.05)

                    result["interactions_performed"].append({
                        "anchor": anchor,
                        "target": target.get("direction", "unknown"),
                        "coordinates": {"x": x, "y": y}
                    })
                    result["total_success"] += 1

                except Exception as e:
                    result["interactions_failed"].append({
                        "anchor": anchor,
                        "target": target.get("direction", "unknown"),
                        "error": str(e)
                    })
                    result["total_failed"] += 1

        logger.info(f"  交互成功: {result['total_success']} 个")
        logger.info(f"  交互失败: {result['total_failed']} 个")
        return result

    async def _phase_c_state_snapshot(self) -> dict[str, Any]:
        """Phase C: 状态快照 - 审计 __vue_app__ 捕获 log/history 数组"""
        logger.info("🔍 Phase C: State Snapshotting (状态快照)...")

        state_config = self.ghost_config.get("state_capture", {})
        target_patterns = state_config.get("target_patterns", ["log", "history"])

        result = await self.page.evaluate(JS_PHASE3_STATE_SNAPSHOT, target_patterns)

        metadata = result.get('metadata', {})
        logger.info(f"  Vue 版本: {metadata.get('vue_version', 'unknown')}")
        logger.info(f"  捕获实体: {metadata.get('captured_count', 0)} 个")
        logger.info(f"  入口点: {len(metadata.get('entry_points_found', []))} 个")

        return result

    async def run_hydration(self) -> dict[str, Any]:
        """执行完整的三阶段水合流程"""

        if not self.target_url:
            raise ValueError("target_url 未在配置或参数中指定")

        logger.info("=" * 70)
        logger.info("V41.206 Visual State Synchronization")
        logger.info("视觉锚点水合引擎")
        logger.info("=" * 70)
        logger.info(f"🎯 目标 URL: {self.target_url}")
        logger.info(f"🎯 锚点数量: {len(self.ghost_config.get('anchors', []))}")

        # 访问页面
        await self.page.goto(self.target_url, wait_until="domcontentloaded", timeout=60000)

        # 等待 SPA 加载
        logger.info("⏳ 等待 SPA 动态内容加载...")
        await asyncio.sleep(3)

        # ========== 执行三阶段水合 ==========
        self.phase_a_result = await self._phase_a_visual_anchor_localization()
        await asyncio.sleep(0.5)

        self.phase_b_result = await self._phase_b_deep_interaction(
            self.phase_a_result["coordinates"]
        )
        await asyncio.sleep(0.5)

        self.phase_c_result = await self._phase_c_state_snapshot()

        # ========== 组装最终报告 ==========
        report = {
            "url": self.target_url,
            "timestamp": datetime.now().isoformat(),
            "version": "V41.206",
            "phase_a": self.phase_a_result,
            "phase_b": self.phase_b_result,
            "phase_c": self.phase_c_result,
            "summary": {
                "anchors_total": len(self.ghost_config.get("anchors", [])),
                "anchors_found": self.phase_a_result["total_found"],
                "interactions_success": self.phase_b_result["total_success"],
                "entities_captured": self.phase_c_result["metadata"]["captured_count"]
            }
        }

        # 保存报告到文件
        self.output_path.parent.mkdir(exist_ok=True)
        with open(self.output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        logger.info("=" * 70)
        logger.info("📊 V41.206 水合摘要")
        logger.info("=" * 70)
        logger.info(f"  锚点总数: {report['summary']['anchors_total']}")
        logger.info(f"  锚点定位: {report['summary']['anchors_found']}")
        logger.info(f"  交互成功: {report['summary']['interactions_success']}")
        logger.info(f"  实体捕获: {report['summary']['entities_captured']}")
        logger.info(f"💾 报告已保存: {self.output_path}")
        logger.info("=" * 70)

        return report

    async def close(self):
        """关闭浏览器"""
        try:
            if self.page and not self.page.is_closed():
                await self.page.close()
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
        except Exception as e:
            logger.debug(f"关闭浏览器时出错: {e}")


# =============================================================================
# CLI 入口 - V41.206
# =============================================================================

async def main():
    """CLI 主程序 - V41.206 Visual State Synchronization"""
    parser = argparse.ArgumentParser(
        description="V41.206 Visual State Synchronization - 视觉锚点水合引擎",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  # 基础用法：从 ghost_config.json 读取
  python scripts/ops/v41_195_spa_state_inspector.py

  # 指定 URL
  python scripts/ops/v41_195_spa_state_inspector.py --url "TARGET_URL"

  # 调试模式：显示浏览器
  python scripts/ops/v41_195_spa_state_inspector.py --no-headless

  # 自定义输出路径
  python scripts/ops/v41_195_spa_state_inspector.py --output custom_output.json
        """
    )

    parser.add_argument("--config", type=str, default=None, help="配置文件路径 (默认: logs/ghost_config.json)")
    parser.add_argument("--url", type=str, default=None, help="目标 SPA URL (覆盖配置文件)")
    parser.add_argument("--output", type=str, default=None, help="输出 JSON 文件路径 (默认: logs/state_debug_output.json)")
    parser.add_argument("--proxy-port", type=int, default=7892, help="代理端口 (默认: 7892)")
    parser.add_argument("--no-headless", action="store_true", help="显示浏览器窗口（调试）")

    args = parser.parse_args()

    # V41.206: 使用视觉锚点水合引擎
    engine = V41_206_VisualHydrationEngine(
        headless=not args.no_headless,
        config_path=Path(args.config) if args.config else None,
        target_url=args.url,
        output_path=Path(args.output) if args.output else None,
        proxy_port=args.proxy_port
    )

    try:
        await engine.init_browser()
        report = await engine.run_hydration()

        # V41.206: 按隐私要求输出通用摘要
        summary = report['summary']
        anchors = summary['anchors_found']
        total = summary['anchors_total']

        for i in range(total):
            status = "SUCCESS" if i < anchors else "FAIL"
            print(f"Entity [{i}] Hydration Status: {status}")

        return 0 if anchors > 0 else 1

    except Exception as e:
        logger.error(f"❌ 错误: {e}", exc_info=True)
        return 1
    finally:
        await engine.close()


# =============================================================================
# 版本别名（向后兼容）
# =============================================================================

V41_195_SPAStateInspector = V41_206_VisualHydrationEngine
V41_203_StateHydrationDebugger = V41_206_VisualHydrationEngine
V41_206_VisualHydrationEngine = V41_206_VisualHydrationEngine


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
