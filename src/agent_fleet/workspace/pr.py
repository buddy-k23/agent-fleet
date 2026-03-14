"""PR provider — pluggable PR/MR creation for GitHub, GitLab, or local summary."""

import shutil
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path

import structlog

logger = structlog.get_logger()


class PRProvider(ABC):
    """Abstract base for PR/MR creation."""

    @abstractmethod
    def create_pr(
        self, repo_path: Path, branch: str, title: str, body: str
    ) -> str | None:
        """Create a PR/MR. Returns URL on success, None on failure."""
        ...


class GitHubPRProvider(PRProvider):
    """Creates PRs via the `gh` CLI."""

    def create_pr(
        self, repo_path: Path, branch: str, title: str, body: str
    ) -> str | None:
        result = subprocess.run(
            ["gh", "pr", "create", "--title", title, "--body", body, "--head", branch],
            cwd=str(repo_path),
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            url = result.stdout.strip()
            logger.info("pr_created", provider="github", url=url)
            return url
        logger.warning("pr_creation_failed", provider="github", error=result.stderr)
        return None


class GitLabPRProvider(PRProvider):
    """Creates MRs via the `glab` CLI."""

    def create_pr(
        self, repo_path: Path, branch: str, title: str, body: str
    ) -> str | None:
        result = subprocess.run(
            [
                "glab", "mr", "create",
                "--title", title,
                "--description", body,
                "--source-branch", branch,
            ],
            cwd=str(repo_path),
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            url = result.stdout.strip()
            logger.info("pr_created", provider="gitlab", url=url)
            return url
        logger.warning("pr_creation_failed", provider="gitlab", error=result.stderr)
        return None


class LocalSummaryProvider(PRProvider):
    """Writes a summary file instead of creating a PR. Always succeeds."""

    def create_pr(
        self, repo_path: Path, branch: str, title: str, body: str
    ) -> str | None:
        summary_path = repo_path / "fleet-summary.md"
        content = f"# {title}\n\n**Branch:** {branch}\n\n{body}\n"
        summary_path.write_text(content)
        logger.info("summary_written", path=str(summary_path))
        return None


def detect_provider(repo_path: Path) -> PRProvider:
    """Detect the git hosting provider and return the appropriate PRProvider."""
    if shutil.which("gh"):
        return GitHubPRProvider()
    if shutil.which("glab"):
        return GitLabPRProvider()
    return LocalSummaryProvider()


def generate_pr_body(
    description: str,
    workflow_name: str,
    total_tokens: int,
    stage_outputs: dict,
) -> str:
    """Generate a PR body from stage outputs."""
    lines = [
        "## Agent Fleet Task Summary",
        "",
        f"**Task:** {description}",
        f"**Workflow:** {workflow_name}",
        f"**Total tokens:** {total_tokens}",
        "",
        "### Stages",
        "",
    ]

    for stage_name, output in stage_outputs.items():
        title = stage_name.replace("-", " ").title()
        lines.append(f"#### {title}")

        if isinstance(output, dict):
            agent_output = output.get("output", "")
            files = output.get("files_changed", [])
            tokens = output.get("tokens_used", 0)

            if files:
                lines.append(f"Files changed: {', '.join(files)}")
            if tokens:
                lines.append(f"Tokens used: {tokens}")
            if agent_output:
                # Truncate long outputs
                summary = agent_output[:500]
                if len(agent_output) > 500:
                    summary += "..."
                lines.append(f"\n{summary}")
        else:
            lines.append(str(output))

        lines.append("")

    return "\n".join(lines)
