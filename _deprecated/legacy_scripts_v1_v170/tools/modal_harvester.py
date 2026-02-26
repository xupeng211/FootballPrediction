#!/usr/bin/env python3
"""
V41.220 "UI Resilience Audit" - 复杂动态环境下的交互式数据捕获

功能：
- 现场清理：自动关闭营销干扰弹窗
- 目标重定向：排雷后的精准二次交互
- 深度提取：结构化表格数据的完整捕获
- 智能判定：检测目标业务数据的特征

合规性：
- 非侵入式检测
- 脱敏输出（不打印具体内容）
- 低调汇报（仅状态和数量）
"""

import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from playwright.async_api import async_playwright, Page


@dataclass
class ModalSnapshot:
    """弹窗快照数据结构"""
    capture_timestamp: str
    target_url: str
    trigger_coordinates: dict[str, int]
    obstruction_cleared: bool
    modal_detected: bool
    modal_info: dict[str, Any] = field(default_factory=dict)
    has_structured_data: bool = False
    text_lines: list[str] = field(default_factory=list)
    table_rows: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class ModalHarvester:
    """
    V41.220: 智能弹窗收割器（带排雷功能）

    专用于复杂动态环境下的数据提取与一致性审计
    """

    # 目标坐标
    TRIGGER_COORDS = {"x": 199, "y": 765}

    # 交互后等待时间（毫秒）
    WAIT_AFTER_CLICK = 1500

    # 清理后等待时间（毫秒）
    WAIT_AFTER_CLEANUP = 500

    def __init__(self, config_path: str = "logs/ui_test_config.json"):
        """
        初始化收割器

        Args:
            config_path: UI 测试配置文件路径
        """
        self.config_path = Path(config_path)
        self.config: dict[str, Any] = {}
        self._load_config()

    def _load_config(self) -> None:
        """加载配置文件"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {self.config_path}")

        with open(self.config_path, encoding="utf-8") as f:
            self.config = json.load(f)

        if "target_url" not in self.config:
            raise ValueError("配置文件缺少 target_url 字段")

    def _build_cleanup_script(self) -> str:
        """
        构建现场清理脚本

        关闭所有营销干扰弹窗，为后续交互腾出净空
        """
        return """
        (() => {
            const result = {
                cleared_count: 0,
                cleared_elements: [],
                used_escape: false
            };

            // 目标关键词
            const obstructionKeywords = ['overlay', 'modal', 'popup', 'dialog', 'banner'];
            const closeKeywords = ['close', 'x', 'dismiss', 'hide', 'remove'];

            // 1. 查找并关闭 overlay-bookie-modal
            const bookieModal = document.querySelector('.overlay-bookie-modal');
            if (bookieModal) {
                // 尝试查找关闭按钮
                const closeBtn = bookieModal.querySelector('[class*="close"], [class*="x"], button, [aria-label*="close"]');
                if (closeBtn) {
                    closeBtn.click();
                    result.cleared_elements.push({
                        type: 'overlay-bookie-modal',
                        method: 'close_button'
                    });
                    result.cleared_count++;
                } else {
                    // 直接隐藏整个 modal
                    bookieModal.style.display = 'none';
                    result.cleared_elements.push({
                        type: 'overlay-bookie-modal',
                        method: 'hide_direct'
                    });
                    result.cleared_count++;
                }
            }

            // 2. 查找所有包含干扰关键词的可见元素
            const allElements = document.querySelectorAll('*');
            for (const el of allElements) {
                const style = window.getComputedStyle(el);
                if (style.display === 'none' || style.visibility === 'hidden') continue;

                // 安全地获取 className 和 id
                const className = String(el.className || '').toLowerCase();
                const id = String(el.id || '').toLowerCase();

                // 检查是否包含干扰关键词
                const hasObstructionKeyword = obstructionKeywords.some(kw =>
                    className.includes(kw) || id.includes(kw)
                );

                if (hasObstructionKeyword) {
                    // 尝试查找关闭按钮
                    const closeBtn = el.querySelector('[class*="close"], [class*="x"], button, [aria-label*="close"]');
                    if (closeBtn) {
                        closeBtn.click();
                        result.cleared_elements.push({
                            type: el.className || el.id || 'unknown',
                            method: 'close_button'
                        });
                        result.cleared_count++;
                    }
                }
            }

            return result;
        })();
        """

    def _build_modal_detector_script(self) -> str:
        """
        构建弹窗检测脚本（增强版）

        识别 z-index 最大的容器，智能判定是否包含目标业务数据
        """
        return """
        (() => {
            const result = {
                detected: false,
                container: null,
                has_table: false,
                has_list: false,
                has_structured_data: false,
                z_index: -1,
                text_lines: [],
                table_rows: []
            };

            // 获取所有可见的定位元素
            const allElements = document.querySelectorAll('*');
            let maxZIndex = -1;
            let topModal = null;

            for (const el of allElements) {
                const style = window.getComputedStyle(el);
                const zIndex = parseInt(style.zIndex);
                const position = style.position;
                const display = style.display;

                // 只考虑定位的、可见的元素
                if (position !== 'static' && display !== 'none' &&
                    zIndex > maxZIndex && zIndex < 999999) {
                    maxZIndex = zIndex;
                    topModal = el;
                }
            }

            // 检查是否包含表格或列表
            if (topModal) {
                result.detected = true;
                result.container = {
                    tagName: topModal.tagName,
                    id: topModal.id || '',
                    className: topModal.className || '',
                    zIndex: maxZIndex
                };

                // 检测表格
                const tables = topModal.querySelectorAll('table');
                result.has_table = tables.length > 0;

                // 检测列表
                const lists = topModal.querySelectorAll('ul, ol, dl');
                result.has_list = lists.length > 0;

                // 智能判定：检查是否包含结构化业务数据
                result.has_structured_data = result.has_table || result.has_list;

                // 提取所有文本行（按视觉块分割）
                const textBlocks = topModal.querySelectorAll('div, p, span, td, th, li');
                const linesSet = new Set();

                for (const block of textBlocks) {
                    const text = block.textContent?.trim();
                    if (text && text.length > 0 && text.length < 500) {
                        linesSet.add(text);
                    }
                }

                result.text_lines = Array.from(linesSet);

                // 深度提取表格行数据
                if (result.has_table) {
                    for (const table of tables) {
                        const rows = table.querySelectorAll('tr');
                        for (const row of rows) {
                            const cells = row.querySelectorAll('td, th');
                            const cellData = [];

                            for (const cell of cells) {
                                // 提取单元格的完整信息
                                const text = cell.textContent?.trim() || '';
                                const hasTimePattern = /\d{1,2}:\d{2}/.test(text);
                                const hasNumberPattern = /\d+\.\d+/.test(text);

                                cellData.push({
                                    text: text,
                                    has_time: hasTimePattern,
                                    has_number: hasNumberPattern,
                                    tag_name: cell.tagName
                                });
                            }

                            if (cellData.length > 0 && cellData.some(c => c['text'].length > 0)) {
                                result.table_rows.push({
                                    column_count: cellData.length,
                                    cells: cellData
                                });
                            }
                        }
                    }
                }
            }

            return result;
        })();
        """

    async def harvest_modal(
        self,
        headless: bool = True,
        wait_before_click: int = 2000
    ) -> ModalSnapshot:
        """
        执行弹窗收割（带排雷功能）

        Args:
            headless: 是否使用无头模式
            wait_before_click: 点击前等待时间（毫秒）

        Returns:
            弹窗快照
        """
        target_url = self.config.get("target_url")
        obstruction_cleared = False

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=headless)
            page = await browser.new_page()

            # 加载页面
            await page.goto(target_url, wait_until="networkidle")

            # 等待页面稳定
            await asyncio.sleep(wait_before_click / 1000)

            # Step 1: 现场清理（排雷）
            cleanup_script = self._build_cleanup_script()
            cleanup_result = await page.evaluate(cleanup_script)
            obstruction_cleared = cleanup_result.get("cleared_count", 0) > 0

            # 发送 Escape 键作为备用清理
            await page.keyboard.press("Escape")

            # 等待 UI 净空
            await asyncio.sleep(self.WAIT_AFTER_CLEANUP / 1000)

            # Step 2: 目标重定向（精准二次交互）
            x = self.TRIGGER_COORDS["x"]
            y = self.TRIGGER_COORDS["y"]
            await page.mouse.click(x, y)

            # 等待弹窗渲染
            await asyncio.sleep(self.WAIT_AFTER_CLICK / 1000)

            # Step 3: 深度检测与提取
            detect_script = self._build_modal_detector_script()
            modal_data = await page.evaluate(detect_script)

            # 构建快照
            snapshot = ModalSnapshot(
                capture_timestamp=datetime.now().isoformat(),
                target_url=target_url,
                trigger_coordinates=self.TRIGGER_COORDS.copy(),
                obstruction_cleared=obstruction_cleared,
                modal_detected=modal_data.get("detected", False),
                modal_info=modal_data.get("container") or {},
                has_structured_data=modal_data.get("has_structured_data", False),
                text_lines=modal_data.get("text_lines") or [],
                table_rows=modal_data.get("table_rows") or [],
                metadata={
                    "scan_version": "V41.220",
                    "has_table": modal_data.get("has_table", False),
                    "has_list": modal_data.get("has_list", False),
                    "z_index": modal_data.get("container", {}).get("z_index", -1),
                    "cleanup_details": cleanup_result
                }
            )

            await browser.close()

        return snapshot

    def save_snapshot(
        self,
        snapshot: ModalSnapshot,
        output_path: str = "logs/modal_audit_final.json"
    ) -> None:
        """
        保存弹窗快照

        Args:
            snapshot: 弹窗快照
            output_path: 输出文件路径
        """
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        serializable = {
            "version": "V41.220",
            "capture_timestamp": snapshot.capture_timestamp,
            "target_url": snapshot.target_url,
            "trigger_coordinates": snapshot.trigger_coordinates,
            "obstruction_cleared": snapshot.obstruction_cleared,
            "modal_detected": snapshot.modal_detected,
            "has_structured_data": snapshot.has_structured_data,
            "modal_info": snapshot.modal_info,
            "text_lines_count": len(snapshot.text_lines),
            "text_lines": snapshot.text_lines,
            "table_rows_count": len(snapshot.table_rows),
            "table_rows": snapshot.table_rows,
            "metadata": snapshot.metadata
        }

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(serializable, f, indent=2, ensure_ascii=False)


# CLI 入口
async def main():
    """命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(
        description="V41.220 UI Resilience Audit - 复杂动态环境下的交互式数据捕获"
    )
    parser.add_argument(
        "--config",
        default="logs/ui_test_config.json",
        help="UI 测试配置文件路径"
    )
    parser.add_argument("--headless", action="store_true", help="启用无头模式")
    parser.add_argument(
        "--output",
        default="logs/modal_audit_final.json",
        help="输出文件路径"
    )
    parser.add_argument(
        "--wait-before-click",
        type=int,
        default=2000,
        help="点击前等待时间（毫秒）"
    )

    args = parser.parse_args()

    try:
        harvester = ModalHarvester(config_path=args.config)
        snapshot = await harvester.harvest_modal(
            headless=args.headless,
            wait_before_click=args.wait_before_click
        )

        # 保存快照
        harvester.save_snapshot(snapshot, output_path=args.output)

        # 脱敏输出
        cleared_status = "Yes" if snapshot.obstruction_cleared else "No"
        rows_count = len(snapshot.table_rows)

        print(f"Obstruction Cleared: {cleared_status}")
        print(f"Structured Rows Found: {rows_count}")

        return 0

    except FileNotFoundError as e:
        print(f"错误: {e}")
        return 1
    except ValueError as e:
        print(f"配置错误: {e}")
        return 1
    except Exception as e:
        print(f"执行错误: {e}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
