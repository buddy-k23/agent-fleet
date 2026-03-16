-- Projects table for onboarding
CREATE TABLE IF NOT EXISTS projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    repo_path TEXT NOT NULL,
    languages TEXT[] DEFAULT '{}',
    frameworks TEXT[] DEFAULT '{}',
    test_frameworks TEXT[] DEFAULT '{}',
    databases TEXT[] DEFAULT '{}',
    has_ci BOOLEAN DEFAULT false,
    ci_platform TEXT,
    has_claude_md BOOLEAN DEFAULT false,
    has_docker BOOLEAN DEFAULT false,
    estimated_loc INT DEFAULT 0,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE projects ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own projects"
    ON projects FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can create own projects"
    ON projects FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can update own projects"
    ON projects FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "Users can delete own projects"
    ON projects FOR DELETE USING (auth.uid() = user_id);

CREATE INDEX idx_projects_user_id ON projects(user_id);
