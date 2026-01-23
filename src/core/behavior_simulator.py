#!/usr/bin/env python3
"""V41.590 Human Behavior Simulator - 人机交互模拟器

This module provides realistic human-like behavior patterns to evade
bot detection systems. It simulates mouse movements, typing patterns,
and interaction timing that mimic real users.

Key Features:
    - Mouse jitter and random movements
    - Random typing delays and patterns
    - Human-like waiting and thinking times
    - Random scroll behavior with momentum
    - Interaction rhythm randomization

Author: V41.590 Stealth Team
Date: 2026-01-21
"""

from __future__ import annotations

import asyncio
import logging
import random
from dataclasses import dataclass
from typing import Any

from playwright.async_api import Page

logger = logging.getLogger(__name__)


# ============================================================================
# Human Behavior Configuration
# ============================================================================

# 鼠标抖动偏移量 (像素)
MOUSE_JITTER_OFFSETS = [
    (-2, -2), (2, -2), (-2, 2), (2, 2),
    (0, -3), (0, 3), (-3, 0), (3, 0),
    (-1, -1), (1, -1), (-1, 1), (1, 1),
    (0, 0),  # 偶尔不抖动
]

# 等待时间范围 (秒)
WAIT_TIMES = {
    "short": (1.0, 3.0),      # 短等待：页面加载后
    "medium": (2.0, 5.0),     # 中等待：交互之间
    "long": (5.0, 10.0),      # 长等待：复杂操作后
    "thinking": (1.5, 4.0),   # 思考时间：重要决策前
}

__all__ = [
    "HumanBehaviorSimulator",
    "get_behavior_simulator",
    "human_hover",
    "stealth_wait",
    "MOUSE_JITTER_OFFSETS",
    "WAIT_TIMES",
]

# 滚动行为参数
SCROLL_CONFIG = {
    "min_scroll": 100,        # 最小滚动距离
    "max_scroll": 500,        # 最大滚动距离
    "scroll_steps": (3, 8),   # 滚动步数
    "step_delay": (50, 200),  # 每步延迟 (毫秒)
}


# ============================================================================
# Behavior Simulator
# ============================================================================


class HumanBehaviorSimulator:
    """V41.590: 人机交互模拟器

    模拟真实用户的行为模式，用于反机器人检测。

    特性:
    - 鼠标抖动 (Mouse Jitter): 随机的微小鼠标移动
    - 随机等待: 不规律的延迟时间
    - 自然滚动: 带惯性的平滑滚动
    - 交互节奏: 模拟真实用户的操作节奏

    Example:
        >>> simulator = HumanBehaviorSimulator()
        >>> await simulator.mouse_jitter(page)
        >>> await simulator.random_wait("medium")
        >>> await simulator.natural_scroll(page)
    """

    def __init__(self, seed: int | None = None):
        """初始化行为模拟器

        Args:
            seed: 随机种子（用于测试，生产环境通常为 None）
        """
        if seed is not None:
            random.seed(seed)

    async def mouse_jitter(
        self,
        page: Page,
        x: int | None = None,
        y: int | None = None
    ) -> None:
        """V41.590: 鼠标抖动 - 模拟人类手部微颤

        在目标位置附近进行微小的随机移动，模拟真实用户
        鼠标悬停时手部自然抖动。

        Args:
            page: Playwright Page 对象
            x: 目标 X 坐标 (None 表示使用当前位置)
            y: 目标 Y 坐标 (None 表示使用当前位置)
        """
        if x is not None and y is not None:
            # 先移动到目标位置
            await page.mouse.move(x, y)

        # 执行 2-4 次微小抖动
        jitter_count = random.randint(2, 4)

        for _ in range(jitter_count):
            offset_x, offset_y = random.choice(MOUSE_JITTER_OFFSETS)
            await page.mouse.move(offset_x, offset_y)

            # 短暂延迟 (50-150ms)
            await asyncio.sleep(random.uniform(0.05, 0.15))

        logger.debug(f"[BehaviorSimulator] 鼠标抖动: {jitter_count} 次")

    async def random_wait(
        self,
        wait_type: str = "medium",
        min_multiplier: float = 0.8,
        max_multiplier: float = 1.5
    ) -> None:
        """随机等待 - 模拟人类操作的不规律性

        Args:
            wait_type: 等待类型 ("short", "medium", "long", "thinking")
            min_multiplier: 最小时间倍数
            max_multiplier: 最大时间倍数
        """
        if wait_type not in WAIT_TIMES:
            wait_type = "medium"

        min_wait, max_wait = WAIT_TIMES[wait_type]

        # 应用随机倍数
        actual_min = min_wait * min_multiplier
        actual_max = max_wait * max_multiplier

        wait_time = random.uniform(actual_min, actual_max)

        logger.debug(f"[BehaviorSimulator] 随机等待: {wait_type} = {wait_time:.2f}秒")
        await asyncio.sleep(wait_time)

    async def natural_scroll(
        self,
        page: Page,
        direction: str = "down",
        distance: int | None = None
    ) -> None:
        """自然滚动 - 带惯性的平滑滚动

        模拟真实用户的滚动行为，具有加速和减速的惯性效果。

        Args:
            page: Playwright Page 对象
            direction: 滚动方向 ("up" 或 "down")
            distance: 滚动距离 (None 表示随机)
        """
        if distance is None:
            distance = random.randint(SCROLL_CONFIG["min_scroll"], SCROLL_CONFIG["max_scroll"])

        # 计算滚动步数
        min_steps, max_steps = SCROLL_CONFIG["scroll_steps"]
        num_steps = random.randint(min_steps, max_steps)

        step_distance = distance / num_steps
        min_delay, max_delay = SCROLL_CONFIG["step_delay"]

        # 执行分段滚动（模拟惯性）
        for i in range(num_steps):
            # 加速阶段
            if i < num_steps / 3:
                delay_factor = 1.0 - (i / (num_steps / 3)) * 0.3
            # 减速阶段
            else:
                remaining = num_steps - i
                delay_factor = 1.0 - (remaining / (num_steps * 0.7)) * 0.5

            delay = random.uniform(min_delay, max_delay) * delay_factor

            scroll_amount = step_distance if direction == "down" else -step_distance

            await page.evaluate(f"window.scrollBy(0, {scroll_amount})")
            await asyncio.sleep(delay / 1000)  # 转换为秒

        logger.debug(f"[BehaviorSimulator] 自然滚动: {direction} {distance}px ({num_steps}步)")

    async def human_click(
        self,
        page: Page,
        selector: str | None = None,
        x: int | None = None,
        y: int | None = None,
        button: str = "left"
    ) -> None:
        """人类点击 - 带随机延迟的点击操作

        Args:
            page: Playwright Page 对象
            selector: CSS 选择器
            x: X 坐标
            y: Y 坐标
            button: 鼠标按钮 ("left", "middle", "right")
        """
        # 点击前的"瞄准"时间
        await self.random_wait("short", 0.5, 1.5)

        # 移动到目标位置
        if selector:
            await page.click(selector, delay=random.randint(50, 200))
        elif x is not None and y is not None:
            await page.mouse.move(x, y)
            await self.random_wait("short", 0.2, 0.8)
            await page.mouse.click(button)
        else:
            raise ValueError("必须指定 selector 或坐标")

        # 点击后的"反应"时间
        await self.random_wait("short", 0.3, 1.0)

        logger.debug(f"[BehaviorSimulator] 人类点击: {selector or f'({x}, {y})'}")

    async def simulate_reading(
        self,
        page: Page,
        min_duration: float = 2.0,
        max_duration: float = 8.0
    ) -> None:
        """模拟阅读行为 - 随机停留和微动

        Args:
            page: Playwright Page 对象
            min_duration: 最短阅读时间
            max_duration: 最长阅读时间
        """
        duration = random.uniform(min_duration, max_duration)
        start_time = asyncio.get_event_loop().time()

        # 随机进行微小的滚动（模拟阅读过程中的调整）
        while (asyncio.get_event_loop().time() - start_time) < duration:
            await asyncio.sleep(random.uniform(0.5, 2.0))

            # 偶尔进行微小滚动
            if random.random() > 0.7:
                scroll_amount = random.choice([-50, -30, 30, 50])
                await page.evaluate(f"window.scrollBy(0, {scroll_amount})")

        logger.debug(f"[BehaviorSimulator] 模拟阅读: {duration:.2f}秒")

    async def simulate_form_filling(
        self,
        page: Page,
        field_values: dict[str, str]
    ) -> None:
        """模拟表单填写 - 人类打字速度和错误更正

        Args:
            page: Playwright Page 对象
            field_values: 字典 {selector: value}
        """
        for selector, value in field_values.items():
            # 点击输入框
            await page.click(selector)

            # 思考时间
            await self.random_wait("short", 0.5, 1.5)

            # 逐字符输入（模拟打字）
            for char in value:
                await page.type(selector, char, delay=random.randint(50, 200))

            # 偶尔"打错"并更正
            if random.random() < 0.1:  # 10% 概率
                wrong_char = chr(ord(value[-1]) + 1) if value else "a"
                await page.type(selector, wrong_char, delay=random.randint(50, 100))
                await asyncio.sleep(0.3)
                # 按退格键删除
                await page.keyboard.press("Backspace")
                await asyncio.sleep(0.2)
                # 重新输入正确字符
                await page.type(selector, value[-1], delay=random.randint(80, 150))

            # 下一个字段前的思考时间
            await self.random_wait("short", 0.3, 1.0)

        logger.debug(f"[BehaviorSimulator] 表单填写: {len(field_values)} 个字段")


# ============================================================================
# Convenience Functions
# ============================================================================

async def human_hover(
    page: Page,
    selector: str,
    min_duration: float = 1.0,
    max_duration: float = 3.0
) -> None:
    """人类悬停 - 自然地将鼠标悬停在元素上

    Args:
        page: Playwright Page 对象
        selector: CSS 选择器
        min_duration: 最短悬停时间
        max_duration: 最长悬停时间
    """
    simulator = HumanBehaviorSimulator()

    # 移动到元素
    element = await page.query_selector(selector)
    if element:
        box = await element.bounding_box()
        if box:
            await page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)

            # 随机悬停时间
            duration = random.uniform(min_duration, max_duration)
            await asyncio.sleep(duration)

            # 悬停期间进行微小抖动
            await simulator.mouse_jitter(page)

            logger.debug(f"[HumanHover] 悬停 {selector}: {duration:.2f}秒")


async def stealth_wait(
    wait_type: str = "medium",
    min_multiplier: float = 0.8,
    max_multiplier: float = 1.5
) -> None:
    """隐身等待 - 随机延迟以避开时间模式检测

    Args:
        wait_type: 等待类型
        min_multiplier: 最小时间倍数
        max_multiplier: 最大时间倍数
    """
    simulator = HumanBehaviorSimulator()
    await simulator.random_wait(wait_type, min_multiplier, max_multiplier)


# ============================================================================
# Singleton Instance
# ============================================================================

_behavior_simulator_instance: HumanBehaviorSimulator | None = None


def get_behavior_simulator(seed: int | None = None) -> HumanBehaviorSimulator:
    """获取行为模拟器单例

    Args:
        seed: 随机种子

    Returns:
        HumanBehaviorSimulator 单例实例
    """
    global _behavior_simulator_instance
    if _behavior_simulator_instance is None:
        _behavior_simulator_instance = HumanBehaviorSimulator(seed=seed)
    return _behavior_simulator_instance
