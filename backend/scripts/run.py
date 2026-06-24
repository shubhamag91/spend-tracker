import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import uvicorn

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    # Bind to localhost only — this serves real financial data with no auth, so it
    # must not be reachable from the LAN. Override with HOST=0.0.0.0 only if you
    # understand the exposure.
    host = os.getenv("HOST", "127.0.0.1")
    uvicorn.run("app.main:app", host=host, port=port, reload=True)
