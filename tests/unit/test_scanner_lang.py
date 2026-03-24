"""Tests for language + framework detection."""

from pathlib import Path

from agent_fleet.onboarding.scanner import detect_frameworks, detect_languages


class TestDetectLanguages:
    def test_detects_python(self, tmp_path: Path) -> None:
        (tmp_path / "main.py").write_text("print('hello')")
        (tmp_path / "utils.py").write_text("def foo(): pass")
        result = detect_languages(tmp_path)
        assert "python" in result

    def test_detects_typescript(self, tmp_path: Path) -> None:
        (tmp_path / "App.tsx").write_text("export default function App() {}")
        (tmp_path / "index.ts").write_text("console.log('hi')")
        result = detect_languages(tmp_path)
        assert "typescript" in result

    def test_detects_java(self, tmp_path: Path) -> None:
        src = tmp_path / "src" / "Main.java"
        src.parent.mkdir(parents=True)
        src.write_text("public class Main {}")
        result = detect_languages(tmp_path)
        assert "java" in result

    def test_primary_language_first(self, tmp_path: Path) -> None:
        for i in range(5):
            (tmp_path / f"file{i}.py").write_text("pass")
        (tmp_path / "one.ts").write_text("x")
        result = detect_languages(tmp_path)
        assert result[0] == "python"

    def test_empty_directory(self, tmp_path: Path) -> None:
        result = detect_languages(tmp_path)
        assert result == []

    def test_ignores_node_modules(self, tmp_path: Path) -> None:
        nm = tmp_path / "node_modules" / "pkg"
        nm.mkdir(parents=True)
        (nm / "index.js").write_text("module.exports = {}")
        (tmp_path / "app.py").write_text("pass")
        result = detect_languages(tmp_path)
        assert "javascript" not in result
        assert "python" in result


class TestDetectFrameworks:
    def test_detects_react(self, tmp_path: Path) -> None:
        pkg = tmp_path / "package.json"
        pkg.write_text('{"dependencies": {"react": "^18.0.0"}}')
        result = detect_frameworks(tmp_path)
        assert "react" in result

    def test_detects_fastapi(self, tmp_path: Path) -> None:
        req = tmp_path / "pyproject.toml"
        req.write_text('[project]\ndependencies = ["fastapi>=0.100"]')
        result = detect_frameworks(tmp_path)
        assert "fastapi" in result

    def test_detects_spring_boot(self, tmp_path: Path) -> None:
        pom = tmp_path / "pom.xml"
        pom.write_text(
            "<project><parent><artifactId>spring-boot-starter-parent</artifactId></parent></project>"
        )
        result = detect_frameworks(tmp_path)
        assert "spring-boot" in result

    def test_detects_django(self, tmp_path: Path) -> None:
        (tmp_path / "manage.py").write_text("#!/usr/bin/env python")
        result = detect_frameworks(tmp_path)
        assert "django" in result

    def test_detects_nextjs(self, tmp_path: Path) -> None:
        pkg = tmp_path / "package.json"
        pkg.write_text('{"dependencies": {"next": "^14.0", "react": "^18"}}')
        result = detect_frameworks(tmp_path)
        assert "nextjs" in result

    def test_detects_vue(self, tmp_path: Path) -> None:
        pkg = tmp_path / "package.json"
        pkg.write_text('{"dependencies": {"vue": "^3.0"}}')
        result = detect_frameworks(tmp_path)
        assert "vue" in result

    def test_detects_flask(self, tmp_path: Path) -> None:
        req = tmp_path / "requirements.txt"
        req.write_text("flask>=2.0\nflask-cors\n")
        result = detect_frameworks(tmp_path)
        assert "flask" in result

    def test_no_framework(self, tmp_path: Path) -> None:
        (tmp_path / "main.py").write_text("print('plain script')")
        result = detect_frameworks(tmp_path)
        assert result == []
