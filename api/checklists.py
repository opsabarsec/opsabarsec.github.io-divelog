# Vercel serverless entry point for the checklists API.
# Vercel detects the `app` variable (ASGI) and serves it.
from app.services.checklists import app  # noqa: F401
