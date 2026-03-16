"""CLAUDE.md generator — auto-generate from ProjectProfile."""

from agent_fleet.onboarding.scanner import ProjectProfile

# Build command templates
BUILD_COMMANDS: dict[str, dict[str, str]] = {
    "pip": {"install": "pip install -e '.[dev]'", "test": "pytest", "lint": "ruff check src/"},
    "poetry": {"install": "poetry install", "test": "poetry run pytest", "lint": "ruff check src/"},
    "npm": {"install": "npm install", "test": "npm test", "lint": "npm run lint"},
    "yarn": {"install": "yarn install", "test": "yarn test", "lint": "yarn lint"},
    "maven": {"install": "mvn clean install -DskipTests", "test": "mvn test", "lint": ""},
    "gradle": {"install": "gradle build -x test", "test": "gradle test", "lint": ""},
    "cargo": {"install": "cargo build", "test": "cargo test", "lint": "cargo clippy"},
}


def generate_claude_md(profile: ProjectProfile) -> str:
    """Generate a CLAUDE.md from a ProjectProfile."""
    sections: list[str] = []

    # Header
    sections.append(f"# {profile.name} — Claude Instructions\n")

    # Overview
    stack = ", ".join(profile.frameworks or profile.languages)
    sections.append("## Project Overview\n")
    sections.append(f"**Stack:** {stack}")
    sections.append(f"**Languages:** {', '.join(profile.languages)}")
    if profile.databases:
        sections.append(f"**Database:** {', '.join(profile.databases)}")
    sections.append("")

    # Build & Test Commands
    sections.append("## Build & Test Commands\n")
    sections.append("```bash")
    for pm in profile.package_managers:
        cmds = BUILD_COMMANDS.get(pm, {})
        if cmds.get("install"):
            sections.append(f"# Install\n{cmds['install']}\n")
        if cmds.get("test"):
            sections.append(f"# Test\n{cmds['test']}\n")
        if cmds.get("lint"):
            sections.append(f"# Lint\n{cmds['lint']}\n")
    sections.append("```\n")

    # Key Directories
    sections.append("## Key Directories\n")
    sections.append("| Path | Purpose |")
    sections.append("|------|---------|")
    if "python" in profile.languages:
        sections.append("| `src/` | Source code |")
        sections.append("| `tests/` | Test files |")
    if any(f in profile.frameworks for f in ["react", "vue", "nextjs"]):
        sections.append("| `src/components/` | UI components |")
        sections.append("| `src/pages/` | Page components |")
    sections.append("")

    # Implementation Rules
    sections.append("## Implementation Rules\n")
    if "python" in profile.languages:
        sections.append("1. **Type hints everywhere** — all function signatures")
        sections.append("2. **Tests first** — write failing tests before implementation")
    if "typescript" in profile.languages:
        sections.append("1. **TypeScript strict** — no `any` types")
        sections.append("2. **data-testid** on all interactive UI elements")
    if any(f in profile.frameworks for f in ["react", "vue", "nextjs"]):
        sections.append("3. **No CSS class selectors in tests** — use data-testid only")
    sections.append("")

    # Commit Convention
    sections.append("## Commit Convention\n")
    sections.append("```")
    sections.append("feat(scope): description")
    sections.append("fix(scope): description")
    sections.append("test(scope): description")
    sections.append("```\n")

    return "\n".join(sections)
