-- Add project_id FK to tasks table
ALTER TABLE tasks ADD COLUMN project_id UUID REFERENCES projects(id) ON DELETE SET NULL;
CREATE INDEX idx_tasks_project_id ON tasks(project_id);

-- Add updated_at trigger for projects (function already exists from initial schema)
CREATE TRIGGER update_projects_updated_at
  BEFORE UPDATE ON projects
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();
