"""Entry point: python -m agent_fleet.worker"""

import json
import os
import sys
from datetime import datetime, timezone

from agent_fleet.worker import FleetWorker

HEARTBEAT_FILE = "/tmp/fleet-worker-heartbeat"


def main() -> None:
    """Start the fleet worker process."""
    if "--health" in sys.argv:
        try:
            with open(HEARTBEAT_FILE) as f:
                data = json.load(f)
            last_beat = datetime.fromisoformat(data["timestamp"])
            age_seconds = (datetime.now(timezone.utc) - last_beat).total_seconds()
            if age_seconds < 30:
                print("healthy")
                sys.exit(0)
            else:
                print(f"stale: {age_seconds:.0f}s since last heartbeat")
                sys.exit(1)
        except (FileNotFoundError, KeyError, ValueError) as e:
            print(f"unhealthy: {e}")
            sys.exit(1)

    worker = FleetWorker(
        max_concurrent_tasks=int(os.getenv("MAX_CONCURRENT_TASKS", "3")),
        poll_interval_seconds=float(os.getenv("POLL_INTERVAL_SECONDS", "3")),
    )
    worker.start()


if __name__ == "__main__":
    main()
