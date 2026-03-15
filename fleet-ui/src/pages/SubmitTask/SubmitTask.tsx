import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
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

export default function SubmitTask() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [repo, setRepo] = useState('');
  const [description, setDescription] = useState('');
  const [workflowId, setWorkflowId] = useState('');
  const [workflows, setWorkflows] = useState<Workflow[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    supabase.from('workflows').select('id, name').then(({ data }) => {
      if (data) {
        setWorkflows(data);
        if (data.length > 0) setWorkflowId(data[0].id);
      }
    });
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!user || !repo || !description) return;
    setLoading(true);
    setError('');

    const { data, error: err } = await supabase.from('tasks').insert({
      user_id: user.id,
      repo,
      description,
      workflow_id: workflowId || null,
      workflow_name: workflows.find((w) => w.id === workflowId)?.name || 'default',
      status: 'queued',
    }).select().single();

    setLoading(false);
    if (err) {
      setError(err.message);
    } else if (data) {
      navigate(`/tasks/${data.id}`);
    }
  };

  return (
    <Container maxWidth="sm" sx={{ py: 4 }}>
      <Typography variant="h4" data-testid="submit-title" gutterBottom>
        Submit Task
      </Typography>

      {error && <Alert severity="error" sx={{ mb: 2 }} data-testid="submit-error">{error}</Alert>}

      <Box component="form" onSubmit={handleSubmit}>
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
