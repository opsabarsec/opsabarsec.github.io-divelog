# tests/test_resolve_dive_metadata.py

from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from api.main import app
from dotenv import load_dotenv
from pathlib import Path
import os

# Load .env file
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

if "CONVEX_URL" not in os.environ:
    os.environ["CONVEX_URL"] = "https://test.convex.cloud"
client = TestClient(app)


def test_resolve_dive_metadata_happy_path() -> None:
    payload = {"location_name": "Lady Elliot Island", "club_name": "Portofino Divers"}

    with (
        patch("app.main.get_coordinates_async", new_callable=AsyncMock) as mock_geo,
        patch("app.main.search_club_website") as mock_club,
    ):
        # Mock geolocation returns [lon, lat]
        mock_geo.return_value = [152.715, -24.112]
        mock_club.return_value = {"success": True, "club_website": "https://portofinodivers.com"}

        resp = client.post("/resolve-dive-metadata", json=payload)
        assert resp.status_code == 200

        body = resp.json()
        assert body["location_name"] == "Lady Elliot Island"
        assert body["coordinates"] == {"latitude": -24.112, "longitude": 152.715}
        assert body["osm_link"].startswith(
            "https://www.openstreetmap.org/?mlat=-24.112&mlon=152.715#map=16/"
        )
        assert body["club_name"] == "Portofino Divers"
        assert body["club_website"] == "https://portofinodivers.com"


def test_resolve_dive_metadata_partial_failure() -> None:
    payload = {"location_name": "Unknown Place", "club_name": "Unknown Club"}

    with (
        patch("app.main.get_coordinates_async", new_callable=AsyncMock) as mock_geo,
        patch("app.main.search_club_website") as mock_club,
    ):
        # Both lookups fail
        mock_geo.return_value = None
        mock_club.return_value = {"success": False, "error": "No results"}

        resp = client.post("/resolve-dive-metadata", json=payload)
        assert resp.status_code == 200

        body = resp.json()
        assert body["coordinates"] is None
        assert body["osm_link"] is None
        assert body["club_website"] is None
