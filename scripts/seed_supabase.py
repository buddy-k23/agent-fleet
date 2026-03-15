"""Seed default agents and workflows into Supabase for a user."""

import json
import os
import sys
from pathlib import Path

import yaml

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from supabase import create_client  # noqa: E402


def load_yaml_agents(agents_dir: Path) -> list[dict]:
    """Load agent configs from YAML files."""
    agents = []
    for f in sorted(agents_dir.glob("*.yaml")):
        with open(f) as fh:
            data = yaml.safe_load(fh)
        agents.append(data)
    return agents


def load_yaml_workflow(path: Path) -> dict:
    """Load a workflow from YAML."""
    with open(path) as f:
        return yaml.safe_load(f)


def seed(user_id: str) -> None:
    """Seed default agents and workflows for a user."""
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    client = create_client(url, key)

    config_dir = Path(__file__).parent.parent / "config"

    # Seed agents
    print("Seeding agents...")
    agents = load_yaml_agents(config_dir / "agents")
    for agent in agents:
        # Check if already exists
        existing = (
            client.table("agents")
            .select("id")
            .eq("user_id", user_id)
            .eq("name", agent["name"])
            .execute()
        )
        if existing.data:
            print(f"  {agent['name']:20s} already exists, skipping")
            continue

        client.table("agents").insert({
            "user_id": user_id,
            "name": agent["name"],
            "description": agent.get("description", ""),
            "model": agent.get("default_model", "anthropic/claude-sonnet-4-6"),
            "tools": agent.get("tools", []),
            "capabilities": agent.get("capabilities", []),
            "system_prompt": agent.get("system_prompt", ""),
            "max_retries": agent.get("max_retries", 2),
            "timeout_minutes": agent.get("timeout_minutes", 30),
            "max_tokens": agent.get("max_tokens", 100000),
            "can_delegate": agent.get("can_delegate", []),
        }).execute()
        print(f"  {agent['name']:20s} seeded")

    # Seed workflows
    print("\nSeeding workflows...")
    for wf_file in ["default.yaml", "two-stage.yaml"]:
        wf_path = config_dir / "workflows" / wf_file
        if not wf_path.exists():
            continue
        wf = load_yaml_workflow(wf_path)

        existing = (
            client.table("workflows")
            .select("id")
            .eq("user_id", user_id)
            .eq("name", wf["name"])
            .execute()
        )
        if existing.data:
            print(f"  {wf['name']:40s} already exists, skipping")
            continue

        client.table("workflows").insert({
            "user_id": user_id,
            "name": wf["name"],
            "stages": json.loads(json.dumps(wf.get("stages", []))),
            "concurrency": wf.get("concurrency", 1),
            "max_cost_usd": wf.get("max_cost_usd"),
            "classifier_mode": wf.get("classifier_mode", "suggest"),
        }).execute()
        print(f"  {wf['name']:40s} seeded")

    print("\nDone!")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/seed_supabase.py <user_id>")
        print("\nFind user_id: Supabase Dashboard → Authentication → Users")
        sys.exit(1)
    seed(sys.argv[1])
