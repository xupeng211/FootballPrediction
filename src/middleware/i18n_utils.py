from typing import Any, Dict, List, Optional, Union

"""
i18n utilities
"""

from fastapi import Request


def get_language_from_request(request: Request) -> str:
    """Get language from request headers"""
    # Try to get language from Accept-Language header
    accept_language = request.headers.get("accept-language", "")
    if accept_language:
        # Parse the first language
        language = accept_language.split(",")[0].split("-")[0]
        return language.lower()

    # Fallback to query parameter
    lang = request.query_params.get("lang")
    if lang:
        return lang.lower()

    # Default to english
    return "en"
