"""Root pytest bootstrap: put each app on sys.path so tests run without PYTHONPATH setup."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
for app in ("demo_ui", "conversation", "seedance", "t1_monitor"):
    sys.path.insert(0, str(ROOT / "apps" / app))
