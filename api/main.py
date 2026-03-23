from typing import Optional, Any
from fastapi import FastAPI, Query, UploadFile, File, Response
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import httpx
import os
import uvicorn

from api.geolocation import get_coordinates_async
from api.search_club_website import search_club_website
from api.fish_finder import identify_fish
from dotenv import load_dotenv

# Load .env file
env_path = ".env"
load_dotenv(env_path)

app = FastAPI()

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------
# Pydantic Models
# ---------------------------------------------------------


class Dive(BaseModel):
    user_id: str
    dive_number: int
    dive_date: int
    location: str
    duration: float
    max_depth: float
    club_name: str
    instructor_name: str
    photo_storage_ids: list[str]  # REQUIRED - list of IDs from `/upload-photos`

    latitude: Optional[float] = None
    longitude: Optional[float] = None
    osm_link: Optional[str] = None
    site: Optional[str] = None
    temperature: Optional[float] = None
    visibility: Optional[float] = None
    weather: Optional[str] = None
    suit_thickness: Optional[float] = None
    lead_weights: Optional[float] = None
    club_website: Optional[str] = None
    notes: Optional[str] = None

    buddy_check: bool = Field(default=True, serialization_alias="Buddy_check")
    briefed: bool = Field(default=True, serialization_alias="Briefed")


class Certification(BaseModel):
    user_id: str
    name: str                              # e.g., "Open Water Diver"
    agency: str                            # e.g., "PADI", "SSI"
    certification_date: int                # Unix timestamp in milliseconds
    certification_number: Optional[str] = None
    instructor_name: Optional[str] = None
    dive_center: Optional[str] = None


class LoginRequest(BaseModel):
    password: str


class ResolveMetadataRequest(BaseModel):
    location_name: str
    club_name: str


class Coordinates(BaseModel):
    latitude: float
    longitude: float


class ResolveMetadataResponse(BaseModel):
    location_name: str
    coordinates: Optional[Coordinates] = None
    osm_link: Optional[str] = None
    club_name: str
    club_website: Optional[str] = None


# ---------------------------------------------------------
# Root / health check
# ---------------------------------------------------------


@app.get("/")
async def root() -> dict:
    return {"status": "ok", "service": "dive-log-api"}


# ---------------------------------------------------------
# File upload: Upload a photo to Convex storage
# ---------------------------------------------------------


CONVEX_URL = os.environ["CONVEX_URL"]  # e.g. https://my-app-123.convex.cloud
CONVEX_GENERATE_URL_FN = os.getenv("CONVEX_GENERATE_URL_FN", "files:generateUploadUrl")
CONVEX_AUTH_TOKEN = os.getenv("CONVEX_AUTH_TOKEN", "").strip()  # optional (Convex auth)


@app.post("/upload-photo", response_model=None)
async def upload_photo(file: UploadFile = File(...)) -> dict[str, str] | JSONResponse:
    allowed = {"image/png", "image/jpeg", "image/bmp"}
    if file.content_type not in allowed:
        return JSONResponse(
            status_code=400, content={"error": f"Unsupported file type: {file.content_type}"}
        )

    file_bytes = await file.read()

    # STEP 1
    try:
        async with httpx.AsyncClient() as client:
            headers = {"Content-Type": "application/json"}
            if CONVEX_AUTH_TOKEN:
                headers["Authorization"] = f"Bearer {CONVEX_AUTH_TOKEN}"

            url_resp = await client.post(
                f"{CONVEX_URL}/api/run/files.js/generateUploadUrl",
                headers=headers,
                json={"args": {}, "format": "json"},
            )
            url_resp.raise_for_status()

            result = url_resp.json()
            signed_url = result.get("value")  # ✅ .value wrapper
            if not signed_url or not isinstance(signed_url, str):
                return JSONResponse(status_code=500, content={"error": f"Invalid URL: {result}"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"Mutation failed: {str(e)}"})

    # STEP 2
    try:
        async with httpx.AsyncClient() as client:
            content_type: str = file.content_type or "application/octet-stream"
            upload_resp = await client.post(
                signed_url, headers={"Content-Type": content_type}, content=file_bytes
            )  # ✅ POST
            upload_resp.raise_for_status()

            result = upload_resp.json()
            storage_id = result.get("storageId")
            if not storage_id:
                return JSONResponse(
                    status_code=500, content={"error": "No storageId", "result": result}
                )
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"Upload failed: {str(e)}"})

    return {"photo_storage_id": storage_id}


@app.post("/upload-photos", response_model=None)
async def upload_photos(files: list[UploadFile] = File(...)) -> dict[str, list[str]] | JSONResponse:
    """
    Upload multiple photos to Convex storage.

    Input:
        files: List of image files (PNG, JPEG, BMP)

    Output:
        - {"photo_storage_ids": ["id1", "id2", ...]} on success
        - JSONResponse with error details on failure
    """
    allowed = {"image/png", "image/jpeg", "image/bmp"}
    storage_ids: list[str] = []

    for file in files:
        if file.content_type not in allowed:
            return JSONResponse(
                status_code=400,
                content={
                    "error": f"Unsupported file type: {file.content_type} for file {file.filename}"
                },
            )

    for file in files:
        file_bytes = await file.read()

        # STEP 1: Get signed upload URL
        try:
            async with httpx.AsyncClient() as client:
                headers = {"Content-Type": "application/json"}
                if CONVEX_AUTH_TOKEN:
                    headers["Authorization"] = f"Bearer {CONVEX_AUTH_TOKEN}"

                url_resp = await client.post(
                    f"{CONVEX_URL}/api/run/files.js/generateUploadUrl",
                    headers=headers,
                    json={"args": {}, "format": "json"},
                )
                url_resp.raise_for_status()

                result = url_resp.json()
                signed_url = result.get("value")
                if not signed_url or not isinstance(signed_url, str):
                    return JSONResponse(
                        status_code=500, content={"error": f"Invalid URL: {result}"}
                    )
        except Exception as e:
            return JSONResponse(status_code=500, content={"error": f"Mutation failed: {str(e)}"})

        # STEP 2: Upload file to signed URL
        try:
            async with httpx.AsyncClient() as client:
                content_type: str = file.content_type or "application/octet-stream"
                upload_resp = await client.post(
                    signed_url, headers={"Content-Type": content_type}, content=file_bytes
                )
                upload_resp.raise_for_status()

                result = upload_resp.json()
                storage_id = result.get("storageId")
                if not storage_id:
                    return JSONResponse(
                        status_code=500,
                        content={
                            "error": f"No storageId for file {file.filename}",
                            "result": result,
                        },
                    )
                storage_ids.append(storage_id)
        except Exception as e:
            return JSONResponse(
                status_code=500, content={"error": f"Upload failed for {file.filename}: {str(e)}"}
            )

    return {"photo_storage_ids": storage_ids}


# ---------------------------------------------------------
# Combined Metadata Resolver
# ---------------------------------------------------------


@app.get("/download-photo/{storage_id}", response_model=None)
async def download_photo(storage_id: str) -> Response | JSONResponse:
    """
    Download an image stored in Convex using its storage ID.
    """

    # Step 1: Request metadata from Convex
    try:
        async with httpx.AsyncClient() as client:
            meta_resp = await client.get(f"{CONVEX_URL}/api/storage/{storage_id}/metadata")
            meta_resp.raise_for_status()
            meta = meta_resp.json()
    except Exception:
        return JSONResponse(
            status_code=404,
            content={"error": f"Could not find metadata for storage ID '{storage_id}'"},
        )

    content_type = meta.get("contentType")
    size = meta.get("size")

    if not content_type:
        return JSONResponse(
            status_code=500, content={"error": "Convex metadata missing 'contentType'"}
        )

    # Step 2: Stream the file bytes from Convex
    try:
        async with httpx.AsyncClient() as client:
            file_resp = await client.get(f"{CONVEX_URL}/api/storage/{storage_id}")
            file_resp.raise_for_status()
            file_bytes = file_resp.content
    except Exception:
        return JSONResponse(
            status_code=500, content={"error": f"Failed to download file with ID '{storage_id}'"}
        )

    # Step 3: Return actual file bytes with correct MIME type
    return Response(
        content=file_bytes,
        media_type=content_type,
        headers={
            "Content-Length": str(size) if size is not None else str(len(file_bytes)),
            "Content-Disposition": f'inline; filename="{storage_id}"',
        },
    )


# ---------------------------------------------------------
# Fish Identification
# ---------------------------------------------------------


@app.post("/identify-fish", response_model=None)
async def identify_fish_endpoint(file: UploadFile = File(...)) -> dict | JSONResponse:
    """
    Identify fish species in an uploaded image using Fishial AI.
    """
    allowed = {"image/png", "image/jpeg", "image/bmp"}
    if file.content_type not in allowed:
        return JSONResponse(
            status_code=400, content={"error": f"Unsupported file type: {file.content_type}"}
        )

    file_bytes = await file.read()
    filename = file.filename or "image.jpg"
    content_type = file.content_type or "image/jpeg"

    result = await identify_fish(
        image_data=file_bytes,
        filename=filename,
        content_type=content_type,
    )

    if not result.success:
        return JSONResponse(status_code=500, content={"success": False, "error": result.error})

    return {
        "success": True,
        "species": [
            {"name": s.name, "accuracy": s.accuracy, "fishangler_id": s.fishangler_id}
            for s in result.species
        ],
    }


@app.post("/resolve-dive-metadata", response_model=ResolveMetadataResponse)
async def resolve_dive_metadata(payload: ResolveMetadataRequest) -> ResolveMetadataResponse:
    """
    Resolve:
    - coordinates + OSM link from location_name
    - club_website from club_name
    """

    # --- Geolocation ---
    lat, lon = None, None
    osm_link = None

    try:
        coords = await get_coordinates_async(payload.location_name)
        if coords:
            lon, lat = coords
            osm_link = f"https://www.openstreetmap.org/?mlat={lat}&mlon={lon}#map=16/{lat}/{lon}"
    except Exception:
        pass

    # --- Club website lookup ---
    club_website = None
    try:
        result = search_club_website(payload.club_name)
        if result.get("success") and result.get("url"):
            club_website = result["url"]
    except Exception:
        pass

    return ResolveMetadataResponse(
        location_name=payload.location_name,
        coordinates=Coordinates(latitude=lat, longitude=lon)
        if lat is not None and lon is not None
        else None,
        osm_link=osm_link,
        club_name=payload.club_name,
        club_website=club_website,
    )


# ---------------------------------------------------------
# Upsert Dive
# ---------------------------------------------------------


@app.post("/dives/upsert")
async def upsert_dive(dive: Dive) -> Any:
    """
    Upsert dive into Convex.
    Automatically enriches:
    - coordinates
    - OSM link
    """
    print(f"[DEBUG] Upserting dive for user_id: {dive.user_id}")

    # Fill missing geolocation data
    if dive.latitude is None or dive.longitude is None:
        try:
            coords = await get_coordinates_async(dive.location)
            if coords:
                dive.longitude, dive.latitude = coords
        except Exception:
            pass

    # Always generate OSM link if coords found
    if dive.latitude and dive.longitude:
        lat, lon = dive.latitude, dive.longitude
        dive.osm_link = f"https://www.openstreetmap.org/?mlat={lat}&mlon={lon}#map=16/{lat}/{lon}"

    payload = dive.model_dump(by_alias=True, exclude_none=True)

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{CONVEX_URL}/api/mutation",
            json={
                "path": "dives:upsertDive",
                "args": payload,
                "format": "json",
            },
        )
        resp.raise_for_status()
        result = resp.json()

    if "error" in result:
        return JSONResponse(
            status_code=400, content={"error": result["error"], "convex_error": True}
        )

    return result.get("value", result)


# ---------------------------------------------------------
# Get Latest Dive (must be before /dives/{dive_id})
# ---------------------------------------------------------


@app.get("/dives/latest")
async def get_latest_dive(user_id: str = Query(..., description="User ID")) -> Any:
    """Get the most recent dive for a user."""
    print(f"[DEBUG] Getting latest dive for user_id: {user_id}")
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{CONVEX_URL}/api/query",
            json={
                "path": "dives:getLatestDive",
                "args": {"user_id": user_id},
                "format": "json",
            },
        )
        resp.raise_for_status()
        data = resp.json()

    if "error" in data:
        return JSONResponse(status_code=400, content={"error": data["error"], "convex_error": True})

    result = data.get("value")
    print(f"[DEBUG] getLatestDive result for {user_id}: {result}")
    if result is None:
        return JSONResponse(status_code=404, content={"error": "No dives found for user"})

    return result


# ---------------------------------------------------------
# Get Dive by ID
# ---------------------------------------------------------


@app.get("/dives/{dive_id}")
async def get_dive_by_id(dive_id: str) -> Any:
    """Retrieve a dive from Convex."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{CONVEX_URL}/api/query",
            json={
                "path": "dives:getDiveById",
                "args": {"id": dive_id},
                "format": "json",
            },
        )
        resp.raise_for_status()
        data = resp.json()

    if "error" in data:
        return JSONResponse(status_code=400, content={"error": data["error"], "convex_error": True})

    result = data.get("value")
    if result is None:
        return JSONResponse(
            status_code=404, content={"error": f"Dive with id '{dive_id}' not found"}
        )

    return result


@app.delete("/dives/{dive_id}")
async def delete_dive(dive_id: str) -> Any:
    """Delete a dive from Convex."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{CONVEX_URL}/api/mutation",
            json={
                "path": "dives:deleteDive",
                "args": {"id": dive_id},
                "format": "json",
            },
        )
        resp.raise_for_status()
        data = resp.json()

    if "error" in data:
        return JSONResponse(status_code=400, content={"error": data["error"], "convex_error": True})

    return data.get("value", {"success": True})


# ---------------------------------------------------------
# List Dives Endpoints
# ---------------------------------------------------------


@app.get("/dives")
async def list_dives(user_id: str = Query(..., description="User ID")) -> Any:
    """List all dives for a user, sorted by date (most recent first)."""
    print(f"[DEBUG] Listing dives for user_id: {user_id}")
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{CONVEX_URL}/api/query",
            json={
                "path": "dives:getAllDives",
                "args": {"user_id": user_id},
                "format": "json",
            },
        )
        resp.raise_for_status()
        data = resp.json()

    if "error" in data:
        return JSONResponse(status_code=400, content={"error": data["error"], "convex_error": True})

    result = data.get("value", [])
    print(f"[DEBUG] Found {len(result)} dives for user_id: {user_id}")
    return result


# ---------------------------------------------------------
# Certifications Endpoints
# ---------------------------------------------------------


@app.get("/certifications")
async def list_certifications(user_id: str = Query(..., description="User ID")) -> Any:
    """List all certifications for a user."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{CONVEX_URL}/api/query",
            json={
                "path": "certifications:getAllCertifications",
                "args": {"user_id": user_id},
                "format": "json",
            },
        )
        resp.raise_for_status()
        data = resp.json()

    if "error" in data:
        return JSONResponse(status_code=400, content={"error": data["error"], "convex_error": True})

    return data.get("value", [])


@app.post("/certifications")
async def add_certification(cert: Certification) -> Any:
    """Add a new certification."""
    payload = cert.model_dump(exclude_none=True)

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{CONVEX_URL}/api/mutation",
            json={
                "path": "certifications:addCertification",
                "args": payload,
                "format": "json",
            },
        )
        resp.raise_for_status()
        data = resp.json()

    if "error" in data:
        return JSONResponse(status_code=400, content={"error": data["error"], "convex_error": True})

    return data.get("value", data)


@app.delete("/certifications/{cert_id}")
async def delete_certification(cert_id: str) -> Any:
    """Delete a certification."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{CONVEX_URL}/api/mutation",
            json={
                "path": "certifications:deleteCertification",
                "args": {"id": cert_id},
                "format": "json",
            },
        )
        resp.raise_for_status()
        data = resp.json()

    if "error" in data:
        return JSONResponse(status_code=400, content={"error": data["error"], "convex_error": True})

    return data.get("value", {"success": True})


# ---------------------------------------------------------
# Config Endpoint (for frontend)
# ---------------------------------------------------------


@app.get("/config")
async def get_config() -> dict:
    """Get configuration for the frontend."""
    return {
        "name_surname": os.getenv("NAME_SURNAME", "Diver"),
        "convex_url": CONVEX_URL,
        "profile_photo": os.getenv("PROFILE_PHOTO", ""),
    }


@app.get("/profile-photo")
async def get_profile_photo() -> Response:
    """Serve the profile photo from the assets folder."""
    from pathlib import Path

    photo_filename = os.getenv("PROFILE_PHOTO", "")
    if not photo_filename:
        return JSONResponse(status_code=404, content={"error": "No profile photo configured"})

    # Look for the photo in assets folder
    photo_path = Path("assets") / photo_filename
    if not photo_path.exists():
        return JSONResponse(status_code=404, content={"error": f"Photo not found: {photo_filename}"})

    # Determine content type
    ext = photo_path.suffix.lower()
    content_types = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".bmp": "image/bmp",
    }
    content_type = content_types.get(ext, "image/jpeg")

    with open(photo_path, "rb") as f:
        photo_bytes = f.read()

    return Response(
        content=photo_bytes,
        media_type=content_type,
        headers={"Content-Disposition": f'inline; filename="{photo_filename}"'},
    )


@app.post("/login")
async def login(request: LoginRequest) -> Any:
    """Validate login password."""
    stored_password = os.getenv("PROFILE_PASSWORD", "")
    if request.password == stored_password:
        return {"success": True}
    return JSONResponse(status_code=401, content={"error": "Invalid password"})


# ---------------------------------------------------------
# Search Club Endpoint
# ---------------------------------------------------------


@app.get("/search-club")
def search_club(q: str = Query(..., description="Club name")) -> Any:
    result = search_club_website(q)
    if result.get("success"):
        return result
    return JSONResponse(
        status_code=404 if "No results" in result.get("error", "") else 500,
        content=result,
    )


# ---------------------------------------------------------
# Run
# ---------------------------------------------------------

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
