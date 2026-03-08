import os
import time
from typing import Dict, Any
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock
from app.main import app

from dotenv import load_dotenv

# Load .env file
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

if "CONVEX_URL" not in os.environ:
    os.environ["CONVEX_URL"] = "https://test.convex.cloud"

client = TestClient(app)


@pytest.fixture
def mock_convex_response() -> Dict[str, Any]:
    return {"value": {"id": "test_dive_id_123", "action": "inserted"}}


@pytest.fixture
def valid_dive_data() -> Dict[str, Any]:
    return {
        "user_id": "test-user-123",
        "dive_number": 1,
        "dive_date": int(time.time() * 1000),
        "location": "Portofino, Italy",
        "latitude": 44.3036653,
        "longitude": 9.2093446,
        "osm_link": "https://www.openstreetmap.org/?mlat=44.3036653&mlon=9.2093446#map=16/44.3036653/9.2093446",
        "site": "Cristo degli Abissi",
        "duration": 45.0,
        "max_depth": 20.0,
        "temperature": 18.5,
        "visibility": 15.0,
        "weather": "sunny",
        "suit_thickness": 5.0,
        "lead_weights": 4.0,
        "club_name": "Portofino Divers",
        "club_website": "https://portofinodivers.com",
        "instructor_name": "Marco Rossi",
        "notes": "Amazing dive",
        "photo_storage_ids": ["photo_123"],
        "buddy_check": True,
        "briefed": True,
    }


@pytest.fixture
def minimal_dive_data() -> Dict[str, Any]:
    return {
        "user_id": "test-user-456",
        "dive_number": 2,
        "dive_date": int(time.time() * 1000),
        "location": "Red Sea",
        "duration": 30.0,
        "max_depth": 15.0,
        "club_name": "Red Sea Divers",
        "instructor_name": "Ahmed Hassan",
        "photo_storage_ids": ["photo_456"],
    }


def test_upsert_dive_success(
    valid_dive_data: Dict[str, Any], mock_convex_response: Dict[str, Any]
) -> None:
    """Test successful dive upsert with all fields"""
    with patch("httpx.AsyncClient") as mock_client:
        mock_response = MagicMock()
        mock_response.json = MagicMock(return_value=mock_convex_response)
        mock_response.raise_for_status = MagicMock()
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
            return_value=mock_response
        )

        response = client.post("/dives/upsert", json=valid_dive_data)
        assert response.status_code == 200
        assert response.json() == mock_convex_response["value"]

        call_args = mock_client.return_value.__aenter__.return_value.post.call_args
        sent_args = call_args.kwargs["json"]["args"]
        # ADDED: ensure osm_link was included in payload sent to Convex
        assert "osm_link" in sent_args
        assert sent_args["osm_link"] == valid_dive_data["osm_link"]


def test_upsert_dive_minimal_fields(
    minimal_dive_data: Dict[str, Any], mock_convex_response: Dict[str, Any]
) -> None:
    """Test upsert with only required fields"""
    with patch("httpx.AsyncClient") as mock_client:
        mock_response = MagicMock()
        mock_response.json = MagicMock(return_value=mock_convex_response)
        mock_response.raise_for_status = MagicMock()

        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
            return_value=mock_response
        )

        response = client.post("/dives/upsert", json=minimal_dive_data)

        assert response.status_code == 200
        assert response.json() == mock_convex_response["value"]


def test_upsert_dive_server_managed_timestamps(valid_dive_data: Dict[str, Any]) -> None:
    """Test that logged_at and updated_at are NOT sent (server-managed)"""
    with patch("httpx.AsyncClient") as mock_client:
        mock_response = MagicMock()
        mock_response.json = MagicMock(return_value={"value": {"id": "123", "action": "updated"}})
        mock_response.raise_for_status = MagicMock()

        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
            return_value=mock_response
        )

        response = client.post("/dives/upsert", json=valid_dive_data)

        # Get the actual payload sent to Convex
        call_args = mock_client.return_value.__aenter__.return_value.post.call_args
        sent_payload = call_args.kwargs["json"]["args"]

        # Verify logged_at and updated_at are NOT in the payload (server-managed)
        assert "logged_at" not in sent_payload
        assert "updated_at" not in sent_payload
        assert response.status_code == 200


def test_upsert_dive_missing_required_field() -> None:
    """Test validation error when required field is missing"""
    invalid_data = {
        "user_id": "test-user",
        "dive_number": 1,
        # Missing required fields like dive_date, location, duration, etc.
    }

    response = client.post("/dives/upsert", json=invalid_data)

    assert response.status_code == 422  # Validation error


def test_upsert_dive_invalid_types() -> None:
    """Test validation error with invalid field types"""
    invalid_data = {
        "user_id": "test-user",
        "dive_number": "not-a-number",  # Should be int
        "dive_date": "invalid-date",  # Should be int
        "location": "Test Location",
        "duration": "not-a-float",  # Should be float
        "max_depth": "not-a-float",  # Should be float
        "club_name": "Test Dive Club",
        "instructor_name": "Test Instructor",
        "photo_storage_ids": ["photo_test"],
        "logged_at": int(time.time() * 1000),
        "updated_at": int(time.time() * 1000),
    }

    response = client.post("/dives/upsert", json=invalid_data)

    assert response.status_code == 422


def test_upsert_dive_empty_arrays() -> None:
    """Test basic dive upsert with minimal optional fields"""
    dive_data = {
        "user_id": "test-user",
        "dive_number": 1,
        "dive_date": int(time.time() * 1000),
        "location": "Test Location",
        "duration": 30.0,
        "max_depth": 15.0,
        "club_name": "Test Dive Club",
        "instructor_name": "Test Instructor",
        "photo_storage_ids": ["photo_test"],
    }

    with patch("httpx.AsyncClient") as mock_client:
        mock_response = MagicMock()
        mock_response.json = MagicMock(return_value={"value": {"id": "123", "action": "inserted"}})
        mock_response.raise_for_status = MagicMock()

        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
            return_value=mock_response
        )

        response = client.post("/dives/upsert", json=dive_data)

        assert response.status_code == 200


def test_upsert_dive_convex_api_call_format(valid_dive_data: Dict[str, Any]) -> None:
    """Test that the Convex API is called with correct format"""
    with patch("httpx.AsyncClient") as mock_client:
        mock_response = MagicMock()
        mock_response.json = MagicMock(return_value={"value": {"id": "123", "action": "inserted"}})
        mock_response.raise_for_status = MagicMock()

        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
            return_value=mock_response
        )

        response = client.post("/dives/upsert", json=valid_dive_data)

        # Verify the API call format
        call_args = mock_client.return_value.__aenter__.return_value.post.call_args
        payload = call_args.kwargs["json"]
        print(payload)
        assert payload["path"] == "dives:upsertDive"
        assert payload["format"] == "json"
        assert "args" in payload
        assert payload["args"]["user_id"] == valid_dive_data["user_id"]
        assert payload["args"]["dive_number"] == valid_dive_data["dive_number"]
        assert response.status_code == 200


def test_post_and_retrieve_dive() -> None:
    """Test posting a dive and then retrieving it by ID"""
    # Create dive data with dive_number 1 (0001)
    dive_data = {
        "user_id": "test-user-001",
        "dive_number": 1,
        "dive_date": 1769212800000,
        "location": "Great Barrier Reef, Australia",
        "latitude": -18.2871,
        "longitude": 147.6992,
        "site": "Cod Hole",
        "duration": 52.0,
        "max_depth": 25.0,
        "temperature": 26.0,
        "visibility": 30.0,
        "weather": "sunny",
        "suit_thickness": 3.0,
        "lead_weights": 2.0,
        "club_name": "Cairns Dive Adventures",
        "club_website": "https://cairnsdive.com",
        "instructor_name": "Steve Irwin Jr",
        "notes": "Amazing dive with giant potato cod!",
        "photo_storage_ids": ["photo_001_gbr"],
        "buddy_check": True,
        "briefed": True,
    }

    # Mock ID returned from Convex after insertion
    created_dive_id = "kg2test001dive123456789abc"

    with patch("httpx.AsyncClient") as mock_client:
        # Setup mock responses list for sequential calls
        mock_post_context = mock_client.return_value.__aenter__.return_value

        # Mock response for POST /dives/upsert
        mock_upsert_response = MagicMock()
        mock_upsert_response.json = MagicMock(
            return_value={"value": {"id": created_dive_id, "action": "inserted"}}
        )
        mock_upsert_response.raise_for_status = MagicMock()

        # Mock response for GET /dives/{id}
        mock_get_response = MagicMock()
        # The retrieved dive should include all the data plus Convex fields
        retrieved_dive = {
            "_id": created_dive_id,
            "_creationTime": 1769295983026,
            **{k: v for k, v in dive_data.items() if k not in ["logged_at", "updated_at"]},
            "logged_at": 1769295983026,
            "updated_at": 1769295983026,
        }
        mock_get_response.json = MagicMock(return_value={"value": retrieved_dive})
        mock_get_response.raise_for_status = MagicMock()

        # Set up the mock to return different responses for each call
        mock_post_context.post = AsyncMock(side_effect=[mock_upsert_response, mock_get_response])

        # Step 1: POST the dive
        post_response = client.post("/dives/upsert", json=dive_data)

        assert post_response.status_code == 200
        assert post_response.json()["id"] == created_dive_id
        assert post_response.json()["action"] == "inserted"

        # Step 2: GET the dive by ID
        get_response = client.get(f"/dives/{created_dive_id}")

        assert get_response.status_code == 200
        retrieved_data = get_response.json()

        # Verify the retrieved data matches what we posted
        assert retrieved_data["_id"] == created_dive_id
        assert retrieved_data["user_id"] == dive_data["user_id"]
        assert retrieved_data["dive_number"] == dive_data["dive_number"]
        assert retrieved_data["location"] == dive_data["location"]
        assert retrieved_data["site"] == dive_data["site"]
        assert retrieved_data["duration"] == dive_data["duration"]
        assert retrieved_data["max_depth"] == dive_data["max_depth"]
        assert retrieved_data["club_name"] == dive_data["club_name"]
        assert retrieved_data["notes"] == dive_data["notes"]

        # Verify both API calls were made
        assert mock_post_context.post.call_count == 2

        # Verify first call was to upsertDive mutation
        first_call = mock_post_context.post.call_args_list[0]
        assert first_call.kwargs["json"]["path"] == "dives:upsertDive"

        # Verify second call was to getDiveById query
        second_call = mock_post_context.post.call_args_list[1]
        assert second_call.kwargs["json"]["path"] == "dives:getDiveById"
        assert second_call.kwargs["json"]["args"]["id"] == created_dive_id


def test_get_dive_not_found() -> None:
    """Test GET endpoint returns 404 for non-existent dive"""
    non_existent_id = "kg2nonexistent123456789"

    with patch("httpx.AsyncClient") as mock_client:
        # Mock response returning None (dive not found)
        mock_response = MagicMock()
        mock_response.json = MagicMock(return_value={"value": None})
        mock_response.raise_for_status = MagicMock()

        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
            return_value=mock_response
        )

        response = client.get(f"/dives/{non_existent_id}")

        assert response.status_code == 404
        assert "error" in response.json()
        assert non_existent_id in response.json()["error"]


# INTEGRATION TEST
@pytest.mark.skipif(
    os.environ.get("CONVEX_URL", "").startswith("https://test"),
    reason="Requires real Convex deployment (set CONVEX_URL env var)",
)
def test_post_and_retrieve_dive_real_convex() -> None:
    """
    Integration test: Actually post to Convex and retrieve the data.
    Requires real Convex deployment - set CONVEX_URL environment variable.
    Run with: CONVEX_URL=https://your-deployment.convex.cloud pytest -k real_convex

    Flags explanation:
    -v = verbose output
    -s = show print statements (so you can see the dive ID and confirmation messages)
    -k real_convex = only run tests matching "real_convex"
    The test will:

    POST a dive with all fields to your real Convex database
    Retrieve it using the GET endpoint
    Verify all data matches
    Print the dive ID and confirmation

    """
    # Create dive data with dive_number 1 (0001)
    dive_data = {
        "user_id": "test-user-integration-001",
        "dive_number": 1,
        "dive_date": 1769212800000,
        "location": "Great Barrier Reef, Australia",
        "latitude": -18.2871,
        "longitude": 147.6992,
        "site": "Cod Hole",
        "duration": 52.0,
        "max_depth": 25.0,
        "temperature": 26.0,
        "visibility": 30.0,
        "weather": "sunny",
        "suit_thickness": 3.0,
        "lead_weights": 2.0,
        "club_name": "Cairns Dive Adventures",
        "club_website": "https://cairnsdive.com",
        "instructor_name": "Steve Irwin Jr",
        "notes": "Integration test dive - Amazing dive with giant potato cod!",
        "photo_storage_ids": ["photo_integration_001_gbr"],
        "buddy_check": True,
        "briefed": True,
    }

    # Step 1: POST the dive to real Convex
    post_response = client.post("/dives/upsert", json=dive_data)

    assert post_response.status_code == 200
    response_data = post_response.json()
    assert "id" in response_data
    assert response_data["action"] in ["inserted", "updated"]

    created_dive_id = response_data["id"]
    print(f"\nCreated dive with ID: {created_dive_id}")

    # Step 2: GET the dive by ID from real Convex
    get_response = client.get(f"/dives/{created_dive_id}")

    assert get_response.status_code == 200
    retrieved_data = get_response.json()

    # Verify the retrieved data matches what we posted
    assert retrieved_data["_id"] == created_dive_id
    assert retrieved_data["user_id"] == dive_data["user_id"]
    assert retrieved_data["dive_number"] == dive_data["dive_number"]
    assert retrieved_data["location"] == dive_data["location"]
    assert retrieved_data["site"] == dive_data["site"]
    assert retrieved_data["duration"] == dive_data["duration"]
    assert retrieved_data["max_depth"] == dive_data["max_depth"]
    assert retrieved_data["temperature"] == dive_data["temperature"]
    assert retrieved_data["visibility"] == dive_data["visibility"]
    assert retrieved_data["weather"] == dive_data["weather"]
    assert retrieved_data["suit_thickness"] == dive_data["suit_thickness"]
    assert retrieved_data["lead_weights"] == dive_data["lead_weights"]
    assert retrieved_data["club_name"] == dive_data["club_name"]
    assert retrieved_data["club_website"] == dive_data["club_website"]
    assert retrieved_data["instructor_name"] == dive_data["instructor_name"]
    assert retrieved_data["notes"] == dive_data["notes"]
    assert retrieved_data["photo_storage_ids"] == dive_data["photo_storage_ids"]
    # Note: Convex stores these with PascalCase field names
    assert retrieved_data["Buddy_check"] == dive_data["buddy_check"]
    assert retrieved_data["Briefed"] == dive_data["briefed"]

    # Verify Convex metadata fields exist
    assert "_id" in retrieved_data
    assert "_creationTime" in retrieved_data
    assert "logged_at" in retrieved_data
    assert "updated_at" in retrieved_data

    print("Successfully verified dive data from Convex!")
    print(f"Dive location: {retrieved_data['location']}")
    print(f"Dive site: {retrieved_data['site']}")
    print(f"Max depth: {retrieved_data['max_depth']}m")


# INTEGRATION TEST - Fish Identification
@pytest.mark.skipif(
    os.environ.get("CONVEX_URL", "").startswith("https://test")
    or not os.environ.get("FISHAL_API_ID")
    or not os.environ.get("FISHAL_API_KEY"),
    reason="Requires real Convex deployment and Fishial API credentials",
)
def test_fish_identification_shark_in_dive_notes() -> None:
    """
    Integration test: Identify fish from shark.jpg and create a dive with species in notes.

    This test:
    1. Uploads assets/shark.jpg to /identify-fish endpoint
    2. Verifies a shark species is identified
    3. Creates a dive entry with observed species in the notes
    4. Retrieves the dive and verifies 'shark' appears in the notes

    Run with:
    uv run pytest tests/test_dive_upsert.py::test_fish_identification_shark_in_dive_notes -v -s
    """
    # Step 1: Load the shark image
    shark_image_path = Path(__file__).parent.parent / "assets" / "shark.jpg"
    assert shark_image_path.exists(), f"Shark image not found at {shark_image_path}"

    with open(shark_image_path, "rb") as f:
        image_data = f.read()

    # Step 2: Identify the fish using the API
    identify_response = client.post(
        "/identify-fish",
        files={"file": ("shark.jpg", image_data, "image/jpeg")},
    )

    assert identify_response.status_code == 200, f"Fish identification failed: {identify_response.text}"
    identify_result = identify_response.json()
    assert identify_result["success"], f"Fish identification unsuccessful: {identify_result}"
    assert len(identify_result["species"]) > 0, "No species identified"

    # Get the top identified species
    top_species = identify_result["species"][0]
    species_name = top_species["name"]
    accuracy = top_species["accuracy"]
    print(f"\nIdentified species: {species_name} (accuracy: {accuracy:.1%})")

    # Known shark genera/species (scientific names)
    shark_indicators = [
        "carcharhinus",  # Bull shark, reef sharks, etc.
        "galeocerdo",    # Tiger shark
        "triaenodon",    # Whitetip reef shark
        "carcharodon",   # Great white shark
        "sphyrna",       # Hammerhead sharks
        "negaprion",     # Lemon shark
        "ginglymostoma", # Nurse shark
        "rhincodon",     # Whale shark
        "isurus",        # Mako shark
        "prionace",      # Blue shark
        "shark",         # Common name fallback
    ]

    # Verify the identified species is a shark
    is_shark = any(indicator in species_name.lower() for indicator in shark_indicators)
    assert is_shark, f"Expected a shark species but got: {species_name}"

    # Step 3: Create dive entry with observed species in notes
    # Include both scientific name and "shark" for readability
    observed_species_note = f"Observed species: {species_name} (shark)"
    dive_data = {
        "user_id": "test-user-fish-001",
        "dive_number": 100,
        "dive_date": int(time.time() * 1000),
        "location": "Bahamas, Tiger Beach",
        "latitude": 26.8667,
        "longitude": -79.0167,
        "site": "Tiger Beach",
        "duration": 45.0,
        "max_depth": 12.0,
        "temperature": 25.0,
        "visibility": 25.0,
        "weather": "sunny",
        "suit_thickness": 3.0,
        "lead_weights": 4.0,
        "club_name": "Bahamas Shark Diving",
        "instructor_name": "Jim Abernethy",
        "notes": observed_species_note,
        "photo_storage_ids": ["shark_photo_001"],
        "buddy_check": True,
        "briefed": True,
    }

    # Step 4: POST the dive
    post_response = client.post("/dives/upsert", json=dive_data)
    assert post_response.status_code == 200, f"Dive upsert failed: {post_response.text}"

    response_data = post_response.json()
    assert "id" in response_data
    dive_id = response_data["id"]
    print(f"Created dive with ID: {dive_id}")

    # Step 5: GET the dive and verify notes contain 'shark'
    get_response = client.get(f"/dives/{dive_id}")
    assert get_response.status_code == 200, f"Failed to retrieve dive: {get_response.text}"

    retrieved_dive = get_response.json()
    notes = retrieved_dive.get("notes", "")

    # Assert that 'shark' appears in the notes (case-insensitive)
    assert "shark" in notes.lower(), (
        f"Expected 'shark' in notes but got: '{notes}'. "
        f"Identified species was: {species_name}"
    )

    print(f"Dive notes: {notes}")
    print("Successfully verified shark identification in dive notes!")


# commands for the integration tests:

# Windows Command Prompt (cmd):
# set CONVEX_URL=https://friendly-finch-619.convex.cloud && uv run pytest tests/test_dive_upsert.py::test_post_and_retrieve_dive_real_convex -v -s

# Windows PowerShell:
# $env:CONVEX_URL="https://friendly-finch-619.convex.cloud"; uv run pytest tests/test_dive_upsert.py::test_post_and_retrieve_dive_real_convex -v -s

# Git Bash / Linux / macOS:
# CONVEX_URL=https://friendly-finch-619.convex.cloud uv run pytest tests/test_dive_upsert.py::test_post_and_retrieve_dive_real_convex -v -s

# Fish identification test:
# uv run pytest tests/test_dive_upsert.py::test_fish_identification_shark_in_dive_notes -v -s
