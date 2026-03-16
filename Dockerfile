FROM python:3.12-slim

WORKDIR /app

# Install git (needed for worktree operations)
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY pyproject.toml .
RUN pip install --no-cache-dir -e "."

# Copy source
COPY src/ src/
COPY cli/ cli/
COPY config/ config/
COPY alembic/ alembic/
COPY alembic.ini .
COPY scripts/ scripts/

EXPOSE 8000

CMD ["uvicorn", "agent_fleet.main:app", "--host", "0.0.0.0", "--port", "8000"]
