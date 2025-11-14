import json
import os
import random
import time
from typing import Dict, List

import httpx
import trafilatura
from duckduckgo_search import DDGS

DATA_PATH = os.path.join(os.path.dirname(__file__), "../data/offline_cache.json")


async def fetch_text(url: str) -> str:
    """Download and extract clean text from a webpage."""
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.get(
                url, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0"}
            )
            r.raise_for_status()
            return (
                trafilatura.extract(
                    r.text, include_comments=False, include_tables=False
                )
                or ""
            )
    except Exception:
        return ""


def _load_offline_cache():
    if not os.path.exists(DATA_PATH):
        return []
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            print("[WARN] Cache file was empty or invalid, resetting.")
            return []


def _save_to_cache(topic: str, new_entries: list):
    """Append new live search results to the offline cache, avoiding duplicates."""
    cache = _load_offline_cache()
    existing_urls = {c["url"] for c in cache}

    added = 0
    for entry in new_entries:
        if entry["url"] not in existing_urls:
            cache.append(
                {
                    "topic": topic,
                    "title": entry["title"],
                    "url": entry["url"],
                    "text": entry["text"],
                }
            )
            added += 1

    if added > 0:
        with open(DATA_PATH, "w", encoding="utf-8") as f:
            json.dump(cache, f, indent=2, ensure_ascii=False)
        print(f"[CACHE] Added {added} new article(s) for '{topic}' to offline cache.")
    else:
        print(f"[CACHE] No new articles to add for '{topic}'.")


def search_and_extract(topic: str, max_results: int = 3, retries: int = 3):
    """Hybrid retriever: tries live search, falls back to offline cache."""
    for attempt in range(retries):
        try:
            ddg = DDGS()
            results = []
            for r in ddg.text(topic, max_results=max_results):
                url = r.get("href") or r.get("url")
                if not url:
                    continue
                downloaded = trafilatura.fetch_url(url)
                if downloaded:
                    content = trafilatura.extract(
                        downloaded, include_comments=False, include_tables=False
                    )
                    if content and len(content.split()) > 100:
                        results.append(
                            {
                                "title": r.get("title", "Untitled"),
                                "url": url,
                                "text": content,
                            }
                        )
            if results:
                print(f"[INFO] Retrieved {len(results)} live results for '{topic}'.")
                _save_to_cache(topic, results)  # 🧠 auto-cache live results
                return results
        except Exception as e:
            print(
                f"[WARN] DuckDuckGo search failed (attempt {attempt + 1}/{retries}): {e}"
            )
            time.sleep(5 + random.randint(1, 3))

    # 🔁 Offline Fallback
    print(f"[OFFLINE] Falling back to offline cache for '{topic}'.")
    cache = _load_offline_cache()
    cached_results = [c for c in cache if topic.lower() in c["topic"].lower()]
    return cached_results


def get_offline_results(topic: str):
    """Return offline cached results for a given topic."""
    cache = _load_offline_cache()
    topic_lower = topic.lower().strip()

    # Match all cached entries whose topic contains this keyword
    matches = [c for c in cache if topic_lower in c.get("topic", "").lower()]

    if matches:
        print(f"[OFFLINE] Returning {len(matches)} cached results for '{topic}'.")
        return matches
    else:
        print(f"[OFFLINE] No cached results found for '{topic}'.")
        return []
