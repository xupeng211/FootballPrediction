"""User-Agent 随机化模块 - 反爬对抗组件
User-Agent Randomization Module - Anti-Scraping Component.

提供智能的User-Agent轮换和管理功能，避免指纹识别。
"""

import random
from dataclasses import dataclass
from src.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class UserAgentProfile:
    """User-Agent配置档案."""

    user_agent: str
    weight: float = 1.0  # 使用权重
    platform: str = "windows"  # windows, macos, linux, mobile
    browser: str = "chrome"  # chrome, firefox, safari, edge

    def __post_init__(self):
        """初始化后处理."""
        if not self.user_agent:
            raise ValueError("User-Agent不能为空")


class UserAgentManager:
    """User-Agent管理器."""

    def __init__(self):
        self.profiles: list[UserAgentProfile] = []
        self._initialize_profiles()
        logger.info(f"User-Agent管理器初始化完成，共{len(self.profiles)}个档案")

    def _initialize_profiles(self):
        """初始化User-Agent档案."""

        # Chrome User-Agents (Windows)
        chrome_windows = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36"
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36"
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36"
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
        ]

        # Firefox User-Agents (Windows)
        firefox_windows = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0"
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/118.0"
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/117.0"
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/116.0"
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0"
        ]

        # Edge User-Agents (Windows)
        edge_windows = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0"
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36 Edg/118.0.2088.76"
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36 Edg/117.0.2045.60"
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36 Edg/116.0.1938.81"
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36 Edg/115.0.1901.203"
        ]

        # Safari User-Agents (macOS)
        safari_macos = [
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15"
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Safari/605.1.15"
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.4 Safari/605.1.15"
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.3 Safari/605.1.15"
        ]

        # Chrome User-Agents (macOS)
        chrome_macos = [
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36"
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36"
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36"
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
        ]

        # Mobile User-Agents (Android)
        mobile_android = [
            "Mozilla/5.0 (Linux; Android 13; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Mobile Safari/537.36"
            "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Mobile Safari/537.36"
            "Mozilla/5.0 (Linux; Android 12; SM-S906N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Mobile Safari/537.36"
            "Mozilla/5.0 (Linux; Android 12; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Mobile Safari/537.36"
            "Mozilla/5.0 (Linux; Android 11; SM-A515F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Mobile Safari/537.36"
        ]

        # Mobile User-Agents (iOS)
        mobile_ios = [
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
            "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1"
            "Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1"
            "Mozilla/5.0 (iPad; CPU OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
            "Mozilla/5.0 (iPhone; CPU iPhone OS 16_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.4 Mobile/15E148 Safari/604.1"
        ]

        # 添加所有档案，设置不同的权重
        # 桌面浏览器权重更高（更常见）
        for ua in chrome_windows:
            self.profiles.append(
                UserAgentProfile(ua, weight=2.5, platform="windows", browser="chrome")
            )

        for ua in firefox_windows:
            self.profiles.append(
                UserAgentProfile(ua, weight=1.5, platform="windows", browser="firefox")
            )

        for ua in edge_windows:
            self.profiles.append(
                UserAgentProfile(ua, weight=1.8, platform="windows", browser="edge")
            )

        for ua in chrome_macos:
            self.profiles.append(
                UserAgentProfile(ua, weight=2.0, platform="macos", browser="chrome")
            )

        for ua in safari_macos:
            self.profiles.append(
                UserAgentProfile(ua, weight=1.6, platform="macos", browser="safari")
            )

        # 移动端权重较低（避免在非移动场景使用）
        for ua in mobile_android:
            self.profiles.append(
                UserAgentProfile(ua, weight=0.8, platform="android", browser="chrome")
            )

        for ua in mobile_ios:
            self.profiles.append(
                UserAgentProfile(ua, weight=0.7, platform="ios", browser="safari")
            )

    def get_random_user_agent(self, platform: str = None, browser: str = None) -> str:
        """获取随机User-Agent."""
        filtered_profiles = self.profiles

        # 按平台过滤
        if platform:
            filtered_profiles = [p for p in filtered_profiles if p.platform == platform]

        # 按浏览器过滤
        if browser:
            filtered_profiles = [p for p in filtered_profiles if p.browser == browser]

        if not filtered_profiles:
            logger.warning(
                f"没有找到匹配的User-Agent档案 (platform={platform}, browser={browser})"
            )
            # 回退到所有档案
            filtered_profiles = self.profiles

        # 根据权重选择
        weights = [p.weight for p in filtered_profiles]
        selected_profile = random.choices(filtered_profiles, weights=weights, k=1)[0]

        return selected_profile.user_agent

    def get_user_agent_by_category(self, category: str) -> str:
        """根据类别获取User-Agent."""
        category_mapping = {
            "windows_chrome": ("windows", "chrome")
            "windows_firefox": ("windows", "firefox")
            "windows_edge": ("windows", "edge")
            "macos_chrome": ("macos", "chrome")
            "macos_safari": ("macos", "safari")
            "mobile_android": ("android", "chrome")
            "mobile_ios": ("ios", "safari")
        }

        if category in category_mapping:
            platform, browser = category_mapping[category]
            return self.get_random_user_agent(platform=platform, browser=browser)
        else:
            logger.warning(f"未知的User-Agent类别: {category}")
            return self.get_random_user_agent()

    def get_realistic_headers(self, user_agent: str = None) -> dict[str, str]:
        """获取逼真的请求头."""
        if not user_agent:
            user_agent = self.get_random_user_agent()

        # 基础请求头 - 移除反爬触发字段
        headers = {
            "User-Agent": user_agent
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
            "Accept-Language": "en-US,en;q=0.9",  # 改为英文，避免中文标识
            "Accept-Encoding": "gzip, deflate, br"
            "Connection": "keep-alive"
            "Upgrade-Insecure-Requests": "1"
        }

        # 根据User-Agent调整请求头
        if "Chrome" in user_agent:
            headers.update(
                {
                    "sec-ch-ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"'
                    "sec-ch-ua-mobile": "?0"
                    "sec-ch-ua-platform": '"macOS"',  # 改为macOS
                    "Sec-Fetch-Dest": "document"
                    "Sec-Fetch-Mode": "navigate"
                    "Sec-Fetch-Site": "none"
                    "Sec-Fetch-User": "?1"
                }
            )
        elif "Firefox" in user_agent:
            headers.update(
                {
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
                }
            )
        elif "Safari" in user_agent and "Chrome" not in user_agent:
            headers.update(
                {
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
                }
            )

        # 移动端调整
        if "Mobile" in user_agent or "Android" in user_agent:
            headers.update(
                {
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
                    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"
                    "sec-ch-ua-mobile": "?1"
                }
            )

        return headers

    def get_stats(self) -> dict:
        """获取User-Agent统计信息."""
        stats = {
            "total_profiles": len(self.profiles)
            "platforms": {}
            "browsers": {}
        }

        for profile in self.profiles:
            # 平台统计
            if profile.platform not in stats["platforms"]:
                stats["platforms"][profile.platform] = 0
            stats["platforms"][profile.platform] += 1

            # 浏览器统计
            if profile.browser not in stats["browsers"]:
                stats["browsers"][profile.browser] = 0
            stats["browsers"][profile.browser] += 1

        return stats


# 全局User-Agent管理器实例
_ua_manager: UserAgentManager = None


def get_user_agent_manager() -> UserAgentManager:
    """获取全局User-Agent管理器实例."""
    global _ua_manager
    if _ua_manager is None:
        _ua_manager = UserAgentManager()
    return _ua_manager


def get_random_user_agent(platform: str = None, browser: str = None) -> str:
    """获取随机User-Agent的便捷函数."""
    return get_user_agent_manager().get_random_user_agent(platform, browser)


def get_realistic_headers(user_agent: str = None) -> dict[str, str]:
    """获取逼真请求头的便捷函数."""
    return get_user_agent_manager().get_realistic_headers(user_agent)
