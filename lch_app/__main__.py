from __future__ import annotations

import os

from lch_app.server import run

if __name__ == "__main__":
    run(
        host=os.environ.get("LCH_HOST", "0.0.0.0"),
        port=int(os.environ.get("LCH_PORT", "43147")),
    )
