"""PII/PCI data scanner — detects sensitive data in source code."""

import re
from pathlib import Path
from typing import Any

import structlog

from agent_fleet.tools.base import BaseTool

logger = structlog.get_logger()

# PII detection patterns
PII_PATTERNS: dict[str, re.Pattern] = {  # type: ignore[type-arg]
    "credit_card": re.compile(r"\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13})\b"),
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "email_hardcoded": re.compile(r'["\'][\w.+-]+@[\w-]+\.[\w.]+["\']'),
    "phone": re.compile(r"\b(?:\+1[-.]?)?\(?\d{3}\)?[-.]?\d{3}[-.]?\d{4}\b"),
    "aws_key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "api_key_anthropic": re.compile(r"\bsk-ant-[a-zA-Z0-9_-]{20,}\b"),
    "api_key_openai": re.compile(r"\bsk-[a-zA-Z0-9]{20,}\b"),
    "private_key": re.compile(r"-----BEGIN (?:RSA |EC )?PRIVATE KEY-----"),
    "password_assignment": re.compile(r'(?:password|passwd|pwd)\s*=\s*["\'][^"\']{3,}["\']', re.I),
    "connection_string": re.compile(
        r"(?:jdbc|postgres|mysql|mongodb)://[^\s\"']+:[^\s\"']+@", re.I
    ),
}

# Directories to skip
SKIP_DIRS = {"node_modules", ".git", ".venv", "venv", "__pycache__", "dist", "build"}

# File extensions to scan
SCAN_EXTENSIONS = {
    ".py",
    ".java",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".yml",
    ".yaml",
    ".xml",
    ".json",
    ".env",
    ".properties",
    ".cfg",
    ".conf",
}


def scan_for_pii(root: Path) -> list[dict[str, Any]]:
    """Scan a directory for PII/PCI data patterns.

    Returns list of findings: [{file, line, type, severity, match}]
    """
    findings: list[dict[str, Any]] = []

    for filepath in root.rglob("*"):
        if any(skip in filepath.parts for skip in SKIP_DIRS):
            continue
        if not filepath.is_file() or filepath.suffix not in SCAN_EXTENSIONS:
            continue

        try:
            content = filepath.read_text(errors="ignore")
            rel_path = str(filepath.relative_to(root))

            for line_num, line in enumerate(content.splitlines(), 1):
                for pii_type, pattern in PII_PATTERNS.items():
                    if pattern.search(line):
                        severity = _get_severity(pii_type)
                        findings.append(
                            {
                                "file": rel_path,
                                "line": line_num,
                                "type": pii_type,
                                "severity": severity,
                                "match": line.strip()[:100],
                            }
                        )
        except OSError:
            continue

    logger.info("pii_scan_complete", findings=len(findings), root=str(root))
    return findings


def _get_severity(pii_type: str) -> str:
    """Map PII type to severity level."""
    critical = {"credit_card", "private_key", "connection_string", "aws_key"}
    high = {"ssn", "password_assignment", "api_key_anthropic", "api_key_openai"}
    if pii_type in critical:
        return "critical"
    if pii_type in high:
        return "high"
    return "medium"


class PIIScannerTool(BaseTool):
    """Tool for agents to scan for PII/PCI data."""

    def __init__(self, workspace_root: Path) -> None:
        self._root = workspace_root

    @property
    def name(self) -> str:
        return "pii_scan"

    @property
    def description(self) -> str:
        return "Scan code for PII/PCI data (credit cards, SSN, passwords, API keys)"

    def execute(self, input: dict[str, Any]) -> dict[str, Any]:
        findings = scan_for_pii(self._root)
        return {
            "total_findings": len(findings),
            "critical": len([f for f in findings if f["severity"] == "critical"]),
            "high": len([f for f in findings if f["severity"] == "high"]),
            "medium": len([f for f in findings if f["severity"] == "medium"]),
            "findings": findings[:50],  # Cap at 50 for context window
        }

    def schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {},
        }
