"""Codebase scanner — detect languages, frameworks, tests, CI, databases."""

import json
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

import structlog

logger = structlog.get_logger()


@dataclass
class ProjectProfile:
    """Complete profile of a scanned project."""

    name: str
    repo_path: str
    languages: list[str] = field(default_factory=list)
    frameworks: list[str] = field(default_factory=list)
    test_frameworks: list[str] = field(default_factory=list)
    databases: list[str] = field(default_factory=list)
    package_managers: list[str] = field(default_factory=list)
    has_ci: bool = False
    ci_platform: str | None = None
    has_claude_md: bool = False
    has_docker: bool = False
    estimated_loc: int = 0
    entry_points: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


# Directories to skip during scanning
SKIP_DIRS = {
    "node_modules",
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    ".fleet-worktrees",
    "dist",
    "build",
    "target",
    ".next",
    ".nuxt",
    "vendor",
    ".tox",
    "egg-info",
}

# File extension → language mapping
EXT_TO_LANG: dict[str, str] = {
    ".py": "python",
    ".java": "java",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".js": "javascript",
    ".jsx": "javascript",
    ".go": "go",
    ".rs": "rust",
    ".rb": "ruby",
    ".cs": "csharp",
    ".kt": "kotlin",
    ".swift": "swift",
    ".php": "php",
    ".scala": "scala",
}


def _iter_files(root: Path) -> list[Path]:
    """Iterate source files, skipping common non-source directories."""
    files: list[Path] = []
    for item in root.rglob("*"):
        if any(skip in item.parts for skip in SKIP_DIRS):
            continue
        if item.is_file() and item.suffix in EXT_TO_LANG:
            files.append(item)
    return files


def detect_languages(root: Path) -> list[str]:
    """Detect programming languages by file extension count.

    Returns sorted list with primary (most files) language first.
    """
    counter: Counter[str] = Counter()
    for f in _iter_files(root):
        lang = EXT_TO_LANG.get(f.suffix)
        if lang:
            counter[lang] += 1

    # Sort by count descending
    return [lang for lang, _ in counter.most_common()]


def detect_frameworks(root: Path) -> list[str]:
    """Detect frameworks from config files and dependencies."""
    frameworks: list[str] = []

    # Check package.json (JS/TS frameworks)
    pkg_json = root / "package.json"
    if pkg_json.exists():
        try:
            pkg = json.loads(pkg_json.read_text())
            deps = {
                **pkg.get("dependencies", {}),
                **pkg.get("devDependencies", {}),
            }
            if "next" in deps:
                frameworks.append("nextjs")
            elif "react" in deps:
                frameworks.append("react")
            if "vue" in deps:
                frameworks.append("vue")
            if "nuxt" in deps:
                frameworks.append("nuxt")
            if "svelte" in deps:
                frameworks.append("svelte")
            if "@angular/core" in deps:
                frameworks.append("angular")
        except (json.JSONDecodeError, OSError):
            pass

    # Check Python frameworks
    for pyfile in ["pyproject.toml", "requirements.txt", "setup.py", "Pipfile"]:
        path = root / pyfile
        if path.exists():
            try:
                content = path.read_text().lower()
                if "fastapi" in content:
                    frameworks.append("fastapi")
                if "django" not in content and (root / "manage.py").exists():
                    frameworks.append("django")
                if "flask" in content:
                    frameworks.append("flask")
            except OSError:
                pass

    # Django by manage.py
    if (root / "manage.py").exists() and "django" not in frameworks:
        frameworks.append("django")

    # Spring Boot (pom.xml)
    pom = root / "pom.xml"
    if pom.exists():
        try:
            content = pom.read_text().lower()
            if "spring-boot" in content:
                frameworks.append("spring-boot")
        except OSError:
            pass

    # Gradle Spring Boot
    gradle = root / "build.gradle"
    if gradle.exists():
        try:
            content = gradle.read_text().lower()
            if "spring-boot" in content:
                frameworks.append("spring-boot")
        except OSError:
            pass

    # Go
    if (root / "go.mod").exists():
        frameworks.append("go-module")

    # Rust
    if (root / "Cargo.toml").exists():
        frameworks.append("rust-cargo")

    return list(dict.fromkeys(frameworks))  # dedupe preserving order


def detect_tests(root: Path) -> list[str]:
    """Detect test frameworks from config files."""
    tests: list[str] = []

    # pytest
    pyproject = root / "pyproject.toml"
    if pyproject.exists():
        try:
            if "pytest" in pyproject.read_text().lower():
                tests.append("pytest")
        except OSError:
            pass
    if (root / "conftest.py").exists() and "pytest" not in tests:
        tests.append("pytest")

    # jest
    for name in ["jest.config.js", "jest.config.ts", "jest.config.mjs"]:
        if (root / name).exists():
            tests.append("jest")
            break
    if "jest" not in tests:
        pkg = root / "package.json"
        if pkg.exists():
            try:
                if '"jest"' in pkg.read_text():
                    tests.append("jest")
            except OSError:
                pass

    # vitest
    for name in ["vitest.config.ts", "vitest.config.js"]:
        if (root / name).exists():
            tests.append("vitest")
            break

    # playwright
    for name in ["playwright.config.ts", "playwright.config.js"]:
        if (root / name).exists():
            tests.append("playwright")
            break

    return list(dict.fromkeys(tests))


def detect_ci(root: Path) -> str | None:
    """Detect CI/CD platform from config files."""
    if (root / ".github" / "workflows").is_dir():
        return "github-actions"
    if (root / ".gitlab-ci.yml").exists():
        return "gitlab-ci"
    if (root / "Jenkinsfile").exists():
        return "jenkins"
    if (root / ".circleci" / "config.yml").exists():
        return "circleci"
    return None


def detect_package_manager(root: Path) -> list[str]:
    """Detect package managers from lock files and config."""
    managers: list[str] = []

    if (root / "package-lock.json").exists():
        managers.append("npm")
    if (root / "yarn.lock").exists():
        managers.append("yarn")
    if (root / "pnpm-lock.yaml").exists():
        managers.append("pnpm")
    if (root / "requirements.txt").exists() or (root / "pyproject.toml").exists():
        managers.append("pip")
    if (root / "poetry.lock").exists():
        managers.append("poetry")
    if (root / "pom.xml").exists():
        managers.append("maven")
    if (root / "build.gradle").exists() or (root / "build.gradle.kts").exists():
        managers.append("gradle")
    if (root / "Cargo.toml").exists():
        managers.append("cargo")

    return managers


def detect_database(root: Path) -> list[str]:
    """Detect databases from config files and dependencies."""
    databases: list[str] = []

    # Check .env and config files for DB URLs
    for name in [".env", ".env.example", "application.yml", "application.properties"]:
        path = root / name
        if path.exists():
            try:
                content = path.read_text().lower()
                if "sqlite" in content:
                    databases.append("sqlite")
                if "postgres" in content or "postgresql" in content:
                    databases.append("postgres")
                if "mysql" in content:
                    databases.append("mysql")
                if "oracle" in content:
                    databases.append("oracle")
                if "mongodb" in content or "mongo" in content:
                    databases.append("mongodb")
            except OSError:
                pass

    # Check docker-compose for DB services
    for name in ["docker-compose.yml", "docker-compose.yaml", "compose.yml"]:
        path = root / name
        if path.exists():
            try:
                content = path.read_text().lower()
                if "postgres" in content:
                    databases.append("postgres")
                if "mysql" in content:
                    databases.append("mysql")
                if "mongo" in content:
                    databases.append("mongodb")
                if "redis" in content:
                    databases.append("redis")
            except OSError:
                pass

    return list(dict.fromkeys(databases))


def estimate_loc(root: Path) -> int:
    """Estimate lines of code (non-empty lines in source files)."""
    total = 0
    count = 0
    for f in _iter_files(root):
        if count >= 200:  # Sample limit for speed
            break
        try:
            lines = f.read_text(errors="ignore").splitlines()
            total += sum(1 for line in lines if line.strip())
            count += 1
        except OSError:
            pass
    return total


def scan_project(root: Path) -> ProjectProfile:
    """Scan a project and return a complete ProjectProfile."""
    root = root.resolve()
    name = root.name

    ci_platform = detect_ci(root)

    profile = ProjectProfile(
        name=name,
        repo_path=str(root),
        languages=detect_languages(root),
        frameworks=detect_frameworks(root),
        test_frameworks=detect_tests(root),
        databases=detect_database(root),
        package_managers=detect_package_manager(root),
        has_ci=ci_platform is not None,
        ci_platform=ci_platform,
        has_claude_md=(root / "CLAUDE.md").exists(),
        has_docker=(root / "Dockerfile").exists() or (root / "docker-compose.yml").exists(),
        estimated_loc=estimate_loc(root),
    )

    logger.info(
        "project_scanned",
        name=name,
        languages=profile.languages,
        frameworks=profile.frameworks,
    )

    return profile
