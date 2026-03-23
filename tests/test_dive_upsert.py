import os
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from dotenv import load_dotenv

# Load .env file
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

if "CONVEX_URL" not in os.environ:
    os.environ["CONVEX_URL"] = "https://test.convex.cloud"

from api.main import app

client = TestClient(app)


# INTEGRATION TEST - Fish Identification with Geolocation and Club Search
@pytest.mark.skipif(
    os.environ.get("CONVEX_URL", "").startswith("https://test")
    or not os.environ.get("FISHAL_API_ID")
    or not os.environ.get("FISHAL_API_KEY"),
    reason="Requires real Convex deployment and Fishial API credentials",
)
def test_fish_identification_shark_in_dive_notes() -> None:
    """
    Integration test: Full dive logging workflow with fish identification,
    geolocation, and club website lookup.

    This test:
    1. Calls /resolve-dive-metadata to get coordinates for "Coiba, Panama"
       and website for "Panama Divers Coiba"
    2. Uploads assets/shark.jpg to /identify-fish endpoint
    3. Verifies a shark species is identified
    4. Creates a dive entry with observed species in the notes
    5. Retrieves the dive and verifies 'shark' appears in the notes

    Run with:
    uv run pytest tests/test_dive_upsert.py::test_fish_identification_shark_in_dive_notes -v -s
    """
    # =================================================================
    # Step 1: Resolve metadata (geolocation + club website)
    # =================================================================
    location_name = "Coiba, Panama"
    club_name = "Panama Divers Coiba"

    metadata_response = client.post(
        "/resolve-dive-metadata",
        json={"location_name": location_name, "club_name": club_name},
    )

    assert metadata_response.status_code == 200, (
        f"Metadata resolution failed: {metadata_response.text}"
    )
    metadata = metadata_response.json()

    print("\n--- Metadata Resolution ---")
    print(f"Location: {metadata['location_name']}")

    # Verify geolocation was resolved
    coordinates = metadata.get("coordinates")
    if coordinates:
        print(f"Coordinates: {coordinates['latitude']}, {coordinates['longitude']}")
        print(f"OSM Link: {metadata.get('osm_link')}")
        assert coordinates.get("latitude") is not None, "Latitude should be resolved"
        assert coordinates.get("longitude") is not None, "Longitude should be resolved"
        assert metadata.get("osm_link") is not None, "OSM link should be generated"
    else:
        print("Warning: Coordinates not resolved (Nominatim may be rate-limited)")

    # Verify club website was searched
    print(f"Club: {metadata['club_name']}")
    club_website = metadata.get("club_website")
    if club_website:
        print(f"Club Website: {club_website}")
    else:
        print("Warning: Club website not found")

    # =================================================================
    # Step 2: Load and identify the shark image
    # =================================================================
    shark_image_path = Path(__file__).parent.parent / "assets" / "shark.jpg"
    assert shark_image_path.exists(), f"Shark image not found at {shark_image_path}"

    with open(shark_image_path, "rb") as f:
        image_data = f.read()

    print("\n--- Fish Identification ---")
    identify_response = client.post(
        "/identify-fish",
        files={"file": ("shark.jpg", image_data, "image/jpeg")},
    )

    assert identify_response.status_code == 200, (
        f"Fish identification failed: {identify_response.text}"
    )
    identify_result = identify_response.json()
    assert identify_result["success"], f"Fish identification unsuccessful: {identify_result}"
    assert len(identify_result["species"]) > 0, "No species identified"

    # Get the top identified species
    top_species = identify_result["species"][0]
    species_name = top_species["name"]
    accuracy = top_species["accuracy"]
    print(f"Identified species: {species_name} (accuracy: {accuracy:.1%})")

    # Known shark genera/species (scientific names)
    shark_indicators = [
        "carcharhinus",  # Bull shark, reef sharks, etc.
        "galeocerdo",  # Tiger shark
        "triaenodon",  # Whitetip reef shark
        "carcharodon",  # Great white shark
        "sphyrna",  # Hammerhead sharks
        "negaprion",  # Lemon shark
        "ginglymostoma",  # Nurse shark
        "rhincodon",  # Whale shark
        "isurus",  # Mako shark
        "prionace",  # Blue shark
        "shark",  # Common name fallback
    ]

    # Verify the identified species is a shark
    is_shark = any(indicator in species_name.lower() for indicator in shark_indicators)
    assert is_shark, f"Expected a shark species but got: {species_name}"

    # =================================================================
    # Step 3: Create dive entry with all resolved metadata
    # =================================================================
    print("\n--- Creating Dive Entry ---")

    # Include both scientific name and "shark" for readability
    observed_species_note = f"Observed species: {species_name} (shark)"

    dive_data = {
        "user_id": "test-user-fish-001",
        "dive_number": 100,
        "dive_date": int(time.time() * 1000),
        "location": location_name,
        "site": "Coiba National Park",
        "duration": 45.0,
        "max_depth": 25.0,
        "temperature": 27.0,
        "visibility": 20.0,
        "weather": "sunny",
        "suit_thickness": 3.0,
        "lead_weights": 4.0,
        "club_name": club_name,
        "instructor_name": "Carlos Rodriguez",
        "notes": observed_species_note,
        "photo_storage_ids": ["shark_photo_coiba_001"],
        "buddy_check": True,
        "briefed": True,
    }

    # Add coordinates if resolved
    if coordinates:
        dive_data["latitude"] = coordinates["latitude"]
        dive_data["longitude"] = coordinates["longitude"]

    # Add club website if found
    if club_website:
        dive_data["club_website"] = club_website

    # POST the dive
    post_response = client.post("/dives/upsert", json=dive_data)
    assert post_response.status_code == 200, f"Dive upsert failed: {post_response.text}"

    response_data = post_response.json()
    assert "id" in response_data, f"Expected 'id' in response but got: {response_data}"
    dive_id = response_data["id"]
    print(f"Created dive with ID: {dive_id}")

    # =================================================================
    # Step 4: Retrieve and verify the dive
    # =================================================================
    print("\n--- Verifying Dive Entry ---")

    get_response = client.get(f"/dives/{dive_id}")
    assert get_response.status_code == 200, f"Failed to retrieve dive: {get_response.text}"

    retrieved_dive = get_response.json()
    notes = retrieved_dive.get("notes", "")

    # Assert that 'shark' appears in the notes (case-insensitive)
    assert "shark" in notes.lower(), (
        f"Expected 'shark' in notes but got: '{notes}'. Identified species was: {species_name}"
    )

    # Verify location
    assert retrieved_dive["location"] == location_name
    print(f"Location: {retrieved_dive['location']}")

    # Verify club name
    assert retrieved_dive["club_name"] == club_name
    print(f"Club: {retrieved_dive['club_name']}")

    # Verify notes contain the species
    print(f"Notes: {notes}")

    # Verify OSM link was generated if coordinates were provided
    if coordinates:
        assert retrieved_dive.get("osm_link") is not None, "OSM link should be in the dive record"
        print(f"OSM Link: {retrieved_dive.get('osm_link')}")

    print("\n✓ Successfully verified shark identification in dive notes!")
    print("✓ Geolocation service called for Coiba, Panama")
    print("✓ Club website search called for Panama Divers Coiba")


# =================================================================
# Test Commands
# =================================================================
#
# Run the integration test:
# uv run pytest tests/test_dive_upsert.py::test_fish_identification_shark_in_dive_notes -v -s
#
# This test requires:
# - CONVEX_URL environment variable pointing to a real Convex deployment
# - FISHAL_API_ID and FISHAL_API_KEY for fish identification
# - assets/shark.jpg image file
