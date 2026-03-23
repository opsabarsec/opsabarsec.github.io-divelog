# tests/test_checklists.py
import os
import sys
import json
from pathlib import Path

# Allow running directly with `python tests/test_checklists.py`
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()

from fastapi.testclient import TestClient
from starlette import status

from app.services.checklists import app

client = TestClient(app)

TRAVEL_CHECKLIST = {
    "name": "Travel checklist diving",
    "link": "https://docs.google.com/document/d/1NymbmUZG72VcBbjJ1sWEK1vI3z0kd2NA6TWIHwJErwE/edit?usp=sharing",
}


def _require_convex_env() -> None:
    """Ensure Convex is configured for live tests."""
    convex_url = os.getenv("CONVEX_URL")
    assert convex_url and convex_url.startswith("http"), (
        "CONVEX_URL must be set and valid (e.g., https://<your>.convex.cloud)"
    )


def _delete_existing_by_name(name: str) -> None:
    """Delete any existing checklist entries with the given name (idempotency)."""
    resp = client.get("/checklists")
    assert resp.status_code == status.HTTP_200_OK, resp.text
    for entry in resp.json():
        if entry.get("name") == name:
            del_resp = client.delete(f"/checklists/{entry['_id']}")
            assert del_resp.status_code == status.HTTP_200_OK, (
                f"Failed to delete existing entry {entry['_id']}: {del_resp.text}"
            )
            print(f"  Removed existing entry: {entry['_id']}")


def test_create_and_verify_travel_checklist() -> None:
    """
    Integration test:
    - If an entry with the same name already exists, delete it first.
    - Create the Travel checklist diving entry in Convex.
    - Fetch it back by ID and verify all fields are stored correctly.
    """
    _require_convex_env()

    # 1. Clean up any pre-existing entry with the same name
    _delete_existing_by_name(TRAVEL_CHECKLIST["name"])

    # 2. Create the checklist entry
    resp = client.post("/checklists", json=TRAVEL_CHECKLIST)
    assert resp.status_code == status.HTTP_200_OK, resp.text
    body = resp.json()

    print(f"\n=== CREATE RESPONSE ===\n{json.dumps(body, indent=2)}\n")

    assert "id" in body, f"Response should contain 'id'. Got: {body}"
    checklist_id = body["id"]
    assert isinstance(checklist_id, str) and checklist_id, "id must be a non-empty string"

    # 3. Fetch the entry back from Convex to verify it was stored
    get_resp = client.get(f"/checklists/{checklist_id}")
    assert get_resp.status_code == status.HTTP_200_OK, get_resp.text
    record = get_resp.json()

    print(f"\n=== FETCHED RECORD ===\n{json.dumps(record, indent=2)}\n")

    assert record["name"] == TRAVEL_CHECKLIST["name"], (
        f"name mismatch: expected '{TRAVEL_CHECKLIST['name']}', got '{record['name']}'"
    )
    assert record["link"] == TRAVEL_CHECKLIST["link"], (
        f"link mismatch: expected '{TRAVEL_CHECKLIST['link']}', got '{record['link']}'"
    )

    print(f"✓ Checklist created and verified: id={checklist_id}")
    print(f"  name : {record['name']}")
    print(f"  link : {record['link']}")


if __name__ == "__main__":
    test_create_and_verify_travel_checklist()
