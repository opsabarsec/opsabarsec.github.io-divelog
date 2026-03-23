# app/services/geolocation.py
from __future__ import annotations

import os
import time
import asyncio
import warnings
from typing import Optional, List, Dict, Tuple

import aiohttp

__all__ = [
    "get_coordinates_async",
    "get_osm_link_async",
    "build_osm_link",
]

# ---------------------------
# Configuration
# ---------------------------

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
DEFAULT_ZOOM = 16
REQUEST_TIMEOUT_SECONDS = 20
CACHE_TTL_SECONDS = int(os.getenv("GEOLOCATION_CACHE_TTL_SECONDS", "86400"))  # 24h default
MIN_INTERVAL_SECONDS = float(os.getenv("GEOLOCATION_MIN_INTERVAL_SECONDS", "1.0"))  # polite: 1 r/s

APP_NAME = os.getenv("APP_NAME", "DiveLog")
APP_VERSION = os.getenv("APP_VERSION", "1.0")
CONTACT_EMAIL = os.getenv("MY_EMAIL")  # optional but recommended


# ---------------------------
# Rate limiter (1 req / second)
# ---------------------------


class _RateLimiter:
    """
    Simple async rate limiter that guarantees a minimum interval between calls.
    Shared across all function calls in this module.
    """

    def __init__(self, min_interval: float) -> None:
        self._min_interval = max(0.0, min_interval)
        self._lock = asyncio.Lock()
        self._last_ts = 0.0

    async def wait(self) -> None:
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_ts
            if elapsed < self._min_interval:
                await asyncio.sleep(self._min_interval - elapsed)
            self._last_ts = time.monotonic()


_rate_limiter = _RateLimiter(MIN_INTERVAL_SECONDS)


# ---------------------------
# Cache (in-memory TTL)
# ---------------------------

# key: normalized location_name -> (stored_at_epoch, (lon, lat))
_cache: Dict[str, Tuple[float, Tuple[float, float]]] = {}


def _normalize_location(name: str) -> str:
    return " ".join(name.strip().split()).lower()


def _from_cache(key: str, ttl: int) -> Optional[List[float]]:
    if ttl <= 0:
        return None
    item = _cache.get(key)
    if not item:
        return None
    stored_at, (lon, lat) = item
    if (time.time() - stored_at) <= ttl:
        return [lon, lat]
    # stale
    _cache.pop(key, None)
    return None


def _to_cache(key: str, lon: float, lat: float) -> None:
    _cache[key] = (time.time(), (lon, lat))


# ---------------------------
# Headers / User-Agent
# ---------------------------


def _build_user_agent(app_name: str = APP_NAME, app_version: str = APP_VERSION) -> str:
    """
    Build a standards-compliant User-Agent for Nominatim.
    Nominatim requires a descriptive UA and a way to contact the developer.
    """
    if CONTACT_EMAIL:
        return f"{app_name}/{app_version} (contact: {CONTACT_EMAIL})"
    warnings.warn(
        "Environment variable MY_EMAIL not set. Using fallback User-Agent. "
        "Set MY_EMAIL to comply with Nominatim usage policy and avoid blocking."
    )
    return f"{app_name}/{app_version} (contact: unspecified)"


# ---------------------------
# Public helpers
# ---------------------------


def build_osm_link(lat: float, lon: float, zoom: int = DEFAULT_ZOOM) -> str:
    """
    Build a browsable OpenStreetMap link centered at (lat, lon).
    """
    return f"https://www.openstreetmap.org/?mlat={lat}&mlon={lon}#map={zoom}/{lat}/{lon}"


async def get_coordinates_async(
    location_name: str,
    *,
    use_cache: bool = True,
    ttl_seconds: int = CACHE_TTL_SECONDS,
) -> Optional[List[float]]:
    """
    Resolve a human-readable location name to [longitude, latitude] using Nominatim.

    Args:
        location_name: e.g., "Portofino, Italy"
        use_cache: use in-memory cache to avoid repeated requests
        ttl_seconds: cache TTL in seconds (default 24h)

    Returns:
        [lon, lat] if found, else None.

    Raises:
        ValueError: if location_name is empty or not a string
        aiohttp.ClientError / asyncio.TimeoutError for network-level errors (not raised if caught below)
    """
    if not isinstance(location_name, str) or not location_name.strip():
        raise ValueError("location_name must be a non-empty string.")

    key = _normalize_location(location_name)
    if use_cache:
        cached = _from_cache(key, ttl_seconds)
        if cached is not None:
            return cached

    headers = {"User-Agent": _build_user_agent()}
    params = {
        "q": location_name,
        "format": "json",
        "limit": 1,
    }
    # Optionally include email param as recommended by Nominatim (redundant but acceptable)
    if CONTACT_EMAIL:
        params["email"] = CONTACT_EMAIL

    # Politeness delay
    await _rate_limiter.wait()

    timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT_SECONDS)
    try:
        async with aiohttp.ClientSession(headers=headers, timeout=timeout) as session:
            async with session.get(NOMINATIM_URL, params=params) as resp:
                resp.raise_for_status()
                data = await resp.json()
    except Exception:
        # Network errors or non-JSON responses: return None (do not crash caller)
        return None

    if not data:
        return None

    try:
        lon = float(data[0]["lon"])
        lat = float(data[0]["lat"])
    except (KeyError, ValueError, TypeError, IndexError):
        return None

    if use_cache:
        _to_cache(key, lon, lat)

    return [lon, lat]


async def get_osm_link_async(location_name: str, zoom: int = DEFAULT_ZOOM) -> Optional[str]:
    """
    Convenience wrapper: geocode a location then build its OSM link.
    Returns None if geocoding fails.
    """
    coords = await get_coordinates_async(location_name)
    if not coords:
        return None
    lon, lat = coords
    return build_osm_link(lat, lon, zoom)
