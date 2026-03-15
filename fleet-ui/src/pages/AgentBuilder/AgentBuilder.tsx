import { useEffect, useState } from 'react';
import { Box, Button, Card, CardContent, Chip, Container, Dialog, DialogActions, DialogContent, DialogTitle, TextField, Typography } from '@mui/material';
import { fetchAgents } from '../../services/api';

interface AgentConfig {
  name: string;
  description: string;
  default_model: string;
  tools: string[];
  capabilities: string[];
}

export default function AgentBuilder() {
  const [agents, setAgents] = useState<AgentConfig[]>([]);
  const [dialogOpen, setDialogOpen] = useState(false);

  useEffect(() => {
    fetchAgents()
      .then((data) => setAgents(data as AgentConfig[]))
      .catch(() => {});
  }, []);

  return (
    <Container maxWidth="md" sx={{ py: 4 }}>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4" data-testid="agents-title">
          Agent Builder
        </Typography>
        <Button
          variant="contained"
          onClick={() => setDialogOpen(true)}
          data-testid="create-agent-btn"
        >
          Create Agent
        </Button>
      </Box>

      {agents.map((agent) => (
        <Card key={agent.name} sx={{ mb: 2 }} data-testid={`agent-card-${agent.name}`}>
          <CardContent>
            <Typography variant="h6">{agent.name}</Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
              {agent.description}
            </Typography>
            <Box display="flex" gap={1} flexWrap="wrap">
              <Chip label={agent.default_model} size="small" color="primary" />
              {agent.tools.map((t) => (
                <Chip key={t} label={t} size="small" variant="outlined" />
              ))}
            </Box>
          </CardContent>
        </Card>
      ))}

      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Create New Agent</DialogTitle>
        <DialogContent>
          <TextField label="Name" fullWidth margin="dense" data-testid="agent-name-input" />
          <TextField label="Description" fullWidth margin="dense" multiline rows={2} data-testid="agent-desc-input" />
          <TextField label="Model" fullWidth margin="dense" placeholder="anthropic/claude-sonnet-4-6" data-testid="agent-model-input" />
          <TextField label="Tools (comma-separated)" fullWidth margin="dense" placeholder="code, shell" data-testid="agent-tools-input" />
          <TextField label="System Prompt" fullWidth margin="dense" multiline rows={4} data-testid="agent-prompt-input" />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)}>Cancel</Button>
          <Button variant="contained" data-testid="save-agent-btn">Save</Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
}
