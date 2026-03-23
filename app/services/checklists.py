from typing import Optional, Any, cast
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import httpx
import os

from dotenv import load_dotenv

load_dotenv(".env")

app = FastAPI()

CONVEX_URL = os.environ["CONVEX_URL"]


# ---------------------------------------------------------
# Pydantic Models
# ---------------------------------------------------------


class ChecklistCreate(BaseModel):
    name: str
    link: str


class ChecklistUpdate(BaseModel):
    name: Optional[str] = None
    link: Optional[str] = None


# ---------------------------------------------------------
# Create checklist
# ---------------------------------------------------------


@app.post("/checklists", response_model=None)
async def create_checklist(payload: ChecklistCreate) -> dict[str, Any] | JSONResponse:
    """Create a new checklist entry."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{CONVEX_URL}/api/mutation",
            json={
                "path": "checklists:createChecklist",
                "args": payload.model_dump(),
                "format": "json",
            },
        )
        resp.raise_for_status()
        data = resp.json()

    if "error" in data:
        return JSONResponse(status_code=400, content={"error": data["error"], "convex_error": True})

    return cast(dict[str, Any], data.get("value", data))


# ---------------------------------------------------------
# Get all checklists
# ---------------------------------------------------------


@app.get("/checklists", response_model=None)
async def get_all_checklists() -> list[Any] | JSONResponse:
    """Retrieve all checklist entries."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{CONVEX_URL}/api/query",
            json={
                "path": "checklists:getAllChecklists",
                "args": {},
                "format": "json",
            },
        )
        resp.raise_for_status()
        data = resp.json()

    if "error" in data:
        return JSONResponse(status_code=400, content={"error": data["error"], "convex_error": True})

    return cast(list[Any], data.get("value", []))
# ---------------------------------------------------------
# Get checklist by ID
# ---------------------------------------------------------


@app.get("/checklists/{checklist_id}", response_model=None)
async def get_checklist_by_id(checklist_id: str) -> Any | JSONResponse:
    """Retrieve a single checklist entry by its Convex ID."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{CONVEX_URL}/api/query",
            json={
                "path": "checklists:getChecklistById",
                "args": {"id": checklist_id},
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
            status_code=404,
            content={"error": f"Checklist with id '{checklist_id}' not found"},
        )

    return result


# ---------------------------------------------------------
# Update checklist
# ---------------------------------------------------------


@app.put("/checklists/{checklist_id}", response_model=None)
async def update_checklist(
    checklist_id: str, payload: ChecklistUpdate
) -> dict[str, Any] | JSONResponse:
    """Update name and/or link of an existing checklist entry."""
    args: dict[str, Any] = {"id": checklist_id}
    if payload.name is not None:
        args["name"] = payload.name
    if payload.link is not None:
        args["link"] = payload.link

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{CONVEX_URL}/api/mutation",
            json={
                "path": "checklists:updateChecklist",
                "args": args,
                "format": "json",
            },
        )
        resp.raise_for_status()
        data = resp.json()

    if "error" in data:
        return JSONResponse(status_code=400, content={"error": data["error"], "convex_error": True})

    if data.get("status") == "error":
        return JSONResponse(
            status_code=404,
            content={"error": data.get("errorMessage", "Checklist not found"), "convex_error": True},
        )

    return cast(dict[str, Any], data.get("value", data))


# ---------------------------------------------------------
# Delete checklist
# ---------------------------------------------------------


@app.delete("/checklists/{checklist_id}", response_model=None)
async def delete_checklist(checklist_id: str) -> dict[str, Any] | JSONResponse:
    """Delete a checklist entry by its Convex ID."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{CONVEX_URL}/api/mutation",
            json={
                "path": "checklists:deleteChecklist",
                "args": {"id": checklist_id},
                "format": "json",
            },
        )
        resp.raise_for_status()
        data = resp.json()

    if "error" in data:
        return JSONResponse(status_code=400, content={"error": data["error"], "convex_error": True})

    if data.get("status") == "error":
        return JSONResponse(
            status_code=404,
            content={"error": data.get("errorMessage", "Checklist not found"), "convex_error": True},
        )

    return cast(dict[str, Any], data.get("value", data))


# ---------------------------------------------------------
# Run
# ---------------------------------------------------------


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)
