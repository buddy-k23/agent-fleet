# Security Guide

## Authentication Flow

1. User signs in via Supabase Auth (email + password)
2. Supabase returns JWT token
3. React UI stores token in localStorage
4. API requests include `Authorization: Bearer <token>`
5. FastAPI middleware validates JWT via Supabase
6. Extracts `user_id` from token claims
7. All queries scoped to `user_id`

## Row Level Security (RLS)

Every table has RLS enabled. Users can only access their own data.

| Table | Policy |
|-------|--------|
| profiles | `auth.uid() = id` |
| agents | `auth.uid() = user_id` |
| workflows | `auth.uid() = user_id` |
| tasks | `auth.uid() = user_id` |
| executions | via tasks FK (join check) |
| gate_results | via executions → tasks FK |
| events | via tasks FK |
| conversations | `auth.uid() = user_id` |
| messages | via conversations FK |
| api_keys | `auth.uid() = user_id` |
| projects | `auth.uid() = user_id` |

## API Key Encryption

- Keys encrypted at rest using **Fernet symmetric encryption**
- Encryption key derived from `JWT_SECRET` via SHA-256
- Keys never returned in plain text via API
- Displayed masked: `sk-ant-***...QwAA` (first 6 + last 4 chars)
- Decrypted only when making LLM calls (server-side only)

## Key Rotation

1. **LLM API Keys:** Delete old key in Settings, add new one
2. **Supabase Keys:** Regenerate in Supabase dashboard, update `.env`
3. **JWT Secret:** Change in Supabase, update all services

## Webhook Security

GitHub webhooks validated via `X-Hub-Signature-256` HMAC-SHA256 when `GITHUB_WEBHOOK_SECRET` is set.

## Best Practices

- Never commit `.env` files (gitignored)
- Use `sb_secret_` key only on backend (never in frontend)
- Rotate API keys regularly
- Enable email confirmation in production
- Use HTTPS in production (reverse proxy)
