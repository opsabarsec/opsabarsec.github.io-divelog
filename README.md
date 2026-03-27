![Dive Log App Hero Image](./assets/hero-dive.jpg)

# DiveLog Web APP — Free & Open Source Digital Dive Logbook

Filling in a paper logbook after every dive takes **10–15 minutes**: writing dive details, getting the club stamp, noting the species you spotted. That is a boring part of the process and you need to remember to bring it in the backpack for every diving holiday. And you need a separate logbook if you do freediving on the side of scuba diving.

**DiveLog** replaces the paper book with a web app you can reach from any device, anywhere. It adds the option to log dives without bottles. Automatizes the logging process and uses AI fish identification.

Key features and autimatization:

- **Automatic geolocation** — type a location name, get GPS coordinates and an OpenStreetMap link instantly
- **Automatic fish identification** — upload a photo of a fish and the species is identified and added to your notes by calling the API endpoint from https://www.fishial.ai/
- **Club website lookup** — the club's official website is found and linked automatically
- **Photo upload** — attach dive photos as digital proof, viewable full-screen on mobile
- **Accessible anywhere** — phone, tablet, or desktop, online or shared with your instructor

The app is **free and open source** (MIT licence). No subscription, no vendor lock-in — host it yourself or fork it. You will just need to create a convex account, get free API keys for geolocation at https://www.geoapify.com/ and fishal.ai and the folders/files structure is made to be easily deployed for free on https://www.vercel.ai . All env variables to be added are documented in the file env_example.txt

---

## Backend

**Stack:** Python 3.12 · FastAPI · Convex · httpx · Pydantic v2

The REST API is built with [FastAPI](https://fastapi.tiangolo.com/) and deployed on Vercel. [Convex](https://www.convex.dev/) acts as the database and file storage backend — no SQL migrations needed, just TypeScript schema files.

### Services

| Service | What it does |
|---------|-------------|
| **Geolocation** (`geolocation.py`) | Resolves a location name to GPS coordinates and an OSM link via Nominatim (OpenStreetMap). Rate-limited to 1 req/s, results cached 24 h. |
| **Club website lookup** (`search_club_website.py`) | Searches the web for a dive club's official website and returns the URL. |
| **Fish identification** (`fish_finder.py`) | Sends a photo to the [Fishial AI API](https://fishial.ai/) and returns the most probable species with a confidence score. |

### Key API endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/dives/upsert` | Create or update a dive record (auto-enriches coords, OSM link, club website) |
| GET | `/dives/{id}` | Fetch a dive by Convex ID |
| POST | `/upload-photos` | Upload one or more photos → returns `photo_storage_ids` |
| GET | `/download-photo/{id}` | Retrieve a photo (307 redirect to signed Convex URL) |
| POST | `/identify-fish` | Identify fish species in an image |
| POST | `/resolve-dive-metadata` | Preview geocoords + club website before submitting |
| GET | `/search-club?q=...` | Look up a club website manually |

### Environment variables

```env
CONVEX_URL=https://<deployment>.convex.cloud
MY_EMAIL=you@example.com          # Nominatim User-Agent compliance
FISHAL_API_ID=your_api_id
FISHAL_API_KEY=your_api_key
```

### Running locally

```bash
uv venv && source .venv/bin/activate
uv pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
npx convex dev --once              # deploy Convex schema & functions
```

---

## Frontend

**Stack:** Vanilla HTML · CSS · JavaScript — no build step, no framework

The frontend is a single-page app served as static files from [GitHub Pages](https://pages.github.com/). It communicates with the FastAPI backend via `fetch`.

### Features

- **My Dives** — paginated list of dive mini-cards; click any card to open a full detail view
- **Log / Edit Dive** — modal form with all dive fields; dive number auto-increments from the last entry; club website auto-filled (editable if wrong)
- **Photo lightbox** — tap any dive photo to view it full-screen with a close button; works on mobile
- **Fish ID in notes** — additional photos (after the cover photo) are each sent to the fish identification API; results appear in the dive notes as `fish1: Sphyraena viridensis (98%), fish2: ...`
- **Certifications & Checklists** — separate views for certifications and Google Doc/Sheet checklist links

### File layout

```
frontend/
├── index.html   # single HTML file — all modals and views
├── app.js       # all UI logic — rendering, API calls, state
└── styles.css   # CSS variables, responsive layout, lightbox, card styles
```

---

## Project structure

```
dive-log-app/
├── app/
│   ├── main.py (or divelog.py)         # FastAPI app — all dive endpoints
│   └── services/
│       ├── geolocation.py
│       ├── search_club_website.py
│       └── fish_finder.py
├── convex/
│   ├── schema.ts                        # table definitions (source of truth)
│   ├── dives.ts                         # upsertDive mutation, getDiveById query
│   ├── checklists.ts                    # checklist CRUD
│   └── files.ts                         # photo storage
├── frontend/
│   ├── index.html
│   ├── app.js
│   └── styles.css
└── tests/
```

---

## Contributing

Contributions are welcome — fork, branch, PR.

## License

MIT — free for personal and commercial use.

## Author

Marco Berta — https://github.com/opsabarsec

---

**Happy diving!** 🐠🌊
