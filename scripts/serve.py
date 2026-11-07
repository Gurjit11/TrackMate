import sys
from pathlib import Path
import uvicorn

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.main import app

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 TrackMate Web Application starting on http://localhost:8000")
    print("   Open your browser and navigate to http://localhost:8000")
    print("=" * 60)
    uvicorn.run(app, host="127.0.0.1", port=8000)
