import { useEffect, useState } from 'react';
import { Box, Button, Card, CardContent, Chip, Container, Dialog, DialogActions, DialogContent, DialogTitle, FormControl, InputLabel, ListSubheader, MenuItem, Select, TextField, Typography } from '@mui/material';
import { fetchAgents } from '../../services/api';

const AVAILABLE_MODELS = [
  { group: 'Anthropic', models: [
    { id: 'anthropic/claude-opus-4-6', label: 'Claude Opus 4.6' },
    { id: 'anthropic/claude-sonnet-4-6', label: 'Claude Sonnet 4.6' },
    { id: 'anthropic/claude-haiku-4-5-20251001', label: 'Claude Haiku 4.5' },
  ]},
  { group: 'OpenAI', models: [
    { id: 'openai/gpt-4o', label: 'GPT-4o' },
    { id: 'openai/gpt-4o-mini', label: 'GPT-4o Mini' },
    { id: 'openai/o3-mini', label: 'o3-mini' },
  ]},
  { group: 'Google', models: [
    { id: 'gemini/gemini-2.5-pro', label: 'Gemini 2.5 Pro' },
    { id: 'gemini/gemini-2.5-flash', label: 'Gemini 2.5 Flash' },
  ]},
  { group: 'Local (Ollama)', models: [
    { id: 'ollama/llama3', label: 'Llama 3' },
    { id: 'ollama/codellama', label: 'Code Llama' },
    { id: 'ollama/deepseek-coder', label: 'DeepSeek Coder' },
    { id: 'ollama/qwen2.5-coder', label: 'Qwen 2.5 Coder' },
  ]},
];

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
  const [selectedModel, setSelectedModel] = useState('anthropic/claude-sonnet-4-6');

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
          <FormControl fullWidth margin="dense" data-testid="agent-model-input">
            <InputLabel>Model</InputLabel>
            <Select
              value={selectedModel}
              label="Model"
              onChange={(e) => setSelectedModel(e.target.value)}
            >
              {AVAILABLE_MODELS.map((group) => [
                <ListSubheader key={group.group}>{group.group}</ListSubheader>,
                ...group.models.map((model) => (
                  <MenuItem key={model.id} value={model.id}>
                    {model.label}
                    <Typography
                      variant="caption"
                      color="text.secondary"
                      sx={{ ml: 1 }}
                    >
                      {model.id}
                    </Typography>
                  </MenuItem>
                )),
              ])}
            </Select>
          </FormControl>
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
