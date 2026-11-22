"""Keep nested fixture imports working during repository-wide pytest collection."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
