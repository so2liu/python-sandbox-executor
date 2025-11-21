import os
import sys
from pathlib import Path

os.environ.setdefault("FAKE_REDIS", "1")
os.environ.setdefault("INLINE_WORKER", "1")

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
