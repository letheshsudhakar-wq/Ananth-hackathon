"""
Root conftest — ensures the repository root is importable when pytest is run
from the repo root (so `src.*` and `app.*` resolve for both backend and
Phase 2 (Member 3) tests).
"""
import os
import sys

_REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)
