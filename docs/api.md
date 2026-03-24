# API Reference

Base URL: `http://localhost:8000`

## Authentication
Protected endpoints require: `Authorization: Bearer <supabase_jwt_token>`

## Endpoints

### Health
```bash
curl http://localhost:8000/health
# {"status":"ok","version":"0.1.0"}
```

### Tasks
```bash
# Submit task
curl -X POST http://localhost:8000/api/v1/tasks \
  -H "Content-Type: application/json" \
  -d '{"repo":"/path/to/repo","description":"Add multiply","workflow_id":"wf-uuid-1234","project_id":"proj-uuid-5678"}'
# project_id is optional
# Response (201):
# {
#   "task_id": "task-a1b2c3d4",
#   "status": "queued",
#   "current_stage": null,
#   "completed_stages": [],
#   "total_tokens": 0,
#   "total_cost_usd": 0.0,
#   "pr_url": null,
#   "error_message": null,
#   "created_at": "2026-03-24T00:00:00Z",
#   "updated_at": "2026-03-24T00:00:00Z"
# }

# List tasks
curl http://localhost:8000/api/v1/tasks
# {"tasks":[...]}

# Get task
curl http://localhost:8000/api/v1/tasks/task-a1b2c3d4
# 404 if not found

# Cancel task (queued or running)
curl -X DELETE http://localhost:8000/api/v1/tasks/task-a1b2c3d4/cancel
# Response (200): {"task_id":"task-a1b2c3d4","status":"cancelled"}
```

### Agents (JWT required)
```bash
# List agents
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/agents

# Create agent
curl -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  http://localhost:8000/api/v1/agents \
  -d '{"name":"DBA","description":"Database agent","model":"anthropic/claude-sonnet-4-6","tools":["code","shell"],"system_prompt":"You are a DBA."}'

# Update: PUT /api/v1/agents/{id}
# Delete: DELETE /api/v1/agents/{id} → 204
```

### Workflows (JWT required)
```bash
# List: GET /api/v1/workflows
# Get:  GET /api/v1/workflows/{id}
# Create: POST /api/v1/workflows
#   Body: {"name":"Custom","stages":[...],"concurrency":1}
# Update: PUT /api/v1/workflows/{id}
# Delete: DELETE /api/v1/workflows/{id} → 204
```

### API Keys (JWT required)
```bash
# List (masked)
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/api-keys
# [{"id":"uuid","provider":"anthropic","masked_key":"sk-ant-***...QwAA","is_active":true}]

# Add key
curl -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  http://localhost:8000/api/v1/api-keys \
  -d '{"provider":"anthropic","api_key":"sk-ant-...","label":"Production"}'

# Test key: POST /api/v1/api-keys/{id}/test → {"status":"ok"} or {"status":"error"}
# Delete:   DELETE /api/v1/api-keys/{id} → 204
```

### Profile (JWT required)
```bash
# Get:    GET /api/v1/profile
# Update: PUT /api/v1/profile -d '{"display_name":"My Name"}'
```

### Webhooks
```bash
# GitHub webhook
curl -X POST http://localhost:8000/api/v1/webhooks/github \
  -H "X-GitHub-Event: issues" \
  -H "Content-Type: application/json" \
  -d '{"action":"opened","issue":{"number":1,"title":"Bug"},"repository":{"full_name":"org/repo"}}'
```

### WebSocket (Chat)
```
ws://localhost:8000/ws/chat/{conversation_id}
Send: {"content":"Review this code","agent":"reviewer"}
Receive: {"type":"token","content":"The "} → {"type":"done","content":"..."}
```

## Error Codes
| Status | Meaning |
|--------|---------|
| 401 | Missing/invalid JWT |
| 404 | Not found |
| 422 | Validation error |
