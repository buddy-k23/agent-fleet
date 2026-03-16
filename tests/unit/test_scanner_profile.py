"""Tests for database detection, LOC, and ProjectProfile."""

from pathlib import Path

from agent_fleet.onboarding.scanner import (
    ProjectProfile,
    detect_database,
    estimate_loc,
    scan_project,
)


class TestDetectDatabase:
    def test_detects_sqlite(self, tmp_path: Path) -> None:
        (tmp_path / ".env").write_text("DATABASE_URL=sqlite:///./app.db")
        assert "sqlite" in detect_database(tmp_path)

    def test_detects_postgres(self, tmp_path: Path) -> None:
        (tmp_path / "docker-compose.yml").write_text("image: postgres:15")
        assert "postgres" in detect_database(tmp_path)

    def test_no_database(self, tmp_path: Path) -> None:
        (tmp_path / "main.py").write_text("pass")
        assert detect_database(tmp_path) == []


class TestEstimateLOC:
    def test_counts_lines(self, tmp_path: Path) -> None:
        (tmp_path / "a.py").write_text("line1\nline2\nline3\n")
        (tmp_path / "b.py").write_text("x\ny\n")
        assert estimate_loc(tmp_path) == 5

    def test_skips_empty_lines(self, tmp_path: Path) -> None:
        (tmp_path / "a.py").write_text("line1\n\n\nline2\n")
        assert estimate_loc(tmp_path) == 2

    def test_empty_dir(self, tmp_path: Path) -> None:
        assert estimate_loc(tmp_path) == 0


class TestScanProject:
    def test_scan_returns_profile(self, tmp_path: Path) -> None:
        (tmp_path / "main.py").write_text("from fastapi import FastAPI\napp = FastAPI()")
        toml = (
            '[project]\ndependencies = ["fastapi"]\n\n'
            '[tool.pytest.ini_options]\ntestpaths = ["tests"]'
        )
        (tmp_path / "pyproject.toml").write_text(toml)
        profile = scan_project(tmp_path)
        assert isinstance(profile, ProjectProfile)
        assert "python" in profile.languages
        assert "fastapi" in profile.frameworks
        assert "pytest" in profile.test_frameworks
        assert profile.estimated_loc > 0

    def test_scan_detects_claude_md(self, tmp_path: Path) -> None:
        (tmp_path / "CLAUDE.md").write_text("# Rules")
        (tmp_path / "main.py").write_text("pass")
        profile = scan_project(tmp_path)
        assert profile.has_claude_md is True

    def test_scan_detects_docker(self, tmp_path: Path) -> None:
        (tmp_path / "Dockerfile").write_text("FROM python:3.12")
        (tmp_path / "main.py").write_text("pass")
        profile = scan_project(tmp_path)
        assert profile.has_docker is True
