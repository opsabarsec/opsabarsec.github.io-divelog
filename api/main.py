# Vercel serverless entry point for the main dive log API.
# Vercel detects the `app` variable (ASGI) and serves it.
from app.main import app  # noqa: F401
