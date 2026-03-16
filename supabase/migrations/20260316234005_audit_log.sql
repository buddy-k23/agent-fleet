-- Immutable audit log — no UPDATE, no DELETE
CREATE TABLE IF NOT EXISTS audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    timestamp TIMESTAMPTZ DEFAULT now() NOT NULL,
    actor_id UUID REFERENCES auth.users(id),
    actor_email TEXT,
    action TEXT NOT NULL,
    resource_type TEXT NOT NULL,
    resource_id TEXT,
    details JSONB DEFAULT '{}',
    ip_address TEXT
);

ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY;

-- SELECT only — no UPDATE, no DELETE (immutable)
CREATE POLICY "Users can view audit log" ON audit_log FOR SELECT USING (true);
CREATE POLICY "System can insert audit entries" ON audit_log FOR INSERT WITH CHECK (true);

CREATE INDEX idx_audit_log_timestamp ON audit_log(timestamp);
CREATE INDEX idx_audit_log_actor_id ON audit_log(actor_id);
CREATE INDEX idx_audit_log_action ON audit_log(action);
CREATE INDEX idx_audit_log_resource ON audit_log(resource_type, resource_id);

-- Approvals table for banking workflows
CREATE TABLE IF NOT EXISTS approvals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    stage TEXT NOT NULL,
    approver_id UUID REFERENCES auth.users(id),
    approver_email TEXT,
    decision TEXT NOT NULL CHECK (decision IN ('approved', 'rejected')),
    reason TEXT,
    ip_address TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE approvals ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can view approvals" ON approvals FOR SELECT USING (true);
CREATE POLICY "Users can create approvals" ON approvals FOR INSERT WITH CHECK (auth.uid() = approver_id);
CREATE INDEX idx_approvals_task_id ON approvals(task_id);
