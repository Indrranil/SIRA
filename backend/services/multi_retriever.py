"""
multi_retriever.py
--------------------------------------------------------
Adaptive multi-provider retriever for SIRA.
Dynamically routes search queries across APIs
(SerpAPI → Bing → Tavily → Brave → DuckDuckGo → Offline Cache)
based on weight, quota, and health.
--------------------------------------------------------
"""

import random
import time
from typing import Any, Dict, List

from services.retriever import get_offline_results

# ────────────────────────────────────────────────────────
# PROVIDER CONFIGURATION
# ────────────────────────────────────────────────────────

SEARCH_PROVIDERS = {
    "serpapi": {"weight": 1.0, "quota": 100, "priority": 1, "healthy": True},
    "bing": {"weight": 0.9, "quota": 1000, "priority": 2, "healthy": True},
    "tavily": {"weight": 0.8, "quota": 500, "priority": 3, "healthy": True},
    "brave": {"weight": 0.7, "quota": 2000, "priority": 4, "healthy": True},
    "duckduckgo": {"weight": 0.5, "quota": None, "priority": 5, "healthy": True},
}

# ────────────────────────────────────────────────────────
# PLACEHOLDER FETCHER FUNCTIONS
# ────────────────────────────────────────────────────────
# (You’ll fill in real API calls later; they just return sample data for now.)


def serpapi_search(topic: str):
    raise NotImplementedError("SerpAPI integration not yet implemented.")


def bing_search(topic: str):
    raise NotImplementedError("Bing API integration not yet implemented.")


def tavily_search(topic: str):
    raise NotImplementedError("Tavily API integration not yet implemented.")


def brave_search(topic: str):
    raise NotImplementedError("Brave API integration not yet implemented.")


def ddg_search(topic: str):
    # DuckDuckGo fallback → use offline cache
    print(f"[INFO] Using DuckDuckGo/Offline fallback for '{topic}'")
    return get_offline_results(topic)


PROVIDER_FUNCTIONS = {
    "serpapi": serpapi_search,
    "bing": bing_search,
    "tavily": tavily_search,
    "brave": brave_search,
    "duckduckgo": ddg_search,
}

# ────────────────────────────────────────────────────────
# UTILITY HELPERS
# ────────────────────────────────────────────────────────


def normalize_results(
    results: List[Dict[str, Any]], provider: str
) -> List[Dict[str, Any]]:
    """Standardize field names and attach provider info."""
    normalized = []
    for r in results:
        normalized.append(
            {
                "title": r.get("title") or r.get("name") or "Untitled",
                "url": r.get("url") or r.get("link") or "",
                "snippet": r.get("snippet") or r.get("summary") or r.get("text") or "",
                "provider": provider,
            }
        )
    return deduplicate(normalized)


def deduplicate(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Remove duplicates by URL or title."""
    seen = set()
    unique = []
    for r in results:
        key = (r["url"], r["title"])
        if key not in seen:
            seen.add(key)
            unique.append(r)
    return unique


def record_success(provider: str):
    SEARCH_PROVIDERS[provider]["weight"] = min(
        1.0, SEARCH_PROVIDERS[provider]["weight"] + 0.05
    )
    SEARCH_PROVIDERS[provider]["healthy"] = True


def record_failure(provider: str):
    SEARCH_PROVIDERS[provider]["weight"] = max(
        0.1, SEARCH_PROVIDERS[provider]["weight"] - 0.1
    )
    SEARCH_PROVIDERS[provider]["healthy"] = False


def pick_provider() -> str:
    """Pick best available provider based on weight & quota."""
    available = [
        (name, meta["weight"])
        for name, meta in SEARCH_PROVIDERS.items()
        if meta["healthy"] and (meta["quota"] is None or meta["quota"] > 0)
    ]
    if not available:
        return "duckduckgo"
    return max(available, key=lambda x: x[1])[0]


# ────────────────────────────────────────────────────────
# MAIN FUNCTION
# ────────────────────────────────────────────────────────


def search_and_extract(topic: str) -> List[Dict[str, Any]]:
    """Unified search entrypoint."""
    provider = pick_provider()
    print(f"[INFO] Using provider: {provider} for '{topic}'")

    try:
        results = PROVIDER_FUNCTIONS[provider](topic)
        if not results:
            raise ValueError("Empty results from provider")
        record_success(provider)
        if SEARCH_PROVIDERS[provider]["quota"] is not None:
            SEARCH_PROVIDERS[provider]["quota"] -= 1
        return normalize_results(results, provider)
    except NotImplementedError:
        print(f"[WARN] {provider} not implemented. Trying next provider...")
        record_failure(provider)
        return search_and_extract(topic)
    except Exception as e:
        print(f"[WARN] {provider} failed: {e}")
        record_failure(provider)
        time.sleep(0.5)
        return search_and_extract(topic)
