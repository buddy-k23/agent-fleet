"""Root conftest — ensure the local src/ directory takes precedence."""

import sys
from pathlib import Path

# Insert the worktree's src/ at the front of sys.path so that local
# changes are picked up before the installed (editable or otherwise)
# package from the shared .venv.
_src = str(Path(__file__).parent / "src")
if _src not in sys.path:
    sys.path.insert(0, _src)
