import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  Alert, Box, Button, Container, FormControl, InputLabel, MenuItem,
  Select, TextField, Typography,
} from '@mui/material';
import { supabase } from '../../lib/supabase';
import { useAuth } from '../../contexts/AuthContext';

interface Workflow {
  id: string;
  name: string;
}

interface Project {
  id: string;
  name: string;
  repo_path: string;
}

export default function SubmitTask() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [repo, setRepo] = useState('');
  const [description, setDescription] = useState('');
  const [workflowId, setWorkflowId] = useState('');
  const [projectId, setProjectId] = useState(searchParams.get('project_id') ?? '');
  const [workflows, setWorkflows] = useState<Workflow[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    supabase.from('workflows').select('id, name').then(({ data }) => {
      if (data) {
        setWorkflows(data);
        if (data.length > 0) setWorkflowId(data[0].id);
      }
    });
    supabase.from('projects').select('id, name, repo_path').order('created_at', { ascending: false }).then(({ data }) => {
      if (data) setProjects(data);
    });
  }, []);

  // Pre-fill repo path when a project is selected
  useEffect(() => {
    if (projectId) {
      const proj = projects.find((p) => p.id === projectId);
      if (proj && !repo) setRepo(proj.repo_path);
    }
  }, [projectId, projects]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!user || !repo || !description) return;
    setLoading(true);
    setError('');

    try {
      const token = (await supabase.auth.getSession()).data.session?.access_token;
      const response = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/v1/tasks`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          repo,
          description,
          workflow_id: workflowId,
          project_id: projectId || null,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to submit task');
      }

      const data = await response.json();
      navigate(`/tasks/${data.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to submit task');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Container maxWidth="sm" sx={{ py: 4 }}>
      <Typography variant="h4" data-testid="submit-title" gutterBottom>
        Submit Task
      </Typography>

      {error && <Alert severity="error" sx={{ mb: 2 }} data-testid="submit-error">{error}</Alert>}

      <Box component="form" onSubmit={handleSubmit}>
        {projects.length > 0 && (
          <FormControl fullWidth margin="normal" data-testid="project-select">
            <InputLabel>Project (optional)</InputLabel>
            <Select
              value={projectId}
              label="Project (optional)"
              onChange={(e) => setProjectId(e.target.value)}
            >
              <MenuItem value=""><em>None</em></MenuItem>
              {projects.map((p) => (
                <MenuItem key={p.id} value={p.id}>{p.name}</MenuItem>
              ))}
            </Select>
          </FormControl>
        )}
        <TextField
          label="Repository Path"
          fullWidth
          margin="normal"
          value={repo}
          onChange={(e) => setRepo(e.target.value)}
          placeholder="/path/to/repo or https://github.com/org/repo"
          required
          data-testid="repo-input"
        />
        <TextField
          label="Task Description"
          fullWidth
          margin="normal"
          multiline
          rows={4}
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Describe what you want the agent fleet to do..."
          required
          data-testid="description-input"
        />
        <FormControl fullWidth margin="normal" data-testid="workflow-select">
          <InputLabel>Workflow</InputLabel>
          <Select value={workflowId} label="Workflow" onChange={(e) => setWorkflowId(e.target.value)}>
            {workflows.map((w) => (
              <MenuItem key={w.id} value={w.id}>{w.name}</MenuItem>
            ))}
          </Select>
        </FormControl>
        <Button
          type="submit"
          variant="contained"
          fullWidth
          size="large"
          disabled={loading || !repo || !description}
          sx={{ mt: 2 }}
          data-testid="submit-task-btn"
        >
          {loading ? 'Submitting...' : 'Submit Task'}
        </Button>
      </Box>
    </Container>
  );
}
