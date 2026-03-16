import { useEffect, useState } from 'react';
import {
  Alert, Box, Button, Card, CardContent, Chip, Container, Dialog,
  DialogActions, DialogContent, DialogTitle, FormControl, Grid, IconButton,
  InputLabel, MenuItem, Select, Snackbar, TextField, Typography,
} from '@mui/material';
import { supabase } from '../../lib/supabase';
import { useAuth } from '../../contexts/AuthContext';

interface ApiKey {
  id: string;
  provider: string;
  label: string;
  masked_key: string;
  is_active: boolean;
}

const PROVIDERS = [
  { id: 'anthropic', label: 'Anthropic', color: '#6366F1' },
  { id: 'openai', label: 'OpenAI', color: '#10B981' },
  { id: 'google', label: 'Google', color: '#3B82F6' },
  { id: 'ollama', label: 'Ollama', color: '#F59E0B' },
];

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';

export default function Settings() {
  const { user } = useAuth();
  const [displayName, setDisplayName] = useState('');
  const [saved, setSaved] = useState(false);
  const [keys, setKeys] = useState<ApiKey[]>([]);
  const [addOpen, setAddOpen] = useState(false);
  const [newProvider, setNewProvider] = useState('anthropic');
  const [newKey, setNewKey] = useState('');
  const [newLabel, setNewLabel] = useState('');
  const [toast, setToast] = useState('');
  const [testResult, setTestResult] = useState<Record<string, string>>({});

  const getAuthHeaders = async () => {
    const { data } = await supabase.auth.getSession();
    return {
      'Authorization': `Bearer ${data.session?.access_token}`,
      'Content-Type': 'application/json',
    };
  };

  const loadProfile = async () => {
    if (!user) return;
    const { data } = await supabase.from('profiles').select('*').eq('id', user.id).single();
    if (data) setDisplayName(data.display_name || '');
  };

  const loadKeys = async () => {
    const headers = await getAuthHeaders();
    const r = await fetch(`${API_BASE}/api/v1/api-keys`, { headers });
    if (r.ok) setKeys(await r.json());
  };

  useEffect(() => { loadProfile(); loadKeys(); }, [user]);

  const handleSaveProfile = async () => {
    if (!user) return;
    await supabase.from('profiles').update({ display_name: displayName }).eq('id', user.id);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  const handleAddKey = async () => {
    const headers = await getAuthHeaders();
    const r = await fetch(`${API_BASE}/api/v1/api-keys`, {
      method: 'POST',
      headers,
      body: JSON.stringify({ provider: newProvider, api_key: newKey, label: newLabel }),
    });
    if (r.ok) {
      setAddOpen(false);
      setNewKey('');
      setNewLabel('');
      setToast('API key added');
      loadKeys();
    } else {
      setToast('Failed to add key');
    }
  };

  const handleDeleteKey = async (id: string) => {
    const headers = await getAuthHeaders();
    await fetch(`${API_BASE}/api/v1/api-keys/${id}`, { method: 'DELETE', headers });
    setToast('Key deleted');
    loadKeys();
  };

  const handleTestKey = async (id: string) => {
    const headers = await getAuthHeaders();
    const r = await fetch(`${API_BASE}/api/v1/api-keys/${id}/test`, { method: 'POST', headers });
    const result = await r.json();
    setTestResult((prev) => ({ ...prev, [id]: result.status === 'ok' ? '✓ Works' : `✗ ${result.message}` }));
  };

  return (
    <Container maxWidth="md" sx={{ py: 4 }}>
      <Typography variant="h4" data-testid="settings-title" gutterBottom>
        Settings
      </Typography>

      {/* Profile */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>Profile</Typography>
          <TextField
            label="Display Name" fullWidth value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            data-testid="display-name-input"
          />
          <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1 }}>
            Email: {user?.email}
          </Typography>
          <Button variant="contained" onClick={handleSaveProfile} sx={{ mt: 2 }} data-testid="save-profile-btn">
            {saved ? 'Saved!' : 'Save'}
          </Button>
        </CardContent>
      </Card>

      {/* API Keys */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
            <Typography variant="h6">API Keys</Typography>
            <Button variant="outlined" size="small" onClick={() => setAddOpen(true)} data-testid="add-key-btn">
              Add Key
            </Button>
          </Box>

          {keys.length === 0 && (
            <Typography variant="body2" color="text.secondary" data-testid="no-keys">
              No API keys configured. Add one to use LLM agents.
            </Typography>
          )}

          {keys.map((key) => {
            const provider = PROVIDERS.find((p) => p.id === key.provider);
            return (
              <Box
                key={key.id}
                sx={{ display: 'flex', alignItems: 'center', gap: 2, py: 1.5, borderBottom: 1, borderColor: 'divider' }}
                data-testid={`key-${key.provider}`}
              >
                <Chip
                  label={provider?.label || key.provider}
                  size="small"
                  sx={{ bgcolor: provider?.color, color: '#fff', minWidth: 90 }}
                />
                <Typography variant="body2" sx={{ fontFamily: '"Fira Code"', flex: 1 }}>
                  {key.masked_key}
                </Typography>
                {key.label && (
                  <Typography variant="caption" color="text.secondary">{key.label}</Typography>
                )}
                <Chip
                  label={key.is_active ? 'Active' : 'Inactive'}
                  size="small"
                  color={key.is_active ? 'success' : 'default'}
                />
                {testResult[key.id] && (
                  <Typography variant="caption" color={testResult[key.id].startsWith('✓') ? 'success.main' : 'error.main'}>
                    {testResult[key.id]}
                  </Typography>
                )}
                <Button size="small" onClick={() => handleTestKey(key.id)} data-testid={`test-${key.provider}`}>
                  Test
                </Button>
                <Button size="small" color="error" onClick={() => handleDeleteKey(key.id)} data-testid={`delete-${key.provider}`}>
                  Delete
                </Button>
              </Box>
            );
          })}
        </CardContent>
      </Card>

      {/* Model Registry */}
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>Model Registry</Typography>
          <Grid container spacing={2}>
            {PROVIDERS.map((p) => {
              const hasKey = keys.some((k) => k.provider === p.id && k.is_active);
              return (
                <Grid size={{ xs: 12, sm: 6 }} key={p.id}>
                  <Box sx={{ p: 2, border: 1, borderColor: 'divider', borderRadius: 1 }} data-testid={`model-${p.id}`}>
                    <Box display="flex" justifyContent="space-between" alignItems="center">
                      <Typography variant="subtitle2">{p.label}</Typography>
                      <Chip label={hasKey ? 'Configured' : 'Not set'} size="small" color={hasKey ? 'success' : 'default'} />
                    </Box>
                  </Box>
                </Grid>
              );
            })}
          </Grid>
        </CardContent>
      </Card>

      {/* Add Key Dialog */}
      <Dialog open={addOpen} onClose={() => setAddOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Add API Key</DialogTitle>
        <DialogContent>
          <FormControl fullWidth margin="dense" data-testid="key-provider-select">
            <InputLabel>Provider</InputLabel>
            <Select value={newProvider} label="Provider" onChange={(e) => setNewProvider(e.target.value)}>
              {PROVIDERS.map((p) => <MenuItem key={p.id} value={p.id}>{p.label}</MenuItem>)}
            </Select>
          </FormControl>
          <TextField
            label="API Key" fullWidth margin="dense" type="password"
            value={newKey} onChange={(e) => setNewKey(e.target.value)}
            placeholder="sk-ant-..." data-testid="key-input"
          />
          <TextField
            label="Label (optional)" fullWidth margin="dense"
            value={newLabel} onChange={(e) => setNewLabel(e.target.value)}
            placeholder="Production key" data-testid="key-label-input"
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setAddOpen(false)}>Cancel</Button>
          <Button variant="contained" onClick={handleAddKey} disabled={!newKey} data-testid="save-key-btn">
            Save Key
          </Button>
        </DialogActions>
      </Dialog>

      <Snackbar open={!!toast} autoHideDuration={3000} onClose={() => setToast('')} message={toast} />
    </Container>
  );
}
