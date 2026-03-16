# API Reference

Base URL: `http://localhost:8000`

## Health
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/health` | No | Returns `{"status":"ok","version":"0.1.0"}` |

## Tasks
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/v1/tasks` | No | Submit task |
| GET | `/api/v1/tasks` | No | List tasks |
| GET | `/api/v1/tasks/{id}` | No | Get task |

## Agents
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/agents` | JWT | List user's agents |
| POST | `/api/v1/agents` | JWT | Create agent |
| PUT | `/api/v1/agents/{id}` | JWT | Update agent |
| DELETE | `/api/v1/agents/{id}` | JWT | Delete agent |

## Workflows
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/workflows` | JWT | List workflows |
| GET | `/api/v1/workflows/{id}` | JWT | Get workflow |
| POST | `/api/v1/workflows` | JWT | Create workflow |
| PUT | `/api/v1/workflows/{id}` | JWT | Update workflow |
| DELETE | `/api/v1/workflows/{id}` | JWT | Delete workflow |

## Profile
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/profile` | JWT | Get profile |
| PUT | `/api/v1/profile` | JWT | Update profile |

## Webhooks
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/v1/webhooks/github` | Signature | GitHub webhook |

## WebSocket
| Path | Description |
|------|-------------|
| `ws://localhost:8000/ws/chat/{conversation_id}` | Chat with agent |

### Auth Header
```
Authorization: Bearer <supabase_jwt_token>
```
