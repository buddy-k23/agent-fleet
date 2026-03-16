import { useEffect, useState } from 'react';
import {
  Box, Button, Card, CardContent, Chip, Container, Dialog, DialogActions,
  DialogContent, DialogTitle, FormControl, Grid, InputLabel, ListSubheader,
  MenuItem, Select, TextField, Typography, Paper,
} from '@mui/material';
import { supabase } from '../../lib/supabase';
import { useAuth } from '../../contexts/AuthContext';

interface Agent {
  id: string;
  name: string;
  description: string;
  model: string;
  tools: string[];
  capabilities: string[];
  system_prompt: string;
  max_retries: number;
  timeout_minutes: number;
  max_tokens: number;
}

const MODELS = [
  { group: 'Anthropic', models: [
    { id: 'anthropic/claude-opus-4-6', label: 'Claude Opus 4.6' },
    { id: 'anthropic/claude-sonnet-4-6', label: 'Claude Sonnet 4.6' },
    { id: 'anthropic/claude-haiku-4-5-20251001', label: 'Claude Haiku 4.5' },
  ]},
  { group: 'OpenAI', models: [
    { id: 'openai/gpt-4o', label: 'GPT-4o' },
    { id: 'openai/gpt-4o-mini', label: 'GPT-4o Mini' },
  ]},
  { group: 'Google', models: [
    { id: 'gemini/gemini-2.5-pro', label: 'Gemini 2.5 Pro' },
    { id: 'gemini/gemini-2.5-flash', label: 'Gemini 2.5 Flash' },
  ]},
  { group: 'Local (Ollama)', models: [
    { id: 'ollama/llama3', label: 'Llama 3' },
    { id: 'ollama/codellama', label: 'Code Llama' },
    { id: 'ollama/deepseek-coder', label: 'DeepSeek Coder' },
  ]},
];

const TOOL_OPTIONS = ['code', 'shell', 'browser', 'search', 'api'];

const MODEL_COLORS: Record<string, string> = {
  anthropic: '#6366F1', openai: '#10B981', gemini: '#3B82F6', ollama: '#F59E0B',
};

function getProviderColor(model: string): string {
  const provider = model.split('/')[0];
  return MODEL_COLORS[provider] || '#9CA3AF';
}

const EMPTY_AGENT = {
  name: '', description: '', model: 'anthropic/claude-sonnet-4-6',
  tools: ['code', 'shell'] as string[], capabilities: [] as string[],
  system_prompt: '', max_retries: 2, timeout_minutes: 30, max_tokens: 100000,
};

export default function AgentBuilder() {
  const { user } = useAuth();
  const [agents, setAgents] = useState<Agent[]>([]);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [form, setForm] = useState(EMPTY_AGENT);
  const [editId, setEditId] = useState<string | null>(null);
  const [search, setSearch] = useState('');

  const load = async () => {
    const { data } = await supabase.from('agents').select('*').order('name');
    if (data) setAgents(data);
  };

  useEffect(() => { load(); }, []);

  const handleSave = async () => {
    if (editId) {
      await supabase.from('agents').update(form).eq('id', editId);
    } else {
      await supabase.from('agents').insert({ ...form, user_id: user?.id });
    }
    setDialogOpen(false);
    setForm(EMPTY_AGENT);
    setEditId(null);
    load();
  };

  const handleEdit = (agent: Agent) => {
    setForm({
      name: agent.name, description: agent.description, model: agent.model,
      tools: agent.tools || [], capabilities: agent.capabilities || [],
      system_prompt: agent.system_prompt, max_retries: agent.max_retries,
      timeout_minutes: agent.timeout_minutes, max_tokens: agent.max_tokens,
    });
    setEditId(agent.id);
    setDialogOpen(true);
  };

  const handleDelete = async (id: string) => {
    await supabase.from('agents').delete().eq('id', id);
    load();
  };

  const filtered = agents.filter((a) =>
    a.name.toLowerCase().includes(search.toLowerCase())
    || a.description.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4" data-testid="agents-title">Agents</Typography>
        <Button variant="contained" onClick={() => { setForm(EMPTY_AGENT); setEditId(null); setDialogOpen(true); }} data-testid="create-agent-btn">
          Create Agent
        </Button>
      </Box>

      <TextField
        placeholder="Search agents..."
        size="small"
        fullWidth
        sx={{ mb: 3 }}
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        data-testid="agent-search"
      />

      <Grid container spacing={2}>
        {filtered.map((agent) => (
          <Grid size={{ xs: 12, sm: 6, md: 4 }} key={agent.id}>
            <Card data-testid={`agent-card-${agent.name}`} sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
              <CardContent sx={{ flex: 1 }}>
                <Typography variant="h6" sx={{ fontFamily: '"Fira Code"' }}>{agent.name}</Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 1, minHeight: 40 }}>
                  {agent.description?.slice(0, 80)}
                </Typography>
                <Chip
                  label={agent.model.split('/')[1]}
                  size="small"
                  sx={{ bgcolor: getProviderColor(agent.model), color: '#fff', mb: 1 }}
                />
                <Box display="flex" gap={0.5} flexWrap="wrap">
                  {agent.tools?.map((t) => (
                    <Chip key={t} label={t} size="small" variant="outlined" />
                  ))}
                </Box>
              </CardContent>
              <Box sx={{ px: 2, pb: 1, display: 'flex', justifyContent: 'flex-end', gap: 1 }}>
                <Button size="small" onClick={() => handleEdit(agent)} data-testid={`edit-${agent.name}`}>Edit</Button>
                <Button size="small" color="error" onClick={() => handleDelete(agent.id)} data-testid={`delete-${agent.name}`}>Delete</Button>
              </Box>
            </Card>
          </Grid>
        ))}
      </Grid>

      {/* Create/Edit Dialog */}
      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>{editId ? 'Edit Agent' : 'Create Agent'}</DialogTitle>
        <DialogContent>
          <Grid container spacing={2} sx={{ mt: 0.5 }}>
            <Grid size={{ xs: 12, md: 6 }}>
              <TextField label="Name" fullWidth value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} data-testid="agent-name-input" />
              <TextField label="Description" fullWidth multiline rows={2} sx={{ mt: 2 }} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} data-testid="agent-desc-input" />
              <FormControl fullWidth sx={{ mt: 2 }} data-testid="agent-model-input">
                <InputLabel>Model</InputLabel>
                <Select value={form.model} label="Model" onChange={(e) => setForm({ ...form, model: e.target.value })}>
                  {MODELS.map((g) => [
                    <ListSubheader key={g.group}>{g.group}</ListSubheader>,
                    ...g.models.map((m) => <MenuItem key={m.id} value={m.id}>{m.label}</MenuItem>),
                  ])}
                </Select>
              </FormControl>
              <Box sx={{ mt: 2 }}>
                <Typography variant="body2" gutterBottom>Tools</Typography>
                <Box display="flex" gap={1} flexWrap="wrap">
                  {TOOL_OPTIONS.map((t) => (
                    <Chip
                      key={t}
                      label={t}
                      variant={form.tools.includes(t) ? 'filled' : 'outlined'}
                      color={form.tools.includes(t) ? 'primary' : 'default'}
                      onClick={() => setForm({
                        ...form,
                        tools: form.tools.includes(t) ? form.tools.filter((x) => x !== t) : [...form.tools, t],
                      })}
                      sx={{ cursor: 'pointer' }}
                      data-testid={`tool-${t}`}
                    />
                  ))}
                </Box>
              </Box>
              <TextField label="System Prompt" fullWidth multiline rows={4} sx={{ mt: 2, fontFamily: '"Fira Code"' }} value={form.system_prompt} onChange={(e) => setForm({ ...form, system_prompt: e.target.value })} data-testid="agent-prompt-input" />
            </Grid>
            <Grid size={{ xs: 12, md: 6 }}>
              <Typography variant="subtitle2" gutterBottom>YAML Preview</Typography>
              <Paper sx={{ p: 2, bgcolor: 'background.default', fontFamily: '"Fira Code", monospace', fontSize: 12, whiteSpace: 'pre-wrap', minHeight: 400, overflow: 'auto' }} data-testid="yaml-preview">
{`name: "${form.name}"
description: "${form.description}"
default_model: "${form.model}"
tools:
${form.tools.map((t) => `  - ${t}`).join('\n')}
system_prompt: |
  ${form.system_prompt.split('\n').join('\n  ')}
max_retries: ${form.max_retries}
timeout_minutes: ${form.timeout_minutes}
max_tokens: ${form.max_tokens}`}
              </Paper>
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)}>Cancel</Button>
          <Button variant="contained" onClick={handleSave} disabled={!form.name} data-testid="save-agent-btn">
            {editId ? 'Update' : 'Create'}
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
}
