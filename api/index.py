"""Vercel Serverless Function entrypoint for the FastAPI backend.

Vercel discovers Python functions from the repository-root ``api`` directory.
The actual application remains in ``backend/app`` so local VPS/systemd deploys
and the Vercel deploy path share the same FastAPI app instance.
"""

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.app.main import app  # noqa: E402
