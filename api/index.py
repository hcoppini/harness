import os
import sys
from pathlib import Path

# Mark environment as Vercel serverless
os.environ["VERCEL"] = "1"

# Add root directory to path for Python module resolution
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from server import app

