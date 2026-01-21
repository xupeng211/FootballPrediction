"""
V41.350 Scrapers Module
=======================

Browser management and scraping infrastructure for FootballPrediction.

Core components:
- BrowserManager: V41.291 Browser Singleton (memory-optimized)
- Anti-modal injection and cookie handling
"""

from .browser_manager import BrowserContextManager, BrowserManager

__all__ = ["BrowserContextManager", "BrowserManager"]
