"""Tests for test setup, CI, and package manager detection."""

from pathlib import Path

from agent_fleet.onboarding.scanner import detect_ci, detect_package_manager, detect_tests


class TestDetectTests:
    def test_detects_pytest(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text("[tool.pytest.ini_options]\ntestpaths = ['tests']")
        assert "pytest" in detect_tests(tmp_path)

    def test_detects_pytest_by_conftest(self, tmp_path: Path) -> None:
        (tmp_path / "conftest.py").write_text("import pytest")
        assert "pytest" in detect_tests(tmp_path)

    def test_detects_jest(self, tmp_path: Path) -> None:
        (tmp_path / "jest.config.js").write_text("module.exports = {}")
        assert "jest" in detect_tests(tmp_path)

    def test_detects_playwright(self, tmp_path: Path) -> None:
        (tmp_path / "playwright.config.ts").write_text("export default {}")
        assert "playwright" in detect_tests(tmp_path)

    def test_detects_vitest(self, tmp_path: Path) -> None:
        (tmp_path / "vitest.config.ts").write_text("export default {}")
        assert "vitest" in detect_tests(tmp_path)

    def test_no_tests(self, tmp_path: Path) -> None:
        (tmp_path / "main.py").write_text("pass")
        assert detect_tests(tmp_path) == []


class TestDetectCI:
    def test_detects_github_actions(self, tmp_path: Path) -> None:
        wf = tmp_path / ".github" / "workflows"
        wf.mkdir(parents=True)
        (wf / "ci.yml").write_text("on: push")
        assert detect_ci(tmp_path) == "github-actions"

    def test_detects_gitlab_ci(self, tmp_path: Path) -> None:
        (tmp_path / ".gitlab-ci.yml").write_text("stages: [build]")
        assert detect_ci(tmp_path) == "gitlab-ci"

    def test_detects_jenkins(self, tmp_path: Path) -> None:
        (tmp_path / "Jenkinsfile").write_text("pipeline {}")
        assert detect_ci(tmp_path) == "jenkins"

    def test_no_ci(self, tmp_path: Path) -> None:
        (tmp_path / "main.py").write_text("pass")
        assert detect_ci(tmp_path) is None


class TestDetectPackageManager:
    def test_detects_npm(self, tmp_path: Path) -> None:
        (tmp_path / "package-lock.json").write_text("{}")
        assert "npm" in detect_package_manager(tmp_path)

    def test_detects_yarn(self, tmp_path: Path) -> None:
        (tmp_path / "yarn.lock").write_text("")
        assert "yarn" in detect_package_manager(tmp_path)

    def test_detects_pip(self, tmp_path: Path) -> None:
        (tmp_path / "requirements.txt").write_text("flask")
        assert "pip" in detect_package_manager(tmp_path)

    def test_detects_poetry(self, tmp_path: Path) -> None:
        (tmp_path / "poetry.lock").write_text("")
        assert "poetry" in detect_package_manager(tmp_path)

    def test_detects_maven(self, tmp_path: Path) -> None:
        (tmp_path / "pom.xml").write_text("<project/>")
        assert "maven" in detect_package_manager(tmp_path)

    def test_no_package_manager(self, tmp_path: Path) -> None:
        (tmp_path / "main.py").write_text("pass")
        assert detect_package_manager(tmp_path) == []
