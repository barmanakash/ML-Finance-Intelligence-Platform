"""Bootstrap the repository root onto sys.path for local backend runs.

When the backend is launched from the backend/ directory (for example:
    cd backend
    python -m uvicorn app.main:app
), the repo root is not automatically on sys.path. That prevents imports like
`ml.*` from resolving even though the ML package lives alongside `backend/` in the
workspace.

This small startup shim keeps local execution consistent with Docker and the
project-root validation flow, without changing app runtime behavior.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
