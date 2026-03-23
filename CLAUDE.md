# CLAUDE.md — Dive Log App

## Project overview

A dive logging application with a **Python/FastAPI** REST layer and a **Convex** (TypeScript) backend-as-a-service for data persistence and file storage.

Author: Marco Berta — https://github.com/opsabarsec/dive-log-app

---

## Stack

| Layer | Technology |
|-------|-----------|
| REST API | FastAPI (Python 3.12) |
| Database + Storage | Convex (TypeScript) |
| HTTP client | httpx (async) |
| Data validation | Pydantic v2 |
| Package manager (Python) | uv (`uv.lock`) |
| Package manager (JS) | npm (`package-lock.json`) |
| Linter / formatter | ruff + black (line-length 100) |
| Type checker | mypy |
| Test runner | pytest |

---

## Repository layout

```
dive-log-app/
├── app/
│   ├── divelog.py              # Main FastAPI app — all dive endpoints
│   └── services/
│       ├── geolocation.py      # Nominatim OSM geocoding (async, rate-limited)
│       ├── search_club_website.py  # DuckDuckGo club website search
│       └── checklists.py       # FastAPI app — CRUD endpoints for checklists table
├── convex/
│   ├── schema.ts               # Convex table definitions (source of truth)
│   ├── dives.ts                # upsertDive mutation, getDiveById query
│   ├── checklists.ts           # createChecklist, getAllChecklists, getChecklistById,
│   │                           #   updateChecklist, deleteChecklist
│   └── files.ts                # generateUploadUrl mutation (photo storage)
├── tests/
│   ├── test_upsert_with_photo.py   # Integration tests for dive upsert + photo upload
│   ├── test_checklists.py          # Integration test for checklist CRUD
│   ├── test_upload_photo.py
│   └── test_resolve_dive_metadata.py
├── assets/
│   └── dive001.jpg             # Sample photo used in tests
├── .env                        # CONVEX_DEPLOYMENT, CONVEX_URL, MY_EMAIL
├── pyproject.toml              # Python deps, ruff/black/mypy/pytest config
└── package.json                # Convex JS deps
```

---

## Environment variables (`.env`)

```
CONVEX_DEPLOYMENT=<dev deployment name>   # set by `npx convex dev`
CONVEX_URL=https://<deployment>.convex.cloud
MY_EMAIL=<your email>
```

`CONVEX_URL` is the only variable the Python code reads at runtime (via `os.environ["CONVEX_URL"]`).

---

## Convex database schema

### `dives` table
All dive log entries. Key fields: `user_id`, `dive_number` (unique per user), `dive_date` (epoch ms), `location`, `duration`, `max_depth`, `club_name`, `instructor_name`, `photo_storage_id`, `mode` (`"scubadiving"` | `"freediving"`), `Buddy_check`, `Briefed`. Optional: `latitude`, `longitude`, `osm_link`, `site`, `water_temperature`, `suit_thickness`, `lead_weights`, `club_website`, `notes`. Server-managed: `logged_at`, `updated_at`.
Index: `by_dive_number` on `(user_id, dive_number)`.

### `checklists` table
Google Drive checklist links. Fields: `name` (string), `link` (string).

---

## FastAPI endpoints

### `app/divelog.py` (port 8000)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/upload-photo` | Upload dive photo → returns `photo_storage_id` |
| GET | `/download-photo/{storage_id}` | Stream photo bytes from Convex storage |
| POST | `/resolve-dive-metadata` | Preview geocoords + club website before submitting |
| POST | `/dives/upsert-with-photo` | Multipart: upload photo + upsert dive (auto-enriches coords & club website) |
| GET | `/dives/{dive_id}` | Fetch dive by Convex ID |

### `app/services/checklists.py` (port 8001)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/checklists` | Create checklist entry |
| GET | `/checklists` | List all checklists |
| GET | `/checklists/{id}` | Get by Convex ID |
| PUT | `/checklists/{id}` | Update name and/or link |
| DELETE | `/checklists/{id}` | Delete entry |

---

## Convex API call pattern (Python → Convex)

All Convex calls go through `httpx` against the HTTP API:

```python
# Mutation
async with httpx.AsyncClient() as client:
    resp = await client.post(
        f"{CONVEX_URL}/api/mutation",
        json={"path": "tableName:functionName", "args": {...}, "format": "json"},
    )
    data = resp.json()
    result = data.get("value")   # actual return value lives under "value"

# Query
async with httpx.AsyncClient() as client:
    resp = await client.post(
        f"{CONVEX_URL}/api/query",
        json={"path": "tableName:functionName", "args": {...}, "format": "json"},
    )
```

Error shape from Convex: `{"status": "error", "errorMessage": "..."}` or `{"error": "..."}`.

---

## Development workflow

### Run the API
```bash
uvicorn app.divelog:app --reload --port 8000
uvicorn app.services.checklists:app --reload --port 8001
```

### Push Convex schema + functions to dev deployment
```bash
npx convex dev --once
```
**Must run this every time `convex/*.ts` files are added or changed**, before running integration tests.

### Run tests
```bash
python -m pytest tests/ -v           # all tests
python -m pytest tests/test_checklists.py -v
python tests/test_checklists.py      # also runnable directly
```

### Lint / format / typecheck
```bash
ruff check .
black .
mypy .
```

---

## Testing conventions

- Tests use `fastapi.testclient.TestClient` (synchronous wrapper, no running server needed).
- Integration tests hit the real Convex dev deployment — `CONVEX_URL` must be set.
- `_require_convex_env()` helper asserts `CONVEX_URL` at the start of each live test.
- Tests that create data first clean up any pre-existing record with the same key to stay idempotent.
- Test files that may be run directly with `python` include `sys.path.insert(0, project_root)` and a `__main__` block.

---

## Adding a new table — checklist

1. Add the table to `convex/schema.ts`.
2. Create `convex/<table>.ts` with mutations (`mutation`) and queries (`query`).
3. Run `npx convex dev --once` to deploy.
4. Create `app/services/<table>.py` with a FastAPI `app` and endpoints using `httpx`.
5. Add `tests/test_<table>.py` following the existing pattern.
