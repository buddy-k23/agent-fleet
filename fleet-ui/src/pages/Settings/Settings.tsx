import { useEffect, useState } from 'react';
import {
  Box, Button, Card, CardContent, Chip, Container, Grid,
  TextField, Typography,
} from '@mui/material';
import { supabase } from '../../lib/supabase';
import { useAuth } from '../../contexts/AuthContext';

export default function Settings() {
  const { user } = useAuth();
  const [displayName, setDisplayName] = useState('');
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (!user) return;
    supabase.from('profiles').select('*').eq('id', user.id).single()
      .then(({ data }) => {
        if (data) setDisplayName(data.display_name || '');
      });
  }, [user]);

  const handleSave = async () => {
    if (!user) return;
    await supabase.from('profiles').update({ display_name: displayName }).eq('id', user.id);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  const models = [
    { provider: 'Anthropic', status: 'configured', color: '#6366F1' },
    { provider: 'OpenAI', status: 'not set', color: '#10B981' },
    { provider: 'Google', status: 'not set', color: '#3B82F6' },
    { provider: 'Ollama', status: 'not set', color: '#F59E0B' },
  ];

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
            label="Display Name"
            fullWidth
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            data-testid="display-name-input"
          />
          <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1 }}>
            Email: {user?.email}
          </Typography>
          <Button
            variant="contained"
            onClick={handleSave}
            sx={{ mt: 2 }}
            data-testid="save-profile-btn"
          >
            {saved ? 'Saved!' : 'Save'}
          </Button>
        </CardContent>
      </Card>

      {/* Model Registry */}
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>Model Registry</Typography>
          <Grid container spacing={2}>
            {models.map((m) => (
              <Grid size={{ xs: 12, sm: 6 }} key={m.provider}>
                <Box
                  sx={{ p: 2, border: 1, borderColor: 'divider', borderRadius: 1 }}
                  data-testid={`model-${m.provider.toLowerCase()}`}
                >
                  <Box display="flex" justifyContent="space-between" alignItems="center">
                    <Typography variant="subtitle2">{m.provider}</Typography>
                    <Chip
                      label={m.status}
                      size="small"
                      color={m.status === 'configured' ? 'success' : 'default'}
                    />
                  </Box>
                </Box>
              </Grid>
            ))}
          </Grid>
        </CardContent>
      </Card>
    </Container>
  );
}
