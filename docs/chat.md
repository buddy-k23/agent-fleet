# Chat Guide

## Starting a Conversation

1. Go to **Chat** in the sidebar
2. Click **New Chat**
3. Select an agent from the dropdown
4. Type your message and press Enter (or click Send)

## Agent Capabilities

| Agent | Best for | Tools available |
|-------|---------|----------------|
| Architect | Planning features, designing architecture | Read files, search |
| Backend Dev | Implementing server-side code | Read/write files, run commands |
| Frontend Dev | Building UI components | Read/write files, run commands |
| Reviewer | Code review, finding bugs | Read files, search |
| Tester | Running tests, checking coverage | Read files, run commands |

## Quick Actions

Click these chips above the input for common operations:

| Action | What it does |
|--------|-------------|
| 📋 Review code | Asks the agent to review recent changes |
| 🏗️ Plan feature | Starts a feature planning conversation |
| 📁 Browse files | Lists the project structure |
| 🧪 Run tests | Runs the test suite |

## Tips for Effective Prompts

1. **Be specific** — "Review src/calculator.py for edge cases" > "Review the code"
2. **Provide context** — "We're using FastAPI with SQLAlchemy" helps the agent
3. **One task at a time** — Don't ask for review + implementation in one message
4. **Reference files** — "Read tests/test_calculator.py and add a test for division by zero"

## How It Works

1. Your message is saved to Supabase
2. Sent to the agent via WebSocket
3. Agent processes using ReAct loop (LLM + tools)
4. Response streamed back token-by-token
5. Saved to conversation history

Messages persist across sessions via Supabase Realtime.
