"""Agent + workflow recommendation based on ProjectProfile."""

from agent_fleet.onboarding.scanner import ProjectProfile


def recommend_agents(profile: ProjectProfile) -> list[dict]:
    """Recommend agents based on detected tech stack."""
    agents: list[dict] = []
    has_frontend = any(
        f in profile.frameworks for f in ["react", "vue", "nextjs", "nuxt", "angular", "svelte"]
    )

    # Architect — always included
    agents.append(
        {
            "name": "Architect",
            "model": "anthropic/claude-sonnet-4-6",
            "tools": ["code", "search"],
            "prompt_hint": (
                f"This is a {', '.join(profile.frameworks or profile.languages)} project."
            ),
        }
    )

    # Backend Dev
    framework = next(
        (
            f
            for f in profile.frameworks
            if f
            not in [
                "react",
                "vue",
                "nextjs",
                "nuxt",
                "angular",
                "svelte",
            ]
        ),
        profile.languages[0] if profile.languages else "general",
    )
    agents.append(
        {
            "name": "Backend Dev",
            "model": "anthropic/claude-sonnet-4-6",
            "tools": ["code", "shell"],
            "prompt_hint": f"You work with {framework}. Follow {framework} conventions.",
        }
    )

    # Frontend Dev — only if frontend detected
    if has_frontend:
        fe_framework = next(
            (
                f
                for f in profile.frameworks
                if f
                in [
                    "react",
                    "vue",
                    "nextjs",
                    "nuxt",
                    "angular",
                    "svelte",
                ]
            ),
            "frontend",
        )
        agents.append(
            {
                "name": "Frontend Dev",
                "model": "anthropic/claude-sonnet-4-6",
                "tools": ["code", "shell", "browser"],
                "prompt_hint": f"You specialize in {fe_framework}.",
            }
        )

    # Reviewer — always, use Sonnet (Haiku scores too harshly)
    agents.append(
        {
            "name": "Reviewer",
            "model": "anthropic/claude-sonnet-4-6",
            "tools": ["code", "search"],
            "prompt_hint": "Score working code with passing tests at least 80.",
        }
    )

    # Tester — use Haiku (just runs tests)
    test_cmd = "pytest" if "pytest" in profile.test_frameworks else "npm test"
    agents.append(
        {
            "name": "Tester",
            "model": "anthropic/claude-haiku-4-5-20251001",
            "tools": ["code", "shell"],
            "prompt_hint": f"Run tests with `{test_cmd}`. Report results. Do not write docs.",
        }
    )

    # Integrator — always, no LLM
    agents.append(
        {
            "name": "Integrator",
            "model": "none",
            "tools": ["code", "shell"],
            "prompt_hint": "Merge branches and create PR.",
        }
    )

    return agents


def recommend_workflow(profile: ProjectProfile) -> dict:
    """Recommend a workflow pipeline based on the project profile."""
    has_frontend = any(
        f in profile.frameworks for f in ["react", "vue", "nextjs", "nuxt", "angular", "svelte"]
    )
    has_tests = len(profile.test_frameworks) > 0

    if has_frontend:
        # Full pipeline with parallel backend + frontend
        stages = [
            {
                "name": "plan",
                "agent": "architect",
                "gate": {"type": "approval"},
                "max_iterations": 10,
            },
            {
                "name": "backend",
                "agent": "backend-dev",
                "depends_on": "plan",
                "gate": {"type": "automated", "checks": ["tests_pass"]},
                "max_iterations": 8,
            },
            {
                "name": "frontend",
                "agent": "frontend-dev",
                "depends_on": "plan",
                "gate": {"type": "automated", "checks": ["tests_pass"]},
                "max_iterations": 8,
            },
            {
                "name": "review",
                "agent": "reviewer",
                "depends_on": ["backend", "frontend"],
                "gate": {"type": "score", "min_score": 80, "on_fail": "route_to", "max_retries": 2},
                "max_iterations": 3,
            },
            {
                "name": "e2e",
                "agent": "tester",
                "depends_on": "review",
                "gate": {"type": "automated", "checks": ["tests_pass"]},
                "max_iterations": 5,
            },
            {
                "name": "deliver",
                "agent": "integrator",
                "depends_on": "e2e",
                "gate": {"type": "approval"},
            },
        ]
        name = "Full Development Pipeline"
    elif has_tests:
        # Backend only with tests
        stages = [
            {
                "name": "plan",
                "agent": "architect",
                "gate": {"type": "approval"},
                "max_iterations": 10,
            },
            {
                "name": "backend",
                "agent": "backend-dev",
                "depends_on": "plan",
                "gate": {"type": "automated", "checks": ["tests_pass"]},
                "max_iterations": 8,
            },
            {
                "name": "review",
                "agent": "reviewer",
                "depends_on": "backend",
                "gate": {"type": "score", "min_score": 80, "on_fail": "route_to", "max_retries": 2},
                "max_iterations": 3,
            },
            {
                "name": "e2e",
                "agent": "tester",
                "depends_on": "review",
                "gate": {"type": "automated", "checks": ["tests_pass"]},
                "max_iterations": 5,
            },
            {
                "name": "deliver",
                "agent": "integrator",
                "depends_on": "e2e",
                "gate": {"type": "approval"},
            },
        ]
        name = "Backend Pipeline"
    else:
        # Minimal — no tests
        stages = [
            {
                "name": "plan",
                "agent": "architect",
                "gate": {"type": "approval"},
                "max_iterations": 10,
            },
            {
                "name": "backend",
                "agent": "backend-dev",
                "depends_on": "plan",
                "gate": {"type": "approval"},
                "max_iterations": 8,
            },
            {
                "name": "review",
                "agent": "reviewer",
                "depends_on": "backend",
                "gate": {"type": "score", "min_score": 80, "max_retries": 1},
                "max_iterations": 3,
            },
            {
                "name": "deliver",
                "agent": "integrator",
                "depends_on": "review",
                "gate": {"type": "approval"},
            },
        ]
        name = "Minimal Pipeline"

    return {"name": name, "stages": stages, "concurrency": 1}
