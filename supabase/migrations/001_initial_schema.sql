-- Agent Fleet — Supabase Schema
-- Run this in the Supabase SQL Editor

-- ============================================================
-- PROFILES (auto-created on signup)
-- ============================================================
CREATE TABLE IF NOT EXISTS profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    display_name TEXT,
    default_workflow UUID,
    preferences JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own profile"
    ON profiles FOR SELECT USING (auth.uid() = id);
CREATE POLICY "Users can update own profile"
    ON profiles FOR UPDATE USING (auth.uid() = id);
CREATE POLICY "Users can insert own profile"
    ON profiles FOR INSERT WITH CHECK (auth.uid() = id);

-- Auto-create profile on signup
CREATE OR REPLACE FUNCTION handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO profiles (id, display_name)
    VALUES (NEW.id, COALESCE(NEW.raw_user_meta_data->>'display_name', NEW.email));
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE OR REPLACE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION handle_new_user();

-- ============================================================
-- AGENTS (AI agent configurations)
-- ============================================================
CREATE TABLE IF NOT EXISTS agents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    description TEXT DEFAULT '',
    model TEXT NOT NULL DEFAULT 'anthropic/claude-sonnet-4-6',
    tools TEXT[] DEFAULT '{}',
    capabilities TEXT[] DEFAULT '{}',
    system_prompt TEXT DEFAULT '',
    max_retries INT DEFAULT 2,
    timeout_minutes INT DEFAULT 30,
    max_tokens INT DEFAULT 100000,
    can_delegate TEXT[] DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE agents ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own agents"
    ON agents FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can create own agents"
    ON agents FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can update own agents"
    ON agents FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "Users can delete own agents"
    ON agents FOR DELETE USING (auth.uid() = user_id);

CREATE INDEX idx_agents_user_id ON agents(user_id);

-- ============================================================
-- WORKFLOWS (pipeline configurations)
-- ============================================================
CREATE TABLE IF NOT EXISTS workflows (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    stages JSONB NOT NULL DEFAULT '[]',
    concurrency INT DEFAULT 1,
    max_cost_usd FLOAT,
    classifier_mode TEXT DEFAULT 'suggest',
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE workflows ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own workflows"
    ON workflows FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can create own workflows"
    ON workflows FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can update own workflows"
    ON workflows FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "Users can delete own workflows"
    ON workflows FOR DELETE USING (auth.uid() = user_id);

CREATE INDEX idx_workflows_user_id ON workflows(user_id);

-- ============================================================
-- TASKS (pipeline executions)
-- ============================================================
CREATE TABLE IF NOT EXISTS tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    repo TEXT NOT NULL,
    description TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'queued',
    workflow_id UUID REFERENCES workflows(id),
    workflow_name TEXT DEFAULT 'default',
    current_stage TEXT,
    completed_stages TEXT[] DEFAULT '{}',
    total_tokens INT DEFAULT 0,
    total_cost_usd FLOAT DEFAULT 0,
    pr_url TEXT,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE tasks ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own tasks"
    ON tasks FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can create own tasks"
    ON tasks FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can update own tasks"
    ON tasks FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "Users can delete own tasks"
    ON tasks FOR DELETE USING (auth.uid() = user_id);

CREATE INDEX idx_tasks_user_id ON tasks(user_id);
CREATE INDEX idx_tasks_status ON tasks(status);

-- ============================================================
-- EXECUTIONS (per-stage agent runs)
-- ============================================================
CREATE TABLE IF NOT EXISTS executions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    stage TEXT NOT NULL,
    agent TEXT NOT NULL,
    model TEXT NOT NULL,
    status TEXT DEFAULT 'running',
    summary TEXT,
    files_changed JSONB DEFAULT '[]',
    tokens_used INT DEFAULT 0,
    worktree_path TEXT,
    started_at TIMESTAMPTZ DEFAULT now(),
    finished_at TIMESTAMPTZ
);

ALTER TABLE executions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own executions"
    ON executions FOR SELECT USING (
        EXISTS (SELECT 1 FROM tasks WHERE tasks.id = executions.task_id AND tasks.user_id = auth.uid())
    );
CREATE POLICY "Users can create own executions"
    ON executions FOR INSERT WITH CHECK (
        EXISTS (SELECT 1 FROM tasks WHERE tasks.id = executions.task_id AND tasks.user_id = auth.uid())
    );
CREATE POLICY "Users can update own executions"
    ON executions FOR UPDATE USING (
        EXISTS (SELECT 1 FROM tasks WHERE tasks.id = executions.task_id AND tasks.user_id = auth.uid())
    );

CREATE INDEX idx_executions_task_id ON executions(task_id);

-- ============================================================
-- GATE RESULTS (quality gate outcomes)
-- ============================================================
CREATE TABLE IF NOT EXISTS gate_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    execution_id UUID NOT NULL REFERENCES executions(id) ON DELETE CASCADE,
    gate_type TEXT NOT NULL,
    passed BOOLEAN DEFAULT false,
    score INT,
    details JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE gate_results ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own gate results"
    ON gate_results FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM executions e
            JOIN tasks t ON t.id = e.task_id
            WHERE e.id = gate_results.execution_id AND t.user_id = auth.uid()
        )
    );
CREATE POLICY "Users can create own gate results"
    ON gate_results FOR INSERT WITH CHECK (
        EXISTS (
            SELECT 1 FROM executions e
            JOIN tasks t ON t.id = e.task_id
            WHERE e.id = gate_results.execution_id AND t.user_id = auth.uid()
        )
    );

CREATE INDEX idx_gate_results_execution_id ON gate_results(execution_id);

-- ============================================================
-- EVENTS (append-only event log)
-- ============================================================
CREATE TABLE IF NOT EXISTS events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    execution_id UUID REFERENCES executions(id) ON DELETE SET NULL,
    event_type TEXT NOT NULL,
    payload JSONB DEFAULT '{}',
    timestamp TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE events ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own events"
    ON events FOR SELECT USING (
        EXISTS (SELECT 1 FROM tasks WHERE tasks.id = events.task_id AND tasks.user_id = auth.uid())
    );
CREATE POLICY "Users can create own events"
    ON events FOR INSERT WITH CHECK (
        EXISTS (SELECT 1 FROM tasks WHERE tasks.id = events.task_id AND tasks.user_id = auth.uid())
    );

CREATE INDEX idx_events_task_id ON events(task_id);
CREATE INDEX idx_events_timestamp ON events(timestamp);

-- ============================================================
-- STORAGE BUCKETS
-- ============================================================
INSERT INTO storage.buckets (id, name, public)
VALUES
    ('task-outputs', 'task-outputs', false),
    ('task-logs', 'task-logs', false)
ON CONFLICT (id) DO NOTHING;

-- Storage RLS: users can access their own task files
CREATE POLICY "Users can upload task outputs"
    ON storage.objects FOR INSERT
    WITH CHECK (bucket_id IN ('task-outputs', 'task-logs'));

CREATE POLICY "Users can view task outputs"
    ON storage.objects FOR SELECT
    USING (bucket_id IN ('task-outputs', 'task-logs'));

-- ============================================================
-- REALTIME (enable for live updates)
-- ============================================================
ALTER PUBLICATION supabase_realtime ADD TABLE tasks;
ALTER PUBLICATION supabase_realtime ADD TABLE executions;
ALTER PUBLICATION supabase_realtime ADD TABLE events;

-- ============================================================
-- UPDATED_AT TRIGGER (auto-update timestamp)
-- ============================================================
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_profiles_updated_at
    BEFORE UPDATE ON profiles FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER update_agents_updated_at
    BEFORE UPDATE ON agents FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER update_workflows_updated_at
    BEFORE UPDATE ON workflows FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER update_tasks_updated_at
    BEFORE UPDATE ON tasks FOR EACH ROW EXECUTE FUNCTION update_updated_at();
