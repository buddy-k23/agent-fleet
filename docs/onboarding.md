# Project Onboarding Guide

## What is fleet init?

`fleet init` scans your codebase and recommends the optimal agent + workflow configuration.

## Usage

```bash
fleet init --repo /path/to/your/project
```

## Example Output

```
🔍 Scanning /path/to/fabric-platform...
  Languages:  Java, TypeScript
  Frameworks: Spring Boot, React
  Tests:      JUnit, Playwright
  Database:   Oracle
  CI:         none
  CLAUDE.md:  Found ✓
  LOC:        ~45,000

🤖 Recommended agents: (6)
  Architect          Claude Sonnet — designs solutions
  Backend Dev        Claude Sonnet — Spring Boot + JdbcTemplate
  Frontend Dev       Claude Sonnet — React + MUI
  Reviewer           Claude Sonnet — code review
  Tester             Claude Haiku  — JUnit + Playwright
  Integrator         (no LLM)

📋 Recommended workflow: Full Development Pipeline
  plan → [backend ∥ frontend] → review → e2e → deliver
```

## What the Scanner Detects

| Category | How it detects |
|----------|---------------|
| Languages | File extensions (.py, .java, .ts, .go, .rs) |
| Frameworks | Config files (pom.xml, package.json, manage.py) + dependency names |
| Tests | pytest (conftest.py), jest (jest.config), playwright, vitest |
| CI | .github/workflows, .gitlab-ci.yml, Jenkinsfile |
| Database | .env files, docker-compose, application.yml |
| Package managers | Lock files (package-lock, yarn.lock, poetry.lock) |

## Agent Recommendations

| Stack | Agents | Notes |
|-------|--------|-------|
| Python backend | 5 agents (no frontend) | Backend-only pipeline |
| Full-stack (React) | 6 agents | Parallel backend + frontend |
| Java + Spring | 5-6 agents | Java-specific prompts |
| No tests | 4 agents | Minimal pipeline |

**Key:** Reviewer always uses Sonnet (Haiku scores too harshly).

## CLAUDE.md Generation

If no CLAUDE.md exists, fleet init can generate one with:
- Build & test commands (from package manager)
- Framework-specific architecture principles
- Known pitfalls (from our database of 5 frameworks)
- Commit conventions

## UI Onboarding Wizard

Go to **Projects** page → **Add Project** → 4-step wizard:
1. Enter repo path
2. View detected stack
3. Review recommended agents
4. Confirm and save
