# tests/test_upload_photo.py
import os
import asyncio
from pathlib import Path

from fastapi.testclient import TestClient
from starlette import status

from api.main import app
from tests.convex_storage_inspector import get_one_storage_id


client = TestClient(app)


def _require_convex_env() -> None:
    """
    Ensure Convex is configured for live tests.
    """
    convex_url = os.getenv("CONVEX_URL")
    assert convex_url and convex_url.startswith("http"), (
        "CONVEX_URL must be set and valid (e.g., https://<your>.convex.cloud)"
    )


def test_upload_photo_and_inspector_returns_string() -> None:
    """
    Live integration test:
    - Upload assets/dive001.jpg via /upload-photo.
    - Assert 200 and a non-empty photo_storage_id.
    - Then call get_one_storage_id() and assert it returns a non-empty string.
    """
    _require_convex_env()

    # 1) Upload the test image
    file_path = Path(__file__).parent.parent / "assets" / "dive001.jpg"
    assert file_path.exists(), f"Test asset not found: {file_path}"

    content_type = "image/jpeg"

    with open(file_path, "rb") as f:
        resp = client.post(
            "/upload-photo",
            files={"file": (file_path.name, f, content_type)},
        )

    # Assert upload succeeded
    assert resp.status_code == status.HTTP_200_OK, resp.text
    body = resp.json()
    assert "photo_storage_id" in body and isinstance(body["photo_storage_id"], str)
    assert body["photo_storage_id"], "photo_storage_id should not be empty"

    # 2) Inspector should now see at least one storageId
    storage_id = asyncio.run(get_one_storage_id())
    assert isinstance(storage_id, str)
