"""
Fishial API integration for fish recognition.

This module provides functions to identify fish species from images
using the Fishial Recognition API.
"""

import os
import hashlib
import base64
from typing import Optional
from dataclasses import dataclass
import httpx
from dotenv import load_dotenv

load_dotenv()

# Fishial API configuration
FISHIAL_API_ID = os.getenv("FISHAL_API_ID", "").strip()
FISHIAL_API_KEY = os.getenv("FISHAL_API_KEY", "").strip()
FISHIAL_AUTH_URL = "https://api-users.fishial.ai/v1/auth/token"
FISHIAL_API_URL = "https://api.fishial.ai/v1"


@dataclass
class FishSpecies:
    """Represents a recognized fish species."""
    name: str
    accuracy: float
    fishangler_id: Optional[str] = None


@dataclass
class FishRecognitionResult:
    """Result of fish recognition on an image."""
    success: bool
    species: list[FishSpecies]
    error: Optional[str] = None


def _compute_md5_base64(data: bytes) -> str:
    """Compute MD5 checksum and return as Base64-encoded string."""
    md5_hash = hashlib.md5(data).digest()
    return base64.b64encode(md5_hash).decode("utf-8")


async def _get_access_token() -> str:
    """
    Obtain an access token from Fishial API.

    Returns:
        Bearer access token string.

    Raises:
        Exception: If authentication fails.
    """
    if not FISHIAL_API_ID or not FISHIAL_API_KEY:
        raise ValueError("FISHAL_API_ID and FISHAL_API_KEY must be set in environment")

    async with httpx.AsyncClient() as client:
        response = await client.post(
            FISHIAL_AUTH_URL,
            headers={"Content-Type": "application/json"},
            json={
                "client_id": FISHIAL_API_ID,
                "client_secret": FISHIAL_API_KEY,
            },
        )
        response.raise_for_status()
        data = response.json()
        return data["access_token"]


async def _get_upload_url(
    token: str,
    filename: str,
    content_type: str,
    byte_size: int,
    checksum: str,
) -> dict:
    """
    Get a signed URL for uploading an image to Fishial cloud.

    Returns:
        Dict containing 'signed_id', 'upload_url', and 'headers'.
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{FISHIAL_API_URL}/recognition/upload",
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json={
                "blob": {
                    "filename": filename,
                    "content_type": content_type,
                    "byte_size": byte_size,
                    "checksum": checksum,
                }
            },
        )
        response.raise_for_status()
        data = response.json()

        return {
            "signed_id": data["signed-id"],
            "upload_url": data["direct-upload"]["url"],
            "headers": data["direct-upload"]["headers"],
        }


async def _upload_image(upload_url: str, headers: dict, image_data: bytes) -> None:
    """
    Upload image data to the signed URL.

    The upload uses PUT method and only the headers returned from
    the upload URL request.
    """
    async with httpx.AsyncClient() as client:
        # Only use headers provided by Fishial API, plus clear Content-Type
        upload_headers = dict(headers)
        upload_headers["Content-Type"] = ""  # Must be empty per API docs

        response = await client.put(
            upload_url,
            headers=upload_headers,
            content=image_data,
        )
        response.raise_for_status()


async def _recognize_fish(token: str, signed_id: str) -> list[dict]:
    """
    Perform fish recognition on an uploaded image.

    Returns:
        List of recognition results.
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{FISHIAL_API_URL}/recognition/image",
            params={"q": signed_id},
            headers={"Authorization": f"Bearer {token}"},
        )
        response.raise_for_status()
        data = response.json()
        return data.get("results", [])


async def identify_fish(
    image_data: bytes,
    filename: str,
    content_type: str,
) -> FishRecognitionResult:
    """
    Identify fish species in an image.

    Args:
        image_data: Raw image bytes.
        filename: Original filename (e.g., "photo.jpg").
        content_type: MIME type (e.g., "image/jpeg").

    Returns:
        FishRecognitionResult with identified species or error.

    Example:
        >>> with open("fish.jpg", "rb") as f:
        ...     result = await identify_fish(f.read(), "fish.jpg", "image/jpeg")
        >>> for species in result.species:
        ...     print(f"{species.name}: {species.accuracy:.1%}")
    """
    try:
        # Step 1: Get access token
        token = await _get_access_token()

        # Step 2: Compute image metadata
        byte_size = len(image_data)
        checksum = _compute_md5_base64(image_data)

        # Step 3: Get upload URL
        upload_info = await _get_upload_url(
            token=token,
            filename=filename,
            content_type=content_type,
            byte_size=byte_size,
            checksum=checksum,
        )

        # Step 4: Upload image
        await _upload_image(
            upload_url=upload_info["upload_url"],
            headers=upload_info["headers"],
            image_data=image_data,
        )

        # Step 5: Recognize fish
        results = await _recognize_fish(token, upload_info["signed_id"])

        # Parse results
        all_species: list[FishSpecies] = []
        for result in results:
            for species_data in result.get("species", []):
                species = FishSpecies(
                    name=species_data.get("name", "Unknown"),
                    accuracy=species_data.get("accuracy", 0.0),
                    fishangler_id=species_data.get("fishangler-id"),
                )
                all_species.append(species)

        # Sort by accuracy (highest first)
        all_species.sort(key=lambda s: s.accuracy, reverse=True)

        return FishRecognitionResult(success=True, species=all_species)

    except httpx.HTTPStatusError as e:
        return FishRecognitionResult(
            success=False,
            species=[],
            error=f"API error: {e.response.status_code} - {e.response.text}",
        )
    except Exception as e:
        return FishRecognitionResult(
            success=False,
            species=[],
            error=str(e),
        )
