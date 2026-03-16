"""Codebase scanner — detect languages, frameworks, tests, CI, databases."""

import json
from collections import Counter
from pathlib import Path

import structlog

logger = structlog.get_logger()

# Directories to skip during scanning
SKIP_DIRS = {
    "node_modules", ".git", ".venv", "venv", "__pycache__", ".fleet-worktrees",
    "dist", "build", "target", ".next", ".nuxt", "vendor", ".tox", "egg-info",
}

# File extension → language mapping
EXT_TO_LANG: dict[str, str] = {
    ".py": "python", ".java": "java", ".ts": "typescript", ".tsx": "typescript",
    ".js": "javascript", ".jsx": "javascript", ".go": "go", ".rs": "rust",
    ".rb": "ruby", ".cs": "csharp", ".kt": "kotlin", ".swift": "swift",
    ".php": "php", ".scala": "scala",
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
