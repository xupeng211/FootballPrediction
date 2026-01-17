"""
Offline HTML Parser Module - Local Price Extraction

This module provides production-grade HTML parsing functionality for extracting
odds data from locally stored HTML files. It is designed with unit-testability
in mind and follows SOLID principles.

Core Features:
    - Priority-based vendor matching (Pinnacle > 1xBet > bet365)
    - Robust price extraction using regex patterns
    - Zero network dependency (pure offline processing)
    - Type-safe interfaces with full annotations

Usage:
    from src.core.scrapers.offline_parser import LocalHtmlParser, VendorConfig

    parser = LocalHtmlParser()
    result = parser.parse_file("match_12345.html")
    if result:
        print(f"Source: {result.source}, Prices: {result.prices}")

Authors: V41.141 -> V41.153 Migration
Version: 1.0.0 (Production)
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import List, Optional, Union

from bs4 import BeautifulSoup, Tag


class VendorPriority(Enum):
    """Vendor priority levels for matching."""

    PINNACLE = 1
    ONE_X_BET = 2
    BET_365 = 3


@dataclass(frozen=True)
class VendorConfig:
    """Vendor configuration for price extraction.

    Attributes:
        pinnacle: Pinnacle vendor tag.
        one_x_bet: 1xBet vendor tag.
        bet_365: bet365 vendor tag.
    """

    pinnacle: str = "Pinnacle"
    one_x_bet: str = "1xBet"
    bet_365: str = "bet365"

    @property
    def priority_list(self) -> List[str]:
        """Get vendors in priority order (highest first)."""
        return [self.pinnacle, self.one_x_bet, self.bet_365]

    @classmethod
    def from_names(cls, vendors: List[str]) -> "VendorConfig":
        """Create config from vendor name list.

        Args:
            vendors: List of vendor names.

        Returns:
            VendorConfig instance.
        """
        return cls(
            pinnacle=vendors[0] if len(vendors) > 0 else "Pinnacle",
            one_x_bet=vendors[1] if len(vendors) > 1 else "1xBet",
            bet_365=vendors[2] if len(vendors) > 2 else "bet365",
        )


@dataclass
class PriceExtractionResult:
    """Result of price extraction from HTML.

    Attributes:
        source: Matched vendor name.
        prices: Extracted price values [home, draw, away].
        raw_text: Raw text content (truncated, for debugging).
        confidence: Extraction confidence score (0-1).
    """

    source: str
    prices: List[float]
    raw_text: str
    confidence: float = 1.0

    def to_dict(self) -> dict:
        """Convert to dictionary representation.

        Returns:
            Dictionary with extracted data.
        """
        return {
            "source": self.source,
            "prices": self.prices,
            "count": len(self.prices),
            "confidence": self.confidence,
        }

    @property
    def is_valid(self) -> bool:
        """Check if result contains valid odds data.

        Returns:
            True if prices list has exactly 3 values.
        """
        return len(self.prices) == 3


class LocalHtmlParser:
    """Local HTML parser for odds extraction.

    This parser uses a priority-based matching algorithm to extract odds data
    from HTML files. It searches for vendor names in the DOM and extracts
    price values using regex patterns.

    Attributes:
        config: Vendor configuration.
        debug: Enable debug logging.
        price_pattern: Regex for matching price values.
    """

    DEFAULT_PRICE_PATTERN = re.compile(r"\b\d+\.\d{2}\b")
    DEFAULT_SELECTORS = ["tr", "div", "td", "span", "li", "p"]

    def __init__(
        self,
        config: Optional[VendorConfig] = None,
        debug: bool = False,
        price_pattern: Optional[re.Pattern] = None,
        selectors: Optional[List[str]] = None,
    ):
        """Initialize the HTML parser.

        Args:
            config: Vendor configuration. Uses default if None.
            debug: Enable debug mode for verbose logging.
            price_pattern: Custom regex for price matching.
            selectors: DOM element selectors to search.
        """
        self.config = config or VendorConfig()
        self.debug = debug
        self.price_pattern = price_pattern or self.DEFAULT_PRICE_PATTERN
        self.selectors = selectors or self.DEFAULT_SELECTORS.copy()

    def parse_file(self, file_path: Union[str, Path]) -> Optional[PriceExtractionResult]:
        """Parse HTML file and extract odds data.

        Args:
            file_path: Path to HTML file.

        Returns:
            PriceExtractionResult if successful, None otherwise.

        Raises:
            FileNotFoundError: If file doesn't exist.
            IOError: If file cannot be read.
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        html_content = path.read_text(encoding="utf-8")
        return self.parse_string(html_content)

    def parse_string(self, html_string: str) -> Optional[PriceExtractionResult]:
        """Parse HTML string and extract odds data.

        Args:
            html_string: HTML content as string.

        Returns:
            PriceExtractionResult if successful, None otherwise.
        """
        soup = BeautifulSoup(html_string, "html.parser")
        return self._extract_by_priority(soup)

    def _extract_by_priority(self, soup: BeautifulSoup) -> Optional[PriceExtractionResult]:
        """Extract odds using priority-based vendor matching.

        Args:
            soup: BeautifulSoup parsed HTML object.

        Returns:
            PriceExtractionResult if found, None otherwise.
        """
        for vendor in self.config.priority_list:
            if self.debug:
                self._log_debug(f"Searching for vendor: {vendor}")

            for selector in self.selectors:
                elements = soup.find_all(selector)

                for element in elements:
                    element_text = self._get_element_text(element)

                    if len(element_text) < 5:
                        continue

                    if self._contains_vendor(element_text, vendor):
                        prices = self._extract_prices(element_text)

                        if prices and len(prices) >= 3:
                            if self.debug:
                                self._log_debug(
                                    f"Found match: {vendor}",
                                    prices=prices[:3],
                                )

                            return PriceExtractionResult(
                                source=vendor,
                                prices=prices[:3],
                                raw_text=element_text[:200],
                            )

        return None

    def _get_element_text(self, element: Tag) -> str:
        """Extract and normalize text from DOM element.

        Args:
            element: BeautifulSoup Tag object.

        Returns:
            Normalized text content.
        """
        text = element.get_text(separator=" ", strip=True)
        return " ".join(text.split())

    def _contains_vendor(self, text: str, vendor: str) -> bool:
        """Check if text contains vendor name (case-insensitive).

        Args:
            text: Text to search.
            vendor: Vendor name to find.

        Returns:
            True if vendor found in text.
        """
        return vendor.lower() in text.lower()

    def _extract_prices(self, text: str) -> List[float]:
        """Extract all price values from text.

        Args:
            text: Text containing price values.

        Returns:
            List of float price values.
        """
        matches = self.price_pattern.findall(text)
        return [float(price) for price in matches]

    def _log_debug(self, message: str, **kwargs) -> None:
        """Log debug message if debug mode enabled.

        Args:
            message: Log message.
            **kwargs: Additional context.
        """
        if self.debug:
            parts = [message]
            parts.extend([f"{k}={v}" for k, v in kwargs.items()])
            print(f"   [DEBUG] {' | '.join(parts)}")


class OfflineParserFactory:
    """Factory for creating parser instances with different configurations."""

    @staticmethod
    def create_default() -> LocalHtmlParser:
        """Create parser with default configuration.

        Returns:
            LocalHtmlParser instance.
        """
        return LocalHtmlParser()

    @staticmethod
    def create_custom(
        vendors: List[str],
        price_pattern: Optional[str] = None,
    ) -> LocalHtmlParser:
        """Create parser with custom configuration.

        Args:
            vendors: List of vendor names in priority order.
            price_pattern: Custom regex pattern for prices.

        Returns:
            LocalHtmlParser instance.
        """
        config = VendorConfig.from_names(vendors)
        pattern = re.compile(price_pattern) if price_pattern else None
        return LocalHtmlParser(config=config, price_pattern=pattern)

    @staticmethod
    def create_debug_mode() -> LocalHtmlParser:
        """Create parser with debug mode enabled.

        Returns:
            LocalHtmlParser instance with debug enabled.
        """
        return LocalHtmlParser(debug=True)


# Convenience exports
__all__ = [
    "LocalHtmlParser",
    "VendorConfig",
    "PriceExtractionResult",
    "VendorPriority",
    "OfflineParserFactory",
]
