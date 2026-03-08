#!/usr/bin/env python3
"""
Search for diving club websites using DuckDuckGo HTML scraping.
Usage: python search_club.py "Marseille Dive Club"
"""

import argparse
import re
import sys
from urllib.parse import unquote, urlparse
from typing import Dict, Any

import httpx

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
)


def search_club_website(query: str) -> Dict[str, Any]:
    """
    Search DuckDuckGo for club website, return first result URL.

    Args:
        query: Search query (e.g. "Marseille Dive Club")

    Returns:
        Dict with 'url', 'query', 'success' or 'error'
    """
    if not query or not query.strip():
        return {
            "error": "Query parameter 'q' is required",
            "query": "",
            "success": False,
        }

    try:
        # Build DuckDuckGo HTML search URL
        search_url = f"https://html.duckduckgo.com/html/?q={query}"

        # Fetch HTML
        with httpx.Client(timeout=10.0) as client:
            response = client.get(
                search_url,
                headers={"User-Agent": USER_AGENT},
            )
            response.raise_for_status()

        html = response.text

        # Pattern 1: Main result link <a class="result__a" href="...">
        result_match = re.search(r'<a[^>]*class="result__a"[^>]*href="([^"]+)"', html)

        if result_match:
            url = result_match.group(1)

            # Extract from DuckDuckGo redirect (uddg= parameter)
            uddg_match = re.search(r"uddg=([^&]+)", url)
            if uddg_match:
                url = unquote(uddg_match.group(1))

            # Ensure proper protocol
            if url.startswith("//"):
                url = "https:" + url

            # Validate URL
            parsed = urlparse(url)
            if parsed.scheme in ("http", "https") and parsed.netloc:
                return {
                    "url": url,
                    "query": query,
                    "success": True,
                }

        # Pattern 2: Fallback - result URL in text
        alt_match = re.search(r'class="result__url"[^>]*>([^<]+)<', html)
        if alt_match:
            url = alt_match.group(1).strip()
            if not url.startswith("http"):
                url = "https://" + url

            parsed = urlparse(url)
            if parsed.scheme in ("http", "https") and parsed.netloc:
                return {
                    "url": url,
                    "query": query,
                    "success": True,
                }

        return {
            "error": "No results found",
            "query": query,
            "success": False,
        }

    except httpx.HTTPStatusError as e:
        return {
            "error": f"DuckDuckGo returned status {e.response.status_code}",
            "query": query,
            "success": False,
        }
    except Exception as e:
        return {
            "error": f"Failed to search DuckDuckGo: {str(e)}",
            "query": query,
            "success": False,
        }


def main() -> None:
    parser = argparse.ArgumentParser(description="Search for diving club websites using DuckDuckGo")
    parser.add_argument("query", nargs="?", help="Club name to search for")
    parser.add_argument(
        "--json", action="store_true", help="Output as JSON (default: human readable)"
    )
    args = parser.parse_args()

    if not args.query:
        query = input("Enter club name to search: ").strip()
    else:
        query = args.query

    if not query:
        print("Error: Query required", file=sys.stderr)
        sys.exit(1)

    result = search_club_website(query)

    if args.json:
        import json

        print(json.dumps(result, indent=2))
    else:
        if result["success"]:
            print(f"✅ Found: {result['url']}")
        else:
            print(f"❌ {result['error']}")


if __name__ == "__main__":
    main()
