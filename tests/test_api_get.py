"""
Test API endpoints for retrieving dives and certifications data.
"""

import pytest
import httpx
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
USER_ID = os.getenv("NAME_SURNAME", "Marco Berta").lower().replace(" ", "_")


@pytest.fixture
def client():
    """Create an httpx client for testing."""
    return httpx.Client(base_url=API_BASE_URL, timeout=30.0)


class TestDivesAPI:
    """Tests for the dives API endpoints."""

    def test_list_all_dives(self, client):
        """Test GET /dives - retrieve all dives for a user."""
        response = client.get("/dives", params={"user_id": USER_ID})

        print(f"\n[TEST] GET /dives?user_id={USER_ID}")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

        if len(data) > 0:
            # Verify dive structure
            dive = data[0]
            assert "user_id" in dive
            assert "dive_number" in dive
            assert "dive_date" in dive
            assert "location" in dive
            assert "max_depth" in dive
            assert "duration" in dive
            print(f"Found {len(data)} dives")
            for d in data:
                print(f"  - Dive #{d['dive_number']}: {d['location']} ({d['max_depth']}m, {d['duration']}min)")
        else:
            print("No dives found for user")

    def test_get_latest_dive(self, client):
        """Test GET /dives/latest - retrieve the most recent dive."""
        response = client.get("/dives/latest", params={"user_id": USER_ID})

        print(f"\n[TEST] GET /dives/latest?user_id={USER_ID}")
        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            dive = response.json()
            print(f"Latest dive: #{dive['dive_number']} at {dive['location']}")
            assert "user_id" in dive
            assert "dive_number" in dive
            assert dive["user_id"] == USER_ID
        elif response.status_code == 404:
            print("No dives found for user (404)")
            data = response.json()
            assert "error" in data
        else:
            pytest.fail(f"Unexpected status code: {response.status_code}")

    def test_get_dive_by_id(self, client):
        """Test GET /dives/{dive_id} - retrieve a specific dive."""
        # First, get list of dives to find a valid ID
        list_response = client.get("/dives", params={"user_id": USER_ID})

        if list_response.status_code == 200 and len(list_response.json()) > 0:
            dives = list_response.json()
            dive_id = dives[0]["_id"]

            response = client.get(f"/dives/{dive_id}")

            print(f"\n[TEST] GET /dives/{dive_id}")
            print(f"Status: {response.status_code}")

            assert response.status_code == 200
            dive = response.json()
            assert dive["_id"] == dive_id
            print(f"Retrieved dive: #{dive['dive_number']} at {dive['location']}")
        else:
            print("\n[TEST] GET /dives/{dive_id} - SKIPPED (no dives available)")
            pytest.skip("No dives available to test")


class TestCertificationsAPI:
    """Tests for the certifications API endpoints."""

    def test_list_all_certifications(self, client):
        """Test GET /certifications - retrieve all certifications for a user."""
        response = client.get("/certifications", params={"user_id": USER_ID})

        print(f"\n[TEST] GET /certifications?user_id={USER_ID}")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

        if len(data) > 0:
            # Verify certification structure
            cert = data[0]
            assert "user_id" in cert
            assert "name" in cert
            assert "agency" in cert
            assert "certification_date" in cert
            print(f"Found {len(data)} certifications")
            for c in data:
                print(f"  - {c['name']} ({c['agency']})")
        else:
            print("No certifications found for user")


class TestConfigAPI:
    """Tests for the config API endpoint."""

    def test_get_config(self, client):
        """Test GET /config - retrieve app configuration."""
        response = client.get("/config")

        print(f"\n[TEST] GET /config")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")

        assert response.status_code == 200
        data = response.json()
        assert "name_surname" in data
        assert "convex_url" in data
        print(f"Config: name_surname={data['name_surname']}, convex_url={data['convex_url']}")


class TestDirectConvexQuery:
    """Tests that query Convex directly to verify data exists."""

    def test_query_all_dives_in_convex(self):
        """Query Convex directly to see ALL dives (regardless of user_id)."""
        convex_url = os.getenv("CONVEX_URL")
        if not convex_url:
            pytest.skip("CONVEX_URL not set")

        print(f"\n[TEST] Direct Convex Query - All Dives")
        print(f"Convex URL: {convex_url}")

        # Query all dives without filtering by user_id
        # We'll use a simple query that gets all documents
        with httpx.Client(timeout=30.0) as client:
            # Try to get dives for different possible user_ids
            test_user_ids = [USER_ID, "default_user", "marco_berta", "Marco Berta"]

            for uid in test_user_ids:
                response = client.post(
                    f"{convex_url}/api/query",
                    json={
                        "path": "dives:getAllDives",
                        "args": {"user_id": uid},
                        "format": "json",
                    },
                )

                if response.status_code == 200:
                    data = response.json()
                    dives = data.get("value", [])
                    print(f"  user_id='{uid}': {len(dives)} dives found")
                    if dives:
                        for d in dives:
                            print(f"    - Dive #{d.get('dive_number')}: {d.get('location')} (user_id={d.get('user_id')})")

    def test_query_all_certifications_in_convex(self):
        """Query Convex directly to see ALL certifications."""
        convex_url = os.getenv("CONVEX_URL")
        if not convex_url:
            pytest.skip("CONVEX_URL not set")

        print(f"\n[TEST] Direct Convex Query - All Certifications")

        with httpx.Client(timeout=30.0) as client:
            test_user_ids = [USER_ID, "default_user", "marco_berta", "Marco Berta"]

            for uid in test_user_ids:
                response = client.post(
                    f"{convex_url}/api/query",
                    json={
                        "path": "certifications:getAllCertifications",
                        "args": {"user_id": uid},
                        "format": "json",
                    },
                )

                if response.status_code == 200:
                    data = response.json()
                    certs = data.get("value", [])
                    print(f"  user_id='{uid}': {len(certs)} certifications found")
                    if certs:
                        for c in certs:
                            print(f"    - {c.get('name')} ({c.get('agency')}) (user_id={c.get('user_id')})")


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "-s"])
