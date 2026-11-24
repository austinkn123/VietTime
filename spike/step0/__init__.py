"""Step 0 feasibility test: ears, brain and voice running together on Austin's PC.

The personas, prompts and engines are the app server's own (server/viettime_server),
so this test measures exactly what the app will run.
"""

import sys
from pathlib import Path

_SERVER = Path(__file__).resolve().parents[2] / "server"
if str(_SERVER) not in sys.path:
    sys.path.insert(0, str(_SERVER))
