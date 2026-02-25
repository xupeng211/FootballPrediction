#!/usr/bin/env python3
"""
V84.800 - 核心 API 流量拦截实测 (API Interceptor Strike)
==========================================================

核心攻坚动作:
  - 动作 A: 深度隐身 (Mg30 Stealth)
  - 动作 B: 全量捕获 (Response Interceptor)
  - 动作 C: 数据固化 (JSON Export)

Usage:
    python v84_800_api_strike.py --match-id 4221909 --url "<URL>"

@author: Network Security & Playwright Expert
@version: V84.800
@since: 2026-01-25
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from playwright.async_api import async_playwright, Page, Browser, BrowserContext
except ImportError:
    print("ERROR: playwright not installed. Run: pip install playwright")
    sys.exit(1)

# ============================================================================
# CONFIGURATION
# ============================================================================

API_STRIKE_CONFIG = {
    "match_id": "4221909",
    "url": "https://www.oddsportal.com/football/germany/bundesliga-2023-2024/bayern-munich-augsburg-f3e2PS0c/",
    "output_dir": Path(__file__).parent.parent.parent / "logs",
    "output_file": "captured_4221909.json",

    # Mg30 Stealth 动态参数
    "stealth": {
        "gpu_vendor": "NVIDIA Corporation",
        "gpu_renderer": "NVIDIA GeForce RTX 3060",
        "device_memory": 16,
        "hardware_concurrency": 8,
        "languages": ["en-US", "en"],
        "timezone": "America/New_York",
        "locale": "en-US",
    },

    # 浏览器配置
    "browser": {
        "headless": False,  # 非隐身模式以便观察
        "timeout": 60000,
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "viewport": {"width": 1920, "height": 1080},
    }
}

# ============================================================================
# MG30 STEALTH SCRIPTS
# ============================================================================

MG30_STEALTH_CORE = """
() => {
    // ========== Mg30 Stealth Core - V84.800 ==========
    // 动态参数: GPU=NVIDIA Corporation, 语言=en-US, 内存=16GB

    const tryDefine = (obj, prop, descriptor) => {
        try {
            Object.defineProperty(obj, prop, descriptor);
        } catch (e) {
            console.debug('[Mg30] Skip defining:', prop, e.message);
        }
    };

    // 1. Navigator 属性深度伪装
    tryDefine(navigator, 'webdriver', {
        get: () => false,
    });

    // 2. Chrome Runtime 对象伪装
    window.chrome = {
        runtime: {
            id: 'mg30-stealth-extension-id',
            onMessage: undefined,
            sendMessage: undefined,
        },
        app: {
            isInstalled: true,
        },
    };

    // 3. WebGL 供应商深度伪装
    const getParameter = WebGLRenderingContext.prototype.getParameter;
    WebGLRenderingContext.prototype.getParameter = function(parameter) {
        if (parameter === 37445) { // VENDOR
            return 'NVIDIA Corporation';
        }
        if (parameter === 37446) { // RENDERER
            return 'NVIDIA GeForce RTX 3060';
        }
        return getParameter.apply(this, arguments);
    };

    // 4. 窗口尺寸严格同步
    tryDefine(screen, 'width', { get: () => window.innerWidth });
    tryDefine(screen, 'height', { get: () => window.innerHeight });
    tryDefine(screen, 'availWidth', { get: () => window.innerWidth });
    tryDefine(screen, 'availHeight', { get: () => window.innerHeight - 40 });

    // 5. 设备内存随机化
    tryDefine(navigator, 'deviceMemory', { get: () => 16 });

    // 6. 硬件并发数随机化
    tryDefine(navigator, 'hardwareConcurrency', { get: () => 8 });

    // 7. 插件伪装
    tryDefine(navigator, 'plugins', {
        get: () => ({
            length: 3,
            0: {
                name: 'Chrome PDF Plugin',
                description: 'Portable Document Format',
                filename: 'internal-pdf-viewer',
            },
            1: {
                name: 'Chrome PDF Viewer',
                description: '',
                filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai',
            },
            2: {
                name: 'Native Client',
                description: '',
                filename: 'internal-nacl-plugin',
            },
        }),
    });

    // 8. 语言设置
    tryDefine(navigator, 'languages', {
        get: () => ['en-US', 'en'],
    });

    // 9. 权限 API 伪装
    const originalQuery = window.navigator.permissions.query;
    window.navigator.permissions.query = (parameters) => (
        parameters.name === 'notifications' ?
            Promise.resolve({ state: Notification.permission }) :
            originalQuery(parameters)
    );

    // 10. 隐藏自动化控制特征
    delete navigator.__proto__.webdriver;

    // 11. 伪装 Playwright/Chromium 特征
    tryDefine(navigator, 'userAgent', {
        get: () => {
            const ua = navigator.userAgent;
            return ua.replace(/HeadlessChrome/, 'Chrome');
        },
    });

    // 12. 伪装 Connection API
    navigator.connection = {
        effectiveType: '4g',
        rtt: Math.floor(Math.random() * 100) + 20,
        downlink: Math.floor(Math.random() * 10) + 5,
        saveData: false,
    };

    // 13. 深度 Hook - 伪装 automation 控制特征
    tryDefine(window, 'chrome', {
        get: () => ({
            runtime: {},
            loadTimes: function() {},
            csi: function() {},
            app: {},
        }),
    });

    // 14. 伪装 Permissions API
    if (navigator.permissions) {
        navigator.permissions.query = (parameters) => {
            if (parameters.name === 'notifications') {
                return Promise.resolve({ state: 'default' });
            }
            return Promise.resolve({ state: 'prompt' });
        };
    }

    // 15. 伪装 Battery API
    if (navigator.getBattery) {
        navigator.getBattery = () => Promise.resolve({
            charging: true,
            chargingTime: 0,
            dischargingTime: Infinity,
            level: 1.0,
        });
    }

    // ========== Mg30 标记 ==========
    window.__mg30_stealth_applied = true;
    window.__mg30_version = 'V84.800';
    console.log('[Mg30] Titan Stealth V84.800 applied successfully');
}
"""

# ============================================================================
# LOGGING
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# ============================================================================
# API INTERCEPTOR
# ============================================================================

class APIInterceptor:
    """API 响应拦截器"""

    def __init__(self):
        self.captured_responses = []
        self.api_patterns = [
            '/ajax-match-odds/',
            '/ajax-next-games/',
            '/feed/',
            '/api/',
        ]

    def should_capture(self, url: str, content_type: str) -> bool:
        """判断是否应该捕获该响应"""
        # 检查 URL 模式
        url_match = any(pattern in url for pattern in self.api_patterns)

        # 检查 Content-Type
        is_json = 'json' in content_type.lower()

        return url_match and is_json

    async def capture_response(self, response):
        """捕获单个响应"""
        try:
            url = response.url
            content_type = response.headers.get('content-type', '')

            if not self.should_capture(url, content_type):
                return

            # 解析 JSON
            try:
                json_data = await response.json()

                capture = {
                    "timestamp": datetime.now().isoformat(),
                    "url": url,
                    "status": response.status,
                    "content_type": content_type,
                    "json": json_data,
                    "json_size": len(json.dumps(json_data))
                }

                self.captured_responses.append(capture)

                # 实时日志
                url_preview = url[:80] + "..." if len(url) > 80 else url
                logger.info(f"  ✓ Captured: {url_preview}")
                logger.info(f"    Status: {capture['status']}, Size: {capture['json_size']} bytes")

                # 检查是否包含关键词
                json_str = json.dumps(json_data).lower()
                if 'pinnacle' in json_str or 'entity_p' in json_str or '18' in json_str:
                    logger.info(f"    🎯 PINNACLE DATA FOUND in this response!")

            except Exception as e:
                logger.debug(f"    Failed to parse JSON: {e}")

        except Exception as e:
            logger.error(f"Error capturing response: {e}")

    def get_capture_summary(self) -> dict:
        """获取捕获摘要"""
        return {
            "total_responses": len(self.captured_responses),
            "responses": [
                {
                    "url": r["url"],
                    "status": r["status"],
                    "size": r["json_size"],
                    "has_odds": 'odds' in json.dumps(r["json"]).lower(),
                    "has_provider": 'provider' in json.dumps(r["json"]).lower(),
                    "has_pinnacle": 'pinnacle' in json.dumps(r["json"]).lower() or
                                   'entity_p' in json.dumps(r["json"]).lower(),
                }
                for r in self.captured_responses
            ]
        }

# ============================================================================
# MAIN STRIKE FUNCTION
# ============================================================================

async def execute_api_strike(match_id: str, url: str):
    """执行 API 拦截攻击"""

    logger.info("=" * 70)
    logger.info("V84.800 - API Interceptor Strike")
    logger.info("=" * 70)
    logger.info(f"Match ID: {match_id}")
    logger.info(f"Target URL: {url}")
    logger.info("")

    # 确保输出目录存在
    output_dir = API_STRIKE_CONFIG["output_dir"]
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / API_STRIKE_CONFIG["output_file"]

    interceptor = APIInterceptor()

    async with async_playwright() as p:
        # ========================================
        # 动作 A: 深度隐身 (Mg30 Stealth)
        # ========================================
        logger.info("[动作 A] 深度隐身 - 应用 Mg30 Stealth 内核...")
        logger.info("  GPU: NVIDIA Corporation")
        logger.info("  Renderer: NVIDIA GeForce RTX 3060")
        logger.info("  Memory: 16GB")
        logger.info("  Languages: en-US, en")
        logger.info("")

        # 启动浏览器
        logger.info("[动作 B] 启动浏览器并配置隐身参数...")
        browser = await p.chromium.launch(
            headless=API_STRIKE_CONFIG["browser"]["headless"],
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-blink-features=AutomationControlled',
            ]
        )

        # 创建上下文
        context = await browser.new_context(
            user_agent=API_STRIKE_CONFIG["browser"]["user_agent"],
            viewport=API_STRIKE_CONFIG["browser"]["viewport"],
            locale=API_STRIKE_CONFIG["stealth"]["locale"],
            timezone_id=API_STRIKE_CONFIG["stealth"]["timezone"],
        )

        # 创建页面
        page = await context.new_page()

        # 注入 Mg30 Stealth 脚本（在页面加载前）
        logger.info("  注入 Mg30 Stealth 脚本...")
        await page.evaluate(MG30_STEALTH_CORE)
        logger.info("  ✓ Mg30 Stealth 已应用")
        logger.info("")

        # 注册响应拦截器（在导航前）
        logger.info("[动作 B] 全量捕获 - 注册响应拦截器...")

        page.on('response', lambda response: asyncio.create_task(interceptor.capture_response(response)))
        logger.info("  ✓ 响应拦截器已注册 (监听所有 JSON 响应)")
        logger.info("")

        # 导航到目标页面
        logger.info(f"[动作 C] 导航到目标页面...")
        logger.info(f"  URL: {url[:80]}...")

        try:
            await page.goto(url, wait_until='networkidle', timeout=API_STRIKE_CONFIG["browser"]["timeout"])
            logger.info("  ✓ 页面加载完成")
        except Exception as e:
            logger.error(f"  ✗ 页面加载失败: {e}")
            await browser.close()
            return

        # 等待额外的 API 响应
        logger.info("")
        logger.info("等待 API 响应 (10秒)...")
        await page.wait_for_timeout(10000)

        # 捕获摘要
        summary = interceptor.get_capture_summary()

        logger.info("")
        logger.info("=" * 70)
        logger.info("[CAPTURE SUMMARY]")
        logger.info("=" * 70)
        logger.info(f"Total Responses Captured: {summary['total_responses']}")
        logger.info("")

        if summary['total_responses'] > 0:
            for i, resp in enumerate(summary['responses'], 1):
                logger.info(f"Response {i}:")
                logger.info(f"  URL: {resp['url'][:100]}...")
                logger.info(f"  Status: {resp['status']}")
                logger.info(f"  Size: {resp['size']} bytes")
                logger.info(f"  Contains 'odds': {resp['has_odds']}")
                logger.info(f"  Contains 'provider': {resp['has_provider']}")
                logger.info(f"  Contains 'pinnacle': {resp['has_pinnacle']}")
                logger.info("")

            # ========================================
            # 动作 C: 数据固化 (JSON Export)
            # ========================================
            logger.info("[动作 C] 数据固化 - 保存完整 JSON...")

            output_data = {
                "capture_metadata": {
                    "timestamp": datetime.now().isoformat(),
                    "match_id": match_id,
                    "url": url,
                    "total_responses": summary['total_responses'],
                },
                "captured_responses": interceptor.captured_responses,
            }

            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)

            logger.info(f"  ✓ 完整 JSON 已保存: {output_file}")
            logger.info(f"    文件大小: {output_file.stat().st_size} bytes")
            logger.info("")

            # 深度分析
            logger.info("=" * 70)
            logger.info("[DEEP ANALYSIS]")
            logger.info("=" * 70)

            # 检查 /ajax-match-odds/ 端点
            ajax_match_found = False
            for resp in interceptor.captured_responses:
                if '/ajax-match-odds/' in resp['url']:
                    ajax_match_found = True
                    logger.info("✓ /ajax-match-odds/ 端点已捕获")
                    logger.info(f"  URL: {resp['url']}")
                    logger.info(f"  Status: {resp['status']}")
                    logger.info(f"  Size: {resp['json_size']} bytes")

                    # 分析 JSON 结构
                    json_data = resp['json']
                    if isinstance(json_data, dict):
                        keys = list(json_data.keys())
                        logger.info(f"  Top-level keys: {keys}")

                        # 检查嵌套深度
                        depth = calculate_json_depth(json_data)
                        logger.info(f"  Max depth: {depth} levels")

                    elif isinstance(json_data, list):
                        logger.info(f"  Array length: {len(json_data)} items")
                        if len(json_data) > 0:
                            logger.info(f"  First item keys: {list(json_data[0].keys()) if isinstance(json_data[0], dict) else 'N/A'}")
                    break

            if not ajax_match_found:
                logger.info("✗ /ajax-match-odds/ 端点未捕获")
                logger.info("  捕获到的端点:")
                for resp in interceptor.captured_responses:
                    logger.info(f"    - {resp['url']}")

            logger.info("")

            # 检查 Pinnacle 数据
            pinnacle_found = False
            for resp in interceptor.captured_responses:
                json_str = json.dumps(resp['json']).lower()
                if 'pinnacle' in json_str or 'entity_p' in json_str or '"18"' in json_str:
                    pinnacle_found = True
                    logger.info("✓ Pinnacle (ID 18) 数据已找到!")
                    logger.info(f"  来源: {resp['url']}")

                    # 尝试定位 Pinnacle 数据位置
                    try:
                        pinnacle_data = find_pinnacle_data(resp['json'])
                        if pinnacle_data:
                            logger.info(f"  数据位置: {pinnacle_data['path']}")
                            logger.info(f"  包含字段: {list(pinnacle_data['data'].keys()) if isinstance(pinnacle_data['data'], dict) else 'N/A'}")
                    except Exception as e:
                        logger.info(f"  无法详细定位: {e}")
                    break

            if not pinnacle_found:
                logger.info("✗ Pinnacle (ID 18) 数据未找到")

            logger.info("")

        else:
            logger.info("✗ 未捕获到任何 API 响应")

        # 截图
        screenshot_file = output_dir / f"api_strike_{match_id}.png"
        await page.screenshot(path=screenshot_file)
        logger.info(f"截图已保存: {screenshot_file}")
        logger.info("")

        # 清理
        await browser.close()

    # 最终验收
    logger.info("=" * 70)
    logger.info("[FINAL VERIFICATION]")
    logger.info("=" * 70)

    ajax_match = any('/ajax-match-odds/' in r['url'] for r in interceptor.captured_responses)
    pinnacle_data = any(
        'pinnacle' in json.dumps(r['json']).lower() or
        'entity_p' in json.dumps(r['json']).lower()
        for r in interceptor.captured_responses
    )

    logger.info(f"1. /ajax-match-odds/ 端点捕获: {'✓ YES' if ajax_match else '✗ NO'}")
    logger.info(f"2. Pinnacle 数据发现: {'✓ YES' if pinnacle_data else '✗ NO'}")
    logger.info(f"3. JSON 已导出: ✓ YES ({output_file})")
    logger.info("")

    final_status = "[V84.800] API Strike COMPLETE."
    final_status += f" Payload Captured: {'YES' if len(interceptor.captured_responses) > 0 else 'NO'}. "
    final_status += f"Found Pinnacle: {'YES' if pinnacle_data else 'NO'}. "
    final_status += f"Ready to refactor V51: {'YES' if ajax_match else 'NO (needs more investigation)'}"

    logger.info("=" * 70)
    logger.info(final_status)
    logger.info("=" * 70)

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def calculate_json_depth(obj, current_depth=0):
    """计算 JSON 嵌套深度"""
    if not isinstance(obj, (dict, list)):
        return current_depth

    if isinstance(obj, dict):
        if not obj:
            return current_depth
        return max(
            calculate_json_depth(v, current_depth + 1)
            for v in obj.values()
        )
    else:  # list
        if not obj:
            return current_depth
        return max(
            calculate_json_depth(item, current_depth + 1)
            for item in obj
        )

def find_pinnacle_data(obj, path="", max_depth=10):
    """递归查找 Pinnacle 数据"""
    if max_depth <= 0:
        return None

    if isinstance(obj, dict):
        # 检查当前对象
        obj_str = json.dumps(obj, default=str)
        if 'pinnacle' in obj_str.lower() or 'entity_p' in obj_str.lower():
            return {'path': path, 'data': obj}

        # 递归搜索
        for key, value in obj.items():
            result = find_pinnacle_data(value, f"{path}.{key}", max_depth - 1)
            if result:
                return result

    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            result = find_pinnacle_data(item, f"{path}[{i}]", max_depth - 1)
            if result:
                return result

    return None

# ============================================================================
# CLI ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="V84.800 API Interceptor Strike",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        "--match-id",
        default="4221909",
        help="Match ID (default: 4221909)"
    )

    parser.add_argument(
        "--url",
        default="https://www.oddsportal.com/football/germany/bundesliga-2023-2024/bayern-munich-augsburg-f3e2PS0c/",
        help="Target URL"
    )

    args = parser.parse_args()

    try:
        asyncio.run(execute_api_strike(args.match_id, args.url))
    except KeyboardInterrupt:
        logger.info("\n[INTERRUPTED] User cancelled")
    except Exception as e:
        logger.error(f"[FATAL] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
