#!/usr/bin/env python3
"""
NowGoal 身份伪装Cookie生成器 - Identity Masquerade Cookie Generator
通过有头浏览器模拟真实用户行为，获取NowGoal信任的Cookie
解决"诱饵赔率"(10.0/11.0/13.0)问题

Usage:
    python scripts/generate_nowgoal_cookie.py

Requirements:
    - 必须在GUI环境运行: Windows桌面 或 WSL2+WSLg 或 X11转发
    - 有头模式(headless=False)通过指纹检测
    - 代理配置确保IP一致性
"""

import asyncio
import random
import time
import os
from pathlib import Path
from playwright.async_api import async_playwright

# 项目路径配置
project_root = Path(__file__).parent.parent
data_dir = project_root / "data"
cookie_file = data_dir / "nowgoal_auth.json"

# 确保数据目录存在
data_dir.mkdir(exist_ok=True)


class NowGoalIdentityMasquerade:
    """NowGoal 身份伪装生成器"""

    def __init__(self):
        self.browser = None
        self.context = None
        self.page = None

        # 代理配置 - 保持IP一致性
        self.proxy_config = {
            "server": "http://172.25.16.1:7890"
        }

    async def start_browser(self):
        """启动有头浏览器 - 关键配置通过指纹检测"""
        print("🚀 启动有头浏览器进行身份伪装...")

        try:
            playwright = await async_playwright().start()

            # 关键配置：有头模式 + 去自动化特征 + 代理
            self.browser = await playwright.chromium.launch(
                headless=False,  # 🔑 必须有头模式通过指纹检测
                proxy=self.proxy_config,
                args=[
                    '--disable-blink-features=AutomationControlled',  # 🔑 去自动化特征
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-web-security',
                    '--disable-features=VizDisplayCompositor',
                    '--disable-extensions',
                    '--no-first-run',
                    '--disable-default-apps',
                    '--disable-infobars',
                    '--disable-background-timer-throttling',
                    '--disable-renderer-backgrounding',
                    '--disable-backgrounding-occluded-windows',
                    '--ignore-certificate-errors',
                    '--ignore-ssl-errors',
                    '--ignore-certificate-errors-spki-list'
                ]
            )

            # 创建具有真实指纹的浏览器上下文
            self.context = await self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                locale='en-US',
                timezone_id='America/New_York',
                geolocation={'latitude': 40.7128, 'longitude': -74.0060},  # 纽约位置
                permissions=['geolocation'],
                proxy=self.proxy_config,
                # 真实浏览器指纹
                extra_http_headers={
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Cache-Control': 'no-cache',
                    'Pragma': 'no-cache'
                }
            )

            self.page = await self.context.new_page()
            print("✅ 有头浏览器启动成功 - 身份伪装模式")

        except Exception as e:
            print(f"❌ 浏览器启动失败: {str(e)}")
            raise

    async def simulate_human_behavior(self):
        """模拟真实用户行为 - 45秒深度交互建立信任"""
        print("👤 开始真实用户行为模拟 (45秒深度交互)...")

        try:
            # 第一步：访问主页
            print("🌐 访问 NowGoal 主页...")
            await self.page.goto("https://www.nowgoal.com/", wait_until="networkidle")

            # 初始等待 - 让页面完全加载
            await asyncio.sleep(random.uniform(3, 5))

            # 第二步：人类化鼠标行为
            print("🖱️ 模拟真实鼠标行为...")
            await self._simulate_mouse_movement()

            # 第三步：人类化页面交互
            print("📜 模拟真实页面浏览...")
            await self._simulate_page_interaction()

            # 第四步：建立网站信任 - 点击元素
            print("🎯 建立网站信任度...")
            await self._establish_trust()

            # 第五步：最终停留确保JS执行和指纹上报
            print("⏱️ 最终停留确保信任建立...")
            await asyncio.sleep(random.uniform(10, 15))

            print("✅ 身份伪装完成 - 信任Cookie已建立")

        except Exception as e:
            print(f"❌ 用户行为模拟失败: {str(e)}")
            raise

    async def _simulate_mouse_movement(self):
        """模拟真实鼠标移动轨迹"""
        # 随机鼠标移动 - 模拟人类不精确性
        movements = [
            (random.randint(100, 300), random.randint(100, 300)),
            (random.randint(400, 800), random.randint(200, 500)),
            (random.randint(200, 600), random.randint(400, 700)),
            (random.randint(500, 900), random.randint(100, 400))
        ]

        for x, y in movements:
            await self.page.mouse.move(x, y)
            await asyncio.sleep(random.uniform(0.2, 0.8))

        # 模拟点击页面空白处
        await self.page.mouse.click(random.randint(300, 700), random.randint(200, 500))
        await asyncio.sleep(random.uniform(1, 2))

    async def _simulate_page_interaction(self):
        """模拟真实页面浏览行为"""
        # 随机滚动 - 模拟用户浏览习惯
        scroll_actions = [
            (0, random.randint(300, 600)),
            (0, random.randint(200, 400)),
            (0, -random.randint(100, 300))
        ]

        for delta_x, delta_y in scroll_actions:
            await self.page.mouse.wheel(delta_x, delta_y)
            await asyncio.sleep(random.uniform(0.5, 1.5))

        # 短暂停顿 - 模拟阅读时间
        await asyncio.sleep(random.uniform(2, 4))

        # 再次滚动
        await self.page.mouse.wheel(0, random.randint(100, 250))
        await asyncio.sleep(random.uniform(1, 3))

    async def _establish_trust(self):
        """建立网站信任度 - 点击页面元素"""
        try:
            # 等待页面元素加载
            await self.page.wait_for_timeout(2000)

            # 尝试点击多种元素以建立信任
            click_attempts = [
                'a[href*="football"]',  # 足球相关链接
                'div.match-item',       # 比赛项
                'span.team-name',       # 队伍名称
                '.nav-item',           # 导航项
                'button',              # 按钮
                'a[href*="/match/"]'   # 比赛详情链接
            ]

            for selector in click_attempts:
                try:
                    elements = await self.page.query_selector_all(selector)
                    if elements:
                        # 随机选择一个元素点击
                        element = random.choice(elements[:3])  # 只选择前3个避免太深
                        await element.scroll_into_view_if_needed()
                        await asyncio.sleep(1)
                        await element.click()
                        await asyncio.sleep(random.uniform(2, 4))

                        # 可能跳转到新页面，返回主页
                        if self.page.url != "https://www.nowgoal.com/":
                            await self.page.goto("https://www.nowgoal.com/", wait_until="networkidle")
                            await asyncio.sleep(2)
                        break
                except:
                    continue

            # 如果没有找到可点击元素，在页面随机位置点击
            else:
                print("⚠️ 未找到特定元素，执行通用点击...")
                await self.page.mouse.click(
                    random.randint(200, 800),
                    random.randint(200, 600)
                )
                await asyncio.sleep(random.uniform(2, 4))

        except Exception as e:
            print(f"⚠️ 信任建立过程中的非致命错误: {str(e)}")
            # 继续执行，不中断流程

    async def save_identity_state(self):
        """保存身份伪装状态 - Cookie + Storage"""
        print("💾 保存身份伪装状态...")

        try:
            # 保存完整的状态 (cookies, localStorage, sessionStorage)
            await self.context.storage_state(path=str(cookie_file))

            print(f"✅ 身份状态已保存到: {cookie_file}")

            # 验证保存的文件
            if cookie_file.exists():
                file_size = cookie_file.stat().st_size
                print(f"📊 文件大小: {file_size} bytes")

                # 读取并统计Cookie数量
                import json
                with open(cookie_file, 'r', encoding='utf-8') as f:
                    state_data = json.load(f)

                cookies_count = len(state_data.get('cookies', []))
                print(f"🍪 保存Cookie数量: {cookies_count}")

                # 显示重要Cookie
                important_cookies = []
                for cookie in state_data.get('cookies', []):
                    name = cookie.get('name', '').lower()
                    if any(key in name for key in ['session', 'token', 'auth', 'user', 'id']):
                        important_cookies.append(cookie.get('name'))

                if important_cookies:
                    print(f"🎯 发现重要Cookie: {', '.join(important_cookies)}")
                else:
                    print("⚠️ 未发现明显的重要Cookie，但状态已完整保存")

            else:
                raise Exception("Cookie文件保存失败")

        except Exception as e:
            print(f"❌ 保存身份状态失败: {str(e)}")
            raise

    async def close_browser(self):
        """关闭浏览器"""
        if self.browser:
            await self.browser.close()
            print("🧹 身份伪装浏览器已关闭")

    async def generate_identity(self):
        """执行完整的身份伪装流程"""
        print("🎭 NowGoal 身份伪装Cookie生成器")
        print("=" * 60)
        print("🎯 目标: 获取真实用户Cookie，解决10.0/11.0/13.0假赔率")
        print("🔧 技术: 有头浏览器 + 行为模拟 + 指纹伪装")
        print("=" * 60)

        try:
            # 启动有头浏览器
            await self.start_browser()

            # 模拟真实用户行为 (45秒深度交互)
            await self.simulate_human_behavior()

            # 保存身份状态
            await self.save_identity_state()

            print("\n🎉 身份伪装Cookie生成成功！")
            print(f"📁 保存位置: {cookie_file}")
            print("✅ 现在可以运行赔率采集获取真实数据:")
            print("   python scripts/collect_odds_data.py --limit 1")

            return True

        except Exception as e:
            print(f"\n❌ 身份伪装失败: {str(e)}")
            return False

        finally:
            # 确保关闭浏览器
            await self.close_browser()


def check_environment():
    """检查运行环境"""
    print("🔍 检查运行环境...")

    # 检查显示环境
    display = os.environ.get('DISPLAY')
    if display:
        print(f"✅ 检测到显示环境: {display}")
    elif os.name == 'nt':  # Windows
        print("✅ Windows环境 - 支持GUI")
    else:
        print("⚠️ 未检测到显示环境")
        print("💡 在WSL中，请确保已配置WSLg或X11转发:")
        print("   - WSLg: 自动支持 (推荐)")
        print("   - X11: export DISPLAY=:0")

    # 检查Playwright安装
    try:
        from playwright.async_api import async_playwright
        print("✅ Playwright已安装")
    except ImportError:
        print("❌ Playwright未安装，请运行: pip install playwright")
        return False

    return True


def main():
    """主函数"""
    print("🍪 NowGoal 身份伪装Cookie生成器")
    print("=" * 50)

    # 环境检查
    if not check_environment():
        print("\n❌ 环境检查失败，请先解决上述问题")
        return

    print("\n⚠️ 重要提示:")
    print("   🖥️  将打开真实浏览器窗口，请不要关闭")
    print("   ⏱️  脚本将自动运行约45秒")
    print("   🎭 会模拟真实用户浏览行为")
    print("   📍 需要GUI环境: Windows/WSLg/X11转发")
    print("=" * 50)

    # 用户确认
    try:
        user_input = input("\n❓ 确认执行身份伪装生成? (y/N): ").strip().lower()
        if user_input not in ['y', 'yes']:
            print("❌ 用户取消操作")
            return
    except KeyboardInterrupt:
        print("\n❌ 用户中断操作")
        return

    # 执行身份伪装
    try:
        masquerade = NowGoalIdentityMasquerade()
        success = asyncio.run(masquerade.generate_identity())

        if success:
            print("\n🚀 下一步操作:")
            print("1. 验证Cookie效果:")
            print("   python scripts/collect_odds_data.py --limit 1")
            print("2. 检查赔率是否不再是10.0/11.0/13.0")
            print("3. 如果成功，可以进行批量采集")
        else:
            print("\n❌ 身份伪装失败")
            print("💡 请检查:")
            print("   - 网络连接是否正常")
            print("   - 代理172.25.16.1:7890是否可用")
            print("   - 显示环境是否正常")

    except KeyboardInterrupt:
        print("\n❌ 用户中断操作")
    except Exception as e:
        print(f"\n❌ 执行失败: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()