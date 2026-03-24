"""GitHub integration — convert issues to fleet tasks."""

from typing import Any

import structlog

logger = structlog.get_logger()


def issue_to_task(payload: dict[str, Any]) -> dict[str, str]:
    """Convert a GitHub issue webhook payload to a fleet task description."""
    issue = payload.get("issue", {})
    repo = payload.get("repository", {})

    title = issue.get("title", "Untitled")
    body = issue.get("body", "")
    repo_name = repo.get("full_name", "")
    clone_url = repo.get("clone_url", "")
    issue_number = issue.get("number", 0)

    # Build task description from issue
    description = f"GitHub Issue #{issue_number}: {title}"
    if body:
        description += f"\n\n{body}"

    # Detect workflow from labels
    labels = [lbl.get("name", "") for lbl in issue.get("labels", [])]
    workflow = "default"
    if "backend-only" in labels:
        workflow = "two-stage"

    logger.info(
        "issue_converted",
        repo=repo_name,
        issue=issue_number,
        workflow=workflow,
    )

    return {
        "repo": clone_url or repo_name,
        "description": description,
        "workflow": workflow,
        "issue_number": str(issue_number),
        "repo_name": repo_name,
    }
