"""Allow `python -m rocketcfd` execution."""
from __future__ import annotations

from rocketcfd import main

if __name__ == "__main__":
    raise SystemExit(main())
